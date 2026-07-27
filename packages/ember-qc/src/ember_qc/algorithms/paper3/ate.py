"""
ember_qc/algorithms/paper3/ate.py
==================================
P1 — ATE, the adaptive template embedder (spec: docs/paper3/proposals/ate.md).

Registered arms:

* ``p3-template`` — the template arm alone. For n <= K_max(target) it is a
  deterministic construction (right-sized busclique K_n template -> span-
  objective assignment -> restriction to the source's edges via spur_prune ->
  deadline-bounded shorten_chains); zero cross-seed variance by construction.
  For n > K_max it is core+periphery: degeneracy-peel until the core fits,
  template the core, then stock ``minorminer.find_embedding`` with the core
  chains as ``initial_chains`` (source passed as a GRAPH OBJECT — the
  edge-list form silently drops isolated vertices) and the remaining budget
  as its timeout.
* ``p3-ate`` — evaluate-both auto-select: run the template arm (~ms below
  K_max) AND stock minorminer inside the single overall ``timeout``, return
  the lower-ACL valid embedding; both ACLs and the winning arm are recorded
  in ``metadata``. Protocol note: this is legal internal best-of-N — the
  whole arm fits inside ONE stock-MM run's budget (protocol.md rule 2).

Shared machinery lives in ``_template_core.py`` (owned by P1; imported by
later paper3 arms).
"""

from __future__ import annotations

import logging
import time
from typing import Dict, List, Optional

import networkx as nx

from ember_qc.registry import EmbeddingAlgorithm, register_algorithm
from ember_qc.embedding_backend import is_valid_embedding
from ember_qc.algorithms.paper3._template_core import (
    TargetState,
    degeneracy_core,
    get_target_state,
    ordered_template,
    assign_slots,
    restrict_template,
    template_embed,
    _sorted_nodes,
)

logger = logging.getLogger(__name__)

_MIN_MM_BUDGET_S = 0.05     # below this we do not bother starting an MM stage
_VERSION = "1.0.0"


def _acl(embedding: Dict) -> float:
    return sum(len(c) for c in embedding.values()) / max(1, len(embedding))


def _failure(t0: float, status: str, err: str, metadata: Optional[Dict] = None) -> Dict:
    out = {
        "embedding": {},
        "time": time.perf_counter() - t0,
        "success": False,
        "status": status,
        "error": err,
    }
    if metadata:
        out["metadata"] = metadata
    return out


def _normalize(raw: Dict) -> Dict[int, List[int]]:
    """Chains as plain lists of plain ints (contract), keys left as-is."""
    return {v: [int(q) for q in c] for v, c in raw.items()}


def _template_arm(
    source: nx.Graph,
    target: nx.Graph,
    state: TargetState,
    deadline: float,
    seed: int,
) -> Dict:
    """The template arm proper. Returns an internal result dict:
    {embedding|None, status, err, metadata}. Never raises on the happy paths
    the callers exercise; callers still wrap it in try/except."""
    n = source.number_of_nodes()
    meta: Dict = {"k_max": state.kmax}

    if n == 0:
        return {"embedding": None, "status": "FAILURE",
                "err": "empty source graph", "metadata": meta}

    if n <= state.kmax:
        emb, info = template_embed(source, state, deadline=deadline)
        meta["template_mode"] = "direct"
        assign = info.get("assign", {})
        meta["assign_order"] = assign.get("seed_order")
        meta["assign_obj_seed"] = assign.get("obj_seed")
        meta["assign_obj_final"] = assign.get("obj_final")
        if emb is None:
            return {"embedding": None, "status": "FAILURE",
                    "err": info.get("err", "template construction failed"),
                    "metadata": meta}
        if not is_valid_embedding(emb, source, target, adj=state.adj):
            return {"embedding": None, "status": "FAILURE",
                    "err": "template embedding failed validation",
                    "metadata": meta}
        return {"embedding": _normalize(emb), "status": "SUCCESS", "err": "",
                "metadata": meta}

    # ── n > K_max: core + periphery ─────────────────────────────────────────
    meta["template_mode"] = "core_periphery"
    core = degeneracy_core(source, state.kmax)
    meta["core_size"] = len(core)
    core_sub = source.subgraph(core)
    tpl = ordered_template(state, len(core))
    if tpl is None:
        return {"embedding": None, "status": "FAILURE",
                "err": "busclique core template unavailable", "metadata": meta}
    chains, pos = tpl
    verts = _sorted_nodes(core_sub)
    remaining = deadline - time.perf_counter()
    if remaining <= 0.005:
        return {"embedding": None, "status": "TIMEOUT",
                "err": "no time for core assignment", "metadata": meta}
    slots, assign_info = assign_slots(
        core_sub, verts, pos, wall_cap_s=min(0.1, 0.25 * remaining))
    meta["assign_order"] = assign_info.get("seed_order")
    meta["assign_obj_seed"] = assign_info.get("obj_seed")
    meta["assign_obj_final"] = assign_info.get("obj_final")
    emb_idx = restrict_template(core_sub, verts, slots, chains, state.adj,
                                deadline=deadline)
    initial = {verts[i]: [int(q) for q in c] for i, c in emb_idx.items()}

    remaining = deadline - time.perf_counter()
    if remaining < _MIN_MM_BUDGET_S:
        return {"embedding": None, "status": "TIMEOUT",
                "err": "no time for periphery routing", "metadata": meta}
    import minorminer
    raw = minorminer.find_embedding(
        source,                       # GRAPH OBJECT (keeps isolated vertices)
        list(target.edges()),
        initial_chains=initial,
        timeout=remaining,
        random_seed=seed,
        verbose=0,
    )
    if not raw:
        status = "TIMEOUT" if time.perf_counter() >= deadline - 0.01 else "FAILURE"
        return {"embedding": None, "status": status,
                "err": "periphery MM stage returned empty", "metadata": meta}
    emb = _normalize(raw)
    if not is_valid_embedding(emb, source, target, adj=state.adj):
        return {"embedding": None, "status": "FAILURE",
                "err": "core+periphery embedding failed validation",
                "metadata": meta}
    return {"embedding": emb, "status": "SUCCESS", "err": "", "metadata": meta}


