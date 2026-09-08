"""Original-graph and injective-assignment oracles for the isolated star core."""
from copy import deepcopy
import itertools
import random

import networkx as nx
import pytest

from ember_qc.algorithms.factored import contact_repair as cr
from ember_qc.algorithms.factored import induced_star_relocation as sr


def valid(embedding, source, target):
    if set(embedding) != set(source):
        return False
    occupied = set()
    for chain in embedding.values():
        if (not chain or len(chain) != len(set(chain))
                or any(q not in target for q in chain) or occupied.intersection(chain)
                or not nx.is_connected(target.subgraph(chain))):
            return False
        occupied.update(chain)
    return all(any(target.has_edge(p, q) for p in embedding[u] for q in embedding[v])
               for u, v in source.edges)


def redundancy(embedding, source, target):
    return sum(sum(target.has_edge(p, q) for p in embedding[u] for q in embedding[v]) - 1
               for u, v in source.edges)


def fixture():
    source = nx.Graph([('c', 'a'), ('c', 'b')])
    target = nx.Graph([(0, 1), (0, 2), (1, 3)])
    embedding = {'c': [0, 1], 'a': [2], 'b': [3]}
    return embedding, source, target


def cached(embedding, source, target):
    assert valid(embedding, source, target)
    ctx = cr._Context(source, target)
    cache = sr.build_owner_cache(embedding, ctx, cr._Budget(100000, None))
    assert cache is not None
    return ctx, cache


def oracle(embedding, source, target, group):
    frozen = {p for v, chain in embedding.items() if v not in group for p in chain}
    available = [p for p in target if p not in frozen]
    for sites in itertools.permutations(available, len(group)):
        trial = {**embedding, **{v: [p] for v, p in zip(group, sites)}}
        if valid(trial, source, target):
            return trial
    return None


class StageBudget:
    def __init__(self, limit=100000, stop_stage=None, reason='work_limit'):
        self.limit, self.stop_stage, self.reason = limit, stop_stage, reason
        self.expansions = 0
        self.stopped_by = None
        self.stages = {}

    def check(self):
        if self.stopped_by is not None:
            return False
        if self.expansions >= self.limit:
            self.stopped_by = self.reason
            return False
        return True

    def charge(self, stage):
        if stage == self.stop_stage:
            self.stopped_by = self.reason
            return False
        if not self.check():
            return False
        self.expansions += 1
        self.stages[stage] = self.stages.get(stage, 0) + 1
        return True

    def pop(self):
        return self.charge('unspecified')


def test_plain_replacement_certificate_and_no_external_obligations():
    embedding, source, target = fixture()
    snapshot = deepcopy(embedding)
    ctx, cache = cached(embedding, source, target)
    group, selected = sr.select_star(embedding, ctx, 'c', StageBudget())
    assert group == ('c', 'a', 'b') and selected['complete']
    result, info = sr.query_star(embedding, ctx, group, cache, StageBudget())
    assert result is not None and info['accepted'] == 1
    assert info['root_seed'] is None
    assert valid({**embedding, **result}, source, target)
    assert info['qubits_saved'] == 1
    assert info['contact_redundancy_gain'] == (
        redundancy({**embedding, **result}, source, target) - redundancy(embedding, source, target))
    assert embedding == snapshot and cache.embedding is embedding


