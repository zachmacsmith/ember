"""Sudoku source semantics and immutable provenance; no embeddings or downloads."""
from copy import deepcopy
from collections import Counter
import importlib.util
import json
from pathlib import Path

import networkx as nx
import pytest


ROOT = Path(__file__).parents[1]
SPEC = importlib.util.spec_from_file_location('codex_sudoku_supplement',
                                            ROOT / 'scripts/codex/sudoku_supplement.py')
supplement = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(supplement)


@pytest.fixture
def inputs(tmp_path):
    manifest = tmp_path / 'inherited.json'
    original = {'graphs': [{'id': 37900, 'name': 'sudoku_n9', 'type': 'sudoku',
                            'n': 6561, 'e': 734832, 'p': {'n': 9}},
                           {'id': 37901, 'name': 'sudoku_n16', 'type': 'sudoku',
                            'n': 65536, 'e': 24084480, 'p': {'n': 16}}]}
    manifest.write_bytes(supplement.json_bytes(original))
    protocol = tmp_path / 'protocol.md'
    protocol.write_text('q2/q3 development; q4/q5 reserved.\n')
    return manifest, protocol


def freeze(tmp_path, inputs):
    manifest, protocol = inputs
    destination = tmp_path / 'frozen'
    supplement.freeze_supplement(destination, manifest_path=manifest, protocol_path=protocol)
    return destination


@pytest.mark.parametrize('q,n,m,degree,row_edges,box_extra',
                         [(2, 16, 56, 7, 24, 8), (3, 81, 810, 20, 324, 162)])
def test_actual_constraints_match_networkx_and_analytic_counts(q, n, m, degree, row_edges, box_extra):
    record = supplement.build_graph_record(q)
    graph = nx.sudoku_graph(q)
    assert record['nodes'] == list(range(n))
    assert record['edges'] == sorted([min(a, b), max(a, b)] for a, b in graph.edges())
    audit = supplement.verify_graph_record(record, q)
    assert (audit['vertices'], audit['edges'], audit['regular_degree']) == (n, m, degree)
    assert audit['constraint_pairs'] == {'same_row': row_edges, 'same_column': row_edges,
                                        'additional_same_box': box_extra}
    assert audit['all_pairs_checked'] == n * (n - 1) // 2
    assert audit['necessary_bounds_passed'] is True
    assert audit['embedding_feasibility'] == 'unproved'
    assert record['metadata'] == {}
    assert all(attrs == {} for _, attrs in record['node_attributes'])
    assert all(attrs == {} for _, _, attrs in record['edge_attributes'])


@pytest.mark.parametrize('q', [0, 1, 4, 5, 9, 16, 2.0, True, '3'])
def test_unapproved_or_ambiguous_orders_are_rejected(q):
    with pytest.raises(ValueError, match='Only development'):
        supplement.build_graph_record(q)


def test_semantic_checker_rejects_same_count_wrong_graph():
    record = supplement.build_graph_record(2)
    original_count = len(record['edges'])
    original_degrees = Counter(v for edge in record['edges'] for v in edge)
    record['edges'].remove([0, 1])  # Required row contact.
    record['edges'].remove([6, 7])  # Another required row contact.
    record['edges'].append([0, 6])  # Different row, column, and box.
    record['edges'].append([1, 7])  # Degree-preserving two-edge replacement.
    record['edges'].sort()
    record['edge_attributes'] = [[a, b, {}] for a, b in record['edges']]
    assert len(record['edges']) == original_count
    assert Counter(v for edge in record['edges'] for v in edge) == original_degrees
    with pytest.raises(ValueError, match='Cell constraint'):
        supplement.verify_graph_record(record, 2)


@pytest.mark.parametrize('defect', ['graph_hint', 'node_hint', 'edge_hint', 'duplicate_edge',
                                   'loop', 'foreign_vertex', 'boolean_vertex', 'boolean_attribute_label',
                                   'extra_key'])
def test_sanitized_record_rejects_hints_and_invalid_structure(defect):
    record = supplement.build_graph_record(2)
    if defect == 'graph_hint':
        record['metadata']['family'] = 'sudoku'
    elif defect == 'node_hint':
        record['node_attributes'][0][1]['row'] = 0
    elif defect == 'edge_hint':
        record['edge_attributes'][0][2]['constraint'] = 'row'
    elif defect == 'duplicate_edge':
        record['edges'].append(record['edges'][0])
    elif defect == 'loop':
        record['edges'][0] = [0, 0]
    elif defect == 'foreign_vertex':
        record['edges'][0] = [0, 999]
    elif defect == 'boolean_vertex':
        record['nodes'][1] = True
    elif defect == 'boolean_attribute_label':
        record['node_attributes'][1][0] = True
    elif defect == 'extra_key':
        record['box_order'] = 2
    with pytest.raises(ValueError):
        supplement.verify_graph_record(record, 2)


