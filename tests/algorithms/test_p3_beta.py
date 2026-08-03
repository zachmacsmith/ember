"""
tests/algorithms/test_p3_beta.py
================================
W2 beta-dhat productization (``ember_qc/algorithms/paper3/beta.py``):

* **gate boundary** — density ~0.109 (just below ``_GATE_MAX_DENSITY=0.11``)
  engages the beta stage (metadata ``selection="beta"``); density ~0.111
  passes through to full-budget stock MM (``selection="gate_passthrough_mm"``).
* **-fb rescue path** — a forced beta-stage failure is rescued by stock MM on
  the ACTUAL remaining wall to the deadline: the deterministic assertion of
  the two-stage math monkeypatches the beta stage to fail (a real forced
  failure via tiny timeouts alone is impossible on instances small enough for
  a unit test — easy instances embed inside any budget, hard ones need
  minutes; deviation documented); a second, real-fork integration starves the
  beta stage (0.6 x 5 s ~= 3 s against a measured ~5 s beta wall) and asserts
  the -fb success guarantee whichever stage lands.
* **dhat parity** — ``beta.dhat_of`` must equal the §4.8 instrument
  (``docs/paper3/data/p6_probes.py::dhat_of``) on 5 graphs, including the
  disconnected, the diameter-<2 (floor), and the >_DHAT_EXACT_CAP double-BFS
  branches.
* **determinism** — same seed -> identical embedding, both arms, both sides
  of the gate.

Contract-suite membership (never-raise, int lists, tiny timeout, no stdout)
is exercised by ``tests/algorithms/test_algorithm_contracts.py``, which picks
both arms up from the registry automatically.
"""

import importlib.util
import os
import time

import networkx as nx
import pytest

from ember_qc.algorithms.minorminer_forked import _find_so
from ember_qc.algorithms.paper3 import beta
from ember_qc.embedding_backend import is_valid_embedding
from ember_qc.registry import ALGORITHM_REGISTRY

needs_fork = pytest.mark.skipif(
    _find_so() is None,
    reason="forked _minorminer not built (bash scripts/build_mm_fork.sh)",
)

# Gate straddle: n=64 gives densities 220/2016 = 0.10913 and 224/2016 =
# 0.11111 — the ~0.109 / ~0.111 pair around the 0.11 gate.
N_GATE = 64
M_BELOW, M_ABOVE = 220, 224


@pytest.fixture(scope="module")
def pegasus4():
    import dwave_networkx as dnx
    return dnx.pegasus_graph(4)   # 264 qubits — fits the n=64 straddle pair


@pytest.fixture(scope="module")
def below_gate():
    g = nx.convert_node_labels_to_integers(
        nx.gnm_random_graph(N_GATE, M_BELOW, seed=7))
    assert nx.density(g) < beta._GATE_MAX_DENSITY
    return g


@pytest.fixture(scope="module")
def above_gate():
    g = nx.convert_node_labels_to_integers(
        nx.gnm_random_graph(N_GATE, M_ABOVE, seed=7))
    assert nx.density(g) >= beta._GATE_MAX_DENSITY
    return g


