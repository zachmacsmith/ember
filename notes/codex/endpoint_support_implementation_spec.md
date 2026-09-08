# Endpoint support: bounded implementation and control specification

2026-09-08. Proposed implementation only, pending root acceptance. No production
edit, embedding call, corpus run or change to frozen experiment 040. This refines
[the mathematical design](endpoint_support_design.md); the
[prior-art review](endpoint_support_prior_art.md) supplies the relevant historical
limits. It is one secondary objective within the existing single evolving state,
with no independent embedder, family dispatch, restart or output selection.

Inspected production SHA256 values (no production edits):

```
contact_repair.py 0ce3c2e7f7287a173294190e476a47901d606043970eb46d6ff3f48ba9ec5f97
native.py         1455154dcc31718b669c8deb75a68656dde5ef695b31bec00df7517adc4f1971
pilot.py          10f74368859fc4e14f16bc921d1a0c4295b6df754cea153b4d67ec3a8c70f8ad
```

## Independently inspected actual-Z12 counterexample

I read the root's supplied script and result in
`results/codex/endpoint-support-review/zephyr_counterexample.{py,json}`, then used
an independent stdlib-only check against the frozen target's **original edge
set**. It rebuilt connectivity by closure, enumerated each directed support set,
checked every single deletion, and enumerated all 21 nonempty chain-subset
assignments for each supplied embedding. It did not import the original verifier
or any algorithm, and did not modify its artifacts. Both embeddings are valid:

| Supplied state | Q | Directed support histogram | Valid single deletions | Minimum Q using only subsets of its supplied chains |
| --- | ---: | --- | --- | ---: |
| A | 7 | N1=6 | center 2606; leaf z's 2508 | 4 |
| B | 7 | N1=5, N2=1 | leaf z's 204 | 6 |

The common frozen leaf chains are `v:[97], w:[121], z:[2508,204]`; centers are
`A:[2604,2605,2606]` and `B:[96,2544,120]`. Among subsets of each supplied center,
with those leaves fixed, the minimum center sizes are 1 and 3. **Unrestricted
relocation with these identical fixed leaves has minimum center size 1 in both
cases**, witnessed by `[2604]`. The original JSON's
`minimum_center_size_with_fixed_leaves` field therefore needs this subset scope;
it does not establish a relocation lower bound. Root is preserving the original
record and documenting this qualification separately.

Neither starting embedding is deletion-minimal. Native applies `spur_prune`
before refinement (`native.py:226`), and the fixture does not establish that the
current bounded proposer generates either state or the A-to-B transition.
Conversely, `_grow` and `_alternatives` (`contact_repair.py:181–287`) do not
promise globally deletion-minimal outputs, so pipeline unreachability is also
unproved. The fixture refutes global alignment between the support histogram
and deletion flexibility. It is neither an observed pipeline regression nor a
proof against a future objective ablation.

Observed original artifact SHA256 values:

```
zephyr_counterexample.py   4841af25e3b63014f3d4dd2552794c8c2e5a9928252a112380a7df1d426f89b1
zephyr_counterexample.json 0c226fbf736c55a9f91343b001558d7a0adc1d969640906c5a43bf45ef95b178
040 prepared target.json  c683ae784e2ee9a1d14f0760368deaa5cfeee2c47a6c2eade683e5412e61177c
```

These bind the records inspected before root's additive correction; they must
not be silently replaced with hashes of a subsequently corrected artifact.

## Control decision and bounded API

Keep existing `objective='qubits_contacts'` **untouched**, including its eager R
scoring, validation placement, default diagnostic schema and expansion
accounting. Also preserve `objective='qubits'`. Add exactly one experimental
choice, `objective='qubits_endpoint_support'`, forwarded by native as
`polish_objective='qubits_endpoint_support'`. No normalized-R choice is proposed
for this first implementation. In particular the control must not build unused
support sets to simulate equal overhead.

