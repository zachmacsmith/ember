# Changelog

All notable changes to `ember-qc` are documented in this file.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

---

## [1.3.0] - 2026-04-17

### Added

- **`oct-fast-oct-reduce-timed`** — new adaptive variant of `fast-oct-reduce`
  that drives the outer iteration loop from Python rather than relying on
  the C++ binary's fixed `-r 100`. It repeatedly invokes the binary with
  a fresh seed each call and keeps the embedding with the shortest max
  chain length. Stops on whichever of the following fires first:

    - `timeout` (wall-clock budget; default 60 s)
    - `tries` (hard cap on subprocess calls; default unbounded)
    - `patience` (consecutive successful attempts without
      max-chain-length improvement; default 20 — analogue of
      `minorminer.find_embedding`'s `max_no_improvement` /
      `chainlength_patience`)

  All knobs are overridable per call via kwargs. The result dict now
  also carries `exit_reason` (`diminishing_returns` / `tries_exhausted`
  / `timeout` / `completed` / `FAILURE`), `n_attempts`,
  `n_successful_attempts`, `best_attempt_idx`, and `stalled_streak`
  for observability.

  Motivation: the existing `-r 100` variant is non-adaptive and cannot
  respond to remaining time. On easy graphs it wastes iterations after
  finding an optimal solution; on hard graphs it can be killed by the
  subprocess timeout before a single run completes, returning no
  embedding at all. The timed variant fixes both failure modes.

- **`oct-fast-oct-reduce-1k`** — non-adaptive variant with `-r 1000`
  (10× the default 100 internal repeats).

- **`oct-fast-oct-reduce-10k`** — non-adaptive variant with `-r 10000`.

All three new variants reuse the existing `fast-oct-reduce` C++
algorithm. Existing algorithms (`oct-triad`, `oct-triad-reduce`,
`oct-fast-oct`, `oct-fast-oct-reduce`, `oct-hybrid-oct`,
`oct-hybrid-oct-reduce`, and the `oct_based` alias) are unchanged.

---

## [1.2.1] - 2026-04-10

### Fixed

- `ember results list` now shows the batch note column.

---

## [1.2.0] - 2026-04-10

### Added

- **Fault-rate sweep** (`--fault-rate` list support): `--fault-rate` now
  accepts a comma-separated list of floats (e.g. `--fault-rate 0.0,0.01,
  0.05,0.10,0.20`) to sweep multiple fault rates in a single batch.
  Each (topology, rate) pair becomes a virtual topology named
  `topology@fr=0.05` in the results, so all rates are benchmarked
  together and results group naturally by topology and fault rate.

  Also supported in YAML via `fault_rate: [0.0, 0.01, 0.05, 0.10]`.

  Fault seeds are derived deterministically per (topology, rate) pair
  via SHA-256 from the master fault seed, ensuring reproducibility and
  independence across rates.

  Usage:
  ```bash
  ember run experiment.yaml --fault-rate 0.0,0.01,0.05,0.10,0.20
  ```

- **`parse_topology_name()` utility** (`benchmark.py`): public function
  to split virtual topology names into `(base_topology, fault_rate)`.
  E.g. `parse_topology_name("chimera_16x16x4@fr=0.05")` returns
  `("chimera_16x16x4", 0.05)`.

### Removed

- **`runs.csv` export**: new batches no longer generate `runs.csv`.
  The SQLite `results.db` is the sole data store. Old batches that
  only have `runs.csv` continue to work via the analysis loader's
  fallback path.

---

## [1.1.12] - 2026-04-09

### Added

- **`sensitivity` graph preset** (`graphs/presets.csv`): new 273-graph
  preset designed for algorithm parameter-sensitivity experiments.
  Includes all 82 graphs from `benchmark` plus 191 additional mid-to-
  large graphs (50–600 nodes) sampled at low and high density per family
  across all 36 graph families.  This fills the size gap in `benchmark`
  (which skews toward n ≤ 20) and provides enough density variation to
  reveal quality/speed tradeoffs between algorithm variants (e.g.
  `pssa-fast` vs `pssa-thorough`, `minorminer-fast` vs
  `minorminer-aggressive`) that are invisible on small graphs.

  Size distribution: 64 tiny (≤ 20), 16 small (21–50), 70 medium
  (51–100), 63 large (101–300), 59 xlarge (301–600).

  Density distribution: 116 ultra-sparse (< 0.05), 56 sparse
  (0.05–0.2), 46 medium (0.2–0.5), 28 dense (0.5–0.8), 25 very dense
  (> 0.8).

  Usage: `ember run --graphs sensitivity ...`

