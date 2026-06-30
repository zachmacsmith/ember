"""
ember_qc/algorithms/minorminer_guided.py
=========================================
**Order-guided minorminer** — drive minorminer's *own* C++ search primitive with
a chosen vertex order, without forking the library.

``minorminer`` exposes a low-level ``miner`` object whose ``quickpass`` method runs
one greedy embedding pass over the source vertices **in a caller-supplied order**
(``varorder=``) or by one of its built-in strategies (``VARORDER`` enum:
SHUFFLE / DFS / BFS / PFS / RPFS / KEEP).  Looping ``quickpass(clear_first=False)``
refines the embedding pass over pass — exactly minorminer's inner machinery, but
with the *ordering* lever in our hands.  This lets us benchmark vertex orderings
on minorminer's real search (the question the C++ fork answers for the full
``find_embedding`` search) cheaply and in pure Python.

Caveat: ``quickpass`` is minorminer's *greedy* primitive, weaker than the full
``find_embedding`` (which adds tear-and-replace + restarts).  So absolute ACL here
is higher than ``find_embedding``; the value is the **relative** comparison across
orderings on identical machinery, and a cheap read on whether ordering is worth
the C++ fork for the full search.  ``local_search=True`` is avoided — in looped
construction it returns empty chains (it expects a pre-seeded embedding).

Registered:
  mm-guided-<order>    looped quickpass with our order (search_orders.ORDERINGS)
  mm-strategy-<name>   looped quickpass with a built-in VARORDER strategy
"""
from __future__ import annotations

import logging
import time
from typing import Dict, List, Optional

import networkx as nx

from ember_qc.registry import EmbeddingAlgorithm, register_algorithm
from ember_qc.algorithms.search_orders import ORDERINGS

logger = logging.getLogger(__name__)


def _acl(emb: Dict[int, List[int]]) -> float:
    return sum(len(c) for c in emb.values()) / len(emb) if emb else float("inf")


def guided_quickpass_embed(
    source: nx.Graph,
    target: nx.Graph,
    *,
    order: Optional[List[int]] = None,
    strategy: Optional[str] = None,
    seed: int = 0,
    timeout: float = 60.0,
    stall: int = 10,
    max_passes: int = 200,
) -> dict:
    """Loop minorminer's ``quickpass`` (in ``order`` or by ``strategy``) keeping the
    fewest-qubit valid embedding; stop on timeout, ``max_passes``, or ``stall``
    passes with no improvement.  Always returns an ember-qc result dict."""
    import minorminer
    from minorminer import miner, VARORDER
    from ember_qc.embedding_backend import build_adjacency, is_valid_embedding

    start = time.perf_counter()
    deadline = start + timeout if timeout else None
    adj = build_adjacency(target)
    n = source.number_of_nodes()
    S = list(source.edges())
    T = list(target.edges())

    strat_enum = {
        "shuffle": VARORDER.VARORDER_SHUFFLE, "dfs": VARORDER.VARORDER_DFS,
        "bfs": VARORDER.VARORDER_BFS, "pfs": VARORDER.VARORDER_PFS,
        "rpfs": VARORDER.VARORDER_RPFS,
    }.get((strategy or "rpfs").lower(), VARORDER.VARORDER_RPFS)

    try:
        m = miner(S, T, random_seed=int(seed))
    except Exception as exc:
        logger.debug("guided miner construction failed: %s", exc)
        return {"embedding": {}, "time": time.perf_counter() - start,
                "success": False, "status": "FAILURE", "error": str(exc)}

    best: Optional[Dict[int, List[int]]] = None
    best_total = float("inf")
    no_improve = 0
    first = True
    for _ in range(max_passes):
        if deadline is not None and time.perf_counter() > deadline:
            break
        try:
            e = m.quickpass(
                varorder=order, strategy=strat_enum,
                overlap_bound=0, local_search=False, clear_first=first,
            )
        except Exception as exc:
            logger.debug("guided quickpass failed: %s", exc)
            break
        first = False
        e = {int(k): [int(q) for q in v] for k, v in e.items() if v}
        improved = False
        if len(e) == n and is_valid_embedding(e, source, target, adj=adj):
            total = sum(len(c) for c in e.values())
            if total < best_total:
                best, best_total, improved = e, total, True
        no_improve = 0 if improved else no_improve + 1
        if no_improve >= stall:
            break

    elapsed = time.perf_counter() - start
    if not best:
        return {"embedding": {}, "time": elapsed, "success": False, "status": "FAILURE"}
    return {"embedding": best, "time": elapsed}


class _GuidedBase(EmbeddingAlgorithm):
    _order: Optional[str] = None      # key into ORDERINGS, or None
    _strategy: Optional[str] = None   # VARORDER strategy name, or None

    @property
    def version(self) -> str:
        return "1.0.0"

    def embed(self, source_graph, target_graph, timeout=60.0, **kwargs) -> dict:
        seed = kwargs.get("seed", 0) or 0
        order = ORDERINGS[self._order](source_graph) if self._order else None
        return guided_quickpass_embed(
            source_graph, target_graph, order=order, strategy=self._strategy,
            seed=int(seed), timeout=timeout,
        )


def _make_guided(order_name: str) -> type:
    cls = type(f"MMGuided_{order_name}", (_GuidedBase,),
               {"_order": order_name,
                "__doc__": f"Order-guided minorminer (quickpass) with '{order_name}' order."})
    return register_algorithm(f"mm-guided-{order_name}")(cls)


def _make_strategy(name: str) -> type:
    cls = type(f"MMStrategy_{name}", (_GuidedBase,),
               {"_strategy": name,
                "__doc__": f"minorminer quickpass with built-in VARORDER_{name.upper()} strategy."})
    return register_algorithm(f"mm-strategy-{name}")(cls)


_GUIDED = {name: _make_guided(name) for name in ORDERINGS}            # incl. 'bfs'
_STRATEGY = {s: _make_strategy(s) for s in ["shuffle", "dfs", "bfs", "pfs", "rpfs"]}
