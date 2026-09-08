"""Bounded mechanism checks; no constructor, corpus, MM, or busclique call."""
from collections import Counter
import hashlib
import importlib.util
from pathlib import Path
import random
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'packages/ember-qc/src/ember_qc/algorithms/variable_regions.py'
spec = importlib.util.spec_from_file_location('isolated_variable_regions', SOURCE)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def adjacency(n, edges):
    rows = [set() for _ in range(n)]
    for u, v in edges:
        rows[u].add(v)
        rows[v].add(u)
    return [tuple(sorted(row)) for row in rows]


def recount(state):
    counts = [[0] * state.n for _ in range(state.n)]
    owner = {}
    for u, region in enumerate(state.regions):
        assert region
        reached, todo = set(), [min(region)]
        while todo:
            q = todo.pop()
            if q in reached:
                continue
            reached.add(q)
            todo.extend(p for p in state.adj[q] if p in region and p not in reached)
        assert reached == region
        for q in region:
            assert q not in owner
            owner[q] = u
    for q, u in owner.items():
        for p in state.adj[q]:
            if q < p and p in owner and owner[p] != u:
                counts[u][owner[p]] += 1
                counts[owner[p]][u] += 1
    missing = {edge for edge in state.edges if not counts[edge[0]][edge[1]]}
    assert counts == state.count
    assert missing == set(state.missing)
    assert len(owner) == state.q
    assert [owner.get(q, -1) for q in range(len(state.adj))] == state.owner
    return len(missing), len(owner)


def state(regions, src, target):
    diag = {'stage_wall': {}}
    meter = module._Meter(time.perf_counter() + 30, diag)
    return module._State([set(r) for r in regions], src, target, meter)


class Mechanisms(unittest.TestCase):
    def test_signed_partial_growth_deletion_and_cache(self):
        src = adjacency(3, [(0, 1), (1, 2), (0, 2)])
        target = adjacency(6, [(q, q + 1) for q in range(5)] + [(5, 0)])
        s = state([{0}, {1}, {2}], src, target)
        self.assertEqual(recount(s), (1, 3))
        old = s.distance(2)
        self.assertEqual(old[3], 1)
        self.assertIs(s.distance(2), old)
        dm, change = s.resize_delta(2, 3, 1)
        s.resize(2, 3, 1, change)
        self.assertEqual((dm, recount(s)), (0, (1, 4)))
        new = s.distance(2)
        self.assertIsNot(new, old)
        self.assertEqual(new[3], 0)
        self.assertTrue(s.removable(3))
        dm, change = s.resize_delta(2, 3, -1)
        s.resize(2, 3, -1, change)
        self.assertEqual((dm, recount(s)), (0, (1, 3)))
        self.assertIsNot(s.distance(2), new)
        self.assertFalse(s.removable(2))

    def test_exact_contacts_on_all_four_moves(self):
        # Multiple couplers between owners must not count as distinct contacts.
        src = adjacency(4, [(0, 1), (1, 2), (2, 3), (0, 3), (0, 2)])
        target = adjacency(8, [(0, 1), (1, 2), (2, 3), (3, 4), (4, 5),
                               (5, 6), (6, 7), (7, 0), (0, 2), (1, 3), (2, 4)])
        s = state([{0, 1}, {2, 3}, {4}, {5}], src, target)
        before = recount(s)
        dm, change = s.swap_delta(0, 2)
        s.swap(0, 2, change)
        after = recount(s)
        self.assertEqual((after[0] - before[0], after[1] - before[1]), (dm, 0))
        self.assertTrue(s.removable(1))
        before = after
        dm, change = s.transfer_delta(1, 1)
        s.transfer(1, 1, change)
        after = recount(s)
        self.assertEqual((after[0] - before[0], after[1] - before[1]), (dm, 0))
        for q, sign in ((6, 1), (6, -1)):
            before = recount(s)
            dm, change = s.resize_delta(3, q, sign)
            s.resize(3, q, sign, change)
            after = recount(s)
            self.assertEqual((after[0] - before[0], after[1] - before[1]), (dm, sign))
        # Geometry changes invalidate destination caches after swap and transfer.
        cached = s.distance(1)
        dm, change = s.swap_delta(1, 3)
        s.swap(1, 3, change)
        self.assertIsNot(s.distance(1), cached)
        recount(s)

    def test_interrupted_prefix_and_commit_deadline(self):
        src = adjacency(3, [(0, 1), (1, 2), (0, 2)])
        target = adjacency(6, [(q, q + 1) for q in range(5)] + [(5, 0)])
        s = state([{0}, {1}, {2}], src, target)
        original = [set(r) for r in s.regions]
        row = {'proposal_prefix_complete': False}
        called = []
        original_delta = s.resize_delta
        def expire_after_score(*args):
            result = original_delta(*args)
            called.append(result)
            s.meter.deadline = -1
            return result
        s.resize_delta = expire_after_score
        with self.assertRaises(module._Expired):
            module._propose(s, 'addition', random.Random(0), s.meter, row, .25)
        self.assertTrue(called)
        self.assertFalse(row['proposal_prefix_complete'])
        self.assertTrue(row['scored'])
        self.assertEqual(s.regions, original)
        with self.assertRaises(module._Expired):
            s.resize(2, 3, 1, {})
        self.assertEqual(s.regions, original)
        recount(s)


if __name__ == '__main__':
    unittest.main(verbosity=2)
