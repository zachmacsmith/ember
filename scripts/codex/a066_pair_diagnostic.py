"""A066 exact two-owner diagnostic, never a complete constructor."""
import time
ENTERED = time.perf_counter()
CPU_ENTERED = time.process_time()
import argparse
from contextlib import contextmanager
import hashlib
import importlib.util
import json
from pathlib import Path
import signal
import sys

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'results/codex/a066-pair-diagnostic'
GRAPHS = ('g0001', 'g0006', 'g0013', 'g0017', 'g0201', 'g0202')
ORACLE = ROOT / 'results/codex/042-results-review/pre-execution/ember_embedding_oracle.py'
ORACLE_SHA = 'e4718c2ec09f3ec80e035ef89648f81b45413f52c7580123ef129419b25612d9'
ARCHIVE = ROOT / 'results/codex/a065-constructor/archive'
PILOT = ARCHIVE / 'source/scripts/codex/pilot.py'
PREPARATION = ARCHIVE / 'source/packages/ember-qc/src/ember_qc/algorithms/factored/mobile_boundary_reconstruction.py'


def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def read(path): return json.loads(Path(path).read_text())
def save(path, value):
    with Path(path).open('x') as out:
        json.dump(value, out, indent=2, sort_keys=True, allow_nan=False)
        out.write('\n')


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


class Deadline(Exception): pass


class Meter:
    def __init__(self, deadline):
        self.deadline = deadline
        self.walls, self.cpus, self.counts = {}, {}, {}
        self.phase = 'setup'
    def check(self):
        if time.perf_counter() >= self.deadline:
            raise Deadline(self.phase)
    def tick(self, name):
        self.counts[name] = self.counts.get(name, 0) + 1
        self.check()
    @contextmanager
    def at(self, phase):
        old = self.phase
        self.phase = phase
        wall, cpu = time.perf_counter(), time.process_time()
        try:
            self.check()
            yield
            self.check()
        finally:
            self.walls[phase] = self.walls.get(phase, 0.) + time.perf_counter() - wall
            self.cpus[phase] = self.cpus.get(phase, 0.) + time.process_time() - cpu
            self.phase = old


def runtime():
    pilot = load('a066_existing_pilot', PILOT)
    for name in ('minorminer', '_minorminer', 'busclique'):
        if name in sys.modules or importlib.util.find_spec(name) is not None:
            raise RuntimeError('prohibited dependency present: ' + name)
    guard = pilot.NoExternalEmbedder()
    sys.meta_path.insert(0, guard)
    assert sha(ORACLE) == ORACLE_SHA
    return (load('a066_existing_oracle', ORACLE),
            load('a066_existing_preparation', PREPARATION), guard)


def boundaries(chains, target, meter):
    answer = {}
    for u, chain in chains.items():
        sites = set()
        for q in chain:
            meter.tick('boundary_site')
            sites.update(target[q])
        answer[u] = sites
    return answer


def intersection_domain(available, neighbors, contact, meter):
    domain = set(available)
    for w in sorted(neighbors):
        meter.tick('domain_intersection')
        domain.intersection_update(contact[w])
    return domain


def pair_domain(u, v, source, target, chains, free, contact, meter):
    """Exact finite assignment counts; only representative witnesses are saved."""
    assert v in source[u] and len(chains[u]) == 2 and len(chains[v]) == 1
    old_u, old_v = set(chains[u]), chains[v][0]
    direct = intersection_domain(free | old_u, source[u], contact, meter)
    released = free | old_u | {old_v}
    du = intersection_domain(released, source[u] - {v}, contact, meter)
    dv = intersection_domain(released, source[v] - {u}, contact, meter)
    counts = dict(assignments=0, neutral_assignments=0,
                  simultaneous_assignments=0, fixed_v_assignments=0)
    witnesses = {}
    if direct:
        witnesses['direct'] = {'u': min(direct), 'v': old_v}
    for p in sorted(du):
        meter.tick('domain_u_site')
        for q in sorted(target[p]):
            meter.tick('hardware_incidence')
            if q not in dv or q == p:
                continue
            counts['assignments'] += 1
            if q == old_v:
                counts['fixed_v_assignments'] += 1
            elif q not in old_u and q in contact[u]:
                counts['neutral_assignments'] += 1
                witnesses.setdefault('neutral', {'u': p, 'v': q})
            else:
                counts['simultaneous_assignments'] += 1
                witnesses.setdefault('simultaneous', {'u': p, 'v': q})
    assert counts['fixed_v_assignments'] == len(direct)
    return dict(owner_u=u, owner_v=v, direct_domain=len(direct),
                domain_u=len(du), domain_v=len(dv), **counts,
                neutral_bridge_requires_relocation=not direct and counts['neutral_assignments'] > 0,
                joint_release_only=not direct and counts['neutral_assignments'] == 0 and counts['simultaneous_assignments'] > 0,
                witnesses=witnesses)


