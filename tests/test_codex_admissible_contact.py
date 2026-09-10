"""C016's three publication-transition risks; no full constructor calls."""
import argparse
import copy
import hashlib
import importlib.abc
import importlib.util
import json
from pathlib import Path
import sys
import time
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
ATTEMPTS, CASES, RUN_CALLS = [], [], []


class Guard(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if 'minorminer' in fullname or 'busclique' in fullname:
            ATTEMPTS.append(fullname)
            raise ImportError('prohibited embedding dependency')


sys.meta_path.insert(0, Guard())
import networkx as nx


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT/path)
    value = importlib.util.module_from_spec(spec); spec.loader.exec_module(value)
    return value


c = load('isolated_c016', 'packages/ember-qc/src/ember_qc/algorithms/zephyr_admissible_contact.py')
ORACLE = ROOT/'results/codex/042-results-review/pre-execution/ember_embedding_oracle.py'
assert hashlib.sha256(ORACLE.read_bytes()).hexdigest() == 'e4718c2ec09f3ec80e035ef89648f81b45413f52c7580123ef129419b25612d9'
oracle = load('unchanged_c016_oracle', ORACLE)


def state(G, H, chains=None):
    engine = c._Engine([set(G[u]) for u in range(len(G))], [set(H[q]) for q in range(len(H))],
                       [(0, 0, 0, 0, 0)]*len(H), 0, 0, c._Budget(time.perf_counter()+30))
    engine.sorder = list(range(len(G))); engine.srank = {u: u for u in G}
    engine.torder = list(range(len(H))); engine.trank = {q: q for q in H}
    engine.adj = [sorted(H[q]) for q in H]
    result = c._State(engine, chains); c._certify(result); engine.published = result
    return result


def payload(s):
    return copy.deepcopy((s.I, s.chains, s.owner, s.contacts, s.domains, s.Q, c._capacities(s)))


def validate(test, label, G, H, entry):
    """Reuse the original oracle on the actual induced partial source."""
    c._certify(entry)
    source = G.subgraph(entry.I)
    sa = {u: set(source[u]) for u in source}; se = {tuple(sorted(e)) for e in source.edges}
    ta = {q: set(H[q]) for q in H}; te = {tuple(sorted(e)) for e in H.edges}
    mapping = {str(u): list(q) for u, q in entry.chains.items()}
    good, reason, quality = oracle.embedding_quality(mapping, sa, se, ta, te)
    test.assertTrue(good, reason)
    test.assertFalse(c._c14._violations(entry))
    CASES.append(dict(case=label, introduced=len(entry.I), source_vertices=len(G),
                      independent_validity=good, reason=reason, quality=quality,
                      capacity_violations=0))


def split_prefix():
    G = nx.path_graph(3)
    H = nx.Graph(); H.add_nodes_from(range(5)); H.add_edges_from([(0, 1), (2, 3), (3, 4)])
    return G, H, state(G, H, {0: {0}, 2: {2}})


def run_fixture(entry, diag):
    RUN_CALLS.append(dict(source_vertices=entry.e.n, target_vertices=entry.e.h,
                          introduced_before=len(entry.I)))
    return c._run(entry, diag)


