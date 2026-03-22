# Part 2: Algorithm Interface Contract

This is the mandatory reference for anyone implementing or modifying an algorithm wrapper
in EMBER. Every rule exists because violating it has caused real data corruption, silent
benchmark invalidation, or pipeline crashes.

---

## Base Class

    from ember import EmbeddingAlgorithm, register_algorithm

    @register_algorithm("my_algorithm")
    class MyAlgorithm(EmbeddingAlgorithm):

        # Declare which optional counters this algorithm reports.
        # Distinguishes "not applicable" from "not instrumented" in analysis.
        # An empty list is valid — do not list counters you don't populate.
        supported_counters = ['target_node_visits', 'cost_function_evaluations']

        @property
        def version(self) -> str:
            """Return a version string for reproducibility.

            Vendored C++ code: return the git commit hash you copied from.
            pip packages: return the installed version string.
            Your own code: return a meaningful semver string.
            """
            return "1.0.0"

        def embed(self, source_graph, target_graph, timeout=60.0, **kwargs):
            ...

---

## Mandatory Signature

    def embed(self, source_graph, target_graph, timeout=60.0, **kwargs):

- `source_graph`: NetworkX Graph. Do not assume specific node labeling.
- `target_graph`: NetworkX Graph. Node labels depend on topology.
- `timeout`: float, seconds. Your algorithm **must** stop within this time.
- `**kwargs`: must be accepted. The runner passes `seed=`, `tries=`, and other
  parameters through this.

---

## Seed Handling

The runner passes `seed=<int>` through kwargs for reproducibility.
Your algorithm **must** use it:

    seed = kwargs.get('seed', None)

    # Python algorithms — set all RNG sources you use:
    if seed is not None:
        import random
        import numpy as np
        random.seed(seed)
        np.random.seed(seed)

    # Algorithms with their own seed parameter (e.g. MinorMiner):
    embedding = minorminer.find_embedding(
        source_edges, target_edges,
        random_seed=seed,
    )

    # C++ subprocess algorithms — pass as a CLI argument:
    cmd = ["./my_binary", "--seed", str(seed), ...]

If your algorithm has no seeding mechanism, document this explicitly in the class
docstring. Reproducibility is limited for unseeded algorithms and this must be
disclosed so analysis pipelines can flag it.

---

## Return Format

### Required Fields (every return path, success or failure)

The runner treats the algorithm as an untrusted black box. These three fields are the
minimum viable contract. Everything else is either computed by the runner or optional:

    {
        'embedding': dict,   # {source_node: [target_node, ...]} on success, {} on failure
        'time':      float,  # wall-clock seconds (perf_counter delta)
        'success':   bool,   # True if algorithm believes it found a valid embedding
    }

**Never return `None`.** Every code path in `embed()` must return a dict. A function
that returns `None` forces null checks throughout the pipeline — one missed check
crashes the benchmark silently.

**Always include `success` explicitly.** Do not rely on the runner inferring success
from embedding non-emptiness. If an algorithm returns a non-empty but invalid embedding,
`success: True` is correct — the runner's validator will catch it and override to
`INVALID_OUTPUT`. But the field must be present in every return dict.

### Suggested Optional Fields

These fields improve analysis and diagnostics but are not required. Populate what you
can measure precisely. A wrong counter is worse than a missing one:

    {
        # === Timing ===
        'cpu_time': float,              # CPU seconds (process_time or RUSAGE_CHILDREN)

        # === Failure context ===
        'status': str,                  # TIMEOUT, FAILURE, OOM — see valid statuses below
        'error':  str,                  # human-readable explanation or traceback
        'partial': bool,                # True if embedding contains overlaps (timeout case)

        # === Algorithmic counters ===
        'target_node_visits':        int,   # nodes examined during path search
        'cost_function_evaluations': int,   # calls to the cost/weight function
        'embedding_state_mutations': int,   # chain assignments created, changed, or destroyed
        'overlap_qubit_iterations':  int,   # complete passes of the overlap-resolution loop
    }

