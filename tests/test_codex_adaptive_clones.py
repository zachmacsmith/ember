"""C010's three focused private-primitive groups; no public constructor calls."""
import copy
import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch


SOURCE = Path(__file__).resolve().parents[1] / 'packages/ember-qc/src/ember_qc/algorithms/adaptive_clones.py'
spec = importlib.util.spec_from_file_location('_adaptive_clones_private_checks', SOURCE)
ac = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ac)


def graph(n, edges):
    result = [set() for _ in range(n)]
    for u, v in edges:
        result[u].add(v)
        result[v].add(u)
    return tuple(tuple(sorted(ns)) for ns in result)


def make(src, target, seed=0):
    return ac._State(src, target, ac._Budget(100., clock=lambda: 0.), seed)


def public_state(s):
    return copy.deepcopy((s.owners, s.aux, s.placement, s.timestamps, s.used,
                          s.serial, s.generation, s.internal_count))


def connected(vertices, neighbors):
    if not vertices:
        return False
    seen = {next(iter(vertices))}
    queue = list(seen)
    for u in queue:
        for v in neighbors[u]:
            if v in vertices and v not in seen:
                seen.add(v)
                queue.append(v)
    return seen == set(vertices)


def clone_oracle(s):
    original, internal = {}, []
    for u, ns in enumerate(s.aux):
        for v, eid in ns.items():
            if s.aux[v].get(u) != eid:
                return False
            if u < v:
                if eid >= 0:
                    if eid in original:
                        return False
                    original[eid] = tuple(sorted((s.owners[u], s.owners[v])))
                else:
                    if s.owners[u] != s.owners[v]:
                        return False
                    internal.append((u, v, eid))
    if original != dict(enumerate(s.original_edges)):
        return False
    for owner in range(len(s.src)):
        clones = {x for x, u in enumerate(s.owners) if u == owner}
        ns = {x: [y for y in s.aux[x] if s.owners[y] == owner] for x in clones}
        if not connected(clones, ns) or sum(map(len, ns.values())) != 2*(len(clones)-1):
            return False
    return len({eid for _, _, eid in internal}) == len(internal) == s.internal_count


def minor_oracle(chains, src, target):
    flat = [q for c in chains for q in c]
    return (len(chains) == len(src) and len(flat) == len(set(flat))
            and all(connected(set(c), target) for c in chains)
            and all(any(p in target[q] for q in chains[u] for p in chains[v])
                    for u, ns in enumerate(src) for v in ns if u < v))


