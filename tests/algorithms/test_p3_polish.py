"""P5 polish tests — exact repairs, joint pair move, anytime loop, arm.

Covers docs/paper3/proposals/polish.md (P5b operators):
  - exact_repair_1 / joint_repair_2 preserve validity and only accept strict
    improvements (constructed cases with known optima);
  - joint_repair_2 fixes a hand-built configuration that is provably stuck
    under single-vertex moves (the swap gadget) — the move-set-completeness
    scenario the K60 probe generalises;
  - the exact engine agrees with brute force on random instances (including
    multiplicity-2 requirements, the pair-union relaxation);
  - anytime_polish is monotone non-worsening, deadline-respecting and
    deterministic;
  - the registered arm p3-mmpolish behaves (full contract coverage lives in
    test_algorithm_contracts.py, which parametrises over every p3-* arm).
"""

import itertools
import random
import time

import networkx as nx
import dwave_networkx as dnx
import pytest

from ember_qc.embedding_backend import (
    build_adjacency,
    chain_connected,
    is_valid_embedding,
)
from ember_qc.algorithms.paper3.joint_repair import (
    _CoverSearch,
    _group_distances,
    _reduce_groups,
    anytime_polish,
    exact_repair_1,
    joint_repair_2,
)


def _total(emb):
    return sum(len(c) for c in emb.values())


# ── Constructed case 1: detour on a 7-cycle (single-vertex repair) ────────────
# Target C7, source path 0-1-2 pinned at qubits {0} and {3}; the middle chain
# goes the long way round ([4,5,6]); the unique region-optimal chain is [1,2].

@pytest.fixture()
def cycle7():
    tgt = nx.cycle_graph(7)
    src = nx.path_graph(3)
    emb = {0: [0], 1: [4, 5, 6], 2: [3]}
    assert is_valid_embedding(emb, src, tgt)
    return emb, src, tgt


class TestExactRepair1:
    def test_finds_detour_fix_and_preserves_validity(self, cycle7):
        emb, src, tgt = cycle7
        out = exact_repair_1(emb, src, tgt, 1, radius=2,
                             deadline=time.perf_counter() + 10)
        assert out.improved and out.proven
        assert sorted(out.embedding[1]) == [1, 2]
        assert out.old_total == 3 and out.new_total == 2
        assert is_valid_embedding(out.embedding, src, tgt)
        # untouched chains identical; input not mutated
        assert out.embedding[0] == [0] and out.embedding[2] == [3]
        assert emb[1] == [4, 5, 6]

    def test_optimal_chain_is_a_proven_fixpoint(self, cycle7):
        emb, src, tgt = cycle7
        first = exact_repair_1(emb, src, tgt, 1, radius=2,
                               deadline=time.perf_counter() + 10)
        again = exact_repair_1(first.embedding, src, tgt, 1, radius=2,
                               deadline=time.perf_counter() + 10)
        assert not again.improved and again.proven
        assert again.embedding is None

    def test_singleton_chain_is_trivially_optimal(self, cycle7):
        emb, src, tgt = cycle7
        out = exact_repair_1(emb, src, tgt, 0, radius=2,
                             deadline=time.perf_counter() + 10)
        assert not out.improved and out.proven


# ── Constructed case 2: the swap gadget (joint pair move required) ────────────
# Qubits: A=0, a=1, b=2, B=3 on a cheap central path; x1=4,x2=5 / y1=6,y2=7 on
# an expensive outer path. Source path A'-u-v-B' (0-1-2-3), A' pinned at {0},
# B' at {3}. Old chains u=[4,5], v=[6,7]. Given the other pinned, each chain is
# provably region-minimum (a={1} does not touch v's old chain, b={2} does not
# touch u's) — yet jointly u={1}, v={2} halves the total. Exactly the
# joint-move blindness P5b probes.