### On Success

    {
        'embedding': {0: [100, 101], 1: [200], 2: [300, 301]},
        'time':      1.243,
        'cpu_time':  1.241,
        'success':   True,

        # Optional counters — include only those you measure precisely:
        'target_node_visits':        42000,
        'cost_function_evaluations': 15000,
        'embedding_state_mutations': 350,
        'overlap_qubit_iterations':  12,
    }

### On Failure

    {
        'embedding': {},
        'time':      60.01,
        'cpu_time':  59.98,
        'success':   False,
        'status':    'TIMEOUT',
        'error':     'Exceeded 60s timeout with 3 overlapping qubits remaining',
    }

### On Timeout with Partial Progress

    {
        'embedding': partial_embedding,   # may contain overlaps — not a valid embedding
        'time':      60.01,
        'cpu_time':  59.98,
        'success':   False,
        'status':    'TIMEOUT',
        'partial':   True,
        'error':     'Timeout with 3 overlapping qubits remaining',
    }

When `partial: True`, the runner preserves the embedding for diagnostic analysis but
skips validation and metric computation. Useful for understanding how close the
algorithm was before timing out.

---

## What the Runner Computes (Never Self-Report These)

The runner independently validates and computes the following from the returned
embedding. Algorithms must never self-report these fields — if present, they are
ignored:

- `is_valid`: Layer 1 structural validation result
- `total_qubits`: sum of all chain lengths
- `max_chain_length`: longest single chain
- `avg_chain_length`: mean chain length
- `chain_length_std`: standard deviation of chain lengths
- `qubit_overhead`: total_qubits / n_source

This ensures a buggy algorithm cannot report misleading quality metrics.

---

## Valid Status Values

| Status           | Meaning                                                  | Set by              |
|------------------|----------------------------------------------------------|---------------------|
| `SUCCESS`        | Valid embedding found within timeout                     | Runner (post-validation) |
| `TIMEOUT`        | Timeout exceeded                                         | Algorithm wrapper   |
| `CRASH`          | Algorithm raised an unhandled exception                  | Runner              |
| `OOM`            | Out of memory (if detectable)                            | Algorithm or runner |
| `INVALID_OUTPUT` | Algorithm claimed success but embedding failed validation | Runner only        |
| `FAILURE`        | Algorithm completed but found no embedding               | Algorithm wrapper   |

Algorithms set `TIMEOUT`, `OOM`, or `FAILURE`. The runner sets `SUCCESS` (after
validation passes) and `INVALID_OUTPUT` (when validation fails). `CRASH` is set by
the runner's exception handler. Never set `INVALID_OUTPUT` or `SUCCESS` from within
an algorithm wrapper.

---

## Algorithmic Operation Counters

These four counters measure algorithmic work independent of hardware. Only populate
counters you can measure precisely — declare them in `supported_counters`.

| Counter | What to count | When to increment |
|---|---|---|
| `target_node_visits` | Each target graph node examined during path search or chain placement | Inside Dijkstra/BFS inner loop, once per node popped from the queue |
| `cost_function_evaluations` | Each call to the objective/cost function used to score a placement | Each time `w(q)`, `cost(g,j)`, or equivalent is computed |
| `embedding_state_mutations` | Each time a chain assignment changes (created, destroyed, extended, shrunk, or reassigned) | Each time the embedding dict is modified |
| `overlap_qubit_iterations` | Each complete pass of the overlap-resolution loop | At the boundary of each iteration of the main refinement loop |

**Counter rules:**

- Only populate counters you can measure precisely. A wrong counter is worse than a
  missing one.
- Each increment must be a single integer addition (`counter += 1`). No function calls,
  no string operations, no memory allocation per increment.
- Counters are `Optional[int]` in the result. Omit keys you don't measure — don't set
  them to `0` unless the algorithm genuinely performed zero of that operation.
- Declare supported counters in the `supported_counters` class attribute.

Example — instrumenting a Python algorithm:

    def embed(self, source_graph, target_graph, timeout=60.0, **kwargs):
        visits    = 0
        cost_evals = 0
        mutations  = 0
        iterations = 0

        wall_start = time.perf_counter()
        cpu_start  = time.process_time()

        # ... main loop ...
        for stage in range(max_iterations):
            iterations += 1
            for v_i in order:
                for q in T_nodes:
                    cost_evals += 1
                    # compute w(q) ...
                visits += 1
                # dijkstra inner loop ...
            phi[v_i] = new_chain
            mutations += 1

        return {
            'embedding': embedding,
            'time':      time.perf_counter() - wall_start,
            'cpu_time':  time.process_time() - cpu_start,
            'success':   True,
            'target_node_visits':        visits,
            'cost_function_evaluations': cost_evals,
            'embedding_state_mutations': mutations,
            'overlap_qubit_iterations':  iterations,
        }

