"""One geometric trajectory with contact-supported physical footprints.

The constant inactive_booking ablation adds virtual point claims to capacity
only. Physical tuples, support objective and conversion never emit those arms.
"""
from __future__ import annotations
from dataclasses import dataclass
import time as _time
from typing import Dict, List, Optional, Tuple
import numpy as np
from ember_qc.algorithms.factored.field import TileGrid, _stair_contacts, line_pools, pack_lines
from ember_qc.algorithms.factored.plane import (
    profiles, stride, ideal_pool, _cover_bricks, _line_profiles, units, rank_of)
from ember_qc.algorithms.factored.contact_footprint_kernels import align_reinsert

Pos = Dict[int, np.ndarray]

@dataclass(frozen=True)
class Books:
    contacts: dict
    supports: dict
    bars: dict
    tuples: dict
    capacity: dict
    inactive_booking: bool

class LayoutDeadline(RuntimeError):
    def __init__(self, info):
        super().__init__('geometry allocation ended before a complete usable layout')
        self.info = info

def supports(contacts):
    """Each pair is (horizontal, vertical) source-coordinate support."""
    out = {}
    for v, (h, w) in contacts.items():
        bend = bool(h) and bool(w)
        out[v] = (tuple(h) + ((v,) if bend else ()),
                  tuple(w) + ((v,) if bend else ()))
    return out

def books(pos, src_adj, grid, yrank, *, snap, contacts=None, inactive_booking=False):
    if type(inactive_booking) is not bool:
        raise TypeError('inactive_booking must be a constant boolean')
    if contacts is None:
        contacts = _stair_contacts(pos, src_adj, yrank=yrank)
    required = supports(contacts)
    bars, physical, capacity = {}, {1: [], 0: []}, {1: [], 0: []}
    for v in sorted(pos):
        intervals = []
        for side, orientation in ((0, 1), (1, 0)):
            members = required[v][side]
            line = int(round(float(pos[v][1-side])))
            if members:
                values = [float(pos[u][side]) for u in members]
                lo, hi = min(values), max(values)
                # Preserve the old intermediate bounds before snap widening:
                # horizontal hull clipped to W; vertical hull nonnegative.
                # Exact physical targets still use the un-clipped supports.
                if side == 0:
                    lo, hi = float(np.clip(lo,0.,grid.W-1.)), float(np.clip(hi,0.,grid.W-1.))
                else:
                    lo, hi = max(0.,lo), max(0.,hi)
                intervals.append((lo, hi))
                a, b = lo, hi
                if snap:
                    crossings = [int(round(x)) for x in values]
                    a = min(a, float(min(crossings)-1))
                    b = max(b, float(max(crossings)))
                b = max(b, a+1.)  # a point arm still occupies capacity
                item = (line, a, b, v)
                physical[orientation].append(item)
                capacity[orientation].append(item)
            else:
                intervals.append(None)
                if inactive_booking:
                    # Old inactive footprint, virtual only. No target/support
                    # is added; a sole active arm still excludes this corner.
                    x = float(pos[v][side])
                    a = b = (float(np.clip(x,0.,grid.W-1.)) if side == 0 else max(0.,x))
                    if snap:
                        a = min(a, float(round(x)-1))
                        b = max(b, float(round(x)))
                    capacity[orientation].append((line, a, max(b,a+1.), v))
        bars[v] = tuple(intervals)
    return Books(contacts, required, bars, physical, capacity, inactive_booking)

def support_energy(pos, bk, *, bar):
    total = 0.
    for pair in bk.supports.values():
        for axis, members in enumerate(pair):
            if members:
                values = [float(pos[u][axis]) for u in members]
                total += max(values)-min(values)+bar
    return total

def _axis_coeffs(bk, pos, axis, *, ranks):
    coeffs = {v: 0 for v in pos}
    for pair in bk.supports.values():
        members = pair[axis]
        if len(members) > 1:
            lo = min(members, key=ranks.__getitem__)
            hi = max(members, key=ranks.__getitem__)
            coeffs[lo] -= 1
            coeffs[hi] += 1
    return coeffs

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
        for (line, a, b, _v) in bk.capacity[o]:
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
    stair = support_energy(pos, bk, bar=bar)
    return int(round(pen)), float(stair)


