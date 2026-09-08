"""Independent fixed-footprint and original-graph checks; no whole embedder."""
from collections import Counter
from copy import deepcopy
import itertools
import random
from types import SimpleNamespace

import networkx as nx
import pytest

from ember_qc.algorithms.factored import contact_repair as cr
from ember_qc.algorithms.factored import induced_star_relocation as sr
from ember_qc.algorithms.factored import connected_star_relocation as cs


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


class Budget:
    """Deterministic operation-prefix interruption, including fatal deadlines."""
    def __init__(self, limit=1000000, reason='work_limit', stop_stage=None):
        self.limit, self.reason, self.stop_stage = limit, reason, stop_stage
        self.expansions, self.stopped_by, self.last_stage = 0, None, None
        self.stages = Counter()

    def check(self):
        if self.stopped_by is not None:
            return False
        if self.expansions >= self.limit:
            self.stopped_by = self.reason
            return False
        return True

    def charge(self, stage):
        self.last_stage = stage
        if stage == self.stop_stage:
            self.stopped_by = self.reason
            return False
        if not self.check():
            return False
        self.expansions += 1
        self.stages[stage] += 1
        return True

    def pop(self):
        return self.charge('visit')


def cached(embedding, source, target):
    assert valid(embedding, source, target)
    ctx = cr._Context(source, target)
    cache = sr.build_owner_cache(embedding, ctx, Budget())
    assert cache is not None
    return ctx, cache


def fixture(growth=False, failure=False):
    source = nx.Graph([(3, 1), (1, 0), (0, 2), (2, 4)])
    if growth:
        # X-A1-A2-C-B2-B1-Y, with shortcut A2-B2. C may grow 1 -> 2.
        target = nx.Graph([(5, 0), (0, 1), (1, 2), (2, 3), (3, 4), (4, 6), (1, 3)])
        embedding = {0: [2], 1: [0, 1], 2: [3, 4], 3: [5], 4: [6]}
    else:
        # The documented one-root failure is the extra X-A2 edge.
        target = nx.Graph([(5, 0), (0, 1), (1, 2), (2, 3), (3, 4), (4, 6)])
        if failure:
            target.add_edge(5, 1)
            embedding = {0: [2, 3], 1: [0, 1], 2: [4], 3: [5], 4: [6]}
        else:
            target.add_edge(1, 3)
            embedding = {0: [1, 2, 3], 1: [0], 2: [4], 3: [5], 4: [6]}
    return embedding, source, target


def fixed_state(embedding, ctx, cache, group, footprint, budget=None):
    budget = budget or Budget()
    info = cs._diagnostics()
    problem = cs._Problem(embedding, ctx, group, cache, budget, info)
    state = cs._State(counts=[0] * len(problem.classes))
    # Test-only construction of a prescribed connected footprint. It does not
    # run growth, select a root, or assert any strict-Q condition.
    for i, q in enumerate(footprint):
        cs._add_center(state, q, problem, initial=i == 0)
    cs._direct_fill(state, sorted(state.boundary, key=ctx.rank.__getitem__), problem)
    cs._maximum_assignment(state, problem)
    return problem, state


def expanded_oracle(domains):
    """Exhaustive partial injective assignment to individual logical leaves."""
    def visit(i, used):
        if i == len(domains):
            return 0
        return max([visit(i + 1, used)] +
                   [1 + visit(i + 1, used | {q}) for q in domains[i] if q not in used])
    return visit(0, set())


def matching_problem(domains, demands, sites):
    problem = SimpleNamespace(
        budget=Budget(), info=cs._diagnostics(), k=sum(demands),
        classes=[SimpleNamespace(count=n) for n in demands],
        ctx=SimpleNamespace(rank={q: i for i, q in enumerate(sites)}),
        eligible=lambda i, q: q in domains[i])
    return problem


