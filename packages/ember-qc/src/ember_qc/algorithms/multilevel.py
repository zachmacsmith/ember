"""
ember_qc/algorithms/multilevel.py
=================================
Multilevel V-cycle minor embedding (approach 3.3).

The multilevel paradigm that dominates graph partitioning (METIS; Karypis &
Kumar 1998) is *coarsen -> solve-at-the-coarsest -> uncoarsen-and-refine*. This
module applies it to minor embedding on the **source** (problem) graph:

1. **Coarsen.** Collapse the source graph by repeated **heavy-edge matching**
   into a hierarchy ``H0 ⊃ H1 ⊃ … ⊃ Hk`` (``Hk`` = a few-to-``coarse_target``
   vertices). A super-vertex is a contracted set of original vertices; parallel
   edges between super-vertices accumulate weight.

2. **Base embed.** Embed the coarsest ``Hk`` with heavy effort — multi-restart
   ``minorminer`` (several seeds, keep the fewest-qubit valid embedding). With
   only tens of vertices this is fast *and* the placement reflects the problem's
   global structure, which is the thing the MM paper named as the key open
   problem ("better initial placement of vertex-models").

3. **Uncoarsen + refine.** Project the embedding one level finer at a time. Each
   super-vertex already *owns* a connected hardware region (its chain ``Q``); the
   **interpolation operator** splits ``Q`` among the super-vertex's constituents,
   then a local **edge-repair** pass re-establishes the external couplings the
   split may have severed, a **trim** pass deletes redundant qubits (the real ACL
   lever), and a light **Fiduccia–Mattheyses** boundary pass rebalances long
   chains into shorter adjacent ones. Validity is re-checked at every level.

Why this might beat MM: the expensive, structure-sensitive decision (where each
cluster of strongly-coupled vertices goes) is made once, at the coarsest level,
where global structure is visible and a single random vertex order barely
matters; everything finer is *local* refinement of an already-good layout. That
should lower run-to-run ACL variance and behave better on large/dense instances
than MM's one random-order rip-up-and-rebuild.

The chain-splitting **interpolation operator** is the crux and has no
off-the-shelf version. The implementation here is deliberately the *sound*
first version from the brief: a graph-Voronoi partition of ``Q`` between two
far-apart seed qubits (so each constituent gets a connected sub-region and the
``a–b`` coupling is automatically satisfied), followed by free-space routing to
re-cover external edges. When a level cannot be made valid (tight regions, dense
instances) the whole V-cycle reports failure and the embedder falls back to a
single ``minorminer`` run, so the algorithm is never *worse* than MM on success
and the result is always a valid embedding or an honest failure dict.

Reuses the shared backend (``ember_qc.embedding_backend``) for all routing:
``build_adjacency``, ``weighted_multisource_dijkstra``, ``reconstruct_path``,
``chain_connected`` and ``is_valid_embedding``. Pure Python; the only heavy
dependency is ``minorminer`` (coarsest base solver and per-level legalizer of
last resort), which is already a project core dependency.
"""

from __future__ import annotations

import collections
import logging
import random
import time
from typing import Dict, List, Optional, Set, Tuple

import networkx as nx

from ember_qc.registry import EmbeddingAlgorithm, register_algorithm
from ember_qc.embedding_backend import (
    Adjacency,
    Embedding,
    build_adjacency,
    chain_connected,
    is_valid_embedding,
    reconstruct_path,
    weighted_multisource_dijkstra,
)

logger = logging.getLogger(__name__)


# ==============================================================================
# Telemetry — one tiny mutable bag threaded through the helpers so the counters
# stay deterministic (no wall-clock-dependent values) and seed-stable.
# ==============================================================================

class _Tele:
    __slots__ = ("visits", "routes")

    def __init__(self) -> None:
        self.visits: List[int] = [0]   # Dijkstra nodes settled (search effort)
        self.routes: int = 0           # base-embed + connect calls (decision effort)


# ==============================================================================
# COARSENING — heavy-edge matching (Karypis & Kumar 1998)
# ==============================================================================

