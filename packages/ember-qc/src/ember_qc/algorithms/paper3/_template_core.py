"""
ember_qc/algorithms/paper3/_template_core.py
=============================================
Shared template-embedding core for the paper3 arms (owned by P1/ATE; P2 CLMM
and later arms import from here — keep the public surface additive).

Pieces (see docs/paper3/proposals/ate.md for the spec):

* **busgraph_cache access** — a per-target singleton keyed by busclique's own
  ``topology_identifier()`` (sha256 of the busgraph; stable across instances
  and processes, distinct per broken-qubit variant). Holds the frozen target
  adjacency, K_max, and per-``n`` ordered-template caches.
* **Chain path-ordering** — every busclique clique chain induces a path (or
  near-path) in the target; we order its qubits from an endpoint by walking
  the induced subgraph, so "position along the chain" is well defined.
* **Crossing-position matrix POS** — ``POS[i][j]`` = index within chain *i*'s
  ordered qubits of the first qubit adjacent to chain *j*. The busclique
  crossbar structure guarantees at least one contact per pair; we pick the
  first (deterministic).
* **Prune simulation + assignment** — a pruned path-chain for source vertex
  ``v`` costs ≈ the span of the crossing positions of ``v``'s neighbours
  (min length 1). Assignment pipeline: seed orders {identity, cuthill,
  spectral} scored exactly under this simulator, then deterministic 2-swap
  local search (fixed RNG, proposal-count budget sized to ~the wall cap,
  wall-clock backstop).
* **Template restriction** — relabel the assigned chains to source vertices
  and ``spur_prune`` against the actual source edges (factored/polish.py).

Everything here is deterministic and seed-free by construction (spec: zero
cross-seed variance for the template arm).
"""

from __future__ import annotations

import random
import time
from typing import Dict, List, Optional, Sequence, Tuple

import networkx as nx

from ember_qc.embedding_backend import Adjacency, build_adjacency
from ember_qc.algorithms.factored.polish import spur_prune, shorten_chains
from ember_qc.algorithms.search_orders import (
    cuthill_mckee_order,
    spectral_order,
)

# ──────────────────────────────────────────────────────────────────────────────
# Tunables (as-built defaults; see ate.md "As built")
# ──────────────────────────────────────────────────────────────────────────────

ASSIGN_WALL_CAP_S = 0.100     # spec default: 100 ms wall cap on the 2-swap search
SHORTEN_CAP_S = 0.050         # spec default: ~50 ms deadline for shorten_chains
_ASSIGN_OP_BUDGET = 2_000_000  # deterministic primary budget (ops model ≈ wall cap)
_ASSIGN_MIN_PROPOSALS = 200
_ASSIGN_MAX_PROPOSALS = 20_000
_ASSIGN_RNG_SEED = 0xA7E      # fixed: the template arm never consumes the run seed
_WALL_CHECK_EVERY = 32        # proposals between wall-clock backstop checks

_SEED_ORDER_NAMES = ("identity", "cuthill", "spectral")  # tie-break priority


# ──────────────────────────────────────────────────────────────────────────────
# Per-target singleton, keyed by busclique's topology_identifier()
# ──────────────────────────────────────────────────────────────────────────────

class TargetState:
    """Frozen per-target context: busgraph_cache + adjacency + template caches."""

    __slots__ = ("bgc", "tid", "adj", "kmax", "templates")

    def __init__(self, bgc, tid: str, adj: Adjacency, kmax: int):
        self.bgc = bgc
        self.tid = tid
        self.adj = adj
        self.kmax = kmax
        # n -> (ordered_chains, POS); populated lazily by ordered_template()
        self.templates: Dict[int, Tuple[List[List[int]], List[List[int]]]] = {}


_TARGET_STATES: Dict[str, TargetState] = {}


