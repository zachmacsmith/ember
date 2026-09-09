"""B026 targeted checks only; public full-constructor gates live in the saved runner."""
import importlib.util
from pathlib import Path
import time
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / 'packages/ember-qc/src/ember_qc/algorithms/factored/mobile_tree_construction.py'
spec = importlib.util.spec_from_file_location('isolated_b026', SOURCE)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def graph(n, edges):
    result = {u: set() for u in range(n)}
    for u, v in edges:
        result[u].add(v); result[v].add(u)
    return result


def path(n):
    return graph(n, [(u, u + 1) for u in range(n - 1)])


def state(engine, mapping):
    chains = {u: frozenset(s) for u, s in mapping.items()}
    owners, trees, witnesses = {}, {}, {}
    for u, sites in chains.items():
        root = min(sites, key=engine.rank.__getitem__)
        parent, queue = {root: None}, [root]
        for q in queue:
            for p in engine.adj[q]:
                if p in sites and p not in parent:
                    parent[p] = q; queue.append(p)
        trees[u] = parent
        for q in sites:
            owners.setdefault(q, set()).add(u)
    for u in chains:
        for v in engine.G[u]:
            if u < v and v in chains:
                pairs = [(q, p) for q in chains[u] for p in chains[v] if p in engine.H[q]]
                if not pairs:
                    raise ValueError('fixture lacks actual coupler')
                witnesses[u, v] = min(pairs, key=lambda x: (engine.rank[x[0]], engine.rank[x[1]]))
    return mod._State(chains, trees, {q: frozenset(v) for q, v in owners.items()}, witnesses,
                      sum(map(len, chains.values())), sum(max(0, len(v) - 1) for v in owners.values()))


def original_valid(G, H, chains):
    if set(chains) != set(G):
        return False
    used = set()
    for sites in chains.values():
        sites = set(sites)
        if not sites or not sites <= H.keys() or sites & used:
            return False
        reached = {next(iter(sites))}
        while True:
            new = reached | {p for q in reached for p in H[q] if p in sites}
            if new == reached:
                break
            reached = new
        if reached != sites:
            return False
        used |= sites
    return all(any(p in H[q] for q in chains[u] for p in chains[v])
               for u in G for v in G[u])


def engine(G, H, mapping=None):
    e = mod._Engine(G, H, mod._Meter(time.perf_counter() + 20), 0)
    if mapping is not None:
        e.state = state(e, mapping)
    return e


def full_distances(H, boundary, costs):
    """Independent repeated relaxation, with no candidate heap/stopping code."""
    D = {q: (costs[q] if q in boundary else float('inf')) for q in H}
    for _ in H:
        previous = dict(D)
        for q in H:
            if costs[q] is not None:
                D[q] = min([previous[q]] + [costs[q] + previous[p] for p in H[q]
                                           if costs[p] is not None])
        if D == previous:
            break
    return D


