"""
ember_qc/algorithms/search_orders.py
=====================================
Vehicle-agnostic **construction-order heuristics** for minor embedding — the
"vertex ordering" search lever.  Each function maps a source graph to a list of
its vertices in *placement order* (the vertex placed first comes first), so the
same ordering can drive any MM-style embedder:

  * the factored embedder (``factored.RouterConfig(order=...)``),
  * a forked ``minorminer`` (passed as ``var_order=``),
  * CHARME's ATOM constructive embedder (its explicit order input).

Why ordering is a lever.  MM-style embedders place / rebuild one chain at a time
against the chains already down; a vertex placed *after* many of its neighbours
can anchor to them and stays compact, while one placed early floats and balloons.
MM is documented to be sensitive to this order (it is the source of much of its
run-to-run variance).  The heuristics below are the classic graph-elimination /
bandwidth / spectral orders, each motivated by "place tightly-coupled vertices
close together in time".

Convention.  Elimination-based orders (degeneracy, min-fill, MCS) are returned in
**placement = reverse-elimination** order: the vertex eliminated *last* (the dense
core) is placed *first*.  All functions are deterministic and handle disconnected
graphs (leftover vertices appended in sorted order).
"""
from __future__ import annotations

import collections
from typing import Callable, Dict, List

import networkx as nx


def _adj_sets(G: nx.Graph) -> Dict[int, set]:
    return {v: set(G.neighbors(v)) for v in G.nodes()}


def _append_missing(order: List[int], G: nx.Graph) -> List[int]:
    seen = set(order)
    order.extend(sorted(v for v in G.nodes() if v not in seen))
    return order


# --------------------------------------------------------------------------- #
# baseline reference (matches ReweaveRouter._bfs_order)
# --------------------------------------------------------------------------- #
def bfs_maxdeg_order(G: nx.Graph) -> List[int]:
    """BFS from the highest-degree vertex — the Reweave cold-start baseline."""
    nodes = list(G.nodes())
    if not nodes:
        return []
    deg = dict(G.degree())
    start = max(nodes, key=lambda v: (deg[v], -v))
    order, seen = [], {start}
    dq = collections.deque([start])
    while dq:
        x = dq.popleft()
        order.append(x)
        for w in sorted(G.neighbors(x)):
            if w not in seen:
                seen.add(w)
                dq.append(w)
    return _append_missing(order, G)


# --------------------------------------------------------------------------- #
# degeneracy: place the densest k-core first (reverse of min-degree elimination)
# --------------------------------------------------------------------------- #
def degeneracy_order(G: nx.Graph) -> List[int]:
    """Reverse degeneracy ordering — highest-coreness vertices placed first.

    Repeatedly removes the current minimum-degree vertex (the standard
    degeneracy/elimination order, low-core first), then reverses so the dense
    core anchors the embedding first."""
    adj = _adj_sets(G)
    deg = {v: len(adj[v]) for v in adj}
    elim: List[int] = []
    remaining = set(adj)
    # simple repeated-min-degree (bucket queue is overkill at eval sizes)
    while remaining:
        v = min(remaining, key=lambda u: (deg[u], u))
        remaining.discard(v)
        elim.append(v)
        for w in adj[v]:
            if w in remaining:
                deg[w] -= 1
    elim.reverse()
    return _append_missing(elim, G)


# --------------------------------------------------------------------------- #
# min-fill: greedy elimination minimizing added fill edges (reverse for placement)
# --------------------------------------------------------------------------- #
def minfill_order(G: nx.Graph) -> List[int]:
    """Reverse min-fill elimination order.

    At each step eliminate the vertex whose elimination adds the fewest fill
    edges among its neighbours (the min-fill tree-decomposition heuristic), then
    reverse so the last-eliminated (most central) vertices are placed first."""
    adj = {v: set(nbrs) for v, nbrs in _adj_sets(G).items()}
    elim: List[int] = []
    remaining = set(adj)
    while remaining:
        def fill(u: int) -> int:
            nb = [w for w in adj[u] if w in remaining]
            miss = 0
            for i in range(len(nb)):
                ai = adj[nb[i]]
                for j in range(i + 1, len(nb)):
                    if nb[j] not in ai:
                        miss += 1
            return miss
        v = min(remaining, key=lambda u: (fill(u), len(adj[u] & remaining), u))
        # add fill edges so the elimination graph stays consistent
        nb = [w for w in adj[v] if w in remaining]
        for i in range(len(nb)):
            for j in range(i + 1, len(nb)):
                adj[nb[i]].add(nb[j])
                adj[nb[j]].add(nb[i])
        remaining.discard(v)
        elim.append(v)
    elim.reverse()
    return _append_missing(elim, G)


