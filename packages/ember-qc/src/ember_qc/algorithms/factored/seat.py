"""
ember_qc/algorithms/factored/seat.py
=====================================
The seat engine (s3.102): crossfinder's loop shape on the IDEAL plane.

State: every variable's seat — an integer (col, row), carried, nothing
derived. Objective (proposer and judge are the same arithmetic):

    E = raw stair energy (hull spans under the diagonal rule)
        + lam * sum over (orientation, line, tile) of
                hinge^2(cover count - lane pool)

where an arm's footprint is its integer hull, endpoints inclusive (a
point arm covers its tile — the s3.76 occupancy lesson, free here), and
pools come from ``line_pools``. Capacity is a COUNT, not a claim: the
two recorded crossfinder killers (exclusive-claim deadlock; unable to
route around claimed bands, notes s3.90) have no referent.

Moves, both strict descent, deterministic:

1. ``best_seat``  — one variable, every in-window seat evaluated.
2. ``best_translate`` — one hierarchy unit, every in-window rigid
   offset. Internal edges are invariant under translation (equal shift
   preserves relative y-order); CROSS-BOUNDARY edges can flip the
   h-arm/v-arm assignment (Max's catch, 2026-08-20), so every vertex
   incident to a boundary edge gets its hulls fully recomputed.

Honesty contract: candidate scans are fast (per-line prefix arrays,
collision corrections omitted), but every chosen candidate is
RE-SCORED exactly — by applying its cover deltas to real arrays, which
is multiset-correct by construction — before acceptance, so strict
descent on the true objective holds unconditionally. ``fast_miss``
counts scan/exact disagreements (oracle-tested in the suite). The
capacity here is SOFT (a price); the driver's caller runs one exact
hard-capacity pack on the result (the single remaining conversion).
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

import numpy as np

from ember_qc.algorithms.factored.field import (
    TileGrid,
    _stair_contacts,
    line_pools,
    stair_energy,
)

Point = np.ndarray


def _pool_arrays(grid: TileGrid):
    lp = line_pools(grid)
    pool_h = np.zeros(grid.H, dtype=float)
    pool_v = np.zeros(grid.W, dtype=float)
    for (o, ln), p in lp.items():
        if o == 1 and 0 <= ln < grid.H:
            pool_h[ln] = p
        elif o == 0 and 0 <= ln < grid.W:
            pool_v[ln] = p
    return pool_h, pool_v


def _arms(pos: Dict[int, Point], contacts) -> Dict[int, tuple]:
    """Integer arm intervals: (row, ha, hb, col, va, vb), endpoints
    inclusive."""
    out = {}
    for v, (h_us, v_us) in contacts.items():
        x = int(round(float(pos[v][0])))
        y = int(round(float(pos[v][1])))
        xs = [int(round(float(pos[u][0]))) for u in h_us] + [x]
        ys = [int(round(float(pos[u][1]))) for u in v_us] + [y]
        out[v] = (y, min(xs), max(xs), x, min(ys), max(ys))
    return out


def _cover_arrays(arms, grid: TileGrid):
    Ch = np.zeros((grid.H, grid.W), dtype=float)   # h-arms: [row, col]
    Cv = np.zeros((grid.W, grid.H), dtype=float)   # v-arms: [col, row]
    for (row, ha, hb, col, va, vb) in arms.values():
        Ch[row, ha:hb + 1] += 1.0
        Cv[col, va:vb + 1] += 1.0
    return Ch, Cv


def seat_energy(pos: Dict[int, Point], src_adj: Dict[int, List[int]],
                grid: TileGrid, *, lam: float = 1.0) -> float:
    """THE reference evaluator — the objective's definition."""
    contacts = _stair_contacts(pos, src_adj)
    e = stair_energy(pos, src_adj, contacts=contacts)
    arms = _arms(pos, contacts)
    Ch, Cv = _cover_arrays(arms, grid)
    pool_h, pool_v = _pool_arrays(grid)
    oh = np.maximum(Ch - pool_h[:, None], 0.0)
    ov = np.maximum(Cv - pool_v[:, None], 0.0)
    return float(e + lam * ((oh * oh).sum() + (ov * ov).sum()))


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
    rare relative to evaluations; O(E) rebuild is measured cheap)."""

    def __init__(self, pos, src_adj, grid, lam):
        self.pos = pos
        self.adj = src_adj
        self.grid = grid
        self.lam = lam
        self.pool_h, self.pool_v = _pool_arrays(grid)
        self.rebuild()

    def rebuild(self):
        self.xi = {v: int(round(float(p[0])))
                   for v, p in self.pos.items()}
        self.yi = {v: int(round(float(p[1])))
                   for v, p in self.pos.items()}
        self.contacts = _stair_contacts(self.pos, self.adj)
        self.arms = _arms(self.pos, self.contacts)
        self.Ch, self.Cv = _cover_arrays(self.arms, self.grid)
        self.e_stair = stair_energy(self.pos, self.adj,
                                    contacts=self.contacts)
        oh = np.maximum(self.Ch - self.pool_h[:, None], 0.0)
        ov = np.maximum(self.Cv - self.pool_v[:, None], 0.0)
        self.pen = float((oh * oh).sum() + (ov * ov).sum())
        self.E = self.e_stair + self.lam * self.pen
        # exclusion-extreme caches per hull (values incl. own coord)
        self.hx4 = {}
        self.vy4 = {}
        for v, (h_us, v_us) in self.contacts.items():
            self.hx4[v] = _ext4([self.xi[u] for u in h_us]
                                + [self.xi[v]])
            self.vy4[v] = _ext4([self.yi[u] for u in v_us]
                                + [self.yi[v]])

    def _pen_of(self, Ch, Cv):
        oh = np.maximum(Ch - self.pool_h[:, None], 0.0)
        ov = np.maximum(Cv - self.pool_v[:, None], 0.0)
        return float((oh * oh).sum() + (ov * ov).sum())

    # ---- the without-v world (shared by scan and audit) ----
    def without(self, v):
        """Remove v's influence: its arms, and each neighbour's hull
        shrunk to its exclusion extremes. Returns (Ch2, Cv2, e_wo,
        nb_wo) where nb_wo[u] = (side, row/col, without-v hull)."""
        Ch2 = self.Ch.copy()
        Cv2 = self.Cv.copy()
        row, ha, hb, col, va, vb = self.arms[v]
        Ch2[row, ha:hb + 1] -= 1.0
        Cv2[col, va:vb + 1] -= 1.0
        e_wo = self.e_stair - float((hb - ha) + (vb - va))
        nb_wo = {}
        for u in self.adj.get(v, []):
            if u not in self.pos or u == v:
                continue
            urow, uha, uhb, ucol, uva, uvb = self.arms[u]
            if v in set(self.contacts[u][0]):
                # v was in u's h-net: shrink u's h-arm
                na = int(_excl_lo(self.hx4[u], self.xi[v]))
                nb = int(_excl_hi(self.hx4[u], self.xi[v]))
                if (na, nb) != (uha, uhb):
                    Ch2[urow, uha:uhb + 1] -= 1.0
                    Ch2[urow, na:nb + 1] += 1.0
                    e_wo -= float((uhb - uha) - (nb - na))
                nb_wo[u] = (1, urow, na, nb)
            else:
                # v was in u's v-net: shrink u's v-arm
                na = int(_excl_lo(self.vy4[u], self.yi[v]))
                nb = int(_excl_hi(self.vy4[u], self.yi[v]))
                if (na, nb) != (uva, uvb):
                    Cv2[ucol, uva:uvb + 1] -= 1.0
                    Cv2[ucol, na:nb + 1] += 1.0
                    e_wo -= float((uvb - uva) - (nb - na))
                nb_wo[u] = (0, ucol, na, nb)
        return Ch2, Cv2, e_wo, nb_wo

    def exact_full(self, v, c, r, wo):
        """Exact E with v at (c, r), built from the without-v world.
        Handles the role assignment cleanly: for each neighbour u,
        v joins exactly one of u's nets by the stair rule at the NEW
        coordinates, extending u's without-v hull on that side."""
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
                _so, line, na, nb = nb_wo[u]
            else:
                # u's other-side hull is untouched by v's removal
                if ext_side == 1:
                    line = urow
                    na, nb = self.arms[u][1], self.arms[u][2]
                else:
                    line = ucol
                    na, nb = self.arms[u][4], self.arms[u][5]
            na2, nb2 = min(na, ext_val), max(nb, ext_val)
            if (na2, nb2) != (na, nb):
                if ext_side == 1:
                    Ch3[line, na:nb + 1] -= 1.0
                    Ch3[line, na2:nb2 + 1] += 1.0
                else:
                    Cv3[line, na:nb + 1] -= 1.0
                    Cv3[line, na2:nb2 + 1] += 1.0
                e += float((nb2 - na2) - (nb - na))
        ha, hb = min(h_vals), max(h_vals)
        va, vb = min(v_vals), max(v_vals)
        Ch3[r, ha:hb + 1] += 1.0
        Cv3[c, va:vb + 1] += 1.0
        e += float((hb - ha) + (vb - va))
        return e + self.lam * self._pen_of(Ch3, Cv3)


