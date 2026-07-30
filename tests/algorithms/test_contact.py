"""
tests/algorithms/test_contact.py
=================================
Tests for the contact model (ember_qc.algorithms.factored.contact),
derived from the notes s3.45(a) model text, not from the implementation.
"""
import networkx as nx
import numpy as np
import pytest
import dwave_networkx as dnx

from ember_qc.algorithms.factored.contact import (
    ContactState,
    contact_energy,
    contact_forces,
    contact_place,
    contact_seeds,
    junction_caps,
)
from ember_qc.algorithms.factored.field import TileGrid
from ember_qc.algorithms.factored.placement import target_layout


def _untyped_grid(B=12, jcap=2.0):
    g = nx.convert_node_labels_to_integers(nx.grid_2d_graph(B, B))
    grid = TileGrid(g, nx.spectral_layout(g), fallback_bins=B)
    return grid


class TestJunctionCaps:
    def test_zephyr_counts_and_sum(self):
        g = dnx.zephyr_graph(3, 4)
        grid = TileGrid(g, target_layout(g))
        J, couplers = junction_caps(grid)
        n_cross = sum(len(v) for v in couplers.values())
        assert J.sum() == n_cross
        # every counted pair is a real cross-orientation coupler
        for pool in list(couplers.values())[:20]:
            for qh, qv in pool:
                assert g.has_edge(qh, qv)
        assert n_cross > 500  # Zephyr junctions are plentiful

    def test_chimera_counts(self):
        g = dnx.chimera_graph(4, 4, 4)
        grid = TileGrid(g, target_layout(g))
        J, _ = junction_caps(grid)
        # each clean chimera tile has 4x4 = 16 in-tile cross couplers
        assert np.all(J == 16.0)


class TestContactForces:
    def _cfg(self, seed=5, n=8, B=12):
        rng = np.random.default_rng(seed)
        src = nx.gnp_random_graph(n, 0.6, seed=3)
        grid = _untyped_grid(B)
        state = ContactState(src, grid)
        state.J = np.full((B, B), 0.4)  # tiny caps -> overloaded regime
        state.cs = 0.4
        m = state.m
        X = 0.71 + (B - 2.4) * rng.random(m)
        Y = 0.73 + (B - 2.4) * rng.random(m)
        return state, X, Y

    def test_finite_difference_gradient(self):
        # THE gate: implemented forces == -grad(E) numerically, every
        # coordinate, random configs away from kinks
        for seed in (5, 11, 23):
            state, X, Y = self._cfg(seed=seed)
            lam = 0.7
            fx, fy = contact_forces(state, X, Y, lam)
            h = 1e-5
            for i in range(state.m):
                for arr, f in ((X, fx), (Y, fy)):
                    a = arr.copy(); a[i] += h
                    b = arr.copy(); b[i] -= h
                    if arr is X:
                        ep = contact_energy(state, a, Y, lam)
                        em = contact_energy(state, b, Y, lam)
                    else:
                        ep = contact_energy(state, X, a, lam)
                        em = contact_energy(state, X, b, lam)
                    grad = (ep - em) / (2 * h)
                    assert f[i] == pytest.approx(-grad, rel=1e-3,
                                                 abs=1e-3), (seed, i)

    def test_gas_inertness(self):
        # slack junction caps: pressure contributes nothing; only net
        # pulls remain, and an isolated single-edge net feels none
        src = nx.Graph()
        src.add_edge(0, 1)
        grid = _untyped_grid()
        state = ContactState(src, grid)
        state.J = np.full((12, 12), 10.0)
        X = np.array([5.3])
        Y = np.array([6.7])
        fx, fy = contact_forces(state, X, Y, 1.0)
        # one contact: it is every net's min AND max -> pulls cancel
        assert abs(fx[0]) < 1e-12 and abs(fy[0]) < 1e-12

    def test_density_separates_stacked_contacts(self):
        # many contacts stacked on one tile beyond its junction cap feel
        # diverging pressure forces
        src = nx.complete_graph(6)  # 15 edges
        grid = _untyped_grid()
        state = ContactState(src, grid)
        state.J = np.full((12, 12), 1.0)
        X = np.full(state.m, 6.2)
        Y = np.full(state.m, 6.2)
        fx, fy = contact_forces(state, X, Y, 5.0)
        assert float(np.abs(fx).max() + np.abs(fy).max()) > 0.1


class TestContactPlace:
    def test_k6_triangle_miniature(self):
        # crystal emergence without any rule: K6's 15 contacts settle
        # dense-but-feasible, and total hpwl stays within a small factor
        # of the packed-seating estimate
        src = nx.complete_graph(6)
        g = dnx.zephyr_graph(3, 4)
        grid = TileGrid(g, target_layout(g))
        contacts, info = contact_place(src, grid, steps=150, cycles=3)
        assert info["residual_overload"] <= 0.5
        # packed-seating estimate: 15 seats at Zephyr junction density
        # occupy ~1 tile; nets of 5 contacts each -> hpwl ~ few tiles
        assert info["final_hpwl"] <= 40.0
        again, _ = contact_place(src, grid, steps=150, cycles=3)
        assert np.allclose(contacts, again)

    def test_seeds_connected_disjoint_covering(self):
        # the Stage-2 readout contract: chains connected, pairwise
        # disjoint, deterministic; every edge whose two seats survived is
        # covered by real adjacency
        src = nx.complete_graph(6)
        g = dnx.zephyr_graph(3, 4)
        grid = TileGrid(g, target_layout(g))
        J, couplers = junction_caps(grid)
        contacts, _ = contact_place(src, grid, steps=100, cycles=2)
        seeds, rinfo = contact_seeds(src, grid, contacts, couplers)
        allq = [q for c in seeds.values() for q in c]
        assert len(allq) == len(set(allq))     # disjoint
        assert set(seeds) == set(src.nodes())  # everyone seeded
        for v, c in seeds.items():
            assert nx.is_connected(g.subgraph(c))  # CONNECTED chains
        covered = sum(
            1 for (u, v) in src.edges()
            if any(g.has_edge(a, b) for a in seeds[u] for b in seeds[v]))
        # K6 on Z3 places cleanly: nearly all edges seat-covered
        assert covered >= src.number_of_edges() - rinfo["dropped_seats"]
        again, _ = contact_seeds(src, grid, contacts, couplers)
        assert again == seeds  # deterministic

    def test_bipartite_pile_settles(self):
        # the turan failure in miniature: K6,6's cross-block contacts all
        # initialize at the midline (one pile). The s3.46 per-contact
        # preconditioning must spread it to a feasible seating (the
        # global-alpha build pinned on exactly this shape at scale).
        src = nx.complete_bipartite_graph(6, 6)
        g = dnx.zephyr_graph(3, 4)
        grid = TileGrid(g, target_layout(g))
        contacts, info = contact_place(src, grid, steps=200, cycles=3)
        assert info["residual_overload"] <= 0.5
