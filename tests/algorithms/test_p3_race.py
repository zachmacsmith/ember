"""P3 racer tests (ember_qc/algorithms/paper3/race.py).

Covers the library contract promised in docs/paper3/proposals/portfolio.md:
wall-clock budget honesty of the sequential race, determinism given
(seed, arms_spec), successive halving actually shrinking the survivor set,
the template floor being recorded, validity of the returned embedding, and
budget honesty of the protocol-rule-2 baseline (race_baseline_bestofk).
The registered arm p3-race8 is additionally covered by the general contract
suite (tests/algorithms/test_algorithm_contracts.py); here we only exercise
its two modes (tiny-timeout degradation and full race mode).

Scales are kept small (chimera_graph(4)/pegasus_graph(4) targets, small ER
sources) so the whole file runs in about a minute.
"""

import time

import networkx as nx
import dwave_networkx as dnx
import pytest

from ember_qc.registry import ALGORITHM_REGISTRY
from ember_qc.embedding_backend import is_valid_embedding
from ember_qc.algorithms.paper3.race import (
    RACE8_SPEC,
    race,
    race_baseline_bestofk,
)

C4 = dnx.chimera_graph(4)
P4 = dnx.pegasus_graph(4)
K6 = nx.complete_graph(6)


def _er(n, p, seed):
    return nx.convert_node_labels_to_integers(
        nx.gnp_random_graph(n, p, seed=seed))


ER40 = _er(40, 0.25, 101)   # dev-registry instance seed (protocol rule 4)


@pytest.fixture(scope="module")
def race12():
    """One 12 s sequential race on ER(40, 0.25)/P4, shared by the budget,
    halving, and validity tests (runs once per module)."""
    t0 = time.perf_counter()
    result = race(ER40, P4, 12.0, seed=0, arms_spec=RACE8_SPEC, n_workers=1)
    wall = time.perf_counter() - t0
    return result, wall


# ── budget honesty ────────────────────────────────────────────────────────────

def test_budget_honesty_sequential(race12):
    result, wall = race12
    # 12 s budget; slack covers the cooperative overshoot of the last MM call.
    assert wall <= 15.0, f"sequential race took {wall:.2f}s on a 12s budget"
    assert result["elapsed_s"] <= 15.0
    assert result["budget"]["total_s"] == 12.0


def test_baseline_budget_honest():
    t0 = time.perf_counter()
    b = race_baseline_bestofk(ER40, P4, 6.0, seed=0, K=4)
    wall = time.perf_counter() - t0
    assert wall <= 9.0, f"baseline took {wall:.2f}s on a 6s budget"
    assert b["K"] == 4
    assert len(b["runs"]) == 4
    assert b["success"]
    assert isinstance(b["acl"], float)
    assert is_valid_embedding(b["embedding"], ER40, P4)
    # best_run really is the argmin of the recorded raw ACLs
    acls = [r["acl"] for r in b["runs"] if r["acl"] is not None]
    assert min(acls) == b["runs"][b["best_run"]]["acl"] == b["acl"]


# ── race mechanics ────────────────────────────────────────────────────────────

def test_valid_output(race12):
    result, _ = race12
    assert result["success"]
    assert is_valid_embedding(result["embedding"], ER40, P4)
    for chain in result["embedding"].values():
        assert isinstance(chain, list)
        assert all(isinstance(q, int) for q in chain)


def test_halving_actually_drops_arms(race12):
    result, _ = race12
    rounds = result["rounds"]
    assert len(rounds) >= 2, "expected at least two halving rounds at 12s"
    sizes = [len(r["survivors_in"]) for r in rounds]
    assert sizes == sorted(sizes, reverse=True)
    for r in rounds:
        assert len(r["dropped"]) >= 1, f"round {r['round']} dropped nobody"
        assert len(r["survivors_out"]) == \
            len(r["survivors_in"]) - len(r["dropped"])
    assert len(rounds[-1]["survivors_out"]) == 1
    assert result["final_survivor"] == rounds[-1]["survivors_out"][0]
    # dropped arms carry the round they died in
    dropped = [a for a in result["arms"] if a["status"].startswith("dropped:")]
    assert len(dropped) >= 3


def test_template_floor_present(race12):
    result, _ = race12
    tv = result["template"]
    assert tv is not None
    assert isinstance(tv["acl"], float)
    tmpl_arm = result["arms"][0]
    assert tmpl_arm["kind"] == "template"
    assert tmpl_arm["status"] == "floor"
    # the floor competes: global best is never worse than the template
    assert result["acl"] <= tv["acl"] + 1e-9
    # and the template is never polished (exactly one trajectory entry)
    assert len(tmpl_arm["trajectory"]) == 1


def test_arm_trajectories_recorded(race12):
    result, _ = race12
    racing = [a for a in result["arms"]
              if a["kind"] != "template" and not a["status"].startswith("skip")]
    assert racing, "no racing arms ran"
    for a in racing:
        stages = [t["stage"] for t in a["trajectory"]]
        assert stages[0] == "legalize"
        # acl_best is monotone non-increasing along the trajectory
        bests = [t["acl_best"] for t in a["trajectory"]
                 if t["acl_best"] is not None]
        assert bests == sorted(bests, reverse=True)
    # the final survivor polished more quanta than a first-round casualty
    surv = next(a for a in result["arms"]
                if a["index"] == result["final_survivor"])
    assert len(surv["trajectory"]) >= 3


def test_determinism():
    r1 = race(K6, C4, 60.0, seed=3, arms_spec=RACE8_SPEC, n_workers=1)
    r2 = race(K6, C4, 60.0, seed=3, arms_spec=RACE8_SPEC, n_workers=1)
    assert r1["embedding"] == r2["embedding"]
    assert r1["acl"] == r2["acl"]
    assert r1["winner"] == r2["winner"]
    assert [a["acl_best"] for a in r1["arms"]] == \
        [a["acl_best"] for a in r2["arms"]]


# ── registered arm ────────────────────────────────────────────────────────────

def test_race8_tiny_timeout_safe():
    algo = ALGORITHM_REGISTRY["p3-race8"]
    t0 = time.perf_counter()
    r = algo.embed(K6, C4, timeout=1.0, seed=0)
    wall = time.perf_counter() - t0
    assert wall < 5.0
    assert r["metadata"]["mode"] == "tiny"
    assert is_valid_embedding(r["embedding"], K6, C4)


def test_race8_full_race_mode():
    algo = ALGORITHM_REGISTRY["p3-race8"]
    src = _er(20, 0.3, 101)
    t0 = time.perf_counter()
    r = algo.embed(src, C4, timeout=8.0, seed=1)
    wall = time.perf_counter() - t0
    assert wall <= 11.0
    assert r["metadata"]["mode"] == "race"
    assert is_valid_embedding(r["embedding"], src, C4)
    assert r["metadata"]["winner"] is not None
    assert "rounds" in r["metadata"] and "trajectories" in r["metadata"]
