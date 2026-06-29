"""
ember_qc_learn — learning-based minor-embedding for Ember.

Amortized models (GNN seed-predictor, GNN direct soft-assignment, Graph-VAE,
retrieval) trained on PathFinder/minorminer-optimized embeddings, then benchmarked
head-to-head vs PF/MM through ember_qc's registry. Importing this package
registers the available ``learned-*`` algorithms (best-effort; skipped if torch or
a checkpoint is unavailable, so ``import ember_qc_learn`` never hard-fails).
"""
__version__ = "0.1.0"

try:  # registering the benchmark adapters needs torch + checkpoints; stay soft.
    from ember_qc_learn import algorithms  # noqa: F401
except Exception:  # pragma: no cover
    pass
