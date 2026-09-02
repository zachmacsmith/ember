# Ideas

The entry point. One page: the algorithm, the constraints any redesign
must respect, and the open fronts. History is elsewhere and is history,
not instruction: `notes.md` (chronicle), `attraction.md` (verdict ledger
— check it before proposing anything), `anatomy.md` (as-built spec),
`fabrics.md` (measured hardware facts), `mm-internals.md` (what shipped
minorminer actually does), `archive/` (everything superseded, including
the previous long version of this file, `ideas_v3.112_full.md`).

## The algorithm

1. A qubit is a **bar** on a grid; the hardware graph is the
   intersection graph of the bars. Lines carry a fixed number of wires,
   with a parity period (the brick).
2. A chain is a **cross** — one horizontal arm, one vertical arm. Each
   source edge is realized at one designated crossing, assigned by the
   order rule: the endpoint lower in the y-order reaches sideways, the
   other reaches down.
3. The **state** is an integer seat (column, row) per variable. Arms,
   orientations, and congestion are readouts, never stored.
4. The **objective** is lexicographic: capacity first (interval depth
   against wire pools, counted per brick so parity cannot lie), then
   total arm length in real units. All integers, so it is one scalar;
   capacity never trades against length at any rate.
5. **Search** is strict descent whose workhorse move is: remove a set
   of variables, re-insert it at the exact optimum over all
   interleavings with the rest (a DP prices every weave, forward and
   reversed). It is a jump — it lands on the endpoint without walking —
   so the hard capacity key cannot path-block it. Jump and hard key
   only work together (measured: either alone loses the crystal).
6. Layout runs on an **idealized unbounded plane**; the real chip's
   finiteness enters only through the census and one final projection.
   (Even when the optimum fits, the initial layout may demand more
   fabric than exists; bounding the plane early was the liquid loss.)
7. Arms become wire claims by **per-line interval arithmetic**;
   completion connects and covers by the same arithmetic. On
   junction-complete fabrics (Zephyr) crossing = coupling, so zero
   deficits is a proof of validity: certified, no router involved.
8. Whatever remains is a router's job (today minorminer legalizes the
   uncertified residue and polishes chains; front 3 below).

Dense templates are never constructed — they emerge from rules 2–5
(turán reaches the exact constructive optimum 6.00 with no
clique-specific code). Sparse layouts are the same rules with short
arms. That continuum is the whole point.

## Constraints any redesign must respect

Each of these was paid for; the receipts are in `attraction.md`.

- **Order is the fundamental variable.** Positions carry orders plus
  extents. Anything derivable from the state is not state.
- **The energy is the objective itself** — real chain length on the
  real fabric, never a proxy. Feasibility lives inside the objective
  (as the leading key), never in a repair stage.
- **Validity by construction beats legalize-and-repair**, and every
  producer/consumer pair must read one shared accounting.
- **The representation can be the ceiling** (the folded coordinate cost
  2× and no search could cross it). Check it before tuning search.
- **Coarsen the moves, never the state**: a unit is a set of real
  variables moved as one proposal, judged by the same gate as any move.
  Nothing is summarized.
- **The crystal is the output shape, not the input shape**:
  pre-committed member orders pre-empt the moves that would find better
  ones. Spectral init is actively harmful on turán (trivial init beats
  it there); the sketch pays only where geometry exists to sketch.
- **The regime map** is a fact about problems, not a branch in code:
  dense → construction must emerge; structured sparse → placement's
  home turf; fixed-degree random → cut-bound, only the constant
  winnable. No mechanism may name a graph type.
- **Wins must not buy fatter tails**: max chain is reported next to ACL.
- **minorminer's residual value is measured, not mysterious**: the fold
  (global re-layout composed of many small relocating strict-descent
  chain moves) and legalization-by-priced-overlap. Seven probes
  eliminated every cheaper explanation; do not re-run them.

## Open fronts

