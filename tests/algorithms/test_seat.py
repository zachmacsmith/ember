"""
tests/algorithms/test_seat.py
==============================
The seat engine (s3.102): reference-evaluator oracles for both moves,
the translation contact-flip case (Max's catch), internal invariance,
strict descent, determinism, and the e2e knob.
"""
import dwave_networkx as dnx
import networkx as nx
import numpy as np
import pytest

from ember_qc.algorithms.factored.field import TileGrid, _stair_contacts
from ember_qc.algorithms.factored.placement import target_layout
from ember_qc.algorithms.factored.seat import (
    best_seat,
    best_translate,
    seat_arrange,
    seat_energy,
)


def _grid():
    g = dnx.chimera_graph(4, 4, 4)
    return TileGrid(g, target_layout(g))


def _case(rng, grid, n, p_edge=0.4):
    g = nx.gnp_random_graph(n, p_edge, seed=int(rng.integers(9999)))
    adj = {v: sorted(g.neighbors(v)) for v in g.nodes()}
    pos = {v: np.array([float(rng.integers(0, grid.W)),
                        float(rng.integers(0, grid.H))])
           for v in g.nodes()}
    return adj, pos


class TestSeatOracles:
    def test_best_seat_matches_bruteforce(self):
        grid = _grid()
        rng = np.random.default_rng(7)
        for _trial in range(10):
            adj, pos = _case(rng, grid, int(rng.integers(5, 10)))
            e_cur = seat_energy(pos, adj, grid, lam=1.0)
            v = sorted(pos)[int(rng.integers(len(pos)))]
            # brute force: every seat, reference-scored
            brute = e_cur
            for r in range(grid.H):
                for c in range(grid.W):
                    cand = {u: p.copy() for u, p in pos.items()}
                    cand[v] = np.array([float(c), float(r)])
                    brute = min(brute,
                                seat_energy(cand, adj, grid, lam=1.0))
            info = {"fast_miss": 0}
            res = best_seat(v, pos, adj, grid, lam=1.0,
                            e_cur=e_cur, info=info)
            if res is not None:
                _, e_new = res
                assert e_new < e_cur - 1e-9
                assert abs(e_new - brute) < 1e-6, (e_new, brute)
            else:
                assert brute >= e_cur - 1e-6

    def test_best_translate_matches_bruteforce(self):
        grid = _grid()
        rng = np.random.default_rng(11)
        for _trial in range(8):
            adj, pos = _case(rng, grid, 8)
            e_cur = seat_energy(pos, adj, grid, lam=1.0)
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
                    brute = min(brute,
                                seat_energy(cand, adj, grid, lam=1.0))
            info = {"fast_miss": 0}
            res = best_translate(unit, pos, adj, grid, lam=1.0,
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
        e_cur = seat_energy(pos, adj, grid, lam=1.0)
        cols = [int(pos[w][0]) for w in unit]
        rows = [int(pos[w][1]) for w in unit]
        brute, barg = e_cur, None
        for dr in range(-min(rows), grid.H - max(rows)):
            for dc in range(-min(cols), grid.W - max(cols)):
                if dr == 0 and dc == 0:
                    continue
                cand = {u: p.copy() for u, p in pos.items()}
                for w in unit:
                    cand[w] = pos[w] + np.array([float(dc), float(dr)])
                e2 = seat_energy(cand, adj, grid, lam=1.0)
                if e2 < brute:
                    brute, barg = e2, (dr, dc)
        info = {"fast_miss": 0}
        res = best_translate(unit, pos, adj, grid, lam=1.0,
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
    def test_swap_matches_reference_all_modes(self):
        # every variant of _swap_exact must equal the reference
        # evaluator on the swapped state — including y-swaps, which
        # flip contacts (the case monotonize cannot express)
        from ember_qc.algorithms.factored.seat import (_Live,
                                                       _swap_exact)
        grid = _grid()
        rng = np.random.default_rng(17)
        for _trial in range(12):
            adj, pos = _case(rng, grid, int(rng.integers(5, 10)))
            live = _Live({v: p.copy() for v, p in pos.items()},
                         adj, grid, 1.0)
            edges = sorted((v, u) for v in pos
                           for u in adj.get(v, []) if u in pos and u > v)
            for (v, u) in edges[:6]:
                for mode in ("x", "y", "b"):
                    got = _swap_exact(live, v, u, mode)
                    cand = {t: p.copy() for t, p in pos.items()}
                    if mode in ("x", "b"):
                        cand[v][0], cand[u][0] = cand[u][0], cand[v][0]
                    if mode in ("y", "b"):
                        cand[v][1], cand[u][1] = cand[u][1], cand[v][1]
                    ref = seat_energy(cand, adj, grid, lam=1.0)
                    if got is not None:
                        assert abs(got - ref) < 1e-6, (mode, got, ref)


class TestGather:
    def test_gather_matches_bruteforce_candidates(self):
        # the accepted candidate equals the brute-force best of the
        # explicit candidate family under the reference evaluator
        from ember_qc.algorithms.factored.seat import best_gather
        grid = _grid()
        rng = np.random.default_rng(29)
        for _trial in range(8):
            adj, pos = _case(rng, grid, 9)
            unit = sorted(pos)[:4]
            e_cur = seat_energy(pos, adj, grid, lam=1.0)
            # brute-force the same family: both axes x {mean,0,end} x
            # {fwd, rev}
            brute = e_cur
            Uset = set(unit)
            for axis in (1, 0):
                order = sorted(pos,
                               key=lambda v: (float(pos[v][axis]), v))
                vals = sorted(float(pos[v][axis]) for v in order)
                rest = [v for v in order if v not in Uset]
                useq = [v for v in order if v in Uset]
                mean_c = (sum(float(pos[v][axis]) for v in useq)
                          / len(useq))
                mean_k = sum(1 for v in rest
                             if (float(pos[v][axis]), v)
                             < (mean_c, useq[0]))
                for k in (mean_k, 0, len(rest)):
                    for block in (useq, useq[::-1]):
                        co = rest[:k] + block + rest[k:]
                        cand = {v: p.copy() for v, p in pos.items()}
                        for r, v in enumerate(co):
                            cand[v][axis] = float(vals[r])
                        brute = min(brute, seat_energy(cand, adj, grid,
                                                       lam=1.0))
            info = {"gather_accepts": 0}
            res = best_gather(unit, pos, adj, grid, lam=1.0,
                              e_cur=e_cur, info=info)
            if res is not None:
                assert abs(res[1] - brute) < 1e-6
                assert res[1] < e_cur - 1e-9
            else:
                assert brute >= e_cur - 1e-6


class TestSeatArrange:
    def test_descends_and_deterministic(self):
        grid = _grid()
        rng = np.random.default_rng(3)
        adj, pos = _case(rng, grid, 12)
        units = [[[0, 1, 2, 3], [4, 5, 6, 7]]]
        e0 = seat_energy(pos, adj, grid, lam=1.0)
        out, info = seat_arrange(
            {v: p.copy() for v, p in pos.items()}, adj, grid, units,
            lam=1.0)
        assert info["seat_E"] <= e0 + 1e-6
        assert abs(seat_energy(out, adj, grid, lam=1.0)
                   - info["seat_E"]) < 0.06  # rounded diag
        again, info2 = seat_arrange(
            {v: p.copy() for v, p in pos.items()}, adj, grid, units,
            lam=1.0)
        assert all(np.array_equal(out[v], again[v]) for v in pos)
        assert info["seat_accepts"] == info2["seat_accepts"]

    def test_untyped_grid_noops(self):
        g = nx.convert_node_labels_to_integers(nx.grid_2d_graph(6, 6))
        grid = TileGrid(g, nx.spectral_layout(g), fallback_bins=4)
        adj = {0: [1], 1: [0]}
        pos = {0: np.array([0.0, 0.0]), 1: np.array([1.0, 1.0])}
        out, info = seat_arrange(pos, adj, grid, None, lam=1.0)
        assert info["passes"] == 0
        assert all(np.array_equal(out[v], pos[v]) for v in pos)


class TestSeatKnob:
    def test_knob_known_field_default_orders(self):
        from dataclasses import fields
        from ember_qc.algorithms.factored.placement import AttractConfig
        assert "arrange_mode" in {f.name for f in fields(AttractConfig)}
        assert AttractConfig().arrange_mode == "orders"

    def test_seats_mode_valid_deterministic(self):
        from ember_qc.algorithms.factored import attract_embed
        from ember_qc.registry import validate_embedding
        src = nx.gnp_random_graph(12, 0.4, seed=7)
        for target in (dnx.chimera_graph(4, 4, 4),
                       dnx.zephyr_graph(3, 4)):
            a = attract_embed(src, target, timeout=60, seed=0,
                              arrange_mode="seats")
            b = attract_embed(src, target, timeout=60, seed=0,
                              arrange_mode="seats")
            assert a["embedding"]
            assert validate_embedding(a["embedding"], src, target)
            assert a["embedding"] == b["embedding"]
            assert "seat_accepts" in a["diag"]
            assert "accept_traj" in a["diag"]
