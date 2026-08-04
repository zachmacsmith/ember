"""
ember_qc/algorithms/paper3/beta_mf.py
======================================
``p3-mm-beta-mf`` — the v1.3 mm-FIRST beta arm (notes.md §4.17 W-A; ledger
item 4 NEXT). The §4.16 autopsy of ``p3-mm-beta-fb`` found two structural
faults: the 0.6/0.4 budget split cost success on five families (instances
stock MM legalizes in 25-60 s got a 24 s rescue), and beta engaged below the
density gate hurt structured sparse lattices. This arm inverts the order —
the mmpolish v1.1 leftover pattern:

* at/above density 0.11 — pure full-budget stock-MM passthrough (beta.py's
  gate convention, unchanged constants imported from beta.py);
* below the gate — stock MM FIRST with the FULL budget (to the arm
  deadline). MM fails -> the arm fails exactly like stock (the -fb failure
  mode is structurally impossible). MM succeeds with >= 1 s of leftover ->
  one forked run (``max_beta = dhat``, no internal fallback) on the
  leftover; the arm returns whichever embedding has lower raw ACL
  (tie -> MM's). A beta result is validated before it can win, so the arm's
  ACL is never worse than its own MM stage's.

Success == stock by construction; the beta stage can only add ACL. On the
§4.8b dev ladder MM patience-expires in 4-17 s, leaving 43-56 s of leftover
— nearly the full-budget beta run whose Z12 margins T1c confirmed
(-3.5/-5.6 % at n=140/180).

Contract: never raises, plain int chains, tiny-timeout safe, deterministic
per seed, no stdout.
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
from ember_qc.algorithms.paper3.beta import (
    _GATE_MAX_DENSITY,
    _fail,
    _is_valid,
    _stock_mm,
    dhat_of,
)

logger = logging.getLogger(__name__)

_MIN_BETA_LEFTOVER_S = 1.0   # below this leftover the beta re-run is skipped


def _acl(emb) -> float:
    return sum(len(c) for c in emb.values()) / max(1, len(emb))


def _mf_embed(source_graph, target_graph, timeout: float, seed: int) -> dict:
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

        # ── stage 1: stock MM with the FULL budget ──────────────────────────
        mm = _stock_mm(source_graph, target_graph, timeout, seed, t0,
                       dict(gmeta))
        mm_emb = mm.get("embedding") or {}
        mm_wall = time.perf_counter() - t0
        if not mm_emb or not _is_valid(mm_emb, source_graph, target_graph):
            # arm == stock by construction: same call, same budget, same seed
            mm.setdefault("metadata", dict(gmeta))
            mm["metadata"] = dict(mm.get("metadata") or gmeta,
                                  selection="mm_failed", stage="mm")
            return mm

        # ── stage 2: beta-dhat re-run on the leftover wall ──────────────────
        leftover = deadline - time.perf_counter()
        meta = dict(gmeta, selection="mm", stage="mm+beta",
                    mm_wall=round(mm_wall, 3), acl_mm=round(_acl(mm_emb), 4),
                    beta_leftover_s=round(max(0.0, leftover), 3))
        chosen = mm_emb
        if leftover >= _MIN_BETA_LEFTOVER_S:
            dhat = dhat_of(source_graph)
            meta["max_beta"] = dhat
            b0 = time.perf_counter()
            try:
                r = forked_find_embedding(
                    source_graph, target_graph, max_beta=dhat,
                    seed=int(seed), timeout=float(leftover), fallback=False)
                b_emb = r.get("embedding") or {}
            except Exception as e:  # defensive: keep MM's result
                logger.error("p3-mm-beta-mf beta stage error: %s", e)
                b_emb = {}
            meta["beta_wall"] = round(time.perf_counter() - b0, 3)
            if b_emb and _is_valid(b_emb, source_graph, target_graph):
                meta["acl_beta"] = round(_acl(b_emb), 4)
                if _acl(b_emb) < _acl(mm_emb):     # strict: tie -> MM's
                    chosen = b_emb
                    meta["selection"] = "beta"
        else:
            meta["beta_skipped"] = "no leftover"
        return {"embedding": {int(w): [int(q) for q in c]
                              for w, c in chosen.items()},
                "time": time.perf_counter() - t0, "metadata": meta}
    except Exception as e:  # contract: never raise
        logger.error("p3-mm-beta-mf error: %s", e)
        return _fail(t0, str(e))


@register_algorithm("p3-mm-beta-mf")
class P3MMBetaMF(EmbeddingAlgorithm):
    """v1.3 mm-first beta (§4.17 W-A): below density 0.11, full-budget stock
    MM first, then one beta-dhat re-run on the leftover wall keeping the
    lower-ACL embedding; at/above the gate, full-budget stock-MM passthrough.
    Success == stock by construction."""

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
        try:
            budget = max(0.01, float(timeout))
        except (TypeError, ValueError):
            budget = 60.0
        return _mf_embed(source_graph, target_graph, budget, int(seed))