class AdaptiveCloneChecks(unittest.TestCase):
    def test_clone_tree_edges_and_named_fixtures(self):
        star = graph(6, [(0, x) for x in range(1, 6)])
        ring = graph(12, [(i, (i+1) % 12) for i in range(12)])
        s = make(star, ring)
        self.assertTrue(clone_oracle(s))
        self.assertTrue(s.split(0, {}))
        old_internal_neighbor = next(y for y, eid in s.aux[0].items() if eid < 0)
        old_internal_id = s.aux[0][old_internal_neighbor]
        receipt = {}
        self.assertTrue(s.split(0, receipt))
        self.assertTrue(clone_oracle(s))
        self.assertNotIn(old_internal_neighbor, s.aux[0])
        self.assertEqual(s.aux[receipt['split']['new_clone']][old_internal_neighbor], old_internal_id)
        # Exact D has 40 sites, although the ranking prefix has only 32.
        empty = make(graph(1, []), graph(40, []), seed=7)
        d, choice = empty.domains(0), {}
        self.assertEqual(d[3], 40)
        self.assertEqual(empty.choose(0, d, choice), empty.order[0])
        self.assertEqual([p[0] for p in choice['prefix']], empty.order[:32])
        # More remaining support outranks an earlier permutation position.
        edge = make(graph(2, [(0, 1)]), graph(5, [(i, i+1) for i in range(4)]), seed=4)
        row = {}
        q = edge.choose(0, edge.domains(0), row)
        self.assertEqual(q, min((1, 2, 3), key=lambda p: edge.rank[p]))
        self.assertEqual(next(r[1:] for r in row['prefix'] if r[0] == q), [2, 2])
        # Private complete tiny run: known singleton solution must stay Q=n.
        path = graph(3, [(0, 1), (1, 2)])
        target = graph(5, [(i, i+1) for i in range(4)])
        singleton = make(path, target)
        diag = {}
        self.assertEqual(ac._run(singleton, diag), 'complete_auxiliary_placement')
        chains, _ = ac._snapshot(singleton)
        self.assertEqual(len(singleton.owners), 3)
        self.assertTrue(minor_oracle(chains, path, target))
        # A triangle cannot be a subgraph of cycle6. Three legal vertex splits
        # construct a cycle6 auxiliary graph, without a supplied constructor seed.
        tri = graph(3, [(0, 1), (1, 2), (0, 2)])
        cycle = graph(6, [(i, (i+1) % 6) for i in range(6)])
        t = make(tri, cycle)
        for x in (0, 1, 2):
            self.assertTrue(t.split(x, {}))
            self.assertTrue(clone_oracle(t))
        order, previous, current = [], None, 0
        while current not in order:
            order.append(current)
            following = [y for y in t.aux[current] if y != previous]
            previous, current = current, min(following)
        self.assertEqual(len(order), 6)
        for q, x in enumerate(order):
            t.publish_single(x, q)
        chains, _ = ac._snapshot(t)
        self.assertTrue(minor_oracle(chains, tri, cycle))
        self.assertTrue(ac._stats(chains, tri, cycle, t.b)['valid'])

    def test_revision_and_transactional_rollback(self):
        path = graph(3, [(0, 1), (1, 2)])
        target = graph(5, [(i, i+1) for i in range(4)])
        s = make(path, target)
        s.publish_single(0, 0)
        s.publish_single(2, 4)
        self.assertEqual(s.domains(1)[3], 0)
        r = {}
        self.assertTrue(s.revise(1, s.domains(1)[1], r))
        self.assertTrue(r['attempts'][-1]['committed'])
        self.assertTrue(minor_oracle(ac._snapshot(s)[0], path, target))
        self.assertEqual(len(set(s.timestamps.values())), 3)
        # No triangle fits a path: every bounded revision must restore exact entry.
        tri = graph(3, [(0, 1), (0, 2), (1, 2)])
        bad = make(tri, target)
        bad.publish_single(0, 1)
        bad.publish_single(1, 2)
        before, r = public_state(bad), {}
        self.assertFalse(bad.revise(2, bad.domains(2)[1], r))
        self.assertEqual(public_state(bad), before)
        self.assertTrue(r['attempts'])
        self.assertTrue(all(not a['committed'] for a in r['attempts']))
        # Interruption after private placement cannot leak timestamps or ownership.
        raw_choose, calls = bad.choose, [0]
        def interrupt(*args, **kwargs):
            answer = raw_choose(*args, **kwargs)
            calls[0] += 1
            if calls[0] == 2:
                raise ac._Stop('injected private interruption')
            return answer
        receipt = {}
        with patch.object(bad, 'choose', interrupt), self.assertRaises(ac._Stop):
            bad.revise(2, bad.domains(2)[1], receipt)
        self.assertEqual(public_state(bad), before)
        self.assertFalse(receipt['attempts'][0]['committed'])
        # Split copy interrupted after support/sort also leaves the public graph.
        star = make(graph(4, [(0, i) for i in range(1, 4)]), target)
        before = public_state(star)
        star.b.limit = star.b.units + 25
        split = {}
        with self.assertRaises(ac._Stop):
            star.split(0, split)
        self.assertEqual(public_state(star), before)
        self.assertFalse(split['split']['committed'])
        self.assertLessEqual(star.b.units, star.b.limit)

    def test_interruption_and_noncredit(self):
        src, target = graph(2, [(0, 1)]), graph(3, [(0, 1), (1, 2)])
        s = make(src, target)
        before = public_state(s)
        d = s.domains(0)
        s.b.limit = s.b.units+5
        row = {}
        with self.assertRaises(ac._Stop):
            s.choose(0, d, row)
        self.assertEqual(public_state(s), before)
        self.assertFalse(row['ranking_complete'])
        self.assertIsNone(row['selected'])
        good = make(src, target)
        good.publish_single(0, 0)
        good.publish_single(1, 1)
        response = dict(status='FAILURE', embedding={}, diag={})
        ac._finish(response, good, ['u', 'v'], ['a', 'b', 'c'], 100.)
        self.assertEqual(response['status'], 'SUCCESS')
        self.assertEqual(response['embedding'], {'u': ['a'], 'v': ['b']})
        now = [0.]
        good.b.clock = lambda: now[0]
        good.b.deadline = 1.
        raw_materialize = ac._materialize
        def late(*args):
            value = raw_materialize(*args)
            now[0] = 2.
            return value
        response = dict(status='FAILURE', embedding={}, diag={})
        with patch.object(ac, '_materialize', late):
            ac._finish(response, good, ['u', 'v'], ['a', 'b', 'c'], 1.)
        self.assertTrue(response['diag']['final']['valid'])
        self.assertEqual(response['status'], 'TIMEOUT')
        self.assertEqual(response['embedding'], {})
        self.assertEqual(response['diagnostic_embedding'], {'u': ['a'], 'v': ['b']})
        now[0], good.b.deadline = 0., 100.
        fatal = dict(status='FAILURE', embedding={}, diag={})
        ac._exception(fatal, ValueError('internal invariant failed'))
        ac._finish(fatal, good, ['u', 'v'], ['a', 'b', 'c'], 100.)
        self.assertEqual(fatal['status'], 'ERROR')
        self.assertEqual(fatal['embedding'], {})
        self.assertEqual(fatal['error'], 'ValueError: internal invariant failed')
        self.assertTrue(fatal['diag']['final']['valid'])
        expected = dict(status='FAILURE', embedding={}, diag={})
        ac._exception(expected, ac._InputError('retained input failure'))
        ac._finish(expected, good, ['u', 'v'], ['a', 'b', 'c'], 100.)
        self.assertEqual(expected['status'], 'FAILURE')
        self.assertEqual(expected['embedding'], {})
        self.assertIn('retained input failure', expected['error'])
        # A fully assigned clone map with a false original edge is never credited.
        good.placement[1] = 2
        invalid = dict(status='SUCCESS', embedding={'stale': [0]}, diag={})
        ac._finish(invalid, good, ['u', 'v'], ['a', 'b', 'c'], 100.)
        self.assertFalse(invalid['diag']['final']['valid'])
        self.assertEqual(invalid['status'], 'FAILURE')
        self.assertEqual(invalid['embedding'], {})


if __name__ == '__main__':
    unittest.main()
