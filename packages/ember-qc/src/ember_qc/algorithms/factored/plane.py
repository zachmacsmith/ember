"""
The plane engine (s3.127 — the rewrite).

State: two orders, one per axis. From the orders alone the packer
derives a position (a line index) per variable under hard capacity,
and from the positions and the y-order the stair rule derives every
chain: a horizontal run and a vertical run per variable, each the hull
of the contacts it must reach. The objective is the derived chain
length on a plane that is strictly weaker than the hardware — capacity
first, then spans plus one bar per active arm. One move: remove a set
of variables from one order and re-insert it at its exact optimum over
all weaves (forward or reversed). Every proposal is adopted; the
proposer prices the frozen picture, the readout re-packs only the axis
that moved, and the judge scores what the readout produced.

Everything fabric-specific is a fact of the ``TileGrid``: line pools,
the brick period, the two boundary lines that carry one course parity.
Everything else is arithmetic on the two orders.
"""
from __future__ import annotations

import time as _time
from typing import Dict, List, Optional, Tuple

import numpy as np

from ember_qc.algorithms.factored.field import (
    TileGrid, _axis_coeffs, _brick_pool_arrays, _stair_contacts,
    align_reinsert, arm_books, line_pools, pack_lines, stair_energy)

Pos = Dict[int, np.ndarray]
Books = tuple  # (contacts, bars, tuples) — arm_books' triple


# ----------------------------------------------------------------------
# the fabric's capacity book


def profiles(grid: TileGrid) -> Tuple[np.ndarray, np.ndarray]:
    """THE capacity book: per-(line, brick) pools, ``(ph, pv)`` indexed
    ``[h-line (row), brick along x]`` and ``[v-line (column), brick
    along y]``. On a course-resolved fabric (stride > 1) the two
    boundary lines of each orientation carry one course parity only
    and are parity-starved at claim time, so their pools are zero. The
    packer packs against this table (extended past the chip with the
    ideal pool, so that a state always exists) and the judge prices
    against it (nothing past the chip, so that overflow is visible)."""
    s = stride(grid)
    cache = getattr(grid, "_plane_profiles", None)
    if cache is not None and cache[0] == s:
        return cache[1]
    ph, pv = _brick_pool_arrays(grid, s)
    ph = np.array(ph, dtype=float, copy=True)
    pv = np.array(pv, dtype=float, copy=True)
    if s > 1:
        for arr in (ph, pv):
            if arr.shape[0] >= 2:
                arr[0, :] = 0.0
                arr[-1, :] = 0.0
    grid._plane_profiles = (s, (ph, pv))
    return ph, pv


def stride(grid) -> int:
    return max(int(getattr(grid, "stride", 1) or 1), 1)


def ideal_pool(grid) -> float:
    lp = line_pools(grid)
    return float(max(lp.values())) if lp else 0.0


# ----------------------------------------------------------------------
# the books and the judge


def rank_of(order: List[int]) -> Dict[int, int]:
    return {v: r for r, v in enumerate(order)}


def books(pos: Pos, src_adj, grid: TileGrid, yrank: Dict[int, int],
          *, snap: bool) -> Books:
    """One accounting. Contacts by the y-order's RANK (the stair rule:
    the lower endpoint reaches sideways, the higher reaches down), bars
    = the hulls of the contacts plus the variable's own seat, tuples =
    the claim intervals the packer packs and the converter seats. No
    capacity floor invented from a degree heuristic (capacity is the
    derived reach, enforced by the packer); every arm is at least one
    tile (``min_span=0`` — the one-tile footprint, so a point arm still
    occupies its tile); y is not clipped to the chip (rows beyond it are
    the judge's business)."""
    contacts = _stair_contacts(pos, src_adj, yrank=yrank)
    return arm_books(pos, src_adj, grid, kappa=1.0, floor=False,
                     snap=snap, min_span=0.0, contacts=contacts,
                     yrank=yrank, ybound=False)


def _cover_bricks(a: float, b: float, s: int, nb_eff: int
                  ) -> Tuple[int, int]:
    """The pack's own brick rule for an inclusive hull [a, b]: bricks
    floor(a/s) .. floor(b/s), as the half-open [lo, hi), hi clamped to
    the last capacity-bearing brick of the line (off-chip extent past
    it is booked on the last real brick — projection and judge agree)."""
    lo = max(0, int(np.floor(a / s)))
    hi = int(np.floor(b / s)) + 1
    return lo, min(hi, nb_eff)


