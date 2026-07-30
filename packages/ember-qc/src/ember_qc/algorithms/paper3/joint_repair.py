"""
ember_qc/algorithms/paper3/joint_repair.py
===========================================
P5 — symmetric polish + move-set completeness (docs/paper3/proposals/polish.md).

Exact, bounded-region chain repairs on a *valid* embedding, and the anytime
polish loop that schedules them:

* :func:`exact_repair_1` — rip one vertex's chain and re-embed it *optimally*
  within a bounded region (freed qubits + a free halo), every neighbour chain
  pinned. This is the single-vertex exact operator that carried all of
  lns-cpsat's measured gain on the abandoned branch
  (``new-algorithm:.../algorithms/lns_cpsat.py``), re-implemented with plain
  branch-and-bound instead of CP-SAT (no ortools dependency; same optimum,
  deterministic, deadline-safe).
* :func:`joint_repair_2` — NEW move class: rip a source-adjacent pair whose
  chains touch and re-embed BOTH jointly (minimum total qubits), boundary
  pinned. Probes the joint-move blindness measured in paper2 notes §3.26.
* :func:`anytime_polish` — dirty-set scheduled loop (schedule ported from
  ``new-algorithm:docs/candidate-algorithms/reweave-improvements/dirtyset.md``)
  over {spur_prune, shorten_chains, exact_repair_1, joint_repair_2};
  longest-first, deterministic, deadline-bounded, monotone non-worsening.

Registered arm: ``p3-mmpolish`` — stock minorminer (~70 % of the budget,
source passed as a GRAPH OBJECT) + ``anytime_polish`` for the rest.

Exactness semantics (mirrored in polish.md "as built")
------------------------------------------------------
Each repair is *exact within its region*. The region is the ripped chains'
qubits (always all of them, so the incumbent is always feasible and a repair
can never worsen) plus every currently-free qubit within a BFS ball of
``radius`` hops of them. The ball is taken over the FULL target adjacency and
then intersected with free fabric — so free pockets that sit just behind a
pinned chain are visible (a singleton chain there needs adjacency, not a
path); cf. ``new-algorithm:.../rw_bounded.py``'s ball. The region is capped at
``region_cap`` qubits (free halo qubits kept in (BFS-depth, id) order).

The optimisation problem is: minimum connected subgraph of the region that
touches every pinned neighbour chain's *contact set* (region qubits adjacent
to that chain) — for the pair, two disjoint connected subgraphs, each covering
its own vertex's contact sets (their union is then automatically connected and
the two halves adjacent, which covers the ripped source edge). It is solved by
duplicate-free connected-subgraph enumeration (ESU-style, min-id rooting) with
an admissible bound (max BFS-distance-to-uncovered-group, and a
disjoint-witness counting bound), incumbent-tightened. When the search
completes within its node cap and deadline the result is **proven** minimum
within the region (``proven=True``); when a cap fires, the best incumbent
found so far is used and the outcome is labelled unproven. Acceptance is
always "strictly fewer total qubits AND full structural validity"
(:func:`ember_qc.embedding_backend.is_valid_embedding`), so every path is
validity-preserving and monotone.
"""

from __future__ import annotations

import logging
import time
from typing import Dict, List, NamedTuple, Optional, Sequence, Set, Tuple

import networkx as nx

from ember_qc.registry import EmbeddingAlgorithm, register_algorithm
from ember_qc.embedding_backend import (
    Adjacency,
    Embedding,
    build_adjacency,
    is_valid_embedding,
)
from ember_qc.algorithms.factored.polish import spur_prune, shorten_chains

logger = logging.getLogger(__name__)

SrcAdj = Dict[int, List[int]]

# ── Tuning constants (defaults; all overridable per call) ─────────────────────
DEFAULT_RADIUS = 2        # BFS-ball radius of the free halo around ripped chains
REGION_CAP = 350          # max qubits in a repair region
X1_NODE_CAP = 150_000     # search-node cap for a single-vertex repair
X2_NODE_CAP = 400_000     # search-node cap for a joint pair repair
X1_MOVE_S = 1.5           # per-move wall cap inside anytime_polish (x1)
X2_MOVE_S = 3.0           # per-move wall cap inside anytime_polish (x2)
_SPLIT_MAX_T = 22         # |U| ceiling for the exact split check (2^22 = 4.2M
                          # subsets ~ tens of ms-seconds); larger candidates are
                          # unproven skips — v1.1.1 C16 runaway fix (§4.12)


