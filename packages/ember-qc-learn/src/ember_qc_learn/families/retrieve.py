"""
Retrieval / embeddings-cache family (patent FIG 2/5/6) — a NON-neural baseline
that learning is meant to beat.

"Training" = build an INDEX over the Reweave-labelled training graphs. Per graph
we store: a fixed graph-level descriptor (degree / clustering / core moments +
spectral moments), the per-vertex structural features (degree, clustering, core),
and the RW embedding (chains) for each target.

Inference (no neural net):
  1. Featurize the query graph.
  2. Retrieve the nearest indexed graph — PREFER an exact node-count (n) match;
     among those, nearest by sorted per-vertex structural features; else fall back
     to the nearest standardized graph descriptor over the whole index.
  3. REMAP the retrieved graph's vertices onto the query's by aligning BOTH vertex
     sets in sorted (degree, clustering, core) order, producing initial_chains =
     retrieved RW chains under that alignment. Qubits absent from a (broken) target
     are dropped; minorminer grows/repairs the rest.
  4. Decode via ``decode.run_minorminer(query, target, initial_chains, seed, timeout)``
     (warm start); cold-MM fallback guarantees we never report an invalid embedding.

Reuses decode.run_minorminer + the shared repair backend — no validity / MM logic is
reimplemented here. Non-neural: numpy + networkx + minorminer only (no torch, no GPU).

Build the index (the train recipe):
  python -m ember_qc_learn.families.retrieve --data data/learn --out ckpts
writes ckpts/retrieve_pegasus_6.pt and ckpts/retrieve_zephyr_4.pt (one per target
that appears in train.jsonl labels). The ``learned-retrieve`` adapter loads the index
matching the passed target.
"""
from __future__ import annotations

import argparse
import json
import os
import pickle
import random
import time
from pathlib import Path
from typing import Dict, List, Optional

import networkx as nx
import numpy as np

from ember_qc.registry import EmbeddingAlgorithm, register_algorithm

INDEX_VERSION = 2
_DEFAULT_TARGETS = ("pegasus_6", "zephyr_4")


# =============================================================================
# Featurization (pure numpy / networkx — shared by index build and inference)
# =============================================================================

def _vertex_features(H: nx.Graph, nodes: List[int]) -> np.ndarray:
    """[n, 3] per-vertex structural features (degree, clustering, core), rows
    aligned to ``nodes``."""
    n = len(nodes)
    out = np.zeros((n, 3), dtype=np.float64)
    if n == 0:
        return out
    deg = dict(H.degree())
    clus = nx.clustering(H)
    try:
        core = nx.core_number(H)
    except Exception:
        core = {u: 0 for u in nodes}
    for i, u in enumerate(nodes):
        out[i] = (deg.get(u, 0), clus.get(u, 0.0), core.get(u, 0))
    return out


def _lex_order(vfeat: np.ndarray) -> np.ndarray:
    """Indices that sort the vertices by (degree, clustering, core) — primary key
    degree. Deterministic (numpy stable lexsort)."""
    if vfeat.shape[0] == 0:
        return np.zeros(0, dtype=np.int64)
    return np.lexsort((vfeat[:, 2], vfeat[:, 1], vfeat[:, 0]))


def _norm_vfeat(vfeat: np.ndarray, n: int) -> np.ndarray:
    """Scale columns to comparable ranges so degree does not dominate the L2 over
    sorted features: degree/(n-1), clustering as-is, core/(n-1)."""
    dn = max(n - 1, 1)
    out = vfeat.copy()
    out[:, 0] /= dn
    out[:, 2] /= dn
    return out


def _sorted_feature_vec(vfeat: np.ndarray, n: int) -> np.ndarray:
    """Length-3n vector: per-column independently sorted, normalized features. Two
    same-n graphs are compared by L2 over this vector (the 'sorted structural-feature
    order')."""
    nv = _norm_vfeat(vfeat, n)
    return np.concatenate([np.sort(nv[:, 0]), np.sort(nv[:, 1]), np.sort(nv[:, 2])])


