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


def multilevel_init(src_adj: Dict[int, List[int]], lo: Point, hi: Point,
                    *, seed: int = 0,
                    threshold: float = 0.34) -> Dict[int, Point]:
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

    levels = coarsen(src_adj, threshold=threshold)
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
