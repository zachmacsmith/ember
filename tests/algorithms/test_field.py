"""
tests/algorithms/test_field.py
================================
Tests for the coarse layer (ember_qc.algorithms.factored.field),
post-consolidation-2 (2026-08-03, one code path): typed tile capacities, the
stair (single-coverage) readout and its subgradient dynamics, the alternating
1-D arrangement with insertion order-search and feasibility-priced gates,
wire-coherent seed derivation (snap-aimed greedy coloring), the exactness
completion, and the parked ``bar_domains`` handoff.
"""
import networkx as nx
import numpy as np
import pytest
import dwave_networkx as dnx

from ember_qc.algorithms.factored.field import (
    TileGrid,
    _color_claim_bars,
    claim_overload,
    complete_seeds,
    _stair_contacts,
    _target_kappa,
    alternate_arrange,
    bar_domains,
    bar_widths,
    derive_bars_stair,
    edge_monotonize,
    insertion_sweeps,
    line_depth,
    stair_energy,
    stair_step,
    wire_seeds_iv,
)
from ember_qc.algorithms.factored.placement import target_layout


def make_grid(target):
    return TileGrid(target, target_layout(target))


def couples(grid, r, s_h, c, s_v):
    """Test-local coupler check: does the h-wire (row r, sub s_h) share a
    physical coupler with the v-wire (col c, sub s_v) at their crossing?
    Re-states the parity rule that ``complete_seeds`` implements inline
    (a course-j bar crossing line c sits at p = c if parities match, else
    c - 1), so the fabric facts it verified stay verified after the
    wire-matching machinery was deleted at consolidation 2."""
    if grid.stride == 2:
        ph = c if c % 2 == s_h % 2 else c - 1
        pv = r if r % 2 == s_v % 2 else r - 1
        qh = grid.wire_map.get((1, r, s_h), {}).get(ph)
        qv = grid.wire_map.get((0, c, s_v), {}).get(pv)
    else:
        qh = grid.wire_map.get((1, r, s_h), {}).get(c)
        qv = grid.wire_map.get((0, c, s_v), {}).get(r)
    return qh is not None and qv is not None and grid.graph.has_edge(qh, qv)


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

    def test_pack_lines_matches_brute_force(self):
        # the s3.59 DP must be exactly optimal over non-decreasing
        # complete assignments whenever no skip is needed
        import itertools
        from ember_qc.algorithms.factored.field import pack_lines
        rng = np.random.RandomState(7)
        for trial in range(30):
            n = rng.randint(2, 7)
            L = rng.randint(2, 5)
            ivs = []
            for _ in range(n):
                a = rng.uniform(0, 6)
                ivs.append((a, a + rng.uniform(0.5, 4)))
            ys = sorted(rng.uniform(0, L - 1) for _ in range(n))
            pools = [float(rng.randint(1, 4)) for _ in range(L)]
            best = None
            for comb in itertools.combinations_with_replacement(
                    range(L), n):
                by_line = {}
                for k, l in enumerate(comb):
                    by_line.setdefault(l, []).append(ivs[k])
                if any(line_depth(v) > pools[l]
                       for l, v in by_line.items()):
                    continue
                cost = sum(abs(ys[k] - comb[k]) for k in range(n))
                if best is None or cost < best - 1e-12:
                    best = cost
            assign, cost = pack_lines(ivs, ys, pools)
            if best is None:
                assert any(a is None for a in assign)
            else:
                assert all(a is not None for a in assign), (trial, assign)
                assert cost == pytest.approx(best, abs=1e-9), trial
                # order preservation: non-decreasing lines
                placed = [a for a in assign if a is not None]
                assert placed == sorted(placed)
                # capacity respected
                by_line = {}
                for k, l in enumerate(assign):
                    by_line.setdefault(l, []).append(ivs[k])
                assert all(line_depth(v) <= pools[l]
                           for l, v in by_line.items())

    def test_pack_lines_skips_only_when_infeasible(self):
        from ember_qc.algorithms.factored.field import pack_lines
        # 5 mutually overlapping intervals, two lines of pool 2:
        # exactly one must be skipped
        ivs = [(0.0, 10.0)] * 5
        ys = [0.0, 0.2, 0.4, 0.6, 0.8]
        assign, _ = pack_lines(ivs, ys, [2.0, 2.0])
        assert sum(1 for a in assign if a is None) == 1
        placed = [a for a in assign if a is not None]
        assert placed == sorted(placed)
        assert all(placed.count(l) <= 2 for l in set(placed))

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


