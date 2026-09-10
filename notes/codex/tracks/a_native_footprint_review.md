# A constructor review: pack only contact-supported arms

2026-09-10 UTC. **Before-code proposal for root review, not implementation
authorization.** Replace an unnecessary footprint in the inherited native
constructor, while retaining its single layout trajectory and A061's surrounding
construction. An arm with no assigned contacts should consume neither a wire
slot nor conversion qubits. A vertex with only one active arm should not extend
that arm to an otherwise unused artificial corner. This changes packing before
first validity; it is distinct from the stopped A063–67 cleanup sequence and
from C019's joint placement of stars.

## What the source and completed evidence establish

A061 calls A053 once. A053 eliminates eligible degree-at-most-three vertices,
constructs its filled core with `native_embed` at most once, then lifts the
journal. An edgeless core uses direct anchors and bypasses native. Native uses
two spectral source orders, monotone line packing and interleaving search, then
one wire conversion/completion, pruning, contact refinement and vacancy cleanup.
No MM/busclique call or alternative completed constructor is proposed here.

The relevant restriction is verified in current source:

* `plane.books` uses `min_span=0`; `arm_books` therefore creates both orientation
  records for every positioned vertex, even when one contact set is empty.
  Packing reserves a nonzero physical footprint for each such point arm.
* `_stair_contacts` assigns each source edge by one carried y-order: the earlier
  vertex's horizontal arm contacts the later vertex's vertical arm. Every hull
  and `_arm_targets` includes the owner's own coordinate, including a sole arm
  that needs no bend to another arm.
* The layout score is overload followed by coordinate spans plus one stride per
  **contact-active** arm. It is not converted Q and does not price an inactive
  arm. Physical parity, lane seating, completion and pruning intervene later.
* The search already accepts feasible repacked worsening states and retains a
  separate best geometric state. Its two-arm representation is a restriction on
  this layout stage, not on the arbitrary connected final maps after refinement.

The following reported scalars come from six existing, root-audited A061 calls;
no constructor or reader was rerun. `A` is the saved number of contact-active
arms; `2c` is the number booked by the inspected code for core size c. Core
Q after refinement is its saved vacancy-stage endpoint, before lifting. These
different graph/cohort observations are not paired runtime comparisons.

| Input | c; active / booked arms | Constructed → pruned → final core Q | Final A061 Q | Layout s; asks |
|---|---:|---:|---:|---:|
| g0013 grid128 | 106; 137 / 212 | 248 → 175 → 142 | 168 | 6.009; 1000 |
| g0014 honeycomb190 | 90; 125 / 180 | 222 → 164 → 136 | 240 | 5.215; 1000 |
| g0102 BA100 | 59; 85 / 118 | 199 → 161 → 143 | 282 | 5.501; 1000 |
| g0302 BA96 | 96; 140 / 192 | 392 → 329 → 290 | 290 | 7.096; 1000 |
| g0307 singleton control96 | 75; 123 / 150 | 285 → 257 → 238 | 266 | 5.714; 1000 |
| g0308 branch control96 | 75; 120 / 150 | 210 → 180 → 155 | 177 | 3.607; 1000 |

All six report zero overload at the returned layout, zero converter misses,
zero completion deficits and no added completion sites. All spectral outputs
meet their reported residual tolerance; that is not an optimal-layout
certificate. Layout admits worsening moves in every case and stops at its
1000-ask limit, not a fixed point. The inactive bookings are substantial across
different source structures, including unreduced BA96 and the zero-fill
singleton-control core. Thus another fill threshold does not address this
restriction. Initial pruning savings are **not** savings available to add to
final Q: the existing pipeline already obtains them.

The earlier [A040 audit](../experiments/040_results_review.md) reconstructed
1,122 saved geometric states with valid raw physical maps. Cached conversion
of 1,088 transitions cost 24.8823 seconds versus 10.7990 for their geometric
transitions. This supports avoiding physical conversion at every proposal;
its old 10% gate is not a universal runtime rule. Those captures concern
full-source layouts, not these unsaved filled-core positions. Their correctness
and zero misses do not show that unused reservations leave packing freedom
unchanged. Conversely, the [physical cost review](../physical_cost_model.md)
already explains pruning of inactive arms: lower raw Q alone would repeat that
known observation. The required new evidence is a better complete constructor.