def _heavy_edge_matching(graph: nx.Graph, order: List[int]) -> Dict[int, int]:
    """Greedy heavy-edge matching: each unmatched vertex pairs with the unmatched
    neighbour joined by the **heaviest** incident edge.

    Returns a symmetric ``partner`` map (``partner[a]=b`` and ``partner[b]=a``)
    holding only matched vertices. Ties break toward the lowest neighbour id so
    the matching is reproducible for a fixed visit ``order`` (METIS visits in
    random order; we derive ``order`` from the seeded RNG).
    """
    partner: Dict[int, int] = {}
    matched: Set[int] = set()
    for v in order:
        if v in matched:
            continue
        best_u: Optional[int] = None
        best_w = -1.0
        for u in graph.neighbors(v):
            if u in matched or u == v:
                continue
            w = float(graph[v][u].get("weight", 1.0))
            if w > best_w or (w == best_w and (best_u is None or u < best_u)):
                best_w = w
                best_u = u
        if best_u is not None:
            partner[v] = best_u
            partner[best_u] = v
            matched.add(v)
            matched.add(best_u)
    return partner


def _coarsen_once(
    graph: nx.Graph, rng: random.Random
) -> Tuple[nx.Graph, Dict[int, List[int]]]:
    """Contract one heavy-edge matching of ``graph`` into a coarser graph.

    Returns ``(coarse, children)`` where ``coarse`` has integer super-vertex ids
    ``0..m-1`` with summed edge weights (self-loops from contracted edges are
    dropped) and ``children[s]`` is the sorted list of ``graph`` vertices that
    super-vertex ``s`` represents (1 or 2 of them).
    """
    order = sorted(graph.nodes())
    rng.shuffle(order)  # seeded -> deterministic; varies across seeds
    partner = _heavy_edge_matching(graph, order)

    label: Dict[int, int] = {}
    children: Dict[int, List[int]] = {}
    placed: Set[int] = set()
    next_id = 0
    for v in order:
        if v in placed:
            continue
        u = partner.get(v)
        if u is not None and u not in placed:
            children[next_id] = sorted((v, u))
            label[v] = label[u] = next_id
            placed.add(v)
            placed.add(u)
        else:
            children[next_id] = [v]
            label[v] = next_id
            placed.add(v)
        next_id += 1

    coarse = nx.Graph()
    coarse.add_nodes_from(range(next_id))
    for a, b, data in graph.edges(data=True):
        sa, sb = label[a], label[b]
        if sa == sb:
            continue  # internal (contracted) edge -> self-loop, drop
        w = float(data.get("weight", 1.0))
        if coarse.has_edge(sa, sb):
            coarse[sa][sb]["weight"] += w
        else:
            coarse.add_edge(sa, sb, weight=w)
    return coarse, children


def _build_hierarchy(
    source: nx.Graph,
    rng: random.Random,
    coarse_target: int,
    max_levels: int,
    deadline: Optional[float],
) -> Tuple[List[nx.Graph], List[Dict[int, List[int]]]]:
    """Build ``H0 ⊃ H1 ⊃ … ⊃ Hk``. ``graphs[0]`` is a weighted copy of ``source``
    (inputs are never mutated); ``children_maps[i]`` maps a vertex of
    ``graphs[i+1]`` to its constituents in ``graphs[i]``.

    Coarsening stops at ``coarse_target`` vertices, ``max_levels`` levels, the
    deadline, or as soon as a matching fails to shrink the graph (e.g. an
    edgeless remainder).
    """
    g0 = nx.Graph()
    g0.add_nodes_from(source.nodes())
    for u, v in source.edges():
        if u != v:
            g0.add_edge(u, v, weight=1.0)
    graphs: List[nx.Graph] = [g0]
    children_maps: List[Dict[int, List[int]]] = []

    cur = g0
    for _ in range(max_levels):
        if cur.number_of_nodes() <= coarse_target:
            break
        if deadline is not None and time.perf_counter() > deadline:
            break
        coarse, children = _coarsen_once(cur, rng)
        if coarse.number_of_nodes() >= cur.number_of_nodes():
            break  # no progress (nothing matched)
        graphs.append(coarse)
        children_maps.append(children)
        cur = coarse
    return graphs, children_maps


