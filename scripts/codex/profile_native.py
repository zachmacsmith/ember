"""Bounded cold/warm profiling of fixed independent native-search configurations.

This diagnostic never reads comparator embeddings or chooses between algorithms.
It snapshots current source and consumes only serialized development input graphs.
"""
from __future__ import annotations

import argparse
import cProfile
import hashlib
import importlib.abc
import importlib.metadata
import importlib.util
import json
import os
from pathlib import Path
import platform
import pstats
import random
import shutil
import signal
import subprocess
import sys
import time
import traceback


ROOT = Path(__file__).resolve().parents[2]
GRAPHS = ('complete_40', 'random_er_80_d8', 'grid_8x8')
BUDGETS = (100, 300, 1000)
PROFILE_CASE = ('random_er_80_d8', 300)
STAGES = {
    'target_adjacency': ('native', 'build_adjacency'),
    'target_layout': ('dnx', 'zephyr_layout'),
    'target_grid': ('native', 'TileGrid'),
    'search_layout': ('plane', 'arrange'),
    'conversion': ('native', 'wire_seeds_exact'),
    'completion': ('native', 'complete_seeds'),
    'prune': ('native', 'spur_prune'),
    'internal_validation': ('native', 'is_valid_embedding'),
}


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def write_json(path, value):
    path = Path(path)
    temporary = path.with_name(path.name + '.tmp')
    temporary.write_text(json.dumps(value, sort_keys=True, indent=2) + '\n')
    temporary.replace(path)


def graph_from_record(record):
    import networkx as nx
    graph = nx.Graph()
    graph.add_nodes_from(record['nodes'])
    graph.add_edges_from(record['edges'])
    for node, attributes in record['node_attributes']:
        graph.nodes[node].update(attributes)
    for a, b, attributes in record['edge_attributes']:
        graph.edges[a, b].update(attributes)
    graph.graph.update(record['metadata'])
    return graph


def verify(embedding, source, target):
    if not isinstance(embedding, dict) or set(embedding) != set(source):
        return 'source_coverage'
    owner = {}
    for vertex, chain in embedding.items():
        if not chain or len(set(chain)) != len(chain):
            return 'empty_or_duplicate_chain'
        if any(q not in target or q in owner for q in chain):
            return 'membership_or_overlap'
        owner.update({q: vertex for q in chain})
        chain_set = set(chain)
        reached, queue = {chain[0]}, [chain[0]]
        for q in queue:
            fresh = (set(target[q]) & chain_set) - reached
            reached.update(fresh)
            queue.extend(fresh)
        if reached != chain_set:
            return 'disconnected_chain'
    if any(not any(owner.get(q) == b for p in embedding[a] for q in target[p])
           for a, b in source.edges()):
        return 'missing_contact'
    return None


class EmbedderBlocker(importlib.abc.MetaPathFinder):
    def __init__(self):
        self.attempts = []

    def find_spec(self, fullname, path=None, target=None):
        root = fullname.split('.')[0].lower()
        if 'minorminer' in root or root == 'busclique':
            self.attempts.append(fullname)
            raise ImportError(f'Forbidden embedding dependency: {fullname}')


def check_snapshot(run, manifest):
    if digest(manifest['source_files']) != manifest['source_snapshot']:
        raise RuntimeError('Source snapshot digest mismatch')
    for relative, expected in manifest['source_files'].items():
        if hashlib.sha256((run / 'source' / relative).read_bytes()).hexdigest() != expected:
            raise RuntimeError(f'Frozen source changed: {relative}')


