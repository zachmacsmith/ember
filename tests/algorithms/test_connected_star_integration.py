"""Connected-policy adapter/scheduler contracts and one fixed Z12 native smoke.

Ordinary outcomes are controlled only where named. Connected queries, physical
certificates and shared accounting remain real. No test asserts corpus advantage.
Historical replays read immutable git6044e200 source, not a second constructor.
"""
from collections import Counter
from copy import deepcopy
import importlib.abc
import importlib.util
from pathlib import Path
import subprocess
import sys
from types import ModuleType, SimpleNamespace

import networkx as nx
import pytest

from ember_qc.algorithms.factored import contact_repair as cr
from ember_qc.algorithms.factored import connected_star_relocation as cs
from ember_qc.algorithms.factored import induced_star_relocation as sr
from ember_qc.algorithms.factored import singleton_relocation as singleton
from ember_qc.algorithms.factored import native


def valid(chains, source, target):
    """Independent full original-edge oracle; no implementation validator."""
    if set(chains) != set(source):
        return False
    occupied = set()
    for chain in chains.values():
        if not chain or len(chain) != len(set(chain)) or occupied.intersection(chain):
            return False
        if any(q not in target for q in chain):
            return False
        own, reached, todo = set(chain), {chain[0]}, [chain[0]]
        for q in todo:
            for p in target[q]:
                if p in own and p not in reached:
                    reached.add(p)
                    todo.append(p)
        if reached != own:
            return False
        occupied.update(chain)
    return all(any(target.has_edge(q, p) for q in chains[v] for p in chains[w])
               for v, w in source.edges)


def redundancy(chains, source, target):
    return sum(sum(target.has_edge(q, p) for q in chains[v] for p in chains[w]) - 1
               for v, w in source.edges)


def fixture(failure=False, isolate=False):
    source = nx.Graph([(3, 1), (1, 0), (0, 2), (2, 4)])
    target = nx.Graph([(5, 0), (0, 1), (1, 2), (2, 3), (3, 4), (4, 6)])
    if failure:
        target.add_edge(5, 1)
        chains = {0: [2, 3], 1: [0, 1], 2: [4], 3: [5], 4: [6]}
    else:
        target.add_edge(1, 3)
        chains = {0: [2], 1: [0, 1], 2: [3, 4], 3: [5], 4: [6]}
    if isolate:
        source.add_node('isolate')
        target.add_edges_from([(10, 11), (11, 12)])
        chains['isolate'] = [10, 11, 12]
    assert valid(chains, source, target)
    return chains, source, target


def ordinary_record(before, after, source, target, work):
    detail = cr._diagnostics()
    detail.update(expansions=work, stopped_by='searched')
    if after is not before:
        assert valid(after, source, target)
        detail.update(accepted=1, complete_proposals=1,
            qubits_saved=sum(map(len, before.values())) - sum(map(len, after.values())),
            member_growth=sum(len(after[v]) > len(before[v]) for v in source),
            contact_redundancy_gain=redundancy(after, source, target) - redundancy(before, source, target))
        detail['equal_size_moves'] = int(detail['qubits_saved'] == 0)
    return after, detail


def schedule(monkeypatch, groups, source, target, *, spend=0, change=None):
    calls = []
    monkeypatch.setattr(cr, '_groups', lambda embedding, ctx, sizes, limit: list(groups[:limit]))
    def ordinary(embedding, ctx, group, **kwargs):
        calls.append((tuple(group), kwargs['max_expansions']))
        result = change(embedding, group) if change else embedding
        return ordinary_record(embedding, result, source, target, min(spend, kwargs['max_expansions']))
    monkeypatch.setattr(cr, '_repair', ordinary)
    return calls


def polish(chains, source, target, **kwargs):
    options = dict(star_policy='connected', singleton_policy='legacy', max_passes=1,
        max_groups=8, group_sizes=(1, 2, 3, 4), group_policy='legacy',
        max_expansions=500000, group_expansions=50000, objective='qubits_contacts')
    options.update(kwargs)
    return cr.contact_polish(chains, source, target, **options)


