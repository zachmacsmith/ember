"""
tests/algorithms/test_factored.py
===================================
Tests for the paper-2 factored embedder
(ember_qc.algorithms.factored): the cost family's algebraic properties
(docs/paper2/notes.md §3.5), the staleness regression, and end-to-end
embedding through the harness.
"""
import networkx as nx
import pytest

from ember_qc import benchmark_one
from ember_qc.registry import ALGORITHM_REGISTRY, validate_embedding
from ember_qc.embedding_backend import build_adjacency
from ember_qc.algorithms.factored import (
    LinearPathFinderCost,
    NegotiatedCost,
    embed_factored,
    estimate_diameter,
    shorten_chains,
    spur_prune,
)


class TestNegotiatedCost:
    def test_mm_corner_price_is_beta_pow_occ(self):
        # alpha = 0 ==> the price is exactly minorminer's beta^occ
        c = NegotiatedCost(range(5), beta=10.0, alpha=0.0)
        c.claim([0, 1])
        c.claim([1, 2])
        assert c.prices[3] == 1.0
        assert c.prices[0] == 10.0
        assert c.prices[1] == 100.0
        c.apply_history_update()  # no-op at alpha = 0
        assert all(h == 0.0 for h in c.hist.values())
        assert c.prices[1] == 100.0

    def test_depth_hierarchy(self):
        # L singly-occupied qubits are cheaper than ONE doubly-occupied qubit
        # for L < beta — the property the linear present term inverts.
        beta = 10.0
        c = NegotiatedCost(range(20), beta=beta, alpha=0.0)
        for q in range(9):
            c.claim([q])
        c.claim([10])
        c.claim([10])
        nine_singles = sum(c.prices[q] for q in range(9))
        assert nine_singles == 9 * beta
        assert c.prices[10] == beta ** 2
        assert nine_singles < c.prices[10]

    def test_history_up_hold_down_floor(self):
        # h <- max(0, h + alpha*(occ-1)): up with overuse, hold at exactly-full,
        # decay while slack, floor at zero.
        c = NegotiatedCost(range(4), beta=5.0, alpha=1.0)
        c.claim([0, 1])
        c.claim([0])
        c.claim([0])  # occ: q0 -> 3, q1 -> 1
        c.apply_history_update()
        assert c.hist[0] == 2.0  # +alpha*(3-1)
        assert c.hist[1] == 0.0  # hold at occ == 1
        assert c.hist[2] == 0.0  # floor at occ == 0
        c.release([0, 1])
        c.release([0])
        c.release([0])
        c.apply_history_update()
        assert c.hist[0] == 1.0  # decay while slack
        c.apply_history_update()
        assert c.hist[0] == 0.0
        c.apply_history_update()
        assert c.hist[0] == 0.0  # floored, never negative

    def test_history_multiplies_price_including_when_free(self):
        # a scarred-but-free qubit stays expensive until the scar decays
        c = NegotiatedCost(range(3), beta=4.0, alpha=1.0)
        c.claim([0])
        c.claim([0])
        c.apply_history_update()  # h[0] = 1
        assert c.prices[0] == (1.0 + 1.0) * 4.0 ** 2
        c.release([0])
        c.release([0])
        assert c.prices[0] == 2.0  # (1 + h) * beta^0

    def test_claim_release_price_coherence(self):
        # The staleness regression (paper-1 bug, notes.md §3.7): releasing a
        # chain must reprice its qubits immediately — a chain must never see
        # its own just-released footprint as occupied.
        c = NegotiatedCost(range(3), beta=7.0, alpha=1.0)
        c.claim([0, 1])
        assert c.prices[0] == 7.0
        c.release([0, 1])
        assert c.prices[0] == 1.0
        assert c.prices[1] == 1.0

    def test_beta_ramp_first_pass_is_congestion_oblivious(self):
        c = NegotiatedCost(range(3), beta=9.0, alpha=1.0, beta_ramp_passes=2)
        c.start_pass(0)
        c.claim([0])
        assert c.prices[0] == 1.0  # beta_eff = 1: occupancy invisible
        c.start_pass(2)
        assert c.prices[0] == 9.0  # ramp complete: full beta

    def test_contested(self):
        c = NegotiatedCost(range(4), beta=3.0)
        c.claim([0, 1])
        c.claim([1, 2])
        assert c.contested() == [1]


