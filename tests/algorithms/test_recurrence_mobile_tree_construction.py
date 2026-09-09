"""Only B027's exact-key/publication risks; no full constructor calls here."""
import importlib.util
from pathlib import Path
import time
import unittest

ROOT = Path(__file__).resolve().parents[2]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


helper = load('b026_fixtures', ROOT / 'tests/algorithms/test_mobile_tree_construction.py')
SOURCE = helper.SOURCE.with_name('recurrence_mobile_tree_construction.py')
mod = load('isolated_b027', SOURCE)


def engine():
    G = helper.path(2)
    H = helper.graph(4, [(0, 1), (1, 2), (2, 3), (3, 0)])
    e = mod._Engine(G, H, mod._Meter(time.perf_counter() + 20), 0)
    e.state = helper.state(e, {0: [0, 1], 1: [2, 3]})
    e.quality = True
    return e


def inherited_projection(text):
    start, stop = text.index('    def quality_key(self):'), text.index('    def run(self, began):')
    text = text[:start] + text[stop:]
    text = text.replace('B027: B026 with exact complete-quality-sweep recurrence termination.',
                        'B026: one fresh tree-construction trajectory with mobile contact boundaries.')
    text = text.replace('notes/codex/tracks/b_027_recurrence_policy.md. Counters measure work;',
                        'notes/codex/tracks/b_026_policy.md.  Counters measure work;')
    for chunk in [
        '        quality_seen, quality_registered = {}, False\n',
        '            if self.quality and not quality_registered:\n'
        '                quality_seen, repeated = self.check_recurrence(quality_seen, 0)\n'
        '                quality_registered = True\n',
        "                quality_seen, repeated = self.check_recurrence(quality_seen, self.stats['quality_sweeps'])\n"
        '                if repeated:\n'
        "                    return 'quality_state_recurrence'\n",
    ]:
        assert text.count(chunk) == 1
        text = text.replace(chunk, '')
    text = text.replace("algorithm='recurrence-mobile-tree-construction', version='B027'",
                        "algorithm='mobile-tree-construction', version='B026'")
    text = text.replace("quality_progress=engine.progress,\n                                recurrence=getattr(engine, 'recurrence_info', None))",
                        'quality_progress=engine.progress)')
    return text


class RecurrenceChecks(unittest.TestCase):
    def test_full_key_distinguishes_equal_Q_contacts_and_cached_state(self):
        e = engine(); baseline = e.state
        first, _ = e.quality_key()
        e.state = helper.state(e, {0: [2, 3], 1: [0, 1]})
        self.assertNotEqual(e.quality_key()[0], first)
        e.state = helper.state(e, baseline.chains)
        pair = e.state.witnesses[0, 1]
        e.state.witnesses[0, 1] = (1, 2) if pair != (1, 2) else (0, 3)
        self.assertTrue(helper.original_valid(e.G, e.H, e.state.chains))
        self.assertNotEqual(e.quality_key()[0], first)
        e.state = helper.state(e, baseline.chains)
        e.state.trees[0] = {1: None, 0: 1}
        if e.state.trees[0] == baseline.trees[0]:
            e.state.trees[0] = {0: None, 1: 0}
        self.assertNotEqual(e.quality_key()[0], first)
        e.state = baseline
        self.assertEqual(e.quality_key()[0], first)

    def test_exact_repeat_not_objective_or_digest_stops(self):
        e = engine(); empty = {}
        seen, repeated = e.check_recurrence(empty, 0)
        self.assertFalse(repeated)
        self.assertEqual(empty, {})
        next_seen, repeated = e.check_recurrence(seen, 3)
        self.assertTrue(repeated)
        self.assertIs(next_seen, seen)
        self.assertEqual(e.recurrence_info['first_seen'], 0)
        self.assertEqual(e.recurrence_info['period'], 3)
        self.assertEqual(len(seen), 1)

    def test_interrupted_key_or_private_storage_cannot_publish(self):
        for cut in ('construction', 'storage'):
            e = engine(); old, prices, seen = e.state, dict(e.prices), {}
            step = e.m.step
            def interrupted(kind='site', amount=1):
                step(kind, amount)
                if kind == ('recurrence_tree_site' if cut == 'construction' else 'recurrence_storage_item'):
                    raise mod._Stop(cut)
            e.m.step = interrupted
            with self.assertRaises(mod._Stop):
                e.check_recurrence(seen, 0)
            self.assertEqual(seen, {})
            self.assertIs(e.state, old)
            self.assertEqual(e.prices, prices)
            self.assertFalse(e.recurrence_info['complete'])
            self.assertFalse(e.recurrence_info['repeated'])
            self.assertEqual(e.stats['recurrence_keys_examined'], 0)

    def test_exact_inherited_source_projection(self):
        self.assertEqual(inherited_projection(SOURCE.read_text()), helper.SOURCE.read_text())


if __name__ == '__main__':
    unittest.main()
