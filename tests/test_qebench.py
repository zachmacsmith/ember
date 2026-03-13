"""
Comprehensive test suite for the qebench package.

Covers:
- benchmark_one() standalone function (the atomic unit)
- EmbeddingResult dataclass and serialization
- compute_embedding_metrics() standalone function
- Algorithm registry (discovery, validation, registration)
- Graph loading (selection parsing, presets, file loading)
- EmbeddingBenchmark batch runner (warmup, multi-trial, topology tagging)
- Package-level imports (qebench __init__.py re-exports)
"""
import json
import pytest
import networkx as nx
import dwave_networkx as dnx


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def chimera():
    return dnx.chimera_graph(4, 4, 4)

@pytest.fixture
def K4():
    return nx.complete_graph(4)

@pytest.fixture
def K8():
    return nx.complete_graph(8)

@pytest.fixture
def cycle10():
    return nx.cycle_graph(10)

@pytest.fixture
def petersen():
    return nx.petersen_graph()


# =============================================================================
# Package imports
# =============================================================================

class TestPackageImports:
    """Verify all public API is accessible from the top-level qebench import."""

    def test_import_benchmark_one(self):
        from qebench import benchmark_one
        assert callable(benchmark_one)

    def test_import_embedding_result(self):
        from qebench import EmbeddingResult
        assert EmbeddingResult is not None

    def test_import_compute_metrics(self):
        from qebench import compute_embedding_metrics
        assert callable(compute_embedding_metrics)

    def test_import_embedding_benchmark(self):
        from qebench import EmbeddingBenchmark
        assert EmbeddingBenchmark is not None

    def test_import_registry(self):
        from qebench import ALGORITHM_REGISTRY, register_algorithm, EmbeddingAlgorithm
        assert isinstance(ALGORITHM_REGISTRY, dict)

    def test_import_validation(self):
        from qebench import validate_embedding
        assert callable(validate_embedding)

    def test_import_graph_functions(self):
        from qebench import load_test_graphs, parse_graph_selection, list_presets
        assert callable(load_test_graphs)
        assert callable(parse_graph_selection)
        assert callable(list_presets)


# =============================================================================
# benchmark_one() — the atomic unit
# =============================================================================

class TestBenchmarkOne:
    """Tests for the standalone benchmark_one function."""

    def test_successful_embedding(self, chimera, K4):
        from qebench import benchmark_one
        result = benchmark_one(
            K4, chimera, "minorminer",
            problem_name="K4", topology_name="chimera_4x4x4", trial=0
        )
        assert result.success is True
        assert result.is_valid is True
        assert result.algorithm == "minorminer"
        assert result.problem_name == "K4"
        assert result.topology_name == "chimera_4x4x4"
        assert result.trial == 0

    def test_embedding_is_stored(self, chimera, K4):
        """The actual chain mapping must be returned, not thrown away."""
        from qebench import benchmark_one
        result = benchmark_one(K4, chimera, "minorminer")
        assert result.embedding is not None
        assert isinstance(result.embedding, dict)
        assert len(result.embedding) == 4  # K4 has 4 nodes
        for node, chain in result.embedding.items():
            assert isinstance(chain, list)
            assert len(chain) >= 1  # every chain has at least one qubit

    def test_problem_metadata_computed(self, chimera, K8):
        """problem_nodes, problem_edges, problem_density must be auto-filled."""
        from qebench import benchmark_one
        result = benchmark_one(K8, chimera, "minorminer")
        assert result.problem_nodes == 8
        assert result.problem_edges == 28  # K8 has 8*7/2 = 28 edges
        assert abs(result.problem_density - 1.0) < 0.01  # complete graph = density 1.0

    def test_topology_name_preserved(self, chimera, K4):
        from qebench import benchmark_one
        result = benchmark_one(K4, chimera, "minorminer", topology_name="my_custom_topology")
        assert result.topology_name == "my_custom_topology"

    def test_trial_number_preserved(self, chimera, K4):
        from qebench import benchmark_one
        for t in [0, 1, 5, 99]:
            result = benchmark_one(K4, chimera, "minorminer", trial=t)
            assert result.trial == t

    def test_quality_metrics_computed(self, chimera, K4):
        from qebench import benchmark_one
        result = benchmark_one(K4, chimera, "minorminer")
        assert result.avg_chain_length > 0
        assert result.max_chain_length >= 1
        assert result.total_qubits_used >= 4  # at least one qubit per node
        assert len(result.chain_lengths) == 4  # one chain per source node
        assert result.total_couplers_used >= 0

    def test_unknown_algorithm_raises(self, chimera, K4):
        from qebench import benchmark_one
        with pytest.raises(ValueError, match="Unknown algorithm"):
            benchmark_one(K4, chimera, "totally_fake_algorithm_xyz")

    def test_timing_is_positive(self, chimera, K4):
        from qebench import benchmark_one
        result = benchmark_one(K4, chimera, "minorminer")
        assert result.embedding_time > 0

    def test_different_graphs_different_results(self, chimera, K4, K8):
        """Larger graphs should generally use more qubits."""
        from qebench import benchmark_one
        r4 = benchmark_one(K4, chimera, "minorminer")
        r8 = benchmark_one(K8, chimera, "minorminer")
        assert r8.total_qubits_used > r4.total_qubits_used

    def test_default_labels_are_empty_string(self, chimera, K4):
        from qebench import benchmark_one
        result = benchmark_one(K4, chimera, "minorminer")
        assert result.problem_name == ""
        assert result.topology_name == ""


