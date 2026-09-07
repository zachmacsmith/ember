# History of the attraction embedder (hand-off, written 2026-09-07)

This is a condensed, chronological account of how the `factored` engine
came to be what it is, written for someone who has never seen the
project. Its job is twofold: explain WHY the current design
(`packages/ember-qc/src/ember_qc/algorithms/factored/plane.py`) looks
the way it does, and list what was already tried and refuted so nobody
re-derives it. Every claim cites the chronicle (`docs/paper2/notes.md`,
entries "3.N", cited here as "notes s3.N") or the verdict ledger
(`docs/paper2/attraction.md`). Numbers are copied from those files; the
artifact paths they cite live under `docs/paper2/data/` and
`docs/paper2/archive/`.

Read alongside: `docs/paper2/ideas.md` (the one-page spec and
principles), `docs/paper2/anatomy.md` (the as-built pipeline),
`docs/paper2/fabrics.md` (measured hardware facts),
`docs/paper2/mm-internals.md` (what minorminer actually does),
`docs/paper2/dp-internals.md` (the s3.117 audit of the two DPs).
`docs/handoff/OPEN_FRONTS.md` is the forward-looking companion.

## 0. Vocabulary

The notes use in-house words. Translation:

| word in the notes | meaning |
|---|---|
| ACL | average chain length (the primary metric); "mx" = max chain length |
| cell | one benchmark instance on one fabric (e.g. `ws_n486` on Z12); a "board" is a set of cells × configurations; an "arm" is one configuration under test; a "probe" is a measured experiment with a CSV in `data/` |
| Z12 / P16 / Z3 | Zephyr Z12 (the main fabric), Pegasus P16, Zephyr Z3 |
| bar | a qubit: a horizontal or vertical segment on the fabric grid (fabrics.md §0) |
| lane / line / wire / brick / stride | a line is a row or column of the fabric; it carries 8 wires on course-resolved Zephyr, counted per brick (the parity period: 2 junctions on Zephyr = `stride` 2; 1 elsewhere) |
| junction | where a row crosses a column; complete bipartite K_{8,8} on Zephyr, ~56% complete on Pegasus |
| stair rule | the rule deriving chains from positions and the y-order: the endpoint lower in the y-order reaches sideways, the higher reaches down; one designated crossing per edge |
| books | the per-variable accounting: contacts, bar hulls, and the claim intervals `(line, a, b, v)` per orientation (`arm_books` in field.py) |
| packer / pack / readout | the DP (`pack_lines`) that assigns each variable a line on one axis, order-preserving, under hard per-brick capacity; "readout" = orders → positions via the packer |
| judge | the objective evaluated on the packed state: lexicographic (overload, chain length) |
| proposer | the interleaver DP's estimate on a frozen picture (other axis fixed, occupants moving) |
| court | a subsystem that evaluates and accepts or rejects proposals; "two courts" = proposer and judge disagreeing |
| lever / knob / switch | a config flag; "default off/on" = whether the shipped path uses it |
| crystal | the exact template layout for turán/cliques (straight runs on one sub-lane, blocks all-horizontal / all-vertical) |
| liquid | cells like `ws_n486` (Watts–Strogatz) and `regular_n316`: sparse, no imposed order, long shortcut edges |
| template / busclique | D-Wave's constructive clique/biclique embedding; the constructive optimum on dense cells |
| the grind | minorminer's warm-started chain-shortening pass (`improve_chainlength_pass`) |
| ball / `ball_polish` | our tail move: evict a small set of whole chains, rebuild jointly, accept iff total length drops (ball.py) |
| tail | post-processing after a legal embedding: `tail="mm"` = grind then ball; `tail="none"` = the engine's own answer |
| skip gate / certified | on Zephyr a zero-deficit completion is a proof of validity; minorminer legalization is skipped (`mm_skipped`) |
| deficit edges | source edges the seeds + completion could not realize with a coupler |
| pen | the overload term of the judge: Σ max(cover − pool, 0)² per (line, brick) |
| fixpoint | a pass with zero accepts — the stop certificate |
| asks / work budget | DP evaluations; `max_asks` is the budget (never seconds) |
| bookmark | the best (pen, stair) state seen; what the engine returns |
| units / N(v) | the sets a move re-inserts: contiguous runs of an order at dyadic scales, and each variable's neighbourhood |
| bag / ladder / rung | orders of asking units in a pass: bag = one shuffled list (current); ladder = coarsest-first fixed order (old); rung = shuffled within a scale |
| the fold | minorminer's measured mechanism on liquids: hundreds of small relocating chain moves that jointly re-layout so long edges become short (s3.87) |
| tol | probe tolerance: max(0.3, 0.05·baseline) ACL |

Cell names on the standard 10-cell Z12 board: K100, K140, ER100_d10,
turan_n162 (≈ K_{81,81}), spin_glass_n163, regular_n316, ws_n486,
grid_200, honeycomb_200, king_graph_196 (`docs/paper2/data/rewrite_board.py`).

## 1. Origins and the geometric premise (notes s3.1–3.21)

The project began as a cost-function study of minorminer. The
first result was negative and it set the whole tone: adding a history
term to minorminer's qubit pricing is a wash (300 paired runs, ΔACL
−0.008, s3.13) because randomness and memory are substitutes — the
program already has the former. Reading the shipped C++ (s3.14–3.17,
`mm-internals.md`) found that the 2014 paper is a sketch, not a spec:
the constructor is a nearest-attach Steiner build; 78–95% of wall time
is the post-legality shortening phase; the legal-stage ACL carries no
information about the polished ACL (r ≈ 0), which killed best-of-N
before it was built (s3.16). Two lessons that never went away: verify
every claim against the source, never the paper; and paired measurement
only (unpaired means are survivor-biased, s3.11).

The positive premise came from s3.18–3.21: a placement (a global,
joint decision) can do what one-chain-at-a-time search structurally
cannot revise; density-limited attraction descends and beats a
same-budget unguided control (s3.19). The regime map (s3.21): fixed-
degree random graphs are cut-bound — ACL is Θ(n) for every embedder,
only the constant is winnable — so structured sources are the home
turf. That bet is what the whole benchmark board was chosen to test.

The hardware premise is in `fabrics.md` and was learned painfully
(s3.49, the "j-fold incident"): a qubit is not a node, it is a bar; the
hardware graph is the intersection graph of bars; junctions on Zephyr
are complete K_{8,8}; lane arithmetic gives the constructive optimum for
a biclique directly — K_{81,81} needs ⌈81/16⌉ = 6 bars per chain, so
turán n162's optimum is ACL 6.00 exactly (fabrics.md §4.4). "6.000 on
turán" throughout the notes means the engine found that construction
from general rules.

## 2. The positions / contraction era (notes s3.22–3.75)

State = continuous 2-D positions per variable, moved by attraction
with a density term, then discretized. The main developments, with what
each taught:

- **v3 hybrid ships and the first full sweep** (s3.22–3.23): geometry
  followed by stock minorminer legalization and unconstrained polish
  (the placement must improve an unconstrained polish or it was not
  real — "free-polish doctrine"). Wins on structured cells, large
  losses on dense: the dense representation was named the top defect.
- **The constructive ceiling** (s3.26): every search method sits 8–57%
  above the busclique template on dense cells and minorminer's polish
  cannot improve the template. Dense is representational; searching
  harder is the wrong instrument. This became principle 2 of ideas.md
  (make the construction emerge from general rules; never hardcode it).
