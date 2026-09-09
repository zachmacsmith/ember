# A063: original-contact whole-chain reconstruction

2026-09-09 UTC. Before-code contract; no implementation, diagnostic or candidate
call is authorized by this note. This follows the [strategic decision](../strategic_review_20260909.md).
Root owns the fresh panel, registry, source freeze and remote lifecycle.

**Hypothesis.** Rebuilding a complete chain while releasing neighboring branches
that serve only its contact can co-locate original-neighbor contacts and reduce
actual Q. Apply this to all owners, including retained-core owners, after the
unchanged A061 constructor has completed. This addresses a shared possible
contact-placement restriction in grid/honeycomb, BA and lifted wheel/LFR owners;
it does not attribute their gaps to fill or recover incomplete construction.
The [fill projection](../strategic_fill_diagnosis_results.md) and [static maps](../tracks/c_a061_static_map_results.md)
are descriptive support, not causal proof. This overlaps established MM operations
and B's proposed mechanism. A tests valid-state improvement of the retained
constructor; B tests fresh feasibility/construction. Neither is independent
novelty evidence for the underlying boundary operation.

**Files/API.** New isolated `factored/mobile_boundary_reconstruction.py` provides
`mobile_boundary_reconstruction(embedding, source_adj, target_adj, *, seed,
deadline, validator) -> (mapping, diagnostics)`; new
`factored/mobile_boundary_construction.py` provides
`mobile_boundary_embed(source, target, *, seed=0, timeout=60., deadline=None)`.
The helper uses the standard library and supplied original adjacency/validator.
The wrapper eagerly imports the unchanged A061 `branched_path_embed` and the
existing original-graph validator. Existing A053/A061/native/branch files and
all current defaults remain unchanged. No external embedder, constructor fallback,
saved map, source family/ID, coordinates or witness map enters the new operator.
Labels are preserved; traversal/ties use ranks from supplied source/target order.

The wrapper calls A061 exactly once under
`D=min(caller_deadline, wrapper_start+timeout)`. A failed/late base supplies no
operator entry; preserve its complete status, error and partial diagnostics.
A successful base supplies the sole incumbent, already valid under original
edges. The existing branch stage is neither repeated nor modified afterward.
Private proposals are not separate complete constructor outputs.

**State and reciprocal contact protection.** Normalize adjacency and source/target
ranks once. Maintain one private incumbent bundle: chains, physical owner array,
Q, and one actual oriented physical coupler witness per original source edge.
Choose the lexicographically first target-rank endpoint pair for each edge,
oriented by source rank. Build contacts by one occupied-target-adjacency scan
and source-edge lookups, not repeated chain scans per logical neighbor. Initial
normalization, copying, ownership/contact reconstruction and validation are timed.
Invalid input/internal inconsistency is an error, never a normal failed proposal.

For a query on owner u, let C be the immutable current bundle. Every other edge's
recorded physical witness stays protected while neighboring chains are trimmed.
In particular, if two neighbors v, w of u are adjacent logically, protect both
ends of the **same** v–w witness. Independently choosing endpoints touching each
other's old chains would be unsound: simultaneous trimming could delete both
opposite supports. Shared witness pairs prevent that error.

For each v in N(u), choose a deterministic BFS spanning tree of C[v], traversing
actual target edges in the once-seeded target order. Protected terminals are v's
endpoints of all its recorded original-edge witnesses except v–u. Root at the
first protected site in target-rank order; if there are none, protect the first
site of C[v] instead. Repeatedly remove unprotected tree leaves in target-rank
order. The remaining R[v] is nonempty and connected, and preserves all protected
endpoints. Removed sites P[v] are the contact-only stems for this contract:
branches unnecessary for the retained witness obligations, not necessarily sites
having literally no redundant coupler to another source neighbor. A chain with
induced cycles uses this spanning tree; no assumption that its full induced
physical graph is a tree is made.

Release all of C[u] and P[v] privately. Outside owners are fixed; R[v] is fixed
for this query. The free domain F is originally unoccupied target sites plus
those released sites. Other owners cannot grow, overlap or lose required contacts.
Thus donor nonemptiness/connectivity and all contacts not incident to u are
preserved before reconstruction. Stem sites can be reassigned to u or remain
unused; this is the boundary redistribution in this first variant. There is no
second neighbor-growth or ownership-split search bundled into it.

**All-neighbor root search and shared paths.** For each v, define B[v] as free
sites adjacent through actual target edges to R[v]. Multi-source BFS in F gives
distance d[v, q] from each free q to B[v], with boundary distance zero. Process
every neighbor and all reachable sites, accumulating root distance sums/maxima
and reach counts. Keep only one neighbor distance array at a time. Eligible
roots reach every B[v]; rank them by `(sum distance, max distance, seeded target
rank)`. Complete this ranking before examining roots. The sum is a placement
proxy, not a lower bound on the size of a shared tree or an admission objective.
No root-prefix or graph-region cap is added.

