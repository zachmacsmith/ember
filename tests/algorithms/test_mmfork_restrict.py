"""
tests/algorithms/test_mmfork_restrict.py
=========================================
Regression tests for the fork's restrict_chains fixes (notes s3.60).
Stock 0.2.22 hung past its timeout (3/3 at scale) and segfaulted at
default chainlength_patience on non-trivial domains; the fork masks the
search by u's domain alone, bounds link_path's parent walk, domain-
filters shortening roots, probes the clock on failure paths, and clips
initial_chains to domains at ingest. Skipped when the fork is unbuilt.
"""
import time

import networkx as nx
import numpy as np
import pytest

from ember_qc.algorithms.minorminer_forked import _find_so, _load_fork

pytestmark = pytest.mark.skipif(_find_so() is None,
                                reason="mm fork not built")


@pytest.fixture(scope="module")
def p16_setup():
    import dwave_networkx as dnx
    from ember_qc.algorithms.factored.field import (
        TileGrid, pack_project, bar_domains, derive_bars_stair,
        stair_step, wire_seeds_iv)
    from ember_qc.algorithms.factored.placement import (
        target_layout, source_positions)
    tgt = dnx.pegasus_graph(16)
    grid = TileGrid(tgt, target_layout(tgt))
    edges = list(tgt.edges())

    def build(n, margin):
        src = nx.complete_graph(n)
        adj = {v: [u for u in range(n) if u != v] for v in range(n)}
        pos = target_layout(tgt)
        coords = np.array(list(pos.values()))
        cent = source_positions(src, coords.min(axis=0), coords.max(axis=0))
        tp = {v: grid.to_tile(p) for v, p in cent.items()}
        for _ in range(8):
            tp = stair_step(tp, adj, eta=0.5)
        tp, _ = pack_project(tp, adj, grid, kappa=13.0)
        bars = derive_bars_stair(tp, adj, kappa=13.0,
                                 bounds=(grid.W, grid.H))
        doms = bar_domains(grid, tp, bars, adj, kappa=13.0, margin=margin)
        seeds = wire_seeds_iv(grid, tp, bars)
        return src, doms, seeds

    return edges, build


class TestRestrictNoHang:
    def test_hang_class_terminates(self, p16_setup):
        # the recorded stock hang: non-trivial domains at scale, no
        # seeds, timeout ignored (notes.md s3.49-era addendum). The fork
        # must terminate promptly — clean failure or embedding, never a
        # hang or crash.
        edges, build = p16_setup
        fork = _load_fork()
        src, doms, _ = build(50, 1)
        t0 = time.perf_counter()
        try:
            emb = fork.find_embedding(src, edges, restrict_chains=doms,
                                      chainlength_patience=0,
                                      random_seed=0, timeout=15)
        except RuntimeError:
            emb = {}
        assert time.perf_counter() - t0 < 60

    def test_default_patience_alive(self, p16_setup):
        # the recorded stock segfault arm: default-patience shortening
        # with domains (crossbar_testbed.py:352-358)
        edges, build = p16_setup
        fork = _load_fork()
        src, doms, seeds = build(50, 2)
        t0 = time.perf_counter()
        try:
            emb = fork.find_embedding(
                src, edges, restrict_chains=doms,
                initial_chains={v: c for v, c in seeds.items()},
                chainlength_patience=10, random_seed=0, timeout=15)
        except RuntimeError:
            emb = {}
        assert time.perf_counter() - t0 < 90

    def test_seeded_restricted_embeds_within_domains(self, p16_setup):
        # the parked bar_domains handoff (anatomy s8): seeds + domains —
        # the exact combination that hung stock — must embed AND every
        # chain must respect its domain (the invariant the AND-mask
        # violated)
        edges, build = p16_setup
        fork = _load_fork()
        src, doms, seeds = build(60, 2)
        emb = fork.find_embedding(
            src, edges, restrict_chains=doms,
            initial_chains={v: c for v, c in seeds.items() if v in doms},
            chainlength_patience=10, random_seed=0, timeout=30)
        assert emb, "seeded restricted embedding failed"
        for v, c in emb.items():
            if v in doms:
                assert set(c) <= set(doms[v]), f"chain {v} left its domain"

    def test_out_of_domain_initial_chains_clipped(self):
        # initial chains outside the domain are clipped at ingest, not
        # installed verbatim (embedding ctor fix)
        import dwave_networkx as dnx
        fork = _load_fork()
        tgt = dnx.chimera_graph(4)
        edges = list(tgt.edges())
        src = nx.complete_graph(6)
        half = [q for q in tgt.nodes() if q < 64]
        other = [q for q in tgt.nodes() if q >= 64]
        doms = {v: half for v in src}
        emb = fork.find_embedding(
            src, edges, restrict_chains=doms,
            initial_chains={0: other[:3]},  # wholly outside 0's domain
            chainlength_patience=0, random_seed=0, timeout=10)
        if emb:
            assert set(emb[0]) <= set(half)
