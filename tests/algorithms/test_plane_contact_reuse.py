"""Contact reuse must preserve carried-rank semantics and complete trajectories."""
from copy import deepcopy

import dwave_networkx as dnx
import networkx as nx
import numpy as np
import pytest

from ember_qc.algorithms.factored import field, plane


def grid():
    target = dnx.zephyr_graph(3, 4)
    return field.TileGrid(target, dnx.zephyr_layout(target), courses=True)


def plain(value):
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, dict):
        return {key: plain(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [plain(item) for item in value]
    return value


def tied_state():
    source = nx.gnp_random_graph(13, 0.3, seed=17)
    source.add_node(13)  # Include an isolate in the participating vertex set.
    adjacency = {v: sorted(source[v]) for v in source}
    positions = {v: np.array([float((v * 5) % 11), 3.0]) for v in source}
    orders = {0: sorted(source, key=lambda v: (positions[v][0], v)),
              1: list(reversed(list(source)))}
    return adjacency, positions, orders


@pytest.mark.parametrize("snap", [False, True])
@pytest.mark.parametrize("bounded", [False, True])
@pytest.mark.parametrize("axes", [(1, 0, 1), (0, 1, 0)])
def test_coordinate_packs_reuse_contacts_but_rebuild_geometry(monkeypatch, snap, bounded, axes):
    adjacency, positions, orders = tied_state()
    original_positions = plain(positions)
    target_grid = grid()
    calls = []
    original_contacts = plane._stair_contacts

    def counted(*args, **kwargs):
        result = original_contacts(*args, **kwargs)
        calls.append(deepcopy(result))
        return result

    monkeypatch.setattr(plane, "_stair_contacts", counted)
    monkeypatch.setattr(field, "_VERIFY_CONTACTS", True)
    current, state = positions, None
    for axis in axes:
        previous = plain(state)
        old_state = state
        current, state, _ = plane.readout(axis, orders, current, adjacency,
                                         target_grid, snap=snap, bounded=bounded, bk=state)
        # Sharing read-only contacts must not mutate prior geometry or contacts.
        assert plain(old_state) == previous
        fresh = field.arm_books(
            current, adjacency, target_grid, kappa=1.0, floor=False,
            snap=snap, min_span=0.0,
            contacts=original_contacts(current, adjacency, yrank=plane.rank_of(orders[1])),
            yrank=plane.rank_of(orders[1]), ybound=False)
        assert plain(state) == plain(fresh)
    assert len(calls) == 1
    assert state[0] == calls[0]
    assert plain(positions) == original_positions
    assert plain(current) != original_positions


def test_new_order_or_source_rebuilds_contacts(monkeypatch):
    adjacency, positions, orders = tied_state()
    target_grid = grid()
    monkeypatch.setattr(field, "_VERIFY_CONTACTS", True)
    _, first, _ = plane.readout(0, orders, positions, adjacency, target_grid, snap=True)
    reversed_orders = {0: orders[0], 1: list(reversed(orders[1]))}
    _, reversed_state, _ = plane.readout(0, reversed_orders, positions, adjacency,
                                        target_grid, snap=True)
    assert reversed_state[0] != first[0]
    assert reversed_state[0] == field._stair_contacts(
        positions, adjacency, yrank=plane.rank_of(reversed_orders[1]))
    # Change the same adjacency object's contents; no cross-call identity cache.
    adjacency[0].append(13)
    adjacency[13].append(0)
    _, changed, _ = plane.readout(0, orders, positions, adjacency, target_grid, snap=True)
    assert changed[0] != first[0]
    assert changed[0] == field._stair_contacts(
        positions, adjacency, yrank=plane.rank_of(orders[1]))


@pytest.mark.parametrize("source", [nx.complete_graph(8),
                                    nx.gnp_random_graph(16, 0.25, seed=29),
                                    nx.convert_node_labels_to_integers(nx.grid_2d_graph(4, 4))])
def test_full_search_matches_forced_contact_recomputation(monkeypatch, source):
    adjacency = {v: sorted(source[v]) for v in source}
    monkeypatch.setattr(field, "_VERIFY_CONTACTS", True)
    original_books, original_reinsert = plane.books, plane.align_reinsert
    attempts = []

    def recorded(*args, **kwargs):
        result = original_reinsert(*args, **kwargs)
        attempts.append((kwargs["axis"], tuple(args[0]), tuple(sorted(args[1])),
                         tuple(args[3]), tuple(sorted(kwargs["other"].items())),
                         None if result[0] is None else tuple(result[0]), result[1]))
        return result

    monkeypatch.setattr(plane, "align_reinsert", recorded)
    optimized = plane.arrange(adjacency, grid(), seed=7, sched_seed=11,
                              max_asks=160, snap=True, trace=True)
    optimized_attempts = list(attempts)
    attempts.clear()

    def recomputed(*args, **kwargs):
        kwargs.pop("contacts", None)
        return original_books(*args, **kwargs)

    monkeypatch.setattr(plane, "books", recomputed)
    reference = plane.arrange(adjacency, grid(), seed=7, sched_seed=11,
                              max_asks=160, snap=True, trace=True)
    assert attempts == optimized_attempts
    assert plain(optimized[:2]) == plain(reference[:2])
    for info in (optimized[2], reference[2]):
        info.pop("wall")
        info.pop("bookmark_wall")
    assert optimized[2] == reference[2]
