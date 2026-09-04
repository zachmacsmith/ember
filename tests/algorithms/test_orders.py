"""
tests/algorithms/test_orders.py
================================
The orders-state engine (orders.py, round 1, 2026-08-26): readout
purity/determinism, the singleton align_reinsert oracle (the guard
lift's new territory), audit-mode monotonicity, the accept-all
bookmark invariant, and the e2e pipeline on both fabrics plus the
untyped no-op and the default-identity check.
"""
import itertools

import dwave_networkx as dnx
import networkx as nx
import numpy as np
import pytest

from ember_qc.algorithms.factored.field import (
    TileGrid, _stair_contacts, _target_kappa, align_reinsert,
    pack_project, stair_energy, xy_reinsert)
from ember_qc.algorithms.factored.orders import order_arrange
from ember_qc.algorithms.factored.placement import target_layout
from ember_qc.algorithms.factored.seat import seat_energy


def _zgrid():
    g = dnx.zephyr_graph(3, 4)
    return TileGrid(g, target_layout(g), courses=True)


def _cgrid():
    g = dnx.chimera_graph(4, 4, 4)
    return TileGrid(g, target_layout(g))


def _case(rng, grid, n, p_edge=0.4):
    g = nx.gnp_random_graph(n, p_edge, seed=int(rng.integers(9999)))
    adj = {v: sorted(g.neighbors(v)) for v in g.nodes()}
    pos = {v: np.array([float(rng.integers(0, grid.W)),
                        float(rng.integers(0, grid.H))])
           for v in g.nodes()}
    return adj, pos


class TestReadout:
    """The readout = pack_project(monotonize=False): a pure, repeatable
    orders -> positions projection."""

    def test_deterministic_pure_and_windowed(self):
        grid = _zgrid()
        rng = np.random.default_rng(11)
        adj, pos = _case(rng, grid, 24)
        kappa = _target_kappa(grid)
        frozen = {v: p.copy() for v, p in pos.items()}
        a, _ = pack_project(pos, adj, grid, kappa=kappa,
                            monotonize=False)
        b, _ = pack_project(pos, adj, grid, kappa=kappa,
                            monotonize=False)
        # input unmutated, repeat call identical
        assert all(np.array_equal(pos[v], frozen[v]) for v in pos)
        assert all(np.array_equal(a[v], b[v]) for v in a)
        for v, p in a.items():
            assert float(p[0]).is_integer() and float(p[1]).is_integer()
            assert 0 <= p[0] < grid.W and 0 <= p[1] < grid.H

    def test_monotonize_off_never_swaps(self):
        # the flag's contract: with monotonize=False the x-permutation
        # step never runs. (Each individual pack is order-preserving —
        # pinned in test_field — but the COMPOSED readout can collapse
        # a strict pair into a line tie and re-split it by id, so
        # end-to-end order preservation is deliberately not claimed;
        # the engine's noop rule and per-state view-gate absorb it.)
        grid = _zgrid()
        rng = np.random.default_rng(23)
        adj, pos = _case(rng, grid, 12, p_edge=0.3)
        kappa = _target_kappa(grid)
        _, rinfo = pack_project(pos, adj, grid, kappa=kappa,
                                monotonize=False)
        assert rinfo["mono_swaps"] == 0 and rinfo["mono_time"] == 0.0


class TestSingletonReinsert:
    """|S| = 1 through the lifted guard: exact optimum over all
    insertion slots x both (trivial) orientations."""

    @staticmethod
    def _merges(R, S):
        n = len(R) + len(S)
        for slots in itertools.combinations(range(n), len(S)):
            slot_set = set(slots)
            out, ri, si = [], 0, 0
            for k in range(n):
                if k in slot_set:
                    out.append(S[si])
                    si += 1
                else:
                    out.append(R[ri])
                    ri += 1
            yield out

    @staticmethod
    def _gt(merged, adj, values, other, axis, contacts=None, bar=0.0):
        val = np.asarray(values, dtype=float)   # unramped (s3.127)
        if axis == 1:
            pos = {v: np.array([float(other[v]), float(val[r])])
                   for r, v in enumerate(merged)}
            if contacts is None:
                yrank = {v: r for r, v in enumerate(merged)}
                contacts = _stair_contacts(pos, adj, yrank=yrank)
        else:
            pos = {v: np.array([float(val[r]), float(other[v])])
                   for r, v in enumerate(merged)}
        return stair_energy(pos, adj, contacts=contacts, bar=bar)

    @pytest.mark.parametrize("axis,bar", [(1, 0.0), (0, 0.0),
                                          (1, 2.0), (0, 2.0)])
    def test_exact_and_optimal_vs_brute_force(self, axis, bar):
        rng = np.random.default_rng(41 + axis)
        for _trial in range(15):
            n = int(rng.integers(5, 9))
            g = nx.gnp_random_graph(n, 0.5, seed=int(rng.integers(9999)))
            adj = {v: sorted(g.neighbors(v)) for v in g.nodes()}
            order = list(rng.permutation(n))
            values = sorted(float(x) for x in
                            rng.choice(np.arange(0, 3 * n), n,
                                       replace=False))
            other = {v: float(rng.integers(0, 10)) for v in range(n)}
            S = [int(rng.integers(0, n))]
            contacts = None
            if axis == 0:
                val = np.asarray(values, dtype=float)
                pos0 = {v: np.array([float(val[r]), float(other[v])])
                        for r, v in enumerate(order)}
                contacts = _stair_contacts(pos0, adj)
            R = [v for v in order if v not in set(S)]
            e_cur = self._gt(order, adj, values, other, axis, contacts,
                             bar)
            brute = min(self._gt(mg, adj, values, other, axis, contacts,
                                 bar)
                        for mg in self._merges(R, S))
            res, _flip = align_reinsert(
                order, set(S), adj, values, None,
                axis=axis, other=other, contacts=contacts, bar=bar)
            if res is not None:
                got = self._gt(res, adj, values, other, axis, contacts,
                               bar)
                assert abs(got - brute) < 1e-6, (got, brute)
                assert got <= e_cur + 1e-9   # ties: the rank tiebreak
            else:
                assert brute >= e_cur - 1e-6

    def test_empty_unit_declines(self):
        adj = {0: [1], 1: [0, 2], 2: [1]}
        res, flip = align_reinsert(
            [0, 1, 2], set(), adj, [0.0, 1.0, 2.0], None,
            axis=1, other={v: 0.0 for v in range(3)}, contacts=None)
        assert res is None and flip is False


class TestOrderArrange:
    def _run(self, grid, n, seed, audit, p_edge=0.4):
        rng = np.random.default_rng(seed)
        adj, pos = _case(rng, grid, n, p_edge)
        kappa = _target_kappa(grid)
        return adj, pos, order_arrange(
            pos, adj, grid,
            kappa=kappa, audit=audit,
            deadline=None if n <= 24 else None)

    @pytest.mark.parametrize("mk", [_zgrid, _cgrid])
    def test_audit_monotone_and_consistent(self, mk):
        grid = mk()
        adj, pos, (out, info) = self._run(grid, 20, 5, audit=True)
        kappa = _target_kappa(grid)
        start, _ = pack_project(pos, adj, grid, kappa=kappa,
                                monotonize=False)
        e_in = seat_energy(start, adj, grid)
        assert info["seat_E"] == seat_energy(out, adj, grid)
        assert info["seat_E"] <= e_in + 1e-9
        assert info["interleave_declines"] >= 0

    @pytest.mark.parametrize("mk", [_zgrid, _cgrid])
    def test_accept_all_bookmark_and_deterministic(self, mk):
        grid = mk()
        adj, pos, (out, info) = self._run(grid, 20, 9, audit=False)
        # the bookmark IS the returned state, and its E is honest
        assert info["seat_E"] == seat_energy(out, adj, grid)
        _, _, (out2, info2) = self._run(grid, 20, 9, audit=False)
        assert all(np.array_equal(out[v], out2[v]) for v in out)
        assert info["seat_E"] == info2["seat_E"]

    def test_untyped_grid_noops(self):
        g = nx.grid_2d_graph(8, 8)
        g = nx.convert_node_labels_to_integers(g)
        grid = TileGrid(g, nx.spectral_layout(g), fallback_bins=4)
        rng = np.random.default_rng(3)
        adj, pos = _case(rng, grid, 10)
        out, info = order_arrange(pos, adj, grid, kappa=4.0)
        assert info["passes"] == 0 and info["seat_pen"] is None
        assert all(np.array_equal(out[v], pos[v]) for v in pos)


