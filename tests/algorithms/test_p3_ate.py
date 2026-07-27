"""Unit tests for P1/ATE (p3-template, p3-ate) and its _template_core module.

Small targets only (chimera_graph(4): 128 qubits, K_max=16; pegasus_graph(4):
264 qubits, K_max=36) so the whole file runs in seconds.

Covers (docs/paper3/proposals/ate.md):
  - chain path-ordering + crossing-position matrix POS correctness
  - prune-simulation vs real spur_prune agreement (measured envelope:
    total gap within ±2.7%, per-vertex |diff| <= 2 on 7 probe cells;
    asserted here with margin)
  - template validity for random subgraphs of K_n (incl. isolated vertices)
  - core+periphery for n > K_max
  - determinism (same-seed AND cross-seed for the template arm)
  - tiny-timeout behavior and clean failure on non-busclique targets
"""

import time

import networkx as nx
import dwave_networkx as dnx
import pytest

from ember_qc.registry import ALGORITHM_REGISTRY
from ember_qc.embedding_backend import is_valid_embedding
from ember_qc.algorithms.paper3._template_core import (
    _sorted_nodes,
    assign_slots,
    crossing_position_matrix,
    degeneracy_core,
    get_target_state,
    order_chain_qubits,
    ordered_template,
    restrict_template,
    simulate_pruned_lengths,
)

C4 = dnx.chimera_graph(4)
P4 = dnx.pegasus_graph(4)

TMPL = ALGORITHM_REGISTRY["p3-template"]
ATE = ALGORITHM_REGISTRY["p3-ate"]


def _nbr_idx(G, verts):
    vidx = {v: i for i, v in enumerate(verts)}
    return [[vidx[u] for u in G.neighbors(v) if u != v] for v in verts]


# ── target state / template plumbing ─────────────────────────────────────────

class TestTargetState:
    def test_singleton_keyed_by_topology(self):
        s1 = get_target_state(C4)
        s2 = get_target_state(dnx.chimera_graph(4))  # equal topology, new object
        assert s1 is s2
        assert s1.kmax == 16

    def test_non_busclique_target_returns_none(self):
        assert get_target_state(nx.path_graph(2)) is None
        assert get_target_state(nx.gnp_random_graph(30, 0.3, seed=1)) is None

    def test_oversized_template_is_none(self):
        st = get_target_state(C4)
        assert ordered_template(st, st.kmax + 1) is None


class TestChainOrderingAndPOS:
    @pytest.mark.parametrize("target,n", [(C4, 8), (C4, 16), (P4, 20)])
    def test_ordered_chains_are_paths(self, target, n):
        st = get_target_state(target)
        chains, _ = ordered_template(st, n)
        assert len(chains) == n
        for chain in chains:
            # same qubit set as an unordered chain, no repeats
            assert len(set(chain)) == len(chain)
            # consecutive qubits in the order are target-adjacent (path walk)
            for a, b in zip(chain, chain[1:]):
                assert b in st.adj[a], f"non-adjacent consecutive qubits {a},{b}"

    def test_order_chain_covers_all_qubits(self):
        st = get_target_state(C4)
        raw = st.bgc.find_clique_embedding(10)
        for key, chain in raw.items():
            ordered = order_chain_qubits(chain, st.adj)
            assert sorted(ordered) == sorted(int(q) for q in chain)

    def test_pos_matrix_correct_on_chimera4(self):
        st = get_target_state(C4)
        chains, pos = ordered_template(st, 12)
        chain_sets = [set(c) for c in chains]
        for i in range(12):
            for j in range(12):
                if i == j:
                    continue
                k = pos[i][j]
                # in range, and the qubit at k really touches chain j
                assert 0 <= k < len(chains[i])
                assert any(w in chain_sets[j] for w in st.adj[chains[i][k]])
                # firstness: no earlier position touches chain j
                for kk in range(k):
                    assert not any(
                        w in chain_sets[j] for w in st.adj[chains[i][kk]]
                    ), f"POS[{i}][{j}]={k} but position {kk} already touches j"


