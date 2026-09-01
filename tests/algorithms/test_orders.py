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
    def _gt(merged, adj, values, other, axis, contacts=None):
        n = len(merged)
        val = np.asarray(values, dtype=float) + 1e-4 * np.arange(n)
        if axis == 1:
            pos = {v: np.array([float(other[v]), float(val[r])])
                   for r, v in enumerate(merged)}
        else:
            pos = {v: np.array([float(val[r]), float(other[v])])
                   for r, v in enumerate(merged)}
        return stair_energy(pos, adj, contacts=contacts)

    @pytest.mark.parametrize("axis", [1, 0])
    def test_exact_and_optimal_vs_brute_force(self, axis):
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
                val = np.asarray(values, dtype=float) \
                    + 1e-4 * np.arange(n)
                pos0 = {v: np.array([float(val[r]), float(other[v])])
                        for r, v in enumerate(order)}
                contacts = _stair_contacts(pos0, adj)
            R = [v for v in order if v not in set(S)]
            e_cur = self._gt(order, adj, values, other, axis, contacts)
            brute = min(self._gt(mg, adj, values, other, axis, contacts)
                        for mg in self._merges(R, S))
            res, _flip = align_reinsert(
                order, set(S), adj, values, None,
                axis=axis, other=other, contacts=contacts)
            if res is not None:
                got = self._gt(res, adj, values, other, axis, contacts)
                assert abs(got - brute) < 1e-6, (got, brute)
                assert got < e_cur - 1e-9
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
    def _gt(ox, oy, adj, vals_x, vals_y):
        pos = {}
        rx = {v: r for r, v in enumerate(ox)}
        for r, v in enumerate(oy):
            pos[v] = np.array([float(vals_x[rx[v]]), float(vals_y[r])])
        yrank = {v: r for r, v in enumerate(oy)}
        return stair_energy(pos, adj,
                            contacts=_stair_contacts(pos, adj,
                                                     yrank=yrank))

    @staticmethod
    def _insert(order, v, k):
        R = [u for u in order if u != v]
        return R[:k] + [v] + R[k:]

    def _trial(self, rng, tie_heavy):
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
        e_cur = self._gt(ox, oy, adj, vals_x, vals_y)
        brute = min(self._gt(self._insert(ox, v, i),
                             self._insert(oy, v, j),
                             adj, vals_x, vals_y)
                    for i in range(n) for j in range(n))
        res = xy_reinsert(v, ox, oy, adj, vals_x, vals_y, contacts)
        if res is not None:
            new_ox, new_oy = res
            got = self._gt(new_ox, new_oy, adj, vals_x, vals_y)
            assert abs(got - brute) < 1e-6, (got, brute)
            assert got <= e_cur + 1e-9
            # sanity: the returned orders are permutations
            assert sorted(new_ox) == sorted(ox)
            assert sorted(new_oy) == sorted(oy)
            return 1
        assert brute >= e_cur - 1e-6, (brute, e_cur)
        return 0

    def test_exact_vs_brute_force_distinct_values(self):
        rng = np.random.default_rng(61)
        hits = 0
        for _trial in range(15):
            hits += self._trial(rng, tie_heavy=False)
        assert hits >= 5  # the property must actually be exercised

    def test_exact_vs_brute_force_tied_values(self):
        rng = np.random.default_rng(67)
        hits = 0
        for _trial in range(15):
            hits += self._trial(rng, tie_heavy=True)
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
                    val = np.asarray(values, dtype=float) \
                        + 1e-4 * np.arange(n)
                    pos0 = {u: np.array([float(val[r]),
                                         float(other[u])])
                            for r, u in enumerate(order)}
                    contacts = _stair_contacts(pos0, adj)
                C = align_reinsert(order, {v}, adj, values, None,
                                   axis=axis, other=other,
                                   contacts=contacts, slot_costs=True)
                assert C is not None and len(C) == n
                j0 = order.index(v)
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
