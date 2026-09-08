# Revision 016: fixed refinement ablation

Protocol and snapshot recorded 2026-09-08 UTC, before revised-arm results. Design and pre-implementation critique: [contact_revision_016.md](../contact_revision_016.md). This experiment refines saved independent embeddings; it does not measure end-to-end embedding time or choose an arm separately for each graph.

## Fixed protocol

Use all 18 `native-search` incumbents from the retrieved experiment 011: all nine existing development inputs at seeds 0 and 1. Load only those saved candidate embeddings as algorithm inputs. Their corresponding `native-search-joint1` outputs are reference expectations, not inputs to reconstruction. The runner does not read MM result files.

All arms run the same `contact_polish` implementation with four passes, 512 total group attempts, beam width 1, group sizes `[1,2,3,4]`, three chain alternatives, halo 2, a 512-qubit region cap, 500000 total work units, 50000 work units per group, and at most two group orders. A work unit is the implementation's shared expansion counter: region/routing BFS pops and, when enabled, charged boundary-site scans. Every refinement call has a 60-second allowance and a 90-second worker watchdog.

| Arm | `boundary_sites` | `group_policy` |
| --- | ---: | --- |
| `legacy` | 0 | `legacy` |
| `sites16` | 16 | `legacy` |
| `groupsround_robin` | 0 | `round_robin` |
| `both` | 16 | `round_robin` |

First run all 18 legacy replays. Revised arms launch only if every replay is valid, timely, and matches the saved Joint1 embedding and quality. Matching an embedding means the same source-to-chain sets; exact chain-list equality is recorded separately. Then run all 54 revised cases. Tasks are shuffled with seed 16001 within these two phases. Each task starts from its own copy of the same saved Search incumbent; no arm output seeds another arm.

Every task executes the frozen runner under `/Users/dabh/ember/.venv/codex-native/bin/python -I` with a separate cache directory and numerical-library thread limits of one. The interpreter path is preserved rather than resolving its symlink. Isolated mode ignores `PYTHON*` environment settings; deterministic reconstruction uses the serialized integer-labeled graphs and explicit stable ordering. Imports, input loading, graph/embedding copying, and independent validation are outside refinement timing; context construction and the implementation's internal validation are inside it. Whole-process wall is saved separately for accounting only.

## Snapshot and artifacts

The [runner](../../../scripts/codex/refinement_ablation.py), all current package Python source, and package metadata were frozen before launch under [results/codex/016-refinement-ablation](../../../results/codex/016-refinement-ablation). The manifest stores exact configurations, execution order, source-file hashes, 18 case identities, and byte hashes of every copied incumbent, expected result, and graph. Raw result JSON preserves every output embedding, full accepted-move trajectory, counters, elapsed times, validity, and dependency evidence.

Source snapshot: `0240d24d46f81f2f4d63ce9675315335ddeaca3ea4513d23967609925756e1c9`.

Input experiment source snapshot: `73cca55965158b69bdbf94340cd36d701acd8fa426be191f457c4945284baeae`.

The worker verifies source and input hashes, original source/target/incumbent validity, and saved reference metrics before calling refinement. MM/busclique package checks and import blockers precede candidate imports; loaded prohibited modules are checked after execution. Each final output is independently validated against original graph copies.

Reproduction with a fresh output directory:

```sh
.venv/bin/python scripts/codex/refinement_ablation.py prepare results/codex/016-refinement-ablation-repeat
.venv/bin/python scripts/codex/refinement_ablation.py run results/codex/016-refinement-ablation-repeat
```

The prepare command refuses to overwrite a directory. Exact reproduction requires the frozen source rather than a later working-tree version. The local run was launched through exec session 41231; its durable outputs are the manifest, logs, reference gate, and result files.

## Results

All 72 tasks completed with valid embeddings within their refinement allowance. The 18 legacy replays match the saved Joint1 outputs exactly, including chain-list order, not merely ACL. Their trajectories and prior work counters also match. Three legacy stop labels are corrected from experiment 011's `no_improvement` to `group_limit`: complete-40 seed 1, king seed 1, and honeycomb seed 1. No embedding or work count changes accompany these corrections.

The combined policy has the lowest fixed-arm mean ACL in this ablation, saving 21 additional qubits across the 18 incumbents relative to legacy. Group scheduling alone accounts for 19 of that net reduction. Sites alone reproduce every legacy output embedding exactly. The combined policy differs from the group-only policy in just one of 18 cases, saving two additional qubits on ER seed 0. This is narrow evidence for an interaction, not a broad demonstration of boundary-site benefits.

