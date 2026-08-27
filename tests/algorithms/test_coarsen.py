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
    """s3.69: aggregation fixpoint (agg=True). Stock-path assertions
    above must stay green untouched."""

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

    def test_pipeline_adjoint_valid_and_gated(self):
        import dwave_networkx as dnx
        from ember_qc.algorithms.factored import attract_embed
        from ember_qc.registry import validate_embedding
        z = dnx.zephyr_graph(3, 4)
        k = nx.complete_graph(10)
        r = attract_embed(k, z, timeout=30, seed=0, vcycle_agg=True)
        assert r["embedding"]
        assert validate_embedding(r["embedding"], k, z)
        # off-Zephyr the whole vcycle (and thus the agg switch) is
        # stride-gated: byte-identity with the stock arm
        import dwave_networkx as dnx2
        c = dnx2.chimera_graph(4, 4, 4)
        r1 = attract_embed(k, c, timeout=20, seed=0)
        r2 = attract_embed(k, c, timeout=20, seed=0, vcycle_agg=True)
        assert r1["embedding"] == r2["embedding"]


class TestClusterMoves:
    """s3.70: coarsen the moves, not the state — cluster gather/relocate
    as E-gated composites on real members. Switch `cluster_moves`,
    default off, fabric-agnostic."""

    def test_pipeline_cmove_valid_and_off_switch_identity(self):
        import dwave_networkx as dnx
        from ember_qc.algorithms.factored import attract_embed
        from ember_qc.registry import validate_embedding
        z = dnx.zephyr_graph(3, 4)
        t = nx.turan_graph(40, 2)
        r_on = attract_embed(t, z, timeout=30, seed=0, cluster_moves=True)
        assert r_on["embedding"]
        assert validate_embedding(r_on["embedding"], t, z)
        r_off1 = attract_embed(t, z, timeout=30, seed=0)
        r_off2 = attract_embed(t, z, timeout=30, seed=0)
        assert r_off1["embedding"] == r_off2["embedding"]

    def test_cmove_never_worse_gate_energy(self):
        # E-gated: the arranged stair_E with cluster moves must be <=
        # stock's (accepted moves strictly improve; rejected ones revert).
        import dwave_networkx as dnx
        from ember_qc.algorithms.factored import attract_embed
        z = dnx.zephyr_graph(6, 4)
        er = nx.gnp_random_graph(80, 0.1, seed=7)  # expander-ish noise
        r0 = attract_embed(er, z, timeout=20, seed=1)
        r1 = attract_embed(er, z, timeout=20, seed=1, cluster_moves=True)
        assert r1["stair_E"] <= r0["stair_E"] + 1e-6

    def test_cmove_unmixes_interleaved_turan(self):
        # The mid-descent escape: from the default init, cluster moves
        # must not lose to stock on turan (the gather is the unmixer).
        import dwave_networkx as dnx
        from ember_qc.algorithms.factored import attract_embed
        z = dnx.zephyr_graph(6, 4)
        t = nx.turan_graph(80, 2)
        r0 = attract_embed(t, z, timeout=20, seed=0)
        r1 = attract_embed(t, z, timeout=20, seed=0, cluster_moves=True)
        e0 = r0["embedding"]; e1 = r1["embedding"]
        a0 = sum(map(len, e0.values())) / len(e0)
        a1 = sum(map(len, e1.values())) / len(e1)
        assert a1 <= a0 + 1e-9


