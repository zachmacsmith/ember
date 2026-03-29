# EMBER — Developer Guide
### Team Organization, Coding Standards, and Contribution Policies

---

## Team Split

**Zach — Core software**

All runner logic, storage pipeline, configuration, analysis, packaging, and algorithm interface enforcement. Phases 1, 3, 4, 5, and 6 of the roadmap are exclusively yours. Nobody else modifies the runner, storage layer, validation logic, or benchmark execution code. A silent data integrity bug from an inexperienced contributor is worse than slow progress — one wrong change and 90K results are silently corrupted.

**Team member A — Algorithm implementations**

Wrap CHARME, fix the existing PSSA violations (see below), and add any other algorithms. Work entirely within the `EmbeddingAlgorithm` base class. If the contract is violated, the validator catches it at runtime. Spec: this document's interface contract section and the vendoring policy. Nothing else.

**Team member B — Graph library (Phase 2)**

Random graph scale-up, structured graphs, QUBO generators + pre-generated graphs, planted-solution graphs, stress tests, graph property computation. Use and extend the existing `graphs.py` generators — do not rewrite them. A different seeding scheme produces a subtly different distribution and breaks reproducibility claims.

The hard part of Phase 2 is **property computation** (Phase 2.5), not the QUBO generators. The Fiedler eigenvalue requires scipy's sparse eigensolver and is expensive at scale. Diameter is prohibitive above ~80 nodes — use BFS approximation or drop it. Allocate time accordingly.

---

## Immediate Fix Required: PSSA Contract Violations

The current PSSA wrapper has five violations that must be fixed before any benchmarks including PSSA are run:

1. `embed()` is missing the `timeout` parameter
2. Returns `None` on failure instead of `{'embedding': {}, 'time': elapsed, 'success': False}`
3. `print(f"PSSA error: {e}")` in the except block — stdout pollution
4. No `seed` kwarg handling — results are not reproducible
5. No CPU time measurement alongside wall-clock

The registration-time `print("✓ PSSA algorithms registered...")` should also become `logging.info(...)`.

---

## Vendoring Policy

All third-party algorithm code (PSSA, CHARME, etc.) must be copied directly into `ember/algorithms/third_party/` alongside:
- The original license file
- A `SOURCE.md` file documenting the source repo URL and exact commit hash copied from

Do not use external pip install dependencies for algorithm implementations.

**Why:** Reproducibility is EMBER's core claim. If an external algorithm repo changes between two runs, results are incomparable. The SHA-256 graph manifest enforces graph reproducibility — algorithm code must be held to the same standard. Vendoring also gives users zero extra setup steps for Python algorithms.

**What stays as a pip dependency:** Infrastructure packages (NetworkX, NumPy, D-Wave SDK). Only algorithm implementations get vendored.

**C++ algorithms** require compilation and cannot be vendored as binaries. Document the exact build steps and compiler version in `ember/algorithms/third_party/{algo}/BUILD.md`.

---

## Algorithm Interface Contract

Every algorithm must subclass `EmbeddingAlgorithm` and register with `@register_algorithm`.

### Mandatory Signature

```python
@register_algorithm("my_algorithm")
class MyAlgorithm(EmbeddingAlgorithm):
    def embed(self, source_graph, target_graph, timeout=60.0, **kwargs):
```

`timeout` is not optional. `**kwargs` must be accepted. `seed=kwargs.get('seed', None)` must be used to seed any randomness.

### Return Format

**Success:**
```python
{
    'embedding': {0: [100, 101], 1: [200], ...},  # plain Python lists only
    'time': wall_elapsed_seconds,                  # float

    # Optional — hardware-agnostic algorithmic operation counters.
    # Populate whichever you can instrument; omit the rest entirely.
    'target_node_visits':        int,   # search effort: target graph nodes examined
    'cost_function_evaluations': int,   # decision effort: times the cost function was called
    'embedding_state_mutations': int,   # editing effort: times the embedding was modified
    'overlap_qubit_iterations':  int,   # congestion effort: overlap-resolving iterations
                                        # (iterative algorithms only — omit for clique embedding)
}
```

**Failure:**
```python
{'embedding': {}, 'time': elapsed, 'success': False, 'status': 'TIMEOUT'}
```

Never return `None`. Never raise unhandled exceptions from `embed()`. The runner catches exceptions and logs them, but a silently-failing algorithm returning garbage is worse than a crash.

### Algorithmic Operation Counters

