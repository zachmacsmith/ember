"""Final cleanup wiring and independent tiny-minor checks, never corpus trials."""
import builtins
from copy import deepcopy
import importlib.util
from pathlib import Path
from types import SimpleNamespace

import dwave_networkx as dnx
import networkx as nx
import pytest

from ember_qc.algorithms.factored import contact_repair as cr
from ember_qc.algorithms.factored import deletion_closure as dc
from ember_qc.algorithms.factored import native, plane, spectral_order


ROOT = Path(__file__).resolve().parents[2]
OPTIONS = dict(final_cleanup='deletion', polish_objective='qubits_contacts',
               polish_passes=1, timeout=60)


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def verify(embedding, source, target):
    assert set(embedding) == set(source)
    occupied = [q for chain in embedding.values() for q in chain]
    assert len(occupied) == len(set(occupied)) and set(occupied) <= set(target)
    for chain in embedding.values():
        assert chain and nx.is_connected(target.subgraph(chain))
    for u, v in source.edges:
        assert any(target.has_edge(q, p) for q in embedding[u] for p in embedding[v])


class Clock:
    value = 100.
    def __call__(self):
        return self.value


def pipeline(monkeypatch, module=native):
    """Inert construction/pruning adapters; real closure and original validators."""
    source = nx.Graph()
    source.add_edge(('center', 0), 'leaf')
    source.add_node(('isolate',))
    target = nx.Graph([(0, 1), (0, 2), (2, 3)])
    target.add_node(4)
    target.graph.update(family='zephyr', labels='int')
    entry = {0: [0, 1, 2], 1: [3], 2: [4]}
    clock, events = Clock(), []
    monkeypatch.setattr(module.time, 'perf_counter', clock)
    monkeypatch.setattr(dnx, 'zephyr_layout', lambda graph: {})
    monkeypatch.setattr(module, 'TileGrid', lambda *a, **k: SimpleNamespace(stride=2, wire_map={0: 1}))
    monkeypatch.setattr(plane, 'arrange', lambda *a, **k: ({}, ({}, {}), {'asks': 0}))
    monkeypatch.setattr(module, 'wire_seeds_exact', lambda *a: (deepcopy(entry), {'fake': True}))
    monkeypatch.setattr(module, 'complete_seeds', lambda grid, chains, *a: (chains, {'fake': True}))
    def prune(chains, *args, **kwargs):
        events.append(('prune', kwargs['deadline']))
        return deepcopy(chains)
    def contact(chains, *args, **kwargs):
        events.append(('contact', kwargs['deadline']))
        return deepcopy(chains), {'qubits_saved': 0, 'accepted': 0, 'trajectory': [], 'stopped_by': 'passes'}
    monkeypatch.setattr(module, 'spur_prune', prune)
    monkeypatch.setattr(cr, 'contact_polish', contact)
    return source, target, entry, clock, events


def prohibit_cleanup_import(monkeypatch):
    original = builtins.__import__
    def guarded(name, *args, **kwargs):
        if name.endswith('deletion_closure'):
            raise AssertionError('cleanup imported on a skipped/off path')
        return original(name, *args, **kwargs)
    monkeypatch.setattr(builtins, '__import__', guarded)


def test_default_and_explicit_off_match_preintegration_envelope_exactly(monkeypatch):
    old = load(ROOT / 'results/codex/deletion-closure-integration-checks/reference/native.py', '_cleanup_old_native')
    source, target, _, _, _ = pipeline(monkeypatch, old)
    expected = old.native_embed(source, target, polish_objective='qubits_contacts', polish_passes=1)
    source, target, _, _, events = pipeline(monkeypatch)
    prohibit_cleanup_import(monkeypatch)
    for options in ({}, {'final_cleanup': 'off'}):
        result = native.native_embed(source, target, polish_objective='qubits_contacts', polish_passes=1, **options)
        assert result == expected
        assert 'final_cleanup' not in result['diag'] and 'final_cleanup_policy' not in result['diag']
    assert [event[0] for event in events] == ['prune', 'contact', 'prune', 'contact']