def get_target_state(target: nx.Graph) -> Optional[TargetState]:
    """Return the (cached) TargetState for ``target``, or None if busclique
    cannot handle it (non-Chimera/Pegasus/Zephyr targets raise inside
    ``busgraph_cache``; we return None so callers fail cleanly).

    Construction of ``busgraph_cache`` itself is cheap (~14 ms on P16, disk
    cache warm); the singleton exists so the adjacency, K_max, and ordered
    templates are computed once per topology per process.
    """
    try:
        from minorminer.busclique import busgraph_cache
        bgc = busgraph_cache(target)
        tid = bgc.topology_identifier()
    except Exception:
        return None
    state = _TARGET_STATES.get(tid)
    if state is not None:
        return state
    try:
        kmax = len(bgc.largest_clique())
    except Exception:
        return None
    state = TargetState(bgc, tid, build_adjacency(target), kmax)
    _TARGET_STATES[tid] = state
    return state


# ──────────────────────────────────────────────────────────────────────────────
# Chain path-ordering
# ──────────────────────────────────────────────────────────────────────────────

def order_chain_qubits(chain: Sequence[int], adj: Adjacency) -> List[int]:
    """Order a chain's qubits along the path it induces in the target.

    Busclique clique chains induce a path (verified empirically on chimera,
    pegasus, zephyr) or a near-path (path + chord). Start from a min-induced-
    degree endpoint (smallest label on ties) and greedily walk to the
    unvisited induced-neighbour with the fewest unvisited neighbours
    (degree-2 corridor first; smallest label on ties). Deterministic; any
    stranded qubits (disconnected chain — never for busclique templates) are
    appended in sorted order.
    """
    qubits = sorted(int(q) for q in chain)
    if len(qubits) <= 1:
        return qubits
    qset = set(qubits)
    nbrs = {q: [w for w in adj.get(q, ()) if w in qset] for q in qubits}
    start = min(qubits, key=lambda q: (len(nbrs[q]), q))
    order = [start]
    seen = {start}
    cur = start
    while len(order) < len(qubits):
        cands = [w for w in nbrs[cur] if w not in seen]
        if not cands:
            break  # stranded remainder handled below
        nxt = min(cands, key=lambda w: (sum(1 for x in nbrs[w] if x not in seen), w))
        order.append(nxt)
        seen.add(nxt)
        cur = nxt
    if len(order) < len(qubits):
        order.extend(q for q in qubits if q not in seen)
    return order


# ──────────────────────────────────────────────────────────────────────────────
# Crossing-position matrix
# ──────────────────────────────────────────────────────────────────────────────

def crossing_position_matrix(
    ordered_chains: Sequence[Sequence[int]], adj: Adjacency
) -> List[List[int]]:
    """POS[i][j] = index in chain i's ordered qubits of the first qubit
    target-adjacent to any qubit of chain j (POS[i][i] = 0, unused; -1 if no
    contact — never the case for a busclique clique template)."""
    n = len(ordered_chains)
    owner: Dict[int, int] = {}
    for j, chain in enumerate(ordered_chains):
        for q in chain:
            owner[q] = j
    pos = [[-1] * n for _ in range(n)]
    for i, chain in enumerate(ordered_chains):
        row = pos[i]
        row[i] = 0
        for k, q in enumerate(chain):
            for w in adj.get(q, ()):
                j = owner.get(w)
                if j is not None and j != i and row[j] < 0:
                    row[j] = k
    return pos


def ordered_template(
    state: TargetState, n: int
) -> Optional[Tuple[List[List[int]], List[List[int]]]]:
    """(ordered chains, POS) for the right-sized K_n template on this target,
    cached per (topology, n). None if n exceeds K_max / busclique fails, or if
    any chain pair lacks a contact (template unusable for the simulator)."""
    if n < 1 or n > state.kmax:
        return None
    hit = state.templates.get(n)
    if hit is not None:
        return hit
    try:
        raw = state.bgc.find_clique_embedding(n)
    except Exception:
        return None
    if not raw or len(raw) < n:
        return None
    chains = [order_chain_qubits(raw[key], state.adj) for key in sorted(raw)]
    pos = crossing_position_matrix(chains, state.adj)
    for i, row in enumerate(pos):
        for j, val in enumerate(row):
            if val < 0 and i != j:
                return None
    state.templates[n] = (chains, pos)
    return chains, pos


# ──────────────────────────────────────────────────────────────────────────────
# Prune simulation (span objective)
# ──────────────────────────────────────────────────────────────────────────────

