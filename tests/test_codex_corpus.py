"""Corpus selection invariants; tests never download graphs or run algorithms."""
import hashlib
import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).parents[1]
SPEC = importlib.util.spec_from_file_location('codex_corpus', ROOT / 'scripts/codex/corpus.py')
corpus = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(corpus)


def fixture_graph(gid=1, family='family_a', labels=(10, 20, 30), edges=((10, 20),), edge_field='links'):
    data = {'id': gid, 'name': 'fixture_' + str(gid), 'category': family,
            'num_nodes': len(labels), 'num_edges': len(edges),
            'graph': {'directed': False, 'multigraph': False, 'graph': {'family_hint': family},
                      'nodes': [{'id': label, 'coordinate_hint': index} for index, label in enumerate(labels)],
                      edge_field: [{'source': a, 'target': b, 'weight': -1} for a, b in edges]}}
    raw = json.dumps(data).encode()
    entry = {'id': gid, 'name': data['name'], 'family': family,
             'nodes': len(labels), 'edges': len(edges),
             'file_hash_prefix': hashlib.sha256(raw).hexdigest()[:16],
             'parameters': {}, 'url': '', 'size_bytes': len(raw)}
    return data, raw, entry


def update_raw(data, entry):
    raw = json.dumps(data).encode()
    entry = dict(entry, file_hash_prefix=hashlib.sha256(raw).hexdigest()[:16])
    return raw, entry


def manifest_entry(entry):
    return {'id': entry['id'], 'name': entry['name'], 'type': entry['family'],
            'n': entry['nodes'], 'e': entry['edges'], 'h': entry['file_hash_prefix'],
            'p': entry['parameters'], 'sz': entry['size_bytes']}


def test_selection_order_independence_bounds_and_empty_families():
    entries = [fixture_graph(gid)[2] for gid in range(1, 8)]
    entries += [dict(fixture_graph(100, 'oversized')[2], nodes=4801),
                dict(fixture_graph(101, 'too_many_edges')[2], nodes=1000, edges=45865)]
    first = corpus.plan_selection(entries)
    second = corpus.plan_selection(list(reversed(entries)))
    assert first['requested_ids'] == second['requested_ids']
    assert first['cells'] == second['cells']
    assert len(first['requested_ids']) == 2
    assert set(first['families']) == {'family_a', 'oversized', 'too_many_edges'}
    assert len(first['cells']) == 3 * len(corpus.BINS)
    assert all(not cell['requested_ids'] for cell in first['cells'] if cell['family'] != 'family_a')
    assert corpus.count_exclusions(4800, 45864) == []
    assert corpus.size_bin(16) == '1-16'
    assert corpus.size_bin(17) == '17-64'
    assert corpus.size_bin(4800) == '2049-4800'
    with pytest.raises(ValueError):
        corpus.plan_selection(entries, per_cell=3)


def test_structural_hash_ignores_storage_order_attributes_and_simple_relabel():
    data, raw, entry = fixture_graph()
    record, audit = corpus.decode_graph(raw, entry)
    data['graph']['nodes'].reverse()
    data['graph']['links'][0].update(source=20, target=10, weight=999)
    data['graph']['graph']['family_hint'] = 'changed'
    reordered, reordered_entry = update_raw(data, entry)
    same_record, same_audit = corpus.decode_graph(reordered, reordered_entry)
    assert record == same_record
    assert audit['source_hash'] == same_audit['source_hash']
    assert audit['raw_sha256'] != same_audit['raw_sha256']
    assert audit['node_order_hash'] != same_audit['node_order_hash']
    assert audit['edge_order_hash'] != same_audit['edge_order_hash']
    _, relabeled, relabeled_entry = fixture_graph(labels=(0, 1, 2), edges=((0, 1),), edge_field='edges')
    changed, changed_audit = corpus.decode_graph(relabeled, relabeled_entry)
    assert record == changed
    assert audit['normalized_topology_hash'] == changed_audit['normalized_topology_hash']
    assert audit['labeled_topology_hash'] != changed_audit['labeled_topology_hash']
    assert audit['actual_nodes'] == 3  # isolate retained
    assert audit['removed_node_attribute_count'] == 3
    assert audit['removed_edge_attribute_count'] == 1
    assert record['metadata'] == {}


@pytest.mark.parametrize('defect', ['bad_hash', 'wrong_id', 'wrong_name', 'wrong_family', 'counts',
                                   'duplicate_node', 'foreign_endpoint', 'self_loop',
                                   'duplicate_edge', 'directed', 'both_edge_fields'])
