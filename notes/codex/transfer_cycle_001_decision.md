# Transfer001 research decision

2026-09-09. **Retain A061. Continue the A mechanism with a bounded scheduling
experiment; reject the fixed B027 and C012 policies.** None meets the all-class
objective. All 198 frozen calls finished, were retrieved once from quiescent
supervisors, and passed the existing independent original-graph oracle. All
solver/CPU/process times are present. Each saved mechanism reader passed its
first execution; no candidate was rerun to repair a result.

The [complete tables](../../results/codex/transfer-cycle-001/milestone001/tables.md)
preserve every input, failure, Q, ACL and same-host timing. Twenty primary
structures are the denominator below; two relabelings remain separate checks.
Twelve structures are fresh development cases across six families and two sizes.
Four controls have evaluator-hidden witnesses. No result is confirmation evidence.

| Policy / same-host references | Successes on 20 primary structures | Fresh 12 successes | Common-success Q versus A061 | Common-success Q versus MM | All-attempt solver seconds: policy / A061 / MM |
|---|---:|---:|---|---|---:|
| A063 / hyde06 | 20; A06120; MM19 | 12 | 6 lower,14 tied,0 higher | 4 lower,15 higher | 1180.613 / 210.447 / 158.743 |
| B027 / hyde02 | 2; A06119; MM18 | 0 | 2 lower | 2 higher | 1118.631 / 750.351 / 304.189 |
| C012 / hyde03 | 4; A06120; MM19 | 2 | 1 lower,3 higher | 4 higher | 76.429 / 175.185 / 144.023 |

These conditional Q comparisons never assign an ACL to failures. The fast failed
C attempts are not an overall speed win. MM's failed K100 call does not establish
an ACL win for A. Host02's A061 timeout and differing deadline-censored Q values
remain part of that experiment; references and raw times are not pooled across
hosts. Across-seed ACL variance is unmeasured throughout this single-seed screen.

## What the MM diagnosis now explains

The [pinned MM source review](stock_mm_capabilities_review.md) identified whole-
chain reconstruction against all neighboring chains, movable contact boundaries,
and continued quality search after validity. The [saved-map diagnosis](tracks/c_a061_static_map_results.md)
showed persistent sparse gaps concentrated in unnecessarily long low-degree
contacts. A's complete-constructor evidence now establishes that replacing such
trees can reduce Q on fresh ER80, SBM80 and BA160 inputs, as well as grid,
honeycomb and wheel anchors. Its inherited base Q exactly matches the fresh A061
control on all22 encodings, so these changes are attributable to the new stage.

The scope is small: eight accepted changes save11 qubits across six structures.
Only three commits actually change donor boundaries: two on BA160 and one on
wheel, saving one qubit each. The other changes support original-contact tree
reconstruction, not a claim that boundary mobility explains every gain. All three
fresh improvements still lose Q to MM. These are established algorithmic
capabilities being investigated; this experiment supplies no novelty claim.

## Why A continues, and what must change

A passes its exploratory transfer signal without losing success or Q to A061.
It cannot be promoted: every operator call exhausts its available wall time,
no owner sweep completes, and16 inputs never get past their first owner. Of
1072.222 operator seconds over22 calls,1045.837 seconds are completed nonimproving
root reconstructions. These nested costs are included in the operator total,
not added again. Certification takes0.538 seconds. No artificial work cap ends
these calls; the allocation within the neighborhood is the measured problem.

The next hypothesis is that interleaving owners and revisiting deferred roots
will expose useful moves across the graph before one owner's unsuccessful root
search consumes the allowance. It must retain later roots: successful root ranks
were1,1,112,3,1,1,1,14. An unexplained first-root-only cap would remove observed
gains. Cached contexts must be invalidated after state changes; regeneration and
partial-query costs remain charged. The [A results/design note](experiments/063_mobile_boundary_results.md)
states the before-code pseudocode, critique and complete-output falsifier.

