# C004: compact allocation retains sparse construction

C004 retains all four C003 successes and reduces their Q by 64–76%, satisfying its predeclared allocation test. Every timely pair still loses to fresh stock MM. The same four harder inputs time out. Compact initial allocation is therefore useful, but this constructor remains uncompetitive in both coverage and ACL.

The [fixed policy](c_004_compact_quotient.md) selects one connected BFS subset of size `min(|H|,4L)`, with L the summed source-degree lower bound, then runs unchanged C003 region reconfiguration. There is no size ladder or independent restart. The unchanged eight development inputs use ideal Z12, seed 0 and 15 seconds per arm in separate paired processes on prepared hyde04.

| Family / graph | Target budget | C004 Q / ACL | MM Q / ACL | Solver seconds C / MM | Final missing edges C |
|---|---:|---:|---:|---:|---:|
| path / ember_2030 | 564 | 287 / 2.035 | 141 / 1.000 | 0.224 / 0.145 | 0 |
| tree / ember_5058 | 484 | 213 / 1.760 | 121 / 1.000 | 0.343 / 0.135 | 0 |
| grid / ember_1584 | 512 | 338 / 2.641 | 134 / 1.047 | 1.214 / 0.342 | 0 |
| random_planar / ember_31536 | 608 | 473 / 3.112 | 281 / 1.849 | 1.440 / 0.563 | 0 |
| random_er / ember_6450 | 540 | timeout | 1044 / 7.850 | 14.501 / 8.314 | 210 |
| regular / ember_14334 | 1680 | timeout | 2481 / 17.721 (late) | 14.501 / 15.346 | 1012 |
| complete / ember_1041 | 3556 | timeout | 2170 / 17.087 (late) | 14.502 / 17.280 | 3514 |
| sbm / ember_30736 | 484 | timeout | 638 / 5.317 | 14.500 / 4.124 | 106 |

The four timely pairs have solver ratios 1.55 / 2.54 / 3.56 / 2.56 and process ratios 1.21 / 1.43 / 2.39 / 2.11. MM’s path/tree outputs attain ACL 1. Its regular/complete outputs are valid but late; their quality is diagnostic only. Candidate failures stop near 14.5 seconds because the common deadline reserves 0.5 seconds for final validation. No failed ownership partition receives embedding quality.

C003’s corresponding Q values were 927 / 598 / 1,411 / 1,633; C004 yields 287 / 213 / 338 / 473 after completed deletion passes. Its fixed budgets already cap Q below those prior outputs, so preserving construction is the substantive result. Earlier timings are not pooled. Restricting the outer domain also increases initial missing contacts. ER/SBM perform 25,449 / 28,203 completed visits yet finish with 210 / 106 missing edges; their best counts were 207 / 102. More visits alone do not resolve the remaining contacts. Dense-source failures cannot distinguish a local search trap from insufficient subset topology or capacity; they do not prove infeasibility on full Z12.

Next retain compact allocation, but investigate a principled way to change the outer domain or relocate whole connected regions within one evolving state. Do not choose larger independent restarts or merely increase temperature/time. Sparse ACL remains too high even when construction succeeds. Movable-region annealing is established prior art, and this allocation experiment does not settle novelty. One repeatedly used instance per selected family and one seed establish no family-mean, solver-variance or held-out generalization claim.

Six focused tests and the affected isolated pilot test passed. After verified controller completion/free lock, the saved-data audit passed all 159 archive hashes, original-label physical validity and quality/status checks, exact connected subset budgets, and all four partial missing-edge recounts. It ran once without constructor/MM calls. [Full results](../../../results/codex/track-c-004/review/results.json), [CSV](../../../results/codex/track-c-004/review/pairs.csv) and [manifest](../../../results/codex/track-c-004/review_manifest.json) retain timing, work, failures and provenance.
