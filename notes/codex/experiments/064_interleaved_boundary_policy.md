# A064: interleave fixed boundary queries across owners

2026-09-09 UTC. **Before-code contract; implementation and experiments await
root review.** This is one bounded follow-up to the rejected A063 allocation,
not a promotion of A063 or a change to its saved experiment. See
[A063 results](063_mobile_boundary_results.md).

**Hypothesis and target explanation.** A063 spent 1045.837 of 1072.222 added-stage
seconds on nonimproving completed root reconstructions. Sixteen of 22 calls
reached only their first owner; none completed an owner pass. Interleaving those
same root searches can expose useful alternative owners before the deadline.
This tests computational allocation. It does not change the embedding
representation, contact obligations, move construction or strict-Q acceptance.
Five accepted A063 moves used root rank1, but three used ranks112, 3 and 14;
their deferred alternatives must remain eligible. Increased coverage without
better complete output would contradict the proposed explanation on the screen.

## Fixed mechanisms and files

Create only `factored/interleaved_boundary_reconstruction.py` and
`factored/interleaved_boundary_construction.py`, plus focused checks/evidence.
The helper API is
`interleaved_boundary_reconstruction(embedding, source_adj, target_adj, *, seed=0, deadline, validator)`.
The wrapper API is
`interleaved_boundary_embed(source, target, *, seed=0, timeout=60., deadline=None)`;
proposed public descriptor `native-interleaved-boundary`, empty configuration.
Root owns registration, frozen screen inputs, source capture and remote lifecycle.

Import and call the **unchanged A063** `_Context`, `_Meter` and `_Stop` helpers.
Their normalization/rank setup, `prepare`, `roots`, `reconstruct`, `certify`,
`bundle` and materialization methods retain the exact current source. Preserve
the A063 source/target RNG namespaces, so scheduling is the only search-policy
change. No A063 complete constructor/operator call occurs in A064. The new
wrapper copies the A063 wrapper with only its operator import, public function
name and algorithm/version metadata changed: it calls unchanged A061 once,
with the same seed, timeout and original absolute deadline. A061's existing
internal policy, import guard and original validator remain untouched.

Frozen references before implementation:

- A063 helper `217436640d2ae9e6266b58c8d20aa7fc0333acbe1ca2cc35140688e899876854`.
- A063 wrapper `a45c5c3ebdb9bb53b974ccede0e5d3675f73b71f93d954cb9f7a46c953e50d63`.
- A061 wrapper `3d2f6672e51a450a24a360bb562d9f6c44c325c92130d74c23c4bb505592da9b`.

The unchanged query retains one reciprocal physical witness for each original
source edge, trims donor spanning trees while preserving all other recorded
contacts, releases the focus chain/contact-only stems, ranks all reachable roots
by summed/maximal all-neighbor distance and seeded target rank, and builds shared
paths from the whole growing tree. Final contact-preserving pruning can remove
the starting root. Actual total Q includes donor savings. Retain the exact
`1 + retained_neighbor_sites >= old_focus_and_neighbor_sites` query bound.
Do not add root-distance pruning, a root prefix, source-family/ID dispatch,
source-size rules, work denial, an exact solver, MM or busclique. Hardware input
is the actual ideal Z12 adjacency, without canned embeddings or witness input.

## Exact schedule: rounds and incumbent epochs

An **epoch** is one unchanged incumbent bundle: chains, physical ownership,
reciprocal witnesses, Q and external mapping. Epoch0 is the independently valid
copy of the sole A061 result. Only an admitted strict-Q change starts a new
epoch. A **round** visits every source owner once in one fixed permutation.
These concepts are deliberately separate: a round may span several epochs.

At the start of each round, sort *all* source owners by
`(-len(current.chains[u]), seeded_source_rank[u])`, using the unchanged metered
sort. Freeze this permutation until the round ends. Set its cursor to zero;
each slot is consumed once, in order. A consumed slot for an already closed
owner needs no query work. Its owner can become eligible again only in a later
epoch, and then receives its next remaining slot or a slot in the next round.

