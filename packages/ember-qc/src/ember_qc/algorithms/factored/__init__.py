"""
ember_qc/algorithms/factored
============================
The **attraction** embedder searches three orders on intact Zephyr.
Contact order determines active bars; spatial orders are packed under a
shared conservative capacity model. Interleaver sweeps are adopted without
a feasibility-veto layer. The default result is native; MinorMiner is an
explicit optional postprocessor. See docs/paper2/three-orders.md.
"""

from ember_qc.registry import EmbeddingAlgorithm, register_algorithm
from ember_qc.algorithms.factored.polish import spur_prune  # noqa: F401
from ember_qc.algorithms.factored.placement import attract_embed  # noqa: F401
from ember_qc.algorithms.factored.ball import ball_polish  # noqa: F401


@register_algorithm("attraction")
class Attraction(EmbeddingAlgorithm):
    """Three-order native Zephyr embedding with optional explicit MM polish."""

    @property
    def version(self) -> str:
        return "0.4.0"

    def embed(self, source_graph, target_graph, timeout: float = 60.0,
              **kwargs) -> dict:
        seed = kwargs.pop("seed", 0)
        if seed is None:
            seed = 0
        return attract_embed(source_graph, target_graph,
                             timeout=timeout, seed=int(seed), **kwargs)
