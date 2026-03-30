# Changelog

All notable changes to `ember-qc` are documented in this file.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

---

## [0.9.1] - 2026-03-30

### Added

- `verbose` is now a configurable setting. Set with `ember config set default_verbose true`
  or via the `EMBER_VERBOSE` environment variable. The CLI `ember run` command gains
  `--verbose` / `--no-verbose` flags to override the config for a single run. When not
  configured, the previous automatic behaviour is preserved: verbose when `n_workers == 1`,
  progress bar otherwise.

---

## [0.9.0] - 2026-03-29

Pre-release hardening for v1.0.0.

### Fixed

- Removed global `warnings.filterwarnings('ignore')` that silenced all warnings for
  the entire Python process on import.
- Fixed `EmbeddingBenchmark.__init__` docstring placement (was after executable code,
  not recognized as a docstring).
- Fixed `benchmark_one()` reporting `wall_time=timeout` instead of actual elapsed time
  when an algorithm returns `None`.
- Fixed `compute_embedding_metrics()` O(n²) coupler counting: replaced the nested-loop
  approach with a neighbor-intersection walk (O(n × d)), eliminating a significant
  performance bottleneck on large embeddings.
- Fixed `validate_layer2()` check ordering: chain format check now runs before
  value/type checks, preventing misleading validation failure messages.
- Fixed unsafe `.astype(bool)` on nullable SQLite columns in `compile.py` — `NaN`
  (from `NULL`) no longer silently converts to `True`.
- Fixed `validate_embedding()` in `registry.py` — now delegates to `validate_layer1()`
  with proper logging instead of duplicating logic with a bare `print()`.
- Removed emoji characters from all runner output for compatibility with terminals
  lacking Unicode support.
- Fixed `_next_batch_name()` using local time while `config.json` timestamp used UTC;
  both now use UTC consistently.
- Fixed stale comment in `cli.py` claiming PyYAML is not a declared dependency (it is).
- Fixed algorithm template: `embed()` signature now includes `timeout` parameter; docs
  clarify that returning `None` is accepted.

### Changed

- `load_benchmark()` and `delete_benchmark()` accept a `confirm: bool = True` parameter.
  When `confirm=False` (programmatic use), single-run cases proceed without prompting;
  multiple-run ambiguity raises `ValueError` instead of showing an interactive list.
- Added Python 3.9 and 3.13 to `pyproject.toml` classifiers (matches `requires-python`).

### Changed

- Added Python 3.9 and 3.13 to `pyproject.toml` classifiers (matches `requires-python`).

## [0.5.0] - 2026-03-28

Initial public release.

### Added

**Package & CLI**
- PyPI packaging under `ember-qc` with `hatchling` build backend and `src/` layout.
  Optional extras: `[analysis]` (matplotlib/seaborn/scipy), `[charme]` (PyTorch/karateclub), `[dev]` (pytest).
- `ember` CLI entry point with subcommand groups: `run`, `resume`, `graphs`, `topologies`,
  `results`, `algos`, `config`, `install-binary`, `version`.
- `ember run [experiment.yaml]` — run a benchmark from a YAML file or CLI flags.
  Writes `<name>_resolved.yaml` recording the exact parameters used.
  `--analyze` flag automatically invokes `ember-qc-analysis` post-run if installed.
- `ember resume [batch_id]` — resume an incomplete run; interactive list when no ID given.
  `--delete` / `--delete-all` subflags for cleaning up incomplete runs.
- `ember graphs list / presets` — list bundled test graphs and named presets.
  Stubs for `graphs status / fetch / cache` (Phase 2).
- `ember topologies list / info` — list registered topologies with qubit and edge counts.
- `ember results list / show / delete` — inspect and manage completed batches.
- `ember algos list [--available] [--custom] / template / dir` — list algorithms with
  availability status. Stubs for `add / remove / validate / reset`.
- `ember config show / get / set / reset / path` — full config management with coercion
  and validation.
- `ember install-binary [atom|oct]` — download and install pre-built C++ binaries from
  GitHub releases. Detects platform automatically (`linux/x86_64`, `darwin/x86_64`,
  `darwin/arm64`). Supports `--version`, `--force`, `--list`.
- `ember version` — print package version.

**Algorithm system**
- `EmbeddingAlgorithm` ABC with `is_available() -> (bool, str)` classmethod; checks
  `_requires` (pip packages) and `_binary` (file existence). `_binary` may be a `Path`,
  string, or zero-argument callable for dynamic resolution.
- `@register_algorithm` decorator injects `cls.name` and instantiates the class into
  `ALGORITHM_REGISTRY`.
