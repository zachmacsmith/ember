"""
tests/algorithms/test_field.py
================================
Tests for the coarse layer (ember_qc.algorithms.factored.field),
post-consolidation: typed tile capacities, the stair (single-coverage)
readout and its subgradient dynamics, the alternating 1-D arrangement with
insertion order-search, wire-coherent seed derivation (greedy coloring and
per-line matching), and the parked ``bar_domains`` handoff.
"""
import networkx as nx
import numpy as np
import pytest
import dwave_networkx as dnx

from ember_qc.algorithms.factored.field import (
    TileGrid,
    _couples,
    _line_tracks,
    _stair_contacts,
    alternate_arrange,
    bar_domains,
    bar_widths,
    derive_bars_stair,
    insertion_sweeps,
    line_depth,
    stair_energy,
    stair_step,
    wire_seeds_iv,
    wire_seeds_matched,
)
from ember_qc.algorithms.factored.placement import target_layout


def make_grid(target):
    return TileGrid(target, target_layout(target))


class TestTileGrid:
    def test_chimera_typed_capacities(self):
        g = dnx.chimera_graph(4, 4, 4)
        grid = make_grid(g)
        assert grid.typed
        assert grid.H == 4 and grid.W == 4
        assert grid.cap.sum() == g.number_of_nodes()
        # every clean chimera tile: 4 vertical + 4 horizontal qubits
        assert np.all(grid.cap == 4.0)

    def test_pegasus_capacities_sum(self):
        g = dnx.pegasus_graph(4)
        grid = make_grid(g)
        assert grid.typed
        assert grid.cap.sum() == g.number_of_nodes()

    def test_dead_qubits_reduce_right_pool(self):
        g = dnx.chimera_graph(4, 4, 4)
        # kill one vertical (u=0) qubit in tile (0,0): linear index 0
        g.remove_node(0)
        grid = make_grid(g)
        assert grid.cap[0, 0, 0] == 3.0
        assert grid.cap[0, 0, 1] == 4.0

    def test_fallback_untyped(self):
        g = nx.grid_2d_graph(10, 10)
        g = nx.convert_node_labels_to_integers(g)
        grid = TileGrid(g, nx.spectral_layout(g), fallback_bins=4)
        assert not grid.typed
        assert grid.cap.sum() == pytest.approx(g.number_of_nodes())

    def test_affine_roundtrip(self):
        g = dnx.chimera_graph(4, 4, 4)
        grid = make_grid(g)
        d_tile = np.array([1.0, -0.5])
        d_draw = grid.to_drawing_delta(d_tile)
        assert np.allclose(grid.M @ d_draw, d_tile)


