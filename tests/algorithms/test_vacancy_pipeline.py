"""Bounded cumulative-stage checks; constructors remain inert."""
from copy import deepcopy
import importlib.util
from pathlib import Path

import networkx as nx
import pytest

from ember_qc.algorithms.factored import native, vacancy_repair as vr


_spec = importlib.util.spec_from_file_location(
    '_deletion_integration_fixtures', Path(__file__).with_name('test_deletion_closure_integration.py'))
fixtures = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(fixtures)


def graphs(count=4):
    return nx.empty_graph(1), nx.path_graph(count), {0: list(range(count))}


def stage(source, target, entry, *, started=95., deadline=160., cleanup='completed'):
    info = {}
    output, error = native._bounded_vacancy_refinement(
        entry, source, target, {v: set(source[v]) for v in source},
        {q: set(target[q]) for q in target}, started=started, deadline=deadline,
        cleanup_info={'status': cleanup}, info=info)
    return output, error, info


def core_info(candidate, before, budget, *, reason=None):
    return dict(candidate_returned=candidate is not None,
                certificate_complete=int(candidate is not None), error=None,
                stopped_reason=reason or 'candidate_returned',
                proposal={'q_before': before, 'q_after': before-1, 'trace': [[0, 0, 1]]}
                if candidate is not None else None,
                work_total=budget.expansions)


def test_two_successes_then_failed_query_share_entry_budget_and_deadline(monkeypatch):
    clock = fixtures.Clock(); monkeypatch.setattr(native.time, 'perf_counter', clock)
    source, target, entry = graphs()
    before = deepcopy(entry); seen = []
    def query(current, source_adj, target_adj, groups, *, budget, deadline):
        seen.append((deepcopy(current), id(budget), budget.expansions, deadline, groups))
        for _ in range(len(seen)):
            assert budget.pop()
        result = {0: current[0][1:]} if len(seen) < 3 else None
        return result, core_info(result, len(current[0]), budget, reason='seeds_exhausted' if result is None else None)
    monkeypatch.setattr(vr, 'vacancy_repair', query)
    output, error, info = stage(source, target, entry)
    fixtures.verify(output, source, target)
    assert error is None and output == {0: [2, 3]} and entry == before
    assert [row[0] for row in seen] == [{0: [0, 1, 2, 3]}, {0: [1, 2, 3]}, {0: [2, 3]}]
    assert len({row[1] for row in seen}) == 1 and {row[3] for row in seen} == {101.}
    assert [row[2] for row in seen] == [0, 1, 3] and all(row[4] == () for row in seen)
    assert info['accepted'] == info['qubits_saved'] == 2 and info['query_calls'] == 3
    assert info['proposals_used'] == 6 and info['reason'] == 'seeds_exhausted'
    assert [row['committed'] for row in info['calls']] == [True, True, False]
    assert [(row['budget_start'], row['budget_end']) for row in info['calls']] == [(0, 1), (1, 3), (3, 6)]
    assert [row['core']['proposal']['trace'] for row in info['calls'][:2]] == [[[0, 0, 1]]] * 2


def test_one_global_proposal_cap_retains_earlier_success(monkeypatch):
    monkeypatch.setattr(native.time, 'perf_counter', fixtures.Clock())
    source, target, entry = graphs()
    calls = []
    def query(current, *args, budget, **kwargs):
        calls.append(budget.expansions)
        if len(calls) == 1:
            for _ in range(49999): assert budget.pop()
            result = {0: current[0][1:]}
            return result, core_info(result, len(current[0]), budget)
        assert budget.pop() and not budget.pop()
        return None, core_info(None, len(current[0]), budget, reason='work')
    monkeypatch.setattr(vr, 'vacancy_repair', query)
    output, error, info = stage(source, target, entry)
    assert output == {0: [1, 2, 3]} and error is None
    assert calls == [0, 49999] and info['proposals_used'] == 50000
    assert info['accepted'] == 1 and info['status'] == 'interrupted' and info['reason'] == 'work'


def test_twenty_successful_calls_are_the_only_iteration_cap(monkeypatch):
    monkeypatch.setattr(native.time, 'perf_counter', fixtures.Clock())
    source, target, entry = graphs(22)
    def query(current, *args, budget, **kwargs):
        assert budget.pop()
        result = {0: current[0][1:]}
        return result, core_info(result, len(current[0]), budget)
    monkeypatch.setattr(vr, 'vacancy_repair', query)
    output, error, info = stage(source, target, entry)
    fixtures.verify(output, source, target)
    assert output == {0: [20, 21]} and error is None
    assert info['accepted'] == info['query_calls'] == info['proposals_used'] == 20
    assert info['reason'] == 'successful_call_limit'


