# Version 1 Progress Log

Reverse-chronological. One entry per session or logical unit of work.

---

**2026-03-22 — Test graph generation infrastructure + repo reorganisation**

### Test graph generation (`test_graphs_generation/`) — excluded from git, local use only

New standalone module for generating, screening, and characterising candidate test graphs before they enter the validated `test_graphs/` library. All scripts live in `test_graphs_generation/`; generated JSON files are excluded from git (regenerated on demand).

- **`generate_graphs.py`** — centralised graph generation registry. `REGISTRY` maps 48 type names to `(generator_fn, [param_names])`. `generate_graphs(type, **params)` generates the cartesian product of all supplied parameter value lists and saves each to `generated_graphs/<type>/<id>_<name>.json` in node-link JSON format. IDs are 15-digit integers derived from a SHA-256 hash of type, parameters, and UTC microsecond timestamp. CLI: `python generate_graphs.py <type> --param values...` or `--list`. Types span: structured (complete, bipartite, grid, cycle, path, star, wheel, binary_tree, hypercube, turan, circulant, johnson, kneser, generalized_petersen, sudoku), named fixed-size graphs (petersen, dodecahedral, icosahedral, moebius_kantor, heawood, pappus, desargues, bull, butterfly, wagner), random (erdos_renyi, barabasi_albert, regular, watts_strogatz, sbm, random_planar, random_tree), physics lattice (triangular_lattice, honeycomb, cubic_lattice, king_graph, frustrated_square), network science (lfr_benchmark, random_geometric), application (spin_glass, weak_strong_cluster, power_grid), and QUBO interaction graphs (mis_qubo, matching_qubo, portfolio_qubo).

- **`check_graph_feasibility.py`** — analytical impossibility screening against chimera_16x16x4, pegasus_16, zephyr_12. Checks node_count and edge_count in order (short-circuits on first failure). Accepts a graph type name (checks all graphs in `generated_graphs/<type>/`) or `"*"` for all types. Outputs a CSV with one row per (graph, topology): `graph_type`, `graph_name`, `graph_id`, `topology`, `source_nodes`, `target_nodes`, `source_edges`, `target_edges`, `embeddable`, `failed_check`. Sorted by graph_type → graph_name → topology. Output defaults to `test_graphs_generation/feasibility_results.csv` regardless of working directory.

- **`find_boundaries.py`** — binary-search boundary finder. For each type in `SEARCH_CONFIG`, binary-searches the primary size-driving integer parameter (n, depth, k, …) while holding secondary parameters fixed at representative values from a `fixed_grid`. For each (type, fixed_params, topology) triple, finds the last feasible and first infeasible primary parameter value. Saves the last-feasible graph to `generated_graphs/boundary_graphs/`. Outputs `boundaries_summary.csv`. Named (fixed-size) graphs are checked trivially without search. CLI: `python find_boundaries.py` (all types) or `--types complete cycle ...`. Initial `hi` doubled up to 6× if not yet infeasible; if still feasible after 6 doublings the boundary is recorded as not reached.

- **`graph_boundaries.md`** — discovered analytical impossibility boundaries per graph type per topology, with notes on which limits bind (node_count vs edge_count) and where boundaries were not yet reached.

- **Supporting docs:** `graph_standard.md` (parameter definitions for all types), `graph_difficulty.md` (implementation difficulty classification), `graphs_application.md` (physics/application graph descriptions).

- **Generated graphs:** structured single-parameter types swept to n ≈ 500 (complete K_2–K_500, cycle C_3–C_5000, path P_2–P_5000, star/wheel to n=5000, binary_tree depth 1–12, hypercube Q_1–Q_12, sudoku n=2–5). All named graphs generated once. 217 JSON files, ~99 MB total — excluded from git.

### `qebench/topologies.py`

- **zephyr_12 fix:** built-in Zephyr registrations were capped at size 8. Added zephyr_12 (4,800 nodes, 45,864 edges) matching current D-Wave Advantage2 hardware.

