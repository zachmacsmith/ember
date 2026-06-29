"""Decisive head-to-head on the full test set at fair budget:
  cold MM | Procrustes layout | RL-finetuned layout   (single-shot and best-of-8).
Answers: does decode-aware RL beat the supervised Procrustes layout, and does
either beat cold minorminer? With per-graph Wilcoxon significance."""
import warnings; warnings.filterwarnings("ignore")
import json, numpy as np, torch, networkx as nx, dwave_networkx as dnx, statistics as st
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor
from torch_geometric.data import Data
from scipy.stats import wilcoxon
from ember_qc_learn.features import target_geometry, source_features
from ember_qc_learn.models.base import build_model
import ember_qc_learn.models.gnn_seed  # noqa

geo = target_geometry(dnx.pegasus_graph(6), "pegasus_6")
QC, QN = geo["coords"], geo["qubit_nodes"]; SCALE = 0.3
def place(P):
    lo, hi = P.min(0), P.max(0); span = np.where(hi-lo > 1e-6, hi-lo, 1.0)
    return 0.5 + ((P-lo)/span - 0.5) * SCALE

def load(path):
    ck = torch.load(path, map_location="cpu", weights_only=False)
    m = build_model(ck["model_name"], **ck["cfg"]); m.load_state_dict(ck["state_dict"]); m.eval(); return m
models = {"proc": load("ckpts/procrustes_pegasus_6.pt"), "rl": load("ckpts/rl_pegasus_6.pt")}

recs = [json.loads(l) for l in open("data/learn/test.jsonl")]
recs = [r for r in recs if r.get("labels", {}).get("pegasus_6", {}).get("embedding")]
# predict layouts per model
def predict(model, rec):
    sf = source_features(_graph(rec))
    d = Data(x=torch.from_numpy(sf["x"]), edge_index=torch.from_numpy(sf["edge_index"])); d.num_nodes = sf["n"]
    with torch.no_grad(): P = model(d).cpu().numpy()
    return place(P).tolist()
def _graph(rec):
    H = nx.Graph(); H.add_nodes_from(range(rec["n"])); H.add_edges_from((u, v) for u, v in rec["edges"]); return H
for r in recs:
    r["_proc"] = predict(models["proc"], r); r["_rl"] = predict(models["rl"], r)
print(f"{len(recs)} test graphs", flush=True)

_E = None
def _init():
    global _E
    import warnings as w; w.filterwarnings("ignore"); _E = list(dnx.pegasus_graph(6).edges())
def _acl(e): return sum(len(c) for c in e.values())/len(e) if e else None
def _run(task):
    import minorminer
    from ember_qc_learn.decode import coords_to_qubit_scores, seed_chains_from_scores
    rec, meth = task; H = _graph(rec); sn = sorted(H.nodes()); n = rec["n"]
    def mm(seed, layout=None):
        kw = dict(random_seed=seed, timeout=25, verbose=0)
        if layout is not None:
            kw["initial_chains"] = seed_chains_from_scores(coords_to_qubit_scores(np.asarray(layout), QC), QN, sn)
        return _acl(minorminer.find_embedding(H, _E, **kw))
    lay = {"cold": None, "proc": rec["_proc"], "rl": rec["_rl"]}[meth.split("_")[0]]
    if meth.endswith("1"): return (rec["id"], meth, mm(0, lay))
    accs = [mm(i, lay) for i in range(8)]
    return (rec["id"], meth, min([a for a in accs if a] or [None]))

methods = ["cold_1","cold_8","proc_1","proc_8","rl_1","rl_8"]
tasks = [(r, m) for r in recs for m in methods]
out = []
with ProcessPoolExecutor(max_workers=28, initializer=_init) as ex:
    for r in ex.map(_run, tasks, chunksize=2): out.append(r)
perg = defaultdict(dict)
for gid, m, a in out:
    if a: perg[gid][m] = a
def mean(m): return st.mean([perg[g][m] for g in perg if m in perg[g]])
print(f"\n{'method':22s}{'mean ACL':>10s}")
for m in methods: print(f"{m:22s}{mean(m):>10.3f}")
def sig(a, b):
    pr = [(perg[g][a], perg[g][b]) for g in perg if a in perg[g] and b in perg[g]]
    w = sum(1 for x, y in pr if x < y-1e-9); l = sum(1 for x, y in pr if x > y+1e-9)
    try: p = wilcoxon([x-y for x, y in pr]).pvalue
    except Exception: p = float("nan")
    return len(pr), w, l, p
for a, b, lab in [("rl_1","proc_1","single: RL vs Procrustes"),("rl_1","cold_1","single: RL vs cold MM"),
                  ("rl_8","cold_8","best-of-8: RL vs cold MM"),("proc_1","cold_1","single: Procrustes vs cold MM")]:
    n, w, l, p = sig(a, b); print(f"{lab}: n={n} win={w} loss={l} p={p:.2e}")
