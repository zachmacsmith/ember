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
import re
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
for _suffix, _sites, _policy in (
        ('sites', 16, 'legacy'), ('groups', 0, 'round_robin'),
        ('sites-groups', 16, 'round_robin')):
    CONFIGS['native-search-joint1-' + _suffix] = dict(
        CONFIGS['native-search-joint1'], polish_boundary_sites=_sites,
        polish_group_policy=_policy)


def load_readiness_selection(path):
    """Load frozen, deduplicated corpus inputs; keep family data outside graphs."""
    selection = json.loads(Path(path).read_text())
    identity = selection['identity']
    if digest(identity) != selection['selection_id']:
        raise ValueError('Corpus selection identity mismatch')
    records, seen_topologies = {}, set()
    originals = {}
    memberships = set()
    for entry in identity['solver_inputs']:
        name = entry['graph_key']
        if not re.fullmatch(r'[A-Za-z0-9_-]+', name) or name in records:
            raise ValueError('Duplicate or unsafe corpus graph key')
        original_path = (ROOT / entry['graph_record_path']).resolve()
        if not original_path.is_relative_to(ROOT.resolve()):
            raise ValueError('Corpus graph path is outside repository')
        record = json.loads(original_path.read_text())
        if digest(record) != entry['source_hash']:
            raise ValueError(f'Corpus graph hash mismatch: {name}')
        graph = graph_from_record(record)
        if (graph_record(graph) != record or list(graph) != list(range(len(graph)))
                or graph.number_of_nodes() != entry['nodes']
                or graph.number_of_edges() != entry['edges']
                or any(a == b for a, b in graph.edges())):
            raise ValueError(f'Corpus graph structure mismatch: {name}')
        if (record['metadata'] or any(attrs for _, attrs in record['node_attributes'])
                or any(attrs for _, _, attrs in record['edge_attributes'])):
            raise ValueError(f'Corpus graph contains solver-visible metadata: {name}')
        topology = digest({'nodes': record['nodes'], 'edges': record['edges']})
        if topology != entry['normalized_topology_hash'] or topology in seen_topologies:
            raise ValueError(f'Corpus topology mismatch or duplicate: {name}')
        if entry['aggregate_structure_weight'] != 1 or not entry['family_memberships']:
            raise ValueError(f'Invalid corpus memberships or weight: {name}')
        for member in entry['family_memberships']:
            key = (member['family'], member['graph_id'])
            if key in memberships:
                raise ValueError('Duplicate corpus family membership')
            memberships.add(key)
        seen_topologies.add(topology)
        records[name] = record
        ledger_path = original_path.parent.parent / 'selection.json'
        originals[ledger_path] = hashlib.sha256(ledger_path.read_bytes()).hexdigest()
    if not records or len(originals) != 1:
        raise ValueError('Corpus requires one original selection and nonempty inputs')
    original_path, original_hash = next(iter(originals.items()))
    original = json.loads(original_path.read_text())
    if (original_hash != identity['original_selection_file_sha256']
            or original['selection_id'] != identity['original_selection_id']):
        raise ValueError('Original corpus selection identity mismatch')
    expected = {(entry['family'], entry['graph_id'])
                for entry in identity['family_selections']}
    if memberships != expected:
        raise ValueError('Corpus selected families and solver memberships disagree')
    return selection, original, records


def check_corpus_provenance(run, manifest):
    """Verify shipped sidecars without consulting mutable external corpus files."""
    corpus = manifest.get('corpus')
    if corpus is None:
        return None
    selection = json.loads((Path(run) / 'corpus_selection.json').read_text())
    original = json.loads((Path(run) / 'original_corpus_selection.json').read_text())
    if (digest(selection) != corpus['selection_digest']
            or digest(selection['identity']) != corpus['selection_id']
            or selection['selection_id'] != corpus['selection_id']
            or digest(original) != corpus['original_selection_digest']
            or original['selection_id'] != selection['identity']['original_selection_id']):
        raise ValueError('Frozen corpus provenance mismatch')
    entries = {entry['graph_key']: entry for entry in selection['identity']['solver_inputs']}
    names = corpus['included_graphs']
    if len(set(names)) != len(names) or not set(names) <= set(entries):
        raise ValueError('Frozen corpus input list mismatch')
    for name in names:
        record = json.loads((Path(run) / 'graphs' / (name + '.json')).read_text())
        if digest(record) != entries[name]['source_hash']:
            raise ValueError(f'Frozen corpus graph mismatch: {name}')
    task_names = set()
    for task_id in manifest['tasks']:
        task = json.loads((Path(run) / 'tasks' / (task_id + '.json')).read_text())
        name = task['graph']
        if name not in names or task['source_hash'] != entries[name]['source_hash']:
            raise ValueError('Frozen corpus task mismatch')
        task_names.add(name)
    if task_names != set(names):
        raise ValueError('Frozen corpus has unattempted included graphs')
    return selection


def initialize(args):
    import dwave_networkx as dnx
    if not math.isfinite(args.timeout) or args.timeout <= 0 or args.seeds < 1:
        raise ValueError('timeout must be finite and positive; seeds must be positive')
    corpus_path = getattr(args, 'corpus_selection', None)
    if corpus_path:
        selection, original_selection, records = load_readiness_selection(corpus_path)
    else:
        selection = None
        records = {name: graph_record(graph) for name, graph in make_graphs().items()}
    names = args.graphs.split(',') if args.graphs else list(records)
    methods = args.methods.split(',')
    if (not names or len(set(names)) != len(names)
            or any(name not in records for name in names)):
        raise ValueError('Unknown or duplicate graph names')
    if (not methods or len(set(methods)) != len(methods)
            or any(method not in CONFIGS for method in methods)):
        raise ValueError('Unknown or duplicate methods')
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
    tasks = []
    for name in names:
        record = records[name]
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
    if selection:
        write_json(run / 'corpus_selection.json', selection)
        write_json(run / 'original_corpus_selection.json', original_selection)
        manifest['corpus'] = {
            'selection_id': selection['selection_id'],
            'selection_digest': digest(selection),
            'original_selection_digest': digest(original_selection),
            'included_graphs': names,
            'claim_scope': 'inherited development data; no holdout or family-level claim'}
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
    check_corpus_provenance(run, manifest)
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
    init.add_argument('--corpus-selection', help='Frozen deduplicated corpus readiness selection')
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