@pytest.mark.parametrize('seed', range(48))
def test_query_feasibility_matches_direct_injective_oracle(seed):
    rng = random.Random(seed)
    source = nx.Graph([('c', 'a'), ('c', 'b')])
    embedding = {'c': [0, 1], 'a': [2, 3], 'b': [4, 5]}
    target = nx.Graph([(0, 1), (2, 3), (4, 5), (0, 2), (1, 4)])
    if seed % 2:
        source.add_edge('a', 'x')
        embedding['x'] = [6]
        target.add_edge(3, 6)
    if seed % 3:
        source.add_edge('b', 'y')
        embedding['y'] = [7]
        target.add_edge(5, 7)
    target.add_nodes_from(range(8))
    for a, b in itertools.combinations(target, 2):
        if rng.random() < .15:
            target.add_edge(a, b)
    snapshot = deepcopy(embedding)
    ctx, cache = cached(embedding, source, target)
    group = ('c', 'a', 'b')
    reference = oracle(embedding, source, target, group)
    output, info = sr.query_star(embedding, ctx, group, cache, StageBudget())
    assert info['complete'], info
    assert (output is not None) == (reference is not None)
    assert embedding == snapshot
    if output is not None:
        trial = {**embedding, **output}
        assert valid(trial, source, target)
        assert set(output) == set(group)
        assert info['qubits_saved'] == sum(map(len, embedding.values())) - sum(map(len, trial.values()))
        assert info['contact_redundancy_gain'] == redundancy(trial, source, target) - redundancy(embedding, source, target)
    else:
        assert info['reason'] == 'exhaustive_no_match'


def test_larger_than_four_block_and_extra_physical_leaf_edges():
    source = nx.star_graph(5)
    embedding = {0: [0, 1], **{i: [i + 1] for i in range(1, 6)}}
    target = nx.Graph([(0, 1), (0, 2), (0, 3), (1, 4), (1, 5), (1, 6)])
    target.add_edges_from((10, p) for p in range(7))
    target.add_edges_from([(2, 3), (3, 4)])
    ctx, cache = cached(embedding, source, target)
    group, _ = sr.select_star(embedding, ctx, 0, StageBudget())
    assert len(group) == 6
    result, info = sr.query_star(embedding, ctx, group, cache, StageBudget())
    assert result is not None and info['qubits_saved'] == 1
    assert valid({**embedding, **result}, source, target)


def test_logical_leaf_edge_rejected_and_greedy_rule_is_not_subset_search():
    embedding, source, target = fixture()
    source.add_edge('a', 'b')
    target.add_edge(2, 3)
    ctx, cache = cached(embedding, source, target)
    group, selection = sr.select_star(embedding, ctx, 'c', StageBudget())
    assert group is None and selection['reason'] == 'too_few_leaves'
    result, info = sr.query_star(embedding, ctx, ('c', 'a', 'b'), cache, StageBudget())
    assert result is None and info['reason'] == 'not_induced_star'


def test_structural_leaf_priority_and_zero_excess():
    source = nx.Graph([('c', 'a'), ('c', 'b'), ('c', 'd'), ('a', 'b')])
    target = nx.complete_graph(12)
    embedding = {'c': [0], 'a': [1, 2], 'b': [3, 4, 5], 'd': [6]}
    ctx, _ = cached(embedding, source, target)
    selected, _ = sr.select_star(embedding, ctx, 'c', StageBudget())
    assert selected == ('c', 'b', 'd')  # excess outranks a's conflicting placement
    singleton = {'c': [0], 'a': [1], 'b': [3], 'd': [6]}
    selected, info = sr.select_star(singleton, ctx, 'c', StageBudget())
    assert selected is None and info['reason'] == 'zero_excess'


def test_degree_bound_before_owner_setup():
    source = nx.star_graph(3)
    target = nx.path_graph(8)
    ctx = cr._Context(source, target)
    search = sr.StarSearch(ctx, 10000)
    # Degree rejection is mathematical and precedes cache access; no claim that
    # these deliberately unsupported branch sets form a valid incumbent.
    result, info = search.propose({v: [v] for v in source}, 0, StageBudget())
    assert result is None and info['reason'] == 'center_degree'
    assert search.info['setup_work'] == 0 and not search.setup_attempted


def test_hall_subset_failure_despite_nonempty_domains_and_large_union():
    leaves = (0, 'leaf', ('leaf', 2))
    domains = [[0], [0], [1, 2]]
    assert len(set().union(*map(set, domains))) == len(leaves)
    info = {'matching_edges': 0}
    result = sr._matching(leaves, domains, StageBudget(), info)
    assert result is None and info['matching_edges'] > 0
    assert not any(all(p in d for p, d in zip(sites, domains))
                   for sites in itertools.permutations([0, 1, 2]))