For an open owner, lazily prepare a query for the current epoch if none exists.
Apply the exact strict-gain bound before root ranking. A bound-closed owner is
closed only for this epoch. Otherwise complete the unchanged root ranking
before selecting any root, then attempt **one next root** in that ranked list.
If it does not yield an admissible strict-Q reduction, retain the next-root
cursor and all unexamined roots for the owner's next round visit. One root is
the scheduling unit, not an eligibility cap or stopping rule. Do not reconstruct
already completed roots again while the incumbent epoch is unchanged.

If that root yields a certified strict-Q reduction, publish the new incumbent
and advance the epoch. Invalidate **every** prepared query and every bound/
exhaustion closure marker, including those for apparently unrelated owners.
Occupancy, witnesses, reduced donors and root ranking can all change; no stale
result is reused. Keep the current round's permutation and its already advanced
cursor. Thus the next visit is its next owner slot, not a new longest-owner
selection. If the commit occupied the last slot, complete that round and sort
the next round from the new incumbent. The next round may start with that same
owner if its new length requires it, but all its other slots are still visited
before a third visit. No round restart occurs merely because a commit happened.

When a completed root is the last in an unchanged query and yields no strict
gain, mark that owner root-exhausted for the epoch and release its bulky cache.
Never infer root exhaustion from a deadline. Stop with `epoch_exhausted` only
when **all source owners are closed in the same current epoch**, through the
exact bound or completed enumeration of their fixed heuristic roots. An empty
source is vacuously exhausted. A completed round with no commit is insufficient
to stop if any owner still has unexamined roots. Round completion is an allocation
diagnostic, not a neighborhood certificate.

With a fixed incumbent and sufficient time, every unclosed owner's finite root
list advances and eventually exhausts. Strict-Q commits are finite, so unlimited
time also eventually reaches a final exhausted epoch. This proves coverage of
these deterministic queries; it does not prove local optimality over alternative
witnesses, donor trees, shared-path choices or neutral preparations.

```text
current = normalize/copy/validate/index the one timely A061 embedding
epoch = 0; queries = {}; closed = {}; round = 0
while current epoch is not closed for every source owner:
    order = sort(all owners, decreasing current chain length, seeded rank)
    round += 1
    for u in order:                         # never restart this loop on a commit
        check original stage deadline
        if u is closed in epoch: continue
        if u has no query for epoch:
            privately prepare the unchanged reduced donors/free domain
            if unchanged exact strict-gain bound closes query:
                mark u closed for epoch; continue
            privately complete unchanged all-neighbor root ranking
            publish this complete epoch-tagged query cache
        reconstruct query[u]'s next root; increment its completed-root cursor
        if actual total Q decreases:
            privately certify and build the entire candidate bundle
            stage receipt, epoch-close record, empty cache/closures, epoch+1
            final stage-clock check
            atomically adopt all prepared state; keep this round's next slot
            dispose invalidated caches under the same timer
        else if query[u] has exhausted every root:
            mark u closed for epoch; dispose its cache under the same timer
        else:
            park query[u] unchanged until its next owner visit
        if all owners are closed in current epoch: stop
on a cooperative deadline: discard only unfinished private work
run the unchanged final original-graph validation under the outer deadline
```

## Lazy cache and publication contract

Each prepared query has a unique `(epoch, owner)` identity, immutable reduced
neighbor chains, free-site set, boundary contacts, complete ordered root list,
`old_local`, retained-site total, and mutable next-root cursor/cost counters.
It holds no independent complete embedding or alternative constructor result.
The temporary removed-site lists need not be retained after the unchanged
`prepare` output has been counted and its free domain is complete. The shared
`_Context` contains only the unchanged graph/rank/validator machinery. Keep one
global current bundle. Cached queries do not own historical incumbent maps.

A query cache becomes available only after its preparation and ranking finish
under the stage deadline. A paused query contains no partially reconstructed
tree. On resumption, assert its epoch equals the current epoch before using
any domain, terminals or root. A violated identity is an internal error,
not an automatic stale-query repair that conceals a scheduler defect.

Root rejection changes only the query cursor and diagnostics. A smaller-Q tree
goes through the unchanged actual-Q reconciliation, full original certificate,
bundle construction and frozen-owner check. Prepare the receipt and the new
epoch's empty query/closure maps before the final clock check. The epoch-close
record contains scalar progress for invalidated queries, distinguishing the
committing query from deferred untested roots. Stage this record privately;
do not mutate live query statuses into an alleged committed epoch prematurely.
One publication assigns the new incumbent, epoch, empty cache/closures and
prepared receipt/event lists. No fallible validation or preparation occurs after
publication. Disposal of old cache storage occurs afterward in a measured phase;
any deadline stop there retains the already certified new incumbent.