def test_real_closure_order_deadline_full_trace_and_q_accounting(monkeypatch):
    source, target, entry, _, events = pipeline(monkeypatch)
    source_before, target_before, entry_before = deepcopy(source), deepcopy(target), deepcopy(entry)
    validator, closure = native.is_valid_embedding, dc.deletion_closure
    validations, calls = [], []
    def validate(chains, source_arg, target_arg, *args, **kwargs):
        validations.append(source_arg)
        events.append(('validate', None))
        return validator(chains, source_arg, target_arg, *args, **kwargs)
    def close(chains, *args, **kwargs):
        calls.append(kwargs)
        events.append(('cleanup', kwargs['deadline']))
        return closure(chains, *args, **kwargs)
    monkeypatch.setattr(native, 'is_valid_embedding', validate)
    monkeypatch.setattr(dc, 'deletion_closure', close)
    result = native.native_embed(source, target, **OPTIONS)
    assert result['success']
    verify(result['embedding'], source, target)
    assert [name for name, _ in events] == ['validate', 'prune', 'contact', 'validate', 'cleanup', 'validate']
    assert validations[-1] is source and all(graph is not source for graph in validations[:-1])
    assert {d for name, d in events if name in ('prune', 'contact', 'cleanup')} == {160.}
    assert len(calls) == 1
    info = result['diag']['final_cleanup']; module = info['module']
    assert info['status'] == 'completed' and info['entry_validated'] is True
    assert info['contact_invoked'] and info['contact_returned'] and not info['contact_invalid_input']
    assert info['module_calls'] == 1 and info['module_returned']
    assert module['input_validated'] and module['private_copy_complete'] and not module['returned_input_alias']
    assert [(r['round'], r['source_vertex'], r['qubit']) for r in module['accepted_sequence']] == [(1, 0, 1), (2, 0, 0)]
    assert info['before_qubits'] == result['diag']['pruned_qubits'] - result['diag']['contact_repair']['qubits_saved'] == 5
    assert info['after_qubits'] == sum(map(len, result['embedding'].values())) == 3
    assert info['qubits_saved'] == module['accepted_deletions'] == len(module['accepted_sequence']) == 2
    # Reconstruct all cleanup states independently, using only final sets and trace.
    labels = list(source)
    recovered = {i: set(result['embedding'][label]) for i, label in enumerate(labels)}
    for record in reversed(module['accepted_sequence']):
        v, q = record['source_vertex'], record['qubit']
        assert q not in set.union(*recovered.values())
        assert len(recovered[v]) == record['new_chain_size']
        recovered[v].add(q)
        assert len(recovered[v]) == record['old_chain_size']
        verify({labels[i]: list(chain) for i, chain in recovered.items()}, source, target)
    assert recovered == {v: set(chain) for v, chain in entry.items()}
    assert entry == entry_before and nx.utils.graphs_equal(source, source_before) and nx.utils.graphs_equal(target, target_before)


@pytest.mark.parametrize('overrides', [dict(final_cleanup='unknown'), dict(polish_objective='qubits'),
    dict(polish_objective='qubits_endpoint_support'), dict(polish_tree_policy='distance'),
    dict(polish_singleton_policy='direct'), dict(polish_star_policy='matching'), dict(polish_star_policy='connected')])
def test_unsupported_policy_combinations_rejected_before_construction(monkeypatch, overrides):
    prohibit_cleanup_import(monkeypatch)
    options = {**OPTIONS, **overrides, 'polish_passes': 0}
    result = native.native_embed(nx.Graph(), dnx.zephyr_graph(1), **options)
    assert result['status'] == 'ERROR' and 'final' in result['error']