---

## CPU Time Measurement

### Python-native algorithms

    wall_start = time.perf_counter()   # NOT time.time() — perf_counter is monotonic
    cpu_start  = time.process_time()

    # ... algorithm work ...

    return {
        'time':     time.perf_counter() - wall_start,
        'cpu_time': time.process_time() - cpu_start,
    }

`time.process_time()` measures CPU time of the current Python process only.
Correct for Python algorithms where all work happens in-process.

### Subprocess algorithms (C++ binaries)

`time.process_time()` reports near-zero because work happens in the child process.
Use `resource.RUSAGE_CHILDREN`:

    import resource, subprocess, time

    wall_start       = time.perf_counter()
    children_before  = resource.getrusage(resource.RUSAGE_CHILDREN)

    proc = subprocess.run(
        ["./my_binary", source_path, target_path, output_path],
        timeout=timeout,
        capture_output=True,
        text=True,
    )

    children_after = resource.getrusage(resource.RUSAGE_CHILDREN)
    wall_end       = time.perf_counter()

    cpu_elapsed = (
        (children_after.ru_utime - children_before.ru_utime) +
        (children_after.ru_stime - children_before.ru_stime)
    )

    return {
        'time':     wall_end - wall_start,
        'cpu_time': cpu_elapsed,
    }

`RUSAGE_CHILDREN` is cumulative — the delta between before/after captures exactly that
child's CPU usage. Never spawn background processes inside `embed()`; they contaminate
the measurement. Note: `RUSAGE_CHILDREN` is Linux/macOS only. On Windows, fall back to
wall-clock time and document the limitation.

---

## Embedding Format

    # Correct: plain Python dict, list values, labels matching target graph nodes
    embedding = {
        0: [100, 101, 102],
        1: [200, 201],
        2: [300],
    }

    # WRONG — sets lose ordering and break downstream processing:
    {0: {100, 101}}

    # WRONG — tuples are not lists:
    {0: (100, 101)}

    # WRONG — numpy arrays break JSON serialization:
    {0: np.array([100, 101])}

    # WRONG — numpy int64 keys break JSON serialization:
    {np.int64(0): [100, 101]}

If your algorithm uses numpy internally, cast before returning:

    embedding = {int(k): [int(v) for v in chain] for k, chain in raw.items()}

---

## Temporary File Handling for C++ Wrappers

    import tempfile, os, json

    fd, source_path = tempfile.mkstemp(suffix='.json')
    try:
        with os.fdopen(fd, 'w') as f:
            json.dump(graph_data, f)
        proc = subprocess.run(["./binary", source_path, ...], ...)
    finally:
        if os.path.exists(source_path):
            os.remove(source_path)

Do **not** use `tempfile.mktemp()` — deprecated due to a race condition. Do **not**
use `NamedTemporaryFile` when the file must be read by a subprocess — on Windows the
file cannot be opened by another process while the Python handle is open.

---

## What `embed()` Must Not Do

- **Print to stdout or stderr.** Use `logging.getLogger(__name__)` at DEBUG level.
  Print statements corrupt runner output and break parallel execution.
- **Write files to the current working directory.** The benchmark runs in parallel.
  Use `tempfile` for all I/O. Always clean up in `finally`.
- **Call `sys.exit()` or `os._exit()`.** Raise an exception. The runner manages
  process lifecycle.
- **Modify input graphs.** `source_graph` and `target_graph` are shared objects.
  Use `.copy()` if you need mutations.
- **Import heavy dependencies at module level.** Import PyTorch etc. inside `embed()`
  or a lazy initializer.
- **Silence all exceptions.** `except Exception: pass` hides bugs. Let exceptions
  propagate or capture the full traceback in the `error` field.
