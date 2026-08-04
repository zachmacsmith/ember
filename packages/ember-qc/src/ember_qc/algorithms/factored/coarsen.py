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

V0 (this file) builds the hierarchy and a **multilevel init** only: the
fine-level machinery (contraction, arrange, seeds) is unchanged and
receives inherited positions instead of the spectral layout. The
coarsest level is placed on a deterministic circle — the V-cycle never
consults spectral, so init-independence (the s3.36 standard; the s3.40
recorded miss) holds by construction. Deterministic per ``seed``.
"""

from __future__ import annotations

import math
from typing import Dict, List, Optional, Tuple

import numpy as np

Point = np.ndarray


class Level:
    """One level of the hierarchy: weighted graph + parent mapping."""

    __slots__ = ("adj", "weight", "parent_of")

    def __init__(self, adj: Dict[int, Dict[int, float]],
                 weight: Dict[int, float],
                 parent_of: Optional[Dict[int, int]] = None):
        self.adj = adj              # u -> {v: edge multiplicity}
        self.weight = weight        # node -> member count
        self.parent_of = parent_of  # finer node -> this level's node


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
    for v, nbrs in adj.items():
        rv = rep[v]
        d = new_adj.setdefault(rv, {})
        for u, m in nbrs.items():
            ru = rep[u]
            if ru != rv:
                d[ru] = d.get(ru, 0.0) + m
    for v in new_w:
        new_adj.setdefault(v, {})
    return Level(new_adj, new_w, parent_of=rep)


def coarsen(src_adj: Dict[int, List[int]], *, threshold: float = 0.34,
            min_nodes: int = 8, max_levels: int = 12) -> List[Level]:
    """Build the hierarchy fine -> coarse. Level 0 is the input graph
    (unit weights). Each round: collapse exact-twin groups, then greedy
    max-score matching over distance <= 2 candidates with weighted
    Jaccard >= ``threshold``. Stops when nothing merges, the graph is
    small enough, or ``max_levels`` is hit (a backstop, not a target).
    """
    adj0 = {v: {u: 1.0 for u in nbrs} for v, nbrs in src_adj.items()}
    for v in src_adj:
        adj0.setdefault(v, {})
    levels = [Level(adj0, {v: 1.0 for v in adj0})]
    while len(levels) <= max_levels:
        cur = levels[-1]
        if len(cur.adj) <= min_nodes:
            break
        groups = _twin_groups(cur.adj)
        matched: set = {v for g in groups for v in g}
        # greedy Jaccard matching on distance <= 2 pairs (pairs only;
        # twin groups above already handle the mass collapses)
        cands: List[Tuple[float, int, int]] = []
        for v in sorted(cur.adj):
            if v in matched:
                continue
            seen: set = set()
            for u in cur.adj[v]:
                if u > v and u not in matched:
                    seen.add(u)
            for u in cur.adj[v]:
                for w in cur.adj.get(u, ()):  # distance 2
                    if w > v and w not in matched and w not in cur.adj[v]:
                        seen.add(w)
            for u in sorted(seen):
                s = _wjaccard(cur.adj[v], cur.weight[v], v,
                              cur.adj[u], cur.weight[u], u)
                if s >= threshold:
                    cands.append((s, v, u))
        cands.sort(key=lambda t: (-t[0], t[1], t[2]))
        for s, v, u in cands:
            if v not in matched and u not in matched:
                groups.append([v, u])
                matched.update((v, u))
        if not groups:
            break
        nxt = _merge(cur.adj, cur.weight, groups)
        if len(nxt.adj) >= len(cur.adj):
            break
        levels.append(nxt)
    return levels


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
                    *, seed: int = 0, steps: int = 24,
                    threshold: float = 0.34) -> Dict[int, Point]:
    """The V0 multilevel init: coarsen, place the coarsest level on a
    deterministic circle (NO spectral anywhere), relax with weighted
    stair steps, expand each level with position inheritance + a small
    deterministic child spread, relax again. Returns fine-level
    positions in the [lo, hi] drawing box — a drop-in replacement for
    ``source_positions``."""
    levels = coarsen(src_adj, threshold=threshold)
    coarse = levels[-1]
    nodes = sorted(coarse.adj)
    n = len(nodes)
    center = (lo + hi) / 2.0
    span = (hi - lo) * 0.4
    rng = np.random.RandomState(seed)
    order = list(range(n))
    rng.shuffle(order)  # coarse placement must not depend on node ids
    pos: Dict[int, Point] = {}
    for i, v in enumerate(nodes):
        a = 2.0 * math.pi * order[i] / max(n, 1)
        pos[v] = center + span * np.array([math.cos(a), math.sin(a)])
    # NO coarse relaxation in V0: unweighted attraction's fixed point is
    # collapse (the s3.18 lesson, re-measured at the coarse level during
    # this build: K_{6,6}'s two supernodes met at the center). The
    # V-cycle's V0 job is TOPOLOGY — who is near whom — which the circle
    # already encodes; the fine pipeline's contraction + arrange do all
    # metric work with capacity in the loop.
    # expand down the hierarchy
    for lvl in range(len(levels) - 1, 0, -1):
        parent_of = levels[lvl].parent_of
        children: Dict[int, List[int]] = {}
        for c in sorted(levels[lvl - 1].adj):
            children.setdefault(parent_of[c], []).append(c)
        fine_pos: Dict[int, Point] = {}
        for p, cs in sorted(children.items()):
            w = levels[lvl].weight[p]
            r = 0.05 * float(np.min(hi - lo)) * math.sqrt(max(w, 1.0)) / 4.0
            for i, c in enumerate(sorted(cs)):
                a = 2.399963 * i  # golden angle: deterministic spread
                rr = r * math.sqrt(i / max(len(cs) - 1, 1)) if len(cs) > 1 \
                    else 0.0
                fine_pos[c] = pos[p] + rr * np.array([math.cos(a),
                                                      math.sin(a)])
        pos = fine_pos
    return {v: np.clip(pos[v], lo, hi) for v in pos}