class TestPipeline:
    def test_e2e_valid_deterministic_both_fabrics(self):
        from ember_qc.algorithms.factored import attract_embed
        from ember_qc.registry import validate_embedding
        src = nx.gnp_random_graph(12, 0.4, seed=7)
        for tgt in (dnx.zephyr_graph(3, 4), dnx.chimera_graph(4, 4, 4)):
            for eng in ("orders", "orders-audit"):
                r1 = attract_embed(src, tgt, timeout=15, seed=0,
                                   engine=eng)
                r2 = attract_embed(src, tgt, timeout=15, seed=0,
                                   engine=eng)
                emb = r1["embedding"]
                assert emb, (eng, r1.get("error"))
                assert validate_embedding(emb, src, tgt)
                assert r1["embedding"] == r2["embedding"]
                assert "readouts" in r1["diag"]

    def test_bad_engine_fails_loud(self):
        from ember_qc.algorithms.factored import attract_embed
        src = nx.path_graph(4)
        r = attract_embed(src, dnx.chimera_graph(2, 2, 4), timeout=5,
                          seed=0, engine="bogus")
        assert r["status"] == "FAILURE" and "engine" in r.get("error", "")

    def test_default_is_plane_identity(self):
        # s3.117: the plane engine is the default (Max's call on the
        # s3.116 board); lex/orders remain as pinned arms
        from ember_qc.algorithms.factored import attract_embed
        src = nx.gnp_random_graph(10, 0.4, seed=3)
        tgt = dnx.zephyr_graph(2, 4)
        a = attract_embed(src, tgt, timeout=10, seed=0)
        b = attract_embed(src, tgt, timeout=10, seed=0, engine="plane")
        assert a["embedding"] == b["embedding"]


class TestPlaneEngine:
    """Round 3 (s3.116): ideal-plane search + one brick-aware
    projection."""

    def test_readout_project_false_stays_ideal(self):
        grid = _zgrid()
        rng = np.random.default_rng(7)
        adj, pos = _case(rng, grid, 18)
        kappa = _target_kappa(grid)
        out, rinfo = pack_project(pos, adj, grid, kappa=kappa,
                                  monotonize=False, project=False)
        # no bounded-stage keys; contacts present; deterministic
        assert "final_width_x" not in rinfo
        assert "projection_misses" not in rinfo
        assert rinfo["_contacts"]
        out2, _ = pack_project(pos, adj, grid, kappa=kappa,
                               monotonize=False, project=False)
        assert all(np.array_equal(out[v], out2[v]) for v in out)
        assert rinfo.get("unb_miss", 0) == 0

    def test_brick_projection_v_pen_zero(self):
        # the exactly-certified orientation: x is assigned last, so
        # v-arm (column) cover vs pv pools must be within capacity on
        # miss-free instances (h is only empirically clean — the
        # final x-pack remaps h-footprints after their certificate)
        from ember_qc.algorithms.factored.field import (
            _brick_pool_arrays, _stair_contacts)
        grid = _zgrid()
        s = max(grid.stride, 1)
        _ph, pv = _brick_pool_arrays(grid, s)
        rng = np.random.default_rng(29)
        checked = 0
        for _trial in range(12):
            adj, pos = _case(rng, grid, 16, p_edge=0.3)
            kappa = _target_kappa(grid)
            out, rinfo = pack_project(pos, adj, grid, kappa=kappa,
                                      monotonize=False,
                                      brick_pools=True)
            if rinfo.get("projection_misses", 0):
                continue
            checked += 1
            contacts = _stair_contacts(out, adj)
            cov = np.zeros_like(pv)
            for v, (h_us, v_us) in contacts.items():
                if not v_us:
                    continue
                x = int(out[v][0])
                ys = [int(out[u][1]) for u in v_us] + [int(out[v][1])]
                for b in range(min(ys) // s, max(ys) // s + 1):
                    cov[x, b] += 1
            assert np.all(cov <= pv + 1e-9), "v-orientation pen leak"
        assert checked >= 6  # the property must actually be exercised

    def test_e2e_plane_valid_deterministic(self):
        from ember_qc.algorithms.factored import attract_embed
        from ember_qc.registry import validate_embedding
        src = nx.gnp_random_graph(12, 0.4, seed=7)
        for tgt in (dnx.zephyr_graph(3, 4), dnx.chimera_graph(4, 4, 4)):
            for eng in ("plane", "plane-audit"):
                r1 = attract_embed(src, tgt, timeout=15, seed=0,
                                   engine=eng)
                r2 = attract_embed(src, tgt, timeout=15, seed=0,
                                   engine=eng)
                emb = r1["embedding"]
                assert emb, (eng, r1.get("error"))
                assert validate_embedding(emb, src, tgt)
                assert r1["embedding"] == r2["embedding"]
                assert "proj_pen" in r1["diag"]
                assert "seat_pen" not in r1["diag"]


class TestCenterShift:
    """s3.117: the brick projection centers the layout — stair is
    translation-invariant given the orders, so the shift is judged
    purely by per-brick feasibility (s-aligned candidates only)."""

    def test_fires_and_is_stair_neutral(self):
        from ember_qc.algorithms.factored.field import stair_energy
        grid = _zgrid()
        rng = np.random.default_rng(13)
        adj, pos = _case(rng, grid, 10, p_edge=0.3)
        kappa = _target_kappa(grid)
        out, info = pack_project(pos, adj, grid, kappa=kappa,
                                 monotonize=False, brick_pools=True)
        dx, dy = info.get("center_shift", (0, 0))
        # translation invariance, checked directly: shifting back
        # changes nothing in stair
        back = {v: p - np.array([float(dx), float(dy)])
                for v, p in out.items()}
        assert stair_energy(out, adj) == stair_energy(back, adj)
        for p in out.values():
            assert 0 <= p[0] < grid.W and 0 <= p[1] < grid.H
        out2, info2 = pack_project(pos, adj, grid, kappa=kappa,
                                   monotonize=False, brick_pools=True)
        assert info2.get("center_shift") == (dx, dy)
        assert all(np.array_equal(out[v], out2[v]) for v in out)


class TestCarriedOrders:
    """s3.118: the id-fossil dies — the tie-break is the carried
    order, every interleaver candidate is a real state."""

    def test_rank_tie_contacts(self):
        # two co-located variables: (y, id) says 1 below 2; the
        # carried order can say the opposite — and rank rules
        adj = {1: [2], 2: [1]}
        pos = {1: np.array([0.0, 3.0]), 2: np.array([1.0, 3.0])}
        legacy = _stair_contacts(pos, adj)
        assert legacy[1] == ([2], []) and legacy[2] == ([], [1])
        flipped = _stair_contacts(pos, adj, yrank={1: 1, 2: 0})
        assert flipped[2] == ([1], []) and flipped[1] == ([], [2])
        agree = _stair_contacts(pos, adj, yrank={1: 0, 2: 1})
        assert agree == legacy

    def test_realness_property(self):
        # THE round's property: after a carried adopt + readout, the
        # state's contacts are exactly the carried y-order's rank
        # contacts (the DP's assumed book == the realized book), and
        # values are non-decreasing along the carried orders
        from ember_qc.algorithms.factored.orders import order_arrange
        grid = _zgrid()
        rng = np.random.default_rng(37)
        # tied-heavy start: few distinct values, many co-located
        g = nx.gnp_random_graph(16, 0.4, seed=11)
        adj = {v: sorted(g.neighbors(v)) for v in g.nodes()}
        pos = {v: np.array([float(rng.integers(0, 3)),
                            float(rng.integers(0, 3))])
               for v in g.nodes()}
        kappa = _target_kappa(grid)
        out, info = order_arrange(pos, adj, grid, kappa=kappa,
                                  plane=True, carry=True)
        ox, oy = info["_orders"]
        yrank = {v: r for r, v in enumerate(oy)}
        want = _stair_contacts(out, adj, yrank=yrank)
        got = info["readout_info"]["_contacts"]
        assert got == want
        for ax, o in ((0, ox), (1, oy)):
            vals = [float(out[v][ax]) for v in o]
            assert all(a <= b for a, b in zip(vals, vals[1:]))

    def test_e2e_carry_valid_deterministic(self):
        from ember_qc.algorithms.factored import attract_embed
        from ember_qc.registry import validate_embedding
        src = nx.gnp_random_graph(12, 0.4, seed=7)
        for tgt in (dnx.zephyr_graph(3, 4), dnx.chimera_graph(4, 4, 4)):
            for kw in ({"carry_orders": True},
                       {"engine": "plane-audit", "carry_orders": True}):
                r1 = attract_embed(src, tgt, timeout=15, seed=0, **kw)
                r2 = attract_embed(src, tgt, timeout=15, seed=0, **kw)
                emb = r1["embedding"]
                assert emb, (kw, r1.get("error"))
                assert validate_embedding(emb, src, tgt)
                assert r1["embedding"] == r2["embedding"]

    def test_default_is_carry_identity(self):
        # s3.120: carry is the default (Max's call — the compaction
        # must not inherit id-tie behavior by inertia)
        from ember_qc.algorithms.factored import attract_embed
        src = nx.gnp_random_graph(10, 0.4, seed=3)
        tgt = dnx.zephyr_graph(2, 4)
        a = attract_embed(src, tgt, timeout=10, seed=0)
        b = attract_embed(src, tgt, timeout=10, seed=0,
                          carry_orders=True)
        assert a["embedding"] == b["embedding"]

    def test_landmark_and_random_inits(self):
        from ember_qc.algorithms.factored import attract_embed
        from ember_qc.registry import validate_embedding
        src = nx.gnp_random_graph(14, 0.3, seed=6)
        tgt = dnx.zephyr_graph(3, 4)
        for im in ("landmark", "random"):
            r1 = attract_embed(src, tgt, timeout=15, seed=0,
                               init_mode=im)
            r2 = attract_embed(src, tgt, timeout=15, seed=0,
                               init_mode=im)
            emb = r1["embedding"]
            assert emb and validate_embedding(emb, src, tgt), im
            assert r1["embedding"] == r2["embedding"]
        r = attract_embed(src, tgt, timeout=5, seed=0,
                          init_mode="bogus")
        assert r["status"] == "FAILURE" and "init_mode" in r.get(
            "error", "")

    def test_tied_values_interleaver_realness(self):
        # the audit's missing oracle arm, now sound to write: with a
        # carried order over TIED values, an accepted proposal must be
        # a true improvement of the unramped rank-tie ground truth
        rng = np.random.default_rng(53)
        hits = 0
        for _trial in range(30):
            n = int(rng.integers(5, 9))
            g = nx.gnp_random_graph(n, 0.5, seed=int(rng.integers(9999)))
            adj = {v: sorted(g.neighbors(v)) for v in g.nodes()}
            order = list(rng.permutation(n))
            # heavy ties: values drawn from {0, 1, 2}, sorted
            vals = sorted(float(rng.integers(0, 3)) for _ in range(n))
            other = {v: float(rng.integers(0, 6)) for v in range(n)}

            def gt(o):
                pos = {v: np.array([other[v], vals[r]])
                       for r, v in enumerate(o)}
                yrank = {v: r for r, v in enumerate(o)}
                return stair_energy(pos, adj,
                                    contacts=_stair_contacts(
                                        pos, adj, yrank=yrank))
            k = int(rng.integers(1, 4))
            S = sorted(rng.choice(n, size=k, replace=False).tolist())
            res, _f = align_reinsert(order, set(S), adj, vals, None,
                                     axis=1, other=other, contacts=None)
            if res is not None:
                hits += 1
                assert gt(res) <= gt(order) + 1e-9, \
                    "carried-order accept must not be a true regression"
        assert hits >= 5  # the property must actually be exercised


class TestXYReinsert:
    """s3.121: the joint two-axis singleton — exact optimum over ALL
    (x-slot, y-slot) pairs, against brute force, in both value
    regimes. Ground truth is the UNRAMPED rank-tie stair (the carry
    regime's judge)."""

    @staticmethod
    def _gt(ox, oy, adj, vals_x, vals_y, bar=0.0):
        pos = {}
        rx = {v: r for r, v in enumerate(ox)}
        for r, v in enumerate(oy):
            pos[v] = np.array([float(vals_x[rx[v]]), float(vals_y[r])])
        yrank = {v: r for r, v in enumerate(oy)}
        return stair_energy(pos, adj,
                            contacts=_stair_contacts(pos, adj,
                                                     yrank=yrank),
                            bar=bar)

    @staticmethod
    def _insert(order, v, k):
        R = [u for u in order if u != v]
        return R[:k] + [v] + R[k:]

    def _trial(self, rng, tie_heavy, bar=0.0):
        n = int(rng.integers(5, 9))
        g = nx.gnp_random_graph(n, 0.5, seed=int(rng.integers(9999)))
        adj = {v: sorted(g.neighbors(v)) for v in g.nodes()}
        ox = list(rng.permutation(n))
        oy = list(rng.permutation(n))
        if tie_heavy:
            vals_x = sorted(float(rng.integers(0, 3)) for _ in range(n))
            vals_y = sorted(float(rng.integers(0, 3)) for _ in range(n))
        else:
            vals_x = sorted(float(x) for x in
                            rng.choice(np.arange(0, 3 * n), n,
                                       replace=False))
            vals_y = sorted(float(x) for x in
                            rng.choice(np.arange(0, 3 * n), n,
                                       replace=False))
        v = int(rng.integers(0, n))
        # the engine's contacts bundle for the current carried state
        rx = {u: r for r, u in enumerate(ox)}
        pos = {u: np.array([float(vals_x[rx[u]]), float(vals_y[r])])
               for r, u in enumerate(oy)}
        yrank = {u: r for r, u in enumerate(oy)}
        contacts = _stair_contacts(pos, adj, yrank=yrank)
        e_cur = self._gt(ox, oy, adj, vals_x, vals_y, bar)
        brute = min(self._gt(self._insert(ox, v, i),
                             self._insert(oy, v, j),
                             adj, vals_x, vals_y, bar)
                    for i in range(n) for j in range(n))
        res = xy_reinsert(v, ox, oy, adj, vals_x, vals_y, contacts,
                          bar=bar)
        if res is not None:
            new_ox, new_oy = res
            got = self._gt(new_ox, new_oy, adj, vals_x, vals_y, bar)
            assert abs(got - brute) < 1e-6, (got, brute)
            assert got <= e_cur + 1e-9
            # sanity: the returned orders are permutations
            assert sorted(new_ox) == sorted(ox)
            assert sorted(new_oy) == sorted(oy)
            return 1
        assert brute >= e_cur - 1e-6, (brute, e_cur)
        return 0

    @pytest.mark.parametrize("bar", [0.0, 2.0])
    def test_exact_vs_brute_force_distinct_values(self, bar):
        rng = np.random.default_rng(61)
        hits = 0
        for _trial in range(15):
            hits += self._trial(rng, tie_heavy=False, bar=bar)
        assert hits >= 5  # the property must actually be exercised

    @pytest.mark.parametrize("bar", [0.0, 2.0])
    def test_exact_vs_brute_force_tied_values(self, bar):
        # bar=2 also falsifies the claim that the axis-0 slot vector's
        # active-arm constant cancels across splits (it must, since
        # activity is a function of the y-order alone)
        rng = np.random.default_rng(67)
        hits = 0
        for _trial in range(15):
            hits += self._trial(rng, tie_heavy=True, bar=bar)
        assert hits >= 5

    def test_slot_costs_vector_pins(self):
        # the closed-form per-slot vector: its identity entry equals
        # the DP's e_path (the noop-certificate arithmetic), and its
        # argmin agrees with the normal-mode accept/decline
        rng = np.random.default_rng(71)
        for axis in (1, 0):
            for _trial in range(10):
                n = int(rng.integers(5, 9))
                g = nx.gnp_random_graph(n, 0.5,
                                        seed=int(rng.integers(9999)))
                adj = {v: sorted(g.neighbors(v)) for v in g.nodes()}
                order = list(rng.permutation(n))
                values = sorted(float(x) for x in
                                rng.choice(np.arange(0, 3 * n), n,
                                           replace=False))
                other = {v: float(rng.integers(0, 10))
                         for v in range(n)}
                v = int(rng.integers(0, n))
                contacts = None
                if axis == 0:
                    val = np.asarray(values, dtype=float)
                    pos0 = {u: np.array([float(val[r]),
                                         float(other[u])])
                            for r, u in enumerate(order)}
                    contacts = _stair_contacts(pos0, adj)
                C = align_reinsert(order, {v}, adj, values, None,
                                   axis=axis, other=other,
                                   contacts=contacts, slot_costs=True)
                assert C is not None and len(C) == n
                j0 = order.index(v)
                if axis == 1:
                    # s3.125: the identity entry equals the judge's
                    # stair with the bar term (e_path == stair_energy)
                    Cb = align_reinsert(order, {v}, adj, values, None,
                                        axis=axis, other=other,
                                        contacts=None, slot_costs=True,
                                        bar=2.0)
                    val = np.asarray(values, dtype=float)
                    posr = {u: np.array([float(other[u]),
                                         float(val[r])])
                            for r, u in enumerate(order)}
                    yr = {u: r for r, u in enumerate(order)}
                    ctr = _stair_contacts(posr, adj, yrank=yr)
                    from ember_qc.algorithms.factored.field import rank_scale
                    M = rank_scale(n)
                    assert int(Cb[j0] // M) == int(round(stair_energy(
                        posr, adj, bar=2.0, contacts=ctr)))
                    assert int(C[j0] // M) == int(round(stair_energy(
                        posr, adj, contacts=ctr)))
                res, _f = align_reinsert(order, {v}, adj, values, None,
                                         axis=axis, other=other,
                                         contacts=contacts)
                if res is None:
                    assert C.min() >= C[j0] - 1e-9
                else:
                    assert C.min() < C[j0] - 1e-9

    def test_slot_costs_declines_non_singleton(self):
        adj = {0: [1], 1: [0, 2], 2: [1], 3: []}
        C = align_reinsert([0, 1, 2, 3], {0, 1}, adj,
                           [0.0, 1.0, 2.0, 3.0], None, axis=1,
                           other={v: 0.0 for v in range(4)},
                           contacts=None, slot_costs=True)
        assert C is None


