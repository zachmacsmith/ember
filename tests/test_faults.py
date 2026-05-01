"""
tests/test_faults.py
=====================
Tests for ember_qc.faults.simulate_faults.

No external dependencies beyond networkx (always available).
"""
import pytest
import networkx as nx

from ember_qc.faults import simulate_faults


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_path(n: int) -> nx.Graph:
    """Path graph P_n with integer-labeled nodes 0..n-1."""
    return nx.path_graph(n)


def make_complete(n: int) -> nx.Graph:
    return nx.complete_graph(n)


def make_cycle(n: int) -> nx.Graph:
    return nx.cycle_graph(n)


# ===========================================================================
# No-fault baseline
# ===========================================================================

class TestNoFaults:
    def test_returns_copy_not_view(self):
        G = make_path(5)
        H = simulate_faults(G)
        assert H is not G

    def test_same_node_set(self):
        G = make_path(5)
        H = simulate_faults(G)
        assert set(H.nodes()) == set(G.nodes())

    def test_same_edge_set(self):
        G = make_path(5)
        H = simulate_faults(G)
        assert set(H.edges()) == set(G.edges())

    def test_zero_fault_rate_explicit(self):
        G = make_complete(6)
        H = simulate_faults(G, fault_rate=0.0)
        assert set(H.nodes()) == set(G.nodes())
        assert H.number_of_edges() == G.number_of_edges()

    def test_single_node_graph(self):
        G = nx.Graph()
        G.add_node(0)
        H = simulate_faults(G)
        assert list(H.nodes()) == [0]

    def test_empty_graph(self):
        G = nx.Graph()
        H = simulate_faults(G)
        assert H.number_of_nodes() == 0


# ===========================================================================
# Random fault mode (fault_rate > 0)
# ===========================================================================

class TestRandomFaultMode:
    def test_correct_node_count_removed(self):
        G = make_complete(10)
        H = simulate_faults(G, fault_rate=0.3, fault_seed=0)
        expected_removed = int(10 * 0.3)  # 3
        assert H.number_of_nodes() == 10 - expected_removed

    def test_fault_rate_0_5(self):
        G = make_complete(10)
        H = simulate_faults(G, fault_rate=0.5, fault_seed=42)
        assert H.number_of_nodes() == 5

    def test_fault_rate_1_0_removes_all(self):
        G = make_path(8)
        H = simulate_faults(G, fault_rate=1.0, fault_seed=0)
        assert H.number_of_nodes() == 0

    def test_deterministic_with_same_seed(self):
        G = make_complete(20)
        H1 = simulate_faults(G, fault_rate=0.4, fault_seed=7)
        H2 = simulate_faults(G, fault_rate=0.4, fault_seed=7)
        assert set(H1.nodes()) == set(H2.nodes())

    def test_different_seeds_give_different_results(self):
        # With a large enough graph this is overwhelmingly likely to differ.
        G = make_complete(50)
        removed_0 = set(G.nodes()) - set(simulate_faults(G, fault_rate=0.4, fault_seed=0).nodes())
        removed_1 = set(G.nodes()) - set(simulate_faults(G, fault_rate=0.4, fault_seed=99).nodes())
        assert removed_0 != removed_1

    def test_removed_nodes_are_subset_of_original(self):
        G = make_complete(15)
        H = simulate_faults(G, fault_rate=0.2, fault_seed=3)
        assert set(H.nodes()).issubset(set(G.nodes()))

    def test_incident_edges_removed_with_faulty_node(self):
        # In a path graph, removing a middle node must remove its two edges.
        G = make_path(5)   # 0-1-2-3-4
        # Force removal of node 2 (the middle) by removing exactly 1 node,
        # then verify that edges (1,2) and (2,3) are gone.
        # We can't control WHICH node is removed, so just verify the
        # invariant: no edge in H touches a removed node.
        H = simulate_faults(G, fault_rate=0.2, fault_seed=0)
        removed = set(G.nodes()) - set(H.nodes())
        for u, v in H.edges():
            assert u not in removed
            assert v not in removed

    def test_returns_networkx_graph(self):
        G = make_complete(5)
        H = simulate_faults(G, fault_rate=0.2, fault_seed=0)
        assert isinstance(H, nx.Graph)

    def test_fault_rate_small_graph_floor(self):
        # int(3 * 0.5) = 1 — only one node removed.
        G = make_path(3)
        H = simulate_faults(G, fault_rate=0.5, fault_seed=0)
        assert H.number_of_nodes() == 2

    def test_all_nodes_present_when_fault_rate_rounds_to_zero(self):
        # int(2 * 0.4) = 0 → no nodes removed
        G = make_path(2)
        H = simulate_faults(G, fault_rate=0.4, fault_seed=0)
        assert H.number_of_nodes() == 2

    def test_without_seed_is_nondeterministic_across_calls(self):
        # Two unseed calls should differ at least sometimes on a large graph.
        G = make_complete(40)
        results = [frozenset(simulate_faults(G, fault_rate=0.5).nodes()) for _ in range(5)]
        assert len(set(results)) > 1  # at least two distinct outcomes


# ===========================================================================
# Explicit fault mode — faulty_nodes
# ===========================================================================

