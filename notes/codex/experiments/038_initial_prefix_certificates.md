# One initial-prefix certificate screen

2026-09-08. Protocol saved before diagnostic implementation or observations.
This is a mechanism and cost screen for the previously critiqued
[termination hypothesis](../certified_termination_design.md), using the reviewed
[instrumentation specification](../initial_prefix_instrumentation_spec.md).
It does not change the production candidate or select a result from multiple
constructors. Experiment 037 is complete and its full quality audit is separate.

## Fixed matrix and stopping rule

Use all 34 distinct original 017 readiness inputs and the same ideal Z12 target.
Use solver seed zero, the fixed spectral search configuration, corrected
conversion, nominal 1,000 layout evaluations and a 60-second common deadline.
Capture only the actual initial native prefix after its three packing readouts,
before the first search proposal. Actual layout asks must be zero. Every input
receives one fresh isolated worker: one invocation with an empty JIT cache,
followed by one second invocation using that worker and cache. Keep both records;
the second invocation is not guaranteed to warm code skipped by the first.
There are at most 68 observations and no unrecorded warm-up or full search.

Compute the exact integer degree bound and the specified necessary gates.
After the native initial-prefix capture, perform at most one physical
conversion/completion/validation/pruning/final-validation sequence, only if
the common deadline permits and initial overload is zero. Positive overload
is a cost throttle, not proof of infeasibility. Do not project such captures,
add a misses-based gate, resume placement, run contact refinement, retry an
initialization, or inspect a later checkpoint. Preserve all skipped, invalid,
late, nonattaining and missing observations. A hard worker failure leaves its
second invocation missing rather than triggering a replacement worker.

Q=L counts as a certificate only for an independently validated original-graph
embedding completed within the common deadline. Other valid outputs remain
diagnostic records. No output is selected for the embedding algorithm.
If no timely initial certificate exists, reject this checkpoint position and
retain the negative result. Do not tune another index from these observations.
A positive screen would require a separately frozen complete-pipeline paired
ablation on all inputs before any deployment or claim of net runtime benefit.

## Freeze, execution and checks

Build the diagnostic under `results/codex/038-initial-prefix-certificates`.
Use the committed 037 implementation bytes from
`13876c22b0576c3d41d54bffe5ec429e37f5d08c`, source snapshot
`5dfc63cfb5bb2a674cb3e556e13d2b4d18a1857c7a8f296ba27cc2dd5075abc9`.
Freeze all diagnostic files, AST transformation, original and normalized
input/label records, target and environment identity before execution. Candidate
inputs include no saved embedding or competitor output. The root will review
the completed freeze and checks before launching this diagnostic.

Run locally with `.venv/codex-native/bin/python`, single-thread numerical
settings and no MM/busclique packages, plus the existing explicit import guard.
Preserve this interpreter's virtual-environment identity. Every input worker
gets a fresh process and empty cache; it executes its two observations
sequentially. Run input workers sequentially in fixed graph-key order. Use
an external 150-second worker timeout followed by at most five seconds of
termination grace. Preserve partial atomic observation files and raw logs on
failure. Each native/physical operation still shares its own 60-second common
deadline; the worker watchdog grants no extra time for timely success.

Pre-freeze supervision review also requires one default-fatal kernel `SIGALRM`
in each worker. Immediately before launch, the controller fixes an absolute
monotonic deadline 150 seconds ahead; worker startup arms only its remaining
allowance. This alarm is never reset between cold and second invocations and
remains effective if the controller dies. Record both the launch deadline and
alarm metadata. Retain the external timeout and process-group cleanup; an alarm
exit may leave an observation missing and must not manufacture a successful row.

The diagnostic controller must refuse existing results and hold a run lock,
publish its PID/status and per-input progress atomically, and wait for each
worker to exit before advancing. An observer disconnect is not permission to
restart it. Freeze this supervision code as part of the diagnostic; do not
launch until its stop/error paths and artifact preservation have been reviewed.
No remote staging or cluster timing comparison is required for this mechanism
screen. Local machine/load facts and full process wall remain in the record.

The AST hook must be the sole change to the copied `arrange` function. Removing
it must recover the original AST. Forbid all proposal and contact-refinement
calls; count exactly three initial readouts and at most one call to each
physical stage. Preserve the original capture before/after hashing, scheduler
state, original-label mapping, full stage timestamps, CPU time and output chains.
Report import/setup/serialization costs separately and retain them in process
wall. Never subtract diagnostic overhead to relabel a late certificate timely.

The before/after capture audit hashes the complete grid state (including its
graph), source adjacency, target adjacency, and caller source/target graphs,
preserving node/neighbor iteration order, attributes and numeric array bits.
Hashing begins after capture and remains within common solver wall. Retain
native's scalar timeout and original deadlines received by spectral/arrange
before clamping. Incomplete or failed capture records remain audit failures;
they cannot count as cold/second replay evidence. Synthetic checks must cover
state mutation, late final validation, partial record analysis, and the worker
alarm after its controller exits, before any corpus invocation.

Independently validate all physical outputs, input/source hashes, call counts,
deadline classifications and cold/second-invocation state/output agreement
where neither execution is deadline-limited. Compare no recorded time with MM
or a different host. Final saved candidate outputs do not enter the prefix
worker and cannot establish an early saving.

## Self-critique before implementation

The cheap degree gates reject no current input, so any nonattaining eligible
check is pure overhead. Initial geometry may already be too poor, and the
zero-overload throttle may skip useful states. The instrumentation is more
intrusive than a production return condition; exception capture, namespace
wrappers and common-deadline propagation require focused checks. Hashing and
copies can influence the measured deadline. These costs remain visible.
Conversion and packing are not internally preemptible, so one call is not a
strict work cap. The outer watchdog and honest late outcomes are necessary.
This is conventional optimality-based stopping, with no novelty claim.

Status: root approves diagnostic implementation and focused correctness checks
under this protocol. No corpus observation or production change is authorized
until the frozen diagnostic has been reviewed. This is an internal research
sequence within the user's existing authorization, not a new user approval
request.