class TestStaircase:
    """Single-coverage diagonal-rule readout (notes s3.34)."""

    def _k(self, n):
        return {v: [u for u in range(n) if u != v] for v in range(n)}

    def test_diagonal_clique_is_the_staircase(self):
        # K5 on the diagonal: arm lengths follow row + column = constant
        pos = {v: np.array([float(v), float(v)]) for v in range(5)}
        bars = derive_bars_stair(pos, self._k(5), floor=False)
        for v in range(5):
            h_iv, v_iv = bars[v]
            assert h_iv[1] - h_iv[0] == pytest.approx(4.0 - v)  # right-reach
            assert v_iv[1] - v_iv[0] == pytest.approx(float(v))  # up-reach
        # ends of the staircase: all-row and all-column
        assert bars[0][1][1] - bars[0][1][0] == pytest.approx(0.0)
        assert bars[4][0][1] - bars[4][0][0] == pytest.approx(0.0)

    def test_single_coverage_and_no_mirror(self):
        pos = {v: np.array([float(v), float(v)]) for v in range(5)}
        adj = self._k(5)
        bars = derive_bars_stair(pos, adj, floor=False)
        for u in range(5):
            for v in range(u + 1, 5):
                # designated crossing (x_v, y_u): u's h-arm covers col v,
                # v's v-arm covers row u
                assert bars[u][0][0] - 1e-9 <= v <= bars[u][0][1] + 1e-9
                assert bars[v][1][0] - 1e-9 <= u <= bars[v][1][1] + 1e-9
                # mirror crossing (x_u, y_v) is NOT required: u's v-arm
                # does not reach row v
                assert not (bars[u][1][0] <= v <= bars[u][1][1])

    def test_diagonal_clique_energy_closed_form(self):
        # each edge is paid at exactly one crossing: total arm length on the
        # diagonal K_n is n*(n-1) — half of the double-coverage readout's
        # 2*n*(n-1) (the s3.34 2x-overpay fix)
        n = 8
        pos = {v: np.array([float(v), float(v)]) for v in range(n)}
        assert stair_energy(pos, self._k(n)) == pytest.approx(n * (n - 1))

    def test_sparse_arms_are_minimal(self):
        # path along x at constant y (ties broken by id): interior v owes an
        # h-arm of length 1 (reaching v+1's column) and a zero v-arm — arms
        # span assigned contacts only, not the whole neighbourhood
        pos = {v: np.array([float(v), 3.0]) for v in range(6)}
        adj = {v: [u for u in (v - 1, v + 1) if 0 <= u < 6] for v in range(6)}
        bars = derive_bars_stair(pos, adj, floor=False)
        for v in range(1, 5):
            h_iv, v_iv = bars[v]
            assert h_iv[1] - h_iv[0] == pytest.approx(1.0)
            assert v_iv[1] - v_iv[0] == pytest.approx(0.0)

    def test_kappa_floor(self):
        # coincident star: raw spans are 0; the contact-capacity floor forces
        # the hub's total arm length to deg/kappa - 1, leaves stay points
        pos = {v: np.array([5.0, 5.0]) for v in range(27)}
        adj = {0: list(range(1, 27))}
        adj.update({v: [0] for v in range(1, 27)})
        bars = derive_bars_stair(pos, adj, kappa=13.0, floor=True)
        w, h = bar_widths(bars)[0]
        assert w + h == pytest.approx(26 / 13.0 - 1.0)
        lw, lh = bar_widths(bars)[1]
        assert lw + lh == pytest.approx(0.0)

    def test_stair_step_moves_extremes_and_descends(self):
        pos = {0: np.array([0.0, 0.0]), 1: np.array([2.0, 0.0]),
               2: np.array([4.0, 0.0])}
        adj = {0: [1], 1: [0, 2], 2: [1]}
        e0 = stair_energy(pos, adj)
        new = stair_step(pos, adj, eta=0.5)
        assert new[0][0] > 0.0 and new[2][0] < 4.0
        assert np.allclose(new[1], pos[1])
        assert stair_energy(new, adj) < e0
        again = stair_step(pos, adj, eta=0.5)
        assert all(np.allclose(new[v], again[v]) for v in pos)

    def test_orientation_assignment_order_invariant(self):
        rng_ys = [3.7, 1.2, 9.9, 5.5, 0.3, 7.1, 2.8, 6.6]
        pos = {v: np.array([float(v), rng_ys[v]]) for v in range(8)}
        adj = self._k(8)
        before = _stair_contacts(pos, adj)
        order = sorted(range(8), key=lambda v: (rng_ys[v], v))
        packed = {v: np.array([float(v), float(order.index(v))])
                  for v in range(8)}
        after = _stair_contacts(packed, adj)
        for v in range(8):
            assert sorted(before[v][0]) == sorted(after[v][0])
            assert sorted(before[v][1]) == sorted(after[v][1])


