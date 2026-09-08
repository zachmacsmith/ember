"""Scheduler/adapter contracts and one fixed native correctness smoke.

These tests follow the frozen implementation specification. Adapter tests stub
construction except the explicitly named final pipeline smoke; no test asserts
an algorithm-quality gain. Only ordinary proposal outcomes are controlled in
scheduler tests; star queries, cache accounting and original-graph validation
remain real unless a test names the interruption or observation it injects.
"""
from collections import Counter
from copy import deepcopy
import importlib.util
from pathlib import Path
from types import SimpleNamespace

import networkx as nx
import pytest

from ember_qc.algorithms.factored import contact_repair as cr
from ember_qc.algorithms.factored import induced_star_relocation as sr
from ember_qc.algorithms.factored import native
from ember_qc.embedding_backend import is_valid_embedding


def fixture(blocked=False, isolate=False):
    if blocked:
        source = nx.Graph([('x', 'a'), ('a', 'c'), ('c', 'b'), ('b', 'y')])
        target = nx.path_graph(6)
        embedding = {'x': [0], 'a': [1], 'c': [2, 3], 'b': [4], 'y': [5]}
    else:
        source = nx.Graph([('c', 'a'), ('c', 'b')])
        target = nx.Graph([(0, 1), (0, 2), (1, 3)])
        embedding = {'c': [0, 1], 'a': [2], 'b': [3]}
    if isolate:
        source.add_node('isolate')
        target.add_edges_from([(10, 11), (11, 12)])
        embedding['isolate'] = [10, 11, 12]
    assert is_valid_embedding(embedding, source, target)
    return embedding, source, target


def redundancy(embedding, source, target):
    return sum(sum(target.has_edge(p, q) for p in embedding[u] for q in embedding[v]) - 1
               for u, v in source.edges)


def move_record(before, after, source, target, spent=0):
    info = cr._diagnostics()
    info['expansions'] = spent
    info['stopped_by'] = 'searched'
    if after is not before:
        assert is_valid_embedding(after, source, target)
        info['accepted'] = info['complete_proposals'] = 1
        info['qubits_saved'] = sum(map(len, before.values())) - sum(map(len, after.values()))
        info['contact_redundancy_gain'] = redundancy(after, source, target) - redundancy(before, source, target)
        info['equal_size_moves'] = int(info['qubits_saved'] == 0)
    return after, info


def schedule(monkeypatch, groups, source, target, spend=0, change=None):
    calls = []
    monkeypatch.setattr(cr, '_groups', lambda embedding, ctx, sizes, limit: list(groups[:limit]))

    def ordinary(embedding, ctx, group, **kwargs):
        calls.append((tuple(group), kwargs['max_expansions']))
        after = change(embedding, group) if change else embedding
        return move_record(embedding, after, source, target,
                           spent=min(spend, kwargs['max_expansions']))
    monkeypatch.setattr(cr, '_repair', ordinary)
    return calls


def polish(embedding, source, target, **kwargs):
    options = dict(star_policy='matching', singleton_policy='legacy',
                   max_passes=1, max_groups=8, group_sizes=(1, 2, 3, 4),
                   group_policy='legacy', max_expansions=500000,
                   group_expansions=50000, objective='qubits_contacts')
    options.update(kwargs)
    return cr.contact_polish(embedding, source, target, **options)


def assert_accounting(info):
    stars = info['star_search']
    visits, attempts, maintenance = stars['visits'], stars['attempts'], stars['maintenance']
    assert len(visits) == info['groups_tried'] == stars['ordinary_groups_tried']
    assert sum(v['work'] for v in visits) == info['expansions']
    assert all(v['ordinary_work'] + v['proposal_work'] + v['refresh_work'] == v['work']
               and v['work'] <= v['limit'] for v in visits)
    assert sum(v['proposal_work'] for v in visits) == sum(a['expansions'] for a in attempts)
    assert sum(v['refresh_work'] for v in visits) == sum(m['work'] for m in maintenance)
    assert sum(v['proposal_work'] for v in visits) == stars['setup_work'] + stars['query_work']
    assert sum(v['refresh_work'] for v in visits) == stars['refresh_work']
    assert stars['work'] == stars['setup_work'] + stars['query_work'] + stars['refresh_work']
    assert info['expansions'] == sum(v['ordinary_work'] for v in visits) + stars['work']
    assert stars['work'] <= stars['work_limit']
    assert all(a['query_work'] <= 2048 and a['query_work'] == sum(a['stage_work'].values())
               for a in attempts)
    assert stars['accepted'] == sum(a['committed'] for a in attempts)