# --------------------------------------------------------------------------- #
# maximum cardinality search: place each vertex after most of its neighbours
# --------------------------------------------------------------------------- #
def mcs_order(G: nx.Graph) -> List[int]:
    """Maximum Cardinality Search visitation order (used forward for placement).

    Start at the highest-degree vertex; repeatedly visit the unvisited vertex
    with the most already-visited neighbours (ties: higher degree). Each vertex
    thus arrives after many of its neighbours — a naturally compact placement
    order (and a perfect elimination order on chordal graphs)."""
    nodes = list(G.nodes())
    if not nodes:
        return []
    adj = _adj_sets(G)
    deg = {v: len(adj[v]) for v in adj}
    wt = {v: 0 for v in nodes}
    visited: set = set()
    order: List[int] = []
    for _ in range(len(nodes)):
        cand = [v for v in nodes if v not in visited]
        v = max(cand, key=lambda u: (wt[u], deg[u], -u))
        visited.add(v)
        order.append(v)
        for w in adj[v]:
            if w not in visited:
                wt[w] += 1
    return order


# --------------------------------------------------------------------------- #
# bandwidth-reducing and spectral orders
# --------------------------------------------------------------------------- #
def cuthill_mckee_order(G: nx.Graph) -> List[int]:
    """Reverse Cuthill–McKee bandwidth-reducing order (places a contiguous,
    low-bandwidth sweep — neighbours stay close in the sequence)."""
    from networkx.utils import reverse_cuthill_mckee_ordering
    try:
        order = list(reverse_cuthill_mckee_ordering(G))
    except Exception:
        return bfs_maxdeg_order(G)
    return _append_missing(order, G)


def spectral_order(G: nx.Graph) -> List[int]:
    """Fiedler (spectral) ordering — sort by the 2nd Laplacian eigenvector, so
    graph-adjacent vertices land near each other in the sequence.

    Computed deterministically: ``nx.spectral_ordering`` defaults to a randomized
    eigensolver (different order each call), which would make any embedder seeded
    by it non-reproducible. We fix the solver seed and canonicalize the Fiedler
    sign (orient by (value, node-id)) so the order is stable across calls."""
    try:
        order = list(nx.spectral_ordering(G, seed=1234, method="tracemin_lu"))
    except Exception:
        try:
            order = list(nx.spectral_ordering(G, seed=1234))
        except Exception:
            return bfs_maxdeg_order(G)
    # Canonicalize sign/direction: the Fiedler vector (hence the order) is only
    # defined up to a global flip; pick the orientation whose endpoints are sorted
    # by node id so repeated calls agree.
    if order and len(order) > 1 and order[0] > order[-1]:
        order = order[::-1]
    return _append_missing(order, G)


# --------------------------------------------------------------------------- #
# community-aware: place whole communities together, densest first
# --------------------------------------------------------------------------- #
def community_order(G: nx.Graph) -> List[int]:
    """Greedy-modularity communities, each emitted as a BFS block; larger / denser
    communities first.  Keeps strongly-coupled vertices contiguous in time."""
    from networkx.algorithms.community import greedy_modularity_communities
    try:
        comms = list(greedy_modularity_communities(G))
    except Exception:
        return bfs_maxdeg_order(G)
    order: List[int] = []
    for comm in sorted(comms, key=lambda c: (-len(c), min(c))):
        sub = G.subgraph(comm)
        order.extend(bfs_maxdeg_order(sub))
    return _append_missing(order, G)


ORDERINGS: Dict[str, Callable[[nx.Graph], List[int]]] = {
    "bfs": bfs_maxdeg_order,
    "degeneracy": degeneracy_order,
    "minfill": minfill_order,
    "mcs": mcs_order,
    "cuthill": cuthill_mckee_order,
    "spectral": spectral_order,
    "community": community_order,
}
