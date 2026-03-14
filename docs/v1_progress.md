# Version 1 Progress Log

Reverse-chronological. One entry per session or logical unit of work.

---

**2026-03-14 — qeanalysis: intersection comparison chart + max chain length additions**
- **`overall_summary()` in `qeanalysis/summary.py`** — added `max_chain_std` column alongside the existing `max_chain_mean`. Both are computed over successful trials only; NaN when no successes.
- **`plot_graph_indexed_chain()` in `qeanalysis/plots.py`** — added `metric` parameter (default `'avg_chain_length'`). Fully backward compatible. When `metric='max_chain_length'`, saves as `max_chain_length.png`. NaN rows (pre-SQLite batches without `max_chain_length`) are silently dropped before plotting. Internal helper `_draw_chain_dots_categorical` updated with the same `metric` param.
- **`plot_max_chain_distribution()`** — new function in `plots.py`. Overlaid KDE of `max_chain_length` per algorithm. Same structure as `plot_chain_distribution()`; saves to `figures/distributions/max_chain_length_kde.png`. Gracefully degrades to empty plot if column absent.
- **`plot_intersection_comparison(df, algo_a, algo_b)`** — new function in `plots.py`. Saves to `figures/pairwise/intersection_{A}_vs_{B}.png`. Grouped bar chart for five metrics: `avg_chain_length`, `max_chain_length`, `wall_time`, `total_qubits_used`, `qubit_overhead_ratio`. Each metric normalised to the better algorithm's intersection value (1.0 = equal, > 1.0 = worse). Ghost bars (alpha=0.22, same colour) rendered behind solid bars to show unfiltered means across all successful runs — makes the skew effect from filtering visible. Raw values annotated on solid bars (rotated 45°, compact format). Reference dashed line at 1.0. Bottom annotation shows intersection N and per-algo success counts. Degrades gracefully to empty plot if no shared data.
- **`generate_report()`** — now generates 12 graph-indexed plots (4 metrics × 3 x_modes, up from 9) and 1 `max_chain_length_kde.png`; calls `plot_intersection_comparison` for every algorithm pair.
- **Smoke test** updated: `EXPECTED_FIGURES` now includes `distributions/max_chain_length_kde.png`, 3 × `graph_indexed/*/max_chain_length.png`, and 3 × `pairwise/intersection_*_vs_*.png`. Check count rises from 62 to 70.
- 245/245 `test_qebench.py` + `test_qeanalysis.py` tests pass.

**2026-03-14 — qeanalysis: remove shared_graph_filter from graph-indexed chain plot**
- `plot_graph_indexed_chain()` previously filtered to only graphs where all algorithms succeeded before plotting, to avoid "unfair" comparisons. Removed this filter entirely. Absence of an algorithm at a given x-position is itself the signal — algorithms that fail on harder/larger graphs simply won't appear there, which is the key comparative insight. Updated docstring and titles accordingly.
- `BenchmarkAnalysis._write_report_md()` updated to reflect the new description.
- 82/82 unit tests continue to pass.

**2026-03-14 — qeanalysis: smoke test output structure fixes**
- `tests/smoke_full_pipeline.py` rewrote `EXPECTED_FIGURES` from 8 flat names to 25 subdir-qualified paths matching the actual subdirectory layout (`distributions/`, `scaling/`, `pairwise/`, `success/`, `topology/`, `graph_indexed/{by_graph_id,by_n_nodes,by_density}/`).
- Added `EXPECTED_STATS` list for `statistics/` outputs (`significance_tests.csv`, `friedman_test.txt`, `correlation_matrix.csv`, `win_rate_matrix.csv`).
- Updated `EXPECTED_TABLES` filenames and CHECK 6 to use `summary_dir` / `statistics_dir` / `report.md` rather than the old `tables/README.md` names.
- Fixed `chain_length_by_category.png` → `avg_chain_length_by_category.png` (plot function generates the metric-prefixed filename).
- 62/62 smoke checks pass.

