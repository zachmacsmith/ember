# `_execute_tasks()` — Design Specification

---

## Purpose

A shared internal method that encapsulates the entire task execution loop — sequential and parallel paths, progress reporting, warning aggregation, and cancel handling. Both `run_full_benchmark()` and `load_benchmark()` call it after their respective setup phases. Neither duplicates any run loop logic.

---

## Signature

```python
def _execute_tasks(
    self,
    tasks: List[TaskTuple],       # flat list of fully-determined task tuples
    batch_dir: Path,              # batch directory, already exists on disk
    batch_logger: BatchLogger,    # already initialised by caller
    n_workers: int,
    verbose: bool,
    timeout: float,               # passed through to every benchmark_one call
    cancel_trigger: Optional[Callable] = None,  # None = default 'q' keypress listener
    elapsed_offset: float = 0.0,  # accumulated wall time from previous sessions
) -> WarningRegistry:
```

### What the caller owns (not passed in)

- Batch directory creation and `config.json` writing
- Task list construction and checkpoint filtering
- Manifest verification
- `compile_batch()` and output directory move on completion
- `resume_count` increment and checkpoint read/write
- `batch_wall_time` accumulation in `config.json`

### What `_execute_tasks` owns

- All run loop logic — sequential and parallel paths
- Timer (starts fresh internally, adds `elapsed_offset` for display)
- Warning registry — constructed internally, returned to caller
- Cancel detection and graceful shutdown
- JSONL writing
- Progress reporting
- Worker process lifecycle (parallel path only)

---

## Task Tuple Format

Each task is a fully-determined tuple carrying everything needed to execute one trial without any external lookups:

```python
(source_graph, target_graph, algo_name, problem_name, topo_name, trial, trial_seed)
```

`timeout` is not in the tuple — it is uniform across all tasks in a run and passed as a top-level parameter.

---

## Timing

`_execute_tasks` owns its own start time:

```python
_start = time.perf_counter()
```

Elapsed time shown in the progress bar:

```python
elapsed = elapsed_offset + (time.perf_counter() - _start)
```

`run_full_benchmark` passes `elapsed_offset=0.0` (the default).

`load_benchmark` reads the accumulated `batch_wall_time` from `config.json` and passes it as `elapsed_offset`. The display shows total time the benchmark has been running across all sessions, not time since the most recent resume.

On return, `_execute_tasks` returns the total elapsed time for this session as part of the `WarningRegistry` or as a second return value, so the caller can add it to `config.json`'s `batch_wall_time` accumulator correctly:

```python
# In config.json on each cancel or completion:
batch_wall_time = elapsed_offset + session_elapsed   # accumulated, not overwritten
```

---

## Warning Registry

Constructed at the start of `_execute_tasks` and returned to the caller on exit — whether exit is by completion, cancel, or crash.

Accumulated throughout execution. In the parallel path, workers pass warning signals back via the result display dict. The main process aggregates them.

Warning types accumulated inside `_execute_tasks`:

| Warning Type | Trigger |
|---|---|
| `INVALID_OUTPUT` | Layer 1 or 2 validation failure |
| `TIMING_OUTLIER` | wall_time > 10× median for (algorithm, graph class) |
| `SEED_NONDETERMINISTIC` | Same seed produced different embeddings |
| `CRASH` | Unhandled exception escaped `embed()` |
| `ALL_ALGORITHMS_FAILED` | Every algorithm failed on a graph instance |

`TOPOLOGY_INCOMPATIBLE` is not accumulated here — it is detected and added to the registry by the caller before `_execute_tasks` is called, since it is a pre-run check that does not involve the run loop.

The caller prints the end summary from the returned registry. `_execute_tasks` does not print the summary itself — it has no knowledge of whether this is a fresh run or a resume, and the summary belongs to the caller's completion phase.

---

## Progress Reporting

The progress bar and per-trial output are owned entirely by `_execute_tasks`. The caller does not print anything during execution.

**`verbose=False`:**
```
  [############################--------] 2847/4500  847s elapsed
```
Updated in-place with `\r`. No per-trial warnings printed during the run.

**`verbose=True`:**
One line per trial as it completes. Per-trial warnings printed inline. Progress bar suppressed.

Both modes write all warnings in full to the batch log via `batch_logger` regardless of verbose setting.

---

## Cancel Handling

`_execute_tasks` owns the cancel listener lifecycle:

- If `cancel_trigger=None`, starts a background thread listening for the default keypress (`q`) at entry and stops it at exit
- If `cancel_trigger` is a callable, polls it between trials / result receptions
- On cancel signal, runs the shutdown sequence and returns the warning registry to the caller
- The caller is responsible for writing the checkpoint from the returned state — `_execute_tasks` does not write the checkpoint itself

On cancel, `_execute_tasks` returns:
- The warning registry accumulated so far
- The list of unfinished tasks (tasks not yet confirmed complete) — for the caller to write to the checkpoint
- The session elapsed time — for the caller to accumulate into `batch_wall_time`

---

## Sequential Path

Iterates the task list directly. Checks the cancel flag at the start of each trial. Writes results to `{workers_dir}/worker_{pid}.jsonl` as each trial completes.

---

## Parallel Path

Builds `task_queue` and `result_queue` from the task list. Spawns `n_workers` worker processes. Main process runs the display loop reading from `result_queue`.

On cancel:
1. Stop reading from `result_queue` for display
2. Drain `result_queue` for `elapsed_offset` seconds (configurable, default 5s) to catch nearly-finished workers
3. Terminate remaining worker processes by PID
4. Wait for all processes to confirm dead
5. Inspect worker JSONL files for truncated final lines — strip any found
6. Derive unfinished tasks from full task list minus confirmed completions
7. Return to caller

`batch_id` is derived from `batch_dir.name` inside `_execute_tasks` — not passed as a separate parameter.

---

## Return Value

```python
@dataclass
class ExecutionResult:
    warning_registry: WarningRegistry
    unfinished_tasks: List[TaskTuple]   # empty on clean completion
    session_elapsed: float              # wall time for this session only
    completed_count: int
    cancelled: bool
```

The caller uses this to:
- Print the end summary (from `warning_registry`)
- Write the checkpoint (from `unfinished_tasks`, if `cancelled=True`)
- Accumulate `batch_wall_time` in `config.json` (from `session_elapsed`)
- Run `compile_batch()` and move to output directory (if `cancelled=False`)