# Isolated ownership-exchange proposal: implementation specification

2026-09-08. Design only. This specifies the hypothesis in
[the mechanism review](research_next_mechanism_review.md) and incorporates
[the prior-art review](ownership_exchange_prior_art.md) and root's corrections.
It authorizes no implementation or corpus diagnostic. Transfers, swaps and
temporary contact deficits are established methods. A useful contribution
would require evidence beyond those ingredients.

## API and ownership of state

Proposed internal API:

```text
ownership_exchange(embedding, source_adj, target_adj, seed_groups,
                   *, budget, deadline=None) -> (candidate_or_none, info)
```

The inputs are one stable valid minor, stable simple undirected loopless source
and target adjacency mappings, and a finite, caller-supplied ordered sequence
of initial groups. `seed_groups` and its groups are ordinary lists or tuples,
stable for the call; generators, callbacks and custom lazy containers are not
accepted. Each inspected group must be nonempty and contain distinct source
vertices. Source/target labels are ordinary Python integers, excluding
booleans; they need not be consecutive. Chains are nonempty lists. Neighbor
collections must be reiterable, not one-use generators. No graph-family data,
graph identifiers, constructor, competitor output, filename or saved-embedding
loader is an API argument. The caller must supply original adjacency, not a
restricted graph that silently omits boundary obligations.

`budget` is a caller-owned finite live allowance exposing `limit`, `expansions`
and `pop()`. Successful `pop()` consumes one unit; failure consumes none. It may
be an adapter sharing a larger/global allowance. Counters cannot be reset by
this routine, and the budget is not concurrently used by another operation.
Reject malformed scalar limits/deadlines; zero remaining work is an ordinary
interruption. Use the earlier of the explicit absolute `perf_counter` deadline
and any deadline exposed by the budget. No relative timeout or renewed allowance
exists. Check that deadline before each charged operation and before return of
a candidate, even if the adapter also checks it.

The first API has **local-only state**. Build a private entry copy, owner map and
entry-validity certificate once per nonempty query, with all traversal/copy
work charged. Reuse these immutable records across all inspected groups and
seeds of that call. Every group starts from that same entry; no proposal is
accepted internally and no later group receives another group's assignment.
There is no cross-call cache, pass object, refresh protocol or acceptance into
the caller's incumbent. Returning a candidate ends the entire query. This
shares setup without choosing a future pipeline scheduler or relying on an
uncharged/stale cache.
Source/target adjacency can be referenced read-only; do not copy the unused
target graph. Their simple-undirected structure is a caller precondition;
the routine checks source coverage, occupied membership/disjointness,
connectivity and every original source edge before search. Interrupted setup
returns no candidate and `entry_validated=False`, never a partially copied map.
Detected malformed structure returns no candidate with `invalid_input` evidence.
An empty supplied group sequence returns no candidate as `no_groups`, with no
entry copy or validation and `entry_validated=False`; checking the sequence
header/count and producing that result still obey the live budget/deadline.

A candidate is a **full private mapping with private list values**. Outside
lists preserve entry order; selected lists use ascending target labels. Returning
None always leaves all inputs untouched. No “best partial embedding” can escape.
The caller's later validation/publication remains separate from this proposal's
certificate. No native/contact/pilot integration is selected by this document.

## Fixed limits and initial seeds

Retain the untuned limits: eight whole selected chains, 64 incumbent occupied
patch sites, depth eight transfer/swap operations, four retained successors per
expanded state and 256 entered assignments per deletion seed. These are fixed
constants of the first implementation, not per-input parameters. The live work
allowance and deadline can stop any stage earlier.

The ordinary container's declared length G is the explicit finite group bound;
this revision introduces no additional numeric group cap. A later caller must
freeze both that length and the supplied order before its diagnostic or pipeline
call. Preserve the exact supplied group order; do not generate, reorder or
select groups using outcomes. Do not materialize or validate the whole sequence
up front. Inspect the next group only when reached, charging access, validation,
normalization and every failed/ineligible group's work to the same live budget.
No group or seed receives a renewed work allowance or deadline. Duplicate groups
are not silently removed: they are separate ordered, charged occurrences and
their repeated effort is visible in diagnostics. With finite budget B remaining,
at most min(G, B) group accesses can occur, even before their other costs.

