"""
ember_qc/algorithms/factored
============================
The **attraction** embedder: a placement-first minor embedder for
D-Wave fabrics. The hardware graph is a product of a grid and complete
bipartite junctions, so a variable's chain is a horizontal run and a
vertical run whose reaches follow from two orders (x and y) alone. The
plane engine (``plane.py``) optimizes the two orders — a packer DP
derives positions under hard capacity, an interleaver DP re-weaves
sets of variables at their exact optimum — and the hardware adapter
(``field.py``: books, converter, completion, certificate) turns the
layout into qubits. Minorminer is an optional polisher at the end.

Modules: ``plane.py`` (the engine), ``field.py`` (fabric adapter and
the exact kernels), ``placement.py`` (the pipeline and the registry
entry), ``polish.py`` (spur pruning), ``ball.py`` (the ball pass of
the tail), ``trees.py`` (the ball pass's Steiner rebuild).
"""

from ember_qc.registry import EmbeddingAlgorithm, register_algorithm
from ember_qc.algorithms.factored.polish import spur_prune  # noqa: F401
from ember_qc.algorithms.factored.placement import attract_embed  # noqa: F401
from ember_qc.algorithms.factored.ball import ball_polish  # noqa: F401


@register_algorithm("attraction")
class Attraction(EmbeddingAlgorithm):
    """Placement-first embedder: two orders, packer + interleaver DPs,
    exact conversion and completion on course-resolved Zephyr (valid
    seeds skip minorminer legalization), optional minorminer tail."""

    @property
    def version(self) -> str:
        return "0.3.0"

    def embed(self, source_graph, target_graph, timeout: float = 60.0,
              **kwargs) -> dict:
        seed = kwargs.pop("seed", 0)
        if seed is None:
            seed = 0
        return attract_embed(source_graph, target_graph,
                             timeout=timeout, seed=int(seed), **kwargs)
