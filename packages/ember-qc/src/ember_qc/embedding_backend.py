"""
ember_qc/embedding_backend.py
=============================
Shared "round → repair" backend and routing primitives for embedding algorithms.

This is the common scaffolding described in §2.2 of the minor-embedding research
brief: a single, *embedder-agnostic* module that turns a soft / partial /
overlapping assignment into a valid minor embedding.  Four of the five candidate
approaches (semi-relaxed Gromov–Wasserstein, differentiable soft-assignment,
multilevel V-cycle, and the LNS matheuristic) all end in some flavour of
"round → grow → de-conflict", so this backend is shared leverage and keeps their
ablations fair.

Two layers live here:

**Routing primitives** — the graph machinery every chain-building method needs:

    build_adjacency(target)                   -> {node: (neighbours, ...)}
    weighted_multisource_dijkstra(adj, ...)   -> (dist, pred)   node-weighted SSSP
    reconstruct_path(pred, node)              -> [source, ..., node]
    chain_connected(chain, adj)               -> bool
    chain_components(chain, adj)              -> [[component], ...]

**Round → repair** — assignment → valid embedding:

    round_assignment(assignment, *, threshold)        argmax per qubit
    grow_to_connected(chains, target)                 stitch each chain connected
    resolve_overlaps(chains, source, target, ...)     rip-up contested qubits

The routing primitives are deliberately node-weighted (cost accrues on *qubits*,
the scarce resource in an embedding) rather than edge-weighted, which is what
makes them directly reusable by the Reweave negotiated-congestion router
(``ember_qc.algorithms.reweave``).

Conventions
-----------
- An ``Embedding`` is ``{source_node: [target_qubit, ...]}`` — identical to the
  format ``minorminer`` returns and the rest of ember-qc consumes.
- Functions never print; diagnostics go through ``logging``.
- Functions never mutate their graph arguments.
"""

from __future__ import annotations

import heapq
import logging
import math
import random
from typing import Callable, Dict, Iterable, List, Optional, Sequence, Set, Tuple

import networkx as nx

logger = logging.getLogger(__name__)

# A chain maps one source vertex to a list of target qubits (same as minorminer).
Embedding = Dict[int, List[int]]
Adjacency = Dict[int, Tuple[int, ...]]
CostMap = Dict[int, float]

_INF = math.inf


# ==============================================================================
# ROUTING PRIMITIVES
# ==============================================================================

def build_adjacency(target: nx.Graph) -> Adjacency:
    """Freeze a target graph's adjacency into plain tuples for fast, stable iteration.

    Returning tuples (not the live ``AtlasView``) means the order is fixed for the
    lifetime of the dict, which is what makes downstream Dijkstra tie-breaking
    reproducible for a given graph object.
    """
    return {u: tuple(target.neighbors(u)) for u in target.nodes()}


def weighted_multisource_dijkstra(
    adj: Adjacency,
    sources: Iterable[int],
    cost: CostMap,
    *,
    targets: Optional[Set[int]] = None,
    forbidden: Optional[Set[int]] = None,
    default_cost: float = 1.0,
    visit_counter: Optional[List[int]] = None,
) -> Tuple[CostMap, Dict[int, Optional[int]]]:
    """Node-weighted multi-source Dijkstra over ``adj``.

    The cost of a path is the **sum of ``cost[node]`` over every node on the
    path, including both endpoints**.  This is the natural metric for embedding:
    a chain *occupies* qubits, so its price is the sum of the prices of the
    qubits it contains, not of the couplers it traverses.

    Args:
        adj:          Frozen adjacency from :func:`build_adjacency`.
        sources:      Seed nodes; each is reached at cost ``cost[source]``.
        cost:         Per-node cost map. Missing nodes default to ``default_cost``.
        targets:      Optional set of nodes; the search stops as soon as all of
                      them are settled (a speed-up when only a few are needed).
        forbidden:    Nodes that may not be entered at all (treated as removed).
                      Source nodes that are forbidden are skipped.
        default_cost: Cost for nodes absent from ``cost``.
        visit_counter: Optional one-element list; incremented by the number of
                      settled nodes (search effort telemetry). Mutated in place.

    Returns:
        ``(dist, pred)`` where ``dist[node]`` is the minimum path cost to reach
        ``node`` and ``pred[node]`` is its predecessor on that path (``None`` for
        sources). Unreachable nodes are absent from both dicts.
    """
    forbidden = forbidden or set()
    dist: CostMap = {}
    pred: Dict[int, Optional[int]] = {}
    heap: List[Tuple[float, int, int]] = []
    tie = 0  # strictly-increasing tie-breaker → never compares node objects

    for s in sources:
        if s in forbidden:
            continue
        c = cost.get(s, default_cost)
        if s not in dist or c < dist[s]:
            dist[s] = c
            pred[s] = None
            heapq.heappush(heap, (c, tie, s))
            tie += 1

    remaining = set(targets) if targets is not None else None
    settled = 0
    while heap:
        d, _, u = heapq.heappop(heap)
        if d > dist.get(u, _INF):
            continue  # stale heap entry
        settled += 1
        if remaining is not None:
            remaining.discard(u)
            if not remaining:
                break
        for w in adj.get(u, ()):  # adj.get: tolerate qubits filtered from adj
            if w in forbidden:
                continue
            nd = d + cost.get(w, default_cost)
            if nd < dist.get(w, _INF):
                dist[w] = nd
                pred[w] = u
                heapq.heappush(heap, (nd, tie, w))
                tie += 1

    if visit_counter is not None:
        visit_counter[0] += settled
    return dist, pred


