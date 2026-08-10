"""
ember_qc/algorithms/factored/coarsen.py
========================================
Source-side multilevel coarsening (the V-cycle, notes s3.62; design
recorded on the ledger 2026-08-03): merge structurally-equivalent
variables into supernodes, place the tiny coarse graph, expand back down
with position inheritance. Global joint decisions (block separation,
clump merging — the failures of s3.19/s3.40/s3.43/s3.51) become single
local moves at the level where a cluster is one node.

The merge score is **closed-neighborhood Jaccard**,
``S(u,v) = |N[u] cap N[v]| / |N[u] cup N[v]|`` — not a heuristic: the
numerator counts exactly the stair nets strained by separating u and v
(common neighbors + the direct edge via the closed neighborhoods), i.e.
dE/dd, the attractive force in arm-tiles per tile; the score is the
fraction of the pair's total pull that is agreement. Limits: clique
S=1 (collapses to one node — the template becomes a readout), turan
block deg/(deg+2) (blocks collapse to the quotient graph), chain edge
1/2 (heavy-edge matching recovered as the sparse limit), ER ~1/d flat
(the s3.21 null class degenerates to edge matching, correctly).
The weighted form (sum-min / sum-max) applies at the coarse level's
weighted candidates.

**Exact twins are collapsed by hashing before any scoring** (open twins:
N(u) == N(v); true twins: N[u] == N[v]) — whole groups at once, so a
turan block or a clique collapses in one level and the hub-quadratic
distance-2 candidate sets never get enumerated.

As shipped (consolidation 3, s3.66): exactly TWO stages — coarsen once,
place the coarse quotient by spectral-of-the-COARSE-graph (circle
fallback), expand children in golden-angle discs at COARSE_SPAN scale.
The fine level never consults spectral; fine-level machinery is
unchanged and receives inherited positions. Losing arms (wire-mass
shares, tangent-tiling closure, segment spreads) live at the
consolidation-3 archive marker with their s3.64 numbers. Deterministic
per ``seed``.
"""

from __future__ import annotations

import math
from typing import Dict, List, Optional, Tuple

import numpy as np

Point = np.ndarray

COARSE_SPAN = 0.4  # coarse-layout halfspan as a fraction of the box
                   # (== source_positions' middle-80% convention)


class Level:
    """One level of the hierarchy: weighted graph + parent mapping."""

    __slots__ = ("adj", "weight", "parent_of", "self_mass", "diag")

    def __init__(self, adj: Dict[int, Dict[int, float]],
                 weight: Dict[int, float],
                 parent_of: Optional[Dict[int, int]] = None,
                 self_mass: Optional[Dict[int, float]] = None):
        self.adj = adj              # u -> {v: edge multiplicity}
        self.weight = weight        # node -> member count
        self.parent_of = parent_of  # finer node -> this level's node
        # Internal edge mass absorbed inside each supernode (s3.69):
        # 0.0 at the fine level; _merge accumulates collapsed multiplicity.
        self.self_mass = self_mass if self_mass is not None else {}
        self.diag: Dict = {}        # per-call coarsening diagnostics (s3.69)


def _twin_groups(adj: Dict[int, Dict[int, float]]) -> List[List[int]]:
    """Groups of exact twins (open OR true), each collapsible to one
    supernode. Open twins share N(v); true twins share N[v]. A group is
    reported once (open groups take precedence for members in both)."""
    open_key: Dict[tuple, List[int]] = {}
    true_key: Dict[tuple, List[int]] = {}
    for v in sorted(adj):
        nbrs = tuple(sorted(adj[v]))
        open_key.setdefault(nbrs, []).append(v)
        closed = tuple(sorted(set(adj[v]) | {v}))
        true_key.setdefault(closed, []).append(v)
    groups: List[List[int]] = []
    taken: set = set()
    for key in sorted(open_key):
        g = [v for v in open_key[key] if v not in taken]
        if len(g) > 1:
            groups.append(g)
            taken.update(g)
    for key in sorted(true_key):
        g = [v for v in true_key[key] if v not in taken]
        if len(g) > 1:
            groups.append(g)
            taken.update(g)
    return groups


def _wjaccard(au: Dict[int, float], wu: float, u: int,
              av: Dict[int, float], wv: float, v: int) -> float:
    """Weighted closed-neighborhood Jaccard: sum-min / sum-max over the
    weighted closed adjacency vectors (self-entry = node weight)."""
    cu = dict(au)
    cu[u] = cu.get(u, 0.0) + wu
    cv = dict(av)
    cv[v] = cv.get(v, 0.0) + wv
    keys = set(cu) | set(cv)
    smin = sum(min(cu.get(k, 0.0), cv.get(k, 0.0)) for k in keys)
    smax = sum(max(cu.get(k, 0.0), cv.get(k, 0.0)) for k in keys)
    return smin / smax if smax > 0 else 0.0


