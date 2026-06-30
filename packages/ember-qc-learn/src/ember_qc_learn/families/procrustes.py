"""
Symmetry-invariant layout learning (the fix for the posterior collapse).

The naive supervised objective regresses each vertex's ABSOLUTE hardware
coordinate (its Reweave chain centroid). That target is ill-posed: a graph's
embedding can be placed anywhere on the fabric (translation + the fabric's
symmetries), so structure cannot predict absolute coordinates and the model
collapses to the constant global mean (flat loss). The fix is a **Procrustes /
similarity-invariant loss**: per graph, align the predicted layout to the target
up to rotation + reflection + scale + translation (closed-form, differentiable)
before the MSE, so the loss only sees the RELATIVE structure, which IS determined
by the graph. This produces a real, structure-aware layout (verified: non-zero
spread, adjacent vertices placed closer than non-adjacent).

At inference the (pose-free) layout is min-max normalized and placed compactly at
the fabric centre, then decoded via seed->minorminer. Registered as
``learned-procrustes`` (single-shot) and ``learned-procrustes-k8`` (best-of-8,
perturbed restarts).
"""
from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Dict, Optional

import networkx as nx

from ember_qc.registry import EmbeddingAlgorithm, register_algorithm

PLACEMENT_SCALE = 0.3   # compact placement fraction of the fabric (swept; 0.3 best)


# --------------------------------------------------------------------------- loss

def procrustes_loss(model, batch, geo):
    """Similarity-invariant layout loss (align pred->target per graph, then MSE)."""
    import torch
    P = model(batch); Y = batch.y; b = batch.batch
    losses = []
    for g in b.unique():
        m = b == g
        if int(m.sum()) < 3:
            continue
        p, y = P[m], Y[m]
        pc = p - p.mean(0, keepdim=True)
        yc = y - y.mean(0, keepdim=True)
        U, S, Vh = torch.linalg.svd(pc.t() @ yc)
        R = U @ Vh                                   # orthogonal (reflection allowed)
        s = S.sum() / ((pc ** 2).sum() + 1e-8)       # optimal scale
        losses.append(((s * (pc @ R) - yc) ** 2).mean())
    return torch.stack(losses).mean() if losses else P.sum() * 0


# --------------------------------------------------------------------- placement

def _place(P, scale=PLACEMENT_SCALE):
    """min-max normalize a pose-free layout, then place compactly at the centre."""
    import numpy as np
    lo, hi = P.min(0), P.max(0)
    span = np.where(hi - lo > 1e-6, hi - lo, 1.0)
    Pn = (P - lo) / span
    return Pn if scale == "fill" else 0.5 + (Pn - 0.5) * scale


# --------------------------------------------------------------------- training

def train_procrustes(data_dir: str, target: str = "pegasus_6",
                     out: Optional[str] = None, *, epochs: int = 90, lr: float = 2e-3,
                     batch_size: int = 32, hidden: int = 160, layers: int = 5,
                     conv: str = "sage", dropout: float = 0.1, device: str = "cpu",
                     eval_every: int = 15, eval_subset: int = 48, seed: int = 0) -> Dict:
    """Train the symmetry-invariant layout; select on val ACL via the compact-placement
    seed->MM decode (the real metric, not the loss). Writes a gnn-seed checkpoint
    tagged with the compact-placement inference recipe."""
    import numpy as np, torch
    import dwave_networkx as dnx
    from torch_geometric.loader import DataLoader
    from ember_qc_learn.dataset import EmbedDataset
    from ember_qc_learn.features import SOURCE_FEATURE_DIM, target_geometry
    from ember_qc_learn.models.base import build_model
    import ember_qc_learn.models.gnn_seed  # noqa
    from ember_qc_learn.decode import coords_to_qubit_scores, decode_seed_path

    torch.manual_seed(seed); np.random.seed(seed)
    dev = torch.device(device)
    tgt = {"pegasus_6": lambda: dnx.pegasus_graph(6),
           "zephyr_4": lambda: dnx.zephyr_graph(4)}[target]()
    geo = target_geometry(tgt, target)
    tr = EmbedDataset(os.path.join(data_dir, "train.jsonl"), target, geo=geo)
    va = EmbedDataset(os.path.join(data_dir, "val.jsonl"), target, geo=geo)
    cfg = dict(in_dim=SOURCE_FEATURE_DIM, hidden=hidden, layers=layers, conv=conv, dropout=dropout)
    model = build_model("gnn-seed", **cfg).to(dev)
    opt = torch.optim.Adam(model.parameters(), lr=lr, weight_decay=1e-5)
    sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, T_max=epochs)
    loader = tr.loader(batch_size=batch_size, shuffle=True)
    qc, qn = geo["coords"], geo["qubit_nodes"]

    def val_acl(n_eval):
        model.eval(); ratios = []
        for d, meta in list(zip(va.examples, va.meta))[:n_eval]:
            bt = next(iter(DataLoader([d], batch_size=1))).to(dev)
            with torch.no_grad():
                P = model(bt).cpu().numpy()
            H = nx.Graph(); H.add_nodes_from(range(meta["n"]))
            H.add_edges_from((u, v) for u, v in meta["edges"])
            sn = sorted(H.nodes())
            emb = decode_seed_path(coords_to_qubit_scores(_place(P), qc), H, tgt, qn, sn,
                                   seed=0, timeout=8)["embedding"]
            if emb:
                ratios.append((sum(len(c) for c in emb.values()) / len(emb)) / meta["acl"])
        return float(np.mean(ratios)) if ratios else float("inf")

    best = {"acl_ratio": float("inf")}
    for ep in range(1, epochs + 1):
        model.train()
        for bt in loader:
            bt = bt.to(dev); opt.zero_grad()
            loss = procrustes_loss(model, bt, geo); loss.backward(); opt.step()
        sched.step()
        if ep % eval_every == 0 or ep == epochs:
            r = val_acl(eval_subset)
            print(f"  ep{ep:3d} val_acl_ratio={r:.3f}", flush=True)
            if r < best["acl_ratio"]:
                best = {"acl_ratio": r, "epoch": ep}
                torch.save({"model_name": "gnn-seed", "cfg": cfg, "target": target,
                            "feature_dim": SOURCE_FEATURE_DIM, "state_dict": model.state_dict(),
                            "inference": {"placement": "compact", "scale": PLACEMENT_SCALE},
                            "metric": best}, out)
    if out and not os.path.exists(out):
        torch.save({"model_name": "gnn-seed", "cfg": cfg, "target": target,
                    "feature_dim": SOURCE_FEATURE_DIM, "state_dict": model.state_dict(),
                    "inference": {"placement": "compact", "scale": PLACEMENT_SCALE},
                    "metric": best}, out)
    print(f"[procrustes/{target}] best val ACL ratio={best['acl_ratio']:.3f} -> {out}", flush=True)
    return {"out": out, "best": best}