@pytest.mark.parametrize('which', ['source', 'target'])
@pytest.mark.parametrize('kind', ['directed', 'parallel', 'loop'])
def test_simple_graph_guards_precede_empty_source(monkeypatch, which, kind):
    graphs = dict(source=nx.Graph(), target=dnx.zephyr_graph(1))
    if kind == 'directed': graphs[which] = nx.DiGraph(graphs[which])
    elif kind == 'parallel': graphs[which] = nx.MultiGraph(graphs[which])
    else: graphs[which].add_edge(0, 0)
    prohibit_cleanup_import(monkeypatch)
    result = native.native_embed(graphs['source'], graphs['target'], **OPTIONS)
    assert result['status'] == 'ERROR' and 'simple undirected loopless' in result['error']
    assert result['diag']['final_cleanup']['prerequisite_wall'] is not None


@pytest.mark.parametrize('label', ['q', .5, False])
def test_actual_target_labels_checked_despite_integer_metadata(label):
    target = nx.Graph()
    target.add_node(label); target.graph.update(family='zephyr', labels='int')
    result = native.native_embed(nx.Graph(), target, **OPTIONS)
    assert result['status'] == 'ERROR' and 'integer target labels' in result['error']


def test_empty_source_and_disabled_refinement_skip_without_import(monkeypatch):
    source, target, _, _, _ = pipeline(monkeypatch)
    prohibit_cleanup_import(monkeypatch)
    empty = native.native_embed(nx.Graph(), target, **OPTIONS)
    assert empty['success'] and empty['embedding'] == {}
    info = empty['diag']['final_cleanup']
    assert info['reason'] == 'empty_source' and info['module_calls'] == 0 and 'module' not in info
    assert info['entry_validated'] is None and info['before_qubits'] == info['after_qubits'] == 0
    result = native.native_embed(source, target, **{**OPTIONS, 'polish_passes': 0})
    verify(result['embedding'], source, target)
    info = result['diag']['final_cleanup']
    assert result['success'] and info['reason'] == 'polish_disabled' and not info['contact_invoked']
    assert info['module_calls'] == 0 and info['qubits_saved'] == 0 and info['module_call_wall'] is None


@pytest.mark.parametrize('stage,reason', [('prune', 'deadline_before_refinement'),
    ('contact', 'deadline_before_cleanup'), ('entry_validation', 'deadline_after_entry_validation')])
def test_deadline_skips_retain_valid_incumbent_and_final_validation(monkeypatch, stage, reason):
    source, target, _, clock, _ = pipeline(monkeypatch)
    if stage == 'prune':
        prune_fn = native.spur_prune
        def prune(*args, **kwargs):
            result = prune_fn(*args, **kwargs); clock.value = 170.; return result
        monkeypatch.setattr(native, 'spur_prune', prune)
    elif stage == 'contact':
        contact_fn = cr.contact_polish
        def contact(*args, **kwargs):
            result = contact_fn(*args, **kwargs); clock.value = 170.; return result
        monkeypatch.setattr(cr, 'contact_polish', contact)
    fn = native.is_valid_embedding; seen = []
    def valid(*args, **kwargs):
        seen.append(args[1])
        result = fn(*args, **kwargs)
        if stage == 'entry_validation' and len(seen) == 2: clock.value = 170.
        return result
    monkeypatch.setattr(native, 'is_valid_embedding', valid)
    prohibit_cleanup_import(monkeypatch)
    result = native.native_embed(source, target, **OPTIONS)
    verify(result['embedding'], source, target)
    info = result['diag']['final_cleanup']
    assert result['status'] == 'TIMEOUT' and info['reason'] == reason and info['module_calls'] == 0
    assert seen[-1] is source and info['after_qubits'] == info['before_qubits'] == 5
    assert info['entry_validated'] is (True if stage == 'entry_validation' else None)
    if stage == 'entry_validation': assert info['entry_validation_wall'] == 70.