def _merge(adj: Dict[int, Dict[int, float]], weight: Dict[int, float],
           groups: List[List[int]],
           self_mass: Optional[Dict[int, float]] = None) -> Level:
    """Collapse each group into its smallest-id member; rebuild the
    weighted graph. Ungrouped nodes pass through. Edge mass collapsed
    INSIDE a group is accumulated into the supernode's self_mass (s3.69)
    rather than discarded — each undirected internal edge is seen twice
    in the directed sweep, hence the /2."""
    rep: Dict[int, int] = {}
    for g in groups:
        r = min(g)
        for v in g:
            rep[v] = r
    for v in adj:
        rep.setdefault(v, v)
    new_adj: Dict[int, Dict[int, float]] = {}
    new_w: Dict[int, float] = {}
    new_sm: Dict[int, float] = {}
    for v in adj:
        new_w[rep[v]] = new_w.get(rep[v], 0.0) + weight[v]
        if self_mass:
            new_sm[rep[v]] = new_sm.get(rep[v], 0.0) + self_mass.get(v, 0.0)
    for v, nbrs in adj.items():
        rv = rep[v]
        d = new_adj.setdefault(rv, {})
        for u, m in nbrs.items():
            ru = rep[u]
            if ru != rv:
                d[ru] = d.get(ru, 0.0) + m
            else:
                new_sm[rv] = new_sm.get(rv, 0.0) + m / 2.0
    for v in new_w:
        new_adj.setdefault(v, {})
        new_sm.setdefault(v, 0.0)
    return Level(new_adj, new_w, parent_of=rep, self_mass=new_sm)


def coarsen(src_adj: Dict[int, List[int]], *, threshold: float = 0.34,
            min_nodes: int = 8, agg: bool = False,
            units: bool = False) -> List[Level]:
    """Build the TWO-STAGE hierarchy [fine, coarse] (s3.63 flatten —
    V0's level loop was vestigial at our sizes: measured depths <= 3
    with later rounds nearly inert). ONE round: collapse exact-twin
    groups (score 1, unconditional; whole blocks at once), then one
    greedy weighted-Jaccard matching over distance <= 2 candidates at
    score >= ``threshold``. No twin fixpoint — iterating would collapse
    turan's block quotient (all true twins) to a point and destroy the
    separation the coarse level exists to provide. Coarseness is decided
    by the GRAPH (twin partition + the tau-boxed threshold: chain edge
    1/2 must merge, ER ~1/d must not, star leaf 1/3 at the boundary),
    never by a size target. Graphs already <= ``min_nodes`` skip
    coarsening ([fine] only).

    ``agg=True`` (s3.68/s3.69) replaces the single pairwise-matching
    round + the no-fixpoint decree with LEADER AGGREGATION ITERATED TO
    ITS NATURAL FIXPOINT: twin round 0 unchanged, then per round stars
    around invariant-ordered seeds under the same weighted score, until
    a round produces no merge. The turan quotient is protected by the
    SCORE (S ~ 0.012 << tau), not by decree — measured s3.68, parity on
    the board with emergent protection. Returns [fine, coarsest] with
    parent_of composed across rounds."""
    adj0 = {v: {u: 1.0 for u in nbrs} for v, nbrs in src_adj.items()}
    for v in src_adj:
        adj0.setdefault(v, {})
    fine = Level(adj0, {v: 1.0 for v in adj0})
    if len(adj0) <= min_nodes:
        return [fine]
    if units:
        return _coarsen_units(fine)
    if agg:
        return _coarsen_agg(fine, threshold)
    groups = _twin_groups(fine.adj)
    matched: set = {v for g in groups for v in g}
    cands: List[Tuple[float, int, int]] = []
    for v in sorted(fine.adj):
        if v in matched:
            continue
        seen: set = set()
        for u in fine.adj[v]:
            if u > v and u not in matched:
                seen.add(u)
        for u in fine.adj[v]:
            for w in fine.adj.get(u, ()):  # distance 2
                if w > v and w not in matched and w not in fine.adj[v]:
                    seen.add(w)
        for u in sorted(seen):
            sc = _wjaccard(fine.adj[v], fine.weight[v], v,
                           fine.adj[u], fine.weight[u], u)
            if sc >= threshold:
                cands.append((sc, v, u))
    cands.sort(key=lambda t: (-t[0], t[1], t[2]))
    for sc, v, u in cands:
        if v not in matched and u not in matched:
            groups.append([v, u])
            matched.update((v, u))
    if not groups:
        return [fine]
    coarse = _merge(fine.adj, fine.weight, groups)
    if len(coarse.adj) >= len(fine.adj):
        return [fine]
    return [fine, coarse]