The new objective accepts a valid lower-Q proposal, or, at equal Q, a strict
lexicographic decrease in `(N1,N2,...)`. Exact histogram ties are rejected; R is
diagnostic only, including when its change is negative. Both comparisons use
actual chain cardinalities and complete original-graph validity.

Initial integration scope is the ordinary group refiner:
`singleton_policy='legacy'`, `star_policy='off'`, `tree_policy='greedy'`. Reject
other combinations with the new objective at the contact/native boundaries,
even if polishing is disabled, its group budget is zero, or the source is empty.
This avoids silently retaining raw-R equal-size acceptance in the direct
singleton path. A future combination with a strict-Q star proposer is
mathematically possible but is outside this bounded implementation/test scope.
Existing combinations for the two old objectives retain their behavior.
For the new choice, explicitly require simple undirected loopless source and
target graphs before constructing context. Preserve existing errors for old
choices; add no default work or diagnostic keys merely to support this option.

Implementation should isolate the endpoint collector in a small new module
and condition only the complete-proposal acceptance/scoring branch of `_repair`.
Do not fork the constructor or duplicate the routing algorithm. Keep all root,
region, alternative, prefix sorting, group, pass and expansion-limit rules.
As with existing R, allow equal-size alternatives in size bounds; support is not
a beam/prefix/group ranking feature. No new tunable parameter or score-work cap.

## Ownership and exact incident scores

For one existing group visit K, let E_K contain each source edge incident to K
once. Build its two directed keys deterministically from the ordered group and
`ctx.src_adj`, deduplicating selected-selected edges. A private scorer tied to
this visit holds **no eagerly built owner map or score**. On its first required
equal-size comparison it builds ownership from the entry embedding once.

Each complete proposal is a copy of that entry mapping with only K replaced.
Do not mutate entry chains, outside chains or a published incumbent. Build a
temporary proposed-owner map for K and reject duplicate sites, target-unknown
sites or a frozen owner's site. Resolve physical ownership by:

```
owner_proposal(q):
    if q is in proposed_group_owner: return proposed_group_owner[q]
    owner = entry_owner.get(q, ABSENT)
    return ABSENT if owner is in K else owner
```

Thus an old selected site released by the proposal is free; it never retains
its stale entry owner. Use a unique absence sentinel, not a possible node label.
No per-pass or cross-group cache is introduced. After any group commit the next
visit creates a new scorer; there is no global owner refresh to omit or charge.

For every selected qubit q, inspect its actual target adjacency. Whenever p has
logical-neighbor owner v, add q to S_(u→v) and p to S_(v→u). This records **both
directions**, including frozen-chain endpoints, without scanning whole frozen
chains. Deduplicate endpoint sets. For a selected-selected physical coupler,
process it only at the endpoint with smaller `ctx.rank`, or equivalently
deduplicate it explicitly. Count each actual physical coupler once for R:

```
H_K[k] = number of directed keys from E_K with support cardinality k
R_K = number of actual physical couplers representing E_K - |E_K|
```

A zero support on a required edge is invalid, not a desirable histogram bin.
Full validity remains separate: support cardinality does not check connectivity.
Integer histogram subtraction cancels unaffected edges exactly, and
`R_K(proposal)-R_K(best)` equals the global signed R change because outside
chains are fixed. Find the minimum nonzero difference key by a linear scan of
the sparse union; sorting all bins is unnecessary for comparison. No weighted
float scalar or support cutoff is used.

Cache only completed scores for the visit's entry/current-best states. These
are tied to their immutable selected chain lists, not to a recycled temporary
mapping or merely the group name. Discard all partially built score/owner state
on interruption. A scored rejected trial must never overwrite the best score.

## Lazy acceptance and deadlines

The new branch compares each complete proposal against the **current best within
the group**, not always its entry. A reduced best size changes subsequent size
bounds exactly as before. The algorithmic ordering is:

