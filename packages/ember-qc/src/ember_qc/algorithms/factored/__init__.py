"""
ember_qc/algorithms/factored
============================
Minorminer's search with its three separable choices factored into
independently swappable axes —

  * **cost**  (``costs.py``)  — what a qubit costs to route through; default
    ``(1 + h) * beta^occ`` with a subgradient history update. ``alpha=0``
    recovers minorminer's ``diam^occ`` exactly.
  * **tree**  (``trees.py``)  — how a chain is assembled; default SPH Steiner
    tree, with minorminer's union-of-paths as the ablation arm.
  * **order** (``search_orders.py`` + ``"random"``) — the vertex placement /
    rebuild order; default Cuthill–McKee.

The minorminer corner of the family is ``order="random", tree="union",
alpha=0.0``. Design rationale and citations: ``docs/paper2/notes.md``.

This package supersedes the paper-1 Reweave line for new work and imports
nothing from it; that code lives only on the ``new-algorithm`` branch.
"""

from ember_qc.registry import EmbeddingAlgorithm, register_algorithm
from ember_qc.algorithms.factored.costs import (   # noqa: F401 (public API)
    COSTS,
    LinearPathFinderCost,
    NegotiatedCost,
    estimate_diameter,
)
from ember_qc.algorithms.factored.trees import TREES  # noqa: F401
from ember_qc.algorithms.factored.polish import (     # noqa: F401
    polish,
    shorten_chains,
    spur_prune,
)
from ember_qc.algorithms.factored.loop import (       # noqa: F401
    RouterConfig,
    embed_factored,
)
from ember_qc.algorithms.factored.placement import (  # noqa: F401
    AttractConfig,
    attract_embed,
)
from ember_qc.algorithms.factored.ball import ball_polish  # noqa: F401
from ember_qc.algorithms.factored.cross import (  # noqa: F401
    CrossConfig,
    crossfinder_embed,
)


@register_algorithm("factored")
class Factored(EmbeddingAlgorithm):
    """Factored minorminer (paper 2): Cuthill–McKee order, SPH
    Steiner chains, and minorminer's exponential qubit cost extended with a
    decaying (subgradient) history term. All three axes overridable per call
    (``order=``, ``tree=``, ``cost=``, ``alpha=``, ``beta=``, ...);
    see ``factored.RouterConfig``."""

    @property
    def version(self) -> str:
        return "0.1.0"

    def embed(self, source_graph, target_graph, timeout: float = 60.0, **kwargs) -> dict:
        seed = kwargs.pop("seed", 0)
        if seed is None:
            seed = 0
        return embed_factored(
            source_graph, target_graph,
            timeout=timeout, seed=int(seed), **kwargs,
        )


@register_algorithm("attraction")
class Attraction(EmbeddingAlgorithm):
    """Placement-first embedder (paper 2 attraction family, notes §3.18+;
    one pipeline since 2026-07-29, one code path since consolidation 2,
    2026-08-03 — the former ``attraction-stack`` preset IS the default now):
    spectral init, contraction on the stair energy, alternating 1-D interval
    arrangement of the capacity-forced variables (insertion order-search,
    feasibility priced into the gates), snap-aimed wire-coherent seeds, and
    on stride>1 fabrics the exactness completion — valid seeds skip
    minorminer legalization entirely. Finish is the unconstrained
    warm-started grind. Capacity gating makes the dense machinery inert on
    sparse sources. See ``factored.AttractConfig``."""

    @property
    def version(self) -> str:
        return "0.2.0"

    def embed(self, source_graph, target_graph, timeout: float = 60.0, **kwargs) -> dict:
        seed = kwargs.pop("seed", 0)
        if seed is None:
            seed = 0
        return attract_embed(
            source_graph, target_graph,
            timeout=timeout, seed=int(seed), **kwargs,
        )


@register_algorithm("crossfinder")
class Crossfinder(EmbeddingAlgorithm):
    """Iterated rip-and-replace at cross granularity (s3.90): every
    chain is one h-run + one v-run; the single operator evicts a
    variable (or a hull window with ``rip_windows``) and re-places it
    in its exact best cross against the frozen rest — anchor tiles
    scored by interval arithmetic, realized via the frozen-aware lane
    audit, judged on routed reality. minorminer's own loop shape with
    the fabric's native chain shape and a cheap exact audition; no
    orders, no hierarchy, no proxy energy. See ``factored.CrossConfig``."""

    @property
    def version(self) -> str:
        return "0.1.0"

    def embed(self, source_graph, target_graph, timeout: float = 60.0, **kwargs) -> dict:
        seed = kwargs.pop("seed", 0)
        if seed is None:
            seed = 0
        return crossfinder_embed(
            source_graph, target_graph,
            timeout=timeout, seed=int(seed), **kwargs,
        )
