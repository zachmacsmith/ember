"""
Family: objective-GNN — amortized *differentiable embedding*, LABEL-FREE.

This is the §3.2 "differentiable embedding by annealed soft-assignment" bet, recast
as an amortized predictor. We reuse the proven ``gnn-seed`` coord-model architecture
(GNNBackbone -> sigmoid head -> per-vertex coords in [0,1]^2), but we do NOT fit the
Reweave chain-centroid labels (``batch.y``). Instead we train the GNN to MINIMISE
a pure *layout objective* computed from its own predicted coords ``P = model(batch)``
and the source ``edge_index`` — no embedding ground truth enters the loss:

    L = w_stretch * edge_stretch  +  w_spread * anti_collapse

  * edge_stretch  = mean over source edges of ||P[u]-P[v]||^2.
        Adjacent logical vertices -> nearby hardware coords -> when we seed->MM,
        neighbours land on nearby qubits -> short chains / satisfied couplers.
        Minimising this ALONE collapses every vertex to one point (ACL would blow
        up: many vertices fighting for one qubit), hence the second term.
  * anti_collapse = relu(target_spread - radius_of_gyration_g), per source graph,
        a one-sided floor on each graph's RMS distance-to-centroid. It stops the
        layout collapsing while letting edge_stretch compact it down to exactly
        the floor. ``batch.batch`` gives the per-node graph id for this per-graph
        term. ``target_spread`` is calibrated to the *measured* spread of the
        Reweave centroids (RoG ~0.07 on pegasus_6 — RW packs into a small corner
        of the fabric), so predicted layouts are RW-compact rather than scattered.
  * boundary is free: the sigmoid head already keeps coords in (0,1)^2.

The model is still *selected* on the real downstream metric (val ACL ratio vs RW
after seed->MM) inside ``train.train`` — only the gradient signal is label-free.

Decode reuses the shared seed->MM path (decode.decode_seed_path): predicted coords
-> proximity scores -> Hungarian distinct-qubit seeds -> minorminer.find_embedding
with initial_chains. Validity/repair is never re-implemented here.

Self-contained: defines its own training entry point and registers its own
``learned-obj`` adapter. Importing this module never hard-fails (torch is imported
lazily inside functions), so the package can wire it in best-effort.
"""
from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Dict, Optional

import networkx as nx

from ember_qc.registry import EmbeddingAlgorithm, register_algorithm

# Internal coord-model architecture reused for this family (identical to gnn-seed).
_MODEL_NAME = "gnn-seed"
# Checkpoint naming: <PREFIX>_<target>.pt  (e.g. obj_pegasus_6.pt).
_CKPT_PREFIX = "obj"

# --- loss hyperparameters (label-free layout objective) ----------------------
# target_spread is the desired per-graph radius of gyration of predicted coords.
# Calibrated to Reweave centroids on pegasus_6 (measured RoG ~0.066, mean
# pairwise dist ~0.086): RW packs the model into a compact corner of the fabric,
# so we want COMPACT predicted layouts (scattered seeds => long chains => high ACL).
DEFAULT_TARGET_SPREAD = 0.06
DEFAULT_W_STRETCH = 1.0
DEFAULT_W_SPREAD = 2.0


# ============================================================================ #
#  LABEL-FREE LAYOUT OBJECTIVE (the family's novelty)                          #
# ============================================================================ #

def _layout_objective(P, edge_index, batch_idx, *, target_spread: float,
                      w_stretch: float, w_spread: float, eps: float = 1e-9):
    """Core differentiable layout loss. Returns (loss, stretch, mean_rog).

    P:          [N, 2] predicted coords in [0,1]^2.
    edge_index: [2, 2E] bidirectional source edges (within-graph after PyG batching).
    batch_idx:  [N] per-node source-graph id (``batch.batch``), or None (one graph).
    """
    import torch
    from torch_geometric.utils import scatter

    # -- edge stretch: pull adjacent logical vertices together -----------------
    if edge_index is not None and edge_index.numel() and edge_index.size(1) > 0:
        d = P[edge_index[0]] - P[edge_index[1]]
        stretch = (d * d).sum(-1).mean()
    else:
        stretch = P.new_zeros(())

    # -- anti-collapse: per-graph radius-of-gyration floor ---------------------
    if batch_idx is None:
        batch_idx = torch.zeros(P.size(0), dtype=torch.long, device=P.device)
    n_graphs = int(batch_idx.max().item()) + 1 if batch_idx.numel() else 1
    mean_g = scatter(P, batch_idx, dim=0, dim_size=n_graphs, reduce="mean")  # [G,2]
    centered = P - mean_g[batch_idx]
    sq = (centered * centered).sum(-1)                                        # [N]
    var_g = scatter(sq, batch_idx, dim=0, dim_size=n_graphs, reduce="mean")  # [G]
    rog = torch.sqrt(var_g + eps)                                            # [G]
    spread_pen = torch.relu(target_spread - rog).mean()

    loss = w_stretch * stretch + w_spread * spread_pen
    return loss, stretch.detach(), rog.mean().detach()


