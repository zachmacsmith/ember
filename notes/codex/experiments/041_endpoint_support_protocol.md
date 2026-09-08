# 041: endpoint support in the complete embedding pipeline

Draft protocol, 2026-09-08, before source freeze or any new corpus call.
The [implementation specification](../endpoint_support_implementation_spec.md)
and its [root critique](../endpoint_support_root_review.md) define the proposed
secondary objective and its counterexample. Implementation and independent
review are in progress. Passing their focused checks is required before launch.

The hypothesis is that, among equal-Q valid reconstructions, avoiding logical
contacts concentrated on one physical endpoint may enable later shortening.
Q reduction remains primary. The endpoint-support histogram is not an exact
measure of deletion flexibility, and novelty is unestablished. This experiment
tests a general scoring policy, without graph-family dispatch or a portfolio.

Use all 34 original development structures and the exact ideal Z12 target from
039: 4,800 sites, 45,864 couplers, maximum degree 20. Preserve all 35 evaluation
memberships, count the shared King's/frustrated-square topology once in totals,
and retain the explicit absence of the malformed original Sudoku inputs. Do
not replace them with the separate Sudoku supplement or filter by previous
quality, expected score activity, degree or measured cost. All normalized
source bytes must match the archived originals and inverse label maps.

The two fixed arms are:

* `native-search-joint1-contacts-spectral`: unchanged legacy raw-contact control.
* `native-search-joint1-endpoint-support-spectral`: the same configuration with
  only `polish_objective='qubits_endpoint_support'` changed.

Both use one spectral construction, 1,000 layout asks, corrected physical
conversion, the existing pre-refinement pruning and one final contact-refinement
call. Retain beam width 1, four passes, 512 groups, sizes 1–4, boundary-sites 16,
round-robin group selection, greedy trees, 500,000 routing-work allowance and
the existing visit limits. Direct singleton and auxiliary star policies are
off. There is no new final deletion pass, normalized-R control, restart,
checkpoint winner or combination of outputs. Neither arm calls MM/busclique
or receives any saved embedding as input.

This is a complete scoring-policy comparison, not a pure mathematical-objective
ablation. The new policy lazily builds ownership and support scores and checks
the deadline immediately before accepting a complete proposal. Historical R
scoring remains eager and keeps its original timing/diagnostic behavior.
Unchanged routing expansion limits do not imply identical total work, group
coverage, trajectories or time-limited output.

Run seed 0 once per input/arm: 68 full-pipeline calls, serially on hyde03 in the
pinned native environment. Every call receives the same absolute 60-second
solver allowance, fresh process and private initially empty JIT cache. Keep
the pilot's fixed single-thread settings and 90-second process watchdog; retain
solver and whole-process timings separately. There is no MM arm in this screen.

Predeclare input order using
`random.Random('ember-codex-041-input-order').shuffle(sorted(graph_keys))`.
Within each input, use the existing pilot rule
`random.Random(f'{name}:0').shuffle(methods)`, starting with the two arms in the
order listed above. Save that list and the exact task matrix before launch.
The saved list is `results/codex/041-protocol/graph_order.json`, SHA256
`9b2dde6634114d8e229219098d394c334f452f21b594fc48d3b8243048db2e74`.
The 105 evaluator/ledger files have map digest
`b8062ff8fd013c10190afc7525999341eeeb094a2448dc787d153396e5ffe208`,
manifest `ac6dc2e0ec67dd5f12625ac8b9d1a68e4eab2a2e6800511480148b6180ef411b`.
Use one detached supervisor with inherited task locks and explicit lifecycle
records. Observer failure cannot authorize a new start. Preserve every partial,
late, invalid and interrupted result, and retrieve only after verified quiescence.

Freeze source revision/file map, this protocol, source/target records, selection
ledgers, evaluator-only original graphs/label maps, task order/configuration,
environment and transport hashes. All implementation reviews must bind the
actual frozen source. Verify legacy outputs and non-time diagnostics under
nonbinding limits, input nonmutation, API skip/error behavior and absence of
prohibited calls. Fresh host preflight must confirm the pinned interpreter,
absent run identity, supervisor availability and exact transported files.
Only root launches. No new experiment may overwrite a previous identity.

The primary result table includes every input's status, original-graph validity,
Q, ACL, maximum chain length, solver wall and process wall for both arms.
Report paired lower/equal/higher ACL, total Q, and arithmetic mean of per-input
ACL on an explicitly identified common timely-valid population. Publish all
unmatched failures alongside that population, without imputing ACL. Preserve
optimal degree-bound ties and all family memberships. One seed cannot estimate
across-seed ACL variance; any across-input dispersion must be labelled as such.
Historical MM observations cannot be presented as a concurrent timing control.

Mechanism accounting must reconcile constructed Q, pre-refinement pruned Q,
committed refinement savings and final Q. Report equal-size accepted moves,
attempted/visited groups, routing work, score scans/cache hits, setup/adjacency/
endpoint/histogram work, score interruption stages and all recorded wall costs.
Scoring time remains inside the common deadline although it is outside routing
expansion counts. Preserve failed or rejected scoring work.
Distinguish `best_equal_updates` (within-group incumbent updates, possibly in
groups that ultimately shorten) from `equal_size_moves` (final equal-Q group
commits). `unknown_moves` counts net committed groups with unavailable deltas.
`interrupted_stage` records the last stage, not a histogram of all interruption
stages. Setup, scoring, comparison and proposal-validation walls are separate;
initial validation and remaining overhead still belong to total solver time.

The new policy's entry-to-returned R/histogram changes are signed values only
when both required complete scores exist. Unknown values remain null, with
explicit completeness and unknown-move counts. Aggregate known contributions
are partial sums, not substitutes for the net change. JSON histogram keys are
strings and must be decoded as integer bins. Do not coerce missing R to zero,
discard negative R or use an intermediate best as the entry baseline. Scalar
trajectory summaries cannot reconstruct unsaved intermediate embeddings; the
auditor must state that limit instead of inventing certificates.

Self-critique: support cardinality ignores articulation, geometry and singleton
saturation. Strict histogram descent can select worse local minima or reject
useful equal-score moves. Setup and scoring can consume time without a commit;
successful local changes can displace later Q improvements. The supplied Z12
counterexample and previous adverse refinement screens make those concerns
concrete. Preserve every regression and unchanged result. Better histograms
alone do not support promotion. A lower mean ACL with retained reliability
would justify further replication; an unchanged/worse mean or extra failures
weighs against this policy. Runtime costs remain part of that assessment.

No outcome of this 34-input development screen proves the full objective.
Positive evidence still requires multiple seeds, new graph instances, a fresh
same-host MM comparison and a contribution/novelty assessment. The final goal
remains general embedding quality across Ember graph classes, not success on
this fixed set.
