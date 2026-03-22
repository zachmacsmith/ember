# Checkpoint & Resume — Feature Specification

---

## Overview

A running benchmark can be cancelled gracefully at any point. Completed results are preserved on disk. Unfinished tasks are saved to a checkpoint file. The benchmark can be resumed later, producing a result set identical to an uninterrupted run. Batch directories are stored internally during execution and only moved to the configured output location on successful completion.

---

## Directory Structure

All batch directories live inside the package data directory until a run completes:

```
{package_data}/
├── runs_unfinished/          # all incomplete batches — running, cancelled, or crashed
│   └── batch_2026-.../
│       ├── config.json
│       ├── checkpoint.json   # present = cancelled cleanly, resumable
│       └── workers/          # no checkpoint.json = still running or crashed
└── runs_output/              # default final output location (overridable globally)
    └── batch_2026-.../       # only complete, compiled runs appear here
```

State transitions:
- **Created** → `runs_unfinished/`
- **Cancelled cleanly** → stays in `runs_unfinished/`, `checkpoint.json` written
- **Crashed** → stays in `runs_unfinished/`, no `checkpoint.json`
- **Completed** → moved to configured output directory after `compile_batch()` succeeds

The output directory is the sole location analysis tools scan. Anything there is guaranteed to be a complete, compiled run. No additional state checks required.

---

## Output Directory Configuration

Three layers of configuration in descending priority:

1. **Per-call:** `run_full_benchmark(..., output_dir="/my/path")`
2. **Global session config:** `ember set output-location /my/path` — writes to `~/.config/ember/config.json`, persists across sessions
3. **Default:** `runs_output/` inside the package data directory

The batch directory is only moved to the output location after `compile_batch()` completes successfully. A crash during compilation leaves the batch in `runs_unfinished/` without a `checkpoint.json` — distinguishable from a clean cancel.

If the output directory is on a different filesystem, `shutil.move()` handles the copy-then-delete transparently.

---

## Cancel Trigger

Configurable at `run_full_benchmark()` call time:

**Interactive mode (default):** A background thread listens for a keypress (default `q`, configurable). When detected, it sets a shared cancel flag the main process checks between trials.

**Programmatic mode:** A callable passed as `cancel_trigger`. The main process polls it periodically. Returns `True` when cancellation is requested. Allows a parent pipeline to trigger cancellation without simulating a keypress.

Workers are never aware of the cancel flag. Cancel can only fire between trials in the sequential path, or between result receptions in the parallel path.

---

## Cancel Sequence

### 1. Stop dispatching new work

**Sequential:** The main loop checks the cancel flag at the start of each trial. When set, breaks immediately without starting another trial.

**Parallel:** The main process stops the display loop and moves to shutdown. Workers continue running their current task uninterrupted.

### 2. Drain completed results

The main process drains any results that arrived in `result_queue` during or just after the cancel signal. These are legitimate completed results and must not be discarded. The drain runs for a configurable period (default 5 seconds) to catch workers that were nearly finished.

### 3. Identify unfinished tasks

**Sequential:** Derived directly from the current loop position. Any `(algo, problem, topo, trial)` combination not yet executed is unfinished.

**Parallel:** Unfinished tasks = full task list built upfront, minus tasks that produced a confirmed result during the display loop or the drain period. Tasks currently held by workers are included in unfinished — they will rerun on resume.

### 4. Terminate workers (parallel only)

Send termination signal to all worker processes that have not already exited. Wait for confirmation that all processes are dead. Only then inspect worker JSONL files for truncated final lines — a truncated final line results from an incomplete write at the moment of termination and must be stripped. The corresponding task is already in the unfinished list and will rerun cleanly on resume.

### 5. Write checkpoint

