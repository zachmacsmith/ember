"""
tests/algorithms/test_reweave.py
===================================
Tests specific to the Reweave negotiated rip-up-and-reroute embedder
(ember_qc.algorithms.reweave), beyond the generic algorithm contract suite.
"""
import networkx as nx
import dwave_networkx as dnx
import pytest

from ember_qc import benchmark_one
from ember_qc.registry import ALGORITHM_REGISTRY, validate_embedding


@pytest.fixture(scope="module")
def chimera():
    return dnx.chimera_graph(4, 4, 4)


PATHFINDER_VARIANTS = ["reweave", "reweave-thorough", "reweave-cold"]


class TestRegistered:
    def test_variants_registered(self):
        for name in PATHFINDER_VARIANTS:
            assert name in ALGORITHM_REGISTRY


class TestValidEmbeddings:
    @pytest.mark.parametrize("name", PATHFINDER_VARIANTS)
    def test_produces_valid_embedding(self, name, chimera):
        r = benchmark_one(nx.complete_graph(6), chimera, name, timeout=15.0, seed=0)
        assert r.success and r.is_valid

    @pytest.mark.parametrize("name", PATHFINDER_VARIANTS)
    def test_embedding_passes_independent_validation(self, name, chimera):
        algo = ALGORITHM_REGISTRY[name]
        emb = algo.embed(nx.cycle_graph(8), chimera, timeout=15.0, seed=1)["embedding"]
        assert emb
        assert validate_embedding(emb, nx.cycle_graph(8), chimera)


class TestNeverWorseThanBase:
    """The defining guarantee: the MM-seeded improver never returns a worse
    embedding than its minorminer base for the same seed."""

    @pytest.mark.parametrize("seed", [0, 1, 2])
    def test_reweave_no_worse_than_minorminer(self, seed, chimera):
        source = nx.gnp_random_graph(14, 0.45, seed=99)
        source = nx.convert_node_labels_to_integers(source)
        mm = benchmark_one(source, chimera, "minorminer", timeout=15.0, seed=seed)
        pf = benchmark_one(source, chimera, "reweave", timeout=15.0, seed=seed)
        if not (mm.success and pf.success):
            pytest.skip("base or improver failed to embed this instance")
        # improver tracks the best valid embedding seen, so it cannot regress
        assert pf.total_qubits_used <= mm.total_qubits_used
        assert pf.avg_chain_length <= mm.avg_chain_length + 1e-9


class TestColdStartStandalone:
    def test_cold_start_needs_no_minorminer_seed(self, chimera):
        # reweave-cold sets base_method=None — it must still embed small graphs
        r = benchmark_one(nx.complete_graph(4), chimera, "reweave-cold",
                          timeout=15.0, seed=0)
        assert r.success and r.is_valid
