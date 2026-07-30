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

## B. As-built: v3 hybrid (registered as `attraction`) — HISTORICAL

**Superseded by the 2026-07-29 consolidation (ledger entry at the top of
§C): the registered `attraction` is now the single stair+arrange pipeline,
spec'd in `anatomy.md`; the v3 hybrid below and every superseded variant
live at archive commit `612ced3e`.** This section is kept as the fossil
record of the pre-consolidation pipeline.

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

### Contact Stage 2 — one bar of four; gridlock + the stubborn pile (2026-07-30; notes s3.46)

Connected BFS readout + per-contact preconditioning, probed. ER win
holds (4.72; twice-reproduced vs mm 4.97/mm2 4.86). K100 improves
17.24→15.50 (bar ≤13 missed). turán ROUTES for the first time (2/3,
15.5) off a still-terrible placement — the readout direction is right —
but the pile survives the preconditioner (resid 928; the K6,6 miniature
passed, K81,81 didn't: NOT step-size throttling; hypothesis =
attraction-dominated equilibrium, needs a per-term force-decomposition
diagnosis, not a third integrator patch). spin_glass REGRESSED (seating
0.26→4.63; routed 0/3): the exclusive connector claiming gridlocks —
dropped seats 49–92% per cell. Named fix candidate: connect WITHOUT
claiming (overlapping connectors; MM's overlap pricing resolves — our
exclusivity was more rigid than the router's own design premise).
1/4 bars; report + discuss. No default changes.

### The contact round — Option B unshelved; first liquid-family WIN (2026-07-30; notes s3.45)

Max's edge-placement reframing = the 2026-07-19 Option B, its hour
arrived. Step-0 diagnosis first: s3.44 was OPTIMIZER-STUCK (hand layout
at half the settled E_total) and even hand layouts keep overload 9 —
contact-pinning convicted. Built `contact.py` (contacts as state, nets as
variables, junction density as native point pressure; FD gate first-run
green, third consecutive). Probe (Z12): **ER100_d10 4.65 vs mm 4.97/4.86
— the program's first family win over minorminer, with exact seating
(resid 0.0)**; spin_glass placement SOLVED (resid 0.26 vs the node
model's pinned 57) but Stage-1's disconnected seeds fail routing; K100
feasible but readout costs ~7 ACL; turán's central contact pile (resid
965) reproduces the hot-spot-α conditioning diagnosis undiluted. Next
moves named by the data: Stage-2 readout (SPH net routing over seats),
diagonal preconditioning. No default changes.

### The Poisson round — term verified, cells unmoved; diagnosis needed (2026-07-30; notes s3.44)

Two-term pressure (hinge feasibility + Poisson interior gradient; the
pure electrostatic form measured contrast-blind and amended same day —
G kills constants, so ½sᵀGs alone drives overload toward UNIFORMITY,
not zero). FD gate green on the summed weights; plateau unit tests
pass. **Go/no-go FAILED: the pinned cells are unmoved** (28.9/57.7 vs
27.4/56.1 at λ 16k) — the plateau was true but not binding there.
Feasible spread states exist by mass counting; descent can't find them.
Recorded diagnoses for the next decision: early-settle tolerance
semantics at large λ·P; hot-spot α throttling (wants a diagonal
preconditioner); or something structural in the readout (Max's "scary"
question). NEXT: a diagnosis probe (P trajectory, per-variable steps,
and whether a hand-built feasible layout is even downhill-reachable)
before any further mechanism. Probe phases not launched; no default
changes.

### The Armijo integrator — numerics fixed; the plateau is the real wall (2026-07-30; notes s3.43)

contract v2.1: frozen-model Armijo backtracking + hardening tail
(penalty continuation to λ 16k). Bang-bang dead, descent monotone by
construction, wall-time halved — and the residual stays pinned (27/56 on
the s3.42 cells): the pre-registered PLATEAU rule fired. Local pressure
is gradient-blind inside uniformly overloaded blobs (only the rim peels);
Gauss's-law problem, third appearance (s3.19, s3.42-risk, now measured
clean). Probe not launched (leak bar fails at smoke). DECISION PENDING
(Max): the recorded fallback — Poisson-solved pressure source
(electrostatic energy of the overload; interior feels enclosed excess) —
own mini-derivation + FD tests under the s3.42 discipline.

### The pressure round — physics verified, integrator failed (2026-07-30; notes s3.42)