The [core/lifted attribution](../strategic_fill_diagnosis_results.md) locates
much grid/honeycomb excess on retained core owners and a BA deficit without any
reduction. It also shows a wheel that bypasses native and a planar win. A
native-only change cannot claim to address all of those regimes. Neither the
old final-map partition nor the table above recovers missing initial positions
or proves that this particular footprint caused an MM gap.

## Exact proposed footprint and search contract

Keep the existing y-rank edge assignment. Let H(v) and V(v) be v's neighbors
assigned to its horizontal and vertical arms. An orientation is active exactly
when its set is nonempty. Define support sets of **source vertices whose
coordinates an arm must reach**:

```text
both H(v), V(v) nonempty: Sh(v) = H(v) union {v}; Sv(v) = V(v) union {v}
only H(v) nonempty:       Sh(v) = H(v);           Sv(v) = empty
only V(v) nonempty:       Sh(v) = empty;          Sv(v) = V(v)
both empty:              no wire arm; later allocate one free site to the isolate
```

A horizontal arm lies on row y(v), spanning x-coordinates of Sh(v); a vertical
arm lies on column x(v), spanning y-coordinates of Sv(v). Build parity-agnostic
capacity intervals and exact parity-specific conversion targets from these same
sets. A nonempty singleton support still consumes one physical site/slot; zero
span must never mean zero occupancy. Retain existing actual Z12 line capacities,
boundary treatment, corrected parity-class assignment and physical lane seating.

When both arms exist, retaining v in both support sets preserves their corner
obligation. Opposite-orientation corner qubits are distinct and must have an
actual coupler; completion and the existing validator still check this. When
only one exists, no such connection is required. Each source edge still joins
the earlier endpoint's active horizontal arm to the later endpoint's active
vertical arm at their required crossing. The target's actual couplers and final
oracle, not a drawn intersection, decide success. No same-orientation contact
capability or arbitrary branching is newly claimed by this proposal.

Use the new support span plus the unchanged stride per active arm as the layout
objective, preceded by the existing overload count. It remains a surrogate.
Monotone packing coefficients are the min/max support-coordinate coefficients
under the carried axis ranks; omit absent supports. Every x-coordinate appearing
in a horizontal support belongs to a vertex with an active vertical arm, and
conversely for y. Thus a coordinate not assigned by active-arm packing has no
effect on the physical support objective; retain its deterministic carried value
without treating it as an occupied line. Isolates remain subject to actual free
site availability and failure accounting.

The interleaving recurrence must change consistently, not just the final score:

* On x moves, contacts and active supports are fixed. Price the span of each
  horizontal support hyperedge by whether it crosses each placed-prefix cut.
  The vertical part is constant, as before.
* On y moves, let P be the placed prefix. An **unplaced** owner v contributes
  vertical span across the next slot gap exactly when
  `0 < |N(v) intersect P| < degree(v)`. Once all its neighbors have been placed,
  it will be vertical-only and its interval already ends at the last neighbor;
  the old rule incorrectly extends the required support to its own later row.
* When v is placed, L and U are its already-placed and still-unplaced neighbors.
  Charge its horizontal span over `U union {v}` if both are nonempty, over U
  if only U is nonempty, and zero otherwise. Charge the fixed active-arm terms
  `stride * (bool(L) + bool(U))` at that transition.

All these values depend only on P and the vertex being placed. P is fixed by
the two interleaving-prefix indices, so the recurrence remains valid for each
existing forward/reversed block subproblem. Apply the same support definition
to the existing rank-span tie-break; the old `2*n*n+1` dominance bound remains
safe because there are at most 2n supports, each with rank span below n. This
is an exact subproblem claim to check, not exact physical-Q optimization.

Every y-order proposal can change arm activation. Rebuild contacts, supports,
capacity records, packing coefficients and conversion targets together; retire
old line reservations. Repack the moved axis and then the other axis with the
same supports, as the current constructor does. No book or capacity cache may
survive an activation change unless its full support identity is unchanged.
Keep current feasibility filtering, acceptance and best-state retention.

