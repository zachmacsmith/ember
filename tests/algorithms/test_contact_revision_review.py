"""Independent checks of revision 016 contact obligations and timing reports."""
from copy import deepcopy

import dwave_networkx as dnx
import networkx as nx
import pytest

from ember_qc.algorithms.factored import contact_repair as cr
from ember_qc.algorithms.factored.native import native_embed


def verify(embedding, source, target):
    assert set(embedding) == set(source)
    occupied = set()
    for chain in embedding.values():
        assert chain and len(chain) == len(set(chain))
        assert set(chain) <= set(target) and not occupied.intersection(chain)
        assert nx.is_connected(target.subgraph(chain))
        occupied.update(chain)
    for a, b in source.edges():
        assert any(target.has_edge(q, r) for q in embedding[a] for r in embedding[b])


def two_relocations():
    source = nx.Graph([(0, 1), (0, 2), (0, 3), (1, 4), (1, 5)])
    target = nx.Graph([
        (0, 1), (2, 3), (1, 2),
        (10, 11), (12, 13), (20, 21), (22, 23),
        (0, 10), (1, 12), (2, 20), (3, 22),
        (100, 11), (100, 13), (200, 21), (200, 23),
    ])
    embedding = {0: [0, 1], 1: [2, 3], 2: [10, 11], 3: [12, 13],
                 4: [20, 21], 5: [22, 23]}
    verify(embedding, source, target)
    return embedding, source, target


def test_boundary_sites_do_not_erase_contacts_between_selected_chains():
    embedding, source, target = two_relocations()
    # Each new site satisfies its frozen contacts. They do not contact each
    # other or the other selected old chain, so neither individual nor joint
    # singleton replacement is valid.
    assert not target.has_edge(100, 200)
    output, info = cr.repair_group(embedding, source, target, (0, 1),
                                    boundary_sites=16, beam_width=4)
    assert info['boundary_sites_added'] == 2
    assert info['accepted'] == 0 and output == embedding
    verify(output, source, target)


def test_a_frozen_owner_excludes_an_otherwise_complete_boundary_site():
    source = nx.Graph([(0, 1), (0, 2)])
    source.add_node(3)
    target = nx.Graph([(0, 1), (0, 10), (1, 20), (10, 11), (20, 21),
                       (11, 50), (21, 50)])
    embedding = {0: [0, 1], 1: [10, 11], 2: [20, 21], 3: [50]}
    verify(embedding, source, target)
    output, info = cr.repair_group(embedding, source, target, (0,), boundary_sites=16)
    assert info['boundary_sites_added'] == 0 and output == embedding
    verify(output, source, target)


def test_boundary_site_ties_are_stable_with_mixed_labels_and_reversed_insertion():
    source = nx.Graph([(0, 1), (0, 2)])
    target = nx.Graph([(0, 1), (0, 10), (1, 20), (10, 11), (20, 21),
                       (11, 50), (21, 50), (11, 60), (21, 60)])
    source_map = {0: ('source', 0), 1: 'left', 2: 7}
    target_map = {50: ('remote', 0), 60: 'remote'}
    source = nx.relabel_nodes(source, source_map)
    target = nx.relabel_nodes(target, target_map)
    embedding = {source_map[0]: [0, 1], source_map[1]: [10, 11], source_map[2]: [20, 21]}
    center = source_map[0]
    first, first_info = cr.repair_group(embedding, source, target, (center,), boundary_sites=1)
    assert first[center] == ['remote']
    reversed_source, reversed_target = nx.Graph(), nx.Graph()
    reversed_source.add_nodes_from(reversed(list(source)))
    reversed_source.add_edges_from((b, a) for a, b in reversed(list(source.edges())))
    reversed_target.add_nodes_from(reversed(list(target)))
    reversed_target.add_edges_from((b, a) for a, b in reversed(list(target.edges())))
    reversed_source.graph['family'] = 'unused metadata'
    reversed_embedding = {v: list(reversed(chain))
                          for v, chain in reversed(list(embedding.items()))}
    second, second_info = cr.repair_group(reversed_embedding, reversed_source, reversed_target,
                                          (center,), boundary_sites=1)
    assert {v: frozenset(chain) for v, chain in first.items()} == {
        v: frozenset(chain) for v, chain in second.items()}
    for key in ('expansions', 'boundary_expansions', 'boundary_sites_added', 'qubits_saved'):
        assert first_info[key] == second_info[key]
    verify(first, source, target)
    verify(second, reversed_source, reversed_target)


