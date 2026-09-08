# Cumulative induced-star refinement comparison

**Superseded before any experiment execution:** use
[037's full-pipeline protocol](037_induced_star_pipeline.md) for the first
benchmark. The existing frozen pilot already supplies process locking, watchdogs,
source/input identities and complete native calls. A saved-incumbent comparison
would require a separate runner adaptation while giving weaker evidence about
cumulative pipeline performance. No treatment setting or outcome informed this
change. Preserve this unexecuted draft as planning history.

Protocol saved on 2026-09-08 before implementing/integrating the new operation
or observing any comparison result. This is a component experiment on saved
valid incumbents. It does not measure complete construction or establish that
adding this operation earlier in the native pipeline improves final embeddings.

## Frozen inputs and two fixed arms

Use every one of the 34 independently validated final embeddings from036,
their original source graphs, ideal Z12 target, original input/task identities,
and result hashes. All inputs come from the same fixed native spectral method
with corrected conversion and legacy singleton policy. No MM embedding, other
algorithm's output, family label, or competitor metric enters either refiner.

Each arm starts from its own copy of exactly the same saved incumbent. The
control applies current ordinary contact refinement; the treatment adds the
single induced-star policy specified in
[the implementation specification](../induced_star_implementation_spec.md).
No output from either arm seeds another arm, and no best-of result is constructed.
Every source receives both arms, including sources at a lower bound or with no
eligible center. Those legitimate skips are part of measured behavior.

Both arms have the same 60-second complete refinement deadline, 500,000 global
units, 50,000 units per ordinary visit, 512 total ordinary groups, four passes,
sizes1–4, beam1, three alternatives, halo2, region cap512, two reconstruction
orders,16 boundary sites, round-robin group scheduling, greedy trees and
`qubits_contacts` objective. Legacy singleton policy remains fixed. The matching
arm shares these limits, with the specified5% auxiliary ceiling and2,048-unit
query ceiling. It adds no group visits and accepts only strict qubit reductions.

Freeze all code, configuration, inputs, graph records and incumbent records
before starting the68 calls. Use sequential fresh isolated-native processes on
one host, paired by input with arm order determined by a fixed input/seed-based
shuffle before results. Preserve per-task claims, raw logs, worker exit status,
process watchdog results and original observations after interruption. Never
restart a trial merely because observation failed. The controller must hold
a process lock inherited by its workers.

## Integrity and measurements

Independently validate both saved incumbents and final results against the full
original source/target: exact source keys, nonempty connected chains, target
membership, duplicate/disjoint ownership, and every logical edge. Recompute
Q, ACL, maximum chain length, within-chain variance and whole-embedding contact
redundancy. Across-solver-seed ACL variance is unavailable from this single
incumbent per input and must not be replaced by within-chain variance.

The reported refinement time includes context construction, input validation,
ordinary reconstruction, all matching/cache work and final acceptance checks.
Keep process startup and independent post-run audit time separate. No MM timing
ratio follows from this experiment. A cached starting embedding removes the
construction cost and supplies no full-algorithm speed claim.

Report every input's control/treatment qubits, ACL, status, actual elapsed time,
total charged work, ordinary group coverage and complete accepted trajectory.
Reconcile trajectory sums with independently counted Q/R. Include selection
rejections, considered centers, selected sizes, cache build/refresh/disable
events, root/domain/matching/certificate work, truncation reasons, successful
matching moves and group sizes. Describe size strata3–4,5–8,9–21 without
using them as separate runtime policies. Isolated matching savings are already
included in final treatment savings and are not gains over the control.

Do not drop failures from success counts or credit incomplete/late embeddings
with competitive quality. Report success-conditioned comparisons and their
coverage explicitly if any call fails. Preserve all ties, losses and zero-work
skips. Controls need not equal036: both arms deliberately perform one additional
bounded refinement from its final incumbent. Their extra cost and this scope
must remain clear.

## Self-critique and next decision

The shared auxiliary cost can still reduce ordinary work coverage, and accepted
moves can change later groups. A correct matching routine can therefore worsen
the final result, as033 demonstrated for another local operation. Conversely,
already-refined incumbents can understate opportunities available earlier in
the pipeline. Neither outcome alone proves performance during construction.

All34 sources are previously observed development structures. The subset/root
rule and numeric work limits are fixed before this comparison. Do not select
parameters by family, source identity, favorable seed, or the best treatment
output. A promising cumulative result justifies a separate frozen full-pipeline
experiment with one globally fixed policy. A negative result requires a retained
failure analysis before revision, not deletion of inconvenient rows.

Novelty of matching itself is ruled out by the documented prior-art overlap.
This experiment can establish only the practical value of the restricted
refinement move under its specified search and budget. The larger project still
requires a general algorithm with the requested MM quality/success/runtime
performance across declared graph-class distributions and new source instances.

Status: protocol only. Core and integration correctness review, experiment
runner validation, source freeze and launch are still outstanding.
