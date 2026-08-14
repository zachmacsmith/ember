"""Crossfinder (s3.90) — the rip-and-replace-at-cross-granularity
prototype. Tests pin the measured capability envelope: legal, fast, and
deterministic on sparse structured sources; the liquid/dense legalize
non-convergence is a RECORDED finding (notes s3.90), not a regression —
do not add xfail cells for it here."""

import networkx as nx
import pytest

dnx = pytest.importorskip("dwave_networkx")

from ember_qc.algorithms.factored import crossfinder_embed
from ember_qc.registry import validate_embedding


class TestCrossfinder:
    def test_small_graphs_legal(self):
        z = dnx.zephyr_graph(3, 4)
        for g in (nx.complete_graph(8), nx.cycle_graph(12),
                  nx.convert_node_labels_to_integers(
                      nx.grid_2d_graph(5, 5))):
            r = crossfinder_embed(g, z, timeout=20, seed=0)
            emb = r["embedding"]
            assert emb, r["diag"]
            assert validate_embedding(emb, g, z)

    def test_cycle400_z12_legal_and_short(self):
        z = dnx.zephyr_graph(12, 4)
        g = nx.cycle_graph(400)
        r = crossfinder_embed(g, z, timeout=30, seed=0)
        emb = r["embedding"]
        assert emb, r["diag"]
        assert validate_embedding(emb, g, z)
        assert r["legal_acl"] < 1.5  # measured 1.042 at build time

    def test_deterministic_per_seed(self):
        z = dnx.zephyr_graph(3, 4)
        g = nx.cycle_graph(20)
        r1 = crossfinder_embed(g, z, timeout=20, seed=3)
        r2 = crossfinder_embed(g, z, timeout=20, seed=3)
        assert r1["embedding"] == r2["embedding"]

    def test_never_raises_on_failure(self):
        # K16 on tiny Z2 cannot embed; the contract is a failure dict
        z = dnx.zephyr_graph(2, 4)
        r = crossfinder_embed(nx.complete_graph(16), z, timeout=5, seed=0)
        assert isinstance(r, dict) and "embedding" in r


class TestBallSingles:
    """s3.91 ball-prime: the |S|=1 exact-cross question inside
    ball_polish."""

    def _finished(self, g, z, seed=0):
        from ember_qc.algorithms.factored import attract_embed
        r = attract_embed(g, z, timeout=30, seed=seed)
        assert r["embedding"]
        return r["embedding"]

    def test_singles_valid_and_non_increasing(self):
        from ember_qc.algorithms.factored.ball import ball_polish
        z = dnx.zephyr_graph(3, 4)
        for g in (nx.complete_graph(8), nx.cycle_graph(20)):
            emb = self._finished(g, z)
            total0 = sum(len(c) for c in emb.values())
            out, info = ball_polish(emb, g, z, singles=True)
            assert validate_embedding(out, g, z)
            assert sum(len(c) for c in out.values()) <= total0

    def test_singles_deterministic(self):
        from ember_qc.algorithms.factored.ball import ball_polish
        z = dnx.zephyr_graph(3, 4)
        g = nx.cycle_graph(20)
        emb = self._finished(g, z)
        o1, _ = ball_polish(emb, g, z, singles=True, rng_seed=5)
        o2, _ = ball_polish(emb, g, z, singles=True, rng_seed=5)
        assert o1 == o2

    def test_singles_off_is_control(self):
        from ember_qc.algorithms.factored.ball import ball_polish
        z = dnx.zephyr_graph(3, 4)
        g = nx.complete_graph(8)
        emb = self._finished(g, z)
        a, _ = ball_polish(emb, g, z)
        b, _ = ball_polish(emb, g, z, singles=False)
        assert a == b