- **Representation ladder** (s3.28–3.31): extents as state failed
  twice (gradient flow cannot break the row/column permutation
  symmetry); the missing physics was contact capacity; the fix was the
  **span state** — extents demoted to a readout of positions, the
  energy becomes the real chain length. Principle 3: anything derivable
  from the state is not state.
- **Product mode and the diagonal** (s3.32–3.35): alternating exact
  1-D packing replaces the continuous field; the staircase readout (one
  designated crossing per edge) halves seed mass; diagonal alignment
  with an insertion-order search gave the first K100 win over
  minorminer; adjacent swaps proven plateau-bound. **Init-independence
  became the standard** here.
- **The move set generalizes** (s3.36–3.40): best-insertion sweeps make
  block separation emerge from random init; post-hoc wire matching
  cannot reach the constructive optimum (geometry and wires must be
  co-designed, s3.37); per-edge monotonization with leverage ∝ edge
  length replaces every cluster-aware rule.
- **The pressure detour** (s3.41–3.47): differentiable capacity
  penalties are gradient-blind inside uniform overload (only the rim
  peels — "Gauss's law"); per-edge contact state lost to corners-only at
  1/60th the state. Gauge freedom is the optimizer's enemy.
- **The Zephyr reset** (s3.48–3.50): the adversary was busclique, not
  minorminer (template turán 6.00 vs mm 12.01 vs ours 14.03). The
  adapter's folded coordinate was a hard 2× ceiling; unfolding the
  courses lifted quality and feasibility at once (turán 13.30 → 10.02;
  K140 0/3 → 3/3 legalized). Principle 4: the representation can be the
  ceiling — check it before tuning the optimizer.
- **Contraction and validity by construction** (s3.51–3.57): contract
  before the first pack (cycle 0 is the whole mechanism; first K100 win
  on Z12); exact seeds — on junction-complete fabrics coverage =
  validity, so minorminer can be skipped; snap (aim parity-exactly at
  claim time; the repair pass becomes a verifier); overload priced into
  every gate made order-annealing unnecessary.
- **The exact packer** (s3.58–3.59): an exact order-preserving DP under
  hard integer pools plus ONE shared census — K140 lands below the
  template quote; lane oversubscription abolished structurally.
  Principle 7: one accounting.
- **V-cycle, consolidations, full sweep 3** (s3.62–3.67): coarse level
  decides topology, fine decides metric; bars rewritten in outcome
  units (final ACL, max chain, feasibility, wall) after the exactness
  gate had quietly become the objective (s3.65). Full sweep: 140,685
  rows, ACL −0.06 (P16) / −0.17 (Z12) paired vs stock minorminer,
  feasibility ~2:1 in our favour; the loss block = geometric lattices
  and dense Pegasus.
- **Aggregation, adjoint transport, cluster moves** (s3.68–3.73):
  leader aggregation replaced twin-hash + matching; adjoint transport
  landed turán 6.00 and fixed the lattices but transmitted noise orders
  on expanders (regular +0.74) — parked. **Cluster moves** (coarsen the
  MOVES, not the state, s3.70): a cluster is a set of real nodes
  gathered as one proposal, judged by the same gates; no sizes are ever
  guessed. Generous (threshold-free) merging; per-member affinity
  criterion shipped by correctness decree even though its deep
  hierarchies exposed a consumption defect (s3.72); strict descent and
  no schedule rules (s3.73).
- **The audit purge** (s3.74): every quantitative claim re-checked
  against artifacts; a contaminated layer in s3.70–3.71 corrected in
  place. Standing rules from it: a number enters the notes only with an
  artifact path; never splice an X→Y delta from two runs; n=3 cannot
  support a ±0.1 verdict; seed-0 smoke is not a verdict.
- **Ball polish and the death of the continuous state** (s3.75):
  `ball_polish` beat minorminer's warm grind 17/26 cells at equal
  seconds; the lattice residual was confirmed order-level. The rider
  probe `contract_stable` refuted plateau stopping — stair energy
  descends monotonically toward collapse, so no internal signal can
  stop a continuous phase honestly; every step cap is a disguised
  density knob. Max's course: remove the continuous state; state wants
  to be two orders plus lanes.

## 3. The orders era (notes s3.76–3.101)

### 3.1 State = two orders (s3.76–3.79)

`order_state` (s3.76): init points reduce to per-axis ranks, no
contraction, the packer packs with the TRUE stair objective, which is
LINEAR given the orders (`_axis_coeffs`: E = Σ c_v·pos_v for any
order-preserving assignment). Result in one flip: turán 6.023 at 10
seeds, the lattice block fell (honeycomb 1.81 → 1.09, king 2.36 → 1.53,
grid 1.41 → 1.12), the largest Pegasus movement ever; expanders paid
+0.16/+0.40. Default flipped with Max's remark that it should be the
default even if it lost, because a loss would locate the error
elsewhere. Then: hier init refuted (a dendrogram linearization destroys
the 2-D geometry, s3.77); the golden-angle offsets refuted as
load-bearing (s3.78); consolidation 4 deleted the continuous arm
(s3.79, archive `d8274198`).

### 3.2 The tail and the grind (s3.80–3.88)

