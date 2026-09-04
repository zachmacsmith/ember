"""
tests/algorithms/test_plane.py
==============================
The plane engine (s3.127): the judge against brute force, the packer's
invariants, the readout, the N(v) gather, the stops, determinism.
"""
import dwave_networkx as dnx
import networkx as nx
import numpy as np
import pytest

from ember_qc.algorithms.factored import plane
from ember_qc.algorithms.factored.field import (TileGrid, _stair_contacts,
                                                stair_energy)
from ember_qc.algorithms.factored.placement import target_layout


def _zgrid(m=3):
    g = dnx.zephyr_graph(m, 4)
    return TileGrid(g, target_layout(g), courses=True)


def _cgrid():
    g = dnx.chimera_graph(4, 4, 4)
    return TileGrid(g, target_layout(g))


def _state(rng, grid, n, p=0.4, ymax=None):
    g = nx.gnp_random_graph(n, p, seed=int(rng.integers(9999)))
    adj = {v: sorted(g.neighbors(v)) for v in g.nodes()}
    H = ymax if ymax is not None else grid.H
    pos = {v: np.array([float(rng.integers(1, grid.W - 1)),
                        float(rng.integers(0, H))]) for v in g.nodes()}
    oy = sorted(pos, key=lambda v: (pos[v][1], v))
    return adj, pos, oy


class TestJudge:
    def test_stair_is_stair_energy_with_bar(self):
        rng = np.random.default_rng(1)
        grid = _zgrid()
        for _ in range(10):
            adj, pos, oy = _state(rng, grid, 12)
            bk = plane.books(pos, adj, grid, plane.rank_of(oy), snap=True)
            pen, stair = plane.judge(bk, pos, adj, grid, bar=2.0)
            want = stair_energy(pos, adj, bar=2.0,
                                contacts=_stair_contacts(
                                    pos, adj, yrank=plane.rank_of(oy)))
            assert stair == pytest.approx(want)

    def test_pen_vs_brute_force_including_off_chip(self):
        rng = np.random.default_rng(2)
        grid = _zgrid()
        s = plane.stride(grid)
        ph, pv = plane.profiles(grid)
        for trial in range(20):
            adj, pos, oy = _state(rng, grid, int(rng.integers(4, 14)),
                                  ymax=2 * grid.H)
            bk = plane.books(pos, adj, grid, plane.rank_of(oy), snap=False)
            pen, _ = plane.judge(bk, pos, adj, grid, bar=0.0)
            want = 0.0
            for o, table in ((1, ph), (0, pv)):
                nl, nb = table.shape
                real_last = int(np.max(np.nonzero(table.max(axis=0) > 0)[0])) + 1
                cover = {}
                for (line, a, b, v) in bk[2][o]:
                    ln = int(line)
                    lo = max(0, int(np.floor(a / s)))
                    hi = int(np.floor(b / s)) + 1
                    if ln < nl:
                        hi = min(hi, real_last)
                    for q in range(lo, hi):
                        cover[(ln, q)] = cover.get((ln, q), 0) + 1
                for (ln, q), c in cover.items():
                    pool = table[ln, q] if (ln < nl and q < nb) else 0.0
                    want += max(c - pool, 0.0) ** 2
            assert pen == int(round(want)), (trial, pen, want)

    def test_boundary_lines_zero_only_on_courses(self):
        ph, pv = plane.profiles(_zgrid())
        assert ph[0].sum() == 0 and ph[-1].sum() == 0
        assert pv[0].sum() == 0 and pv[-1].sum() == 0
        assert ph[1].max() == 8
        ch, cv = plane.profiles(_cgrid())
        assert ch[0].sum() > 0 and cv[-1].sum() > 0


