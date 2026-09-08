"""Original-graph oracles for bounded, current-owner singleton relocation."""
from copy import deepcopy

import networkx as nx
import pytest

from ember_qc.algorithms.factored import contact_repair as cr
from ember_qc.algorithms.factored import singleton_relocation as sr


def validate(embedding, source, target):
    """Independent full certificate: no use of proposer masks or owner cache."""
    assert set(embedding) == set(source)
    occupied = set()
    for chain in embedding.values():
        assert chain and len(chain) == len(set(chain))
        assert set(chain) <= set(target)
        assert not occupied.intersection(chain)
        assert nx.is_connected(target.subgraph(chain))
        occupied.update(chain)
    for v, w in source.edges:
        assert any(target.has_edge(p, q) for p in embedding[v] for q in embedding[w])


def redundancy(embedding, source, target):
    return sum(sum(target.has_edge(p, q) for p in embedding[v] for q in embedding[w]) - 1
               for v, w in source.edges)


def unlock_fixture():
    source = nx.Graph([('x', 'a'), ('a', 'v'), ('v', 'b')])
    target = nx.Graph([(0, 1), (1, 6), (0, 2), (2, 3), (0, 5), (1, 5), (3, 5)])
    embedding = {'x': [6], 'a': [0, 1], 'v': [2], 'b': [3]}
    return embedding, source, target


def polish(embedding, source, target, **kwargs):
    options = dict(singleton_policy='direct', group_sizes=(1,), max_groups=64,
                   max_passes=4, max_expansions=10000, group_expansions=1000,
                   objective='qubits_contacts', group_policy='round_robin',
                   boundary_sites=16, beam_width=1)
    options.update(kwargs)
    return cr.contact_polish(embedding, source, target, **options)


def cached(embedding, source, target):
    validate(embedding, source, target)
    ctx = cr._Context(source, target)
    cache = sr.build_singleton_cache(embedding, ctx, cr._Budget(10000, None))
    assert cache is not None
    return ctx, cache


def test_zero_excess_relocation_unlocks_later_qubit_saving():
    embedding, source, target = unlock_fixture()
    snapshot = deepcopy(embedding)
    legacy, legacy_info = polish(embedding, source, target, singleton_policy='legacy')
    output, info = polish(embedding, source, target)
    assert legacy == embedding and legacy_info['accepted'] == 0
    assert 'singleton_search' not in legacy_info
    assert output == {'x': [6], 'a': [1], 'v': [5], 'b': [3]}
    validate(output, source, target)
    assert info['qubits_saved'] == 1 and info['equal_size_moves'] == 1
    assert [(m['group'], m['qubits_saved'], m['contact_redundancy_gain'])
            for m in info['trajectory']] == [(['v'], 0, 1), (['a'], 1, -1)]
    assert info['singleton_search']['cache_refreshes'] == 2
    assert embedding == snapshot


def test_full_non_time_legacy_regression_from_pre_edit_reference():
    # Frozen before this revision, using the declared unlock fixture/settings.
    embedding, source, target = unlock_fixture()
    output, info = polish(embedding, source, target, singleton_policy='legacy')
    info.pop('wall')
    assert output == embedding
    assert info == {
        'accepted': 0, 'qubits_saved': 0, 'member_growth': 0, 'expansions': 9,
        'region_size': 0, 'tree_attempts': 3, 'beam_expansions': 1, 'beam_pruned': 0,
        'unreachable_contacts': 0, 'complete_proposals': 1, 'orders_tried': 1,
        'boundary_sites_added': 0, 'boundary_expansions': 2, 'equal_size_moves': 0,
        'contact_redundancy_gain': 0, 'tree_search': {}, 'stopped_by': 'no_improvement',
        'groups_tried': 1, 'passes': 1, 'trajectory': [], 'max_region_size': 3}