- `list_algorithms()` public function.
- Individual algorithm modules under `ember_qc/algorithms/`:
  - **`minorminer.py`** — `minorminer`, `minorminer-aggressive` (tries=50),
    `minorminer-fast` (tries=3), `minorminer-chainlength` (chainlength_patience=20),
    `clique`.
  - **`atom.py`** — ATOM wrapper; binary resolved via `EMBER_ATOM_BINARY` env var or
    user data directory.
  - **`oct.py`** — 6 OCT variants via factory (`oct-triad`, `oct-triad-reduce`,
    `oct-fast-oct`, `oct-fast-oct-reduce`, `oct-hybrid-oct`, `oct-hybrid-oct-reduce`);
    `oct_based` alias for `oct-triad`.
  - **`pssa.py`** — 4 PSSA variants (`pssa`, `pssa-weighted`, `pssa-fast`,
    `pssa-thorough`) inlined from the previously editable `pssa_dwave/` package.
  - **`charme.py`** — stub with `_requires = ["torch", "karateclub"]`; gracefully
    returns failure with install instructions.
- `algorithms/_loader.py` — loads user-defined algorithms from
  `~/…/ember-qc/algorithms/` at import time; broken files log a warning and are skipped.
- Pre-run availability check in `run_full_benchmark()` raises `RuntimeError` listing
  all unavailable algorithms before any work starts.

**Graph library**
- 167 bundled test graphs across 8 categories (complete, bipartite, grid, cycle, tree,
  special, random, np_problems), stored under `src/ember_qc/graphs/library/`.
- `manifest.json` — authoritative graph descriptor (id, type, parameters, nodes, edges,
  hash, size_bytes) bundled with the package.
- `load_graph(graph_id: int)` — three-layer lookup: local cache → bundled files →
  remote download (Phase 2 stub). Verifies SHA-256 on each layer.
- `load_manifest()`, `verify_manifest()` — manifest access and integrity checking.
- `scripts/generate_manifest.py` — developer script to regenerate `manifest.json` after
  adding or modifying graphs (not part of the installed package API).
- `ember graphs fetch / cache / status` CLI stubs registered and discoverable.

**Benchmark runner**
- `run_full_benchmark()` gains `output_dir`, `cancel_delay`, `fault_rate`, `fault_seed`,
  `faulty_nodes`, `faulty_couplers` parameters.
- `_execute_tasks()` module-level function encapsulates the full run loop (sequential +
  parallel paths, progress reporting, JSONL writing, warning accumulation, cancel
  handling); shared by `run_full_benchmark()` and `load_benchmark()`.
- `ExecutionResult` dataclass returned by `_execute_tasks`.
- `batch_wall_time` written to `config.json` after all trials complete.
- Results path printed to stdout on successful completion.

**Seeding & reproducibility**
- `_derive_seed(root_seed, algorithm, problem_name, topology_name, trial)` — SHA-256
  keyed seed derivation, independent of execution order and stable across Python versions.
  Warmup seeds use negative trial indices to avoid collisions.
- Global RNG reseeding (`_reseed_globals`) before every `embed()` call seeds both
  `random` and `numpy.random` for algorithms using global state.
- Default `seed=42` — runs are reproducible out-of-the-box.

**Parallel execution**
- `n_workers` parameter on `run_full_benchmark()`; workers push tasks from a
  `multiprocessing.Queue` and write results to per-worker JSONL files.
- Cancel support: keypress listener (`select`-based) + `KeyboardInterrupt`. Parallel
  cancel drains the result queue for `cancel_delay` seconds before terminating workers.
- Worker stdin redirected to `/dev/null` to prevent TTY contention.

**Storage**
- Two-phase write: each trial appended immediately to `workers/worker_{pid}.jsonl`;
  `compile_batch()` consolidates into `results.db` after all trials complete.
- `compile_batch()` (`compile.py`) — SQLite WAL database with tables: `runs`,
  `embeddings`, `partial_embeddings`, `graphs`, `batches`, `suspensions` (stub),
  `layer4_flags` (stub). Enforces `UNIQUE(algorithm, problem_name, topology_name, trial, seed)`.
  Exports `runs.csv` for analysis package compatibility.
- `EmbeddingResult.to_jsonl_dict()` — stores embedding as a nested dict for JSONL;
  `to_dict()` stores embedding as a JSON string for CSV compatibility.
- `chain_length_std` column in the `runs` table.
- `ResultsManager.move_to_output()` — moves batch from `runs_unfinished/` to the
  configured output directory after compilation; creates/updates `latest` symlink.

**Checkpoint & resume**
- `checkpoint.py` — `write_checkpoint()`, `read_checkpoint()`, `delete_checkpoint()`,
  `completed_seeds_from_jsonl()` (strips truncated last lines from crash-killed workers),
  `scan_incomplete_runs()` (classifies each run as cancelled or crashed).
- Batch directories created in `runs_unfinished/` and only moved to `results/` after
  `compile_batch()` completes. Presence in `results/` is the sole completeness signal.
