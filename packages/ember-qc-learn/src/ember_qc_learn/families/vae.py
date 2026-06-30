"""
Graph-VAE family (patent FIG 7) — registration + training + inference adapter.

This module is import-safe: it pulls in NO torch at module top, so
``import ember_qc_learn.families.vae`` never hard-fails. All torch-coupled work
(the GraphVAE model + VAELoss live in models/graph_vae.py) is imported lazily
inside ``train_vae`` and the adapter's methods.

Training (``train_vae``): reuses the shared train.train() loop, passing a custom
VAE loss (reconstruction MSE of the *reparameterized* decode against Reweave
chain centroids + KL) and ``extra_cfg={"latent_dim": ...}``. The model is still
*selected* on the real downstream metric (val ACL ratio after seed->MM decode),
and the self-describing checkpoint ``vae_<target>.pt`` reloads through build_model.

Inference (``@register_algorithm("learned-vae")``): encode the source once, then
sample K latents (the deterministic mu plus K-1 stochastic draws), decode each to
a layout, run seed->MM for each, and KEEP THE BEST ACL. This generative
multi-sample search is the point: more layouts -> better/lower-variance picks,
all legalized by the shared repair backend (decode.py never re-implements validity).
"""
from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Dict, Optional

import networkx as nx

from ember_qc.registry import EmbeddingAlgorithm, register_algorithm

MODEL_TAG = "vae"          # checkpoint file is <MODEL_TAG>_<target>.pt
MODEL_NAME = "graph-vae"   # MODEL_REGISTRY name (models/graph_vae.py)
DEFAULT_SAMPLES = 8


def _ckpt_dir() -> Path:
    env = os.environ.get("EMBER_LEARN_CKPT_DIR")
    if env:
        return Path(env)
    # families/vae.py -> ember_qc_learn -> src -> ember-qc-learn -> packages -> <repo>
    return Path(__file__).resolve().parents[5] / "ckpts"


def _ckpt_path(target_name: str) -> Path:
    return _ckpt_dir() / f"{MODEL_TAG}_{target_name}.pt"


def _infer_target_name(G: nx.Graph) -> Optional[str]:
    from ember_qc_learn.features import _family
    return {"pegasus": "pegasus_6", "zephyr": "zephyr_4"}.get(_family(G))


# --------------------------------------------------------------------------- train

def train_vae(data_dir: str, target: str = "pegasus_6", out: Optional[str] = None, *,
              epochs: int = 60, lr: float = 2e-3, batch_size: int = 16,
              hidden: int = 128, layers: int = 4, conv: str = "sage",
              dropout: float = 0.1, latent_dim: int = 16, beta: float = 0.01,
              warmup_steps: int = 200, device: str = "cpu", eval_every: int = 5,
              eval_subset: int = 24, seed: int = 0) -> Dict:
    """Train the Graph-VAE on RW-labeled data and write ``vae_<target>.pt``.

    Reuses ember_qc_learn.train.train() with the custom VAELoss so selection
    still happens on real val ACL ratio (seed->MM decode), and the checkpoint is
    in the standard self-describing format. Returns {'out', 'best'}.
    """
    import ember_qc_learn.models.graph_vae as gv  # registers "graph-vae" + VAELoss
    from ember_qc_learn.train import train as _train

    if out is None:
        out = str(_ckpt_dir() / f"{MODEL_TAG}_{target}.pt")
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    loss = gv.VAELoss(beta=beta, warmup_steps=warmup_steps)
    return _train(MODEL_NAME, data_dir, target, out, epochs=epochs, lr=lr,
                  batch_size=batch_size, hidden=hidden, layers=layers, conv=conv,
                  dropout=dropout, device=device, eval_every=eval_every,
                  eval_subset=eval_subset, seed=seed, loss_fn=loss,
                  extra_cfg={"latent_dim": latent_dim})


# ----------------------------------------------------------------------- inference