def test_common_site_outside_old_region_and_full_redundancy_ranking():
    source = nx.Graph([('v', 'w')])
    target = nx.Graph([(10, 11), (11, 100), (100, 101), (100, 0), (100, 1), (101, 1)])
    embedding = {'v': [10, 11], 'w': [100, 101]}
    ctx, cache = cached(embedding, source, target)
    region = cr._region(ctx, embedding, {'v'}, 0, 512, cr._Budget(1000, None))
    site, info = sr.direct_singleton(embedding, ctx, 'v', cache, cr._Budget(1000, None))
    assert site == 1 and site not in region
    assert info['contact_redundancy_gain'] == 1 and info['complete']
    validate({**embedding, 'v': [site]}, source, target)


def test_truncated_enumeration_returns_only_a_fully_certified_site():
    source = nx.Graph([('v', 'w')])
    target = nx.Graph([(10, 11), (11, 100), (100, 101), (100, 0), (100, 1), (101, 1)])
    embedding = {'v': [10, 11], 'w': [100, 101]}
    ctx, cache = cached(embedding, source, target)
    budget = cr._Budget(5, None)
    site, info = sr.direct_singleton(embedding, ctx, 'v', cache, budget)
    assert site == 0 and not info['complete'] and info['reason'] == 'work_limit'
    assert budget.expansions == 5
    validate({**embedding, 'v': [site]}, source, target)


def test_fixed_scan_limit_bounds_large_boundary_without_hiding_cache_cost():
    source = nx.Graph([('v', 'w')])
    target = nx.Graph([(0, 1), (1, 1000)])
    target.add_edges_from((p, p + 1) for p in range(1000, 1399))
    target.add_edges_from((p, p + 4000) for p in range(1000, 1400))
    embedding = {'v': [0, 1], 'w': list(range(1000, 1400))}
    validate(embedding, source, target)
    search = sr.SingletonSearch(cr._Context(source, target), 1000, 1)
    budget = cr._Budget(10000, None)
    site, info = search.propose(embedding, 'v', budget, 'qubits_contacts')
    assert info['reason'] == 'scan_limit' and not info['complete']
    assert search.info['scan_work'] == 256 and search.info['setup_work'] == 404
    assert budget.expansions == search.info['work'] == 660
    validate({**embedding, 'v': [site]}, source, target)


def test_shrinking_long_chain_may_reduce_redundancy_below_singleton_bound():
    source = nx.Graph([('v', 'w')])
    target = nx.Graph([(0, 1), (10, 11), (0, 10), (0, 11), (1, 10), (1, 11)])
    embedding = {'v': [0, 1], 'w': [10, 11]}
    ctx, cache = cached(embedding, source, target)
    site, info = sr.direct_singleton(embedding, ctx, 'v', cache, cr._Budget(1000, None))
    assert info['old_redundancy'] > ctx.max_degree - 1
    assert site == 0 and info['qubits_saved'] == 1
    assert info['contact_redundancy_gain'] == -2
    output = {**embedding, 'v': [site]}
    validate(output, source, target)
    assert redundancy(output, source, target) - redundancy(embedding, source, target) == -2


def test_degree_bound_does_not_rely_on_loose_chain_lower_bound():
    # Source degree three cannot fit a target of maximum degree two. The valid
    # incumbent precondition is deliberately unnecessary for this exact skip.
    source, target = nx.star_graph(3), nx.path_graph(4)
    ctx = cr._Context(source, target)
    embedding = {v: [v] for v in source}
    cache = sr.build_singleton_cache(embedding, ctx, cr._Budget(100, None))
    budget = cr._Budget(100, None)
    site, info = sr.direct_singleton(embedding, ctx, 0, cache, budget)
    assert ctx.lower_bound(0) == 1
    assert site is None and info['reason'] == 'degree_bound' and budget.expansions == 0


