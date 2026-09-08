"""Small semantic checks for B018; the three frozen reach calls live elsewhere."""
import copy
import importlib.util
import itertools
from pathlib import Path
import time
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
PATH = ROOT / 'packages/ember-qc/src/ember_qc/algorithms/factored/movable_contact.py'
spec = importlib.util.spec_from_file_location('b018_primitive', PATH)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def meter():
    return m._Meter(time.perf_counter() + 5, 100000)


def small():
    return ({0: [0], 1: [1, 2]}, {0: (1,), 1: (0,)},
            {0: (1,), 1: (0, 2), 2: (1,)}, {(0, 1): (0, 1)}, [(0, 1)])


class ContactChecks(unittest.TestCase):
    def test_terminal_multiplicity_and_tree_pruning(self):
        tree = {0: {1, 2, 3}, 1: {0}, 2: {0}, 3: {0}}
        old = copy.deepcopy(tree)
        self.assertEqual(m._trim(tree, {1, 2}, dict(enumerate(range(4))), meter()),
                         {0: {1, 2}, 1: {0}, 2: {0}})
        self.assertEqual(m._trim(tree, set(), dict(enumerate(range(4))), meter()), {})
        self.assertEqual(tree, old)
        terms = m._terminal_lists([0, 1, 2], {(0, 1): (4, 5), (0, 2): (4, 6)}, meter())
        self.assertEqual(terms, {0: [4, 4], 1: [5], 2: [6]})

    def test_actual_union_energy_and_node_increments(self):
        self.assertEqual(m._score({10: {0, 1}, 20: {1, 2}}, meter()),
                         dict(qubits=4, overlap=1, energy=5))
        owners = {1: {10, 20}, 2: {20}, 3: {10}}
        self.assertEqual(m._increment(1, {1}, 10, owners), 0)
        self.assertEqual(m._increment(2, {1}, 10, owners), 2)
        self.assertEqual(m._increment(3, {1}, 10, owners), 1)
        self.assertEqual(m._increment(4, {1}, 10, owners), 1)

    def test_original_contact_obligation_cannot_disappear(self):
        H = {0: (1,), 1: (0, 2), 2: (1,)}
        m._certificate({0: {0, 1}, 1: {2}}, {(0, 1): (1, 2)}, H, {0: 0, 1: 1, 2: 2}, meter())
        with self.assertRaisesRegex(ValueError, 'witness'):
            m._certificate({0: {0}, 1: {2}}, {(0, 1): (1, 2)}, H, {0: 0, 1: 1, 2: 2}, meter())

    def test_work_and_private_route_interruptions_rollback(self):
        args = small(); before = copy.deepcopy(args)
        candidate, info = m.propose_contacts(*args, max_work=0)
        self.assertIsNone(candidate); self.assertEqual(info['status'], 'work_limit')
        self.assertEqual(info['work'], 0); self.assertEqual(args, before)
        with patch.object(m, '_attach', side_effect=m._Stop('work_limit')):
            candidate, info = m.propose_contacts(*args)
        self.assertIsNone(candidate); self.assertFalse(info['accepted'])
        self.assertFalse(info['combinations'][0]['complete'])
        self.assertEqual(args, before)
        self.assertEqual(sum(info['stage_units'].values()), info['work'])

    def test_expired_before_work_and_late_final_publication(self):
        args = small(); before = copy.deepcopy(args)
        candidate, info = m.propose_contacts(*args, deadline=time.perf_counter() - 1)
        self.assertIsNone(candidate); self.assertEqual(info['work'], 0)
        clock = [0.0]
        def crossing_product(*pools):
            yield from itertools.product(*pools)
            clock[0] = 5.125
        with patch.object(m, 'perf_counter', side_effect=lambda: clock[0]), patch.object(m, 'product', crossing_product):
            candidate, info = m.propose_contacts(*args)
        self.assertIsNone(candidate); self.assertEqual(info['status'], 'deadline')
        self.assertIn('best_combination', info)
        self.assertEqual(info['wall'], 5.125)
        self.assertEqual(info['deadline_overrun'], .125)
        self.assertEqual(args, before)

    def test_outside_chain_lists_survive_every_complete_proposal(self):
        E = {0: [0], 1: [1], 2: [2, 3], 3: [5, 4]}
        S = {0: (1,), 1: (0, 2), 2: (1, 3), 3: (2,)}
        H = {q: tuple(p for p in (q-1, q+1) if 0 <= p < 6) for q in range(6)}
        links = {(0, 1): (0, 1), (1, 2): (1, 2), (2, 3): (3, 4)}
        before = copy.deepcopy((E, S, H, links))
        _, info = m.propose_contacts(E, S, H, links, [(1, 2)])
        self.assertEqual(info['status'], 'no_improvement')
        self.assertTrue(info['combinations'])
        for row in info['combinations']:
            if 'embedding' in row:
                self.assertEqual(row['embedding'][0], [0])
                self.assertEqual(row['embedding'][3], [5, 4])
        self.assertEqual((E, S, H, links), before)

    def test_invalid_integer_labels_and_asymmetric_graph(self):
        args = list(small()); args[1] = {0: (1,), 1: ()}
        candidate, info = m.propose_contacts(*args)
        self.assertIsNone(candidate); self.assertEqual(info['status'], 'invalid_input')
        args = list(small()); args[3] = {(False, 1): (0, 1)}
        candidate, info = m.propose_contacts(*args)
        self.assertIsNone(candidate); self.assertEqual(info['status'], 'invalid_input')


if __name__ == '__main__':
    unittest.main()