class RepairOutcome(NamedTuple):
    """Result of one exact repair attempt.

    ``embedding`` is the full improved embedding when ``improved`` (a fresh
    dict; the input is never mutated) and ``None`` otherwise. ``proven`` means
    the bounded search ran to completion, so the outcome is exact *within the
    region*: an improvement is region-minimum, a non-improvement means no
    strictly smaller re-embedding exists in the region.
    """

    embedding: Optional[Embedding]
    improved: bool
    proven: bool
    old_total: int
    new_total: int
    region_size: int
    nodes: int


# ══════════════════════════════════════════════════════════════════════════════
# Region construction
# ══════════════════════════════════════════════════════════════════════════════

def _region_qubits(adj: Adjacency, embedding: Embedding, ripped: Sequence[int],
                   radius: int, region_cap: int) -> List[int]:
    """Freed qubits + free halo, deterministic, capped.

    Freed = the ripped vertices' chain qubits (ALWAYS all included — the
    incumbent must stay feasible). Halo = free qubits (used by no pinned
    chain) within ``radius`` BFS hops of the freed set, ball taken over the
    full adjacency (see module docstring), appended ring by ring in
    (depth, id) order until ``region_cap``.
    """
    ripped_set = set(ripped)
    freed = sorted({int(q) for v in ripped_set for q in embedding[v]})
    used_pinned: Set[int] = {
        q for v, c in embedding.items() if v not in ripped_set for q in c
    }
    region: List[int] = list(freed)
    seen: Set[int] = set(freed)
    frontier = freed
    for _ in range(max(0, int(radius))):
        ring: List[int] = []
        for q in frontier:
            for w in adj.get(q, ()):
                if w not in seen:
                    seen.add(w)
                    ring.append(w)
        ring.sort()
        for q in ring:
            if q not in used_pinned and len(region) < region_cap:
                region.append(q)
        frontier = ring
        if not ring:
            break
    return sorted(region)


def _contact_masks(pinned: Sequence[int], embedding: Embedding,
                   adj: Adjacency, index: Dict[int, int]) -> Dict[int, int]:
    """Per pinned neighbour ``h``: bitmask (over region indices) of region
    qubits target-adjacent to ``h``'s chain."""
    masks: Dict[int, int] = {}
    for h in pinned:
        m = 0
        for q in embedding[h]:
            for w in adj.get(q, ()):
                i = index.get(w)
                if i is not None:
                    m |= 1 << i
        masks[h] = m
    return masks


def _reduce_groups(groups: List[Tuple[int, int]]) -> List[Tuple[int, int]]:
    """Dedupe coverage groups and drop dominated ones.

    A group is ``(mask, req)``: the solution must contain at least ``req``
    qubits of ``mask``. ``g2`` is redundant when some other ``g1`` has
    ``mask1 ⊆ mask2`` and ``req1 >= req2`` (satisfying g1 then implies g2).
    Deterministic output order: (popcount, mask).
    """
    merged: Dict[int, int] = {}
    for mask, req in groups:
        merged[mask] = max(merged.get(mask, 0), req)
    items = sorted(merged.items(), key=lambda t: (bin(t[0]).count("1"), t[0]))
    kept: List[Tuple[int, int]] = []
    for mask, req in items:
        dominated = any(
            (m1 & ~mask) == 0 and r1 >= req and (m1, r1) != (mask, req)
            for m1, r1 in kept
        )
        if not dominated:
            kept.append((mask, req))
    return kept


# ══════════════════════════════════════════════════════════════════════════════
# The exact engine: minimum connected (multi-)cover by branch-and-bound
# ══════════════════════════════════════════════════════════════════════════════