class TestExplicitFaultyNodes:
    def test_specific_nodes_removed(self):
        G = make_path(6)
        H = simulate_faults(G, faulty_nodes=[2, 4])
        assert 2 not in H.nodes()
        assert 4 not in H.nodes()
        assert {0, 1, 3, 5} == set(H.nodes())

    def test_incident_edges_removed_automatically(self):
        G = make_complete(5)
        H = simulate_faults(G, faulty_nodes=[0])
        for u, v in H.edges():
            assert u != 0 and v != 0

    def test_empty_faulty_nodes_list_is_noop(self):
        G = make_path(5)
        H = simulate_faults(G, faulty_nodes=[])
        assert set(H.nodes()) == set(G.nodes())

    def test_remove_all_nodes_explicitly(self):
        G = make_path(4)
        H = simulate_faults(G, faulty_nodes=[0, 1, 2, 3])
        assert H.number_of_nodes() == 0

    def test_single_faulty_node(self):
        G = make_complete(5)
        H = simulate_faults(G, faulty_nodes=[3])
        assert 3 not in H.nodes()
        assert H.number_of_nodes() == 4

    def test_unknown_node_raises(self):
        G = make_path(3)
        with pytest.raises(ValueError, match="faulty_nodes contains nodes not in topology"):
            simulate_faults(G, faulty_nodes=[99])

    def test_preserves_non_faulty_edges(self):
        G = make_complete(5)  # edges: all pairs
        H = simulate_faults(G, faulty_nodes=[4])
        # All edges among 0-3 must survive
        for u in range(4):
            for v in range(u + 1, 4):
                assert H.has_edge(u, v)


# ===========================================================================
# Explicit fault mode — faulty_couplers
# ===========================================================================

class TestExplicitFaultyCouplers:
    def test_specific_edge_removed(self):
        G = make_path(5)
        H = simulate_faults(G, faulty_couplers=[(1, 2)])
        assert not H.has_edge(1, 2)

    def test_isolated_node_cleaned_up(self):
        # Remove both edges incident to node 1 in path 0-1-2-3.
        G = make_path(4)   # edges: 0-1, 1-2, 2-3
        H = simulate_faults(G, faulty_couplers=[(0, 1), (1, 2)])
        # Node 1 becomes isolated → should be removed
        assert 1 not in H.nodes()

    def test_non_isolated_nodes_kept(self):
        G = make_path(4)
        H = simulate_faults(G, faulty_couplers=[(1, 2)])
        # 0 still connected (via edge to 1), 3 via edge to 2 — none isolated
        assert 0 in H.nodes()
        assert 1 in H.nodes()
        assert 2 in H.nodes()
        assert 3 in H.nodes()

    def test_unknown_edge_raises(self):
        G = make_path(3)
        with pytest.raises(ValueError, match="faulty_couplers references edges not in topology"):
            simulate_faults(G, faulty_couplers=[(0, 2)])  # edge 0-2 doesn't exist

    def test_edge_referencing_unknown_node_raises(self):
        G = make_path(3)
        with pytest.raises(ValueError, match="faulty_couplers references nodes not in topology"):
            simulate_faults(G, faulty_couplers=[(0, 99)])

    def test_multiple_edges_removed(self):
        G = make_complete(4)
        H = simulate_faults(G, faulty_couplers=[(0, 1), (0, 2), (0, 3)])
        # Node 0 loses all edges → isolated → removed
        assert 0 not in H.nodes()

    def test_reverse_edge_tuple_accepted(self):
        # (2, 1) same as (1, 2) for undirected graph
        G = make_path(4)
        H = simulate_faults(G, faulty_couplers=[(2, 1)])
        assert not H.has_edge(1, 2)

    def test_combined_faulty_nodes_and_couplers_is_allowed(self):
        # faulty_nodes + faulty_couplers can be used together (only fault_rate
        # is mutually exclusive with explicit modes).
        G = make_path(5)
        H = simulate_faults(G, faulty_nodes=[0], faulty_couplers=[(2, 3)])
        assert 0 not in H.nodes()
        assert not H.has_edge(2, 3)


# ===========================================================================
# Validation / error paths
# ===========================================================================

class TestValidation:
    def test_negative_fault_rate_raises(self):
        G = make_path(5)
        with pytest.raises(ValueError, match="fault_rate must be in"):
            simulate_faults(G, fault_rate=-0.1)

    def test_fault_rate_above_one_raises(self):
        G = make_path(5)
        with pytest.raises(ValueError, match="fault_rate must be in"):
            simulate_faults(G, fault_rate=1.01)

    def test_fault_rate_with_faulty_nodes_raises(self):
        G = make_path(5)
        with pytest.raises(ValueError, match="Cannot combine"):
            simulate_faults(G, fault_rate=0.2, faulty_nodes=[1])

    def test_fault_rate_with_faulty_couplers_raises(self):
        G = make_path(5)
        with pytest.raises(ValueError, match="Cannot combine"):
            simulate_faults(G, fault_rate=0.2, faulty_couplers=[(0, 1)])

    def test_fault_rate_exactly_one_is_valid(self):
        G = make_path(5)
        H = simulate_faults(G, fault_rate=1.0, fault_seed=0)
        assert H.number_of_nodes() == 0

    def test_fault_rate_exactly_zero_is_valid(self):
        G = make_path(5)
        H = simulate_faults(G, fault_rate=0.0)
        assert H.number_of_nodes() == 5
