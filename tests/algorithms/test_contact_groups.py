"""Coverage and bounds for contact groups, without embedding-algorithm calls."""
from copy import deepcopy
from itertools import combinations

import networkx as nx
import pytest

from ember_qc.algorithms.factored.contact_groups import round_robin_groups
from ember_qc.algorithms.factored.contact_repair import _Context


def complete_fixture(lengths=(3, 2, 1, 1), labels=(0, 1, 2, 3)):
    source = nx.complete_graph(labels)
    embedding = {}
    start = 0
    for v, length in zip(labels, lengths):
        embedding[v] = list(range(start, start + length))
        start += length
    target = nx.complete_graph(start)
    ctx = _Context(source, target)
    assert ctx.valid(embedding)
    return embedding, source, target, ctx


def test_later_windows_expose_pairs_omitted_by_top_neighbor_selection():
    embedding, _source, _target, ctx = complete_fixture()
    # With these costs, every vertex's highest-ranked neighbor is 0, except
    # vertex 0, whose first neighbor is 1. The old one-neighbor rule can only
    # propose {0,1}, {0,2}, and {0,3}; it cannot propose the useful-cost pair
    # {1,2}, regardless of its group cap.
    legacy_pairs = {frozenset((0, v)) for v in (1, 2, 3)}
    result = round_robin_groups(embedding, ctx, (2,), 100)
    sets = {frozenset(group) for group in result}
    assert frozenset((1, 2)) not in legacy_pairs
    assert frozenset((1, 2)) in sets
    expected = {frozenset(pair) for pair in combinations(ctx.nodes, 2)
                if any(len(embedding[v]) > ctx.lower_bound(v) for v in pair)}
    assert sets == expected


def test_every_center_gets_a_pair_round_before_triples():
    embedding, _source, _target, ctx = complete_fixture((2, 2, 2, 2))
    result = round_robin_groups(embedding, ctx, (2, 3), 4)
    assert [len(group) for group in result] == [2, 2, 2, 3]
    assert set().union(*(set(group) for group in result[:3])) == set(ctx.nodes)
    assert frozenset(result[3]) == frozenset((0, 1, 2))


def test_enabled_singletons_precede_other_configured_sizes():
    embedding, _source, _target, ctx = complete_fixture()
    result = round_robin_groups(embedding, ctx, (3, 1, 2, 1), 100)
    assert result[:2] == [(0,), (1,)]
    assert all(len(group) >= 2 for group in result[2:])
    assert len(result[2]) == 3  # Larger sizes retain the configured order.
    without = round_robin_groups(embedding, ctx, (2, 3), 100)
    assert all(len(group) > 1 for group in without)


@pytest.mark.parametrize("limit", [0, 1, 2, 4, 7, 100])
def test_limits_give_deterministic_prefixes_of_distinct_known_groups(limit):
    embedding, _source, _target, ctx = complete_fixture((2, 2, 2, 2))
    full = round_robin_groups(embedding, ctx, (1, 2, 3, 4), 100)
    result = round_robin_groups(embedding, ctx, (1, 2, 3, 4), limit)
    assert result == full[:limit]
    assert len(result) <= limit
    assert len({frozenset(group) for group in result}) == len(result)
    for group in result:
        assert 1 <= len(group) <= 4
        assert len(set(group)) == len(group)
        assert set(group) <= set(embedding)
        assert sum(len(embedding[v]) - ctx.lower_bound(v) for v in group) > 0


def test_physical_blockers_and_logical_neighbors_share_the_neighbor_universe():
    source = nx.Graph()
    source.add_nodes_from((0, 1, 2))
    source.add_edge(0, 1)
    target = nx.Graph([(0, 1), (1, 2), (3, 4), (0, 3)])
    embedding = {0: [0, 1], 1: [2], 2: [3, 4]}
    ctx = _Context(source, target)
    assert ctx.valid(embedding)
    pairs = {frozenset(group)
             for group in round_robin_groups(embedding, ctx, (2,), 100)}
    assert pairs == {frozenset((0, 1)), frozenset((0, 2))}
    assert not source.has_edge(0, 2)


def test_order_and_metadata_do_not_change_groups_or_mutate_inputs():
    labels = ("center", 7, ("source", 2), -4)
    embedding, source, target, ctx = complete_fixture((2, 2, 2, 2), labels)
    snapshot = deepcopy(embedding)
    expected = round_robin_groups(embedding, ctx, (1, 2, 3), 100)
    reversed_source = nx.Graph()
    reversed_source.add_nodes_from(reversed(list(source)))
    reversed_source.add_edges_from((b, a) for a, b in reversed(list(source.edges())))
    reversed_source.graph["family"] = "unused metadata"
    reversed_target = nx.Graph()
    reversed_target.add_nodes_from(reversed(list(target)))
    reversed_target.add_edges_from((b, a) for a, b in reversed(list(target.edges())))
    reversed_embedding = {v: list(reversed(chain))
                          for v, chain in reversed(list(embedding.items()))}
    reversed_ctx = _Context(reversed_source, reversed_target)
    assert round_robin_groups(reversed_embedding, reversed_ctx, (1, 2, 3), 100) == expected
    assert embedding == snapshot
    assert reversed_embedding == {v: list(reversed(chain))
                                  for v, chain in reversed(list(snapshot.items()))}


def test_empty_inputs_and_zero_excess_produce_no_groups():
    assert round_robin_groups({}, _Context(nx.Graph(), nx.Graph()), (1, 2), 10) == []
    embedding, _source, _target, ctx = complete_fixture((1, 1, 1, 1))
    assert round_robin_groups(embedding, ctx, (1, 2, 3, 4), 100) == []


def test_singleton_cap_returns_before_scanning_physical_neighbors():
    embedding, _source, _target, ctx = complete_fixture((2, 2, 2, 2))
    # A tight singleton-first cap needs only the chain costs. Requiring the
    # full physical adjacency scan here would defeat that bounded fast path.
    ctx.adj = None
    assert round_robin_groups(embedding, ctx, (1, 2, 3), 2) == [(0,), (1,)]
