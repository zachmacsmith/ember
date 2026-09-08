"""Portable bounded author checks: supplied tiny minors, no constructors/corpus."""
import argparse
from copy import deepcopy
import hashlib
import importlib.abc
import importlib.util
import io
import json
from pathlib import Path
import sys
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import networkx as nx


ROOT = Path(__file__).resolve().parents[1]
ADAPTER = CONTACT = None
BLOCKED = []
DETAILS = {}


class NoEmbeddingImports(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if (fullname.split('.')[0] in ('ember_qc', 'minorminer', 'dwave', 'dwave_networkx')
                or 'busclique' in fullname):
            BLOCKED.append(fullname)
            raise AssertionError('Prohibited import: ' + fullname)


def fixture():
    source = nx.Graph()
    source.add_nodes_from([2, 0, 1])
    source.add_edge(0, 1)
    target = nx.path_graph(5)
    target.add_edge(1, 3)
    entry = {2: [4], 0: [0, 1], 1: [2]}
    return entry, source, target


def mathematical_valid(candidate, source, target):
    if set(candidate) != set(source):
        return False
    occupied = []
    for c in candidate.values():
        if not c or len(c) != len(set(c)) or not set(c) <= set(target):
            return False
        if not nx.is_connected(target.subgraph(c)):
            return False
        occupied.extend(c)
    if len(occupied) != len(set(occupied)):
        return False
    return all(any(target.has_edge(q, p) for q in candidate[u] for p in candidate[v])
               for u, v in source.edges())


def replay(delta, entry):
    out = dict(entry)
    for v in delta.get('removed_keys', []):
        out.pop(v)
    out.update(delta['changed'])
    return {v: out[v] for v in delta.get('key_order', list(entry))}


def stub(callback, context=None):
    return SimpleNamespace(_Context=context or CONTACT._Context,
                           _parameters=CONTACT._parameters, _repair=callback)


def raw(expansions=0, accepted=0, saved=0):
    record = CONTACT._diagnostics()
    record.update(expansions=expansions, accepted=accepted, qubits_saved=saved,
                  wall=0., stopped_by='searched')
    return record


def without_times(record):
    return {k: v for k, v in record.items() if k not in ('wall', 'deadline_overrun')}


class CutClock:
    def __init__(self, cut=None):
        self.calls, self.cut = 0, cut
    def __call__(self):
        self.calls += 1
        return 100. if self.cut is not None and self.calls >= self.cut else 0.


class Checks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        global ADAPTER, CONTACT
        if ADAPTER is None:  # Also supports direct unittest/pytest discovery.
            path = ROOT/'scripts/codex/ordinary_proposal_diagnostic.py'
            spec = importlib.util.spec_from_file_location('_ordinary_diagnostic_author', path)
            ADAPTER = importlib.util.module_from_spec(spec)
            sys.modules[spec.name] = ADAPTER
            spec.loader.exec_module(ADAPTER)
            CONTACT = ADAPTER.load_contact_repair(
                ROOT/'packages/ember-qc/src/ember_qc/algorithms/factored/contact_repair.py')

    def call(self, entry, source, target, groups, **kwargs):
        options = dict(deadline=time.perf_counter()+60, max_expansions=500000,
                       contact_module=CONTACT)
        options.update(kwargs)
        return ADAPTER.ordinary_batch(entry, source, target, groups, **options)

    def test_real_proposals_match_public_wrapper_and_context_is_shared(self):
        entry, source, target = fixture()
        original = deepcopy(entry)
        groups = [(2,), (2,), (0,), (1,)]
        observations, contexts, initial_validations = [], [], []
        class Context(CONTACT._Context):
            def __init__(self, *args):
                super().__init__(*args)
                contexts.append(self)
            def valid(self, e):
                if not initial_validations:
                    initial_validations.append(id(e))
                elif id(e) == initial_validations[0]:
                    initial_validations.append(id(e))
                return super().valid(e)
        def proposal(e, ctx, group, **kwargs):
            self.assertEqual(e, original)
            self.assertEqual(id(e), initial_validations[0])
            self.assertEqual(kwargs['beam_width'], 1)
            result, info = CONTACT._repair(e, ctx, group, **kwargs)
            observations.append((group, kwargs, deepcopy(result), deepcopy(info)))
            return result, info
        candidate, info = self.call(entry, source, target, groups,
                                    contact_module=stub(proposal, Context))
        self.assertIsNotNone(candidate)
        self.assertEqual(len(contexts), 1)
        self.assertEqual(len(initial_validations), 1)
        self.assertEqual(info['groups_called'], 3)
        self.assertEqual(info['uninspected_groups'], 1)
        self.assertTrue(mathematical_valid(candidate, source, target))
        self.assertEqual(candidate[0], [1])
        self.assertEqual(entry, original)
        for row, (group, kwargs, output, move) in zip(info['groups'], observations):
            expected, baseline = CONTACT.repair_group(original, source, target, group, **kwargs)
            self.assertEqual(output, expected)
            self.assertEqual(without_times(move), without_times(baseline))
            self.assertEqual(replay(row['result'], original), output)
        self.assertEqual(sum(r['raw']['expansions'] for r in info['groups']), info['expansions'])
        self.assertTrue(info['inputs_unchanged'] and info['context_unchanged'])
        for v in entry:
            self.assertIsNot(candidate[v], entry[v])
        self.assertAlmostEqual(sum(info['stage_wall'].values()), info['wall'])
        DETAILS['real_public_replays'] = len(observations)

    def test_equal_q_is_diagnostic_only_and_first_return_stops_batch(self):
        entry, source, target = fixture()
        seen = []
        def proposal(e, ctx, group, **kwargs):
            seen.append(deepcopy(e))
            result = deepcopy(e)
            if len(seen) == 1:
                result[0] = [1, 3]
                self.assertTrue(mathematical_valid(result, source, target))
                move = raw(3, 1, 0)
                move.update(equal_size_moves=1, contact_redundancy_gain=1)
            else:
                result[0] = [1]
                move = raw(2, 1, 1)
            return result, move
        candidate, info = self.call(entry, source, target, [(0,), (0,), (0,)],
                                    contact_module=stub(proposal))
        self.assertEqual(seen, [entry, entry])
        self.assertEqual(info['groups_called'], 2)
        self.assertEqual(info['groups'][0]['raw']['accepted'], 1)
        self.assertEqual(info['groups'][0]['q_returned'], 4)
        self.assertEqual(info['final_gate']['qubits_saved'], 1)
        self.assertEqual(candidate[0], [1])

    def test_ordering_multiple_qubit_gain_and_no_followup_selection(self):
        source = nx.Graph()
        source.add_nodes_from([2, 10, 1])
        source.add_edge(10, 1)
        target = nx.path_graph(7)
        entry = {2: [6], 10: [0, 1, 2], 1: [3]}
        seen = []
        def proposal(e, ctx, group, **kwargs):
            self.assertEqual(ctx.nodes, [1, 10, 2])  # repr order, not numeric
            self.assertEqual(group, (10, 2))
            seen.append(1)
            result = dict(e)
            result[10] = [2]
            return result, raw(1, 1, 2)
        candidate, info = self.call(entry, source, target, [(10, 2), (2, 10)],
                                    contact_module=stub(proposal))
        self.assertEqual(len(seen), 1)
        self.assertEqual(info['final_gate']['qubits_saved'], 2)
        self.assertEqual(candidate[1], [3])

    def test_global_work_remainder_duplicates_and_last_unit(self):
        entry, source, target = fixture()
        allowances = []
        def failed(e, ctx, group, **kwargs):
            a = kwargs['max_expansions']
            allowances.append(a)
            return e, raw(min(25000, a))
        result, info = self.call(entry, source, target, [(2,)]*4,
                                 max_expansions=60000, contact_module=stub(failed))
        self.assertIsNone(result)
        self.assertEqual(allowances, [50000, 35000, 10000])
        self.assertEqual(info['expansions'], 60000)
        self.assertEqual(info['stopped_by'], 'work_limit')
        self.assertEqual(info['uninspected_groups'], 1)
        def last(e, ctx, group, **kwargs):
            out = dict(e, **{})
            out[0] = [1]
            return out, raw(kwargs['max_expansions'], 1, 1)
        result, info = self.call(entry, source, target, [(0,)], max_expansions=7,
                                 contact_module=stub(last))
        self.assertIsNotNone(result)
        self.assertEqual(info['expansions'], 7)

    def test_final_gate_original_edges_and_invalid_outputs(self):
        entry, source, target = fixture()
        valid = dict(entry, **{})
        valid[0] = [1]
        mutants = []
        for change in (lambda x: x.pop(2), lambda x: x.update({9: [3]}),
                       lambda x: x.update({0: [99]}), lambda x: x.update({0: []}),
                       lambda x: x.update({0: [1, 1]}), lambda x: x.update({0: [2]}),
                       lambda x: x.update({0: [0, 3]}), lambda x: x.update({0: [0]})):
            bad = deepcopy(valid)
            change(bad)
            mutants.append(bad)
        for bad in mutants:
            with self.subTest(candidate=bad):
                self.assertFalse(mathematical_valid(bad, source, target))
                out, gate = ADAPTER.final_gate(bad, entry, source, target,
                                               deadline=time.perf_counter()+60, allowed_changed=[0])
                self.assertIsNone(out)
                self.assertEqual(gate['reason'], 'invalid_output')
        # A valid minor can still violate the frozen-outside or exact-Q contract.
        outside = deepcopy(valid)
        outside[2] = [3]
        self.assertTrue(mathematical_valid(outside, source, target))
        out, gate = ADAPTER.final_gate(outside, entry, source, target,
                                       deadline=time.perf_counter()+60, allowed_changed=[0])
        self.assertIsNone(out)
        self.assertEqual(gate['outside_unchanged'], False)
        out, gate = ADAPTER.final_gate(valid, entry, source, target,
                                       deadline=time.perf_counter()+60, expected_drop=2)
        self.assertIsNone(out)
        for bad in (mutants[2], outside):
            def proposal(e, ctx, group, **kwargs):
                return deepcopy(bad), raw(1, 1, 1)
            out, info = self.call(entry, source, target, [(0,), (1,)],
                                  contact_module=stub(proposal))
            self.assertIsNone(out)
            self.assertEqual(info['stopped_by'], 'invalid_output')
            self.assertEqual(replay(info['groups'][0]['result'], entry), bad)

    def test_every_gate_and_adapter_clock_cut_rejects_late_credit(self):
        entry, source, target = fixture()
        good = deepcopy(entry)
        good[0] = [1]
        def proposal(e, ctx, group, **kwargs):
            return deepcopy(good), raw(2, 1, 1)
        baseline = CutClock()
        out, _ = ADAPTER.final_gate(good, entry, source, target, deadline=100.,
                                    allowed_changed=[0], clock=baseline)
        self.assertIsNotNone(out)
        for cut in range(1, baseline.calls+1):
            out, info = ADAPTER.final_gate(good, entry, source, target, deadline=100.,
                                           allowed_changed=[0], clock=CutClock(cut))
            self.assertIsNone(out, cut)
            self.assertFalse(info['credited'], cut)
        DETAILS['gate_clock_cuts'] = baseline.calls
        baseline = CutClock()
        out, _ = self.call(entry, source, target, [(0,), (1,)], deadline=100.,
                            contact_module=stub(proposal), clock=baseline)
        self.assertIsNotNone(out)
        for cut in range(1, baseline.calls+1):
            out, info = self.call(entry, source, target, [(0,), (1,)], deadline=100.,
                                   contact_module=stub(proposal), clock=CutClock(cut))
            self.assertIsNone(out, cut)
            self.assertFalse(info['credited_contraction'], cut)
            self.assertEqual(info['stopped_by'], 'deadline', cut)
            self.assertAlmostEqual(sum(info['stage_wall'].values()), info['wall'])
        DETAILS['adapter_clock_cuts'] = baseline.calls

    def test_no_proposal_final_clock_crossing_updates_metadata(self):
        entry, source, target = fixture()
        def unchanged(e, ctx, group, **kwargs):
            return e, raw(1)
        total = 0
        for groups in ([], [(2,)]):
            baseline = CutClock()
            out, info = self.call(entry, source, target, groups, deadline=100.,
                                   contact_module=stub(unchanged), clock=baseline)
            self.assertIsNone(out)
            for cut in range(1, baseline.calls+1):
                out, info = self.call(entry, source, target, groups, deadline=100.,
                                       contact_module=stub(unchanged), clock=CutClock(cut))
                self.assertIsNone(out)
                self.assertTrue(info['deadline_exceeded'])
                self.assertEqual(info['stopped_by'], 'deadline')
                self.assertAlmostEqual(sum(info['stage_wall'].values()), info['wall'])
            total += baseline.calls
        DETAILS['no_proposal_clock_cuts'] = total

    def test_loader_rejects_unbound_bytes_without_importing_them(self):
        with self.assertRaisesRegex(ValueError, 'differs from the reviewed'):
            ADAPTER.load_contact_repair(Path(__file__))
        self.assertEqual(CONTACT.diagnostic_source_sha256, ADAPTER.CONTACT_SHA256)

    def test_raw_late_candidate_and_exception_are_retained(self):
        entry, source, target = fixture()
        state = {'now': 0.}
        def late(e, ctx, group, **kwargs):
            result = deepcopy(e)
            result[0] = [1]
            state['now'] = 101.
            return result, raw(4, 1, 1)
        out, info = self.call(entry, source, target, [(0,)], deadline=100.,
                               clock=lambda: state['now'], contact_module=stub(late))
        self.assertIsNone(out)
        self.assertEqual(info['stopped_by'], 'deadline')
        self.assertTrue(info['returned_contraction'])
        self.assertEqual(info['groups'][0]['q_returned'], 3)
        self.assertEqual(info['expansions'], 4)
        self.assertEqual(replay(info['groups'][0]['result'], entry)[0], [1])
        def failing(e, ctx, group, **kwargs):
            raise RuntimeError('synthetic failure')
        out, info = self.call(entry, source, target, [(0,)], contact_module=stub(failing))
        self.assertEqual(info['groups_called'], 1)
        self.assertEqual(info['stopped_by'], 'error')
        self.assertIn('synthetic failure', info['groups'][0]['call_error'])
        self.assertGreaterEqual(info['groups'][0]['call_wall'], 0)
        self.assertFalse(info['routing_accounting_complete'])
        self.assertIsNone(info['expansions_exact'])
        self.assertEqual(info['unaccounted_group_indices'], [0])

    def test_failed_stages_keep_elapsed_and_unknown_work_is_explicit(self):
        for stage, elapsed in (('setup', 2.), ('entry_validation', 3.), ('final_gate', 5.)):
            entry, source, target = fixture()
            state = {'now': 0.}
            class Context(CONTACT._Context):
                def __init__(self, *args):
                    super().__init__(*args)
                    if stage == 'setup':
                        state['now'] = elapsed
                        raise RuntimeError('synthetic setup')
                def valid(self, e):
                    if stage == 'entry_validation':
                        state['now'] = elapsed
                        raise RuntimeError('synthetic entry validation')
                    return super().valid(e)
            def proposal(e, ctx, group, **kwargs):
                out = deepcopy(e)
                out[0] = [1]
                return out, raw(7, 1, 1)
            def broken_gate(*args, **kwargs):
                state['now'] = elapsed
                raise RuntimeError('synthetic final gate')
            with patch.object(ADAPTER, 'final_gate', broken_gate):
                out, info = self.call(entry, source, target, [(0,)], deadline=100.,
                                       contact_module=stub(proposal, Context),
                                       clock=lambda: state['now'])
            self.assertIsNone(out)
            self.assertEqual(info['stopped_by'], 'error')
            self.assertEqual(info['stage_wall'][stage], elapsed)
            self.assertEqual(info['wall'], elapsed)
            self.assertEqual(info['stage_wall']['diagnostics_and_administration'], 0.)
            self.assertTrue(info['routing_accounting_complete'])
            self.assertEqual(info['expansions_exact'], 7 if stage == 'final_gate' else 0)
        entry, source, target = fixture()
        calls = []
        def interrupted(e, ctx, group, **kwargs):
            calls.append(1)
            if len(calls) == 1:
                return e, raw(7)
            raise RuntimeError('unknown partial routing')
        out, info = self.call(entry, source, target, [(2,), (2,), (0,)],
                               contact_module=stub(interrupted))
        self.assertIsNone(out)
        self.assertEqual(info['expansions'], 7)
        self.assertIsNone(info['expansions_exact'])
        self.assertFalse(info['routing_accounting_complete'])
        self.assertEqual(info['unaccounted_group_indices'], [1])
        self.assertEqual(info['groups_called'], 2)
        self.assertEqual(info['uninspected_groups'], 1)

    def test_empty_invalid_scalar_group_and_entry_contracts(self):
        entry, source, target = fixture()
        out, info = self.call(entry, source, target, [])
        self.assertEqual(info['stopped_by'], 'no_groups')
        self.assertFalse(info['setup_completed'])
        for group in ([], [0, 0], [99], [True], [0, 1, 2, 3, 4], iter([0])):
            out, info = self.call(entry, source, target, [group])
            self.assertIsNone(out)
            self.assertEqual(info['stopped_by'], 'invalid_input')
            self.assertEqual(info['groups_called'], 0)
        for cap in (-1, True, 1.2):
            with self.assertRaises(ValueError):
                self.call(entry, source, target, [(0,)], max_expansions=cap)
        for deadline in (None, float('nan'), float('inf'), True):
            with self.assertRaises(ValueError):
                self.call(entry, source, target, [(0,)], deadline=deadline)
        bad = deepcopy(entry)
        bad.pop(2)
        out, info = self.call(bad, source, target, [(0,)])
        self.assertEqual(info['stopped_by'], 'invalid_input')
        self.assertFalse(info['entry_validated'])

    def test_input_context_mutation_and_counter_corruption_fail_closed(self):
        for mutation in ('entry', 'context', 'counter'):
            entry, source, target = fixture()
            saved = deepcopy(entry)
            def proposal(e, ctx, group, **kwargs):
                result = deepcopy(e)
                result[0] = [1]
                if mutation == 'entry':
                    e[0].append(99)
                if mutation == 'context':
                    ctx.adj[0] = ()
                return result, raw(-1 if mutation == 'counter' else 1, 1, 1)
            out, info = self.call(entry, source, target, [(0,)], contact_module=stub(proposal))
            self.assertIsNone(out)
            self.assertEqual(info['stopped_by'], 'error')
            self.assertEqual(entry, saved)  # private ordinary entry protects caller
            self.assertIsNotNone(info['groups'][0]['result'])

    def test_evaluator_validator_and_exchange_gate_share_original_predicate(self):
        entry, source, target = fixture()
        check = ADAPTER.validate_embedding(entry, source, target)
        self.assertTrue(check['valid'])
        self.assertEqual(check['qubits'], 4)
        candidate = deepcopy(entry)
        candidate[0] = [1]
        out, gate = ADAPTER.final_gate(candidate, entry, source, target,
                                       deadline=time.perf_counter()+60,
                                       allowed_changed=[0], expected_drop=1)
        self.assertTrue(gate['credited'])
        self.assertTrue(mathematical_valid(out, source, target))
        for v in candidate:
            self.assertIsNot(out[v], candidate[v])
            self.assertIsNot(out[v], entry[v])
        target.remove_edge(1, 2)
        self.assertFalse(ADAPTER.validate_embedding(candidate, source, target)['valid'])


def main():
    global ROOT, ADAPTER, CONTACT
    parser = argparse.ArgumentParser()
    parser.add_argument('--repo', type=Path, default=ROOT)
    parser.add_argument('--output-dir', type=Path, required=True)
    parser.add_argument('--test', action='append', help='Run only these named focused checks')
    args = parser.parse_args()
    ROOT = args.repo.absolute()
    args.output_dir.mkdir(parents=True, exist_ok=False)
    paths = [ROOT/'scripts/codex/ordinary_proposal_diagnostic.py', Path(__file__).absolute(),
             ROOT/'packages/ember-qc/src/ember_qc/algorithms/factored/contact_repair.py']
    before = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    (args.output_dir/'source_hashes.json').write_text(json.dumps(before, sort_keys=True, indent=2)+'\n')
    spec = importlib.util.spec_from_file_location('_ordinary_diagnostic_author', paths[0])
    ADAPTER = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = ADAPTER
    guard = NoEmbeddingImports()
    sys.meta_path.insert(0, guard)
    spec.loader.exec_module(ADAPTER)
    CONTACT = ADAPTER.load_contact_repair(paths[2])
    stream = io.StringIO()
    started = time.perf_counter()
    suite = (unittest.TestSuite(Checks(name) for name in args.test) if args.test else
             unittest.defaultTestLoader.loadTestsFromTestCase(Checks))
    outcome = unittest.TextTestRunner(stream=stream, verbosity=2).run(suite)
    elapsed = time.perf_counter()-started
    loaded = sorted(name for name in sys.modules if name.split('.')[0] in
                    ('ember_qc', 'minorminer', 'dwave', 'dwave_networkx') or 'busclique' in name)
    after = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    status = outcome.wasSuccessful() and before == after and not BLOCKED and not loaded
    summary = dict(status='PASS' if status else 'FAIL', tests=outcome.testsRun,
                   failures=len(outcome.failures), errors=len(outcome.errors),
                   skipped=len(outcome.skipped), wall=elapsed, source_hashes=before,
                   sources_unchanged=before == after, blocked_imports=BLOCKED,
                   forbidden_loaded=loaded, python=sys.executable, argv=sys.argv,
                   details=DETAILS,
                   fixtures='tiny supplied synthetic graphs only; no constructor/corpus/competitor')
    (args.output_dir/'tests.txt').write_text(stream.getvalue())
    (args.output_dir/'summary.json').write_text(json.dumps(summary, sort_keys=True, indent=2)+'\n')
    print(json.dumps(summary, sort_keys=True))
    raise SystemExit(0 if status else 1)


if __name__ == '__main__':
    main()