@pytest.mark.parametrize('mode', ['flag', 'invalid'])
def test_invalid_contact_result_never_reaches_closure(monkeypatch, mode):
    source, target, _, _, _ = pipeline(monkeypatch)
    def contact(chains, *a, **k):
        if mode == 'invalid': chains = {**chains, 0: [0, 1]}
        return chains, {'invalid_input': mode == 'flag', 'qubits_saved': 0}
    monkeypatch.setattr(cr, 'contact_polish', contact)
    prohibit_cleanup_import(monkeypatch)
    result = native.native_embed(source, target, **OPTIONS)
    info = result['diag']['final_cleanup']
    assert result['status'] == 'INVALID_OUTPUT' and not result['embedding']
    assert info['reason'] == ('invalid_contact_input' if mode == 'flag' else 'invalid_cleanup_entry')
    assert info['module_calls'] == 0 and info['entry_validated'] is (None if mode == 'flag' else False)


@pytest.mark.parametrize('stage', ['copy', 'second_commit'])
def test_actual_core_interruption_alias_or_private_prefix(monkeypatch, stage):
    source, target, _, clock, _ = pipeline(monkeypatch)
    checkpoint = dc._Meter.checkpoint; commits = 0
    def expire(self, current):
        nonlocal commits
        if current == 'commit': commits += 1
        if (stage == 'copy' and current == 'copy') or (stage == 'second_commit' and current == 'commit' and commits == 2):
            clock.value = 170.
        return checkpoint(self, current)
    monkeypatch.setattr(dc._Meter, 'checkpoint', expire)
    result = native.native_embed(source, target, **OPTIONS)
    verify(result['embedding'], source, target)
    info = result['diag']['final_cleanup']; module = info['module']
    assert result['status'] == 'TIMEOUT' and info['status'] == 'interrupted' and info['entry_validated']
    assert info['module_calls'] == 1 and not module['closure_complete']
    assert module['returned_input_alias'] == (stage == 'copy')
    assert module['input_validated'] == (stage != 'copy')
    assert info['qubits_saved'] == module['accepted_deletions'] == (0 if stage == 'copy' else 1)
    assert info['after_qubits'] == sum(map(len, result['embedding'].values()))


@pytest.mark.parametrize('mode', ['invalid', 'late'])
def test_original_final_validator_is_retained_after_complete_cleanup(monkeypatch, mode):
    source, target, _, clock, _ = pipeline(monkeypatch)
    fn = native.is_valid_embedding; seen = []
    def validate(*args, **kwargs):
        seen.append(args[1]); valid = fn(*args, **kwargs)
        if args[1] is source:
            if mode == 'invalid': return False
            clock.value = 170.
        return valid
    monkeypatch.setattr(native, 'is_valid_embedding', validate)
    result = native.native_embed(source, target, **OPTIONS)
    assert seen[-1] is source and len(seen) == 3
    assert result['diag']['final_cleanup']['status'] == 'completed'
    assert result['status'] == ('INVALID_OUTPUT' if mode == 'invalid' else 'TIMEOUT')
    if mode == 'late': verify(result['embedding'], source, target)


def test_construction_failure_preserves_unknown_cleanup_fields(monkeypatch):
    source, target, _, _, _ = pipeline(monkeypatch)
    monkeypatch.setattr(native, 'wire_seeds_exact', lambda *a: ({0: [0, 1], 1: [3], 2: [4]}, {}))
    prohibit_cleanup_import(monkeypatch)
    result = native.native_embed(source, target, **OPTIONS)
    info = result['diag']['final_cleanup']
    assert result['status'] == 'CONSTRUCTION_FAILED' and result['partial_embedding']
    assert info['reason'] == 'pipeline_not_reached' and info['pipeline_stage'] == 'conversion'
    assert info['before_qubits'] is info['after_qubits'] is info['qubits_saved'] is None
    assert not info['contact_invoked'] and info['wall'] is None and 'module' not in info