class TestArrangement:
    def _grid(self, B=20, cap=1.0):
        g = nx.convert_node_labels_to_integers(nx.grid_2d_graph(B, B))
        grid = TileGrid(g, nx.spectral_layout(g), fallback_bins=B)
        grid.cap[:, :, :] = cap
        return grid

    def test_line_depth(self):
        assert line_depth([]) == 0
        # touching endpoints do not overlap
        assert line_depth([(0, 2), (2, 4)]) == 1
        assert line_depth([(0, 2), (1, 3), (2, 4)]) == 2
        assert line_depth([(0, 4), (1, 3), (2, 5)]) == 3

    def test_arrange_packs_distinct_rows_and_is_monotone(self):
        grid = self._grid()
        n = 16  # deg 15 > kappa: all participate
        pos = {v: np.array([10.0 + 0.01 * v, 10.0 + 0.01 * v])
               for v in range(n)}
        adj = {v: [u for u in range(n) if u != v] for v in range(n)}
        new, info = alternate_arrange(pos, adj, grid, iters=8)
        assert info["assigned"] == n
        rows = [int(round(new[v][1])) for v in range(n)]
        cols = [int(round(new[v][0])) for v in range(n)]
        # pool depth 1 per line: overlapping intervals need distinct lines
        assert len(set(rows)) == n and len(set(cols)) == n
        # monotone after the feasibility projection (iteration 0 = 2 entries)
        tail = info["E"][3:]
        assert all(b <= a + 1e-6 for a, b in zip(tail, tail[1:]))
        again, _ = alternate_arrange(pos, adj, grid, iters=8)
        assert all(np.allclose(new[v], again[v]) for v in pos)

    def test_arrange_leaves_sparse_untouched(self):
        grid = self._grid()
        pos = {v: np.array([float(v), 3.7]) for v in range(8)}
        adj = {v: [u for u in (v - 1, v + 1) if 0 <= u < 8] for v in range(8)}
        new, info = alternate_arrange(pos, adj, grid)
        assert info["assigned"] == 0
        assert all(np.allclose(new[v], pos[v]) for v in pos)

    def test_alignment_couples_orders(self):
        # K16 from an anti-diagonal-ish init: alignment must couple x-rank
        # to y-rank (the busclique diagonal) and keep E near n*side
        grid = self._grid()
        n = 16
        pos = {v: np.array([10.0 - 0.3 * v, 4.0 + 0.3 * v])  # x anti-ordered
               for v in range(n)}
        adj = {v: [u for u in range(n) if u != v] for v in range(n)}
        new, info = alternate_arrange(pos, adj, grid, iters=8)
        xr = sorted(range(n), key=lambda v: (new[v][0], v))
        yr = sorted(range(n), key=lambda v: (new[v][1], v))
        assert xr == yr  # orders coupled: the diagonal
        # E ~ n * side for the staircase (16 rows at cap 1 -> side ~ 15)
        assert info["E"][-1] <= 16 * 16