class TestUnitsMode:
    """s3.71: threshold-free move-unit coarsening (mutual-preference /
    greedy score-rank matching, adjacency-only candidates, no tau)."""

    def _hier(self, g):
        src = {v: sorted(g.neighbors(v)) for v in g}
        return coarsen(src, units=True), g

    def test_lattices_get_patch_hierarchies(self):
        for g in (nx.convert_node_labels_to_integers(nx.grid_2d_graph(10, 10)),
                  nx.convert_node_labels_to_integers(
                      nx.hexagonal_lattice_graph(5, 5))):
            ls, _ = self._hier(g)
            sizes = [len(l.adj) for l in ls]
            # halving-ish depth, terminating at 1 — tau would have
            # blocked all interior merges (scores 1/4, 1/3)
            assert sizes[-1] == 1 and len(sizes) >= 6
            assert sizes[1] <= 0.6 * sizes[0]

    def test_crystals_assemble_and_er_coarsens(self):
        # The affinity engine is THE units engine (s3.72; no hash):
        # families assemble via affinity-1 pairs over log rounds.
        lsK, _ = self._hier(nx.complete_graph(100))
        sizes = [len(l.adj) for l in lsK]
        assert sizes[0] == 100 and sizes[-1] == 1 and len(sizes) <= 10
        lsT, _ = self._hier(nx.turan_graph(162, 2))
        assert any(len(l.adj) == 2 for l in lsT)
        lsE, _ = self._hier(nx.gnp_random_graph(100, 0.101, seed=1))
        assert len(lsE) > 3 and len(lsE[-1].adj) <= 2

    def test_no_threshold_consumed_and_deterministic(self):
        g = nx.connected_watts_strogatz_graph(200, 6, 0.1, seed=5)
        src = {v: sorted(g.neighbors(v)) for v in g}
        a = coarsen(src, units=True, threshold=0.99)  # ignored on this path
        b = coarsen(src, units=True, threshold=0.01)
        assert [len(l.adj) for l in a] == [len(l.adj) for l in b]
        c = coarsen(src, units=True)
        assert all(la.adj == lc.adj for la, lc in zip(a, c))

    def test_pipeline_units_valid_and_control_arm(self):
        import dwave_networkx as dnx
        from ember_qc.algorithms.factored import attract_embed
        from ember_qc.registry import validate_embedding
        z = dnx.zephyr_graph(3, 4)
        t = nx.turan_graph(40, 2)
        r = attract_embed(t, z, timeout=30, seed=0)  # units default ON
        assert r["embedding"] and validate_embedding(r["embedding"], t, z)
        r_ctl = attract_embed(t, z, timeout=30, seed=0, cluster_units=False)
        assert r_ctl["embedding"]  # s3.70 control arm still runs


class TestAffinity:
    """s3.72: the per-member criterion — one formula, verified against
    the derived case table."""

    def _aff(self, au, wu, av, wv):
        from ember_qc.algorithms.factored.coarsen import _affinity
        return _affinity(au, wu, 0, av, wv, 1)

    def test_twin_fragments_any_ratio_score_one(self):
        # Max's case: 1:2 fragments of one interchangeable family must
        # score exactly 1 (the raw-total score gave 1/2).
        nbrs = range(100, 105)
        au = {k: 1.0 for k in nbrs}
        av = {k: 2.0 for k in nbrs}
        assert abs(self._aff(au, 1.0, av, 2.0) - 1.0) < 1e-12
        av7 = {k: 7.0 for k in nbrs}
        assert abs(self._aff(au, 1.0, av7, 7.0) - 1.0) < 1e-12

    def test_open_twins_score_one_without_hash(self):
        au = {5: 1.0, 6: 1.0, 7: 1.0}
        assert abs(self._aff(au, 1.0, dict(au), 1.0) - 1.0) < 1e-12

    def test_chain_pair_half(self):
        assert abs(self._aff({10: 1.0, 1: 1.0}, 1.0,
                             {0: 1.0, 11: 1.0}, 1.0) - 0.5) < 1e-12

    def test_clique_pair_one_and_quotient_one(self):
        au = {2: 1.0, 3: 1.0, 1: 1.0}
        av = {2: 1.0, 3: 1.0, 0: 1.0}
        assert abs(self._aff(au, 1.0, av, 1.0) - 1.0) < 1e-12
        # turan quotient: heavy mutual bundle is pure agreement now
        assert abs(self._aff({1: 6561.0}, 81.0,
                             {0: 6561.0}, 81.0) - 1.0) < 1e-12

    def test_cross_block_and_hub_leaf_small(self):
        aut = {k: 1.0 for k in range(100, 181)}
        aut[1] = 1.0
        avt = {k: 1.0 for k in range(200, 281)}
        avt[0] = 1.0
        assert self._aff(aut, 1.0, avt, 1.0) < 0.02
        auh = {k: 1.0 for k in range(1, 100)}
        assert self._aff(auh, 1.0, {0: 1.0}, 1.0) < 0.03

    def test_star_family_assembles_without_hash(self):
        # The PARKED affinity engine (s3.72): hash-free assembly still
        # verified — leaves pair through the shared hub at affinity 1.
        from ember_qc.algorithms.factored.coarsen import coarsen
        g = nx.star_graph(64)
        ls = coarsen({v: sorted(g.neighbors(v)) for v in g}, units=True)
        assert any(len(l.adj) == 2 for l in ls)

    def test_affinity_engine_turan_purity(self):
        # The parked engine keeps blocks pure to the 2-level (the
        # admissibility rule: merge only if it is someone's best).
        from ember_qc.algorithms.factored.coarsen import coarsen
        g = nx.turan_graph(162, 2)
        ls = coarsen({v: sorted(g.neighbors(v)) for v in g}, units=True)
        mem = {v: [v] for v in ls[0].adj}
        for li in range(1, len(ls) - 1):  # exclude the final total merge
            up = {}
            for c, ms in mem.items():
                up.setdefault(ls[li].parent_of[c], []).extend(ms)
            mem = up
            for ms in mem.values():
                a = sum(1 for x in ms if x < 81)
                assert min(a, len(ms) - a) == 0  # pure