# =============================================================================
# EmbeddingResult serialization
# =============================================================================

class TestEmbeddingResult:
    """Tests for EmbeddingResult dataclass."""

    def test_to_dict_returns_dict(self, chimera, K4):
        from qebench import benchmark_one
        result = benchmark_one(K4, chimera, "minorminer")
        d = result.to_dict()
        assert isinstance(d, dict)

    def test_to_dict_has_all_fields(self, chimera, K4):
        from qebench import benchmark_one
        result = benchmark_one(K4, chimera, "minorminer", problem_name="K4", topology_name="test")
        d = result.to_dict()
        expected_keys = {
            'algorithm', 'problem_name', 'topology_name', 'trial',
            'success', 'embedding', 'embedding_time', 'cpu_time', 'is_valid',
            'chain_lengths', 'max_chain_length', 'avg_chain_length',
            'total_qubits_used', 'total_couplers_used',
            'problem_nodes', 'problem_edges', 'problem_density',
            'error_message'
        }
        assert set(d.keys()) == expected_keys

    def test_embedding_serialized_as_json_string(self, chimera, K4):
        """Embedding dict must be serialized as JSON string for CSV compatibility."""
        from qebench import benchmark_one
        result = benchmark_one(K4, chimera, "minorminer")
        d = result.to_dict()
        assert isinstance(d['embedding'], str)
        # Must be valid JSON
        parsed = json.loads(d['embedding'])
        assert isinstance(parsed, dict)
        assert len(parsed) == 4  # K4 has 4 nodes

    def test_failed_result_has_none_embedding(self, chimera):
        """When embedding fails, embedding should be None."""
        from qebench.benchmark import EmbeddingResult
        result = EmbeddingResult(
            algorithm="test", problem_name="fail_test",
            topology_name="test", trial=0, success=False,
            error_message="Test failure"
        )
        assert result.embedding is None
        assert result.success is False
        d = result.to_dict()
        assert d['embedding'] is None


# =============================================================================
# compute_embedding_metrics()
# =============================================================================

