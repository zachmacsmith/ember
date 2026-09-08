"""Independent contact counts, atomic acceptance and frozen old-path replays.

Injected proposals test acceptance semantics, not proposer reachability or ACL.
The quotient fixtures and actual-Z12 witness invoke no external embedder.
"""
from copy import deepcopy
import importlib.util
import itertools
from pathlib import Path
import random
import sys

import networkx as nx
import pytest

from ember_qc.algorithms.factored import contact_repair as cr
from ember_qc.algorithms.factored import endpoint_support as es


OBJECTIVE = 'qubits_endpoint_support'
ROOT = Path(__file__).resolve().parents[2]


def valid(embedding, source, target):
    assert set(embedding) == set(source)
    sites = [q for chain in embedding.values() for q in chain]
    assert len(sites) == len(set(sites)) and set(sites) <= set(target)
    for chain in embedding.values():
        assert chain and nx.is_connected(target.subgraph(chain))
    for u, v in source.edges:
        assert any(target.has_edge(q, p) for q in embedding[u] for p in embedding[v])


def oracle(embedding, group, source, target):
    """Enumerate the whole physical edge set, independent of selected scans."""
    valid(embedding, source, target)
    owner = {q: u for u, chain in embedding.items() for q in chain}
    edges = {frozenset((u, v)) for u, v in source.edges if u in group or v in group}
    support = {(u, v): set() for u, v in source.edges if frozenset((u, v)) in edges}
    support.update({(v, u): set() for u, v in list(support)})
    contacts = 0
    for q, p in target.edges:
        if q not in owner or p not in owner:
            continue
        u, v = owner[q], owner[p]
        if u != v and frozenset((u, v)) in edges:
            contacts += 1
            support[u, v].add(q)
            support[v, u].add(p)
    hist = {}
    for sites in support.values():
        hist[len(sites)] = hist.get(len(sites), 0) + 1
    return dict(histogram=hist, redundancy=contacts-len(edges))


def quotient(seed):
    rng = random.Random(seed)
    source = nx.complete_graph(4)
    source.remove_edge(2, 3)  # A real physical edge that must not enter the score.
    target = nx.empty_graph(16)
    embedding = {u: [3*u, 3*u+1, 3*u+2] for u in source}
    for chain in embedding.values():
        target.add_edges_from(zip(chain, chain[1:]))
    target.add_edges_from(itertools.combinations(range(0, 12, 3), 2))
    target.add_edges_from((q, p) for q in range(12, 16) for p in range(0, 12, 3))
    target.add_edges_from((q, p) for q in target for p in target if q < p and rng.random() < .22)
    return embedding, source, target


@pytest.mark.parametrize('seed', range(8))
def test_scores_match_whole_target_oracle_after_owner_transfer_and_release(seed):
    entry, source, target = quotient(seed)
    # Mixed labels prevent integer-ID assumptions; each selected group has at
    # least one multi-qubit outside chain except the deliberate all-chain case.
    labels = {0: ('v', 0), 1: 'one', 2: -7, 3: ('v', 3)}
    physical = {q: ('q', q) if q % 2 else f'q{q}' for q in target}
    source, target = nx.relabel_nodes(source, labels), nx.relabel_nodes(target, physical)
    entry = {labels[u]: [physical[q] for q in chain] for u, chain in entry.items()}
    snapshot = deepcopy(entry)
    for raw_group in ((0,), (0, 1), (0, 2, 3), (0, 1, 2, 3)):
        group = tuple(labels[u] for u in raw_group)
        scorer = es.EndpointScorer(entry, cr._Context(source, target), group)
        assert scorer.info['owner_entries'] == 0 and scorer._owner is None
        assert scorer.score(entry) == oracle(entry, group, source, target)
        proposal = dict(entry)
        if len(group) > 1:
            for u, v in zip(group, (*group[1:], group[0])):
                proposal[u] = list(entry[v])
        else:
            proposal[group[0]] = [physical[12]]
        assert scorer.score(proposal) == oracle(proposal, group, source, target)
        assert scorer.info['owner_setup_attempts'] == 1
        assert scorer.info['owner_entries'] == sum(map(len, entry.values()))
        assert scorer.info['attempted'] == scorer.info['completed'] == 2
        assert scorer.info['incident_source_edges'] == sum(
            u in group or v in group for u, v in source.edges)
        assert scorer.info['source_adjacency_entries'] == sum(source.degree(v) for v in group)
    assert entry == snapshot


