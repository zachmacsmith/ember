"""Revalidate a completed frozen pilot and report per-input paired observations.

Quality summaries use only timely valid successes. Failed and late observations
retain separate counts; no per-instance algorithm selection or portfolio score
is constructed. These reports describe development samples, not family effects.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import csv
import hashlib
import json
from pathlib import Path
import statistics

from pilot import (check_corpus_provenance, check_supplement_provenance, check_result, check_task, digest,
                   graph_from_record, verify_embedding, write_json)


def checked_run(run):
    run = Path(run)
    manifest = json.loads((run / 'manifest.json').read_text())
    if manifest.get('format_version') != 2:
        raise ValueError('Only version-2 frozen runs are supported')
    if len(set(manifest['tasks'])) != len(manifest['tasks']):
        raise ValueError('Duplicate tasks in manifest')
    if digest(manifest['source_files']) != manifest['source_snapshot']:
        raise ValueError('Source snapshot identity mismatch')
    for relative, expected in manifest['source_files'].items():
        if hashlib.sha256((run / 'source' / relative).read_bytes()).hexdigest() != expected:
            raise ValueError(f'Source hash mismatch: {relative}')
    check_corpus_provenance(run, manifest)
    check_supplement_provenance(run, manifest)
    target_record = json.loads((run / 'target.json').read_text())
    if digest(target_record) != manifest['target_hash']:
        raise ValueError('Target hash mismatch')
    target = graph_from_record(target_record)
    sources, records = {}, []
    unique_trials = set()
    for task_id in manifest['tasks']:
        task = json.loads((run / 'tasks' / (task_id + '.json')).read_text())
        check_task(task, task_id, manifest)
        key = (task['source_hash'], task['target_hash'], task['method'], task['seed'])
        if key in unique_trials:
            raise ValueError(f'Duplicate source/method/seed trial: {task_id}')
        unique_trials.add(key)
        graph = task['graph']
        if graph not in sources:
            source_record = json.loads((run / 'graphs' / (graph + '.json')).read_text())
            sources[graph] = (graph_from_record(source_record), digest(source_record))
        source, source_hash = sources[graph]
        if source_hash != task['source_hash']:
            raise ValueError(f'Source graph hash mismatch: {task_id}')
        result_path = run / 'results' / (task_id + '.json')
        if not result_path.exists():
            raise ValueError(f'Run is incomplete: missing {task_id}')
        outcome = json.loads(result_path.read_text())
        check_result(outcome, task)
        if not outcome.get('controller_finalized'):
            raise ValueError(f'Result is not finalized: {task_id}')
        raw = outcome.get('embedding')
        valid = False
        acl = variance = None
        if raw is not None:
            # Frozen pilot graphs have integer labels. Detect lossy key decoding.
            embedding = {int(v): chain for v, chain in raw.items()}
            if len(embedding) != len(raw):
                raise ValueError(f'Embedding key collision: {task_id}')
            valid = verify_embedding(embedding, source, target) is None
            if valid:
                lengths = [len(embedding[v]) for v in source]
                acl = statistics.mean(lengths) if lengths else None
                variance = statistics.pvariance(lengths) if lengths else None
        if 'embedding_valid' in outcome and outcome['embedding_valid'] != valid:
            raise ValueError(f'Validity report mismatch: {task_id}')
        if outcome['status'] == 'SUCCESS':
            if not valid or outcome.get('solver_wall', float('inf')) > task['timeout']:
                raise ValueError(f'Invalid or late success: {task_id}')
            if (outcome.get('acl') != acl
                    or abs(outcome.get('within_chain_variance', 0) - (variance or 0)) > 1e-10):
                raise ValueError(f'Quality report mismatch: {task_id}')
            if outcome.get('returncode') not in (0, None):
                raise ValueError(f'Success with abnormal process exit: {task_id}')
            if task['method'] != 'mm':
                if (outcome.get('forbidden_import_attempts') != []
                        or outcome.get('loaded_embedding_libraries') != []
                        or outcome.get('versions', {}).get('minorminer') is not None):
                    raise ValueError(f'Candidate independence failure: {task_id}')
        elif any(key in outcome for key in ('acl', 'qubits', 'within_chain_variance')):
            raise ValueError(f'Non-success has credited quality: {task_id}')
        records.append(outcome)
    if len({row.get('host') for row in records}) > 1:
        raise ValueError('Mixed hosts: analyze separate machine runs before comparing timing')
    return manifest, records


def _mean(values):
    return statistics.mean(values) if values else None


def summarize(records):
    groups, trials, configs = defaultdict(list), {}, {}
    for row in records:
        key = (row['graph'], row['source_hash'], row['target_hash'], row['method'])
        config_hash = digest(row['config'])
        if key in configs and configs[key] != config_hash:
            raise ValueError(f'Mixed configurations in method: {key}')
        configs[key] = config_hash
        groups[key].append(row)
        trials[(row['source_hash'], row['target_hash'], row['method'], row['seed'])] = row
    summary = []
    for (graph, source_hash, target_hash, method), rows in sorted(groups.items()):
        successful = [r for r in rows if r['status'] == 'SUCCESS']
        acl = [r['acl'] for r in successful if r.get('acl') is not None]
        wall = [r['solver_wall'] for r in rows if r.get('solver_wall') is not None]
        process = [r['process_wall'] for r in rows if r.get('process_wall') is not None]
        summary.append({'graph': graph, 'source_hash': source_hash, 'target_hash': target_hash,
                        'method': method, 'attempted': len(rows), 'successes': len(successful),
                        'statuses': dict(Counter(r['status'] for r in rows)),
                        'acl_mean': _mean(acl),
                        'acl_sample_variance': statistics.variance(acl) if len(acl) > 1 else None,
                        'within_chain_variance_mean': _mean([r['within_chain_variance'] for r in successful
                                                            if r.get('within_chain_variance') is not None]),
                        'solver_wall_mean_all_returned': _mean(wall),
                        'solver_wall_observations': len(wall),
                        'process_wall_mean': _mean(process),
                        'process_wall_observations': len(process)})
    paired = []
    for row in records:
        if row['method'] == 'mm':
            continue
        base = trials.get((row['source_hash'], row['target_hash'], 'mm', row['seed']))
        timely_pair = base is not None and row['status'] == base['status'] == 'SUCCESS'
        quality_pair = timely_pair and row.get('acl') is not None and base.get('acl') is not None
        paired.append({'graph': row['graph'], 'method': row['method'], 'seed': row['seed'],
                       'source_hash': row['source_hash'], 'target_hash': row['target_hash'],
                       'candidate_status': row['status'], 'mm_status': base['status'] if base else 'NOT_ATTEMPTED',
                       'paired_timely_success': timely_pair,
                       'acl_delta': row['acl'] - base['acl'] if quality_pair else None,
                       'acl_ratio': row['acl'] / base['acl'] if quality_pair and base['acl'] else None,
                       'solver_wall_ratio': row['solver_wall'] / base['solver_wall']
                        if timely_pair and base['solver_wall'] else None,
                       'process_wall_ratio': row['process_wall'] / base['process_wall']
                        if timely_pair and row.get('process_wall') is not None and base.get('process_wall') else None})
    return {'per_input': summary, 'paired_trials': paired}


def report(run, destination):
    manifest, records = checked_run(run)
    summary = summarize(records)
    destination.mkdir(parents=True, exist_ok=True)
    if manifest.get('input_supplement') is not None:
        checked = check_supplement_provenance(run, manifest)
        provenance = dict(manifest['input_supplement'],
                          sources={entry['graph_key']: entry['provenance'] for entry in checked['entries']})
        summary['input_supplement'] = provenance
        write_json(destination / 'input_provenance.json', provenance)
    write_json(destination / 'summary.json', dict(summary, source_snapshot=manifest['source_snapshot'],
                                                  planned=len(manifest['tasks']),
                                                  statuses=dict(Counter(r['status'] for r in records))))
    for name in ('per_input', 'paired_trials'):
        rows = summary[name]
        with (destination / (name + '.csv')).open('w', newline='') as stream:
            writer = csv.DictWriter(stream, fieldnames=list(rows[0]) if rows else [])
            writer.writeheader()
            writer.writerows(rows)
    def fmt(value):
        return '—' if value is None else f'{value:.6g}'
    lines = ['# Validated development observations', '',
             'Quality includes only timely valid successes. Variance is the sample variance',
             'of ACL across successful solver trials on the same input; failed trials are',
             'reported separately. Small samples are not evidence of family-wide superiority.',
             'Solver wall includes failed calls that returned a measurement. Process wall',
             'is separate; interrupted observations with unknown timing are never zero.', '',
             '| Input | Method | Success / attempted | Mean ACL | ACL sample variance | Mean solver s | Mean process s |',
             '| --- | --- | ---: | ---: | ---: | ---: | ---: |']
    for row in summary['per_input']:
        lines.append(f"| {row['graph']} | {row['method']} | {row['successes']} / {row['attempted']} | "
                     f"{fmt(row['acl_mean'])} | {fmt(row['acl_sample_variance'])} | "
                     f"{fmt(row['solver_wall_mean_all_returned'])} | {fmt(row['process_wall_mean'])} |")
    (destination / 'report.md').write_text('\n'.join(lines) + '\n')
    print(json.dumps({'observations': len(records), 'statuses': dict(Counter(r['status'] for r in records)),
                      'destination': str(destination)}, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run', type=Path)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    report(args.run, args.output or args.run / 'analysis')