```text
run one A061-derived pipeline with its native-core entry replaced
    same reduction, spectral orders and seeded layout scheduler
    derive active supports; pack their actual claims
    search the same interleaving move family using the revised support cost
        rebuild both-axis packing after each changed order
        retain one best geometric state along this trajectory
    convert only active supports once; complete and validate
    run the same pruning, contact/vacancy cleanup, lifting and A061 path stage
return the one complete validated embedding, or the ordinary explicit failure
```

## Ablation, implementation boundary and risks

**Inactive-booking ablation:** use the same new support objective, sole-arm
corner omission and active-only physical conversion, but add the old inactive
point-arm reservations to packing/overload accounting. They are conservative
virtual reservations only and must never be emitted as disconnected physical
arms. This control isolates the earlier capacity/placement restriction; it does
not duplicate A061, which also emits those arms. Constant policy per call, with
no runtime choice between outputs. The full candidate versus A061 measures the
coherent footprint package; full versus ablation tests booking's contribution.

Proposed isolated files: `contact_footprint_layout.py` for supports/books/score
and the adapted layout loop; `contact_footprint_kernels.py` for the revised
interleaving pricing; `contact_footprint_conversion.py` for active-only targets
and conversion orchestration; `contact_footprint_native.py` for an isolated
native wrapper; `contact_footprint_construction.py` for isolated A053/A061 entry
wrappers and the constant ablation. Preserve all current files. Reuse spectral
initialization, hardware indexing, existing packing recurrence, corrected
`_class_interval_assignment`/`_convert_line`, completion, pruning, original
contact/vacancy operators, reduction/lifting and final validators. If an existing
helper embeds the old support assumption, copy and adapt it explicitly instead
of monkey-patching shared state. No new numerical/global IP solver is needed.

Few new checks are warranted: actual-coupler single/dual-arm and isolate cases;
small independent enumerations of the changed x/y interleaving cost with ties
and activation changes; equality of packing/conversion support identities and
the booking-only ablation; interrupted preparation/publication preserving a
complete prior state or an explicit failure. Reuse dependency isolation and the
independent minor oracle. Do not repeat the old exhaustive converter campaign.

**One self-critique.** Pruning already removes inactive arms, and packing may
already have enough spare capacity; removing their earlier reservations could
change nothing useful or concentrate active claims in worse locations. The new
score still ignores exact parity and usable side contacts, and the global y
assignment still excludes many compact contact patterns. The revised objective
can remove useful geometric guidance or increase search cost. Later core repair
and lifting may erase or reverse any raw gain. This is a plausible packing
mechanism, not established novelty or evidence that it will close class gaps.

## Cheap falsifier and complete screen for review

A tiny fixed-layout source edge suffices to falsify the support semantics:
u at (2,2), v at (8,8), u earlier in y. The only required arms are u's horizontal
site at column8 and v's vertical site at row2. On suitable intact Z12 lanes they
are two distinct coupled sites; neither must reach its unused old corner. Add
a path order that makes its middle owner dual-arm, then changes that activation.
This tests actual paths/couplers and packing claims, not benchmark performance.
Old pruning can also reach the two-site result, so success is only a correctness
gate. No saved-map optimization campaign is needed before complete construction.

Propose twelve existing encodings, eleven structures: grid g0013, honeycomb
g0014, BA100 g0102, BA96 g0302 and relabel g0309, regular96 g0303, WS96 g0304,
controls g0307/g0308, and ER160/SBM160/wheel anchors g0007/g0011/g0015.
Four separate methods—full footprint, inactive-booking ablation, retained A061,
pinned MM—give 48 calls on one host, seed0, within the existing 60-second
envelope. Root must freeze the exact protocol before execution. No new inputs
or held-out confirmation set are created here; these are exposed development
examples. Wheel explicitly tests a native-bypass case and stays in accounting.

**Allocation decision for this first screen:** label it explicitly as a
controlled **1000-ask comparison**, preserving the old exposure for attribution.
This cap is not a proposed final default or a demonstrated quality ceiling:
all six saved layouts stop there at 3.6–7.1 seconds, with useful later search
unmeasured. Apply the same count to full and booking-ablation arms, record the
last improving geometric bookmark's ask/time and report every cap stop as
unfinished search. Do not add a new operation-count limit.

