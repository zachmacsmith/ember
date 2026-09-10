# A065: distinguish contact restrictions from additional search cost

2026-09-10. **Design only. Prioritize a small, exact test of whether moving one
neighbor enables a shortening that is impossible with that neighbor fixed.**
Keep contact-preserving pruning as the second hypothesis. No new diagnostic,
constructor, source modification or cluster action was performed for this note.
The running broader A065 screen remains unchanged and root-owned.

The [nine-input result](../experiments/065_constructor_results.md) retains seven
MM Q losses, one win and its K100 timeout. A065's three gains over A064 come from
longer committed trajectories from exactly equal bases; the other six final
ordered maps are identical ([receipt recovery](../experiments/065_base_recovery_results.md)).
This establishes useful additional search on BA/WS/SBM, not that all remaining
gaps are computational. A061 is still the retained algorithm pending the broader
comparison. These are development observations, not class-level estimates.

## What the current evidence separates

| Possible cause | What is established | Observation that would distinguish it |
|---|---|---|
| Global embedding representation | The added stage stores arbitrary connected, disjoint site sets. It is not restricted to rail intervals or fixed-length templates. The inherited constructor can still place them poorly. | A valid better map outside an alleged representation would establish a representational exclusion. No such exclusion is identified here; do not confuse the query's restrictions with the state format. |
| Query representation and move neighborhood | One fixed spanning tree and one lexicographically selected coupler per protected source edge constrain donor trimming. One deterministic nearest-contact extension is produced per root. Most other owners stay fixed. | A contact-preserving donor deletion forbidden only by its chosen witness isolates that restriction. A shorter connected tree on the same free sites and contact groups isolates greedy reconstruction. A feasible coupled placement when the exact one-owner shortening domain is empty isolates a coordination limitation for that move. |
| Strict-Q acceptance | Only complete strict-Q improvements change the added-stage incumbent. The prepare bound closes exactly a singleton focus with zero removable donor sites. | A valid equal-Q first move followed by a valid strict shortening, where the specified shortening was impossible before that first move, establishes a useful neutral bridge. A rejected proposal count alone establishes neither neutral availability nor a barrier. |
| Computation and allocation | 387.328 seconds, 86.6% of A065's added-stage total, reconstruct non-improving proposals. All stages reach time limits; none exhausts a fixed epoch. Grid completes 22,991 trees but ends at Q162. | Later strict improvements under identical query semantics support insufficient search time. Complete failure of a precisely specified finite neighborhood supports that neighborhood's insufficiency. Interrupted scans remain censored. Rejected maps are not saved, so duplicate reconstructed trees are currently unmeasured. |

The singleton deduction follows directly from
`1 + retained >= |C(u)| + sum(old donor sizes)`: donor savings are nonnegative
and `|C(u)| >= 1`, so closure requires `|C(u)|=1` and zero donor savings.
Last-epoch closed-owner counts are grid 77/128, relabeled grid 85/128, planar
45/80, ER 8/80 and the singleton-witness control 6/80. This identifies excluded
mobility, not useful destinations. It also cautions against assuming one
singleton mechanism explains the ER/control gap.

The source was read directly: A065 imports A064's unchanged `_Search`; A063
`prepare` pins witness endpoints, while `reconstruct` repeatedly attaches the
nearest unmet contact to the whole growing tree, then pins newly chosen
witnesses before trimming. It already uses shared branches. Claiming that it
merely connects every neighbor independently to a root would be incorrect.

Pinned MM's `pathfinder.hpp` lines 193–200, 292–302, 378–440 and 674–705 show
whole-chain removal/reconstruction, a separate current and saved-best map, and
continued completed passes without restoring the previous map merely because
the best statistic did not improve. `check_improvement` at lines 142–184 ranks
chain-length histograms, not total Q. Thus its useful capability is revising
physical contacts without a strict total-Q improvement at every working-state
change. This source observation does not establish that MM used a neutral
bridge on any saved comparison map, or that its whole policy should be copied.

## 1. Relocation followed by shortening in one private transaction

**Hypothesis.** Some sparse and control excess consists of chains whose contacts
cannot share one physical site while adjacent owners remain fixed. A valid
same-size relocation of one adjacent chain can open that contact intersection.
Evaluate the resulting shortening before publishing either change. This replaces
a speculative neutral score with an actual, independently certified Q saving.

```text
on the current valid embedding, consider an owner v and its source neighbors
    privately reconstruct v at equal total Q, preserving all original contacts
    for an affected adjacent owner u:
        reconstruct u against that private map
        if the composed map is valid and strictly smaller than the entry:
            certify and publish the composed change; invalidate affected queries
    otherwise discard the private map; the incumbent never changes
```

This is a mechanism sketch, not a frozen production schedule. Singleton v has
an inexpensive exact relocation domain; larger chains would use whole-chain
reconstruction, not a singleton-only global constructor. No wider implementation
is warranted merely because the singleton diagnostic is easy. The public state
remains one evolving embedding, and the operator never selects between complete
algorithms. The initial A061 call remains the sole constructor entry.

