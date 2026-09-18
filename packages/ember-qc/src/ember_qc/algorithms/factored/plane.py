"""Live reference moves with per-query fixed slots and immediate native decoding.

See docs/paper2/three-orders.md for the design contract and its exactness limits.
Capacity belongs to the total decoder; a proposal never invokes legalization.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import time
from typing import Optional

import numpy as np

from .native_model import (Book, Source, capacity_ok, complete_coordinates,
                           make_book, packing_problem)
from .order_dp import _check_inputs, check_cost_bounds, interleave
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



RELATIONS = ("source", "x", "y", "contact", "anchor", "whole")
SCHEDULER_VERSION = "live-reference-v1"


def nominate(orders, source, reference, relation, rng):
    """Read a fresh group from the current state; no membership survives a query."""
    if relation == 0:
        return source.indices[source.indptr[reference]:source.indptr[reference + 1]]
    if relation == 4:
        return np.asarray([reference], dtype=np.int64)
    order = orders[relation - 1]
    n = len(order)
    size = max(1, n // 2)
    position = int(np.flatnonzero(order == reference)[0])
    # Every admissible start is equally likely, including clipped end ranges.
    start = int(rng.integers(max(0, position - size + 1),
                             min(position, n - size) + 1))
    return order[start:start + size]


def arrange(source: Source, chip_m: int, tile: int, *, seed: int = 0,
            max_asks: Optional[int] = None, deadline: Optional[float] = None,
            sched_seed: Optional[int] = None, trace: bool = False,
            moves: bool = True, target_qubits: Optional[int] = None):
    """Reorganize one order, squish, and retain an independent usable bookmark.

    Reference rounds provide visit coverage, never a convergence certificate.
    An unlimited search therefore runs until its caller interrupts it.
    """
    started = time.perf_counter()
    n = len(source.labels)
    target_qubits = (4 * tile * chip_m * (2 * chip_m + 1)
                     if target_qubits is None else target_qubits)
    info = dict(asks=0, accepts=0, passes=0, completed_rounds=0,
                reference_visits=0, readouts=0, decode_calls=0,
                bookmark_asks=0, bookmark_wall=0.0, stopped_by=None,
                scheduler_version=SCHEDULER_VERSION, last_query=None,
                adopt_worse=0, infeasible=0, accept_traj=[],
                accepted_by_order=[0, 0, 0], interleave_wall=0.0,
                packing_wall=0.0, decode_wall=0.0, flow_nodes=0,
                flow_arcs=0, trace=[] if trace else None,
                strict_accepts=0, neutral_accepts=0, borrowed_accepts=0,
                whole_order_accepts=0, accepted_by_donor=[[0] * 3 for _ in range(3)],
                dp_solves=0, dp_cells=0, direct_scores=0, interrupted_asks=0,
                preparation_wall=0.0, transition_wall=0.0,
                dp_wall=0.0, direct_wall=0.0, traceback_wall=0.0, sweep_traj=[],
                repeated_sweep_states=0, unique_partitions=None,
                nomination_duplicates=None, nomination_wall=0.0,
                candidate_pairs=0, candidate_duplicates=0,
                accepted_by_side=[0, 0], event_states=0, event_updates=0,
                strand_preparations=0, traceback_checks=0, tracebacks=0,
                nomination_counts=dict.fromkeys(RELATIONS, 0),
                relation_work={})
    for name in RELATIONS:
        info["relation_work"][name] = dict(
            asks=0, accepts=0, strict_accepts=0, neutral_accepts=0,
            dp_solves=0, dp_cells=0, direct_scores=0, candidate_pairs=0,
            candidate_duplicates=0, event_states=0, event_updates=0,
            strand_preparations=0, traceback_checks=0, tracebacks=0,
            nomination_wall=0.0, interleave_wall=0.0, preparation_wall=0.0,
            transition_wall=0.0, dp_wall=0.0, direct_wall=0.0, traceback_wall=0.0,
            decode_calls=0, decode_wall=0.0, packing_wall=0.0,
            decoded_improvements=0, decoded_worse=0, bookmark_improvements=0)
    rng = np.random.default_rng(seed)
    orders = np.asarray([rng.permutation(n) for _ in range(3)], dtype=np.int64)
    effective_sched_seed = seed if sched_seed is None else sched_seed
    rng = np.random.default_rng(np.random.SeedSequence([effective_sched_seed, 1]))
    references = rng.permutation(n)
    relation_phase = int(rng.integers(5))
    destination_phase = int(rng.integers(3))
    current = decode(orders, source, chip_m, tile, seed=seed, deadline=deadline, info=info)
    best = None
    best_expanded = current.book.score
    seen_states = set()
    checked = False

    def usable(layout):
        return (layout.book.outside == 0 and
                layout.book.reserved + len(source.isolates) <= target_qubits)

    def bookmark(layout):
        nonlocal best, best_expanded
        best_expanded = min(best_expanded, layout.book.score)
        if usable(layout) and (best is None or layout.book.reserved < best.book.reserved):
            best = layout
            info["bookmark_asks"] = info["asks"]
            info["bookmark_wall"] = time.perf_counter() - started
            return True
        return False

    def record_round(changes=0, strict=0, complete=True):
        # Observation only: recurrence neither rejects a state nor stops search.
        digest = hashlib.blake2b(digest_size=16)
        digest.update(current.orders.tobytes())
        digest.update(current.coords.tobytes())
        state = digest.digest()
        repeated = state in seen_states
        seen_states.add(state)
        info["repeated_sweep_states"] += int(repeated)
        info["sweep_traj"].append(dict(
            scheduler_version=SCHEDULER_VERSION,
            pass_index=info["passes"], ask=info["asks"],
            wall=time.perf_counter() - started,
            current_score=current.book.score,
            bookmark_score=None if best is None else best.book.score,
            current_usable=usable(current), changed=changes, strict=strict,
            neutral=changes - strict, complete=complete,
            decode_complete=current.complete, repeated_state=repeated))

    def expired():
        if max_asks is not None and info["asks"] >= max_asks:
            return "asks"
        if deadline is not None and time.perf_counter() >= deadline:
            return "deadline"
        return None

    def query(axis, reference=None, relation=5):
        nonlocal current, checked
        name = RELATIONS[relation]
        work = info["relation_work"][name]
        nomination_start = time.perf_counter()
        unit = (np.arange(n, dtype=np.int64) if relation == 5 else
                nominate(current.orders, source, reference, relation, rng))
        nomination_wall = time.perf_counter() - nomination_start
        info["nomination_wall"] += nomination_wall
        work["nomination_wall"] += nomination_wall
        info["nomination_counts"][name] += 1
        proposal = current.orders.copy()
        coords = complete_coordinates(proposal, current.coords,
                                      current.book.active, 2 * tile)
        if not checked:
            _check_inputs(proposal, coords, source.indptr, source.indices, chip_m)
            checked = True
        else:
            check_cost_bounds(n, source.indices.size // 2, chip_m, int(coords.max()))
        info["last_query"] = dict(reference=reference, relation=RELATIONS[relation],
                                  axis=axis, size=len(unit))
        info["asks"] += 1
        work["asks"] += 1
        metrics = {}
        t0 = time.perf_counter()
        order, flipped = interleave(proposal, coords, source.indptr,
                                   source.indices, axis, unit, chip_m,
                                   deadline=deadline, info=metrics, checked=False)
        elapsed = time.perf_counter() - t0
        info["interleave_wall"] += elapsed
        work["interleave_wall"] += elapsed
        for name, query_name in (("dp_solves", "strand_solves"),
                                 ("dp_cells", "dp_cells"),
                                 ("candidate_pairs", "candidate_pairs"),
                                 ("candidate_duplicates", "candidate_duplicates"),
                                 ("direct_scores", "direct_scores"),
                                 ("preparation_wall", "preparation_wall"),
                                 ("transition_wall", "transition_wall"),
                                 ("dp_wall", "dp_wall"),
                                 ("direct_wall", "direct_wall"),
                                 ("traceback_wall", "traceback_wall"),
                                 ("event_states", "event_states"),
                                 ("event_updates", "event_updates"),
                                 ("strand_preparations", "strand_preparations"),
                                 ("traceback_checks", "traceback_checks"),
                                 ("tracebacks", "tracebacks")):
            value = metrics.get(query_name, 0)
            info[name] += value
            work[name] += value
        interrupted = not metrics.get("complete", True)
        info["interrupted_asks"] += int(interrupted)
        changed = order is not None
        strict = changed and bool(metrics.get("strict", False))
        before = current.book.score
        if changed:
            proposal[axis] = order
            info["accepts"] += 1
            work["accepts"] += 1
            info["accepted_by_order"][axis] += 1
            donor = int(metrics.get("donor", axis))
            info["accepted_by_donor"][axis][donor] += 1
            side = int(metrics.get("borrow_side", 0))
            info["accepted_by_side"][side] += 1
            for key, value in (("strict_accepts", int(strict)),
                               ("neutral_accepts", int(not strict))):
                info[key] += value
                work[key] += value
            info["borrowed_accepts"] += int(metrics.get("borrowed", False))
            info["whole_order_accepts"] += int(len(unit) == n)
            decode_before = {key: info[key] for key in
                             ("decode_calls", "decode_wall", "packing_wall")}
            # Even an interrupted query gets a total, capacity-valid decode.
            # There is no decoded-score veto and no later batched boundary.
            current = decode(proposal, source, chip_m, tile, seed=seed,
                             deadline=deadline, info=info)
            for key, old in decode_before.items():
                work[key] += info[key] - old
            worse = current.book.score > before
            info["adopt_worse"] += int(worse)
            work["decoded_worse"] += int(worse)
            work["decoded_improvements"] += int(current.book.score < before)
            work["bookmark_improvements"] += int(bookmark(current))
        if trace:
            info["trace"].append(dict(
                ask=info["asks"], reference=reference, relation=RELATIONS[relation],
                order=axis, size=len(unit), flipped=bool(flipped), changed=changed,
                donor=metrics.get("donor"), donor_mask=metrics.get("donor_mask"),
                borrow_side=metrics.get("borrow_side", -1),
                borrow_size=metrics.get("borrow_size", 0),
                borrowed=metrics.get("borrowed", False), strict=strict,
                complete=not interrupted, before=metrics.get("baseline_score"),
                after=metrics.get("score"), decoded_before=before,
                current_score=current.book.score,
                bookmark_score=None if best is None else best.book.score,
                decode_complete=current.complete))
        return int(changed), int(strict), interrupted

    bookmark(current)
    record_round(complete=current.complete)
    while n > 1 and moves and not expired():
        round_index = info["passes"]
        info["passes"] += 1
        changes = strict_changes = 0
        complete = True
        first_axis = (round_index + destination_phase) % 3
        for offset in range(3):
            if expired():
                complete = False
                break
            changed, strict, interrupted = query((first_axis + offset) % 3)
            changes += changed
            strict_changes += strict
            if interrupted:
                complete = False
                break
        if complete:
            for i, vertex in enumerate(references):
                if expired():
                    complete = False
                    break
                info["reference_visits"] += 1
                relation = (i + round_index + relation_phase) % 5
                first_axis = (i + round_index + destination_phase) % 3
                for offset in range(3):
                    if expired():
                        complete = False
                        break
                    changed, strict, interrupted = query(
                        (first_axis + offset) % 3, int(vertex), relation)
                    changes += changed
                    strict_changes += strict
                    if interrupted:
                        complete = False
                        break
                if not complete:
                    break
        info["accept_traj"].append(changes)
        info["completed_rounds"] += int(complete)
        record_round(changes, strict_changes, complete)
        if not complete:
            break
    info["stopped_by"] = expired() or ("moves-off" if not moves else
                                      "trivial" if n <= 1 else "interrupted")
    shown = best.book if best is not None else current.book
    info.update(outside_reserved_qubits=shown.outside,
                reserved_qubits=shown.reserved + len(source.isolates),
                active_horizontal=int(shown.active[1].sum()),
                active_vertical=int(shown.active[0].sum()),
                mixed_vertices=int(np.logical_and(*shown.active).sum()),
                pen=shown.outside, stair=shown.reserved,
                bars=int(shown.active.sum()), misses=0,
                best_expanded_score=best_expanded,
                final_current_score=current.book.score,
                final_current_usable=usable(current),
                final_bookmark_score=None if best is None else best.book.score,
                arrange_wall=time.perf_counter() - started)
    return best, info
