"""
tests/algorithms/test_seat.py
==============================
The lex engine (s3.110-112, the single arrange engine since
consolidation 7): reference-evaluator oracles for every move, the
lexicographic hand-pins, the interleave jump's exactness and
soundness, strict descent, determinism, the feasibility invariant,
and the e2e pipeline on both fabrics.
"""
import dwave_networkx as dnx
import networkx as nx
import numpy as np
import pytest

from ember_qc.algorithms.factored.field import TileGrid, _stair_contacts
from ember_qc.algorithms.factored.placement import target_layout
from ember_qc.algorithms.factored.seat import (
    _LEX_M,
    best_interleave,
    best_seat,
    best_translate,
    seat_arrange,
    seat_energy,
)


def _grid():
    g = dnx.chimera_graph(4, 4, 4)
    return TileGrid(g, target_layout(g))


def _zgrid():
    # course-resolved Zephyr: stride 2, the brick quantum is real
    g = dnx.zephyr_graph(3, 4)
    return TileGrid(g, target_layout(g), courses=True)


# the one engine runs on both: chimera exercises stride 1 (junction ==
# brick), zephyr exercises the real brick quantum
ORACLE_GRIDS = [_grid, _zgrid]


def _case(rng, grid, n, p_edge=0.4):
    g = nx.gnp_random_graph(n, p_edge, seed=int(rng.integers(9999)))
    adj = {v: sorted(g.neighbors(v)) for v in g.nodes()}
    pos = {v: np.array([float(rng.integers(0, grid.W)),
                        float(rng.integers(0, grid.H))])
           for v in g.nodes()}
    return adj, pos


class TestEvaluator:
    def test_hand_pinned_case(self):
        # zephyr(3,4) courses: stride 2, junctions 0..6, bricks 0..3
        # (brick 3 = the over-allocated boundary junction, pool 0).
        # Edge (0, 1): 1 is y-lower so 1 spends the h-arm (junction
        # stair 5) and 0 spends the v-arm (stair 3); brick cover is
        # clean, so E = the plain junction stair 8.
        grid = _zgrid()
        assert grid.stride == 2
        adj = {0: [1], 1: [0]}
        pos = {0: np.array([0.0, 3.0]), 1: np.array([5.0, 0.0])}
        assert seat_energy(pos, adj, grid) == pytest.approx(8.0)

    def test_lexicographic_order(self):
        # capacity leads: a brick-feasible state with LARGER stair
        # must score below an overloaded state with smaller stair
        grid = _zgrid()
        adj = {0: [1], 1: [0]}
        feas = {0: np.array([0.0, 3.0]), 1: np.array([5.0, 0.0])}
        over = {0: np.array([6.0, 3.0]), 1: np.array([6.0, 0.0])}
        e_feas = seat_energy(feas, adj, grid)
        e_over = seat_energy(over, adj, grid)
        assert e_feas == pytest.approx(8.0)
        assert e_over == pytest.approx(_LEX_M + 3.0)
        assert e_feas < e_over   # despite stair 8 > 3

    def test_same_brick_partners_cost_the_same(self):
        # one bar reaches both lines of its brick: reaching column 4
        # and column 5 from the same side costs the same capacity (the
        # s3.107 whole-brick booking; stair still distinguishes them
        # at junction resolution)
        grid = _zgrid()
        adj = {0: [1], 1: [0]}
        p4 = {0: np.array([4.0, 3.0]), 1: np.array([0.0, 0.0])}
        p5 = {0: np.array([5.0, 3.0]), 1: np.array([0.0, 0.0])}
        b4 = seat_energy(p4, adj, grid)
        b5 = seat_energy(p5, adj, grid)
        # both clean: difference is exactly the one-junction stair
        assert abs(b5 - b4) == pytest.approx(1.0)


