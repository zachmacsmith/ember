"""B023 targeted stdlib checks; no public constructor or corpus invocation."""
from collections import Counter
from copy import deepcopy
import importlib.util
from pathlib import Path
from random import Random
from time import perf_counter
import unittest


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / 'packages/ember-qc/src/ember_qc/algorithms/factored/temporary_contact_construction.py'
spec = importlib.util.spec_from_file_location('b023_candidate', SOURCE)
b = importlib.util.module_from_spec(spec)
spec.loader.exec_module(b)


def graph(vertices, edges):
    answer = {u: set() for u in vertices}
    for u, v in edges:
        answer[u].add(v); answer[v].add(u)
    return answer


def oracle(G, H, chains, mu=None, lam=None):
    """Independent whole-chain Cartesian-pair contact and occupancy counting."""
    mu, lam = mu or {}, lam or {}
    counts = Counter(q for c in chains.values() for q in c)
    contacts = {(u, v): sum(p in H[q] for q in chains[u] for p in chains[v])
                for u in G for v in G[u] if u < v}
    Q = sum(map(len, chains.values()))
    O = sum(max(0, count-1) for count in counts.values())
    M = sum(count == 0 for count in contacts.values())
    F = Q + sum(lam.get(q, 1)*max(0, count-1) for q, count in counts.items())
    F += sum(mu.get(e, 1) for e, count in contacts.items() if not count)
    connected = set(chains) == set(G)
    for chain in chains.values():
        if not chain or not set(chain) <= H.keys():
            connected = False; continue
        reached = {next(iter(chain))}; stack = list(reached)
        while stack:
            for p in H[stack.pop()]:
                if p in chain and p not in reached:
                    reached.add(p); stack.append(p)
        connected &= reached == set(chain)
    return dict(qubits=Q, overlap=O, missing=M, energy=F), contacts, bool(connected and not O and not M)


def context(G, H, chains):
    ctx = b._Context(G, H, b._Meter(perf_counter()+5), 0)
    ctx.install(chains)
    return ctx


def loss_fixture():
    # Source a-u-v-b. Every initial contact is real, but u and v share q=0.
    G = graph(range(4), [(0, 1), (1, 2), (2, 3)])
    H = graph(range(5), [(0, 1), (0, 2), (0, 3), (1, 4), (3, 4)])
    chains = {0: {2}, 1: {0}, 2: {0, 1}, 3: {3}}
    return G, H, chains