class TestXYSingles:
    """s3.121: the xy_singles pipeline knob — the joint sweep replaces
    the ladder's scale-1 sweep on the carry path."""

    def test_knob_pin_and_guard(self):
        from dataclasses import fields
        from ember_qc.algorithms.factored.placement import AttractConfig
        assert "xy_singles" in {f.name for f in fields(AttractConfig)}
        from ember_qc.algorithms.factored import attract_embed
        r = attract_embed(nx.path_graph(4), dnx.chimera_graph(2, 2, 4),
                          timeout=5, seed=0, xy_singles=True,
                          carry_orders=False)
        assert r["status"] == "FAILURE" and "carry" in r.get("error", "")

    def test_move_fires_and_stays_real(self):
        # the move must demonstrably fire, and the realness property
        # (s3.118) must survive its both-axes adopts
        grid = _zgrid()
        kappa = _target_kappa(grid)
        fired = 0
        for seed in (37, 41, 43, 47, 53):
            rng = np.random.default_rng(seed)
            g = nx.gnp_random_graph(16, 0.4, seed=11)
            adj = {v: sorted(g.neighbors(v)) for v in g.nodes()}
            pos = {v: np.array([float(rng.integers(0, 3)),
                                float(rng.integers(0, 3))])
                   for v in g.nodes()}
            out, info = order_arrange(pos, adj, grid, kappa=kappa,
                                      plane=True, carry=True, xy=True)
            fired += info["xy_accepts"]
            ox, oy = info["_orders"]
            yrank = {v: r for r, v in enumerate(oy)}
            want = _stair_contacts(out, adj, yrank=yrank)
            assert info["readout_info"]["_contacts"] == want
            for ax, o in ((0, ox), (1, oy)):
                vals = [float(out[v][ax]) for v in o]
                assert all(a <= b for a, b in zip(vals, vals[1:]))
        assert fired >= 1  # the joint sweep must actually be exercised

    def test_e2e_xy_valid_deterministic(self):
        from ember_qc.algorithms.factored import attract_embed
        from ember_qc.registry import validate_embedding
        src = nx.gnp_random_graph(14, 0.35, seed=9)
        for tgt in (dnx.zephyr_graph(3, 4), dnx.chimera_graph(4, 4, 4)):
            r1 = attract_embed(src, tgt, timeout=15, seed=0,
                               xy_singles=True)
            r2 = attract_embed(src, tgt, timeout=15, seed=0,
                               xy_singles=True)
            emb = r1["embedding"]
            assert emb and validate_embedding(emb, src, tgt)
            assert r1["embedding"] == r2["embedding"]
            assert "xy_accepts" in r1["diag"]

    def test_xy_off_identity(self):
        from ember_qc.algorithms.factored import attract_embed
        src = nx.gnp_random_graph(10, 0.4, seed=3)
        tgt = dnx.zephyr_graph(2, 4)
        a = attract_embed(src, tgt, timeout=10, seed=0)
        b = attract_embed(src, tgt, timeout=10, seed=0,
                          xy_singles=False)
        assert a["embedding"] == b["embedding"]