def test_augmenting_path_repairs_previous_assignment_and_separates_labels():
    leaves = (0, 'leaf', (1,))
    domains = [[0, 'p'], [0, ('q',)], [0, ('q',)]]
    info = {'matching_edges': 0}
    result = sr._matching(leaves, domains, StageBudget(), info)
    assert result is not None and len(set(result.values())) == 3
    assert all(result[v] in domains[i] for i, v in enumerate(leaves))


def test_heterogeneous_source_and_target_labels():
    embedding, source, target = fixture()
    source_map = {'c': 0, 'a': '0', 'b': ('b',)}
    target_map = {0: 0, 1: '0', 2: ('q',), 3: ('b',)}
    source = nx.relabel_nodes(source, source_map)
    target = nx.relabel_nodes(target, target_map)
    embedding = {source_map[v]: [target_map[p] for p in chain] for v, chain in embedding.items()}
    ctx, cache = cached(embedding, source, target)
    result, info = sr.query_star(embedding, ctx, (0, '0', ('b',)), cache, StageBudget())
    assert result is not None and valid({**embedding, **result}, source, target)
    assert info['qubits_saved'] == 1


@pytest.mark.parametrize('stage', ['obligations', 'root_generation', 'eligibility',
                                   'domains', 'matching', 'scoring', 'certificate'])
@pytest.mark.parametrize('reason', ['work_limit', 'deadline'])
def test_every_query_stage_interruption_preserves_incumbent(stage, reason):
    embedding, source, target = fixture()
    snapshot = deepcopy(embedding)
    ctx, cache = cached(embedding, source, target)
    owners = dict(cache.owner)
    budget = StageBudget(stop_stage=stage, reason=reason)
    result, info = sr.query_star(embedding, ctx, ('c', 'a', 'b'), cache, budget)
    assert result is None and not info['complete'] and info['reason'] == reason
    assert embedding == snapshot and cache.owner == owners and cache.valid


def test_every_work_prefix_returns_only_certified_complete_result():
    embedding, source, target = fixture()
    snapshot = deepcopy(embedding)
    ctx, cache = cached(embedding, source, target)
    full = StageBudget()
    result, _ = sr.query_star(embedding, ctx, ('c', 'a', 'b'), cache, full)
    assert result is not None
    for limit in range(full.expansions + 2):
        budget = StageBudget(limit=limit)
        result, info = sr.query_star(embedding, ctx, ('c', 'a', 'b'), cache, budget)
        assert budget.expansions <= limit
        assert embedding == snapshot
        if result is not None:
            assert info['accepted'] and valid({**embedding, **result}, source, target)
        else:
            assert not info['accepted'] and not info['complete']


def test_setup_interruption_and_stale_identity_disable_without_rebuild():
    embedding, source, target = fixture()
    ctx = cr._Context(source, target)
    assert sr.build_owner_cache(embedding, ctx, StageBudget(stop_stage='setup')) is None
    search = sr.StarSearch(ctx, 100000)
    group, _ = sr.select_star(embedding, ctx, 'c', StageBudget())
    selecting = StageBudget()
    sr.select_star(embedding, ctx, 'c', selecting)
    result, info = search.propose(embedding, 'c', StageBudget(limit=selecting.expansions + 2))
    assert result is None and search.info['disabled_reason'].startswith('setup_')
    result, _ = search.propose(embedding, 'c', StageBudget())
    assert result is None and search.info['cache_builds'] == 0
    search = sr.StarSearch(ctx, 100000)
    search.propose(embedding, 'c', StageBudget())
    result, info = search.propose(dict(embedding), 'c', StageBudget())
    assert result is None and info['reason'] == 'stale_cache'
    assert search.cache is None


