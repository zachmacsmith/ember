"""
qebench/loggers.py
==================
Logging infrastructure for the benchmark runner.

Implemented:
  1. Per-run stdout/stderr capture — context manager wrapping each embed() call,
     writing algorithm output + a runner diagnostic footer to logs/runs/.
  2. Runner-level structured logging — batch lifecycle events written to
     logs/runner/{batch_id}.log (DEBUG) and WARNING+ surfaced to stderr.

Not yet implemented (TODO):
  - Suspension threshold: skip remaining trials when CRASH/INVALID_OUTPUT rate
    exceeds a configurable threshold. Parallel mode complicates this because
    tasks are pre-queued; a shared multiprocessing flag would be needed.
  - Retention policy: delete per-run logs for SUCCESS/FAILURE after the database
    write is confirmed. Keeps CRASH/INVALID_OUTPUT/TIMEOUT logs indefinitely.
  - CLI log retrieval: `ember logs <algorithm> <graph_id> <trial> <seed>` command
    to print a log file without knowing its filesystem path.

Import:
    from qebench.loggers import BatchLogger, capture_run, run_log_path
"""

import logging
import sys
from contextlib import contextmanager
from pathlib import Path
from typing import List, Optional


# ── List-based log handler (for buffered warning mode) ──────────────────────────

class _ListHandler(logging.Handler):
    """Accumulates log records in a list instead of writing immediately."""

    def __init__(self, level=logging.NOTSET):
        super().__init__(level)
        self.records: List[logging.LogRecord] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.records.append(record)


# ── Per-run log helpers ─────────────────────────────────────────────────────────

def run_log_path(logs_runs_dir: Path, algorithm: str, problem_name: str,
                 trial: int, seed: int) -> Path:
    """Return the path for a per-run log file.

    All four components of the identifying tuple (algorithm, problem_name, trial,
    seed) are encoded in the filename so they are recoverable without querying
    the database — useful when the database is unavailable or corrupt.
    """
    safe_algo = algorithm.replace('/', '_').replace(' ', '_')
    safe_prob = problem_name.replace('/', '_').replace(' ', '_')
    return logs_runs_dir / f"{safe_algo}__{safe_prob}__{trial}__{seed}.log"


@contextmanager
def capture_run(log_path: Path):
    """Redirect sys.stdout and sys.stderr to log_path for the duration of the block.

    Guaranteed to restore original streams even on exception. Safe for both
    sequential (main process) and parallel (worker process) use — each process
    has its own stdout/stderr, so redirection is local to the calling process
    and does not affect other workers or the main process display output.

    Usage::

        with capture_run(log_path):
            result = algo.embed(source, target, timeout=timeout)
        batch_logger.append_footer(log_path, result)
    """
    log_path.parent.mkdir(parents=True, exist_ok=True)
    orig_stdout, orig_stderr = sys.stdout, sys.stderr
    with open(log_path, 'w') as log_fh:
        sys.stdout = log_fh
        sys.stderr = log_fh
        try:
            yield log_fh
        finally:
            sys.stdout = orig_stdout
            sys.stderr = orig_stderr


# ── BatchLogger ─────────────────────────────────────────────────────────────────

