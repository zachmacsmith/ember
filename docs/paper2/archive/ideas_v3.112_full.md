# Ideas

This is the entry point for the embedding project. It contains the ideas —
the general principles that survived measurement, and the open questions.
It exists because the old notes grew a fossil record of micro-verdicts and
self-invented doctrine that crowded these out (Max, 2026-08-06). The rule
for this file: an entry is either a general idea, a measurement that
changed the algorithm, or a verified hardware fact. Nothing else.

The full history lives in `archive/` (chronological lab record and the
old idea ledger). Treat the archives as history, not instruction: they
record what was believed at the time, in a vocabulary this project no
longer uses. The as-built pipeline spec is `anatomy.md`; measured
hardware facts are `fabrics.md`; what shipped minorminer actually does is
`mm-internals.md`. Those three remain live references.

## 1. The problem, correctly stated

Minor embedding on D-Wave fabrics is not the general NP-complete
graph-minor problem. The hardware is a two-layer routing fabric: **a
qubit is a bar** — a horizontal or vertical segment on a grid — and the
hardware graph is the intersection graph of those bars (fabrics.md).
Embedding is therefore **placement plus routing**, and a chain wants to
be one horizontal arm and one vertical arm meeting near a point. An edge
is realized at one designated crossing between one endpoint's h-arm and
the other's v-arm.

Three consequences set the whole design:

- **Order is the fundamental variable, not the metric.** The designated
  crossing rule keys on the y-*order* of the endpoints; the packing that
  legalizes a layout is order-preserving. Positions are a carrier for
  orders plus extents.
- **Capacity is the binding constraint.** Lines carry a fixed number of
  lanes; feasibility on a line is interval-overlap depth against an
  integer pool. Everything else is negotiable; this is not.
- **The energy is the objective itself.** Total arm length IS total
  chain length, measured in real units on the real fabric — never a
  simulated proxy. (When a proxy and the objective diverged, the proxy
  was always the one lying.)

## 2. Principles that survived measurement

Each entry: the principle, then the strongest single piece of evidence.

1. **Placement first.** A global placement makes the joint decisions
   that one-chain-at-a-time search structurally cannot revise; the
   router is kept for what it is unbeatable at (local legalization and
   free-descent polish). *Full-library sweep: attraction embeds ~2× more
   graphs that stock minorminer cannot than vice versa, on both fabrics.*

2. **In the crystal regime, search is the wrong instrument.** Every
   search method, minorminer included, sits 8–57% above a free
   constructive template on dense cells (per-cell range,
   `data/dense_attrib.csv`; corrected s3.74), and minorminer's polish cannot
   improve the template at all. The answer is not to search harder but
   to make the construction **emerge from general rules** — never to
   hardcode it, and never to run a portfolio. *Turán reached the exact
   constructive optimum (6.00 = ⌈81/16⌉) from a general
   order-and-measure rule with zero turán-specific code.*

3. **Anything derivable from the state is not state.** Extents,
   orientations, and seats are readouts of positions; every time the
   state was enriched beyond that (per-edge contacts, explicit extents),
   the leaner representation won. Gauge freedom is the optimizer's
   enemy.

4. **The representation can be the ceiling.** A folded fabric coordinate
   imposed a hard quality floor (~2× the template) that no amount of
   search could cross; unfolding it lifted quality and feasibility at
   once. Check the representation before tuning the optimizer.

5. **Validity by construction beats legalize-and-repair.** Aim claims
   parity-exactly at construction time and the repair pass becomes a
   verifier; when seeds are valid the legalizer is skipped entirely, and
   abolishing the repair stage removed a tax that had been silently
   punishing the tightest (best) geometry.

6. **Feasibility belongs inside the energy.** Pricing constraint
   violation into every selection gate (evaluation only, never descended
   on) let the gates stop choosing configurations they could not see
   were infeasible — and made a whole annealing mechanism unnecessary,
   because that mechanism had only ever been accidentally dodging
   invisible overload.

7. **One accounting.** Every consumer — packer, coloring, feasibility
   census — reads the same books. Exact order-preserving DP under a hard
   integer capacity beat greedy packing, and every "two books" divergence
   eventually surfaced as a deficit on the tightest instance.

