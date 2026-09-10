"""One injected post-incumbent error; no complete-constructor search."""
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


class FatalAfterIncumbent(unittest.TestCase):
    observations = {}
    guard = None

    def test_post_incumbent_valueerror_overrides_synthetic_late_clock(self):
        pilot = load('_b030_error_pilot', ROOT/'scripts/codex/pilot.py')
        for name in ('minorminer', '_minorminer', 'busclique'):
            self.assertNotIn(name, sys.modules)
            self.assertIsNone(importlib.util.find_spec(name))
        type(self).guard = pilot.NoExternalEmbedder()
        sys.meta_path.insert(0, self.guard)
        oracle = load('_b030_error_oracle', ORACLE)
        subject = load('_b030_error_subject', SUBJECT)
        source_record = {'nodes': [101, -9], 'edges': [[101, -9]]}
        target_record = json.loads(TARGET.read_text())
        G, E = oracle.adjacency(source_record)
        H, F = oracle.adjacency(target_record)
        real_clock, run = subject.perf_counter, subject._Engine.run
        injected = dict(late=False, run_calls=0, independent_valid=False)

        def fixture_then_error(engine):
            injected['run_calls'] += 1
            # The same public rail fixture as check001, with a real production
            # certificate followed by a separately verified original minor.
            a, b, c = 1155, 1156, 1157
            engine.state = engine.prepare({0: {a, b}, 1: {c}})
            engine.initial = engine.snapshot()
            engine.incumbent_check()
            self.assertIsNotNone(engine.incumbent)
            raw = {str(v): chain for v, chain in engine.mapping(engine.incumbent).items()}
            valid, reason, quality = oracle.embedding_quality(raw, G, E, H, F)
            self.assertTrue(valid, reason)
            injected.update(independent_valid=valid, certified_Q=quality['qubits'])
            # No sleep or late work: the one case also checks that separately
            # recorded clock overrun cannot erase a known implementation error.
            injected['late'] = True
            raise ValueError('B030 focused injected post-incumbent runtime error')

        subject._Engine.run = fixture_then_error
        subject.perf_counter = lambda: real_clock() + (60. if injected['late'] else 0.)
        try:
            response = subject.ownership_embed(G, H, timeout=30., seed=0)
        finally:
            subject._Engine.run, subject.perf_counter = run, real_clock
        self.assertEqual(response['status'], 'ERROR')
        self.assertIs(response['fatal'], True)
        self.assertIs(response['diag']['fatal'], True)
        self.assertIn('injected post-incumbent runtime error', response['error'])
        self.assertEqual(response['embedding'], {})
        self.assertEqual(response['diag']['first_valid']['Q'], 3)
        self.assertEqual(len(response['diag']['quality_progress']), 1)
        self.assertGreater(response['diag']['deadline_overrun'], 0)
        self.assertFalse(oracle.embedding_quality(response['embedding'], G, E, H, F)[0])
        self.assertEqual(self.guard.attempts, [])
        self.observations.update(injected, reported_status=response['status'],
            top_level_error=response['error'], first_valid=response['diag']['first_valid'],
            final_embedding_independently_invalid=True,
            synthetic_deadline_overrun=response['diag']['deadline_overrun'])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--manifest', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text())
    for name, expected in manifest['source_bindings'].items():
        assert sha(ROOT/name) == expected, name
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(FatalAfterIncumbent)
    result = unittest.TextTestRunner(stream=sys.stdout, verbosity=2).run(suite)
    changed = [p for p, h in manifest['source_bindings'].items() if sha(ROOT/p) != h]
    guard = FatalAfterIncumbent.guard
    summary = dict(status='PASS' if result.wasSuccessful() and not changed else 'FAIL',
        tests=result.testsRun, failures=[(str(t), d) for t, d in result.failures],
        errors=[(str(t), d) for t, d in result.errors], source_changed=changed,
        manifest_sha256=sha(args.manifest), wall=perf_counter()-STARTED,
        cpu=process_time()-CPU_STARTED, observations=FatalAfterIncumbent.observations,
        prohibited_import_attempts=None if guard is None else guard.attempts,
        scope='one wrapper call with search replaced by fixed fixture and error; no development constructor; synthetic late clock only')
    with args.output.open('x') as stream:
        json.dump(summary, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write('\n')
    return 0 if summary['status'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
