"""Independent capacity, lexicographic optimum, and int64-flow oracles."""
import itertools
from collections import defaultdict

import numpy as np
import pytest

from ember_qc.algorithms.factored.packing import (
    _add_arc,
    _predecessors,
    _push_relabel,
    pack_axis,
)


def direct(lines, own_lo, own_hi, opposite_lines, first, last, capacity, chip_m):
    """Count occupied reservation cells directly, without predecessor formulas."""
    own = defaultdict(int)
    opposite = defaultdict(int)
    total = outside = 0
    for line, a, b in zip(lines, own_lo, own_hi):
        for brick in range(int(a), int(b) + 1):
            own[int(line), brick] += 1
            total += 1
            outside += int(line > 2 * chip_m - 1 or brick >= chip_m)
    for line, i, j in zip(opposite_lines, first, last):
        for brick in range((lines[i] - 1) // 2, lines[j] // 2 + 1):
            opposite[int(line), brick] += 1
            total += 1
            outside += int(line > 2 * chip_m - 1 or brick >= chip_m)
    feasible = max(own.values(), default=0) <= capacity
    feasible &= max(opposite.values(), default=0) <= capacity
    return feasible, (outside, total)


def brute(own_lo, own_hi, opposite_lines, first, last, capacity, chip_m, extent_m):
    best = None
    minima = []
    for lines in itertools.combinations_with_replacement(
            range(1, 2 * extent_m), len(own_lo)):
        feasible, objective = direct(lines, own_lo, own_hi, opposite_lines,
                                     first, last, capacity, chip_m)
        if not feasible:
            continue
        if best is None or objective < best:
            best, minima = objective, [lines]
        elif objective == best:
            minima.append(lines)
    if best is None:
        return None, None
    smallest = tuple(np.min(np.asarray(minima), axis=0))
    assert smallest in minima
    return smallest, best


def test_exhaustive_conditional_optima_and_smallest_ties():
    rng = np.random.default_rng(914027)
    for trial in range(100):
        n = int(rng.integers(1, 7))
        extent = int(rng.integers(1, 5))
        chip = int(rng.integers(1, extent + 1))
        capacity = int(rng.integers(1, 4))
        own_lo = rng.integers(0, extent + 1, n)
        own_hi = own_lo + rng.integers(0, 3, n)
        m = int(rng.integers(0, n + 5))
        opposite_lines = rng.integers(1, 2 * extent + 3, m)
        first = rng.integers(0, n, m)
        last = np.array([rng.integers(i, n) for i in first], dtype=np.int64)
        expected, score = brute(own_lo, own_hi, opposite_lines, first, last,
                                capacity, chip, extent)
        actual, info = pack_axis(list(range(n)), own_lo, own_hi, opposite_lines,
                                 first, last, capacity=capacity,
                                 chip_m=chip, extent_m=extent)
        assert info["objective"] == score, trial
        assert info["infeasible"] == (expected is None), trial
        assert (None if actual is None else tuple(actual)) == expected, trial


def test_three_junction_guard_rejects_two_row_approximation():
    # Point contacts at rows 2 and 4 both reserve brick 1. Treating a brick
    # as only two junction rows would miss this conflict.
    lo = np.array([0, 1])
    hi = lo.copy()
    opposite = np.array([1, 1])
    first = np.array([0, 1])
    last = first.copy()
    same, cross = _predecessors(lo, hi, opposite, first, last, 1)
    assert tuple(same) == (-1, -1)
    assert tuple(cross) == (-1, 0)
    assert not direct((2, 4), lo, hi, opposite, first, last, 1, 3)[0]
    assert direct((2, 5), lo, hi, opposite, first, last, 1, 3)[0]


def test_intrinsic_opposite_overlap_is_infeasible_even_with_more_rows():
    lines, info = pack_axis([0, 1], [0, 1], [0, 1], [1, 1], [0, 0], [1, 1],
                            capacity=1, chip_m=2, extent_m=100)
    assert lines is None and info["infeasible"]
    assert info["flow_nodes"] == 0


def test_outside_volume_precedes_total_and_counts_both_causes():
    own_lo, own_hi = [0, 1, 0], [2, 2, 1]
    opposite, first, last = [1, 4, 2], [0, 0, 1], [2, 1, 2]
    expected, score = brute(own_lo, own_hi, opposite, first, last, 2, 1, 4)
    actual, info = pack_axis([7, 100, 33], own_lo, own_hi, opposite, first, last,
                             capacity=2, chip_m=1, extent_m=4)
    assert tuple(actual) == expected
    assert info["objective"] == score
    assert score[0] > 0


def _flow_graph(n, arcs):
    head = np.full(n, -1, dtype=np.int64)
    target = np.empty(2 * len(arcs), dtype=np.int64)
    link = np.empty_like(target)
    residual = np.empty_like(target)
    used = 0
    for u, v, cap in arcs:
        used = _add_arc(head, target, link, residual, used, u, v, cap)
    return head, target, link, residual


def _brute_cut(n, arcs):
    best = None
    best_sets = []
    for bits in itertools.product((False, True), repeat=n - 2):
        chosen = {0} | {i + 1 for i, value in enumerate(bits) if value}
        value = sum(cap for u, v, cap in arcs if u in chosen and v not in chosen)
        if best is None or value < best:
            best, best_sets = value, [chosen]
        elif value == best:
            best_sets.append(chosen)
    return best, set.intersection(*best_sets)


def test_int64_flow_and_minimum_source_cut_against_exhaustive_oracle():
    rng = np.random.default_rng(993)
    for trial in range(100):
        n = int(rng.integers(2, 8))
        scale = 2 ** 40 if trial % 4 == 0 else 1
        arcs = [(u, v, int(rng.integers(1, 9)) * scale)
                for u in range(n) for v in range(n)
                if u != v and rng.random() < 0.27]
        expected, selected = _brute_cut(n, arcs)
        head, target, link, residual = _flow_graph(n, arcs)
        value, reached = _push_relabel(head, target, link, residual, 0, n - 1)
        assert int(value) == expected, trial
        assert set(np.flatnonzero(reached)) == selected, trial
    graph = _flow_graph(2, [(0, 1, 2 ** 40 + 7)])
    value, reached = _push_relabel(*graph, 0, 1)
    assert int(value) == 2 ** 40 + 7
    assert tuple(reached) == (True, False)


def test_large_exact_packing_encoding_and_overflow_guard():
    # Wide fixed reservations produce capacities above int32 while the exact
    # objective remains in int64. No iteration over their coordinate span.
    lo, hi = [0, 0, 0], [10 ** 8] * 3
    first, last, opposite = [0, 0, 1], [1, 2, 2], [1, 2, 3]
    actual, info = pack_axis([0, 1, 2], lo, hi, opposite, first, last,
                             capacity=3, chip_m=1, extent_m=4)
    assert tuple(actual) == (1, 1, 1)
    assert info["objective"] == (300000002, 300000006)
    with pytest.raises(OverflowError, match="int64"):
        pack_axis([0], [0], [10 ** 12], [], [], [],
                  capacity=1, chip_m=1, extent_m=2)


def test_empty_and_input_validation():
    actual, info = pack_axis([], [], [], [], [], [], capacity=8, chip_m=3, extent_m=3)
    assert actual.size == 0 and info["objective"] == (0, 0)
    with pytest.raises(ValueError, match="duplicate"):
        pack_axis([0, 0], [0, 0], [0, 0], [], [], [], capacity=8, chip_m=3, extent_m=3)
    with pytest.raises(ValueError, match="integer"):
        pack_axis([0], [0.5], [1], [], [], [], capacity=8, chip_m=3, extent_m=3)
    with pytest.raises(ValueError, match="endpoint"):
        pack_axis([0], [0], [0], [1], [0], [1], capacity=8, chip_m=3, extent_m=3)


def test_generated_sources_decode_with_shared_book_and_both_capacities():
    """Exercise larger flow graphs through real contact activation and recourse.

    The exhaustive tests above prove the small optimization cases. This checks
    the separate integration risk: actual changing H/V books, variable track
    counts, and repeated conditional cuts must reach a common feasible state.
    """
    import networkx as nx
    from ember_qc.algorithms.factored.native_model import Source, capacity_ok, make_book
    from ember_qc.algorithms.factored.plane import decode

    rng = np.random.default_rng(303)
    for n, tile in ((31, 1), (57, 2), (96, 4), (121, 1)):
        graph = nx.gnp_random_graph(n, 4.0 / (n - 1), seed=n)
        source = Source.from_graph(graph)
        orders = np.asarray([rng.permutation(len(source.labels)) for _ in range(3)])
        layout = decode(orders, source, chip_m=3, tile=tile, seed=n)
        fresh = make_book(orders, layout.coords, source.indptr, source.indices, 3)
        assert layout.complete
        assert fresh.score == layout.book.score
        assert capacity_ok(fresh, layout.coords, 2 * tile, layout.extent_m)
        for axis in (0, 1):
            active_order = orders[axis][fresh.active[axis, orders[axis]]]
            assert np.all(np.diff(layout.coords[axis, active_order]) >= 0)
    again = decode(orders, source, chip_m=3, tile=tile, seed=n)
    assert np.array_equal(again.coords, layout.coords)