def objective_loss(model, batch, geo, *, target_spread: float = DEFAULT_TARGET_SPREAD,
                   w_stretch: float = DEFAULT_W_STRETCH,
                   w_spread: float = DEFAULT_W_SPREAD):
    """train.train-compatible ``loss_fn(model, batch, geo) -> scalar``.

    LABEL-FREE: ``batch.y`` (RW centroids) is intentionally unused. The signal is
    entirely the layout objective on the model's own predicted coords.
    """
    P = model(batch)  # [N, 2]
    batch_idx = getattr(batch, "batch", None)
    loss, _stretch, _rog = _layout_objective(
        P, batch.edge_index, batch_idx,
        target_spread=target_spread, w_stretch=w_stretch, w_spread=w_spread)
    return loss


def make_loss_fn(*, target_spread: float = DEFAULT_TARGET_SPREAD,
                 w_stretch: float = DEFAULT_W_STRETCH,
                 w_spread: float = DEFAULT_W_SPREAD):
    """Bind the layout-objective hyperparameters into a ``loss_fn`` for train.train."""
    def _loss(model, batch, geo):
        return objective_loss(model, batch, geo, target_spread=target_spread,
                              w_stretch=w_stretch, w_spread=w_spread)
    return _loss


# ============================================================================ #
#  TRAINING ENTRY POINT                                                        #
# ============================================================================ #

def _repo_ckpt_dir() -> Path:
    env = os.environ.get("EMBER_LEARN_CKPT_DIR")
    if env:
        return Path(env)
    # …/packages/ember-qc-learn/src/ember_qc_learn/families/objective_gnn.py
    return Path(__file__).resolve().parents[5] / "ckpts"


def train_objective(data_dir: str, target: str = "pegasus_6",
                    out: Optional[str] = None, *, epochs: int = 60, lr: float = 2e-3,
                    batch_size: int = 16, hidden: int = 128, layers: int = 4,
                    conv: str = "sage", dropout: float = 0.1, device: str = "cpu",
                    target_spread: float = DEFAULT_TARGET_SPREAD,
                    w_stretch: float = DEFAULT_W_STRETCH,
                    w_spread: float = DEFAULT_W_SPREAD,
                    eval_every: int = 5, eval_subset: int = 24, seed: int = 0) -> Dict:
    """Train the objective-GNN (label-free) and write ``obj_<target>.pt``.

    Reuses the shared ``train.train`` harness with the ``gnn-seed`` architecture and
    our custom ``loss_fn`` (so model selection still uses the real val ACL ratio).
    """
    from ember_qc_learn.train import train

    if out is None:
        out = str(_repo_ckpt_dir() / f"{_CKPT_PREFIX}_{target}.pt")
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    loss_fn = make_loss_fn(target_spread=target_spread, w_stretch=w_stretch,
                           w_spread=w_spread)
    return train(_MODEL_NAME, data_dir, target, out, epochs=epochs, lr=lr,
                 batch_size=batch_size, hidden=hidden, layers=layers, conv=conv,
                 dropout=dropout, device=device, eval_every=eval_every,
                 eval_subset=eval_subset, seed=seed, loss_fn=loss_fn)


def _main() -> None:
    import argparse
    ap = argparse.ArgumentParser(description="Train the objective-GNN (label-free).")
    ap.add_argument("--data", default="data/learn")
    ap.add_argument("--target", default="pegasus_6")
    ap.add_argument("--out", default=None)
    ap.add_argument("--epochs", type=int, default=60)
    ap.add_argument("--lr", type=float, default=2e-3)
    ap.add_argument("--batch-size", type=int, default=16)
    ap.add_argument("--hidden", type=int, default=128)
    ap.add_argument("--layers", type=int, default=4)
    ap.add_argument("--conv", default="sage", choices=["sage", "gat", "gcn"])
    ap.add_argument("--device", default="cpu")
    ap.add_argument("--target-spread", type=float, default=DEFAULT_TARGET_SPREAD)
    ap.add_argument("--w-stretch", type=float, default=DEFAULT_W_STRETCH)
    ap.add_argument("--w-spread", type=float, default=DEFAULT_W_SPREAD)
    args = ap.parse_args()
    train_objective(args.data, args.target, args.out, epochs=args.epochs, lr=args.lr,
                    batch_size=args.batch_size, hidden=args.hidden, layers=args.layers,
                    conv=args.conv, device=args.device, target_spread=args.target_spread,
                    w_stretch=args.w_stretch, w_spread=args.w_spread)


