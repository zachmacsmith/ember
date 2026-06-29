"""
Featurization for learned minor-embedding.

Two sides:
  * source_features(H)   -> structural node features + edge_index for the problem graph
  * target_geometry(G)   -> hardware qubit 2-D coordinates + adjacency for P6/Z4

Pure NumPy (no torch) so datagen/decode can reuse it; models wrap to tensors.
The target's 2-D coordinates (from dwave_networkx's layout) are the key idea: a
model predicts *where in the hardware* each logical vertex goes (a learned layout),
then we snap to qubits (seed->MM) or score qubits by proximity (direct->repair).
"""
from __future__ import annotations

from typing import Dict, List, Optional

import networkx as nx
import numpy as np

# Number of Laplacian positional-encoding eigenvectors appended to source features.
LAP_PE_K = 8
# Column layout of source_features(H)["x"], for reference / model input_dim.
SOURCE_SCALAR_FEATURES = [
    "deg_norm", "clustering", "tri_norm", "core_norm", "avg_nbr_deg_norm", "log_n",
]
SOURCE_FEATURE_DIM = len(SOURCE_SCALAR_FEATURES) + LAP_PE_K


# --------------------------------------------------------------------------- source

def _laplacian_pe(H: nx.Graph, nodes: List[int], k: int) -> np.ndarray:
    """k smallest non-trivial normalized-Laplacian eigenvectors as an [n, k] array.

    Sign of each eigenvector is arbitrary; callers may random-flip during training.
    Zero-padded when n <= k."""
    n = len(nodes)
    if n == 0:
        return np.zeros((0, k), dtype=np.float32)
    idx = {u: i for i, u in enumerate(nodes)}
    A = np.zeros((n, n), dtype=np.float64)
    for u, v in H.edges():
        if u in idx and v in idx:
            A[idx[u], idx[v]] = A[idx[v], idx[u]] = 1.0
    deg = A.sum(1)
    dinv = np.divide(1.0, np.sqrt(deg), out=np.zeros_like(deg), where=deg > 0)
    L = np.eye(n) - (dinv[:, None] * A * dinv[None, :])
    L = 0.5 * (L + L.T)
    try:
        w, V = np.linalg.eigh(L)
    except np.linalg.LinAlgError:
        return np.zeros((n, k), dtype=np.float32)
    order = np.argsort(w)
    V = V[:, order]
    # drop the trivial (smallest) eigenvector; take the next k
    pe = V[:, 1:1 + k] if V.shape[1] > 1 else np.zeros((n, k))
    if pe.shape[1] < k:  # pad small graphs
        pe = np.pad(pe, ((0, 0), (0, k - pe.shape[1])))
    return pe.astype(np.float32)


def source_features(H: nx.Graph) -> Dict:
    """Structural node features + bidirectional edge_index for a problem graph.

    Returns dict with:
      nodes: sorted source-node ids
      node_to_idx: {node: row}
      x: [n, SOURCE_FEATURE_DIM] float32 (scalars + Laplacian PE)
      edge_index: [2, 2|E|] int64 (both directions)
      n, m: counts
    """
    nodes = sorted(H.nodes())
    n = len(nodes)
    idx = {u: i for i, u in enumerate(nodes)}
    deg = dict(H.degree())
    clustering = nx.clustering(H)
    triangles = nx.triangles(H) if not H.is_directed() else {u: 0 for u in nodes}
    core = nx.core_number(H) if n else {}
    avg_nbr = nx.average_neighbor_degree(H) if n else {}
    max_deg = max(deg.values()) if deg else 1
    max_tri = max(triangles.values()) if triangles else 1
    max_core = max(core.values()) if core else 1
    log_n = float(np.log1p(n))

    scal = np.zeros((n, len(SOURCE_SCALAR_FEATURES)), dtype=np.float32)
    for u, i in idx.items():
        scal[i] = (
            deg.get(u, 0) / max(max_deg, 1),
            clustering.get(u, 0.0),
            triangles.get(u, 0) / max(max_tri, 1),
            core.get(u, 0) / max(max_core, 1),
            avg_nbr.get(u, 0.0) / max(max_deg, 1),
            log_n,
        )
    pe = _laplacian_pe(H, nodes, LAP_PE_K)
    x = np.concatenate([scal, pe], axis=1).astype(np.float32)

    ei = []
    for u, v in H.edges():
        if u in idx and v in idx:
            ei.append((idx[u], idx[v])); ei.append((idx[v], idx[u]))
    edge_index = (np.array(ei, dtype=np.int64).T if ei
                  else np.zeros((2, 0), dtype=np.int64))
    return {"nodes": nodes, "node_to_idx": idx, "x": x,
            "edge_index": edge_index, "n": n, "m": H.number_of_edges()}


# --------------------------------------------------------------------------- target

def _family(G: nx.Graph) -> str:
    fam = G.graph.get("family")
    if fam:
        return fam
    # infer from node attribute keys
    node0 = next(iter(G.nodes), None)
    if node0 is not None:
        keys = G.nodes[node0].keys()
        for f in ("pegasus", "zephyr", "chimera"):
            if f"{f}_index" in keys:
                return f
    return "pegasus"


def _layout_coords(G: nx.Graph, nodes: List[int]) -> np.ndarray:
    """2-D coordinate per qubit, normalized to [0,1]^2. Uses dwave_networkx's
    topology layout; falls back to a spring layout."""
    import dwave_networkx as dnx
    fam = _family(G)
    pos = None
    layout_fn = getattr(dnx, f"{fam}_layout", None)
    if layout_fn is not None:
        try:
            pos = layout_fn(G)
        except Exception:
            pos = None
    if pos is None:
        pos = nx.spring_layout(G, seed=0)
    P = np.array([pos[u] for u in nodes], dtype=np.float64)
    lo, hi = P.min(0), P.max(0)
    span = np.where(hi - lo > 1e-9, hi - lo, 1.0)
    return ((P - lo) / span).astype(np.float32)


def target_geometry(G: nx.Graph, topology_name: Optional[str] = None) -> Dict:
    """Hardware qubit geometry + adjacency for the target graph.

    Returns dict with:
      qubit_nodes: sorted qubit ids
      node_to_idx: {qubit: row}
      coords: [m, 2] float32 normalized layout coordinates (positional features)
      degree: [m] float32 normalized qubit degree
      edge_index: [2, 2|E_G|] int64
      m: qubit count
    """
    nodes = sorted(G.nodes())
    idx = {q: i for i, q in enumerate(nodes)}
    coords = _layout_coords(G, nodes)
    deg = np.array([G.degree(q) for q in nodes], dtype=np.float32)
    deg = deg / max(deg.max(), 1.0)
    ei = []
    for u, v in G.edges():
        ei.append((idx[u], idx[v])); ei.append((idx[v], idx[u]))
    edge_index = (np.array(ei, dtype=np.int64).T if ei
                  else np.zeros((2, 0), dtype=np.int64))
    return {"qubit_nodes": nodes, "node_to_idx": idx, "coords": coords,
            "degree": deg, "edge_index": edge_index, "m": len(nodes),
            "topology_name": topology_name or _family(G)}
