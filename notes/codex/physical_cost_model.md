# Physical qubit cost of a geometric placement change

Source inspection and design only. No production change, new placement run, or
embedding benchmark was performed for this note. The mathematical statements
below distinguish counting the current converter's actual output from optimizing
a theoretical wire assignment. A name or docstring containing "exact" does not
establish either claim.

The useful decomposition is **by physical orientation and line, before empty-chain
seeding and completion**. Those line conversions are independent on the current
hardware representation, so their actual emitted qubit counts can be cached and
updated exactly. There is no demonstrated cheap local formula for the complete
pre-pruning embedding, and still less for post-pruning qubits. A current placement
proposal repacks both axes and can invalidate many line entries even when its
selected source unit contains one vertex. Whether incremental line pricing is
cheap enough therefore needs a bounded locality/cost measurement first.

## Four quantities that must remain separate

For a layout `L`, define:

* `Q_wire(L)`: qubits emitted by all `_convert_line` calls, before `_ensure_seeds`.
* `Q_seed(L)`: qubits returned by `wire_seeds_exact`, including nearest-free seeds
  for chains with no seated arm.
* `Q_constructed(L)`: qubits after `complete_seeds` and native isolate filling,
  before `spur_prune`. This is native's `constructed_qubits`, and is an embedding
  metric only if original-graph validation succeeds.
* `Q_pruned(L)`: qubits after the actual deterministic, possibly deadline-limited
  pruning pass. Final contact reconstruction may change the count again.

