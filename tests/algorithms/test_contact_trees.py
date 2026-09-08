"""Contact-tree mechanism, admissible bound, and shared-budget invariants."""
from collections import defaultdict
from copy import deepcopy
from itertools import combinations
import time

import networkx as nx
import pytest

from ember_qc.algorithms.factored.contact_repair import _Budget, _Context, _grow
from ember_qc.algorithms.factored.contact_trees import _prepare, grow_contact_tree


def verify(tree, root, available, masks, required, target, cap):
    assert tree is not None and root in tree and tree <= available
    assert 1 <= len(tree) <= cap and nx.is_connected(target.subgraph(tree))
    covered = 0
    for q in tree:
        covered |= masks.get(q, 0)
    assert covered & required == required


def misleading_nearest_contact():
    # Contact A can be reached immediately at 1, or incidentally at 3 on the
    # route to B or C. Taking the first A makes a redundant physical branch.
    target = nx.Graph([(0, 1), (0, 2), (2, 3), (3, 4), (3, 5)])
    masks = {1: 1, 3: 1, 4: 2, 5: 4}
    return target, set(target), masks, _Context(nx.Graph(), target)


def test_distance_priority_recovers_a_missed_greedy_tree_at_width_one():
    target, available, masks, ctx = misleading_nearest_contact()
    greedy_budget = _Budget(1000, None)
    assert _grow(0, available, masks, 7, ctx, greedy_budget, 5) is None
    stats = {}
    budget = _Budget(1000, None)
    tree = grow_contact_tree(0, available, masks, 7, ctx, budget, 5,
                             frontier_width=1, diagnostics=stats)
    assert tree == frozenset((0, 2, 3, 4, 5))
    assert stats['initial_bound'] == 3
    assert stats['states_expanded'] >= 2 and stats['frontier_peak'] == 1
    verify(tree, 0, available, masks, 7, target, 5)


def test_distance_policy_integrates_with_atomic_group_reconstruction(monkeypatch):
    from ember_qc.algorithms.factored import contact_repair as cr
    target, _, _, _ = misleading_nearest_contact()
    target.add_edges_from([(100, 1), (100, 3), (200, 4), (300, 5)])
    source = nx.star_graph(3)
    incumbent = {0: list(range(6)), 1: [100], 2: [200], 3: [300]}
    original = deepcopy(incumbent)

    def prohibited_greedy(*args, **kwargs):
        raise AssertionError('Distance policy called the other tree builder')

    monkeypatch.setattr(cr, '_grow', prohibited_greedy)
    output, info = cr.contact_polish(incumbent, source, target, tree_policy='distance',
                                    group_sizes=(1,), beam_width=1, max_groups=1,
                                    max_expansions=1000)
    assert len(output[0]) < 6 and info['qubits_saved'] > 0
    assert incumbent == original
    assert all(output[v] == incumbent[v] for v in (1, 2, 3))
    occupied = set()
    for chain in output.values():
        assert nx.is_connected(target.subgraph(chain)) and not occupied.intersection(chain)
        occupied.update(chain)
    assert all(any(target.has_edge(p, q) for p in output[u] for q in output[v])
               for u, v in source.edges())
    assert info['tree_search']['states_prepared'] > 0
    assert info['tree_search']['frontier_peak'] == 1
    assert info['tree_search']['bfs_expansions'] <= info['expansions'] <= 1000
    with pytest.raises(ValueError, match='tree policy'):
        cr.contact_polish(incumbent, source, target, tree_policy='unknown')


def test_distinct_contact_masks_can_share_the_small_frontier():
    target = nx.star_graph(3)
    available, masks = set(target), {1: 1, 2: 2, 3: 4}
    stats = {}
    tree = grow_contact_tree(0, available, masks, 7, _Context(nx.Graph(), target),
                             _Budget(1000, None), 4, frontier_width=2, diagnostics=stats)
    verify(tree, 0, available, masks, 7, target, 4)
    assert stats['coverage_peak'] == 2 and stats['frontier_peak'] <= 2


@pytest.mark.parametrize('partial', [{0}, {0, 1}, {0, 1, 3}])
def test_distance_estimate_is_admissible_for_connected_extensions(partial):
    target = nx.cycle_graph(6)
    target.add_edges_from([(0, 3), (1, 4)])
    available, masks, required = set(target), {2: 1, 3: 2, 4: 1, 5: 4}, 7
    covered = 0
    for q in partial:
        covered |= masks.get(q, 0)
    stats = defaultdict(int)
    state = _prepare(frozenset(partial), covered, available, masks, required,
                     _Context(nx.Graph(), target), _Budget(1000, None), len(target),
                     2, False, stats)
    assert state is not None
    missing_bits = [bit for bit in (1, 2, 4) if not covered & bit]
    expected = max(min(nx.shortest_path_length(target, q, r)
                       for q in partial for r in target if masks.get(r, 0) & bit)
                   for bit in missing_bits)
    assert state.bound == expected
    minimum_added = None
    free = list(available - partial)
    for count in range(len(free) + 1):
        for addition in combinations(free, count):
            candidate = partial | set(addition)
            mask = 0
            for q in candidate:
                mask |= masks.get(q, 0)
            if mask & required == required and nx.is_connected(target.subgraph(candidate)):
                minimum_added = count
                break
        if minimum_added is not None:
            break
    assert minimum_added is not None and state.bound <= minimum_added