Malformed encountered groups (wrong container/label type, unknown vertices,
empty groups or duplicates within a group) stop the query as `invalid_input`.
Well-formed groups that exceed eight vertices or the physical patch constraints
are instead ineligible: record why and proceed to the next supplied group when
work/time remains. Validation uses charged traversal; interruption takes
precedence over any fact that could only be established by an unfinished scan.
Unvisited suffix groups are explicitly uninspected, not assumed valid or useful.

Normalize each reached group into increasing source-label order using charged
work. The initial selected set S is exactly this group. Its patch
P = union(entry[v] for v in S) must contain at most 64 sites and induce a
connected target subgraph. An oversized or disconnected initial group yields
an explicit ineligible group record; do not trim it, choose a different subset
or add connecting free sites. The site cap counts original P, including the deletion
site. It is not a cap of 64 surviving sites plus one deletion.

Consider vertices of the group and their entry qubits in ascending order. Each
candidate seed q must belong to a chain of length at least two; removing it
must leave a nonempty connected chain and lose at least one represented source
edge. Count every attempted seed check. Reject disconnected/empty remainders;
skip already safe deletions as `safe_deletion`, since ordinary deletion closure
owns that operation. Seed enumeration is itself bounded by the original patch's
64 sites and the remaining work/deadline. The routine does not perform closure.

For each eligible `(group_index, q)`, reset seed-local DFS/visited state.
The same q in another group occurrence is a distinct seed, even if the groups
are equal; no visited/depth table is shared across groups or deletion seeds.
Permanently mark q unavailable for the entire seed. Use a distinct deleted-site sentinel, not
source integer zero. A new seed restarts from the unchanged entry, not from any
failed private assignment. When all seeds of a group finish or reach their
individual state caps, proceed to the next supplied group if work/time remains.
Stop the whole call on the first returned certified candidate. Uninspected
groups do not need validation after that return; the diagnostic identifies the
inspected prefix and the returning group/seed occurrence.

## State invariant and atomic admission

Each private state contains the deleted q, S, original patch P, a partition of
P minus q among S, the exact missing-edge set M, depth, and its operation trace.
Owners outside S retain their entry chains. Every chain in S is nonempty and
connected, and every surviving patch site has exactly one owner. No additional
site is unassigned or allocated from free space. Thus global Q is always entry
Q minus one, even when logical contacts are missing.

M contains each unordered source edge incident to S that currently lacks a
physical coupler. Count an edge once even when both endpoints are selected.
Derive contacts from actual adjacency and the current ownership overlay;
the deleted q is absent. Edges wholly outside S remain represented by entry
validity. Missing-contact count is an exploration order, not a secondary score
for published valid embeddings.

Only an actual candidate site's current owner can be admitted. If that donor
is outside S, its chain is still exactly its entry chain. Add that **whole**
chain to S/P only if both caps hold and the enlarged original P is physically
connected. No partial-chain admission, speculative owner queue or empty bridge
is allowed. Admission does not consume search depth; the associated transfer
or swap does. It never occurs as a standalone move. Existing admitted chains
keep their current assignments; do not reset them to their entry locations.

Admission and the proposed operation are staged together. The simplest first
implementation uses a complete private child view for the bounded patch rather
than editing the parent in place. All child copying is charged. Failed checks
or interruption discard that view, including its admitted owner and expanded
P. The parent and original owner map remain intact. DFS retains parent handles;
backtracking restores a handle, not a sequence of partially completed owner
edits. Charge explicit stack/copy/discard bookkeeping. On interruption the
entire private search is abandoned, so no external rollback or unbudgeted graph
reconstruction is needed. Do not continue another seed or group after global
work/time exhaustion. These are the required atomic undo semantics; an implementation
using mutable undo records must prove equivalent interruption behavior.

