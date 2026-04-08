# Changelog

All notable changes to `ember-qc-analysis` are documented in this file.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

---

## [0.10.6] - 2026-04-07

### Fixed

- `plot_success_heatmap`, `plot_graph_indexed_success`, and
  `_draw_chain_dots_categorical` all used nested `algos × graphs` loops with
  a full DataFrame scan inside each iteration — O(N²) in the number of
  graphs.  With 30,000+ graphs this caused multi-minute hangs.  All three now
  use vectorised `groupby` + `pivot` / `.map()` operations instead.
- `plot_success_heatmap` and `plot_graph_indexed_success` now return a
  readable placeholder figure (instead of hanging) when the graph count
  exceeds 300, since a 300+-column heatmap is not useful visually.

---

## [0.10.5] - 2026-04-07

### Fixed

- `report`, `plots`, `tables`, and `stats` commands now print `"Loading data..."`
  before importing seaborn/matplotlib, not after.  Previously the deferred
  `from ember_qc_analysis import BenchmarkAnalysis` import (which pulls in
  seaborn, matplotlib, scipy, numpy) was the first line of each command
  function, causing a silent 5–15 s hang before any output appeared.  The
  import is now moved to just before instantiation so batch/output info and
  the loading message print immediately on startup.

---

## [0.10.4] - 2026-04-07

### Added

- All four CLI commands (`report`, `plots`, `tables`, `stats`) now print
  `"Loading data..."` before reading the SQLite database and `"N rows loaded"`
  immediately after, so large batches no longer appear to hang on startup.
- `report` and `plots` now print `"  Generating X... done"` (or `failed: …`)
  for each plot as it runs, giving continuous feedback during long plot
  generation passes.

---

## [0.10.3] - 2026-04-07

### Added

- **`random_planar` graph category** — graphs with names starting with
  `planar_` are now classified as `'random_planar'` rather than `'other'`.
  This category is recognised by `--graph-type random_planar` and is included
  in the `graph_categories` parameter of `plot_size_density_heatmap()`,
  allowing random-planar graphs to be visualised on the size-density heatmap
  independently from Erdős-Rényi random graphs.

---

## [0.10.2] - 2026-04-07

### Added

- **`plot_size_density_heatmap()`** — 2-D heatmap of graph size (nodes, x-axis)
  × density (y-axis) coloured by a configurable metric.  Supports four metrics:
  - `avg_chain_length` (default) — mean over successful trials per cell
  - `max_chain_length` — mean max chain over successful trials per cell
  - `qubit_overhead_ratio` — mean qubit overhead over successful trials per cell
  - `success_rate` — fraction of trials that succeeded per cell; with one trial
    per graph, this is the fraction of distinct (n, density) graphs that
    embedded successfully, giving a valid rate estimate when ≥ 2 graphs share
    a cell

  Colourmap is auto-selected per metric (red=bad for chain/qubit, green=good
  for success rate).  Accepts `node_bin_size` / `density_bin_size` to coarsen
  the grid, `algo` to restrict to one algorithm, `vmin`/`vmax`/`cmap` overrides.
  Defaults to `graph_categories=['random']` (Erdős-Rényi graphs).

  Added to `BenchmarkAnalysis.plot_size_density_heatmap()`,
  `generate_report()` (4 variants in the scaling group), and the `scaling`
  CLI plot group.

### Fixed

- `infer_category()` now classifies graph names starting with `er_` as
  `'random'` (Erdős-Rényi graphs from the ember-qc library are named
  `er_n{n}_p{p}_s{seed}` and were previously falling through to `'other'`).

---

## [0.10.1] - 2026-04-07

### Added

- **Graph subset filtering** — all four analysis commands (`report`, `plots`,
  `tables`, `stats`) now accept two new flags:

  - `--graphs SPEC` — restrict analysis to a selection of graphs by ID.
    Supports integers, inclusive ranges, exclusions, and comma-separated
    combinations (e.g. `"1-100"`, `"1-60,!35"`, `"1,5,10-20"`).  Named
    presets (e.g. `"quick"`, `"benchmark"`) are also accepted when ember-qc
    is installed.  `"*"` is a no-op wildcard.
  - `--graph-type TYPE` — restrict to a single graph category
    (`complete`, `bipartite`, `grid`, `cycle`, `tree`, `random`, `special`,
    `other`).

  Both flags compose (AND semantics).  When either flag is active, all output
  is written into a named subdirectory of the normal analysis folder so the
  unfiltered run is never overwritten:

  ```
  analysis/<batch>/                      ← full run (unchanged)
  analysis/<batch>/graphs_1-100/         ← --graphs 1-100
  analysis/<batch>/type_random/          ← --graph-type random
  analysis/<batch>/graphs_1-100__type_random/  ← both flags
  ```

