# Experiment 019: independent review of the Ember readiness screen

Both fixed candidate configurations returned timely valid embeddings on all
34 selected structures. MM returned 31 timely valid embeddings; its other
three calls exceeded the frozen 60-second allowance. Among the 31 common
timely successes, each candidate achieved lower ACL on 8 inputs and higher
ACL on 23, with no ties. The revised contact policy improves the reference
modestly, but neither candidate meets the project objective across these
development inputs. Several sparse inputs also exceed the desired 10× MM
runtime range.

This is one source graph per represented family and one solver seed (0).
These are observations of selected inputs, not estimates of family means or
evidence of generalization. No across-seed ACL variance can be estimated.
The population variance of chain lengths *inside one embedding*, retained in
the result files, is a different quantity. No local 018 smoke results or later
candidate runs are pooled here. No best-of output is formed between the two
candidate arms.

## Completion and preserved evidence

The existing controller on hyde03 completed all 102 tasks. Fresh SSH status
confirmed `controller.status=complete`, `lock_busy=false`,
`tmux_running=false`, and supervisor exit 0 before retrieval. Controller PID
was 115997. All 102 worker processes returned exit code 0; no interrupted,
unfinalized, dependency-violation, or harness-error record remains. The
recorded first-to-last worker span is 1346.869697 seconds. All consecutive
recorded worker intervals are disjoint, with a minimum gap of 0.001633 seconds.
The stale final worker entry in `active.json` is not a running process.

The completed archive is
`results/codex/retrieved/hyde03/019-ember-readiness-screen/`.
Retrieval verified 598 files. Independent review rechecked that inventory,
the transport inventory, all 43 frozen source files, all 102 task identities,
all 102 claims and worker/final result pairs, the target, the 34 source
records, and both corpus sidecars. Every worker field is preserved unchanged
in its finalized result. There are exactly 102 files in each of `tasks/`,
`claims/`, `worker_results/`, and `results/`, with matching task ID sets.

| Identity | SHA-256 |
| --- | --- |
| Source snapshot | `466bf012bb71aeb6ca9981fbef1935a00e6e27580328481741fc0e2f7fa00024` |
| Target | `38cde794d3c1461054a45b5a660d157737b019c19cb9a7b38e2027730e3d5938` |
| Transport inputs | `e94992ad66322fee4db82d02191468305345ffde37b782513811bfe21fe07b9d` |
| Retrieved archive inventory | `d0e97f16e31dca16cea634abd320a75512191568618d8b7af0164f39a0b09ca4` |
| Readiness sidecar file | `7474bf4d873295f0c485134b7445753c5035af5b64876668d91673315b615c46` |
| Original selection sidecar file | `2b5d85755a519596230d25a0972b67028da5224e419ac8ce757288ca4a2ee47c` |

The frozen source commit is `d270f2bb1fe6a6808bc18a89a9a3ff4af36a9dac`.
Readiness selection ID is
`06c02356f8df5503b57f280ba4939c298cc05834c563a3da8a71f96fe245db98`.
The target is the frozen ideal Z12, with 4800 vertices and 45864 edges.
Graph/source metadata and attributes are empty in the candidate source inputs;
family names and graph IDs are retained in the external provenance ledger.

The ordinary analyzer passed. A second verifier uses Python's standard
library, importing neither the candidate nor the runner's validation routine.
For every output it checks exact source keys including isolates, nonempty
integer chains, original-target membership, chain disjointness and
connectivity, and source-edge coverage in the quotient of the **original
target edges**. It recomputes qubit count, ACL, maximum chain length, and
within-embedding chain-length variance. All 99 credited embeddings pass;
the two late valid MM witnesses also pass and retain diagnostic quality only.

The scripts and outputs are saved in the retrieved archive's `analysis/`:
`independent_review.py`, `independent_review.json`, `family_report.py`,
`family_results.csv`, and `family_table.md`. The ordinary analyzer also saved
`summary.json`, `per_input.csv`, `paired_trials.csv`, and `report.md`.
The original manifest, source, tasks, claims, embeddings, logs, and sidecars
are preserved. Analysis files were added after retrieval and are not members
of its frozen 598-file inventory.

## Fixed arms and dependency checks

“Reference” means `native-search-joint1`; “revision” means
`native-search-joint1-sites-groups`. Both are the independent native pipeline,
not the earlier embedding entry point with an external fallback. Both use
search construction, seed 0, width one, 1000 proposal evaluations, four
refinement passes, at most 512 groups of sizes 1–4, and the frozen default
500000 work-unit allowance. The revision additionally requests 16 boundary
sites and round-robin group coverage. These settings are identical across
all inputs for each arm. The metadata-free graph structure is the solver's
input; family membership is not a dispatch input.

