"""Three-order search with fixed-slot proposal sweeps and native decoding.

See docs/paper2/three-orders.md for the design contract and its exactness limits.
Capacity belongs to the total decoder; a proposal never invokes legalization.
"""
from __future__ import annotations

from dataclasses import dataclass
import time
from typing import Optional

import numpy as np

from .native_model import (Book, Source, capacity_ok, complete_coordinates,
                           make_book, packing_problem)
from .order_dp import interleave
from .packing import pack_axis


@dataclass
class Layout:
    orders: np.ndarray
    coords: np.ndarray
    book: Book
    extent_m: int
    complete: bool = True


def decode(orders, source, chip_m, tile, *, seed=0, deadline=None, info=None):
    """A total, deterministic decoder on an expanded intact ideal fabric.

    Every initial lane has at most C arms TOTAL. Thus every order triple has
    a valid starting layout, including triples changing both arm masks at once.
    Each subsequent exact conditional pack preserves both capacity directions.
    """
    t0 = time.perf_counter()
    if info is None:
        info = {}
    info["decode_calls"] = info.get("decode_calls", 0) + 1
    n = orders.shape[1]
    capacity = 2 * tile
    coords = np.ones((2, n), dtype=np.int64)
    book = make_book(orders, coords, source.indptr, source.indices, chip_m)
    max_groups = 1
    for axis in range(2):
        active = orders[axis][book.active[axis, orders[axis]]]
        coords[axis, active] = 1 + np.arange(len(active)) // capacity
        max_groups = max(max_groups, (len(active) + capacity - 1) // capacity)
    extent_m = max(chip_m, (max_groups + 2) // 2)
    book = make_book(orders, coords, source.indptr, source.indices, chip_m)
    finished = True
    while n:
        previous = coords.copy()
        for axis in (int(seed) & 1, 1 - (int(seed) & 1)):
            if deadline is not None and time.perf_counter() >= deadline:
                finished = False
                break
            problem = packing_problem(axis, orders, coords, book)
            if not len(problem[0]):
                continue
            pack_start = time.perf_counter()
            lines, metrics = pack_axis(*problem, capacity=capacity,
                                       chip_m=chip_m, extent_m=extent_m)
            info["packing_wall"] = info.get("packing_wall", 0.0) + time.perf_counter() - pack_start
            info["readouts"] = info.get("readouts", 0) + 1
            for key in ("flow_nodes", "flow_arcs"):
                info[key] = info.get(key, 0) + int(metrics.get(key, 0))
            if lines is None:
                raise AssertionError("conditional pack rejected its feasible input")
            old_score = book.score
            old_lines = coords[axis, problem[0]].copy()
            coords[axis, problem[0]] = lines
            book = make_book(orders, coords, source.indptr, source.indices, chip_m)
            if book.score > old_score:
                raise AssertionError("conditional pack increased the shared objective")
            if book.score == old_score and np.any(lines > old_lines):
                raise AssertionError("equal-cost pack is not componentwise minimal")
        info["decode_sweeps"] = info.get("decode_sweeps", 0) + 1
        if not finished or np.array_equal(previous, coords):
            break
    if not capacity_ok(book, coords, capacity, extent_m):
        raise AssertionError("decoded book violates the conservative capacity invariant")
    info["decode_wall"] = info.get("decode_wall", 0.0) + time.perf_counter() - t0
    return Layout(orders.copy(), coords, book, extent_m, finished)


def units(orders, source, rng):
    """One deduplicated seeded bag, using only general order/neighbor sets."""
    n = orders.shape[1]
    scales = []
    scale = n // 2
    while scale >= 2:
        scales.append(scale)
        scale //= 2
    scales.append(1)
    neighborhoods = []
    for v in range(n):
        neighbors = source.indices[source.indptr[v]:source.indptr[v + 1]]
        if 0 < len(neighbors) < n:
            neighborhoods.append(tuple(int(u) for u in neighbors))
    result = []
    for axis in range(3):
        seen = set()
        candidates = []
        for scale in scales:
            for start in range(0, n, max(1, scale // 2)):
                candidates.append(tuple(sorted(int(v) for v in orders[axis, start:start + scale])))
        candidates.extend(neighborhoods)
        for unit in candidates:
            if 0 < len(unit) < n and unit not in seen:
                seen.add(unit)
                result.append((axis, unit))
    return [result[int(i)] for i in rng.permutation(len(result))]


def arrange(source: Source, chip_m: int, tile: int, *, seed: int = 0,
            max_asks: Optional[int] = None, deadline: Optional[float] = None,
            sched_seed: Optional[int] = None, trace: bool = False,
            moves: bool = True, target_qubits: Optional[int] = None):
    """Explore complete sweeps, adopt them unconditionally, return a native bookmark."""
    started = time.perf_counter()
    n = len(source.labels)
    target_qubits = (4 * tile * chip_m * (2 * chip_m + 1)
                     if target_qubits is None else target_qubits)
    info = dict(asks=0, accepts=0, passes=0, readouts=0, decode_calls=0,
                bookmark_asks=0, bookmark_wall=0.0, stopped_by=None,
                adopt_worse=0, infeasible=0, accept_traj=[],
                accepted_by_order=[0, 0, 0], interleave_wall=0.0,
                packing_wall=0.0, decode_wall=0.0, flow_nodes=0,
                flow_arcs=0, trace=[] if trace else None)
    rng = np.random.default_rng(seed)
    orders = np.asarray([rng.permutation(n) for _ in range(3)], dtype=np.int64)
    rng = np.random.default_rng(seed if sched_seed is None else sched_seed)
    current = decode(orders, source, chip_m, tile, seed=seed, deadline=deadline, info=info)
    best = None
    best_expanded = current.book.score

    def bookmark(layout):
        nonlocal best, best_expanded
        best_expanded = min(best_expanded, layout.book.score)
        usable = (layout.book.outside == 0 and
                  layout.book.reserved + len(source.isolates) <= target_qubits)
        if usable and (best is None or layout.book.reserved < best.book.reserved):
            best = layout
            info["bookmark_asks"] = info["asks"]
            info["bookmark_wall"] = time.perf_counter() - started

    def expired():
        if max_asks is not None and info["asks"] >= max_asks:
            return "asks"
        if deadline is not None and time.perf_counter() >= deadline:
            return "deadline"
        return None

    bookmark(current)
    while n > 1 and moves and not expired():
        info["passes"] += 1
        changes = 0
        proposal = current.orders.copy()
        coords = complete_coordinates(proposal, current.coords,
                                      current.book.active, 2 * tile)
        slots = np.asarray([coords[axis, proposal[axis]].copy() for axis in range(2)])
        for axis, unit in units(proposal, source, rng):
            if expired():
                break
            info["asks"] += 1
            t0 = time.perf_counter()
            order, flipped = interleave(proposal, coords, source.indptr,
                                         source.indices, axis, unit, chip_m)
            info["interleave_wall"] += time.perf_counter() - t0
            if order is None:
                continue
            proposal[axis] = order
            if axis < 2:
                coords[axis, order] = slots[axis]
            info["accepts"] += 1
            info["accepted_by_order"][axis] += 1
            changes += 1
            if trace:
                info["trace"].append(dict(ask=info["asks"], order=axis,
                                           size=len(unit), flipped=bool(flipped)))
        info["accept_traj"].append(changes)
        if changes:
            # One compound proposal, one decoder boundary. There is no veto
            # based on its decoded score or its intermediate capacity.
            candidate = decode(proposal, source, chip_m, tile, seed=seed,
                               deadline=deadline, info=info)
            info["adopt_worse"] += int(candidate.book.score > current.book.score)
            current = candidate
            bookmark(current)
        elif not expired():
            info["stopped_by"] = "fixpoint"
            break
    if info["stopped_by"] is None:
        info["stopped_by"] = expired() or ("moves-off" if not moves else "trivial")
    shown = best.book if best is not None else current.book
    info.update(outside_reserved_qubits=shown.outside,
                reserved_qubits=shown.reserved + len(source.isolates),
                active_horizontal=int(shown.active[1].sum()),
                active_vertical=int(shown.active[0].sum()),
                mixed_vertices=int(np.logical_and(*shown.active).sum()),
                pen=shown.outside, stair=shown.reserved,
                bars=int(shown.active.sum()), misses=0,
                best_expanded_score=best_expanded,
                arrange_wall=time.perf_counter() - started)
    return best, info
