"""
ember_qc/algorithms/factored/seat.py
=====================================
THE arrange engine (consolidation 7, s3.112): the lex engine —
crossfinder's loop shape on the ideal plane, one objective, one ruler
pair, no modes.

State: every variable's seat — an integer (col, row), carried, nothing
derived. Objective (proposer and judge are the same arithmetic), in
lexicographic (capacity, stair) order expressed as one scalar:

    E = pen * 2**26 + stair

    pen   = sum over (orientation, line, brick) of
            hinge^2(cover - pool)      [the BRICK ruler: one brick =
            grid.stride junctions = one qubit-length; demand-honest
            arms (a contact-free side deposits nothing); per-brick
            pools from wire_map — near-hard capacity]
    stair = sum of hull spans under the diagonal rule
            [the JUNCTION ruler — the sharp objective]

All quantities are integer-valued, so the scalar IS the tuple order
exactly (s3.110): capacity never trades against length; a search that
reaches pen 0 holds feasibility as an invariant thereafter. Hulls,
seats, and transverse line choices keep full junction resolution —
only the capacity accounting quantizes (s3.107/109: whole-brick
booking removes the phantom half-qubit savings; a brick holds one
junction of each parity, so whole-brick promises cannot be
parity-infeasible).

Moves, strict descent, deterministic:

1. ``best_interleave`` — the unit move (s3.111, Max's
   sliced-Wasserstein frame): evict a unit from one axis's order and
   re-insert at the exact optimum over ALL interleavings
   (``align_reinsert``'s DP), audited by the reference evaluator.
   A JUMP: it lands on the final state without traversing overloaded
   intermediates, so the hard capacity key cannot path-block it (the
   s3.110b lesson; jump + hard key together reach the turán crystal
   that either alone misses — s3.111b).
2. ``swap_sweep`` — pairwise seat swaps over source edges (x/y/both).
3. ``best_seat`` — one variable, every seat evaluated.
4. ``best_translate`` — one unit, every rigid in-window offset
   (cross-boundary contact flips priced in full — Max's catch).

Honesty contract: candidate scans are fast (per-line prefix arrays,
collision corrections omitted), but every chosen candidate is
RE-SCORED exactly before acceptance, so strict descent on the true
objective holds unconditionally; ``fast_miss`` counts scan/exact
disagreements (oracle-tested). The driver brackets the search with
``pack_project`` (init projection; family normalizer — s3.110: the
converter/completion stack is co-designed with packer-family states).
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

import numpy as np

from ember_qc.algorithms.factored.field import (
    TileGrid,
    _brick_pool_arrays,
    _stair_contacts,
    align_reinsert,
    line_pools,
)

Point = np.ndarray

# lexicographic weight: pen * M + stair is exact in floats (worst-case
# pen*M ~ 4e14 < 2^53) and M exceeds any reachable stair total (< 25k),
# so scalar comparison IS (pen, stair) tuple comparison
_LEX_M = float(2 ** 26)


def _arms(pos: Dict[int, Point], contacts) -> Dict[int, tuple]:
    """Integer arm intervals: (row, ha, hb, col, va, vb), endpoints
    inclusive, junction coordinates."""
    out = {}
    for v, (h_us, v_us) in contacts.items():
        x = int(round(float(pos[v][0])))
        y = int(round(float(pos[v][1])))
        xs = [int(round(float(pos[u][0]))) for u in h_us] + [x]
        ys = [int(round(float(pos[u][1]))) for u in v_us] + [y]
        out[v] = (y, min(xs), max(xs), x, min(ys), max(ys))
    return out


_ECACHE: dict = {}


def _edge_arrays(pos, src_adj):
    """Sorted vertex ids and the edge index arrays (u > v once), for
    the vectorized evaluator. Cached per (adjacency identity, vertex
    count) — one graph at a time (the gather evaluates ~12 candidates
    per call over the same graph; the per-edge Python walk was the
    s3.109 perf round's hog)."""
    key = (id(src_adj), len(pos))
    hit = _ECACHE.get(key)
    if hit is not None:
        return hit
    ids = sorted(pos)
    ix = {v: i for i, v in enumerate(ids)}
    A: List[int] = []
    B: List[int] = []
    for v in ids:
        for u in src_adj.get(v, []):
            if u > v and u in ix:
                A.append(ix[v])
                B.append(ix[u])
    out = (ids, np.asarray(A, dtype=np.int64),
           np.asarray(B, dtype=np.int64))
    _ECACHE.clear()
    _ECACHE[key] = out
    return out


def seat_energy(pos: Dict[int, Point], src_adj: Dict[int, List[int]],
                grid: TileGrid, yrank=None) -> float:
    """THE reference evaluator — the objective's definition.

    Vectorized (s3.109 perf round; verified == the per-edge original):
    the stair rule per edge is "the (y, id)-lower endpoint spends the
    h-arm" — or the carried y-order's rank when ``yrank`` is given
    (s3.118: the carried-order engines read ONE orientation book) —
    hulls come from scatter-min/max, cover from the diff-and-cumsum
    trick. All quantities are integer-valued, so sums are exact in
    any order."""
    s_cov = max(int(getattr(grid, "stride", 1)), 1)
    ids, A, B = _edge_arrays(pos, src_adj)
    n = len(ids)
    X = np.fromiter((int(round(float(pos[v][0]))) for v in ids),
                    dtype=np.int64, count=n)
    Y = np.fromiter((int(round(float(pos[v][1]))) for v in ids),
                    dtype=np.int64, count=n)
    if yrank is not None:
        R = np.fromiter((yrank[v] for v in ids), dtype=np.int64,
                        count=n)
        lower = R[A] < R[B]
    else:
        lower = (Y[A] < Y[B]) | ((Y[A] == Y[B]) & (A < B))
    L = np.where(lower, A, B)
    Hi = np.where(lower, B, A)
    hmin = X.copy()
    hmax = X.copy()
    vmin = Y.copy()
    vmax = Y.copy()
    if len(A):
        np.minimum.at(hmin, L, X[Hi])
        np.maximum.at(hmax, L, X[Hi])
        np.minimum.at(vmin, Hi, Y[L])
        np.maximum.at(vmax, Hi, Y[L])
    e = float((hmax - hmin).sum() + (vmax - vmin).sum())
    Wb = (grid.W + s_cov - 1) // s_cov
    Hb = (grid.H + s_cov - 1) // s_cov
    qhmin, qhmax = hmin // s_cov, hmax // s_cov
    qvmin, qvmax = vmin // s_cov, vmax // s_cov
    hcnt = np.zeros(n, dtype=np.int64)
    vcnt = np.zeros(n, dtype=np.int64)
    if len(A):
        np.add.at(hcnt, L, 1)
        np.add.at(vcnt, Hi, 1)
    hm = hcnt > 0
    vm = vcnt > 0
    Dh = np.zeros((grid.H, Wb + 1))
    Dv = np.zeros((grid.W, Hb + 1))
    np.add.at(Dh, (Y[hm], qhmin[hm]), 1.0)
    np.add.at(Dh, (Y[hm], qhmax[hm] + 1), -1.0)
    np.add.at(Dv, (X[vm], qvmin[vm]), 1.0)
    np.add.at(Dv, (X[vm], qvmax[vm] + 1), -1.0)
    Ch = np.cumsum(Dh, axis=1)[:, :Wb]
    Cv = np.cumsum(Dv, axis=1)[:, :Hb]
    ph, pv = _brick_pool_arrays(grid, s_cov)
    oh = np.maximum(Ch - ph, 0.0)
    ov = np.maximum(Cv - pv, 0.0)
    return float(e + _LEX_M * ((oh * oh).sum() + (ov * ov).sum()))


def _span_vectors(pos, src_adj, yrank):
    """Per-variable stair spans (s3.122 — the wave scheduler's
    disturbance ground truth): the (hspan, vspan) vectors whose sum
    is the stair energy under the carried y-order. Same
    one-direction-per-edge split as ``seat_energy``'s carried-rank
    rule (== ``_stair_contacts(yrank=...)``), but float coordinates —
    plane-mode states live at rank scale — and no cover terms.
    Returns (ids, hspan, vspan) with ids sorted."""
    ids, A, B = _edge_arrays(pos, src_adj)
    n = len(ids)
    X = np.fromiter((float(pos[v][0]) for v in ids),
                    dtype=np.float64, count=n)
    Y = np.fromiter((float(pos[v][1]) for v in ids),
                    dtype=np.float64, count=n)
    hmin = X.copy()
    hmax = X.copy()
    vmin = Y.copy()
    vmax = Y.copy()
    if len(A):
        R = np.fromiter((yrank[v] for v in ids), dtype=np.int64,
                        count=n)
        lower = R[A] < R[B]
        L = np.where(lower, A, B)
        Hi = np.where(lower, B, A)
        np.minimum.at(hmin, L, X[Hi])
        np.maximum.at(hmax, L, X[Hi])
        np.minimum.at(vmin, Hi, Y[L])
        np.maximum.at(vmax, Hi, Y[L])
    return ids, hmax - hmin, vmax - vmin


def judge_pools(grid):
    """s3.124: the sound judge's per-(line, brick) pools — EXACTLY the
    packer's profiles (one accounting): the `_brick_pool_arrays` census
    with the two boundary lines zeroed on both orientations, the
    measured s3.116 rule (count-4 boundary pools flooded 257+ deficits:
    boundary lines carry one course parity and are parity-starved at
    claim time). The phantom trailing brick stays 0. Memoized on the
    grid (the line_pools pattern). Returns (ph, pv): ph indexed
    [h-line (row), brick along x], pv indexed [v-line (col), brick
    along y]."""
    s = max(int(getattr(grid, "stride", 1) or 1), 1)
    cache = getattr(grid, "_judge_pools", None)
    if cache is not None and cache[0] == s:
        return cache[1]
    ph, pv = _brick_pool_arrays(grid, s)
    ph = np.array(ph, dtype=float, copy=True)
    pv = np.array(pv, dtype=float, copy=True)
    for arr in (ph, pv):
        if arr.shape[0] >= 2:
            arr[0, :] = 0.0
            arr[-1, :] = 0.0
    grid._judge_pools = (s, (ph, pv))
    return ph, pv


def _phantom_edge(arr) -> int:
    """Index of the first along-brick with zero pool on every line (the
    phantom trailing brick), or the array width when there is none."""
    nz = np.flatnonzero(arr.max(axis=0) > 0)
    return int(nz.max()) + 1 if nz.size else int(arr.shape[1])


def brick_energy(pos, src_adj, grid, yrank, *, pools, kappa=None,
                 floor=True) -> float:
    """s3.124 — the sound judge: brick-ruler lex energy on PHYSICAL
    coordinates, `pen * _LEX_M + stair`, where stair counts each
    active arm's span in WHOLE BRICKS (qubits — an upper bound on the
    real chain, the s3.107 ruler) and pen is the hinge² overload of
    per-(line, brick) cover against ``pools`` (`judge_pools`). Cover
    arrays are sized to the occupied extent: lines and bricks beyond
    the chip have pool 0, so an off-chip arm is PRICED, never clamped
    or wrapped (negative coordinates are asserted away — virtual
    coordinates are >= 0 and strips are >= 0). An endpoint landing in
    the phantom trailing brick is booked in the last real brick (the
    same legality `pack_lines`' nb_eff clamp grants — projection and
    judge agree there); endpoints beyond it are not clamped. Same
    one-direction-per-edge split as `seat_energy` (carried rank).

    ONE ACCOUNTING (measured, s3.124 smoke): the cover is booked on
    the CONVERTER's claim intervals — the `arm_books` rule: every
    variable's cross, a contact-free side as a one-tile footprint
    (b = a + 1), the kappa contact floor widening both axes — because
    that is what the converter seats; the s3.108 demand-honest census
    booked nothing for point arms and a pen-0 state then missed 10
    arms at conversion. Stair stays on ACTIVE arms only: a point arm
    is spur-pruned in the real chain, so it is capacity, not cost."""
    s = max(int(getattr(grid, "stride", 1) or 1), 1)
    ph, pv = pools
    ids, A, B = _edge_arrays(pos, src_adj)
    n = len(ids)
    if n == 0:
        return 0.0
    X = np.fromiter((int(round(float(pos[v][0]))) for v in ids),
                    dtype=np.int64, count=n)
    Y = np.fromiter((int(round(float(pos[v][1]))) for v in ids),
                    dtype=np.int64, count=n)
    assert X.min() >= 0 and Y.min() >= 0, "physical coordinates < 0"
    hmin = X.copy()
    hmax = X.copy()
    vmin = Y.copy()
    vmax = Y.copy()
    hcnt = np.zeros(n, dtype=np.int64)
    vcnt = np.zeros(n, dtype=np.int64)
    if len(A):
        R = np.fromiter((yrank[v] for v in ids), dtype=np.int64,
                        count=n)
        lower = R[A] < R[B]
        L = np.where(lower, A, B)
        Hi = np.where(lower, B, A)
        np.minimum.at(hmin, L, X[Hi])
        np.maximum.at(hmax, L, X[Hi])
        np.minimum.at(vmin, Hi, Y[L])
        np.maximum.at(vmax, Hi, Y[L])
        np.add.at(hcnt, L, 1)
        np.add.at(vcnt, Hi, 1)
    hm = hcnt > 0
    vm = vcnt > 0
    qhmin, qhmax = hmin // s, hmax // s
    qvmin, qvmax = vmin // s, vmax // s
    stair = float((qhmax[hm] - qhmin[hm] + 1).sum()
                  + (qvmax[vm] - qvmin[vm] + 1).sum())
    # cover on the books' claim intervals (the converter's truth):
    # kappa floor on the raw widths, then the one-tile footprint
    ah = hmin.astype(float)
    bh = hmax.astype(float)
    av = vmin.astype(float)
    bv = vmax.astype(float)
    if floor and kappa:
        deg = np.zeros(n)
        if len(A):
            np.add.at(deg, A, 1.0)
            np.add.at(deg, B, 1.0)
        need = deg / float(kappa) - 1.0
        deficit = need - ((bh - ah) + (bv - av))
        d4 = np.where(deficit > 0, deficit / 4.0, 0.0)
        ah = ah - d4
        bh = bh + d4
        av = av - d4
        bv = bv + d4
    bh = np.maximum(bh, ah + 1.0)
    bv = np.maximum(bv, av + 1.0)
    cqhmin = (np.maximum(np.floor(ah), 0.0).astype(np.int64)) // s
    cqhmax = (np.ceil(bh).astype(np.int64)) // s
    cqvmin = (np.maximum(np.floor(av), 0.0).astype(np.int64)) // s
    cqvmax = (np.ceil(bv).astype(np.int64)) // s
    # phantom absorption (both along axes)
    nbx = _phantom_edge(ph)
    nby = _phantom_edge(pv)
    cqhmin = np.where(cqhmin == nbx, nbx - 1, cqhmin)
    cqhmax = np.where(cqhmax == nbx, nbx - 1, cqhmax)
    cqvmin = np.where(cqvmin == nby, nby - 1, cqvmin)
    cqvmax = np.where(cqvmax == nby, nby - 1, cqvmax)
    pen = 0.0
    Hn, Wb = ph.shape
    Hpad = max(Hn, int(Y.max()) + 1)
    Wpad = max(Wb, int(cqhmax.max()) + 1)
    Dh = np.zeros((Hpad, Wpad + 1))
    np.add.at(Dh, (Y, cqhmin), 1.0)
    np.add.at(Dh, (Y, cqhmax + 1), -1.0)
    Ch = np.cumsum(Dh, axis=1)[:, :Wpad]
    PH = np.zeros((Hpad, Wpad))
    PH[:Hn, :Wb] = ph
    oh = np.maximum(Ch - PH, 0.0)
    pen += float((oh * oh).sum())
    Wn, Hb = pv.shape
    Wpad2 = max(Wn, int(X.max()) + 1)
    Hpad2 = max(Hb, int(cqvmax.max()) + 1)
    Dv = np.zeros((Wpad2, Hpad2 + 1))
    np.add.at(Dv, (X, cqvmin), 1.0)
    np.add.at(Dv, (X, cqvmax + 1), -1.0)
    Cv = np.cumsum(Dv, axis=1)[:, :Hpad2]
    PV = np.zeros((Wpad2, Hpad2))
    PV[:Wn, :Hb] = pv
    ov = np.maximum(Cv - PV, 0.0)
    pen += float((ov * ov).sum())
    return float(pen * _LEX_M + stair)


def row_overflow(pos, src_adj, yrank, *, H: int, s: int, kappa=None,
                 floor=True) -> float:
    """s3.125 strip — the capacity-first key beyond the chip's rows.
    hinge² cover per (line, brick) at pool 0 for every footprint that
    reaches a row the chip does not have: h-footprints on rows
    ``y >= H-1`` (the zeroed boundary row and everything above it,
    re-indexed from H-1) and v-footprints on bricks ``>= (H-1)//s``.
    Same claim intervals as `brick_energy` (rank split, kappa floor,
    one-tile footprint: a point arm still occupies its tile) and NO
    phantom absorption — an endpoint on the boundary row IS overflow.
    On-chip rows are deliberately not priced: the strip's y-pack is
    the uniform junction-depth pack and its own certificate."""
    ids, A, B = _edge_arrays(pos, src_adj)
    n = len(ids)
    if n == 0:
        return 0.0
    X = np.fromiter((int(round(float(pos[v][0]))) for v in ids),
                    dtype=np.int64, count=n)
    Y = np.fromiter((int(round(float(pos[v][1]))) for v in ids),
                    dtype=np.int64, count=n)
    assert X.min() >= 0 and Y.min() >= 0, "strip coordinates < 0"
    hmin = X.copy()
    hmax = X.copy()
    vmin = Y.copy()
    vmax = Y.copy()
    if len(A):
        R = np.fromiter((yrank[v] for v in ids), dtype=np.int64,
                        count=n)
        lower = R[A] < R[B]
        L = np.where(lower, A, B)
        Hi = np.where(lower, B, A)
        np.minimum.at(hmin, L, X[Hi])
        np.maximum.at(hmax, L, X[Hi])
        np.minimum.at(vmin, Hi, Y[L])
        np.maximum.at(vmax, Hi, Y[L])
    ah = hmin.astype(float)
    bh = hmax.astype(float)
    av = vmin.astype(float)
    bv = vmax.astype(float)
    if floor and kappa:
        deg = np.zeros(n)
        if len(A):
            np.add.at(deg, A, 1.0)
            np.add.at(deg, B, 1.0)
        need = deg / float(kappa) - 1.0
        deficit = need - ((bh - ah) + (bv - av))
        d4 = np.where(deficit > 0, deficit / 4.0, 0.0)
        ah = ah - d4
        bh = bh + d4
        av = av - d4
        bv = bv + d4
    bh = np.maximum(bh, ah + 1.0)
    bv = np.maximum(bv, av + 1.0)
    cqhmin = (np.maximum(np.floor(ah), 0.0).astype(np.int64)) // s
    cqhmax = (np.ceil(bh).astype(np.int64)) // s
    cqvmin = (np.maximum(np.floor(av), 0.0).astype(np.int64)) // s
    cqvmax = (np.ceil(bv).astype(np.int64)) // s
    pen = 0.0
    top = int(H) - 1
    hm = Y >= top
    if hm.any():
        rows = Y[hm] - top
        Wpad = int(cqhmax[hm].max()) + 1
        Dh = np.zeros((int(rows.max()) + 1, Wpad + 1))
        np.add.at(Dh, (rows, cqhmin[hm]), 1.0)
        np.add.at(Dh, (rows, cqhmax[hm] + 1), -1.0)
        Ch = np.cumsum(Dh, axis=1)[:, :Wpad]
        pen += float((Ch * Ch).sum())
    nby = top // s
    lo = np.maximum(cqvmin, nby)
    vm = cqvmax >= lo
    if vm.any():
        cols = X[vm]
        b0 = lo[vm] - nby
        b1 = cqvmax[vm] - nby
        Hpad = int(b1.max()) + 1
        Dv = np.zeros((int(cols.max()) + 1, Hpad + 1))
        np.add.at(Dv, (cols, b0), 1.0)
        np.add.at(Dv, (cols, b1 + 1), -1.0)
        Cv = np.cumsum(Dv, axis=1)[:, :Hpad]
        pen += float((Cv * Cv).sum())
    return float(pen)


def _ext4(vals: List[int]):
    """(min1, #min1, min2, max1, #max1, max2) for O(1) exclusion
    extremes; min2/max2 are +/-inf sentinels when absent."""
    s = sorted(vals)
    m1 = s[0]
    c1 = 1
    i = 1
    while i < len(s) and s[i] == m1:
        c1 += 1
        i += 1
    m2 = s[i] if i < len(s) else np.inf
    M1 = s[-1]
    C1 = 1
    j = len(s) - 2
    while j >= 0 and s[j] == M1:
        C1 += 1
        j -= 1
    M2 = s[j] if j >= 0 else -np.inf
    return (m1, c1, m2, M1, C1, M2)


def _excl_lo(e4, x):
    m1, c1, m2, _M1, _C1, _M2 = e4
    return m2 if (x == m1 and c1 == 1) else m1


def _excl_hi(e4, x):
    _m1, _c1, _m2, M1, C1, M2 = e4
    return M2 if (x == M1 and C1 == 1) else M1


class _Live:
    """Live books: contacts, arms, covers, prefix caches, exclusion
    extremes. Rebuilt from scratch on every accepted move (accepts are
    rare relative to evaluations; O(E) rebuild is measured cheap).

    Accounting convention: hull VALUES are junction coordinates;
    cover deposits map endpoints through ``// s_cov`` (the brick
    quantum) at the array boundary, stair spans stay raw.
    ``h_act``/``v_act`` mark demand-honest sides — only active sides
    carry a deposit (spans of inactive sides are 0 by construction,
    so span arithmetic never branches).
    """

    def __init__(self, pos, src_adj, grid):
        self.pos = pos
        self.adj = src_adj
        self.grid = grid
        self.s_cov = max(int(getattr(grid, "stride", 1)), 1)
        self.w = _LEX_M
        self.pool_h2, self.pool_v2 = _brick_pool_arrays(grid,
                                                        self.s_cov)
        self.rebuild()

    def rebuild(self):
        self.xi = {v: int(round(float(p[0])))
                   for v, p in self.pos.items()}
        self.yi = {v: int(round(float(p[1])))
                   for v, p in self.pos.items()}
        self.contacts = _stair_contacts(self.pos, self.adj)
        self.arms = _arms(self.pos, self.contacts)
        self.h_act = {v: bool(c[0])
                      for v, c in self.contacts.items()}
        self.v_act = {v: bool(c[1])
                      for v, c in self.contacts.items()}
        sc = self.s_cov
        Wb = (self.grid.W + sc - 1) // sc
        Hb = (self.grid.H + sc - 1) // sc
        self.Ch = np.zeros((self.grid.H, Wb), dtype=float)
        self.Cv = np.zeros((self.grid.W, Hb), dtype=float)
        e = 0.0
        for v, (row, ha, hb, col, va, vb) in self.arms.items():
            e += float((hb - ha) + (vb - va))
            if self.h_act[v]:
                self.Ch[row, ha // sc:hb // sc + 1] += 1.0
            if self.v_act[v]:
                self.Cv[col, va // sc:vb // sc + 1] += 1.0
        self.e_stair = e
        assert self.e_stair < _LEX_M, "stair total exceeds the lex " \
                                      "weight — raise _LEX_M"
        oh = np.maximum(self.Ch - self.pool_h2, 0.0)
        ov = np.maximum(self.Cv - self.pool_v2, 0.0)
        self.pen = float((oh * oh).sum() + (ov * ov).sum())
        self.E = self.e_stair + self.w * self.pen
        # exclusion-extreme caches per hull (values incl. own coord)
        self.hx4 = {}
        self.vy4 = {}
        for v, (h_us, v_us) in self.contacts.items():
            self.hx4[v] = _ext4([self.xi[u] for u in h_us]
                                + [self.xi[v]])
            self.vy4[v] = _ext4([self.yi[u] for u in v_us]
                                + [self.yi[v]])

    def _pen_of(self, Ch, Cv):
        oh = np.maximum(Ch - self.pool_h2, 0.0)
        ov = np.maximum(Cv - self.pool_v2, 0.0)
        return float((oh * oh).sum() + (ov * ov).sum())

    # ---- the without-v world (shared by scan and audit) ----
    def without(self, v):
        """Remove v's influence: its arms, and each neighbour's hull
        shrunk to its exclusion extremes. Returns (Ch2, Cv2, e_wo,
        nb_wo) where nb_wo[u] = (side, row/col, without-v hull,
        still-deposited flag)."""
        sc = self.s_cov
        Ch2 = self.Ch.copy()
        Cv2 = self.Cv.copy()
        row, ha, hb, col, va, vb = self.arms[v]
        if self.h_act[v]:
            Ch2[row, ha // sc:hb // sc + 1] -= 1.0
        if self.v_act[v]:
            Cv2[col, va // sc:vb // sc + 1] -= 1.0
        e_wo = self.e_stair - float((hb - ha)
                                    + (vb - va))
        nb_wo = {}
        for u in self.adj.get(v, []):
            if u not in self.pos or u == v:
                continue
            urow, uha, uhb, ucol, uva, uvb = self.arms[u]
            if v in set(self.contacts[u][0]):
                # v was in u's h-net: shrink u's h-arm
                na = int(_excl_lo(self.hx4[u], self.xi[v]))
                nb = int(_excl_hi(self.hx4[u], self.xi[v]))
                act2 = len(self.contacts[u][0]) > 1
                if not act2:
                    # u's h-net was {v}: the deposit goes entirely
                    Ch2[urow, uha // sc:uhb // sc + 1] -= 1.0
                    e_wo -= float(uhb - uha)
                elif (na, nb) != (uha, uhb):
                    Ch2[urow, uha // sc:uhb // sc + 1] -= 1.0
                    Ch2[urow, na // sc:nb // sc + 1] += 1.0
                    e_wo -= float((uhb - uha)
                                  - (nb - na))
                nb_wo[u] = (1, urow, na, nb, act2)
            else:
                # v was in u's v-net: shrink u's v-arm
                na = int(_excl_lo(self.vy4[u], self.yi[v]))
                nb = int(_excl_hi(self.vy4[u], self.yi[v]))
                act2 = len(self.contacts[u][1]) > 1
                if not act2:
                    Cv2[ucol, uva // sc:uvb // sc + 1] -= 1.0
                    e_wo -= float(uvb - uva)
                elif (na, nb) != (uva, uvb):
                    Cv2[ucol, uva // sc:uvb // sc + 1] -= 1.0
                    Cv2[ucol, na // sc:nb // sc + 1] += 1.0
                    e_wo -= float((uvb - uva)
                                  - (nb - na))
                nb_wo[u] = (0, ucol, na, nb, act2)
        return Ch2, Cv2, e_wo, nb_wo

    def exact_full(self, v, c, r, wo):
        """Exact E with v at (c, r), built from the without-v world.
        Handles the role assignment cleanly: for each neighbour u,
        v joins exactly one of u's nets by the stair rule at the NEW
        coordinates, extending u's without-v hull on that side."""
        sc = self.s_cov
        Ch2, Cv2, e_wo, nb_wo = wo
        Ch3 = Ch2.copy()
        Cv3 = Cv2.copy()
        e = e_wo
        h_vals = [c]
        v_vals = [r]
        for u in self.adj.get(v, []):
            if u not in self.pos or u == v:
                continue
            ux, uy = self.xi[u], self.yi[u]
            if (r, v) < (uy, u):
                h_vals.append(ux)         # v reaches u's column
                ext_side = 0              # u's v-arm reaches v's row r
                ext_val = r
            else:
                v_vals.append(uy)         # v reaches u's row
                ext_side = 1              # u's h-arm reaches v's col c
                ext_val = c
            # u's hull on ext_side: without-v hull, extended by ext_val
            urow, _uha, _uhb, ucol, _uva, _uvb = self.arms[u]
            if u in nb_wo and nb_wo[u][0] == ext_side:
                _so, line, na, nb, act2 = nb_wo[u]
            else:
                # u's other-side hull is untouched by v's removal
                if ext_side == 1:
                    line = urow
                    na, nb = self.arms[u][1], self.arms[u][2]
                    act2 = self.h_act[u]
                else:
                    line = ucol
                    na, nb = self.arms[u][4], self.arms[u][5]
                    act2 = self.v_act[u]
            na2, nb2 = min(na, ext_val), max(nb, ext_val)
            if not act2:
                # u's net on this side was empty; v joins it: the
                # deposit is fresh even when the hull is unchanged
                if ext_side == 1:
                    Ch3[line, na2 // sc:nb2 // sc + 1] += 1.0
                else:
                    Cv3[line, na2 // sc:nb2 // sc + 1] += 1.0
                e += float((nb2 - na2)
                           - (nb - na))
            elif (na2, nb2) != (na, nb):
                if ext_side == 1:
                    Ch3[line, na // sc:nb // sc + 1] -= 1.0
                    Ch3[line, na2 // sc:nb2 // sc + 1] += 1.0
                else:
                    Cv3[line, na // sc:nb // sc + 1] -= 1.0
                    Cv3[line, na2 // sc:nb2 // sc + 1] += 1.0
                e += float((nb2 - na2)
                           - (nb - na))
        ha, hb = min(h_vals), max(h_vals)
        va, vb = min(v_vals), max(v_vals)
        if len(h_vals) > 1:
            Ch3[r, ha // sc:hb // sc + 1] += 1.0
        if len(v_vals) > 1:
            Cv3[c, va // sc:vb // sc + 1] += 1.0
        e += float((hb - ha) + (vb - va))
        return e + self.w * self._pen_of(Ch3, Cv3)


def _fast_seat_grid(live: _Live, v, wo):
    """Fast scan over all seats (H x W grid of totals; lower better).
    Prefix-array pricing; same-line collision corrections omitted (the
    exact audit absorbs them)."""
    grid = live.grid
    W, H = grid.W, grid.H
    w_cap = live.w
    sc = live.s_cov
    Ch2, Cv2, e_wo, nb_wo = wo
    nbrs = [u for u in live.adj.get(v, []) if u in live.pos and u != v]
    xv = live.xi
    yv = live.yi

    def _gain_prefix(C, pool2):
        g = w_cap * ((np.maximum(C + 1.0 - pool2, 0.0) ** 2)
                     - (np.maximum(C - pool2, 0.0) ** 2))
        P = np.zeros((C.shape[0], C.shape[1] + 1))
        np.cumsum(g, axis=1, out=P[:, 1:])
        return P

    Ph = _gain_prefix(Ch2, live.pool_h2)
    Pv = _gain_prefix(Cv2, live.pool_v2)
    oh = np.maximum(Ch2 - live.pool_h2, 0.0)
    ov = np.maximum(Cv2 - live.pool_v2, 0.0)
    pen_wo = w_cap * float((oh * oh).sum() + (ov * ov).sum())

    cc = np.arange(W, dtype=int)
    total = np.full((H, W), e_wo + pen_wo, dtype=float)

    for r in range(H):
        h_us = [u for u in nbrs if (r, v) < (yv[u], u)]
        v_us = [u for u in nbrs if not (r, v) < (yv[u], u)]
        if h_us:
            lo = min(xv[u] for u in h_us)
            hi = max(xv[u] for u in h_us)
            ha = np.minimum(cc, lo)
            hb = np.maximum(cc, hi)
        else:
            ha = cc
            hb = cc
        if h_us:
            row_total = (total[r]
                         + (hb - ha).astype(float)
                         + Ph[r, hb // sc + 1] - Ph[r, ha // sc])
        else:
            row_total = total[r] + 0.0
        if v_us:
            rlo = min(yv[u] for u in v_us)
            rhi = max(yv[u] for u in v_us)
            va, vb = min(rlo, r), max(rhi, r)
        else:
            va, vb = r, r
        if v_us:
            row_total = (row_total + float(vb - va)
                         + Pv[cc, vb // sc + 1] - Pv[cc, va // sc])
        for u in nbrs:
            ux, uy = xv[u], yv[u]
            if (r, v) < (uy, u):
                ext_side, ext_is_grid = 0, False   # u's v-arm to row r
            else:
                ext_side, ext_is_grid = 1, True    # u's h-arm to col c
            if u in nb_wo and nb_wo[u][0] == ext_side:
                _so, line, na, nb, act2 = nb_wo[u]
            else:
                if ext_side == 1:
                    line, na, nb = (live.arms[u][0], live.arms[u][1],
                                    live.arms[u][2])
                    act2 = live.h_act[u]
                else:
                    line, na, nb = (live.arms[u][3], live.arms[u][4],
                                    live.arms[u][5])
                    act2 = live.v_act[u]
            if ext_is_grid:
                na2 = np.minimum(na, cc)
                nb2 = np.maximum(nb, cc)
                d = ((nb2 - na2)
                     - (nb - na)).astype(float)
                if act2:
                    dpen = ((Ph[line, nb2 // sc + 1]
                             - Ph[line, na2 // sc])
                            - (Ph[line, nb // sc + 1]
                               - Ph[line, na // sc]))
                else:
                    dpen = (Ph[line, nb2 // sc + 1]
                            - Ph[line, na2 // sc])
                row_total = row_total + d + dpen
            else:
                na2, nb2 = min(na, r), max(nb, r)
                d = float((nb2 - na2)
                          - (nb - na))
                if act2:
                    dpen = float((Pv[line, nb2 // sc + 1]
                                  - Pv[line, na2 // sc])
                                 - (Pv[line, nb // sc + 1]
                                    - Pv[line, na // sc]))
                else:
                    dpen = float(Pv[line, nb2 // sc + 1]
                                 - Pv[line, na2 // sc])
                row_total = row_total + d + dpen
        total[r] = row_total
    return total


def best_seat(v, pos, src_adj, grid, *, e_cur, info, live=None):
    """Try every seat for ``v``; exact (array-patch) re-score of the
    top fast candidates; strict descent. Returns (new_pos, new_E) or
    None."""
    if live is None:
        live = _Live({u: p.copy() for u, p in pos.items()},
                     src_adj, grid)
    wo = live.without(v)
    scores = _fast_seat_grid(live, v, wo)
    r0, c0 = live.yi[v], live.xi[v]
    flat = np.argsort(scores, axis=None, kind="stable")
    tried = 0
    for k in flat[:4]:
        r, c = int(k) // grid.W, int(k) % grid.W
        if (r, c) == (r0, c0):
            break
        e_new = live.exact_full(v, c, r, wo)
        tried += 1
        if e_new < e_cur - 1e-9:
            if tried > 1:
                info["fast_miss"] += 1
            cand = {u: p.copy() for u, p in live.pos.items()}
            cand[v] = np.array([float(c), float(r)])
            return cand, e_new
    if tried:
        info["fast_miss"] += 1
    return None


def _unit_boundary(unit_set, pos, src_adj):
    B = set()
    for w in unit_set:
        for u in src_adj.get(w, []):
            if u in pos and u not in unit_set:
                B.add(w)
                B.add(u)
    return B


def best_translate(unit, pos, src_adj, grid, *, e_cur, info,
                   live=None):
    """Every rigid in-window offset for ``unit``; exact per-offset
    delta (boundary hulls recomputed in full — cross-boundary contact
    flips included, Max's catch — plus the moved cover field, applied
    to real arrays). Deterministic work bound coarsens the offset grid
    when the exact scan would be enormous."""
    U = sorted(w for w in unit if w in pos)
    if len(U) < 2:
        return None
    if live is None:
        live = _Live({u: p.copy() for u, p in pos.items()},
                     src_adj, grid)
    sc = live.s_cov
    Uset = set(U)
    cols = [live.xi[w] for w in U]
    rows = [live.yi[w] for w in U]
    dr_lo, dr_hi = -min(rows), (grid.H - 1) - max(rows)
    dc_lo, dc_hi = -min(cols), (grid.W - 1) - max(cols)
    if dr_hi < dr_lo or dc_hi < dc_lo:
        return None

    arms = live.arms
    B = _unit_boundary(Uset, live.pos, src_adj)
    touched = Uset | B
    Ch_wo = live.Ch.copy()
    Cv_wo = live.Cv.copy()
    old_span = {}
    for w in touched:
        row, ha, hb, col, va, vb = arms[w]
        if live.h_act[w]:
            Ch_wo[row, ha // sc:hb // sc + 1] -= 1.0
        if live.v_act[w]:
            Cv_wo[col, va // sc:vb // sc + 1] -= 1.0
        old_span[w] = float((hb - ha)
                            + (vb - va))
    xi, yi = live.xi, live.yi
    reshaped = sorted(B)
    rigid = [w for w in U if w not in B]

    def _delta(dr, dc):
        Ch2 = Ch_wo.copy()
        Cv2 = Cv_wo.copy()
        d_stair = 0.0
        for w in rigid:
            row, ha, hb, col, va, vb = arms[w]
            if live.h_act[w]:
                Ch2[row + dr,
                    (ha + dc) // sc:(hb + dc) // sc + 1] += 1.0
            if live.v_act[w]:
                Cv2[col + dc,
                    (va + dr) // sc:(vb + dr) // sc + 1] += 1.0
        for w in reshaped:
            inU = w in Uset
            wx = xi[w] + (dc if inU else 0)
            wy = yi[w] + (dr if inU else 0)
            xs = [wx]
            ys = [wy]
            for u in src_adj.get(w, []):
                if u not in live.pos or u == w:
                    continue
                ux = xi[u] + (dc if u in Uset else 0)
                uy = yi[u] + (dr if u in Uset else 0)
                if (wy, w) < (uy, u):
                    xs.append(ux)
                else:
                    ys.append(uy)
            ha, hb = min(xs), max(xs)
            va, vb = min(ys), max(ys)
            if len(xs) > 1:
                Ch2[wy, ha // sc:hb // sc + 1] += 1.0
            if len(ys) > 1:
                Cv2[wx, va // sc:vb // sc + 1] += 1.0
            d_stair += (float((hb - ha)
                              + (vb - va)) - old_span[w])
        return (live.e_stair + d_stair
                + live.w * live._pen_of(Ch2, Cv2))

    per_off = (len(rigid)
               + sum(len(src_adj.get(w, [])) for w in reshaped)
               + grid.W * grid.H)
    n_off = (dr_hi - dr_lo + 1) * (dc_hi - dc_lo + 1)
    budget = 250_000
    if per_off * 2 > budget:
        return None   # even a handful of offsets would blow the budget
    stride = 1
    while per_off * (n_off // (stride * stride) + 1) > budget:
        stride += 1
    base = _delta(0, 0)
    best_dr = best_dc = None
    best_val = None
    for dr in range(dr_lo, dr_hi + 1, stride):
        for dc in range(dc_lo, dc_hi + 1, stride):
            if dr == 0 and dc == 0:
                continue
            val = _delta(dr, dc)
            if best_val is None or val < best_val - 1e-12:
                best_val, best_dr, best_dc = val, dr, dc
    if best_val is None or best_val >= base - 1e-9:
        return None
    if best_val < e_cur - 1e-9:
        cand = {u: p.copy() for u, p in live.pos.items()}
        for w in U:
            cand[w] = live.pos[w] + np.array([float(best_dc),
                                              float(best_dr)])
        return cand, best_val
    info["fast_miss"] += 1
    return None


def _swap_exact(live: _Live, u, w, mode):
    """Exact E after swapping u's and w's coordinates — ``mode`` in
    {"x", "y", "b"} (x-only, y-only, both). O(deg) per attempt: every
    third-party t sees u (and w) as one (side, value) entry in its
    hulls; the swap removes the old entry and adds the new one, with
    extremes maintained by the ext4 caches. Pairs with common
    neighbours fall back to per-t recompute (skipped when large — a
    work bound, not a rule). Returns new E or None (skipped)."""
    adj = live.adj
    sc = live.s_cov
    xi, yi = live.xi, live.yi
    Nu = [t for t in adj.get(u, []) if t in live.pos and t != u]
    Nw = [t for t in adj.get(w, []) if t in live.pos and t != w]
    common = set(Nu) & set(Nw)
    if len(common) > 64:
        return None
    nx_u, ny_u = xi[u], yi[u]
    nx_w, ny_w = xi[w], yi[w]
    if mode in ("x", "b"):
        nx_u, nx_w = xi[w], xi[u]
    if mode in ("y", "b"):
        ny_u, ny_w = yi[w], yi[u]
    if (nx_u, ny_u) == (xi[u], yi[u]):
        return None
    newx = dict(xi)
    newy = dict(yi)
    newx[u], newy[u] = nx_u, ny_u
    newx[w], newy[w] = nx_w, ny_w

    def _hulls_scratch(t):
        xs = [newx[t]]
        ys = [newy[t]]
        for t2 in adj.get(t, []):
            if t2 not in live.pos or t2 == t:
                continue
            if (newy[t], t) < (newy[t2], t2):
                xs.append(newx[t2])
            else:
                ys.append(newy[t2])
        nh_act = len(xs) > 1
        nv_act = len(ys) > 1
        return ((min(xs), max(xs), nh_act),
                (min(ys), max(ys), nv_act))

    def _third(t, m):
        """t's new hulls in O(1): t sees only ``m`` (one of u, w)
        change — remove m's old (side, value) entry via the ext4
        caches, add its new one. When m's side ASSIGNMENT flips (a
        y-move can migrate m between t's h-net and v-net), the net
        sizes change with it — the active flags are recomputed from
        the migration, not carried over."""
        row, ha, hb, col, va, vb = live.arms[t]
        old_h = (yi[t], t) < (yi[m], m)     # m was above t: h-side
        new_h = (yi[t], t) < (newy[m], m)
        n_h = len(live.contacts[t][0])
        n_v = len(live.contacts[t][1])
        if old_h:
            base_h = (int(_excl_lo(live.hx4[t], xi[m])),
                      int(_excl_hi(live.hx4[t], xi[m])))
            base_v = (va, vb)
            n_h -= 1
        else:
            base_h = (ha, hb)
            base_v = (int(_excl_lo(live.vy4[t], yi[m])),
                      int(_excl_hi(live.vy4[t], yi[m])))
            n_v -= 1
        if new_h:
            nh = (min(base_h[0], newx[m]), max(base_h[1], newx[m]))
            nv = base_v
            n_h += 1
        else:
            nh = base_h
            nv = (min(base_v[0], newy[m]), max(base_v[1], newy[m]))
            n_v += 1
        nh_act = n_h > 0
        nv_act = n_v > 0
        return nh, nv, nh_act, nv_act

    # diffs: (orient, line_old, iv_old, act_old, line_new, iv_new,
    #         act_new)
    diffs = []
    d_stair = 0.0
    seen = set()
    for t in sorted({u, w} | set(Nu) | set(Nw)):
        if t in seen:
            continue
        seen.add(t)
        row, ha, hb, col, va, vb = live.arms[t]
        h_act0, v_act0 = live.h_act[t], live.v_act[t]
        if t == u or t == w or t in common:
            ((nha, nhb, nh_act),
             (nva, nvb, nv_act)) = _hulls_scratch(t)
        elif t in set(Nu):
            (nha, nhb), (nva, nvb), nh_act, nv_act = _third(t, u)
        else:
            (nha, nhb), (nva, nvb), nh_act, nv_act = _third(t, w)
        nrow, ncol = newy[t], newx[t]
        if (nrow, nha, nhb, nh_act) != (row, ha, hb, h_act0):
            diffs.append((1, row, (ha, hb), h_act0,
                          nrow, (nha, nhb), nh_act))
        if (ncol, nva, nvb, nv_act) != (col, va, vb, v_act0):
            diffs.append((0, col, (va, vb), v_act0,
                          ncol, (nva, nvb), nv_act))
        d_stair += (float((nhb - nha)
                          + (nvb - nva))
                    - float((hb - ha)
                            + (vb - va)))
    if not diffs:
        return None
    Ch2 = live.Ch.copy()
    Cv2 = live.Cv.copy()
    for o, l0, (a0, b0), act0, l1, (a1, b1), act1 in diffs:
        A = Ch2 if o == 1 else Cv2
        if act0:
            A[l0, a0 // sc:b0 // sc + 1] -= 1.0
        if act1:
            A[l1, a1 // sc:b1 // sc + 1] += 1.0
    return (live.e_stair + d_stair
            + live.w * live._pen_of(Ch2, Cv2))


def best_interleave(unit, pos, src_adj, grid, *, e_cur, info,
                    live=None):
    """The insertion DP resurrected as a one-court move (s3.111,
    Max's sliced-Wasserstein frame): evict unit U from one axis's
    coordinate order and re-insert it at the EXACT optimum over ALL
    interleavings — ``align_reinsert``'s s3.100 machinery
    (induced-rule pricing on y, frozen contacts on x, forward and
    reversed arms), handing the same value multiset back by rank
    (the gather's idiom; the gather's contiguous family is a strict
    subset of this one). The DP's interior prices the
    frozen-other-axis stair exactly and is capacity-blind; the single
    candidate per axis is AUDITED by the reference evaluator and
    accepted only on strict descent of the true objective. One court:
    a decline costs one evaluation, never a rejection cycle — near
    the optimum almost every call certifies "already optimal for this
    (set, axis)" (interleave_noops), and the audit's few declines
    (interleave_declines) are the measured answer to whether the DP
    interior ever needs a capacity term. As a JUMP move it cannot be
    path-blocked: in lex mode it lands directly on the best final
    interleaving without traversing overloaded intermediates (the
    s3.110b lesson's named counter-move)."""
    U = sorted(w for w in unit if w in pos)
    if len(U) < 2 or len(U) >= len(pos):
        return None
    contacts = (live.contacts if live is not None
                else _stair_contacts(pos, src_adj))
    best = None
    best_e = e_cur - 1e-9
    for axis in (1, 0):
        order = sorted(pos, key=lambda v: (float(pos[v][axis]), v))
        vals = sorted(float(pos[v][axis]) for v in order)
        other = {v: float(pos[v][1 - axis]) for v in pos}
        new_order, _flip = align_reinsert(
            order, U, src_adj, vals, None, axis=axis, other=other,
            contacts=contacts)
        if new_order is None:
            info["interleave_noops"] += 1   # view-local optimum
            continue
        cand = {v: p.copy() for v, p in pos.items()}
        for r, v in enumerate(new_order):
            cand[v][axis] = float(vals[r])
        e2 = seat_energy(cand, src_adj, grid)
        if e2 < best_e:
            best_e = e2
            best = cand
        else:
            info["interleave_declines"] += 1
    if best is not None:
        return best, best_e
    return None


def swap_sweep(pos, src_adj, grid, *, e_cur, info, live,
               deadline=None, max_sweeps: int = 8):
    """Pairwise seat swaps over source edges, all three variants,
    strict descent — the sorting network the crystal's ORDER needs,
    including the y-variants monotonize cannot express (they flip
    contacts; priced exactly here). Returns (pos, e_cur, live)."""
    import time as _time
    edges = sorted((v, u) for v in pos
                   for u in src_adj.get(v, []) if u in pos and u > v)
    for _ in range(max(max_sweeps, 1)):
        if deadline is not None and _time.perf_counter() > deadline:
            break
        improved = False
        for (v, u) in edges:
            best_mode = None
            best_e = e_cur - 1e-9
            for mode in ("x", "y", "b"):
                e2 = _swap_exact(live, v, u, mode)
                if e2 is not None and e2 < best_e:
                    best_e, best_mode = e2, mode
            if best_mode is not None:
                if best_mode in ("x", "b"):
                    pos[v][0], pos[u][0] = pos[u][0], pos[v][0]
                if best_mode in ("y", "b"):
                    pos[v][1], pos[u][1] = pos[u][1], pos[v][1]
                live = _Live(pos, src_adj, grid)
                e_cur = live.E
                info["swap_accepts"] += 1
                improved = True
        if not improved:
            break
    return pos, e_cur, live


def seat_arrange(pos0: Dict[int, Point], src_adj: Dict[int, List[int]],
                 grid: TileGrid, units, *,
                 deadline: Optional[float] = None):
    """Passes of moves until an accept-free pass or the deadline:
    every unit via best_interleave (coarsest first — the jump move),
    then, once the coarse phase reaches its fixpoint, swap sweeps,
    every variable via best_seat, and every unit via best_translate
    (the s3.81 ladder: coarse moves to their own fixpoint FIRST).
    Positions and the candidate lattice stay at junction resolution;
    the objective is the module's single lexicographic scalar."""
    import time as _time
    if not getattr(grid, "typed", False) or not line_pools(grid):
        return ({v: p.copy() for v, p in pos0.items()},
                {"seat_accepts": 0, "trans_accepts": 0, "passes": 0,
                 "accept_traj": [], "fast_miss": 0, "seat_E": None,
                 "seat_pen": None, "seat_stair": None})
    pos = {v: np.asarray(p, dtype=float).copy() for v, p in pos0.items()}
    for v in pos:
        pos[v][0] = float(min(max(int(round(pos[v][0])), 0), grid.W - 1))
        pos[v][1] = float(min(max(int(round(pos[v][1])), 0), grid.H - 1))
    live = _Live(pos, src_adj, grid)
    e_cur = live.E
    info = {"seat_accepts": 0, "trans_accepts": 0, "passes": 0,
            "accept_traj": [], "fast_miss": 0, "swap_accepts": 0,
            "interleave_accepts": 0, "interleave_declines": 0,
            "interleave_noops": 0}
    unit_lists = []
    if units:
        for level in reversed(list(units)):
            for cl in sorted(level, key=lambda g: (-len(g), g)):
                if len(cl) >= 2:
                    unit_lists.append(sorted(cl))

    coarse_phase = True   # s3.81 ladder: coarse moves to their own
    #                       fixpoint FIRST — greedy fine moves narrow
    #                       the coarse basin (the ball-first lesson)
    while True:
        if deadline is not None and _time.perf_counter() > deadline:
            break
        info["passes"] += 1
        accepts = 0
        for cl in unit_lists:
            if (deadline is not None
                    and _time.perf_counter() > deadline):
                break
            res = best_interleave(cl, pos, src_adj, grid,
                                  e_cur=e_cur, info=info, live=live)
            if res is not None:
                pos, e_cur = res
                live = _Live(pos, src_adj, grid)
                info["interleave_accepts"] += 1
                accepts += 1
        pre_swaps = info["swap_accepts"]
        if not coarse_phase:
            pos, e_cur, live = swap_sweep(
                pos, src_adj, grid, e_cur=e_cur, info=info,
                live=live, deadline=deadline, max_sweeps=1)
        accepts += info["swap_accepts"] - pre_swaps
        for v in (sorted(pos) if not coarse_phase else ()):
            if (deadline is not None
                    and _time.perf_counter() > deadline):
                break
            res = best_seat(v, pos, src_adj, grid,
                            e_cur=e_cur, info=info, live=live)
            if res is not None:
                pos, e_cur = res
                live = _Live(pos, src_adj, grid)
                info["seat_accepts"] += 1
                accepts += 1
        for cl in unit_lists:
            if (deadline is not None
                    and _time.perf_counter() > deadline):
                break
            res = best_translate(cl, pos, src_adj, grid,
                                 e_cur=e_cur, info=info, live=live)
            if res is not None:
                pos, e_cur = res
                live = _Live(pos, src_adj, grid)
                info["trans_accepts"] += 1
                accepts += 1
        # per-pass honesty cross-check: live books vs the reference
        e_ref = seat_energy(pos, src_adj, grid)
        if abs(e_ref - e_cur) > 1e-6:
            info["fast_miss"] += 1000   # loud drift marker
            e_cur = e_ref
            live = _Live(pos, src_adj, grid)
        info["accept_traj"].append(accepts)
        if accepts == 0:
            if coarse_phase:
                coarse_phase = False   # release the fine moves
                continue
            break
    info["seat_E"] = round(e_cur, 1)
    # the composite made legible: capacity and length reported apart
    # (seat_pen == 0 means feasibility was reached and held as an
    # invariant)
    info["seat_pen"] = round(live.pen, 1)
    info["seat_stair"] = round(live.e_stair, 1)
    return pos, info