def check_matching(domains, demands, sites, deleted=None):
    problem = matching_problem(domains, demands, sites)
    state = cs._State(boundary=set(sites), counts=[0] * len(demands))
    cs._direct_fill(state, sites, problem)
    cs._maximum_assignment(state, problem)
    if deleted is not None:
        state.boundary.remove(deleted)
        owner = state.assignment.pop(deleted, None)
        if owner is not None:
            state.counts[owner] -= 1
        cs._maximum_assignment(state, problem)
    expanded = [set(domain) & state.boundary for domain, count in zip(domains, demands)
                for _ in range(count)]
    assert len(state.assignment) == expanded_oracle(expanded)
    assert state.maximum
    assert state.counts == [sum(i == j for i in state.assignment.values())
                            for j in range(len(demands))]
    assert all(count <= demand for count, demand in zip(state.counts, demands))
    assert all(q in domains[i] and q in state.boundary for q, i in state.assignment.items())
    if len(state.assignment) < sum(demands):
        neighbors = set().union(*(set(domains[i]) & state.boundary
                                  for i in state.hall_classes))
        assert neighbors == set(state.hall_sites)
        assert sum(demands[i] for i in state.hall_classes) > len(neighbors)
    return problem, state


def test_exhaustive_compressed_matching_and_occupied_site_deletion():
    sites = (0, 1, 2)
    subsets = [set(q for q in sites if mask & 1 << q) for mask in range(8)]
    for domains in itertools.product(subsets, repeat=2):
        for demands in itertools.product((1, 2), repeat=2):
            check_matching(domains, demands, sites)
            for q in sites:
                check_matching(domains, demands, sites, deleted=q)
    for domains in itertools.product(subsets, repeat=3):
        check_matching(domains, (1, 1, 1), sites)


def test_direct_fill_requires_exchange_and_hall_includes_owned_sites():
    problem, state = check_matching(({0, 1}, {0}), (1, 1), (0, 1))
    assert state.assignment == {0: 1, 1: 0}
    assert problem.info['successful_augmentations'] == 1
    problem, state = check_matching(({0},), (2,), (0, 1))
    assert state.hall_classes == (0,) and state.hall_sites == frozenset({0})
    assert problem.info['hall_demand_peak'] == 2


@pytest.mark.parametrize('seed', range(16))
def test_actual_graph_fixed_footprints_match_individual_assignment_oracle(seed):
    rng = random.Random(seed)
    source = nx.Graph([(0, 1), (0, 2), (0, 3), (1, 4), (2, 4), (3, 5)])
    if seed % 2:
        source.add_edge(0, 5)
    embedding = {0: [0, 1], 1: [2, 3], 2: [4], 3: [5], 4: [6, 7], 5: [8]}
    target = nx.Graph([(0, 1), (2, 3), (6, 7), (0, 2), (1, 4), (0, 5),
                       (3, 6), (4, 7), (5, 8), (1, 8)])
    target.add_node(9)
    target.add_edges_from((a, b) for a, b in itertools.combinations(range(10), 2)
                          if rng.random() < .12)
    ctx, cache = cached(embedding, source, target)
    group = (0, 1, 2, 3)
    occupied = set(embedding[4] + embedding[5])
    available = [q for q in target if q not in occupied]
    footprints = [(q,) for q in available]
    footprints += [(q, p) for q, p in target.edges if q in available and p in available]
    for footprint in footprints:
        problem, state = fixed_state(embedding, ctx, cache, group, footprint)
        assert len(problem.classes) == 2  # Leaves 1 and 2 have identical F.
        boundary = {p for q in footprint for p in target[q]
                    if p in available and p not in footprint}
        assert state.boundary == boundary
        domains = []
        for v in group[1:]:
            frozen = [w for w in source[v] if w not in group]
            domains.append({q for q in boundary if all(
                any(target.has_edge(q, p) for p in embedding[w]) for w in frozen)})
        assert len(state.assignment) == expanded_oracle(domains)
        assert state.edge_boundary == sum(p not in footprint for q in footprint for p in target[q])
        assert set(state.coverage) == {w for w in source[0] if w not in group
                                      and any(target.has_edge(q, p) for q in footprint
                                              for p in embedding[w])}
    output, info = cs.query_connected_star(embedding, ctx, group, cache, Budget())
    if output is not None:
        result = {**embedding, **output}
        assert set(output) == set(group) and valid(result, source, target)
        assert result[4] is embedding[4] and result[5] is embedding[5]
        assert info['qubits_saved'] == sum(len(embedding[v]) - len(result[v]) for v in source) > 0
        assert info['contact_redundancy_gain'] == redundancy(result, source, target) - redundancy(embedding, source, target)
    else:
        assert info['reason'] == 'heuristic_no_proposal'


