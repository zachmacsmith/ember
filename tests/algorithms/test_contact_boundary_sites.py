"""Contact-set relocation can reach sites beyond a chain's free-space halo."""
from copy import deepcopy

import networkx as nx
import pytest

from ember_qc.algorithms.factored.contact_repair import contact_polish, repair_group


@pytest.fixture
def distant_site():
    source = nx.Graph([(0, 1), (0, 2)])
    target = nx.Graph([(0, 1), (0, 10), (1, 20), (10, 11), (11, 12),
                       (20, 21), (21, 22), (12, 50), (22, 50)])
    embedding = {0: [0, 1], 1: [10, 11, 12], 2: [20, 21, 22]}
    return source, target, embedding


def verify(source, target, embedding):
    assert set(source) == set(embedding)
    occupied = set()
    for chain in embedding.values():
        assert chain and len(set(chain)) == len(chain)
        assert not occupied.intersection(chain) and set(chain) <= set(target)
        occupied.update(chain)
        assert nx.is_connected(target.subgraph(chain))
    for a, b in source.edges:
        assert any(target.has_edge(q, r) for q in embedding[a] for r in embedding[b])


def test_boundary_sites_reach_a_valid_disconnected_relocation(distant_site):
    source, target, embedding = distant_site
    original = deepcopy(embedding)
    local, local_info = repair_group(embedding, source, target, [0], boundary_sites=0)
    moved, info = repair_group(embedding, source, target, [0], boundary_sites=1)
    assert local == original and local_info['accepted'] == 0
    assert moved[0] == [50] and moved[1] == original[1] and moved[2] == original[2]
    assert info['boundary_sites_added'] == 1 and info['boundary_expansions'] > 0
    assert info['qubits_saved'] == 1 and info['expansions'] >= info['boundary_expansions']
    assert embedding == original
    verify(source, target, moved)


def test_original_region_is_preserved_under_cap_and_work_exhaustion(distant_site):
    source, target, embedding = distant_site
    for options in ({'max_region': 2}, {'max_expansions': 2}, {'deadline': -1}):
        moved, info = repair_group(embedding, source, target, [0], boundary_sites=16, **options)
        assert moved == embedding and info['boundary_sites_added'] == 0
        verify(source, target, moved)


def test_boundary_options_and_group_policy_are_explicit(distant_site):
    source, target, embedding = distant_site
    with pytest.raises(ValueError):
        repair_group(embedding, source, target, [0], boundary_sites=-1)
    with pytest.raises(ValueError):
        repair_group(embedding, source, target, [0], boundary_sites=True)
    with pytest.raises(ValueError):
        contact_polish(embedding, source, target, group_policy='source_family')
    moved, info = contact_polish(embedding, source, target, boundary_sites=16,
                                 group_policy='round_robin', group_sizes=(1, 2), max_groups=12)
    verify(source, target, moved)
    assert info['groups_tried'] <= 12 and sum(map(len, moved.values())) <= 8


def test_unsuccessful_truncated_pass_reports_its_group_limit():
    source = nx.Graph([(0, 1), (0, 2)])
    target = nx.path_graph(5)
    embedding = {0: [1, 2, 3], 1: [0], 2: [4]}
    moved, info = contact_polish(embedding, source, target, max_groups=1,
                                 max_passes=4, group_sizes=(1,))
    assert moved == embedding and info['accepted'] == 0
    assert info['groups_tried'] == 1 and info['stopped_by'] == 'group_limit'