---

## [1.1.11] - 2026-04-09

### Fixed — PSSA algorithm correctness

Every PSSA trial on every topology had been returning `status=FAILURE`
since the algorithm was first registered.  Four distinct bugs were
compounding; all were in `algorithms/pssa.py`, none were in the
underlying Sugie et al. (2020) algorithm.

- **`initial_placement` produced disconnected chains**
  (`algorithms/pssa.py`).  The original implementation concatenated all
  guiding-pattern chains plus any leftover H nodes into a flat list and
  then sliced that list into `|V(I)|` contiguous blocks with
  `unique_hw[idx:idx+size]`.  This is topology-blind: a slice that
  straddles two guiding super-vertices, or that includes leftover H
  nodes from the other side of the hardware graph, is not connected in
  H — violating PSSA's M1 invariant before the annealing loop even
  began.  Fixed by replacing the slice with two topology-aware cases:
  (1) when the busclique guiding pattern already contains at least
  `|V(I)|` super-vertices (the common case), adopt the first `|V(I)|`
  of them verbatim — they are a valid `K_n` minor embedding, so the
  search starts from a feasible state; (2) otherwise fall back to a
  paper-faithful path-partition sub-slicing: build a greedy path cover
  of H via `_path_partition_guiding` and repeatedly split the longest
  path in half until the partition has `|V(I)|` connected sub-paths.
  Sub-paths of a simple path are themselves simple paths, so
  connectivity is trivially preserved.  This mirrors the original
  Sugie et al. King's-graph construction (slice a single Hamiltonian
  stripe into `|V(I)|` contiguous sub-paths), generalised to
  arbitrary hardware by slicing multiple greedy paths.  Longer chains
  are assigned to higher-degree source vertices to give hubs more
  hardware room.

- **`_leaves` returned list-order endpoints, not topological leaves**
  (`algorithms/pssa.py`).  The original `_leaves(path)` returned
  `[path[0], path[-1]]` — i.e. the first and last positions of the
  chain's Python list.  This is correct on King's graph because
  Sugie et al.'s diagonal-stripe guiding pattern makes every chain a
  simple path in H, so `path[0]` and `path[-1]` coincide with the
  topological endpoints.  On D-Wave hardware, however, busclique
  produces **tree-shaped** clique chains, so list-order endpoints are
  arbitrary nodes that may have topological degree > 1 inside the
  chain — removing one disconnects the chain.  Combined with the bug
  above, every SHIFT move silently violated chain connectivity,
  `is_valid_embedding` rejected the final state, and the wrapper
  returned `status=FAILURE` even though `Eemb == |E_I|`.  Fixed by
  rewriting `_leaves(chain, H_adj)` to return **true topological
  leaves** computed from the induced-subgraph degree (`≤ 1`), with a
  full BFS connectivity check as a fallback for cyclic chains.  This
  is a principled generalisation of Sugie et al.'s Path Super-Vertex
  (PSV) invariant to a Tree Super-Vertex (TSV) invariant, which is
  required for any D-Wave port of PSSA.  Paths are a strict special
  case of trees, so on King's graph the new `_leaves` reduces exactly
  to the paper's formulation.

- **`_remove_leaf` / `_attach_leaf` were order-sensitive**
  (`algorithms/pssa.py`).  The original `_remove_leaf` stripped
  `path[0]` or `path[-1]` depending on which matched the node to
  remove; `_attach_leaf` prepended or appended to maintain a path
  orientation.  Both made sense only under the path invariant.  After
  the TSV generalisation above, chains are order-agnostic connected
  subgraphs, so `_remove_leaf(chain, u)` now simply filters `u` out
  and `_attach_leaf(chain, u, v)` appends `u` to the chain list.  The
  `v` parameter is retained for call-site compatibility but no longer
  consulted.  Callers must guarantee `u` is a safe leaf (enforced by
  the updated SHIFT branch of `pssa()`).

- **`pssa()` SHIFT branch rejected legal moves and sometimes
  disconnected chains** (`algorithms/pssa.py`).  The inner loop used
  the old list-order `_leaves`, then further required the candidate
  target node `v` to also be a list-order leaf of chain `j`.  The
  extra `j`-leaf restriction was only needed under the path invariant
  (so that a move grows `j` at one of its two ends); under TSV, any
  `v ∈ j` adjacent in H to `u` produces a valid tree attachment.  The
  restriction was also breaking PSSA on tree chains because busclique
  chains rarely have list-order leaves that happen to be neighbours of
  each other.  Fixed by (1) replacing both `_leaves(...)` calls with
  the topology-aware version, (2) removing the `j`-leaf restriction on
  the receiving side of a SHIFT, and (3) adding an explicit safe-leaf
  check on the reverse-direction move (when shifting `v` from `j` to
  `i`), which was previously implicit in the path assumption.

