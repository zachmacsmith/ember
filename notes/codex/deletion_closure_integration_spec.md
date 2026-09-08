# Final deletion closure: bounded native integration specification

2026-09-08. Design only, before integration or 042 calls. Root has accepted the
initial API and skip choices below. The complete specification still requires
root review, independent core clearance and the 041 source freeze before any
native or pilot edit. The isolated module and its tests remain frozen at the
hashes in [its implementation note](deletion_closure_implementation.md).

## One optional stage, one incumbent

Add the keyword `final_cleanup='off'` to `native_embed`; supported values are
`'off'` and `'deletion'`. Unknown values return the existing native `ERROR`
envelope. The enabled policy is initially supported only with
`polish_objective='qubits_contacts'`, `polish_tree_policy='greedy'`,
`polish_singleton_policy='legacy'` and `polish_star_policy='off'`. Reject other
combinations before construction. This is the bounded supported API for this
experiment, not a mathematical incompatibility between deletion and those
other rules. Construction and initialization retain their existing options;
042 fixes search and spectral initialization.

Insert the enabled stage after the existing `contact_polish` call returns a
valid incumbent, and before restoring original source labels and running the
existing final original-graph validator. Keep initial `spur_prune`, every
contact parameter, its work limits and its call order unchanged. Call the
closure at most once. It consumes that returned incumbent; it does not retrieve
saved embeddings, choose outputs or call another constructor.

The off branch must not import the closure, perform additional graph/embedding
scans or emit cleanup keys. Preserve prior embeddings and all non-time
diagnostics under nonbinding limits, including existing default omissions.
Do not add an explicit `final_cleanup='off'` to the old pilot configuration.
A single string-policy check does not promise bit-identical elapsed time or
identical prefixes when the deadline binds.

For the enabled branch, enforce simple undirected loopless source and target
graphs. Source labels may remain arbitrary native-supported labels: native's
existing inverse map supplies ordinary canonical integer keys to the closure.
Check actual target keys are ordinary Python integers, excluding booleans;
target metadata alone is insufficient. Build/use adjacency from the original
target through the existing canonical helper. Neither graph may be mutated.
These checks and any repeated scans count inside native's absolute allowance.

## Entry, skipping and return behavior

Initialize enabled-only diagnostic records early enough to describe every
return. Use `diag['final_cleanup_policy']='deletion'` and
`diag['final_cleanup']`, without changing legacy fields. Record whether contact
refinement was invoked and returned; zero accepted contact moves is still a
normal successful return. A work/group/pass stop is not itself a failure.

Apply the following precedence after policy/graph validation:

| Condition | Cleanup behavior | Native behavior |
| --- | --- | --- |
| Empty source | Skip, `empty_source`; never import/call closure | Preserve the existing empty SUCCESS return, subject to existing timeliness handling |
| Pipeline fails before a valid contact return | Skip, `pipeline_not_reached`, with native failure stage/status | Preserve the existing failure; do not invent cleanup quality or validity |
| `polish_passes=0` on a nonempty completed construction | Skip, `polish_disabled` | Preserve the initial-pruned result and final original-graph validation |
| Contact was not called because time expired | Skip, `deadline_before_refinement` | Preserve existing final validation and TIMEOUT handling |
| Contact reports `invalid_input` | No closure; `invalid_contact_input` | Return INVALID_OUTPUT (TIMEOUT may supersede under the existing result wrapper) |
| Contact returned normally, but no time remains | Skip, `deadline_before_cleanup` | Retain incumbent and existing final validation/timeliness |
| Time remains, but an independent entry validity check fails | No closure; `invalid_cleanup_entry` | Return INVALID_OUTPUT, subject to existing timeliness handling |
| Entry check succeeds, but expires during that check | Skip, `deadline_after_entry_validation` | Retain incumbent and existing final validation/timeliness |
| Entry check succeeds and time remains | Call the closure once | Retain its last complete incumbent, then final original-graph validation |

The enabled entry check uses the original target and canonical source with
`is_valid_embedding`, independent of contact's flag. Its wall time is recorded
and included in native time. It deliberately duplicates some checks performed
inside the closure to guarantee the valid-entry precondition even if the closure
immediately interrupts while copying. The validator itself currently has no
internal deadline checks: test before/after it, retain overrun reporting, and
do not claim preemptive cancellation. An exception must follow the native ERROR
path with available cleanup diagnostics retained; do not report a false closure.