- **Reuse mutable state between `embed()` calls.** Initialize all local state at the
  start of each call. Instance-level caches that grow across runs corrupt later results.
- **Spawn background processes or threads that outlive `embed()`.** All computation
  must complete before `embed()` returns. Orphaned processes contaminate
  `RUSAGE_CHILDREN` measurements for subsequent calls.

---

## Validation Layers

The runner independently validates every result before it enters the database.
Algorithms cannot opt out of validation.

### Layer 1 — Structural Validation (mandatory, every run)

Cheap (O(n + e)) and catches the most common bugs. Any failure marks the run
`INVALID_OUTPUT` regardless of what the algorithm claimed:

1. **Coverage**: every source vertex has a key in the embedding dict
2. **Non-empty chains**: every chain has at least one target node
3. **Connectivity**: every chain is a connected subgraph of the target graph
4. **Disjointness**: no target node appears in more than one chain
5. **Edge preservation**: for every source edge (u, v), at least one target edge exists
   between chain(u) and chain(v)

### Layer 2 — Type/Format Validation (mandatory, every run)

Catches serialization bugs before they corrupt the database:

- All keys in `embedding` are valid source node IDs
- All values in chains are valid target node IDs (exist in the target graph)
- All values are plain Python `int`, not `numpy.int64`
- All chains are lists, not sets/tuples/arrays
- Wall time is positive and finite
- CPU time (if present) is non-negative and ≤ wall time × number of cores

### Layer 3 — Consistency Validation (mandatory, every run)

Catches logical contradictions:

- If `success: True`, embedding must be non-empty
- If `success: False` and `partial: False`, embedding should be empty
- If counters are present, they must be non-negative integers
- `status` must be a valid enum value

### Layer 4 — Statistical Sanity Checks (optional, per-batch)

Runs once after the full benchmark as a quality report, not a gate:

- **Seed reproducibility spot-check**: for a random 5% of (algorithm, graph, topology)
  triples, run twice with the same seed and verify identical embeddings
- **Timing outlier detection**: flag runs where wall time is >10× the median for that
  (algorithm, graph class)
- **Counter monotonicity**: for the same algorithm on graphs of increasing size,
  counters should generally increase
- **Cross-algorithm sanity**: if all algorithms fail on an instance, flag it as
  potentially unembeddable

### Layer 5 — Ground Truth Validation (optional, rare)

For instances with known-optimal embeddings (IP method or planted-solution graphs):
compare total qubits to the known optimal. Does not validate correctness (Layer 1
does that) but validates quality claims for the paper.

---

## EmbeddingResult Dataclass

The runner populates this from the validated algorithm output. Fields marked
*runner-computed* are never trusted from the algorithm:

    @dataclass
    class EmbeddingResult:

        # === Set by runner (never trust algorithm for these) ===
        success:          bool
        status:           str
        is_valid:         bool
        wall_time:        float
        cpu_time:         float
        algorithm_name:   str
        algorithm_version: str

        # === Computed by runner from validated embedding ===
        embedding:         Optional[Dict[int, List[int]]]
        total_qubits:      Optional[int]
        max_chain_length:  Optional[int]
        avg_chain_length:  Optional[float]
        chain_length_std:  Optional[float]
        qubit_overhead:    Optional[float]      # total_qubits / n_source

        # === Passed through from algorithm (optional) ===
        target_node_visits:        Optional[int]
        cost_function_evaluations: Optional[int]
        embedding_state_mutations: Optional[int]
        overlap_qubit_iterations:  Optional[int]
        partial:                   bool
        error:                     Optional[str]
        metadata:                  Optional[dict]

---

## Algorithm Contract Test Suite

