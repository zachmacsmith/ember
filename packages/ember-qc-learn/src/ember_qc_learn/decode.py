"""
Decoders: turn a model's raw output into a VALID embedding. Two paths (both reuse
ember_qc's battle-tested repair backend, so models never re-implement validity):

  seed-for-MM:  per-vertex qubit scores -> disjoint 1-qubit seeds (Hungarian)
                -> minorminer.find_embedding(initial_chains=...)   [always grows valid chains]

  direct:       soft assignment S[qubit, vertex] -> round_assignment_matrix
                -> grow_to_connected -> resolve_overlaps           [partial -> connected -> legal]

All functions are model-agnostic: they take plain numpy arrays.
"""
from __future__ import annotations

import time
from typing import Dict, List, Optional, Sequence

import networkx as nx
import numpy as np

from ember_qc.embedding_backend import (
    build_adjacency, grow_to_connected, is_valid_embedding,
    resolve_overlaps, round_assignment_matrix,
)

Embedding = Dict[int, List[int]]


# ----------------------------------------------------------------- score helpers

def coords_to_qubit_scores(pred_coords: np.ndarray, target_coords: np.ndarray) -> np.ndarray:
    """[n,2] predicted logical coords + [m,2] qubit coords -> [n,m] proximity scores
    (higher = closer). score = -squared Euclidean distance."""
    d2 = ((pred_coords[:, None, :] - target_coords[None, :, :]) ** 2).sum(-1)
    return -d2.astype(np.float64)


# ----------------------------------------------------------------- seed -> MM

def seed_chains_from_scores(scores: np.ndarray,
                            qubit_nodes: Sequence[int],
                            source_nodes: Sequence[int]) -> Dict[int, List[int]]:
    """Assign each logical vertex a DISTINCT seed qubit maximizing total score
    (optimal 1-to-1 via Hungarian). scores: [n_source, m_qubit]. Returns
    {source_node: [qubit_node]} suitable for minorminer initial_chains."""
    from scipy.optimize import linear_sum_assignment
    n = len(source_nodes)
    if n == 0:
        return {}
    cost = -np.asarray(scores, dtype=np.float64)        # maximize score = minimize -score
    rows, cols = linear_sum_assignment(cost)            # rectangular OK (n <= m)
    return {int(source_nodes[r]): [int(qubit_nodes[c])] for r, c in zip(rows, cols)}


def run_minorminer(source: nx.Graph, target: nx.Graph,
                   initial_chains: Optional[Dict[int, List[int]]] = None,
                   *, seed: int = 0, timeout: float = 20.0,
                   tries: int = 1) -> Optional[Embedding]:
    """minorminer.find_embedding, optionally warm-started with initial_chains.
    Returns the embedding dict or None on failure."""
    import minorminer
    kw = dict(random_seed=int(seed) & 0xFFFFFFFF, timeout=timeout, verbose=0, tries=tries)
    if initial_chains:
        kw["initial_chains"] = {int(k): [int(q) for q in v] for k, v in initial_chains.items() if v}
    emb = minorminer.find_embedding(source, list(target.edges()), **kw)
    if not emb:
        return None
    return {int(k): [int(q) for q in v] for k, v in emb.items()}


# ----------------------------------------------------------------- direct -> repair

def embedding_from_soft(S: np.ndarray,
                        qubit_nodes: Sequence[int],
                        source_nodes: Sequence[int],
                        source: nx.Graph,
                        target: nx.Graph,
                        *, seed: int = 0,
                        threshold: float = 0.0,
                        adj=None) -> Optional[Embedding]:
    """Soft assignment S[qubit, vertex] -> valid embedding via round -> grow -> resolve.
    Returns a valid embedding, or None if repair can't legalize it."""
    adj = adj if adj is not None else build_adjacency(target)
    partial = round_assignment_matrix(np.asarray(S, dtype=np.float64),
                                      list(qubit_nodes), list(source_nodes),
                                      threshold=threshold)
    if not partial:
        return None
    grown = grow_to_connected(partial, target, adj=adj)
    emb = resolve_overlaps(grown, source, target, seed=seed, adj=adj)
    if emb and is_valid_embedding(emb, source, target, adj=adj):
        return {int(k): [int(q) for q in v] for k, v in emb.items()}
    return None


# ----------------------------------------------------------------- timed wrappers

def decode_seed_path(scores: np.ndarray, source: nx.Graph, target: nx.Graph,
                     qubit_nodes: Sequence[int], source_nodes: Sequence[int],
                     *, seed: int = 0, timeout: float = 20.0) -> Dict:
    """Full seed->MM decode with timing. Returns {'embedding', 'time'}."""
    t0 = time.perf_counter()
    init = seed_chains_from_scores(scores, qubit_nodes, source_nodes)
    emb = run_minorminer(source, target, init, seed=seed, timeout=timeout)
    return {"embedding": emb or {}, "time": time.perf_counter() - t0}


def decode_direct_path(S: np.ndarray, source: nx.Graph, target: nx.Graph,
                       qubit_nodes: Sequence[int], source_nodes: Sequence[int],
                       *, seed: int = 0, threshold: float = 0.0,
                       mm_fallback: bool = True, timeout: float = 20.0) -> Dict:
    """Full direct->repair decode with timing; optional MM fallback if repair fails.
    Returns {'embedding', 'time'}."""
    t0 = time.perf_counter()
    emb = embedding_from_soft(S, qubit_nodes, source_nodes, source, target,
                              seed=seed, threshold=threshold)
    if emb is None and mm_fallback:
        # use the soft argmax as MM seed rather than giving up
        scores = np.asarray(S, dtype=np.float64).T          # [vertex, qubit]
        init = seed_chains_from_scores(scores, qubit_nodes, source_nodes)
        emb = run_minorminer(source, target, init, seed=seed, timeout=timeout)
    return {"embedding": emb or {}, "time": time.perf_counter() - t0}
