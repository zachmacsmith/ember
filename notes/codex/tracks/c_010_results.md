# C010 adaptive clones — retire the fixed policy

C010 completes **2/8 timely valid embeddings**, versus MM's **6/8**. Path and tree attain optimal **ACL=1**, tying MM without any split. These two Q ties fail the required three, and coverage fails the required six. The median solver-time ratio on those two common timely pairs is **2.314**, passing only that condition. The fixed policy is retired unchanged.

`S` means timely success; `F` means failure; `late` is a valid but uncredited MM map. Successful cells report Q. Failed candidate cells report **placed sites / total clones / missing original edges**; these are incomplete assignments, not original minors. Times are solver seconds. Full ACL, process times and statuses remain in the [sixteen-row table](../../../results/codex/track-c-010-review/analysis001/table.csv) and [audited rows](../../../results/codex/track-c-010-review/analysis001/rows.json).

| Input | C010 outcome | Seconds | MM outcome | Seconds |
|---|---:|---:|---:|---:|
| Path | S: 141 | 0.408 | S: 141 | 0.174 |
| Tree | S: 121 | 0.374 | S: 121 | 0.164 |
| Grid | F: 117/151/47 | 0.439 | S: 134 | 0.353 |
| Planar | F: 9/165/434 | 0.449 | S: 281 | 0.580 |
| ER | F: 5/137/863 | 0.332 | S: 1044 | 8.336 |
| Regular | F: 0/284/2800 | 0.401 | late: 2481 | 15.369 |
| Complete | F: 0/239/8001 | 0.653 | late: 2170 | 17.415 |
| SBM | F: 7/124/614 | 0.318 | S: 638 | 4.083 |

**All six failures are work-allowance censored:** each reaches nineteen million search units after just **0.318–0.653 seconds**, far below the fifteen-second wall deadline. None terminates as an unresolved-conflict exit or wall timeout. Conservative full-width bitset charges are not measured CPU costs, so this is not evidence of expensive wall-time construction or inadequate runtime scaling. Across all eight candidate calls, setup consumes **45.4% of units**, but input/initialization takes **0.748 seconds**, only **22.2% of solver wall**; placement/splitting takes 2.158 seconds. Shared domain operations consume 38.9% of units and cannot be assigned precisely to selection versus support callers.

There is also completed neighborhood evidence. Grid finishes **55 failed revisions and 23 splits** before an interrupted split. Planar finishes **52 failed/3 committed revisions and 13 splits**, then an interrupted revision. ER finishes **13 failed/1 committed revision and 4 splits**, then an interrupted split. SBM finishes **11 failed/2 committed revisions and 4 splits**, then an interrupted revision. Regular and complete finish **144/112 degree splits**, respectively, place no sites, and stop during selection. Overall, **139 revision attempts = 131 failed + 6 committed + 2 interrupted**; **300 splits commit and two are interrupted**. The fixed local placement/partition neighborhood often fails before censoring, but neither those failures nor the untested dense placement phase proves global clone inadequacy or necessary Q growth.

[Receipt arithmetic](../../../results/codex/track-c-010-review/receipt_summary.json) retains all attempts: candidate solver/CPU/process totals are **3.375/3.375/5.484 seconds**; MM totals are **46.474/46.472/48.591**, including both late maps. Unequal completion coverage prevents treating those totals as a speed win. Nested attempt walls are not counted twice.

The frozen auditor ran once and passed with zero errors: all **195 archived files**, original-label final/partial contacts, physical membership, clone IDs, owner trees and original-edge identities were checked. Saved receipt arithmetic was reconciled without replaying unsaved domains or intermediate placements. [Final bindings](../../../results/codex/track-c-010-review/review_manifest.json) preserve every failure. No constructor rerun, cap adjustment, follow-up numerical work, family-mean/variance estimate or novelty claim follows this repeated-development, single-seed screen.
