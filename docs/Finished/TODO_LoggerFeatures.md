# Logging Implementation Specification

---

## Overview

The benchmark runner must capture all algorithm output and maintain structured
logs without letting algorithm chatter reach the terminal or corrupt benchmark
progress output. Logging is split into two concerns: per-run capture (everything
an algorithm does during a single embed call) and runner-level logging (batch
lifecycle, suspensions, anomalies).

All logging infrastructure must be initialized before the first trial runs and
torn down cleanly after the batch completes, including on crash or early exit.

---

## Where Logging Lives in the Codebase

Logging should be implemented as its own module that the runner imports. It must
have no dependencies on algorithm code or validation logic. The runner calls into
this module at three points: batch start (setup), around each embed call
(per-run capture), and batch end (cleanup and retention policy). The CLI log
retrieval command also imports from this module directly.

---

## Directory Structure

The output directory for a benchmark run must contain the following layout,
created at batch start before any trials execute:

    ember_results/
    ├── results/          # database and output files — the primary deliverable
    ├── logs/
    │   ├── runs/         # one log file per (algorithm, graph_id, trial, seed)
    │   └── runner/       # one log file per batch
    └── metadata/         # benchmark config, graph inventories, algorithm versions

Directory creation must be idempotent — running twice against the same output
directory must not fail or overwrite existing results. Use `exist_ok=True`
semantics throughout.

---

## Per-Run Log Files

**Purpose:** Capture everything that happens during a single `embed()` call —
algorithm stdout, algorithm stderr, and runner diagnostics for that run.

**Naming:** Each file is uniquely identified by the tuple
`(algorithm, graph_id, trial, seed)`. The filename format should make all four
components recoverable from the filename alone without querying the database,
since logs may need to be consulted when the database is unavailable or corrupt.

**Lifecycle:** The file is opened immediately before `embed()` is called and
closed immediately after the runner has finished appending its own diagnostics.
It must be closed in a `finally` block so it is always flushed even if the
algorithm crashes or the runner raises an exception.

**What gets captured:**

- All stdout the algorithm emits during `embed()`
- All stderr the algorithm emits during `embed()`
- A runner-appended diagnostic footer after `embed()` returns, containing at
  minimum: final status, success flag, wall time, and validation failure reason
  if applicable. This footer must be clearly delimited from algorithm output so
  the two are not confused when reading the file.

**stdout/stderr redirection:** Use context manager-based redirection so that
redirection is guaranteed to be restored even if an exception occurs. The
redirection must be scoped exactly to the `embed()` call — runner progress
output before and after must not be captured.

**Important constraint:** Redirection using standard library context managers
only affects the current thread. If trials run in parallel across threads,
each thread's redirection is independent and correct. If trials run in parallel
across processes, each process has its own stdout/stderr and no special handling
is needed. Do not use global redirection approaches that would affect the runner's
own output.

---

## Runner-Level Logger

**Purpose:** Record batch lifecycle events, suspension decisions, and high-rate
anomalies. This is the authoritative record of what the runner did and why.

**One logger per batch**, named to include the batch ID so that log records from
concurrent or sequential batches are distinguishable if log files are ever
aggregated.

**Two output destinations:**

- A file handler writing to `logs/runner/{batch_id}.log` at DEBUG level — full
  detail, every event. This file is never auto-deleted.
- A stderr handler at WARNING level only — surfaces critical issues to the
  terminal in real time without cluttering normal progress output.

**Events that must be logged:**

At INFO level: batch start (with total planned run count), batch completion
(with SUCCESS/total summary), any algorithm suspension decision.

At WARNING level (goes to both file and stderr): any algorithm suspension for
high CRASH or INVALID_OUTPUT rate, any Layer 4 anomaly summary, any result
that fails validation after the algorithm claimed success.

At DEBUG level (file only): individual run completions, validation outcomes,
counter values if present.

---

## Suspension Threshold and Real-Time Surfacing