class TestInsertionSweeps:
    def test_bipartite_blocks_emerge_from_interleaved(self):
        # K5,5 with blocks maximally interleaved in the initial order:
        # insertion must separate them (the biclique order)
        a = list(range(5))          # block A: 0..4
        b = list(range(5, 10))      # block B: 5..9
        adj = {v: (b if v in a else a) for v in range(10)}
        interleaved = [0, 5, 1, 6, 2, 7, 3, 8, 4, 9]
        new_order, traj = insertion_sweeps(interleaved, adj, max_sweeps=8)
        first_half = set(new_order[:5])
        assert first_half == set(a) or first_half == set(b)
        assert traj[-1] < traj[0]  # energy strictly improved
        again, _ = insertion_sweeps(interleaved, adj, max_sweeps=8)
        assert new_order == again  # deterministic

    def test_clique_is_noop(self):
        n = 8
        adj = {v: [u for u in range(n) if u != v] for v in range(n)}
        order = list(range(n))
        new_order, traj = insertion_sweeps(order, adj, max_sweeps=8)
        assert new_order == order          # permutation-symmetric: no move
        assert len(traj) == 2              # one sweep, no improvement, exit

    def test_monotone_energy(self):
        # random-ish structured graph: energy trajectory never increases
        g = nx.random_regular_graph(4, 12, seed=7)
        adj = {v: sorted(g.neighbors(v)) for v in g}
        order = sorted(g.nodes(), key=lambda v: (v * 7919) % 12)
        _, traj = insertion_sweeps(order, adj, max_sweeps=8)
        assert all(b <= a + 1e-9 for a, b in zip(traj, traj[1:]))

    def test_arrange_insert_no_worse_and_deterministic(self):
        g = nx.convert_node_labels_to_integers(nx.grid_2d_graph(20, 20))
        grid = TileGrid(g, nx.spectral_layout(g), fallback_bins=20)
        grid.cap[:, :, :] = 1.0
        n = 16
        pos = {v: np.array([10.0 + 0.01 * v, 10.0 + 0.01 * v])
               for v in range(n)}
        adj = {v: [u for u in range(n) if u != v] for v in range(n)}
        base, ib = alternate_arrange(pos, adj, grid, iters=8)
        ins, ii = alternate_arrange(pos, adj, grid, iters=8, insert_sweeps=4)
        assert ii["E"][-1] <= ib["E"][-1] + 1e-6  # composite E-gate holds
        again, _ = alternate_arrange(pos, adj, grid, iters=8, insert_sweeps=4)
        assert all(np.allclose(ins[v], again[v]) for v in pos)


class TestWireSeeds:
    def _chimera_grid(self):
        g = dnx.chimera_graph(8, 8, 4)
        return g, TileGrid(g, target_layout(g))

    def test_overlapping_bars_get_disjoint_contiguous_runs(self):
        g, grid = self._chimera_grid()
        pos = {0: np.array([2.0, 2.0]), 1: np.array([1.0, 2.0]),
               2: np.array([7.0, 7.0])}
        bars = {0: (np.array([2.0, 6.0]), np.array([2.0, 2.0])),
                1: (np.array([1.0, 5.0]), np.array([2.0, 2.0])),
                2: (np.array([7.0, 7.0]), np.array([7.0, 7.0]))}
        seeds = wire_seeds_iv(grid, pos, bars)
        allq = [q for c in seeds.values() for q in c]
        assert len(allq) == len(set(allq))       # no qubit claimed twice
        assert set(seeds) == {0, 1, 2}           # every variable seeded
        conv = dnx.chimera_coordinates(8, 8, 4)
        wires = {}
        for v in (0, 1):
            cs = [conv.linear_to_chimera(q) for q in seeds[v]]
            assert all(u == 1 for (_, _, u, _) in cs)         # horizontal
            assert len({(i, k) for (i, _, _, k) in cs}) == 1  # ONE wire
            wires[v] = {(i, k) for (i, _, _, k) in cs}.pop()
            js = sorted(j for (_, j, _, _) in cs)
            assert js == list(range(js[0], js[-1] + 1))       # contiguous
            # a contiguous same-wire run is a real coupled path
            assert nx.is_connected(g.subgraph(seeds[v]))
        # overlapping intervals on one row may NOT share a wire
        assert wires[0] != wires[1]

    def test_interval_seeds_cover_one_sided_bar(self):
        g, grid = self._chimera_grid()
        pos = {0: np.array([2.0, 5.0])}
        bars = {0: (np.array([2.0, 7.0]), np.array([5.0, 5.0]))}
        seeds = wire_seeds_iv(grid, pos, bars)
        conv = dnx.chimera_coordinates(8, 8, 4)
        cs = [conv.linear_to_chimera(q) for q in seeds[0]]
        assert all(u == 1 for (_, _, u, _) in cs)
        js = sorted(j for (_, j, _, _) in cs)
        # claims run over the ACTUAL interval [2, 7] -- a centered bar of the
        # same length at x=2 would span [-0.5, 4.5] and never reach column 6
        assert js[0] >= 2 and js[-1] >= 6

    def test_wire_seeds_iv_untyped_fallback(self):
        g = nx.convert_node_labels_to_integers(nx.grid_2d_graph(10, 10))
        grid = TileGrid(g, nx.spectral_layout(g), fallback_bins=10)
        pos = {0: np.array([2.0, 5.0])}
        bars = {0: (np.array([2.0, 6.0]), np.array([5.0, 5.0]))}
        seeds = wire_seeds_iv(grid, pos, bars)
        assert len(seeds[0]) >= 4  # center + ~1 qubit per interval tile


