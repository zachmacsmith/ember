"""Regressions for benchmark inputs; avoid confusing harness bugs with failure."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import time

import dwave_networkx as dnx
import numpy as np
import pytest


spec = importlib.util.spec_from_file_location(
    'codex_pilot', Path(__file__).resolve().parents[1] / 'scripts/codex/pilot.py')
pilot = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pilot)


def test_serialized_zephyr_retains_topology_and_layout_inputs():
    original = dnx.zephyr_graph(2)
    record = json.loads(json.dumps(pilot.graph_record(original)))
    restored = pilot.graph_from_record(record)
    assert set(restored) == set(original)
    assert set(restored.edges) == set(original.edges)
    assert restored.graph == original.graph
    positions = dnx.zephyr_layout(restored)
    expected = dnx.zephyr_layout(original)
    for q in original:
        assert tuple(restored.nodes[q]['zephyr_index']) == original.nodes[q]['zephyr_index']
        np.testing.assert_allclose(positions[q], expected[q])
    assert pilot.digest(pilot.graph_record(restored)) == pilot.digest(record)


def test_independent_validator_checks_all_source_edges_and_target_membership():
    import networkx as nx
    source = nx.path_graph(3)
    target = nx.path_graph(5)
    assert pilot.verify_embedding({0: [0], 1: [1, 2, 3], 2: [4]}, source, target) is None
    assert pilot.verify_embedding({0: [0], 1: [1], 2: [4]}, source, target) == 'missing_logical_edge'
    assert pilot.verify_embedding({0: [0], 1: [1], 2: [9]}, source, target) == 'membership_or_overlap'


def test_task_identity_detects_changes_to_config():
    manifest = {'source_snapshot': 'abc', 'target_hash': 'def'}
    task = dict(manifest, config={'beam_width': 4})
    task_id = pilot.digest(task)[:24]
    task['task_id'] = task_id
    pilot.check_task(task, task_id, manifest)
    task['config']['beam_width'] = 8
    with pytest.raises(RuntimeError, match='Task identity'):
        pilot.check_task(task, task_id, manifest)


def test_surviving_worker_holds_lock_and_resume_preserves_observation(tmp_path):
    """Kill the controller while its worker lives: resume must not duplicate it."""
    for name in ('source/scripts/codex', 'tasks', 'results', 'worker_results', 'claims', 'logs', 'jit_cache'):
        (tmp_path / name).mkdir(parents=True)
    child = tmp_path / 'source/scripts/codex/pilot.py'
    child.write_text('''import json, pathlib, sys, time
task_path = pathlib.Path(sys.argv[2])
run = task_path.parent.parent
task = json.loads(task_path.read_text())
with (run / 'starts').open('a') as stream:
    stream.write('started\\n')
end = time.monotonic() + 5
while not (run / 'release').exists() and time.monotonic() < end:
    time.sleep(0.01)
(run / 'worker_results' / task_path.name).write_text(json.dumps(dict(task, status='FAILURE')))
''')
    manifest = {'format_version': 2, 'source_files': {}, 'source_snapshot': 'abc',
                'target_hash': 'def', 'candidate_python': sys.executable,
                'mm_python': sys.executable}
    task = {'graph': 'test', 'method': 'native', 'seed': 0, 'config': {}, 'timeout': 3,
            'source_hash': 'ghi', 'source_snapshot': 'abc', 'target_hash': 'def'}
    task_id = pilot.digest(task)[:24]
    task['task_id'] = task_id
    manifest['tasks'] = [task_id]
    (tmp_path / 'manifest.json').write_text(json.dumps(manifest))
    (tmp_path / 'tasks' / (task_id + '.json')).write_text(json.dumps(task))
    command = [sys.executable, str(Path(pilot.__file__)), 'run', str(tmp_path)]
    controller = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        end = time.monotonic() + 4
        while not (tmp_path / 'starts').exists() and time.monotonic() < end:
            time.sleep(0.01)
        assert (tmp_path / 'starts').exists()
        controller.terminate()
        controller.communicate(timeout=3)
        refused = subprocess.run(command, capture_output=True, text=True, timeout=3)
        assert refused.returncode != 0
        assert 'currently holds this run lock' in refused.stderr
        (tmp_path / 'release').touch()
        end = time.monotonic() + 4
        while time.monotonic() < end:
            resumed = subprocess.run(command, capture_output=True, text=True, timeout=3)
            if resumed.returncode == 0:
                break
            assert 'currently holds this run lock' in resumed.stderr
            time.sleep(0.01)
        assert resumed.returncode == 0, resumed.stderr
        result = json.loads((tmp_path / 'results' / (task_id + '.json')).read_text())
        assert result['status'] == 'FAILURE'
        assert result['controller_finalized'] and result['controller_interrupted']
        assert result['process_wall'] is None and result['returncode'] is None
        assert (tmp_path / 'starts').read_text().splitlines() == ['started']
        assert subprocess.run(command, capture_output=True, timeout=3).returncode == 0
        assert (tmp_path / 'starts').read_text().splitlines() == ['started']
    finally:
        (tmp_path / 'release').touch()
        if controller.poll() is None:
            controller.terminate()
            controller.communicate(timeout=3)
