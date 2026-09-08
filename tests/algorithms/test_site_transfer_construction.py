"""Eight bounded transfer/adapter checks, independent physical graph predicates."""
from collections import defaultdict
import copy
import time
import unittest
from unittest.mock import patch

import networkx as nx
from ember_qc.algorithms.factored import site_transfer as st
from ember_qc.algorithms.factored import site_transfer_construction as rc
from ember_qc.algorithms.factored import reduced_reinsertion_construction as ancestor


def valid(chains, source, target):
    if set(chains) != set(source): return False
    used = set()
    for chain in chains.values():
        if not chain or len(chain) != len(set(chain)) or used.intersection(chain): return False
        if not set(chain) <= set(target) or not nx.is_connected(target.subgraph(chain)): return False
        used.update(chain)
    return all(any(q in target[p] for p in chains[a] for q in chains[b]) for a, b in source.edges())


def engine(source, target):
    info = defaultdict(int, stage='test', scans_by_stage={}, stopped_by=None)
    e = rc._Expansion(source, target, time.perf_counter()+10, 0, info)
    e.vrank = {v: v for v in source}
    e.qrank = {q: q for q in target}
    return e


def minor_fixture(degree=2):
    # v=0; donor=1. Entry realizes the filled neighbor clique.
    source = nx.star_graph(degree)
    target = nx.Graph([(0, 1), (1, 2)])
    entry = {1: {0, 1}, 2: {2}}
    if degree == 3:
        target.add_edges_from([(1, 3), (2, 3)])
        entry[3] = {3}
    return source, target, entry


def pipeline_fixture():
    source = nx.complete_graph(5)
    source.remove_edge(0, 1)
    source.add_edges_from([(0, 5), (5, 1)])
    target = source.copy()
    entry = {0: [0, 5], 1: [1], 2: [2], 3: [3], 4: [4]}
    return source, target, entry


