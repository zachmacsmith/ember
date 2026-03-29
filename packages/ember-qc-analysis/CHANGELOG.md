# Changelog

All notable changes to `ember-qc-analysis` are documented in this file.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

---

## [0.0.1] - 2026-03-28

Initial PyPI placeholder release to reserve the package name.

### Added

**Package**
- PyPI packaging under `ember-qc-analysis` with `hatchling` build backend and `src/` layout.
- Optional install via `pip install ember-qc[analysis]` from the `ember-qc` package.
- `ember-analysis` and `ember-a` CLI entry points.

**CLI** (`ember-analysis` / `ember-a`)
- `ember-analysis stage <batch_dir>` — validate and set a batch as the active context;
  prints graph count, algorithm list, topology, and trial count.
- `ember-analysis unstage` — clear the active batch context.
- `ember-analysis report` — run the full analysis pipeline (plots, tables, stats)
  on the active or specified batch.
- `ember-analysis plots [GROUP...]` — generate plot groups selectively or all at once.
  Groups: `distributions`, `scaling`, `pairwise`, `success`, `graph-indexed`, `topology`.
  `--list` flag enumerates available groups. `--overwrite` flag regenerates existing files.
- `ember-analysis tables` — generate CSV and LaTeX summary tables.
- `ember-analysis stats` — run significance tests, Friedman test, correlation matrix,
  and win rate matrix.
- `ember-analysis batches list` — discover all valid batches under the configured input
  directory. `ember-analysis batches show <batch>` — print batch metadata.
- `ember-analysis config show / get / set / reset / path` — full configuration management.
- `ember-analysis version` — print package version.

**Configuration system** (`_config.py`, `_paths.py`)
- Platform-appropriate user data directory via `platformdirs` (`~/Library/Application
  Support/ember-qc-analysis/` on macOS, `~/.local/share/ember-qc-analysis/` on Linux).
- `config.json` with four keys: `input_dir`, `output_dir`, `fig_format`, `active_batch`.
- Full priority chain: explicit argument → environment variable
  (`EMBER_ANALYSIS_INPUT_DIR`, `EMBER_ANALYSIS_OUTPUT_DIR`, `EMBER_ANALYSIS_FIG_FORMAT`)
  → `config.json` → package default.
- Opportunistic ember-qc output directory discovery: reads ember-qc's own `config.json`
  to suggest its `output_dir` as the input directory when none is configured. Interactive
  prompt offers session-only or persistent use.
- Batch validation: a valid batch requires `results.db` (primary) or `runs.csv` (fallback).

**Analysis modules**
- `loader.py` — load batch data from `results.db` (SQLite) or `runs.csv`; derives
  computed columns (`qubit_overhead_ratio`, `coupler_overhead_ratio`, `is_timeout`,
  `category`).
- `summary.py` — `overall_summary()`, `summary_by_category()`, `rank_table()`.
- `statistics.py` — `win_rate_matrix()`, `significance_tests()`, `friedman_test()`,
  `correlation_matrix()`, `density_hardness_summary()`.
- `plots.py` — 30+ plot functions across six groups: distributions (chain length KDE,
  violin plots, consistency), scaling (performance vs. problem size, density hardness),
  pairwise (win rate heatmap, head-to-head scatter), success (success heatmap, by nodes,
  by density), graph-indexed (metrics by ID/nodes/density), topology (comparison,
  Pareto frontier).
- `export.py` — DataFrame to LaTeX table export.
- `filters.py` — graph filtering utilities.
- `BenchmarkAnalysis` class — unified entry point wrapping all modules; `generate_report()`
  produces the full output directory structure.

### Known Issues

- **`ember-analysis` requires a completed ember-qc batch** — the package expects
  `results.db` or `runs.csv` to exist in the batch directory. Pointing at an incomplete
  or empty directory raises a clear `ValueError`.
- **`ember graphs fetch / cache`** (ember-qc) stubs mean remote graph download is not
  yet available; analysis is limited to locally-run batches.
