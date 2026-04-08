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
import select
import statistics
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
from ember_qc.registry import ALGORITHM_REGISTRY
from ember_qc.validation import validate_layer1, validate_layer2
from ember_qc.faults import simulate_faults
from ember_qc.load_graphs import load_test_graphs as _load_test_graphs
from ember_qc.results import ResultsManager
from ember_qc.topologies import get_topology
from ember_qc.compile import compile_batch
from ember_qc.loggers import BatchLogger, capture_run, run_log_path
from ember_qc.checkpoint import (
    write_checkpoint, read_checkpoint, delete_checkpoint,
    completed_seeds_from_jsonl, scan_incomplete_runs,
)


@dataclass
class EmbeddingResult:
    """Result from a single embedding attempt."""
    # Identification
    algorithm: str
    graph_name: str         # human-readable label (may duplicate across graphs)
    graph_id: int           # manifest ID (unique); 0 for custom/non-manifest graphs
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
        chain_set = set(chain)
        seen: set = set()
        for qubit in chain:
            seen.add(qubit)
            for neighbor in target_graph.neighbors(qubit):
                if neighbor in chain_set and neighbor not in seen:
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
                  graph_name: str = "",
                  graph_id: int = 0,
                  topology_name: str = "",
                  trial: int = 0,
                  **kwargs) -> EmbeddingResult:
    """Run a single embedding benchmark. The atomic unit of the framework.

    Args:
        source_graph: Problem graph to embed.
        target_graph: Hardware topology graph.
        algorithm: Name of registered algorithm (e.g., "minorminer").
        timeout: Max seconds for this attempt.
        graph_name: Human-readable label for this problem (e.g., "K10").
        graph_id: Manifest integer ID; 0 for custom/non-manifest graphs.
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
        graph_name=graph_name,
        graph_id=graph_id,
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
                wall_time=_wall_elapsed,
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
            _emb_size = len(result.get('embedding') or {})
            _outcome = f"returned embedding (size={_emb_size})" if _emb_size else "returned empty embedding"
            return EmbeddingResult(
                **fail_base,
                status='INVALID_OUTPUT',
                wall_time=_wall_elapsed,
                cpu_time=_cpu_elapsed,
                algorithm_version=algo_version,
                error=(
                    f"{_outcome}; "
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
                graph_name=graph_name,
                graph_id=graph_id,
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
                    f"returned embedding (size={len(raw_embedding)}); "
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


def _derive_seed(root_seed: int, algorithm: str, graph_id: int,
                 topology_name: str, trial: int) -> int:
    """Derive a deterministic per-trial seed via SHA-256.

    Uses the root seed and the full task identity so that:
    - Seeds are independent of execution order — safe for parallel workers.
    - Same (root_seed, task) always produces the same trial seed.
    - SHA-256, not Python hash(), so values are stable across interpreter runs.

    Returns a 32-bit unsigned integer.
    """
    key = f"{root_seed}:{algorithm}:{graph_id}:{topology_name}:{trial}"
    digest = hashlib.sha256(key.encode()).digest()
    return int.from_bytes(digest[:4], 'big')


def _keypress_cancel_listener(cancel_flag: threading.Event) -> None:
    """Background thread: set cancel_flag when user presses 'q' + Enter.

    Polls stdin with a 0.5s timeout so it checks cancel_flag between reads
    and exits promptly when the run completes (caller sets cancel_flag).
    Only started when stdin is a real TTY.
    """
    try:
        while not cancel_flag.is_set():
            ready, _, _ = select.select([sys.stdin], [], [], 0.5)
            if ready:
                line = sys.stdin.readline()
                if line.strip().lower() == 'q':
                    cancel_flag.set()
                    break
    except Exception:
        pass


def _algo_topo_compatible(algo_name: str, topo_name: str) -> bool:
    """Return True if algo_name supports topo_name (or has no restriction).

    Matching is prefix-based: supported_topologies=['chimera'] matches
    'chimera_4x4x4', 'chimera_16x16x4', etc.
    """
    algo = ALGORITHM_REGISTRY.get(algo_name)
    if algo is None:
        return True  # unknown algo — let it fail naturally later
    supported = getattr(algo, 'supported_topologies', None)
    if supported is None:
        return True
    topo_lower = topo_name.lower()
    return any(topo_lower.startswith(s.lower()) for s in supported)


def _graph_topo_compatible(graph_id: int, source_graph, target_graph,
                           topo_name: str) -> bool:
    """Return True if source_graph is potentially embeddable in target_graph.

    Checks the graph's manifest topology list (prefix match) if the graph is
    in the library.  Falls back to a size check (nodes and edges must both fit)
    for custom graphs (graph_id == 0) not present in the manifest.
    """
    if graph_id:
        try:
            from ember_qc.load_graphs import _manifest_by_id
            entry = _manifest_by_id().get(graph_id)
            if entry is not None:
                compatible_topos = entry.get('topologies', [])
                if compatible_topos:
                    topo_lower = topo_name.lower()
                    return any(topo_lower.startswith(t.lower()) for t in compatible_topos)
        except Exception:
            pass
    # Custom graph or no topology annotation: size is a necessary condition
    return (source_graph.number_of_nodes() <= target_graph.number_of_nodes() and
            source_graph.number_of_edges() <= target_graph.number_of_edges())


def _print_warn_summary(warn_registry: dict, log_dir: Path) -> None:
    """Print the end-of-run warning summary block. No-op if registry is empty."""
    if not warn_registry:
        return

    # Count total warning events across all categories
    total = 0
    if 'TOPOLOGY_INCOMPATIBLE' in warn_registry:
        total += len(warn_registry['TOPOLOGY_INCOMPATIBLE']['entries'])
    if 'INVALID_OUTPUT' in warn_registry:
        total += sum(warn_registry['INVALID_OUTPUT'].values())
    if 'CRASH' in warn_registry:
        total += sum(v['count'] for v in warn_registry['CRASH'].values())
    if 'TIMING_OUTLIER' in warn_registry:
        total += sum(warn_registry['TIMING_OUTLIER'].values())
    if 'ALL_ALGORITHMS_FAILED' in warn_registry:
        total += len(warn_registry['ALL_ALGORITHMS_FAILED'])
    if 'TOPOLOGY_DISCONNECTED' in warn_registry:
        total += len(warn_registry['TOPOLOGY_DISCONNECTED'])
    if total == 0:
        return

    print(f"\nWarnings ({total} total):")

    if 'TOPOLOGY_INCOMPATIBLE' in warn_registry:
        entry = warn_registry['TOPOLOGY_INCOMPATIBLE']
        by_algo: dict = {}
        for algo, topo, _ in entry['entries']:
            by_algo.setdefault(algo, []).append(topo)
        for algo, topos in by_algo.items():
            print(f"   TOPOLOGY_INCOMPATIBLE  {algo} incompatible with {', '.join(topos)}")
        print(f"                          {entry['total_skipped']:,} trials skipped before run.")

    if 'INVALID_OUTPUT' in warn_registry:
        counts = warn_registry['INVALID_OUTPUT']
        total_inv = sum(counts.values())
        detail = "  ".join(f"{a}: {n}" for a, n in counts.items())
        print(f"   INVALID_OUTPUT         {total_inv} trials had invalid embeddings.")
        print(f"                          {detail}")

    if 'CRASH' in warn_registry:
        crashes = warn_registry['CRASH']
        total_crash = sum(v['count'] for v in crashes.values())
        first_err = next(iter(crashes.values()))['first_error']
        detail = "  ".join(f"{a}: {v['count']}" for a, v in crashes.items())
        err_suffix = f'  (first error: "{first_err}")' if first_err else ""
        print(f"   CRASH                  {total_crash} trials raised unhandled exceptions.")
        print(f"                          {detail}{err_suffix}")

    if 'TIMING_OUTLIER' in warn_registry:
        outliers = warn_registry['TIMING_OUTLIER']
        total_out = sum(outliers.values())
        detail = "  ".join(f"{a} on {t}: {n}" for (a, t), n in outliers.items())
        print(f"   TIMING_OUTLIER         {total_out} runs exceeded 10× median wall time.")
        print(f"                          {detail}")

    if 'ALL_ALGORITHMS_FAILED' in warn_registry:
        failed = warn_registry['ALL_ALGORITHMS_FAILED']
        shown = ', '.join(failed[:5])
        ellipsis = '...' if len(failed) > 5 else ''
        print(f"   ALL_ALGORITHMS_FAILED  {len(failed)} problem(s) had no successful embedding.")
        print(f"                          {shown}{ellipsis}")

    if 'TOPOLOGY_DISCONNECTED' in warn_registry:
        disc = warn_registry['TOPOLOGY_DISCONNECTED']
        print(f"   TOPOLOGY_DISCONNECTED  Fault simulation produced a disconnected topology.")
        for tn, n_comp in disc.items():
            print(f"                          {tn}: {n_comp} connected components after fault removal.")

    print(f"\nFull warning details: {log_dir.resolve()}")


@dataclass
class ExecutionResult:
    """Return value from _execute_tasks().

    The caller uses this to write checkpoints, accumulate wall time,
    and print the end-of-run warning summary.
    """
    warning_registry: dict
    unfinished_tasks: list    # empty on clean completion
    session_elapsed: float    # wall time for this session only
    completed_count: int
    cancelled: bool


def _load_results_from_jsonl(workers_dir: Path) -> List[EmbeddingResult]:
    """Reconstruct EmbeddingResult objects from all worker JSONL files.

    Called after _execute_tasks() returns — workers are terminated by then,
    so JSONL files are stable. Works for both sequential (single worker file)
    and parallel (multiple worker files) paths.
    """
    valid_fields = set(EmbeddingResult.__dataclass_fields__.keys())
    results: List[EmbeddingResult] = []
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
    return results


def _compute_postrun_warnings(results: List[EmbeddingResult]) -> dict:
    """Compute TIMING_OUTLIER and ALL_ALGORITHMS_FAILED from a completed result list.

    Called by both run_full_benchmark and load_benchmark after reading results
    from JSONL. Returns a partial warning registry dict to be merged into the
    registry returned by _execute_tasks().
    """
    warn_additions: dict = {}

    # TIMING_OUTLIER: (algo, topo) pairs with any trial > 10× median wall time
    _times_by_key: dict = {}
    for r in results:
        if r.success:
            _times_by_key.setdefault((r.algorithm, r.topology_name), []).append(r.wall_time)
    _outlier_counts: dict = {}
    for (algo, topo), times in _times_by_key.items():
        if len(times) >= 2:
            med = statistics.median(times)
            n_out = sum(1 for t in times if t > 10 * med)
            if n_out:
                _outlier_counts[(algo, topo)] = n_out
    if _outlier_counts:
        warn_additions['TIMING_OUTLIER'] = _outlier_counts

    # ALL_ALGORITHMS_FAILED: (problem, topo) pairs with no successful embedding
    _prob_topo_seen: set = set()
    _prob_topo_success: set = set()
    for r in results:
        _prob_topo_seen.add((r.graph_name, r.topology_name))
        if r.success:
            _prob_topo_success.add((r.graph_name, r.topology_name))
    _all_failed = sorted(
        (p, t) for (p, t) in _prob_topo_seen if (p, t) not in _prob_topo_success
    )
    if _all_failed:
        _n_topos = len(set(t for _, t in _prob_topo_seen))
        if _n_topos > 1:
            warn_additions['ALL_ALGORITHMS_FAILED'] = [f"{p} [{t}]" for p, t in _all_failed]
        else:
            warn_additions['ALL_ALGORITHMS_FAILED'] = [p for p, _ in _all_failed]

    return warn_additions


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


def _execute_tasks(
    tasks: list,
    batch_dir: Path,
    batch_logger: 'BatchLogger',
    n_workers: int,
    verbose: bool,
    timeout: float,
    cancel_trigger=None,
    elapsed_offset: float = 0.0,
    cancel_delay: float = 5.0,
    completed_offset: int = 0,
    total_tasks: int = 0,
) -> ExecutionResult:
    """Execute a flat list of measured tasks — the shared run loop for all paths.

    Owns: sequential/parallel execution, progress reporting, warning aggregation,
    JSONL writing, cancel handling, and worker lifecycle.

    Does NOT own: batch directory creation, config.json writing, warmup trials,
    topology compatibility checking, compile_batch, checkpoint writing, or
    self.results population. Those belong to the caller.

    Task tuple format: (source_graph, target_graph, algo_name, graph_id,
                        graph_name, topo_name, trial, trial_seed)
    timeout is uniform across all tasks and passed as a top-level parameter.

    Args:
        tasks:          Flat list of fully-determined task tuples (measured only).
        batch_dir:      Batch directory, already exists on disk.
        batch_logger:   Already initialised by caller.
        n_workers:      1 = sequential, >1 = parallel worker processes.
        verbose:        True = per-trial output; False = progress bar.
        timeout:        Seconds allowed per embed() call (uniform across tasks).
        cancel_trigger: Optional callable() -> bool polled between trials.
                        None = 'q' keypress listener only.
        elapsed_offset: Accumulated wall time from previous sessions, added to
                        progress bar display so resumed runs show total elapsed time.
        cancel_delay:   Seconds to drain result queue after cancel (parallel only).

    Returns:
        ExecutionResult with warning_registry, unfinished_tasks, session_elapsed,
        completed_count, and cancelled flag. Caller reads results from JSONL.
    """
    batch_id = batch_dir.name
    workers_dir = batch_dir / "workers"
    workers_dir.mkdir(exist_ok=True)

    _warn_registry: dict = {}
    _start = time.perf_counter()
    _cancelled = False
    n_tasks = len(tasks)
    # For display: show progress relative to the full batch (including already-done tasks)
    _display_total = total_tasks if total_tasks > n_tasks else n_tasks
    _display_offset = completed_offset  # tasks already done before this session

    def _bar(done: int) -> str:
        """Render a progress bar relative to the full batch."""
        display_done = _display_offset + done
        pct = int(40 * display_done / max(_display_total, 1))
        bar = '#' * pct + '-' * (40 - pct)
        return f"[{bar}] {display_done}/{_display_total}"

    # Cancel detection — keypress listener or caller-supplied trigger
    _cancel_flag = threading.Event()
    if cancel_trigger is None and sys.stdin.isatty():
        _cancel_listener = threading.Thread(
            target=_keypress_cancel_listener, args=(_cancel_flag,), daemon=True
        )
        _cancel_listener.start()

    def _is_cancelled() -> bool:
        return _cancel_flag.is_set() or (cancel_trigger is not None and cancel_trigger())

    # ── Sequential path (n_workers == 1) ───────────────────────────────────────
    if n_workers == 1:
        worker_file = workers_dir / f"worker_{os.getpid()}.jsonl"
        done_count = 0
        prev_topo: Optional[str] = None
        prev_prob: Optional[str] = None
        if not verbose:
            # Print initial bar so user sees state immediately (before any trial completes)
            print(f"\r  {_bar(0)}  {elapsed_offset:.0f}s elapsed", end="", flush=True)

        try:
            for task in tasks:
                if _is_cancelled():
                    raise KeyboardInterrupt

                source_graph, target_graph, algo_name, graph_id, graph_name, topo_name, trial, trial_seed = task

                # Transition detection: print topo/problem headers in verbose mode
                if verbose:
                    if topo_name != prev_topo:
                        print(f"\n{'='*80}")
                        print(f"Topology: {topo_name} ({target_graph.number_of_nodes()} qubits, "
                              f"{target_graph.number_of_edges()} couplers)")
                        print(f"{'='*80}")
                        prev_topo = topo_name
                        prev_prob = None
                    if graph_name != prev_prob:
                        print(f"\nProblem: {graph_name} "
                              f"(id={graph_id}, n={source_graph.number_of_nodes()}, "
                              f"e={source_graph.number_of_edges()})")
                        prev_prob = graph_name
                    print(f"  [{done_count+1}/{n_tasks}] Running {algo_name}...", end=" ")

                log_path = batch_logger.run_log_path(algo_name, graph_name, trial, trial_seed)
                _reseed_globals(trial_seed)
                with capture_run(log_path):
                    result = benchmark_one(
                        source_graph, target_graph, algo_name,
                        timeout=timeout, graph_name=graph_name, graph_id=graph_id,
                        topology_name=topo_name, trial=trial, seed=trial_seed,
                    )
                batch_logger.append_footer(log_path, result)
                batch_logger.log_run(result, trial_seed)

                if result.status == 'INVALID_OUTPUT':
                    _inv = _warn_registry.setdefault('INVALID_OUTPUT', {})
                    _inv[result.algorithm] = _inv.get(result.algorithm, 0) + 1
                elif result.status == 'CRASH':
                    _cr = _warn_registry.setdefault('CRASH', {})
                    if result.algorithm not in _cr:
                        _cr[result.algorithm] = {'count': 0, 'first_error': result.error}
                    _cr[result.algorithm]['count'] += 1

                with open(worker_file, "a") as wf:
                    rec = result.to_jsonl_dict()
                    rec['seed'] = trial_seed
                    rec['batch_id'] = batch_id
                    wf.write(json.dumps(rec) + "\n")
                done_count += 1  # advance only after JSONL write

                if verbose:
                    if result.success:
                        valid_str = " [valid]" if result.is_valid else " [invalid]"
                        print(f"[ok] wall={result.wall_time:.3f}s "
                              f"cpu={result.cpu_time:.3f}s, "
                              f"avg_chain={result.avg_chain_length:.2f}, "
                              f"qubits={result.total_qubits_used}{valid_str}")
                    else:
                        print(f"[fail] {result.error}")
                else:
                    elapsed = elapsed_offset + (time.perf_counter() - _start)
                    print(f"\r  {_bar(done_count)}  {elapsed:.0f}s elapsed",
                          end="", flush=True)

        except KeyboardInterrupt:
            _cancel_flag.set()
            _cancelled = True

        if not verbose:
            print()  # newline after progress bar

        unfinished_tasks = list(tasks[done_count:])

    # ── Parallel path (n_workers > 1) ──────────────────────────────────────────
    else:
        task_queue: multiprocessing.Queue = multiprocessing.Queue()
        result_queue: multiprocessing.Queue = multiprocessing.Queue()

        for task in tasks:
            task_queue.put(task)
        for _ in range(n_workers):
            task_queue.put(None)  # one sentinel per worker

        worker_procs = []
        for _ in range(n_workers):
            p = multiprocessing.Process(
                target=_worker_process,
                args=(task_queue, result_queue, str(workers_dir), batch_id,
                      str(batch_logger.logs_runs_dir), timeout),
            )
            p.start()
            worker_procs.append(p)

        completed_display = 0
        if not verbose:
            # Print initial bar so user sees state immediately (before any trial completes)
            print(f"\r  {_bar(0)}  {elapsed_offset:.0f}s elapsed", end="", flush=True)
        try:
            while completed_display < n_tasks:
                if _is_cancelled():
                    break
                try:
                    display = result_queue.get(timeout=0.5)
                except queue.Empty:
                    continue
                completed_display += 1
                batch_logger.log_run_from_display(display)

                _dstatus = display.get('status', '')
                if _dstatus == 'INVALID_OUTPUT':
                    _inv = _warn_registry.setdefault('INVALID_OUTPUT', {})
                    _dalgo = display['algorithm']
                    _inv[_dalgo] = _inv.get(_dalgo, 0) + 1
                elif _dstatus == 'CRASH':
                    _cr = _warn_registry.setdefault('CRASH', {})
                    _dalgo = display['algorithm']
                    if _dalgo not in _cr:
                        _cr[_dalgo] = {'count': 0, 'first_error': display.get('error')}
                    _cr[_dalgo]['count'] += 1

                if verbose:
                    algo = display['algorithm']
                    prob = display['graph_name']
                    trial = display['trial']
                    if display['success']:
                        print(f"  [{completed_display}/{n_tasks}] {algo} / {prob} "
                              f"trial {trial}: [ok] wall={display['wall_time']:.3f}s "
                              f"avg_chain={display['avg_chain_length']:.2f}")
                    else:
                        print(f"  [{completed_display}/{n_tasks}] {algo} / {prob} "
                              f"trial {trial}: [fail] {display['status']}")
                else:
                    elapsed = elapsed_offset + (time.perf_counter() - _start)
                    print(f"\r  {_bar(completed_display)}  {elapsed:.0f}s elapsed",
                          end="", flush=True)
        except KeyboardInterrupt:
            _cancel_flag.set()

        if not verbose:
            print()

        if _is_cancelled():
            _cancelled = True
            # Drain: collect results that arrived during/just after cancel signal
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
            # Prevent Python from hanging at exit trying to flush queue pipes
            # whose feeder threads are stuck because workers were killed.
            task_queue.cancel_join_thread()
            result_queue.cancel_join_thread()
            for jf in workers_dir.glob("worker_*.jsonl"):
                _strip_truncated_jsonl(jf)
        else:
            for p in worker_procs:
                p.join()

        # Derive unfinished from confirmed completions in JSONL
        completed_seeds = completed_seeds_from_jsonl(batch_dir)
        unfinished_tasks = [
            t for t in tasks
            if (t[2], t[3], t[5], t[7]) not in completed_seeds
            # indices: (algo_name, graph_id, topo_name, trial_seed)
        ]
        done_count = n_tasks - len(unfinished_tasks)

    # Signal the keypress listener to exit its poll loop (exits within 0.5s)
    _cancel_flag.set()

    session_elapsed = time.perf_counter() - _start
    return ExecutionResult(
        warning_registry=_warn_registry,
        unfinished_tasks=unfinished_tasks,
        session_elapsed=session_elapsed,
        completed_count=done_count,
        cancelled=_cancelled,
    )


def _worker_process(task_queue: multiprocessing.Queue,
                    result_queue: multiprocessing.Queue,
                    workers_dir_str: str,
                    batch_id: str,
                    logs_runs_dir_str: str,
                    timeout: float) -> None:
    """Worker process: consume tasks, write JSONL, push display records.

    Pulls (source_graph, target_graph, algo_name, graph_id, graph_name,
           topo_name, trial, trial_seed) tuples from task_queue until it
    receives a None sentinel, then exits. timeout is uniform across all tasks
    and passed as a top-level argument rather than stored in each tuple.

    Workers never print anything — all output is driven by the main process
    reading result_queue. Algorithm stdout/stderr is captured to a per-run
    log file in logs/runs/ for the duration of each embed() call.
    """
    # Detach from the parent's TTY so terminate() can't corrupt terminal state
    try:
        devnull = open(os.devnull, 'r')
        os.dup2(devnull.fileno(), sys.stdin.fileno())
        devnull.close()
    except Exception:
        pass

    worker_file = Path(workers_dir_str) / f"worker_{os.getpid()}.jsonl"
    logs_runs_dir = Path(logs_runs_dir_str)
    while True:
        task = task_queue.get()
        if task is None:  # sentinel — this worker's share is done
            break
        (source_graph, target_graph, algo_name,
         graph_id, graph_name, topo_name, trial, trial_seed) = task

        log_path = run_log_path(logs_runs_dir, algo_name, graph_name, trial, trial_seed)
        _reseed_globals(trial_seed)
        with capture_run(log_path):
            result = benchmark_one(
                source_graph, target_graph, algo_name,
                timeout=timeout, graph_name=graph_name, graph_id=graph_id,
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
            'graph_name':       graph_name,
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
        # Store the raw setting so run_full_benchmark can resolve it against the
        # real output_dir (which isn't known yet at __init__ time).  "child" and
        # "default" are sentinel values that must be resolved via
        # resolve_unfinished_dir(); treating them as literal paths is wrong.
        from ember_qc.config import get as _cfg
        self._unfinished_dir_setting: Optional[str] = (
            unfinished_dir if unfinished_dir is not None else _cfg("unfinished_dir")
        )
        self._default_results_dir: str = results_dir
        self.target_graph = target_graph
        # Deferred: ResultsManager is created in run_full_benchmark once the real
        # output_dir is known, so "child" resolves correctly.
        self.results_manager: Optional[ResultsManager] = None
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
            print("Warning: No pre-generated graphs found. Generating on the fly.")
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
                          cancel_delay: float = 5.0,
                          fault_rate: float = 0.0,
                          fault_seed: Optional[int] = None,
                          faulty_nodes=None,
                          faulty_couplers=None,
                          analyze: bool = False):
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
            fault_rate: Fraction of topology qubits to remove randomly before
                        running. Must be in [0, 1]. Applied once per topology;
                        all trials share the same faulted graph. Default 0.0
                        (no faults).
            fault_seed: Seed for random fault generation. Only used when
                        fault_rate > 0.
            faulty_nodes: Explicit list of qubit IDs to remove from the
                          topology. Cannot be combined with fault_rate > 0.
            faulty_couplers: Explicit list of (u, v) coupler pairs to remove.
                             Isolated nodes left behind are cleaned up
                             automatically. Cannot be combined with fault_rate > 0.

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
            from ember_qc.config import get as _cfg
            cfg_verbose = _cfg("default_verbose")
            verbose = cfg_verbose if cfg_verbose is not None else (n_workers == 1)

        # Validate and create output directory early — fail before any work begins
        # rather than crashing at save time after a long run.
        if output_dir is not None:
            try:
                Path(output_dir).expanduser().mkdir(parents=True, exist_ok=True)
            except OSError as e:
                raise OSError(
                    f"Cannot create output directory '{output_dir}': {e}. "
                    "Check the path and permissions before starting a benchmark run."
                ) from e

        # Create ResultsManager now that the real output_dir is known, so
        # "child" resolves to output_dir/.runs_unfinished/ rather than a path
        # relative to the __init__-time placeholder.
        from ember_qc.config import resolve_unfinished_dir as _resolve_ud
        _effective_results_dir = output_dir or self._default_results_dir
        _resolved_ud = str(_resolve_ud(self._unfinished_dir_setting, output_dir=_effective_results_dir))
        self.results_manager = ResultsManager(
            _effective_results_dir,
            unfinished_dir=_resolved_ud,
        )

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

        # ── Fault simulation ───────────────────────────────────────────────────
        # Applied once per topology before task list construction.
        # All trials/algorithms share the same faulted topology.
        # Each parameter accepts a scalar (applied to all topologies) or a dict
        # keyed by topology name (per-topology control).
        _fault_log: dict = {}           # topo_name -> per-topology fault info or None
        _disconnected_topos: dict = {}  # topo_name -> n_components
        topo_names = [tn for _, _, tn in topo_list]
        n_topos = len(topo_names)

        # Resolve fault_rate per topology (default 0.0)
        if isinstance(fault_rate, dict):
            _fr = {t: float(fault_rate.get(t, 0.0)) for t in topo_names}
        else:
            _fr = {t: float(fault_rate) for t in topo_names}

        # Resolve fault_seed per topology (default to run master seed)
        if isinstance(fault_seed, dict):
            _fs = {t: fault_seed.get(t, seed) for t in topo_names}
        elif fault_seed is not None:
            _fs = {t: fault_seed for t in topo_names}
        else:
            _fs = {t: seed for t in topo_names}

        # Resolve faulty_nodes per topology — flat collection only for single-topo runs
        if isinstance(faulty_nodes, dict):
            _fn = {t: list(faulty_nodes.get(t, [])) for t in topo_names}
        elif faulty_nodes:
            if n_topos > 1:
                raise ValueError(
                    "faulty_nodes must be a dict keyed by topology name for "
                    "multi-topology runs. Expected format:\n"
                    f"  faulty_nodes={{ {', '.join(repr(t)+': [...]' for t in topo_names)} }}"
                )
            _fn = {topo_names[0]: list(faulty_nodes)}
        else:
            _fn = {t: [] for t in topo_names}

        # Resolve faulty_couplers per topology — flat collection only for single-topo runs
        if isinstance(faulty_couplers, dict):
            _fc = {t: list(faulty_couplers.get(t, [])) for t in topo_names}
        elif faulty_couplers:
            if n_topos > 1:
                raise ValueError(
                    "faulty_couplers must be a dict keyed by topology name for "
                    "multi-topology runs. Expected format:\n"
                    f"  faulty_couplers={{ {', '.join(repr(t)+': [...]' for t in topo_names)} }}"
                )
            _fc = {topo_names[0]: list(faulty_couplers)}
        else:
            _fc = {t: [] for t in topo_names}

        # Per-topology mutual exclusion check — before any runs start
        for tn in topo_names:
            if _fr[tn] > 0 and (_fn[tn] or _fc[tn]):
                raise ValueError(
                    f"Topology '{tn}': cannot combine fault_rate with "
                    f"faulty_nodes/faulty_couplers. Use one mode at a time."
                )

        _any_faults = any(_fr[t] > 0 or _fn[t] or _fc[t] for t in topo_names)

        if _any_faults:
            faulted_topo_list = []
            for label, tg, topo_name in topo_list:
                fr, fs = _fr[topo_name], _fs[topo_name]
                fn, fc = _fn[topo_name], _fc[topo_name]

                if not (fr > 0 or fn or fc):
                    _fault_log[topo_name] = None
                    faulted_topo_list.append((label, tg, topo_name))
                    continue

                _topo_mode = 'random' if fr > 0 else 'explicit'
                faulted = simulate_faults(
                    tg,
                    fault_rate=fr,
                    fault_seed=fs,
                    faulty_nodes=fn or None,
                    faulty_couplers=fc or None,
                )
                faulted_node_set = set(faulted.nodes())
                removed_nodes = sorted(set(tg.nodes()) - faulted_node_set)
                removed_couplers = sorted(
                    [list(e) for e in tg.edges()
                     if e[0] in faulted_node_set and e[1] in faulted_node_set
                     and not faulted.has_edge(*e)]
                ) if _topo_mode == 'explicit' else []
                _fault_log[topo_name] = {
                    'mode': _topo_mode,
                    'fault_rate': fr if _topo_mode == 'random' else None,
                    'fault_seed': fs if _topo_mode == 'random' else None,
                    'faulty_nodes': removed_nodes,
                    'faulty_couplers': removed_couplers,
                }
                if not nx.is_connected(faulted):
                    n_comp = nx.number_connected_components(faulted)
                    _disconnected_topos[topo_name] = n_comp
                    print(f"Warning: Fault simulation produced a disconnected topology: "
                          f"{topo_name} ({n_comp} connected components).")
                faulted_topo_list.append((label, faulted, topo_name))
            topo_list = faulted_topo_list

        # Resolve problems
        if problems is None:
            selection = graph_selection or "*"
            problems = _load_test_graphs(selection)
            if not problems:
                print(f"Warning: No graphs matched selection '{selection}'. "
                      f"Run: python generate_test_graphs.py")
                return None

        # Normalize user-supplied problems to (graph_id, name, graph) triples.
        # Legacy callers pass (name, graph) 2-tuples; assign graph_id=0 for those.
        problems = [
            p if len(p) == 3 else (0, p[0], p[1])
            for p in problems
        ]

        # Resolve methods from registry
        available = list(ALGORITHM_REGISTRY.keys())
        if methods is None:
            methods = available

        valid_methods = [m for m in methods if m in ALGORITHM_REGISTRY]
        missing = set(methods) - set(valid_methods)
        if missing:
            print(f"Warning: Unknown algorithms (skipped): {missing}")
            print(f"   Available: {available}")

        # Pre-run availability check — fail fast before any work starts
        unavailable = []
        for algo_name in valid_methods:
            ok, reason = ALGORITHM_REGISTRY[algo_name].is_available()
            if not ok:
                unavailable.append((algo_name, reason))
        if unavailable:
            lines = ["The following algorithms are not available on this machine:"]
            for algo_name, reason in unavailable:
                lines.append(f"  {algo_name}: {reason}")
            raise RuntimeError("\n".join(lines))

        # Pre-run topology compatibility check
        _incompatible_pairs: set = set()  # (algo_name, topo_name) to skip
        _topo_incompat_entries = []       # (algo_name, topo_name, n_skipped)
        for algo_name in valid_methods:
            for _, _, topo_name in topo_list:
                if not _algo_topo_compatible(algo_name, topo_name):
                    n_skip = len(problems) * n_trials
                    _incompatible_pairs.add((algo_name, topo_name))
                    _topo_incompat_entries.append((algo_name, topo_name, n_skip))

        if _topo_incompat_entries:
            print("Warning: Pre-run checks:")
            for algo_name, topo_name, n_skip in _topo_incompat_entries:
                print(f"   {algo_name} is not compatible with topology {topo_name}"
                      f" — {n_skip:,} trials skipped.")

        # Pre-run graph-topology compatibility check — skip graphs that are too
        # large or explicitly marked incompatible with a topology in the manifest.
        _incompat_graph_topo: set = set()  # (graph_id, topo_name) to skip
        for _, target_graph, topo_name in topo_list:
            for graph_id, graph_name, source_graph in problems:
                if not _graph_topo_compatible(graph_id, source_graph,
                                              target_graph, topo_name):
                    _incompat_graph_topo.add((graph_id, topo_name))

        n_graph_topo_skipped = 0
        if _incompat_graph_topo:
            for graph_id, topo_name in _incompat_graph_topo:
                n_compat_algos = sum(
                    1 for a in valid_methods
                    if (a, topo_name) not in _incompatible_pairs
                )
                n_graph_topo_skipped += n_compat_algos * n_trials
            print(f"Pre-run: {len(_incompat_graph_topo):,} graph/topology pair(s) skipped "
                  f"(graph incompatible with topology) — "
                  f"{n_graph_topo_skipped:,} trials skipped before run.")

        n_compatible_combos = len(valid_methods) * len(topo_list) - len(_incompatible_pairs)
        total_measured = len(problems) * n_compatible_combos * n_trials - n_graph_topo_skipped
        total_warmup = len(problems) * n_compatible_combos * warmup_trials

        if n_workers > 1 and warmup_trials > 0:
            print(f"Warning: Warmup trials skipped (not supported with n_workers > 1).")
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
            'output_dir': str(Path(output_dir).expanduser().resolve()) if output_dir else None,
            'fault_rate': fault_rate,
            'fault_seed': fault_seed,
            'faulty_nodes': (
                {k: list(v) for k, v in faulty_nodes.items()}
                if isinstance(faulty_nodes, dict)
                else list(faulty_nodes) if faulty_nodes else None
            ),
            'faulty_couplers': (
                {k: [list(e) for e in v] for k, v in faulty_couplers.items()}
                if isinstance(faulty_couplers, dict)
                else [list(e) for e in faulty_couplers] if faulty_couplers else None
            ),
        }
        # Serialize custom problems into config so they can be reconstructed on resume
        if graph_selection is None or graph_selection == 'custom':
            config['custom_problems'] = [
                {'name': graph_name, 'graph': nx.node_link_data(g, edges="links")}
                for _, graph_name, g in problems
            ]
        if batch_note:
            config['batch_note'] = batch_note

        config['fault_simulation'] = _fault_log if _any_faults else None

        batch_dir = self.results_manager.create_batch(config, batch_note=batch_note)
        batch_id = batch_dir.name

        workers_dir = batch_dir / "workers"
        workers_dir.mkdir(exist_ok=True)

        batch_logger = BatchLogger(batch_dir, batch_id)
        batch_logger.setup(buffered=not verbose)
        batch_logger.info(
            f"Batch {batch_id} starting: {total_measured} planned runs, n_workers={n_workers}"
        )

        # Warning registry — pre-run entries populated here.
        _warn_registry: dict = {}
        if _topo_incompat_entries:
            _warn_registry['TOPOLOGY_INCOMPATIBLE'] = {
                'entries': _topo_incompat_entries,
                'total_skipped': sum(n for _, _, n in _topo_incompat_entries),
            }
        if _disconnected_topos:
            _warn_registry['TOPOLOGY_DISCONNECTED'] = _disconnected_topos

        # Build flat task list — 7-element tuple (timeout excluded, passed uniformly).
        all_tasks = []
        for _, target_graph, topo_name in topo_list:
            for graph_id, graph_name, source_graph in problems:
                if (graph_id, topo_name) in _incompat_graph_topo:
                    continue
                for algo_name in valid_methods:
                    if (algo_name, topo_name) in _incompatible_pairs:
                        continue
                    for trial in range(n_trials):
                        trial_seed = _derive_seed(seed, algo_name, graph_id, topo_name, trial)
                        all_tasks.append((source_graph, target_graph, algo_name,
                                          graph_id, graph_name, topo_name, trial, trial_seed))

        # Warmup: caller-owned, sequential only (n_workers > 1 disables warmup upstream).
        if warmup_trials > 0 and n_workers == 1:
            for _, target_graph, topo_name in topo_list:
                for graph_id, graph_name, source_graph in problems:
                    if (graph_id, topo_name) in _incompat_graph_topo:
                        continue
                    for algo_name in valid_methods:
                        if (algo_name, topo_name) in _incompatible_pairs:
                            continue
                        for w in range(warmup_trials):
                            warmup_seed = _derive_seed(seed, algo_name, graph_id,
                                                       topo_name, -(w + 1))
                            if verbose:
                                print(f"  Warm-up {algo_name} [{w+1}/{warmup_trials}]...", end=" ")
                            _reseed_globals(warmup_seed)
                            benchmark_one(
                                source_graph, target_graph, algo_name,
                                timeout=timeout, graph_name=graph_name, graph_id=graph_id,
                                topology_name=topo_name, trial=-1, seed=warmup_seed,
                            )
                            if verbose:
                                print("(discarded)")

        # Use the actual task count now that all_tasks is built — more accurate
        # than the formula-based total_measured (which can be off if graph loading
        # silently skipped files or names collide across the filtering sets).
        total_measured = len(all_tasks)
        total_runs = total_measured + total_warmup
        config['total_measured_runs'] = total_measured
        config_path = batch_dir / 'config.json'
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)

        topo_str = f" × {len(topo_list)} topologies" if len(topo_list) > 1 else ""
        trials_str = f" × {n_trials} trials" if n_trials > 1 else ""
        warmup_str = f" (+ {warmup_trials} warm-up)" if warmup_trials > 0 else ""
        workers_str = f" [{n_workers} workers]" if n_workers > 1 else ""
        print(f"Starting benchmark: {len(problems)} problems × {len(valid_methods)} algorithms"
              f"{topo_str}{trials_str}{warmup_str} = {total_runs} runs{workers_str}")
        print("Press 'q' + Enter to cancel and save a checkpoint.")
        print("=" * 80)

        # Execute measured tasks
        exec_result = _execute_tasks(
            all_tasks, batch_dir, batch_logger,
            n_workers=n_workers, verbose=verbose, timeout=timeout,
            elapsed_offset=0.0, cancel_delay=cancel_delay,
        )

        # Reconstruct self.results from JSONL (workers terminated inside _execute_tasks)
        self.results = _load_results_from_jsonl(workers_dir)

        # Merge post-run warnings then pre-run (setdefault preserves existing keys)
        exec_result.warning_registry.update(_compute_postrun_warnings(self.results))
        for k, v in _warn_registry.items():
            exec_result.warning_registry.setdefault(k, v)

        # ── Handle cancellation ────────────────────────────────────────────────
        if exec_result.cancelled:
            write_checkpoint(
                batch_dir,
                unfinished_tasks=exec_result.unfinished_tasks,
                total_tasks=len(all_tasks),
                completed_count=exec_result.completed_count,
            )
            batch_logger.teardown()
            print(f"\nCancelled. {exec_result.completed_count}/{len(all_tasks)} trials complete.")
            print(f"Checkpoint saved. Resume with: load_benchmark()")
            _print_warn_summary(exec_result.warning_registry, batch_dir / "logs")
            return None

        # ── Normal completion ──────────────────────────────────────────────────
        batch_wall_time = exec_result.session_elapsed
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
        config['batch_wall_time'] = round(batch_wall_time, 3)
        config_path = batch_dir / "config.json"
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)
        compile_batch(batch_dir)
        # Write summary/README into staging dir BEFORE moving — if the move fails,
        # the batch is fully intact in runs_unfinished/ and recoverable via resume.
        self.results_manager.save_results(self.results, batch_dir, config=config)
        batch_logger.teardown()
        _out = Path(output_dir).expanduser() if output_dir else None
        final_dir = self.results_manager.move_to_output(batch_dir, output_dir=_out)
        _print_warn_summary(exec_result.warning_registry, final_dir / "logs")
        print(f"Results: {final_dir.resolve()}")
        print("=" * 80)
        if analyze:
            _run_post_analysis(final_dir)
        return final_dir


def _run_post_analysis(batch_dir: Path) -> None:
    """Run ember-qc-analysis on a completed batch if the package is installed."""
    try:
        from ember_qc_analysis import BenchmarkAnalysis
    except ImportError:
        print(
            "\nNote: ember-qc-analysis is not installed. "
            "To auto-generate analysis, run:\n"
            "  pip install ember-qc-analysis\n"
            "  or: pip install ember-qc[analysis]"
        )
        return

    # Resolve output root:
    #   1. ember-qc-analysis config output_dir (if set)
    #   2. Default: analysis/ sibling to the batch directory
    output_root = None
    try:
        from ember_qc_analysis._config import resolve as _acfg
        cfg_dir = _acfg("output_dir")
        if cfg_dir:
            output_root = Path(cfg_dir)
    except Exception:
        pass

    if output_root is None:
        output_root = batch_dir.parent / "analysis"

    print(f"\nRunning analysis → {(output_root / batch_dir.name).resolve()}")
    try:
        an = BenchmarkAnalysis(str(batch_dir), output_root=str(output_root))
        an.generate_report()
    except Exception as e:
        print(f"Analysis failed: {e}")


def load_benchmark(batch_id: Optional[str] = None,
                   unfinished_dir: Optional[str] = None,
                   output_dir: Optional[str] = None,
                   n_workers: Optional[int] = None,
                   verbose: bool = None,
                   cancel_delay: float = 5.0,
                   confirm: bool = True,
                   analyze: bool = False) -> Optional[Path]:
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
        confirm: When True (default), prompt the user before resuming if
                 batch_id is not provided. Set False for programmatic use:
                 if exactly one incomplete run exists it is resumed without
                 prompting; if multiple exist a ValueError is raised (pass
                 batch_id to resolve the ambiguity).

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
    # Resolve staging directory: always go through resolve_unfinished_dir so
    # sentinel values like "child" and "default" are handled correctly.
    from ember_qc.config import resolve_unfinished_dir as _resolve_ud
    _unfinished = _resolve_ud(unfinished_dir, output_dir=output_dir)

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
        if confirm:
            try:
                ans = input("Resume it? [Y/n] ").strip().lower()
            except (EOFError, KeyboardInterrupt):
                return None
            if ans not in ('', 'y', 'yes'):
                return None
    else:
        if not confirm:
            raise ValueError(
                f"Multiple incomplete runs found; pass batch_id= to resume "
                f"non-interactively. Available: "
                f"{[r['batch_id'] for r in incomplete_runs]}"
            )
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
                print(f"     [no checkpoint] crashed or still running  "
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

    # Resolve output_dir: explicit arg > saved in config > default (./results/)
    if output_dir is None:
        output_dir = config.get('output_dir')  # absolute path saved at run start

    if verbose is None:
        from ember_qc.config import get as _cfg
        cfg_verbose = _cfg("default_verbose")
        verbose = cfg_verbose if cfg_verbose is not None else (n_workers == 1)

    # Validate and create output directory early — fail before execution begins.
    if output_dir is not None:
        try:
            Path(output_dir).expanduser().mkdir(parents=True, exist_ok=True)
        except OSError as e:
            raise OSError(
                f"Cannot create output directory '{output_dir}': {e}. "
                "Check the path and permissions before resuming a benchmark run."
            ) from e

    # Reconstruct problems
    if 'custom_problems' in config:
        problems = [
            (0, p['name'], nx.node_link_graph(p['graph'], edges="links"))
            for p in config['custom_problems']
        ]
    else:
        problems = _load_test_graphs(graph_selection)
        if not problems:
            raise ValueError(
                f"No graphs matched selection '{graph_selection}'. "
                f"Cannot resume batch {batch_dir.name}."
            )
        # Normalize legacy 2-tuples just in case
        problems = [
            p if len(p) == 3 else (0, p[0], p[1])
            for p in problems
        ]

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

    # Rebuild graph-topology incompatibility set (same logic as run_full_benchmark).
    _incompat_graph_topo_resume: set = set()
    for _, target_graph, topo_name in topo_list:
        for graph_id, graph_name, source_graph in problems:
            if not _graph_topo_compatible(graph_id, source_graph, target_graph, topo_name):
                _incompat_graph_topo_resume.add((graph_id, topo_name))

    # Build full task list (same order as original run) — 8-element tuple.
    all_tasks = []
    for _, target_graph, topo_name in topo_list:
        for graph_id, graph_name, source_graph in problems:
            if (graph_id, topo_name) in _incompat_graph_topo_resume:
                continue
            for algo_name in algorithms:
                for trial in range(n_trials):
                    trial_seed = _derive_seed(seed, algo_name, graph_id, topo_name, trial)
                    all_tasks.append((source_graph, target_graph, algo_name,
                                      graph_id, graph_name, topo_name, trial, trial_seed))

    # Determine which tasks remain
    checkpoint = read_checkpoint(batch_dir)
    # Always scan JSONL — used as the authoritative completed set in both paths.
    # In the checkpoint path this catches tasks written to JSONL by workers
    # after the checkpoint was saved but before the cancel-drain completed
    # (race condition in parallel mode that would otherwise cause duplicates).
    completed_seeds = completed_seeds_from_jsonl(batch_dir)
    if checkpoint:
        resume_count = checkpoint.get('resume_count', 0)
        stored_unfinished = checkpoint.get('unfinished_tasks', [])
        # Legacy checkpoints (pre-v1.1) stored problem_name instead of graph_id.
        # If graph_id is absent, fall through to JSONL-only recovery.
        _has_graph_id = stored_unfinished and 'graph_id' in stored_unfinished[0]
        if _has_graph_id:
            unfinished_set = {
                (t['algo_name'], t['graph_id'], t['topo_name'], t['trial'], t['trial_seed'])
                for t in stored_unfinished
            }
            remaining_tasks = [
                t for t in all_tasks
                if (t[2], t[3], t[5], t[6], t[7]) in unfinished_set
                and (t[2], t[3], t[5], t[7]) not in completed_seeds
            ]
        else:
            # Legacy checkpoint — graph_id not available; fall back to JSONL
            print("  Note: legacy checkpoint format detected — resuming from JSONL.")
            remaining_tasks = [
                t for t in all_tasks
                if (t[2], t[3], t[5], t[7]) not in completed_seeds
            ]
    else:
        # Crashed run — derive entirely from JSONL
        resume_count = 0
        remaining_tasks = [
            t for t in all_tasks
            if (t[2], t[3], t[5], t[7]) not in completed_seeds
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

    # If all tasks already done (e.g. crashed at save time), compile and save
    if n_remaining == 0:
        print("All tasks already complete. Compiling and saving results...")
        compile_batch(batch_dir)
        delete_checkpoint(batch_dir)
        workers_dir = batch_dir / "workers"
        all_results = _load_results_from_jsonl(workers_dir)
        _results_root = Path(output_dir).expanduser() if output_dir else Path("./results")
        _rm = ResultsManager(str(_results_root), unfinished_dir=str(_unfinished))
        _rm.save_results(all_results, batch_dir, config=config)
        final_dir = _rm.move_to_output(batch_dir)
        print(f"Results: {final_dir.resolve()}")
        if analyze:
            _run_post_analysis(final_dir)
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
    batch_logger.setup(buffered=not verbose)
    batch_logger.info(
        f"Resuming {batch_id}: {n_remaining} tasks remaining "
        f"(resume #{resume_count + 1})"
    )

    print("Press 'q' + Enter to cancel and save a checkpoint.")
    print("=" * 80)

    elapsed_offset = config.get('batch_wall_time', 0.0)

    # Execute remaining tasks
    exec_result = _execute_tasks(
        remaining_tasks, batch_dir, batch_logger,
        n_workers=n_workers, verbose=verbose, timeout=timeout,
        elapsed_offset=elapsed_offset, cancel_delay=cancel_delay,
        completed_offset=n_already_done, total_tasks=len(all_tasks),
    )

    # Read all results from JSONL (original session + this session)
    all_results = _load_results_from_jsonl(workers_dir)

    # Post-run warnings computed over all results (full picture including original run)
    _warn_registry: dict = {}
    _warn_registry.update(_compute_postrun_warnings(all_results))
    exec_result.warning_registry.update(_warn_registry)

    # ── Handle cancel during resume ────────────────────────────────────────────
    if exec_result.cancelled:
        write_checkpoint(
            batch_dir,
            unfinished_tasks=exec_result.unfinished_tasks,
            total_tasks=len(all_tasks),
            completed_count=len(all_tasks) - len(exec_result.unfinished_tasks),
            resume_count=resume_count + 1,
        )
        batch_logger.teardown()
        n_done = len(all_tasks) - len(exec_result.unfinished_tasks)
        print(f"\nCancelled. {n_done}/{len(all_tasks)} trials complete.")
        print(f"Checkpoint saved. Resume again with: load_benchmark()")
        _print_warn_summary(exec_result.warning_registry, batch_dir / "logs")
        return batch_dir

    # ── Normal completion of resume ────────────────────────────────────────────
    session_elapsed = exec_result.session_elapsed
    batch_wall_time = elapsed_offset + session_elapsed
    n_success = sum(1 for r in all_results if r.success)
    batch_logger.info(
        f"Resume of {batch_id} complete: {n_success}/{len(all_results)} succeeded "
        f"in {session_elapsed:.1f}s (total {batch_wall_time:.1f}s)"
    )
    m, s = divmod(int(batch_wall_time), 60)
    h, m = divmod(m, 60)
    time_str = f"{h}h {m}m {s}s" if h else f"{m}m {s}s" if m else f"{s}s"
    print("\n" + "=" * 80)
    print("Benchmark complete!")
    print(f"Total wall time: {batch_wall_time:.1f}s ({time_str})")

    config['batch_wall_time'] = round(batch_wall_time, 3)
    config_path = batch_dir / "config.json"
    with open(config_path, 'w') as f:
        json.dump(config, f, indent=2)

    compile_batch(batch_dir)
    delete_checkpoint(batch_dir)
    _results_root = Path(output_dir).expanduser() if output_dir else Path("./results")
    _rm = ResultsManager(str(_results_root), unfinished_dir=str(_unfinished))
    _rm.save_results(all_results, batch_dir, config=config)
    batch_logger.teardown()
    final_dir = _rm.move_to_output(batch_dir)
    _print_warn_summary(exec_result.warning_registry, final_dir / "logs")
    print(f"Results: {final_dir.resolve()}")
    print("=" * 80)
    if analyze:
        _run_post_analysis(final_dir)
    return final_dir


def delete_benchmark(batch_id: Optional[str] = None,
                     unfinished_dir: Optional[str] = None,
                     output_dir: Optional[str] = None,
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

    from ember_qc.config import resolve_unfinished_dir as _resolve_ud
    _unfinished = _resolve_ud(unfinished_dir, output_dir=output_dir)

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
        if force:
            raise ValueError(
                f"Multiple incomplete runs found; pass batch_id= to delete "
                f"non-interactively. Available: "
                f"{[r['batch_id'] for r in incomplete_runs]}"
            )
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
                print(f"     [no checkpoint] crashed or still running  "
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

