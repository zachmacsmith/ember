# Next A hypothesis: choose a weave after packing

Design only; no candidate, saved-state replay, constructor call or registry change
for this hypothesis. Retain fixed A053 and stop reduction eligibility/order tuning
after [054](experiments/054_results_screen.md) and
[055](experiments/055_results_screen.md). Proposed next evidence is **one bounded
saved-state discriminator**, followed only if supported by a small complete-
constructor comparison. Root review is required before implementation or calls.

## Diagnose the failure before changing it

Two explanations remain plausible. **Representation/objective mismatch:** the
geometric representation or its score does not favor the compact physical states
we need. **Proposal selection:** a useful state is inside the existing geometric
move family but discarded before its actual packed score is known. Search cost
and finite coverage can amplify either; absence of a timeout does not mean the
1,000-ask or contact-work limits are irrelevant.

The code makes these distinctions concrete:

* [`plane.books`](../../packages/ember-qc/src/ember_qc/algorithms/factored/plane.py#L81)
  assigns stair contacts from the y-order, then produces horizontal/vertical hulls
  including each owner's seat. The geometric judge is `(capacity penalty, stair
  span plus active-arm bars)`, not validated physical Q. Later pruning and contact
  repair can leave this two-arm representation, so it is not a restriction on
  every final minor the complete pipeline can return.
* [`field.align_reinsert`](../../packages/ember-qc/src/ember_qc/algorithms/factored/field.py#L1532)
  computes the optimal weave for both the carried block and its reversal,
  preserving the remainder's order. It compares **both already-computed outputs**
  under the frozen axis picture, returns only the smaller, and requires strict
  improvement over the identity. This comparison already contains the exact
  rank-span tie-break; simply enabling geometric tie moves is not a new fix.
* [`plane.arrange`](../../packages/ember-qc/src/ember_qc/algorithms/factored/plane.py#L390)
  subsequently repacks the selected order on the moved axis and then the other
  axis. It adopts every feasible proposal, even when its repacked score is worse,
  and retains a separate best bookmark. Thus a blanket “allow uphill moves”
  proposal would misdiagnose the code. The other orientation is never repacked.
* [`contact_repair._alternatives`](../../packages/ember-qc/src/ember_qc/algorithms/factored/contact_repair.py#L226)
  tries at most nine roots and three generated greedy trees under the current
  configuration. The group beam retains one shortest, physical-ID-ranked prefix.
  Complete valid strict-Q replacements are accepted; equal Q needs higher raw
  coupler redundancy. A missed shorter tree can be a generation/coverage loss,
  not an acceptance rejection. No saved trace proves which applies to every
  current deficit.

The A053 saved accounting also prevents one universal story:

| Input | Core vertices / edges | Core Q → full Q | Historical048 full Q |
|---|---:|---:|---:|
| cycle1829 | 1 / 0 | 1 → 148 | 126 |
| cubic33219 | 117 / 300 | 251 → 258 | 216 |
| kagome32122 | 105 / 210 | 144 → 173 | 154 |
| grid1584 | 104 / 222 | 140 → 167 | 165 |
| planted34404 | 25 / 42 | 28 → 158 | 144 |
| Petersen4083 | 77 / 189 | 151 → 174 | 199 |

Cycle bypasses native entirely: this proposal cannot repair its lifting deficit.
Its known Q126 proves a compact minor exists, not that the reduced lifting
neighborhood reaches it. A054's cubic core Q216 still exceeds the known MM187;
removing artificial demand therefore did not settle native optimization. These
core/lift arithmetic partitions are descriptive, not causal interventions.
Petersen is retained as a case where A053 already improved, to expose regressions.

## One precise hypothesis and prospective rule

The lower frozen score need not select the better **repacked** of the two weaves.
Test that selection loss before inventing a physical score or another move family.
Only consider the second weave when it is distinct from both identity and the
legacy winner and also strictly improves the same frozen, rank-tied objective.
No equal/worse frozen proposal is newly admitted.

```text
run the existing forward/reverse DP, unchanged
identify the exact legacy winner and its existing strict-improvement test
if legacy would decline: decline
repack the legacy winner from copies of the same entry picture, as today
if the other distinct orientation also passes the existing strict test:
    repack it from fresh copies of that same entry picture
