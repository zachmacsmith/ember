# Correct the converter's parity-class capacity recurrence

Specification and one self-critique saved before implementation. Experiment 033
is already frozen at `684a95d5`; this correction is separate. Scope is the class
interval assignment inside `field._convert_line`, its description, and bounded
converter-only verification. No source placement, initialization, completion,
pruning, contact search, pilot setting, or external embedder changes.

## Problem and corrected subproblem

[Review 034](conversion_capacity_review.md) independently reproduced a class
capacity violation and a feasible line that the current converter fails to seat.
The existing recurrence orders arms by their earliest possible start but drops
old intervals using a chosen class's later start. A later arm can need occupancy
that was already forgotten. Actual seating avoids overlapping physical claims,
so the observed consequence is a missed arm, not silent shared ownership.

For arm `i` and parity class `p in {0,1}`, retain the existing required closed
integer interval `I[i,p]=[lo[i,p],hi[i,p]]`, class lane count `cap[p]`, cost
`hi[i,p]-lo[i,p]`, initial arm indexing, and history tie rule. The exact subproblem
is to choose one class per arm such that each class's interval overlap depth is
at most its capacity, minimizing summed interval span, then the existing history
tuple lexicographically. This is **not** exact joint physical-lane assignment:
missing qubits/endpoints, external occupied sites and actual couplers are still
handled or checked separately by seating and validation.

Extract the recurrence into a private helper for direct oracle testing, with no
new public option or production diagnostics. `_convert_line` will use it and
retain its existing actual seating and return contract. Tests/diagnostics may
observe helper states with tracing; measured ordinary timings must run untraced.

## Common frontier and complete overlap test

Process arms in the existing order
`(min(lo[i,0],lo[i,1]), original_vertex_id)`. Before either choice for the current
arm, define the **shared** frontier `f=min(lo[i,0],lo[i,1])` and retain every
previous selected interval whose end is at least `f`. Forget only intervals
ending strictly before this common frontier.

For a proposed class `p`, check actual closed-interval overlap depth of the
retained intervals in class `p` **together with the proposed interval**, throughout
the proposed interval. Do not substitute the count of retained intervals with
`end >= proposed_lo`. Such a count assumes class starts are monotone, which
boundary-filtered required intervals can violate; it can wrongly reject
disjoint future-start intervals.

The previous state is already capacity-feasible. Thus it suffices to intersect
each retained same-class interval with the proposed interval and check that the
maximum simultaneous count of those intersections is at most `cap[p]-1`.
For integer closed ranges, use events `+1` at `intersection_lo`, `-1` at
`intersection_hi+1`, coalesced by position. Zero capacity rejects the candidate.
If fewer than `cap[p]` old intervals intersect, the check succeeds immediately.

```
states = {empty_active_set: (cost=0, history=())}
for i in existing_earliest_start_order:
    f = min(lo[i,0], lo[i,1])
    next_states = {}
    for active, (cost, history) in states:
        live = {(j,p) in active : hi[j,p] >= f}
        for p in (0,1):
            intersections = old class-p intervals intersected with I[i,p]
            if 1 + maximum_closed_integer_depth(intersections) > cap[p]:
                continue
            state2 = live union {(i,p)}
            value2 = (cost + hi[i,p] - lo[i,p], history + ((i,p),))
            retain the lexicographically least value2 for state2
    states = next_states
    if empty: return no complete class assignment
return assignment from the least (cost, history) among final states
```

The event calculation does not change the span objective. Actual lane order,
alternate-parity attempts, fallback intervals, misses and emitted chains retain
their current implementation.

## Why the state reduction is exact for this interval subproblem

The shared frontiers are nondecreasing. Every possible start of an unprocessed
arm is at least the current frontier, so an old interval ending before it can
never overlap a future choice. Retaining only the remaining chosen intervals
therefore preserves every future capacity constraint. Every retained state's
past assignment is feasible by induction; the complete overlap test admits
exactly the choices preserving feasibility.