1. **One state, one family — the seam deletion.** The normalizer pack
   exists only because the converter and completion are co-designed
   with packer-shaped states. Preferred resolution: state = the two
   orders, positions always *derived* by the hard-capacity
   true-objective DP. Then every state is packer output by
   construction: the normalizer, the pen machinery, `best_seat`, and
   `best_translate` all delete; the jump survives unchanged (it is
   already an order move — same coordinates, new occupants); singles
   subsume re-seats. The orders era's old disease does not return
   because proposer == judge now (a declined DP candidate costs one
   evaluation, not a rejection cycle). Fallback if it loses: the
   lex-family converter (spill-aware per-line brick seating).
   ROUND 1 MEASURED (s3.113, `engine="orders"`): turán at the exact
   6.000 optimum on all 10 seeds in both acceptance arms and
   load-robust where the default collapses; ws parity while
   budget-bound at one pass; residuals ER +0.84, king +1.5/+0.6,
   grid +0.5 (accept-all only — audit holds parity there). Banked:
   the readout enforces LINE capacity but pen counts BRICK capacity —
   a two-books seam to close. s3.113b decided the acceptance fork
   (audit finds equal-or-better answers faster; accept-all stays as
   the control arm, re-measurable after readout perf) and found the
   seam is plausibly the liquid's gate: ws bookmarks freeze at
   readout 2 in both arms because brick-pen the pack cannot fix
   dominates the lex bookmark. s3.114 (numba; readout 111→10 ms,
   state-version memo) made the schedule cycle and NOTHING moved —
   the residuals are capability, not compute: the interval family
   cannot express ER/king (variance-cluster gathers), and the
   brick/line seam still freezes the ws bookmark. s3.115: hierarchy
   groups as extra units CONFIRMED the ER variance thesis (audit+h
   −0.40 on 21 gathers; gap to default now +0.12) and acquitted king
   of it (±0.05 — a different mechanism, likely the pen class or fine
   moves). s3.116 (the Infinite Plane): search on the ideal plane +
   ONE brick-aware annotated projection — king −1.25 (solved), ER
   −0.53, grid −0.39, crystal in-tol, accept-all now BEATS audit on
   the plane (Max's conviction measured right in its setting);
   hier_units toxic on the plane crystal (do not compose, diagnose).
   Plane accept-all is the recommended engine candidate; remaining ws
   gap lives below the plane (claim/tail, the s3.95 map). s3.117:
   plane IS the default (flip board: wins dense/regular/ws-mx, ER
   +0.46 the one open residual); projection centering shipped
   (stair-neutral); the DP audit (`dp-internals.md`) surfaced the
   measured shortlist. s3.118 (carry the order): state = the two
   orders literally, every move a real state — ER falls to 4.42 (the
   confound confirmed), edge-pairs subsume monotonize, and the
   crystal exposes the INIT front: carry+trivial = exact 6.000/10
   while carry+spectral fails (the id-collapse had been laundering
   the init's order all along). `carry_orders` off pending the init
   question — which is now THE open front: init as one swappable
   ordering function, its quality no longer launderable. s3.119:
   tiles (the 2-D-joint family) refuted as built (partial crystal
   rescue, K140 broken, seed-0 smoke did not replicate);
   settle_projection quality-neutral but its proj_iters instrument
   confirmed the fixpoint premise exactly (holds at slack/crystal,
   fails at saturation/liquid). Both off. s3.120: CARRY IS THE
   DEFAULT (the id fossil is dead by default); the init round:
   landmark (double-BFS) holds the crystal at exact 6.000 label-
   independently while trivial's win was proven label luck; no init
   flip (regular +0.54 fails the bar); random init = best-ever ER
   (4.383) and ≈spectral on turán — the init's whole value is
   regular+ws, the joint-move front's own cells. One question, two
   sides.
2. **Units without the hierarchy.** Replace affinity-hierarchy units
   with contiguous runs of the current order, at all scales. Singleton
   insertions do the gathering (insertion sweeps built block structure
   from random init before), wider intervals do the weaving. If parity:
   the hierarchy deletes and init shrinks to one swappable ordering
   function the jump should overpower anyway. ROUND 1: interval units
   are what `engine="orders"` runs — they hold the crystal and the
   liquid but not king/ER (see front 1).
3. **minorminer to the very end, then out.** In order: (i) grow the
   certificate — native completion for the small residues (measured
   membranes where seeds are submitted: ER 1 edge, regular 19, grid 29)
   instead of summoning a router to patch one edge; (ii) mm then
   remains only as final polish, an afterthought; (iii) full removal
   needs exactly one native component: a relocating, randomized,
   BFS-based chain shortener — mm's measured value with its measured
   waste cut (the audition burns most where nothing can improve;
   `tries` stop at first success; the heap should be a BFS). Interim
   surgical cut if mm lingers: the `short_audit` budgeted-audition
   fork switch (mm-internals §6).
4. **The expander toll** (Z12 +0.16/+0.40 vs stock): the no-order
   regime. ER is not order-free (variance makes some nodes more alike
   than others) but a 1-D dendrogram linearization destroys the 2-D
   geometry spectral ranks carry; wanted: an order generator that keeps
   both. May be mooted by front 5 if those cells are capacity-bound.
5. **Lower bounds as certificates.** Contact (deg/κ), cut (wires
   across a sweep line), treewidth (busclique as witness) — one object
   at three scales, currently used only as floors. As per-instance
   certificates they would attribute any remaining gap to capacity
   wall vs packing vs search — i.e. say where not to work.
6. **Parked**: Pegasus (weird and going obsolete; unblock = an elegant
   coupler-predicate cover accounting shared with the Zephyr machinery,
   never a parallel engine); max-chain as a third lexicographic slot;
   king +0.24 and grid +0.04 residuals.
7. **Nomination — pay for order, not for asks (DIRECTION: discuss
   before build).** A rejection is cheap; bulk rejections are not. The
   scheduling information is already computed and discarded: (a) the
   state-version memo's invalidation set on every accept IS the
   worklist (re-ask exactly what the accept disturbed); (b) a declined
   DP carries its reason-set — the variables realizing the binding
   hull extremes (what `_axis_coeffs` counts); (c) recurring
   co-blocking clusters escalate into discovered joint units (subsumes
   span-ranked edge nomination, and operationally detects ER variance
   clusters: delocalized flat score landscapes with overlapping
   near-minima — candidate replacement for hier_units without static
   machinery). Bonus: an empty worklist is a fixpoint certificate over
   the move family — the honest internal stopping rule s3.75 said
   doesn't exist, and the structural kill for mm-style patience
   sweeps. Distinction on the record: this is history-as-SCHEDULE
   (judge untouched, misnomination costs one evaluation) — not the
   twice-refuted history-as-cost. FIRST BUILD SHIPPED (s3.122,
   `wave_schedule`, lever off pending the flip call): wave 0 = the
   blind first pass, maintenance waves dirty-restricted by the
   ground-truth span/contacts diff, empty completed wave =
   full-family fixpoint certificate. Round-2 board: parity (7 exact
   ties incl. deciders at 10 seeds), bmw wins on regular/grid,
   certificate fires on ER/grid/honeycomb. SECOND BUILD (s3.123,
   `axis_inner`+`cross_widen`, levers off): the discovered-units
   question answered by measurement — the capacity-coupled sets ARE
   discoverable from adoption diffs and prolifically askable
   (60-75% of widened questions adopt) but their joint adoptions
   are plateau wanders under accept-all (crystal +0.552/10; movers
   ~parity). The front's open question moves DOWN a level: not
   "which sets" (the diffs know) but "under what judge/acceptance
   do joint set-moves profit" — the slack-view-or-acceptance fork,
   reached independently by s3.121b (ws audit declines 100% of
   joint proposals), the 240s fold verdict, and the widening board.
   Still open here: scoped/per-node invalidation (the two-trees
   design — order tree x affinity hierarchy, agreement as the
   progress meter), and the dense-cell economics (churn accepts
   dirty their whole cut, so waves ≈ passes there — the acceptance
   question's new face).
   FIRST MEASURED MOTIVATION (s3.121):
   the blind coarse ladder deadline-cuts pass 1 before the fine end
   on ws/regular in EVERY arm — the shipped pair units and the new
   2-D singleton (`xy_singles`, built oracle-exact, lever off) never
   run on exactly the cells that need them, and on ER the extra
   sweep feeds accept-all churn (+0.48). Blind sweeps are expensive
   in both currencies; the fold thesis awaits a schedule that can
   reach its atom. The `slot_costs` per-slot vector is the
   delocalization detector's instrument, already built.

## Method

Measure paired by (instance, seed) against the shipped default, on
outcomes: final ACL, max chain, feasibility, wall. One pipeline —
winners become the default immediately, losers are archived and
deleted. No mechanism may name a graph type. When a validated mechanism
fails to move a cell, diagnose why before building the next thing.

## Status (2026-08-26)

The shipped pipeline (spec: `anatomy.md`) beats stock minorminer on the
full 24k-graph library on both fabrics — ACL −0.06 (P16) / −0.17 (Z12),
feasibility ~2:1 — with max chain ≤ mm's wherever both were measured,
and ws below stock's band since the infinite packer. Consolidation 7
left one engine (lex + interleave jump) at board parity with everything
it replaced, crystal included. Sweep data:
`results/batch_2026-08-05_19-43-17` and siblings;
`/data/max/fullember3/REPORT.md`. The board deserves a fresh full sweep
on the current baseline.
