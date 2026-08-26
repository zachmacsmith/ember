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
    line_pools, pack_project)
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
    }
    if not getattr(grid, "typed", False) or not line_pools(grid):
        return _copy(pos0), info
    t0 = _time.perf_counter()

    def _expired() -> bool:
        return deadline is not None and _time.perf_counter() > deadline

    def _readout(p):
        info["readouts"] += 1
        return pack_project(p, src_adj, grid, kappa=kappa, floor=floor,
                            snap=snap, monotonize=False)

    pos, rinfo = _readout(pos0)
    e_cur = seat_energy(pos, src_adj, grid)
    contacts = _stair_contacts(pos, src_adj)
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
        e2 = seat_energy(cand2, src_adj, grid)
        if audit and not (e2 < e_cur - 1e-9):
            info["interleave_declines"] += 1
            return False
        pos, e_cur, rinfo = cand2, e2, rinfo2
        contacts = _stair_contacts(pos, src_adj)
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

    # proposals whose readout collapsed back to the proposing state
    # recur identically while that state stands (the (value, id)
    # re-sort makes them unrepresentable) — remember them so each
    # costs one readout ever, not one per pass
    seen_noop: set = set()

    while info["passes"] < _MAX_PASSES and not _expired():
        info["passes"] += 1
        changes = 0
        for scale in scales:
            for axis in (1, 0):
                for off in range(0, n, max(scale // 2, 1)):
                    if _expired():
                        break
                    order = sorted(pos, key=lambda v:
                                   (float(pos[v][axis]), v))
                    unit = order[off:off + scale]
                    if not unit or len(unit) >= n:
                        continue
                    vals = sorted(float(pos[v][axis]) for v in order)
                    other = {v: float(pos[v][1 - axis]) for v in pos}
                    new_order, _flip = align_reinsert(
                        order, set(unit), src_adj, vals, None,
                        axis=axis, other=other, contacts=contacts)
                    if new_order is None:
                        info["interleave_noops"] += 1
                        continue
                    key = (axis, tuple(order), tuple(new_order))
                    if key in seen_noop:
                        info["interleave_noops"] += 1
                        continue
                    cand = _copy(pos)
                    for r, v in enumerate(new_order):
                        cand[v][axis] = float(vals[r])
                    if _try_adopt(cand):
                        info["interleave_accepts"] += 1
                        changes += 1
                    elif not audit:
                        seen_noop.add(key)
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
        info["accept_traj"].append(changes)
        if changes == 0:
            break

    pen = int(best_e // _LEX_M)
    info["seat_E"] = best_e
    info["seat_pen"] = pen
    info["seat_stair"] = best_e - pen * _LEX_M
    info["readout_info"] = best_rinfo
    return best_pos, info