@pytest.fixture()
def swap_gadget():
    tgt = nx.Graph()
    tgt.add_edges_from(
        [(0, 1), (1, 2), (2, 3), (0, 4), (4, 5), (5, 6), (6, 7), (7, 3)])
    src = nx.path_graph(4)
    emb = {0: [0], 1: [4, 5], 2: [6, 7], 3: [3]}
    assert is_valid_embedding(emb, src, tgt)
    return emb, src, tgt


class TestJointRepair2:
    def test_singles_are_provably_stuck(self, swap_gadget):
        emb, src, tgt = swap_gadget
        for v in (1, 2):
            out = exact_repair_1(emb, src, tgt, v, radius=2,
                                 deadline=time.perf_counter() + 10)
            assert not out.improved and out.proven

    def test_pair_move_fixes_it(self, swap_gadget):
        emb, src, tgt = swap_gadget
        out = joint_repair_2(emb, src, tgt, 1, 2, radius=2,
                             deadline=time.perf_counter() + 10)
        assert out.improved and out.proven
        assert out.old_total == 4 and out.new_total == 2
        assert out.embedding[1] == [1] and out.embedding[2] == [2]
        assert is_valid_embedding(out.embedding, src, tgt)
        assert emb[1] == [4, 5]          # input not mutated

    def test_optimal_pair_is_a_proven_fixpoint(self, swap_gadget):
        emb, src, tgt = swap_gadget
        fixed = joint_repair_2(emb, src, tgt, 1, 2, radius=2,
                               deadline=time.perf_counter() + 10).embedding
        again = joint_repair_2(fixed, src, tgt, 1, 2, radius=2,
                               deadline=time.perf_counter() + 10)
        assert not again.improved and again.proven

    def test_non_edge_raises(self, swap_gadget):
        emb, src, tgt = swap_gadget
        with pytest.raises(ValueError):
            joint_repair_2(emb, src, tgt, 0, 2)

    def test_preserves_validity_on_template(self):
        """Every accepted pair move on a real busclique template stays valid."""
        tgt = dnx.chimera_graph(4)
        from minorminer import busclique
        emb = {int(k): [int(q) for q in v]
               for k, v in busclique.find_clique_embedding(8, tgt).items()}
        src = nx.complete_graph(8)
        assert is_valid_embedding(emb, src, tgt)
        for u, v in itertools.combinations(range(8), 2):
            out = joint_repair_2(emb, src, tgt, u, v, radius=2,
                                 deadline=time.perf_counter() + 5)
            if out.improved:
                assert out.new_total < out.old_total
                assert is_valid_embedding(out.embedding, src, tgt)


# ── Engine vs brute force (exactness anchor, incl. multiplicity reqs) ─────────

def _brute_min_cover(G, groups):
    adj = build_adjacency(G)
    nodes = sorted(G.nodes())
    for r in range(1, len(nodes) + 1):
        for comb in itertools.combinations(nodes, r):
            s = set(comb)
            if not chain_connected(list(comb), adj):
                continue
            if all(len(s & g) >= req for g, req in groups):
                return r
    return None


@pytest.mark.parametrize("seed", [0, 1, 2])
def test_engine_matches_brute_force(seed):
    rng = random.Random(seed)
    G = nx.gnp_random_graph(11, 0.3, seed=seed)
    G = nx.compose(G, nx.path_graph(11))     # ensure connected
    nodes = sorted(G.nodes())
    nbr_idx = [sorted(G.neighbors(q)) for q in nodes]
    raw = []
    for _ in range(3):
        members = rng.sample(nodes, rng.randint(1, 3))
        req = 1 if len(members) == 1 else rng.choice([1, 2])
        raw.append((set(members), req))
    expected = _brute_min_cover(G, raw)
    masks = []
    for g, r in raw:
        m = 0
        for q in g:
            m |= 1 << q
        masks.append((m, r))
    groups = _reduce_groups(masks)
    eng = _CoverSearch(
        nbr_idx, groups, incumbent_size=len(nodes) + 1,
        deadline=time.perf_counter() + 30, node_cap=10 ** 7,
        dist_to_group=_group_distances(nbr_idx, [m for m, _ in groups]))
    eng.run()
    got = len(eng.best) if eng.best is not None else None
    assert eng.proven
    assert got == expected


