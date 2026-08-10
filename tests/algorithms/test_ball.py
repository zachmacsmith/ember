"""Invariant tests for ball_polish (docs/paper2 s3.74 build round).

The two tests that matter most were fixed before any benchmark ran:
identity-flavored no-ops (invalid input, empty input) and idempotence
(a second pass on ball_polish's own fixpoint accepts nothing). These
catch the classic rot modes of ruin-and-recreate mechanisms — background
accounting drift and oscillation — structurally.
"""

import networkx as nx
import pytest

import dwave_networkx as dnx

from ember_qc.algorithms.factored import ball_polish, spur_prune
from ember_qc.algorithms.factored.ball import _rebuild_ball, _trim_ball
from ember_qc.embedding_backend import build_adjacency, is_valid_embedding
from ember_qc.registry import validate_embedding


@pytest.fixture(scope="module")
def zephyr():
    return dnx.zephyr_graph(3, 4)


@pytest.fixture(scope="module")
def source():
    return nx.gnp_random_graph(14, 0.35, seed=11)


@pytest.fixture(scope="module")
def finished(source, zephyr):
    import minorminer
    emb = minorminer.find_embedding(source, list(zephyr.edges()),
                                    random_seed=3, timeout=30)
    assert emb and validate_embedding(emb, source, zephyr)
    return {int(v): sorted(int(q) for q in c) for v, c in emb.items()}


def total(emb):
    return sum(len(c) for c in emb.values())


class TestGuards:
    def test_empty_input_unchanged(self, source, zephyr):
        out, info = ball_polish({}, source, zephyr)
        assert out == {} and info["invalid_input"]

    def test_invalid_input_unchanged(self, source, zephyr, finished):
        broken = dict(finished)
        broken.pop(sorted(broken)[0])  # uncovered vertex -> invalid
        out, info = ball_polish(broken, source, zephyr)
        assert out == broken and info["invalid_input"]


class TestMove:
    def test_valid_and_never_longer(self, source, zephyr, finished):
        out, info = ball_polish(finished, source, zephyr)
        assert validate_embedding(out, source, zephyr)
        assert total(out) <= total(finished)
        assert info["tried"] >= info["accepted"]

    def test_deterministic(self, source, zephyr, finished):
        a, ia = ball_polish(finished, source, zephyr)
        b, ib = ball_polish(finished, source, zephyr)
        assert a == b
        assert ia["accepted"] == ib["accepted"]

    def test_idempotent_at_fixpoint(self, source, zephyr, finished):
        once, _ = ball_polish(finished, source, zephyr)
        twice, info = ball_polish(once, source, zephyr)
        assert twice == once
        assert info["accepted"] == 0

    def test_constructed_improvement(self):
        # a path source embedded, then made deliberately wasteful by
        # padding one chain with free connected qubits; the move must
        # strictly shorten it back (the source must be big enough for
        # unit balls to exist: coarsen skips sources <= 8 nodes)
        target = dnx.chimera_graph(3, 3, 4)
        source = nx.path_graph(12)
        import minorminer
        emb = minorminer.find_embedding(source, list(target.edges()),
                                        random_seed=1, timeout=10)
        assert emb and validate_embedding(emb, source, target)
        emb = {int(v): sorted(int(q) for q in c) for v, c in emb.items()}
        adj = build_adjacency(target)
        used = set().union(*emb.values())
        v0 = sorted(emb)[0]
        pad = [q for q in emb[v0]
               for w in adj[q] if w not in used][:1]
        assert pad, "no free qubit adjacent to the first chain"
        free_nbr = next(w for q in emb[v0] for w in adj[q]
                        if w not in used)
        emb[v0] = sorted(emb[v0] + [free_nbr])
        assert validate_embedding(emb, source, target)
        out, _ = ball_polish(emb, source, target)
        assert validate_embedding(out, source, target)
        assert total(out) < total(emb)


class TestHelpers:
    def test_trim_drops_isolated_and_interior_components(self):
        # source: triangle 0-1-2 plus edge 3-4 plus isolated 5
        src_adj = {0: [1, 2], 1: [0, 2], 2: [0, 1], 3: [4], 4: [3], 5: []}
        # ball = whole graph: no component touches outside -> ()
        assert _trim_ball((0, 1, 2, 3, 4, 5), src_adj) == ()
        # ball = {0, 1}: touches 2 outside -> kept, isolated 5 dropped
        assert _trim_ball((0, 1, 5), src_adj) == (0, 1)

    def test_rebuild_rejects_cleanly_on_deadline(self, source, zephyr,
                                                 finished):
        import time
        adj = build_adjacency(zephyr)
        src_adj = {int(v): sorted(source.neighbors(v)) for v in source}
        S = _trim_ball(tuple(sorted(source)[:3]), src_adj)
        if not S:
            pytest.skip("trim emptied the ball on this instance")
        out = _rebuild_ball(S, finished, src_adj, adj, [0],
                            time.perf_counter() - 1.0)
        assert out is None

    def test_contract_stable_off_is_default(self, source):
        # off-switch identity on the continuous control arm (v4: the
        # contraction phase only exists when order_state=False)
        from ember_qc.algorithms.factored import attract_embed
        chim = dnx.chimera_graph(4, 4, 4)
        a = attract_embed(source, chim, timeout=60, seed=0,
                          order_state=False)
        b = attract_embed(source, chim, timeout=60, seed=0,
                          order_state=False, contract_stable=False)
        assert a["embedding"] and a["embedding"] == b["embedding"]
        assert a["stair_E"] == b["stair_E"]
        assert "contract_steps" not in a["diag"]

    def test_contract_stable_on_valid_and_capped(self, source):
        from ember_qc.algorithms.factored import attract_embed
        chim = dnx.chimera_graph(4, 4, 4)
        r = attract_embed(source, chim, timeout=60, seed=0,
                          order_state=False, contract_stable=True)
        assert r["embedding"]
        assert validate_embedding(r["embedding"], source, chim)
        steps = r["diag"]["contract_steps"]
        assert 1 <= steps <= 4 + 4  # cap = grid.W + grid.H on C4

    def test_spur_prune_only_restricts(self, source, zephyr, finished):
        pruned_all = spur_prune(finished, {int(v): sorted(source.neighbors(v))
                                           for v in source},
                                build_adjacency(zephyr))
        keys = sorted(finished)
        sub = keys[:2]
        pruned_sub = spur_prune(finished,
                                {int(v): sorted(source.neighbors(v))
                                 for v in source},
                                build_adjacency(zephyr), only=sub)
        for v in keys:
            if v not in sub:
                assert pruned_sub[v] == finished[v]
        assert is_valid_embedding(pruned_sub, source, zephyr)
        assert is_valid_embedding(pruned_all, source, zephyr)
