# 050: repair only blocked reduced-core insertions

Proposed before implementation, 2026-09-08. This is a bounded extension of
frozen 049, not a promotion of its failed quality/coverage result. No candidate repair has run. The four fixed explanatory frontier probes
described below have completed; their relaxed outputs are inadmissible.

**Hypothesis.** The actual 049 failures are competition for a last free extension
site, not missing geometric contact reach. A cycle insertion must consume site
686, which is also pending owner68's sole free port. The wheel's common singleton
site517 strands pending owner12. Privately releasing a required neighbor or a
competing owner may resolve that contention while retaining all other chains.
These two failures make this an immediate, small reach test. It does not address the seven quality regressions among
049's successful outputs.

## Exact proposed policy

Keep 049's reduction journal, anchors, reverse order, requirement graph `R`,
core construction, ordinary insertion and deadline rules. Change only an
ordinary insertion that returns `None`: attempt one bounded local repair.
Do not trigger repair for an expensive successful insertion. Do not retry
on deadline, global-work exhaustion, invalid output or internal error.

For new `v`, let `S = R[v] ∩ placed` after privately removing this journal
entry's created fill. There are at most three such neighbors. From the current
entry, compute each placed chain's **distinct free boundary** and let `U` be
the union of the boundaries of `S`. A critical competitor is a placed owner
outside `S` with a pending neighbor and exactly one free boundary site `q`,
where `q` lies in `U`. Rank competitors by decreasing number of required
neighbors whose boundary contains `q`, then increasing chain size and fixed
source tie rank. Retain at most two. This identifies port contention using
current structure, without recording special IDs or relaxing a validity rule.

Pool order is those competitors in their ranked order, followed by `S` in
increasing chain size and fixed source rank. Enumerate all nonempty subsets
`K` of this pool with one or two vertices: at most 15 blocks. Order blocks by
`(sum of entry chain sizes in K, |K|, sorted pool ranks in K)`. This favors
smaller releases and resolves equal-cost choices toward the identified
competitors; two short chains precede a long hub. The ranking uses no graph
identity or family. Only owners actually in `K` are movable.

Every block starts from the **same immutable failed-step entry**, with exactly
`K`'s whole chains removed privately. Vertex `v` has no existing chain to
release. Every owner outside `K` is frozen. Insert `v` first, then the released
owners in decreasing number of already placed required neighbors, decreasing
current `R` degree, and increasing fixed source tie rank (the existing B004
reinsertion order). Retain B004's 64 screened roots, four local root branches,
price formula, connected routing, and frozen-aware growth/cut rules. Return
the **first fully rebuilt valid block**, without comparing successful block
outputs. A failed block's state is discarded before considering the next one.

```text
ordinary = insert(v, current, trial R)
if ordinary exists:
    use unchanged 049 released-fill endpoint cleanup and admission
else:
    start one repair allowance, clipped to original deadline/global work
    for K in fixed ordered one/two-owner subsets:
        private = current with whole K chains absent
        freeze all other owners
        insert v, then reinsert K using frozen-aware connected primitives
        if rebuilding blocks, try the next K while allowance remains
        prune only movable owners; validate exact coverage and trial R
        require every frozen chain to equal its entry chain exactly
        if timely: return this one candidate
    if none returns: retain the 049 entry and its preceding R; report failure
commit trial R and the candidate together, then continue reverse expansion
```

The **whole blocked-step repair**, including failed blocks and validation,
shares at most **1,000,000 scans**, inherited from B004's local allowance.
All blocked repairs in one constructor share **5,000,000 scans**, included
inside 049's unchanged **20,000,000 global scans**, never added on top.
Clipping uses live counters, with no per-block renewal. The original absolute
deadline applies through selection, copying, rebuilding, pruning, certification
and final commit. There are at most 40 insertion calls across 15 blocks
(five single-owner blocks with two insertions; ten pairs with three), and
at most 160 local root branches; path work still needs the scan/time bounds.
Stop the constructor after an unrepaired block, as in 049.