8. **Contract before the first commitment.** One settle pass before the
   first discrete projection is worth more than any amount of subsequent
   re-shaking; the first projection is nearly irrevocable because
   everything downstream is order-preserving.

9. **Known dead ends in force-based placement.** A local congestion
   penalty is gradient-blind inside a uniformly overloaded region (only
   the rim peels — Gauss's law). Realized demand cannot signal crowding;
   only proposal demand can. A memory term is inert when a
   freshly-calibrated present term covers its job (measured twice,
   independently — in minorminer itself and in our field).

10. **Coarsen the moves, not the state.** Merging defines who moves
    together, never how big anything is: a cluster is a set of real
    nodes gathered or relocated as ONE proposal, in rank space, judged
    by the same energy and capacity gates as every fine move. Nothing is
    summarized, so no size is ever guessed and density artifacts cannot
    exist; the E-gate is the only discriminator needed — where the
    coarse order is real the moves fire (turán 8.12 → 6.52 at 3 seeds,
    worst 6.80 vs stock's 9.46 — `data/cmove_probe.csv`; a
    previously-cited 10-seed version of these numbers had no artifact,
    s3.74), where it is noise they are
    silently rejected (expanders at exact stock parity, where
    unconditional transport had lost). Cadence matters: coarse moves
    judged on unpacked geometry accept fictions — they fire after each
    projection, never before the first.

11. **The crystal is the output shape, not the input shape.** Arithmetic
    may size a region; rules must never draw its shape. A pre-committed
    member order pre-empts exactly the E-gated moves that would discover
    a better one — measured twice (segment spreads; the pre-formed K_n
    diagonal, which lost to a shapeless anchor despite better energy).

12. **The regime map.** Fixed-degree random graphs are cut-bound: ACL is
    Θ(n) for every embedder and only the constant is winnable there.
    Structured sources are the home turf — that is where placement finds
    what local search cannot. Dense crystals belong to construction
    (which must emerge, see 2). The map is a fact about problems, not a
    branch in the code: mechanisms participate by capacity pressure, so
    they go structurally inert outside their regime instead of being
    switched.

13. **Wins must not buy fatter tails.** Chain-strength physics is set by
    the worst chain: max chain length is reported next to ACL, and the
    current pipeline beats minorminer on both simultaneously (max chain
    ≤ minorminer's on every board cell).

14. **Restrict the family, never the fidelity.** Expressivity lives in
    the candidate set, never in a proposal view: a restricted family
    judged exactly can only miss moves; a corrupted evaluation takes
    wrong ones and lies about the losers. *The alignment DP's
    exponential family under a capacity-blind view ran 87–99% gate
    rejections on sparse cells (s3.101 revert attribution); every
    seat-engine move is a small exact-judged family and has no revert
    class at all (s3.102).*

15. **Completability is enforced by construction, or it is not
    enforced — REFINED at s3.110/112.** The orders pipeline never
    needed its gates to see claim-realizability because every state
    it occupies was packer output — a regular subfamily the
    exactness stack was co-designed with (s3.37/56). The lex engine
    resolves the same obligation differently: capacity is a
    lexicographic INVARIANT of the search (near-hard by the brick
    pools), and ONE pack — the family NORMALIZER — projects the
    result into the packer-shaped family before conversion
    (measured, s3.110: pen-0 states convert at 578 deficits raw, 0
    after one pack, pen preserved). So the converter arithmetic is
    convertibility technology co-designed with a FAMILY, and either
    the state stays in the family by construction (orders era) or
    is projected into it once (lex era). The remaining sharpening:
    a converter co-designed with the LEX family (spill-aware
    per-line brick seating) would delete the projection too.

## 3. Open questions — where the next ideas are needed

- **The completability question — CLOSED (s3.104 → s3.112).** The
  answer arrived in three measured pieces, none of them a "term":
  the brick ruler makes capacity near-hard (a brick holds one
  junction of each parity, so whole-brick honest-arm promises
  cannot be parity-infeasible — s3.107/109); the lexicographic
  order makes it an invariant instead of a price (λ deleted, the
  swamping defect class unrepresentable — s3.110); and the
  interleave JUMP gives the hard key the reach the soft engines got
  by wading (s3.111b, the complementarity: jump+soft loses turán
  7.28, hard-without-jump loses 7.42, jump+hard = 6.000/10). The
  residue moved into §2.15's refinement: the normalizer pack is the
  last place completability is bought rather than owned, and its
  deletion is the lex-family converter's (open, below).

- **The lex-family converter (the named next front, s3.110/112).**
  Per-line spill-aware brick-interval seating: aligned wires host
  abutting bricks bar-for-bar; straddling wires need one-brick gaps
  (the +1 spill); the even-lo required-hull poke is the boundary
  case. Built and measured, it deletes the normalizer pack AND the
  classed active-set DP — the last two-court seam in the pipeline.
  Design discussion first; the abutment cases have real teeth.

- **The extents object — mostly dissolved (s3.70).** The six blocked
  items needed extents only because the coarse level *summarized*;
  cluster moves never summarize, so the placement path no longer needs
  the derivation. What remains of it: the merge score's self-entry (a
  cluster-quality question now, lower stakes) and any future wish for a
  cheap summarized coarse energy (a speed play, not a correctness one).
  "When is an order real?" is likewise resolved: the E-gate answers it
  per proposal, with no discriminator machinery.

- **The init-time residual (confirmed three ways; THE named target,
  Max 2026-08-08).** Threshold-free units gave lattices proper patch
  hierarchies — and grid/honeycomb still barely moved (s3.71). The
  adjoint wins there (−0.90, −0.54) live in *init-time* ordering,
  before any lane commitment: a post-pack gated move cannot reproduce
  them, and a pre-pack gated move judges on fictions (measured, both
  directions). s3.75 closed the last escape route: even whole-region
  re-layout on the real wires (ball polish) cannot reach it — local
  reconstruction renegotiates HOW a neighborhood is laid out, never
  WHERE the order came from. The sparse geometric cells are cheap
  graphs we lose for one reason: the init mangles an order the graph
  makes obvious. LARGELY RESOLVED by the order state (s3.76): with
  positions derived from orders by the true-objective readout instead
  of anchored displacement packing, the lattice block fell in one flip
  (honeycomb 1.81→1.09, king 2.36→1.53, both below stock; grid
  1.41→1.12 vs stock ~1.08). Residual: grid's last +0.04 to stock, and
  the Z12 expanders now pay a modest toll (+0.16/+0.40) — the
  no-order regime.

- **Remove the continuous state (Max, 2026-08-08).** The cheap
  elimination failed informatively: cstable (s3.75) measured that
  stair-E descends monotonically toward collapse — the plateau rule
  never fires, so NO internal energy signal can honestly stop the
  continuous phase; every step count or cap is a disguised density
  knob. The counter-force was always the discretization. Endpoint:
  state = two orders + lane assignments; continuous coordinates demoted
  to an init-only order-generator (spectral ranks in, orders out). This
  and the init-time residual are likely one project — under the
  envelope view every regime is an order-quality problem (dense: the
  identity order is optimal; sparse geometric: a 2-D snake; expanders:
  none exists), so a state that IS the order unifies the regimes the
  pipeline currently straddles. STAGE O1 BUILT, MEASURED, AND DEFAULT
  (s3.76, `order_state=True`; Max: it should be the default even if it
  lost — a loss would locate the error elsewhere): both named residuals
  moved in one flip — turán 6.02 at 10 seeds, lattices at/below stock,
  all three P16 cells won — at a modest expander cost, exactly the
  predicted regime split. Open: the expander/ER toll (next bullet);
  retiring the positions dict entirely (stage O2, cosmetic once the
  invariant holds).

- **ER graphs are not order-free (Max, 2026-08-08).** The expander toll
  reads as "no order to exploit," but a random graph only lacks order
  in expectation: variance makes the average node measurably more alike
  to some nodes than to others, and those should be placed together.
  The affinity hierarchy already detects exactly this (its units are
  the fluctuation clusters) — but it currently feeds only the cluster
  MOVES, never the init ORDER, which still comes from spectral ranks
  (noise on ER). Candidate: derive the init orders from the hierarchy
  itself — a dendrogram linearization puts affine nodes adjacent by
  construction, one order-generator serving lattices (patch snakes),
  ER (variance clusters), and dense (twin blocks) alike — and it would
  retire the V-cycle's disc/anchor geometry, which under the order
  state generates continuous points only for them to be flattened into
  ranks. MEASURED AND REFUTED AS BUILT (s3.77, `data/hier_probe.csv`):
  the thesis cells moved the wrong way (ER +0.23, regular +1.07) while
  only the crystal regime held (turán 6.000 on 10/10 seeds). The
  hierarchy detects the variance but a 1-D dendrogram linearization
  destroys the 2-D geometry spectral ranks carry — the thesis needs an
  order generator that keeps both, and remains open. Spectral init
  stays; the disc geometry survives as its feeder.

- **Unit selection from deep hierarchies (the s3.72 lesson).** The
  correct merge criterion is settled — per-member affinity: compare
  average members; fragments of one family score 1 at any size ratio;
  the direct edge and shared support share one scale (chains ½). But
  the criterion and its CONSUMPTION are separate questions: a hash-free
  deep hierarchy emits nested fragment units whose one-shot gathers
  pre-empt the full-block gather (turán 6.71 vs 6.46) — more units made
  the move set worse. Open: which units from a deep hierarchy should be
  offered, in what order — selection/ordering, not scoring. ANSWERED
  in s3.73: no selection rules at all — both axes, strict energy
  descent, free proxy no-ops; the energy is the schedule. What remains
  is sharper: **the gate energy has a measured blind spot** — fragment
  moves strictly lower stair-E while worsening routed chains (turán
  pinned at 6.8 while five other cells improved). Partially dissolved
  by s3.75: post-embedding composites now exist that judge on routed
  reality directly (ball polish — no pricing, just counted qubits), so
  the claim-layer pricing question survives only for the in-arrange
  gates, at lower priority. Also banked in s3.73: the first
  dense-Pegasus improvement ever (P16 turán −0.61 via 2-D gathers),
  reaching a fabric the stride-gated exactness stack never could.

- **Fabric-side coarsening.** Only the source is coarsened today; the
  fabric coarsens naturally (supertiles with pooled capacities), and
  then every level is the same problem — coarser source on coarser
  fabric, with real capacities at every scale. Acceptance case
  (rescoped s3.74 — "lost to minorminer" was an overstatement): the
  full sweep shows hardware_native *mixed*, not lost — P16 favors
  attraction where both embed (−0.34/−0.39 at 101–1000; only-att 4 vs
  only-mm 0 at n>1000) while Z12 keeps a +0.55 loss band at 101–300
  (2/4) — so the acceptance case is the Z12 band.

- **Pegasus — WRITTEN OFF (Max, s3.112: "weird and going
  obsolete... if I never saw pegasus results again I don't think
  I'd mind").** The lex engine runs there but regresses (its cover
  arithmetic assumes junction completeness). PARKED, unblock
  condition: an ELEGANT adapter — coupler-predicate cover
  accounting shared with the Zephyr machinery, not a parallel
  engine — should Pegasus ever matter again.

- **Legalization is not one thing (Max, 2026-08-14).** With the
  infinite packer condensing layouts onto the chip, part of
  legalization now demonstrably lives BEFORE any embedding exists —
  and the rest decomposes. Four separable obligations that
  minorminer's legalizer bundles (because its representation cannot
  separate them): (1) **geometric fit** — the layout must fit the
  window under lane capacity; now placement's job (census + width
  observables + final projection, s3.93). (2) **micro-realization**
  — each edge needs an actual coupler (parity, corners, junction
  existence); the claim adapter's job; residues are tiny where seeds
  are submitted (ER 1 edge, regular 19, grid 29 — s3.92). (3)
  **topological connection** — chains connected, residues bridged;
  completion's corner/bridge passes. (4) **local re-construction** —
  when the placement is genuinely wrong somewhere, re-route
  through/around occupied fabric; the only part that intrinsically
  wants mm-style overlap negotiation, and it shrinks as 1–3 improve.
  The campaign against mm's legalizer is therefore not one battle:
  (1) is won, (2)–(3) want the negotiated-completion design
  (eviction audit at claim time, pre-ratchet), and the open question
  is how much genuine (4) remains per cell once the rest is native —
  measurable as the deficit counts on the s3.93 baseline. Three lower bounds — contact (deg/κ),
  cut (wires crossing a sweep line bound every separator), treewidth
  (feasibility; busclique is its witness) — are one object at three
  scales. They are currently used only as floors in the code; as
  *certificates* they would attribute any gap to capacity-wall vs
  packing vs search, per instance.

