"""
Training harness for coord-models. Loss = MSE to Reweave chain centroids (the
learned-layout target); the model is *selected* on the real downstream metric —
val ACL ratio vs RW after seed->MM decode — not on MSE. Checkpoints are
self-describing so algorithms.py can reload for benchmarking.

CLI:
  python -m ember_qc_learn.train --model gnn-seed --data data/learn \
      --target pegasus_6 --out ckpts/gnn-seed_p6.pt --epochs 60 --device cuda
"""
from __future__ import annotations

import argparse
import json
import os
import time
from typing import Callable, Dict, Optional

import networkx as nx
import numpy as np
import torch
import torch.nn.functional as F

from ember_qc_learn.dataset import EmbedDataset
from ember_qc_learn.decode import coords_to_qubit_scores, decode_seed_path
from ember_qc_learn.features import SOURCE_FEATURE_DIM, target_geometry
from ember_qc_learn.models.base import build_model
import ember_qc_learn.models.gnn_seed  # noqa: F401  (registers gnn-seed)


def _build_target(target_name: str):
    import dwave_networkx as dnx
    return {"pegasus_6": lambda: dnx.pegasus_graph(6),
            "zephyr_4": lambda: dnx.zephyr_graph(4)}[target_name]()


def mse_coord_loss(model, batch, geo) -> torch.Tensor:
    """Default learned-layout loss: MSE(pred coords, RW centroid coords)."""
    pred = model(batch)
    return F.mse_loss(pred, batch.y)


@torch.no_grad()
def eval_acl(model, ds: EmbedDataset, target_graph, *, n_eval: int,
             device, timeout: float = 8.0) -> Dict:
    """Real metric: predict coords -> seed->MM -> ACL ratio vs RW, over a subset."""
    from torch_geometric.loader import DataLoader
    model.eval()
    geo = ds.geo
    qcoords, qnodes = geo["coords"], geo["qubit_nodes"]
    exs = list(zip(ds.examples[:n_eval], ds.meta[:n_eval]))
    if not exs:
        return {"valid_frac": 0.0, "acl_ratio": float("inf")}
    ratios, valid = [], 0
    for d, meta in exs:
        batch = next(iter(DataLoader([d], batch_size=1))).to(device)
        coords = model(batch).cpu().numpy()
        H = nx.Graph(); H.add_nodes_from(range(meta["n"]))
        H.add_edges_from((int(u), int(v)) for u, v in meta["edges"])
        snodes = sorted(H.nodes())
        scores = coords_to_qubit_scores(coords, qcoords)
        emb = decode_seed_path(scores, H, target_graph, qnodes, snodes,
                               seed=0, timeout=timeout)["embedding"]
        if emb:
            valid += 1
            ratios.append((sum(len(c) for c in emb.values()) / len(emb)) / meta["acl"])
    return {"valid_frac": valid / len(exs),
            "acl_ratio": float(np.mean(ratios)) if ratios else float("inf")}


def train(model_name: str, data_dir: str, target: str, out: str, *,
          epochs: int = 60, lr: float = 2e-3, batch_size: int = 16,
          hidden: int = 128, layers: int = 4, conv: str = "sage", dropout: float = 0.1,
          device: str = "cpu", eval_every: int = 5, eval_subset: int = 24,
          eval_timeout: float = 8.0, seed: int = 0,
          loss_fn: Optional[Callable] = None, extra_cfg: Optional[Dict] = None) -> Dict:
    torch.manual_seed(seed); np.random.seed(seed)
    dev = torch.device(device)
    tgt_graph = _build_target(target)
    geo = target_geometry(tgt_graph, target)
    tr = EmbedDataset(os.path.join(data_dir, "train.jsonl"), target, geo=geo)
    va = EmbedDataset(os.path.join(data_dir, "val.jsonl"), target, geo=geo)
    print(f"[{model_name}/{target}] train={len(tr)} val={len(va)} feat_dim={SOURCE_FEATURE_DIM} dev={dev}", flush=True)
    if len(tr) == 0:
        raise SystemExit("empty training set")

    cfg = dict(in_dim=SOURCE_FEATURE_DIM, hidden=hidden, layers=layers,
               conv=conv, dropout=dropout, **(extra_cfg or {}))
    model = build_model(model_name, **cfg).to(dev)
    opt = torch.optim.Adam(model.parameters(), lr=lr, weight_decay=1e-5)
    sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, T_max=epochs)
    loss_fn = loss_fn or mse_coord_loss

    best = {"acl_ratio": float("inf")}
    history = []
    loader = tr.loader(batch_size=batch_size, shuffle=True)
    for ep in range(1, epochs + 1):
        model.train(); tot = 0.0
        for batch in loader:
            batch = batch.to(dev)
            opt.zero_grad()
            loss = loss_fn(model, batch, geo)
            loss.backward(); opt.step()
            tot += loss.item() * batch.num_graphs
        sched.step()
        train_loss = tot / max(len(tr), 1)
        rec = {"epoch": ep, "train_loss": train_loss}
        if ep % eval_every == 0 or ep == epochs:
            m = eval_acl(model, va, tgt_graph, n_eval=eval_subset, device=dev, timeout=eval_timeout)
            rec.update(m)
            improved = m["acl_ratio"] < best["acl_ratio"]
            print(f"  ep{ep:3d} loss={train_loss:.4f} val_acl_ratio={m['acl_ratio']:.3f} "
                  f"valid={m['valid_frac']:.2f}{' *' if improved else ''}", flush=True)
            if improved:
                best = {**m, "epoch": ep}
                torch.save({"model_name": model_name, "cfg": cfg, "target": target,
                            "feature_dim": SOURCE_FEATURE_DIM,
                            "state_dict": model.state_dict(), "metric": best},
                           out)
        history.append(rec)
    # always keep a final checkpoint if none beat inf
    if not os.path.exists(out):
        torch.save({"model_name": model_name, "cfg": cfg, "target": target,
                    "feature_dim": SOURCE_FEATURE_DIM,
                    "state_dict": model.state_dict(), "metric": best}, out)
    with open(out + ".history.json", "w") as f:
        json.dump({"model_name": model_name, "target": target, "best": best,
                   "history": history}, f, indent=2)
    print(f"[{model_name}/{target}] best val ACL ratio={best['acl_ratio']:.3f} "
          f"@ep{best.get('epoch')} -> {out}", flush=True)
    return {"out": out, "best": best}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="gnn-seed")
    ap.add_argument("--data", default="data/learn")
    ap.add_argument("--target", default="pegasus_6")
    ap.add_argument("--out", required=True)
    ap.add_argument("--epochs", type=int, default=60)
    ap.add_argument("--lr", type=float, default=2e-3)
    ap.add_argument("--batch-size", type=int, default=16)
    ap.add_argument("--hidden", type=int, default=128)
    ap.add_argument("--layers", type=int, default=4)
    ap.add_argument("--conv", default="sage", choices=["sage", "gat", "gcn"])
    ap.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    ap.add_argument("--eval-every", type=int, default=5)
    ap.add_argument("--eval-subset", type=int, default=24)
    args = ap.parse_args()
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    train(args.model, args.data, args.target, args.out, epochs=args.epochs, lr=args.lr,
          batch_size=args.batch_size, hidden=args.hidden, layers=args.layers,
          conv=args.conv, device=args.device, eval_every=args.eval_every,
          eval_subset=args.eval_subset)


if __name__ == "__main__":
    main()