def test_failed_ordinary_visit_attaches_star_without_an_extra_group(monkeypatch):
    embedding, source, target = fixture()
    snapshot = deepcopy(embedding)
    calls = schedule(monkeypatch, [('c',)], source, target, spend=7)
    output, info = polish(embedding, source, target, max_groups=1)
    assert is_valid_embedding(output, source, target)
    assert sum(map(len, output.values())) == 3
    assert embedding == snapshot and len(calls) == info['groups_tried'] == 1
    stars = info['star_search']
    assert stars['ordinary_groups_tried'] == 1
    assert stars['accepted'] == info['accepted'] == 1
    assert stars['qubits_saved'] == info['qubits_saved'] == 1
    assert info['expansions'] == 7 + stars['work']
    assert info['trajectory'][0]['operator'] == 'star'
    assert set(info['trajectory'][0]['group']) == {'c', 'a', 'b'}
    assert len(stars['attempts']) == 1
    assert_accounting(info)


def test_once_per_center_per_pass_and_ordinary_success_refreshes_cache(monkeypatch):
    embedding, source, target = fixture(blocked=True, isolate=True)

    def change(incumbent, group):
        if group == ('isolate',) and len(incumbent['isolate']) > 1:
            return {**incumbent, 'isolate': incumbent['isolate'][1:]}
        return incumbent
    calls = schedule(monkeypatch, [('c',), ('c', 'a'), ('isolate',)], source, target, change=change)
    observed = []
    original_refresh = sr.StarSearch.refresh

    def refreshed(self, old, new, group, budget):
        had_cache = self.cache is not None
        outcome = original_refresh(self, old, new, group, budget)
        observed.append((tuple(group), had_cache, outcome, self.info['last_refresh_work']))
        return outcome
    monkeypatch.setattr(sr.StarSearch, 'refresh', refreshed)
    output, info = polish(embedding, source, target, max_passes=2)
    assert is_valid_embedding(output, source, target) and output['isolate'] == [12]
    assert len(calls) == info['groups_tried'] == 6
    stars = info['star_search']
    attempts = stars['attempts']
    assert len(attempts) == 2
    assert all(attempt['center'] == 'c' for attempt in attempts)
    assert set(Counter(attempt['pass'] for attempt in attempts).values()) == {1}
    assert len({attempt['pass'] for attempt in attempts}) == 2
    assert observed == [(('isolate',), True, True, 7), (('isolate',), True, True, 5)]
    assert stars['cache_builds'] == 1 and stars['cache_refreshes'] == 2
    assert stars['accepted'] == 0 and info['accepted'] == 2
    assert all(entry['operator'] == 'group' for entry in info['trajectory'])
    assert info['expansions'] == stars['work']  # mocked ordinary search consumed zero
    assert_accounting(info)


def test_equal_qubit_ordinary_success_suppresses_star_proposal(monkeypatch):
    embedding, source, target = fixture()
    target.add_edges_from([(0, 4), (4, 2), (4, 3)])
    alternative = {**embedding, 'c': [0, 4]}
    assert redundancy(alternative, source, target) > redundancy(embedding, source, target)
    schedule(monkeypatch, [('c',)], source, target,
             change=lambda incumbent, group: alternative)

    def forbidden(*args, **kwargs):
        raise AssertionError('ordinary acceptance must suppress attached proposal')
    monkeypatch.setattr(sr.StarSearch, 'propose', forbidden)
    output, info = polish(embedding, source, target)
    assert output == alternative and info['accepted'] == 1 and info['qubits_saved'] == 0
    assert info['equal_size_moves'] == 1
    assert info['star_search']['queries'] == info['star_search']['accepted'] == 0
    assert info['trajectory'][0]['operator'] == 'group'
    assert_accounting(info)


def test_all_singletons_do_not_create_a_new_sweep(monkeypatch):
    source, target = nx.path_graph(3), nx.path_graph(4)
    embedding = {v: [v] for v in source}
    monkeypatch.setattr(sr.StarSearch, 'propose',
                        lambda *a, **k: pytest.fail('no zero-excess queue is authorized'))
    output, info = polish(embedding, source, target)
    assert output == embedding and info['groups_tried'] == 0
    assert info['star_search']['work'] == 0