def _affinity(au: Dict[int, float], wu: float, u: int,
              av: Dict[int, float], wv: float, v: int) -> float:
    """Per-member affinity (s3.72) — THE merge criterion, stated for
    disjoint sets S, T over the real edges of the source graph:

        p_S(w)  = E(S, w) / |S|          (per-member pull toward w)
        mu      = 2 E(S, T) / (|S|+|T|)  (per-member mutual pull)
        affinity = [sum_w min(p_S, p_T) + mu + 1]
                 / [sum_w max(p_S, p_T) + mu + 1]

    "Put the average member of S next to the average member of T: what
    fraction of their pull do they agree on?" — mutual pull and one's
    own body count as agreement. The +1 is one body per member
    (constant; regularizer only — the old body term's size penalty was
    WRONG: 1:2 fragments of one twin family scored 1/2; here any-ratio
    fragments score exactly 1). Internal edges of S or T do not appear.
    Nothing asks whether S and T touch: the direct edge is one term on
    the same scale as shared support (chain neighbors 1/2; 99%-shared
    non-adjacent pairs ~1). affinity = 1  <=>  the rest of the graph
    cannot tell S and T apart (per member) — clique members and
    same-block independent-set members alike, no species detection.

    Here the sets are supernodes: au/av are aggregated adjacency rows
    (cached sums of member rows), wu/wv the member counts."""
    m = au.get(v, 0.0)
    mu = 2.0 * m / (wu + wv)
    smin = 0.0
    smax = 0.0
    for k, a in au.items():
        if k == u or k == v:
            continue
        b = av.get(k, 0.0) / wv
        a = a / wu
        if a < b:
            smin += a
            smax += b
        else:
            smin += b
            smax += a
    for k, b in av.items():
        if k == u or k == v or k in au:
            continue
        smax += b / wv
    return (smin + mu + 1.0) / (smax + mu + 1.0)


def _coarsen_units(fine: Level) -> List[Level]:
    """Move-unit hierarchy (s3.72, THE units engine — Max, 2026-08-07:
    the correct criterion ships even where the deleted wrong-but-working
    one measured a hair better; wrong code does not stay default). Known
    open defect, named and owned by the CONSUMPTION side, not this
    engine: deep hierarchies emit nested fragment units whose one-shot
    gathers can pre-empt a full-block gather (turan 6.71 vs 6.46) — the
    fix is unit selection/ordering in the cluster pass.

    The engine: ONE formula, no hash, no adjacency
    rule, no threshold. Per round: enumerate pairs that share an edge or
    a neighbor, rank them by ``_affinity`` (the per-member criterion —
    see its docstring), greedy maximal matching by rank, rebuild, repeat
    to fixpoint (one node per component). Ratio <= 2x per round -> log
    depth. The gate owns correctness: over-generous units cost one
    rejected proposal; missing units cost inexpressible joint moves.

    Deleted here and why (s3.72):
    - the exact-twin hash — topology detection; affinity-1 pairs
      assemble twin families through the ordinary rounds;
    - the adjacency-only candidate rule — it overrode the criterion's
      own direct-edge/shared-support interpolation, and its
      justification (connected units) was an UNMEASURED structural
      indicator, retracted; the probe measures the outcome instead;
    - the raw-total score — pure size mismatch read as disagreement
      (1:2 twin fragments at 1/2); per-member profiles fix it at the
      root, which also retires the straggler pathology permanently."""
    diag: Dict = {"rounds": 0, "ratios": [], "max_cluster": 1}
    cur = fine
    chain: List[Level] = [fine]

    while len(cur.adj) > 1:
        adj, weight = cur.adj, cur.weight
        pairs: List[Tuple[float, int, int]] = []
        for v in sorted(adj):
            cand: set = set()
            for x in adj[v]:
                if x > v:
                    cand.add(x)
                for y in adj.get(x, ()):
                    if y > v:
                        cand.add(y)
            for x in sorted(cand):
                pairs.append((_affinity(adj[v], weight[v], v,
                                        adj[x], weight[x], x), v, x))
        # Admissibility: a pair may merge only if it is at least ONE
        # endpoint's best available option (ties allowed). Without this,
        # greedy maximality forces leftovers of odd-count families into
        # bad marriages (turan: one 0.012 cross-block pairing at round 1
        # snowballed to a 64/17 mixed blob — no pure block level, every
        # gather screened out). A leftover whose kin were all taken this
        # round waits; next round its kin score 1 again at any size
        # ratio (the per-member formula). The global-max pair is always
        # admissible, so every round merges something and termination
        # is unchanged.
        bestval: Dict[int, float] = {}
        for sc, v, x in pairs:
            if sc > bestval.get(v, 0.0):
                bestval[v] = sc
            if sc > bestval.get(x, 0.0):
                bestval[x] = sc
        pairs.sort(key=lambda t: (-t[0], t[1], t[2]))
        matched: set = set()
        groups = []
        for sc, v, x in pairs:
            if v in matched or x in matched:
                continue
            if (sc < bestval.get(v, 0.0) - 1e-12
                    and sc < bestval.get(x, 0.0) - 1e-12):
                continue
            groups.append([v, x])
            matched.update((v, x))
        if not groups:
            break
        nxt = _merge(cur.adj, cur.weight, groups, cur.self_mass)
        if len(nxt.adj) >= len(cur.adj):
            break
        diag["rounds"] += 1
        diag["ratios"].append(round(len(cur.adj) / len(nxt.adj), 3))
        chain.append(nxt)
        cur = nxt

    chain[-1].diag = diag
    return chain


