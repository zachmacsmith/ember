# First bounded induced-star implementation

Saved before implementation on 2026-09-08. This fixes the choices left open in
the [initial hypothesis](induced_star_relocation_spec.md), using the independent
[mathematical/prior-art review](induced_star_relocation_review.md) and
[integration review](induced_star_integration_review.md). Those reviews and
their limitations remain part of this specification.

## Fixed policy

Implement the integration review's rule without per-family exceptions: attach
one attempt to a failed ordinary group visit; use its first vertex as center,
at most once per center per pass; keep ordinary group order and total group
count unchanged. An accepted ordinary move, including an equal-Q contact move,
suppresses the attached attempt. No new center queue or extra sweep is added.
The current `singleton_policy='legacy'` stays fixed. The new optional star policy
and direct-singleton policy are mutually exclusive in the first integration.

Use the exact structural leaf selection in the integration review: center
degree between two and the actual target maximum degree; eligible neighboring
leaves with degree at most that maximum; decreasing current chain excess,
increasing logical degree, then stable logical rank; greedily retain mutually
nonadjacent leaves. Require at least two leaves and strictly positive total
selected excess above singleton size. This allows 3–21 vertices on Z12.
The routine searches only that one selected block, not all independent subsets.

Use the review's deterministic necessary root superset: the cheapest estimated
one-hop neighborhood of a frozen center-neighbor chain or two-hop neighborhood
of a frozen leaf-neighbor chain, with the specified hop/rank tie breaks. With
no frozen obligations, enumerate the target's stable rank order. Fully eligible
intermediates may prune the two-hop leaf walk. Record all duplicate processing
and do not replace this rule with a favorable-region or witness-specific order.

Compute available/frozen-owner contacts lazily per physical site within the
current immutable block query, then cache selected-vertex eligibility masks.
Eligibility includes actual site degree, availability after releasing the block,
and every frozen logical contact. Build leaf domains from actual neighbors of
the proposed center. A plain augmenting-path matching with most-constrained
leaf order and stable physical-site order returns the first covering matching.
Use separate logical and physical identities internally to avoid label collision.

Every proposed selected chain is a singleton. Certify the entire selected
replacement and exact old/new incident-contact redundancy before acceptance;
all constraints touching the block must be checked against original adjacency.
Accept only strict qubit reduction. The unchanged outside embedding supplies
the rest of the validity argument. Never accept a partial matching, partially
scored proposal, or uncertified map. No weighted matching or best-root selection
is included: all complete proposals for this fixed block have the same Q.

## Fixed work and cache rules

Use an auxiliary ceiling `max_expansions // 20`, shared with the existing global
limit, and a **2,048-unit per-query ceiling** for selection, obligation building,
root generation, eligibility, matching, scoring and certificate work. These are
engineering choices fixed before observing implementation results. Owner setup
and refresh are outside the query ceiling, but remain inside the same active
visit, auxiliary and global limits. No extra time or group budget is granted.

Use the integration review's explicit units: source/chain record, occupied
qubit, physical adjacency scan, selected-vertex eligibility check, or matching
edge examination. Repeated work, unsuccessful paths, duplicates, scoring and
certificate checks all consume allowance. A physical adjacency scan can inspect
up to the target maximum degree; these units are not CPU instruction counts.
Record time and actual stage counters alongside units. Check deadline/work
inside root walks and augmenting paths. If a necessary stage cannot finish,
return no proposal with the incumbent unchanged and distinguish truncation
from an exhaustive failure for this one block.

Use a dedicated lazy owner-only cache; do not invoke `SingletonSearch` or its
queue. The cache refers to the exact current immutable incumbent object.
After every accepted ordinary or matching move, invalidate it, remove every old
selected owner, add all new selected owners, and publish the new identity only
when the update completes. An incomplete refresh disables matching for that
polish call but retains the already accepted valid embedding. A stale identity
also disables the cache, rather than silently rebuilding from an unknown state.
Query-local eligibility masks never survive a committed move.

## Implementation sequence and ownership

First implement only a new internal module
`algorithms/factored/induced_star_relocation.py`, with its bounded selection,
owner cache, query, matching and certificate operations, and focused tests.
Pass the existing context and a budget adapter into the operation; no constructor,
external embedder, saved competing embedding, or graph-family metadata is input.
Do not edit the native or contact scheduler during this core step.

Then root and an independent reviewer check the core against direct injective
assignment oracles, budgets and actual-graph validators. Only after that review
integrate the fixed scheduler above as one optional policy in the existing
contact search, with the off path retaining current behavior and diagnostics.
Before any full pipeline call, freeze the separately specified037 cumulative
ablation. The initial saved-incumbent runner proposal was superseded before
execution by the existing frozen pilot's full-pipeline comparison, which provides
stronger evidence about construction/refinement interactions without a new
controller implementation. Core review still precedes integration and freezing.
Every input and all zero-gain cases remain included; no method is selected per
input. The numeric policy and work limits are unchanged by this planning revision.

## Self-critique before code

The 2,048-unit query cap can truncate eligibility or matching before a useful
root, especially for larger blocks. Owner setup can consume much of a visit
or the auxiliary budget. An ordinary failed visit may leave no allowance at all.
Conversely, loosening every restriction would recreate the coverage cost seen
in033. Keep these settings fixed for the first diagnostic and expose exactly
where work ends. No success probability or useful-root coverage is guaranteed.

The scheduling avoids inserted zero-excess visits but still consumes global
work and changes trajectories after a reduction. Successful equal-Q ordinary
moves suppress matching attempts; one greedy subset can be infeasible even
when a smaller subset works. A final benchmark can regress despite valid local
reductions. Isolated savings and matching counts are not comparative success.

The singleton-center restriction cannot improve a chain whose logical degree
exceeds the target maximum degree, and cannot alone solve all remaining graph
classes. It is a bounded component investigation within the unchanged broader
goal. A future connected center-chain extension would need its own design,
critique and evidence; no such extension is hidden in this first implementation.

Matching and the domain filter overlap directly with Solnon's LAD. The fixed
Z12 witness establishes only that this restricted complete search can find a
smaller result than one bounded generic proposal, not that the mechanism is
new or improves a graph family. Novelty and cumulative usefulness remain open.

## Required checks before integration

Check the fixed Z12 witness (8→5) and the existing generic result (8→7) through
original-edge validation. Compare complete matching results to direct injective
assignments on independently generated tiny graphs with explicit budgets large
enough to finish. Include unmatchable Hall subsets, no external obligations,
frozen occupancy, selected ownership transfers, extra physical leaf-leaf edges,
forbidden logical leaf-leaf edges, heterogeneous label types and degree limits.
Test every interruption stage, incomplete cache setup/refresh, stale identity,
and an ordinary accepted move followed by a matching query. Independently
recompute qubits and contact deltas. No source mutation on any failed query.

Status: core implementation authorized by root after this saved specification;
no implementation or new solver result existed when it was written.