@register_algorithm("learned-vae")
class LearnedVAE(EmbeddingAlgorithm):
    """Generative Graph-VAE embedder: sample K layouts, decode each via seed->MM,
    keep the best (lowest-ACL) valid embedding. Skipped by the harness unless
    torch + torch_geometric + a vae_<target>.pt checkpoint are present."""

    _requires = ["torch", "torch_geometric"]

    def __init__(self):
        self.model_tag = MODEL_TAG
        self.K = DEFAULT_SAMPLES
        self._models: Dict[str, object] = {}   # target_name -> model | None

    # -- availability ---------------------------------------------------------
    def is_available(self):
        try:
            import torch  # noqa: F401
            import torch_geometric  # noqa: F401
        except Exception:
            return (False, "needs torch + torch_geometric")
        for t in ("pegasus_6", "zephyr_4"):
            if _ckpt_path(t).exists():
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
        import ember_qc_learn.models.graph_vae  # noqa: F401  (registers "graph-vae")
        ck = _ckpt_path(target_name)
        if not ck.exists():
            self._models[target_name] = None
            return None
        blob = torch.load(str(ck), map_location="cpu", weights_only=False)
        model = build_model(blob["model_name"], **blob["cfg"])
        model.load_state_dict(blob["state_dict"])
        model.eval()
        self._models[target_name] = model
        return model

    # -- embed ----------------------------------------------------------------
    def embed(self, source_graph: nx.Graph, target_graph: nx.Graph,
              timeout: float = 60.0, **kwargs) -> Dict:
        t0 = time.time()
        seed = int(kwargs.get("seed", 0))
        K = max(1, int(kwargs.get("vae_samples", self.K)))
        empty = {"embedding": {}, "time": 0.0, "success": False, "status": "FAILURE"}

        tname = _infer_target_name(target_graph)
        if tname is None:
            return {**empty, "time": time.time() - t0}
        model = self._load(tname)
        if model is None:
            return {**empty, "time": time.time() - t0}

        import numpy as np
        import torch
        from torch_geometric.data import Data

        from ember_qc_learn.decode import coords_to_qubit_scores, decode_seed_path
        from ember_qc_learn.features import source_features, target_geometry

        sf = source_features(source_graph)
        if sf["n"] == 0:
            return {**empty, "time": time.time() - t0}
        geo = target_geometry(target_graph, tname)
        snodes, qnodes, qcoords = sf["nodes"], geo["qubit_nodes"], geo["coords"]

        data = Data(x=torch.from_numpy(sf["x"]),
                    edge_index=torch.from_numpy(sf["edge_index"]))
        data.num_nodes = sf["n"]

        # determinism: seed both torch and the per-sample latent generator
        torch.manual_seed(seed)
        np.random.seed(seed & 0xFFFFFFFF)
        gen = torch.Generator().manual_seed((seed * 1000003 + 7) & 0x7FFFFFFF)

        mm_cap = max(1.0, min(float(timeout), 20.0))
        budget = max(float(timeout) - 1.0, 1.0)   # keep total within `timeout`
        deadline = t0 + budget

        best_acl = float("inf")
        best_emb: Dict[int, list] = {}
        n_tried = 0
        with torch.no_grad():
            h, b, mu, logvar = model.encode(data)
            std = torch.exp(0.5 * logvar)
            # candidate latents: deterministic mu first, then K-1 stochastic draws
            latents = [mu]
            for _ in range(K - 1):
                eps = torch.randn(mu.shape, generator=gen, dtype=mu.dtype)
                latents.append(mu + std * eps)

            for i, z in enumerate(latents):
                remaining = deadline - time.time()
                if remaining <= 0 and best_emb:
                    break
                n_left = len(latents) - i
                per_to = max(0.5, min(mm_cap, remaining / n_left)) if n_left > 0 else mm_cap
                coords = model.decode_coords(h, b, z).cpu().numpy().astype(np.float64)
                scores = coords_to_qubit_scores(coords, qcoords)
                res = decode_seed_path(scores, source_graph, target_graph, qnodes,
                                       snodes, seed=seed + i, timeout=per_to)
                emb = res.get("embedding") or {}
                n_tried += 1
                if not emb:
                    continue
                acl = sum(len(c) for c in emb.values()) / len(emb)
                if acl < best_acl:
                    best_acl, best_emb = acl, emb

        if not best_emb:
            return {**empty, "time": time.time() - t0}
        return {"embedding": best_emb, "time": time.time() - t0,
                "success": True, "status": "SUCCESS",
                "metadata": {"vae_samples": n_tried, "best_acl": best_acl}}
