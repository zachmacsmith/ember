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
        # strictly shorten it back
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


class TestHullQuestions:
    """v3 selector: one question per chain from its obligation hull,
    regenerated at the start of every pass."""

    @staticmethod
    def _grid_rev(target):
        from ember_qc.algorithms.factored.field import TileGrid
        from ember_qc.algorithms.factored.placement import target_layout
        grid = TileGrid(target, target_layout(target), courses=True)
        rev = {}
        for (o, ln, s), run in grid.wire_map.items():
            for p, q in run.items():
                rev[q] = (o, ln, s, p)
        return grid, rev

    def test_every_chain_is_an_anchor(self, source, zephyr, finished):
        from ember_qc.algorithms.factored.ball import _hull_balls
        grid, rev = self._grid_rev(zephyr)
        src_adj = {int(v): sorted(source.neighbors(v)) for v in source}
        balls = _hull_balls(finished, src_adj, grid, rev)
        assert balls
        covered = set().union(*map(set, balls))
        for v in source:
            if source.degree(v) >= 1:
                assert v in covered

    def test_hull_contains_footprint_and_targets(self, source, zephyr,
                                                 finished):
        from ember_qc.algorithms.factored.ball import _hull_balls
        grid, rev = self._grid_rev(zephyr)
        src_adj = {int(v): sorted(source.neighbors(v)) for v in source}
        balls = _hull_balls(finished, src_adj, grid, rev)

        def footprint(v):
            ts, cs, rs = set(), set(), set()
            for q in finished[v]:
                o, ln, _s, p = rev[q]
                if o == 1:
                    ts.add((p, ln))
                    rs.add(ln)
                else:
                    ts.add((ln, p))
                    cs.add(ln)
            return ts, sorted(cs), sorted(rs)

        v = next(v for v in sorted(finished) if src_adj.get(v))
        ts, _, _ = footprint(v)
        x0 = min(t[0] for t in ts)
        x1 = max(t[0] for t in ts)
        y0 = min(t[1] for t in ts)
        y1 = max(t[1] for t in ts)
        hx0, hx1, hy0, hy1 = x0, x1, y0, y1
        for u in src_adj[v]:
            _, ucols, urows = footprint(u)
            if ucols:
                t = min(ucols, key=lambda ln: (0 if x0 <= ln <= x1
                                               else min(abs(ln - x0),
                                                        abs(ln - x1)), ln))
                hx0, hx1 = min(hx0, t), max(hx1, t)
            if urows:
                t = min(urows, key=lambda ln: (0 if y0 <= ln <= y1
                                               else min(abs(ln - y0),
                                                        abs(ln - y1)), ln))
                hy0, hy1 = min(hy0, t), max(hy1, t)
        expected = {v}
        for w in finished:
            if w == v:
                continue
            wts, _, _ = footprint(w)
            if any(hx0 <= x <= hx1 and hy0 <= y <= hy1 for (x, y) in wts):
                expected.add(w)
        assert len(expected) >= 2
        assert tuple(sorted(expected)) in balls

    def test_clique_self_gates(self, zephyr):
        # the exact-embed gate's clique layout is already at the
        # constructor family's fixpoint: v3 questions exist every pass
        # but none accepts, and dryness terminates without a deadline
        from ember_qc.algorithms.factored import attract_embed
        k = nx.complete_graph(10)
        r = attract_embed(k, zephyr, timeout=45, seed=0)
        assert r["embedding"]
        assert r["diag"].get("mm_skipped") is True
        emb = {int(v): sorted(int(q) for q in c)
               for v, c in r["embedding"].items()}
        assert validate_embedding(emb, k, zephyr)
        out, info = ball_polish(emb, k, zephyr)
        assert info["accepted"] == 0
        assert info["sweeps"] <= 2
        assert out == emb


class TestBarRebuild:
    """v4 ball rebuild: bars first, router fallback on bars-reject.
    Determinism/validity/never-longer on the winner path are covered by
    TestMove (plain ball_polish calls)."""

    def test_bars_on_pegasus(self, source):
        import minorminer
        import dwave_networkx as dnx
        tgt = dnx.pegasus_graph(4)
        emb = minorminer.find_embedding(source, list(tgt.edges()),
                                        random_seed=5, timeout=30)
        assert emb and validate_embedding(emb, source, tgt)
        emb = {int(v): sorted(int(q) for q in c) for v, c in emb.items()}
        out, info = ball_polish(emb, source, tgt)
        assert validate_embedding(out, source, tgt)
        assert total(out) <= total(emb)


class TestTail:
    def test_tail_arms_valid_deterministic(self, source, zephyr):
        from ember_qc.algorithms.factored import attract_embed
        for tail in ("ball+mm", "ball"):
            a = attract_embed(source, zephyr, timeout=45, seed=0, tail=tail)
            b = attract_embed(source, zephyr, timeout=45, seed=0, tail=tail)
            assert a["embedding"], tail
            assert validate_embedding(a["embedding"], source, zephyr)
            assert a["embedding"] == b["embedding"]
            assert "ball_accepts" in a["diag"]

    def test_ball_only_is_mm_free_when_gate_fires(self):
        import networkx as nx
        from ember_qc.algorithms.factored import attract_embed
        z = dnx.zephyr_graph(3, 4)
        k = nx.complete_graph(10)
        r = attract_embed(k, z, timeout=45, seed=0, tail="ball")
        assert r["embedding"]
        assert validate_embedding(r["embedding"], k, z)
        assert r["diag"].get("mm_skipped") is True
        assert "ball_accepts" in r["diag"]

    def test_tail_default_is_mm_ball(self, source, zephyr):
        from ember_qc.algorithms.factored import attract_embed
        a = attract_embed(source, zephyr, timeout=45, seed=0)
        b = attract_embed(source, zephyr, timeout=45, seed=0,
                          tail="mm+ball")
        assert a["embedding"] == b["embedding"]
        assert "ball_accepts" in a["diag"]
        c = attract_embed(source, zephyr, timeout=45, seed=0, tail="mm")
        assert c["embedding"]
        assert "ball_accepts" not in c["diag"]

    def test_rng_seeded_deterministic_and_valid(self, source, zephyr,
                                                finished):
        a, ia = ball_polish(finished, source, zephyr, rng_seed=5)
        b, ib = ball_polish(finished, source, zephyr, rng_seed=5)
        assert a == b and ia["accepted"] == ib["accepted"]
        assert validate_embedding(a, source, zephyr)
        assert total(a) <= total(finished)
        c, _ = ball_polish(finished, source, zephyr, rng_seed=6)
        assert validate_embedding(c, source, zephyr)

    def test_tail_ball_rng_valid_deterministic(self, source, zephyr):
        from ember_qc.algorithms.factored import attract_embed
        a = attract_embed(source, zephyr, timeout=45, seed=0,
                          tail="ball-rng")
        b = attract_embed(source, zephyr, timeout=45, seed=0,
                          tail="ball-rng")
        assert a["embedding"] and a["embedding"] == b["embedding"]
        assert validate_embedding(a["embedding"], source, zephyr)

    def test_tail_shorten_ball_valid_deterministic(self, source, zephyr):
        from ember_qc.algorithms.factored import attract_embed
        a = attract_embed(source, zephyr, timeout=45, seed=0,
                          tail="shorten+ball")
        b = attract_embed(source, zephyr, timeout=45, seed=0,
                          tail="shorten+ball")
        assert a["embedding"] and a["embedding"] == b["embedding"]
        assert validate_embedding(a["embedding"], source, zephyr)
        assert "ball_accepts" in a["diag"]