@pytest.mark.parametrize('crossing', ['query', 'validation'])
def test_late_second_candidate_never_replaces_first(monkeypatch, crossing):
    clock = fixtures.Clock(); monkeypatch.setattr(native.time, 'perf_counter', clock)
    source, target, entry = graphs(); calls = []
    validator = native.is_valid_embedding
    def query(current, *args, budget, deadline, **kwargs):
        calls.append(deadline); assert budget.pop()
        result = {0: current[0][1:]}
        if len(calls) == 2 and crossing == 'query': clock.value = deadline
        return result, core_info(result, len(current[0]), budget)
    def validate(*args):
        result = validator(*args)
        if len(calls) == 2 and crossing == 'validation': clock.value = calls[-1]
        return result
    monkeypatch.setattr(vr, 'vacancy_repair', query)
    monkeypatch.setattr(native, 'is_valid_embedding', validate)
    output, error, info = stage(source, target, entry, started=99., deadline=100.15)
    assert output == {0: [1, 2, 3]} and error is None and calls == [100.15, 100.15]
    assert info['allowance'] == pytest.approx(.2)
    assert info['accepted'] == 1 and info['reason'] == 'deadline'
    assert info['calls'][1]['core']['certificate_complete'] == 1
    assert info['calls'][1]['committed'] is False and info['calls'][1]['commit_rejection'] == 'deadline'


@pytest.mark.parametrize('failure', ['core_error', 'exception', 'bad_cardinality', 'invalid_chain'])
def test_invalid_or_exceptional_query_is_an_explicit_error(monkeypatch, failure):
    monkeypatch.setattr(native.time, 'perf_counter', fixtures.Clock())
    source, target, entry = graphs()
    def query(current, *args, budget, **kwargs):
        assert budget.pop()
        if failure == 'exception': raise RuntimeError('synthetic query failure')
        if failure == 'core_error':
            return None, {'stopped_reason': 'internal_error', 'error': 'synthetic'}
        result = deepcopy(current) if failure == 'bad_cardinality' else {0: [0, 2, 3]}
        return result, core_info(result, len(current[0]), budget)
    monkeypatch.setattr(vr, 'vacancy_repair', query)
    output, error, info = stage(source, target, entry)
    assert output is entry and error in ('ERROR', 'INVALID_OUTPUT')
    assert info['status'] == 'error' and info['accepted'] == 0 and info['proposals_used'] == 1
    assert info['calls'][0]['committed'] is False
    assert info['calls'][0]['budget_end'] == 1 and info['calls'][0]['module_call_wall'] is not None


def test_real_five_cycle_query_and_final_exhaustion_are_valid_and_immutable():
    source = nx.Graph([(0, 1), (0, 2)])
    target = nx.Graph([(10, 11), (10, 12), (11, 13), (12, 14), (13, 14)])
    entry = {0: [11, 10], 1: [12], 2: [13]}; before = deepcopy(entry)
    # This is a constructor-free physical witness; neither possible initial
    # deletion retains both contacts, but relocation to site 14 does.
    for removed in entry[0]:
        trial = deepcopy(entry); trial[0].remove(removed)
        assert not native.is_valid_embedding(trial, source, target)
    now = native.time.perf_counter()
    output, error, info = stage(source, target, entry, started=now-5, deadline=now+10)
    fixtures.verify(output, source, target)
    assert error is None and output == {0: [14], 1: [12], 2: [13]} and entry == before
    assert info['accepted'] == 1 and info['query_calls'] == 2
    assert info['calls'][0]['core']['proposal']['trace']
    assert info['calls'][1]['core']['stopped_reason'] == 'seeds_exhausted'


def test_last_wrapper_clock_crossing_is_reported_without_discarding_entry(monkeypatch):
    pending = []
    def clock(): return pending.pop(0) if pending else 100.
    monkeypatch.setattr(native.time, 'perf_counter', clock)
    source, target, entry = graphs()
    def query(current, *args, budget, **kwargs):
        pending.extend([100., 101.])  # query timer, then wrapper's final observation
        return None, core_info(None, len(current[0]), budget, reason='seeds_exhausted')
    monkeypatch.setattr(vr, 'vacancy_repair', query)
    output, error, info = stage(source, target, entry)
    assert output is entry and error is None and info['wall'] == 1.
    assert info['status'] == 'interrupted' and info['reason'] == 'deadline'
    assert info['calls'][0]['core']['stopped_reason'] == 'seeds_exhausted'