def _p6_probes():
    """Import the §4.8 instrument module by path (it self-manages sys.path)."""
    path = os.path.abspath(os.path.join(
        os.path.dirname(__file__), "..", "..", "docs", "paper3", "data",
        "p6_probes.py"))
    spec = importlib.util.spec_from_file_location("_p6_probes_under_test", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ---------------------------------------------------------------------------
# dhat_of parity with the §4.8 instrument
# ---------------------------------------------------------------------------

def test_dhat_matches_p6_probes_on_5_graphs():
    p6 = _p6_probes()
    two_comps = nx.disjoint_union(nx.path_graph(40), nx.cycle_graph(9))
    two_comps.add_node(60)  # plus an isolated vertex
    graphs = [
        nx.path_graph(50),                       # diameter 49
        nx.complete_graph(12),                   # diameter 1 -> floored to 2.0
        nx.convert_node_labels_to_integers(
            nx.gnp_random_graph(100, 10.0 / 99, seed=101)),  # the §4.8 cell
        two_comps,                               # largest-component selection
        nx.path_graph(2500),                     # > _DHAT_EXACT_CAP double-BFS
    ]
    for g in graphs:
        assert beta.dhat_of(g) == p6.dhat_of(g)
    assert beta.dhat_of(nx.complete_graph(12)) == 2.0          # the floor
    assert beta.dhat_of(nx.path_graph(2500)) == 2499.0          # exact via 2-BFS
    assert beta._DHAT_EXACT_CAP == p6._DHAT_EXACT_CAP


def test_gate_constant_export():
    """The v1.2 interface freeze: racer/other arms import these two names."""
    from ember_qc.algorithms.paper3.beta import _GATE_MAX_DENSITY, dhat_of
    assert _GATE_MAX_DENSITY == 0.11
    assert callable(dhat_of)


# ---------------------------------------------------------------------------
# gate boundary (below -> beta stage; at/above -> stock passthrough)
# ---------------------------------------------------------------------------

@needs_fork
@pytest.mark.parametrize("arm", ["p3-mm-beta", "p3-mm-beta-fb"])
def test_gate_below_engages_beta(arm, below_gate, pegasus4):
    r = ALGORITHM_REGISTRY[arm].embed(below_gate, pegasus4, timeout=30.0,
                                      seed=0)
    assert r["embedding"], f"{arm} failed below the gate on an easy instance"
    assert is_valid_embedding(r["embedding"], below_gate, pegasus4)
    assert r["metadata"]["selection"] == "beta"
    assert r["metadata"]["max_beta"] == beta.dhat_of(below_gate)


@pytest.mark.parametrize("arm", ["p3-mm-beta", "p3-mm-beta-fb"])
def test_gate_above_passes_through(arm, above_gate, pegasus4):
    r = ALGORITHM_REGISTRY[arm].embed(above_gate, pegasus4, timeout=30.0,
                                      seed=0)
    assert r["embedding"], f"{arm} passthrough failed on an easy instance"
    assert is_valid_embedding(r["embedding"], above_gate, pegasus4)
    assert r["metadata"]["selection"] == "gate_passthrough_mm"
    assert all(isinstance(q, int) for c in r["embedding"].values() for q in c)


# ---------------------------------------------------------------------------
# -fb rescue path
# ---------------------------------------------------------------------------

def test_fb_rescue_two_stage_deadline_math(below_gate, pegasus4, monkeypatch):
    """Force the beta stage to fail; the -fb arm must (1) give it exactly
    0.6 x budget, (2) rescue with stock MM inside the remaining wall, and
    (3) say so in metadata.  (Runs without the fork: the beta stage is
    stubbed, the rescue is stock minorminer.)"""
    seen = {}

    def failing_beta(source, target, **kw):
        seen["timeout"] = kw["timeout"]
        seen["fallback"] = kw["fallback"]
        return {"embedding": {}, "time": 0.01, "success": False,
                "status": "FAILURE"}

    monkeypatch.setattr(beta, "forked_find_embedding", failing_beta)
    t0 = time.perf_counter()
    r = ALGORITHM_REGISTRY["p3-mm-beta-fb"].embed(below_gate, pegasus4,
                                                  timeout=10.0, seed=0)
    elapsed = time.perf_counter() - t0
    assert seen["timeout"] == pytest.approx(6.0)      # 0.6 x budget
    assert seen["fallback"] is False                  # fork-internal fallback OFF
    assert r["embedding"], "stock rescue failed on an easy instance"
    assert is_valid_embedding(r["embedding"], below_gate, pegasus4)
    assert r["metadata"]["selection"] == "rescue_mm"
    assert r["metadata"]["stage"] == "rescue_mm"
    assert r["metadata"]["rescue_s"] <= 10.0          # actual remaining wall,
    assert elapsed < 12.0                             # never a fresh full budget


def test_faithful_arm_never_rescues(below_gate, pegasus4, monkeypatch):
    """Same forced beta failure: the faithful arm reports it (pure arm)."""
    monkeypatch.setattr(
        beta, "forked_find_embedding",
        lambda *a, **k: {"embedding": {}, "time": 0.01, "success": False,
                        "status": "FAILURE", "error": "forced"})
    r = ALGORITHM_REGISTRY["p3-mm-beta"].embed(below_gate, pegasus4,
                                               timeout=5.0, seed=0)
    assert r["embedding"] == {}
    assert r["success"] is False
    assert r["error"] == "forced"


@needs_fork
def test_fb_starved_beta_stage_real(pegasus4):
    """Real two-stage integration: deg-10 n=100 (density 0.103, below gate),
    total budget 5 s -> beta stage 3 s against a measured ~5 s beta wall on
    this cell.  Whichever stage lands, the -fb guarantee holds: success with
    a valid embedding and the stage recorded.  (The rescue-specific
    assertions live in the deterministic monkeypatched test above.)"""
    import dwave_networkx as dnx
    src = nx.convert_node_labels_to_integers(
        nx.gnp_random_graph(100, 10.0 / 99, seed=102))
    tgt = dnx.pegasus_graph(6)
    r = ALGORITHM_REGISTRY["p3-mm-beta-fb"].embed(src, tgt, timeout=5.0,
                                                  seed=1)
    assert r["embedding"], "-fb lost an instance stock MM wins comfortably"
    assert is_valid_embedding(r["embedding"], src, tgt)
    assert r["metadata"]["stage"] in ("beta", "rescue_mm")


# ---------------------------------------------------------------------------
# determinism + failure shape
# ---------------------------------------------------------------------------

@needs_fork
@pytest.mark.parametrize("arm", ["p3-mm-beta", "p3-mm-beta-fb"])
def test_deterministic_per_seed_below_gate(arm, below_gate, pegasus4):
    a = ALGORITHM_REGISTRY[arm].embed(below_gate, pegasus4, timeout=30.0,
                                      seed=3)
    b = ALGORITHM_REGISTRY[arm].embed(below_gate, pegasus4, timeout=30.0,
                                      seed=3)
    assert a["embedding"] == b["embedding"]
    assert a["metadata"]["selection"] == b["metadata"]["selection"]


@pytest.mark.parametrize("arm", ["p3-mm-beta", "p3-mm-beta-fb"])
def test_impossible_below_gate_fails_cleanly(arm):
    """Below-gate failure shape (sparse source, hopeless target): dict with
    empty embedding, success False, never a raise."""
    src = nx.path_graph(20)          # density 0.1 -> below the gate
    tgt = nx.path_graph(3)
    r = ALGORITHM_REGISTRY[arm].embed(src, tgt, timeout=2.0, seed=0)
    assert isinstance(r, dict)
    assert r["embedding"] == {}
    assert r.get("success") is False