def test_query_receives_only_remaining_active_and_global_work(monkeypatch):
    embedding, source, target = fixture(blocked=True)
    calls = schedule(monkeypatch, [('c',), ('a',)], source, target, spend=195)
    observed = []
    original = sr.StarSearch.propose

    def propose(self, incumbent, center, budget):
        before, limit = budget.expansions, budget.limit
        result = original(self, incumbent, center, budget)
        observed.append((before, limit, budget.expansions))
        return result
    monkeypatch.setattr(sr.StarSearch, 'propose', propose)
    output, info = polish(embedding, source, target, max_expansions=400,
                          group_expansions=200, max_groups=2)
    assert output == embedding and len(calls) == 2
    assert observed == [(195, 200, 200), (195, 200, 200)]
    stars = info['star_search']
    assert stars['work_limit'] == 20 and stars['work'] == 10
    assert info['expansions'] == 390 + stars['work'] == 400
    assert stars['visit_work_peak'] == 200
    assert_accounting(info)


def test_auxiliary_ceiling_is_shared_across_queries(monkeypatch):
    embedding, source, target = fixture(blocked=True)
    schedule(monkeypatch, [('c',), ('a',)], source, target)
    output, info = polish(embedding, source, target, max_expansions=400)
    assert output == embedding
    assert info['star_search']['work_limit'] == 20
    assert info['expansions'] == info['star_search']['work'] == 20
    assert info['groups_tried'] == 2
    assert_accounting(info)


def test_deadline_after_certification_discards_proposal_before_commit(monkeypatch):
    embedding, source, target = fixture()
    schedule(monkeypatch, [('c',)], source, target)
    clock = [100.0]
    monkeypatch.setattr(cr.time, 'perf_counter', lambda: clock[0])
    original = sr.StarSearch.propose

    def late(self, incumbent, center, budget):
        result = original(self, incumbent, center, budget)
        assert result[0] is not None
        clock[0] = 102.0
        return result
    monkeypatch.setattr(sr.StarSearch, 'propose', late)
    output, info = polish(embedding, source, target, deadline=101.0)
    assert output == embedding and is_valid_embedding(output, source, target)
    assert info['accepted'] == 0 and info['trajectory'] == []
    assert info['stopped_by'] == 'deadline'
    assert info['star_search']['certified_proposals'] == 1
    assert info['star_search']['accepted'] == 0
    assert info['star_search']['attempts'][0]['commit_rejection'] == 'deadline'
    assert not info['star_search']['attempts'][0]['committed']
    assert_accounting(info)


def test_incomplete_refresh_keeps_the_accepted_embedding(monkeypatch):
    embedding, source, target = fixture()
    schedule(monkeypatch, [('c',)], source, target)
    # Measure only this tiny core fixture's exact charge count, then make that
    # the active visit limit. The real query finishes on its final unit; real
    # maintenance has no remaining unit and must preserve the accepted result.
    probe = sr.StarSearch(cr._Context(source, target), 25000)
    replacement, probe_info = probe.propose(embedding, 'c', cr._Budget(50000, None))
    assert replacement is not None
    limit = probe_info['expansions']
    output, info = polish(embedding, source, target, group_expansions=limit)
    assert output != embedding and is_valid_embedding(output, source, target)
    assert info['accepted'] == 1 and info['qubits_saved'] == 1
    assert info['star_search']['disabled_reason'].startswith('refresh_')
    assert info['star_search']['last_refresh_work'] == 0
    assert info['expansions'] == limit
    assert_accounting(info)


def strip_times(value):
    if isinstance(value, dict):
        return {key: strip_times(item) for key, item in value.items()
                if not key.endswith('wall') and key != 'deadline_overrun'}
    if isinstance(value, list):
        return [strip_times(item) for item in value]
    return value


def test_default_off_replays_existing_contact_path_exactly():
    embedding, source, target = fixture()
    options = dict(max_groups=4, max_passes=2, group_sizes=(1, 2, 3, 4),
                   group_policy='round_robin', boundary_sites=16, objective='qubits_contacts')
    default, first = cr.contact_polish(embedding, source, target, **options)
    off, second = cr.contact_polish(embedding, source, target, star_policy='off', **options)
    assert default == off and strip_times(first) == strip_times(second)
    assert 'star_search' not in first and 'star_search' not in second


@pytest.mark.parametrize('policy', ['unknown', None, True])
def test_unknown_contact_star_policy_rejected(policy):
    embedding, source, target = fixture()
    with pytest.raises(ValueError):
        polish(embedding, source, target, star_policy=policy)


def test_star_and_direct_singleton_policies_are_mutually_exclusive():
    embedding, source, target = fixture()
    with pytest.raises(ValueError):
        polish(embedding, source, target, singleton_policy='direct')


@pytest.mark.parametrize('case', ['source_directed', 'target_multigraph', 'target_loop'])
def test_matching_requires_original_simple_undirected_loopless_graphs(case):
    embedding, source, target = fixture()
    if case == 'source_directed':
        source = nx.DiGraph(source)
    elif case == 'target_multigraph':
        target = nx.MultiGraph(target)
    else:
        target.add_edge(0, 0)
    with pytest.raises(ValueError):
        polish(embedding, source, target)


