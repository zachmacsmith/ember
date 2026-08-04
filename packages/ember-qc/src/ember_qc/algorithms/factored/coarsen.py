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
Deeper levels use the weighted form (sum-min / sum-max over weighted
closed adjacency vectors, self-entry = node weight).

**Exact twins are collapsed by hashing before any scoring** (open twins:
N(u) == N(v); true twins: N[u] == N[v]) — whole groups at once, so a
turan block or a clique collapses in one level and the hub-quadratic
distance-2 candidate sets never get enumerated.

V1 (s3.63, this file): exactly TWO stages — coarsen once (Max's
flatten: V0's level loop was vestigial at our sizes), place the coarse
quotient by spectral-of-the-COARSE-graph (circle fallback), expand with
weight-proportional regions. The fine level never consults spectral;
fine-level machinery (contraction, arrange, seeds) is unchanged and
receives inherited positions. Deterministic per ``seed``.
"""

from __future__ import annotations

import math
from typing import Dict, List, Optional, Tuple

import numpy as np

Point = np.ndarray

SIZING = "count"   # footprint area shares (s3.64 ladder verdicts):
                   # "mass" = wire-mass shares (the moat fix; correct
                   # bookkeeping, marginal measured effect — helps the
                   # one heterogeneous cell, spin_glass 12.16) |
                   # "count" = V1 (DEFAULT per the no-partial-changes
                   # failure rule)
TILING = False     # True = tangent-tiling closure: gates turan with NO
                   # constant (d14->d0 at 8.80) + ladder-best ER 4.71,
                   # but +0.66 vs the tuned 0.26 constant and taxes
                   # ws/spin_glass | False = V1 COARSE_SPAN (DEFAULT)
SHAPE = "disc"     # "segment" REFUTED (s3.64): the crystal is the
                   # OUTPUT shape, not the input — pre-ordering members
                   # pre-empts the moves that discover better orders
                   # (K100 7.79->8.68, turan gate broken). Discs stand.
COARSE_SPAN = 0.4  # only read when TILING is False (the V1 constant)


class Level:
    """One level of the hierarchy: weighted graph + parent mapping."""

    __slots__ = ("adj", "weight", "parent_of", "internal")

    def __init__(self, adj: Dict[int, Dict[int, float]],
                 weight: Dict[int, float],
                 parent_of: Optional[Dict[int, int]] = None,
                 internal: Optional[Dict[int, float]] = None):
        self.adj = adj              # u -> {v: edge multiplicity}
        self.weight = weight        # node -> member count
        self.parent_of = parent_of  # finer node -> this level's node
        self.internal = internal or {}  # node -> merged-away edge mass


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
           groups: List[List[int]]) -> Level:
    """Collapse each group into its smallest-id member; rebuild the
    weighted graph. Ungrouped nodes pass through."""
    rep: Dict[int, int] = {}
    for g in groups:
        r = min(g)
        for v in g:
            rep[v] = r
    for v in adj:
        rep.setdefault(v, v)
    new_adj: Dict[int, Dict[int, float]] = {}
    new_w: Dict[int, float] = {}
    for v in adj:
        new_w[rep[v]] = new_w.get(rep[v], 0.0) + weight[v]
    new_int: Dict[int, float] = {}
    for v, nbrs in adj.items():
        rv = rep[v]
        d = new_adj.setdefault(rv, {})
        for u, m in nbrs.items():
            ru = rep[u]
            if ru != rv:
                d[ru] = d.get(ru, 0.0) + m
            else:
                # intra-supernode edge, seen once from each endpoint —
                # the wire mass the count-sizing rule was blind to
                # (s3.64 M1; Max's moat observation)
                new_int[rv] = new_int.get(rv, 0.0) + m / 2.0
    for v in new_w:
        new_adj.setdefault(v, {})
    return Level(new_adj, new_w, parent_of=rep, internal=new_int)


def coarsen(src_adj: Dict[int, List[int]], *, threshold: float = 0.34,
            min_nodes: int = 8) -> List[Level]:
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
    coarsening ([fine] only)."""
    adj0 = {v: {u: 1.0 for u in nbrs} for v, nbrs in src_adj.items()}
    for v in src_adj:
        adj0.setdefault(v, {})
    fine = Level(adj0, {v: 1.0 for v in adj0})
    if len(adj0) <= min_nodes:
        return [fine]
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


def _stair_step_weighted(pos: Dict[int, Point],
                         adj: Dict[int, Dict[int, float]],
                         eta: float) -> Dict[int, Point]:
    """One subgradient step on the weighted coarse graph: per closed
    neighborhood, pull the two extreme members inward per axis, force
    scaled by the net's edge mass; trust-region clipped at one tile
    (the fine-level stair_step's shape, weight-aware)."""
    new = {v: p.copy() for v, p in pos.items()}
    force = {v: np.zeros(2) for v in pos}
    for v, nbrs in adj.items():
        if not nbrs:
            continue
        members = [v] + list(nbrs)
        mass = sum(nbrs.values())
        for ax in (0, 1):
            xs = sorted(members, key=lambda m: (float(pos[m][ax]), m))
            lo_m, hi_m = xs[0], xs[-1]
            if float(pos[hi_m][ax]) - float(pos[lo_m][ax]) > 1e-9:
                f = min(1.0, mass / max(1.0, len(members)))
                force[lo_m][ax] += f
                force[hi_m][ax] -= f
    for v in pos:
        step = np.clip(force[v], -1.0, 1.0) * eta
        new[v] = pos[v] + step
    return new


def multilevel_init(src_adj: Dict[int, List[int]], lo: Point, hi: Point,
                    *, seed: int = 0,
                    threshold: float = 0.34) -> Dict[int, Point]:
    """The V2 footprint-true init (s3.64): coarsen once; size each
    supernode's footprint by WIRE MASS (SIZING="mass": area share =
    sum of member fine-degrees — kappa cancels; the moat fix), set the
    layout scale by the TANGENT-TILING closure (TILING=True: minimal
    uniform scale at which footprints do not overlap — no free
    constant; on box overflow the whole picture zooms down evenly),
    and spread children along a DIAGONAL SEGMENT of footprint length
    (SHAPE="segment": the crystal's own 1D-order form; members are
    interchangeable by the merge score's certificate). Unit-layout
    centers come from spectral-of-the-COARSE-graph (circle fallback).
    The fine level never consults spectral. Deterministic per ``seed``
    (seed only breaks circle-rotation ties on the fallback path)."""
    import networkx as nx

    levels = coarsen(src_adj, threshold=threshold)
    coarse = levels[-1]
    nodes = sorted(coarse.adj)
    n = len(nodes)
    center = (lo + hi) / 2.0
    span_min = float(np.min(hi - lo))
    R_AREA = 0.45 * span_min  # V1's measured total-area budget (shares
                              # and scale change below; the budget does
                              # not)

    if SIZING == "mass":
        mass = {v: 2.0 * coarse.internal.get(v, 0.0)
                + sum(coarse.adj[v].values()) for v in nodes}
        tot = sum(mass.values())
        if tot <= 0:
            mass = dict(coarse.weight)
            tot = sum(mass.values()) or 1.0
        share = {v: mass[v] / tot for v in nodes}
    else:
        W = sum(coarse.weight.values()) or 1.0
        share = {v: coarse.weight[v] / W for v in nodes}
    radius = {v: R_AREA * math.sqrt(share[v]) for v in nodes}

    _DIAG = np.array([1.0, 1.0]) / math.sqrt(2.0)

    def _spread(out, cs, cpos, r):
        k = len(cs)
        for i, c in enumerate(sorted(cs)):
            if k == 1:
                out[c] = cpos.copy()
            elif SHAPE == "segment":
                t = -1.0 + 2.0 * i / (k - 1)
                out[c] = cpos + r * t * _DIAG
            else:
                a = 2.399963 * i  # golden angle (the V1 disc)
                rr = r * math.sqrt(i / (k - 1))
                out[c] = cpos + rr * np.array([math.cos(a), math.sin(a)])
        return out

    if n == 1:
        # degenerate quotient (K_n and friends). Disc arm: V0's MEASURED
        # geometry exactly (circle-point anchor + compact disc; the
        # centered repair measured worse — s3.63). Segment arm: the
        # proto-staircase — children on the diagonal THROUGH THE CENTER
        # at footprint length (the template's own geometry; the anchor
        # was a disc artifact).
        v0 = nodes[0]
        cs = sorted(levels[0].adj) if len(levels) > 1 else [v0]
        out: Dict[int, Point] = {}
        if SHAPE == "segment":
            _spread(out, cs, center, radius[v0])
        else:
            w = coarse.weight[v0]
            anchor = center + (hi - lo) * 0.4 * np.array([1.0, 0.0])
            r = 0.05 * span_min * math.sqrt(max(w, 1.0)) / 4.0
            for i, c in enumerate(cs):
                a = 2.399963 * i
                rr = r * math.sqrt(i / max(len(cs) - 1, 1)) \
                    if len(cs) > 1 else 0.0
                out[c] = anchor + rr * np.array([math.cos(a),
                                                 math.sin(a)])
        return {v: np.clip(out[v], lo, hi) for v in out}

    # unit layout: spectral of the weighted coarse graph, circle fallback
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

    if TILING:
        # tangent-tiling closure (s3.64 M3): the smallest uniform scale
        # of the unit layout at which no two footprints overlap. If the
        # tiled picture exceeds the box, zoom the WHOLE picture down
        # evenly (footprints then overlap minimally and uniformly — the
        # honest state when demand exceeds fabric).
        lam = 1e-9
        for i in range(n):
            for j in range(i + 1, n):
                dist = float(np.linalg.norm(arr[i] - arr[j]))
                need = radius[nodes[i]] + radius[nodes[j]]
                lam = max(lam, need / max(dist, 1e-9))
        halfbox = (hi - lo) / 2.0
        over = 1.0
        for i, v in enumerate(nodes):
            for ax in (0, 1):
                ext = lam * abs(float(arr[i][ax])) + radius[v]
                if ext > float(halfbox[ax]):
                    over = max(over, ext / float(halfbox[ax]))
        zoom = 1.0 / over
        cpos = {v: center + (lam * zoom) * arr[i]
                for i, v in enumerate(nodes)}
        rad = {v: radius[v] * zoom for v in nodes}
    else:
        halfspan = (hi - lo) * COARSE_SPAN
        cpos = {v: center + halfspan * arr[i]
                for i, v in enumerate(nodes)}
        rad = radius

    parent_of = coarse.parent_of
    children: Dict[int, List[int]] = {}
    for c in sorted(levels[0].adj):
        children.setdefault(parent_of[c], []).append(c)
    fine_pos: Dict[int, Point] = {}
    for pnode, cs in sorted(children.items()):
        _spread(fine_pos, cs, cpos[pnode], rad[pnode])
    return {v: np.clip(fine_pos[v], lo, hi) for v in fine_pos}
