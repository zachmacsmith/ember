"""Independent exhaustive oracles for native fixed-slot order moves."""

from itertools import combinations

import numpy as np
import pytest

from ember_qc.algorithms.factored.order_dp import check_cost_bounds, interleave, score_layout


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


def canonical_sides(n, unit):
    selected = set(unit)
    complement = set(range(n)) - selected
    if len(selected) > len(complement) or (
        len(selected) == len(complement) and sorted(selected) > sorted(complement)
    ):
        selected, complement = complement, selected
    return complement, selected


def exhaustive(orders, coords, edges, axis, unit, chip_m, donors=None,
               both_sides=True):
    selected = set(unit)
    best = oracle_score(orders, coords, edges, chip_m)
    n = orders.shape[1]
    if not selected or n <= 1:
        return best
    sides = [selected]
    if both_sides and len(selected) < n:
        sides.append(set(range(n)) - selected)
    for selected in sides:
        rest = [v for v in orders[axis] if v not in selected]
        for donor in ({0, 1, 2} if donors is None else set(donors) | {axis}):
            part = [v for v in orders[donor] if v in selected]
            for strand in (part, part[::-1]):
                for candidate in merges(strand, rest):
                    changed, placed = apply_order(orders, coords, axis, candidate)
                    best = min(best, oracle_score(changed, placed, edges, chip_m))
    return best


def check_move(orders, coords, edges, axis, unit, chip_m):
    ptr, idx = csr(orders.shape[1], edges)
    old_orders, old_coords = orders.copy(), coords.copy()
    before = oracle_score(orders, coords, edges, chip_m)
    assert score_layout(orders, coords, ptr, idx, chip_m) == before
    expected = exhaustive(orders, coords, edges, axis, unit, chip_m)
    info = {}
    result, flipped = interleave(orders, coords, ptr, idx, axis, unit, chip_m, info=info)
    np.testing.assert_array_equal(orders, old_orders)
    np.testing.assert_array_equal(coords, old_coords)
    if result is None:
        assert expected == before
        assert not flipped
        return before
    assert result is not None
    changed, placed = apply_order(orders, coords, axis, result)
    actual = oracle_score(changed, placed, edges, chip_m)
    assert actual == expected
    assert score_layout(changed, placed, ptr, idx, chip_m) == actual
    selected = (set(unit) if len(set(unit)) == orders.shape[1] else
                canonical_sides(orders.shape[1], unit)[info["borrow_side"]])
    assert info["borrow_size"] == len(selected)
    part = [v for v in orders[info["donor"]] if v in selected]
    rest = [v for v in orders[axis] if v not in selected]
    assert [v for v in result if v not in selected] == rest
    assert [v for v in result if v in selected] == (part[::-1] if flipped else part)
    assert info["strict"] == (actual < before)
    assert info["complete"]
    assert info["score"] <= info["baseline_score"]
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
    result, flipped = interleave(orders, coords, ptr, idx, 0, range(5), 3,
                                 donors=(0,), accept_equal=False)
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


def test_neutral_borrowed_winner_and_oriented_deduplication():
    # Both foreign donors name the same two oriented strands. They differ
    # from both incumbent strands. Reversing the other side adds a fifth family.
    orders = np.array([[0, 1, 2, 3, 4], [1, 0, 2, 3, 4], [2, 0, 1, 3, 4]])
    coords = np.ones((2, 5), dtype=np.int64)
    ptr, idx = csr(5, [])
    info = {}
    result, flipped = interleave(orders, coords, ptr, idx, 0, [0, 1, 2], 3, info=info)
    np.testing.assert_array_equal(result, [3, 4, 1, 0, 2])
    assert not flipped
    assert info["donor"] == 1 and info["donor_mask"] == 0b110
    assert info["borrowed"] and not info["strict"] and info["complete"]
    assert info["score"] == info["baseline_score"] == (0, 0, 0)
    assert info["strand_solves"] == info["candidate_pairs"] == 5
    assert info["candidate_duplicates"] == 12 - 5
    assert info["dp_cells"] == 5 * (4 * 3 - 1)
    assert info["direct_scores"] == 0
    assert info["preparation_wall"] >= info["transition_wall"] >= 0
    assert info["dp_wall"] >= 0
    assert interleave(orders, coords, ptr, idx, 0, [0, 1, 2], 3,
                      accept_equal=False) == (None, False)