```
best = entry; best_score = UNKNOWN
for each existing complete proposal trial with Q_K(trial) <= Q_K(best):
    if absolute deadline reached: stop with the last certified best
    if Q_K(trial) < Q_K(best):
        if not full_original_graph_valid(trial): continue
        if absolute deadline reached: discard trial and stop
        publish trial as the group's best; mark its secondary score UNKNOWN
        continue                     # no scoring is needed to justify lower Q

    old_score = completed_cached_or_compute_score(best)
    new_score = compute_score(trial)
    if interrupted: stop with the last certified best
    if either score is invalid: reject trial (invalid best is an internal error)
    if first_nonzero(new_score.H - old_score.H) is not negative: continue
    if not full_original_graph_valid(trial): continue
    if absolute deadline reached: discard trial and stop
    publish trial and its completed score as the group's best
return that best, with truthful end-time/deadline diagnostics
```

Final validation can cross the deadline because `_Context.valid` has no internal
cancellation. Its result then **cannot authorize a new commit**. Retain an
earlier certified improvement if one exists. Check after potentially expensive
comparison/record preparation too, immediately before changing best and its
acceptance counters. Do not run a finish-time score solely to fill diagnostics.
If a strict-Q candidate was timely validated, a later interrupted score cannot
undo it. Native's final validation and overall TIMEOUT reporting remain intact;
returning an earlier valid incumbent does not imply timely solver completion.

Score cancellation uses the absolute deadline directly, not `_Budget.pop()` or
`_Budget.check()`'s expansion test. A complete proposal already generated using
the last allowed routing expansion may still be considered, as in the ordinary
control. Scoring grants no new routing expansion. Check the deadline throughout
ownership construction, overlay creation, incident-edge/physical-adjacency
scanning and histogram processing; a partial scan never supports equal-Q
acceptance. No wall time is subtracted from the native deadline.

## Work and signed diagnostics

Existing R builds a full owner map and scans physical adjacency without charging
`_Budget.expansions` (`contact_repair.py:303–321`). Retain that historical meaning:
region/boundary/routing work keeps the same ceilings, while all new scoring time
is charged to the same absolute deadline. Equal expansion limits do **not** mean
equal total work or equal group coverage.

For the new objective only, expose a separate score record: attempted/completed/
interrupted scans and cache hits; owner-map entries; overlay sites; incident
source edges; selected qubits and target-adjacency entries visited; unique
endpoints inserted; histogram entries inspected; owner/setup and score wall
time; interrupted stage. Count performed operations, including partial scans.
Use disjoint timer subtotals, and keep final validity time separately visible.
These counters do not consume ordinary expansions or create an auxiliary limit.

Expected per-score work is O(Q_K*Delta+|E_K|), with O(Q) ownership setup once per
scoring visit and O(old_Q_K+new_Q_K) overlay work; storage is O(Q+Q_K*Delta+|E_K|).
Hash/set costs are expected bounds. No improvement over current runtime is
claimed: endpoint deduplication adds work even when ownership reuse saves work.

Keep `qubits_saved`, final `equal_size_move`, and member-growth semantics. For
the new path, a group-entry-to-returned-best R delta is a **signed integer only
when both completed scores are available**, otherwise null with an explicit
incomplete flag. Do not encode missing as 0, truncate negative changes, or
reinterpret an increase in R as qubits saved. A pure equal-Q accepted group has
both scores and must report its exact signed R and sparse signed histogram
delta. A group that strictly reduces Q may legitimately leave both secondary
deltas unmeasured. Within-group equal-size best updates can still record their
known local deltas even if the final net group delta is unknown.
Never substitute an intermediate equal-Q comparison baseline for the original
group-entry baseline. The literature agent independently confirmed this scope
and the affected-edge comparison; this was a mathematical review, not execution.

