"""Three bounded primitive groups; never call the public constructor."""
import importlib.util
import math
from pathlib import Path
import unittest
from unittest.mock import patch


SOURCE = Path(__file__).resolve().parents[1] / 'packages/ember-qc/src/ember_qc/algorithms/connected_domains.py'
spec = importlib.util.spec_from_file_location('_independent_connected_domains', SOURCE)
cd = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cd)


def graph(n, edges):
    a = [set() for _ in range(n)]
    for u, v in edges:
        a[u].add(v)
        a[v].add(u)
    return tuple(tuple(sorted(x)) for x in a)


def connected(chain, adj):
    allowed = set(chain)
    if not allowed:
        return False
    seen, stack = {next(iter(allowed))}, []
    stack.extend(seen)
    while stack:
        for p in adj[stack.pop()]:
            if p in allowed and p not in seen:
                seen.add(p)
                stack.append(p)
    return seen == allowed


def oracle(chains, src, adj):
    if len(chains) != len(src) or not all(connected(c, adj) for c in chains):
        return False
    flat = [q for c in chains for q in c]
    if len(flat) != len(set(flat)):
        return False
    return all(any(p in adj[q] for q in chains[u] for p in chains[v])
               for u, ns in enumerate(src) for v in ns if u < v)


def budget():
    return cd._Budget(100., clock=lambda: 0.)


