"""
ember_qc/algorithms/paper3/beta.py
===================================
W2 — productized beta-dhat: the confirmed sparse-regime finite-beta pricing
win (improvement-notes item 4; evidence notes.md §4.8/§4.8b: the 2014 paper's
own D^occ pricing beats shipped minorminer's lexicographic overlap pricing by
-2.6/-3.9/-5.0% median ACL on deg-10 ER n in {100,140,180} at 63-87% win
rates, at a real feasibility cost — success 64/75 at n=180).

Two registered arms (both version 1.0.0):

``p3-mm-beta`` — the faithful arm.  Below the density gate: ONE engaged
    ``forked_find_embedding(max_beta=dhat_of(source), fallback=False)`` run on
    the full budget (pure — failures are reported, never rescued).  At/above
    the gate: full-budget stock-MM passthrough (the p3-clmm guard precedent),
    metadata ``selection="gate_passthrough_mm"`` — the arm is exactly
    minorminer off-regime.

``p3-mm-beta-fb`` — the product arm (protocol: internal fallback carries an
    explicit ``-fb`` suffix).  Below the gate the beta attempt gets 0.6x the
    budget; an empty/invalid result is rescued by stock
    ``minorminer.find_embedding`` on the ACTUAL remaining wall to the
    deadline — the two-stage deadline math lives HERE, not in the fork's
    internal fallback (whose 1 s floor can overshoot the deadline).  At/above
    the gate: passthrough.  Metadata records the stage used
    (``beta`` / ``rescue_mm`` / ``gate_passthrough_mm``).

Gate: ``_GATE_MAX_DENSITY = 0.11`` — NOT 0.10: the measured n=100 win sits at
deg-10 density 10/99 ~= 0.101 (§4.8b), which a 0.10 gate would exclude.

``dhat_of`` is lifted VERBATIM from ``docs/paper3/data/p6_probes.py`` (the
§4.8 instrument): exact ``nx.diameter`` of the largest connected component,
double-BFS eccentricity lower bound above ``_DHAT_EXACT_CAP`` nodes, floored
at 2.0.  ``tests/algorithms/test_p3_beta.py`` pins the two implementations
equal; racer/other consumers import ``dhat_of`` and ``_GATE_MAX_DENSITY``
from this module (the v1.2 interface freeze).

Contract: never raises; plain int chain lists; tiny-timeout safe; same seed
-> same output; no stdout.  Fork not built: ``is_available`` reports it, and
a below-gate ``embed`` still returns the fork wrapper's clean failure dict.
"""
from __future__ import annotations

import logging
import time
from typing import List

import networkx as nx

from ember_qc.registry import EmbeddingAlgorithm, register_algorithm
from ember_qc.algorithms.minorminer_forked import (
    _FORK_DIR,
    _find_so,
    forked_find_embedding,
)

logger = logging.getLogger(__name__)

_GATE_MAX_DENSITY = 0.11   # engage finite beta strictly below this density
_BETA_BUDGET_FRAC = 0.6    # -fb only: the beta stage's share of the budget
_RESCUE_FLOOR_S = 0.05     # -fb only: minimum rescue window (tiny timeouts)
_DHAT_EXACT_CAP = 2000     # above this, double-BFS estimate (never at n<=180)


def dhat_of(src: nx.Graph) -> float:
    if src.number_of_nodes() == 0:
        return 2.0
    comp = max(nx.connected_components(src), key=len)
    sub = src.subgraph(comp)
    if sub.number_of_nodes() <= 2:
        d = 1
    elif sub.number_of_nodes() > _DHAT_EXACT_CAP:
        # double-BFS eccentricity lower bound (cost cap; never at n<=180)
        v0 = min(sub.nodes())
        d1 = nx.single_source_shortest_path_length(sub, v0)
        far = max(d1, key=lambda v: (d1[v], v))
        d2 = nx.single_source_shortest_path_length(sub, far)
        d = max(d2.values())
    else:
        d = nx.diameter(sub)
    return float(max(2.0, d))


def _fail(t0: float, msg: str, status: str = "FAILURE") -> dict:
    return {"embedding": {}, "time": time.perf_counter() - t0,
            "success": False, "status": status, "error": msg}


