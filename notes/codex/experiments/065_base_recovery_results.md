# A065/A064 base-map and committed-prefix result

2026-09-10. **All nine paired starting embeddings are exactly equal, including
chain order, and each A064 committed trajectory is a complete prefix of A065's.**
This resolves the previously unmeasured base-map comparison for the completed
nine-input screen. It supports attributing its three Q gains to additional
committed search from the same inherited state, rather than a better initial map.
It changes no benchmark outcome or promotion decision.

All 18 recovered entry maps pass the unchanged independent minor oracle. Reverse
after-chain checks, forward before-chain/full-state checks, owner/index/Q checks
and exact physical-map comparisons pass for every receipt. Comparisons use full
ordered values directly; fingerprints are compact evidence only. Source/target
record order determines indices, with no seeded-rank or chain sorting conversion.

| Development input | A064 commits | A065 commits | Additional A065 Q saving |
|---|---:|---:|---:|
| ER80 | 6 | 6 | 0 |
| BA160 | 11 | 37 | 34 |
| planar80 | 1 | 1 | 0 |
| grid128 | 4 | 4 | 0 |
| K100 | 0 | 0 | 0 |
| singleton control80 | 2 | 2 | 0 |
| fresh WS100 | 3 | 4 | 1 |
| fresh SBM100 | 8 | 10 | 2 |
| nested grid relabeling | 4 | 4 | 0 |

The six tied cases have identical final ordered maps and identical complete
commit sequences, not merely equal Q. BA160 adds 26 strict-Q commits after the
shared 11; WS100 and SBM100 add one and two commits. No shared state or semantic
move diverges. Semantic comparison includes owner, root, root rank, round/slot,
query identity, Q and ordered changed-owner chains; timing/work counters are
excluded. The grid relabeling remains a nested observation, not a ninth
independent structure.

This is saved-receipt consistency evidence, not a replay of every rejected query.
Recovered intermediate maps are receipt-derived; only the recovered entries
receive new independent validation, while the previous common audit owns final
map credit. Same bases and shared committed prefixes support the computational
explanation on these calls, without proving that remaining MM gaps come from
computation alone. The six unchanged maps preserve the contrary evidence that
cheaper ranking did not produce further quality gains there within this screen.
The already-running broader screen must report its own outcomes separately.

Root reviewed the plan, implementation and focused corrupt-receipt check before
authorizing one outcome execution. Recovery passed first attempt: 0.7521s
analysis, 0.8111s recorded process. There were no recovery failures, constructor
calls, candidate imports, rerouting or MM-map/witness reads. The initial tiny
check passed once and its two corrupt-receipt rejections remain recorded.

The [complete recovery report](../../../results/codex/a065-base-recovery/recover001/output/summary.json)
and sibling `rows.json` preserve all entry maps, state fingerprints, direct
comparison results and bindings. The code SHA256 is
`5ae27ee6ed28821b84516f67e36ac2aa7864bb2b9bd0e7a99ca76ff5eb6ab9b1`;
`execution_preparation.json` SHA256 is
`cac410c3696ba68140a6f56f439a2bd0140508f13a8e2f8b7aa7766b31d8bf5f`.
This addendum supplements the frozen constructor result note, which is unchanged.