def worker(run, job_id):
    signal.signal(signal.SIGALRM, signal.SIG_DFL)
    signal.alarm(120)
    manifest = json.loads((run / 'manifest.json').read_text())
    check_snapshot(run, manifest)
    job = manifest['jobs'][job_id]
    if digest(job)[:24] != job_id:
        raise RuntimeError('Job digest mismatch')
    outcome = {'job_id': job_id, **job, 'source_snapshot': manifest['source_snapshot'],
               'host': platform.node(), 'python': sys.version,
               'python_executable': sys.executable, 'python_prefix': sys.prefix,
               'machine': platform.uname()._asdict(), 'load_start': os.getloadavg(),
               'cache_dir': os.environ.get('NUMBA_CACHE_DIR'), 'calls': []}
    blocker = EmbedderBlocker()
    try:
        if any(importlib.util.find_spec(name) is not None for name in
               ('minorminer', '_minorminer', 'busclique')):
            raise RuntimeError('Candidate environment contains prohibited package')
        sys.meta_path.insert(0, blocker)
        sys.path.insert(0, str(run / 'source/packages/ember-qc/src'))
        start = time.perf_counter()
        import dwave_networkx as dnx
        from ember_qc.algorithms.factored import native
        outcome['import_wall'] = time.perf_counter() - start
        implementation = Path(native.__file__).resolve()
        if not implementation.is_relative_to(run / 'source'):
            raise RuntimeError('Candidate loaded outside source snapshot')
        outcome['implementation_path'] = str(implementation)
        outcome['versions'] = {}
        for package in ('networkx', 'numpy', 'numba', 'dwave-networkx', 'minorminer', 'scipy'):
            try:
                outcome['versions'][package] = importlib.metadata.version(package)
            except importlib.metadata.PackageNotFoundError:
                outcome['versions'][package] = None
        start = time.perf_counter()
        source_data = json.loads((run / 'graphs' / (job['graph'] + '.json')).read_text())
        target_data = json.loads((run / 'target.json').read_text())
        if digest(source_data) != job['source_hash'] or digest(target_data) != job['target_hash']:
            raise RuntimeError('Input hash mismatch')
        source, target = graph_from_record(source_data), graph_from_record(target_data)
        outcome['input_wall'] = time.perf_counter() - start
        modules = {'native': native, 'plane': native.plane, 'dnx': dnx}
        stage_wall, stage_calls = {}, {}

        def instrument(original, stage):
            def measured(*args, **kwargs):
                start = time.perf_counter()
                try:
                    return original(*args, **kwargs)
                finally:
                    stage_wall[stage] = stage_wall.get(stage, 0.0) + time.perf_counter() - start
                    stage_calls[stage] = stage_calls.get(stage, 0) + 1
            return measured

        for stage, (module, attribute) in STAGES.items():
            obj = modules[module]
            setattr(obj, attribute, instrument(getattr(obj, attribute), stage))

        def run_call(mode, profiler=None):
            stage_wall.clear()
            stage_calls.clear()
            start, cpu = time.perf_counter(), time.process_time()
            if profiler:
                profiler.enable()
            try:
                result = native.native_embed(source.copy(), target.copy(),
                                             **job['configuration'])
            finally:
                if profiler:
                    profiler.disable()
            solver_wall = time.perf_counter() - start
            solver_cpu = time.process_time() - cpu
            embedding = result.get('embedding', {})
            validation_start = time.perf_counter()
            error = verify(embedding, source, target)
            external_validation_wall = time.perf_counter() - validation_start
            lengths = [len(c) for c in embedding.values()]
            record = {'mode': mode, 'solver_wall': solver_wall, 'solver_cpu': solver_cpu,
                      'stage_wall': dict(stage_wall), 'stage_calls': dict(stage_calls),
                      'other_solver_wall': solver_wall - sum(stage_wall.values()),
                      'external_validation_wall': external_validation_wall,
                      'reported_status': result.get('status'), 'validation_error': error,
                      'status': 'SUCCESS' if error is None and result.get('status') == 'SUCCESS'
                      and solver_wall <= job['configuration']['timeout'] else 'UNSUCCESSFUL',
                      'diag': result.get('diag', {}), 'error': result.get('error'),
                      'embedding': {str(v): list(c) for v, c in embedding.items()}}
            if error is None:
                record.update(qubits=sum(lengths), acl=sum(lengths) / len(source),
                              max_chain=max(lengths), embedding_hash=digest(record['embedding']))
            return record

        for mode in ('cold', 'warm'):
            outcome['calls'].append(run_call(mode))
        if job['cprofile']:
            profiler = cProfile.Profile()
            record = run_call('warm_cprofile', profiler)
            profiler.dump_stats(str(run / 'profiles' / (job_id + '.prof')))
            stats = pstats.Stats(profiler)
            entries = []
            for (filename, line, function), (primitive, total, own, cumulative, _) in stats.stats.items():
                entries.append({'file': filename, 'line': line, 'function': function,
                                'primitive_calls': primitive, 'total_calls': total,
                                'self_seconds': own, 'cumulative_seconds': cumulative})
            record['profile_top_cumulative'] = sorted(entries, key=lambda e: -e['cumulative_seconds'])[:40]
            record['profile_top_self'] = sorted(entries, key=lambda e: -e['self_seconds'])[:40]
            record['profile_source_functions'] = sorted(
                [e for e in entries if '/ember_qc/' in e['file']],
                key=lambda e: -e['cumulative_seconds'])[:40]
            outcome['calls'].append(record)
        outcome['status'] = 'COMPLETE'
    except Exception:
        outcome['status'] = 'ERROR'
        outcome['traceback'] = traceback.format_exc()
    outcome['forbidden_import_attempts'] = blocker.attempts
    outcome['loaded_embedding_libraries'] = [name for name in sys.modules
        if 'minorminer' in name.split('.')[0].lower() or name.split('.')[0].lower() == 'busclique']
    if outcome['forbidden_import_attempts'] or outcome['loaded_embedding_libraries']:
        outcome['status'] = 'DEPENDENCY_VIOLATION'
    outcome['load_end'] = os.getloadavg()
    write_json(run / 'results' / (job_id + '.json'), outcome)