class _StopSearch(Exception):
    """Node cap or deadline fired — unwind with the best incumbent so far."""


def _mask_connected(mask: int, nbr: List[int]) -> bool:
    """Is the set of bits in ``mask`` connected under bit-adjacency ``nbr``?"""
    if mask == 0:
        return False
    start = mask & -mask
    seen = start
    frontier = start
    while frontier:
        nxt = 0
        m = frontier
        while m:
            b = m & -m
            m ^= b
            nxt |= nbr[b.bit_length() - 1]
        nxt &= mask & ~seen
        seen |= nxt
        frontier = nxt
    return seen == mask


class _CoverSearch:
    """Minimum connected subgraph of a small region hitting every group.

    Two modes:

    * **single** (``split=None``): find the minimum connected vertex set S
      with ``|S & mask_g| >= req_g`` for every group g. Used by
      :func:`exact_repair_1` (the chain itself).
    * **pair** (``split=(gu, gv)``): enumerate connected candidate unions U
      satisfying the merged group requirements (a *necessary* relaxation),
      and accept U only if it splits into two disjoint connected halves, the
      first covering every mask in ``gu``, the second every mask in ``gv``
      (:meth:`_find_split` — the exact side condition). Used by
      :func:`joint_repair_2`.

    Enumeration is ESU-style (min-index rooting + once-only extension lists),
    so every connected vertex set is visited at most once. ``best_size`` is
    seeded with the incumbent total, so only strictly smaller solutions are
    ever recorded, and the bound tightens as solutions are found. Everything
    is deterministic: indices are region-sorted, loops are ordered.
    """

    def __init__(self, nbr_idx: List[List[int]],
                 groups: List[Tuple[int, int]], incumbent_size: int,
                 deadline: Optional[float], node_cap: int,
                 split: Optional[Tuple[List[int], List[int]]] = None,
                 min_size: int = 1,
                 dist_to_group: Optional[List[List[int]]] = None):
        self.nbr_idx = nbr_idx
        self.groups = groups
        self.masks = [m for m, _ in groups]
        self.reqs = [r for _, r in groups]
        self.k = len(groups)
        self.best_size = incumbent_size          # strictly-better only
        self.best: Optional[List[int]] = None    # single mode
        self.best_split: Optional[Tuple[List[int], List[int]]] = None
        self.deadline = deadline
        self.node_cap = int(node_cap)
        self.split = split
        self.min_size = min_size
        self.nodes = 0
        self.proven = True
        self.dist = dist_to_group or []          # dist[g][i] = BFS hops i -> g
        self._inf = len(nbr_idx) + 1

    # ------------------------------------------------------------- bounds -----

    def _bound(self, size: int, s_mask: int, hits: List[int],
               dmin: List[int]) -> int:
        """Admissible lower bound on the FINAL size of any completion of S."""
        h_dist = 0
        deficits: List[int] = []
        for g in range(self.k):
            deficit = self.reqs[g] - hits[g]
            if deficit <= 0:
                continue
            avail = bin(self.masks[g] & ~s_mask).count("1")
            if avail < deficit:
                return self._inf + size          # infeasible completion
            if hits[g] == 0:
                d = dmin[g]
                h_g = d + (deficit - 1)          # reach group, then extra hits
            else:
                h_g = deficit                    # >=1 new node per missing hit
            if h_g > h_dist:
                h_dist = h_g
            deficits.append(g)
        if not deficits:
            return size
        # Disjoint-witness counting bound: groups with pairwise-disjoint
        # remaining members need distinct new nodes — sum their deficits.
        h_disj = 0
        if len(deficits) > 1:
            taken = 0
            rem = sorted(
                ((bin(self.masks[g] & ~s_mask).count("1"),
                  self.masks[g] & ~s_mask, self.reqs[g] - hits[g])
                 for g in deficits))
            for _, m, deficit in rem:
                if m & taken == 0:
                    taken |= m
                    h_disj += deficit
        return size + max(h_dist, h_disj)

    # ------------------------------------------------------------- search -----

    def run(self) -> None:
        n = len(self.nbr_idx)
        try:
            for root in range(n):
                # Root-level prune: any completion rooted here needs >= bound.
                hits = [1 if self.masks[g] >> root & 1 else 0
                        for g in range(self.k)]
                dmin = [self.dist[g][root] for g in range(self.k)]
                if self._bound(1, 1 << root, hits, dmin) > self.best_size - 1:
                    continue
                ext = [w for w in self.nbr_idx[root] if w > root]
                self._extend([root], 1 << root, ext, 0, hits, dmin)
        except _StopSearch:
            self.proven = False

    def _tick(self) -> None:
        self.nodes += 1
        if self.nodes > self.node_cap:
            raise _StopSearch
        if (self.deadline is not None and (self.nodes & 0xFF) == 0
                and time.perf_counter() > self.deadline):
            raise _StopSearch

    def _candidate(self, s_list: List[int], s_mask: int,
                   hits: List[int]) -> bool:
        """Record S if it satisfies every requirement. Returns covered?"""
        for g in range(self.k):
            if hits[g] < self.reqs[g]:
                return False
        if len(s_list) < self.min_size or len(s_list) >= self.best_size:
            return True                # covered but too small / not stricter
        if self.split is None:
            self.best_size = len(s_list)
            self.best = list(s_list)
            return True
        found = self._find_split(s_list)
        if found is not None:
            self.best_size = len(s_list)
            self.best_split = found
        return True

    def _find_split(self, s_list: List[int]
                    ) -> Optional[Tuple[List[int], List[int]]]:
        """Exact side condition for pair mode: partition U into two disjoint,
        connected, nonempty halves covering gu / gv respectively.

        U is connected, so any such partition automatically has an edge
        between the halves (the ripped source edge's coupler). Iterates the
        2^|U| ordered subsets ascending (deterministic first hit); coverage
        masks are checked before the connectivity BFS.

        BUDGET (v1.1.1, the C16 runaway fix — notes §4.12): the subset loop
        previously ran without deadline/cap checks; on long-chain fabrics
        (Chimera degree 6) candidates reach |U| = 25-40, i.e. 2^30-2^40
        subsets, which turned a "3 s" move into hours. Now: candidates with
        |U| > _SPLIT_MAX_T are skipped as unproven, and the loop ticks the
        shared node/deadline accounting every 4096 subsets (raising
        _StopSearch on expiry, same semantics as the enumeration phase).
        """
        gu, gv = self.split
        t = len(s_list)
        if t > _SPLIT_MAX_T:                 # 2^t infeasible — unproven skip
            self.proven = False
            return None
        pos = {q: i for i, q in enumerate(s_list)}
        local_nbr = [0] * t
        for i, q in enumerate(s_list):
            m = 0
            for w in self.nbr_idx[q]:
                j = pos.get(w)
                if j is not None:
                    m |= 1 << j
            local_nbr[i] = m
        gu_local = []
        for gm in gu:
            lm = 0
            for i, q in enumerate(s_list):
                if gm >> q & 1:
                    lm |= 1 << i
            if lm == 0:
                return None
            gu_local.append(lm)
        gv_local = []
        for gm in gv:
            lm = 0
            for i, q in enumerate(s_list):
                if gm >> q & 1:
                    lm |= 1 << i
            if lm == 0:
                return None
            gv_local.append(lm)
        full = (1 << t) - 1
        for a in range(1, full):
            if (a & 0xFFF) == 0:             # tick every 4096 subsets
                self._tick()
            b = full ^ a
            if any(a & lm == 0 for lm in gu_local):
                continue
            if any(b & lm == 0 for lm in gv_local):
                continue
            if not _mask_connected(a, local_nbr):
                continue
            if not _mask_connected(b, local_nbr):
                continue
            part_u = [s_list[i] for i in range(t) if a >> i & 1]
            part_v = [s_list[i] for i in range(t) if b >> i & 1]
            return part_u, part_v
        return None

    def _extend(self, s_list: List[int], s_mask: int, ext: List[int],
                excl_mask: int, hits: List[int], dmin: List[int]) -> None:
        """Branch on the ordered extension list.

        Branch i takes ``ext[i]`` with every earlier entry excluded forever in
        that subtree (``excl_mask`` accumulates the skips), which makes the
        enumeration duplicate-free: each connected set whose minimum index is
        the root is generated by exactly one include/skip decision sequence.
        """
        self._tick()
        covered = self._candidate(s_list, s_mask, hits)
        if covered and self.split is None:
            return                                # supersets are never better
        # In pair mode a covered-but-unsplittable U may still split after
        # growing, so extension continues either way.
        if len(s_list) + 1 > self.best_size - 1:
            return
        root = s_list[0]
        ext_bits = 0
        for e in ext:
            ext_bits |= 1 << e
        skipped = 0
        for i, w in enumerate(ext):
            wbit = 1 << w
            new_hits = list(hits)
            new_dmin = list(dmin)
            for g in range(self.k):
                if self.masks[g] & wbit:
                    new_hits[g] += 1
                d = self.dist[g][w]
                if d < new_dmin[g]:
                    new_dmin[g] = d
            new_mask = s_mask | wbit
            if self._bound(len(s_list) + 1, new_mask, new_hits,
                           new_dmin) <= self.best_size - 1:
                blocked = s_mask | ext_bits | excl_mask
                new_ext = list(ext[i + 1:])
                for u in self.nbr_idx[w]:
                    if u > root and not (blocked >> u & 1):
                        new_ext.append(u)
                s_list.append(w)
                self._extend(s_list, new_mask, new_ext, excl_mask | skipped,
                             new_hits, new_dmin)
                s_list.pop()
            skipped |= wbit