class BatchLogger:
    """Runner-level structured logger for one benchmark batch.

    Handles two concerns:
    - Per-run log files: one file per (algorithm, problem_name, trial, seed)
      written to ``logs/runs/`` within the batch directory. Captures algorithm
      stdout/stderr via the ``capture_run()`` context manager, plus a runner
      diagnostic footer appended after ``embed()`` returns.
    - Runner log: ``logs/runner/{batch_id}.log`` capturing batch lifecycle events
      at DEBUG level. WARNING and above are also written to stderr so critical
      issues (e.g., repeated crashes) surface during a long run.

    Not yet implemented — see module docstring for TODO items.

    Usage::

        logger = BatchLogger(batch_dir, batch_id)
        logger.setup()
        logger.info(f"Batch {batch_id} starting")
        # ... run trials, calling log_run() after each ...
        logger.teardown()
    """

    def __init__(self, batch_dir: Path, batch_id: str):
        self.batch_dir = Path(batch_dir)
        self.batch_id = batch_id
        self.logs_runs_dir = self.batch_dir / "logs" / "runs"
        self.logs_runner_dir = self.batch_dir / "logs" / "runner"
        self._logger: Optional[logging.Logger] = None
        self._file_handler: Optional[logging.FileHandler] = None
        self._stderr_handler: Optional[logging.StreamHandler] = None
        self._list_handler: Optional[_ListHandler] = None

    def setup(self, buffered: bool = False) -> None:
        """Create log directories and configure the runner logger.

        Args:
            buffered: When True, WARNING messages are accumulated in memory
                      instead of written to stderr immediately. Call
                      flush_warning_buffer() to print them. Use this in
                      non-verbose (progress bar) mode so warnings don't
                      interleave with the \r-based bar.

        Idempotent — calling setup() twice against the same batch directory
        does not fail or overwrite existing logs.
        """
        self.logs_runs_dir.mkdir(parents=True, exist_ok=True)
        self.logs_runner_dir.mkdir(parents=True, exist_ok=True)

        # One named logger per batch so records from concurrent batches are
        # distinguishable if log files are ever aggregated. propagate=False
        # ensures we never touch the root logger or any algorithm's logger.
        logger_name = f"qebench.runner.{self.batch_id}"
        self._logger = logging.getLogger(logger_name)
        self._logger.setLevel(logging.DEBUG)
        self._logger.propagate = False

        log_file = self.logs_runner_dir / f"{self.batch_id}.log"
        self._file_handler = logging.FileHandler(log_file)
        self._file_handler.setLevel(logging.DEBUG)
        fmt = logging.Formatter(
            '%(asctime)s %(levelname)-8s %(message)s',
            datefmt='%Y-%m-%dT%H:%M:%S',
        )
        self._file_handler.setFormatter(fmt)
        self._logger.addHandler(self._file_handler)

        if buffered:
            # Collect WARNING+ in memory; caller flushes after progress bar ends
            self._list_handler = _ListHandler(level=logging.WARNING)
            self._list_handler.setFormatter(logging.Formatter('%(levelname)s: %(message)s'))
            self._logger.addHandler(self._list_handler)
        else:
            # WARNING+ goes to stderr immediately so issues are visible in real time
            self._stderr_handler = logging.StreamHandler(sys.stderr)
            self._stderr_handler.setLevel(logging.WARNING)
            self._stderr_handler.setFormatter(logging.Formatter('%(levelname)s: %(message)s'))
            self._logger.addHandler(self._stderr_handler)

    def flush_warning_buffer(self) -> None:
        """Print any buffered WARNING messages to stderr, then clear the buffer.

        No-op when not in buffered mode or when there are no warnings.
        Call this after the progress bar's final newline so warnings appear
        as a clean block below the bar rather than interleaving with it.
        """
        if not self._list_handler or not self._list_handler.records:
            return
        formatter = self._list_handler.formatter or logging.Formatter('%(levelname)s: %(message)s')
        for record in self._list_handler.records:
            print(formatter.format(record), file=sys.stderr)
        self._list_handler.records.clear()

    def teardown(self) -> None:
        """Flush and close all log handlers."""
        if self._logger:
            for h in list(self._logger.handlers):
                h.flush()
                h.close()
                self._logger.removeHandler(h)

    # ── Convenience log-level wrappers ─────────────────────────────────────────

    def info(self, msg: str) -> None:
        if self._logger:
            self._logger.info(msg)

    def warning(self, msg: str) -> None:
        if self._logger:
            self._logger.warning(msg)

    def debug(self, msg: str) -> None:
        if self._logger:
            self._logger.debug(msg)

    # ── Per-run log helpers ─────────────────────────────────────────────────────

    def run_log_path(self, algorithm: str, problem_name: str,
                     trial: int, seed: int) -> Path:
        """Return the path for a specific per-run log file."""
        return run_log_path(self.logs_runs_dir, algorithm, problem_name, trial, seed)

    def append_footer(self, log_path: Path, result) -> None:
        """Append a runner diagnostic footer to a per-run log file.

        Clearly delimited from algorithm output. Called after the capture_run()
        context manager exits so the footer is written to the file (not captured
        as algorithm output).
        """
        try:
            with open(log_path, 'a') as fh:
                fh.write('\n--- RUNNER DIAGNOSTICS ---\n')
                fh.write(f'status:    {result.status}\n')
                fh.write(f'success:   {result.success}\n')
                fh.write(f'is_valid:  {result.is_valid}\n')
                fh.write(f'wall_time: {result.wall_time:.4f}s\n')
                fh.write(f'cpu_time:  {result.cpu_time:.4f}s\n')
                if result.error:
                    fh.write(f'error:     {result.error}\n')
        except OSError:
            pass  # best-effort; never let logging break a benchmark run

    # ── Runner log events ──────────────────────────────────────────────────────

    def log_run(self, result, trial_seed: int) -> None:
        """Log a completed run. CRASH/INVALID_OUTPUT → WARNING; else DEBUG."""
        if not self._logger:
            return
        msg = (
            f"{result.algorithm} / {result.problem_name} "
            f"trial={result.trial} seed={trial_seed} "
            f"→ {result.status} wall={result.wall_time:.3f}s"
        )
        if result.status in ('CRASH', 'INVALID_OUTPUT'):
            self._logger.warning(msg + (f" | {result.error}" if result.error else ""))
        else:
            self._logger.debug(msg)

    def log_run_from_display(self, display: dict) -> None:
        """Log a completed run from a parallel-path display record.

        The display record is the lightweight dict pushed by worker processes
        onto the result queue. It must contain at minimum: algorithm,
        problem_name, trial, status, wall_time, and optionally seed and error.
        """
        if not self._logger:
            return
        msg = (
            f"{display['algorithm']} / {display['problem_name']} "
            f"trial={display['trial']} seed={display.get('seed', '?')} "
            f"→ {display['status']} wall={display['wall_time']:.3f}s"
        )
        if display['status'] in ('CRASH', 'INVALID_OUTPUT'):
            self._logger.warning(
                msg + (f" | {display['error']}" if display.get('error') else "")
            )
        else:
            self._logger.debug(msg)