def disagreement():
    source = nx.Graph([('u', 'v')])
    target = nx.Graph([('a', 'b'), ('c', 'd'), ('x', 'y'), ('y', 'z'),
                       ('a', 'x'), ('a', 'y'), ('a', 'z'), ('c', 'x'), ('d', 'y')])
    return {'u': ['a', 'b'], 'v': ['x', 'y', 'z']}, source, target


def test_released_sites_of_a_selected_neighbor_never_remain_phantom_supports():
    entry, source, target = disagreement()
    proposal = dict(entry, v=['z'])  # x/y are free, although both touch a.
    scorer = es.EndpointScorer(entry, cr._Context(source, target), ('u', 'v'))
    assert scorer.score(proposal) == oracle(proposal, ('u', 'v'), source, target)
    assert scorer.score(proposal) == dict(histogram={1: 2}, redundancy=0)


def force(monkeypatch, chains):
    def alternatives(*args, **kwargs):
        return [frozenset(chain) for chain in chains]
    monkeypatch.setattr(cr, '_alternatives', alternatives)


def test_equal_size_histogram_improvement_can_have_negative_signed_R(monkeypatch):
    entry, source, target = disagreement()
    force(monkeypatch, [('c', 'd')])
    result, info = cr.repair_group(entry, source, target, ('u',), objective=OBJECTIVE,
                                    max_orders=1, beam_width=1)
    valid(result, source, target)
    assert result['u'] == ['c', 'd'] and result['v'] is entry['v']
    assert info['qubits_saved'] == 0 and info['equal_size_moves'] == 1
    assert info['contact_redundancy_gain'] == -1
    assert info['endpoint_support']['histogram_delta'] == {1: -1, 2: 2, 3: -1}
    assert info['endpoint_support']['histogram_complete']
    original, legacy = cr.repair_group(entry, source, target, ('u',),
                                       objective='qubits_contacts', max_orders=1)
    assert original == entry and legacy['accepted'] == 0


def test_equal_proposal_compares_against_current_best_and_rejects_exact_ties(monkeypatch):
    source = nx.Graph([(0, 1)])
    target = nx.Graph([(0, 1), (2, 3), (4, 5), (6, 7), (10, 11), (11, 12),
                       (0, 10), (2, 10), (3, 11), (4, 10), (4, 11), (6, 10), (7, 11)])
    entry = {0: [0, 1], 1: [10, 11, 12]}
    force(monkeypatch, [(2, 3), (4, 5), (6, 7)])
    result, info = cr.repair_group(entry, source, target, (0,), objective=OBJECTIVE,
                                    max_orders=1, beam_width=3)
    assert result[0] == [2, 3]
    assert info['endpoint_support']['best_equal_updates'] == 1
    assert info['endpoint_support']['score']['cache_hits'] == 2
    assert info['endpoint_support']['score']['owner_setup_attempts'] == 1
    valid(result, source, target)


@pytest.mark.parametrize('api', ['repair_group', 'contact_polish'])
def test_strict_Q_commits_without_any_secondary_scan_and_reports_unknown(monkeypatch, api):
    force(monkeypatch, [(0,)])
    def forbidden(*args, **kwargs):
        raise AssertionError('strict Q must not require a secondary score')
    monkeypatch.setattr(es.EndpointScorer, 'score', forbidden)
    source, target, entry = nx.empty_graph(1), nx.path_graph(3), {0: [0, 1, 2]}
    if api == 'repair_group':
        result, info = cr.repair_group(entry, source, target, (0,), objective=OBJECTIVE,
                                        max_orders=1)
    else:
        result, info = cr.contact_polish(entry, source, target, objective=OBJECTIVE,
                                         group_sizes=(1,), max_groups=1, max_passes=1)
        assert info['trajectory'][0]['contact_redundancy_gain'] is None
        assert not info['trajectory'][0]['secondary_complete']
    assert result == {0: [0]} and info['qubits_saved'] == 2
    assert info['contact_redundancy_gain'] is None
    assert info['endpoint_support']['histogram_delta'] is None
    assert info['endpoint_support']['unknown_moves'] == 1
    assert info['endpoint_support']['score']['attempted'] == 0
    assert info['endpoint_support']['score']['owner_entries'] == 0
    valid(result, source, target)