The new path's aggregate R delta is null if any committed net move is unknown;
also report the signed sum of known contributions and unknown-move count,
clearly labelled as partial. Apply the same completeness rule to histogram
aggregation. Existing numeric `contact_redundancy_gain` fields need explicit
new-objective nullable handling in move aggregation/trajectory/analysis; old
objectives retain their exact numeric schema. Do not mix two objective schemas
under an unlabeled historical auditor. No additional scan is authorized merely
to turn a diagnostic null into an integer.

## Pre-implementation critique and decisive tests

The saved Z12 witness disproves a general shrinkability ordering. Singleton
support-one terms often cannot change; articulations and the placement of sole
obligations can dominate cardinality. Strict histogram descent prevents a finite
state cycle but can lead to worse local minima, reject useful ties, or prolong
passes. Existing groups still omit zero-excess chains. Equal-size commits alter
later states and possibly group construction; extra scans can displace ordinary
work even without a commit. No same-trajectory guarantee follows from retaining
the same schedule rule. The potential and endpoint bookkeeping are not asserted
to be publication-level novelty.

The untouched control is scientifically clear but this first comparison is a
**complete scoring-policy comparison**, not a pure mathematical-objective
ablation. The support path adds lazy ownership/scoring and final acceptance
deadline checks; these can affect finite-budget outcomes. A future separately
named, lean lazy-R arm could isolate those implementation effects if needed.
It must not compute unused histograms. With nonbinding deadlines, pure exact R
scoring and validation, lazy rather than eager R should preserve proposal
accept/reject decisions and subsequent non-time chain trajectories. Work/score
diagnostics would still change; deadline-binding outputs and stop locations
can differ. Therefore such a normalization is neither byte-compatible nor a
silent replacement for legacy R. It is not included in this initial work.

Before any corpus call, require focused independent tests:

1. Whole-target-edge enumeration agrees with incident H and R for varied small
   valid minors, frozen reverse supports, selected-selected edges, repeated
   couplers sharing one endpoint, released sites and owner transfers. Include
   the root Z12 witness, but do not force it into the proposer.
2. Injected complete proposals establish histogram/R ordering disagreement,
   exact tie rejection, and comparison against an already improved group best.
   Test two directions independently; counting only selected endpoints must fail.
3. A valid strict-Q improvement survives a deliberately failing or interrupted
   secondary scorer; its missing R is null. A later equal-Q attempt requires the
   lazily computed best score. Negative R is retained when known.
4. Fake clocks interrupt each score stage and cross final validity/acceptance;
   no partial score or late candidate commits, and an earlier certified best
   survives. Exhausted routing work does not manufacture extra expansions.
5. Old `qubits` and `qubits_contacts` results plus all non-time diagnostics
   replay exactly against frozen pre-edit source under nonbinding limits. New
   option/error/skip handling is tested at both APIs with prohibited imports
   blocked. Inputs and outside chain lists remain unchanged.

If independently accepted, freeze a separately numbered, all-34-input screen:
one untouched `native-search-joint1-contacts-spectral` control and one
`native-search-joint1-endpoint-support-spectral` arm differing only in the new
objective option. Both use the same canonical source bytes, target, seed 0,
1,000 layout asks, 60-second common allowance, existing group/pass/routing
ceilings and one final refinement call; star off, direct singleton off, greedy
trees. This is 68 full-pipeline calls, with no checkpoint/output winner selection
and no new MM call needed for this development ablation. Freeze input/config/
source/environment identities and paired run order before observing results.

Report every validity/timeliness result, Q and ACL delta, variance across this
fixed input set (not seed variance), scoring cost/completeness, accepted equal-Q
moves, visits and expansions. Report family summaries only as evaluation labels.
Failure-aware all-input results accompany common-success means; historical MM
comparisons remain labelled historical. No lower common-success mean ACL,
additional failures, or material runtime/group-coverage harm counts against
promotion. Better histogram values alone do not constitute success. Positive
development evidence would still require repeated seeds/new instances and a
separate contribution/novelty assessment. No result or implementation is assumed
by this specification.
