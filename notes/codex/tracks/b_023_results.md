B023 fails its fixed gate and is **retired**: **6/9 timely valid embeddings and one common Q win**, versus the required seven and three. The single approved saved analysis passes without audit errors. All eighteen calls remain recorded; no constructor was rerun.

| Input | B023 status / valid Q | MM status / valid Q | Solver seconds B023 / MM |
|---|---:|---:|---:|
| K40 | Success / 183 | Success / 194 | 2.631 / 14.230 |
| K100 | Failure / — | Timeout / — | 19.106 / 27.438 |
| Bipartite | Success / 195 | Success / 180 | 6.101 / 7.515 |
| ER | Failure / — | Success / 211 | 15.948 / 10.718 |
| Regular | Success / 277 | Success / 90 | 7.638 / 1.719 |
| Watts–Strogatz | Success / 306 | Success / 94 | 14.021 / 1.159 |
| Grid | Success / 195 | Success / 70 | 4.886 / 1.349 |
| Honeycomb | Success / 145 | Success / 71 | 5.141 / 0.882 |
| King | Failure / — | Success / 90 | 8.540 / 1.183 |

**The intended transition is exercised.** Every successful trajectory records contact loss followed by restoration: 1,279 such events across those six inputs, with actual final minors independently validated. This supports temporary contact loss as a usable construction transition. It does not isolate its causal benefit from changed initialization, neighborhood and acceptance. K40 saves eleven Q (5.7%) at 0.185× MM solver time; that individual win does not satisfy the general gate.

**Short chains remain the principal quality deficit.** The four sparse successes use 2.04–3.26× MM's Q. Cleanup already removes 307 Q across the six successes, taking their first-feasible total from 1,608 to 1,301. Thus omission of that simple cleanup does not explain the losses. Poor initial/coordinated placement, path-union growth, limited owner relocation and stopping at first feasibility remain confounded. These outcomes do not establish which one dominates.

**Forced acceptance permits progress and disruption.** All 2,867 completed route/erasure actions commit; 694 commits increase the current priced energy. Erasures lose 4,362 contact events, of which 3,087 have later restoration recorded. There is no strict-energy rejection bottleneck here. ER and king finish all eight passes with respectively two and one missing contacts, all previously present and then lost. Neither has a primitive interruption. This is an incomplete bounded trajectory with disruptive repairs, not proof of neighborhood infeasibility or a repeated whole-state cycle. All final maps have O=0; their missing contacts still disqualify them.

**The search deadline binds K100; interruptions do not explain the other losses.** It reaches that deadline before completing one pass, with 2,808 missing contacts. Its one interrupted routing action discards one scored proposal, which is not a zero-defect proposal. Every input exercises erasure and price updates. Work ranges from 1.52M to 8.43M, below 20M. Routing accounts for 57.848 seconds (68.9% of candidate solver wall) and 64.6% of work units. No larger pass, price, route or work allowance follows this result.

All-attempt solver/CPU/process totals are **84.011/83.983/99.368 seconds** for B023 and **66.195/66.076/81.028** for MM, including MM's late K100 timeout. Median common solver ratio is 4.03×. Starting load is 33.87–34.12 on 32 affinity CPUs; no historical timing is pooled. Keep the positive mechanism evidence and retire this fixed policy. Any next proposal must address complete construction and sparse Q together, rather than rescue these outcomes with another local adjustment.

[Complete table and fixed decision](../../../results/codex/track-b023-analysis/analysis001/summary.json), [all per-input Q/M/O/F and timings](../../../results/codex/track-b023-analysis/analysis001/table.csv), and [mechanism/cost projection](../../../results/codex/track-b023-analysis/mechanism001/summary.json) retain the detailed evidence and its limits.