All 68 candidate records identify the frozen run's
`source/packages/ember-qc/src/ember_qc/algorithms/factored/native.py` entry
point and the separate interpreter
`/home/dabh/ember-codex/envs/4e1fb892db12754e/native/bin/python`.
Each worker passed the pre-import absence check for `minorminer`,
`_minorminer`, and `busclique`, recorded no prohibited import attempts or
loaded embedding libraries, and recorded no installed minorminer package.
All 34 comparator records used the separate `mm/bin/python` environment and
MM 0.2.22. The frozen comparator calls `minorminer.find_embedding` with
`random_seed=0`, `timeout=60`, and otherwise default settings; it receives no
candidate embedding. No candidate is supplied an MM witness.

Every record reports Python 3.10.12 and common packages NetworkX 3.4.2,
NumPy 2.2.6, Numba 0.65.1, SciPy 1.15.3, and dwave-networkx 0.8.19. There is
no missing worker provenance. This verifies the recorded execution path and
dependency guards; it is not a substitute for reviewing future source changes.

## Quality and failures

All aggregate counts below count each of the 34 distinct normalized inputs
once. A macro-average here is an equally weighted mean across those input
structures, not a graph-family population estimate.

| Fixed arm | Timely successes / attempted | Lower / higher / equal ACL versus MM on 31 common successes | Mean ACL on those same 31 inputs | Mean ACL on all 34 candidate successes |
| --- | ---: | ---: | ---: | ---: |
| MM | 31 / 34 | — | 2.961536 | undefined: 3 lack a timely result |
| Reference | 34 / 34 | 8 / 23 / 0 | 2.907427 | 3.537137 |
| Revision | 34 / 34 | 8 / 23 / 0 | 2.859913 | 3.493185 |

The revision's mean ACL on the common-success subset is 3.43% below MM's,
but that descriptive average hides its 23 individual losses. It excludes
three inputs based on MM's outcome and cannot stand in for an all-input or
all-family superiority claim. Comparing either candidate's 34-input mean
directly with MM's 31-input mean would compare different populations.

Both candidates beat MM on the selected bipartite, Johnson, random ER, SBM,
star, Turán, Watts–Strogatz, and weak–strong cluster inputs. Their largest
absolute gains occur on a few of these inputs. On the selected cycle, path,
binary tree, tree, and named-special graph, MM reaches the ACL lower bound 1
and both candidates remain above it. A future correct solver can at best tie
MM's ACL on these particular outcomes. These observations do not justify
introducing family-specific solver dispatch.

Relative to the reference, the revision lowers ACL on 22 structures, raises
it on 5, and ties on 7. It uses 15771 rather than 15973 total qubits, a net
saving of 202. The regressions are cycle (+1 qubit), path (+1), BCC (+1),
Shastry–Sutherland (+1), and planted solution (+2). This does not authorize
choosing the better arm separately for each input.

| MM timeout input | Solver / process seconds | Returned embedding | Diagnostic ACL | Task ID |
| --- | ---: | --- | ---: | --- |
| complete, 1041 | 64.049142 / 65.335095 | valid, late | 15.645669 | `de9cbf5b86edff6faeb2f21f` |
| regular, 14334 | 61.109701 / 62.107016 | valid, late | 15.100000 | `ee4204f564896169a07680f0` |
| spin_glass, 37302 | 67.352261 / 68.271741 | no valid source-covering output | — | `7db44ffff4abdbfca4b3062d` |

The hard worker lifetime includes a 30-second watchdog margin; success credit
still requires the externally measured solver wall to be at most 60 seconds.
MM's three ordinary returns overrun by 4.049142, 1.109701, and 7.352261 seconds,
respectively. There was no watchdog kill. Late witnesses remain available for
diagnosis but are excluded from credited ACL. Their existence does not reveal
whether MM held a usable incumbent internally before the deadline. The two
valid late MM outputs have worse ACL than either timely candidate, but they
are not added to the 31 paired timely comparisons.

## Runtime interpretation

Methods were run sequentially on the same host with deterministic shuffled
method order per input and one numerical-library thread. Each trial uses a
fresh worker and its own initially empty JIT cache. Solver wall includes the
graph copies, construction, pruning/refinement, and first-call compilation.
Implementation imports, input loading, independent post-call validation, and
process startup are outside solver wall and included in process wall. Both
measurements are retained. Start-of-trial one-minute system load ranged from
10.56 to 16.95; these are shared-host measurements, not isolated-host speed
constants. No timing comparison to another machine or later run is made.