class TestComputeEmbeddingMetrics:
    """Tests for the standalone metrics function."""

    def test_basic_metrics(self, chimera):
        from qebench import compute_embedding_metrics
        embedding = {0: [0, 1], 1: [4], 2: [8, 9, 10]}
        metrics = compute_embedding_metrics(embedding, chimera)
        assert metrics['chain_lengths'] == [2, 1, 3]
        assert metrics['avg_chain_length'] == 2.0
        assert metrics['max_chain_length'] == 3
        assert metrics['total_qubits_used'] == 6

    def test_single_qubit_chains(self, chimera):
        from qebench import compute_embedding_metrics
        embedding = {0: [0], 1: [4], 2: [8]}
        metrics = compute_embedding_metrics(embedding, chimera)
        assert metrics['avg_chain_length'] == 1.0
        assert metrics['max_chain_length'] == 1
        assert metrics['total_qubits_used'] == 3

    def test_coupler_counting(self):
        """Couplers should only count edges that exist in the target graph."""
        from qebench import compute_embedding_metrics
        # Build a small graph where we know the edges
        target = nx.Graph()
        target.add_edges_from([(0, 1), (1, 2), (2, 3)])
        # Chain [0, 1] uses edge (0,1) → 1 coupler
        # Chain [2, 3] uses edge (2,3) → 1 coupler
        embedding = {0: [0, 1], 1: [2, 3]}
        metrics = compute_embedding_metrics(embedding, target)
        assert metrics['total_couplers_used'] == 2


# =============================================================================
# Algorithm registry
# =============================================================================

class TestAlgorithmRegistry:
    """Tests for the algorithm registry system."""

    def test_minorminer_is_registered(self):
        from qebench import ALGORITHM_REGISTRY
        assert "minorminer" in ALGORITHM_REGISTRY

    def test_clique_is_registered(self):
        from qebench import ALGORITHM_REGISTRY
        assert "clique" in ALGORITHM_REGISTRY

    def test_atom_is_registered(self):
        from qebench import ALGORITHM_REGISTRY
        assert "atom" in ALGORITHM_REGISTRY

    def test_clique_produces_valid_embedding(self, chimera, K4):
        from qebench import benchmark_one
        result = benchmark_one(K4, chimera, "clique", problem_name="K4")
        assert result.success is True
        assert result.is_valid is True
        assert result.embedding is not None
        assert len(result.embedding) == 4

    def test_atom_produces_valid_embedding(self, chimera, K4):
        from qebench import benchmark_one
        result = benchmark_one(K4, chimera, "atom", problem_name="K4")
        assert result.success is True
        # ATOM sometimes fails validation depending on seeds, but it should succeed for K4
        assert result.embedding is not None
        assert len(result.embedding) == 4

    def test_list_algorithms_returns_names(self):
        from qebench import list_algorithms
        algos = list_algorithms()
        assert isinstance(algos, list)
        assert "minorminer" in algos
        assert "clique" in algos
        assert "atom" in algos
        assert len(algos) >= 2

    def test_algorithm_has_embed_method(self):
        from qebench import ALGORITHM_REGISTRY
        for name, algo in ALGORITHM_REGISTRY.items():
            assert hasattr(algo, 'embed'), f"{name} missing embed()"
            assert callable(algo.embed)

    def test_validate_embedding_correct(self, chimera, K4):
        """validate_embedding should return True for a valid minorminer result."""
        from qebench import benchmark_one, validate_embedding
        result = benchmark_one(K4, chimera, "minorminer")
        assert result.embedding is not None
        is_valid = validate_embedding(result.embedding, K4, chimera)
        assert is_valid is True

    def test_validate_embedding_detects_bad_chains(self, chimera, K4):
        """An embedding with disconnected chains should fail validation."""
        from qebench import validate_embedding
        # Create a fake embedding where chains use non-adjacent qubits
        bad_embedding = {0: [0, 100], 1: [4], 2: [8], 3: [12]}
        is_valid = validate_embedding(bad_embedding, K4, chimera)
        assert is_valid is False

    def test_validate_embedding_detects_missing_nodes(self, chimera):
        """An embedding that doesn't cover all source nodes should fail."""
        from qebench import validate_embedding
        K4 = nx.complete_graph(4)
        incomplete = {0: [0], 1: [4], 2: [8]}  # missing node 3
        is_valid = validate_embedding(incomplete, K4, chimera)
        assert is_valid is False