def _coarsen_agg(fine: Level, threshold: float) -> List[Level]:
    """Leader aggregation iterated to fixpoint (s3.68, validated at
    parity with emergent turan protection). Round 0: stock exact-twin
    collapse (whole groups). Rounds 1..k: every node either seeds a
    cluster or joins its best seed with S >= threshold; clusters are
    stars in the similarity graph (radius 1 — no single-link chaining);
    seed order is invariant (weight desc, degree desc; id as last-resort
    tie-break, the documented residual label dependence). Iterates until
    a round produces no merge and returns the FULL CHAIN [fine, L1, ...,
    coarsest] — each level's parent_of maps the previous level's nodes
    (the transport junction expands level-by-level; deep hierarchies are
    compositions of the same adjoint pair, never a one-shot flatten).
    Diagnostics on the coarsest Level's ``diag``."""
    diag: Dict = {"rounds": 0, "ratios": [], "max_cluster": 1}
    cur = fine
    chain: List[Level] = [fine]

    groups = _twin_groups(cur.adj)
    if groups:
        nxt = _merge(cur.adj, cur.weight, groups, cur.self_mass)
        diag["ratios"].append(round(len(cur.adj) / len(nxt.adj), 3))
        diag["max_cluster"] = max(len(g) for g in groups)
        chain.append(nxt)
        cur = nxt

    while True:
        adj, weight = cur.adj, cur.weight
        order = sorted(adj, key=lambda v: (-weight[v], -len(adj[v]), v))
        assigned: Dict[int, int] = {}
        # Accumulated cluster state per seed: a joiner is scored against
        # the cluster AS IT CURRENTLY IS, not the seed as it was — the
        # correct semantics of joining, and what stops a star of
        # individually-similar joiners from over-merging past what any
        # pair would accept (K_{5,5,5}: B joins A at 0.47, then C vs the
        # merged AB scores 0.15 < tau and correctly stays out).
        cl_adj: Dict[int, Dict[int, float]] = {}
        cl_w: Dict[int, float] = {}
        cl_members: Dict[int, set] = {}
        for v in order:
            if v in assigned:
                continue
            cand: set = set()
            for u in adj[v]:
                if assigned.get(u) == u:
                    cand.add(u)
                for w in adj.get(u, ()):
                    if w != v and assigned.get(w) == w:
                        cand.add(w)
            best, best_sc = None, threshold
            for s in sorted(cand):
                # Score against the cluster AS IF already merged: member
                # keys collapse onto the cluster key (the direct-edge
                # bundle), externals pass through. For a singleton
                # cluster this reduces exactly to plain _wjaccard — the
                # s3.68-measured pairwise semantics.
                m_vs = sum(m for k, m in adj[v].items()
                           if k in cl_members[s])
                v_vec = {k: m for k, m in adj[v].items()
                         if k not in cl_members[s]}
                if m_vs:
                    v_vec[s] = v_vec.get(s, 0.0) + m_vs
                s_vec = {k: m for k, m in cl_adj[s].items()
                         if k not in cl_members[s] and k != v}
                if m_vs:
                    s_vec[v] = s_vec.get(v, 0.0) + m_vs
                sc = _wjaccard(v_vec, weight[v], v, s_vec, cl_w[s], s)
                if sc > best_sc or (sc == best_sc and best is not None
                                    and s < best):
                    best, best_sc = s, sc
            if best is None:
                assigned[v] = v
                cl_adj[v] = dict(adj[v])
                cl_w[v] = weight[v]
                cl_members[v] = {v}
            else:
                assigned[v] = best
                cl_members[best].add(v)
                cl_w[best] += weight[v]
                d = cl_adj[best]
                for k, m in adj[v].items():
                    d[k] = d.get(k, 0.0) + m
        clusters: Dict[int, List[int]] = {}
        for v, s in assigned.items():
            clusters.setdefault(s, []).append(v)
        groups = [g for g in clusters.values() if len(g) > 1]
        if not groups:
            break
        nxt = _merge(cur.adj, cur.weight, groups, cur.self_mass)
        if len(nxt.adj) >= len(cur.adj):
            break
        diag["rounds"] += 1
        diag["ratios"].append(round(len(cur.adj) / len(nxt.adj), 3))
        diag["max_cluster"] = max(diag["max_cluster"],
                                  max(len(g) for g in groups))
        chain.append(nxt)
        cur = nxt

    chain[-1].diag = diag
    return chain


