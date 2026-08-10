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

## 0. The algorithm in one paragraph

Every variable of the source graph gets a place on the hardware's tile
grid, expressed as two orders: who is left of whom, and who is below
whom. From those two orders alone, everything physical is *derived*:
which row and column each variable's two arms occupy, how long the arms
are, which wires they claim, which qubits form the chain. A small set of
deterministic moves permutes the orders, and an exact assignment step
(the "readout") recomputes the physical layout after each move; moves
are kept only if the real total chain length (plus a penalty for
overfull wire bundles) does not get worse. On Zephyr, the resulting
chains are completed into a provably valid embedding and minorminer is
skipped entirely; otherwise minorminer legalizes the seeded layout.
Either way, minorminer's polish runs next, unconstrained — and then
`ball_polish` (§7) runs LAST, harvesting the coordinated improvements
the single-chain grind cannot see (default `tail="mm+ball"`, s3.81:
wins or ties every board cell). The ladder is coarse→fine→coarse:
cluster moves teleport, the grind polishes chains, ball re-lays
neighborhoods at the end. Running ball BEFORE the grind was measured
worse (s3.80): the grind's stochastic wandering needs an unconstrained
basin — nothing may run ahead of it that narrows its options,
including a smarter polisher.

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

## 1. The state: two orders

**What.** The algorithm's state is two total orders over the source
variables: an x-order and a y-order. Nothing else is state.

**How.** In memory the orders are carried as a dict of positions
`{v: (x, y)}`, but every value in it is a *derived* integer line index,
recomputed from the orders by the readout (§3). No code writes a
position except the readout and order-permuting moves; a test enforces
that every post-arrange position is an integer.

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

### 3c. The line assignment (the true-objective DP)

**What.** The step that turns order into geometry: assign each variable
a row (its y line) and a column (its x line), respecting the orders and
the wire capacities, minimizing real total arm length.

**How.** One axis at a time. Sort the variables by their current value
on that axis (ties by id). The key fact: *given the orders, total arm
length is a linear function of the assigned positions* — each variable
gets a fixed coefficient equal to (number of nets it is the top of)
minus (number it is the bottom of), because every net's span is just
(top member's position − bottom member's position). A dynamic program
then assigns contiguous runs of the sorted sequence to successive
lines: a run is feasible on a line if its arms' interval-overlap depth
fits the line's integer lane pool (boundary lines: pool zero), and the
cost of a run on line l is (sum of the run's coefficients) × l. The DP
is exact and order-preserving by construction. Row assignment needs the
column extents (for capacity) and vice versa, so the two axes alternate
inside the arrange loop until neither changes.

**Why.** The previous packer minimized *displacement from the previous
positions* — a memory of the continuous era that made early layouts
sticky. Minimizing the actual objective given the order is what
"positions are a readout" means taken literally. Capacity as a hard
constraint in the same DP is what abolished lane oversubscription
structurally (s3.59). Contacts are reused across evaluations whenever
the mutation provably preserved the y-order (x-swaps, x-permutations);
any y-order change recomputes them, because collapsing two y-values
onto one line can flip a tie-break (a silent proxy drift otherwise).

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
books as the packer and the coloring.

## 4. The moves

All moves run inside `alternate_arrange`, all are judged by the same
gate (stair energy + overload census, computed on the derived
positions), and all revert by snapshot on rejection. Deterministic
throughout; the deadline is checked between iterations.

- **Iteration-0 projection.** The first per-axis DP pass is accepted
  unconditionally — it is the feasibility projection that turns the
  init's ranks into real line assignments.
- **Per-axis packs.** Each later iteration re-runs the DP per axis and
  accepts if the gate does not worsen. This is the readout refreshing
  itself as the orders change.
- **Edge monotonize.** For each source edge whose x-order disagrees
  with its y-order, try swapping the two variables' x-values; keep the
  swap if total h-arm length strictly drops. Leverage scales with edge
  length, which is exactly the sparse/dense interpolation (s3.40).
- **Insertion sweeps.** A best-insertion search over the long-arm
  variables' order on one axis: repeatedly try moving one variable to
  the slot that most reduces a span-sum proxy (priced at the actual
  values the permutation would assign, with frozen non-participants as
  fixed anchors), then apply the winning order as one composite:
  permute the values, re-monotonize, re-pack both axes, and accept or
  revert on the full gate. Up to two accepted composites per call.
  This is the global relocation move that makes block structure emerge
  from any init (s3.36).
- **Cluster composites.** The same composite mechanism, but the
  proposal is "gather this hierarchy unit into a contiguous block of
  ranks" (both axes, coarsest units first). Units come from the
  affinity coarsening (§4.5); members are moved as one proposal, on
  real positions, judged by the ordinary gate with strict descent —
  nothing is summarized, no sizes are guessed (ideas §2.10). Where the
  coarse structure is real the gathers fire (turán's crystal); where
  it is noise they are silently rejected (expanders).

## 4.5 The hierarchy

**What.** A multi-level clustering of the source graph, used twice: to
propose cluster composites, and (on Zephyr) to build the init sketch.

**How.** Round 0 collapses exact twins (variables with identical
neighbourhoods) in one shot. Then rounds of greedy pair-merging by
*per-member affinity* — compare the average members of two clusters:
sum of min over sum of max of their per-member pull profiles, with the
mutual pull counted and one body per member as regularizer — merging a
pair only when it is at least one side's best available option
(admissibility), iterated to a natural fixpoint. No thresholds.

**Why.** The affinity score is the correct merge criterion (fragments
of one family score 1 at any size ratio — s3.72, shipped by
correctness decree); admissibility prevents forced marriages of
leftovers without a constant. The hierarchy is a good detector of
"who belongs together" and a measured-bad dictator of "in what order"
(s3.77) — so it feeds moves and membership, never sequences.

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

**How.** Ball candidates come from two selectors: the hierarchy's
units (who belongs together) and tile windows (who lives together).
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

`round_frac=0.5` (budget fraction before the polish),
`arrange_iters=8`, `insert_sweeps=8`, `kappa=None` (derived from the
fabric), `span_floor=True`, `exact_seeds=True` (Zephyr gate),
`snap_claims=True` (Zephyr gate), `overload_lam=1.0`, `vcycle=True`,
`vcycle_agg=True`, `cluster_moves=True`, `cluster_units=True`.
Unknown kwargs are ignored (old probe scripts degrade gracefully).

Diagnostics (`diag`): `assigned`/`assigned_rows`/`assigned_cols`
(participants placed by the last packs), `insert_reverts`,
`cluster_accepts`/`cluster_reverts`, `mono_time`, `extent_mean`/
`extent_max` (bar widths), `stride` (2 = course-resolved Zephyr),
`E_interp`/`E_contract` (stair energy at init; equal since
consolidation 4 — the contraction phase no longer exists),
`max_chain`, and on Zephyr `mm_skipped`, `deficit_edges`,
`corner_deficit`, `extensions`, `ext_qubits`, `bridges`.

## 9. Known gaps

See ideas.md §3 for the live list. The load-bearing ones: the polish
is still minorminer (ball_polish is the replacement path); the
in-arrange gate energy has a measured blind spot below capacity
(parity/nesting costs the census cannot see — s3.73); expanders pay a
small toll under the order state (the no-order regime); Pegasus
exactness (coupler-aware aiming on incomplete junctions) remains the
generalization test.
