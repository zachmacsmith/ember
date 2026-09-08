"""Eligibility and coverage checks for the explicit independent constructor."""
import importlib.abc
import sys

import dwave_networkx as dnx
import networkx as nx
import pytest

from ember_qc.algorithms.factored.native import native_embed
from ember_qc.embedding_backend import is_valid_embedding


class _NoEmbeddingLibrary(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split('.')[0] in {'minorminer', '_minorminer', 'busclique'}:
            raise AssertionError(f'Forbidden embedding library: {fullname}')


def test_native_succeeds_and_fails_without_legalizer(monkeypatch):
    from ember_qc.algorithms.factored import placement
    def forbidden(*args, **kwargs):
        raise AssertionError('inherited MM legalizer called')
    monkeypatch.setattr(placement, '_mm_route', forbidden)
    blocker = _NoEmbeddingLibrary()
    sys.meta_path.insert(0, blocker)
    try:
        source, target = nx.complete_graph(8), dnx.zephyr_graph(3)
        result = native_embed(source, target, timeout=30, max_asks=100)
        assert result['success'], result
        assert is_valid_embedding(result['embedding'], source, target)
        failed = native_embed(nx.complete_graph(30), dnx.zephyr_graph(2),
                              timeout=30, max_asks=1)
        assert failed['status'] == 'CONSTRUCTION_FAILED', failed
        assert not failed['embedding']
    finally:
        sys.meta_path.remove(blocker)


def test_mixed_source_labels_and_isolates_survive():
    source = nx.empty_graph(['a', ('b', 2), 99])
    target = dnx.zephyr_graph(3)
    result = native_embed(source, target, construction='packed', timeout=30)
    assert result['success'], result
    assert set(result['embedding']) == set(source)
    assert is_valid_embedding(result['embedding'], source, target)


@pytest.mark.parametrize('strategy', ['random', 'degree', 'bfs'])
def test_fixed_packed_constructor_is_deterministic(strategy):
    source, target = nx.complete_graph(8), dnx.zephyr_graph(3)
    a = native_embed(source, target, construction='packed', order_strategy=strategy)
    b = native_embed(source, target, construction='packed', order_strategy=strategy)
    assert a['success'], a
    assert a['embedding'] == b['embedding']
    assert is_valid_embedding(a['embedding'], source, target)


def test_capacity_and_unsupported_target_are_explicit():
    assert native_embed(nx.empty_graph(5000), dnx.zephyr_graph(12))['status'] == 'INFEASIBLE_CAPACITY'
    assert native_embed(nx.path_graph(4), nx.path_graph(8))['status'] == 'UNSUPPORTED'