def test_refresh_transfers_ownership_atomically_and_interrupt_disables():
    source = nx.Graph([('a', 'b')])
    target = nx.path_graph(3)
    old = {'a': [0, 1], 'b': [2]}
    new = {'a': [2], 'b': [0, 1]}
    ctx, cache = cached(old, source, target)
    assert valid(new, source, target)
    assert sr.refresh_owner_cache(cache, old, new, ('a', 'b'), ctx, StageBudget())
    assert cache.owner == {2: 'a', 0: 'b', 1: 'b'} and cache.embedding is new
    for limit in range(10):
        _, cache = cached(old, source, target)
        assert not sr.refresh_owner_cache(cache, old, new, ('a', 'b'), ctx, StageBudget(limit))
        assert not cache.valid and old == {'a': [0, 1], 'b': [2]} and valid(new, source, target)


def test_finishing_exactly_at_work_limit_is_complete_not_partial():
    embedding, source, target = fixture()
    ctx = cr._Context(source, target)
    budget = StageBudget(len(embedding) + sum(map(len, embedding.values())))
    cache = sr.build_owner_cache(embedding, ctx, budget)
    assert cache is not None and cache.valid
    full = StageBudget()
    result, _ = sr.query_star(embedding, ctx, ('c', 'a', 'b'), cache, full)
    exact = StageBudget(full.expansions)
    repeated, info = sr.query_star(embedding, ctx, ('c', 'a', 'b'), cache, exact)
    assert repeated == result and info['accepted'] and info['complete']
    new = {**embedding, **result}
    units = 2 * 3 + sum(map(len, embedding.values())) + sum(map(len, new.values()))
    assert sr.refresh_owner_cache(cache, embedding, new, ('c', 'a', 'b'), ctx, StageBudget(units))
    assert cache.valid and cache.embedding is new


def test_search_refresh_after_ordinary_move_then_current_query():
    embedding, source, target = fixture()
    source.add_node('outside')
    target.add_edge(10, 11)
    embedding['outside'] = [10, 11]
    ctx = cr._Context(source, target)
    search = sr.StarSearch(ctx, 100000)
    assert search.refresh(embedding, embedding, (), StageBudget())
    assert search.info['work'] == 0  # lazy no-cache maintenance is a no-op
    search.propose(embedding, 'c', StageBudget())
    ordinary = {**embedding, 'outside': [11]}
    assert valid(ordinary, source, target)
    assert search.refresh(embedding, ordinary, ('outside',), StageBudget())
    assert 10 not in search.cache.owner
    result, info = search.propose(ordinary, 'c', StageBudget())
    assert result is not None and valid({**ordinary, **result}, source, target)
    accepted = {**ordinary, **result}
    assert not search.refresh(ordinary, accepted, info['group'], StageBudget(limit=0))
    assert search.cache is None and search.info['disabled_reason'].startswith('refresh_')
    assert valid(accepted, source, target)


def test_query_cap_and_shared_work_accounting():
    source = nx.star_graph(20)
    source.add_node('frozen')
    embedding = {0: [5000, 5001], **{i: [6000 + i] for i in range(1, 21)}, 'frozen': [7000]}
    target = nx.Graph([(5000, 5001)])
    target.add_edges_from((5000 if i <= 10 else 5001, 6000 + i) for i in range(1, 21))
    target.add_edges_from((7000, 8000 + i) for i in range(20))
    target.add_nodes_from(range(3000))
    assert valid(embedding, source, target)
    search = sr.StarSearch(cr._Context(source, target), 10000)
    visit = StageBudget()
    result, info = search.propose(embedding, 0, visit)
    assert result is None and info['reason'] == 'query_limit'
    assert info['query_work'] == 2048 and info['setup_work'] > 0
    assert info['expansions'] == visit.expansions == search.info['work']
    assert search.info['work'] == sum(search.info[k] for k in ('setup_work', 'query_work', 'refresh_work'))
    assert sum(info['stage_work'].values()) == info['query_work']
    assert sum(search.info['query_stage_work'].values()) == search.info['query_work']


def test_owner_setup_can_exceed_query_ceiling_but_not_shared_limits():
    embedding, source, target = fixture()
    for v in range(2200):
        source.add_node(('isolated', v))
        target.add_node(10000 + v)
        embedding[('isolated', v)] = [10000 + v]
    search = sr.StarSearch(cr._Context(source, target), 10000)
    visit = StageBudget(10000)
    result, info = search.propose(embedding, 'c', visit)
    assert result is not None
    assert info['setup_work'] > 2048 and info['query_work'] < 2048
    assert visit.expansions == info['expansions'] < 10000
    assert valid({**embedding, **result}, source, target)