A long arc on what minorminer's grind owns. ball-before-grind traps the
grind's basin (turán +0.59, ws +0.87) — refuted; grind-then-ball
(`mm+ball`) wins or ties every cell — shipped (s3.80–3.81). Replicating
the grind's randomness at ball scale (s3.82), completing the ball's
question set (s3.83), a native shortener (s3.84), an exact lane audit
(s3.85) — every move-level factor was eliminated one by one. The
autopsy (s3.86) found the answer upstream: the raw seeds on liquids
carried monster chains (ws max 46) and the grind does not polish them,
it re-embeds them; s3.87 named the mechanism — **the fold**: hundreds
of small relocating strictly-improving chain moves whose composition is
a global re-layout that collapses long shortcut edges (all 16 >10-tile
ws edges collapse to max 7.3 post-grind). s3.88: from a trivial init
the crystal cells improve (turán exact 6.000 on 10/10 — "the best dense
init is no init") while geometric cells regress; the fold cannot be
reached by real-judged moves from any origin.

### 3.3 Orientation bit, folds, crossfinder (s3.89–3.91)

The move family was translations-only; a reversal cannot be composed
from translations under strict descent, so the fold was unreachable by
construction. The gather orientation bit (every gather offers its
reversed block) shipped at zero cost (ws −0.113, grid −0.090). The
two-axis hairpin fold moved ws on both fabrics but produced fictions on
Pegasus's 56% junctions (P16 K100 +1.05) and was later deleted when it
won nothing on the s3.93 baseline (s3.98). Crossfinder (s3.90) built
rip-and-replace as the whole algorithm at cross granularity: sparse
structured cells legal and near-optimal in seconds, but liquids and
dense never legalized — straight crosses cannot route around load, and
exclusive claims delete minorminer's load-bearing feature, overlap.
Grind removal (s3.91, re-measured s3.94): dead weight on dense
(ties at 6–20× speedup), irreplaceable elsewhere.

### 3.4 The infinite packer (s3.92–3.93)

s3.92 diagnosed two packer defects on ws (stragglers that never fit
again; a feasibility pass re-sorting its window at every step) and a
pipeline bug (seeds discarded on liquids). s3.93 named the root cause:
even when the optimum fits, the INITIAL layout can demand more fabric
than exists, and a bounded DP's only recourse was dropping variables.
The design: keep lane capacity HARD, drop the LINE-COUNT bound (with
unbounded uniform lines, hard-capacity packing is always feasible — the
L_max lemma), let the census price the finite fabric (unknown lines at
pool 0), project once into the real window at the end. Anchor at line
1, not 0 (line 0 is a boundary line; anchoring there broke turán 6.00
→ 6.70). Verdict: **ws 3.037 → 2.552 with max chain 10.7 → 8.1 at 10
seeds — the first sub-minorminer liquid result**; turán 6.000 on 10/10;
king +0.237 the one regression. This "search on the ideal plane, price
the finite chip" idea is the direct ancestor of the s3.116 plane engine
and of the current `_line_profiles(bounded=False)`.

### 3.5 Converter, certificate, consolidation 5 (s3.95–3.98)

The exact per-line converter v2 (s3.96: required-hull claims + a
classed active-set DP) made corner deficits 0 on every cell and let ER
legalize natively for the first time; dense wins came from shedding
padding (K100 −0.26, K140 −0.27, spin_glass −0.31). The certificate
(s3.97: converter misses 0 and completion closed ⇒ valid) shipped as an
observable; the same census as a gate term was inert (±35 vs stair in
the thousands). Consolidation 5 (s3.98, archive `09467299`) made the
winners unconditional and deleted the refuted levers.

### 3.6 Orientation flips, alignment reinsertion, the truth round (s3.99–3.101)

`orient_flips` (un-gated per-edge orientation flips inside the readout)
won where geometry was frustrated and regressed dense K100 on both
fabrics: un-gated by construction, judged on raw hull spans only — the
claim layer had no voice (s3.99). **Alignment reinsertion** (s3.100):
remove a unit from an axis order and re-insert it at the exact optimum
over ALL interleavings with the rest (both sequences keep internal
order; the reversed block competes), with induced-rule pricing on y
(contacts re-derived per candidate) and frozen nets on x; exact by
brute-force oracle. After a profiled perf round (s3.100b: the hog was
`edge_monotonize` re-reducing spans, not the DP) it flipped to default.
That DP, `align_reinsert` in field.py, is the one move of the current
engine. The truth round (s3.101) measured the gap between the proposer's
capacity-blind view and the judge: 87–99% of reverts on sparse cells
were capacity-side; a capacity pressure inside the DP won liquids but
distorted ER (+0.577) by swamping energy gaps — the birth of the "no λ"
rule.

## 4. The seat / lex engine and the brick ruler (notes s3.102–3.112)

### 4.1 The seat engine and its judge (s3.102–3.106)

The three-level orders architecture existed to make two DPs possible
by freezing what they could not carry. The alternative (s3.102):
crossfinder's loop with the state on the ideal plane — carried integer
seats, capacity a COUNT, one objective, proposer == judge, strict
descent. A ~250-line engine won K100 −0.170 and ER −0.173 at its first
board but lost the turán crystal decisively (+1.91): the twin-block
diagonal order needs order moves, not re-seating. s3.103 borrowed one
full orders iteration as a single proposal and landed 6.000 — later
shown to be path luck (s3.104): **the seat objective preferred the
stalled ~7.4 layout (1704) to the crystal (1766)**. Converting both
through the real claim path showed the true separator was
completability (the stalled state left 73 deficit edges). The deficit
autopsy (s3.106) found the failing class general: arm truncation far
beyond the one-junction parity slack, not local parity misses.

### 4.2 The brick ruler: why brick-as-objective lost the crystal (s3.107–3.109b)

Design (s3.107/107b): quantize arm EXTENTS to the fabric's parity
period — one brick = one qubit length — so whole-brick promises can
never be parity-infeasible; transverse line choices stay exact. The
falsification gate (s3.108) refuted its stated premise: once phantom
point arms were excluded, the junction-resolution census already saw
the stalled state's overload (v-line 2 at depth 9 > pool 8); and the
shipped objective saw it too but was outvoted (Δstair 73 vs Δpen 11 at
λ = 1). Built anyway (s3.109) on Max's call: hulls stay in junction
coordinates, only the accounting quantizes. Board (s3.109b): liquids and
lattices lean brick (ER −0.210, ws −0.069), the crystal family leans
stock (turán +0.092, spin_glass +0.086, regular +0.097). The reason,
sharpened at s3.125: a brick STEP objective (`hmax//s − hmin//s`) is a
rounding — an odd-course chain over junctions [1,12] prices one brick
more than its even-course twin over [0,11]; a step function cannot hold
a sharp optimum, and the crystal lives exactly at abutment-sharing at
pool. The lesson that stands: capacity may be booked per brick; LENGTH
must stay at junction resolution.

### 4.3 Lex: capacity first (s3.110–3.110b)

The two-ruler lexicographic engine: descend on (overload at the brick
ruler, stair at the junction ruler) as one scalar `pen·2^26 + stair`
(exact in floats; all integers) — λ is unrepresentable, the swamping
defect family mooted rather than tuned. Two discoveries outranked the
build: (1) a pen-0 lex state converts at 578 deficits raw and 0 after
one packer pass with pen preserved — **the packer's last load-bearing
role was family normalization**, not capacity (the converter is
co-designed with packer-shaped states); (2) hard-leading-key strict
descent is PATH-BLOCKED: the crystal is lex-feasible but the routes
into it wade through transient overload (turán +1.326, s3.110b).

### 4.4 The interleave jump and the complementarity (s3.111–3.111b)

Max's framing: the alignment DP's frozen-rest assumption is exact at
the optimum and near-exact nearby (a sliced-Wasserstein plan agreeing
with the true plan in the limit); its historical failure was the
architecture around it — exact optimization in one court, rejected by
another. Re-homed where proposer == judge, the same DP becomes a JUMP
that lands on the final interleaving without traversing overloaded
intermediates. Board: **lex + interleave holds turán at 6.000/mx 6 on
all 10 deep seeds** where lex alone (7.42) and seats + interleave
(7.28) both failed — the hard key filters the DP's stair-optimal jumps
onto the feasible manifold, and the jump gives the hard key the reach
it cannot walk. Plus K100 −0.210, ER −0.263, best board max chain on ws.

### 4.5 Consolidation 7 (s3.112)

lex + interleave became the default and every mode knob dissolved
(AttractConfig 20 → 12; −1145/+282 lines; archive `12fe484c`). Deleted:
the order-search court (insertion sweeps, order composites, the gather
executor, `claim_overload`). Kept with new jobs: `align_reinsert` as the
jump's interior; `edge_monotonize` inside `pack_project` (it was
load-bearing between the two unbounded packs). Pegasus written off by
Max ("weird and going obsolete"); parked with an unblock condition
(coupler-predicate cover accounting shared with the Zephyr machinery).

## 5. The plane engine (notes s3.113–3.123)

### 5.1 Orders engine rounds and the perf unlock (s3.113–3.115)