def accounting(info):
    search = info['connected_star_search']
    assert search['policy'] == 'connected'
    assert 'star_search' not in info and 'singleton_search' not in info
    visits, attempts, maintenance = search['visits'], search['attempts'], search['maintenance']
    assert len(visits) == info['groups_tried'] == search['ordinary_groups_tried']
    assert sum(v['work'] for v in visits) == info['expansions']
    assert all(v['ordinary_work'] + v['proposal_work'] + v['refresh_work'] == v['work'] <= v['limit'] for v in visits)
    assert sum(v['proposal_work'] for v in visits) == sum(a['expansions'] for a in attempts)
    assert sum(v['refresh_work'] for v in visits) == sum(m['work'] for m in maintenance)
    assert sum(v['proposal_work'] for v in visits) == search['setup_work'] + search['query_work']
    assert sum(v['refresh_work'] for v in visits) == search['refresh_work']
    assert search['work'] == search['setup_work'] + search['query_work'] + search['refresh_work']
    assert info['expansions'] == sum(v['ordinary_work'] for v in visits) + search['work']
    assert search['work'] <= search['work_limit']
    assert all(a['policy'] == 'connected' and a['query_work'] == sum(a['stage_work'].values()) for a in attempts)
    assert search['accepted'] == sum(a['committed'] for a in attempts)
    for counter in ('qubits_saved', 'member_growth', 'contact_redundancy_gain'):
        assert search[counter] == sum(a[counter] for a in attempts if a['committed'])
    assert search['accepted'] == sum(t['operator'] == 'connected_star' for t in info['trajectory'])


def test_connected_commit_uses_one_factory_and_records_actual_growth(monkeypatch):
    chains, source, target = fixture()
    before = deepcopy(chains)
    calls = schedule(monkeypatch, [(0,)], source, target, spend=7)
    constructors = []
    real = cs.ConnectedStarSearch.__init__
    def construct(self, *args, **kwargs):
        constructors.append(1)
        real(self, *args, **kwargs)
    def forbidden(*args, **kwargs):
        pytest.fail('Connected policy invoked another search factory')
    monkeypatch.setattr(cs.ConnectedStarSearch, '__init__', construct)
    monkeypatch.setattr(sr.StarSearch, '__init__', forbidden)
    monkeypatch.setattr(singleton.SingletonSearch, '__init__', forbidden)
    output, info = polish(chains, source, target, max_groups=1)
    assert valid(output, source, target) and chains == before
    assert len(constructors) == len(calls) == info['groups_tried'] == 1
    assert len(output[0]) == 2 and len(chains[0]) == 1
    assert output[3] is chains[3] and output[4] is chains[4]
    assert info['accepted'] == info['qubits_saved'] == info['member_growth'] == 1
    assert info['trajectory'][0]['operator'] == 'connected_star'
    assert info['trajectory'][0]['member_growth'] == 1
    assert info['contact_redundancy_gain'] == redundancy(output, source, target) - redundancy(chains, source, target)
    assert info['expansions'] == 7 + info['connected_star_search']['work']
    accounting(info)


def test_connected_commit_retains_negative_redundancy_delta(monkeypatch):
    source, target = nx.star_graph(2), nx.complete_graph(5)
    chains = {0: [0], 1: [1, 2], 2: [3, 4]}
    schedule(monkeypatch, [(0,)], source, target)
    output, info = polish(chains, source, target)
    assert valid(output, source, target)
    assert info['qubits_saved'] == 2 and info['contact_redundancy_gain'] == -2
    assert info['trajectory'][0]['contact_redundancy_gain'] == -2
    accounting(info)