class TransferChecks(unittest.TestCase):
    def test_two_valid_filled_step_witnesses(self):
        for degree in (2, 3):
            source, target, entry = minor_fixture(degree)
            self.assertTrue(valid(entry, nx.complete_graph(list(entry)), target))
            saved = copy.deepcopy(entry)
            e = engine(source, target)
            trial, rec = st.transfer_site(e, 0, entry)
            self.assertIsNotNone(trial, rec)
            self.assertTrue(valid(trial, source, target))
            self.assertEqual(trial[0], {1}); self.assertEqual(trial[1], {0})
            self.assertEqual(set.union(*entry.values()), set.union(*trial.values()))
            self.assertEqual(rec['before_q'], rec['raw_q'])
            self.assertTrue(rec['certified']); self.assertFalse(rec['committed'])
            self.assertEqual(entry, saved)
            trial[2].add(99); self.assertEqual(entry, saved)

    def test_original_and_older_fill_contacts_are_not_released(self):
        source, target, entry = minor_fixture()
        source.add_edge(1, 2)
        e = engine(source, target)
        r = {v: set(source[v]) for v in source}
        trial_r = rc._trial_requirements(r, {'created_fill': []}, e)
        self.assertEqual(trial_r, r)
        out, rec = st.transfer_site(e, 0, entry)
        self.assertIsNone(out); self.assertGreater(rec['rejections']['donor_contacts'], 0)
        # z=3 was eliminated earlier and created 1--2; v=0 did not create it.
        original = nx.Graph([(3, 1), (3, 2), (0, 1), (0, 2)])
        r = {v: set(original[v]) for v in original}
        r[1].add(2); r[2].add(1)
        target.add_edges_from([(0, 3), (2, 4)])
        e = engine(nx.Graph([(a, b) for a in r for b in r[a]]), target)
        trial_r = rc._trial_requirements(r, {'created_fill': []}, e)
        rc._set_required(e, trial_r)
        out, rec = st.transfer_site(e, 0, entry)
        self.assertIsNone(out); self.assertIn(2, e.source[1])
        self.assertGreater(rec['rejections']['donor_contacts'], 0)
        # Only the earlier row removes this synthetic edge on its own reversal.
        later = rc._trial_requirements(trial_r, {'created_fill': [(1, 2)]}, e)
        self.assertNotIn(2, later[1]); self.assertEqual(r[1], {0, 2, 3})

    def test_articulation_and_both_frontier_rejections(self):
        source = nx.star_graph(2)
        target = nx.Graph([(0, 1), (1, 2), (1, 3)])
        out, rec = st.transfer_site(engine(source, target), 0, {1: {0, 1, 2}, 2: {3}})
        self.assertIsNone(out); self.assertEqual(rec['rejections']['donor_disconnected'], 1)
        source, target, entry = minor_fixture()
        source.add_edge(1, 3); target.add_edge(1, 3)
        out, rec = st.transfer_site(engine(source, target), 0, entry)
        self.assertIsNone(out); self.assertEqual(rec['rejections']['donor_future_port'], 1)
        source, target, entry = minor_fixture()
        source.add_edge(0, 3); target.add_edges_from([(0, 3), (2, 4)])
        out, rec = st.transfer_site(engine(source, target), 0, entry)
        self.assertIsNone(out); self.assertEqual(rec['rejections']['new_future_port'], 1)

    def test_first_certified_and_exact_64_site_prefix(self):
        source = nx.star_graph(2); target = nx.complete_graph(3)
        entry = {1: {0, 1}, 2: {2}}
        out, rec = st.transfer_site(engine(source, target), 0, entry)
        self.assertEqual(rec['site'], 0); self.assertEqual(rec['inspected'], [[1, 0]])
        self.assertTrue(valid(out, source, target))
        target = nx.complete_graph(70); target.add_edge(69, 70)
        entry = {1: set(range(70)), 2: {70}}
        e = engine(source, target)
        out, rec = st.transfer_site(e, 0, entry)
        self.assertIsNone(out); self.assertEqual(rec['status'], 'site_limit')
        self.assertEqual(rec['inspected'], [[1, q] for q in range(64)])
        self.assertEqual(rec['pool_size'], 70)
        # The excluded site is independently admissible, proving genuine truncation.
        expected = {1: set(range(69)), 2: {70}, 0: {69}}
        self.assertTrue(valid(expected, source, target))
        e = engine(source, target); e.qrank[69] = -1
        out, rec = st.transfer_site(e, 0, entry)
        self.assertEqual(rec['site'], 69); self.assertTrue(valid(out, source, target))

    def test_live_limits_and_final_deadline_discard_private_proposal(self):
        source, target, entry = minor_fixture(); saved = copy.deepcopy(entry)
        e = engine(source, target); e.info['transfer_scans'] = st.TOTAL_SCANS-7
        before = e.scans
        out, rec = st.transfer_site(e, 0, entry)
        self.assertIsNone(out); self.assertEqual(rec['status'], 'local_work_limit')
        self.assertEqual(e.scans-before, 7); self.assertEqual(e.info['transfer_scans'], st.TOTAL_SCANS)
        out, rec = st.transfer_site(e, 0, entry)
        self.assertIsNone(out); self.assertEqual(rec['status'], 'transfer_total_limit')
        self.assertEqual(rec['scans'], 0); self.assertIsNone(e.transfer_end)
        e = engine(source, target); e.scans = rc._helpers.SCANS-2
        with self.assertRaises(rc._Stop): st.transfer_site(e, 0, entry)
        self.assertEqual(e.scans, rc._helpers.SCANS); self.assertEqual(e.info['stopped_by'], 'work_limit')
        e = engine(source, target); e.deadline = 10.; clock = [0.]; gate = st._gate
        def late(*args):
            gate(*args); clock[0] = 11.
        with patch.object(st.time, 'perf_counter', side_effect=lambda: clock[0]), patch.object(st, '_gate', side_effect=late):
            with self.assertRaises(rc._Stop): st.transfer_site(e, 0, entry)
        rec = e.info['transfer_records'][-1]
        self.assertTrue(rec['certified']); self.assertFalse(rec['returned'])
        self.assertEqual(rec['status'], 'deadline'); self.assertEqual(rec['wall'], 11.)
        self.assertEqual(entry, saved); self.assertIsNone(e.transfer_end)
        # Crossing while handling the local cap must also annotate its receipt.
        e = engine(source, target); e.deadline = 10.; clock = [0.]
        e.info['transfer_scans'] = st.TOTAL_SCANS-7
        check = e.check; cap_checks = [0]
        def cap_crossing():
            if getattr(e, 'transfer_end', None) is not None and e.scans >= e.transfer_end:
                cap_checks[0] += 1
                if cap_checks[0] == 2: clock[0] = 11.
            check()
        with patch.object(st.time, 'perf_counter', side_effect=lambda: clock[0]), patch.object(e, 'check', side_effect=cap_crossing):
            with self.assertRaises(rc._Stop): st.transfer_site(e, 0, entry)
        self.assertEqual(cap_checks[0], 2)
        self.assertEqual(e.info['transfer_records'][-1]['status'], 'deadline')
        self.assertEqual(e.info['transfer_records'][-1]['scans'], 7)
        self.assertEqual(entry, saved)

    def test_no_transfer_constructor_matches_fixed_050(self):
        for source in (nx.path_graph(4), nx.star_graph(4)):
            target = nx.complete_graph(10)
            a = ancestor.reduced_core_embed(source, target, timeout=5)
            b = rc.reduced_core_embed(source, target, timeout=5)
            self.assertEqual(a['status'], 'SUCCESS'); self.assertEqual(b['status'], 'SUCCESS')
            self.assertEqual(a['embedding'], b['embedding'])
            for key in ('journal', 'committed_updates', 'partial_requirements', 'core_config',
                        'ordinary_insertion_queries', 'blocked_repair_queries'):
                self.assertEqual(a['diag'][key], b['diag'][key])
            self.assertEqual(b['diag']['transfer_accepted'], 0)

    def test_real_reduction_pipeline_transfer_and_fill_recovery(self):
        source, target, entry = pipeline_fixture(); calls = []
        def core(s, t, **kwargs):
            calls.append(s.copy()); return dict(status='SUCCESS', embedding=entry, diag={})
        with patch.object(rc, '_native_embed', side_effect=core), patch.object(rc._Expansion, 'insert', side_effect=AssertionError('ordinary called')):
            result = rc.reduced_core_embed(source, target, timeout=5)
        self.assertEqual(result['status'], 'SUCCESS', result['diag'])
        self.assertTrue(valid(result['embedding'], source, target)); self.assertEqual(len(calls), 1)
        self.assertTrue(calls[0].has_edge(0, 1))
        d = result['diag']; self.assertEqual(d['transfer_accepted'], 1)
        self.assertEqual(d['ordinary_insertion_queries'], 0)
        self.assertEqual(d['committed_updates'][0]['qubits_added'], 0)
        self.assertEqual(d['committed_updates'][0]['insertion_operator'], 'transfer')
        self.assertEqual(d['committed_updates'][0]['removed_fill'], ((0, 1),))
        self.assertEqual(d['partial_requirements'], {v: sorted(source[v]) for v in source})
        self.assertEqual(sum(d['scans_by_stage'].values()), d['scan_count'])
        self.assertEqual(d['transfer_scans'], sum(r['scans'] for r in d['transfer_records']))

    def test_cleanup_interruption_retains_entry_and_preceding_filled_R(self):
        source, target, entry = pipeline_fixture(); saved = copy.deepcopy(entry)
        clock = [0.]
        def core(*args, **kwargs): return dict(status='SUCCESS', embedding=entry, diag={})
        def interrupted(e, trial, row):
            clock[0] = 6.; e.check()
        with patch.object(rc.time, 'perf_counter', side_effect=lambda: clock[0]), patch.object(rc, '_native_embed', side_effect=core), patch.object(rc, '_prune_released', side_effect=interrupted):
            result = rc.reduced_core_embed(source, target, timeout=5)
        self.assertEqual(result['status'], 'TIMEOUT')
        d = result['diag']; self.assertEqual(d['stopped_by'], 'deadline')
        self.assertEqual(d['partial_embedding'], saved); self.assertEqual(entry, saved)
        self.assertIn(1, d['partial_requirements'][0]); self.assertEqual(d['committed_updates'], [])
        self.assertTrue(d['transfer_records'][0]['certified']); self.assertFalse(d['transfer_records'][0]['committed'])
        self.assertEqual(d['transfer_accepted'], 0)


if __name__ == '__main__': unittest.main()
