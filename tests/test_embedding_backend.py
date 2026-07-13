"""
tests/test_embedding_backend.py
===============================
Unit tests for the shared round → repair backend (ember_qc.embedding_backend):
routing primitives (node-weighted Dijkstra, path reconstruction, connectivity)
and the round → grow → de-conflict pipeline.
"""
import numpy as np
import networkx as nx
import pytest

from ember_qc.embedding_backend import (
    build_adjacency,
    chain_components,
    chain_connected,
    grow_to_connected,
    is_valid_embedding,
    reconstruct_path,
    resolve_overlaps,
    round_assignment,
    round_assignment_matrix,
    weighted_multisource_dijkstra,
)


@pytest.fixture
def path5():
    """Path 0-1-2-3-4 — predictable adjacency for routing tests."""
    return nx.path_graph(5)


# ── Routing primitives ─────────────────────────────────────────────────────────

class TestDijkstra:
    def test_node_weighted_distance_sums_node_costs(self, path5):
        adj = build_adjacency(path5)
        cost = {q: 1.0 for q in path5}
        dist, pred = weighted_multisource_dijkstra(adj, {0}, cost)
        # path cost includes both endpoints, so reaching node k costs k+1
        assert dist == {0: 1.0, 1: 2.0, 2: 3.0, 3: 4.0, 4: 5.0}

    def test_expensive_node_is_routed_around_in_cost(self, path5):
        adj = build_adjacency(path5)
        cost = {q: 1.0 for q in path5}
        cost[2] = 10.0
        dist, _ = weighted_multisource_dijkstra(adj, {0}, cost)
        assert dist[2] == 12.0 and dist[3] == 13.0

    def test_multisource(self, path5):
        adj = build_adjacency(path5)
        cost = {q: 1.0 for q in path5}
        dist, _ = weighted_multisource_dijkstra(adj, {0, 4}, cost)
        assert dist[0] == 1.0 and dist[4] == 1.0 and dist[2] == 3.0

    def test_forbidden_blocks_paths(self, path5):
        adj = build_adjacency(path5)
        cost = {q: 1.0 for q in path5}
        dist, _ = weighted_multisource_dijkstra(adj, {0}, cost, forbidden={2})
        assert 3 not in dist and 4 not in dist  # 2 walls off the far side
        assert set(dist) == {0, 1}

    def test_reconstruct_path(self, path5):
        adj = build_adjacency(path5)
        cost = {q: 1.0 for q in path5}
        _, pred = weighted_multisource_dijkstra(adj, {0}, cost)
        assert reconstruct_path(pred, 3) == [0, 1, 2, 3]
        assert reconstruct_path({}, 9) == []  # unreachable

    def test_visit_counter_accumulates(self, path5):
        adj = build_adjacency(path5)
        cost = {q: 1.0 for q in path5}
        counter = [0]
        weighted_multisource_dijkstra(adj, {0}, cost, visit_counter=counter)
        assert counter[0] == 5  # all nodes settled


class TestConnectivity:
    def test_chain_connected(self, path5):
        adj = build_adjacency(path5)
        assert chain_connected([1, 2, 3], adj)
        assert not chain_connected([0, 2], adj)  # gap at 1
        assert chain_connected([0], adj)         # singleton
        assert chain_connected([], adj)          # empty

    def test_chain_components_deterministic(self, path5):
        adj = build_adjacency(path5)
        comps = chain_components([0, 2, 1, 4], adj)
        # {0,1,2} contiguous, {4} isolated; discovered in list order
        assert sorted(map(sorted, comps)) == [[0, 1, 2], [4]]


# ── Round → repair ─────────────────────────────────────────────────────────────

class TestRoundAssignment:
    def test_argmax_per_qubit_with_tiebreak(self):
        assignment = {
            10: {0: 0.9, 1: 0.1},
            11: {0: 0.2, 1: 0.8},
            12: {0: 0.5, 1: 0.5},  # tie → lowest source id (0)
        }
        chains = round_assignment(assignment)
        assert chains == {0: [10, 12], 1: [11]}

    def test_threshold_drops_weak_assignments(self):
        assignment = {10: {0: 0.9}, 11: {0: 0.3}}
        chains = round_assignment(assignment, threshold=0.5)
        assert chains == {0: [10]}

    def test_matrix_form_matches_dict_form(self):
        mat = np.array([[0.9, 0.1], [0.2, 0.8]])
        chains = round_assignment_matrix(mat, qubit_nodes=[10, 11], source_nodes=[0, 1])
        assert chains == {0: [10], 1: [11]}


class TestGrowToConnected:
    def test_disconnected_chain_is_stitched(self, path5):
        # chain {0:[0,2]} has a gap at qubit 1; growth should fill it
        grown = grow_to_connected({0: [0, 2]}, path5)
        adj = build_adjacency(path5)
        assert chain_connected(grown[0], adj)
        assert set(grown[0]) == {0, 1, 2}

    def test_already_connected_chain_unchanged(self, path5):
        grown = grow_to_connected({0: [1, 2]}, path5)
        assert set(grown[0]) == {1, 2}


class TestResolveOverlaps:
    def test_fixable_overlap_legalized(self, path5):
        # source edge A(0)-B(1); chains share qubit 2 → one must yield
        source = nx.path_graph(2)
        chains = {0: [1, 2], 1: [2, 3]}
        out = resolve_overlaps(chains, source, path5)
        assert out is not None
        assert is_valid_embedding(out, source, path5)
        # disjoint
        all_q = [q for c in out.values() for q in c]
        assert len(all_q) == len(set(all_q))

    def test_valid_input_returns_valid(self, path5):
        source = nx.path_graph(2)
        chains = {0: [0, 1], 1: [2, 3]}
        out = resolve_overlaps(chains, source, path5)
        assert out is not None and is_valid_embedding(out, source, path5)

    def test_impossible_returns_none(self):
        # K4 cannot embed into a single edge — legalization must fail cleanly
        target = nx.path_graph(2)
        source = nx.complete_graph(4)
        chains = {v: [0, 1] for v in source.nodes()}
        assert resolve_overlaps(chains, source, target, max_passes=5) is None


class TestIsValidEmbedding:
    def test_detects_valid_and_invalid(self, path5):
        source = nx.path_graph(2)
        assert is_valid_embedding({0: [0, 1], 1: [2, 3]}, source, path5)
        # overlap on qubit 1
        assert not is_valid_embedding({0: [0, 1], 1: [1, 2]}, source, path5)
        # missing edge: chains 0 and 4 not adjacent in the path
        assert not is_valid_embedding({0: [0], 1: [4]}, source, path5)
