"""Reproducible local/remote screening, with one isolated process per trial.

This is a development experiment, not a confirmatory benchmark or an algorithm
portfolio. Every method has its own row and independent input. Candidates never
receive comparator embeddings. All graph inputs and Python sources are frozen
before execution; immutable task files allow reconnect/resume without rerunning
completed tasks. Run the controller under a detached remote session for persistence.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.abc
import importlib.metadata
import importlib.util
import json
import math
import os
from pathlib import Path
import platform
import random
import resource
import shutil
import signal
import subprocess
import sys
import time
import traceback

ROOT = Path(__file__).resolve().parents[2]


def write_json(path, value):
    path = Path(path)
    temp = path.with_name(path.name + f'.tmp-{os.getpid()}')
    temp.write_text(json.dumps(value, sort_keys=True, indent=2, default=_json_scalar) + '\n')
    os.replace(temp, path)


def _json_scalar(value):
    if hasattr(value, 'item'):
        return value.item()
    if isinstance(value, (set, tuple)):
        return list(value)
    raise TypeError(type(value).__name__)


def graph_record(graph):
    return {'nodes': sorted(graph),
            'edges': sorted([min(a, b), max(a, b)] for a, b in graph.edges()),
            'node_attributes': [[v, dict(graph.nodes[v])] for v in sorted(graph)],
            'edge_attributes': [[a, b, dict(graph.edges[a, b])]
                                for a, b in sorted((min(a, b), max(a, b))
                                                   for a, b in graph.edges())],
            'metadata': dict(graph.graph)}


def graph_from_record(record):
    import networkx as nx
    graph = nx.Graph()
    graph.add_nodes_from(record['nodes'])
    graph.add_edges_from(record['edges'])
    for vertex, attributes in record.get('node_attributes', []):
        graph.nodes[vertex].update(attributes)
    for a, b, attributes in record.get('edge_attributes', []):
        graph.edges[a, b].update(attributes)
    graph.graph.update(record['metadata'])
    return graph


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def check_task(task, task_id, manifest):
    payload = {key: value for key, value in task.items() if key != 'task_id'}
    if task.get('task_id') != task_id or digest(payload)[:24] != task_id:
        raise RuntimeError(f'Task identity mismatch: {task_id}')
    if (task['source_snapshot'] != manifest['source_snapshot']
            or task['target_hash'] != manifest['target_hash']):
        raise RuntimeError(f'Task provenance mismatch: {task_id}')


def check_result(outcome, task):
    for key in task:
        if outcome.get(key) != task[key]:
            raise RuntimeError(f'Result identity mismatch: {task["task_id"]}: {key}')
    if not outcome.get('status'):
        raise RuntimeError(f'Result has no status: {task["task_id"]}')


def verify_embedding(embedding, source, target):
    """Independent plain-graph validator, without solver-reported trust inputs."""
    if not isinstance(embedding, dict) or set(embedding) != set(source):
        return 'source_coverage'
    used = set()
    sets = {}
    for v, chain in embedding.items():
        if not chain or len(set(chain)) != len(chain):
            return 'empty_or_duplicate_chain'
        group = set(chain)
        if not group <= set(target) or used & group:
            return 'membership_or_overlap'
        used.update(group)
        reached = {chain[0]}
        frontier = [chain[0]]
        for q in frontier:
            for neighbor in target[q]:
                if neighbor in group and neighbor not in reached:
                    reached.add(neighbor)
                    frontier.append(neighbor)
        if reached != group:
            return 'disconnected_chain'
        sets[v] = group
    if any(not any(b in sets[v] for a in sets[u] for b in target[a]) for u, v in source.edges()):
        return 'missing_logical_edge'
    return None


class NoExternalEmbedder(importlib.abc.MetaPathFinder):
    def __init__(self):
        self.attempts = []

    def find_spec(self, fullname, path=None, target=None):
        first = fullname.split('.')[0].lower()
        if 'minorminer' in first or first == 'busclique':
            self.attempts.append(fullname)
            raise ImportError(f'Forbidden candidate dependency: {fullname}')


def worker(task_path):
    task = json.loads(Path(task_path).read_text())
    run = Path(task_path).parent.parent
    manifest = json.loads((run / 'manifest.json').read_text())
    check_task(task, Path(task_path).stem, manifest)
    # Kernel-enforced lifetime survives controller death, including a stuck
    # native extension. Unix platforms only, matching this cluster and macOS.
    signal.signal(signal.SIGALRM, signal.SIG_DFL)
    signal.alarm(math.ceil(task['timeout'] + 30))
    sys.path.insert(0, str(run / 'source/packages/ember-qc/src'))
    method = task['method']
    blocker = None
    output = {'task_id': task['task_id'], 'graph': task['graph'],
              'source_hash': task['source_hash'], 'target_hash': task['target_hash'],
              'source_snapshot': task['source_snapshot'], 'method': method,
              'config': task['config'], 'seed': task['seed'],
              'timeout': task['timeout'], 'host': platform.node(),
              'pid': os.getpid(), 'python': sys.version, 'status': 'ERROR',
              'python_executable': sys.executable, 'python_prefix': sys.prefix,
              'python_base_prefix': sys.base_prefix,
              'load_average_start': os.getloadavg(),
              'cpu_affinity': sorted(os.sched_getaffinity(0)) if hasattr(os, 'sched_getaffinity') else None,
              'machine': platform.uname()._asdict(),
              'jit_cache_policy': 'empty per-task cache; compilation charged to solver',
              'numba_cache_dir': os.environ.get('NUMBA_CACHE_DIR')}
    try:
        if method != 'mm':
            if any(importlib.util.find_spec(name) is not None
                   for name in ('minorminer', '_minorminer', 'busclique')):
                raise RuntimeError('Candidate environment contains a prohibited embedding package')
            blocker = NoExternalEmbedder()
            sys.meta_path.insert(0, blocker)
        def load_graph(path):
            record = json.loads(path.read_text())
            return graph_from_record(record), record
        source, source_data = load_graph(run / 'graphs' / (task['graph'] + '.json'))
        target, target_data = load_graph(run / 'target.json')
        if digest(source_data) != task['source_hash'] or digest(target_data) != task['target_hash']:
            raise RuntimeError('Input hash mismatch')
        packages = ('networkx', 'numpy', 'numba', 'dwave-networkx', 'minorminer', 'scipy')
        output['versions'] = {}
        for name in packages:
            try:
                output['versions'][name] = importlib.metadata.version(name)
            except importlib.metadata.PackageNotFoundError:
                output['versions'][name] = None
        # Both methods import their implementation before measurement. Fresh-process
        # startup is measured separately by the controller. JIT first-call cost stays
        # inside candidate time; any warm-cache reuse is recorded by per-task mode.
        if method == 'mm':
            import minorminer
            output['implementation_path'] = minorminer.__file__
            call = lambda: {'embedding': minorminer.find_embedding(
                source.copy(), target.copy(), random_seed=task['seed'], timeout=task['timeout'],
                **task['config'])}
        else:
            from ember_qc.algorithms.factored.native import native_embed
            implementation = Path(sys.modules[native_embed.__module__].__file__).resolve()
            if not implementation.is_relative_to(run / 'source'):
                raise RuntimeError(f'Candidate imported outside frozen source: {implementation}')
            output['implementation_path'] = str(implementation)
            call = lambda: native_embed(source.copy(), target.copy(), seed=task['seed'],
                                         timeout=task['timeout'], **task['config'])
        started, cpu_started = time.perf_counter(), time.process_time()
        response = call()
        output['solver_wall'] = time.perf_counter() - started
        output['solver_cpu'] = time.process_time() - cpu_started
        embedding = response.get('embedding', {})
        reason = verify_embedding(embedding, source, target)
        output['embedding_valid'] = reason is None
        output['validation_error'] = reason
        output['reported_status'] = response.get('status')
        output['diag'] = response.get('diag', {})
        output['error'] = response.get('error')
        late = output['solver_wall'] > task['timeout']
        output['deadline_overrun'] = max(0, output['solver_wall'] - task['timeout'])
        claimed = response.get('status', 'FAILURE')
        output['status'] = ('TIMEOUT' if late else 'SUCCESS' if reason is None else
                            'INVALID_OUTPUT' if claimed == 'SUCCESS' else claimed)
        output['embedding'] = {str(v): list(chain) for v, chain in embedding.items()}
        output['partial_embedding'] = response.get('partial_embedding')
        if reason is None:
            lengths = [len(embedding[v]) for v in source]
            output['qubits'] = sum(lengths)
            output['acl'] = sum(lengths) / len(source) if source else None
            output['max_chain'] = max(lengths, default=0)
            mean = output['acl'] or 0
            output['within_chain_variance'] = sum((n - mean) ** 2 for n in lengths) / len(lengths) if lengths else None
    except Exception as exc:
        output['error'] = f'{type(exc).__name__}: {exc}'
        output['traceback'] = traceback.format_exc()
    output['forbidden_import_attempts'] = blocker.attempts if blocker else []
    output['loaded_embedding_libraries'] = [name for name in sys.modules
        if 'minorminer' in name.split('.')[0].lower() or name.split('.')[0] == 'busclique']
    if method != 'mm' and (output['forbidden_import_attempts'] or output['loaded_embedding_libraries']):
        output['status'] = 'DEPENDENCY_VIOLATION'
    if output['status'] != 'SUCCESS':
        output['diagnostic_quality'] = {key: output.pop(key) for key in
            ('acl', 'qubits', 'max_chain', 'within_chain_variance') if key in output}
    peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    output['load_average_end'] = os.getloadavg()
    output['peak_rss_bytes'] = peak if sys.platform == 'darwin' else peak * 1024
    write_json(run / 'worker_results' / (task['task_id'] + '.json'), output)


def make_graphs():
    import networkx as nx
    graphs = {
        'complete_40': nx.complete_graph(40),
        'complete_100': nx.complete_graph(100),
        'bipartite_30_30': nx.complete_bipartite_graph(30, 30),
        'random_er_80_d8': nx.gnp_random_graph(80, 8/79, seed=81001),
        'regular_80_d3': nx.random_regular_graph(3, 80, seed=81002),
        'watts_strogatz_80': nx.watts_strogatz_graph(80, 4, 0.15, seed=81003),
        'grid_8x8': nx.grid_2d_graph(8, 8),
        'honeycomb_5x5': nx.hexagonal_lattice_graph(5, 5),
        'king_8x8': nx.strong_product(nx.path_graph(8), nx.path_graph(8)),
    }
    return {name: nx.convert_node_labels_to_integers(graph) for name, graph in graphs.items()}


CONFIGS = {
    'mm': {},
    'native-search': {'construction': 'search', 'max_asks': 1000, 'polish_passes': 0},
    'native-packed': {'construction': 'packed', 'order_strategy': 'random', 'polish_passes': 0},
    'native-packed-b4': {'construction': 'packed', 'order_strategy': 'random', 'polish_passes': 2,
                         'beam_width': 4, 'max_groups': 48},
    'native-packed-b1': {'construction': 'packed', 'order_strategy': 'random', 'polish_passes': 2,
                         'beam_width': 1, 'max_groups': 48},
    'native-search-b4': {'construction': 'search', 'max_asks': 1000, 'polish_passes': 2,
                         'beam_width': 4, 'max_groups': 48},
    'native-search-single': {'construction': 'search', 'max_asks': 1000, 'polish_passes': 4,
                            'beam_width': 1, 'max_groups': 512, 'polish_group_sizes': [1]},
    'native-search-joint1': {'construction': 'search', 'max_asks': 1000, 'polish_passes': 4,
                            'beam_width': 1, 'max_groups': 512, 'polish_group_sizes': [1, 2, 3, 4]},
    'native-search-joint4': {'construction': 'search', 'max_asks': 1000, 'polish_passes': 4,
                            'beam_width': 4, 'max_groups': 512, 'polish_group_sizes': [1, 2, 3, 4]},
}


def initialize(args):
    import dwave_networkx as dnx
    if not math.isfinite(args.timeout) or args.timeout <= 0 or args.seeds < 1:
        raise ValueError('timeout must be finite and positive; seeds must be positive')
    run = Path(args.run).resolve()
    run.mkdir(parents=True, exist_ok=False)
    for name in ('graphs', 'tasks', 'results', 'worker_results', 'claims', 'logs', 'source', 'jit_cache'):
        (run / name).mkdir()
    files = sorted((ROOT / 'packages/ember-qc/src/ember_qc').rglob('*.py'))
    files += [Path(__file__).resolve()]
    hashes = {}
    for original in files:
        relative = original.relative_to(ROOT)
        destination = run / 'source' / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(original, destination)
        hashes[str(relative)] = hashlib.sha256(original.read_bytes()).hexdigest()
    # Eager package imports require the graph manifest/presets even though the
    # pilot supplies its own graphs. Preserve these source inputs as well.
    library = ROOT / 'packages/ember-qc/src/ember_qc/graphs'
    for pattern in ('*.json', '*.csv'):
        for original in library.glob(pattern):
            relative = original.relative_to(ROOT)
            destination = run / 'source' / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(original, destination)
            hashes[str(relative)] = hashlib.sha256(original.read_bytes()).hexdigest()
    snapshot = digest(hashes)
    target = graph_record(dnx.zephyr_graph(12, 4))
    target_hash = digest(target)
    write_json(run / 'target.json', target)
    graphs = make_graphs()
    names = args.graphs.split(',') if args.graphs else list(graphs)
    methods = args.methods.split(',')
    for method in methods:
        if method not in CONFIGS:
            raise ValueError(method)
    tasks = []
    for name in names:
        record = graph_record(graphs[name])
        source_hash = digest(record)
        write_json(run / 'graphs' / (name + '.json'), record)
        for seed in range(args.seeds):
            order = list(methods)
            random.Random(f'{name}:{seed}').shuffle(order)
            for method in order:
                task = {'graph': name, 'source_hash': source_hash, 'target_hash': target_hash,
                        'source_snapshot': snapshot, 'seed': seed, 'method': method,
                        'config': CONFIGS[method], 'timeout': args.timeout}
                task['task_id'] = digest(task)[:24]
                tasks.append(task['task_id'])
                write_json(run / 'tasks' / (task['task_id'] + '.json'), task)
    revision = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    manifest = {'format_version': 2,
                'created_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
                'git_revision': revision, 'source_files': hashes, 'source_snapshot': snapshot,
                'target_hash': target_hash, 'tasks': tasks, 'purpose': 'development screening',
                # Resolving a venv python symlink bypasses pyvenv.cfg and silently
                # invokes the base interpreter without the pinned dependencies.
                'candidate_python': str(Path(args.candidate_python).absolute()),
                'mm_python': str(Path(args.mm_python).absolute()),
                'threads': 1, 'timing': 'fresh processes; empty per-task JIT cache; solver and whole-process wall times'}
    write_json(run / 'manifest.json', manifest)
    print(f'Created {len(tasks)} tasks in {run}', flush=True)


def execute(args):
    run = Path(args.run).resolve()
    manifest = json.loads((run / 'manifest.json').read_text())
    if manifest.get('format_version') != 2:
        raise RuntimeError('Initialize a new version-2 run; older artifacts are read-only')
    lock = run / 'controller.lock'
    # OS advisory lock is released on process death; stale file alone is not live.
    import fcntl
    lockfile = lock.open('a+')
    try:
        fcntl.flock(lockfile, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        raise SystemExit('A controller currently holds this run lock')
    for relative, expected in manifest['source_files'].items():
        if hashlib.sha256((run / 'source' / relative).read_bytes()).hexdigest() != expected:
            raise RuntimeError(f'Source changed: {relative}')
    write_json(run / 'controller.json', {'pid': os.getpid(), 'host': platform.node(),
                                       'started': time.time(), 'status': 'running'})
    env = os.environ.copy()
    for key in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMBA_NUM_THREADS'):
        env[key] = '1'
    env['PYTHONHASHSEED'] = '0'
    env['PYTHONPATH'] = str(run / 'source/packages/ember-qc/src')
    for task_id in manifest['tasks']:
        result_path = run / 'results' / (task_id + '.json')
        task_path = run / 'tasks' / (task_id + '.json')
        task = json.loads(task_path.read_text())
        check_task(task, task_id, manifest)
        if result_path.exists():
            outcome = json.loads(result_path.read_text())
            check_result(outcome, task)
            if not outcome.get('controller_finalized'):
                raise RuntimeError(f'Unfinalized terminal result: {task_id}')
            continue
        worker_result = run / 'worker_results' / (task_id + '.json')
        claim_path = run / 'claims' / (task_id + '.json')
        if claim_path.exists() or worker_result.exists():
            # Acquiring the inherited run lock proves no former worker still
            # holds it. Preserve its observation rather than silently retrying.
            if worker_result.exists():
                outcome = json.loads(worker_result.read_text())
                check_result(outcome, task)
            else:
                outcome = dict(task, status='INTERRUPTED', host=platform.node())
            outcome.update(controller_finalized=True, controller_interrupted=True,
                           process_wall=None, returncode=None)
            write_json(result_path, outcome)
            continue
        python = manifest['mm_python'] if task['method'] == 'mm' else manifest['candidate_python']
        cache = run / 'jit_cache' / task_id
        env['NUMBA_CACHE_DIR'] = str(cache)
        command = [python, str(run / 'source/scripts/codex/pilot.py'), 'worker', str(task_path)]
        started = time.perf_counter()
        # Claim before spawning: a crash in the launch window is recorded as
        # interrupted, never treated as authorization for an invisible retry.
        write_json(claim_path, {'task_id': task_id, 'host': platform.node(),
                               'started': time.time()})
        cache.mkdir(exist_ok=False)
        with (run / 'logs' / (task_id + '.log')).open('w') as log:
            # flock follows this open-file description into the child. If the
            # controller dies, its surviving worker prevents a second controller.
            process = subprocess.Popen(command, cwd=run, env=env, stdout=log, stderr=log,
                                       pass_fds=(lockfile.fileno(),))
            write_json(run / 'active.json', {'task_id': task_id, 'pid': process.pid,
                                             'host': platform.node(), 'started': time.time()})
            try:
                process.wait(timeout=task['timeout'] + 30)
                terminal = 'PROCESS_ERROR' if process.returncode else 'NO_RESULT'
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
                terminal = 'WATCHDOG_TIMEOUT'
        total = time.perf_counter() - started
        if worker_result.exists():
            outcome = json.loads(worker_result.read_text())
            check_result(outcome, task)
        else:
            outcome = dict(task, status=terminal, host=platform.node())
        if process.returncode and outcome['status'] == 'SUCCESS':
            outcome['status'] = terminal
            outcome['diagnostic_quality'] = {key: outcome.pop(key) for key in
                ('acl', 'qubits', 'max_chain', 'within_chain_variance') if key in outcome}
        outcome['process_wall'] = total
        outcome['returncode'] = process.returncode
        outcome['controller_finalized'] = True
        write_json(result_path, outcome)
        print(task['graph'], task['method'], task['seed'], outcome['status'],
              outcome.get('acl'), round(total, 3), flush=True)
    write_json(run / 'controller.json', {'pid': os.getpid(), 'host': platform.node(),
                                       'finished': time.time(), 'status': 'complete'})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    init = sub.add_parser('init')
    init.add_argument('run')
    init.add_argument('--graphs')
    init.add_argument('--methods', default='mm,native-search,native-packed')
    init.add_argument('--seeds', type=int, default=1)
    init.add_argument('--timeout', type=float, default=30)
    init.add_argument('--candidate-python', default=str(ROOT / '.venv/codex-native/bin/python'))
    init.add_argument('--mm-python', default=str(ROOT / '.venv/bin/python'))
    run = sub.add_parser('run')
    run.add_argument('run')
    child = sub.add_parser('worker')
    child.add_argument('task')
    args = parser.parse_args()
    if args.command == 'init':
        initialize(args)
    elif args.command == 'run':
        execute(args)
    else:
        worker(args.task)


if __name__ == '__main__':
    main()