def test_interrupted_later_equal_score_retains_prior_strict_Q_commit(monkeypatch):
    source, target, entry = nx.empty_graph(1), nx.path_graph(3), {0: [0, 1, 2]}
    force(monkeypatch, [(0,), (1,)])
    def interrupted(*args, **kwargs):
        raise es.ScoreDeadline('forced')
    monkeypatch.setattr(es.EndpointScorer, 'score', interrupted)
    result, info = cr.repair_group(entry, source, target, (0,), objective=OBJECTIVE,
                                    max_orders=1, beam_width=2)
    assert result == {0: [0]} and info['qubits_saved'] == 2
    assert info['contact_redundancy_gain'] is None
    assert info['stopped_by'] == 'deadline'


def test_scoring_does_not_redefine_or_extend_routing_expansion_budget(monkeypatch):
    entry, source, target = disagreement()
    def last_expansion(v, prefix, occupied, selected, region, embedding, ctx,
                       alternatives, size_cap, budget, info, tree_policy):
        assert budget.pop() and budget.expansions == budget.limit == 1
        return [frozenset(('c', 'd'))]
    monkeypatch.setattr(cr, '_alternatives', last_expansion)
    result, info = cr.repair_group(entry, source, target, ('u',), objective=OBJECTIVE,
                                    max_orders=1, halo=0, max_expansions=1)
    assert info['accepted'] == 1 and result['u'] == ['c', 'd']
    assert info['expansions'] == 1 and info['stopped_by'] == 'work_limit'
    assert info['endpoint_support']['score']['target_adjacency_entries'] > 1


def test_aggregate_retains_known_negative_R_beside_unknown_strict_Q_delta(monkeypatch):
    entry, source, target = disagreement()
    source.add_node('isolated')
    target.add_edge('m', 'n')
    entry['isolated'] = ['m', 'n']
    monkeypatch.setattr(cr, '_groups', lambda *args: [('u',), ('isolated',)])
    def alternatives(v, *args, **kwargs):
        return [frozenset(('c', 'd') if v == 'u' else ('m',))]
    monkeypatch.setattr(cr, '_alternatives', alternatives)
    result, info = cr.contact_polish(entry, source, target, objective=OBJECTIVE,
                                     max_groups=2, max_passes=1, max_orders=1)
    valid(result, source, target)
    assert info['accepted'] == 2 and info['qubits_saved'] == 1
    assert info['contact_redundancy_gain'] is None
    detail = info['endpoint_support']
    assert detail['known_contact_redundancy_gain'] == -1
    assert detail['known_histogram_delta'] == {1: -1, 2: 2, 3: -1}
    assert detail['unknown_moves'] == 1 and not detail['histogram_complete']
    assert detail['histogram_delta'] is None
    assert [row['contact_redundancy_gain'] for row in info['trajectory']] == [-1, None]


@pytest.mark.parametrize('equal', [False, True])
@pytest.mark.parametrize('api', ['repair_group', 'contact_polish'])
def test_validation_crossing_deadline_cannot_commit_new_proposal(monkeypatch, equal, api):
    if equal:
        entry, source, target = disagreement()
        group, choice = ('u',), ('c', 'd')
    else:
        source, target, entry = nx.empty_graph(1), nx.path_graph(2), {0: [0, 1]}
        group, choice = (0,), (0,)
    force(monkeypatch, [choice])
    clock, original = [0.0], cr._Context.valid
    def checked(ctx, embedding):
        answer = original(ctx, embedding)
        if embedding is not entry:
            clock[0] = 2.0
        return answer
    monkeypatch.setattr(cr.time, 'perf_counter', lambda: clock[0])
    monkeypatch.setattr(cr._Context, 'valid', checked)
    if api == 'repair_group':
        result, info = cr.repair_group(entry, source, target, group, objective=OBJECTIVE,
                                        deadline=1.0, max_orders=1)
    else:
        monkeypatch.setattr(cr, '_groups', lambda *args: [group])
        result, info = cr.contact_polish(entry, source, target, objective=OBJECTIVE,
                                         deadline=1.0, max_groups=1, max_passes=1)
    assert result is entry and info['accepted'] == 0
    assert info['stopped_by'] == 'deadline' and info['deadline_overrun'] == 1.0
    assert info['wall'] == 2.0