@pytest.mark.parametrize('growth', [False, True])
def test_strict_certificate_original_graphs_and_actual_member_growth(growth):
    embedding, source, target = fixture(growth=growth)
    snapshot = deepcopy(embedding)
    ctx, cache = cached(embedding, source, target)
    output, info = cs.query_connected_star(embedding, ctx, (0, 1, 2), cache, Budget())
    assert output is not None, info
    result = {**embedding, **output}
    assert valid(result, source, target)
    assert info['qubits_saved'] == 1
    assert info['member_growth'] == int(growth)
    assert info['member_growth'] == sum(len(result[v]) > len(embedding[v]) for v in source)
    assert info['contact_redundancy_gain'] == redundancy(result, source, target) - redundancy(embedding, source, target)
    assert info['complete_proposals'] == info['accepted'] == 1
    assert info['first_zero_successors'] == 1
    assert info['completed_successors'] == 1  # First zero stops the shortlist.
    assert embedding == snapshot and cache.embedding is embedding and cache.valid


def test_negative_redundancy_gain_allowed_on_strict_qubit_reduction():
    source, target = nx.star_graph(2), nx.complete_graph(5)
    embedding = {0: [0], 1: [1, 2], 2: [3, 4]}
    ctx, cache = cached(embedding, source, target)
    output, info = cs.query_connected_star(embedding, ctx, (0, 1, 2), cache, Budget())
    assert valid({**embedding, **output}, source, target)
    assert info['qubits_saved'] == 2 and info['contact_redundancy_gain'] == -2
    assert info['successor_trials'] == 0


def test_documented_root_failure_and_nonmonotone_matching_are_retained():
    embedding, source, target = fixture(failure=True)
    ctx, cache = cached(embedding, source, target)
    output, info = cs.query_connected_star(embedding, ctx, (0, 1, 2), cache, Budget())
    assert output is None and info['reason'] == 'heuristic_no_proposal'
    assert info['complete'] and info['root'] == 1
    assert info['stopped_detail'] == 'steering_exhausted'
    better = {**embedding, 0: [2, 3], 1: [1], 2: [4]}
    assert valid(better, source, target)
    assert sum(map(len, better.values())) < sum(map(len, embedding.values()))
    _, first = fixed_state(embedding, ctx, cache, (0, 1, 2), (1,))
    _, grown = fixed_state(embedding, ctx, cache, (0, 1, 2), (1, 0))
    assert len(first.assignment) == 1 and len(grown.assignment) == 0


def test_distinct_site_capacity_rejects_passing_coupler_capacity():
    source = nx.star_graph(4)
    target = nx.Graph([('r', 's'), ('r', 'p'), ('r', 'q'), ('s', 'p'), ('s', 'q'),
                       ('a', 'b'), ('b', 'c'), ('c', 'd'), ('p', 'a1'),
                       ('a', 'a1'), ('b', 'b1'), ('c', 'c1'), ('d', 'd1')])
    embedding = {0: ['a', 'b', 'c', 'd'], 1: ['a1'], 2: ['b1'], 3: ['c1'], 4: ['d1']}
    ctx, cache = cached(embedding, source, target)
    problem, state = fixed_state(embedding, ctx, cache, (0, 1, 2, 3, 4), ('r', 's'))
    assert ctx.max_degree == 3 and problem.ceiling == 3
    assert state.edge_boundary == 4 and state.boundary == {'p', 'q'}
    assert len(state.assignment) == 2
    assert cs._bounds(state, problem) == 'site_boundary'