class TemporaryContactChecks(unittest.TestCase):
    def assert_counts(self, ctx):
        score, contacts, valid = oracle(ctx.G, ctx.H, ctx.state.chains, ctx.mu, ctx.lam)
        self.assertEqual(ctx.state.score(), score)
        self.assertEqual(ctx.state.contacts, contacts)
        self.assertEqual(ctx.m.work, sum(ctx.m.units.values()))
        return valid

    def test_exact_multiple_owner_contacts_and_changed_outside_support(self):
        G = graph([7, -2, 19], [(7, -2), (-2, 19), (7, 19)])
        H = graph(range(4), [(0, 1), (1, 2), (2, 0), (2, 3)])
        ctx = context(G, H, {-2: {0, 1}, 7: {0, 1, 2}, 19: {1, 2}})
        ctx.mu[(-2, 7)] = 5; ctx.lam[1] = 4
        ctx.install(ctx.state.chains)
        self.assert_counts(ctx)
        before = deepcopy(ctx.state.chains)
        p = ctx.replacement(7, {2, 3})
        candidate = dict(before); candidate[7] = {2, 3}
        self.assertEqual(p['score'], oracle(G, H, candidate, ctx.mu, ctx.lam)[0])
        row = {}; ctx.publish(p, row)
        self.assert_counts(ctx)
        self.assertEqual(ctx.state.chains[-2], before[-2])
        self.assertEqual(ctx.state.chains[19], before[19])
        self.assertEqual(ctx.state.owners[1], frozenset({-2, 19}))

    def test_actual_connected_contact_loss_then_repair(self):
        G, H, chains = loss_fixture(); original = deepcopy((G, H, chains))
        ctx = context(G, H, chains)
        self.assertEqual((ctx.state.Q, ctx.state.M, ctx.state.O), (5, 0, 1))
        ctx.price_site(0)
        erased = ctx.erase(0)
        self.assertTrue(erased['committed'])
        self.assertEqual(erased['owner'], 2)
        self.assertEqual(erased['lost_contacts'], [(2, 3)])
        self.assertEqual(ctx.state.chains[2], frozenset({1}))
        self.assertEqual((ctx.state.Q, ctx.state.M, ctx.state.O), (4, 1, 0))
        self.assert_counts(ctx)
        ctx.price_edge((2, 3)); routed = ctx.route((2, 3))
        self.assertEqual(routed['restored_contacts'], [(2, 3)])
        self.assertEqual(ctx.state.chains[2], frozenset({1, 4}))
        self.assertTrue(self.assert_counts(ctx))
        self.assertIsNone(ctx.validate())
        self.assertEqual((G, H, chains), original)

    def test_singleton_free_and_occupied_fallback_nonempty(self):
        G = graph(range(2), [(0, 1)])
        H = graph(range(3), [(0, 1), (1, 2)])
        ctx = context(G, H, {0: {1}, 1: {1}})
        free = next(q for q in ctx.qorder if q != 1)
        row = ctx.erase(1)
        self.assertEqual(row['owner'], 0)
        self.assertEqual(ctx.state.chains[0], frozenset({free}))
        self.assertTrue(self.assert_counts(ctx))
        G = graph(range(3), [(0, 1), (1, 2), (0, 2)])
        ctx = context(G, H, {0: {1}, 1: {1}, 2: {0, 1, 2}})
        row = ctx.erase(1)
        self.assertEqual(row['scored'], 6)
        self.assertTrue(all(ctx.state.chains.values()))
        self.assert_counts(ctx)

    def test_increasing_energy_route_then_safe_anchor_free_pruning(self):
        G = graph(range(2), [(0, 1)])
        H = graph(range(5), [(0, 1), (1, 2), (2, 3), (3, 4)])
        ctx = context(G, H, {0: {0}, 1: {4}})
        ctx.price_edge((0, 1))
        row = ctx.route((0, 1))
        self.assertGreater(row['after']['energy'], row['before']['energy'])
        self.assertTrue(self.assert_counts(ctx))
        self.assertEqual(ctx.state.Q, 5)
        ctx.cleanup()
        self.assertEqual(ctx.state.Q, 2)
        self.assertEqual(ctx.stats['cleanup_deletions'], 3)
        self.assertTrue(self.assert_counts(ctx))

    def test_work_interruption_after_a_scored_direction_keeps_valid_prefix(self):
        G, H, chains = loss_fixture(); ctx = context(G, H, chains)
        ctx.price_site(0); ctx.erase(0); ctx.price_edge((2, 3))
        entry = ctx.state
        scores = ctx.replacement
        def first_then_limit(owner, sites):
            proposal = scores(owner, sites)
            ctx.m.limit = ctx.m.work
            return proposal
        ctx.replacement = first_then_limit
        with self.assertRaisesRegex(b._Stop, 'work_limit'):
            ctx.route((2, 3))
        self.assertIs(ctx.state, entry)
        self.assertFalse(ctx.moves[-1]['committed'])
        self.assertEqual(ctx.moves[-1]['discarded_scored'], 1)
        self.assertEqual(ctx.m.work, ctx.m.limit)
        self.assert_counts(ctx)

    def test_last_clock_rejects_publication_and_last_unit_can_publish(self):
        G, H, chains = loss_fixture(); ctx = context(G, H, chains)
        ctx.erase(0); entry = ctx.state
        clock = ctx.m.clock
        def reject_publication():
            if ctx.m.stage == 'publication':
                raise b._Stop('search_deadline')
            return clock()
        ctx.m.clock = reject_publication
        with self.assertRaisesRegex(b._Stop, 'deadline'):
            ctx.route((2, 3))
        self.assertIs(ctx.state, entry)
        self.assertFalse(ctx.moves[-1]['committed'])
        ctx.m.clock = clock
        proposal = ctx.replacement(2, {1, 4})
        start = ctx.m.work; row = {}; ctx.publish(proposal, row)
        used = ctx.m.work-start
        other = context(G, H, entry.chains)
        proposal = other.replacement(2, {1, 4})
        other.m.limit = other.m.work+used
        row = {}; other.publish(proposal, row)
        self.assertEqual(other.m.work, other.m.limit)
        self.assertTrue(row['committed'])
        self.assertTrue(self.assert_counts(other))

    def test_original_graph_final_gate_and_late_validation_noncredit(self):
        G = graph(range(3), [(0, 1), (1, 2), (0, 2)])
        H = graph(range(3), [(0, 1), (1, 2)])
        ctx = context(G, H, {0: {0, 1}, 1: {1}, 2: {1, 2}})
        ctx.state.M = ctx.state.O = 0  # Counter corruption must not create credit.
        info = {'error': None}
        embedding, status = b._finish(ctx, ctx.m, info, perf_counter()+2)
        self.assertEqual((embedding, status), ({}, 'FAILURE'))
        self.assertEqual(info['final_validation'], 'overlap')
        G = graph(range(2), [(0, 1)])
        ctx = context(G, H, {0: {0}, 1: {1}})
        validate = ctx.validate
        def late_valid():
            result = validate()
            ctx.m.deadline = perf_counter()-1
            return result
        ctx.validate = late_valid
        info = {'error': None}
        embedding, status = b._finish(ctx, ctx.m, info, perf_counter()+2)
        self.assertEqual((embedding, status), ({}, 'FAILURE'))
        self.assertEqual(info['finalization_stop'], 'final_deadline')

    def test_seeded_initialization_and_first_edge_erasure_interleave(self):
        G = graph(range(3), [(0, 1), (1, 2)])
        H = graph(range(3), [(0, 1), (1, 2)])
        ctx = b._Context(G, H, b._Meter(perf_counter()+5), 0)
        order = ctx.initialize()
        self.assertEqual(order['source_order'], [1, 0, 2])
        self.assertEqual(ctx.state.Q, 3)
        self.assertTrue(all(len(c) == 1 for c in ctx.state.chains.values()))
        expected = [(0, 1), (1, 2)]; Random(0).shuffle(expected)
        self.assertEqual(ctx.edge_order, expected)
        ctx.install({0: {1}, 1: {1}, 2: {1}})
        trace = []
        def route(e):
            trace.append(('route', e))
            ctx.state.contacts[e] = 1; ctx.state.M -= 1
        def erase(q):
            trace.append(('erase', q))
            raise b._Stop('schedule_probe_complete')
        ctx.route, ctx.erase = route, erase
        with self.assertRaisesRegex(b._Stop, 'schedule_probe_complete'):
            ctx.search()
        self.assertEqual([r[0] for r in trace], ['route', 'erase'])
        self.assertEqual(ctx.stats['edge_visits'], 1)
        self.assertEqual(ctx.stats['edge_price_updates'], 1)
        self.assertEqual(ctx.stats['site_price_updates'], 1)


if __name__ == '__main__':
    unittest.main()