def _fast_seat_grid(live: _Live, v, wo):
    """Fast scan over all seats (H x W grid of totals; lower better).
    Prefix-array pricing; same-line collision corrections omitted (the
    exact audit absorbs them)."""
    grid = live.grid
    W, H = grid.W, grid.H
    lam = live.lam
    Ch2, Cv2, e_wo, nb_wo = wo
    nbrs = [u for u in live.adj.get(v, []) if u in live.pos and u != v]
    xv = live.xi
    yv = live.yi

    def _gain_prefix(C, pool):
        g = lam * ((np.maximum(C + 1.0 - pool[:, None], 0.0) ** 2)
                   - (np.maximum(C - pool[:, None], 0.0) ** 2))
        P = np.zeros((C.shape[0], C.shape[1] + 1))
        np.cumsum(g, axis=1, out=P[:, 1:])
        return P

    Ph = _gain_prefix(Ch2, live.pool_h)
    Pv = _gain_prefix(Cv2, live.pool_v)
    oh = np.maximum(Ch2 - live.pool_h[:, None], 0.0)
    ov = np.maximum(Cv2 - live.pool_v[:, None], 0.0)
    pen_wo = lam * float((oh * oh).sum() + (ov * ov).sum())

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
        row_total = (total[r]
                     + (hb - ha).astype(float)
                     + Ph[r, hb + 1] - Ph[r, ha])
        if v_us:
            rlo = min(yv[u] for u in v_us)
            rhi = max(yv[u] for u in v_us)
            va, vb = min(rlo, r), max(rhi, r)
        else:
            va, vb = r, r
        row_total = (row_total + float(vb - va)
                     + Pv[cc, vb + 1] - Pv[cc, va])
        for u in nbrs:
            ux, uy = xv[u], yv[u]
            if (r, v) < (uy, u):
                ext_side, ext_is_grid = 0, False   # u's v-arm to row r
            else:
                ext_side, ext_is_grid = 1, True    # u's h-arm to col c
            if u in nb_wo and nb_wo[u][0] == ext_side:
                _so, line, na, nb = nb_wo[u]
            else:
                if ext_side == 1:
                    line, na, nb = (live.arms[u][0], live.arms[u][1],
                                    live.arms[u][2])
                else:
                    line, na, nb = (live.arms[u][3], live.arms[u][4],
                                    live.arms[u][5])
            if ext_is_grid:
                na2 = np.minimum(na, cc)
                nb2 = np.maximum(nb, cc)
                d = ((nb2 - na2) - (nb - na)).astype(float)
                dpen = ((Ph[line, nb2 + 1] - Ph[line, na2])
                        - (Ph[line, nb + 1] - Ph[line, na]))
                row_total = row_total + d + dpen
            else:
                na2, nb2 = min(na, r), max(nb, r)
                d = float((nb2 - na2) - (nb - na))
                dpen = float((Pv[line, nb2 + 1] - Pv[line, na2])
                             - (Pv[line, nb + 1] - Pv[line, na]))
                row_total = row_total + d + dpen
        total[r] = row_total
    return total