The phase-picture synthesis (gas/crystal/liquid as ground states of
E = wirelength + line-overload barrier): derivation committed BEFORE code
(s3.42(a)); forces verified by finite-difference gradient tests on first
run. Smoke feasible (resid 0.0). Phase A at probe scale: **leak-closed
bar FAILED** — residual overload 24–160 on dense cells, diagnosed to the
INTEGRATOR: a stiff barrier (o ~ 100 → force ≫ the 1-tile clip) turns
fixed-step descent into full-tile bang-bang; soft-λ cycles beat hard-λ
cycles (best_cycle=0 fingerprint). Where the barrier is soft, it works
(P16 regular 0.1, wsc c3 0.22). Blob-area law: first data, occupied
~1.5–2× predicted (right order, outside the 25% band; unscoreable until
settlements are real). Integrator candidates on record, unbuilt:
per-step E_total acceptance with step-halving; force normalization with
decaying schedule; within-cycle λ continuation. The derivation, FD
tests, and pressure machinery stand; contract v2 stays probe-callable;
no default changes.

### Contraction Stage 1 — the leaky wall (built + probed 2026-07-29; notes s3.41)

Max's "capacity should never veto an energy-lowering move; approach
capacity from below" + two amendments (settle-and-reshake cycles; Zephyr
frontier). Built: `contract_layout` (spread-start, entry-gated excluded
volume, cycles), typed Zephyr TileGrid adapter, derived κ (target mean
degree − 2; kappa=None default — the 13 stops being magic). Verdict:
screen passed on the letter but **the wall leaks through arm growth**
(entry gating stops bodies; arms lengthen in place; dense settlements
60–140 over depth — their E is fictional) and the routed bars failed
along exactly that line (Z12 spin_glass 0/3; sparse E gains bought no
routing). CONFIRMED: cycles (reshake rescues jams 10–100× — keep),
multi-patch payoff where the wall holds (P16 wsc c3×K32 5.32, gap 0.64 ≤
0.7 target — the round's one routed win), Z12 ER win. REFUTED:
magnets-rate (unnormalized hub-rush thrashes; normalized + cycles wins).
RECORDED: first per-cell Z12 baselines — mm markedly stronger on Zephyr
(margins thinner everywhere). Stage 2 precondition, if pursued: a
growth-tight wall (excluded volume must bind BARS, not just bodies).
No default changes; `contract_layout` stays probe-callable.

### Local interpolation refinements (built + probed 2026-07-29; notes s3.40)

Max's design ask: one simple rule interpolating between perfect clique
embedding and geometric layout, never aware of any particular cluster.
Built: `edge_monotonize` (per-edge x-transpositions, strict E-gate —
replaces the global `_align_diagonal`; leverage ∝ edge length IS the
interpolation), arm-length per-axis participation (interval ≥ 1 tile
replaces deg > κ; κ is floor physics only), value-priced insertion with
fixed anchors (+ the lexicographic ε-tie-break after the bisection found
the tie-plateau: post-packing y-values quantize, flat proxy, no strict
descent — rank pricing had been an accidental smoother). Discovered: the
diagonal is sufficient not necessary (contiguous-suffix "tent" states are
E-equivalent and ROUTE fine — K100 13.09/13.14, best ever). Post-fix
board holds or improves everywhere except two recorded misses: random-init
turán 9.93 vs the 8.5 emergence bar (the global permutation's long jumps
are not fully replaced by local transpositions — candidate fixes on
record: E-tie monotone bias, block insertion, or accept spectral
dependence on multipartite) and ER +0.25. wsc: c8×K32 and c3×K64 now
WINS; c3×K32 gap −1.16 → patches-too-small confirmed as the dominant
small-patch story. Deleted: `_align_diagonal`, the degree gate.

### THE CONSOLIDATION — one algorithm (2026-07-29; notes s3.38)

Max's call ("I can barely follow one version... it's the ideas and our
discussions that count"): the registered `attraction` is now the single
stair+arrange+insertion+wire-seeds pipeline; everything superseded is
DELETED from the tree and lives at archive commit `612ced3e` + this ledger.
Current as-built spec: `anatomy.md`. Deleted, with verdicts: point state
(relax + DensityField push; dense losses s3.23), cross state (extents as
state; s3.28-31, span dominated with fewer knobs), span field dynamics
(PoissonField, RUDY smear, deposits/forces, assign_rows_cols; arrange owns
every measured dense cell since s3.35-36), mu multiplier field (inert,
s3.26), slack_relax (inert as built, s3.33), wire_couple (superseded by
wire_exact), seed_stride, swap-Metropolis contingency (inert at 30 sweeps,
s3.35), region-priced polish gamma (refuted s3.22), selection="best_legal"
(s3.16), native backend/polish purity arm (Max's call; `factored` stays
registered), charge feedback lam0/lam_tau (span deposits are forward
functions of positions). KEPT parked: bar_domains + restrict_bug_repro.py
(Max: the exact-handoff interface for the STRIP-MINORMINER-DOWN agenda —
"how much of minorminer can we strip down; its exhaustive searching should
be rendered unnecessary by our guidance"; unblock = fork-level patch of the
restrict_chains hang when its hour comes, no upstream report wanted).
wire_exact stays the one seed switch, default off (K100 champion is blind
greedy; matching holds K140/spin_glass/turan records).

**Defaults flipped to the champion config**: insert_sweeps=8 (was 0),
readout/dynamics/seeds hardwired stair/arrange/wire, and — per the probe's
pre-registered protocol rule — **max_rounds=1, round_frac=0.5** (1shot beat
the rounds protocol on ALL four dense cells; rounds re-derive geometry from
realized centroids and destroy insertion-found order, turan 12.73 vs 8.40).
Tests 745 pass (35 deleted-machinery tests removed).

**Consolidation probe** (pre-registered bars in the plan + s3.38; 3 seeds,
60 s, P16, 8 workers; the first 24-worker run was DISCARDED as
contention-confounded — load ~70, spin_glass 0/3 for every arm including
mm, while a sequential run legalized in 2 rounds): new default (1shot) vs
paired stock mm — K100 13.41 vs 13.77 W; K140 18.55 vs 21.91 W 3/3;
**spin_glass 17.22 vs 24.53 (mm 2/3) W — new record** (old 17.50); turan
8.40 vs 8.26 (-0.14, parity; mm near-optimal there); regular_n316 3.56 vs
4.02 W; ws_n486 3.76 vs 3.89 W; ER100_d10 5.88 vs 5.67 (~noise). Minimum
bars met except the turan hair; target bars met on spin_glass + turan,
K100/K140 target (<=12.6/<=17.6) NOT met in-pipeline. Gap suspect (1)
compact init: probed (init30, pre-registered acceptance) — K100/K140 -0.15
but turan +2.0 / spin_glass +0.5 (compact init interleaves blocks harder
than insertion recovers; the s3.35 circle-init lesson) — REVERTED; the
acceptance rule as written passed on its letter (it omitted non-K100 dense
cells) and was overridden by the consolidation's own minimum bars, noted
here as a pre-registration drafting lesson. Suspects (2) insertion
plumbing: confirmed working in-pipeline (turan 8.40 ~ harness 8.24/8.47).
Remaining opens on record: (a) the K100/K140 in-pipeline residual vs the
harness records (12.51/17.04) — suspect eta and harness protocol details
(mean-over-routing-seeds on ONE arrangement vs per-seed re-derivation);
cross-run absolutes are noisy on the shared box (mm itself swung
13.72-14.33 between runs) so chase this on a quiet machine; (b) ws_n486:
rounds beat 1shot there (3.41 vs 3.76) — seeded re-rolls help sparse
quality; a participant-gated adaptive-rounds rule (dense => 1shot, sparse
=> rounds, using the existing capacity gate, no topology detection) is the
obvious candidate, UNDESIGNED, needs its own decision.

### Wire-exactness — alternating per-line matchings (built 2026-07-31; notes s3.37)

The s3.36 residual decomposes ~60% coupler repair / ~40% seed slop. Fix:
`wire_seeds_matched` — per line, arms grouped into TRACKS (interval color
classes; #tracks = depth, so tracks->subs matching never breaks the
chi=omega feasibility), tracks matched to physical subs by maximum-weight
bipartite matching (scipy linear_sum_assignment, 12x12/line), alternating
columns<->rows: coordinate ascent on satisfied DESIGNATED crossings, exact
per half-step, monotone, deterministic. Hungarian = discrete OT at eps=0
(Sinkhorn's exact limit — Max's early intuition closes the loop).
**Runtime is ALWAYS best-effort (Max): unsatisfied crossings are left for
the router, exactly as with greedy coloring; no error paths.** Tier
discipline: matchings only; below-bar => report + discuss, no SAT/ILP
escalation.

**Pre-registered bars (before any run):** mechanism — designated-crossing
satisfaction >= 99% on K100 (blind-greedy baseline 95.7%), strict
improvement everywhere (spin_glass 92% the big target); K100 routed <=
11.2 (the s3.26 bar, now the EXPECTED outcome); spin_glass < 17.5; K140
<= ~17.0; turan holds <= ~8.5; sparse untouched (participants only);
matching wall-time <= ~1 s at n_p~163. K_n sanity: ~100% satisfaction
expected (busclique existence); if seeds come out fully legal, record the
router-optional milestone. Verdict (same day; notes s3.37): mechanism bar REFUTED — matching plateaus ~62-67% (greedy = chance ~56%); two causes named: the objective omits SELF-JUNCTIONS (K100 connectivity 100->44, routed regressed 12.51->13.25) and the busclique existence proof does not transfer to coupler-blind layouts (perfect assignment may not exist post-hoc; co-design needed). Where corners don't bind it already wins: turan 8.04 (record; mm 8.26 beaten), K140 17.17 (record). STOPPED per tier discipline; design-round item (i) APPROVED by Max same day ('the self-coupler thing definitely should be fixed'): junction-weighted objective built (junction_w=2.0; contacts metric unchanged for comparability). Mini-bars for the rerun: K100 conn >= 95/100 and routed <= 12.51; spin_glass <= 18.05; turan <= ~8.1 and K140 <= ~17.2 hold. Junction-fix rerun verdict: conn restored everywhere (K100 100/100, spin_glass 150/163); records K140 17.04 + spin_glass 17.50; turan 8.04 held; K100 matched still trails blind greedy (13.13 vs 12.51) — open, co-design domain. Remaining agenda: geometry/wire co-design (Pegasus-era problem — Zephyr's junctions are COMPLETE per dnx topology, the 56% pathology absent there; Zephyr currently untyped in TileGrid, adapter queued), corridor reservation.


