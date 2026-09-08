"""Small adapter checks; no actual constructor, corpus or MM invocation."""
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

import networkx as nx
import pytest

ROOT = Path(__file__).resolve().parents[1]
PILOT_PATH = ROOT / 'scripts/codex/pilot.py'
NATIVE_PYTHON = ROOT / '.venv/codex-native/bin/python'
spec = importlib.util.spec_from_file_location('_constructor_pilot_test', PILOT_PATH)
pilot = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pilot)


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, sort_keys=True)+'\n')


def bundle(tmp_path, method, body, timeout=1.0):
    run = tmp_path/'run'
    run.mkdir()
    for name in ('tasks','worker_results','graphs'):
        (run/name).mkdir()
    relative, function = pilot.CONSTRUCTORS[method]
    source_path = run/'source'/relative
    source_path.parent.mkdir(parents=True)
    source_path.write_text('def '+function+'(source,target,*,seed,timeout,deadline):\n'+
                           '\n'.join('    '+line for line in body.splitlines())+'\n')
    files = {relative:hashlib.sha256(source_path.read_bytes()).hexdigest()}
    source = nx.Graph([(0,1)])
    target = nx.Graph([(10,11),(11,12)])
    source_data, target_data = pilot.graph_record(source), pilot.graph_record(target)
    write(run/'graphs/tiny.json',source_data)
    write(run/'target.json',target_data)
    snapshot = pilot.digest(files)
    task = dict(graph='tiny',source_hash=pilot.digest(source_data),target_hash=pilot.digest(target_data),
                source_snapshot=snapshot,method=method,config=pilot.method_config(method),seed=7,timeout=timeout)
    task['task_id'] = pilot.digest(task)[:24]
    write(run/'tasks'/(task['task_id']+'.json'),task)
    manifest = dict(source_files=files,source_snapshot=snapshot,target_hash=task['target_hash'])
    write(run/'manifest.json',manifest)
    return run,task,manifest,source_path


def execute(run, task, prohibited=()):
    completed = subprocess.run([str(NATIVE_PYTHON),'-I','-B',str(PILOT_PATH),'worker',
        str(run/'tasks'/(task['task_id']+'.json'))],capture_output=True,text=True,timeout=8)
    assert completed.returncode == 0, completed.stderr
    row = json.loads((run/'worker_results'/(task['task_id']+'.json')).read_text())
    assert row['forbidden_import_attempts'] == list(prohibited)
    assert row['loaded_embedding_libraries'] == []
    return row


@pytest.mark.parametrize('method',('native-reduced-core','native-reduced-core-repair','native-original-soft-guide','demand-tree','frontier-tree','frontier-tree-bounded','frontier-tree-reinsert','propagating-tree','propagating-tree-reuse','propagating-tree-growth','propagating-tree-matching','propagating-tree-ports','multilevel-regions','multilevel-regions-v2','quotient-reconfiguration','quotient-compact','quotient-vacancy','quotient-distinct'))
def test_constructor_worker_deadline_and_output(tmp_path,method):
    run,task,manifest,path = bundle(tmp_path,method,
        "import time\nassert seed == 7 and 0 < deadline-time.perf_counter() <= timeout\n"
        "return {'embedding':{0:[10,11],1:[12]},'status':'SUCCESS',"
        "'diag':{'received_deadline':deadline,'constructor_name':__name__}}")
    row = execute(run,task)
    assert row['status'] == 'SUCCESS' and row['embedding_valid']
    assert row['qubits'] == 3 and row['acl'] == 1.5
    assert row['implementation_path'] == str(path.resolve())
    assert row['diag']['constructor_name'].startswith('_codex_pilot_constructor_')
    assert row['solver_wall'] < task['timeout']
    assert row['diag']['received_deadline'] > 0


def test_mutating_constructor_cannot_change_original_validation(tmp_path):
    run,task,_,_ = bundle(tmp_path,'demand-tree',
        "source.remove_edge(0,1)\ntarget.add_edge(10,12)\n"
        "return {'embedding':{0:[10],1:[12]},'status':'SUCCESS','diag':{}}")
    row = execute(run,task)
    assert row['status'] == 'INVALID_OUTPUT' and not row['embedding_valid']
    assert row['validation_error'] == 'missing_logical_edge'
    assert 'qubits' not in row and row['diagnostic_quality'] == {}


def test_late_valid_constructor_has_diagnostic_quality_only(tmp_path):
    run,task,_,_ = bundle(tmp_path,'multilevel-regions',
        "import time\ntime.sleep(.03)\n"
        "return {'embedding':{0:[10,11],1:[12]},'status':'SUCCESS','diag':{}}",timeout=.01)
    row = execute(run,task)
    assert row['status'] == 'TIMEOUT' and row['embedding_valid']
    assert row['deadline_overrun'] > 0 and 'qubits' not in row
    assert row['diagnostic_quality']['qubits'] == 3


def test_constructor_corruption_is_rejected_before_execution(tmp_path):
    run,task,manifest,path = bundle(tmp_path,'demand-tree',"raise AssertionError('must not execute')")
    path.write_text(path.read_text()+'# mutation\n')
    with pytest.raises(RuntimeError,match='source hash mismatch'):
        pilot.load_constructor(run,manifest,'demand-tree')


def test_constructor_cannot_hide_prohibited_import_attempt(tmp_path):
    run,task,_,_ = bundle(tmp_path,'demand-tree',
        "try:\n    import busclique\nexcept ImportError:\n    pass\n"
        "return {'embedding':{0:[10,11],1:[12]},'status':'SUCCESS','diag':{}}")
    row = execute(run,task,prohibited=('busclique',))
    assert row['status'] == 'DEPENDENCY_VIOLATION'
    assert row['loaded_embedding_libraries'] == []
    assert 'qubits' not in row and row['diagnostic_quality']['qubits'] == 3


def test_constructor_unknown_and_noncallable_entrypoints(tmp_path):
    with pytest.raises(KeyError):
        pilot.method_config('unknown-constructor')
    run,task,manifest,path = bundle(tmp_path,'multilevel-regions','return {}')
    path.write_text('multilevel_embed = 3\n')
    relative = pilot.CONSTRUCTORS['multilevel-regions'][0]
    manifest['source_files'][relative] = hashlib.sha256(path.read_bytes()).hexdigest()
    with pytest.raises(TypeError,match='not callable'):
        pilot.load_constructor(run,manifest,'multilevel-regions')


def test_config_lookup_preserves_historical_registry():
    assert not set(pilot.CONSTRUCTORS) & set(pilot.CONFIGS)
    for method,config in pilot.CONFIGS.items():
        assert pilot.method_config(method) is config
    for method in pilot.CONSTRUCTORS:
        first = pilot.method_config(method)
        assert first == {}
        first['unexpected'] = 1
        assert pilot.method_config(method) == {}
