"""Corpus provenance must survive staging without leaking family data to solvers."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path

import networkx as nx
import pytest

SPEC = importlib.util.spec_from_file_location(
    'codex_pilot_corpus', Path(__file__).parents[1] / 'scripts/codex/pilot.py')
pilot = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(pilot)


def make_selection(tmp_path, monkeypatch):
    monkeypatch.setattr(pilot, 'ROOT', tmp_path)
    graph_dir = tmp_path / 'corpus/graphs'
    graph_dir.mkdir(parents=True)
    record = pilot.graph_record(nx.path_graph(3))
    pilot.write_json(graph_dir / 'ember_1.json', record)
    original = {'selection_id': 'original', 'records': [], 'input_errors': ['missing']}
    original_path = graph_dir.parent / 'selection.json'
    pilot.write_json(original_path, original)
    members = [{'family': 'family_a', 'graph_id': 1}, {'family': 'family_b', 'graph_id': 2}]
    identity = {
        'original_selection_id': original['selection_id'],
        'original_selection_file_sha256': hashlib.sha256(original_path.read_bytes()).hexdigest(),
        'family_selections': copy.deepcopy(members), 'missing_families': ['family_c'],
        'solver_inputs': [{'graph_key': 'ember_1', 'graph_record_path': 'corpus/graphs/ember_1.json',
                          'nodes': 3, 'edges': 2, 'source_hash': pilot.digest(record),
                          'normalized_topology_hash': pilot.digest({
                              'nodes': record['nodes'], 'edges': record['edges']}),
                          'aggregate_structure_weight': 1, 'family_memberships': members}]}
    selection = {'identity': identity, 'selection_id': pilot.digest(identity)}
    path = tmp_path / 'selection.json'
    pilot.write_json(path, selection)
    return path, selection, original, record


def test_loader_preserves_shared_memberships_and_missing_families(tmp_path, monkeypatch):
    path, expected, original, record = make_selection(tmp_path, monkeypatch)
    selection, parent, graphs = pilot.load_readiness_selection(path)
    assert selection == expected and parent == original
    assert graphs == {'ember_1': record}
    assert len(selection['identity']['solver_inputs'][0]['family_memberships']) == 2
    assert selection['identity']['missing_families'] == ['family_c']
    assert graphs['ember_1']['metadata'] == {}


@pytest.mark.parametrize('defect', ['selection_hash', 'graph_hash', 'metadata', 'topology_duplicate',
                                  'membership', 'original_hash', 'unsafe_key'])
def test_loader_rejects_changed_or_ambiguous_input(tmp_path, monkeypatch, defect):
    path, selection, _, record = make_selection(tmp_path, monkeypatch)
    identity = selection['identity']
    entry = identity['solver_inputs'][0]
    if defect == 'selection_hash':
        selection['selection_id'] = 'changed'
    elif defect in ('graph_hash', 'metadata'):
        record['metadata'] = {'family': 'leaked'}
        pilot.write_json(tmp_path / entry['graph_record_path'], record)
        if defect == 'metadata':
            entry['source_hash'] = pilot.digest(record)
    elif defect == 'topology_duplicate':
        duplicate = copy.deepcopy(entry)
        duplicate['graph_key'] = 'ember_2'
        identity['solver_inputs'].append(duplicate)
    elif defect == 'membership':
        identity['family_selections'][0]['family'] = 'changed'
    elif defect == 'original_hash':
        identity['original_selection_file_sha256'] = 'changed'
    else:
        entry['graph_key'] = '../changed'
    if defect != 'selection_hash':
        selection['selection_id'] = pilot.digest(identity)
    pilot.write_json(path, selection)
    with pytest.raises(ValueError):
        pilot.load_readiness_selection(path)


def test_shipped_provenance_binds_tasks_and_sidecars(tmp_path, monkeypatch):
    _, selection, original, record = make_selection(tmp_path, monkeypatch)
    run = tmp_path / 'run'
    (run / 'graphs').mkdir(parents=True)
    (run / 'tasks').mkdir()
    pilot.write_json(run / 'graphs/ember_1.json', record)
    pilot.write_json(run / 'corpus_selection.json', selection)
    pilot.write_json(run / 'original_corpus_selection.json', original)
    task = {'graph': 'ember_1', 'source_hash': pilot.digest(record)}
    pilot.write_json(run / 'tasks/task.json', task)
    manifest = {'tasks': ['task'], 'corpus': {
        'selection_id': selection['selection_id'], 'selection_digest': pilot.digest(selection),
        'original_selection_digest': pilot.digest(original), 'included_graphs': ['ember_1']}}
    assert pilot.check_corpus_provenance(run, manifest) == selection
    task['source_hash'] = 'changed'
    pilot.write_json(run / 'tasks/task.json', task)
    with pytest.raises(ValueError, match='task'):
        pilot.check_corpus_provenance(run, manifest)
    pilot.write_json(run / 'tasks/task.json', {'graph': 'ember_1', 'source_hash': pilot.digest(record)})
    original['input_errors'] = []
    pilot.write_json(run / 'original_corpus_selection.json', original)
    with pytest.raises(ValueError, match='provenance'):
        pilot.check_corpus_provenance(run, manifest)