### Repo reorganisation

- `EMBER_developer_guide.md` → `docs/EMBER_developer_guide.md`
- Added to `docs/`: `EMBER_roadmap.md`, `TODO_graphFeasibility`, `TODO_newAlgorithms.md`, `TODO_newAlgorithmsORder`
- Added `docs/Finished/`: completed TODO docs (checkpointing, executetasks, faultyQubits, logger features, output validation, SQL/multithreading, new analysis)
- Added `archived/Algorithm_Contract.md`
- `.gitignore`: added `runs_unfinished/`, `Curr_experiments/`, `test_graphs_generation/`

---

**2026-03-19 — Faulty qubit simulation**

- **`qebench/faults.py`** — new standalone module. Single public function `simulate_faults(topology, fault_rate, fault_seed, faulty_nodes, faulty_couplers) -> nx.Graph`. Mode inferred from arguments: random (`fault_rate > 0`), explicit (`faulty_nodes`/`faulty_couplers`), or no-op (all defaults). Returns a copy, never a view.
- **Random mode:** `rng = random.Random(fault_seed)` → removes `int(N * fault_rate)` randomly selected nodes and all incident edges. Deterministic given the same seed.
- **Explicit mode:** `remove_nodes_from` → `remove_edges_from` → isolated-node cleanup. Nodes that become isolated after coupler removal are automatically removed.
- **Validation (all pre-modification):**
  - `fault_rate` outside `[0.0, 1.0]` → `ValueError`
  - `fault_rate > 0` combined with non-empty `faulty_nodes`/`faulty_couplers` → `ValueError`
  - Any node in `faulty_nodes` absent from topology → `ValueError` (lists offending IDs)
  - Any coupler in `faulty_couplers` referencing a nonexistent node → `ValueError`
  - Any coupler in `faulty_couplers` where both endpoint nodes exist but the edge does not → `ValueError`
  - `fault_rate=0.0` alongside non-empty `faulty_nodes`/`faulty_couplers` is allowed — zero rate is treated as no random faults.
- **Integration with `run_full_benchmark()`:** four new parameters added — `fault_rate`, `fault_seed`, `faulty_nodes`, `faulty_couplers`. Each accepts a scalar (applied to all topologies) or a dict keyed by topology name (per-topology control). Flat collections (`faulty_nodes=[...]`, `faulty_couplers=[...]`) raise `ValueError` for multi-topology runs with a helpful example of the expected dict format. Per-topology mutual exclusion checked before any runs start, naming the topology in the error message.
- **`fault_seed` defaults to run `seed`:** when `fault_seed` is not specified, each topology's fault seed resolves to the run master seed. An explicit `fault_seed` (scalar or per-topology dict) overrides this.
- **Config logging:** `fault_simulation` key written to `config.json`. Per-topology entry records `mode`, `fault_rate`, `fault_seed`, `faulty_nodes` (exact removed node list), and `faulty_couplers` (exact removed coupler list), so the precise faulted topology can be reconstructed without re-running. `fault_simulation` is `null` when no faults are active. Isolated nodes removed during cleanup are included in the logged `faulty_nodes` list.
- **`TOPOLOGY_DISCONNECTED` warning:** after fault simulation, connectivity is checked. If a topology becomes disconnected, `TOPOLOGY_DISCONNECTED` is added to the run-level warning registry and printed in the end-of-run summary block (`_print_warn_summary`) with component count per topology.
- **`simulate_faults` exported** from `qebench.__init__` and listed in `__all__`.
- *Note: Random fault simulation is a uniform approximation for stress testing. For physically accurate simulation, pass calibration data from your hardware instance directly as `faulty_nodes` and `faulty_couplers`.*
- **TODO:** The `topologies` parameter in `run_full_benchmark()` currently only accepts registered topology name strings (looked up via `get_topology()`). Custom graph objects can only be used for single-topology runs via `EmbeddingBenchmark(target_graph=my_graph)`. Extend `topologies` to also accept `(name, graph)` tuples so that custom/unregistered graphs can be used in multi-topology runs.
- 245/245 tests pass.