def test_foreign_alias_of_incumbent_does_not_hide_real_borrowing():
    orders = np.array([[0, 1, 2, 3], [0, 1, 2, 3], [1, 0, 2, 3]])
    coords = np.ones((2, 4), dtype=np.int64)
    ptr, idx = csr(4, [])
    info = {}
    result, _ = interleave(orders, coords, ptr, idx, 0, [0, 1, 2], 2, info=info)
    assert info["donor"] == 2 and info["borrowed"]
    np.testing.assert_array_equal(result, [3, 1, 0, 2])


@pytest.mark.parametrize("axis", range(3))
def test_donor_restriction_retains_incumbent_and_full_union_is_no_worse(axis):
    for seed in range(12):
        rng = np.random.default_rng(8100 + 20 * axis + seed)
        n = 6
        edges = [edge for edge in combinations(range(n), 2) if rng.random() < 0.5]
        orders = np.stack([rng.permutation(n) for _ in range(3)])
        coords = np.empty((2, n), dtype=np.int64)
        for physical in (0, 1):
            coords[physical, orders[physical]] = np.sort(rng.integers(1, 9, n))
        ptr, idx = csr(n, edges)
        scores = []
        for donors in ((), ((axis + 1) % 3,), None):
            info = {}
            result, _ = interleave(orders, coords, ptr, idx, axis, [0, 2, 4], 3,
                                    donors=donors, info=info)
            changed, placed = ((orders, coords) if result is None else
                               apply_order(orders, coords, axis, result))
            actual = oracle_score(changed, placed, edges, 3)
            assert actual == exhaustive(orders, coords, edges, axis, [0, 2, 4], 3, donors)
            assert info["score"] <= info["baseline_score"]
            scores.append(actual)
        assert scores[2] <= scores[1] <= scores[0]


def test_whole_set_uses_direct_scores_and_changed_tie_beats_incumbent():
    orders = np.array([[0, 1, 2, 3], [1, 0, 2, 3], [2, 0, 3, 1]])
    coords = np.ones((2, 4), dtype=np.int64)
    ptr, idx = csr(4, [])
    info = {}
    result, flipped = interleave(orders, coords, ptr, idx, 0, range(4), 3, info=info)
    np.testing.assert_array_equal(result, orders[1])
    assert not flipped and info["borrowed"]
    assert info["strand_solves"] == info["dp_cells"] == 0
    assert info["direct_scores"] == 5  # six unique strands; incumbent is known
    info = {}
    result, flipped = interleave(orders, coords, ptr, idx, 0, range(4), 3,
                                 donors=(), info=info)
    np.testing.assert_array_equal(result, orders[0, ::-1])
    assert flipped and not info["borrowed"]
    assert info["direct_scores"] == 1


def test_singleton_aliases_collapse_but_complement_can_reverse():
    orders = np.array([[0, 1, 2], [1, 2, 0], [2, 0, 1]])
    coords = np.ones((2, 3), dtype=np.int64)
    ptr, idx = csr(3, [])
    info = {}
    result, _ = interleave(orders, coords, ptr, idx, 0, [0], 2, info=info)
    np.testing.assert_array_equal(result, [0, 2, 1])
    assert info["strand_solves"] == 2 and info["donor_mask"] == 0b111
    assert info["borrow_side"] == 0 and info["borrow_size"] == 2
    assert info["candidate_duplicates"] == 10
    assert not info["borrowed"]