class TestSeatOracles:
    @pytest.mark.parametrize("mk", ORACLE_GRIDS)
    def test_best_seat_matches_bruteforce(self, mk):
        grid = mk()
        rng = np.random.default_rng(7)
        for _trial in range(10):
            adj, pos = _case(rng, grid, int(rng.integers(5, 10)))
            e_cur = seat_energy(pos, adj, grid)
            v = sorted(pos)[int(rng.integers(len(pos)))]
            # brute force: every seat, reference-scored
            brute = e_cur
            for r in range(grid.H):
                for c in range(grid.W):
                    cand = {u: p.copy() for u, p in pos.items()}
                    cand[v] = np.array([float(c), float(r)])
                    brute = min(brute, seat_energy(cand, adj, grid))
            info = {"fast_miss": 0}
            res = best_seat(v, pos, adj, grid, e_cur=e_cur, info=info)
            if res is not None:
                _, e_new = res
                assert e_new < e_cur - 1e-9
                assert abs(e_new - brute) < 1e-6, (e_new, brute)
            else:
                assert brute >= e_cur - 1e-6

    @pytest.mark.parametrize("mk", ORACLE_GRIDS)
    def test_best_translate_matches_bruteforce(self, mk):
        grid = mk()
        rng = np.random.default_rng(11)
        for _trial in range(8):
            adj, pos = _case(rng, grid, 8)
            e_cur = seat_energy(pos, adj, grid)
            unit = sorted(pos)[:3]
            brute = e_cur
            cols = [int(pos[w][0]) for w in unit]
            rows = [int(pos[w][1]) for w in unit]
            for dr in range(-min(rows), grid.H - max(rows)):
                for dc in range(-min(cols), grid.W - max(cols)):
                    if dr == 0 and dc == 0:
                        continue
                    cand = {u: p.copy() for u, p in pos.items()}
                    for w in unit:
                        cand[w] = pos[w] + np.array([float(dc),
                                                     float(dr)])
                    brute = min(brute, seat_energy(cand, adj, grid))
            info = {"fast_miss": 0}
            res = best_translate(unit, pos, adj, grid,
                                 e_cur=e_cur, info=info)
            if res is not None:
                _, e_new = res
                assert e_new < e_cur - 1e-9
                assert abs(e_new - brute) < 1e-6, (e_new, brute)
            else:
                assert brute >= e_cur - 1e-6

    def test_translation_contact_flip_case(self):
        # Max's catch: shifting a unit across an external neighbour's
        # row flips who-is-below on the boundary edge — the evaluator's
        # chosen offset must still agree with the reference brute force
        grid = _grid()
        adj = {0: [1], 1: [0, 2], 2: [1, 3], 3: [2]}
        pos = {0: np.array([0.0, 0.0]), 1: np.array([1.0, 1.0]),
               2: np.array([2.0, 2.0]), 3: np.array([3.0, 3.0])}
        unit = [0, 1]   # boundary edge (1, 2) flips when unit crosses
        e_cur = seat_energy(pos, adj, grid)
        cols = [int(pos[w][0]) for w in unit]
        rows = [int(pos[w][1]) for w in unit]
        brute = e_cur
        for dr in range(-min(rows), grid.H - max(rows)):
            for dc in range(-min(cols), grid.W - max(cols)):
                if dr == 0 and dc == 0:
                    continue
                cand = {u: p.copy() for u, p in pos.items()}
                for w in unit:
                    cand[w] = pos[w] + np.array([float(dc), float(dr)])
                brute = min(brute, seat_energy(cand, adj, grid))
        info = {"fast_miss": 0}
        res = best_translate(unit, pos, adj, grid,
                             e_cur=e_cur, info=info)
        if res is not None:
            assert abs(res[1] - brute) < 1e-6
        else:
            assert brute >= e_cur - 1e-6

    def test_internal_edges_invariant_under_translation(self):
        # internal spans identical before/after a rigid shift
        grid = _grid()
        adj = {0: [1, 2], 1: [0, 2], 2: [0, 1]}
        pos = {0: np.array([0.0, 0.0]), 1: np.array([1.0, 1.0]),
               2: np.array([0.0, 2.0])}
        c0 = _stair_contacts(pos, adj)
        shifted = {v: p + np.array([1.0, 1.0]) for v, p in pos.items()}
        c1 = _stair_contacts(shifted, adj)
        for v in pos:
            assert c0[v] == c1[v]


