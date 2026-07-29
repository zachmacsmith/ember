# Anatomy of the attraction embedder — every piece, what it does, why it exists

Structural companion to `attraction.md` (the chronological idea ledger) and
`notes.md` (the lab record). That pair answers "what did we try and when";
this file answers "what is in the program right now, what does each part do,
and what measured failure justifies its existence." One entry per component,
with its status (default / opt-in / ablation arm / parked / deletion
candidate), so complexity stays visible and accountable. Update this file
when a component is added, promoted, or killed.

Code map:

| file | contents |
|---|---|
| `placement.py` | the driver: `attract_embed`, `AttractConfig`, init, snap, round loop, budget, fallback, polish dispatch |
| `field.py` | all coarse geometry: `TileGrid`, `PoissonField`, the three state models (point/cross/span), deposits, forces, discrete arrangement, seed derivation |
| `loop.py` + `costs.py` + `trees.py` | the **native router** (the minorminer-free ablation arm; also registered standalone as `factored`) |
| `polish.py` | `spur_prune`, `shorten_chains` — the native cleanup |
| `__init__.py` | registry: `attraction` (this algorithm), `factored` (the router alone) |

## 0. The one-paragraph version

The algorithm is a **multilevel embedder**: a continuous, gradient-style
placement over a coarse capacitated grid decides *where* each variable lives;
discrete projection steps enforce what gradients structurally cannot (integer
capacity, row/column ownership, clique structure); the placement is
transmitted to minorminer as seeds; minorminer legalizes cheaply per round,
realized geometry feeds back, and after the last round minorminer's full
grind polishes **unconstrained**. Division of labour: geometry makes the
global joint decisions local search can't revise; minorminer does what it is
unbeatable at (fine legalization, free local descent). The placement earns
its keep only by improving the endpoint of an *unconstrained* polish
(free-polish doctrine, notes §3.22).

## 1. Two operating points, not one

The config space is large but in practice there are two named regimes:

- **Default pipeline** (`AttractConfig()` as registered): `state="point"`,
  `field="poisson"`, snap singleton seeds. This is the general-purpose /
  sparse / hard-frontier configuration — the one the full-Ember sweep
  (§3.23) scored. All the span/arrange/stair/wire machinery is *off* here.
- **Dense/cliff configuration** (the research frontier): `state="span"` +
  `span_dynamics="arrange"` + `readout="stair"` + `seed_mode="wire"`.
  Per-regime standings on record (§3.32–3.36): field dynamics owns
  comfortable-dense, arrange owns the cliff (K140), and the arrange+insertion
  board now sweeps stock MM on the dense cells (12.51/17.39/17.59/8.24 vs
  13.44/20.70/25.37/8.26).

Everything below is tagged with which regime uses it.

## 2. The driver loop (`placement.py::attract_embed`)

Per call: init → repeat {geometry step(s) → derive seeds → seeded route →
feedback} under a budget → select a round → unconstrained polish → validity
guard. Pieces:

- **Init — spectral layout, circle fallback** (`source_positions`). A
  deterministic, router-free warm start scaled into the middle 80% of the
  target's drawing box. *Why spectral*: respects coarse source geometry with
  zero routing cost. *Why the circle fallback*: complete/tiny/disconnected
  sources have degenerate spectra; the density field does the shaping from a
  circle. **Status: default, but demoted in principle** — the
  init-independence standard (§3.36: random init reaches the same dense
  results through insertion search) makes spectral a warm-start heuristic,
  never load-bearing. Known open weakness: disconnected sources can stack
  components (only *detected* degeneracy falls back).
- **Round budget** (`round_frac=0.4`, `max_rounds=10`). Rounds may spend at
  most 40% of the timeout; the rest is reserved for the polish *by
  construction*. *Why*: MM's polish earns ~30–38% ACL (mm-internals §6);
  starving it was the v3 budget bug. Adaptive by cheapness: mid-size
  instances get ~10 tight rounds, hard instances collapse to 1.
