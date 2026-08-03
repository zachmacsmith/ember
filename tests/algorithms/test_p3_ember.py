"""Unit tests for the v1.2 unified arm ``p3-ember`` and its native fast path
(``ember_qc.algorithms.paper3.native``). Pre-registration: notes.md §4.15.

Covers:
  - structural gates + Glasgow timeout clamp (unit level)
  - native hit on a Zephyr subgraph source (ACL exactly 1.0)
  - native miss falls through to template/MM. NOTE: the pre-registered miss
    exemplar was petersen -> Zephyr, but petersen IS a Glasgow hit on the
    degree-20 Zephyr fabric (measured 2026-08-03, 0.01 s); the miss case here
    uses a Chimera target, where petersen's odd cycles are provably absent.
  - find_subgraph determinism on identical inputs
  - the sub-K_max sparse gate (density < 0.08 -> template skipped)
  - dense cell: p3-ember ACL <= p3-ate ACL on the same (instance, seed)
  - non-int-label sources, tiny timeouts, clean failure
"""

import time

import networkx as nx
import dwave_networkx as dnx
import pytest

from ember_qc.registry import ALGORITHM_REGISTRY
from ember_qc.embedding_backend import is_valid_embedding
from ember_qc.algorithms.paper3.native import (
    glasgow_timeout,
    structural_pass,
    try_native,
)

C4 = dnx.chimera_graph(4)
Z2 = dnx.zephyr_graph(2)
Z3 = dnx.zephyr_graph(3)

EMBER = ALGORITHM_REGISTRY["p3-ember"]
ATE = ALGORITHM_REGISTRY["p3-ate"]


def _acl(emb):
    return sum(len(c) for c in emb.values()) / max(1, len(emb))


# ── structural gates + timeout clamp (unit) ──────────────────────────────────

class TestStructuralGates:
    def test_node_count_gate(self):
        assert not structural_pass(nx.complete_graph(20), nx.path_graph(2))

    def test_edge_count_gate(self):
        # n 10<=10, max deg 2<=2, but 10 edges > 9
        assert not structural_pass(nx.cycle_graph(10), nx.path_graph(10))

    def test_max_degree_gate(self):
        # n 10<=10, m 9<=15, but max deg 9 > 3
        assert not structural_pass(nx.star_graph(9), nx.petersen_graph())

    def test_empty_source_fails(self):
        assert not structural_pass(nx.empty_graph(0), C4)

    def test_feasible_shape_passes(self):
        assert structural_pass(nx.path_graph(3), C4)

    def test_timeout_clamp_never_zero(self):
        # find_subgraph treats 0 as UNLIMITED; the clamp must never emit it
        assert glasgow_timeout(0.2) == 1
        assert glasgow_timeout(0.0) == 1
        assert glasgow_timeout(-3.0) == 1
        assert glasgow_timeout(1.99) == 1
        assert glasgow_timeout(2.0) == 2
        assert glasgow_timeout(60.0) == 2


# ── native tier behavior ─────────────────────────────────────────────────────

class TestNativeFastPath:
    def test_zephyr_subgraph_is_native_hit(self):
        r = EMBER.embed(Z2, Z3, timeout=10.0, seed=0)
        emb = r["embedding"]
        assert emb and is_valid_embedding(emb, Z2, Z3)
        assert all(len(c) == 1 for c in emb.values())
        assert _acl(emb) == 1.0
        assert r["metadata"]["native"] in ("glasgow_hit", "label_identity")
        assert isinstance(r["metadata"]["native_s"], float)
        assert r["metadata"]["winner"] == "native"

    def test_native_miss_falls_through(self):
        # petersen has odd cycles; Chimera has none -> provable Glasgow miss
        pet = nx.petersen_graph()
        r = EMBER.embed(pet, C4, timeout=10.0, seed=0)
        assert r["metadata"]["native"] == "miss"
        emb = r["embedding"]
        assert emb and is_valid_embedding(emb, pet, C4)
        assert _acl(emb) > 1.0     # no subgraph placement exists
        assert r["metadata"]["winner"] in ("template", "mm")

    def test_find_subgraph_deterministic_on_same_inputs(self):
        from minorminer.subgraph import find_subgraph
        m1 = find_subgraph(Z2, Z3, timeout=2, parallel=False, seed=0)
        m2 = find_subgraph(Z2, Z3, timeout=2, parallel=False, seed=0)
        assert m1 == m2 and m1     # a hit, and byte-identical across calls

    def test_try_native_validates_glasgow_output(self):
        # deadline passed but structural+identity still run; no exception
        meta = {}
        out = try_native(nx.petersen_graph(), C4, time.perf_counter() + 5.0,
                         meta=meta)
        assert out is None and meta["native"] == "miss"

    def test_label_identity_tier(self):
        # a literal labelled subgraph of C4: identity map, no Glasgow needed
        sub = C4.subgraph(list(C4.nodes)[:16]).copy()
        meta = {}
        out = try_native(sub, C4, time.perf_counter() + 5.0,
                         allow_glasgow=False, meta=meta)
        assert out is not None and meta["native"] == "label_identity"
        assert is_valid_embedding(out, sub, C4)
        assert all(len(c) == 1 for c in out.values())


