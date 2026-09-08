"""Regression cases for benchmark validation against the original problem."""

from types import SimpleNamespace

import networkx as nx
import pytest

from ember_qc.benchmark import benchmark_one
from ember_qc.registry import ALGORITHM_REGISTRY
from ember_qc.validation import validate_layer1, validate_layer2


def run_algorithm(monkeypatch, source, target, embed, **kwargs):
    monkeypatch.setitem(ALGORITHM_REGISTRY, 'validation-regression', SimpleNamespace(embed=embed))
    return benchmark_one(source, target, 'validation-regression', **kwargs)


def test_algorithm_supplied_target_cannot_invent_edges(monkeypatch):
    source = nx.complete_graph(3)
    target = nx.path_graph(3)
    result = run_algorithm(monkeypatch, source, target, lambda *args, **kwargs: {
        'embedding': {0: [0], 1: [1], 2: [2]},
        'chimera_graph': nx.complete_graph(3),
        'success': True,
    })
    assert result.status == 'INVALID_OUTPUT'
    assert result.success is result.is_valid is False
    assert result.avg_chain_length == result.total_qubits_used == 0
    assert 'edge_preservation' in result.error


@pytest.mark.parametrize('mutate_source', [False, True])
def test_algorithm_graph_mutation_cannot_change_reference_problem(monkeypatch, mutate_source):
    source = nx.complete_graph(3)
    target = nx.path_graph(3)

    def embed(working_source, working_target, **kwargs):
        if mutate_source:
            working_source.remove_edge(0, 2)
        else:
            working_target.add_edge(0, 2)
        return {'embedding': {0: [0], 1: [1], 2: [2]}}

    result = run_algorithm(monkeypatch, source, target, embed)
    assert result.status == 'INVALID_OUTPUT'
    assert source.has_edge(0, 2)
    assert not target.has_edge(0, 2)


def test_algorithm_cannot_delete_isolates_from_reference_source(monkeypatch):
    source = nx.Graph([(0, 1)])
    source.add_node(2)

    def embed(working_source, target, **kwargs):
        working_source.remove_node(2)
        return {'embedding': {0: [0], 1: [1]}}

    result = run_algorithm(monkeypatch, source, nx.path_graph(3), embed)
    assert result.status == 'INVALID_OUTPUT'
    assert 2 in source


@pytest.mark.parametrize('metadata', [
    {'success': False, 'status': 'FAILURE'},
    {'success': False, 'status': 'TIMEOUT', 'partial': True},
    {'success': True, 'status': 'SUCCESS'},
])
def test_success_is_inferred_from_valid_embedding(monkeypatch, metadata):
    result = run_algorithm(monkeypatch, nx.path_graph(2), nx.path_graph(3),
                           lambda *args, **kwargs: {
                               'embedding': {0: [0], 1: [1, 2]}, **metadata,
                           })
    assert result.status == 'SUCCESS'
    assert result.success is result.is_valid is True
    assert result.partial is False
    assert result.avg_chain_length == 1.5


@pytest.mark.parametrize('output', [
    {'embedding': {0: [0], 1: [99]}, 'success': True},
    {'embedding': {0: [0], 1: [1], 2: [2]}, 'success': True},
    {'embedding': {0: [0], 1: []}, 'success': True},
    {'embedding': {0: [0, 0], 1: [1]}, 'success': True},
    {'embedding': {0: [0], 1: [2]}, 'success': True},
    {'embedding': {0: [0], 1: [[1]]}, 'success': True},
    {'embedding': [{0: [0], 1: [1]}], 'success': True},
    {'embedding': {}, 'success': True},
    {'embedding': None, 'success': True},
    ['not', 'a', 'result'],
])
def test_invalid_ingestion_never_computes_quality(monkeypatch, output):
    def forbidden_metrics(*args, **kwargs):
        pytest.fail('invalid output reached metric computation')

    monkeypatch.setattr('ember_qc.benchmark.compute_embedding_metrics', forbidden_metrics)
    result = run_algorithm(monkeypatch, nx.path_graph(2), nx.path_graph(3),
                           lambda *args, **kwargs: output)
    assert result.status == 'INVALID_OUTPUT'
    assert result.success is result.is_valid is False
    assert result.chain_lengths == []
    assert result.avg_chain_length == result.total_qubits_used == 0


def test_declared_partial_failure_remains_failure(monkeypatch):
    result = run_algorithm(monkeypatch, nx.path_graph(2), nx.path_graph(3),
                           lambda *args, **kwargs: {
                               'embedding': {0: [0, 1], 1: [1, 2]},
                               'success': False, 'partial': True, 'status': 'TIMEOUT',
                           })
    assert result.status == 'TIMEOUT'
    assert result.success is False
    assert result.avg_chain_length == 0