def reconstruct_path(pred: Dict[int, Optional[int]], node: int) -> List[int]:
    """Rebuild the path ``[source, ..., node]`` from a Dijkstra predecessor map.

    Returns ``[]`` if ``node`` was never reached (absent from ``pred``).
    """
    if node not in pred:
        return []
    path: List[int] = []
    cur: Optional[int] = node
    while cur is not None:
        path.append(cur)
        cur = pred.get(cur)
    path.reverse()
    return path


def chain_connected(chain: Sequence[int], adj: Adjacency) -> bool:
    """Return True if ``chain`` induces a connected subgraph under ``adj``.

    Singletons and empties are trivially connected. Mirrors the connectivity
    check in :mod:`ember_qc.validation` but operates on a frozen adjacency.
    """
    if len(chain) <= 1:
        return True
    chain_set = set(chain)
    start = chain[0]
    seen = {start}
    stack = [start]
    while stack:
        x = stack.pop()
        for w in adj.get(x, ()):
            if w in chain_set and w not in seen:
                seen.add(w)
                stack.append(w)
    return len(seen) == len(chain_set)


def chain_components(chain: Sequence[int], adj: Adjacency) -> List[List[int]]:
    """Split ``chain`` into its connected components (in deterministic order).

    Components are discovered in the order nodes first appear in ``chain``, so
    the result is reproducible for a fixed input list.
    """
    chain_set = set(chain)
    seen: Set[int] = set()
    comps: List[List[int]] = []
    for start in chain:  # iterate the list (not the set) for determinism
        if start in seen:
            continue
        comp = [start]
        seen.add(start)
        stack = [start]
        while stack:
            x = stack.pop()
            for w in adj.get(x, ()):
                if w in chain_set and w not in seen:
                    seen.add(w)
                    comp.append(w)
                    stack.append(w)
        comps.append(comp)
    return comps


# ==============================================================================
# ROUND → REPAIR
# ==============================================================================

def round_assignment(
    assignment: Dict[int, Dict[int, float]],
    *,
    threshold: float = 0.0,
) -> Embedding:
    """Round a soft qubit→vertex assignment to hard (partial) chains.

    Each qubit is awarded to the source vertex with the largest weight (its
    argmax), provided that weight exceeds ``threshold``; ties break toward the
    lowest source-vertex id for reproducibility. Qubits whose best weight is at
    or below ``threshold`` are left unassigned.

    This is the rounding step shared by the relaxation-based approaches (srGW,
    differentiable soft-assignment): it consumes a coupling / soft-assignment
    matrix expressed row-wise per qubit and emits nascent chains, which
    :func:`grow_to_connected` and :func:`resolve_overlaps` then make valid.

    Args:
        assignment: ``{qubit: {source_vertex: weight}}``. Typically one row of a
                    transport plan / soft-assignment matrix per qubit.
        threshold:  Minimum weight required to assign a qubit at all.

    Returns:
        Partial chains ``{source_vertex: [qubit, ...]}``. Disjoint by
        construction (each qubit appears once) but not necessarily connected.
    """
    chains: Embedding = {}
    for qubit, weights in assignment.items():
        best_src: Optional[int] = None
        best_w = -_INF
        for src, w in sorted(weights.items()):  # sorted → deterministic tie-break
            if w > best_w:
                best_w = w
                best_src = src
        if best_src is None or best_w <= threshold:
            continue
        chains.setdefault(best_src, []).append(qubit)
    return chains