# --------------------------------------------------------------------- inference

def _ckpt_dir() -> Path:
    return Path(os.environ.get("EMBER_LEARN_CKPT_DIR",
                               str(Path(__file__).resolve().parents[4] / "ckpts")))


class _ProcrustesBase(EmbeddingAlgorithm):
    _requires = ["torch", "torch_geometric"]
    _k = 1

    def __init__(self):
        self._models = {}

    def _tname(self, G):
        from ember_qc_learn.features import _family
        return {"pegasus": "pegasus_6", "zephyr": "zephyr_4"}.get(_family(G))

    def is_available(self):
        try:
            import torch, torch_geometric  # noqa
        except Exception:
            return (False, "needs torch + torch_geometric")
        if any((_ckpt_dir() / f"procrustes_{t}.pt").exists() for t in ("pegasus_6", "zephyr_4")):
            return (True, "")
        return (False, f"no procrustes_*.pt in {_ckpt_dir()}")

    @property
    def version(self):
        return "0.1.0"

    def _load(self, tname):
        if tname in self._models:
            return self._models[tname]
        import torch
        from ember_qc_learn.models.base import build_model
        import ember_qc_learn.models.gnn_seed  # noqa
        ck = _ckpt_dir() / f"procrustes_{tname}.pt"
        if not ck.exists():
            self._models[tname] = None; return None
        blob = torch.load(str(ck), map_location="cpu", weights_only=False)
        m = build_model(blob["model_name"], **blob["cfg"]); m.load_state_dict(blob["state_dict"]); m.eval()
        self._models[tname] = (m, blob); return self._models[tname]

    def embed(self, source_graph, target_graph, timeout=60.0, **kwargs):
        t0 = time.time(); seed = int(kwargs.get("seed", 0))
        empty = {"embedding": {}, "time": 0.0, "success": False, "status": "FAILURE"}
        tname = self._tname(target_graph)
        if tname is None:
            return {**empty, "time": time.time() - t0}
        loaded = self._load(tname)
        if loaded is None:
            return {**empty, "time": time.time() - t0}
        model, blob = loaded
        import numpy as np, torch
        from torch_geometric.data import Data
        from ember_qc_learn.features import source_features, target_geometry
        from ember_qc_learn.decode import coords_to_qubit_scores, seed_chains_from_scores, run_minorminer
        sf = source_features(source_graph)
        if sf["n"] == 0:
            return {**empty, "time": time.time() - t0}
        geo = target_geometry(target_graph, tname)
        data = Data(x=torch.from_numpy(sf["x"]), edge_index=torch.from_numpy(sf["edge_index"]))
        data.num_nodes = sf["n"]
        with torch.no_grad():
            P = model(data).cpu().numpy().astype(np.float64)
        scale = blob.get("inference", {}).get("scale", PLACEMENT_SCALE)
        Pn = _place(P, scale)
        snodes, qnodes = sf["nodes"], geo["qubit_nodes"]
        mm_to = min(timeout, 20.0)
        best = None
        for i in range(self._k):
            L = Pn if i == 0 else Pn + np.random.default_rng(seed * 97 + i).normal(0, 0.04, Pn.shape)
            init = seed_chains_from_scores(coords_to_qubit_scores(L, geo["coords"]), qnodes, snodes)
            emb = run_minorminer(source_graph, target_graph, init, seed=seed + i, timeout=mm_to)
            if emb:
                acl = sum(len(c) for c in emb.values()) / len(emb)
                if best is None or acl < best[0]:
                    best = (acl, emb)
        if best is None:
            return {**empty, "time": time.time() - t0}
        return {"embedding": best[1], "time": time.time() - t0}


@register_algorithm("learned-procrustes")
class LearnedProcrustes(_ProcrustesBase):
    _k = 1


@register_algorithm("learned-procrustes-k8")
class LearnedProcrustesK8(_ProcrustesBase):
    _k = 8
