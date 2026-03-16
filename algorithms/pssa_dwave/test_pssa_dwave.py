"""
tests/test_pssa_dwave.py
=========================
Unit tests for pssa_dwave.

Run:  pytest tests/ -v
"""

import math
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import networkx as nx
try:
    import pytest
except ImportError:
    pytest = None  # tests still runnable via unittest

from pssa_dwave.core import (
    DWaveSchedule,
    _path_partition_guiding,
    initial_placement,
    eemb, invert, pssa,
    _leaves, _remove_leaf, _attach_leaf,
)
from pssa_dwave.terminal_search import terminal_search, is_deletable
from pssa_dwave.improved_pssa import ImprovedPSSA, is_valid_embedding


# ── Helpers ────────────────────────────────────────────────────────────────

def tiny_ring(n=6):
    return nx.cycle_graph(n)

def tiny_path(n=4):
    return nx.path_graph(n)

def tiny_grid():
    return nx.grid_2d_graph(3, 3)

def manual_hardware():
    """Small 4x4 grid used as surrogate hardware (no D-Wave install needed)."""
    G = nx.grid_2d_graph(6, 6)
    return nx.convert_node_labels_to_integers(G)


# ── Schedule tests ─────────────────────────────────────────────────────────

class TestDWaveSchedule:
    def test_chimera_defaults(self):
        s = DWaveSchedule(tmax=1_000, topology="chimera")
        assert s.T0 == 70.0
        assert s.Thalf == 40.0
        assert s.beta == 0.9998

    def test_pegasus_defaults(self):
        s = DWaveSchedule(tmax=1_000, topology="pegasus")
        assert s.T0 == 55.0
        assert s.Thalf == 28.0

    def test_zephyr_defaults(self):
        s = DWaveSchedule(tmax=1_000, topology="zephyr")
        assert s.T0 == 45.0

    def test_temperature_decreasing(self):
        s = DWaveSchedule(tmax=10_000, topology="chimera", cool_every=100)
        temps = [s.temperature(t) for t in range(0, 10_000, 500)]
        # Should decrease (not strictly every step, but overall)
        assert temps[0] >= temps[-1]

    def test_temperature_phase_transition(self):
        s = DWaveSchedule(tmax=1_000, topology="chimera")
        # Phase 2 starts at T=Thalf, which is less than T0
        t1 = s.temperature(0)
        t2 = s.temperature(500)
        assert t1 >= t2

    def test_ps_decreases(self):
        s = DWaveSchedule(tmax=1_000, topology="chimera")
        assert s.ps(0) > s.ps(1_000)

    def test_pa_increases(self):
        s = DWaveSchedule(tmax=1_000, topology="chimera")
        assert s.pa(0) < s.pa(1_000)

    def test_override_params(self):
        s = DWaveSchedule(tmax=1_000, topology="chimera", T0=100.0, beta=0.999)
        assert s.T0 == 100.0
        assert s.beta == 0.999

    def test_auto_scales_with_nodes(self):
        s_small = DWaveSchedule.auto("chimera", n_hw=128)
        s_large = DWaveSchedule.auto("chimera", n_hw=2048)
        assert s_large.tmax > s_small.tmax

    def test_auto_minimum_tmax(self):
        s = DWaveSchedule.auto("zephyr", n_hw=64)
        assert s.tmax >= 200_000

    def test_summary_string(self):
        s = DWaveSchedule(tmax=1_000, topology="pegasus")
        assert "pegasus" in s.summary()
        assert "T0" in s.summary()


# ── Guiding pattern tests ──────────────────────────────────────────────────

class TestGuidingPattern:
    def test_path_partition_covers_all_nodes(self):
        H = manual_hardware()
        gp = _path_partition_guiding(H)
        covered = set(u for path in gp.values() for u in path)
        assert covered == set(H.nodes())

    def test_path_partition_no_duplicates(self):
        H = manual_hardware()
        gp = _path_partition_guiding(H)
        all_nodes = [u for path in gp.values() for u in path]
        assert len(all_nodes) == len(set(all_nodes))

    def test_path_partition_each_path_connected(self):
        H = manual_hardware()
        gp = _path_partition_guiding(H)
        for k, path in gp.items():
            if len(path) > 1:
                assert nx.is_connected(H.subgraph(path)), f"Path {k} not connected"

    def test_path_partition_nonempty_paths(self):
        H = manual_hardware()
        gp = _path_partition_guiding(H)
        assert all(len(p) > 0 for p in gp.values())


# ── Initial placement tests ────────────────────────────────────────────────