Histories with the same retained state have the same feasible future choices.
Their expired intervals affect only already accumulated cost and the prefix tie
tuple. Keeping the smaller `(cost, history)` preserves the optimal complete cost
and deterministic tie rule because future choices append the same possible
suffixes. Exploring both classes with this safe merging is exhaustive for the
declared interval problem. No assumption of monotone per-class starts is needed.

This proof assumes well-formed finite closed integer ranges, as the converter's
existing required-hull construction produces. It does not establish that a
parity range lies on an existing physical lane or covers every intended crossing.
In particular, negative snapped targets may have been discarded earlier, and
`_lane_ok` currently does not require both requested endpoints to exist.

## Self-critique before implementation

The old recurrence obtained some of its small state count by discarding needed
constraints. Correct retention can increase states and time substantially.
Maximum simultaneous depth does not bound the number of possible active
assignments by a small constant; boundary alternatives can retain intervals
whose actual starts are still far ahead. Worst-case growth remains exponential
in line-arm count. This correction must not hide that increase behind a claim
of a tiny or uniformly bounded state space.

The full overlap check adds work to each candidate transition, even on normal
interior lines. A cheaper start-only check would require a proved and enforced
precondition; this first correction deliberately uses the general exact test.
Measure work/state counts and plain wall time before deciding whether another
semantics-preserving optimization is warranted. Do not introduce a beam or
arbitrary state cap while still calling the interval optimum exact.

Correct class feasibility can yield more emitted qubits by seating previously
missing arms. That is an improvement in coverage, not a worsening physical
objective. Conversely, more reliable raw conversion does not guarantee lower
post-pruning or final ACL. Changes in class assignment can also alter physical
contacts and downstream refinement. A converter-only correction cannot be
promoted as an end-to-end win without a separate full-pipeline experiment.

Lane defects, missing endpoints and actual edge connectivity remain separate
limitations. Narrow the old docstrings rather than implying this correction
solves them. Preserve all outcomes, including genuinely infeasible lines and any
physical seating failure after a class-feasible assignment. No MM or other
embedding algorithm is involved in construction, testing inputs, or fallback.

## Predeclared bounded verification and measurements

Save source snapshots, fixture inputs, scripts, hashes and raw measurements under
`results/codex/035-converter-correction`. Use the isolated native interpreter,
block forbidden embedder imports, and record versions. No full embedding solver
or geometric placement stage is called.

1. Preserve all four 034 cases: two-lane and actual-Z12 identical-point overloads,
   and two-lane and Z12 feasible mixed-crossing cases. Capture full old/new class
   assignments, objective values, state growth, actual seating and misses.
2. Independently enumerate all `2^n` class vectors for 256 deterministic small
   interval instances, seed 3501, with `n=1..9`, capacities `0..4`, and independent
   integer interval endpoints in a bounded range. Check capacity by directly
   counting every selected interval at every relevant integer position, not by
   reusing the implementation's event sweep. Compare feasibility, optimum span
   and complete deterministic history. Include explicit empty, zero-capacity,
   touching-endpoint, tied-cost and reversed class-start cases.
3. Include the boundary-shaped case `I[A,0]=[0,8], I[A,1]=[7,7]`,
   `I[B,0]=[0,0], I[B,1]=[1,1]`, capacities `(0,1)`. The exact class answer is
   both odd intervals, cost zero; a start-only count after shared-frontier
   retention would reject this valid disjoint assignment. This is a class-interval
   witness, not a physical claim that an odd lane covers crossing zero.
4. Add 12 deterministic intact interior Z12-line fixtures: arm counts 4, 8 and 12,
   four repetitions each, seed 3502, crossing endpoints in 1..23 with spans at
   most six. Enumerate class assignments, independently verify actual target
   membership, disjointness, chain connectivity and required couplers. Keep
   feasible and infeasible cases. These are target-realistic converter inputs,
   not samples claiming to represent the distribution produced by the packer.
