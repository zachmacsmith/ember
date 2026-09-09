B022 fails its fixed gate and is **retired**: one of nine valid timely embeddings, with zero common-success Q wins/ties (required: seven and three). The one approved saved analysis passed without audit errors. All 18 calls and failures remain recorded.

| Input | B022 final O (initial O) | B022 valid Q | MM Q | Solver seconds B022 / MM |
|---|---:|---:|---:|---:|
| K40 | 46 (49) | — | 194 | 19.074 / 16.030 |
| K100 | 167 (169) | — | timeout | 19.084 / 25.264 |
| Bipartite | 50 (69) | — | 180 | 19.048 / 9.859 |
| ER | 77 (123) | — | 211 | 19.057 / 6.616 |
| Regular | 25 (107) | — | 90 | 19.057 / 1.508 |
| Watts–Strogatz | 39 (125) | — | 94 | 19.060 / 1.964 |
| Grid | 4 (86) | — | 70 | 19.042 / 0.624 |
| Honeycomb | 0 (88) | 93 | 71 | 19.017 / 0.410 |
| King | 37 (95) | — | 90 | 19.011 / 0.609 |

The eight B022 failures retain overlap; their partial Q is not ACL evidence. Honeycomb resolves its initial conflict, then makes eight commits after feasibility, but finishes **22 Q above MM (+31.0%) at 46.4× solver time**. All nine searches stop at the reserved search deadline, using 5.45–7.22M of the 20M global allowance. MM succeeds on eight and times out on K100; its late elapsed time stays in totals.

**Neighborhood reach changed:** 474 commits include 291 overlap reductions. Dense states now move, unlike B020's certified compulsory-terminal lock. This is consistent with releasing whole incidence, although the owner schedule changed too. Local reach did not become reliable complete construction.

**Acceptance remains restrictive:** 795 scored overlap reductions and 181 Q reductions are ineligible under the current energy/feasible-Q rule. Twenty-one accepted moves increase overlap while decreasing weighted energy. These receipts do not establish that changing acceptance would solve the inputs; prices change between sweeps, so initial/final E are not a common descent metric.

**Interruption is material:** 1,017/1,124 queries complete. The 107 interruptions comprise 98 query work caps and nine search deadlines. They discard 230 certified eligible proposals across 47 queries, including 110 with lower overlap. K100 completes only 1/55 queries and discards eligible proposals in 28. That is a cost/publication restriction, not neighborhood infeasibility. None of the discarded proposals reports O=0; honeycomb is the only input with any scored O=0 proposal.

**Cost is broad:** 40.8% of query units go to routing, 33.6% to contact recounting and 20.3% to roots; these are work fractions, not time fractions. Query wall totals 155.989 seconds. All-attempt solver/CPU/process totals are B022 **171.451/171.304/187.096 seconds**, MM **62.883/62.737/76.982 seconds**. Starting load is 33.90–34.22 on 32 affinity CPUs. No historical timing is pooled.

No cap, beam, root or publication rescue follows this failure. It does not prove whole-incidence representations impossible, but it rejects this complete policy. [All rows/table and fixed decision](../../../results/codex/track-b022-analysis/analysis001/summary.json), [per-input CSV](../../../results/codex/track-b022-analysis/analysis001/table.csv), and [saved-counter mechanism projection](../../../results/codex/track-b022-analysis/mechanism001/summary.json) retain exact scores, counts, limits and attribution boundaries. No constructor was rerun.