## Exact successor generation and deterministic selection

At an entered state with nonempty M and depth below eight, choose the smallest
unordered missing source edge (u,v), ordered by integer labels. Consider both
orientations `(receiver, other)` in lexicographic order, retaining only receivers
already in S. At least one exists. An outside endpoint is not moved unless it
is admitted as the donor of an actual operation.

For an orientation (a,b), traverse the current chain of b and its original
target neighbors, collecting **occupied** sites x adjacent to that chain.
Discard q, free sites and sites already owned by a. Deduplicate and order x by
target label. This walk can scan a long frozen chain; every visited qubit,
adjacency entry, duplicate and materialized site is charged. There is no hidden
uncapped boundary scan. If it cannot finish, generation is incomplete.

For each x, let d be its current donor. Stage whole-donor admission when needed,
then generate these descriptors in fixed order:

1. Transfer x from d to a.
2. For each y in a's current chain in increasing target order, simultaneously
   swap ownership of x and y.

Transfers require the donor remainder and receiver addition to be nonempty and
connected. Swaps test both **final** chains simultaneously: singleton-owner
swaps are permitted; no empty intermediate removal is tested. All untouched
chains retain their preceding connectivity. Recompute all incident logical
contacts for the prospective S, including any just lost, and require that this
particular chosen edge is now represented. Other deficits may increase, remain
equal or decrease. A preparatory move that does not restore the chosen edge is
outside this first successor rule, even if it could help a later repair.

Deduplicate descriptors across repeated witnesses/orientations: a transfer key
is `(transfer,x,new_owner)`, and a swap key uses its unordered physical-site pair.
Charge duplicate processing. Rank each completely checked child by:

`(len(M_child), changed_sites, descriptor_kind, descriptor_integer_fields)`.

Here `changed_sites` counts surviving sites whose owner differs from the entry;
q's removal is excluded, and unchanged newly admitted sites contribute zero.
Use transfer before swap for `descriptor_kind`; descriptor fields use the
canonical keys above. No randomness, secondary contact score or source-family
rule breaks ties. Store at most the best four complete children while streaming
the full candidate enumeration. Materialization, comparisons and rejected
children consume work even when not retained.

**Finish the whole generation and ranking step before exploring any child.**
If any domain walk, admission, connectivity/contact check or comparison is
interrupted, discard the incomplete shortlist. Do not treat the best four of
a prefix as the declared top four, and do not publish a feasible child spotted
during unfinished generation. A complete feasible child is considered only
when entered in the ensuing ranked DFS. Record whether a valid-looking child
was discarded by interruption without calling it a returned certificate.

## DFS, repeated states and termination

The seed root has depth zero and counts as the first entered assignment.
Every transfer/swap increases depth by one; admission and backtracking do not.
Check a newly entered depth-eight state for full validity, but do not generate
its successors. Enter retained children in rank order with depth-first search.
The 256 limit counts every admitted DFS entry, including a revisit at improved
depth. Generated children, rejected descriptors and duplicate attempts are
separate counters; they are not hidden behind the entered-state cap.

A signature must include sorted S and the owner of every surviving original
patch site in canonical target order; q and its group occurrence are implicit
in the fresh per-seed table.
Different admitted sets are distinct states even if the full ownership happens
to be equal, because caps and future receiver eligibility differ. Use exact
signature equality, not a digest alone. Retain the smallest depth previously
entered for that signature. Prune a repeat at equal/greater depth; permit one
at smaller depth, which has more remaining exchange steps. Deficit count, the
missing-edge set alone, or a changed-site set alone is not a sufficient key.
No path-dependent ban on returning a qubit to an earlier owner is added.

If the state cap is reached, stop that seed and report truncation, then consider
the next seed only if shared work/time remains. Depth limits and discarded
fifth/later successors are also heuristic truncations. Finishing this restricted
DFS is not proof of no contraction in the patch. Report exhaustion of the
retained search separately from a budget/deadline interruption; never label
either global minor infeasibility.