| Aggregate over the same 18 incumbents | Legacy | Sites16 | Groups round-robin | Both |
| --- | ---: | ---: | ---: | ---: |
| Final qubits, sum | 3620 | 3620 | 3601 | 3599 |
| Qubits saved from Search incumbents, sum | 170 | 170 | 189 | 191 |
| Equal-source mean ACL | 2.680046 | 2.680046 | 2.665637 | 2.664248 |
| Better / equal / worse qubit count than legacy | 0 / 18 / 0 | 0 / 18 / 0 | 9 / 8 / 1 | 9 / 8 / 1 |
| Total refinement wall, seconds | 13.9399 | 14.4285 | 15.6819 | 16.1554 |
| Total refinement CPU, seconds | 13.9324 | 14.4251 | 15.6757 | 16.1518 |

The common input sum is 3790 physical qubits. Neither revised group policy dominates legacy on every trial: honeycomb seed 0 increases from 77 to 79 qubits, while seed 1 improves from 84 to 82. Its two-seed mean therefore ties. All policies still improve or tie their own valid Search starting embeddings; every accepted move is strict total-qubit descent.

Mean ACL by exact source graph, averaging the same two saved seed incumbents:

| Source | Legacy and Sites16 | Groups round-robin | Both |
| --- | ---: | ---: | ---: |
| Bipartite 30+30 | 2.466667 | 2.466667 | 2.466667 |
| Complete 100 | 7.260000 | 7.260000 | 7.260000 |
| Complete 40 | 3.850000 | 3.837500 | 3.837500 |
| Grid 8×8 | 1.328125 | 1.328125 | 1.328125 |
| Honeycomb 5×5 | 1.150000 | 1.150000 | 1.150000 |
| King 8×8 | 1.796875 | 1.773438 | 1.773438 |
| ER 80 | 3.193750 | 3.156250 | 3.143750 |
| Regular 80, degree 3 | 1.462500 | 1.450000 | 1.450000 |
| Watts–Strogatz 80 | 1.612500 | 1.568750 | 1.568750 |

These are the same development sources as experiment 011, not additional independent graph samples. The combined policy weakly improves all nine two-seed means, but the one worsening trial and the tiny number of seeds prevent a dominance claim. Its observed gains do not close any of the six sparse-input mean ACL gaps to MM documented in [011_results_review.md](011_results_review.md). No MM result file was loaded by this experiment, and no MM timing comparison is made here.

Unbiased sample ACL variances, for sources where the revised group policy changes them:

| Source | Legacy and Sites16 | Groups round-robin | Both |
| --- | ---: | ---: | ---: |
| Complete 40 | 0.0012500 | 0.0028125 | 0.0028125 |
| Honeycomb 5×5 | 0.0050000 | 0.0009184 | 0.0009184 |
| King 8×8 | 0.0004883 | 0.0010986 | 0.0010986 |
| ER 80 | 0.0569531 | 0.0488281 | 0.0413281 |
| Regular 80, degree 3 | 0.0153125 | 0.0112500 | 0.0112500 |
| Watts–Strogatz 80 | 0.0200000 | 0.0132031 | 0.0132031 |

Grid variance remains 0.00048828125; complete-100 and bipartite variance remain zero for all arms. These variances use denominator one because there are only two ACL observations per source. They describe variation across the two saved incumbents and resulting deterministic refinement trajectories, not a well-estimated distribution over fresh embeddings. They must not be confused with within-embedding chain-length variance.

## Mechanism and bounded work

| Work over 18 trials | Legacy | Sites16 | Groups round-robin | Both |
| --- | ---: | ---: | ---: | ---: |
| Group attempts | 7913 | 7903 | 8977 | 8981 |
| Accepted moves | 160 | 160 | 180 | 182 |
| Reported growing members in accepted moves | 12 | 12 | 11 | 11 |
| Total charged expansions | 3869129 | 4018959 | 3959765 | 4142004 |
| Boundary scans charged within that total | 0 | 149663 | 0 | 185475 |
| Added-site occurrences across attempted regions | 0 | 634 | 0 | 763 |
| Tree construction attempts | 250043 | 249658 | 298487 | 298533 |
| Stops: no improvement / group cap / work cap | 9 / 7 / 2 | 9 / 7 / 2 | 0 / 17 / 1 | 0 / 16 / 2 |

Site occurrences count additions per attempted region, not distinct physical sites across the experiment. Boundary work is included in the same total allowance as routing; enabling sites does not receive extra uncharged expansion capacity. Costs such as group generation and context construction still require elapsed-time measurement beyond this operation counter.

The new group schedule reaches more group attempts in aggregate. It also changes which sizes and centers are visited first, so this ablation cannot separate wider group coverage from ordering effects. Almost every revised group run reaches the total 512-attempt cap. These are bounded results, not local-optimality certificates or exhaustive neighbor-group coverage.