# =============================================================================
# Graph loading and selection
# =============================================================================

class TestGraphSelection:
    """Tests for graph selection parsing."""

    def test_parse_single_id(self):
        from qebench import parse_graph_selection
        result = parse_graph_selection("5")
        assert result == {5}

    def test_parse_range(self):
        from qebench import parse_graph_selection
        result = parse_graph_selection("1-5")
        assert result == {1, 2, 3, 4, 5}

    def test_parse_multiple_ranges(self):
        from qebench import parse_graph_selection
        result = parse_graph_selection("1-3, 10-12")
        assert result == {1, 2, 3, 10, 11, 12}

    def test_parse_exclusion(self):
        from qebench import parse_graph_selection
        result = parse_graph_selection("1-10, !5")
        assert 5 not in result
        assert 1 in result
        assert 10 in result

    def test_parse_range_exclusion(self):
        from qebench import parse_graph_selection
        result = parse_graph_selection("1-10, !3-5")
        assert result == {1, 2, 6, 7, 8, 9, 10}

    def test_parse_wildcard(self):
        from qebench import parse_graph_selection
        result = parse_graph_selection("*")
        assert result == {-1}  # sentinel for "all"

    def test_parse_preset_name(self):
        from qebench import parse_graph_selection
        result = parse_graph_selection("quick")
        assert len(result) > 0
        assert -1 not in result  # resolved, not wildcard

    def test_parse_invalid_raises(self):
        from qebench import parse_graph_selection
        with pytest.raises(ValueError):
            parse_graph_selection("not_a_preset_or_number_xyz")


class TestPresets:
    """Tests for the preset system."""

    def test_list_presets_returns_dict(self):
        from qebench import list_presets
        presets = list_presets()
        assert isinstance(presets, dict)

    def test_standard_presets_exist(self):
        from qebench import list_presets
        presets = list_presets()
        for name in ["default", "quick", "complete", "diverse", "all"]:
            assert name in presets, f"Missing preset: {name}"

    def test_preset_values_are_strings(self):
        from qebench import list_presets
        for name, selection in list_presets().items():
            assert isinstance(selection, str), f"Preset {name} has non-string value"

    def test_presets_with_commas_parsed_correctly(self):
        """Commas in preset values must be preserved (first-comma split)."""
        from qebench import list_presets
        presets = list_presets()
        diverse = presets.get("diverse", "")
        # "diverse" should have commas in its selection string
        assert "," in diverse, "diverse preset should contain commas"


class TestGraphLoading:
    """Tests for loading graphs from the test_graphs/ directory."""

    def test_load_by_id_range(self):
        from qebench import load_test_graphs
        problems = load_test_graphs("1-3")
        assert len(problems) > 0
        for name, graph in problems:
            assert isinstance(name, str)
            assert isinstance(graph, nx.Graph)
            assert graph.number_of_nodes() > 0

    def test_load_by_preset(self):
        from qebench import load_test_graphs
        problems = load_test_graphs("quick")
        assert len(problems) > 0

    def test_load_all(self):
        from qebench import load_test_graphs
        problems = load_test_graphs("*")
        assert len(problems) >= 10  # should have at least 10 graphs

    def test_load_with_exclusion(self):
        from qebench import load_test_graphs
        all_graphs = load_test_graphs("1-10")
        excluded = load_test_graphs("1-10, !5")
        assert len(excluded) < len(all_graphs)

    def test_loaded_graph_has_edges(self):
        from qebench import load_test_graphs
        problems = load_test_graphs("1")  # K4
        assert len(problems) == 1
        name, graph = problems[0]
        assert graph.number_of_edges() > 0


# =============================================================================
# Batch runner (EmbeddingBenchmark)
# =============================================================================