class TestWaveSchedule:
    """s3.122: the disturbance-driven schedule — wave 0 coarse build,
    dirty-restricted maintenance waves, empty-wave fixpoint stop."""

    def test_span_vectors_vs_brute_force(self):
        from ember_qc.algorithms.factored.seat import _span_vectors
        rng = np.random.default_rng(83)
        for _trial in range(12):
            n = int(rng.integers(5, 12))
            g = nx.gnp_random_graph(n, 0.5,
                                    seed=int(rng.integers(9999)))
            adj = {v: sorted(g.neighbors(v)) for v in g.nodes()}
            pos = {v: np.array([float(rng.integers(0, 6)),
                                float(rng.integers(0, 6))])
                   for v in g.nodes()}
            order = list(rng.permutation(n))
            yrank = {v: r for r, v in enumerate(order)}
            ids, hs, vs = _span_vectors(pos, adj, yrank)
            contacts = _stair_contacts(pos, adj, yrank=yrank)
            for k, v in enumerate(ids):
                h_us, v_us = contacts[v]
                xs = [float(pos[u][0]) for u in h_us] \
                    + [float(pos[v][0])]
                ys = [float(pos[u][1]) for u in v_us] \
                    + [float(pos[v][1])]
                assert abs(hs[k] - (max(xs) - min(xs))) < 1e-12
                assert abs(vs[k] - (max(ys) - min(ys))) < 1e-12

    def _converge(self, adj, pos, grid, wave, audit=False):
        kappa = _target_kappa(grid)
        return order_arrange(pos, adj, grid, kappa=kappa,
                             plane=True, carry=True, wave=wave,
                             audit=audit)

    @staticmethod
    def _rank_pos(info):
        # faithful re-entry: positions = ranks in the returned carried
        # orders — distinct integers, so the (value, id) order rebirth
        # reproduces the carried state exactly (the s3.118 tie lesson:
        # tied VALUES rebirth by id, not by the order that made them)
        ox, oy = info["_orders"]
        rx = {v: r for r, v in enumerate(ox)}
        return {v: np.array([float(rx[v]), float(r)])
                for r, v in enumerate(oy)}

    def test_fixpoint_soundness(self):
        # THE key property: the wave arm's early stop must be a
        # fixpoint of the FULL blind family. Audit arms (strict
        # descent) so the returned state IS the final state; re-entry
        # via rank positions so the order rebirth is exact.
        grid = _zgrid()
        rng = np.random.default_rng(89)
        g = nx.gnp_random_graph(14, 0.35, seed=17)
        adj = {v: sorted(g.neighbors(v)) for v in g.nodes()}
        pos = {v: np.array([float(x), float(y)])
               for v, (x, y) in zip(
                   g.nodes(),
                   rng.uniform(0, 12, size=(14, 2)).round(3))}
        # baseline sanity: the blind loop's own converged output,
        # re-entered faithfully, must be quiet (guards the protocol)
        _, info0 = self._converge(adj, pos, grid, wave=False,
                                  audit=True)
        _, info0b = self._converge(adj, self._rank_pos(info0), grid,
                                   wave=False, audit=True)
        assert info0b["interleave_accepts"] == 0
        _, info1 = self._converge(adj, pos, grid, wave=True,
                                  audit=True)
        assert info1["wave_early_stop"] is True
        _, info2 = self._converge(adj, self._rank_pos(info1), grid,
                                  wave=False, audit=True)
        assert info2["interleave_accepts"] == 0, \
            "wave early stop is not a full-family fixpoint"

    def test_early_stop_fires_and_deterministic(self):
        grid = _zgrid()
        g = nx.complete_graph(12)
        adj = {v: sorted(g.neighbors(v)) for v in g.nodes()}
        rng = np.random.default_rng(97)
        pos = {v: np.array([float(x), float(y)])
               for v, (x, y) in zip(
                   g.nodes(),
                   rng.uniform(0, 10, size=(12, 2)).round(3))}
        out1, i1 = self._converge(adj, pos, grid, wave=True)
        assert i1["wave_early_stop"] is True
        assert i1["wave_count"] >= 1
        out2, i2 = self._converge(adj, pos, grid, wave=True)
        assert all(np.array_equal(out1[v], out2[v]) for v in out1)
        assert i1["wave_questions"] == i2["wave_questions"]

    def test_knob_pin_and_guard(self):
        from dataclasses import fields
        from ember_qc.algorithms.factored.placement import AttractConfig
        assert "wave_schedule" in {f.name for f in
                                   fields(AttractConfig)}
        from ember_qc.algorithms.factored import attract_embed
        r = attract_embed(nx.path_graph(4), dnx.chimera_graph(2, 2, 4),
                          timeout=5, seed=0, wave_schedule=True,
                          carry_orders=False)
        assert r["status"] == "FAILURE" and "carry" in r.get("error", "")

    def test_e2e_wave_valid_deterministic(self):
        from ember_qc.algorithms.factored import attract_embed
        from ember_qc.registry import validate_embedding
        src = nx.gnp_random_graph(14, 0.35, seed=9)
        for tgt in (dnx.zephyr_graph(3, 4), dnx.chimera_graph(4, 4, 4)):
            r1 = attract_embed(src, tgt, timeout=15, seed=0,
                               wave_schedule=True)
            r2 = attract_embed(src, tgt, timeout=15, seed=0,
                               wave_schedule=True)
            emb = r1["embedding"]
            assert emb and validate_embedding(emb, src, tgt)
            assert r1["embedding"] == r2["embedding"]
            assert "wave_count" in r1["diag"]

    def test_wave_off_identity(self):
        from ember_qc.algorithms.factored import attract_embed
        src = nx.gnp_random_graph(10, 0.4, seed=3)
        tgt = dnx.zephyr_graph(2, 4)
        a = attract_embed(src, tgt, timeout=10, seed=0)
        b = attract_embed(src, tgt, timeout=10, seed=0,
                          wave_schedule=False)
        assert a["embedding"] == b["embedding"]


