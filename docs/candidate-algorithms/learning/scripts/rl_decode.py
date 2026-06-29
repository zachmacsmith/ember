"""Decode-aware RL: REINFORCE with minorminer in the loop. The policy (GNN ->
per-vertex layout mean mu, + learnable sigma) is warm-started from the Procrustes
model, then fine-tuned to directly minimize decoded ACL. Reward = per-graph
baseline - ACL (so it needs no differentiable decode). A small Procrustes anchor
keeps the layout structured. Parallel MM decodes via a persistent process pool.

Usage: python rl_decode.py [smoke]
"""
import warnings; warnings.filterwarnings("ignore")
import sys, json, time, numpy as np, torch, networkx as nx, dwave_networkx as dnx, statistics as st
from concurrent.futures import ProcessPoolExecutor
from torch_geometric.loader import DataLoader
from ember_qc_learn.dataset import EmbedDataset
from ember_qc_learn.features import target_geometry, SOURCE_FEATURE_DIM
from ember_qc_learn.models.base import build_model
import ember_qc_learn.models.gnn_seed  # noqa

SMOKE = len(sys.argv) > 1 and sys.argv[1] == "smoke"
dev = torch.device("cuda" if torch.cuda.is_available() else "cpu")
torch.manual_seed(0); np.random.seed(0)
geo = target_geometry(dnx.pegasus_graph(6), "pegasus_6")
QC, QN = geo["coords"], geo["qubit_nodes"]
SCALE = 0.3

def place(P):
    lo, hi = P.min(0), P.max(0); span = np.where(hi-lo > 1e-6, hi-lo, 1.0)
    return 0.5 + ((P-lo)/span - 0.5) * SCALE

# ---- pooled MM decode ----
_E = _QC = _QN = None
def _pool_init(qc, qn):
    global _E, _QC, _QN
    import warnings as w; w.filterwarnings("ignore")
    _E = list(dnx.pegasus_graph(6).edges()); _QC = qc; _QN = qn
def _decode(args):
    import minorminer
    from ember_qc_learn.decode import coords_to_qubit_scores, seed_chains_from_scores
    edges, n, placed, seed = args
    H = nx.Graph(); H.add_nodes_from(range(n)); H.add_edges_from(edges)
    sn = sorted(H.nodes())
    init = seed_chains_from_scores(coords_to_qubit_scores(np.asarray(placed), _QC), _QN, sn)
    e = minorminer.find_embedding(H, _E, initial_chains=init, random_seed=seed, timeout=20, verbose=0)
    return sum(len(c) for c in e.values())/len(e) if e else None
def _decode_cold(args):
    import minorminer
    edges, n, seed = args
    H = nx.Graph(); H.add_nodes_from(range(n)); H.add_edges_from(edges)
    e = minorminer.find_embedding(H, _E, random_seed=seed, timeout=20, verbose=0)
    return sum(len(c) for c in e.values())/len(e) if e else None

# ---- procrustes warm-start ----
def ploss_g(p, y):
    pc = p-p.mean(0,keepdim=True); yc = y-y.mean(0,keepdim=True)
    U,S,Vh = torch.linalg.svd(pc.t()@yc); R = U@Vh; s = S.sum()/((pc**2).sum()+1e-8)
    return ((s*(pc@R)-yc)**2).mean()
def ploss(model, batch):
    P = model(batch); Y = batch.y; b = batch.batch
    ls = [ploss_g(P[b==g], Y[b==g]) for g in b.unique() if (b==g).sum()>=3]
    return torch.stack(ls).mean() if ls else P.sum()*0

tr = EmbedDataset("data/learn/train.jsonl", "pegasus_6", geo=geo)
va = EmbedDataset("data/learn/val.jsonl", "pegasus_6", geo=geo)
trex = tr.examples[:300] if SMOKE else tr.examples
trmeta = tr.meta[:300] if SMOKE else tr.meta
model = build_model("gnn-seed", in_dim=SOURCE_FEATURE_DIM, hidden=160, layers=5, conv="sage", dropout=0.1).to(dev)
opt = torch.optim.Adam(model.parameters(), lr=2e-3, weight_decay=1e-5)
pre_ep = 5 if SMOKE else 90
for ep in range(pre_ep):
    model.train()
    for bt in DataLoader(trex, batch_size=32, shuffle=True):
        bt = bt.to(dev); opt.zero_grad(); ploss(model, bt).backward(); opt.step()
print(f"procrustes warm-start done ({pre_ep}ep)", flush=True)