These tests run against every registered algorithm. Add new tests when new contract
rules are added:

    import pytest
    import hashlib, io, sys
    import networkx as nx
    from ember import benchmark_one, ALGORITHM_REGISTRY

    @pytest.fixture
    def small_target():
        import dwave_networkx as dnx
        return dnx.chimera_graph(4, 4, 4)

    @pytest.fixture
    def small_source():
        return nx.complete_graph(6)

    @pytest.fixture
    def impossible_source():
        return nx.complete_graph(200)


    @pytest.mark.parametrize("algo_name", list(ALGORITHM_REGISTRY.keys()))
    class TestAlgorithmContract:

        def test_returns_result_on_success(self, algo_name, small_source, small_target):
            result = benchmark_one(small_source, small_target, algo_name, timeout=30)
            assert result is not None
            assert isinstance(result.wall_time, float)
            assert isinstance(result.cpu_time, float)
            assert result.cpu_time >= 0

        def test_returns_result_on_failure(self, algo_name, impossible_source, small_target):
            result = benchmark_one(impossible_source, small_target, algo_name, timeout=5)
            assert result is not None
            assert result.success == False
            assert result.status in {'TIMEOUT', 'CRASH', 'FAILURE', 'OOM', 'INVALID_OUTPUT'}

        def test_respects_timeout(self, algo_name, impossible_source, small_target):
            result = benchmark_one(impossible_source, small_target, algo_name, timeout=2)
            assert result.wall_time < 5.0, f"{algo_name} exceeded timeout by >3s"

        def test_seed_reproducibility(self, algo_name, small_source, small_target):
            r1 = benchmark_one(small_source, small_target, algo_name, seed=42, timeout=30)
            r2 = benchmark_one(small_source, small_target, algo_name, seed=42, timeout=30)
            if r1.success and r2.success:
                assert r1.embedding == r2.embedding, \
                    f"{algo_name} produced different embeddings with same seed"

        def test_does_not_modify_inputs(self, algo_name, small_source, small_target):
            source_hash = hashlib.sha256(
                str(sorted(small_source.edges())).encode()
            ).hexdigest()
            target_hash = hashlib.sha256(
                str(sorted(small_target.edges())).encode()
            ).hexdigest()
            benchmark_one(small_source, small_target, algo_name, timeout=10)
            assert hashlib.sha256(
                str(sorted(small_source.edges())).encode()
            ).hexdigest() == source_hash
            assert hashlib.sha256(
                str(sorted(small_target.edges())).encode()
            ).hexdigest() == target_hash

        def test_no_stdout_output(self, algo_name, small_source, small_target):
            captured = io.StringIO()
            old_stdout = sys.stdout
            sys.stdout = captured
            try:
                benchmark_one(small_source, small_target, algo_name, timeout=10)
            finally:
                sys.stdout = old_stdout
            assert captured.getvalue() == "", \
                f"{algo_name} printed to stdout: {captured.getvalue()[:200]}"

        def test_counters_are_valid_types(self, algo_name, small_source, small_target):
            result = benchmark_one(small_source, small_target, algo_name, timeout=30)
            for c in ['target_node_visits', 'cost_function_evaluations',
                      'embedding_state_mutations', 'overlap_qubit_iterations']:
                value = getattr(result, c, None)
                if value is not None:
                    assert isinstance(value, int), \
                        f"{algo_name}.{c} is {type(value)}, expected int"
                    assert value >= 0, f"{algo_name}.{c} is negative: {value}"

        def test_counters_reproducible_with_seed(self, algo_name, small_source, small_target):
            r1 = benchmark_one(small_source, small_target, algo_name, seed=42, timeout=30)
            r2 = benchmark_one(small_source, small_target, algo_name, seed=42, timeout=30)
            if r1.success and r2.success:
                for c in ['target_node_visits', 'cost_function_evaluations',
                          'embedding_state_mutations', 'overlap_qubit_iterations']:
                    v1 = getattr(r1, c, None)
                    v2 = getattr(r2, c, None)
                    if v1 is not None and v2 is not None:
                        assert v1 == v2, \
                            f"{algo_name}.{c} not reproducible: {v1} vs {v2}"

        def test_version_is_string(self, algo_name):
            algo = ALGORITHM_REGISTRY[algo_name]()
            assert isinstance(algo.version, str)
            assert len(algo.version) > 0

        def test_required_fields_present(self, algo_name, small_source, small_target):
            """Verify the three required fields are present on every return path."""
            result = benchmark_one(small_source, small_target, algo_name, timeout=30)
            assert hasattr(result, 'success'), f"{algo_name} missing 'success' field"
            assert hasattr(result, 'wall_time'), f"{algo_name} missing 'time' field"
            assert result.embedding is not None, f"{algo_name} returned None embedding"