class TestPacker:
    def test_pack_axis_zero_own_overload_and_order_kept(self):
        rng = np.random.default_rng(3)
        grid = _zgrid(4)
        for _ in range(10):
            adj, pos, oy = _state(rng, grid, int(rng.integers(6, 20)))
            ox = sorted(pos, key=lambda v: (pos[v][0], v))
            orders = {0: ox, 1: oy}
            for ax in (1, 0):
                new, bk, miss = plane.readout(ax, orders, pos, adj, grid,
                                              snap=True)
                lines = [new[v][ax] for v in orders[ax]]
                assert lines == sorted(lines)          # monotone in order
                assert all(float(x).is_integer() for x in lines)
                if ax == 0:
                    assert 0 <= min(lines) and max(lines) <= grid.W - 1
                if miss == 0:
                    # the packed axis carries no overload on the chip
                    pen, _ = plane.judge(bk, new, adj, grid, bar=0.0)
                    ph, pv = plane.profiles(grid)
                    table = ph if ax == 1 else pv
                    nl = table.shape[0]
                    over = 0.0
                    s = plane.stride(grid)
                    real_last = int(np.max(np.nonzero(
                        table.max(axis=0) > 0)[0])) + 1
                    cov = {}
                    for (line, a, b, v) in bk[2][ax]:
                        ln = int(line)
                        if ln >= nl:
                            continue
                        lo = max(0, int(np.floor(a / s)))
                        hi = min(int(np.floor(b / s)) + 1, real_last)
                        for q in range(lo, hi):
                            cov[(ln, q)] = cov.get((ln, q), 0) + 1
                    for (ln, q), c in cov.items():
                        over += max(c - table[ln, q], 0.0)
                    assert over == 0.0
                pos = new

    def test_readout_deterministic(self):
        rng = np.random.default_rng(4)
        grid = _zgrid()
        adj, pos, oy = _state(rng, grid, 12)
        ox = sorted(pos, key=lambda v: (pos[v][0], v))
        a = plane.readout(1, {0: ox, 1: oy}, pos, adj, grid, snap=True)
        b = plane.readout(1, {0: ox, 1: oy}, pos, adj, grid, snap=True)
        assert all(np.array_equal(a[0][v], b[0][v]) for v in a[0])
        assert a[2] == b[2]


class TestArrange:
    def test_trivial_and_untyped_noop(self):
        adj = {0: [1], 1: [0]}
        pos, bk, info = plane.arrange(adj, _zgrid(), seed=0)
        assert info["stopped_by"] == "trivial" and len(pos) == 2
        g = nx.grid_2d_graph(6, 6)
        grid = TileGrid(g, {v: np.array(v, dtype=float) for v in g})
        adj = {v: [u for u in range(5) if u != v] for v in range(5)}
        pos, bk, info = plane.arrange(adj, grid, seed=0)
        assert info["stopped_by"] == "trivial"

    def test_bookmark_equals_judge_and_stops(self):
        rng = np.random.default_rng(5)
        grid = _zgrid(4)
        g = nx.gnp_random_graph(24, 0.2, seed=7)
        adj = {v: sorted(g.neighbors(v)) for v in g.nodes()}
        pos, bk, info = plane.arrange(adj, grid, seed=0, max_asks=10 ** 6,
                                      snap=True)
        assert info["stopped_by"] == "fixpoint"
        pen, stair = plane.judge(bk, pos, adj, grid,
                                 bar=float(plane.stride(grid)))
        assert (pen, stair) == (info["pen"], info["stair"])
        pos2, _, info2 = plane.arrange(adj, grid, seed=0, max_asks=30,
                                       snap=True)
        assert info2["stopped_by"] == "asks" and info2["asks"] == 30
        assert 0 <= info2["bookmark_asks"] <= 30
        pos3, _, info3 = plane.arrange(adj, grid, seed=0, max_asks=30,
                                       snap=True)
        assert all(np.array_equal(pos2[v], pos3[v]) for v in pos2)

    def test_biclique_gather_is_one_move(self):
        # K_{8,8} from an interleaved y-order: the N(v) unit re-weaves
        # the other block as ONE contiguous run — the bipartition in a
        # single accepted ask — and the crystal's every variable is
        # one-sided (bars == n)
        from ember_qc.algorithms.factored.field import align_reinsert
        g = nx.complete_bipartite_graph(8, 8)
        adj = {v: sorted(g.neighbors(v)) for v in g.nodes()}
        oy = [0, 8, 1, 9, 2, 10, 3, 11, 4, 12, 5, 13, 6, 14, 7, 15]
        vals = [float(i // 2) for i in range(16)]
        other = {v: float(v % 8) for v in range(16)}
        new, _flip = align_reinsert(oy, set(adj[0]), adj, vals, None,
                                    axis=1, other=other, contacts=None,
                                    bar=2.0)
        assert new is not None
        blocks = [v // 8 for v in new]
        runs = 1 + sum(1 for a, b in zip(blocks, blocks[1:]) if a != b)
        assert runs == 2
        grid = _zgrid(4)
        pos, bk, info = plane.arrange(adj, grid, seed=0, max_asks=2000,
                                      snap=True)
        assert info["bars"] == 16 and info["pen"] == 0
