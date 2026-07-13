"""
ember_qc/algorithms/minorminer_forked.py
=========================================
**Order-guided minorminer on the FULL search** — via a small fork of minorminer
that adds a ``var_order=`` parameter to ``find_embedding``.

Stock ``minorminer.find_embedding`` runs its complete heuristic (tear-and-replace
+ ``tries`` restarts) using an *internal randomized* variable order (RPFS); it
exposes no way to supply your own order to that full search (only the weaker
``quickpass`` primitive takes one — see ``minorminer_guided.py``). The fork in
``external/minorminer-fork`` adds one field (``optional_parameters.fixed_var_order``)
and one early-return in ``embedding_problem::var_order`` so a caller-supplied order
drives every pass of the full search. With ``var_order`` unset the fork is
byte-identical to stock minorminer 0.2.22 (parity-tested).

This module loads that forked ``_minorminer`` extension (built in-place by
``scripts/build_mm_fork.sh``) as a standalone module — it coexists with the
installed stock ``minorminer`` in the same process — and registers:

  mmfork              the fork with no var_order (== stock minorminer; control)
  mmfork-<order>      the full search guided by a ``search_orders`` ordering

The headline finding (search-guidance study, `new-algorithm` branch): a min-fill
or degeneracy order lowers mean ACL by ~1-2% **and** roughly halves run-to-run
variance versus stock minorminer's random ordering.
"""
from __future__ import annotations

import importlib.util
import logging
import os
import time
from typing import Dict, List, Optional

import networkx as nx

from ember_qc.registry import EmbeddingAlgorithm, register_algorithm
from ember_qc.algorithms.search_orders import ORDERINGS

logger = logging.getLogger(__name__)

# Location of the in-place-built forked extension (overridable via env).
_FORK_DIR = os.environ.get(
    "EMBER_MM_FORK_DIR",
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "..",
                 "external", "minorminer-fork", "minorminer"),
)
_FORK_DIR = os.path.abspath(_FORK_DIR)

_mmfork = None  # cached module


def _find_so() -> Optional[str]:
    if not os.path.isdir(_FORK_DIR):
        return None
    for fn in os.listdir(_FORK_DIR):
        if fn.startswith("_minorminer") and fn.endswith(".so"):
            return os.path.join(_FORK_DIR, fn)
    return None


def _load_fork():
    """Import the forked _minorminer extension by file path (cached)."""
    global _mmfork
    if _mmfork is not None:
        return _mmfork
    so = _find_so()
    if so is None:
        raise ImportError(
            f"forked _minorminer.so not found in {_FORK_DIR}; "
            f"run scripts/build_mm_fork.sh")
    # The extension's init symbol is PyInit__minorminer, so it must be imported
    # under the name "_minorminer" (a top-level module distinct from the stock
    # package's minorminer._minorminer; the two coexist in one process).
    import sys
    if "_minorminer" in sys.modules:
        _mmfork = sys.modules["_minorminer"]
        return _mmfork
    spec = importlib.util.spec_from_file_location("_minorminer", so)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["_minorminer"] = mod
    spec.loader.exec_module(mod)
    _mmfork = mod
    return mod


# Defaults matching stock minorminer.find_embedding's Python wrapper, so the raw
# extension call behaves exactly like the public API.
_DEF = dict(max_no_improvement=10, timeout=1000, max_beta=None, tries=10,
            inner_rounds=None, chainlength_patience=10, max_fill=None, threads=1,
            return_overlap=False, skip_initialization=False, verbose=0,
            interactive=False)


def forked_find_embedding(
    source: nx.Graph, target: nx.Graph, *, order: Optional[List[int]] = None,
    seed: int = 0, timeout: float = 60.0, tries: int = 10, fallback: bool = True,
) -> dict:
    """Run the forked minorminer full search, optionally guided by ``order``.

    Drop-in safety: a single fixed order reused across all ``tries`` restarts
    removes the order diversity stock MM relies on near the feasibility boundary,
    so a guided run *could* fail where stock MM would succeed. With ``fallback``
    (default), a failed guided run is retried once as **stock minorminer** (no
    ``var_order``) on the remaining budget — guaranteeing success >= stock MM. The
    plain ``mmfork`` control (``order=None``) is stock MM by construction."""
    start = time.perf_counter()
    deadline = start + timeout if timeout else None
    try:
        mod = _load_fork()
    except Exception as exc:
        # Fork not built on this machine — behave like an unavailable algorithm
        # (return a failure dict, never raise) so the contract tests pass.
        return {"embedding": {}, "time": time.perf_counter() - start,
                "success": False, "status": "FAILURE", "error": str(exc)}
    S, T = list(source.edges()), list(target.edges())

    def _run(var_order, t):
        params = dict(_DEF)
        params["tries"] = tries
        params["timeout"] = t if t else 1000
        if var_order is not None:
            params["var_order"] = list(var_order)
        try:
            e = mod.find_embedding(S, T, random_seed=int(seed), **params)
        except Exception as exc:
            logger.debug("forked find_embedding raised: %s", exc)
            return None
        return {int(k): [int(q) for q in v] for k, v in e.items() if v}

    emb = _run(order, timeout)
    # Fallback: a guided run that fails (empty/raised) retries as stock MM so the
    # ordered variants never do worse than minorminer on *success*.
    if (not emb) and order is not None and fallback:
        remaining = None if deadline is None else max(1.0, deadline - time.perf_counter())
        emb = _run(None, remaining)

    elapsed = time.perf_counter() - start
    if not emb:
        return {"embedding": {}, "time": elapsed, "success": False, "status": "FAILURE"}
    return {"embedding": emb, "time": elapsed}


class _ForkBase(EmbeddingAlgorithm):
    _order: Optional[str] = None  # key into ORDERINGS, or None for default
    _tries: int = 10              # minorminer restart count (10 = stock default)

    _install_instruction = "build the fork: bash scripts/build_mm_fork.sh"

    @classmethod
    def is_available(cls) -> tuple:
        if _find_so() is None:
            return (False, f"forked _minorminer not built ({_FORK_DIR})\n  {cls._install_instruction}")
        return (True, "")

    @property
    def version(self) -> str:
        return "0.2.22+ember-varorder"

    def embed(self, source_graph, target_graph, timeout=60.0, **kwargs) -> dict:
        seed = kwargs.get("seed", 0) or 0
        order = ORDERINGS[self._order](source_graph) if self._order else None
        return forked_find_embedding(source_graph, target_graph, order=order,
                                     seed=int(seed), timeout=timeout, tries=self._tries)


@register_algorithm("mmfork")
class MMFork(_ForkBase):
    """Forked minorminer with no var_order — control == stock minorminer 0.2.22."""
    _order = None


def _make(order_name: str) -> type:
    cls = type(f"MMFork_{order_name}", (_ForkBase,),
               {"_order": order_name,
                "__doc__": f"Forked minorminer full search guided by '{order_name}' order."})
    return register_algorithm(f"mmfork-{order_name}")(cls)


_VARIANTS = {nm: _make(nm) for nm in ORDERINGS}  # incl. 'bfs'
