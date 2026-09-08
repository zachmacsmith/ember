# C006: distinct-neighbor preservation improves the initial quotient

C006 passes its [initial-capacity hypothesis](c_006_distinct_quotient.md), but fails its separate promotion test. All eight initial quotients contain more distinct edges, and all four harder inputs start with more represented source edges. Construction remains 4/8 successful; every timely quality pair still loses to fresh stock MM.

The experiment uses unchanged C004 allocation, assignment, search and cleanup. Equal-size contraction partners are ranked by current distinct adjacency loss, `1 + |N(u)∩N(v)|`, with immediate quotient updates. C005 exchanges are excluded. The same eight development inputs, ideal Z12, seed 0 and 15-second allowance were paired with fresh MM processes on hyde04.

| Family / graph | Initial quotient edges C004 → C006 | Final missing C004 → C006 | C006 Q / ACL | MM Q / ACL | Solver seconds C / MM |
|---|---:|---:|---:|---:|---:|
| path / ember_2030 | 1845 → 3328 | 0 → 0 | 313 / 2.220 | 141 / 1.000 | 0.226 / 0.146 |
| tree / ember_5058 | 1480 → 2639 | 0 → 0 | 207 / 1.711 | 121 / 1.000 | 0.177 / 0.135 |
| grid / ember_1584 | 1574 → 2854 | 0 → 0 | 367 / 2.867 | 134 / 1.047 | 0.369 / 0.369 |
| random_planar / ember_31536 | 2025 → 3484 | 0 → 0 | 457 / 3.007 | 281 / 1.849 | 0.580 / 0.560 |
| random_er / ember_6450 | 1733 → 3056 | 210 → 190 | timeout | 1044 / 7.850 | 14.501 / 8.365 |
| regular / ember_14334 | 2305 → 5925 | 1012 → 337 | timeout | 2481 / 17.721 (late) | 14.501 / 15.373 |
| complete / ember_1041 | 2447 → 6833 | 3514 → 146 | timeout | 2170 / 17.087 (late) | 14.502 / 17.339 |
| sbm / ember_30736 | 1470 → 2623 | 106 → 90 | timeout | 638 / 5.317 | 14.500 / 4.068 |

Initial missing source edges decrease from 443→298 on ER, 1,749→823 on regular, 5,554→1,168 on complete and 287→191 on SBM. The complete graph ends with 146 of 8,001 edges missing, versus C004’s 3,514; regular ends with 337 of 2,800, versus 1,012. These are still failed embeddings. Their exact connected, disjoint partial regions retain the unchanged budgets; the lower missing counts do not establish feasibility or eventual success.

The four timely candidate/MM solver ratios are 1.54 / 1.31 / approximately 1.00 / 1.04; process ratios are 1.22 / 1.11 / 0.93 / approximately 1.00. Single-run near-equalities support no speed-superiority claim. MM regular/complete outputs are valid but late, with diagnostic-only quality. Candidate timeouts occur near 14.5 seconds under the existing validation reserve.

The new coarsening costs 0.020–0.564 seconds, including 82,914–2,990,182 neighbor-membership tests. Dense failures still spend most time in search. Sparse Q is mixed against C004: 287→313, 213→207, 338→367 and 473→457. Thus extra quotient contacts help initial representability but do not automatically produce compact valid minors. Retain distinct-neighbor preservation as a useful mechanism; further work must resolve remaining source-specific contacts and chain length without treating larger quotient capacity as the final objective.

Five focused groups passed, including 192 independently checked contractions, equal-raw/different-distinct-loss and stale-batch witnesses. One approved C004 initialization-only replay matched every historical initial-missing count; its 3.105 seconds are diagnostic time, with no constructor/search/MM calls. The post-quiescence audit passed all 163 archive hashes, original-label validity, both initial maps, exact distinct/physical-coupler conservation and partial missing counts. [Results](../../../results/codex/track-c-006/review/results.json), [CSV](../../../results/codex/track-c-006/review/pairs.csv) and [manifest](../../../results/codex/track-c-006/review_manifest.json) retain costs, reference provenance and failures. The contraction identity and movable-region framework are established ideas; novelty, family means, variance and held-out generalization remain unproved.
