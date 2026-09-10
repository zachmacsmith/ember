# A068 implementation review and narrow design amendment

2026-09-10 UTC. **Prepared for root review; no candidate or check has run.**
The approved before-code contract is
[a_native_footprint_review.md](a_native_footprint_review.md), SHA256
`03c9576f0e24bb83e320e81e0430ad8767ffa21d0127c29b917e169be37896b5`.
Its hypothesis, self-critique, complete-constructor falsifier and allocation
rationale remain in force. The five new modules preserve the old sources.

The candidate constructs one geometric state, converts it once, and uses the
unchanged A053 reduction/lifting and A061 path operator. Its public entries are
`contact_footprint_construction.contact_footprint_embed` and
`contact_footprint_construction.inactive_booking_embed`. The latter changes
only a constant virtual inactive-arm capacity policy; it emits the same active
physical supports and uses the same physical conversion as the full variant.

## Exact changes and reuse

* `contact_footprint_layout.py` builds contacts, active supports, physical arm
  intervals and separate capacity records. Its layout score and linear packing
  coefficients use the same supports. Both-active arms include their corner;
  sole arms exclude it. Inactive physical arms and their artificial seed sites
  are absent. Isolates retain the native wrapper's ordinary free-site rule.
* `contact_footprint_kernels.py` adapts `field.align_reinsert` support membership,
  y-placement horizontal cost and vertical cut count. The vectorized lattice
  solver, both block orientations, backtrack and moved-axis rank tie arithmetic
  are inherited. A y-order change rebuilds contact activity and both packings.
* `contact_footprint_conversion.py` passes the stored active supports to the
  unchanged `field._convert_line`. That function and its existing parity-class
  assignment and actual-lane seating are reused directly. No virtual capacity
  item becomes a physical target or chain. Unseated non-isolates remain visible
  to unchanged completion and validation; no artificial corner is manufactured.
* `contact_footprint_native.py` copies the native pipeline around those two
  seams. Spectral initialization, pruning, contact refinement, deletion,
  vacancy refinement and validators are reused. The new entry supports only
  search construction. It passes the original absolute deadline, reserves
  measured downstream time from geometry and records conversion/completion/
  initial-core-validation timings. The old converter/completion still have
  no internal cancellation; pre/post checks and the external watchdog account
  for overruns. Initial native validity concerns the filled core only.
* `contact_footprint_construction.py` copies the A053 and A061 wrappers while
  reusing their reduction, expansion, transfer, repair, path and validation
  helpers. Core and path interruption exception classes remain distinct.
  Each wrapper invokes its one base at most once. New timing fields distinguish
  core validity from the observed full-source valid handoff and retain complete
  downstream wall, reserve excess and original-deadline excess separately.

The following old helpers are imported directly: `plane.profiles`, `stride`,
`ideal_pool`, `_cover_bricks`, `_line_profiles`, `units`, `rank_of`;
`field._stair_contacts`, `line_pools`, `pack_lines`, `rank_scale`, `TileGrid`,
`_convert_line`, `complete_seeds`; native cleanup/vacancy helpers; all A053
reduction/lifting helpers and A061's path operator/final-validation adapters.
The source review JSON binds these source files and stores function-level diffs
for copied functions. Source generation and AST inspection do not import or
execute the candidate.

## Explicit amendments before execution

Packing an active subset requires **monotone completion of unused coordinates**:
use the preceding active coordinate, the first active coordinate for a leading
prefix, and zero if no arm is active on that axis. This replaces the contract's
earlier suggestion to retain an arbitrary carried value. The coordinate is
absent from every current physical support, so this completion leaves those
supports unchanged and restores nonnegative interleaving slot gaps. Carried
ranks and their contact rule are preserved. A later activation can make the
coordinate relevant before repacking; there is no claim of no effect on future
search. Root approved this clarification before tests.

The inherited intermediate clipping is retained: horizontal hulls are clipped
to `[0,W−1]`, vertical hulls are nonnegative, then snap widening uses required
crossings. The virtual ablation uses the same old inactive-point clipping and
widening. This avoids an unrelated off-chip booking change.

When geometry expires during a private proposal, discard its partial readout
and convert the previous complete geometric bookmark. If initial packing or a
required bounded projection cannot complete, return an explicitly accounted
geometry-allocation failure. Never publish a partly repacked geometric state.
The layout records both ask and geometry-deadline conditions if simultaneous;
its inherited primary stop-reason precedence is retained.

## Frozen exposure, checks and decision

The first complete screen uses **1000 asks as controlled experimental exposure**,
not a saturation result, justified quality ceiling or proposed final default.
At native entry the geometry deadline is `D−min(10 seconds, remaining/2)`;
conversion, cleanup, lifting and the existing path stage use surviving time
under the original `D`. Native downstream time and complete-constructor
downstream time are reported separately. Spending beyond the ten-second reserve
is distinct from exceeding the original deadline. All inherited cleanup, path
and lifting limits remain unchanged and visible; this experiment does not
justify them. No subsequent allocation comparison is authorized yet.

The prepared [checks](../../../results/codex/a068-implementation/checks.py) have
four bounded groups: actual ideal-Z12 sole/dual-arm couplers, activation and an
isolate; direct enumeration of tiny interleavings with coordinate/rank ties;
support/conversion/capacity identity including the virtual ablation, inherited
clipping and monotone unused coordinates; interrupted private packing and
stubbed wrapper/native publication with deadline accounting. They reuse the
audited import guard and independent embedding oracle. There are no development
constructor probes, saved-map reads, new validators or old converter campaign.
Root must review this packet before its first execution.

For the root-owned 48-call complete screen, retain every failure, timing and Q
regression. Require no success/Q loss against A061 **or** the booking ablation;
at least one-third closure of a positive MM Q gap on two ordinary source
families; and Q improvement over booking on two independent structures.
Controls provide separate mechanism evidence; relabelings are not additional
families or structures. These are necessary continuation criteria, not a
publication claim. Raw deletion savings alone do not support continuation.
