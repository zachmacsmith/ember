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
        # overlap on qubit 1 → not a valid embedding, but metrics still computed
        source = nx.path_graph(2)
        report = evaluate({0: [0, 1], 1: [1, 2]}, source, path4)
        assert report['valid'] is False
        assert report['total_qubits_used'] == 3  # union of qubits

    def test_validate_false_skips_validation(self, path4):
        report = evaluate({0: [0], 1: [1, 2]}, nx.path_graph(2), path4, validate=False)
        assert report['valid'] is None  # not checked