def _rcm(adj: Dict[int, Dict[int, float]]) -> List[int]:
    """Deterministic reverse Cuthill-McKee over a Level adjacency: per
    component (candidate starts by (degree, id)), BFS with neighbours
    visited by (degree, id), concatenation reversed. No networkx (its
    start/tie rules are insertion-order dependent), no matrices — O(E),
    and RCM minimizes exactly the envelope the diagonal regime pays."""
    deg = {v: len(nb) for v, nb in adj.items()}
    seen: set = set()
    order: List[int] = []
    for start in sorted(adj, key=lambda v: (deg[v], v)):
        if start in seen:
            continue
        queue = [start]
        seen.add(start)
        i = 0
        while i < len(queue):
            v = queue[i]
            i += 1
            for u in sorted(adj[v], key=lambda u: (deg[u], u)):
                if u not in seen:
                    seen.add(u)
                    queue.append(u)
        order.extend(queue)
    return list(reversed(order))


def hier_orders(levels: List[Level], *, serpentine: bool = True
                ) -> Dict[int, Tuple[int, int]]:
    """The hierarchy init (v4): both axis orders straight from the
    affinity hierarchy — no eigensolver, no disc geometry, no metric.
    Coarsest order = _rcm of the quotient; expansion is the adjoint
    walk of unpack_transport (same children loop, same within-block
    external-attachment rank) carrying integer RANKS only. Axis 1 (y)
    = the plain linearization; axis 0 (x) reverses the child order in
    every odd-ranked block at every level (``serpentine``) — a pure
    diagonal (serpentine=False) makes every edge dx*dy >= 0 and
    structurally disables edge_monotonize. Returns {v: (rank_x,
    rank_y)} over the fine ids."""
    if len(levels) < 2:
        base = _rcm(levels[0].adj)
        return {v: (j, j) for j, v in enumerate(base)}
    coarse = _rcm(levels[-1].adj)
    rank: Dict[int, Tuple[float, float]] = {
        v: (float(j), float(j)) for j, v in enumerate(coarse)}
    for i in range(len(levels) - 1, 0, -1):
        upper, lower = levels[i], levels[i - 1]
        children: Dict[int, List[int]] = {}
        for c in sorted(lower.adj):
            children.setdefault(upper.parent_of[c], []).append(c)
        new_rank: Dict[int, List[float]] = {}
        for axis in (0, 1):
            sup_order = sorted(children,
                               key=lambda p: (rank[p][axis], p))
            sup_rank = {p: j for j, p in enumerate(sup_order)}
            seq: List[int] = []
            for j, p in enumerate(sup_order):
                cs = children[p]

                def _akey(c):
                    num = den = 0.0
                    for u, m in lower.adj[c].items():
                        pu = upper.parent_of[u]
                        if pu != p:
                            num += m * sup_rank[pu]
                            den += m
                    att = num / den if den > 0 else float(sup_rank[p])
                    return (att, -lower.weight[c],
                            -len(lower.adj[c]), c)
                block = sorted(cs, key=_akey)
                if serpentine and axis == 0 and j % 2 == 1:
                    block = list(reversed(block))
                seq.extend(block)
            for j2, v in enumerate(seq):
                new_rank.setdefault(v, [0.0, 0.0])[axis] = float(j2)
        rank = {v: (r[0], r[1]) for v, r in new_rank.items()}
    return {v: (int(r[0]), int(r[1])) for v, r in rank.items()}


