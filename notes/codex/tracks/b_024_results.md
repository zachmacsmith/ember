# B024 result: improved placement proxies, worse complete construction

**Retire the fixed policy.** B024 produced **4/9 valid outputs**, versus B023's 6/9 and MM's 8/9, and only one common MM Q win. It fails both the >=7/9 validity and >=3 Q-win/tie requirements. One authorized saved analysis passed with no audit errors; all 27 outcomes, original-graph validity, exact Q/M/O/F and paired initial footprints/orders were checked. These are exposed development inputs, one seed and one twenty-second run per method.

Each cell is **valid Q / solver seconds**; failures have no credited Q.

| Input | B024 | B023 control | Fresh MM |
|---|---:|---:|---:|
| Complete40 | 183 / 2.86 | 183 / 2.57 | 194 / 8.87 |
| Complete100 | failure / 19.09 | failure / 19.09 | timeout / 26.87 |
| Bipartite30×30 | 233 / 10.70 | 195 / 7.33 | 180 / 5.41 |
| ER80/d8 | failure / 11.05 | failure / 18.80 | 211 / 8.33 |
| Regular80/d3 | 223 / 4.74 | 277 / 7.98 | 90 / 0.69 |
| Watts–Strogatz80 | failure / 4.22 | 306 / 10.97 | 94 / 0.83 |
| Grid8×8 | failure / 4.73 | 195 / 4.38 | 70 / 1.02 |
| Honeycomb5×5 | 147 / 4.52 | 145 / 5.44 | 71 / 0.36 |
| King8×8 | failure / 5.58 | failure / 10.26 | 90 / 1.19 |

All nine preparations completed. All **seven noncliques reduced both exact distance cost C and initial missing contacts M**, using 464 accepted swaps on unchanged site sets. Yet WS/grid lost their prior successes, bipartite worsened by38Q, and honeycomb by2Q. Regular saved54Q versus B023 but still used 2.48× MM Q. Honeycomb remained 2.07× MM Q. Complete-source permutations correctly made no changes; Complete40's sole MM win was inherited unchanged. These results reject this placement policy as a general improvement; they do not show that coordinated placement is irrelevant.

Preparation completion rules out interrupted setup as the explanation for the seven nonclique outcomes. ER/WS/grid/king completed eight passes with **7/9/3/5 missing contacts**, respectively, versus B023's 2/0/0/1; all final overlaps were zero. Their actions were uninterrupted. Complete100 instead hit the search deadline: preparation spent **7.39s and 6.27M units without changing its assignment**, leaving less construction time. Its 3,351 remaining contacts are a failed-state diagnostic, not quality evidence.

Across B024, all **2,754 completed route/erasure actions committed**, including545 energy increases. Only one action was interrupted, on Complete100; its single discarded scored proposal was not defect-free. Contact restoration and overlap clearance were exercised, and cleanup removed162 sites from the four valid outputs. Thus a strict energy rejection barrier or widespread unpublished useful proposals does not explain the result. Restricted routing/owner moves and forced repair decisions remain coupled to placement; this screen cannot separate them or prove infeasibility.

All-attempt **solver/CPU/process** totals were B024 **67.501/67.471/78.893s**, B023 **86.814/86.781/99.108s**, MM **53.575/53.543/65.010s**, including failures and the late MM result. B024 preparation consumed10.911s and9.344M units, already included in its totals. Its lower total time comes with fewer successes; it is not a speed improvement claim. Same-host start load was33.02–34.27 with32 affinity CPUs, and historical timings are not pooled. No source, pass, price or cap adjustment follows this result.

[Full paired CSV](../../../results/codex/track-b024-analysis/analysis001/table.csv), [audited rows](../../../results/codex/track-b024-analysis/analysis001/rows.json), [mechanism receipts](../../../results/codex/track-b024-analysis/mechanism001/summary.json), and [saved-analysis status](../../../results/codex/track-b024-analysis/analysis001-status.json) retain every input and failure. No candidate was rerun.
