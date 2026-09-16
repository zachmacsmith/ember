"""The native model, total decoder and per-sweep adoption contracts."""
import networkx as nx
import numpy as np

from ember_qc.algorithms.factored import plane
from ember_qc.algorithms.factored.native_model import (
    Source, capacity_ok, complete_coordinates, make_book)


def _orders(n, seed=0):
    rng = np.random.default_rng(seed)
    return np.asarray([rng.permutation(n) for _ in range(3)], dtype=np.int64)


def _query_info(kwargs, *, strict=True, donor=0, borrowed=False, complete=True):
    """Controlled kernel metadata lets these tests isolate sweep orchestration."""
    kwargs["info"].update(
        baseline_score=(0, 20, 100),
        score=(0, 19 if strict else 20, 100),
        donor=donor, donor_mask=1 << donor, borrowed=borrowed,
        strict=strict, complete=complete, strand_solves=2, dp_cells=30,
        direct_scores=3, preparation_wall=0.0, dp_wall=0.0,
    )


def test_single_bars_do_not_reach_ghost_corners():
    source = Source.from_graph(nx.path_graph(2))
    orders = np.tile(np.arange(2), (3, 1))
    coords = np.array([[100, 3], [5, 100]], dtype=np.int64)
    book = make_book(orders, coords, source.indptr, source.indices, 3)
    assert book.active.tolist() == [[False, True], [True, False]]
    assert book.lo[1, 0] == book.hi[1, 0] == 3
    assert book.lo[0, 1] == book.hi[0, 1] == 5
    assert book.score == (0, 2)


def test_shared_even_boundary_is_reserved():
    source = Source.from_graph(nx.path_graph(2))
    orders = np.tile(np.arange(2), (3, 1))
    coords = np.full((2, 2), 2, dtype=np.int64)
    book = make_book(orders, coords, source.indptr, source.indices, 3)
    assert book.guard_lo[book.active].tolist() == [0, 0]
    assert book.guard_hi[book.active].tolist() == [1, 1]
    assert book.reserved == 4


def test_dormant_interpolation_is_ordered_and_does_not_change_active_positions():
    orders = np.tile(np.arange(7), (3, 1))
    coords = np.array([[99, 1, 99, 99, 7, 99, 99]] * 2)
    active = np.array([[False, True, False, False, True, False, False]] * 2)
    filled = complete_coordinates(orders, coords, active, 8)
    assert filled[0].tolist() == [1, 1, 3, 5, 7, 7, 7]
    assert np.array_equal(filled[active], coords[active])


def test_decoder_is_deterministic_and_enforces_both_orientations():
    for graph in (nx.path_graph(12), nx.complete_graph(12), nx.complete_bipartite_graph(7, 9)):
        source = Source.from_graph(graph)
        orders = _orders(len(source.labels), 4)
        a = plane.decode(orders, source, 3, 4, seed=1)
        b = plane.decode(orders, source, 3, 4, seed=1)
        assert np.array_equal(a.coords, b.coords)
        assert a.book.score == b.book.score
        assert capacity_ok(a.book, a.coords, 8, a.extent_m)
        for axis in range(2):
            active = orders[axis][a.book.active[axis, orders[axis]]]
            assert np.all(np.diff(a.coords[axis, active]) >= 0)


def test_total_decoder_accepts_roles_on_an_expanded_fabric():
    source = Source.from_graph(nx.complete_graph(20))
    layout = plane.decode(_orders(20, 2), source, 1, 2)
    assert layout.extent_m > 1
    assert capacity_ok(layout.book, layout.coords, 4, layout.extent_m)
    assert layout.book.outside > 0


def test_units_deduplicate_neighborhoods_and_cover_three_orders():
    source = Source.from_graph(nx.complete_bipartite_graph(8, 8))
    bag = plane.units(_orders(16), source, np.random.default_rng(0))
    keys = [(axis, tuple(sorted(unit))) for axis, unit in bag]
    assert len(keys) == len(set(keys))
    assert {axis for axis, _ in keys} == {0, 1, 2}
    for axis in range(3):
        assert (axis, tuple(range(8))) in keys
        assert (axis, tuple(range(8, 16))) in keys
        assert keys.count((axis, tuple(range(16)))) == 1


