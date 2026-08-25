# Anatomy of the attraction embedder (v4, plain language)

Rewritten 2026-08-10 after consolidation 4 (one code path; the deleted
arms live at archive commit `d8274198`). Every section answers three
questions: **what** the stage is, **how** it works mechanically, and
**why** it is there (with a pointer into notes.md for the paper trail).
This document is meant to be interrogated — if a "how" here is not
enough to re-implement the stage, that is a bug in this file.

Code map: `placement.py` (driver), `field.py` (grid, readout, moves,
seeds, completion), `coarsen.py` (hierarchy + init), `polish.py`
(prune/shorten), `ball.py` (standalone post-processor), `trees.py` +
`loop.py` + `costs.py` (the separate `factored` router used as the
fallback rebuild and the minorminer-analysis family).

## 0. The pipeline, one sentence per step

1. **Init**: a spectral sketch of the source graph is computed once and
   immediately discarded except for its per-axis ranks — the two orders
   (x and y) that are the algorithm's entire state, initially a
   permutation matrix.
2. **Init projection** (`pack_project`): from the ranks, the books
   are derived — stair contacts, arm hulls — and the
   infinite-crossbar DP packs each axis (monotonize between them),
   then one bounded pack per axis lands the layout in the real
   window, nobody ever dropped.
3. **Arrange** (the lex engine, `seat.py`, since consolidation 7):
   strict descent on ONE lexicographic objective — capacity (brick
   ruler, demand-honest arms, wire_map pools) ordered above stair
   (junction ruler) — with the interleave jump as the unit move,
   plus swaps, single re-seats, and rigid translations; proposer and
   judge are the same evaluator.
4. **Normalizer** (`pack_project` again): one more pack projects the
   searched state into the packer-shaped family the converter and
   completion were co-designed with (s3.110 — their measured
   remaining job; capacity is already the search's invariant),
   reporting the instance's ideal fabric demand (`final_width`).
5. **Conversion**: the exact per-line converter claims actual wires —
   parity targets and corners chosen jointly per line — and completion
   runs as verifier and bridge, emitting the `certified` flag
   (converter misses 0 + deficits 0 ⇒ provably valid, known before
   any fallback).
6. **Legalization fallback** (the shrinking minorminer territory):
   only when deficits remain, capped mm legalization from our seeds,
   then an uncapped last-resort attempt — five board cells now
   provably never enter this step.
7. **Tail polish**: minorminer's warm unconstrained grind (measured
   irreplaceable for now, s3.94), then ball_polish LAST, harvesting
   the coordinated re-layouts single-chain moves cannot see.
8. **Done**: spur-pruned, validity-guarded — a broken late pass can
   never corrupt a legal result.