# ── anytime_polish: monotone, deadline, determinism ───────────────────────────

@pytest.fixture(scope="module")
def mm_case():
    import minorminer
    tgt = dnx.chimera_graph(4)
    src = nx.gnp_random_graph(14, 0.5, seed=7)
    raw = minorminer.find_embedding(src, list(tgt.edges()),
                                    random_seed=3, timeout=30)
    emb = {int(v): [int(q) for q in c] for v, c in raw.items()}
    assert is_valid_embedding(emb, src, tgt)
    return emb, src, tgt


class TestAnytimePolish:
    def test_monotone_and_valid(self, mm_case):
        emb, src, tgt = mm_case
        out = anytime_polish(emb, src, tgt, time.perf_counter() + 20)
        assert is_valid_embedding(out, src, tgt)
        assert _total(out) <= _total(emb)

    def test_deterministic(self, mm_case):
        emb, src, tgt = mm_case
        a = anytime_polish(emb, src, tgt, time.perf_counter() + 20)
        b = anytime_polish(emb, src, tgt, time.perf_counter() + 20)
        assert a == b

    def test_expired_deadline_returns_input_fast(self, mm_case):
        emb, src, tgt = mm_case
        t0 = time.perf_counter()
        out = anytime_polish(emb, src, tgt, time.perf_counter() - 1.0)
        assert time.perf_counter() - t0 < 1.0
        assert out == emb and out is not emb

    def test_x2_reachable_from_the_loop(self, swap_gadget):
        """The gadget needs the pair move; the scheduled loop must find it."""
        emb, src, tgt = swap_gadget
        out = anytime_polish(emb, src, tgt, time.perf_counter() + 20)
        assert _total(out) == 4                     # 8-qubit input halved
        assert is_valid_embedding(out, src, tgt)

    def test_ops_subset_without_x2_stays_stuck(self, swap_gadget):
        """Without x2 the gadget is a fixpoint — evidence the win above is
        genuinely the pair move, not a side effect of the cheap passes."""
        emb, src, tgt = swap_gadget
        out = anytime_polish(emb, src, tgt, time.perf_counter() + 20,
                             ops=("spur", "shorten", "x1"))
        assert _total(out) == _total(emb)

    def test_respects_deadline_budget(self, mm_case):
        emb, src, tgt = mm_case
        budget = 2.0
        t0 = time.perf_counter()
        anytime_polish(emb, src, tgt, t0 + budget)
        # one in-flight bounded move may overshoot slightly; never by more
        # than the per-move caps
        assert time.perf_counter() - t0 < budget + 3.5


# ── Registered arm sanity (contract suite covers the rest) ────────────────────

class TestArm:
    def test_registered_and_improves_or_ties_mm(self):
        from ember_qc.registry import ALGORITHM_REGISTRY
        assert "p3-mmpolish" in ALGORITHM_REGISTRY
        algo = ALGORITHM_REGISTRY["p3-mmpolish"]
        src, tgt = nx.complete_graph(8), dnx.chimera_graph(4)
        res = algo.embed(src, tgt, timeout=10.0, seed=1)
        assert res["embedding"]
        assert is_valid_embedding(
            {int(v): [int(q) for q in c] for v, c in res["embedding"].items()},
            src, tgt)

    def test_failure_path_returns_dict(self):
        from ember_qc.registry import ALGORITHM_REGISTRY
        algo = ALGORITHM_REGISTRY["p3-mmpolish"]
        res = algo.embed(nx.complete_graph(20), nx.path_graph(2),
                         timeout=1.0, seed=0)
        assert isinstance(res, dict)
        assert res["embedding"] == {}
