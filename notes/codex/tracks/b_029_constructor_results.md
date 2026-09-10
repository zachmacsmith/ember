# B029 complete-constructor results

2026-09-10. **Reject this fixed policy; do not broaden its screen.** B029 succeeds
on 3/9 development inputs, its fixed-anchor ablation and B028 on 2/9, and
A061/A064/MM on 9/9. It retains both earlier successes but worsens their Q by
26 and 8. Its sole recovered success is planar100; recovery in two families,
required by the frozen continuation rule, did not occur. These results reject
this integration and objective choice, not every use of root movement.

All 54 calls ran separately on hyde02, ideal Z12, seed0, with 60-second cold
allowances. The independent original-graph audit passed. All solver wall/CPU
and process-wall fields are known; every failure is retained. The 27 native
receipts contain no fatal constructor or finalization error. Failed B calls
reach their search deadline with overlap; they earn no Q/ACL credit.

Cells below are Q; mean ACL is Q divided by the stated source size. F denotes
failure, with undefined quality. Anchor and B028 have identical success/Q cells
here but are independent runs with different costs.

| Input | B029 | Anchor / B028 | A061 | A064 | MM |
|---|---:|---:|---:|---:|---:|
| ER80 g0001 | F | F / F | 261 | 259 | 248 |
| SBM80 g0005 | 166 | 140 / 140 | 153 | 149 | 131 |
| Grid128 g0013 | 147 | 139 / 139 | 168 | 162 | 133 |
| Singleton80 g0017 | F | F / F | 201 | 200 | 181 |
| ER100 g0101 | F | F / F | 345 | 345 | 350 |
| BA100 g0102 | F | F / F | 282 | 266 | 199 |
| WS100 g0201 | F | F / F | 248 | 247 | 223 |
| SBM100 g0202 | F | F / F | 261 | 259 | 241 |
| Planar100 g0203 | 171 | F / F | 174 | 172 | 155 |

The three B029 mean ACLs are 2.075, 1.148438 and 1.71, all worse than MM's
1.6375, 1.039063 and 1.55. The variance of chain lengths within each embedding also worsens against MM on
all three: respectively 1.269375 versus 0.406094; 0.157654 versus 0.037537;
1.1459 versus 0.5875. Both shared successes regress against anchor/B028 in
variance as well as mean ACL. Across-seed variability is unestimated.

| Total cost, including failures | B029 | Anchor | B028 | A061 | A064 | MM |
|---|---:|---:|---:|---:|---:|---:|
| Solver wall, s | 513.755 | 507.710 | 491.044 | 260.993 | 531.294 | 41.842 |
| Solver CPU, s | 513.462 | 507.530 | 490.876 | 260.115 | 530.980 | 41.829 |
| Process wall, s | 534.111 | 528.744 | 513.080 | 302.273 | 575.693 | 54.076 |

For the three shared MM successes, B029 solver-wall ratios are 34.79×, 25.22×
and 18.26×; process-wall ratios are 20.35×, 11.86× and 11.36×. These are paired
single-run measurements, not universal runtime gates. The quality/success
deficits already reject the policy. Whole-process CPU is not recorded by the
existing pilot; RSS is retained without an algorithm-specific interpretation.

**Time to validity and incumbent ACL trajectories.** The following are recorded
first-valid and strict-quality events, in seconds from constructor entry.
Intermediate states are constructor receipts; independent credit applies to
the final maps above. All omitted intervals retain the preceding incumbent.

| Input / method | Time : incumbent mean ACL | Stop |
|---|---|---|
| SBM80 / B029 | 42.278: 2.125 → 45.405: 2.1125 → 45.518: 2.1 → 51.417: 2.0875 → 53.450: 2.075 | Search deadline, 59.088 s |
| SBM80 / anchor | 39.206: 1.7625 → 39.428: 1.75 | Period-2 quality recurrence, 51.839 s |
| SBM80 / B028 | 33.816: 1.7625 → 34.463: 1.75 | Period-2 quality recurrence, 50.172 s |
| Grid128 / B029 | 30.626: 1.148438; no subsequent strict gain | Period-2 quality recurrence, 41.390 s |
| Grid128 / anchor | 30.185: 1.101563 → 30.885: 1.09375 → 33.673: 1.085938 | Period-2 quality recurrence, 42.629 s |
| Grid128 / B028 | 19.894: 1.101563 → 20.283: 1.09375 → 21.970: 1.085938 | Period-2 quality recurrence, 27.652 s |
| Planar100 / B029 | 55.743: 1.74 → 56.741: 1.72 → 58.079: 1.71 | Search deadline, 59.094 s |

Every other native call records no first-valid state. The recovered planar
result is an end-to-end gain on one structure new to the B sequence; the added
WS100/SBM100 both fail. The panel has no new source relabeling, no untouched
confirmation and one seed. These limits prevent a class-level generalization
claim. [The causal decision](b_029_causal_decision.md) separates the demonstrated
cost reduction from the unsuccessful complete algorithm.

Evidence: `results/codex/b029-constructor/`. One terminal fetch verified 405 files,
digest `3a9e923de0b39bdbc6eebc5b597a8b9cc748f284e3c58e324c5340eecb4b0cc6`.
The original audit in `audit001/output` passed and binds all 54 raw outcomes.
The first passive reader (`mechanism001`) failed with 18 assertions: its phase
list omitted the existing `routing_array_export` stage. This was a reader
omission, not a candidate change. The failed reader and attempt remain intact.
`mechanism_v2.py` adds that one stage only; reversing it recovers the full old
AST. A 0.087 s focused check explains exactly those 18 failures and verifies
all 27 native stage sums. Root reviewed and ran v2 once: PASS in 0.267 s with
59 output bindings. Approved summary SHA256 is
`99b4a59f1e9c550682c18c1b20cd9f597fde2f7992dc557ee0717e4c8ed8c645`.
Complete per-call quality/time rows and controlled comparisons are saved under
`mechanism002/output`; no constructor or validator was repeated for this correction.