class TestCompleteSeeds:
    """s3.54 exactness completion: coverage by interval arithmetic on
    junction-complete fabrics."""

    def _setup(self, m=3):
        g = dnx.zephyr_graph(m, 4)
        grid = TileGrid(g, target_layout(g), courses=True)
        adj = {q: set(g[q]) for q in g.nodes()}
        return g, grid, adj

    def _run_qubits(self, grid, key, ps):
        run = grid.wire_map[key]
        return [run[p] for p in ps if p in run]

    def test_edge_extension_creates_coupler(self):
        g, grid, adj = self._setup()
        # h-run on row 2 far from a v-run on column 5: no coupler
        ch_a = self._run_qubits(grid, (1, 2, 0), [0, 2])
        ch_b = self._run_qubits(grid, (0, 5, 0), [0, 2])
        chains = {0: list(ch_a), 1: list(ch_b)}
        sa, sb = set(ch_a), set(ch_b)
        assert not any(nb in sb for q in ch_a for nb in adj[q])
        out, info = complete_seeds(grid, chains, {0: [1], 1: [0]}, adj)
        assert info["deficit_edges"] == 0
        oa, ob = set(out[0]), set(out[1])
        assert any(nb in ob for q in oa for nb in adj[q])  # real coupler
        assert not (oa & ob)                               # disjoint
        assert info["extensions"] >= 1 and info["ext_qubits"] >= 1

    def test_corner_pass_connects_l_chain(self):
        g, grid, adj = self._setup()
        # one variable with disjoint h- and v-runs
        ch = (self._run_qubits(grid, (1, 2, 0), [0]) +
              self._run_qubits(grid, (0, 5, 1), [5]))
        out, info = complete_seeds(grid, {0: ch}, {0: []}, adj)
        assert info["corner_deficit"] == 0
        import networkx as nx2
        assert nx2.is_connected(g.subgraph(out[0]))

    def test_bridge_pass_parallel_runs(self):
        g, grid, adj = self._setup()
        # two h-runs on adjacent rows: parallel-only, needs a bridge
        ch_a = self._run_qubits(grid, (1, 3, 0), [2])
        ch_b = self._run_qubits(grid, (1, 4, 0), [2])
        out, info = complete_seeds(grid, {0: ch_a, 1: ch_b},
                                   {0: [1], 1: [0]}, adj)
        assert info["deficit_edges"] == 0
        assert info["bridges"] >= 1
        oa, ob = set(out[0]), set(out[1])
        assert any(nb in ob for q in oa for nb in adj[q])
        assert not (oa & ob)

    def test_deterministic_and_input_untouched(self):
        g, grid, adj = self._setup()
        ch = {0: self._run_qubits(grid, (1, 2, 0), [0, 2]),
              1: self._run_qubits(grid, (0, 5, 0), [0, 2])}
        snapshot = {v: list(c) for v, c in ch.items()}
        a, ia = complete_seeds(grid, ch, {0: [1], 1: [0]}, adj)
        b, ib = complete_seeds(grid, ch, {0: [1], 1: [0]}, adj)
        assert a == b and ia == ib
        assert ch == snapshot  # input not mutated


