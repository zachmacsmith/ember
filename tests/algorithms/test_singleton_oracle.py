"""Exhaustive original-graph oracle for singleton proposals on small minors."""
from copy import deepcopy
import random

import networkx as nx
import pytest

from ember_qc.algorithms.factored.contact_repair import _Budget, _Context
from ember_qc.algorithms.factored.singleton_relocation import (
    build_singleton_cache, direct_singleton,
)


def valid(embedding, source, target):
    if set(embedding) != set(source):
        return False
    occupied = set()
    for chain in embedding.values():
        if (not chain or len(set(chain)) != len(chain) or not set(chain) <= set(target)
                or occupied.intersection(chain)
                or not nx.is_connected(target.subgraph(chain))):
            return False
        occupied.update(chain)
    return all(any(target.has_edge(p, q) for p in embedding[v] for q in embedding[w])
               for v, w in source.edges())


def redundancy(embedding, source, target):
    return sum(sum(target.has_edge(p, q) for p in embedding[v] for q in embedding[w]) - 1
               for v, w in source.edges())


@pytest.mark.parametrize('seed', range(24))
def test_untruncated_proposals_match_exhaustive_original_graph_oracle(seed):
    rng = random.Random(73000 + seed)
    target = nx.gnp_random_graph(18, (0.1, 0.25, 0.45)[seed % 3], seed=seed)
    physical = list(target)
    rng.shuffle(physical)
    embedding = {}
    index = 0
    for v in range(5):
        length = rng.randint(1, 3)
        chain = physical[index:index + length]
        index += length
        embedding[v] = chain
        target.add_edges_from(zip(chain, chain[1:]))
    # Choose only edges supported by the connected, disjoint input chains.
    # Physical sites after `index` stay free and may supply new replacements.
    source = nx.Graph()
    source.add_nodes_from(embedding)
    for v in embedding:
        for w in range(v):
            if (rng.random() < 0.8
                    and any(target.has_edge(p, q) for p in embedding[v] for q in embedding[w])):
                source.add_edge(v, w)
    assert valid(embedding, source, target)
    original = deepcopy(embedding)
    ctx = _Context(source, target)
    cache = build_singleton_cache(embedding, ctx, _Budget(10000, None))
    old_q = sum(map(len, embedding.values()))
    old_r = redundancy(embedding, source, target)

    for objective in ('qubits', 'qubits_contacts'):
        for v in source:
            eligible = {}
            for q in target:
                trial = dict(embedding)
                trial[v] = [q]
                if not valid(trial, source, target):
                    continue
                new_q = sum(map(len, trial.values()))
                new_r = redundancy(trial, source, target)
                if new_q < old_q or (objective == 'qubits_contacts'
                                     and new_q == old_q and new_r > old_r):
                    eligible[q] = new_r

            site, info = direct_singleton(embedding, ctx, v, cache,
                                          _Budget(10000, None), objective)
            assert info['complete'], info
            if not eligible:
                assert site is None
            else:
                assert site in eligible
                assert eligible[site] == max(eligible.values())
                assert info['qubits_saved'] == len(embedding[v]) - 1
                assert info['contact_redundancy_gain'] == eligible[site] - old_r
            assert embedding == original
            assert cache.valid and cache.embedding is embedding