def test_all_singleton_neighbors_exact_skip_and_isolate_shortening():
    embedding = {0: [0], 1: [1]}
    source, target = nx.path_graph(2), nx.complete_graph(3)
    ctx, cache = cached(embedding, source, target)
    site, info = sr.direct_singleton(embedding, ctx, 0, cache, cr._Budget(100, None))
    assert site is None and info['reason'] == 'singleton_neighbors'
    source, target = nx.empty_graph(1), nx.path_graph(3)
    embedding = {0: [2, 1, 0]}
    ctx, cache = cached(embedding, source, target)
    site, info = sr.direct_singleton(embedding, ctx, 0, cache, cr._Budget(100, None))
    assert site == 0 and info['qubits_saved'] == 2 and info['contact_redundancy_gain'] == 0


def test_refresh_transfers_ownership_then_supports_next_valid_singleton():
    source = nx.path_graph(['a', 'b', 'c'])
    target = nx.Graph([(0, 1), (1, 2), (2, 3), (3, 4), (0, 5), (4, 5)])
    old = {'a': [0, 1], 'b': [2, 3], 'c': [4]}
    current = {'a': [0], 'b': [1, 2, 3], 'c': [4]}
    ctx, cache = cached(old, source, target)
    validate(current, source, target)
    assert sr.refresh_singleton_cache(cache, old, current, ('a', 'b'), ctx, cr._Budget(8, None))
    assert cache.owner[1] == 'b' and cache.embedding is current and cache.valid
    assert cache.volume['b'] == sum(target.degree(q) for q in current['b'])
    site, info = sr.direct_singleton(current, ctx, 'b', cache, cr._Budget(100, None))
    assert site == 5 and info['qubits_saved'] == 2
    validate({**current, 'b': [site]}, source, target)


@pytest.mark.parametrize('limit', [0, 1, 3, 6])
def test_partial_refresh_invalidates_cache_and_preserves_embeddings(limit):
    embedding, source, target = unlock_fixture()
    ctx, cache = cached(embedding, source, target)
    current = {**embedding, 'v': [5], 'a': [1]}
    snapshot = deepcopy((embedding, current))
    budget = cr._Budget(limit, None)
    success = sr.refresh_singleton_cache(cache, embedding, current, ('a', 'v'), ctx, budget)
    assert success == (limit >= 5)
    assert cache.valid == success and budget.expansions <= limit
    assert (embedding, current) == snapshot
    if not success:
        with pytest.raises(ValueError, match='stale'):
            sr.direct_singleton(current, ctx, 'v', cache, cr._Budget(100, None))


def test_equal_copy_is_not_the_cached_incumbent():
    embedding, source, target = unlock_fixture()
    ctx, cache = cached(embedding, source, target)
    with pytest.raises(ValueError, match='stale'):
        sr.direct_singleton(deepcopy(embedding), ctx, 'v', cache, cr._Budget(100, None))


@pytest.mark.parametrize('exhaust_group', [False, True])
def test_accepted_joint_move_refreshes_or_disables_cache_before_next_visit(
        monkeypatch, exhaust_group):
    source = nx.path_graph(['a', 'b', 'c'])
    target = nx.Graph([(0, 1), (1, 2), (2, 3), (3, 4), (4, 6),
                       (1, 5), (5, 6), (0, 7), (6, 7)])
    embedding = {'a': [0, 1], 'b': [2, 3, 4], 'c': [6]}
    transferred = {'a': [0], 'b': [1, 5], 'c': [6]}
    validate(embedding, source, target)
    validate(transferred, source, target)
    original = cr._repair
    recorded = []

    def prescribed_groups(*args):
        # Start with a zero-size-change visit solely to establish the cache;
        # exercise the cache dependency, not the ordinary group scheduler.
        return [('c',), ('a', 'b'), ('b',)]

    def reconstruct(current, ctx, group, **kwargs):
        if group == ('a', 'b'):
            assert current == embedding
            move = cr._diagnostics()
            move.update(accepted=1, qubits_saved=2,
                        expansions=kwargs['max_expansions'] if exhaust_group else 1)
            recorded.append(group)
            return transferred, move
        return original(current, ctx, group, **kwargs)

    monkeypatch.setattr(cr, '_groups', prescribed_groups)
    monkeypatch.setattr(cr, '_repair', reconstruct)
    output, info = polish(embedding, source, target, group_policy='legacy', max_passes=1)
    assert recorded == [('a', 'b')]
    validate(output, source, target)
    direct = info['singleton_search']
    if exhaust_group:
        assert direct['disabled_reason'] == 'refresh_work_limit'
        assert direct['cache_refreshes'] == 0
    else:
        assert direct['cache_refreshes'] == 2 and output['b'] == [7]
        assert info['trajectory'][-1]['operator'] == 'singleton'


