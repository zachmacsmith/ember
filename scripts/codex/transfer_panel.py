"""Generate the declared transfer001 development panel; never call an embedder.

Private original labels and feasibility witnesses stay on the evaluator host.
The public bundle contains sanitized source graphs, hashes and an attempt ledger.
"""
from __future__ import annotations

import concurrent.futures
import hashlib
import importlib.util
import json
from pathlib import Path
import platform
import random
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
PUBLIC = ROOT / 'results/codex/transfer-cycle-001'
PRIVATE = ROOT.parent / 'ember-evaluator-private/transfer-cycle-001'
GENERATOR = ROOT / 'scripts/generated_graphs/New_Generation/generate_graphs2.py'
PROTOCOL = ROOT / 'notes/codex/transfer_cycle_001_inputs.md'
ORACLE = ROOT / 'results/codex/042-results-review/pre-execution/ember_embedding_oracle.py'
ARCHIVE = ROOT / 'results/codex/retrieved/hyde06/061-branched-path-breadth'


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(path, value):
    with Path(path).open('x') as f:
        f.write(json.dumps(value, sort_keys=True, indent=2) + '\n')


def load_module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def seed(namespace, case):
    return int.from_bytes(hashlib.sha256(
        f'ember-codex-transfer001/{namespace}/{case}'.encode()).digest()[:8], 'big')


def record(nodes, edges):
    nodes = sorted(nodes)
    edges = sorted({tuple(sorted(e)) for e in edges})
    return dict(nodes=nodes, edges=[list(e) for e in edges], metadata={},
                node_attributes=[[v, {}] for v in nodes],
                edge_attributes=[[a, b, {}] for a, b in edges])


def cases():
    out = []
    for n in (80, 160):
        for family, params in (
            ('random_er', dict(n=n, p=.10)), ('barabasi_albert', dict(n=n, m=4)),
            ('regular', dict(n=n, d=8)), ('watts_strogatz', dict(n=n, k=6, beta=.2)),
            ('sbm', dict(n=n, n_communities=4, p_in=.20, p_out=.02)),
            ('random_planar', dict(n=n))):
            out.append(dict(case=f'{family}-{n}', family=family, kind='fresh', params=params,
                            generation_timeout=300 if family == 'random_planar' else 30))
    for family, name in [('grid', 'ember_1584'), ('honeycomb', 'ember_32367'), ('wheel', 'ember_2429')]:
        out.append(dict(case=name, family=family, kind='anchor', path=str(ARCHIVE/'graphs'/(name+'.json')),
                        generation_timeout=30))
    out.append(dict(case='complete-100', family='complete', kind='dense_sentinel', generation_timeout=30))
    for kind in ('singleton_control', 'branch_control'):
        for n in (80, 160):
            out.append(dict(case=f'{kind}-{n}', family='diagnostic_control', kind=kind, n=n,
                            generation_timeout=30))
    return out