The round permutation/cursor survive publication. Old query metadata remains
as scalar evidence marked closed by the epoch event; diagnostics must not retain
their free sets, root lists, boundary dictionaries or incumbent maps. A commit
is never inferred merely from a staged record. Missing/interrupted preparation,
ranking, reconstruction, certificate, bundle, event preparation or final check
publishes no candidate. Earlier commits remain valid on normal deadline stops.

Retain the A063 wrapper's absolute deadline
`D=min(caller_deadline, wrapper_start+timeout)` and stage boundary
`S=D-min(1 second, 0.05*timeout)`. All setup, caches, scheduling, disposal and
report preparation consume this original allowance; no renewal or extra stage
budget is introduced. A failed or late base does not enter the stage. Internal
errors return FAILURE with no creditable embedding and preserve the last valid
map only diagnostically. The unchanged final gate uses D, and a late outer
return is TIMEOUT even if an earlier incumbent was valid. Preserve the existing
input-alias behavior before a full private copy is complete. No partial map is
published as success.

## Cost and coverage records

Reuse `_Meter` and the existing wrapper's disjoint base/stage/final wall and CPU
costs. Add metered `schedule`, `cache_accounting` and `cache_disposal` work as
needed, without an active work threshold. Reuse audited worker
`peak_rss_bytes` for process peak memory; it includes base/import/runtime cost.
No `tracemalloc`, deep heap traversal or per-root memory snapshot is introduced.

For complete prepared caches, report current/peak numbers of live contexts,
stored root entries (including the consumed list prefix), unexamined roots,
free-site memberships, reduced-neighbor sites, boundary keys and boundary-owner
memberships. These are retained payload counts, not resident bytes or exact
Python heap size. Count and time the accounting itself. Partial-preparation
allocation and transient BFS arrays remain visible through stage cost and
process peak RSS, without being falsely included as fully prepared live caches.
All cache release cost is charged; record how much payload was invalidated by
commits and how much root work/ranking cost was discarded or repeated afterward.

Record round start/end/cursor, epoch start/commit/exhaustion, unique owners
prepared/visited, current-epoch closed counts, and per-query roots prepared,
examined, completed and deferred. Keep query identity, first/last visit and
active visit count; annotate each committed receipt with round, epoch, owner,
accepted root rank and time. Preserve A063 before/after Q, donor changes and
query construction/admission counters. A mixed-epoch round is explicitly marked.

Per-query wall/CPU are **sums of its active visit intervals**. Time parked behind
other owners is not query computation. Store first/last timestamps separately as
elapsed-span evidence, never sum those spans into cost totals. Phase subtotals,
query active intervals and cache-accounting intervals are nested in the stage;
do not add them again to the exclusive wrapper total. Distinguish interruption
from completed no-gain, and invalidation from exhausted search. Track whether
the inherited base Q differs from fresh A063/A061 control bases; do not attribute
such differences to scheduling.

## Focused new-risk checks before the complete screen

1. **Deferred roots and correct exhaustion.** A tiny controlled query fixture
   with multiple owners and at least three roots each checks the exact
   round-robin visit trace, preservation of later roots, no duplicate completed
   `(epoch, owner, root)` work, and no stop after a no-commit first round. Exhaustion
   is reported only after all owners' queries close in the same epoch. Include
   bound-closed and empty-source cases. No corpus or saved MM map is used.
2. **Epoch invalidation and rotation.** Use a tiny original-valid supplied
   embedding with a cached nonimproving owner, followed by a donor-trimming
   commit (the existing P3-in-P5 fixture suffices for this state risk). Check
   the next round slot is preserved, all prior caches/closures become unusable,
   a subsequently revisited owner is prepared against the new physical bundle,
   and the returned embedding passes the existing independent oracle. Also
   cover a last-slot commit, where the next round is sorted from current lengths.