def test_expired_query_returns_incumbent_without_candidate_work(monkeypatch):
    import ember_qc.algorithms.factored.order_dp as module

    orders = np.tile(np.arange(4), (3, 1))
    coords = np.ones((2, 4), dtype=np.int64)
    ptr, idx = csr(4, [(0, 3)])
    monkeypatch.setattr(module.time, "perf_counter", lambda: 1.0)
    info = {}
    assert interleave(orders, coords, ptr, idx, 0, [0, 1], 3,
                      deadline=0.0, info=info) == (None, False)
    assert not info["complete"]
    assert info["strand_solves"] == info["direct_scores"] == 0
    assert info["score"] == info["baseline_score"]


def test_deadline_keeps_completed_neutral_winner(monkeypatch):
    import ember_qc.algorithms.factored.order_dp as module

    orders = np.array([[0, 1, 2, 3], [1, 0, 2, 3], [2, 0, 1, 3]])
    coords = np.ones((2, 4), dtype=np.int64)
    ptr, idx = csr(4, [])
    clock = [0.0]
    original_fill = module._fill

    def finish_then_expire(*args):
        result = original_fill(*args)
        clock[0] = 2.0
        return result

    monkeypatch.setattr(module.time, "perf_counter", lambda: clock[0])
    monkeypatch.setattr(module, "_fill", finish_then_expire)
    info = {}
    result, _ = interleave(orders, coords, ptr, idx, 0, [0, 1, 2], 3,
                           deadline=1.0, info=info)
    np.testing.assert_array_equal(result, [3, 1, 0, 2])
    assert info["strand_solves"] == 1 and not info["complete"]
    assert info["borrowed"] and not info["strict"]