- **`parse_graph_ids(spec)`** and **`apply_graph_filter(df, graphs, graph_type)`**
  added to `ember_qc_analysis.filters` and exported from the top-level package.
- **`BenchmarkAnalysis.filter_graphs(graphs, graph_type)`** method — applies the
  filter in-place and routes output to the correct subfolder.  Supports chaining.

---

## [0.10.0] - 2026-04-07

Schema alignment with ember-qc v1.1.0 — **breaking change**.

### Changed

- `problem_name` column replaced by `graph_id` (INTEGER, manifest ID; 0 for custom
  graphs) and `graph_name` (TEXT, human-readable label) throughout all modules.
  - `loader.py`: `_REQUIRED_COLUMNS` and `_DESIRED_COLS` updated; `ORDER BY` now uses
    `graph_id`; `_derive_columns` keys `category` off `graph_name`; `infer_category`
    parameter renamed accordingly.
  - `filters.py`, `summary.py`, `statistics.py`: all groupby/filter operations now
    use `graph_name`.
  - `plots.py`: all per-graph operations use `graph_name`; `plot_problem_deep_dive`
    parameter renamed to `graph_name`.
  - `__init__.py`: `plot_problem_deep_dive(graph_name=...)` and report string updated.

### Added

- Backward-compat shim in `load_batch()`: if the loaded DataFrame has `problem_name`
  but not `graph_name` (pre-v1.1.0 batch), the column is silently renamed and
  `graph_id` is set to 0. Old batches continue to load without errors.

---

## [0.9.2] - 2026-03-30

### Fixed

- Fixed `ConstantInputWarning` from scipy in `correlation_matrix`: columns with zero
  variance now return `NaN` instead of triggering a warning.

### Changed

- CLI commands (`report`, `plots`, `tables`, `stats`) now prompt the user to choose an
  output directory when none is configured, instead of silently writing into the batch
  directory. Three options are offered: alongside ember-qc results, a custom path, or
  inside the batch directory. Choices 1 and 2 offer to save as the default.
- `resolve_output_dir()` added to `_config.py` for interactive resolution; the existing
  `get_output_dir()` is unchanged for non-interactive / library use.

---

## [0.9.1] - 2026-03-30

Patch release — changelog corrections only. No code changes.

---

## [0.9.0] - 2026-03-29

Pre-release hardening for v1.0.0.

### Fixed

- Fixed `spearmanr` / `pearsonr` result access: uses `[0]` indexing instead of tuple
  unpacking for compatibility with scipy >= 1.9 (`SpearmanrResult` / `PearsonRResult`
  named result objects).
- Fixed unsafe `.astype(bool)` on nullable SQLite columns in `loader.py` — `NaN`
  (from `NULL`) no longer silently converts to `True`.
- Fixed `generate_report(fmt=...)` parameter being accepted but never passed to plot
  functions — all 19 `plot_*` functions now accept and respect `fmt`.
- Fixed `_load_from_db()` using `SELECT *` — columns are now selected explicitly using
  `PRAGMA table_info(runs)`, keeping backward compatibility with older database schemas.
- Fixed `correlation_matrix` transposed semantics: result is now correctly shaped
  `(graph_props × embed_metrics)` as documented.

### Changed

- `resolve_input_dir()` added to `_config.py`: interactive prompt discovers ember-qc's
  configured output directory and offers session-only or persistent use as the input dir.
- Added Python 3.9 and 3.13 to `pyproject.toml` classifiers (matches `requires-python`).
- Updated `BenchmarkAnalysis` docstring from "qebench" to "ember-qc".
- Added inline comment clarifying `correlation_matrix` DataFrame construction.

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