def test_rejects_corrupt_or_ambiguous_sources(defect):
    data, raw, entry = fixture_graph()
    if defect == 'bad_hash':
        entry['file_hash_prefix'] = '0' * 16
    else:
        if defect == 'wrong_id':
            data['id'] = 999
        elif defect == 'wrong_name':
            data['name'] = 'other'
        elif defect == 'wrong_family':
            data['category'] = 'other'
        elif defect == 'counts':
            entry['nodes'] += 1
        elif defect == 'duplicate_node':
            data['graph']['nodes'].append(data['graph']['nodes'][0])
        elif defect == 'foreign_endpoint':
            data['graph']['links'][0]['target'] = 999
        elif defect == 'self_loop':
            data['graph']['links'][0]['target'] = 10
        elif defect == 'duplicate_edge':
            data['graph']['links'].append({'source': 20, 'target': 10})
        elif defect == 'directed':
            data['graph']['directed'] = True
        elif defect == 'both_edge_fields':
            data['graph']['edges'] = data['graph']['links']
        raw, entry = update_raw(data, entry)
    with pytest.raises(ValueError):
        corpus.decode_graph(raw, entry)


def test_duplicate_groups_preserve_within_and_cross_family_membership():
    rows = []
    for gid, family in ((1, 'a'), (2, 'a'), (3, 'b')):
        _, raw, entry = fixture_graph(gid, family)
        _, audit = corpus.decode_graph(raw, entry)
        rows.append(dict(entry, **audit, status='READY'))
    groups = corpus.duplicate_groups(rows)
    assert len(groups) == 1
    assert groups[0]['within_family'] and groups[0]['cross_family']
    assert groups[0]['graph_ids'] == [1, 2, 3]


def test_full_local_selection_adapter_and_identity(tmp_path):
    inputs = tmp_path / 'inputs'
    inputs.mkdir()
    items = []
    for gid in (1, 2):
        _, raw, entry = fixture_graph(gid)
        (inputs / f'{gid}_{entry["name"]}.json').write_bytes(raw)
        items.append(manifest_entry(entry))
    manifest = tmp_path / 'manifest.json'
    corpus.save(manifest, {'graphs': items, 'count': len(items)})
    out = tmp_path / 'selection'
    result = corpus.select(out, manifest, search_dirs=[inputs])
    assert len(result['records']) == 2
    assert len(result['duplicate_groups']) == 1
    adapter = list(corpus.load_selection(out / 'selection.json'))
    assert len(adapter) == 2
    pilot_spec = importlib.util.spec_from_file_location('codex_pilot', ROOT / 'scripts/codex/pilot.py')
    pilot = importlib.util.module_from_spec(pilot_spec)
    pilot_spec.loader.exec_module(pilot)
    for gid, key, graph, metadata in adapter:
        assert corpus.digest(pilot.graph_record(graph)) == metadata['source_hash']
        assert list(graph) == [0, 1, 2]
        assert not graph.graph
    changed = json.loads((out / 'selection.json').read_text())
    changed['records'][0]['family'] = 'invented'
    corpus.save(out / 'selection.json', changed)
    with pytest.raises(ValueError, match='metadata'):
        list(corpus.load_selection(out / 'selection.json'))
    with pytest.raises(ValueError, match='immutable'):
        corpus.select(out, manifest, search_dirs=[inputs])


def test_input_errors_are_not_substituted_or_hidden(tmp_path):
    _, _, entry = fixture_graph()
    manifest = tmp_path / 'manifest.json'
    corpus.save(manifest, {'graphs': [manifest_entry(entry)]})
    result = corpus.select(tmp_path / 'selection', manifest)
    assert result['records'][0]['status'] == 'INPUT_ERROR'
    assert result['families'][0]['requested'] == result['families'][0]['input_errors'] == 1
    assert result['families'][0]['ready'] == 0
    with pytest.raises(ValueError, match='unresolved'):
        list(corpus.load_selection(tmp_path / 'selection/selection.json'))
    partial = corpus.load_selection(tmp_path / 'selection/selection.json', allow_missing=True)
    assert list(partial) == []
    assert len(partial.missing_inputs) == 1
    assert partial.selection['families'][0]['requested'] == 1
    assert partial.selection['records'] == result['records']


def test_actual_zephyr12_counts_match_declared_necessary_bounds():
    import dwave_networkx as dnx
    target = dnx.zephyr_graph(12, 4)
    assert (len(target), target.number_of_edges()) == (corpus.TARGET_N, corpus.TARGET_M)