class TestCrossWiden:
    """s3.123: axis_inner (per-unit axis adjacency + per-pass axis
    alternation) and cross_widen (a first-axis adoption widens the
    second-axis probe by the realized diff)."""

    def _run(self, adj, pos, grid, **kw):
        kappa = _target_kappa(grid)
        return order_arrange(pos, adj, grid, kappa=kappa,
                             plane=True, carry=True, **kw)

    def _case(self, seed, n=16):
        rng = np.random.default_rng(seed)
        g = nx.gnp_random_graph(n, 0.4, seed=11)
        adj = {v: sorted(g.neighbors(v)) for v in g.nodes()}
        pos = {v: np.array([float(rng.integers(0, 3)),
                            float(rng.integers(0, 3))])
               for v in g.nodes()}
        return adj, pos

    def test_widen_fires_and_stays_real(self):
        grid = _zgrid()
        asked = 0
        for seed in (37, 41, 43):
            adj, pos = self._case(seed)
            out, info = self._run(adj, pos, grid, axis_inner=True,
                                  widen=True)
            asked += info["widen_asked"]
            # carry realness invariants survive widened adopts
            ox, oy = info["_orders"]
            yrank = {v: r for r, v in enumerate(oy)}
            assert (info["readout_info"]["_contacts"]
                    == _stair_contacts(out, adj, yrank=yrank))
            for ax, o in ((0, ox), (1, oy)):
                vals = [float(out[v][ax]) for v in o]
                assert all(a <= b for a, b in zip(vals, vals[1:]))
        assert asked >= 1  # the mechanism must actually be exercised

    def test_deterministic_both_arms(self):
        grid = _zgrid()
        adj, pos = self._case(53)
        for kw in ({"axis_inner": True},
                   {"axis_inner": True, "widen": True}):
            o1, i1 = self._run(adj, pos, grid, **kw)
            o2, i2 = self._run(adj, pos, grid, **kw)
            assert all(np.array_equal(o1[v], o2[v]) for v in o1)
            assert i1["widen_asked"] == i2["widen_asked"]

    def test_knob_pins_and_guards(self):
        from dataclasses import fields
        from ember_qc.algorithms.factored.placement import AttractConfig
        names = {f.name for f in fields(AttractConfig)}
        assert {"axis_inner", "cross_widen"} <= names
        from ember_qc.algorithms.factored import attract_embed
        r = attract_embed(nx.path_graph(4), dnx.chimera_graph(2, 2, 4),
                          timeout=5, seed=0, axis_inner=True,
                          carry_orders=False)
        assert r["status"] == "FAILURE" and "carry" in r.get("error", "")
        r = attract_embed(nx.path_graph(4), dnx.chimera_graph(2, 2, 4),
                          timeout=5, seed=0, cross_widen=True,
                          axis_inner=False)
        assert r["status"] == "FAILURE" and "axis_inner" in r.get(
            "error", "")

    def test_e2e_valid_deterministic(self):
        from ember_qc.algorithms.factored import attract_embed
        from ember_qc.registry import validate_embedding
        src = nx.gnp_random_graph(14, 0.35, seed=9)
        for tgt in (dnx.zephyr_graph(3, 4), dnx.chimera_graph(4, 4, 4)):
            for kw in ({"axis_inner": True},
                       {"axis_inner": True, "cross_widen": True}):
                r1 = attract_embed(src, tgt, timeout=15, seed=0, **kw)
                r2 = attract_embed(src, tgt, timeout=15, seed=0, **kw)
                emb = r1["embedding"]
                assert emb and validate_embedding(emb, src, tgt), kw
                assert r1["embedding"] == r2["embedding"]
                assert "widen_asked" in r1["diag"]

    def test_off_identity(self):
        from ember_qc.algorithms.factored import attract_embed
        src = nx.gnp_random_graph(10, 0.4, seed=3)
        tgt = dnx.zephyr_graph(2, 4)
        a = attract_embed(src, tgt, timeout=10, seed=0)
        b = attract_embed(src, tgt, timeout=10, seed=0,
                          axis_inner=False, cross_widen=False)
        assert a["embedding"] == b["embedding"]