def test_unfiltered_boundary_formula_under_every_available_center_extension():
    embedding, source, target = fixture(growth=True)
    ctx, cache = cached(embedding, source, target)
    problem, state = fixed_state(embedding, ctx, cache, (0, 1, 2), (1,))
    assert any(not any(problem.eligible(i, q) for i in range(len(problem.classes)))
               for q in state.boundary)
    for x in state.boundary:
        expected = (state.boundary - {x}) | {
            q for q in target[x] if problem.available(q)
            and q not in state.footprint and q not in state.boundary}
        trial = cs._copy_state(state, problem)
        cs._add_center(trial, x, problem)
        assert trial.boundary == expected
        assert len(trial.boundary) <= len(state.boundary) + ctx.max_degree - 2


@pytest.mark.parametrize('failure', [False, True])
@pytest.mark.parametrize('reason', ['work_limit', 'deadline'])
def test_every_query_work_and_deadline_prefix_discards_partial_state(failure, reason):
    embedding, source, target = fixture(growth=not failure, failure=failure)
    snapshot = deepcopy(embedding)
    ctx, cache = cached(embedding, source, target)
    full = Budget()
    expected, full_info = cs.query_connected_star(embedding, ctx, (0, 1, 2), cache, full)
    stages = Counter()
    for limit in range(full.expansions + 2):
        budget = Budget(limit, reason)
        output, info = cs.query_connected_star(embedding, ctx, (0, 1, 2), cache, budget)
        stages.update(budget.stages)
        assert budget.expansions <= limit
        assert embedding == snapshot and cache.valid and cache.embedding is embedding
        if output is not None:
            assert output == expected and valid({**embedding, **output}, source, target)
            assert info['qubits_saved'] > 0 and info['accepted'] == 1
            assert info['complete']
        else:
            assert info['accepted'] == info['qubits_saved'] == 0
            if not info['complete']:
                assert info['reason'] == reason
    assert {'obligations', 'classes', 'memo', 'matching_queue', 'copy'} <= set(stages)
    if failure:
        assert expected is None and full_info['reason'] == 'heuristic_no_proposal'
        assert {'hall', 'steering_queue'} <= set(stages)
    else:
        assert {'recovery', 'certificate', 'scoring', 'certificate_edges'} <= set(stages)


@pytest.mark.parametrize('reason', ['work_limit', 'deadline'])
def test_actual_steering_route_and_every_interruption_prefix(reason):
    # Give the bad-root example one more unit of strict center allowance by
    # extending its *old* center to a new pendant site. The fixed root stays 1.
    embedding, source, target = fixture(failure=True)
    target.add_edge(2, 7)
    embedding[0].append(7)
    ctx, cache = cached(embedding, source, target)
    full = Budget()
    expected, reference = cs.query_connected_star(embedding, ctx, (0, 1, 2), cache, full)
    assert expected is not None and reference['steering_steps'] == 1
    assert reference['growth'][1]['operator'] == 'steering'
    assert reference['growth'][1]['added'] == 2
    assert reference['root'] == 1 and len(expected[0]) == 3
    assert 'steering_path' in full.stages
    snapshot = deepcopy(embedding)
    for limit in range(full.expansions + 2):
        output, info = cs.query_connected_star(embedding, ctx, (0, 1, 2), cache, Budget(limit, reason))
        assert embedding == snapshot and cache.valid
        if output is not None:
            assert output == expected and valid({**embedding, **output}, source, target)
            assert info['qubits_saved'] == 1
        else:
            assert info['accepted'] == 0 and info['qubits_saved'] == 0