def round_assignment_matrix(
    matrix,
    qubit_nodes: Sequence[int],
    source_nodes: Sequence[int],
    *,
    threshold: float = 0.0,
) -> Embedding:
    """``round_assignment`` for a dense 2-D array indexed ``[qubit, source]``.

    Convenience wrapper for the differentiable / OT approaches whose native
    output is a NumPy / Torch tensor. ``matrix[i, j]`` is the weight of assigning
    ``qubit_nodes[i]`` to ``source_nodes[j]``.
    """
    assignment: Dict[int, Dict[int, float]] = {}
    for i, q in enumerate(qubit_nodes):
        row = matrix[i]
        assignment[q] = {source_nodes[j]: float(row[j]) for j in range(len(source_nodes))}
    return round_assignment(assignment, threshold=threshold)


def grow_to_connected(
    chains: Embedding,
    target: nx.Graph,
    *,
    detour_penalty: float = 1000.0,
    adj: Optional[Adjacency] = None,
) -> Embedding:
    """Expand each chain's support into a connected subgraph of ``target``.

    A rounded assignment gives each vertex a *set* of qubits that need not be
    connected. This stitches every chain's components together with minimum-cost
    paths, preferring qubits that no chain currently claims so the grown chains
    stay as disjoint as possible. Qubits already owned by *another* chain may be
    borrowed as connectors when unavoidable (priced at ``detour_penalty``);
    :func:`resolve_overlaps` cleans up any overlaps that result.

    Args:
        chains:          Partial chains, e.g. from :func:`round_assignment`.
        target:          Hardware graph.
        detour_penalty:  Cost of routing a connector through a qubit owned by a
                         different chain (vs. cost 1 for a free qubit).
        adj:             Optional pre-built adjacency (avoids a rebuild).

    Returns:
        New chains, each connected (where the target permits). Input is not
        mutated.
    """
    if adj is None:
        adj = build_adjacency(target)

    owner: Dict[int, int] = {}
    for v, chain in chains.items():
        for q in chain:
            owner[q] = v

    grown: Embedding = {}
    for v, chain in chains.items():
        if chain_connected(chain, adj):
            grown[v] = list(chain)
            continue

        own = set(chain)
        comps = chain_components(chain, adj)
        # Cost: own qubits and free qubits are cheap (1); qubits owned by another
        # chain are expensive but usable as a last-resort connector.
        cost: CostMap = {
            q: (1.0 if (q not in owner or owner[q] == v) else detour_penalty)
            for q in adj
        }
        merged = set(comps[0])
        for comp in comps[1:]:
            comp_set = set(comp)
            dist, pred = weighted_multisource_dijkstra(
                adj, merged, cost, targets=comp_set
            )
            reachable = [(dist[q], q) for q in comp if q in dist]
            if not reachable:
                # Target is disconnected between these components — keep the
                # component anyway; validation will flag it if it matters.
                merged |= comp_set
                continue
            _, nearest = min(reachable, key=lambda t: (t[0], t[1]))
            path = reconstruct_path(pred, nearest)
            merged.update(path)
            merged |= comp_set
        grown[v] = sorted(merged)
    return grown


def resolve_overlaps(
    chains: Embedding,
    source: nx.Graph,
    target: nx.Graph,
    *,
    max_passes: int = 30,
    seed: Optional[int] = None,
    adj: Optional[Adjacency] = None,
) -> Optional[Embedding]:
    """Rip-up contested qubits until chains are pairwise disjoint, then verify.

    A MM-style legalizer used as a repair / finishing pass by the relaxation
    approaches and as a safety net by Reweave. Each pass:

    1. Finds every **contested** qubit (claimed by more than one chain).
    2. Awards each contested qubit to a single *keeper* — the chain that would be
       left disconnected without it, breaking remaining ties toward the chain
       with the shorter total length (spreading qubits, lowering peak chain
       length) — and rips it from the others.
    3. Reconnects any chain that the rip-up disconnected, routing only through
       currently-free qubits.

    The loop ends when no qubit is contested. The result is returned only if it
    passes structural validation (connected, disjoint, all source edges
    covered); otherwise ``None`` (the caller should fall back, e.g. report
    failure or try more search).

    Args:
        chains:     Possibly overlapping chains.
        source:     Problem graph (for edge-coverage validation).
        target:     Hardware graph.
        max_passes: Iteration bound before giving up.
        seed:       Seeds tie-breaking for reproducibility.
        adj:        Optional pre-built adjacency.

    Returns:
        A valid :data:`Embedding`, or ``None`` if legalization failed.
    """
    if adj is None:
        adj = build_adjacency(target)
    rng = random.Random(seed)
    work: Embedding = {v: list(ch) for v, ch in chains.items()}

    for _ in range(max_passes):
        occ: Dict[int, List[int]] = {}
        for v, chain in work.items():
            for q in chain:
                occ.setdefault(q, []).append(v)
        contested = {q: owners for q, owners in occ.items() if len(owners) > 1}
        if not contested:
            break

        for q, owners in contested.items():
            keeper = _select_keeper(q, owners, work, adj, rng)
            for v in owners:
                if v != keeper:
                    # remove() once — a qubit appears at most once per chain
                    try:
                        work[v].remove(q)
                    except ValueError:
                        pass

        # Reconnect chains damaged by the rip-up, using only free qubits.
        used = {q for chain in work.values() for q in chain}
        for v, chain in work.items():
            if chain and not chain_connected(chain, adj):
                work[v] = _reconnect_chain(v, chain, adj, used)
                used.update(work[v])

    embedding = {int(v): [int(q) for q in chain] for v, chain in work.items()}
    if _is_valid_embedding(embedding, source, adj):
        return embedding
    logger.debug("resolve_overlaps: could not legalize within %d passes", max_passes)
    return None


