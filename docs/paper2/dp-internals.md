# DP internals — what the two DPs actually do

Source-verified reference (2026-08-27, s3.117 audit round) for the two
dynamic programs everything rides on: **the pack DP** (`pack_lines` +
kernels + `pack_project`, the readout) and **the interleaver DP**
(`align_reinsert`/`_arm`, the one structural move). Compiled from two
independent fresh-eyes audits; ⚑ marks claims MEASURED during the
audit, not inferred. House rule as for mm-internals.md: verify against
this file and the source, never against docstrings — several were
found false (list at the end).

## 1. The pack DP — decision rules nobody chose

- **Tie order is carry ≻ run ≻ skip**, enforced by the evaluation
  sequence and a 1e-12 epsilon that, in production (integer-valued
  coefficient mode), never resolves anything — it only implements
  strict inequality. The ordering itself has no recorded rationale.
- **The deque pops ties (`>=`)** → among equal-cost run starts the
  newest survives → prefer the shortest run on the current line —
  a second, independent low-line bias. One-character experiment
  (`>` instead of `>=`); would move plateau-heavy cells (⚑ 12/40 and
  6/40 zero coefficients on a random 5-regular n=40).
- **The objective is translation-invariant** (Σ coeffs = 0 exactly, ⚑
  verified — every net contributes +1/−1 and participation is
  universal at min_span=0). Consequences: layouts LEFT-JUSTIFY by
  tie-break (⚑ four rows and three columns of a Z4 chip permanently
  empty); `values` is dead in coefficient mode (the packer has zero
  attraction to incoming positions); overflow damage concentrates on
  the high corner; the `+nlines` slack in L_max is unreachable work.
  s3.117's `_center_shift` fixes placement for the plane engine only,
  and only when the projection is miss-free.