**2026-03-14 — qeanalysis overhaul: graph-indexed plots, new output structure, filters**
- **`qeanalysis/filters.py`** — new module. `shared_graph_filter(df, algorithms)` returns rows where every specified algorithm has ≥1 success per graph. Used for fair multi-algorithm comparisons.
- **`qeanalysis/plots.py`** — major additions:
  - Colorblind-safe palette (`sns.color_palette('colorblind', 6)`) + per-algo marker shapes; both built once and passed to all plots for cross-figure consistency.
  - **Graph-indexed dot plots** (3 functions × 3 x_modes = 9 new plots): `plot_graph_indexed_chain`, `plot_graph_indexed_time`, `plot_graph_indexed_success`. x_modes: `by_graph_id` (categorical, section labels by graph category), `by_n_nodes` (numeric, deterministic jitter), `by_density` (numeric). Shows per-trial dots + per-graph mean diamonds.
  - `plot_win_rate_matrix()` — heatmap of pairwise win rates between algorithms.
  - `plot_success_heatmap()`, `plot_success_by_nodes()`, `plot_success_by_density()` — success rate visualisations.
  - Fixed category label coordinate bug in `_draw_chain_dots_categorical`: was using data y-coordinate with the axes transform; replaced with fixed axes coordinate `1.02`.
  - All plot functions write to subdirectories within `figures/` (`distributions/`, `scaling/`, `pairwise/`, `success/`, `topology/`, `graph_indexed/`).
- **`qeanalysis/__init__.py`** — `generate_report()` rewritten: `summary/` replaces `tables/`; new `statistics/` directory for significance tests + Friedman + correlation; palette computed once and passed to all plots; `report.md` replaces `README.md`; `_write_report_md()` documents every output file.
- **`qebench/compile.py`** — added `chain_length_std` column to `runs` table (computed from the `chain_lengths` list via `statistics.stdev`); added `ALTER TABLE` migration for existing DBs that predate this column.
- **Tests** updated: fixture writes `results.db` via `pandas.to_sql`; directory/file assertions updated for new `summary/`/`statistics/` layout.

**2026-03-14 — qeanalysis loader: SQLite as primary source**
- `qeanalysis/loader.py` rewritten to read from `results.db` (SQLite) as the primary source, falling back to `runs.csv` for legacy batches. Eliminates the CSV round-trip and aligns with the `compile_batch()` pipeline.
- `_load_from_db(db_path, batch_id)`: reads `runs` table filtered by `batch_id` via `pd.read_sql_query`; coerces `success`, `is_valid`, `partial` INTEGER columns to Python `bool`.
- `_load_config_from_db(db_path, batch_id)`: reads `config_json` from the `batches` table as a fallback when `config.json` is absent.
- Test fixture updated to write `results.db` (SQLite) so integration tests exercise the new path. Fixed stale column names in fixture (`embedding_time` → `wall_time`, `error_message` → `error`). Added `test_load_batch_reads_sqlite` asserting correct row count and bool dtype.
- 243/243 tests pass.

**2026-03-14 — Expand test suite to 163 tests covering all v1 features**
- Added 79 new tests across 10 new test classes in `tests/test_qebench.py`:
  - **`TestDeriveSeed`** — determinism, per-trial uniqueness, 32-bit range, warmup index isolation.
  - **`TestValidationResult`** — `bool()` protocol, field defaults.
  - **`TestValidateLayer1`** — unit test for each of 5 structural checks, check ordering (stops at first failure).
  - **`TestValidateLayer2`** — unit test for each of 6 type/format checks including `numpy.int64` detection, tuple chains, NaN/zero/negative wall time, CPU plausibility.
  - **`TestValidationIntegration`** — `benchmark_one()` produces correct status + error message format (`Layer X [check] + original claim`) for both layers.
  - **`TestBatchLogger`** — directory setup idempotency, runner log content, per-run log naming, `capture_run()` redirect + exception safety, footer fields, WARNING routing for `INVALID_OUTPUT`.
  - **`TestCompileBatch`** — `results.db` schema (runs/embeddings/graphs/batches tables), seed stored in DB, UNIQUE constraint prevents duplicates, `runs.csv` export.
  - **`TestSeedingBehavior`** — seed in JSONL, distinct per-trial, deterministic across runs.
  - **`TestMultiprocessing`** — correct result count, DB storage, seeds match sequential, warmup-skipped warning.
  - **`TestEmbeddingResultSpec`** — status values, `algorithm_version`, `cpu_time`, counter defaults, `to_jsonl_dict` (nested dict embedding) vs `to_dict` (JSON string embedding).
  - **`TestNewModuleImports`** — `validate_layer1/2`, `ValidationResult`, `BatchLogger`, `capture_run`, `compile_batch`, `_derive_seed` all importable.
