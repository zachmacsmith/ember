"""p3-mm-beta-mf (v1.3 W-A) unit tests — §4.17 design properties.

The contract suite auto-covers determinism/validity/no-stdout; these pin the
mm-first mechanism: gate passthrough, mm-failure identity, leftover beta,
strict lower-ACL selection (tie -> MM), and defensive beta-stage failure.
"""
from __future__ import annotations

import networkx as nx
import dwave_networkx as dnx
import pytest

from ember_qc.algorithms.paper3 import beta_mf
from ember_qc.embedding_backend import is_valid_embedding

TGT = dnx.zephyr_graph(3)

# below-gate source (realized density ~0.097 < 0.11): deg-6 at n=60 embeds
# in Z3 in well under a second, so every mechanism path is reachable fast.
# (deg-10 at n=100 — the ladder's straddle point — does NOT fit Z3; the T3
# ladder runs it on Z12.)
def _sparse60():
    return nx.gnp_random_graph(60, 6.0 / 59, seed=101)



def _run(src, timeout=20.0, seed=0):
    return beta_mf.P3MMBetaMF().embed(src, TGT, timeout=timeout, seed=seed)


def test_gate_passthrough_above_threshold():
    src = nx.gnp_random_graph(30, 0.3, seed=2)   # density 0.3 >= 0.11
    r = _run(src)
    assert r["metadata"]["selection"] == "gate_passthrough_mm"
    assert is_valid_embedding(
        {int(k): v for k, v in r["embedding"].items()}, src, TGT)


def test_below_gate_success_and_selection_fields():
    src = _sparse60()    # density ~0.10 — below the gate; easy in Z3
    r = _run(src, timeout=20.0)
    md = r["metadata"]
    assert md["gate_density"] < beta_mf._GATE_MAX_DENSITY
    assert md["selection"] in ("mm", "beta")
    assert md["stage"] == "mm+beta"
    assert md["mm_wall"] > 0
    emb = {int(k): v for k, v in r["embedding"].items()}
    assert is_valid_embedding(emb, src, TGT)
    if md["selection"] == "beta":
        assert md["acl_beta"] < md["acl_mm"]
        assert abs(beta_mf._acl(emb) - md["acl_beta"]) < 1e-3  # md rounded
    else:
        assert abs(beta_mf._acl(emb) - md["acl_mm"]) < 1e-3    # md rounded


def test_mm_failure_is_stock_failure(monkeypatch):
    src = _sparse60()
    calls = {"n": 0}

    def failing_stock(source, target, timeout, seed, t0, meta):
        calls["n"] += 1
        return beta_mf._fail(t0, "forced")

    monkeypatch.setattr(beta_mf, "_stock_mm", failing_stock)
    r = _run(src)
    assert r["success"] is False and r["embedding"] == {}
    assert calls["n"] == 1                     # exactly the one stock call
    assert r["metadata"]["selection"] == "mm_failed"


def test_beta_stage_exception_keeps_mm_result(monkeypatch):
    src = _sparse60()

    def boom(*a, **k):
        raise RuntimeError("forced beta failure")

    monkeypatch.setattr(beta_mf, "forked_find_embedding", boom)
    r = _run(src, timeout=20.0)
    md = r["metadata"]
    assert md["selection"] == "mm"
    emb = {int(k): v for k, v in r["embedding"].items()}
    assert is_valid_embedding(emb, src, TGT)


def test_tie_goes_to_mm(monkeypatch):
    src = _sparse60()
    captured = {}
    real = beta_mf._stock_mm

    def spying_stock(source, target, timeout, seed, t0, meta):
        out = real(source, target, timeout, seed, t0, meta)
        captured["emb"] = out.get("embedding") or {}
        return out

    def same_acl_beta(*a, **k):                # returns MM's own embedding
        return {"embedding": dict(captured["emb"]), "time": 0.01}

    monkeypatch.setattr(beta_mf, "_stock_mm", spying_stock)
    monkeypatch.setattr(beta_mf, "forked_find_embedding", same_acl_beta)
    r = _run(src, timeout=20.0)
    assert r["metadata"]["selection"] == "mm"   # strict <: tie stays with MM


def test_small_budget_stays_bounded():
    # any leftover >= the 1 s floor legally runs beta — the invariant is the
    # deadline: total wall <= budget + scheduling slack, result valid.
    src = _sparse60()
    r = _run(src, timeout=1.2)
    assert r["time"] <= 3.0
    if r.get("embedding"):
        emb = {int(k): v for k, v in r["embedding"].items()}
        assert is_valid_embedding(emb, src, TGT)


def test_isolated_vertices_survive():
    src = _sparse60()
    src.add_nodes_from([97, 98, 99])            # isolated
    r = _run(src, timeout=20.0)
    emb = {int(k): v for k, v in r["embedding"].items()}
    assert set(emb) == set(int(v) for v in src.nodes)
    assert is_valid_embedding(emb, src, TGT)


@pytest.mark.parametrize("seed", [0, 1])
def test_deterministic_per_seed(seed):
    src = _sparse60()
    a = _run(src, timeout=8.0, seed=seed)
    b = _run(src, timeout=8.0, seed=seed)
    assert a["embedding"] == b["embedding"]
    assert a["metadata"]["selection"] == b["metadata"]["selection"]