class MobileTreeChecks(unittest.TestCase):
    def test_contact_stem_moves_and_strict_Q(self):
        G, H = path(3), path(5)
        e = engine(G, H, {0: [0], 1: [1, 2, 3], 2: [4]})
        before = e.state; e.quality = True
        self.assertTrue(original_valid(G, H, before.chains))
        self.assertEqual(e.visit(0), 'changed')
        self.assertEqual(e.state.Q, 3)
        self.assertTrue(original_valid(G, H, e.state.chains))
        self.assertEqual(before.chains[1], frozenset((1, 2, 3)))
        self.assertEqual(e.last_visit['neighbor_sites_released'], 2)
        self.assertEqual(e.last_visit['cross_owner_transfers'], 1)

    def test_both_ends_of_shared_neighbor_witness_survive(self):
        G = graph(3, [(0, 1), (1, 2), (0, 2)])
        H = graph(5, [(0, 1), (1, 2), (2, 3), (3, 4), (4, 0)])
        e = engine(G, H, {0: [0], 1: [1, 2], 2: [3, 4]}); e.quality = True
        pair = e.state.witnesses[1, 2]
        e.visit(0)
        self.assertEqual(e.state.witnesses[1, 2], pair)
        self.assertTrue(original_valid(G, H, e.state.chains))
        self.assertEqual(e.last_visit['neighbor_sites_released'], 2)

    def test_repeated_terminals_are_contacts_but_overlap_is_not(self):
        G = graph(4, [(0, 1), (0, 2), (0, 3)])
        e = engine(G, G, {u: [u] for u in G}); e.quality = True
        e.visit(0)
        self.assertEqual(e.state.Q, 4)
        self.assertEqual(e.last_visit['root_score'], 1)
        self.assertEqual(e.last_visit['shared_attachments'], 3)
        self.assertTrue(original_valid(G, G, e.state.chains))
        bad = engine(path(2), graph(2, []))
        with self.assertRaisesRegex(ValueError, 'contact'):
            bad.contacts(0, frozenset((0,)), {1: frozenset((0,))}, {})

    def test_joint_root_matches_complete_tiny_distance_oracle(self):
        fixtures = [path(7), graph(6, [(u, (u + 1) % 6) for u in range(6)]),
                    graph(6, [(0, 1), (1, 2), (2, 3), (3, 4), (4, 5), (1, 4)])]
        for H in fixtures:
            for quality in (False, True):
                G = graph(3, [(0, 1), (0, 2)])
                e = engine(G, H, {1: [0], 2: [len(H) - 1]})
                e.prices = {0: 3, 1: 2}
                neighbors = sorted((1, 2), key=e.srank.__getitem__)
                result = e.joint_root(neighbors, e.state.chains, {}, quality)
                costs = {q: (None if quality and q in e.state.owners else
                             1 + (0 if quality else e.prices.get(q, 1) * len(e.state.owners.get(q, ())))) for q in H}
                maps = {}
                for v in neighbors:
                    boundary = {q for p in e.state.chains[v] for q in H[p] if costs[q] is not None}
                    maps[v] = full_distances(H, boundary, costs)
                scores = {q: sum(maps[v][q] for v in neighbors) - costs[q]
                          for q in H if costs[q] is not None}
                expected = min(scores, key=lambda q: (scores[q], e.rank[q]))
                self.assertEqual(result[0], expected)
                self.assertEqual(result[3]['root_score'], scores[expected])
                for v in neighbors:
                    self.assertEqual(result[1][v][expected], maps[v][expected])
        e = engine(path(2), path(5), {1: [2]})
        result = e.joint_root([1], e.state.chains, {}, True)
        self.assertEqual(result[0], min((1, 3), key=e.rank.__getitem__))

    def test_shared_attachment_and_outside_owner_overlap_delta(self):
        H = graph(7, [(0, 1), (1, 2), (2, 3), (3, 5), (2, 4), (4, 6)])
        e = engine(graph(3, [(0, 1), (0, 2)]), H, {1: [5], 2: [6]})
        maps, parents = {}, {}
        for v, boundary in [(1, 3), (2, 4)]:
            D = full_distances(H, {boundary}, {q: 1 for q in H})
            maps[v] = D
            parents[v] = {q: (None if q == boundary else min(
                (p for p in H[q] if D[p] == D[q] - 1), key=e.rank.__getitem__)) for q in H}
        sites, shared, added = e.attach(0, [1, 2], e.state.chains, maps, parents)
        self.assertEqual(sites, frozenset((0, 1, 2, 3, 4)))
        self.assertGreater(shared, 0)
        G, H = graph(3, [(0, 1)]), path(5)
        e = engine(G, H, {0: [0], 1: [1, 2, 3], 2: [1]})
        self.assertEqual(e.state.O, 1)
        e.visit(0)
        self.assertEqual(e.state.chains[2], frozenset((1,)))
        self.assertEqual(e.state.O, 0)
        self.assertTrue(original_valid(G, H, e.state.chains))

    def test_feasibility_uphill_quality_rejection_and_neutral_motion(self):
        for quality, mapping, expected in [(False, {0: [0, 1]}, 'changed'),
                                            (True, {0: [0, 1]}, 'rejected'),
                                            (True, {0: [1]}, 'changed')]:
            e = engine(graph(1, []), path(3), {0: [0]}); e.quality = quality
            proposed = state(e, mapping); old = e.state
            def proposal(u, row):
                row.update(proposal_complete=True, neighbor_sites_released=0,
                           cross_owner_transfers=0, shared_attachments=0)
                return proposed
            e.proposal = proposal
            self.assertEqual(e.visit(0), expected)
            self.assertIs(e.state, old if expected == 'rejected' else proposed)
        # Witness-only changes affect the next pruning query and cannot be
        # mistaken for a quality fixed point merely because site sets agree.
        G, H = path(2), graph(4, [(0, 1), (1, 2), (2, 3), (3, 0)])
        e = engine(G, H, {0: [0, 1], 1: [2, 3]}); e.quality = True
        proposed = state(e, e.state.chains)
        proposed.witnesses[0, 1] = (1, 2) if e.state.witnesses[0, 1] != (1, 2) else (0, 3)
        def proposal(u, row):
            row.update(proposal_complete=True, neighbor_sites_released=0,
                       cross_owner_transfers=0, shared_attachments=0)
            return proposed
        e.proposal = proposal
        self.assertEqual(e.visit(0), 'changed')
        self.assertFalse(e.last_visit['chain_changed'])
        self.assertTrue(e.last_visit['witness_changed'])

    def test_interruptions_leave_exact_old_state_and_prices(self):
        for stage, cut in [('trim', 3), ('routing', 3), ('certificate', 3), ('publication', 2)]:
            e = engine(path(3), path(5), {0: [0], 1: [1, 2, 3], 2: [4]})
            e.quality = True; e.prices = {1: 8}
            old, prices, clock = e.state, dict(e.prices), e.m.clock
            counts = [0]
            def interrupt():
                if e.m.stage == stage:
                    counts[0] += 1
                    if counts[0] == cut:
                        raise mod._Stop(stage)
                return clock()
            e.m.clock = interrupt
            with self.assertRaises(mod._Stop):
                e.visit(0)
            self.assertIs(e.state, old)
            self.assertEqual(e.prices, prices)
            self.assertFalse(e.last_visit['accepted'])
            self.assertTrue(original_valid(e.G, e.H, e.state.chains))

    def test_fatal_error_never_credits_but_deadline_can_recertify(self):
        """Public wrapper exercised with search stubbed, not additional full construction."""
        for error, credit in [(RuntimeError('forced fatal'), False), (mod._Stop('forced deadline'), True)]:
            e = engine(path(2), path(3), {0: [0], 1: [1]})
            def build(source, target, meter, seed):
                e.m = meter
                return e
            def run(began):
                e.began = began
                raise error
            e.run = run
            with patch.object(mod, '_Engine', build):
                result = mod.contact_embed(path(2), path(3), timeout=2)
            self.assertEqual(result['status'] == 'SUCCESS', credit)
            if credit:
                self.assertTrue(original_valid(e.G, e.H, result['embedding']))
            else:
                self.assertEqual(result['embedding'], {})


if __name__ == '__main__':
    unittest.main()