def test_once_per_center_each_pass_and_ordinary_commits_refresh_same_cache(monkeypatch):
    chains, source, target = fixture(failure=True, isolate=True)
    def shrink(incumbent, group):
        return {**incumbent, 'isolate': incumbent['isolate'][1:]} if group == ('isolate',) else incumbent
    calls = schedule(monkeypatch, [(0,), (0, 1), ('isolate',)], source, target, change=shrink)
    output, info = polish(chains, source, target, max_passes=2)
    search = info['connected_star_search']
    assert valid(output, source, target) and output['isolate'] == [12]
    assert len(calls) == info['groups_tried'] == 6
    assert len(search['attempts']) == 2 and all(a['center'] == 0 for a in search['attempts'])
    assert Counter(a['pass'] for a in search['attempts']) == {1: 1, 2: 1}
    assert search['cache_builds'] == 1 and search['cache_refreshes'] == 2
    assert [m['work'] for m in search['maintenance']] == [7, 5]
    assert search['accepted'] == 0 and info['accepted'] == 2
    assert all(t['operator'] == 'group' for t in info['trajectory'])
    accounting(info)


def test_equal_qubit_ordinary_acceptance_suppresses_connected_query(monkeypatch):
    source = nx.star_graph(2)
    target = nx.Graph([(0, 1), (0, 2), (1, 3), (0, 4), (4, 2), (4, 3)])
    chains = {0: [0, 1], 1: [2], 2: [3]}
    alternative = {**chains, 0: [0, 4]}
    assert redundancy(alternative, source, target) > redundancy(chains, source, target)
    schedule(monkeypatch, [(0,)], source, target, change=lambda *args: alternative)
    monkeypatch.setattr(cs.ConnectedStarSearch, 'propose', lambda *a, **k: pytest.fail('ordinary acceptance was ignored'))
    output, info = polish(chains, source, target)
    assert output == alternative and info['equal_size_moves'] == 1
    assert info['connected_star_search']['considerations'] == 0
    accounting(info)


def test_no_new_groups_for_an_all_singleton_incumbent(monkeypatch):
    source, target = nx.path_graph(3), nx.path_graph(4)
    chains = {v: [v] for v in source}
    monkeypatch.setattr(cs.ConnectedStarSearch, 'propose', lambda *a, **k: pytest.fail('unauthorized sweep'))
    output, info = polish(chains, source, target)
    assert output == chains and info['groups_tried'] == 0
    assert info['connected_star_search']['work'] == 0
    accounting(info)


def test_only_remaining_visit_and_global_allowance_is_available(monkeypatch):
    chains, source, target = fixture(failure=True)
    schedule(monkeypatch, [(0,), (1,)], source, target, spend=195)
    real, seen = cs.ConnectedStarSearch.propose, []
    def observe(self, incumbent, center, budget):
        before = budget.expansions
        result = real(self, incumbent, center, budget)
        seen.append((before, budget.limit, budget.expansions))
        return result
    monkeypatch.setattr(cs.ConnectedStarSearch, 'propose', observe)
    output, info = polish(chains, source, target, max_expansions=400, group_expansions=200, max_groups=2)
    assert output == chains and seen == [(195, 200, 200), (195, 200, 200)]
    assert info['connected_star_search']['work_limit'] == 20
    assert info['expansions'] == 400 and info['connected_star_search']['work'] == 10
    accounting(info)


def test_connected_query_has_no_hidden_singleton_2048_cap(monkeypatch):
    chains, source, target = fixture()
    schedule(monkeypatch, [(0,)], source, target)
    real = cs.ConnectedStarSearch.propose
    def accounted_prefix(self, incumbent, center, budget):
        # Force measured query work, without fabricating a successful proposal.
        prefix = cs._StageBudget(self, budget, 'query')
        assert prefix.limit is None
        for _ in range(2050):
            assert prefix.charge('integration_prefix')
        output, detail = real(self, incumbent, center, budget)
        detail['query_work'] += prefix.expansions
        detail['expansions'] += prefix.expansions
        detail['stage_work']['integration_prefix'] = prefix.expansions
        return output, detail
    monkeypatch.setattr(cs.ConnectedStarSearch, 'propose', accounted_prefix)
    output, info = polish(chains, source, target)
    assert valid(output, source, target)
    assert info['connected_star_search']['attempts'][0]['query_work'] > 2048
    accounting(info)