class TestLinearAblationArm:
    def test_linear_prices_and_ramp(self):
        c = LinearPathFinderCost(range(3), alpha=0.0, pres0=0.5, pres_mult=2.0,
                                 pres_max=4.0)
        c.claim([0])
        assert c.prices[0] == 1.5  # 1 + 0.5*1
        c.claim([0])
        assert c.prices[0] == 2.0  # 1 + 0.5*2
        c.start_pass(2)            # pres = min(0.5*2^2, 4.0) = 2.0
        assert c.prices[0] == 5.0  # 1 + 2.0*2
        c.start_pass(10)           # capped at pres_max
        assert c.prices[0] == 9.0  # 1 + 4.0*2


class TestDiameterEstimate:
    def test_path_graph_exact(self):
        adj = build_adjacency(nx.path_graph(6))
        assert estimate_diameter(adj) == 5

    def test_cycle_graph_exact(self):
        adj = build_adjacency(nx.cycle_graph(8))
        assert estimate_diameter(adj) == 4


class TestEndToEnd:
    def test_registered(self):
        assert "factored" in ALGORITHM_REGISTRY

    def test_valid_embedding_complete_graph(self, chimera):
        r = benchmark_one(nx.complete_graph(6), chimera, "factored",
                          timeout=15.0, seed=0)
        assert r.success and r.is_valid

    def test_valid_embedding_er_graph(self, chimera):
        source = nx.convert_node_labels_to_integers(
            nx.gnp_random_graph(14, 0.45, seed=99))
        r = benchmark_one(source, chimera, "factored", timeout=20.0, seed=0)
        assert r.success and r.is_valid

    def test_independent_validation(self, chimera):
        algo = ALGORITHM_REGISTRY["factored"]
        emb = algo.embed(nx.cycle_graph(8), chimera, timeout=15.0, seed=1)["embedding"]
        assert emb
        assert validate_embedding(emb, nx.cycle_graph(8), chimera)

    def test_axis_overrides_pass_through_registry(self, chimera):
        algo = ALGORITHM_REGISTRY["factored"]
        emb = algo.embed(nx.complete_graph(5), chimera, timeout=15.0, seed=0,
                         order="bfs", tree="union", alpha=0.0)["embedding"]
        assert emb
        assert validate_embedding(emb, nx.complete_graph(5), chimera)


class TestDeterminism:
    def test_same_seed_same_embedding(self, chimera):
        source = nx.convert_node_labels_to_integers(
            nx.gnp_random_graph(12, 0.4, seed=7))
        a = embed_factored(source, chimera, timeout=20.0, seed=3)
        b = embed_factored(source, chimera, timeout=20.0, seed=3)
        assert a["embedding"] == b["embedding"]

    def test_random_order_is_seed_deterministic(self, chimera):
        source = nx.convert_node_labels_to_integers(
            nx.gnp_random_graph(10, 0.4, seed=5))
        a = embed_factored(source, chimera, timeout=20.0, seed=2, order="random")
        b = embed_factored(source, chimera, timeout=20.0, seed=2, order="random")
        assert a["embedding"] == b["embedding"]


class TestPolish:
    def test_spur_prune_removes_dead_leaf(self):
        # path 0-1-2; source edge (0,1); chain0=[0,1], chain1=[2].
        # Qubit 0 dangles: removing it keeps chain0 connected and the edge
        # covered (1~2), so it must go.
        adj = build_adjacency(nx.path_graph(3))
        pruned = spur_prune({0: [0, 1], 1: [2]}, {0: [1], 1: [0]}, adj)
        assert pruned == {0: [1], 1: [2]}

    def test_spur_prune_keeps_covering_qubit(self):
        # path 0-1-2-3; source edge (0,1); chain0=[1,2], chain1=[3].
        # Qubit 2 carries the edge (2~3) and must survive; qubit 1 is the spur.
        adj = build_adjacency(nx.path_graph(4))
        pruned = spur_prune({0: [1, 2], 1: [3]}, {0: [1], 1: [0]}, adj)
        assert pruned == {0: [2], 1: [3]}

    def test_shorten_chains_takes_free_space_shortcut(self):
        # cycle 0..5; source edge (0,1); chain0 routes the long way [0,5,4,3];
        # the one-qubit rebuild [1] reaches chain1=[2] directly.
        adj = build_adjacency(nx.cycle_graph(6))
        out = shorten_chains({0: [0, 5, 4, 3], 1: [2]}, {0: [1], 1: [0]}, adj)
        assert out == {0: [1], 1: [2]}

    def test_polish_flag_end_to_end(self, chimera):
        source = nx.convert_node_labels_to_integers(
            nx.gnp_random_graph(14, 0.45, seed=99))
        raw = embed_factored(source, chimera, timeout=20.0, seed=0)
        pol = embed_factored(source, chimera, timeout=20.0, seed=0, polish=True)
        assert pol["embedding"]
        assert validate_embedding(pol["embedding"], source, chimera)
        q_raw = sum(len(c) for c in raw["embedding"].values())
        q_pol = sum(len(c) for c in pol["embedding"].values())
        assert q_pol <= q_raw
        pol2 = embed_factored(source, chimera, timeout=20.0, seed=0, polish=True)
        assert pol["embedding"] == pol2["embedding"]


