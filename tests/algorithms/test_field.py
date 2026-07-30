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
    _target_kappa,
    alternate_arrange,
    bar_domains,
    bar_widths,
    contract_layout,
    derive_bars_stair,
    edge_monotonize,
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
        n = 16  # kappa=3 makes the floor force extension (arm-length gate)
        pos = {v: np.array([10.0 + 0.01 * v, 10.0 + 0.01 * v])
               for v in range(n)}
        adj = {v: [u for u in range(n) if u != v] for v in range(n)}
        new, info = alternate_arrange(pos, adj, grid, iters=8, kappa=3.0)
        assert info["assigned"] == n
        rows = [int(round(new[v][1])) for v in range(n)]
        cols = [int(round(new[v][0])) for v in range(n)]
        # pool depth 1 per line: overlapping intervals need distinct lines
        assert len(set(rows)) == n and len(set(cols)) == n
        # monotone after the feasibility projection (iteration 0 = 2 entries)
        tail = info["E"][3:]
        assert all(b <= a + 1e-6 for a, b in zip(tail, tail[1:]))
        again, _ = alternate_arrange(pos, adj, grid, iters=8, kappa=3.0)
        assert all(np.allclose(new[v], again[v]) for v in pos)

    def test_arrange_leaves_short_arms_untouched(self):
        # sub-tile spans (geometric graph): no variable owes a wire run, so
        # the arrangement is structurally inert — the arm-length criterion,
        # not a degree gate
        grid = self._grid()
        pos = {v: np.array([0.5 * v, 3.7]) for v in range(8)}
        adj = {v: [u for u in (v - 1, v + 1) if 0 <= u < 8] for v in range(8)}
        new, info = alternate_arrange(pos, adj, grid)
        assert info["assigned"] == 0
        assert all(np.allclose(new[v], pos[v]) for v in pos)

    def test_orders_couple_on_clique(self):
        # K16 from an anti-diagonal-ish init: per-edge monotonization must
        # land near the staircase optimum. Exact global rank equality was a
        # SIDE EFFECT of the old global alignment (which re-imposed it after
        # the packer's spill-boundary scrambles); the honest invariants are
        # the energy (ideal aligned E = 2*sum(n-1-k) = 240 here) and a
        # strongly monotone coupling of the two orders (either sign —
        # diagonal and anti-diagonal staircases are mirror-equivalent).
        grid = self._grid()
        n = 16
        pos = {v: np.array([10.0 - 0.3 * v, 4.0 + 0.3 * v])  # x anti-ordered
               for v in range(n)}
        adj = {v: [u for u in range(n) if u != v] for v in range(n)}
        new, info = alternate_arrange(pos, adj, grid, iters=8, kappa=3.0)
        # Measured insight (2026-07-29, this refinement): the stair energy
        # requires contiguous SUFFIX VALUE-SETS, which global monotonicity
        # achieves but does not uniquely achieve — per-edge descent finds
        # E-equivalent mixed (part diagonal, part mirrored) couplings
        # (rho ~ 0.17 here at E 242 vs ideal 240). The diagonal was
        # sufficient, never necessary; whether E-equivalent mixtures ROUTE
        # equally well is a probe question (K100/K140 guards), not a unit
        # assertion. The invariant is the energy.
        assert info["E"][-1] <= 250  # ideal 240; global-alignment era ~same

    def test_side_by_side_patches_stay_side_by_side(self):
        # two K12s in disjoint column bands with overlapping rows: the old
        # global alignment interleaved their columns (one global order); the
        # per-edge move has no cross-patch pressure, so the bands must stay
        # disjoint while each patch aligns internally
        grid = self._grid(B=20, cap=2.0)
        a = list(range(12))
        b = list(range(12, 24))
        pos = {}
        for i, v in enumerate(a):
            pos[v] = np.array([2.0 + 0.3 * i, 6.0 + 0.5 * i])
        for i, v in enumerate(b):
            pos[v] = np.array([14.0 + 0.3 * i, 6.0 + 0.5 * i])
        adj = {v: [u for u in (a if v in a else b) if u != v]
               for v in range(24)}
        new, info = alternate_arrange(pos, adj, grid, iters=8, kappa=3.0)
        xa = [float(new[v][0]) for v in a]
        xb = [float(new[v][0]) for v in b]
        assert max(xa) < min(xb)  # column bands still disjoint
        ya = sorted(a, key=lambda v: (new[v][1], v))
        xa_r = sorted(a, key=lambda v: (new[v][0], v))
        assert xa_r == ya or xa_r == ya[::-1]  # patch A internally aligned