def test_packing_occurs_once_after_many_adoptions_and_worse_output_is_kept(monkeypatch):
    source = Source.from_graph(nx.path_graph(6))
    actual_decode = plane.decode
    decoded_orders = []
    first_layout = []

    def decode(*args, **kwargs):
        layout = actual_decode(*args, **kwargs)
        decoded_orders.append(layout.orders.copy())
        if not first_layout:
            first_layout.append(layout)
        else:
            # An even translation preserves both capacity directions while
            # producing a genuinely worse expanded layout with a fresh book.
            layout.coords += 10
            layout.extent_m += 5
            layout.book = make_book(layout.orders, layout.coords,
                                    source.indptr, source.indices, 3)
            assert capacity_ok(layout.book, layout.coords, 8, layout.extent_m)
        return layout

    def propose(orders, coords, indptr, indices, axis, unit, chip_m, **kwargs):
        assert len(decoded_orders) == 1  # No pack between accepted questions.
        _query_info(kwargs, donor=axis)
        return np.roll(orders[axis], 1), False

    monkeypatch.setattr(plane, "decode", decode)
    monkeypatch.setattr(plane, "interleave", propose)
    best, info = plane.arrange(source, 3, 4, max_asks=5)
    assert info["asks"] == info["accepts"] == 5
    assert info["strict_accepts"] == 5
    assert info["neutral_accepts"] == 0
    assert info["decode_calls"] == len(decoded_orders) == 2
    assert info["adopt_worse"] == 1
    assert best is first_layout[0]
    assert not np.array_equal(decoded_orders[0], decoded_orders[1])
    assert info["stopped_by"] == "asks"
    assert info["final_current_score"] > info["final_bookmark_score"]
    assert not info["final_current_usable"]


def test_only_finite_decoded_layouts_can_be_bookmarks():
    source = Source.from_graph(nx.complete_graph(20))
    best, info = plane.arrange(source, 1, 2, max_asks=2)
    assert best is None
    assert info["outside_reserved_qubits"] > 0
    assert info["infeasible"] == 0


def test_work_budget_and_schedule_reproducibility():
    source = Source.from_graph(nx.gnp_random_graph(12, .3, seed=4))
    a, da = plane.arrange(source, 3, 4, seed=2, max_asks=25)
    b, db = plane.arrange(source, 3, 4, seed=2, sched_seed=2, max_asks=25)
    assert da["asks"] == db["asks"] == 25
    assert np.array_equal(a.coords, b.coords)
    assert np.array_equal(a.orders, b.orders)
    assert a.book.score == b.book.score
    for key in ("accepts", "strict_accepts", "neutral_accepts", "dp_solves",
                "dp_cells", "whole_order_accepts", "accepted_by_donor",
                "repeated_sweep_states"):
        assert da[key] == db[key], key
    trajectories = [[{k: v for k, v in row.items() if k != "wall"}
                     for row in info["sweep_traj"]] for info in (da, db)]
    assert trajectories[0] == trajectories[1]


def test_deadline_between_axis_packs_preserves_last_valid_state(monkeypatch):
    source = Source.from_graph(nx.path_graph(16))
    orders = _orders(len(source.labels))
    now = [0.0]
    actual_pack = plane.pack_axis
    packed = []

    def pack_then_expire(*args, **kwargs):
        lines, metrics = actual_pack(*args, **kwargs)
        packed.append((args[0].copy(), lines.copy()))
        now[0] = 2.0
        return lines, metrics

    monkeypatch.setattr(plane.time, "perf_counter", lambda: now[0])
    monkeypatch.setattr(plane, "pack_axis", pack_then_expire)
    info = {}
    layout = plane.decode(orders, source, 3, 4, seed=0, deadline=1.0, info=info)

    assert len(packed) == info["readouts"] == 1
    assert not layout.complete
    assert capacity_ok(layout.book, layout.coords, 8, layout.extent_m)
    vertices, last_lines = packed[0]
    np.testing.assert_array_equal(layout.coords[0, vertices], last_lines)
    rebuilt = make_book(layout.orders, layout.coords, source.indptr, source.indices, 3)
    assert layout.book.score == rebuilt.score