def judge(bk: Books, pos: Pos, src_adj, grid: TileGrid, *, bar: float
          ) -> Tuple[int, float]:
    """The objective, lexicographic: ``(pen, stair)``.

    ``pen`` = sum over every (orientation, line, brick) of the squared
    overload of the books' claim intervals against ``profiles(grid)``;
    lines and bricks the chip does not have are pool 0, so a state that
    hangs off the chip is priced, never clamped. ``stair`` = the total
    derived chain length: every active arm's hull span plus one bar
    (``bar`` junctions) for the qubit the arm needs even when its hull
    is a single junction. Integers throughout, so a tuple comparison is
    the exact lexicographic order — no weight, no lambda."""
    s = stride(grid)
    ph, pv = profiles(grid)
    pen = 0.0
    for o, table in ((1, ph), (0, pv)):
        nlines, nb = table.shape
        nb_eff_real = int(np.max(np.nonzero(table.max(axis=0) > 0)[0])) + 1 \
            if np.any(table > 0) else 0
        cover: Dict[int, np.ndarray] = {}
        for (line, a, b, _v) in bk[2][o]:
            ln = int(line)
            if ln < 0:
                continue
            on_chip = ln < nlines
            # off-chip lines have no last real brick: every brick counts
            lo, hi = _cover_bricks(float(a), float(b), s,
                                   nb_eff_real if on_chip else 10 ** 9)
            if hi <= lo:
                continue
            arr = cover.get(ln)
            if arr is None or arr.size < hi + 1:
                new = np.zeros(max(hi + 1, nb + 1, 1))
                if arr is not None:
                    new[:arr.size] = arr
                cover[ln] = arr = new
            arr[lo] += 1.0
            arr[hi] -= 1.0
        for ln, diff in cover.items():
            c = np.cumsum(diff)[:-1]
            pool = np.zeros_like(c)
            if ln < nlines:
                k = min(nb, c.size)
                pool[:k] = table[ln, :k]
            over = np.maximum(c - pool, 0.0)
            pen += float((over * over).sum())
    stair = stair_energy(pos, src_adj, contacts=bk[0], bar=bar)
    return int(round(pen)), float(stair)


# ----------------------------------------------------------------------
# the packer: one axis, against the other axis held fixed