### Fixed — PSSA topology handling

These two bugs were specific to Zephyr and caused 100% failure on
every Zephyr hardware graph regardless of problem size.

- **`_detect_size` used the wrong Zephyr size-inversion formula**
  (`algorithms/pssa.py`).  `dnx.zephyr_graph(m)` with the default tile
  size `t=4` produces `n = 16·m·(2m+1)` qubits, so the correct inverse
  is `m = (−1 + √(1 + n/2)) / 4`.  The old code used
  `(−1 + √(1 + 2n)) / 4`, which for `zephyr(4)` with `n=576` returned
  `m=8` — off by a factor of 2.  Combined with the bug below, this
  caused PSSA to build a guiding pattern on a completely different
  (larger) Zephyr graph and then reference qubit IDs that did not
  exist in the actual hardware.  Fixed by correcting the formula and
  adding a fast path that reads the authoritative `m` directly from
  the `H.graph` attribute dict when the networkx graph was produced by
  `dwave_networkx` (which always annotates its outputs with the
  construction parameters).

- **`build_guiding_pattern` ran busclique on a fresh `dnx` graph
  instead of the real hardware graph** (`algorithms/pssa.py`).  The
  old implementation built a new `dnx.chimera_graph(size)` /
  `pegasus_graph(size)` / `zephyr_graph(size)` from the
  (potentially-wrong) inferred size and ran
  `find_clique_embedding(mid, topo_graph)` against that fresh graph.
  The returned chain nodes were therefore qubit IDs of the *fresh*
  graph, not of `self.H` — and when `_detect_size` was wrong (Zephyr),
  or when the user passed a faulty-qubit subgraph, those IDs did not
  exist in `self.H` at all.  The subsequent `H_adj[u]` lookup inside
  `pssa()` crashed with `KeyError`, surfacing as
  `pssa error: <qubit_id>` in the wrapper's exception handler.  Fixed
  by always calling `find_clique_embedding(mid, H)` directly against
  the real hardware graph, which eliminates the entire foreign-node
  failure mode.  The `topology` and `size` parameters of
  `build_guiding_pattern` are now retained only for call-site
  compatibility and are no longer consulted — busclique infers the
  topology from `H` itself.

### Changed

- **PSSA Path Super-Vertex invariant generalised to Tree
  Super-Vertex**: this is documented above under `_leaves` but is
  worth calling out as a semantic change to the algorithm's
  assumptions.  On King's graph (the paper's original hardware) the
  invariant reduces exactly to the paper's formulation, so no change
  in behaviour.  On any D-Wave topology this is strictly necessary
  for correctness because busclique produces tree-shaped chains.

### Verification

Across 8 D-Wave topologies (chimera 4×4×4 / 8×8×4 / 16×16×4,
pegasus 4 / 8 / 16, zephyr 4 / 12) and 14 problem graph families
(cliques, cycles, paths, grids, 3-regular, Erdős-Rényi, Barabási-Albert,
Petersen), the broad regression test goes from **0/112 before this
release** to **91/112 passing**.  All three realistic-scale D-Wave
topologies — chimera_16×16×4 (D-Wave 2000Q, 2048 qubits), pegasus_16
(Advantage, 5640 qubits), zephyr_12 (Advantage2 prototype, 4800
qubits) — reach **14/14** on the broad suite.  The 21 remaining
failures are all cases where `|V(I)| > maxclique(H)`, i.e. the
problem exceeds the hardware's complete-graph embedding threshold;
Sugie et al. (2020) explicitly state that PSSA cannot beat that
threshold for dense graphs, so these failures are paper-predicted
rather than regression-class.

A separate large-problem regression sweep (`n = 100 … 400` on
realistic hardware) exposes a pre-existing performance bottleneck in
`eemb()`, which is `O(|E_H|)` per call (≈6016 edge iterations per
annealing step on chimera_16×16×4).  This limits the annealing loop
to ~100k steps per 30s timeout, well below the 10⁷–10⁸ steps Sugie
et al. use for sparse graphs beyond the clique threshold, causing
realistic-hardware sparse-large problems to time out rather than
converge.  The initial placement and annealing logic are correct;
only the step budget is insufficient.  Implementing an incremental
edge-count delta on shift/swap (`O(deg(u))` per step instead of
`O(|E_H|)`) is tracked as a follow-up.

---

## [1.1.10] - 2026-04-08

### Fixed