def _group_distances(nbr_idx: List[List[int]],
                     masks: List[int]) -> List[List[int]]:
    """dist[g][i] = BFS hop count from region-index i to group g's nearest
    member (0 if i is a member; n+1 sentinel if unreachable)."""
    n = len(nbr_idx)
    inf = n + 1
    out: List[List[int]] = []
    for gm in masks:
        dist = [inf] * n
        frontier = [i for i in range(n) if gm >> i & 1]
        for i in frontier:
            dist[i] = 0
        d = 0
        while frontier:
            d += 1
            nxt = []
            for i in frontier:
                for w in nbr_idx[i]:
                    if dist[w] > d:
                        dist[w] = d
                        nxt.append(w)
            frontier = nxt
        out.append(dist)
    return out


# ══════════════════════════════════════════════════════════════════════════════
# The repair operators
# ══════════════════════════════════════════════════════════════════════════════

def _region_setup(embedding: Embedding, source: nx.Graph, adj: Adjacency,
                  ripped: Sequence[int], radius: int, region_cap: int):
    """Shared plumbing: region, index maps, per-ripped-vertex pinned contact
    masks. Returns ``None`` if some pinned neighbour has an empty contact set
    (cannot happen for a valid input embedding — defensive)."""
    region = _region_qubits(adj, embedding, ripped, radius, region_cap)
    index = {q: i for i, q in enumerate(region)}
    nbr_idx: List[List[int]] = []
    for q in region:
        row = [index[w] for w in adj.get(q, ()) if w in index]
        row.sort()
        nbr_idx.append(row)
    ripped_set = set(ripped)
    contacts: Dict[int, Dict[int, int]] = {}
    for v in ripped:
        pinned = sorted(int(u) for u in source.neighbors(v)
                        if int(u) not in ripped_set and embedding.get(int(u)))
        cm = _contact_masks(pinned, embedding, adj, index)
        if any(m == 0 for m in cm.values()):
            return None
        contacts[v] = cm
    return region, nbr_idx, contacts


