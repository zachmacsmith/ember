"""
tests/algorithms/test_attraction.py
=====================================
Tests for the attraction embedder (ember_qc.algorithms.factored.placement):
seeded routing via ``initial_chains``, the geometry primitives, and the
end-to-end pipeline (validity, determinism, registry contract).
"""
import math

import networkx as nx
import numpy as np
import pytest

from ember_qc.registry import ALGORITHM_REGISTRY, validate_embedding
from ember_qc.embedding_backend import build_adjacency
from ember_qc.algorithms.factored import (
    AttractConfig,
    RouterConfig,
    attract_embed,
    embed_factored,
)
from ember_qc.algorithms.factored.placement import (
    DensityField,
    relax,
    snap,
    source_positions,
    target_layout,
)

import dwave_networkx as dnx


@pytest.fixture(scope="module")
def chimera():
    return dnx.chimera_graph(4, 4, 4)


@pytest.fixture(scope="module")
def source():
    return nx.gnp_random_graph(12, 0.4, seed=7)


class TestSeededRouting:
    def test_initial_chains_produce_valid_embedding(self, chimera, source):
        adj = build_adjacency(chimera)
        qubits = sorted(adj)
        seeds = {v: [qubits[i * 7]] for i, v in enumerate(sorted(source.nodes()))}
        res = embed_factored(source, chimera, timeout=30, seed=0,
                             initial_chains=seeds)
        assert res["embedding"], "seeded routing failed to legalize"
        assert validate_embedding(res["embedding"], source, chimera)

    def test_bogus_seed_entries_are_ignored(self, chimera, source):
        seeds = {99999: [0], 0: [-5]}  # unknown vertex; unknown qubit
        res = embed_factored(source, chimera, timeout=30, seed=0,
                             initial_chains=seeds)
        assert res["embedding"]
        assert validate_embedding(res["embedding"], source, chimera)

    def test_seeding_is_deterministic(self, chimera, source):
        adj = build_adjacency(chimera)
        qubits = sorted(adj)
        seeds = {v: [qubits[i * 5]] for i, v in enumerate(sorted(source.nodes()))}
        a = embed_factored(source, chimera, timeout=30, seed=3,
                           initial_chains=seeds)
        b = embed_factored(source, chimera, timeout=30, seed=3,
                           initial_chains=seeds)
        assert a["embedding"] == b["embedding"]


class TestGeometry:
    def test_source_positions_inside_box(self):
        g = nx.path_graph(10)
        lo, hi = np.array([0.0, 0.0]), np.array([4.0, 2.0])
        cent = source_positions(g, lo, hi)
        for p in cent.values():
            assert np.all(p >= lo) and np.all(p <= hi)

    def test_source_positions_complete_graph_fallback(self):
        # complete graphs have degenerate spectra; the circle fallback must
        # still give distinct, in-box, finite positions
        g = nx.complete_graph(8)
        lo, hi = np.array([0.0, 0.0]), np.array([1.0, 1.0])
        cent = source_positions(g, lo, hi)
        pts = np.array(list(cent.values()))
        assert np.all(np.isfinite(pts))
        assert len({tuple(np.round(p, 9)) for p in pts}) == len(pts)

    def test_relax_moves_toward_neighbours(self):
        g = nx.path_graph(3)
        src_adj = {v: sorted(g.neighbors(v)) for v in g}
        cent = {0: np.array([0.0, 0.0]), 1: np.array([10.0, 0.0]),
                2: np.array([20.0, 0.0])}
        out = relax(cent, src_adj, eta=0.5)
        assert out[1][0] == pytest.approx(10.0)  # middle stays at its mean
        assert 0.0 < out[0][0] < 10.0            # ends pull inward

    def test_density_push_leaves_underfull_alone(self):
        coords = np.array([[float(i), float(j)] for i in range(8) for j in range(8)])
        f = DensityField(coords, bins=4)
        cent = {0: np.array([0.5, 0.5])}
        out = f.push(cent, {0: 1.0})
        assert np.allclose(out[0], cent[0])

    def test_density_push_moves_overfull(self):
        coords = np.array([[float(i), float(j)] for i in range(8) for j in range(8)])
        f = DensityField(coords, bins=4)
        # pile 20 centroids of charge 3 into one corner bin (capacity 4)
        cent = {v: np.array([0.2, 0.2]) for v in range(20)}
        out = f.push(cent, {v: 3.0 for v in cent})
        assert any(not np.allclose(out[v], cent[v]) for v in cent)

    def test_snap_distinct_qubits(self):
        coords = np.array([[float(i), 0.0] for i in range(10)])
        qubits = list(range(10))
        cent = {v: np.array([0.0, 0.0]) for v in range(5)}  # all want qubit 0
        seeds = snap(cent, coords.copy(), qubits, degree_order=list(range(5)))
        assert len(set(seeds.values())) == 5


class TestAttractEmbed:
    def test_valid_and_deterministic(self, chimera, source):
        a = attract_embed(source, chimera, timeout=60, seed=0)
        b = attract_embed(source, chimera, timeout=60, seed=0)
        assert a["embedding"], "attraction failed on an easy instance"
        assert validate_embedding(a["embedding"], source, chimera)
        assert a["embedding"] == b["embedding"]

    def test_native_arm_valid_and_deterministic(self, chimera, source):
        a = attract_embed(source, chimera, timeout=60, seed=0,
                          backend="native", polish="native")
        b = attract_embed(source, chimera, timeout=60, seed=0,
                          backend="native", polish="native")
        assert a["embedding"], "native attraction failed on an easy instance"
        assert validate_embedding(a["embedding"], source, chimera)
        assert a["embedding"] == b["embedding"]

    def test_dense_source(self, chimera):
        res = attract_embed(nx.complete_graph(8), chimera, timeout=60, seed=0)
        assert res["embedding"]
        assert validate_embedding(res["embedding"], nx.complete_graph(8), chimera)

    def test_registry_contract(self, chimera, source):
        algo = ALGORITHM_REGISTRY["attraction"]
        res = algo.embed(source, chimera, timeout=60, seed=1)
        assert res["embedding"]
        assert "time" in res
        assert validate_embedding(res["embedding"], source, chimera)

    def test_overrides_reach_router_and_config(self, chimera, source):
        res = attract_embed(source, chimera, timeout=60, seed=0,
                            outer_rounds=1, alpha=0.0, gamma=0.0)
        assert res.get("rounds", 0) <= 1
        if res["embedding"]:
            assert validate_embedding(res["embedding"], source, chimera)
