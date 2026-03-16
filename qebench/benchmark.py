"""
Benchmarking Framework for Minor Embedding Algorithms

Core function:
    result = benchmark_one(source_graph, target_graph, "minorminer")

Batch runner:
    bench = EmbeddingBenchmark(target_graph)
    bench.run_full_benchmark(graph_selection="quick", methods=["minorminer"])
"""

import hashlib
import multiprocessing
import os
import time
try:
    import resource as _resource
    _HAS_RESOURCE = True
except ImportError:
    _HAS_RESOURCE = False
import numpy as np
import networkx as nx
import json
import pandas as pd
from typing import Dict, List, Tuple, Any, Optional
from dataclasses import dataclass, asdict, field
from collections import defaultdict
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

from qebench.registry import ALGORITHM_REGISTRY, list_algorithms
from qebench.validation import validate_layer1, validate_layer2
from qebench.graphs import load_test_graphs as _load_test_graphs, parse_graph_selection, verify_manifest
from qebench.results import ResultsManager
from qebench.topologies import get_topology, TOPOLOGY_REGISTRY
from qebench.compile import compile_batch
from qebench.loggers import BatchLogger, capture_run, run_log_path


@dataclass
class EmbeddingResult:
    """Result from a single embedding attempt."""
    # Identification
    algorithm: str
    problem_name: str
    topology_name: str
    trial: int

    # Always populated by the runner:
    success: bool
    status: str = 'FAILURE'    # 'SUCCESS' | 'INVALID_OUTPUT' | 'TIMEOUT' | 'CRASH' | 'OOM' | 'FAILURE'
    wall_time: float = 0.0     # wall-clock seconds (runner-measured)
    cpu_time: float = 0.0      # CPU seconds (RUSAGE_CHILDREN for subprocess; process_time otherwise)
    is_valid: bool = False
    embedding: Optional[Dict] = None  # {source_node: [target_qubits, ...]}

    # Embedding quality metrics (populated on SUCCESS only):
    chain_lengths: List[int] = field(default_factory=list)
    max_chain_length: int = 0
    avg_chain_length: float = 0.0
    total_qubits_used: int = 0
    total_couplers_used: int = 0

    # Problem metadata:
    problem_nodes: int = 0
    problem_edges: int = 0
    problem_density: float = 0.0

    # Algorithm metadata:
    algorithm_version: str = "unknown"

    # Failure / diagnostic fields:
    partial: bool = False              # True if embedding has overlaps (timeout case)
    error: Optional[str] = None        # traceback or error message on failure
    metadata: Optional[Dict] = None    # anything else the algorithm wants to report

    # Algorithmic operation counters — hardware-agnostic work metrics.
    # None means the algorithm does not report this counter; 0 is a valid value.
    target_node_visits: Optional[int] = None        # search effort
    cost_function_evaluations: Optional[int] = None # decision effort
    embedding_state_mutations: Optional[int] = None # editing effort
    overlap_qubit_iterations: Optional[int] = None  # congestion effort (iterative algos only)
    
    def to_dict(self):
        """Convert to dict. Embedding stored as JSON string for CSV compatibility."""
        d = asdict(self)
        if d['embedding'] is not None:
            # Convert int keys to strings for JSON serialization
            d['embedding'] = json.dumps({str(k): v for k, v in d['embedding'].items()})
        return d

    def to_jsonl_dict(self):
        """Convert to dict for worker JSONL files.

        Differs from to_dict():
        - embedding stored as nested dict {"0": [q1, q2], ...} — not a JSON string
        - chain_lengths included as a plain list (omitted from SQLite later, not here)
        This makes the JSONL record the definitive complete archive of each trial.
        """
        d = asdict(self)
        if d['embedding'] is not None:
            d['embedding'] = {str(k): list(v) for k, v in d['embedding'].items()}
        return d


# ==============================================================================
# STANDALONE FUNCTIONS — the atomic building blocks
# ==============================================================================

def compute_embedding_metrics(embedding: Dict[int, list], 
                               target_graph: nx.Graph) -> Dict:
    """Compute quality metrics for an embedding.
    
    Args:
        embedding: {source_node: [target_qubits, ...]}
        target_graph: Hardware graph (needed for coupler counting)
        
    Returns:
        Dict with chain_lengths, avg/max chain length, qubits, couplers.
    """
    chain_lengths = [len(chain) for chain in embedding.values()]
    
    all_qubits = set()
    coupler_count = 0
    
    for chain in embedding.values():
        all_qubits.update(chain)
        for i in range(len(chain)):
            for j in range(i + 1, len(chain)):
                if target_graph.has_edge(chain[i], chain[j]):
                    coupler_count += 1
    
    return {
        'chain_lengths': chain_lengths,
        'avg_chain_length': float(np.mean(chain_lengths)),
        'max_chain_length': max(chain_lengths),
        'total_qubits_used': len(all_qubits),
        'total_couplers_used': coupler_count
    }