The ladder is coarse→fine→coarse: cluster moves teleport, the grind
polishes chains, ball re-lays neighborhoods at the end (ball before
the grind was measured worse, s3.80 — nothing may narrow the grind's
basin) (I still stand in incredible disbelief of this, surely this is 
only happening because something else is going on somewhere else and 
it's rippling to effect us here). Steps 1–4 live on the ideal infinite 
crossbar and never touch hardware facts; steps 5–8 are the adapter and its nets.

## 0.5 The five hardware facts

Everything fabric-specific reduces to these (measured; details in
fabrics.md):

1. **A qubit is a bar** — a horizontal or vertical segment on a grid.
   The hardware graph is the intersection graph of bars: couplers exist
   where bars cross (internal), abut end-to-end (external), or run
   parallel one step apart (odd).
2. **Lines carry a fixed number of lanes** (8 on course-resolved
   Zephyr, 12 on Pegasus, 4 on Chimera). More overlapping arms than
   lanes on one line means someone gets no wire.
3. **Zephyr bars have parity** (two "courses" per track, laid like
   brickwork): a claim can only land at every other position, so
   aiming a claim at a crossing must respect parity.
4. **Junctions are complete on Zephyr** (every h-bar couples every
   v-bar where they cross: K_{8,8}), **~56% on Pegasus**. On Zephyr,
   "my arm crosses your arm" arithmetic is the same as "we are
   coupled"; on Pegasus it is not. This is the only reason any
   mechanism is gated by fabric.
5. **Boundary lines have half capacity** on Zephyr (one parity only);
   the packer treats their pools as zero.

## 1. The state: integer seats (carried), orders (induced)

**What.** The algorithm's state is every variable's integer (col,
row) seat, carried directly (the s3.102 seat paradigm). The two
axis ORDERS — the v4 era's whole state — are now induced readouts
of the seats: sorting by (coordinate, id) recovers them, and the
interleave jump still operates in that order space (evict a unit,
re-splice, hand the value multiset back by rank).

**How.** In memory: a dict of positions `{v: (x, y)}`, integers
after every pack and every move; a test enforces that post-arrange
positions are integer line indices.

**Why.** Three failures traced to richer state: continuous coordinates
made capacity invisible before packing (moves were judged on layouts
that could not exist), displacement-based packing anchored each step to
the previous positions (early commitments compounded — "the first
projection is nearly irrevocable"), and the continuous phase had no
honest stopping rule (its energy decreases monotonically toward total
collapse; any step count is a hidden density knob — measured, notes
s3.75). Moving to orders deleted all three problem classes and won the
board on both fabrics (notes s3.76). Everything derivable is a readout,
never state (ideas §2.3).

## 2. Init: continuous points, used once, for their ranks

**What.** A starting pair of orders, produced by ranking a quick
2-D sketch of the source graph.

**How.** Two routes to the sketch:
- On course-resolved Zephyr (`vcycle=True` and stride 2): coarsen the
  source (§4.5's hierarchy machinery, aggregation variant), lay out the
  small quotient graph with a spectral embedding (eigenvectors of its
  Laplacian; circle fallback for degenerate spectra), then spread each
  supernode's members in a small disc around it using golden-angle
  (sunflower) offsets.
- Otherwise: a spectral layout of the whole source (sparse eigensolver
  above n=300), scaled into the target's box.
Then, per axis, sort the points by (coordinate, id) and replace each
coordinate with its rank. The continuous sketch is discarded.

**Why.** The init's only job is to hand the moves a starting order in
which "close in the graph" roughly means "close in both orders."
Spectral sketches do that; ranking removes their scale, which is pure
gauge. Two measured negative results justify the shape: deriving orders
from the hierarchy directly (a dendrogram walk) lost broadly — a 1-D
linearization destroys the 2-D structure spectral ranks carry (s3.77) —
and the within-disc offset pattern barely matters at all (spiral vs
random vs grid: near-inert; evenness helps only on giant twin blocks —
s3.78). So the init is deliberately unclever: coarse geometry plus
membership, nothing more. Results must survive a random init anyway
(insertion moves recover block structure — s3.36).

## 3. The readout: from orders to a physical layout

This is the heart. Given the two orders, three derivations run in
sequence, and together they are called the "books" — the single set of
records every other stage reads (one accounting, ideas §2.7).

### 3a. Contacts (the stair rule)

**What.** For every source edge, a decision about which endpoint's
horizontal arm meets which endpoint's vertical arm.

**How.** For an edge (u, v): if u is *below* v in the y-order (ties
broken by id), then u reaches v with its horizontal arm, and v reaches
down to u with its vertical arm. So each variable's h-arm must span the
*columns* of its y-above neighbours, and its v-arm the *rows* of its
y-below neighbours. Every edge is assigned exactly one designated
crossing.

**Why.** This is busclique's diagonal construction generalized: on a
clique laid along the diagonal it reproduces the optimal template
exactly, and on sparse graphs it decays gracefully into short local
arms. Paying for each edge once (instead of at both possible crossings)
halved seed cost when introduced (s3.34). The rule depends only on the
y-*order* — which is what makes orders a sufficient state.

*Lever (s3.99, default OFF):* `orient_flips` relaxes the y-keying —
per-edge orientation bits initialized from the rule, improved by a
strict-descent flip pass on raw hull spans (never worse than the rule
at seed level; contacts stay a derived readout). Measured mixed: wins
king/spin_glass/P16-ws, regresses dense K100 both fabrics — the flip
pass is un-gated inside the readout and the claim-margin blind spot
(s3.73) has no voice there. See notes s3.99 and the attraction.md row.

### 3b. Bars

**What.** Each variable's two arm intervals: h-arm = [leftmost needed
column, rightmost needed column] on its own row; v-arm likewise on its
own column.

**How.** The h-interval is the hull of the variable's own x-position
and the x-positions of its h-contacts; symmetric for v. Two
adjustments: (1) a capacity floor — a chain of L qubits can host at
most ~kappa·L couplers (kappa = the fabric's fresh-contact rate per
tile), so total arm length is widened to at least deg/kappa − 1,
split evenly; (2) an occupancy footprint — any arm narrower than one
tile is widened to width 1, because a bar occupies its tile even when
its interval is a point (without this, point arms are invisible to the
capacity census and the packer can pile everyone onto one line — the
measured P16 collapse, s3.76).

**Why.** Arms are readouts, not state (s3.31). The floor is counting,
not tuning: it is the minimum length physics allows given the degree.

### 3c. The packer (the infinite-crossbar DP, s3.93)

**What.** The readout's core: given the two orders, assign every
variable a row and a column — exactly the cheapest assignment those
orders allow, under hard lane capacity. It is the order's PRICE TAG:
moves propose orders, this step says what each is worth, the gate
compares. Packing happens on the IDEAL crossbar (uniform lanes, as
many lines as needed), so it always succeeds; the finite chip enters
only through the census (3d) and one final projection.

**The objects, in words** (rows below; columns are the mirror):

- **The lineup.** The variables in y-order. Packing y = seating the
  lineup into rows, in order: each row takes one contiguous group
  (order preservation), and a row is the home of its members' h-arms.
  The only decisions in the whole problem are where each row's group
  ends.
- **The coefficient.** One integer per variable: (#hulls it tops) −
  (#hulls it bottoms). Total arm length is a sum of hull gaps; folded
  per variable (the accordion), it becomes Σ coefficient × row — each
  variable carries its own separable term, fixed by the order. This
  fold is what makes tiny DP states possible: no joint hull
  bookkeeping survives it. Safety comes with it: every hull donates
  one +1 and one −1 (translation invariance — elevation never pays),
  and order preservation keeps every gap ≥ 0.
- **The window.** For each possible group-end, the earliest legal
  start. Capacity (arms ≤ 8 deep) is monotone — growing a group never
  fixes it, shrinking never breaks it — so legal starts form an
  interval whose left edge only moves right. One two-pointer sweep
  computes it; the depth inside is maintained incrementally (segment
  tree, s3.92).
- **The scoreboard.** The DP table, two indexes: best[rows used]
  [variables seated] = cheapest arrangement seating that many in
  those rows. Two indexes because both resources are metered:
  banking a hull-bottom's negative term high up also SPENDS rows,
  and everything unpaid must then sit higher still — the escrow that
  makes mid-table negatives safe. Cell values are ledgers, not
  energies: candidates within one cell owe identical futures, so
  ledger differences are total differences.
- **The queue (deque).** Pure speed, zero authority. A cell's SEAT
  option asks "cheapest legal place this row's group could have
  started" — a min over a window that only slides right, the
  textbook sliding-window minimum. Each queue item is an IOU ("this
  row could open here"), valued by scoreboard-below minus
  cost-prefix; an IOU dies from the front when capacity outlaws it,
  from the back when a younger one arrives no more expensive (it
  could never win again). What remains is the staircase of
  still-rational new-row decisions; the front is the answer. Delete
  the queue and scan the window instead: same table, same answers,
  just O(n) slower.

**The algorithm.** Two nested loops — rows outer (bottom to top),
lineup inner (left to right). Every cell is one min of two options:
CARRY (this row seats nobody new — copy the cell below) or SEAT
(group from the queue's front through here — scoreboard at the start
plus group coefficient-sum × row). Cells are written once, never
revised: "join the row" is a group silently extending; "take a new
row" is a carry followed by a start chosen one row up. Competing
hypotheses coexist in different cells until the future EXTENDS the
cheaper one — revision is replaced by superposition, which is why no
flip-flop is possible inside a pack. At the end, the final cell is
the exact minimum and recorded choices are walked backward to read
off each variable's row. No iteration inside a pack; the x/y
ALTERNATION around it (rows need frozen column extents, and vice
versa) is coordinate descent — energy monotone under the accept
rule, no convergence theorem, capped at arrange_iters.

**Boundary conditions.**
- *Bootstrap:* ranks are already coordinates in a stretched gauge;
  the first pack collapses the gauge. (Permutation-matrix framing,
  Max 2026-08-14: the init IS a permutation matrix; packing relaxes
  it toward the best ≤8-per-line matrix that fits the window; the
  alternation is Sinkhorn's silhouette; the crystal is the identity.)
- *Ideal fabric (s3.93):* uniform pools on real-lines + ⌈n/8⌉
  virtual lines — always enough (groups of ≤8 always fit), so nobody
  is ever dropped and the s3.92 straggler class is structurally
  gone. Layouts anchor at line 1: line 0 is a boundary line
  (hardware fact; anchoring there broke turán 6.00→6.70).
- *Projection:* after the arrange loop, one forced bounded pack per
  axis (real pools, boundary zeroing, clamp) lands everything in the
  real window. `final_width_x/y` first records the ideal demand
  (turán 12, grid 9, K100 13, ws 22-25 of 25) and
  `projection_misses` the residue.

**Why this and not greedy.** The step's job is evaluation, not
compaction. State = orders requires positions = derived-BEST: a
greedy packer turns the gate into a lying judge (its error is noise
over the order signal — measured, s3.59/s3.73 — and first-fit
misprices exactly the orders whose value hinges on ending a row
early, the ones the moves must discover). Within its model class the
abstraction is lossless: any cross-shaped line-level embedding is
order-preserving for the order it induces, so minimizing packed cost
over orders IS finding the model-class optimum; the residual gaps to
the true optimum are orientation freedom, shape freedom, and qubit
granularity — all outside this layer. Lineage: displacement packer →
exact bounded DP (s3.59) → repairs (s3.92) → line-count bound
deleted (s3.93: ws 3.037→2.552 at 10 seeds, the first
sub-minorminer liquid).

### 3d. The overload census

**What.** The feasibility term in every accept/reject decision.

**How.** Group the bars by their line; on each line compute the maximum
number of arms that overlap at any point (an interval-sweep) minus the
line's lane count; square any excess and sum. The gate energy is
`stair energy + overload_lam × census` (default weight 1.0). It is
priced into evaluation only — nothing descends on it.

**Why.** Gates that cannot see infeasibility accept configurations the
claim layer cannot build; pricing overload into every gate made a whole
annealing mechanism unnecessary (s3.57). The census reads the same
books as the packer and the coloring. Since s3.93 it carries a second
duty: it is the ONLY place the finite chip exists during arrange —
the packer works on the ideal crossbar, and lines outside the real
window (pool 0 here) or over their real pools are priced by the
census alone, so the E-gated moves are what condense an unbounded
layout onto the chip. Part of what minorminer's legalizer used to do
— making the embedding FIT — now happens here, before any embedding
exists.

## 4. The moves (the lex engine, seat.py — since consolidation 7)

All moves run inside `seat_arrange`, all are judged by ONE evaluator
(`seat_energy`: the lexicographic scalar pen·2^26 + stair — capacity
at the brick ruler with demand-honest arms and wire_map pools, stair
at the junction ruler), strict descent, deterministic; the deadline
is checked between move batches. The packer (`pack_project`) runs
once before the search (init projection) and once after (the family
normalizer the converter stack requires — s3.110); edge_monotonize
lives inside the pack, between its two unbounded per-axis passes.

- **Interleave jump (`best_interleave`, the unit move, s3.111).**
  Evict a hierarchy unit from one axis's coordinate order and
  re-insert it at the exact optimum over ALL interleavings with the
  rest (`align_reinsert`'s DP: induced-rule pricing on y, frozen
  contacts on x, forward and reversed block), handing the same value
  multiset back by rank; the DP's stair-optimal candidate is audited
  by the reference evaluator. A JUMP: it lands on the final state
  without traversing overloaded intermediates, so the hard capacity
  key cannot path-block it — jump + hard key together reach the
  turán crystal that either alone misses (s3.111b).
- **Swap sweeps.** Pairwise seat swaps over source edges, three
  variants (x/y/both) — including the y-swaps that flip contacts,
  priced exactly.
- **Single re-seats (`best_seat`).** One variable, every in-window
  seat: fast prefix-array scan, exact audit of the top candidates.
- **Rigid translations (`best_translate`).** One unit, every
  in-window offset; cross-boundary contact flips priced in full.

Ladder (s3.81): the coarse move (interleave, coarsest units first)
runs to its own fixpoint before the fine moves are released.

## 5. Seeds, aiming, completion

### 5a. Coloring (bars → actual qubits)

**What.** Turning each arm interval into a claimed run of physical
qubits on one wire.

**How.** Per line: sort the arms by left endpoint; walk them in order,
giving each arm the first lane (sub-wire) that is free — arms whose
intervals do not overlap may share a lane. This "interval coloring by
left-endpoint sweep" is exact for interval graphs and costs
milliseconds. The chosen lane's qubits across the interval are claimed
(skipping any qubit already claimed). Every variable is guaranteed at
least one qubit afterwards (nearest-free fallback).

**Why.** The name "coloring" sounds expensive; the mechanism is a
sort and a sweep. It is exact because arm conflicts on one line form
an interval graph, whose optimal coloring greedy-by-left-endpoint
achieves.

### 5b. Snap aiming (Zephyr only)

**What.** Choosing lanes and claim ranges so that each designated
crossing lands on a coupler *at claim time*.

**How.** Zephyr's parity fact (§0.5.3): a lane of parity s can couple
a crossing line c only at position c (parities agree) or c−1 (they
differ). When coloring an arm, prefer the free lane that covers the
most of the arm's designated crossings under that arithmetic, and
widen the claim hull to include the parity-exact positions.

**Why.** "Aim, don't repair": with aiming on, the completion pass
(next) finds nearly nothing to fix — extensions dropped to ~0 when
this shipped (s3.56).

### 5c. Completion and the mm-skip gate (Zephyr only)

**What.** A deterministic pass that drives the seeded chains to a
provably valid embedding, so minorminer's legalizer can be skipped.

**How.** Three passes of pure interval arithmetic over the claimed
runs: connect each chain's own h-run and v-run at their cheapest
feasible crossing (corner pass); for each still-uncovered source edge,
extend the cheapest of the four run-pairs until the crossing coupler
exists (edge pass); bridge the residue through one or two free qubits
(bridge pass). If the deficit counters reach zero and the full
validity check passes, the seeds ARE the embedding — minorminer
legalization never runs (`mm_skipped`).

**Why.** On Zephyr, junctions are complete, so crossing arithmetic *is*
adjacency — validity by construction beats legalize-and-repair
(ideas §2.5). On Pegasus (~56% junctions) the same arithmetic would
claim couplers that do not exist, so the stage is gated off there —
the one fabric gate left, and it encodes a hardware fact, not a tuning
choice.

## 6. The routing tail

**How.** If the gate did not fire: stock minorminer legalizes the
seeded layout (`initial_chains`, patience 0), capped at `round_frac`
(default half) of the budget so the polish cannot be starved. If
nothing legalized: one uncapped fallback attempt from
nearest-qubit-per-variable seeds. Then spur-pruning (delete qubits a
chain no longer needs), then stock minorminer's full grind runs
warm-started and *unconstrained* with the remaining budget, followed
by a validity guard (a broken finishing pass can never corrupt a legal
result).

**Why.** The placement must improve the endpoint of an unconstrained
polish or it was not a real improvement (free-polish doctrine, s3.22).
Minorminer's polish is still the strongest local shortener we have not
yet replaced; its economics (78–95% of its own runtime, ~29–40% ACL
earned) are in mm-internals §6.

## 7. ball_polish (standalone post-processor)

**What.** A composite improvement move on any finished legal
embedding: evict the whole chains of a small variable set, rebuild
them jointly against everything else frozen, keep the rebuild only if
total real chain length strictly drops.

**How.** One question per chain, regenerated from the live embedding
at the start of every pass (v3, s3.83): the chain's obligation hull —
its footprint's bounding rectangle, extended per source neighbour to
the nearest line that neighbour's claimed runs occupy on each axis —
selects as members every chain with a tile inside. No windows, no
size caps, no inflation: the hull is derived, so questions scale with
each chain's own situation and cliques self-gate to free no-ops
(all-chain balls have no frozen boundary and trim away).
Candidates are trimmed so every component touches the frozen world.
Rebuild is bars-first: members get positions from the median of their
frozen obligations, arms from the stair rule, wires from the coloring
run in frozen-aware mode (a lane is admissible only if its qubits over
the claim range are unclaimed), completion scoped to the members
(Zephyr), then a scoped verify; if the bar rebuild rejects, a
router-based rebuild (Steiner trees over free fabric only) is tried as
fallback. Accept on strict total decrease after member-scoped
spur-pruning; a final whole-embedding validity check backstops
everything. Deterministic; fixpoint reached means a second call
accepts nothing.

**Why.** Tearing one chain leaves a chain-shaped hole that refills in
its own image; tearing a region lets the interior re-crystallize —
this is the coordinated move minorminer structurally cannot make. It
is judged directly on qubit counts, so no proxy exists to lie.
Measured: beats giving minorminer's grind the same seconds on 17/26
cells, never harmful, first fabric-agnostic Pegasus wins (s3.75);
bars+fallback beat both pure arms (s3.77). Not yet wired into the
pipeline's tail — that replacement is a named open item.

## 8. Knobs (complete list — 12) and diagnostics

`round_frac=0.5` (budget fraction before the polish), `kappa=None`
(derived from the fabric), `span_floor=True`, `exact_seeds=True`
(Zephyr gate), `snap_claims=True` (Zephyr gate), `vcycle=True`,
`vcycle_agg=True`, `cluster_moves=True`, `cluster_units=True`,
`init_mode="spectral"`, `tail="mm+ball"` ({"mm+ball", "ball+mm",
"mm", "ball", "none"}), `ball_singles=False` (s3.91 lever).
Consolidation 5 (archive 09467299) deleted strain_rank,
submit_seeds, fold_moves, the ball-rng tails and the crossfinder
driver; consolidation 6 (archive 5be76754) deleted orient_flips,
align_insert and cap_pressure; consolidation 7 (archive 12fe484c,
purge 37d3439c) shipped lex+interleave as THE engine and deleted
arrange_mode, interleave_moves, brick_plane, align_moves,
census_required, arrange_iters, insert_sweeps and overload_lam with
the orders court (verdicts in attraction.md). Unknown kwargs are
ignored (old probe scripts degrade gracefully).

Diagnostics (`diag`): `extent_mean`/`extent_max` (bar widths),
`stride` (2 = course-resolved Zephyr), `E_interp`/`E_contract`
(stair energy at init), `max_chain`, the walls, the engine counters
(`seat_accepts`, `trans_accepts`, `swap_accepts`,
`interleave_accepts`/`_declines`/`_noops`, `seat_passes`,
`seat_fast_miss`, `accept_traj`, `seat_pen`/`seat_stair` — pen 0
certifies the feasibility invariant held), the normalizer pack's
fit observables (`final_width_x/y`, `projection_misses`,
`unb_miss`), and on Zephyr `mm_skipped`, `deficit_edges`,
`corner_deficit`, `extensions`, `ext_qubits`, `bridges`,
`convert_miss`, `certified`.

## 9. Lineage of the engine (s3.102 → s3.112)

The lex engine descends from the s3.102 "seat engine" research
vehicle through three measured rounds: the brick ruler (s3.107-109:
capacity quantized to the fabric parity period — a brick holds one
junction of each parity, so whole-brick promises cannot be
parity-infeasible; demand-honest arms; wire_map pools), the
lexicographic objective (s3.110: capacity ordered above stair, λ
deleted; alone it was path-blocked out of the crystal basin), and
the interleave jump (s3.111: the insertion DP resurrected where
proposer == judge; jump + hard key are complements — s3.111b
measured 6.000/10-seed turán, either alone loses it). Consolidation
7 (s3.112) shipped the combination as the only engine and deleted
the orders court. Two structural facts carried out of the era: the
packer's remaining job is FAMILY NORMALIZATION, not capacity
(s3.110: pen-0 states convert at 578 deficits raw, 0 after one
pack, pen preserved — the converter/completion stack is co-designed
with packer-family states), and its deletion belongs to a future
lex-family converter (spill-aware per-line brick seating), which
would also retire the classed active-set DP.

## 10. Known gaps

See ideas.md §3 for the live list. The load-bearing ones: the polish
is still minorminer (ball_polish is the replacement path); the
normalizer pack and the converter's classed DP are the last
two-court seam (the lex-family converter deletes both); Pegasus is
WRITTEN OFF as of consolidation 7 (owner's call, s3.112 — the lex
engine runs there but regresses; the elegant-adapter idea is parked
in ideas.md, unblocked by coupler-predicate cover accounting if
Pegasus ever matters again).