def test_deadline_after_certificate_discards_all_commit_counters(monkeypatch):
    chains, source, target = fixture()
    schedule(monkeypatch, [(0,)], source, target)
    clock = [100.]
    monkeypatch.setattr(cr.time, 'perf_counter', lambda: clock[0])
    real = cs.ConnectedStarSearch.propose
    def expire(self, incumbent, center, budget):
        answer = real(self, incumbent, center, budget)
        assert answer[0] is not None and answer[1]['member_growth'] == 1
        clock[0] = 102.
        return answer
    monkeypatch.setattr(cs.ConnectedStarSearch, 'propose', expire)
    output, info = polish(chains, source, target, deadline=101.)
    search = info['connected_star_search']
    assert output is chains and valid(output, source, target)
    assert info['trajectory'] == [] and info['stopped_by'] == 'deadline'
    assert info['accepted'] == info['qubits_saved'] == info['member_growth'] == info['contact_redundancy_gain'] == 0
    assert search['certified_proposals'] == search['proposed_member_growth'] == 1
    assert search['accepted'] == search['member_growth'] == 0
    assert search['attempts'][0]['commit_rejection'] == 'deadline'
    accounting(info)


def test_refresh_interruption_retains_the_already_valid_committed_embedding(monkeypatch):
    chains, source, target = fixture()
    schedule(monkeypatch, [(0,)], source, target)
    probe = cs.ConnectedStarSearch(cr._Context(source, target), 25000)
    replacement, detail = probe.propose(chains, 0, cr._Budget(50000, None))
    assert replacement is not None
    output, info = polish(chains, source, target, group_expansions=detail['expansions'])
    assert output != chains and valid(output, source, target)
    assert info['accepted'] == info['qubits_saved'] == info['member_growth'] == 1
    assert info['connected_star_search']['disabled_reason'].startswith('refresh_')
    assert info['connected_star_search']['last_refresh_work'] == 0
    assert info['expansions'] == detail['expansions']
    accounting(info)


def z12_incumbent():
    import dwave_networkx as dnx
    source, target = nx.star_graph(22), dnx.zephyr_graph(12)
    ctx = cr._Context(source, target)
    def boundary(chain):
        return {p for q in chain for p in target[q] if p not in chain}
    root = next(q for q in ctx.adj if len(target[q]) == ctx.max_degree)
    mate = next(q for q in ctx.adj[root] if len(boundary({root, q})) >= 22)
    center = {root, mate}
    center.add(next(q for q in sorted(boundary(center), key=ctx.rank.__getitem__)
                    if len(boundary(center | {q})) >= 22))
    sites = sorted(boundary(center), key=ctx.rank.__getitem__)[:22]
    chains = {0: sorted(center, key=ctx.rank.__getitem__), **{v: [q] for v, q in zip(range(1, 23), sites)}}
    assert valid(chains, source, target)
    return chains, source, target


def test_z12_above_delta_center_commits_a_23_member_block_in_one_visit(monkeypatch):
    chains, source, target = z12_incumbent()
    calls = schedule(monkeypatch, [(0,)], source, target)
    output, info = polish(chains, source, target, max_groups=1)
    assert valid(output, source, target) and len(source[0]) > 20
    assert len(calls) == info['groups_tried'] == 1 and calls[0][0] == (0,)
    assert len(info['trajectory'][0]['group']) == 23
    assert len(output[0]) == 2 and info['qubits_saved'] == 1
    assert info['contact_redundancy_gain'] == -1
    accounting(info)


