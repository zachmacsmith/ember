# C014 complete-constructor decision

2026-09-09. **Reject the fixed capacity-reservation constructor; do not broaden it.** C014 succeeds on4/9 inputs versus A061/MM9/9. It reaches the hidden singleton control’s independently certified optimum Q80/ACL1, but loses every ER/BA success and regresses in Q on SBM and Watts–Strogatz. The frozen requirement of improvements on two generated development families is unmet. No selected mix of C014 and A061 outputs is retained.

The27 calls on hyde03 completed under seed0, empty configuration, ideal Z12 and60s allocations. Root fetched the quiescent run once (262 files; digest48e2b32b752b5b0fe4798e62293959eb198a26f7c9e0a1282b70b6dc4d656d93). The common original-label audit passes in its first14.060s attempt; every solver wall/CPU and process time is known. The prepared passive reader passes first attempt in23.644s with all nine receipts checked. Root reviewed its full source, verified index semantics and rechecked all25 evidence bindings. Neither analysis calls a constructor.

| Input | C014 Q / ACL | A061 Q | MM Q / ACL | C014 / MM solver seconds | C014 process seconds |
|---|---:|---:|---:|---:|---:|
| random_er-80 (g0001) | FAILURE | 261 | 248 / 3.100000 | 14.508 / 2.545 | 17.004 |
| sbm-80 (g0005) | 187 / 2.337500 | 153 | 131 / 1.637500 | 49.574 / 0.561 | 71.543 |
| barabasi_albert-160 (g0008) | FAILURE | 633 | 597 / 3.731250 | 59.501 / 10.180 | 60.086 |
| watts_strogatz-80 (g0004) | 175 / 2.187500 | 163 | 136 / 1.700000 | 54.989 / 0.489 | 81.295 |
| random_planar-160 (g0012) | FAILURE | 284 | 276 / 1.725000 | 59.505 / 1.450 | 77.975 |
| singleton_control-80 (g0017) | 80 / 1.000000 | 201 | 181 / 2.262500 | 6.310 / 1.530 | 7.137 |
| ember_1584 (g0013) | 143 / 1.117188 | 168 | 133 / 1.039062 | 23.083 / 0.344 | 35.899 |
| random_er-100-p008 (g0101) | FAILURE | 344 | 350 / 3.500000 | 27.017 / 1.927 | 32.761 |
| barabasi_albert-100-m3 (g0102) | FAILURE | 282 | 199 / 1.990000 | 23.081 / 4.975 | 24.318 |

The two newly generated100-vertex ER/BA inputs both fail. Seven other inputs were exposed development. The control’s witness was evaluator-only and never supplied to C014. Its Q80 result proves this constructor can represent and discover a compact native subgraph on this one control; it does not isolate the causal contribution of capacity reservation or establish generalization. Grid improves over A061 but remains10Q worse than MM. SBM and WS regress by34Q and12Q versus A061, respectively.

Within-chain variances for the four successes (C014 / A061 / MM):

- g0005: 2.04859375 / 0.77984375 / 0.40609375.
- g0004: 2.05234375 / 0.86109375 / 0.43500000.
- g0017: 0.00000000 / 0.77484375 / 0.91859375.
- g0013: 0.30657959 / 0.32421875 / 0.03753662.

Across-seed ACL variance remains unestimated; within-chain values are distinct secondary outcomes. Full [original audit rows](../../../results/codex/transfer-cycle-002/audit-c001/output/rows.json) preserve every failure and tradeoff. Total solver wall/CPU/process seconds, including failures: C014317.567/317.542/408.019; A06168.453/68.442/81.419; MM24.000/23.997/27.405. The90.452s difference between C014 process and solver sums includes imports, worker validation/output and launch overhead; it is not an isolated serialization measurement.

## Failure mechanism and computation

| Input | Published / n | Stop | Successful rebuild transactions |
|---|---:|---|---:|
| g0001 | 23 / 80 | construction_obstructed | 2 |
| g0005 | 80 / 80 | complete_introduced_source | 8 |
| g0008 | 3 / 160 | search_deadline | 0 |
| g0004 | 80 / 80 | complete_introduced_source | 14 |
| g0012 | 81 / 160 | search_deadline | 13 |
| g0017 | 80 / 80 | complete_introduced_source | 1 |
| g0013 | 128 / 128 | complete_introduced_source | 7 |
| g0101 | 28 / 100 | construction_obstructed | 4 |
| g0102 | 20 / 100 | construction_obstructed | 0 |

All published and checked final states satisfy the individual capacity inequality. This does not guarantee simultaneous future contacts. ER80, fresh ER100 and fresh BA100 stop structurally after14.508,27.017 and23.081s, well before the allowance. Their terminal private rebuilds cannot place an owner without violating earlier private owners’ quotas. The recorded blockers lie inside the movable set; merely expanding that set has no recorded outside blocker to add. The final movable sets contain22/23,28/28 and20/20 published owners, respectively. Enumerated root counts at the failing birth are1,12 and12. No time/work cap explains these three stops, but this is not exhaustive connected-chain infeasibility: each root uses one greedy contact tree and the reconstruction does not backtrack over earlier private placements.

BA160 and planar160 instead stop at the search deadline, after3/160 and81/160 published owners. BA160 spends57.466s in ordinary placement; planar spends56.511s in retraction. The screen therefore separates a computational failure from a greedy reconstruction/capacity-policy failure. Faster logging alone cannot remove the three early structural stops.

Coordinated movement is now exercised by complete constructors: successful rebuild transactions occur on ER80, SBM, WS, planar, the hidden control and grid. They include closed-owner retractions on several inputs. These are broader capabilities than the two zero-retraction tiny controls proved, yet SBM/WS quality regressions show that successful rebuilding alone is insufficient.

The reader counts768,728 completed root proposals and21,360,555 recorded owner-capacity pairs across the nine calls, including rejected and discarded work. The retrieved archive occupies3,923,184,225 bytes; the nine finalized candidate JSON files alone occupy1,950,447,581 bytes. Transfer took200.355s outside benchmark time. These volumes justify revisiting diagnostic representation and computational reuse; they do not measure avoidable time directly. [Receipt projections](../../../results/codex/c014-transfer-analysis/attempt001/output/details.json) preserve nested stage costs without adding overlapping timers.

A separate [targeted measurement probe](../measurement_rss_scope_diagnostic.md) confirms that worker ru_maxrss can inherit the parent’s historical peak under the measured spawn path. Preserve raw peak_rss_bytes, but do not interpret them as algorithm-specific memory requirements. This supersedes such unqualified interpretations in earlier notes, without changing any validity/Q/time record.

## Next decision

Stop the fixed greedy hard-reservation policy and repeated all-root reconstruction as a default refinement sequence. Any follow-up must address revisiting choices inside the private movable set, or show that a different connected-tree space resolves the observed capacity conflict. More outside-set expansion alone does not answer this evidence. A bounded diagnostic may compare the recorded capacity-rejected contact tree with alternative private choices, keeping original partial contacts valid and separating hard quota rejection from missing routes. It must first establish whether the saved rank-encoded states can be reconstructed without inventing history. No new diagnostic or constructor is authorized by this result note.

Self-critique: the optimal hidden control is one exposed structure, the source-family regressions remain, and individual quota counts are only necessary for fixed earlier chains. Some useful capacity-debt or alternative-routing states may be excluded. The next mechanism needs a specific discriminating observation and then a small complete-constructor screen; lower intermediate deficits or more local repairs alone cannot justify continuation. No confirmation, publication or all-class claim is made.