def worker(case, destination):
    start = time.perf_counter(); cpu = time.process_time()
    import networkx as nx
    assert nx.__version__ == '3.4.2'
    oracle = load_module(ORACLE, '_transfer_oracle')
    target_record = json.loads((ARCHIVE/'target.json').read_text())
    adjacency, _ = oracle.adjacency(target_record)
    rng = random.Random(seed('generation', case['case']))
    witness = None
    try:
        kind = case['kind']
        if kind == 'fresh':
            generator = load_module(GENERATOR, '_transfer_generators')
            graph, _, _ = getattr(generator, 'gen_' + case['family'])(
                **case['params'], seed=seed('generation', case['case']))
            original = record(graph.nodes(), graph.edges())
        elif kind == 'anchor':
            original = json.loads(Path(case['path']).read_text())
        elif kind == 'dense_sentinel':
            original = record(range(100), ((a, b) for a in range(100) for b in range(a+1, 100)))
        elif kind == 'singleton_control':
            n = case['n']; queue = [rng.choice(sorted(adjacency))]; seen = set(queue)
            cursor = 0
            while len(queue) < n:
                q = queue[cursor]; cursor += 1
                neighbors = sorted(adjacency[q] - seen); rng.shuffle(neighbors)
                for w in neighbors:
                    seen.add(w); queue.append(w)
                    if len(queue) == n: break
            owner = {q: v for v, q in enumerate(queue)}
            original = record(range(n), ((owner[q], owner[w]) for q in queue
                              for w in adjacency[q] if w in owner and q < w))
            witness = {str(v): [q] for v, q in enumerate(queue)}
        elif kind == 'branch_control':
            occupied = {}; witness = {}; n = case['n']
            for v in range(n):
                boundary = (set().union(*(adjacency[q] for q in occupied)) - occupied.keys()
                            if occupied else set(adjacency))
                if not boundary: raise ValueError('No free branch root')
                chain = {rng.choice(sorted(boundary))}
                while len(chain) < 1 + v % 3:
                    options = set().union(*(adjacency[q] for q in chain)) - occupied.keys() - chain
                    if not options: raise ValueError('One-pass branch growth blocked')
                    chain.add(rng.choice(sorted(options)))
                occupied.update((q, v) for q in chain); witness[str(v)] = sorted(chain)
            original = record(range(n), ((v, occupied[w]) for q, v in occupied.items()
                              for w in adjacency[q] if w in occupied and v < occupied[w]))
        else: raise ValueError(kind)
        source = oracle.adjacency(original)
        assert original == record(source[0], source[1]), 'Unsanitized original'
        result = dict(status='READY', original=original, witness=witness)
        if witness is not None:
            valid, reason, quality = oracle.embedding_quality(witness, *source, adjacency, oracle.adjacency(target_record)[1])
            assert valid, reason
            result['witness_quality'] = quality
    except Exception as exc:
        result = dict(status='GENERATION_ERROR', error=type(exc).__name__ + ': ' + str(exc))
    result.update(wall=time.perf_counter()-start, cpu=time.process_time()-cpu)
    save(destination, result)


def attempt(case):
    folder = PRIVATE / case['case']; folder.mkdir()
    argv = [sys.executable, '-I', '-B', str(Path(__file__).resolve()), '--worker',
            json.dumps(case, sort_keys=True), str(folder/'generated.json')]
    save(folder/'invocation.json', dict(argv=argv, script_sha256=sha(__file__)))
    started = time.perf_counter()
    with (folder/'stdout').open('xb') as stdout, (folder/'stderr').open('xb') as stderr:
        try:
            p = subprocess.run(argv, stdout=stdout, stderr=stderr, timeout=case['generation_timeout'], check=False)
            status = dict(returncode=p.returncode, process_wall=time.perf_counter()-started)
        except subprocess.TimeoutExpired:
            status = dict(returncode=None, timed_out=True, process_wall=time.perf_counter()-started)
    save(folder/'status.json', status)
    if status.get('timed_out') or status['returncode'] != 0 or not (folder/'generated.json').exists():
        return dict(case=case, status='GENERATION_TIMEOUT' if status.get('timed_out') else 'GENERATION_ERROR', **status)
    value = json.loads((folder/'generated.json').read_text())
    print(case['case'], value['status'], f'{status["process_wall"]:.3f}s', flush=True)
    return dict(case=case, **status, **value)