`engine="orders"` (s3.113): state edited only through the two orders;
positions re-derived by the packer after every adopted move; units =
contiguous dyadic intervals; every DP return adopted ("accept-all") vs
a strict-descent control ("audit"). Turán 6.000 on all 10 seeds in
both arms (a structural property, load-robust); ER +0.84 and king
+1.53 the residuals. s3.113b asked work-to-answer, not stop time; the
ws bookmark froze at readout 2 — two books (line capacity in the
packer, brick capacity in the judge) disagreed. s3.114 ported the pack
DP to numba (readout 111 → 10.1 ms) and nothing moved: the residuals
were capability, not compute. s3.115 confirmed Max's ER variance
hypothesis (hierarchy groups as joint gathers: ER 5.31 → 4.907) and
acquitted king of it.

### 5.2 The infinite plane (s3.116)

`engine="plane"`: readout = the two unbounded packs only; the search
lives on the ideal plane where capacity is the unbounded pack's
invariant; the judge is pure stair; the finite chip enters exactly once
in a final brick-aware projection with ONE capacity book
(`_brick_pool_arrays`). First board flooded 257+ deficit edges until the
boundary lines were zeroed inside the brick profile (they carry one
course parity and are parity-starved at claim time — fabrics.md §4.3b;
this is why `plane.profiles()` zeroes lines 0 and 2m today). Clean
board: king −1.25 (the mystery loss solved — it was the boundary-brick
class), ER −0.53, grid −0.39, regular −0.17, K100 −0.14; turán +0.137
in-tol. **The acceptance verdict inverted on the plane: accept-all beat
audit on the crystal (6.14 vs 6.49).** `hier_units` was toxic there
(turán 10.9). Default flipped at s3.117.

### 5.3 The DP audit (s3.117, `dp-internals.md`)

Two fresh-eyes audits of the two DPs. Headlines: the interleaver's tie
regime was unsound under accept-all (142/400 accepts not improvements,
55/400 strictly worse) because the readout's (value, id) collapse
re-split ties the DP had assumed; boundary-line zeroing was un-gated
across fabrics; the pack's linearization was invalidated by its own
output (32/40 contact sets flipped through one pack); a phantom trailing
brick; monotonize blind to ~30% of edges; the 1e-4 ramp was a second
objective (+9..+11 units at n=486). Several of these are now resolved
by construction in the rewrite (see §9); the rest are listed in
OPEN_FRONTS.md as hygiene.

### 5.4 Carry the orders (s3.118)

`carry_orders`: the state IS the two orders literally — tie-break by
rank in the carried order everywhere; ids speak once at entry; every
interleaver candidate is a real state (a tested property). ER 5.09 →
4.42 (the best ever at that point; the tie-fiction confound confirmed),
spin_glass −0.26 — and **turán +3.3 under the spectral init**, while
carry + trivial init landed exactly 6.000 on 10/10. Diagnosis: the
id-collapse it replaced had been re-sorting every line by id at every
readout, a hidden corrective force that laundered the spectral init's
poison on the block-numbered crystal. Flipped to default at s3.120 with
the 9.253 turán regression recorded as the open item this exposed.

### 5.5 The init round and "label luck" (s3.120)

Four inits under carry: spectral (default), landmark (double-BFS,
order-native), trivial (identity ranks), random. Landmark landed turán
6.000/10 and survived a relabel shuffle; **trivial collapsed from 6.000
to 10.96 under relabeling — the dataset's node ids had been a hidden
generator-order oracle.** Random ≈ spectral on turán (9.24 vs 9.39:
the spectral order carried zero crystal information); random was the
best ER ever (4.383); the init's whole measured value was regular
(+0.52) and ws (+0.48). No flip by the pre-stated bar (landmark lost
regular +0.543). s3.121b banked that the 240 s control reaches 6.000
under spectral — the regression was budget-bound, not basin-lost. From
this came the **optimizer/init separation principle** (Max, 2026-08-28):
the best optimizer wins from random; the init's only job is speed; an
init that changes quality is an optimizer bug report.

### 5.6 The joint moves that were refuted (s3.119, 3.121, 3.122, 3.123)

All four aimed at the fold on liquids; all four are off or deleted.

- **Tiles** (s3.119): 2-D joint tile family (windows × rigid
  displacements × reversals) screened by frozen-contact deltas. Seed-0
  smoke said it fixed the crystal; the 10-seed board said turán 7.50
  and **K140 +2.0/+3.0 — tiles broke the complete graph**. Refuted as
  built. Lesson re-taught: seed-0 smoke is not a verdict.
- **xy singles** (s3.121): evict one variable from BOTH orders,
  re-insert at the exact joint optimum (separable through deg+1
  splits; oracle-exact). At 60 s the coarse ladder starved the fine end
  (ws never reached it); at 240 s where it ran, ws +0.054, regular
  +0.059, and ws max edge span WORSENED 29.0 → 32.3 — relocations
  stretch the shortcuts they were built to collapse. Under the real
  judge every joint proposal on ws was declined (byte-equal endpoints).
  **The fold does not decompose into single-variable 2-D relocations
  at plane resolution** — minorminer's fold atoms improve a qubit
  objective with slack dimensions the plane stair lacks.
- **Waves** (s3.122): a disturbance-driven schedule (re-ask only blocks
  containing a variable the previous wave disturbed; an empty completed
  wave is a full-family fixpoint certificate). Validated at exact
  parity (seven cells +0.000) with small work-to-answer gains; never
  flipped; superseded by the s3.126 finding that the schedule is worth
  nothing on 8/10 cells.
- **Cross-axis widening** (s3.123): a first-axis adoption's realized
  displacement widens the same unit's second-axis probe. The coupled
  sets are real and prolifically askable (60–75% acceptance) but
  adopted ≠ profitable: turán +0.552 — the third independent
  confirmation that set-scale cross-axis meddling scrambles the forming
  crystal. The named fork: joint set-moves need a slack-carrying view or
  acceptance discipline.

## 6. The sound plane and the wrap (notes s3.124, "s3.124b" = its third build)

Built three times in one day. First build (brick judge on physical
coordinates + an ideal-plane fold onto the chip via a boustrophedon
strip map): (1) the judge was unsound by one book — a pen-0 state
missed 10–24 arms at conversion because the converter seats every
variable's cross (point arms as one-tile footprints) while the judge
had excluded empty sides; fixed by booking the books' own intervals —
one accounting; (2) **the ideal-plane fold never compresses**: folded
turán 12.438 where the bounded pack fits the layout in one strip; (3)
accept-all is judge-blind by construction, so a sounder judge only
re-selects the bookmark. The boundary-line "correction" (pool 8 → 4)
was retracted: count-4 profiles were MEASURED to flood deficits; zero
is the rule. Second build (bounded pack with real pools as the per-move
state): turán 10.5 — the ideal plane's freedom is what finds the
crystal (Max: ignore real hardware in the optimization; a folded
optimum of the infinite plane is not the finite optimum, so the wrap
must live in the loop). Third build, `wrap_pack`: the state stays
ideal; at every adopt it is ALSO projected by a wrapped bounded pack (k
strips, overflow continues into the next strip instead of clamping) and
the judge scores that. Smoke: k = 1 on every cell; ws +0.21 with pen 213
from the judge's stricter books. **On its board the wrap never
wrapped** (one strip on every run, s3.125) — its deltas were bookmark
selection. Nothing of it survives in the rewrite except the lesson that
the search state must stay on the ideal plane and the chip must be
priced, not imposed.

## 7. `arm_cost` and `strip` (notes s3.125)

