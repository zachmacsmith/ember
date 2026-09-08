# Review: physical-line locality along the spectral placement trajectory

Design only, before diagnostic implementation or observations. This is a new
all-34-input, spectral-initialization diagnostic; the three random-initialization
inputs in [030 and the earlier cost model](physical_cost_model.md) supply the
motivation, not observations for this protocol. Nothing changes experiment 039,
the candidate objective, or its placement/refinement policy.

The question is whether **exact replay of the current raw wire output** usually
needs substantially fewer line conversions after an adopted placement move.
It is not whether that output predicts final ACL. Use initial packing and the
first 32 adopted, fully repacked states, including equal/worse geometric scores.
Continue the original search after observation 32, up to its unchanged 1,000 asks
or existing earlier stop. Physical evaluations take place only after capture.

## Frozen source and observation boundaries

Use the 48 files from frozen 039, snapshot
`63a0aed1a880cbf008aa68ae7201aed7a4da635dea9362e5d296b1d13a91a473`,
already copied with all 103 original/label/normalized/target files and both
selection ledgers to
[`040-physical-locality/prepared`](../../results/codex/040-physical-locality/prepared).
The preparation's 153-file map digest is
`a5ddbd44613f37ebfa63c2e4232920573775fd3727e647dedce0b968b945bdcf`.
Preparation is not a diagnostic freeze or launch authorization. Independently
verify every byte, original source-node iteration order, normalization mapping,
and the single ideal Z12 target before the eventual diagnostic freeze.

Workers consume the exact frozen `evaluation/expected_normalized/<key>.json`
record in its canonical `0..n-1` insertion order, as 039 did. Original graphs
and inverse label maps are evaluator-only. In particular, the valid label map
for `ember_37761` does not follow its original JSON node insertion order;
reconstructing a worker graph directly from that original order would change
the seeded search. Recording original order does not authorize using it as
the native input order.

The following line identities refer to that frozen source, not a moving checkout:

| Source | Relevant boundary |
| --- | --- |
| `native.py:168–199` | Preserve insertion-order native labels, sorted adjacency, target/grid construction, spectral initialization, scheduler seed 0, `snap=True`, and `max_asks=1000`. |
| `plane.py:365–372` | Initial three packs `(1,0,1)`, score, and first `best` assignment. Capture immediately after this assignment. |
| `plane.py:388–436` | Actual proposal, moved-axis pack, other-axis pack if the first succeeds, score, adoption and bookmark update. Capture after the whole adoption/bookmark block. |
| `plane.py:437–482` | Continue unchanged to the natural stop, including its existing final projection when necessary. Record the return for replay checking; it is not an additional observed proposal. |
| `native.py:196–209` | A wrapper obtains the complete `arrange` return, then terminates this diagnostic invocation before native conversion, completion or refinement. |
| `field.py:622,700,801` | `_arm_targets`, `_convert_line`, and full wire conversion through the point immediately before `_ensure_seeds`. |

Initial packing may remain overloaded. A proposal is observed only after both
packs succeed and adoption actually occurs; the code adopts every feasible
proposal, not only a new best score. Do not project an observed state, replace it
with the best bookmark, or call an overloaded state's small chain count a gain.

## Minimum data, ordering and independent reconstruction

For a pure `_convert_line` replay the sufficient arguments are its orientation,
line, complete item list, per-item target lists, immutable `wire_map` and stride.
For an independently auditable diagnostic, retaining only callback-generated
arguments/signatures is insufficient. Save these underlying data:

* Once per input: exact original source/target and label map; native adjacency;
  complete wire-map keys, along-wire positions and qubits; stride and grid
  dimensions; source/grid/environment hashes; source iteration orders.
* Each observation: the ordered `pos` entries with exact coordinate float bits;
  both carried vertex orders; complete books, including contact lists, bars and
  orientation tuple lists with their order and exact numeric values; current
  score, misses, ask/adoption/pass counts and moved axis/unit. Initial observation
  has no moved unit. Record initial spectral orders and final non-time state.
* Provenance: common/native deadlines, seed/configuration, actual proposal stream,
  call order, capture count and copy timings; actual counts of converter,
  completion, pruning and refinement calls during geometry must all remain zero.

Copy only these at most 33 states in the live capture hook; no conversion, graph
validation, filesystem serialization or derived line signatures there. Keep
serialization and original-graph checks outside the geometry invocation and
report their wall time separately. Copies themselves remain inside its deadline.

Offline, independently reconstruct contact obligations from original adjacency
and carried y-order rank, not packed-coordinate order. Reconstruct target sets
from those contacts and positions using the original half-to-even rounding.
Compare them with the recorded books before pricing. Retain the actual tuple
endpoints: `arm_books` uses `snap=True` widening and the minimum occupancy span,
so tuple `(a,b)` need not equal the stored bar endpoints. A book reconstruction
must use these same rules and bounds (`ybound=False`), not an inferred hull-only
substitute. Any discrepancy is an instrumentation/reference failure.

