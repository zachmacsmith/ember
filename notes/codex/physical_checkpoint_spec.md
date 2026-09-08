# Physical-qubit incumbents along one placement trajectory

Design and self-critique saved before diagnostics, 2026-09-08 UTC. This proposal
changes which physical result is retained from one existing geometric search.
It does not change that search's initialization, proposals, acceptance rule,
scheduler, or sequence of geometric states. It has not been integrated.

## Motivation and proposed policy

Experiment 014 shows a concrete mismatch: on complete-40, a lower retained
geometric score (317 → 316) corresponds to more qubits after conversion and pruning
(155 → 156). The geometric score prices arm spans and activity, whereas physical
construction also depends on lane/parity choices, completion, and pruning. The
current pipeline converts only its lowest geometric-score state. A strict proxy
improvement therefore does not guarantee a better physical embedding.

Maintain one valid physical-qubit incumbent while the same placement trajectory
continues. Evaluate its initially packed state and subsequent strict new proxy
incumbents using the existing deterministic bounded projection, conversion,
completion, isolate handling, and pruning. Compare only valid post-pruning physical
qubit counts; retain the earlier result on exact qubit ties. Physical comparison
does not feed back into geometric proposal acceptance or restore an earlier
geometric state. Apply the configured contact repair **once**, to the retained
physical incumbent after placement ends.

This is incumbent selection within one evolving search, not competition between
initializers, independent constructors, graph-family rules, or stored answers.
No MM/busclique call, restart, or contact-polishing trial occurs per checkpoint.

## Explicit bounded evaluation rule

Use a single fixed allowance `max_physical_evaluations=64`, including invalid
construction attempts. Reserve one evaluation for the final geometric incumbent
so a long series of early improvements cannot exclude the baseline's final state.
The first 63 slots cover the initially packed state and strict record improvements
in chronological order. If that final state was already evaluated, reuse its
evaluation; do not convert the same state twice. The minimum permitted allowance
is two, for the initial and final states. This is one fixed policy on all inputs,
not a per-instance allocation chosen from observed results.

```text
physical_best = absent
evaluations = 0
last_evaluated_geometric_record = absent

evaluate(record, positions, books, carried_orders):
    check original absolute deadline and total evaluation allowance
    copy geometry; do not mutate the current search or its retained proxy state
    if record.overload > 0:
        apply exactly the existing bounded projection: axes 0, 1, 0
        preserve the carried orders; use copies and the existing packer
    convert exact wires; run existing completion; fill missing isolates as native
    independently check source coverage, target membership, disjointness,
        chain connectedness, and every source-edge contact
    if invalid: record failure, consume this evaluation, continue same search
    prune with the original deadline; validate again
    if timely and valid and Q is strictly less than physical_best.Q:
        retain the chains and complete source/checkpoint provenance
    otherwise retain the previous physical incumbent

after the initial proxy bookmark and every strict lower proxy bookmark:
    if evaluations < max_physical_evaluations - 1: evaluate this record
    otherwise record that conversion was skipped by the fixed allowance
continue placement exactly as before

at the end of placement:
    evaluate its final geometric incumbent if it was not already evaluated
    if no timely valid physical incumbent exists: explicit construction failure
    otherwise run contact repair once with remaining original time/work allowance
    independently validate and return, reporting any final deadline overrun
```

The proxy comparison remains the existing lexicographic `(overload, stair)`
comparison, including the initially packed state even if it overloads the chip.
Checkpoint records and the final bookmark are identified by one increasing record
number. If an overloaded record is evaluated, its temporary projection uses the
same code path and carried orders as the existing final projection. This is not
a new proposal fed back into search. The final materialized geometry must be
checked against that projected evaluation before reusing it.

Zero physical qubits from a failed or empty chain map are not an improvement.
Failed attempts retain their reason, conversion/completion counters, and optional
partial chains as diagnostics; they do not replace a valid incumbent. If a
cooperative operation overruns the original deadline, the whole call is late
under the current runtime contract, even if a valid earlier incumbent is saved.
The diagnostic should distinguish an earlier timely incumbent from a timely
completed solver call.

## Cost, state, and provenance

