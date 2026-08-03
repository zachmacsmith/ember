"""
ember_qc/algorithms/paper3/ember.py
====================================
``p3-ember`` — the v1.2 unified arm (notes.md §5; pre-registered §4.15
T1a/T1b). One arm carrying all three measured wins, in evidence order
(improvement-notes.md items 12, 2, 1):

* stage 0 — native fast path (``native.try_native``): structural gates →
  label-subset identity → Glasgow subgraph solver. A hit is all-length-1
  chains (ACL exactly 1.0) and returns immediately.
* stage 1 — ate's template arm (imported ``_template_arm``, byte-identical
  logic) with ONE change: below K_max the template is attempted only when
  ``nx.density(source) >= 0.08`` (kills the sparse "insurance tax"; every
  measured template win is at density ≥ 0.12). The n > K_max overflow rule
  (density ≥ 0.15, half budget) is exactly ate's.
* stage 2 — stock minorminer with the remaining budget (ate's stage 2).
* stage 3 — lower-ACL valid embedding wins, tie → template (ate's stage 3).
* stage 4 — leftover-wall ``anytime_polish`` on the winner (monotone and
  validity-guarded; any exception falls back to the unpolished winner).

Contract: never raises, plain int chains, tiny-timeout safe (timeout ≤ 2 s
skips the Glasgow tier and the polish), deterministic per seed, no stdout.
Protocol note: legal internal best-of-N — the whole arm fits inside ONE
stock-MM run's budget (protocol.md rule 2).
"""

from __future__ import annotations

import logging
import time
from typing import Dict

import networkx as nx

from ember_qc.registry import EmbeddingAlgorithm, register_algorithm
from ember_qc.embedding_backend import is_valid_embedding
from ember_qc.algorithms.paper3.ate import (
    _MIN_MM_BUDGET_S,
    _acl,
    _failure,
    _normalize,
    _template_arm,
)
from ember_qc.algorithms.paper3._template_core import get_target_state
from ember_qc.algorithms.paper3.joint_repair import anytime_polish
from ember_qc.algorithms.paper3.native import try_native

logger = logging.getLogger(__name__)

_TEMPLATE_MIN_DENSITY = 0.08    # below-K_max gate (improvement-notes item 2)
_OVERFLOW_MIN_DENSITY = 0.15    # n > K_max rule, exactly as ate (§4.11 M5)
_TINY_TIMEOUT_S = 2.0           # ≤ this: no Glasgow, no polish
_MIN_POLISH_BUDGET_S = 0.05


@register_algorithm("p3-ember")
class P3Ember(EmbeddingAlgorithm):
    """v1.2 unified arm: native fast path -> density-gated template-vs-MM
    race (ate clone) -> leftover-wall anytime polish on the winner."""

    supported_counters: list = []
    _uses_subprocess = False

    @property
    def version(self) -> str:
        return "1.0.0"

    def embed(self, source_graph, target_graph, timeout=60.0, **kwargs):
        t0 = time.perf_counter()
        try:
            timeout = max(0.01, float(timeout))
            seed = kwargs.get("seed", 42)
            seed = 42 if seed is None else int(seed)
            deadline = t0 + timeout
            tiny = timeout <= _TINY_TIMEOUT_S
            n = source_graph.number_of_nodes()

            meta: Dict = {"winner": None, "acl_template": None,
                          "acl_mm": None, "native": "miss"}

            # ── stage 0: native fast path ───────────────────────────────────
            nat0 = time.perf_counter()
            nat = try_native(source_graph, target_graph, deadline,
                             allow_glasgow=not tiny, meta=meta)
            meta["native_s"] = round(time.perf_counter() - nat0, 4)
            if nat is not None:
                meta["winner"] = "native"
                return {"embedding": _normalize(nat),
                        "time": time.perf_counter() - t0, "metadata": meta}

            # ── stage 1: template arm (ate clone + sparse gate) ─────────────
            tmpl_emb = None
            state = get_target_state(target_graph)
            if state is None:
                meta["template_mode"] = "unavailable"
            else:
                if n <= state.kmax:
                    if nx.density(source_graph) >= _TEMPLATE_MIN_DENSITY:
                        tmpl_deadline = deadline
                    else:
                        tmpl_deadline = None
                        meta["template_mode"] = "skipped_sparse"
                elif nx.density(source_graph) >= _OVERFLOW_MIN_DENSITY:
                    tmpl_deadline = t0 + 0.5 * timeout
                else:
                    tmpl_deadline = None
                    meta["template_mode"] = "skipped_sparse_overflow"
                if tmpl_deadline is not None:
                    try:
                        r = _template_arm(source_graph, target_graph, state,
                                          tmpl_deadline, seed)
                        meta.update(r.get("metadata", {}))
                        if r["embedding"] is not None:
                            tmpl_emb = r["embedding"]
                            meta["acl_template"] = round(_acl(tmpl_emb), 4)
                        else:
                            meta["template_err"] = r["err"]
                    except Exception as e:   # never sink the product arm
                        logger.error("p3-ember template stage error: %s", e)
                        meta["template_err"] = f"{type(e).__name__}: {e}"

            # ── stage 2: stock MM with the remaining budget ─────────────────
            mm_emb = None
            remaining = deadline - time.perf_counter()
            if remaining >= _MIN_MM_BUDGET_S:
                import minorminer
                try:
                    raw = minorminer.find_embedding(
                        source_graph,        # GRAPH OBJECT (isolated verts)
                        list(target_graph.edges()),
                        timeout=remaining,
                        random_seed=seed,
                        verbose=0,
                    )
                except Exception as e:
                    logger.error("p3-ember MM stage error: %s", e)
                    raw = None
                if raw:
                    cand = _normalize(raw)
                    if is_valid_embedding(cand, source_graph, target_graph):
                        mm_emb = cand
                        meta["acl_mm"] = round(_acl(mm_emb), 4)
            else:
                meta["mm_skipped"] = "no remaining budget"

            # ── stage 3: select (tie -> template) ───────────────────────────
            if tmpl_emb is not None and (
                    mm_emb is None or _acl(tmpl_emb) <= _acl(mm_emb)):
                meta["winner"] = "template"
                chosen = tmpl_emb
            elif mm_emb is not None:
                meta["winner"] = "mm"
                chosen = mm_emb
            else:
                meta["winner"] = "none"
                status = ("TIMEOUT" if time.perf_counter() >= deadline - 0.01
                          else "FAILURE")
                return _failure(t0, status, "both arms failed", meta)

            # ── stage 4: leftover-wall polish (monotone, validity-guarded) ──
            if not tiny and deadline - time.perf_counter() > _MIN_POLISH_BUDGET_S:
                meta["acl_pre_polish"] = round(_acl(chosen), 4)
                p0 = time.perf_counter()
                try:
                    chosen = anytime_polish(
                        chosen, source_graph, target_graph, deadline,
                        adj=state.adj if state else None)
                except Exception as e:   # fall back to the unpolished winner
                    logger.error("p3-ember polish error: %s", e)
                meta["polish_s"] = round(time.perf_counter() - p0, 4)

            return {
                "embedding": chosen,
                "time": time.perf_counter() - t0,
                "metadata": meta,
            }
        except Exception as e:   # contract: never raise
            logger.error("p3-ember error: %s", e)
            return _failure(t0, "FAILURE", f"{type(e).__name__}: {e}")
