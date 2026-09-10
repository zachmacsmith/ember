"""Focused B030 rail-patch accounting check; no complete constructor run."""
from time import perf_counter, process_time
STARTED, CPU_STARTED = perf_counter(), process_time()
import argparse
from collections import deque
import hashlib
import importlib.util
import importlib.metadata
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
SUBJECT = ROOT/'packages/ember-qc/src/ember_qc/algorithms/factored/disconnected_ownership_construction.py'
ORACLE = ROOT/'results/codex/042-results-review/pre-execution/ember_embedding_oracle.py'
TARGET = ROOT/'results/codex/b029-constructor/archive/target.json'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def rail(z):
    return (((0*25+12)*4+0)*2+0)*12+z


def direct_field(target, starts):
    distance = {q: 0 for q in starts}; queue = deque(starts)
    while queue:
        q = queue.popleft()
        for r in target[q]:
            if r not in distance:
                distance[r] = distance[q]+1; queue.append(r)
    return distance


class RailPatch(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pilot = load('_b030_check_existing_pilot', ROOT/'scripts/codex/pilot.py')
        for name in ('minorminer', '_minorminer', 'busclique'):
            if name in sys.modules or importlib.util.find_spec(name) is not None:
                raise RuntimeError('prohibited dependency present: '+name)
        cls.guard = pilot.NoExternalEmbedder(); sys.meta_path.insert(0, cls.guard)
        cls.oracle = load('_b030_check_original_oracle', ORACLE)
        cls.subject = load('_b030_check_subject', SUBJECT)
        cls.support = cls.subject._load('support', SUBJECT.with_name('compiled_mobile_tree_construction.py'))
        cls.target_record = json.loads(TARGET.read_text())
        cls.H, cls.F = cls.oracle.adjacency(cls.target_record)
        # Source labels deliberately differ from the candidate's owner indices.
        cls.source_record = {'nodes': [101, -9], 'edges': [[101, -9]]}
        cls.G, cls.E = cls.oracle.adjacency(cls.source_record)
        cls.meter = cls.support._Meter(perf_counter()+30)
        cls.engine = cls.subject._Engine(cls.G, cls.H, 0, cls.meter, STARTED, False, cls.support)
        cls.observations = {}

    def setUp(self):
        e = self.engine
        e.state = None; e.connected_only = False; e.lam = [1]; e.gamma = [1, 1]
        e.incumbent = e.first_valid = None; e.events = []
        self.a, self.b, self.c, self.d = map(rail, (3, 4, 5, 6))
        e.state = e.prepare({0: {self.a, self.b}, 1: {self.c}})

    def independent(self, state):
        raw = {str(k): v for k, v in self.engine.mapping(state).items()}
        return self.oracle.embedding_quality(raw, self.G, self.E, self.H, self.F)

    def moved(self):
        e = self.engine
        patch = sorted([self.b, self.c], key=e.rank.__getitem__)
        offsets, images = e.arrays.translations(patch, e.state.labels)
        selected = [i for i, pair in enumerate(offsets.tolist()) if pair == [2, 0]]
        self.assertEqual(len(selected), 1)
        self.assertNotIn([-2, 0], offsets.tolist())  # would overwrite outside a
        image = list(map(int, images[selected[0]]))
        self.assertEqual(dict(zip(patch, image)), {self.b: self.c, self.c: self.d})
        changes = e.patch_changes(patch, image)
        return e.prepare(changes)

    def test_a_overlapping_patch_and_actual_cheapest_merge(self):
        e = self.engine
        self.assertTrue(self.independent(e.state)[0])
        candidate = self.moved()
        self.assertEqual(candidate.chains, (frozenset([self.a, self.c]), frozenset([self.d])))
        self.assertEqual(e.snapshot(candidate), dict(Q=3, M=0, D=0, P=1,
                         component_excess=1, fragmented_owners=1, E=4))
        self.assertEqual(self.independent(candidate)[1], 'disconnected_chain')
        row = {}
        self.assertTrue(e.admit(candidate, .9, row))  # measured ΔE=+1 permitted
        e.incumbent_check()
        self.assertIsNone(e.incumbent)
        merge = {}
        changes = e.merge(0, 0., merge)
        bridges = [q for q in self.H[self.a] & self.H[self.c] if candidate.labels[q] == -1]
        self.assertTrue(bridges)
        best = min(bridges, key=e.rank.__getitem__)
        component = candidate.components[0][0]
        start = next(iter(component)); end = self.c if start == self.a else self.a
        self.assertEqual(merge['merge_cost'], 1)
        self.assertEqual(merge['merge_path'], [start, best, end])
        repaired = e.prepare(changes)
        self.assertEqual(repaired.Q, 4)
        self.assertEqual(repaired.debts, (0, 0))
        self.assertTrue(self.independent(repaired)[0])
        e.certify(repaired)  # unchanged production validator, original labels
        self.observations['fixture'] = dict(initial_Q=3, moved_Q=3, moved_P=1,
            merge_Q=4, least_free_merge_cost=1, tied_free_bridges=len(bridges),
            selected_tie_path=merge['merge_path'], delta_E=row['delta_E'])

    def test_b_cache_identity_and_component_mst(self):
        e = self.engine
        old_sites = e.state.chains[0]
        old_field = e.arrays.field(old_sites)
        moved = self.moved(); new_field = e.arrays.field(moved.chains[0])
        self.assertEqual(old_field[self.d], 2)
        self.assertEqual(new_field[self.d], 1)
        self.assertIs(e.arrays.field(old_sites), old_field)
        self.assertFalse(old_field.flags.writeable)
        for sites, field in ((old_sites, old_field), (moved.chains[0], new_field)):
            direct = direct_field(self.H, sites)
            self.assertTrue(all(field[q] == direct[q] for q in self.H))
        # Same rail fixture extended to three components: compare all three
        # possible component spanning trees, not an alternative embedding search.
        sites = {self.a, self.c, rail(9)}
        components = e.components(sites)
        self.assertEqual(len(components), 3)
        weights = {}
        for i, ci in enumerate(components):
            field = direct_field(self.H, ci)
            for j in range(i):
                weights[j, i] = max(0, min(field[q] for q in components[j])-1)
        expected = min(weights[0, 1]+weights[0, 2], weights[0, 1]+weights[1, 2],
                       weights[0, 2]+weights[1, 2])
        self.assertEqual(e.debt(components), expected)
        self.observations['distance_cache'] = dict(old_distance=2, new_distance=1,
                                                  three_component_mst=expected)

    def test_c_ablation_and_prepublication_interruption(self):
        e = self.engine; entry = e.state
        candidate = self.moved()
        e.connected_only = True; row = {}
        self.assertFalse(e.admit(candidate, .9, row))
        self.assertEqual(row['reason'], 'connected_ablation')
        self.assertIs(e.state, entry)
        e.connected_only = False
        clock = e.m.clock
        def stop_publication():
            if e.m.stage == 'publication':
                raise self.support._Stop('publication')
            return clock()
        e.m.clock = stop_publication
        try:
            with self.assertRaises(self.support._Stop):
                e.admit(candidate, .9, {})
        finally:
            e.m.clock = clock
        self.assertIs(e.state, entry)
        self.assertIsNone(e.incumbent)
        self.assertTrue(self.independent(e.state)[0])
        self.assertEqual(self.guard.attempts, [])
        self.observations['rollback'] = dict(ablation_preserved_entry=True,
                                            interrupted_publication_preserved_entry=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--manifest', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    manifest_path = Path(args.manifest)
    manifest = json.loads(manifest_path.read_text())
    for relative, expected in manifest['source_bindings'].items():
        if sha(ROOT/relative) != expected:
            raise RuntimeError('before-check source identity mismatch: '+relative)
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(RailPatch)
    result = unittest.TextTestRunner(stream=sys.stdout, verbosity=2).run(suite)
    changed = [p for p, h in manifest['source_bindings'].items() if sha(ROOT/p) != h]
    guard = getattr(RailPatch, 'guard', None)
    final = dict(status='PASS' if result.wasSuccessful() and not changed else 'FAIL',
                 tests=result.testsRun, failures=result.failures, errors=result.errors,
                 wall=perf_counter()-STARTED, cpu=process_time()-CPU_STARTED,
                 observations=getattr(RailPatch, 'observations', {}),
                 prohibited_import_attempts=None if guard is None else guard.attempts,
                 source_changed=changed, manifest_sha256=sha(manifest_path),
                 versions={name: importlib.metadata.version(name) for name in ('numpy', 'scipy', 'networkx')},
                 scope='one rail fixture with cache/MST/ablation/rollback checks; no constructor run')
    final['failures'] = [(str(test), detail) for test, detail in result.failures]
    final['errors'] = [(str(test), detail) for test, detail in result.errors]
    with Path(args.output).open('x') as out:
        json.dump(final, out, sort_keys=True, indent=2, allow_nan=False); out.write('\n')
    return 0 if final['status'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
