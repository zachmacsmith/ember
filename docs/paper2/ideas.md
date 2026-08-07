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
   search method, minorminer included, sits 30–60% above a free
   constructive template on dense cells, and minorminer's polish cannot
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
    coarse order is real the moves fire (turán 8.10 → 6.53 at 10 seeds,
    worst-seed 7.00 vs stock's 10.09), where it is noise they are
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

## 3. Open questions — where the next ideas are needed

- **The extents object — mostly dissolved (s3.70).** The six blocked
  items needed extents only because the coarse level *summarized*;
  cluster moves never summarize, so the placement path no longer needs
  the derivation. What remains of it: the merge score's self-entry (a
  cluster-quality question now, lower stakes) and any future wish for a
  cheap summarized coarse energy (a speed play, not a correctness one).
  "When is an order real?" is likewise resolved: the E-gate answers it
  per proposal, with no discriminator machinery.

- **The init-time residual (now confirmed, s3.71).** Threshold-free
  units gave lattices proper patch hierarchies — and grid/honeycomb
  still barely moved, while everything else improved. The adjoint
  wins there (−0.90, −0.54) definitively live in *init-time* ordering,
  before any lane commitment: a post-pack gated move cannot reproduce
  them, and a pre-pack gated move judges on fictions (measured, both
  directions). The next round is the init: a safe form of
  transport-at-init — perhaps trusted exactly where cluster moves'
  accept/reject history certifies the order class as real, or an init
  whose first projection is itself order-aware.

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
  pinned at 6.8 while five other cells improved). The named next round
  prices the claim-layer cost into cluster-composite scoring: make the
  judge see what routing pays. Also banked in s3.73: the first
  dense-Pegasus improvement ever (P16 turán −0.61 via 2-D gathers),
  reaching a fabric the stride-gated exactness stack never could.

- **Fabric-side coarsening.** Only the source is coarsened today; the
  fabric coarsens naturally (supertiles with pooled capacities), and
  then every level is the same problem — coarser source on coarser
  fabric, with real capacities at every scale. Acceptance case:
  hardware_native graphs (literal fabric subgraphs with near-identity
  embeddings) are currently *lost* to minorminer.

- **Pegasus.** Everything stride-gated is inert there; dense Pegasus
  still loses to minorminer. The exactness principle's generalization
  test is coupler-aware claim aiming on incomplete (~56%) junctions.

- **The bounds as instruments.** Three lower bounds — contact (deg/κ),
  cut (wires crossing a sweep line bound every separator), treewidth
  (feasibility; busclique is its witness) — are one object at three
  scales. They are currently used only as floors in the code; as
  *certificates* they would attribute any gap to capacity-wall vs
  packing vs search, per instance.

- **Corridor pricing.** The arrange step does not price non-participant
  traversal; suspected loss mode on cluster-of-clusters sources.

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
−0.06 (P16) / −0.17 (Z12), feasibility ~2:1 in our favor, max chain no
worse. Defaults now include the aggregation-fixpoint coarsening
(`vcycle_agg`) and **cluster moves** (`cluster_moves`, s3.70 — coarse
moves on raw members through the ordinary gates: turán 8.10→6.53 with
the blow-up tail eliminated, expanders untouched, first Pegasus
movement). Known remaining losses: grid/honeycomb lattices (the fix
lives at init time — open question above) and dense Pegasus. Parked:
`vcycle_transport` (subsumed as ungated init; lattice-init residual
only), `bar_domains` (unblocked, unprobed). Full sweep data:
`results/batch_2026-08-05_19-43-17` and siblings; report at
`/data/max/fullember3/REPORT.md`.
