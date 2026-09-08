"""Select actual Ember development graphs without using embedding outcomes.

The complete inherited corpus is development data. Necessary count bounds do not
certify embeddability. Each family/size cell has fixed, hash-ranked requested IDs;
unavailable, invalid, or duplicate inputs are recorded, never silently replaced.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import re
import time
from urllib.parse import quote
from urllib.request import urlopen


ROOT = Path(__file__).absolute().parents[2]
MANIFEST = ROOT / 'packages/ember-qc/src/ember_qc/graphs/manifest.json'
BUNDLED = MANIFEST.parent / 'library'
BINS = ((1, 16), (17, 64), (65, 128), (129, 256), (257, 512),
        (513, 1024), (1025, 2048), (2049, 4800))
SEED = 'ember-codex-development-v1'
TARGET_N, TARGET_M = 4800, 45864


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, sort_keys=True, indent=2) + '\n')


def size_bin(nodes):
    return next((f'{low}-{high}' for low, high in BINS if low <= nodes <= high), None)


def count_exclusions(nodes, edges):
    reasons = []
    if nodes == 0:
        reasons.append('empty_source_outside_acl_screen')
    if nodes > TARGET_N:
        reasons.append('source_vertices_exceed_target')
    if edges > TARGET_M:
        reasons.append('source_edges_exceed_target')
    return reasons


def entries_from_manifest(manifest):
    entries = []
    seen = set()
    for item in manifest['graphs']:
        entry = {'id': item['id'], 'name': item['name'],
                 'family': item.get('type', item.get('category')),
                 'nodes': item.get('n', item.get('nodes', item.get('num_nodes'))),
                 'edges': item.get('e', item.get('edges', item.get('num_edges'))),
                 'file_hash_prefix': item.get('h', item.get('hash')),
                 'parameters': item.get('p', item.get('parameters', {})),
                 'url': item.get('url', ''), 'size_bytes': item.get('sz', item.get('size_bytes'))}
        if entry['id'] in seen or type(entry['id']) is not int:
            raise ValueError('Duplicate or invalid graph ID')
        seen.add(entry['id'])
        for field in ('nodes', 'edges'):
            if type(entry[field]) is not int or entry[field] < 0:
                raise ValueError(f'Invalid {field}: graph {entry["id"]}')
        if not isinstance(entry['family'], str) or not entry['family']:
            raise ValueError('Missing family')
        if any('/' in entry[k] or '\\' in entry[k] or entry[k] in ('.', '..') for k in ('name', 'family')):
            raise ValueError('Unsafe manifest name or family')
        if not re.fullmatch(r'[0-9a-f]{16,64}', entry['file_hash_prefix'] or ''):
            raise ValueError('Missing or malformed manifest file hash')
        entries.append(entry)
    if manifest.get('count', len(entries)) != len(entries):
        raise ValueError('Manifest count mismatch')
    return sorted(entries, key=lambda entry: entry['id'])


def plan_selection(entries, per_cell=2, seed=SEED):
    if per_cell not in (1, 2):
        raise ValueError('Initial screen requires one or two IDs per cell')
    families = sorted({entry['family'] for entry in entries})
    grouped = defaultdict(list)
    ledger = []
    for entry in entries:
        excluded = count_exclusions(entry['nodes'], entry['edges'])
        bucket = size_bin(entry['nodes'])
        rank = digest({'seed': seed, 'family': entry['family'], 'size_bin': bucket, 'id': entry['id']})
        record = dict(entry, size_bin=bucket, manifest_bound_exclusions=excluded,
                      rank=rank, requested=False)
        ledger.append(record)
        if not excluded:
            grouped[(entry['family'], bucket)].append(record)
    cells = []
    for family in families:
        for low, high in BINS:
            bucket = f'{low}-{high}'
            ordered = sorted(grouped[(family, bucket)], key=lambda item: (item['rank'], item['id']))
            for entry in ordered[:per_cell]:
                entry['requested'] = True
            cells.append({'family': family, 'size_bin': bucket, 'manifest_eligible': len(ordered),
                          'requested_ids': [entry['id'] for entry in ordered[:per_cell]]})
    return {'families': families, 'cells': cells, 'ledger': ledger,
            'requested_ids': sorted(entry['id'] for entry in ledger if entry['requested'])}


def label_key(label):
    # Typed JSON labels remain in provenance; algorithms see deterministic integer
    # labels. This is not graph-isomorphism canonicalization.
    if type(label) is int:
        return (0, label)
    if isinstance(label, str):
        return (1, label)
    if isinstance(label, list):
        for value in label:
            label_key(value)
        return (2, json.dumps(label, sort_keys=True, separators=(',', ':')))
    raise ValueError(f'Unsupported node label type: {type(label).__name__}')


def decode_graph(raw, entry):
    """Validate raw node-link input and strip nonstructural solver attributes."""
    file_hash = hashlib.sha256(raw).hexdigest()
    if not file_hash.startswith(entry['file_hash_prefix']):
        raise ValueError('File hash differs from manifest')
    data = json.loads(raw)
    if data.get('id') != entry['id'] or data.get('name') != entry['name']:
        raise ValueError('Raw graph ID/name differs from requested manifest entry')
    if data.get('category', entry['family']) != entry['family']:
        raise ValueError('Raw graph family differs from manifest')
    graph = data['graph']
    if graph.get('directed') is not False or graph.get('multigraph') is not False:
        raise ValueError('Expected a simple undirected graph')
    if ('edges' in graph) == ('links' in graph):
        raise ValueError('Expected exactly one node-link edge field')
    raw_nodes = graph['nodes']
    labels = [item['id'] for item in raw_nodes]
    keys = [label_key(label) for label in labels]
    if len(keys) != len(set(keys)):
        raise ValueError('Duplicate node declarations')
    ordered = sorted(zip(keys, labels), key=lambda pair: pair[0])
    mapping = {key: index for index, (key, _) in enumerate(ordered)}
    raw_edges = graph.get('edges', graph.get('links'))
    edges = []
    original_edges = []
    for edge in raw_edges:
        left, right = label_key(edge['source']), label_key(edge['target'])
        if left not in mapping or right not in mapping:
            raise ValueError('Edge endpoint absent from node declarations')
        if left == right:
            raise ValueError('Self-loop outside simple source graph contract')
        edges.append(sorted((mapping[left], mapping[right])))
        original_edges.append([edge['source'], edge['target']])
    if len({tuple(edge) for edge in edges}) != len(edges):
        raise ValueError('Duplicate undirected edge declarations')
    n, m = len(labels), len(edges)
    if (n, m) != (entry['nodes'], entry['edges']):
        raise ValueError(f'Actual counts {(n, m)} differ from manifest {(entry["nodes"], entry["edges"])}')
    for key, expected in (('num_nodes', n), ('num_edges', m)):
        if key in data and data[key] != expected:
            raise ValueError('Raw count metadata mismatch: ' + key)
    exclusions = count_exclusions(n, m)
    if exclusions:
        raise ValueError('Actual graph violates selection bounds: ' + ','.join(exclusions))
    nodes, edges = list(range(n)), sorted(edges)
    # Exactly compatible with pilot.graph_record(graph) for a graph with no
    # attributes. IDs/families/coordinates/weights stay in sidecars, not solver input.
    record = {'nodes': nodes, 'edges': edges, 'metadata': {},
              'node_attributes': [[v, {}] for v in nodes],
              'edge_attributes': [[a, b, {}] for a, b in edges]}
    audit = {'raw_sha256': file_hash, 'source_hash': digest(record),
             'normalized_topology_hash': digest({'nodes': nodes, 'edges': edges}),
             'labeled_topology_hash': digest({'labels': [label for _, label in ordered], 'edges': edges}),
             'node_order_hash': digest(labels), 'edge_order_hash': digest(original_edges),
             'node_order_already_sorted': keys == sorted(keys),
             'labels_already_zero_based_integers': labels == nodes and all(type(v) is int for v in labels),
             'original_labels_in_integer_order': [label for _, label in ordered],
             'removed_node_attribute_count': sum(len(item) - 1 for item in raw_nodes),
             'removed_edge_attribute_count': sum(len(item) - 2 for item in raw_edges),
             'removed_graph_attribute_keys': sorted(graph.get('graph', {})),
             'actual_nodes': n, 'actual_edges': m,
             'necessary_bounds_passed': True, 'embedding_feasibility': 'unproved'}
    return record, audit


def source_url(entry):
    if entry['url']:
        if not entry['url'].startswith('https://huggingface.co/datasets/zachmacsmith/ember-graphs/'):
            raise ValueError('Manifest URL outside declared corpus')
        return entry['url']
    filename = f'{entry["id"]}_{entry["name"]}.json'
    family = entry['family']
    if family == 'watts_strogatz':
        match = re.search(r'_k([0-9]+)_', filename)
        family = 'watts_strogatz_k' + match.group(1) if match else 'watts_strogatz_other'
    return 'https://huggingface.co/datasets/zachmacsmith/ember-graphs/resolve/main/' + quote(family) + '/' + quote(filename)


def materialize(entry, destination, search_dirs, download=False):
    graph_id = entry['id']
    filename = f'{graph_id}_{entry["name"]}.json'
    try:
        origin = next((root / filename for root in search_dirs if (root / filename).is_file()), None)
        if origin is not None:
            raw, location = origin.read_bytes(), str(origin)
        elif download:
            location = source_url(entry)
            with urlopen(location, timeout=40) as response:
                raw = response.read()
        else:
            raise FileNotFoundError('Requested original graph unavailable locally; downloads disabled')
        raw_path, graph_path = f'raw/{filename}', f'graphs/ember_{graph_id}.json'
        (destination / raw_path).write_bytes(raw)
        record, audit = decode_graph(raw, entry)
        save(destination / graph_path, record)
        labels = audit.pop('original_labels_in_integer_order')
        save(destination / 'labels' / f'ember_{graph_id}.json', {'original_labels_in_integer_order': labels})
        return dict(entry, status='READY', graph_key=f'ember_{graph_id}', graph_path=graph_path,
                    raw_path=raw_path, source_location=location,
                    labels_path=f'labels/ember_{graph_id}.json', **audit)
    except Exception as error:
        result = dict(entry, status='INPUT_ERROR', error=f'{type(error).__name__}: {error}')
        if 'raw' in locals():
            result.update(raw_sha256=hashlib.sha256(raw).hexdigest(), raw_path=raw_path,
                          source_location=location)
        return result


def duplicate_groups(records):
    by_hash = defaultdict(list)
    for record in records:
        if record['status'] == 'READY':
            by_hash[record['normalized_topology_hash']].append(record)
    groups = []
    for topology, entries in sorted(by_hash.items()):
        if len(entries) > 1:
            families = sorted({entry['family'] for entry in entries})
            groups.append({'normalized_topology_hash': topology,
                           'graph_ids': sorted(entry['id'] for entry in entries),
                           'families': families, 'cross_family': len(families) > 1,
                           'within_family': any(count > 1 for count in Counter(e['family'] for e in entries).values())})
    return groups


class LoadedSelection:
    """Iterable graph inputs together with the complete requested-input ledger."""
    def __init__(self, directory, selection):
        self.directory = directory
        self.selection = selection

    @property
    def missing_inputs(self):
        return [item for item in self.selection['records'] if item['status'] != 'READY']

    def __iter__(self):
        import networkx as nx

        for item in self.selection['records']:
            if item['status'] != 'READY':
                continue
            if item['graph_path'] != f'graphs/ember_{item["id"]}.json' or item['graph_key'] != f'ember_{item["id"]}':
                raise ValueError('Unexpected selected graph path or key')
            record = json.loads((self.directory / item['graph_path']).read_text())
            if digest(record) != item['source_hash']:
                raise ValueError('Selected graph changed: ' + str(item['id']))
            graph = nx.Graph()
            graph.add_nodes_from(record['nodes'])
            graph.add_edges_from(record['edges'])
            yield item['id'], item['graph_key'], graph, item


def load_selection(path, allow_missing=False):
    """Return iterable inputs plus full coverage and missing-input records.

    Iteration yields (integer ID, safe graph key, NetworkX graph, metadata).
    Missing inputs fail by default. Explicit allow_missing=True permits a declared
    partial development screen; .selection and .missing_inputs retain its ledger.
    """

    path = Path(path)
    selection = json.loads(path.read_text())
    if not allow_missing and any(item['status'] != 'READY' for item in selection['records']):
        raise ValueError('Selection has unresolved input errors')
    if digest(selection['identity']) != selection['selection_id']:
        raise ValueError('Selection identity mismatch')
    inputs = [{key: item.get(key) for key in ('id', 'status', 'source_hash', 'raw_sha256')}
              for item in selection['records']]
    if inputs != selection['identity']['inputs']:
        raise ValueError('Record identity differs from frozen selection')
    manifest_bytes = (path.parent / 'original-manifest.json').read_bytes()
    if hashlib.sha256(manifest_bytes).hexdigest() != selection['identity']['manifest_sha256']:
        raise ValueError('Original manifest changed')
    entries = {entry['id']: entry for entry in entries_from_manifest(json.loads(manifest_bytes))}
    for item in selection['records']:
        entry = entries[item['id']]
        if any(item[key] != entry[key] for key in entry):
            raise ValueError('Selected metadata differs from original manifest')
    return LoadedSelection(path.parent, selection)


def select(destination, manifest_path=MANIFEST, per_cell=2, seed=SEED, search_dirs=(), download=False, workers=4):
    if destination.exists():
        raise ValueError('Use a new selection directory; existing artifacts are immutable')
    raw_manifest = manifest_path.read_bytes()
    manifest = json.loads(raw_manifest)
    plan = plan_selection(entries_from_manifest(manifest), per_cell, seed)
    destination.mkdir(parents=True)
    for name in ('raw', 'graphs', 'labels'):
        (destination / name).mkdir()
    selector_bytes = Path(__file__).read_bytes()
    (destination / 'selector.py').write_bytes(selector_bytes)
    (destination / 'original-manifest.json').write_bytes(raw_manifest)
    save(destination / 'request.json', plan)
    requested = [entry for entry in plan['ledger'] if entry['requested']]
    print(f'Frozen {len(requested)} requested IDs across {len(plan["families"])} families', flush=True)
    records = []
    with ThreadPoolExecutor(max_workers=workers) as pool:
        for record in pool.map(lambda entry: materialize(entry, destination, search_dirs, download), requested):
            records.append(record)
            if len(records) % 25 == 0 or record['status'] != 'READY':
                print(f'{len(records)}/{len(requested)}: {record["id"]} {record["status"]} {record.get("error", "")}', flush=True)
    by_id = {item['id']: item for item in records}
    for cell in plan['cells']:
        cell['ready_ids'] = [gid for gid in cell['requested_ids'] if by_id[gid]['status'] == 'READY']
        cell['input_error_ids'] = [gid for gid in cell['requested_ids'] if by_id[gid]['status'] != 'READY']
        cell['distinct_normalized_topologies'] = len({by_id[gid]['normalized_topology_hash'] for gid in cell['ready_ids']})
    coverage = []
    for family in plan['families']:
        entries = [item for item in plan['ledger'] if item['family'] == family]
        cells = [item for item in plan['cells'] if item['family'] == family]
        coverage.append({'family': family, 'manifest_count': len(entries),
                         'manifest_bound_eligible': sum(not item['manifest_bound_exclusions'] for item in entries),
                         'manifest_bound_excluded': sum(bool(item['manifest_bound_exclusions']) for item in entries),
                         'nonempty_manifest_cells': sum(bool(item['manifest_eligible']) for item in cells),
                         'requested': sum(len(item['requested_ids']) for item in cells),
                         'ready': sum(len(item['ready_ids']) for item in cells),
                         'input_errors': sum(len(item['input_error_ids']) for item in cells)})
    identity = {'manifest_sha256': hashlib.sha256(raw_manifest).hexdigest(), 'seed': seed,
                'per_cell': per_cell, 'size_bins': BINS, 'target_nodes': TARGET_N, 'target_edges': TARGET_M,
                'requested_ids': plan['requested_ids'],
                'inputs': [{k: item.get(k) for k in ('id', 'status', 'source_hash', 'raw_sha256')} for item in records],
                'selector_sha256': hashlib.sha256(selector_bytes).hexdigest()}
    result = {'format_version': 1, 'purpose': 'inherited corpus development screening',
              'selection_id': digest(identity), 'identity': identity, 'created_unix': time.time(),
              'criteria': {'ranking': 'SHA256(seed,family,node-bin,manifest-ID)',
                           'uses_algorithm_results': False, 'replacement_on_error_or_duplicate': False,
                           'bounds_certify_feasibility': False, 'attributes_supplied_to_solver': False,
                           'isomorphism_complete': False},
              'families': coverage, 'cells': plan['cells'], 'records': records,
              'duplicate_groups': duplicate_groups(records)}
    save(destination / 'selection.json', result)
    table = ['| Family | Manifest | Bound-eligible | Cells | Requested | Ready | Errors |',
             '| --- | ---: | ---: | ---: | ---: | ---: | ---: |']
    for item in coverage:
        table.append('| ' + ' | '.join(str(item[key]) for key in
                     ('family', 'manifest_count', 'manifest_bound_eligible', 'nonempty_manifest_cells', 'requested', 'ready', 'input_errors')) + ' |')
    (destination / 'coverage.md').write_text('\n'.join(table) + '\n')
    print(json.dumps({'selection_id': result['selection_id'], 'requested': len(records),
                      'statuses': dict(Counter(item['status'] for item in records)),
                      'duplicate_groups': len(result['duplicate_groups'])}, indent=2))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('destination', type=Path)
    parser.add_argument('--manifest', type=Path, default=MANIFEST)
    parser.add_argument('--per-cell', type=int, choices=(1, 2), default=2)
    parser.add_argument('--seed', default=SEED)
    parser.add_argument('--graph-dir', action='append', type=Path, default=[])
    parser.add_argument('--download', action='store_true')
    args = parser.parse_args()
    from platformdirs import user_data_dir
    search_dirs = args.graph_dir + [BUNDLED, Path(user_data_dir('ember-qc', 'ember-qc')) / 'graphs']
    select(args.destination, args.manifest, args.per_cell, args.seed, search_dirs, args.download)


if __name__ == '__main__':
    main()