def exact_repair_1(embedding: Embedding, source: nx.Graph, target: nx.Graph,
                   v: int, radius: int = DEFAULT_RADIUS,
                   deadline: Optional[float] = None, *,
                   adj: Optional[Adjacency] = None,
                   node_cap: int = X1_NODE_CAP,
                   region_cap: int = REGION_CAP) -> RepairOutcome:
    """Rip ``v``'s chain and re-embed it region-optimally, neighbours pinned.

    Finds the minimum connected subgraph of the bounded region touching every
    pinned neighbour chain, and accepts iff it is strictly smaller than the
    old chain (then the total strictly decreases and, by construction plus a
    final :func:`is_valid_embedding` guard, validity holds). ``deadline`` is
    an absolute ``time.perf_counter()`` timestamp. The input is not mutated.
    """
    if adj is None:
        adj = build_adjacency(target)
    v = int(v)
    old_size = len(embedding[v])
    if old_size <= 1:
        return RepairOutcome(None, False, True, old_size, old_size, 0, 0)
    setup = _region_setup(embedding, source, adj, (v,), radius, region_cap)
    if setup is None:
        return RepairOutcome(None, False, False, old_size, old_size, 0, 0)
    region, nbr_idx, contacts = setup
    groups = _reduce_groups([(m, 1) for m in contacts[v].values()])
    search = _CoverSearch(
        nbr_idx, groups, incumbent_size=old_size,
        deadline=deadline, node_cap=node_cap,
        dist_to_group=_group_distances(nbr_idx, [m for m, _ in groups]),
    )
    search.run()
    if search.best is None:
        return RepairOutcome(None, False, search.proven, old_size, old_size,
                             len(region), search.nodes)
    new_chain = sorted(region[i] for i in search.best)
    candidate = {u: list(c) for u, c in embedding.items()}
    candidate[v] = new_chain
    if not is_valid_embedding(candidate, source, target, adj=adj):
        logger.debug("exact_repair_1: candidate failed validity (v=%s)", v)
        return RepairOutcome(None, False, False, old_size, old_size,
                             len(region), search.nodes)
    return RepairOutcome(candidate, True, search.proven, old_size,
                         len(new_chain), len(region), search.nodes)


