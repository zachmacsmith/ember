"""
tests/algorithms/test_field.py
================================
Tests for the VLSI-style coarse model (ember_qc.algorithms.factored.field):
typed tile capacities, segment-smeared deposits (traversal charging), and the
one-sided Poisson repulsion field (zero-on-slack, Gauss interior force, mu
multiplier dynamics).
"""
import networkx as nx
import numpy as np
import pytest
import dwave_networkx as dnx

from ember_qc.algorithms.factored.field import PoissonField, TileGrid
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


class TestDeposits:
    def test_total_mass_conserved(self):
        g = dnx.chimera_graph(4, 4, 4)
        grid = make_grid(g)
        pos = target_layout(g)
        src = nx.path_graph(3)
        adj = {v: sorted(src.neighbors(v)) for v in src}
        qs = sorted(pos)
        cent = {0: pos[qs[0]], 1: pos[qs[40]], 2: pos[qs[100]]}
        lam = {0: 4.0, 1: 6.0, 2: 2.0}
        demand = grid.deposit(cent, lam, adj, smear=True)
        assert demand.sum() == pytest.approx(sum(lam.values()))

    def test_traversal_charges_intermediate_tiles(self):
        g = dnx.chimera_graph(8, 8, 4)
        grid = make_grid(g)
        # two variables at opposite horizontal ends, connected
        cent = {0: grid.Minv @ (np.array([0.5, 4.0]) - grid.c),
                1: grid.Minv @ (np.array([7.5, 4.0]) - grid.c)}
        demand = grid.deposit(cent, {0: 8.0, 1: 8.0}, {0: [1], 1: [0]},
                              smear=True)
        # middle tiles along the row must carry deposited mass
        assert demand[4, 3, :].sum() > 0 or demand[4, 4, :].sum() > 0
        # and it lands (mostly) in the horizontal pool for an h-segment
        row = demand[4, :, :]
        assert row[:, 1].sum() > row[:, 0].sum()

    def test_point_mode_charges_only_own_tile(self):
        g = dnx.chimera_graph(8, 8, 4)
        grid = make_grid(g)
        cent = {0: grid.Minv @ (np.array([0.5, 4.0]) - grid.c),
                1: grid.Minv @ (np.array([7.5, 4.0]) - grid.c)}
        demand = grid.deposit(cent, {0: 8.0, 1: 8.0}, {0: [1], 1: [0]},
                              smear=False)
        assert demand[4, 2:6, :].sum() == pytest.approx(0.0)


class TestPoissonField:
    def _uniform_grid(self, B=8, cap=4.0):
        g = nx.grid_2d_graph(B, B)
        g = nx.convert_node_labels_to_integers(g)
        grid = TileGrid(g, nx.spectral_layout(g), fallback_bins=B)
        grid.cap[:, :, :] = cap / 2.0
        return grid

    def test_zero_force_when_slack(self):
        grid = self._uniform_grid()
        f = PoissonField(grid)
        demand = np.zeros_like(grid.cap)
        demand[:, :, :] = 1.0  # under capacity everywhere
        psi = f.potential(demand)
        assert np.allclose(psi, 0.0)

    def test_gauss_interior_force(self):
        grid = self._uniform_grid(B=9, cap=2.0)
        f = PoissonField(grid)
        demand = np.zeros_like(grid.cap)
        demand[2:7, 2:7, :] = 4.0  # uniformly overfull 5x5 blob, center (4,4)
        psi = f.potential(demand)
        pts = {"center": np.array([4.0, 4.0]),
               "inner": np.array([5.0, 4.0]),   # inside the blob, off-center
               "far": np.array([8.0, 4.0])}
        forces = f.force_at(psi, pts, scale=1.0)
        # interior point off-center feels a strictly outward (positive-x) push
        assert forces["inner"][0] > 1e-6
        # center is (near) equilibrium by symmetry
        assert abs(forces["center"][0]) < abs(forces["inner"][0])
        # field is long-range: even outside the blob the push is outward
        assert forces["far"][0] >= 0.0

    def test_mu_dynamics(self):
        grid = self._uniform_grid()
        f = PoissonField(grid, mu_alpha=0.5)
        over = np.zeros_like(grid.cap); over[:, :, :] = 10.0
        under = np.zeros_like(grid.cap)
        f.update_mu(over)
        rose = f.mu.sum()
        assert rose > 0
        f.update_mu(under)
        assert f.mu.sum() < rose  # decays while slack
        for _ in range(50):
            f.update_mu(under)
        assert f.mu.sum() == pytest.approx(0.0)  # floors at zero

    def test_trust_region_clip(self):
        grid = self._uniform_grid(B=8, cap=0.5)
        f = PoissonField(grid, max_step=1.0)
        demand = np.zeros_like(grid.cap)
        demand[3:5, 3:5, :] = 500.0  # violent violation
        psi = f.potential(demand)
        forces = f.force_at(psi, {0: np.array([4.5, 4.0])}, scale=50.0)
        assert np.hypot(*forces[0]) <= 1.0 + 1e-9


