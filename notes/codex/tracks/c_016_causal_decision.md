# C016 mechanism decision: allocation improves, construction remains inadequate

2026-09-10 UTC. **Reject C016 and stop allocation-only refinements of this fixed greedy capacity policy.** Its [complete results](c_016_results.md) are 3/8 successes with three large ACL regressions, versus A061/MM 8/8. The experiment nevertheless resolves its specific computation hypothesis and exposes a shared structural failure across ER and BA. No new implementation or experiment is proposed for automatic execution here.

## Resolved allocation hypothesis

All **614 successful ordinary births publish immediately**, including 277 that empty a pending singleton domain. No successful ordinary birth triggers a transaction or remains unpublished. C015's 242 proactive transactions and 181 discarded complete rebuilds are absent. The remaining 12 transactions all follow completed ordinary failures: eight publish a rebuilt birth, three stop at a capacity obstruction and one is interrupted.

Retraction-stage wall is 64.737 seconds, compared with C015's 376.603 seconds on the same eight inputs. Ordinary placement now consumes 188.289 seconds, 73.7% of C016's 255.450-second solver total. The remaining transaction placements consume 23.689 seconds in successful transactions, 13.612 seconds in the three stopped transactions and 27.381 seconds in the interrupted transaction. These are nested placement times, not additional full transaction durations. The policy removes the measured proactive work and recovers WS/grid/planar completion. Different published histories, changed stopping points and separate run conditions prevent interpreting the historical time difference as an isolated counterfactual speedup.

## Shared terminal obstruction

| Input | Solver stop (s) | Final private movable-set size | Recorded blocking owners' capacity / pending degree |
|---|---:|---:|---|
| ER80 | 25.437 | 10 | 2/2 |
| ER100 | 7.368 | 11 | 5/5 and 8/8 |
| BA100 | 53.650 | 6 | 4/4 and 4/4 |

All three terminal placements report **zero generated, started and completed roots**, completed `capacity_exhausted` failure, and `rebuild_failed_capacity_no_outside`. Saved snapshot counts and source adjacency show that every recorded blocker is a non-neighbor of the failing source vertex, has zero spare capacity, and was already reintroduced inside the private movable set. For such an owner, placing the current source vertex does not reduce its pending degree; the hard quota forbids consuming any site in its remaining physical boundary. Under the pinned root-generation code, this removes every qualifying root component before contact-path search begins.

The greedy reconstruction has therefore recreated a conflict *inside the set it already knows how to move*. Its next action can only add recorded outside blockers; none remains to add, so it stops. ER80 and ER100 leave substantial unused time; BA100 also terminates before its search deadline. These stops are not artificial work caps or evidence that Z12 has run out of sites: published states leave 4,564/4,666/4,424 sites unused. Nor are they proofs that no connected-chain embedding exists. The policy does not revisit an earlier private placement within the same reconstruction attempt or relax its fixed-chain quota exclusions.

This directly identifies a move-neighborhood and hard-constraint limitation shared by two source families. Improving the path implementation alone cannot change these particular terminal outcomes because no root reaches that path search. The earlier C014 screen exposed the same inside-set obstruction through a different contact-tree policy; the recurrence is stronger evidence against another allocation-only repair.

## Remaining cost and quality

The hidden control instead spends 42.320 seconds rebuilding after actual placement failures, and ends during an unfinished root. SBM spends 52.268 seconds in ordinary placement and ends during its next unfinished root. Their neighborhoods remain censored; extending time might or might not complete them. Neither case supports treating additional time as a remedy for the three completed zero-root failures.

WS, grid and planar complete but retain Q218/212/281 versus MM136/133/155. Successful first-admissible construction establishes feasibility without ensuring compact contact placement. The receipts alone do not distinguish a poor source order, root ranking, path neighborhood or the absence of later chain rearrangement as the dominant quality cause. C014's better WS/grid and optimal control results remain explicit regressions; the present experiment does not isolate those historical quality differences.

A future coherent redesign would need to reconsider already reintroduced chains when a private reconstruction blocks, and also address complete-embedding quality. The distinguishing evidence for the first requirement is already concrete: zero-root quota conflicts belong to owners inside the movable set. Whether a useful alternative exists under fixed quotas, or requires temporarily revising them, is unresolved. Do not keep expanding outside sets, optimizing the same path kernel or relaxing an arbitrary clock gate as if those mechanisms answer this observation. Any follow-up needs a separately stated mechanism and a prompt complete-constructor test; no local metric earns continuation by itself.

One possible bounded follow-up is a separately frozen saved-state diagnostic of conflict-directed retraction or backtracking **within K**, initially holding quotas fixed. It would test whether revisiting those particular private choices removes the recorded obstruction. That is a diagnostic of an unresolved neighborhood question, not revival or promotion of C016; even a valid local alternative would leave all three complete quality regressions to resolve. No such diagnostic has been implemented or launched.

This attribution uses one frozen passive projection, first execution PASS: 0.107019 seconds analysis wall / 0.097548 CPU, 0.140724 enclosing process wall. It performs no candidate import, graph search or validator replay. It verifies and binds 33 inputs, in addition to eight preparation bindings; the existing audit and reader supply all validity and accounting. Projection source SHA256 `4ecbac777b8de8a518c1873b0994114a12cda8fb6a33b0404b6abdae6d05a1da`; output `689f2122f047dddc1b24f324250c9e378e6d32fa84a8d2f0603b8a57148bf583`; preparation `f9f1559f7482e7d71cafacae59bd8def706038ef6591f012e98b65e71e55c98e`. Self-critique: receipt attribution establishes the performed policy and its terminal cause, not an alternative embedding, causally isolated speedup or general theorem about capacity-based construction.