- **Corridor pricing.** The arrange step does not price non-participant
  traversal; suspected loss mode on cluster-of-clusters sources.

- **The fold (s3.86-87) — the liquid residual's mechanism, and the
  design that answers it with no third mechanism.** Measured: our
  liquid seeds carry monster chains because layouts never fold —
  order-irreducible long edges (WS shortcuts) stay long; minorminer's
  entire irreplaceable contribution is gradual folding via small
  relocating strict-descent steps (all 16 >10-tile ws edges collapse
  post-grind to max 7.3). Design notes, assembled with Max 2026-08-12:
  (1) the units hierarchy is a FILTRATION — no thresholds, merges run
  to one node per component; an edge's MERGE ROUND is a free, general,
  threshold-free measure of structural range (ring edges round 1, WS
  chords last). (2) The coarse-init layout still bills wrongly:
  multiplicity-weighted springs charge per fine edge, but stair arms
  are HULLS (parallel edges share arms) — bundles over-billed, lone
  long edges under-billed, so the coarse circle always beats the fold.
  (3) The fold's activation barrier (boundary stretch paid up front,
  chord gain collected at completion) blocks every small-step path our
  gates evaluate; COARSE relocations jump it — gates compare endpoints
  only. (4) The endpoint consistent with "coarsen the moves, not the
  state": delete the weighted coarse spectral rather than fix it —
  dumb init, coarse-scale relocation moves judged on the REAL fine
  books do the layout, unifying init and moves into one real-judged
  family. Open: budget cost of layout-by-moves vs warm start. CENSUS RUN AND
  PREDICTION REFUTED (2026-08-12): the late-merge FRACTION does not
  separate strongholds (ws 0.04 ≈ grid 0.03; heavy tails belong to
  DENSE cells — turán 1.00 trivially, blocks are internally edgeless).
  Merge-round alone conflates long-range with dense/disordered. The
  surviving detector: an edge that merges late AND is long in the
  CURRENT layout — graph × layout, free to evaluate at coarse-move
  time (where the layout exists), impossible only as the layout-free
  statistic the census asked for. Also settled this exchange (Max):
  the weighted-coarse-spectral init is the un-migrated half of
  "coarsen the moves, not the state" — the endpoint deletes it (dumb
  init + real-judged coarse relocations), not re-weights it.
  MOVED (s3.89, discussed then built 2026-08-13): the move family was
  translations-only — a reversal cannot be composed from translations
  under strict descent, so the fold was unreachable BY CONSTRUCTION.
  The orientation bit (every gather offers its reversed block; the
  gate picks) SHIPPED as default: ws −0.113, grid −0.090 at zero cost.
  The fold itself is irreducibly TWO-AXIS — a one-axis reversal
  preserves the axis's value multiset, putting both strands on the
  same wires (194/194 ov-vetoed, refuted); the shipped shape riffles
  the interval on the strand axis and splits its own multiset on the
  other. First mechanism to move ws on both fabrics (Z12 2.998→2.814
  with max 10.4→9.4 at 10 seeds; P16 −0.271) — held OFF by one
  defect: on incomplete junctions accepted folds are stair-E fictions
  (P16 K100 +1.05), the Pegasus exactness gap surfacing in a new
  mechanism. Banked lesson: the s3.61 ratchet guards feasibility ONCE
  ATTAINED — on infeasible mid-states it blocked E 57k→12k over +250
  overload; the fold composite relaxes it there, absolute once
  colorable.