class TestCouplers:
    def test_couples_chimera_all_pairs(self):
        g = dnx.chimera_graph(4, 4, 4)
        grid = TileGrid(g, target_layout(g))
        for s in range(4):
            for s2 in range(4):
                assert _couples(grid, 1, s, 2, s2)

    def test_couples_pegasus_partial(self):
        g = dnx.pegasus_graph(4)
        grid = TileGrid(g, target_layout(g))
        hsubs = sorted({s for (u, ln, s) in grid.wire_map
                        if u == 1 and ln == 1})
        vsubs = sorted({s for (u, ln, s) in grid.wire_map
                        if u == 0 and ln == 1})
        vals = [_couples(grid, 1, s, 1, s2) for s in hsubs for s2 in vsubs]
        assert any(vals) and not all(vals)  # the ~56% structure is real

    def test_couples_missing_wire_false(self):
        g = dnx.chimera_graph(4, 4, 4)
        grid = TileGrid(g, target_layout(g))
        assert not _couples(grid, 1, 99, 2, 0)


class TestWireSeedsMatched:
    def test_line_tracks_depth(self):
        items = [(0.0, 4.0, 1), (1.0, 3.0, 2), (2.0, 5.0, 3), (4.5, 6.0, 4)]
        tr = _line_tracks(items)
        assert len(tr) == 3  # depth at x=2.5 is 3
        # disjoint arms share: (0,4) and (4.5,6) in one track
        assert any(len(t) == 2 for t in tr)

    def _stair_state(self, n=20, P=4):
        g = dnx.pegasus_graph(P)
        grid = TileGrid(g, target_layout(g))
        adj = {v: [u for u in range(n) if u != v] for v in range(n)}
        pos = {v: np.array([1.5 + 0.05 * v, 1.5 + 0.05 * v])
               for v in range(n)}
        pos = stair_step(pos, adj, eta=0.3)
        pos, _ = alternate_arrange(pos, adj, grid, iters=8)
        bars = derive_bars_stair(pos, adj, bounds=(grid.W, grid.H))
        return g, grid, adj, pos, bars

    def test_matching_beats_or_equals_greedy(self):
        g, grid, adj, pos, bars = self._stair_state()
        _, sat0, tot0 = wire_seeds_matched(grid, pos, bars, adj, sweeps=0)
        chains, sat, tot = wire_seeds_matched(grid, pos, bars, adj, sweeps=4)
        assert tot == tot0 and tot > 0
        assert sat >= sat0
        allq = [q for c in chains.values() for q in c]
        assert len(allq) == len(set(allq))  # disjoint
        again, sat2, _ = wire_seeds_matched(grid, pos, bars, adj, sweeps=4)
        assert chains == again and sat2 == sat  # deterministic

    def test_matching_finds_couplable_pair_greedy_misses(self):
        # force the designated arms onto tracks (i, j) whose greedy subs do
        # NOT couple, while hs[i] has SOME couplable v-partner: greedy init
        # scores 0, the matching must score 1
        g = dnx.pegasus_graph(4)
        grid = TileGrid(g, target_layout(g))
        found = None
        for r in range(1, grid.H - 1):
            for c in range(1, grid.W - 1):
                hs = sorted({s for (u, ln, s) in grid.wire_map
                             if u == 1 and ln == r})
                vs = sorted({s for (u, ln, s) in grid.wire_map
                             if u == 0 and ln == c})
                if len(hs) < 3 or len(vs) < 3:
                    continue
                for i in range(len(hs)):
                    for j in range(len(vs)):
                        if (not _couples(grid, r, hs[i], c, vs[j])
                                and any(_couples(grid, r, hs[i], c, s2)
                                        for s2 in vs)):
                            found = (r, c, i, j)
                            break
                    if found:
                        break
                if found:
                    break
            if found:
                break
        assert found is not None, "no greedy-miss configuration on P4?"
        r, c, i, j = found
        pos, bars, adj = {}, {}, {}
        vid = 0
        for k in range(i):   # h-fillers occupying tracks 0..i-1 on row r
            pos[vid] = np.array([c - 1.0, float(r)])
            bars[vid] = (np.array([c - 1.0 - 0.01 * (k + 1), c + 1.0]),
                         np.array([float(r)] * 2))
            adj[vid] = []
            vid += 1
        for k in range(j):   # v-fillers occupying tracks 0..j-1 on col c
            pos[vid] = np.array([float(c), r + 1.0])
            bars[vid] = (np.array([float(c)] * 2),
                         np.array([r - 1.0 - 0.01 * (k + 1), r + 1.0]))
            adj[vid] = []
            vid += 1
        vh, uv = vid, vid + 1  # designated pair: vh's h-arm x uv's v-arm
        pos[vh] = np.array([c - 1.0, float(r)])
        bars[vh] = (np.array([c - 1.0, c + 1.0]), np.array([float(r)] * 2))
        pos[uv] = np.array([float(c), r + 1.0])
        bars[uv] = (np.array([float(c)] * 2), np.array([r - 1.0, r + 1.0]))
        adj[vh] = [uv]
        adj[uv] = [vh]
        _, sat0, tot = wire_seeds_matched(grid, pos, bars, adj, sweeps=0)
        _, sat, _ = wire_seeds_matched(grid, pos, bars, adj, sweeps=4)
        assert tot == 1
        assert sat0 == 0   # greedy tracks (i, j) miss by construction
        assert sat == 1    # the matching recovers it

    def test_untyped_fallback(self):
        gu = nx.convert_node_labels_to_integers(nx.grid_2d_graph(10, 10))
        gridu = TileGrid(gu, nx.spectral_layout(gu), fallback_bins=10)
        ch, s, t = wire_seeds_matched(gridu, {0: np.array([2.0, 5.0])},
                                      {0: (np.array([2.0, 6.0]),
                                           np.array([5.0, 5.0]))},
                                      {0: []})
        assert ch and s == 0 and t == 0  # graceful untyped fallback