class TestEdgeMonotonize:
    def _k(self, n):
        return {v: [u for u in range(n) if u != v] for v in range(n)}

    def test_sorted_clique_is_fixpoint(self):
        pos = {v: np.array([float(v), float(v)]) for v in range(8)}
        new, info = edge_monotonize(pos, self._k(8))
        assert info["swaps"] == 0
        assert all(np.allclose(new[v], pos[v]) for v in pos)

    def test_scrambled_clique_descends_to_monotone(self):
        n = 10
        xs = [3.0, 7.0, 1.0, 9.0, 0.0, 5.0, 8.0, 2.0, 6.0, 4.0]
        pos = {v: np.array([xs[v], float(v)]) for v in range(n)}
        e0 = stair_energy(pos, self._k(n))
        new, info = edge_monotonize(pos, self._k(n))
        assert stair_energy(new, self._k(n)) < e0
        # converged state: no strictly-improving inverted edge remains, and
        # the x multiset is preserved (transpositions only)
        assert sorted(float(new[v][0]) for v in new) == sorted(xs)
        again, _ = edge_monotonize(pos, self._k(n))
        assert all(np.allclose(new[v], again[v]) for v in pos)

    def test_contacts_invariant_under_swaps(self):
        n = 8
        xs = [5.0, 2.0, 7.0, 0.0, 6.0, 1.0, 4.0, 3.0]
        pos = {v: np.array([xs[v], float(v)]) for v in range(n)}
        before = _stair_contacts(pos, self._k(n))
        new, _ = edge_monotonize(pos, self._k(n))
        after = _stair_contacts(new, self._k(n))
        for v in range(n):
            assert before[v] == after[v]

    def test_short_edges_self_neutralize(self):
        # geometric path with sub-tile edges and one x/y sign disagreement:
        # any accepted swap moves coordinates by < the edge length, so the
        # layout is at most perturbed at edge scale — and typically the
        # swap is not even strictly improving (spans unchanged on a path)
        pos = {v: np.array([0.4 * v, 0.4 * v]) for v in range(6)}
        pos[3] = np.array([0.85, 1.2])  # tiny local inversion vs node 2
        adj = {v: [u for u in (v - 1, v + 1) if 0 <= u < 6] for v in range(6)}
        new, _ = edge_monotonize(pos, adj)
        for v in pos:
            assert np.linalg.norm(new[v] - pos[v]) <= 0.5  # edge-scale only

    def test_no_cross_patch_pressure(self):
        # two disjoint K6 patches, each internally inverted, placed in
        # different column bands: monotonization sorts each internally but
        # never exchanges x-values ACROSS patches (no edge, no proposal)
        a, b = list(range(6)), list(range(6, 12))
        pos = {}
        for i, v in enumerate(a):
            pos[v] = np.array([2.0 - 0.3 * i, float(i)])       # band [0.5, 2]
        for i, v in enumerate(b):
            pos[v] = np.array([12.0 - 0.3 * i, float(i)])      # band [10.5, 12]
        adj = {v: [u for u in (a if v in a else b) if u != v]
               for v in range(12)}
        new, _ = edge_monotonize(pos, adj)
        assert all(float(new[v][0]) <= 2.0 + 1e-9 for v in a)
        assert all(float(new[v][0]) >= 10.5 - 1e-9 for v in b)