@pytest.mark.parametrize('limit', [0, 1, 3])
def test_work_exhaustion_does_not_return_partial_trees_or_mutate_inputs(limit):
    target, available, masks, ctx = misleading_nearest_contact()
    before = deepcopy((available, masks, ctx.adj))
    budget, stats = _Budget(limit, None), {}
    assert grow_contact_tree(0, available, masks, 7, ctx, budget, 5,
                              diagnostics=stats) is None
    assert budget.expansions <= limit and stats['bfs_expansions'] == budget.expansions
    assert (available, masks, ctx.adj) == before


def test_expired_deadline_and_impossible_size_cap_return_no_tree():
    target = nx.path_graph(4)
    available, masks, ctx = set(target), {3: 1}, _Context(nx.Graph(), target)
    expired = _Budget(1000, time.perf_counter() - 1)
    assert grow_contact_tree(0, available, masks, 1, ctx, expired, 4) is None
    assert expired.expansions == 0 and expired.stopped_by == 'deadline'
    stats = {}
    assert grow_contact_tree(0, available, masks, 1, ctx, _Budget(1000, None), 3,
                              diagnostics=stats) is None
    assert stats['distance_pruned'] == 1


def test_unavailable_contact_is_not_routed_through_frozen_space():
    target = nx.path_graph(3)
    stats = {}
    tree = grow_contact_tree(0, {0, 1}, {2: 1}, 1, _Context(nx.Graph(), target),
                             _Budget(1000, None), 3, diagnostics=stats)
    assert tree is None and stats['unreachable_pruned'] == 1


def test_completed_tree_survives_a_subsequent_deadline(monkeypatch):
    target, available, masks, ctx = misleading_nearest_contact()
    stats, budget = {}, _Budget(1000, None)
    real_check = budget.check

    def expires_after_completion():
        if stats.get('completed_trees', 0):
            budget.stopped_by = 'deadline'
            return False
        return real_check()

    monkeypatch.setattr(budget, 'check', expires_after_completion)
    tree = grow_contact_tree(0, available, masks, 7, ctx, budget, 5,
                             frontier_width=2, diagnostics=stats)
    verify(tree, 0, available, masks, 7, target, 5)
    assert budget.stopped_by == 'deadline'


def test_mixed_target_labels_and_insertion_order_are_deterministic():
    target, _available, masks, _ctx = misleading_nearest_contact()
    labels = {0: ('root', 0), 1: 'near', 2: 9, 3: 'branch', 4: ('end', 1), 5: -3}
    target = nx.relabel_nodes(target, labels)
    masks = {labels[q]: value for q, value in masks.items()}
    available, root = set(target), labels[0]
    first_stats = {}
    first = grow_contact_tree(root, available, masks, 7, _Context(nx.Graph(), target),
                               _Budget(1000, None), 5, diagnostics=first_stats)
    reverse = nx.Graph()
    reverse.add_nodes_from(reversed(list(target)))
    reverse.add_edges_from((b, a) for a, b in reversed(list(target.edges())))
    second_stats = {}
    second = grow_contact_tree(root, available, masks, 7, _Context(nx.Graph(), reverse),
                                _Budget(1000, None), 5, diagnostics=second_stats)
    assert first == second and first_stats == second_stats
    verify(first, root, available, masks, 7, target, 5)


def test_root_already_covering_contacts_needs_no_bfs():
    target = nx.path_graph(2)
    budget = _Budget(10, None)
    tree = grow_contact_tree(0, set(target), {0: 15}, 3, _Context(nx.Graph(), target), budget, 1)
    assert tree == frozenset((0,)) and budget.expansions == 0


@pytest.mark.parametrize('options', [{'frontier_width': 0}, {'frontier_width': True},
                                    {'witnesses_per_contact': 0}])
def test_invalid_search_bounds_are_rejected(options):
    target = nx.path_graph(2)
    with pytest.raises(ValueError):
        grow_contact_tree(0, set(target), {1: 1}, 1, _Context(nx.Graph(), target),
                          _Budget(10, None), 2, **options)


@pytest.mark.parametrize('required,cap', [(-1, 2), (1, float('nan'))])
def test_invalid_masks_and_noninteger_caps_cannot_escape_budget_semantics(required, cap):
    target = nx.path_graph(2)
    with pytest.raises(ValueError):
        grow_contact_tree(0, set(target), {1: 1}, required, _Context(nx.Graph(), target),
                          _Budget(10, None), cap)
