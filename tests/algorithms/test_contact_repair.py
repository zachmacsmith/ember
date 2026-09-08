"""Physical invariants and a coordinated move, with no external embedder."""
import builtins
from copy import deepcopy
import random
import time

import networkx as nx
import pytest

from ember_qc.algorithms.factored.contact_repair import contact_polish, repair_group


def valid(embedding, source, target):
    """Independent straightforward graph oracle, not the production checker."""
    assert set(embedding) == set(source)
    occupied = []
    for chain in embedding.values():
        assert chain and len(set(chain)) == len(chain)
        assert set(chain) <= set(target)
        assert nx.is_connected(target.subgraph(chain))
        occupied.extend(chain)
    assert len(occupied) == len(set(occupied))
    for u, v in source.edges():
        assert any(target.has_edge(a, b) for a in embedding[u] for b in embedding[v])


@pytest.fixture
def coordinated():
    # A's one-qubit chain occupies the shortcut B needs. B cannot shrink while
    # A is frozen. Moving A to {5,6} grows it by one but lets B shrink by three.
    # With A built first, beam width one retains A={0} and loses the useful
    # prefix. A wider beam can keep A={5,6} until B is reconstructed.
    source = nx.Graph([(0, 1), (0, 2), (0, 3), (1, 4), (1, 5)])
    target = nx.Graph([
        (1, 2), (2, 3), (3, 4), (0, 1),
        (0, 10), (0, 11), (0, 12), (0, 13), (1, 12), (4, 13),
        (5, 6), (5, 10), (6, 11), (6, 0),
    ])
    embedding = {0: [0], 1: [1, 2, 3, 4], 2: [10], 3: [11], 4: [12], 5: [13]}
    valid(embedding, source, target)
    return embedding, source, target


def test_beam_keeps_a_prefix_that_enables_net_group_gain(coordinated):
    embedding, source, target = coordinated
    snapshot = deepcopy(embedding)
    one, greedy = repair_group(embedding, source, target, (0, 1),
                                beam_width=1, max_orders=1)
    joint, info = repair_group(embedding, source, target, (0, 1),
                               beam_width=4, max_orders=1)
    assert one == snapshot and greedy["accepted"] == 0
    assert info["accepted"] == 1
    assert info["qubits_saved"] == 2 and info["member_growth"] == 1
    assert len(joint[0]) == 2 and len(joint[1]) == 1
    assert embedding == snapshot
    for v in (2, 3, 4, 5):
        assert joint[v] == snapshot[v]
    valid(joint, source, target)


def test_single_chain_replacements_cannot_improve_this_incumbent(coordinated):
    embedding, source, target = coordinated
    for vertex in source:
        output, info = repair_group(embedding, source, target, [vertex])
        assert output == embedding
        assert info["accepted"] == 0
    # This is also a structural fixture: A and the four frozen chains already
    # have length one. With A frozen, B must connect 1 to 4 through 2 and 3.
    free_for_b = set(target) - {q for v, c in embedding.items() if v != 1 for q in c}
    assert nx.shortest_path_length(target.subgraph(free_for_b), 1, 4) == 3


def test_polish_is_one_valid_monotone_state_and_records_growth(coordinated):
    embedding, source, target = coordinated
    output, info = contact_polish(embedding, source, target, max_groups=20,
                                  max_expansions=10000, group_sizes=(2,))
    valid(output, source, target)
    assert info["accepted"] >= 1
    assert info["qubits_saved"] >= 2
    counts = [sum(map(len, embedding.values()))]
    counts.extend(row["total_qubits"] for row in info["trajectory"])
    assert all(a > b for a, b in zip(counts, counts[1:]))
    assert info["expansions"] <= 10000