### Insertion order search + random-init standard (built 2026-07-30; notes s3.36)

The general global move after s3.35 measured adjacent swaps plateau-bound:
`insertion_sweeps` — best-insertion (rank relocation) on the participants'
queue, exact integer-slot semantics (the fractional-rank shortcut collapses
— rank stacking, s3.30's pathology reborn in the proxy — caught by the
clique no-op test), candidates adjacent to neighbours' slots, monotone,
deterministic; wired into alternate_arrange as `insert_sweeps` (default 0)
with propose-in-rank-space / dispose-by-true-E composite gating.
Corridor/routing-capacity reservation explicitly OUT OF SCOPE (Max: naive
reservation sabotages cliques; needs its own design round) — open question
on record: arrange mode does not price non-participant traversal
(suspected weak_strong_cluster loss mode).

**Pre-registered bars (before any run):** PRIMARY — turan_n162 with
insertion: block separation EMERGES (mean-rank gap of the two sides >
0.9 * n/2) and routed < 10.97; stretch <= 9.5 (~mm+15%).
INIT-INDEPENDENCE — random-init arms within ~5% routed of spectral arms on
all four cells (spectral demoted to warm-start heuristic).
GUARDS — K100 <= ~12.5+noise, K140 <= ~17.6+noise, spin_glass <=
~18.1+noise, all 3/3. WALL-TIME — insertion phase <= 2x the alternation's
own wall-time (printed per call); K_n must no-op in one sweep
(permutation-symmetric, verified in tests). Failure modes on record: no
block emergence -> paired/block insertion next, NOT a bipartite rule;
random-init fails while spectral passes -> structure was living in the
init; report as-is. Verdict (same day; notes s3.36): PRIMARY BAR PASSED COMPLETELY — blocks emerged 81/81 from BOTH inits; turan routed 8.47/8.24 (random BEATS mm's 8.26). Guards passed. Init-independence 3/4 (K100 random fails — insertion provably inert on K_n; the deficit is continuous contraction, attraction's real job; 1-step harness artifact, cheap remeasure pending). Wall-time bar miscalibrated (letter failed at 20x an 0.05 s alternation; absolute 0.2-5 s ~ 3-8% of one routing call). Dense board now swept vs stock mm: 12.51/17.39/17.59/8.24 vs 13.44/20.70/25.37/8.26. Open: corridor reservation (own design round), K_n template gap, pipeline confirmation.