## Full certificate and charged work

On entering a state with M empty, build a full private candidate. Independently
rebuild its ownership and check original source-key coverage, target membership,
uniqueness, disjointness, nonempty connected chains and **every original source
edge**, without trusting the incremental M. Check exact outside equality,
partition of P minus q, absence of q and total Q = entry Q minus one. Construct
the full diagnostic trace before the final work/deadline publication check.
Interrupted materialization or validation returns None. A mismatch between M
and the full certificate is an internal-error result that stops the query, not
an ordinary rejected move to conceal and search past.

Reserve/consume a publication unit only after this preparation; immediately
check the absolute deadline and return at most this one candidate. No later
state is explored. A successful final reservation may consume the last available
unit: check timeliness without additionally requiring spare work. The caller
separately decides publication into its incumbent.
All candidate lists are private, including unchanged outside lists.

One work unit covers one explicitly performed elementary record operation:
source/chain/group record (including sequence access), qubit membership/copy,
source or target adjacency entry,
connectivity queue step, contact/set update, descriptor, ordering comparison,
ordering item write, signature token, exact-signature comparison token, or
stack transition. Counter updates themselves are bookkeeping, not recursively
charged operations. Charge before doing the operation; failed reservations do
not claim performed work. Use checked loops for scans and a comparison/item-
metered sort rather than hiding arbitrary-length sorting inside one unit.
Signature hashing charges every token; collisions require charged exact token
comparisons, not unverified hash equality. Full validation and copying cannot
call an unmetered graph traversal helper.

Counters distinguish setup, group traversal/validation/normalization, seed tests,
boundary walks, admission, generation, connectivity, contacts, ordering,
signatures, DFS, output copying and final
validation. Their charged total equals the live budget's delta exactly, including
unsuccessful and discarded work. No new per-group or per-seed work allowance is
granted. Group iteration cannot hide generator work or an uncharged whole-input
normalization pass.
Integer/dictionary/container primitives remain cooperative runtime operations,
not CPU-instruction or hard real-time guarantees. Record total and disjoint
stage walls; do not sum nested timings twice. Interpreter return/deallocation
overhead remains in observed wall time and does not justify extra graph scans.

With Q occupied sites, maximum target degree Δ, and n/m source sizes, complete
owner setup and entry checking require O(QΔ+n+m) ordinary scan work, once for
the immutable entry, not multiplied by the number of supplied groups. Group
inspection and normalization add their actually performed charged costs. Selected
connectivity/contact checking costs O(pΔ) with p≤64, but frozen-boundary walks
and candidate enumeration can be much larger. Sorting adds its charged costs.
Each eligible group has at most 64 seeds with at most 256 entered states each,
and at most G supplied groups can be inspected. These bounds do **not**
bound generation to that many descriptors. The external finite allowance is
the ultimate work bound. Memory includes the entry/owner data, one boundary
domain, depth-eight top-four child views and at most 256 entered signatures per
seed. The supplied outer sequence is referenced read-only; no copy of every
group is needed. Any materialized records also require charged allocation/copy
work, including retained per-group diagnostics.

## Required diagnostics and hand-checkable oracles

Save setup completion/entry validity and its once-per-query work; declared group
count, group accesses, completely inspected groups, malformed/ineligible group
records, and the uninspected suffix; seed attempts and rejection reasons;
per-seed q/group index/normalized initial group; entered/generated/retained/
duplicate counts; original patch size and all admissions; depth and state peaks,
observed top-four pruning,
incomplete generation stage, every work category, elapsed walls, stop reason,
and candidate/certificate/publication status. For a returned proposal save full
S/P, old/new Q, exact selected chains and the complete admission/operation trace.
Distinguish `generated_feasible`, `certificate_complete` and `candidate_returned`.
No caller commit count is inferred. Unknown quantities on interruption stay
unknown. Preserve rejected work and failures.