Two facts opened the round. (1) The plane's stair priced an arm as its
hull span, so a contact-bearing arm whose hull is one junction cost 0 —
but the converter must seat a bar for it. grid_200: plane stair 240
for 200 variables vs real pre-tail ACL 1.965; minorminer's entire gain
there (1.965 → 1.330) was turning 96 two-bar crosses into single-bar
chains. `arm_cost` = one bar (`stride` junctions) per ACTIVE arm, in
`stair_energy(bar=)` AND inside the interleaver's transitions
(proposer == judge; oracles pass). (2) A ribbon is short but wider than
the chip and length cannot see it; `strip` packs the x half into the
REAL columns (boundary columns zero, profiles extended above the chip
with the ideal pool) and prices rows the chip lacks and stragglers as
the leading key. Smoke (seed 0, Z12, load ~90; board never run):

| cell | plane | arm | strip | arm+strip | pre-tail plane / arm / strip / arm+strip |
|---|---|---|---|---|---|
| grid_200 | 1.33–1.395 | 1.385 | **1.14** (mx 2) | 1.235 (mx 2) | 1.965 / **1.77** / 1.965 / **1.76** |
| ws_n486 | 2.508–2.541 | 2.547 | 2.484 | 2.504 | 3.733–3.813 / 3.763 (lmx 18) / 3.708 (lmx 17) / 3.883 |
| turán 60 s | 9.253 | 9.401 | 9.191 | **6.000** | same |
| turán 240 s | 6.000 | 6.000 (nt) | 6.000 | 6.000 | same |

Reads: the bar term moves the proposer on the lattice (grid pre-tail
1.965 → 1.77 with 202 active arms for 200 variables — the plane now
hands minorminer one-sided variables); strip alone makes seeds that fit
the chip so the polisher finishes them (grid 1.14, mx 2); **arm + strip
reaches the exact turán crystal in 60 s where plane needed 240 s** —
the bar makes one-sidedness (the biclique) cheap and the strip removes
the width the ribbon-shaped intermediates had to shed. Both became
unconditional in the rewrite (the bar term in the judge and proposer;
the strip generalized into "real profiles extended past the chip").

## 8. The order-invariance instrument (notes s3.126)

Max's principle — question order must not matter; schedule sensitivity
is a family/judge bug, the twin of init separation — had never been
measured. Built as measurement only: `sched` permutes the pass's ask
list ("ladder" = identity, coarsest-first; "rung" = shuffled within
scale; "bag" = the whole pass shuffled), `sched_seed`, and **`max_asks`
= a WORK budget in DP evaluations so the box's load never enters the
data**. Board (Z12, tail none, 10 cells × 5 arms × 5 draws; pre-tail ACL,
mean over draws (range); tol = max(0.3, 0.05·ladder)):

| cell | ladder | rung | bag | rinit | rinit+bag |
|---|---|---|---|---|---|
| K100 | 7.260 | 7.262 (0.01) | 7.264 (0.02) | 7.260 (0) | 7.260 (0) |
| K140 | 9.757 | 9.760 (0.01) | 9.757 (0) | 9.760 (0.01) | 9.757 (0) |
| spin_glass | 10.847 | 10.866 (0.04) | 10.876 (0.03) | 10.892 (0.16) | 10.902 (0.13) |
| honeycomb | 2.165 (fixpoint) | 2.139 (0.11) | 2.123 (0.21) | 2.400 (0.20) | 2.206 (0.27) |
| grid | 1.965 | 2.138 (0.15) | 2.093 (0.20) | 1.994 (0.22) | 1.979 (0.32) |
| regular | 4.440 | 4.414 (0.15) | 4.459 (0.12) | **4.861 (0.32)** | 4.708 (0.09) |
| ws | 3.850 | 3.853 (0.20) | 3.790 (0.31) | **4.180 (0.31)** | 4.158 (0.33) |
| king | 2.388 | 2.424 (0.13) | 2.471 (0.18) | **2.748 (0.27)** | 2.790 (0.25) |
| ER100 | 4.950 | **4.804 (0.43)** | **4.768 (0.48)** | **4.796 (0.50)** | 4.846 (0.28) |
| turán | 6.265 (mx 7) | **7.495 (3.35)** | **6.664 (2.69)** | **6.964 (2.36)** | **7.198 (3.25)** |

The map: order- and init-free — K100, K140, spin_glass, honeycomb.
Order-free but init-sensitive — regular (+0.42), ws (+0.33), king
(+0.36): the spectral init's whole measured value, once more exactly
those three cells. Order-sensitive — ER (every randomized mean beats
the ladder; many near-minima) and turán (the crystal reached by 12 of
20 randomized draws and NOT by the ladder at 15k asks; endpoints
6.0–9.35 — the **9.253 attractor**). Grid is the one cell where the
ladder's order earns something (+0.13–0.17 under shuffles). Conclusion
for the rewrite: the ladder is worth nothing on eight of ten cells and
is the worst order on ER and turán — the schedule can be a bag and a
work budget; the init still carries {regular, ws, king} (+0.3–0.4),
which by the separation principle is an optimizer-strength gap.

## 9. The audit and the rewrite (notes s3.127)

Max's direction after s3.126: stop measuring the old engine, find the
philosophy deviations hidden in the code, count meat vs engineering,
write a fresh engine a person can read.

### 9.1 The census

8,244 lines: 29% comments, 20% live meat, 13% live engineering, 31%
dead; of executable code 49% dead. The exact, oracle-tested logic was
~580 lines (interleaver 210, completion 130, converter 108, packer
kernels 131). 28 knobs: 12 load-bearing, 13 read but inert, 3 never
evaluated.

### 9.2 The ranked deviations (with their measurements)

1. **The init pre-committed turán's interleaved y-order, and only two
   inits ever existed.** `multilevel_init` collapsed turán to a 2-node
   quotient; the n < 3 circle fallback put both supernodes at the same
   y; the disc spread alternated the blocks 133 times along y; `seed`
   reached the init only as a shuffle of a 2-element list — two inits,
   mirror images: why 9.253 "recurred across seeds". Every init whose
   y-order is nearly block-separated (spectral, landmark, trivial)
   reached 6.000 in 60 s.
2. **Contiguous runs cannot un-interleave.** A reinsert keeps both
   sides as subsequences; the one unit that gathers a scattered block
   (`hier_units`) was off and labelled toxic — measured the best arm on
   turán.
3. **93% of a pass was edge pairs** (938 interval asks + 13,122 pair
   asks); the bookmark sat at ask 726 and 12,700 pair asks improved
   nothing; the clock was a parameter of the answer.
