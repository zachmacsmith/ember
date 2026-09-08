"""Infrastructure checks that never connect to the cluster or run a solver."""
import ast
import hashlib
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest


SPEC = importlib.util.spec_from_file_location(
    'codex_cluster', Path(__file__).parents[1] / 'scripts/codex/cluster.py')
cluster = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(cluster)


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value))


@pytest.fixture
def frozen(tmp_path):
    run = tmp_path / 'frozen'
    source = run / 'source/scripts/codex/pilot.py'
    source.parent.mkdir(parents=True)
    source.write_text('# An inert test fixture, not an executable benchmark.\n')
    sources = {'scripts/codex/pilot.py': hashlib.sha256(source.read_bytes()).hexdigest()}
    graph = {'nodes': [0], 'edges': [], 'metadata': {}}
    task = {'graph': 'fixture', 'source_hash': cluster.digest(graph),
            'target_hash': cluster.digest(graph), 'source_snapshot': cluster.digest(sources),
            'method': 'fixture', 'seed': 0, 'timeout': 1, 'config': {}}
    task['task_id'] = cluster.digest(task)[:24]
    manifest = {'format_version': 2, 'source_files': sources,
                'source_snapshot': cluster.digest(sources),
                'target_hash': cluster.digest(graph), 'tasks': [task['task_id']]}
    write_json(run / 'manifest.json', manifest)
    write_json(run / 'target.json', graph)
    write_json(run / 'graphs/fixture.json', graph)
    write_json(run / 'tasks' / (task['task_id'] + '.json'), task)
    return run, manifest, task


@pytest.fixture
def helper():
    tree = ast.parse(cluster.REMOTE_HELPER)
    # Execute only the helper's definitions; no remote action or network access.
    definitions = ast.Module(body=[node for node in tree.body
                                  if isinstance(node, (ast.Import, ast.ImportFrom, ast.FunctionDef))],
                             type_ignores=[])
    namespace = {}
    exec(compile(definitions, '<cluster helper definitions>', 'exec'), namespace)
    return namespace


def test_bundle_roundtrip_and_remote_verification(frozen, tmp_path, helper):
    run, manifest, task = frozen
    destination = tmp_path / 'bundle'
    transport = cluster.build_bundle(run, destination)
    assert helper['verify'](destination) == transport
    assert len(transport['files']) == 5
    for relative, expected in transport['files'].items():
        assert (destination / relative).read_bytes() == (run / relative).read_bytes()
        assert hashlib.sha256((destination / relative).read_bytes()).hexdigest() == expected
    assert json.loads((destination / 'manifest.json').read_text()) == manifest


def test_bundle_preserves_and_verifies_corpus_sidecars(frozen, tmp_path, helper):
    run, manifest, _ = frozen
    identity = {'missing_families': ['missing'], 'solver_inputs': []}
    selection = {'identity': identity, 'selection_id': cluster.digest(identity)}
    original = {'selection_id': 'parent', 'input_errors': ['missing_input']}
    manifest['corpus'] = {
        'selection_id': selection['selection_id'],
        'selection_digest': cluster.digest(selection),
        'original_selection_digest': cluster.digest(original)}
    write_json(run / 'manifest.json', manifest)
    write_json(run / 'corpus_selection.json', selection)
    write_json(run / 'original_corpus_selection.json', original)
    destination = tmp_path / 'bundle'
    transport = cluster.build_bundle(run, destination)
    assert helper['verify'](destination) == transport
    assert len(transport['files']) == 7
    assert json.loads((destination / 'original_corpus_selection.json').read_text()) == original
    write_json(run / 'original_corpus_selection.json', {'selection_id': 'parent', 'input_errors': []})
    with pytest.raises(ValueError, match='Corpus'):
        cluster.build_bundle(run, tmp_path / 'damaged')


@pytest.mark.parametrize('relative', [
    'source/scripts/codex/pilot.py', 'target.json', 'graphs/fixture.json', 'TASK'])
def test_bundle_rejects_changed_inputs(frozen, tmp_path, relative):
    run, _, task = frozen
    if relative == 'TASK':
        relative = 'tasks/' + task['task_id'] + '.json'
        value = dict(task, timeout=5)
    elif relative.endswith('.json'):
        value = {'nodes': [1], 'edges': [], 'metadata': {}}
    else:
        value = 'changed'
    (run / relative).write_text(json.dumps(value))
    with pytest.raises(ValueError):
        cluster.build_bundle(run, tmp_path / 'bundle')


@pytest.mark.parametrize('directory', ['results', 'worker_results', 'claims'])
def test_bundle_does_not_repeat_attempted_runs(frozen, tmp_path, directory):
    run, _, _ = frozen
    write_json(run / directory / 'record.json', {})
    with pytest.raises(ValueError, match='already attempted'):
        cluster.build_bundle(run, tmp_path / 'bundle')


def test_bundle_rejects_symlinked_ancestor(frozen, tmp_path):
    run, _, _ = frozen
    (run / 'graphs').rename(run / 'actual-graphs')
    (run / 'graphs').symlink_to(run / 'actual-graphs', target_is_directory=True)
    with pytest.raises(ValueError, match='Symlinks'):
        cluster.build_bundle(run, tmp_path / 'bundle')


def test_remote_records_are_json_and_transport_detects_damage(frozen, tmp_path, helper):
    run, _, _ = frozen
    path = tmp_path / 'record.json'
    helper['save'](path, {'ok': True})
    assert json.loads(path.read_text()) == {'ok': True}
    destination = tmp_path / 'bundle'
    cluster.build_bundle(run, destination)
    (destination / 'target.json').write_text('{}')
    with pytest.raises(RuntimeError, match='Input changed'):
        helper['verify'](destination)


@pytest.mark.parametrize('invalid', [None, 'unfinalized', 'wrong_task'])
def test_status_counts_only_matching_finalized_results(frozen, helper, monkeypatch, invalid):
    run, _, task = frozen
    record = dict(task, status='SUCCESS', controller_finalized=True)
    if invalid == 'unfinalized':
        record.pop('controller_finalized')
    elif invalid == 'wrong_task':
        record['seed'] = 99
    write_json(run / 'results' / (task['task_id'] + '.json'), record)
    monkeypatch.setattr(helper['subprocess'], 'run', lambda *args, **kwargs:
                        SimpleNamespace(stdout='', returncode=1))
    if invalid:
        with pytest.raises(RuntimeError, match='Invalid terminal result'):
            helper['state'](run)
    else:
        result = helper['state'](run)
        assert result['finalized'] == result['planned'] == 1
        assert result['statuses'] == {'SUCCESS': 1}


def test_ssh_namespace_is_fresh_short_and_applies_to_jump():
    first, second = cluster.SSH('hyde03'), cluster.SSH('hyde03')
    try:
        assert first.config != second.config
        config = first.config.read_text()
        assert 'Host *\n' in config
        assert 'ControlMaster no' in config
        assert 'ProxyJump dabh@hyde01.dabh.io' in config
        assert len(str(first.config.parent / ('x' * 40))) < 104
        assert first.command == ['ssh', '-F', str(first.config)]
    finally:
        first.temp.cleanup()
        second.temp.cleanup()