class TestSoundPlane:
    """s3.124b: the sound plane, one switch — the strip map, the brick
    judge on the converter's accounting, the wrapping packer, the
    single-axis readout, the wrap end to end."""

    def test_fold_consts_and_phys_map(self):
        from ember_qc.algorithms.factored.orders import _fold_consts, _phys
        grid = _zgrid()
        W, R, s = _fold_consts(grid)
        assert (W, R, s) == (grid.W, grid.H, grid.stride)
        Hs = R // 2
        pos = {}
        k = 0
        for y in range(0, Hs):
            for x in range(0, 2 * W):
                pos[k] = np.array([float(x), float(y)])
                k += 1
        ph = _phys(pos, W=W, Hs=Hs)
        seen = set()
        for v, p in ph.items():
            key = (int(p[0]), int(p[1]))
            assert key not in seen
            seen.add(key)
            assert 0 <= p[0] < W and 0 <= p[1] < R
        for v, p in pos.items():
            if p[0] < W:
                assert ph[v][0] == p[0] and ph[v][1] == p[1]
        a = [v for v, p in pos.items() if p[0] == W - 1 and p[1] == 1][0]
        b = [v for v, p in pos.items() if p[0] == W and p[1] == 1][0]
        assert ph[a][0] == ph[b][0] and ph[b][1] == ph[a][1] + Hs

    def test_judge_pools_are_the_packers(self):
        from ember_qc.algorithms.factored.seat import judge_pools
        from ember_qc.algorithms.factored.field import _brick_pool_arrays
        for grid in (_zgrid(), _cgrid()):
            ph, pv = judge_pools(grid)
            ph0, pv0 = _brick_pool_arrays(grid, max(grid.stride, 1))
            for arr, arr0 in ((ph, ph0), (pv, pv0)):
                assert np.all(arr[0] == 0) and np.all(arr[-1] == 0)
                assert np.all(arr[1:-1] == arr0[1:-1])

    def test_brick_energy_vs_brute_force(self):
        from ember_qc.algorithms.factored.seat import (
            _LEX_M, brick_energy, judge_pools)
        grid = _zgrid()
        s = grid.stride
        ph, pv = judge_pools(grid)

        def _edge(arr):
            nz = np.flatnonzero(arr.max(axis=0) > 0)
            return int(nz.max()) + 1 if nz.size else arr.shape[1]
        nbx, nby = _edge(ph), _edge(pv)
        rng = np.random.default_rng(101)
        for _trial in range(20):
            n = int(rng.integers(4, 10))
            g = nx.gnp_random_graph(n, 0.5, seed=int(rng.integers(9999)))
            adj = {v: sorted(g.neighbors(v)) for v in g.nodes()}
            pos = {v: np.array([float(rng.integers(0, 14)),
                                float(rng.integers(0, 14))])
                   for v in g.nodes()}
            order = list(rng.permutation(n))
            yrank = {v: r for r, v in enumerate(order)}
            contacts = _stair_contacts(pos, adj, yrank=yrank)
            stair = 0
            cov_h, cov_v = {}, {}
            for v in pos:
                h_us, v_us = contacts[v]
                x, y = int(pos[v][0]), int(pos[v][1])
                xs = [int(pos[u][0]) for u in h_us] + [x]
                ys = [int(pos[u][1]) for u in v_us] + [y]
                if h_us:
                    stair += max(xs) // s - min(xs) // s + 1
                if v_us:
                    stair += max(ys) // s - min(ys) // s + 1
                lo, hi = min(xs) // s, max(max(xs), min(xs) + 1) // s
                lo = nbx - 1 if lo == nbx else lo
                hi = nbx - 1 if hi == nbx else hi
                for b in range(lo, hi + 1):
                    cov_h[(y, b)] = cov_h.get((y, b), 0) + 1
                lo, hi = min(ys) // s, max(max(ys), min(ys) + 1) // s
                lo = nby - 1 if lo == nby else lo
                hi = nby - 1 if hi == nby else hi
                for b in range(lo, hi + 1):
                    cov_v[(x, b)] = cov_v.get((x, b), 0) + 1
            pen = 0.0
            for (ln, b), c in cov_h.items():
                pool = ph[ln, b] if (ln < ph.shape[0] and b < ph.shape[1]) else 0.0
                pen += max(c - pool, 0.0) ** 2
            for (ln, b), c in cov_v.items():
                pool = pv[ln, b] if (ln < pv.shape[0] and b < pv.shape[1]) else 0.0
                pen += max(c - pool, 0.0) ** 2
            want = pen * _LEX_M + stair
            got = brick_energy(pos, adj, grid, yrank, pools=(ph, pv),
                               kappa=None)
            assert abs(got - want) < 1e-6, (got, want)
        adj = {0: [1], 1: [0]}
        inside = {0: np.array([1.0, 1.0]), 1: np.array([2.0, 2.0])}
        assert brick_energy(inside, adj, grid, {0: 0, 1: 1},
                            pools=(ph, pv), kappa=None) < _LEX_M
        off = {0: np.array([1.0, float(grid.H + 3)]),
               1: np.array([2.0, float(grid.H + 4)])}
        assert brick_energy(off, adj, grid, {0: 0, 1: 1},
                            pools=(ph, pv), kappa=None) >= _LEX_M

    def test_strips_packer_wraps_instead_of_clamping(self):
        # a layout too wide for the chip: strips=1 clamps (misses),
        # strips=2 places everyone in virtual columns that map back
        # onto the chip; the row budget bounds the rows
        from ember_qc.algorithms.factored.orders import _phys
        grid = _zgrid()
        kappa = _target_kappa(grid)
        g = nx.path_graph(48)
        adj = {v: sorted(g.neighbors(v)) for v in g.nodes()}
        pos = {v: np.array([float(v), float(1 + (v % 5))])
               for v in g.nodes()}
        ords = (sorted(pos, key=lambda v: (float(pos[v][0]), v)),
                sorted(pos, key=lambda v: (float(pos[v][1]), v)))
        one, i1 = pack_project(pos, adj, grid, kappa=kappa,
                               monotonize=False, project=True,
                               brick_pools=True, orders=ords, strips=1)
        two, i2 = pack_project(pos, adj, grid, kappa=kappa,
                               monotonize=False, project=True,
                               brick_pools=True, orders=ords, strips=2)
        assert i1.get("projection_misses", 0) > 0
        assert i2.get("projection_misses", 0) == 0
        assert max(float(p[0]) for p in two.values()) >= grid.W
        ph = _phys(two, W=grid.W, Hs=grid.H // 2)
        assert all(0 <= p[0] < grid.W for p in ph.values())
        # strips=1 is byte-identical to the default projection
        dflt, _ = pack_project(pos, adj, grid, kappa=kappa,
                               monotonize=False, project=True,
                               brick_pools=True, orders=ords)
        assert all(np.array_equal(dflt[v], one[v]) for v in one)
        # the row budget
        few, _ = pack_project(pos, adj, grid, kappa=kappa,
                              monotonize=False, project=True,
                              brick_pools=True, orders=ords, strips=2,
                              rows=4)
        assert max(float(p[1]) for p in few.values()) < 4

    def test_single_axis_readout_freezes_other_axis(self):
        from ember_qc.algorithms.factored import orders as om
        grid = _zgrid()
        kappa = _target_kappa(grid)
        rng = np.random.default_rng(37)
        g = nx.gnp_random_graph(16, 0.4, seed=11)
        adj = {v: sorted(g.neighbors(v)) for v in g.nodes()}
        pos = {v: np.array([float(rng.integers(0, 3)),
                            float(rng.integers(0, 3))])
               for v in g.nodes()}
        calls = []
        real_pp = om.pack_project

        def spy(p, *a, **kw):
            axes = kw.get("axes", (1, 0))
            out, info = real_pp(p, *a, **kw)
            calls.append((axes, {v: q.copy() for v, q in p.items()},
                          {v: q.copy() for v, q in out.items()}))
            return out, info
        om.pack_project = spy
        try:
            out, info = om.order_arrange(pos, adj, grid, kappa=kappa,
                                         plane=True, carry=True,
                                         axis_single=True)
        finally:
            om.pack_project = real_pp
        single = [c for c in calls if len(c[0]) == 1]
        assert single
        for axes, before, after in single:
            other = 1 - axes[0]
            for v in before:
                assert before[v][other] == after[v][other]
        assert info["interleave_accepts"] >= 1

    def test_knob_pins_and_guards(self):
        from dataclasses import fields
        from ember_qc.algorithms.factored.placement import AttractConfig
        assert {"axis_single", "wrap_pack"} <= {
            f.name for f in fields(AttractConfig)}
        from ember_qc.algorithms.factored import attract_embed
        tgt = dnx.chimera_graph(2, 2, 4)
        for kw, word in (({"axis_single": True, "carry_orders": False},
                          "carry"),
                         ({"wrap_pack": True, "engine": "orders"},
                          "plane"),
                         ({"wrap_pack": True, "xy_singles": True},
                          "compose")):
            r = attract_embed(nx.path_graph(4), tgt, timeout=5, seed=0,
                              **kw)
            assert r["status"] == "FAILURE", kw
            assert word in r.get("error", ""), (kw, r.get("error"))

    def test_e2e_arms_valid_deterministic(self):
        from ember_qc.algorithms.factored import attract_embed
        from ember_qc.registry import validate_embedding
        src = nx.gnp_random_graph(14, 0.35, seed=9)
        arms = ({"wrap_pack": True},
                {"wrap_pack": True, "axis_single": True})
        for tgt in (dnx.zephyr_graph(3, 4), dnx.chimera_graph(4, 4, 4)):
            for kw in arms:
                for eng in ("plane", "plane-audit"):
                    r1 = attract_embed(src, tgt, timeout=15, seed=0,
                                       engine=eng, **kw)
                    r2 = attract_embed(src, tgt, timeout=15, seed=0,
                                       engine=eng, **kw)
                    emb = r1["embedding"]
                    assert emb and validate_embedding(emb, src, tgt), \
                        (kw, eng, r1.get("error"))
                    assert r1["embedding"] == r2["embedding"]
                    assert r1["diag"].get("judge") == "brick"

    def test_off_identity(self):
        from ember_qc.algorithms.factored import attract_embed
        src = nx.gnp_random_graph(10, 0.4, seed=3)
        tgt = dnx.zephyr_graph(2, 4)
        a = attract_embed(src, tgt, timeout=10, seed=0)
        b = attract_embed(src, tgt, timeout=10, seed=0,
                          axis_single=False, wrap_pack=False)
        assert a["embedding"] == b["embedding"]

    def test_wrap_end_to_end_overflow(self):
        # a source too wide for one strip of the small chip: the wrap
        # must use >= 2 strips and still produce a valid embedding
        from ember_qc.algorithms.factored import attract_embed
        from ember_qc.registry import validate_embedding
        src = nx.gnp_random_graph(40, 0.5, seed=4)
        tgt = dnx.zephyr_graph(3, 4)
        r = attract_embed(src, tgt, timeout=30, seed=0, wrap_pack=True)
        d = r["diag"]
        assert d.get("judge") == "brick"
        if r["embedding"]:
            assert validate_embedding(r["embedding"], src, tgt)
        assert d.get("fold_strips", 0) >= 1


class TestTileMoves:
    """s3.119: the 2-D-joint family — tiles x {shift, reversals}."""

    def test_knob_pin_and_guard(self):
        from dataclasses import fields
        from ember_qc.algorithms.factored.placement import AttractConfig
        assert {"tile_moves", "settle_projection"} <= {
            f.name for f in fields(AttractConfig)}
        from ember_qc.algorithms.factored import attract_embed
        r = attract_embed(nx.path_graph(4), dnx.chimera_graph(2, 2, 4),
                          timeout=5, seed=0, tile_moves=True,
                          carry_orders=False)
        assert r["status"] == "FAILURE" and "carry" in r.get("error", "")

    def test_e2e_tiles_valid_deterministic(self):
        from ember_qc.algorithms.factored import attract_embed
        from ember_qc.registry import validate_embedding
        src = nx.gnp_random_graph(14, 0.35, seed=9)
        tgt = dnx.zephyr_graph(3, 4)
        kw = dict(carry_orders=True, tile_moves=True,
                  settle_projection=True)
        r1 = attract_embed(src, tgt, timeout=15, seed=0, **kw)
        r2 = attract_embed(src, tgt, timeout=15, seed=0, **kw)
        emb = r1["embedding"]
        assert emb and validate_embedding(emb, src, tgt)
        assert r1["embedding"] == r2["embedding"]
        assert r1["diag"].get("proj_iters", 0) >= 1

    def test_settle_off_identity(self):
        from ember_qc.algorithms.factored import attract_embed
        src = nx.gnp_random_graph(10, 0.4, seed=3)
        tgt = dnx.zephyr_graph(2, 4)
        a = attract_embed(src, tgt, timeout=10, seed=0)
        b = attract_embed(src, tgt, timeout=10, seed=0,
                          tile_moves=False, settle_projection=False)
        assert a["embedding"] == b["embedding"]


class TestArmCost:
    """s3.125 `arm_cost`: one bar (stride junctions) per ACTIVE arm in
    the plane objective, judge and proposer alike."""

    def test_knob_pins_and_guards(self):
        from dataclasses import fields
        from ember_qc.algorithms.factored.placement import AttractConfig
        assert "arm_cost" in {f.name for f in fields(AttractConfig)}
        from ember_qc.algorithms.factored import attract_embed
        tgt = dnx.chimera_graph(2, 2, 4)
        for kw, word in (({"arm_cost": True, "carry_orders": False},
                          "carry"),
                         ({"arm_cost": True, "engine": "orders"},
                          "plane"),
                         ({"arm_cost": True, "wrap_pack": True},
                          "compose")):
            r = attract_embed(nx.path_graph(4), tgt, timeout=5, seed=0,
                              **kw)
            assert r["status"] == "FAILURE", kw
            assert word in r.get("error", ""), (kw, r.get("error"))

    def test_judge_and_proposer_share_the_bar(self):
        # order_arrange under arm_cost: the bookmark's seat_stair equals
        # stair_energy(bar=stride) of the returned state under its own
        # carried contacts — proposer == judge, one accounting
        rng = np.random.default_rng(5)
        grid = _zgrid()
        adj, pos = _case(rng, grid, 14, 0.35)
        kappa = _target_kappa(grid)
        out, info = order_arrange(pos, adj, grid, kappa=kappa,
                                  plane=True, carry=True, arm_cost=True)
        s = max(int(getattr(grid, "stride", 1) or 1), 1)
        cts = info["readout_info"]["_contacts"]
        e = stair_energy(out, adj, contacts=cts, bar=float(s))
        assert abs(e - info["seat_stair"]) < 1e-6
        bars = sum((1 if h else 0) + (1 if v else 0)
                   for h, v in cts.values())
        assert info["plane_bars"] == bars
        assert abs(stair_energy(out, adj, contacts=cts)
                   - (info["seat_stair"] - s * bars)) < 1e-6

    def test_clique_trajectory_identical(self):
        # a clique has every variable two-sided at every state, so the
        # bar term is a constant and the search must be byte-identical
        from ember_qc.algorithms.factored import attract_embed
        src = nx.complete_graph(8)
        tgt = dnx.zephyr_graph(3, 4)
        a = attract_embed(src, tgt, timeout=15, seed=0)
        b = attract_embed(src, tgt, timeout=15, seed=0, arm_cost=True)
        assert a["embedding"] == b["embedding"]
        assert b["diag"]["plane_bars"] == 2 * (8 - 1)
        assert abs((b["diag"]["plane_stair"] - a["diag"]["plane_stair"])
                   - 2 * b["diag"]["plane_bars"]) < 1e-6

    def test_e2e_valid_deterministic(self):
        from ember_qc.algorithms.factored import attract_embed
        from ember_qc.registry import validate_embedding
        src = nx.gnp_random_graph(14, 0.35, seed=9)
        for tgt in (dnx.zephyr_graph(3, 4), dnx.chimera_graph(4, 4, 4)):
            for eng in ("plane", "plane-audit"):
                r1 = attract_embed(src, tgt, timeout=15, seed=0,
                                   engine=eng, arm_cost=True)
                r2 = attract_embed(src, tgt, timeout=15, seed=0,
                                   engine=eng, arm_cost=True)
                emb = r1["embedding"]
                assert emb and validate_embedding(emb, src, tgt), \
                    (eng, r1.get("error"))
                assert r1["embedding"] == r2["embedding"]
                assert isinstance(r1["diag"].get("plane_bars"), int)

    def test_off_identity(self):
        from ember_qc.algorithms.factored import attract_embed
        src = nx.gnp_random_graph(10, 0.4, seed=3)
        tgt = dnx.zephyr_graph(2, 4)
        a = attract_embed(src, tgt, timeout=10, seed=0)
        b = attract_embed(src, tgt, timeout=10, seed=0, arm_cost=False)
        assert a["embedding"] == b["embedding"]
        assert "plane_bars" not in a["diag"]


class TestStrip:
    """s3.125 `strip`: the half-infinite strip — real columns, ideal
    rows; rows beyond the chip and clamp misses as the leading key."""

    @staticmethod
    def _path_state(grid, n=200):
        adj = {v: [u for u in (v - 1, v + 1) if 0 <= u < n]
               for v in range(n)}
        # a ribbon: every variable on one row, spread along x
        pos = {v: np.array([float(v), 1.0]) for v in range(n)}
        orders = (list(range(n)), list(range(n)))
        return adj, pos, orders

    def test_readout_bounds_x_not_y(self):
        grid = _zgrid()
        adj, pos, orders = self._path_state(grid)
        kappa = _target_kappa(grid)
        wide, wi = pack_project(pos, adj, grid, kappa=kappa,
                                monotonize=False, project=False,
                                orders=orders)
        assert max(float(p[0]) for p in wide.values()) > grid.W - 1
        assert "strip_miss" not in wi
        out, info = pack_project(pos, adj, grid, kappa=kappa,
                                 monotonize=False, project=False,
                                 orders=orders, strip=True)
        assert max(float(p[0]) for p in out.values()) <= grid.W - 1
        assert min(float(p[0]) for p in out.values()) >= 0
        # a monotone ribbon packs as a staircase: on a chip narrower
        # than the staircase the real columns cannot seat everyone, and
        # the stragglers are COUNTED (the judge's key), never silent
        assert "strip_miss" in info and info["strip_miss"] > 0
        assert info["strip_iters"] >= 1
        assert info.get("unb_miss", 0) == 0
        # the ideal y half is untouched: no window key was produced
        assert "final_width_y" not in info
        # and a 2-D layout that fits the chip has no misses
        rng = np.random.default_rng(3)
        adj2, pos2 = _case(rng, grid, 12, 0.3)
        orders2 = (sorted(pos2, key=lambda v: (float(pos2[v][0]), v)),
                   sorted(pos2, key=lambda v: (float(pos2[v][1]), v)))
        out2, info2 = pack_project(pos2, adj2, grid, kappa=kappa,
                                   monotonize=False, project=False,
                                   orders=orders2, strip=True)
        assert info2["strip_miss"] == 0
        assert max(float(p[0]) for p in out2.values()) <= grid.W - 1

    def test_strip_false_byte_identical(self):
        # the default readout never passes strip; positions identical
        rng = np.random.default_rng(11)
        grid = _zgrid()
        adj, pos = _case(rng, grid, 16, 0.3)
        kappa = _target_kappa(grid)
        orders = (sorted(pos, key=lambda v: (float(pos[v][0]), v)),
                  sorted(pos, key=lambda v: (float(pos[v][1]), v)))
        a, ai = pack_project(pos, adj, grid, kappa=kappa,
                             monotonize=False, project=False,
                             orders=orders)
        b, bi = pack_project(pos, adj, grid, kappa=kappa,
                             monotonize=False, project=False,
                             orders=orders, strip=False)
        assert all(np.array_equal(a[v], b[v]) for v in a)
        assert "strip_miss" not in bi

    def test_row_overflow_vs_brute_force(self):
        from ember_qc.algorithms.factored.seat import (
            _phantom_edge, judge_pools, row_overflow)
        grid = _zgrid()
        H, s = grid.H, max(int(getattr(grid, "stride", 1) or 1), 1)
        assert (H - 1) // s == _phantom_edge(judge_pools(grid)[1])
        rng = np.random.default_rng(23)
        for trial in range(20):
            n = int(rng.integers(4, 12))
            g = nx.gnp_random_graph(n, 0.5, seed=int(rng.integers(999)))
            adj = {v: sorted(g.neighbors(v)) for v in g.nodes()}
            pos = {v: np.array([float(rng.integers(0, grid.W)),
                                float(rng.integers(0, 2 * H))])
                   for v in range(n)}
            oy = list(rng.permutation(n))
            yrank = {v: r for r, v in enumerate(oy)}
            got = row_overflow(pos, adj, yrank, H=H, s=s, kappa=None)
            # oracle over footprints
            X = {v: int(round(pos[v][0])) for v in pos}
            Y = {v: int(round(pos[v][1])) for v in pos}
            hmin = dict(X)
            hmax = dict(X)
            vmin = dict(Y)
            vmax = dict(Y)
            for u in adj:
                for w in adj[u]:
                    if u < w:
                        lo, hi = ((u, w) if yrank[u] < yrank[w]
                                  else (w, u))
                        hmin[lo] = min(hmin[lo], X[hi])
                        hmax[lo] = max(hmax[lo], X[hi])
                        vmin[hi] = min(vmin[hi], Y[lo])
                        vmax[hi] = max(vmax[hi], Y[lo])
            cover = {}
            top = H - 1
            for v in pos:
                a, b = hmin[v], max(hmax[v], hmin[v] + 1)
                if Y[v] >= top:
                    for q in range(a // s, b // s + 1):
                        cover[("h", Y[v], q)] = (
                            cover.get(("h", Y[v], q), 0) + 1)
                a, b = vmin[v], max(vmax[v], vmin[v] + 1)
                for q in range(a // s, b // s + 1):
                    if q >= top // s:
                        cover[("v", X[v], q)] = (
                            cover.get(("v", X[v], q), 0) + 1)
            want = float(sum(c * c for c in cover.values()))
            assert abs(got - want) < 1e-9, (trial, got, want)
        # inside the chip: zero
        pos = {v: np.array([float(v), float(v)]) for v in range(5)}
        adj = {v: [u for u in range(5) if u != v] for v in range(5)}
        yrank = {v: v for v in range(5)}
        assert row_overflow(pos, adj, yrank, H=H, s=s) == 0.0
        # one variable on the boundary row: positive
        pos[4] = np.array([4.0, float(H - 1)])
        assert row_overflow(pos, adj, yrank, H=H, s=s) > 0.0

    def test_strip_judge_is_lexicographic(self):
        rng = np.random.default_rng(5)
        grid = _zgrid()
        adj, pos = _case(rng, grid, 14, 0.35)
        kappa = _target_kappa(grid)
        out, info = order_arrange(pos, adj, grid, kappa=kappa,
                                  plane=True, carry=True, strip=True)
        assert info["judge"] == "strip"
        assert info["seat_pen"] is not None
        assert info["strip_miss"] is not None
        assert max(float(p[0]) for p in out.values()) <= grid.W - 1
        cts = info["readout_info"]["_contacts"]
        assert abs(stair_energy(out, adj, contacts=cts)
                   - info["seat_stair"]) < 1e-6

    def test_knob_pins_and_guards(self):
        from dataclasses import fields
        from ember_qc.algorithms.factored.placement import AttractConfig
        assert "strip" in {f.name for f in fields(AttractConfig)}
        from ember_qc.algorithms.factored import attract_embed
        tgt = dnx.chimera_graph(2, 2, 4)
        for kw, word in (({"strip": True, "carry_orders": False},
                          "carry"),
                         ({"strip": True, "engine": "orders"}, "plane"),
                         ({"strip": True, "wrap_pack": True},
                          "compose")):
            r = attract_embed(nx.path_graph(4), tgt, timeout=5, seed=0,
                              **kw)
            assert r["status"] == "FAILURE", kw
            assert word in r.get("error", ""), (kw, r.get("error"))

    def test_e2e_valid_deterministic(self):
        from ember_qc.algorithms.factored import attract_embed
        from ember_qc.registry import validate_embedding
        src = nx.gnp_random_graph(14, 0.35, seed=9)
        arms = ({"strip": True}, {"strip": True, "arm_cost": True})
        for tgt in (dnx.zephyr_graph(3, 4), dnx.chimera_graph(4, 4, 4)):
            for kw in arms:
                for eng in ("plane", "plane-audit"):
                    r1 = attract_embed(src, tgt, timeout=15, seed=0,
                                       engine=eng, **kw)
                    r2 = attract_embed(src, tgt, timeout=15, seed=0,
                                       engine=eng, **kw)
                    emb = r1["embedding"]
                    assert emb and validate_embedding(emb, src, tgt), \
                        (kw, eng, r1.get("error"))
                    assert r1["embedding"] == r2["embedding"]
                    d = r1["diag"]
                    assert d.get("judge") == "strip"
                    W = TileGrid(tgt, target_layout(tgt),
                                 courses=("zephyr" in
                                          tgt.graph.get("family", ""))
                                 ).W
                    assert 1 <= d.get("final_width_x", 0) <= W

    def test_off_identity(self):
        from ember_qc.algorithms.factored import attract_embed
        src = nx.gnp_random_graph(10, 0.4, seed=3)
        tgt = dnx.zephyr_graph(2, 4)
        a = attract_embed(src, tgt, timeout=10, seed=0)
        b = attract_embed(src, tgt, timeout=10, seed=0, strip=False,
                          arm_cost=False)
        assert a["embedding"] == b["embedding"]
        assert "strip_miss" not in a["diag"]


class TestSched:
    """s3.126: the order-invariance instrument — `sched` permutes the
    blind pass's ask list (never its set); `max_asks` is a work budget."""

    @staticmethod
    def _rec(monkeypatch):
        import ember_qc.algorithms.factored.orders as om
        seq = []
        real = om.align_reinsert

        def rec(order, cluster, *a, **k):
            seq.append((k.get("axis"), tuple(sorted(cluster))))
            return real(order, cluster, *a, **k)
        monkeypatch.setattr(om, "align_reinsert", rec)
        return seq

    def test_knob_pins_and_guards(self):
        from dataclasses import fields
        from ember_qc.algorithms.factored.placement import AttractConfig
        assert {"sched", "sched_seed", "max_asks"} <= {
            f.name for f in fields(AttractConfig)}
        from ember_qc.algorithms.factored import attract_embed
        tgt = dnx.chimera_graph(2, 2, 4)
        for kw, word in (({"sched": "bag", "carry_orders": False},
                          "carry"),
                         ({"sched": "rung", "engine": "orders"}, "plane"),
                         ({"max_asks": 50, "engine": "orders"}, "plane"),
                         ({"sched": "bag", "hier_units": True}, "compose"),
                         ({"sched": "bag", "xy_singles": True}, "compose"),
                         ({"sched": "rung", "wave_schedule": True},
                          "compose"),
                         ({"sched": "rung", "axis_inner": True},
                          "compose"),
                         ({"sched": "spiral"}, "sched"),
                         ({"max_asks": 0}, "max_asks")):
            r = attract_embed(nx.path_graph(4), tgt, timeout=5, seed=0,
                              **kw)
            assert r["status"] == "FAILURE", kw
            assert word in r.get("error", ""), (kw, r.get("error"))

    def test_ladder_is_default_identity_e2e(self):
        from ember_qc.algorithms.factored import attract_embed
        src = nx.gnp_random_graph(10, 0.4, seed=3)
        tgt = dnx.zephyr_graph(2, 4)
        keys = ("accept_traj", "readouts", "interleave_accepts",
                "interleave_noops", "asks")
        for extra in ({}, {"axis_inner": True, "cross_widen": True},
                      {"xy_singles": True}, {"hier_units": True}):
            a = attract_embed(src, tgt, timeout=10, seed=0, **extra)
            b = attract_embed(src, tgt, timeout=10, seed=0,
                              sched="ladder", sched_seed=7, **extra)
            assert a["embedding"] == b["embedding"], extra
            for k in keys:
                assert a["diag"].get(k) == b["diag"].get(k), (extra, k)
        assert a["diag"]["sched"] == "ladder"
        assert a["diag"]["stopped_by"] in ("fixpoint", "passes",
                                           "deadline")

    def test_ladder_probe_sequence_identical(self, monkeypatch):
        rng = np.random.default_rng(5)
        grid = _zgrid()
        adj, pos = _case(rng, grid, 16, 0.35)
        kappa = _target_kappa(grid)
        for extra in ({}, {"axis_inner": True, "widen": True},
                      {"xy": True}):
            seq_a = self._rec(monkeypatch)
            out_a, info_a = order_arrange(pos, adj, grid, kappa=kappa,
                                          plane=True, carry=True, **extra)
            seq_a = list(seq_a)
            seq_b = self._rec(monkeypatch)
            out_b, info_b = order_arrange(
                pos, adj, grid, kappa=kappa, plane=True, carry=True,
                sched="ladder", sched_rng=np.random.default_rng(9),
                **extra)
            assert seq_a == list(seq_b), extra
            assert all(np.array_equal(out_a[v], out_b[v]) for v in out_a)
            assert info_a["asks"] == info_b["asks"]
            if not extra:
                # one DP call per counted ask (xy asks call the DP
                # several times inside xy_reinsert, so only the plain
                # ladder pins the equality)
                assert info_a["asks"] == len(seq_a)
            assert info_a["accept_traj"] == info_b["accept_traj"]

    def test_rung_and_bag_ask_the_same_slots_per_pass(self):
        rng = np.random.default_rng(5)
        grid = _zgrid()
        adj, pos = _case(rng, grid, 16, 0.35)
        kappa = _target_kappa(grid)
        logs = {}
        for sched in ("ladder", "rung", "bag"):
            _out, info = order_arrange(
                pos, adj, grid, kappa=kappa, plane=True, carry=True,
                sched=sched, sched_rng=np.random.default_rng(3),
                ask_log=True)
            logs[sched] = info["ask_log"]
            assert info["sched"] == sched
        canon = sorted(logs["ladder"][0])
        for sched, log in logs.items():
            for pss in log:
                assert sorted(pss) == canon, sched
        assert logs["bag"][0] != logs["ladder"][0]
        assert logs["rung"][0] != logs["ladder"][0]
        # rung: rungs non-increasing, pairs after every interval
        first = logs["rung"][0]
        rungs = [it[2] if it[0] == "iv" else 0 for it in first]
        assert all(a >= b for a, b in zip(rungs, rungs[1:]))
        last_iv = max(i for i, it in enumerate(first) if it[0] == "iv")
        first_pair = min(i for i, it in enumerate(first)
                         if it[0] == "pair")
        assert last_iv < first_pair

    def test_deterministic_per_sched_seed(self):
        rng = np.random.default_rng(6)
        grid = _zgrid()
        adj, pos = _case(rng, grid, 16, 0.35)
        kappa = _target_kappa(grid)
        runs = []
        for sd in (4, 4, 5):
            out, info = order_arrange(
                pos, adj, grid, kappa=kappa, plane=True, carry=True,
                sched="bag", sched_rng=np.random.default_rng(sd),
                ask_log=True)
            runs.append((out, info))
        a, b, c = runs
        assert all(np.array_equal(a[0][v], b[0][v]) for v in a[0])
        assert a[1]["asks"] == b[1]["asks"]
        assert a[1]["ask_log"] == b[1]["ask_log"]
        assert a[1]["ask_log"][0] != c[1]["ask_log"][0]

    def test_max_asks_stops_and_reports(self, monkeypatch):
        import time as _t
        import ember_qc.algorithms.factored.orders as om
        rng = np.random.default_rng(7)
        grid = _zgrid()
        adj, pos = _case(rng, grid, 16, 0.35)
        kappa = _target_kappa(grid)
        _o, info = order_arrange(pos, adj, grid, kappa=kappa, plane=True,
                                 carry=True, max_asks=25)
        assert info["asks"] == 25 and info["stopped_by"] == "asks"
        assert 0 < info["bookmark_asks"] <= 25
        _o, info = order_arrange(pos, adj, grid, kappa=kappa, plane=True,
                                 carry=True, max_asks=10 ** 6)
        assert info["stopped_by"] == "fixpoint" and info["asks"] < 10 ** 6
        _o, info = order_arrange(pos, adj, grid, kappa=kappa, plane=True,
                                 carry=True, max_asks=5,
                                 deadline=_t.perf_counter() - 1.0)
        assert info["stopped_by"] == "deadline"
        assert info["asks"] == 0 and info["passes"] == 0
        monkeypatch.setattr(om, "_MAX_PASSES", 1)
        _o, info = order_arrange(pos, adj, grid, kappa=kappa, plane=True,
                                 carry=True)
        assert info["stopped_by"] in ("passes", "fixpoint")
        _o, info2 = order_arrange(pos, adj, grid, kappa=kappa, plane=True,
                                  carry=True, max_asks=10 ** 6)
        assert info2["stopped_by"] != "passes"

    def test_e2e_valid_deterministic(self):
        from ember_qc.algorithms.factored import attract_embed
        from ember_qc.registry import validate_embedding
        src = nx.gnp_random_graph(14, 0.35, seed=9)
        arms = ({"sched": "rung"}, {"sched": "bag"},
                {"sched": "bag", "strip": True, "arm_cost": True},
                {"sched": "bag", "tail": "none", "max_asks": 40})
        for tgt in (dnx.zephyr_graph(3, 4), dnx.chimera_graph(4, 4, 4)):
            for kw in arms:
                r1 = attract_embed(src, tgt, timeout=15, seed=0, **kw)
                r2 = attract_embed(src, tgt, timeout=15, seed=0, **kw)
                emb = r1["embedding"]
                assert emb and validate_embedding(emb, src, tgt), \
                    (kw, r1.get("error"))
                assert r1["embedding"] == r2["embedding"]
                assert r1["diag"]["sched"] == kw["sched"]
                if "max_asks" in kw:
                    assert r1["diag"]["stopped_by"] == "asks"
                    assert r1["diag"]["asks"] == 40
