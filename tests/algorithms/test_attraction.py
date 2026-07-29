"""
tests/algorithms/test_attraction.py
=====================================
Tests for the attraction embedder (ember_qc.algorithms.factored.placement),
post-consolidation (one pipeline: stair attraction + alternating arrangement
+ wire seeds + minorminer legalize/polish): seeded routing via
``initial_chains``, the geometry primitives, and the end-to-end pipeline
(validity, determinism, registry contract).
"""
import networkx as nx
import numpy as np
import pytest

from ember_qc.registry import ALGORITHM_REGISTRY, validate_embedding
from ember_qc.embedding_backend import build_adjacency
from ember_qc.algorithms.factored import (
    AttractConfig,
    attract_embed,
    embed_factored,
)
from ember_qc.algorithms.factored.placement import (
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

    def test_snap_distinct_qubits(self):
        coords = np.array([[float(i), 0.0] for i in range(10)])
        qubits = list(range(10))
        cent = {v: np.array([0.0, 0.0]) for v in range(5)}  # all want qubit 0
        seeds = snap(cent, coords.copy(), qubits, degree_order=list(range(5)))
        assert len(set(seeds.values())) == 5

    def test_target_layout_native_and_fallback(self, chimera):
        pos = target_layout(chimera)
        assert set(pos) == set(chimera.nodes())
        plain = nx.convert_node_labels_to_integers(nx.grid_2d_graph(4, 4))
        pos2 = target_layout(plain)
        assert set(pos2) == set(plain.nodes())


class TestAttractEmbed:
    def test_valid_and_deterministic(self, chimera, source):
        a = attract_embed(source, chimera, timeout=60, seed=0)
        b = attract_embed(source, chimera, timeout=60, seed=0)
        assert a["embedding"], "attraction failed on an easy instance"
        assert validate_embedding(a["embedding"], source, chimera)
        assert a["embedding"] == b["embedding"]

    def test_dense_source(self, chimera):
        res = attract_embed(nx.complete_graph(8), chimera, timeout=60, seed=0)
        assert res["embedding"]
        assert validate_embedding(res["embedding"], nx.complete_graph(8), chimera)

    def test_dense_source_engages_arrangement(self, chimera):
        # deg > kappa forces participation: the dense machinery must engage
        k = nx.complete_graph(16)
        res = attract_embed(k, chimera, timeout=60, seed=0)
        assert res["embedding"]
        assert validate_embedding(res["embedding"], k, chimera)
        assert res["diag"]["assigned"] == 16
        assert res["round_E"], "stair energy trajectory missing"

    def test_sparse_source_is_capacity_gated(self, chimera, source):
        # every deg <= kappa: no participants, the arrangement must be inert
        res = attract_embed(source, chimera, timeout=60, seed=0)
        assert res["diag"]["assigned"] == 0

    def test_registry_contract(self, chimera, source):
        algo = ALGORITHM_REGISTRY["attraction"]
        res = algo.embed(source, chimera, timeout=60, seed=1)
        assert res["embedding"]
        assert "time" in res
        assert validate_embedding(res["embedding"], source, chimera)

    def test_overrides_reach_config_and_unknowns_ignored(self, chimera, source):
        # unknown kwargs (including pre-consolidation knobs) are ignored
        res = attract_embed(source, chimera, timeout=60, seed=0,
                            max_rounds=1, state="cross", gamma=0.0)
        assert res.get("rounds", 0) <= 1
        if res["embedding"]:
            assert validate_embedding(res["embedding"], source, chimera)

    def test_round_acls_diagnostic(self, chimera, source):
        res = attract_embed(source, chimera, timeout=60, seed=0, max_rounds=3)
        acls = res["round_acls"]
        assert isinstance(acls, list) and 1 <= len(acls) <= 3
        assert any(a is not None for a in acls)
        assert res["legal_acl"] is not None

    def test_vary_rng_false_deterministic(self, chimera, source):
        a = attract_embed(source, chimera, timeout=60, seed=2,
                          vary_rng=False, max_rounds=3)
        b = attract_embed(source, chimera, timeout=60, seed=2,
                          vary_rng=False, max_rounds=3)
        assert a["embedding"] and a["embedding"] == b["embedding"]
        assert a["round_acls"] == b["round_acls"]

    def test_wire_exact_valid_and_reports_metric(self, chimera):
        k = nx.complete_graph(10)
        res = attract_embed(k, chimera, timeout=60, seed=0, wire_exact=True)
        assert res["embedding"], "wire_exact arm failed on K10"
        assert validate_embedding(res["embedding"], k, chimera)
        assert "designated" in res["diag"]

    def test_feasibility_fallback(self, chimera, source):
        # round_frac=0 exhausts the rounds budget instantly: the rounds loop
        # never runs and the uncapped fallback must still legalize.
        res = attract_embed(source, chimera, timeout=60, seed=0,
                            round_frac=0.0)
        assert res["embedding"], "fallback did not legalize an easy instance"
        assert validate_embedding(res["embedding"], source, chimera)
        assert res["rounds"] == 1  # the fallback attempt only
        assert len(res["round_acls"]) == 1

    def test_untyped_target_fallback(self, source):
        target = nx.convert_node_labels_to_integers(nx.grid_2d_graph(12, 12))
        res = attract_embed(nx.random_regular_graph(3, 12, seed=2), target,
                            timeout=30, seed=0)
        assert res["embedding"], "untyped-grid fallback failed"

    def test_isolated_vertices_survive(self, chimera):
        g = nx.gnp_random_graph(10, 0.4, seed=3)
        g.add_nodes_from([100, 101])  # isolated
        res = attract_embed(g, chimera, timeout=60, seed=0)
        assert res["embedding"]
        assert 100 in res["embedding"] and 101 in res["embedding"]
        assert validate_embedding(res["embedding"], g, chimera)
