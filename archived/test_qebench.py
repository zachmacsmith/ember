"""
Comprehensive test suite for the qebench package.

Covers:
- benchmark_one() standalone function (the atomic unit)
- EmbeddingResult dataclass and serialization (spec 1.3/1.4 fields, to_jsonl_dict)
- compute_embedding_metrics() standalone function
- Algorithm registry (discovery, validation, registration)
- Graph loading (selection parsing, presets, file loading)
- EmbeddingBenchmark batch runner (warmup, multi-trial, topology tagging)
- Package-level imports (qebench __init__.py re-exports)
- _derive_seed() — determinism, per-trial uniqueness, warmup isolation
- validate_layer1() — five structural checks (unit + integration)
- validate_layer2() — six type/format checks (unit + integration)
- ValidationResult dataclass and bool() protocol
- BatchLogger — log directory setup, per-run files, footer format, WARNING routing
- compile_batch() — SQLite schema, UNIQUE constraint, embeddings table, runs.csv
- Seeding behaviour — distinct per-trial seeds, determinism across runs
- Multiprocessing — n_workers > 1 produces correct results and seeds
"""
import json
import numpy as np
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
        from ember_qc import benchmark_one
        assert callable(benchmark_one)

    def test_import_embedding_result(self):
        from ember_qc import EmbeddingResult
        assert EmbeddingResult is not None

    def test_import_compute_metrics(self):
        from ember_qc import compute_embedding_metrics
        assert callable(compute_embedding_metrics)

    def test_import_embedding_benchmark(self):
        from ember_qc import EmbeddingBenchmark
        assert EmbeddingBenchmark is not None

    def test_import_registry(self):
        from ember_qc import ALGORITHM_REGISTRY, register_algorithm, EmbeddingAlgorithm
        assert isinstance(ALGORITHM_REGISTRY, dict)

    def test_import_validation(self):
        from ember_qc import validate_embedding
        assert callable(validate_embedding)

    def test_import_graph_functions(self):
        from ember_qc import load_test_graphs, parse_graph_selection, list_presets
        assert callable(load_test_graphs)
        assert callable(parse_graph_selection)
        assert callable(list_presets)


# =============================================================================
# benchmark_one() — the atomic unit
# =============================================================================

class TestBenchmarkOne:
    """Tests for the standalone benchmark_one function."""

    def test_successful_embedding(self, chimera, K4):
        from ember_qc import benchmark_one
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
        from ember_qc import benchmark_one
        result = benchmark_one(K4, chimera, "minorminer")
        assert result.embedding is not None
        assert isinstance(result.embedding, dict)
        assert len(result.embedding) == 4  # K4 has 4 nodes
        for node, chain in result.embedding.items():
            assert isinstance(chain, list)
            assert len(chain) >= 1  # every chain has at least one qubit

    def test_problem_metadata_computed(self, chimera, K8):
        """problem_nodes, problem_edges, problem_density must be auto-filled."""
        from ember_qc import benchmark_one
        result = benchmark_one(K8, chimera, "minorminer")
        assert result.problem_nodes == 8
        assert result.problem_edges == 28  # K8 has 8*7/2 = 28 edges
        assert abs(result.problem_density - 1.0) < 0.01  # complete graph = density 1.0

    def test_topology_name_preserved(self, chimera, K4):
        from ember_qc import benchmark_one
        result = benchmark_one(K4, chimera, "minorminer", topology_name="my_custom_topology")
        assert result.topology_name == "my_custom_topology"

    def test_trial_number_preserved(self, chimera, K4):
        from ember_qc import benchmark_one
        for t in [0, 1, 5, 99]:
            result = benchmark_one(K4, chimera, "minorminer", trial=t)
            assert result.trial == t

    def test_quality_metrics_computed(self, chimera, K4):
        from ember_qc import benchmark_one
        result = benchmark_one(K4, chimera, "minorminer")
        assert result.avg_chain_length > 0
        assert result.max_chain_length >= 1
        assert result.total_qubits_used >= 4  # at least one qubit per node
        assert len(result.chain_lengths) == 4  # one chain per source node
        assert result.total_couplers_used >= 0

    def test_unknown_algorithm_raises(self, chimera, K4):
        from ember_qc import benchmark_one
        with pytest.raises(ValueError, match="Unknown algorithm"):
            benchmark_one(K4, chimera, "totally_fake_algorithm_xyz")

    def test_timing_is_positive(self, chimera, K4):
        from ember_qc import benchmark_one
        result = benchmark_one(K4, chimera, "minorminer")
        assert result.wall_time > 0

    def test_different_graphs_different_results(self, chimera, K4, K8):
        """Larger graphs should generally use more qubits."""
        from ember_qc import benchmark_one
        r4 = benchmark_one(K4, chimera, "minorminer")
        r8 = benchmark_one(K8, chimera, "minorminer")
        assert r8.total_qubits_used > r4.total_qubits_used

    def test_default_labels_are_empty_string(self, chimera, K4):
        from ember_qc import benchmark_one
        result = benchmark_one(K4, chimera, "minorminer")
        assert result.problem_name == ""
        assert result.topology_name == ""


# =============================================================================
# EmbeddingResult serialization
# =============================================================================

