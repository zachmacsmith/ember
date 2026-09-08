# Ember benchmark audit for the Codex research plan

Date: 2026-09-07. Scope: read the current benchmark, manifest, saved evidence and selected tests; perform small local reproductions; propose a defensible experiment protocol. This audit does not implement an embedding algorithm, run a large benchmark, or access the cluster. Earlier claims are treated as hypotheses. The user's clarified requirement is **one algorithm, with no MM or busclique calls and no portfolio of independent methods**; slower execution is acceptable if mean ACL improves. The selected target is now **ideal Z12**; other sizes and defective targets are deferred.

## What the present evidence establishes

The frozen handoff CSVs support the arithmetic in most of the displayed 10-cell table. They do **not** establish valid, independent, equal-budget superiority on all Ember families. There are 36 manifest categories; the development board represents only nine of them. Its `new+mm` and `old` arms explicitly include MM. Its `new` arm, configured with `tail='none'`, reports worse ACL than MM on the regular, Watts–Strogatz, grid, honeycomb and king-graph cells. The board does not independently validate its returned embeddings or save embedding witnesses, so even its positive ACL results require reconstruction and revalidation.

**Clarification after the source audit:** the original version of this note called the `new` arm independent based on its `tail='none'` setting. That inference was incorrect: the algorithm audit found hidden MM legalization/fallback paths even with that setting. The unchanged CSV arithmetic describes the named experimental arm; it does not establish MM-free execution. See `notes/codex/algorithm_audit.md`. The validation findings below describe the audited starting version; subsequent repairs are recorded separately in `notes/codex/experiments/001_validation.md`.

There are several repairable problems in the benchmark and analysis code, including an algorithm-controlled target override in validation, analysis keys that merge different graph IDs, and inadequate structural deduplication. None of these proves that a specific archived win was false. They prevent treating an unchecked summary as proof.

## Actual graph taxonomy and target scope

The authoritative bundled manifest is `packages/ember-qc/src/ember_qc/graphs/manifest.json:1`: version `1.3.2`, **31,149 entries, 36 categories**. The following counts and size ranges were computed directly from its `graphs` entries. They are raw entry counts, before deduplication or target feasibility filtering.

| Category | Entries | Source vertices, minimum–maximum |
|---|---:|---:|
| barabasi_albert | 3,532 | 3–5,640 |
| bcc_lattice | 26 | 35–6,119 |
| binary_tree | 11 | 3–4,095 |
| bipartite | 208 | 4–492 |
| circulant | 351 | 5–5,640 |
| complete | 56 | 2–287 |
| cubic_lattice | 76 | 8–4,913 |
| cycle | 65 | 3–5,640 |
| frustrated_square | 72 | 9–5,184 |
| generalized_petersen | 782 | 8–5,640 |
| grid | 149 | 4–5,625 |
| hardware_native | 42 | 8–4,928 |
| honeycomb | 162 | 8–5,830 |
| hypercube | 11 | 4–4,096 |
| johnson | 74 | 10–2,002 |
| kagome | 144 | 12–5,824 |
| king_graph | 72 | 9–5,184 |
| kneser | 41 | 10–406 |
| lfr_benchmark | 61 | 50–3,000 |
| named_special | 12 | 5–46 |
| path | 65 | 3–5,640 |
| planted_solution | 2,616 | 25–1,318 |
| random_er | 3,024 | 10–4,283 |
| random_planar | 216 | 10–1,167 |
| regular | 3,521 | 6–5,640 |
| sbm | 1,125 | 20–600 |
| shastry_sutherland | 72 | 4–1,369 |
| spin_glass | 598 | 10–958 |
| star | 64 | 4–5,316 |
| sudoku | 2 | 6,561–65,536 |
| tree | 27 | 7–5,461 |
| triangular_lattice | 196 | 9–2,926 |
| turan | 607 | 3–428 |
| watts_strogatz | 12,550 | 6–5,640 |
| weak_strong_cluster | 456 | 16–5,640 |
| wheel | 63 | 4–5,316 |

An overall average over raw entries would be strongly influenced by Watts–Strogatz (40.3% of entries). It cannot substitute for a per-family claim.