| Fixed arm | Median solver / process seconds, all 34 attempts | Mean solver / process seconds, all 34 attempts |
| --- | ---: | ---: |
| MM | 1.486 / 2.328 | 11.511 / 12.274 |
| Reference | 9.378 / 11.796 | 11.058 / 13.785 |
| Revision | 9.582 / 12.596 | 10.717 / 13.543 |

| Candidate/MM measured ratio | Median, all 34 attempts | Maximum | Inputs over 10× | Median, 31 common timely successes |
| --- | ---: | ---: | ---: | ---: |
| Reference solver wall | 8.893 | 26.104 | 16 / 34 | 10.223 |
| Reference process wall | 6.815 | 12.191 | 4 / 34 | 7.448 |
| Revision solver wall | 8.648 | 34.512 | 15 / 34 | 9.886 |
| Revision process wall | 6.152 | 15.836 | 7 / 34 | 7.082 |

Ratios in the all-attempt columns compare actual measured cost, including MM
calls that failed the deadline. They are not ratios of time to successful
embedding for those three failures. The per-input family table marks them.
MM's expensive dense-input attempts dominate its pooled mean runtime; a
similar pooled mean does not mean the candidate stays within 10× MM on each
input. On binary_tree the revision takes 14.526 versus 0.421 solver seconds,
or 34.51×, and 18.560 versus 1.172 process seconds, or 15.84×. Repeated seeds
and dedicated timing runs are needed before attributing small time
differences between the candidate policies to an algorithmic speed change.

## Family-mapped observations

Each row is one observation at solver seed 0. IDs retain their original family
membership. The two rows marked `*` share the exact same normalized input,
embedding trials, and task IDs; all aggregates above count it once. Their
normalized topology hash is
`ad061ab01ea949cfe9e993013fde26052d059f31be29c63a2ef3a93d3a06c1c4`
and source-record hash is
`629d308e0f90fbbb26519f608092432e76d4b1197b8896cd737d72aaa1109449`.
The 34 distinct hashes establish absence of exact normalized duplicates,
not pairwise non-isomorphism. CSV consumers must group by `graph_key` before
aggregating; repeated family membership rows are not independent trials.

Sudoku remains explicitly missing: its two inherited manifest entries have
no input passing the fixed necessary Z12 count bounds, so readiness 017
contains no eligible READY Sudoku graph. It was not attempted or silently
replaced. The original incomplete corpus selection and its failed-input ledger
remain in the shipped sidecar. Thirty-five family labels are represented here;
there is no evidence for all 36 families.

`†` denotes measured cost relative to an MM timeout, not a speed ratio between
two successful calls. ACL entries labeled TIMEOUT receive no quality credit.