def test_extra_visits_interleave_and_share_original_group_cap(monkeypatch):
    embedding, source, target = unlock_fixture()
    # Repeated ordinary groups deliberately isolate scheduling from proposal
    # selection. None of these groups can improve before v's extra relocation.
    monkeypatch.setattr(cr, '_groups', lambda *args: [('a',)] * min(20, args[-1]))
    seen = []
    original = cr._repair

    def counted(current, ctx, group, **kwargs):
        seen.append(group)
        return original(current, ctx, group, **kwargs)

    monkeypatch.setattr(cr, '_repair', counted)
    output, info = polish(embedding, source, target, group_policy='legacy',
                          max_passes=1, max_groups=16)
    validate(output, source, target)
    assert len(seen) == 15 and output['v'] == [5]
    assert info['groups_tried'] == 16 and info['stopped_by'] == 'group_limit'
    assert info['singleton_search']['extra_visits'] == 1
    assert info['singleton_search']['ordinary_groups_tried'] == 15
    assert info['singleton_search']['ordinary_groups_displaced'] == 1


def test_no_singleton_does_not_remove_three_to_two_reconstruction(monkeypatch):
    source = nx.path_graph(['a', 'v', 'b'])
    target = nx.Graph([(0, 10), (10, 11), (11, 12), (12, 1),
                       (0, 20), (20, 21), (21, 1), (10, 20), (12, 21)])
    embedding = {'a': [0], 'v': [10, 11, 12], 'b': [1]}
    seen = []
    original = cr._repair

    def checked(*args, **kwargs):
        seen.append((args[2], kwargs['max_expansions']))
        return original(*args, **kwargs)

    monkeypatch.setattr(cr, '_repair', checked)
    output, info = polish(embedding, source, target, objective='qubits')
    validate(output, source, target)
    assert len(output['v']) == 2 and info['qubits_saved'] == 1
    assert seen and seen[0][0] == ('v',) and 0 < seen[0][1] < 1000
    assert info['singleton_search']['accepted'] == 0


@pytest.mark.parametrize('max_expansions,group_expansions', [
    (0, 100), (19, 100), (100, 0), (100, 5), (200, 20), (1000, 30), (10000, 1000)])
def test_all_auxiliary_work_shares_original_group_and_global_caps(
        monkeypatch, max_expansions, group_expansions):
    embedding, source, target = unlock_fixture()
    original = cr._repair
    ordinary_work = []

    def measured(*args, **kwargs):
        output, info = original(*args, **kwargs)
        ordinary_work.append(info['expansions'])
        return output, info

    monkeypatch.setattr(cr, '_repair', measured)
    output, info = polish(embedding, source, target, max_expansions=max_expansions,
                          group_expansions=group_expansions)
    validate(output, source, target)
    assert info['expansions'] <= max_expansions and info['groups_tried'] <= 64
    if 'singleton_search' in info:
        direct = info['singleton_search']
        assert direct['work'] <= max_expansions // 20
        assert direct['visit_work_peak'] <= group_expansions
        assert direct['work'] == sum(direct[k] for k in (
            'setup_work', 'refresh_work', 'queue_work', 'scan_work'))
        assert info['expansions'] == sum(ordinary_work) + direct['work']
        assert direct['extra_visits'] <= direct['extra_slots'] <= 64 // 16