- **`ember version` always printed `0.9.0`** (`__init__.py`): the package
  version was hard-coded as `__version__ = "0.9.0"` and had never been
  bumped alongside `pyproject.toml`, so every release since 0.9.0 reported
  the wrong version from both `ember version` and `ember doctor`.  Fixed
  by reading the version dynamically from installed package metadata via
  `importlib.metadata.version("ember-qc")`, with a `"0.0.0+unknown"`
  fallback for source checkouts that have no `.dist-info`.  This makes
  future drift impossible — the string now always matches whatever
  `pyproject.toml` says at install time.
- **`ember doctor`** (`cli.py`): `cmd_doctor()` referenced `os.access()`
  but the `os` module was never imported at the module level (only
  `platform`, `subprocess`, and `time` were imported lazily inside the
  function), crashing with `NameError: name 'os' is not defined` when the
  work-dir writability check ran.  `os` is now imported at the top of
  `cli.py`.
- **`ember doctor`** (`cli.py`): the Linux `ldd` diagnostic reported
  `✓ all shared libraries found` even when the binary was unloadable due to
  GLIBC / GLIBCXX symbol version mismatches (e.g. a binary built on
  Ubuntu 24.04 / glibc 2.39 deployed on Debian 12 / glibc 2.36).  `ldd`
  only verifies that the `.so` files *exist*, not that required symbol
  versions within them are present.  A new `loader` check now actually
  invokes the binary with a bogus probe flag, captures stderr, and greps
  for `version \`GLIBC*\` not found (required by …)` lines — reporting
  the exact missing symbol versions and pointing at the v1.1.9 binary
  rebuild as the fix.
- **`ember install-binary`** (`_install_binary.py`): the downloader used
  `urllib.request.urlretrieve`, which does **not** raise on HTTP
  4xx/5xx — it silently saved GitHub's HTML 404 error page to disk as
  if it were the requested binary.  The subsequent verification step
  only checked file existence and the executable bit, both of which an
  HTML file trivially passes, so a bad download produced an "installed"
  binary that crashed with `Exec format error` on first use.  Fixed by:
    1. Replacing `urlretrieve` with `urlopen` + explicit status check +
       streaming `copyfileobj`, so HTTP errors raise `HTTPError` and are
       caught with a targeted message (including a 404-specific hint to
       check the release tag / asset name on GitHub).
    2. After download, validating the first four bytes against the known
       magic numbers for ELF (`\x7fELF`) and Mach-O (thin and universal),
       printing a content preview and exiting non-zero if the payload
       looks like text (likely an HTML error page routed via a proxy or
       cached CDN).

---

## [1.1.9] - 2026-04-08

### Fixed

- **CI / Linux binaries** (`.github/workflows/publish-ember-qc.yml`):
  pre-compiled Linux binaries shipped in v1.1.6 – v1.1.8 were built on
  `ubuntu-latest` (= ubuntu-24.04, glibc 2.39 / GLIBCXX 3.4.32) and failed to
  load on any older Linux with errors like
  `version 'GLIBC_2.38' not found (required by …/atom/main)` and
  `version 'GLIBCXX_3.4.32' not found`.  This made ATOM and all OCT variants
  appear to fail 100 % of trials on Debian 12 / Ubuntu 22.04 servers even
  though macOS worked.  Fix: the Linux matrix entry now pins
  `os: ubuntu-22.04` (glibc 2.35 baseline, compatible with Debian 12 and
  newer) and both compile commands add `-static-libstdc++ -static-libgcc` so
  the libstdc++ dependency is baked into the binary and future runner bumps
  cannot reintroduce GLIBCXX skew.  An `objdump -T` verification step prints
  the required symbol versions after each Linux compile, so any future
  baseline creep is visible in CI output before release.
- No code changes in the package itself — this release exists to publish
  rebuilt, portable Linux binaries through the existing tag-triggered
  workflow.

---

## [1.1.8] - 2026-04-07

### Added

- **`ember doctor`** — new CLI command that diagnoses binary algorithm
  health on the current machine.  For each algorithm it reports:
  - Binary path and whether the file exists
  - Architecture match (`file` output vs `platform.machine()`) — catches
    Mac-compiled binaries deployed to a Linux server
  - Shared library dependencies (`ldd` on Linux, `otool -L` on macOS) with
    specific fix hints for common missing libraries (`libgomp1`, `libstdc++6`)
  - Working-directory writability check (OCT writes temp files there)
  - End-to-end **smoke test**: embeds K₄ → C(4,4,4) with a 30 s timeout and
    reports success/failure with elapsed time or the exact error
  - `--algo NAME` flag to restrict the check to one algorithm

