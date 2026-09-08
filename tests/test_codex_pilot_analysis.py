"""Scientific accounting controls for the frozen development report."""
import copy
import importlib
import json
from pathlib import Path

import networkx as nx
import pytest


@pytest.fixture
def analysis(monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1] / 'scripts/codex'))
    return importlib.import_module('analyze_pilot')


@pytest.fixture
def tiny_run(tmp_path, analysis):
    from pilot import graph_record
    for directory in ('graphs', 'tasks', 'results'):
        (tmp_path / directory).mkdir()
    source, target = graph_record(nx.path_graph(3)), graph_record(nx.path_graph(5))
    snapshot = analysis.digest({})
    task = {'graph': 'input', 'source_hash': analysis.digest(source),
            'target_hash': analysis.digest(target), 'source_snapshot': snapshot,
            'method': 'native', 'seed': 0, 'config': {}, 'timeout': 2}
    task['task_id'] = analysis.digest(task)[:24]
    result = dict(task, status='SUCCESS', controller_finalized=True, host='one',
                  embedding={'0': [0], '1': [1, 2, 3], '2': [4]},
                  embedding_valid=True, acl=5/3, within_chain_variance=8/9,
                  solver_wall=1.0, process_wall=1.5, returncode=0,
                  forbidden_import_attempts=[], loaded_embedding_libraries=[],
                  versions={'minorminer': None})
    manifest = {'format_version': 2, 'source_files': {}, 'source_snapshot': snapshot,
                'target_hash': task['target_hash'], 'tasks': [task['task_id']]}
    for path, value in [('manifest.json', manifest), ('target.json', target),
                        ('graphs/input.json', source), ('tasks/' + task['task_id'] + '.json', task),
                        ('results/' + task['task_id'] + '.json', result)]:
        (tmp_path / path).write_text(json.dumps(value))
    return tmp_path, result


def test_complete_record_revalidated_from_original_graphs(tiny_run, analysis):
    run, result = tiny_run
    manifest, records = analysis.checked_run(run)
    assert len(records) == 1 and records[0]['acl'] == 5/3
    assert manifest['tasks'] == [result['task_id']]


@pytest.mark.parametrize('change', [
    {'embedding': {'0': [0], '1': [1], '2': [4]}},
    {'solver_wall': 2.01},
    {'acl': 1.0},
    {'forbidden_import_attempts': ['minorminer']},
    {'controller_finalized': False},
])
def test_report_rejects_invalid_credit_or_incomplete_records(tiny_run, analysis, change):
    run, result = tiny_run
    result.update(change)
    (run / 'results' / (result['task_id'] + '.json')).write_text(json.dumps(result))
    with pytest.raises(ValueError):
        analysis.checked_run(run)


def test_timeout_quality_cannot_improve_successful_mean(tiny_run, analysis):
    _, successful = tiny_run
    late = copy.deepcopy(successful)
    late.update(seed=1, status='TIMEOUT', solver_wall=2.01, diagnostic_quality={'acl': 1.0})
    del late['acl']
    del late['within_chain_variance']
    report = analysis.summarize([successful, late])
    row = report['per_input'][0]
    assert row['attempted'] == 2 and row['successes'] == 1
    assert row['acl_mean'] == 5/3 and row['acl_sample_variance'] is None
    assert row['statuses'] == {'SUCCESS': 1, 'TIMEOUT': 1}
    assert all(p['mm_status'] == 'NOT_ATTEMPTED' for p in report['paired_trials'])
    assert all(p['acl_delta'] is None for p in report['paired_trials'])


def test_sample_variance_and_pairs_use_exact_source_and_seed(tiny_run, analysis):
    _, first = tiny_run
    first = dict(first, acl=2.0)
    second = dict(first, seed=1, acl=4.0)
    mm = dict(first, method='mm', seed=1, acl=5.0)
    unrelated = dict(mm, source_hash='different', seed=0, acl=99.0)
    report = analysis.summarize([first, second, mm, unrelated])
    row = next(r for r in report['per_input'] if r['method'] == 'native')
    assert row['acl_mean'] == 3 and row['acl_sample_variance'] == 2
    paired = {r['seed']: r for r in report['paired_trials']}
    assert paired[0]['mm_status'] == 'NOT_ATTEMPTED'
    assert paired[1]['acl_delta'] == -1
    assert paired[1]['acl_ratio'] == 0.8


def test_different_configs_do_not_silently_pool(tiny_run, analysis):
    _, first = tiny_run
    second = dict(first, seed=1, config={'beam_width': 4})
    with pytest.raises(ValueError, match='Mixed configurations'):
        analysis.summarize([first, second])
