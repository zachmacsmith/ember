"""
ember_qc/algorithms/reweave_opt.py
=====================================
Production Reweave = the base engine (``reweave.py``) wrapped with the
three optimizations verified in the optimization pass
(see ``docs/candidate-algorithms/pf-improvements/``):

  S3  bounded-region routing + early termination   ~3x faster routing, identical chains
  S4  dirty-set incremental LNS schedule           fewer redundant re-sweeps, same moves
  Q3  spur-pruning finishing pass                   ~free ACL reduction

They compose by multiple inheritance because each overrides a *different* method
(run / _lns_improve / _steiner_route):

  _OptimizedRouter -> SpurRouter(run) -> DirtySetRouter(_lns_improve)
                   -> ReweaveBoundedRouter(_steiner_route) -> ReweaveRouter

Measured vs the original engine (``reweave-base``), 7-cell grid x 3 seeds:
**time x0.30 (3.3x faster), ACL -0.6%, variance neutral-to-better, 100% valid,
deterministic.** The ``-stacked`` variant additionally seeds from the multilevel
placement (Q1): ACL -1.1%, std -0.048 (a variance win), x0.35.

Rejected in the pass (not baked in): A* routing (+1.7% ACL regression), exact
Dreyfus–Wagner Steiner (no gain), numba fast-Dijkstra (a further ~2x but adds a
dependency and overlaps with bounded routing), parallel restarts (orthogonal,
left as future work).
"""
from ember_qc.registry import register_algorithm
from ember_qc.algorithms.reweave import _ReweaveBase
from ember_qc.algorithms.rw_bounded import ReweaveBoundedRouter
from ember_qc.algorithms.rw_dirtyset import DirtySetRouter
from ember_qc.algorithms.rw_spur import SpurRouter


class _OptimizedRouter(SpurRouter, DirtySetRouter, ReweaveBoundedRouter):
    """Production Reweave router: bounded-region routing + dirty-set LNS + spur-pruning."""
    pass


@register_algorithm("reweave")
class Reweave(_ReweaveBase):
    """Reweave — MM-seeded negotiated rip-up-and-reroute improver, optimized
    (bounded routing + dirty-set + spur). ~3x faster than the base engine at
    equal-or-better ACL; never worse than minorminer."""
    _params = {"router_cls": _OptimizedRouter, "base_method": "minorminer"}


@register_algorithm("reweave-thorough")
class ReweaveThorough(_ReweaveBase):
    """Best-of-4 restarts with deeper reroute — lower ACL & variance, more time."""
    _params = {"router_cls": _OptimizedRouter, "base_method": "minorminer",
               "lns_rounds": 80, "lns_penalty": 4.0, "base_fraction": 0.4,
               "n_restarts": 4}


@register_algorithm("reweave-stacked")
class ReweaveStacked(_ReweaveBase):
    """Optimized Reweave seeded from the multilevel placement instead of MM.
    Helps on large, dense Pegasus instances but the multilevel base regresses
    badly on small/sparse ones (net worse than MM pooled over the K=15 grid) —
    an optional variant, not a default."""
    _params = {"router_cls": _OptimizedRouter, "base_method": "multilevel"}


@register_algorithm("reweave-cold")
class ReweaveCold(_ReweaveBase):
    """Optimized Reweave standalone — BFS negotiated cold start (no MM seed)."""
    _params = {"router_cls": _OptimizedRouter, "base_method": None}


@register_algorithm("reweave-mmfork-cuthill")
class ReweaveMMForkCuthill(_ReweaveBase):
    """Optimized Reweave seeded from ``mmfork-cuthill`` (the full minorminer search
    under a fixed Cuthill–McKee order) instead of stock minorminer. Stacks the two
    orthogonal gains — a better-ordered base and the negotiated improver — at
    roughly plain ``reweave``'s cost (the Cuthill base is ${\\sim}1\\times$ MM),
    unlike the portfolio-seeded stack which pays the portfolio's ${\\sim}6\\times$.
    ``base_fraction=0.4`` gives the cheap base a bit less of the budget so the LNS
    gets more."""
    _params = {"router_cls": _OptimizedRouter, "base_method": "mmfork-cuthill",
               "base_fraction": 0.4}


@register_algorithm("reweave-ablate-paths")
class ReweaveAblatePaths(_ReweaveBase):
    """Ablation: MM's inner step inside Reweave — every neighbour attaches to
    the tree ROOT only (union of independent paths) instead of the nearest tree
    node (SPH sharing). Isolates the Steiner-tree ingredient."""
    _params = {"router_cls": _OptimizedRouter, "base_method": "minorminer",
               "union_paths": True}


@register_algorithm("reweave-ablate-nocong")
class ReweaveAblateNoCong(_ReweaveBase):
    """Ablation: congestion pricing off — the LNS shortcut routes at uniform
    cost (lns_penalty=0) instead of pricing occupied qubits. Isolates the
    negotiated-congestion ingredient."""
    _params = {"router_cls": _OptimizedRouter, "base_method": "minorminer",
               "lns_penalty": 0.0}


@register_algorithm("reweave-ablate-both")
class ReweaveAblateBoth(_ReweaveBase):
    """Ablation: both ingredients off (union-of-paths inner step AND uniform
    shortcut cost) — completes the 2x2 factorial with reweave / -paths /
    -nocong."""
    _params = {"router_cls": _OptimizedRouter, "base_method": "minorminer",
               "union_paths": True, "lns_penalty": 0.0}
