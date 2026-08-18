"""Ball-prime singles (s3.91): the |S|=1 exact-cross question inside
ball_polish (the operator moved from the retired crossfinder at
consolidation 5; archive 09467299 holds the standalone driver)."""

import networkx as nx
import pytest

dnx = pytest.importorskip("dwave_networkx")

from ember_qc.registry import validate_embedding  # noqa: E402


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