Define each line signature as its orientation/line, full **sorted `(a,b,v)`**
items, presence and full sorted crossing targets for every item, and the fixed
wire-map/stride identity. Preserve repeated items and numeric bits. `a,b,v`
affect fallback and DP/seating ties even when the required spans agree. Counts,
span extrema or selected-unit identities alone are not sufficient signatures.

## Exact decomposition and dirty lines

Verify once that every represented physical qubit occurs under exactly one
orientation/line/sublane key. Then a line cannot encounter physical claims from
another line. With this precondition, the unchanged converter is a deterministic
function of the complete line signature, including its actual seating failures.

Let `F_k(S)` be the ordered per-vertex chain fragments and counters emitted for
line `k` from signature `S`. Between consecutive captured states, define

```
D = {k in old_keys union new_keys : old_signature[k] != new_signature[k]}
Delta Q_wire = sum(Q(F_k(new)) - Q(F_k(old)) for k in D)
```

A missing line emits no fragments. Reconvert **all arms of each dirty line**;
changing one arm can change the assignment of otherwise unchanged arms there.
Global repacking can change many coordinates, and carried-order changes can
change contact assignments even when coordinates tie. Therefore dirty lines
cannot be restricted to the moved unit or its incident source edges.

Merge cached fragments in the original outer order: orientation `(1,0)`, then
ascending line, retaining each local emitted list order. Initialize chains with
every position key in its original iteration order, including empty chains.
For the independent full reference, stop frozen `wire_seeds_exact` immediately
before `_ensure_seeds`; compare complete ordered raw chains, claimed qubits and
both counters, not only Q. The current second counter is always zero and is not
evidence of unchanged seated parity. An unchanged signature must have identical
output; a changed signature may still emit identical fragments.

The validated 035 correction is present in this source: the class DP uses a
shared monotone frontier and complete closed-interval overlap checking. Do not
reuse 034's defective recurrence or treat its historical failure as current.
The corrected class optimum still does not solve physical-lane placement exactly;
seating can change parity, use fallback, miss endpoints or miss arms. Its state
growth is potentially exponential, and its `0.0` accumulator's exact-integer
qualification remains (the declared Z12 ranges satisfy it).

## Bounded implementation protocol for review

1. Freeze new diagnostic code, original/restored/transformed AST identities,
   environment and all prepared files under `results/codex/040-physical-locality`.
   Use the MM/busclique-blocked native environment, one host, serial inputs in the
   frozen ledger order, no saved embeddings. First run only synthetic hook,
   mutation, ordering, deadline and supervision checks. Root review precedes
   any corpus invocation.
2. Per input, use one fresh worker and at most **two** geometry invocations:
   reference first, capture second. Each gets its own unchanged 60-second common
   allowance, spectral seed 0 and 1,000 asks. Preserve all native setup and abort
   only after `arrange` returns. Reference retains the original function body;
   capture adds the two reviewed copy hooks. Removing those hooks must restore
   the original AST exactly. Neither run is truncated at 32 adoptions.
3. Both invocations use identical read-only helper wrappers and `trace=True` to
   record existing accepted trace, yielded units and actual `align_reinsert`
   invocation/return sequence (including full returned orders and failure
   results). Hash their stable serialization; do not consume or clone extra RNG
   draws or prefetch the unit generator. This is an **instrumented reference
   environment**, not a claim of completely uninstrumented wall-time measurement.
   Record wrapper overhead separately. Compare full final non-time geometry,
   books, orders, layout counters/trace and actual proposal-stream hashes.
4. Enforce an absolute 150-second worker backstop for both geometry invocations
   together, with an external process-group timeout and five-second cleanup
   grace, inherited run lock and atomic no-clobber observations. The worker's
   fatal alarm must not reset between invocations. Preserve initialization
   failure, late return, partial capture and missing observation explicitly;
   never retry an input automatically. Snapshot serialization has no exemption
   from the process allowance.
   Publish the reference record before beginning capture. A fatal alarm can
   destroy unflushed RAM-only snapshots; mark those missing, without claiming
   that every interrupted capture is recoverable.
5. Offline, give each input a separate **60-second analysis cap** and at most its
   33 recorded states in a new supervised process. Arm its fatal alarm before
   heavy imports and input decoding; the same 60 seconds includes that setup,
   validation and replay. Use an external timeout with five-second kill grace.
   Never reset the geometry alarm or use its leftover time for this phase.
   Validate snapshot schema and immutable inputs, then run
   one complete raw-converter reference and one incremental-cache evaluation per
   state. Initialize the cache by converting all initial lines. For subsequent
   states, derive all signatures independently, reconvert dirty lines and merge.
   Alternate full-first/incremental-first by state index after the initial state;
   never select an order from observed cost. There are no extra repetitions or
   full embedding calls. Use cooperative boundary checks plus a process alarm
   and external cleanup because a line DP itself has no deadline check.
