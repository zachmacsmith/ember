"""The orders-state arrange engine (round 1, 2026-08-26).

State is the two axis orders; positions are always DERIVED by the pack
readout — ``pack_project(monotonize=False)``, a pure orders->positions
projection (books -> forced y-pack -> forced x-pack -> bounded window
packs). Every state the engine occupies is therefore packer output by
construction, so no family normalizer runs before conversion.

One structural move: ``align_reinsert`` on contiguous intervals of the
current induced order, coarsest scale first, singletons included
(singles gather, wider intervals weave). The DP already gates on its
own view of the current order, so in the default mode every non-None
proposal is adopted and the readout projects it back onto the feasible
manifold — projected block-coordinate descent: the order is the graph's
variable, the positions are the fabric's. The lexicographic objective
survives in exactly one place, the best-state bookmark, which is what
the engine returns. ``audit=True`` is the acceptance-rule control arm:
adopt only on strict post-readout descent (monotone by construction).
"""
from __future__ import annotations

import time as _time
from typing import Dict, List, Optional, Tuple

import numpy as np

from ember_qc.algorithms.factored.field import (
    TileGrid, _stair_contacts, align_reinsert, edge_monotonize,
    line_pools, pack_project, stair_energy)
from ember_qc.algorithms.factored.seat import _LEX_M, seat_energy

# belt-and-braces pass cap: accept-all descends on the DP's view, not on
# E, so no internal energy signal is guaranteed to terminate it — the
# deadline is the real bound, this is the backstop for deadline=None
_MAX_PASSES = 64


def _copy(pos: Dict[int, np.ndarray]) -> Dict[int, np.ndarray]:
    return {v: p.copy() for v, p in pos.items()}


def _same(a: Dict[int, np.ndarray], b: Dict[int, np.ndarray]) -> bool:
    return all(np.array_equal(a[v], b[v]) for v in a)