# ==============================================================================
# BASE EMBED — multi-restart minorminer on the coarsest graph
# ==============================================================================

def _base_embed(
    coarse: nx.Graph,
    target: nx.Graph,
    adj: Adjacency,
    seed: int,
    n_restarts: int,
    deadline: Optional[float],
    tele: _Tele,
) -> Optional[Embedding]:
    """Embed ``coarse`` with ``n_restarts`` independent ``minorminer`` seeds; keep
    the fewest-qubit *valid* embedding. Deterministic for a fixed seed."""
    import minorminer

    edgelist = list(target.edges())
    now = time.perf_counter()
    remaining = (deadline - now) if deadline is not None else 60.0
    if remaining <= 0:
        remaining = 0.05
    per = max(remaining / max(n_restarts, 1), 0.05)

    best: Optional[Embedding] = None
    best_total = float("inf")
    for i in range(max(n_restarts, 1)):
        if deadline is not None and time.perf_counter() > deadline:
            break
        tele.routes += 1
        try:
            raw = minorminer.find_embedding(
                coarse, edgelist, random_seed=seed + i, timeout=per, verbose=0
            )
        except Exception as exc:  # pragma: no cover - defensive
            logger.debug("multilevel base embed restart %d failed: %s", i, exc)
            continue
        if not raw:
            continue
        emb: Embedding = {int(v): sorted(int(q) for q in raw[v]) for v in raw}
        if not is_valid_embedding(emb, coarse, target, adj=adj):
            continue
        total = sum(len(c) for c in emb.values())
        if total < best_total:
            best, best_total = emb, total
    return best


# ==============================================================================
# THE INTERPOLATION OPERATOR — split a super-vertex chain among its constituents
# ==============================================================================

def _bfs_farthest(start: int, q_set: Set[int], adj: Adjacency) -> int:
    """Return the vertex of ``q_set`` farthest (in hops, BFS *restricted to*
    ``q_set``) from ``start``; ties break toward the lowest id."""
    dist = {start: 0}
    dq = collections.deque([start])
    far, far_d = start, 0
    while dq:
        x = dq.popleft()
        dx = dist[x]
        for w in adj[x]:
            if w in q_set and w not in dist:
                dist[w] = dx + 1
                dq.append(w)
                if dist[w] > far_d or (dist[w] == far_d and w < far):
                    far_d, far = dist[w], w
    return far


def _voronoi_split(
    chain: List[int], adj: Adjacency
) -> Tuple[List[int], List[int]]:
    """Partition a connected qubit set ``chain`` (``|chain| >= 2``) into two
    connected, non-empty cells by nearest-seed graph-Voronoi.

    Two far-apart seeds are found by the standard double-BFS diameter heuristic,
    then a single multi-source BFS (restricted to ``chain``) assigns each qubit
    to the seed whose wave reaches it first. Each cell is connected because a
    qubit's BFS parent shares its owner, and — since ``chain`` is connected and
    split into two non-empty parts — at least one target edge crosses the cut, so
    the two constituents are automatically adjacent (covering the internal
    ``a–b`` coupling). Ties break toward the first seed (deterministic).
    """
    q_set = set(chain)
    s_a = _bfs_farthest(min(chain), q_set, adj)
    s_b = _bfs_farthest(s_a, q_set, adj)
    if s_b == s_a:
        others = [q for q in sorted(chain) if q != s_a]
        s_b = others[0]

    owner: Dict[int, int] = {s_a: 0, s_b: 1}
    dist: Dict[int, int] = {s_a: 0, s_b: 0}
    dq = collections.deque([s_a, s_b])  # s_a first -> ties favour cell A
    while dq:
        x = dq.popleft()
        for w in adj[x]:
            if w in q_set and w not in dist:
                dist[w] = dist[x] + 1
                owner[w] = owner[x]
                dq.append(w)

    cell_a = sorted(q for q in chain if owner.get(q, 0) == 0)
    cell_b = sorted(q for q in chain if owner.get(q) == 1)
    return cell_a, cell_b