---

## [1.1.7] - 2026-04-07

### Fixed

- **OCT** (`algorithms/oct.py`): All OCT variants now declare
  `supported_topologies = ['chimera']` (matching ATOM).  Previously OCT was
  not skipped for non-Chimera topologies; when run against a Pegasus target
  `_infer_chimera_dims()` silently fell back to a 4×4×4 placeholder, producing
  embeddings with wrong qubit labels that always failed layer-1 validation —
  the root cause of 100 % failure on Pegasus benchmarks.
- **OCT** (`algorithms/oct.py`): `subprocess.returncode` is now checked after
  the OCT binary returns.  A non-zero exit (binary crash, missing shared
  library, wrong architecture, etc.) is now logged at ERROR level with the
  first 300 chars of stderr and recorded with `status='CRASH'`, making server
  environment issues immediately diagnosable instead of silently appearing as
  `FAILURE` with an empty embedding.
- **ATOM** (`algorithms/atom.py`): Same `returncode` check and CRASH status
  added so binary execution failures on the server are clearly surfaced in
  logs and results.

---

## [1.1.6] - 2026-04-07

### Added

- `load_test_graphs()` now shows an inline progress bar when loading 50 or
  more graphs.  For large selections (30,000+) the load + integrity-verify
  phase could take several minutes with no output; the bar updates on every
  graph loaded and switches to a "Verifying integrity…" message during the
  SHA-256 pass, finishing with a total count and elapsed time.

---

## [1.1.5] - 2026-04-07

### Fixed

- `_load_results_from_jsonl()` now skips malformed JSONL lines instead of
  raising `json.JSONDecodeError`.  Previously, a line corrupted by a mid-run
  crash (e.g. server reboot) would be correctly skipped by
  `completed_seeds_from_jsonl()` during task-list recovery, causing the task
  to be re-run and its new result appended to the same file — but the old
  corrupted line would remain mid-file and crash the final compile step when
  `_load_results_from_jsonl()` processed it.

---

## [1.1.4] - 2026-04-07

### Fixed

- `unfinished_dir = "child"` (and `"default"`) now work correctly end-to-end.
  Three related bugs were fixed:

  1. **Write path** — `EmbeddingBenchmark.__init__` was resolving `"child"`
     against a placeholder `results_dir="./results"` before the real
     `output_dir` was known, staging cancelled runs in `./results/.runs_unfinished/`
     relative to CWD rather than `output_dir/.runs_unfinished/`.
     `ResultsManager` creation is now deferred to `run_full_benchmark()` where
     the real `output_dir` is available.

  2. **Read path** — `load_benchmark()` and `delete_benchmark()` treated any
     non-empty `unfinished_dir` string as a literal `Path()`, so `"child"` and
     `"default"` were looked up as literal directory names.  Both now go through
     `resolve_unfinished_dir()` unconditionally.

  3. **CLI resume** — `cmd_resume` hardcoded `get_user_unfinished_dir()` for
     the `--delete-all` path, ignoring config.  All three resume code paths now
     share a single resolved staging directory derived from config.
     `delete_benchmark` gains an `output_dir` parameter to support `"child"` mode.

---

## [1.1.3] - 2026-04-07

### Fixed

- Pressing `q` to cancel a running benchmark no longer crashes with
  `IndexError: tuple index out of range` when writing the checkpoint.
  `write_checkpoint()` expects the full 8-element task tuple
  `(source_graph, target_graph, algo_name, graph_id, graph_name, topo_name, trial, trial_seed)`
  and indexes into it starting at position 2; the two call sites in
  `benchmark.py` were incorrectly pre-slicing the tuples down to 5 elements
  before passing them.  Both call sites now pass the raw tuples unchanged.

---

## [1.1.2] - 2026-04-07

### Fixed

- `parse_graph_selection()` now normalises en dashes (–) and em dashes (—)
  to hyphens before parsing.  macOS autocorrects the hyphen in range specs
  like `5550-8802` to an en dash in some input contexts, causing a
  `ValueError: Invalid ID or unknown preset`.

---

## [1.1.1] - 2026-04-07

### Fixed

- Updated `docs/results-schema.md`, `docs/reproducibility.md`, and
  `docs/getting-started.md` to reflect the v1.1.0 schema change: `problem_name`
  replaced by `graph_id` + `graph_name` in column tables, uniqueness constraint,
  seed formula, and code examples.

---

## [1.1.0] - 2026-04-07

### Changed (breaking)