def test_default_off_preserves_existing_deletion_result_and_imports(monkeypatch):
    source, target, _, _, _ = fixtures.pipeline(monkeypatch)
    expected = native.native_embed(source, target, **fixtures.OPTIONS)
    original = __import__('builtins').__import__
    def guard(name, *args, **kwargs):
        if name.endswith('vacancy_repair'): raise AssertionError('disabled import')
        return original(name, *args, **kwargs)
    monkeypatch.setattr('builtins.__import__', guard)
    actual = native.native_embed(source, target, **fixtures.OPTIONS, vacancy_refinement='off')
    assert actual == expected and 'vacancy_refinement' not in actual['diag']


def test_pipeline_mixed_labels_after_deletion_and_before_original_validation(monkeypatch):
    source, target, _, clock, events = fixtures.pipeline(monkeypatch)
    cleanup = native._final_deletion_cleanup
    def close(*args, **kwargs):
        result = cleanup(*args, **kwargs)
        clock.value += 1
        events.append(('deletion_complete', None))
        return result
    def query(current, *args, budget, deadline, **kwargs):
        assert current == {0: [2], 1: [3], 2: [4]}
        assert deadline == pytest.approx(101.2)
        events.append(('vacancy', deadline))
        return None, core_info(None, 3, budget, reason='seeds_exhausted')
    monkeypatch.setattr(native, '_final_deletion_cleanup', close)
    monkeypatch.setattr(vr, 'vacancy_repair', query)
    result = native.native_embed(source, target, **fixtures.OPTIONS, vacancy_refinement='bounded')
    fixtures.verify(result['embedding'], source, target)
    assert result['status'] == 'SUCCESS'
    info = result['diag']['vacancy_refinement']
    assert info['before_qubits'] == result['diag']['final_cleanup']['after_qubits'] == 3
    assert info['after_qubits'] == sum(map(len, result['embedding'].values()))
    assert info['pipeline_status'] == 'SUCCESS' and info['query_calls'] == 1
    assert [row[0] for row in events][-2:] == ['deletion_complete', 'vacancy']


def test_pipeline_core_error_is_uncredited_and_preserves_valid_partial(monkeypatch):
    source, target, _, clock, _ = fixtures.pipeline(monkeypatch)
    cleanup = native._final_deletion_cleanup
    def close(*args, **kwargs):
        result = cleanup(*args, **kwargs); clock.value += 1
        return result
    monkeypatch.setattr(native, '_final_deletion_cleanup', close)
    monkeypatch.setattr(vr, 'vacancy_repair', lambda *a, **k:
                        (None, {'error': 'synthetic core error', 'stopped_reason': 'internal_error'}))
    result = native.native_embed(source, target, **fixtures.OPTIONS, vacancy_refinement='bounded')
    assert result['status'] == 'ERROR' and not result['embedding'] and not result['success']
    fixtures.verify(result['partial_embedding'], source, target)
    assert result['diag']['vacancy_refinement']['pipeline_status'] == 'ERROR'
    assert result['diag']['vacancy_refinement']['reason'] == 'core_error'


@pytest.mark.parametrize('policy,cleanup', [('bad', 'deletion'), ('bounded', 'off')])
def test_policy_rejected_before_construction(policy, cleanup):
    result = native.native_embed(nx.Graph(), nx.Graph(), vacancy_refinement=policy, final_cleanup=cleanup)
    assert result['status'] == 'ERROR' and 'vacancy' in result['error']


@pytest.mark.parametrize('why', ['cleanup', 'deadline'])
def test_skips_do_not_import_or_query(monkeypatch, why):
    clock = fixtures.Clock(); monkeypatch.setattr(native.time, 'perf_counter', clock)
    def forbidden(*args, **kwargs): raise AssertionError('skipped query')
    monkeypatch.setattr(vr, 'vacancy_repair', forbidden)
    source, target, entry = graphs()
    output, error, info = stage(source, target, entry,
                               deadline=100. if why == 'deadline' else 160.,
                               cleanup='interrupted' if why == 'cleanup' else 'completed')
    assert output is entry and error is None and info['status'] == 'skipped'
    assert info['query_calls'] == 0 and info['proposals_used'] == 0