- 163/163 tests pass.

**2026-03-14 — benchmark wall time measurement**
- `run_full_benchmark()` in `qebench/benchmark.py` measures total batch wall time with `time.perf_counter()`. Timer starts just before the first trial runs.
- Sequential path (`n_workers=1`, `verbose=False`): `\r` progress bar with elapsed time shown during the run (identical pattern to the parallel path).
- Both paths: after all trials complete, prints a separator and `Total wall time: X.Xs (Nh Mm Ss)` human-readable summary.
- `batch_wall_time` (rounded to 3 decimal places) is written back to `config.json` after runs complete and before `compile_batch()` runs, so it is available to `qeanalysis` via the loaded config.

**2026-03-14 — Layer 2 type/format validation + original-output logging + validation test script**
- **`validate_layer2(result, source_graph, target_graph)`** added to `qebench/validation.py`. Six checks in order (stops at first failure): (1) key validity — no extra/missing source-graph keys in embedding; (2) value validity — all chain qubits exist in target graph; (3) type correctness — embedding keys and chain values are plain Python `int` (`type(x) is int`, not `isinstance`, so `numpy.int64` is rejected); (4) chain format — chains are `list` objects (not set/tuple/ndarray); (5) wall time validity — if `result['time']` present, must be a positive finite float; (6) CPU time plausibility — if `result['cpu_time']` present, must be ≥0 and ≤ `wall_time × os.cpu_count()`.
- **Runs before Layer 1** on every result, even failures. Type errors would cause Layer 1 to raise exceptions rather than return a clean INVALID_OUTPUT.
- **Original-output logging**: when Layer 2 or Layer 1 flags a result, the error message includes what the algorithm originally claimed — e.g. `"Algorithm claimed success=True, embedding_size=10; Layer 2 [type_correctness]: ..."`. This appears in both the per-run log footer and the runner WARNING log line.
- **`tests/test_validation_layers.py`** — new runnable test script. Registers 8 mock algorithms (MockValid + 7 invalid variants), runs a single batch against a hand-crafted 6-node target graph + K3 source, then asserts each result has the expected status and check name. All 8 assertions pass. Batch is written with `batch_note="testingValidationLayers1_2"` for manual inspection of log files.
- **3 stale tests updated** in `tests/test_qebench.py` — `test_results_saved_to_json` → `test_results_saved_to_db` (queries SQLite); `test_runs_csv_excludes_embeddings` → uses `run_full_benchmark` (compile_batch path); `test_runs_json_includes_embeddings` → `test_worker_jsonl_includes_embeddings` (reads worker JSONL).
- 84/84 `test_qebench.py` tests pass.
- **Not yet implemented** (deferred): Layer 3 (consistency — success↔embedding, counter types, valid status strings); Layer 4 (batch-level statistical checks). See `TODO_OutputValidation.md`.

**2026-03-14 — Layer 1 structural validation (`qebench/validation.py`)**
- **`qebench/validation.py`** — new module (no deps on algorithm code). Exports `validate_layer1(embedding, source_graph, target_graph) -> ValidationResult`. `ValidationResult` is a dataclass with `passed: bool`, `check_name: str | None`, `detail: str | None`.
- **Five checks in order** (stops at first failure): (1) coverage — every source vertex has a chain; (2) non-empty chains — every chain has ≥1 target node; (3) connectivity — every chain forms a connected subgraph of target (BFS, no subgraph object created); (4) disjointness — no target qubit in >1 chain (reverse-map dict, O(1) collision detection); (5) edge preservation — every source edge has a corresponding target edge between chains (O(e) via neighbor iteration into chain_v set).
- **Failure detail flows to `result.error`**: on INVALID_OUTPUT from Layer 1, error is set to `"Layer 1 [{check_name}]: {detail}"` (e.g. `"Layer 1 [disjointness]: target qubit 42 appears in chains for source vertex 3 and 7"`). `batch_logger.log_run()` logs this at WARNING automatically.
- **Replaced `validate_embedding()`** in `benchmark_one()` — old function returned `bool` only with no detail and swallowed exceptions silently. New module returns structured result; `validate_embedding` import removed from `benchmark.py`.
- **Not yet implemented** (deferred — see `TODO_OutputValidation.md`): Layer 2 (type/format — numpy int keys, tuple chains, NaN wall time, CPU plausibility; must run before Layer 1); Layer 3 (consistency — success↔embedding, counter types, valid status strings); Layer 4 (batch-level statistical checks).
- 38/38 smoke checks pass.