def unpack_transport(levels: List[Level],
                     coarse_rank: Dict[int, "np.ndarray"],
                     grid, kappa: float,
                     src_adj: Dict[int, List[int]]) -> Dict[int, Point]:
    """The measure-transport junction (s3.69): the fine layout is the
    coarse layout's ORDERS, expanded by MASS.

    Merge and unpack are adjoint — the merge score certifies which
    sibling orders are free (interchangeability); this rule uses exactly
    that freedom and no more. Per axis: fine order = coarse order with
    each supernode a contiguous block (within-block order = external-
    attachment rank; ties broken by invariants, certified free by the
    merge); coordinates = cumulative wire-mass integral in tile units
    scaled by the fabric's mean line-pool density. No cramming (every
    node gets exactly its mass), no moats (no space without mass), no
    shapes, no geometry constants — the disc/anchor/COARSE_SPAN family
    is not consulted on this path. A single-supernode quotient is not a
    special case: one contiguous block under cumulative mass on both
    axes yields the diagonal-scale cloud (K_n's crystal) by arithmetic.

    ``coarse_rank`` carries each COARSEST-level supernode's per-axis rank
    source (spectral coordinates of the coarsest quotient — used for
    ORDER only, their metric is discarded). The expansion walks the
    chain one level at a time — each junction is one application of the
    adjoint rule, using THAT level's adjacency for attachment ranks, so
    deep fixpoint hierarchies (lattices) recover locality scale by
    scale instead of being flattened through a single composed map.
    Returns TILE-SPACE positions at the fabric-linear mass scale."""
    fine = levels[0]

    # Per-axis dense ranks, expanded coarsest -> fine.
    rank: Dict[int, Tuple[float, float]] = {
        v: (float(coarse_rank[v][0]), float(coarse_rank[v][1]))
        for v in levels[-1].adj}
    for i in range(len(levels) - 1, 0, -1):
        upper, lower = levels[i], levels[i - 1]
        children: Dict[int, List[int]] = {}
        for c in sorted(lower.adj):
            children.setdefault(upper.parent_of[c], []).append(c)
        new_rank: Dict[int, List[float]] = {}
        for axis in (0, 1):
            sup_order = sorted(children,
                               key=lambda p: (rank[p][axis], p))
            sup_rank = {p: j for j, p in enumerate(sup_order)}
            seq: List[int] = []
            for p in sup_order:
                cs = children[p]

                # Within-block order: external-attachment rank — the
                # mass-weighted mean rank of each child's neighbor
                # blocks at THIS level. Ties (no external pull —
                # merge-certified interchangeable) fall to invariants:
                # weight desc, degree desc, id.
                def _akey(c):
                    num = den = 0.0
                    for u, m in lower.adj[c].items():
                        pu = upper.parent_of[u]
                        if pu != p:
                            num += m * sup_rank[pu]
                            den += m
                    att = num / den if den > 0 else float(sup_rank[p])
                    return (att, -lower.weight[c],
                            -len(lower.adj[c]), c)
                seq.extend(sorted(cs, key=_akey))
            for j, v in enumerate(seq):
                new_rank.setdefault(v, [0.0, 0.0])[axis] = float(j)
        rank = {v: (r[0], r[1]) for v, r in new_rank.items()}

    # Wire mass (fabric units: body + arms). kappa is the fresh-contact
    # rate per tile-STEP; a bar advances ``stride`` steps, so the
    # per-bar rate is kappa*stride (Zephyr: 7.7*2 ~ the 16 contacts/bar
    # of fabrics 4.2; stride-1 fabrics unchanged). Arm length in bars =
    # deg / (kappa*stride).
    k_bar = max(kappa, 1.0) * max(getattr(grid, "stride", 1), 1)
    mass = {v: 1.0 + len(src_adj.get(v, ())) / k_bar
            for v in fine.adj}

    # Fabric-linear scale: the extent a mass M claims along an axis is
    # M/rho tiles, where rho is the fabric's mean wire capacity per unit
    # of that axis (grid.cap is (H, W, 2); pool 0 = vertical wires, pool
    # 1 = horizontal; untyped grids carry a 0.5/0.5 split — still
    # valid). Dense sources get their crystal-scale footprint (K100/Z12:
    # ~7 tiles — matches the measured diagonal); sparse sources come out
    # compact and the iteration-0 capacity projection spreads them
    # exactly as far as the pools demand (its job, s3.52) — no moats,
    # no cramming, no free constants. The h/v mass split by order
    # duality is the documented extents refinement (v1: symmetric /2).
    import numpy as _np
    cap = _np.asarray(grid.cap, dtype=float)
    rho = (max(cap[:, :, 1].sum() / max(grid.W, 1), 1.0),
           max(cap[:, :, 0].sum() / max(grid.H, 1), 1.0))
    span = (float(grid.W), float(grid.H))

    out: Dict[int, Point] = {v: np.zeros(2) for v in fine.adj}
    for axis in (0, 1):
        seq = sorted(fine.adj, key=lambda v: (rank[v][axis], v))
        total = sum(mass[v] for v in seq) / 2.0
        need = total / rho[axis]          # tiles claimed by the mass
        scale = min(1.0, (span[axis] - 1e-6) / max(need, 1e-9))
        off = (span[axis] - min(need, span[axis])) / 2.0
        cum = 0.0
        for v in seq:
            half = mass[v] / 2.0
            cum += half / 2.0
            out[v][axis] = off + scale * (cum / rho[axis])
            cum += half / 2.0
    return {v: np.clip(out[v], 0.0,
                       np.array(span) - 1e-9) for v in out}


