"""
ember_qc/algorithms/factored/trees.py
=======================================
The **chain-construction axis**: how a vertex's chain is assembled from
shortest-path searches toward its already-placed neighbours.

Two named strategies over one shared assembly:

* ``sph``   — shortest-path-heuristic Steiner tree (Takahashi–Matsuyama): each
              neighbour attaches to the *nearest node of the growing tree*, so
              paths share trunk structure and chains come out shorter.
* ``union`` — every neighbour attaches to the root only: the union of
              independent shortest paths, which is minorminer's inner step.
              Kept as the ablation arm for this axis.

Assembly (adapted from the paper-1 implementation's ``_steiner_route``
(``reweave.py``, ``new-algorithm`` branch only) and cleaned — not imported, so
this package has no dependency on the paper-1 code):

1. For each placed neighbour ``u``, run a node-weighted multisource Dijkstra
   from ``u``'s *boundary* (qubits adjacent to ``u``'s chain but not in it),
   with ``u``'s own chain forbidden — the new chain must connect *to* ``u``,
   not through it. Other chains' qubits are not forbidden, only priced: routing
   through them creates contention for the cost's history to negotiate away.
2. Root = the qubit reached by the most neighbours (ties: least total cost,
   then lowest id).
3. Attach neighbours nearest-first to the tree (``sph``) or to the root
   (``union``).

Prices come in as a plain ``{qubit: float}`` map (the cost object's live view).
Unreachability is signalled by absence from a Dijkstra's ``dist`` map and
handled with an ``inf`` sentinel — NOT a large finite constant, because
exponential congestion prices make genuinely-reachable paths arbitrarily
expensive, and a finite sentinel would silently drop the connection instead of
paying for it.
"""

from __future__ import annotations

from typing import Dict, List, Optional

from ember_qc.embedding_backend import (
    Adjacency,
    CostMap,
    Embedding,
    reconstruct_path,
    weighted_multisource_dijkstra,
)

_INF = float("inf")


def _assemble(
    v: int,
    placed: List[int],
    chains: Embedding,
    adj: Adjacency,
    prices: CostMap,
    visit_counter: List[int],
    *,
    attach_to_root_only: bool,
    forbidden_extra: Optional[Set[int]] = None,
    require_all_neighbors: bool = False,
    rng=None,
) -> Optional[List[int]]:
    """Build a chain for ``v`` connecting every reachable placed neighbour.

    ``forbidden_extra`` removes qubits from play entirely (subtracted from
    boundaries, added to every per-neighbour forbidden set) — used by the
    polish pass to rebuild strictly within free fabric. With
    ``require_all_neighbors`` the assembly returns ``None`` unless *every*
    placed neighbour was attached, so a caller that swaps the result in can
    never uncover a source edge.

    Returns a sorted, connected, de-duplicated qubit list, or ``None`` if no
    neighbour is reachable (empty boundaries or fully forbidden fabric) — or,
    under ``require_all_neighbors``, if any neighbour could not be attached.
    """
    forbidden_extra = forbidden_extra or set()
    dist_by_u: Dict[int, CostMap] = {}
    pred_by_u: Dict[int, Dict[int, Optional[int]]] = {}
    for u in placed:
        chain_u = set(chains[u])
        boundary = {w for q in chains[u] for w in adj[q] if w not in chain_u}
        boundary -= forbidden_extra
        if not boundary:
            continue
        dist, pred = weighted_multisource_dijkstra(
            adj, boundary, prices,
            forbidden=chain_u | forbidden_extra, visit_counter=visit_counter,
        )
        if dist:
            dist_by_u[u] = dist
            pred_by_u[u] = pred

    if not dist_by_u:
        return None

    # Root: reachable from the most neighbours; ties by least total cost.
    # Remaining ties: lowest id (deterministic), or — with an rng — a uniform
    # random choice among the exact tie set, which is precisely shipped
    # minorminer's root rule (pathfinder.hpp: collectMinima + randint).
    reach: Dict[int, int] = {}
    total: Dict[int, float] = {}
    for dist in dist_by_u.values():
        for q, d in dist.items():
            reach[q] = reach.get(q, 0) + 1
            total[q] = total.get(q, 0.0) + d
    best_key = max((reach[q], -total[q]) for q in reach)
    candidates = sorted(q for q in reach if (reach[q], -total[q]) == best_key)
    if rng is not None and len(candidates) > 1:
        root = candidates[rng.randrange(len(candidates))]
    else:
        root = candidates[0]

    tree = {root}
    attached = 0
    for u in sorted(dist_by_u, key=lambda u: (dist_by_u[u].get(root, _INF), u)):
        dist = dist_by_u[u]
        attach = (root,) if attach_to_root_only else tree
        best_t: Optional[int] = None
        best_d = _INF
        for t in attach:
            d = dist.get(t, _INF)
            if d < best_d or (d == best_d and best_t is not None and t < best_t):
                best_d, best_t = d, t
        if best_t is None:
            continue  # this neighbour cannot reach the tree; skip, negotiate later
        tree.update(reconstruct_path(pred_by_u[u], best_t))
        attached += 1
    if require_all_neighbors and attached < len(placed):
        return None
    return sorted(tree)


def sph_tree(v, placed, chains, adj, prices, visit_counter, **kwargs):
    """Shortest-path-heuristic Steiner tree (nearest-tree attachment)."""
    return _assemble(v, placed, chains, adj, prices, visit_counter,
                     attach_to_root_only=False, **kwargs)


def union_of_paths(v, placed, chains, adj, prices, visit_counter, **kwargs):
    """Union of independent shortest paths to the root — minorminer's inner step."""
    return _assemble(v, placed, chains, adj, prices, visit_counter,
                     attach_to_root_only=True, **kwargs)


TREES = {
    "sph": sph_tree,
    "union": union_of_paths,
}