Every old site of C[u] must be an eligible root after a completed correct setup:
old C[u] is connected and released; each old contact either reaches R[v] directly
or via released sites of its connected former chain. A missing old root is an
implementation/identity error, not an infeasibility finding. This establishes
connectivity reach only, not a strictly smaller constructed tree.

For each ranked root q, begin T={q}. Mark every neighbor already contacted by T.
Until all are contacted, run multi-source BFS from the entire current T through
F. Select a shortest extension ending adjacent to any unmet R[v]; complete the
first successful distance layer and break ties by seeded source-neighbor rank,
then seeded target endpoint rank. BFS predecessor ties use seeded target order.
Append its path to T. Recount contacts of new sites, so one extension can satisfy
several obligations. Start the next BFS from the expanded tree, allowing shared
branches rather than independent root-to-neighbor arms. Existing T is traversable,
not an obstacle. No owner-order permutation, exact Steiner solve or IP is used.

After all contacts exist, select canonical actual u–v witness pairs, protect
their u endpoints and prune unprotected leaves of T's construction tree; an
isolated u retains one site. Construct C' with u=T, neighbors=R[v], all others
unchanged. The proposed total is
`Q'=Q-|C[u]|-sum(|C[v]|-|R[v]|)+|T|`.
Recount it from C' before admission. Neighbor savings are not omitted, and moving
a stem between owners is not counted as a saving by itself. A cheap exact bound
`1+sum(|R[v]|) >= |C[u]|+sum(|C[v]|)` can skip a query, since this fixed query
cannot then strictly reduce Q. This bound is not a search-work limit.

Only Q'<Q candidates reach the admission certificate. Check the changed ownership
partition, connected/nonempty chains, frozen equality, original contacts and the
existing full original-graph validator. Prepare the complete new owner/witness
bundle, actual-Q reconciliation and receipt privately. After a final stage-clock
check, publish the entire bundle atomically. First fully certified strict-Q root
wins this visit; equal-Q/worse candidates never change the incumbent. Roots that
were not visited remain unknown. A failed certificate is an internal error,
not a routine rejection that conceals an unsound proposal.

**Schedule.** Seed source and target tie ranks once per operator call, using
separate deterministic RNG instances/namespaces. At each pass start, order all
owners by decreasing current chain size, then seeded source rank. Visit every
owner in that fixed pass order unless the deadline stops the stage. Failed visits
leave all incumbent indexes unchanged. A commit refreshes the shared physical
witness bundle; the next query reads the new incumbent. Repeat only if the
completed pass made a strict-Q commit. Stop after the first completed no-gain
pass or the deadline. There is no active pass, root, owner-degree or operation
cap; strict-Q commits are finite. This is not exhaustive neighborhood optimality:
terminal choices, BFS ties, shared-path construction and first-improvement order
remain heuristic restrictions.

```text
D = common absolute wrapper deadline
base = unchanged A061(source, target, original D)  # one call
if base is not timely SUCCESS: preserve failure; stop
current = base.embedding
S = D - min(1 second, 0.05 * requested timeout)
if now < S:
    copy/validate/index current under S
    repeat:
        order = all owners sorted by (-current length, seeded rank)
        pass_changed = false
        for u in order:
            pin reciprocal witnesses except u's incidences
            trim neighbor spanning trees; privately release u and stems
            complete all-neighbor BFS root ranking
            for root in rank order:
                build one shared tree; prune contact-preserving leaves
                if actual total Q decreases:
                    certify/stage complete bundle and receipt under S
                    atomically adopt; pass_changed = true; break
        until complete pass has no commit
on cooperative stop: discard unfinished proposal, retain current
validate/materialize returned current under original D
publish SUCCESS only on valid, timely outer return
```

**Wall and failure contract.** The new stage may use all remaining original
allowance except `min(1s, 5% of requested timeout)` reserved for finalization: 1s
in the approved 60s screen. This explicit reserve is an engineering allocation,
not an empirically guaranteed validation bound or competitive runtime claim.
It replaces neither A061's existing internal policy nor its original deadline.
There is no additional new 1s stage cap and no uncalibrated work-denial predicate.

Clock checks occur at query/pass boundaries, BFS pops, within long adjacency,
copying and pruning loops, before/after bulk sorts, and immediately before
publication. Incomplete root generation/ranking selects nothing. Incomplete
reconstruction, certification, index refresh or receipt preparation publishes
nothing. Earlier admitted improvements survive a later cooperative stop; the
unchanged A061 base is also a certified fallback within this single trajectory.
Before a complete private copy exists, a deadline return may alias the untouched
full input mapping, explicitly marked `input_copy_complete=false`; a partial
copy is never returned. Final wrapper validation/materialization uses D, without
renewing search. A late outer return is TIMEOUT with no credited embedding.
An internal error surfaces FAILURE and preserves the last valid map diagnostically.
Base failure/partial evidence is retained verbatim. Normal stage deadline stops
can still yield timely valid SUCCESS; they do not prove unvisited moves useless.

