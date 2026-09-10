"""One focused B031 operation packet. No development constructor is called."""
from time import perf_counter, process_time
STARTED, CPU_STARTED = perf_counter(), process_time()
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
SUBJECT = ROOT/'packages/ember-qc/src/ember_qc/algorithms/factored/strip_transport_construction.py'
ORACLE = ROOT/'results/codex/042-results-review/pre-execution/ember_embedding_oracle.py'
TARGET = ROOT/'results/codex/b030-constructor/archive/target.json'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def q(u, w, k, j, z):
    # Explicit public Z12 linear formula, independent of the subject's decoder.
    return (((u*25+w)*4+k)*2+j)*12+z


class StripRisk(unittest.TestCase):
    guard = None
    observations = {}

    @classmethod
    def setUpClass(cls):
        pilot = load('_b031_check_pilot', ROOT/'scripts/codex/pilot.py')
        for name in ('minorminer', '_minorminer', 'busclique'):
            if name in sys.modules or importlib.util.find_spec(name) is not None:
                raise RuntimeError('prohibited dependency present: '+name)
        cls.guard = pilot.NoExternalEmbedder(); sys.meta_path.insert(0, cls.guard)
        cls.oracle = load('_b031_check_oracle', ORACLE)
        cls.subject = load('_b031_check_subject', SUBJECT)
        cls.support = cls.subject._load('support', SUBJECT.with_name('compiled_mobile_tree_construction.py'))
        cls.H, cls.F = cls.oracle.adjacency(json.loads(TARGET.read_text()))

    def engine(self, n, edges):
        # Nonconsecutive original labels exercise induced-prefix validation.
        labels = [101+17*i for i in range(n)]
        record = dict(nodes=labels, edges=[[labels[u], labels[v]] for u, v in edges])
        G, _ = self.oracle.adjacency(record)
        meter = self.support._Meter(perf_counter()+30.)
        return self.subject._Engine(G, self.H, 0, meter, STARTED, False, self.support)

    def state(self, engine, chains):
        values, labels = [frozenset() for _ in engine.G], [-1]*4800
        for u, sites in chains.items():
            values[u] = frozenset(sites)
            for site in sites:
                self.assertEqual(labels[site], -1)
                labels[site] = u
        return self.subject._State(values, labels)

    def independent(self, engine, state):
        vertices = state.introduced
        record = dict(nodes=[engine.vlabels[u] for u in sorted(vertices)],
                      edges=[[engine.vlabels[u], engine.vlabels[v]] for u in sorted(vertices)
                             for v in sorted(engine.G[u]) if v in vertices and u < v])
        G, E = self.oracle.adjacency(record)
        raw = {str(v): chain for v, chain in engine.mapping(state).items()}
        valid, reason, quality = self.oracle.embedding_quality(raw, G, E, self.H, self.F)
        self.assertTrue(valid, reason)
        return quality

    def transform_sites(self, chains, direction):
        # Fixture conjugation; correctness is assessed against original adjacency.
        return {u: {self.subject._linear(self.subject._orient(self.subject._coord(site), direction,
                                                            inverse=True)) for site in sites}
                for u, sites in chains.items()}

    def test_a_required_external_odd_internal_edges_and_directions(self):
        rail_a = {q(1,11,0,0,4), q(1,11,0,0,5)}
        rail_b = {q(1,11,1,1,4), q(1,11,1,1,5)}
        blockers = [q(0,w,k,j,5) for w in (9,10,11) for k in range(4) for j in range(2)]
        edges = [(u, 2+i) for i in range(24) if i < 8 or i >= 16 for u in (0,1)]
        vertex = 26
        e = self.engine(27, edges+[(0,vertex),(1,vertex)])
        chains = {0: rail_a, 1: rail_b, **{2+i: {site} for i, site in enumerate(blockers)}}
        before = self.state(e, chains); e.state = before
        self.assertEqual(self.independent(e, before)['qubits'], 28)
        common = set.intersection(*(set().union(*(self.H[x] for x in before.chains[u])) for u in (0,1)))
        self.assertEqual(common, set(blockers))
        self.assertFalse([site for site in common if before.labels[site] < 0])
        after, reason, added = e.transport(before, e.witnesses(before), 0, 5, 7)
        self.assertEqual((reason, added), ('prepared', 2))
        self.assertEqual(self.independent(e, after)['qubits'], 30)
        center = q(0,11,0,0,5)
        self.assertEqual(after.labels[center], -1)
        self.assertTrue(all(self.H[center] & after.chains[u] for u in (0,1)))
        transaction = e.prepare_birth(after, vertex, {center}, center, 'transport', 2, before.Q, [0,5,7])
        self.assertEqual(self.independent(e, transaction.state)['qubits'], 31)
        e.certify(transaction.state)
        self.observations['common_singleton'] = dict(initial_Q=28, transported_Q=30, full_Q=31,
            initial_common_singletons=0, new_common_site=center, bridge_Q=2,
            scope='common-singleton domain; no claim all larger ordinary trees were blocked')

        # Two distinct required source couplers: odd and internal near-cut cases.
        pair_chains = {0:{q(1,11,2,1,4)}, 1:{q(1,11,2,0,5)},
                       2:{q(1,11,3,1,4)}, 3:{q(0,10,3,0,5)}}
        e = self.engine(4, [(0,1),(2,3)])
        directions = []
        for direction in range(4):
            before = self.state(e, self.transform_sites(pair_chains, direction))
            self.independent(e, before)
            after, reason, added = e.transport(before, e.witnesses(before), direction, 5, 7)
            self.assertEqual((reason, added), ('prepared', 2))
            self.assertEqual(self.independent(e, after)['qubits'], 6)
            e.certify(after)
            directions.append(dict(direction=direction, Q=6, bridge_Q=2))
        self.observations['odd_internal_conjugates'] = directions

    def test_b_blocked_birth_actual_edges_atomicity_and_equal_Q_ties(self):
        center = q(0,10,0,0,5)
        halo = sorted(self.H[center])
        required = q(1,11,0,0,5)
        self.assertIn(required, halo)
        vertex = 1+len(halo)
        e = self.engine(vertex+1, [(0, 1+halo.index(required)), (0,vertex)])
        before = self.state(e, {0:{center}, **{1+i:{site} for i, site in enumerate(halo)}})
        e.state = before
        self.independent(e, before)
        e.birth(before, vertex)
        self.assertIsNone(e.pending)
        self.assertEqual(e.births[-1]['reason'], 'no_clean_common_root')
        R = e.witnesses(before)
        after, reason, added = e.transport(before, R, 0, 5, 7)
        self.assertEqual((reason, added), ('prepared', 0))
        self.assertEqual(self.independent(e, after)['qubits'], before.Q)
        e.birth(after, vertex, origin='transport', bridge_Q=0, entry_Q=before.Q, cut=[1,5,7])
        candidate = e.pending
        self.assertIsNotNone(candidate)
        self.assertEqual(candidate.state.Q, before.Q+1)
        self.independent(e, candidate.state)
        # Same total Q but an earlier declared direction must win even though
        # the previous completed transaction permits equality-based pruning.
        e.birth(after, vertex, origin='transport', bridge_Q=0, entry_Q=before.Q, cut=[0,5,7])
        self.assertEqual(e.pending.cut, [0,5,7])
        self.assertEqual(e.pending.state.Q, candidate.state.Q)
        self.assertGreaterEqual(e.births[-1]['materialized_roots'], 1)
        # The explicit key also excludes bridge cost as an unintended tie field.
        equal = self.subject._Transaction(candidate.state, vertex, candidate.root,
                    'transport', 1, before.Q-1, [0,4,7])
        e.retain(equal)
        self.assertIs(e.pending, equal)
        self.assertEqual(equal.state.Q, candidate.state.Q)

        production_certify = e.certify
        def stop_after_certificate(state):
            production_certify(state)
            raise self.support._Stop('injected before public commit')
        e.certify = stop_after_certificate
        try:
            with self.assertRaises(self.support._Stop):
                e.publish(candidate)
        finally:
            e.certify = production_certify
        self.assertIs(e.state, before)
        self.assertEqual(e.prefix_progress, [])
        e.publish(candidate)
        self.assertIs(e.state, candidate.state)
        self.assertEqual(e.stats['published_transports'], 1)
        self.assertEqual(e.first_valid['Q'], before.Q+1)

        # Reject an occupied destination, and an identity map at an empty A=0 slab.
        e2 = self.engine(1, [])
        occupied = self.state(e2, {0:{q(0,14,0,0,5)}})
        self.assertEqual(e2.transport(occupied, (), 0, 5, 7)[1], 'occupied_destination_band')
        stationary = self.state(e2, {0:{q(0,24,0,0,5)}})
        self.assertEqual(e2.transport(stationary, (), 0, 0, 1)[1], 'identical_map')
        # Remove the actual image of the required old contact, symmetrically.
        mapped_p, mapped_r = q(0,12,0,0,5), q(1,11,0,0,6)
        self.assertIn(mapped_r, self.H[mapped_p])
        broken = {site: set(adj) for site, adj in self.H.items()}
        broken[mapped_p].remove(mapped_r); broken[mapped_r].remove(mapped_p)
        saved_H, e.H = e.H, broken
        try:
            self.assertEqual(e.transport(before, R, 0, 5, 7)[1], 'missing_required_image_coupler')
        finally:
            e.H = saved_H
        self.observations['sealed_leaf'] = dict(initial_Q=before.Q, bridge_Q=0,
            full_Q=candidate.state.Q, ordinary_reachable_roots=0, transported_birth_Q=1,
            source_required_contacts_preserved=True, incidental_contacts_may_change=True,
            public_prefix_unchanged_on_interruption=True, equal_total_Q_tie_checked=True,
            occupied_band_rejected=True, identical_map_skipped=True, missing_image_edge_rejected=True)

    def test_c_deadline_salvage_partial_failure_and_fatal_credit(self):
        subject, support = self.subject, self.support
        source = {101:{118}, 118:{101}}
        real_run, real_clock = subject._Engine.run, subject.perf_counter
        rows = []
        for mode in ('complete_pending', 'partial_pending', 'late_complete_pending', 'fatal_after_valid'):
            clock_state = dict(late=False)
            def injected(engine):
                a, b = q(1,11,0,0,4), q(1,11,0,0,5)
                entry = self.state(engine, {})
                engine.state = entry
                if mode == 'partial_pending':
                    transaction = engine.prepare_birth(entry, 0, {a}, a, 'ordinary', 0, 0, None)
                else:
                    partial = self.state(engine, {0:{a}})
                    engine.state = partial
                    transaction = engine.prepare_birth(partial, 1, {b}, b, 'ordinary', 0, 1, None)
                engine.retain(transaction)
                self.independent(engine, transaction.state)
                if mode == 'fatal_after_valid':
                    engine.publish(transaction)
                    clock_state['late'] = True
                    raise ValueError('B031 injected post-valid fatal error')
                if mode == 'late_complete_pending':
                    clock_state['late'] = True
                raise support._Stop('injected scan cutoff after private candidate')
            subject._Engine.run = injected
            subject.perf_counter = lambda: real_clock()+(60. if clock_state['late'] else 0.)
            try:
                response = subject.strip_embed(source, self.H, timeout=30., seed=0)
            finally:
                subject._Engine.run, subject.perf_counter = real_run, real_clock
            raw = {str(v): chain for v, chain in response['embedding'].items()}
            G, E = self.oracle.adjacency(dict(nodes=[101,118], edges=[[101,118]]))
            valid, reason, quality = self.oracle.embedding_quality(raw, G, E, self.H, self.F)
            if mode == 'complete_pending':
                self.assertEqual(response['status'], 'SUCCESS')
                self.assertTrue(valid, reason)
                self.assertTrue(response['diag']['first_valid']['salvage'])
            elif mode == 'partial_pending':
                self.assertEqual(response['status'], 'FAILURE')
                self.assertEqual(response['diag']['final']['introduced'], 0)
                self.assertIsNone(response['diag']['first_valid'])
                self.assertFalse(valid)
            elif mode == 'late_complete_pending':
                self.assertEqual(response['status'], 'TIMEOUT')
                self.assertFalse(valid)
                self.assertGreater(response['diag']['deadline_overrun'], 0)
            else:
                self.assertEqual(response['status'], 'ERROR')
                self.assertIs(response['fatal'], True)
                self.assertIn('injected post-valid fatal error', response['error'])
                self.assertFalse(valid)
                self.assertEqual(response['diag']['first_valid']['Q'], 2)
                self.assertGreater(response['diag']['deadline_overrun'], 0)
            rows.append(dict(mode=mode, status=response['status'], independently_valid=valid,
                             first_valid=response['diag']['first_valid'], error=response['error'],
                             wall=response['diag']['wall'], cpu=response['diag']['cpu'],
                             stopped_by=response['diag']['stopped_by'], final=response['diag']['final'],
                             deadline_overrun=response['diag']['deadline_overrun']))
        self.assertEqual(self.guard.attempts, [])
        self.observations['publication'] = rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--manifest', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text())
    for name, expected in manifest['source_bindings'].items():
        assert sha(ROOT/name) == expected, name
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(StripRisk)
    result = unittest.TextTestRunner(stream=sys.stdout, verbosity=2).run(suite)
    changed = [name for name, expected in manifest['source_bindings'].items() if sha(ROOT/name) != expected]
    summary = dict(status='PASS' if result.wasSuccessful() and not changed else 'FAIL',
        tests=result.testsRun, failures=[(str(t), d) for t, d in result.failures],
        errors=[(str(t), d) for t, d in result.errors], source_changed=changed,
        manifest_sha256=sha(args.manifest), wall=perf_counter()-STARTED,
        cpu=process_time()-CPU_STARTED, observations=StripRisk.observations,
        prohibited_import_attempts=None if StripRisk.guard is None else StripRisk.guard.attempts,
        scope='three operation-risk groups, four wrapper calls with run replaced by fixture injection; '
              'no development constructor, global solver or full cut-domain search')
    with args.output.open('x') as stream:
        json.dump(summary, stream, indent=2, sort_keys=True, allow_nan=False); stream.write('\n')
    return 0 if summary['status'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