def _stock_mm(source_graph, target_graph, timeout, seed, t0, meta) -> dict:
    """One full stock-minorminer run (the p3-clmm passthrough precedent).

    The source goes in as the GRAPH OBJECT so isolated vertices survive
    (edge-list input silently drops them — the §3.23 bug class)."""
    try:
        import minorminer
        raw = minorminer.find_embedding(
            source_graph, list(target_graph.edges()),
            timeout=max(0.001, float(timeout)), random_seed=int(seed),
            verbose=0)
        if not raw:
            return _fail(t0, "stock MM stage returned empty")
        emb = {int(w): [int(q) for q in c] for w, c in raw.items()}
        return {"embedding": emb, "time": time.perf_counter() - t0,
                "metadata": meta}
    except Exception as e:  # contract: never raise
        logger.error("p3-mm-beta stock stage error: %s", e)
        return _fail(t0, str(e))


def _is_valid(emb, source_graph, target_graph) -> bool:
    try:
        from ember_qc.embedding_backend import is_valid_embedding
        return bool(is_valid_embedding(emb, source_graph, target_graph))
    except Exception:
        return False


def _beta_embed(source_graph, target_graph, timeout: float, seed: int,
                fb: bool) -> dict:
    """Gate -> beta stage -> (fb only) stock rescue on the remaining wall."""
    t0 = time.perf_counter()
    deadline = t0 + timeout
    try:
        density = float(nx.density(source_graph))
        gmeta = {"gate_density": round(density, 6),
                 "gate_threshold": _GATE_MAX_DENSITY}
        if density >= _GATE_MAX_DENSITY:
            meta = dict(gmeta, selection="gate_passthrough_mm",
                        stage="gate_passthrough_mm")
            return _stock_mm(source_graph, target_graph, timeout, seed, t0,
                             meta)

        dhat = dhat_of(source_graph)
        stage_t = _BETA_BUDGET_FRAC * timeout if fb else timeout
        r = forked_find_embedding(source_graph, target_graph, max_beta=dhat,
                                  seed=int(seed), timeout=stage_t,
                                  fallback=False)
        emb = r.get("embedding") or {}
        if not fb:  # faithful: the engaged run's outcome IS the arm's outcome
            if emb:
                return {"embedding": emb, "time": time.perf_counter() - t0,
                        "metadata": dict(gmeta, selection="beta",
                                         stage="beta", max_beta=dhat)}
            return _fail(t0, r.get("error", "beta stage returned empty"),
                         r.get("status", "FAILURE"))

        if emb and _is_valid(emb, source_graph, target_graph):
            return {"embedding": emb, "time": time.perf_counter() - t0,
                    "metadata": dict(gmeta, selection="beta", stage="beta",
                                     max_beta=dhat)}
        # Stage 2: stock rescue on the ACTUAL remaining wall to the deadline
        # (floored only for degenerate tiny budgets) — NOT the fork's internal
        # fallback and NOT a fresh full budget.
        remaining = max(_RESCUE_FLOOR_S, deadline - time.perf_counter())
        meta = dict(gmeta, selection="rescue_mm", stage="rescue_mm",
                    max_beta=dhat, beta_stage_s=round(stage_t, 3),
                    rescue_s=round(remaining, 3))
        return _stock_mm(source_graph, target_graph, remaining, seed, t0,
                         meta)
    except Exception as e:  # contract: never raise
        logger.error("p3-mm-beta%s error: %s", "-fb" if fb else "", e)
        return _fail(t0, str(e))


class _BetaArm(EmbeddingAlgorithm):
    _fb = False
    _requires = ["minorminer"]
    supported_counters: List[str] = []
    _install_instruction = "build the fork: bash scripts/build_mm_fork.sh"

    @classmethod
    def is_available(cls) -> tuple:
        if _find_so() is None:
            return (False, f"forked _minorminer not built ({_FORK_DIR})\n"
                           f"  {cls._install_instruction}")
        return (True, "")

    @property
    def version(self) -> str:
        return "1.0.0"

    def embed(self, source_graph, target_graph, timeout=60.0, **kwargs):
        seed = kwargs.get("seed", None)
        if seed is None:
            seed = 42
        return _beta_embed(source_graph, target_graph, float(timeout),
                           int(seed), self._fb)


@register_algorithm("p3-mm-beta")
class P3MMBeta(_BetaArm):
    """Faithful density-gated beta-dhat: below density 0.11, one pure
    forked-MM run with max_beta = dhat (full budget, no rescue); at/above the
    gate, full-budget stock-MM passthrough."""
    _fb = False


@register_algorithm("p3-mm-beta-fb")
class P3MMBetaFB(_BetaArm):
    """Product beta-dhat: below the gate, beta at 0.6x budget, then stock-MM
    rescue on the actual remaining wall if the beta stage returned nothing
    usable; at/above the gate, passthrough.  Success tracks stock MM."""
    _fb = True