from ember_qc.algorithms.factored.field import (
    bar_seeds, contact_step, deposit_cross, fit_extents,
)


class TestCrossState:
    def _pts(self, d):
        return {k: np.array(v, dtype=float) for k, v in d.items()}

    def test_point_limit_is_l1_attraction(self):
        pos = self._pts({0: [0.0, 0.0], 1: [4.0, 3.0]})
        ext = self._pts({0: [0.0, 0.0], 1: [0.0, 0.0]})
        np2, ne = contact_step(pos, ext, {0: [1], 1: [0]},
                               eta=0.1, extent_eta=0.0, extent_cost=0.0)
        # both move toward each other, componentwise (L1 gradient signs)
        assert np2[0][0] > 0 and np2[0][1] > 0
        assert np2[1][0] < 4.0 and np2[1][1] < 3.0

    def test_crossing_bars_exert_no_force(self):
        # u's h-bar spans x in [-3,3] at y=0; v's v-bar spans y in [-3,3] at x=2
        pos = self._pts({0: [0.0, 0.0], 1: [2.0, 2.0]})
        ext = self._pts({0: [6.0, 0.0], 1: [0.0, 6.0]})
        np2, ne = contact_step(pos, ext, {0: [1], 1: [0]},
                               eta=0.5, extent_eta=0.5, extent_cost=0.0)
        assert np.allclose(np2[0], pos[0]) and np.allclose(np2[1], pos[1])
        assert np.allclose(ne[0], ext[0]) and np.allclose(ne[1], ext[1])

    def test_deficit_grows_extents(self):
        pos = self._pts({0: [0.0, 0.0], 1: [5.0, 5.0]})
        ext = self._pts({0: [0.0, 0.0], 1: [0.0, 0.0]})
        _, ne = contact_step(pos, ext, {0: [1], 1: [0]},
                             eta=0.0, extent_eta=0.3, extent_cost=0.0)
        assert ne[0].sum() + ne[1].sum() > 0  # some bar grew

    def test_extent_cost_shrinks_unneeded_bars(self):
        pos = self._pts({0: [0.0, 0.0], 1: [0.5, 0.5]})
        ext = self._pts({0: [4.0, 4.0], 1: [4.0, 4.0]})  # crossing, oversized
        _, ne = contact_step(pos, ext, {0: [1], 1: [0]},
                             eta=0.0, extent_eta=0.5, extent_cost=0.2)
        assert ne[0].sum() < 8.0 and ne[1].sum() < 8.0

    def test_deposit_cross_mass(self):
        g = dnx.chimera_graph(8, 8, 4)
        grid = TileGrid(g, target_layout(g))
        pos = self._pts({0: [4.0, 4.0], 1: [2.0, 2.0]})
        ext = self._pts({0: [4.0, 2.0], 1: [0.0, 0.0]})
        demand = deposit_cross(grid, pos, ext)
        assert demand.sum() == pytest.approx(1 + 4 + 2 + 1)
        # h-bar mass lands in the horizontal pool
        assert demand[:, :, 1].sum() > demand[:, :, 0].sum()

    def test_clique_extents_emerge_when_spread_is_enforced(self):
        # Physics note (first version of this test got it wrong): absent
        # capacity repulsion a clique COLLAPSES to a point (deficits -> 0, no
        # extents needed). Bars emerge from contact demand only when
        # something keeps variables apart -- in the real pipeline, the
        # Poisson field. Pin positions (eta=0) to isolate that mechanism.
        rng_pos = {v: np.array([float(v % 3) * 2.0, float(v // 3) * 2.0])
                   for v in range(8)}
        k8 = {v: [u for u in range(8) if u != v] for v in range(8)}
        path = {v: [u for u in (v - 1, v + 1) if 0 <= u < 8] for v in range(8)}
        ek = {v: np.zeros(2) for v in range(8)}
        ep = {v: np.zeros(2) for v in range(8)}
        pk, pp = dict(rng_pos), dict(rng_pos)
        for _ in range(60):
            pk, ek = contact_step(pk, ek, k8, eta=0.0, extent_eta=0.3,
                                  extent_cost=0.05)
            pp, ep = contact_step(pp, ep, path, eta=0.0, extent_eta=0.3,
                                  extent_cost=0.05)
        mean_k = np.mean([ek[v].sum() for v in ek])
        mean_p = np.mean([ep[v].sum() for v in ep])
        assert mean_k > mean_p  # spread clique demands more extent than path
        assert mean_k > 1.0     # bars genuinely grew

    def test_fit_extents_recovers_l_shape(self):
        g = dnx.chimera_graph(8, 8, 4)
        grid = TileGrid(g, target_layout(g))
        pos = target_layout(g)
        # build an L: qubits spanning tiles (0..4, row 2) and (col 4, rows 2..5)
        conv_pick = []
        import dwave_networkx as dnx2
        conv = dnx2.chimera_coordinates(8, 8, 4)
        for j in range(5):
            conv_pick.append(conv.chimera_to_linear((2, j, 1, 0)))
        for i in range(2, 6):
            conv_pick.append(conv.chimera_to_linear((i, 4, 0, 0)))
        fits = fit_extents(grid, {7: conv_pick}, pos)
        assert fits[7][0] == pytest.approx(4.0, abs=0.5)   # w spans 4 tiles
        assert fits[7][1] == pytest.approx(3.0, abs=0.5)   # h spans 3 tiles

    def test_bar_seeds_distinct_and_orientation_matched(self):
        g = dnx.chimera_graph(8, 8, 4)
        grid = TileGrid(g, target_layout(g))
        pos = self._pts({0: [4.0, 4.0], 1: [3.0, 3.0]})
        ext = self._pts({0: [4.0, 4.0], 1: [3.0, 0.0]})
        seeds = bar_seeds(grid, pos, ext)
        allq = [q for c in seeds.values() for q in c]
        assert len(allq) == len(set(allq))       # no qubit claimed twice
        assert len(seeds[0]) >= 5                 # center + bar samples
        # h-bar samples (beyond center) are horizontal qubits where typed
        qmap = {q: grid.orient[i] for i, q in enumerate(grid.qubits)}
        hsamples = seeds[1][1:]
        assert all(qmap[q] == 1 for q in hsamples)


from ember_qc.algorithms.factored.field import assign_rows_cols, bar_force


class TestV2FieldCoupling:
    def _grid(self, B=10):
        g = nx.convert_node_labels_to_integers(nx.grid_2d_graph(B, B))
        grid = TileGrid(g, nx.spectral_layout(g), fallback_bins=B)
        return grid

    def test_zero_field_zero_forces(self):
        grid = self._grid()
        psi = np.zeros((grid.H, grid.W))
        pos = {0: np.array([5.0, 5.0])}
        ext = {0: np.array([4.0, 2.0])}
        dpos, dext = bar_force(grid, psi, pos, ext, scale=1.0, ext_w=1.0)
        assert np.allclose(dpos[0], 0) and np.allclose(dext[0], 0)

    def test_tip_in_ridge_retracts(self):
        grid = self._grid()
        psi = np.zeros((grid.H, grid.W))
        psi[:, 8] = 5.0  # high-potential column ridge at x=8
        pos = {0: np.array([5.0, 5.0])}
        ext = {0: np.array([6.0, 0.0])}  # h-bar spans x in [2, 8]: tip in ridge
        _, dext = bar_force(grid, psi, pos, ext, scale=0.0, ext_w=1.0)
        assert dext[0][0] < 0          # h-bar retracts
        assert abs(dext[0][1]) < 0.5   # v-bar (tips at psi~0 row band) ~free

    def test_far_tip_translation(self):
        # Max's scenario: oversubscription overlapping only the far tip must
        # produce net translation away -- center sampling gives ~zero.
        grid = self._grid()
        psi = np.zeros((grid.H, grid.W))
        psi[:, 8] = 5.0
        pos = {0: np.array([4.0, 5.0])}
        ext = {0: np.array([8.0, 0.0])}  # bar spans [0, 8]; center at 4
        dpos, _ = bar_force(grid, psi, pos, ext, scale=1.0, ext_w=0.0)
        assert dpos[0][0] < -1e-6      # pushed away from the ridge (negative x)

    def test_assignment_unstacks_preserving_order(self):
        grid = self._grid(8)
        grid.cap[:, :, :] = 1.0
        pos = {v: np.array([4.0, 4.0 + 0.01 * v]) for v in range(5)}
        ext = {v: np.array([4.0, 4.0]) for v in range(5)}
        new, n = assign_rows_cols(pos, ext, grid, threshold=2.0)
        assert n == 5
        rows = [float(new[v][1]) for v in range(5)]
        assert len(set(rows)) == 5                    # distinct rows
        assert rows == sorted(rows)                   # y-order preserved
        assert max(abs(r - 4.0) for r in rows) <= 4   # bounded displacement

    def test_assignment_ignores_points(self):
        grid = self._grid(8)
        pos = {0: np.array([3.3, 3.7]), 1: np.array([3.4, 3.6])}
        ext = {0: np.zeros(2), 1: np.array([0.5, 0.5])}
        new, n = assign_rows_cols(pos, ext, grid, threshold=2.0)
        assert n == 0
        assert np.allclose(new[0], pos[0]) and np.allclose(new[1], pos[1])

    def test_assignment_deterministic(self):
        grid = self._grid(8)
        grid.cap[:, :, :] = 1.0
        pos = {v: np.array([4.0 + 0.001 * v, 4.0]) for v in range(6)}
        ext = {v: np.array([3.0, 3.0]) for v in range(6)}
        a, _ = assign_rows_cols(pos, ext, grid)
        b, _ = assign_rows_cols(pos, ext, grid)
        assert all(np.allclose(a[v], b[v]) for v in a)


from ember_qc.algorithms.factored.field import (
    bar_force_iv, bar_widths, deposit_bars, derive_bars, span_energy,
    span_step, wire_seeds, wire_seeds_iv,
)


class TestSpanState:
    """Derived extents (notes s3.31): position is the only state; bars are
    the spans of closed neighbourhoods, energy = implied qubit mass."""

    def _grid(self, B=10):
        g = nx.convert_node_labels_to_integers(nx.grid_2d_graph(B, B))
        return TileGrid(g, nx.spectral_layout(g), fallback_bins=B)

    def test_sparse_limit_spans_stay_point_like(self):
        # path graph on consecutive integer tiles: interior closed nbhds span
        # exactly 2 along the axis and 0 across it; endpoints span 1
        pos = {v: np.array([float(v), 3.0]) for v in range(6)}
        adj = {v: [u for u in (v - 1, v + 1) if 0 <= u < 6] for v in range(6)}
        bars = derive_bars(pos, adj, floor=False)
        for v in range(1, 5):
            h_iv, v_iv = bars[v]
            assert h_iv[1] - h_iv[0] == pytest.approx(2.0)
            assert v_iv[1] - v_iv[0] == pytest.approx(0.0)
        assert span_energy(pos, adj) == pytest.approx(2.0 * 4 + 1.0 * 2)

    def test_clique_spans_equal_occupied_region(self):
        # K9 spread over a 4x4 block: every derived bar is exactly the
        # occupied region's bounding box (the crossbar readout)
        pos = {v: np.array([float(v % 3) * 2.0, float(v // 3) * 2.0])
               for v in range(9)}
        adj = {v: [u for u in range(9) if u != v] for v in range(9)}
        bars = derive_bars(pos, adj, floor=False)
        for v in range(9):
            h_iv, v_iv = bars[v]
            assert h_iv[0] == pytest.approx(0.0)
            assert h_iv[1] == pytest.approx(4.0)
            assert v_iv[0] == pytest.approx(0.0)
            assert v_iv[1] == pytest.approx(4.0)

    def test_deposit_bars_mass_and_pools(self):
        g = dnx.chimera_graph(8, 8, 4)
        grid = TileGrid(g, target_layout(g))
        pos = {0: np.array([4.0, 4.0]), 1: np.array([2.0, 2.0])}
        bars = {0: (np.array([2.0, 6.0]), np.array([3.0, 5.0])),  # w=4, h=2
                1: (np.array([2.0, 2.0]), np.array([2.0, 2.0]))}  # point
        demand = deposit_bars(grid, pos, bars)
        assert demand.sum() == pytest.approx(1 + 4 + 2 + 1)
        # h-bar mass lands in the horizontal pool
        assert demand[:, :, 1].sum() > demand[:, :, 0].sum()

    def test_subgradient_moves_only_extremes(self):
        # path 0-1-2 at x = 0, 2, 4: the HPWL subgradient pulls only the
        # extreme members of each net; the middle vertex's forces cancel
        pos = {0: np.array([0.0, 0.0]), 1: np.array([2.0, 0.0]),
               2: np.array([4.0, 0.0])}
        adj = {0: [1], 1: [0, 2], 2: [1]}
        e0 = span_energy(pos, adj)
        new = span_step(pos, adj, eta=0.5)
        assert np.allclose(new[1], pos[1])          # interior: zero net force
        assert new[0][0] > 0.0 and new[2][0] < 4.0  # extremes move inward
        assert new[0][1] == pytest.approx(0.0)      # no off-axis motion
        assert span_energy(new, adj) < e0
        again = span_step(pos, adj, eta=0.5)
        assert all(np.allclose(new[v], again[v]) for v in pos)  # deterministic

    def test_kappa_floor(self):
        # coincident star: raw spans are 0; the contact-capacity floor forces
        # the hub's total bar length to deg/kappa - 1, leaves stay points
        pos = {v: np.array([5.0, 5.0]) for v in range(27)}
        adj = {0: list(range(1, 27))}
        adj.update({v: [0] for v in range(1, 27)})
        bars = derive_bars(pos, adj, kappa=13.0, floor=True)
        w, h = bar_widths(bars)[0]
        assert w + h == pytest.approx(26 / 13.0 - 1.0)
        lw, lh = bar_widths(bars)[1]
        assert lw + lh == pytest.approx(0.0)

    def test_assignment_rederive_idempotent(self):
        # derive -> assign -> re-derive -> assign must be a no-op: extents
        # are a readout of positions, so the post-assignment state is
        # self-consistent (the v2 assignment-vs-attraction fight is dead)
        grid = self._grid()
        grid.cap[:, :, :] = 1.0
        pos = {v: np.array([4.0 + 0.6 * v, 4.0 + 0.6 * v]) for v in range(5)}
        adj = {v: [u for u in range(5) if u != v] for v in range(5)}
        bars = derive_bars(pos, adj, floor=False)
        p1, n1 = assign_rows_cols(pos, bar_widths(bars), grid, threshold=2.0)
        assert n1 == 5
        bars1 = derive_bars(p1, adj, floor=False)
        p2, n2 = assign_rows_cols(p1, bar_widths(bars1), grid, threshold=2.0)
        assert n2 == 5
        assert all(np.allclose(p1[v], p2[v]) for v in p1)

    def test_bar_force_iv_one_sided(self):
        # a one-sided h-interval reaching into a high-psi ridge is pushed
        # away even though the owner's position sits far from the ridge
        grid = self._grid()
        psi = np.zeros((grid.H, grid.W))
        psi[:, 8] = 5.0
        pos = {0: np.array([4.0, 5.0])}
        bars = {0: (np.array([4.0, 8.0]), np.array([5.0, 5.0]))}
        d = bar_force_iv(grid, psi, pos, bars, scale=1.0)
        assert d[0][0] < -1e-6
        d0 = bar_force_iv(grid, np.zeros((grid.H, grid.W)), pos, bars,
                          scale=1.0)
        assert np.allclose(d0[0], 0.0)


class TestWireSeeds:
    def _chimera_grid(self):
        g = dnx.chimera_graph(8, 8, 4)
        return g, TileGrid(g, target_layout(g))

    def test_overlapping_bars_get_disjoint_contiguous_runs(self):
        g, grid = self._chimera_grid()
        pos = {0: np.array([4.0, 2.0]), 1: np.array([3.0, 2.0]),
               2: np.array([7.0, 7.0])}
        ext = {0: np.array([4.0, 0.0]), 1: np.array([4.0, 0.0]),
               2: np.array([0.0, 0.0])}
        seeds = wire_seeds(grid, pos, ext)
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


from ember_qc.algorithms.factored.field import (
    _couples, alternate_arrange, bar_domains, line_depth, slack_relax,
)


class TestProductMode:
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

    def test_coupled_coloring_prefers_couplable(self):
        g = dnx.pegasus_graph(4)
        grid = TileGrid(g, target_layout(g))
        # u=0: h-bar on row 1 over cols [0,2]; v=1: v-bar on col 1 over
        # rows [0,2]; single edge (0,1). Their only possible coupler is at
        # the crossing tile (1,1) between the two chosen wires.
        pos = {0: np.array([0.0, 1.0]), 1: np.array([1.0, 1.0])}
        bars = {0: (np.array([0.0, 2.0]), np.array([1.0, 1.0])),
                1: (np.array([1.0, 1.0]), np.array([0.0, 2.0]))}
        adj = {0: [1], 1: [0]}
        # phase 1 gives u the first free h-sub; check a couplable v-sub
        # exists for it at all (else the instance can't test the mechanism)
        hsubs = sorted({s for (u, ln, s) in grid.wire_map
                        if u == 1 and ln == 1})
        vsubs = sorted({s for (u, ln, s) in grid.wire_map
                        if u == 0 and ln == 1})
        assert any(_couples(grid, 1, hsubs[0], 1, s2) for s2 in vsubs)
        cpl = wire_seeds_iv(grid, pos, bars, src_adj=adj)
        assert any(g.has_edge(a, b) for a in cpl[0] for b in cpl[1])
        again = wire_seeds_iv(grid, pos, bars, src_adj=adj)
        assert cpl == again  # deterministic

    def test_stride_claims_alternate_tiles(self):
        g = dnx.chimera_graph(8, 8, 4)
        grid = TileGrid(g, target_layout(g))
        pos = {0: np.array([2.0, 5.0])}
        bars = {0: (np.array([2.0, 7.0]), np.array([5.0, 5.0]))}
        s1 = wire_seeds_iv(grid, pos, bars, stride=1)
        s2 = wire_seeds_iv(grid, pos, bars, stride=2)
        conv = dnx.chimera_coordinates(8, 8, 4)
        js1 = sorted(j for (_, j, _, _) in
                     (conv.linear_to_chimera(q) for q in s1[0]))
        js2 = sorted(j for (_, j, _, _) in
                     (conv.linear_to_chimera(q) for q in s2[0]))
        assert js2 == js1[::2]  # every other tile, same wire

    def test_slack_relax_line_invariant(self):
        pos = {v: np.array([float(v), 3.0]) for v in range(6)}
        adj = {v: [u for u in (v - 1, v + 1) if 0 <= u < 6] for v in range(6)}
        out = slack_relax(pos, adj, eta=0.4, steps=3)
        for v in pos:
            assert np.all(np.round(out[v]) == np.round(pos[v]))  # same lines
        assert any(not np.allclose(out[v], pos[v]) for v in pos)  # but moved
        again = slack_relax(pos, adj, eta=0.4, steps=3)
        assert all(np.allclose(out[v], again[v]) for v in pos)

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