- **⚑ The linearization is invalidated by its own output** (the
  deepest item): `_axis_coeffs` prices the diagonal rule of the
  PRE-pack order; the pack COLLAPSES values (not permutes — the
  module docstring's invariant is false), and (y,id) tie re-splits
  flip contact assignments — ⚑ 32/40 variables changed h-contact sets
  through one `pack_project`. The DP exactly optimizes coefficients
  its own output no longer satisfies. Known narrowly (the s3.77
  axis-1 contacts-reuse refusal) but never as a statement about the
  DP's optimality. Candidate resolutions: id-consistent within-line
  ordering, or a 2-3 round coefficient fixpoint. Cells: dense
  (n >> nlines).
- **⚑ Boundary-line zeroing is un-gated across fabrics**: applied to
  both axes on every typed fabric, though the recorded rationale
  (fabrics s4.3b, course parity) is Zephyr-only — ⚑ it discards
  12.5% of Chimera's lanes and 7.4% of P16's (the FAT end, line 0 at
  pool 12). Also the load-bearing comments conflate hosting count
  (⚑ 8, measured) with crossing count (4). The two boundary lines are
  restricted to OPPOSITE parities; zeroing both erases a real degree
  of freedom (the parked crossing-parity-aware-packing item).
- **⚑ The phantom trailing brick**: `_brick_pool_arrays` emits a
  final brick column with pool 0 (Wb rounds up past the last real
  along-position); the brick clamp lands right-overhang INTO it, so
  "out-of-fabric bricks are free" is false on the right (and true on
  the left) — right-overhanging hulls become infeasible → misses →
  `_center_shift` silently disabled (it is gated on miss-free).
  Cells: plane engine on ws/K140/spin_glass.
- **The straggler clamp can land on the zeroed boundary lines** it
  was just forbidden from using, and in the unbounded branch targets
  a pre-anchor frame (latent only because unbounded misses are
  structurally impossible).
- `_MISS_COST = 1e6` was sized for the retired displacement
  objective; in coefficient mode the safety margin is ~12× at n=486
  and gone by n≈2000. Derive it, don't hard-code it.
- `pool_u = max(lp.values())` maxes across BOTH orientations and all
  lines (⚑ live on Pegasus: pools 2..12 on one fabric).
- `edge_monotonize`: ⚑ ~30% of edges are same-row after a pack and
  structurally invisible to it (the `dy==0` skip uses raw values
  where the stair rule uses (y,id)); its gate prices un-floored
  spans (the s3.73 blind-spot charge, never recorded against it);
  the "sorted edge order" claim holds only by caller convention;
  `max_sweeps=16` has no recorded rationale and caps silently.
- kappa floor widens BOTH axes by deficit/4 even when only one side
  has contacts — manufactures point-arm capacity demand from
  nothing; then the bounds clip silently un-does the floor near
  edges (which, combined with left-justification, bites the same
  variables the tie-break already crushed).
- Verified sound (checked, not assumed): the L_max lemma; the
  skip-ends-a-run restriction (mild as documented); snap's
  asymmetric widening (a−1 vs b — parity arithmetic, principled);
  the min_span footprint (b=a+1, right-only, principled); np.rint
  vs round() half-to-even consistency (⚑ checked); `_center_shift`'s
  termination and s-aligned-shifts argument; contacts survive
  uniform translation.

## 2. The interleaver DP — the tie regime and the missing gate

- **⚑ THE HEADLINE: under tied values (the production regime —
  post-pack line indices), the DP's accepts are unsound and the
  correcting gate no longer exists.** n=9, 400 trials, axis 1:
  142/400 accepts are not true improvements, 55/400 are STRICTLY
  worse (Δ up to +9), 6/400 "noop certificates" are false. The
  docstring's "corrected by the composite's real-books gate" refers
  to machinery deleted at consolidation 7; the default plane engine
  adopts every proposal. ⚑ The epsilon ramp is NOT the cause
  (removing it quadruples false noops while barely reducing bad
  accepts) — the cause is the induced rule's within-plateau
  assumption colliding with the readout's (value,id) collapse.
  Axis 0 is structurally sound (0 strictly-worse in 400 trials).
  Cheapest sound repair: one O(E) re-price of the returned order
  against the UNRAMPED view, reject unless strictly better — makes
  the proposer honest about its own view without adding a
  truth-gate. CONFOUNDS recorded findings: ER/grid accept-all churn,
  possibly the s3.116 acceptance inversion.
- **⚑ The exactness oracle never sees a tie**: the test generator
  draws distinct values and grades against the RAMPED ground truth —
  circular w.r.t. the ramp, blind to the operating regime. A
  tied-values arm reproduces the table above immediately.
- **⚑ The ramp is a second objective, not a tiebreak**: the DP
  minimizes true cost + 1e-4·(total rank-span) — bias measured at
  +9 to +11 units at n=486 against an integer-quantum objective. The
  recorded "max ~0.05 tiles" bound bounds the coordinate, not the
  cost. Don't shrink it blindly (false noops quadruple); make it an
  explicit lexicographic tiebreak if wanted.
- Tie rules: CH backtrack prefers the R-step (pushes the unit toward
  earlier slots — a systematic directional bias among equal optima);
  the reversed arm must beat forward by 1e-12, which is BELOW the
  float noise floor at n=486 (~1e-11) so exact ties are decided by
  rounding residue (deterministic per input); the 1e-9 accept margin
  is sound at current magnitudes, scale-dependent (~E 1e7 fails).
- Counters lie a little: seat.py's `interleave_declines` conflates
  three events (true decline / lost-to-other-axis / identity-collapse)
  — the s3.111 "357 cheap declines" is inflated; orders.py's
  `interleave_noops` conflates memo-skip / DP-None / readout-collapse.
- Verified sound: e_path exactly equals the identity path's DP cost
  (the noop certificate is internally sound); the axis-0 omitted
  v-term is exactly constant; the induced rule matches the stair
  rule outside plateaus; the reversed-arm reflection at all
  boundaries; `_rect` clipping drops no mass (one rescue rests on
  the unstated m ≤ n invariant); the p<=m sweep switch introduces
  no fwd/rev asymmetry; capacity is invariant under the move (the
  value multiset is preserved).
- Stale docstrings (load-bearing — they are why the tie regime went
  unexamined): references to `cluster_gather_order` and
  `_order_proxy` (both deleted at consolidation 7); "path cost
  equals its true view energy" (false by the ramp bias); "exact
  within the view" (axis-1: only when values are distinct);
  "same-line edges only" (bounds the set, not the magnitude).
- Dead paths: `anchors` (production-dead), `other` on axis 0,
  `contacts` on axis 1 (and unguarded None on axis 0), the
  `border != order` net, `flipped` return (both callers discard).

## 3. Ranked shortlist (candidate rounds, each its own measured flip)

1. **Interleaver view-gate** (one O(E) unramped re-price of the
   returned order) — kills measured strictly-worse accepts; cells:
   ER/grid/turán accept-all. Re-measures the s3.116 inversion.
2. **Boundary zeroing gated to stride>1** — ⚑ frees 12.5% of Chimera
   / 7.4% of P16 lanes; cells: Chimera, all P16, ws-class.
3. **Phantom trailing brick clamp fix** — unblocks right-overhang
   projection and re-enables centering on crowded plane cells.
4. **Monotonize stair-predicate fix** (the dy==0 blind spot, ~30% of
   edges) — dense + plane cells; update its oracle in lockstep.
5. **Coefficient/collapse fixpoint** (the linearization's self-
   invalidation) — design round; dense cells.
6. **Centering for all engines + on miss-y projections** (currently
   plane-only, clean-only).
7. Tied-values test arm + unramped ground truth (test gap; cheap).
8. Deque `>=` → `>` one-char probe; `_MISS_COST` derived; pool_u
   per-orientation; clamp to [1, nlines-2]; kappa split
   contact-weighted (measure); counter de-conflation; docstring
   corrections and dead-code sweep (hygiene, zero behavior).

The two full audit reports (with all measurements and line numbers)
are condensed here; details live in the session record (s3.117).