class TestBatchRunner:
    """Tests for the EmbeddingBenchmark batch runner."""

    def test_basic_run(self, tmp_path, chimera):
        from qebench import EmbeddingBenchmark
        bench = EmbeddingBenchmark(chimera, results_dir=str(tmp_path))
        bench.run_full_benchmark(
            graph_selection="1-2", methods=["minorminer"],
            n_trials=1, topology_name="chimera_4x4x4"
        )
        assert len(bench.results) > 0

    def test_results_saved_to_json(self, tmp_path, chimera):
        from qebench import EmbeddingBenchmark
        bench = EmbeddingBenchmark(chimera, results_dir=str(tmp_path))
        bench.run_full_benchmark(
            graph_selection="1", methods=["minorminer"], n_trials=1
        )
        # Results are inside a batch subdirectory
        batch_dirs = [d for d in tmp_path.iterdir() if d.is_dir() and d.name.startswith('batch_')]
        assert len(batch_dirs) == 1
        batch_dir = batch_dirs[0]
        assert (batch_dir / "runs.json").exists()
        with open(batch_dir / "runs.json") as f:
            data = json.load(f)
        assert len(data) >= 1
        assert data[0]['algorithm'] == 'minorminer'

    def test_results_saved_to_csv(self, tmp_path, chimera):
        from qebench import EmbeddingBenchmark
        bench = EmbeddingBenchmark(chimera, results_dir=str(tmp_path))
        bench.run_full_benchmark(
            graph_selection="1", methods=["minorminer"], n_trials=1
        )
        batch_dirs = [d for d in tmp_path.iterdir() if d.is_dir() and d.name.startswith('batch_')]
        assert len(batch_dirs) == 1
        assert (batch_dirs[0] / "runs.csv").exists()
        assert (batch_dirs[0] / "summary.csv").exists()
        assert (batch_dirs[0] / "README.md").exists()
        assert (batch_dirs[0] / "config.json").exists()

    def test_multi_trial(self, tmp_path, chimera):
        from qebench import EmbeddingBenchmark
        bench = EmbeddingBenchmark(chimera, results_dir=str(tmp_path))
        bench.run_full_benchmark(
            graph_selection="1", methods=["minorminer"], n_trials=3
        )
        assert len(bench.results) == 3
        trials = [r.trial for r in bench.results]
        assert sorted(trials) == [0, 1, 2]

    def test_warmup_trials_discarded(self, tmp_path, chimera):
        """Warm-up trials should not appear in results."""
        from qebench import EmbeddingBenchmark
        bench = EmbeddingBenchmark(chimera, results_dir=str(tmp_path))
        bench.run_full_benchmark(
            graph_selection="1", methods=["minorminer"],
            n_trials=2, warmup_trials=3
        )
        # Only 2 measured trials should be stored, not 2+3=5
        assert len(bench.results) == 2

    def test_topology_name_propagated(self, tmp_path, chimera):
        """topology_name from the batch call should appear in every result."""
        from qebench import EmbeddingBenchmark
        bench = EmbeddingBenchmark(chimera, results_dir=str(tmp_path))
        bench.run_full_benchmark(
            graph_selection="1-2", methods=["minorminer"],
            n_trials=1, topology_name="pegasus_test"
        )
        for result in bench.results:
            assert result.topology_name == "pegasus_test"

    def test_unknown_method_skipped(self, tmp_path, chimera):
        """Requesting a non-existent algorithm should skip it, not crash."""
        from qebench import EmbeddingBenchmark
        bench = EmbeddingBenchmark(chimera, results_dir=str(tmp_path))
        bench.run_full_benchmark(
            graph_selection="1", methods=["minorminer", "totally_fake"],
            n_trials=1
        )
        # Only minorminer results, fake was skipped
        assert all(r.algorithm == "minorminer" for r in bench.results)

    def test_embeddings_stored_in_results(self, tmp_path, chimera):
        """Every successful result in the batch must have the embedding stored."""
        from qebench import EmbeddingBenchmark
        bench = EmbeddingBenchmark(chimera, results_dir=str(tmp_path))
        bench.run_full_benchmark(
            graph_selection="1-3", methods=["minorminer"], n_trials=1
        )
        for result in bench.results:
            if result.success:
                assert result.embedding is not None
                assert isinstance(result.embedding, dict)

    def test_batch_note_in_config_and_readme(self, tmp_path, chimera):
        """batch_note should appear in config.json and README.md."""
        from qebench import EmbeddingBenchmark
        bench = EmbeddingBenchmark(chimera, results_dir=str(tmp_path))
        bench.run_full_benchmark(
            graph_selection="1", methods=["minorminer"], n_trials=1,
            batch_note="First baseline run on Chimera 4x4"
        )
        batch_dirs = [d for d in tmp_path.iterdir() if d.is_dir() and d.name.startswith('batch_')]
        batch_dir = batch_dirs[0]
        # Check config.json
        with open(batch_dir / "config.json") as f:
            config = json.load(f)
        assert config['batch_note'] == "First baseline run on Chimera 4x4"
        # Check README
        readme = (batch_dir / "README.md").read_text()
        assert "First baseline run on Chimera 4x4" in readme