class ConnectedDomainChecks(unittest.TestCase):
    def test_connectivity_contact_and_overlap(self):
        src, adj = graph(2, [(0, 1)]), graph(4, [(0, 1), (1, 2), (2, 3)])
        domains = (((0,), (0, 1)), ((0,), (1, 2)))
        m = cd._Model(domains, src, adj, budget())
        self.assertFalse(m.compatibility[0, 1][0][0])
        self.assertTrue(m.compatibility[0, 1][0][1])
        for chains in (((0,), (0,)), ((0, 1), (1, 2)), ((0,), (1, 2))):
            self.assertEqual(cd._stats(chains, src, adj, budget())['valid'], oracle(chains, src, adj))
        self.assertFalse(cd._stats(((0, 2), (1,)), src, adj, budget())['connected_nonempty'])
        with self.assertRaises(ValueError):
            cd._Model((((-1,),), ((1,),)), src, adj, budget())
        # Contact probabilities deduplicate couplers; overlap counts owner incidences.
        prob = [[.25, .75], [.5, .5]]
        fields = m.fields(prob)
        self.assertAlmostEqual(fields[1][0][1], 1.)
        self.assertAlmostEqual(m.expected(prob, fields)['missing'], .125)
        self.assertAlmostEqual(m.costs(prob, 4, fields)[0][0], 1.+4*(.5+.5))
        # One private generator invocation from hand-made domains; no constructor.
        src3 = graph(3, [(0, 1), (1, 2)])
        adj6 = graph(6, [(i, i+1) for i in range(5)])
        m3 = cd._Model((((0,),), ((2,),), ((5,),)), src3, adj6, budget())
        records = []
        generated = cd._regenerate(m3, [[1.]]*3, [tuple(range(6))]*3, 4, None, records)
        self.assertTrue(all(connected(c, adj6) for row in generated for c in row))
        self.assertTrue(all(1 <= len(row) <= 8 for row in generated))
        self.assertTrue(all(r['completed'] for r in records))
        self.assertTrue(any(len(c) > 1 for row in generated for c in row))

    def test_probability_and_known_feasible_domains(self):
        # Unique feasible choice for u is {2}; isolate w owns {0}, v owns {1}.
        # This supplied domain list is a test fixture, never a constructor seed.
        src, adj = graph(3, [(0, 1)]), graph(3, [(0, 1), (1, 2)])
        domains = (((0,), (2,)), ((1,),), ((0,),))
        model = cd._Model(domains, src, adj, budget())
        prob = [[.5, .5], [1.], [1.]]
        ranks = [tuple(range(3))]*3
        self.assertTrue(oracle(((2,), (1,), (0,)), src, adj))
        self.assertFalse(oracle(model.select(prob, ranks), src, adj))
        self.assertEqual(model.costs(prob, 4, model.fields(prob))[0], [5., 1.])
        updated = model.update(prob, 4)
        expected = .25 + .5*math.exp(-4)/(1+math.exp(-4))
        self.assertAlmostEqual(updated[0][0], expected)
        self.assertEqual(prob, [[.5, .5], [1.], [1.]])
        for _ in range(7):
            updated = model.update(updated, 4)
        selected = model.select(updated, ranks)
        self.assertEqual(selected, ((2,), (1,), (0,)))
        self.assertTrue(oracle(selected, src, adj))
        self.assertTrue(cd._stats(selected, src, adj, budget())['valid'])
        for row in updated:
            self.assertAlmostEqual(math.fsum(row), 1.)
            self.assertTrue(all(math.isfinite(x) and x >= 0 for x in row))
        with self.assertRaises(ValueError):
            model.fields([[math.nan, .5], [1.], [1.]])
        with self.assertRaises(ValueError):
            model.fields([[1.], [1.], [1.]])
        # Pairwise support can be globally inconsistent: triangle domains on one edge.
        triangle = graph(3, [(0, 1), (1, 2), (0, 2)])
        pair = graph(2, [(0, 1)])
        bad = cd._Model([((0,), (1,))]*3, triangle, pair, budget())
        p = [[.5, .5]]*3
        self.assertEqual(bad.expected(p, bad.fields(p))['edges_without_any_pairwise_support'], 0)
        self.assertFalse(oracle(bad.select(p, [(0, 1)]*3), triangle, pair))

    def test_interruption_and_noncredit(self):
        src, adj = graph(2, [(0, 1)]), graph(3, [(0, 1), (1, 2)])
        b = budget()
        model = cd._Model((((0,),), ((2,),)), src, adj, b)
        original = model.domains
        p = [[1.], [1.]]
        b.limit = b.units + 15
        records = []
        with self.assertRaises(cd._Stop):
            cd._regenerate(model, p, [tuple(range(3))]*2, 4, None, records)
        self.assertEqual(model.domains, original)
        self.assertEqual(p, [[1.], [1.]])
        self.assertLessEqual(b.units, b.limit)
        self.assertIsNotNone(b.denied)
        now = [0.]
        b = cd._Budget(1., clock=lambda: now[0])
        with self.assertRaises(cd._Stop):
            with b.stage('forced_interruption'):
                now[0] = 2.
        self.assertEqual(b.stage_wall['forced_interruption'], 2.)
        response = dict(status='FAILURE', embedding={}, diag={})
        b = cd._Budget(1., clock=lambda: 0.)
        cd._finish(response, ((0,), (1,)), ['u', 'v'], ['a', 'b', 'c'], src, adj, b, 1.)
        self.assertEqual(response['status'], 'SUCCESS')
        self.assertEqual(response['embedding'], {'u': ['a'], 'v': ['b']})
        now[0] = 0.
        b = cd._Budget(1., clock=lambda: now[0])
        raw_materialize = cd._materialize
        def crosses_at_copy(*args):
            result = raw_materialize(*args)
            now[0] = 2.
            return result
        late = dict(status='FAILURE', embedding={}, diag={})
        with patch.object(cd, '_materialize', crosses_at_copy):
            cd._finish(late, ((0,), (1,)), ['u', 'v'], ['a', 'b', 'c'], src, adj, b, 1.)
        self.assertTrue(late['diag']['final']['valid'])
        self.assertEqual(late['status'], 'TIMEOUT')
        self.assertEqual(late['embedding'], {})
        self.assertEqual(late['diagnostic_embedding'], {'u': ['a'], 'v': ['b']})
        invalid = dict(status='FAILURE', embedding={}, diag={})
        cd._finish(invalid, ((0,), (2,)), ['u', 'v'], ['a', 'b', 'c'], src, adj, budget(), 100.)
        self.assertFalse(invalid['diag']['final']['valid'])
        self.assertEqual(invalid['embedding'], {})
        # An unexpected ValueError after a feasible epoch is fatal; a valid
        # incumbent must not conceal it. Expected input failure remains separate.
        fatal = dict(status='FAILURE', embedding={}, diag={})
        cd._record_exception(fatal, ValueError('invalid probabilities'), input_complete=True)
        cd._finish(fatal, ((0,), (1,)), ['u', 'v'], ['a', 'b', 'c'], src, adj, budget(), 100.)
        self.assertEqual(fatal['status'], 'ERROR')
        self.assertEqual(fatal['embedding'], {})
        self.assertTrue(fatal['diag']['fatal_error'])
        self.assertEqual(fatal['diag']['exception'], dict(type='ValueError',
            message='invalid probabilities', expected_input=False))
        self.assertEqual(fatal['error'], 'ValueError: invalid probabilities')
        self.assertTrue(fatal['diag']['final']['valid'])
        expected = dict(status='FAILURE', embedding={}, diag={})
        cd._record_exception(expected, ValueError('bad input'), input_complete=False)
        self.assertEqual(expected['status'], 'FAILURE')
        self.assertTrue(expected['diag']['exception']['expected_input'])
        stopped = dict(status='TIMEOUT', embedding={}, error='search deadline', diag={})
        cd._finish(stopped, ((0,), (1,)), ['u', 'v'], ['a', 'b', 'c'], src, adj, budget(), 100.)
        self.assertEqual(stopped['status'], 'SUCCESS')
        self.assertEqual(stopped['embedding'], {'u': ['a'], 'v': ['b']})


if __name__ == '__main__':
    unittest.main()