The extra cost is at most 63 additional materializations relative to the existing
one-final-conversion pipeline: bounded projection when necessary, wire conversion,
completion, validation, and pruning. Source/target/grid setup is shared. This can
be expensive even if 014's one final conversion was a small fraction of runtime.
The evaluation count is a work limit, not a wall-time guarantee. There is one
original absolute deadline covering initialization, placement, checkpoints, and
final repair. Current conversion/completion lack internal cancellation; checks
between stages and an external watchdog remain necessary.

Production would retain only the current geometric state, the existing geometric
bookmark, a current checkpoint workspace, and the best physical embedding.
It need not store every checkpoint geometry. The diagnostic may retain all
records and embeddings for reproducibility, bounded by the 1,000 proposal limit
and the 64 physical evaluations. Copy/serialization/validation overhead must be
reported separately from conversion where possible.

Source inspection finds conversion's claimed-qubit sets and completion's chain
maps local to each evaluation. Existing target capacity caches are derived from
the immutable target. Still, the diagnostic must verify that evaluation leaves
the search geometry unchanged, and compare actual proposal sequences with an
unmodified reference. Retain source/input hashes, record number, proposal count,
proxy score, projection status, failure reason, constructed and pruned qubits,
embedding hash, elapsed time, and whether the record became the physical incumbent.

## Self-critique before any diagnostic runs

1. **A cheap proxy mismatch does not prove useful headroom.** An earlier valid
   checkpoint might save only one qubit, or none, while repeated conversion costs
   far more. Retain negative results and compare checkpoint cost to the same
   trajectory's placement time. Do not promote from the known clique example.
2. **Strict proxy records omit many states.** A physically good non-record state
   or equal-proxy state will not be evaluated. This deliberately bounded policy
   does not claim to minimize physical qubits over every visited geometry.
3. **An allowance can bias toward early states.** Reserving the final evaluation
   preserves the original final state as a candidate when time permits, but the
   skipped middle/late records might contain the actual best embedding. Report
   saturation and skipped records explicitly; do not tune the cap by graph family.
4. **Repeated evaluation can reduce useful search work.** At an ample fixed-work
   diagnostic, the same final proxy state remains available, but at a binding
   deadline conversion overhead may prevent reaching it. Thus a non-worsening
   qubit comparison on one complete trajectory is not an end-to-end guarantee.
5. **Final refinement can change the ranking again.** A smaller post-pruning
   embedding may leave fewer opportunities for contact repair. Running refinement
   on every checkpoint would confound cost and violate this proposed policy.
   First diagnose unrefined checkpoint rankings; any later integrated trial runs
   repair once and reports cumulative physical quality and total time.
6. **State mutation would invalidate the experiment.** Copies, unchanged proposal
   hashes, exact non-time final geometry/trace equality, and original-graph
   validation are mandatory. A conversion failure must not silently switch
   algorithms or restart the search.

## Prespecified diagnostic

Use all three exact serialized 014 inputs: complete-40, ER-80, grid-64; ideal Z12,
random initialization, seed zero, 1,000 placement evaluations, and no contact
refinement. Freeze current package source, the diagnostic script, and graph/target
records in `results/codex/030-physical-checkpoint-diagnostic`. No production
`plane.py`/`native.py` callback or pilot configuration will be added.

Each source gets a fresh sequential isolated worker and empty JIT cache. First run
the unchanged geometry search to obtain a reference proposal/final-state hash and
warm existing compiled packing code. Then execute an in-memory copy of that same
function with a diagnostic callback inserted only after the initial `best`
assignment and each strict subsequent `best` assignment. This callback evaluates
checkpoints inline, under one 30-second absolute deadline beginning before shared
target preparation. The unchanged reference has its own equal 30-second allowance.
An outer 105-second worker watchdog bounds the two calls and validation.

Record every proxy record, evaluate under the fixed 64-call policy, validate actual
chains independently, and measure construction/pruning/validation/checkpoint
overhead. Compare reference and instrumented final non-time geometry, accepted
trace, and actual proposal sequence. Evaluate the reference final construction
once for baseline physical-Q agreement, but never supply that embedding to the
instrumented run or use it in that run's incumbent choice. Report checkpoint count,
failure/cap/deadline outcomes, ranking reversals, earliest/best/final qubits, and
timely checkpoint cost. Warm diagnostic timing and cold reference timing answer
different questions and must not be presented as a speed comparison.

All three inputs and all failures remain in the report. This diagnostic can show
proxy/physical disagreement and its evaluation cost, not an across-class gain,
novelty claim, or speed comparison with MM.
