# B019: the four complete-constructor gates pass

2026-09-08. Exactly four seed-0 calls ran, each with its fixed five-second deadline. **No panel or registry edit occurred.** The new standalone constructor uses the reviewed prepared-state policy; frozen B018 remains unchanged.

| Case | Initial → final Q/O | Result | Total / query units | Total / query ms |
| --- | --- | --- | ---: | ---: |
| Path3 → path5 | 3/0 → 3/0 | Valid, already feasible | 2,243 / 2,016 | 2.868 / 2.433 |
| Star → same star | 4/0 → 4/0 | Valid, already feasible | 3,130 / 2,856 | 3.074 / 2.785 |
| Triangle → triangle | 4/1 → 3/0 | Valid, overlap resolved | 8,715 / 8,440 | 7.944 / 7.538 |
| Triangle → path3 | 4/1 → 4/1 | Failure, overlap retained | 36,520 / 36,144 | 32.184 / 31.632 |

Path and star start at their Q=n lower bounds, so their success concerns initialization and safe termination, not search reach. Triangle on triangle supplies the actual continuation: its first query commits Q4/O1/E5 → Q3/O0/E3, changing two witnesses; subsequent feasible queries preserve Q3. The negative case completes eight price epochs and 24 queries without a commit. Its final energy increases from 5 to 13 solely because the unresolved site's price rises; this is not worsening physical Q or a comparable fixed-price objective increase.

All three returned embeddings pass the reused independent original-graph validator. Independent initial/final snapshot checks verify all original witness couplers, nonempty connected chains, actual Q/O and price-weighted energy. The negative snapshot is rejected for overlap and its public embedding is empty. All 35 queries complete, with no local/global work or deadline limit, unchanged original inputs and consistent nested work accounting. Initial setup costs 185–214 units; finalization costs 8–42. These tiny costs do not test Z12 scaling.

The mechanism conclusion remains narrow. Representation and acceptance permit one real overlap resolution here. The winning two-witness move does **not** establish that pairing is necessary: in the triangle's initial state, changing witness 12 alone from `(2,0)` to `(2,1)` would allow the three singleton chains. This is a hand-checked alternative on the saved actual target, not an additional call. The inspected negative case cannot distinguish neighborhood from acceptance limitations because a triangle has no minor embedding in a path. No result yet establishes placement quality on the exposed panel.

[Nine targeted checks](../../../results/codex/track-b019-constructor/attempt002-checks/summary.json) pass, including frozen B018 pool/score/winner equivalence at lambda=1, weighted local deltas, outside-owner conflict totals, exact last-unit/query offsets, interrupted private commits, isolate-prefix retention and reserved final validation. The earlier eight-check pass is preserved; the ninth only covers metered price serialization. No failed test or post-observation source correction occurred, and no prohibited import loaded.

After root review, propose **one 27-call screen** on the unchanged exposed nine inputs: fixed B019 paired contacts, an otherwise identical primary-edge-only ablation, and fresh isolated MM. Keep initialization, prices, shared budgets and validation fixed. Measure overlap resolution, ACL, query coverage and cost together; count optimal ACL1 ties as reaching the lower bound. No output selection or cap/pool rescue is proposed.

Evidence: [pre-code policy](b_019_constructor_policy.md), [pre-observation mechanism decisions](b_019_mechanism_gate.md), [four raw outcomes](../../../results/codex/track-b019-constructor/attempt003-cases/summary.json), [manifest](../../../results/codex/track-b019-constructor/artifact_manifest.json). Source SHA-256: `86d5b6dcc3cfee449ae499b727f4d201e5730db451ee07e7553aaddb02a9d65b`.