def test_each_score_check_prefix_discards_partial_state_and_preserves_inputs(monkeypatch):
    entry, source, target = disagreement()
    ctx, snapshot = cr._Context(source, target), deepcopy(entry)
    complete = es.EndpointScorer(entry, ctx, ('u',))
    stages = []
    original = complete.check
    def recorded(stage):
        stages.append(stage)
        original(stage)
    monkeypatch.setattr(complete, 'check', recorded)
    expected = complete.score(entry)
    for limit in range(len(stages)):
        scorer = es.EndpointScorer(entry, ctx, ('u',))
        calls = [0]
        def truncated(stage):
            scorer._stage = stage
            if calls[0] == limit:
                raise es.ScoreDeadline(stage)
            calls[0] += 1
        monkeypatch.setattr(scorer, 'check', truncated)
        with pytest.raises(es.ScoreDeadline):
            scorer.score(entry)
        assert scorer.info['completed'] == 0 and scorer.info['interrupted'] == 1
        if stages[limit] in ('start', 'owner', 'source_edges', 'owner_complete'):
            assert scorer._owner is None
        assert entry == snapshot
    assert expected == oracle(entry, ('u',), source, target)


@pytest.mark.parametrize('chain', [[], ['x'], ['c', 'c'], ['not-a-qubit'], ['b']])
def test_invalid_owner_or_missing_contact_never_returns_a_score(chain):
    entry, source, target = disagreement()
    scorer = es.EndpointScorer(entry, cr._Context(source, target), ('u',))
    assert scorer.score(dict(entry, u=chain)) is None
    assert scorer.info['invalid'] == 1 and scorer.info['completed'] == 0


def test_actual_Z12_proxy_counterexample_is_scored_without_constructing_an_embedding():
    import dwave_networkx as dnx
    target = dnx.zephyr_graph(12)
    source = nx.Graph([('u', 'v'), ('u', 'w'), ('u', 'z')])
    fixed = dict(v=[97], w=[121], z=[2508, 204])
    a, b = dict(u=[2604, 2605, 2606], **fixed), dict(u=[96, 2544, 120], **fixed)
    scorer = es.EndpointScorer(a, cr._Context(source, target), ('u',))
    before, after = scorer.score(a), scorer.score(b)
    assert before == oracle(a, ('u',), source, target)
    assert after == oracle(b, ('u',), source, target)
    assert before['histogram'] == {1: 6} and after['histogram'] == {1: 5, 2: 1}
    assert scorer.improves(before, after)
    # These supplied chains are not deletion-minimal/proven proposer outputs.
    valid(dict(a, u=[2604]), source, target)
    valid(dict(b, u=[2604]), source, target)


def comparable(value):
    if isinstance(value, dict):
        time_keys = {'wall', 'proposal_wall', 'query_wall', 'setup_wall',
                     'refresh_wall', 'last_refresh_wall'}
        return {k: comparable(v) for k, v in value.items() if k not in time_keys}
    if isinstance(value, (tuple, list)):
        return [comparable(v) for v in value]
    return value


@pytest.fixture(scope='module')
def frozen():
    path = ROOT / 'results/codex/endpoint-support-checks/reference/contact_repair.py'
    name = 'ember_qc.algorithms.factored._endpoint_frozen_reference'
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize('objective', ['qubits', 'qubits_contacts'])
@pytest.mark.parametrize('group_policy', ['legacy', 'round_robin'])
@pytest.mark.parametrize('policies', [{}, {'singleton_policy': 'direct'},
                                      {'star_policy': 'matching'}, {'star_policy': 'connected'}])
def test_old_paths_replay_frozen_embeddings_and_every_nontime_diagnostic(frozen, objective,
                                                                      group_policy, policies):
    for seed in (2, 5):
        entry, source, target = quotient(seed)
        options = dict(objective=objective, group_policy=group_policy, group_sizes=(1, 2, 3),
                       max_passes=2, max_groups=5, max_expansions=800, group_expansions=160,
                       boundary_sites=2, beam_width=1, **policies)
        old = frozen.contact_polish(entry, source, target, **options)
        new = cr.contact_polish(entry, source, target, **options)
        assert comparable(old) == comparable(new)
        assert 'endpoint_support' not in new[1]
        valid(new[0], source, target)
