# Scope of a separate auxiliary work allowance

2026-09-08. Design review only: no implementation, solver invocation, corpus
observation or protocol change. Experiment 039 retains its shared 500,000-work
budget and 25,000-unit auxiliary share. This review does not use its outcomes.

The [allocation note](refinement_work_allocation.md) has a defensible conditional
replay argument, but the condition must refer to an **ordinary-search trace**,
not the complete diagnostics or final-quality dominance after auxiliary commits.
Separate accounting can remove one source of displacement; it cannot remove
elapsed-time cost, changed embeddings or independently imposed group limits.

## What the existing evidence establishes

[037](experiments/037_results_review.md) records 38 qubits saved by auxiliary
commits, 31 fewer saved by ordinary moves, and a net seven-qubit improvement.
Treatment uses 166,748 fewer ordinary work units and 53 fewer ordinary visits,
while its total work rises by 433,733. Two regressing inputs have no auxiliary
commit. Saved upstream summaries agree and calls are timely, supporting the
allocation hypothesis without establishing that every missing ordinary reduction
was caused by work quotas. Full intermediate embeddings were not saved.

[033](experiments/033_results_review.md) also changes scheduling: its 520 extra
visits use ordinary group slots, and direct proposals precede reconstruction
inside a visit. Ordinary visits fall by 399; the 450 recorded displaced groups
count generated suffixes and are not the same quantity. Its auxiliary moves
save 143 qubits locally, while total treatment savings fall from 615 to 614.
Giving only a separate global work counter would not repair these slot and
within-visit effects. The no-extra-group, ordinary-first star schedule is the
relevant starting point for the proposed guarantee.

## A precise conditional guarantee

Fix the exact original graphs, node/adjacency order, valid initial embedding,
ordinary proposal implementation, parameters and deterministic environment.
Let W be the ordinary work ceiling, A=floor(W/20) the separate auxiliary ceiling,
G the existing per-visit ceiling, and O/H the respective work actually spent.
Preserve the existing total ordinary-group and pass limits. Queries retain the
same first-failed-visit, once-per-center/pass rule; ordinary acceptance permits
cache refresh but suppresses a new auxiliary query. At ordinary visit j:

```text
L_j = min(G, W - O)
run ordinary reconstruction with limit L_j and original absolute deadline D
u_j = its actual work; O += u_j
publish any accepted ordinary move
auxiliary query/refresh may use at most min(A - H, L_j - u_j)
charge all setup, selection, query and maintenance to H, once
ordinary stopping and next-visit limits read O, never O + H
report total work O + H <= W + A
```

The displayed auxiliary allowance is shared by query and maintenance during
that visit; it is not granted afresh to each. The combined visit cap remains
unchanged. An ordinary visit exhausting L_j leaves no auxiliary capacity, even
if H<A. This policy guarantees neither that A is consumed nor that every
eligible auxiliary block is attempted. Exhausting A disables only auxiliary
work; it must not terminate, skip or reorder ordinary work.

Assume that no auxiliary move commits, auxiliary access does not mutate the
incumbent/context/ordinary search state, and the common deadline never changes
a control decision in either execution. Then ordinary group lists, per-call
limits, returned embeddings, accepted ordinary moves, ordinary work counters
and non-time stopping reason match the auxiliary-off control.

Proof is by induction over ordinary visits. Initially the inputs and O agree.
The same current embedding and ordinary counters generate the same group and
L_j. Ordinary reconstruction is deterministic under those inputs and nonbinding
clock checks, so its result and u_j agree. Failed/read-only auxiliary work
changes only H and private auxiliary state. Ordinary acceptance and the pass's
`changed` flag therefore agree, completing the induction across visits and
passes. “The same ordinary limits are reached” is thus a consequence of these
rules, not an assumption that silently requires the desired result.

The compared trace must retain each ordinary call's group, input/output chain
state or hash, actual allowance, ordinary work, acceptance, and ordinary Q/R
change. Project cumulative expansions to O. Raw combined trajectory expansions,
proposal counts, cache diagnostics and wall time intentionally differ; merely
removing time fields from the current aggregate is insufficient. In a general
run the argument establishes only the completed ordinary prefix before the
first auxiliary commit or first differing deadline decision.

