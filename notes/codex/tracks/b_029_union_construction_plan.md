# B029: local construction using actual shared-site cost

Before code, 2026-09-09. Plan only; root reviews implementation and experiment
contracts separately. B028 remains rejected. This proposal uses one evolving
embedding state and no MM/busclique code, maps, initialization or output selection.

## Hypothesis and the failure being addressed

The [completed B028 diagnostic](b_028_failure_diagnostic_results.md) establishes a
**proposal-ranking failure**: all four states contain better constructed chains
within the captured route representation and fixed other-owner chains. It also
establishes a **computational failure of exhaustive diagnosis**: complete root
reconstruction took 171.171 s, 71.3% of worker time. Contact movement was never
tested; its absence is not established as the cause. Finishing the pending route
gave two score ties, one regression and one small overlap improvement.

Hypothesis: score the actual chain produced after path attachment and trimming,
then move its root locally through Zephyr couplers. Evaluating only that owner's
sites can make these choices affordable. An explicit overlap priority prevents
this new root-selection operator from preferring the observed fresh-ER100
overlap regression solely for a lower priced potential. Whether the resulting
complete construction converges remains a separate experimental question.

## One constructor and an explicit objective

Retain B028's empty start, source ordering, neighbor trimming, negotiated site
prices, feasibility sweeps, quality phase and recurrence accounting. Replace
the root-selection/materialization portion of each visit. No saved diagnostic
state enters a complete constructor. Use actual target adjacency, including
Zephyr couplers; no source labels, classes, instance IDs or canned placements
affect policy.

For the owner u being rebuilt, remove u and trim its already placed neighbors
once, preserving their other source-edge witnesses. Call this fixed residual
state R, with occupancy k(q). For any constructed connected owner chain C:

```
Q(C)   = Q(R)   + |C|
O(C)   = O(R)   + sum(1[k(q) > 0] for q in C)
Phi(C) = Phi(R) + sum(1 + price(q)*k(q) for q in C)
```

Overlap means **excess memberships**, O=sum(max(k-1,0)); it is not overlapping
pairs. Adding u to a site with residual k=3 changes O from 2 to 3, hence delta O=1,
while its pair-price contribution changes from 3p to 6p, hence delta Phi=1+3p.
The same formulas hold for every k>=1, and k=0 adds no overlap. Specific checks
must cover k>=3, not only pairwise collisions.
These are exact membership/overlap/price identities. The diagnostic checked the Phi identity with unchanged residual
chains throughout every completed current-root proposal. Score **after** the
same contact selection and final trimming used by the materialized proposal.

During feasibility, rank roots lexicographically by **(O, Phi, Q)**. During the
disjoint quality phase, rank by **Q**. Target rank breaks ties deterministically
but does not permit a step with an unchanged objective. Phi is an adaptive
congestion cost, not the number of overlaps; this distinction is intentional.
The final research objective is success, then ACL/variability/runtime per class.

Keep B028's visit acceptance: a completed feasibility proposal may increase
overlap relative to the *entry* embedding when the fixed trimmed residual and
local root options cannot do better. This preserves negotiation rather than
imposing global monotone descent. Root refinement itself cannot worsen O
relative to its initial min-J root. It may lengthen chains to reduce O, or raise
Phi when O decreases; all such changes must be recorded. This is a coordinated
ranking redesign, not an assertion that either scalar objective solves embedding.

## Root movement and inexpensive evaluation

Run the existing standalone compiled routing once for the fixed residual.
Its min-J root is an initial anchor only. Preserve the finalized distance and
parent arrays and settled masks. Let S be the roots with finalized labels for
every required neighbor. **J is neither a bound nor a pruning criterion.**

Evaluate the anchor, then its immediate hardware neighbors in S. Move to the
best strict objective improvement and repeat until no adjacent improvement
exists. This is a specified physical move neighborhood, not a top-K root list.
Memoize scores within the visit because prices, residual chains and route maps
are fixed. At each explored root, record physical neighbors excluded because
at least one required label is unsettled, including the missing source-neighbor
labels. Report whether the terminal local optimum has any such exclusions:
an optimum only on the captured domain must not be called a geometric trap.
No independent starts, full-target root scan, plateau enumeration or
selection among complete algorithms occurs. Every trial has the same source
owner and residual state. The global wall deadline remains binding; there is
no new visit counter cap or per-query time gate.

