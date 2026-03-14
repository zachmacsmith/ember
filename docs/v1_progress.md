# Version 1 Progress Log

Reverse-chronological. One entry per session or logical unit of work.

---

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