def _spectral(H: nx.Graph, nodes: List[int]) -> np.ndarray:
    """Sorted eigenvalues of the normalized Laplacian (length n), or empty on error."""
    try:
        L = nx.normalized_laplacian_matrix(H, nodelist=nodes).toarray()
        w = np.linalg.eigvalsh(0.5 * (L + L.T))
        return np.sort(w)
    except Exception:
        return np.zeros(0)


def _graph_descriptor(H: nx.Graph, vfeat: np.ndarray, nodes: List[int]) -> np.ndarray:
    """Fixed-length (17) scalar graph descriptor for cross-n nearest-neighbor."""
    n = len(nodes)
    m = H.number_of_edges()
    dn = max(n - 1, 1)
    deg, clus, core = vfeat[:, 0], vfeat[:, 1], vfeat[:, 2]
    density = (2.0 * m) / (n * (n - 1)) if n > 1 else 0.0
    feats = [
        float(n), float(m), float(density),
        float(deg.mean() / dn), float(deg.std() / dn),
        float(deg.max() / dn), float(deg.min() / dn),
        float(clus.mean()), float(clus.std()),
        float(core.mean() / dn), float(core.max() / dn),
    ]
    try:
        trans = float(nx.transitivity(H))
    except Exception:
        trans = 0.0
    try:
        ass = float(nx.degree_assortativity_coefficient(H))
        if not np.isfinite(ass):
            ass = 0.0
    except Exception:
        ass = 0.0
    feats += [trans, ass]
    w = _spectral(H, nodes)
    if w.size >= 2:
        feats += [float(w.mean()), float(w.std()), float(w.max()), float(w[1])]
    else:
        feats += [0.0, 0.0, 0.0, 0.0]
    return np.array(feats, dtype=np.float64)


# =============================================================================
# Index build ("training") — reads data_dir/train.jsonl, writes ckpts/retrieve_<target>.pt
# =============================================================================

def _record_to_graph(rec: Dict) -> nx.Graph:
    H = nx.Graph()
    H.add_nodes_from(range(rec["n"]))
    H.add_edges_from((int(u), int(v)) for u, v in rec["edges"])
    return H


def build_index(data_dir: str, target: str, out_dir: str) -> Optional[str]:
    """Build + persist the retrieval index for one target. Returns the written path,
    or None if no labelled graphs exist for this target."""
    path = os.path.join(data_dir, "train.jsonl")
    if not os.path.exists(path):
        raise FileNotFoundError(f"no train.jsonl in {data_dir}")
    entries: List[Dict] = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            lab = rec.get("labels", {}).get(target)
            if not lab or "embedding" not in lab:
                continue
            H = _record_to_graph(rec)
            nodes = sorted(H.nodes())
            vfeat = _vertex_features(H, nodes)
            emb = {int(k): [int(q) for q in v] for k, v in lab["embedding"].items()}
            entries.append({
                "id": rec.get("id"),
                "n": int(rec["n"]),
                "nodes": nodes,
                "vfeat": vfeat.astype(np.float32),
                "sfvec": _sorted_feature_vec(vfeat, rec["n"]).astype(np.float32),
                "gdesc": _graph_descriptor(H, vfeat, nodes).astype(np.float32),
                "embedding": emb,
                "acl": float(lab.get("acl", 0.0)),
            })
    if not entries:
        return None
    G = np.stack([e["gdesc"] for e in entries]).astype(np.float64)
    mu = G.mean(0)
    sd = G.std(0)
    sd[sd < 1e-6] = 1.0
    index = {
        "target": target,
        "version": INDEX_VERSION,
        "entries": entries,
        "gdesc_mean": mu.astype(np.float32),
        "gdesc_std": sd.astype(np.float32),
        "desc_dim": int(G.shape[1]),
        "n_entries": len(entries),
    }
    os.makedirs(out_dir, exist_ok=True)
    out = os.path.join(out_dir, f"retrieve_{target}.pt")
    with open(out, "wb") as f:
        pickle.dump(index, f, protocol=pickle.HIGHEST_PROTOCOL)
    return out


