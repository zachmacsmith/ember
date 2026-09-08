"""Source-only spectral initialization invariants and honest bounded failure."""
from copy import deepcopy

import networkx as nx
import numpy as np
import pytest

from ember_qc.algorithms.factored import spectral_order as spectral


def adjacency(graph):
    return {v: list(graph[v]) for v in graph}


def check_orders(orders, graph):
    assert orders is not None
    for order in orders:
        assert len(order) == len(graph) and set(order) == set(graph)


def test_small_path_reports_correct_nonconstant_eigenvalues():
    graph = nx.path_graph(8)
    orders, info = spectral.spectral_orders(adjacency(graph))
    check_orders(orders, graph)
    component = info['components'][0]
    expected = [1 - np.cos(k * np.pi / 8) for k in (1, 2, 3)]
    assert np.allclose(component['eigenvalues'], expected, atol=1e-12)
    assert max(component['residuals']) < 1e-12
    assert info['status'] == 'residual_tolerance'


def test_disconnected_components_isolates_and_two_vertex_component():
    graph = nx.disjoint_union_all([nx.path_graph(18), nx.path_graph(2),
                                   nx.empty_graph(3), nx.cycle_graph(8)])
    orders, info = spectral.spectral_orders(adjacency(graph), seed=7)
    check_orders(orders, graph)
    expected_components = sorted((set(c) for c in nx.connected_components(graph)),
                                 key=lambda c: (-len(c), min(c)))
    for order in orders:
        cursor = 0
        for component in expected_components:
            assert set(order[cursor:cursor + len(component)]) == component
            cursor += len(component)
    two_vertex = next(i for i in info['components'] if i['vertices'] == 2)
    assert len(two_vertex['eigenvalues']) == 1
    assert orders[0][26:28] == orders[1][26:28]
    assert sum(i['solver'] == 'isolate' for i in info['components']) == 3


@pytest.mark.parametrize('graph', [nx.empty_graph(), nx.empty_graph(7)])
def test_empty_or_edgeless_source_needs_no_spectral_work(graph):
    orders, info = spectral.spectral_orders(adjacency(graph), max_work=0)
    check_orders(orders, graph)
    assert info['work'] == 0


def test_repeat_insertion_order_and_metadata_controls():
    graph = nx.gnp_random_graph(48, 0.12, seed=43)
    source = adjacency(graph)
    original = deepcopy(source)
    first, first_info = spectral.spectral_orders(source, seed=19)
    graph.graph.update(family='irrelevant_label', known_embedding={'wrong': [1]})
    second, second_info = spectral.spectral_orders(adjacency(graph), seed=19)
    reversed_source = {v: list(reversed(source[v])) for v in reversed(list(source))}
    third, third_info = spectral.spectral_orders(reversed_source, seed=19)
    assert first == second == third
    assert first_info['work'] == second_info['work'] == third_info['work']
    assert source == original


def test_orientation_is_invariant_to_rotation_of_a_fixed_subspace():
    rng = np.random.default_rng(42)
    reference = rng.standard_normal((20, 2))
    reference -= reference.mean(axis=0)
    vectors, _ = np.linalg.qr(reference)
    angle = 0.73
    rotation = np.array([[np.cos(angle), -np.sin(angle)],
                         [np.sin(angle), np.cos(angle)]])
    first, deficient = spectral._orient(vectors, reference)
    second, other_deficient = spectral._orient(vectors @ rotation, reference)
    assert np.allclose(first, second, atol=1e-12)
    assert not deficient and not other_deficient


def test_degeneracy_at_selected_subspace_boundary_is_exposed():
    orders, info = spectral.spectral_orders(adjacency(nx.complete_graph(32)))
    check_orders(orders, nx.complete_graph(32))
    entry = info['components'][0]
    assert entry['cutoff_uncertain']
    assert abs(entry['cutoff_gap']) < 1e-12


def test_iteration_limit_returns_honestly_approximate_orders():
    graph = nx.path_graph(100)
    orders, info = spectral.spectral_orders(adjacency(graph), max_iterations=0)
    check_orders(orders, graph)
    assert info['status'] == 'approximate'
    assert max(info['components'][0]['residuals'][:2]) > info['tolerance']
    assert info['warnings']


@pytest.mark.parametrize('graph, limit', [(nx.path_graph(8), 100),
                                         (nx.path_graph(100), 300)])
def test_work_limit_rejects_whole_output_with_no_overcharge(graph, limit):
    source = adjacency(graph)
    original = deepcopy(source)
    orders, info = spectral.spectral_orders(source, max_work=limit)
    assert orders is None and info['status'] == 'work_limit'
    assert info['work'] <= limit and source == original


def test_work_cap_is_shared_across_components():
    graph = nx.disjoint_union(nx.path_graph(8), nx.path_graph(8))
    # One component uses 8^3 plus three 22-nonzero residual products = 578.
    orders, info = spectral.spectral_orders(adjacency(graph), max_work=600)
    assert orders is None and info['status'] == 'work_limit'
    assert info['work'] == 578
    assert info['components'][0]['status'] == 'residual_tolerance'


def test_expired_deadline_does_no_spectral_work():
    orders, info = spectral.spectral_orders(adjacency(nx.path_graph(100)), deadline=0)
    assert orders is None and info['status'] == 'deadline'
    assert info['work'] == 0 and info['deadline_overrun'] > 0


def test_late_ordering_does_not_report_timely_output(monkeypatch):
    clock = [0.0]
    monkeypatch.setattr(spectral.time, 'perf_counter', lambda: clock[0])
    original_sort = spectral._axis_order

    def late_sort(*args):
        output = original_sort(*args)
        clock[0] = 2.0
        return output

    monkeypatch.setattr(spectral, '_axis_order', late_sort)
    orders, info = spectral.spectral_orders(adjacency(nx.path_graph(8)), deadline=1.0)
    assert orders is None and info['status'] == 'deadline'
    assert info['wall'] == 2.0 and info['deadline_overrun'] == 1.0


def test_nonfinite_solver_output_is_reported_without_fallback(monkeypatch):
    import scipy.sparse.linalg

    def invalid_solver(operator, initial, **kwargs):
        return np.zeros(3), np.full_like(initial, np.nan)

    monkeypatch.setattr(scipy.sparse.linalg, 'lobpcg', invalid_solver)
    orders, info = spectral.spectral_orders(adjacency(nx.path_graph(80)))
    assert orders is None and info['status'] == 'numerical_failure'


def test_solver_rank_failure_is_reported_without_retry(monkeypatch):
    import scipy.sparse.linalg
    calls = []

    def failed_solver(*args, **kwargs):
        calls.append(1)
        raise ValueError('Linearly dependent initial approximations')

    monkeypatch.setattr(scipy.sparse.linalg, 'lobpcg', failed_solver)
    orders, info = spectral.spectral_orders(adjacency(nx.path_graph(80)))
    assert orders is None and info['status'] == 'numerical_failure'
    assert len(calls) == 1 and 'Linearly dependent' in info['error']


@pytest.mark.parametrize('source', [{0: [1], 1: []}, {0: [0]}, {0: [9]}, {'x': []}])
def test_malformed_adjacency_fails_explicitly(source):
    with pytest.raises(ValueError):
        spectral.spectral_orders(source)
