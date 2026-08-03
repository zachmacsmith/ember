"""
ember_qc/algorithms/paper3/native.py
=====================================
Native fast path for (near-)hardware-native sources (improvement-notes.md
item 12; pre-registered §4.15 T1b). Tries to place the source as a SUBGRAPH
of the target — every chain length 1, ACL exactly 1.0, unbeatable — before
any search or template arm spends budget. Three tiers, cheapest first:

1. structural gates (µs): |V|, max degree and |E| monotonicity — any failure
   proves no subgraph placement exists;
2. label-subset identity (ms): source nodes ⊆ target nodes and every source
   edge already a target edge → the identity map;
3. Glasgow subgraph solver: ``minorminer.subgraph.find_subgraph`` from STOCK
   minorminer 0.2.22 (the C++ fork build lacks the module; the import is
   guarded). Its ``timeout`` is clamped to ``max(1, int(min(remaining, 2)))``
   — the solver treats 0 as UNLIMITED, so 0 is never passed — and its answer
   is never trusted blindly: the length-1 chains must pass
   ``is_valid_embedding`` or the tier reports a miss.

Measured caveat (2026-08-03): find_subgraph builds supplemental graphs
OUTSIDE its own timeout (~4 s for a ~2000-node source into Z12), so callers
gate the Glasgow tier on budget (p3-ember: skipped when the call has ≤ 2 s).
"""

from __future__ import annotations

import time
from typing import Dict, List, Optional

import networkx as nx

from ember_qc.embedding_backend import is_valid_embedding

_GLASGOW_SEED = 0        # fixed: the native tier is deterministic by design
_MIN_GLASGOW_BUDGET_S = 0.05


def glasgow_timeout(remaining: float) -> int:
    """Integer timeout for find_subgraph: min(remaining, 2) s, floor 1.
    Never 0 — find_subgraph interprets timeout=0 as UNLIMITED."""
    return max(1, int(min(remaining, 2)))


def structural_pass(source: nx.Graph, target: nx.Graph) -> bool:
    """Necessary conditions for a subgraph placement (µs)."""
    n_src = source.number_of_nodes()
    if n_src == 0 or n_src > target.number_of_nodes():
        return False
    if source.number_of_edges() > target.number_of_edges():
        return False
    max_deg_src = max((d for _, d in source.degree()), default=0)
    max_deg_tgt = max((d for _, d in target.degree()), default=0)
    return max_deg_src <= max_deg_tgt


def _label_identity(source: nx.Graph, target: nx.Graph) -> Optional[Dict]:
    """Identity map when source is literally a labelled subgraph of target."""
    if not set(source.nodes) <= set(target.nodes):
        return None
    tadj = target.adj
    for u, v in source.edges():
        if v not in tadj[u]:
            return None
    return {v: [int(v)] for v in source.nodes}


def try_native(source: nx.Graph, target: nx.Graph, deadline: float, *,
               allow_glasgow: bool = True,
               meta: Optional[Dict] = None) -> Optional[Dict[int, List[int]]]:
    """Return a validated all-length-1 embedding, or None (miss). Never
    raises. ``deadline`` is an absolute ``time.perf_counter()`` timestamp.
    If ``meta`` is passed it records which tier hit under ``meta["native"]``
    ("label_identity" / "glasgow_hit"; left at "miss" otherwise)."""
    info = meta if meta is not None else {}
    info.setdefault("native", "miss")
    try:
        if not structural_pass(source, target):
            return None
        emb = _label_identity(source, target)
        if emb is not None and is_valid_embedding(emb, source, target):
            info["native"] = "label_identity"
            return emb
        if not allow_glasgow:
            return None
        remaining = deadline - time.perf_counter()
        if remaining <= _MIN_GLASGOW_BUDGET_S:
            return None
        try:
            from minorminer.subgraph import find_subgraph
        except Exception:
            return None    # fork build or missing extra: no Glasgow tier
        raw = find_subgraph(source, target,
                            timeout=glasgow_timeout(remaining),
                            parallel=False, seed=_GLASGOW_SEED)
        if not raw:
            return None
        emb = {v: [int(q)] for v, q in raw.items()}
        if not is_valid_embedding(emb, source, target):
            return None    # never trust the solver blindly
        info["native"] = "glasgow_hit"
        return emb
    except Exception:
        return None