def _coarse_rank_positions(coarse: Level, seed: int) -> Dict[int, "np.ndarray"]:
    """Per-supernode rank source for the transport unpack: the same
    deterministic spectral-of-the-weighted-coarse-graph (circle fallback)
    the stock init uses — but consumed for ORDER only, so the returned
    metric is arbitrary."""
    import networkx as nx

    nodes = sorted(coarse.adj)
    n = len(nodes)
    if n == 1:
        return {nodes[0]: np.zeros(2)}
    arr = None
    if n >= 3:
        g = nx.Graph()
        g.add_nodes_from(nodes)
        for v, nbrs in coarse.adj.items():
            for u, m in nbrs.items():
                if u > v:
                    g.add_edge(v, u, weight=m)
        try:
            sp = nx.spectral_layout(g, weight="weight")
            cand = np.array([sp[v] for v in nodes], dtype=float)
            spn = cand.max(axis=0) - cand.min(axis=0)
            if np.all(np.isfinite(cand)) and np.all(spn > 1e-9):
                arr = cand
        except Exception:
            arr = None
    if arr is None:
        rng = np.random.RandomState(seed)
        order = list(range(n))
        rng.shuffle(order)
        arr = np.array([[math.cos(2.0 * math.pi * order[i] / max(n, 1)),
                         math.sin(2.0 * math.pi * order[i] / max(n, 1))]
                        for i in range(n)])
    return {v: arr[i] for i, v in enumerate(nodes)}