### Diagonal alignment + order-search (built 2026-07-30; notes s3.35)

The s3.34 K100 residual (E 1211 vs template 878) was mis-attributed to
within-row nesting; the true cause: the two 1-D orders were UNCORRELATED
(rows sorted by y-noise, columns by x-noise), so h-arms reach backward.
Busclique's diagonal = x-rank == y-rank; aligned, E = n*side ~ 880 exactly
(K4 arithmetic in conversation, 2026-07-30). Built: `_align_diagonal` in
alternate_arrange (stair readout only) — a pure PERMUTATION of the
participants' existing x-values (x-rank := y-rank), E-gated like every
projection; acts only in attraction's null directions. Max's call: no
dual proposals — committed diagonal bias, the standing E-gate is the only
safety. Row-first vs column-first: mirror-symmetric, transient-only
difference; row-first kept. ALSO REALIZED (kills the per-edge orientation
variable proposal): the diagonal rule already CONTAINS the biclique — if
the y-order separates bipartite blocks, one side's chains are pure
h-lines and the other's pure v-lines. Turan's failure was an ORDER
problem (interleaved blocks from the circle init), so the general move is
order-search on y = the existing swap sweeps, now scoring stair E.

**Pre-registered emergence bars (one configuration, no topology
detection; before any run):** K100 aligned — E <= ~950, seeds <= ~11,
routed <= 11.2 (the s3.26 bar becomes the PRIMARY bar for the first
time). Turan_n162 — swap sweeps must discover block separation
(E drops materially vs swap-free; routed < 10.97 = improvement,
<= 8.26 = parity with mm). K140 — no regression (3/3, ~<= 19.5+noise).
spin_glass_n163 — hold ~<= 21. Sparse guards structurally untouched
(no participants). Verdict (same day; notes s3.35): K100 12.51 — FIRST search win over stock mm in program history (13.44); K140 record 17.64 (-3.1 vs mm); spin_glass 18.05 (alignment general — irregular cell -2.5); turan: adjacent swaps measured PLATEAU-BOUND exactly as pre-registered (E 2276->2219 vs optimal ~1094; mm 8.26 is near-optimal there); blocks did not emerge; swap contingency inert everywhere at 30 sweeps. Next (unbuilt): rank-RELOCATION order moves + the random-init emergence arm (init-independence standard, Max 2026-07-30: p-norm/spectral layouts are warm-start heuristics, never load-bearing).