def test_freeze_roundtrip_hashes_original_preservation_and_pilot_compatibility(tmp_path, inputs):
    manifest_path, protocol_path = inputs
    original_manifest = manifest_path.read_bytes()
    original_protocol = protocol_path.read_bytes()
    directory = freeze(tmp_path, inputs)
    loaded = supplement.load_supplement(directory)
    assert [item['id'] for item in loaded] == [1000002, 1000003]
    manifest = json.loads((directory / 'manifest.json').read_bytes())
    assert manifest['reserved_ungenerated_box_orders'] == [4, 5]
    assert manifest['original_manifest_sha256'] == supplement.byte_hash(original_manifest)
    assert set(manifest['files']) == {
        'graphs/1000002.json', 'graphs/1000003.json',
        'provenance/1000002.json', 'provenance/1000003.json',
        'provenance/original_sudoku_entries.json',
        'source/sudoku_supplement.py', 'source/generalization_protocol.md'}
    assert manifest_path.read_bytes() == original_manifest
    assert protocol_path.read_bytes() == original_protocol
    inherited = json.loads((directory / 'provenance/original_sudoku_entries.json').read_bytes())
    assert inherited == json.loads(original_manifest)['graphs']
    pilot_spec = importlib.util.spec_from_file_location('codex_pilot_sudoku', ROOT / 'scripts/codex/pilot.py')
    pilot = importlib.util.module_from_spec(pilot_spec)
    pilot_spec.loader.exec_module(pilot)
    for item in loaded:
        record, provenance = item['record'], item['provenance']
        assert pilot.graph_record(pilot.graph_from_record(record)) == record
        assert pilot.digest(record) == provenance['source_hash']
        assert provenance['box_order'] ** 2 == provenance['board_side']
        assert provenance['split'] == 'development'
        assert provenance['generator_version'] == supplement.VERSION
        assert provenance['structure_novelty'].startswith('not_audited')


def test_refuses_existing_and_incomplete_destinations_without_writes(tmp_path, inputs):
    directory = freeze(tmp_path, inputs)
    before = {p.relative_to(directory): p.read_bytes() for p in directory.rglob('*') if p.is_file()}
    with pytest.raises(FileExistsError, match='Immutable'):
        supplement.freeze_supplement(directory, manifest_path=inputs[0], protocol_path=inputs[1])
    assert before == {p.relative_to(directory): p.read_bytes() for p in directory.rglob('*') if p.is_file()}
    partial = tmp_path / 'partial'
    partial.mkdir()
    with pytest.raises(FileExistsError, match='Immutable'):
        supplement.freeze_supplement(partial, manifest_path=inputs[0], protocol_path=inputs[1])
    with pytest.raises(ValueError, match='incomplete'):
        supplement.load_supplement(partial)


def test_collision_is_rejected_before_destination_creation(tmp_path, inputs):
    manifest_path, protocol_path = inputs
    original = json.loads(manifest_path.read_bytes())
    original['graphs'].append({'id': 1000002})
    manifest_path.write_bytes(supplement.json_bytes(original))
    destination = tmp_path / 'collision'
    with pytest.raises(ValueError, match='collides'):
        supplement.freeze_supplement(destination, manifest_path=manifest_path, protocol_path=protocol_path)
    assert not destination.exists()


@pytest.mark.parametrize('defect', ['graph_bytes', 'source_bytes', 'protocol_bytes', 'provenance_bytes',
                                   'manifest_identity', 'missing', 'extra', 'symlink'])
def test_load_rejects_corrupt_or_expanded_frozen_bundle(tmp_path, inputs, defect):
    directory = freeze(tmp_path, inputs)
    names = {'graph_bytes': 'graphs/1000002.json', 'source_bytes': 'source/sudoku_supplement.py',
             'protocol_bytes': 'source/generalization_protocol.md', 'provenance_bytes': 'provenance/1000002.json',
             'manifest_identity': 'manifest.json'}
    if defect in names:
        path = directory / names[defect]
        if defect == 'manifest_identity':
            record = json.loads(path.read_bytes())
            record['supplement_id'] = '0' * 64
            path.write_bytes(supplement.json_bytes(record))
        else:
            path.write_bytes(path.read_bytes() + b' ')
    elif defect == 'missing':
        (directory / 'graphs/1000002.json').unlink()
    elif defect == 'extra':
        (directory / 'graphs/reserved-q4.json').write_text('{}')
    elif defect == 'symlink':
        path = directory / 'graphs/1000002.json'
        raw = path.read_bytes()
        path.unlink()
        target = tmp_path / 'outside.json'
        target.write_bytes(raw)
        path.symlink_to(target)
    with pytest.raises(ValueError):
        supplement.load_supplement(directory)


def test_semantics_checked_even_after_consistent_file_rehashing(tmp_path, inputs):
    directory = freeze(tmp_path, inputs)
    graph_path = directory / 'graphs/1000002.json'
    record = json.loads(graph_path.read_bytes())
    record['edges'].remove([0, 1])
    record['edges'].append([0, 6])
    record['edges'].sort()
    record['edge_attributes'] = [[a, b, {}] for a, b in record['edges']]
    graph_path.write_bytes(supplement.json_bytes(record))
    manifest_path = directory / 'manifest.json'
    manifest = json.loads(manifest_path.read_bytes())
    manifest['files']['graphs/1000002.json'] = supplement.byte_hash(graph_path.read_bytes())
    manifest.pop('supplement_id')
    manifest['supplement_id'] = supplement.digest(manifest)
    manifest_path.write_bytes(supplement.json_bytes(manifest))
    with pytest.raises(ValueError, match='Cell constraint'):
        supplement.load_supplement(directory)


def test_repeat_generation_and_loading_do_not_share_mutable_graphs(tmp_path, inputs):
    first = supplement.build_graph_record(2)
    original = deepcopy(first)
    first['edges'].clear()
    assert supplement.build_graph_record(2) == original
    directory = freeze(tmp_path, inputs)
    loaded = supplement.load_supplement(directory)
    loaded[0]['record']['edges'].clear()
    assert supplement.load_supplement(directory)[0]['record'] == original
