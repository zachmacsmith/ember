# B017: capacity-directed releases still fail both blocked-state gates

2026-09-08. **Do not launch a panel for this fixed policy.** The exact B016 capacity/priority implementation changes which block is tried and agrees with the independent static classifier, but neither actual saved blockage is repaired. No full constructor, MM call, registry edit or cluster run occurred.

| Fixed local call | Result | Repair units | Capacity units, included | Whole diagnostic wall |
|---|---|---:|---:|---:|
| Tiny occupied endpoint | Valid full minor, 4 Q | 248 | 70 | 0.113 s |
| Saved ER66 | No reconstruction; local limit | 1,000,000 | 69,072 | 0.803 s |
| Saved K40, next vertex 9 | Sole eligible block fails | 611,854 | 31,021 | 0.618 s |

The isolated `propagating_capacity_construction.py` completes all block assessments before exposing a reordered vector. It rejects necessary capacity violations, prioritizes constrained required owners and their protecting owners, then applies released-Q ties. Its owner pool, one/two-owner limit, B015 first-v component predicate, ordinary roots/routing, frozen chains, future growth/matching, first valid return and all shared limits remain fixed. No candidate-source correction or failed test attempt occurred.

ER first releases `[72]`, as prescribed. It inserts 66 **privately**, then reaches the one-million-unit limit while restoring 72; no block commits. The final recorded path search lacks contact 57 and protects site 4581 for owners 53, 55 and 66. This records the encountered conflict, not a proof against every restoration alternative. The remaining 19 capacity-surviving blocks are not tried.

K40 tries its only capacity-surviving release `[0,12]`. It privately inserts 9 and then 0, but insertion of 12 returns no candidate. Its query ends with `all_blocks_failed` at 611,854 units, below the local cap. A larger allowance alone would not revisit different choices in this completed query. The original 24-chain/137-Q entry remains unchanged; temporary insertions receive no additional-placement or ACL credit.

The live assessment receipts total 69,072 units/0.0506 seconds for ER and 31,021/0.0215 seconds for K40. Component filtering adds 5,475 and 125 units respectively. These are overlapping subtotals inside the reported repair work. ER adds only five growth units; K40 adds 78, all completed `no_singleton_neighbor` checks. Matching and propagation totals do not change. Each replay restores the saved global/sub-budget counters and promotion set; separate setup and all failed work remain in the raw records. No static operation totals are substituted for engine scans.

[Ten targeted test groups](../../../results/codex/track-b017-checks/attempt001/summary.json) pass, including selected-versus-future demand, shared guard sites, assessment-before-search ordering, unknown interruption without a reordered prefix, rollback/last-unit/global limits, frozen ownership, and unchanged ordinary-success choices. For both saved states, **every completed capacity row and the entire reordered vector match the independent static result exactly**. The tiny returned minor independently validates original contacts, disjointness, connectedness and outside equality. [All three local records](../../../results/codex/track-b017-checks/attempt002-local-reach/summary.json) are retained.

The tested capacity rules explain some impossible neighborhoods, but preserving complete-block necessary conditions does not make greedy sequential restoration succeed. These outcomes do not justify another priority tweak or cap increase. A future change would need to address the committed choices inside the local rebuild, or reconsider this constructor strategy, rather than treating static eligibility as evidence of actual reach.

Stable source SHA-256: `cf918f29cc16b2965d168cef49fc54add1d4a3d13eabe33c5a15bcef2b75cbf1`; tests: `e081b7f3e2227c0393641e05f6d3ba9969e85489aee86e5eabe8b83fbdcfd1a5`. Synthetic checks can be repeated in a new directory with `.venv/codex-native/bin/python -B results/codex/track-b017-checks/run_checks.py OUTPUT`. No repeat of the three local observations is needed.