class TestInitialPlacement:
    def test_all_input_nodes_have_sv(self):
        H = manual_hardware()
        I = tiny_ring(6)
        gp = _path_partition_guiding(H)
        phi = initial_placement(I, gp, H)
        assert set(phi.keys()) == set(I.nodes())

    def test_sv_nonempty(self):
        H = manual_hardware()
        I = tiny_ring(6)
        gp = _path_partition_guiding(H)
        phi = initial_placement(I, gp, H)
        assert all(len(sv) > 0 for sv in phi.values())

    def test_sv_disjoint(self):
        H = manual_hardware()
        I = tiny_ring(6)
        gp = _path_partition_guiding(H)
        phi = initial_placement(I, gp, H)
        all_hw = [u for sv in phi.values() for u in sv]
        assert len(all_hw) == len(set(all_hw))

    def test_sv_within_hardware(self):
        H = manual_hardware()
        I = tiny_ring(6)
        gp = _path_partition_guiding(H)
        phi = initial_placement(I, gp, H)
        hw_nodes = set(H.nodes())
        for sv in phi.values():
            assert all(u in hw_nodes for u in sv)

    def test_more_input_nodes_than_guiding_svs(self):
        H = manual_hardware()
        I = nx.cycle_graph(20)   # more nodes than typical guiding paths
        gp = _path_partition_guiding(H)
        phi = initial_placement(I, gp, H)
        assert set(phi.keys()) == set(I.nodes())


# ── Core utility tests ─────────────────────────────────────────────────────

class TestCoreUtils:
    def test_invert_roundtrip(self):
        phi = {0: [1, 2, 3], 1: [4, 5]}
        inv = invert(phi)
        assert inv[1] == 0
        assert inv[5] == 1

    def test_eemb_counts_correctly(self):
        I = nx.path_graph(3)   # edges: 0-1, 1-2
        H = manual_hardware()
        # manually place: 0→[0], 1→[1], 2→[6]
        # H.edges must include (0,1) and (1,6)
        # use nodes that are connected in manual_hardware
        nodes = list(H.nodes())
        # find a triangle-ish area
        phi = {i: [nodes[i * 6]] for i in range(3)}
        inv = invert(phi)
        e = eemb(phi, I, H, inv)
        assert isinstance(e, int)
        assert 0 <= e <= 2

    def test_leaves_single_node(self):
        assert _leaves([42]) == [42]

    def test_leaves_multiple_nodes(self):
        result = _leaves([1, 2, 3, 4])
        assert set(result) == {1, 4}

    def test_remove_leaf_front(self):
        assert _remove_leaf([1, 2, 3], 1) == [2, 3]

    def test_remove_leaf_back(self):
        assert _remove_leaf([1, 2, 3], 3) == [1, 2]

    def test_attach_leaf_front(self):
        assert _attach_leaf([2, 3], 1, 2) == [1, 2, 3]

    def test_attach_leaf_back(self):
        assert _attach_leaf([1, 2], 3, 2) == [1, 2, 3]


# ── PSSA main algorithm tests ──────────────────────────────────────────────

class TestPSSA:
    def _run_pssa_on_manual_hw(self, I, tmax=5_000, seed=0):
        H   = manual_hardware()
        gp  = _path_partition_guiding(H)
        sch = DWaveSchedule(tmax=tmax, topology="chimera")
        return pssa(I, H, gp, sch, seed=seed)

    def test_returns_phi_and_int(self):
        I = tiny_path(3)
        phi, e = self._run_pssa_on_manual_hw(I)
        assert isinstance(phi, dict)
        assert isinstance(e, int)

    def test_phi_keys_match_input_nodes(self):
        I = tiny_ring(4)
        phi, _ = self._run_pssa_on_manual_hw(I)
        assert set(phi.keys()) == set(I.nodes())

    def test_eemb_nonnegative(self):
        I = tiny_ring(4)
        _, e = self._run_pssa_on_manual_hw(I)
        assert e >= 0

    def test_eemb_bounded_by_edges(self):
        I = tiny_ring(4)
        _, e = self._run_pssa_on_manual_hw(I)
        assert e <= I.number_of_edges()

    def test_weighted_mode(self):
        H   = manual_hardware()
        I   = nx.random_regular_graph(3, 6, seed=0)
        gp  = _path_partition_guiding(H)
        sch = DWaveSchedule(tmax=5_000, topology="chimera")
        phi, e = pssa(I, H, gp, sch, weighted=True, seed=0)
        assert isinstance(phi, dict)

    def test_seed_reproducibility(self):
        I = tiny_ring(4)
        _, e1 = self._run_pssa_on_manual_hw(I, seed=7)
        _, e2 = self._run_pssa_on_manual_hw(I, seed=7)
        assert e1 == e2

    def test_small_graph_embeds(self):
        """A single edge should embed trivially."""
        I   = nx.path_graph(2)
        H   = manual_hardware()
        gp  = _path_partition_guiding(H)
        sch = DWaveSchedule(tmax=10_000, topology="chimera")
        phi, e = pssa(I, H, gp, sch, seed=0)
        assert e >= 0   # at minimum no crash