- **Graph ID as unique benchmark key** — `problem_name` has been replaced by
  `graph_id` (integer manifest ID) + `graph_name` (human-readable label) throughout
  the entire pipeline. `graph_id` is definitionally unique across the library,
  eliminating silent result loss caused by graphs sharing the same name.

  - `load_test_graphs()` now returns `List[Tuple[int, str, nx.Graph]]`
    (`graph_id`, `name`, `graph`) instead of `List[Tuple[str, nx.Graph]]`.
    User-supplied problems (2-tuples) are accepted and normalised automatically
    with `graph_id = 0`.
  - `EmbeddingResult.problem_name` renamed to `graph_name`; `graph_id: int`
    field added.
  - `benchmark_one()` parameters `problem_name` → `graph_name`, `graph_id` added.
  - `_derive_seed()` now keys on `graph_id` instead of `problem_name`; seeds
    for identical tasks will differ from v1.0.x runs.
  - `results.db` schema: `graphs` table primary key is now `(graph_id, graph_name)`;
    `runs` table replaces `problem_name` with `graph_id` + `graph_name`; UNIQUE
    constraint is `(algorithm, graph_id, graph_name, topology_name, trial, seed)`.
    Old databases can still be recompiled (`problem_name` falls back gracefully).
  - `runs.csv` export includes `graph_id` and `graph_name` instead of `problem_name`.

- **Structural graph deduplication** — `load_test_graphs()` silently skips
  duplicate graph IDs (identical graph re-issued with a different ID during
  library generation) when the canonical (lowest) ID is also in the selection.
  `load_graph()` redirects duplicate IDs to their canonical counterpart, so
  only one copy is ever downloaded or cached. Both behaviours become no-ops if
  duplicates are later removed from the manifest.

- **`_graph_topo_compatible` uses graph ID** — topology lookup is now a direct
  `_manifest_by_id` call instead of a name-based lookup, removing the need for
  any name-parsing heuristics.

### Fixed

- Legacy checkpoint format (pre-v1.1) is handled gracefully on resume: if
  checkpoint tasks lack a `graph_id` key, ember falls back to JSONL-only
  recovery and prints a notice rather than crashing with a `KeyError`.

---

## [1.0.5] - 2026-04-07

### Fixed

- **Duplicate results on resume** — in parallel mode, workers write results
  directly to their `worker_{pid}.jsonl` files independently of the result
  queue. When the user cancels, the main process drains the queue for
  `cancel_delay` seconds, but a worker can write to JSONL and enqueue a result
  faster than the drain consumes it. Any result written to JSONL but not yet
  consumed from the queue when the drain ends was being recorded as "unfinished"
  in the checkpoint, causing it to run again on resume and produce a duplicate
  JSONL entry that `compile_batch` would skip. Fixed by always scanning the
  JSONL files when loading a checkpoint and excluding any task already present
  in JSONL from the remaining set, regardless of what the checkpoint says.

- **"Starting benchmark" run count off by a small amount** — `total_measured`
  was computed from a formula before `all_tasks` was built, so edge cases
  (silently skipped graph load failures, name collisions across filter sets)
  could make the displayed count differ from the actual task count. Now
  `total_measured` is set to `len(all_tasks)` after the task list is fully
  built, and `config.json` is updated accordingly. The progress bar and
  checkpoint now always reflect the exact planned trial count.

---

## [1.0.4] - 2026-04-07

### Added

- **Graph-topology compatibility pre-filter** — before any trials run, ember
  now checks whether each graph is compatible with each topology being
  benchmarked. Incompatible pairs are skipped entirely; no trials are launched
  and no timeouts are wasted. At full library scale, 7,149 of 31,083 graphs are
  incompatible with Chimera — without this filter those trials would all timeout.

  Compatibility is resolved in two layers:
  1. **Manifest topology field** — every library graph has a precomputed
     `topologies` list (e.g. `["pegasus", "zephyr"]`) stored in `manifest.json`.
     Checked via prefix match (`"chimera_16x16x4"` matches `"chimera"`), the
     same style as the existing algorithm-topology check.
  2. **Size fallback** — for custom (user-supplied) graphs not in the manifest,
     falls back to a necessary-condition size check: the problem graph must have
     no more nodes *and* no more edges than the target topology.

  A pre-run summary line is printed reporting how many graph/topology pairs and
  trials were skipped. `total_measured_runs` in `config.json` and the progress
  bar reflect the actual planned trial count rather than the inflated total.
  The same filter is applied when rebuilding the task list in `load_benchmark`
  (resume) for consistency.

- **Manifest lookup cache** — `_manifest_by_name()` added to `load_graphs.py`:
  a `lru_cache`-backed dict of `name → manifest entry` built once from the
  already-cached `_manifest_by_id()`. Zero cost after first call.