- **Geometry cadence** (`geo_iters=1` for point state). One coarse step per
  router projection — the trust-region reading: the coarse model is only
  calibrated near the last realized embedding; iterating it further
  optimizes fictions (the v3 regression, §3.23/§3.24). Exception: the span
  state may take many steps (`geo_iters=30` in probes) because its model
  takes *no* fine-level calibration — positions are its only input (§3.31
  decision (b)).
- **Per-round routing** (`_route` → `_mm_route`). Stock minorminer with
  `initial_chains` = the derived seeds and `chainlength_patience=0`: the
  cheap ~5–15% legalization phase only, at C++ speed. The source is passed
  as a *graph object*, never an edge list (edge lists drop isolated
  vertices — the 1,546-failure bug of the first sweep). `backend="native"`
  swaps in the factored router (§5) for the purity arm.
- **Feedback** (end of round). `spur_prune` the legalized embedding, read
  realized centroids back as next round's positions, and update charges with
  damping `lam ← (1−τ)·lam + τ·realized` (`lam_tau=0.5`). *Why damping*: the
  charge-feedback instability — congestion fat inflates demand → field
  over-spreads → longer chains → more demand, a positive feedback loop
  through the router with one-round lag. The span state **skips** charge
  updates entirely: its deposit mass is a forward function of positions
  (1 + derived spans), so that feedback channel doesn't exist there.
- **RNG discipline** (`vary_rng`). True (default): fresh router stream per
  round — restarts and steering both active. False: frozen stream, so *only
  geometry* varies between rounds — the attribution arm (failed rounds still
  re-roll, else a failure repeats forever). §3.26: steering alone reaches
  parity with re-rolling — the trajectory gains are geometric.
- **Selection** (`selection="last"`). The trajectory endpoint feeds the
  polish, not the best legal round. *Why*: legal-stage ACL carries ~zero
  information about polished ACL (§3.16, r ≈ −0.01 on ER); the endpoint is
  where the steering converged. `"best_legal"` kept as the ablation arm;
  `round_acls` accumulates free rank-stability data in every result in case
  the §3.16 null fails on steered/structured runs.
- **Feasibility fallback**. If no round legalized: one *uncapped* seeded
  attempt with all remaining time. Degradation mode = "spectral-seeded stock
  MM", the net feasibility winner of §3.23.
- **Finish** (`polish="mm"`). Stock MM full grind, warm-started
  (`skip_initialization`), **unconstrained** — the free-polish doctrine.
  Region-biased polish (`gamma>0`, native arm) is the refuted ablation:
  it cut 17% where the free grind cuts ~37% (§3.22). Do not resurrect.
- **Validity guard**. A broken finishing pass can never corrupt a legal
  result: the polished embedding is validity-checked and the pre-polish
  embedding restored on failure. Same paranoia guard in the native router.

## 3. State models — what a variable *is* in the coarse layer

Three representations, selected by `cfg.state`. The through-line (§3.26
"smear reinterpreted" discussion): the point model's dense failure was a
*representation* failure — a centroid is the monopole approximation of an
extended chain, and contact between extended bodies is invisible at monopole
order.

### 3.1 `point` (default) — centroid + charge

State: one (x, y) per variable. Attraction = `relax`: each centroid moves
η=0.5 toward the mean of its neighbours' centroids (Laplacian smoothing).
Charge λ_v = damped realized chain length (initial `lam0=3`), i.e. how much
fabric v is expected to consume. *Why the charge exists*: repulsion must
price mass, not headcount — a 20-qubit chain crowds a region 20× more than
a singleton. Right model for the sparse regime (chains short ⇒ monopole
fine); the measured failure mode is dense sources (§3.23: complete +8.2,
turán +4.1 before the span/arrange line existed).

### 3.2 `cross` (legacy, deletion candidate) — position + evolved extents