def strip_times(value):
    if isinstance(value, dict):
        return {k: strip_times(v) for k, v in value.items() if not k.endswith('wall') and k != 'deadline_overrun'}
    if isinstance(value, list):
        return [strip_times(v) for v in value]
    return value


@pytest.fixture(scope='module')
def historical_contact():
    root = Path(__file__).resolve().parents[2]
    path = 'packages/ember-qc/src/ember_qc/algorithms/factored/contact_repair.py'
    source = subprocess.run(['git', 'show', '6044e200ff36c8585938e8113189d9c3200c8a4b:' + path],
        cwd=root, check=True, capture_output=True, text=True, timeout=10).stdout
    name = 'ember_qc.algorithms.factored._connected_integration_historical'
    module = ModuleType(name)
    module.__file__ = 'git:6044e200:' + path
    module.__package__ = 'ember_qc.algorithms.factored'
    sys.modules[name] = module
    exec(compile(source, module.__file__, 'exec'), module.__dict__)
    return module


@pytest.mark.parametrize('policy', ['off', 'matching'])
@pytest.mark.parametrize('group_policy', ['legacy', 'round_robin'])
@pytest.mark.parametrize('failure', [False, True])
def test_historical_off_and_matching_outputs_and_all_non_time_diagnostics_replay(historical_contact, policy, group_policy, failure):
    chains, source, target = fixture(failure=failure, isolate=True)
    options = dict(star_policy=policy, max_groups=8, max_passes=2, group_sizes=(1, 2, 3, 4),
        group_policy=group_policy, max_expansions=20000, group_expansions=2000,
        boundary_sites=16, objective='qubits_contacts', beam_width=1)
    old, expected = historical_contact.contact_polish(chains, source, target, **options)
    new, observed = cr.contact_polish(chains, source, target, **options)
    assert new == old and strip_times(observed) == strip_times(expected)
    assert 'connected_star_search' not in observed


@pytest.mark.parametrize('case', ['direct_combination', 'source_directed', 'source_multigraph', 'source_loop',
                                  'target_directed', 'target_multigraph', 'target_loop'])
def test_connected_contact_preconditions_apply_even_when_polishing_disabled(monkeypatch, case):
    chains, source, target = fixture()
    options = {}
    if case == 'direct_combination':
        options['singleton_policy'] = 'direct'
    elif case.startswith('source_'):
        if case.endswith('directed'):
            source = nx.DiGraph(source)
        elif case.endswith('multigraph'):
            source = nx.MultiGraph(source)
        else:
            source.add_edge(0, 0)
    else:
        if case.endswith('directed'):
            target = nx.DiGraph(target)
        elif case.endswith('multigraph'):
            target = nx.MultiGraph(target)
        else:
            target.add_edge(0, 0)
    monkeypatch.setattr(cs.ConnectedStarSearch, '__init__', lambda *a, **k: pytest.fail('invalid policy constructed search'))
    with pytest.raises(ValueError):
        polish(chains, source, target, max_passes=0, max_groups=0, **options)


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


def test_native_connected_option_forwards_once_with_original_labels_and_deadline(monkeypatch, inert_native):
    source, target = inert_native
    seen = []
    def contact(chains, src, tgt, **kwargs):
        seen.append(kwargs)
        assert set(src) == {0, 1, 2} and tgt is target
        return chains, {'inert': True}
    monkeypatch.setattr(cr, 'contact_polish', contact)
    result = native.native_embed(source, target, max_asks=1, polish_passes=1, polish_star_policy='connected')
    assert result['status'] == 'SUCCESS' and valid(result['embedding'], source, target)
    assert result['diag']['polish_star_policy'] == 'connected'
    assert len(seen) == 1 and seen[0]['star_policy'] == 'connected' and seen[0]['deadline'] is not None


@pytest.mark.parametrize('case', ['direct_combination', 'source_loop', 'source_directed', 'source_multigraph',
                                  'target_loop', 'target_directed', 'target_multigraph'])
