"""Unit tests for the P2 CLMM arms (`p3-clmm`, `p3-clmm-core`).

Covers, per the P2 deliverable: seeding correctness (template chains are a
disjoint clique template; pruned core seeds stay valid for the core-induced
subgraph; MM's legalized output is a valid embedding), both Zbinden selection
rules, the k < n and k >= n branches, degeneracy-core peeling, determinism,
and the tiny-timeout contract. Small targets (chimera_graph(4),
pegasus_graph(4)) keep every MM stage sub-second.

v1.2 additions: the architecture-aware guard threshold (0.35 chimera-class /
0.15 pegasus-zephyr-class / 0.15 non-busclique fallback, improvement-notes
#11) and the Z12-class identity regression (§5 frozen-arm policy: the gate
edit must leave pegasus/zephyr-class behavior byte-identical to v1.1).
"""

import hashlib
import time

import networkx as nx
import dwave_networkx as dnx
import pytest

from ember_qc.registry import ALGORITHM_REGISTRY
from ember_qc.embedding_backend import is_valid_embedding
from ember_qc.algorithms.search_orders import degeneracy_order
from ember_qc.algorithms.paper3.clmm import (
    _bus_entry,
    _guard_threshold,
    _prune_seed_chains,
    _select_core,
    _select_zbinden,
    _template_chains,
)

C4 = dnx.chimera_graph(4)     # busclique max clique 16 (chimera-class gate 0.35)
P4 = dnx.pegasus_graph(4)     # busclique max clique 36 (pegasus-class gate 0.15)
Z3 = dnx.zephyr_graph(3)      # busclique max clique 40 (zephyr-class gate 0.15)
C4_MAXCLIQUE = 16

CLMM = ALGORITHM_REGISTRY["p3-clmm"]
CORE = ALGORITHM_REGISTRY["p3-clmm-core"]


def _assert_valid(result, source, target):
    emb = result["embedding"]
    assert emb, f"expected success, got {result.get('status')}: {result.get('error')}"
    assert set(emb) == set(source.nodes())
    for chain in emb.values():
        assert isinstance(chain, list)
        assert all(isinstance(q, int) for q in chain)
    assert is_valid_embedding(emb, source, target)
    return emb


# ── template + seeding correctness ────────────────────────────────────────────

class TestSeeding:
    def test_template_chains_are_disjoint_int_lists(self):
        entry = _bus_entry(C4)
        chains = _template_chains(entry, 8)
        assert len(chains) == 8
        seen = set()
        qubits = set(C4.nodes())
        for c in chains:
            assert isinstance(c, list) and c
            assert all(isinstance(q, int) and q in qubits for q in c)
            assert not (set(c) & seen), "template chains overlap"
            seen |= set(c)

    def test_template_oversized_k_returns_none(self):
        entry = _bus_entry(C4)
        assert _template_chains(entry, C4_MAXCLIQUE + 1) is None

    def test_seeded_output_is_valid_when_template_is_already_legal(self):
        # K16 -> C4: the busclique template IS a legal K16 embedding, so MM
        # only has to legalize/keep the seeds. Output must be valid.
        src = nx.complete_graph(C4_MAXCLIQUE)
        r = CLMM.embed(src, C4, timeout=10.0, seed=0)
        _assert_valid(r, src, C4)
        assert r["metadata"]["selection"] == "all"
        assert r["metadata"]["n_seeded"] == C4_MAXCLIQUE

    def test_core_seeds_pruned_chains_stay_valid_for_core_subgraph(self):
        # Directly exercise the seed-prune step: pruned chains must still be a
        # valid embedding of the core-induced source subgraph, using no more
        # qubits than the raw template chains.
        src = nx.gnp_random_graph(24, 0.25, seed=3)
        entry = _bus_entry(C4)
        k = min(24, entry["maxclique"])
        chains = _template_chains(entry, k)
        chosen = _select_core(src, sorted(src.nodes()), k)
        initial = {v: chains[i] for i, v in enumerate(chosen)}
        raw_qubits = sum(len(c) for c in initial.values())
        pruned = _prune_seed_chains(src, chosen, initial, C4, entry,
                                    deadline=time.perf_counter() + 10.0)
        assert set(pruned) == set(chosen)
        assert sum(len(c) for c in pruned.values()) <= raw_qubits
        core_sub = src.subgraph(chosen)
        assert is_valid_embedding(pruned, core_sub, C4)

    def test_isolated_source_vertices_are_embedded(self):
        # Graph-object gotcha: isolated vertices must survive to the output.
        src = nx.gnp_random_graph(12, 0.15, seed=5)
        src.add_nodes_from([100, 101])   # guaranteed isolates
        for algo in (CLMM, CORE):
            r = algo.embed(src, C4, timeout=10.0, seed=0)
            emb = _assert_valid(r, src, C4)
            assert emb[100] and emb[101]