@pytest.mark.parametrize('reason', ['work_limit', 'deadline'])
def test_each_augmentation_path_prefix_is_not_a_completed_maximum(reason):
    domains, demands, sites = ({0, 1}, {0}), (1, 1), (0, 1)
    reference = matching_problem(domains, demands, sites)
    initial = cs._State(boundary=set(sites), counts=[1, 0], assignment={0: 0})
    complete = deepcopy(initial)
    cs._maximum_assignment(complete, reference)
    assert 'matching_path' in reference.budget.stages
    for limit in range(reference.budget.expansions + 2):
        problem = matching_problem(domains, demands, sites)
        problem.budget = Budget(limit, reason)
        trial = deepcopy(initial)
        try:
            cs._maximum_assignment(trial, problem)
        except sr._Interrupted:
            assert not trial.maximum
        else:
            assert trial.maximum and trial.assignment == complete.assignment
            assert trial.counts == complete.counts
        assert initial.assignment == {0: 0} and initial.counts == [1, 0]


@pytest.mark.parametrize('stage', ['eligibility_contacts', 'memo'])
def test_unknown_static_eligibility_never_becomes_cached_false(stage):
    embedding, source, target = fixture(growth=True)
    ctx, cache = cached(embedding, source, target)
    budget = Budget()
    problem = cs._Problem(embedding, ctx, (0, 1, 2), cache, budget, cs._diagnostics())
    budget.stop_stage = stage
    with pytest.raises(sr._Interrupted):
        problem.eligible(0, 0)
    assert problem.memo == {} and problem.info['memo_entries'] == 0
    budget.stop_stage, budget.stopped_by = None, None
    assert problem.eligible(0, 0)
    assert problem.memo == {(0, 0): True}
    assert not problem.eligible(0, 4)
    assert problem.memo[(0, 4)] is False


def test_interrupted_copy_is_not_shared_with_original_state():
    embedding, source, target = fixture(growth=True)
    ctx, cache = cached(embedding, source, target)
    problem, state = fixed_state(embedding, ctx, cache, (0, 1, 2), (1,))
    expected = deepcopy(state)
    records = (len(state.footprint) + len(state.boundary) + len(state.coverage)
               + len(state.assignment) + len(state.counts) + 1)
    for limit in range(records):
        problem.budget = Budget(limit)
        with pytest.raises(sr._Interrupted):
            cs._copy_state(state, problem)
        assert state == expected
    problem.budget = Budget(records)
    copied = cs._copy_state(state, problem)
    assert problem.budget.expansions == records
    assert copied.footprint is not state.footprint and copied.counts is not state.counts
    assert copied.assignment is not state.assignment and copied.coverage is not state.coverage


def test_covered_leaf_shortlist_matches_unsimplified_ranking_without_domain_calls():
    embedding, source, target = fixture(growth=True)
    source.add_edge(0, 7)
    embedding[7] = [7]
    target.add_edges_from([(2, 7), (3, 7)])
    ctx, cache = cached(embedding, source, target)
    problem, state = fixed_state(embedding, ctx, cache, (0, 1, 2), (1, 3))
    assert len(state.assignment) == problem.k and not state.hall_classes
    # Pretend one already-covered center obligation still needs coverage to
    # exercise the numerical rank; this is only a shortlist algebra fixture.
    state.coverage = {}
    expected = []
    for x in state.boundary:
        new_owners = {cache.owner.get(q) for q in ctx.adj[x]}
        new_owners &= problem.center_frozen - set(state.coverage)
        new_sites = [q for q in ctx.adj[x] if q not in state.boundary
                     and q not in state.footprint and problem.available(q)]
        eligible = sum(any(problem.eligible(i, q) for i in range(len(problem.classes)))
                       for q in new_sites)
        score = (problem.k - min(problem.k, len(state.assignment) + eligible)
                 + len(problem.center_frozen) - len(state.coverage) - len(new_owners))
        expected.append((score, 0, ctx.rank[x], x))
    expected.sort(key=lambda record: record[:3])
    def forbidden(*args):
        raise AssertionError('complete leaf demand needs no successor-domain scan')
    problem.eligible = forbidden
    assert cs._shortlist(state, problem) == expected[:4]