- Custom problems serialised into `config.json` under `custom_problems` so they can be
  reconstructed on resume.
- `load_benchmark(batch_id, …)` — standalone function; resumes from checkpoint (clean
  cancel) or JSONL scan (crash). Interactive discovery table when no `batch_id` given.
- `delete_benchmark(batch_id, …)` — removes incomplete runs; prints size, progress
  fraction, and cancellation time before acting; `force=True` skips confirmation.

**Validation**
- `validate_layer1(embedding, source_graph, target_graph) -> ValidationResult` — five
  structural checks in order: coverage, non-empty chains, chain connectivity, disjointness,
  edge preservation.
- `validate_layer2(result, source_graph, target_graph)` — six type/format checks: key
  validity, value validity, type correctness (rejects `numpy.int64`), chain format,
  wall-time validity, CPU-time plausibility.
- `ValidationResult` dataclass with `passed`, `check_name`, `detail`.
- Original algorithm output included in `INVALID_OUTPUT` error messages
  (e.g. `"Algorithm claimed success=True; Layer 2 [type_correctness]: …"`).

**Logging**
- `BatchLogger`, `capture_run(log_path)`, `run_log_path` in `loggers.py`.
- Per-run log files at `logs/runs/{algo}__{problem}__{trial}__{seed}.log` capturing
  stdout/stderr from each `embed()` call plus a structured footer.
- `BatchLogger` writes `logs/runner/{batch_id}.log`; WARNING+ also goes to stderr.
- Buffered `_ListHandler` suppresses mid-run WARNING interleaving with the progress bar.
- Run-level warning registry accumulates `TOPOLOGY_INCOMPATIBLE`, `INVALID_OUTPUT`,
  `CRASH`, `TIMING_OUTLIER`, `ALL_ALGORITHMS_FAILED` throughout the run.
- End-of-run summary block prints grouped warning counts; silent on clean runs.

**Timing & provenance**
- `wall_time` always runner-measured; algorithms no longer need to self-report timing.
- `cpu_time`: `RUSAGE_CHILDREN` for subprocess algorithms (ATOM/OCT); `process_time`
  for Python algorithms. `_uses_subprocess` flag on `EmbeddingAlgorithm`.
- Environment provenance written to `config.json`: `ember_version`, `python_version`,
  `platform`, `processor`, `dependencies` (pip freeze), per-algorithm versions.
- `ember_version` column in the `batches` SQLite table.

**Fault simulation**
- `simulate_faults(topology, fault_rate, fault_seed, faulty_nodes, faulty_couplers)`
  in `faults.py`. Modes: random (uniform node removal) or explicit (node/coupler lists).
  Returns a copy; validates all inputs before modification; isolated-node cleanup.
- `TOPOLOGY_DISCONNECTED` warning added to registry when faults disconnect a topology.
- `fault_simulation` key written to `config.json` recording exact removed nodes/couplers.
- `run_full_benchmark()` accepts fault params as scalars (all topologies) or dicts
  (per-topology). `fault_seed` defaults to the run master seed.

**Topology compatibility**
- `supported_topologies: Optional[List[str]]` on `EmbeddingAlgorithm`
  (default `None` = all; `AtomAlgorithm` set to `['chimera']`).
- `_algo_topo_compatible()` prefix matching; incompatible pairs skipped pre-run with
  a warning and counted in `TOPOLOGY_INCOMPATIBLE`.

**Configuration**
- `config.py` extended with five new persistent keys: `default_graphs`, `default_n_trials`,
  `default_warmup_trials`, `default_seed`, `default_fault_rate`. Full priority chain:
  CLI flag → YAML → env var → `config.json` → schema default.
- `_paths.py` — cross-platform user directory resolution using `platformdirs`.
- `runs_unfinished/` staging moved to the OS user data directory
  (`~/Library/Application Support/ember-qc/` on macOS).
- `ensure_user_dirs()` creates all user directories on import.

**EmbeddingResult fields**
- `status` field: `SUCCESS | INVALID_OUTPUT | TIMEOUT | CRASH | OOM | FAILURE`.
- `algorithm_version: str` — populated from `algo.version` on every run.
- `partial: bool`, `metadata: Optional[dict]`.
- Four optional algorithmic counters: `target_node_visits`, `cost_function_evaluations`,
  `embedding_state_mutations`, `overlap_qubit_iterations`.
- `cpu_time: float`.

**Binary installation**
- `_install_binary.py` — cross-platform downloader for C++ binaries from GitHub releases.
  Supports `linux/x86_64`, `darwin/x86_64`, `darwin/arm64`.
- Priority-based binary discovery: `EMBER_ATOM_BINARY` / `EMBER_OCT_BINARY` env var →
  user data directory. Warning messages point to `ember install-binary`.

