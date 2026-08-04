"""
tests/algorithms/test_coarsen.py
=================================
Source-side multilevel coarsening (s3.62 V0): the twin-first hierarchy,
the weighted-Jaccard limits from the ledger derivation, and the
multilevel init's structural guarantees.
"""
import networkx as nx
import numpy as np
import pytest

from ember_qc.algorithms.factored.coarsen import (
    Level, _wjaccard, coarsen, multilevel_init)


class TestCoarsen:
    def test_clique_collapses_to_one(self):
        adj = {v: [u for u in range(12) if u != v] for v in range(12)}
        ls = coarsen(adj)
        assert len(ls[-1].adj) == 1
        assert list(ls[-1].weight.values()) == [12.0]

    def test_biclique_collapses_to_quotient(self):
        adj = {v: [u for u in range(12) if (u < 6) != (v < 6)]
               for v in range(12)}
        ls = coarsen(adj)
        assert len(ls[-1].adj) == 2
        assert sorted(ls[-1].weight.values()) == [6.0, 6.0]
        # the quotient edge carries the full 36-edge mass
        (a, d), = [(v, n) for v, n in ls[-1].adj.items() if v == min(ls[-1].adj)]
        assert sum(d.values()) == 36.0

    def test_multipartite_blocks(self):
        # turan-shaped: 3 blocks of 5 -> 3 supernodes
        adj = {v: [u for u in range(15) if u // 5 != v // 5]
               for v in range(15)}
        ls = coarsen(adj)
        assert len(ls[-1].adj) == 3
        assert sorted(ls[-1].weight.values()) == [5.0, 5.0, 5.0]

    def test_chain_halves_by_edges(self):
        adj = {v: [u for u in (v - 1, v + 1) if 0 <= u < 32]
               for v in range(32)}
        ls = coarsen(adj)
        assert len(ls[1].adj) <= 17  # first level ~halves via edge merges

    def test_er_stops_early(self):
        g = nx.gnp_random_graph(60, 6 / 59, seed=3)
        adj = {v: sorted(g.neighbors(v)) for v in g}
        ls = coarsen(adj)
        # the s3.21 null class: nothing to find; hierarchy stays shallow
        assert len(ls) <= 3

    def test_deterministic(self):
        g = nx.gnp_random_graph(40, 0.2, seed=9)
        adj = {v: sorted(g.neighbors(v)) for v in g}
        a = coarsen(adj)
        b = coarsen(adj)
        assert [sorted(l.adj) for l in a] == [sorted(l.adj) for l in b]
        assert [l.weight for l in a] == [l.weight for l in b]

    def test_wjaccard_limits(self):
        # star leaves: share the hub only -> 1/3; leaf-hub -> small
        au = {0: 1.0}
        av = {0: 1.0}
        assert _wjaccard(au, 1.0, 1, av, 1.0, 2) == pytest.approx(1 / 3)


class TestMultilevelInit:
    def test_blocks_separate_and_in_box(self):
        adj = {v: [u for u in range(12) if (u < 6) != (v < 6)]
               for v in range(12)}
        lo, hi = np.array([0.0, 0.0]), np.array([10.0, 10.0])
        pos = multilevel_init(adj, lo, hi, seed=0)
        assert set(pos) == set(range(12))
        for p in pos.values():
            assert np.all(p >= lo - 1e-9) and np.all(p <= hi + 1e-9)
        a = np.mean([pos[v] for v in range(6)], axis=0)
        b = np.mean([pos[v] for v in range(6, 12)], axis=0)
        assert np.linalg.norm(a - b) > 2.0  # blocks land apart

    def test_deterministic_and_seed_sensitivity(self):
        adj = {v: [u for u in range(12) if (u < 6) != (v < 6)]
               for v in range(12)}
        lo, hi = np.array([0.0, 0.0]), np.array([8.0, 8.0])
        a = multilevel_init(adj, lo, hi, seed=1)
        b = multilevel_init(adj, lo, hi, seed=1)
        assert all(np.allclose(a[v], b[v]) for v in a)

    def test_pipeline_vcycle_valid(self):
        import dwave_networkx as dnx
        from ember_qc.algorithms.factored import attract_embed
        from ember_qc.registry import validate_embedding
        z = dnx.zephyr_graph(3, 4)
        k = nx.complete_graph(10)
        r = attract_embed(k, z, timeout=30, seed=0, vcycle=True)
        assert r["embedding"]
        assert validate_embedding(r["embedding"], k, z)