**2026-03-14 — Per-run log capture + runner logger (`qebench/loggers.py`)**
- **`qebench/loggers.py`** — new module (no deps on algorithm or validation code). Exports `BatchLogger`, `capture_run`, `run_log_path`.
- **`capture_run(log_path)`** — context manager that redirects `sys.stdout` and `sys.stderr` to a per-run log file for the duration of each `embed()` call. Restores original streams in `finally`. Safe for both sequential and parallel (per-process) use.
- **Per-run log files** written to `logs/runs/{algo}__{problem}__{trial}__{seed}.log`. Filename encodes all four identifying components. A runner diagnostic footer (status, success, wall_time, error) is appended after `embed()` returns, clearly delimited from algorithm output.
- **`BatchLogger`** — one instance per batch. Writes `logs/runner/{batch_id}.log` at DEBUG (every run completion). WARNING+ also goes to stderr so crashes/invalid-output runs surface in real time. `propagate=False` — never touches the root logger.
- **Integrated into both execution paths**: sequential wraps each measured trial with `capture_run()` + `log_run()`; parallel workers do their own capture+footer, display loop calls `log_run_from_display()`.
- **Not yet implemented** (deferred — see `TODO_LoggerFeatures.md`): suspension threshold / SKIPPED status; retention policy (delete SUCCESS logs after DB write); `ember logs` CLI retrieval. Suspension in parallel mode requires a shared multiprocessing flag and is non-trivial.
- 38/38 smoke checks pass.

**2026-03-14 — Multiprocessing + SHA-256 seed derivation**
- **`n_workers` parameter** added to `run_full_benchmark()` (default 1). When `n_workers > 1`, a flat task list is pushed onto a `multiprocessing.Queue`; N worker processes each pull tasks and append results to their own `workers/worker_{pid}.jsonl`. Warmup trials are skipped with a warning in parallel mode.
- **Display record pattern:** workers never print. Each worker pushes a lightweight completion record (algorithm, problem, trial, status, wall_time, avg_chain_length) onto a `result_queue`; the main process reads it and drives all output — verbose per-trial lines when `verbose=True`, an ASCII progress bar otherwise. `verbose` defaults to `True` for `n_workers=1` and `False` for `n_workers>1`.
- **SHA-256 seed derivation:** replaced `random.Random` RNG with `_derive_seed(root_seed, algorithm, problem_name, topology_name, trial)` — each task's seed is keyed on the full task identity via SHA-256, so seeds are independent of execution order and stable across Python versions. Warmup seeds use negative trial indices to avoid collisions with measured trials.
- **`self.results` reconstruction:** after workers join, the parallel path reads all `worker_*.jsonl` files and reconstructs `EmbeddingResult` objects so `save_results()` / `summary.csv` / `README.md` work unchanged.
- Reference snapshot regenerated for new SHA-256 seed values; 38/38 smoke checks pass.

**2026-03-14 — SQLite-backed storage with per-worker JSONL files**
- **Two-phase write pattern:** each measured trial is appended to `workers/worker_{pid}.jsonl` immediately after completion (no locking needed — one file per process). After all trials complete, `compile_batch()` consolidates all JSONL files into `results.db`.
- **`qebench/compile.py`** — new module, exports `compile_batch(batch_dir)`. Reads `workers/worker_*.jsonl`, creates `results.db` (SQLite, WAL mode) with tables: `runs`, `embeddings`, `partial_embeddings`, `graphs`, `batches`, `suspensions` (stub), `layer4_flags` (stub). Inserts per worker file in a single transaction, enforces a `UNIQUE(algorithm, problem_name, topology_name, trial, seed)` constraint, builds indexes and runs `ANALYZE` after all inserts. Also exports `runs.csv` from SQLite for backward compatibility with `qeanalysis`.
- **`EmbeddingResult.to_jsonl_dict()`** — new method. Stores embedding as a nested dict (`{"0": [q1, q2], ...}`) rather than a JSON string, and includes `chain_lengths` as a plain list. JSONL records are augmented with `seed` and `batch_id` at write time.
- **`results.py` simplified** — `save_results()` now only writes `summary.csv` and `README.md`; `_save_runs_csv()` and `_save_runs_json()` removed (superseded by `compile_batch()`).
- **Smoke test updated** — CHECK 2 verifies `results.db` and `workers/` exist; CHECK 3 queries SQLite directly (row count, `PRAGMA table_info`, status validity, `embeddings`/`graphs`/`batches` table counts); CHECK 7 reference comparison reads from SQLite rather than `runs.csv`. Parquet telemetry is a documented stub — algorithms do not yet emit per-stage data.
- 38/38 smoke checks pass; regression detection verified by corrupting `avg_chain_length` in the reference snapshot and confirming the exact row/column/value is reported.