5. (The notes' own numbering skips 4.) **The judge was blind to one qubit per active arm**: predicted vs
   realized qubit mass off by −76% on grid, −68% on ws; with the bar
   term −1% to −8%. The s3.125 claim "the active-arm count is fixed on
   turán" was false: crystal 162 active arms vs 322 interleaved.
6. **Single-axis readout**: re-packing only the moved axis after a
   one-axis move — adopt_worse 7% from the init, 40% AT the crystal.
7. **The ramp**: 0 bad accepts, 0 missed improvements under rank
   contacts — exonerated as a driver (but load-bearing as a tiebreak,
   see 9.4).
8. **The kappa floor**: exonerated on turán (0 deficits).

The judge itself preferred the crystal all along (1768 vs 2598 vs 3906
at the init): turán was reachability + budget, not objective.

### 9.3 What was built (`plane.py`, ~430 lines)

State = two orders; init = two seeded permutations. Readout = the
packer on real columns/rows with brick profiles (boundary lines zero on
course fabrics), extended past the chip with the ideal pool so a
packing always exists. Books = `arm_books(floor=False, min_span=0)` —
one accounting for packer, judge and converter. Judge = lexicographic
(brick overload against `profiles(grid)`, pool 0 off-chip; spans + one
bar per active arm). Move = `align_reinsert`. Units per pass = every
contiguous run of each order at scales n/2 … 1 on both axes PLUS every
N(v) — the order-independent gather (for a biclique N(v) is the other
block, so the bipartition is one move: measured on K_{81,81}, one ask,
5219 → 3134). No pairs. One shuffled bag per pass. Accept-all. Stop =
fixpoint | `max_asks` | deadline (reported).

### 9.4 What measurement changed during the build

(a) **The ramp restored as an exact tiebreak.** Removing it outright
stalled sparse graphs (path-60: 1.017 → 1.5 — the tie-moves ARE the
drift that compacts a chain); now `rank_scale(n) = 2n²+1` scales the
true cost so total rank span is an exact lexicographic tiebreak.
(b) **Both-axes readout.** Re-packing only the moved axis left the
other overloaded and accept-all wandered in overloaded states (turán
bookmark frozen at the init for 15,000 asks on 3/10 seeds); now the
moved axis is re-packed, then the other.
(c) **Decline on unpackable.** A proposal the packer cannot seat is
outside the valid set and is declined.
(d) **The strip was wrong as a start condition.** On regular/ws the
first board pass made ZERO accepts — a random start cannot be packed
into the chip's 23 usable columns, every proposal was declined. Fix:
extend BOTH axes past the chip with the ideal pool during the search;
the judge prices anything off the chip; a bounded projection hands
over a counted layout only when the bookmark still hangs off the chip.
(e) **Projection columns first.** h-arms past the last real brick are
free in a row pack, so rows-before-columns stacked everyone on row 1.

### 9.5 Fingerprints (`data/plane_fingerprint.py`, tail none, work budgets)

| cell | old engine (random init) | new engine |
|---|---|---|
| K8 / K10 on Z3 | 1.5 / 1.8 certified | 1.5 / 1.8 certified |
| path-60 | 1.017 | 1.033 |
| K100 | 7.26 (budget-bound at 10k asks) | 7.26 at a FIXPOINT, 1,370 asks |
| turán n162, seeds 0–9 | 6.000 on 3/10 | **6.000 on 10/10** (bookmark 1.9k–14.8k asks) |
| grid_200 pre-tail | 1.87 | **1.40** (old polished: 1.33) |

All certified, minorminer skipped, extensions 0. NOTE for the reader:
that table is the step-4 checkpoint (`plane_fingerprint_step4-plane2.json`).
The step-5 file recorded after the strip fix of 9.4(d)
(`plane_fingerprint_step5-default.json`) reads grid_200 **1.605** (mx
6) and path-60 **1.067**, with K100 7.26 and turán 6.000 on 10/10
unchanged. `ideas.md` quotes 1.40 and `CLAUDE.md` says "≤ 1.76"; the
current tree's number should be re-established before it is used as an
acceptance bar (see OPEN_FRONTS.md).

### 9.6 Step 5: the deletion (archive commit `ea5d1cf2`)

Deleted: orders.py, seat.py, coarsen.py, costs.py, loop.py, the dead
half of field.py (`pack_project`, `edge_monotonize`, `xy_reinsert`,
`_center_shift`, `stair_step`, `bar_domains`), `AttractConfig` and its
28 knobs; placement.py rewritten (292 lines;
`attract_embed(source, target, *, timeout, seed, max_asks, sched_seed,
tail in {"none","mm"})`); 110 probe scripts moved to
`docs/paper2/archive/probes/`. Package 8,244 → 3,859 lines (plane 425,
placement 292, field 1,901, ball 858, polish 185, trees 156, init 42).
Suite 505 passed. Live harnesses: `plane_fingerprint.py`,
`rewrite_board.py`, `invariance_probe.py`.

### 9.7 The paired board (`rewrite_board.py`; ACL / mean max chain)

mm = stock minorminer 60 s; old = the archived default 60 s with its
tail; new = the rewrite at a WORK budget, tail none; new+mm = the
rewrite with the tail at 60 s wall; deep cells 10 seeds, others 3:

| cell | mm | old (+tail) | new (no tail) | new+mm |
|---|---|---|---|---|
| K100 | 10.47 / 15 | 7.26 / 8 | 7.26 / 8 | 7.26 / 8 |
| K140 | 20.29 / 40 (2/3) | 9.76 / 10 | 9.77 / 10.7 | 9.77 / 10.7 |
| spin_glass | 20.56 / 35 | 11.04 / 12.7 | 10.85 / 12.3 | 10.84 / 12 |
| turán | 11.30 / 18.9 | 9.46 / 12.5 | **6.000 / 6** | **6.000 / 6** |
| ER100 | 4.82 / 8.8 | 4.65 / 7.8 | 4.60 / 8.1 | **4.45 / 7.5** |
| regular | 3.59 / 9.6 | **2.78 / 6.5** | 4.75 / 13.6 | 3.61 / 9.3 |
| ws | 3.14 / 11.7 | **2.56 / 8.0** | 4.40 / 27.4 | 3.34 / 12.1 |
| grid | 1.08 / 2 | 1.27 / 3 | 1.59 / 5.7 | 1.29 / 2.7 |
| honeycomb | 1.16 / 2.3 | 1.33 / 2.7 | 1.89 / 6 | 1.24 / 2.7 |
| king | 1.76 / 3.7 | 1.83 / 4 | 2.56 / 7.7 | 2.11 / 4.7 |

Reads (from the notes). Dense and ER: the rewrite wins outright —
every dense cell at the template, turán exact on 10/10 (old 9.46,
minorminer 11.3), ER the best ever recorded with the tail (4.45).
Sparse: the rewrite LOSES to the old engine on regular (+0.83), ws
(+0.78) and king (+0.28) with the tail, ties on grid, wins on
honeycomb. Two measured causes: (a) the wall-clock arm is
budget-starved — a new-engine ask costs ~5× an old one (two packs +
books per adopt, the N(v) units, the `stepR` Python loop), so at 30 s
the engine finishes a fraction of a pass on ws (~40 asks/s) and hands
minorminer worse seeds; (b) at a full work budget the engine's own
pre-tail on ws (4.40, max chain 27) is still worse than the old engine
from its spectral init (3.76) and comparable to the old engine from a
random init (4.18): the optimizer has not yet replaced the +0.4 the init
carried on exactly {regular, ws, king}, and long chains survive on ws.

### 9.8 The invariance map (`invariance_probe.py`, 5 order × 5 init draws, tail none, work budgets)

Range of pre-tail ACL, tol = max(0.3, 0.05·mean). Order- AND init-free:
K100, K140, spin_glass, turán (exact, range 0), ER (0.24 / 0.25), grid
(0.23 / 0.20), honeycomb (0.17 / 0.15). SENSITIVE: regular (order range
0.54; init 0.11), ws (order 0.39; init **1.01**), king (init 0.32).
Every regular/ws run stopped by the ask budget (15k asks ≈ 4 passes on
ws), so part of that spread is unfinished descent; the rest is the
engine. (Per-draw rows: `data/invariance_probe_board.csv`; the summary
block at the end of `data/invariance_probe.log`.)

### 9.9 Where this left things (the notes' closing paragraph, condensed)

A 3,900-line tree a person can read; the dense half of the problem
solved to the template from random starts; ER better than anything
before; the sparse half open with two named causes — per-ask cost
(vectorize the interleaver's transition loop; one books computation
per pack) and the sparse family's reach on ws/regular/king (long
chains, order sensitivity, the init's lost +0.4). Both are fronts in
`ideas.md` and in OPEN_FRONTS.md.

## 10. Refuted and superseded ideas — do not re-derive

Condensed from `attraction.md` plus the post-s3.112 entries of the
notes. Verdicts: SHIPPED (in the default), REFUTED (measured worse or
wrong), SUPERSEDED (replaced by something better), DELETED (removed
from the tree; archive commit noted), PARKED (live with an unblock
condition). "Shipped" items from the old engine that the rewrite did not
carry are marked "(old engine)".

### 10.1 Representation and state

| idea | verdict | one-line reason |
|---|---|---|
| Extents as state (v1, v2) | REFUTED | gradient flow cannot break the row/column permutation symmetry (s3.28–29) |
| Per-edge contact state ("place the edges") | REFUTED | 60× the state, nothing bought; corners + derived arms is the representation (s3.45–47) |
| Point state + density bins | SUPERSEDED | monopole approximation is disinformation when chains are long |
| Span state (positions only; extents derived) | SHIPPED → SUPERSEDED by orders | the energy became the real chain length (s3.31) |
| Continuous positions + contraction | DELETED (consolidation 4, `d8274198`) | stair energy is monotone toward collapse; no honest internal stop exists (s3.75); the discretization was the only counter-force |
| Order state (two orders; positions a readout) | SHIPPED (s3.76) — the current state | true-objective linear DP; turán ≈ 6.02, lattices fell in one flip |
| Carried orders (ties by carried rank; ids speak once) | SHIPPED (s3.118/120) — in the rewrite | the id-collapse was a hidden re-sort laundering the init; realness of every candidate is a test |
| Folded (j-folded) Zephyr coordinates | REFUTED | a 2× ceiling: the claimable object was the odd-coupler zigzag (fabrics.md §4.5) |
| Exclusive connector claiming | REFUTED | more rigid than the router's own overlap pricing |

### 10.2 Objective and constraint handling

| idea | verdict | one-line reason |
|---|---|---|
| Local congestion penalty at any weight | REFUTED | gradient-blind inside uniform overload; only the rim peels (s3.42–44) |
| Excluded-volume wall / stiff barriers | REFUTED | leaks through arm growth; bang-bang |
| Realized-demand congestion charge | REFUTED | realized state satisfies capacity by construction; only proposal demand signals |
| History / multiplier memory terms | REFUTED twice | inert next to a fresh present term (minorminer AND our field) |
| Overload hinge² in gate energies at λ | SUPERSEDED (consolidation 7) | swamps energy gaps on uniformly crowded graphs (cap_pressure ER +0.577, s3.101; lam=4 over-trades); replaced by lexicographic order — no λ |
| Brick-step stair (`hmax//s − hmin//s`) as the length objective | REFUTED (s3.109b, explained s3.125) | rounding: a step function cannot hold the sharp optimum at abutment; crystal +0.092 |
| Brick ruler for CAPACITY | SHIPPED — in the rewrite's `profiles()` | whole-brick promises cannot be parity-infeasible (s3.107/109) |
| Lexicographic (capacity, stair) with a hard key | SHIPPED (s3.110/112) — in the rewrite's `judge` | λ unrepresentable; path-blocking cured by the jump (s3.111b) |
| Required-hull census as a gate term (`census_required`) | DELETED | inert at lam=1 on Z12 (s3.97); small liquid wins later (s3.101) but died with the court |
| Qubit pricing per arm ceil((L+1)/2) | REFUTED as a separator | ties the crystal and the stalled state at 972 (s3.104) |
| Σ max(0, truncation − 1) as a judge term | SUPERSEDED (never built) | the diagnostic that found the brick idea; the s3.108 gate showed the junction census already sees the overload |
| Span-only stair (no bar per active arm) | REFUTED (s3.125/127) | −76% predicted qubit mass on grid; the bar term is in the rewrite |
| Max chain as a lexicographic slot | PARKED | never built; principle 13 (wins must not buy fatter tails) and s3.106 (the tail of the distribution is what separates) are the design notes |

### 10.3 Packing and the claim layer

| idea | verdict | one-line reason |
|---|---|---|
| Exact order-preserving DP under integer pools + one census | SHIPPED (s3.59) — `pack_lines` | oversubscription abolished structurally |
| Infinite (unbounded) packer, census carries the chip | SHIPPED (s3.93) — generalized in the rewrite | first sub-minorminer liquid; the bounded DP's only recourse was dropping variables |
| Anchor unbounded layouts at line 1 | SHIPPED | line 0 is a boundary line (turán 6.00 → 6.70 otherwise) |
| Boundary lines at half pool (4) | REFUTED (s3.124) | measured to flood 257+ deficits; zero is the rule on course fabrics |
| Straggler clamp (`clamp_miss`) | SHIPPED (old) → SUPERSEDED | the rewrite declines unpackable proposals and extends both axes instead |
| Uniform packing slack | REFUTED | trades away the parity slack the aim step needs |
| Unconditional boundary spill | REFUTED | wins one cell, regresses cells with interior slack |
| Deficit-first selection | SUPERSEDED | deficit and E must be traded, not ordered |
| Claim-time parity-exact aiming (snap) | SHIPPED | extensions → 0; completion becomes a verifier (s3.56) |
| Exact per-line converter v2 | SHIPPED (s3.96) — `wire_seeds_exact` | corner deficits 0 everywhere; ER legalizes natively |
| Certificate diag | SHIPPED (s3.97) | certified-and-invalid = 0 empirically; the skip gate's premise |
| Wire-exact post-hoc matching | PARKED | coupler-blind layouts admit no perfect assignment — existence, not optimization |
| Coupler-aware coloring / scoring | REFUTED (0-for-4) | metric saturates; superseded by exactness on complete junctions |
| Lex-family converter (spill-aware brick seating) | PARKED (never built) | would delete the normalizer pack; moot since the rewrite's states are packer output again |
| Family normalizer pack | SUPERSEDED | the rewrite's every state is packer output, so no normalizer is needed |

### 10.4 Moves and schedule

| idea | verdict | one-line reason |
|---|---|---|
| Adjacent-swap / swap-Metropolis order search | REFUTED | plateau-bound (s3.35) |
| Discrete order annealing (`order_shake`) | SUPERSEDED | only ever dodged overload the gates could not see |
| Best-insertion order sweeps | DELETED (consolidation 7, `12fe484c`) | job passed to the interleave jump |
| `edge_monotonize` | DELETED (rewrite) | pair units were 93% of a pass and improved nothing (s3.127 deviation 3) |
| Cluster moves (member sets gathered as one proposal) | SHIPPED (old) → SUPERSEDED by N(v) units | the order-independent gather in the rewrite does the job without a hierarchy |
| Generous merging / per-member affinity / admissibility matching | SHIPPED (old) → DELETED (rewrite: coarsen.py) | the hierarchy is gone; N(v) is the order-independent unit |
| `hier_units` (hierarchy groups as extra units) | validated on ER (s3.115), toxic on the plane crystal (s3.116), best arm on turán under the audit (s3.127) | superseded by N(v) |
| Gather orientation bit (reversed block competes) | SHIPPED (s3.89) — inside `align_reinsert` | reversal is the fold's atom translations cannot compose |
| One-axis fold (rank-interval reversal) | REFUTED | preserves the axis multiset — both strands on the same wires (194/194 vetoed) |
| Two-axis hairpin fold | DELETED (consolidation 5) | fictions on 56% junctions (P16 K100 +1.05); won nothing on the s3.93 baseline |
| Eager fold pass | REFUTED | ~150 composites ate the budget, ACL worse despite 9 accepts |
| `strain_rank` (proxy-gain-ordered execution) | REFUTED, DELETED | ranking was not the bottleneck |
| Orientation flips (un-gated, in the readout) | DELETED (consolidation 6, `5be76754`) | regresses dense K100 on both fabrics: no claim-layer voice at the decision (s3.99) |
| Alignment reinsertion DP | SHIPPED (s3.100b) — THE move | exact over all interleavings; induced-rule pricing on y |
| `align_insert` (\|S\|=1 alignment for insertion) | near-inert, DELETED | value was consolidation, not quality |
| `cap_pressure` inside the proposal DP | DELETED | liquids won, ER +0.577 by ranking distortion (s3.101) |
| Seat engine (exhaustive re-seat, translations, swaps) | SUPERSEDED (consolidation 7) | loses the twin-block crystal at a converged fixpoint (s3.102) |
| Native gather (evict-S splice) | DELETED | the interleave jump's family is its strict superset |
| Seat/orders synthesis (one borrowed orders iteration) | SUPERSEDED | path luck (s3.104); broken on P16 |
| Interleave jump (`best_interleave`) | SHIPPED (s3.111) — the rewrite's move | jump + hard key = 6.000/10 where either alone fails |
| Tiles (2-D joint windows) | REFUTED as built (s3.119) | K140 +2.0/+3.0; frozen-contact screen mispriced at saturation |
| xy singles (joint 2-D singleton) | REFUTED as built (s3.121) | ws max edge span worsens 29 → 32; all joint proposals judge-declined on ws |
| Wave schedule | validated at parity (s3.122); not carried | superseded by the s3.126 finding (bag suffices) |
| Cross-axis widening / `axis_inner` | REFUTED as value (s3.123) | adopted ≠ profitable; turán +0.552 |
| Edge-pair units | DELETED (rewrite) | 93% of asks, zero bookmark improvement (s3.127) |
| Coarsest-first ladder | SUPERSEDED (s3.126) | worth nothing on 8/10 cells, worst on ER and turán; a bag + work budget replaces it |
| Strict-descent acceptance ("audit") on the plane | SUPERSEDED (s3.116) | accept-all beat audit on the crystal once projection distortions were gone; the rewrite adopts every proposal |
| Single-axis re-pack after a move | REFUTED (s3.127 deviation 6) | adopt_worse 40% at the crystal; both axes re-packed now |
| Ramp removed outright | REFUTED (s3.127) | path-60 1.017 → 1.5; the tie drift compacts chains; restored as an exact lexicographic tiebreak |
| Strip (real columns) as a START condition | REFUTED (s3.127) | zero accepts on regular/ws from a random start; extend both axes instead |

### 10.5 Init

| idea | verdict | one-line reason |
|---|---|---|
| Spectral / multilevel init as load-bearing | SUPERSEDED (rewrite: random) | carried zero crystal information (s3.120); pre-committed turán's interleaved y-order with two inits ever (s3.127) |
| Hier (dendrogram) init | REFUTED (s3.77) | ER +0.23, regular +1.07; 1-D linearization destroys 2-D geometry |
| Init offset generators (spiral/grid/random) | near-inert (s3.78) | arrange erases within-cluster offsets; golden angle was ornamentation |
| Trivial (identity) init | REFUTED as a method (s3.120) | its turán 6.000 was label luck: relabel → 10.96 |
| Landmark (double-BFS) init | validated candidate (s3.120), not carried | lost regular +0.543; the separation principle says the optimizer must replace it |
| Segment ("crystal-shaped") spreads; pre-formed K_n diagonal; compact init | REFUTED | pre-ordering members pre-empts the moves that discover better orders (principle 11) |
| Adjoint transport (`vcycle_transport`) | PARKED then DELETED | transmits noise orders on expanders (s3.69) |

### 10.6 Tail and polish

| idea | verdict | one-line reason |
|---|---|---|
| Ball polish after the grind (`mm+ball`) | SHIPPED (s3.81) — `tail="mm"` today | wins or ties every cell at equal budget |
| Ball before the grind | REFUTED (s3.80) | traps the grind's basin (turán +0.59, ws +0.87) |
| Ball-rng (mm's randomization at ball scale) | REFUTED (s3.82) | randomizing a confined family explores the confinement |
| Ball v3 obligation-hull questions | SHIPPED as selector; ladder claim REFUTED (s3.83) | asking is not answering: sum-descent ratchets into blight |
| Native shortener (deterministic / randomized) | REFUTED (s3.84) | same non-minorminer plateau as every other arm |
| Lane audit (exact member placement) | REFUTED as the missing piece (s3.85) | plateau survives exact selection |
| Bars-only ball rebuild | REFUTED standalone | near-zero accepts off turán |
| Grind removal | REFUTED twice (s3.91, s3.94) | dense ties grind-free; everywhere else the grind is irreplaceable — better seeds made its contribution larger |
| Crossfinder as the whole algorithm | PROTOTYPED, DELETED (consolidation 5) | liquids/dense never legalize; overlap is minorminer's load-bearing feature |
| `submit_seeds` (warm seeds to the fallback) | REFUTED | no effect (legal-stage carries no information) |
| Region-biased polish | REFUTED | the placement must improve an unconstrained polish |
| Best-of-N by legal-stage ACL | REFUTED | r ≈ 0 between legal and polished ACL |

### 10.7 Protocol

| idea | verdict | one-line reason |
|---|---|---|
| Multi-round feedback (re-derive from realized centroids) | REFUTED dense / PARKED sparse | rounds destroy insertion-found order |
| Exactness gate as a decision bar | REFUTED (s3.65) | gate-as-trophy blocks outcome-improving flips |
| Per-cell best-arm boards; minorminer+busclique max "as an algorithm" | REFUTED | the portfolio trap |
| Wall-clock budgets for the engine | SUPERSEDED (s3.126) | the clock was a parameter of the answer; `max_asks` |
| Seed-0 smoke as a verdict | REFUTED (s3.74, s3.119) | path luck; 10 seeds on deciders |
| Pegasus (P16) | PARKED (s3.112) | cover arithmetic assumes crossing = coupler; unblock = a coupler-predicate adapter shared with Zephyr |

## 11. Where the archived code lives

- Archive commit of the pre-rewrite tree: `ea5d1cf2` (a worktree at
  `/data/max/ember-archive` was used for the "old" arm of the board).
- Earlier consolidation archives: `d8274198` (4), `09467299` (5),
  `5be76754` (6), `12fe484c` (7).
- Old probe scripts: `docs/paper2/archive/probes/`; their CSV/log
  outputs: `docs/paper2/data/`.
- The pre-condensation notes and ledger: `docs/paper2/archive/notes_v3.69_full.md`,
  `attraction_v3.69_full.md`; the long ideas file:
  `archive/ideas_v3.112_full.md`.