class TestClaimOverload:
    """s3.57: the gate-energy hinge is the claim layer's own
    uncolorability census, squared."""

    def _grid(self, m=3):
        g = dnx.zephyr_graph(m, 4)
        return TileGrid(g, target_layout(g), courses=True)

    def test_feasible_zero_overdeep_hinge(self):
        grid = self._grid()
        # 9 variables, all long h-arms on the SAME row line (8 sub-lanes)
        n = 9
        adj = {v: [] for v in range(n)}
        pos = {v: np.array([3.0, 3.0]) for v in range(n)}
        import ember_qc.algorithms.factored.field as F
        bars9 = {v: (np.array([1.0, 5.0]), np.array([3.0, 3.0]))
                 for v in range(n)}
        orig = F.derive_bars_stair
        F.derive_bars_stair = lambda *a, **k: bars9
        try:
            over = claim_overload(pos, adj, grid, kappa=3.0)
        finally:
            F.derive_bars_stair = orig
        assert over == 1.0  # depth 9 vs 8 -> hinge 1^2
        # drop one variable: feasible, hinge 0
        pos8 = {v: pos[v] for v in range(8)}
        bars8 = {v: bars9[v] for v in range(8)}
        F.derive_bars_stair = lambda *a, **k: bars8
        try:
            assert claim_overload(pos8, adj, grid, kappa=3.0) == 0.0
        finally:
            F.derive_bars_stair = orig

    def test_arrange_lam_zero_byte_identical(self):
        grid = self._grid()
        n = 12
        adj = {v: [u for u in range(n) if u != v] for v in range(n)}
        pos = {v: np.array([2.0 + 0.3 * v, 2.0 + 0.3 * v])
               for v in range(n)}
        a, _ = alternate_arrange(dict(pos), adj, grid, iters=4, kappa=3.0)
        b, _ = alternate_arrange(dict(pos), adj, grid, iters=4, kappa=3.0,
                                 overload_lam=0.0)
        assert all(np.array_equal(a[v], b[v]) for v in a)
        # lam > 0 runs and returns a full arrangement
        c, ic = alternate_arrange(dict(pos), adj, grid, iters=4,
                                  kappa=3.0, overload_lam=1.0)
        assert set(c) == set(pos) and ic["E"]


class TestSnapClaims:
    """s3.56 claim-time crossing alignment: aim, don't repair."""

    def _setup(self, m=3):
        g = dnx.zephyr_graph(m, 4)
        grid = TileGrid(g, target_layout(g), courses=True)
        adj = {q: set(g[q]) for q in g.nodes()}
        return g, grid, adj

    def test_snap_covers_offset_crossing(self):
        g, grid, adj = self._setup()
        # 0's h-arm interval stops short of 1's column; snap must claim
        # the parity-exact bar anyway
        pos = {0: np.array([1.0, 2.0]), 1: np.array([4.0, 4.0])}
        bars = {0: (np.array([0.0, 1.4]), np.array([2.0, 2.0])),
                1: (np.array([4.0, 4.0]), np.array([1.0, 4.0]))}
        legacy = wire_seeds_iv(grid, pos, bars)
        snapped = wire_seeds_iv(grid, pos, bars,
                                src_adj={0: [1], 1: [0]})
        def touch(seeds):
            sa, sb = set(seeds.get(0, [])), set(seeds.get(1, []))
            return any(nb in sb for q in sa for nb in adj[q])
        assert not touch(legacy)   # the misalignment
        assert touch(snapped)      # aimed at claim time
        # snapped seeds disjoint
        allq = [q for c in snapped.values() for q in c]
        assert len(allq) == len(set(allq))

    def test_none_and_stride1_byte_identical(self):
        g, grid, adj = self._setup()
        n = 8
        adjs = {v: [u for u in range(n) if u != v] for v in range(n)}
        pos = {v: np.array([2.0 + 0.4 * v, 2.0 + 0.4 * v])
               for v in range(n)}
        bars = derive_bars_stair(pos, adjs, kappa=3.0,
                                 bounds=(grid.W, grid.H))
        a = wire_seeds_iv(grid, pos, bars)
        b = wire_seeds_iv(grid, pos, bars, src_adj=None)
        assert a == b
        # stride-1 grid: src_adj ignored entirely
        folded = TileGrid(g, target_layout(g))
        c = wire_seeds_iv(folded, pos, bars)
        d = wire_seeds_iv(folded, pos, bars, src_adj=adjs)
        assert c == d


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
                            hits += couples(gr, r, sh, c, sv)
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


