"""The native model, total decoder and live reference/packing contracts."""
import networkx as nx
import numpy as np

from ember_qc.algorithms.factored import plane
from ember_qc.algorithms.factored.native_model import (
    Source, capacity_ok, complete_coordinates, make_book)


def _orders(n, seed=0):
    rng = np.random.default_rng(seed)
    return np.asarray([rng.permutation(n) for _ in range(3)], dtype=np.int64)


def _query_info(kwargs, *, strict=True, donor=0, borrowed=False, complete=True,
                borrow_side=0, borrow_size=1):
    """Controlled kernel metadata lets these tests isolate reference-loop orchestration."""
    kwargs["info"].update(
        baseline_score=(0, 20, 100),
        score=(0, 19 if strict else 20, 100),
        donor=donor, donor_mask=1 << donor, borrowed=borrowed,
        strict=strict, complete=complete, strand_solves=2, dp_cells=30,
        direct_scores=3, preparation_wall=0.0, dp_wall=0.0, traceback_wall=0.25,
        candidate_pairs=7, candidate_duplicates=5,
        borrow_side=borrow_side, borrow_size=borrow_size,
        event_states=11, event_updates=13, strand_preparations=4,
        traceback_checks=2, tracebacks=1,
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



def _schedule(n, seed):
    rng = np.random.default_rng(np.random.SeedSequence([seed, 1]))
    return rng.permutation(n), int(rng.integers(5)), int(rng.integers(3))


def _no_change(orders, coords, indptr, indices, axis, unit, chip_m, **kwargs):
    _query_info(kwargs, strict=False, donor=axis)
    return None, False


def test_nomination_reads_source_and_anchor_without_sampling():
    source = Source.from_graph(nx.path_graph(8))
    orders = _orders(8)

    class NoRandom:
        def integers(self, *args):
            raise AssertionError("source and anchor nominations are deterministic")

    np.testing.assert_array_equal(plane.nominate(orders, source, 3, 0, NoRandom()), [2, 4])
    np.testing.assert_array_equal(plane.nominate(orders, source, 3, 4, NoRandom()), [3])


def test_live_windows_sample_exactly_the_admissible_starts():
    for n in (2, 3, 8, 9):
        source = Source.from_graph(nx.path_graph(n))
        orders = _orders(n, 7)
        size = max(1, n // 2)
        for relation in (1, 2, 3):
            for position, vertex in enumerate(orders[relation - 1]):
                lo = max(0, position - size + 1)
                hi = min(position, n - size) + 1
                for start in range(lo, hi):
                    class FixedRandom:
                        def integers(self, actual_lo, actual_hi):
                            assert (actual_lo, actual_hi) == (lo, hi)
                            return start

                    window = plane.nominate(orders, source, int(vertex), relation, FixedRandom())
                    assert len(window) == size and vertex in window
                    np.testing.assert_array_equal(window, orders[relation - 1, start:start + size])


def test_reference_relation_and_destination_coverage_without_a_membership_queue(monkeypatch):
    source = Source.from_graph(nx.path_graph(6))
    n, seed, rounds = 6, 7, 15
    references, relation_phase, destination_phase = _schedule(n, seed)
    monkeypatch.setattr(plane, "interleave", _no_change)
    budget = rounds * (3 + 3 * n)
    best, info = plane.arrange(source, 3, 4, seed=seed, max_asks=budget, trace=True)
    assert info["asks"] == budget
    assert info["passes"] == info["completed_rounds"] == rounds
    assert info["reference_visits"] == rounds * n
    assert info["decode_calls"] == 1
    assert info["unique_partitions"] is info["nomination_duplicates"] is None
    assert info["scheduler_version"] == plane.SCHEDULER_VERSION
    rows = iter(info["trace"])
    coverage = {int(v): set() for v in references}
    for r in range(rounds):
        for offset in range(3):
            row = next(rows)
            assert row["reference"] is None and row["relation"] == "whole"
            assert row["order"] == (r + destination_phase + offset) % 3
            assert row["size"] == n
        for i, vertex in enumerate(references):
            relation = (i + r + relation_phase) % 5
            first_axis = (i + r + destination_phase) % 3
            coverage[int(vertex)].add((relation, first_axis))
            for offset in range(3):
                row = next(rows)
                assert row["reference"] == vertex
                assert row["relation"] == plane.RELATIONS[relation]
                assert row["order"] == (first_axis + offset) % 3
                assert not row["changed"]
    assert all(len(pairs) == 15 for pairs in coverage.values())
    assert info["nomination_counts"]["whole"] == 3 * rounds
    assert sum(info["nomination_counts"].values()) == budget
    assert all(work["asks"] == info["nomination_counts"][name]
               for name, work in info["relation_work"].items())
    assert info["stopped_by"] == "asks"  # Quiet rounds never prove convergence.
    assert info["repeated_sweep_states"] == rounds
    assert len(info["sweep_traj"]) == rounds + 1
    assert best.book.outside == 0


def test_pack_after_each_change_and_continue_from_worse_decoded_layout(monkeypatch):
    source = Source.from_graph(nx.path_graph(6))
    actual_decode = plane.decode
    decoded = []
    queries = []

    def capture_decode(*args, **kwargs):
        layout = actual_decode(*args, **kwargs)
        if decoded:
            layout.coords += 10 * len(decoded)
            layout.extent_m += 5 * len(decoded)
            layout.book = make_book(layout.orders, layout.coords,
                                    source.indptr, source.indices, 3)
            assert capacity_ok(layout.book, layout.coords, 8, layout.extent_m)
        decoded.append(layout)
        return layout

    def propose(orders, coords, indptr, indices, axis, unit, chip_m, **kwargs):
        assert len(decoded) == len(queries) + 1
        np.testing.assert_array_equal(orders, decoded[-1].orders)
        np.testing.assert_array_equal(coords, complete_coordinates(
            decoded[-1].orders, decoded[-1].coords, decoded[-1].book.active, 8))
        queries.append(axis)
        _query_info(kwargs, donor=axis)
        return np.roll(orders[axis], 1), False

    monkeypatch.setattr(plane, "decode", capture_decode)
    monkeypatch.setattr(plane, "interleave", propose)
    best, info = plane.arrange(source, 3, 4, max_asks=5, trace=True)
    assert info["asks"] == info["accepts"] == info["strict_accepts"] == 5
    assert info["decode_calls"] == len(decoded) == 6
    assert info["adopt_worse"] == 1
    assert all(layout.book.score > decoded[0].book.score for layout in decoded[1:])
    assert best is decoded[0]
    assert info["final_current_score"] > info["final_bookmark_score"]
    assert not info["final_current_usable"]
    assert sum(w["decoded_worse"] for w in info["relation_work"].values()) == 1
    assert sum(w["decode_calls"] for w in info["relation_work"].values()) == 5
    assert info["last_query"]["reference"] == info["trace"][-1]["reference"]


def test_nomination_is_fresh_before_every_destination_even_when_unchanged(monkeypatch):
    source = Source.from_graph(nx.complete_graph(8))
    actual_nominate = plane.nominate
    nominated = []
    calls = []
    decoded = []
    actual_decode = plane.decode

    def capture_decode(*args, **kwargs):
        layout = actual_decode(*args, **kwargs)
        decoded.append(layout)
        return layout

    def capture_nomination(orders, graph, reference, relation, rng):
        np.testing.assert_array_equal(orders, decoded[-1].orders)
        unit = actual_nominate(orders, graph, reference, relation, rng)
        nominated.append((orders.copy(), reference, relation, unit.copy()))
        return unit

    def propose(orders, coords, indptr, indices, axis, unit, chip_m, **kwargs):
        call = len(calls)
        calls.append(axis)
        np.testing.assert_array_equal(orders, decoded[-1].orders)
        if call >= 3:
            assert len(nominated) == call - 2
            np.testing.assert_array_equal(unit, nominated[-1][3])
        _query_info(kwargs, donor=axis)
        # Alternate changes and unchanged results, including within one visit.
        return (np.roll(orders[axis], 1) if call % 2 == 0 else None), False

    monkeypatch.setattr(plane, "nominate", capture_nomination)
    monkeypatch.setattr(plane, "decode", capture_decode)
    monkeypatch.setattr(plane, "interleave", propose)
    _, info = plane.arrange(source, 3, 4, seed=3, max_asks=9, trace=True)
    assert len(nominated) == 6
    assert len(decoded) == info["decode_calls"] == 6
    assert info["reference_visits"] == 2
    assert info["accepts"] == 5
    assert info["completed_rounds"] == 0


def test_slots_are_completed_per_query_and_donors_follow_immediate_decodes(monkeypatch):
    source = Source.from_graph(nx.complete_graph(12))
    actual_decode = plane.decode
    actual_complete = plane.complete_coordinates
    decoded, completions, axes = [], [], []

    def capture_decode(*args, **kwargs):
        result = actual_decode(*args, **kwargs)
        decoded.append(result)
        return result

    def capture_complete(*args, **kwargs):
        result = actual_complete(*args, **kwargs)
        completions.append(result.copy())
        return result

    def propose(orders, coords, indptr, indices, axis, unit, chip_m, **kwargs):
        assert len(decoded) == len(completions) == len(axes) + 1
        np.testing.assert_array_equal(orders, decoded[-1].orders)
        np.testing.assert_array_equal(coords, completions[-1])
        assert kwargs.get("donors") is None
        donor = axis if not axes else axes[-1]
        result = orders[axis, ::-1].copy() if not axes else orders[donor].copy()
        assert not np.array_equal(result, orders[axis])
        _query_info(kwargs, strict=not axes, donor=donor, borrowed=bool(axes),
                    borrow_side=len(axes) % 2, borrow_size=len(unit))
        axes.append(axis)
        return result, len(axes) == 1

    monkeypatch.setattr(plane, "decode", capture_decode)
    monkeypatch.setattr(plane, "complete_coordinates", capture_complete)
    monkeypatch.setattr(plane, "interleave", propose)
    best, info = plane.arrange(source, 4, 4, seed=0, max_asks=3, trace=True)
    assert len(decoded) == info["decode_calls"] == 4
    assert info["accepts"] == info["whole_order_accepts"] == 3
    assert info["strict_accepts"] == 1
    assert info["neutral_accepts"] == info["borrowed_accepts"] == 2
    assert info["accepted_by_side"] == [2, 1]
    for key, expected in (("dp_solves", 6), ("dp_cells", 90), ("direct_scores", 9),
                          ("candidate_pairs", 21), ("candidate_duplicates", 15),
                          ("event_states", 33), ("event_updates", 39),
                          ("strand_preparations", 12), ("traceback_checks", 6),
                          ("tracebacks", 3), ("traceback_wall", 0.75)):
        assert info[key] == expected
        assert info["relation_work"]["whole"][key] == expected
    assert info["sweep_traj"][-1]["strict"] == 1
    assert info["sweep_traj"][-1]["neutral"] == 2
    assert best.book.outside == 0
    assert capacity_ok(best.book, best.coords, 8, best.extent_m)


def test_immutable_graph_validation_happens_once(monkeypatch):
    source = Source.from_graph(nx.path_graph(6))
    actual_check = plane._check_inputs
    calls = []

    def count_check(*args, **kwargs):
        calls.append(True)
        return actual_check(*args, **kwargs)

    monkeypatch.setattr(plane, "_check_inputs", count_check)
    monkeypatch.setattr(plane, "interleave", _no_change)
    plane.arrange(source, 3, 4, max_asks=30)
    assert len(calls) == 1


def test_search_without_queries_skips_nomination(monkeypatch):
    source = Source.from_graph(nx.path_graph(6))

    def forbidden(*args, **kwargs):
        raise AssertionError("no-query search must not nominate")

    monkeypatch.setattr(plane, "nominate", forbidden)
    monkeypatch.setattr(plane, "interleave", forbidden)
    for options, reason in ((dict(moves=False), "moves-off"),
                            (dict(max_asks=0), "asks"),
                            (dict(deadline=-1.0), "deadline")):
        best, info = plane.arrange(source, 3, 4, **options)
        assert best.book.outside == 0
        assert info["asks"] == info["passes"] == info["completed_rounds"] == 0
        assert info["reference_visits"] == info["nomination_wall"] == 0
        assert info["unique_partitions"] is None
        assert info["stopped_by"] == reason
        assert info["last_query"] is None


def test_work_budget_during_prelude_visit_and_exact_round_boundary(monkeypatch):
    source = Source.from_graph(nx.path_graph(6))
    monkeypatch.setattr(plane, "interleave", _no_change)
    for budget, visits, rounds in ((1, 0, 0), (2, 0, 0), (3, 0, 0),
                                   (4, 1, 0), (5, 1, 0), (6, 1, 0),
                                   (21, 6, 1), (22, 6, 1)):
        _, info = plane.arrange(source, 3, 4, max_asks=budget)
        assert info["asks"] == budget
        assert info["reference_visits"] == visits
        assert info["completed_rounds"] == rounds
        assert info["passes"] == (2 if budget > 21 else 1)
        assert info["sweep_traj"][-1]["complete"] == (budget == 21)
        assert info["stopped_by"] == "asks"


def test_only_finite_decoded_layouts_can_be_bookmarks():
    source = Source.from_graph(nx.complete_graph(20))
    best, info = plane.arrange(source, 1, 2, max_asks=2)
    assert best is None
    assert info["outside_reserved_qubits"] > 0
    assert info["infeasible"] == 0


def test_work_budget_and_schedule_reproducibility():
    source = Source.from_graph(nx.gnp_random_graph(12, .3, seed=4))
    a, da = plane.arrange(source, 3, 4, seed=2, max_asks=25, trace=True)
    b, db = plane.arrange(source, 3, 4, seed=2, sched_seed=2, max_asks=25, trace=True)
    assert da["asks"] == db["asks"] == 25
    assert np.array_equal(a.coords, b.coords)
    assert np.array_equal(a.orders, b.orders)
    assert a.book.score == b.book.score
    for key in ("accepts", "strict_accepts", "neutral_accepts", "dp_solves",
                "dp_cells", "whole_order_accepts", "accepted_by_donor",
                "repeated_sweep_states", "accepted_by_side", "unique_partitions",
                "nomination_duplicates", "candidate_pairs", "candidate_duplicates",
                "trace", "nomination_counts", "reference_visits", "completed_rounds"):
        assert da[key] == db[key], key
    trajectories = [[{k: v for k, v in row.items() if k != "wall"}
                     for row in info["sweep_traj"]] for info in (da, db)]
    assert trajectories[0] == trajectories[1]


def test_schedule_seed_does_not_change_initialization():
    source = Source.from_graph(nx.path_graph(12))
    a, _ = plane.arrange(source, 3, 4, seed=2, sched_seed=4, max_asks=0)
    b, _ = plane.arrange(source, 3, 4, seed=2, sched_seed=9, max_asks=0)
    np.testing.assert_array_equal(a.orders, b.orders)
    np.testing.assert_array_equal(a.coords, b.coords)
    np.testing.assert_array_equal(a.orders, _orders(12, 2))


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

    def accept_then_expire(orders, coords, indptr, indices, axis, unit, chip_m, **kwargs):
        _query_info(kwargs, donor=axis, complete=False)
        now[0] = 2.0
        return np.roll(orders[axis], 1), False

    monkeypatch.setattr(plane.time, "perf_counter", lambda: now[0])
    monkeypatch.setattr(plane, "decode", capture_decode)
    monkeypatch.setattr(plane, "interleave", accept_then_expire)
    best, info = plane.arrange(source, 3, 4, seed=0, max_asks=10, deadline=1.0, trace=True)
    assert len(decoded) == info["decode_calls"] == 2
    initial, interrupted = decoded
    assert initial.complete and not interrupted.complete
    assert initial.book.outside == interrupted.book.outside == 0
    assert initial.book.score < interrupted.book.score
    assert best is initial
    assert readout_counts[0] > 0 and readout_counts[0] == readout_counts[1]
    axis = info["trace"][0]["order"]
    np.testing.assert_array_equal(interrupted.orders[axis], np.roll(initial.orders[axis], 1))
    for layout in decoded:
        assert capacity_ok(layout.book, layout.coords, 8, layout.extent_m)
    assert info["asks"] == info["accepts"] == info["interrupted_asks"] == 1
    assert info["dp_solves"] == 2 and info["adopt_worse"] == 1
    assert info["bookmark_asks"] == 0
    assert info["stopped_by"] == "deadline"


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
    assert best is decoded[0] and best.complete
    assert info["asks"] == info["interrupted_asks"] == 1
    assert info["accepts"] == info["strict_accepts"] == info["neutral_accepts"] == 0
    assert info["dp_solves"] == 2 and info["dp_cells"] == 30
    assert info["stopped_by"] == "deadline"
    assert capacity_ok(best.book, best.coords, 8, best.extent_m)


def test_interruption_inside_reference_visit_preserves_last_completed_query(monkeypatch):
    source = Source.from_graph(nx.path_graph(8))
    calls = []

    def interrupt(orders, coords, indptr, indices, axis, unit, chip_m, **kwargs):
        calls.append(axis)
        _query_info(kwargs, strict=False, donor=axis, complete=len(calls) < 5)
        return None, False

    monkeypatch.setattr(plane, "interleave", interrupt)
    best, info = plane.arrange(source, 3, 4, max_asks=100, trace=True)
    assert info["asks"] == 5 and info["reference_visits"] == 1
    assert info["completed_rounds"] == 0
    assert info["decode_calls"] == 1
    assert info["interrupted_asks"] == 1
    assert info["stopped_by"] == "interrupted"
    assert best.book.outside == 0


def test_neutral_cycle_is_adopted_and_bookmark_stays_physically_valid(monkeypatch):
    source = Source.from_graph(nx.complete_graph(6))
    actual_decode = plane.decode
    decoded = []

    def capture_decode(*args, **kwargs):
        result = actual_decode(*args, **kwargs)
        decoded.append(result)
        return result

    def reverse_neutrally(orders, coords, indptr, indices, axis, unit, chip_m, **kwargs):
        assert kwargs.get("accept_equal", True)
        _query_info(kwargs, strict=False, donor=axis)
        return orders[axis, ::-1].copy(), True

    monkeypatch.setattr(plane, "decode", capture_decode)
    monkeypatch.setattr(plane, "interleave", reverse_neutrally)
    best, info = plane.arrange(source, 3, 4, seed=0, max_asks=6)
    assert len(decoded) == 7
    assert info["strict_accepts"] == 0
    assert info["accepts"] == info["neutral_accepts"] == 6
    assert best is decoded[0]
    np.testing.assert_array_equal(decoded[0].orders, decoded[-1].orders)
    np.testing.assert_array_equal(decoded[0].coords, decoded[-1].coords)
    assert info["repeated_sweep_states"] == 1
    assert info["sweep_traj"][-1]["repeated_state"]
    assert info["stopped_by"] == "asks"
    assert tuple(info["final_current_score"]) == decoded[-1].book.score
    assert tuple(info["final_bookmark_score"]) == best.book.score
    assert info["final_current_usable"]

    import dwave_networkx as dnx
    import minorminer
    from ember_qc.algorithms.factored.placement import ZephyrFabric, materialize
    from ember_qc.embedding_backend import is_valid_embedding

    def forbidden(*args, **kwargs):
        raise AssertionError("native output must not call MinorMiner")

    monkeypatch.setattr(minorminer, "find_embedding", forbidden)
    target = dnx.zephyr_graph(3, 4)
    embedding = materialize(best, source, ZephyrFabric.from_graph(target))
    assert is_valid_embedding(embedding, nx.complete_graph(6), target)


def test_isolated_and_single_vertex_sources_are_trivial(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("trivial search must not query")

    monkeypatch.setattr(plane, "interleave", forbidden)
    isolated = Source.from_graph(nx.empty_graph(3))
    singleton = Source((0,), (), np.zeros(2, dtype=np.int64), np.empty(0, dtype=np.int64))
    for source in (isolated, singleton):
        best, info = plane.arrange(source, 3, 4)
        assert best is not None
        assert info["stopped_by"] == "trivial"
        assert info["asks"] == info["passes"] == info["reference_visits"] == 0
    assert plane.arrange(isolated, 3, 4, target_qubits=2)[0] is None