# ---- RL fine-tune ----
log_sigma = torch.tensor(float(np.log(0.06)), device=dev, requires_grad=True)
opt = torch.optim.Adam(list(model.parameters()) + [log_sigma], lr=5e-4)
M = 6                                   # samples per graph
RL_EP = 1 if SMOKE else 12
edge_cache = {m["id"]: (m["edges"], m["n"]) for m in trmeta}
id_by_ex = [m["id"] for m in trmeta]
pool = ProcessPoolExecutor(max_workers=(8 if SMOKE else 28), initializer=_pool_init, initargs=(QC, QN))

@torch.no_grad()
def eval_policy(n_eval, pool):
    """Deterministic policy single-shot vs cold MM on val (same graphs)."""
    model.eval()
    ptasks, ctasks, metas = [], [], []
    for d, meta in list(zip(va.examples, va.meta))[:n_eval]:
        bt = next(iter(DataLoader([d], batch_size=1))).to(dev)
        P = model(bt).cpu().numpy()
        ptasks.append((meta["edges"], meta["n"], place(P).tolist(), 0))
        ctasks.append((meta["edges"], meta["n"], 0)); metas.append(meta)
    pacl = list(pool.map(_decode, ptasks)); cacl = list(pool.map(_decode_cold, ctasks))
    pr = [a for a in pacl if a]; cr = [a for a in cacl if a]
    return st.mean(pr), st.mean(cr)

best = {"gain": -9}
for ep in range(1, RL_EP+1):
    model.train(); t0 = time.time()
    order = np.random.permutation(len(trex))
    B = 24
    for s in range(0, len(order), B):
        idx = order[s:s+B]; bex = [trex[i] for i in idx]
        bt = next(iter(DataLoader(bex, batch_size=len(bex)))).to(dev)
        mu = model(bt)                              # [sumN,2] grad
        sigma = log_sigma.exp().clamp(min=0.02, max=0.25)
        bvec = bt.batch
        tasks, rec = [], []                          # rec: (gpos, sample_tensor)
        for gi, i in enumerate(idx):
            mg = mu[bvec == gi]
            eid = id_by_ex[i]; edges, n = edge_cache[eid]
            for m in range(M):
                eps = torch.randn_like(mg)
                x = (mg.detach() + sigma.detach()*eps).clamp(0, 1)
                tasks.append((edges, n, place(x.detach().cpu().numpy()).tolist(), m))
                rec.append((gi, x))
        acls = list(pool.map(_decode, tasks, chunksize=2))
        # per-graph baseline + advantage; policy loss
        from collections import defaultdict
        by_g = defaultdict(list)
        for k, (gi, x) in enumerate(rec):
            by_g[gi].append((k, acls[k]))
        ploss_terms = []
        for gi, items in by_g.items():
            valid = [(k, a) for k, a in items if a is not None]
            if len(valid) < 2: continue
            base = float(np.mean([a for _, a in valid])); sd = float(np.std([a for _, a in valid])) + 1e-6
            mg = mu[bvec == gi]
            for k, a in valid:
                adv = (base - a) / sd                # normalized advantage (lower ACL -> +)
                x = rec[k][1]
                logp = (-0.5*((x - mg)/sigma)**2 - torch.log(sigma)).sum()
                ploss_terms.append(-logp * adv)
        if not ploss_terms: continue
        pg = torch.stack(ploss_terms).mean()
        anchor = 0.2 * ploss(model, bt)              # keep layout structured
        loss = pg + anchor
        opt.zero_grad(); loss.backward()
        torch.nn.utils.clip_grad_norm_(list(model.parameters()) + [log_sigma], 5.0)
        opt.step()
    pa, ca = eval_policy(40 if SMOKE else 120, pool)
    gain = (ca - pa) / ca * 100
    print(f"RL ep{ep:2d} val: policy {pa:.3f} vs coldMM {ca:.3f}  gain {gain:+.2f}%  "
          f"sigma={log_sigma.exp().item():.3f}  ({time.time()-t0:.0f}s)", flush=True)
    if gain > best["gain"]:
        best = {"gain": gain, "ep": ep}
        torch.save({"model_name": "gnn-seed",
                    "cfg": dict(in_dim=SOURCE_FEATURE_DIM, hidden=160, layers=5, conv="sage", dropout=0.1),
                    "target": "pegasus_6", "feature_dim": SOURCE_FEATURE_DIM,
                    "state_dict": model.state_dict(),
                    "inference": {"placement": "compact", "scale": SCALE},
                    "metric": best}, "ckpts/rl_pegasus_6.pt")
pool.shutdown()
print(f"BEST RL gain over cold MM (val, single-shot): {best['gain']:+.2f}% @ep{best.get('ep')}", flush=True)