# ── sub-K_max sparse gate ────────────────────────────────────────────────────

class TestSparseGate:
    def test_sparse_source_skips_template(self):
        g = nx.gnp_random_graph(40, 0.05, seed=3)     # density 0.05 < 0.08
        assert nx.density(g) < 0.08
        r = EMBER.embed(g, dnx.zephyr_graph(4), timeout=2.0, seed=0)
        assert r["metadata"]["template_mode"] == "skipped_sparse"
        assert r["metadata"]["acl_template"] is None
        assert r["embedding"]      # MM still delivers on the sparse cell

    def test_dense_source_attempts_template(self):
        g = nx.gnp_random_graph(14, 0.5, seed=101)    # density 0.5 >= 0.08
        r = EMBER.embed(g, C4, timeout=2.0, seed=0)
        assert r["metadata"]["template_mode"] == "direct"
        assert r["metadata"]["acl_template"] is not None


# ── dense cell vs p3-ate (monotone polish) ───────────────────────────────────

class TestDenseVsAte:
    @pytest.mark.parametrize("seed", [0, 1])
    def test_ember_never_worse_than_ate_same_pair(self, seed):
        g = nx.gnp_random_graph(14, 0.5, seed=101)
        re_ = EMBER.embed(g, C4, timeout=10.0, seed=seed)
        ra = ATE.embed(g, C4, timeout=10.0, seed=seed)
        assert re_["embedding"] and ra["embedding"]
        assert is_valid_embedding(re_["embedding"], g, C4)
        assert _acl(re_["embedding"]) <= _acl(ra["embedding"]) + 1e-9
        meta = re_["metadata"]
        assert meta["acl_pre_polish"] is not None
        # metadata value is rounded to 4 decimals -> compare at that grain
        assert _acl(re_["embedding"]) <= meta["acl_pre_polish"] + 1e-3


# ── contract corners ─────────────────────────────────────────────────────────

class TestContractCorners:
    def test_non_int_label_source_does_not_crash(self):
        g = nx.relabel_nodes(nx.cycle_graph(6), {i: f"v{i}" for i in range(6)})
        r = EMBER.embed(g, C4, timeout=5.0, seed=0)
        assert isinstance(r, dict) and "embedding" in r and "time" in r
        if r["embedding"]:
            assert is_valid_embedding(r["embedding"], g, C4)

    def test_tiny_timeout_returns_quickly(self):
        t0 = time.perf_counter()
        r = EMBER.embed(nx.complete_graph(15), C4, timeout=0.5, seed=0)
        assert time.perf_counter() - t0 < 5.0
        assert isinstance(r, dict) and "embedding" in r

    def test_impossible_target_clean_failure(self):
        r = EMBER.embed(nx.complete_graph(20), nx.path_graph(2),
                        timeout=1.0, seed=0)
        assert r["embedding"] == {}
        assert r["success"] is False
        assert r["metadata"]["winner"] == "none"

    def test_same_seed_identical_including_native(self):
        r1 = EMBER.embed(Z2, Z3, timeout=10.0, seed=7)
        r2 = EMBER.embed(Z2, Z3, timeout=10.0, seed=7)
        assert r1["embedding"] == r2["embedding"]
        assert r1["metadata"]["native"] == r2["metadata"]["native"]