# ── selection rules ───────────────────────────────────────────────────────────

class TestSelectionRules:
    def test_dense_rule_is_seeded_random_sample(self):
        src = nx.gnp_random_graph(24, 0.5, seed=1)   # density >= 0.3
        nodes = sorted(src.nodes())
        got = _select_zbinden(src, nodes, 10, seed=7)
        import random as _random
        expected = sorted(_random.Random(7).sample(nodes, 10))
        assert got == expected

    def test_sparse_rule_is_lowest_degree(self):
        src = nx.gnp_random_graph(24, 0.1, seed=2)   # density < 0.3
        nodes = sorted(src.nodes())
        got = _select_zbinden(src, nodes, 10, seed=7)
        degs = dict(src.degree())
        expected = sorted(sorted(nodes, key=lambda v: (degs[v], v))[:10])
        assert got == expected
        assert max(degs[v] for v in got) <= min(
            degs[v] for v in nodes if v not in got)

    def test_arm_reports_random_branch_when_dense_and_k_lt_n(self):
        # n=18 > k=16, realized density 0.353 >= 0.3, stock-MM-feasible on C4
        src = nx.gnp_random_graph(18, 0.35, seed=1)
        r = CLMM.embed(src, C4, timeout=10.0, seed=0)
        _assert_valid(r, src, C4)
        assert r["metadata"]["selection"] == "random"
        assert r["metadata"]["template_k"] == C4_MAXCLIQUE
        assert r["metadata"]["n_seeded"] == C4_MAXCLIQUE

    def test_arm_reports_lowdeg_branch_when_sparse_and_k_lt_n(self):
        # v1.1: the density guard would pass this sparse source through to
        # stock MM — guard=False exercises the faithful Zbinden branch.
        src = nx.gnp_random_graph(30, 0.08, seed=4)  # n=30 > k=16, sparse
        r = CLMM.embed(src, C4, timeout=10.0, seed=0, guard=False)
        _assert_valid(r, src, C4)
        assert r["metadata"]["selection"] == "lowdeg"

    def test_guard_passthrough_below_density_gate(self):
        src = nx.gnp_random_graph(30, 0.08, seed=4)  # density < 0.15
        r = CLMM.embed(src, C4, timeout=10.0, seed=0)
        _assert_valid(r, src, C4)
        assert r["metadata"]["selection"] == "guard_passthrough_mm"

    def test_arm_reports_all_branch_when_k_ge_n(self):
        # v1.2: C4 is chimera-class (gate 0.35), so this density-0.27 source
        # would pass through — guard=False exercises the k >= n branch itself.
        src = nx.gnp_random_graph(12, 0.3, seed=6)   # n=12 <= k=16
        for algo in (CLMM, CORE):
            r = algo.embed(src, C4, timeout=10.0, seed=0, guard=False)
            _assert_valid(r, src, C4)
            assert r["metadata"]["selection"] == "all"
            assert r["metadata"]["template_k"] == 12
            assert r["metadata"]["n_seeded"] == 12


# ── v1.2 architecture-aware gate (improvement-notes #11, §4.11-C16) ──────────