- **Manifest and manifest-by-id caching** (`lru_cache`) — `load_manifest()` and
  `_manifest_by_id()` are now decorated with `@functools.lru_cache(maxsize=None)`
  so the manifest JSON is parsed only once per process and the 31,083-entry
  normalised dict is built only once. Previously both were recomputed on every
  `load_graph()` call — with 4,490 physics graphs this caused ~139 million
  redundant `_normalize_entry` calls before a single trial ran (visible as a
  multi-minute hang at startup).

---

## [1.0.3] - 2026-04-07

### Fixed

- **Tilde not expanded in `output_dir` paths** — paths containing `~` (e.g.
  `~/ember_results` set via `ember config set output_dir ~/ember_results`) were
  treated as a literal `~` directory name instead of the user's home directory,
  producing paths like `/home/user/~/ember_results/`. Added `.expanduser()` to
  all `Path(output_dir)` calls in `benchmark.py` and `config.py`.
- **"Results saved to \<staging path\>"** — `save_results()` printed the
  pre-move staging directory path rather than the final output location. Removed
  that header line; callers already print `Results: <final_dir>` after
  `move_to_output()`. The file-tree lines are still printed.

---

## [1.0.2] - 2026-04-06

### Added

- **`unfinished_dir` config key** — controls where in-progress benchmark runs are staged.
  Three modes: `"default"` (platform user data dir, e.g. `~/.local/share/ember-qc/runs_unfinished/`),
  `"child"` (`.runs_unfinished/` inside the output directory — guarantees same filesystem for
  atomic renames on servers), or any explicit directory path. Set via
  `ember config set unfinished_dir child` or `EMBER_UNFINISHED_DIR` environment variable.
- **`--verbose` / `--no-verbose` / `--analyze` flags** on `ember resume`, matching the flags
  already available on `ember run`.

### Fixed

- **Output directory crash** — `run_full_benchmark` now validates and creates the output
  directory at run start (fail-fast). Previously the run completed all trials then crashed
  with `OSError` when trying to save, losing all results.
- **Cross-filesystem move data loss** — `ResultsManager.move_to_output` rewritten to use
  atomic `Path.rename` first (same filesystem), falling back to explicit `copytree` + `rmtree`
  with proper error recovery. The copy is verified before the source is removed; any copy
  failure leaves the run fully intact in staging for recovery via `ember resume`.
- **Write-before-move** — all output files (`results.db`, `summary.csv`, `README.md`,
  `runs.csv`) are now written into the staging directory before `move_to_output` is called.
  A move failure no longer causes data loss.
- **Stale destination cleanup** — `move_to_output` removes any stale destination directory
  left by a previous failed move before attempting the rename/copy.
- **Post-move existence check** — `move_to_output` raises `RuntimeError` if the destination
  directory does not exist after the move, making silent failures detectable.
- **Resume output directory** — `output_dir` is now saved as an absolute path in `config.json`
  at run start. `load_benchmark` reads it back so resumed runs save to the correct location
  rather than falling back to the ember-qc user data directory.
- **Resume progress bar** — `ember resume` now shows the progress bar immediately (before the
  first trial completes) and displays the correct total context, e.g. `[45/100]` instead of
  `[0/30]`, so resumed runs show overall progress rather than only the remaining portion.
- **Resume with zero remaining tasks** — when all trials completed but the batch was not yet
  compiled (crash during save), `load_benchmark` now compiles and saves results correctly
  instead of silently returning without producing output files.
- **Resume completion output** — `load_benchmark` now prints the same completion summary as
  `run_full_benchmark`: wall time, results path, warning summary, and closing banner.
- **`unfinished_dir` fallback** — `EmbeddingBenchmark.__init__` and `load_benchmark` now
  both use `resolve_unfinished_dir` from `config.py` so the fallback location is always
  consistent with the config setting.
- **`results.py` save safety net** — `save_results` now calls `batch_dir.mkdir(parents=True,
  exist_ok=True)` before writing, preventing `OSError` if the staging directory was removed.

---

## [1.0.1] - 2026-04-06

### Changed

- Updated `README.md`, `docs/graph-library.md`, `docs/cli-reference.md`, and
  `docs/getting-started.md` to reflect the 1.0.0 graph library overhaul: new ID
  ranges, 36 graph types, 13 presets, full `ember graphs` CLI reference, and
  corrected quick-start example using the `installed` preset.

---

## [1.0.0] - 2026-04-06

### Added

**Graph library — 31,083 graphs across 36 types**