def prepare(run, inputs, python):
    run.mkdir(parents=True, exist_ok=False)
    for directory in ('graphs', 'source', 'results', 'profiles', 'logs', 'jit_cache'):
        (run / directory).mkdir()
    source_files = {}
    package = ROOT / 'packages/ember-qc/src/ember_qc'
    files = list(package.rglob('*.py')) + [Path(__file__), package / 'graphs/manifest.json',
                                          package / 'graphs/presets.csv']
    for source in files:
        relative = source.relative_to(ROOT)
        content = source.read_bytes()
        dest = run / 'source' / relative
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(content)
        source_files[str(relative)] = hashlib.sha256(content).hexdigest()
    shutil.copyfile(inputs / 'target.json', run / 'target.json')
    target_hash = digest(json.loads((run / 'target.json').read_text()))
    jobs = {}
    for graph in GRAPHS:
        shutil.copyfile(inputs / 'graphs' / (graph + '.json'), run / 'graphs' / (graph + '.json'))
        source_hash = digest(json.loads((run / 'graphs' / (graph + '.json')).read_text()))
        for budget in BUDGETS:
            job = {'graph': graph, 'source_hash': source_hash, 'target_hash': target_hash,
                   'configuration': {'construction': 'search', 'max_asks': budget,
                                     'polish_passes': 0, 'seed': 0, 'timeout': 30.0},
                   'cprofile': (graph, budget) == PROFILE_CASE}
            jobs[digest(job)[:24]] = job
    order = list(jobs)
    random.Random(14001).shuffle(order)
    manifest = {'purpose': 'bounded runtime diagnostic; no comparator embeddings',
                'created_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
                'python': os.path.abspath(python), 'inputs': str(inputs),
                'source_files': source_files, 'source_snapshot': digest(source_files),
                'jobs': jobs, 'job_order': order, 'threads': 1,
                'cache_policy': 'empty per worker; cold then warm; one separate warm cProfile call',
                'git_revision': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()}
    write_json(run / 'manifest.json', manifest)
    print('Prepared', len(jobs), 'jobs:', run, flush=True)


def run_jobs(run):
    manifest = json.loads((run / 'manifest.json').read_text())
    check_snapshot(run, manifest)
    env = os.environ.copy()
    env.update({key: '1' for key in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS',
                                   'MKL_NUM_THREADS', 'NUMBA_NUM_THREADS')})
    env['PYTHONHASHSEED'] = '0'
    env['PYTHONPATH'] = str(run / 'source/packages/ember-qc/src')
    for job_id in manifest['job_order']:
        output = run / 'results' / (job_id + '.json')
        if output.exists():
            continue
        cache = run / 'jit_cache' / job_id
        cache.mkdir(exist_ok=False)
        env['NUMBA_CACHE_DIR'] = str(cache)
        command = [manifest['python'], str(run / 'source/scripts/codex/profile_native.py'),
                   'worker', str(run), job_id]
        started = time.perf_counter()
        with (run / 'logs' / (job_id + '.log')).open('w') as log:
            try:
                child = subprocess.run(command, env=env, cwd=run, stdout=log, stderr=log,
                                       timeout=105, check=False)
                returncode = child.returncode
            except subprocess.TimeoutExpired:
                returncode = None
        result = json.loads(output.read_text()) if output.exists() else {'status': 'NO_RESULT'}
        result.update(process_wall=time.perf_counter() - started, returncode=returncode)
        write_json(output, result)
        print(job_id, result['status'], [(r['mode'], r['status'], r.get('acl'),
              round(r['solver_wall'], 3)) for r in result.get('calls', [])], flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='action', required=True)
    prep = sub.add_parser('prepare')
    prep.add_argument('run', type=Path)
    prep.add_argument('--inputs', type=Path, default=ROOT / 'results/codex/009-first-development-screen')
    prep.add_argument('--python', default=str(ROOT / '.venv/codex-native/bin/python'))
    execute = sub.add_parser('run')
    execute.add_argument('run', type=Path)
    child = sub.add_parser('worker')
    child.add_argument('run', type=Path)
    child.add_argument('job_id')
    args = parser.parse_args()
    run = args.run.absolute()
    if args.action == 'prepare':
        prepare(run, args.inputs.absolute(), args.python)
    elif args.action == 'run':
        run_jobs(run)
    else:
        worker(run, args.job_id)


if __name__ == '__main__':
    main()
