"""
ember_qc/registry.py
=====================
Algorithm registry infrastructure.

Provides:
- EmbeddingAlgorithm  — abstract base class all algorithms subclass
- @register_algorithm — decorator that registers a class and injects cls.name
- ALGORITHM_REGISTRY  — dict[str, EmbeddingAlgorithm instance]
- validate_embedding  — correctness check for produced embeddings
- infer_chimera_dims  — helper used by OCT and ATOM wrappers

Algorithm implementations live in ember_qc/algorithms/.
They are imported at the bottom of this file to trigger registration.
"""

import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import dwave_networkx as dnx
import networkx as nx
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


# ==============================================================================
# REGISTRY
# ==============================================================================

ALGORITHM_REGISTRY: Dict[str, 'EmbeddingAlgorithm'] = {}


def register_algorithm(name: str):
    """Decorator to register an embedding algorithm.

    Injects the registered name onto the class as ``cls.name`` so it is
    accessible from the class and all instances without a registry lookup.

    Usage:
        @register_algorithm("my_algo")
        class MyAlgorithm(EmbeddingAlgorithm):
            ...
    """
    def decorator(cls):
        cls.name = name
        ALGORITHM_REGISTRY[name] = cls()
        return cls
    return decorator


def list_algorithms() -> List[str]:
    """Return list of all registered algorithm names."""
    return list(ALGORITHM_REGISTRY.keys())


def get_algorithm(name: str) -> Optional['EmbeddingAlgorithm']:
    """Get a registered algorithm instance by name."""
    return ALGORITHM_REGISTRY.get(name)


# ==============================================================================
# BASE CLASS
# ==============================================================================

class EmbeddingAlgorithm(ABC):
    """Abstract base class for embedding algorithms.

    Subclass this and implement ``embed()``, then decorate with
    ``@register_algorithm("name")`` to make it available in ember-qc.

    Availability attributes (set in subclasses that have extra requirements;
    base-class defaults mean "no extra requirements"):

        _requires             list of pip package names that must be importable
        _binary               Path / callable returning Path / None
        _install_instruction  shown to the user when is_available() returns False
    """

    @abstractmethod
    def embed(self, source_graph: nx.Graph, target_graph: nx.Graph,
              timeout: float = 60.0, **kwargs) -> Optional[Dict]:
        """Find a minor embedding of source_graph into target_graph.

        Returns:
            Dict with at minimum:
                'embedding': Dict[int, List[int]] mapping logical nodes to chains
                'time':      float elapsed seconds
            Or None if embedding fails.
        """

    _uses_subprocess: bool = False

    supported_topologies: Optional[List[str]] = None
    """Topology families this algorithm supports. None means all topologies."""

    # ------------------------------------------------------------------
    # Availability
    # ------------------------------------------------------------------

    _requires: List[str] = []
    _binary: Optional[Path] = None
    _install_instruction: str = ""

    @classmethod
    def is_available(cls) -> tuple:
        """Check whether this algorithm can run on the current machine.

        ``_binary`` may be a Path, string, or zero-argument callable returning
        a Path (useful for env-var-based dynamic resolution).

        Returns:
            (True, "")           all requirements met
            (False, reason_str)  something missing
        """
        import importlib

        missing_pkgs = [p for p in cls._requires
                        if importlib.util.find_spec(p) is None]

        binary_path = cls._binary() if callable(cls._binary) else cls._binary
        binary_missing = binary_path is not None and not Path(binary_path).exists()

        if not missing_pkgs and not binary_missing:
            return (True, "")

        parts = []
        if missing_pkgs:
            parts.append(f"missing packages: {', '.join(missing_pkgs)}")
        if binary_missing:
            parts.append(f"binary not installed: {Path(binary_path).name}")
        reason = "; ".join(parts)
        if cls._install_instruction:
            reason += f"\n  {cls._install_instruction}"
        return (False, reason)

    @property
    def version(self) -> str:
        """Algorithm version string. Override in subclasses."""
        return "unknown"

    @property
    def description(self) -> str:
        """Short human-readable description."""
        return self.__class__.__doc__ or self.__class__.__name__


# ==============================================================================
# VALIDATION
# ==============================================================================

def validate_embedding(embedding: Dict[int, list], source_graph: nx.Graph,
                       target_graph: nx.Graph) -> bool:
    """Validate that an embedding is a correct minor embedding.

    Delegates to :func:`ember_qc.validation.validate_layer1`, which is the
    canonical implementation. Returns True if all structural checks pass,
    False otherwise (validation errors are logged at WARNING level, not printed).
    """
    from ember_qc.validation import validate_layer1
    try:
        result = validate_layer1(embedding, source_graph, target_graph)
        if not result.passed:
            logger.warning("validate_embedding: %s — %s", result.check_name, result.detail)
        return result.passed
    except Exception as e:
        logger.error("validate_embedding: unexpected error: %s", e)
        return False


# ==============================================================================
# CHIMERA HELPERS
# ==============================================================================

def infer_chimera_dims(target_graph: nx.Graph) -> Optional[Tuple[int, int, int]]:
    """Try to infer Chimera dimensions (m, n, t) from a target graph."""
    try:
        gd = target_graph.graph
        if 'rows' in gd and 'columns' in gd and 'tile' in gd:
            return (gd['rows'], gd['columns'], gd['tile'])
        num_nodes = target_graph.number_of_nodes()
        for m in range(1, 20):
            for t in [4, 8]:
                if num_nodes == 2 * t * m * m:
                    candidate = dnx.chimera_graph(m, m, t)
                    if (candidate.number_of_nodes() == num_nodes and
                            candidate.number_of_edges() == target_graph.number_of_edges()):
                        return (m, m, t)
    except Exception:
        pass
    return None


# ==============================================================================
# TRIGGER ALGORITHM REGISTRATION
# Must be at the bottom — algorithms/ imports from registry, so this line
# must come after all class/function definitions to avoid circular imports.
# ==============================================================================

import ember_qc.algorithms  # noqa: E402, F401
