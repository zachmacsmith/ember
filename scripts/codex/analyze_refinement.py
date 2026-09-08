"""Validate frozen refinement observations and compare one fixed control arm."""
import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import statistics

from refinement_ablation import (canonical_embedding, check_snapshot, contact_redundancy,
                                digest, graph_from_record, verify, write_json)


def analyze(run, control='both', reference=None):
    manifest = json.loads((run / 'manifest.json').read_text())
    check_snapshot(run, manifest)
    previous = {}
    if reference:
        for path in (reference / 'results').glob('*.json'):
            result = json.loads(path.read_text())
            previous[result['graph'], result['seed'], result['arm']] = result
    rows, checked_replays = [], 0
    target = graph_from_record(json.loads((run / 'target.json').read_text()))
    for task_id, task in manifest['tasks'].items():
        result = json.loads((run / 'results' / (task_id + '.json')).read_text())
        if digest(task)[:24] != task_id or any(result.get(k) != v for k, v in task.items()):
            raise ValueError('Task/result identity mismatch')
        if (result['source_snapshot'] != manifest['source_snapshot']
                or result.get('forbidden_import_attempts') != []
                or result.get('loaded_embedding_libraries') != []
                or result.get('versions', {}).get('minorminer') is not None):
            raise ValueError('Source or dependency evidence mismatch')
        if result['status'] != 'SUCCESS' or result.get('returncode') != 0:
            raise ValueError(f'Non-success needs explicit separate analysis: {task_id}')
        case = manifest['cases'][task['case_id']]
        record = json.loads((run / 'graphs' / (case['graph'] + '.json')).read_text())
        source = graph_from_record(record)
        if digest(record) != case['source_hash']:
            raise ValueError('Graph identity mismatch')
        old = json.loads((run / 'incumbents' / (task['case_id'] + '.json')).read_text())
        initial = {int(v): c for v, c in old['embedding'].items()}
        embedding = {int(v): c for v, c in result['embedding'].items()}
        initial_quality, quality = verify(initial, source, target), verify(embedding, source, target)
        if any(result[k] != quality[k] for k in ('qubits', 'acl', 'max_chain')):
            raise ValueError('Output metric mismatch')
        if digest(canonical_embedding(embedding)) != result['embedding_hash']:
            raise ValueError('Output embedding hash mismatch')
        diag, config = result['diag'], task['configuration']
        if (result['refinement_wall'] > config['timeout']
                or diag['expansions'] > config['max_expansions']
                or diag['groups_tried'] > config['max_groups']
                or diag['max_region_size'] > config['max_region']):
            raise ValueError('Claimed success exceeds declared allowance')
        current, equal_moves = initial_quality['qubits'], 0
        for move in diag['trajectory']:
            saved = current - move['total_qubits']
            if saved < 0 or saved != move['qubits_saved']:
                raise ValueError('Nonmonotonic qubit trajectory or false gain')
            if saved == 0:
                if not move.get('equal_size_move') or move.get('contact_redundancy_gain', 0) <= 0:
                    raise ValueError('Equal-size move lacks strict secondary progress')
                equal_moves += 1
            current = move['total_qubits']
        if (current != quality['qubits'] or len(diag['trajectory']) != diag['accepted']
                or equal_moves != diag.get('equal_size_moves', 0)):
            raise ValueError('Trajectory totals mismatch')
        if config.get('objective') == 'qubits_contacts':
            actual_gain = (contact_redundancy(embedding, source, target)
                           - contact_redundancy(initial, source, target))
            if actual_gain != diag['contact_redundancy_gain']:
                raise ValueError('Secondary objective delta mismatch')
        key = result['graph'], result['seed'], result['arm']
        if key in previous:
            if canonical_embedding(result['embedding']) != canonical_embedding(previous[key]['embedding']):
                raise ValueError(f'Prior strict reference replay differs: {key}')
            checked_replays += 1
        rows.append(result)
    if len({row['host'] for row in rows}) != 1:
        raise ValueError('Mixed hosts')
    by_arm, by_case = defaultdict(list), {}
    for row in rows:
        by_arm[row['arm']].append(row)
        by_case[row['graph'], row['seed'], row['arm']] = row
    comparisons = []
    for arm, group in by_arm.items():
        wins = ties = losses = delta = 0
        time_ratios = []
        for row in group:
            base = by_case[row['graph'], row['seed'], control]
            difference = row['qubits'] - base['qubits']
            wins += difference < 0
            ties += difference == 0
            losses += difference > 0
            delta += difference
            time_ratios.append(row['refinement_wall'] / base['refinement_wall'])
        comparisons.append({
            'arm': arm, 'trials': len(group), 'mean_acl': statistics.mean(r['acl'] for r in group),
            'wins': wins, 'ties': ties, 'losses': losses, 'total_qubit_delta': delta,
            'total_refinement_wall': sum(r['refinement_wall'] for r in group),
            'median_paired_wall_ratio': statistics.median(time_ratios),
            'expansions': sum(r['diag']['expansions'] for r in group),
            'equal_size_moves': sum(r['diag'].get('equal_size_moves', 0) for r in group),
            'stops': dict(Counter(r['diag']['stopped_by'] for r in group))})
    output = {'source_snapshot': manifest['source_snapshot'], 'verified_results': len(rows),
              'checked_prior_replays': checked_replays, 'control': control,
              'comparisons': comparisons,
              'per_trial': [{k: r[k] for k in ('graph', 'seed', 'arm', 'qubits', 'acl',
                                              'refinement_wall')} for r in rows],
              'limits': 'Development saved incumbents, refinement-only timing on an unreserved host; no family-level claim.'}
    write_json(run / 'analysis.json', output)
    print(json.dumps({k: v for k, v in output.items() if k != 'per_trial'}, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run', type=Path)
    parser.add_argument('--control', default='both')
    parser.add_argument('--reference', type=Path)
    args = parser.parse_args()
    analyze(args.run, args.control, args.reference)
