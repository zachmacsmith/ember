# C014 bounded routing diagnostic: before-code contract

2026-09-09. **Plan only.** This is the held routing instrument following the [completed saved-choice diagnostic](c_014_failure_diagnostic_results.md). No routing code or execution is authorized by this note. It uses the same three frozen candidate-owned private prefixes on ideal Z12; all earlier chains remain fixed. C014 remains rejected.

## Hypothesis and distinguishing evidence

C014 constructs contact trees without accounting for how their sites consume earlier owners' reserved boundary capacity, then rejects those trees. A different connected tree may satisfy every old quota and the new owner's quota with the same earlier chains fixed. The completed diagnostic found no zero-allowance cut, but that necessary connectivity result does not establish feasibility. Its 140 recorded previous-birth substitutions produced no valid witness.

| Explanation | Observation this probe can supply |
|---|---|
| Representation cannot express the needed partial minor | A validated, disjoint connected tree with all old chains fixed refutes this explanation for that prefix; it is already expressible by C014's chain-set state. |
| Root/path neighborhood misses a usable tree | A validated tree outside the recorded rejected choices supports this explanation. Record whether the successful root was previously eligible and whether singleton-only root enumeration had excluded it. |
| Hard quota acceptance causes unavoidable rejection | A tree satisfying all unchanged quotas refutes necessity of relaxing quotas for that prefix. Failed bounded search does not prove hard-quota infeasibility. |
| Computation prevents useful routing | Record time to first fully validated tree, roots started/completed and the stage interrupted at five seconds. A late or unvalidated tree is not a positive witness. |

The new root and path rules are coordinated changes. A positive result establishes that a quota-safe route is discoverable by this instrument; it cannot isolate which tie-breaking or root-order change supplied the gain. That finer causal question can be addressed in a complete-constructor ablation if the mechanism survives its first screen.

## Exact proposed policy

Reuse the frozen rank decode, candidate graph order and unchanged original oracle. Let `F` be the free sites; `B(u)` the distinct free boundary sites of an old chain; and

`b(u) = |B(u)| - |G(u) minus (I union {x})|`.

For any new chain or partial tree `T`, track `used(u,T) = |T intersect B(u)|`. This counts sites, not couplers. Exclude every site in a boundary with `b(u)=0`. Component qualification uses all required old neighbors of x, as in the completed necessary test.

**Roots.** If x has introduced neighbors, choose the neighbor with the smallest permitted boundary in qualifying components, breaking ties by source rank. Enumerate every site of that boundary in those components, ordered by decreasing number of required chains already contacted, then target rank. If there are no introduced neighbors, enumerate every permitted site by target rank. A singleton contact domain does not suppress other pivot-boundary roots. There is no top-12 or other root-count cap: the old 12-root receipts reflected available pivot sites, not an artificial limit.

**One shared contact tree per root.** Start with the singleton root and track its actual quota consumption. Repeatedly connect the current tree to any still-missing old neighbor using a multisource path search from its current sites. A path may use only free sites outside the tree, cannot repeat a site, and is discarded immediately if adding its distinct sites would exceed any old owner's remaining allowance. Retain one best feasible path label per reached site, ordered by:

1. Number of newly claimed sites.
2. Sum, over old owners with positive remaining allowance, of the path's additional consumption divided by that allowance.
3. The target-rank sequence along the path.

Select the first missing-contact site removed from the priority queue, breaking any remaining tie by target rank; add that path, update all quota counts, mark every newly contacted required chain, and repeat. Neighbor scans and multisource initialization follow target-rank order. Retaining one label per site is a heuristic restriction: a discarded longer path may preserve a different resource needed later. Failure of an extension ends that root's proposal. A new root begins another chain proposal for this same fixed partial minor, not an independent complete algorithm.

**Acceptance.** After all required old contacts exist, recompute all old and new capacity counts, then run the unchanged independent oracle on the complete induced partial source graph. Record any new-owner capacity failure, overlap, disconnected chain or missing old contact. This instrument adds no capacity-growth or pruning operator; it isolates constrained contact routing. The first tree passing every check before the deadline is the diagnostic witness and ends that prefix's probe. Save its complete chain and receipt, without supplying it to any future constructor.

```text
for each of the three frozen prefixes:
    start a 5-second monotonic interval
    decode and independently verify the saved entry; build allowances/components
    enumerate roots by the fixed rule above
    for each root until the interval expires:
        grow one shared tree by quota-admissible path extensions
        record failed extensions or capacity/independent-validation failures
        if all checks pass before the deadline:
            save the diagnostic witness and stop this prefix
    record exhausted-root or deadline outcome, including every interrupted stage
```

## Cost, falsifier and self-critique

There are exactly three probes, at most five seconds each, including prefix setup and witness validation. Cold interpreter/module startup and final output are separately measured. Check the monotonic deadline throughout graph, root and path work; an oracle call that finishes after the deadline is charged and recorded as late, without a timely witness. No root/path-count cap, earlier-chain movement, exact/IP solve, global construction, MM call, busclique call or witness access is allowed. Reuse the isolated candidate-only packet and audited oracle; add only checks specific to path consumption, label discard and interrupted validation.

A timely independently valid tree is the decisive cheap falsifier of the claim that these fixed-chain quotas make insertion impossible. The converse is asymmetric: a finite heuristic search cannot falsify the existence of every possible route. If all three probes fail to produce a timely witness, the practical claim that this routing rule resolves the observed failures cheaply is unsupported; do not implement a routing-only constructor on that evidence. Report the unresolved cause and return to coherent construction design rather than adding successive local diagnostic variants.

Self-critique: greedy contact order and one path label per site can discard feasible resource allocations; shortest paths need not give the new owner enough future boundary capacity; and these are exposed prefixes. The instrument can succeed with chains that are longer than useful in a complete embedding. One witness establishes local feasibility only, and even three witnesses do not establish improved ACL, success rate or runtime for complete constructors.

## Immediate follow-through after a positive result

After root reviews a timely positive witness, move the mechanism into one complete constructor and one small frozen screen, with no intervening routing-diagnostic sequence. Use one evolving partial minor with contact routing informed by old quota consumption; preserve C014's source-order, publication, retraction and capacity rules initially. The diagnostic states and discovered chains never initialize that constructor. Full construction uses its global wall budget, not a new five-second per-owner cap.

The first screen should cover the three observed ER/BA failures, a WS input, grid, the hidden singleton control, and fresh SBM and planar development instances: eight structures, seed 0, ideal Z12, candidate/A061/MM tested separately with paired timing on one host. Freeze exact generated inputs and allocations before execution; independently validate every embedding and charge every failure. Preserve the earlier BA160/planar160 deadline failures and SBM/WS Q regressions as unresolved obligations outside any narrower screen. Continuation requires complete-constructor success improvement beyond one source family and evidence on fresh instances, with per-class ACL and all runtime/variance tradeoffs reported. No promotion follows from aggregate Q, one optimal control, local witnesses or this one-seed screen.
