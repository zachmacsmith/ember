# Sequential repair completes the complete state, but quality remains poor

The [fixed sequential diagnostic](c_sequential_repair_diagnostic.md) produced an original-valid complete minor for the complete-graph state within its common 30-second deadline. Cleanup reduced Q from 3572 to 2896, giving ACL 22.8031 for that one embedding. The other three inputs remain incomplete. This is useful reach evidence; it does not justify a full C007 constructor or an MM performance claim.

| Supplied input | Missing contacts, initial → final | Added / deleted sites | Final Q | Diagnostic wall | Outcome |
|---|---:|---:|---:|---:|---|
| ER 6450 | 161 → 122 | +182 / 0 | 722 | 5.988 s | Partial |
| Regular 14334 | 232 → 150 | +475 / 0 | 2155 | 9.741 s | Partial |
| Complete 1041 | 3 → 0 | +16 / −676 | 2896 | 17.149 s | Timely valid |
| SBM 30736 | 82 → 56 | +142 / 0 | 626 | 15.563 s | Partial |

On complete, the actual evolving incumbent first uses two neutral donor exchanges and a seven-site path to repair `(8,63)`. It then adds seven sites for `(17,61)` and two for `(43,123)`, protecting every contact realized by earlier steps. Its occupied-site count changes 3556→3572 before cleanup. The unchanged audited deletion routine accepts 676 of 8,741 attempted deletions and completes in 15.215 s. The independent final original-edge gate passes before the deadline. Cleanup therefore dominates this successful diagnostic's cost. Its final Q is still far above the historical MM witness's 1913 sites, which was returned late in the earlier 60-second run; that comparison is quality context only.

All four inputs finished without deadline or error. Across them, 141 committed repairs comprised 133 unused-path additions and eight neutral-transport repairs. They realized 150 original contacts, including nine incidental contacts incorporated into P before subsequent queries. The 25 neutral invocations attempted 473 proposals. All three incomplete inputs exhausted their eight-query ownership allowance; 639 subsequent visit records skip ownership search for that reason. They stalled under the declared schedule and caps, not because all possible repairs were proved absent. No cleanup ran on an incomplete minor.

Independent saved-data replay passed: every committed proposal, all 15 committed donor exchanges, current original-contact protection, deterministic path additions, final ownership/Q accounting and all 676 deletion certificates were checked. The review did not independently enumerate every possible deletion from the final state, so no separate optimality or minimum-Q claim is made. Six targeted sequential groups and a saved-data corruption group passed before execution; a test-only fixture correction is preserved. The four diagnostics took 48.996 s including serialization; saved-data verification added 6.301 s.

These timings start from previously failed C006b states. They omit construction, and the diagnostic ran locally rather than on the earlier constructor host. No constructor, MM, remote run or assembly of independent witnesses occurred. The next useful question concerns initialization quality and access, not automatically increasing repair time.

The [summary](../../../results/codex/track-c-sequential-repair/summary.json), [806-visit ledger](../../../results/codex/track-c-sequential-repair/visits.csv), [commit table](../../../results/codex/track-c-sequential-repair/commits.csv), [query table](../../../results/codex/track-c-sequential-repair/queries.csv), [deletion trace](../../../results/codex/track-c-sequential-repair/deletions.csv) and [manifest](../../../results/codex/track-c-sequential-repair/review_manifest.json) preserve complete outcomes and costs.