# ── prune simulation vs real spur_prune ──────────────────────────────────────

class TestPruneSimulation:
    @pytest.mark.parametrize("G,target", [
        (nx.gnp_random_graph(14, 0.5, seed=101), C4),
        (nx.complete_graph(16), C4),
        (nx.gnp_random_graph(30, 0.5, seed=101), P4),
        (nx.gnp_random_graph(36, 0.8, seed=101), P4),
    ])
    def test_simulator_tracks_real_prune(self, G, target):
        st = get_target_state(target)
        n = G.number_of_nodes()
        chains, pos = ordered_template(st, n)
        verts = _sorted_nodes(G)
        nbrs = _nbr_idx(G, verts)
        slots, _ = assign_slots(G, verts, pos)
        sim = simulate_pruned_lengths(slots, nbrs, pos)
        emb = restrict_template(G, verts, slots, chains, st.adj)
        real = [len(emb[i]) for i in range(n)]
        # measured envelope (probe, 7 cells): total gap within ±2.7%,
        # per-vertex |diff| <= 2, >=86% exact. Asserted with margin.
        assert abs(sum(sim) - sum(real)) <= max(2, 0.10 * sum(real))
        assert max(abs(s - r) for s, r in zip(sim, real)) <= 3
        exact = sum(1 for s, r in zip(sim, real) if s == r)
        assert exact >= 0.6 * n

    def test_isolated_vertex_simulates_to_one(self):
        st = get_target_state(C4)
        G = nx.empty_graph(6)
        chains, pos = ordered_template(st, 6)
        verts = _sorted_nodes(G)
        sim = simulate_pruned_lengths(list(range(6)), _nbr_idx(G, verts), pos)
        assert sim == [1] * 6


# ── template arm end-to-end ──────────────────────────────────────────────────

class TestTemplateArm:
    @pytest.mark.parametrize("p", [0.2, 0.5, 0.8])
    def test_valid_on_random_subgraphs_of_kn(self, p):
        G = nx.gnp_random_graph(15, p, seed=101)
        r = TMPL.embed(G, C4, timeout=10.0, seed=0)
        emb = r["embedding"]
        assert emb, f"template arm failed: {r.get('error')}"
        assert is_valid_embedding(emb, G, C4)
        assert set(emb) == set(G.nodes())
        for chain in emb.values():
            assert isinstance(chain, list)
            assert all(type(q) is int for q in chain)

    def test_valid_at_exactly_kmax(self):
        G = nx.complete_graph(16)  # == K_max(C4)
        r = TMPL.embed(G, C4, timeout=10.0, seed=0)
        assert r["embedding"] and is_valid_embedding(r["embedding"], G, C4)
        assert r["metadata"]["template_mode"] == "direct"

    def test_isolated_vertices_get_singleton_chains(self):
        G = nx.Graph()
        G.add_nodes_from(range(8))
        G.add_edges_from([(0, 1), (2, 3)])
        r = TMPL.embed(G, C4, timeout=5.0, seed=0)
        emb = r["embedding"]
        assert emb and is_valid_embedding(emb, G, C4)
        for v in (4, 5, 6, 7):
            assert len(emb[v]) == 1

    def test_core_periphery_above_kmax(self):
        G = nx.gnp_random_graph(20, 0.4, seed=101)  # 20 > K_max(C4)=16
        r = TMPL.embed(G, C4, timeout=10.0, seed=0)
        emb = r["embedding"]
        assert emb, f"core+periphery failed: {r.get('error')}"
        assert is_valid_embedding(emb, G, C4)
        assert r["metadata"]["template_mode"] == "core_periphery"
        assert r["metadata"]["core_size"] == 16

    def test_degeneracy_core_is_dense_suffix(self):
        # planted core: K8 plus a path of pendants
        G = nx.complete_graph(8)
        G.add_edges_from([(7 + i, 8 + i) for i in range(1, 6)])
        core = degeneracy_core(G, 8)
        assert sorted(core) == list(range(8))

    def test_failure_on_non_busclique_target(self):
        r = TMPL.embed(nx.complete_graph(4), nx.path_graph(2), timeout=1.0, seed=0)
        assert r["embedding"] == {}
        assert r["status"] == "FAILURE"
        assert isinstance(r["time"], float)