def best_seat(v, pos, src_adj, grid, *, lam, e_cur, info, live=None):
    """Try every seat for ``v``; exact (array-patch) re-score of the
    top fast candidates; strict descent. Returns (new_pos, new_E) or
    None."""
    if live is None:
        live = _Live({u: p.copy() for u, p in pos.items()},
                     src_adj, grid, lam)
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


def best_translate(unit, pos, src_adj, grid, *, lam, e_cur, info,
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
                     src_adj, grid, lam)
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
        Ch_wo[row, ha:hb + 1] -= 1.0
        Cv_wo[col, va:vb + 1] -= 1.0
        old_span[w] = float((hb - ha) + (vb - va))
    xi, yi = live.xi, live.yi
    reshaped = sorted(B)
    rigid = [w for w in U if w not in B]

    def _delta(dr, dc):
        Ch2 = Ch_wo.copy()
        Cv2 = Cv_wo.copy()
        d_stair = 0.0
        for w in rigid:
            row, ha, hb, col, va, vb = arms[w]
            Ch2[row + dr, ha + dc:hb + dc + 1] += 1.0
            Cv2[col + dc, va + dr:vb + dr + 1] += 1.0
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
            Ch2[wy, ha:hb + 1] += 1.0
            Cv2[wx, va:vb + 1] += 1.0
            d_stair += float((hb - ha) + (vb - va)) - old_span[w]
        return (live.e_stair + d_stair
                + lam * live._pen_of(Ch2, Cv2))

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
        for s in adj.get(t, []):
            if s not in live.pos or s == t:
                continue
            if (newy[t], t) < (newy[s], s):
                xs.append(newx[s])
            else:
                ys.append(newy[s])
        return (min(xs), max(xs)), (min(ys), max(ys))

    def _third(t, m):
        """t's new hulls in O(1): t sees only ``m`` (one of u, w)
        change — remove m's old (side, value) entry via the ext4
        caches, add its new one."""
        row, ha, hb, col, va, vb = live.arms[t]
        old_h = (yi[t], t) < (yi[m], m)     # m was above t: h-side
        new_h = (yi[t], t) < (newy[m], m)
        if old_h:
            base_h = (int(_excl_lo(live.hx4[t], xi[m])),
                      int(_excl_hi(live.hx4[t], xi[m])))
            base_v = (va, vb)
        else:
            base_h = (ha, hb)
            base_v = (int(_excl_lo(live.vy4[t], yi[m])),
                      int(_excl_hi(live.vy4[t], yi[m])))
        if new_h:
            nh = (min(base_h[0], newx[m]), max(base_h[1], newx[m]))
            nv = base_v
        else:
            nh = base_h
            nv = (min(base_v[0], newy[m]), max(base_v[1], newy[m]))
        return nh, nv

    diffs = []      # (orient, line_old, iv_old, line_new, iv_new)
    d_stair = 0.0
    seen = set()
    for t in sorted({u, w} | set(Nu) | set(Nw)):
        if t in seen:
            continue
        seen.add(t)
        row, ha, hb, col, va, vb = live.arms[t]
        if t == u or t == w or t in common:
            (nha, nhb), (nva, nvb) = _hulls_scratch(t)
        elif t in set(Nu):
            (nha, nhb), (nva, nvb) = _third(t, u)
        else:
            (nha, nhb), (nva, nvb) = _third(t, w)
        nrow, ncol = newy[t], newx[t]
        if (nrow, nha, nhb) != (row, ha, hb):
            diffs.append((1, row, (ha, hb), nrow, (nha, nhb)))
        if (ncol, nva, nvb) != (col, va, vb):
            diffs.append((0, col, (va, vb), ncol, (nva, nvb)))
        d_stair += (float((nhb - nha) + (nvb - nva))
                    - float((hb - ha) + (vb - va)))
    if not diffs:
        return None
    Ch2 = live.Ch.copy()
    Cv2 = live.Cv.copy()
    for o, lo_line, (a0, b0), nl_line, (a1, b1) in diffs:
        A = Ch2 if o == 1 else Cv2
        A[lo_line, a0:b0 + 1] -= 1.0
        A[nl_line, a1:b1 + 1] += 1.0
    return (live.e_stair + d_stair
            + live.lam * live._pen_of(Ch2, Cv2))