State: (x, y, w, h) — an axis-aligned cross whose extents evolve under
contact-demand growth, rent (`extent_cost`), tip-potential retraction
(`field_ext_w`), and measured-extent feedback (`fit_extents`). Built as
Option A of the dense unification (§3.26–3.29). **Verdict: superseded.**
Extents-as-state produced the s3.28–3.30 pathology zoo (assignment fights
attraction, collapse attractors, growth/rent force balances), and §3.31
measured span dominating cross on every cell with strictly fewer knobs.
Cross deletion is on record as Max's call. Components that die with it:
`contact_step`, `deposit_cross`, `fit_extents`, `bar_force`, `bar_seeds`,
centered `wire_seeds`, and the knobs `extent_eta`, `extent_cost`,
`field_ext_w`. Until deleted, nothing else depends on them.

### 3.3 `span` (the live dense-regime state) — derived extents

The s3.31 simplification, from "is there a way to capture the properties we
want with minimal complexity?": **extents were never legitimate state.** Any
embedding of v must reach its neighbours, so v's bars owe exactly the span
of its neighbours' coordinates — a deterministic *readout* of positions.
State shrinks back to one (x, y) per variable.

- `derive_bars`: h-bar = x-interval of N[v]∪{v} at row y_v; v-bar symmetric.
  Contact for (u,v) is at (x_u, y_v), inside both bars **by construction** —
  which is why bars are never recentered (load-bearing invariant: the
  energy identity, wire seeding at `round(y_v)`, and the contact guarantee
  all assume the bar sits on its owner's row/column).
- `span_energy` E = Σ_v [xspan(N[v]) + yspan(N[v])] — exactly the total bar
  length of the implied embedding. VLSI HPWL with one net per closed
  neighbourhood: **chain length is the objective itself**, not a simulated
  proxy.
- `span_step`: the HPWL subgradient — per net, per axis, unit forces pull
  the two extreme members inward; interior members feel nothing. Replaces
  `relax` in this state.
- Contact-capacity floor (`span_floor`, `kappa=13`): a chain of L qubits
  hosts ≲ κL contacts (Pegasus degree counting, §3.26), so derived bars are
  clamped to w + h ≥ deg/κ − 1. The *only* surviving remnant of extent
  dynamics — a readout-side clamp, not state.
- `cap_derate`: capacity scale during rounds (<1 keeps packing off 100%
  utilization). *Why*: packing at exactly full capacity starves routing
  slack — legalizes worse, routes worse (measured twice: §3.29 K140
  regression, §3.31 testbed 15.16-at-full vs 13.15-derated).

Why each s3.30 pathology dies structurally in span: collapse is infeasible
in-model (stacked variables still deposit 1+w+h each, the pool overfills);
the blob attractor can't exist (no growth/retract balance); the
assignment-vs-attraction fight is dead (assignment moves positions, extents
re-derive self-consistently — tested as idempotence).

### 3.4 `readout="stair"` (span sub-mode) — single coverage

The cross readout pays every edge at **two** crossings (both variables span
their whole neighbourhoods) — measured 2× overpay on K100 (seed ACL 20 vs
busclique 9.78). Busclique's construction (verified in its source) is the
staircase: each pair meets exactly once. Generalization = the **diagonal
rule**, a pure readout: edge (u,v) is covered at u's h-arm × v's v-arm iff
(y_u, u) < (y_v, v) — the y-lower variable reaches across columns, the
y-upper reaches up rows. Components: `_stair_contacts` (who owes whom),
`derive_bars_stair`, `stair_energy`, `stair_step` (same HPWL subgradient on
directional nets). Arms span *assigned contacts only*, so they shrink below
the cross readout's. Invariant: the rule is keyed on y-*order*, so the
order-preserving packing leaves the per-edge orientation assignment valid
across a half-step — the sort's order preservation is load-bearing for
correctness, not just optimality. Cost forfeited, on record: single coverage
loses the redundancy that made double-covered seeds auto-legal; Pegasus's
~56% in-tile coupler density then bites at designated crossings, and the
router (or the matching, §4.6) must carry legality.

## 4. Discrete operations — what gradients structurally cannot do

Each exists because a specific continuous failure was measured. All share
one acceptance discipline: **propose discretely, dispose by the true energy**
(the E-gate), and all are deterministic.

### 4.1 `assign_rows_cols` — the symmetry break

Rank-order participants by y → distinct integer rows (capacity-many per
row), by x → columns. *Why*: co-row bars are a symmetric configuration —
swap is a zero-gradient direction, slide-past raises energy first, so
gradient flow equilibrates at a smeared multi-bar-per-row compromise
(§3.28: max_violation 14–25 at equilibrium; the §3.9 deadlock at coarse
level). The sort is order-preserving = the minimal-total-displacement 1-D
transport plan, and the two axis sorts cannot conflict (a cross occupies one
row AND one column). Participation is **capacity-gated**: only variables
whose contact floor forces extension (deg/κ − 1 > 0) enter; sparse sources
are structurally untouched — the win-guard rule that keeps every dense
mechanism inert on the sparse cells. Used by span "field" dynamics
(`assign_every` cadence; ak=5 routed better than ak=1 at K100).

### 4.2 `alternate_arrange` — product mode (the cliff's engine)

The fabric viewed as two coupled 1-D wire layers (rows of h-wires, columns
of v-wires, glued by tile-local coupling). Coordinate descent on the same
span/stair energy: alternately pack rows (columns frozen — each
participant's h-interval is then a fixed 1-D interval, and rows are exact
interval packing) and columns (rows frozen). Capacity per line = interval
overlap **depth** (`line_depth`, the interval graph's clique number ω = χ) —
no wire coloring inside the optimizer, only the depth test. Iteration 0 is
an unconditional feasibility projection (spreading from a compact init must
raise E); every later half-step is E-gated, so the alternation is monotone
on the feasible set. As an optimizer: ~2 iterations / ~0 s replaces 300
field steps / ~20 s, with exact feasibility and zero schedule knobs. First
ACL win over stock MM on any dense cell (K140, §3.32).

Sub-pieces, in the order they act:

- **`_align_diagonal`** (stair only, §3.35): x-rank := y-rank — a pure
  permutation of the participants' existing x-values. *Why*: the two 1-D
  orders were uncorrelated (rows sorted by y-noise, columns by x-noise), so
  h-arms reached backward; aligned, K_n's E collapses to ~n·side (the
  busclique diagonal). Acts entirely in attraction's null directions,
  E-gated like every projection. Also *contains* the biclique: if the
  y-order separates bipartite blocks, one side becomes pure h-lines and the
  other pure v-lines — which killed the per-edge orientation-variable
  proposal.
- **`insertion_sweeps`** (`insert_sweeps>0`, §3.36): best-insertion order
  search on the participants' y-queue — relocating one variable flips ALL
  its edge orientations across the jumped interval at once, exactly where
  adjacent swaps are plateau-bound (§3.35's turán verdict). Exact
  integer-slot semantics (the fractional-rank shortcut collapses into rank
  stacking); candidates adjacent to neighbours' slots; composite gating:
  propose in rank space, realign + repack, dispose by true E with full
  revert. This is the move that made block structure *emerge* from random
  init (turán 8.24, beating MM's 8.26) — the init-independence standard.
- **Metropolis `swap_sweeps`** (default 0): noise applied only along the
  permutation directions block descent cannot explore. Built as the
  contingency for joint blind spots; measured inert everywhere at 30 sweeps
  (§3.35). **Status: off, contingency only — candidate for deletion if
  insertion keeps covering it.**

### 4.3 `snap` — point-state seed projection

Variables claim distinct nearest qubits, high degree first. *Why high degree
first*: hubs are hardest to place; giving them first pick of the contested
center is the cheap greedy that matters. Default seed path for the point
state and the fallback everywhere.

### 4.4 `wire_seeds_iv` — wire-coherent seeds (span)

The sub-tile last mile. Bars sharing an integer line with disjoint intervals
may share a physical wire; overlapping ones may not — interval-graph
coloring, solved exactly by the greedy left-endpoint sweep
(`_color_claim_bars`). Each bar claims the **contiguous run** of its colored
wire's qubits, so seed chains are real coupled paths instead of stitched
nearest qubits (which inflated routed ACL ~30%, §3.30). Oversubscribed bars
are simply left point-seeded (`_ensure_seeds` guarantees everyone ≥1 qubit)
— seeds are always best-effort, never an error path. Options bolted on,
all default-off:

- `wire_couple` (§3.33): columns prefer the sub that actually *couples* to
  contact partners' assigned row wires at the crossing tiles (Pegasus
  couples only ~56% of in-tile h/v pairs; Chimera 100% — no-ops there).
  Mechanism measured real at tight packing (15.09→14.51) but gate failed;
  off.
- `seed_stride` (§3.33): claim every stride-th qubit — negotiation slack for
  the router. Off (stride 1).
- `slack_steps` → `slack_relax` (§3.33): fractionalize positions within
  their assigned lines (round() invariant) before seeding. **Measured inert
  as built** (floor/ceil swallows sub-tile shifts). **Deletion candidate.**

### 4.5 `wire_seeds_matched` (`wire_exact`, §3.37) — coupler-exact seeds

Per line, arms grouped into TRACKS (the greedy coloring's color classes;
#tracks = depth, so track→sub matching can never break feasibility), then
tracks matched to physical subs by max-weight bipartite matching
(`linear_sum_assignment`, ≤12×12/line), alternating columns↔rows —
coordinate ascent on satisfied designated crossings, exact per half-step,
monotone. **Self-junctions** (a variable's own h×v corner) are in the
objective at `junction_w=2` — omitting them let the matcher trade chain
*connectivity* for contacts (K100 conn 100→44 before the fix). Always
best-effort; leftovers go to the router. Verdict: wins where corners don't
bind (turán 8.04 record, K140 17.04 record) but plateaus ~62–67% crossing
satisfaction on K100 — the busclique existence proof does not transfer to
coupler-blind layouts; geometry/wire **co-design** is the named open
problem (Zephyr's complete junctions would dissolve it; Zephyr is untyped
in TileGrid so far). Tier discipline on record: matchings only, no SAT/ILP.

### 4.6 `bar_domains` (`seed_mode="domains"`) — **parked**

Shape transmitted as a *constraint region* (`restrict_chains`) instead of a
constructed chain, so MM keeps every sub-tile identity choice. Built,
tested, and **disabled**: stock minorminer 0.2.22 hangs past its timeout /
segfaults when `restrict_chains` carries non-trivial domains alongside
`initial_chains` (isolated repro; upstream report owed). Raises on use.

## 5. The coarse field machinery (`field.py`, top)

Used by the point state (always) and span "field" dynamics; **not** used on
the arrange path at all (product mode's feasibility is exact per line).

- **`TileGrid`** — the hardware's own canonical coarsening: per-tile
  **typed** wire pools, cap shape (H, W, 2), pool 0 vertical / pool 1
  horizontal, counted from working qubits (dead qubits reduce the right
  pool by construction). *Why typed* (§3.25 correction): separate "edge
  capacities" are the wrong abstraction — crossing a tile consumes a qubit
  *in* it, so cut capacity is implied by node pools; but untyped capacity
  can read 50% free while the h-pool is saturated. Exactly VLSI gcells with
  per-direction track capacities. Also owns `wire_map` ((orientation, line,
  sub) → {tile: qubit}) — the lookup all wire seeding runs on — and the
  affine drawing↔tile mapping. Unrecognized targets (incl. Zephyr, for
  now) fall back to untyped drawing-space bins, halved across both pools.
- **`TileGrid.deposit`** — RUDY-style segment-smeared demand (point state):
  each variable spreads λ_v along straight segments toward its neighbours,
  charging every *traversed* tile, split h/v by segment direction. *Why*:
  point deposits never charge passed-through tiles — that is precisely how
  the old field was blind to the cut constraint (§3.21). The smear is a
  prior over chain geometry given endpoints; its known false assumption
  (contact happens *between* endpoints) is what the span state fixes.
  `deposit_bars` is the span-state sibling: exact traversal charging of the
  shape that will actually be seeded — no RUDY approximation left.
- **`PoissonField`** — long-range repulsion, sourced **one-sidedly from
  violation only**: `source = hinge_w·relu(ρ−cap)² + μ`, solved with the
  pre-factorized grid-Laplacian pseudo-inverse (Neumann, mean-subtracted).
  *Why a solved field*: the one-bin push has a plateau problem — the
  interior of a uniformly overfull region feels nothing, only the rim
  peels; by Gauss's law the solved potential gives an interior centroid
  force ∝ total enclosed excess. *Why one-sided*: stock ePlace's
  mean-subtracted two-sided density pulls cells into all whitespace
  (uniform-utilization objective — wrong for us: chain length scales with
  occupied-region size; we want compactness and "slack fabric is silent").
  *Why hinge²*: the raw hinge's defect was the derivative jump; softplus
  was rejected for phantom repulsion from its positive tails.
- **μ multiplier field** (`mu_alpha`, default 0): projected-subgradient
  price memory, `μ ← max(0, μ + α(ρ−cap))` once per router round — the §3.5
  history update lifted to the coarse grid; complementary slackness gives
  zero-on-slack as a KKT property. **Measured inert** next to hinge²
  (§3.26, all cells; 30–60% stale μ-mass real but harmless) — the recurring
  pattern (§3.13): a memory mechanism is inert when another mechanism
  already covers its job. Kept as a knob by the ablation-pair decision;
  diagnostics (`mu_stale_frac`) still reported.
- **Forces** — `force_at` (point: −∇ψ at the centroid), `bar_force_iv`
  (span: −∇ψ averaged along the implied bars — the source-distributed/
  response-distributed consistency fix). All forces trust-region clipped at
  `max_step=1` tile: the explicit bound on placement steps that carries the
  cadence principle even when the field is iterated.
- **μ-ramp** (`ramp_rounds=3`): field weight scales in over rounds —
  ePlace's schedule (attraction-dominant early, capacity-enforcing late).
- **`DensityField`** (`field="push"`) — the v1 one-bin density push.
  **Control arm only**; superseded by Poisson on every measured cell
  (2026-07-18 probe). Kept for the ablation record.

## 6. The native router & polish (`loop.py`, `costs.py`, `trees.py`, `polish.py`)

The minorminer-free arm (`backend="native"`, `polish="native"`), also
registered standalone as `factored`. Exists for two reasons: the *purity
ablation* (is any claimed win secretly minorminer's?) and as the factored
family whose corners isolate MM's three separable choices
(order/tree/cost). Not the performance path — stock MM's C++ wins on speed.

- **`loop.py`** — MM-shaped negotiation: per pass, each vertex releases and
  rebuilds its chain cheapest-first under current prices (overlap priced,
  not forbidden); done when nothing is contested. Deterministic per seed
  with flags off; `order_per_pass` / `random_ties` restore MM's
  randomization channels faithfully (they are *feasibility* mechanisms —
  mm-internals §5). Isolated vertices seed farthest-from-occupied
  (deterministic) or uniform-random (MM-faithful) — the deterministic rule
  under a random order scatters seeds into cross-fabric walls, measured
  0/3 vs 3/3.
- **`costs.py`** — `price(q) = (1+h)·β^occ`; `α=0` is exactly MM's
  memoryless corner (β effectively-infinite in shipped MM — occupancy is
  lexicographic, mm-internals §4). The history `h` is the
  subgradient/Lagrangian update: rises with overuse, holds at full, decays
  when slack, floors at 0. Verdict on record: history substitutes for
  randomness in the deterministic replica (~2× legalization) but is
  **inert inside real MM** (§3.13) — randomness and cross-pass memory are
  substitutes. `LinearPathFinderCost` = VPR's linear present term, ablation
  arm for present-term shape only.
- **`trees.py`** — one assembly, two strategies: `sph` (Takahashi–Matsuyama
  nearest-attach Steiner — what shipped MM actually does) and `union`
  (independent paths to the root — what MM's *paper* says; kept as the
  "what does the Steiner trick buy" ablation). Boundary-seeded multisource
  Dijkstra per neighbour; `inf` (never a large constant) signals
  unreachability, because exponential prices make reachable paths
  arbitrarily expensive.
- **`polish.py`** — `spur_prune` (delete every qubit whose removal keeps
  the chain connected and every edge covered — pure overhead by
  definition; deadline-bounded after the star/wheel quadratic blowup) and
  `shorten_chains` (free-space rip-up-and-shorten, longest first, keep iff
  strictly fewer qubits — MM's chainlength move class). `spur_prune` also
  runs in the main pipeline after every MM legalization (cheap, and it
  cleans the centroids the feedback reads). `vertex_prices`/`gamma` is the
  refuted region-biased arm.

## 7. Load-bearing invariants (break these and the algorithm is wrong, not just worse)

1. **Never recenter a derived bar** — the contact-at-(x_u, y_v) guarantee,
   wire seeding's `line = round(y_v)`, and the E ≡ implied-qubit-mass
   identity all assume bars sit on their owner's row/column.
2. **Order-preserving packing** — under the stair readout the per-edge
   orientation assignment is a function of the y-order; the packing may
   only permute *values*, never relative order, or contacts silently point
   at the wrong arms.
3. **The E-gate on every discrete projection** (except the iteration-0
   feasibility projection, which is unconditionally accepted by design) —
   projections are proposals; the continuous objective disposes.
4. **Seeds are always best-effort** — oversubscribed bars, unsatisfied
   crossings, and unmatched tracks are left for the router. No discrete
   stage has an error path that can fail a run.
5. **Capacity-gated participation** (deg/κ − 1 > 0) — every dense mechanism
   must be structurally inert on sparse sources. This is what protects the
   sparse win-guards without topology detection.
6. **Free polish** — the finishing grind is never restricted, priced, or
   region-biased. Any placement claim must survive it.
7. **Paired measurement** — every mechanism ships as a switch defaulted to
   the incumbent behavior, measured one flip at a time against it
   (CLAUDE.md ground rule); pre-registered bars before any run.
8. **Determinism per seed** — sorted iteration everywhere; the only RNG is
   the router's seeded stream and the (default-off) Metropolis contingency.

## 8. Complexity ledger — what could go

Standing decisions and candidates, so pruning is a checklist rather than an
archaeology project:

| component | status | basis |
|---|---|---|
| `cross` state + `contact_step`, `deposit_cross`, `fit_extents`, `bar_force`, `bar_seeds`, centered `wire_seeds`, knobs `extent_*`/`field_ext_w` | **deletion approved in principle** (Max's call, §3.31: span dominates on every cell with fewer knobs) | delete when convenient |
| `slack_relax` / `slack_steps` | inert as built (§3.33) | deletion candidate |
| `swap_sweeps` Metropolis contingency | inert at 30 sweeps everywhere measured (§3.35) | deletion candidate once insertion is confirmed to cover it |
| `DensityField` (`field="push"`) | superseded control arm | keep only while the point-state ablation record matters |
| `mu_alpha` machinery | measured inert; default 0 | keep the knob, or delete with the next field simplification |
| `gamma` region prices | refuted (§3.22) | kept for the record only |
| `bar_domains` / `seed_mode="domains"` | parked on the upstream MM bug | keep; re-enable against a fixed fork |
| `wire_couple` | mechanism real, gate failed, saturating metric | superseded by `wire_exact` line; candidate to fold in |
| `selection="best_legal"` | doubtful (§3.16) ablation arm | keep until steered/structured rank-stability data (free via `round_acls`) settles it |
| `union` tree, `LinearPathFinderCost` | ablation arms of the factored family | keep: they are the paper's control corners |

Open problems on record (not components, but the reasons remaining
complexity exists): geometry/wire co-design (the K100 matched-seeds gap; the
Pegasus 56% junction pathology — absent on Zephyr, whose TileGrid adapter is
queued), corridor/routing-capacity reservation (own design round; naive
reservation sabotages cliques), the K_n template gap, and the disconnected-
source init weakness.