def _interpolate(
    coarse_emb: Embedding,
    children: Dict[int, List[int]],
    adj: Adjacency,
    all_qubits: Set[int],
) -> Optional[Embedding]:
    """Project ``coarse_emb`` one level finer: split each super-vertex's chain
    among its constituents. Returns a disjoint, connected fine embedding whose
    *internal* edges are already covered, or ``None`` if a degenerate split could
    not be seeded (a single-qubit chain with no free neighbour to lend)."""
    used: Set[int] = set()
    for chain in coarse_emb.values():
        used.update(chain)
    free = all_qubits - used

    fine: Embedding = {}
    for s in sorted(coarse_emb):
        q = coarse_emb[s]
        kids = children[s]
        if len(kids) == 1:
            fine[kids[0]] = sorted(q)
            continue
        a, b = kids
        if len(q) >= 2:
            cell_a, cell_b = _voronoi_split(q, adj)
            fine[a], fine[b] = cell_a, cell_b
        else:
            # |Q| == 1: lend constituent b a free qubit adjacent to a's qubit so
            # both chains are non-empty and the a-b coupling holds.
            q0 = q[0]
            lend = sorted(w for w in adj[q0] if w in free)
            if not lend:
                return None
            qb = lend[0]
            free.discard(qb)
            fine[a], fine[b] = [q0], [qb]
    return fine


# ==============================================================================
# EDGE REPAIR — free-space routing to re-cover external couplings
# ==============================================================================

def _connect(
    fine: Embedding,
    u: int,
    v: int,
    adj: Adjacency,
    used: Set[int],
    tele: _Tele,
) -> bool:
    """Grow ``fine[u]`` through currently-free qubits until it touches ``fine[v]``.

    Routes a shortest free-space path from ``u``'s chain to a free qubit adjacent
    to ``v``'s chain (other chains, including ``v``'s, are forbidden so the
    detour never overlaps), appends the path's free qubits to ``u``, and marks
    them used. Returns False if no such path exists."""
    chain_u = set(fine[u])
    chain_v = set(fine[v])
    targets = {w for q in chain_v for w in adj[q] if w not in used}
    if not targets:
        return False
    forbidden = used - chain_u  # may start from u; forbid every other chain
    tele.routes += 1
    dist, pred = weighted_multisource_dijkstra(
        adj, sorted(chain_u), {}, targets=set(targets),
        forbidden=forbidden, visit_counter=tele.visits,
    )
    reach = [(dist[t], t) for t in targets if t in dist]
    if not reach:
        return False
    _, best = min(reach, key=lambda t: (t[0], t[1]))
    add = [q for q in reconstruct_path(pred, best) if q not in chain_u]
    if not add:
        return False
    fine[u] = sorted(chain_u.union(add))
    used.update(add)
    return True


def _repair_edges(
    fine: Embedding,
    edges: List[Tuple[int, int]],
    adj: Adjacency,
    deadline: Optional[float],
    tele: _Tele,
) -> bool:
    """Cover every uncovered fine-level edge by growing one endpoint chain toward
    the other through free space. Returns False if some edge cannot be covered."""
    used: Set[int] = set()
    for ch in fine.values():
        used.update(ch)

    def covered(a: int, b: int) -> bool:
        cb = set(fine[b])
        return any(w in cb for q in fine[a] for w in adj[q])

    for (u, v) in edges:
        if deadline is not None and time.perf_counter() > deadline:
            return False
        if covered(u, v):
            continue
        if _connect(fine, u, v, adj, used, tele):
            continue
        if _connect(fine, v, u, adj, used, tele):
            continue
        return False
    return True


# ==============================================================================
# REFINEMENT — trim redundant qubits, then light Fiduccia–Mattheyses rebalance
# ==============================================================================