**Receipts and cost.** Record base status/Q/wall, stage start/deadline/reserve and
stop phase; complete/incomplete passes and owner visits; eligible/released donor
sites; root-domain/ranking completion and roots examined; BFS searches/pops/edges,
shared sites, completed trees, Q rejections, certificates/admissions; setup,
stem selection, root search, reconstruction, validation, index refresh and
bookkeeping wall/CPU. Work counters are diagnostic named events, not CPU units
or hidden limits. Per-query summaries retain tested counts and best completed
Q, plus interrupted work; no full per-root trace is required. Every commit saves
u, changed-owner before/after sites, Q before/after, chosen root, transfer counts
and admission timestamp. Receipt construction, copying and any hashing are timed
before admission; subsequent worker JSON/disk transport remains in process time,
not falsely reported as solver work. Reuse saved original validators and current
failure schema. Preserve base-Q versus fresh-control differences separately from
new-stage savings; do not claim the added stage speeds an independently timed base.

**Only new-risk checks before the complete screen.**

1. Path a–b–c on hardware 0–1–2–3–4, entry a={0}, b={1,2,3}, c={4}: protect b–c, 
   release b's u-only stem while rebuilding a, obtain independently valid Q3.
   Check total-Q conservation through intermediate reassignment and final saving.
2. Shared-junction helper fixture: target edges 0–1, 1–2, 1–3, 1–4, with fixed neighbor
   singletons at 2, 3, 4. Reconstruction from supplied root 0 must use T={0,1}, with
   the common junction satisfying all three contacts. The public root search
   may choose 1 and obtain the smaller singleton; no general optimum assertion.
3. Neighbor–neighbor reciprocal-witness fixture with two available physical
   couplers: source triangle u, v, w; C[u]={4}, C[v]={0,1}, C[w]={2,3}; target edges
   0–1, 2–3, 0–2, 1–3, 4–0, 4–2. For the u query, retain shared witness (0,2), not the
   incompatible independent endpoints 0 and 3. Also include
   branching/cyclic donor, required articulation protection and singleton donor.
4. No-gain singleton/isolate and an ordinary valid tree: input immutability, 
   deterministic ordering, no acceptance of neutral or larger total Q, and the
   old-root reach invariant after complete stem setup.
5. Fake deadlines during ranking, tree construction, certificate/index staging
   and immediately before commit; preserve an earlier valid improvement, never
   a partial new one. Exercise base failure, no-time skip and late outer return.
6. Real wrapper import under the audited no-external-embedder guard; one A061
   dispatch with unchanged arguments/source, existing original-validator gate,
   and no MM/busclique import or hidden additional constructor.

No saved-final gate or exact local solver is added. Root's [frozen panel](../../../results/codex/transfer-cycle-001/panel.json)
contains 20 structures plus two nested relabelings: 12 fresh cases at n80/n160,
grid/honey/wheel anchors, K100, and four evaluator-hidden feasibility witnesses.
The proposed next execution is exactly those 22 encodings, seed0, A063/A061/freshMM,
60s on hyde06 (66 calls), only after root review/freeze. Candidate code sees no
family or witness metadata; relabelings are not new structures.

**Cheap disproof and continuation.** Completed visits with no strict-Q gain on
fresh structures reject the tested neighborhood as a useful next stage; only
repeating anchor gains is insufficient. Entirely deadline-censored searches
instead expose cost and leave their unvisited alternatives unknown. Record
whether stem mobility occurred, complete lower-Q proposals were admitted, and
where time went. Any actually generated smaller valid map rejected for a
non-time reason contradicts the specified acceptance contract. A minimum proposed
continuation signal is gains on two fresh structures, no lost A061 success and
no aggregate Q/mean-ACL regression on common successful structure/seed pairs;
all per-input/MM regressions and witness misses remain visible. Root freezes the
final screen decision alongside the panel; no outcome-based root/order/allowance
change follows. This signal is exploratory continuation, not replacement of A061
or a claim across all classes.

Self-critique: this is an established MM-like neighborhood added to an already
expensive inherited constructor. Fixed reciprocal terminals can overprotect
shared branches; first-improvement BFS trees can miss compact arrangements;
strict Q forbids neutral preparation. Full-target all-neighbor distances may
dominate Python time, especially for high-degree owners, while the actual base
failures remain unreachable. Original constraints remove obsolete fill demands
from the new stage, not their earlier placement/cost effects. The test must be
allowed to end this direction if fresh complete-output benefit does not justify
its cost; static contact counts alone cannot authorize another repair series.