The `installed` preset resolves to 37 entries in 35 categories; `quick` to 12 in 12; `default` to 36 in 36; `diverse` to 31 in 26; `benchmark` to 82 in 33. Thus none of these names by itself establishes representative coverage. The two Sudoku entries are absent from `installed`; `default` includes a capacity-impossible Sudoku entry for Z12. Evidence: `graphs/presets.csv`, parsed with the current loader. There are 37 bundled graph files; the much older `test_graphs/` tree is a different library and must not silently define modern Ember coverage. The handoff's description of the bundled files as old IDs 1–60/100–199 is stale (`docs/handoff/EXPERIMENTS.md:69`).

Current registered targets are Chimera sizes 4, 8, 12, 16 with shore size 4; Pegasus sizes 4, 6, 8, 16; Zephyr sizes 2, 4, 6, 12 with default shore size 4 (`topologies.py:133`, `:150`, `:165`). The development board uses `dnx.zephyr_graph(12, 4)` and small fingerprints also use Z3. Direct generation with the installed package yielded:

| Zephyr size | Qubits | Couplers | Maximum degree |
|---|---:|---:|---:|
| Z2 | 160 | 1,224 | 19 |
| Z3 | 336 | 2,808 | 20 |
| Z4 | 576 | 5,032 | 20 |
| Z6 | 1,248 | 11,400 | 20 |
| Z12 | 4,800 | 45,864 | 20 |

**A literal win on every current category at Z12 is impossible.** Sudoku IDs 37900 and 37901 have 6,561 and 65,536 vertices (and 734,832 and 24,084,480 edges). Both exceed Z12's qubit and coupler counts. Every valid minor embedding requires nonempty, disjoint chains, so a source with more than 4,800 vertices cannot fit. This is a proof of infeasibility, not algorithm failure. Both entries nevertheless list `['chimera', 'pegasus', 'zephyr']` in their manifest topology annotations. Keep these cases visible as proved infeasible. To study Sudoku quality on Zephyr, explicitly agree to add smaller correctly generated instances or use a sufficiently larger Zephyr target; do not silently redefine the family or exclude its inconvenient rows. Similar capacity exclusions apply to large instances in many other categories.

`benchmark.py:515` returns immediately from a nonempty manifest topology annotation, before its node/edge capacity checks at `:526`. Consequently a family annotation can admit impossible instances even on the smallest target of that family. Conversely, an incorrect annotation can exclude valid cases. Manifest tags are not embeddability certificates.

Applying only the necessary bounds `source_vertices <= 4800` and `source_edges <= 45864` to the raw manifest leaves **30,200 entries** and excludes **949**. Vertex count alone excludes 928; edge count alone excludes 23; two fail both bounds. These are raw metadata counts, before structural deduplication; passing the bounds does not prove embeddability. Excluded counts by affected category are: barabasi_albert 116, bcc_lattice 4, circulant 14, cubic_lattice 2, cycle 2, frustrated_square 2, generalized_petersen 27, grid 6, hardware_native 1, honeycomb 11, kagome 14, king_graph 2, kneser 3, path 2, random_er 15, regular 146, spin_glass 3, star 1, sudoku 2, tree 1, watts_strogatz 562, weak_strong_cluster 12, wheel 1. All other categories have zero exclusions under just these two bounds.

## Definitions and analysis problems

For a nonempty valid embedding of source graph G, ACL is `sum_v len(C_v) / |V(G)|`, equivalently used qubits divided by source vertices. The normal benchmark computes a mean over returned chains after its validation pipeline (`benchmark.py:135`, `:330`, `:355`, `:376`). `evaluate()` additionally reports population standard deviation across chain lengths **within one embedding** (`benchmark.py:222`). This is different from variance of ACL over independent algorithm runs on the same graph (`:190`). The research must distinguish within-embedding chain dispersion, within-instance across-run ACL variance, and variation of difficulty across different source graphs.

The analysis summaries filter to successful trials before averaging ACL and timing (`ember_qc_analysis/summary.py:38`, `:55`, `:102`). `overall_summary.chain_std` pools ACL over different graphs and topologies, so it is not the requested within-instance algorithm variability. Success-only times also omit expensive failed attempts. A solver can appear better by failing on hard inputs; report every attempted run and its status alongside any conditional quality mean.