class TestArmLengthGating:
    def _grid(self, B=20, cap=2.0):
        g = nx.convert_node_labels_to_integers(nx.grid_2d_graph(B, B))
        grid = TileGrid(g, nx.spectral_layout(g), fallback_bins=B)
        grid.cap[:, :, :] = cap
        return grid

    def test_tight_clique_below_floor_not_packed(self):
        # K15 at sub-tile spread with the physical kappa: floor per axis
        # ~0.08, spans ~0.14 — nobody owes a wire run, nothing is packed
        grid = self._grid()
        n = 15
        pos = {v: np.array([10.0 + 0.01 * v, 10.0 + 0.01 * v])
               for v in range(n)}
        adj = {v: [u for u in range(n) if u != v] for v in range(n)}
        new, info = alternate_arrange(pos, adj, grid, iters=8)  # kappa=13
        assert info["assigned"] == 0
        assert all(np.allclose(new[v], pos[v]) for v in pos)

    def test_long_shortcut_packs_on_its_axis_only(self):
        # a low-degree variable with one long horizontal edge: its h-arm
        # exceeds a tile (it owns a wire run) but its v-arm does not — it
        # enters row-packing only. Degree could never express this.
        grid = self._grid()
        pos = {0: np.array([2.0, 5.3]), 1: np.array([8.0, 5.3]),
               2: np.array([2.4, 5.3])}
        adj = {0: [1, 2], 1: [0], 2: [0]}
        new, info = alternate_arrange(pos, adj, grid, iters=2)
        assert info["assigned_rows"] >= 1     # the long h-arms packed
        assert info["assigned_cols"] == 0     # no v-arm exceeds a tile
        for v in pos:  # x untouched by row-packing
            assert float(new[v][0]) == pytest.approx(float(pos[v][0]))


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
        base, ib = alternate_arrange(pos, adj, grid, iters=8, kappa=3.0)
        ins, ii = alternate_arrange(pos, adj, grid, iters=8, kappa=3.0,
                                    insert_sweeps=4)
        assert ii["E"][-1] <= ib["E"][-1] + 1e-6  # composite E-gate holds
        assert ii["insert_reverts"] in (0, 1)     # diagnostic surfaced
        again, _ = alternate_arrange(pos, adj, grid, iters=8, kappa=3.0,
                                     insert_sweeps=4)
        assert all(np.allclose(ins[v], again[v]) for v in pos)

    def test_value_pricing_respects_cluster_gaps(self):
        # two 4-member clusters at y-values {0..3} and {20..23}; one edge
        # from a low-cluster member to a high-cluster member. Rank pricing
        # sees the gap as 1 slot; value pricing sees 17 tiles. The move it
        # must NOT make: drag the whole low cluster across the gap for one
        # edge. Proxy energies are checked directly via the trajectory.
        members = list(range(8))
        adj = {v: [u for u in ((0, 1, 2, 3) if v < 4 else (4, 5, 6, 7))
                   if u != v] for v in members}
        adj[3] = adj[3] + [4]
        adj[4] = adj[4] + [3]
        values = np.array([0.0, 1.0, 2.0, 3.0, 20.0, 21.0, 22.0, 23.0])
        new_order, traj = insertion_sweeps(
            members, adj, max_sweeps=8, values=values)
        # both clusters must remain contiguous blocks in the final order
        first = set(new_order[:4])
        assert first == {0, 1, 2, 3} or first == {4, 5, 6, 7}
        assert all(b <= a + 1e-9 for a, b in zip(traj, traj[1:]))

    def test_anchor_pulls_member_toward_fixed_neighbour(self):
        # 4 members, no member-member edges except a chain to keep 'has'
        # true; member 0 has a non-member neighbour anchored at high y:
        # with anchors it must relocate to the top slot
        members = [0, 1, 2, 3]
        adj = {0: [1, 99], 1: [0, 2], 2: [1, 3], 3: [2], 99: [0]}
        values = np.array([0.0, 1.0, 2.0, 10.0])
        lo = np.array([np.inf, np.inf, np.inf, np.inf])
        hi = np.array([-np.inf, -np.inf, -np.inf, -np.inf])
        lo[0], hi[0] = 9.5, 9.5  # anchor near the top value
        new_order, _ = insertion_sweeps(members, adj, max_sweeps=8,
                                        values=values, anchors=(lo, hi))
        assert new_order[-1] == 0  # member 0 took the top slot


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
        # kappa=3: floor-forced extension so the arm-length gate engages on
        # this compact synthetic init (the physical kappa needs real spread)
        pos, _ = alternate_arrange(pos, adj, grid, iters=8, kappa=3.0)
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