# ============================================================================ #
#  REGISTRY ADAPTER  ->  "learned-obj"                                         #
# ============================================================================ #

def _ckpt_dir() -> Path:
    return _repo_ckpt_dir()


def _infer_target_name(G: nx.Graph) -> Optional[str]:
    from ember_qc_learn.features import _family
    return {"pegasus": "pegasus_6", "zephyr": "zephyr_4"}.get(_family(G))


@register_algorithm("learned-obj")
class LearnedObjective(EmbeddingAlgorithm):
    """objective-GNN: amortized label-free differentiable-layout embedder.

    Loads ``obj_<target>.pt``, predicts a per-vertex hardware layout, and decodes it
    via the shared seed->MM path. Skipped by the harness when torch/PyG or the
    checkpoint is missing; never hard-fails import.
    """
    _requires = ["torch", "torch_geometric"]

    def __init__(self):
        self._models: Dict[str, object] = {}   # target_name -> (model, blob) | None

    # -- availability ---------------------------------------------------------
    def _ckpt_path(self, target_name: str) -> Path:
        return _ckpt_dir() / f"{_CKPT_PREFIX}_{target_name}.pt"

    def is_available(self):
        try:
            import torch  # noqa: F401
            import torch_geometric  # noqa: F401
        except Exception:
            return (False, "needs torch + torch_geometric")
        for t in ("pegasus_6", "zephyr_4"):
            if self._ckpt_path(t).exists():
                return (True, "")
        return (False, f"no checkpoint {_CKPT_PREFIX}_*.pt in {_ckpt_dir()}")

    @property
    def version(self) -> str:
        return "0.1.0"

    # -- model loading --------------------------------------------------------
    def _load(self, target_name: str):
        if target_name in self._models:
            return self._models[target_name]
        import torch
        from ember_qc_learn.models.base import build_model
        import ember_qc_learn.models.gnn_seed  # noqa: F401  (registers gnn-seed)
        ck = self._ckpt_path(target_name)
        if not ck.exists():
            self._models[target_name] = None
            return None
        blob = torch.load(str(ck), map_location="cpu", weights_only=False)
        model = build_model(blob["model_name"], **blob["cfg"])
        model.load_state_dict(blob["state_dict"])
        model.eval()
        self._models[target_name] = (model, blob)
        return self._models[target_name]

    # -- embed ----------------------------------------------------------------
    def embed(self, source_graph: nx.Graph, target_graph: nx.Graph,
              timeout: float = 60.0, **kwargs) -> Dict:
        t0 = time.time()
        seed = int(kwargs.get("seed", 0))
        empty = {"embedding": {}, "time": 0.0, "success": False, "status": "FAILURE"}

        tname = _infer_target_name(target_graph)
        if tname is None:
            return {**empty, "time": time.time() - t0}
        loaded = self._load(tname)
        if loaded is None:
            return {**empty, "time": time.time() - t0}
        model, _blob = loaded

        import numpy as np
        import torch
        from torch_geometric.data import Data
        from ember_qc_learn.features import source_features, target_geometry
        from ember_qc_learn.decode import coords_to_qubit_scores, decode_seed_path

        # determinism
        torch.manual_seed(seed)
        np.random.seed(seed & 0xFFFFFFFF)

        sf = source_features(source_graph)
        if sf["n"] == 0:
            return {**empty, "time": time.time() - t0}
        geo = target_geometry(target_graph, tname)
        data = Data(x=torch.from_numpy(sf["x"]),
                    edge_index=torch.from_numpy(sf["edge_index"]))
        data.num_nodes = sf["n"]
        with torch.no_grad():
            coords = model(data).cpu().numpy().astype(np.float64)  # [n,2]

        snodes, qnodes = sf["nodes"], geo["qubit_nodes"]
        mm_timeout = min(float(timeout), 20.0)
        scores = coords_to_qubit_scores(coords, geo["coords"])     # [n,m]
        res = decode_seed_path(scores, source_graph, target_graph, qnodes, snodes,
                               seed=seed, timeout=mm_timeout)
        emb = res.get("embedding") or {}
        if not emb:
            return {**empty, "time": time.time() - t0}
        return {"embedding": emb, "time": time.time() - t0}


if __name__ == "__main__":
    _main()