`ember_qc_analysis/statistics.py:26` and `summary.py:134` group by **algorithm and graph_name**, omitting graph_id and topology. Distinct graphs with the same name, or the same source on different targets, are merged. A small in-memory reproduction with graph IDs 1 and 2 sharing `graph_name='collision'` and ACLs `(2,8)` versus `(3,7)` returned one row with `(5,5)`. This is a reproducible analysis defect. Use immutable graph and target fingerprints plus IDs, run configuration and replicate identifiers; never use graph_name as a join key.

The batch seed is deterministic, but `_derive_seed` includes the algorithm name (`benchmark.py:467`). Thus matching `trial` and root seed does not imply matching numeric RNG seeds across algorithms, unlike the development board's explicit seeds. Different numeric seeds are not intrinsically unfair, because different algorithms use random numbers differently; however the pairing design and seed generation must be recorded accurately. Source-generator seeds, algorithm seeds, relabeling seeds and target-defect seeds are different experimental dimensions.

Failure fields have zero-valued default quality metrics (`benchmark.py:82`), while `evaluate(None,...)` returns zeroed metrics (`:206`). Those zeros must never enter an ACL mean or be interpreted as good quality. `total_couplers_used` presently counts induced couplers internal to chains (`benchmark.py:151`), not all inter-chain logical couplers; label it accordingly if used.

## Independently reproduced validation weaknesses

The production path has useful coverage, nonempty-chain, connectivity, disjointness, edge-preservation, membership and type checks (`validation.py:63`, `:183`). It should be retained and made target-immutable. Two concise in-memory probes expose gaps:

```python
evaluate({0: [0], 1: [1], 2: [2]}, nx.path_graph(2), nx.path_graph(3))['valid']
# Observed True: the extra source key is accepted by evaluate().
```

`evaluate()` calls only Layer 1 and computes metrics before validation (`benchmark.py:222`), although Layer 1 documents that Layer 2 is a precondition (`validation.py:90`). The normal production path does run Layer 2 and rejects an extra key. This gap is specific to callers using `evaluate()` or Layer 1 alone as a complete verifier.

```python
# Registered a temporary in-memory algorithm whose embed() returns:
{'embedding': {0: [0], 1: [1], 2: [2]}, 'chimera_graph': nx.complete_graph(3)}
# benchmark_one(nx.complete_graph(3), nx.path_graph(3), temporary_name)
# Observed: status='SUCCESS', success=True, is_valid=True, ACL=1.0.
```

The requested target path has no edge joining its endpoints, so that returned embedding is invalid on the requested target. `benchmark.py:358` lets an algorithm replace the structural validation target through `result['chimera_graph']`. Layer 2 checks original target membership, but it cannot detect invented edges among existing nodes. All research results must be checked against the exact immutable requested target graph. A solver's topology change can only be a separately identified experiment.

No source changes were made to run these probes; the temporary registry binding existed only within the Python process.

## Duplicate graphs and experiment leakage

The current loader identifies **7,088 alias IDs** and **2,739 IDs with name collisions** from the manifest. Its purported structural fingerprint is `(nodes, edges, sorted(parameters))` within a shared name (`load_graphs.py:180`, `:185`, `:196`). It never compares adjacency. Equal counts and parameters do not prove equal or isomorphic graphs; unequal names hide duplicates. All manifest file-hash prefixes are distinct, which is unsurprising because JSON metadata includes IDs/names and is not a topology-only hash. Bulk selection removes aliases when their canonical IDs are also selected (`load_graphs.py:631`). Audit any single-ID redirect separately before relying on the selected ID as the actual source identity.

Actual NetworkX isomorphism checks on only the 37 bundled graph files confirmed these examples:

| Isomorphic source structures | IDs |
|---|---|
| K10 and fully connected spin-glass graph | 1008, 36904 |
| K2,2, 2×2 grid, Q2, 2×2 Shastry–Sutherland | 1200, 1553, 4750, 33000 |
| Cube and generalized Petersen G(4,1) | 33200, 3800 |
| Path on three vertices and Turán T(3,2) | 2000, 2600 |
| Petersen graph and Kneser KG(5,2) | 37760, 5400 |

Grouping by family or generator seed alone will therefore leak identical structural problems between train/development and test sets. Preserve all legitimate family memberships, but keep isomorphic copies in the same split and account for shared structure in inference. Use topology-only canonical fingerprints where feasible; use cheap structural invariants to propose buckets followed by exact isomorphism verification for ambiguous cases. A Weisfeiler–Lehman hash alone is not an isomorphism proof.

