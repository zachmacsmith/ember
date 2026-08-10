"""
tests/algorithms/test_attraction.py
=====================================
Tests for the attraction embedder (ember_qc.algorithms.factored.placement),
post-consolidation-2 (one code path: contraction + alternating arrangement
+ snap-aimed wire seeds + exactness completion on stride>1 fabrics +
minorminer legalize/polish): seeded routing via ``initial_chains``, the
geometry primitives, and the end-to-end pipeline (validity, determinism,
stride gating, registry contract).
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
        # vcycle=False: this test pins the ARRANGE engagement mechanism;
        # the coarse init compacts K16 below full participation (s3.66)
        res = attract_embed(k, chimera, timeout=60, seed=0, vcycle=False)
        assert res["embedding"]
        assert validate_embedding(res["embedding"], k, chimera)
        assert res["diag"]["assigned"] == 16
        assert res["stair_E"] is not None

    def test_diag_reports_arm_gating_fields(self, chimera, source):
        # participation is arm-length (per axis) since the 2026-07-29
        # refinement; the mechanism itself is unit-tested in test_field
        # (TestArmLengthGating) — here just assert the diagnostics surface
        res = attract_embed(source, chimera, timeout=60, seed=0)
        d = res["diag"]
        for key in ("assigned", "assigned_rows", "assigned_cols",
                    "insert_reverts", "mono_time"):
            assert key in d
        assert d["assigned"] <= len(source)

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
        assert "stair_E" in res or res["embedding"]
        if res["embedding"]:
            assert validate_embedding(res["embedding"], source, chimera)

    def test_courses_default_on_zephyr(self):
        # course-resolved wires (s3.49) are the default since consolidation
        # 2; courses=False is the folded control arm
        import dwave_networkx as dnx
        z = dnx.zephyr_graph(3, 4)
        k = nx.complete_graph(10)
        res = attract_embed(k, z, timeout=60, seed=0)
        assert res["embedding"], "default arm failed on K10/Z3"
        assert validate_embedding(res["embedding"], k, z)
        assert res["diag"]["stride"] == 2
        res0 = attract_embed(k, z, timeout=60, seed=0, courses=False)
        assert res0["embedding"]
        assert res0["diag"]["stride"] == 1

    def test_exact_stack_default_diag_on_zephyr(self):
        # the consolidation-2 default = the measured s3.57 ovl_nos arm:
        # completion runs, deficit fields surface, snap zeroes extensions,
        # deterministic, valid
        import dwave_networkx as dnx
        z = dnx.zephyr_graph(3, 4)
        k = nx.complete_graph(10)
        a = attract_embed(k, z, timeout=60, seed=0)
        b = attract_embed(k, z, timeout=60, seed=0)
        assert a["embedding"], "default exact stack failed on K10/Z3"
        assert validate_embedding(a["embedding"], k, z)
        assert a["embedding"] == b["embedding"]
        for key in ("mm_skipped", "deficit_edges", "corner_deficit",
                    "extensions", "ext_qubits", "bridges"):
            assert key in a["diag"], key
        assert a["diag"]["mm_skipped"] in (True, False)
        assert a["diag"]["extensions"] == 0  # the snap fingerprint (s3.56)
        assert a["stair_E"] is not None

    def test_stride_gate_byte_identity_off_zephyr(self, chimera, source):
        # the exactness/snap machinery stays stride-gated (junction
        # completeness is physics): on stride-1 fabrics the default must
        # be byte-identical to the exactness-off configuration. NOTE
        # (v4, s3.76): overload_lam is no longer in this list — under
        # the order state the gate is live on every fabric by design.
        a = attract_embed(source, chimera, timeout=60, seed=0)
        b = attract_embed(source, chimera, timeout=60, seed=0,
                          exact_seeds=False, snap_claims=False)
        assert a["embedding"] and a["embedding"] == b["embedding"]
        assert a["stair_E"] == b["stair_E"]
        assert "mm_skipped" not in a["diag"]

    def test_courses_noop_off_zephyr(self, chimera):
        k = nx.complete_graph(8)
        res = attract_embed(k, chimera, timeout=60, seed=0)
        assert res["embedding"]
        assert validate_embedding(res["embedding"], k, chimera)
        assert res["diag"]["stride"] == 1

    def test_feasibility_fallback(self, chimera, source):
        # round_frac=0 exhausts the rounds budget instantly: the rounds loop
        # never runs and the uncapped fallback must still legalize.
        res = attract_embed(source, chimera, timeout=60, seed=0,
                            round_frac=0.0)
        assert res["embedding"], "fallback did not legalize an easy instance"
        assert validate_embedding(res["embedding"], source, chimera)
        assert res["legal_acl"] is not None

    def test_vcycle_stride_gated(self, chimera, source, monkeypatch):
        # s3.66: the coarse init activates only where measured (stride-2);
        # stride-1 fabrics keep the spectral init
        import ember_qc.algorithms.factored.coarsen as C
        called = []
        real = C.multilevel_init
        monkeypatch.setattr(C, "multilevel_init",
                            lambda *a, **k: called.append(1) or real(*a, **k))
        res = attract_embed(source, chimera, timeout=30, seed=0)
        assert res["embedding"] and not called

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


class TestOrderState:
    """v4 stage O1: state = two orders, positions = derived readout."""

    def test_default_is_order_state(self, source, chimera):
        # v4 default flip (s3.76): the default IS the order state; the
        # continuous carrier survives only as the control arm
        a = attract_embed(source, chimera, timeout=60, seed=0)
        b = attract_embed(source, chimera, timeout=60, seed=0,
                          order_state=True)
        assert a["embedding"] and a["embedding"] == b["embedding"]
        assert a["diag"].get("order_state") is True
        c = attract_embed(source, chimera, timeout=60, seed=0,
                          order_state=False)
        assert c["embedding"]
        assert validate_embedding(c["embedding"], source, chimera)
        assert "order_state" not in c["diag"]

    def test_order_state_valid_and_deterministic(self, source, chimera):
        a = attract_embed(source, chimera, timeout=60, seed=0,
                          order_state=True)
        b = attract_embed(source, chimera, timeout=60, seed=0,
                          order_state=True)
        assert a["embedding"]
        assert validate_embedding(a["embedding"], source, chimera)
        assert a["embedding"] == b["embedding"]
        assert a["diag"]["order_state"] is True

    def test_order_state_zephyr_and_pegasus(self, source):
        import dwave_networkx as dnx
        for target in (dnx.zephyr_graph(3, 4), dnx.pegasus_graph(4)):
            r = attract_embed(source, target, timeout=60, seed=0,
                              order_state=True)
            assert r["embedding"], f"failed on {target.graph.get('family')}"
            assert validate_embedding(r["embedding"], source, target)

    def test_positions_are_derived_line_indices(self, source):
        # the derived-values invariant: after an order-mode arrange,
        # every position is an integer line index (never a rank, never
        # a fractional drift value) — the rank-pricing trap guard
        import dwave_networkx as dnx
        from ember_qc.algorithms.factored.field import (
            TileGrid, alternate_arrange, _target_kappa)
        from ember_qc.algorithms.factored.placement import target_layout
        target = dnx.zephyr_graph(3, 4)
        grid = TileGrid(target, target_layout(target), courses=True)
        src_adj = {v: sorted(source.neighbors(v)) for v in source}
        # rank-seeded start, as the driver builds it
        import numpy as np
        pos = {v: np.array([float(i), float(i)])
               for i, v in enumerate(sorted(source))}
        out, _info = alternate_arrange(
            pos, src_adj, grid, iters=4, kappa=_target_kappa(grid),
            use_dp=True, overload_lam=1.0, snap=True, order_mode=True)
        for v, p in out.items():
            assert float(p[0]).is_integer(), (v, p)
            assert float(p[1]).is_integer(), (v, p)