5. Trace one call per fixture/revision to collect peak states, candidate-state
   transitions and retained-set sizes. For each physical line fixture use a
   fresh isolated worker, retaining its first converter invocation and five
   alternating-order paired warm invocations of old/new code. Initial imports
   are measured separately; "cold converter" means first invocation in that
   worker, not a fresh operating-system disk cache. The arbitrary class matrices
   share one diagnostic process and receive first-observed plus five paired
   repeat timings; those first observations are not labelled process-cold.
   Inputs are identical and no tracing runs during timing.
   Report totals and individual cases, not only favorable averages. Import/JIT
   setup is distinct from plain converter time; this correction adds no new JIT.

Any false feasible assignment, false infeasibility, wrong optimum or wrong
specified tie against the exhaustive class oracle rejects the correction.
Any physical overlap rejects actual seating safety. Infeasible class instances
may still emit a safe partial seating; incomplete output must never be scored as
a better full placement. If the corrected state/time growth is material, report
it and obtain root review before a full-pipeline correction experiment. Keep 033
and its conclusions unchanged.

## Implemented correction and independent verification

The private `_class_interval_assignment` helper now implements the common-frontier
retention and complete overlap test above. `_convert_line` calls it; hull creation,
physical lane seating, fallback and return counters are unchanged. The converter
and wrapper docstrings now limit exactness to the interval-class problem. No
state cap, new public policy, alternate constructor or new JIT kernel was added.

The focused test file runs five test methods containing all 256 declared random
class cases, the boundary case, explicit empty/capacity/tie/endpoint cases and all
16 physical fixtures. They pass in the isolated native environment. The endpoint
test demonstrates only that class feasibility does not certify physical coverage:
its odd-only crossing-zero fixture emits no chain. Its original explanatory
comment was corrected; no algorithm or assertion changed.

Root independently checked **431,901** exhaustive 0–3-arm cases over coordinates
0..2 and capacities 0..2, including **236,853 feasible** cases. There were zero
feasibility, optimum or full-history differences. This separate oracle and frozen
source are in
[`035-root-capacity-verification`](../../results/codex/035-root-capacity-verification).
Its 7.14-second duration is verification work, not a solver runtime comparison.
Root also reports 109 integration tests plus 276 subtests passing, covering the
native, spectral, geometry, contact and pilot interfaces.

The task's frozen converter-only run is in
[`035-converter-correction`](../../results/codex/035-converter-correction), with
complete class inputs, physical crossing lists, source snapshots, raw assignments,
state traces, chains and every timing observation. There are **257 class-oracle
records**: the 256 declared random cases plus the explicit boundary case. The new
helper matches every oracle result. The old extracted recurrence differs on 30:
seven invalid full assignments, nine false infeasibilities and 14 other optimum
or tie differences. The old recurrence was extracted without changing its AST
statements, and its assignments were checked against the actual old converter on
every physical fixture. These deliberately varied/adversarial cases do not
estimate a production defect rate.

Every actual emitted chain map was rechecked independently for physical membership,
disjointness, connected seated arms and required target couplers. All 14 class-
feasible intact physical fixtures are fully seated by the corrected converter.
The two deliberately infeasible fixtures retain safe partial output and one miss;
they are not counted as complete valid embeddings.

| 034 mechanism | Old seated arms / misses | Corrected seated arms / misses | Old peak states | Corrected peak states |
| --- | ---: | ---: | ---: | ---: |
| Two lanes, three identical points | 2 / 1 | 2 / 1 | 2 | 2 |
| Two lanes, crossings 2,3,3 | 2 / 1 | 3 / 0 | 2 | 3 |
| Z12, nine identical points | 8 / 1 | 8 / 1 | 208 | 70 |
| Z12, four crossing-2 and five crossing-3 arms | 8 / 1 | 9 / 0 | 30 | 240 |

The four 034 crossing/capacity witnesses and their original artifacts remain
preserved. The test toy scaffold includes extra unused wire positions and
crossing-zero support for the boundary test; both revisions receive that same
scaffold, and their 034 arms use the same required positions as the original
toy examples. The two actual Z12 witnesses use the canonical ideal hardware
unchanged. No upstream packer was run, and these converter inputs are not a
claim about which layouts the placement stage encounters.