def benchmark_one(source_graph: nx.Graph,
                  target_graph: nx.Graph,
                  algorithm: str,
                  timeout: float = 60.0,
                  problem_name: str = "",
                  topology_name: str = "",
                  trial: int = 0,
                  **kwargs) -> EmbeddingResult:
    """Run a single embedding benchmark. The atomic unit of the framework.
    
    Args:
        source_graph: Problem graph to embed.
        target_graph: Hardware topology graph.
        algorithm: Name of registered algorithm (e.g., "minorminer").
        timeout: Max seconds for this attempt.
        problem_name: Label for this problem (e.g., "K10").
        topology_name: Label for the hardware (e.g., "chimera_4x4x4").
        trial: Which trial number (metadata only).
        **kwargs: Forwarded to algorithm.embed() for hyperparameter control.
    
    Returns:
        EmbeddingResult with the embedding, metrics, and validation.
    """
    # Resolve algorithm from registry
    if algorithm not in ALGORITHM_REGISTRY:
        raise ValueError(
            f"Unknown algorithm '{algorithm}'. "
            f"Available: {list(ALGORITHM_REGISTRY.keys())}"
        )
    algo = ALGORITHM_REGISTRY[algorithm]
    
    # Problem metadata
    n_nodes = source_graph.number_of_nodes()
    n_edges = source_graph.number_of_edges()
    density = (2 * n_edges / (n_nodes * (n_nodes - 1))) if n_nodes > 1 else 0.0
    
    # Common fields for failure results
    fail_base = dict(
        algorithm=algorithm,
        problem_name=problem_name,
        topology_name=topology_name,
        trial=trial,
        success=False,
        problem_nodes=n_nodes,
        problem_edges=n_edges,
        problem_density=density,
    )
    
    try:
        uses_subprocess = getattr(algo, '_uses_subprocess', False)
        if uses_subprocess and _HAS_RESOURCE:
            _rusage_before = _resource.getrusage(_resource.RUSAGE_CHILDREN)
        _cpu_start = time.process_time()

        result = algo.embed(source_graph, target_graph, timeout=timeout, **kwargs)

        _cpu_elapsed = time.process_time() - _cpu_start
        if uses_subprocess and _HAS_RESOURCE:
            _rusage_after = _resource.getrusage(_resource.RUSAGE_CHILDREN)
            _cpu_elapsed = (
                (_rusage_after.ru_utime - _rusage_before.ru_utime) +
                (_rusage_after.ru_stime - _rusage_before.ru_stime)
            )

        algo_version = getattr(algo, 'version', 'unknown')

        if result is None:
            return EmbeddingResult(
                **fail_base,
                status='FAILURE',
                wall_time=timeout,
                cpu_time=_cpu_elapsed,
                algorithm_version=algo_version,
                error="Algorithm returned None",
            )

        # ------------------------------------------------------------------
        # Layer 2 — type/format validation (always, before anything else).
        # Catches numpy int leakage, bad chain types, NaN times, etc.
        # If it fails, status is INVALID_OUTPUT — no further processing.
        # ------------------------------------------------------------------
        layer2 = validate_layer2(result, source_graph, target_graph)
        if not layer2.passed:
            _claimed_success = result.get('success', '<absent>')
            _emb_size = len(result.get('embedding') or {})
            return EmbeddingResult(
                **fail_base,
                status='INVALID_OUTPUT',
                wall_time=result.get('time', 0.0),
                cpu_time=_cpu_elapsed,
                algorithm_version=algo_version,
                error=(
                    f"Algorithm claimed success={_claimed_success}, "
                    f"embedding_size={_emb_size}; "
                    f"Layer 2 [{layer2.check_name}]: {layer2.detail}"
                ),
            )

        # ------------------------------------------------------------------
        # Trustless success inference — never trust the algorithm's own flag.
        # Infer from embedding presence if the key is absent.
        # ------------------------------------------------------------------
        claimed_success = result.get('success', len(result.get('embedding', {})) > 0)
        raw_embedding = result.get('embedding') or None  # treat {} as falsy
        is_partial = result.get('partial', False)
        layer1 = None  # set below only when structural validation runs

        if claimed_success and raw_embedding:
            # Validate against the target graph the algorithm actually used
            # (OCT self-reports chimera_graph when it resizes the topology)
            validation_target = result.get('chimera_graph', target_graph)
            layer1 = validate_layer1(raw_embedding, source_graph, validation_target)
            if layer1.passed:
                status = 'SUCCESS'
                success = True
            else:
                status = 'INVALID_OUTPUT'
                success = False
        elif is_partial:
            # Algorithm hit a limit but returned a partial state — preserve for
            # diagnostic telemetry but do not pass to metrics calculators.
            status = result.get('status', 'TIMEOUT')
            success = False
            raw_embedding = None
        else:
            status = result.get('status', 'FAILURE')
            success = False

        if success and raw_embedding:
            metrics = compute_embedding_metrics(raw_embedding, validation_target)
            return EmbeddingResult(
                algorithm=algorithm,
                problem_name=problem_name,
                topology_name=topology_name,
                trial=trial,
                success=True,
                status=status,
                wall_time=result.get('time', 0.0),
                cpu_time=_cpu_elapsed,
                is_valid=True,
                embedding=raw_embedding,
                chain_lengths=metrics['chain_lengths'],
                max_chain_length=metrics['max_chain_length'],
                avg_chain_length=metrics['avg_chain_length'],
                total_qubits_used=metrics['total_qubits_used'],
                total_couplers_used=metrics['total_couplers_used'],
                problem_nodes=n_nodes,
                problem_edges=n_edges,
                problem_density=density,
                algorithm_version=algo_version,
                partial=False,
                metadata=result.get('metadata'),
                target_node_visits=result.get('target_node_visits'),
                cost_function_evaluations=result.get('cost_function_evaluations'),
                embedding_state_mutations=result.get('embedding_state_mutations'),
                overlap_qubit_iterations=result.get('overlap_qubit_iterations'),
            )
        else:
            # For INVALID_OUTPUT from Layer 1, use the specific check failure detail.
            # For other failures (TIMEOUT, CRASH, etc.), use the algorithm's error.
            if status == 'INVALID_OUTPUT' and layer1 is not None and not layer1.passed:
                error_msg = (
                    f"Algorithm claimed success=True, "
                    f"embedding_size={len(raw_embedding)}; "
                    f"Layer 1 [{layer1.check_name}]: {layer1.detail}"
                )
            else:
                error_msg = result.get('error', f"status={status}")
            return EmbeddingResult(
                **fail_base,
                status=status,
                wall_time=result.get('time', 0.0),
                cpu_time=_cpu_elapsed,
                is_valid=False,
                embedding=raw_embedding,  # preserve partial/invalid output for diagnostics
                algorithm_version=algo_version,
                partial=is_partial,
                error=error_msg,
                metadata=result.get('metadata'),
            )

    except Exception as e:
        return EmbeddingResult(
            **fail_base,
            status='CRASH',
            wall_time=timeout,
            algorithm_version=getattr(algo, 'version', 'unknown'),
            error=str(e),
        )