### Staircase readout — per-edge single coverage (built 2026-07-29; notes s3.34)

The 2x-overpay fix: the cross readout pays every edge at two crossings
(seed ACL 20 vs implied 10 vs busclique 9.78, measured 2026-07-29).
Busclique's construction verified in source = the staircase (arms
row+col ~ constant, one crossing per pair). Generalization = the DIAGONAL
RULE, a pure readout: edge (u,v) covered at u's h-arm x v's v-arm iff
(y_u,u) < (y_v,v); arms span assigned contacts only. State unchanged
(positions); order-preserving packing keeps the assignment invariant
(the sort is now load-bearing for correctness). Built behind
`readout="stair"` (default "cross" = stock): derive_bars_stair,
stair_energy, stair_step, alternation readout param; +7 tests (515 pass).

**Pre-registered bars (before any run):** sanity — staircase seed ACL at
derate 1.0 ~ 10-11 (cross readout: 20); if ~20 the rule is miswired, stop.
Testbed gate: K100 stair(+couple) polished <= 13.15 to run the pipeline
probe; **stretch <= 11.2 (the s3.26 bar, within 15% of template — plausible
for the first time)**. K140: 3/3 legal, no regression vs 21.84/19.69.
Risk on record: single coverage forfeits the redundancy that made
double-covered seeds auto-legal; the 56% coupler density now bites at
designated crossings — expect seeds NOT legal, `+couple` essential, MM
doing real (short-range) repair. If repair overhead eats the 2x gain,
verdict = single coverage needs busclique-grade t-coordination (next:
exact per-line matching).