def test_per_call_query_and_refresh_deltas_exclude_prior_ordinary_work():
    embedding, source, target = fixture()
    search = sr.StarSearch(cr._Context(source, target), 1000)
    visit = StageBudget(1000)
    for _ in range(23):
        visit.pop()
    result, move = search.propose(embedding, 'c', visit)
    assert result is not None
    assert move['expansions'] == visit.expansions - 23
    assert move['expansions'] == move['query_work'] + move['setup_work']
    assert move['query_wall'] + move['setup_wall'] == pytest.approx(move['wall'])
    previous = visit.expansions
    accepted = {**embedding, **result}
    assert search.refresh(embedding, accepted, move['group'], visit)
    assert search.info['last_refresh_work'] == visit.expansions - previous
    assert search.info['refresh_work'] == search.info['last_refresh_work']
    assert search.info['last_refresh_wall'] == search.info['refresh_wall']
    assert search.info['last_refresh_reason'] == 'refreshed'
    assert search.info['work'] == visit.expansions - 23
    assert search.info['certified_proposals'] == 1


@pytest.mark.parametrize('auxiliary_limit', [0, 1, 20, 40])
def test_auxiliary_and_visit_caps_never_overrun(auxiliary_limit):
    embedding, source, target = fixture()
    search = sr.StarSearch(cr._Context(source, target), auxiliary_limit)
    budget = StageBudget(30)
    result, info = search.propose(embedding, 'c', budget)
    assert result is None and not info['complete']
    assert search.info['work'] <= auxiliary_limit and budget.expansions <= 30
    assert search.info['work'] == budget.expansions


def test_constructor_does_not_traverse_context():
    class Context:
        def __getattr__(self, name):
            raise AssertionError('constructor must not inspect ' + name)
    sr.StarSearch(Context(), 100)


def test_real_expired_deadline():
    embedding, source, target = fixture()
    search = sr.StarSearch(cr._Context(source, target), 1000)
    result, info = search.propose(embedding, 'c', cr._Budget(1000, -1))
    assert result is None and info['reason'] == 'deadline' and search.info['work'] == 0


def test_fixed_actual_z12_witness_and_saved_generic_quality():
    import dwave_networkx as dnx
    source = nx.Graph([('x', 'a'), ('a', 'c'), ('c', 'b'), ('b', 'y')])
    target = dnx.zephyr_graph(12, 4, coordinates=True)
    embedding = {
        'x': [(0, 0, 0, 0, 0)], 'a': [(0, 0, 0, 0, 1), (0, 0, 0, 0, 2)],
        'c': [(1, 5, 0, 0, 0), (1, 5, 0, 0, 1)],
        'b': [(0, 3, 0, 0, 2), (0, 3, 0, 0, 1)], 'y': [(0, 3, 0, 0, 0)],
    }
    saved_generic = {**embedding, 'a': [(0, 0, 0, 0, 1)], 'b': [(0, 3, 0, 0, 1)],
                     'c': [(0, 0, 0, 1, 0), (1, 2, 3, 0, 0), (1, 2, 3, 0, 1)]}
    assert valid(embedding, source, target) and valid(saved_generic, source, target)
    assert sum(map(len, saved_generic.values())) == 7
    search = sr.StarSearch(cr._Context(source, target), 25000)
    result, info = search.propose(embedding, 'c', cr._Budget(50000, None))
    assert result is not None, info
    trial = {**embedding, **result}
    assert valid(trial, source, target) and sum(map(len, trial.values())) == 5
    assert info['qubits_saved'] == 3 and info['query_work'] <= 2048
    assert info['contact_redundancy_gain'] == redundancy(trial, source, target) - redundancy(embedding, source, target)
    assert info['root_seed']['hops'] == 2
    for v in ('a', 'b', 'c'):
        assert not any(valid({**embedding, v: [p]}, source, target) for p in target)
