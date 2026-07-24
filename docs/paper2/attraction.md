# The attraction embedder — design doc & idea ledger

Living document for the placement-first ("attraction") algorithm: what it *is*, what
it *currently does* (as-built), and what it *should* do next, with every idea's
status recorded so nothing is re-litigated from memory. Chronology and raw numbers:
`notes.md` §3.18–§3.22. Minorminer facts: `mm-internals.md`.

## A. Framing: multilevel minor embedding

The honest description of this algorithm family (2026-07-17 discussion):

- The geometric layer computes a **soft embedding of H into a coarse capacitated
  grid**: bins = coarse vertices with capacity (working qubits per bin), centroid
  positions + charges = how much of each variable lives where. Minorminer then
  *refines* the coarse solution into the real fabric (seeded legalization) and
  *polishes* it (warm-started grind). This is the multilevel method of partitioning [`karypis1999hmetis`]/
  placement/multigrid, applied to minor embedding.
- **Division of labour**: geometry makes the global, joint decisions that
  one-chain-at-a-time local search cannot revise (which region each variable lives
  in — the §3.9 wall/pocket failures are exactly local search failing at a joint
  move); minorminer's machinery does what it is unbeatable at (fine legalization,
  free local descent).
- **The placement earns its keep by improving the endpoint of an *unconstrained*
  polish, or it wasn't real.** Hobbling the polish to protect the layout is
  rejected — tried and measured worse (region-biased finish: −17% vs the free
  grind's −37%, notes §3.22).
- **A centroid is the monopole approximation of an extended chain.** Fine for short
  chains (sparse regime); near-disinformation for long chains (dense regime), where
  contact between extended bodies — where one chain's horizontal crosses another's
  vertical — is invisible at monopole order. Fidelity ladder: point charge →
  charge smeared along the expected chain tree (mass + shape) → one particle per
  needed qubit with connectivity + exclusion (which *is* the embedding problem,
  written as a lattice-polymer system — solving it exactly re-derives routing).
- **"Forgiving" is quantitative**: capacities > 1 make the coarse problem a
  fractional relaxation (smooth, descendable), while the essential obstruction
  survives coarsening — an expander's bisection width doesn't shrink with the grid,
  which is why coarse geometry predicts feasibility and the Θ(n) ACL law (§3.21).
  Corollary: on fixed-degree ER there is nothing for geometry to discover; only the
  constant is winnable there. Home turf is structured and (potentially) dense.
- Dense-limit anchor: busclique's crossbar beats MM outright near the clique cliff —
  pure placement, zero polish. The attraction family with density-limited collapse
  interpolates between that and the sparse local-search regime.

## B. As-built: v3 hybrid (registered as `attraction`)

Code: `packages/ember-qc/src/ember_qc/algorithms/factored/placement.py`; seeded
routing via `initial_chains` in `loop.py`; optional region-priced shortening via
`vertex_prices` in `polish.py`. Registry: `attraction` (hybrid default) — the
minorminer-free purity arm is `backend="native", polish="native"`. Deterministic per
`seed`. Probe script: `docs/paper2/data/placement_v3.py`.

Pipeline per call (v3.1 plumbing, 2026-07-18):

1. **Init**: spectral layout of H scaled into the middle 80% of the target's drawing
   coordinates (`pegasus_layout` etc.); circle fallback for degenerate spectra
   (complete/tiny/disconnected graphs). No router call, no MM basin as anchor.
2. **Geometry** (per round): `geo_iters=1` step of Laplacian attraction (η=0.5
   toward neighbour-centroid mean) + the coarse repulsion field. Default
   `field="poisson"` (since the 2026-07-18 probe): typed tile grid (per-tile
   h/v wire pools from hardware coordinates, `field.py`), RUDY-style
   segment-smeared demand [`spindler2007rudy`] (traversal charging), one-sided
   `hinge²+μ` Poisson source [`lu2015eplace`], forces trust-region-clipped at
   1 tile; λ charges damped (`lam_tau=0.5`). `field="push"` = the v3.1 one-bin
   density push, kept as the control arm. One geometry step per router
   projection is the trust-region cadence — the coarse model is only calibrated
   near the last realized embedding; iterating it further optimizes fictions
   (the v3 regression).
3. **Snap**: variables claim distinct nearest qubits, high degree first.
4. **Routing**: stock MM seeded cheap legalization (`initial_chains` singletons,
   `chainlength_patience=0`), each call capped by the *rounds budget*.
5. **Feedback + adaptive rounds**: spur-prune, read realized centroids +
   per-variable chain lengths back; repeat from 2 while the rounds budget
   (`round_frac=0.4` of timeout) and `max_rounds=10` allow — mid-size instances
   get ~10 tight rounds, hard instances collapse to 1. Per-round RNG: fresh
   stream per round (`vary_rng=True`); the `False` arm freezes RNG so only
   geometry varies between rounds (attribution; failed rounds still re-roll).
6. **Feasibility fallback**: if no round legalized, one *uncapped* seeded attempt
   with all remaining time — degradation mode is "spectral-seeded stock MM",
   the net feasibility winner of §3.23.
7. **Select**: `selection="last"` (trajectory endpoint; default) or
   `"best_legal"` (v3 behavior, doubtful per §3.16). Every round's legal ACL is
   returned as `round_acls` — a free rank-stability diagnostic that accumulates
   with every run and will decide whether a polish-race is ever worth building.
8. **Finish**: stock MM full grind warm-started from the selected round
   (`skip_initialization`), unconstrained, with ≥ ~(1−round_frac) of the budget
   reserved for it by construction.

Magic numbers, none swept: η=0.5, λ₀=3.0, round_frac=0.4, max_rounds=10, bins≈16,
γ=0 (region bias off by default; >0 is the refuted ablation arm).

## C. Idea ledger

### Span state — derived extents (design settled 2026-07-23; notes s3.31)

The simplification after the s3.28–3.30 failures, from Max's "is there a way
to capture the properties we want with minimal complexity?": **extents were
never legitimate state.** Any embedding of v must reach its neighbours, so
v's bars owe exactly the span of its neighbours' coordinates — a
deterministic READOUT of positions. State shrinks to one (x, y) per
variable; h-bar = x-interval of N[v] ∪ {v} at row y_v, v-bar symmetric.
Contact for (u,v) is at (x_u, y_v), inside both bars by construction (never
recenter a bar). The energy `E = Σ_v [xspan(N[v]) + yspan(N[v])]` is exactly
the total bar length of the implied embedding — VLSI HPWL with one net per
closed neighbourhood; chain length IS the objective, not a simulated
quantity. Dynamics keep the v2 shape (Max's call: no annealing): HPWL
subgradient attraction + Poisson field on exact implied-bar deposits +
argsort assignment as projection of the same energy.

Why each s3.30 pathology dies structurally: collapse is infeasible in-model
(stacked variables still deposit 1+w+h each; the pool overfills — the
contact-capacity floor survives only as a readout clamp `w+h ≥ deg/κ − 1`);
the blob attractor cannot exist (no growth/retract force balance); the v2
assignment-vs-attraction fight is dead (assignment moves positions, extents
re-derive self-consistently — tested as idempotence). Deleted in this state:
extent ODEs (`extent_eta`/`extent_cost`), tip retraction (`field_ext_w`),
λ/chain_len damped feedback (`lam0`/`lam_tau`; deposit mass is 1 + derived
spans, so the charge-feedback instability channel does not exist),
`fit_extents` measured-extent feedback, RUDY smear (deposits are exact).

Built (2026-07-23): `field.py` span section (`derive_bars`, `span_energy`,
`span_step`, `deposit_bars`, `bar_force_iv`, `bar_widths`, `wire_seeds_iv` —
interval-native; `wire_seeds`/`bar_seeds` refactored onto shared helpers,
behavior-preserving), `state="span"` arm in placement.py (default unchanged:
`"point"`; new knobs `kappa=13`, `span_floor=True`, `cap_derate=1.0`;
`seed_mode="wire"` wires the s3.30 interval coloring into the pipeline),
`span_sweep` in the router-free testbed, tests (TestSpanState +
TestWireSeeds, closing the wire_seeds coverage hole). Cross arm kept until
the probe verdict (Max, 2026-07-23).

**Pre-registered bar (Max, 2026-07-23, set before the probe): K100 ≤ 13.46
polished (the s3.30 cross-emergent result) at near-default settings — no
schedule zoo; biK48_96 beats point; no win-guard regression (regular_n316
~3.5, ws_n486 ~3.1); K140 feasibility ≥ point. Stretch: ≤ ~11.2 (within 15%
of template 9.78).** Probe: `data/span_probe.py`; testbed gate first
(`crossbar_testbed.py span 100`, finalist ACL ≤ 13.46 required to run the
pipeline probe at all).

**Testbed gate PASSED (2026-07-23, K100, 24 combos, zero schedules;
`data/span_sweep_k100.log`):** the dynamics is insensitive to eta and
threshold (identical outcomes across both axes — the no-knob-zoo property
the simplification was built to buy); only assignment cadence and derate
matter. Stock capacity converges to a 10-row coarse crossbar (viol≈2,
E=1800) but routes at 15.16 — packing at 100% starves routing slack, the
s3.29 lesson re-measured; the 0.65-derated 14-row config routes at
**13.15 ≤ 13.46 (ak=5)** / 13.94 (ak=1). Assignment projection cost is
small and local (E 1740→1800 typical). Decisions carried into the probe,
recorded before it runs: (a) probe arm `span-tb` = wire seeds +
`geo_iters=30` + `cap_derate=0.65` + `assign_every=5`; (b) `geo_iters=30`
is principled for span, not tuned — the span coarse model takes no
fine-level calibration (positions are its only input), so the s3.24
trust-region argument for one step per projection does not apply; (c)
assignment participation is capacity-gated (only `deg/κ − 1 > 0` variables
enter the sort; sparse sources untouched — the win-guard rule).

**Probe verdict (2026-07-23; notes s3.31): K100 bar FAILED** (span-tb 15.11,
one-shot 13.96, vs bar 13.46; mm 13.44) — defaults unchanged
(`state="point"`). Salvaged, in order: (1) **span-tb is the only search arm
that legalizes K140 — 3/3** (21.84; best seed 20.74 ~ mm 20.70) vs 0/3 for
point, span-default, and cross — the s3.26 anti-placement failure is fixed;
feeds the hard-frontier eval directly. (2) The coarse layer is exonerated:
converged in-pipeline (max_violation ~2.4); the residual dense gap is
transfer economics (round interleaving −~1.1 ACL, init/budget −~0.8;
K140 prefers the opposite protocol — rounds beat one-shot there).
(3) span-tb sweeps both win guards (3.44 / 3.12) and biK48_96 (8.01);
one ER regression (+0.44, span-tb only; span-defaults hold parity).
(4) **span dominates cross on every measured cell with strictly fewer
knobs** — cross deletion is Max's call. Options on record in s3.31.

### Extent-state v2 verdict (2026-07-19; notes s3.29)

Tip-coupling + assignment built and probed; **bar failed 0-for-2, K140 bars
feasibility regressed** (2/3 -> 0/3; row packing at 100% pool capacity
starves routing slack). Root cause: assignment and attraction fight per
round -- the crossbar is a fixpoint of the assignment, not of the composed
dynamics; pinning would be required. Guards unharmed. Defaults unchanged
(`state="point"`). Build paused pending Max: (a) v3 pinning + slack-packing,
(b) template arm concession, (c) park dense, run the hard-frontier eval.

### v2 design settled in discussion (2026-07-19, Max's three challenges)

- **Field-bar coupling (fixes the center-sampling inconsistency Max caught:
  source distributed, response point-sampled)**: from E = density * integral of
  psi over the bar -- translation force = bar-AVERAGED gradient (not center
  sample); **extent force = -psi at the bar tips** (growing adds charge at the
  tips; bars refuse to grow into, and retract out of, high-potential regions).
  Gives the field direct actuation of extents; a far-tip oversubscription now
  produces a local retract signal instead of ~nothing.
- **Assignment step**: rank h-bars by y -> distinct integer rows (capacity-many
  per row), v-bars by x -> columns; sorts are order-preserving = minimal-total-
  displacement 1D optimal transport; the two sorts cannot conflict (a cross
  occupies one row AND one column; all pairs realizable). Bar LENGTHS are
  never set by the sort -- post-sort deficits regrow bars only up to the span
  of neighbours' assigned coordinates, which is the length any embedding owes.
  Reassign each round (not a one-shot cage). Genuine failure mode = honest
  infeasibility (total bar demand > wire supply = the clique cliff), reported
  by the existing violation diagnostic.
- **"Wrongly stacked" precisely**: co-row bars are a symmetric configuration --
  swap is a zero-gradient direction, slide-past raises energy first; gradient
  flow equilibrates at a smeared multi-bar-per-row compromise. The assignment
  is the symmetry break continuous dynamics cannot perform.

### Extent-state v1 verdict (2026-07-19; notes s3.28)

Built and probed; **pre-registered bar failed** (K100 14.7-15.3 vs bar 11.2);
default remains `state="point"`. Salvaged: bars of the right scale DO emerge
(extent_mean ~12 tiles on K100), the sparse limit is safe, and `seed_mode=
"bars"` is the only arm that legalizes K140 (2/3 vs 0/3 point-seeded) --
shape transmission works; the s3.10 multi-qubit-seed caution is refuted for
dense. The failure is the *assignment*: gradient flow cannot break the
row/column permutation symmetry (max_violation 14-25 at equilibrium; the
s3.9 deadlock at coarse level). v2 candidate, unbuilt: discrete
rank-order/matching step assigning distinct rows+columns to bars, dynamics
polishing around the broken symmetry.

### The smear reinterpreted; extent-state as the dense unification (2026-07-19 discussion)

Prompted by Max's "I don't understand what the smearing is / it's a hack if it
isn't the actual path": the smear IS a prior over chain geometry given endpoint
positions only -- a pre-route corridor forecast (RUDY's move). Its hidden false
assumption, now explicit: **contact happens between the endpoints**. The
current model freezes each edge's contact point onto the inter-centroid
segment; the crossbar violates this maximally (contact at (x_u, y_v), far from
both centroids). The dense failure is therefore a *representation* failure
with a named missing variable: contact location.

Two unification candidates (either makes busclique an EQUILIBRIUM of the same
dynamics rather than a rival algorithm -- important since template+polish is
existing D-Wave practice via DWaveCliqueSampler, so a template arm is parity,
not contribution):

- **(A) extent-state (build first)**: per-variable (x, y, h_extent, v_extent)
  -- an axis-aligned cross; deposit along your own bars (the planned shape;
  typed-pool charging becomes exact); an edge is satisfied when bars cross;
  extents grow only under contact demand, so sparse sources collapse to
  points (recovering today's model identically) and cliques grow bars (the
  crossbar emerges). Field machinery unchanged; only the stencil + a contact
  term + 2 scalars/variable. Pre-registered success bar (from s3.26): K100
  within ~15% of template ACL (~11.2, vs mm 13.6), no win-guard regression,
  no K140 feasibility failure.
- **(B) contact-point state (the theory behind A)**: per-edge movable contact
  c_uv; v's planned chain = tree through its contacts; smear along that tree;
  lambda_v = measured tree length. Current model = B with contacts frozen at
  segment midpoints; crossbar = contacts aligned into rows/columns. State
  scales with |E| -- richer, heavier, hold in reserve.

The attraction intuitions (neighbours close, don't overcompact) survive
unchanged; the state was too small to express what "close" means for extended
objects. K140's anti-placement reading likewise: disk-point seeds were the
point representation's only possible answer to a question it cannot parse.

### Ablation + dense-attribution verdicts (2026-07-19; notes s3.26-3.27)

- **mu multiplier field: measured inert** next to hinge2 (all cells, 5 seeds);
  staleness (30-60% of mu-mass on slack tiles) real but harmless. Default now
  `mu_alpha=0` by parsimony; the exact-dual/MCF alternative loses its urgency.
- **Cadence: wash under the poisson field** -- the v3 over-solving regression
  did not reproduce (push-field-specific or noise); geo_iters=1 stays default
  by cheapness, and the trust-region clip in the field carries the principle.
- **Frozen-RNG attribution: steering alone reaches parity with re-rolling**
  (geo10_frozen best on both win-guards) -- trajectory gains are geometric.
- **Dense verdict (s3.26)**: the busclique-derived template, restricted to the
  source's edges, beats every search method by 15-57%, and MM's polish cannot
  improve it at all (a local optimum of the chain-local move set). K100's gap
  was mostly budget split; near the cliff (K140) our seeds actively hurt and
  the default pipeline fails outright. NEXT BUILD: the **template arm** --
  generate the constructive prior, restrict, spur-prune, brief polish; run as
  a rival to the geometric rounds and keep the better (no density threshold
  needed; template evaluation ~free). This is the placement-first thesis at
  full strength: for dense sources the right placement is a theorem, and the
  coarse layer's job is to recognize that and select it.

### Strategic emphasis (Max, 2026-07-18)

Structured-source ACL wins are nice but secondary: minorminer's ecosystem role
is the robust fallback for *hard* embeddings, so the claim that matters is the
**hard-instance frontier** — success rate, time-to-first-legal, and
max-embeddable-n near capacity. Evidence in hand: §3.23's only-att bucket (396
graphs stock MM couldn't legalize in 60 s, concentrated in the tight 301–1000
band) — geometry winning on *feasibility*; and the structured/hard distinction
is mostly nominal (those wins were driven by tightness, not prettiness; the
mechanism is placement assembling globally consistent arrangements under
capacity pressure). Hard regime also reverses the budget confound (runs are
feasibility-bound; polish barely enters). Next eval after the ablations: the
**hard-frontier probe** — sample the §3.23 neither-bucket (7,819 graphs),
success-vs-budget curves at 60/300/900 s for both methods + per-class
max-embeddable-n cliffs. Dense-but-comfortable at ACL parity is acceptable;
dense *at the cliff* is the version that counts. (Busclique note: provably
extremal in clique *size* on Chimera-class fabrics — treewidth upper bound +
Boothby–King–Roy construction — but NOT proven chain-length-optimal for
sub-maximal K_n; degree counting gives ACL ≳ (n−1)/14 on Pegasus, ~30% below
busclique's K180 16.67. Verify exact bounds from the literature before
claiming or attacking optimality.)

### Confirmed (keep)

- **Density-limited attraction descends and beats the same-budget unguided control**
  — v1: −0.34 ACL vs control (10/15), −0.31 vs mm-full at half budget; edge
  replicated ×3 (v1, v2-vs-control, v2-vs-mm). §3.19–3.20.
- **Pure attraction (no repulsion) orbits — the force law needed the density term.**
  Pre-registered and confirmed. §3.18.
- **History is the feasibility mechanism of the deterministic replica** (substitutes
  for MM's randomness; ~2× legalization, −0.15 ACL paired there) — but **inert
  inside real minorminer** (300 paired runs, ΔACL −0.008). The cost axis is closed.
  §3.6, §3.11, §3.13.
- **The hybrid principle**: best attraction + best (unconstrained) polish. n=100
  probe: 6.16 in 5.9 s vs stock 5.66 in 5.4 s (single seed, ER — the class where
  parity is the ceiling). §3.22.

### Refuted (do not resurrect without new evidence)

- **Region-biased polish** (γ>0): search bias hides genuinely shorter rebuilds even
  with acceptance on true length; cut 17% where the free grind cuts ~37%. §3.22.
- **Best-of-N cheap legalizations selected by legal ACL**: legal ACL carries no
  information about polished ACL (r ≈ −0.01 pooled, ER). §3.16. *Caveat: measured
  on random basins; steered basins on structured sources unmeasured.*
- **Per-variable measured charge (v2)**: improves legal-stage geometry, not the
  polished endpoint; v1 kept by parsimony. §3.20.
- **Realized-footprint density charge**: logically inert (realized chains never
  exceed capacity-1); only *proposal* demand signals crowding. §3.20.
- **Attraction-only relaxation**: collapse is its fixed point; orbits. §3.18.

### v3 regressions — resolved by design in v3.1 (2026-07-18); ablation pending

The three unvalidated v3 changes (spectral init replacing MM round-0;
`geo_iters=10` replacing one-step cadence; 3 rounds replacing 10) are addressed:
cadence restored to 1 step per router projection (the trust-region reading — the
coarse model is a local proxy calibrated at the last realized embedding;
over-optimizing a misaligned proxy *harms*, it doesn't just waste — and its
fixpoint dynamics erase the router's feedback), rounds adaptive up to 10 under a
budget. Directional check: n=100 ER single seed 6.16 → **5.96** (v1 mean ≈ 5.95).
The proper paired ablation ({cadence} × {rounds} × {init}, using `vary_rng=False`
for clean geometry attribution) is still owed before publication claims.

### Known operational weaknesses (status after v3.1, 2026-07-18)

- **Budget structure** — FIXED: rounds capped at `round_frac` of timeout, polish
  reserve by construction, uncapped feasibility fallback when no round legalizes
  (verified on a §3.23 neither-bucket instance: 61.5 s total against a 60 s
  budget; star/wheel spur_prune blowups separately fixed by `deadline=`).
- **Correlated attempts** — partially addressed: adaptive R gives more, cheaper
  rounds; `vary_rng` separates the restart channel from the steering channel.
  Seeding from *bad* anchors being slower than unseeded (§3.10) remains
  unmitigated.
- **Vestigial selection** — default now `"last"` (trajectory endpoint);
  `"best_legal"` kept as the ablation arm. §3.16's null was measured on
  unsteered i.i.d. ER basins — steered+structured is unproven either way; the
  `round_acls` diagnostic accumulates the rank-stability data for free.
- **Disconnected sources**: spectral layout degenerates; components may stack.
  Still open (circle fallback catches only detected-degenerate cases).
- **Proxy metric**: drawing coordinates ≠ hop distance on Pegasus (long wires);
  error largest at snap resolution. Open; tile coarsening (roadmap 4) subsumes.

### Parked / next (ordered; one switch at a time)

1. ~~Budget fix~~ — done (v3.1: `round_frac` + fallback).
2. ~~Selection fix~~ — done (v3.1: `selection="last"` default).
3. Cadence/rounds/init ablation — machinery in place (`geo_iters`, `max_rounds`,
   `vary_rng`, `selection` all switchable); the paired experiment itself is
   still owed.
4. **BUILT (2026-07-18, field.py; probe: notes §3.25) — Tile-graph coarse target**: replace uniform layout bins with the hardware's
   canonical coarsening (Chimera = grid of K4,4 tiles; Pegasus/Zephyr unit cells).
   Re-corrected (2026-07-18, Max's second challenge): separate "edge
   capacities" are the WRONG abstraction — in these fabrics crossing consumes
   qubits (a horizontal crossing occupies an h-qubit in every traversed tile),
   so cut capacity is implied by node pools. What the current model actually
   misses: (a) **direction typing** — a tile's qubits split into
   horizontal/vertical wire pools (Pegasus: orientations, fractional tile
   membership); untyped capacity can read 50% free while the h-pool is
   saturated. Exactly VLSI global routing's gcells with per-direction track
   capacities. (b) **traversal charging** — point deposits charge only the
   sitting tile, never the passed-through tiles, which is HOW the field is
   blind to §3.21's cut constraint (cut demand never deposited). Route
   smearing (item 5) IS the traversal-charging mechanism — items 4+5 are one
   model: typed per-tile capacities + route-smeared typed demand.
   Solver note (corrected): flow does not replace force/gradient placement —
   even VLSI SOTA is ePlace-style nonlinear opt for placement, negotiated
   congestion for routing (Bonn's fractional-MCF resource sharing [`mueller2011resource`] being the
   shipped exception). The honest opportunity: our coarse routing subproblem
   (~256 tiles, ~10³ commodities) is small enough for Garg–Könemann [`garg1998mcf`] fractional
   MCF in milliseconds — whose multiplicative-weight prices are exactly the μ
   multiplier field with exponential updates (same lineage as §3.1's
   Raghavan–Thompson/AAP citations). Flow = the negotiation with guarantees,
   affordable at our scale.
   Trust-region interaction (2026-07-18, Max's question "does exact MCF repeat
   the v3 over-solving mistake?"): **no — the trust region governs steps in
   decision space, not effort in evaluation space.** The v3 sin was letting the
   model extrapolate the placement (unbounded step); MCF with pinned endpoints
   moves nothing — it exactly evaluates the *current* placement's congestion,
   which only improves gradients. Being an LP, its duals are a memoryless
   function of the current placement — shadow prices that structurally cannot
   be stale (an answer to the μ-field trajectory-shadow critique; loses μ's
   noise-damping memory — measurable pair: hinge²+μ vs exact duals). Caveats:
   never transmit fractional routes downward (fractionality gap; downward map
   stays snap-to-seeds); placement steps remain bounded however sharp the
   duals; one solve per fresh measurement (exact on stale λ = exactly optimal
   for the wrong problem).
5. **BUILT (2026-07-18, segment smear; anisotropy weights + multi-qubit seeds
   still deferred) — Mass + shape charges**: smear each variable's λ along its expected chain
   instead of a point deposit (fixes the dense-regime monopole lie cheaply; the
   full particles-per-qubit model is the expensive limit).
   Design settled (2026-07-18): smear along **straight segments** between
   endpoint positions (RUDY-style; continuous in positions — tile-path stencils
   would step discretely on re-route), stencils recomputed per iteration and
   frozen for the gradient step. Two roles per the §3.20 lesson: **measured**
   footprint (realized chain per tile) only *calibrates* λ_v and per-neighbour
   anisotropy weights — it can never exceed capacity, so it can't pressurize;
   **proposal** smear (λ_v along segments from proposed position toward
   neighbours, anisotropy-weighted) sources the field. Downward map initially
   UNCHANGED: snap position → single-qubit seed (smear lives only in the
   geometry layer). Multi-qubit shape-transmitting seeds are a separate later
   switch (§3.10 anti-placement risk — do not bundle). Cost: O(|E|·route-len)
   deposits + a tiny Poisson solve ≈ sub-ms/iteration — negligible vs ~1 s
   router calls.
6. **BUILT (2026-07-18, PoissonField; hinge²-only vs +μ ablation owed — first
   staleness data: 32–60% of μ-mass on slack tiles, §3.25) — Continuous
   long-range density**: ePlace-style [`lu2015eplace`, `cheng2019replace`] Poisson/electrostatic field or a
   capacitated-transport solve, replacing one-bin local pushes — fixes the plateau
   problem (interior of a uniformly overfull region currently cannot move; only the
   rim peels). Max's "real-valued centroids drifting under continuous repulsion".
   Architecture note (2026-07-18 discussion): attraction is NOT part of the field —
   the ePlace objective is `wirelength(x) + μ·potential(x)` with all-positive
   charges; electricity models only "spread where density > capacity", connectivity
   only ever enters the wirelength term, and μ ramps (attraction-dominant early,
   capacity-enforcing late).
   **Open risk — charge-feedback instability** (Max, 2026-07-18): charge = realized
   chain length is lagged measured feedback; congestion fat inflates demand →
   field over-spreads the region → intrinsically longer chains → more demand
   (positive feedback through the router, one-round lag). Partly self-limiting
   (push is thresholded on overfill; when crowding causes length, spreading
   shortens chains = negative feedback), but the fat channel is real. Mitigations,
   in order: damped/capped charge update `λ ← (1−τ)λ + τ·realized` (same lesson as
   §3.4 history decay); derive demand from the coarse model itself instead of
   lagged fine-level measurement; smear charge along the chain route (a point
   deposit puts all of v's charge exactly where v's neighbours must sit — the
   monopole shells its own friends; a smeared deposit defends the route against
   unrelated variables instead). Exclude self-force (v's own deposit must not push
   v).
   Field design settled (2026-07-18 discussion, revised same day): decision
   variables stay per-variable positions; the *deposit* is route-shaped
   (RUDY [`spindler2007rudy`]-style: ~1 unit at the variable + λ−1 smeared along the expected route;
   dead qubits = fixed charges). Source the Poisson field **one-sidedly from
   violation only**, NOT stock ePlace's mean-subtracted total density — stock's
   two-sided field pulls cells into all whitespace (uniform-utilization objective,
   wrong for us: chain length scales with occupied-region size, §3.21; we want
   compactness). One-sided source keeps "slack fabric is silent" (field ≡ 0 when
   nothing violates anywhere) yet still fixes the plateau: by Gauss's law an
   interior centroid of an overfull blob feels force ∝ total enclosed excess, not
   just its own bin.
   Rectifier choice (Max rejected softplus — rightly: strictly positive tails =
   phantom repulsion from slack fabric; sharpening recreates the kink). Two
   principled forms, both exactly zero on slack:
   (a) squared hinge `max(0, ρ−c)²` — C¹, canonical exterior penalty method with
   μ-ramp; the raw hinge's defect was the derivative *jump*, not the zero tail.
   (b) **multiplier field** — μ(x) ← max(0, μ(x) + α(ρ(x) − c(x))),
   μ sources the field. This is the §3.5 history update lifted from qubits to the
   coarse grid: zero-on-slack is complementary slackness (a KKT property, not
   curve-shaping); smoothness lives in bounded iteration steps, no rectifier
   needed; memory integrates persistent violation and damps transient noise
   (also mitigates the charge-feedback instability above). Unifies the fine-level
   history term and the coarse-level density field as one Lagrangian mechanism at
   two scales.
   Decision (Max, 2026-07-18): **both have value — implement as an ablation
   pair**, `source = hinge²(present) + μ(history)` — which is the McMurchie–
   Ebeling present+history decomposition at the coarse level. hinge²-only is the
   memoryless control arm; +μ is the single flip; knobs α and asymmetric up/down
   steps (same open knob as §3.5). Risk register for μ (Max's critique): in a
   nonconvex problem the multipliers are shadow prices of the trajectory, not the
   problem (no duality theorem); stale μ-hills can deflect ACL-reducing moves and
   slow convergence — bounded by the decay clock (~h/α iterations), but our coarse
   optimizer is deterministic gradient flow, i.e. closer to the deterministic
   replica (where history had real teeth AND the h≈108 no-yield ratchet was
   observed, §3.9) than to randomized MM (where scars were repeatedly tested and
   found second-order, §3.9/§3.13). Pre-registered diagnostic: fraction of total
   μ-mass on currently-slack bins over the trajectory, correlated with descent
   stalls — so the stale-shadow failure mode is detectable, not arguable.
7. Native-arm speed (only if the purity arm earns investment): BFS instead of
   heap-Dijkstra at uniform prices; `targets=` early-exit in
   `weighted_multisource_dijkstra`; region-bounded searches.

### Predictions on record — full-Ember sweep of 2026-07-17 — SCORED (§3.23)

(attraction hybrid v3 vs stock minorminer, 23,642 P16-eligible graphs, 60 s,
shared seed. Overall: paired ΔACL +0.016, W/L/T 6,481/5,995/1,114; successes
13,986 vs 15,427 — see notes §3.23 for the full table and the two bugs the
sweep exposed, both fixed: isolated-vertex seeding [1,546 failures, ~the whole
success gap], unbounded spur_prune on hub sources.)

- Small n: ACL ties, wall-clock worse but sub-timeout. → **CONFIRMED.**
- Mid-size structured: best chance of genuine ACL wins. → **CONFIRMED, stronger
  and larger than predicted**: regular 301-1000 −0.755 (82/5), planted_solution
  301-1000 −0.497 (512/188, +154 net feasibility), watts_strogatz −0.21,
  lattices swept at scale (honeycomb n>1000 11/0, bcc 6/0).
- Mid-size random/expander: parity to slight loss. → **WORSE at the congested
  band** (ER 101-300 +1.24) — consistent with the unvalidated v3 regressions;
  cadence ablation now urgent.
- Dense: blunted to ~parity by the plateau problem. → **TOO OPTIMISTIC: clear
  losses** (complete +8.2, turán +4.1, bipartite +4.0, weak_strong_cluster
  +0.3–0.5 everywhere). Plateau + monopole now the top algorithmic defect;
  roadmap items 5–6 rise in priority.
- Hard-tail success deficit. → **CONFIRMED but ~fully bug-1-explained; INVERTED
  at 301-1000** (only-att 396 concentrated there): seeding is a feasibility
  mechanism at scale.
