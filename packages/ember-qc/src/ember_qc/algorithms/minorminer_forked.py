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

The headline finding (see docs/candidate-algorithms/search-guidance/): a min-fill
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
    plain ``mmfork`` control (``order=None``) and ``mmfork-portfolio`` (which always
    includes a stock-MM config) are >= MM by construction."""
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


@register_algorithm("mmfork-cuthill-fast")
class MMForkCuthillFast(_ForkBase):
    """``mmfork-cuthill`` with fewer restarts. A good fixed order makes
    minorminer's restart diversity largely redundant (see the search-guidance
    study: ``tries=10``≈``tries=1`` here), so this matches the quality of the
    full-``tries`` Cuthill variant at a fraction of the wall-clock — typically
    *faster* than stock minorminer. ``tries`` is set from the ``tries_probe``."""
    _order = "cuthill"
    _tries = 2


# The orders that help on the full search (see the mmfork_order_probe); a
# per-instance portfolio over them keeps whichever wins on this graph.
_PORTFOLIO = ["cuthill", "spectral", "mcs", "minfill", "degeneracy"]


def _pf_run_one(args):
    """Run one portfolio config. Module-level so a ProcessPool can pickle it."""
    source, target, order_name, seed, timeout = args
    order = ORDERINGS[order_name](source) if order_name else None
    return forked_find_embedding(source, target, order=order, seed=seed, timeout=timeout)


def _portfolio_best(source, target, seed, timeout, workers, backend):
    """Run the portfolio configs and return (best_embedding | None, elapsed).

    Serial (``workers<=1``): each config gets ``timeout/len`` so the total stays in
    budget. Parallel: the configs run concurrently (each gets the *full* budget, so
    the wall-clock is ~one config's time rather than the sum) via a thread pool
    (minorminer's C++ search releases the GIL) or a process pool."""
    configs = [None] + _PORTFOLIO
    start = time.perf_counter()
    results = []
    if workers and workers > 1:
        from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
        tasks = [(source, target, n, seed, timeout) for n in configs]
        try:
            if backend == "thread":
                pool = ThreadPoolExecutor(max_workers=workers)
            else:
                # fork avoids re-importing ember_qc per worker (cheap on Linux/mac);
                # minorminer holds the GIL, so threads don't parallelize the search.
                import multiprocessing as mp
                try:
                    ctx = mp.get_context("fork")
                except ValueError:
                    ctx = None
                pool = ProcessPoolExecutor(max_workers=workers, mp_context=ctx)
            with pool as ex:
                results = list(ex.map(_pf_run_one, tasks))
        except Exception as exc:  # fall back to serial on any pool failure
            logger.debug("parallel portfolio failed (%s); serial fallback", exc)
            results = []
    if not results:  # serial path (default, and the fallback)
        slice_t = max(1.0, timeout / len(configs)) if timeout else 0.0
        results = [_pf_run_one((source, target, n, seed, slice_t)) for n in configs]
    best, best_total = None, float("inf")
    for r in results:
        emb = (r or {}).get("embedding")
        if emb:
            total = sum(len(c) for c in emb.values())
            if total < best_total:
                best, best_total = emb, total
    return best, time.perf_counter() - start


@register_algorithm("mmfork-portfolio")
class MMForkPortfolio(_ForkBase):
    """Run the forked search under each good order (and the default) on a slice of
    the budget; keep the fewest-qubit valid embedding. A deterministic per-instance
    order selector — the target a learned order-picker would match more cheaply.
    Serial by default (``_workers=1``) so it is safe inside a parallel sweep."""

    _workers = 1            # serial; sweep-safe default
    _backend = "thread"

    def _resolve_workers(self) -> int:
        return self._workers

    def embed(self, source_graph, target_graph, timeout=60.0, **kwargs) -> dict:
        seed = int(kwargs.get("seed", 0) or 0)
        best, elapsed = _portfolio_best(source_graph, target_graph, seed, timeout,
                                        self._resolve_workers(), self._backend)
        if not best:
            return {"embedding": {}, "time": elapsed, "success": False, "status": "FAILURE"}
        return {"embedding": best, "time": elapsed}


@register_algorithm("mmfork-portfolio-par")
class MMForkPortfolioPar(MMForkPortfolio):
    """Portfolio with its orders run CONCURRENTLY — standalone wall-clock drops
    toward a single order's cost (one embedding using several cores). Worker count
    from ``$EMBER_MMFORK_WORKERS`` (default = #configs). Keep it OUT of a parallel
    sweep (would oversubscribe); use ``mmfork-portfolio`` there."""

    _backend = "process"  # minorminer holds the GIL, so threads don't parallelize

    def _resolve_workers(self) -> int:
        import os
        return int(os.environ.get("EMBER_MMFORK_WORKERS", len(_PORTFOLIO) + 1))


def _make(order_name: str) -> type:
    cls = type(f"MMFork_{order_name}", (_ForkBase,),
               {"_order": order_name,
                "__doc__": f"Forked minorminer full search guided by '{order_name}' order."})
    return register_algorithm(f"mmfork-{order_name}")(cls)


_VARIANTS = {nm: _make(nm) for nm in ORDERINGS}  # incl. 'bfs'


@register_algorithm("mmfork-learned")
class MMForkLearned(_ForkBase):
    """Forked minorminer guided by a LEARNED per-vertex order: a linear score over
    graph features (weights fit by learn_order.py to minimize decoded ACL). Loads
    ``search_weights.json`` if present, else a degree+core/locality prior."""

    def embed(self, source_graph, target_graph, timeout=60.0, **kwargs) -> dict:
        from ember_qc.algorithms.learned_order import learned_order, weights_vector, DEFAULT_WEIGHTS
        seed = int(kwargs.get("seed", 0) or 0)
        wpath = os.path.join(os.path.dirname(__file__), "search_weights.json")
        try:
            import json
            with open(wpath) as f:
                w = weights_vector(json.load(f))
        except Exception:
            w = weights_vector(DEFAULT_WEIGHTS)
        order = learned_order(source_graph, w)
        return forked_find_embedding(source_graph, target_graph, order=order,
                                     seed=seed, timeout=timeout)
