"""Fix #1: symmetry-invariant (Procrustes) layout loss. The collapse came from
regressing ABSOLUTE coords (placement is arbitrary up to similarity transform).
Align prediction to target up to rotation+reflection+scale+translation before MSE
-> the loss only sees RELATIVE structure, which IS determined by the graph."""
import warnings; warnings.filterwarnings("ignore")
import numpy as np, torch, networkx as nx, dwave_networkx as dnx
from torch_geometric.loader import DataLoader
from ember_qc_learn.dataset import EmbedDataset
from ember_qc_learn.features import target_geometry, SOURCE_FEATURE_DIM
from ember_qc_learn.models.base import build_model
import ember_qc_learn.models.gnn_seed  # noqa

def procrustes_loss_graph(p, y):
    pc = p - p.mean(0, keepdim=True); yc = y - y.mean(0, keepdim=True)
    M = pc.t() @ yc
    U, S, Vh = torch.linalg.svd(M)
    R = U @ Vh                                  # orthogonal (reflection allowed)
    s = S.sum() / ((pc**2).sum() + 1e-8)        # optimal scale
    return ((s * (pc @ R) - yc) ** 2).mean()

def procrustes_loss(model, batch, geo):
    P = model(batch); Y = batch.y; b = batch.batch
    ls = [procrustes_loss_graph(P[b == g], Y[b == g])
          for g in b.unique() if (b == g).sum() >= 3]
    return torch.stack(ls).mean() if ls else (P.sum() * 0)

# --- unit test: a similarity transform of Y should align to ~0 loss ---
torch.manual_seed(0)
Y = torch.rand(20, 2)
th = 0.7; Rm = torch.tensor([[np.cos(th), -np.sin(th)], [np.sin(th), np.cos(th)]]).float()
Ptransf = 2.3 * (Y @ Rm.t()) + torch.tensor([0.4, -0.2])     # rotate+scale+translate
print(f"[unit] loss(similarity-transform of Y, Y) = {procrustes_loss_graph(Ptransf, Y):.2e} (want ~0)")
print(f"[unit] loss(random, Y)                    = {procrustes_loss_graph(torch.rand(20,2), Y):.4f} (want >0)")

# --- quick train on a subset, check it does NOT collapse ---
geo = target_geometry(dnx.pegasus_graph(6), "pegasus_6")
tr = EmbedDataset("data/learn/train.jsonl", "pegasus_6", geo=geo)
va = EmbedDataset("data/learn/val.jsonl", "pegasus_6", geo=geo)
sub = tr.examples[:500]
model = build_model("gnn-seed", in_dim=SOURCE_FEATURE_DIM, hidden=128, layers=4, conv="sage", dropout=0.1)
opt = torch.optim.Adam(model.parameters(), lr=2e-3, weight_decay=1e-5)
loader = DataLoader(sub, batch_size=16, shuffle=True)
for ep in range(1, 41):
    model.train(); tot = 0
    for bt in loader:
        opt.zero_grad(); l = procrustes_loss(model, bt, geo); l.backward(); opt.step(); tot += l.item()
    if ep % 10 == 0:
        # collapse check on val
        model.eval(); spreads, gaps = [], []
        for d, meta in list(zip(va.examples, va.meta))[:40]:
            bt = next(iter(DataLoader([d], batch_size=1)))
            with torch.no_grad(): P = model(bt).numpy()
            spreads.append(P.std(0).mean())
            H = nx.Graph(); H.add_nodes_from(range(meta["n"])); H.add_edges_from((u,v) for u,v in meta["edges"])
            D = np.sqrt(((P[:,None,:]-P[None,:,:])**2).sum(-1))
            ed = [D[u,v] for u,v in H.edges()]; non = [D[i,j] for i in range(meta["n"]) for j in range(i+1,meta["n"]) if not H.has_edge(i,j)]
            if ed and non: gaps.append(np.mean(non)-np.mean(ed))
        print(f"  ep{ep:2d} loss={tot/len(loader):.4f} pred-spread={np.mean(spreads):.4f} edge-gap={np.mean(gaps):+.4f}")
print("=> spread>0 and edge-gap>0 means NO collapse + structure-aware (the fix worked)")
