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
    """Placement-first embedder (paper 2 attraction family, notes §3.18+):
    spectral initialization, Laplacian attraction + density-overflow repulsion
    in target-layout coordinates, snapped seeds, then the strongest available
    routing/polish from that placement (default: minorminer seeded cheap
    legalization per round + unconstrained warm-started grind; a fully
    minorminer-free arm via ``backend="native", polish="native"``). See
    ``factored.AttractConfig``."""

    @property
    def version(self) -> str:
        return "0.1.0"

    def embed(self, source_graph, target_graph, timeout: float = 60.0, **kwargs) -> dict:
        seed = kwargs.pop("seed", 0)
        if seed is None:
            seed = 0
        return attract_embed(
            source_graph, target_graph,
            timeout=timeout, seed=int(seed), **kwargs,
        )