class TestArchitectureAwareGate:
    def test_threshold_by_target_architecture(self):
        # kmax-keyed, size-invariant: chimera-class kmax/sqrt(|V|) ~ 1.41
        # gates at 0.35; pegasus/zephyr-class (>= 1.7) keep the measured 0.15.
        assert _guard_threshold(Z3) == 0.15
        assert _guard_threshold(P4) == 0.15
        assert _guard_threshold(C4) == 0.35

    def test_threshold_non_busclique_target_falls_back(self):
        # busclique raises on non-{chimera,pegasus,zephyr} targets: the gate
        # must return the v1.1 threshold (0.15), never raise.
        assert _guard_threshold(nx.path_graph(2)) == 0.15
        assert _guard_threshold(nx.gnp_random_graph(40, 0.3, seed=0)) == 0.15

    @pytest.mark.parametrize("algo", [CLMM, CORE], ids=["clmm", "core"])
    def test_density_02_passthrough_on_chimera_seeded_on_zephyr(self, algo):
        # Density exactly 0.2 sits between the two gates: passthrough on
        # chimera-class (0.2 < 0.35), seeded on zephyr-class (0.2 >= 0.15).
        src = nx.gnm_random_graph(20, 38, seed=1)    # 38/190 = 0.2 exactly
        assert nx.density(src) == pytest.approx(0.2)

        r = algo.embed(src, C4, timeout=10.0, seed=0)
        _assert_valid(r, src, C4)
        assert r["metadata"]["selection"] == "guard_passthrough_mm"
        assert r["metadata"]["guard_threshold"] == 0.35

        rz = algo.embed(src, Z3, timeout=10.0, seed=0)
        _assert_valid(rz, src, Z3)
        assert rz["metadata"]["selection"] == "all"   # seeded: n=20 <= kmax=40
        assert rz["metadata"]["template_k"] == 20
        assert rz["metadata"]["n_seeded"] == 20


class TestZ12ClassIdentityRegression:
    """§5 frozen-arm policy: the v1.2 kmax-keyed gate is the sole in-place
    clmm edit and must leave pegasus/zephyr-class behavior BYTE-IDENTICAL to
    v1.1. Hashes captured from the v1.1 code (paper3 @ 2161c9dc) on this
    exact instance with minorminer 0.2.22. A mismatch means the gate altered
    Zephyr-class output — a protocol breach to fix, not a hash to update."""

    _V11_HASH = {
        "p3-clmm":
            "dff253c3b8b7777e5f7e4c82394076f2c4707d39b274ed9746728c23afaada65",
        "p3-clmm-core":
            "bf492a65a7d6574c0a8a3b1c9f86e4d3b7af0a88e5cd82ae07a9655bf60c6ff9",
    }

    @pytest.mark.parametrize("name", ["p3-clmm", "p3-clmm-core"])
    def test_embedding_identical_to_v11_on_zephyr_class(self, name):
        z4 = dnx.zephyr_graph(4)                      # kmax 56, gate 0.15
        src = nx.gnp_random_graph(30, 0.3, seed=2)    # density 0.285 -> seeded
        algo = ALGORITHM_REGISTRY[name]
        r1 = algo.embed(src, z4, timeout=10.0, seed=0)
        r2 = algo.embed(src, z4, timeout=10.0, seed=0)
        emb = _assert_valid(r1, src, z4)
        assert r1["embedding"] == r2["embedding"]     # same-seed determinism
        assert r1["metadata"]["selection"] == "all"   # seeded path, not guard
        canon = sorted((v, tuple(c)) for v, c in emb.items())
        digest = hashlib.sha256(repr(canon).encode()).hexdigest()
        assert digest == self._V11_HASH[name], (
            f"{name} output on the fixed Z12-class instance differs from "
            f"v1.1 (got {digest})")


# ── degeneracy-core peeling ───────────────────────────────────────────────────

