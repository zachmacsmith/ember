"""
ember_qc/algorithms/minorminer_forked.py
=========================================
**Stock minorminer with its decisions exposed as switches** — via a small fork
(``scripts/mm_fork.patch``) that adds two parameters to ``find_embedding``:

* ``var_order=`` — a caller-supplied variable order drives every pass of the
  full search (stock uses an internal randomized order, RPFS, and exposes no
  way to override it on the full heuristic).
* ``history_alpha=`` — PathFinder-style history in the qubit cost: the routing
  price becomes ``(1 + h_q) * weight_table[occ(q)]`` and once per pass
  ``h_q <- max(0, h_q + alpha*(occ(q) - 1))`` (rises while contested, holds at
  exactly-full, decays while free; docs/paper2/notes.md §3.5/§3.12).
* paper3 P4 shortener-economics switches — ``short_audit=`` / ``audit_budget=``
  (audition policy inside ``find_short_chain``) and ``dirty_skip=`` (negative
  cache over provably-unchanged neighborhoods in the chainlength phase).
* paper3 P6 anatomy switches — ``chain_tree=`` (stock Steiner / revived
  union-of-paths / pure SPH) and ``root_boltzmann=`` (temperature-weighted root
  choice, the 2014 paper's never-shipped proposal); ``max_beta=`` (stock knob,
  finite = the paper's beta^occ pricing) is surfaced via the wrapper.
* paper3 W2 beta-ramp switches — ``beta_ramp=`` (per-pass geometric ramp of
  the live ``max_beta`` while the embedding is invalid: finite-beta quality
  pricing gliding toward stock's lexicographic feasibility pricing) and
  ``beta_ramp_hold=`` (restore the caller's beta once embedded; source-truth
  caveat: the chainlength phase never re-reads qubit prices, so in a plain
  ``find_embedding`` call hold is an expected exact tie with hold=0).
  See ``forked_find_embedding`` below and docs/paper3/proposals/{shortener,anatomy}.md.

With every switch unset the fork is byte-identical to stock minorminer 0.2.22
(parity self-tested at build: identical embeddings across seeds).

This module loads that forked ``_minorminer`` extension (built in-place by
``scripts/build_mm_fork.sh``) as a standalone module — it coexists with the
installed stock ``minorminer`` in the same process — and registers:

  mmfork              the fork with every switch off (== stock minorminer; control)
  mmfork-<order>      the full search guided by a ``search_orders`` ordering
  mmfork-history      stock dynamics with the history cost on (history_alpha=1)

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
    history_alpha: float = 0.0,
    short_audit: int = 0, audit_budget: int = 3, dirty_skip: int = 0,
    chain_tree: int = 0, root_boltzmann: float = 0.0,
    max_beta: Optional[float] = None,
    beta_ramp: float = 0.0, beta_ramp_hold: int = 0,
    seed: int = 0, timeout: float = 60.0, tries: int = 10, fallback: bool = True,
) -> dict:
    """Run the forked minorminer full search with any of the fork's switches.

    Switches (every default is byte-identical stock minorminer 0.2.22):

    * ``order`` — caller-supplied variable order for every pass.
    * ``history_alpha`` — PathFinder-style history cost (paper2 §3.5/§3.12).
    * ``short_audit`` — P4 audition policy in ``find_short_chain``: 0 stock
      exhaustive; 1 estimate-only (one construction at the best-estimated
      meeting point, kept only on strict improvement); 2 budgeted (audition in
      estimated-cost order, stop at first improvement or ``audit_budget``
      constructions). ``audit_budget`` is passed only alongside
      ``short_audit`` (it is meaningless without it).
    * ``dirty_skip`` — P4 negative-result cache: skip re-auditing a variable in
      the chainlength phase while its closed neighborhood of chains is
      provably unchanged since its last failed audition.
    * ``chain_tree`` — P6 constructor: 0 stock nearest-attach Steiner; 1 the
      revived ``construct_chain`` (union of independent paths, the 2014
      paper's build); 2 pure SPH (attach filter dropped).
    * ``root_boltzmann`` — P6 temperature for Boltzmann root choice in the
      legalization phase (0 = stock uniform-among-minima); T in units of the
      zero-occupancy qubit price (one free-qubit hop).
    * ``max_beta`` — stock minorminer knob, surfaced here for P6: finite values
      give the 2014 paper's beta^occ exchange-rate pricing instead of the
      shipped effectively-infinite (lexicographic-overlap) default.
    * ``beta_ramp`` / ``beta_ramp_hold`` — paper3 W2 ramp: after every pass
      that leaves the embedding invalid, the live ``max_beta`` is multiplied
      by ``beta_ramp`` (finite-beta quality pricing gliding toward stock's
      lexicographic feasibility pricing); with ``beta_ramp_hold`` the caller's
      beta is restored once embedded (source-truth caveat: the chainlength
      phase never re-reads qubit prices, so in a plain ``find_embedding``
      call hold is an expected exact tie with hold=0 — T1c pins it).
      ``beta_ramp_hold`` is passed only alongside ``beta_ramp`` (it is
      meaningless without it).  Kwargs-only — no registered ramp arm.

    Drop-in safety: any engaged switch *could* fail where stock MM would
    succeed. With ``fallback`` (default), a failed modified run is retried once
    as **stock minorminer** (all switches off) on the remaining budget —
    guaranteeing success >= stock MM. For paired experiments pass
    ``fallback=False`` so the arm stays pure. The plain ``mmfork`` control
    (every switch at default) is stock MM by construction."""
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

    # Isolated source vertices never reach the C++ core (edge-list input drops
    # them — the §3.23 bug class). Two consequences fixed here: (1) they must be
    # placed on free qubits after the main call; (2) they must be pruned from
    # ``order``, else its length mismatches the core's num_v and the C++ guard
    # silently disables the custom order (observed in E0: <30 ms failures on
    # exactly the disconnected instances, notes.md §4.1 data-quality (i)).
    isolated = [v for v in source.nodes() if source.degree(v) == 0]
    if isolated and order is not None:
        _iso = set(isolated)
        order = [v for v in order if v not in _iso]

    engaged = (order is not None or history_alpha or short_audit or dirty_skip
               or chain_tree or root_boltzmann or max_beta is not None
               or beta_ramp)

    def _run(t, modified):
        params = dict(_DEF)
        params["tries"] = tries
        params["timeout"] = t if t else 1000
        if modified:  # keep every param out entirely on the stock path
            if order is not None:
                params["var_order"] = list(order)
            if history_alpha:
                params["history_alpha"] = float(history_alpha)
            if short_audit:
                params["short_audit"] = int(short_audit)
                params["audit_budget"] = int(audit_budget)
            if dirty_skip:
                params["dirty_skip"] = int(dirty_skip)
            if chain_tree:
                params["chain_tree"] = int(chain_tree)
            if root_boltzmann:
                params["root_boltzmann"] = float(root_boltzmann)
            if max_beta is not None:
                params["max_beta"] = float(max_beta)
            if beta_ramp:
                params["beta_ramp"] = float(beta_ramp)
                params["beta_ramp_hold"] = int(beta_ramp_hold)
        try:
            e = mod.find_embedding(S, T, random_seed=int(seed), **params)
        except Exception as exc:
            logger.debug("forked find_embedding raised: %s", exc)
            return None
        return {int(k): [int(q) for q in v] for k, v in e.items() if v}

    if not S:
        emb = {}  # edgeless source: nothing for the core to do; placement below
    else:
        emb = _run(timeout, engaged)
        # Fallback: a modified run that fails (empty/raised) retries as stock MM
        # so the variants never do worse than minorminer on *success*.
        if (not emb) and engaged and fallback:
            remaining = None if deadline is None else max(1.0, deadline - time.perf_counter())
            emb = _run(remaining, False)

    if emb is not None and isolated:
        used = {q for chain in emb.values() for q in chain}
        free = (q for q in sorted(target.nodes()) if q not in used)
        try:
            for v in isolated:
                emb[int(v)] = [int(next(free))]
        except StopIteration:  # target exhausted — genuine failure
            emb = None

    elapsed = time.perf_counter() - start
    if not emb:
        return {"embedding": {}, "time": elapsed, "success": False, "status": "FAILURE"}
    return {"embedding": emb, "time": elapsed}


class _ForkBase(EmbeddingAlgorithm):
    _order: Optional[str] = None  # key into ORDERINGS, or None for default
    _alpha: float = 0.0           # history step size; 0 = stock cost
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
        alpha = float(kwargs.get("history_alpha", self._alpha) or 0.0)
        fallback = bool(kwargs.get("fallback", True))
        return forked_find_embedding(source_graph, target_graph, order=order,
                                     history_alpha=alpha, fallback=fallback,
                                     seed=int(seed), timeout=timeout, tries=self._tries)


@register_algorithm("mmfork")
class MMFork(_ForkBase):
    """Forked minorminer with every switch off — control == stock minorminer 0.2.22."""
    _order = None


@register_algorithm("mmfork-history")
class MMForkHistory(_ForkBase):
    """Stock minorminer dynamics with the history cost switched on: the routing
    price becomes ``(1 + h_q) * beta^occ(q)`` with the once-per-pass subgradient
    update ``h_q <- max(0, h_q + alpha*(occ(q) - 1))`` (docs/paper2/notes.md §3.5,
    inside real minorminer instead of the Python replica). Order stays stock.
    ``alpha`` defaults to 1.0; override per call with ``history_alpha=``."""
    _alpha = 1.0


def _make(order_name: str) -> type:
    cls = type(f"MMFork_{order_name}", (_ForkBase,),
               {"_order": order_name,
                "__doc__": f"Forked minorminer full search guided by '{order_name}' order."})
    return register_algorithm(f"mmfork-{order_name}")(cls)


_VARIANTS = {nm: _make(nm) for nm in ORDERINGS}  # incl. 'bfs'
