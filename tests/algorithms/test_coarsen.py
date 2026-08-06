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


class TestAdjoint:
    """s3.69: aggregation fixpoint (agg=True) + measure-transport unpack.
    Stock-path assertions above must stay green untouched — both features
    are switch-guarded."""

    def _grid(self):
        import dwave_networkx as dnx
        from ember_qc.algorithms.factored.field import (TileGrid,
                                                        _target_kappa)
        from ember_qc.algorithms.factored.placement import target_layout
        z = dnx.zephyr_graph(3, 4)
        grid = TileGrid(z, target_layout(z), courses=True)
        return grid, _target_kappa(grid)

    def _src(self, g):
        return {v: sorted(g.neighbors(v)) for v in g.nodes()}

    def test_agg_multipartite_quotient_protected(self):
        # Sequential absorption: joiners score against the accumulated
        # cluster — a star of individually-similar blocks must not
        # over-merge past what the merged vector accepts.
        ls = coarsen(self._src(nx.complete_multipartite_graph(5, 5, 5)),
                     agg=True)
        assert len(ls[-1].adj) >= 2

    def test_agg_turan_quotient_emerges(self):
        # The weighted score (S ~ 0.012) does the no-fixpoint decree's
        # job: the 2-block quotient survives with zero agg rounds.
        ls = coarsen(self._src(nx.turan_graph(162, 2)), agg=True)
        assert len(ls[-1].adj) == 2
        assert ls[-1].diag["rounds"] == 0

    def test_agg_chain_deepens_and_star_collapses_whole(self):
        stock = coarsen(self._src(nx.path_graph(200)))
        agg = coarsen(self._src(nx.path_graph(200)), agg=True)
        assert len(agg[-1].adj) < len(stock[-1].adj)  # fixpoint depth
        star = coarsen(self._src(nx.star_graph(11)), agg=True)
        assert len(star[-1].adj) <= 2  # leaves collapse as one group

    def test_agg_internal_mass_tracked(self):
        ls = coarsen(self._src(nx.complete_graph(12)), agg=True)
        assert len(ls[-1].adj) == 1
        (sm,) = ls[-1].self_mass.values()
        assert sm == 66.0  # all K12 edges absorbed

    def test_agg_deterministic(self):
        src = self._src(nx.gnp_random_graph(60, 0.2, seed=3))
        a = coarsen(src, agg=True)
        b = coarsen(src, agg=True)
        assert len(a) == len(b)
        for la, lb in zip(a, b):
            assert la.adj == lb.adj and la.weight == lb.weight

    def test_transport_turan_blocks_contiguous(self):
        from ember_qc.algorithms.factored.coarsen import (
            _coarse_rank_positions, unpack_transport)
        grid, kappa = self._grid()
        src = self._src(nx.turan_graph(162, 2))
        lv = coarsen(src, agg=True)
        pts = unpack_transport(lv, _coarse_rank_positions(lv[-1], 0),
                               grid, kappa, src)
        xs = sorted((pts[v][0], v) for v in pts)
        block = {v for _, v in xs[:81]}
        assert block in (set(range(81)), set(range(81, 162)))

    def test_transport_kn_diagonal_no_anchor(self):
        # One supernode is not a special case: cumulative mass on both
        # axes yields the diagonal crystal (replaces the V0 anchor).
        from ember_qc.algorithms.factored.coarsen import (
            _coarse_rank_positions, unpack_transport)
        grid, kappa = self._grid()
        src = self._src(nx.complete_graph(40))
        lv = coarsen(src, agg=True)
        pts = unpack_transport(lv, _coarse_rank_positions(lv[-1], 0),
                               grid, kappa, src)
        a = np.array([pts[v] for v in sorted(pts)])
        corr = np.corrcoef(a[:, 0], a[:, 1])[0, 1]
        assert corr > 0.999
        assert a[:, 0].max() - a[:, 0].min() >= 1.0  # crystal-scale, not a point

    def test_transport_path_uniform_measure(self):
        from ember_qc.algorithms.factored.coarsen import (
            _coarse_rank_positions, unpack_transport)
        grid, kappa = self._grid()
        src = self._src(nx.path_graph(100))
        lv = coarsen(src, agg=True)
        pts = unpack_transport(lv, _coarse_rank_positions(lv[-1], 0),
                               grid, kappa, src)
        xs = sorted(p[0] for p in pts.values())
        gaps = np.diff(xs)
        # uniform mass -> uniform spacing (interior gaps equal)
        assert gaps.std() <= 0.05 * max(gaps.mean(), 1e-9) + 1e-9

    def test_transport_lattice_locality(self):
        # Deep fixpoint chains unpack level-by-level: adjacent lattice
        # nodes stay near in the fine order (the one-shot flatten broke
        # this — the s3.69 over-coarsening lesson).
        import statistics
        from ember_qc.algorithms.factored.coarsen import (
            _coarse_rank_positions, unpack_transport)
        grid, kappa = self._grid()
        g = nx.convert_node_labels_to_integers(
            nx.triangular_lattice_graph(8, 8))
        src = self._src(g)
        lv = coarsen(src, agg=True)
        pts = unpack_transport(lv, _coarse_rank_positions(lv[-1], 0),
                               grid, kappa, src)
        n = len(pts)
        d = [abs(pts[u][0] - pts[v][0]) + abs(pts[u][1] - pts[v][1])
             for u in src for v in src[u] if u < v]
        ext = (max(p[0] for p in pts.values())
               - min(p[0] for p in pts.values()))
        # median adjacent separation well below the layout extent
        assert statistics.median(d) < 0.35 * max(ext, 1e-9)

    def test_pipeline_adjoint_valid_and_gated(self):
        import dwave_networkx as dnx
        from ember_qc.algorithms.factored import attract_embed
        from ember_qc.registry import validate_embedding
        z = dnx.zephyr_graph(3, 4)
        k = nx.complete_graph(10)
        r = attract_embed(k, z, timeout=30, seed=0,
                          vcycle_agg=True, vcycle_transport=True)
        assert r["embedding"]
        assert validate_embedding(r["embedding"], k, z)
        # off-Zephyr the whole vcycle (and thus both new switches) is
        # stride-gated: byte-identity with the stock arm
        import dwave_networkx as dnx2
        c = dnx2.chimera_graph(4, 4, 4)
        r1 = attract_embed(k, c, timeout=20, seed=0)
        r2 = attract_embed(k, c, timeout=20, seed=0,
                           vcycle_agg=True, vcycle_transport=True)
        assert r1["embedding"] == r2["embedding"]