ER seed 0 illustrates the interaction. Legacy and Sites16 reach 217 and 214 group attempts, respectively, before exhausting work, and both finish at 269 qubits. Sites16 adds no outside-region site in those attempted groups. Groups round-robin reaches 273 attempts and finishes at 265; Both reaches 282 and finishes at 263, also at the same 500000-unit cap.

In Both's accepted trajectory, source vertex 47 changes from a two-qubit chain to singleton qubit 2845. This is the outside-region opportunity previously diagnosed in experiment 013. Group-only refinement does not take that move. Later accepted groups and final chains differ too: the combined run loses the group-only singleton gain at vertex 51 and gains reductions at other vertices. Its net two-qubit advantage therefore must not be described as the sum of independent site reductions. Complete output embeddings validate the combined result.

The sites-only arm adds 634 site occurrences but changes no final embedding in any case. Thus adding eligible sites alone did not overcome the legacy schedule's limitations on these incumbents. The combined policy's sole extra quality gain over group-only is a useful mechanism witness, while its general value remains uncertain. This experiment contains no matched halo-enlargement arm, so it does not establish that boundary sites are preferable to that alternative, nor does it establish novelty.

## Timing interpretation

The directly measured refinement totals are about 3.5% higher for Sites16, 12.5% higher for Groups round-robin, and 15.9% higher for Both than legacy. Median paired refinement-wall ratios are 1.045, 1.066, and 1.092, respectively. Both versus group-only has median ratio 1.032 and aggregate ratio about 1.030. These are descriptive ratios from single calls, not stable speed estimates.

The largest refinement call took 2.290 seconds. All 72 worker process times sum to 111.151 seconds, including excluded imports, input loading, copying, and validation. This process sum is accounting for the diagnostic, not embedding-service latency. There was no fresh constructor run and no MM call, so these measurements cannot establish end-to-end speed or an MM runtime ratio.

The host was `dabhmbp`, Darwin 25.6.0 arm64, Python 3.10.19, NetworkX 3.4.2, NumPy 2.2.6, Numba 0.65.1, dwave-networkx 0.8.19, and SciPy 1.15.3. Worker-start one-minute load ranged from 35.79 to 119.16. In addition to this unreserved host, the mandatory reference-gate phase puts all legacy timings before revised-arm timings, so temporal host effects are confounded with that comparison. CPU times closely match wall times but do not remove this limitation. Do not compare these laptop timings directly with 011's hyde03 timings.

## Final audit and interpretation

An independent read-only audit after completion rechecked all 43 frozen source files, all 46 copied input files, 18 case identities, 72 task configurations/results, all 72 output embeddings and recomputed metrics, and all 682 accepted-trajectory arithmetic entries. Every legacy reference matches exactly. No candidate worker has installed MM metadata, a prohibited import attempt, or a loaded MM/busclique module. All worker return codes are zero. Work, pass, group, and region caps hold in every result.

The audit also checked that all 36 copied incumbent/reference files are byte-identical to their corresponding retrieved 011 files. Original source, target, and saved inputs were validated before each call; final outputs were checked again after execution. Intermediate chain contents are not serialized, so the accepted-move diagnostics beyond total-qubit/work arithmetic are recorded evidence, not independently reconstructed intermediate embeddings.

Additional artifact identities:

| Artifact | SHA-256 |
| --- | --- |
| Manifest bytes | `0987b22713e82bf617d05f29ac65d3932b51c173c24a11f981a1c7dad5e2b351` |
| Frozen contact repair bytes | `c7cf4f821c3f378087e9f08a4f967225e2cba880eb8a82dd1554aabb1a8427e6` |
| Frozen contact group schedule bytes | `43574f6f13eb33d790de535e4e614533d0f1df7f50d129932301b7832e1301bd` |
| Frozen runner bytes | `ff32100489fdf95ef38d66f39b893da588ef30064897108516b15791642d6fee` |
| Canonical map of 72 result-file hashes | `857cfe4a74fcc1e01fdbae0d24fd45f4dd6e625ba64981c7b77f8272df770b77` |
| Analysis JSON bytes | `6a03d13eef0826bec1d70e5f08f82ed536dd9a2107c18611643dd45aeae17597` |

`analysis.json` retains complete per-source qubit pairs, mean/sample-variance ACL, timings, work totals, and fixed-arm comparisons. `audit.json` retains individual result hashes and audit counts; `reference_gate.json` binds the successful baseline gate to those exact legacy records. The script passed syntax compilation. No algorithm, pilot, or source-test file was edited by this ablation task.

The combined policy is a defensible fixed candidate for a broader development screen because it has the lowest observed mean ACL at modest additional refinement cost. Group-only is nearly tied and is the necessary control for judging site benefits. The result does not justify choosing between them per graph. Existing graphs informed the revision design, gains are small, only one case distinguishes the combined policy from group-only, and one seed regresses relative to legacy; a broader fixed-policy end-to-end screen is the appropriate next evidence.
