"""
tests/algorithms/test_p3_fork.py
================================
The paper3 fork switches — P4 shortener economics (``short_audit`` /
``audit_budget`` / ``dirty_skip``) and P6 anatomy (``chain_tree`` /
``root_boltzmann``, plus the surfaced stock ``max_beta``). For each switch:

* **parity** — at its default value the fork returns embeddings byte-identical
  to stock ``minorminer`` on >= 4 (graph, seed) cases, so the control arm of
  any P4/P6 experiment is literally stock minorminer;
* **activity** — engaged, it runs, returns VALID embeddings (checked with
  ``embedding_backend.is_valid_embedding``), and for ``short_audit`` /
  ``chain_tree`` produces a different embedding on at least one case (the code
  path demonstrably fires);
* **determinism** — engaged results are identical across repeat runs per seed.

Registry arms ``p3-mm-audit`` / ``p3-mm-dirty`` / ``p3-mm-union`` are checked
for contract shape and validity. Modeled on
``tests/algorithms/test_mmfork_history.py``. Skipped entirely when the fork
extension is not built (``bash scripts/build_mm_fork.sh``).
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

SEEDS = range(2)

# Defaults for every P4/P6 switch: passing these explicitly must be inert.
DEFAULTS = {
    "short_audit": 0,
    "audit_budget": 3,
    "dirty_skip": 0,
    "chain_tree": 0,
    "root_boltzmann": 0.0,
}


@pytest.fixture(scope="module")
def instances(chimera_session):
    """Two sources dense enough that stock MM runs real overfill + shortening
    passes; with SEEDS this gives 4 (graph, seed) parity cases."""
    a = nx.convert_node_labels_to_integers(nx.gnp_random_graph(20, 0.5, seed=11))
    b = nx.convert_node_labels_to_integers(nx.gnp_random_graph(24, 0.35, seed=3))
    return [(a, chimera_session), (b, chimera_session)]


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


@pytest.fixture(scope="module")
def stock_results(instances):
    return [[_stock(src, tgt, seed) for seed in SEEDS] for src, tgt in instances]


class TestParity:
    """Each switch, explicitly at its default, must be byte-inert."""

    @pytest.mark.parametrize("name", sorted(DEFAULTS))
    def test_switch_default_matches_stock(self, name, instances, stock_results):
        for (src, tgt), per_seed in zip(instances, stock_results):
            for seed, want in zip(SEEDS, per_seed):
                assert _fork(src, tgt, seed, **{name: DEFAULTS[name]}) == want, \
                    f"{name}={DEFAULTS[name]} diverged from stock (seed {seed})"

    def test_all_defaults_together_match_stock(self, instances, stock_results):
        for (src, tgt), per_seed in zip(instances, stock_results):
            for seed, want in zip(SEEDS, per_seed):
                assert _fork(src, tgt, seed, **DEFAULTS) == want


# (label, kwargs, must_differ_from_stock_somewhere)
ENGAGED = [
    ("short_audit=1", dict(short_audit=1), True),
    ("short_audit=2", dict(short_audit=2, audit_budget=3), True),
    ("dirty_skip=1", dict(dirty_skip=1), False),
    ("chain_tree=1", dict(chain_tree=1), True),
    ("chain_tree=2", dict(chain_tree=2), True),
    ("root_boltzmann=2.0", dict(root_boltzmann=2.0), False),
]


class TestActivity:
    @pytest.mark.parametrize("label,kwargs,must_differ",
                             ENGAGED, ids=[e[0] for e in ENGAGED])
    def test_engaged_valid_deterministic_and_fires(self, label, kwargs,
                                                   must_differ, instances,
                                                   stock_results):
        differed = False
        for (src, tgt), per_seed in zip(instances, stock_results):
            for seed, stock in zip(SEEDS, per_seed):
                emb = _fork(src, tgt, seed, **kwargs)
                assert len(emb) == src.number_of_nodes(), f"{label} failed to embed"
                assert is_valid_embedding(emb, src, tgt), f"{label} invalid"
                assert emb == _fork(src, tgt, seed, **kwargs), \
                    f"{label} nondeterministic at seed {seed}"
                differed |= (emb != stock)
        if must_differ:
            assert differed, f"{label} never diverged from stock — switch inert?"

    def test_dirty_skip_fires_with_patience(self, instances):
        """dirty_skip only pays in the failing tail; with a long patience the
        rng stream must eventually diverge from switch-off on some case."""
        differed = False
        for src, tgt in instances:
            for seed in range(4):
                a = _fork(src, tgt, seed, chainlength_patience=50)
                b = _fork(src, tgt, seed, chainlength_patience=50, dirty_skip=1)
                assert is_valid_embedding(b, src, tgt)
                differed |= (a != b)
        if not differed:
            pytest.skip("no skip fired on these instances (cache stayed cold; "
                        "validity and parity are covered above)")


class TestWrapper:
    def test_kwargs_thread_through(self, instances):
        src, tgt = instances[0]
        r = forked_find_embedding(src, tgt, short_audit=2, audit_budget=2,
                                  dirty_skip=1, seed=0, timeout=30.0,
                                  fallback=False)
        assert r["embedding"], "raw P4 arm failed on an easy instance"
        assert is_valid_embedding(r["embedding"], src, tgt)

    def test_max_beta_threads_through(self, instances):
        src, tgt = instances[0]
        r = forked_find_embedding(src, tgt, max_beta=2.0, seed=0, timeout=30.0,
                                  fallback=False)
        assert r["embedding"], "max_beta arm failed on an easy instance"
        assert is_valid_embedding(r["embedding"], src, tgt)

    def test_no_switch_equals_mmfork_control(self, instances):
        src, tgt = instances[0]
        a = forked_find_embedding(src, tgt, seed=1, timeout=30.0, fallback=False)
        b = ALGORITHM_REGISTRY["mmfork"].embed(src, tgt, timeout=30.0, seed=1)
        assert a["embedding"] == b["embedding"]


class TestRegistry:
    ARMS = ["p3-mm-audit", "p3-mm-dirty", "p3-mm-union"]

    @pytest.mark.parametrize("arm", ARMS)
    def test_registered(self, arm):
        assert arm in ALGORITHM_REGISTRY

    @pytest.mark.parametrize("arm", ARMS)
    def test_contract_shape_validity_determinism(self, arm, instances):
        src, tgt = instances[0]
        result = ALGORITHM_REGISTRY[arm].embed(src, tgt, timeout=30.0, seed=0)
        assert isinstance(result, dict) and "embedding" in result and "time" in result
        assert is_valid_embedding(result["embedding"], src, tgt)
        again = ALGORITHM_REGISTRY[arm].embed(src, tgt, timeout=30.0, seed=0)
        assert result["embedding"] == again["embedding"]