## 4. Method

The only rule is to find the correct algorithm based on the principles
of what makes it good. In service of that, five practices — this list
replaces the ~97 named doctrines of the old notes (archived; do not
resurrect them by name):

1. **Change one thing.** Every mechanism ships as a switch so it can be
   measured as a single flip against the shipped default. Switches exist
   for measurement, not timidity: **an obvious winner becomes the
   default immediately** (Max, 2026-08-06) — the off position remains
   only as the control arm. (this is a claude written rule. a fixed point 
   you will naturally find yourself adopting. As a human I don't really care)
   (in fact I find that I have to go through and have you purge the code
   of all the 'levers' that didn't work and flip the defaults that did)
   (I guess it's maybe nice that it's that modular. but you seem obsessed 
   with this and talk about it too much. I want talk of good ideas
   conveinient workflows are useless if you aren't creative).
2. **Measure paired.** Compare by (instance, seed) pairs against the
   real baseline (stock minorminer, or the shipped default). Unpaired
   means are survivor-biased. Verify baseline behavior against its
   source, never its paper.
3. **Say in advance what ships it.** State the outcome that would flip
   the default before running — in outcome units (final ACL, max chain,
   feasibility, wall time), never internal diagnostics. If it fails,
   it doesn't ship, however pretty the mechanism. (this is another
   'fixed point of claude' you seem to do this every time, when I just think 
   good/bad. it's pretty obvious what's bad or when you've backtracked and 
   broken something) (I honestly don't know if this has ever made a 
   tangible difference and its sort of annoying).
4. **Diagnose before building the next thing.** When a validated
   mechanism doesn't move a cell, find out why before adding another
   mechanism. Archive-then-delete what lost; keep one pipeline.
5. **No mechanism may name a graph type.** No rule may detect a clique,
   a lattice, a density threshold. Graph-specific optima must fall out
   of general rules — if they don't, the general rule is wrong, and
   that is information.

## 5. Where things stand (one paragraph, 2026-08-06)

The shipped `attraction` pipeline (spec: anatomy.md) beats stock
minorminer on the full 24k-graph library on both fabrics — ACL edge
−0.06 (P16) / −0.17 (Z12), feasibility ~2:1 in our favor. Max chain ≤
minorminer's on the 7-cell consolidation-3 board (n=3,
`data/consolidation3_probe.csv`); the sweep itself recorded no
max-chain column, so that claim is board-scope only (rescoped s3.74).
Defaults now include the aggregation-fixpoint coarsening
(`vcycle_agg`) and **cluster moves** (`cluster_moves`, s3.70 — coarse
moves on raw members through the ordinary gates: turán 8.12→6.52 at 3
seeds with the blow-up tail eliminated, expanders untouched, first
Pegasus movement). Known remaining losses: grid/honeycomb lattices (the fix
lives at init time — open question above) and dense Pegasus. Standalone
and validated but not yet in the pipeline: `ball_polish` (s3.75 —
whole-chain composite re-embedding; beats minorminer's warm grind at
equal seconds on 17/26 cells including the first fabric-agnostic
Pegasus wins). Parked: `vcycle_transport` (subsumed as ungated init;
lattice-init residual only), `bar_domains` (unblocked, unprobed),
Deleted at consolidation 4 (archive d8274198): the continuous arm, transport, hier/offsets levers. Full sweep
data: `results/batch_2026-08-05_19-43-17` and siblings; report at
`/data/max/fullember3/REPORT.md`.

Update (2026-08-14, s3.89-93): the gather orientation bit and the
INFINITE PACKER (`unbounded_pack` — drop the line-count bound, keep
hard capacity, census carries the finite fabric) are shipped
defaults; **the liquid loss is resolved** — ws/Z12 2.552 with max
chain 8.1 at 10 seeds, below stock minorminer's band for the first
time, plus P16 ws −0.46 — by deleting a constraint, not adding a
mechanism. The board deserves a fresh full sweep on the new
baseline; the s3.91 grind question and the parked fold lever deserve
re-measurement there too (several residuals were downstream of the
deleted bound). Known remaining: king_graph +0.24 under the new
packer (open), dense Pegasus, the mm legalizer/grind dependencies
(the membrane map, notes s3.92).
