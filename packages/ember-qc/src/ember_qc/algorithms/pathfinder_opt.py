"""
ember_qc/algorithms/pathfinder_opt.py
=====================================
Production PathFinder = the base engine (``pathfinder.py``) wrapped with the
three optimizations verified in the optimization pass
(see ``docs/candidate-algorithms/pf-improvements/``):

  S3  bounded-region routing + early termination   ~3x faster routing, identical chains
  S4  dirty-set incremental LNS schedule           fewer redundant re-sweeps, same moves
  Q3  spur-pruning finishing pass                   ~free ACL reduction

They compose by multiple inheritance because each overrides a *different* method
(run / _lns_improve / _steiner_route):

  _OptimizedRouter -> SpurRouter(run) -> DirtySetRouter(_lns_improve)
                   -> PathFinderBoundedRouter(_steiner_route) -> PathFinderRouter

Measured vs the original engine (``pathfinder-base``), 7-cell grid x 3 seeds:
**time x0.30 (3.3x faster), ACL -0.6%, variance neutral-to-better, 100% valid,
deterministic.** The ``-stacked`` variant additionally seeds from the multilevel
placement (Q1): ACL -1.1%, std -0.048 (a variance win), x0.35.

Rejected in the pass (not baked in): A* routing (+1.7% ACL regression), exact
Dreyfus–Wagner Steiner (no gain), numba fast-Dijkstra (a further ~2x but adds a
dependency and overlaps with bounded routing), parallel restarts (orthogonal,
left as future work).
"""
from ember_qc.registry import register_algorithm
from ember_qc.algorithms.pathfinder import _PathFinderBase
from ember_qc.algorithms.pf_bounded import PathFinderBoundedRouter
from ember_qc.algorithms.pf_dirtyset import DirtySetRouter
from ember_qc.algorithms.pf_spur import SpurRouter


class _OptimizedRouter(SpurRouter, DirtySetRouter, PathFinderBoundedRouter):
    """Production PathFinder router: bounded-region routing + dirty-set LNS + spur-pruning."""
    pass


@register_algorithm("pathfinder")
class PathFinder(_PathFinderBase):
    """PathFinder — MM-seeded negotiated rip-up-and-reroute improver, optimized
    (bounded routing + dirty-set + spur). ~3x faster than the base engine at
    equal-or-better ACL; never worse than minorminer."""
    _params = {"router_cls": _OptimizedRouter, "base_method": "minorminer"}


@register_algorithm("pathfinder-thorough")
class PathFinderThorough(_PathFinderBase):
    """Best-of-4 restarts with deeper reroute — lower ACL & variance, more time."""
    _params = {"router_cls": _OptimizedRouter, "base_method": "minorminer",
               "lns_rounds": 80, "lns_penalty": 4.0, "base_fraction": 0.4,
               "n_restarts": 4}


@register_algorithm("pathfinder-stacked")
class PathFinderStacked(_PathFinderBase):
    """Optimized PathFinder seeded from the multilevel placement instead of MM —
    lower ACL and markedly lower run-to-run variance (Q1 placement-stacking)."""
    _params = {"router_cls": _OptimizedRouter, "base_method": "multilevel"}


@register_algorithm("pathfinder-cold")
class PathFinderCold(_PathFinderBase):
    """Optimized PathFinder standalone — BFS negotiated cold start (no MM seed)."""
    _params = {"router_cls": _OptimizedRouter, "base_method": None}