def simulate_pruned_lengths(
    slots: Sequence[int],
    nbr_idx: Sequence[Sequence[int]],
    pos: Sequence[Sequence[int]],
) -> List[int]:
    """Simulated post-prune chain length for every source vertex index.

    Vertex i sits on chain ``slots[i]``; its pruned path-chain must retain the
    first-contact position with each neighbour's chain, so its length ≈
    max−min+1 over those positions (1 for isolated vertices — spur_prune
    always keeps one qubit). Exact under: path chains, single contact per
    pair, first-contact retention; see ate.md for measured mismatch.
    """
    out = []
    for i, nbrs in enumerate(nbr_idx):
        if not nbrs:
            out.append(1)
            continue
        row = pos[slots[i]]
        lo = hi = row[slots[nbrs[0]]]
        for j in nbrs[1:]:
            p = row[slots[j]]
            if p < lo:
                lo = p
            elif p > hi:
                hi = p
        out.append(hi - lo + 1)
    return out


def simulate_objective(
    slots: Sequence[int],
    nbr_idx: Sequence[Sequence[int]],
    pos: Sequence[Sequence[int]],
) -> int:
    """Total simulated pruned length (the span objective)."""
    return sum(simulate_pruned_lengths(slots, nbr_idx, pos))


# ──────────────────────────────────────────────────────────────────────────────
# Assignment: seed orders + deterministic 2-swap local search
# ──────────────────────────────────────────────────────────────────────────────

def _sorted_nodes(G: nx.Graph) -> List:
    try:
        return sorted(G.nodes())
    except TypeError:  # mixed-type labels: fall back to a stable repr order
        return sorted(G.nodes(), key=repr)


def _seed_orders(G: nx.Graph, verts: List) -> List[Tuple[str, List]]:
    """The three seed vertex orders, as (name, order) in tie-break priority."""
    orders: List[Tuple[str, List]] = [("identity", list(verts))]
    try:
        orders.append(("cuthill", list(cuthill_mckee_order(G))))
    except Exception:
        pass
    try:
        orders.append(("spectral", list(spectral_order(G))))
    except Exception:
        pass
    return orders


def two_swap_refine(
    slots: List[int],
    nbr_idx: Sequence[Sequence[int]],
    pos: Sequence[Sequence[int]],
    *,
    wall_cap_s: float = ASSIGN_WALL_CAP_S,
    op_budget: int = _ASSIGN_OP_BUDGET,
) -> Tuple[List[int], int, Dict]:
    """Deterministic 2-swap local search on the span objective.

    Proposals are random vertex pairs from a FIXED RNG (seed-independent).
    The primary budget is a deterministic proposal count derived from an
    operation-cost model sized to ≈``wall_cap_s`` on this class of machine;
    the wall clock is a backstop only (checked every few proposals), so
    repeated calls on the same inputs give identical output unless the
    machine is far slower than the model.

    Returns (slots, objective, info).
    """
    n = len(slots)
    slots = list(slots)
    lengths = simulate_pruned_lengths(slots, nbr_idx, pos)
    total = sum(lengths)
    info = {"proposals": 0, "accepted": 0, "capped_by": "converged"}
    if n < 2:
        return slots, total, info

    # Deterministic proposal budget from the op-cost model: each proposal
    # touches {a,b} ∪ N(a) ∪ N(b) and recomputes each affected span twice.
    avg_deg = sum(len(x) for x in nbr_idx) / n
    per_prop = max(8.0, 2.0 * (2.0 + 2.0 * avg_deg) * max(1.0, avg_deg))
    budget = int(op_budget * (wall_cap_s / ASSIGN_WALL_CAP_S) / per_prop)
    budget = max(_ASSIGN_MIN_PROPOSALS, min(_ASSIGN_MAX_PROPOSALS, budget))

    rng = random.Random(_ASSIGN_RNG_SEED)
    deadline = time.perf_counter() + max(0.005, wall_cap_s)
    floor = n  # every simulated length is >= 1
    consecutive_rejects = 0
    max_rejects = max(_ASSIGN_MIN_PROPOSALS, 4 * n)

    for it in range(budget):
        if (it % _WALL_CHECK_EVERY) == 0 and time.perf_counter() > deadline:
            info["capped_by"] = "wall_clock"
            break
        if total <= floor:
            info["capped_by"] = "floor"
            break
        if consecutive_rejects >= max_rejects:
            info["capped_by"] = "converged"
            break
        a = rng.randrange(n)
        b = rng.randrange(n - 1)
        if b >= a:
            b += 1
        info["proposals"] += 1
        affected = {a, b}
        affected.update(nbr_idx[a])
        affected.update(nbr_idx[b])
        old = sum(lengths[w] for w in affected)
        slots[a], slots[b] = slots[b], slots[a]
        new_lengths = {}
        new = 0
        for w in affected:
            nbrs = nbr_idx[w]
            if not nbrs:
                lw = 1
            else:
                row = pos[slots[w]]
                lo = hi = row[slots[nbrs[0]]]
                for j in nbrs[1:]:
                    p = row[slots[j]]
                    if p < lo:
                        lo = p
                    elif p > hi:
                        hi = p
                lw = hi - lo + 1
            new_lengths[w] = lw
            new += lw
        if new < old:
            for w, lw in new_lengths.items():
                lengths[w] = lw
            total += new - old
            info["accepted"] += 1
            consecutive_rejects = 0
        else:
            slots[a], slots[b] = slots[b], slots[a]
            consecutive_rejects += 1
    else:
        info["capped_by"] = "op_budget"
    return slots, total, info


