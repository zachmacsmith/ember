"""
pssa_dwave/terminal_search.py
==============================
Terminal search (Algorithm 2) — topology-agnostic.

Identical logic to the King's graph version.
Works on any networkx hardware graph: Chimera, Pegasus, Zephyr.
"""

from collections import defaultdict, deque
from typing import Dict, List, Optional, Set, Tuple

import networkx as nx

from pssa_dwave.core import NodeH, NodeI, Phi, InvPhi, eemb, invert


def _repr_counts(phi, I, H, inv):
    counts = defaultdict(int)
    for u, v in H.edges():
        i = inv.get(u)
        j = inv.get(v)
        if i is None or j is None or i == j:
            continue
        edge = (min(i, j), max(i, j))
        if I.has_edge(i, j):
            counts[edge] += 1
    return counts


def is_deletable(u, i, phi, I, H, inv, repr_counts):
    sv = phi[i]
    if len(sv) <= 1:
        return False
    remaining = [w for w in sv if w != u]
    if not nx.is_connected(H.subgraph(remaining)):
        return False
    for v in H.neighbors(u):
        j = inv.get(v)
        if j is None or j == i:
            continue
        if not I.has_edge(i, j):
            continue
        edge = (min(i, j), max(i, j))
        via_u = sum(1 for w in H.neighbors(u) if inv.get(w) == j)
        if repr_counts.get(edge, 0) - via_u <= 0:
            return False
    return True


def bfs_path(i, j, phi, H, free):
    source = set(phi[i])
    target = set(phi[j])
    queue  = deque(source)
    parent: Dict[NodeH, Optional[NodeH]] = {u: None for u in source}
    visited = set(source)

    while queue:
        u = queue.popleft()
        for v in H.neighbors(u):
            if v in visited:
                continue
            if v not in free and v not in target:
                continue
            if v in target:
                path: List[NodeH] = []
                cur = u
                while cur not in source:
                    path.append(cur)
                    cur = parent[cur]
                path.reverse()
                return path
            visited.add(v)
            parent[v] = u
            queue.append(v)
    return None


def terminal_search(phi: Phi, I: nx.Graph, H: nx.Graph) -> Phi:
    """
    Algorithm 2 — Terminal search.

    Works on any hardware graph topology (Chimera, Pegasus, Zephyr).
    Never decreases Eemb(φ).
    """
    phi = {i: list(p) for i, p in phi.items()}
    inv = invert(phi)
    rc  = _repr_counts(phi, I, H, inv)

    hw_nodes = list(H.nodes())
    n_hw     = len(hw_nodes)
    free: Set[NodeH] = set()
    no_del = 0
    idx    = 0

    # Phase 1: Free wasted hardware nodes
    while no_del < n_hw:
        u = hw_nodes[idx % n_hw]
        idx += 1
        i = inv.get(u)
        if i is None or u in free:
            no_del += 1
            continue
        if is_deletable(u, i, phi, I, H, inv, rc):
            phi[i] = [w for w in phi[i] if w != u]
            del inv[u]
            free.add(u)
            for v in H.neighbors(u):
                j = inv.get(v)
                if j is None or j == i:
                    continue
                edge = (min(i, j), max(i, j))
                if I.has_edge(i, j):
                    via_u = sum(1 for w in H.neighbors(u) if inv.get(w) == j)
                    rc[edge] = max(0, rc.get(edge, 0) - via_u)
            no_del = 0
        else:
            no_del += 1

    # Phase 2: BFS link remaining unconnected input edges
    for i in sorted(I.nodes()):
        for j in I.neighbors(i):
            if j <= i:
                continue
            linked = any(
                inv.get(v) == j
                for u in phi[i]
                for v in H.neighbors(u)
            )
            if linked:
                continue
            path = bfs_path(i, j, phi, H, free)
            if path is not None:
                for v in path:
                    phi[i].append(v)
                    inv[v] = i
                    free.discard(v)
                edge = (min(i, j), max(i, j))
                if I.has_edge(i, j):
                    rc[edge] = rc.get(edge, 0) + 1

    return phi