def test_native_rejects_connected_contract_errors_before_disabled_polishing(monkeypatch, inert_native, case):
    source, target = inert_native
    options = {}
    if case == 'direct_combination':
        options['polish_singleton_policy'] = 'direct'
    else:
        graph = source if case.startswith('source') else target
        if case.endswith('loop'):
            graph.add_edge(next(iter(graph)), next(iter(graph)))
        elif case.endswith('directed'):
            graph = nx.DiGraph(graph)
        else:
            graph = nx.MultiGraph(graph)
        if case.startswith('source'):
            source = graph
        else:
            target = graph
    monkeypatch.setattr(native, 'TileGrid', lambda *a, **k: pytest.fail('invalid input reached constructor'))
    result = native.native_embed(source, target, polish_passes=0, polish_star_policy='connected', **options)
    assert result['status'] == 'ERROR'


def test_native_final_validator_rejects_corrupted_connected_result(monkeypatch, inert_native):
    source, target = inert_native
    monkeypatch.setattr(cr, 'contact_polish', lambda chains, *a, **k: ({0: chains[0]}, {}))
    result = native.native_embed(source, target, max_asks=1, polish_passes=1, polish_star_policy='connected')
    assert result['status'] == 'INVALID_OUTPUT' and not result['success']


def test_pilot_connected_method_changes_exactly_one_option():
    path = Path(__file__).resolve().parents[2] / 'scripts/codex/pilot.py'
    spec = importlib.util.spec_from_file_location('connected_integration_pilot', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    base = module.CONFIGS['native-search-joint1-contacts-spectral']
    actual = module.CONFIGS['native-search-joint1-contacts-spectral-connected-star']
    assert actual == {**base, 'polish_star_policy': 'connected'}
    assert actual.get('polish_singleton_policy', 'legacy') == 'legacy'


def test_one_fixed_native_spectral_z12_smoke_with_import_guard():
    """One actual correctness call, not a tuned input or quality comparison."""
    class Guard(importlib.abc.MetaPathFinder):
        def find_spec(self, fullname, path=None, target=None):
            if 'minorminer' in fullname.split('.')[0].lower() or fullname.split('.')[0].lower() == 'busclique':
                raise AssertionError('Prohibited embedding import: ' + fullname)
    assert not [n for n in sys.modules if 'minorminer' in n.split('.')[0].lower() or n.split('.')[0].lower() == 'busclique']
    guard = Guard()
    sys.meta_path.insert(0, guard)
    try:
        import dwave_networkx as dnx
        source = nx.gnp_random_graph(18, 3 / 17, seed=39001)
        source = nx.relabel_nodes(source, {v: ('node', v) if v % 2 else 'v' + str(v) for v in source})
        source.add_node(('explicit_isolate', 18))
        target = dnx.zephyr_graph(12)
        before = (set(source), set(map(frozenset, source.edges)), set(target), set(map(frozenset, target.edges)))
        result = native.native_embed(source, target, initialization='spectral', seed=0, max_asks=20,
            polish_passes=1, max_groups=8, polish_group_sizes=(1, 2, 3, 4), polish_expansions=8000,
            beam_width=1, polish_boundary_sites=16, polish_group_policy='round_robin',
            polish_objective='qubits_contacts', polish_star_policy='connected', timeout=30)
        assert result['status'] == 'SUCCESS', result
        assert valid(result['embedding'], source, target)
        assert len(result['embedding'][('explicit_isolate', 18)]) == 1
        assert before == (set(source), set(map(frozenset, source.edges)), set(target), set(map(frozenset, target.edges)))
        assert result['diag']['polish_star_policy'] == 'connected'
        info = result['diag']['contact_repair']
        assert info['groups_tried'] <= 8 and info['expansions'] <= 8000
        assert info['connected_star_search']['work_limit'] == 400
        accounting(info)
    finally:
        sys.meta_path.remove(guard)