class TestSwapExact:
    @pytest.mark.parametrize("mk", ORACLE_GRIDS)
    def test_swap_matches_reference_all_modes(self, mk):
        # every variant of _swap_exact must equal the reference
        # evaluator on the swapped state — including y-swaps, which
        # flip contacts
        from ember_qc.algorithms.factored.seat import (_Live,
                                                       _swap_exact)
        grid = mk()
        rng = np.random.default_rng(17)
        for _trial in range(12):
            adj, pos = _case(rng, grid, int(rng.integers(5, 10)))
            live = _Live({v: p.copy() for v, p in pos.items()},
                         adj, grid)
            edges = sorted((v, u) for v in pos
                           for u in adj.get(v, []) if u in pos and u > v)
            for (v, u) in edges[:6]:
                for smode in ("x", "y", "b"):
                    got = _swap_exact(live, v, u, smode)
                    cand = {t: p.copy() for t, p in pos.items()}
                    if smode in ("x", "b"):
                        cand[v][0], cand[u][0] = cand[u][0], cand[v][0]
                    if smode in ("y", "b"):
                        cand[v][1], cand[u][1] = cand[u][1], cand[v][1]
                    ref = seat_energy(cand, adj, grid)
                    if got is not None:
                        assert abs(got - ref) < 1e-6, (smode, got, ref)


class TestInterleave:
    def _brute(self, pos, adj, grid, unit):
        # brute force over ALL rank-interleavings x {fwd, rev} x axes,
        # reference-judged — the DP's full candidate family
        from itertools import combinations
        Uset = set(unit)
        best = seat_energy(pos, adj, grid)
        for axis in (1, 0):
            order = sorted(pos, key=lambda v: (float(pos[v][axis]), v))
            vals = sorted(float(pos[v][axis]) for v in order)
            rest = [v for v in order if v not in Uset]
            useq = [v for v in order if v in Uset]
            n = len(order)
            for block in (useq, useq[::-1]):
                for ranks in combinations(range(n), len(block)):
                    co = []
                    bi = ri = 0
                    rk = set(ranks)
                    for k in range(n):
                        if k in rk:
                            co.append(block[bi])
                            bi += 1
                        else:
                            co.append(rest[ri])
                            ri += 1
                    cand = {v: p.copy() for v, p in pos.items()}
                    for r, v in enumerate(co):
                        cand[v][axis] = float(vals[r])
                    best = min(best, seat_energy(cand, adj, grid))
        return best

    def test_exact_optimum_when_capacity_slack(self):
        # tiny graphs on the chimera fixture: no overload is
        # reachable, so the DP's stair-exact interior IS the whole
        # objective and the move must land on the brute-force optimum
        grid = _grid()
        rng = np.random.default_rng(41)
        for _trial in range(6):
            adj, pos = _case(rng, grid, 7, p_edge=0.5)
            unit = sorted(pos)[:3]
            e_cur = seat_energy(pos, adj, grid)
            brute = self._brute(pos, adj, grid, unit)
            info = {"interleave_accepts": 0, "interleave_declines": 0,
                    "interleave_noops": 0}
            res = best_interleave(unit, pos, adj, grid,
                                  e_cur=e_cur, info=info)
            if res is not None:
                assert res[1] < e_cur - 1e-9
                assert abs(res[1] - brute) < 1e-6, (res[1], brute)
            else:
                assert brute >= e_cur - 1e-4

    @pytest.mark.parametrize("mk", ORACLE_GRIDS)
    def test_soundness(self, mk):
        # any accepted result strictly improves the TRUE objective;
        # deterministic; a decline leaves pos untouched
        grid = mk()
        rng = np.random.default_rng(43)
        for _trial in range(8):
            adj, pos = _case(rng, grid, 10)
            unit = sorted(pos)[:4]
            e_cur = seat_energy(pos, adj, grid)
            snap0 = {v: p.copy() for v, p in pos.items()}
            info = {"interleave_accepts": 0, "interleave_declines": 0,
                    "interleave_noops": 0}
            res = best_interleave(unit, pos, adj, grid,
                                  e_cur=e_cur, info=info)
            assert all(np.array_equal(pos[v], snap0[v]) for v in pos)
            if res is not None:
                cand, e_new = res
                assert e_new < e_cur - 1e-9
                assert abs(seat_energy(cand, adj, grid)
                           - e_new) < 1e-6
                res2 = best_interleave(unit, pos, adj, grid,
                                       e_cur=e_cur, info=info)
                assert res2 is not None
                assert all(np.array_equal(res[0][v], res2[0][v])
                           for v in pos)