**2026-03-13 — RNG-based seeding + default seed=42 fallback**
- `run_full_benchmark()` default changed from `seed=None` to `seed=42` — runs are reproducible out-of-the-box without the caller having to think about it.
- Replaced `seed + trial` arithmetic with a `random.Random(seed)` RNG: each `benchmark_one()` call draws an independent `randint(0, 2**31-1)` from the RNG, so every (problem, algorithm, topology, trial) gets a truly distinct seed while the full run remains reproducible from the master seed.
- All MinorMiner wrapper variants changed `kwargs.get('seed', None)` → `kwargs.get('seed', 42)` so direct calls to `algo.embed()` without a seed also default to deterministic behaviour.
- Reference snapshot regenerated to reflect the new per-call seed sequence.

**2026-03-13 — Full pipeline smoke test + reference snapshot regression system**
- `tests/smoke_full_pipeline.py` rewritten to use the complete pipeline (`EmbeddingBenchmark.run_full_benchmark()` → `ResultsManager` → `BenchmarkAnalysis.generate_report()`), not just `benchmark_one()` directly.
- **Seeded runs:** `run_full_benchmark()` accepts `seed: int = 42`; a `random.Random` RNG draws an independent seed for every `benchmark_one()` call. OCT randomised variants (`fast-oct`, `hybrid-oct`, `-reduce` forms) forward the seed via the `-s` CLI flag (replacing hardcoded `42`). `qeanalysis/` renamed `embedding_time` → `wall_time` throughout (loader, summary, plots, statistics, \_\_init\_\_).
- **Reference snapshot:** deterministic columns (success, status, chain lengths, qubits, etc.) stored in `tests/reference_data/smoke_reference.csv`. Every subsequent smoke run compares against this snapshot — catches silent regressions in embedding logic.
- **Snapshot update flow:** set `UPDATE_REFERENCE = True` in the file, or run with `UPDATE_REFERENCE=1 conda run -n minor python tests/smoke_full_pipeline.py`. Reset the flag before committing.
- Smoke test: 6 graphs × 3 algorithms × 2 topologies × 2 trials = 72 runs; 32/32 checks pass including reference comparison.

**2026-03-13 — EmbeddingResult spec 1.3 + 1.4 alignment**
- **1.3 fields:** `embedding_time` → `wall_time`; `error_message` → `error`; added `algorithm_version: str`, `partial: bool`, `metadata: Optional[dict]`; status enum extended with `CRASH` and `OOM`.
- **1.4 algorithm versioning:** `version` property added to `EmbeddingAlgorithm` base class (default `"unknown"`); `benchmark_one()` reads `algo.version` and stores it as `algorithm_version` on every `EmbeddingResult`.

**2026-03-13 — Trustless success inference + counter extraction in benchmark_one()**
Runner no longer trusts `raw['success']`. Infers success from embedding presence, then calls `validate_embedding()` to mathematically verify. Assigns strict status: `SUCCESS`, `INVALID_OUTPUT`, `TIMEOUT`, `CRASH`, or `FAILURE`. Algorithmic counters (`target_node_visits` etc.) now extracted from the result dict and stored on `EmbeddingResult` — previously they were never read from the wrapper return value.