class TestRandomizedModes:
    """MM-faithful randomization knobs: per-pass order reshuffle + random ties."""

    REPLICA = dict(order="random", order_per_pass=True, random_ties=True,
                   tree="union", alpha=0.0)

    def test_replica_mode_embeds_validly(self, chimera):
        source = nx.complete_graph(5)
        r = embed_factored(source, chimera, timeout=20.0, seed=0, **self.REPLICA)
        assert r["embedding"]
        assert validate_embedding(r["embedding"], source, chimera)

    def test_replica_mode_seed_reproducible(self, chimera):
        source = nx.convert_node_labels_to_integers(
            nx.gnp_random_graph(12, 0.4, seed=7))
        a = embed_factored(source, chimera, timeout=20.0, seed=5, **self.REPLICA)
        b = embed_factored(source, chimera, timeout=20.0, seed=5, **self.REPLICA)
        assert a["embedding"] == b["embedding"]

    def test_root_tie_sampling_uses_rng(self):
        # cycle 0-1-2-3: v=0 connects chains [1] and [3]; qubits 0 and 2 are
        # exactly-tied roots. rng must sample among them; no rng = lowest id.
        import random as _random
        from ember_qc.algorithms.factored.trees import sph_tree
        adj = build_adjacency(nx.cycle_graph(4))
        chains = {1: [1], 2: [3]}
        ones = {q: 1.0 for q in adj}
        seen = {tuple(sph_tree(0, [1, 2], chains, adj, ones, [0],
                               rng=_random.Random(s)))
                for s in range(10)}
        assert seen == {(0,), (2,)}  # both tie candidates get sampled
        assert sph_tree(0, [1, 2], chains, adj, ones, [0]) == [0]  # det: min id

    def test_seed_qubit_uses_rng(self):
        import random as _random
        from ember_qc.algorithms.factored.loop import _seed_qubit
        adj = build_adjacency(nx.path_graph(6))
        qubits = tuple(adj)
        occ = {q: 0 for q in qubits}
        seen = {_seed_qubit(qubits, adj, occ, rng=_random.Random(s))
                for s in range(12)}
        assert len(seen) >= 2                       # rng: uniform over free
        assert _seed_qubit(qubits, adj, occ) == 0   # deterministic: min free

    def test_flags_off_unchanged_by_new_knobs(self, chimera):
        # Defaults must not consume rng draws for ties: identical to a run
        # with the knobs explicitly disabled.
        source = nx.convert_node_labels_to_integers(
            nx.gnp_random_graph(12, 0.4, seed=7))
        a = embed_factored(source, chimera, timeout=20.0, seed=3)
        b = embed_factored(source, chimera, timeout=20.0, seed=3,
                             order_per_pass=False, random_ties=False)
        assert a["embedding"] == b["embedding"]


class TestFamilyCorners:
    """Every corner of the (cost, tree, order) family must still embed."""

    @pytest.mark.parametrize("overrides", [
        dict(order="random", tree="union", alpha=0.0),  # the minorminer corner
        dict(order="bfs", tree="sph", alpha=1.0),
        dict(order="cuthill", tree="union", alpha=1.0),
        dict(cost="linear", order="cuthill", tree="sph", alpha=1.0),
        dict(beta_ramp_passes=4),                        # ME-style oblivious start
    ])
    def test_corner_embeds_validly(self, chimera, overrides):
        source = nx.complete_graph(5)
        r = embed_factored(source, chimera, timeout=15.0, seed=0, **overrides)
        assert r["embedding"]
        assert validate_embedding(r["embedding"], source, chimera)