def is_valid_embedding(
    embedding: Embedding,
    source: nx.Graph,
    target: nx.Graph,
    *,
    adj: Optional[Adjacency] = None,
) -> bool:
    """Public structural validity check: connected, disjoint, edges covered.

    Equivalent to :func:`ember_qc.validation.validate_layer1` returning
    ``passed``, but operating on a frozen adjacency so chain-builders can gate
    "success" cheaply without constructing :class:`ValidationResult` objects.
    """
    if adj is None:
        adj = build_adjacency(target)
    return _is_valid_embedding(embedding, source, adj)


# ------------------------------------------------------------------------------
# Internal helpers
# ------------------------------------------------------------------------------

def _select_keeper(
    qubit: int,
    owners: Sequence[int],
    chains: Embedding,
    adj: Adjacency,
    rng: random.Random,
) -> int:
    """Choose which chain keeps a contested qubit.

    Priority: (1) a chain that becomes disconnected without the qubit keeps it
    (losing it would break a hard invariant); (2) otherwise the shorter chain
    keeps it, which discourages a single chain from hoarding contested qubits
    and lowers peak chain length. Ties break deterministically via ``rng``.
    """
    critical = []
    for v in owners:
        remainder = [q for q in chains[v] if q != qubit]
        if remainder and not chain_connected(remainder, adj):
            critical.append(v)
    pool = critical if critical else list(owners)
    # Shorter chain wins; deterministic jitter from the seeded rng breaks ties.
    return min(pool, key=lambda v: (len(chains[v]), rng.random(), v))


def _reconnect_chain(
    vertex: int,
    chain: Sequence[int],
    adj: Adjacency,
    used: Set[int],
) -> List[int]:
    """Stitch a disconnected chain back together through free qubits only.

    ``used`` is the set of qubits currently claimed by *any* chain (including
    this one). Connectors are drawn from free qubits so the repair introduces no
    new overlaps. If the components cannot be joined through free space the chain
    is returned with whatever could be merged (validation will catch a residual
    break).
    """
    chain_set = set(chain)
    free_or_own = {q for q in adj if q not in used or q in chain_set}
    cost: CostMap = {q: 1.0 for q in free_or_own}
    comps = chain_components(chain, adj)
    merged = set(comps[0])
    for comp in comps[1:]:
        comp_set = set(comp)
        dist, pred = weighted_multisource_dijkstra(
            adj, merged & free_or_own or merged, cost,
            targets=comp_set, forbidden={q for q in adj if q not in free_or_own},
        )
        reachable = [(dist[q], q) for q in comp if q in dist]
        if not reachable:
            merged |= comp_set
            continue
        _, nearest = min(reachable, key=lambda t: (t[0], t[1]))
        merged.update(reconstruct_path(pred, nearest))
        merged |= comp_set
    return sorted(merged)


def _is_valid_embedding(embedding: Embedding, source: nx.Graph, adj: Adjacency) -> bool:
    """Structural validity check (connected, disjoint, edges covered).

    A self-contained mirror of :func:`ember_qc.validation.validate_layer1` that
    runs on the frozen adjacency, so the backend has no import-time dependency on
    the validation module.
    """
    # Coverage + non-empty
    for v in source.nodes():
        if v not in embedding or not embedding[v]:
            return False
    # Disjointness
    seen: Set[int] = set()
    for chain in embedding.values():
        for q in chain:
            if q in seen:
                return False
            seen.add(q)
    # Connectivity
    for chain in embedding.values():
        if not chain_connected(chain, adj):
            return False
    # Edge coverage
    for u, v in source.edges():
        chain_v = set(embedding[v])
        if not any(w in chain_v for q in embedding[u] for w in adj.get(q, ())):
            return False
    return True
