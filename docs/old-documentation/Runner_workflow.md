# Runner Workflow

How `run_full_benchmark()` works from call to stored results.

---

## Overview

```
EmbeddingBenchmark.run_full_benchmark()
    │
    ├── Setup: config.json, batch dir, BatchLogger
    │
    ├── Sequential path (n_workers=1)          Parallel path (n_workers>1)
    │       │                                          │
    │   per trial:                              per worker process:
    │   _reseed_globals(trial_seed)             _reseed_globals(trial_seed)
    │   capture_run(log_path)                   capture_run(log_path)
    │   benchmark_one()                         benchmark_one()
    │   → EmbeddingResult                       → JSONL + display record
    │   → JSONL                                        │
    │                                           main: display loop
    │
    ├── compile_batch()      JSONL → SQLite results.db + runs.csv
    ├── save_results()       summary.csv + README.md
    └── returns batch_dir
```

---

## Stage 1 — Setup

`run_full_benchmark()` begins before any embedding runs:

1. **Manifest check** — `verify_manifest()` hashes every graph file in `test_graphs/`
   against the stored SHA-256 manifest. Raises `RuntimeError` if any file has changed.
   Silently skipped if the manifest doesn't exist yet.

2. **Resolve topology** — builds `topo_list` of `(name, nx.Graph, label)` tuples from
   either `topologies=['chimera_4x4x4', ...]` (registry lookup) or the `target_graph`
   passed to `__init__`.

3. **Resolve graphs** — loads `(name, nx.Graph)` pairs from `test_graphs/` using the
   selection string (e.g. `"1-60"`, `"*"`), or uses the `problems` list if passed directly.

4. **Resolve algorithms** — filters `methods` against `ALGORITHM_REGISTRY`. Unknown
   names are skipped with a warning.

5. **Create batch directory** — `ResultsManager.create_batch()` makes
   `results/batch_YYYY-MM-DD_HH-MM-SS/`, writes `config.json` with:
   - algorithms, graph selection, topologies, n_trials, timeout, n_problems
   - provenance: Python version, platform, pip freeze, qebench version, timestamp
   - `results/latest` symlink updated to point here

6. **Create `workers/` directory** and initialise `BatchLogger` (creates
   `logs/runs/` and `logs/runner/<batch_id>.log`).

7. **Print header** and start `_batch_start = time.perf_counter()`.

---

## Stage 2 — Per-trial execution

### Sequential path (`n_workers=1`)

Outer loop: topology → problem → algorithm → trial.

For each **warm-up trial**:
```
warmup_seed = _derive_seed(root_seed, algo, problem, topo, -(w+1))
_reseed_globals(warmup_seed)
benchmark_one(...)           # result discarded
```

For each **measured trial**:
```
trial_seed = _derive_seed(root_seed, algo, problem, topo, trial)
_reseed_globals(trial_seed)
with capture_run(log_path):
    result = benchmark_one(...)
batch_logger.append_footer(log_path, result)
batch_logger.log_run(result, trial_seed)
result → self.results
result.to_jsonl_dict() + seed + batch_id → workers/worker_<pid>.jsonl
```

Progress: `verbose=True` prints one line per trial; `verbose=False` shows a
`[####----] N/N  Xs elapsed` progress bar updated with `\r`.

### Parallel path (`n_workers>1`)

Warm-up is skipped entirely (not compatible with pre-queued tasks).

All tasks are built upfront as a flat list and enqueued. Seeds are derived before
spawning — each worker gets a fully determined `(source, target, algo, timeout,
problem, topo, trial, trial_seed)` tuple, so task order doesn't affect results.

Each worker process (`_worker_process`):
```
_reseed_globals(trial_seed)
with capture_run(log_path):
    result = benchmark_one(...)
append footer to log_path
result.to_jsonl_dict() → workers/worker_<pid>.jsonl  (append)
lightweight display dict → result_queue
```

Main process runs a display loop reading from `result_queue` until all tasks
complete, then calls `p.join()` on all workers. After join, reconstructs
`self.results` by re-reading all worker JSONL files.

---

## Stage 3 — `benchmark_one()` (the atomic unit)

Called once per trial. Never touches the filesystem — pure in-memory.

```
1. Look up algo from ALGORITHM_REGISTRY
2. Compute problem metadata (n_nodes, n_edges, density)
3. Start cpu timer:
       process_time()  for Python algorithms
       RUSAGE_CHILDREN for subprocess algorithms (_uses_subprocess=True)
4. algo.embed(source_graph, target_graph, timeout=timeout, seed=trial_seed, ...)
5. Compute cpu_elapsed from timer
6. Handle None return → FAILURE
7. validate_layer2(result, source, target)
       fails → INVALID_OUTPUT (type/format errors caught here)
8. Infer claimed_success from result.get('success') or non-empty embedding
9. If claimed_success and embedding present:
       validate_layer1(embedding, source, validation_target)
           passes → status=SUCCESS, compute metrics
           fails  → status=INVALID_OUTPUT
   elif partial=True:
       status=TIMEOUT, preserve embedding for diagnostics
   else:
       status = result.get('status', 'FAILURE')
10. compute_embedding_metrics() on validated embedding:
        chain_lengths, avg_chain_length, max_chain_length,
        total_qubits_used, total_couplers_used
11. Build and return EmbeddingResult dataclass
```

**What the runner reads from the algorithm's return dict:**