class TestBarDomains:
    def test_bar_domains_gating_and_bands(self):
        g = dnx.chimera_graph(8, 8, 4)
        grid = TileGrid(g, target_layout(g))
        n = 15  # v0 has deg 14 > kappa; leaves have deg 1
        pos = {0: np.array([4.0, 3.0])}
        pos.update({v: np.array([2.0 + 0.2 * v, 3.0]) for v in range(1, n)})
        adj = {0: list(range(1, n))}
        adj.update({v: [0] for v in range(1, n)})
        bars = {0: (np.array([2.0, 6.0]), np.array([1.0, 5.0]))}
        bars.update({v: (np.array([pos[v][0]] * 2), np.array([3.0, 3.0]))
                     for v in range(1, n)})
        doms = bar_domains(grid, pos, bars, adj, margin=1)
        assert set(doms) == {0}  # capacity-gated: only the hub
        conv = dnx.chimera_coordinates(8, 8, 4)
        assert len(doms[0]) > 0
        for q in doms[0]:
            i, j, u, k = conv.linear_to_chimera(q)
            if u == 1:   # h-wire: row band around row 3, cols in [2-1, 6+1]
                assert abs(i - 3) <= 1 and 1 <= j <= 7
            else:        # v-wire: col band around col 4, rows in [1-1, 5+1]
                assert abs(j - 4) <= 1 and 0 <= i <= 6