@register_algorithm("p3-template")
class P3Template(EmbeddingAlgorithm):
    """P1 template arm: busclique K_n template + span-objective assignment +
    prune/shorten; core+periphery via MM initial_chains when n > K_max.
    Deterministic below K_max (seed only reaches the periphery MM stage)."""

    supported_counters: List[str] = []
    _uses_subprocess = False

    @property
    def version(self) -> str:
        return _VERSION

    def embed(self, source_graph, target_graph, timeout=60.0, **kwargs):
        t0 = time.perf_counter()
        try:
            timeout = max(0.01, float(timeout))
            seed = kwargs.get("seed", 42)
            seed = 42 if seed is None else int(seed)
            deadline = t0 + timeout

            state = get_target_state(target_graph)
            if state is None:
                return _failure(t0, "FAILURE",
                                "target not supported by busclique "
                                "(non-Chimera/Pegasus/Zephyr)")
            r = _template_arm(source_graph, target_graph, state, deadline, seed)
            if r["embedding"] is None:
                return _failure(t0, r["status"], r["err"], r.get("metadata"))
            return {
                "embedding": r["embedding"],
                "time": time.perf_counter() - t0,
                "metadata": r.get("metadata", {}),
            }
        except Exception as e:  # contract: never raise
            logger.error("p3-template error: %s", e)
            return _failure(t0, "FAILURE", f"{type(e).__name__}: {e}")


@register_algorithm("p3-ate")
class P3ATE(EmbeddingAlgorithm):
    """P1 product arm: template arm AND stock MM inside one timeout; returns
    the lower-ACL valid embedding (tie -> template). Winner + both ACLs in
    metadata. Never worse than the better of its two components on the cells
    where both run."""

    supported_counters: List[str] = []
    _uses_subprocess = False

    @property
    def version(self) -> str:
        return _VERSION

    def embed(self, source_graph, target_graph, timeout=60.0, **kwargs):
        t0 = time.perf_counter()
        try:
            timeout = max(0.01, float(timeout))
            seed = kwargs.get("seed", 42)
            seed = 42 if seed is None else int(seed)
            deadline = t0 + timeout
            n = source_graph.number_of_nodes()

            meta: Dict = {"winner": None, "acl_template": None, "acl_mm": None}

            # ── stage 1: template arm ───────────────────────────────────────
            tmpl_emb = None
            state = get_target_state(target_graph)
            if state is None:
                meta["template_mode"] = "unavailable"
            else:
                # Below K_max the template path costs ~ms and gets the full
                # deadline (its internal caps keep it tiny); above K_max its
                # MM-periphery stage would eat the whole budget, so it gets
                # half and stock MM keeps the rest (as-built split).
                if n <= state.kmax:
                    tmpl_deadline = deadline
                else:
                    tmpl_deadline = t0 + 0.5 * timeout
                try:
                    r = _template_arm(source_graph, target_graph, state,
                                      tmpl_deadline, seed)
                    meta.update(r.get("metadata", {}))
                    if r["embedding"] is not None:
                        tmpl_emb = r["embedding"]
                        meta["acl_template"] = round(_acl(tmpl_emb), 4)
                    else:
                        meta["template_err"] = r["err"]
                except Exception as e:  # template arm must never sink the product
                    logger.error("p3-ate template stage error: %s", e)
                    meta["template_err"] = f"{type(e).__name__}: {e}"

            # ── stage 2: stock MM with the remaining budget ─────────────────
            mm_emb = None
            remaining = deadline - time.perf_counter()
            if remaining >= _MIN_MM_BUDGET_S:
                import minorminer
                try:
                    raw = minorminer.find_embedding(
                        source_graph,             # GRAPH OBJECT (isolated verts)
                        list(target_graph.edges()),
                        timeout=remaining,
                        random_seed=seed,
                        verbose=0,
                    )
                except Exception as e:
                    logger.error("p3-ate MM stage error: %s", e)
                    raw = None
                if raw:
                    cand = _normalize(raw)
                    if is_valid_embedding(cand, source_graph, target_graph):
                        mm_emb = cand
                        meta["acl_mm"] = round(_acl(mm_emb), 4)
            else:
                meta["mm_skipped"] = "no remaining budget"

            # ── select ──────────────────────────────────────────────────────
            if tmpl_emb is not None and (
                    mm_emb is None or _acl(tmpl_emb) <= _acl(mm_emb)):
                meta["winner"] = "template"
                chosen = tmpl_emb
            elif mm_emb is not None:
                meta["winner"] = "mm"
                chosen = mm_emb
            else:
                meta["winner"] = "none"
                status = ("TIMEOUT"
                          if time.perf_counter() >= deadline - 0.01 else "FAILURE")
                return _failure(t0, status, "both arms failed", meta)

            return {
                "embedding": chosen,
                "time": time.perf_counter() - t0,
                "metadata": meta,
            }
        except Exception as e:  # contract: never raise
            logger.error("p3-ate error: %s", e)
            return _failure(t0, "FAILURE", f"{type(e).__name__}: {e}")