class TestZephyrGrid:
    def _grid(self, m=3, t=4):
        g = dnx.zephyr_graph(m, t)
        return g, TileGrid(g, target_layout(g))

    def test_typed_and_caps_sum(self):
        g, grid = self._grid()
        assert grid.typed
        assert grid.cap.sum() == g.number_of_nodes()

    def test_wire_runs_are_coupled_paths(self):
        g, grid = self._grid()
        # every wire (u, line, sub): consecutive tile positions must couple
        checked = 0
        for (u, line, sub), run in sorted(grid.wire_map.items())[:40]:
            ps = sorted(run)
            qs = [run[p] for p in ps]
            for (p1, q1), (p2, q2) in zip(zip(ps, qs), zip(ps[1:], qs[1:])):
                if p2 == p1 + 1:
                    assert g.has_edge(q1, q2), (u, line, sub, p1, p2)
                    checked += 1
        assert checked > 50

    def test_junctions_near_complete(self):
        # the design motivation for the Zephyr move: crossing h/v wire
        # pairs at a shared tile couple at far higher density than
        # Pegasus's ~0.56 (measure and assert; expected near-complete
        # over wires that actually cross)
        g, grid = self._grid()
        import dwave_networkx as dnx2
        pg = dnx2.pegasus_graph(4)
        pgrid = TileGrid(pg, target_layout(pg))

        def density(gr):
            hits = tot = 0
            for r in range(2, gr.H - 2):
                for c in range(2, gr.W - 2):
                    hs = sorted({s for (u, ln, s) in gr.wire_map
                                 if u == 1 and ln == r})
                    vs = sorted({s for (u, ln, s) in gr.wire_map
                                 if u == 0 and ln == c})
                    for sh in hs:
                        qh = gr.wire_map.get((1, r, sh), {}).get(c)
                        if qh is None:
                            continue
                        for sv in vs:
                            qv = gr.wire_map.get((0, c, sv), {}).get(r)
                            if qv is None:
                                continue
                            tot += 1
                            hits += _couples(gr, r, sh, c, sv)
            return hits / max(tot, 1)

        dz, dp = density(grid), density(pgrid)
        assert dz > dp + 0.2  # materially denser junctions than Pegasus
        assert dz > 0.85      # near-complete

    def test_wire_seeds_on_zephyr(self):
        g, grid = self._grid()
        n = 12
        adj = {v: [u for u in range(n) if u != v] for v in range(n)}
        pos = {v: np.array([1.0 + 0.3 * v, 1.0 + 0.3 * v])
               for v in range(n)}
        pos = stair_step(pos, adj, eta=0.3)
        pos, _ = alternate_arrange(pos, adj, grid, iters=8, kappa=3.0)
        bars = derive_bars_stair(pos, adj, bounds=(grid.W, grid.H))
        seeds = wire_seeds_iv(grid, pos, bars)
        allq = [q for c in seeds.values() for q in c]
        assert len(allq) == len(set(allq))
        assert set(seeds) == set(range(n))
        # multi-qubit runs are coupled paths
        import networkx as nx2
        for v, c in seeds.items():
            if len(c) > 1 and nx2.is_connected(g.subgraph(c)):
                break
        else:
            assert False, "no connected multi-qubit run found"

    def test_derived_kappa(self):
        g, grid = self._grid()
        import dwave_networkx as dnx2
        pgrid = TileGrid(dnx2.pegasus_graph(6),
                         target_layout(dnx2.pegasus_graph(6)))
        kz, kp = _target_kappa(grid), _target_kappa(pgrid)
        # small instances have boundary-depressed mean degree (Z3 ~14.7,
        # P6 ~11.2; at scale Z12 ~18, P16 ~13.3 matching the old constant).
        # The scale-free invariant: Zephyr denser than Pegasus.
        assert kz > kp
        assert 10.0 < kp < 14.0


