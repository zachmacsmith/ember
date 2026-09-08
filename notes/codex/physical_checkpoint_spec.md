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

## Completed diagnostic and independent audit

The diagnostic is complete. **Do not promote the 64-evaluation policy from these
results.** It exposes physical-score disagreement and one unrefined opportunity,
but the repeated evaluations cost substantially more than the small optimization
from 028, and neither sparse input improves. No production callback, pilot
configuration, or per-checkpoint contact polishing was added.

Artifacts are in
[`results/codex/030-physical-checkpoint-diagnostic`](../../results/codex/030-physical-checkpoint-diagnostic):
`frozen/` contains the source snapshot, inputs, manifest, worker logs and complete
raw checkpoint chains; `analysis.json` contains the audited aggregate/ranking data.
`diagnostic.py` and `support.py` implement only the frozen research harness.
`analyze.py` independently reloads the original graphs and verifies every saved
chain map and metric. Raw JSON stays separate from this readable note.

The source snapshot was prepared at git commit
`4cad1d67c59484b4d9583e02f49d06e1a556b2af`; its full source-map SHA256 is
`3ea225fe8e6681d5ab6cd96b65d018e0526245764f6d0a2376d5afc8d13653c6`.
Input hashes are identical to 014 and recorded in the manifest. The run used
Python 3.10.19, NumPy 2.2.6, NetworkX 3.4.2, Numba 0.65.1 and dwave-networkx 0.8.19,
with the isolated interpreter symlink preserved. Each worker had an empty JIT
cache, startup `PYTHONHASHSEED=0`, and numerical thread limits one. The source order
was fixed as complete, ER, grid; the host was not reserved.

All three workers completed within their watchdogs. For each input, the unchanged
reference and instrumented searches have **identical actual proposal hashes,
final geometry hashes, and complete final non-time state/accepted-trace hashes**.
The callback's pre/post hash assertions show that checkpoint evaluation did not
mutate the current geometric bookmark. Final checkpoint chains exactly match the
separately converted reference final chains. Runtime import guards found no
attempted or loaded MM/busclique module, and installed-package availability was
checked before importing candidate code.

There are 153 records including the three initial states, and **150 evaluated
checkpoints**, all valid and timely. Every saved evaluated chain map was checked
again from original source/target adjacency: exact source coverage, nonempty and
internally duplicate-free chains, target membership, no inter-chain overlap,
connected chains, and every logical edge's contact. Post-pruning counts and chain
hashes match the records; no invalid zero-size result enters selection. All proxy
record comparisons are strictly decreasing after the initial state. The chosen
record is exactly the earliest evaluated valid minimizer of physical qubits.

| Input | Initial + strict records | Physical evaluations | Initial Q | Final proxy-state Q | Selected Q | Selected placement ask / proxy |
|---|---:|---:|---:|---:|---:|---|
| complete-40 | 29 | 29 | 177 | 156 | **149** | placement ask 48; `(0,326)` |
| ER-80 | 67 | 64 | 439 | 273 | 273 | placement ask 994; `(0,614)` |
| grid-64 | 57 | 57 | 216 | 89 | 89 | placement ask 796; `(0,222)` |

Complete-40's final proxy is `(0,316)`, ten units better than the selected
checkpoint's proxy, but uses seven more qubits. This is **seven unrefined qubits**
of opportunity along this exact trajectory, not a measured improvement after
contact polishing. No checkpoint was polished, and the smaller checkpoint might
offer different subsequent repair opportunities. ER's selected checkpoint is its
final one. Grid's selected checkpoint reaches the same 89 qubits one record before
the final proxy `(0,221)`; the earliest-tie rule retains it without a qubit gain.

ER exhausts the chronological allowance: zero-based records 63, 64 and 65 are
recorded but not physically evaluated; the reserved slot evaluates final record
66. Thus its negative result applies to the **declared evaluated subset**, not to
an exhaustive physical ranking of all 67 records. No extra diagnostic conversions
were performed to inspect those skipped states. The other two inputs do not hit
the cap. Grid's first two records have nonzero overload and use the existing
bounded projection on copies; both yield valid embeddings. No source-specific
evaluation exception was introduced.

## Ranking mismatch is common; useful selection gain is not