6. Publish a cache update only after all dirty lines finish and the complete
   ordered result equals the full reference. On failure/timeout, keep the last
   complete cache and terminate that input's incremental sequence, preserving
   completed and partial records. Missing lines/states are unknown, not zero
   work, zero qubits or verified reuse. Record the interrupted line/stage and
   suppress incomplete aggregate speed ratios.
7. Independently check raw-chain source coverage, physical-node membership,
   duplicates/ownership, connectivity and every original source edge. Preserve
   all failures and empty chains. No `_ensure_seeds`, completion, pruning or
   contact repair is authorized in this diagnostic. Raw Q remains a raw count
   even when that particular chain map passes validation.

Only paired runs that both finish before their deadlines with identical complete
traces and final non-time state support an observed noninterference statement.
If capture changes a deadline stop, retain its snapshots for explicitly labeled
locality analysis but do not assert replay of the reference trajectory. Equal
60-second limits are necessary, not sufficient. The final projection is audited
as original search behavior but is never inserted into the adopted-state series.

## Measurements and decision limits

Retain per input/state/line: arm counts; changed positions, ranks and signatures;
dirty/total line counts; actual changed fragments; emitted Q and misses; physical
validity; complete full/cache equivalence; signature-building, dirty conversion,
merge, reference and verification times. Report initial cache construction
separately and included in amortized totals. Report timing-weighted dirty work,
not only the fraction of dirty lines: the class DP has highly nonuniform cost.

Reference-first timing includes first-call initialization/JIT effects; the
second capture is only a **same-worker second invocation**, with actual warmness
and environment recorded. It is not a clean cold-versus-warm speed experiment.
Measure capture proposal work from the actual align call through its successful
packs and score/adoption, with recording time separate. Offline incremental
cost divided by this measured second-invocation transition work is a descriptive
cost ratio. Keep all setup, initial packing, spectral, wrappers, copying,
serialization and verification totals visible. Never subtract overhead to
invent a solver budget or call a late result timely.

Define incremental update cost as signature construction, dirty-line conversion,
candidate-cache work/merge and commit bookkeeping. Exclude diagnostic full
reference conversion, equality checking and original-graph verification from
that deployable-operation subtotal; report each separately and include all in
total diagnostic cost. A staged cache is published only after timely equality
checking succeeds. A mismatch or expired comparison discards it and preserves
the last complete cache. This diagnostic validation gate is not a proposed
production double-conversion policy.

Retain the earlier cost model's fixed falsifiers: any unexplained full/cache
mismatch rejects exactness. If aggregate incremental update cost is at least
the corresponding complete-conversion cost, reject a speed benefit. If aggregate
updates exceed 10% of the corresponding captured adopted-transition work, defer
per-proposal use as insufficiently cheap. Report initial cache construction and
all setup separately and in amortized totals; the 10% comparison concerns the
post-initial updates and their corresponding adopted transitions. Zero-transition
inputs have no such ratio. Missing/timed-out analysis precludes an all-input
cheapness claim, and no failed input may be dropped to meet a threshold.

These ratios concern adopted proposals only. An eventual proposal objective may
need to price rejected proposals as well, update acceptance behavior, and maintain
its cache after every adoption. Consequently even large offline savings cannot
establish an end-to-end speed or ACL improvement. Report each of the 34 inputs
and all incomplete cases; do not pool away failures or select promising families.

## Self-critique and falsifiers

The exact decomposition does not imply useful locality: two repacks can dirty
most lines, while signature construction alone scans source-scale data. A few
expensive dirty lines can dominate even when most cache entries survive. The
corrected DP's worst case can exhaust the offline cap. Any unexplained full/cache
mismatch falsifies the implementation's exact-replay claim; frequent broad dirty
sets or little measured cost reduction reject the proposed computational benefit.

Instrumentation itself can perturb timed trajectories. Common wrappers, fixed
quotas and trace comparison expose this risk but cannot remove it. Complete
results may be biased toward cheaper sources; coverage is therefore a primary
reported outcome. Thirty-two early adoptions do not establish late-search
locality. Finally, exact raw-wire pricing can favor incomplete layouts and can
misrank post-pruning embeddings, as 030 already demonstrates. This diagnostic
can justify or reject further cost-model work; it cannot justify promoting a
physical objective or another refinement policy.

Remaining implementation choices are mechanical: choose one stable binary
snapshot encoding, fixed process-supervision implementation and precise timer
boundaries; save them before execution and verify them synthetically. No new
algorithm option, family dispatch, source edit, solver call or outcome-dependent
threshold is authorized by this review.