def test_deadline_after_adoption_keeps_earlier_better_finite_bookmark(monkeypatch):
    source = Source.from_graph(nx.path_graph(16))
    now = [0.0]
    actual_decode = plane.decode
    decoded = []
    readout_counts = []

    def capture_decode(*args, **kwargs):
        layout = actual_decode(*args, **kwargs)
        decoded.append(layout)
        readout_counts.append(kwargs["info"]["readouts"])
        return layout

    def one_unit(orders, source, rng, **kwargs):
        return [(0, (int(orders[0, -1]),))]

    def accept_then_expire(orders, coords, indptr, indices, axis, unit, chip_m, **kwargs):
        # An admissible singleton interleaving; this test controls acceptance
        # independently of the exhaustive tests of the proposal optimizer.
        _query_info(kwargs, donor=axis, complete=False)
        now[0] = 2.0
        return np.roll(orders[axis], 1), False

    monkeypatch.setattr(plane.time, "perf_counter", lambda: now[0])
    monkeypatch.setattr(plane, "decode", capture_decode)
    monkeypatch.setattr(plane, "units", one_unit)
    monkeypatch.setattr(plane, "interleave", accept_then_expire)
    best, info = plane.arrange(source, 3, 4, seed=0, max_asks=10, deadline=1.0)

    assert len(decoded) == info["decode_calls"] == 2
    initial, interrupted = decoded
    assert initial.complete and not interrupted.complete
    assert initial.book.outside == interrupted.book.outside == 0
    assert initial.book.score < interrupted.book.score
    assert best is initial
    assert readout_counts[0] > 0
    assert readout_counts[0] == readout_counts[1]
    np.testing.assert_array_equal(interrupted.orders[0], np.roll(initial.orders[0], 1))
    for layout in decoded:
        assert capacity_ok(layout.book, layout.coords, 8, layout.extent_m)
    assert info["asks"] == info["accepts"] == 1
    assert info["interrupted_asks"] == 1
    assert info["dp_solves"] == 2
    assert info["adopt_worse"] == 1
    assert info["bookmark_asks"] == 0
    assert info["stopped_by"] == "deadline"


def test_all_three_orders_see_live_donors_with_one_frozen_slot_vector(monkeypatch):
    source = Source.from_graph(nx.complete_graph(12))
    actual_decode = plane.decode
    actual_complete = plane.complete_coordinates
    decoded = []
    completions = []
    expected_orders = []
    expected_coords = []
    fixed_slots = []
    asked_axes = []

    def capture_decode(*args, **kwargs):
        if decoded:
            np.testing.assert_array_equal(args[0], expected_orders[0])
        result = actual_decode(*args, **kwargs)
        decoded.append(result)
        return result

    def complete_once(*args, **kwargs):
        result = actual_complete(*args, **kwargs)
        completions.append(result.copy())
        return result

    def three_units(orders, source, rng, **kwargs):
        whole = tuple(range(orders.shape[1]))
        return [(0, whole), (2, whole), (1, whole)]

    def propose(orders, coords, indptr, indices, axis, unit, chip_m, **kwargs):
        assert len(decoded) == len(completions) == 1
        donors = kwargs.get("donors")
        assert donors is None or set(donors) == {0, 1, 2}
        assert kwargs.get("accept_equal", True)
        if not expected_orders:
            expected_orders.append(orders.copy())
            expected_coords.append(coords.copy())
            fixed_slots.append(np.asarray([coords[a, orders[a]].copy() for a in range(2)]))
            assert any(len(np.unique(slots)) > 1 for slots in fixed_slots[0])
        np.testing.assert_array_equal(orders, expected_orders[0])
        np.testing.assert_array_equal(coords, expected_coords[0])
        asked_axes.append(axis)
        if axis == 0:
            result, donor = orders[axis, ::-1].copy(), axis
        else:
            donor = 0 if axis == 2 else 2
            # t borrows x AFTER x changed, then y borrows t AFTER t changed.
            result = orders[donor].copy()
        assert not np.array_equal(result, orders[axis])
        _query_info(kwargs, strict=axis == 0, donor=donor, borrowed=donor != axis)
        expected_orders[0][axis] = result
        if axis < 2:
            expected_coords[0][axis, result] = fixed_slots[0][axis]
        return result, axis == 0

    monkeypatch.setattr(plane, "decode", capture_decode)
    monkeypatch.setattr(plane, "complete_coordinates", complete_once)
    monkeypatch.setattr(plane, "units", three_units)
    monkeypatch.setattr(plane, "interleave", propose)
    best, info = plane.arrange(source, 4, 4, seed=0, max_asks=3, trace=True)

    assert asked_axes == [0, 2, 1]
    assert len(decoded) == info["decode_calls"] == 2
    assert info["accepts"] == info["whole_order_accepts"] == 3
    assert info["strict_accepts"] == 1
    assert info["neutral_accepts"] == info["borrowed_accepts"] == 2
    assert info["dp_solves"] == 6 and info["dp_cells"] == 90
    assert info["direct_scores"] == 9
    assert info["accepted_by_donor"][2][0] == 1
    assert info["accepted_by_donor"][1][2] == 1
    assert len(info["sweep_traj"]) == 2
    assert info["sweep_traj"][-1]["strict"] == 1
    assert info["sweep_traj"][-1]["neutral"] == 2
    assert best.book.outside == 0
    assert capacity_ok(best.book, best.coords, 8, best.extent_m)