def test_search_shared_accounting_refresh_and_cache_identity():
    embedding, source, target = fixture(growth=True)
    ctx = cr._Context(source, target)
    search = cs.ConnectedStarSearch(ctx, 25000)
    assert search.cache is None and search.info['work'] == 0
    assert search.refresh(embedding, embedding, (), Budget(0))
    visit = Budget()
    output, info = search.propose(embedding, 0, visit)
    assert output is not None and info['member_growth'] == 1
    assert info['expansions'] == visit.expansions == search.info['work']
    assert info['setup_work'] == len(source) + sum(map(len, embedding.values()))
    assert info['query_work'] == sum(info['stage_work'].values())
    assert info['setup_work'] + info['query_work'] == info['expansions']
    accepted = {**embedding, **output}
    before = visit.expansions
    assert search.refresh(embedding, accepted, info['group'], visit)
    expected = 2 * len(output) + sum(len(embedding[v]) + len(output[v]) for v in output)
    assert visit.expansions - before == expected == search.info['last_refresh_work']
    assert search.cache.embedding is accepted and search.cache.valid
    assert search.cache.owner == {q: v for v, chain in accepted.items() for q in chain}
    assert search.info['work'] == sum(search.info[k + '_work'] for k in ('setup', 'query', 'refresh'))
    output, info = search.propose(dict(accepted), 0, Budget())
    assert output is None and info['reason'] == 'stale_cache' and search.cache is None


@pytest.mark.parametrize('reason', ['work_limit', 'deadline'])
def test_every_shared_setup_query_and_refresh_prefix_keeps_accepted_embedding(reason):
    embedding, source, target = fixture(growth=True)
    ctx = cr._Context(source, target)
    full_search = cs.ConnectedStarSearch(ctx, 25000)
    full, expected = full_search.propose(embedding, 0, Budget())
    for limit in range(expected['expansions'] + 2):
        search = cs.ConnectedStarSearch(ctx, 25000)
        visit = Budget(limit, reason)
        output, info = search.propose(embedding, 0, visit)
        assert search.info['work'] == visit.expansions == info['expansions']
        assert info['setup_work'] + info['query_work'] == info['expansions']
        assert search.info['work'] <= limit
        if output is not None:
            assert output == full and valid({**embedding, **output}, source, target)
        else:
            assert info['accepted'] == 0 and info['qubits_saved'] == 0
    accepted = {**embedding, **full}
    snapshot = deepcopy(accepted)
    refresh_work = 2 * len(full) + sum(len(embedding[v]) + len(full[v]) for v in full)
    for limit in range(refresh_work + 2):
        search = cs.ConnectedStarSearch(ctx, 25000)
        output, info = search.propose(embedding, 0, Budget())
        visit = Budget(limit, reason)
        ok = search.refresh(embedding, accepted, info['group'], visit)
        assert search.info['last_refresh_work'] == visit.expansions <= limit
        assert accepted == snapshot and valid(accepted, source, target)
        if not ok:
            assert search.cache is None and search.info['disabled_reason'].startswith('refresh_')
            later, detail = search.propose(accepted, 0, Budget())
            assert later is None and detail['reason'] == 'disabled'
        else:
            assert search.cache.embedding is accepted


def test_auxiliary_is_live_across_setup_and_queries_and_has_no_2048_query_cap():
    embedding, source, target = fixture(growth=True)
    ctx = cr._Context(source, target)
    search = cs.ConnectedStarSearch(ctx, 200)
    visit = Budget(1000)
    output, info = search.propose(embedding, 0, visit)
    assert output is None and info['reason'] == 'auxiliary_limit'
    assert info['expansions'] == visit.expansions == 200
    later, detail = search.propose(embedding, 0, Budget(1000))
    assert later is None and detail['expansions'] == 0
    assert search.info['work'] == 200
    # This tests the interface's live allowance directly, without forcing a
    # favorable graph or embedding run to consume a particular amount of work.
    unlimited = cs.ConnectedStarSearch(ctx, 25000)
    visit = Budget(4000)
    shared = cs._StageBudget(unlimited, visit, 'query')
    assert all(shared.charge('diagnostic') for _ in range(3000))
    assert shared.limit is None and shared.expansions == visit.expansions == 3000