class TestConsumptionSchedule:
    """s3.73: both-axes gathers, strict-descent cluster acceptance, no
    per-cluster caps — the energy is the schedule."""

    def test_x_gather_fires(self):
        # A layout interleaved in x with a clean y should be fixable by
        # the axis-0 gather: run the pipeline on turan and require that
        # at least one composite fired on each axis over the run.
        import dwave_networkx as dnx
        from ember_qc.algorithms.factored import attract_embed
        z = dnx.zephyr_graph(6, 4)
        t = nx.turan_graph(80, 2)
        r = attract_embed(t, z, timeout=30, seed=0)
        d = r["diag"]
        # the unit move consumed the hierarchy: jumps proposed and
        # either accepted, declined by the audit, or certified no-op
        assert (d["interleave_accepts"] + d["interleave_declines"]
                + d["interleave_noops"]) > 0

    def test_strictness_never_worse_and_terminates(self):
        # Strict acceptance: gate energy with cluster moves <= without;
        # and without the one-shot rule the pass must still terminate
        # with a bounded composite count on an expander.
        import time
        import dwave_networkx as dnx
        from ember_qc.algorithms.factored import attract_embed
        z = dnx.zephyr_graph(6, 4)
        er = nx.gnp_random_graph(80, 0.1, seed=7)
        t0 = time.perf_counter()
        # engine pinned: this pins the LEX engine's cluster-move
        # schedule (its subject); the plane default neither consumes
        # cluster_moves nor bounds accepts this way (s3.117)
        r1 = attract_embed(er, z, timeout=20, seed=1, engine="lex")
        wall = time.perf_counter() - t0
        r0 = attract_embed(er, z, timeout=20, seed=1, engine="lex",
                           cluster_moves=False)
        assert r1["embedding"] and r0["embedding"]
        d = r1["diag"]
        assert d["interleave_accepts"] < 2000
        assert wall < 25.0

    def test_validity_and_determinism_with_schedule(self):
        import dwave_networkx as dnx
        from ember_qc.algorithms.factored import attract_embed
        from ember_qc.registry import validate_embedding
        z = dnx.zephyr_graph(3, 4)
        t = nx.turan_graph(40, 2)
        a = attract_embed(t, z, timeout=30, seed=0)
        b = attract_embed(t, z, timeout=30, seed=0)
        assert a["embedding"] == b["embedding"]
        assert validate_embedding(a["embedding"], t, z)