For a repaired step, do **not** apply 049's extra fill-endpoint cleanup to
frozen owners outside `K`: that would violate the neighborhood's promise.
Movable released-fill endpoints may be cleaned and revalidated inside the
repair allowance. Ordinary-success cleanup remains unchanged. Selected chain
size need not decrease: insertion adds a logical vertex, and final Q is
measured rather than assumed to improve. Full original-graph validation and
the outer return-time gate remain mandatory.

## Explanatory evidence before repair implementation

Root's exact set diagnostics are preserved in `049_failure_frontiers.md` and
its linked JSON. The unchanged B003 insertion was then called once per frozen
failed entry, followed by one counterfactual call ignoring only that entry's
identified competitor in the future-port guard. All four calls finish within
0.13 seconds and the five-second diagnostic allowance, with no errors or MM
imports. Original insertion returns no candidate; all recorded guard failures
name owner68 for the cycle and owner12 for the wheel. The relaxed calls produce
valid **current** partial minors at Q120 and Q112 respectively, but leave those
same owners with no free future port. They are explicitly **INADMISSIBLE** and
will never be adopted by A050. Query scans are 30,056/49,736 for cycle and
5,830/22,853 for wheel (normal/relaxed), with fresh setup reported separately.
This isolates the guard obstruction; it does not show that reinsertion can
repair it. Script, fixed plan, input hashes and results are under
`results/codex/a050-blocked-reinsertion/frontier_probe001`.

The earlier neighbor-only draft is preserved at
`results/codex/a050-blocked-reinsertion/neighbor_only_draft.md` and is superseded.

## Smallest implementation and evidence

Pin B004 `frontier_reinsertion_construction.py` SHA
`f29cdef92e5e0d6ce51594c7a13dfe2b234c3dfa15e25e4b5b0022d92c5f678d`.
Its insertion primitives with an empty frozen set have the same choices as
B003; their actual diff adds frozen protection and the local scan check.
A separate A050 module can use that builder, with the same existing engine
state and counters throughout expansion. Do not call B004's constructor or
its existing `repair()` selector: that selector can admit non-required
neighbors and also runs for costly successful insertions, outside this policy.
No second full engine setup or cached cross-call state is needed.

Record each blocked-step entry Q, ordered blocks, released owners/sites,
reinserted order, per-block work and reason, completed proposal Q, frozen
comparison, certificate status, actual commit, and elapsed wall. Nested repair
work is already included in global scans and expansion wall; its counters are
overlapping subtotals. Preserve an already committed partial minor if later
work interrupts, and retain the exact preceding requirement graph on failure.
A successful rebuilding certificate is not a committed update until the final
clock check and joint graph/chain adoption succeed.

**Cheap falsifier, before a broader screen.** Freeze one fixed P4 occupied-
endpoint witness and the two exact, independently validated 049 failed entries
(cycle `ember_1829`, wheel `ember_2429`). Reconstruct their trial R from the
saved journal; never use MM output. Use the stated query limits and a common
five-second diagnostic wall allowance. Call only the local rebuilding helper,
not a constructor. Report whether it completes each blocked insertion, exact
Q, immutable frozen chains, work and time; retain every failed attempt.
Do not search alternative witnesses or increase caps to obtain success.
Then check atomic rollback, global/local budget continuity, and that an
ordinary successful insertion does not invoke repair. A no-block fixture must
preserve 049's non-time output/choices. Root will decide whether the reach
results justify a fresh same-input 34-pair comparison against frozen 049;
this proposal does not authorize that run.

**Self-critique.** Rebuilding a long neighbor can be expensive and can lose a
useful placement. A two-competitor cap and the boundary-union filter can omit a relevant
remote blocker, especially one encountered only along a longer routed path.
Building `v` first can consume sites needed to restore `K`; a different joint
assignment might exist but remain unexplored. A one-million-scan failed block
can prevent later blocks being inspected. Frozen frontier protection can be
conservative. Even success can inflate Q and worsen later insertions. These
are conventional local release/reinsertion moves, not a novelty claim. The
hypothesis earns support only through added reach with acceptable measured
cost and later full-pipeline quality; passing the three local fixtures alone
would not establish an all-class improvement.