def publish(value, key, label_case, parent=None):
    original = value['original']; vertices = original['nodes']; permutation = list(range(len(vertices)))
    random.Random(seed('label', label_case)).shuffle(permutation)
    mapping = dict(zip(vertices, permutation))
    normalized = record(permutation, ((mapping[a], mapping[b]) for a, b in original['edges']))
    reverse = {v: k for k, v in mapping.items()}
    assert len(reverse) == len(vertices)
    assert {tuple(sorted((reverse[a], reverse[b]))) for a, b in normalized['edges']} == {tuple(e) for e in original['edges']}
    save(PUBLIC/'graphs'/(key+'.json'), normalized)
    private = dict(original=original, original_to_solver=mapping, solver_to_original=reverse,
                   witness_original=value.get('witness'), case=value['case'], source_hash=digest(normalized))
    if value.get('witness') is not None:
        mapped = {str(mapping[int(v)]): c for v, c in value['witness'].items()}
        oracle = load_module(ORACLE, '_label_oracle')
        target = oracle.adjacency(json.loads((ARCHIVE/'target.json').read_text()))
        assert oracle.embedding_quality(mapped, *oracle.adjacency(normalized), *target)[0]
        private['witness_solver'] = mapped
    save(PRIVATE/(key+'.json'), private)
    return dict(graph=key, case=value['case']['case'], kind=value['case']['kind'],
                family=value['case']['family'], nodes=len(vertices), edges=len(original['edges']),
                parent=parent, source_hash=digest(normalized), graph_sha256=sha(PUBLIC/'graphs'/(key+'.json')),
                original_topology_hash=digest({'nodes': vertices, 'edges': original['edges']}),
                structure_identity='EXPOSED' if value['case']['kind'] in ('anchor', 'dense_sentinel') else 'NOVELTY_UNRESOLVED',
                label_seed=seed('label', label_case), private_record_sha256=sha(PRIVATE/(key+'.json')))


def main():
    assert sha(ORACLE) == 'e4718c2ec09f3ec80e035ef89648f81b45413f52c7580123ef129419b25612d9'
    assert sha(ARCHIVE/'target.json') == 'c683ae784e2ee9a1d14f0760368deaa5cfeee2c47a6c2eade683e5412e61177c'
    plan = cases()
    PUBLIC.mkdir(exist_ok=False); (PUBLIC/'graphs').mkdir()
    PRIVATE.mkdir(parents=True, exist_ok=False)
    frozen = dict(cases=plan, script_sha256=sha(__file__), generator_sha256=sha(GENERATOR),
                  protocol_sha256=sha(PROTOCOL), target_sha256=sha(ARCHIVE/'target.json'),
                  oracle_sha256=sha(ORACLE), python=platform.python_version(), source_seed_namespace='transfer001',
                  private_directory=str(PRIVATE), purpose='development; no embeddings from solvers')
    save(PUBLIC/'generation_plan.json', frozen)
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
        values = list(pool.map(attempt, plan))
    rows=[]; ledger=[]; by_case={}
    for i, value in enumerate(values, 1):
        ledger.append({k:v for k,v in value.items() if k not in ('original', 'witness', 'witness_quality')})
        if value['status'] != 'READY': continue
        key=f'g{i:04d}'; row=publish(value,key,value['case']['case']); rows.append(row)
        by_case[value['case']['case']] = (key,value)
    for i, case in enumerate(('ember_1584','barabasi_albert-80'),21):
        if case not in by_case:
            ledger.append(dict(case=case, status='RELABEL_PARENT_UNAVAILABLE')); continue
        parent,value=by_case[case]; rows.append(publish(value,f'g{i:04d}',case+'/relabel',parent=parent))
    save(PUBLIC/'attempt_ledger.json',ledger)
    save(PUBLIC/'panel.json',dict(inputs=rows, intended_structures=20, intended_relabelings=2,
                                realized_inputs=len(rows), private_witnesses_shipped=False,
                                generation_plan_sha256=sha(PUBLIC/'generation_plan.json')))
    print(json.dumps(dict(status='PANEL_FROZEN',inputs=len(rows),generation_failures=sum(v['status']!='READY' for v in values))))


if __name__ == '__main__':
    if len(sys.argv)>1 and sys.argv[1]=='--worker': worker(json.loads(sys.argv[2]),Path(sys.argv[3]))
    else: main()