`{batch_dir}/checkpoint.json` contains:
- Unfinished task list as `(algo_name, problem_name, topo_name, trial, trial_seed)` tuples — seeds stored explicitly so resume does not depend on re-derivation or task order
- `total_tasks` and `completed_count` for display
- `cancelled_at` timestamp
- `resume_count` — incremented on each resume, starts at 0

`config.json` already holds everything else. The checkpoint does not duplicate it.

### 6. User feedback

```
Cancelled. 2,847 / 4,500 trials complete.
Checkpoint saved. Resume with: ember load
```

---

## `ember load` — Discovery and Resume

### Discovery

Scans `runs_unfinished/` and displays all incomplete batches:

```
[1]  batch_2026-03-17_14-22-01   "dense ER sweep"
     2,847 / 4,500 trials complete   resumed 0×   cancelled 14 min ago

[2]  batch_2026-03-15_09-11-44   "chimera stress test"
     120 / 600 trials complete    resumed 1×   cancelled 2 days ago

[3]  batch_2026-03-14_08-00-12   "BA sweep"
     ✗ no checkpoint — crashed or still running   340 JSONL lines on disk
```

Crashed batches (no `checkpoint.json`) are shown with a warning and a line count from the worker JSONL files as a rough progress indicator. The user can still attempt to resume them — the resume logic handles this case.

If only one incomplete run exists, it is selected automatically with a confirmation prompt.

### Resume execution

`resume_benchmark(batch_dir)` — also callable as `ember load` from the CLI:

1. Reads `config.json` to reconstruct benchmark parameters
2. Reads `checkpoint.json` for the unfinished task list — if no checkpoint exists (crashed run), derives unfinished tasks by comparing all expected `(algo, problem, topo, trial_seed)` combinations against completed results found in worker JSONL files
3. Re-verifies the SHA-256 graph manifest — raises an error if any graph file has changed since the checkpoint was written, since different graphs would produce non-comparable results
4. Runs only the unfinished tasks, appending to existing worker JSONL files
5. Increments `resume_count` in the checkpoint at start of resume
6. On completion, runs `compile_batch()` over all worker JSONL files — both original and resumed — deduplicating by `(algo, problem, topo, trial_seed)` key to handle any edge case where a worker completed and wrote its result just before termination
7. Deletes `checkpoint.json` on successful compile
8. Moves batch directory to configured output location

---

## Invariants

- Completed results are written to JSONL before the cancel flag is acted on — no completed result is ever lost
- Resumed runs produce bitwise-identical results to uninterrupted runs — seeds are stored in the checkpoint rather than re-derived, so task order on resume does not affect results
- Anything in the output directory is a complete, compiled run — the directory location is the sole completeness signal
- Tasks in-flight at cancel time are rerun on resume — any duplicate JSONL lines produced if a worker completed just before termination are deduplicated at compile time
- A batch in `runs_unfinished/` with no `checkpoint.json` is either still running or crashed — `ember load` handles both and distinguishes them in the display


Current Implementation vs. Future CLI
In the current implementation, resume is exposed as a Python function:
pythonfrom qebench import load_benchmark

# With a specific batch directory — skips the selection prompt
load_benchmark("batch_2026-03-17_14-22-01")

# Without an argument — lists all incomplete runs and prompts for selection
load_benchmark()
load_benchmark() validates the argument against runs_unfinished/ and raises a clear error if the batch ID doesn't exist or is already complete.
When no argument is passed, it prints the discovery table and accepts a selection by number from input(). This is intentionally simple — no curses UI, no interactive menus. A number typed at the prompt is sufficient.
Future: When EMBER becomes a pip-installable package with a CLI entry point, load_benchmark() becomes callable as ember load [batch_id] from the terminal. The underlying logic is identical — the CLI is a thin wrapper over the same function. This should be kept in mind during implementation: load_benchmark() should not assume it is being called from an interactive Python session, so all output should go through print() rather than any notebook-specific display mechanism, and it should return the batch directory path so a CLI wrapper can use it without re-parsing stdout.