def assign_slots(
    G: nx.Graph,
    verts: List,
    pos: Sequence[Sequence[int]],
    *,
    wall_cap_s: float = ASSIGN_WALL_CAP_S,
    refine: bool = True,
) -> Tuple[List[int], Dict]:
    """Full assignment pipeline: seed orders scored exactly under the prune
    simulator, then 2-swap refinement of the best seed.

    Returns (slots, info): ``slots[i]`` is the template-chain slot of the i-th
    vertex of ``verts``. For complete sources every bijection has an identical
    objective (chains are interchangeable under the simulator), so scoring and
    refinement are skipped (exact fast path, not an approximation).
    """
    n = len(verts)
    vidx = {v: i for i, v in enumerate(verts)}
    nbr_idx: List[List[int]] = [
        [vidx[u] for u in G.neighbors(v) if u != v] for v in verts
    ]
    m2 = sum(len(x) for x in nbr_idx)
    info: Dict = {"n": n}
    if n and m2 == n * (n - 1):  # complete source: objective is assignment-invariant
        slots = list(range(n))
        info.update(seed_order="identity", obj_seed=simulate_objective(slots, nbr_idx, pos),
                    obj_final=None, complete_skip=True)
        info["obj_final"] = info["obj_seed"]
        return slots, info

    best_name, best_slots, best_obj = None, None, None
    for name, order in _seed_orders(G, verts):
        slots = [0] * n
        ok = len(order) == n
        if ok:
            try:
                for k, v in enumerate(order):
                    slots[vidx[v]] = k
            except KeyError:
                ok = False
        if not ok:
            continue
        obj = simulate_objective(slots, nbr_idx, pos)
        if best_obj is None or obj < best_obj:
            best_name, best_slots, best_obj = name, slots, obj
    if best_slots is None:  # all seed orders failed (cannot happen: identity always works)
        best_name, best_slots = "identity", list(range(n))
        best_obj = simulate_objective(best_slots, nbr_idx, pos)

    info.update(seed_order=best_name, obj_seed=best_obj, complete_skip=False)
    if refine:
        best_slots, best_obj, ls_info = two_swap_refine(
            best_slots, nbr_idx, pos, wall_cap_s=wall_cap_s)
        info["local_search"] = ls_info
    info["obj_final"] = best_obj
    return best_slots, info


# ──────────────────────────────────────────────────────────────────────────────
# Template restriction
# ──────────────────────────────────────────────────────────────────────────────

