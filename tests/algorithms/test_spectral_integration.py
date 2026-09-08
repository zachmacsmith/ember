"""Order semantics, scheduler isolation, and native spectral failure boundaries."""
from copy import deepcopy

import dwave_networkx as dnx
import networkx as nx
import numpy as np
import pytest

from ember_qc.algorithms.factored import field, native, plane, spectral_order
from ember_qc.embedding_backend import is_valid_embedding


def grid():
    target = dnx.zephyr_graph(3)
    return field.TileGrid(target, dnx.zephyr_layout(target), courses=True)


def plain(value):
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, dict):
        return {key: plain(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [plain(item) for item in value]
    return value


def comparable(result):
    positions, state, info = result
    info = {k: v for k, v in info.items() if k not in ('wall', 'bookmark_wall')}
    return plain((positions, state, info))


@pytest.mark.parametrize('source', [nx.complete_graph(8),
                                    nx.gnp_random_graph(18, 0.22, seed=39)])
def test_explicit_random_orders_preserve_rank_semantics_and_full_search(source):
    adjacency = {v: sorted(source[v]) for v in source}
    ids = sorted(adjacency)
    rng = np.random.default_rng(7)
    # The original initializer draws ranks indexed by sorted vertex ID.
    ranks = [rng.permutation(len(ids)) for _ in (0, 1)]
    orders = tuple([ids[i] for i in np.argsort(axis)] for axis in ranks)
    original_orders = deepcopy(orders)
    baseline = plane.arrange(adjacency, grid(), seed=7, sched_seed=23,
                             max_asks=120, snap=True, trace=True)
    explicit = plane.arrange(adjacency, grid(), seed=91, sched_seed=23,
                             max_asks=120, snap=True, trace=True,
                             initial_orders=orders)
    assert comparable(explicit) == comparable(baseline)
    assert orders == original_orders


@pytest.mark.parametrize('orders', [([0, 1], [0, 1]),
                                    ([0, 1, 1], [0, 1, 2]),
                                    ([0, 1, 2], [0, 1, 9]),
                                    ([0, 1, 2],)])
def test_invalid_orders_fail_before_packing(monkeypatch, orders):
    def forbidden(*args, **kwargs):
        raise AssertionError('packing called with invalid source coverage')

    monkeypatch.setattr(plane, 'readout', forbidden)
    with pytest.raises(ValueError, match='two permutations'):
        plane.arrange({0: [1], 1: [0, 2], 2: [1]}, grid(), initial_orders=orders)


@pytest.mark.parametrize('status', ['work_limit', 'numerical_failure',
                                    'dependency_unavailable', 'deadline'])
def test_no_initial_orders_never_runs_an_alternate_constructor(monkeypatch, status):
    calls = []

    def failed(source, **kwargs):
        calls.append(kwargs)
        return None, {'status': status}

    def forbidden(*args, **kwargs):
        raise AssertionError('placement called after initialization failure')

    monkeypatch.setattr(spectral_order, 'spectral_orders', failed)
    monkeypatch.setattr(plane, 'arrange', forbidden)
    result = native.native_embed(nx.path_graph(8), dnx.zephyr_graph(3),
                                 initialization='spectral', seed=19)
    expected = 'TIMEOUT' if status == 'deadline' else 'INITIALIZATION_FAILED'
    assert result['status'] == expected and not result['embedding']
    assert result['diag']['initialization_info']['status'] == status
    assert len(calls) == 1 and calls[0]['seed'] == 19


def test_initialization_placement_and_repair_share_deadline(monkeypatch):
    from ember_qc.algorithms.factored import contact_repair
    seen = []

    def wrap(original):
        def recorded(*args, **kwargs):
            seen.append(kwargs['deadline'])
            return original(*args, **kwargs)
        return recorded

    monkeypatch.setattr(spectral_order, 'spectral_orders', wrap(spectral_order.spectral_orders))
    monkeypatch.setattr(plane, 'arrange', wrap(plane.arrange))
    monkeypatch.setattr(contact_repair, 'contact_polish', wrap(contact_repair.contact_polish))
    source, target = nx.path_graph(8), dnx.zephyr_graph(3)
    result = native.native_embed(source, target, initialization='spectral',
                                 max_asks=20, polish_passes=1, timeout=30)
    assert result['success'], result
    assert len(seen) == 3 and len(set(seen)) == 1 and seen[0] is not None
    assert is_valid_embedding(result['embedding'], source, target)


def test_finite_approximate_orders_are_used_once_and_remain_labeled(monkeypatch):
    calls = []
    original = plane.arrange

    def approximate(source, **kwargs):
        calls.append('initializer')
        return (sorted(source), sorted(source)), {'status': 'approximate'}

    def placement(*args, **kwargs):
        calls.append('placement')
        return original(*args, **kwargs)

    monkeypatch.setattr(spectral_order, 'spectral_orders', approximate)
    monkeypatch.setattr(plane, 'arrange', placement)
    source, target = nx.path_graph(8), dnx.zephyr_graph(3)
    result = native.native_embed(source, target, initialization='spectral',
                                 max_asks=20, timeout=30)
    assert result['success'], result
    assert calls == ['initializer', 'placement']
    assert result['diag']['initialization_info']['status'] == 'approximate'
    assert is_valid_embedding(result['embedding'], source, target)


def test_spectral_native_preserves_labels_isolates_and_ignores_metadata():
    source = nx.cycle_graph(12)
    source.add_node(12)
    labels = {v: ('variable', v) if v % 2 else f'x-{v}' for v in source}
    transformed = nx.Graph(family='arbitrary', name='ignored',
                           embedding={'irrelevant': [-123]})
    transformed.add_nodes_from(labels[v] for v in source)
    transformed.add_edges_from((labels[v], labels[u]) for u, v in reversed(list(source.edges())))
    target = dnx.zephyr_graph(3)
    config = dict(initialization='spectral', seed=4, max_asks=50,
                  polish_passes=1, max_groups=8, timeout=30)
    baseline = native.native_embed(source, target, **config)
    changed = native.native_embed(transformed, target, **config)
    assert baseline['success'] and changed['success'], (baseline, changed)
    assert {v: changed['embedding'][labels[v]] for v in source} == baseline['embedding']
    assert is_valid_embedding(changed['embedding'], transformed, target)


def test_expired_initialization_cannot_start_placement(monkeypatch):
    now = [0.0]
    monkeypatch.setattr(native.time, 'perf_counter', lambda: now[0])

    def late(source, **kwargs):
        now[0] = 2.0
        return (sorted(source), sorted(source)), {'status': 'approximate'}

    def forbidden(*args, **kwargs):
        raise AssertionError('placement started after the overall deadline')

    monkeypatch.setattr(spectral_order, 'spectral_orders', late)
    monkeypatch.setattr(plane, 'arrange', forbidden)
    result = native.native_embed(nx.path_graph(8), dnx.zephyr_graph(3),
                                 initialization='spectral', timeout=1)
    assert result['status'] == 'TIMEOUT' and not result['embedding']
    assert result['diag']['deadline_overrun'] == 1