def joint_repair_2(embedding: Embedding, source: nx.Graph, target: nx.Graph,
                   u: int, v: int, radius: int = DEFAULT_RADIUS,
                   deadline: Optional[float] = None, *,
                   adj: Optional[Adjacency] = None,
                   node_cap: int = X2_NODE_CAP,
                   region_cap: int = REGION_CAP) -> RepairOutcome:
    """Rip the source-adjacent pair (u, v) and re-embed BOTH jointly.

    Enumerates connected unions in the bounded region that could serve both
    chains (merged contact requirements as a necessary relaxation; identical
    contact sets needed by both sides require two distinct qubits) and
    accepts the smallest union that exactly splits into two disjoint
    connected chains, each covering its own vertex's pinned neighbours — the
    split's cross-edge covers the (u, v) source edge. Accept iff total qubits
    strictly decrease and :func:`is_valid_embedding` passes. Raises
    ``ValueError`` if (u, v) is not a source edge (in a valid embedding every
    source-adjacent pair's chains touch, so touching is implied).
    """
    if adj is None:
        adj = build_adjacency(target)
    u, v = int(u), int(v)
    if not source.has_edge(u, v):
        raise ValueError(f"joint_repair_2: ({u}, {v}) is not a source edge")
    old_total = len(embedding[u]) + len(embedding[v])
    if old_total <= 2:
        return RepairOutcome(None, False, True, old_total, old_total, 0, 0)
    setup = _region_setup(embedding, source, adj, (u, v), radius, region_cap)
    if setup is None:
        return RepairOutcome(None, False, False, old_total, old_total, 0, 0)
    region, nbr_idx, contacts = setup
    gu = [m for m, _ in _reduce_groups([(m, 1) for m in contacts[u].values()])]
    gv = [m for m, _ in _reduce_groups([(m, 1) for m in contacts[v].values()])]
    merged: List[Tuple[int, int]] = []
    gu_set, gv_set = set(gu), set(gv)
    for m in sorted(gu_set | gv_set):
        merged.append((m, (1 if m in gu_set else 0) + (1 if m in gv_set else 0)))
    groups = _reduce_groups(merged)
    search = _CoverSearch(
        nbr_idx, groups, incumbent_size=old_total,
        deadline=deadline, node_cap=node_cap, split=(gu, gv), min_size=2,
        dist_to_group=_group_distances(nbr_idx, [m for m, _ in groups]),
    )
    search.run()
    if search.best_split is None:
        return RepairOutcome(None, False, search.proven, old_total, old_total,
                             len(region), search.nodes)
    part_u, part_v = search.best_split
    candidate = {w: list(c) for w, c in embedding.items()}
    candidate[u] = sorted(region[i] for i in part_u)
    candidate[v] = sorted(region[i] for i in part_v)
    new_total = len(candidate[u]) + len(candidate[v])
    if not is_valid_embedding(candidate, source, target, adj=adj):
        logger.debug("joint_repair_2: candidate failed validity (%s, %s)", u, v)
        return RepairOutcome(None, False, False, old_total, old_total,
                             len(region), search.nodes)
    return RepairOutcome(candidate, True, search.proven, old_total, new_total,
                         len(region), search.nodes)