**2026-03-13 — Algorithm registry contract compliance**
All built-in algorithm wrappers updated to match the developer guide interface contract:
- Never return `None` — all failure paths return `{'embedding': {}, 'time': elapsed, 'success': False, 'status': '...'}`.
- All `print()` → `logging.error/warning` via module-level `logger = logging.getLogger(__name__)`.
- All MinorMiner variants: `seed = kwargs.get('seed', None)` passed as `random_seed=seed`.
- OCT factory: `tempfile.mktemp()` → `NamedTemporaryFile(delete=False)`; cleanup moved to `finally` block.
- ATOM: `print("⚠️ ATOM not compiled")` → `logger.warning`; cleanup in `finally`; `TIMEOUT` status on `subprocess.TimeoutExpired`.
- `version` property added to `EmbeddingAlgorithm` base class.

**2026-03-13 — EmbeddingResult `status` field + pipeline updates**
Added `status: str` to `EmbeddingResult` with values `SUCCESS | INVALID_OUTPUT | TIMEOUT | CRASH | OOM | FAILURE`. Updated `results.py` summary stats and `benchmark.py` progress output to use `wall_time` and `error`.

**2026-03-13 — Phase 1 smoke benchmark**
Ran 20 graphs × 2 topologies × 2 algorithms × 3 trials (240 runs). All four Phase 1 integrity checks confirmed: manifest tamper detection fires on 1-byte corruption, config.json written before runs start, ATOM cpu_time > 0 via RUSAGE_CHILDREN, MinorMiner cpu_time > 0 via process_time. 240/240 succeeded. Script: `smoke_phase1.py`.

**2026-03-13 — Hardware-agnostic algorithmic operation counters**
Added four optional `int` fields to `EmbeddingResult`: `target_node_visits`, `cost_function_evaluations`, `embedding_state_mutations`, `overlap_qubit_iterations`. All default to `None`; algorithms populate whichever they can instrument. Each increment must be a bare `+= 1`. Documented in `EMBER_developer_guide.md` with applicability table, constraints, and example.

**TODO — CPU timing: self-reported vs. runner-measured**
The spec for 1.1 calls for subprocess wrappers (ATOM, OCT) to self-report `cpu_time` in their return dict (measured with `RUSAGE_CHILDREN` internally), and for the runner to use `raw.get('cpu_time', process_time_delta)`. The current implementation measures `RUSAGE_CHILDREN` externally in the runner. This is adequate for single-threaded C++ processes but will be inaccurate if the algorithm uses multiple threads (RUSAGE_CHILDREN accumulates CPU time across all child processes, not per-thread). Migrate to self-reported timing in the wrappers before multi-threaded algorithm support is added.

**2026-03-13 — Phase 1: CPU timing, SHA-256 manifest, environment provenance (1.1–1.3)**
- **1.1 CPU time:** `_uses_subprocess` flag on ATOM/OCT triggers `RUSAGE_CHILDREN` measurement in the runner; Python algorithms use `process_time`. `cpu_time` field on `EmbeddingResult`.
- **1.2 Manifest:** `generate_manifest()` hashes all graph JSONs to `test_graphs/manifest.sha256`; `verify_manifest()` raises `RuntimeError` on any mismatch; called automatically at benchmark startup.
- **1.3 Provenance:** `__version__ = "0.5.0"` added; `qebench_version` + pip freeze written to `config.json`; batch directory created before runs start so provenance survives crashes.

**2026-03-13 — Developer guide and algorithm documentation**
Added `EMBER_developer_guide.md` (team split, algorithm interface contract, vendoring policy, coding standards, testing strategy) and `docs/adding_algorithms.md` / `docs/adding_test_graphs.md` (contributor how-tos).

**2026-03-13 — PSSA integration**
Cloned PSSA D-Wave implementation into `algorithms/pssa_dwave/`; installed as editable package (`pip install -e`). Four variants registered: `pssa`, `pssa-weighted`, `pssa-fast`, `pssa-thorough`.

**2026-03-13 — README and algorithm status update**
`oct-fast-oct-reduce` marked as recommended OCT variant; `oct-triad-reduce` corrected to warning status (produces invalid embeddings on non-bipartite graphs). PSSA marked working. CHARME correctly noted as requiring a trained model and PyTorch.

**2026-03-13 — MinorMiner variants**
Added three additional registered MinorMiner variants: `minorminer-aggressive` (tries=50), `minorminer-fast` (tries=3), `minorminer-chainlength` (chainlength_patience=20).
