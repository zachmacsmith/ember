"""The secondary objective must be an exact count on valid source contacts."""
from copy import deepcopy

import networkx as nx
import pytest

from ember_qc.algorithms.factored import contact_repair as cr


def fixture():
    source = nx.path_graph(3)
    target = nx.Graph([(100, 101), (10, 11), (20, 21), (100, 10), (101, 20),
                       (0, 1), (0, 10), (0, 11), (1, 20), (1, 21),
                       (100, 0), (101, 1)])
    embedding = {0: [10, 11], 1: [100, 101], 2: [20, 21]}
    return embedding, source, target


def direct(embedding, selected, source, target):
    return sum(sum(target.has_edge(p, q) for p in embedding[u] for q in embedding[v]) - 1
               for u, v in source.edges if u in selected or v in selected)


def test_equal_size_relocation_increases_actual_contact_options():
    embedding, source, target = fixture()
    snapshot = deepcopy(embedding)
    original, strict = cr.repair_group(embedding, source, target, (1,), beam_width=1)
    assert original == embedding and strict['accepted'] == 0
    output, info = cr.repair_group(embedding, source, target, (1,), beam_width=1,
                                    objective='qubits_contacts')
    assert output[1] == [0, 1]
    assert output[0] == embedding[0] and output[2] == embedding[2]
    assert sum(map(len, output.values())) == sum(map(len, embedding.values()))
    assert info['equal_size_moves'] == info['accepted'] == 1
    assert info['qubits_saved'] == 0 and info['contact_redundancy_gain'] == 2
    assert embedding == snapshot
    assert cr._Context(source, target).valid(output)
    assert direct(output, {1}, source, target) - direct(embedding, {1}, source, target) == 2


@pytest.mark.parametrize('selected', [(0,), (1,), (0, 1), (0, 2), (0, 1, 2)])
def test_incident_score_agrees_with_source_edge_coupler_enumeration(selected):
    embedding, source, target = fixture()
    embedding[1] = [0, 1]
    target.add_edge(10, 20)  # Not a source edge: contributes nothing.
    ctx = cr._Context(source, target)
    assert ctx.valid(embedding)
    assert cr._contact_redundancy(embedding, selected, ctx) == direct(
        embedding, selected, source, target)


def test_repeated_rearrangement_has_strict_lexicographic_progress_and_caps():
    embedding, source, target = fixture()
    initial_q = sum(map(len, embedding.values()))
    initial_r = direct(embedding, set(source), source, target)
    output, info = cr.contact_polish(embedding, source, target, group_sizes=(1,),
                                    objective='qubits_contacts', max_passes=8, max_groups=30,
                                    max_expansions=5000, beam_width=1)
    assert cr._Context(source, target).valid(output)
    assert (sum(map(len, output.values())), -direct(output, set(source), source, target)) <= (
        initial_q, -initial_r)
    prior = initial_q
    for move in info['trajectory']:
        assert move['total_qubits'] <= prior
        if move['total_qubits'] == prior:
            assert move['equal_size_move'] and move['contact_redundancy_gain'] > 0
        prior = move['total_qubits']
    assert info['groups_tried'] <= 30 and info['expansions'] <= 5000


def test_invalid_objective_and_exhausted_budget_preserve_inputs():
    embedding, source, target = fixture()
    with pytest.raises(ValueError, match='objective'):
        cr.repair_group(embedding, source, target, (1,), objective='unknown')
    with pytest.raises(ValueError, match='objective'):
        cr.contact_polish(embedding, source, target, objective='unknown')
    output, info = cr.repair_group(embedding, source, target, (1,),
                                    objective='qubits_contacts', max_expansions=0)
    assert output == embedding and info['accepted'] == 0