This distinguishes a computational scheduling failure from an exhausted useful
neighborhood. More visited owners alone is insufficient: a subsequent frozen
complete screen must improve final Q across diverse inputs and preserve every
regression. If regeneration consumes the allowance or broader visits yield no
additional complete-Q gains, reject that allocation. Root-distance bounds cannot
blindly prune roots because the current constructor may remove its unprotected
root during final tree pruning.

A's cost deficit is large:15/19 primary common-MM solver comparisons exceed10×,
and14/19 process comparisons exceed10×. There is no universal3× gate. Variance
also needs care: within-embedding chain variance worsens on BA160 and wheel
despite lower Q; that metric is distinct from unmeasured across-seed ACL variance.

## Directions to stop or redesign

B027 demonstrates real overlap resolution on grid, honeycomb and the grid
relabel, followed by exact quality recurrence. It gives no fresh-structure
success and fails all four hidden-witness controls. Routing consumes1146.187 of
1196.241 solver seconds across22 calls. Three calls do not finish initialization;
twelve further failures finish no feasibility sweep, leaving the additive price
update scarcely exercised. This supports a bounded routing-cost diagnosis,
not a conclusion that more time alone would produce good embeddings. Four
failures complete one to four sweeps and remain unresolved. Stop promotion and
uncontrolled parameter changes; the [B note](tracks/b_027_transfer_results.md)
defines the next distinguishing observation. Preserve B026's original neutral
cycling failure and B027's failed transfer policy separately.

C012's17 failures stop at frontier/port restrictions in0.488–25.839 seconds,
not at a work or wall cap. It fails every witness control. Its poor complete
embeddings are not explained only by carrying: the relabeled grid uses Q294
with zero carrying sites versus A061163/MM133. Joint suffix transactions publish
only21 of19,331 attempts and use48.357 seconds; only one successful complete
call includes a joint publication. Stop the fixed monotone frontier and its
suffix-repair sequence. A fresh geometric design must reconsider placement and
available contact space together; the [C note](tracks/c_012_transfer_results.md)
separates the evidence from a proposed alternative. Zephyr geometry remains a
valid source of general heuristics; this particular spatial restriction failed.

## Progress against the class objective

The [retained A061 breadth table](mm_gap_retained_a061.md) remains authoritative:
34/34 successes versus MM29/34; eight lower-Q, seventeen higher-Q and four optimal
ACL1 ties on common successes, with Sudoku and across-seed variability still
unmeasured for that cohort. Earlier failures remain visible. A063 is not substituted
for A061 on selected classes or inputs.

The new fixed-A061 development expansion on06 has12/12 fresh successes versus
MM12/12, four lower-Q and eight higher-Q cases. Regular improves at both sizes;
ER and BA each have a win and a loss; Watts–Strogatz, SBM and planar lose at both
sizes. The class table reports those splits beside mean ACL so the dense ER gain
cannot conceal its size80 regression. A061 and A063 both remain far above the
known ACL1 bounds on the two hidden singleton controls. Contact compactness and
effective search coverage remain shared structural hypotheses, not solved gaps.

All work preserves idealZ12, isolated no-MM/no-busclique candidates, one evolving
state per algorithm, independent validation and full failure/time accounting.
No global exact solver, portfolio selection or source-family dispatch is used.
Future promotion still requires per-class repeat-seed evidence and a separately
frozen untouched confirmation set.

## Two decision self-critiques

First review: A's transfer signal could encourage another sequence of small
repairs while the MM gaps remain. The evidence supports a specific cost
allocation question, not promotion: no sweep completed, later-root gains exist,
and all fresh gains still lose to MM. Require complete-output gains and retain
the variance/runtime deficits; reject a follow-up justified only by owner counts.

Second review: B's implementation acceleration might merely reproduce an
established MM capability, while C's redesign could overfit these newly exposed
examples. Treat B as a bounded causal diagnostic, not novelty evidence; preserve
three independent tracks and source-general choices. Carry fresh structures,
sizes and relabelings into subsequent complete screens and keep confirmation
separate. A future mechanism must justify itself against the retained class gaps,
not against the number of experiments completed.