The published-in-repo 10-cell board, its seeds, acceptance thresholds and prior full-library experiments are all development data now. Fresh algorithm RNG seeds on the same heavily tuned graph are not fresh graph generalization evidence. Hold out new generator instances, some sizes/densities/defect realizations, and graph structure groups. Once a held-out result informs tuning it becomes development data; preserve a remaining final test set. The `hardware_native` category especially needs relabeling and attribute-sanitization probes to detect source-coordinate or target-identity leakage. Embedding is driven by unweighted adjacency here; changes to spin-glass coupler signs can produce the same embedding problem and must not be counted as independent structural instances.

`load_test_graphs()` catches a graph download/load exception and prints a warning while continuing (`load_graphs.py:683`). A complete claimed benchmark needs an explicit expected-task ledger and missing-data audit; an unavailable graph must not simply vanish from denominators.

## What the frozen board actually reports

Evidence files: `docs/handoff/baseline/rewrite_board_mm.csv`, `rewrite_board_new-newmm.csv`, `rewrite_board_old.csv`; summarized claims in `docs/handoff/baseline/RESULTS.md:44`. The three CSVs contain 58, 116 and 58 rows. The following means were independently recalculated from the frozen rows; they remain **unverified embedding claims** because witnesses are absent from these CSVs.

| Cell | Trials per arm | Stock MM ACL | Reported `new` ACL | `new` mean wall, seconds | MM mean wall, seconds |
|---|---:|---:|---:|---:|---:|
| K100 | 3 | 10.467 | 7.260 | 21.3 | 61.6 |
| K140 | 3 | 20.286 (2 successes) | 9.766 | 37.8 | 65.8 |
| spin_glass_n163 | 3 | 20.564 | 10.849 | 44.2 | 60.8 |
| turan_n162 | 10 | 11.304 | 6.000 | 215.5 | 62.3 |
| ER100_d10 | 10 | 4.818 | 4.599 | 28.0 | 6.1 |
| regular_n316 | 10 | 3.590 | 4.747 | 139.3 | 4.8 |
| ws_n486 | 10 | 3.144 | 4.401 | 341.7 | 7.2 |
| grid_200 | 3 | 1.082 | 1.590 | 66.7 | 0.5 |
| honeycomb_200 | 3 | 1.160 | 1.890 | 62.4 | 0.7 |
| king_graph_196 | 3 | 1.760 | 2.561 | 72.0 | 1.8 |

The board's MM arm calls `minorminer.find_embedding(source_graph, target_edges, random_seed=seed, timeout=60)` (`docs/paper2/data/rewrite_board.py:75`). The `new` arm calls the engine with `tail='none'`, graph-specific work budgets and a 1,800-second safety timeout (`:82`), but that setting does not exclude the hidden MM legalization/fallback paths found by the source audit. `new+mm` calls the engine with `tail='mm'` and a 60-second timeout (`:85`); `old` uses the former defaults with the MM tail. None of these arm configurations by itself establishes the user's independence constraint. Slower execution is now acceptable, but elapsed work must still be reported accurately and compared with strengthened MM quality baselines.

The board counts any nonempty returned embedding as success, divides by the number of returned keys, rounds ACL to three decimals, and saves only summary fields (`rewrite_board.py:89`). It bypasses both validation layers. Its summary globs every `rewrite_board_*.csv`, without an experiment-ID deduplication rule, and forms a dictionary keyed by seed for MM while averaging all selected arm rows (`:108`, `:126`). Duplicate runs or different versions in that directory can therefore be pooled asymmetrically. The frozen handoff files can be read individually, but the live glob summary is unsafe for publication. The baseline comparison drops failed pairs before computing mean deltas and uses tolerance `max(0.05, 2% of old ACL)` (`docs/handoff/compare_baseline.py:47`, `:109`), which is a development tolerance rather than statistical evidence.

## Timing, baselines and archived breadth

The stock registered `minorminer` adapter passes only source graph, target edge list, timeout, verbosity and `random_seed`; other supplied kwargs are ignored (`algorithms/minorminer.py:21`). Passing the source as a graph preserves isolated source vertices. Target edge-list conversion can discard isolated target vertices on defective targets; pass graph objects or otherwise retain those vertices in a corrected baseline. Pin and record the actual MM version and parameter values rather than assuming library defaults cannot change.