def test_matching_preserves_mixed_labels_isolates_and_original_graphs(monkeypatch):
    embedding, source, target = fixture(isolate=True)
    mapping = {'c': 9, 'a': 'a', 'b': ('leaf', 2), 'isolate': ('isolated',)}
    source = nx.relabel_nodes(source, mapping)
    embedding = {mapping[v]: list(chain) for v, chain in embedding.items()}
    saved = deepcopy(embedding)
    original_edges = set(map(frozenset, target.edges))
    schedule(monkeypatch, [(9,)], source, target)
    output, info = polish(embedding, source, target)
    assert is_valid_embedding(output, source, target)
    assert set(output) == set(source) and output[('isolated',)] == [10, 11, 12]
    assert embedding == saved and set(map(frozenset, target.edges)) == original_edges
    assert info['qubits_saved'] == 1


def test_actual_z12_matching_attaches_to_one_failed_visit(monkeypatch):
    import dwave_networkx as dnx
    source = nx.Graph([('x', 'a'), ('a', 'c'), ('c', 'b'), ('b', 'y')])
    target = dnx.zephyr_graph(12, 4, coordinates=True)
    embedding = {'x': [(0, 0, 0, 0, 0)],
                 'a': [(0, 0, 0, 0, 1), (0, 0, 0, 0, 2)],
                 'c': [(1, 5, 0, 0, 0), (1, 5, 0, 0, 1)],
                 'b': [(0, 3, 0, 0, 2), (0, 3, 0, 0, 1)], 'y': [(0, 3, 0, 0, 0)]}
    schedule(monkeypatch, [('c',)], source, target)
    output, info = polish(embedding, source, target, max_groups=1)
    assert is_valid_embedding(output, source, target)
    assert sum(map(len, output.values())) == 5
    assert info['groups_tried'] == info['star_search']['ordinary_groups_tried'] == 1
    assert info['expansions'] == info['star_search']['work'] == 720
    assert_accounting(info)


def test_selected_star_can_exceed_ordinary_group_size_limit(monkeypatch):
    source = nx.star_graph(5)
    embedding = {0: [0, 1], **{v: [v + 1] for v in range(1, 6)}}
    target = nx.Graph([(0, 1), (0, 2), (0, 3), (1, 4), (1, 5), (1, 6)])
    target.add_edges_from((10, q) for q in range(7))
    calls = schedule(monkeypatch, [(0,)], source, target)
    output, info = polish(embedding, source, target)
    assert is_valid_embedding(output, source, target)
    assert calls[0][0] == (0,) and info['star_search']['visits'][0]['group'] == [0]
    assert len(info['trajectory'][0]['group']) == 6
    assert info['qubits_saved'] == 1
    assert_accounting(info)


@pytest.fixture
def inert_native(monkeypatch):
    import dwave_networkx as dnx
    source = nx.Graph([('left', ('right', 2))])
    source.add_node(99)
    target = nx.path_graph(8)
    target.graph.update(family='zephyr', labels='int')
    monkeypatch.setattr(dnx, 'zephyr_layout', lambda graph: {})
    monkeypatch.setattr(native, 'TileGrid', lambda *a, **k: SimpleNamespace(stride=2, wire_map={'inert': {}}))
    monkeypatch.setattr(native.plane, 'arrange', lambda *a, **k: ({}, ({}, {}), {}))
    monkeypatch.setattr(native, 'wire_seeds_exact', lambda *a, **k: ({0: [0], 1: [1]}, {}))
    monkeypatch.setattr(native, 'complete_seeds', lambda grid, chains, *a, **k: (chains, {}))
    monkeypatch.setattr(native, 'spur_prune', lambda chains, *a, **k: chains)
    return source, target


def test_native_forwards_policy_and_preserves_labels_without_constructor(monkeypatch, inert_native):
    source, target = inert_native
    observed = []

    def contact(embedding, src, tgt, **kwargs):
        observed.append(kwargs)
        assert set(src) == {0, 1, 2} and tgt is target
        return embedding, {'fixture': 'policy forwarding only'}
    monkeypatch.setattr(cr, 'contact_polish', contact)
    result = native.native_embed(source, target, max_asks=1, polish_passes=1,
                                 polish_star_policy='matching')
    assert result['status'] == 'SUCCESS', result
    assert is_valid_embedding(result['embedding'], source, target)
    assert set(result['embedding']) == set(source)
    assert observed[0]['star_policy'] == 'matching'
    assert result['diag']['polish_star_policy'] == 'matching'