The evaluator operates on compact scratch arrays for **C alone**. Reproduce the
existing neighbor order, shared-path attachment, contact choice and final trim;
count each physical site once. Precompute residual contact membership once per
visit. The implementation uses a degree-by-target array of contact endpoints,
supporting degree greater than 64 with no hidden source-degree restriction.
A parent path joins the existing connected set, and
the final witnessed trim remains connected by construction. Use rank-consistent
adjacency/contact traversal and the existing positive-weight arithmetic guard.
If integer bounds fail, the same evaluator with Python integers is a semantic
fallback, not a different embedding algorithm.

Retain native route arrays instead of copying them into Python maps merely to
evaluate roots. The isolated B029 adapter may expose the existing kernel's
finalized arrays without changing its relaxation, ties or stopping rule. This
requires its own pinned source copy or private adapter; do not edit the shared
B028 implementation or harness. Scratch allocation, compilation, imports,
packing and every trial are charged, including the first call; no warmup or JIT
cache is excluded.

After local descent, recover C and its incident witnesses once, construct one
full candidate state, recount its scores and run the existing selected-owner
certificate before publication. Assert equality with the inexpensive evaluator's
chain, witnesses and objective. A mismatch is a recorded error, never silent
publication or an unreported fallback. Unselected roots require no full state
copies or general certificate. On interruption, preserve the entry embedding
and record incomplete work; do not claim the uncommitted trial as progress.

```
visit(u):
    R = fixed neighbor trims, excluding u
    maps, anchor = existing standalone routing(R)
    if no complete anchor: record no proposal; return
    evaluate(q):
        attach paths for u using fixed maps and R
        select actual incident contacts; trim u's resulting chain
        return exact local (O, Phi, Q), chain and incident witnesses
    root = anchor; score[root] = evaluate(root).objective
    loop:
        evaluate uncached physical neighbors of root with complete labels
        next = best strict improvement, using fixed target rank for ties
        if none: break
        root = next
    materialize only selected root; verify with existing certificate
    apply existing visit acceptance; record first valid and quality progress
```

No-neighbor initialization and disconnected source components retain the
inherited general placement rule. Quality routing continues to forbid occupied
residual sites. Partial-source initialization requires contacts only to already
placed neighbors, exactly as in the inherited constructor.

## One self-critique

Favorable roots may require uphill or equal-cost physical moves. A one-coupler
descent can stop before reaching them; fewer state copies do not fix that
neighborhood limitation. The captured root set can itself be incomplete. Fresh
ER100 has no observed improvement under the proposed (O, Phi, Q) key despite
its lower-Phi alternatives: this objective choice, rather than root adjacency,
can explain a tie there. Neither local optimality nor failed descent proves
that no good embedding exists.

Overlap priority may build long chains and leave quality refinement unable to
recover ACL. It may also suppress useful weighted-congestion redistribution;
keeping global visit acceptance and price updates does not guarantee escape.
Reproducing attachment/trim in compact form adds risks around shared contacts,
roots removed by trimming, settled masks, high source degree and tie order.
Cold compilation can negate cheaper trial evaluation. These are reasons for a
bounded falsifier and complete-constructor screen, not grounds for another long
sequence of proxy-only repairs.

## Checks and cheap falsifier after approval

Reuse the frozen diagnostic checker, original oracle and current harness. Add
only checks for the new evaluator/array/publication risks:

1. Compare inexpensive evaluation with the existing **saved** original-root,
   first-better, best-Phi and best-O chain/witness deltas on each of the four
   candidate-only states. Check original-root equality and exact Q/O/Phi,
   including higher-order occupancy; no genuine routing or constructor is
   needed for these saved-map checks. Use exact root identity as well as state
   hash because distinct roots can yield identical states.
2. Tiny targeted controls cover one site meeting multiple source contacts,
   reused path segments, a root removed by final trimming, degree above 64,
   rank ties and a root missing one settled label. Verify rejected/unavailable
   roots cannot consume unfinalized array entries. Reuse independent connectivity
   and contact checks; do not add a broad exhaustive suite.