def _targets_in_data(data_dir: str) -> List[str]:
    """Distinct targets that have at least one valid label in train.jsonl."""
    path = os.path.join(data_dir, "train.jsonl")
    seen: List[str] = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            for t, lab in json.loads(line).get("labels", {}).items():
                if "embedding" in lab and t not in seen:
                    seen.append(t)
    return seen


def train(data_dir: str = "data/learn", out_dir: str = "ckpts",
          targets: Optional[List[str]] = None) -> List[str]:
    """Build the retrieval index for every requested target (the train recipe).
    Returns the list of written checkpoint paths."""
    if targets is None:
        targets = _targets_in_data(data_dir) or list(_DEFAULT_TARGETS)
    written = []
    for t in targets:
        out = build_index(data_dir, t, out_dir)
        if out:
            written.append(out)
            print(f"[retrieve/{t}] wrote {out}", flush=True)
        else:
            print(f"[retrieve/{t}] no labelled graphs — skipped", flush=True)
    return written


def main() -> None:
    ap = argparse.ArgumentParser(description="Build the learned-retrieve index.")
    ap.add_argument("--data", default="data/learn")
    ap.add_argument("--out", default="ckpts")
    ap.add_argument("--targets", nargs="*", default=None,
                    help="targets to index; default = those present in train.jsonl")
    args = ap.parse_args()
    train(args.data, args.out, args.targets)


# =============================================================================
# Retrieval + remap (inference helpers)
# =============================================================================

def _retrieve_nearest(index: Dict, n_q: int, vfeat_q: np.ndarray,
                      gdesc_q: np.ndarray) -> Optional[Dict]:
    """Nearest indexed graph: exact-n bucket by sorted-feature L2, else whole index
    by standardized descriptor L2."""
    entries = index["entries"]
    if not entries:
        return None
    same_n = [e for e in entries if e["n"] == n_q]
    if same_n:
        key_q = _sorted_feature_vec(vfeat_q, n_q).astype(np.float32)
        best = min(same_n, key=lambda e: float(np.sum((e["sfvec"] - key_q) ** 2)))
        return {**best, "_match": "exact_n"}
    mu = np.asarray(index["gdesc_mean"], dtype=np.float64)
    sd = np.asarray(index["gdesc_std"], dtype=np.float64)
    zq = (gdesc_q - mu) / sd
    best = min(entries, key=lambda e: float(
        np.sum(((np.asarray(e["gdesc"], dtype=np.float64) - mu) / sd - zq) ** 2)))
    return {**best, "_match": "cross_n"}


def _remap_chains(entry: Dict, nodes_q: List[int], vfeat_q: np.ndarray,
                  target_graph: nx.Graph) -> Dict[int, List[int]]:
    """Align query and retrieved vertices in sorted structural-feature order and
    transfer RW chains, dropping qubits absent from the (possibly broken) target."""
    nodes_r = entry["nodes"]
    vfeat_r = np.asarray(entry["vfeat"])
    chains_r = entry["embedding"]
    order_q = _lex_order(vfeat_q)
    order_r = _lex_order(vfeat_r)
    target_nodes = set(target_graph.nodes())
    k = min(len(nodes_q), len(nodes_r))
    initial: Dict[int, List[int]] = {}
    for t in range(k):
        qn = int(nodes_q[order_q[t]])
        rn = int(nodes_r[order_r[t]])
        chain = [int(q) for q in chains_r.get(rn, []) if q in target_nodes]
        if chain:
            initial[qn] = chain
    return initial


# =============================================================================
# Registry adapter
# =============================================================================

def _ckpt_dir() -> Path:
    env = os.environ.get("EMBER_LEARN_CKPT_DIR")
    if env:
        return Path(env)
    # repo-root/ckpts (…/ember_qc_learn/families/retrieve.py -> parents[5] = repo root)
    return Path(__file__).resolve().parents[5] / "ckpts"