class TestSeatArrange:
    def test_descends_deterministic_invariant(self):
        from ember_qc.algorithms.factored.seat import _Live
        grid = _zgrid()
        rng = np.random.default_rng(5)
        adj, pos = _case(rng, grid, 12)
        units = [[[0, 1, 2, 3], [4, 5, 6, 7]]]
        pen_in = _Live({v: p.copy() for v, p in pos.items()},
                       adj, grid).pen
        e0 = seat_energy(pos, adj, grid)
        out, info = seat_arrange(
            {v: p.copy() for v, p in pos.items()}, adj, grid, units)
        assert info["seat_E"] <= e0 + 1e-6
        assert abs(seat_energy(out, adj, grid)
                   - info["seat_E"]) < 0.06
        assert info["fast_miss"] < 1000, "live books drifted from " \
                                         "the reference"
        # capacity is the leading key: pen never rises, and this case
        # is comfortably feasible so the search must reach pen 0
        assert info["seat_pen"] <= pen_in + 1e-9
        assert info["seat_pen"] == pytest.approx(0.0)
        again, info2 = seat_arrange(
            {v: p.copy() for v, p in pos.items()}, adj, grid, units)
        assert all(np.array_equal(out[v], again[v]) for v in pos)
        assert info["seat_accepts"] == info2["seat_accepts"]

    def test_untyped_grid_noops(self):
        g = nx.convert_node_labels_to_integers(nx.grid_2d_graph(6, 6))
        grid = TileGrid(g, nx.spectral_layout(g), fallback_bins=4)
        adj = {0: [1], 1: [0]}
        pos = {0: np.array([0.0, 0.0]), 1: np.array([1.0, 1.0])}
        out, info = seat_arrange(pos, adj, grid, None)
        assert info["passes"] == 0
        assert all(np.array_equal(out[v], pos[v]) for v in pos)


class TestPipeline:
    def test_config_is_fifteen_knobs(self):
        from dataclasses import fields
        from ember_qc.algorithms.factored.placement import AttractConfig
        names = {f.name for f in fields(AttractConfig)}
        assert names == {"round_frac", "kappa", "span_floor",
                         "exact_seeds", "snap_claims", "vcycle",
                         "vcycle_agg", "cluster_moves",
                         "cluster_units", "init_mode", "tail",
                         "ball_singles", "engine", "hier_units",
                         "carry_orders"}

    def test_e2e_valid_deterministic_both_fabrics(self):
        from ember_qc.algorithms.factored import attract_embed
        from ember_qc.registry import validate_embedding
        src = nx.gnp_random_graph(12, 0.4, seed=7)
        for target in (dnx.zephyr_graph(3, 4),
                       dnx.chimera_graph(4, 4, 4)):
            a = attract_embed(src, target, timeout=60, seed=0)
            b = attract_embed(src, target, timeout=60, seed=0)
            assert a["embedding"]
            assert validate_embedding(a["embedding"], src, target)
            assert a["embedding"] == b["embedding"]
            assert "interleave_accepts" in a["diag"]
            assert "accept_traj" in a["diag"]
