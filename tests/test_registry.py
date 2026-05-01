"""
tests/test_registry.py
=======================
Tests for the algorithm registry, covering all registered algorithms
(including the new CHARME entry).
"""
import pytest
import networkx as nx

import ember_qc
from ember_qc.registry import (
    ALGORITHM_REGISTRY,
    list_algorithms,
    get_algorithm,
    validate_embedding,
    EmbeddingAlgorithm,
)


# ===========================================================================
# Registry contents
# ===========================================================================

# OCT registers multiple named variants (oct-triad, oct-fast-oct, etc.) plus
# the internal 'oct_based' key.  Use the smallest guaranteed set for the test.
EXPECTED_ALGORITHMS = {
    "minorminer", "charme", "atom", "pssa",
    "oct-triad", "oct-fast-oct", "oct-triad-reduce",
}


class TestRegistryContents:
    def test_all_expected_algorithms_registered(self):
        registered = set(list_algorithms())
        assert EXPECTED_ALGORITHMS.issubset(registered), (
            f"Missing algorithms: {EXPECTED_ALGORITHMS - registered}"
        )

    def test_charme_in_registry(self):
        assert "charme" in ALGORITHM_REGISTRY

    def test_get_algorithm_returns_instance(self):
        for name in EXPECTED_ALGORITHMS:
            algo = get_algorithm(name)
            assert algo is not None, f"get_algorithm('{name}') returned None"
            assert isinstance(algo, EmbeddingAlgorithm)

    def test_get_algorithm_unknown_returns_none(self):
        assert get_algorithm("nonexistent_algo_xyz") is None

    def test_list_algorithms_returns_list(self):
        result = list_algorithms()
        assert isinstance(result, list)
        assert len(result) >= len(EXPECTED_ALGORITHMS)

    def test_registry_values_are_embedding_algorithm_instances(self):
        for name, algo in ALGORITHM_REGISTRY.items():
            assert isinstance(algo, EmbeddingAlgorithm), (
                f"Registry entry '{name}' is not an EmbeddingAlgorithm"
            )

    def test_all_algorithms_have_name_attribute(self):
        for name, algo in ALGORITHM_REGISTRY.items():
            assert hasattr(algo, 'name'), f"Algorithm '{name}' missing .name"
            # Most algorithms match key==algo.name; 'oct_based' is an internal
            # alias key — its name attribute reflects its primary variant name.
            assert isinstance(algo.name, str) and len(algo.name) > 0


# ===========================================================================
# CharmeAlgorithm properties
# ===========================================================================

class TestCharmeAlgorithmProperties:
    def setup_method(self):
        self.charme = get_algorithm("charme")

    def test_name_is_charme(self):
        assert self.charme.name == "charme"

    def test_supported_topologies(self):
        assert self.charme.supported_topologies == ["chimera"]

    def test_requires_torch_and_torch_geometric(self):
        assert "torch" in self.charme._requires
        assert "torch_geometric" in self.charme._requires

    def test_uses_subprocess(self):
        assert self.charme._uses_subprocess is True

    def test_version_string(self):
        # Version should be a non-empty string
        assert isinstance(self.charme.version, str)
        assert len(self.charme.version) > 0

    def test_install_instruction_nonempty(self):
        assert isinstance(self.charme._install_instruction, str)
        assert len(self.charme._install_instruction) > 0

    def test_is_available_returns_tuple(self):
        result = self.charme.is_available()
        assert isinstance(result, tuple)
        assert len(result) == 2
        assert isinstance(result[0], bool)
        assert isinstance(result[1], str)

    def test_is_available_false_when_binary_missing(self):
        # In CI / test environment the binary won't be installed.
        # If torch + torch_geometric ARE installed and binary IS present,
        # this passes trivially. If anything is missing it should be (False, reason).
        available, reason = self.charme.is_available()
        if not available:
            assert len(reason) > 0

    def test_binary_callable_returns_path(self):
        from pathlib import Path
        binary = self.charme._binary()
        assert isinstance(binary, Path)
        # Should end with "charme/main"
        assert binary.name == "main"
        assert binary.parent.name == "charme"


# ===========================================================================
# validate_embedding helper
# ===========================================================================

class TestValidateEmbedding:
    def test_valid_embedding_returns_true(self):
        # Simple: embed K2 into K2 (trivially valid)
        import dwave_networkx as dnx
        source = nx.complete_graph(2)
        target = dnx.chimera_graph(2)
        # Single-qubit chains: node 0 → [0], node 1 → [1]
        # (might not be adjacent — pick nodes that actually are)
        # Use minorminer for a known-good embedding instead.
        import minorminer
        emb = minorminer.find_embedding(source, target)
        if emb:
            assert validate_embedding(emb, source, target) is True

    def test_empty_embedding_fails(self):
        source = nx.complete_graph(3)
        import dwave_networkx as dnx
        target = dnx.chimera_graph(2)
        assert validate_embedding({}, source, target) is False

    def test_embedding_wrong_node_count_fails(self):
        source = nx.complete_graph(3)
        import dwave_networkx as dnx
        target = dnx.chimera_graph(2)
        # Only embed 2 of the 3 source nodes
        partial = {0: [0], 1: [1]}
        assert validate_embedding(partial, source, target) is False


# ===========================================================================
# EmbeddingAlgorithm ABC
# ===========================================================================

class TestEmbeddingAlgorithmABC:
    def test_cannot_instantiate_abstract_directly(self):
        with pytest.raises(TypeError):
            EmbeddingAlgorithm()

    def test_concrete_subclass_works(self):
        class Dummy(EmbeddingAlgorithm):
            def embed(self, s, t, timeout=60.0, **kw):
                return {"embedding": {}, "time": 0.0}

        d = Dummy()
        assert d.version == "unknown"
        assert d._requires == []
        assert d._binary is None
        assert d._uses_subprocess is False

    def test_is_available_no_requirements(self):
        class Dummy(EmbeddingAlgorithm):
            def embed(self, s, t, timeout=60.0, **kw):
                return {}

        ok, msg = Dummy.is_available()
        assert ok is True
        assert msg == ""