def _covers_all(
    u: int,
    cand: List[int],
    fine: Embedding,
    nbrs: Dict[int, List[int]],
    adj: Adjacency,
) -> bool:
    """True if chain ``cand`` would still cover every edge incident to ``u``.

    Only ``u``'s own incident edges can break when ``u``'s chain shrinks/moves
    (edges are symmetric and other chains are untouched), so this single check is
    sufficient for global edge coverage."""
    cand_nb: Set[int] = set()
    for q in cand:
        cand_nb.update(adj[q])
    for x in nbrs[u]:
        if cand_nb.isdisjoint(fine[x]):
            return False
    return True


def _trim(
    fine: Embedding,
    nbrs: Dict[int, List[int]],
    adj: Adjacency,
    deadline: Optional[float],
) -> None:
    """Delete redundant qubits: drop any qubit whose removal keeps its chain
    connected and still covers all incident edges. The main ACL lever — the
    split+repair output is deliberately generous and trimming makes it lean.
    Globally safe (removing qubits can only help disjointness/coverage of
    others)."""
    for u in sorted(fine, key=lambda x: (-len(fine[x]), x)):
        if deadline is not None and time.perf_counter() > deadline:
            return
        changed = True
        while changed and len(fine[u]) > 1:
            changed = False
            for q in sorted(fine[u]):
                cand = [x for x in fine[u] if x != q]
                if not cand or not chain_connected(cand, adj):
                    continue
                if _covers_all(u, cand, fine, nbrs, adj):
                    fine[u] = sorted(cand)
                    changed = True
                    break


def _fm_rebalance(
    fine: Embedding,
    nbrs: Dict[int, List[int]],
    adj: Adjacency,
    deadline: Optional[float],
    rounds: int,
) -> None:
    """Light Fiduccia–Mattheyses boundary pass: move a boundary qubit from a long
    chain to a strictly-shorter adjacent chain when both stay valid. Lowers max
    chain length / improves uniformity without changing the total qubit count.
    Only validity-preserving, length-reducing moves are committed."""
    owner: Dict[int, int] = {}
    for v, ch in fine.items():
        for q in ch:
            owner[q] = v

    for _ in range(rounds):
        if deadline is not None and time.perf_counter() > deadline:
            return
        moved = False
        for u in sorted(fine, key=lambda x: (-len(fine[x]), x)):
            if len(fine[u]) <= 1:
                continue
            done_u = False
            for q in sorted(fine[u]):
                cand_u = [x for x in fine[u] if x != q]
                if not cand_u or not chain_connected(cand_u, adj):
                    continue
                if not _covers_all(u, cand_u, fine, nbrs, adj):
                    continue
                adj_chains = sorted(
                    {owner[w] for w in adj[q] if w in owner and owner[w] != u},
                    key=lambda v: (len(fine[v]), v),
                )
                for v in adj_chains:
                    if len(fine[v]) >= len(fine[u]) - 1:
                        continue  # only worthwhile if it shortens the long chain
                    cand_v = sorted(fine[v] + [q])
                    if not chain_connected(cand_v, adj):
                        continue
                    fine[u] = sorted(cand_u)
                    fine[v] = cand_v
                    owner[q] = v
                    moved = done_u = True
                    break
                if done_u:
                    break
        if not moved:
            break


# ==============================================================================
# V-CYCLE DRIVER
# ==============================================================================