def _infer_target_name(G: nx.Graph) -> Optional[str]:
    from ember_qc_learn.features import _family
    return {"pegasus": "pegasus_6", "zephyr": "zephyr_4"}.get(_family(G))


@register_algorithm("learned-retrieve")
class RetrieveCache(EmbeddingAlgorithm):
    """Retrieval / embeddings-cache embedder: nearest indexed RW embedding, remapped
    onto the query graph and grown to validity by minorminer (non-neural)."""

    _requires = ["minorminer", "numpy", "networkx"]

    def __init__(self):
        self._index_cache: Dict[str, Optional[Dict]] = {}

    # -- availability ---------------------------------------------------------
    def _ckpt_path(self, target_name: str) -> Path:
        return _ckpt_dir() / f"retrieve_{target_name}.pt"

    def is_available(self):
        try:
            import minorminer  # noqa: F401
            import numpy  # noqa: F401
            import networkx  # noqa: F401
        except Exception:
            return (False, "needs minorminer + numpy + networkx")
        for t in _DEFAULT_TARGETS:
            if self._ckpt_path(t).exists():
                return (True, "")
        return (False, f"no retrieve_*.pt in {_ckpt_dir()}")

    @property
    def version(self) -> str:
        return "0.1.0"

    @property
    def supported_topologies(self):
        return ["pegasus", "zephyr"]

    # -- index loading --------------------------------------------------------
    def _load(self, target_name: str) -> Optional[Dict]:
        if target_name in self._index_cache:
            return self._index_cache[target_name]
        p = self._ckpt_path(target_name)
        idx: Optional[Dict] = None
        if p.exists():
            try:
                with open(p, "rb") as f:
                    idx = pickle.load(f)
            except Exception:
                idx = None
        self._index_cache[target_name] = idx
        return idx

    # -- embed ----------------------------------------------------------------
    def embed(self, source_graph: nx.Graph, target_graph: nx.Graph,
              timeout: float = 60.0, **kwargs) -> Dict:
        from ember_qc_learn.decode import run_minorminer

        t0 = time.time()
        seed = int(kwargs.get("seed", 0))
        random.seed(seed)
        np.random.seed(seed & 0xFFFFFFFF)
        empty = {"embedding": {}, "time": 0.0, "success": False, "status": "FAILURE"}

        tname = _infer_target_name(target_graph)
        if tname is None:
            return {**empty, "time": time.time() - t0, "error": "unknown target family"}
        index = self._load(tname)
        if not index or not index.get("entries"):
            return {**empty, "time": time.time() - t0,
                    "error": f"no retrieval index for {tname}"}

        nodes_q = sorted(source_graph.nodes())
        if not nodes_q:
            return {**empty, "time": time.time() - t0}
        vfeat_q = _vertex_features(source_graph, nodes_q)
        gdesc_q = _graph_descriptor(source_graph, vfeat_q, nodes_q)

        entry = _retrieve_nearest(index, len(nodes_q), vfeat_q, gdesc_q)
        initial = _remap_chains(entry, nodes_q, vfeat_q, target_graph) if entry else {}

        mm_to = float(min(timeout, 20.0))
        emb = run_minorminer(source_graph, target_graph, initial or None,
                             seed=seed, timeout=mm_to)
        match = entry.get("_match") if entry else None
        warm = bool(emb)
        if not emb:
            # cold-MM fallback so a misleading warm start never costs us validity
            remaining = max(1.0, timeout - (time.time() - t0))
            emb = run_minorminer(source_graph, target_graph, None,
                                 seed=seed, timeout=float(min(remaining, mm_to)))
            match = (match + "+cold") if match else "cold"

        if not emb:
            return {**empty, "time": time.time() - t0, "error": "minorminer failed"}
        return {
            "embedding": emb,
            "time": time.time() - t0,
            "success": True,
            "status": "SUCCESS",
            "metadata": {"retrieved_id": entry.get("id") if entry else None,
                         "match": match, "warm_start": warm,
                         "seeded_vertices": len(initial)},
        }


if __name__ == "__main__":
    main()