3. **No partial publication on new boundaries.** Inject deadlines during lazy
   cache construction, parked-query resumption, epoch-event staging, immediately
   before publication and during old-cache disposal afterward. Before publication
   retain the old certified incumbent; afterward retain the new one. Inject a
   stale-epoch identity error and preserve it as fatal. Reuse the unchanged
   original validator, clock helpers and failure schema.
4. **Accounting and dependency binding.** Check active query intervals exclude
   parked time; payload current/peak/disposal counts reconcile on a tiny fixture
   without retaining bulky arrays in diagnostics. Verify the new wrapper makes
   one unchanged A061 dispatch and imports the pinned A063 helpers under the
   audited no-external-embedder guard. Cover base failure and late outer return
   with existing stubs; do not rerun the whole A063 correctness suite.

Freeze test/source hashes before the first check execution. Preserve every
attempt, failure and fix. Root reviews the resulting source and only these new
risks before authorizing any panel call.

## Cheap complete-constructor falsifier and decisions

Root has prepared a nine-input development panel, with A064, A063,
fresh A061 and pinned MM separately evaluated, seed0, 60s, empty configs,
paired on the same host. The frozen keys are g0001, g0005, g0008, g0004,
g0012, g0017, g0013, g0101 and g0102: ER80, SBM80, BA160, Watts–Strogatz80,
planar160, singleton-control80, grid128, fresh ER100 and fresh BA100. BA160
tests recorded late-root gains. Wheel is not in this small screen: its late-root
gain and variance regression remain preserved, untested transfer risks requiring
a broader follow-up. The root input proposal originally had eight cases; adding
grid makes nine before any constructor call. This corrects the first policy
draft's inaccurate wheel inclusion, whose bytes are preserved at
`results/codex/interleaved-boundary-checks/before-screen-correction.md`.
Only this screen-description paragraph changes. Root has generated ER100
(`p=.08`, 378 edges) and BA100 (`m=3`, 291 edges) before any candidate call.
The final sanitized input vector, reused cases, method order and generation
records are root-owned frozen screen evidence (36 separate calls). Root's input
review finds the two new graphs distinct within its declared 512-file exposed
index; this bounded comparison is not a global novelty claim. Candidate behavior cannot depend
on their family labels, case identities, private originals or hidden witnesses.

Report final original-valid success, per-input Q/ACL, within-chain variance,
all-attempt solver/CPU/process costs and paired MM/A061/A063 deficits first.
Then use owner coverage, per-owner root ranks, active query cost, invalidated
preparation, time to admitted Q and process memory to distinguish explanations:

- Broader coverage but no complete-output quality benefit on any input rejects
  the proposed quality explanation on this screen. Coverage alone cannot
  authorize another local repair. A measured end-to-end speed improvement at
  unchanged quality is a separate result and must be identified as such.
- Failure to broaden coverage because new-owner ranking, cache operations or
  repeated invalidation consumes the allowance identifies a computation-cost
  limitation of this schedule. Unvisited owners remain unknown; no claim that
  their representation or neighborhood failed follows.
- Additional Q gains on at least two different structures/families, including
  a stalled or fresh intermediate-size case, support one broader complete screen.
  Show whether MM gaps actually close. Any success loss, Q regression or variance
  regression is preserved; none is hidden by total dense-graph gains. Regressions
  block promotion and require their own specific explanation for any follow-up.

Do not introduce a universal 3× gate. The experiment keeps its frozen 60s wall
allocation, while reporting every repeated roughly-order-of-magnitude runtime
deficit. A064 is not promoted over A061 by this screen. Positive evidence must
promptly face the complete development transfer panel, fresh instances/relabelings,
repeated seeds and the later untouched confirmation set. No selection among
independent algorithms' outputs or MM-derived initialization is allowed.

**Self-critique.** Interleaving is fair in root count, not in CPU time. Full
all-neighbor ranking for newly exposed owners may become expensive, and each
commit invalidates already paid-for preparation. Cached domains grow memory
with the number of prepared owners. Changed visit order changes later embeddings;
strict-Q moves do not guarantee a better final map than A063, and the late-root
BA/wheel gains may arrive too late. Fixed terminals, shared-path greediness,
strict-Q acceptance and inherited construction cost remain unresolved. This
policy tests whether reallocating existing useful search improves complete
embeddings; round-robin scheduling itself is not claimed as novel or sufficient
for the final all-class objective.