def _run_vcycle(
    source: nx.Graph,
    target: nx.Graph,
    adj: Adjacency,
    all_qubits: Set[int],
    seed: int,
    coarse_target: int,
    max_levels: int,
    n_restarts: int,
    fm_rounds: int,
    deadline: Optional[float],
    tele: _Tele,
) -> Tuple[Optional[Embedding], int]:
    """Run one full coarsen -> base-embed -> uncoarsen+refine V-cycle.

    Returns ``(embedding_or_None, n_coarsening_levels)``."""
    rng = random.Random((seed * 2654435761 + 12345) & 0xFFFFFFFF)
    graphs, children_maps = _build_hierarchy(
        source, rng, coarse_target, max_levels, deadline
    )
    n_levels = len(graphs) - 1

    emb = _base_embed(graphs[-1], target, adj, seed, n_restarts, deadline, tele)
    if emb is None:
        return None, n_levels

    # Uncoarsen from the coarsest down to the original (graphs[0]).
    for i in range(len(graphs) - 2, -1, -1):
        if deadline is not None and time.perf_counter() > deadline:
            return None, n_levels
        h_fine = graphs[i]
        fine = _interpolate(emb, children_maps[i], adj, all_qubits)
        if fine is None:
            return None, n_levels
        # Snapshot the freshly-split layout (disjoint + connected) as a warm
        # start, in case the hand-built repair below can't legalize this level.
        layout = {v: list(c) for v, c in fine.items()}
        edges = sorted((min(u, v), max(u, v)) for u, v in h_fine.edges())
        nbrs = {v: list(h_fine.neighbors(v)) for v in fine}

        # (1) Try the custom interpolation operator: free-space edge repair,
        #     then trim + Fiduccia–Mattheyses rebalance. This legalizes the
        #     coarse, structurally-loose levels on its own.
        ok = _repair_edges(fine, edges, adj, deadline, tele)
        if ok:
            _trim(fine, nbrs, adj, deadline)
            _fm_rebalance(fine, nbrs, adj, deadline, fm_rounds)
            ok = is_valid_embedding(fine, h_fine, target, adj=adj)

        # (2) Dense / tight levels: the greedy free-space repair cannot
        #     reproduce the snaking chains they need. Refine with minorminer
        #     *warm-started from the projected layout* — the multilevel
        #     initialization drives a local MM solve for this level.
        if not ok:
            fine = _mm_refine_level(
                h_fine, target, adj, layout, seed, deadline, tele
            )
            if fine is None:
                return None, n_levels
            _trim(fine, nbrs, adj, deadline)

        emb = fine

    return emb, n_levels


def _mm_refine_level(
    h_fine: nx.Graph,
    target: nx.Graph,
    adj: Adjacency,
    initial: Embedding,
    seed: int,
    deadline: Optional[float],
    tele: _Tele,
) -> Optional[Embedding]:
    """Legalize one level with ``minorminer`` warm-started from the projected
    multilevel layout (``initial_chains``). Returns a valid embedding or None."""
    import minorminer

    now = time.perf_counter()
    remaining = (deadline - now) if deadline is not None else 30.0
    if remaining <= 0.02:
        remaining = 0.02
    tele.routes += 1
    try:
        raw = minorminer.find_embedding(
            h_fine, list(target.edges()), random_seed=seed,
            timeout=remaining, verbose=0, initial_chains=initial,
        )
    except Exception as exc:  # pragma: no cover - defensive
        logger.debug("multilevel mm-refine failed: %s", exc)
        return None
    if not raw:
        return None
    emb: Embedding = {int(v): sorted(int(q) for q in raw[v]) for v in raw}
    return emb if is_valid_embedding(emb, h_fine, target, adj=adj) else None


def _mm_fallback(
    source: nx.Graph,
    target: nx.Graph,
    adj: Adjacency,
    seed: int,
    deadline: Optional[float],
    tele: _Tele,
) -> Optional[Embedding]:
    """Single ``minorminer`` run on the original graph (robustness net)."""
    import minorminer

    now = time.perf_counter()
    remaining = (deadline - now) if deadline is not None else 60.0
    if remaining <= 0.01:
        remaining = 0.01
    tele.routes += 1
    try:
        raw = minorminer.find_embedding(
            source, list(target.edges()), random_seed=seed,
            timeout=remaining, verbose=0,
        )
    except Exception:  # pragma: no cover - defensive
        return None
    if not raw:
        return None
    emb: Embedding = {int(v): sorted(int(q) for q in raw[v]) for v in raw}
    return emb if is_valid_embedding(emb, source, target, adj=adj) else None


# ==============================================================================
# FUNCTIONAL ENTRY POINT
# ==============================================================================