The repo also contains aggressive, fast, chainlength and layout MM adapters (`algorithms/minorminer.py:46`, `:73`, `:100`, `:127`). The layout adapter docstring calls itself the primary baseline, while the handoff board uses stock MM. The user's stock-MM goal should set the primary comparison; layout and stronger MM runs are useful secondary reference curves and a defense against a weak-baseline explanation.

Normal `benchmark_one` measures `perf_counter` around `embed()`; graph loading and post-return validation are excluded (`benchmark.py:299`). This appropriately includes algorithm-specific construction and repair if they run inside `embed()`. Batch warmups are skipped with multiple workers or lazy loading (`benchmark.py:1697`). JIT/import/cache cost can therefore depend on worker assignment. Distinguish cold-start and explicitly prewarmed measurements, without silently excluding graph-dependent preparation.

Parallel trials have a hard cap of `max(120 seconds, 5 × cooperative timeout)` (`benchmark.py:1075`). A nominal 60-second experiment can run for 300 seconds before it is killed, and success is not automatically invalidated for finishing after the nominal deadline. The board itself has no equivalent parent-enforced per-job timeout. Quality-at-time comparisons need actual timestamps and an explicit deadline rule, with the most recent independently validated incumbent saved before the deadline. A watchdog's grace period is operational overhead, not extra search time to credit.

Read-only inspection of saved configs found older full-library Z12 experiments with 30,221 requested problems, **one trial**, 60 workers, 60-second timeout and root seed 4242. Their methods are `minorminer`, `p3-template`, `p3-ate`, `p3-clmm`, `p3-mmpolish` (`results/m5full_z12/batch/config.json`). The analogous Chimera/Pegasus configs also have one trial. Such data cannot estimate across-seed ACL variance. Read-only SQLite queries found 25,010 one-trial `minorminer-layout` rows in `m5full_z12_layout` and 30,201 one-trial rows per algorithm in `t2_z12` (`p3-ember`, `p3-mm-beta-fb`). They concern older implementations. Opening `m5full_z12` SQLite in ordinary read-only mode failed locally; no completeness claim about that database was inferred. Existing database/WAL files were not modified.

The local environment is not the handoff environment:

| Component | Local observed | Handoff claim |
|---|---|---|
| Python | 3.10.19 | 3.11.2 |
| networkx | 3.4.2 | 3.6.1 |
| numpy | 2.2.6 | 2.4.6 |
| numba | 0.65.1 | 0.67.0 |
| minorminer | 0.2.22 | 0.2.22 |
| dwave-networkx | 0.8.19 | 0.8.19 |
| pytest / pytest-timeout | 9.1.1 / 2.4.0 | 9.1.1 / 2.4.0 |

Local values came from `importlib.metadata` and `sys.version`; claimed values are `docs/handoff/EXPERIMENTS.md:18`. Reproduction needs an explicit environment lock and native/JIT build information.

## Proposed evidence protocol