def pack_axis(axis: int, order: List[int], pos: Pos, bk: Books,
              grid: TileGrid, ranks: Dict[int, Dict[int, int]], *,
              bounded: bool = False) -> Tuple[Dict[int, int], int]:
    """One forced pack of ``axis``: each line takes a contiguous run of
    the carried order, feasible iff the run's claim intervals fit the
    line's per-brick pools; cost = the true stair objective linearized
    by ``_axis_coeffs`` (exact for any assignment monotone in the
    carried order). A variable the DP cannot seat is placed on its
    order-predecessor's line — monotone by construction, no re-sort,
    and COUNTED (its overload is the judge's to see). Returns
    ``({v: line}, misses)``."""
    s = stride(grid)
    ivs_by_v = {v: (a, b) for (_line, a, b, v) in bk.capacity[axis]}
    carried = list(order)
    order = [v for v in order if v in ivs_by_v]
    if not order:
        return {v: 0 for v in carried}, 0
    items = [(ivs_by_v[v][0], ivs_by_v[v][1], v) for v in order]
    prof = _line_profiles(axis, grid, items, s, bounded=bounded)
    L = len(prof)
    cmap = _axis_coeffs(bk, pos, axis, ranks=ranks[axis])
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
    # Unbooked axis coordinates are absent from every active support. Fill
    # them monotonically so slot gaps in the inherited interleaver stay
    # nonnegative; carried ranks, contact assignment and physical claims stay
    # unchanged. The virtual-booking ablation has no unbooked coordinates.
    prev = lines[order[0]]
    for v in carried:
        if v in lines:
            prev = lines[v]
        else:
            lines[v] = prev
    return lines, misses


def readout(axis: int, orders: Dict[int, List[int]], pos: Pos, src_adj,
            grid: TileGrid, *, snap: bool, bounded: bool = False,
            bk: Optional[Books] = None, inactive_booking: bool = False) -> Tuple[Pos, Books, int]:
    """Orders -> positions on ``axis``, the other axis held exactly as
    it is. Books on the current positions (``bk`` if the caller already
    holds them for exactly these positions and this y-order), one pack,
    positions rewritten as integer-valued floats, books again on the
    result (the y-order is untouched by a pack, so contacts are the
    same)."""
    ranks = {ax: rank_of(orders[ax]) for ax in (0, 1)}
    if bk is None:
        bk = books(pos, src_adj, grid, ranks[1], snap=snap, inactive_booking=inactive_booking)
    lines, misses = pack_axis(axis, orders[axis], pos, bk, grid, ranks,
                              bounded=bounded)
    new = {v: p.copy() for v, p in pos.items()}
    for v, ln in lines.items():
        new[v][axis] = float(ln)
    bk2 = books(new, src_adj, grid, ranks[1], snap=snap, contacts=bk.contacts,
                inactive_booking=inactive_booking)
    return new, bk2, misses