def test_policy_selection_independence_zero_excess_degree_and_constructor_work():
    class OpaqueContext:
        def __getattr__(self, name):
            raise AssertionError('constructor inspected a context/source record')
    assert cs.ConnectedStarSearch(OpaqueContext(), 0).info['work'] == 0
    for bad in (-1, True, 1.5, None):
        with pytest.raises(ValueError):
            cs.ConnectedStarSearch(OpaqueContext(), bad)
    source, target = nx.Graph([(0, 1), (0, 2), (0, 3), (1, 2)]), nx.complete_graph(8)
    embedding = {0: [0], 1: [1], 2: [2, 3], 3: [4]}
    ctx, cache = cached(embedding, source, target)
    group, _ = cs.select_connected_star(embedding, ctx, 0, Budget())
    assert group == (0, 2, 3)
    output, info = cs.query_connected_star(embedding, ctx, (0, 1, 2), cache, Budget())
    assert output is None and info['reason'] == 'not_induced_star'
    singleton = {v: chain[:1] for v, chain in embedding.items()}
    group, info = cs.select_connected_star(singleton, ctx, 0, Budget())
    assert group is None and info['reason'] == 'zero_excess'


def test_mixed_labels_and_same_logical_physical_namespaces():
    embedding, source, target = fixture(growth=True)
    names = {0: ('c', 0), 1: '1', 2: 1, 3: ('f', 0), 4: 'z'}
    source = nx.relabel_nodes(source, names)
    embedding = {names[v]: chain for v, chain in embedding.items()}
    ctx, cache = cached(embedding, source, target)
    output, info = cs.query_connected_star(embedding, ctx, tuple(names[v] for v in (0, 1, 2)), cache, Budget())
    assert output is not None and valid({**embedding, **output}, source, target)
    assert info['qubits_saved'] == 1


def zephyr_witness():
    """Fixed structural construction on ideal Z12; no embedding solver call."""
    import dwave_networkx as dnx
    source, target = nx.star_graph(22), dnx.zephyr_graph(12)
    ctx = cr._Context(source, target)
    root = next(q for q in ctx.adj if len(ctx.adj[q]) == ctx.max_degree)
    def boundary(chain):
        return {p for q in chain for p in ctx.adj[q] if p not in chain}
    mate = next(q for q in ctx.adj[root] if len(boundary({root, q})) >= 22)
    pair = {root, mate}
    extra = next(q for q in sorted(boundary(pair), key=ctx.rank.__getitem__)
                 if len(boundary(pair | {q})) >= 22)
    center = pair | {extra}
    leaves = sorted(boundary(center), key=ctx.rank.__getitem__)[:22]
    embedding = {0: sorted(center, key=ctx.rank.__getitem__),
                 **{v: [q] for v, q in zip(range(1, 23), leaves)}}
    return embedding, source, target


def test_actual_z12_high_degree_multi_qubit_center_from_independent_incumbent():
    embedding, source, target = zephyr_witness()
    snapshot = deepcopy(embedding)
    ctx, _ = cached(embedding, source, target)
    assert len(source[0]) == 22 > ctx.max_degree == 20
    search, visit = cs.ConnectedStarSearch(ctx, 25000), Budget(25000)
    output, info = search.propose(embedding, 0, visit)
    assert output is not None, info
    assert valid({**embedding, **output}, source, target)
    assert info['leaves'] == 22 and info['demand_classes'] == 1
    assert len(output[0]) == 2 and info['qubits_saved'] == 1
    assert len(info['group']) == 23 > 4
    assert info['expansions'] == visit.expansions <= 25000
    assert embedding == snapshot
