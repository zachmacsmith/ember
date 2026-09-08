"""Supplement provenance survives the runner path; all outcomes are inert fixtures."""
import ast
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import sys
from types import SimpleNamespace

import networkx as nx
import pytest


ROOT = Path(__file__).parents[1]
METHODS = ['mm', 'native-search-joint1-contacts', 'native-search-joint1-contacts-spectral']


def module_from(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def setup(tmp_path, monkeypatch):
    # A tiny inert repository avoids copying or running candidate implementations.
    repo = tmp_path / 'repo'
    scripts = repo / 'scripts/codex'
    scripts.mkdir(parents=True)
    for name in ('pilot.py', 'sudoku_supplement.py'):
        shutil.copy2(ROOT / 'scripts/codex' / name, scripts / name)
    package = repo / 'packages/ember-qc/src/ember_qc'
    package.mkdir(parents=True)
    (package / '__init__.py').write_text('# Inert test source, no embedding implementation.\n')
    pilot = module_from(scripts / 'pilot.py', 'fixture_supplement_pilot')
    generator = module_from(scripts / 'sudoku_supplement.py', 'fixture_supplement_generator')
    inherited = tmp_path / 'inherited.json'
    inherited.write_text(json.dumps({'graphs': [{'id': 37900, 'n': 6561}, {'id': 37901, 'n': 65536}]}))
    protocol = tmp_path / 'protocol.md'
    protocol.write_text('Only q2 and q3 development. q4 and q5 remain reserved.\n')
    source = tmp_path / 'supplement'
    generator.freeze_supplement(source, manifest_path=inherited, protocol_path=protocol)
    monkeypatch.setattr(pilot.subprocess, 'check_output', lambda *args, **kwargs: 'fixture-revision\n')
    import dwave_networkx as dnx
    monkeypatch.setattr(dnx, 'zephyr_graph', lambda *args, **kwargs: nx.path_graph(2))
    args = SimpleNamespace(run=str(tmp_path / 'run'), input_supplement=str(source), corpus_selection=None,
                           graphs=None, methods=','.join(METHODS), seeds=1, timeout=60.0,
                           candidate_python='/fixture/native/bin/python', mm_python='/fixture/mm/bin/python')
    return pilot, source, args


@pytest.fixture
def frozen(setup):
    pilot, source, args = setup
    pilot.initialize(args)
    run = Path(args.run)
    manifest = json.loads((run / 'manifest.json').read_bytes())
    return pilot, source, run, manifest


def save_manifest(pilot, run, manifest):
    pilot.write_json(run / 'manifest.json', manifest)


def replace_task(pilot, run, manifest, index, **changes):
    old_id = manifest['tasks'][index]
    path = run / 'tasks' / (old_id + '.json')
    task = json.loads(path.read_bytes())
    task.update(changes)
    task.pop('task_id')
    task['task_id'] = pilot.digest(task)[:24]
    path.unlink()
    pilot.write_json(run / 'tasks' / (task['task_id'] + '.json'), task)
    manifest['tasks'][index] = task['task_id']
    save_manifest(pilot, run, manifest)
    return task


def finalized_failure_fixtures(pilot, run, manifest):
    for task_id in manifest['tasks']:
        task = json.loads((run / 'tasks' / (task_id + '.json')).read_bytes())
        # Deliberately no embeddings or quality metrics: these are synthetic failures.
        pilot.write_json(run / 'results' / (task_id + '.json'),
                         dict(task, status='TIMEOUT', controller_finalized=True,
                              host='fixture-host', solver_wall=60.0, process_wall=61.0,
                              returncode=0, fixture_only=True))


def analyzer(monkeypatch, pilot):
    monkeypatch.setitem(sys.modules, 'pilot', pilot)
    return module_from(ROOT / 'scripts/codex/analyze_pilot.py', 'fixture_supplement_analysis')


def cluster_module():
    return module_from(ROOT / 'scripts/codex/cluster.py', 'fixture_supplement_cluster')


def remote_definitions(cluster):
    tree = ast.parse(cluster.REMOTE_HELPER)
    definitions = ast.Module(body=[node for node in tree.body
                                  if isinstance(node, (ast.Import, ast.ImportFrom, ast.FunctionDef))],
                             type_ignores=[])
    namespace = {}
    exec(compile(definitions, '<inert remote helper definitions>', 'exec'), namespace)
    return namespace


def test_init_freezes_complete_six_trial_matrix_and_plain_graphs(frozen):
    pilot, source, run, manifest = frozen
    checked = pilot.check_supplement_provenance(run, manifest)
    assert len(manifest['tasks']) == 6
    assert 'corpus' not in manifest
    descriptor = manifest['input_supplement']
    assert descriptor['methods'] == METHODS and descriptor['seeds'] == [0]
    assert descriptor['timeout'] == 60.0
    assert descriptor['comparison_plan_id'] == pilot._supplement_plan_id(descriptor)
    assert len(checked['entries']) == 2
    assert 'scripts/codex/sudoku_supplement.py' in manifest['source_files']
    assert (run / 'source/scripts/codex/sudoku_supplement.py').read_bytes() == (
        source / 'source/sudoku_supplement.py').read_bytes()
    for relative, expected in descriptor['bundle_files'].items():
        raw = (run / 'input_supplement' / relative).read_bytes()
        assert raw == (source / relative).read_bytes()
        assert hashlib.sha256(raw).hexdigest() == expected
    matrix = set()
    for task_id in manifest['tasks']:
        task = json.loads((run / 'tasks' / (task_id + '.json')).read_bytes())
        pilot.check_task(task, task_id, manifest)
        assert task['input_supplement_id'] == descriptor['supplement_id']
        assert task['supplement_graph_id'] in (1000002, 1000003)
        assert task['config'] == pilot.CONFIGS[task['method']]
        assert not {'family', 'box_order', 'board_side', 'supplement_graph_id'} & set(task['config'])
        graph = json.loads((run / 'graphs' / (task['graph'] + '.json')).read_bytes())
        assert pilot.graph_record(pilot.graph_from_record(graph)) == graph
        assert graph['metadata'] == {}
        assert all(attrs == {} for _, attrs in graph['node_attributes'])
        assert all(attrs == {} for _, _, attrs in graph['edge_attributes'])
        matrix.add((task['supplement_graph_id'], task['method'], task['seed']))
    assert matrix == {(gid, method, 0) for gid in (1000002, 1000003) for method in METHODS}


def test_mutable_original_is_not_used_after_initialization(frozen):
    pilot, source, run, manifest = frozen
    shutil.rmtree(source)
    assert len(pilot.check_supplement_provenance(run, manifest)['entries']) == 2


@pytest.mark.parametrize('defect', ['subset', 'both_input_paths'])
def test_selection_errors_fail_before_run_creation(setup, defect):
    pilot, _, args = setup
    if defect == 'subset':
        args.graphs = 'sudoku_supplement_v1_q2'
    else:
        args.corpus_selection = 'also-specified.json'
    with pytest.raises(ValueError):
        pilot.initialize(args)
    assert not Path(args.run).exists()


def test_cli_input_paths_are_mutually_exclusive(setup, monkeypatch):
    pilot, source, args = setup
    monkeypatch.setattr(sys, 'argv', ['pilot.py', 'init', args.run,
                                     '--input-supplement', str(source), '--corpus-selection', 'another.json'])
    with pytest.raises(SystemExit) as error:
        pilot.main()
    assert error.value.code == 2 and not Path(args.run).exists()


def test_old_builtin_init_needs_no_new_argument_or_supplement_loader(setup, monkeypatch):
    pilot, _, args = setup
    del args.input_supplement
    monkeypatch.setattr(pilot, 'make_graphs', lambda: {'old_fixture': nx.path_graph(3)})
    pilot.initialize(args)
    manifest = json.loads((Path(args.run) / 'manifest.json').read_bytes())
    assert 'input_supplement' not in manifest
    assert 'scripts/codex/sudoku_supplement.py' not in manifest['source_files']
    assert pilot.check_supplement_provenance(Path(args.run), manifest) is None
    for task_id in manifest['tasks']:
        task = json.loads((Path(args.run) / 'tasks' / (task_id + '.json')).read_bytes())
        assert not any('supplement' in key for key in task)


@pytest.mark.parametrize('relative', ['provenance/1000002.json', 'provenance/original_sudoku_entries.json',
                                     'source/generalization_protocol.md', 'source/sudoku_supplement.py',
                                     'graphs/1000003.json', 'manifest.json'])
@pytest.mark.parametrize('defect', ['missing', 'modified'])
def test_controller_and_analyzer_reject_bundle_damage_before_work(frozen, monkeypatch, relative, defect):
    pilot, _, run, manifest = frozen
    path = run / 'input_supplement' / relative
    if defect == 'missing':
        path.unlink()
    else:
        path.write_bytes(path.read_bytes() + b' ')
    calls = []
    monkeypatch.setattr(pilot.subprocess, 'Popen', lambda *args, **kwargs: calls.append(args))
    with pytest.raises((ValueError, FileNotFoundError)):
        pilot.execute(SimpleNamespace(run=str(run)))
    assert calls == [] and list((run / 'results').iterdir()) == []
    with pytest.raises((ValueError, FileNotFoundError)):
        analyzer(monkeypatch, pilot).checked_run(run)


@pytest.mark.parametrize('defect', ['one_trial_missing', 'whole_source_missing', 'duplicate_task',
                                   'source_id', 'supplement_id', 'configuration', 'timeout', 'plan_id'])
def test_complete_trial_plan_detects_missingness_and_misbound_tasks(frozen, defect):
    pilot, _, run, manifest = frozen
    if defect == 'one_trial_missing':
        manifest['tasks'].pop()
        save_manifest(pilot, run, manifest)
    elif defect == 'whole_source_missing':
        manifest['tasks'] = [tid for tid in manifest['tasks'] if json.loads(
            (run / 'tasks' / (tid + '.json')).read_bytes())['supplement_graph_id'] == 1000002]
        save_manifest(pilot, run, manifest)
    elif defect == 'duplicate_task':
        manifest['tasks'].append(manifest['tasks'][0])
        save_manifest(pilot, run, manifest)
    else:
        changes = {'source_id': {'supplement_graph_id': 37900},
                   'supplement_id': {'input_supplement_id': 'other'},
                   'configuration': {'config': {'family_hint': 'sudoku'}},
                   'timeout': {'timeout': 10},
                   'plan_id': {'input_supplement_plan_id': 'other'}}[defect]
        replace_task(pilot, run, manifest, 0, **changes)
    with pytest.raises((ValueError, RuntimeError)):
        pilot.check_supplement_provenance(run, manifest)


def test_comparison_plan_cannot_be_shrunk_without_breaking_task_binding(frozen):
    pilot, _, run, manifest = frozen
    descriptor = manifest['input_supplement']
    descriptor['methods'].remove('mm')
    descriptor['configurations'].pop('mm')
    descriptor['comparison_plan_id'] = pilot._supplement_plan_id(descriptor)
    manifest['tasks'] = [tid for tid in manifest['tasks'] if json.loads(
        (run / 'tasks' / (tid + '.json')).read_bytes())['method'] != 'mm']
    save_manifest(pilot, run, manifest)
    with pytest.raises(RuntimeError, match='supplement provenance'):
        pilot.check_supplement_provenance(run, manifest)


@pytest.mark.parametrize('defect', ['modified_loader', 'missing_loader_identity', 'source_hint', 'mixed_corpus'])
def test_validator_rejects_loader_or_source_boundary_changes(frozen, defect):
    pilot, _, run, manifest = frozen
    if defect == 'modified_loader':
        (run / 'source/scripts/codex/sudoku_supplement.py').write_text('raise AssertionError("must not execute")')
    elif defect == 'missing_loader_identity':
        manifest['source_files'].pop('scripts/codex/sudoku_supplement.py')
        manifest['source_snapshot'] = pilot.digest(manifest['source_files'])
    elif defect == 'source_hint':
        path = run / 'graphs/sudoku_supplement_v1_q2.json'
        graph = json.loads(path.read_bytes())
        graph['metadata'] = {'family': 'sudoku'}
        pilot.write_json(path, graph)
    else:
        manifest['corpus'] = {}
    with pytest.raises(ValueError):
        pilot.check_supplement_provenance(run, manifest)


def test_transport_and_retrieved_copy_preserve_all_provenance(frozen, tmp_path, monkeypatch):
    pilot, _, run, manifest = frozen
    cluster = cluster_module()
    destination = tmp_path / 'transport-fixture'
    transport = cluster.build_bundle(run, destination)
    remote = remote_definitions(cluster)
    assert remote['verify'](destination) == transport
    for relative in manifest['input_supplement']['bundle_files']:
        shipped = 'input_supplement/' + relative
        assert shipped in transport['files']
        assert (destination / shipped).read_bytes() == (run / shipped).read_bytes()
    assert 'source/scripts/codex/sudoku_supplement.py' in transport['files']
    retrieved = tmp_path / 'retrieved-fixture'
    shutil.copytree(destination, retrieved)
    (retrieved / 'results').mkdir()
    finalized_failure_fixtures(pilot, retrieved, manifest)
    assert len(pilot.check_supplement_provenance(retrieved, manifest)['entries']) == 2
    analysis = analyzer(monkeypatch, pilot)
    _, outcomes = analysis.checked_run(retrieved)
    assert len(outcomes) == 6 and all(row['status'] == 'TIMEOUT' for row in outcomes)
    analysis.report(retrieved, retrieved / 'analysis')
    summary = json.loads((retrieved / 'analysis/summary.json').read_bytes())
    provenance = json.loads((retrieved / 'analysis/input_provenance.json').read_bytes())
    assert summary['input_supplement'] == provenance
    assert sorted(p['id'] for p in provenance['sources'].values()) == [1000002, 1000003]
    assert all(p['embedding_feasibility'] == 'unproved' for p in provenance['sources'].values())
    assert all(row['acl_mean'] is None for row in summary['per_input'])
    assert all(row['acl_sample_variance'] is None for row in summary['per_input'])
    damaged = retrieved / 'input_supplement/provenance/1000003.json'
    damaged.write_bytes(damaged.read_bytes() + b' ')
    with pytest.raises(RuntimeError, match='Input changed'):
        remote['verify'](retrieved)
    with pytest.raises(ValueError):
        analysis.checked_run(retrieved)


def test_transfer_rejects_sidecar_corruption_or_missingness(frozen, tmp_path):
    _, _, run, _ = frozen
    (run / 'input_supplement/provenance/1000003.json').unlink()
    with pytest.raises(ValueError):
        cluster_module().build_bundle(run, tmp_path / 'transport-fixture')


def test_analyzer_requires_every_planned_terminal_result(frozen, monkeypatch):
    pilot, _, run, manifest = frozen
    finalized_failure_fixtures(pilot, run, manifest)
    (run / 'results' / (manifest['tasks'][-1] + '.json')).unlink()
    with pytest.raises(ValueError, match='incomplete'):
        analyzer(monkeypatch, pilot).checked_run(run)


def test_task_result_provenance_must_survive_controller_finalization(frozen, monkeypatch):
    pilot, _, run, manifest = frozen
    finalized_failure_fixtures(pilot, run, manifest)
    path = run / 'results' / (manifest['tasks'][0] + '.json')
    result = json.loads(path.read_bytes())
    result.pop('input_supplement_id')
    pilot.write_json(path, result)
    with pytest.raises(RuntimeError, match='Result identity'):
        analyzer(monkeypatch, pilot).checked_run(run)


def test_worker_preserves_provenance_when_guard_stops_before_solver_import(frozen, monkeypatch):
    pilot, _, run, manifest = frozen
    task = next(json.loads((run / 'tasks' / (tid + '.json')).read_bytes())
                for tid in manifest['tasks']
                if json.loads((run / 'tasks' / (tid + '.json')).read_bytes())['method'] != 'mm')
    monkeypatch.setattr(pilot.signal, 'signal', lambda *args: None)
    monkeypatch.setattr(pilot.signal, 'alarm', lambda *args: None)
    monkeypatch.setattr(pilot.sys, 'path', list(pilot.sys.path))
    # Force the existing dependency guard to reject immediately. No solver can run.
    monkeypatch.setattr(pilot.importlib.util, 'find_spec', lambda name: object())
    pilot.worker(str(run / 'tasks' / (task['task_id'] + '.json')))
    result = json.loads((run / 'worker_results' / (task['task_id'] + '.json')).read_bytes())
    assert result['status'] == 'ERROR' and 'prohibited embedding package' in result['error']
    pilot.check_result(result, task)
    assert result['input_supplement_id'] == manifest['input_supplement']['supplement_id']
    assert result['input_supplement_plan_id'] == manifest['input_supplement']['comparison_plan_id']
    assert 'embedding' not in result