class TestZephyrCourses:
    """Course-resolved Zephyr wires (s3.49, fabrics s4.5): sub = 2k+j,
    stride-2 same-course runs — the representation the constructive
    templates use. Default (courses=False) must be byte-identical to the
    recorded folded arm; stride-1 fabrics must be unaffected either way."""

    def _grids(self, m=3, t=4):
        g = dnx.zephyr_graph(m, t)
        pos = target_layout(g)
        return g, TileGrid(g, pos), TileGrid(g, pos, courses=True)

    def test_course_subs_stride_and_coupling(self):
        g, folded, course = self._grids()
        assert folded.stride == 1 and course.stride == 2
        assert course.cap.sum() == g.number_of_nodes()
        # geometry identical between representations
        assert course.W == folded.W and course.H == folded.H
        assert np.array_equal(course.cap, folded.cap)
        lines = {}
        for (u, ln, s), run in course.wire_map.items():
            lines.setdefault((u, ln), set()).add(s)
            ps = sorted(run)
            # every run is one course: keys share the sub's j-parity...
            assert all(p % 2 == s % 2 for p in ps), (u, ln, s)
            # ...and consecutive bars are coupled (external couplers)
            for p1, p2 in zip(ps, ps[1:]):
                assert p2 == p1 + 2
                assert g.has_edge(run[p1], run[p2]), (u, ln, s, p1)
        # 8 sub-lanes per line (4 tracks x 2 courses)
        assert all(s == set(range(8)) for s in lines.values())

    def test_stride1_fabrics_invariant(self):
        # the cheap P16/C16 guard: courses is a structural no-op off Zephyr
        for g in (dnx.pegasus_graph(4), dnx.chimera_graph(4)):
            pos = target_layout(g)
            a, b = TileGrid(g, pos), TileGrid(g, pos, courses=True)
            assert b.stride == 1
            assert a.wire_map == b.wire_map
            assert np.array_equal(a.sub, b.sub)
            assert np.array_equal(a.cap, b.cap)
            assert _target_kappa(a) == _target_kappa(b)

    def test_course_couples_junction_complete(self):
        # interior junction: all 8x8 (s_h, s_v) pairs couple — Zephyr's
        # K_{8,8} completeness through the parity lookup (fabrics s4.2)
        g, folded, course = self._grids()
        r = c = 3
        for sh in range(8):
            for sv in range(8):
                assert couples(course, r, sh, c, sv), (sh, sv)

    def test_course_couples_boundary_no_raise(self):
        g, folded, course = self._grids(m=3)
        edge = 6  # line 2m: even-parity bars would sit at p = 2m (absent)
        for sh in range(8):
            res = couples(course, 3, sh, edge, 0)
            assert res in (True, False)
        assert couples(course, 3, 0, edge, 0) is False  # j=0 parity miss

    def test_course_kappa(self):
        g, folded, course = self._grids()
        kf, kc = _target_kappa(folded), _target_kappa(course)
        # course kappa is fresh contacts PER TILE of the claimable run
        # (cross-orientation degree / stride): Z3 ~6.9, Z12 ~7.7. It is
        # EXPECTED to be far below the folded degree-derived ~14.7 — the
        # folded value was the 2x arm under-provisioning of s3.49.
        assert 5.0 < kc < 8.5
        assert kc < kf

    def test_course_claim_capacity_doubles(self):
        # 8 mutually overlapping arms on one line: folded rep can claim
        # only 4 (one per track); course rep claims all 8 (one per course)
        g, folded, course = self._grids()
        bars = [(3, 0.0, 3.0, v) for v in range(8)]
        out = {}
        for name, grid in (("folded", folded), ("course", course)):
            claimed: set = set()
            chains = {v: [] for v in range(8)}
            _color_claim_bars(grid, claimed, chains, 1, bars)
            out[name] = sum(1 for c in chains.values() if c)
        assert out["folded"] == 4
        assert out["course"] == 8

    def test_line_pools_census(self):
        # s3.59 one-accounting: integer sub-lane pools from wire_map —
        # 8 per line on course-resolved Zephyr, 4 folded; the packer and
        # claim_overload share this census
        from ember_qc.algorithms.factored.field import line_pools
        g, folded, course = self._grids()
        lpc = line_pools(course)
        for o in (0, 1):
            for ln in range(course.H if o == 1 else course.W):
                assert lpc.get((o, ln), 0) == 8, (o, ln)
        lpf = line_pools(folded)
        assert all(v == 4 for v in lpf.values())

    def test_arrange_postpack_overload_zero(self):
        # the structural identity the DP buys: a fresh packing censuses
        # to zero overload (the d729 class is impossible by construction)
        g, folded, course = self._grids()
        n = 20
        adj = {v: [u for u in range(n) if u != v] for v in range(n)}
        pos = {v: np.array([2.0 + 0.15 * v, 2.0 + 0.15 * v])
               for v in range(n)}
        for _ in range(8):
            pos = stair_step(pos, adj, eta=0.5)
        new, info = alternate_arrange(pos, adj, course, iters=8,
                                      kappa=3.0, overload_lam=1.0)
        assert claim_overload(new, adj, course, kappa=3.0) == 0.0

    def test_boundary_half_pool_and_parity_coloring(self):
        # s3.61: stride-2 boundary lines pack at HALF pool (4), and the
        # parity-preferring lane choice steers claims onto lanes that can
        # couple boundary crossings (junction 0 = even-course only)
        from ember_qc.algorithms.factored.field import pack_lines
        g, folded, course = self._grids()
        # packer side: 5 mutually overlapping arms aimed at line 0 —
        # only 4 fit (half pool); the 5th must go to line 1
        ivs = [(0.0, 5.0)] * 5
        ys = [0.0] * 5
        pools = [4.0, 8.0, 8.0]
        assign, _ = pack_lines(ivs, ys, pools)
        assert all(a is not None for a in assign)
        assert sum(1 for a in assign if a == 0) <= 4
        # coloring side: a bar with a crossing at line 0 must take an
        # even-parity lane even when an odd lane is free first
        from ember_qc.algorithms.factored.field import _color_claim_bars
        claimed: set = set()
        chains = {0: []}
        bars = [(3, 0.0, 3.0, 0)]
        targets = {0: (0.0, 3.0, [0, 2])}  # crossing at junction 0
        _color_claim_bars(course, claimed, chains, 1, bars, targets)
        assert chains[0], "bar got no wire"
        # every claimed qubit's sub-lane must reach junction 0: p*=0 needs
        # even parity
        subs = {s for q in chains[0]
                for (o, ln, s), run in course.wire_map.items()
                if o == 1 and ln == 3 and q in run.values()}
        assert subs and all(s % 2 == 0 for s in subs), subs

    def test_course_wire_seeds_valid_connected(self):
        g, folded, course = self._grids()
        n = 12
        adj = {v: [u for u in range(n) if u != v] for v in range(n)}
        pos = {v: np.array([1.0 + 0.3 * v, 1.0 + 0.3 * v])
               for v in range(n)}
        pos = stair_step(pos, adj, eta=0.3)
        pos, _ = alternate_arrange(pos, adj, course, iters=8, kappa=3.0)
        bars = derive_bars_stair(pos, adj, bounds=(course.W, course.H))
        seeds = wire_seeds_iv(course, pos, bars)
        allq = [q for c in seeds.values() for q in c]
        assert len(allq) == len(set(allq))
        assert set(seeds) == set(range(n))
        import networkx as nx2
        for v, c in seeds.items():
            if len(c) > 1 and nx2.is_connected(g.subgraph(c)):
                break
        else:
            assert False, "no connected multi-qubit course run found"


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