def multilevel_init(src_adj: Dict[int, List[int]], lo: Point, hi: Point,
                    *, seed: int = 0,
                    threshold: float = 0.34,
                    agg: bool = False, transport: bool = False,
                    grid=None, kappa: Optional[float] = None
                    ) -> Dict[int, Point]:
    """The two-stage V-cycle init (s3.62-3.66, the shipped cell of the
    s3.64 ladder): coarsen once; place the coarse quotient by a
    deterministic spectral layout of the weighted coarse graph (circle
    fallback for degenerate spectra); spread each supernode's children
    in a golden-angle disc with area proportional to member count at
    COARSE_SPAN layout scale. Degenerate single-supernode quotients
    (K_n and friends) reproduce the V0 measured geometry (circle-point
    anchor + compact disc — the centered variant measured worse,
    s3.63). Graphs that do not coarsen return the layout of the fine
    graph directly. The fine level never consults spectral. Losing
    arms (wire-mass shares, tangent-tiling closure, segment spreads)
    live at the consolidation-3 archive marker with their s3.64
    numbers. Deterministic per ``seed`` (circle-rotation ties only)."""
    import networkx as nx

    levels = coarsen(src_adj, threshold=threshold, agg=agg)

    if transport:
        # s3.69 measure-transport junction: orders + mass, no discs, no
        # anchors, no COARSE_SPAN — see unpack_transport. Requires the
        # fabric context (grid, kappa); returns drawing-space to keep
        # the caller contract identical to the stock path.
        if grid is None or kappa is None:
            raise ValueError("transport unpack requires grid and kappa")
        if len(levels[-1].adj) > 1:
            cr = _coarse_rank_positions(levels[-1], seed)
            tile_pts = unpack_transport(levels, cr, grid, kappa, src_adj)
            return {v: grid.Minv @ (tile_pts[v] - grid.c)
                    for v in tile_pts}
        # Single-supernode quotient (K_n and friends): the transport
        # rule's precondition fails — there are no coarse orders to
        # preserve and every sibling order is a merge-certified tie, so
        # the junction carries ZERO information. Among certified-free
        # unpacks we keep the measured-best one (the V0 anchor geometry
        # below, s3.63; the pre-formed diagonal measured +0.41 on K100 —
        # the attraction.md 'pre-ordering pre-empts E-gated discovery'
        # mechanism, re-observed s3.69). This is the rule acknowledging
        # its degenerate case, not a shape heuristic: transport engages
        # exactly when there is structure to transport.

    if len(levels) > 2:
        # Disc path on a deep (agg) chain: compose parent maps to the
        # 2-level view the disc spread expects (the s3.68-measured
        # configuration). The transport path above never flattens.
        total = dict(levels[1].parent_of)
        for lv in levels[2:]:
            total = {f: lv.parent_of[c] for f, c in total.items()}
        flat = levels[-1]
        flat.parent_of = total
        levels = [levels[0], flat]

    coarse = levels[-1]
    nodes = sorted(coarse.adj)
    n = len(nodes)
    center = (lo + hi) / 2.0
    span_min = float(np.min(hi - lo))

    W = sum(coarse.weight.values()) or 1.0
    radius = {v: 0.45 * span_min * math.sqrt(coarse.weight[v] / W)
              for v in nodes}

    def _spread(out, cs, cpos, r):
        k = len(cs)
        for i, c in enumerate(sorted(cs)):
            if k == 1:
                out[c] = cpos.copy()
            else:
                a = 2.399963 * i  # golden angle
                rr = r * math.sqrt(i / (k - 1))
                out[c] = cpos + rr * np.array([math.cos(a), math.sin(a)])
        return out

    if n == 1:
        v0 = nodes[0]
        cs = sorted(levels[0].adj) if len(levels) > 1 else [v0]
        w = coarse.weight[v0]
        anchor = center + (hi - lo) * COARSE_SPAN * np.array([1.0, 0.0])
        r = 0.05 * span_min * math.sqrt(max(w, 1.0)) / 4.0
        out: Dict[int, Point] = {}
        _spread(out, cs, anchor, r)
        return {v: np.clip(out[v], lo, hi) for v in out}

    arr = None
    if n >= 3:
        g = nx.Graph()
        g.add_nodes_from(nodes)
        for v, nbrs in coarse.adj.items():
            for u, m in nbrs.items():
                if u > v:
                    g.add_edge(v, u, weight=m)
        try:
            sp = nx.spectral_layout(g, weight="weight")
            cand = np.array([sp[v] for v in nodes], dtype=float)
            spn = cand.max(axis=0) - cand.min(axis=0)
            if np.all(np.isfinite(cand)) and np.all(spn > 1e-9):
                arr = (cand - cand.min(axis=0)) / spn * 2.0 - 1.0
        except Exception:
            arr = None
    if arr is None:
        rng = np.random.RandomState(seed)
        order = list(range(n))
        rng.shuffle(order)
        arr = np.array([[math.cos(2.0 * math.pi * order[i] / max(n, 1)),
                         math.sin(2.0 * math.pi * order[i] / max(n, 1))]
                        for i in range(n)])
    halfspan = (hi - lo) * COARSE_SPAN
    pos = {v: center + halfspan * arr[i] for i, v in enumerate(nodes)}

    if len(levels) == 1 or coarse.parent_of is None:
        # graph did not coarsen (<= min_nodes or zero merges): the
        # coarse layout IS the fine layout (the s3.66 guard — the
        # missing branch the vcycle flip exposed on K8/chimera)
        return {v: np.clip(pos[v], lo, hi) for v in pos}

    children: Dict[int, List[int]] = {}
    for c in sorted(levels[0].adj):
        children.setdefault(coarse.parent_of[c], []).append(c)
    fine_pos: Dict[int, Point] = {}
    for pnode, cs in sorted(children.items()):
        _spread(fine_pos, cs, pos[pnode], radius[pnode])
    return {v: np.clip(fine_pos[v], lo, hi) for v in fine_pos}