**Cheap falsifier, to freeze separately.** Use the already validated A065 final
maps of ER80, planar80, grid128, control80, fresh WS100 and fresh SBM100; no MM
maps or synthetic witnesses enter the diagnostic. Enumerate source edges
`(u,v)` with `|C(u)|=2`, `|C(v)|=1`. With every outside chain fixed, form the
exact singleton placement domains after releasing these two owners:

`D(x) = available sites intersect intersection_{w in N(x) minus {u,v}} N_H(C(w))`.

Here `available` includes all unused sites and both released chains; `N_H` is
actual target adjacency. Empty intersections impose no contact restriction.
Enumerate actual couplers `p in D(u), q in D(v)` with `p != q`. First test
whether u could already become a singleton with v at its original site. If
that domain is empty but a two-singleton pair exists, the particular 2-to-1
shortening needs coordinated movement. Then check whether placing v at q first
is disjoint from the original two-site C(u) and retains all original contacts,
including its edge to u. If so, this is an exact
neutral-then-strict witness for the proposed mechanism. If not, it supports
joint release only; do not credit it as a neutral bridge.

For the strongest acceptance attribution, separately mark pairs where u has
zero removable donors under the existing query: there, its strict-Q test
requires a singleton. Verify every positive composed map with the unchanged
original oracle. Exhaust this finite two-owner primitive under a frozen wall
allowance; report unfinished scans as unknown, plus all zero-domain/no-bridge
cases and setup/query/validation time. No IP solver is needed.

No witnesses rejects this primitive as the immediate integration target; it
does not rule out larger or temporarily uphill rearrangements. Positive
witnesses on several structures warrant a small complete-constructor screen
promptly, with a specified interleaving and full cold/runtime accounting.
Local witness counts alone cannot justify production continuation.

**Self-critique.** Adjacent singleton domains may be unique, especially at high
degree; some improvements may require three owners or temporary invalidity.
Nested reconstruction can multiply cost and changing the incumbent can lose
later improvements. Historical [033](../experiments/033_results_review.md)
already rejected a direct-singleton policy despite local savings, while
[045](../experiments/045_results_screen.md) demonstrated some two-owner vacancy
repairs. This proposal is neither evidence of novelty nor a reason to restart
those policies. Its narrower new question is whether a fully specified valid
neutral bridge remains available in the present A065 states and pays in complete
construction. If the primitive is absent, do not enlarge its search repeatedly
without a new observed obstruction.

## 2. Preserve contact existence rather than a chosen contact endpoint

**Hypothesis.** Some donor and newly reconstructed sites are retained solely
because they carry a chosen witness, even though another actual coupler can
preserve the same logical edge. Removing that artificial obligation can release
sites and change boundary placement across several source structures.

```text
prepare the same donor spanning trees as the control
maintain actual remaining coupler counts for all protected source edges
    consider donor leaves in a fixed order against one shared private state
    remove a leaf only if its chain remains nonempty and connected
        and every protected edge retains at least one actual coupler
    update counts immediately; focus-owner contacts are rebuilt later
reconstruct the focus with the unchanged search
trim its leaves using contact existence, rather than fixed witness endpoints
certify the entire composed map and require a strict total-Q improvement
```

Counts must reflect **both** changing endpoints: independently trimming two
donors against the old other chain can destroy their mutual edge. Sequential
updates to one shared private state avoid that new correctness risk. Fix the
old spanning trees and orders in the first comparison so that a result concerns
contact obligations, not a simultaneous tree-order change. Connectivity through
the retained tree is sufficient; it is not a minimum connected group cover.

**Cheap falsifier, to freeze separately.** On the same six final maps, compare
the control's preparation with this exact contact-preserving leaf rule for each
owner. Report sites that the old chosen witness protected but the actual edge
does not require. Also compare final trimming on fixed reconstructed trees if
such trees are captured in a separately frozen query packet. No newly released
sites rejects witness pinning as the immediate explanation on those states.
New space alone is insufficient: a short fixed-root packet must produce actual
strict-Q improvements before a small complete-constructor screen is justified.
All validation/setup/reconstruction cost belongs to the candidate comparison.

**Self-critique.** Alternative couplers may be rare. Singleton donors have no
leaf to release, so this cannot by itself repair their immobility. Greedy
deletion order can discard a useful boundary and make the focus chain longer;
the strict-Q gate protects the incumbent within a query but does not guarantee
better complete trajectories. Contact-count maintenance can cost more than it
saves. Stem redistribution already exists in MM and A063; changing protected
obligations is a testable general heuristic, not a novelty claim.

Both ideas use Zephyr's actual external, odd and cross-orientation couplers.
The pinned generator confirms these three edge types; their real neighbor
intersections, including staggered offsets and boundary truncation, determine
whether a relocation/contact substitute exists. A geometric crossing alone is
never a contact. No source family, instance ID or prescribed rail embedding
enters either mechanism.

Stop further ranking optimization and unmeasured neutral-score refinement.
Keep the broader A065 result independent. Any later complete screen must retain
the old success/Q regressions, fresh structures and relabelings, paired host
timing and all failed/censored calls. Neither mechanism repairs an inherited
constructor failure, and neither changes the final per-class objective.