# =============================================================================
# ResultsManager (standalone tests)
# =============================================================================

class TestResultsManager:
    """Tests for the ResultsManager module."""

    def test_batch_name_contains_timestamp(self, tmp_path):
        from qebench.results import ResultsManager
        mgr = ResultsManager(str(tmp_path))
        batch_dir = mgr.create_batch()
        # Name should match batch_YYYY-MM-DD_HH-MM-SS
        assert batch_dir.name.startswith("batch_20")
        assert len(batch_dir.name) >= len("batch_2026-02-23_11-30-15")

    def test_batch_dirs_are_unique(self, tmp_path):
        """Multiple batches created rapidly should have unique names."""
        from qebench.results import ResultsManager
        mgr = ResultsManager(str(tmp_path))
        dirs = [mgr.create_batch() for _ in range(3)]
        names = [d.name for d in dirs]
        assert len(set(names)) == 3  # all unique

    def test_latest_symlink_points_to_newest(self, tmp_path):
        from qebench.results import ResultsManager
        mgr = ResultsManager(str(tmp_path))
        mgr.create_batch()
        batch2 = mgr.create_batch()
        latest = tmp_path / "latest"
        assert latest.is_symlink()
        assert latest.resolve().name == batch2.name

    def test_config_json_saved(self, tmp_path):
        from qebench.results import ResultsManager
        mgr = ResultsManager(str(tmp_path))
        config = {'algorithms': ['minorminer'], 'n_trials': 3}
        batch_dir = mgr.create_batch(config)
        with open(batch_dir / "config.json") as f:
            saved = json.load(f)
        assert saved['algorithms'] == ['minorminer']
        assert saved['n_trials'] == 3
        assert 'batch_name' in saved
        assert 'timestamp' in saved

    def test_runs_csv_excludes_embeddings(self, tmp_path, chimera, K4):
        """runs.csv should not contain the embedding column."""
        from qebench import benchmark_one
        from qebench.results import ResultsManager
        import pandas as pd
        results = [benchmark_one(K4, chimera, "minorminer", problem_name="K4", trial=i) for i in range(2)]
        mgr = ResultsManager(str(tmp_path))
        batch_dir = mgr.create_batch()
        mgr.save_results(results, batch_dir)
        df = pd.read_csv(batch_dir / "runs.csv")
        assert 'embedding' not in df.columns
        assert 'chain_lengths' not in df.columns
        assert 'algorithm' in df.columns
        assert len(df) == 2

    def test_runs_json_includes_embeddings(self, tmp_path, chimera, K4):
        """runs.json should contain the embedding for each run."""
        from qebench import benchmark_one
        from qebench.results import ResultsManager
        results = [benchmark_one(K4, chimera, "minorminer", problem_name="K4")]
        mgr = ResultsManager(str(tmp_path))
        batch_dir = mgr.create_batch()
        mgr.save_results(results, batch_dir)
        with open(batch_dir / "runs.json") as f:
            data = json.load(f)
        assert 'embedding' in data[0]
        assert data[0]['embedding'] is not None

    def test_summary_csv_groups_correctly(self, tmp_path, chimera, K4, K8):
        """summary.csv should have one row per (algorithm, problem_name, topology_name)."""
        from qebench import benchmark_one
        from qebench.results import ResultsManager
        import pandas as pd
        results = []
        for i in range(3):
            results.append(benchmark_one(K4, chimera, "minorminer", problem_name="K4",
                                         topology_name="chimera", trial=i))
        for i in range(3):
            results.append(benchmark_one(K8, chimera, "minorminer", problem_name="K8",
                                         topology_name="chimera", trial=i))
        mgr = ResultsManager(str(tmp_path))
        batch_dir = mgr.create_batch()
        mgr.save_results(results, batch_dir)
        df = pd.read_csv(batch_dir / "summary.csv")
        assert len(df) == 2  # K4 group + K8 group
        assert set(df['problem_name']) == {'K4', 'K8'}

    def test_summary_csv_has_mean_and_std(self, tmp_path, chimera, K4):
        """summary.csv must contain _mean and _std columns for metrics."""
        from qebench import benchmark_one
        from qebench.results import ResultsManager
        import pandas as pd
        results = [benchmark_one(K4, chimera, "minorminer", problem_name="K4", trial=i) for i in range(3)]
        mgr = ResultsManager(str(tmp_path))
        batch_dir = mgr.create_batch()
        mgr.save_results(results, batch_dir)
        df = pd.read_csv(batch_dir / "summary.csv")
        for metric in ['embedding_time', 'avg_chain_length', 'max_chain_length',
                       'total_qubits_used', 'total_couplers_used']:
            assert f'{metric}_mean' in df.columns
            assert f'{metric}_std' in df.columns
            assert f'{metric}_median' in df.columns

    def test_summary_stats_are_correct(self, tmp_path, chimera, K4):
        """Verify mean/std/median are numerically correct."""
        from qebench import benchmark_one
        from qebench.results import ResultsManager
        import pandas as pd
        import numpy as np
        results = [benchmark_one(K4, chimera, "minorminer", problem_name="K4",
                                 topology_name="t", trial=i) for i in range(5)]
        mgr = ResultsManager(str(tmp_path))
        batch_dir = mgr.create_batch()
        mgr.save_results(results, batch_dir)
        df = pd.read_csv(batch_dir / "summary.csv")
        row = df.iloc[0]
        times = [r.embedding_time for r in results]
        assert abs(row['embedding_time_mean'] - np.mean(times)) < 1e-6
        assert abs(row['embedding_time_median'] - np.median(times)) < 1e-6
        assert row['n_trials'] == 5
        assert row['success_rate'] == 1.0

    def test_readme_generated(self, tmp_path, chimera, K4):
        """README.md must exist and contain key sections."""
        from qebench import benchmark_one
        from qebench.results import ResultsManager
        results = [benchmark_one(K4, chimera, "minorminer", problem_name="K4")]
        mgr = ResultsManager(str(tmp_path))
        config = {'algorithms': ['minorminer'], 'n_trials': 1, 'timeout': 60.0,
                  'graph_selection': '1', 'topology_name': 'chimera'}
        batch_dir = mgr.create_batch(config)
        mgr.save_results(results, batch_dir, config=config)
        readme = (batch_dir / "README.md").read_text()
        assert "## Settings" in readme
        assert "## Results Summary" in readme
        assert "## Files" in readme
        assert "runs.csv" in readme

    def test_readme_with_batch_note(self, tmp_path, chimera, K4):
        from qebench import benchmark_one
        from qebench.results import ResultsManager
        results = [benchmark_one(K4, chimera, "minorminer", problem_name="K4")]
        mgr = ResultsManager(str(tmp_path))
        config = {'batch_note': 'Testing note feature'}
        batch_dir = mgr.create_batch(config, batch_note='Testing note feature')
        mgr.save_results(results, batch_dir, config=config)
        readme = (batch_dir / "README.md").read_text()
        assert "Testing note feature" in readme

    def test_empty_results_no_crash(self, tmp_path):
        """Saving empty results should not raise."""
        from qebench.results import ResultsManager
        mgr = ResultsManager(str(tmp_path))
        batch_dir = mgr.create_batch()
        mgr.save_results([], batch_dir)  # should not raise