def modified(chains, changes):
    return {str(u): list(changes.get(u, sites)) for u, sites in chains.items()}


def certify_witnesses(row, chains, G, E, H, F, oracle, meter):
    u, v = row['owner_u'], row['owner_v']
    before = sum(map(len, chains.values()))
    for name, witness in row['witnesses'].items():
        meter.tick('witness_begin')
        changes = {u: [witness['u']], v: [witness['v']]}
        valid, reason, quality = oracle.embedding_quality(modified(chains, changes), G, E, H, F)
        meter.check()
        assert valid, (name, reason)
        assert quality['qubits'] == before - 1
        witness.update(final_valid=True, final_quality=quality)
        if name == 'neutral':
            valid, reason, quality = oracle.embedding_quality(modified(chains, {v: [witness['v']]}), G, E, H, F)
            meter.check()
            assert valid, reason
            assert quality['qubits'] == before
            witness.update(intermediate_valid=True, intermediate_quality=quality)
        meter.tick('witness_certified')


def prepare_packet():
    packet = BASE / 'packet001'
    packet.mkdir(exist_ok=False)
    common = read(ARCHIVE.parent / 'audit001/output/summary.json')
    assert common['status'] == 'PASS' and not common['errors']
    rows = read(ARCHIVE.parent / 'audit001/output/rows.json')
    files, provenance = {}, {}
    target = ARCHIVE / 'target.json'
    assert sha(target) == common['files'][str(target)]
    (packet / 'target.json').write_bytes(target.read_bytes())
    files[str((packet / 'target.json').relative_to(ROOT))] = sha(packet / 'target.json')
    for graph in GRAPHS:
        row, = [r for r in rows if r['graph'] == graph and r['method'] == 'native-compiled-boundary']
        assert row['credited'] and row['status'] == 'SUCCESS' and row['seed'] == 0
        source = ARCHIVE / 'graphs' / (graph + '.json')
        result = ARCHIVE / 'results' / (row['task_id'] + '.json')
        assert sha(source) == common['files'][str(source)]
        assert sha(result) == common['files'][str(result)]
        raw = read(result)
        assert raw['method'] == 'native-compiled-boundary' and raw['task_id'] == row['task_id']
        record = dict(graph=graph, source=read(source), embedding=raw['embedding'],
                      seed=0, audited_qubits=row['qubits'], task_id=row['task_id'])
        path = packet / (graph + '.json')
        save(path, record)
        files[str(path.relative_to(ROOT))] = sha(path)
        provenance[graph] = {'candidate_raw': {str(result.relative_to(ROOT)): sha(result)},
                             'source': {str(source.relative_to(ROOT)): sha(source)}}
    for p in (Path(__file__), ROOT / 'scripts/codex/a066_pair_check.py', ORACLE, PILOT,
              PREPARATION, ROOT / 'notes/codex/tracks/a_066_pair_diagnostic_contract.md'):
        files[str(p.relative_to(ROOT))] = sha(p)
    freeze = dict(created_epoch=time.time(), files=files, provenance=provenance,
                  graphs=GRAPHS, seconds=30., outer_seconds=45.,
                  input_scope='Candidate A065 final maps only; no MM/private witness reads',
                  self_review='Exact domains checked against brute-force complete/intermediate oracle; fixed-v equality asserted; original preparation attribution; every saved witness independently checked; no constructor calls.')
    save(packet / 'manifest.json', freeze)
    print(json.dumps(dict(status='FROZEN', manifest_sha256=sha(packet / 'manifest.json'), files=len(files))))