**Developer tooling**
- `scripts/compute_graph_properties.py` — computes 25 structural graph properties and
  writes them back into graph JSON files in-place.
- `scripts/generate_manifest.py` — regenerates `manifest.json` from the graph library.
- `test_graphs_generation/` infrastructure: `generate_graphs.py` (48 graph types),
  `check_graph_feasibility.py`, `find_boundaries.py`.
- `smoke_phase1.py`, `smoke_full_pipeline.py`, `smoke_test_warnings.py`.
- Reference snapshot regression system: deterministic output columns stored in
  `tests/reference_data/smoke_reference.csv`; `UPDATE_REFERENCE=1` to refresh.

### Changed

- CLI entry point renamed from `ember-qc` to `ember`.
- `graphs.py` replaced by `load_graphs.py`; graph-generation functions removed from the
  installed package (moved to `test_graphs_generation/`).
- `load_graph(filepath)` signature changed to `load_graph(graph_id: int)` with
  three-layer lookup.
- SHA-256 `_derive_seed()` replaced the earlier `seed + trial` arithmetic and
  `random.Random` per-trial draw.
- Seed default changed from `None` to `42` — reproducible out-of-the-box.
- Wall/CPU time measurement fully owned by the runner; algorithms no longer need to
  self-report timing.
- `validate_embedding()` (bool return, no detail) replaced by `validate_layer1()` /
  `validate_layer2()` returning `ValidationResult`.
- `save_results()` simplified to summary.csv + README.md only; SQLite storage via
  `compile_batch()`.
- `latest` symlink now only updated in `move_to_output()` — always points to the most
  recently *completed* batch.
- Provenance key renamed from `qebench_version` to `ember_version` in `config.json`
  and the `batches` SQLite table.

### Fixed

- **ATOM index formula** — column count now read from `target_graph.graph['columns']`
  (with fallback); previously `max_y + 1` was always 1 short, causing every multi-row
  embedding to produce wrong qubit indices.
- **ATOM bounds check** — returns clean `FAILURE` when embedding exceeds target
  dimensions instead of `INVALID_OUTPUT` on wrong-but-valid qubit indices.
- **Binary paths** — ATOM/OCT previously resolved binaries relative to the repo working
  directory, breaking all installed-package usage. Now use priority-based discovery
  (env var → user data dir).
- **Progress bar / warning interleaving** — `BatchLogger` buffers WARNING messages during
  runs and flushes them after the progress bar's final newline.
- **Terminal freeze after parallel cancel** — `cancel_join_thread()` called immediately
  after worker termination prevents the multiprocessing queue feeder thread from hanging.
- **Keypress listener blocked on cancel** — replaced blocking `readline()` with
  `select.select` (0.5s timeout) so the thread exits promptly.
- **`run_full_benchmark()` return value on cancel** — now returns `None` (previously
  returned the staging `batch_dir`, causing `BenchmarkAnalysis` to crash on an
  incomplete directory).
- **`ember results delete`** — fixed to use `shutil.rmtree` directly; previously
  incorrectly called `delete_benchmark()` which only operates on `runs_unfinished/`.
- **NetworkX `FutureWarning`** — `nx.node_link_data` / `nx.node_link_graph` now pass
  `edges="links"` explicitly, suppressing the warning that the default will change in
  NetworkX 3.6.
- **`verify_manifest()` scope** — now called from inside `load_test_graphs()` and checks
  only the graphs selected for the current run, not the entire library.
- **PSSA missing `time` key** — all four PSSA variants now return `time` (elapsed
  seconds) in every code path, matching the algorithm contract.
- **PSSA timeout not respected** — `pssa()` now accepts a `deadline` parameter and
  checks wall time every 1000 iterations; `_PSSABase.embed()` computes and passes the
  deadline from the `timeout` kwarg, replacing the previous behaviour where the algorithm
  ran to completion regardless of timeout.

### Known Issues

- **PSSA disconnected chains** — all four PSSA variants (`pssa`, `pssa-weighted`,
  `pssa-fast`, `pssa-thorough`) return `success: False` on every test graph. Chains have
  correct qubit coverage but fail connectivity validation. Pre-existing bug in
  `_PSSABase.embed()` chain construction; not introduced by this release.
- **`ember config reset` / `ember results delete` crash in non-interactive environments**
  — `EOFError` not caught in `cmd_config_reset` and `cmd_results_delete`. Workaround:
  use `ember config set` individually or remove the config file manually.
- **`ember graphs fetch / cache / status`** — stubs only; Phase 2.
- **Custom algorithm registration** (`ember algos add / remove / validate / reset`) —
  stubs only; not yet implemented.
- **`topologies` parameter in `run_full_benchmark()`** only accepts registered topology
  name strings; custom graph objects require single-topology `EmbeddingBenchmark` usage.