@pytest.mark.parametrize('reported_status', ['SUCCESS', 'TIMEOUT'])
def test_valid_late_embedding_is_diagnostic_not_credited(monkeypatch, reported_status):
    clock = iter([10.0, 10.25])
    monkeypatch.setattr('ember_qc.benchmark.time.perf_counter', lambda: next(clock))

    def forbidden_metrics(*args, **kwargs):
        pytest.fail('late embedding reached quality computation')

    monkeypatch.setattr('ember_qc.benchmark.compute_embedding_metrics', forbidden_metrics)
    embedding = {0: [0], 1: [1, 2]}
    result = run_algorithm(monkeypatch, nx.path_graph(2), nx.path_graph(3),
                           lambda *args, **kwargs: {
                               'embedding': embedding,
                               'success': reported_status == 'SUCCESS',
                               'status': reported_status,
                               'time': 0.001,  # self-reported time cannot hide the overrun
                           }, timeout=0.1)
    assert result.status == 'TIMEOUT'
    assert result.success is False
    assert result.is_valid is True
    assert result.embedding == embedding
    assert result.wall_time == pytest.approx(0.25)
    assert result.avg_chain_length == result.total_qubits_used == 0
    assert result.chain_lengths == []
    assert 'exceeding' in result.error


def test_result_returned_at_deadline_remains_eligible(monkeypatch):
    clock = iter([10.0, 10.25])
    monkeypatch.setattr('ember_qc.benchmark.time.perf_counter', lambda: next(clock))
    result = run_algorithm(monkeypatch, nx.path_graph(2), nx.path_graph(3),
                           lambda *args, **kwargs: {'embedding': {0: [0], 1: [1, 2]}},
                           timeout=0.25)
    assert result.status == 'SUCCESS'
    assert result.avg_chain_length == 1.5


@pytest.mark.parametrize('output', [None, {'embedding': None}, {'embedding': [0, 1]}])
def test_late_missing_or_malformed_output_is_timeout(monkeypatch, output):
    clock = iter([10.0, 10.25])
    monkeypatch.setattr('ember_qc.benchmark.time.perf_counter', lambda: next(clock))
    result = run_algorithm(monkeypatch, nx.path_graph(2), nx.path_graph(3),
                           lambda *args, **kwargs: output, timeout=0.1)
    assert result.status == 'TIMEOUT'
    assert result.success is result.is_valid is False
    assert result.avg_chain_length == 0


def test_status_cannot_claim_success_without_embedding(monkeypatch):
    result = run_algorithm(monkeypatch, nx.path_graph(2), nx.path_graph(3),
                           lambda *args, **kwargs: {'embedding': {}, 'status': 'SUCCESS'})
    assert result.status == 'INVALID_OUTPUT'
    assert result.success is result.is_valid is False


def test_empty_source_embedding_is_valid_at_ingestion(monkeypatch):
    result = run_algorithm(monkeypatch, nx.Graph(), nx.Graph(),
                           lambda *args, **kwargs: {'embedding': {}, 'success': False})
    assert result.status == 'SUCCESS'
    assert result.success is result.is_valid is True
    assert result.embedding == {}
    assert result.problem_nodes == 0
    assert result.avg_chain_length == result.max_chain_length == 0


def test_isolated_target_vertices_remain_available(monkeypatch):
    source = nx.empty_graph(2)
    target = nx.empty_graph(3)
    result = run_algorithm(monkeypatch, source, target,
                           lambda *args, **kwargs: {'embedding': {0: [0], 1: [2]}})
    assert result.success is True
    assert result.avg_chain_length == 1


@pytest.mark.parametrize('embedding', [None, [], {0: []}, {0: [99]}, {0: [0, 0]}, {0: [[0]]}])
def test_structural_validator_is_safe_without_layer2(embedding):
    assert not validate_layer1(embedding, nx.empty_graph(1), nx.empty_graph(1)).passed


def test_structural_validator_empty_source_policy():
    assert validate_layer1({}, nx.Graph(), nx.Graph()).passed
    assert not validate_layer1(None, nx.Graph(), nx.Graph()).passed
    assert not validate_layer1({0: [0]}, nx.Graph(), nx.empty_graph(1)).passed


def test_type_validator_returns_failure_for_malformed_outer_containers():
    source = target = nx.path_graph(2)
    assert not validate_layer2([], source, target).passed
    assert not validate_layer2({'embedding': [0, 1]}, source, target).passed