class SpecificRisks(unittest.TestCase):
    def test_01_publish_ordinary_that_empties_a_singleton_domain(self):
        G, H = nx.complete_graph(3), nx.cycle_graph(4)
        entry = state(G, H, {0: {0}}); before = payload(entry)
        diag, proposals = dict(publications=[]), []
        place = c._place

        def observe(current, v, context='ordinary'):
            self.assertIs(current.e.published, current)
            if proposals:
                self.assertIs(current, proposals[-1])
                self.assertEqual(diag['publications'][-2]['Q_after'], current.Q)
            proposal = place(current, v, context)
            self.assertIsNotNone(proposal)
            self.assertEqual(proposal.I, current.I | {v})
            validate(self, 'ordinary_proposal_'+str(v), G, H, proposal)
            proposals.append(proposal)
            return proposal

        with patch.object(c, '_place', observe), patch.object(
                c, '_transaction', side_effect=AssertionError('available ordinary birth rebuilt')) as tx:
            result, stop = run_fixture(entry, diag)
        self.assertEqual(stop, 'complete_introduced_source')
        self.assertEqual(diag['publications'][0]['newly_empty'], [2])
        self.assertEqual(proposals[0].chains, {0: frozenset({0}), 1: frozenset({1})})
        self.assertTrue(all(row['status'] == 'ordinary' and row['published'] for row in diag['publications']))
        self.assertEqual([row['introduced_after']-row['introduced_before'] for row in diag['publications']], [1, 1])
        self.assertIs(result, proposals[-1]); self.assertIs(entry.e.published, result)
        tx.assert_not_called(); self.assertFalse(entry.e.rebuilds)
        self.assertEqual(payload(entry), before)
        validate(self, 'ordinary_complete', G, H, result)

    def test_02_completed_failure_rebuilds_or_records_obstruction(self):
        G, H, entry = split_prefix(); before = payload(entry)
        diag = dict(publications=[])
        with patch.object(c, '_transaction', wraps=c._transaction) as tx:
            result, stop = run_fixture(entry, diag)
        self.assertEqual(stop, 'complete_introduced_source')
        tx.assert_called_once()
        args = tx.call_args.args
        self.assertIsNone(args[2]); self.assertIs(args[4], entry.e.placements[0])
        self.assertEqual(args[4]['status'], 'failure'); self.assertTrue(args[4]['exhaustive'])
        self.assertEqual(args[4]['failure_reason'], 'contact_unreachable')
        self.assertEqual(entry.e.rebuilds[0]['status'], 'rebuilt')
        self.assertEqual(result.I, entry.I | {1})
        self.assertTrue(diag['publications'][0]['published'])
        self.assertEqual(payload(entry), before)
        validate(self, 'successful_failed_birth_rebuild', G, H, result)

        G, H = nx.star_graph(4), nx.cycle_graph(5)
        entry = state(G, H); before = payload(entry); diag = dict(publications=[])
        with patch.object(c, '_transaction', wraps=c._transaction) as tx:
            result, stop = run_fixture(entry, diag)
        self.assertEqual(stop, 'construction_obstructed'); tx.assert_called_once()
        self.assertEqual(entry.e.placements[0]['status'], 'failure')
        self.assertTrue(entry.e.placements[0]['exhaustive'])
        self.assertEqual(entry.e.rebuilds[0]['status'], 'rebuild_failed_capacity_no_outside')
        self.assertFalse(any(row.get('published', False) for row in diag['publications']))
        self.assertIs(result, entry); self.assertIs(entry.e.published, entry)
        self.assertEqual(payload(entry), before)
        validate(self, 'failed_birth_obstruction_prefix', G, H, entry)

    def test_03_interruptions_preserve_the_published_prefix(self):
        for phase in ('ordinary', 'retraction', 'publication_certificate'):
            with self.subTest(phase=phase):
                if phase == 'retraction':
                    G, H, entry = split_prefix()
                else:
                    G, H = nx.complete_graph(3), nx.cycle_graph(4)
                    entry = state(G, H, {0: {0}})
                before = payload(entry); diag = dict(publications=[])
                budget, clock = entry.e.b, [0.]
                budget.clock = lambda: clock[0]; budget.deadline = 1.
                tick, certify = budget.tick, c._certify

                def interrupt_tick(name, count=1):
                    if phase != 'publication_certificate' and budget.active == phase and name == 'constrained_root_attempts':
                        clock[0] = 2.
                    return tick(name, count)

                def interrupt_certificate(proposal):
                    certify(proposal)
                    self.assertIs(entry.e.published, entry)
                    clock[0] = 2.

                certificate = interrupt_certificate if phase == 'publication_certificate' else certify
                with patch.object(budget, 'tick', interrupt_tick), patch.object(c, '_certify', certificate):
                    with self.assertRaises(c._Deadline): run_fixture(entry, diag)
                clock[0] = 0.
                self.assertIs(entry.e.published, entry)
                self.assertEqual(payload(entry), before)
                self.assertIsNone(entry.e.complete)
                self.assertFalse(any(row.get('published', False) for row in diag['publications']))
                if phase == 'publication_certificate':
                    self.assertEqual(entry.e.placements[-1]['status'], 'success')
                    self.assertFalse(entry.e.rebuilds)
                else:
                    self.assertEqual(entry.e.placements[-1]['status'], 'interrupted')
                    self.assertFalse(entry.e.placements[-1]['exhaustive'])
                    if phase == 'ordinary':
                        self.assertFalse(entry.e.rebuilds)
                    else:
                        self.assertEqual(entry.e.placements[0]['status'], 'failure')
                        self.assertEqual(entry.e.rebuilds[0]['status'], 'interrupted')
                validate(self, 'interrupted_'+phase+'_prefix', G, H, entry)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    args = parser.parse_args(); args.output.mkdir(parents=True, exist_ok=False)
    started, cpu = time.perf_counter(), time.process_time()
    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(SpecificRisks))
    prohibited_imported = [n for n in sys.modules if 'minorminer' in n or 'busclique' in n]
    summary = dict(status='PASS' if result.wasSuccessful() and not ATTEMPTS and not prohibited_imported else 'FAIL',
                   groups=result.testsRun, errors=len(result.errors), failures=len(result.failures),
                   full_constructor_calls=0, fixture_run_calls=len(RUN_CALLS), fixture_calls=RUN_CALLS,
                   wall=time.perf_counter()-started, cpu=time.process_time()-cpu,
                   prohibited_attempts=ATTEMPTS, prohibited_imported=prohibited_imported,
                   imported_modules=sorted(sys.modules), cases=CASES)
    (args.output/'summary.json').write_text(json.dumps(summary, indent=2, sort_keys=True)+'\n')
    print(json.dumps({k: v for k, v in summary.items() if k not in ('imported_modules', 'cases')}))
    if summary['status'] != 'PASS': raise SystemExit(1)
