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
    RACE9_SPEC,
    _arm_seed,
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


# ── race9 (v1.2): roster append, mm-beta preflight, terminal polish ──────────

def _pin_fork_absent(monkeypatch):
    """Pin the mm fork .so ABSENT so fork-dependent arms (cuthill, mm-beta)
    are deterministically skipped regardless of the running environment."""
    import ember_qc.algorithms.minorminer_forked as mf
    monkeypatch.setattr(mf, "_find_so", lambda: None)


def test_race9_spec_preserves_race8_seed_derivations():
    """Arms 0-7 of RACE9_SPEC are byte-identical to RACE8_SPEC — same kinds,
    same params, same _arm_seed derivations at any master seed — so race9 vs
    race8 at one master seed is a clean paired A/B (notes §4.15 T1d)."""
    assert tuple(RACE9_SPEC[:8]) == tuple(RACE8_SPEC)
    assert len(RACE9_SPEC) == 9
    assert RACE9_SPEC[8] == ("mm-beta", {})
    for master in (0, 1, 7, 42, 12345):
        a8 = [(kind, dict(params), _arm_seed(master, i))
              for i, (kind, params) in enumerate(RACE8_SPEC)]
        a9 = [(kind, dict(params), _arm_seed(master, i))
              for i, (kind, params) in enumerate(RACE9_SPEC)]
        assert a9[:8] == a8


def test_race9_mm_beta_skipped_without_fork(monkeypatch):
    """Without the fork .so, the mm-beta arm is marked skipped, spends no
    budget (empty trajectory), and the rest of the roster still races."""
    _pin_fork_absent(monkeypatch)
    r = race(K6, C4, 4.0, seed=0, arms_spec=RACE9_SPEC, n_workers=1)
    beta = [a for a in r["arms"] if a["kind"] == "mm-beta"]
    assert len(beta) == 1
    assert beta[0]["index"] == 8
    assert beta[0]["status"] == "skipped:fork-unavailable"
    assert beta[0]["trajectory"] == []
    cut = [a for a in r["arms"] if a["kind"] == "cuthill"]
    assert cut[0]["status"] == "skipped:fork-unavailable"
    assert r["success"]
    assert is_valid_embedding(r["embedding"], K6, C4)


def test_terminal_polish_monotone():
    """Converged-early scenario (K6/C4: every polish quantum trips patience,
    the race ends ~2 s into a 12 s budget => real leftover wall): the
    terminal polish ENGAGES (nonzero accounting), and never worsens the
    winner — result ACL <= the best pre-polish arm ACL."""
    r = race(K6, C4, 12.0, seed=3, arms_spec=RACE9_SPEC, n_workers=1,
             terminal_polish=True)
    assert r["success"]
    assert is_valid_embedding(r["embedding"], K6, C4)
    assert r["budget"]["terminal_polish_s"] > 0.0   # it actually ran
    acl_before = min(a["acl_best"] for a in r["arms"]
                     if a["acl_best"] is not None)
    assert r["acl"] <= acl_before + 1e-9


def test_terminal_polish_budget_exhausted_honest():
    """When the race consumes its whole budget (ER(20,0.3)/C4 never trips
    patience at this scale) the polish spends only what is left — total wall
    stays budget-honest and the result is still monotone vs the arms."""
    src = _er(20, 0.3, 101)
    r = race(src, C4, 10.0, seed=1, arms_spec=RACE9_SPEC, n_workers=1,
             terminal_polish=True)
    assert r["success"]
    assert is_valid_embedding(r["embedding"], src, C4)
    assert "terminal_polish_s" in r["budget"]
    assert r["budget"]["terminal_polish_s"] >= 0.0
    acl_before = min(a["acl_best"] for a in r["arms"]
                     if a["acl_best"] is not None)
    assert r["acl"] <= acl_before + 1e-9
    assert r["elapsed_s"] <= 13.0


def test_terminal_polish_validate_false_lazy_adj():
    """validate=False leaves adj unbuilt during the race; the terminal-polish
    block builds it lazily (converged-early case so the block really runs)
    and the returned embedding is still valid."""
    r = race(K6, C4, 12.0, seed=2, arms_spec=RACE8_SPEC, n_workers=1,
             validate=False, terminal_polish=True)
    assert r["success"]
    assert r["budget"]["terminal_polish_s"] > 0.0   # lazy-adj path exercised
    assert is_valid_embedding(r["embedding"], K6, C4)