def _line_profiles(axis: int, grid: TileGrid, items, s: int
                   ) -> List[np.ndarray]:
    """The packer's capacity table for ``axis``: the chip's real lines
    (boundary lines zero), extended with the ideal pool so that every
    order has a packing — columns (axis 0) are extended along their
    bricks past the chip up to the tallest v-hull; rows (axis 1) gain
    enough uniform rows to seat everyone at full pool (the L_max
    lemma). The extension is the strip: real in x, ideal above."""
    ph, pv = profiles(grid)
    pool_u = ideal_pool(grid)
    if axis == 0:
        ymax = max((float(b) for (_a, b, _v) in items), default=0.0)
        need_b = int(ymax // s) + 2
        out = []
        for pr in pv:
            nz = np.flatnonzero(pr > 0)
            if not nz.size:
                out.append(np.zeros(max(need_b, pr.size)))
                continue
            ne = int(nz.max()) + 1
            out.append(np.concatenate(
                [pr[:ne], np.full(max(need_b - ne, 0), pool_u)]))
        return out
    n = len(items)
    extra = int((n + max(int(pool_u), 1) - 1) // max(int(pool_u), 1)) + 1
    shape = np.where(ph.max(axis=0) > 0, pool_u, 0.0)  # an interior row
    return [row for row in ph] + [shape.copy() for _ in range(extra)]


def pack_axis(axis: int, order: List[int], pos: Pos, bk: Books,
              grid: TileGrid, ranks: Dict[int, Dict[int, int]]
              ) -> Tuple[Dict[int, int], int]:
    """One forced pack of ``axis``: each line takes a contiguous run of
    the carried order, feasible iff the run's claim intervals fit the
    line's per-brick pools; cost = the true stair objective linearized
    by ``_axis_coeffs`` (exact for any assignment monotone in the
    carried order). A variable the DP cannot seat is placed on its
    order-predecessor's line — monotone by construction, no re-sort,
    and COUNTED (its overload is the judge's to see). Returns
    ``({v: line}, misses)``."""
    s = stride(grid)
    ivs_by_v = {v: (a, b) for (_line, a, b, v) in bk[2][axis]}
    order = [v for v in order if v in ivs_by_v]
    if not order:
        return {}, 0
    items = [(ivs_by_v[v][0], ivs_by_v[v][1], v) for v in order]
    prof = _line_profiles(axis, grid, items, s)
    L = len(prof)
    cmap = _axis_coeffs(bk[0], pos, axis, ranks=ranks[axis])
    cs = [float(cmap.get(v, 0)) for v in order]
    vals = [float(pos[v][axis]) for v in order]
    assign, _cost = pack_lines([ivs_by_v[v] for v in order], vals,
                               [0.0] * L, coeffs=cs, brick=(s, prof))
    lines: Dict[int, int] = {}
    misses = 0
    first = next((ln for ln in assign if ln is not None), 0)
    prev = int(first)
    for v, ln in zip(order, assign):
        if ln is None:
            misses += 1
            ln = prev
        lines[v] = int(ln)
        prev = int(ln)
    return lines, misses


def readout(axis: int, orders: Dict[int, List[int]], pos: Pos, src_adj,
            grid: TileGrid, *, snap: bool) -> Tuple[Pos, Books, int]:
    """Orders -> positions on ``axis``, the other axis held exactly as
    it is. Books on the current positions, one pack, positions
    rewritten as integer-valued floats, books again on the result (the
    y-order is untouched by a pack, so contacts are the same)."""
    ranks = {ax: rank_of(orders[ax]) for ax in (0, 1)}
    bk = books(pos, src_adj, grid, ranks[1], snap=snap)
    lines, misses = pack_axis(axis, orders[axis], pos, bk, grid, ranks)
    new = {v: p.copy() for v, p in pos.items()}
    for v, ln in lines.items():
        new[v][axis] = float(ln)
    bk2 = books(new, src_adj, grid, ranks[1], snap=snap)
    return new, bk2, misses


# ----------------------------------------------------------------------
# the search


def units(orders: Dict[int, List[int]], src_adj,
          rng: np.random.Generator) -> List[Tuple[int, tuple]]:
    """One pass's questions, shuffled: on each axis, every contiguous
    run of the current order at scales n/2, n/4, ..., 2, 1
    (half-overlapping), and every variable's neighbourhood N(v) as one
    block (the order-independent gather: for a complete bipartite graph
    N(v) is the other block, so the bipartition is one move; for a
    sparse graph it is "bring my neighbours to me"). Returned as
    ``(axis, unit)`` with ``unit`` a tuple of variables."""
    n = len(orders[0])
    scales: List[int] = []
    s = n // 2
    while s >= 2:
        scales.append(s)
        s //= 2
    scales.append(1)
    out: List[Tuple[int, tuple]] = []
    for ax in (0, 1):
        order = orders[ax]
        for sc in scales:
            step = max(sc // 2, 1)
            for off in range(0, n, step):
                blk = tuple(order[off:off + sc])
                if blk:
                    out.append((ax, blk))
        for v in sorted(src_adj):
            nb = tuple(sorted(u for u in src_adj[v] if u != v))
            if 1 <= len(nb) < n:
                out.append((ax, nb))
    perm = rng.permutation(len(out))
    return [out[i] for i in perm]


def arrange(src_adj: Dict[int, List[int]], grid: TileGrid, *,
            seed: int = 0, max_asks: Optional[int] = None,
            deadline: Optional[float] = None, snap: bool = False,
            moves: bool = True, trace: bool = False
            ) -> Tuple[Pos, Books, dict]:
    """The engine. Init = two seeded permutations. Loop: for each unit
    in the pass's bag, ask the interleaver (strict improvement in the
    true objective on the frozen picture), re-pack the moved axis,
    judge, adopt (every proposal is adopted), bookmark the best
    ``(pen, stair)``. Stop = a pass with zero accepts (the fixpoint
    certificate), or ``max_asks`` DP evaluations (the work budget), or
    the deadline (a safety net, reported). Returns the bookmark's
    positions and books and the diagnostics."""
    t0 = _time.perf_counter()
    ids = sorted(src_adj)
    n = len(ids)
    info: dict = {"asks": 0, "accepts": 0, "passes": 0, "readouts": 0,
                  "bookmark_asks": 0, "bookmark_wall": 0.0,
                  "stopped_by": None, "pen": None, "stair": None,
                  "bars": None, "misses": None, "accept_traj": [],
                  "adopt_worse": 0, "infeasible": 0,
                  "trace": [] if trace else None}
    rng = np.random.default_rng(seed)
    px = rng.permutation(n)
    py = rng.permutation(n)
    pos: Pos = {v: np.array([float(px[i]), float(py[i])])
                for i, v in enumerate(ids)}
    typed = bool(getattr(grid, "typed", False)) and bool(line_pools(grid))
    if n < 3 or not typed:
        yr = rank_of(sorted(ids, key=lambda v: (pos[v][1], v)))
        bk = arm_books(pos, src_adj, grid, kappa=1.0, floor=False,
                       snap=snap, min_span=0.0,
                       contacts=_stair_contacts(pos, src_adj, yrank=yr),
                       yrank=yr, ybound=True) if n else ((), {}, {1: [], 0: []})
        info["stopped_by"] = "trivial"
        return pos, bk, info
    orders = {ax: sorted(ids, key=lambda v: (float(pos[v][ax]), v))
              for ax in (0, 1)}
    bar = float(stride(grid))
    nbr_units = {tuple(sorted(u for u in src_adj[v] if u != v))
                 for v in ids}

    def _expired() -> bool:
        if max_asks is not None and info["asks"] >= max_asks:
            return True
        return deadline is not None and _time.perf_counter() > deadline

    # the first picture: rows, columns, rows against the packed columns
    for ax in (1, 0, 1):
        pos, bk, miss = readout(ax, orders, pos, src_adj, grid, snap=snap)
        info["readouts"] += 1
    e_cur = judge(bk, pos, src_adj, grid, bar=bar)
    best = (e_cur, {v: p.copy() for v, p in pos.items()}, bk, miss,
            {ax: list(orders[ax]) for ax in (0, 1)})
    fix = False
    tried: Dict[Tuple[int, tuple], int] = {}
    state_ver = 0
    while moves and not _expired():
        info["passes"] += 1
        changes = 0
        for ax, unit in units(orders, src_adj, rng):
            if _expired():
                break
            key = (ax, unit)
            if tried.get(key) == state_ver:
                continue
            info["asks"] += 1
            order = orders[ax]
            vals = [float(pos[v][ax]) for v in order]
            other = {v: float(pos[v][1 - ax]) for v in ids}
            new_order, _flip = align_reinsert(
                order, set(unit), src_adj, vals, None, axis=ax,
                other=other, contacts=bk[0], bar=bar)
            if new_order is None:
                tried[key] = state_ver
                continue
            cand = {v: p.copy() for v, p in pos.items()}
            for r, v in enumerate(new_order):
                cand[v][ax] = float(vals[r])
            new_orders = {a: (new_order if a == ax else orders[a])
                          for a in (0, 1)}
            # the packer's guarantee is capacity on BOTH axes: re-pack
            # the moved axis (its contacts changed), then the other (its
            # hulls changed). Re-packing only the moved axis left the
            # other axis overloaded until its next accepted move — the
            # search then wandered in overloaded states (turán: bookmark
            # frozen at the init for 15,000 asks).
            cand, bk2, miss = readout(ax, new_orders, cand, src_adj, grid,
                                      snap=snap)
            info["readouts"] += 1
            if miss == 0:
                cand, bk2, miss = readout(1 - ax, new_orders, cand, src_adj,
                                          grid, snap=snap)
                info["readouts"] += 1
            if miss > 0:
                # the packer could not seat everyone: the proposal is
                # outside the valid set and is declined — feasibility by
                # construction, never a priced or adopted overload
                # (measured: adopting one such state on turán left the
                # bookmark at the init for 15,000 asks)
                info["infeasible"] += 1
                tried[key] = state_ver
                continue
            e2 = judge(bk2, cand, src_adj, grid, bar=bar)
            if e2 > e_cur:
                info["adopt_worse"] += 1
            if trace:
                info["trace"].append((info["asks"], ax, len(unit),
                                      unit in nbr_units, e_cur, e2))
            pos, bk, orders, e_cur = cand, bk2, new_orders, e2
            state_ver += 1
            changes += 1
            info["accepts"] += 1
            if e2 < best[0]:
                best = (e2, {v: p.copy() for v, p in pos.items()}, bk,
                        miss, {a: list(orders[a]) for a in (0, 1)})
                info["bookmark_asks"] = info["asks"]
                info["bookmark_wall"] = round(_time.perf_counter() - t0, 2)
        info["accept_traj"].append(changes)
        if changes == 0:
            fix = not _expired()
            break
    if fix:
        info["stopped_by"] = "fixpoint"
    elif max_asks is not None and info["asks"] >= max_asks:
        info["stopped_by"] = "asks"
    elif deadline is not None and _time.perf_counter() > deadline:
        info["stopped_by"] = "deadline"
    else:
        info["stopped_by"] = "moves-off" if not moves else "passes"
    (pen, stair), bpos, bbk, bmiss, bords = best
    info["pen"] = int(pen)
    info["stair"] = float(stair)
    info["bars"] = int(sum((1 if h else 0) + (1 if v else 0)
                           for h, v in bbk[0].values()))
    info["misses"] = int(bmiss)
    info["orders"] = (list(bords[0]), list(bords[1]))
    info["yrank"] = rank_of(bords[1])
    info["wall"] = round(_time.perf_counter() - t0, 2)
    return bpos, bbk, info