For both new arms, at native-core entry set a geometry deadline `D - R`, where
D is the original call deadline and `R = min(10 seconds, remaining_wall / 2)`.
The six observed complete solver-wall-minus-layout costs span 1.756–6.093
seconds, including conversion/completion, core refinement, lifting and A061's
path/final stage. Ten seconds is an explicit starting reserve above that
observed maximum, not a probabilistic guarantee or a claim covering every
source. Existing records do not separately expose all conversion costs; add
only adjacent stage timestamps in the isolated wrapper, reusing its actual
validation calls. Compilation and failed work remain charged. A cooperative
operation may overrun its reserve or deadline; preserve that outcome.

After layout, all surviving call wall is available to the unchanged downstream
pipeline, under D. There is no forced spending of unused time and no A067
postprocessing tail. If no complete map can be finalized in time, report the
failure/timeout normally. Native's first successful existing check certifies
only its core input; record its timestamp as a core handoff, not first validity
for the full source. Full-source validity is observed only after the normal
expansion/final checks. A binding reserve is recorded separately from the
1000-ask limit and can confound an unqualified equal-exposure claim.

If complete evidence supports further exposure—for example the footprint
mechanism improves final quality and still improves its geometric bookmark
near its count stop—propose **one separately frozen 12-call allocation screen**
on grid g0013, honeycomb g0014, BA100 g0102 and singleton control g0307. Compare
the same full footprint algorithm at 1000 asks versus **no ask cap**, plus fresh
MM, on one host. Both footprint arms retain the identical reserve, acceptance,
downstream code and 60-second outer deadline; the uncapped layout stops at its
ordinary fixed point or geometry deadline. The experiment asks whether extra
layout computation improves final ACL enough to justify later first validity
and runtime, not whether a proxy improves. No output selection or new budget
framework is needed. A rejected first policy remains rejected; any such
follow-up requires its specific completed evidence and root review. Do not
infer a universal cutoff or MM multiplier from either allocation.

Proposed continuation requires no success/Q loss against A061 or the ablation,
and meaningful complete gains on several structures. A concrete threshold for
root review is one-third closure of A061's positive paired-MM Q gap in at least
two different structural families, plus Q benefit over the booking ablation on
two structures. Gains confined to lower constructed Q or fewer deleted arms
reject the mechanism as a complete-constructor improvement. Preserve dense
losses, relabel sensitivity, within-chain variance and unknown across-seed
variance. Record first valid core/full handoff and final ACL trajectories where
the wrapper observes them, plus every setup, conversion, compilation, failed
proposal and finalization cost. No intermediate metric alone authorizes further
footprint or ordering adjustments.

Prior overlap is explicit: spectral initialization (026/032), converter repair
(034–036), post-conversion deletion and vacancy (042–048), source reduction
(049 onward), geometric checkpoint pricing (030/038/040) and packed-orientation
selection already exist. This proposal changes neither spectral seeds nor fill
eligibility, and does not choose among converted checkpoints. Old handoff
orientation-flip outcomes are unverified history; independent source-edge
orientation flips are not part of this design. The active-arm score is also
old; the proposed change is removing inactive **capacity obligations** and
unused sole-arm corner requirements coherently before conversion.

Current reviewed source SHA256: native `496b54221c2ea77710dc6979fc7f9a202af995c51d029134bdbe6b703764a225`;
plane `5459df9e949df9b0b2e855f100361770b054523542a67c06ece50cbfa1b9b1e8`;
field `a055553988ba3db17ef3588986c1719070c3fcfae4bbfcce7a7084ffe45c7690`;
A053 `801432d5e5d1fc1918e7eb933a3af443064ee0833030a5b962773f2b50f700a1`;
A061 `3d2f6672e51a450a24a360bb562d9f6c44c325c92130d74c23c4bb505592da9b`.
The six scalar records are A066-initial archive tasks eeb37b30b541ba2e6beed941 /
f28d3d4fed4b8d236c9d2a28, A066-broader a6286b4e2581e349aaa26f1c, and A067
accad2638abe6a9ba6803cfa / 3ce4323f292d9ab7438c3ddc / b8bb8248fa7ca3cdcec1b8ed.
Their existing completed common audits own validation and provenance. This note
adds no source edits, input generation, candidate/reader calls or validation.