---

**2026-03-18 — `_execute_tasks()` refactor + cancel/stdin fixes**

- **`_execute_tasks()` module-level function:** extracted the entire run loop (sequential + parallel paths, progress reporting, JSONL writing, warning accumulation, cancel handling) into a single shared function called by both `run_full_benchmark()` and `load_benchmark()`. Neither function duplicates run loop logic.
- **`ExecutionResult` dataclass:** return type of `_execute_tasks`. Carries `warning_registry`, `unfinished_tasks`, `session_elapsed`, `completed_count`, `cancelled`.
- **`_load_results_from_jsonl(workers_dir)`:** shared helper — reads all `worker_*.jsonl` files and reconstructs `EmbeddingResult` objects.
- **`_compute_postrun_warnings(results)`:** shared helper — computes `TIMING_OUTLIER` and `ALL_ALGORITHMS_FAILED` from a completed result list. Called by both callers after `_execute_tasks` returns.
- **Task tuple format:** changed from 8-element `(src, tgt, algo, timeout, prob, topo, trial, seed)` to 7-element `(src, tgt, algo, prob, topo, trial, seed)`. `timeout` removed from tuple — passed as a uniform top-level argument to `_execute_tasks` and `_worker_process`.
- **Warmup moved to caller:** `run_full_benchmark` runs warmup trials before calling `_execute_tasks`; `_execute_tasks` receives measured tasks only.
- **Transition detection for topo/problem headers:** sequential path inside `_execute_tasks` detects when `topo_name` or `problem_name` changes between consecutive tasks and prints section headers inline (no nested loop needed).
- **`cancel_trigger: Optional[Callable]`:** included in `_execute_tasks` signature. Polled between trials/results alongside the keypress flag.
- **`elapsed_offset`:** `load_benchmark` passes `config.get('batch_wall_time', 0.0)` so the progress bar shows cumulative time across all sessions, not just the current one.
- **`run_full_benchmark` returns `None` on cancel** (previously returned the staging `batch_dir`). Callers that do `if direc:` before analysis now correctly skip analysis on cancel without crashing `BenchmarkAnalysis` on an incomplete directory.
- **Terminal stdin fix — `cancel_join_thread()`:** when workers are `terminate()`d mid-operation, Python's `multiprocessing.Queue` cleanup would hang at exit trying to join feeder threads stuck waiting for killed workers to drain pipes. Fixed by calling `task_queue.cancel_join_thread()` and `result_queue.cancel_join_thread()` immediately after worker termination. This was the root cause of the terminal appearing frozen after every parallel cancel.
- **Keypress listener uses `select` with timeout:** `_keypress_cancel_listener` now uses `select.select([sys.stdin], [], [], 0.5)` instead of a blocking `readline()`, so the thread exits promptly (within 0.5s) when `_cancel_flag` is set at the end of `_execute_tasks`.
- **Worker stdin detached:** each `_worker_process` redirects fd 0 to `/dev/null` via `os.dup2` at startup, preventing spawned workers from holding the parent's TTY file descriptor.
- 215/215 tests pass.

---

**2026-03-18 — Topology compatibility + run-level warning registry**