# ── determinism ──────────────────────────────────────────────────────────────

class TestDeterminism:
    def test_template_same_seed_identical(self):
        G = nx.gnp_random_graph(14, 0.5, seed=101)
        r1 = TMPL.embed(G, C4, timeout=10.0, seed=0)
        r2 = TMPL.embed(G, C4, timeout=10.0, seed=0)
        assert r1["embedding"] == r2["embedding"]

    def test_template_cross_seed_identical_below_kmax(self):
        # spec: zero cross-seed variance by construction for the direct path
        G = nx.gnp_random_graph(14, 0.5, seed=101)
        r1 = TMPL.embed(G, C4, timeout=10.0, seed=0)
        r2 = TMPL.embed(G, C4, timeout=10.0, seed=1)
        assert r1["embedding"] == r2["embedding"]

    def test_ate_same_seed_identical(self):
        G = nx.gnp_random_graph(14, 0.5, seed=101)
        r1 = ATE.embed(G, C4, timeout=10.0, seed=3)
        r2 = ATE.embed(G, C4, timeout=10.0, seed=3)
        assert r1["embedding"] == r2["embedding"]
        assert r1["metadata"]["winner"] == r2["metadata"]["winner"]


# ── auto-select arm ──────────────────────────────────────────────────────────

class TestATESelection:
    def test_winner_and_both_acls_recorded(self):
        G = nx.gnp_random_graph(14, 0.5, seed=101)
        r = ATE.embed(G, C4, timeout=10.0, seed=0)
        meta = r["metadata"]
        assert r["embedding"]
        assert meta["winner"] in ("template", "mm")
        assert meta["acl_template"] is not None
        assert meta["acl_mm"] is not None
        chosen_acl = sum(len(c) for c in r["embedding"].values()) / len(r["embedding"])
        assert chosen_acl == pytest.approx(
            min(meta["acl_template"], meta["acl_mm"]), abs=1e-3)

    def test_ate_succeeds_when_template_infeasible_target(self):
        # non-busclique target: template arm unavailable, MM still delivers
        tgt = nx.grid_2d_graph(8, 8)
        tgt = nx.convert_node_labels_to_integers(tgt)
        G = nx.cycle_graph(6)
        r = ATE.embed(G, tgt, timeout=10.0, seed=0)
        assert r["embedding"] and is_valid_embedding(r["embedding"], G, tgt)
        assert r["metadata"]["winner"] == "mm"
        assert r["metadata"]["template_mode"] == "unavailable"

    def test_ate_failure_is_clean(self):
        r = ATE.embed(nx.complete_graph(20), nx.path_graph(2), timeout=1.0, seed=0)
        assert r["embedding"] == {}
        assert r["status"] in ("FAILURE", "TIMEOUT")
        assert r["metadata"]["winner"] == "none"


# ── timeout behavior ─────────────────────────────────────────────────────────

class TestTinyTimeout:
    @pytest.mark.parametrize("algo", [TMPL, ATE], ids=["p3-template", "p3-ate"])
    def test_returns_quickly_with_tiny_timeout(self, algo):
        G = nx.complete_graph(15)
        t0 = time.perf_counter()
        r = algo.embed(G, C4, timeout=0.2, seed=0)
        elapsed = time.perf_counter() - t0
        assert elapsed < 3.0
        assert isinstance(r, dict) and "embedding" in r and "time" in r

    def test_core_periphery_tiny_timeout(self):
        G = nx.gnp_random_graph(20, 0.4, seed=101)
        t0 = time.perf_counter()
        r = TMPL.embed(G, C4, timeout=0.3, seed=0)
        elapsed = time.perf_counter() - t0
        assert elapsed < 3.0
        assert isinstance(r, dict) and "embedding" in r