@pytest.mark.parametrize('work_limit', [1, 7, 25, 80])
def test_boundary_scans_share_the_global_reconstruction_work_cap(work_limit):
    embedding, source, target = two_relocations()
    snapshot = deepcopy(embedding)
    output, info = cr.contact_polish(
        embedding, source, target, group_policy='round_robin', group_sizes=(1, 2, 3),
        boundary_sites=16, max_groups=7, max_passes=2, max_expansions=work_limit,
        group_expansions=11, max_region=16)
    assert 0 <= info['boundary_expansions'] <= info['expansions'] <= work_limit
    assert info['groups_tried'] <= 7 and info['max_region_size'] <= 16
    assert embedding == snapshot
    assert sum(map(len, output.values())) <= sum(map(len, snapshot.values()))
    verify(output, source, target)


@pytest.mark.parametrize('api', ['repair_group', 'contact_polish'])
def test_final_validation_crossing_deadline_is_reported_truthfully(monkeypatch, api):
    clock = [0.0]
    real_valid = cr._Context.valid

    def validate(self, embedding):
        valid = real_valid(self, embedding)
        if valid and sum(map(len, embedding.values())) == 1:
            clock[0] = 2.0  # Full validation has crossed the fixed deadline.
        return valid

    monkeypatch.setattr(cr.time, 'perf_counter', lambda: clock[0])
    monkeypatch.setattr(cr._Context, 'valid', validate)
    source, target = nx.empty_graph(1), nx.path_graph(2)
    if api == 'contact_polish':
        output, info = cr.contact_polish(
            {0: [0, 1]}, source, target, deadline=1.0, max_passes=1,
            max_groups=1, group_sizes=(1,), group_policy='round_robin', boundary_sites=16)
    else:
        output, info = cr.repair_group(
            {0: [0, 1]}, source, target, (0,), deadline=1.0, boundary_sites=16)
    verify(output, source, target)
    assert info['accepted'] == 1  # A valid incumbent can survive a late return.
    assert info['wall'] == 2.0 and info['deadline_overrun'] == 1.0
    assert info['stopped_by'] == 'deadline'


def test_native_outer_deadline_guard_does_not_report_late_polish_as_success(monkeypatch):
    clock = [0.0]
    calls = []

    def polish_late(embedding, source, target, **options):
        calls.append(options)
        verify(embedding, source, target)
        clock[0] = 2.0
        return embedding, {'wall': 2.0, 'stopped_by': 'deadline'}

    monkeypatch.setattr(cr.time, 'perf_counter', lambda: clock[0])
    monkeypatch.setattr(cr, 'contact_polish', polish_late)
    source, target = nx.complete_graph(4), dnx.zephyr_graph(3)
    result = native_embed(source, target, construction='packed', timeout=1.0,
                          polish_passes=1, polish_boundary_sites=16,
                          polish_group_policy='round_robin',
                          polish_objective='qubits_contacts', polish_tree_policy='distance')
    assert len(calls) == 1
    assert calls[0]['boundary_sites'] == 16 and calls[0]['group_policy'] == 'round_robin'
    assert calls[0]['objective'] == 'qubits_contacts' and calls[0]['tree_policy'] == 'distance'
    assert result['status'] == 'TIMEOUT' and not result['success']
    assert result['diag']['deadline_overrun'] == 1.0
    verify(result['embedding'], source, target)