def arrange(src_adj: Dict[int, List[int]], grid: TileGrid, *,
            seed: int = 0, max_asks: Optional[int] = None,
            deadline: Optional[float] = None, snap: bool = False,
            moves: bool = True, trace: bool = False,
            sched_seed: Optional[int] = None,
            initial_orders: Optional[Tuple[List[int], List[int]]] = None,
            inactive_booking: bool = False
            ) -> Tuple[Pos, Books, dict]:
    """Search a geometric placement from one fixed initialization.

    By default use two seeded rank permutations. Explicit ``initial_orders``
    are vertex orders, converted to ranks; the search scheduler has its own
    seeded generator in either case. Proposals optimize a frozen geometric
    surrogate and are then repacked. Retain the best ``(pen, stair)`` state;
    this score is not the final physical chain objective. Stop on a pass with
    no accepted proposal, the evaluation allowance, or the common deadline.
    """
    t0 = _time.perf_counter()
    ids = sorted(src_adj)
    n = len(ids)
    info: dict = {"asks": 0, "accepts": 0, "passes": 0, "readouts": 0,
                  "bookmark_asks": 0, "bookmark_wall": 0.0,
                  "stopped_by": None, "pen": None, "stair": None,
                  "bars": None, "misses": None, "accept_traj": [],
                  "adopt_worse": 0, "infeasible": 0,
                  "trace": [] if trace else None}
    if initial_orders is None:
        rng = np.random.default_rng(seed)
        px = rng.permutation(n)
        py = rng.permutation(n)
    else:
        if (len(initial_orders) != 2 or any(
                len(order) != n or set(order) != set(ids)
                for order in initial_orders)):
            raise ValueError('initial_orders must contain two permutations of source vertices')
        ranks = [rank_of(order) for order in initial_orders]
        px = [ranks[0][v] for v in ids]
        py = [ranks[1][v] for v in ids]
    # the bag's own seed (the order-invariance instrument varies it
    # independently of the init); defaults to the init's
    rng = np.random.default_rng(seed if sched_seed is None else sched_seed)
    pos: Pos = {v: np.array([float(px[i]), float(py[i])])
                for i, v in enumerate(ids)}
    typed = bool(getattr(grid, "typed", False)) and bool(line_pools(grid))
    if n == 0 or not typed:
        yr = rank_of(sorted(ids, key=lambda v: (pos[v][1], v)))
        bk = books(pos, src_adj, grid, yr, snap=snap,
                   inactive_booking=inactive_booking)
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

    info.update(inactive_booking=inactive_booking, max_asks=max_asks,
                exposure='controlled_1000_asks_not_saturation_or_default',
                geometry_deadline=deadline, projection_aborted=False)

    def geometry_expired():
        return deadline is not None and _time.perf_counter() >= deadline

    def initial_guard():
        if geometry_expired():
            info.update(stopped_by='deadline_before_initial_readout_complete',
                        wall=_time.perf_counter()-t0)
            raise LayoutDeadline(info)

    # the first picture: rows, columns, rows against the packed columns
    bk = None
    for ax in (1, 0, 1):
        initial_guard()
        pos, bk, miss = readout(ax, orders, pos, src_adj, grid, snap=snap,
                                bk=bk, inactive_booking=inactive_booking)
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
                other=other, contacts=bk.contacts, bar=bar)
            if geometry_expired():
                break
            if new_order is None:
                tried[key] = state_ver
                continue
            cand = {v: p.copy() for v, p in pos.items()}
            for r, v in enumerate(new_order):
                cand[v][ax] = float(vals[r])
            new_orders = {a: (new_order if a == ax else orders[a])
                          for a in (0, 1)}
            # Rebuild contact supports and pack the moved axis, then rebuild
            # and pack the other axis against those new hulls. A changed y
            # order can activate or remove an arm on either axis.
            cand, bk2, miss = readout(ax, new_orders, cand, src_adj, grid,
                                      snap=snap, inactive_booking=inactive_booking)
            info["readouts"] += 1
            if geometry_expired():
                break
            if miss == 0:
                cand, bk2, miss = readout(1 - ax, new_orders, cand, src_adj,
                                          grid, snap=snap, bk=bk2,
                                          inactive_booking=inactive_booking)
                info["readouts"] += 1
            if geometry_expired():
                break
            if miss > 0:
                # A missed placement is a rejected private proposal.
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
    info["projected"] = False
    info["proj_misses"] = 0
    if pen > 0:
        # Project an off-chip bookmark using bounded capacity tables.
        # All three readouts must finish before publishing the projection.
        ppos = {v: p.copy() for v, p in bpos.items()}
        pm = 0
        # Columns, rows, columns: bound horizontal extent before packing
        # rows, then repack columns against the resulting vertical hulls.
        pbk = None
        for ax in (0, 1, 0):
            if geometry_expired():
                info.update(stopped_by='deadline_before_projection_complete',
                            projection_aborted=True, pen=int(pen), stair=float(stair),
                            wall=_time.perf_counter()-t0)
                raise LayoutDeadline(info)
            ppos, pbk, m = readout(ax, bords, ppos, src_adj, grid,
                                   snap=snap, bounded=True, bk=pbk,
                                   inactive_booking=inactive_booking)
            pm = m
        bbk = pbk
        bpos = ppos
        info["projected"] = True
        info["proj_misses"] = int(pm)
    info["pen"] = int(pen)
    info["stair"] = float(stair)
    info["bars"] = int(sum((1 if h else 0) + (1 if v else 0)
                           for h, v in bbk.contacts.values()))
    info["misses"] = int(bmiss)
    info["orders"] = (list(bords[0]), list(bords[1]))
    info["yrank"] = rank_of(bords[1])
    info['physical_arms'] = sum(map(len, bbk.tuples.values()))
    info['capacity_arms'] = sum(map(len, bbk.capacity.values()))
    info['stopping_conditions'] = (["asks"] if max_asks is not None and info['asks'] >= max_asks else [])
    if geometry_expired():
        info['stopping_conditions'].append('geometry_deadline')
    if fix:
        info['stopping_conditions'].append('fixpoint')
    info['geometry_remaining'] = None if deadline is None else deadline-_time.perf_counter()
    info["wall"] = _time.perf_counter() - t0
    return bpos, bbk, info

