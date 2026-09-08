"""Freeze corrected Sudoku development inputs without running an embedder.

Only box orders 2 and 3 are authorized here. All scientific parameters and cell
interpretation stay in provenance; solver records contain plain graph structure.
Existing output directories are immutable, including incomplete earlier writes.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
from itertools import combinations
import json
from pathlib import Path
import platform


ROOT = Path(__file__).absolute().parents[2]
ORIGINAL_MANIFEST = ROOT / 'packages/ember-qc/src/ember_qc/graphs/manifest.json'
PROTOCOL = ROOT / 'notes/codex/generalization_protocol.md'
DEFAULT_OUTPUT = ROOT / 'results/codex/027-sudoku-development-supplement'
VERSION = 'sudoku-cell-conflict-v1'
IDS = {2: 1000002, 3: 1000003}
PRESERVED_IDS = (37900, 37901)
RESERVED_ORDERS = (4, 5)
TARGET_N, TARGET_M = 4800, 45864


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def json_bytes(value):
    return (json.dumps(value, sort_keys=True, indent=2) + '\n').encode()


def byte_hash(raw):
    return hashlib.sha256(raw).hexdigest()


def _check_order(box_order):
    if type(box_order) is not int or box_order not in IDS:
        raise ValueError('Only development box orders 2 and 3 are authorized')


def build_graph_record(box_order):
    """Generate one row/column/box conflict graph as a sanitized pilot record."""
    _check_order(box_order)
    q, side = box_order, box_order ** 2
    nodes = list(range(side ** 2))
    groups = [[r * side + c for c in range(side)] for r in range(side)]
    groups += [[r * side + c for r in range(side)] for c in range(side)]
    groups += [[(br * q + dr) * side + bc * q + dc
                for dr in range(q) for dc in range(q)]
               for br in range(q) for bc in range(q)]
    edges = sorted({tuple(sorted(pair)) for group in groups for pair in combinations(group, 2)})
    record = {'nodes': nodes, 'edges': [list(edge) for edge in edges],
              'metadata': {}, 'node_attributes': [[v, {}] for v in nodes],
              'edge_attributes': [[a, b, {}] for a, b in edges]}
    verify_graph_record(record, box_order)
    return record


def verify_graph_record(record, box_order):
    """Check every cell pair independently of the generator's clique unions."""
    _check_order(box_order)
    q, side = box_order, box_order ** 2
    nodes = list(range(q ** 4))
    if (not isinstance(record, dict)
            or set(record) != {'nodes', 'edges', 'metadata', 'node_attributes', 'edge_attributes'}
            or record['nodes'] != nodes
            or any(type(v) is not int for v in record['nodes'])):
        raise ValueError('Unexpected graph schema or vertex declarations')
    edges = record['edges']
    if (not isinstance(edges, list)
            or any(not isinstance(edge, list) or len(edge) != 2
                   or any(type(v) is not int for v in edge)
                   or not 0 <= edge[0] < edge[1] < len(nodes) for edge in edges)
            or edges != sorted(edges)
            or len({tuple(edge) for edge in edges}) != len(edges)):
        raise ValueError('Invalid, unordered, or duplicate edges')
    if (record['metadata'] != {}
            or digest(record['node_attributes']) != digest([[v, {}] for v in nodes])
            or digest(record['edge_attributes']) != digest([[a, b, {}] for a, b in edges])):
        raise ValueError('Solver-visible metadata or attributes are forbidden')
    actual = {tuple(edge) for edge in edges}
    pair_counts = Counter()
    # Deliberately independent of row/column/box clique construction above.
    for a in nodes:
        ar, ac = divmod(a, side)
        for b in range(a + 1, len(nodes)):
            br, bc = divmod(b, side)
            row, column = ar == br, ac == bc
            box = ar // q == br // q and ac // q == bc // q
            if ((a, b) in actual) != (row or column or box):
                raise ValueError(f'Cell constraint mismatch at pair {(a, b)}')
            if row:
                pair_counts['same_row'] += 1
            if column:
                pair_counts['same_column'] += 1
            if box and not row and not column:
                pair_counts['additional_same_box'] += 1
    degree = 3 * q ** 2 - 2 * q - 1
    degrees = Counter(v for edge in edges for v in edge)
    if len(edges) != len(nodes) * degree // 2 or any(degrees[v] != degree for v in nodes):
        raise ValueError('Counts or regular degree do not match Sudoku constraints')
    return {'vertices': len(nodes), 'edges': len(edges), 'regular_degree': degree,
            'constraint_pairs': dict(sorted(pair_counts.items())),
            'all_pairs_checked': len(nodes) * (len(nodes) - 1) // 2,
            'necessary_bounds_passed': len(nodes) <= TARGET_N and len(edges) <= TARGET_M,
            'embedding_feasibility': 'unproved'}


