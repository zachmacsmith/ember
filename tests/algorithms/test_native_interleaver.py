"""Independent exhaustive oracles for native fixed-slot order moves."""

from itertools import combinations

import numpy as np
import pytest

from ember_qc.algorithms.factored.order_dp import interleave, score_layout


def csr(n, edges):
    neighbors = [[] for _ in range(n)]
    for u, v in edges:
        neighbors[u].append(v)
        neighbors[v].append(u)
    ptr = np.zeros(n + 1, dtype=np.int64)
    for v in range(n):
        ptr[v + 1] = ptr[v] + len(neighbors[v])
    return ptr, np.asarray([u for ns in neighbors for u in sorted(ns)], dtype=np.int64)


def oracle_score(orders, coords, edges, chip_m):
    """Build actual required contact sets, then enumerate reserved indices."""
    n = orders.shape[1]
    rank = [{int(v): i for i, v in enumerate(order)} for order in orders]
    vertical = [set() for _ in range(n)]
    horizontal = [set() for _ in range(n)]
    for u, v in edges:
        if rank[2][u] > rank[2][v]:
            u, v = v, u
        horizontal[u].add(int(coords[0, v]))
        vertical[v].add(int(coords[1, u]))
    outside, volume = 0, 0
    for v in range(n):
        if vertical[v] and horizontal[v]:
            vertical[v].add(int(coords[1, v]))
            horizontal[v].add(int(coords[0, v]))
        for orientation, contact in enumerate((vertical[v], horizontal[v])):
            if not contact:
                continue
            bricks = list(range((min(contact) - 1) // 2, max(contact) // 2 + 1))
            volume += len(bricks)
            outside += sum(
                int(coords[orientation, v]) > 2 * chip_m - 1 or z >= chip_m
                for z in bricks
            )
    span = sum(abs(r[u] - r[v]) for r in rank for u, v in edges)
    return outside, volume, span


def apply_order(orders, coords, axis, candidate):
    changed = orders.copy()
    placed = coords.copy()
    changed[axis] = candidate
    if axis < 2:
        placed[axis, candidate] = coords[axis, orders[axis]]
    return changed, placed


def merges(a, b):
    n = len(a) + len(b)
    for slots in combinations(range(n), len(a)):
        selected = set(slots)
        ai, bi = iter(a), iter(b)
        yield np.asarray([next(ai) if k in selected else next(bi) for k in range(n)],
                         dtype=np.int64)


def exhaustive(orders, coords, edges, axis, unit, chip_m):
    selected = set(unit)
    part = [v for v in orders[axis] if v in selected]
    rest = [v for v in orders[axis] if v not in selected]
    best = oracle_score(orders, coords, edges, chip_m)
    for side in (part, part[::-1]):
        for candidate in merges(side, rest):
            changed, placed = apply_order(orders, coords, axis, candidate)
            best = min(best, oracle_score(changed, placed, edges, chip_m))
    return best


def check_move(orders, coords, edges, axis, unit, chip_m):
    ptr, idx = csr(orders.shape[1], edges)
    old_orders, old_coords = orders.copy(), coords.copy()
    before = oracle_score(orders, coords, edges, chip_m)
    assert score_layout(orders, coords, ptr, idx, chip_m) == before
    expected = exhaustive(orders, coords, edges, axis, unit, chip_m)
    result, flipped = interleave(orders, coords, ptr, idx, axis, unit, chip_m)
    np.testing.assert_array_equal(orders, old_orders)
    np.testing.assert_array_equal(coords, old_coords)
    if expected == before:
        assert result is None
        assert not flipped
        return before
    assert result is not None
    changed, placed = apply_order(orders, coords, axis, result)
    actual = oracle_score(changed, placed, edges, chip_m)
    assert actual == expected
    assert score_layout(changed, placed, ptr, idx, chip_m) == actual
    selected = set(unit)
    part = [v for v in orders[axis] if v in selected]
    rest = [v for v in orders[axis] if v not in selected]
    assert [v for v in result if v not in selected] == rest
    assert [v for v in result if v in selected] == (part[::-1] if flipped else part)
    return actual


@pytest.mark.parametrize("axis", range(3))
def test_exhaustive_random_merges(axis):
    for seed in range(48):
        rng = np.random.default_rng(1000 * axis + seed)
        n = 2 + seed % 6
        edges = [(u, v) for u in range(n) for v in range(u + 1, n)
                 if rng.random() < (0.15 + 0.14 * (seed % 6))]
        orders = np.stack([rng.permutation(n) for _ in range(3)])
        coords = np.empty((2, n), dtype=np.int64)
        for physical in range(2):
            coords[physical, orders[physical]] = np.sort(rng.integers(1, 12, n))
        unit = rng.choice(n, size=seed % (n + 1), replace=False).tolist()
        check_move(orders, coords, edges, axis, unit, 2 + seed % 4)


@pytest.mark.parametrize("axis", range(3))
def test_every_four_vertex_graph(axis):
    pairs = list(combinations(range(4), 2))
    for mask in range(1 << len(pairs)):
        rng = np.random.default_rng(700 + mask)
        edges = [pair for i, pair in enumerate(pairs) if mask & (1 << i)]
        orders = np.stack([rng.permutation(4) for _ in range(3)])
        coords = np.empty((2, 4), dtype=np.int64)
        for physical in range(2):
            coords[physical, orders[physical]] = np.sort(rng.integers(1, 8, 4))
        check_move(orders, coords, edges, axis, [0, 2], 2)


@pytest.mark.parametrize("axis", range(3))
def test_equal_coordinates_still_optimize_rank_span(axis):
    orders = np.tile(np.arange(4, dtype=np.int64), (3, 1))
    coords = np.ones((2, 4), dtype=np.int64)
    before = oracle_score(orders, coords, [(0, 3)], 2)
    after = check_move(orders, coords, [(0, 3)], axis, [0], 2)
    assert after[:2] == before[:2]
    assert after[2] < before[2]


def test_pure_bars_do_not_include_dormant_anchors():
    orders = np.array([[1, 0], [0, 1], [0, 1]], dtype=np.int64)
    coords = np.array([[99, 1], [1, 99]], dtype=np.int64)
    ptr, idx = csr(2, [(0, 1)])
    assert score_layout(orders, coords, ptr, idx, 2) == (0, 2, 3)


def test_contact_order_can_remove_a_mixed_arm():
    orders = np.tile(np.arange(3, dtype=np.int64), (3, 1))
    coords = np.array([[1, 3, 5], [1, 9, 11]], dtype=np.int64)
    edges = [(0, 1), (1, 2)]
    before = oracle_score(orders, coords, edges, 8)
    after = check_move(orders, coords, edges, 2, [1], 8)
    assert before[1] == 9
    assert after[1] == 5


def test_reversed_unit_is_a_distinct_candidate_family():
    edges = [(0, 2), (0, 3), (0, 4)]
    orders = np.array([[3, 2, 0, 1, 4], [4, 2, 1, 3, 0], [4, 0, 3, 2, 1]],
                      dtype=np.int64)
    coords = np.array([[4, 5, 3, 1, 5], [4, 1, 1, 2, 1]], dtype=np.int64)
    ptr, idx = csr(5, edges)
    result, flipped = interleave(orders, coords, ptr, idx, 0, range(5), 3)
    assert flipped
    np.testing.assert_array_equal(result, orders[0, ::-1])
    check_move(orders, coords, edges, 0, range(5), 3)


@pytest.mark.parametrize("axis", range(3))
def test_integer_costs_preserve_unit_differences_above_float_precision(axis):
    base = 1 << 54
    orders = np.tile(np.arange(3, dtype=np.int64), (3, 1))
    coords = np.array([[base + 1, base + 3, base + 5], [1, 9, 11]], dtype=np.int64)
    check_move(orders, coords, [(0, 1), (1, 2)], axis, [1], base // 2 + 10)


def test_unsafe_integer_bounds_fail_before_compiled_cost_arithmetic():
    orders = np.tile(np.arange(3, dtype=np.int64), (3, 1))
    coords = np.full((2, 3), (1 << 62), dtype=np.int64)
    ptr, idx = csr(3, [(0, 1), (1, 2)])
    with pytest.raises(OverflowError, match="reserved-volume"):
        interleave(orders, coords, ptr, idx, 2, [1], 2)
    with pytest.raises(OverflowError, match="reserved-volume"):
        score_layout(orders, coords, ptr, idx, 2)
    coords[:] = 1
    with pytest.raises(OverflowError, match="chip extent"):
        interleave(orders, coords, ptr, idx, 0, [1], 1 << 62)


def test_malformed_slots_and_vertex_indices_are_rejected():
    orders = np.tile(np.arange(3, dtype=np.int64), (3, 1))
    coords = np.ones((2, 3), dtype=np.int64)
    ptr, idx = csr(3, [(0, 1), (1, 2)])
    bad_order = orders.copy()
    bad_order[0, 1] = 0
    with pytest.raises(ValueError, match="permutation"):
        interleave(bad_order, coords, ptr, idx, 0, [1], 2)
    bad_coords = coords.copy()
    bad_coords[0, 0] = 2
    with pytest.raises(ValueError, match="nondecreasing"):
        interleave(orders, bad_coords, ptr, idx, 0, [1], 2)
    bad_indices = idx.copy()
    bad_indices[-1] = 3
    with pytest.raises(ValueError, match="neighbor"):
        interleave(orders, coords, ptr, bad_indices, 2, [1], 2)
    bad_ptr = ptr.copy()
    bad_ptr[1] = len(idx) + 1
    with pytest.raises(ValueError, match="offsets"):
        interleave(orders, coords, bad_ptr, idx, 2, [1], 2)


@pytest.mark.parametrize("axis", range(3))
def test_axis_exchange_and_contact_reversal_symmetry(axis):
    for seed in range(12):
        rng = np.random.default_rng(4000 + seed)
        n = 6
        edges = [e for e in combinations(range(n), 2) if rng.random() < 0.5]
        orders = np.stack([rng.permutation(n) for _ in range(3)])
        coords = np.empty((2, n), dtype=np.int64)
        for physical in range(2):
            coords[physical, orders[physical]] = np.sort(rng.integers(1, 10, n))
        swapped_orders = orders[[1, 0, 2]].copy()
        swapped_orders[2] = orders[2, ::-1]
        swapped_coords = coords[::-1].copy()
        swapped_axis = 1 - axis if axis < 2 else 2
        assert oracle_score(orders, coords, edges, 3) == oracle_score(
            swapped_orders, swapped_coords, edges, 3,
        )
        best = check_move(orders, coords, edges, axis, [0, 2, 4], 3)
        symmetric_best = check_move(
            swapped_orders, swapped_coords, edges, swapped_axis, [0, 2, 4], 3,
        )
        assert best == symmetric_best


def test_empty_singleton_and_duplicate_units():
    orders = np.tile(np.arange(1, dtype=np.int64), (3, 1))
    coords = np.ones((2, 1), dtype=np.int64)
    ptr, idx = csr(1, [])
    assert interleave(orders, coords, ptr, idx, 0, [0], 2) == (None, False)
    assert interleave(orders, coords, ptr, idx, 2, [], 2) == (None, False)
    orders = np.tile(np.arange(4, dtype=np.int64), (3, 1))
    coords = np.ones((2, 4), dtype=np.int64)
    check_move(orders, coords, [(0, 3)], 0, [0, 0, 0], 2)


def test_book_compiler_agrees_on_mixed_and_outside_layouts():
    from ember_qc.algorithms.factored.native_model import make_book

    for seed in range(20):
        rng = np.random.default_rng(6000 + seed)
        n = 7
        edges = [e for e in combinations(range(n), 2) if rng.random() < 0.45]
        orders = np.stack([rng.permutation(n) for _ in range(3)])
        coords = np.empty((2, n), dtype=np.int64)
        for physical in range(2):
            coords[physical, orders[physical]] = np.sort(rng.integers(1, 13, n))
        ptr, idx = csr(n, edges)
        expected = oracle_score(orders, coords, edges, 3)
        assert tuple(make_book(orders, coords, ptr, idx, 3).score) == expected[:2]
