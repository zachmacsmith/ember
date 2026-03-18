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
import queue
import sys
import threading
import time
try:
    import resource as _resource
    _HAS_RESOURCE = True
except ImportError:
    _HAS_RESOURCE = False
import numpy as np
import networkx as nx
import json
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, asdict, field
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

from qebench.registry import ALGORITHM_REGISTRY
from qebench.validation import validate_layer1, validate_layer2
from qebench.graphs import load_test_graphs as _load_test_graphs
from qebench.results import ResultsManager
from qebench.topologies import get_topology
from qebench.compile import compile_batch
from qebench.loggers import BatchLogger, capture_run, run_log_path
from qebench.checkpoint import (
    write_checkpoint, read_checkpoint, delete_checkpoint,
    completed_seeds_from_jsonl, scan_incomplete_runs,
)


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
        _wall_start = time.perf_counter()

        result = algo.embed(source_graph, target_graph, timeout=timeout, **kwargs)

        _wall_elapsed = time.perf_counter() - _wall_start
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
                wall_time=_wall_elapsed,
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
                wall_time=_wall_elapsed,
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
                wall_time=_wall_elapsed,
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


def _keypress_cancel_listener(cancel_flag: threading.Event) -> None:
    """Background thread: set cancel_flag when user presses 'q' + Enter.

    Reads stdin line by line. Daemon thread — exits automatically when the
    main process exits. Only started when stdin is a real TTY so it does not
    block indefinitely when running in a script or CI pipeline.
    """
    try:
        while not cancel_flag.is_set():
            line = sys.stdin.readline()
            if line.strip().lower() == 'q':
                cancel_flag.set()
                break
    except Exception:
        pass