# ══════════════════════════════════════════════════════════════════════════════
# Anytime polish — dirty-set scheduled, deterministic, monotone
# ══════════════════════════════════════════════════════════════════════════════

def anytime_polish(embedding: Embedding, source: nx.Graph, target: nx.Graph,
                   deadline: float,
                   ops: Sequence[str] = ("spur", "shorten", "x1", "x2"), *,
                   adj: Optional[Adjacency] = None,
                   radius: int = DEFAULT_RADIUS,
                   x1_move_s: float = X1_MOVE_S,
                   x2_move_s: float = X2_MOVE_S) -> Embedding:
    """Deadline-bounded polish: cheap passes, then exact repairs on a worklist.

    ``deadline`` is an absolute ``time.perf_counter()`` timestamp. Phases (each
    opt-in via ``ops``): one ``spur_prune`` -> ``shorten_chains`` ->
    ``spur_prune`` prefix (the factored ``polish`` recipe), then a dirty-set
    loop: single-vertex exact repairs (``x1``) drain first, longest chain
    first (max key ``(len, -id)`` — dirtyset.md's rule), then joint pair
    repairs (``x2``) longest-combined-first; any acceptance re-dirties the
    closed source-neighbourhood of the changed chains (and every pair meeting
    it) and returns to draining x1. One deviation from dirtyset.md: an
    x1-repaired vertex is NOT self-re-dirtied — it just re-proved
    region-minimum, so it re-enters only when a neighbour changes.

    Deterministic for a fixed input when it reaches its fixpoint before the
    deadline. Always returns a valid embedding no worse (total qubits) than
    the input: every accepted move is strictly improving and validity-checked,
    and a final guard falls back to the input copy.
    """
    if not embedding:
        return embedding
    original = {int(w): [int(q) for q in c] for w, c in embedding.items()}
    work = {w: list(c) for w, c in original.items()}
    if adj is None:
        adj = build_adjacency(target)
    src_adj: SrcAdj = {int(w): sorted(int(x) for x in source.neighbors(w))
                       for w in source.nodes()}

    def left() -> float:
        return deadline - time.perf_counter()

    if "spur" in ops and left() > 0:
        work = spur_prune(work, src_adj, adj, deadline=deadline)
    if "shorten" in ops and left() > 0:
        work = shorten_chains(work, src_adj, adj, deadline=deadline)
        if "spur" in ops and left() > 0:     # shortening can expose new spurs
            work = spur_prune(work, src_adj, adj, deadline=deadline)

    do_x1 = "x1" in ops
    do_x2 = "x2" in ops
    dirty: Set[int] = set(work) if do_x1 else set()
    all_pairs: List[Tuple[int, int]] = []
    pairs_by_vertex: Dict[int, List[Tuple[int, int]]] = {}
    if do_x2:
        for a, b in source.edges():
            a, b = int(a), int(b)
            pair = (a, b) if a < b else (b, a)
            all_pairs.append(pair)
            pairs_by_vertex.setdefault(pair[0], []).append(pair)
            pairs_by_vertex.setdefault(pair[1], []).append(pair)
    pair_dirty: Set[Tuple[int, int]] = set(all_pairs)

    def redirty(changed: Sequence[int]) -> None:
        closed: Set[int] = set()
        for w in changed:
            closed.add(w)
            closed.update(src_adj.get(w, ()))
        if do_x1:
            dirty.update(x for x in closed if x in work)
            for w in changed:
                dirty.discard(w)          # just re-proved region-minimum (x1)
        if do_x2:
            for w in closed:
                pair_dirty.update(pairs_by_vertex.get(w, ()))

    while (dirty or pair_dirty) and left() > 0:
        if dirty:
            v = max(dirty, key=lambda t: (len(work[t]), -t))
            dirty.discard(v)
            if len(work[v]) <= 1 or not src_adj.get(v):
                continue
            move_deadline = min(deadline, time.perf_counter() + x1_move_s)
            out = exact_repair_1(work, source, target, v, radius=radius,
                                 deadline=move_deadline, adj=adj)
            if out.improved:
                work = out.embedding
                redirty((v,))
            continue
        pair = max(pair_dirty,
                   key=lambda p: (len(work[p[0]]) + len(work[p[1]]),
                                  -p[0], -p[1]))
        pair_dirty.discard(pair)
        a, b = pair
        if len(work[a]) + len(work[b]) <= 2:
            continue
        move_deadline = min(deadline, time.perf_counter() + x2_move_s)
        out = joint_repair_2(work, source, target, a, b, radius=radius,
                             deadline=move_deadline, adj=adj)
        if out.improved:
            work = out.embedding
            redirty((a, b))
            dirty.update(x for x in (a, b) if x in work)  # x2 optimum is
            # joint; each side may still admit an x1 move in ITS own region.

    ok = (sum(len(c) for c in work.values())
          <= sum(len(c) for c in original.values()))
    if not ok or not is_valid_embedding(work, source, target, adj=adj):
        logger.debug("anytime_polish: fallback to input (guard tripped)")
        return original
    return work