| Key | Used for | Default if absent |
|-----|----------|-------------------|
| `'embedding'` | validation + metrics | `{}` treated as failure |
| `'time'` | `wall_time` on result | `0.0` — silent, no warning |
| `'success'` | infer success | inferred from embedding non-emptiness |
| `'status'` | failure status label | `'FAILURE'` (or `'TIMEOUT'` if partial) |
| `'partial'` | preserve diagnostic embedding | `False` |
| `'error'` | error message | status string |
| `'metadata'` | pass-through dict | `None` |
| four counters | pass-through to result | `None` |

**What the runner does NOT read from the algorithm:**
- `'cpu_time'` — always measured externally by the runner
- `'is_valid'`, `'chain_length_std'`, `'qubit_overhead'` — always computed by runner

**Exceptions:** any unhandled exception from `embed()` is caught at the outer
`try/except Exception` and produces `status='CRASH'` with the exception string
as `error`. `SystemExit` and `KeyboardInterrupt` are not caught and will propagate.

---

## Stage 4 — Per-trial logging

Two independent log outputs per measured trial:

**Per-run log** (`logs/runs/<algo>__<problem>__<trial>__<seed>.log`):
- `capture_run()` redirects `sys.stdout` and `sys.stderr` to this file for the
  entire duration of the `embed()` call. Any `print()` inside the algorithm lands
  here, not on the terminal.
- After `capture_run()` exits, the runner appends a `--- RUNNER DIAGNOSTICS ---`
  footer with status, success, is_valid, wall_time, cpu_time, and error.

**Runner log** (`logs/runner/<batch_id>.log`):
- DEBUG: every completed run with algo, problem, trial, seed, status, wall_time.
- WARNING: CRASH and INVALID_OUTPUT runs (also echoed to stderr in real time).

---

## Stage 5 — `compile_batch()`

Reads all `workers/worker_*.jsonl` files and consolidates into `results.db` (SQLite).

**Schema:**

| Table | Contents |
|-------|----------|
| `batches` | One row per batch: run counts, config JSON, provenance |
| `graphs` | One row per unique problem graph (name, nodes, edges, density) |
| `runs` | One row per trial: all metrics, status, seed, timestamps |
| `embeddings` | One row per SUCCESS: embedding JSON, n_chains, qubits |
| `suspensions` | Reserved for future suspension-threshold feature |
| `layer4_flags` | Reserved for future statistical batch checks |

**`runs` UNIQUE constraint**: `(algorithm, problem_name, topology_name, trial, seed)` —
duplicate records from a re-run of compile are silently skipped.

**`chain_length_std`** is computed by compile from the `chain_lengths` list in each
JSONL record (using `statistics.stdev`). It is not stored on `EmbeddingResult`.

**Indexes** built after insert: `batch_id`, `(algorithm, problem_name)`, `status`,
`problem_name`. `ANALYZE` is run to update query planner statistics.

After inserting, the `batches` row is updated with final counts
(n_success, n_timeout, n_crash, n_invalid_output, n_failure).

**`runs.csv`** is exported from SQLite for backward compatibility with qeanalysis.

---

## Stage 6 — `save_results()`

Writes two human-readable files into the batch root:

- **`summary.csv`** — grouped averages ± std dev per (algorithm, problem, topology):
  wall_time, avg_chain_length, max_chain_length, total_qubits_used, success_rate,
  valid_rate. Superseded by the richer `qeanalysis` output but kept for quick inspection.

- **`README.md`** — batch overview: settings table, success/valid counts, mean timing
  and chain length, file inventory.

---

## Stage 7 — Wall time and teardown

```
batch_wall_time = time.perf_counter() - _batch_start
print("Benchmark complete! Total wall time: Xs (Xm Xs)")
config['batch_wall_time'] = round(batch_wall_time, 3)
config.json rewritten with wall time added
compile_batch(batch_dir)
batch_logger.teardown()
save_results(...)
return batch_dir
```

The returned `batch_dir` path can be passed directly to `qeanalysis`:

```python
batch_dir = bench.run_full_benchmark(...)
from qeanalysis import BenchmarkAnalysis
BenchmarkAnalysis(batch_dir).generate_report()
```

---

## Seed derivation

Every trial seed is derived deterministically:

```python
key = f"{root_seed}:{algorithm}:{problem_name}:{topology_name}:{trial}"
trial_seed = int.from_bytes(hashlib.sha256(key.encode()).digest()[:4], 'big')
```

- Independent of execution order — safe for parallel dispatch
- Stable across Python versions (SHA-256, not `hash()`)
- Warm-up trials use negative trial indices: `trial = -(w+1)`
- The 32-bit result is used for both `_reseed_globals()` and `kwargs['seed']`

`_reseed_globals(trial_seed)` is called before every `embed()` invocation (warm-up
and measured, sequential and parallel). It seeds `random.seed()` and
`numpy.random.seed()` so algorithms using global RNGs without explicit seeding still
produce deterministic results.

---

## Batch directory layout

```
results/batch_YYYY-MM-DD_HH-MM-SS/
├── config.json          settings + provenance + batch_wall_time
├── results.db           SQLite: batches, graphs, runs, embeddings
├── runs.csv             runs table exported for qeanalysis
├── summary.csv          grouped averages (quick inspection)
├── README.md            human-readable batch overview
├── workers/
│   ├── worker_<pid>.jsonl   per-process durable record (one line per trial)
│   └── ...
└── logs/
    ├── runner/
    │   └── <batch_id>.log   batch lifecycle events (DEBUG + WARNING→stderr)
    └── runs/
        └── <algo>__<problem>__<trial>__<seed>.log   per-trial stdout/stderr capture
```

`results/latest` symlinks to the most recent batch directory.
