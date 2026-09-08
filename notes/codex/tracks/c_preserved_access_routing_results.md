# Preserving access blocks this fixed shortest-path policy

The invariant holds on every committed state, but none of the eight supplied initializations reaches a complete original minor. Six inputs exhaust their single pass; regular and complete reach the 30-second deadline. Every final assignment has nonempty connected disjoint chains and realizes its claimed original-source contact subset P. Every incomplete state keeps the unused full-target graph connected and gives every chain with missing contacts a free neighbor. Preserving that availability did not make the fixed shortest paths admissible often enough.

The [predeclared policy](c_preserved_access_routing_proposal.md) used the same saved starts, target, canonical pass and 30-second/1,024-visit/256-commit limits. It tried endpoint cuts of one shortest path, considering full-original completion before connectivity rejection. No alternate paths, repeated passes, ownership transfers, reserve changes, cleanup, constructors or MM calls ran. Q below describes occupied sites in incomplete assignments, not valid-embedding quality.

| Input | Stop | Initial missing | Final missing | Prior unrestricted final missing | Final Q | Seconds |
|---|---|---:|---:|---:|---:|---:|
| Path 2030 | Exhausted | 18 | 6 | 3 | 566 | 1.572 |
| Tree 5058 | Exhausted | 7 | 2 | 0 | 447 | 0.813 |
| Grid 1584 | Exhausted | 35 | 16 | 13 | 533 | 2.696 |
| Planar 31536 | Exhausted | 82 | 61 | 42 | 632 | 4.377 |
| ER 6450 | Exhausted | 356 | 277 | 262 | 779 | 18.305 |
| Regular 14334 | Timeout | 984 | 759 | 696 | 2044 | 30.001 |
| Complete 1041 | Timeout | 1634 | 1300 | 1199* | 3716 | 30.002 |
| SBM 30736 | Exhausted | 220 | 153 | 135 | 624 | 13.100 |

*The prior complete-input result reached its visit cap. These are separate supplied-state diagnostics, with different censoring, not paired constructor performance measurements.*

There were 446 commits and 1,356 fully guard-rejected paths. Of 12,666 examined cuts, 11,917 failed unused connectivity/nonemptiness, 303 lost a required free boundary and 446 were feasible. Accepted assignments were 440 all-to-lower-endpoint and six all-to-upper-endpoint; no actual input selected an interior split. Thus the dominant obstacle is the whole-path unused-connectivity requirement, not the endpoint cut. Tree's previous completion becomes two missing edges, an explicit regression.

No remaining edge lacks a shared unused component. This is not evidence that a safe path exists, or that the fixed one-pass schedule is sufficient. Some rejected edges were later realized incidentally; other rejected guards could become admissible later. `SCHEDULE_EXHAUSTED` therefore asserts no impossibility theorem.

Both timeouts preserve their last certified incumbents. Regular interrupts the unused-remainder traversal before testing a cut. Complete retains eight rejected cuts of fifteen possible assignments and an uncommitted raw Q=3,730 proposal that realizes P plus its requested edge but fails the guard; final Q remains 3,716. There are 419 and 833 unattempted schedule entries respectively. All 454 committed-state access records completed. SBM's one sealed chain has no remaining required contacts, so it does not violate the invariant.

Six targeted routing groups and four tiny saved-data replays/four corruption checks passed before execution. Independent replay verified all committed invariants, 471 original-label gates and the saved cut/contact/port arithmetic. Input wall totals 100.866 seconds, including 52.573 seconds in cut guards and 35.726 seconds in independent commit checks. Total diagnostic wall including serialization is 105.840 seconds; saved-data replay costs another 43.534 seconds. These intrusive local costs imply no constructor/MM speed claim.

Keep the invariant as a verified property, but reject this fixed shortest-path/cut policy as sufficient. The [outcomes](../../../results/codex/track-c-preserved-access-routing/analysis001/summary.json), [all cuts](../../../results/codex/track-c-preserved-access-routing/analysis001/cuts.csv), [visits](../../../results/codex/track-c-preserved-access-routing/analysis001/visits.csv), [costs](../../../results/codex/track-c-preserved-access-routing/analysis001/stages.csv) and [raw records](../../../results/codex/track-c-preserved-access-routing/results.json) preserve failures and interruptions. This does not reject every reserved-space constructor or establish novelty; no further routing call follows automatically.