- **`supported_topologies` class attribute on `EmbeddingAlgorithm`:** Optional `List[str]` (default `None` = all topologies). Set to `['chimera']` on `AtomAlgorithm`. Matching is prefix-based — `'chimera'` matches `chimera_4x4x4`, `chimera_16x16x4`, etc.
- **Pre-run compatibility check:** Before the task list is built, every `(algorithm, topology)` pair is tested via `_algo_topo_compatible()`. Incompatible pairs are collected, a pre-run warning is printed for each (`"atom is not compatible with topology pegasus_16 — 450 trials skipped."`), and those pairs are excluded from `all_tasks` and from the sequential execution loop. `total_measured` and `total_runs` reflect only the tasks that will actually run. The incompatible combos are stored in the warning registry under `TOPOLOGY_INCOMPATIBLE`.
- **Run-level warning registry:** `_warn_registry` dict accumulated throughout each run in both `run_full_benchmark()` and `load_benchmark()`. Warning types: `TOPOLOGY_INCOMPATIBLE` (pre-run), `INVALID_OUTPUT` and `CRASH` (accumulated per-trial in sequential and parallel display loops), `TIMING_OUTLIER` and `ALL_ALGORITHMS_FAILED` (computed post-run from `self.results`). TIMING_OUTLIER detects any (algo, topology) where ≥2 successful results have any trial exceeding 10× the median wall time. ALL_ALGORITHMS_FAILED identifies (problem, topology) pairs where no algorithm succeeded across all trials.
- **End-of-run summary block:** Printed after results are saved, via `_print_warn_summary(warn_registry, log_dir)`. Groups TOPOLOGY_INCOMPATIBLE by algo, shows per-algo counts for INVALID_OUTPUT and CRASH (including first error message), per-(algo, topo) counts for TIMING_OUTLIER, and up to 5 problem names for ALL_ALGORITHMS_FAILED with `...` if more. Total warning count in header. No-op on a clean run — only prints when the registry is non-empty. Final line shows absolute path to `logs/` directory.
- **`flush_warning_buffer()` removed from run paths:** The buffered `_ListHandler` approach (which dumped raw WARNING log messages after the progress bar) is replaced by the structured end summary. The `_ListHandler` / buffered mode in `BatchLogger` is still used to suppress mid-run WARNING log interleaving with the progress bar, but `flush_warning_buffer()` is no longer called — the summary takes its place.
- **`smoke_test_warnings.py`** added at project root — visual smoke test covering all five scenarios: full registry, topology-only, mid-run warnings only, clean run (silent), and `_algo_topo_compatible()` correctness checks.
- 215/215 tests pass.

---

**2026-03-18 — ATOM wrapper bug fixes + warning/progress bar display fix**

- **ATOM index formula bug (critical):** The wrapper inferred ATOM's internal `topo_column` from the output as `max_y + 1`. ATOM always calls `expanding_border()` one final time after the last successful pass, which shifts all coordinates by +1 and adds 2 to `topo_column`, leaving an empty outer border. This meant `max_y_in_output = topo_column_internal - 2`, so the wrapper's column count was always 1 short. Every qubit at row > 0 received a wrong linear index (`x * wrong_ncols * 8 + ...`), while row-0 qubits were unaffected (multiplied by 0). Fix: use `target_graph.graph['columns']` (stored by dwave_networkx) as the column count, with a fallback of `round(sqrt(n_nodes / 8))` for non-dwave graphs. This explains why K4 (fits in 1 row) always succeeded while anything needing multiple rows failed with `INVALID_OUTPUT`.
- **ATOM bounds check:** ATOM grows its own Chimera dynamically and sometimes produces an embedding that exceeds the target's dimensions. Previously this generated wrong qubit indices that mapped to valid-but-disconnected qubits, causing `INVALID_OUTPUT` (false success). Now the wrapper checks all `(x, y)` coordinates against `target_graph.graph['rows']` and `['columns']` before conversion, returning clean `FAILURE` with a descriptive message (`"ATOM's embedding requires a 6×3 Chimera but target is 4×4"`) when bounds are exceeded. Correctly reflects that ATOM simply couldn't embed within the given target size.
- **Warning/progress bar interleaving fix:** In non-verbose mode, `BatchLogger` was writing `WARNING` messages to `sys.stderr` immediately, interleaving with the `\r`-based progress bar on `sys.stdout`. Fix: `BatchLogger.setup(buffered=True)` now attaches a `_ListHandler` (new list-based `logging.Handler` subclass) instead of a `StreamHandler`. `flush_warning_buffer()` prints all buffered warnings after the progress bar's final newline. Both `run_full_benchmark()` and `load_benchmark()` call `setup(buffered=not verbose)` and `flush_warning_buffer()` after each path's progress bar ends. Verbose mode is unchanged.
- **Validation error messages updated:** `INVALID_OUTPUT` error messages no longer say `"Algorithm claimed success=<absent>"` (misleading since the contract forbids returning `success`). Now say `"returned embedding (size=N)"` for non-empty embeddings and `"returned empty embedding"` for empty ones, making false-success vs. format-error cases visually distinct. Two tests updated to match.
- 215/215 tests pass.