- Full graph library hosted on HuggingFace (`zachmacsmith/ember-graphs`), covering
  structured, random, physics-lattice, and hardware-native topologies.
- 37 graphs bundled with the package spanning 35 types for offline use; the rest
  are downloaded on demand and cached locally.
- New graph types: `hardware_native` (Chimera/Pegasus/Zephyr identity-embeddable
  topologies), `planted_solution` (random subgraphs of hardware graphs), `named_special`
  (Petersen, Tutte, House, Chvátal, McGee, Franklin), `triangular_lattice`, `kagome`,
  `honeycomb`, `king_graph`, `frustrated_square`, `shastry_sutherland`, `cubic_lattice`,
  `bcc_lattice`, `weak_strong_cluster`, `spin_glass`, `random_planar`, `lfr_benchmark`,
  `sbm`, plus extensions to existing structured and random types up to n ≈ 5,000+.
- `manifest.json` updated to abbreviated key format (`n`, `e`, `d`, `h`, `sz`, `p`,
  `topo`) — reduces file size; `_normalize_entry()` expands keys transparently at load time.

**`load_graphs.py` — three-layer loader**

- Layer 1: local user cache (`~/.local/share/ember-qc/graphs/`).
- Layer 2: bundled package files (`ember_qc/graphs/library/{id}_{name}.json`).
- Layer 3: remote download from HuggingFace with atomic write (temp + rename) and
  SHA-256 prefix verification before caching.
- `_hf_subdir()`: routes download URLs to the correct HF subdirectory; handles the
  `watts_strogatz_k{k}/` split used to stay under HF's 10,000 files-per-directory limit.
- `_hash_ok()`: accepts both full 64-char SHA-256 and the 16-char prefix stored in
  the manifest; used at every integrity-check site.
- `_bundled_id_set()` / `_is_installed()`: new helpers that count both bundled and
  cached files as "installed" — fixes `list_graph_types()`, `list_graphs_of_type()`,
  and `graph_info()` which previously reported 0 installed graphs despite bundled files.
- New public functions: `list_graph_types()`, `list_graphs_of_type()`, `graph_info()`,
  `install_graphs()`, `cache_summary()`, `delete_from_cache()`, `verify_cache()`,
  `search_graphs()`.
- `load_test_graphs()`: pre-filters by node count against the manifest before
  downloading, avoiding unnecessary network requests.
- All graph selection — CLI install, cache delete, benchmark loader — goes through
  the same `parse_graph_selection()`, so `"1000-1010, !1005"`, preset names, and
  `"*"` work identically everywhere.

**`ember graphs` CLI — full subcommand suite**

- `ember graphs list` — type overview: ID ranges, total count, installed count.
- `ember graphs list <type>` — per-graph table with nodes, edges, installed status.
- `ember graphs list -a` — restrict to installed types/graphs only.
- `ember graphs info <id>` — full metadata; reads live from file when installed.
- `ember graphs install <spec>` — download by ID range, selection string, or preset;
  `--dry-run` previews without downloading.
- `ember graphs presets` — lists all named presets with resolved graph counts.
- `ember graphs search` — filter by `--type`, `--topology`, `--min-nodes`,
  `--max-nodes`, `--min-edges`, `--max-edges`, `-a`.
- `ember graphs cache` — disk usage summary with per-type breakdown.
- `ember graphs cache delete <spec>` — remove specific graphs; `--all` wipes cache.
- `ember graphs verify` — SHA-256 integrity check on all cached graphs;
  `--fix` re-downloads and repairs corrupt files.

**Presets (`graphs/presets.csv`)**

- 13 named presets replacing the old ID-based set: `all`, `installed`, `quick` (12),
  `default` (36), `diverse` (31), `benchmark` (82), `structured` (2,568),
  `lattice` (820), `physics` (4,490), `hardware_native` (42), `named_special` (12),
  `small` (617).

### Fixed

- **Bundled library mismatch**: 20 files in `graphs/library/` had IDs that were
  reassigned to different graph types during the library ID overhaul. Loading any of
  them would raise `RuntimeError: Bundled graph ... failed integrity check`. All 20
  removed; replaced with correct small examples for the previously uncovered types.
- **`list_graph_types()` / `list_graphs_of_type()` / `graph_info()` always reported
  installed=0**: these functions only checked the user cache directory, ignoring the
  37 graphs bundled with the package. Fixed via new `_bundled_id_set()` helper.
- **`load_graphs.py` module docstring** incorrectly described the library structure as
  `library/<category>/<id>_<name>.json` (old nested layout); corrected to flat
  `library/{id}_{name}.json`.


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