def worker(graph, out):
    out.mkdir(exist_ok=False)
    meter = Meter(ENTERED + 30.)
    rows, errors, guard, current = [], [], None, None
    result = dict(graph=graph, status='UNRESOLVED', pairs_total=None, pairs_completed=0,
                  rows=rows, errors=errors, candidate_constructor_calls=0,
                  mm_map_reads=0, budget_seconds=30., unvalidated_interrupted_witnesses=None)
    def interrupted(signum, frame): raise Deadline(meter.phase)
    old_handler = signal.signal(signal.SIGALRM, interrupted)
    signal.setitimer(signal.ITIMER_REAL, max(0.000001, meter.deadline-time.perf_counter()))
    try:
        with meter.at('setup'):
            freeze = read(BASE / 'packet001/manifest.json')
            assert freeze['graphs'] == list(GRAPHS) and freeze['seconds'] == 30.
            for path, digest in freeze['files'].items():
                meter.tick('binding_check')
                assert sha(ROOT / path) == digest, path
            oracle, preparation, guard = runtime()
            data = read(BASE / 'packet001' / (graph + '.json'))
            target = read(BASE / 'packet001/target.json')
            G, E = oracle.adjacency(data['source']); H, F = oracle.adjacency(target)
            chains = {u: tuple(data['embedding'][str(u)]) for u in G}
        with meter.at('validation'):
            valid, reason, quality = oracle.embedding_quality(data['embedding'], G, E, H, F)
            assert valid, reason
            assert quality['qubits'] == data['audited_qubits']
            result['entry_quality'] = quality
        with meter.at('setup'):
            contact = boundaries(chains, H, meter)
            occupied = {q for sites in chains.values() for q in sites}
            free = set(H) - occupied
            pairs = sorted((u, v) for u in G if len(chains[u]) == 2
                           for v in G[u] if len(chains[v]) == 1)
            result['pairs_total'] = len(pairs)
        # Invoke only the unchanged preparation, never a reconstruction/constructor.
        with meter.at('preparation'):
            old_meter = preparation._Meter(meter.deadline)
            context = preparation._Context(G, H, data['seed'], None, old_meter)
            bundle = context.bundle(context.read_entry({u: list(sites) for u, sites in chains.items()}))
            donor_sites = {}
            for u in sorted({u for u, v in pairs}):
                record = {}
                context.prepare(bundle, context.vindex[u], record)
                donor_sites[u] = record['stem_sites']
                meter.tick('existing_preparation')
            result['preparation_meter'] = old_meter.finish()
        for u, v in pairs:
            current = dict(owner_u=u, owner_v=v, status='INCOMPLETE')
            with meter.at('domains'):
                current.update(pair_domain(u, v, G, H, chains, free, contact, meter))
                current['removable_donor_sites'] = donor_sites[u]
                current['strict_query_obstructed'] = donor_sites[u] == 0 and current['direct_domain'] == 0
            with meter.at('validation'):
                certify_witnesses(current, chains, G, E, H, F, oracle, meter)
            current['status'] = 'EXHAUSTED_AND_WITNESSES_VALIDATED'
            rows.append(current); current = None
            result['pairs_completed'] += 1
        result['status'] = 'EXHAUSTED'
    except (Deadline,) as exc:
        result['status'] = 'CENSORED'
        result['interruption'] = str(exc)
    except Exception as exc:
        # Existing preparation raises its own deadline exception.
        if type(exc).__name__ == '_Stop':
            result['status'] = 'CENSORED'; result['interruption'] = 'existing_preparation: '+str(exc)
        else:
            result['status'] = 'ERROR'; errors.append(repr(exc))
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0.)
        signal.signal(signal.SIGALRM, old_handler)
    if current is not None:
        result['interrupted_pair'] = current
        result['unvalidated_interrupted_witnesses'] = [k for k, w in current.get('witnesses', {}).items()
            if not w.get('final_valid') or (k == 'neutral' and not w.get('intermediate_valid'))]
    result.update(wall_before_output=time.perf_counter()-ENTERED, cpu_before_output=time.process_time()-CPU_ENTERED,
                  wall_by_phase=meter.walls, cpu_by_phase=meter.cpus, counts=meter.counts,
                  guard_attempts=None if guard is None else guard.attempts,
                  script_sha256=sha(Path(__file__)), manifest_sha256=sha(BASE/'packet001/manifest.json'))
    result['pairs_remaining'] = None if result['pairs_total'] is None else result['pairs_total']-result['pairs_completed']
    result['summary'] = {key: sum(bool(r[key]) for r in rows) for key in
        ('direct_domain', 'neutral_bridge_requires_relocation', 'joint_release_only', 'strict_query_obstructed')}
    result['summary']['neutral_bridge_and_strict_query_obstructed'] = sum(
        r['neutral_bridge_requires_relocation'] and r['strict_query_obstructed'] for r in rows)
    result['summary']['saved_final_witnesses'] = sum(len(r['witnesses']) for r in rows)
    result['summary']['saved_neutral_intermediates'] = sum('neutral' in r['witnesses'] for r in rows)
    save(out/'output.json', result)
    print(json.dumps({key: result[key] for key in ('graph','status','pairs_total','pairs_completed','summary','errors')}))
    return 1 if errors else 0


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=('prepare', 'worker'))
    parser.add_argument('graph', nargs='?', choices=GRAPHS)
    parser.add_argument('out', nargs='?', type=Path)
    args = parser.parse_args()
    if args.action == 'prepare': prepare_packet()
    else: raise SystemExit(worker(args.graph, args.out))