def embed_multilevel(
    source_graph: nx.Graph,
    target_graph: nx.Graph,
    *,
    timeout: float = 60.0,
    seed: int = 0,
    coarse_target: int = 8,
    max_levels: int = 8,
    n_restarts: int = 4,
    fm_rounds: int = 2,
    vcycle_fraction: float = 0.8,
    mm_fallback: bool = True,
    **_ignored,
) -> dict:
    """Multilevel V-cycle embedding -> ember-qc result dict.

    Runs the V-cycle within ``vcycle_fraction`` of the time budget; on failure
    (and when ``mm_fallback``) spends the remainder on a plain ``minorminer``
    run, so the contract is always met (a dict, never ``None``, never raises) and
    a returned embedding is always valid. ``metadata['provenance']`` records
    whether the answer came from the V-cycle or the fallback, and
    ``metadata['levels']`` the number of coarsening levels used."""
    start = time.perf_counter()
    deadline = (start + timeout) if timeout else None
    tele = _Tele()
    provenance = "none"
    n_levels = 0

    try:
        adj = build_adjacency(target_graph)
        all_qubits = set(adj.keys())
        vcycle_deadline = (
            start + timeout * vcycle_fraction if timeout else None
        )

        emb, n_levels = _run_vcycle(
            source_graph, target_graph, adj, all_qubits, int(seed),
            coarse_target, max_levels, n_restarts, fm_rounds,
            vcycle_deadline, tele,
        )
        provenance = "vcycle"

        if emb is None and mm_fallback:
            emb = _mm_fallback(
                source_graph, target_graph, adj, int(seed), deadline, tele
            )
            provenance = "mm_fallback"

        # Final globally-safe trim: drop any qubit whose removal keeps its chain
        # connected and all incident source edges covered. Lowers ACL on top of
        # whatever produced the embedding (V-cycle or fallback).
        if emb:
            nbrs = {v: list(source_graph.neighbors(v)) for v in emb}
            _trim(emb, nbrs, adj, deadline)

        elapsed = max(time.perf_counter() - start, 1e-9)
        counters = {
            "target_node_visits": int(tele.visits[0]),
            "cost_function_evaluations": int(tele.routes),
            "embedding_state_mutations": int(
                sum(len(c) for c in emb.values()) if emb else 0
            ),
            "overlap_qubit_iterations": 0,
        }

        if emb and is_valid_embedding(emb, source_graph, target_graph, adj=adj):
            embedding = {int(k): [int(q) for q in v] for k, v in emb.items()}
            return {
                "embedding": embedding,
                "time": elapsed,
                "metadata": {"provenance": provenance, "levels": int(n_levels)},
                **counters,
            }
        return {
            "embedding": {},
            "time": elapsed,
            "success": False,
            "status": "FAILURE",
            "metadata": {"provenance": provenance, "levels": int(n_levels)},
            **counters,
        }
    except Exception as exc:  # never raise — contract requires a failure dict
        logger.error("multilevel error: %s", exc)
        return {
            "embedding": {},
            "time": max(time.perf_counter() - start, 1e-9),
            "success": False,
            "status": "FAILURE",
            "error": str(exc),
            "target_node_visits": int(tele.visits[0]),
            "cost_function_evaluations": int(tele.routes),
            "embedding_state_mutations": 0,
            "overlap_qubit_iterations": 0,
        }


# ==============================================================================
# Registration
# ==============================================================================

@register_algorithm("multilevel")
class Multilevel(EmbeddingAlgorithm):
    """Multilevel V-cycle — coarsen (heavy-edge matching) -> multi-restart MM at
    the coarsest level -> uncoarsen with chain-splitting interpolation, edge
    repair, trim, and a light Fiduccia–Mattheyses rebalance. Falls back to plain
    minorminer if the V-cycle cannot legalize a level."""

    @property
    def version(self) -> str:
        return "1.0.0"

    def embed(self, source_graph, target_graph, timeout: float = 60.0, **kwargs) -> dict:
        seed = kwargs.get("seed", 0)
        if seed is None:
            seed = 0
        return embed_multilevel(
            source_graph, target_graph, timeout=timeout, seed=int(seed)
        )