def _inherited_entries(raw):
    manifest = json.loads(raw)
    entries = manifest['graphs']
    ids = [entry['id'] for entry in entries]
    if any(type(gid) is not int for gid in ids) or len(set(ids)) != len(ids):
        raise ValueError('Original manifest has invalid or duplicate IDs')
    if set(IDS.values()) & set(ids):
        raise ValueError('Supplement ID collides with original manifest')
    preserved = [entry for entry in entries if entry['id'] in PRESERVED_IDS]
    if sorted(entry['id'] for entry in preserved) != list(PRESERVED_IDS):
        raise ValueError('Original Sudoku entries are missing')
    return sorted(preserved, key=lambda entry: entry['id'])


def freeze_supplement(output=DEFAULT_OUTPUT, *, manifest_path=ORIGINAL_MANIFEST,
                      protocol_path=PROTOCOL):
    """Create a new immutable bundle; reject any existing destination.

    The completion manifest is written last. Interrupted partial destinations
    remain inspectable and cannot be silently overwritten or resumed.
    """
    output = Path(output)
    if output.exists() or output.is_symlink():
        raise FileExistsError(f'Immutable supplement destination already exists: {output}')
    original_raw = Path(manifest_path).read_bytes()
    preserved = _inherited_entries(original_raw)
    files = {'source/sudoku_supplement.py': Path(__file__).read_bytes(),
             'source/generalization_protocol.md': Path(protocol_path).read_bytes(),
             'provenance/original_sudoku_entries.json': json_bytes(preserved)}
    entries = []
    for q, gid in sorted(IDS.items()):
        record = build_graph_record(q)
        audit = verify_graph_record(record, q)
        graph_path, provenance_path = f'graphs/{gid}.json', f'provenance/{gid}.json'
        provenance = {'id': gid, 'supplement_instance_id': f'{VERSION}-q{q}',
                      'generator_version': VERSION, 'split': 'development',
                      'family': 'sudoku', 'box_order': q, 'board_side': q ** 2,
                      'label_convention': 'row-major cell index: row * board_side + column',
                      'source_hash': digest(record),
                      'normalized_topology_hash': digest({'nodes': record['nodes'], 'edges': record['edges']}),
                      'generator_source_sha256': byte_hash(files['source/sudoku_supplement.py']),
                      'target_count_reference': {'architecture': 'ideal_zephyr', 'm': 12, 't': 4,
                                                 'vertices': TARGET_N, 'edges': TARGET_M},
                      'structure_novelty': 'not_audited_against_complete_inherited_universe',
                      **audit}
        files[graph_path] = json_bytes(record)
        files[provenance_path] = json_bytes(provenance)
        entries.append({'id': gid, 'graph_key': f'sudoku_supplement_v1_q{q}',
                        'box_order': q, 'graph_record_path': graph_path,
                        'provenance_path': provenance_path,
                        'source_hash': provenance['source_hash']})
    manifest = {'schema_version': 1, 'generator_version': VERSION,
                'purpose': 'development_input_supplement_no_embedding_results',
                'generated_box_orders': sorted(IDS), 'reserved_ungenerated_box_orders': list(RESERVED_ORDERS),
                'original_manifest_sha256': byte_hash(original_raw),
                'preserved_original_ids': list(PRESERVED_IDS),
                'python_version': platform.python_version(), 'entries': entries,
                'files': {name: byte_hash(raw) for name, raw in sorted(files.items())}}
    manifest['supplement_id'] = digest(manifest)
    output.mkdir(parents=True, exist_ok=False)
    for name, raw in files.items():
        path = output / name
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('xb') as stream:
            stream.write(raw)
    with (output / 'manifest.json').open('xb') as stream:
        stream.write(json_bytes(manifest))
    load_supplement(output)
    return manifest