def restrict_template(
    G: nx.Graph,
    verts: List,
    slots: Sequence[int],
    chains: Sequence[Sequence[int]],
    adj: Adjacency,
    *,
    deadline: Optional[float] = None,
) -> Dict[int, List[int]]:
    """Relabel the assigned template chains to source vertices and spur_prune
    against the actual source edges. Works in vertex-index space (0..n-1) so
    arbitrary hashable source labels survive; returns index-keyed chains."""
    vidx = {v: i for i, v in enumerate(verts)}
    emb = {i: list(chains[slots[i]]) for i in range(len(verts))}
    src_adj = {
        i: sorted(vidx[u] for u in G.neighbors(v) if u != v)
        for i, v in enumerate(verts)
    }
    return spur_prune(emb, src_adj, adj, deadline=deadline)


def template_embed(
    G: nx.Graph,
    state: TargetState,
    *,
    deadline: float,
    assign_wall_cap_s: float = ASSIGN_WALL_CAP_S,
    shorten_cap_s: float = SHORTEN_CAP_S,
    refine: bool = True,
    shorten: bool = True,
) -> Tuple[Optional[Dict], Dict]:
    """The full direct template pipeline for n <= K_max (ate.md Mechanism):
    find_clique_embedding(n) -> assign -> restrict -> spur_prune ->
    deadline-bounded shorten_chains.

    ``deadline`` is a perf_counter timestamp bounding the whole pipeline;
    stages that do not fit are skipped (prune/shorten are safe to cut short).
    Returns (embedding keyed by source vertex | None, info dict). Fully
    deterministic; never consumes the run seed.
    """
    info: Dict = {"mode": "direct"}
    n = G.number_of_nodes()
    if n == 0 or n > state.kmax:
        info["err"] = f"n={n} outside (0, K_max={state.kmax}]"
        return None, info
    tpl = ordered_template(state, n)
    if tpl is None:
        info["err"] = "busclique template unavailable"
        return None, info
    chains, pos = tpl
    verts = _sorted_nodes(G)

    remaining = deadline - time.perf_counter()
    if remaining <= 0.001:
        info["err"] = "no time for assignment"
        return None, info
    cap = min(assign_wall_cap_s, 0.5 * remaining)
    slots, assign_info = assign_slots(G, verts, pos, wall_cap_s=cap, refine=refine)
    info["assign"] = assign_info

    emb_idx = restrict_template(G, verts, slots, chains, state.adj,
                                deadline=deadline)
    info["acl_pruned"] = sum(len(c) for c in emb_idx.values()) / n

    if shorten:
        now = time.perf_counter()
        budget = min(shorten_cap_s, deadline - now)
        if budget > 0.002:
            vidx = {v: i for i, v in enumerate(verts)}
            src_adj = {
                i: sorted(vidx[u] for u in G.neighbors(v) if u != v)
                for i, v in enumerate(verts)
            }
            emb_idx = shorten_chains(emb_idx, src_adj, state.adj,
                                     deadline=now + budget)
            info["acl_shortened"] = sum(len(c) for c in emb_idx.values()) / n

    embedding = {verts[i]: [int(q) for q in c] for i, c in emb_idx.items()}
    return embedding, info


# ──────────────────────────────────────────────────────────────────────────────
# Degeneracy peel (core selection for n > K_max)
# ──────────────────────────────────────────────────────────────────────────────

def degeneracy_core(G: nx.Graph, k: int) -> List:
    """The k vertices remaining after peeling minimum-degree vertices until k
    are left (== the last-k suffix of the degeneracy elimination order).
    Deterministic (min (degree, label) peel). Returns sorted labels."""
    verts = _sorted_nodes(G)
    if k >= len(verts):
        return verts
    adjs = {v: set(u for u in G.neighbors(v) if u != v) for v in verts}
    deg = {v: len(adjs[v]) for v in verts}
    remaining = set(verts)
    for _ in range(len(verts) - k):
        v = min(remaining, key=lambda u: (deg[u], repr(u)))
        remaining.discard(v)
        for w in adjs[v]:
            if w in remaining:
                deg[w] -= 1
    return sorted(remaining, key=repr) if any(
        not isinstance(v, int) for v in remaining) else sorted(remaining)
