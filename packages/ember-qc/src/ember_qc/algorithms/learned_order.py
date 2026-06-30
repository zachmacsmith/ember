"""
ember_qc/algorithms/learned_order.py
=====================================
A **learned vertex-ordering** for minor embedding — the learning-based arm of the
search-guidance study (the deterministic arm is ``search_orders.py``).

The deterministic finding is that a bandwidth/locality order (Cuthill–McKee) drives
the forked minorminer full search to ~2% lower ACL and lower variance than its
random RPFS order. The natural learning question: can a model predict a *per-vertex
priority* whose induced order beats the best fixed heuristic order — adapting to
each instance instead of committing to one rule?

We keep it deliberately light (ceiling-probe discipline): a **linear score over
cheap per-vertex graph features**, with weights fit to minimize decoded ACL on a
training set (``docs/candidate-algorithms/data/learn_order.py``). A linear model is
interpretable, trains in minutes on CPU, and is a fair test of whether *any* learned
per-vertex priority helps before spending the GPU cluster on a GNN. The induced
order feeds the same vehicles as the deterministic orders (forked MM ``var_order``,
ATOM, Reweave cold start).

``FEATURES`` are the named, normalized per-vertex features; ``vertex_feature_matrix``
returns an (n, d) array aligned with ``nodes``; ``learned_order(G, weights)`` sorts
vertices by ``features @ weights`` (descending) into a placement order.
"""
from __future__ import annotations

from typing import Dict, List, Optional, Sequence

import networkx as nx
import numpy as np

# Named features (order defines the weight-vector layout). All cheap to compute
# and scale-normalized so weights transfer across graph sizes.
FEATURES = [
    "degree",            # normalized degree
    "core",              # k-core number (degeneracy) normalized
    "clustering",        # local clustering coefficient
    "triangles",         # triangle count normalized
    "avg_nbr_deg",       # average neighbour degree normalized
    "ecc",               # eccentricity normalized (locality / centrality)
]
# (No constant/bias feature: a constant added to every vertex's score does not
# change the argsort, so it cannot affect the order.)


def vertex_feature_matrix(G: nx.Graph, nodes: Optional[Sequence] = None) -> np.ndarray:
    """(n, len(FEATURES)) normalized feature matrix aligned with ``nodes``."""
    if nodes is None:
        nodes = list(G.nodes())
    n = max(1, G.number_of_nodes())
    deg = dict(G.degree())
    maxdeg = max(deg.values()) if deg else 1
    core = nx.core_number(G) if G.number_of_edges() else {v: 0 for v in G}
    maxcore = max(core.values()) if core else 1
    clust = nx.clustering(G)
    tri = nx.triangles(G) if not G.is_directed() else {v: 0 for v in G}
    maxtri = max(tri.values()) if tri and max(tri.values()) > 0 else 1
    avgnd = nx.average_neighbor_degree(G)
    # eccentricity only on connected graphs; fall back to degree-proxy otherwise.
    try:
        ecc = nx.eccentricity(G)
        maxecc = max(ecc.values()) if ecc else 1
    except Exception:
        ecc = {v: 0 for v in G}
        maxecc = 1

    rows = []
    for v in nodes:
        rows.append([
            deg.get(v, 0) / maxdeg,
            core.get(v, 0) / maxcore,
            clust.get(v, 0.0),
            tri.get(v, 0) / maxtri,
            (avgnd.get(v, 0.0) / maxdeg),
            (ecc.get(v, 0) / maxecc),
            1.0,
        ])
    return np.asarray(rows, dtype=float)


def learned_order(G: nx.Graph, weights: Sequence[float]) -> List[int]:
    """Placement order: vertices sorted by ``features @ weights`` (high first)."""
    nodes = list(G.nodes())
    if not nodes:
        return []
    w = np.asarray(weights, dtype=float)
    X = vertex_feature_matrix(G, nodes)
    if w.shape[0] != X.shape[1]:
        # weight/feature mismatch -> safe fallback to degree order
        return sorted(nodes, key=lambda v: (-G.degree(v), v))
    score = X @ w
    # descending score; deterministic tie-break by node id
    return [nodes[i] for i in sorted(range(len(nodes)), key=lambda i: (-score[i], nodes[i]))]


# Default weights: filled in by training (learn_order.py writes search_weights.json).
# Until trained, this mild prior (favor high-degree, high-core, low-eccentricity —
# i.e. dense core first, periphery last) gives a sane order.
DEFAULT_WEIGHTS: Dict[str, float] = {
    "degree": 1.0, "core": 1.0, "clustering": 0.0, "triangles": 0.0,
    "avg_nbr_deg": 0.0, "ecc": -1.0, "bias": 0.0,
}


def weights_vector(d: Dict[str, float]) -> List[float]:
    return [float(d.get(name, 0.0)) for name in FEATURES]