def load_supplement(directory=DEFAULT_OUTPUT):
    """Verify the whole frozen bundle; return dictionaries with record/provenance.

    Each returned item contains ``id``, ``graph_key``, ``graph_record_path``,
    ``record``, and evaluator-only ``provenance``. Convert only ``record`` with
    ``pilot.graph_from_record`` when integrating into a later runner.
    """
    directory = Path(directory)
    if directory.is_symlink():
        raise ValueError('Supplement directory must not be a symlink')
    manifest_path = directory / 'manifest.json'
    if not manifest_path.is_file() or manifest_path.is_symlink():
        raise ValueError('Supplement is incomplete or its manifest is not a regular file')
    manifest = json.loads(manifest_path.read_bytes())
    identity = {k: v for k, v in manifest.items() if k != 'supplement_id'}
    if digest(identity) != manifest.get('supplement_id'):
        raise ValueError('Supplement manifest identity mismatch')
    if (manifest['schema_version'] != 1 or manifest['generator_version'] != VERSION
            or manifest['generated_box_orders'] != sorted(IDS)
            or manifest['reserved_ungenerated_box_orders'] != list(RESERVED_ORDERS)
            or manifest['preserved_original_ids'] != list(PRESERVED_IDS)):
        raise ValueError('Supplement scope or version mismatch')
    expected_names = {'source/sudoku_supplement.py', 'source/generalization_protocol.md',
                      'provenance/original_sudoku_entries.json'}
    for gid in IDS.values():
        expected_names.update((f'graphs/{gid}.json', f'provenance/{gid}.json'))
    paths = list(directory.rglob('*'))
    if (any(path.is_symlink() for path in paths)
            or {path.relative_to(directory).as_posix() for path in paths if path.is_file()}
            != expected_names | {'manifest.json'}
            or set(manifest['files']) != expected_names):
        raise ValueError('Supplement file set mismatch or symlink')
    for name, expected_hash in manifest['files'].items():
        if byte_hash((directory / name).read_bytes()) != expected_hash:
            raise ValueError(f'Supplement file hash mismatch: {name}')
    inherited = json.loads((directory / 'provenance/original_sudoku_entries.json').read_bytes())
    if [entry['id'] for entry in inherited] != list(PRESERVED_IDS):
        raise ValueError('Preserved original identities mismatch')
    expected_entries = [(q, gid) for q, gid in sorted(IDS.items())]
    if len(manifest['entries']) != len(expected_entries):
        raise ValueError('Supplement entry count mismatch')
    output = []
    for entry, (q, gid) in zip(manifest['entries'], expected_entries):
        if (entry['id'] != gid or entry['box_order'] != q
                or entry['graph_key'] != f'sudoku_supplement_v1_q{q}'
                or entry['graph_record_path'] != f'graphs/{gid}.json'
                or entry['provenance_path'] != f'provenance/{gid}.json'):
            raise ValueError('Supplement entry identity mismatch')
        record_path = directory / entry['graph_record_path']
        record = json.loads(record_path.read_bytes())
        provenance = json.loads((directory / entry['provenance_path']).read_bytes())
        audit = verify_graph_record(record, q)
        if (digest(record) != entry['source_hash'] or provenance['source_hash'] != entry['source_hash']
                or provenance['normalized_topology_hash'] != digest({'nodes': record['nodes'], 'edges': record['edges']})
                or type(provenance['id']) is not int or provenance['id'] != gid
                or type(provenance['box_order']) is not int or provenance['box_order'] != q
                or type(provenance['board_side']) is not int or provenance['board_side'] != q ** 2
                or provenance['family'] != 'sudoku'
                or provenance['supplement_instance_id'] != f'{VERSION}-q{q}'
                or provenance['generator_version'] != VERSION or provenance['split'] != 'development'
                or provenance['target_count_reference'] != {'architecture': 'ideal_zephyr', 'm': 12, 't': 4,
                                                           'vertices': TARGET_N, 'edges': TARGET_M}
                or provenance['generator_source_sha256'] != manifest['files']['source/sudoku_supplement.py']
                or any(provenance.get(key) != value for key, value in audit.items())):
            raise ValueError('Supplement provenance or semantic identity mismatch')
        output.append({'id': gid, 'graph_key': entry['graph_key'],
                       'graph_record_path': record_path, 'record': record,
                       'provenance': provenance})
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('freeze', 'verify'))
    parser.add_argument('--output', type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    if args.action == 'freeze':
        manifest = freeze_supplement(args.output)
        print(json.dumps({'supplement_id': manifest['supplement_id'], 'output': str(args.output)}))
    else:
        entries = load_supplement(args.output)
        print(json.dumps({'verified_ids': [entry['id'] for entry in entries],
                          'source_hashes': [entry['provenance']['source_hash'] for entry in entries]}))


if __name__ == '__main__':
    main()