def order_arrange(pos0: Dict[int, np.ndarray],
                  src_adj: Dict[int, List[int]],
                  grid: TileGrid,
                  *,
                  kappa: float,
                  floor: bool = True,
                  snap: bool = False,
                  audit: bool = False,
                  deadline: Optional[float] = None,
                  extra_units: Optional[List[List[List[int]]]] = None,
                  plane: bool = False,
                  ) -> Tuple[Dict[int, np.ndarray], dict]:
    info: dict = {
        "passes": 0, "accept_traj": [],
        "interleave_accepts": 0, "interleave_declines": 0,
        "interleave_noops": 0,
        "seat_accepts": 0, "trans_accepts": 0, "swap_accepts": 0,
        "fast_miss": 0,
        "seat_E": None, "seat_pen": None, "seat_stair": None,
        "readouts": 0, "mono_swaps": 0, "readout_info": {},
        "bookmark_wall": 0.0, "bookmark_readouts": 0,
        "hier_accepts": 0,
    }
    if not getattr(grid, "typed", False) or not line_pools(grid):
        return _copy(pos0), info
    t0 = _time.perf_counter()

    def _expired() -> bool:
        return deadline is not None and _time.perf_counter() > deadline

    def _readout(p):
        info["readouts"] += 1
        return pack_project(p, src_adj, grid, kappa=kappa, floor=floor,
                            snap=snap, monotonize=False,
                            project=not plane)

    def _judge(p, cts):
        # plane mode: states live on the ideal plane — pure stair (the
        # brick arrays would index out of bounds there, and capacity
        # is the unbounded pack's invariant, not a price). Windowed
        # mode: the full lexicographic evaluator.
        if plane:
            return stair_energy(p, src_adj, contacts=cts)
        return seat_energy(p, src_adj, grid)

    pos, rinfo = _readout(pos0)
    contacts = rinfo.get("_contacts") or _stair_contacts(pos, src_adj)
    e_cur = _judge(pos, contacts)
    best_e, best_pos, best_rinfo = e_cur, _copy(pos), rinfo
    n = len(pos)

    def _try_adopt(cand) -> bool:
        """Readout the materialized candidate; adopt per the acceptance
        rule; bookmark. Returns True iff the state changed."""
        nonlocal pos, e_cur, rinfo, contacts, best_e, best_pos, best_rinfo
        cand2, rinfo2 = _readout(cand)
        if _same(cand2, pos):
            # the DP's within-line order intent is unrepresentable in
            # positions ((value, id) re-sort) — a no-op, not an accept,
            # or accept-all livelocks on it forever
            info["interleave_noops"] += 1
            return False
        cts2 = (rinfo2.get("_contacts")
                or _stair_contacts(cand2, src_adj))
        e2 = _judge(cand2, cts2)
        if audit and not (e2 < e_cur - 1e-9):
            info["interleave_declines"] += 1
            return False
        pos, e_cur, rinfo = cand2, e2, rinfo2
        contacts = cts2
        if e2 < best_e:
            best_e, best_pos, best_rinfo = e2, _copy(pos), rinfo2
            # when the returned answer was actually found — the
            # work-to-answer metric; later churn is harvestable budget
            info["bookmark_wall"] = round(_time.perf_counter() - t0, 2)
            info["bookmark_readouts"] = info["readouts"]
        return True

    scales: List[int] = []
    s = n // 2
    while s >= 2:
        scales.append(s)
        s //= 2
    scales.append(1)

    # a unit re-probed on an UNCHANGED state repeats its outcome
    # exactly (the DP and the readout are deterministic functions of
    # the state), so stamp every state change and skip units whose
    # last fruitless probe saw the current stamp — late passes then
    # cost nothing on quiet regions, which is what lets the schedule
    # actually cycle (s3.114)
    state_ver = 0
    tried: dict = {}

    def _probe(unit, axis, key) -> int:
        """One DP proposal on ``unit`` (any variable set — an order
        interval or a graph-derived group), adopted per the acceptance
        rule. Returns 1 iff the state changed."""
        nonlocal state_ver
        if tried.get(key) == state_ver:
            info["interleave_noops"] += 1
            return 0
        if not (1 <= len(unit) < n):
            return 0
        order = sorted(pos, key=lambda v: (float(pos[v][axis]), v))
        vals = sorted(float(pos[v][axis]) for v in order)
        other = {v: float(pos[v][1 - axis]) for v in pos}
        new_order, _flip = align_reinsert(
            order, set(unit), src_adj, vals, None,
            axis=axis, other=other, contacts=contacts)
        if new_order is None:
            info["interleave_noops"] += 1
            tried[key] = state_ver
            return 0
        cand = _copy(pos)
        for r, v in enumerate(new_order):
            cand[v][axis] = float(vals[r])
        if _try_adopt(cand):
            info["interleave_accepts"] += 1
            state_ver += 1
            return 1
        tried[key] = state_ver
        return 0

    while info["passes"] < _MAX_PASSES and not _expired():
        info["passes"] += 1
        changes = 0
        if extra_units:
            # graph-derived groups (the affinity hierarchy) as EXTRA
            # units, coarsest level first: a scattered similar set is
            # gathered as ONE jointly-judged weave — the move interval
            # accretion cannot express (Max's ER variance hypothesis)
            for li, level in enumerate(reversed(extra_units)):
                for gi, grp in enumerate(level):
                    for axis in (1, 0):
                        if _expired():
                            break
                        unit = [v for v in grp if v in pos]
                        got = _probe(unit, axis, ("h", li, gi, axis))
                        if got:
                            info["hier_accepts"] += 1
                        changes += got
                    if _expired():
                        break
                if _expired():
                    break
        for scale in scales:
            for axis in (1, 0):
                for off in range(0, n, max(scale // 2, 1)):
                    if _expired():
                        break
                    order = sorted(pos, key=lambda v:
                                   (float(pos[v][axis]), v))
                    changes += _probe(order[off:off + scale], axis,
                                      (axis, scale, off))
                if _expired():
                    break
            if _expired():
                break
        if not _expired():
            mpos, mi = edge_monotonize(pos, src_adj, contacts=contacts)
            if mi["swaps"]:
                info["mono_swaps"] += mi["swaps"]
                if _try_adopt(mpos):
                    changes += 1
                    state_ver += 1
        info["accept_traj"].append(changes)
        if changes == 0:
            break

    info["seat_E"] = best_e
    if plane:
        # pure-stair judge: pen does not exist during plane search —
        # reporting 0 here would fake a feasibility certificate, so
        # the keys stay None (the projection's proj_pen is the real
        # capacity report)
        info["seat_stair"] = best_e
    else:
        pen = int(best_e // _LEX_M)
        info["seat_pen"] = pen
        info["seat_stair"] = best_e - pen * _LEX_M
    info["readout_info"] = best_rinfo
    return best_pos, info