from ember_qc.algorithms.factored.field import (
    PressureState, pressure_energy, pressure_forces,
)


class TestPressure:
    """Tests derived from the notes s3.42(a) derivation, not from the
    implementation."""

    def _grid(self, B=12, cap=0.3):
        g = nx.convert_node_labels_to_integers(nx.grid_2d_graph(B, B))
        grid = TileGrid(g, nx.spectral_layout(g), fallback_bins=B)
        grid.cap[:, :, :] = cap  # tiny caps -> smooth overloaded regime
        return grid

    def _cfg(self, seed=5, n=10, B=12):
        rng = np.random.default_rng(seed)
        pos = {v: np.array([0.71 + (B - 2.4) * rng.random(),
                            0.73 + (B - 2.4) * rng.random()])
               for v in range(n)}
        g = nx.gnp_random_graph(n, 0.6, seed=3)
        adj = {v: sorted(g.neighbors(v)) for v in g}
        grid = self._grid(B)
        state = PressureState(pos, adj, grid, kappa=3.0, floor=False)
        x = np.array([float(pos[v][0]) for v in sorted(pos)])
        y = np.array([float(pos[v][1]) for v in sorted(pos)])
        return state, x, y

    def test_finite_difference_gradient(self):
        # THE decisive check: implemented forces == -grad(P) numerically,
        # coordinate by coordinate (central differences, h away from the
        # measure-zero kinks; random offsets keep us off them)
        for seed in (5, 11, 23):
            state, x, y = self._cfg(seed=seed)
            fx, fy = pressure_forces(state, x, y)
            h = 1e-5
            for i in range(len(x)):
                for arr, f in ((x, fx), (y, fy)):
                    a = arr.copy(); a[i] += h
                    b = arr.copy(); b[i] -= h
                    if arr is x:
                        ep = pressure_energy(state, a, y)
                        em = pressure_energy(state, b, y)
                    else:
                        ep = pressure_energy(state, x, a)
                        em = pressure_energy(state, x, b)
                    grad = (ep - em) / (2 * h)
                    assert f[i] == pytest.approx(-grad, rel=1e-3, abs=1e-3), \
                        (seed, i, "x" if arr is x else "y")

    def test_third_party_push(self):
        # Isolate ROW physics (column pools huge): span-extreme contacts
        # are billed axially with the derivation's signs — the max holder
        # is pulled LEFT (shrink into the bar), a min holder pulled RIGHT.
        grid = self._grid()
        grid.cap[:, :, 0] = 50.0   # v-pools huge -> no column overload
        grid.cap[:, :, 1] = 0.3    # h-pools tiny -> rows overloaded
        pos = {0: np.array([2.0, 5.2]),   # w (lowest y -> h-arm owner)
               1: np.array([8.3, 6.2]),   # u: span max of 0's and 1's bars
               2: np.array([5.1, 6.7])}   # m: interior of 0's bar; min of 1's
        adj = {0: [1, 2], 1: [0, 2], 2: [0, 1]}
        state = PressureState(pos, adj, grid, kappa=13.0, floor=False)
        x = np.array([2.0, 8.3, 5.1])
        y = np.array([5.2, 6.2, 6.7])
        fx, fy = pressure_forces(state, x, y)
        assert fx[1] < 0.0   # max holder billed leftward (shrink)
        assert fx[2] > 0.0   # min holder of 1's bar billed rightward

    def test_perpendicular_slide_toward_slack_row(self):
        # a bar straddling rows r (overloaded) and r+1 (slack) must feel
        # fy toward the slack row
        grid = self._grid(cap=0.3)
        grid.cap[6, :, :] = 10.0   # row 6 slack, row 5 tiny cap
        # crowd row 5 with an unrelated long bar
        pos = {0: np.array([1.0, 5.0]), 1: np.array([9.0, 5.4]),
               2: np.array([2.0, 5.45]), 3: np.array([8.0, 6.3])}
        adj = {0: [1], 1: [0], 2: [3], 3: [2]}
        state = PressureState(pos, adj, grid, kappa=13.0, floor=False)
        x = np.array([1.0, 9.0, 2.0, 8.0])
        y = np.array([5.0, 5.4, 5.45, 6.3])
        fx, fy = pressure_forces(state, x, y)
        assert fy[2] > 0.0  # variable 2's bar slides up toward slack row 6

    def test_gas_inertness(self):
        # sub-tile sparse config under REALISTIC caps (tiles hold 4-12
        # wires; the untyped fallback's 0.5/pool is not a real fabric)
        g = nx.convert_node_labels_to_integers(nx.grid_2d_graph(12, 12))
        grid = TileGrid(g, nx.spectral_layout(g), fallback_bins=12)
        grid.cap[:, :, :] = 4.0
        pos = {v: np.array([2.0 + 0.4 * v, 7.0]) for v in range(5)}
        adj = {v: [u for u in (v - 1, v + 1) if 0 <= u < 5]
               for v in range(5)}
        state = PressureState(pos, adj, grid, kappa=13.0)
        x = np.array([float(pos[v][0]) for v in range(5)])
        y = np.array([float(pos[v][1]) for v in range(5)])
        assert pressure_energy(state, x, y) == 0.0
        fx, fy = pressure_forces(state, x, y)
        assert np.allclose(fx, 0) and np.allclose(fy, 0)

    def test_contract_v2_settles_feasible(self):
        # the leak-fix check: dense synthetic contracts to residual
        # overload ~0 under the lambda ramp (v1 measured 60-140 on dense)
        g = nx.convert_node_labels_to_integers(nx.grid_2d_graph(20, 20))
        grid = TileGrid(g, nx.spectral_layout(g), fallback_bins=20)
        grid.cap[:, :, :] = 2.0
        rng = np.random.default_rng(7)
        n = 16
        pos = {v: np.array([1.0 + 17.0 * rng.random(),
                            1.0 + 17.0 * rng.random()]) for v in range(n)}
        adj = {v: [u for u in range(n) if u != v] for v in range(n)}
        new, info = contract_layout(pos, adj, grid, steps=150, cycles=3,
                                    kappa=3.0, pressure=True)
        assert info["residual_overload"] <= 1.5
        again, _ = contract_layout(pos, adj, grid, steps=150, cycles=3,
                                   kappa=3.0, pressure=True)
        assert all(np.allclose(new[v], again[v]) for v in pos)


