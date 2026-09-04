"""
tests/algorithms/test_attraction.py
=====================================
The attraction embedder end to end (s3.127): validity, determinism,
the parameter surface, the stride gate, the fallback, the registry
contract, and the fingerprints a rewrite is held to.
"""
import networkx as nx
import numpy as np
import pytest

from ember_qc.registry import ALGORITHM_REGISTRY, validate_embedding
from ember_qc.algorithms.factored import attract_embed
from ember_qc.algorithms.factored.placement import snap, target_layout

import dwave_networkx as dnx


@pytest.fixture(scope="module")
def chimera():
    return dnx.chimera_graph(4, 4, 4)


@pytest.fixture(scope="module")
def source():
    return nx.gnp_random_graph(12, 0.4, seed=7)


class TestGeometry:
    def test_snap_distinct_qubits(self):
        coords = np.array([[float(i), 0.0] for i in range(10)])
        qubits = list(range(10))
        cent = {v: np.array([0.0, 0.0]) for v in range(5)}
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
        k = nx.complete_graph(8)
        res = attract_embed(k, chimera, timeout=60, seed=0)
        assert res["embedding"]
        assert validate_embedding(res["embedding"], k, chimera)
        assert res["stair_E"] is not None

    def test_diag_surface(self, chimera, source):
        res = attract_embed(source, chimera, timeout=60, seed=0)
        d = res["diag"]
        for key in ("extent_mean", "extent_max", "stride", "max_chain",
                    "asks", "accepts", "passes", "stopped_by", "pen",
                    "stair", "bars", "accept_traj", "legal_acl",
                    "legal_max_chain", "bookmark_asks"):
            assert key in d, key
        assert d["stopped_by"] in ("fixpoint", "asks", "deadline",
                                   "passes", "trivial")

    def test_registry_contract(self, chimera, source):
        algo = ALGORITHM_REGISTRY["attraction"]
        res = algo.embed(source, chimera, timeout=60, seed=1)
        assert res["embedding"]
        assert "time" in res
        assert validate_embedding(res["embedding"], source, chimera)

    def test_unknown_kwargs_ignored_and_bad_values_fail_loudly(
            self, chimera, source):
        res = attract_embed(source, chimera, timeout=60, seed=0,
                            max_rounds=1, state="cross", gamma=0.0)
        assert res["embedding"]
        assert validate_embedding(res["embedding"], source, chimera)
        bad = attract_embed(source, chimera, timeout=5, seed=0, tail="grind")
        assert bad["status"] == "FAILURE" and "tail" in bad["error"]
        bad = attract_embed(source, chimera, timeout=5, seed=0, max_asks=0)
        assert bad["status"] == "FAILURE" and "max_asks" in bad["error"]

    def test_courses_default_on_zephyr(self):
        z = dnx.zephyr_graph(3, 4)
        k = nx.complete_graph(10)
        res = attract_embed(k, z, timeout=60, seed=0)
        assert res["embedding"], "default failed on K10/Z3"
        assert validate_embedding(res["embedding"], k, z)
        assert res["diag"]["stride"] == 2

    def test_exact_stack_default_diag_on_zephyr(self):
        z = dnx.zephyr_graph(3, 4)
        k = nx.complete_graph(10)
        a = attract_embed(k, z, timeout=60, seed=0)
        b = attract_embed(k, z, timeout=60, seed=0)
        assert a["embedding"], "default exact stack failed on K10/Z3"
        assert validate_embedding(a["embedding"], k, z)
        assert a["embedding"] == b["embedding"]
        for key in ("mm_skipped", "deficit_edges", "corner_deficit",
                    "extensions", "ext_qubits", "bridges", "certified"):
            assert key in a["diag"], key
        assert a["diag"]["extensions"] == 0
        assert a["stair_E"] is not None

    def test_fingerprint_k10_z3_certified_template(self):
        # the crystal fingerprint in miniature: K10 on Z3 converts
        # certified with no router, at the template's chain length
        z = dnx.zephyr_graph(3, 4)
        k = nx.complete_graph(10)
        r = attract_embed(k, z, timeout=60, seed=0, tail="none",
                          max_asks=2000)
        d = r["diag"]
        assert d["certified"] and d["mm_skipped"]
        assert d["pen"] == 0
        assert r["legal_acl"] == pytest.approx(1.8)
        assert d["max_chain"] == 2

    def test_stride_gate_off_zephyr(self, chimera, source):
        a = attract_embed(source, chimera, timeout=60, seed=0)
        assert a["embedding"]
        assert "mm_skipped" not in a["diag"]
        assert a["diag"]["stride"] == 1

    def test_work_budget_and_tail_none(self, chimera, source):
        # a one-ask budget still legalizes (the router does the rest)
        res = attract_embed(source, chimera, timeout=60, seed=0,
                            max_asks=1, tail="none")
        assert res["embedding"], "budget-1 run did not legalize"
        assert validate_embedding(res["embedding"], source, chimera)
        assert res["diag"]["asks"] <= 1
        assert res["diag"]["stopped_by"] == "asks"

    def test_sched_seed_is_independent_of_seed(self):
        z = dnx.zephyr_graph(3, 4)
        g = nx.gnp_random_graph(14, 0.35, seed=9)
        a = attract_embed(g, z, timeout=30, seed=0, tail="none",
                          max_asks=300)
        b = attract_embed(g, z, timeout=30, seed=0, tail="none",
                          max_asks=300, sched_seed=0)
        c = attract_embed(g, z, timeout=30, seed=0, tail="none",
                          max_asks=300, sched_seed=5)
        assert a["embedding"] == b["embedding"]
        assert validate_embedding(c["embedding"], g, z)

    def test_untyped_target_fallback(self, source):
        target = nx.convert_node_labels_to_integers(nx.grid_2d_graph(12, 12))
        res = attract_embed(nx.random_regular_graph(3, 12, seed=2), target,
                            timeout=30, seed=0)
        assert res["embedding"], "untyped-grid fallback failed"
        assert res["diag"]["stopped_by"] == "trivial"

    def test_isolated_vertices_survive(self, chimera):
        g = nx.gnp_random_graph(10, 0.4, seed=3)
        g.add_nodes_from([100, 101])  # isolated
        res = attract_embed(g, chimera, timeout=60, seed=0)
        assert res["embedding"]
        assert 100 in res["embedding"] and 101 in res["embedding"]
        assert validate_embedding(res["embedding"], g, chimera)

    def test_zephyr_and_pegasus_valid(self, source):
        for target in (dnx.zephyr_graph(3, 4), dnx.pegasus_graph(4)):
            r = attract_embed(source, target, timeout=60, seed=0)
            assert r["embedding"], f"failed on {target.graph.get('family')}"
            assert validate_embedding(r["embedding"], source, target)

    def test_positions_are_integer_line_indices(self, source):
        from ember_qc.algorithms.factored import plane
        from ember_qc.algorithms.factored.field import TileGrid
        target = dnx.zephyr_graph(3, 4)
        grid = TileGrid(target, target_layout(target), courses=True)
        src_adj = {v: sorted(source.neighbors(v)) for v in source}
        pos, bk, info = plane.arrange(src_adj, grid, seed=0, max_asks=200,
                                      snap=True)
        for v, p in pos.items():
            assert float(p[0]).is_integer() and float(p[1]).is_integer()
            assert 0 <= p[0] <= grid.W - 1