---

**2026-03-17 — `compute_graph_properties.py` standalone script**

- **`compute_graph_properties.py`** (project root) — standalone script that scans all (or a selection of) graphs in `test_graphs/`, computes 25 structural properties for each, and writes them back into each JSON file under a top-level `"properties"` key in-place. Importable as a function or run as a CLI script.
- **25 properties computed:** `n_vertices`, `n_edges`, `density`, `avg_degree`, `max_degree`, `min_degree`, `degree_std`, `avg_clustering`, `global_clustering`, `n_triangles`, `algebraic_connectivity`, `avg_shortest_path_length`, `diameter`, `girth`, `is_planar`, `is_bipartite`, `is_connected`, `is_regular`, `n_connected_components`, `largest_component_fraction`, `degree_assortativity`, `degeneracy`, `treewidth_upper`, `clique_number`, `clique_lower_bound`.
- **Skip logic:** existing property values are preserved by default (`overwrite=False`). A file is only written if at least one property was newly computed — prevents unnecessary disk writes and timestamp churn.
- **Error handling:** per-property `try/except`; if any property in the requested batch fails, the entire file is skipped and the failure is logged. No partial writes — consistent state guaranteed.
- **Edge cases:** `algebraic_connectivity`, `avg_shortest_path_length`, `diameter` return `None` for disconnected graphs. `girth` returns `None` for acyclic graphs (`math.isinf` guard). `degree_assortativity` returns `None` for fewer than 2 edges or `nan` result. `clique_number` returns `None` for `n > 50` and `density ≥ 0.3` (intractable). `clique_lower_bound` uses `itertools.islice(nx.find_cliques(), 2000)` to bound runtime. `treewidth_upper` via `networkx.algorithms.approximation.treewidth_min_degree`.
- **Progress reporting:** one line per graph — `[  i/N]  graph_{id}  {name}  prop=val  prop=val …` — plus a final count summary. Prints a manifest-update reminder (`⚠️  REMEMBER TO UPDATE GRAPH HASH MANIFEST`) on every run.
- **CLI:** `--properties / -p`, `--selection / -s`, `--overwrite` flags via `argparse`.
- **`source_problem`** initialised to `null` in the properties dict if not yet set, preserving the field for manual annotation.
- 297/297 tests pass (215 `test_qebench.py` + 82 `test_qeanalysis.py`).

---

**2026-03-17 — `delete_benchmark()` + checkpoint/resume test suite**