Pass the exact native absolute deadline to `deletion_closure`, with no renewed
timeout, reserved fraction or extra work parameter. The 500,000 contact routing
limit remains the contact limit; cleanup operations are separately counted and
share time, not that unit system. Keep the core's full info dictionary intact.

If the module returns the untouched entry alias before finishing its copy,
record its actual `returned_input_alias=True`, `input_validated=False` and
`closure_complete=False`. The preceding successful native entry check establishes
the supplied minor's validity; do not rewrite the module's local flags. Native
then makes its existing label-restoring lists and performs its final validator.
An incomplete private result is likewise a valid accepted prefix, not a closed
embedding. A valid late result remains TIMEOUT, with its chains retained under
the existing native result convention. Empty source remains separately covered
by core tests even though native deliberately skips the module.

## Diagnostics and arithmetic

The enabled wrapper saves `status` (`not_reached`, `skipped`, `completed`,
`interrupted` or `error`), `reason`, contact invocation/return flags,
`entry_validated`, `before_qubits`, `after_qubits`, `qubits_saved`, wrapper wall,
entry-validation wall and the unchanged nested `module` info when called.
Unavailable quantities are null, not zero. Skipped modules have no invented
work counters. A known zero-operation skip may record zero module calls; it
must remain distinguishable from an executed closure with no accepted deletion.
Initialize/update partial diagnostics before expensive steps so caught failures
retain known work. Fatal process kills may leave no final envelope.

Compute before/after Q from complete mappings where available, charging this
accounting to the wrapper. Preserve the module's accepted sequence in full,
including canonical source keys, removed target qubits, round and old/new chain
sizes. The existing inverse source map remains evaluator-only provenance for
interpreting these keys against original labels. Do not relabel or truncate
the trace. Wrapper wall contains entry checks, module work and bookkeeping;
module/phase walls are nested components and must not be added again to solver
wall. Native final relabeling, final validation and return overhead are also
inside solver time, outside the closure's own wall.

For each successful recorded stage, require:

`constructed_Q - initial_prune_savings = pruned_Q`;
`pruned_Q - contact_repair.qubits_saved = cleanup_before_Q`;
`cleanup_before_Q - accepted_deletions = cleanup_after_Q = returned_Q`.

The final equation uses `accepted_deletions == len(accepted_sequence)` and
wrapper `qubits_saved`; each record changes one chain's size by exactly one.
A no-call skip after a complete contact return has equal before/after Q when
both are measured. Missing/failure stages remain explicitly unreconciled.
Do not merge cleanup savings into contact savings or modify contact trajectories.

For independently valid final chains and a complete accepted trace, the auditor
can reconstruct cleanup chain **sets** by reversing the deletions, then verify
every forward deletion against the original graphs. List order before cleanup
is not recoverable from this trace, but is irrelevant to minor validity. This
does not reconstruct earlier contact-refinement states. Reject repeated/missing
sites, wrong source keys, size discontinuities or mismatched Q arithmetic.

## Integration checks and self-critique

Before source freeze, independently test absent/default/explicit-off parity;
policy rejection and each skip path; target/source preconditions; mixed labels
and isolates; exactly one call after contact and before final validation; the
same absolute deadline; early alias and private interrupted returns; retained
earlier deletions; no input mutation; original final validation and late status;
full trace and Q reconciliation. Use a real tiny native smoke plus synthetic
fixtures; no cached corpus trial is needed for this integration gate. Block
MinorMiner/busclique imports in candidate correctness checks.

The added entry validation and copying may outweigh deletion work. Even a
strictly smaller closure result can turn a timely control into a late treatment.
Enabled graph checks also precede construction and can alter time-limited
prefixes; nonbinding tests must establish unchanged pre-cleanup behavior, while
042 measures the complete cost rather than assuming equal contact outcomes.
Cleanup can remove witnesses useful to future relocation, but no further
relocation follows this stage. The one-deletion closure is conventional and
does not repair poor placement. Independent core tests plus integration tests
establish correctness only; they do not establish runtime benefit, minimum Q
or improved mean ACL on the full development set.