Before any implementation gate, plan independent tiny checks against exhaustive
ownership partitions, original-graph validity and direct transfer/swap enumeration.
These oracles distinguish the mathematical footprint space from the deliberately
restricted DFS. Test multi-qubit frozen neighbors, edges between selected owners,
simultaneous singleton swaps, full donor admission at both size caps, rejected
disconnected patches, admission rollback, attempted q resurrection, repeated
signature with different S/depth, and every budget/deadline prefix. Verify exact
ordering and the full-generation requirement by interrupting after a candidate
that would otherwise succeed. Inputs and retained parents must remain unchanged.
Also verify that setup is charged once across multiple groups; the same q with
different initial S gets a fresh visited table; duplicate group occurrences
retain their supplied positions and consume work; malformed and ineligible
groups have different outcomes; and interruption during lazy group validation
does not inspect the suffix or renew the allowance. An early returned candidate
must leave every later group untouched. All group attempts reference the same
immutable entry and never compose earlier hypothetical moves.

The earlier six-source path witness remains a basic Q−1 certificate; it does
not establish superiority over ordinary reconstruction. Two additional
hand-checkable limits should become explicit fixtures, not favorable-result
selection criteria:

* **Missing free-site escape.** On target path `x–a–b–c–y`, frozen endpoint
  chains are `{x}` and `{y}` and the middle source chain is `{a,b,c}`. A free
  z adjacent to x and y gives a one-site replacement. The occupied-only patch
  cannot obtain it: every occupied interior connection needs a,b,c. This is a
  genuine neighborhood exclusion, not budget failure.
* **Three-owner cycle / unsafe deficit pruning.** Let the source be path
  `L–A–B–C–D–R`. Target edges are `l–a`, `a–q`, `q–b`, `b–c`, `c–d`, `d–r`,
  `a–d`, `d–b`, `c–r`. The entry is `L:{l}, A:{a,q}, B:{b}, C:{c}, D:{d}, R:{r}`.
  Neither A site is individually safe. Delete q: only A–B is missing. Swap B/D
  (owners of b,d): only D–R is missing. Swap D/C (owners of b,c): all contacts
  return with six sites. Each intermediate chain is a singleton. The first
  exchange preserves deficit count while changing the missing edge, so strict
  deficit descent or count-only visited pruning wrongly removes this route.
  The final owners of b,c,d form a three-cycle; forbidding return/continuation
  merely because those owners were already touched is likewise unjustified.

These are hand-derived arbitrary-target examples, not executed Zephyr results.
A separate abstract search-tree test must expose top-four incompleteness: five
ranked children can have four dead ends and a fifth leading to a valid return.
That is a truncation counterexample, not a claim that a particular target graph
realizes the abstract tree. Any physical realization must be independently
validated before reporting it as embedding evidence.

## Explicit self-critique and next authorization boundary

This is a constrained search assembled from established moves. It can miss a
solution because the initial group is unsuitable, the donor cannot fit, a
preparatory move does not restore the chosen edge, the useful child ranks fifth,
or the search needs more depth/sites or temporarily disconnected chains. The
complete-generation rule can consume the allowance after finding a promising
child but before permitting its exploration. Once-per-query setup may still be
expensive, and a poor or repeated early group can consume the whole shared
allowance before later groups are reached. Sharing immutable setup does not
demonstrate useful amortization, and future cross-call reuse would require a
separately reviewed cache/refresh contract. Strict Q−1 improvement does not imply
better final pipeline ACL or useful runtime.

Integration remains open. **Do not require replacing ordinary reconstruction.**
Multiple local moves on one evolving incumbent can satisfy the single-algorithm
constraint; preserving ordinary free-space moves may be necessary. The first
mechanism evidence must compare usefulness against the fixed ordinary proposer,
and bounded elementary-exchange controls are required before a contribution
claim. Root will separately specify all 34 own-control incumbents, independent
deletion closure to remove easy opportunities, and comparison work/time budgets.
This note freezes neither that corpus diagnostic nor a pipeline schedule, and
authorizes no new calls, source changes or implementation.
