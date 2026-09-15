"""The native model, total decoder and per-sweep adoption contracts."""
import networkx as nx
import numpy as np

from ember_qc.algorithms.factored import plane
from ember_qc.algorithms.factored.native_model import (
    Source, capacity_ok, complete_coordinates, make_book)


def _orders(n, seed=0):
    rng = np.random.default_rng(seed)
    return np.asarray([rng.permutation(n) for _ in range(3)], dtype=np.int64)


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
            # A worse successful decoder response must not veto its proposal.
            layout.book.reserved += 100
        return layout

    def propose(orders, coords, indptr, indices, axis, unit, chip_m):
        return np.roll(orders[axis], 1), False

    monkeypatch.setattr(plane, "decode", decode)
    monkeypatch.setattr(plane, "interleave", propose)
    best, info = plane.arrange(source, 3, 4, max_asks=5)
    assert info["asks"] == info["accepts"] == 5
    assert info["decode_calls"] == len(decoded_orders) == 2
    assert info["adopt_worse"] == 1
    assert best is first_layout[0]
    assert not np.array_equal(decoded_orders[0], decoded_orders[1])
    assert info["stopped_by"] == "asks"


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

    def one_unit(orders, source, rng):
        return [(0, (int(orders[0, -1]),))]

    def accept_then_expire(orders, coords, indptr, indices, axis, unit, chip_m):
        # An admissible singleton interleaving; this test controls acceptance
        # independently of the exhaustive tests of the proposal optimizer.
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
    assert info["adopt_worse"] == 1
    assert info["bookmark_asks"] == 0
    assert info["stopped_by"] == "deadline"
