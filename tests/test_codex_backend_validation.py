"""Regression tests for the backend's public embedding trust boundary."""

import copy
import itertools

import networkx as nx
import pytest

from ember_qc.embedding_backend import (
    build_adjacency,
    is_valid_embedding,
    resolve_overlaps,
)


@pytest.mark.parametrize(
    "embedding",
    [
        None,
        [],
        {},
        {0: []},
        {0: None},
        {0: 0},
        {0: "0"},
        {0: {0: True}},
        {0: [[]]},
        {0: [999]},
        {0: [0, 999]},
        {0: [0, 0]},
        {0: [0, 2]},
        {0: [0], 7: [2]},
        {7: [0]},
    ],
)
def test_rejects_malformed_or_incomplete_single_vertex_embedding(embedding):
    assert not is_valid_embedding(embedding, nx.empty_graph(1), nx.path_graph(3))


@pytest.mark.parametrize("target", [nx.Graph(), nx.path_graph(3)])
def test_empty_source_requires_exactly_empty_mapping(target):
    source = nx.Graph()
    assert is_valid_embedding({}, source, target)
    assert not is_valid_embedding(None, source, target)
    assert not is_valid_embedding({7: [0]}, source, target)


def test_membership_is_checked_for_isolated_vertices():
    source = nx.empty_graph(2)
    target = nx.empty_graph(2)
    assert is_valid_embedding({0: [0], 1: [1]}, source, target)
    assert not is_valid_embedding({0: [0], 1: [2]}, source, target)
    assert not is_valid_embedding({0: [0], 1: [0]}, source, target)


@pytest.mark.parametrize(
    ("source", "target", "embedding", "cached_graph"),
    [
        (nx.empty_graph(1), nx.empty_graph(1), {0: [1]}, nx.path_graph(2)),
        (nx.empty_graph(1), nx.path_graph(3), {0: [0, 2]}, nx.complete_graph(3)),
        (nx.path_graph(2), nx.empty_graph(2), {0: [0], 1: [1]}, nx.path_graph(2)),
    ],
)
def test_routing_cache_cannot_add_nodes_or_couplers(source, target, embedding, cached_graph):
    cache = build_adjacency(cached_graph)
    before = copy.deepcopy(cache)
    assert not is_valid_embedding(embedding, source, target, adj=cache)
    assert cache == before


@pytest.mark.parametrize("cache", [{}, {0: ()}, {999: (1000,), 1000: (999,)}])
def test_incomplete_routing_cache_cannot_reject_valid_embedding(cache):
    assert is_valid_embedding(
        {0: [0, 1], 1: [2]}, nx.path_graph(2), nx.path_graph(3), adj=cache
    )


def test_cache_from_target_before_coupler_deletion_is_not_authoritative():
    target = nx.path_graph(3)
    cached = build_adjacency(target)
    target.remove_edge(1, 2)
    assert not is_valid_embedding(
        {0: [0, 1], 1: [2]}, nx.path_graph(2), target, adj=cached
    )


def test_repair_final_gate_uses_target_instead_of_routing_cache():
    source = nx.path_graph(2)
    target = nx.empty_graph(2)
    cache = build_adjacency(nx.path_graph(2))
    assert resolve_overlaps({0: [0], 1: [1]}, source, target, adj=cache) is None


def test_hashable_labels_and_branching_chains_are_valid_without_mutation():
    source = nx.Graph([("branch", "leaf")])
    source.add_node("isolated")
    target = nx.Graph([((0, 0), (0, 1)), ((0, 0), (1, 0)), ((0, 0), (1, 1))])
    target.add_node((2, 2))
    embedding = {"branch": [(0, 0), (0, 1), (1, 0)], "leaf": [(1, 1)], "isolated": [(2, 2)]}
    original = copy.deepcopy(embedding)
    source_before, target_before = source.copy(), target.copy()

    assert is_valid_embedding(embedding, source, target)
    assert embedding == original
    assert nx.utils.graphs_equal(source, source_before)
    assert nx.utils.graphs_equal(target, target_before)


@pytest.mark.parametrize("chain_type", [list, tuple, set])
def test_structural_predicate_accepts_chain_collections(chain_type):
    assert is_valid_embedding(
        {0: chain_type([0, 1]), 1: chain_type([2])}, nx.path_graph(2), nx.path_graph(3)
    )


def test_matches_networkx_quotients_for_all_small_disjoint_assignments():
    """Exhaust four-qubit targets and disjoint two-chain assignments.

    NetworkX's connectivity and quotient construction provide an independent
    oracle for the optimized predicate, including unused and isolated qubits.
    """
    possible_edges = list(itertools.combinations(range(4), 2))
    sources = [nx.empty_graph(2), nx.path_graph(2)]
    for edge_mask in range(1 << len(possible_edges)):
        target = nx.empty_graph(4)
        target.add_edges_from(
            edge for bit, edge in enumerate(possible_edges) if edge_mask & (1 << bit)
        )
        for owners in itertools.product((-1, 0, 1), repeat=4):
            embedding = {v: [q for q, owner in enumerate(owners) if owner == v] for v in range(2)}
            if not all(embedding.values()):
                for source in sources:
                    assert not is_valid_embedding(embedding, source, target)
                continue
            connected = all(nx.is_connected(target.subgraph(chain)) for chain in embedding.values())
            if connected:
                used = set(embedding[0]) | set(embedding[1])
                quotient = nx.quotient_graph(target.subgraph(used), list(embedding.values()))
                has_contact = quotient.number_of_edges() > 0
            else:
                has_contact = False
            for source in sources:
                expected = connected and (not source.number_of_edges() or has_contact)
                assert is_valid_embedding(embedding, source, target) == expected