3. Interrupt at trial evaluation, selected materialization and prepublication.
   Require immutable entry chains/witnesses/prices/route arrays and a preserved
   failure receipt. Independently validate a published candidate through the
   original harness; never equate an overlapping partial state with a minor.

Then one frozen, fresh-process packet uses those four saved candidate states and
saved route maps. Run the specified local descent, without an exhaustive root
scan, under the same 60 s inclusive worker allowance. Record every root visited,
local stopping reason, O/Phi/Q versus anchor and entry, cold cost, cached hits,
and useful proposals lost to the deadline. No hidden/MM witness or constructor
call is permitted in this packet.

The low-cost assumption is contradicted if a completed one-neighbor pass costs
as much as the measured warm routing it supplements (approximately 0.782,
0.549, 1.389 and 1.165 s for these four states), or if cold compilation prevents
meaningful descent within the allowance. These are measured comparisons, not
new active algorithm limits. If inexpensive evaluation is correct and fast but
descent finds no improvement despite a saved root better under **B029's key**,
the specified neighborhood is the immediate problem. A lower-Phi witness with
worse O does not meet that condition. If descent changes O/Phi/Q but complete
construction still fails, revisit acceptance/price dynamics or representation;
do not extend descent solely because local scores improved.

## Small complete-constructor screen if the falsifier supports it

Promptly use the six original B028 inputs plus three Transfer003 instances:
g0001 (ER80), g0005 (SBM80), g0013 (grid128), g0017 (singleton control80),
g0101 (ER100), g0102 (BA100), and g0201/g0202/g0203 (WS100/SBM100/planar100).
This retains both prior B028 successes and all four failures, and adds three
different new development structures. Panel SHA is
`83e16a8b3144f9e81ab4811b4bfe5fb2e869ddec49b11570f450572d72599dec`.
Freshness is measured at each experiment freeze; other tracks may expose these
instances before B029. None belongs to the untouched confirmation set.

The exact arms and call count require root's separate freeze. The intended
comparators are B029, its **fixed-anchor ablation**, B028, retained control A061,
promising challenger A064, and pinned MM, on nine inputs at seed 0 and 60 s per
fresh worker (54 calls if all six arms are retained). A061 remains the retained
control; A064 has not been promoted. The ablation uses identical compact evaluation/materialization but
does not move the min-J anchor, separating acceleration from root refinement.
Its completed fixed-root proposals must match B028; deadline differences need
not preserve trajectories. These arms are evaluated separately and never
combined. Root freezes exact descriptors, source identities and task vector;
use one available cluster host with paired timing and recorded load.

Reuse original-graph validation and full failure/process accounting. Report
success, Q/ACL, within-chain variability, first-valid time, price/sweep progress,
root-refinement time and every O/Q regression per input. Seed variance remains
unknown. A broader B screen needs retained old successes and recovered success
over B028 in at least two source families, including one of the new structures;
otherwise the fixed policy is rejected. Also inspect Q and actual time against
A061/A064/MM before allocating broader experiments. This is an exploratory
continuation rule, not a claim of class superiority or a universal runtime gate.
An informative failure may justify a separately frozen mechanism test, with its
specific cause stated first; it does not justify automatically continuing local
repairs. No paper or promotion follows from this screen alone.

## Transfer003 adapter review supporting this input proposal

Read-only review compared full `transfer_panel003.py` / `transfer_verify003.py`
with 002, the pinned shared generator/sanitizer and both Transfer003 notes.
No concrete blocker found. Copy precedence selects the 22 Transfer001 encodings
and then the two 002-only encodings; parent/prior-kind checks retain both
relabelings. Seed namespaces, IDs, parameters and generation watchdogs match
the protocol. Only sanitized graph records go to candidates; originals and
witnesses remain evaluator-private. The verifier extends the exposed index
with Transfer002 and preserves match/unknown results. Its PASS means identity
checks completed; the result note separately reports no fresh matches/unknowns.
No adapter was executed and no private witness was read for this review.