## Runtime and state-growth evidence, including the slowdown

**The feasible nine-arm Z12 witness becomes substantially slower:** mean warm
converter time rises from **0.292602 ms to 1.816144 ms**, about **6.21 times**,
while peak states rise from 30 to 240. Correct retention preserves alternatives
the old recurrence incorrectly discarded. This material cost must remain visible
in any decision to test the correction end to end.

Each physical fixture used a fresh isolated process. Its first invocation and
five alternating-order warm before/after pairs are all retained. Timings below
sum the five-repeat mean for each fixture; they are not one combined solver call.

| Frozen workload | Before summed mean warm time | Corrected summed mean warm time | Ratio |
| --- | ---: | ---: | ---: |
| All 16 physical line fixtures | 3.833651 ms | 5.161325 ms | 1.346 |
| The 12 predeclared generated Z12 line fixtures | 2.186009 ms | 1.952059 ms | 0.893 |
| All 257 arbitrary class matrices, helper only | 15.952149 ms | 28.706791 ms | 1.800 |

The generated Z12 fixtures all remain fully seated. Their individual warm ratios
range from 0.512 to 1.069; all individual observations, including slower cases,
are saved. Peak states across the arbitrary class matrices rise from 200 to 308.
The physical fixtures reach a maximum retained active-set size of eight in both
revisions, but that does not imply equal numbers of states or a global bound on
future workloads.

These short timings come from an unreserved local machine and five pairs per
fixture. They provide no general speedup claim, tail-runtime guarantee, or full
pipeline estimate. Import timing is recorded separately; neither converter path
executes a new JIT kernel. Cold-first and warm observations must not be conflated.
The observed absolute line costs support a bounded full-pipeline measurement,
with the difficult-case slowdown retained and no change to exactness or state
limits. Root's separately specified experiment 036 is the next quality/cost test;
no full pipeline was run for this task.

## Reproduction and final source identity

Run the semantic suite against the current source:

```sh
PYTHONPATH=packages/ember-qc/src .venv/codex-native/bin/python -m unittest discover -s tests/algorithms -p test_converter_capacity.py -v
```

To re-audit saved raw results without overwriting them, use a **new output path**:

```sh
.venv/codex-native/bin/python results/codex/035-converter-correction/verify_existing.py results/codex/035-converter-correction/analysis_recheck_2.json
```

The verifier fails if that output already exists. It runs the saved-data analyzer
with only its output destination redirected; no converter measurements or source
files are rewritten. `analysis_verified.json` is the completed independent
re-read made by this task. The original measurement command, which writes its
declared result files, was:

```sh
PYTHONHASHSEED=0 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 .venv/codex-native/bin/python results/codex/035-converter-correction/diagnose.py
```

Use a separate copy/output directory for any new timing run; preserve the current
raw observations. The current field source differs from the measured snapshot
only by restoration of its original trailing blank line. Full AST equality is
asserted by the analyzer, retaining the relevance of both exhaustive audits.

| Item | SHA256 |
| --- | --- |
| Before `field.py` | `6d717696317192ad0df4f0fb6f5a26bb1da0dc4f57408cfad7ac810bb1a1fbfd` |
| Measured corrected snapshot | `4e143729ac3da926f829a9d366f69253a98e49c63562610833be23445c7bf762` |
| Final current `field.py` | `a055553988ba3db17ef3588986c1719070c3fcfae4bbfcce7a7084ffe45c7690` |
| `diagnose.py` | `2a0aaf46a8cc55f7c5ae0173f86e69e447b135d66c47561058847e2f9d0de793` |
| `analysis_verified.json` | `8ce59aa8073460fccdaa9ae6b77a5c541bbf8e79fc94122472ea49fd91bfb35a` |

The verified artifact hash-map digest is
`b3b4f52020edcac556cff499f0a8f989ca1de7604e5c8813ef76750442e27a18`.
Source/policy changes outside this narrow correction remain root-owned. No
commit was made by this task.
