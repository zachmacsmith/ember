# A065 complete-constructor result

2026-09-10. Exploratory evidence: **A065 preserves 9/9 successes and improves Q over A064 on three different structures, including both new inputs; six ties, no Q regressions.** This meets the frozen small-screen continuation criterion. It does not meet the final MM objective: one MM win and seven losses on eight common successes, plus MM's K100 timeout. Eight primary structures and one nested grid relabeling are not nine independent structures. A061 remains the retained algorithm pending broader evidence.

The original-graph audit and passive mechanism reader passed first attempts; root read both adapters and verified 34 mechanism bindings. All 36 calls are accounted for, 35 SUCCESS and one MM TIMEOUT, with no unknown wall/CPU fields in the audit's defined scope. No candidate depends on MM/busclique, no witness entered a constructor, and outputs were never combined. The common audit alone supplies final embedding credit.

| Input | A065 Q / ACL | A064 Q | A061 Q | MM Q / ACL | A065 / MM solver seconds |
|---|---:|---:|---:|---:|---:|
| g0001 random_er n80 | 252 / 3.150000 | 252 | 261 | 248 / 3.100000 | 59.014 / 3.834 |
| g0008 barabasi_albert n160 | 580 / 3.625000 | 614 | 633 | 597 / 3.731250 | 59.034 / 12.610 |
| g0006 random_planar n80 | 126 / 1.575000 | 126 | 127 | 118 / 1.475000 | 59.009 / 0.532 |
| g0013 grid n128 | 162 / 1.265625 | 162 | 168 | 133 / 1.039062 | 59.011 / 0.490 |
| g0016 complete n100 | 726 / 7.260000 | 726 | 726 | TIMEOUT | 59.185 / 60.597 |
| g0017 diagnostic_control n80 | 199 / 2.487500 | 199 | 201 | 181 / 2.262500 | 59.011 / 1.777 |
| g0201 watts_strogatz n100 | 244 / 2.440000 | 245 | 248 | 223 / 2.230000 | 59.017 / 0.816 |
| g0202 sbm n100 | 251 / 2.510000 | 253 | 261 | 241 / 2.410000 | 59.017 / 1.642 |
| g0021 grid n128 | 158 / 1.234375 | 158 | 163 | 133 / 1.039062 | 59.008 / 0.399 |

Within-chain variance (across-seed variance is unknown):

| Input | A065 | A064 | A061 | MM |
|---|---:|---:|---:|---:|
| g0001 | 1.55250000 | 1.55250000 | 1.56859375 | 1.64000000 |
| g0008 | 5.60937500 | 5.16109375 | 5.39183594 | 5.87152344 |
| g0006 | 0.69437500 | 0.69437500 | 0.71734375 | 0.37437500 |
| g0013 | 0.19506836 | 0.19506836 | 0.32421875 | 0.03753662 |
| g0016 | 0.19240000 | 0.19240000 | 0.19240000 | TIMEOUT |
| g0017 | 0.79984375 | 0.79984375 | 0.77484375 | 0.91859375 |
| g0201 | 1.24640000 | 1.26750000 | 1.34960000 | 0.93710000 |
| g0202 | 1.52990000 | 1.52910000 | 1.35790000 | 1.22190000 |
| g0021 | 0.19506836 | 0.19506836 | 0.24554443 | 0.03753662 |

The control's hidden singleton witness certifies Q80, making candidate Q199 a substantial construction deficit despite MM's Q181 also being suboptimal. Relabeling changes the grid result from Q162 to Q158 while MM remains Q133. A065's BA160 maximum chain rises from A064's 11 to 13 and its within-chain variance rises; SBM variance also increases slightly. Every variance remains visible above. Across-seed ACL variance is unmeasured.

All four methods were paired on hyde06 in the unchanged shuffled order, seed 0, 60-second allowances. Total solver wall / CPU / process wall seconds: A065 531.306 / 531.251 / 548.563; A064 531.209 / 531.142 / 547.997; A061 83.264 / 83.218 / 98.946; MM 82.698 / 82.683 / 87.471, including its failed call. The per-input record preserves all times, status, max chain and variance. Process CPU is not separately reported by this audit; solver CPU and parent-observed process wall are distinct. Raw RSS is preserved but has the previously diagnosed inherited-peak limitation.

A065/MM solver ratios on common successes range from 4.68 to 147.86. The roughly-MM-order runtime goal remains unmet on most sparse examples; no universal gate is used. These are full-allocation quality results, not complete-constructor speedups. All nine A065 and A064 added stages reach the deadline with no closed fixed epoch. Compilation is charged. The candidate does more work in roughly the same elapsed time.

## Mechanism resolved and next decision

Root ranking falls from 329.908/449.677 A064 stage seconds (73.37%) to 42.184/447.406 A065 stage seconds (9.43%). These are different amounts of searched work, not a paired per-query speed ratio; the earlier exact six-query packet supplies that controlled comparison. A065 makes 68 strict-Q commits versus 39. The saved base Q agrees with both A064 and fresh A061 on all nine inputs; exact base-map equality and common trajectory prefixes are being checked by a separate passive receipt reversal before attributing the full difference to extra search.

The remaining cost is 387.480 seconds of reconstruction, 387.328 of it in non-improving proposals: 86.6% of the added stage. The grid result remains Q162 despite 22,991 completed trees, 22,987 Q rejections and four commits; the relabeling remains Q158 after 18,760 completed trees. Neither search exhausts its fixed-epoch neighborhood, so these counters do not prove local optimality or an acceptance barrier. They identify where computation now goes.

Continue the unchanged A065 policy to previously unmeasured development structures and sizes rather than optimizing root ranking further. Preserve paired A064/A061/MM controls, all small-screen ties and losses, cold costs and historical failures. Before another mechanism change, distinguish expensive tree construction from a neighborhood/acceptance limitation: a cheaper exact evaluation might expose later strict improvements; a bounded diagnostic showing only neutral or temporarily longer routes would instead motivate a different move or acceptance policy. No chain of local repairs is authorized merely because the rejection count rises. A's findings complement B's actual-union-cost diagnosis and C's constrained routing evidence without combining independent algorithms.

Evidence: `results/codex/a065-constructor/{audit001,mechanism001,report001}`. Report projections are generated by `report.py`, with source/result bindings in `report001/bindings.json`. Terminal retrieval occurred once after controller completion, missing tmux handle and free lock; all 311 archive files verified, artifact digest `9b97096fc9d4f0e10826c9e7e97668574adeb573ad6832c1ff67cd7a8b83ccf1`. First audit process wall 1.030s; passive reader 0.520s; table projection 0.097s. No additional constructor calls were made during analysis.