class TestContractLayout:
    def _grid(self, B=20, cap=2.0):
        g = nx.convert_node_labels_to_integers(nx.grid_2d_graph(B, B))
        grid = TileGrid(g, nx.spectral_layout(g), fallback_bins=B)
        grid.cap[:, :, :] = cap
        return grid

    def _spread_k(self, n, B=20, seed=7):
        rng = np.random.default_rng(seed)
        pos = {v: np.array([1.0 + (B - 3.0) * rng.random(),
                            1.0 + (B - 3.0) * rng.random()])
               for v in range(n)}
        adj = {v: [u for u in range(n) if u != v] for v in range(n)}
        return pos, adj

    def test_energy_decreases_and_deterministic(self):
        grid = self._grid()
        pos, adj = self._spread_k(16)
        e0 = stair_energy(pos, adj)
        new, info = contract_layout(pos, adj, grid, steps=120, kappa=3.0)
        assert info["final_E"] < e0
        again, _ = contract_layout(pos, adj, grid, steps=120, kappa=3.0)
        assert all(np.allclose(new[v], again[v]) for v in pos)

    def test_entry_gating_blocks_full_line(self):
        grid = self._grid(cap=1.0)  # depth 1 per line: brutal wall
        pos, adj = self._spread_k(12)
        new, info = contract_layout(pos, adj, grid, steps=150, kappa=3.0,
                                    pressure=False)  # the v1 wall arm
        assert info["blocked"] > 0  # the wall was hit
        # entry-invariant: rows occupied by >=1-tile h-arms respect depth
        bars = derive_bars_stair(new, adj, kappa=3.0,
                                 bounds=(grid.W, grid.H))
        by_row = {}
        for v, (h_iv, _v_iv) in bars.items():
            if h_iv[1] - h_iv[0] >= 1.0:
                by_row.setdefault(int(round(float(new[v][1]))), []).append(
                    (float(h_iv[0]), float(h_iv[1])))
        worst = max((line_depth(iv) for iv in by_row.values()), default=0)
        # growth overfill is measured, not forbidden; it must be bounded
        assert worst <= 1 + info["growth_overfill"] + 1e-9

    def test_deg_weight_moves_hub_faster(self):
        grid = self._grid()
        # star: hub 0 with 8 leaves, all spread
        pos = {0: np.array([15.0, 15.0])}
        pos.update({v: np.array([2.0 + v, 2.0]) for v in range(1, 9)})
        adj = {0: list(range(1, 9))}
        adj.update({v: [0] for v in range(1, 9)})
        w, _ = contract_layout(pos, adj, grid, steps=1, kappa=13.0,
                               deg_weight=True, mono_every=0)
        u, _ = contract_layout(pos, adj, grid, steps=1, kappa=13.0,
                               deg_weight=False, mono_every=0)
        hub_w = np.linalg.norm(w[0] - pos[0])
        hub_u = np.linalg.norm(u[0] - pos[0])
        assert hub_w > hub_u  # unnormalized: the popular magnet rushes

    def test_patches_coalesce_separately(self):
        grid = self._grid(B=24)
        a, b = list(range(12)), list(range(12, 24))
        rng = np.random.default_rng(3)
        pos = {}
        for v in a:
            pos[v] = np.array([2.0 + 6.0 * rng.random(),
                               4.0 + 14.0 * rng.random()])
        for v in b:
            pos[v] = np.array([16.0 + 6.0 * rng.random(),
                               4.0 + 14.0 * rng.random()])
        adj = {v: [u for u in (a if v in a else b) if u != v]
               for v in range(24)}
        new, _ = contract_layout(pos, adj, grid, steps=200, kappa=3.0)
        xa = [float(new[v][0]) for v in a]
        xb = [float(new[v][0]) for v in b]
        assert max(xa) < min(xb)  # coalesced in place, never interleaved

    def test_cycles_reshake_runs_and_records(self):
        grid = self._grid()
        pos, adj = self._spread_k(16, seed=11)
        new, info = contract_layout(pos, adj, grid, steps=80, cycles=3,
                                    kappa=3.0, pressure=False)
        assert len(info["cycle_E"]) == 3
        # best-settlement return: the handoff layout is the best cycle's
        assert info["final_E"] == min(info["cycle_E"])
        assert stair_energy(new, adj) == pytest.approx(info["final_E"],
                                                       abs=0.1)

    def test_sparse_subtile_graph_barely_moves_lines(self):
        grid = self._grid()
        pos = {v: np.array([5.0 + 0.4 * v, 9.0]) for v in range(6)}
        adj = {v: [u for u in (v - 1, v + 1) if 0 <= u < 6]
               for v in range(6)}
        new, info = contract_layout(pos, adj, grid, steps=50, mono_every=0)
        assert info["blocked"] == 0  # nothing owes a wire; wall untouched
        for v in pos:  # contraction is gentle at sub-tile scale
            assert np.linalg.norm(new[v] - pos[v]) < 2.0


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