def _reseed_globals(trial_seed: int) -> None:
    """Seed Python and NumPy global RNGs to the per-trial seed.

    Called by the runner immediately before every embed() invocation so that
    algorithms using random/numpy.random without explicit seeding still produce
    deterministic results.  Algorithms that seed their own RNG from kwargs
    are unaffected — this just closes the gap for ones that don't.
    """
    import random
    random.seed(trial_seed)
    try:
        import numpy as np
        np.random.seed(trial_seed % (2**32))
    except ImportError:
        pass


def _derive_seed(root_seed: int, algorithm: str, problem_name: str,
                 topology_name: str, trial: int) -> int:
    """Derive a deterministic per-trial seed via SHA-256.

    Uses the root seed and the full task identity so that:
    - Seeds are independent of execution order — safe for parallel workers.
    - Same (root_seed, task) always produces the same trial seed.
    - SHA-256, not Python hash(), so values are stable across interpreter runs.

    Returns a 32-bit unsigned integer.
    """
    key = f"{root_seed}:{algorithm}:{problem_name}:{topology_name}:{trial}"
    digest = hashlib.sha256(key.encode()).digest()
    return int.from_bytes(digest[:4], 'big')


def _worker_process(task_queue: multiprocessing.Queue,
                    result_queue: multiprocessing.Queue,
                    workers_dir_str: str,
                    batch_id: str,
                    logs_runs_dir_str: str) -> None:
    """Worker process: consume tasks, write JSONL, push display records.

    Pulls (source_graph, target_graph, algo_name, timeout, problem_name,
           topo_name, trial, trial_seed) tuples from task_queue until it
    receives a None sentinel, then exits.

    Workers never print anything — all output is driven by the main process
    reading result_queue. Algorithm stdout/stderr is captured to a per-run
    log file in logs/runs/ for the duration of each embed() call.
    """
    worker_file = Path(workers_dir_str) / f"worker_{os.getpid()}.jsonl"
    logs_runs_dir = Path(logs_runs_dir_str)
    while True:
        task = task_queue.get()
        if task is None:  # sentinel — this worker's share is done
            break
        (source_graph, target_graph, algo_name, timeout,
         problem_name, topo_name, trial, trial_seed) = task

        log_path = run_log_path(logs_runs_dir, algo_name, problem_name, trial, trial_seed)
        _reseed_globals(trial_seed)
        with capture_run(log_path):
            result = benchmark_one(
                source_graph, target_graph, algo_name,
                timeout=timeout, problem_name=problem_name,
                topology_name=topo_name, trial=trial, seed=trial_seed,
            )

        # Append runner diagnostics footer after capture exits (not captured)
        try:
            with open(log_path, 'a') as _lf:
                _lf.write('\n--- RUNNER DIAGNOSTICS ---\n')
                _lf.write(f'status:    {result.status}\n')
                _lf.write(f'success:   {result.success}\n')
                _lf.write(f'is_valid:  {result.is_valid}\n')
                _lf.write(f'wall_time: {result.wall_time:.4f}s\n')
                _lf.write(f'cpu_time:  {result.cpu_time:.4f}s\n')
                if result.error:
                    _lf.write(f'error:     {result.error}\n')
        except OSError:
            pass

        # Full result → JSONL (the durable record)
        with open(worker_file, "a") as wf:
            rec = result.to_jsonl_dict()
            rec['seed'] = trial_seed
            rec['batch_id'] = batch_id
            wf.write(json.dumps(rec) + "\n")

        # Lightweight display record → result queue (main process only prints)
        result_queue.put({
            'algorithm':        algo_name,
            'problem_name':     problem_name,
            'topology_name':    topo_name,
            'trial':            trial,
            'seed':             trial_seed,
            'status':           result.status,
            'success':          result.success,
            'wall_time':        result.wall_time,
            'cpu_time':         result.cpu_time,
            'total_qubits_used': result.total_qubits_used,
            'avg_chain_length': result.avg_chain_length,
            'is_valid':         result.is_valid,
            'error':            result.error,
        })