@pytest.mark.parametrize("options,reason", [
    ({"max_expansions": 0}, "work_limit"),
    ({"max_expansions": 1}, "work_limit"),
    ({"deadline": -1}, "deadline"),
    ({"max_region": 4}, "region_limit"),
])
def test_exhaustion_rolls_back_atomically(coordinated, options, reason):
    embedding, source, target = coordinated
    before = deepcopy(embedding)
    output, info = repair_group(embedding, source, target, (0, 1), **options)
    assert output == before and embedding == before
    assert info["accepted"] == 0 and info["stopped_by"] == reason
    if "max_expansions" in options:
        assert info["expansions"] <= options["max_expansions"]
    valid(output, source, target)


@pytest.mark.parametrize("bad", [
    {0: [999]}, {0: [0], 7: [2]}, {0: [0, 0]}, {0: []}, {0: [0, 2]},
])
def test_invalid_incumbents_are_not_treated_as_valid(bad):
    source, target = nx.empty_graph(1), nx.path_graph(3)
    snapshot = deepcopy(bad)
    output, info = repair_group(bad, source, target, (0,))
    assert output == snapshot and bad == snapshot
    assert info["invalid_input"] and info["accepted"] == 0


def test_isolates_and_labels_are_preserved():
    source = nx.empty_graph(["isolated"])
    target = nx.path_graph(["q0", "q1", "q2"])
    embedding = {"isolated": ["q0", "q1", "q2"]}
    output, info = repair_group(embedding, source, target, ("isolated",))
    assert info["qubits_saved"] == 2
    valid(output, source, target)


def test_no_external_embedder_is_loaded_at_runtime(coordinated, monkeypatch):
    original_import = builtins.__import__

    def guarded(name, *args, **kwargs):
        assert "minorminer" not in name and "busclique" not in name
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", guarded)
    embedding, source, target = coordinated
    output, info = contact_polish(embedding, source, target, max_groups=5,
                                  max_expansions=5000)
    assert info["accepted"]
    valid(output, source, target)


def test_repeated_bounded_runs_are_deterministic(coordinated):
    embedding, source, target = coordinated
    first, ia = contact_polish(embedding, source, target, max_groups=10)
    second, ib = contact_polish(embedding, source, target, max_groups=10)
    assert first == second
    for key in ("accepted", "qubits_saved", "expansions", "tree_attempts", "trajectory"):
        assert ia[key] == ib[key]


def test_small_random_quotient_embeddings_preserve_physical_invariants():
    rng = random.Random(17)
    for seed in range(8):
        target = nx.gnp_random_graph(24, 0.16, seed=seed)
        # The path guarantees connectivity of each independently made block.
        target.add_edges_from((q, q + 1) for q in range(23))
        cuts = sorted(rng.sample(range(1, 24), 5))
        bounds = [0, *cuts, 24]
        embedding = {v: list(range(a, b)) for v, (a, b)
                     in enumerate(zip(bounds, bounds[1:]))}
        owner = {q: v for v, chain in embedding.items() for q in chain}
        source = nx.empty_graph(6)
        source.add_edges_from((owner[a], owner[b]) for a, b in target.edges()
                              if owner[a] != owner[b])
        before = deepcopy(embedding)
        output, info = contact_polish(embedding, source, target,
                                      max_groups=8, max_expansions=8000)
        valid(output, source, target)
        assert sum(map(len, output.values())) <= sum(map(len, embedding.values()))
        assert embedding == before
        assert info["groups_tried"] <= 8 and info["expansions"] <= 8000


def test_expired_polish_deadline_does_not_change_incumbent(coordinated):
    embedding, source, target = coordinated
    output, info = contact_polish(embedding, source, target,
                                  deadline=time.perf_counter() - 1)
    assert output == embedding
    assert info["stopped_by"] == "deadline" and info["groups_tried"] == 0


def test_rejects_unbounded_or_invalid_parameters(coordinated):
    embedding, source, target = coordinated
    for options in ({"beam_width": 0}, {"halo": -1}, {"max_orders": 0},
                    {"max_expansions": -1}):
        with pytest.raises(ValueError):
            repair_group(embedding, source, target, (0, 1), **options)
