"""Two specific atomic-addition checks; no full constructor or corpus call."""
import importlib.util
from pathlib import Path
import random
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('atomic_check_candidate', ROOT / 'packages/ember-qc/src/ember_qc/algorithms/atomic_regions.py')
candidate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(candidate)


def adjacency(n, edges):
    rows = [set() for _ in range(n)]
    for u, v in edges:
        rows[u].add(v)
        rows[v].add(u)
    return [tuple(sorted(row)) for row in rows]


def make(regions, src, adj):
    meter = candidate._elementary._Meter(time.perf_counter() + 30., {'stage_wall': {}})
    return candidate._State([set(r) for r in regions], src, adj, meter)


def snapshot(s):
    return ([set(r) for r in s.regions], list(s.owner), [list(r) for r in s.count],
            list(s.missing), dict(s.position), list(s.version), s.q)


def recount(s):
    owner = {}
    counts = [[0] * s.n for _ in range(s.n)]
    for u, region in enumerate(s.regions):
        assert region
        visited, todo = set(), [min(region)]
        while todo:
            q = todo.pop()
            if q in visited:
                continue
            visited.add(q)
            todo.extend(p for p in s.adj[q] if p in region and p not in visited)
        assert visited == region
        for q in region:
            assert q not in owner
            owner[q] = u
    for q, u in owner.items():
        for p in s.adj[q]:
            v = owner.get(p, -1)
            if q < p and v >= 0 and v != u:
                counts[u][v] += 1
                counts[v][u] += 1
    assert counts == s.count
    missing = {e for e in s.edges if not counts[e[0]][e[1]]}
    assert missing == set(s.missing)
    assert len(owner) == s.q
    return len(missing), len(owner)


class AtomicChecks(unittest.TestCase):
    def test_multisite_distinct_contact_delta_and_geometry_cache(self):
        src = adjacency(4, [(0, 1), (0, 2), (0, 3), (1, 2)])
        adj = adjacency(7, [(0, 1), (1, 2), (2, 3), (3, 4), (1, 5), (2, 5), (3, 6), (4, 5)])
        s = make([{0}, {4}, {5}, {6}], src, adj)
        before = snapshot(s)
        cached = s.distance(0)
        record = {}
        dm, change = s.path_delta(0, (1, 2, 3), record)
        self.assertEqual(snapshot(s), before)
        self.assertEqual(recount(s), (3, 4))
        self.assertEqual(dm, -3)
        self.assertEqual(change[2], {(0, 1): 1, (0, 2): 2, (0, 3): 1})
        s.resize(0, (1, 2, 3), 3, change)
        self.assertEqual(recount(s), (0, 7))
        self.assertIsNot(s.distance(0), cached)
        self.assertEqual(s.distance(0)[3], 0)

    def test_interrupted_bfs_score_and_prepublication_rollback(self):
        src = adjacency(3, [(0, 1), (0, 2), (1, 2)])
        adj = adjacency(6, [(0, 1), (1, 2), (2, 3), (3, 4), (4, 5), (0, 5)])
        for stop_key in ('atomic_bfs_vertices', 'atomic_score_adjacency'):
            with self.subTest(stage=stop_key):
                s = make([{1}, {0}, {2}], src, adj)
                before = snapshot(s)
                original_tick = s.meter.tick
                def tick(key, count=1):
                    original_tick(key, count)
                    if key == stop_key:
                        s.meter.deadline = -1
                        s.meter.check()
                s.meter.tick = tick
                row = {'proposal_prefix_complete': False}
                with self.assertRaises(candidate._elementary._Expired):
                    candidate._propose(s, 'addition', random.Random(0), s.meter, row, .25)
                self.assertFalse(row['proposal_prefix_complete'])
                self.assertIn(row['atomic']['stage'], ('bfs', 'path_score'))
                self.assertEqual(snapshot(s), before)
        s = make([{1}, {0}, {2}], src, adj)
        before = snapshot(s)
        dm, change = s.path_delta(1, (5, 4, 3), {})
        self.assertEqual(dm, -1)
        s.meter.deadline = -1
        with self.assertRaises(candidate._elementary._Expired):
            s.resize(1, (5, 4, 3), 3, change)
        self.assertEqual(snapshot(s), before)
        self.assertEqual(recount(s), (1, 3))


if __name__ == '__main__':
    unittest.main(verbosity=2)
