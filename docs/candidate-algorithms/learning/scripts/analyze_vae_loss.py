"""Why is the VAE loss flat? Decompose: is the model beating 'predict the mean',
or is the absolute-coordinate target ill-posed (irreducible floor)?"""
import warnings; warnings.filterwarnings("ignore")
import numpy as np, torch
import dwave_networkx as dnx
from torch_geometric.loader import DataLoader
from ember_qc_learn.dataset import EmbedDataset
from ember_qc_learn.features import target_geometry
from ember_qc_learn.models.base import build_model
import ember_qc_learn.models.graph_vae as gv  # noqa

geo = target_geometry(dnx.pegasus_graph(6), "pegasus_6")
tr = EmbedDataset("data/learn/train.jsonl", "pegasus_6", geo=geo)
va = EmbedDataset("data/learn/val.jsonl", "pegasus_6", geo=geo)
print(f"train graphs={len(tr)} val={len(va)}")

# ---- target distribution + null models ----
ys = [d.y.numpy() for d in tr.examples]
Y = np.concatenate(ys, 0)
print(f"\nTARGET centroids: global mean={Y.mean(0).round(3)} std={Y.std(0).round(3)} "
      f"range=[{Y.min(0).round(2)},{Y.max(0).round(2)}]")
gmean = Y.mean(0)
mse_global = ((Y - gmean) ** 2).mean()
mse_pergraph = np.mean([((y - y.mean(0)) ** 2).mean() for y in ys])  # predict each graph's own mean
print(f"\nNULL-MODEL MSE (the 'loss floor' a dumb predictor reaches):")
print(f"  predict GLOBAL mean for every vertex : {mse_global:.4f}")
print(f"  predict PER-GRAPH mean for every vtx : {mse_pergraph:.4f}  (= within-graph residual)")

# ---- trained VAE ----
ck = torch.load("ckpts/vae_pegasus_6.pt", map_location="cpu", weights_only=False)
print(f"\nloaded ckpt cfg: {ck['cfg']}  (hidden tells us smoke vs real)")
model = build_model(ck["model_name"], **ck["cfg"]); model.load_state_dict(ck["state_dict"]); model.eval()

def vae_mse(ds):
    P, T = [], []
    for d in ds.examples:
        b = next(iter(DataLoader([d], batch_size=1)))
        with torch.no_grad():
            P.append(model(b).numpy())
        T.append(d.y.numpy())
    P = np.concatenate(P, 0); T = np.concatenate(T, 0)
    return ((P - T) ** 2).mean(), P, T

mse_tr, P, T = vae_mse(tr)
mse_va, _, _ = vae_mse(va)
print(f"\nTRAINED VAE (z=mu) recon MSE: train={mse_tr:.4f}  val={mse_va:.4f}")
print(f"  -> beats global-mean by {(mse_global-mse_tr)/mse_global*100:.1f}% ; "
      f"beats per-graph-mean by {(mse_pergraph-mse_tr)/mse_pergraph*100:.1f}%")

# does the model collapse predictions to ~constant, or vary per vertex?
pred_spread = np.mean([P[s:s+len(ys[i])].std(0).mean()
                       for i, s in zip(range(len(ys)), np.cumsum([0]+[len(y) for y in ys[:-1]]))])
print(f"\nper-graph prediction coord-std: {pred_spread:.4f}  vs target coord-std: "
      f"{np.mean([y.std(0).mean() for y in ys]):.4f}")
print(f"VAE prediction GLOBAL std: {P.std(0).round(3)}  (target {T.std(0).round(3)})")
print("\nINTERPRETATION:")
print(" - if VAE MSE ~= per-graph-mean MSE -> model learned the graph's CENTER but not")
print("   per-vertex placement (absolute placement is symmetry-ambiguous -> ill-posed).")
print(" - if VAE pred-std << target-std -> predictions partially collapsed to the mean.")