def test_native_final_validator_rejects_corrupted_polish_output(monkeypatch, inert_native):
    source, target = inert_native
    monkeypatch.setattr(cr, 'contact_polish',
                        lambda embedding, *a, **k: ({0: embedding[0], 1: embedding[1]}, {}))
    result = native.native_embed(source, target, max_asks=1, polish_passes=1,
                                 polish_star_policy='matching')
    assert result['status'] == 'INVALID_OUTPUT' and not result['success']


def test_native_off_default_preserves_existing_adapter_arguments(monkeypatch, inert_native):
    source, target = inert_native
    observed = []

    def contact(embedding, *args, **kwargs):
        observed.append(kwargs)
        return embedding, {'fixture': 'off adapter'}
    monkeypatch.setattr(cr, 'contact_polish', contact)
    first = native.native_embed(source, target, max_asks=1, polish_passes=1)
    second = native.native_embed(source, target, max_asks=1, polish_passes=1, polish_star_policy='off')
    assert first['status'] == second['status'] == 'SUCCESS'
    assert first['embedding'] == second['embedding']
    assert strip_times(first['diag']) == strip_times(second['diag'])
    assert all('star_policy' not in kwargs for kwargs in observed)
    assert 'polish_star_policy' not in first['diag'] and 'polish_star_policy' not in second['diag']


def test_native_matching_rejects_target_loops_before_constructor(monkeypatch, inert_native):
    source, target = inert_native
    target.add_edge(0, 0)
    monkeypatch.setattr(native.plane, 'arrange', lambda *a, **k: pytest.fail('invalid target reached constructor'))
    result = native.native_embed(source, target, polish_star_policy='matching', polish_passes=0)
    assert result['status'] == 'ERROR'


@pytest.mark.parametrize('options', [dict(polish_star_policy='unknown'),
                                    dict(polish_star_policy='matching', polish_singleton_policy='direct')])
def test_native_policy_errors_precede_construction(monkeypatch, inert_native, options):
    source, target = inert_native
    monkeypatch.setattr(native.plane, 'arrange', lambda *a, **k: pytest.fail('invalid policy reached construction'))
    result = native.native_embed(source, target, polish_passes=0, **options)
    assert result['status'] == 'ERROR'


def test_pilot_method_is_one_fixed_extension_of_current_candidate():
    path = Path(__file__).resolve().parents[2] / 'scripts/codex/pilot.py'
    spec = importlib.util.spec_from_file_location('star_integration_pilot_config', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    base = module.CONFIGS['native-search-joint1-contacts-spectral']
    candidate = module.CONFIGS['native-search-joint1-contacts-spectral-stars']
    assert candidate == {**base, 'polish_star_policy': 'matching'}
    assert candidate.get('polish_singleton_policy', 'legacy') == 'legacy'


def test_one_fixed_native_pipeline_smoke_with_mixed_labels_and_isolate():
    """One prespecified correctness call; no gain assertion or parameter search."""
    import dwave_networkx as dnx
    source = nx.gnp_random_graph(24, 3 / 23, seed=37001)
    labels = {v: ('vertex', v) if v % 3 == 0 else f'node_{v}' if v % 3 == 1 else 1000 + v
              for v in source}
    source = nx.relabel_nodes(source, labels)
    source.add_node(('explicit_isolate', 24))
    target = dnx.zephyr_graph(3)
    original_source = set(source), set(map(frozenset, source.edges))
    original_target = set(target), set(map(frozenset, target.edges))
    result = native.native_embed(
        source, target, initialization='spectral', seed=0, max_asks=40,
        polish_passes=1, max_groups=16, polish_group_sizes=(1, 2, 3, 4),
        polish_expansions=8000, beam_width=1, polish_boundary_sites=16,
        polish_group_policy='round_robin', polish_objective='qubits_contacts',
        polish_star_policy='matching', timeout=30)
    assert result['status'] == 'SUCCESS', result
    assert is_valid_embedding(result['embedding'], source, target)
    assert set(result['embedding']) == set(source)
    assert len(result['embedding'][('explicit_isolate', 24)]) == 1
    assert (set(source), set(map(frozenset, source.edges))) == original_source
    assert (set(target), set(map(frozenset, target.edges))) == original_target
    assert result['diag']['polish_star_policy'] == 'matching'
    assert result['diag'].get('deadline_overrun', 0) == 0
    repair = result['diag']['contact_repair']
    assert repair['groups_tried'] <= 16 and repair['expansions'] <= 8000
    assert repair['star_search']['work_limit'] == 400
    assert repair['star_search']['work'] <= 400
    assert_accounting(repair)