@pytest.mark.parametrize('stage', ['contact', 'entry_validation', 'module'])
def test_caught_exceptions_retain_known_costs_without_fabricated_module_info(monkeypatch, stage):
    source, target, _, clock, _ = pipeline(monkeypatch)
    def fail(*args, **kwargs):
        clock.value = 105.
        raise RuntimeError('synthetic failure')
    if stage == 'contact': monkeypatch.setattr(cr, 'contact_polish', fail)
    elif stage == 'module': monkeypatch.setattr(dc, 'deletion_closure', fail)
    else:
        fn = native.is_valid_embedding; calls = 0
        def validate(*a, **k):
            nonlocal calls
            calls += 1
            if calls == 2: return fail()
            return fn(*a, **k)
        monkeypatch.setattr(native, 'is_valid_embedding', validate)
    result = native.native_embed(source, target, **OPTIONS)
    info = result['diag']['final_cleanup']
    assert result['status'] == 'ERROR' and 'synthetic failure' in result['error']
    assert 'module' not in info and not info['module_returned']
    if stage == 'contact':
        assert info['reason'] == 'pipeline_not_reached' and info['contact_invoked'] and not info['contact_returned']
    else:
        assert info['reason'] == 'exception' and info['status'] == 'error' and info['wall'] == 5.
        assert info['entry_validation_wall'] == (5. if stage == 'entry_validation' else 0.)
        assert info['module_calls'] == (1 if stage == 'module' else 0)
        assert info['module_call_wall'] == (5. if stage == 'module' else None)


def test_one_real_native_smoke_common_deadline_labels_and_unchanged_inputs(monkeypatch):
    calls = []
    def observe(name, fn):
        def wrapper(*args, **kwargs):
            calls.append((name, kwargs)); return fn(*args, **kwargs)
        return wrapper
    for module, attr, name in [(spectral_order, 'spectral_orders', 'initial'),
                              (plane, 'arrange', 'layout'), (native, 'spur_prune', 'prune'),
                              (cr, 'contact_polish', 'contact'), (dc, 'deletion_closure', 'cleanup')]:
        monkeypatch.setattr(module, attr, observe(name, getattr(module, attr)))
    source = nx.path_graph(7); source.add_node(7)
    source = nx.relabel_nodes(source, {v: ('v', v) if v % 2 else f'x{v}' for v in source})
    source.graph.update(family='unused', embedding={'unused': [-1]})
    target = dnx.zephyr_graph(3)
    before = deepcopy(source), deepcopy(target)
    result = native.native_embed(source, target, **{**OPTIONS, 'timeout': 30}, initialization='spectral',
        seed=0, max_asks=16, max_groups=4, polish_group_sizes=(1, 2), polish_expansions=2000, beam_width=1)
    assert result['success'], result
    verify(result['embedding'], source, target)
    assert [name for name, _ in calls] == ['initial', 'layout', 'prune', 'contact', 'cleanup']
    assert len({options['deadline'] for _, options in calls}) == 1
    assert result['diag']['contact_repair']['expansions'] <= 2000
    info = result['diag']['final_cleanup']; module = info['module']
    assert info['before_qubits'] == result['diag']['pruned_qubits'] - result['diag']['contact_repair']['qubits_saved']
    assert info['after_qubits'] == sum(map(len, result['embedding'].values()))
    assert info['qubits_saved'] == module['accepted_deletions'] == len(module['accepted_sequence'])
    assert 0 <= module['wall'] <= info['module_call_wall'] <= info['wall'] <= result['time']
    assert nx.utils.graphs_equal(source, before[0]) and nx.utils.graphs_equal(target, before[1])


def test_pilot_adds_exactly_one_fixed_arm_and_preserves_every_existing_config():
    pilot = load(ROOT / 'scripts/codex/pilot.py', '_cleanup_pilot')
    old = load(ROOT / 'results/codex/deletion-closure-integration-checks/reference/pilot.py', '_cleanup_old_pilot')
    control = 'native-search-joint1-contacts-spectral'
    variant = control + '-final-deletion'
    assert pilot.CONFIGS[variant] == dict(pilot.CONFIGS[control], final_cleanup='deletion')
    assert {key: value for key, value in pilot.CONFIGS.items() if key != variant} == old.CONFIGS
    assert 'final_cleanup' not in pilot.CONFIGS[control]