def test_trusted_queries_share_bounds_and_preserve_checked_result(monkeypatch):
    import ember_qc.algorithms.factored.order_dp as module

    orders = np.array([[0, 1, 2, 3], [1, 0, 2, 3], [2, 0, 3, 1]])
    coords = np.array([[1, 2, 3, 4], [2, 1, 3, 4]], dtype=np.int64)
    ptr, idx = csr(4, [(0, 2), (1, 2), (2, 3)])
    check_cost_bounds(4, len(idx) // 2, 3, int(coords.max()))
    expected, expected_flip = interleave(orders, coords, ptr, idx, 0, [0, 1, 2], 3)
    original_bounds = module._bounds
    calls = []

    def counted_bounds(*args):
        calls.append(1)
        return original_bounds(*args)

    def forbidden_validation(*args):
        raise AssertionError("trusted query repeated source/slot validation")

    monkeypatch.setattr(module, "_bounds", counted_bounds)
    monkeypatch.setattr(module, "_check_inputs", forbidden_validation)
    result, flipped = interleave(orders, coords, ptr, idx, 0, [0, 1, 2], 3, checked=False)
    assert len(calls) == 1
    assert flipped == expected_flip
    np.testing.assert_array_equal(result, expected)


def test_cheap_bounds_and_donor_validation():
    with pytest.raises(OverflowError, match="rank-span"):
        check_cost_bounds(100, 1 << 60, 3, 1)
    with pytest.raises(ValueError, match="maximum"):
        check_cost_bounds(2, 1, 3, 0)
    orders = np.tile(np.arange(2), (3, 1))
    ptr, idx = csr(2, [(0, 1)])
    with pytest.raises(ValueError, match="donors"):
        interleave(orders, np.ones((2, 2), dtype=np.int64), ptr, idx, 0, [0], 3, donors=(4,))


@pytest.mark.parametrize("axis", range(3))
def test_complementary_nominations_have_identical_results_and_provenance(axis):
    for seed in range(20):
        rng = np.random.default_rng(12000 + 100 * axis + seed)
        n = 2 + seed % 6
        unit = rng.choice(n, size=1 + seed % (n - 1), replace=False).tolist()
        complement = sorted(set(range(n)) - set(unit))
        orders = np.stack([rng.permutation(n) for _ in range(3)])
        coords = np.empty((2, n), dtype=np.int64)
        for physical in range(2):
            coords[physical, orders[physical]] = np.sort(rng.integers(1, 9, n))
        edges = [e for e in combinations(range(n), 2) if rng.random() < 0.5]
        ptr, idx = csr(n, edges)
        infos, results = [], []
        for selected in (unit, complement, unit[::-1] + unit):
            info = {}
            result, flipped = interleave(orders, coords, ptr, idx, axis, selected, 3,
                                          info=info)
            results.append((result, flipped))
            infos.append({k: v for k, v in info.items() if not k.endswith("_wall")})
        for result, flipped in results[1:]:
            np.testing.assert_array_equal(result, results[0][0])
            assert flipped == results[0][1]
        assert infos[0] == infos[1] == infos[2]


@pytest.mark.parametrize("axis", range(3))
def test_partition_union_contains_old_one_sided_minimum(axis):
    for seed in range(12):
        rng = np.random.default_rng(14000 + 100 * axis + seed)
        n = 6
        orders = np.stack([rng.permutation(n) for _ in range(3)])
        coords = np.empty((2, n), dtype=np.int64)
        for physical in range(2):
            coords[physical, orders[physical]] = np.sort(rng.integers(1, 10, n))
        edges = [e for e in combinations(range(n), 2) if rng.random() < 0.5]
        unit = rng.choice(n, size=1 + seed % (n - 1), replace=False).tolist()
        best = check_move(orders, coords, edges, axis, unit, 3)
        assert best <= exhaustive(orders, coords, edges, axis, unit, 3,
                                  both_sides=False)


def nominated_merge_orders(orders, axis, unit):
    """Independent set-valued oracle, disregarding DP tie choices."""
    n = orders.shape[1]
    sides = (set(unit), set(range(n)) - set(unit))
    result = set()
    for selected in sides:
        fixed = [v for v in orders[axis] if v not in selected]
        for donor in range(3):
            strand = [v for v in orders[donor] if v in selected]
            for sequence in (strand, strand[::-1]):
                result.update(tuple(candidate) for candidate in merges(sequence, fixed))
    return result


@pytest.mark.parametrize("axis", range(3))
def test_singleton_partition_contains_local_insertion_and_all_whole_transfers(axis):
    orders = np.array([[0, 1, 2, 3, 4], [2, 0, 3, 1, 4], [4, 1, 0, 3, 2]])
    for vertex in range(5):
        family = nominated_merge_orders(orders, axis, [vertex])
        local = [v for v in orders[axis] if v != vertex]
        assert {tuple(order) for order in merges([vertex], local)} <= family
        for order in orders:
            assert tuple(order) in family
            assert tuple(order[::-1]) in family


def test_canonical_orientation_preserves_traceback_rule_not_first_nomination(monkeypatch):
    import ember_qc.algorithms.factored.order_dp as module

    orders = np.tile(np.arange(4), (3, 1))
    coords = np.ones((2, 4), dtype=np.int64)
    ptr, idx = csr(4, [])
    original = module._fill
    calls = []

    def record(part, rest, *args):
        calls.append((tuple(part), tuple(rest)))
        return original(part, rest, *args)

    monkeypatch.setattr(module, "_fill", record)
    info = {}
    result, flipped = interleave(orders, coords, ptr, idx, 0, [1, 3], 3, info=info)
    # With all-zero charges _fill takes A at each backward tie, so B is
    # emitted first. Swapping kernel orientation would produce [1, 3, 0, 2].
    np.testing.assert_array_equal(result, [0, 2, 1, 3])
    assert not flipped and info["donor"] == 1
    assert info["borrow_side"] == 0
    assert len(calls) == len(set(calls)) == info["candidate_pairs"] == 3
    assert all(set(a) == {1, 3} and set(b) == {0, 2} for a, b in calls)


@pytest.mark.parametrize("axis", range(3))
def test_eleven_pair_bound_and_narrow_rolling_rows(axis, monkeypatch):
    import ember_qc.algorithms.factored.order_dp as module

    orders = np.array([[0, 1, 2, 3, 4, 5], [1, 0, 2, 4, 3, 5],
                       [0, 2, 1, 3, 5, 4]])
    coords = np.ones((2, 6), dtype=np.int64)
    ptr, idx = csr(6, [])
    original = module._prepare_transitions
    pairs = []

    def record(*args):
        part, rest = args[5:7]
        assert len(rest) <= len(part)
        pairs.append((tuple(part), tuple(rest)))
        return original(*args)

    monkeypatch.setattr(module, "_prepare_transitions", record)
    for unit in ([0, 1, 2], [0], [1, 2, 3, 4, 5], [0, 1]):
        pairs.clear()
        info = {}
        interleave(orders, coords, ptr, idx, axis, unit, 3, info=info)
        assert len(pairs) == len(set(pairs)) == info["candidate_pairs"]
        assert info["strand_solves"] == info["candidate_pairs"]
        assert info["candidate_pairs"] + info["candidate_duplicates"] == 12
        if len(unit) == 3:
            assert info["candidate_pairs"] == 11
        if min(len(unit), 6 - len(unit)) == 1:
            assert info["candidate_pairs"] <= 6


def test_singleton_can_reach_six_distinct_complement_strands():
    orders = np.array([[0, 1, 2, 3, 4], [0, 2, 1, 3, 4], [0, 1, 3, 2, 4]])
    coords = np.ones((2, 5), dtype=np.int64)
    ptr, idx = csr(5, [])
    info = {}
    result, _ = interleave(orders, coords, ptr, idx, 0, [0], 3, info=info)
    np.testing.assert_array_equal(result, orders[1])
    assert info["borrowed"] and info["borrow_side"] == 0 and info["borrow_size"] == 4
    assert info["strand_solves"] == info["candidate_pairs"] == 6
    assert info["candidate_duplicates"] == 6


def test_noop_metrics_distinguish_empty_from_whole():
    for n in (0, 1, 4):
        orders = np.tile(np.arange(n), (3, 1))
        coords = np.ones((2, n), dtype=np.int64)
        ptr, idx = csr(n, [])
        info = {}
        assert interleave(orders, coords, ptr, idx, 0, [], 3, info=info) == (None, False)
        assert info["candidate_pairs"] == info["candidate_duplicates"] == 0
        assert info["strand_solves"] == info["direct_scores"] == 0
        assert info["borrow_side"] == -1 and info["borrow_size"] == 0
    info = {}
    interleave(orders, coords, ptr, idx, 0, range(n), 3, info=info)
    assert info["candidate_pairs"] == 2 and info["candidate_duplicates"] == 4
    assert info["direct_scores"] == 1 and info["strand_solves"] == 0


@pytest.mark.parametrize("axis", range(3))
def test_streamed_queries_match_frozen_dense_canonical_results(axis):
    from . import _dense_order_reference as dense

    for seed in range(80):
        rng = np.random.default_rng(30000 + 100 * axis + seed)
        n = seed % 17
        orders = np.stack([rng.permutation(n) for _ in range(3)])
        coords = np.empty((2, n), dtype=np.int64)
        for physical in range(2):
            coords[physical, orders[physical]] = np.sort(rng.integers(1, 20, n))
        density = (0, 0.1, 0.5, 1)[seed % 4]
        edges = [e for e in combinations(range(n), 2) if rng.random() < density]
        ptr, idx = csr(n, edges)
        unit = rng.choice(n, size=seed % (n + 1), replace=False).tolist()
        options = dict(donors=(axis,) if seed % 3 == 0 else None,
                       accept_equal=seed % 5 != 0)
        old, new = {}, {}
        expected, old_flip = dense.interleave(orders, coords, ptr, idx, axis, unit, 3,
                                              info=old, **options)
        actual, new_flip = interleave(orders, coords, ptr, idx, axis, unit, 3,
                                      info=new, **options)
        np.testing.assert_array_equal(actual, expected)
        assert new_flip == old_flip
        for name, value in old.items():
            if not name.endswith("_wall"):
                assert new[name] == value, (seed, name)
        assert new["tracebacks"] <= 1
        assert new["traceback_checks"] <= new["strand_solves"]
        assert new["strand_preparations"] <= 2 * new["strand_solves"]


@pytest.mark.parametrize("axis", range(3))
@pytest.mark.parametrize("edge_mode", ["none", "same", "cross", "complete"])
def test_every_streamed_transition_matches_dense_at_boundaries(axis, edge_mode):
    from . import _dense_order_reference as dense
    import ember_qc.algorithms.factored.order_dp as module

    n = 8
    part, rest = np.array([6, 3, 4, 1, 7]), np.array([0, 5, 2])
    aset = set(part)
    edges = [e for e in combinations(range(n), 2)
             if edge_mode == "complete" or
             (edge_mode == "cross" and ((e[0] in aset) != (e[1] in aset))) or
             (edge_mode == "same" and ((e[0] in aset) == (e[1] in aset)))]
    ptr, idx = csr(n, edges)
    orders = np.array([[7, 6, 5, 4, 3, 2, 1, 0], [4, 7, 1, 5, 3, 0, 6, 2],
                       [0, 6, 3, 5, 4, 1, 2, 7]])
    coords = np.empty((2, n), dtype=np.int64)
    coords[0, orders[0]] = [1, 1, 2, 3, 4, 7, 8, 11]
    coords[1, orders[1]] = [1, 2, 2, 3, 5, 6, 6, 9]
    trank, (lo, hi) = module._ranks(orders[2]), module._bounds(orders, coords, ptr, idx)
    _, ca, cb = dense._prepare_transitions(orders, coords, ptr, idx, axis, part,
                                           rest, 2, trank, lo, hi)
    prepared = module._prepare_transitions(orders, coords, ptr, idx, axis, part,
                                           rest, 2, trank, lo, hi)
    if axis == 2:
        a_offsets, cross, a_states, a_cost, b_states, b_cost = prepared[2]
        for i in range(len(part)):
            for j in range(len(rest) + 1):
                consumed = np.count_nonzero(cross[a_offsets[i]:a_offsets[i + 1]] < j)
                np.testing.assert_array_equal(a_cost[a_states[i] + consumed], ca[i, j])
        for j in range(len(rest)):
            for i in range(len(part) + 1):
                consumed = sum(tuple(sorted((int(rest[j]), int(v)))) in edges for v in part[:i])
                np.testing.assert_array_equal(b_cost[b_states[j] + consumed], cb[j, i])
        cross_count = sum((u in aset) != (v in aset) for u, v in edges)
        assert prepared[3] == n + 2 * cross_count
    else:
        a_offsets, ae, b_offsets, be, coefficients, unary, outside = prepared[2]
        for i in range(len(part)):
            events = ae[a_offsets[i]:a_offsets[i + 1]]
            for j in range(len(rest) + 1):
                counts = np.zeros(4, dtype=np.int64)
                for threshold, kind, change in events:
                    if threshold <= j:
                        counts[kind] += change
                assert module._spatial_price(counts, coefficients[i + j], unary[part[i]],
                                             outside[i + j]) == tuple(ca[i, j])
        counts = np.zeros((len(rest), 4), dtype=np.int64)
        for i in range(len(part) + 1):
            for vertex, kind, change in be[b_offsets[i]:b_offsets[i + 1]]:
                counts[vertex, kind] += change
            for j in range(len(rest)):
                assert module._spatial_price(counts[j], coefficients[i + j], unary[rest[j]],
                                             outside[i + j]) == tuple(cb[j, i])
        assert prepared[3] <= 6 * n
    expected, expected_cost = dense._solve(orders, coords, ptr, idx, axis, part, rest, 2)
    parent, cost, updates = module._fill(part, rest, prepared)
    np.testing.assert_array_equal(module._traceback(part, rest, parent), expected)
    np.testing.assert_array_equal(cost, expected_cost)
    cross_count = sum((u in aset) != (v in aset) for u, v in edges)
    assert updates == (2 * cross_count if axis == 2 else prepared[3] + cross_count)
    assert parent.dtype == np.uint8 and parent.shape == (len(part) + 1, len(rest) + 1)
    # All transition arrays are O(n+E). The sole quadratic array is parent.
    scratch = sum(array.size for group in prepared[1:3] for array in group)
    assert scratch <= 60 * (n + len(edges) + 1)


@pytest.mark.parametrize("axis", range(3))
def test_strand_summaries_are_shared_across_the_query(axis, monkeypatch):
    import ember_qc.algorithms.factored.order_dp as module

    orders = np.array([[0, 1, 2, 3, 4, 5], [1, 0, 2, 4, 3, 5],
                       [0, 2, 1, 3, 5, 4]])
    coords = np.ones((2, 6), dtype=np.int64)
    ptr, idx = csr(6, [(0, 3), (1, 4), (2, 5)])
    original, calls = module._strand_summary, []
    def record(sequence, *args):
        calls.append(tuple(sequence))
        return original(sequence, *args)
    monkeypatch.setattr(module, "_strand_summary", record)
    info = {}
    interleave(orders, coords, ptr, idx, axis, [0, 1, 2], 3, info=info)
    assert info["strand_solves"] == 11
    assert info["strand_preparations"] == len(calls) == len(set(calls)) == 12


def test_deadline_between_preparation_and_fill_discards_incomplete_candidate(monkeypatch):
    import ember_qc.algorithms.factored.order_dp as module

    orders = np.array([[0, 1, 2, 3], [1, 0, 2, 3], [2, 0, 1, 3]])
    coords = np.ones((2, 4), dtype=np.int64)
    ptr, idx = csr(4, [])
    clock = [0.0]
    original = module._prepare_transitions
    def finish_then_expire(*args):
        prepared = original(*args)
        clock[0] = 2.0
        return prepared
    def forbidden(*args):
        raise AssertionError("expired preparation must not enter fill")
    monkeypatch.setattr(module.time, "perf_counter", lambda: clock[0])
    monkeypatch.setattr(module, "_prepare_transitions", finish_then_expire)
    monkeypatch.setattr(module, "_fill", forbidden)
    info = {}
    assert interleave(orders, coords, ptr, idx, 0, [0, 1], 3,
                      deadline=1.0, info=info) == (None, False)
    assert not info["complete"] and info["strand_solves"] == 0
    assert info["strand_preparations"] == 2


def test_deadline_between_strand_kernels_stops_remaining_preparation(monkeypatch):
    import ember_qc.algorithms.factored.order_dp as module

    orders = np.tile(np.arange(4), (3, 1))
    coords = np.ones((2, 4), dtype=np.int64)
    ptr, idx = csr(4, [])
    clock = [0.0]
    original = module._strand_summary
    def finish_then_expire(*args):
        prepared = original(*args)
        clock[0] = 2.0
        return prepared
    monkeypatch.setattr(module.time, "perf_counter", lambda: clock[0])
    monkeypatch.setattr(module, "_strand_summary", finish_then_expire)
    info = {}
    assert interleave(orders, coords, ptr, idx, 0, [0, 1], 3,
                      deadline=1.0, info=info) == (None, False)
    assert not info["complete"] and info["strand_preparations"] == 1
    assert info["event_states"] == info["strand_solves"] == 0


def test_only_final_winner_is_materialized(monkeypatch):
    import ember_qc.algorithms.factored.order_dp as module

    orders = np.array([[0, 1, 2, 3, 4, 5], [1, 0, 2, 4, 3, 5],
                       [0, 2, 1, 3, 5, 4]])
    coords = np.ones((2, 6), dtype=np.int64)
    ptr, idx = csr(6, [])
    original, calls = module._traceback, []
    def record(*args):
        calls.append(1)
        return original(*args)
    monkeypatch.setattr(module, "_traceback", record)
    info = {}
    result, _ = interleave(orders, coords, ptr, idx, 0, [0, 1, 2], 3, info=info)
    assert result is not None and info["strand_solves"] == 11
    assert info["tracebacks"] == len(calls) == 1
    assert info["traceback_checks"] == 11
    calls.clear()
    result, _ = interleave(orders, coords, ptr, idx, 0, [0, 1, 2], 3,
                          accept_equal=False, info=info)
    assert result is None and info["tracebacks"] == len(calls) == 0
