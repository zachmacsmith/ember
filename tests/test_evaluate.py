"""
tests/test_evaluate.py
======================
Tests for the single-call evaluation harness ember_qc.evaluate().
"""
import networkx as nx
import pytest

from ember_qc import evaluate


@pytest.fixture
def path4():
    return nx.path_graph(4)  # 0-1-2-3


class TestEvaluate:
    def test_empty_embedding_is_invalid_and_zeroed(self, path4):
        source = nx.path_graph(2)
        report = evaluate({}, source, path4)
        assert report['valid'] is False
        assert report['total_qubits_used'] == 0
        assert report['avg_chain_length'] == 0.0
        assert report['num_chains'] == 0

    def test_none_embedding(self, path4):
        report = evaluate(None, nx.path_graph(2), path4)
        assert report['valid'] is False

    def test_known_embedding_metrics(self, path4):
        # source edge 0-1; embed 0->[0], 1->[1,2]; chain lengths {1,2}
        source = nx.path_graph(2)
        embedding = {0: [0], 1: [1, 2]}
        report = evaluate(embedding, source, path4, wall_time=0.5)

        assert report['valid'] is True
        assert report['num_chains'] == 2
        assert report['total_qubits_used'] == 3
        assert report['avg_chain_length'] == pytest.approx(1.5)
        assert report['std_chain_length'] == pytest.approx(0.5)
        assert report['max_chain_length'] == 2
        assert report['min_chain_length'] == 1
        assert report['chain_length_cv'] == pytest.approx(1.0 / 3.0)
        assert report['total_couplers_used'] == 1   # qubits 1-2 adjacent
        assert report['wall_time'] == 0.5

    def test_invalid_embedding_flagged(self, path4):
        # Overlap on qubit 1 cannot produce a quality observation.
        source = nx.path_graph(2)
        report = evaluate({0: [0, 1], 1: [1, 2]}, source, path4)
        assert report['valid'] is False
        assert report['total_qubits_used'] == 0
        assert report['avg_chain_length'] == 0.0
        assert report['num_chains'] == 0

    @pytest.mark.parametrize('embedding, valid', [
        ({0: [0], 1: [1, 2]}, True),
        ({0: [0, 1], 1: [1, 2]}, False),
    ])
    def test_validate_false_cannot_bypass_validation(self, path4, embedding, valid):
        with pytest.warns(DeprecationWarning, match='always validated'):
            report = evaluate(embedding, nx.path_graph(2), path4, validate=False)
        assert report['valid'] is valid
        if not valid:
            assert report['total_qubits_used'] == 0

    @pytest.mark.parametrize('embedding', [
        {0: [0], 1: [1], 2: [2]},  # extra source vertex
        {0: [0]},                  # missing source vertex
        {0: [0], 1: []},          # empty chain
        {0: [0], 1: [99]},        # foreign singleton
        {0: [0], 1: [1, 99]},     # foreign vertex in a longer chain
        {0: [0, 2], 1: [1]},      # disconnected chain
        {0: [0, 0], 1: [1]},      # duplicate within a chain
        {0: [0], 1: [2]},         # unrealized logical edge
        {0: [0], 1: None},        # malformed chain
        {0: [0], 1: [[1]]},       # unhashable qubit
        [{0: [0], 1: [1]}],       # malformed outer container
    ])
    def test_invalid_outputs_do_not_reach_metrics(self, path4, embedding, monkeypatch):
        def forbidden_metrics(*args, **kwargs):
            pytest.fail('invalid embedding reached metric computation')

        monkeypatch.setattr('ember_qc.benchmark.compute_embedding_metrics', forbidden_metrics)
        report = evaluate(embedding, nx.path_graph(2), path4)
        assert report['valid'] is False
        assert report['total_qubits_used'] == 0
        assert report['avg_chain_length'] == 0.0

    def test_isolated_source_vertices_count_in_acl(self, path4):
        source = nx.Graph([(0, 1)])
        source.add_node(2)
        embedding = {0: [0], 1: [1, 2], 2: [3]}
        report = evaluate(embedding, source, path4)
        assert report['valid'] is True
        assert report['avg_chain_length'] == pytest.approx(4 / 3)
        assert not evaluate({0: [0], 1: [1, 2]}, source, path4)['valid']

    def test_empty_source_has_explicit_zero_acl_convention(self, path4):
        report = evaluate({}, nx.Graph(), path4)
        assert report['valid'] is True
        assert report['num_source_nodes'] == report['num_chains'] == 0
        assert report['avg_chain_length'] == 0.0
        assert not evaluate(None, nx.Graph(), path4)['valid']

    def test_structural_evaluation_supports_hashable_labels(self):
        source = nx.Graph([('left', 'right')])
        target = nx.path_graph([(0, 0), (0, 1), (0, 2)])
        embedding = {'left': {(0, 0)}, 'right': ((0, 1), (0, 2))}
        report = evaluate(embedding, source, target)
        assert report['valid'] is True
        assert report['avg_chain_length'] == 1.5
