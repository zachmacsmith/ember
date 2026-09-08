# 045: vacancy repair adds first-contraction reach

2026-09-08. **Vacancy repair returns a valid contraction on eight additional inputs in this fixed development screen.** It returns 25 credited contractions versus ordinary’s 17, retaining all 17 shared successes. This is useful first-return evidence for the proposed mechanism; it is not a cumulative pipeline result or an advantage over MM.

The frozen minimal screen passes on all 68 rows. All 42 credited outputs validate against original source labels and the original target, and every completed pair has the same generated group vector/hash. Vacancy ignores that vector and uses its own flat deletion-seed order: these are different search neighborhoods and schedules. All 34 inputs and 35 memberships remain represented.

| Paired credited outcome | Inputs |
|---|---:|
| Both | 17 |
| Vacancy only | 8 |
| Ordinary only | 0 |
| Neither | 9 |

| Fresh 045 measurement | Ordinary | Vacancy |
|---|---:|---:|
| Credited contractions | 17 | 25 |
| No contraction | 12 | 6 |
| No eligible groups | 2 | Not used |
| Global work limit | 3 | 3 |
| Common wall, total | 25.036 s | 6.822 s |
| Common wall, median | 0.498 s | 0.166 s |
| Common wall, maximum | 3.155 s | 0.654 s |
| Process wall, total | 32.118 s | 13.664 s |

Neither arm has an invalid output, deadline or process failure. Ordinary uses 4,093,011 routing expansions and inspects 8,715 groups. Vacancy examines 346,555 relocation proposals across 4,233 deletion seeds; 1,341 seeds reach the 256-proposal ceiling. Its counter is attempted relocation proposals, not routing or 043/044 elementary work units. All totals are known and exclusive phase walls reconcile. A seed-exhausted result remains a bounded heuristic negative.

Vacancy’s common wall includes 1.483 s inside its method, 1.753 s in independent final gates and 2.018 s generating the control’s group vector, plus the shared graph preparation, snapshots and mutation checks. These are fresh paired measurements on hyde03. Repeated calls and cumulative gains have not been measured.

Each vacancy success saves one qubit. Ordinary saves one on 16 successes and two on one. Independent proposals are not summed as a realized multi-move improvement. The eight vacancy-only observations below merit short trace checks. Seven ordinary comparisons finish their supplied group sequence without a returned contraction; the regular-graph comparison hits its global routing cap. Neither establishes exact local infeasibility.

| Input | Development membership | Entry Q → returned Q | Relocations | Selected owners | Ordinary status |
|---|---|---:|---:|---:|---|
| ember_14334 | regular | 1303 → 1302 | 1 | 2 | WORK_LIMIT |
| ember_30736 | sbm | 613 → 612 | 1 | 2 | NO_CONTRACTION |
| ember_31879 | triangular_lattice | 286 → 285 | 1 | 2 | NO_CONTRACTION |
| ember_4905 | binary_tree | 138 → 137 | 2 | 2 | NO_CONTRACTION |
| ember_33018 | shastry_sutherland | 162 → 161 | 2 | 3 | NO_CONTRACTION |
| ember_1584 | grid | 173 → 172 | 2 | 3 | NO_CONTRACTION |
| ember_33587 | weak_strong_cluster | 427 → 426 | 2 | 1 | NO_CONTRACTION |
| ember_33219 | cubic_lattice | 222 → 221 | 2 | 3 | NO_CONTRACTION |

The exact one/two-move traces, deleted site, seed owner and immutable source/entry paths are extracted with result hashes in [vacancy_only_traces.json](../../../results/codex/045-results-review/vacancy_only_traces.json). This reviewer has **not replayed those traces**; root owns the targeted independent replay before a cumulative implementation. Final original-graph validity and strict Q reduction are already established by this screen. The source was previously checked with fixed synthetic incremental-contact and cap fixtures.

[All rows](../../../results/codex/045-results-review/screen001/rows.json), [paired records](../../../results/codex/045-results-review/screen001/pairs.json), and [summary](../../../results/codex/045-results-review/screen001/summary.json) preserve all statuses and counts. Prior 043/044 exchange screens found only three contractions and none absent from ordinary; that historical reach comparison is descriptive, not a pooled timing experiment.

Archive digest: `5f073d9a2d04c33352967918d55d06660368c21872eb63b6b4b6e11f43359c4c` (496 verified files). Frozen screen: `ae333f553709fdcf87851a2625725a30f1e29cb33a44b25b05958c2060ffaf07`. Manifest: `114c7746daaccf9592e8eb2df2949bf7fcb188ee62b4a6acdcd10391dcaa044b`. One saved-result screen executed and passed; no candidate or corpus rerun occurred during analysis.

No novelty, graph-family generalization, final ACL or end-to-end runtime claim follows from eight additional first contractions. The next useful test is a separately fixed cumulative integration after the short successful traces pass, retaining all failures and a shared deadline.

**Root follow-up, 17:39 UTC.** All eight additional traces (13 relocations)
passed independent replay against original source and target edges. The replay
checks connectivity, disjointness, contact changes, Q-minus-one size, exact
returned mappings, and the eight-owner/64-original-site limits after each move.
Evidence: `results/codex/045-results-review/root_new_trace_replay.json`;
replay code: `results/codex/045-preparation/replay_new_traces.py`. An initial
record-key typo stopped the script before any replay and was corrected. This
supports the separately specified 046 cumulative pipeline experiment; it does
not establish that its gains will accumulate.