| Family | Selected ID → input ID | n / m | MM ACL | Reference ACL | Revision ACL | Revision/MM solver / process time |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| barabasi_albert | 10662 | 122 / 472 | 3.3607 | 3.8279 | 3.6721 | 1.14 / 1.32 |
| bcc_lattice | 33402 | 91 / 216 | 1.2637 | 1.7033 | 1.7143 | 15.43 / 9.00 |
| binary_tree | 4905 | 127 / 126 | 1.0000 | 1.1811 | 1.1654 | 34.51 / 15.84 |
| bipartite | 1363 | 126 / 3969 | 6.1587 | 4.4921 | 4.4921 | 0.21 / 0.28 |
| circulant | 3499 | 134 / 402 | 1.4627 | 1.8507 | 1.8433 | 20.91 / 12.03 |
| complete | 1041 | 127 / 8001 | TIMEOUT | 9.2913 | 9.2913 | 0.30 / 0.36 † |
| cubic_lattice | 33219 | 125 / 300 | 1.4960 | 1.9760 | 1.9600 | 10.11 / 7.41 |
| cycle | 1829 | 126 / 126 | 1.0000 | 1.1508 | 1.1587 | 22.08 / 10.38 |
| frustrated_square * | 32816 → 32616 | 121 / 420 | 1.4132 | 2.3471 | 2.3306 | 13.40 / 9.02 |
| generalized_petersen | 4083 | 126 / 189 | 1.3095 | 1.9762 | 1.8333 | 13.96 / 7.73 |
| grid | 1584 | 128 / 232 | 1.0469 | 1.7031 | 1.6953 | 14.41 / 8.66 |
| hardware_native | 37603 | 128 / 352 | 1.4609 | 2.2422 | 2.1875 | 8.63 / 6.86 |
| honeycomb | 32367 | 190 / 264 | 1.0316 | 1.7789 | 1.7053 | 19.61 / 11.43 |
| hypercube | 4755 | 128 / 448 | 3.2969 | 3.5859 | 3.5547 | 4.20 / 3.98 |
| johnson | 5242 | 120 / 1680 | 9.8750 | 7.4500 | 7.3833 | 0.85 / 1.05 |
| kagome | 32122 | 131 / 236 | 1.2214 | 1.9084 | 1.8244 | 9.89 / 5.45 |
| king_graph * | 32616 | 121 / 420 | 1.4132 | 2.3471 | 2.3306 | 13.40 / 9.02 |
| kneser | 5411 | 126 / 315 | 2.8968 | 3.6190 | 3.4048 | 7.51 / 7.29 |
| lfr_benchmark | 31357 | 100 / 204 | 1.6000 | 1.9800 | 1.9700 | 10.62 / 7.10 |
| named_special | 37761 | 46 / 69 | 1.0000 | 1.1522 | 1.1522 | 10.13 / 5.30 |
| path | 2030 | 141 / 140 | 1.0000 | 1.2411 | 1.2482 | 29.84 / 13.79 |
| planted_solution | 34404 | 133 / 175 | 1.0226 | 1.3534 | 1.3684 | 21.90 / 10.72 |
| random_er | 6450 | 133 / 870 | 7.8496 | 6.6992 | 6.5564 | 0.85 / 0.98 |
| random_planar | 31536 | 152 / 450 | 1.8487 | 2.4342 | 2.3421 | 7.00 / 4.99 |
| regular | 14334 | 140 / 2800 | TIMEOUT | 9.3786 | 9.3571 | 0.19 / 0.23 † |
| sbm | 30736 | 120 / 625 | 5.3167 | 5.1917 | 5.0083 | 1.70 / 1.98 |
| shastry_sutherland | 33018 | 121 / 270 | 1.2149 | 1.6612 | 1.6694 | 13.00 / 8.78 |
| spin_glass | 37302 | 160 / 12720 | TIMEOUT | 11.4625 | 11.4625 | 0.35 / 0.39 † |
| star | 2229 | 127 / 126 | 1.1339 | 1.0709 | 1.0709 | 0.61 / 0.80 |
| sudoku | no eligible READY input | — | not attempted | not attempted | not attempted | — |
| tree | 5058 | 121 / 120 | 1.0000 | 1.2149 | 1.1983 | 23.05 / 11.28 |
| triangular_lattice | 31879 | 128 / 384 | 2.0859 | 2.7266 | 2.7031 | 8.66 / 7.08 |
| turan | 3060 | 90 / 2700 | 8.8111 | 5.0778 | 5.0778 | 0.18 / 0.24 |
| watts_strogatz | 22972 | 174 / 1740 | 13.7931 | 10.1437 | 10.0000 | 0.45 / 0.50 |
| weak_strong_cluster | 33587 | 128 / 1988 | 3.6797 | 3.3828 | 3.3828 | 2.02 / 2.15 |
| wheel | 2429 | 127 / 252 | 1.1575 | 2.0079 | 1.9843 | 2.10 / 2.40 |

## Lessons and limits for the next development step

The same per-input construction qubit counts, pruned qubit counts, layout
orders, and recorded ranks occur in both candidate arms. Across 34 inputs,
construction uses 19255 qubits and pruning reduces that to 16370. Contact
refinement then saves 397 qubits for the reference and 599 for the revision.
These diagnostics support attributing the observed final-quality differences
to the changed refinement policy, without implying that all intermediate
embeddings were separately saved and compared.

Reference refinement reports work-limit stops on 24 inputs, group-limit stops
on 8, and no-improvement stops on 2; the revision reports 22, 11, and 1,
respectively. Neither arm stops refinement on its wall deadline. These
diagnostics identify bounded search coverage as a possible limitation; they
do not show that merely increasing work will close the gap. In particular,
reliable construction is already present at these sizes, while low-ACL
embeddings for many sparse inputs remain the main missing behavior.

Retain these losses as development evidence. Test any general revision as one
fixed configuration across the same readiness inputs before scaling the full
corpus; use paired fresh MM runs when making new timing claims. Prior tuning
on these and other inherited graphs means they cannot become a clean holdout.
Future family-level claims require the protected generation/source protocol,
more source instances and sizes, repeated solver seeds, explicit missingness,
and success guardrails described in `../generalization_protocol.md`.

Reproduction after verified retrieval:

```sh
.venv/bin/python scripts/codex/analyze_pilot.py results/codex/retrieved/hyde03/019-ember-readiness-screen
.venv/bin/python results/codex/retrieved/hyde03/019-ember-readiness-screen/analysis/independent_review.py results/codex/retrieved/hyde03/019-ember-readiness-screen
.venv/bin/python results/codex/retrieved/hyde03/019-ember-readiness-screen/analysis/family_report.py results/codex/retrieved/hyde03/019-ember-readiness-screen
```