class EmbeddingBenchmark:
    """Main benchmarking framework — batch runner built on benchmark_one()."""
    
    def __init__(self, target_graph: nx.Graph = None, results_dir: str = "./results"):
        """
        Initialize benchmark.
        
        Args:
            target_graph: Hardware graph. Optional if using topology names
                          in run_full_benchmark(topologies=[...]).
            results_dir: Root directory for results batches
        """
        self.target_graph = target_graph
        self.results_manager = ResultsManager(results_dir)
        self.results: List[EmbeddingResult] = []
        
    def generate_test_problems(self, sizes: List[int] = None, 
                               densities: List[float] = None,
                               instances_per_config: int = 5,
                               graph_selection: str = None) -> List[Tuple[str, nx.Graph]]:
        """Load or generate test problem graphs.
        
        Preferred usage (loads pre-generated graphs from test_graphs/):
            problems = benchmark.generate_test_problems(graph_selection="1-60")
        
        Legacy usage (generates on-the-fly, for backward compatibility):
            problems = benchmark.generate_test_problems(sizes=[4, 8], densities=[0.3])
        
        Args:
            graph_selection: Selection string for pre-generated graphs.
                             E.g., "1-10" (complete), "1-60" (all structured),
                             "*" (everything), "1-60, !5" (exclude graph 5).
                             See test_graphs/REGISTRY.md for the full ID listing.
            sizes: Legacy — list of node sizes for on-the-fly random graphs.
            densities: Legacy — list of densities for on-the-fly random graphs.
            instances_per_config: Legacy — instances per size/density combo.
            
        Returns:
            List of (name, graph) tuples
        """
        # If a selection string is given (or no args at all), load from disk
        if graph_selection is not None or (sizes is None and densities is None):
            selection = graph_selection or "*"
            problems = _load_test_graphs(selection)
            if problems:
                return problems
            # Fall through to on-the-fly generation if no graphs on disk
            print("⚠️  No pre-generated graphs found. Generating on the fly.")
            print("   Run: python generate_test_graphs.py")
        
        # Legacy on-the-fly generation
        sizes = sizes or [4, 6, 8, 10]
        densities = densities or [0.3, 0.5]
        problems = []
        
        for size in sizes:
            for density in densities:
                for instance in range(instances_per_config):
                    G = nx.gnp_random_graph(size, density, seed=instance)
                    name = f"random_n{size}_d{density:.2f}_i{instance}"
                    problems.append((name, G))
        
        # Add structured problems
        for n in [4, 6, 8, 10]:
            problems.append((f"complete_K{n}", nx.complete_graph(n)))
        for m in [3, 4, 5]:
            G = nx.convert_node_labels_to_integers(nx.grid_2d_graph(m, m))
            problems.append((f"grid_{m}x{m}", G))
        for n in [5, 10, 15, 20]:
            problems.append((f"cycle_n{n}", nx.cycle_graph(n)))
        for depth in [3, 4]:
            problems.append((f"tree_d{depth}", nx.balanced_tree(2, depth)))
        
        return problems
    # NOTE: Algorithm implementations live in algorithm_registry.py, not here.
    # Use @register_algorithm("name") to add new algorithms.
    # The benchmark engine discovers them automatically from ALGORITHM_REGISTRY.
    
    def run_full_benchmark(self, problems: List[Tuple[str, nx.Graph]] = None,
                          timeout: float = 60.0,
                          methods: Optional[List[str]] = None,
                          n_trials: int = 1,
                          warmup_trials: int = 0,
                          graph_selection: str = None,
                          topology_name: str = "",
                          topologies: Optional[List[str]] = None,
                          batch_note: str = "",
                          seed: int = 42,
                          n_workers: int = 1,
                          verbose: bool = None):
        """
        Run complete benchmark suite.

        Args:
            problems: List of (name, graph) tuples. If None, uses graph_selection.
            timeout: Timeout per embedding attempt.
            methods: Algorithm names to test (from ALGORITHM_REGISTRY).
            n_trials: Number of measured trials per (algorithm, problem) pair.
            warmup_trials: Warm-up trials to discard before measuring.
            graph_selection: Selection string for pre-generated graphs.
            topology_name: Label for a single topology (backward compat).
            topologies: List of registered topology names for multi-topology runs.
                        Overrides target_graph/topology_name if provided.
            batch_note: Human-readable note describing this run.
            seed: Master seed. Each (algorithm, problem, topology, trial) gets a
                  deterministic 32-bit seed derived via SHA-256 from this master
                  seed and the full task identity, so seeds are independent of
                  execution order and stable across Python versions. Default 42.
            n_workers: Number of parallel worker processes. Default 1 (sequential).
                       Warmup trials are skipped with a warning when n_workers > 1.
            verbose: Print per-trial output. Default: True when n_workers==1,
                     False (progress bar) when n_workers > 1.

        Returns:
            Path to the batch directory where results were saved, or None if no
            graphs matched the selection.  Can be passed directly to
            BenchmarkAnalysis for immediate post-processing::

                batch_dir = bench.run_full_benchmark(...)
                from qeanalysis import BenchmarkAnalysis
                BenchmarkAnalysis(batch_dir).generate_report()
        """
        # Phase 1 integrity check — raises RuntimeError if any graph file has changed
        try:
            verify_manifest()
        except FileNotFoundError:
            pass  # manifest not yet generated; skip check

        if verbose is None:
            verbose = (n_workers == 1)

        # Multi-topology: loop over each topology
        if topologies:
            topo_list = [(name, get_topology(name), name) for name in topologies]
        elif self.target_graph is not None:
            topo_list = [(topology_name, self.target_graph, topology_name)]
        else:
            raise ValueError(
                "No topology specified. Either pass target_graph to __init__ "
                "or use topologies=['chimera_4x4x4', ...] in run_full_benchmark."
            )

        # Resolve problems
        if problems is None:
            selection = graph_selection or "*"
            problems = _load_test_graphs(selection)
            if not problems:
                print(f"⚠️  No graphs matched selection '{selection}'. "
                      f"Run: python generate_test_graphs.py")
                return

        # Resolve methods from registry
        available = list(ALGORITHM_REGISTRY.keys())
        if methods is None:
            methods = available

        valid_methods = [m for m in methods if m in ALGORITHM_REGISTRY]
        missing = set(methods) - set(valid_methods)
        if missing:
            print(f"⚠️  Unknown algorithms (skipped): {missing}")
            print(f"   Available: {available}")

        total_measured = len(problems) * len(valid_methods) * n_trials * len(topo_list)
        total_warmup = len(problems) * len(valid_methods) * warmup_trials * len(topo_list)

        if n_workers > 1 and warmup_trials > 0:
            print(f"⚠️  Warmup trials skipped (not supported with n_workers > 1).")
            total_warmup = 0
            warmup_trials = 0

        total_runs = total_measured + total_warmup
        topo_names_for_config = [t[2] for t in topo_list]

        # Build config and create batch directory NOW — before any runs start —
        # so config.json (with provenance) is on disk even if the run crashes.
        config = {
            'algorithms': valid_methods,
            'graph_selection': graph_selection or 'custom',
            'topologies': topo_names_for_config,
            'n_trials': n_trials,
            'warmup_trials': warmup_trials,
            'timeout': timeout,
            'n_problems': len(problems),
            'n_algorithms': len(valid_methods),
            'n_topologies': len(topo_list),
            'total_measured_runs': total_measured,
        }
        if batch_note:
            config['batch_note'] = batch_note
        batch_dir = self.results_manager.create_batch(config, batch_note=batch_note)
        batch_id = batch_dir.name

        workers_dir = batch_dir / "workers"
        workers_dir.mkdir(exist_ok=True)

        batch_logger = BatchLogger(batch_dir, batch_id)
        batch_logger.setup()
        batch_logger.info(
            f"Batch {batch_id} starting: {total_measured} planned runs, n_workers={n_workers}"
        )

        topo_str = f" × {len(topo_list)} topologies" if len(topo_list) > 1 else ""
        trials_str = f" × {n_trials} trials" if n_trials > 1 else ""
        warmup_str = f" (+ {warmup_trials} warm-up)" if warmup_trials > 0 else ""
        workers_str = f" [{n_workers} workers]" if n_workers > 1 else ""
        print(f"Starting benchmark: {len(problems)} problems × {len(valid_methods)} algorithms{topo_str}{trials_str}{warmup_str} = {total_runs} runs{workers_str}")
        print("=" * 80)
        _batch_start = time.perf_counter()

        # ── Sequential path (n_workers == 1) ───────────────────────────────────
        if n_workers == 1:
            worker_file = workers_dir / f"worker_{os.getpid()}.jsonl"
            current_run = 0

            for _, target_graph, topo_name in topo_list:
                if len(topo_list) > 1:
                    print(f"\n{'='*80}")
                    print(f"Topology: {topo_name} ({target_graph.number_of_nodes()} qubits, "
                          f"{target_graph.number_of_edges()} couplers)")
                    print(f"{'='*80}")

                for problem_name, source_graph in problems:
                    if verbose:
                        print(f"\nProblem: {problem_name} (n={source_graph.number_of_nodes()}, "
                              f"e={source_graph.number_of_edges()})")

                    for algo_name in valid_methods:
                        # Warm-up trials (results discarded) — seed uses negative trial index
                        for w in range(warmup_trials):
                            current_run += 1
                            warmup_seed = _derive_seed(seed, algo_name, problem_name, topo_name, -(w + 1))
                            if verbose:
                                print(f"  [{current_run}/{total_runs}] Warm-up {algo_name} [{w+1}/{warmup_trials}]...", end=" ")
                            _reseed_globals(warmup_seed)
                            benchmark_one(
                                source_graph, target_graph, algo_name,
                                timeout=timeout, problem_name=problem_name,
                                topology_name=topo_name, trial=-1,
                                seed=warmup_seed,
                            )
                            if verbose:
                                print("(discarded)")

                        # Measured trials — trial number is part of seed derivation
                        for trial in range(n_trials):
                            current_run += 1
                            trial_seed = _derive_seed(seed, algo_name, problem_name, topo_name, trial)
                            trial_str = f" [trial {trial+1}/{n_trials}]" if n_trials > 1 else ""
                            topo_tag = f" [{topo_name}]" if len(topo_list) > 1 else ""
                            if verbose:
                                print(f"  [{current_run}/{total_runs}] Running {algo_name}{trial_str}{topo_tag}...", end=" ")

                            log_path = batch_logger.run_log_path(algo_name, problem_name, trial, trial_seed)
                            _reseed_globals(trial_seed)
                            with capture_run(log_path):
                                result = benchmark_one(
                                    source_graph, target_graph, algo_name,
                                    timeout=timeout, problem_name=problem_name,
                                    topology_name=topo_name, trial=trial,
                                    seed=trial_seed,
                                )
                            batch_logger.append_footer(log_path, result)
                            batch_logger.log_run(result, trial_seed)

                            self.results.append(result)
                            with open(worker_file, "a") as wf:
                                rec = result.to_jsonl_dict()
                                rec['seed'] = trial_seed
                                rec['batch_id'] = batch_id
                                wf.write(json.dumps(rec) + "\n")

                            if verbose:
                                if result.success:
                                    valid_str = " ✓valid" if result.is_valid else " ✗invalid"
                                    print(f"✓ wall={result.wall_time:.3f}s "
                                          f"cpu={result.cpu_time:.3f}s, "
                                          f"avg_chain={result.avg_chain_length:.2f}, "
                                          f"qubits={result.total_qubits_used}{valid_str}")
                                else:
                                    print(f"✗ Failed: {result.error}")
                            else:
                                pct = int(40 * current_run / total_runs)
                                bar = '#' * pct + '-' * (40 - pct)
                                elapsed = time.perf_counter() - _batch_start
                                print(f"\r  [{bar}] {current_run}/{total_runs}  {elapsed:.0f}s elapsed", end="", flush=True)

            if not verbose:
                print()  # newline after progress bar

        # ── Parallel path (n_workers > 1) ──────────────────────────────────────
        else:
            task_queue: multiprocessing.Queue = multiprocessing.Queue()
            result_queue: multiprocessing.Queue = multiprocessing.Queue()

            # Build flat task list — seed for each task is fully determined by
            # (root_seed, algorithm, problem, topology, trial), so it is
            # independent of dispatch order and identical for any n_workers.
            tasks = []
            for _, target_graph, topo_name in topo_list:
                for problem_name, source_graph in problems:
                    for algo_name in valid_methods:
                        for trial in range(n_trials):
                            trial_seed = _derive_seed(seed, algo_name, problem_name, topo_name, trial)
                            tasks.append((source_graph, target_graph, algo_name, timeout,
                                          problem_name, topo_name, trial, trial_seed))

            for task in tasks:
                task_queue.put(task)
            for _ in range(n_workers):
                task_queue.put(None)  # one sentinel per worker

            # Spawn worker processes
            worker_procs = []
            for _ in range(n_workers):
                p = multiprocessing.Process(
                    target=_worker_process,
                    args=(task_queue, result_queue, str(workers_dir), batch_id,
                          str(batch_logger.logs_runs_dir)),
                )
                p.start()
                worker_procs.append(p)

            # Display loop — main process is the only one that prints
            completed = 0
            n_tasks = len(tasks)
            while completed < n_tasks:
                display = result_queue.get()
                completed += 1
                batch_logger.log_run_from_display(display)
                if verbose:
                    algo = display['algorithm']
                    prob = display['problem_name']
                    trial = display['trial']
                    if display['success']:
                        print(f"  [{completed}/{n_tasks}] {algo} / {prob} trial {trial}: "
                              f"✓ wall={display['wall_time']:.3f}s "
                              f"avg_chain={display['avg_chain_length']:.2f}")
                    else:
                        print(f"  [{completed}/{n_tasks}] {algo} / {prob} trial {trial}: "
                              f"✗ {display['status']}")
                else:
                    pct = int(40 * completed / n_tasks)
                    bar = '#' * pct + '-' * (40 - pct)
                    elapsed = time.perf_counter() - _batch_start
                    print(f"\r  [{bar}] {completed}/{n_tasks}  {elapsed:.0f}s elapsed", end="", flush=True)

            if not verbose:
                print()  # newline after progress bar

            for p in worker_procs:
                p.join()

            # Reconstruct self.results from JSONL files for save_results()
            valid_fields = set(EmbeddingResult.__dataclass_fields__.keys())
            for jf in sorted(workers_dir.glob("worker_*.jsonl")):
                with open(jf) as fh:
                    for line in fh:
                        line = line.strip()
                        if line:
                            rec = json.loads(line)
                            self.results.append(
                                EmbeddingResult(**{k: v for k, v in rec.items()
                                                   if k in valid_fields})
                            )

        batch_wall_time = time.perf_counter() - _batch_start

        print("\n" + "=" * 80)
        print("Benchmark complete!")

        m, s = divmod(int(batch_wall_time), 60)
        h, m = divmod(m, 60)
        time_str = f"{h}h {m}m {s}s" if h else f"{m}m {s}s" if m else f"{s}s"
        print(f"Total wall time: {batch_wall_time:.1f}s ({time_str})")

        n_success = sum(1 for r in self.results if r.success)
        batch_logger.info(
            f"Batch {batch_id} complete: {n_success}/{len(self.results)} succeeded "
            f"in {batch_wall_time:.1f}s"
        )

        # Persist total wall time in config.json
        config['batch_wall_time'] = round(batch_wall_time, 3)
        config_path = batch_dir / "config.json"
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)

        compile_batch(batch_dir)
        batch_logger.teardown()
        self.results_manager.save_results(self.results, batch_dir, config=config)
        return batch_dir
    
    @property
    def results_dir(self):
        """For backward compatibility with generate_report plot paths."""
        return self.results_manager.results_dir
    
    def generate_report(self):
        """Generate comprehensive analysis and visualizations"""
        if not self.results:
            print("No results to analyze!")
            return
        
        df = pd.DataFrame([r.to_dict() for r in self.results])
        
        # Create visualizations
        self._plot_success_rates(df)
        self._plot_embedding_times(df)
        self._plot_chain_lengths(df)
        self._plot_scalability(df)
        self._generate_summary_statistics(df)
    
    def _plot_success_rates(self, df: pd.DataFrame):
        """Plot success rates by method"""
        fig, ax = plt.subplots(figsize=(10, 6))
        
        success_rates = df.groupby('algorithm')['success'].mean() * 100
        success_rates.plot(kind='bar', ax=ax, color='steelblue')
        
        ax.set_ylabel('Success Rate (%)')
        ax.set_xlabel('Method')
        ax.set_title('Embedding Success Rates by Method')
        ax.set_ylim([0, 105])
        ax.grid(axis='y', alpha=0.3)
        
        plt.tight_layout()
        plt.savefig(self.results_dir / 'success_rates.png', dpi=300)
        print(f"Success rate plot saved to {self.results_dir / 'success_rates.png'}")
        plt.close()
    
    def _plot_embedding_times(self, df: pd.DataFrame):
        """Plot embedding time distributions"""
        fig, ax = plt.subplots(figsize=(12, 6))
        
        successful_df = df[df['success'] == True]
        
        if len(successful_df) > 0:
            successful_df.boxplot(column='embedding_time', by='algorithm', ax=ax)
            ax.set_ylabel('Embedding Time (seconds)')
            ax.set_xlabel('Method')
            ax.set_title('Embedding Time Distribution (Successful Embeddings Only)')
            plt.suptitle('')  # Remove default title
            ax.grid(axis='y', alpha=0.3)
            
            plt.tight_layout()
            plt.savefig(self.results_dir / 'embedding_times.png', dpi=300)
            print(f"Embedding time plot saved to {self.results_dir / 'embedding_times.png'}")
            plt.close()
    
    def _plot_chain_lengths(self, df: pd.DataFrame):
        """Plot chain length comparisons"""
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
        
        successful_df = df[df['success'] == True]
        
        if len(successful_df) > 0:
            # Average chain length
            successful_df.boxplot(column='avg_chain_length', by='algorithm', ax=ax1)
            ax1.set_ylabel('Average Chain Length')
            ax1.set_xlabel('Method')
            ax1.set_title('Average Chain Length Distribution')
            
            # Max chain length
            successful_df.boxplot(column='max_chain_length', by='algorithm', ax=ax2)
            ax2.set_ylabel('Maximum Chain Length')
            ax2.set_xlabel('Method')
            ax2.set_title('Maximum Chain Length Distribution')
            
            plt.suptitle('')
            plt.tight_layout()
            plt.savefig(self.results_dir / 'chain_lengths.png', dpi=300)
            print(f"Chain length plot saved to {self.results_dir / 'chain_lengths.png'}")
            plt.close()
    
    def _plot_scalability(self, df: pd.DataFrame):
        """Plot scalability analysis"""
        fig, ax = plt.subplots(figsize=(12, 6))
        
        successful_df = df[df['success'] == True]
        
        if len(successful_df) > 0:
            for method in successful_df['algorithm'].unique():
                method_df = successful_df[successful_df['algorithm'] == method]
                grouped = method_df.groupby('problem_nodes')['embedding_time'].mean()
                ax.plot(grouped.index, grouped.values, marker='o', label=method, linewidth=2)
            
            ax.set_xlabel('Problem Size (number of nodes)')
            ax.set_ylabel('Average Embedding Time (seconds)')
            ax.set_title('Scalability: Embedding Time vs Problem Size')
            ax.legend()
            ax.grid(alpha=0.3)
            
            plt.tight_layout()
            plt.savefig(self.results_dir / 'scalability.png', dpi=300)
            print(f"Scalability plot saved to {self.results_dir / 'scalability.png'}")
            plt.close()
    
    def _generate_summary_statistics(self, df: pd.DataFrame):
        """Generate and save summary statistics"""
        summary = []
        
        for method in df['algorithm'].unique():
            method_df = df[df['algorithm'] == method]
            successful_df = method_df[method_df['success'] == True]
            
            stats = {
                'Method': method,
                'Total Runs': len(method_df),
                'Successful': len(successful_df),
                'Success Rate (%)': len(successful_df) / len(method_df) * 100,
                'Avg Time (s)': successful_df['embedding_time'].mean() if len(successful_df) > 0 else None,
                'Std Time (s)': successful_df['embedding_time'].std() if len(successful_df) > 0 else None,
                'Avg Chain Length': successful_df['avg_chain_length'].mean() if len(successful_df) > 0 else None,
                'Avg Max Chain': successful_df['max_chain_length'].mean() if len(successful_df) > 0 else None,
                'Avg Qubits Used': successful_df['total_qubits_used'].mean() if len(successful_df) > 0 else None
            }
            summary.append(stats)
        
        summary_df = pd.DataFrame(summary)
        summary_path = self.results_dir / 'summary_statistics.csv'
        summary_df.to_csv(summary_path, index=False)
        
        print(f"\nSummary statistics saved to {summary_path}")
        print("\n" + "=" * 80)
        print("SUMMARY STATISTICS")
        print("=" * 80)
        print(summary_df.to_string(index=False))


