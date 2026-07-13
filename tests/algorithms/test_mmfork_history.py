"""
tests/algorithms/test_mmfork_history.py
=======================================
The history-cost switch of the minorminer fork (``history_alpha``):

* **parity** — with the switch off (absent OR explicitly 0.0) the fork returns
  embeddings identical to stock ``minorminer`` for the same seed, so the control
  arm of any history experiment is literally stock minorminer;
* **behavior** — with the switch on, results are valid embeddings and
  deterministic per seed;
* **registry** — ``mmfork-history`` is registered and contract-shaped.

Skipped entirely when the fork extension is not built
(``bash scripts/build_mm_fork.sh``).
"""

import networkx as nx
import pytest

from ember_qc.algorithms.minorminer_forked import (
    _find_so,
    _load_fork,
    forked_find_embedding,
)
from ember_qc.embedding_backend import is_valid_embedding
from ember_qc.registry import ALGORITHM_REGISTRY

pytestmark = pytest.mark.skipif(
    _find_so() is None,
    reason="forked _minorminer not built (bash scripts/build_mm_fork.sh)",
)

SEEDS = range(4)


@pytest.fixture(scope="module")
def instance(chimera_session):
    """A source dense enough that stock MM needs real overfill passes."""
    src = nx.convert_node_labels_to_integers(nx.gnp_random_graph(20, 0.5, seed=11))
    return src, chimera_session


def _stock(src, tgt, seed):
    import minorminer

    emb = minorminer.find_embedding(
        list(src.edges()), list(tgt.edges()), random_seed=seed)
    return {int(k): sorted(int(q) for q in v) for k, v in emb.items() if v}


def _fork(src, tgt, seed, **kwargs):
    fork = _load_fork()
    params = dict(max_no_improvement=10, timeout=1000, tries=10,
                  chainlength_patience=10)
    params.update(kwargs)
    emb = fork.find_embedding(
        list(src.edges()), list(tgt.edges()), random_seed=seed, **params)
    return {int(k): sorted(int(q) for q in v) for k, v in emb.items() if v}


class TestParity:
    def test_param_absent_matches_stock(self, instance):
        src, tgt = instance
        for seed in SEEDS:
            assert _fork(src, tgt, seed) == _stock(src, tgt, seed)

    def test_alpha_zero_matches_stock(self, instance):
        """Plumbing must be inert at 0.0, not merely 'usually equal'."""
        src, tgt = instance
        for seed in SEEDS:
            assert _fork(src, tgt, seed, history_alpha=0.0) == _stock(src, tgt, seed)


class TestBehavior:
    def test_alpha_on_gives_valid_embedding(self, instance):
        src, tgt = instance
        emb = _fork(src, tgt, 0, history_alpha=1.0)
        assert len(emb) == src.number_of_nodes()
        assert is_valid_embedding(emb, src, tgt)

    def test_alpha_on_is_deterministic_per_seed(self, instance):
        src, tgt = instance
        a = _fork(src, tgt, 3, history_alpha=1.0)
        b = _fork(src, tgt, 3, history_alpha=1.0)
        assert a == b

    def test_wrapper_threads_alpha_and_fallback(self, instance):
        src, tgt = instance
        r = forked_find_embedding(src, tgt, history_alpha=1.0, seed=0,
                                  timeout=30.0, fallback=False)
        assert r["embedding"], "raw history arm failed on an easy instance"
        assert is_valid_embedding(r["embedding"], src, tgt)


class TestRegistry:
    def test_registered(self):
        assert "mmfork-history" in ALGORITHM_REGISTRY

    def test_contract_shape_and_validity(self, instance):
        src, tgt = instance
        result = ALGORITHM_REGISTRY["mmfork-history"].embed(
            src, tgt, timeout=30.0, seed=0)
        assert isinstance(result, dict) and "embedding" in result and "time" in result
        assert is_valid_embedding(result["embedding"], src, tgt)

    def test_per_call_alpha_override(self, instance):
        """history_alpha=0 through the registry entry == plain mmfork control."""
        src, tgt = instance
        a = ALGORITHM_REGISTRY["mmfork-history"].embed(
            src, tgt, timeout=30.0, seed=1, history_alpha=0.0)
        b = ALGORITHM_REGISTRY["mmfork"].embed(src, tgt, timeout=30.0, seed=1)
        assert a["embedding"] == b["embedding"]