among feasible complete readouts choose smaller existing (pen, stair)
on exact ties choose legacy; if neither is feasible decline
adopt the chosen picture using today's rule, even if worse than current
update today's best bookmark; continue the same search and constructor
```

Both DP calculations already occur. The added work is the second copy/readout/
judge, not another constructor, restart or selection among complete embeddings.
Readout can move many vertices, so cost is not constant. The original deadline
covers every copy and readout; an interrupted secondary evaluation must not admit
its partial result or retroactively reject a still-timely complete legacy result.
No physical conversion runs per proposal in the prospective algorithm.

## One saved-state gate, not a new search trajectory

Propose using exactly adoption32 from the already audited **040** captures for
cubic33219, kagome32122, grid1584, planted34404 and Petersen4083, plus cycle1829 as
an explicit full-source geometry/control observation. They carry complete orders,
positions and books; final native diagnostic orders alone cannot reconstruct the
path-dependent packed picture. These are **full-source early states**, not A053's
filled-core states or terminal layouts. A positive finding establishes the local
selection mechanism only; current complete-constructor usefulness stays unproved.

Freeze the six record hashes and runner first. Reuse the 040 tagged codec and
snapshot/book checks, the frozen `plane.readout`/`judge`, and the original-graph
validator. A narrow in-memory observer at `align_reinsert`'s final `bf/bb/e0`
comparison exposes both weaves without changing its recurrence or tie-breaking.
No geometry search/capture needs rerunning.

For each saved state, independently generate the existing unit bag with a fresh
seed0 RNG and inspect its **first32 questions**, under **5s total/input** including
setup, copies and validation. This is a prospective counterfactual question list,
not a claim that these questions were asked at that historical point. Each probe
starts from the unchanged saved state; no candidate feeds the next probe.
Before the questions, perform exactly one unscored readout per axis on fresh
copies of the saved picture, discarding its output. This compiles the same packing
kernels and creates the fixed grid profiles. Cold imports/setup/these two readouts
remain charged to the5s clock and reported separately. If they exhaust it, stop
as cost/unknown. Alternate legacy/other readout evaluation order by question index;
both start from independent entry copies. The proposed25% cost gate uses matched
query DP plus legacy readout time after this common setup, never a denominator
inflated by first-use compilation. It is a warm kernel ratio, not cold pipeline
speed. Record both frozen costs, orders, feasibility, repacked scores, and
DP/legacy/extra-readout wall and CPU, including unsuccessful/interrupted work.

For only the **first** strict repacked-score reversal per input with both pictures
on-chip and feasible, perform the unchanged conversion/completion/isolate handling
and deterministic initial pruning once per picture, within the same allowance;
validate against original edges. Thus at most12 physical evaluations, not physical
pricing for192 proposals. Their diagnostic cost is reported separately from the
prospective extra-readout cost. Keep invalid, late and missing pairs explicit.
Compare both constructed and pruned Q; do not select the best physical probe or
run contact refinement on each. Use a fixed20s process watchdog per input; no
retry, allowance increase, later snapshot search or substituted input after results.

Interpretation is fixed before running:

* **Zero packed-score reversals in a completed gate:** stop this bounded hypothesis;
  do not infer representation impossibility or universal local optimality.
* **Packed gains without lower validated pruned Q:** evidence for score/physical
  mismatch, not a useful constructor improvement. Do not escalate into repeated
  per-proposal conversion. [030](physical_checkpoint_spec.md) already exposed such
  reversals; [040](experiments/040_results_review.md) measured cached conversion at
  2.304 times the corresponding geometric transition cost.
* **At least two non-cycle inputs have a lower pruned-Q counterfactual:** enough to
  consider the small complete screen, not promotion. All other probes remain in
  the denominator. Require complete accounting and extra-readout cost at most25%
  of the summed measured legacy query cost before pursuing this cost-sensitive
  version. This is a proposed gate, not a throughput guarantee.
* **Costs exceed10× their matched legacy query/full-constructor domain:** classify
  an economic failure regardless of a tiny Q gain. Do not compare cold diagnostic
  startup or its one-off physical oracle cost with warm kernel timings, nor infer
  an MM runtime ratio from this diagnostic. Incomplete coverage stays unknown.

## Complete outcome, self-critique and stopping rule

If root accepts the gate and it passes, propose **12 fresh calls**: fixed A053
versus A053 with only this native-core proposal choice on these same six inputs,
seed0,60s, paired fresh processes on one host. Preserve anchors, reduction,
transfer/repair policies and all existing limits; use one evolving construction
and at most its existing one native call. Cycle should be unchanged under
nonbinding time, and must still be reported. All six statuses, original-valid
Q/ACL, core/lift counts, asks/readouts, total CPU/solver/process wall and losses
are primary outputs. There is no new MM arm or mixed-output selection; 28 absent
inputs and seed variability remain unmeasured.

The strongest objection is that repacked-score selection could suppress useful
excursions or alter future questions, while the lower-Q frozen probe loses its
advantage after contact repair and lifting. Both DP orientations can also coincide
or the useful ordering may lie outside either optimum. The extra readout can
consume time needed by later construction. Earlier isolated improvements from
[023](experiments/023_contact_tree_ablation.md) and
[033](experiments/033_results_review.md) did not improve cumulative quality;
this is why the gate leads to complete outputs, not further intermediate-only
repair rounds. Negative/mixed complete evidence stops this variant rather than
prompting new orientation, eligibility, scoring or cap tweaks. No novelty or
all-class improvement is claimed.

Reviewed source SHA256: native `496b54221c2ea77710dc6979fc7f9a202af995c51d029134bdbe6b703764a225`;
plane `5459df9e949df9b0b2e855f100361770b054523542a67c06ece50cbfa1b9b1e8`;
field `a055553988ba3db17ef3588986c1719070c3fcfae4bbfcce7a7084ffe45c7690`;
contact repair `c6f9a5555b010d5e877b568c1ee760e72d170f1f7e0c186179de16b53630da85`.
The A053 table is from `053-results-review/screen001/pairs.json`, SHA256
`38c74a93d772478db06a21a9dae638490b679100f881a0b60379c07cf1f8f845`.
