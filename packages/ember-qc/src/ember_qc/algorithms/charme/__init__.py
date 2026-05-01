"""
ember_qc.algorithms.charme
==========================
CHARME — PPO-trained RL policy for minor embedding on Chimera.

This package bundles three things:
  - the registered :class:`CharmeAlgorithm` wrapper (exposed at module level)
  - the vendored actor-critic network (:mod:`models`)
  - an inference-only environment (:mod:`env_infer`) + driver (:mod:`inference`)

Training code (PPO update loop, action-order caches, training-data generation)
stays in ``archived/algorithms/charme/`` and is intentionally *not* vendored.

Binary discovery:
  1. ``EMBER_CHARME_BINARY`` env var
  2. ``get_user_binary_dir() / "charme" / "main"``

Weights discovery:
  1. ``EMBER_CHARME_WEIGHTS`` env var
  2. ``<repo-root>/external/CHARME/ppo_CHARME_ep1800.pth`` (editable install)

Runtime constraints imposed by the shipped checkpoint:
  - target topology must be ``chimera_16x16x4``
  - source graph must have exactly 120 nodes
"""
from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Optional

from ember_qc.registry import EmbeddingAlgorithm, register_algorithm

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Public re-export (used directly by tests / notebooks that want inference
# without going through the registry).
# ---------------------------------------------------------------------------
from ember_qc.algorithms.charme.inference import run_charme  # noqa: E402,F401


# ---------------------------------------------------------------------------
# Path helpers
# ---------------------------------------------------------------------------

def _resolve_charme_binary() -> Path:
    for var in ("EMBER_CHARME_BINARY", "CHARME_ATOM_BINARY"):
        val = os.environ.get(var)
        if val:
            return Path(val)
    from ember_qc._paths import get_user_binary_dir
    return get_user_binary_dir() / "charme" / "main"


def _resolve_charme_weights() -> Optional[Path]:
    for var in ("EMBER_CHARME_WEIGHTS", "CHARME_CHECKPOINT"):
        val = os.environ.get(var)
        if val:
            return Path(val)
    # Installed location: downloaded alongside the binary by install-binary charme.
    from ember_qc._paths import get_user_binary_dir
    installed = get_user_binary_dir() / "charme" / "ppo_CHARME_ep1800.pth"
    if installed.exists():
        return installed
    # Editable / repo checkout fallback.
    here = Path(__file__).resolve()
    for parent in here.parents:
        candidate = parent / "external" / "CHARME" / "ppo_CHARME_ep1800.pth"
        if candidate.exists():
            return candidate
    return None


# ---------------------------------------------------------------------------
# Registered algorithm
# ---------------------------------------------------------------------------

@register_algorithm("charme")
class CharmeAlgorithm(EmbeddingAlgorithm):
    """CHARME — PPO-trained RL policy for minor embedding on Chimera."""

    _uses_subprocess = True
    supported_topologies = ['chimera']
    # torch_geometric is the import-time-optional dep; karateclub was a
    # *training*-only dep and is intentionally NOT required for inference.
    _requires = ["torch", "torch_geometric"]
    _binary = staticmethod(_resolve_charme_binary)
    _install_instruction = (
        "Run: ember install-binary charme  "
        "(and pip install torch torch_geometric if missing)"
    )

    @property
    def version(self) -> str:
        return "ep1800"

    def embed(self, source_graph, target_graph, timeout: float = 60.0, **kwargs):
        weights = _resolve_charme_weights()
        if weights is None:
            logger.warning(
                "CHARME weights not found. Set EMBER_CHARME_WEIGHTS or place "
                "ppo_CHARME_ep1800.pth under external/CHARME/.",
            )
            return {
                'embedding': {}, 'time': 0.0, 'success': False, 'status': 'FAILURE',
                'error': "CHARME weights file not found",
            }

        num_samples = int(kwargs.get('num_samples', 1))
        return run_charme(
            source_graph=source_graph,
            target_graph=target_graph,
            weights_path=weights,
            timeout=timeout,
            seed=int(kwargs.get('seed', 42)),
            greedy=bool(kwargs.get('greedy', True)) if num_samples == 1 else False,
            num_samples=num_samples,
        )