# ══════════════════════════════════════════════════════════════════════════════
# Registered arm
# ══════════════════════════════════════════════════════════════════════════════

@register_algorithm("p3-mmpolish")
class P3MMPolish(EmbeddingAlgorithm):
    """Stock minorminer (FULL budget) + P5 anytime polish on the leftover wall.

    v1.1 (§4.11 M5 guard): MM gets the entire budget — it patience-expires
    early on most instances (§4.7 "budget on the table"), and the polish spends
    only whatever wall remains to the same deadline. On time-marginal
    instances MM consumes everything, the polish is skipped, and success is
    identical to stock MM by construction (the v1.0 fixed 70/30 split cost
    success on instances needing 70-100 % of the budget to legalize).
    Contract-clean: never raises, plain ints, tiny-timeout safe,
    deterministic per seed, no stdout. Source is passed to minorminer as a
    GRAPH OBJECT (edge-list form drops isolated vertices).
    """

    @property
    def version(self) -> str:
        return "1.1.1"   # 1.1.1: _find_split budget enforcement (C16 runaway)

    def embed(self, source_graph, target_graph, timeout=60.0, **kwargs) -> dict:
        start = time.perf_counter()
        try:
            import minorminer

            seed = kwargs.get("seed", 0)
            if seed is None:
                seed = 0
            try:
                budget = float(timeout) if timeout else 60.0
            except (TypeError, ValueError):
                budget = 60.0
            deadline = start + budget
            raw = minorminer.find_embedding(
                source_graph, list(target_graph.edges()),
                timeout=budget, verbose=0, random_seed=int(seed),
            )
            if not raw:
                return {"embedding": {}, "time": time.perf_counter() - start,
                        "success": False, "status": "FAILURE"}
            emb = {int(w): [int(q) for q in c] for w, c in raw.items()}
            if deadline - time.perf_counter() > 0.05:
                emb = anytime_polish(emb, source_graph, target_graph, deadline)
            return {"embedding": emb, "time": time.perf_counter() - start}
        except Exception as exc:  # pragma: no cover — contract safety net
            logger.error("p3-mmpolish error: %s", exc)
            return {"embedding": {}, "time": time.perf_counter() - start,
                    "success": False, "status": "FAILURE", "error": str(exc)}