def best_gather(unit, pos, src_adj, grid, *, lam, e_cur, info):
    """The native gather (s3.104): evict unit U from one axis's
    coordinate order and reinsert it CONTIGUOUSLY, handing the same
    value multiset back out by rank — displacement/room-making by
    construction, exactly as rank space provided it, with nothing
    inside the move but a list splice. Candidates: insert position in
    {nearest U's mean coordinate, bottom, top} x {U forward, U
    reversed} per axis; every candidate judged by the reference
    evaluator. Restrict the family, never the fidelity."""
    U = sorted(w for w in unit if w in pos)
    if len(U) < 2 or len(U) >= len(pos):
        return None
    Uset = set(U)
    best = None
    best_e = e_cur - 1e-9
    for axis in (1, 0):
        order = sorted(pos, key=lambda v: (float(pos[v][axis]), v))
        vals = sorted(float(pos[v][axis]) for v in order)
        rest = [v for v in order if v not in Uset]
        useq = [v for v in order if v in Uset]
        mean_c = sum(float(pos[v][axis]) for v in useq) / len(useq)
        mean_k = sum(1 for v in rest
                     if (float(pos[v][axis]), v)
                     < (mean_c, useq[0]))
        seen = set()
        for k in (mean_k, 0, len(rest)):
            for block in (useq, useq[::-1]):
                cand_order = rest[:k] + block + rest[k:]
                key = tuple(cand_order)
                if key in seen or cand_order == order:
                    continue
                seen.add(key)
                cand = {v: p.copy() for v, p in pos.items()}
                for r, v in enumerate(cand_order):
                    cand[v][axis] = float(vals[r])
                e2 = seat_energy(cand, src_adj, grid, lam=lam)
                if e2 < best_e:
                    best_e = e2
                    best = cand
    if best is not None:
        return best, best_e
    return None