def _strip_truncated_jsonl(filepath: Path) -> None:
    """Remove a potentially truncated last line from a worker JSONL file.

    A worker process killed mid-write may leave an incomplete JSON object as
    the final line. Stripping it ensures compile_batch() does not error on
    malformed input. The corresponding task is in the unfinished list and
    will rerun on resume.
    """
    try:
        content = filepath.read_bytes()
    except OSError:
        return
    if not content:
        return
    last_newline = content.rfind(b'\n')
    if last_newline == -1:
        filepath.write_bytes(b'')
        return
    after = content[last_newline + 1:].strip()
    if after:
        try:
            json.loads(after)
        except json.JSONDecodeError:
            filepath.write_bytes(content[:last_newline + 1])


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
    
    def __init__(self, target_graph: nx.Graph = None, results_dir: str = "./results",
                 unfinished_dir: Optional[str] = None):
        """
        Initialize benchmark.

        Args:
            target_graph: Hardware graph. Optional if using topology names
                          in run_full_benchmark(topologies=[...]).
            results_dir: Output directory for completed batches. Default: ./results
            unfinished_dir: Staging directory for in-progress/cancelled batches.
                            Default: runs_unfinished/ sibling to results_dir.
        """
        self.target_graph = target_graph
        self.results_manager = ResultsManager(results_dir, unfinished_dir=unfinished_dir)
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
                          verbose: bool = None,
                          output_dir: Optional[str] = None,
                          cancel_delay: float = 5.0):
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
            output_dir: Directory for completed batches. Defaults to results/
                        sibling to the runs_unfinished/ staging directory.
            cancel_delay: Seconds to drain results after cancel signal (parallel
                          mode only). Default 5.0.

        Returns:
            Path to the completed batch directory (in output_dir) on success,
            or the staging batch directory if the run was cancelled.
            Returns None if no graphs matched the selection.

        Note:
            # TODO: cancel_trigger callable — pass a callable() -> bool for
            # programmatic cancellation from a parent pipeline. Not yet
            # implemented; currently only interactive 'q' keypress and
            # KeyboardInterrupt (Ctrl+C) are supported.
        """
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
                return None

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
            'seed': seed,
            'n_workers': n_workers,
            'n_problems': len(problems),
            'n_algorithms': len(valid_methods),
            'n_topologies': len(topo_list),
            'total_measured_runs': total_measured,
        }
        # Serialize custom problems into config so they can be reconstructed on resume
        if graph_selection is None or graph_selection == 'custom':
            config['custom_problems'] = [
                {'name': name, 'graph': nx.node_link_data(g, edges="links")}
                for name, g in problems
            ]
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

        # Build flat task list upfront — same order as the nested loops.
        # Enables accurate cancel tracking for both sequential and parallel paths.
        all_tasks = []
        for _, target_graph, topo_name in topo_list:
            for problem_name, source_graph in problems:
                for algo_name in valid_methods:
                    for trial in range(n_trials):
                        trial_seed = _derive_seed(seed, algo_name, problem_name, topo_name, trial)
                        all_tasks.append((source_graph, target_graph, algo_name, timeout,
                                          problem_name, topo_name, trial, trial_seed))

        topo_str = f" × {len(topo_list)} topologies" if len(topo_list) > 1 else ""
        trials_str = f" × {n_trials} trials" if n_trials > 1 else ""
        warmup_str = f" (+ {warmup_trials} warm-up)" if warmup_trials > 0 else ""
        workers_str = f" [{n_workers} workers]" if n_workers > 1 else ""
        print(f"Starting benchmark: {len(problems)} problems × {len(valid_methods)} algorithms"
              f"{topo_str}{trials_str}{warmup_str} = {total_runs} runs{workers_str}")
        print("Press 'q' + Enter to cancel and save a checkpoint.")
        print("=" * 80)
        _batch_start = time.perf_counter()

        # Cancel flag — set by keypress listener or KeyboardInterrupt handler
        _cancel_flag = threading.Event()
        if sys.stdin.isatty():
            _cancel_listener = threading.Thread(
                target=_keypress_cancel_listener, args=(_cancel_flag,), daemon=True
            )
            _cancel_listener.start()

        _cancelled = False

        # ── Sequential path (n_workers == 1) ───────────────────────────────────
        if n_workers == 1:
            worker_file = workers_dir / f"worker_{os.getpid()}.jsonl"
            current_run = 0  # total runs including warmup, for display
            done_count = 0   # completed measured tasks (advances after JSONL write)

            try:
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
                            # Warm-up trials (results discarded)
                            for w in range(warmup_trials):
                                current_run += 1
                                warmup_seed = _derive_seed(seed, algo_name, problem_name,
                                                           topo_name, -(w + 1))
                                if verbose:
                                    print(f"  [{current_run}/{total_runs}] Warm-up "
                                          f"{algo_name} [{w+1}/{warmup_trials}]...", end=" ")
                                _reseed_globals(warmup_seed)
                                benchmark_one(
                                    source_graph, target_graph, algo_name,
                                    timeout=timeout, problem_name=problem_name,
                                    topology_name=topo_name, trial=-1, seed=warmup_seed,
                                )
                                if verbose:
                                    print("(discarded)")

                            # Measured trials
                            for trial in range(n_trials):
                                # Check cancel flag before starting each trial
                                if _cancel_flag.is_set():
                                    raise KeyboardInterrupt

                                current_run += 1
                                trial_seed = _derive_seed(seed, algo_name, problem_name,
                                                          topo_name, trial)
                                trial_str = f" [trial {trial+1}/{n_trials}]" if n_trials > 1 else ""
                                topo_tag = f" [{topo_name}]" if len(topo_list) > 1 else ""
                                if verbose:
                                    print(f"  [{current_run}/{total_runs}] Running "
                                          f"{algo_name}{trial_str}{topo_tag}...", end=" ")

                                log_path = batch_logger.run_log_path(
                                    algo_name, problem_name, trial, trial_seed)
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
                                done_count += 1  # advance only after JSONL write

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
                                    print(f"\r  [{bar}] {current_run}/{total_runs}  "
                                          f"{elapsed:.0f}s elapsed", end="", flush=True)

            except KeyboardInterrupt:
                _cancel_flag.set()
                _cancelled = True

            if not verbose:
                print()  # newline after progress bar

        # ── Parallel path (n_workers > 1) ──────────────────────────────────────
        else:
            task_queue: multiprocessing.Queue = multiprocessing.Queue()
            result_queue: multiprocessing.Queue = multiprocessing.Queue()

            for task in all_tasks:
                task_queue.put(task)
            for _ in range(n_workers):
                task_queue.put(None)  # one sentinel per worker

            worker_procs = []
            for _ in range(n_workers):
                p = multiprocessing.Process(
                    target=_worker_process,
                    args=(task_queue, result_queue, str(workers_dir), batch_id,
                          str(batch_logger.logs_runs_dir)),
                )
                p.start()
                worker_procs.append(p)

            # Display loop — non-blocking with cancel check
            n_tasks = len(all_tasks)
            completed_display = 0
            try:
                while completed_display < n_tasks:
                    if _cancel_flag.is_set():
                        break
                    try:
                        display = result_queue.get(timeout=0.5)
                    except queue.Empty:
                        continue
                    completed_display += 1
                    batch_logger.log_run_from_display(display)
                    if verbose:
                        algo = display['algorithm']
                        prob = display['problem_name']
                        trial = display['trial']
                        if display['success']:
                            print(f"  [{completed_display}/{n_tasks}] {algo} / {prob} "
                                  f"trial {trial}: ✓ wall={display['wall_time']:.3f}s "
                                  f"avg_chain={display['avg_chain_length']:.2f}")
                        else:
                            print(f"  [{completed_display}/{n_tasks}] {algo} / {prob} "
                                  f"trial {trial}: ✗ {display['status']}")
                    else:
                        pct = int(40 * completed_display / n_tasks)
                        bar = '#' * pct + '-' * (40 - pct)
                        elapsed = time.perf_counter() - _batch_start
                        print(f"\r  [{bar}] {completed_display}/{n_tasks}  "
                              f"{elapsed:.0f}s elapsed", end="", flush=True)
            except KeyboardInterrupt:
                _cancel_flag.set()

            if not verbose:
                print()

            if _cancel_flag.is_set():
                _cancelled = True
                # Drain: collect results that arrived during/just after cancel
                _drain_end = time.perf_counter() + cancel_delay
                while time.perf_counter() < _drain_end:
                    try:
                        display = result_queue.get(timeout=0.1)
                        completed_display += 1
                        batch_logger.log_run_from_display(display)
                    except queue.Empty:
                        break
                # Terminate all workers
                for p in worker_procs:
                    p.terminate()
                for p in worker_procs:
                    p.join(timeout=10)
                for p in worker_procs:
                    if p.is_alive():
                        p.kill()
                        p.join()
                # Strip potentially truncated last lines written at termination time
                for jf in workers_dir.glob("worker_*.jsonl"):
                    _strip_truncated_jsonl(jf)
            else:
                for p in worker_procs:
                    p.join()

            # Reconstruct self.results from JSONL files
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
            done_count = len(self.results)

        # ── Handle cancellation ────────────────────────────────────────────────
        if _cancelled:
            if n_workers == 1:
                unfinished = all_tasks[done_count:]
            else:
                completed_seeds = completed_seeds_from_jsonl(batch_dir)
                unfinished = [
                    t for t in all_tasks
                    if (t[2], t[4], t[5], t[7]) not in completed_seeds
                    # index: (algo_name, problem_name, topo_name, trial_seed)
                ]
            write_checkpoint(
                batch_dir,
                unfinished_tasks=[(t[2], t[4], t[5], t[6], t[7]) for t in unfinished],
                total_tasks=len(all_tasks),
                completed_count=len(all_tasks) - len(unfinished),
            )
            batch_logger.teardown()
            n_done = len(all_tasks) - len(unfinished)
            print(f"\nCancelled. {n_done}/{len(all_tasks)} trials complete.")
            print(f"Checkpoint saved. Resume with: load_benchmark()")
            return batch_dir

        # ── Normal completion ──────────────────────────────────────────────────
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
        _out = Path(output_dir) if output_dir else None
        final_dir = self.results_manager.move_to_output(batch_dir, output_dir=_out)
        self.results_manager.save_results(self.results, final_dir, config=config)
        return final_dir


def load_benchmark(batch_id: Optional[str] = None,
                   unfinished_dir: Optional[str] = None,
                   output_dir: Optional[str] = None,
                   n_workers: Optional[int] = None,
                   verbose: bool = None,
                   cancel_delay: float = 5.0) -> Optional[Path]:
    """Resume an incomplete or crashed benchmark run.

    Scans runs_unfinished/ for incomplete batches. With no arguments, lists
    all found runs and prompts for selection. Pass batch_id to skip the prompt.

    Args:
        batch_id: Name of the batch directory to resume (e.g.
                  "batch_2026-03-17_14-22-01"). If None, shows a discovery
                  table and prompts for selection.
        unfinished_dir: Override for the runs_unfinished/ staging directory.
                        Defaults to runs_unfinished/ in the current directory.
        output_dir: Destination for the completed batch. Defaults to results/
                    sibling to unfinished_dir.
        n_workers: Number of parallel worker processes. Defaults to the value
                   stored in the original run's config.json.
        verbose: Per-trial output. Default: True when n_workers==1.
        cancel_delay: Seconds to drain results on cancel (parallel only).

    Returns:
        Path to the completed batch directory, or the staging batch directory
        if the resumed run was cancelled again. None if no runs found or the
        user declined.

    Note:
        load_benchmark() validates batch_id against runs_unfinished/ and raises
        a clear error if the batch does not exist or is already complete.
        When no argument is passed it prints the discovery table and accepts
        a selection by number from input().
    """
    # Resolve staging directory
    _unfinished = Path(unfinished_dir) if unfinished_dir else Path("runs_unfinished")

    incomplete_runs = scan_incomplete_runs(_unfinished)
    if not incomplete_runs:
        print(f"No incomplete runs found in: {_unfinished.resolve()}")
        return None

    # Select batch
    if batch_id is not None:
        matches = [r for r in incomplete_runs if r['batch_id'] == batch_id]
        if not matches:
            raise ValueError(
                f"No incomplete run named '{batch_id}' found in {_unfinished}.\n"
                f"Available: {[r['batch_id'] for r in incomplete_runs]}"
            )
        selected = matches[0]
    elif len(incomplete_runs) == 1:
        selected = incomplete_runs[0]
        print(f"Found 1 incomplete run: {selected['batch_id']}")
        try:
            ans = input("Resume it? [Y/n] ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            return None
        if ans not in ('', 'y', 'yes'):
            return None
    else:
        # Show discovery table
        print("\nIncomplete benchmark runs:")
        print("-" * 72)
        for i, run in enumerate(incomplete_runs, 1):
            cp = run['checkpoint']
            cfg = run['config']
            note = cfg.get('batch_note', '')
            note_str = f'  "{note}"' if note else ''
            if run['has_checkpoint'] and cp:
                done = cp.get('completed_count', '?')
                total = cp.get('total_tasks', '?')
                resumed = cp.get('resume_count', 0)
                cancelled_at = cp.get('cancelled_at', '')[:16].replace('T', ' ')
                progress = f"{done}/{total} trials complete"
                resume_str = f"  resumed {resumed}×" if resumed else ""
                age_str = f"  cancelled {cancelled_at}" if cancelled_at else ""
                print(f"[{i}]  {run['batch_id']}{note_str}")
                print(f"     {progress}{resume_str}{age_str}")
            else:
                jsonl = run['jsonl_lines']
                print(f"[{i}]  {run['batch_id']}{note_str}")
                print(f"     ✗ no checkpoint — crashed or still running  "
                      f"{jsonl} JSONL lines on disk")
        print()

        while True:
            try:
                choice = input("Select run number (or q to cancel): ").strip()
            except (EOFError, KeyboardInterrupt):
                return None
            if choice.lower() == 'q':
                return None
            try:
                idx = int(choice) - 1
                if 0 <= idx < len(incomplete_runs):
                    selected = incomplete_runs[idx]
                    break
                else:
                    print(f"Please enter a number between 1 and {len(incomplete_runs)}.")
            except ValueError:
                print("Invalid input.")

    batch_dir: Path = selected['batch_dir']
    config: dict = selected['config']

    # Reconstruct run parameters from config
    seed = config.get('seed', 42)
    if n_workers is None:
        n_workers = config.get('n_workers', 1)
    timeout = config.get('timeout', 60.0)
    n_trials = config.get('n_trials', 1)
    algorithms = config.get('algorithms', [])
    topo_names = config.get('topologies', [])
    graph_selection = config.get('graph_selection', 'custom')

    if verbose is None:
        verbose = (n_workers == 1)

    # Reconstruct problems
    if 'custom_problems' in config:
        problems = [
            (p['name'], nx.node_link_graph(p['graph'], edges="links"))
            for p in config['custom_problems']
        ]
    else:
        problems = _load_test_graphs(graph_selection)
        if not problems:
            raise ValueError(
                f"No graphs matched selection '{graph_selection}'. "
                f"Cannot resume batch {batch_dir.name}."
            )

    # Reconstruct topology list
    topo_list = [(name, get_topology(name), name) for name in topo_names]
    if not topo_list:
        raise ValueError(f"No topologies found in config for batch {batch_dir.name}.")

    # Validate algorithms are still registered
    missing_algos = [a for a in algorithms if a not in ALGORITHM_REGISTRY]
    if missing_algos:
        raise ValueError(
            f"Algorithms not in registry: {missing_algos}. "
            f"Available: {list(ALGORITHM_REGISTRY.keys())}"
        )

    # Build full task list (same order as original run)
    all_tasks = []
    for _, target_graph, topo_name in topo_list:
        for problem_name, source_graph in problems:
            for algo_name in algorithms:
                for trial in range(n_trials):
                    trial_seed = _derive_seed(seed, algo_name, problem_name, topo_name, trial)
                    all_tasks.append((source_graph, target_graph, algo_name, timeout,
                                      problem_name, topo_name, trial, trial_seed))

    # Determine which tasks remain
    checkpoint = read_checkpoint(batch_dir)
    if checkpoint:
        resume_count = checkpoint.get('resume_count', 0)
        stored_unfinished = checkpoint.get('unfinished_tasks', [])
        unfinished_set = {
            (t['algo_name'], t['problem_name'], t['topo_name'], t['trial'], t['trial_seed'])
            for t in stored_unfinished
        }
        remaining_tasks = [
            t for t in all_tasks
            if (t[2], t[4], t[5], t[6], t[7]) in unfinished_set
        ]
    else:
        # Crashed run — derive from JSONL
        resume_count = 0
        completed_seeds = completed_seeds_from_jsonl(batch_dir)
        remaining_tasks = [
            t for t in all_tasks
            if (t[2], t[4], t[5], t[7]) not in completed_seeds
        ]

    n_remaining = len(remaining_tasks)
    n_already_done = len(all_tasks) - n_remaining

    print(f"\nResuming {batch_dir.name}")
    note = config.get('batch_note', '')
    if note:
        print(f"  Note: {note}")
    print(f"  {n_already_done}/{len(all_tasks)} trials already complete, "
          f"{n_remaining} remaining")
    print(f"  n_workers={n_workers}, timeout={timeout}s")

    # If all tasks already done, just compile and move
    if n_remaining == 0:
        print("All tasks already complete. Compiling...")
        compile_batch(batch_dir)
        delete_checkpoint(batch_dir)
        _results_root = Path(output_dir) if output_dir else (_unfinished.parent / "results")
        _rm = ResultsManager(str(_results_root), unfinished_dir=str(_unfinished))
        final_dir = _rm.move_to_output(batch_dir)
        print(f"Batch moved to: {final_dir}")
        return final_dir

    # Increment resume_count in checkpoint at start of resume
    if checkpoint:
        checkpoint['resume_count'] = resume_count + 1
        cp_path = batch_dir / 'checkpoint.json'
        with open(cp_path, 'w') as f:
            json.dump(checkpoint, f, indent=2)

    batch_id = batch_dir.name
    workers_dir = batch_dir / "workers"
    workers_dir.mkdir(exist_ok=True)

    batch_logger = BatchLogger(batch_dir, batch_id)
    batch_logger.setup()
    batch_logger.info(
        f"Resuming {batch_id}: {n_remaining} tasks remaining "
        f"(resume #{resume_count + 1})"
    )

    print("Press 'q' + Enter to cancel and save a checkpoint.")
    print("=" * 80)
    _batch_start = time.perf_counter()

    _cancel_flag = threading.Event()
    if sys.stdin.isatty():
        _cancel_listener = threading.Thread(
            target=_keypress_cancel_listener, args=(_cancel_flag,), daemon=True
        )
        _cancel_listener.start()

    _cancelled = False
    results = []
    done_count = 0

    # ── Sequential path ────────────────────────────────────────────────────────
    if n_workers == 1:
        worker_file = workers_dir / f"worker_{os.getpid()}.jsonl"
        try:
            for task_idx, task in enumerate(remaining_tasks):
                if _cancel_flag.is_set():
                    raise KeyboardInterrupt

                (source_graph, target_graph, algo_name, task_timeout,
                 problem_name, topo_name, trial, trial_seed) = task

                if verbose:
                    print(f"  [{task_idx+1}/{n_remaining}] Resuming {algo_name} / "
                          f"{problem_name} trial {trial}...", end=" ")

                log_path = batch_logger.run_log_path(algo_name, problem_name, trial, trial_seed)
                _reseed_globals(trial_seed)
                with capture_run(log_path):
                    result = benchmark_one(
                        source_graph, target_graph, algo_name,
                        timeout=task_timeout, problem_name=problem_name,
                        topology_name=topo_name, trial=trial, seed=trial_seed,
                    )
                batch_logger.append_footer(log_path, result)
                batch_logger.log_run(result, trial_seed)

                results.append(result)
                with open(worker_file, "a") as wf:
                    rec = result.to_jsonl_dict()
                    rec['seed'] = trial_seed
                    rec['batch_id'] = batch_id
                    wf.write(json.dumps(rec) + "\n")
                done_count += 1

                if verbose:
                    if result.success:
                        print(f"✓ wall={result.wall_time:.3f}s "
                              f"avg_chain={result.avg_chain_length:.2f}")
                    else:
                        print(f"✗ {result.error}")
                else:
                    pct = int(40 * done_count / n_remaining)
                    bar = '#' * pct + '-' * (40 - pct)
                    elapsed = time.perf_counter() - _batch_start
                    print(f"\r  [{bar}] {done_count}/{n_remaining}  "
                          f"{elapsed:.0f}s elapsed", end="", flush=True)

        except KeyboardInterrupt:
            _cancel_flag.set()
            _cancelled = True

        if not verbose:
            print()

    # ── Parallel path ──────────────────────────────────────────────────────────
    else:
        task_queue: multiprocessing.Queue = multiprocessing.Queue()
        result_queue: multiprocessing.Queue = multiprocessing.Queue()

        for task in remaining_tasks:
            task_queue.put(task)
        for _ in range(n_workers):
            task_queue.put(None)

        worker_procs = []
        for _ in range(n_workers):
            p = multiprocessing.Process(
                target=_worker_process,
                args=(task_queue, result_queue, str(workers_dir), batch_id,
                      str(batch_logger.logs_runs_dir)),
            )
            p.start()
            worker_procs.append(p)

        completed_display = 0
        try:
            while completed_display < n_remaining:
                if _cancel_flag.is_set():
                    break
                try:
                    display = result_queue.get(timeout=0.5)
                except queue.Empty:
                    continue
                completed_display += 1
                batch_logger.log_run_from_display(display)
                if verbose:
                    algo = display['algorithm']
                    prob = display['problem_name']
                    trial = display['trial']
                    if display['success']:
                        print(f"  [{completed_display}/{n_remaining}] {algo} / {prob} "
                              f"trial {trial}: ✓ wall={display['wall_time']:.3f}s "
                              f"avg_chain={display['avg_chain_length']:.2f}")
                    else:
                        print(f"  [{completed_display}/{n_remaining}] {algo} / {prob} "
                              f"trial {trial}: ✗ {display['status']}")
                else:
                    pct = int(40 * completed_display / n_remaining)
                    bar = '#' * pct + '-' * (40 - pct)
                    elapsed = time.perf_counter() - _batch_start
                    print(f"\r  [{bar}] {completed_display}/{n_remaining}  "
                          f"{elapsed:.0f}s elapsed", end="", flush=True)
        except KeyboardInterrupt:
            _cancel_flag.set()

        if not verbose:
            print()

        if _cancel_flag.is_set():
            _cancelled = True
            _drain_end = time.perf_counter() + cancel_delay
            while time.perf_counter() < _drain_end:
                try:
                    display = result_queue.get(timeout=0.1)
                    completed_display += 1
                    batch_logger.log_run_from_display(display)
                except queue.Empty:
                    break
            for p in worker_procs:
                p.terminate()
            for p in worker_procs:
                p.join(timeout=10)
            for p in worker_procs:
                if p.is_alive():
                    p.kill()
                    p.join()
            for jf in workers_dir.glob("worker_*.jsonl"):
                _strip_truncated_jsonl(jf)
        else:
            for p in worker_procs:
                p.join()

        # Reconstruct results from all JSONL files (original + resumed)
        valid_fields = set(EmbeddingResult.__dataclass_fields__.keys())
        for jf in sorted(workers_dir.glob("worker_*.jsonl")):
            with open(jf) as fh:
                for line in fh:
                    line = line.strip()
                    if line:
                        rec = json.loads(line)
                        results.append(
                            EmbeddingResult(**{k: v for k, v in rec.items()
                                               if k in valid_fields})
                        )
        done_count = len(results)

    # ── Handle cancel during resume ────────────────────────────────────────────
    if _cancelled:
        if n_workers == 1:
            new_unfinished = remaining_tasks[done_count:]
        else:
            completed_seeds = completed_seeds_from_jsonl(batch_dir)
            new_unfinished = [
                t for t in all_tasks
                if (t[2], t[4], t[5], t[7]) not in completed_seeds
            ]
        write_checkpoint(
            batch_dir,
            unfinished_tasks=[(t[2], t[4], t[5], t[6], t[7]) for t in new_unfinished],
            total_tasks=len(all_tasks),
            completed_count=len(all_tasks) - len(new_unfinished),
            resume_count=resume_count + 1,
        )
        batch_logger.teardown()
        n_done = len(all_tasks) - len(new_unfinished)
        print(f"\nCancelled. {n_done}/{len(all_tasks)} trials complete.")
        print(f"Checkpoint saved. Resume again with: load_benchmark()")
        return batch_dir

    # ── Normal completion of resume ────────────────────────────────────────────
    batch_wall_time = time.perf_counter() - _batch_start

    # Read all results from JSONL (original + resumed) for save_results
    all_results = []
    valid_fields = set(EmbeddingResult.__dataclass_fields__.keys())
    for jf in sorted(workers_dir.glob("worker_*.jsonl")):
        with open(jf) as fh:
            for line in fh:
                line = line.strip()
                if line:
                    rec = json.loads(line)
                    all_results.append(
                        EmbeddingResult(**{k: v for k, v in rec.items()
                                           if k in valid_fields})
                    )

    n_success = sum(1 for r in all_results if r.success)
    batch_logger.info(
        f"Resume of {batch_id} complete: {n_success}/{len(all_results)} succeeded "
        f"in {batch_wall_time:.1f}s"
    )

    m, s = divmod(int(batch_wall_time), 60)
    h, m = divmod(m, 60)
    time_str = f"{h}h {m}m {s}s" if h else f"{m}m {s}s" if m else f"{s}s"
    print(f"\nResume complete! Total wall time: {batch_wall_time:.1f}s ({time_str})")

    compile_batch(batch_dir)
    delete_checkpoint(batch_dir)
    batch_logger.teardown()

    _results_root = Path(output_dir) if output_dir else (_unfinished.parent / "results")
    _rm = ResultsManager(str(_results_root), unfinished_dir=str(_unfinished))
    final_dir = _rm.move_to_output(batch_dir)
    _rm.save_results(all_results, final_dir, config=config)
    return final_dir


def delete_benchmark(batch_id: Optional[str] = None,
                     unfinished_dir: Optional[str] = None,
                     force: bool = False) -> bool:
    """Delete an incomplete benchmark run from runs_unfinished/.

    Only operates on runs_unfinished/. Completed runs in the output directory
    are never touched — use filesystem operations to remove those.

    Shows a summary (progress, age, disk size) before deleting and requires
    explicit confirmation unless force=True.

    Args:
        batch_id: Name of the batch directory to delete (e.g.
                  "batch_2026-03-17_14-22-01"). If None, shows a discovery
                  table and prompts for selection.
        unfinished_dir: Override for the runs_unfinished/ staging directory.
                        Defaults to runs_unfinished/ in the current directory.
        force: Skip interactive confirmation. For programmatic/pipeline use.
               Default False.

    Returns:
        True if the batch was deleted, False if aborted by the user.

    Note:
        # TODO: partial-compile path — offer to compile finished JSONL data and
        # move it to the output directory as a partial result flagged with
        # "completed": false in config.json. Deferred; add if large partially-
        # completed runs prove valuable enough to preserve.

        When EMBER gets a CLI entry point, this becomes:
            ember delete [batch_id]
    """
    import shutil
    from datetime import datetime, timezone

    _unfinished = Path(unfinished_dir) if unfinished_dir else Path("runs_unfinished")

    incomplete_runs = scan_incomplete_runs(_unfinished)
    if not incomplete_runs:
        print(f"No incomplete runs found in: {_unfinished.resolve()}")
        return False

    # Select batch
    if batch_id is not None:
        matches = [r for r in incomplete_runs if r['batch_id'] == batch_id]
        if not matches:
            raise ValueError(
                f"No incomplete run named '{batch_id}' found in {_unfinished}.\n"
                f"Available: {[r['batch_id'] for r in incomplete_runs]}"
            )
        selected = matches[0]
    elif len(incomplete_runs) == 1:
        selected = incomplete_runs[0]
    else:
        print("\nIncomplete benchmark runs:")
        print("-" * 72)
        for i, run in enumerate(incomplete_runs, 1):
            cp = run['checkpoint']
            cfg = run['config']
            note = cfg.get('batch_note', '')
            note_str = f'  "{note}"' if note else ''
            if run['has_checkpoint'] and cp:
                done = cp.get('completed_count', '?')
                total = cp.get('total_tasks', '?')
                print(f"[{i}]  {run['batch_id']}{note_str}")
                print(f"     {done}/{total} trials complete")
            else:
                print(f"[{i}]  {run['batch_id']}{note_str}")
                print(f"     ✗ no checkpoint — crashed or still running  "
                      f"{run['jsonl_lines']} JSONL lines on disk")
        print()
        while True:
            try:
                choice = input("Select run number to delete (or q to cancel): ").strip()
            except (EOFError, KeyboardInterrupt):
                return False
            if choice.lower() == 'q':
                return False
            try:
                idx = int(choice) - 1
                if 0 <= idx < len(incomplete_runs):
                    selected = incomplete_runs[idx]
                    break
                else:
                    print(f"Please enter a number between 1 and {len(incomplete_runs)}.")
            except ValueError:
                print("Invalid input.")

    batch_dir: Path = selected['batch_dir']
    config: dict = selected['config']
    cp = selected['checkpoint']

    # Compute disk size
    disk_bytes = sum(f.stat().st_size for f in batch_dir.rglob('*') if f.is_file())
    if disk_bytes >= 1024 ** 3:
        size_str = f"{disk_bytes / 1024**3:.1f}GB"
    elif disk_bytes >= 1024 ** 2:
        size_str = f"{disk_bytes / 1024**2:.0f}MB"
    elif disk_bytes >= 1024:
        size_str = f"{disk_bytes / 1024:.0f}KB"
    else:
        size_str = f"{disk_bytes}B"

    # Build summary
    note = config.get('batch_note', '')
    note_str = f'  "{note}"' if note else ''

    if selected['has_checkpoint'] and cp:
        done = cp.get('completed_count', '?')
        total = cp.get('total_tasks', '?')
        cancelled_at = cp.get('cancelled_at', '')
        age_str = ''
        if cancelled_at:
            try:
                cancelled_dt = datetime.fromisoformat(cancelled_at)
                delta = datetime.now(timezone.utc) - cancelled_dt
                days, rem = divmod(delta.total_seconds(), 86400)
                hours, rem = divmod(rem, 3600)
                mins = rem // 60
                if days >= 1:
                    age_str = f"cancelled {int(days)}d ago"
                elif hours >= 1:
                    age_str = f"cancelled {int(hours)}h ago"
                else:
                    age_str = f"cancelled {max(1, int(mins))}m ago"
            except Exception:
                pass
        done_fmt = f"{done:,}" if isinstance(done, int) else str(done)
        total_fmt = f"{total:,}" if isinstance(total, int) else str(total)
        summary_parts = [f"{done_fmt}/{total_fmt} complete"]
        if age_str:
            summary_parts.append(age_str)
        summary_parts.append(size_str)
    else:
        summary_parts = [
            f"crashed or still running",
            f"{selected['jsonl_lines']} JSONL lines",
            size_str,
        ]

    summary = ", ".join(summary_parts)

    print(f"\nBatch: {batch_dir.name}{note_str}")
    print(f"  {summary}")

    if not force:
        prompt = f"\nDelete {batch_dir.name} ({summary})? [y/N] "
        try:
            ans = input(prompt).strip().lower()
        except (EOFError, KeyboardInterrupt):
            print("\nAborted.")
            return False
        if ans not in ('y', 'yes'):
            print("Aborted.")
            return False

    shutil.rmtree(batch_dir)
    print(f"Deleted {batch_dir.name}.")
    return True