**Verdict (same day; notes s3.34): K100 gate FAILED (14.21 vs 13.15 —
though best-ever for arrange-family) BUT: K140 program record 19.51, 3/3,
paired win over stock mm on every seed; halving confirmed (seeds 20->14,
repair costs ~0.2); polish collapse (seed ~= routed — converging on the
constructive no-router limit); coupled scoring retired (0-for-4).
First-ever irregular-dense measurement: spin_glass_n163 WIN 20.53 vs mm
25.37 (2/3) — paired + feasibility, the home-turf thesis confirmed;
turan_n162 LOSS (8.26 vs 10.97) — the diagonal rule is clique-shaped,
bipartite needs a block-aware orientation rule. K100 residual = packing
NESTING (E 1211 vs template 878; one-arm-per-wire complementary-length
pairing vs our similar-length stacking). Options in s3.34.**


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

### Product mode — alternating 1-D arrangement (built + probed 2026-07-27; notes s3.32)

**s3.33 build (2026-07-27, Max: "let's do 1 and 2"): coupler-aware coloring
+ handoff slack.** Premise verified: Pegasus tiles couple only ~56% of h/v
wire pairs (80/144 at a P4 tile; Chimera 16/16 — mechanism no-ops there).
Built, all default-off: `wire_couple` (t-coordinated coloring: columns
prefer subs that couple to contact partners' assigned row wires at the
crossing tiles — the coloring stays exact, the score only breaks the
freedom), `slack_steps` (slack_relax: fractionalize within assigned lines,
round() invariant), `seed_stride` (claim every stride-th qubit — partial
confidence). **Pre-registered gates, set before any run:** testbed K100
coupled(+slack) finalist ≤ 13.46 to run the pipeline probe; ≤ 13.15
confirms the coupler mechanism (beats the field dynamics); < 13.44 = first
K100 search win vs stock mm. Mechanism check: realized couplable-contact
fraction must RISE under +couple, else the scoring is miswired — debug
before interpreting ACL. Mandatory K140 regression check: the s3.32 cliff
win (arrange-1shot 19.69, paired 3/3) must survive coupled seeds. Routing
×3 seeds per finalist (s3.32 bimodality lesson). Status/verdict (same day, notes s3.33):
coupler mechanism REAL at tight packing (15.09 -> 14.51, all seeds) but
the gate FAILED at every operating point (best 14.51 vs 13.46); slack
inert as built (floor/ceil swallows sub-tile shifts); the
couplable-fraction metric saturates and needs a per-crossing redesign.
Sharpest finding: uniform exact packing QUANTIZES row counts
(10/11/12/13/16 — the field's winning 14-row state is unreachable), and
routed ACL is non-monotone in rows; the field states' residual advantage
is heterogeneity, not physics. Knobs stay default-off. Per-regime
standings: field dynamics owns comfortable-dense (13.15), arrange owns
the cliff (19.69 K140, paired 3/3).

The product-topology framing made operational: capacity-forced variables
packed into integer rows/columns by monotone coordinate descent on the span
energy (exact per-line interval packing; capacity = overlap depth — no wire
coloring in the algorithm). `span_dynamics="arrange"`; no field calls on
that path; swap-Metropolis contingency default OFF (E-neutral on K_n, as
the symmetry argument predicted). As an optimizer: 2 iterations / ~0 s
replaces 300 field steps / ~20 s, exact feasibility, zero schedule knobs.

**Verdict (mini-probe vs s3.31 baselines): K140 — first ACL win over stock
minorminer on any dense cell: arrange-1shot 19.69, arrange 20.45, vs mm
20.70, all 3/3 legal** (point/cross fail 0/3). K100 unbeaten (arrange
14.60; the 13.46 bar stands; testbed keep-alive failed at 14.22 — the
E-vs-routability wedge, measured a third way: tightest-E states route
worst). Guard ws_n486 3.41 = the standing span-arm offset, arrange inert on
sparse by capacity gating. Defaults unchanged; the emerging role is
regime-specific — product mode + wire seeds as the cliff/hard-frontier
configuration. Next: hard-frontier eval with arrange-1shot; irregular-dense
cells; slack-aware objective for the K100 residual.

**Domains handoff PARKED on an upstream minorminer 0.2.22 bug** (report
upstream): `restrict_chains` + `initial_chains` on the same variable hangs
indefinitely ignoring the timeout (isolated repro; restrict alone returns
instantly; disjoint variable sets safe); segfaults also observed with
non-trivial domains. `bar_domains` is built + tested; `seed_mode="domains"`
raises until a fork-level fix exists.

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