The pipeline ordering is explicit in
[`native.py:196`](../../packages/ember-qc/src/ember_qc/algorithms/factored/native.py#L196).
For a valid embedding of a nonempty source, ACL is assigned qubits divided by
source-vertex count; the denominator is fixed within a trial. A smaller partial
or disconnected chain map is not a better embedding.

## What the saved 030 observations establish

The existing [030 artifacts](../../results/codex/030-physical-checkpoint-diagnostic)
contain 150 evaluated checkpoints from the three predeclared inputs, all already
independently validated. Every evaluated record reports zero converter misses,
zero completion extensions and zero bridges. These sources have no isolates, and
both arms were seated when the converter reported zero misses. Thus for these
particular observations `Q_wire = Q_seed = Q_constructed`. This conclusion does
not hold generally or merely because the placement's overload is zero.

Re-reading the saved scalars, without executing a solver, gives:

| Input | Evaluated records | Strict proxy improvement but constructed Q increases, successive evaluated records | Strict constructed/pruned ranking reversals among unordered record pairs | Final constructed Q | Final pruned Q |
| --- | ---: | ---: | ---: | ---: | ---: |
| complete-40 | 29 | 10 | 4 | 160 | 156 |
| ER-80 | 64 | 6 | 36 | 323 | 273 |
| grid-64 | 57 | 9 | 28 | 145 | 89 |

For example, complete-40 record 18 has `(constructed, pruned)=(154,151)`, whereas
record 21 has `(156,150)`. On ER, records 5 and 6 give `(437,394)` and `(439,387)`.
The smaller pre-pruning embedding can therefore have the larger post-pruning
embedding. Pair comparisons along one trajectory are correlated, not independent
statistical samples. The three skipped ER records remain unevaluated. Grid's
first two evaluations use bounded projection because their original layouts are
overloaded; counts describe the projected layouts.

Summed converter time already recorded in 030 is 0.224107, 0.893011 and 0.495133
seconds for these three respective sets of evaluations. Corresponding placement
time excluding callbacks is 0.764117, 2.392093 and 1.501154 seconds. These totals
do not measure per-placement-move incremental pricing. The old checkpoint policy
was expensive and provided no sparse-input savings; it is not being promoted.
The saved data identify a real raw-wire mismatch, but also show why correcting
that mismatch cannot be called an exact surrogate for final ACL.

Records retain constructed counts and post-pruning chains, not the full
pre-pruning arm/lane assignment or all checkpoint coordinates. They cannot by
themselves reveal how many converter lines a particular proposal changes.
The raw-result hash-map digest remains
`4d116e101b901f64b5c0f2c91e6f00292348eda4c9c04cbaa5da01eb69d1a541`.

Reproduce the new scalar comparisons from saved results only:

```sh
python3 - <<'PY'
import json
from pathlib import Path
base = Path('results/codex/030-physical-checkpoint-diagnostic/frozen/results')
for name in ('complete_40', 'random_er_80_d8', 'grid_8x8'):
    records = json.loads((base / (name + '.json')).read_text())['diagnostic']['records']
    rows = [r for r in records if 'qubits' in r]
    increases = sum(b['constructed_qubits'] > a['constructed_qubits']
                    for a, b in zip(rows, rows[1:]))
    reversals = sum((a['constructed_qubits'] - b['constructed_qubits']) *
                    (a['qubits'] - b['qubits']) < 0
                    for i, a in enumerate(rows) for b in rows[i + 1:])
    assert all(r['conversion']['convert_miss'] == 0 and
               r['completion']['ext_qubits'] == r['completion']['bridges'] == 0
               for r in rows)
    print(name, len(rows), increases, reversals,
          rows[-1]['constructed_qubits'], rows[-1]['qubits'])
PY
```

## Arm obligations and integer endpoints

Write a source vertex's packed coordinates as `(x_v,y_v)` and its carried
vertical-order rank as `r_v`. Logical edges are assigned by rank, including when
packed coordinates are equal:

```
H(v) = {u adjacent to v : r_v < r_u}
V(v) = {u adjacent to v : r_u < r_v}
horizontal arm: physical row y_v, crossing columns {x_v} union {x_u : u in H(v)}
vertical arm:   physical column x_v, crossing rows {y_v} union {y_u : u in V(v)}
```

See [`_stair_contacts:237`](../../packages/ember-qc/src/ember_qc/algorithms/factored/field.py#L237)
and [`_arm_targets:622`](../../packages/ember-qc/src/ember_qc/algorithms/factored/field.py#L622).
Coordinates are integer-valued after a normal pack. The implementation still
uses Python half-to-even `round`/NumPy `rint`; any general calculator must preserve
that operation for noninteger diagnostic inputs rather than assume truncation.

`plane.books` disables the old degree floor and uses `min_span=0`.
Consequently **every positioned vertex produces both orientation arms**, including
an arm with no assigned logical contact and an isolate's two point arms. Each
such arm still targets its own corner. This follows from
[`plane.py:94`](../../packages/ember-qc/src/ember_qc/algorithms/factored/plane.py#L94)
and the nonnegative participation test in
[`field.py:863`](../../packages/ember-qc/src/ember_qc/algorithms/factored/field.py#L863).
The geometric score instead adds its fixed arm term only when the corresponding
logical-contact set is nonempty. Pruning can remove an entire unnecessary arm.

For course-resolved Zephyr, a physical wire key is
`k=(orientation, line, sublane)`; along-wire positions have stride two and parity
`pi = sublane mod 2`. The canonical mapping is
[`field.py:98`](../../packages/ember-qc/src/ember_qc/algorithms/factored/field.py#L98).
For an integer crossing line `c`, the converter requests

```
f_pi(c) = c - ((c - pi) mod 2)
```

For an arm with crossing set `S`, the implemented required hull is the min/max of
the nonnegative `f_pi(c)` values. If there are none, it uses the separate midpoint
fallback in `_convert_line`. Therefore a formula using just `min(S)` is not
universally valid at the lower hardware boundary.

Under the restricted conditions that both snapped endpoints exist on an intact
chosen wire and no target is discarded at the boundary, let `l=min(S)`, `u=max(S)`
and `D=u-l`. The exact number of qubits in that arm's required interval is

```
N_pi(l,u) = (f_pi(u) - f_pi(l))/2 + 1
           = floor((u-pi)/2) - floor((l-pi)/2) + 1
           = floor(D/2) + 1 + 1[D odd and pi != (l mod 2)].
```

Thus a one-coordinate step can add/remove a qubit or only change parity
preference; span divided by two is not the count. If `D` is even, both parities
have equal length in this restricted interior case. If it is odd, parity can
change the arm count by one. Capacity couples those parity choices among arms
sharing a physical line.

For general existing wire keys, the exact *emitted* count of an accepted range
`[a,b]` is instead

```
N_k[a,b] = number of p in grid.wire_map[k] with a <= p <= b.
```

The current `_lane_ok` accepts only a nonempty set of those positions, all
unclaimed, with successive existing positions separated by the configured
stride. It does **not** require the requested endpoints themselves to exist,
and does not inspect the actual target edge between consecutive wire positions.
Missing endpoints or deleted couplers can therefore invalidate the intended
contact/connectivity certificate without invalidating this counting identity.
Original-graph validation remains necessary. On defective targets, do not replace
`N_k` with the intact-lane formula.

## Physical overlap does not subtract a corner qubit

Two opposite-orientation arms at the same drawn corner use distinct physical
qubits joined by a coupler. They do not share a physical vertex. Different
sublanes also hold distinct physical qubits even when their coordinates agree.
Therefore a successfully seated two-arm chain contributes the sum of its two
arm counts; do **not** subtract one for their intersection in the drawing.

On one sublane, ranges include both endpoints. The converter rejects a new arm
when `lane_busy[s] >= new_lo`, so ranges meeting at the same along-wire position
cannot both occupy that sublane. The claimed-qubit set also prevents stealing an
already assigned qubit. Visual or interval overlap on different sublanes does
not imply physical overlap.

With `n` vertices and both arms seated on intact required ranges, a particular
actual parity assignment yields

```
Q_wire = 2n + sum_over_arms (required_hi - required_lo)/2.
```

If every seat uses the DP-selected parity, with no changed-parity seating,
fallback, boundary truncation or missing arm, this equals `2n + DP_cost/2`.
Those conditions must be checked; they are not guaranteed by the current
converter. The seating stage can try the other parity and then an interval
fallback, and `convert_flips` is currently returned as zero unconditionally.
Neither that counter nor zero `convert_miss` proves the selected and seated
parities coincide.

The geometric second score is `sum(D_arm) + 2*A`, where `A` is the number of
contact-active arms on course-resolved Zephyr. This differs from the physical
formula in its activity convention, integer parity terms, class/lane constraints,
and any fallback effects. Its continuous-span coefficient is not an exact
physical marginal cost.

## A converter feasibility defect independently reproduced

The class DP orders arms by the minimum of their two possible starts
[`field.py:693`](../../packages/ember-qc/src/ember_qc/algorithms/factored/field.py#L693),
but expires stored arms using the current chosen class's start at
[`field.py:705`](../../packages/ember-qc/src/ember_qc/algorithms/factored/field.py#L705).
The chosen starts need not be monotone within a tie in minimum start.

A hand-derived counterexample uses one lane per parity and three identical
crossing sets `{1}`. Every arm's parity ranges are `[0,0]` and `[1,1]` with
zero span. A class history `0,1,0` can drop the first class-zero arm while
processing the middle arm, then admit the final class-zero arm at the earlier
position. It exceeds the real class-zero capacity. No actual assignment can
seat three arms on these two single-position lanes. Greedy seating is still
protected by physical occupancy and can report a miss.

After the static report, root authorized a separate converter-only diagnostic by
the literature agent. Its saved
[034 observations](../../results/codex/034-conversion-capacity-diagnostic/observations.json)
reproduce this case: the DP reports a full assignment with implied three arm
qubits, but independent exhaustive lane enumeration finds no feasible assignment;
actual seating emits two qubits and one miss. An ideal Z12 line with nine
identical point arms also overfills the DP's class capacity and seats only eight.
There is additionally a feasible missed case: crossing lists `[2]`, `[3]`, `[3]`
on one lane per parity have a valid three-qubit assignment `(1,0,1)`, while the
current DP/seater emits two qubits and one miss. The returned physical claims
remain disjoint; incomplete seating is the observed consequence.

The independent diagnostic uses frozen `field.py` SHA256
`6d717696317192ad0df4f0fb6f5a26bb1da0dc4f57408cfad7ac810bb1a1fbfd`.
It does not establish the defect's incidence on full placement trajectories, and
no field or packing change was made by this task. The physical cost calculator
must simulate actual seating rather than treat the invalid DP feasibility claim
as an actual chain count. The separate `conversion_capacity_review.md` records
the broader review and any proposed correction.

## Which pieces a placement move changes

Distinguish a hypothetical fixed-coordinate point move from the implemented
order proposal followed by two global repacks.

For a point-coordinate change with the carried order held fixed:

* Changing `x_u` changes the vertical arm's physical line for `u`, the horizontal
  arm's own target for `u`, and horizontal targets for vertices `v` with `u in H(v)`.
* Changing `y_u` changes the horizontal arm's physical line for `u`, the vertical
  arm's own target for `u`, and vertical targets for vertices `v` with `u in V(v)`.
* An edge whose endpoint ranks reverse changes its two endpoints' assigned arm
  obligations, even if their packed coordinates remain equal.

With cached extrema/contact membership, fixed coordinates and unchanged lane
assignments, this is a bounded neighborhood calculation for a bounded-degree
source. Maintaining only a min/max is insufficient when the removed value was
the sole extremum; a multiset, extremum multiplicities/second extrema, or a local
rescan is needed. It remains only a fixed-lane calculation until capacity and
actual seating are reconsidered.

In the implemented pipeline,
[`align_reinsert:1515`](../../packages/ember-qc/src/ember_qc/algorithms/factored/field.py#L1515)
preserves the rest sequence and interleaves the selected unit with it, possibly
reversing that unit. Vertical-order edge reversals therefore have at least one
endpoint in the selected unit. But coordinates are reassigned from the old sorted
slots, which can shift other vertices too. Then
[`plane.py:405`](../../packages/ember-qc/src/ember_qc/algorithms/factored/plane.py#L405)
packs the moved axis and the other axis. Each pack is a global order-preserving
dynamic program; changing one interval or order position can change contiguous
block boundaries and positions of many vertices.

After both repacks, let `M_x` and `M_y` be the vertices whose actual coordinates
changed, and `E_flip` the source edges whose carried rank relation changed. The
rules above, applied to these sets and to both old and new contact assignments,
give a conservative set of changed arms. It may contain all source vertices.
One selected source vertex does not imply one changed physical chain.

Any changed arm dirties its **old and new orientation/line**. All other arms on
either line must participate in recomputation: parity-state choices and greedy
lane assignment can change downstream, including for arms with unchanged target
sets. Caching just the selected vertex or its source neighbors is therefore not
an exact update of the current converter.

## Exact line decomposition and a possible count-only implementation

Every physical qubit has exactly one orientation/line/sublane key in the canonical
`wire_map`. Before `_ensure_seeds`, claims from other orientation/line pairs cannot
overlap a line's physical qubits. Hence `_convert_line` is a deterministic function
of that line's arm records, crossing targets, and immutable target wire data.
Its output is independent of which other physical lines were converted first.

Define a line signature containing **all** input items `(a,b,v)` in their exact
sort order and each item's exact crossing set. Keep `a,b` even if required hulls
did not change: they affect fallback and the initial item indices used in DP
history tie breaking. An unchanged signature has unchanged pure-wire output.
For dirty line keys `D_lines`, the exact identity is

```
Delta Q_wire = sum(F(new_signature[k]) - F(old_signature[k]) for k in D_lines),
```

where `F` counts what the complete current line algorithm actually seats, not an
unconstrained minimum over individual arm parities. A removed line has zero new
output; a newly used line has zero old output. This identity survives seating
fallbacks and missing arms as a count, but does not assert embedding validity.

There are two possible implementations, neither implemented here:

1. Cache complete line outputs and rerun the existing converter only for dirty
   lines. This is the simpler reference: it avoids unrelated line conversions
   but still materializes changed physical runs and performs line DP/seating.
2. Use a count-only version of exactly the same line DP and seating order.
   Immutable sorted wire positions plus prefix counts of non-stride gaps permit
   `_lane_ok`'s existing nonempty/contiguity/count test by two binary searches and
   a prefix-gap query. Per-lane `lane_busy` ensures accepted intervals are strictly
   separated, so physical claimed-set construction is redundant for this pure
   line-only count. Preserve alternate-parity/fallback attempts and all ties.
   This saves scanning/materializing each range; it does not remove the coupled
   class DP. Cache the actual selected ranges if a later physical certificate is
   required. A defective-target counter must reproduce the existing node-based
   behavior and label physical validity separately.

Pseudocode for an exact *raw-wire* query:

```
price_candidate(old_layout_cache, fully_repacked_candidate, budget):
    identify changed positions and assigned edge orientations
    derive candidate arm records for affected vertices
    dirty = old and new orientation/line keys of changed arm records
    delta = 0
    for line in stable sorted(dirty):
        check one shared work/deadline allowance
        gather ALL current candidate arms on this line
        simulate the existing class assignment AND actual seating
        delta += actual_new_line_count - cached_old_line_count
        retain candidate-only range/count/signature data
    if interrupted: return UNKNOWN; leave all current caches unchanged
    return EXACT_RAW_COUNT(old_Q_wire + delta), candidate_cache_changes

if the geometric state is adopted:
    apply its candidate cache changes atomically
else:
    discard the candidate changes
```

When the cheap budget is exhausted, do not silently substitute an unlabelled
estimate or the previous state's value. A count-query failure must not choose a
different constructor or independent embedding. How an eventual search would
use an unknown value is a separate policy decision requiring prior specification.

The cost is signature maintenance plus the sum of dirty-line DP/seating costs,
not `O(degree(selected_vertex))` in general. The count-only range queries improve
one inner operation but do not establish a speedup for the full pricing call.
If most lines change, recomputation approaches full conversion cost. The existing
alignment/packing objectives depend on additive linearized spans; parity-rounded
costs and coupled lane assignments cannot simply be inserted as replacement
coefficients while retaining their existing optimality arguments.

The current `_convert_line` has no internal cancellation check. A diagnostic
that calls it unchanged can check time between lines, but must report a late
line/query honestly and use an outer watchdog; a line-call count is not a hard
deadline guarantee. An eventual bounded count-only implementation would need
checks inside DP-state transitions and seating as well as atomic cache commits.

## Why completion and pruning break a cheap exact final-cost claim

`_ensure_seeds` visits empty chains in sorted source order and searches for the
nearest unclaimed physical vertex among its bounded candidate horizon
[`field.py:517`](../../packages/ember-qc/src/ember_qc/algorithms/factored/field.py#L517).
The available set depends on *all* wire claims and earlier point seeds. A local
wire change can displace a remote fallback choice. An exact cache must either
prove no chain is empty or reconstruct this shared occupancy/seed process; it
cannot preserve old point seeds as frozen obstacles while claiming equivalence
to full conversion, because full conversion claims wires before point seeds.

Completion visits corners, then sorted logical edges, then residual bridges
[`field.py:943`](../../packages/ember-qc/src/ember_qc/algorithms/factored/field.py#L943).
It extends runs through globally free qubits, rechecks live contacts and commits
choices immediately. Earlier extensions can cover later edges incidentally, or
block a later extension/bridge. A changed wire can therefore alter an arbitrarily
long suffix of completion decisions. Restricting completion to incident source
vertices would be a different algorithm, not an exact reproduction of its count.
Its aggregate `bridges` counter also does not distinguish one from two added
qubits, so counters alone do not reconstruct an arbitrary raw-to-completed delta.

There is one useful restricted certificate: if the old raw wire embedding is
valid and the changed line outputs also leave every changed chain connected and
every logical edge incident to a changed chain coupled, the raw candidate remains
valid. Unchanged chains and external contacts retain their certificates. Completion
then has nothing to add. The changed chain set includes **all** chains recolored
on dirty lines. Its connectivity/contact checks can use actual adjacency and
current owners, but may cost substantial work when packing changes most chains.
Zero geometric overload, zero pack misses or zero conversion misses alone is not
this physical certificate.

Pruning tests actual chain connectivity and live neighboring contacts, repeatedly
in sorted order, until a fixpoint or deadline
[`polish.py:45`](../../packages/ember-qc/src/ember_qc/algorithms/factored/polish.py#L45).
Deleting one qubit can change what a neighboring chain can later delete. Distinct
lane assignments with equal raw cost may also have different redundant couplers
and therefore different pruning outcomes. Full line range counts do not determine
those outcomes. The strict pre/post ranking reversals in 030 are direct empirical
counterexamples to equating the two objectives.

Overloaded layouts require special care. The search permits off-chip positions;
its final retained state is projected with bounded axes `0,1,0` if needed
[`plane.py:451`](../../packages/ember-qc/src/ember_qc/algorithms/factored/plane.py#L451).
That projection is another global transformation. Raw counts of the unprojected
layout price a different state and may be artificially small when lines cannot
seat arms. Keep overload/validity status explicit; do not call this a global ACL
surrogate or reward a failed construction for emitting fewer qubits.

## Self-critique before any implementation or new diagnostic

The separability proof is useful but limited: it removes cross-line interactions
only before point seeding/completion. Global repacking may erase practical
locality, and the residual per-line dynamic program may dominate even a count-only
version. Cached minima and a parity formula alone do not price current seating.
The reproduced class-DP issue further requires separating simulated output from
an asserted optimum.

Exact raw cost could improve a geometric bookmark while worsening its final
pruned/contact-repaired embedding. It may mainly reward the two-arm construction's
own allocation convention, retaining avoidable inactive-arm qubits that the
ultimate metric removes. A smaller raw incumbent is not enough to justify a
production policy or publication claim. Conversely, a useful approximate physical
term need not be exact, but should be called approximate and tested independently.

Caching target-dependent ranges adds invalidation obligations for position changes,
edge-orientation changes, line membership, tie ordering and hardware identity.
Reusing a cache after only comparing scalar counts would be unsafe for later
validity checks: equal counts can describe different actual qubits. Failed budget
checks must return no answer atomically. Missing or stale entries cannot be
silently accepted as the current count.

Experiment 023 already showed that a stronger isolated proposal can lose because
it consumes cumulative search coverage. Experiment 030 showed that observing
physical quality can itself be expensive. This design must pass both equivalence
and useful-cost tests before changing the geometric search. No family-specific
exception or per-input selector is proposed.

## Falsifiable bounded next diagnostic, not yet authorized or run

First finish reviewing the independently authorized tiny converter-capacity evidence. Any
calculator must then target a clearly frozen converter revision and its actual
seating behavior; a future converter fix would require its own validation and
must not be silently folded into a pricing comparison.

For locality/cost, use the same three exact serialized 030 sources, ideal Z12,
random initialization, seed zero and 1,000 asks. Freeze source/inputs. Instrument
one unchanged placement trajectory in memory to observe its initially packed
layout and **first 32 adopted, fully repacked proposals** in chronological order.
Do not select favorable move sizes or record scores. Keep singleton and larger
selected-unit statistics as descriptive strata afterward, with every sampled
transition retained. The instrumentation must not change proposal acceptance,
initialization, scheduler, current state or returned embedding.

For each sampled transition, record selected-unit size, changed `x`/`y` vertex
counts, flipped logical-edge count, changed arm count, dirty line count/fraction,
all chains affected by those lines, and old/new proxy values. Build a complete
baseline per-line cache once. Compare each incremental candidate against a full
unmodified converter evaluation of the same candidate: exact physical chain
multisets before `_ensure_seeds`, exact counts, assigned ranges, misses and
seeding/validity status. Include explicit boundary, missing-node and equal-start
fixtures for any count-only implementation. An interrupted calculation must
preserve the baseline cache and return `UNKNOWN`.

Measure warm incremental signature, line DP, seating/count and physical-certificate
time separately, plus total query time. Preserve cold import/JIT preparation as a
separate measurement; adding Python arithmetic requires no new JIT claim. Compare
with both full conversion and the corresponding unmodified placement-transition
cost, not with a cold reference run. A shared deadline/work cap applies to every
query; diagnostic instrumentation time is reported rather than excluded from an
eventual production budget.

Any raw-chain/count mismatch falsifies the proposed exact update. If incremental
queries cost at least full conversion, reject the locality/speed claim. If their
aggregate extra cost exceeds 10% of corresponding placement-transition time,
defer per-proposal use as insufficiently cheap under the current runtime problem;
retain every case and avoid changing that threshold after looking at results.
Passing these checks would establish only an exact, bounded raw-cost observation,
not a better search policy or final embedding quality. Such a policy would still
need a separate globally fixed full-pipeline experiment.

Status: this note contains source-derived equations, saved-data analysis and a
future diagnostic design. No field/plane/native code was edited, no calculator
implemented, and no new embedding run performed by this task.