These four counters are the hardware-agnostic complement to wall-clock and CPU time. They measure *how much work* the algorithm did, independent of the machine it ran on. An algorithm that converges in 500 cost evaluations on a Raspberry Pi did the same algorithmic work as one that converges in 500 evaluations on a datacenter node.

| Counter | What to count | Applicable to |
|---------|--------------|---------------|
| `target_node_visits` | Each time a target graph node is examined during path search or chain placement | All search-based algorithms |
| `cost_function_evaluations` | Each call to the objective/cost function used to accept or reject a move | All algorithms with an explicit cost model |
| `embedding_state_mutations` | Each time a chain assignment is changed (node added, removed, or reassigned) | All algorithms |
| `overlap_qubit_iterations` | Each pass of an overlap-resolution loop (one iteration = one attempt to remove all qubit conflicts) | Iterative algorithms only; omit for deterministic one-shot methods like clique embedding |

**Guidelines:**

- Only populate counters you can measure precisely. A wrong counter is worse than a missing one — it silently invalidates comparisons.
- Count at the finest granularity that is natural to your algorithm. Do not aggregate multiple inner-loop operations into a single increment.
- **Each increment must be a single integer addition (`counter += 1`).** No function calls, no branch logic, no memory allocation per increment. The overhead of instrumentation must be negligible relative to the algorithm's actual work — if the counter itself meaningfully changes wall-clock or CPU time, the measurement invalidates the metric it is trying to capture.
- Counters are `Optional[int]` in `EmbeddingResult`. `None` means "not reported"; `0` is a valid value meaning "the algorithm ran but performed zero of these operations".
- The runner does not require any counters. Algorithms that cannot be instrumented (e.g., C++ binaries without modified output) simply omit the keys from the return dict.

**Example — instrumenting a Python algorithm:**
```python
def embed(self, source_graph, target_graph, timeout=60.0, **kwargs):
    visits = 0
    mutations = 0
    cost_evals = 0

    for node in source_graph.nodes():
        for candidate in target_graph.nodes():
            visits += 1                        # single integer addition only
            cost = self._cost(candidate, ...)
            cost_evals += 1                    # single integer addition only
            if cost < best_cost:
                embedding[node] = candidate
                mutations += 1                 # single integer addition only

    return {
        'embedding': embedding,
        'time': elapsed,
        'target_node_visits': visits,
        'cost_function_evaluations': cost_evals,
        'embedding_state_mutations': mutations,
        # overlap_qubit_iterations omitted — not applicable to this algorithm
    }
```

### Embedding Format

```python
# Correct: plain Python lists, target-graph node labels
embedding = {
    0: [100, 101, 102],
    1: [200, 201],
    2: [300],
}

# Wrong: sets, tuples, or numpy arrays break downstream code and JSON serialization
embedding = {0: {100, 101}, 1: (200,), 2: np.array([300])}
```

### What `embed()` Must Not Do

1. **Print to stdout or stderr.** Use `logging` at DEBUG level. Print statements corrupt the output stream and break progress reporting.
2. **Use `tempfile.mktemp()`.** It is deprecated specifically because of the race condition between filename generation and file creation. Use `NamedTemporaryFile(delete=False)` for output paths.
3. **Hardcode file paths.** Use `tempfile` for all I/O. Always clean up in a `finally` block.
4. **Call `sys.exit()` or `os._exit()`.** Raise exceptions instead.
5. **Modify input graphs.** `source_graph` and `target_graph` are shared across runs. Use `.copy()` if you need a modified version.
6. **Place heavy imports at module level.** Import PyTorch, TensorFlow, or other large libraries inside `embed()` or in a lazy initializer.
7. **Catch and silence all exceptions.** `except Exception: pass` is never acceptable. Let exceptions propagate.

### CPU Time for C++ Algorithms

`time.process_time()` only measures the current Python process. For algorithms using `subprocess`, use `resource.RUSAGE_CHILDREN`:

```python
import resource

children_before = resource.getrusage(resource.RUSAGE_CHILDREN)
proc = subprocess.run([...], timeout=timeout, ...)
children_after = resource.getrusage(resource.RUSAGE_CHILDREN)

cpu_elapsed = (
    (children_after.ru_utime - children_before.ru_utime) +
    (children_after.ru_stime - children_before.ru_stime)
)
```

Pure Python algorithms use `time.process_time()` directly.

### Algorithm Contract Test Suite

Run this before merging any new or modified algorithm wrapper:

- Returns correct dict type on success
- Returns `{'embedding': {}, ...}` on failure — not `None`, not an exception
- Respects `timeout` — test with a graph that takes longer than a 0.1s timeout
- Same `seed` produces identical results on two consecutive runs
- Does not modify input graphs — hash source and target before and after `embed()`, assert unchanged
- Produces no stdout — capture stdout during `embed()` and assert empty
- If any algorithmic counters are populated: assert each is a non-negative `int` (not float, not None when present); assert counter values are consistent across two runs with the same seed

---

## Coding Standards

These are non-negotiable. Violations will be caught in code review.

### Python Rules

**No bare `except:` clauses.**
```python
# WRONG — silently swallows KeyboardInterrupt and SystemExit
try:
    result = algo.embed(...)
except:
    pass

# CORRECT
try:
    result = algo.embed(...)
except Exception as e:
    logging.error(f"Embed failed: {e}")
```

**No mutable default arguments.**
```python
# WRONG — mutates the default across all calls
def run(graphs=[]):
    graphs.append(new_graph)

# CORRECT
def run(graphs=None):
    if graphs is None:
        graphs = []
```

**No `print()` in library code.** Use `logging`. `print()` is acceptable only in top-level CLI scripts.

**No `import *`.**
```python
from networkx import Graph, DiGraph    # correct
from networkx import *                 # wrong — pollutes namespace
```

**No hardcoded paths.** Use `pathlib.Path` or `os.path.join`. `"results/myfile.csv"` breaks on Windows and when the working directory changes.

**No `tempfile.mktemp()`.** Use `NamedTemporaryFile(delete=False)`.

**Docstrings on public functions.** Include what the function raises and why if it can raise.

### Git Practices

- Work on feature branches. Never push directly to `main`.
- Branch naming: `feature/qubo-generators`, `fix/pssa-timeout`, `refactor/sqlite-pipeline`
- Commit messages must describe the change: "Fix chain validation crash on empty chains in validator.py", not "fix bug"
- Never commit: results files, `.db` files, compiled binaries, or graph library files generated during testing

### Pull Request Checklist

Before opening a PR, confirm:

- [ ] All existing tests pass: `pytest tests/ -v`
- [ ] New code has corresponding unit tests
- [ ] No `print()` statements in library code
- [ ] No bare `except:` clauses
- [ ] No mutable default arguments
- [ ] No `import *`
- [ ] Algorithm contract test suite passes (if PR touches an algorithm wrapper)
- [ ] Vendored code has license file and `SOURCE.md` with commit hash (if PR adds third-party code)
- [ ] No results files, binaries, or generated data committed

---

## Testing Strategy

### Two Levels — Do Not Conflate Them

**Unit tests (pytest):** Fast. Run on every push via CI. Test individual functions in isolation: hash verification, graph property computation, embedding validation, metric calculation, provenance logging, train/test overlap detection. Must complete in under 2 minutes.

**Smoke benchmarks:** End-to-end pipeline verification. Run manually after completing a phase or making significant runner changes. These take 5–20 minutes and require access to the full algorithm suite. Not CI.

A pytest that instantiates `EmbeddingBenchmark` and calls `.run()` on 500 graphs is wrong. pytest tests data structures, property computations, and algorithm contracts. Smoke benchmarks test the runner under real conditions.

### Smoke Benchmark Configuration

After Phase 4 (YAML config) is implemented, version-control this as `tests/smoke/smoke_benchmark.yaml`:

```yaml
experiment_name: "smoke_test"
algorithms: [minorminer, oct-fast-oct-reduce, atom]
graphs:
  selection: ["er", "qubo/tsp", "stress/near_threshold"]
  max_per_category: 8
topologies: [pegasus_16, chimera_16x16x4]
seeds: 5
timeout_seconds: 30
record_per_vertex: true
```

Run with: `ember run tests/smoke/smoke_benchmark.yaml --smoke`

This becomes a reproducible test fixture rather than an informal ad-hoc run.

### Tests Directory Structure

```
tests/
├── phase1/          # scientific integrity: hashing, CPU time, provenance, train/test split
├── phase2/          # graph library: generators, properties, planted solutions
├── phase3/          # pipeline: JSONL, SQLite, Parquet, checkpointing
├── phase4/          # config: YAML loading, fault simulation
├── phase5/          # analysis: metrics, regression, LaTeX export
├── algorithms/      # contract tests for every registered algorithm
└── smoke/
    └── smoke_benchmark.yaml
```

Test file headers reference the relevant roadmap section they cover.