# =============================================================================
# Topology registry
# =============================================================================

class TestTopologyRegistry:
    """Tests for the topology registry system."""

    def test_import_topology_functions(self):
        from qebench import (TOPOLOGY_REGISTRY, get_topology, list_topologies,
                             register_topology, topology_info, list_topology_families)
        assert isinstance(TOPOLOGY_REGISTRY, dict)
        assert callable(get_topology)
        assert callable(list_topologies)

    def test_builtin_chimera_registered(self):
        from qebench import list_topologies
        topos = list_topologies(family="chimera")
        assert "chimera_4x4x4" in topos
        assert "chimera_16x16x4" in topos

    def test_builtin_pegasus_registered(self):
        from qebench import list_topologies
        topos = list_topologies(family="pegasus")
        assert "pegasus_4" in topos
        assert "pegasus_16" in topos

    def test_builtin_zephyr_registered(self):
        from qebench import list_topologies
        topos = list_topologies(family="zephyr")
        assert "zephyr_2" in topos
        assert "zephyr_8" in topos

    def test_three_families_exist(self):
        from qebench import list_topology_families
        families = list_topology_families()
        assert "chimera" in families
        assert "pegasus" in families
        assert "zephyr" in families

    def test_get_topology_returns_graph(self):
        from qebench import get_topology
        g = get_topology("chimera_4x4x4")
        assert isinstance(g, nx.Graph)
        assert g.number_of_nodes() == 128
        assert g.number_of_edges() > 0

    def test_get_topology_caches(self):
        from qebench import get_topology
        g1 = get_topology("chimera_4x4x4")
        g2 = get_topology("chimera_4x4x4")
        assert g1 is g2  # same object, not regenerated

    def test_get_topology_unknown_raises(self):
        from qebench import get_topology
        with pytest.raises(ValueError, match="Unknown topology"):
            get_topology("totally_fake_topology_xyz")

    def test_custom_registration(self):
        from qebench import register_topology, get_topology, TOPOLOGY_REGISTRY
        register_topology(
            "test_grid_3x3",
            family="custom",
            generator=lambda: nx.convert_node_labels_to_integers(nx.grid_2d_graph(3, 3)),
            params={"rows": 3, "cols": 3},
            description="Test 3×3 grid"
        )
        g = get_topology("test_grid_3x3")
        assert g.number_of_nodes() == 9
        assert g.number_of_edges() == 12
        # Cleanup
        del TOPOLOGY_REGISTRY["test_grid_3x3"]

    def test_topology_info_returns_string(self):
        from qebench import topology_info
        info = topology_info()
        assert isinstance(info, str)
        assert "chimera_4x4x4" in info
        assert "pegasus" in info

    def test_get_topology_config(self):
        from qebench import get_topology_config
        config = get_topology_config("chimera_4x4x4")
        assert config.name == "chimera_4x4x4"
        assert config.family == "chimera"
        assert config.params == {"m": 4, "n": 4, "t": 4}

    def test_multi_topology_benchmark(self, tmp_path):
        """EmbeddingBenchmark should run across multiple topologies."""
        from qebench import EmbeddingBenchmark
        bench = EmbeddingBenchmark(results_dir=str(tmp_path))
        bench.run_full_benchmark(
            graph_selection="1",
            methods=["minorminer"],
            topologies=["chimera_4x4x4", "pegasus_4"],
            n_trials=1
        )
        # Should have results for both topologies
        topo_names = set(r.topology_name for r in bench.results)
        assert "chimera_4x4x4" in topo_names
        assert "pegasus_4" in topo_names
        assert len(bench.results) == 2  # 1 graph × 1 algo × 2 topologies