- **`delete_benchmark(batch_id, unfinished_dir, force)`** — new standalone function, exported from `qebench`. Only operates on `runs_unfinished/`; completed results in the output directory are never touched. Computes actual disk size via `rglob`. Prints a summary line before acting: `{done:,}/{total:,} complete, cancelled Xd/Xh/Xm ago, 340MB` for clean cancels; `crashed or still running, N JSONL lines, size` for crash-killed batches. With `force=False` (default) prompts `Delete batch_X (summary)? [y/N]` — defaults to no on bare Enter. With `force=True` skips the prompt for pipeline use. Returns `True` if deleted, `False` if aborted or nothing found. TODO comment for the future partial-compile path (compile finished JSONL into a partial result flagged `"completed": false`) and future CLI note (`ember delete [batch_id]`).
- **52 new tests** added to `tests/test_qebench.py` across five new test classes:
  - **`TestNewModuleImports`** (+3): `load_benchmark`, `delete_benchmark`, and all 5 `checkpoint` functions importable.
  - **`TestCheckpoint`** (14 tests): `write_checkpoint`/`read_checkpoint` roundtrip; `cancelled_at` ISO timestamp; `resume_count` stored; absent file returns `None`; `delete_checkpoint` removes file and is a no-op when absent; `completed_seeds_from_jsonl` reads valid JSONL, strips truncated last lines, aggregates multiple worker files, handles missing `workers/` dir; `scan_incomplete_runs` finds checkpoint batches, detects crashed batches, counts JSONL lines, returns newest-first, skips dirs without `config.json`.
  - **`TestResultsManagerDirectory`** (8 tests): `create_batch()` writes to `unfinished_dir` not `results_dir`; default `unfinished_dir` is sibling; `unfinished_dir` created automatically; `move_to_output` moves batch and deletes staging copy; custom `output_dir` override; `latest` symlink created on move and tracks most-recent move; `results_dir` stays empty until `move_to_output`.
  - **`TestRunFullBenchmarkV2`** (8 tests): `seed` and `n_workers` written to `config.json`; `batch_wall_time` written to `config.json`; `custom_problems` serialized when `graph_selection=None`; not serialized when `graph_selection` given; `runs_unfinished/` empty after successful run; return value is in `results_dir`; `output_dir` override routes completed batch correctly.
  - **`TestLoadBenchmark`** (8 tests): no-runs returns `None`; invalid `batch_id` raises; all-done path (compile + move, 1 DB row, checkpoint deleted); resume from checkpoint (2nd trial run, 2 DB rows); resume crashed run from JSONL; checkpoint deleted after success; `n_workers` override runs both trials.
  - **`TestDeleteBenchmark`** (9 tests): no-runs returns `False`; invalid `batch_id` raises; `force=True` deletes and returns `True`; works on crashed runs (no checkpoint); never touches `results/`; disk size appears in output; progress fraction in output; batch note in output.
- **NetworkX FutureWarning silenced** — `nx.node_link_data(g, edges="links")` and `nx.node_link_graph(data, edges="links")` now pass the kwarg explicitly, suppressing the warning that the default will change in NetworkX 3.6. 0 warnings in the full test run.
- 215/215 tests pass.

**2026-03-17 — Checkpoint & resume feature + directory restructure**