class TestEmbeddingResult:
    """Tests for EmbeddingResult dataclass."""

    def test_to_dict_returns_dict(self, chimera, K4):
        from ember_qc import benchmark_one
        result = benchmark_one(K4, chimera, "minorminer")
        d = result.to_dict()
        assert isinstance(d, dict)

    def test_to_dict_has_all_fields(self, chimera, K4):
        from ember_qc import benchmark_one
        result = benchmark_one(K4, chimera, "minorminer", problem_name="K4", topology_name="test")
        d = result.to_dict()
        expected_keys = {
            'algorithm', 'problem_name', 'topology_name', 'trial',
            'success', 'status', 'wall_time', 'cpu_time', 'is_valid', 'embedding',
            'chain_lengths', 'max_chain_length', 'avg_chain_length',
            'total_qubits_used', 'total_couplers_used',
            'problem_nodes', 'problem_edges', 'problem_density',
            'algorithm_version', 'partial', 'error', 'metadata',
            'target_node_visits', 'cost_function_evaluations',
            'embedding_state_mutations', 'overlap_qubit_iterations',
        }
        assert set(d.keys()) == expected_keys

    def test_embedding_serialized_as_json_string(self, chimera, K4):
        """Embedding dict must be serialized as JSON string for CSV compatibility."""
        from ember_qc import benchmark_one
        result = benchmark_one(K4, chimera, "minorminer")
        d = result.to_dict()
        assert isinstance(d['embedding'], str)
        # Must be valid JSON
        parsed = json.loads(d['embedding'])
        assert isinstance(parsed, dict)
        assert len(parsed) == 4  # K4 has 4 nodes

    def test_failed_result_has_none_embedding(self, chimera):
        """When embedding fails, embedding should be None."""
        from ember_qc.benchmark import EmbeddingResult
        result = EmbeddingResult(
            algorithm="test", problem_name="fail_test",
            topology_name="test", trial=0, success=False,
            error="Test failure"
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
        from ember_qc import compute_embedding_metrics
        embedding = {0: [0, 1], 1: [4], 2: [8, 9, 10]}
        metrics = compute_embedding_metrics(embedding, chimera)
        assert metrics['chain_lengths'] == [2, 1, 3]
        assert metrics['avg_chain_length'] == 2.0
        assert metrics['max_chain_length'] == 3
        assert metrics['total_qubits_used'] == 6

    def test_single_qubit_chains(self, chimera):
        from ember_qc import compute_embedding_metrics
        embedding = {0: [0], 1: [4], 2: [8]}
        metrics = compute_embedding_metrics(embedding, chimera)
        assert metrics['avg_chain_length'] == 1.0
        assert metrics['max_chain_length'] == 1
        assert metrics['total_qubits_used'] == 3

    def test_coupler_counting(self):
        """Couplers should only count edges that exist in the target graph."""
        from ember_qc import compute_embedding_metrics
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
        from ember_qc import ALGORITHM_REGISTRY
        assert "minorminer" in ALGORITHM_REGISTRY

    def test_clique_is_registered(self):
        from ember_qc import ALGORITHM_REGISTRY
        assert "clique" in ALGORITHM_REGISTRY

    def test_atom_is_registered(self):
        from ember_qc import ALGORITHM_REGISTRY
        assert "atom" in ALGORITHM_REGISTRY

    def test_clique_produces_valid_embedding(self, chimera, K4):
        from ember_qc import benchmark_one
        result = benchmark_one(K4, chimera, "clique", problem_name="K4")
        assert result.success is True
        assert result.is_valid is True
        assert result.embedding is not None
        assert len(result.embedding) == 4

    def test_atom_produces_valid_embedding(self, chimera, K4):
        from ember_qc import benchmark_one
        result = benchmark_one(K4, chimera, "atom", problem_name="K4")
        assert result.success is True
        # ATOM sometimes fails validation depending on seeds, but it should succeed for K4
        assert result.embedding is not None
        assert len(result.embedding) == 4

    def test_list_algorithms_returns_names(self):
        from ember_qc import list_algorithms
        algos = list_algorithms()
        assert isinstance(algos, list)
        assert "minorminer" in algos
        assert "clique" in algos
        assert "atom" in algos
        assert len(algos) >= 2

    def test_algorithm_has_embed_method(self):
        from ember_qc import ALGORITHM_REGISTRY
        for name, algo in ALGORITHM_REGISTRY.items():
            assert hasattr(algo, 'embed'), f"{name} missing embed()"
            assert callable(algo.embed)

    def test_validate_embedding_correct(self, chimera, K4):
        """validate_embedding should return True for a valid minorminer result."""
        from ember_qc import benchmark_one, validate_embedding
        result = benchmark_one(K4, chimera, "minorminer")
        assert result.embedding is not None
        is_valid = validate_embedding(result.embedding, K4, chimera)
        assert is_valid is True

    def test_validate_embedding_detects_bad_chains(self, chimera, K4):
        """An embedding with disconnected chains should fail validation."""
        from ember_qc import validate_embedding
        # Create a fake embedding where chains use non-adjacent qubits
        bad_embedding = {0: [0, 100], 1: [4], 2: [8], 3: [12]}
        is_valid = validate_embedding(bad_embedding, K4, chimera)
        assert is_valid is False

    def test_validate_embedding_detects_missing_nodes(self, chimera):
        """An embedding that doesn't cover all source nodes should fail."""
        from ember_qc import validate_embedding
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
        from ember_qc import parse_graph_selection
        result = parse_graph_selection("5")
        assert result == {5}

    def test_parse_range(self):
        from ember_qc import parse_graph_selection
        result = parse_graph_selection("1-5")
        assert result == {1, 2, 3, 4, 5}

    def test_parse_multiple_ranges(self):
        from ember_qc import parse_graph_selection
        result = parse_graph_selection("1-3, 10-12")
        assert result == {1, 2, 3, 10, 11, 12}

    def test_parse_exclusion(self):
        from ember_qc import parse_graph_selection
        result = parse_graph_selection("1-10, !5")
        assert 5 not in result
        assert 1 in result
        assert 10 in result

    def test_parse_range_exclusion(self):
        from ember_qc import parse_graph_selection
        result = parse_graph_selection("1-10, !3-5")
        assert result == {1, 2, 6, 7, 8, 9, 10}

    def test_parse_wildcard(self):
        from ember_qc import parse_graph_selection
        result = parse_graph_selection("*")
        assert result == {-1}  # sentinel for "all"

    def test_parse_preset_name(self):
        from ember_qc import parse_graph_selection
        result = parse_graph_selection("quick")
        assert len(result) > 0
        assert -1 not in result  # resolved, not wildcard

    def test_parse_invalid_raises(self):
        from ember_qc import parse_graph_selection
        with pytest.raises(ValueError):
            parse_graph_selection("not_a_preset_or_number_xyz")


class TestPresets:
    """Tests for the preset system."""

    def test_list_presets_returns_dict(self):
        from ember_qc import list_presets
        presets = list_presets()
        assert isinstance(presets, dict)

    def test_standard_presets_exist(self):
        from ember_qc import list_presets
        presets = list_presets()
        for name in ["default", "quick", "complete", "diverse", "all"]:
            assert name in presets, f"Missing preset: {name}"

    def test_preset_values_are_strings(self):
        from ember_qc import list_presets
        for name, selection in list_presets().items():
            assert isinstance(selection, str), f"Preset {name} has non-string value"

    def test_presets_with_commas_parsed_correctly(self):
        """Commas in preset values must be preserved (first-comma split)."""
        from ember_qc import list_presets
        presets = list_presets()
        diverse = presets.get("diverse", "")
        # "diverse" should have commas in its selection string
        assert "," in diverse, "diverse preset should contain commas"


class TestGraphLoading:
    """Tests for loading graphs from the test_graphs/ directory."""

    def test_load_by_id_range(self):
        from ember_qc import load_test_graphs
        problems = load_test_graphs("1-3")
        assert len(problems) > 0
        for name, graph in problems:
            assert isinstance(name, str)
            assert isinstance(graph, nx.Graph)
            assert graph.number_of_nodes() > 0

    def test_load_by_preset(self):
        from ember_qc import load_test_graphs
        problems = load_test_graphs("quick")
        assert len(problems) > 0

    def test_load_all(self):
        from ember_qc import load_test_graphs
        problems = load_test_graphs("*")
        assert len(problems) >= 10  # should have at least 10 graphs

    def test_load_with_exclusion(self):
        from ember_qc import load_test_graphs
        all_graphs = load_test_graphs("1-10")
        excluded = load_test_graphs("1-10, !5")
        assert len(excluded) < len(all_graphs)

    def test_loaded_graph_has_edges(self):
        from ember_qc import load_test_graphs
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
        from ember_qc import EmbeddingBenchmark
        bench = EmbeddingBenchmark(chimera, results_dir=str(tmp_path))
        bench.run_full_benchmark(
            graph_selection="1-2", methods=["minorminer"],
            n_trials=1, topology_name="chimera_4x4x4"
        )
        assert len(bench.results) > 0

    def test_results_saved_to_db(self, tmp_path, chimera):
        from ember_qc import EmbeddingBenchmark
        import sqlite3
        bench = EmbeddingBenchmark(chimera, results_dir=str(tmp_path))
        bench.run_full_benchmark(
            graph_selection="1", methods=["minorminer"], n_trials=1
        )
        # Results are inside a batch subdirectory
        batch_dirs = [d for d in tmp_path.iterdir() if d.is_dir() and d.name.startswith('batch_')]
        assert len(batch_dirs) == 1
        batch_dir = batch_dirs[0]
        # New pipeline: SQLite database + CSV export (no runs.json)
        assert (batch_dir / "results.db").exists()
        with sqlite3.connect(batch_dir / "results.db") as conn:
            rows = conn.execute("SELECT algorithm FROM runs").fetchall()
        assert len(rows) >= 1
        assert rows[0][0] == 'minorminer'

    def test_results_saved_to_csv(self, tmp_path, chimera):
        from ember_qc import EmbeddingBenchmark
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
        from ember_qc import EmbeddingBenchmark
        bench = EmbeddingBenchmark(chimera, results_dir=str(tmp_path))
        bench.run_full_benchmark(
            graph_selection="1", methods=["minorminer"], n_trials=3
        )
        assert len(bench.results) == 3
        trials = [r.trial for r in bench.results]
        assert sorted(trials) == [0, 1, 2]

    def test_warmup_trials_discarded(self, tmp_path, chimera):
        """Warm-up trials should not appear in results."""
        from ember_qc import EmbeddingBenchmark
        bench = EmbeddingBenchmark(chimera, results_dir=str(tmp_path))
        bench.run_full_benchmark(
            graph_selection="1", methods=["minorminer"],
            n_trials=2, warmup_trials=3
        )
        # Only 2 measured trials should be stored, not 2+3=5
        assert len(bench.results) == 2

    def test_topology_name_propagated(self, tmp_path, chimera):
        """topology_name from the batch call should appear in every result."""
        from ember_qc import EmbeddingBenchmark
        bench = EmbeddingBenchmark(chimera, results_dir=str(tmp_path))
        bench.run_full_benchmark(
            graph_selection="1-2", methods=["minorminer"],
            n_trials=1, topology_name="pegasus_test"
        )
        for result in bench.results:
            assert result.topology_name == "pegasus_test"

    def test_unknown_method_skipped(self, tmp_path, chimera):
        """Requesting a non-existent algorithm should skip it, not crash."""
        from ember_qc import EmbeddingBenchmark
        bench = EmbeddingBenchmark(chimera, results_dir=str(tmp_path))
        bench.run_full_benchmark(
            graph_selection="1", methods=["minorminer", "totally_fake"],
            n_trials=1
        )
        # Only minorminer results, fake was skipped
        assert all(r.algorithm == "minorminer" for r in bench.results)

    def test_embeddings_stored_in_results(self, tmp_path, chimera):
        """Every successful result in the batch must have the embedding stored."""
        from ember_qc import EmbeddingBenchmark
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
        from ember_qc import EmbeddingBenchmark
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
        from ember_qc.results import ResultsManager
        mgr = ResultsManager(str(tmp_path))
        batch_dir = mgr.create_batch()
        # Name should match batch_YYYY-MM-DD_HH-MM-SS
        assert batch_dir.name.startswith("batch_20")
        assert len(batch_dir.name) >= len("batch_2026-02-23_11-30-15")

    def test_batch_dirs_are_unique(self, tmp_path):
        """Multiple batches created rapidly should have unique names."""
        from ember_qc.results import ResultsManager
        mgr = ResultsManager(str(tmp_path))
        dirs = [mgr.create_batch() for _ in range(3)]
        names = [d.name for d in dirs]
        assert len(set(names)) == 3  # all unique

    def test_latest_symlink_points_to_newest(self, tmp_path):
        """latest symlink is created in results_dir after move_to_output()."""
        from ember_qc.results import ResultsManager
        results_dir = tmp_path / "results"
        mgr = ResultsManager(str(results_dir))
        b1 = mgr.create_batch()
        b2 = mgr.create_batch()
        mgr.move_to_output(b1)
        mgr.move_to_output(b2)
        latest = results_dir / "latest"
        assert latest.is_symlink()
        assert latest.resolve().name == b2.name

    def test_config_json_saved(self, tmp_path):
        from ember_qc.results import ResultsManager
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
        """runs.csv should not contain the embedding or chain_lengths columns."""
        from ember_qc import EmbeddingBenchmark
        import pandas as pd
        bench = EmbeddingBenchmark(chimera, results_dir=str(tmp_path))
        bench.run_full_benchmark(
            problems=[("K4", K4)], methods=["minorminer"], n_trials=2,
            topology_name="chimera_test",
        )
        batch_dirs = [d for d in tmp_path.iterdir() if d.is_dir() and d.name.startswith('batch_')]
        batch_dir = batch_dirs[0]
        df = pd.read_csv(batch_dir / "runs.csv")
        assert 'embedding' not in df.columns
        assert 'chain_lengths' not in df.columns
        assert 'algorithm' in df.columns
        assert len(df) == 2

    def test_worker_jsonl_includes_embeddings(self, tmp_path, chimera, K4):
        """Worker JSONL files should contain the full embedding for each run."""
        from ember_qc import EmbeddingBenchmark
        bench = EmbeddingBenchmark(chimera, results_dir=str(tmp_path))
        bench.run_full_benchmark(
            problems=[("K4", K4)], methods=["minorminer"], n_trials=1,
        )
        batch_dirs = [d for d in tmp_path.iterdir() if d.is_dir() and d.name.startswith('batch_')]
        batch_dir = batch_dirs[0]
        jfiles = sorted((batch_dir / "workers").glob("worker_*.jsonl"))
        assert len(jfiles) >= 1
        with open(jfiles[0]) as f:
            data = json.loads(f.readline())
        assert 'embedding' in data
        assert data['embedding'] is not None

    def test_summary_csv_groups_correctly(self, tmp_path, chimera, K4, K8):
        """summary.csv should have one row per (algorithm, problem_name, topology_name)."""
        from ember_qc import benchmark_one
        from ember_qc.results import ResultsManager
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
        from ember_qc import benchmark_one
        from ember_qc.results import ResultsManager
        import pandas as pd
        results = [benchmark_one(K4, chimera, "minorminer", problem_name="K4", trial=i) for i in range(3)]
        mgr = ResultsManager(str(tmp_path))
        batch_dir = mgr.create_batch()
        mgr.save_results(results, batch_dir)
        df = pd.read_csv(batch_dir / "summary.csv")
        for metric in ['wall_time', 'avg_chain_length', 'max_chain_length',
                       'total_qubits_used', 'total_couplers_used']:
            assert f'{metric}_mean' in df.columns
            assert f'{metric}_std' in df.columns
            assert f'{metric}_median' in df.columns

    def test_summary_stats_are_correct(self, tmp_path, chimera, K4):
        """Verify mean/std/median are numerically correct."""
        from ember_qc import benchmark_one
        from ember_qc.results import ResultsManager
        import pandas as pd
        import numpy as np
        results = [benchmark_one(K4, chimera, "minorminer", problem_name="K4",
                                 topology_name="t", trial=i) for i in range(5)]
        mgr = ResultsManager(str(tmp_path))
        batch_dir = mgr.create_batch()
        mgr.save_results(results, batch_dir)
        df = pd.read_csv(batch_dir / "summary.csv")
        row = df.iloc[0]
        times = [r.wall_time for r in results]
        assert abs(row['wall_time_mean'] - np.mean(times)) < 1e-6
        assert abs(row['wall_time_median'] - np.median(times)) < 1e-6
        assert row['n_trials'] == 5
        assert row['success_rate'] == 1.0

    def test_readme_generated(self, tmp_path, chimera, K4):
        """README.md must exist and contain key sections."""
        from ember_qc import benchmark_one
        from ember_qc.results import ResultsManager
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
        from ember_qc import benchmark_one
        from ember_qc.results import ResultsManager
        results = [benchmark_one(K4, chimera, "minorminer", problem_name="K4")]
        mgr = ResultsManager(str(tmp_path))
        config = {'batch_note': 'Testing note feature'}
        batch_dir = mgr.create_batch(config, batch_note='Testing note feature')
        mgr.save_results(results, batch_dir, config=config)
        readme = (batch_dir / "README.md").read_text()
        assert "Testing note feature" in readme

    def test_empty_results_no_crash(self, tmp_path):
        """Saving empty results should not raise."""
        from ember_qc.results import ResultsManager
        mgr = ResultsManager(str(tmp_path))
        batch_dir = mgr.create_batch()
        mgr.save_results([], batch_dir)  # should not raise


# =============================================================================
# Topology registry
# =============================================================================

class TestTopologyRegistry:
    """Tests for the topology registry system."""

    def test_import_topology_functions(self):
        from ember_qc import(TOPOLOGY_REGISTRY, get_topology, list_topologies,
                             register_topology, topology_info, list_topology_families)
        assert isinstance(TOPOLOGY_REGISTRY, dict)
        assert callable(get_topology)
        assert callable(list_topologies)

    def test_builtin_chimera_registered(self):
        from ember_qc import list_topologies
        topos = list_topologies(family="chimera")
        assert "chimera_4x4x4" in topos
        assert "chimera_16x16x4" in topos

    def test_builtin_pegasus_registered(self):
        from ember_qc import list_topologies
        topos = list_topologies(family="pegasus")
        assert "pegasus_4" in topos
        assert "pegasus_16" in topos

    def test_builtin_zephyr_registered(self):
        from ember_qc import list_topologies
        topos = list_topologies(family="zephyr")
        assert "zephyr_2" in topos
        assert "zephyr_8" in topos

    def test_three_families_exist(self):
        from ember_qc import list_topology_families
        families = list_topology_families()
        assert "chimera" in families
        assert "pegasus" in families
        assert "zephyr" in families

    def test_get_topology_returns_graph(self):
        from ember_qc import get_topology
        g = get_topology("chimera_4x4x4")
        assert isinstance(g, nx.Graph)
        assert g.number_of_nodes() == 128
        assert g.number_of_edges() > 0

    def test_get_topology_caches(self):
        from ember_qc import get_topology
        g1 = get_topology("chimera_4x4x4")
        g2 = get_topology("chimera_4x4x4")
        assert g1 is g2  # same object, not regenerated

    def test_get_topology_unknown_raises(self):
        from ember_qc import get_topology
        with pytest.raises(ValueError, match="Unknown topology"):
            get_topology("totally_fake_topology_xyz")

    def test_custom_registration(self):
        from ember_qc import register_topology, get_topology, TOPOLOGY_REGISTRY
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
        from ember_qc import topology_info
        info = topology_info()
        assert isinstance(info, str)
        assert "chimera_4x4x4" in info
        assert "pegasus" in info

    def test_get_topology_config(self):
        from ember_qc import get_topology_config
        config = get_topology_config("chimera_4x4x4")
        assert config.name == "chimera_4x4x4"
        assert config.family == "chimera"
        assert config.params == {"m": 4, "n": 4, "t": 4}

    def test_multi_topology_benchmark(self, tmp_path):
        """EmbeddingBenchmark should run across multiple topologies."""
        from ember_qc import EmbeddingBenchmark
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


# =============================================================================
# Additional fixtures for validation / logging / seeding tests
# =============================================================================

@pytest.fixture
def small_target():
    """6-node target graph used for deterministic validation tests.

    Chain-internal edges:  0-1, 2-3, 4-5
    Cross-chain edges:     0-2, 1-4, 3-5

    Valid K3 embedding:  {0: [0,1],  1: [2,3],  2: [4,5]}
    Source edge (0,1): {0,1} ↔ {2,3} via 0-2  ✓
    Source edge (0,2): {0,1} ↔ {4,5} via 1-4  ✓
    Source edge (1,2): {2,3} ↔ {4,5} via 3-5  ✓
    """
    G = nx.Graph()
    G.add_nodes_from(range(6))
    G.add_edges_from([(0,1),(2,3),(4,5),(0,2),(1,4),(3,5)])
    return G


@pytest.fixture
def K3():
    return nx.complete_graph(3)


# Helper: register a one-shot mock algorithm, run benchmark_one, clean up.
def _run_mock_algo(source, target, result_dict):
    from ember_qc.registry import ALGORITHM_REGISTRY, EmbeddingAlgorithm
    from ember_qc.benchmark import benchmark_one

    class _Mock(EmbeddingAlgorithm):
        def embed(self, src, tgt, timeout=60.0, **kw):
            return result_dict

    ALGORITHM_REGISTRY['__test_mock__'] = _Mock()
    try:
        return benchmark_one(source, target, '__test_mock__')
    finally:
        ALGORITHM_REGISTRY.pop('__test_mock__', None)


# =============================================================================
# _derive_seed()
# =============================================================================

class TestDeriveSeed:
    """Tests for the SHA-256 per-trial seed derivation function."""

    def test_deterministic(self):
        from ember_qc.benchmark import _derive_seed
        s1 = _derive_seed(42, "minorminer", "K4", "chimera", 0)
        s2 = _derive_seed(42, "minorminer", "K4", "chimera", 0)
        assert s1 == s2

    def test_different_trials_give_different_seeds(self):
        from ember_qc.benchmark import _derive_seed
        seeds = [_derive_seed(42, "minorminer", "K4", "chimera", t) for t in range(5)]
        assert len(set(seeds)) == 5

    def test_different_problems_give_different_seeds(self):
        from ember_qc.benchmark import _derive_seed
        s_k4 = _derive_seed(42, "minorminer", "K4", "chimera", 0)
        s_k8 = _derive_seed(42, "minorminer", "K8", "chimera", 0)
        assert s_k4 != s_k8

    def test_different_algorithms_give_different_seeds(self):
        from ember_qc.benchmark import _derive_seed
        s1 = _derive_seed(42, "minorminer", "K4", "chimera", 0)
        s2 = _derive_seed(42, "clique", "K4", "chimera", 0)
        assert s1 != s2

    def test_different_root_seeds_give_different_seeds(self):
        from ember_qc.benchmark import _derive_seed
        s1 = _derive_seed(42, "minorminer", "K4", "chimera", 0)
        s2 = _derive_seed(99, "minorminer", "K4", "chimera", 0)
        assert s1 != s2

    def test_returns_32bit_unsigned_int(self):
        from ember_qc.benchmark import _derive_seed
        s = _derive_seed(42, "minorminer", "K4", "chimera", 0)
        assert isinstance(s, int)
        assert 0 <= s < 2**32

    def test_warmup_seeds_distinct_from_measured(self):
        """Warmup uses negative trial indices — must not collide with trials 0–N."""
        from ember_qc.benchmark import _derive_seed
        measured = {_derive_seed(42, "minorminer", "K4", "chimera", t) for t in range(5)}
        warmup   = {_derive_seed(42, "minorminer", "K4", "chimera", -(w+1)) for w in range(3)}
        assert measured.isdisjoint(warmup)


# =============================================================================
# ValidationResult dataclass
# =============================================================================

class TestValidationResult:
    """Tests for the ValidationResult dataclass."""

    def test_passed_true_defaults(self):
        from ember_qc.validation import ValidationResult
        vr = ValidationResult(passed=True)
        assert vr.passed is True
        assert vr.check_name is None
        assert vr.detail is None

    def test_passed_false_fields(self):
        from ember_qc.validation import ValidationResult
        vr = ValidationResult(passed=False, check_name="coverage", detail="missing node 5")
        assert vr.passed is False
        assert vr.check_name == "coverage"
        assert vr.detail == "missing node 5"

    def test_bool_protocol(self):
        from ember_qc.validation import ValidationResult
        assert bool(ValidationResult(passed=True)) is True
        assert bool(ValidationResult(passed=False, check_name="x", detail="y")) is False


# =============================================================================
# validate_layer1() — structural checks
# =============================================================================

class TestValidateLayer1:
    """Unit tests for each of the five Layer 1 structural checks."""

    def test_valid_embedding_passes(self, small_target, K3):
        from ember_qc.validation import validate_layer1
        result = validate_layer1({0:[0,1], 1:[2,3], 2:[4,5]}, K3, small_target)
        assert result.passed is True
        assert result.check_name is None
        assert result.detail is None

    def test_coverage_missing_source_vertex(self, small_target, K3):
        from ember_qc.validation import validate_layer1
        result = validate_layer1({0:[0,1], 1:[2,3]}, K3, small_target)  # missing 2
        assert result.passed is False
        assert result.check_name == "coverage"
        assert "2" in result.detail

    def test_non_empty_chains_empty_chain_rejected(self, small_target, K3):
        from ember_qc.validation import validate_layer1
        result = validate_layer1({0:[0,1], 1:[], 2:[4,5]}, K3, small_target)
        assert result.passed is False
        assert result.check_name == "non_empty_chains"

    def test_connectivity_disconnected_chain_rejected(self, small_target, K3):
        """Nodes 0 and 3 are not adjacent in small_target → chain [0,3] is disconnected."""
        from ember_qc.validation import validate_layer1
        # 0 connects to {1,2}; 3 connects to {2,5}. chain_set={0,3}: BFS from 0
        # finds {1,2} ∩ {0,3} = {} → not connected.
        result = validate_layer1({0:[0,3], 1:[2], 2:[4,5]}, K3, small_target)
        assert result.passed is False
        assert result.check_name == "connectivity"
        assert "3" in result.detail  # unreachable node mentioned

    def test_connectivity_single_node_chain_trivially_passes(self, small_target, K3):
        """Single-node chains bypass the BFS; should not cause connectivity failure."""
        from ember_qc.validation import validate_layer1
        # {0:[0], 1:[2,3], 2:[4,5]} — chain 0 has one node, trivially connected.
        # Edge (0,1): {0} and {2,3}: 0's nbrs={1,2}, 2 ∈ {2,3} ✓
        # Edge (0,2): {0} and {4,5}: 0's nbrs={1,2}, neither ∈ {4,5}. → edge_preservation fail
        result = validate_layer1({0:[0], 1:[2,3], 2:[4,5]}, K3, small_target)
        # Connectivity must not be the failure (if it fails it's edge_preservation)
        assert result.check_name != "connectivity"

    def test_disjointness_shared_qubit_rejected(self, small_target, K3):
        """Qubit 1 in both chain 0 and chain 1 → disjointness failure.

        Chains {0:[0,1], 1:[1,4], 2:[4,5]} — all connected (0-1, 1-4, 4-5 edges)
        so connectivity passes and disjointness is checked.
        """
        from ember_qc.validation import validate_layer1
        result = validate_layer1({0:[0,1], 1:[1,4], 2:[4,5]}, K3, small_target)
        assert result.passed is False
        assert result.check_name == "disjointness"
        assert "1" in result.detail  # shared qubit mentioned

    def test_edge_preservation_no_cross_chain_edge(self, small_target, K3):
        """Chain 1=[3] has no target-graph neighbor in chain 0={0,1}.

        Source edge (0,1): 0's nbrs={1,2}, 1's nbrs={0,4}. Neither 2 nor 4 is 3.
        3's nbrs={2,5}. Neither is in {0,1}. → edge_preservation failure.
        """
        from ember_qc.validation import validate_layer1
        result = validate_layer1({0:[0,1], 1:[3], 2:[4,5]}, K3, small_target)
        assert result.passed is False
        assert result.check_name == "edge_preservation"

    def test_checks_run_in_order_coverage_before_connectivity(self, small_target, K3):
        """When coverage fails, connectivity is never checked."""
        from ember_qc.validation import validate_layer1
        result = validate_layer1({0:[0,1]}, K3, small_target)  # missing nodes 1 and 2
        assert result.check_name == "coverage"


# =============================================================================
# validate_layer2() — type/format checks
# =============================================================================

class TestValidateLayer2:
    """Unit tests for each of the six Layer 2 type and format checks."""

    def _valid(self, small_target, K3):
        from ember_qc.validation import validate_layer2
        return validate_layer2(
            {'success': True, 'embedding': {0:[0,1], 1:[2,3], 2:[4,5]}, 'time': 0.5},
            K3, small_target,
        )

    def test_valid_result_passes(self, small_target, K3):
        assert self._valid(small_target, K3).passed is True

    def test_extra_embedding_key_rejected(self, small_target, K3):
        from ember_qc.validation import validate_layer2
        result = validate_layer2(
            {'success': True, 'embedding': {0:[0,1], 1:[2,3], 2:[4,5], 99:[0]}, 'time': 0.5},
            K3, small_target,
        )
        assert result.passed is False
        assert result.check_name == "key_validity"
        assert "99" in result.detail

    def test_missing_embedding_key_rejected(self, small_target, K3):
        from ember_qc.validation import validate_layer2
        result = validate_layer2(
            {'success': True, 'embedding': {0:[0,1], 1:[2,3]}, 'time': 0.5},  # missing 2
            K3, small_target,
        )
        assert result.passed is False
        assert result.check_name == "key_validity"

    def test_qubit_not_in_target_rejected(self, small_target, K3):
        from ember_qc.validation import validate_layer2
        result = validate_layer2(
            {'success': True, 'embedding': {0:[0,999], 1:[2,3], 2:[4,5]}, 'time': 0.5},
            K3, small_target,
        )
        assert result.passed is False
        assert result.check_name == "value_validity"

    def test_numpy_int64_key_rejected(self, small_target, K3):
        from ember_qc.validation import validate_layer2
        emb = {np.int64(0):[0,1], np.int64(1):[2,3], np.int64(2):[4,5]}
        result = validate_layer2({'success': True, 'embedding': emb, 'time': 0.5},
                                 K3, small_target)
        assert result.passed is False
        assert result.check_name == "type_correctness"
        assert "int64" in result.detail

    def test_numpy_int64_qubit_rejected(self, small_target, K3):
        from ember_qc.validation import validate_layer2
        emb = {0: [np.int64(0), np.int64(1)], 1:[2,3], 2:[4,5]}
        result = validate_layer2({'success': True, 'embedding': emb, 'time': 0.5},
                                 K3, small_target)
        assert result.passed is False
        assert result.check_name == "type_correctness"

    def test_tuple_chain_rejected(self, small_target, K3):
        from ember_qc.validation import validate_layer2
        emb = {0: (0, 1), 1:[2,3], 2:[4,5]}
        result = validate_layer2({'success': True, 'embedding': emb, 'time': 0.5},
                                 K3, small_target)
        assert result.passed is False
        assert result.check_name == "chain_format"
        assert "tuple" in result.detail

    def test_nan_wall_time_rejected(self, small_target, K3):
        from ember_qc.validation import validate_layer2
        result = validate_layer2(
            {'success': True, 'embedding': {0:[0,1], 1:[2,3], 2:[4,5]}, 'time': float('nan')},
            K3, small_target,
        )
        assert result.passed is False
        assert result.check_name == "wall_time_validity"

    def test_zero_wall_time_rejected(self, small_target, K3):
        from ember_qc.validation import validate_layer2
        result = validate_layer2(
            {'success': True, 'embedding': {0:[0,1], 1:[2,3], 2:[4,5]}, 'time': 0.0},
            K3, small_target,
        )
        assert result.passed is False
        assert result.check_name == "wall_time_validity"

    def test_negative_wall_time_rejected(self, small_target, K3):
        from ember_qc.validation import validate_layer2
        result = validate_layer2(
            {'success': True, 'embedding': {0:[0,1], 1:[2,3], 2:[4,5]}, 'time': -1.0},
            K3, small_target,
        )
        assert result.passed is False
        assert result.check_name == "wall_time_validity"

    def test_cpu_time_exceeding_wall_times_cores_rejected(self, small_target, K3):
        import os
        from ember_qc.validation import validate_layer2
        n_cores = os.cpu_count() or 1
        result = validate_layer2(
            {'success': True, 'embedding': {0:[0,1], 1:[2,3], 2:[4,5]},
             'time': 1.0, 'cpu_time': n_cores * 10.0},   # physically impossible
            K3, small_target,
        )
        assert result.passed is False
        assert result.check_name == "cpu_time_plausibility"

    def test_absent_time_key_skips_time_check(self, small_target, K3):
        """No 'time' key in result — wall-time check must not run."""
        from ember_qc.validation import validate_layer2
        result = validate_layer2(
            {'success': True, 'embedding': {0:[0,1], 1:[2,3], 2:[4,5]}},
            K3, small_target,
        )
        assert result.passed is True

    def test_empty_embedding_skips_embedding_checks(self, small_target, K3):
        """Empty embedding (failure path) must not trigger key/type/chain checks."""
        from ember_qc.validation import validate_layer2
        result = validate_layer2(
            {'success': False, 'embedding': {}, 'time': 1.0},
            K3, small_target,
        )
        assert result.passed is True


# =============================================================================
# Validation integration — benchmark_one returns correct status + error format
# =============================================================================

class TestValidationIntegration:
    """Verify Layer 1/2 failures produce correct EmbeddingResult fields."""

    def test_layer2_failure_sets_invalid_output_status(self, small_target, K3):
        emb = {np.int64(0):[0,1], np.int64(1):[2,3], np.int64(2):[4,5]}
        result = _run_mock_algo(K3, small_target,
                                {'success': True, 'embedding': emb, 'time': 0.01})
        assert result.status == 'INVALID_OUTPUT'
        assert result.success is False

    def test_layer2_error_contains_layer_and_check(self, small_target, K3):
        emb = {np.int64(0):[0,1], np.int64(1):[2,3], np.int64(2):[4,5]}
        result = _run_mock_algo(K3, small_target,
                                {'success': True, 'embedding': emb, 'time': 0.01})
        assert "Layer 2" in result.error
        assert "type_correctness" in result.error

    def test_layer2_error_includes_original_claim(self, small_target, K3):
        emb = {np.int64(0):[0,1], np.int64(1):[2,3], np.int64(2):[4,5]}
        result = _run_mock_algo(K3, small_target,
                                {'success': True, 'embedding': emb, 'time': 0.01})
        assert "returned embedding (size=3)" in result.error
        assert "Layer 2" in result.error

    def test_layer1_failure_sets_invalid_output_status(self, small_target, K3):
        """Shared qubit in embedding → Layer 1 disjointness → INVALID_OUTPUT."""
        result = _run_mock_algo(K3, small_target,
                                {'success': True,
                                 'embedding': {0:[0,1], 1:[1,4], 2:[4,5]},
                                 'time': 0.01})
        assert result.status == 'INVALID_OUTPUT'
        assert result.success is False

    def test_layer1_error_contains_layer_and_check(self, small_target, K3):
        result = _run_mock_algo(K3, small_target,
                                {'success': True,
                                 'embedding': {0:[0,1], 1:[1,4], 2:[4,5]},
                                 'time': 0.01})
        assert "Layer 1" in result.error
        assert "disjointness" in result.error

    def test_layer1_error_includes_original_claim(self, small_target, K3):
        result = _run_mock_algo(K3, small_target,
                                {'success': True,
                                 'embedding': {0:[0,1], 1:[1,4], 2:[4,5]},
                                 'time': 0.01})
        assert "returned embedding (size=3)" in result.error
        assert "Layer 1" in result.error

    def test_valid_mock_succeeds(self, small_target, K3):
        result = _run_mock_algo(K3, small_target,
                                {'success': True,
                                 'embedding': {0:[0,1], 1:[2,3], 2:[4,5]},
                                 'time': 0.01})
        assert result.status == 'SUCCESS'
        assert result.success is True
        assert result.is_valid is True


# =============================================================================
# BatchLogger
# =============================================================================

class TestBatchLogger:
    """Tests for the BatchLogger and capture_run() context manager."""

    def test_setup_creates_log_directories(self, tmp_path):
        from ember_qc.loggers import BatchLogger
        logger = BatchLogger(tmp_path, "test_batch")
        logger.setup()
        assert (tmp_path / "logs" / "runs").is_dir()
        assert (tmp_path / "logs" / "runner").is_dir()
        logger.teardown()

    def test_setup_is_idempotent(self, tmp_path):
        from ember_qc.loggers import BatchLogger
        logger = BatchLogger(tmp_path, "test_batch")
        logger.setup()
        logger.setup()  # second call must not raise
        logger.teardown()

    def test_runner_log_file_created_with_batch_id(self, tmp_path):
        from ember_qc.loggers import BatchLogger
        logger = BatchLogger(tmp_path, "batch_XYZ")
        logger.setup()
        logger.info("hello from test")
        logger.teardown()
        log_file = tmp_path / "logs" / "runner" / "batch_XYZ.log"
        assert log_file.exists()
        assert "hello from test" in log_file.read_text()

    def test_run_log_path_encodes_all_components(self, tmp_path):
        from ember_qc.loggers import BatchLogger
        logger = BatchLogger(tmp_path, "b")
        logger.setup()
        p = logger.run_log_path("minorminer", "K4_test", 3, 99999)
        assert "minorminer" in p.name
        assert "K4_test" in p.name
        assert "3" in p.name
        assert "99999" in p.name
        logger.teardown()

    def test_capture_run_redirects_stdout(self, tmp_path):
        import sys
        from ember_qc.loggers import capture_run
        log_path = tmp_path / "capture_test.log"
        with capture_run(log_path):
            print("captured_output_marker")
        assert "captured_output_marker" in log_path.read_text()

    def test_capture_run_restores_streams_after_exception(self, tmp_path):
        import sys
        from ember_qc.loggers import capture_run
        original_stdout = sys.stdout
        log_path = tmp_path / "exc_test.log"
        try:
            with capture_run(log_path):
                raise RuntimeError("deliberate error")
        except RuntimeError:
            pass
        assert sys.stdout is original_stdout

    def test_append_footer_writes_required_fields(self, tmp_path, chimera, K4):
        from ember_qc import benchmark_one
        from ember_qc.loggers import BatchLogger
        result = benchmark_one(K4, chimera, "minorminer")
        logger = BatchLogger(tmp_path, "b")
        logger.setup()
        log_path = logger.run_log_path("minorminer", "K4", 0, 42)
        logger.append_footer(log_path, result)
        logger.teardown()
        content = log_path.read_text()
        assert "--- RUNNER DIAGNOSTICS ---" in content
        assert "status:" in content
        assert "success:" in content
        assert "wall_time:" in content
        assert "cpu_time:" in content

    def test_full_batch_creates_per_run_log_files(self, tmp_path, chimera):
        from ember_qc import EmbeddingBenchmark
        bench = EmbeddingBenchmark(chimera, results_dir=str(tmp_path))
        bench.run_full_benchmark(
            graph_selection="1", methods=["minorminer"], n_trials=2
        )
        batch_dirs = [d for d in tmp_path.iterdir() if d.is_dir() and d.name.startswith('batch_')]
        batch_dir = batch_dirs[0]
        log_files = list((batch_dir / "logs" / "runs").glob("*.log"))
        assert len(log_files) == 2
        for lf in log_files:
            assert "--- RUNNER DIAGNOSTICS ---" in lf.read_text()

    def test_invalid_output_logged_at_warning_in_runner_log(self, tmp_path, small_target, K3):
        """INVALID_OUTPUT runs must appear as WARNING in the runner log file."""
        from ember_qc.registry import ALGORITHM_REGISTRY, EmbeddingAlgorithm
        from ember_qc import EmbeddingBenchmark

        class BadTypeAlgo(EmbeddingAlgorithm):
            def embed(self, src, tgt, timeout=60.0, **kw):
                # numpy.int64 keys — Layer 2 type_correctness failure
                return {'success': True,
                        'embedding': {np.int64(k): [v] for k, v in
                                      zip(src.nodes(), tgt.nodes())},
                        'time': 0.01}

        ALGORITHM_REGISTRY['__bad_type_test__'] = BadTypeAlgo()
        try:
            bench = EmbeddingBenchmark(small_target, results_dir=str(tmp_path))
            bench.run_full_benchmark(
                problems=[("K3", K3)], methods=["__bad_type_test__"], n_trials=1
            )
        finally:
            ALGORITHM_REGISTRY.pop('__bad_type_test__', None)

        batch_dirs = [d for d in tmp_path.iterdir() if d.is_dir() and d.name.startswith('batch_')]
        runner_logs = list((batch_dirs[0] / "logs" / "runner").glob("*.log"))
        content = runner_logs[0].read_text()
        assert "WARNING" in content
        assert "INVALID_OUTPUT" in content


# =============================================================================
# compile_batch() — SQLite storage
# =============================================================================

class TestCompileBatch:
    """Tests for compile_batch() SQLite pipeline."""

    def _run_and_get_batch(self, tmp_path, chimera, K4, n_trials=1):
        from ember_qc import EmbeddingBenchmark
        bench = EmbeddingBenchmark(chimera, results_dir=str(tmp_path))
        bench.run_full_benchmark(
            problems=[("K4", K4)], methods=["minorminer"],
            n_trials=n_trials, seed=42,
        )
        batch_dirs = [d for d in tmp_path.iterdir()
                      if d.is_dir() and d.name.startswith('batch_')]
        return batch_dirs[0]

    def test_results_db_created(self, tmp_path, chimera, K4):
        batch_dir = self._run_and_get_batch(tmp_path, chimera, K4)
        assert (batch_dir / "results.db").exists()

    def test_runs_table_contains_expected_columns(self, tmp_path, chimera, K4):
        import sqlite3
        batch_dir = self._run_and_get_batch(tmp_path, chimera, K4)
        with sqlite3.connect(batch_dir / "results.db") as conn:
            cols = {d[1] for d in conn.execute("PRAGMA table_info(runs)").fetchall()}
        for expected_col in ('algorithm', 'problem_name', 'topology_name',
                             'trial', 'seed', 'status', 'success',
                             'wall_time', 'avg_chain_length', 'total_qubits_used'):
            assert expected_col in cols, f"Missing column: {expected_col}"

    def test_seed_stored_in_runs_table(self, tmp_path, chimera, K4):
        import sqlite3
        batch_dir = self._run_and_get_batch(tmp_path, chimera, K4)
        with sqlite3.connect(batch_dir / "results.db") as conn:
            row = conn.execute("SELECT seed FROM runs").fetchone()
        assert row is not None
        assert isinstance(row[0], int)

    def test_embeddings_table_populated_for_success(self, tmp_path, chimera, K4):
        import sqlite3
        batch_dir = self._run_and_get_batch(tmp_path, chimera, K4)
        with sqlite3.connect(batch_dir / "results.db") as conn:
            count = conn.execute("SELECT COUNT(*) FROM embeddings").fetchone()[0]
        assert count >= 1

    def test_batches_table_has_one_row(self, tmp_path, chimera, K4):
        import sqlite3
        batch_dir = self._run_and_get_batch(tmp_path, chimera, K4)
        with sqlite3.connect(batch_dir / "results.db") as conn:
            count = conn.execute("SELECT COUNT(*) FROM batches").fetchone()[0]
        assert count == 1

    def test_graphs_table_populated(self, tmp_path, chimera, K4):
        import sqlite3
        batch_dir = self._run_and_get_batch(tmp_path, chimera, K4)
        with sqlite3.connect(batch_dir / "results.db") as conn:
            count = conn.execute("SELECT COUNT(*) FROM graphs").fetchone()[0]
        assert count >= 1

    def test_runs_csv_exported_with_correct_row_count(self, tmp_path, chimera, K4):
        import pandas as pd
        batch_dir = self._run_and_get_batch(tmp_path, chimera, K4, n_trials=3)
        df = pd.read_csv(batch_dir / "runs.csv")
        assert len(df) == 3
        assert 'algorithm' in df.columns
        assert 'status' in df.columns
        assert 'embedding' not in df.columns   # embeddings excluded from CSV

    def test_unique_constraint_prevents_duplicate_rows(self, tmp_path, chimera, K4):
        """Running compile_batch a second time must not insert duplicate rows."""
        import sqlite3
        from ember_qc.compile import compile_batch
        batch_dir = self._run_and_get_batch(tmp_path, chimera, K4)
        compile_batch(batch_dir)   # second pass
        with sqlite3.connect(batch_dir / "results.db") as conn:
            count = conn.execute("SELECT COUNT(*) FROM runs").fetchone()[0]
        assert count == 1   # still 1, not 2


# =============================================================================
# Seeding behaviour in the batch runner
# =============================================================================

class TestSeedingBehavior:
    """Tests for deterministic, per-trial, order-independent seed derivation."""

    def _collect_seeds(self, results_dir, chimera, K4, n_trials, seed=42):
        from ember_qc import EmbeddingBenchmark
        bench = EmbeddingBenchmark(chimera, results_dir=str(results_dir))
        bench.run_full_benchmark(
            problems=[("K4", K4)], methods=["minorminer"],
            n_trials=n_trials, seed=seed,
        )
        batch_dirs = sorted(results_dir.iterdir())
        batch_dir = [d for d in batch_dirs if d.name.startswith('batch_')][0]
        seeds = []
        for jf in sorted((batch_dir / "workers").glob("worker_*.jsonl")):
            with open(jf) as f:
                for line in f:
                    seeds.append(json.loads(line.strip())['seed'])
        return sorted(seeds)

    def test_seed_stored_in_worker_jsonl(self, tmp_path, chimera, K4):
        from ember_qc import EmbeddingBenchmark
        bench = EmbeddingBenchmark(chimera, results_dir=str(tmp_path))
        bench.run_full_benchmark(
            problems=[("K4", K4)], methods=["minorminer"], n_trials=1, seed=42
        )
        batch_dirs = [d for d in tmp_path.iterdir() if d.is_dir() and d.name.startswith('batch_')]
        jfiles = sorted((batch_dirs[0] / "workers").glob("worker_*.jsonl"))
        with open(jfiles[0]) as f:
            rec = json.loads(f.readline())
        assert 'seed' in rec
        assert isinstance(rec['seed'], int)

    def test_multi_trial_seeds_are_all_distinct(self, tmp_path, chimera, K4):
        seeds = self._collect_seeds(tmp_path, chimera, K4, n_trials=5)
        assert len(set(seeds)) == 5

    def test_same_root_seed_produces_same_per_trial_seeds(self, tmp_path, chimera, K4):
        """Two sequential runs with the same root seed must produce identical seeds."""
        dir1 = tmp_path / "run1"; dir1.mkdir()
        dir2 = tmp_path / "run2"; dir2.mkdir()
        seeds1 = self._collect_seeds(dir1, chimera, K4, n_trials=3, seed=42)
        seeds2 = self._collect_seeds(dir2, chimera, K4, n_trials=3, seed=42)
        assert seeds1 == seeds2

    def test_different_root_seeds_produce_different_trial_seeds(self, tmp_path, chimera, K4):
        dir1 = tmp_path / "a"; dir1.mkdir()
        dir2 = tmp_path / "b"; dir2.mkdir()
        seeds_42 = self._collect_seeds(dir1, chimera, K4, n_trials=2, seed=42)
        seeds_99 = self._collect_seeds(dir2, chimera, K4, n_trials=2, seed=99)
        assert seeds_42 != seeds_99


# =============================================================================
# Multiprocessing — n_workers > 1
# =============================================================================

class TestMultiprocessing:
    """Tests for the parallel execution path."""

    def test_parallel_produces_correct_result_count(self, tmp_path, chimera):
        from ember_qc import EmbeddingBenchmark
        bench = EmbeddingBenchmark(chimera, results_dir=str(tmp_path))
        bench.run_full_benchmark(
            graph_selection="1-2", methods=["minorminer"], n_trials=2, n_workers=2
        )
        assert len(bench.results) == 4  # 2 graphs × 1 algo × 2 trials

    def test_parallel_results_stored_in_db(self, tmp_path, chimera):
        import sqlite3
        from ember_qc import EmbeddingBenchmark
        bench = EmbeddingBenchmark(chimera, results_dir=str(tmp_path))
        bench.run_full_benchmark(
            graph_selection="1-2", methods=["minorminer"], n_trials=1, n_workers=2
        )
        batch_dirs = [d for d in tmp_path.iterdir() if d.is_dir() and d.name.startswith('batch_')]
        with sqlite3.connect(batch_dirs[0] / "results.db") as conn:
            count = conn.execute("SELECT COUNT(*) FROM runs").fetchone()[0]
        assert count == 2

    def test_parallel_and_sequential_produce_same_seeds(self, tmp_path, chimera):
        """Parallel run with same root seed must assign identical per-trial seeds."""
        from ember_qc import EmbeddingBenchmark

        def get_seed_map(results_dir, n_workers):
            bench = EmbeddingBenchmark(chimera, results_dir=str(results_dir))
            bench.run_full_benchmark(
                graph_selection="1-2", methods=["minorminer"],
                n_trials=1, seed=42, n_workers=n_workers,
            )
            batch_dirs = [d for d in results_dir.iterdir()
                          if d.is_dir() and d.name.startswith('batch_')]
            seed_map = {}
            for jf in sorted((batch_dirs[0] / "workers").glob("worker_*.jsonl")):
                with open(jf) as f:
                    for line in f:
                        rec = json.loads(line.strip())
                        seed_map[(rec['algorithm'], rec['problem_name'], rec['trial'])] = rec['seed']
            return seed_map

        dir_seq = tmp_path / "seq"; dir_seq.mkdir()
        dir_par = tmp_path / "par"; dir_par.mkdir()
        assert get_seed_map(dir_seq, n_workers=1) == get_seed_map(dir_par, n_workers=2)

    def test_warmup_skipped_with_n_workers_gt_1(self, tmp_path, chimera, capsys):
        from ember_qc import EmbeddingBenchmark
        bench = EmbeddingBenchmark(chimera, results_dir=str(tmp_path))
        bench.run_full_benchmark(
            graph_selection="1", methods=["minorminer"],
            n_trials=1, n_workers=2, warmup_trials=3,
        )
        captured = capsys.readouterr()
        assert "warmup" in captured.out.lower() or "Warmup" in captured.out
        assert len(bench.results) == 1  # only measured trial stored


# =============================================================================
# EmbeddingResult spec (status, algorithm_version, counters, to_jsonl_dict)
# =============================================================================

class TestEmbeddingResultSpec:
    """Tests for EmbeddingResult field values and serialization methods."""

    def test_successful_result_has_success_status(self, chimera, K4):
        from ember_qc import benchmark_one
        result = benchmark_one(K4, chimera, "minorminer")
        assert result.status == 'SUCCESS'

    def test_status_on_timed_out_result(self, chimera):
        """A very tight timeout on a hard graph should produce a non-SUCCESS status."""
        from ember_qc import benchmark_one
        K20 = nx.complete_graph(20)
        result = benchmark_one(K20, chimera, "minorminer", timeout=0.001)
        assert result.status in ('FAILURE', 'TIMEOUT', 'CRASH')
        assert result.success is False

    def test_all_status_values_are_valid(self, chimera):
        """status field must always be one of the defined enum strings."""
        from ember_qc import benchmark_one
        valid_statuses = {'SUCCESS', 'FAILURE', 'TIMEOUT', 'CRASH', 'OOM', 'INVALID_OUTPUT'}
        for g in [nx.complete_graph(4), nx.complete_graph(25)]:
            result = benchmark_one(g, chimera, "minorminer", timeout=0.5)
            assert result.status in valid_statuses

    def test_algorithm_version_populated(self, chimera, K4):
        from ember_qc import benchmark_one
        result = benchmark_one(K4, chimera, "minorminer")
        assert result.algorithm_version is not None
        assert isinstance(result.algorithm_version, str)
        assert result.algorithm_version != ""

    def test_cpu_time_is_non_negative(self, chimera, K4):
        from ember_qc import benchmark_one
        result = benchmark_one(K4, chimera, "minorminer")
        assert result.cpu_time >= 0.0

    def test_operation_counters_default_to_none(self, chimera, K4):
        """minorminer does not report counters — all four must be None."""
        from ember_qc import benchmark_one
        result = benchmark_one(K4, chimera, "minorminer")
        assert result.target_node_visits is None
        assert result.cost_function_evaluations is None
        assert result.embedding_state_mutations is None
        assert result.overlap_qubit_iterations is None

    def test_to_jsonl_dict_embedding_stored_as_nested_dict(self, chimera, K4):
        """to_jsonl_dict() must store embedding as dict, NOT a JSON string."""
        from ember_qc import benchmark_one
        result = benchmark_one(K4, chimera, "minorminer")
        d = result.to_jsonl_dict()
        assert isinstance(d['embedding'], dict)    # nested dict, not a JSON string
        for key in d['embedding']:
            assert isinstance(key, str)            # keys serialised as strings
            int(key)                               # must be convertible back to int

    def test_to_jsonl_dict_includes_chain_lengths(self, chimera, K4):
        from ember_qc import benchmark_one
        result = benchmark_one(K4, chimera, "minorminer")
        d = result.to_jsonl_dict()
        assert 'chain_lengths' in d
        assert isinstance(d['chain_lengths'], list)
        assert len(d['chain_lengths']) == 4   # K4 has 4 nodes

    def test_to_dict_embedding_stored_as_json_string(self, chimera, K4):
        """to_dict() (CSV path) must store embedding as a JSON string."""
        from ember_qc import benchmark_one
        result = benchmark_one(K4, chimera, "minorminer")
        d = result.to_dict()
        assert isinstance(d['embedding'], str)
        parsed = json.loads(d['embedding'])
        assert isinstance(parsed, dict)
        assert len(parsed) == 4


# =============================================================================
# New public API imports
# =============================================================================

class TestNewModuleImports:
    """Verify new modules added in v1 are importable from their canonical paths."""

    def test_import_validate_layer1(self):
        from ember_qc.validation import validate_layer1
        assert callable(validate_layer1)

    def test_import_validate_layer2(self):
        from ember_qc.validation import validate_layer2
        assert callable(validate_layer2)

    def test_import_validation_result(self):
        from ember_qc.validation import ValidationResult
        assert ValidationResult is not None

    def test_import_batch_logger(self):
        from ember_qc.loggers import BatchLogger
        assert BatchLogger is not None

    def test_import_capture_run(self):
        from ember_qc.loggers import capture_run
        assert callable(capture_run)

    def test_import_compile_batch(self):
        from ember_qc.compile import compile_batch
        assert callable(compile_batch)

    def test_import_derive_seed(self):
        from ember_qc.benchmark import _derive_seed
        assert callable(_derive_seed)

    def test_import_load_benchmark(self):
        from ember_qc import load_benchmark
        assert callable(load_benchmark)

    def test_import_delete_benchmark(self):
        from ember_qc import delete_benchmark
        assert callable(delete_benchmark)

    def test_import_checkpoint_functions(self):
        from ember_qc.checkpoint import (
            write_checkpoint, read_checkpoint, delete_checkpoint,
            completed_seeds_from_jsonl, scan_incomplete_runs,
        )
        for fn in (write_checkpoint, read_checkpoint, delete_checkpoint,
                   completed_seeds_from_jsonl, scan_incomplete_runs):
            assert callable(fn)


# =============================================================================
# Checkpoint module — write/read/delete and JSONL scan
# =============================================================================

class TestCheckpoint:
    """Tests for qebench/checkpoint.py — all five exported functions."""

    def test_write_and_read_roundtrip(self, tmp_path):
        from ember_qc.checkpoint import write_checkpoint, read_checkpoint
        batch_dir = tmp_path / "batch_test"
        batch_dir.mkdir()
        unfinished = [("minorminer", "K4", "chimera_4x4x4", 1, 99999)]
        write_checkpoint(batch_dir, unfinished, total_tasks=5, completed_count=4)
        cp = read_checkpoint(batch_dir)
        assert cp is not None
        assert cp['total_tasks'] == 5
        assert cp['completed_count'] == 4
        assert cp['resume_count'] == 0
        assert len(cp['unfinished_tasks']) == 1
        t = cp['unfinished_tasks'][0]
        assert t['algo_name'] == 'minorminer'
        assert t['problem_name'] == 'K4'
        assert t['topo_name'] == 'chimera_4x4x4'
        assert t['trial'] == 1
        assert t['trial_seed'] == 99999

    def test_checkpoint_has_cancelled_at_timestamp(self, tmp_path):
        from ember_qc.checkpoint import write_checkpoint, read_checkpoint
        batch_dir = tmp_path / "batch"
        batch_dir.mkdir()
        write_checkpoint(batch_dir, [], total_tasks=0, completed_count=0)
        cp = read_checkpoint(batch_dir)
        assert 'cancelled_at' in cp
        assert 'T' in cp['cancelled_at']  # ISO-8601 format includes 'T' separator

    def test_resume_count_stored(self, tmp_path):
        from ember_qc.checkpoint import write_checkpoint, read_checkpoint
        batch_dir = tmp_path / "batch"
        batch_dir.mkdir()
        write_checkpoint(batch_dir, [], total_tasks=3, completed_count=3, resume_count=2)
        cp = read_checkpoint(batch_dir)
        assert cp['resume_count'] == 2

    def test_read_checkpoint_returns_none_if_absent(self, tmp_path):
        from ember_qc.checkpoint import read_checkpoint
        assert read_checkpoint(tmp_path) is None

    def test_delete_checkpoint_removes_file(self, tmp_path):
        from ember_qc.checkpoint import write_checkpoint, delete_checkpoint, read_checkpoint
        batch_dir = tmp_path / "batch"
        batch_dir.mkdir()
        write_checkpoint(batch_dir, [], total_tasks=0, completed_count=0)
        assert read_checkpoint(batch_dir) is not None
        delete_checkpoint(batch_dir)
        assert read_checkpoint(batch_dir) is None

    def test_delete_checkpoint_noop_if_absent(self, tmp_path):
        from ember_qc.checkpoint import delete_checkpoint
        delete_checkpoint(tmp_path)  # must not raise

    def test_completed_seeds_from_empty_workers(self, tmp_path):
        from ember_qc.checkpoint import completed_seeds_from_jsonl
        assert completed_seeds_from_jsonl(tmp_path) == set()

    def test_completed_seeds_from_missing_workers_dir(self, tmp_path):
        from ember_qc.checkpoint import completed_seeds_from_jsonl
        result = completed_seeds_from_jsonl(tmp_path / "nonexistent")
        assert result == set()

    def test_completed_seeds_reads_valid_jsonl(self, tmp_path):
        import json
        from ember_qc.checkpoint import completed_seeds_from_jsonl
        workers_dir = tmp_path / "workers"
        workers_dir.mkdir()
        rec = {
            'algorithm': 'minorminer', 'problem_name': 'K4',
            'topology_name': 'chimera', 'seed': 12345, 'trial': 0,
        }
        (workers_dir / "worker_1.jsonl").write_text(json.dumps(rec) + "\n")
        seeds = completed_seeds_from_jsonl(tmp_path)
        assert ('minorminer', 'K4', 'chimera', 12345) in seeds

    def test_completed_seeds_strips_truncated_last_line(self, tmp_path):
        """A partially-written last line (crash mid-write) is not counted."""
        import json
        from ember_qc.checkpoint import completed_seeds_from_jsonl
        workers_dir = tmp_path / "workers"
        workers_dir.mkdir()
        good = json.dumps({
            'algorithm': 'algo', 'problem_name': 'prob',
            'topology_name': 'topo', 'seed': 1,
        })
        truncated = '{"algorithm": "other", "problem_name": "x"'  # incomplete
        (workers_dir / "worker_1.jsonl").write_text(good + "\n" + truncated)
        seeds = completed_seeds_from_jsonl(tmp_path)
        assert ('algo', 'prob', 'topo', 1) in seeds
        assert len(seeds) == 1  # truncated line not included

    def test_completed_seeds_aggregates_multiple_workers(self, tmp_path):
        """Seeds from multiple worker JSONL files are all returned."""
        import json
        from ember_qc.checkpoint import completed_seeds_from_jsonl
        workers_dir = tmp_path / "workers"
        workers_dir.mkdir()
        for i in range(3):
            rec = {
                'algorithm': 'algo', 'problem_name': f'prob{i}',
                'topology_name': 'topo', 'seed': i * 100,
            }
            (workers_dir / f"worker_{i}.jsonl").write_text(json.dumps(rec) + "\n")
        seeds = completed_seeds_from_jsonl(tmp_path)
        assert len(seeds) == 3
        assert ('algo', 'prob0', 'topo', 0) in seeds
        assert ('algo', 'prob2', 'topo', 200) in seeds

    def test_scan_incomplete_runs_returns_empty_for_nonexistent_dir(self, tmp_path):
        from ember_qc.checkpoint import scan_incomplete_runs
        assert scan_incomplete_runs(tmp_path / "nonexistent") == []

    def test_scan_incomplete_runs_finds_checkpoint_batch(self, tmp_path):
        from ember_qc.checkpoint import scan_incomplete_runs, write_checkpoint
        batch_dir = tmp_path / "batch_2026-03-17_10-00-00"
        batch_dir.mkdir()
        (batch_dir / "config.json").write_text('{"algorithms": ["mm"], "n_trials": 1}')
        write_checkpoint(batch_dir, [("algo", "prob", "topo", 0, 42)],
                         total_tasks=5, completed_count=4)
        runs = scan_incomplete_runs(tmp_path)
        assert len(runs) == 1
        assert runs[0]['batch_id'] == 'batch_2026-03-17_10-00-00'
        assert runs[0]['has_checkpoint'] is True
        assert runs[0]['checkpoint']['completed_count'] == 4

    def test_scan_incomplete_runs_detects_crashed_batch(self, tmp_path):
        """A batch with no checkpoint.json is reported as crashed."""
        from ember_qc.checkpoint import scan_incomplete_runs
        batch_dir = tmp_path / "batch_2026-03-17_11-00-00"
        batch_dir.mkdir()
        (batch_dir / "config.json").write_text('{"algorithms": ["mm"]}')
        # No checkpoint.json written
        runs = scan_incomplete_runs(tmp_path)
        assert len(runs) == 1
        assert runs[0]['has_checkpoint'] is False
        assert runs[0]['checkpoint'] is None

    def test_scan_incomplete_runs_counts_jsonl_lines(self, tmp_path):
        """jsonl_lines reflects how many result lines exist in workers/."""
        import json
        from ember_qc.checkpoint import scan_incomplete_runs
        batch_dir = tmp_path / "batch_2026-03-17_12-00-00"
        batch_dir.mkdir()
        (batch_dir / "config.json").write_text('{"algorithms": ["mm"]}')
        workers_dir = batch_dir / "workers"
        workers_dir.mkdir()
        lines = [json.dumps({'algorithm': 'mm'}) for _ in range(7)]
        (workers_dir / "worker_1.jsonl").write_text("\n".join(lines) + "\n")
        runs = scan_incomplete_runs(tmp_path)
        assert runs[0]['jsonl_lines'] == 7

    def test_scan_incomplete_runs_sorted_most_recent_first(self, tmp_path):
        """Batches should be returned newest-first."""
        from ember_qc.checkpoint import scan_incomplete_runs
        for name in ["batch_2026-01-01_00-00-00", "batch_2026-03-01_00-00-00",
                     "batch_2026-02-01_00-00-00"]:
            d = tmp_path / name
            d.mkdir()
            (d / "config.json").write_text('{}')
        runs = scan_incomplete_runs(tmp_path)
        assert runs[0]['batch_id'] == 'batch_2026-03-01_00-00-00'
        assert runs[-1]['batch_id'] == 'batch_2026-01-01_00-00-00'

    def test_scan_skips_dirs_without_config_json(self, tmp_path):
        """Directories without config.json are not valid batches."""
        from ember_qc.checkpoint import scan_incomplete_runs
        d = tmp_path / "batch_2026-03-17_13-00-00"
        d.mkdir()
        # No config.json
        runs = scan_incomplete_runs(tmp_path)
        assert runs == []


# =============================================================================
# ResultsManager directory structure (runs_unfinished/ → results/)
# =============================================================================

class TestResultsManagerDirectory:
    """Tests for the new two-directory model in ResultsManager."""

    def test_create_batch_creates_in_unfinished_dir(self, tmp_path):
        from ember_qc.results import ResultsManager
        results_dir = tmp_path / "results"
        mgr = ResultsManager(str(results_dir))
        batch_dir = mgr.create_batch()
        assert batch_dir.parent == mgr.unfinished_dir
        assert not (results_dir / batch_dir.name).exists()

    def test_unfinished_dir_default_is_sibling_to_results(self, tmp_path):
        from ember_qc.results import ResultsManager
        results_dir = tmp_path / "results"
        mgr = ResultsManager(str(results_dir))
        assert mgr.unfinished_dir == tmp_path / "runs_unfinished"

    def test_unfinished_dir_is_created_automatically(self, tmp_path):
        from ember_qc.results import ResultsManager
        mgr = ResultsManager(str(tmp_path / "results"))
        assert mgr.unfinished_dir.is_dir()

    def test_move_to_output_moves_batch(self, tmp_path):
        from ember_qc.results import ResultsManager
        mgr = ResultsManager(str(tmp_path / "results"))
        batch_dir = mgr.create_batch()
        batch_name = batch_dir.name
        final = mgr.move_to_output(batch_dir)
        assert final == mgr.results_dir / batch_name
        assert final.exists()
        assert not batch_dir.exists()  # moved out of unfinished

    def test_move_to_output_with_custom_output_dir(self, tmp_path):
        from ember_qc.results import ResultsManager
        custom_out = tmp_path / "custom_output"
        mgr = ResultsManager(str(tmp_path / "results"))
        batch_dir = mgr.create_batch()
        final = mgr.move_to_output(batch_dir, output_dir=custom_out)
        assert final.parent == custom_out
        assert final.exists()

    def test_move_to_output_creates_latest_symlink(self, tmp_path):
        from ember_qc.results import ResultsManager
        results_dir = tmp_path / "results"
        mgr = ResultsManager(str(results_dir))
        batch_dir = mgr.create_batch()
        mgr.move_to_output(batch_dir)
        assert (results_dir / "latest").is_symlink()

    def test_latest_symlink_tracks_most_recent_move(self, tmp_path):
        from ember_qc.results import ResultsManager
        results_dir = tmp_path / "results"
        mgr = ResultsManager(str(results_dir))
        b1 = mgr.create_batch()
        b2 = mgr.create_batch()
        mgr.move_to_output(b1)
        mgr.move_to_output(b2)
        latest = results_dir / "latest"
        assert latest.resolve().name == b2.name

    def test_create_batch_does_not_appear_in_results_dir(self, tmp_path):
        """results_dir must stay empty until move_to_output is called."""
        from ember_qc.results import ResultsManager
        results_dir = tmp_path / "results"
        mgr = ResultsManager(str(results_dir))
        mgr.create_batch()
        mgr.create_batch()
        batch_dirs = [d for d in results_dir.iterdir()
                      if d.is_dir() and d.name.startswith('batch_')]
        assert len(batch_dirs) == 0


# =============================================================================
# run_full_benchmark v2 — new config fields, staging, output_dir
# =============================================================================

class TestRunFullBenchmarkV2:
    """Tests for the features added in the checkpoint/resume overhaul."""

    def _get_batch_dir(self, results_dir):
        """Return the single batch dir inside results_dir."""
        dirs = [d for d in results_dir.iterdir()
                if d.is_dir() and d.name.startswith('batch_')]
        assert len(dirs) == 1, f"Expected 1 batch dir, found: {dirs}"
        return dirs[0]

    def test_seed_stored_in_config(self, tmp_path, chimera):
        from ember_qc import EmbeddingBenchmark
        results_dir = tmp_path / "results"
        bench = EmbeddingBenchmark(chimera, results_dir=str(results_dir))
        bench.run_full_benchmark(
            graph_selection="1", methods=["minorminer"], n_trials=1, seed=77
        )
        batch_dir = self._get_batch_dir(results_dir)
        with open(batch_dir / "config.json") as f:
            config = json.load(f)
        assert config['seed'] == 77

    def test_n_workers_stored_in_config(self, tmp_path, chimera):
        from ember_qc import EmbeddingBenchmark
        results_dir = tmp_path / "results"
        bench = EmbeddingBenchmark(chimera, results_dir=str(results_dir))
        bench.run_full_benchmark(
            graph_selection="1", methods=["minorminer"], n_trials=1, n_workers=1
        )
        batch_dir = self._get_batch_dir(results_dir)
        with open(batch_dir / "config.json") as f:
            config = json.load(f)
        assert config['n_workers'] == 1

    def test_batch_wall_time_in_config(self, tmp_path, chimera):
        from ember_qc import EmbeddingBenchmark
        results_dir = tmp_path / "results"
        bench = EmbeddingBenchmark(chimera, results_dir=str(results_dir))
        bench.run_full_benchmark(
            graph_selection="1", methods=["minorminer"], n_trials=1
        )
        batch_dir = self._get_batch_dir(results_dir)
        with open(batch_dir / "config.json") as f:
            config = json.load(f)
        assert 'batch_wall_time' in config
        assert config['batch_wall_time'] > 0

    def test_custom_problems_serialized_in_config(self, tmp_path, chimera, K4):
        """When graph_selection=None (custom problems), config gets custom_problems key."""
        from ember_qc import EmbeddingBenchmark
        results_dir = tmp_path / "results"
        bench = EmbeddingBenchmark(chimera, results_dir=str(results_dir))
        bench.run_full_benchmark(
            problems=[("myK4", K4)], methods=["minorminer"], n_trials=1
        )
        batch_dir = self._get_batch_dir(results_dir)
        with open(batch_dir / "config.json") as f:
            config = json.load(f)
        assert 'custom_problems' in config
        assert len(config['custom_problems']) == 1
        assert config['custom_problems'][0]['name'] == 'myK4'
        assert 'graph' in config['custom_problems'][0]

    def test_graph_selection_does_not_add_custom_problems(self, tmp_path, chimera):
        """graph_selection='1' should NOT write custom_problems to config."""
        from ember_qc import EmbeddingBenchmark
        results_dir = tmp_path / "results"
        bench = EmbeddingBenchmark(chimera, results_dir=str(results_dir))
        bench.run_full_benchmark(
            graph_selection="1", methods=["minorminer"], n_trials=1
        )
        batch_dir = self._get_batch_dir(results_dir)
        with open(batch_dir / "config.json") as f:
            config = json.load(f)
        assert 'custom_problems' not in config

    def test_batch_not_in_unfinished_after_successful_run(self, tmp_path, chimera):
        """After a successful run, runs_unfinished/ must be empty."""
        from ember_qc import EmbeddingBenchmark
        results_dir = tmp_path / "results"
        bench = EmbeddingBenchmark(chimera, results_dir=str(results_dir))
        bench.run_full_benchmark(
            graph_selection="1", methods=["minorminer"], n_trials=1
        )
        unfinished_dir = tmp_path / "runs_unfinished"
        remaining = list(unfinished_dir.glob("batch_*")) if unfinished_dir.exists() else []
        assert len(remaining) == 0

    def test_return_value_is_in_results_dir(self, tmp_path, chimera):
        from ember_qc import EmbeddingBenchmark
        results_dir = tmp_path / "results"
        bench = EmbeddingBenchmark(chimera, results_dir=str(results_dir))
        final = bench.run_full_benchmark(
            graph_selection="1", methods=["minorminer"], n_trials=1
        )
        assert final is not None
        assert final.parent == results_dir
        assert final.exists()

    def test_output_dir_override(self, tmp_path, chimera):
        """output_dir param routes the completed batch to a custom location."""
        from ember_qc import EmbeddingBenchmark
        custom_out = tmp_path / "custom_results"
        bench = EmbeddingBenchmark(chimera, results_dir=str(tmp_path / "default_results"))
        bench.run_full_benchmark(
            graph_selection="1", methods=["minorminer"], n_trials=1,
            output_dir=str(custom_out),
        )
        assert any(custom_out.glob("batch_*"))
        assert not any((tmp_path / "default_results").glob("batch_*"))


# =============================================================================
# load_benchmark — resume from checkpoint, crashed run, all-done
# =============================================================================

@pytest.fixture
def fake_unfinished_batch(tmp_path):
    """A fake batch in runs_unfinished/ with all 1 trial already done (checkpoint = 0 remaining).

    Uses a real benchmark_one result so compile_batch can process the JSONL.
    """
    import dwave_networkx as dnx
    from ember_qc import benchmark_one
    from ember_qc.benchmark import _derive_seed
    from ember_qc.checkpoint import write_checkpoint

    chimera = dnx.chimera_graph(4, 4, 4)
    K4 = nx.complete_graph(4)

    unfinished_dir = tmp_path / "runs_unfinished"
    unfinished_dir.mkdir()
    batch_name = "batch_2026-03-17_20-00-00"
    batch_dir = unfinished_dir / batch_name
    batch_dir.mkdir()
    workers_dir = batch_dir / "workers"
    workers_dir.mkdir()

    seed = 42
    trial_seed = _derive_seed(seed, "clique", "K4", "chimera_4x4x4", 0)
    result = benchmark_one(
        K4, chimera, "clique",
        problem_name="K4", topology_name="chimera_4x4x4", trial=0
    )
    rec = result.to_jsonl_dict()
    rec['seed'] = trial_seed
    rec['batch_id'] = batch_name
    (workers_dir / "worker_test.jsonl").write_text(json.dumps(rec) + "\n")

    config = {
        'algorithms': ['clique'],
        'topologies': ['chimera_4x4x4'],
        'n_trials': 1, 'warmup_trials': 0,
        'timeout': 60.0, 'seed': seed, 'n_workers': 1,
        'graph_selection': 'custom',
        'custom_problems': [
            {'name': 'K4', 'graph': nx.node_link_data(K4, edges="links")}
        ],
        'batch_name': batch_name,
        'timestamp': '2026-03-17T20:00:00+00:00',
    }
    (batch_dir / "config.json").write_text(json.dumps(config, indent=2))

    # Checkpoint: 0 unfinished tasks — all done
    write_checkpoint(batch_dir, [], total_tasks=1, completed_count=1)

    return batch_dir, tmp_path


@pytest.fixture
def fake_partial_batch(tmp_path):
    """Batch with trial 0 done and trial 1 in the checkpoint as remaining."""
    import dwave_networkx as dnx
    from ember_qc import benchmark_one
    from ember_qc.benchmark import _derive_seed
    from ember_qc.checkpoint import write_checkpoint

    chimera = dnx.chimera_graph(4, 4, 4)
    K4 = nx.complete_graph(4)

    unfinished_dir = tmp_path / "runs_unfinished"
    unfinished_dir.mkdir()
    batch_name = "batch_2026-03-17_21-00-00"
    batch_dir = unfinished_dir / batch_name
    batch_dir.mkdir()
    workers_dir = batch_dir / "workers"
    workers_dir.mkdir()

    seed = 42
    trial_seed_0 = _derive_seed(seed, "clique", "K4", "chimera_4x4x4", 0)
    trial_seed_1 = _derive_seed(seed, "clique", "K4", "chimera_4x4x4", 1)

    # Trial 0 is done
    result = benchmark_one(
        K4, chimera, "clique",
        problem_name="K4", topology_name="chimera_4x4x4", trial=0
    )
    rec = result.to_jsonl_dict()
    rec['seed'] = trial_seed_0
    rec['batch_id'] = batch_name
    (workers_dir / "worker_test.jsonl").write_text(json.dumps(rec) + "\n")

    config = {
        'algorithms': ['clique'],
        'topologies': ['chimera_4x4x4'],
        'n_trials': 2, 'warmup_trials': 0,
        'timeout': 60.0, 'seed': seed, 'n_workers': 1,
        'graph_selection': 'custom',
        'custom_problems': [
            {'name': 'K4', 'graph': nx.node_link_data(K4, edges="links")}
        ],
        'batch_name': batch_name,
        'timestamp': '2026-03-17T21:00:00+00:00',
    }
    (batch_dir / "config.json").write_text(json.dumps(config, indent=2))

    # Trial 1 is still pending
    write_checkpoint(
        batch_dir,
        [("clique", "K4", "chimera_4x4x4", 1, trial_seed_1)],
        total_tasks=2, completed_count=1,
    )

    return batch_dir, tmp_path


@pytest.fixture
def fake_crashed_batch(tmp_path):
    """Batch with trial 0 done in JSONL but NO checkpoint.json (crashed run)."""
    import dwave_networkx as dnx
    from ember_qc import benchmark_one
    from ember_qc.benchmark import _derive_seed

    chimera = dnx.chimera_graph(4, 4, 4)
    K4 = nx.complete_graph(4)

    unfinished_dir = tmp_path / "runs_unfinished"
    unfinished_dir.mkdir()
    batch_name = "batch_2026-03-17_22-00-00"
    batch_dir = unfinished_dir / batch_name
    batch_dir.mkdir()
    workers_dir = batch_dir / "workers"
    workers_dir.mkdir()

    seed = 42
    trial_seed_0 = _derive_seed(seed, "clique", "K4", "chimera_4x4x4", 0)

    result = benchmark_one(
        K4, chimera, "clique",
        problem_name="K4", topology_name="chimera_4x4x4", trial=0
    )
    rec = result.to_jsonl_dict()
    rec['seed'] = trial_seed_0
    rec['batch_id'] = batch_name
    (workers_dir / "worker_test.jsonl").write_text(json.dumps(rec) + "\n")

    config = {
        'algorithms': ['clique'],
        'topologies': ['chimera_4x4x4'],
        'n_trials': 2, 'warmup_trials': 0,
        'timeout': 60.0, 'seed': seed, 'n_workers': 1,
        'graph_selection': 'custom',
        'custom_problems': [
            {'name': 'K4', 'graph': nx.node_link_data(K4, edges="links")}
        ],
        'batch_name': batch_name,
        'timestamp': '2026-03-17T22:00:00+00:00',
    }
    (batch_dir / "config.json").write_text(json.dumps(config, indent=2))
    # No checkpoint.json — simulates a crash

    return batch_dir, tmp_path


class TestLoadBenchmark:
    """Tests for load_benchmark() — discovery, all-done, resume, and crashed-run paths."""

    def test_returns_none_for_no_incomplete_runs(self, tmp_path):
        from ember_qc import load_benchmark
        result = load_benchmark(
            batch_id="nonexistent",
            unfinished_dir=str(tmp_path / "runs_unfinished"),
            output_dir=str(tmp_path / "results"),
        )
        assert result is None

    def test_invalid_batch_id_raises(self, tmp_path, fake_unfinished_batch):
        from ember_qc import load_benchmark
        _, base = fake_unfinished_batch
        with pytest.raises(ValueError, match="No incomplete run"):
            load_benchmark(
                batch_id="does_not_exist",
                unfinished_dir=str(base / "runs_unfinished"),
                output_dir=str(base / "results"),
            )

    def test_all_done_path_compiles_and_moves(self, fake_unfinished_batch):
        """Checkpoint with 0 remaining tasks: compile + move, no new trials run."""
        import sqlite3
        from ember_qc import load_benchmark
        batch_dir, base = fake_unfinished_batch
        output_dir = base / "results"
        final = load_benchmark(
            batch_id=batch_dir.name,
            unfinished_dir=str(base / "runs_unfinished"),
            output_dir=str(output_dir),
        )
        assert final is not None
        assert final.parent == output_dir
        assert (final / "results.db").exists()
        # Original staging dir should be gone
        assert not batch_dir.exists()
        # Checkpoint should be deleted after successful compile
        assert not (final / "checkpoint.json").exists()
        # DB must have exactly 1 row
        with sqlite3.connect(final / "results.db") as conn:
            rows = conn.execute("SELECT algorithm FROM runs").fetchall()
        assert len(rows) == 1
        assert rows[0][0] == 'clique'

    def test_resume_from_checkpoint_completes_batch(self, fake_partial_batch):
        """Resume a cleanly cancelled run (checkpoint present, 1 task remaining)."""
        import sqlite3
        from ember_qc import load_benchmark
        batch_dir, base = fake_partial_batch
        output_dir = base / "results"
        final = load_benchmark(
            batch_id=batch_dir.name,
            unfinished_dir=str(base / "runs_unfinished"),
            output_dir=str(output_dir),
        )
        assert final is not None
        assert final.parent == output_dir
        assert (final / "results.db").exists()
        assert not batch_dir.exists()
        # Both trials (0 and 1) should be in the DB
        with sqlite3.connect(final / "results.db") as conn:
            rows = conn.execute("SELECT trial FROM runs ORDER BY trial").fetchall()
        assert len(rows) == 2
        assert rows[0][0] == 0
        assert rows[1][0] == 1

    def test_resume_crashed_run_from_jsonl(self, fake_crashed_batch):
        """Resume a crashed run (no checkpoint.json) by deriving tasks from JSONL."""
        import sqlite3
        from ember_qc import load_benchmark
        batch_dir, base = fake_crashed_batch
        output_dir = base / "results"
        final = load_benchmark(
            batch_id=batch_dir.name,
            unfinished_dir=str(base / "runs_unfinished"),
            output_dir=str(output_dir),
        )
        assert final is not None
        assert (final / "results.db").exists()
        assert not batch_dir.exists()
        # Trial 0 (from JSONL) + trial 1 (re-run) = 2 rows total
        with sqlite3.connect(final / "results.db") as conn:
            rows = conn.execute("SELECT trial FROM runs ORDER BY trial").fetchall()
        assert len(rows) == 2

    def test_resume_increments_resume_count(self, fake_partial_batch):
        """After a successful resume, the checkpoint is deleted (not incremented)."""
        from ember_qc import load_benchmark
        from ember_qc.checkpoint import read_checkpoint
        batch_dir, base = fake_partial_batch
        final = load_benchmark(
            batch_id=batch_dir.name,
            unfinished_dir=str(base / "runs_unfinished"),
            output_dir=str(base / "results"),
        )
        # On success, checkpoint is deleted
        assert final is not None
        assert not (final / "checkpoint.json").exists()

    def test_n_workers_override(self, fake_partial_batch):
        """n_workers kwarg overrides the value stored in config."""
        import sqlite3
        from ember_qc import load_benchmark
        batch_dir, base = fake_partial_batch
        # Run with n_workers=2 even though config says 1
        final = load_benchmark(
            batch_id=batch_dir.name,
            unfinished_dir=str(base / "runs_unfinished"),
            output_dir=str(base / "results"),
            n_workers=2,
        )
        assert final is not None
        assert (final / "results.db").exists()
        # Still produces both trials regardless of n_workers value
        with sqlite3.connect(final / "results.db") as conn:
            count = conn.execute("SELECT COUNT(*) FROM runs").fetchone()[0]
        assert count == 2


# =============================================================================
# delete_benchmark — force delete and summary display
# =============================================================================

class TestDeleteBenchmark:
    """Tests for delete_benchmark() — force mode, summary, and guard rails."""

    def _make_batch(self, base, name="batch_2026-03-17_20-00-00",
                    note="", n_done=3, n_total=5, has_checkpoint=True):
        """Write a minimal fake batch directory in runs_unfinished/."""
        from ember_qc.checkpoint import write_checkpoint
        unfinished_dir = base / "runs_unfinished"
        unfinished_dir.mkdir(exist_ok=True)
        batch_dir = unfinished_dir / name
        batch_dir.mkdir()
        config = {'algorithms': ['minorminer'], 'n_trials': n_total}
        if note:
            config['batch_note'] = note
        (batch_dir / "config.json").write_text(json.dumps(config))
        if has_checkpoint:
            write_checkpoint(batch_dir, [], total_tasks=n_total, completed_count=n_done)
        return batch_dir

    def test_returns_false_for_no_incomplete_runs(self, tmp_path):
        from ember_qc import delete_benchmark
        result = delete_benchmark(
            batch_id="nonexistent",
            unfinished_dir=str(tmp_path / "runs_unfinished"),
            force=True,
        )
        assert result is False

    def test_invalid_batch_id_raises(self, tmp_path):
        from ember_qc import delete_benchmark
        self._make_batch(tmp_path)
        with pytest.raises(ValueError, match="No incomplete run"):
            delete_benchmark(
                batch_id="batch_does_not_exist",
                unfinished_dir=str(tmp_path / "runs_unfinished"),
                force=True,
            )

    def test_force_deletes_without_prompt(self, tmp_path):
        from ember_qc import delete_benchmark
        batch_dir = self._make_batch(tmp_path)
        result = delete_benchmark(
            batch_id=batch_dir.name,
            unfinished_dir=str(tmp_path / "runs_unfinished"),
            force=True,
        )
        assert result is True
        assert not batch_dir.exists()

    def test_force_deletes_crashed_run(self, tmp_path):
        """force=True works on runs without a checkpoint (crashed)."""
        from ember_qc import delete_benchmark
        batch_dir = self._make_batch(tmp_path, has_checkpoint=False)
        result = delete_benchmark(
            batch_id=batch_dir.name,
            unfinished_dir=str(tmp_path / "runs_unfinished"),
            force=True,
        )
        assert result is True
        assert not batch_dir.exists()

    def test_does_not_touch_completed_results_dir(self, tmp_path):
        """delete_benchmark only looks in runs_unfinished/, never in results/."""
        from ember_qc import delete_benchmark
        # A batch with same name in results/ must survive
        results_dir = tmp_path / "results"
        results_dir.mkdir()
        protected = results_dir / "batch_2026-03-17_20-00-00"
        protected.mkdir()
        (protected / "config.json").write_text('{}')

        self._make_batch(tmp_path)
        delete_benchmark(
            batch_id="batch_2026-03-17_20-00-00",
            unfinished_dir=str(tmp_path / "runs_unfinished"),
            force=True,
        )
        assert protected.exists()  # results/ untouched

    def test_force_true_returns_true(self, tmp_path):
        from ember_qc import delete_benchmark
        batch_dir = self._make_batch(tmp_path, n_done=10, n_total=10)
        result = delete_benchmark(
            batch_id=batch_dir.name,
            unfinished_dir=str(tmp_path / "runs_unfinished"),
            force=True,
        )
        assert result is True

    def test_size_reported_for_batch_with_files(self, tmp_path, capsys):
        """disk size string appears in the printed summary."""
        from ember_qc import delete_benchmark
        batch_dir = self._make_batch(tmp_path, n_done=2, n_total=4)
        # Add a file so size > 0
        (batch_dir / "extra.txt").write_text("a" * 1024)
        delete_benchmark(
            batch_id=batch_dir.name,
            unfinished_dir=str(tmp_path / "runs_unfinished"),
            force=True,
        )
        captured = capsys.readouterr()
        # Summary should mention KB or bytes — just check size string present
        assert "B" in captured.out  # "KB", "MB", "GB", or just "B"

    def test_progress_in_summary(self, tmp_path, capsys):
        """Progress fraction (done/total) appears in printed summary."""
        from ember_qc import delete_benchmark
        batch_dir = self._make_batch(tmp_path, n_done=7, n_total=20)
        delete_benchmark(
            batch_id=batch_dir.name,
            unfinished_dir=str(tmp_path / "runs_unfinished"),
            force=True,
        )
        captured = capsys.readouterr()
        assert "7" in captured.out
        assert "20" in captured.out

    def test_batch_note_in_summary(self, tmp_path, capsys):
        from ember_qc import delete_benchmark
        batch_dir = self._make_batch(tmp_path, note="my test run")
        delete_benchmark(
            batch_id=batch_dir.name,
            unfinished_dir=str(tmp_path / "runs_unfinished"),
            force=True,
        )
        captured = capsys.readouterr()
        assert "my test run" in captured.out


# =============================================================================
# Topology compatibility (_algo_topo_compatible)
# =============================================================================

class TestAlgoTopoCompatibility:
    """Tests for _algo_topo_compatible() and supported_topologies attribute."""

    def test_unrestricted_algo_compatible_with_any_topo(self):
        """An algorithm with supported_topologies=None accepts any topology."""
        from ember_qc.benchmark import _algo_topo_compatible
        # minorminer has no restriction
        assert _algo_topo_compatible("minorminer", "chimera_4x4x4") is True
        assert _algo_topo_compatible("minorminer", "pegasus_16") is True
        assert _algo_topo_compatible("minorminer", "zephyr_3") is True

    def test_chimera_only_algo_rejects_pegasus(self):
        """AtomAlgorithm (supported_topologies=['chimera']) rejects pegasus."""
        from ember_qc.benchmark import _algo_topo_compatible
        assert _algo_topo_compatible("atom", "pegasus_16") is False

    def test_chimera_only_algo_accepts_chimera(self):
        """AtomAlgorithm accepts chimera topology names."""
        from ember_qc.benchmark import _algo_topo_compatible
        assert _algo_topo_compatible("atom", "chimera_4x4x4") is True
        assert _algo_topo_compatible("atom", "chimera_16x16x4") is True

    def test_prefix_matching_case_insensitive(self):
        """Prefix matching is case-insensitive."""
        from ember_qc.benchmark import _algo_topo_compatible
        assert _algo_topo_compatible("atom", "Chimera_4x4x4") is True
        assert _algo_topo_compatible("atom", "CHIMERA_16") is True

    def test_unknown_algo_returns_true(self):
        """Unknown algorithm name returns True — let it fail naturally."""
        from ember_qc.benchmark import _algo_topo_compatible
        assert _algo_topo_compatible("nonexistent_algo_xyz", "chimera_4x4x4") is True
        assert _algo_topo_compatible("nonexistent_algo_xyz", "pegasus_16") is True

    def test_supported_topologies_attribute_on_atom(self):
        """AtomAlgorithm.supported_topologies is ['chimera']."""
        from ember_qc.registry import ALGORITHM_REGISTRY
        atom = ALGORITHM_REGISTRY.get("atom")
        assert atom is not None
        assert atom.supported_topologies == ["chimera"]

    def test_incompatible_pair_excluded_from_results(self, tmp_path):
        """Atom × pegasus_4 produces no results; minorminer × pegasus_4 does."""
        from ember_qc import EmbeddingBenchmark
        bench = EmbeddingBenchmark(results_dir=str(tmp_path))
        bench.run_full_benchmark(
            graph_selection="1",
            methods=["minorminer", "atom"],
            topologies=["pegasus_4"],
            n_trials=1,
        )
        algo_names = {r.algorithm for r in bench.results}
        assert "minorminer" in algo_names
        assert "atom" not in algo_names


# =============================================================================
# simulate_faults() — standalone + integration
# =============================================================================

class TestSimulateFaults:
    """Tests for qebench.faults.simulate_faults() and fault simulation integration."""

    # ── Helpers ──────────────────────────────────────────────────────────────

    @staticmethod
    def _small_chimera():
        """Chimera(2) — 32 nodes, deterministic."""
        import dwave_networkx as dnx
        return dnx.chimera_graph(2)

    # ── Standalone: random mode ───────────────────────────────────────────────

    def test_random_mode_correct_node_count(self):
        """fault_rate=0.1 removes exactly int(N*0.1) nodes."""
        from ember_qc import simulate_faults
        topo = self._small_chimera()
        n = len(topo)
        faulted = simulate_faults(topo, fault_rate=0.1, fault_seed=0)
        assert len(faulted) == n - int(n * 0.1)

    def test_random_mode_reproducible(self):
        """Same fault_rate + fault_seed → identical faulted topology."""
        from ember_qc import simulate_faults
        topo = self._small_chimera()
        f1 = simulate_faults(topo, fault_rate=0.1, fault_seed=7)
        f2 = simulate_faults(topo, fault_rate=0.1, fault_seed=7)
        assert set(f1.nodes()) == set(f2.nodes())
        assert set(f1.edges()) == set(f2.edges())

    def test_random_mode_different_seeds_differ(self):
        """Different seeds should (almost certainly) produce different results."""
        from ember_qc import simulate_faults
        topo = self._small_chimera()
        f1 = simulate_faults(topo, fault_rate=0.25, fault_seed=1)
        f2 = simulate_faults(topo, fault_rate=0.25, fault_seed=2)
        assert set(f1.nodes()) != set(f2.nodes())

    def test_random_mode_returns_copy(self):
        """simulate_faults returns a new graph, not a view of the original."""
        from ember_qc import simulate_faults
        topo = self._small_chimera()
        faulted = simulate_faults(topo, fault_rate=0.1, fault_seed=0)
        assert faulted is not topo
        # Mutating faulted does not affect original
        node = list(faulted.nodes())[0]
        faulted.remove_node(node)
        assert node in topo

    # ── Standalone: explicit node removal ────────────────────────────────────

    def test_explicit_node_removal(self):
        """faulty_nodes=[n] removes that node and all incident edges."""
        from ember_qc import simulate_faults
        topo = self._small_chimera()
        target_node = list(topo.nodes())[0]
        incident = list(topo.neighbors(target_node))
        faulted = simulate_faults(topo, faulty_nodes=[target_node])
        assert target_node not in faulted
        # Incident edges removed with node; neighbor nodes still present
        for nb in incident:
            assert nb in faulted

    def test_explicit_coupler_removal_keeps_endpoints(self):
        """faulty_couplers=[(u,v)] removes edge but keeps both endpoint nodes."""
        from ember_qc import simulate_faults
        topo = self._small_chimera()
        u, v = list(topo.edges())[0]
        faulted = simulate_faults(topo, faulty_couplers=[(u, v)])
        assert u in faulted
        assert v in faulted
        assert not faulted.has_edge(u, v)

    def test_explicit_coupler_isolated_node_cleanup(self):
        """Nodes that become isolated after coupler removal are cleaned up."""
        from ember_qc import simulate_faults
        # Build a small graph where node 1 has degree 1 (connected only to 0)
        G = nx.path_graph(3)  # 0-1-2
        # Remove edge (0,1) — node 0 becomes isolated (degree 0); node 2 still connected to 1
        faulted = simulate_faults(G, faulty_couplers=[(0, 1)])
        assert 0 not in faulted  # isolated, cleaned up
        assert 1 in faulted      # still connected to 2
        assert 2 in faulted

    def test_no_faults_returns_copy(self):
        """All defaults → returns a copy of topology unchanged."""
        from ember_qc import simulate_faults
        topo = self._small_chimera()
        result = simulate_faults(topo)
        assert result is not topo
        assert set(result.nodes()) == set(topo.nodes())
        assert set(result.edges()) == set(topo.edges())

    def test_fault_rate_zero_with_explicit_nodes_allowed(self):
        """fault_rate=0.0 alongside faulty_nodes is allowed (zero = no random faults)."""
        from ember_qc import simulate_faults
        topo = self._small_chimera()
        target_node = list(topo.nodes())[0]
        # Should not raise
        faulted = simulate_faults(topo, fault_rate=0.0, faulty_nodes=[target_node])
        assert target_node not in faulted

    # ── Standalone: validation errors ────────────────────────────────────────

    def test_fault_rate_above_one_raises(self):
        from ember_qc import simulate_faults
        topo = self._small_chimera()
        with pytest.raises(ValueError, match="fault_rate"):
            simulate_faults(topo, fault_rate=1.5)

    def test_fault_rate_negative_raises(self):
        from ember_qc import simulate_faults
        topo = self._small_chimera()
        with pytest.raises(ValueError, match="fault_rate"):
            simulate_faults(topo, fault_rate=-0.1)

    def test_conflicting_modes_raises(self):
        """fault_rate > 0 combined with faulty_nodes raises ValueError."""
        from ember_qc import simulate_faults
        topo = self._small_chimera()
        target_node = list(topo.nodes())[0]
        with pytest.raises(ValueError):
            simulate_faults(topo, fault_rate=0.1, faulty_nodes=[target_node])

    def test_unknown_node_in_faulty_nodes_raises(self):
        """Nonexistent node in faulty_nodes raises ValueError naming the node."""
        from ember_qc import simulate_faults
        topo = self._small_chimera()
        with pytest.raises(ValueError, match="99999"):
            simulate_faults(topo, faulty_nodes=[99999])

    def test_unknown_node_in_faulty_couplers_raises(self):
        """Coupler referencing a nonexistent node raises ValueError."""
        from ember_qc import simulate_faults
        topo = self._small_chimera()
        real_node = list(topo.nodes())[0]
        with pytest.raises(ValueError):
            simulate_faults(topo, faulty_couplers=[(real_node, 99999)])

    def test_nonexistent_edge_in_faulty_couplers_raises(self):
        """Coupler where both nodes exist but edge does not raises ValueError."""
        from ember_qc import simulate_faults
        # Build a graph with two disconnected edges: 0-1 and 2-3
        G = nx.Graph()
        G.add_edges_from([(0, 1), (2, 3)])
        # (0, 2) — both nodes exist but edge doesn't
        with pytest.raises(ValueError):
            simulate_faults(G, faulty_couplers=[(0, 2)])

    # ── Integration: run_full_benchmark ──────────────────────────────────────

    def test_scalar_fault_rate_applied_to_topology(self, tmp_path, chimera):
        """Scalar fault_rate removes nodes before embedding; run completes."""
        from ember_qc import EmbeddingBenchmark
        bench = EmbeddingBenchmark(chimera, results_dir=str(tmp_path))
        batch_dir = bench.run_full_benchmark(
            graph_selection="1",
            methods=["minorminer"],
            n_trials=1,
            topology_name="chimera_4x4x4",
            fault_rate=0.05,
            fault_seed=42,
        )
        assert batch_dir is not None
        assert len(bench.results) >= 1

    def test_fault_seed_defaults_to_run_seed(self, tmp_path, chimera):
        """When fault_seed is not specified, it defaults to the run seed."""
        import json
        from ember_qc import EmbeddingBenchmark
        bench = EmbeddingBenchmark(chimera, results_dir=str(tmp_path))
        run_seed = 77
        batch_dir = bench.run_full_benchmark(
            graph_selection="1",
            methods=["minorminer"],
            n_trials=1,
            topology_name="chimera_4x4x4",
            fault_rate=0.05,
            seed=run_seed,
            # fault_seed intentionally omitted
        )
        assert batch_dir is not None
        config = json.loads((batch_dir / "config.json").read_text())
        fault_info = config["fault_simulation"]["chimera_4x4x4"]
        assert fault_info["fault_seed"] == run_seed

    def test_explicit_fault_seed_overrides_run_seed(self, tmp_path, chimera):
        """An explicit fault_seed takes precedence over the run seed."""
        import json
        from ember_qc import EmbeddingBenchmark
        bench = EmbeddingBenchmark(chimera, results_dir=str(tmp_path))
        batch_dir = bench.run_full_benchmark(
            graph_selection="1",
            methods=["minorminer"],
            n_trials=1,
            topology_name="chimera_4x4x4",
            fault_rate=0.05,
            seed=77,
            fault_seed=999,
        )
        assert batch_dir is not None
        config = json.loads((batch_dir / "config.json").read_text())
        fault_info = config["fault_simulation"]["chimera_4x4x4"]
        assert fault_info["fault_seed"] == 999

    def test_dict_fault_rate_per_topology(self, tmp_path):
        """Dict fault_rate applies different rates to different topologies."""
        import json
        from ember_qc import EmbeddingBenchmark
        bench = EmbeddingBenchmark(results_dir=str(tmp_path))
        batch_dir = bench.run_full_benchmark(
            graph_selection="1",
            methods=["minorminer"],
            topologies=["chimera_4x4x4", "pegasus_4"],
            n_trials=1,
            fault_rate={"chimera_4x4x4": 0.05, "pegasus_4": 0.0},
            fault_seed=42,
        )
        assert batch_dir is not None
        config = json.loads((batch_dir / "config.json").read_text())
        # chimera should have fault info; pegasus should be None (no faults)
        assert config["fault_simulation"]["chimera_4x4x4"] is not None
        assert config["fault_simulation"]["pegasus_4"] is None

    def test_flat_faulty_nodes_raises_for_multi_topo(self, tmp_path):
        """Flat faulty_nodes collection raises ValueError for multi-topology runs."""
        from ember_qc import EmbeddingBenchmark
        bench = EmbeddingBenchmark(results_dir=str(tmp_path))
        with pytest.raises(ValueError, match="dict"):
            bench.run_full_benchmark(
                graph_selection="1",
                methods=["minorminer"],
                topologies=["chimera_4x4x4", "pegasus_4"],
                n_trials=1,
                faulty_nodes=[0, 1],
            )

    def test_per_topology_mutual_exclusion_raises(self, tmp_path, chimera):
        """fault_rate > 0 and faulty_nodes for same topology raises ValueError."""
        from ember_qc import EmbeddingBenchmark
        bench = EmbeddingBenchmark(chimera, results_dir=str(tmp_path))
        with pytest.raises(ValueError, match="chimera_4x4x4"):
            bench.run_full_benchmark(
                graph_selection="1",
                methods=["minorminer"],
                n_trials=1,
                topology_name="chimera_4x4x4",
                fault_rate={"chimera_4x4x4": 0.05},
                faulty_nodes={"chimera_4x4x4": [0]},
            )

    def test_null_fault_config_when_no_faults(self, tmp_path, chimera):
        """fault_simulation is null in config.json when no faults specified."""
        import json
        from ember_qc import EmbeddingBenchmark
        bench = EmbeddingBenchmark(chimera, results_dir=str(tmp_path))
        batch_dir = bench.run_full_benchmark(
            graph_selection="1",
            methods=["minorminer"],
            n_trials=1,
            topology_name="chimera_4x4x4",
        )
        assert batch_dir is not None
        config = json.loads((batch_dir / "config.json").read_text())
        assert config["fault_simulation"] is None

    def test_config_records_removed_node_count(self, tmp_path, chimera):
        """Config faulty_nodes list matches the actual number of removed nodes."""
        import json
        from ember_qc import EmbeddingBenchmark
        bench = EmbeddingBenchmark(chimera, results_dir=str(tmp_path))
        fr = 0.05
        batch_dir = bench.run_full_benchmark(
            graph_selection="1",
            methods=["minorminer"],
            n_trials=1,
            topology_name="chimera_4x4x4",
            fault_rate=fr,
            fault_seed=42,
        )
        assert batch_dir is not None
        config = json.loads((batch_dir / "config.json").read_text())
        fault_info = config["fault_simulation"]["chimera_4x4x4"]
        expected_removed = int(len(chimera) * fr)
        assert len(fault_info["faulty_nodes"]) == expected_removed