CRASH and INVALID_OUTPUT failures that exceed a rate threshold must trigger
an immediate warning to stderr, not just the log file. This ensures a systematic
bug is visible during a long benchmark run rather than discovered at the end.

The threshold check must run after every completed trial for a given
(algorithm, graph class) combination, not just at batch end. Suspension means
the algorithm is skipped for all remaining trials in that graph class — skipped
runs are recorded with status `SKIPPED` and a reason referencing the suspension.

The suspension threshold (suggested default: 10%) should be configurable at
batch start, not hardcoded, so it can be adjusted for debugging runs where
higher failure rates are expected.

---

## Log Retrieval

The runner must provide a way to retrieve the log for a specific run by its
identifying tuple without requiring the user to know the filesystem path or
naming convention. This should be accessible both programmatically (for use in
tests and tooling) and via the CLI.

The retrieval function must return a clear message if no log exists for the
requested run rather than raising a file-not-found error — log files for
successful runs are deleted by the retention policy and a missing log for a
successful run is expected, not an error.

**CLI interface:** The `ember logs` command should accept algorithm name, graph
ID, trial number, and seed as arguments and print the log contents to stdout.
If the log was deleted due to retention policy, the command should say so
explicitly rather than just reporting the file is missing.

---

## Retention Policy

The retention policy runs once after all results are written to the database
and verified. It must not run before database writes are confirmed complete —
deleting logs before results are stored would lose debugging information if
the database write fails.

**Keep indefinitely:**

- All runner-level logs (`logs/runner/`)
- Per-run logs for status `CRASH`, `INVALID_OUTPUT`, and `TIMEOUT`

These are active debugging artifacts. They must not be deleted automatically
under any circumstances.

**Delete after batch completes:**

- Per-run logs for status `SUCCESS`, `FAILURE`, `SKIPPED`, and `INVALID_INPUT`

The information from these runs is fully captured in the database. The log
files have no additional diagnostic value once results are confirmed stored.

**Deletion must be safe:** If a log file is missing at cleanup time (e.g. it
was already deleted manually), the cleanup must continue silently rather than
raising an error.

---

## What Algorithms Must Not Do

These are contract violations — the logging system is designed around the
assumption that algorithms respect these rules. Violations that bypass
redirection will corrupt benchmark output and may break parallel execution:

- **Print directly to stdout or stderr.** Any diagnostic information that must
  survive the run belongs in the `error` field of the return dict, not in print
  statements. Print statements may be silently swallowed or may corrupt runner
  output depending on execution context.
- **Configure the root logger or add handlers to it.** Algorithms may use
  `logging.getLogger(__name__)` at DEBUG level for internal diagnostics.
  Any logger configuration that affects handlers above the algorithm's own
  logger namespace will interfere with the runner's logging setup.
- **Assume their output is visible during benchmark execution.** Algorithms
  must not rely on print output for correctness — for example, printing a
  result and assuming the runner will parse it.

---

## What to Test After Implementation

**Directory initialization:**
- Running batch setup twice against the same output directory does not fail or
  overwrite existing files.
- All required subdirectories exist after setup.

**Per-run capture:**
- An algorithm that prints to stdout has that output captured in the log file
  and not visible on the terminal.
- An algorithm that raises an exception has the full traceback in the log file.
- The runner diagnostic footer is present in every log file, including crash logs.
- Log files are closed cleanly even when the algorithm crashes mid-execution.

**Runner logger:**
- INFO events appear in the runner log file but not on stderr.
- WARNING events appear in both the runner log file and on stderr.
- A simulated high CRASH rate triggers a suspension warning to stderr before
  the batch completes.

**Retention policy:**
- After a clean batch, log files for SUCCESS results are deleted.
- Log files for CRASH and INVALID_OUTPUT results are retained.
- Retention cleanup does not fail if a log file is already missing.
- Retention does not run until database writes are confirmed.

**CLI retrieval:**
- `ember logs` with a valid (algorithm, graph, trial, seed) for a retained log
  prints the log contents.
- `ember logs` for a SUCCESS run whose log was deleted prints a clear
  explanation rather than a file-not-found error.