class TestCorePeeling:
    def test_core_selection_matches_degeneracy_order_prefix(self):
        src = nx.gnp_random_graph(30, 0.2, seed=8)
        got = _select_core(src, sorted(src.nodes()), 16)
        assert got == sorted(degeneracy_order(src)[:16])

    def test_core_keeps_planted_clique_and_drops_pendants(self):
        # K8 (vertices 0..7) with a pendant path hanging off vertex 0:
        # peeling to 8 vertices must keep exactly the K8.
        src = nx.complete_graph(8)
        src.add_edges_from([(0, 8), (8, 9), (9, 10), (10, 11)])
        got = _select_core(src, sorted(src.nodes()), 8)
        assert got == list(range(8))

    def test_core_arm_seeds_the_core_only(self):
        src = nx.complete_graph(8)
        src.add_edges_from([(0, 8), (8, 9), (9, 10), (10, 11)])
        # n=12 > forced k? No: k=min(12,16)=12 -> all. Use a bigger pendant
        # fringe so n > 16 and the core branch is real. v1.2: density 0.21 is
        # below C4's chimera-class gate (0.35) — guard=False keeps the core
        # branch under test.
        src.add_edges_from((10, x) for x in range(12, 20))   # n=20 > 16
        r = CORE.embed(src, C4, timeout=10.0, seed=0, guard=False)
        _assert_valid(r, src, C4)
        assert r["metadata"]["selection"] == "core"
        assert r["metadata"]["n_seeded"] == C4_MAXCLIQUE
        # prune must not have grown the seeds
        assert r["metadata"]["seed_qubits"] <= r["metadata"]["seed_qubits_pre_prune"]

    def test_frontier_branch_k_lt_n_on_pegasus(self):
        # K38 > P4's max clique 36: k clamps to 36, dense -> random selection.
        # Success is not asserted (frontier); the contract shape is.
        src = nx.complete_graph(38)
        r = CLMM.embed(src, P4, timeout=10.0, seed=0)
        assert isinstance(r, dict) and "embedding" in r
        if r["embedding"]:
            _assert_valid(r, src, P4)
            assert r["metadata"]["template_k"] == 36
            assert r["metadata"]["selection"] == "random"


# ── determinism ───────────────────────────────────────────────────────────────

class TestDeterminism:
    @pytest.mark.parametrize("algo", [CLMM, CORE], ids=["clmm", "core"])
    def test_same_seed_same_embedding(self, algo):
        src = nx.gnp_random_graph(20, 0.3, seed=9)
        r1 = algo.embed(src, C4, timeout=10.0, seed=42)
        r2 = algo.embed(src, C4, timeout=10.0, seed=42)
        assert r1["embedding"] == r2["embedding"]

    def test_different_seed_may_differ_but_is_valid(self):
        src = nx.gnp_random_graph(18, 0.35, seed=1)  # random-selection branch
        r1 = CLMM.embed(src, C4, timeout=10.0, seed=0)
        r2 = CLMM.embed(src, C4, timeout=10.0, seed=1)
        _assert_valid(r1, src, C4)
        _assert_valid(r2, src, C4)


# ── timeout + failure contract ────────────────────────────────────────────────

class TestTimeoutAndFailure:
    @pytest.mark.parametrize("algo", [CLMM, CORE], ids=["clmm", "core"])
    def test_tiny_timeout_returns_within_grace(self, algo):
        # Infeasible K30 -> C4 with a 0.5 s budget: the MM stage gets the
        # >= 1 s cooperative floor; total must stay far under the 5 s grace.
        start = time.perf_counter()
        r = algo.embed(nx.complete_graph(30), C4, timeout=0.5, seed=0)
        elapsed = time.perf_counter() - start
        assert elapsed < 5.0, f"took {elapsed:.2f}s with 0.5s timeout"
        assert isinstance(r, dict)
        assert r["embedding"] == {}
        assert r.get("success") is False
        assert r.get("status") in ("FAILURE", "TIMEOUT")
        assert isinstance(r["time"], float)

    @pytest.mark.parametrize("algo", [CLMM, CORE], ids=["clmm", "core"])
    def test_non_busclique_target_fails_cleanly(self, algo):
        r = algo.embed(nx.complete_graph(20), nx.path_graph(2),
                       timeout=1.0, seed=0)
        assert isinstance(r, dict)
        assert r["embedding"] == {}
        assert r.get("success") is False
        assert "busclique" in r.get("error", "")

    @pytest.mark.parametrize("algo", [CLMM, CORE], ids=["clmm", "core"])
    def test_inputs_not_mutated(self, algo):
        src = nx.gnp_random_graph(15, 0.3, seed=11)
        tgt = C4.copy()
        src_edges, tgt_edges = set(src.edges()), set(tgt.edges())
        src_nodes, tgt_nodes = set(src.nodes()), set(tgt.nodes())
        algo.embed(src, tgt, timeout=10.0, seed=0)
        assert set(src.edges()) == src_edges and set(src.nodes()) == src_nodes
        assert set(tgt.edges()) == tgt_edges and set(tgt.nodes()) == tgt_nodes