Among successive **evaluated** records, physical qubits increase despite a strict
proxy improvement 10 times on complete-40, eight on ER-80, and 15 on grid-64.
Examples are:

| Input | Earlier proxy / Q | Later proxy / Q |
|---|---|---|
| complete-40 | `(0,354)` / 160 | `(0,352)` / 164 |
| ER-80 | `(0,642)` / 278 | `(0,641)` / 288 |
| grid-64 | `(0,486)` / 202 | `(0,481)` / 208 |

There are respectively 61/406, 37/2016 and 24/1596 earlier/later evaluated pairs
where the earlier, worse-proxy state has fewer physical qubits. These pairwise
inversions are correlated comparisons along one trajectory, not independent
statistical observations. They establish that the proxy is not a physical-Q
ordering, but do not imply that choosing an earlier checkpoint helps every input.

## Cost and negative findings

The warm diagnostic includes every callback under its original 30-second deadline.
The reference first call also has a 30-second allowance but warms compiled packing
code. Therefore **cold reference and warm diagnostic wall times are not a speed
comparison**. The stage measurements below directly measure checkpoint work
inside the instrumented trajectory. Callback time includes provenance hashing and
copying, so a production implementation could differ, but the conversion,
completion, validation and pruning time itself is already substantial.

| Input | Warm total diagnostic (s) | Placement excluding callbacks (s) | All physical evaluations (s) | Inline callbacks (s) | Additional non-final evaluations (s) |
|---|---:|---:|---:|---:|---:|
| complete-40 | 1.46757 | 0.76412 | 0.58238 | 0.62062 | 0.56309 |
| ER-80 | 4.32213 | 2.39209 | 1.75268 | 1.82551 | 1.72963 |
| grid-64 | 2.41998 | 1.50115 | 0.78021 | 0.83915 | 0.77020 |

Inline callback time is 81.2%, 76.3% and 55.9% of the remaining placement time
respectively. The ER final reserved conversion occurs after the placement loop,
so it contributes to physical-evaluation and total time but not inline callback
time. The measured evaluation cost occupies about 39.7%, 40.6% and 32.2% of total
diagnostic time. Additional non-final evaluation time excludes the final state
which the original pipeline would also convert; callback overhead is reported
separately to avoid counting it as pure conversion cost.

All checkpoint and complete-call deadline overruns are zero. This confirms timely
behavior on the three short runs, not hard cancellation behavior or a guarantee
under binding deadlines. No construction failures occurred; the failure branches
have not been empirically exercised by this diagnostic. No ACL variance, broad
Ember performance, cross-machine timing, or MM speed ratio is measured here.

The seven-qubit complete-40 improvement and two zero-gain sparse results must all
be retained. Increasing the cap, selecting favorable checkpoint indices, or
running contact repair on every checkpoint would answer different questions and
is not justified by these results. Use the completed broad 026 evidence to choose
the next general quality change. This diagnostic's lasting lesson is the need to
distinguish the geometric proxy from actual validated physical cost while charging
the full cost of observing the latter.

The complete result-file SHA256 map digest is
`4d116e101b901f64b5c0f2c91e6f00292348eda4c9c04cbaa5da01eb69d1a541`.
Every individual result hash and all source/input hashes are retained in
`analysis.json` and `frozen/manifest.json`.

Reproduce from the frozen source in a new directory, preserving all three inputs
and the original policy:

```sh
.venv/codex-native/bin/python results/codex/030-physical-checkpoint-diagnostic/reproduce.py \
  results/codex/030-physical-checkpoint-diagnostic-repeat
.venv/codex-native/bin/python results/codex/030-physical-checkpoint-diagnostic-repeat/diagnostic.py \
  run results/codex/030-physical-checkpoint-diagnostic-repeat/frozen
.venv/codex-native/bin/python results/codex/030-physical-checkpoint-diagnostic-repeat/analyze.py
```

The reproduction script refuses to reuse a directory and copies only frozen
source/input/manifests, creating empty results/log/cache directories. Moving to
another checkout or host requires explicitly updating the recorded interpreter
path and reporting that environment change. `analyze.py` can also be rerun against
the original results; it writes only the derived `analysis.json` summary.
