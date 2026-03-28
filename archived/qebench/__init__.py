"""
QEBench — Quantum Embedding Benchmark Suite

Core usage:
    from qebench import benchmark_one, EmbeddingResult, load_test_graphs

    result = benchmark_one(source_graph, target_graph, "minorminer")
"""

__version__ = "0.5.0"

# Core benchmark function and result type
from qebench.benchmark import (
    benchmark_one,
    compute_embedding_metrics,
    EmbeddingResult,
    EmbeddingBenchmark,
    load_benchmark,
    delete_benchmark,
)

# Fault simulation
from qebench.faults import simulate_faults

# Results storage
from qebench.results import ResultsManager

# Algorithm registry
from qebench.registry import (
    ALGORITHM_REGISTRY,
    EmbeddingAlgorithm,
    register_algorithm,
    validate_embedding,
    list_algorithms,
)

# Graph library
from qebench.graphs import (
    load_test_graphs,
    parse_graph_selection,
    load_presets,
    list_presets,
    generate_manifest,
    verify_manifest,
)

# Topology registry
from qebench.topologies import (
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
    "generate_manifest",
    "verify_manifest",
    # Fault simulation
    "simulate_faults",
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