- **Directory restructure:** batch directories are now created in `runs_unfinished/` (sibling to `results/`) and only moved to `results/` (the configured output directory) after `compile_batch()` completes successfully. Location in `results/` is the sole completeness signal — anything in `runs_unfinished/` is by definition incomplete. `ResultsManager` updated: `create_batch()` writes to `unfinished_dir`; new `move_to_output(batch_dir, output_dir=None)` performs the `shutil.move` and updates the `latest` symlink. `latest` is now only created in `move_to_output()` so it always points to the most recently *completed* batch.
- **`qebench/checkpoint.py`** — new module. Exports: `write_checkpoint()`, `read_checkpoint()`, `delete_checkpoint()`, `completed_seeds_from_jsonl()` (reads worker JSONL files and strips potentially truncated last lines from crash-killed workers), `scan_incomplete_runs()` (scans `runs_unfinished/`, classifies each as cleanly cancelled / crashed).
- **Cancel mechanism:** a `threading.Event` cancel flag is set by (a) a background daemon thread reading stdin for `'q'` + Enter (only when `sys.stdin.isatty()`), or (b) `KeyboardInterrupt` (Ctrl+C). Workers are never cancel-aware — cancel can only fire between trials.
- **Sequential cancel:** cancel flag checked at the start of each measured trial. `done_count` advances only after the JSONL write, so no completed result is ever lost. On cancel, `unfinished = all_tasks[done_count:]`.
- **Parallel cancel:** display loop uses non-blocking `result_queue.get(timeout=0.5)`. On cancel: drains the queue for `cancel_delay` seconds (default 5s, configurable), terminates all workers, strips truncated JSONL last lines, derives unfinished tasks from `completed_seeds_from_jsonl()`.
- **`run_full_benchmark()` changes:** new `output_dir` and `cancel_delay` parameters. Config now stores `seed` and `n_workers` for resume. Custom problems (`graph_selection=None`) serialized into `config.json` under `custom_problems: [{name, graph: node_link_data}]`. Flat `all_tasks` list built upfront. On cancel: writes `checkpoint.json`, returns staging `batch_dir`. On completion: `compile_batch` → `move_to_output` → `save_results`, returns final `output_dir`.
- **`load_benchmark(batch_id, unfinished_dir, output_dir, n_workers, verbose, cancel_delay)`** — new standalone function, exported from `qebench`. With no `batch_id`, prints a discovery table of all incomplete runs (progress, resume count, cancel time for clean cancels; JSONL line count for crashed runs) and prompts for selection by number. With a single incomplete run, auto-selects with a confirmation prompt. Reads `config.json` to reconstruct problems, topologies, algorithms, seed, and n_workers. Derives unfinished tasks from stored checkpoint (clean cancel) or JSONL scan (crashed). `n_workers` defaults to the value stored in the original run; can be overridden. On completion: `compile_batch` → `delete_checkpoint` → `move_to_output` → `save_results`.
- **TODO:** `cancel_trigger` callable parameter (for programmatic cancellation from a parent pipeline) documented as a comment in `run_full_benchmark`; not yet implemented.
- **TODO (flagged):** global session config (`~/.config/ember/config.json` for persistent output-directory preference) deferred for future work.
- Test suite updated: `test_latest_symlink_points_to_newest` now calls `move_to_output()` before asserting the symlink (reflects new semantics). 163/163 tests pass, 0 warnings.

**2026-03-16 — Runner improvements, contract & documentation overhaul**
- **Wall/CPU time ownership moved to runner** — `benchmark_one()` now starts `_wall_start = time.perf_counter()` around every `embed()` call. `wall_time` always uses the runner-measured `_wall_elapsed`; any `'time'` key returned by an algorithm is ignored. `cpu_time` was already runner-measured; now explicit. Algorithms no longer need to self-report timing.
- **Global RNG reseeding** — `_reseed_globals(trial_seed)` added; called before every `embed()` invocation in all three paths (sequential warm-up, sequential measured, parallel worker). Seeds `random` and `numpy.random` so algorithms using global RNGs without explicit seeding produce deterministic results.
- **`verify_manifest()` scoped to loaded graphs** — previously checked every entry in the manifest (all files on disk) at the start of `run_full_benchmark()`. Now called from inside `load_test_graphs()` and checks only the specific graph files selected for the current run. New graph files not yet in the manifest are silently allowed; modified existing graphs raise `RuntimeError` and cancel the run before any trials start.
- **`CONTRACT_algorithms.md`** rewritten (in `docs/`): three-tier structure (strict / suggestions / opt-in), correct `qebench` package imports, timing removed from algorithm contract, `_uses_subprocess` flag documented, failure status table, partial embedding path, minimum valid example, contract test suite with correct `benchmark_one` import and `ALGORITHM_REGISTRY[name]` fix.
- **`docs/Runner_workflow.md`** — new document describing full runner workflow: setup, per-trial execution (sequential + parallel), `benchmark_one()` internals, per-trial logging, `compile_batch()` schema, seed derivation, batch directory layout.
- **`docs/TODO_algorithms.md`** — new document: prioritised algorithm layer TODO derived from contract/code audit (PSSA wrapping, Layer 3 validation, `chain_length_std`/`qubit_overhead` on dataclass, etc.).
- 163/163 tests pass.

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