1. **Freeze scope before selecting wins.** Enumerate every manifest family, source structure group, size/density stratum, ideal Z12 adjacency, and necessary infeasibility exclusion. Other sizes and defective targets are deferred by the user's scope decision. Resolve the Sudoku scope visibly. Retain simple and native instances, including provable ACL=1 ties. For any valid embedding ACL is at least 1; strict improvement over an MM result already at 1 is mathematically impossible. The achievable claim is strict per-family mean improvement wherever there is headroom, and optimal ties where there is none, with the precise exceptions stated.
2. **Repair and verify the evaluator first.** Require exactly the source vertex set, finite nonempty disjoint connected chains inside the original target, and every logical edge realized. Revalidate stored witnesses in a separate process against frozen source/target hashes. Check `total_qubits / source_nodes == ACL`; retain full precision and integer totals. Reject forbidden dependency use with source inspection plus dynamic call interception under a clean process. An existing MM-derived embedding or graph-specific embedding cache is not an independent starting point.
3. **Keep one solver and charge all its work.** Every reported candidate run is the single algorithm's own construction, optimization and repair sequence. No independent-method best-of selection, family router, MM tail, busclique tail or oracle incumbent. Algorithm variants are separate experimental hypotheses/ablations and are never combined by taking the best result per test instance. Count initialization, topology preparation, routing, repair and any internal restarts in that solver's budget; disclose offline training or topology preprocessing and amortization assumptions if introduced.
4. **Separate quality-first claims from equal-time claims.** Fix a sufficiently generous primary quality budget after a development-only pilot and before validation/test. Run stock MM at its default configuration under the same ceiling; if it terminates early, retain that as the stock-baseline behavior. Also report predeclared equal-time curves and a stronger MM parameter configuration, with any repeated-MM reference explicitly disclosed as a secondary baseline and fully charged. Suggested exploratory horizons are 1, 10, 60, 300 and 1,800 seconds, subject to cluster-resource calibration. Quality-first improvement at longer runtime is a valid measured outcome; do not label it a speed win.
5. **Use the machines as experimental blocks.** Match candidate and MM runs for a source/target/budget replicate on the same node and comparable dedicated core allocation. Randomize or interleave their order; record CPU model, physical cores, frequency/governor, memory, OS, load, thread limits and environment hashes. Do not pool raw wall times across the heterogeneous Hyde nodes. Report per-node results or a model with explicit machine effects; CPU seconds do not eliminate microarchitectural differences. Use low contention for publication timing and larger concurrency for development screening.
6. **Freeze disjoint development, validation and final-test structure groups.** The known board is development only. Generate new independent graph instances where families permit it; hold out sizes/parameter regimes as an additional generalization check. All isomorphic copies, weighted variants of the same adjacency, and relabelings stay in one split. Relabelings are robustness probes, not independent graph samples. Lock any data-driven choices before the final test and record every adaptation.
7. **Estimate across both instances and random runs.** Start with a small balanced pilot across all feasible families and size strata. Use its paired effect and variance estimates to plan final sample sizes; do not choose the number of seeds based on favorable emerging test results. Ten or more algorithm seeds per independent stochastic instance is a useful initial variance target, but required sample size must follow the precision needed. Deterministic graph families have fewer independent structures; use their legitimate size/parameter variation and acknowledge that limit. Three seeds on one graph are screening evidence only.
8. **Keep success and quality inseparable in reporting.** Show success probability, invalid outputs, timeouts/crashes, and candidate-only/MM-only failures per family. Predeclare a success noninferiority guardrail and its confidence bound. Report conditional ACL means explicitly; show results on common-success pairs as a secondary diagnostic, not the only conclusion. Include a failure-aware sensitivity loss—for example ACL on success and `|V(target)|/|V(source)| + 1` on failure, which is worse than any valid ACL for that instance—while clearly labeling it a loss rather than mean ACL. The guardrail and sensitivity analysis prevent apparent quality gains caused by selective failure.
9. **Make the graph instance the principal unit.** Average repeated trials per graph, then combine graph effects using predeclared family/size weights. Report candidate-minus-MM ACL, relative reduction, confidence intervals, seed variance per instance, and runtime distributions. Use hierarchical resampling or a suitable mixed model to respect repeated seeds, related graph structures and machine blocks. Provide simultaneous confidence coverage or multiplicity-adjusted tests for the family statements; do not rely on a pooled p-value or arbitrary development tolerance. A complete all-family claim must have support in every relevant family; inconclusive cells remain inconclusive.
10. **Make every scheduled experiment auditable.** Save expected task IDs before launching, append complete per-run records durably, include status for every attempted task, write embeddings/checksums, and record commit plus dirty diff, dependencies, parameters, seeds, host and target/source hashes. Resume by immutable task ID, never by name or ambiguous seed alone. Atomic output and detached remote execution support Wi-Fi switching; no run should depend on a live laptop SSH session. Reconcile expected versus completed versus excluded tasks before any summary. Preserve lessons from failed variants with the evidence and reason for rejection.

## Local verification performed

Command: `.venv/bin/python -m pytest tests/test_evaluate.py tests/test_faults.py tests/test_presets.py -q`.

Observed **57 passed, one dwave-networkx deprecation warning, 0.94 seconds**. These tests cover useful existing evaluation/fault/preset behavior, but their passing result does not contradict the separate reproduced validator and analysis defects. Small manifest, CSV, topology-generation, isomorphism and in-memory counterexample scripts were also run. No large embedding experiment, algorithm implementation, remote execution or claim of novel performance was made by this audit.

The untracked graph verification cache `packages/ember-qc/src/ember_qc/graphs/library/.verified.json` was confirmed by the parent agent to have existed at the start of the session and was preserved. It is not source code or performance evidence.