def test_deadline_inside_query_without_winner_keeps_the_only_decoded_bookmark(monkeypatch):
    source = Source.from_graph(nx.path_graph(16))
    actual_decode = plane.decode
    now = [0.0]
    decoded = []

    def capture_decode(*args, **kwargs):
        result = actual_decode(*args, **kwargs)
        decoded.append(result)
        return result

    def interrupt_query(orders, coords, indptr, indices, axis, unit, chip_m, **kwargs):
        assert kwargs["deadline"] == 1.0
        _query_info(kwargs, strict=False, donor=axis, complete=False)
        now[0] = 2.0
        return None, False

    monkeypatch.setattr(plane.time, "perf_counter", lambda: now[0])
    monkeypatch.setattr(plane, "decode", capture_decode)
    monkeypatch.setattr(plane, "interleave", interrupt_query)
    best, info = plane.arrange(source, 3, 4, seed=0, max_asks=10, deadline=1.0)

    assert len(decoded) == info["decode_calls"] == 1
    assert best is decoded[0]
    assert best.complete
    assert info["asks"] == info["interrupted_asks"] == 1
    assert info["accepts"] == info["strict_accepts"] == info["neutral_accepts"] == 0
    assert info["dp_solves"] == 2 and info["dp_cells"] == 30
    assert info["stopped_by"] == "deadline"
    assert capacity_ok(best.book, best.coords, 8, best.extent_m)


def test_neutral_cycle_is_adopted_and_visible_separately_from_bookmark(monkeypatch):
    source = Source.from_graph(nx.complete_graph(6))
    actual_decode = plane.decode
    decoded = []

    def capture_decode(*args, **kwargs):
        result = actual_decode(*args, **kwargs)
        decoded.append(result)
        return result

    def one_unit(orders, source, rng, **kwargs):
        return [(0, tuple(range(orders.shape[1])))]

    def reverse_neutrally(orders, coords, indptr, indices, axis, unit, chip_m, **kwargs):
        assert kwargs.get("accept_equal", True)
        _query_info(kwargs, strict=False, donor=axis)
        return orders[axis, ::-1].copy(), True

    monkeypatch.setattr(plane, "decode", capture_decode)
    monkeypatch.setattr(plane, "units", one_unit)
    monkeypatch.setattr(plane, "interleave", reverse_neutrally)
    best, info = plane.arrange(source, 3, 4, seed=0, max_asks=2)

    assert len(decoded) == 3
    assert info["strict_accepts"] == 0
    assert info["accepts"] == info["neutral_accepts"] == 2
    assert best is decoded[0]
    assert not np.array_equal(decoded[0].orders, decoded[1].orders)
    np.testing.assert_array_equal(decoded[0].orders, decoded[2].orders)
    np.testing.assert_array_equal(decoded[0].coords, decoded[2].coords)
    assert info["repeated_sweep_states"] == 1
    assert info["sweep_traj"][-1]["repeated_state"]
    assert info["stopped_by"] == "asks"
    assert tuple(info["final_current_score"]) == decoded[-1].book.score
    assert tuple(info["final_bookmark_score"]) == best.book.score
    assert info["final_current_usable"]

    # Independently verify that the saved bookmark still converts to a valid
    # embedding after later neutral states were adopted and revisited.
    import dwave_networkx as dnx
    from ember_qc.algorithms.factored.placement import ZephyrFabric, materialize
    from ember_qc.embedding_backend import is_valid_embedding

    target = dnx.zephyr_graph(3, 4)
    embedding = materialize(best, source, ZephyrFabric.from_graph(target))
    assert is_valid_embedding(embedding, nx.complete_graph(6), target)
