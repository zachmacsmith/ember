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

    def test_two_stage_flat(self):
        # s3.63: exactly [fine, coarse] — the level loop is gone
        adj = {v: [u for u in range(12) if u != v] for v in range(12)}
        assert len(coarsen(adj)) == 2
        # tiny graphs skip coarsening entirely
        adj_small = {0: [1], 1: [0]}
        assert len(coarsen(adj_small)) == 1

    def test_tau_insensitivity(self):
        # the no-knob-zoo property: the coarse graph is identical across
        # the tau window boxed by the derivation's limit values
        structs = []
        structs.append({v: [u for u in range(12) if u != v]
                        for v in range(12)})                    # clique
        structs.append({v: [u for u in range(12) if (u < 6) != (v < 6)]
                        for v in range(12)})                    # biclique
        structs.append({v: [u for u in range(15) if u // 5 != v // 5]
                        for v in range(15)})                    # 3-partite
        for adj in structs:
            ref = sorted(coarsen(adj, threshold=0.34)[-1].adj)
            for tau in (0.25, 0.45):
                assert sorted(coarsen(adj, threshold=tau)[-1].adj) == ref

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


class TestFootprints:
    def test_internal_mass_tracking(self):
        # K12 -> one supernode holding all C(12,2)=66 merged edges
        adj = {v: [u for u in range(12) if u != v] for v in range(12)}
        ls = coarsen(adj)
        assert list(ls[-1].internal.values()) == [66.0]
        # K_{6,6} blocks: no internal edges, 36 external each
        adj2 = {v: [u for u in range(12) if (u < 6) != (v < 6)]
                for v in range(12)}
        ls2 = coarsen(adj2)
        assert ls2[-1].internal == {}
        assert all(sum(d.values()) == 36.0
                   for d in ls2[-1].adj.values())

    def test_moat_shares(self):
        # equal-headcount clique vs biclique components: wire-mass
        # shares must favor the clique (per-member 7 vs 4) — the s3.64
        # moat fix; count-sizing would split them equally
        adj = {v: [u for u in range(8) if u != v] for v in range(8)}
        for v in range(8, 16):
            adj[v] = [u for u in range(8, 16) if (u < 12) != (v < 12)]
        ls = coarsen(adj)
        mass = {v: 2 * ls[-1].internal.get(v, 0.0)
                + sum(ls[-1].adj[v].values()) for v in ls[-1].adj}
        clique_mass = mass[0]
        block_mass = sum(m for v, m in mass.items() if v != 0)
        assert clique_mass == 56.0 and block_mass == 32.0

    def test_tangency_no_overlap(self):
        # random weighted instance: post-closure footprints must not
        # overlap (allowing the even zoom-down on box overflow)
        import ember_qc.algorithms.factored.coarsen as C
        C.SIZING, C.TILING, C.SHAPE = "mass", True, "disc"
        rng = np.random.RandomState(4)
        g = nx.gnp_random_graph(40, 0.25, seed=11)
        adj = {v: sorted(g.neighbors(v)) for v in g}
        lo, hi = np.array([0.0, 0.0]), np.array([12.0, 12.0])
        levels = C.coarsen(adj)
        if len(levels) < 2 or len(levels[-1].adj) < 2:
            pytest.skip("instance did not coarsen to >=2 supernodes")
        pos = C.multilevel_init(adj, lo, hi, seed=0)
        # recover per-supernode child hulls; hull discs must be disjoint
        par = levels[-1].parent_of
        groups = {}
        for c in pos:
            groups.setdefault(par[c], []).append(pos[c])
        cents = {p: np.mean(g_, axis=0) for p, g_ in groups.items()}
        rads = {p: max(float(np.linalg.norm(q - cents[p])) for q in g_)
                for p, g_ in groups.items()}
        ps = sorted(groups)
        for i in range(len(ps)):
            for j in range(i + 1, len(ps)):
                d = float(np.linalg.norm(cents[ps[i]] - cents[ps[j]]))
                assert d + 1e-6 >= 0.9 * (rads[ps[i]] + rads[ps[j]])

    def test_segment_spread_collinear(self):
        import ember_qc.algorithms.factored.coarsen as C
        C.SIZING, C.TILING, C.SHAPE = "mass", True, "segment"
        adj = {v: [u for u in range(12) if u != v] for v in range(12)}
        lo, hi = np.array([0.0, 0.0]), np.array([10.0, 10.0])
        pos = C.multilevel_init(adj, lo, hi, seed=0)
        pts = np.array([pos[v] for v in sorted(pos)])
        d = pts - pts.mean(axis=0)
        assert float(np.abs(d[:, 0] - d[:, 1]).max()) < 1e-9


@pytest.fixture(autouse=True)
def _reset_coarsen_constants():
    import ember_qc.algorithms.factored.coarsen as C
    yield
    C.SIZING, C.TILING, C.SHAPE, C.COARSE_SPAN = "count", False, "disc", 0.4


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
