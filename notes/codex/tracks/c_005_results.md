# C005: free-site exchanges do not improve construction coverage

C005 fails its [predeclared test](c_005_vacancy_quotient.md). It retains four valid embeddings, but produces no new success and no 50% reduction of missing contacts on a harder input. Every timely pair still loses to fresh stock MM. The constant-size exchange policy is rejected for further promotion in its current form.

The same eight development graphs, ideal Z12, seed 0 and 15-second allowance were used in separate paired processes on hyde04. C005 starts with C004’s compact allocation and alternates region-label swaps, owned-site transfers and joint free-site addition/safe release. Initial missing-edge counts match C004 exactly. Total Q remains fixed during search; full-target BFS replaces fixed-domain distance queries.

| Family / graph | C005 Q / ACL | MM Q / ACL | Solver seconds C / MM | Final missing C004 → C005 | Final sites outside initial domain |
|---|---:|---:|---:|---:|---:|
| path / ember_2030 | 289 / 2.050 | 141 / 1.000 | 0.270 / 0.146 | 0 → 0 | 8 |
| tree / ember_5058 | 197 / 1.628 | 121 / 1.000 | 0.226 / 0.138 | 0 → 0 | 6 |
| grid / ember_1584 | 373 / 2.914 | 134 / 1.047 | 0.998 / 0.370 | 0 → 0 | 20 |
| random_planar / ember_31536 | 470 / 3.092 | 281 / 1.849 | 2.632 / 0.567 | 0 → 0 | 35 |
| random_er / ember_6450 | timeout | 1044 / 7.850 | 14.500 / 8.468 | 210 → 195 | 78 |
| regular / ember_14334 | timeout | 2481 / 17.721 (late) | 14.501 / 15.334 | 1012 → 1128 | 183 |
| complete / ember_1041 | timeout | 2170 / 17.087 (late) | 14.501 / 17.419 | 3514 → 3959 | 146 |
| sbm / ember_30736 | timeout | 638 / 5.317 | 14.500 / 4.087 | 106 → 79 | 89 |

The four timely solver ratios are 1.86 / 1.64 / 2.70 / 4.64; process ratios are 1.32 / 1.22 / 1.84 / 3.58. MM regular/complete outputs are valid but late and their quality is diagnostic only. Candidate failures stop near 14.5 seconds under the existing final-validation reserve. They have no credited embedding quality.

The four failed states independently retain their exact budgets of 540 / 1,680 / 3,556 / 484 sites, with 78 / 183 / 146 / 89 sites outside the initial domain. The occupied domain therefore extends beyond its initial boundary. However, ER/SBM missing contacts improve only modestly, while regular/complete worsen. Their best counts are 194 / 1,128 / 3,959 / 77; final counts can be worse under annealing. Proposal BFS still examines about 85–90 million adjacency entries per failed call. This exposes a cost problem even with truncated queries. The schedule and query implementation also changed, so this is a fixed-policy screen rather than an isolated causal estimate for one operator.

Sparse Q changes from C004 are 287→289, 213→197, 338→373 and 473→470: two improvements, two regressions. Retain compact allocation as the useful prior finding; reconsider how construction supplies distinct logical neighbors and how search spends its time. Simply extending time, adding seeds or another domain size does not address these observations. The result does not prove any input infeasible on full Z12. Novelty remains unresolved within the established movable-region literature.

Six focused test groups pass after documented pre-screen corrections to a test coverage count and a BFS stopping condition. Independent checks cover all eight legal tiny exchanges, 80 successive moves, connectivity/Q/contact arithmetic and original-target deadline gates. After quiescence, the frozen saved-data auditor passed all 161 archived hashes, original-label validation, exact partial missing counts and actual domain crossing, without constructor/MM calls. [Results](../../../results/codex/track-c-005/review/results.json), [CSV](../../../results/codex/track-c-005/review/pairs.csv) and [manifest](../../../results/codex/track-c-005/review_manifest.json) preserve all failures, work and provenance. This one-seed development screen supports no family-mean, variance or held-out claim.