def create_chimera_graph(m: int = 4, n: int = 4, t: int = 4) -> nx.Graph:
    """
    Create a Chimera graph (D-Wave topology)
    
    Args:
        m, n: Grid dimensions
        t: Number of qubits per unit cell
        
    Returns:
        NetworkX graph representing Chimera topology
    """
    try:
        import dwave_networkx as dnx
        return dnx.chimera_graph(m, n, t)
    except ImportError:
        print("Warning: dwave_networkx not installed, creating simplified Chimera")
        # Simplified version if dwave_networkx not available
        G = nx.Graph()
        # This is a simplified placeholder - install dwave_networkx for real Chimera
        G.add_nodes_from(range(m * n * t * 2))
        return G


if __name__ == "__main__":
    # Example usage
    print("Minor Embedding Benchmarking Framework")
    print("=" * 80)
    
    # Create target hardware graph (Chimera 4x4)
    target_graph = create_chimera_graph(4, 4, 4)
    print(f"Target graph: Chimera 4×4 with {target_graph.number_of_nodes()} qubits")
    
    # Initialize benchmark
    benchmark = EmbeddingBenchmark(target_graph, results_dir="./benchmark_results")
    
    # Generate test problems
    problems = benchmark.generate_test_problems(
        sizes=[4, 6, 8, 10],
        densities=[0.3, 0.5, 0.7],
        instances_per_config=3
    )
    print(f"Generated {len(problems)} test problems")
    
    # Run benchmark (only minorminer is implemented, others are placeholders)
    benchmark.run_full_benchmark(problems, timeout=30.0, methods=['minorminer'])
    
    # Generate analysis report
    benchmark.generate_report()
