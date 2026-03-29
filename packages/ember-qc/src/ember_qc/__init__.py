"""
ember-qc — Quantum Minor-Embedding Benchmark Suite

Core usage:
    from ember_qc import benchmark_one, EmbeddingResult, load_test_graphs

    result = benchmark_one(source_graph, target_graph, "minorminer")
"""

__version__ = "0.5.0"

# Core benchmark function and result type
from ember_qc.benchmark import (
    benchmark_one,
    compute_embedding_metrics,
    EmbeddingResult,
    EmbeddingBenchmark,
    load_benchmark,
    delete_benchmark,
)

# Fault simulation
from ember_qc.faults import simulate_faults

# Results storage
from ember_qc.results import ResultsManager

# Algorithm registry
from ember_qc.registry import (
    ALGORITHM_REGISTRY,
    EmbeddingAlgorithm,
    register_algorithm,
    validate_embedding,
    list_algorithms,
)

# Graph library
from ember_qc.load_graphs import (
    load_graph,
    load_test_graphs,
    parse_graph_selection,
    load_presets,
    list_presets,
    load_manifest,
    verify_manifest,
)

# User config
from ember_qc.config import get, set_value, reset, show, resolve_output_dir, get_user_data_dir

# Topology registry
from ember_qc.topologies import (
    TOPOLOGY_REGISTRY,
    TopologyConfig,
    register_topology,
    get_topology,
    get_topology_config,
    list_topologies,
    list_topology_families,
    topology_info,
)

__all__ = [
    # Benchmark
    "benchmark_one",
    "compute_embedding_metrics",
    "EmbeddingResult",
    "EmbeddingBenchmark",
    "load_benchmark",
    "delete_benchmark",
    # Results
    "ResultsManager",
    # Registry
    "ALGORITHM_REGISTRY",
    "EmbeddingAlgorithm",
    "register_algorithm",
    "validate_embedding",
    "list_algorithms",
    # Graphs
    "load_test_graphs",
    "parse_graph_selection",
    "load_presets",
    "list_presets",
    "load_graph",
    "load_manifest",
    "verify_manifest",
    # Fault simulation
    "simulate_faults",
    # Config
    "get",
    "set_value",
    "reset",
    "show",
    "resolve_output_dir",
    "get_user_data_dir",
    # Topologies
    "TOPOLOGY_REGISTRY",
    "TopologyConfig",
    "register_topology",
    "get_topology",
    "get_topology_config",
    "list_topologies",
    "list_topology_families",
    "topology_info",
]
