"""C015 focused risks and, in a separate mode, exactly two Z2 constructors."""
import argparse
from collections import Counter
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
ATTEMPTS = []
class Guard(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if 'minorminer' in fullname or 'busclique' in fullname:
            ATTEMPTS.append(fullname)
            raise ImportError('prohibited embedding dependency')
sys.meta_path.insert(0, Guard())
import networkx as nx
import dwave_networkx as dnx

def load(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT/path)
    value = importlib.util.module_from_spec(spec); spec.loader.exec_module(value)
    return value
c = load('isolated_c015', 'packages/ember-qc/src/ember_qc/algorithms/zephyr_constrained_contact.py')
ORACLE = ROOT/'results/codex/042-results-review/pre-execution/ember_embedding_oracle.py'
assert hashlib.sha256(ORACLE.read_bytes()).hexdigest() == 'e4718c2ec09f3ec80e035ef89648f81b45413f52c7580123ef129419b25612d9'
oracle = load('unchanged_c015_oracle', ORACLE)


def state(G, H, chains=None):
    engine = c._Engine([set(G[u]) for u in range(len(G))], [set(H[q]) for q in range(len(H))],
                       [(0, 0, 0, 0, 0)]*len(H), 0, 0, c._Budget(time.perf_counter()+30))
    engine.sorder = list(range(len(G))); engine.srank = {u: u for u in G}
    engine.torder = list(range(len(H))); engine.trank = {q: q for q in H}
    engine.adj = [sorted(H[q]) for q in H]
    result = c._State(engine, chains); result.certify(); engine.published = result
    return result


def payload(s):
    return copy.deepcopy((s.I, s.chains, s.owner, s.contacts, s.domains, s.Q, c._capacities(s)))


def valid(G, H, mapping):
    sa = {u: set(G[u]) for u in G}; se = {tuple(sorted(e)) for e in G.edges}
    ta = {q: set(H[q]) for q in H}; te = {tuple(sorted(e)) for e in H.edges}
    return oracle.embedding_quality({str(u): list(q) for u, q in mapping.items()}, sa, se, ta, te)


def corridor():
    H = nx.Graph(); H.add_nodes_from(range(9))
    H.add_edges_from([(0, 1), (1, 2), (2, 3), (2, 4), (2, 5), (3, 6), (3, 7), (3, 8)])
    return nx.star_graph(5), H


class SpecificRisks(unittest.TestCase):
    def test_01_scratch_counts_score_growth_and_pruning(self):
        G, H = nx.path_graph(4), nx.complete_graph(9)
        entry = state(G, H, {0: {0, 1}, 1: {2}}); before = payload(entry)
        scratch = c._Scratch(entry, 2, 3, c._placement_data(entry, 2))
        scratch.add(4)
        materialized, score = c._materialize(scratch)
        self.assertEqual(score, materialized.score())
        self.assertEqual(payload(entry), before)
        self.assertFalse(c._c14._violations(materialized))
        G, H = corridor(); entry = state(G, H); before = payload(entry)
        scratch = c._Scratch(entry, 0, 0, c._placement_data(entry, 0))
        counts = Counter(); self.assertTrue(c._grow_prune(scratch, set(), counts))
        self.assertGreater(counts['nonpositive_growth_claims'], 0)
        self.assertEqual(scratch.sites, {2, 3})
        result, _ = c._materialize(scratch)
        self.assertEqual(c._capacities(result)[0], (6, 5))
        self.assertEqual(payload(entry), before)
        boundary = sorted(c._bits(result.boundaries[0] & result.free))
        mapping = {0: result.chains[0], **{u: {q} for u, q in enumerate(boundary[:5], 1)}}
        self.assertTrue(valid(G, H, mapping)[0])

    def test_02_first_admissible_and_quota_aware_path(self):
        entry = state(nx.path_graph(2), nx.cycle_graph(6)); before = payload(entry)
        result = c._place(entry, 0); row = entry.e.placements[-1]
        self.assertIsNotNone(result); self.assertGreater(row['roots_generated'], 1)
        self.assertEqual((row['roots_started'], row['roots_completed']), (1, 1))
        self.assertFalse(row['exhaustive']); self.assertTrue(row['first_admissible'])
        self.assertEqual(payload(entry), before)
        G = nx.Graph(); G.add_nodes_from(range(5)); G.add_edges_from([(0, 2), (1, 2), (3, 4)])
        H = nx.Graph(); H.add_nodes_from(range(7))
        H.add_edges_from([(0, 2), (1, 2), (3, 2), (0, 4), (1, 5), (4, 6), (6, 5), (6, 2)])
        entry = state(G, H, {0: {0}, 1: {1}, 3: {3}}); before = payload(entry)
        result = c._place(entry, 2)
        self.assertEqual(result.chains[2], frozenset({4, 5, 6}))
        self.assertGreater(entry.e.placements[-1]['counts']['quota_denials'], 0)
        self.assertFalse(c._c14._violations(result)); self.assertEqual(payload(entry), before)
        self.assertTrue(valid(G.subgraph(result.I), H, result.chains)[0])

    def test_03_obstruction_scope_and_capacity_refusal(self):
        G = nx.Graph(); G.add_nodes_from(range(4)); G.add_edges_from([(0, 2), (1, 3)])
        H = nx.Graph(); H.add_nodes_from(range(3)); H.add_edges_from([(0, 2), (1, 2)])
        entry = state(G, H, {0: {0}, 1: {1}}); before = payload(entry)
        self.assertIsNone(c._place(entry, 2)); row = entry.e.placements[-1]
        self.assertEqual(row['failure_reason'], 'capacity_exhausted')
        self.assertEqual(row['capacity_obstructions'], [1]); self.assertEqual(payload(entry), before)
        H = nx.Graph(); H.add_nodes_from(range(4)); H.add_edges_from([(0, 1), (2, 3)])
        entry = state(nx.path_graph(3), H, {0: {0}, 2: {2}})
        self.assertIsNone(c._place(entry, 1))
        self.assertEqual(entry.e.placements[-1]['failure_reason'], 'contact_unreachable')
        entry = state(nx.star_graph(4), nx.cycle_graph(5)); before = payload(entry)
        self.assertIsNone(c._place(entry, 0)); failure = entry.e.placements[-1]
        self.assertEqual(failure['failure_reason'], 'capacity_exhausted')
        with patch.object(c._c, '_place', side_effect=AssertionError('capacity failure used contact guide')):
            transaction = {}; self.assertIsNone(c._transaction(entry, 0, None, transaction, failure))
        self.assertEqual(transaction['status'], 'rebuild_failed_capacity_no_outside')
        self.assertEqual(payload(entry), before)

    def test_04_interruption_rollback_and_late_materialization(self):
        G, H = corridor(); entry = state(G, H); before = payload(entry)
        scratch = c._Scratch(entry, 0, 0, c._placement_data(entry, 0))
        tick = entry.e.b.tick
        def interrupt(name, count=1):
            if name == 'scratch_site_additions': raise c._Deadline('injected_growth')
            return tick(name, count)
        with patch.object(entry.e.b, 'tick', interrupt):
            with self.assertRaises(c._Deadline): c._grow_prune(scratch, set(), Counter())
        self.assertEqual(payload(entry), before)
        entry = state(nx.empty_graph(1), nx.cycle_graph(4)); before = payload(entry)
        clock = [0.]; entry.e.b.clock = lambda: clock[0]; entry.e.b.deadline = 1.
        certify = c._certify
        def expire_after_certificate(proposal):
            certify(proposal); clock[0] = 2.
        with patch.object(c, '_certify', expire_after_certificate):
            with self.assertRaises(c._Deadline): c._place(entry, 0)
        self.assertIsNone(entry.e.complete)
        self.assertEqual(entry.e.placements[-1]['status'], 'interrupted')
        self.assertFalse(entry.e.placements[-1]['exhaustive'])
        clock[0] = 0.; self.assertEqual(payload(entry), before)


def tiny(output):
    target = dnx.zephyr_graph(2)
    results, errors = [], []
    for name, source, reference_q in [('star22', nx.star_graph(21), 23),
                                     ('k2_10', nx.complete_bipartite_graph(2, 10), 12)]:
        for u in source: source.nodes[u].clear()
        start, cpu = time.perf_counter(), time.process_time()
        raw = c.constrained_contact_embed(source, target, seed=0, timeout=5.)
        wall, used_cpu = time.perf_counter()-start, time.process_time()-cpu
        good, reason, quality = valid(source, target, raw.get('embedding', {}))
        with (output/(name+'.json')).open('x') as f:
            json.dump(dict(raw=raw, independently_valid=good, validation_reason=reason, quality=quality,
                           measured_wall=wall, measured_cpu=used_cpu), f, indent=2, sort_keys=True); f.write('\n')
        results.append(dict(case=name, status=raw['status'], independently_valid=good, quality=quality,
                            c014_reference_Q=reference_q,
                            q_change_from_c014=quality['qubits']-reference_q if quality else None,
                            measured_wall=wall, measured_cpu=used_cpu,
                            roots_started=sum(p.get('roots_started', 0) for p in raw['diag'].get('placements', [])),
                            roots_generated=sum(p.get('roots_generated', 0) for p in raw['diag'].get('placements', []))))
        if raw['status'] != 'SUCCESS' or not good: errors.append(dict(case=name, status=raw['status'], reason=reason))
    return dict(status='PASS' if not errors else 'FAIL', errors=errors, constructor_calls=2, cases=results)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=['risk', 'tiny']); parser.add_argument('output', type=Path)
    args = parser.parse_args(); args.output.mkdir(parents=True, exist_ok=False)
    started, cpu = time.perf_counter(), time.process_time()
    if args.mode == 'risk':
        result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(SpecificRisks))
        summary = dict(status='PASS' if result.wasSuccessful() else 'FAIL', groups=result.testsRun,
                       errors=len(result.errors), failures=len(result.failures), constructor_calls=0)
    else:
        summary = tiny(args.output)
    summary.update(mode=args.mode, wall=time.perf_counter()-started, cpu=time.process_time()-cpu,
                   prohibited_attempts=ATTEMPTS, imported_modules=sorted(sys.modules))
    if ATTEMPTS: summary['status'] = 'FAIL'
    (args.output/'summary.json').write_text(json.dumps(summary, indent=2, sort_keys=True)+'\n')
    print(json.dumps({k: v for k, v in summary.items() if k != 'imported_modules'}))
    if summary['status'] != 'PASS': raise SystemExit(1)