def test_no_setup_without_passes_or_enabled_singletons():
    embedding, source, target = unlock_fixture()
    output, info = polish(embedding, source, target, max_passes=0)
    assert output is embedding and info['singleton_search']['work'] == 0
    output, info = polish(embedding, source, target, group_sizes=(2,))
    assert 'singleton_search' not in info
    validate(output, source, target)


def test_extra_visit_can_initialize_cache_when_all_excess_chains_exceed_degree_bound():
    source = nx.star_graph(5)
    target = nx.Graph([(0, 1), (1, 2), (0, 10), (0, 11), (1, 12),
                       (2, 13), (2, 14), (0, 5), (1, 5)])
    embedding = {0: [0, 1, 2], **{v: [9 + v] for v in range(1, 6)}}
    ctx = cr._Context(source, target)
    assert source.degree(0) > ctx.max_degree
    assert len(embedding[0]) > ctx.lower_bound(0)
    output, info = polish(embedding, source, target, max_passes=1)
    validate(output, source, target)
    assert output[1] == [5] and output[0] == embedding[0]
    direct = info['singleton_search']
    assert direct['degree_skips'] == 1 and direct['cache_builds'] == 1
    assert direct['extra_visits'] == direct['equal_size_moves'] == 1
    assert info['qubits_saved'] == 0 and info['contact_redundancy_gain'] == 1


def test_deadline_before_commit_abandons_certified_but_uncommitted_site(monkeypatch):
    embedding, source, target = unlock_fixture()
    now = [0.0]
    original = sr.direct_singleton

    def delayed(*args, **kwargs):
        site, info = original(*args, **kwargs)
        if site is not None:
            now[0] = 2.0
        return site, info

    monkeypatch.setattr(cr.time, 'perf_counter', lambda: now[0])
    monkeypatch.setattr(sr, 'direct_singleton', delayed)
    output, info = polish(embedding, source, target, deadline=1.0)
    assert output == embedding and info['accepted'] == 0
    assert info['stopped_by'] == 'deadline' and info['deadline_overrun'] == 1.0
    assert info['wall'] == 2.0
    validate(output, source, target)


@pytest.mark.parametrize('change', ['source_directed', 'target_directed',
                                    'source_multi', 'target_multi',
                                    'source_loop', 'target_loop'])
def test_unsupported_certificate_inputs_are_rejected(change):
    embedding, source, target = unlock_fixture()
    graph = source if change.startswith('source') else target
    if change.endswith('directed'):
        graph = nx.DiGraph(graph)
    elif change.endswith('multi'):
        graph = nx.MultiGraph(graph)
    else:
        vertex = next(iter(graph))
        graph.add_edge(vertex, vertex)
    if change.startswith('source'):
        source = graph
    else:
        target = graph
    with pytest.raises(ValueError, match='simple undirected loopless'):
        polish(embedding, source, target)


def test_metadata_and_insertion_order_do_not_dispatch_policy():
    embedding, source, target = unlock_fixture()
    expected, original = polish(embedding, source, target)
    changed_source = nx.Graph()
    changed_source.add_nodes_from(reversed(list(source)))
    changed_source.add_edges_from(reversed(list(source.edges)))
    changed_source.graph.update(family='invented', name='irrelevant')
    changed_target = nx.Graph()
    changed_target.add_nodes_from(reversed(list(target)))
    changed_target.add_edges_from(reversed(list(target.edges)))
    changed = {v: list(reversed(embedding[v])) for v in reversed(list(embedding))}
    output, info = polish(changed, changed_source, changed_target)
    assert output == expected
    info.pop('wall')
    original.pop('wall')
    assert info == original
    validate(output, source, target)
