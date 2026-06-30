"""
Registry adapters: expose trained coord-models as ``learned-*`` algorithms so they
drop into ember_qc's benchmark_one head-to-head with RW/MM. Each adapter loads the
checkpoint matching the *passed* target (P6/Z4, incl. broken variants), predicts a
layout, and decodes (seed->MM or direct->repair). Unavailable (skipped by the
harness) when torch or the checkpoint is missing — never hard-fails import.

Checkpoints are looked up in $EMBER_LEARN_CKPT_DIR (default <repo>/ckpts), named
``<model_tag>_<target>.pt`` (e.g. gnn-seed_pegasus_6.pt).
"""
from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Dict, Optional

import networkx as nx

from ember_qc.registry import EmbeddingAlgorithm, register_algorithm

# (registry name, model_tag, decode_path) — workflow families append here.
_LEARNED_SPECS = [
    ("learned-gnn-seed", "gnn-seed", "seed"),
    ("learned-gnn-seed-direct", "gnn-seed", "direct"),
]


def _ckpt_dir() -> Path:
    env = os.environ.get("EMBER_LEARN_CKPT_DIR")
    if env:
        return Path(env)
    # repo-root/ckpts (…/packages/ember-qc-learn/src/ember_qc_learn/algorithms.py)
    return Path(__file__).resolve().parents[4] / "ckpts"


def _infer_target_name(G: nx.Graph) -> Optional[str]:
    from ember_qc_learn.features import _family
    fam = _family(G)
    return {"pegasus": "pegasus_6", "zephyr": "zephyr_4"}.get(fam)


class LearnedCoord(EmbeddingAlgorithm):
    """Adapter: load a coord-model checkpoint, predict a layout, decode to embedding."""
    _requires = ["torch", "torch_geometric"]

    def __init__(self, model_tag: str = "gnn-seed", path: str = "seed"):
        self.model_tag = model_tag
        self.path = path           # "seed" | "direct"
        self._models: Dict[str, object] = {}   # target_name -> (model, cfg)

    # -- availability ---------------------------------------------------------
    def _ckpt_path(self, target_name: str) -> Path:
        return _ckpt_dir() / f"{self.model_tag}_{target_name}.pt"

    def is_available(self):
        try:
            import torch  # noqa: F401
            import torch_geometric  # noqa: F401
        except Exception:
            return (False, "needs torch + torch_geometric")
        for t in ("pegasus_6", "zephyr_4"):
            if self._ckpt_path(t).exists():
                return (True, "")
        return (False, f"no checkpoint {self.model_tag}_*.pt in {_ckpt_dir()}")

    @property
    def version(self) -> str:
        return "0.1.0"

    # -- model loading --------------------------------------------------------
    def _load(self, target_name: str):
        if target_name in self._models:
            return self._models[target_name]
        import torch
        from ember_qc_learn.models.base import build_model
        import ember_qc_learn.models.gnn_seed  # noqa: F401  (register)
        try:
            import ember_qc_learn.models.gnn_direct  # noqa: F401
        except Exception:
            pass
        try:
            import ember_qc_learn.models.graph_vae  # noqa: F401
        except Exception:
            pass
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
        from ember_qc_learn.decode import (coords_to_qubit_scores, decode_seed_path,
                                           decode_direct_path)

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
        mm_timeout = min(timeout, 20.0)
        if self.path == "direct":
            d2 = ((geo["coords"][:, None, :] - coords[None, :, :]) ** 2).sum(-1)  # [m,n]
            S = np.exp(-d2 / 0.0008)
            res = decode_direct_path(S, source_graph, target_graph, qnodes, snodes,
                                     seed=seed, threshold=0.05, timeout=mm_timeout)
        else:
            scores = coords_to_qubit_scores(coords, geo["coords"])               # [n,m]
            res = decode_seed_path(scores, source_graph, target_graph, qnodes, snodes,
                                   seed=seed, timeout=mm_timeout)
        emb = res.get("embedding") or {}
        if not emb:
            return {**empty, "time": time.time() - t0}
        return {"embedding": emb, "time": time.time() - t0}


def _register_all() -> None:
    for name, tag, path in _LEARNED_SPECS:
        # bind tag/path via default args in a fresh subclass per name
        cls = type(
            f"Learned_{name.replace('-', '_')}",
            (LearnedCoord,),
            {"__init__": (lambda t, p: (lambda self: LearnedCoord.__init__(self, t, p)))(tag, path)},
        )
        register_algorithm(name)(cls)


_register_all()