The source points requiring separation are the star loop's `remaining`, visit
limit, accumulation and work-stop checks in
[`contact_repair.py:671`](../../packages/ember-qc/src/ember_qc/algorithms/factored/contact_repair.py#L671).
It currently derives them from total `info['expansions']`. The ordinary pass's
`changed` flag must continue to reflect actual accepted moves, and auxiliary
attempts must not increment `groups_tried`. After a commit the existing flag may
legitimately extend the trajectory; the no-commit theorem no longer applies.

## Where stronger claims fail

**Commits can remove a later opportunity.** A hand-derived physical example
uses two independent source stars, with centers a,b and two leaves each. The
incumbent centers are a=[1,2], b=[5,6,7]; their respective leaves are [3],[4]
and [8],[9]. The target has exactly edges
`1–2,1–3,2–4,5–6,6–7,5–8,7–9,0–3,0–4,0–8,0–9`.
The incumbent uses nine qubits. Moving a to [0] is valid and saves one. With a
unchanged, moving b to [0] instead saves two. After the first move, frozen a
owns 0 and b cannot shorten while its leaves remain fixed. Hence a valid local
descent can leave Q=8 where another ordinary continuation reaches Q=7, regardless
of unused work allowance. This demonstrates the limit of a monotone-Q argument;
it is not a claim that the current bounded ordinary solver follows that
particular sequence. The observed 037 local four-qubit saving with a two-qubit
final regression is a separate empirical warning, with allocation and trajectory
effects still mixed.

**Deadline binding defeats no-commit replay.** If a last ordinary improvement
needs 0.02 seconds with 0.05 seconds remaining, a preceding failed auxiliary
query taking 0.10 seconds can prevent it without consuming one unit of O.
Neither the separate counter nor a 5% operation share reserves ordinary wall
time. The original absolute deadline must remain authoritative; extending it
would test a different resource policy.

**Maintenance can break the guarantee if coupled incorrectly.** An ordinary
commit may exhaust its visit allowance while ownership refresh still needs
work. Correct behavior is to retain that valid commit, invalidate/disable only
the auxiliary cache and continue the ordinary schedule. Charging refresh to O,
returning from the whole call because A is exhausted, or letting stale auxiliary
ownership influence ordinary domains invalidates the induction. Successful
ordinary commits may require this maintenance even when no auxiliary move ever
commits. All such work belongs in H and elapsed time.

**Scheduling remains an independent resource.** With two available group slots,
counting a failed auxiliary attempt as the second slot suppresses an improving
second ordinary group even when O<W and no auxiliary move commits. Similarly,
subtracting a pre-ordinary auxiliary scan from G changes that visit's proposal
limit. These are relevant to 033 and excluded from the proposed star policy.
No extra passes may be triggered merely by an attempted query or cache setup.

## One falsifiable future test

If separately authorized, first test the theorem with deterministic tiny
incumbents and auxiliary queries whose commits are suppressed by a test harness.
Compare complete projected ordinary traces to the off control, including work
exhaustion, no-improvement/pass/group stops and failed post-ordinary refresh.
Every mismatch under nonbinding deadlines is an implementation failure. Fake
clock checks should separately demonstrate the expected loss of the guarantee
at deadline binding; those failures must not be hidden by a larger timeout.

Then freeze one allocation-only, complete-pipeline comparison of the current
connected kernel: shared W versus ordinary W plus separate A, with identical
constructor, kernel, visit cap, groups, passes, seed and 60-second deadline.
Use all 34 fixed development structures, seed zero, both arms on one host in
prespecified adjacent randomized pairs: 68 calls. Keep A=W/20=25,000 fixed,
report the separate arm's 525,000 total ceiling honestly, and retain all failures
and regressions. Freeze this independently of 039's eventual outcomes; do not
choose a kernel, fraction, input subset or seed from those outcomes.

Record exact starting-refinement hashes and ordinary call traces as well as
final validity/ACL/Q, total time, O/H, maintenance and no-commit strata. The
primary allocation hypothesis is lower common-timely-success mean ACL without
additional failed/late calls; absence of that gain is evidence against spending
the extra work. Report paired regressions and total Q even if that mean improves.
This two-arm comparison does not itself test equality to an auxiliary-off
control; the preceding correctness test supplies that distinct check. No MM
timing or unseen-instance claim follows from this development experiment.

Self-critique: the conditional theorem deliberately excludes the difficult
cases—commits and binding deadlines—and is mostly a scheduler correctness
property. Work units have unequal costs, so a modest operation increase may be
an expensive runtime increase. Restoring ordinary quota could recover few or no
useful reductions and leave the much larger quality gap unchanged. The proposed
experiment must therefore be allowed to reject this policy; it cannot justify
progressively raising allowances until one result improves.