def swap_sweep(pos, src_adj, grid, *, lam, e_cur, info, live,
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
                live = _Live(pos, src_adj, grid, lam)
                e_cur = live.E
                info["swap_accepts"] += 1
                improved = True
        if not improved:
            break
    return pos, e_cur, live


def seat_arrange(pos0: Dict[int, Point], src_adj: Dict[int, List[int]],
                 grid: TileGrid, units, *, lam: float = 1.0,
                 deadline: Optional[float] = None, pack_move=None):
    """Passes of (every variable via best_seat, id order; every unit
    via best_translate, coarsest first; then the PACK MOVE — the exact
    packer as one move among moves, its joint reseating re-scored on
    the seat objective and accepted only on strict descent, gap-free
    by construction), until an accept-free pass or the deadline.
    ``pack_move`` is a callable(pos) -> pos supplied by the driver."""
    import time as _time
    if not getattr(grid, "typed", False) or not line_pools(grid):
        return ({v: p.copy() for v, p in pos0.items()},
                {"seat_accepts": 0, "trans_accepts": 0, "passes": 0,
                 "accept_traj": [], "fast_miss": 0, "seat_E": None})
    pos = {v: np.asarray(p, dtype=float).copy() for v, p in pos0.items()}
    for v in pos:
        pos[v][0] = float(min(max(int(round(pos[v][0])), 0), grid.W - 1))
        pos[v][1] = float(min(max(int(round(pos[v][1])), 0), grid.H - 1))
    live = _Live(pos, src_adj, grid, lam)
    e_cur = live.E
    info = {"seat_accepts": 0, "trans_accepts": 0, "passes": 0,
            "accept_traj": [], "fast_miss": 0, "pack_accepts": 0,
            "swap_accepts": 0, "gather_accepts": 0}
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
            res = best_gather(cl, pos, src_adj, grid, lam=lam,
                              e_cur=e_cur, info=info)
            if res is not None:
                pos, e_cur = res
                live = _Live(pos, src_adj, grid, lam)
                info["gather_accepts"] += 1
                accepts += 1
        if pack_move is not None and (deadline is None
                                      or _time.perf_counter()
                                      < deadline):
            cand = pack_move({v: p.copy() for v, p in pos.items()})
            if cand is not None:
                for v in cand:
                    cand[v][0] = float(min(max(int(round(cand[v][0])),
                                               0), grid.W - 1))
                    cand[v][1] = float(min(max(int(round(cand[v][1])),
                                               0), grid.H - 1))
                e2 = seat_energy(cand, src_adj, grid, lam=lam)
                if e2 < e_cur - 1e-9:
                    pos, e_cur = cand, e2
                    live = _Live(pos, src_adj, grid, lam)
                    info["pack_accepts"] += 1
                    accepts += 1
        pre_swaps = info["swap_accepts"]
        if not coarse_phase:
            pos, e_cur, live = swap_sweep(
                pos, src_adj, grid, lam=lam, e_cur=e_cur, info=info,
                live=live, deadline=deadline, max_sweeps=1)
        accepts += info["swap_accepts"] - pre_swaps
        for v in (sorted(pos) if not coarse_phase else ()):
            if (deadline is not None
                    and _time.perf_counter() > deadline):
                break
            res = best_seat(v, pos, src_adj, grid, lam=lam,
                            e_cur=e_cur, info=info, live=live)
            if res is not None:
                pos, e_cur = res
                live = _Live(pos, src_adj, grid, lam)
                info["seat_accepts"] += 1
                accepts += 1
        for cl in unit_lists:
            if (deadline is not None
                    and _time.perf_counter() > deadline):
                break
            res = best_translate(cl, pos, src_adj, grid, lam=lam,
                                 e_cur=e_cur, info=info, live=live)
            if res is not None:
                pos, e_cur = res
                live = _Live(pos, src_adj, grid, lam)
                info["trans_accepts"] += 1
                accepts += 1
        # per-pass honesty cross-check: live books vs the reference
        e_ref = seat_energy(pos, src_adj, grid, lam=lam)
        if abs(e_ref - e_cur) > 1e-6:
            info["fast_miss"] += 1000   # loud drift marker
            e_cur = e_ref
            live = _Live(pos, src_adj, grid, lam)
        info["accept_traj"].append(accepts)
        if accepts == 0:
            if coarse_phase:
                coarse_phase = False   # release the fine moves
                continue
            break
    info["seat_E"] = round(e_cur, 1)
    return pos, info