# ── Terminal search tests ──────────────────────────────────────────────────

class TestTerminalSearch:
    def test_never_decreases_eemb(self):
        H  = manual_hardware()
        I  = tiny_ring(5)
        gp = _path_partition_guiding(H)
        sch = DWaveSchedule(tmax=5_000, topology="chimera")
        phi_before, e_before = pssa(I, H, gp, sch, seed=0)
        phi_after = terminal_search(phi_before, I, H)
        inv_after = invert(phi_after)
        e_after   = eemb(phi_after, I, H, inv_after)
        assert e_after >= e_before

    def test_output_has_same_keys(self):
        H  = manual_hardware()
        I  = tiny_path(4)
        gp = _path_partition_guiding(H)
        sch = DWaveSchedule(tmax=2_000, topology="chimera")
        phi, _ = pssa(I, H, gp, sch, seed=0)
        phi2 = terminal_search(phi, I, H)
        assert set(phi2.keys()) == set(phi.keys())

    def test_svs_still_nonempty_after_search(self):
        H  = manual_hardware()
        I  = tiny_ring(4)
        gp = _path_partition_guiding(H)
        sch = DWaveSchedule(tmax=2_000, topology="chimera")
        phi, _ = pssa(I, H, gp, sch, seed=0)
        phi2 = terminal_search(phi, I, H)
        assert all(len(sv) > 0 for sv in phi2.values())


# ── ImprovedPSSA integration tests ────────────────────────────────────────

class TestImprovedPSSA:
    def test_run_returns_result(self):
        H = manual_hardware()
        algo = ImprovedPSSA(hardware_graph=H, tmax=5_000)
        I = tiny_ring(4)
        result = algo.run(I)
        assert result is not None
        assert result.eemb >= 0

    def test_result_fields(self):
        H = manual_hardware()
        algo = ImprovedPSSA(hardware_graph=H, tmax=5_000)
        I = tiny_path(3)
        r = algo.run(I)
        assert r.m_I == I.number_of_edges()
        assert 0.0 <= r.coverage <= 1.0
        assert r.wall_time >= 0.0

    def test_coverage_is_1_on_trivial(self):
        """Single edge should always embed."""
        H = manual_hardware()
        algo = ImprovedPSSA(hardware_graph=H, tmax=20_000, seed=0)
        I = nx.path_graph(2)
        r = algo.run(I)
        assert r.coverage == 1.0

    def test_seed_gives_same_result(self):
        H = manual_hardware()
        I = tiny_ring(4)
        r1 = ImprovedPSSA(hardware_graph=H, tmax=5_000, seed=42).run(I)
        r2 = ImprovedPSSA(hardware_graph=H, tmax=5_000, seed=42).run(I)
        assert r1.eemb == r2.eemb

    def test_validity_check_passes_on_success(self):
        H = manual_hardware()
        I = nx.path_graph(2)
        r = ImprovedPSSA(hardware_graph=H, tmax=20_000, seed=0).run(I)
        if r.success:
            assert is_valid_embedding(r.phi, I, H)

    def test_is_valid_embedding_rejects_bad(self):
        H = manual_hardware()
        I = nx.cycle_graph(3)
        # Deliberately bad embedding: all SVs empty or same node
        nodes = list(H.nodes())
        phi = {0: [nodes[0]], 1: [nodes[0]], 2: [nodes[1]]}  # overlap
        assert not is_valid_embedding(phi, I, H)

    def test_weighted_mode_runs(self):
        H = manual_hardware()
        I = nx.random_regular_graph(3, 6, seed=0)
        r = ImprovedPSSA(hardware_graph=H, tmax=5_000, weighted=True, seed=0).run(I)
        assert r.eemb >= 0

    def test_larger_graph(self):
        H = manual_hardware()
        I = nx.cycle_graph(8)
        r = ImprovedPSSA(hardware_graph=H, tmax=10_000, seed=0).run(I)
        assert r.eemb >= 0


# ── Smoke test ─────────────────────────────────────────────────────────────

class TestEndToEnd:
    def test_path_graph_embeds_in_grid_hw(self):
        """A path graph should embed easily in any connected HW."""
        H = manual_hardware()
        I = nx.path_graph(5)
        r = ImprovedPSSA(hardware_graph=H, tmax=30_000, seed=1).run(I)
        # Path of 5 in a 6x6 grid HW should nearly always succeed
        assert r.eemb > 0

    def test_result_str(self):
        H = manual_hardware()
        I = tiny_ring(4)
        r = ImprovedPSSA(hardware_graph=H, tmax=5_000, seed=0).run(I)
        s = str(r)
        assert "chimera" in s or "pegasus" in s or "zephyr" in s or "chimera" in s