# race8 freeze: recorded on 2026-08-03 at paper3 2161c9dc (PRE-race9 code)
# by scratchpad/record_race8.py — race(K6, C4, 60.0, seed=3, RACE8_SPEC,
# n_workers=1) with the fork pinned absent. Every stage ends on its own
# stopping rule at this scale (module docstring), so the projection below is
# machine-independent. p3-race9's roster/polish must not move ANY of it.
_RACE8_FROZEN = {
    "acl": 2.3333,
    "winner": {"index": 0, "kind": "template", "stage": "template"},
    "final_survivor": 1,
    "template_acl": 2.3333,
    "embedding": {0: [0, 32], 1: [33, 38], 2: [34, 39], 3: [7, 3, 35],
                  4: [36, 44], 5: [37, 45, 41]},
    "arms": [
        {"index": 0, "kind": "template", "status": "floor",
         "acl_best": 2.3333, "converged": False},
        {"index": 1, "kind": "mm", "status": "final",
         "acl_best": 2.3333, "converged": True},
        {"index": 2, "kind": "mm", "status": "survivor",
         "acl_best": 2.3333, "converged": True},
        {"index": 3, "kind": "mm", "status": "survivor",
         "acl_best": 2.3333, "converged": True},
        {"index": 4, "kind": "mm", "status": "dropped:r1",
         "acl_best": 2.3333, "converged": True},
        {"index": 5, "kind": "cuthill", "status": "skipped:fork-unavailable",
         "acl_best": None, "converged": False},
        {"index": 6, "kind": "clmm", "status": "dropped:r1",
         "acl_best": 2.3333, "converged": True},
        {"index": 7, "kind": "clmm-core", "status": "dropped:r1",
         "acl_best": 2.3333, "converged": True},
    ],
    "rounds": [
        {"round": 1, "survivors_in": [6, 7, 1, 2, 3, 4],
         "dropped": [4, 6, 7], "survivors_out": [1, 2, 3],
         "acl_best": {1: 2.3333, 2: 2.3333, 3: 2.3333}},
    ],
    "budget_keys": ["elapsed_s", "final_s", "legalize_s", "rounds_s",
                    "template_s", "total_s"],
}


def test_race8_result_frozen_pre_post_race9(monkeypatch):
    """M4-freeze regression: race() with RACE8_SPEC (terminal_polish left at
    its default) reproduces the recorded PRE-race9 result exactly — the
    embedding, winner, survivor structure, and (crucially) the budget
    accounting keys, which must NOT gain terminal_polish_s."""
    _pin_fork_absent(monkeypatch)
    r = race(K6, C4, 60.0, seed=3, arms_spec=RACE8_SPEC, n_workers=1)
    assert r["acl"] == _RACE8_FROZEN["acl"]
    assert r["winner"] == _RACE8_FROZEN["winner"]
    assert r["final_survivor"] == _RACE8_FROZEN["final_survivor"]
    assert r["template"]["acl"] == _RACE8_FROZEN["template_acl"]
    assert {int(k): list(v) for k, v in r["embedding"].items()} == \
        _RACE8_FROZEN["embedding"]
    got_arms = [{"index": a["index"], "kind": a["kind"],
                 "status": a["status"], "acl_best": a["acl_best"],
                 "converged": a["converged"]} for a in r["arms"]]
    assert got_arms == _RACE8_FROZEN["arms"]
    got_rounds = [{"round": x["round"], "survivors_in": x["survivors_in"],
                   "dropped": x["dropped"],
                   "survivors_out": x["survivors_out"],
                   "acl_best": x["acl_best"]} for x in r["rounds"]]
    assert got_rounds == _RACE8_FROZEN["rounds"]
    assert sorted(r["budget"].keys()) == _RACE8_FROZEN["budget_keys"]


def test_race9_tiny_timeout_safe():
    algo = ALGORITHM_REGISTRY["p3-race9"]
    t0 = time.perf_counter()
    r = algo.embed(K6, C4, timeout=1.0, seed=0)
    wall = time.perf_counter() - t0
    assert wall < 5.0
    assert r["metadata"]["mode"] == "tiny"
    assert is_valid_embedding(r["embedding"], K6, C4)


def test_race9_full_race_mode():
    algo = ALGORITHM_REGISTRY["p3-race9"]
    src = _er(20, 0.3, 101)
    t0 = time.perf_counter()
    r = algo.embed(src, C4, timeout=8.0, seed=1)
    wall = time.perf_counter() - t0
    assert wall <= 11.0
    assert r["metadata"]["mode"] == "race"
    assert is_valid_embedding(r["embedding"], src, C4)
    assert r["metadata"]["winner"] is not None
    assert "terminal_polish_s" in r["metadata"]["budget"]
    arms = r["metadata"]["arms"]
    assert len(arms) == 9
    assert arms[8]["kind"] == "mm-beta"
