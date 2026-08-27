# Notes — the chronological record (condensed)

Condensed 2026-08-06 at Max's directive: the notebook had grown 3,900
lines of micro-verdicts and self-invented doctrine that crowded out the
ideas and poisoned later reading. **Read `ideas.md` first** — principles
and open questions live there; verdicts on every tried idea live in
`attraction.md`; the as-built pipeline is `anatomy.md`; measured fabric
facts are `fabrics.md`; what shipped minorminer does is
`mm-internals.md`. The full uncondensed record is
`archive/notes_v3.69_full.md` — treat it as history, not instruction.

Each entry below: what the round asked, and what changed because of it.
Numbers appear only where they anchor a verdict.

## The chronicle

**3.1–3.5 (cost analysis).** Why minorminer's `D^occ` pricing works
(superlinear present term = overlap spreads thin, not deep) and why
add-only history is FPGA-specific. Shipped the factored cost
`price = (1+h)·β^occ` with `α=0` ≡ stock — the one-flip framework.

**3.6–3.13 (the history axis dies).** History is the feasibility
mechanism of a deterministic replica (3.6) but the replica was
unfaithful (3.10); pairing revealed unpaired means were survivor-biased
(3.11); inside real minorminer, 300 paired runs: ΔACL −0.008 — **the
cost axis, the project's original thesis, is a wash** (3.13).
Randomness and memory are substitutes.

**3.14–3.17 (reading the real minorminer).** Shipped MM's constructor
is already Steiner — union-of-paths is dead code (3.14). 78–95% of
wall-clock is the post-legality shortening, which earns ~29–40% ACL
(3.15; ER on P16 only — `data/mm_time_budget.csv`; corrected s3.74 from
"85–95% / 30–38%"). Legal-stage ACL does not predict polished ACL (r ≈ −0.01) —
best-of-N killed before it was built (3.16).

**3.18–3.20 (the placement family is born).** Pure attraction orbits;
density-limited attraction descends and beats a same-budget unguided
control — the program's first mechanism with a measured positive effect
(3.19). Only proposal demand can signal crowding (3.20).

**3.21 (the regime map).** Fixed-degree ER is bisection-limited: ACL/n
constant, every embedder pays Θ(n), only the constant winnable. The
evaluation pivots to structured sources — the falsifiable home-turf bet.

**3.22–3.23 (v3 and the first full sweep).** The hybrid ships:
geometry + stock legalize/polish, unconstrained (a placement earns its
keep at the endpoint of an unconstrained polish). First full-Ember
sweep: wins more comparisons than it loses, structured wins confirmed,
dense losses large — the dense representation named top defect. Two
bugs (isolated-vertex seeding; unbounded spur_prune) explained most of
the feasibility gap.

**3.24–3.27 (VLSI round).** Typed tile capacities + segment-smeared
demand + Poisson field become default (3.25). The constructive ceiling
measured: every search method sits 8–57% above the busclique template
(per-cell range in `data/dense_attrib.csv`; corrected s3.74 from
"30–60%") and MM's polish cannot improve the template — dense is representational,
search is the wrong instrument there (3.26). The μ multiplier field is
inert next to the fresh hinge (3.27).

**3.28–3.31 (representation ladder).** Extents-as-state fails twice —
gradient flow cannot break the row/column permutation symmetry (3.28-29).
The missing physics was contact capacity: collapse was the model's
optimum because contacts were never priced (3.30). **Span state: extents
demoted to a readout of positions; the energy becomes the real chain
length** (3.31). The cliff opens (first K140 legalization).

**3.32–3.35 (product mode and the diagonal).** Alternating exact 1-D
packing replaces the continuous field — first dense ACL win over stock
mm (3.32). Staircase readout halves seed mass; first irregular-dense
win, spin_glass −19% (3.34 — caveat s3.74: mm legalized only 2/3 seeds
there, so −19% compares a 3/3 mean against a 2-seed survivor mean plus
one feasibility win). **Diagonal alignment + insertion order
search: first search win over stock mm on K100 (P16-era testbed
protocol); adjacent swaps proven
plateau-bound; the crystal emerges from a topology-blind move** (3.35).
Init-independence becomes the standard.

**3.36–3.40 (the move set generalizes).** Best-insertion order sweeps
make block separation emerge from random init (3.36). Post-hoc wire
matching cannot reach the constructive optimum — geometry and wires
must be co-designed (3.37). Consolidation 1: one algorithm, rounds
deleted on dense (3.38). Constructive block structure only pays above a
patch-size threshold (3.39). Every cluster-aware rule replaced by
per-edge monotonization with leverage ∝ edge length (3.40). The
diagonal is demoted: sufficient, never necessary.

**3.41–3.47 (the pressure detour, and what killed it).** Excluded
volume leaks through arm growth (3.41). Differentiable capacity passes
its FD tests and fails its bars: a local penalty is gradient-blind
inside uniform overload — Gauss's law, measured three ways (3.42-44).
Place-the-edges (contact state) wins one liquid cell and loses the
representation war: corners-only dominates at 1/60th the state
(3.45-47). Gauge freedom is the optimizer's enemy.

**3.48–3.50 (the Zephyr reset).** **The adversary was wrong: busclique,
not minorminer, owns dense Zephyr** (template turán 6.00 vs mm 12.01 vs
ours 14.03) — the target becomes template-gap closure (3.48). The
adapter's j-fold was a representation ceiling (~2× template floor); κ
was miscalibrated 2× (3.49). The course unfold lifts quality AND
feasibility at once (K140 0/3 → 3/3) (3.50).

**3.51–3.53 (compaction and contraction).** Coloring acquitted
byte-identically; the residual is compaction — local rules cannot merge
distant clumps (3.51). **Contract before the first pack: cycle 0 is the
entire mechanism; first K100 win over mm on Z12** (3.52 — the s3.35
"first" was the earlier P16-era testbed protocol; different fabric and
protocol, both kept with their qualifiers). Discrete order
annealing helps only while overload is invisible (3.53).

**3.54–3.57 (validity by construction).** Exact seeds: coverage =
validity on junction-complete fabrics; the mm-skip gate fires and the
repair tax disappears (3.54). Off-template identity audit: the
exactness stack is graph-agnostic churn reduction, not dense overfit
(3.55). Snap: aim parity-exactly at claim time, extensions → 0; the
d729 defect was oversubscription, not misalignment (3.56). **Overload
priced into every gate: feasibility joins the energy; order-annealing
becomes unnecessary** (3.57).

**3.58–3.59 (consolidation 2 and the exact packer).** Deletion round:
zero-kwarg default beats stock mm on 12/14 cells; fabric-specific
mechanisms stride-gated (3.58). **Exact order-preserving DP under hard
integer pools + ONE shared census: K140 lands below the template quote;
the oversubscription class abolished structurally** (3.59). Cost:
depth-full packing trades the parity slack aiming needs — still open.

**3.60–3.61 (unblocks and diagnosis-first).** Four real defects found
and fixed in stock minorminer's restrict_chains (fork) — the domains
handoff unblocked (3.60). Phase-0 diagnosis overturned both defect
hypotheses; three light mechanisms instead of the heavy planned one;
first sub-template gate-valid clique (3.61).

**3.62–3.64 (the V-cycle).** Coarse level decides topology, fine
decides metric; the exactness gate fires on all dense cells including
ER (3.62). Spectral-of-the-coarse-graph heals sparse; five records; no
single span constant serves both regimes (3.63). The attribution
ladder: **the crystal is the OUTPUT shape — pre-committed member orders
pre-empt the moves that discover better ones; arithmetic sizes, rules
shape** (3.64).

**3.65–3.66 (self-critique and consolidation 3).** The exactness gate
had become the objective; bars rewritten in outcome units (final ACL,
max chain, feasibility, wall) (3.65). One accounting made literal;
Z12 board beats mm 7/7 **with max chain ≤ mm everywhere** — the ACL
wins are not bought with fatter tails; vcycle joins the stride gate
(3.66).

**3.67 (full sweep 3).** Harness hardened (the six hangs were a
worker-side queue starvation; fixed by JSONL-only accounting + hard
per-trial caps). Full library, both fabrics, 140,685 rows, zero
retries: **ACL −0.06 (P16) / −0.17 (Z12) paired vs stock mm;
feasibility ~2:1 in our favor; loss block = geometric lattices (both
fabrics) and dense Pegasus.** The lattice block becomes the target.

**3.68 (aggregation).** One clustering rule (leader aggregation to
fixpoint, sequential absorption) replaces twin-hash + matching round +
depth decree at measured parity; quotient protection emerges from the
weighted score. Validated candidate default. Discovered en route: the
vcycle is stride-gated (anatomy had claimed fabric-agnostic — fixed).

**3.69 (the adjoint round).** Merge and unpack are adjoint: decompress
by expanding coarse ORDERS with wire MASS, level by level. **Turán
lands the constructive optimum (6.00) from the general rule; the
lattice loss block falls (honeycomb −0.90, king −1.28). But faithful
transport of a noise order loses the expanders (regular +0.74) — with
junction energy IMPROVED: transmitting fiction pre-empts discovery.**
Transport parked per the pre-registered rule; the order-reality
discriminator is the open question. (See ideas.md §3.)

**3.70 (cluster moves — coarsen the moves, not the state).** Max
rejected size-guessing for coarse nodes outright; the replacement rule:
clusters are member SETS moved as one — gather/relocate proposed in rank
space on real members, judged by the same gates as every fine move.
Nothing summarized, no sizes exist. One cadence lesson (pre-pack passes
accept fictions — coarse moves fire after each projection) and one
refactor (the insertion composite generalized to any order proposal).
Probe: **BAR1 PASS — the s3.69 noise-transmission losses are eliminated
(regular ±0.00, sbm +0.00 vs transport's +0.74/+1.11) with zero
discriminator machinery**; turán 3-seed mean 6.52 vs stock 8.12 with
the tail killed (worst 6.80 vs 9.46; 1/3 seeds at the 6.00 optimum) —
the probe printed **BAR2 (≤6.5): FAIL** (`data/cmove_probe.log`); owner
call open. *(Corrected s3.74: this entry previously cited 10-seed
statistics — 6.535 vs 8.098, worst 7.00 vs 10.09, 4/10 at optimum,
"BAR2 missed by 0.035" — for which no artifact exists anywhere.)*
First Pegasus movement from coarse machinery (ws −0.32). Residual:
honeycomb at exact parity, grid +0.10 (inside probe tolerance; corrected
s3.74 from "grid/honeycomb stay at stock") — their adjoint wins lived in
the ordered INIT, which gating can't reproduce post-pack; the lattice fix
lives at init time; named open. Switch `cluster_moves`, fabric-agnostic.

**3.71 (generous merging — move units without thresholds).** The merge
criterion was inherited from the init job; under the move frame the risk
asymmetry inverts (over-merge = one rejected proposal; under-merge = an
inexpressible joint move). Change: move units from THRESHOLD-FREE
coarsening — greedy score-rank matching per round, iterate to fixpoint;
τ never consulted; every graph gets its natural log-depth hierarchy.
Two structural guards forced by measurement, neither a constant:
adjacency-only merging (distance-2 pairing made disconnected patches —
units must induce connected subgraphs, by induction; round-0 twin
classes exempt by nature) and one-composite-per-cluster (the pack
disperses what gather assembles on expanders — 289-composite
accept/perturb churn, zero ACL effect; repetition is the fine moves'
domain). Probe (16 cells + 10-seed turán): units win or tie every cell
**except king_graph_196 (+0.19)** — ER −0.20, spin_glass −0.24,
ws −0.08/P16 ws −0.30, honeycomb −0.14 (`data/units_probe.csv`).
Turán 10-seed 6.457 — but the in-probe τ control ALSO scored 6.457 with
per-seed byte-identical results: the units change was a no-op on turán,
and the apparent 6.53→6.46 gain over s3.70 was between-probe drift, not
the mechanism. Wall grew seconds on winning cells inside a 60 s budget,
and the probe printed **BAR1: FAIL** on its wall clause (the clause
mis-specified productive spend as waste; recorded). *(Corrected s3.74:
previously "win or tie EVERY cell … zero ACL regressions", with the
turán delta credited to units.)* BAR2's decisive branch fired: patch units exist and
barely move grid/honeycomb ⇒ **the lattice residual is init-time, not
move-time — the next round is the init.** Default ON (winners ship);
`cluster_units=False` = the τ control arm.

**3.72 (per-member affinity — right formula, wrong hierarchy; parked).**
Max's critique held: the twin hash was topology detection, adjacency-only
candidates overrode the score's own interpolation (justification
retracted as unmeasured), and the raw-total score misread size mismatch
as disagreement — 1:2 fragments of one twin family scored 1/2 (the
straggler artifact at its root). The repaired criterion compares AVERAGE
members: affinity = [Σ min(p_S,p_T) + μ + 1]/[Σ max + μ + 1] with
per-member profiles p and mutual pull μ; the +1 is one body per member
(regularizer only). Verified: fragments any ratio → 1; chains ½
(preserved); heavy mutual bundles switch from mostly-against to
purely-for. Build lesson: greedy maximal matching forces odd-count
leftovers into cross-block marriages (one 0.012 pairing snowballed to a
64/17 blob) — fixed constant-free by admissibility (merge only if it is
at least one endpoint's best available; leftovers wait, and per-member
scoring makes waiting free). **Probe verdict: BAR3 FAIL — turán 10-seed
6.71 vs s3.71's 6.46, optimum never reached; board slightly worse on
six structured cells.** Diagnosis: not the score — the hash-free deep
hierarchy emits nested FRAGMENT units whose one-shot gathers pre-empt
the full block gather (8–14 accepts doing worse than s3.71's single
clean one). Owner override (Max, 2026-08-07): the correct
criterion SHIPS anyway — wrong-but-working code does not stay default,
it lingers and poisons later sessions. The s3.71 engine (hash +
adjacency rule + raw-total score) is DELETED; the affinity engine is
the only units engine. The 0.25 turán delta is owned by the named open
question: unit SELECTION/ordering from deep hierarchies — the
criterion and the consumption are separate questions, and consumption
is the open one, to be fixed on the correct substrate.

**3.73 (the consumption round — both axes, strict descent, no schedule
rules).** The churn's engine was LATERAL acceptance: gather and pack
both accepted equal-energy states, so expanders circled plateaus paying
four evaluations per lap; strict descent for cluster composites makes
the energy itself the schedule, and the one-shot cap (a budget rule
wearing physics clothes) is deleted — unchanged re-asks no-op free at
the proxy. The y-only gather was an inherited asymmetry, not a design:
clusters now gather on both axes. Probe: **BAR1 pass with five real
wins, headlined by the first dense-Pegasus movement in program history
— P16 turán 8.54 → 7.94 (the 2-D gathers reach a fabric the exactness
stack never could)**; spin_glass −0.31, ws −0.13, honeycomb −0.15.
BAR2: turán/Z12 6.79 — unmoved (and 0.04 above even the pre-registered
blind-spot branch edge, recorded, not rounded). The isolation is now
clean and strong: fragment moves STRICTLY lower stair-E and worsen
routed chains — the gate energy is provably incomplete at that margin,
and no schedule can fix a lying judge. Named next: price the
claim-layer cost into cluster-composite scoring. Control branch
deleted; the schedule ships.

**3.74 (the audit purge, 2026-08-08).** Every quantitative claim in the
current notes was audited against the artifacts in `data/`,
`/data/max/fullember3/`, and the archive. The empirical spine held
(full-sweep 3, the fabric censuses, K140-below-template, history-inert,
course unfold — all reproduce to the digit), but a contaminated layer
concentrated in s3.70–s3.71 was purged in place, each site marked
"corrected s3.74": the s3.70 10-seed turán statistics had **no
artifact** (replaced by the 3-seed `cmove_probe` values; a real 10-seed
stock-vs-cluster_moves run is open); s3.71's "zero regressions" was
contradicted by its own CSV (king +0.19) and its turán credit was
between-probe drift (τ control byte-identical); decorative ranges
("30–60%", "85–95%") were widened back to their own tables; "max chain
no worse" was rescoped from the sweep (which recorded no max-chain
column) to the 7-cell board that measured it. Re-deriving fabrics
§4.4's unlogged constants (`data/template_quotes_z12.py`) confirmed
three of four exactly (K162 12.00, K184 13.00, K_{80,80} 5.50) and
caught one wrong-as-stated: busclique's biclique constructor gives
K_{81,81} ACL **11.00**, not "exactly 6.0" — the true 6.00 quote comes
from the K162-restriction route (`data/zephyr_triad.log`), i.e. the
sharpness fact was real but its attribution was not. Lessons that stand, in
place of doctrine: a number enters these notes only with an artifact
path; never splice an X→Y delta from two different runs (stock
baselines drift — mm K100 ranged 10.28–13.62 across protocols); cells
that fail in ALL arms must be listed, not dropped (sbm_600, ws_804,
P16 sbm_288); n=3 cannot support a ±0.1 verdict. Probe-reading warning:
`units_probe.py`'s printed [ok]/[REGRESS] tags are unreliable — the
wall clause marks ACL winners REGRESS and the 0.3 tolerance marked the
king regression ok; read the CSVs, not the tags. `data/` and `archive/`
are historical records and were not edited.

**3.75 (ball polish — the round the judge went real).** The move
minorminer's one-chain audition cannot express, built standalone
(`ball.py::ball_polish`): evict the WHOLE chains of a small variable set
(affinity-hierarchy units + tile-window sets), rebuild them jointly
against the frozen rest (frozen chains = forbidden fabric, edges to them
= attachment targets), accept the composite iff total real chain length
strictly drops, verifier backstop. No proxy energy exists anywhere in
the loop — the s3.73 lying-judge class is structurally absent, and
nothing needs junction completeness, so it is the program's first
fabric-agnostic mechanism by construction. Probe
(`data/ball_probe.csv`): 13 cells × {stock mm, attract} finished
embeddings × 3 seeds; 30 s of ball vs 30 s of warm-started stock grind
on the SAME embedding. **Ball wins 17/26 cells (worst loss +0.11);
stock-input headliners turán −1.45, K140 −0.58, spin_glass −0.53 vs a
grind that is at its own fixpoint in <1 s and occasionally returns worse
than its input; first dense-Pegasus wins from an ungated mechanism (K100
P16 −0.33/−0.19).** Two informative negatives: lattices barely move
(grid 1.41→1.385; stock inputs already at floor) — the lattice residual
is confirmed ORDER-level; local re-layout cannot reach it — and P16
turán accepted zero balls in both arms (uniform-price router rebuilds
cannot match near-straight incumbents on 56% junctions: the rebuild
primitive, not the move class). Rider probe, `contract_stable`
(energy-plateau stopping for contraction, cap W+H, un-gated on stride-1;
`data/cstable_probe.csv`): **REFUTED as a default, decisive as a
measurement — the plateau NEVER fires on Z12 (every cell ran to the
cap): stair-E descends monotonically toward collapse, so no internal
energy signal can honestly stop the continuous phase; the step count IS
the repulsion, now measured.** 50 steps beat 16 on turán (6.78→6.25, a
3-seed record) and spin_glass (−0.22) while losing K100 (+0.28), and
un-gated contraction still hurts dense P16 (+0.42/+0.19) even under the
honest rule. Course set by Max on the round's evidence: the sparse
geometric cells are the named target, and the continuous state is to be
REMOVED, not re-knobbed — state wants to be two orders plus lanes, with
init demoted to a pure order-generator. ball_polish is a validated
candidate, not yet wired into the pipeline; its stage-1 is sharing the
bar constructor as the rebuild primitive (one way to build a chain, not
two).

**3.76 (the order state — v4 stage O1).** The continuous carrier
removed in one switch (`order_state`): init points reduce to per-axis
RANKS (sort keys only), no contraction phase exists, the DP packs with
the TRUE stair objective — which is LINEAR given the orders
(`_axis_coeffs`: E_axis = Σ c_v·pos_v for any order-preserving
assignment, c_v = nets topped − nets bottomed) — and the packer +
overload gate run on every fabric; positions are thereafter always
derived line indices (invariant-tested). One real defect caught by the
first run and fixed before the rerun: on the no-snap path zero-width
arms were invisible to the census (`line_depth` treats point intervals
as disjoint), so the true-objective DP collapsed the whole placement
onto one line for free (P16 E=0.0, turán 7.9→13.1); the fix is the bar
picture taken literally — an occupancy footprint (width-floor b=a+1) in
the order-mode books; no-op under snap, which is why Zephyr was immune.
Probe (`data/order_probe2.csv`; the collapsed first run kept as
`data/order_probe.csv`): **turán/Z12 6.023 at 10 seeds (max chain
8→6.1) — essentially the 6.00 constructive optimum as a structural
property, the number three rounds chased; the lattice block falls
(honeycomb 1.81→1.09, king 2.36→1.53 — both now BELOW stock mm's level;
grid 1.41→1.12 vs stock's ~1.08); spin_glass −0.60, K140 −0.29; and the
largest Pegasus movement in program history from the fabric-agnostic
bundle: P16 K100 13.33→11.46 (max 20→16.7), P16 turán 7.94→7.65, P16
ws 3.80→3.33.** Max chain improves nearly everywhere. Losses, all
Z12 expanders/near-noise: regular +0.16, ws +0.40, K100 +0.05, ER
+0.01 — the no-order-to-exploit regime, consistent with the regime map.
Deleting the vestigial organ did not lose contraction's covert order
search; the honest readout replaced it and moved BOTH named residuals
(lattice init, dense Pegasus) in one flip. **Default FLIPPED (Max,
2026-08-08): "there's solid reasoning behind it and it wins. it should
be the default even if it lost, because that would just mean the error
is somewhere else."** `order_state=False` remains as the
continuous-carrier control arm; the stride gate narrows to
exact_seeds/snap only (the packer and gate are state properties now).
Named next on the expander/ER toll: Max's variance observation — an ER
graph is not order-free; fluctuation makes some nodes more alike than
uniform, so there IS an order to find, just not a spectral one (see
ideas §3).

**3.77 (the simple-and-fast round).** Three directives (Max): dirty
fast init, slim the state-enabled complexity, bar-based ball rebuild.
Speed, honestly: the planned pack_lines feasibility rewrite was benched
and **REFUTED** (dense 6→6 ms, sparse 21→17 at n=486 — never the
bottleneck; reverted same-day, property test kept). Profiling found the
real sink: `arm_books` computed contacts twice per gate evaluation;
fixed by y-order-invariant reuse (safe sites only — axis-1 mutations
recompute, since a line-collapse can flip the (y,id) tie-break),
byte-identical, ~2 s/embed returned to the move budget. **Ball v2**
(`data/ballbar_probe.csv`): bar rebuild through the pipeline's own
claim machinery (`require_free` coloring, `only=`-scoped completion;
also fixed a live bug — ball's grid was built courses=False, folded
wires). Verdict: **bars+fallback ≥ router on every cell** (turán 10.83
vs 10.92, king 1.69 vs 1.71, rest ties) and ships as the default arm;
**bars-only REFUTED standalone** (near-zero accepts off turán; stride-1
corners are a ~56% junction coin without completion) — `sph_tree`
remains load-bearing; the one-constructor unification is partial, not
total. **Hier init REFUTED as built** (`data/hier_probe.csv`): the
ER-variance thesis cells moved the WRONG way — ER +0.23 (diagonal arm
+1.21), regular +1.07, ws +0.36, king +0.74, honeycomb +0.10, all
three P16 cells up — only the crystal regime at/below parity (turán
exactly 6.000 on 10/10 seeds, its first all-seed optimum). Reading:
the affinity hierarchy is the right MOVE-UNIT generator and the wrong
ORDER generator for liquids — a dendrogram linearization seats
variance clusters together but destroys the 2-D geometry that spectral
ranks carry; the variance thesis itself stays open, this mechanism for
it is parked. Spectral-ranks init remains default; consolidation 4
rescoped — the vcycle/disc path SURVIVES (it feeds the winning init),
and the continuous-arm deletion waits for its own round.

**3.78 (the offsets probe — a pre-registered prediction refuted).**
Which property of the golden-angle sunflower does the rank-flattening
need? Three child-offset generators inside the unchanged disc expansion
(`data/offsets_probe.csv`; spiral = even + decorrelated, random =
decorrelated + clumpy, grid = even + axis-aligned). Predicted (recorded
before the run): grid worst, spiral >= random. **Both wrong.** Grid is
NOT worst — it wins or ties most cells (regular 2.72 vs spiral 2.85,
spin_glass 11.23 vs 11.42, K100 7.72 vs 7.84) — and random beats spiral
on several (ws −0.30, ER −0.17). Nearly all deltas sit inside the n=3
noise band (spiral's own ws reading drifted 3.04→3.21 across probes).
The one trustworthy signal is turán at 10 seeds: spiral 6.023, grid
6.091, random 6.344 — on the giant-twin-block cell (two blocks of 81),
EVENNESS matters (clumpy random pays +0.32) and axis-alignment does
not. Conclusion: the decorrelation/irrationality story is refuted as
load-bearing; the arrange machinery erases within-cluster offset
structure on ordinary cells, and the only cargo is coarse geometry +
membership (+ evenness on giant blocks). The golden angle is
ornamentation — purge-eligible: any even generator serves. The spiral
stays for now only because three lines that work need no replacement
until the disc path's own consolidation.

**3.79 (consolidation 4 — one code path, and the anatomy rewritten).**
Purge to the winner configuration (archive commit `d8274198`): deleted
the continuous control arm (contraction, CONTRACT_STEPS, eta,
contract_stable, the order_state switch itself), the greedy packer,
the order_mode/use_dp flags (true-objective DP + full census are now
unconditional), the folded-courses arm, hier_orders/_rcm (s3.77),
init_offsets (s3.78), vcycle_transport/unpack_transport (superseded —
its lattice claim is solved by the order state, s3.76), and ball's
rebuild knob (bars+fallback hardcoded). AttractConfig 20→12 fields;
−819/+152 lines; default byte-identical on all three fabrics; 578
tests green. anatomy.md rewritten from the purged code in plain
language (what/how/why per stage) as the substrate for the owner's
question pass.

**3.80 (the tail round — ball wired in; the ordering bet refuted).**
ball_polish is now a pipeline stage (`tail=` in {"mm", "ball+mm",
"ball"}; one-sweep structural cap on the tail ball after the smoke
showed fixpoint-chasing starving the grind on lattices). Probe at equal
TOTAL budget (`data/tail_probe.csv`): **ball-BEFORE-grind does not
clear the bar** — wins on ER −0.33, K100 −0.06/P16 −0.05, spin_glass
−0.06, grid −0.01, but turán +0.59 at 10 seeds (max chain 6.1→7.6) and
ws +0.87 (max chain 11→22). Mechanism, read off the arms: ball-only ≈
ball+mm on the losing cells — ball's greedy neighborhood descent moves
the pre-polish embedding into basins the grind cannot escape (from the
raw state the grind reaches 6.02 on turán; from the ball state it goes
nowhere). The free-polish doctrine (s3.22) generalizes: nothing may
constrain the polish's basin, including a smarter polisher run first.
Joint reading with s3.75 (ball ON grind output: 17/26 wins, never
harmful): **the ladder runs coarse→fine→coarse — clusters teleport,
grind polishes chains, ball harvests LAST what the grind cannot see.**
No default flip (bar failed by rule); `tail` stays as the measured
platform; the named next arm is "mm+ball" (grind first, ball after,
equal budget), which both prior datasets support. Also banked: on
gate-fired dense Zephyr, tail="ball" ties the board with minorminer
absent end to end — the minorminer-free Zephyr pipeline exists and
costs nothing on crystals (turán 6.616 vs 6.612 ball+mm; the gap to
6.02 is the grind's basin work, not legalization).

**3.81 (mm+ball ships — the ladder is coarse→fine→coarse).** The
reordered tail at equal total budget (`data/tail_probe2.csv`): **wins
or ties EVERY cell, zero regressions** — ws −0.35 (max chain 11→9.3),
P16 ws −0.22, ER −0.17, regular −0.06, K100 −0.05/P16 −0.03 (max
16.7→15.7), spin_glass −0.05; ties on the gate-fired crystals (ball
finds nothing after the grind there — the grind's basin work is
complete) and the lattices. Max chain never worse. DEFAULT FLIPPED:
`tail="mm+ball"`. Max's pre-run read stands: it IS weird that this
works — the grind owns something we lack, and the s3.80/s3.81 pair
names it precisely: cheap stochastic plateau diffusion (order
reshuffled per pass, randomized ties/roots, hundreds of near-no-op
passes) that strict descent deliberately excludes. Ball before the
grind traps its basin; ball after harvests what single-chain vision
cannot see. Named open (the replacement brainstorm): give OUR side a
stochasticity source — keep-best kicks on ball composites, or
top-level seeded diversity (distinct from the s3.16-killed best-of-N:
no legal-stage proxy involved) — so the sandwich's middle can go.

**3.82 (re-asked descent — REFUTED by its own mechanism check).** mm's
two named stochasticity channels (per-pass order reshuffle, uniform
ties) replicated at ball scale with strict acceptance untouched
(`tail="ball-rng"`; rng=None byte-identical). Probe
(`data/tail_probe3.csv`, turán AND ws at 10 seeds): **ball-rng ≈
deterministic ball everywhere** (turán 6.633 vs 6.612, ws 4.141 vs
4.126; only the lattices moved slightly, grid 1.44→1.35), and nowhere
near mm+ball (turán 6.02, ws 2.76). The pre-registered check fired:
re-asking is NOT minorminer's mechanism — or not sufficient. The
sharpened reading: mm's diffusion runs over a COMPLETE, RELOCATING
proposal family (any single chain, rebuilt anywhere in free fabric,
every pass), while ball re-asks a small FIXED question set (units +
windows, computed once, rebuilt in-place near their old footprint).
Randomizing the ties of a confined family explores the confinement.
What mm still owns is now named more precisely: not randomness per se
but randomized interrogation × global relocation freedom at single-
chain granularity. Named next candidates: relocating ball rebuilds
(drop the in-place footprint restriction), per-chain re-ask (our own
grind: mm's move at mm's granularity under our books), or regenerating
the ball question set from the CURRENT embedding each pass (the fixed
candidate list is itself a frozen die). No flip; the sandwich stays.

**3.83 (ball v3 — completeness achieved, and the askability
hypothesis refuted by it).** The selector rebuilt constant-free: one
question per chain from its obligation hull, regenerated every pass
(`data/tail_probe4.csv`; unit balls, windows, caps, floor, inflation
all deleted; clique self-gating verified in-test and in-probe — dense
cells tie all arms at zero ball cost). The ladder prediction FAILED
again, decisively: ball-first still wrecks the liquid cells (ws +1.68
with max chain 10→22, regular +1.38, ER +1.13, P16 ws +1.54 with max
13.7→31.7) even though the fat-chain repair question now provably
exists every pass. So the s3.80 diagnosis ("the damage was unaskable")
is refuted: asking is not answering — a sum-optimal state containing a
blighted chain admits no sum-improving rebuild that removes it, so
strict sum descent ratchets into blight regardless of question
completeness. Max's geometry instinct sharpens into a measured fact:
the damage is OBJECTIVE-level, not move-level. The move-strategy-first
路 was tried per the owner's preference and measured insufficient;
what remains is the acceptance/objective question we deferred (how to
price or forbid blight without max/average dogma), or accepting the
sandwich (mm+ball, still the unbeaten default — all v3 arms ≤ it
nowhere, and ball-after gains no new ground from richer questions).
Also banked: pure ball ties the sandwich on every gate-fired crystal
at zero cost — the minorminer-free Zephyr pipeline remains real
exactly where construction already owns the answer.

**3.84 (the 2x2 closes in — slack refuted, one cell left).** The
hypothesis-(b) discriminator (`data/tail_probe5.csv`): our native
deterministic per-chain shortener where the grind sits (shorten+ball,
no minorminer post-gate) lands at PURE-BALL levels, not sandwich
levels — turán 6.63 vs 6.02, ws 4.18 vs 3.07, regular 4.08 vs 2.85,
max chains ballooned identically. **Slack removal is refuted as the
grind's role.** The elimination is now a clean factorial {chain, ball}
x {deterministic, randomized}: ball-det (s3.81), ball-rng (s3.82), and
chain-det (s3.84) all fail equally; minorminer occupies the one
untested cell — per-chain granularity x randomized interrogation,
JOINTLY. Built: `tail="rshorten+ball"` (shorten_chains with mm's
channels: per-sweep order shuffle, rng root ties, patience 2,
unbounded sweeps under the deadline). Probe verdict
(`data/tail_probe6.csv`): **FAILED — the fourth cell does not
reproduce minorminer either** (turán 6.64, ws 4.24, regular 4.04 — all
at the same non-mm plateau as every other arm; crystals tie as
always). The factorial is complete and every named factor is
eliminated, jointly and severally: granularity, randomization, slack,
askability, staleness, scale. What our reconstruction of mm's move
never included, and mm-internals documented all along: the
**exhaustive audition** — find_short_chain CONSTRUCTS the full chain
at EVERY candidate root (each qubit reached by all neighbour balls)
and keeps the measured best, hundreds of built-and-measured candidates
per chain per pass, where our sph_tree picks ONE root and builds once.
Not randomness, not granularity: per-move candidate breadth. The
audition is the last unnamed mechanism standing and the next
discriminator when the owner returns. Alternatively the wrongness is
upstream (Max's (b), still live at pipeline level: all these arms
polish the SAME seeds — only the sandwich's mm ever re-legalizes).

**3.85 (the lane audit — the polish phase is exonerated).** Member
placement by measured cost over candidate lanes (mm's audition over the
bar family, O(hull lines) arithmetic; kappa widening fell out as dead
code). Probe (`data/tail_probe7.csv`): **the plateau survives exact
selection too** — audited ball 6.65/4.62 (turán/ws), audited ball-rng
6.65/4.48, sandwich 6.02/2.95. rng-over-exact helps lattices modestly
(grid 1.39 vs 1.63, king 1.76 vs 2.01) but breaks nothing. Banked: the
audit makes crystal no-ops near-instant (K100 ball wall 31s→1.3s —
exact selection dries immediately). Seven probes have now eliminated
EVERY move-level factor: granularity, randomness, their product,
slack, askability, staleness, scale, per-candidate exactness. The
polish phase looked exonerated, and a "validity corridor" hypothesis
was briefly recorded here — **CORRECTED the same day by Max against
mm-internals (the house rule applied to our own claim): REFUTED BY
SOURCE before costing a probe.** find_short_chain expands through FREE
qubits only; the shipped overlap cost is lexicographically infinite;
warm-started on a legal embedding the overfill passes no-op — the
sandwich's minorminer never leaves legal space. What the correction
exposes instead: the elimination factorial had a THIRD axis we only
sampled — the audition. probe6's rshorten was chain-granularity × rng
WITHOUT the audition (one sph build per chain per sweep); probe7's
audit was audition × rng at BALL/bar level, never per-chain Steiner
breadth. mm's actual move — chain granularity × rng × the full Steiner
audition (construct at every mutually-reached root, radius order,
first strict improvement) — has never been replicated. That cell,
find_short_chain ported natively, is the last constructible
discriminator: reproduce the sandwich and the mechanism is named and
owned (minorminer exits); fail and the polish phase truly is
exonerated, leaving the seeds alone.

**3.86 (the autopsy — the seeds are guilty, measured).** Distribution
tables only (`data/grind_autopsy.csv`), raw pre-tail seeds
(tail="none") vs 30 s warm grind. The headline is upstream, exactly as
Max hypothesized: **the raw liquid seeds contain monster chains — ws
max chain 46 (grind → 11), regular 22 (→ 6), grid 10 (→ 3) — and the
grind does not polish them, it RE-EMBEDS them wholesale**: ws
2422/2430 chains changed, regular 948/948, grid 590/600;
displacements >3 tiles dominate. Second finding, the capability gap
made visible: on ws, 631 of 2422 changed chains GREW — the grind
performs net-negative REDISTRIBUTION, trading length between chains —
an operation forbidden by construction in every arm we built (per-
chain strict descent cannot grow anything; sum-strict balls buy blight
when they try). Turán's autopsy shows the crystal version: only
150/810 rows changed, L→straight-run conversions at >3-tile
displacement — the grind straightens what the seeds mis-bent. Verdict:
seven tail probes measured the wrong phase. The blight is BORN in the
seeds — the placement/coloring/completion stack emits massively
imbalanced chains on liquids — and minorminer's seat in the middle is
explained: it is the only component capable of re-embedding from a bad
start (legalizer-grade rebuilding), which no polish of ours was ever
meant to do. The question for the anatomy pass is now precise: WHICH
stage births the 46-chain on ws — the arrange compaction, the kappa
floor, the coloring, or completion's extensions. Fix the seeds and
every tail experiment this week predicts the sandwich collapses on its
own.

**3.87 (the fold — the mystery resolves, and the L is exonerated).**
Measured on ws seed 0 (edge-span distributions, endpoint-chain tile
distance): raw seeds carry 16 edges spanning >10 tiles (the WS
shortcuts; max 11.8); **after the warm grind, ZERO remain — all 16
collapse to mean 3.9, max 7.3.** minorminer does not pay the shortcut
tax with cleverer shapes; it MOVES the endpoints together. Combined
with the s3.86 autopsy (every chain touched, displacements >3 tiles,
cascade 1.0, redistribution with growth): the grind's irreplaceable
contribution is **the fold** — gradual global re-layout via hundreds
of small, strictly-improving, RELOCATING per-chain moves, each locally
trivial, jointly folding the placement so order-irreducible long edges
stop being long. This path exists only at chain granularity: the
intermediate states of a fold are net-negative as single jumps, so
every big-move arm of ours (composites, balls, one-shot rebuilds)
correctly rejects them, and our per-chain arms never relocated. The
week's seven refutations close coherently: not shapes (the bar-family
pricing claim of s3.86-era is RETRACTED — third self-correction of the
arc), not randomness, not audition breadth, not the seeds' books — the
gap is a move class: small relocating strict-descent steps whose
composition is a global fold. Candidate responses for the owner:
(a) chain-granularity relocating polish (rebuild-toward-current-
neighbours, iterated — mm's real mechanism, natively ownable);
(b) fold-aware init sketch (the spectral circle leaves the fabric
interior EMPTY on ring-like graphs; a stress layout folds chords at
init — but s3.77 counsels humility on init cleverness); (c) an arrange
move that relocates arcs across the net-negative ridge. The regime map
gains a mechanism: liquids lose exactly where layouts need folding.

**3.88 (every move real — the warm sketch earns its keep, with one
beautiful exception).** init_mode="trivial" (identity ranks, no
summary physics; `data/fold_probe.csv`; stage walls now permanent
diag). Verdict = pre-registered (c) with structure: **the sketch pays
its way exactly where geometry exists to sketch** — lattices, liquids,
Pegasus all regress from a dumb start (regular +0.67, king +0.59, P16
K100 +0.74, ws +0.18) — while on crystals the summary physics was
NOISE: **trivial hits turán's exact 6.000 optimum on 10/10 seeds,
beating the sketch's 6.023**, and K100 improves −0.12 with max 9→8.
The crystal is the output shape, purely (s3.64 at its strongest: the
best dense init is NO init). The ws fold did not happen from the dumb
start either — real-judged moves cannot fold from any origin, so the
single-arc +D barrier holds at every scale we possess, and the
tile-resolution corridor / telescoping multi-arc composites (ideas §3)
are confirmed as the genuine frontier, to be DISCUSSED before built
(Max's rule). Cost accounting: init_wall is negligible (<0.1 s) at
benchmark sizes — the sketch is effectively free, so keeping it costs
nothing; the trivial arm's losses are pure move-budget spent
recovering what the sketch hands over. Standing default unchanged;
candidate cheap flip for a future round: trivial init on gate-fired
dense cells only — rejected as stated (graph-type rule); the general
version (sketch-vs-trivial as measured per-instance restart arms)
belongs to a portfolio discussion we have always refused. Park.

**3.89 (the orientation bit, the two-axis fold, and the strain agenda —
the fold barrier finally moves).** Design discussed with Max 2026-08-13
(the ideas §3 "DISCUSSED before built" marker): the move family was
translations-only — monotonize (transposition), insertion (singleton
relocation), gather (block relocation, internal order DERIVED) — and a
reversal cannot be composed from translations under strict descent, so
the fold was unreachable by construction. Three switches
(`data/strain_probe.py`, cumulative arms, 10 seeds on the deciding
cells, load caveat: box load rose 30→58 through the run, later arms
disadvantaged):

- **`gather_orient` — SHIPPED, DEFAULT ON.** Every gather offers its
  reversed block; the E-gate picks (ideas §2.11 honored: the derived
  order is a candidate, not a commitment). ws −0.113/max −0.6 (10
  seeds), grid −0.090 (the lattice residual moves), honeycomb/king/
  regular won, dense parity, zero regressions, zero wall cost. One
  line of mechanism (`block[::-1]` competes in the screen).
- **`fold_moves` — VALIDATED ON TARGET, OFF pending the Pegasus
  defect.** Two findings en route, both measured in-session: (1) the
  ONE-AXIS rank-interval reversal is NOT the fold — it preserves the
  axis's value multiset, so both strands land on the same wires
  (194/194 overload-vetoed) and in rank terms it trades the chord's
  span to the seam edge, net zero. The fold is irreducibly two-axis:
  riffle the [u..v] interval on the strand axis (partners on adjacent
  slots), split the interval's own value multiset on the other axis
  (strands on different lines). (2) The s3.61 overload ratchet guards
  feasibility ONCE ATTAINED; applied to still-infeasible mid-arrange
  states it blocked E 57k→12k drops over +250 overload (fold_trace) —
  the fold composite relaxes it while ov_pre > 0, absolute once
  colorable. Cadence: eager folding starved the ordinary moves (~150
  composites ate the placement budget, acl WORSE despite 9 accepts);
  shipped shape is ONE executed composite per pass, lazily screened
  down the span×merge-round ranking, rejections memoized by geometry.
  Result: ws/Z12 2.998→2.814 with max 10.4→9.4, ws/P16 −0.271 with
  max 13.3→11.7 — the first mechanism to move the fold residual on
  both fabrics. Defect that holds it: on P16 K100 the accepted folds
  (2/3, all seeds) are stair-E fictions on 56% junctions — +1.05 acl,
  max 16.7→18. The Pegasus exactness gap surfacing inside a new
  mechanism; the fold pass needs a coupler-aware judge there (or the
  general fix, ideas §3 "Pegasus").
- **`strain_rank` — REFUTED as built.** Executing cluster composites
  in descending proxy-gain order (the screen's own e0−best_e, priced
  over both orientations) instead of coarsest-first: adds nothing over
  the fold arm on any cell beyond noise; ER +0.084, spin_glass +0.104,
  king +0.029, P16 ws +0.4-vs-fold (all with the load caveat). The
  estimate-schedules-gates-decide principle survives — the RANKING was
  not the bottleneck at these move volumes; coarsest-first was already
  a good-enough schedule once the moves themselves are right. Lever
  kept off for one round pending discussion; purge candidate.

Also banked: per-edge merge rounds (the filtration as a free
structural-range measure) ride the existing membership composition;
`max_edge_span` is a first-class diag (the s3.87 statistic, live in
every run); fold counters + fold_trace in diag. The spin_glass wall
"failure" in the probe bar is load noise (fold arm: 0 accepts, exact
reverts, identical layouts, arrange_wall ≈ default; the +13 s totals
track the box load ramp).

**3.90 (crossfinder — THE move built standalone; the capability
envelope measured, and overlap identified as mm's load-bearing
feature).** Paradigm thesis (discussed 2026-08-13): every winning move
is evict-a-subset-and-re-place-against-the-frozen-rest; build that as
the whole algorithm at cross granularity — mm's own loop shape
(mm-internals: the dominant phase IS rip + ball-intersection
candidates + exhaustive audition) with the fabric's native chain
shape and an exact O(deg)-per-anchor audition attacking mm's measured
90% slice. Built: `cross.py` / `crossfinder_embed` / registered
`"crossfinder"`; state = real claimed chains (judge-real, no proxy
anywhere), operator = score all ~W×H anchors by interval arithmetic
(per-neighbour h/v coverage choice, hull cost, lexicographic
deficit-first pricing), realize ranked anchors via the frozen-aware
lane audit + scoped completion + scoped verify, sph_tree fallback;
passes = strict-coverage BFS init → legalize (rip + re-place) →
worst-first shorten → optional hull-window evictions (`rip_windows`).
Attraction pipeline untouched.

Measured envelope (Z12, 60 s, seed 0): **sparse structured is a
clean win on wall** — cycle400 ACL 1.042 legal in 4.3 s, grid 14×14
1.816 in 2.6 s, small graphs instant — but **liquids and dense do not
legalize**: ws_n486 stuck at 143/972 uncovered edges (down 395 → 238 →
143 across three legalization designs: deficit-deferral, strict init +
interval blocker rips, eviction-priced lanes — each helped, none
converged), K100 catastrophic (2850/4950). The diagnosis is
structural, twofold: (1) **a straight cross cannot route around
occupied bands** — its hull necessarily spans the crowded region its
targets live in, so a fully-free straight run is exponentially rare
at load, and (2) **exclusive claims delete mm's actual load-bearing
legalization feature: overlap** — mm's chains coexist on qubits at
lexicographically-hard occupancy prices and the overfill is squeezed
afterwards; rip-based negotiation without escalating prices cycles
(A evicts B evicts A). The named endpoint, to be DISCUSSED before
built (Max's rule): occupancy-priced overlap in the claim model
(claims as multisets + a pushdown/squeeze phase) — mm's §4 pricing
transplanted, at cross granularity. No probe was run: the deciding
cells fail at legalize, so a board probe would only record that fact
at 24 workers. Tests pin the working envelope
(`test_crossfinder.py`); the prototype's per-variable exact
re-placement operator (`_place_cross`) and eviction-priced audit
(`_audit_claim_evict`) are the reusable artifacts either way — the
operator is exactly the "single-variable ball" that s3.75's selector
structurally excluded.

**3.91 (kill-the-grinder — REFUTED for now, with the map and the
reasons).** Ball-prime = ball_polish + the |S|=1 exact-cross question
(`cross._place_cross` via `ball_singles`; profiled 1.2 ms/question —
the singles were never the cost). Probe (`data/grind_probe.csv`, 4
arms, load-ramp caveat again): **the grind is dead weight on dense**
— K100/K140/spin_glass tie grind-free at 6-20x wall speedup (K100
7.84 in 1.1 s vs ~20 s) — **and irreplaceable everywhere else**:
turán +0.61 (the grind polishes crystal seeds 6.65→6.05; ball
cannot), ws +1.31/max 10→21, ER +1.02, regular +1.31, lattices
+0.2-0.5. Singles beat plain ball consistently but marginally (ER
−0.11, ws −0.12, grid −0.01). Two named reasons the no-grind arms
lose: (1) on sparse cells the tail polishes MM'S OWN CONSTRUCTION
(seeds discarded or mm-legalized) — the grind is continuous with it;
(2) ball's fallback router is the wall hog: `sph_tree`'s
weighted_multisource_dijkstra at 41 ms/tree, 14.2 of 15 profiled
seconds — exactly the heap mm-internals says a native shortener must
not use. Ball-prime stays a lever (`ball_singles`, off). Caveat: all
sparse rows measured the PRE-s3.92 broken arrange; re-measure after.

**3.92 (the pack_lines repairs — Max-directed diagnosis: "something
in there is janky and I don't think it needs an experiment").**
Profiled on ws: arrange ran 1 of 8 iterations (~18-20 s each) and
permanently dropped 69/486 variables. Two defects: (1) **stragglers**
— a variable the DP cannot fit keeps its OLD position, at init a rank
coordinate (≤485 on a 25-line fabric); its hulls then stay enormous
so it never fits again — 69 permanent ghosts, E inflated 14x, cluster
churn on phantom proxy gains, seeds worthless. Fixed: `clamp_miss`
(default ON) clamps misses to the nearest real line — the census then
sees localized real pressure and the hulls shrink to packable.
(2) **the feasibility pass re-sorted the whole window at every
two-pointer step** — 412k line_depth calls / 14M comparator lambdas
per ws run; the docstring's "one two-pointer pass" was aspirational.
Fixed: incremental lazy max-segment-tree over compressed endpoints,
byte-identical jstar (equivalence-tested on 200 randomized instances
incl. rank-scale stragglers; no probe arm needed). Smoke: dense inert
(K100/turán byte-identical); ws completion deficits 141→97 with
cluster accepts 23→48 — but final ws ACL is NOISE because of the
discovery underneath: **on ws the pipeline discards its seeds
entirely** — arrange exhausts the placement half, `cap <= 0` skips
seed legalization, and the FALLBACK runs stock mm from single-qubit
nearest-tile hints. 30 s of arrange currently buys position hints,
nothing more, on exactly the liquid cells. The named next repair (to
discuss): when `cap <= 0`, submit the completed seeds warm to the
fallback instead of single-qubit hints — the seeds cover ~90% of
edges (97/972 deficits); discarding them is a bug-shaped decision,
not a doctrine. Probe verdict (`data/pack_probe.csv`, clamp
single-flip): dense + ER byte-identical (clamp inert, as predicted);
on every cell where misses exist the clamp arm is consistently but
sub-tolerance WORSE on final ACL (ws +0.123 at 10 seeds, P16 ws
+0.268, regular +0.086; all < tol 0.3) — exactly the pre-registered
hint-noise mechanism: the improved seeds are DISCARDED on those
cells, so the clamp's only reachable effect is different fallback
hints. The clamp stays default per the pre-registered rule, but the
verdict couples the two repairs: the clamp's value (deficits 141→97)
is unrealizable until seeds are submitted — the discard fix is the
unlock, not an independent nicety.
Also banked: the sparse-cell membrane is tiny where seeds ARE
submitted — ER 1 deficit edge, regular 19, grid 29 — mm's negotiation
summoned to patch ONE edge on ER; the negotiated-completion design
(eviction audit at claim time, before the validity ratchet) is the
named legalizer attack there.

**3.93 (the infinite Zephyr packer — the liquid residual falls).**
Root cause named by Max: even when the optimum fits, the INITIAL
layout can demand more fabric than exists, and the bounded DP's only
recourse was dropping variables. Design settled in discussion: keep
lane capacity HARD (the only honest anti-collapse force — the
isotonic/PAV idea died against Max's "what else could possibly
prevent collapse"), drop the LINE-COUNT bound (the only reason skips
ever fired; with unbounded uniform lines, hard-capacity packing is
always feasible by the L_max lemma), let the CENSUS alone carry the
finite fabric (verified: `claim_overload` already prices unknown
lines at pool 0 — out-of-window mass was priced by shipped machinery
all along), and project once into the real window at the end. Clean-
topology separation: the DP now packs the ideal crossbar; Zephyr's
finiteness/boundaries live in census + claim adapter only. One
measured correction en route: canonical translation must anchor at
line 1, not 0 (line 0 is a boundary line; anchoring there broke
turán's exactness 6.00→6.70).

Verdict (`data/unb_probe.csv`, 2x2 with submit_seeds, 10 seeds on
deciders): **`unbounded_pack` SHIPS, DEFAULT ON. ws/Z12 3.037→2.552
with max chain 10.7→8.1 — the first sub-minorminer liquid result in
program history (stock band 2.82-3.23 / mx 11-13), at 10 seeds, both
metrics at once.** ws/P16 −0.461 (mx 14→12) unprompted; turán exact
6.000 on 10/10 (beats default's 6.046); regular −0.075; dense
byte-identical; costs: king +0.237 (within tol, the one real
regression — open item), honeycomb +0.027 with a wall flag at load
~40. The new observables tell the story: ideal widths turán 12×12,
grid 9×9, K100 13×13, ws 22-25×25 — ws genuinely wants nearly the
whole chip, which is WHY the bounded packer choked on it; the
algorithm now reports fabric demand per instance instead of gambling
at projection. **`submit_seeds` REFUTED** (no effect anywhere; ws
+0.043 — consistent with mm-internals "legal-stage ACL carries no
information"); lever kept off. Fallout: the s3.92 clamp is dead code
on typed grids under the new default (guards only the final
projection); the s3.91 grind question and the fold/orient levers
deserve re-measurement on top of the new baseline — several
residuals (fold, seed-discard, stragglers) were downstream of the
one deleted constraint.

**3.94 (grind re-measure on the s3.93 baseline — the grinder's
territory is real, not a packer artifact).** Same four arms as s3.91
(`data/grind_probe2.csv`). The new default replicates s3.93 cleanly
(ws 2.554/8.1 at 10 seeds; turán exact 6.000/6.0). The grind verdict
is unchanged and STRONGER: no-grind arms lose ws +1.19 (max 8.1→16),
turán +0.92 (max 6→14.2!), regular +1.43, ER +1.02, lattices
+0.22-0.46; dense still ties grind-free at 5-20x speedup. Better
seeds made the grind's absolute contribution LARGER, not smaller —
its chain-level polish (randomized shortening through free fabric)
is genuine value the tail cannot yet replicate, and ball still burns
the full 60 s chasing its fixpoint through the sph/Dijkstra fallback
(the mm-internals §3 lesson: a native shortener wants plain BFS, not
a heap). Campaign implication: the grinder is the WRONG next target —
its value is real; the cheap fronts are obligations (2)-(3) of the
legalization decomposition (negotiated completion over 1-29-edge
residues) and making ball's router BFS-native so the tail gets more
shots per second.

**3.95 (the demotion autopsy — is the grind still editing our
patterns on the s3.93 baseline?).** Re-run of the s3.86 autopsy
(`data/grind_autopsy2.csv`; emb0 = tail="none", emb1 = 30 s warm
grind). Verdict: **demotion is real on lattices, partial on the
crystal, and NOT yet true on liquids/expanders.** grid_200: demoted —
412/559 changed chains moved ≤1 tile, ONE moved >3, transitions
overwhelmingly →1run, max 16→2: coupler-snapping and in-place
slimming, the layout survives. turán: the crystal pattern holds
(548 1run→1run) but the grind relocates 330/659 chains >3 tiles and
fixes max-chain OUTLIERS (19→6) the claim layer leaves — evidence
for the exact per-line converter (the outliers are conversion
artifacts, not layout artifacts). ws: better than s3.86 (max 20→9
vs 46→11; big moves 46% vs 54%) but still heavy editing — 1119/2424
chains >3 tiles, shape churn in all directions, grind earns −1.2;
yet warm-from-ours (2.55) beats cold mm (2.9+), so the global
pattern is load-bearing even as chains wander locally. regular:
NOT demoted — 615/948 moved, grind earns −2.3; the expander seeds
are still weak (the no-order regime, ideas §2.12). Campaign map by
cell: grid needs only the converter + slack shortener; turán needs
the converter (outlier tails); ws/regular still have plane-level
residuals the grind is papering over.

**3.96 (the exact per-line converter — built, first-measured, NOT yet
the win; honest status).** Built as designed (`wire_seeds_exact` /
`_convert_line`, toggle `exact_convert` OFF): joint parity+lane choice
per line (exhaustive ≤12 arms, greedy+deepest-point repair above),
widened-interval occupancy (fixing the diagnosed s3.61 defect:
`_color_claim_bars` tracks occupancy by the UN-widened end while
claiming through the widened one — silent truncation), dead qubits
absorbed as lane-infeasibility (never the packer's problem — Max).
First smoke (seed 0, tail="none"): **mixed** — ws corner deficits
collapse 23→2 (the corner logic works) but edge deficits WORSEN 32→48
with convert_miss 84 and 1747 repair flips; ER slightly worse; turán
parity (and note: today's baseline turán premx at seed 0 is 10, not
the autopsy's cross-seed 19 — the outlier is seed-dependent).
Diagnosis: (1) strict widened-DISJOINTNESS refuses seatings the old
greedy survives by benign truncation — overlap is sometimes harmless
when the contested positions differ; (2) the greedy+repair parity
path (which crowded ws lines always take, n>12) is weak — the flip
churn shows it thrashing where the true small-state DP would be
exact. The design's promise lives or dies on those two: next
iteration = the real (cap0+1)x(cap1+1)-state DP over endpoint events
(exact at any n) + truncation-tolerant seating (contest POSITIONS,
not hulls). Toggle stays off; all 617 tests green; control untouched.

V2 BUILT AND SHIPPED (same day): both diagnosed fixes landed —
required-hull claims (arms contest only the span their parity targets
need; benign overlap stops blocking seats and chains shed the
kappa-floor padding) and the exact classed-active-set DP (state = the
<=8 live (arm, class) pairs; the greedy+repair thrash is gone).
Smoke: corner deficits 0 on EVERY cell; **ER 1→0 deficits and the
skip gate fires on a sparse cell for the first time in program
history**; regular 17→10 (premx 18→13), grid 21→10, ws 32→30,
extensions collapse everywhere. Probe (`data/conv_probe.csv`, single
flip, box load ~50-87 — wall caveat): wins or ties every cell —
**K100 −0.260 with max 9→8, K140 −0.272, spin_glass −0.313, ER
−0.120, regular −0.088** (the dense wins are the shed floor padding:
shorter claims = shorter chains), deciders turán/ws at exact parity,
one wall flag (K100 26→37 s at load 87, noise-suspect).
`exact_convert` DEFAULT ON per the winners rule; 617 tests green.
Named next (discussed with Max, not yet built): the EXACT CENSUS
certificate — strengthen the census to the converter's true per-line
feasibility (per-parity required-hull depth <= 4), closing the s3.73
blind spot and making "exact-census 0 ⇒ valid embedding" a provable
pre-claims guarantee; mm then needed exactly on runs ending
exact-census > 0, with ball's sph router as the native last resort.

**3.97 (the certificate ships; the census pressure is refuted as
priced).** Built per the discussed design: `_arm_targets` shared
helper (converter and census read one book), `claim_overload(
required=True)` pricing the converter's actual claim spans, the
`certified` diag (converter misses 0 AND completion closed — the
conditional theorem's premise, verified post-hoc every run). Probe
(`data/cens_probe.csv`, load ~55-68): **census_required is INERT on
Z12** — byte-identical on every cell despite the blind spot being
genuinely visible (41 vs 6 census units on the ws end-state,
threading verified live): a ±35 delta against stair-E in the
thousands flips no strict-descent decision at lam=1. On P16 it
REGRESSED turán +0.629 — mispricing hulls nothing will claim (the
converter is stride-gated; the lever now is too). Verdict: REFUTED
as an energy term at shipped pricing; lever kept off; re-pricing is
a lam study nobody asked for. **The certificate is the product**:
certified-and-invalid = 0 everywhere (soundness held empirically);
Z12 certified rates — K100/K140/ER/spin_glass 3/3 (all also skip
mm), turán 0/10 (44 fallback-seated arms: valid but premise fails —
the certificate honestly refuses), ws/grid/honeycomb/king/regular 0
(real deficits). The mm-elimination criterion is now a per-cell
number: five cells provably mm-free-legalizable today; the follow-up
flip when wanted: skip mm legalization when certified (behavior
change, own probe).

**3.98 (consolidation 5 — the purge).** Archive commit **09467299**
holds everything deleted; behavior-neutrality PROVEN, not assumed:
K100/turán/ws/grid seed-0 embeddings byte-identical before and after
(sha256 of the sorted chains), full suite green (596 tests; 24
deleted with their subjects). Fold gate first (Max: re-measure, then
decide): `data/fold2_probe.csv` — fold wins NOTHING beyond tol on the
s3.93 baseline (best −0.04; ws −0.001) and still regresses P16 K100
+0.94 → DELETED per the pre-registered rule. Also deleted: strain_rank
(refuted s3.89), submit_seeds (refuted s3.93), census_required
(refuted s3.97; `certified` diag and `_arm_targets` survive),
the crossfinder driver (envelope recorded s3.90; `_place_cross` +
`_runs_of` moved into ball.py where their only consumer, the singles
pass, lives), the ball-rng/shorten+ball/rshorten+ball tails (settled
s3.82/s3.84; `shorten_chains` itself survives with its unit tests).
Shipped winners made UNCONDITIONAL (knobs deleted): the orientation
bit, the infinite packer (bounded mode survives only as the final
projection), the exact converter (the stride gate alone decides), the
straggler clamp (reachable only at projection). AttractConfig: 20 →
15 knobs. Kept deliberately: ball_singles + _place_cross (the
grind-replacement front), bar_domains (parked, unblock condition
recorded), wire_seeds_iv (P16/untyped), _coarsen_agg (live in the
default init), all of data/ (history).

**3.99 (orientation flips — the y-rule relaxation, first measurement).**
Design discussed with Max 2026-08-19: the stair rule's y-keyed
orientation is a one-order-era artifact; the real freedom is a per-edge
bit, and the safe relaxation is strict-descent flips FROM the y-rule
(each flip re-prices exactly four raw hull spans, so seed stair-E can
never exceed the rule it relaxes; the hub-blight hypothesis — an
extreme-rank hub pays a whole neighbourhood hull on one arm — named as
the target). Built as `orient_flips` (default OFF): `_flip_contacts` /
`_oriented_contacts` in the readout, threaded through arm_books, the
seed books, and a mode-aware staleness fence; `edge_monotonize` now
takes the LIVE bits (a fresh y-rule recompute inside it would gate
swaps on nets the pipeline no longer prices — found in design
validation, fixed before first run; flag-off byte-identical, 606 tests
green). Probe (`data/orient_probe.csv`, 13 cells, 10 seeds on the
deciders): **mixed — wins exactly where geometry is frustrated, loses
exactly where the gate is blind.** Wins: king −0.145 with mx 3.3→2.7
(recovering the s3.93 open regression, both metrics), spin_glass
−0.098, P16 ws −0.120 with mx 12.7→11.0, P16 turán −0.054. Parity:
turán/Z12 exact 6.000 on 10/10 (the diagonal is flip-free by mirror
symmetry, as predicted), ws/Z12 2.55 vs 2.56 at 10 seeds (the smoke's
seed-0 −0.118 was noise), K140, honeycomb. Losses: **dense K100 on
BOTH fabrics** — Z12 +0.33 with mx 8→10 and the skip gate firing in
both arms (a deterministic seed-quality regression, not legalization
noise), P16 +0.79; regular +0.128 with mx 6→7; grid wall flag (arrange
+2.2 s of flip cost; the rest of the +12 s total tracks the load ramp
4→21). Lever stays OFF per the pre-registered rule (no win beyond tol;
one regression beyond it). The mechanism reading, sharper than the
fold's version of the same lesson: **the flip pass is un-gated by
construction** — it lives inside the readout, accepts on raw hull
spans alone, and since every flip weakly lowers stair-E the E-gate
could never veto one anyway; the claim layer (parity/nesting on
complete junctions — K100/Z12 skip-fired both arms, so junction
existence is NOT the mechanism) has no voice at the only decision
point. The blind spot s3.73 measured as a margin is load-bearing the
moment a new degree of freedom prices against it. Named candidate
responses (to discuss): a claim-aware flip margin (flip only when the
hull-span gain clears a parity/nesting toll), or batch flips per
vertex (the single-flip activation barrier on hubs — one leaf +4, all
ten −25 — is measured arithmetic, notes of the design session), or
accepting the regime split and gating flips off the certified path.
Hub-blight verdict: NOT confirmed on Z12 liquids (ws mx 8.2→8.2,
regular mx worse); the max-chain wins landed on king and P16 ws
instead.

**3.100 (alignment reinsertion — the interleaving DP, first
measurement).** Design settled with Max 2026-08-19: the cluster pass's
executor becomes an alignment DP — a unit is removed from the axis
order and reinserted at the exact optimum over ALL interleavings with
the rest (both sequences keep internal order; the reversed block
competes), replacing the gather's one-position screen. Two structural
upgrades landed in the build: **induced-rule pricing** on the y-axis
(the stair rule is an order statistic of the y-order and the DP builds
that order bottom-up, so contacts are re-derived per candidate — the
y-staleness every y-composite carried is deleted, and orientation
freedom arrives INSIDE a gated composite, the fix the s3.99 defect
demanded), and exact frozen-net pricing on x. Pricing verified exact
by test: DP best == brute-force min of ground-truth stair energy over
all merges x orientations, both axes (`TestAlignReinsert`); 615 tests
green; switch `align_moves`, default OFF. Probe
(`data/align_probe.csv`, 13 cells, 10 deep seeds): **the gated route
works where s3.99's un-gated flips failed — dense Zephyr improves
(K100 −0.060, K140 −0.107) instead of regressing — plus spin_glass
−0.208, king −0.119 (mx 3.3→2.7, the s3.93 open regression again
recovered), grid −0.031, P16 ws −0.078 (mx 12.3→11.3), turán exact
6.000 on 10/10.** Held OFF by two named defects: (1) **wall** — the
DP's Python constants eat placement budget (turán arrange 6.9→30 s,
regular 7→30, honeycomb 3.5→20; spin_glass won anyway), a mechanical
fix (numpy-ified neighbour setup + the fold-style unchanged-context
memo); (2) **the s3.73 gate blind spot, now actively exploited** — ER
+0.600 (426 accepted composites on an expander where gathers accept
~none; stair-E-real, claim-layer-fictional — the sub-capacity
parity/nesting margin) and P16 K100 +0.604 (junction fictions, the
fold's defect verbatim, at only 5.8 s arrange — genuine mispricing,
not budget). The sharpened lesson: **a stronger proposal optimizer
makes the judge's blind spots load-bearing** — the gate energy that
was good enough for weak moves is now the binding constraint, which
re-motivates the exact-census pricing line (s3.97's census_required
was inert at lam=1 against the OLD move set; against align's exact
proposals that inertness claim needs re-measurement). Verdict: lever
OFF per the pre-registered rule; the campaign order is perf fix →
re-probe → gate-pricing round.

**s3.100b (the perf round — profiled, not guessed).** The DP was not
the hog: setup vectorization + a per-row minimum.accumulate DP (the
right/down grid recurrence collapses each line to one running-min)
gave 2.5x per call, but the profile showed **15.5 of turán's 19.8 s
arrange was edge_monotonize inside the composites** — ~700k full
h_total re-reductions, a pre-existing cost that align's stronger
proposals expose. Fix: incremental per-net span accounting in
edge_monotonize (a swap re-prices only the nets containing its two
endpoints against a cached row-span vector) — decisions provably
identical on integer line indices, pinned by a permanent oracle test
against the old evaluator (the s3.92 pattern); benefits the DEFAULT
pipeline too. Plus the unchanged-context memo (fingerprint of global
positions; state-preserving outcomes only). 616 tests green. Re-probe
(`data/align_probe.csv`; v1 archived as `align_probe1.csv`): **every
ACL bar now passes.** ER +0.600 → +0.160 (three-quarters of the v1
regression was budget displacement, as hypothesized; the in-tol
residue is the gate blind spot's true size there), P16 K100 +0.604 →
+0.360 (in-tol at that cell's 5% band), regular +0.112, ws/Z12 +0.036
≈ parity at 10 seeds. Wins unchanged: K100 −0.060, K140 −0.107,
spin_glass −0.208, king −0.119 (mx 3.3→2.7), grid −0.031, honeycomb
−0.025; turán exact 6.000 on 10/10. Remaining flags are wall-only
(spin_glass 37.6→50.7 s, honeycomb 20.7→29.9 of the 60 s budget):
the align arm now SPENDS more of its allowed budget on cells that
used to finish early — and wins them. **DEFAULT FLIPPED (Max, 2026-08-20: "it wins and there's reasons
behind it winning")** — `align_moves=True`; the gather executor
survives as the control arm. The gate-pricing round (re-measuring
s3.97's census inertness against this move set) remains the named
attack on the in-tol expander/Pegasus residue. CORRECTED (Max's
question, 2026-08-20): gate pricing targets FALSE ACCEPTS only (the
gate-vs-reality gap). The ws revert volume (584 vs 42 accepts) is the
OTHER gap — proposal-view-vs-gate, dominated by the DP's capacity
blindness — which gate pricing does not shrink (and may slightly
widen); revert COST was already slashed by the s3.100b monotonize fix,
and an early-bail inside the composite (the applied state's
stair+census is known before the packs run) is the named cheap cut if
the residue matters. Capacity awareness inside the proposal DP itself
is explicitly NOT planned (the complexity it would import into the
proposer is the reason the two-level design exists).

**3.101 (the truth round — three level boundaries priced, first
measurement).** Built as planned (625 tests green, all switches
default OFF): `align_insert` (|S|=1 alignment DP replaces
_order_proxy's O(n²) double-coverage energy under the insertion
sweeps; long-net-quartile nomination as the wall guard),
`census_required` (the s3.97 required-hull gate term restored verbatim
from archive 09467299 with its monotonicity test; stride-gated),
`cap_pressure` (per-line crossing-depth hinge² folded into the
alignment DP's gap pricing — the screen objective becomes energy +
capacity pressure with no new DP state; verified by a brute-force
oracle of the pressured objective), and the revert-attribution
counters (census-rose vs energy-rose, per composite). Probe
(`data/truth_probe.csv`, cumulative arms, 10 deep seeds on deciders):

- **The 1→2 gap measured (Max's question): the proposal view's
  capacity blindness is nearly the whole story on sparse cells** — ws
  472 census-reverts vs 72 energy-reverts (87%), regular 726 vs 7
  (99%). And it is regime-diagnostic: spin_glass inverts (1 vs 404 —
  its reverts are footprint-gap, not capacity).
- **census_required is NOT inert against this move set** (the s3.97
  verdict was move-set-relative, as suspected): ws/Z12 −0.050 at 10
  seeds, P16 ws −0.070, dense/crystals byte-inert (identical counters
  — structurally inert where it doesn't bind), no regression beyond
  tol anywhere. The lam=4 escalation over-trades exactly as the old
  doctrine said (turán 6.09, P16 K100 +0.224) — REFUTED, lam=1 right.
- **cap_pressure is the arm that moves the liquids** — ws/Z12
  2.634→2.514 (−0.120, mx 8.4→8.0) and P16 ws −0.148 (mx 11→10.3),
  the predicted monotone gradient across the stack on both fabrics —
  **but it regresses ER +0.577**: the attribution shows the mechanism
  (ER's revert counts barely move, 253→251) — the pressure doesn't
  prevent doomed proposals there, it DISTORTS the ranking among
  candidates: on a uniformly-crowded expander every line sits at the
  hinge, so the pressure integral swamps the tiny energy differences
  and steers merges by capacity noise. A units/normalization question,
  not a mechanism refutation; unresolved.
- `align_insert` alone is near-inert on the board (byte-identical on
  most cells; spin_glass +0.135 in-tol its one delta) — the proxy's
  candidate restriction was not costing outcomes; the replacement's
  value is consolidation (deletes the O(n²) proxy dependency), not
  quality.
- turán exact 6.000 10/10 on every arm except the refuted lam-4; no
  wall flags anywhere.

Verdict: no default flips by the pre-registered rule (inscap's ER
+0.577 is beyond tol; insreq's wins are sub-tol). The live design
question for the owner: insreq is strictly safe with small liquid
wins; cap_pressure's liquid wins are real and its ER defect is a
pressure-units problem (candidate fixes: normalize the hinge to the
energy scale, or hinge only above pool+1, or restrict pressure to
lines the census already flags). Levers all OFF pending that
discussion.

**3.102 (the seat engine — v5 prototype, built and first-measured).**
Decided with Max: the three-level architecture exists to make two DPs
possible by freezing what they can't carry; the alternative paradigm is
crossfinder's loop (s3.90) with the STATE on the ideal plane — carried
integer seats, capacity a COUNT (both recorded crossfinder killers are
claim-level artifacts with no plane referent). Built (`seat.py`,
`arrange_mode="seats"`, default "orders"; init + adapter + tail shared
verbatim): one objective (raw stair + per-tile cover hinge², proposer
== judge, reference-scored acceptance — strict descent unconditional),
two moves (exhaustive exact single-variable re-seat; rigid unit
translation with full boundary-vertex hull recompute — cross-boundary
edges can flip the arm assignment, Max's catch) plus the exact packer
as a gap-free pack-move. Three measured corrections in-session: soft
capacity needs one hard-pack legalization after the search (turán
15.5→9.1 without it); a translate work-bound (2→6 passes, real
convergence); the pack-move itself (turán declined it — informative).
633 tests green incl. brute-force oracles for both moves and the
contact-flip case. Probe (`data/seat_probe.csv`, 10 deep seeds on
deciders): **a ~250-line engine at its first board wins K100/Z12
−0.170, ER −0.173 (the cell the s3.101 truth round could not move),
king −0.052, regular −0.047, and holds ws at parity (−0.003 with max
chain 8.3→8.1) — while losing the turán crystal family decisively
(Z12 +1.91, P16 +1.18) and spin_glass +0.249.** The turán loss is
mechanistically understood and was converged (accept-free fixpoint,
25s): the twin-block diagonal ORDER is discovered by the order moves
(monotonize's sorting network, gathers) that the seat engine
deliberately lacks — the packer alone cannot reach it from seat-space
fixpoints (pack-move declined). Note K100's crystal IS reachable
(seats beat default there): the loss is specifically the bipartite
twin-block structure. Also measured: seats' raw placement beats the
ENTIRE order machinery on ws pre-tail (3.63 vs 3.68 no-tail, seed 0).
Open: fast-grid ranking noise on liquids (fast_miss high — collision
corrections omitted; audit width 4), and the v5 synthesis question —
which halves of the two engines belong together. Lever stays
"orders"; owner discussion next.

**3.103 (the crystal rescue — the seat/orders synthesis, and the
Pegasus fact resurfacing).** Max's mandate: keep the seat paradigm
("the two orders alternative is not something I want to go back to").
The arc, all arms measured on turán/Z12 seed 0 no-tail: mono_move
borrowed as a proposal (9.07, converged — insufficient late); pass
reordering (marginal); native 3-mode pairwise swaps built with O(1)
ext4 third-party updates, oracle-exact (`_swap_exact`; 10.15 — greedy
fine swaps narrowed the coarse basin, the s3.80 lesson inside the
engine); the coarse-first ladder (8.49); and the answer hiding behind
all four: **one full order-engine iteration (packs + monotonize +
gathers) borrowed as a SINGLE proposal, re-scored on the seat
objective — turán lands exactly 6.000/mx 6, converged.** The v5 shape
this proves: carried seats, one objective, proposer == judge, native
seat moves, and the entire two-orders machinery demoted to one
proposal generator the engine is free to decline. Board
(`data/seat_probe.csv`, synthesized engine): **Z12 at effective
parity-or-better with the shipped default across the board** — K100
−0.170, regular −0.076, ER −0.020, ws +0.007 (mx 8.2→8.1), turán
6.076 at 10 seeds (one seed FAILED to embed — a feasibility miss vs
default's 10/10, open), lattices/spin_glass within noise. **P16 is
the catastrophe and the diagnosis is the oldest fact in the file:**
turán/P16 21.5 with mx 46 — the seat objective's cover counts assume
crossing = coupler, which is FALSE on 56% junctions; the fold's s3.89
defect, now in the seat engine's own capacity model, plus orders_move
wall blowups (P16 K100 60.5 s). The paradigm's counts are truth
exactly where junctions are complete — the engine as built is a
ZEPHYR engine, and the honest first-release shape is the same stride
gate every exactness mechanism carries (a hardware fact, not tuning);
the real generalization is predicate-aware cover accounting (ideas
§3 "Pegasus"). Walls also flagged on Z12 dense/lattice cells
(orders_move cost per pass — cadence tuning open). Lever stays
"orders"; 634 tests green; owner call on the Z12-gated flip vs the
predicate round first.

**3.104 (the native gather — built, oracle-green, and the round's real
finding: OUR judge lies on the crystal).** The borrowed `_orders_move`
deleted; the native gather built under the evict-S schema ("restrict
the family, never the fidelity" — expressivity lives in the CANDIDATE
SET: contiguous insert at {mean, bottom, top} x {forward, reversed}
per axis, pure splice + rank-wise multiset reassignment, displacement
by construction, every candidate reference-judged; 635 tests green
incl. its brute-force oracle). It works as a move: turán 8.49 → 7.44
with 13 accepts, genuine coarse fixpoint. But the pre-registered 6.1
bar is unreachable by ANY move, measured directly: **the orders
engine's crystal layout scores seat_energy 1766 while the seat
engine's stalled non-crystal state scores 1704 — the seat objective
(raw hulls + above-pool hinge) PREFERS the layout that converts to
~7.4 ACL over the one that converts to 6.0.** The sub-pool
nesting/parity blindness (the s3.73 class) is inside our own
objective; s3.103's turán 6.000 was PATH LUCK (the borrowed proposal
was accepted early, before the engine dug below the crystal's energy —
consistent with the probe's 9/10 with variance). Matthew 23:26 lands
on the objective itself: the inner cup is the energy. CORRECTED same session (three follow-up measurements, Max's
what-objective question): (1) qubit pricing (per-arm ceil((L+1)/2))
TIES the two states at exactly 972 — the unit-error story is refuted;
(2) the required-hull census barely separates them (1.0 vs 0.0);
(3) converting BOTH states through the real claim path: crystal →
seeds ACL 7.04, deficits 0, COMPLETE; stalled → seeds ACL 6.84 but
**73 deficit edges** — its cheaper seeds are bought with unfinished
coverage, and the 6.0-vs-7.4 endpoint difference is the tail working
from a complete vs an incomplete start. So the quantity that actually
separates them is **completability** — whether the designated
crossings can all be realized — and EVERY plane-resolution term we
own (junction-stair, qubit-stair, tile hinge, required-hull hinge)
is blind to it, including s3.97's census (1 unit vs 73 deficits: the
blind-spot indictment now reaches the required census itself). The
separating structure is still deterministic ideal-Zephyr arithmetic
(course parity, per-junction wire seats — fabric structure, not
defects), so this is a RESOLUTION gap, not NP-mortality leaking in —
but the hope that one line-resolution objective suffices on dense is
measured dead. Open (diagnose before designing): WHERE do the 73
deficits come from — which per-junction/parity condition does the
stalled layout violate that the crystal satisfies, and what is the
cheapest plane-computable term that predicts it. Probe not spent;
lever stays "orders".

**3.105 (consolidation 6 — the refuted-lever purge).** Archive commit
**5be76754** holds the pre-purge state. Deleted (all measured-refuted
or dead, all default-off): `orient_flips` and its whole machinery
(`_flip_contacts`/`_oriented_contacts`/`_contacts_consistent`, the
mode-aware fence — reverted to the plain s3.86 equality assert — and
all threading), `align_insert` (`align_insertion_sweeps`, the
singleton guard reverted), `cap_pressure` (the per-line pressure grids
and threading), and the seat engine's dead `mono_move` hook. KEPT with
reasons on record: `census_required` (validated; the claim-arithmetic
toolkit of the completability question), the entire orders engine
(shipped default; its search half is consolidation-7 material, gated
on a seat-engine board), the packer + converter (the convertibility
technology — see ideas §2.15), and the seat engine with its four
moves. Behavior-neutrality PROVEN: sha256 of sorted-chain default
embeddings byte-identical pre/post on K100 (bdd0fdd9), turán
(d59bac34), ws (34d5e39b), grid (23c023ff), Z12 seed 0; 621 tests
green (14 retired with their subjects); AttractConfig 21 → 18 fields.
Docs trued in the same pass: anatomy's stale fold_moves text replaced
with its deletion note, the knob list refreshed, a seat-engine section
added (§9); ideas.md gained principles 2.14 (restrict the family,
never the fidelity) and 2.15 (completability by construction) and the
§3 completability question — Max's edit/veto invited on those.
Answer to the owner's why-can-orders-reach-turán question recorded in
full at s3.104/ideas 2.15: the orders engine's states are ALL packer
output, a regular subfamily the exactness stack was co-designed with —
completability enforced by representation, not by pricing.

**3.106 (the deficit autopsy — one general class, not 73 anecdotes).**
Run with the overfitting guard built in: the same classifier on the
seat-stalled turán (73 deficits), the orders crystal (control), and
the orders engine's OWN natural membrane on ws (41 deficits).
Findings: **(1) deficits are overwhelmingly LONG-RANGE, not
parity-local** — turán/seat: minimum closest-approach 3 tiles, 60/73
at ≥5; ws/orders: 23/41 at ≥5, only 1 co-tile — the failing chains are
nowhere near each other; the mechanism is ARM TRUNCATION (claims far
short of the promised hulls), not crossing-level parity misses.
**(2) convert_miss does not predict deficits**: the crystal carries 65
converter misses and completes to 0 deficits (stalled: 63 misses → 73
deficits) — what differs is whether completion can locally REPAIR a
miss, i.e., whether the truncated arm's partner is still within
extension reach. **(3) the class is general** — the dominant failure
is identical in both engines, differing only in volume, so a term
addressing it is not turán-tuning. Design conclusion (consistent with
Max's sum-vs-max principle: the term is a COUNT): the plane's
tile-depth hinge says "≤8 fits", but the claim layer must seat
REQUIRED (snap-widened, parity-classed) hulls into 8 lanes per line —
a strictly tighter per-line feasibility that the converter's own
classed-active-set DP already decides. CAVEAT (caught answering
Max's converter-miss question, same session): raw MISS COUNT does not
separate the states either — crystal 65 misses/0 deficits vs stalled
63 misses/73 deficits — so "per-line converter feasibility" as a
count is measurably as blind as the census; the separator is what
happens AFTER a miss (truncation magnitude / whether the partner
stays within repair reach). Refined candidates measured same
session: lost-span MASS also fails to separate (crystal 65 vs stalled
74) — but the DISTRIBUTION separates cleanly: crystal = 65 lossy
arms each losing EXACTLY 1 junction (the benign parity-slack trim —
the crossing survives at the other course; worst=1), stalled = 63
arms with amputations up to 12 junctions (worst=12). **The separating
term: Σ max(0, truncation − 1) — truncation beyond the one-junction
parity slack — scores crystal 0, stalled positive.** Sum-natured
(Max's principle), per-line computable, prices the general amputation
class, not turán. Note the resonance: the separator is the TAIL of
the truncation distribution, not its mass — Max's avg-vs-max weekend
observation recurring one level down, resolved the same way (a sum
with the benign unit exempted). Awaiting the owner's call on building
it into the seat judge. Bearing on the bigger deletion Max floated: if the judge
carries per-line seatability, the regularity the packer currently
provides by construction may emerge from the objective, and the
packer could retreat to init-only — plausible, testable only after
the term exists, promised as nothing.

**3.107 (design note, discussed with Max 2026-08-24 — the brick
plane; UNBUILT, recorded against compaction).** The s3.106 autopsy's
cure is a RULER change, not a term: quantize the ideal plane to the
fabric's parity period — on Zephyr one "brick" = 2 junctions = one
qubit-length. Framings that must survive: (1) **effective-Chimera
resolution** — Zephyr is two Chimera sheets stapled at half-cell
offset; a brick is one cell of each sheet superimposed; Chimera was
ALREADY brick-quantized (qubit = cell), and every parity pathology is
the leak from keeping cell-resolution paper over 2-cell dominoes. The
principle: the plane lives at one qubit per cell per lane. (2) **the
geometric budget** — the coarsening quantum is the BAR LENGTH (one
qubit-length), not the sheet count; what matters is chip width in
qubit-lengths: Chimera ~16, Z12 ~12.5, P16 ~5 — deriving "Pegasus
looks mortal" in advance (thin geometric regime + incomplete gluing
as a second independent wound). (3) **the overpay analysis** (Max's
question): end-rounding to brick boundaries costs ≤1 junction per
arm-end but ZERO extra qubits vs reality — the old junction-plane was
booking phantom half-qubit savings (the crystal's 65 benign 1-unit
trims are this rounding surfacing at conversion); the parity does NOT
vanish physically — it is demoted to a **straddle spill**: the 4
phase-aligned wires per ribbon host brick-intervals at exactly 1
qubit/brick (clean depth≤4 theorem), the 4 off-phase wires host them
at +1 qubit spill per arm, payable from the whole-brick booking —
graceful, bounded, taken only when aligned wires fill. Honest theorem
status: exact seatability guaranteed at depth ≤ 4, practical at ≤ 8
with spill-aware seating — the falsification gate before any build:
at brick resolution the stalled turán state's infeasibility must
become VISIBLE as cover overload while the crystal stays clean.
(4) **roles**: a variable = a cross of bricks; its NUCLEUS = the
corner brick where its two arms meet (sub-brick corner-qubit choice
belongs to the converter); the plane decides LINES (seats + hulls),
the converter decides WIRES (per-ribbon interval seating, aligned
phase preferred, spill as fallback), completion verifies. Supersedes
the s3.106 term-hunting: Σ max(0, truncation − slack) remains the
diagnostic that found this, not the design.

**3.107b (sharpening, from Max's two-rows-of-8 question, same day).**
The brick quantization is ANISOTROPIC — per arm, along the arm's own
axis only. Parallel lines are spaced HALF a qubit-length apart (a bar
spans 2 junctions ⇒ 2 perpendicular lines per bar-length, fabrics.md
§4), so a fully-2D brick would swallow TWO parallel lines = 16 wires
per brick-row. We do NOT pool them: an arm cannot continue from line
w to line w±1 (no same-orientation coupler crosses lines; a line
switch is a bend through a perpendicular bar), so 16-per-brick-row
would be paper capacity across an uncrossable boundary — exactly the
phantom-fidelity sin the design removes. Ledger stays per line:
transverse coordinates (WHICH line each arm sits on, hence the
nucleus) remain at full line resolution; only arm EXTENTS are
brick-quantized. Capacity per (line, brick) = 8 wires, 4 aligned +
4 straddling. Corollaries: (a) the crossing junction between u and v
is fully determined by the two line choices (u's h-line × v's v-line)
— nothing new for a converter to decide about WHERE; junction
K_{8,8}-completeness makes any wire pair couple there, so the
converter's surviving job is only which wire within each line, with
coverage of the crossing brick guaranteed by the aligned/spill
booking. (b) Brick boundaries = even junctions: j=0 bars tile bricks
{2z, 2z+1} exactly; j=1 bars straddle; the leftover junction 2m at
the chip edge is the known boundary-half-capacity fact appearing as a
half-brick. The "2×2 superimposed Chimera cell" of s3.107 is the
DERIVATION of the quantum (why one qubit-length, why Chimera never
had the disease), not the data structure. The absorption mechanism,
stated once (Max's how-is-parity-absorbed question): a brick contains
one junction of EACH parity, so a whole-brick promise covers both
classes at every step of its length — no whole-brick promise can be
parity-infeasible, and covering a brick covers both its junctions, so
which one the partner's crossing lands on is free (this is why
extents can be coarse while line choices stay exact). Each
orientation's accounting cell is 1 line × 1 brick = a 1×2 domino in
junction units = exactly one qubit footprint; the two orientations'
cell grids are woven dominoes — no common 2×2 supertile exists
anywhere in the algorithm, only in the derivation.
STATUS: refuted at its own gate — see s3.108. Nothing was built.

**3.108 (the brick gate — s3.107's premise refuted; the objective
already sees the doom).** Ran the recorded falsification gate
(`data/brick_gate.py`, kept; states = the exact s3.106 autopsy
specimens, deterministic). Three findings, in the order they fell:
**(1) the raw census does not separate** — with `_arms` as
seat_energy uses them, brick-resolution cover shows cover-16 bricks
in BOTH states (crystal hinge² 514 vs stalled 521, same lines h12/v1).
Breakdown traced every cover-16 cell to **phantom point arms**:
`_arms` seeds each side's interval with the variable's own
coordinate, so a contact-free side still deposits cover 1; stacks of
8 co-located variables put 8 phantom points per junction, and two
adjacent stacks merge to 16 at brick resolution. Under the stair rule
an edge consumes u's h-arm and v's v-arm only — an empty side demands
no bar. (Benign at junction resolution today: stacking is capped at
pool, so phantoms never cross the hinge; any coarser or
required-widened census they poison.) **(2) the demand-honest census
separates at BOTH resolutions**: excluding empty sides, the crystal
is perfectly clean (junction 0, brick 0) and the stalled state is
visibly overloaded (junction hinge² 11, brick 6 — v-line 2 at depth
9 > pool 8 along its whole length, a plain depth violation, not a
parity artifact). **The s3.107 premise — infeasibility invisible at
junction resolution, visible only at brick — is false. The junction
plane already sees it; the brick ruler adds nothing for this failure
mode.** Design refuted at its own gate; no engine code was changed.
**(3) the completability question's answer was hiding in the shipped
objective**: seat_energy decomposes as crystal = 1766 stair + 0 pen,
stalled = 1693 stair + 11 pen (λ=1). The capacity term SEES the
stalled state's infeasibility — it is outvoted: Δstair 73 vs Δpen 11,
endpoint ordering flips at λ > 73/11 ≈ 6.6. (Resolves the s3.104
"blind objective" reading: the qubit-pricing tie and the
line-granular census-1 were the wrong instruments; per-cell hinge
integration along the line reads 11. Note also Δstair = 73 =
deficit count is numerology until shown otherwise.) Caveat kept honest: cover ≤
pool is necessary, not sufficient (the converter's classed DP is the
real judge); depth-9-on-one-line is not yet shown to account for all
73 deficits.

**3.108b (same-session correction, at Max's challenge).** Two
overstatements withdrawn. (1) The λ-sweep suggestion (reweight the
hinge via `overload_lam`) is RETRACTED: it contradicts the standing
cap_pressure verdict (hinge² integral swamps energy gaps on
uniformly-crowded graphs — the ER defect) and the measured lam=4
over-trade; hinge² is on record as the non-decomposable form of the
right idea, and turning it up is the knob the ledger already warns
about. (2) "Design refuted at gate" over-claimed: the gate tested
ONLY the visibility premise (stalled doom invisible at junction
resolution — false), on one state pair. The brick plane's structural
content was NOT tested and remains open: whole-qubit stair pricing
(the junction ruler books phantom half-qubits; the crystal's 65
benign trims are that fiction surfacing), promises that cannot be
parity-infeasible (the converter's parity-classed DP retreats toward
plain interval seating + spill), and depth ⟺ seatability becoming a
theorem rather than an approximation. Adjudication of those is
build-and-measure per house rules: the switch (Phase B plan, sites
enumerated) defaulted off, judged by the paired board — pending the
owner's word.

**3.109 (the brick plane BUILT — `brick_plane`, seats-mode switch,
default off).** Max's call ("let's build it and see what happens").
The implementation rule that kept it tractable: **hulls stay in
junction coordinates everywhere** (seats, contacts, transverse line
choices, the candidate lattice); only the ACCOUNTING quantizes, at
the array boundary — every cover deposit/removal and every stair
span maps endpoints through `p // s` with `s = grid.stride` (1 when
off → stock arithmetic reproduced exactly), pools become
per-(line, brick) counts derived from `wire_map` (interior Zephyr 8;
the over-allocated boundary column self-absorbs to 0 — the packer's
own boundary treatment), and arms are demand-honest (a contact-free
side deposits nothing; spans of empty sides are 0 by construction so
span arithmetic never branches — only deposits carry act flags).
Threaded through the whole engine: `_Live`
(rebuild/without/exact_full with 5-tuple nb_wo carrying the act
flag), `_fast_seat_grid` (brick prefix arrays, junction candidate
lattice, fresh-deposit pricing for empty→nonempty nets),
`best_translate._delta` (deposits quantized AFTER the shift — brick
spans are deliberately not translation-invariant, end-rounding is a
real cost), `_swap_exact` (diffs carry act-old/act-new), gather/pack
re-scored by the brick reference. One real bug caught by the swap
oracle on the stride-2 grid: `_third`'s "net sizes unchanged"
assumption is FALSE under y-moves (the moved endpoint migrates
between the third party's h-net and v-net; act flags must be
recomputed from the migration). Knob `AttractConfig.brick_plane`
(default False), stride-gated like the exactness stack. Perf round
(the s3.100b precedent, the probe walls forced it): the reference
evaluator (`seat_energy`) vectorized — stair rule as scatter-min/max
over edge index arrays, cover via diff-and-cumsum, per-graph edge
cache; verified `==` (exact, not approx) against the per-edge
original on 800 random cases both rulers both fabrics; brick pools
memoized on the grid (the line_pools pattern). All integer-valued
quantities, so vectorized sums are exact. 634 tests green (oracle
matrix: stock-Chimera, brick-Chimera s=1, brick-Zephyr s=2;
hand-pinned brick cases incl. the boundary brick and the
same-brick-partners-cost-the-same design claim); default-path
fingerprints byte-identical pre/post (K100 56ec1320736ff19e, turan
5edf09889bfba452, ws 4aa8f0d4729ca26c, grid 5b37c311a83ba60d — note
these are this session's protocol hashes, not s3.105's). Smoke
(turán Z12 seed 0, 60s): seats 6.000/mx 6, brick 6.500/mx 7, BOTH
deficit-0 and mm-skipped; at 240s brick converter misses drop to 24
vs stock's 43 (the parity-miss class shrinking, the design's
promise) but ACL holds at 6.5 — under the brick ruler the crystal's
junction-packed abutment states are priced differently and the
engine settles elsewhere. Board probe `data/brick_probe.py`
(seats vs seats+brick, one flip) launched; verdict entry to follow.

**3.109b (the brick board verdict — VALIDATED MIXED, lever off).**
`data/brick_probe.csv`, 13 cells, deep seeds turán/ws Z12, paired,
TIMEOUT 60. Bar: PASS (no cell beyond tolerance, no feasibility
loss). Deltas (brick − seats, negative = brick wins): the liquids
and lattices lean brick — ER100 −0.210 (the expander, the s3.102
engine's own best regime), ws −0.069 with mx 8.8→8.6 (the BAR
liquid, 10 seeds), grid −0.028, honeycomb −0.035, king −0.003;
the ordered-dense cells lean stock — turán +0.092 (6.0→6.092, mx
6.0→6.4; the crystal family again: junction-packed abutment at
exactly pool is optimal there and whole-brick booking prices it
conservatively), spin_glass +0.086, regular +0.097; K100/K140
tie/noise. P16 gate check: K100 ties EXACTLY (the stride gate is a
true no-op); P16 turán/ws deltas (−0.763/+0.165) are deadline
jitter under load ~86, not signal — both arms run byte-identical
code there and only wall-clock differs. Converter misses under
brick hold in the 20s on turán rather than dropping to zero — the
smoke's 43→24 improvement came with the budget, not the ruler
alone. Verdict: the ruler change is REAL but not a default-flipper
— it trades a small crystal-family toll for small liquid/lattice/
expander gains, all in-tol. Lever stays off; the brick plane is now
a measured one-line switch on the seats research vehicle, and the
s3.107 theory stands adjusted: whole-brick booking is honest about
qubits but conservative about abutment-sharing, exactly where the
crystal lives (the s3.108 gate's lesson, now visible in ACL).
SCOPE CAVEAT (Max's question, same day): this verdict measured a
MIXED-RULER pipeline, not brick end-to-end — the seats branch still
brackets the search with three junction-ruler packer invocations:
the init projection (imposed), the pack move (harmless — re-scored
under brick E, strict descent), and the FINAL HARD LEGALIZATION
(imposed, un-gated: the last touch before the converter re-jostles
the state at junction resolution, blind to bricks). The small
losses could live entirely in that last pack. Named follow-up, not
yet run: brick arm with the final legalization skipped — the brick
hinge over per-brick wire_map pools is near-hard capacity, so if
brick-clean states convert WITHOUT the packer's rescue, the ruler
does by pricing what the packer does by construction (the
packer-retreats-to-init-only deletion, with a measurable path);
if not, the packer's tenure is re-confirmed. Owner's call.

**3.110 (the two-ruler lexicographic engine BUILT —
`arrange_mode="lex"` — and the packer's true job discovered).**
Max's directive: capacity as certificate, each detail at its own
resolution, fewer steps. Design: descend on lexicographic
(overload, stair) — capacity at the BRICK ruler (honest arms,
wire_map per-(line, brick) pools; the near-hard constraint), stair
at the JUNCTION ruler (the sharp objective; no brick plateaus) —
expressed as ONE scalar `pen * 2**26 + stair`, exact in floats
because every quantity is integer-valued, so the entire existing
scalar machinery (moves, audits, prefix scans, thresholds) carries
over unchanged. Implementation: the s3.109 single quantum `s`
split into `s_cov` (deposits/pools) and `s_len` (spans); one mode
enum {stock, brick, lex} derived in `_mode_params`; λ is UNUSED in
lex — the swamping/weighting defect family (cap_pressure ER, the
s3.108 outvoting) is unrepresentable, mooted not tuned. 642 tests
green (4-mode oracle matrix; lex hand-pins; the pen-never-rises
invariant; e2e). Fingerprint protocol caveat discovered: the ws
board fingerprint is NOT run-stable at 60s under load (two runs of
identical code differ; deadline jitter) — K100/turan/grid remain
byte-stable and matched. **The finding that outranks the build**:
the plan's no-legalization pipeline FAILED its smoke in the most
informative way — the lex search does its job perfectly (pen 0,
stair 1695 < the seats arm's 1704) and the converter then produces
578 deficits on the raw state; ONE packer pass on the same state →
0 deficits, with pen 0 PRESERVED. So the packer's irreplaceable
role was never capacity (the invariant owns that now, measured):
it is FAMILY NORMALIZATION — wire_seeds_exact + completion are
co-designed with packer-output states (ideas 2.15, now measured
from the other side). Not snap-specific (snap off: still 323
deficits); the lex state carries stacks (max 9 vs packed 8) and
per-line order shapes the exactness stack has never seen. Shipped
accordingly: lex pipeline = init → pack → search → pack(normalizer)
→ convert → verify — still shorter than seats (no per-pass pack
moves, no λ), e2e turán 6.500/mx 7/0 deficits/certified at 60s.
NAMED NEXT (the deletion that finishes the design): a lex-family
converter — per-line spill-aware brick-interval seating (aligned
wires host abutting bricks bar-for-bar; straddling wires need
1-brick gaps, the +1 spill; the even-lo required-hull poke is the
boundary case) — would delete the normalizer AND the classed
active-set DP. That is converter co-design work for discussion,
not a solo build. Board verdict (lex vs seats vs default,
`data/lex_probe.py`): entry to follow.

**3.110b (the lex board verdict — REFUTED AS REPLACEMENT; the
path-freedom lesson).** `data/lex_probe.csv`, 13 cells × 3 arms
(default/seats/lex), deep seeds turán/ws Z12, TIMEOUT 60. Bar: FAIL
— Z12 turán +1.326 vs default (7.326/10 seeds, mx 10, where the
seats arm holds 6.000 exactly; P16 turán fails for both engine arms,
the known crossing≠coupler defect, lex 19.1 < seats 24.6 but both
far out). The rest of the board is parity-or-better for lex vs
default: K100 −0.170, ER −0.196 (its best cell — the expander
again), ws −0.002 with mx 8.2→8.5 (vs the seats arm's +0.075/9.0),
king −0.012; small losses spin_glass +0.208, grid +0.155,
honeycomb +0.068. **The diagnosis that matters**: the crystal IS
inside the lex-feasible family (the s3.108 gate measured it pen-0),
so this is not a representation failure — it is a PATH failure.
Strict descent under a hard leading key cannot cross even one
transiently-overloaded state, and the routes into the crystal basin
apparently wade through overload; the soft hinge (λ=1) that the
seats arm keeps is load-bearing exactly as path freedom, not as a
price. The session's completability lesson closes into a loop: the
orders engine reaches the crystal by CONSTRUCTION, the seats engine
by WADING, and the lex engine — which holds the strongest
end-state guarantee — cannot get there at all. Constraint
handling, not the constraint itself, is the open design surface:
what survives of s3.110 regardless is the λ deletion mechanism
(scalar lexicographic weight), the two-ruler split, the invariant
machinery, and the measured normalizer discovery. Lever stays off;
"lex" remains in the tree as the third mode of the shared engine
(one enum, no duplicated machinery). For the owner: the fork is
(a) path-freedom variants of lex (e.g., lex only after first
feasibility, soft within pen-ties) — design discussion first, house
warning about knob-breeding applies; (b) accept the seats engine's
soft hinge as the wading mechanism and spend the simplification
budget on the converter co-design instead (the normalizer deletion,
which s3.110 measured as the packer's last load-bearing role).

**3.111 (best_interleave — the insertion DP resurrected as a
one-court move; Max's sliced-Wasserstein frame).** The owner's
insight, recorded as the design's premise: the alignment DP's
frozen-rest assumption is exact at the optimum and near-exact nearby
(the sliced plan agreeing with the true plan in the limit); its
historical failure was the ARCHITECTURE around it — exact
optimization in one court, judged and mostly rejected by another (a
rejection generator) — never the assumption. In the seat engine
proposer == judge, so the same DP cannot generate a rejection
cycle: each call either returns a true improvement, certifies "this
(set, axis) is already optimally interleaved" (interleave_noops —
the measure-zero-disagreement set), or has its stair-optimal
candidate declined by the audit at the cost of ONE evaluation
(interleave_declines — the measured diagnostic for whether the DP
interior ever needs a capacity term; none built speculatively).
Build: `best_interleave` in seat.py — evict unit, re-insert at the
exact optimum over ALL interleavings via the EXISTING
`align_reinsert` (s3.100/100b machinery, untouched), value multiset
handed back by rank (the gather idiom; the gather's 6-candidate
family is a strict subset), audited by `seat_energy(mode)`; knob
`interleave_moves` (default off) swaps it for best_gather in the
unit loop of both seat modes. Doubles as the named counter-move to
the s3.110b path-blocking refutation: a JUMP lands on the final
interleaving without traversing overloaded intermediates, so the
lex mode's hard capacity key cannot block its route. 649 tests
green (exact-optimum oracle vs brute force over all interleavings
on the capacity-slack tier — the DP's view-argmin matched the true
optimum; soundness+determinism across all four mode/grid combos);
stable fingerprints byte-identical (ws excluded per the s3.110
jitter finding). SMOKE, the headline: turán Z12 seed 0 at 60s under
lex+interleave = **6.000 / mx 6 / 0 deficits / certified** — the
crystal-class result the lex engine alone could not reach (6.5-7.3),
via 2 accepted jumps, 357 cheap declines, 937 noop certificates.
Board probe `data/int_probe.py` (default / seats / seats+int / lex /
lex+int): verdict entry to follow.

**3.111b (the interleave board verdict — lex+interleave reaches
BOARD PARITY with the shipped default on Z12; the complementarity
finding).** `data/int_probe.csv`, 13 cells x 5 arms, deep seeds
turán/ws Z12, TIMEOUT 60. The headline: **lex+interleave holds
turán at 6.000/mx 6 across ALL TEN deep seeds — exact parity with
the orders default on the cell that refuted lex outright at
s3.110b** — and posts no Z12 ACL loss beyond tolerance anywhere:
wins K100 −0.210, ER −0.263 (the expander, the family's best cell),
king −0.058, ws +0.028 with the best max chain on the board (8.1 vs
default 8.2); small in-tol losses spin_glass +0.156, regular
+0.074, grid +0.071, K140 +0.036, honeycomb +0.015. **The
complementarity finding (the run's deepest fact)**: the jump and
the hard key only work TOGETHER — seats+interleave (jump, soft
key) LOSES turán to 7.28, lex alone (hard key, no jump) loses it
to 7.42, lex+interleave lands 6.000/10. Mechanism: the DP's
stair-optimal jumps need the lexicographic audit to filter them
onto the feasible manifold (soft λ=1 accepts stair-good/pen-bad
jumps that wander off the crystal path), and the hard key needs
the jump to cross the overloaded valleys it cannot walk through.
Max's sliced-Wasserstein resurrection and the capacity certificate
are two halves of one move-acceptance geometry. P16: the whole
seat family remains broken (crossing≠coupler, the standing named
gap; seats+interleave is outright toxic there, K100 25.4 — the
jump amplifies the broken cover model). Wall bars: engine arms
consume the full budget on K140/grid (slower, in-budget).
CONSEQUENCE FOR THE OWNER: the seat engine (as lex+interleave) has
for the first time met the consolidation-7 precondition on Z12 —
board parity with the orders engine, crystal included — with a
shorter pipeline (init → pack → lex-search-with-jumps →
pack-normalizer → convert → verify; no per-pass packs, no λ, no
insertion sweeps, no align court in the loop). What consolidation
7 would delete if Max calls it: the order-search court
(monotonize, insertion_sweeps, _order_composite, the arrange move
machinery, cluster order gathers), with align_reinsert RETAINED —
it is now the seat engine's own jump interior (the resurrection
inverted the deletion list). Gates before the call: P16 predicate
work or an explicit P16 carve-out; a deeper seed sweep on the
in-tol losses; the owner's word.

**3.112 (CONSOLIDATION 7 — the winner ships, the orders court
closes).** Max's call after the s3.111b board ("it's probably just
time to consolidate now, this seems like a clear winner"; goal: the
algorithm "in as small a state as possible so that I can steer it
again"). THE FLIP: lex+interleave becomes the default — then every
mode/engine knob dissolves. ONE pipeline: init → pack_project → the
lex engine (lexicographic (capacity, stair); moves: interleave-jump,
swaps, re-seats, translations) → pack_project (family normalizer) →
converter → completion → tail. AttractConfig 20 → 12 knobs (deleted:
arrange_mode, interleave_moves, brick_plane, align_moves,
census_required, arrange_iters, insert_sweeps, overload_lam).
DELETED (archive 12fe484c; purge commit 37d3439c; −1145/+282 lines
across field/placement/seat): `alternate_arrange` and its court
(order composites, cluster pass, the insertion court, align memo,
revert attribution), `insertion_sweeps`, `cluster_gather_order`,
`_order_proxy`, `claim_overload`; seat.py collapsed to the single
lex objective (mode enum, stock/brick branches, best_gather, the
pack_move hook all gone). SURVIVED WITH NEW JOBS: `edge_monotonize`
— the dependency map proved it LOAD-BEARING inside the pack
projection (it permutes x between the two unbounded packs; its
removal would be a behavior change, recorded as an optional future
measured flip) — and `align_reinsert`, now the jump move's interior
(the deletion list inverted at s3.111). `pack_project` is the
verbatim extraction of the old iters-1 path (books → forced pack(y)
→ monotonize → forced pack(x) → bounded final projections); the
map's dead-energy analysis (every accept forced ⇒ stair/census
evaluations unread) predicted byte-identity and the protocol
CONFIRMED it: post-flip fingerprints K100 7e109b936a1435fd / turan
20333e0b0f33e5aa / grid 2714eeb5c3e0325a byte-identical through the
purge (ws excluded per the s3.110 jitter finding). 609 tests green
(courts' suites deleted with their subjects; align_reinsert
exactness core, packer, converter, and the lex oracles kept green;
fixtures re-tuned to pack_project). Smoke on the finished tree:
turán Z12 seed 0 = 6.000 / mx 6 / 0 deficits / pen 0 / certified /
mm skipped, via 2 interleave jumps. P16 WRITTEN OFF (Max: "weird
and going obsolete... if I never saw pegasus results again I don't
think I'd mind") — the lex engine runs there but regresses vs the
deleted orders engine; recorded openly, the elegant-adapter idea
parked in ideas.md; probe boards may drop P16 cells. data/ probes
untouched (history; stale calls allowed — the consolidation-6
precedent). Named next fronts, in the order the week ranked them:
the lex-family converter (deletes the normalizer pack AND the
classed active-set DP — the last two-court seam), the P16 predicate
(only if Pegasus ever matters again), max-chain's lexicographic
slot (parked).

**3.113 (the orders engine — round 1: state = two orders, pack as
readout, accept-all).** Built per the 2026-08-26 design discussion
(ideas fronts 1+2 together, plus the acceptance question): `engine`
knob ("lex" default / "orders" / "orders-audit"), new `orders.py`
(~170 lines). State is edited only through the induced orders;
positions are re-derived after every adopted move by
`pack_project(monotonize=False)` — the readout; units are contiguous
dyadic intervals of the current order including singletons
(`align_reinsert` guard lifted to |S|>=1; the hierarchy is not
consumed); "orders" adopts every DP return (projected block-coordinate
descent), "orders-audit" is the strict-descent control; the best-lex-E
bookmark is what returns; no normalizer stage (states are packer
output by construction). Default path byte-identical (K100/turán/grid
fingerprints == the s3.112 hashes, re-verified twice; suite + 13 new
tests green). Board (`data/orders_probe.csv`; LOAD CAVEAT: 100-122
throughout): **turán 6.000/mx 6 on ALL 10 seeds in BOTH arms — the
crystal as a structural property of the new engine, and load-robust:
the default control collapsed to 12.4 mean (6/10 seeds at 14.5-17.6,
mx to 56) under the same load, while quiet default = 6.0 — so the
−6.4 delta is a robustness claim, not a quality claim.** ws 2.595 vs
2.589 at 10 seeds (mx 8.2 vs 8.3) — parity while budget-bound at ONE
pass (a readout costs ~0.3 s at n=486; perf is the named unlock).
regular −0.058; K100/K140/spin_glass/honeycomb in-tol. Losses, the
named residuals: **ER +0.84** (both arms; accept-all churned 700-900
adopts to no effect) and **king +1.53/+0.60** — the regime the deleted
fine moves (re-seats, swaps, translations) and/or the hierarchy's
patch units served; **grid +0.50 in accept-all only** (audit parity,
+0.003) — the acceptance fork's first data: the projection-diffusion
won nothing measurable on this board and costs on lattices, so audit
is currently the safer arm. Discovery banked (the one-accounting
principle firing again): **the readout enforces LINE capacity while
seat_energy's pen counts BRICK capacity** — pack-legal lattice states
carry pen 12-100 at the bookmark (boundary bricks pool below the
line's 8); the lex engine descended that away, the orders engine
cannot see it. Two books; resolution candidates: a brick-aware bounded
pack, or pen in the acceptance rule. No default flip (losses beyond
tol). Round-2 candidates in EV order: the readout perf unlock (ws
parity at one pass suggests headroom), the brick/line accounting seam,
fine-scale moves, king/ER diagnosis.

**3.113b (work-to-answer — the acceptance fork decided, and the ws
bookmark discovery).** Max's question: how long did each policy take
to FIND its answer, not to stop. Instrumented (`bookmark_wall`/
`bookmark_readouts` — when the returned state was last improved) and
measured (`data/accept_work_probe.csv`, deep seeds turán/ws): **audit
finds equal-or-better answers FASTER on turán (6.0 @ 11.0s/133
readouts vs accept-all's 18.6s/189) and grid (1.1 @ 12s vs 1.54 @
18.5s); ER is the one inversion (accept-all 5.62 @ 3s then ~1190
readouts of pure churn; audit 5.53 @ 27s/1418) — slightly better
answer, 9x the work.** Combined with the s3.113 board, audit is the
better policy AS BUILT; the accept-all/SGD bet loses round 1 on the
evidence (caveat: at current readout cost its diffusion never got
cheap moves — re-measure after the perf unlock; accept-all stays as
the control arm). The deeper finding: **ws bookmarks at readout 2 in
BOTH arms** — nothing after the first adopt ever improved the lex
bookmark, so the arrange phase currently contributes ~nothing on the
liquid and the parity is inherited from init+pack+tail. Suspected
mechanism = the s3.113 two-books seam: ws states carry brick-pen
~56-67 the line-capacity pack can neither see nor fix, so pen
dominates the lex bookmark and freezes it — later genuine stair
improvements at wobbling pen cannot register. The brick/line
unification is therefore not hygiene; it is plausibly the liquid's
gate. Round-2 order sharpened: (1) readout perf, (2) brick/line
unification (Max: "we need to unify the brick idea with everything
else"), (3) hierarchy groups as EXTRA units on ER/king (Max's
variance hypothesis: scattered similar nodes need joint gathers that
interval accretion cannot express).

**3.114 (the perf round — numba, 11× readout; the budget excuse
dies).** Max's call: numba (pinned in requirements + the ember-qc
pyproject). The pack_lines DP + jstar segment tree ported op-for-op to
`@njit` kernels — same operations, same order, bit-identical by
construction (the Python original survives as the oracle in
TestPackLinesFeasibilityEquivalence, tightened to exact cost equality
plus tie-cascade/duplicate cases); derive_bars_stair/arm_books
vectorized by scatter min/max (`_bars_arrays`; the per-vertex original
frozen as TestBooksEquivalence's reference); pack_project exposes its
final contacts (`info["_contacts"]` — sound by the axis-0 reuse
invariant) and orders.py reuses them; unit probes memoized by state
version (a unit re-probed on an unchanged state repeats its outcome
exactly, so quiet regions cost nothing and the schedule can cycle).
**Readout 111 → 10.1 ms** (ws, n=486). 625 tests green; default AND
engine="lex" fingerprints byte-identical to the s3.112 hashes (one
load-contaminated lex run re-verified quiet — the usual jitter class).
Board re-run (`orders_probe.csv`; round 1 kept as `orders_probe1.csv`):
**the engine now cycles (grid 2→5-6 passes, ER 4→7-12, turán 2→4;
adopts 3-4×) and NOTHING moved — every round-1 delta reproduces
(ER +0.83/+0.52, king +1.50/+0.56, grid +0.47 accept-all vs +0.07
audit, ws +0.02/+0.05, crystal exact 6.000/10 both arms).** The budget
excuse is dead: the residuals are capability, not compute. Sharpened
readings: (1) ER accept-all makes 2,704 adopts across 10 passes and
lands exactly where 800 adopts landed — the interval family cannot
express what ER needs; Max's variance hypothesis (scattered similar
nodes need joint gathers) is now the primary suspect, cleanly
de-confounded from budget. (2) ws's first pass alone still exceeds
30 s (~5,800 units) and its bookmark still freezes at ~1 s on
pen-carrying states — the brick/line two-books seam remains the
liquid's gate. (3) Late coarse recapture now demonstrably fires and
does not rescue the losses — necessary, not sufficient. Acceptance
under speed: accept-all is now the cheaper policy per unit of progress
(readouts per adopt vs per candidate: ws 323 vs 758) but still buys
grid +0.47 where audit pays +0.07 — the s3.113b verdict stands. Named
next, unchanged in order and now unblocked: hierarchy groups as extra
units (the ER/king discriminator), then the brick/line unification.

**3.115 (hierarchy groups as extra units — the ER variance hypothesis
CONFIRMED; king acquitted of it).** Built as `hier_units` (default
off): the affinity hierarchy's groups offered to the orders engine as
extra units, coarsest level first, each a single jointly-judged weave
through the same `align_reinsert`/adopt path as the intervals (the
`_probe` refactor). Probe (`data/hunits_probe.csv`, 6 cells × 4 arms,
deep seeds turán/ws, load ~95-128): **ER is the confirmation — audit+h
5.31 → 4.907 (−0.40, the largest ER movement any orders arm has
produced; the gap to the default engine closes from +0.52 to +0.12) on
just 21 accepted gathers; accept-all+h −0.18 on 1,217** — a few good
joint gathers carry the win, consistent with the s3.113b acceptance
verdict. Max's mechanism reading stands: variance makes some nodes
measurably alike, and a scattered similar set needs a joint gather
that interval accretion cannot express. **king is acquitted of the
same charge**: ±0.05 in both arms — its +0.6 loss has a different
mechanism (candidates: the boundary-brick pen class, or the deleted
fine moves). Guards held: turán exact 6.000 on all arms (173 hier
adopts in accept-all and the crystal still lands exactly — the E-gate
filters), ws ±0.06, regular flat; grid accept-all −0.235 (still above
its audit arm). Verdict: `hier_units` is a validated candidate for the
audit path pending the brick round (the remaining ER gap may be
bookmark/pen-related); not a default flip on its own.

## 4. References

Numbered here; BibTeX in `refs.bib` (keys in brackets).

1. Cai, Macready, Roy (2014). *A Practical Heuristic for Finding Graph Minors.*
   arXiv:1406.2741. — minorminer; the `D^occ` cost and the open initial-placement
   problem. [`cai2014minorminer`]
2. McMurchie, Ebeling (1995). *PathFinder: A Negotiation-Based Performance-Driven Router
   for FPGAs.* FPGA '95. — negotiated congestion; `(b+h)·p`; no convergence claim.
   [`mcmurchie1995pathfinder`]
3. Awerbuch, Azar, Plotkin (1993). *Throughput-Competitive On-Line Routing.* FOCS '93. —
   exponential-in-load pricing, O(log n)-competitive congestion. [`awerbuch1993online`]
4. Raghavan, Thompson (1987). *Randomized Rounding.* Combinatorica 7(4). — exponential
   potential in provable congestion minimization. [`raghavan1987rounding`]
5. Räcke (2002). *Minimizing Congestion in General Networks.* FOCS '02. — exponential
   congestion potentials in general networks. [`racke2002congestion`]
6. Betz, Rose (1997). *VPR: A New Packing, Placement and Routing Tool for FPGA Research.*
   FPL '97; and the VTR documentation (`docs.verilogtorouting.org`) for the modern cost
   parameterization (`pres_fac`, `acc_fac`, `max_pres_fac`). [`betz1997vpr`, `vtrdocs`]
7. Murray et al. (2020). *VTR 8: High-Performance CAD and Customizable FPGA Architecture
   Modelling.* ACM TRETS. — current reference implementation of negotiated congestion.
   [`murray2020vtr8`]
8. Hoo, Kumar, Ha (2015). *ParaLaR: A Parallel FPGA Router Based on Lagrangian
   Relaxation.* FPL '15. — FPGA routing as LP with relaxed capacity constraints;
   multipliers ≈ history. [`hoo2015paralar`]
9. Agrawal, Ahuja, et al. (2019). *ParaLarPD: Parallel FPGA Router Using Primal-Dual
   Sub-Gradient Method.* Electronics 8(12):1439. — the subgradient multiplier update we
   adopt for history. [`paralarpd2019`]
10. Takahashi, Matsuyama (1980). *An Approximate Solution for the Steiner Problem in
    Graphs.* Math. Japonica 24. — the SPH tree-construction heuristic.
    [`takahashi1980sph`]
11. Mehlhorn (1988). *A Faster Approximation Algorithm for the Steiner Problem in
    Graphs.* IPL 27(3). — Steiner approximation context. [`mehlhorn1988steiner`]
12. Cuthill, McKee (1969). *Reducing the Bandwidth of Sparse Symmetric Matrices.* ACM '69.
    — the bandwidth-reducing vertex order. [`cuthill1969bandwidth`]
13. Benchoff. *OrthoRoute — GPU-accelerated PCB autorouting* (web,
    `bbenchoff.com/pages/OrthoRoute.html`, accessed 2026-07-10). — practitioner
    documentation of blanket-decay oscillation and pres_fac capping in a PathFinder
    implementation. [`benchoff2025orthoroute`]
14. Gómez-Tejedor, Osaba, Villar-Rodriguez (2025). *Addressing the Minor-Embedding
    Problem in Quantum Annealing and Evaluating State-of-the-Art Algorithm Performance.*
    arXiv:2504.13376. — evaluation protocol and MM failure modes. [`gomez2025eval`]
15. Spindler, Johannes (2007). *Fast and Accurate Routing Demand Estimation for
    Efficient Routability-driven Placement.* DATE '07. — RUDY: segment/rect-smeared
    routing demand; the deposit model of `field.py`. [`spindler2007rudy`]
16. Lu, Chen, Chang, Sha, Huang, Teng, Cheng (2015). *ePlace: Electrostatics-Based
    Placement Using FFT and Nesterov's Method.* ACM TODAES 20(2). — charges +
    Poisson-solved density potential; the field architecture attraction.md adapts
    (one-sided source is our departure). [`lu2015eplace`]
17. Cheng, Kahng, Kang, Wang (2019). *RePlAce.* IEEE TCAD 38(9). — ePlace line's
    current reference implementation. [`cheng2019replace`]
18. Eisenmann, Johannes (1998). *Generic Global Placement and Floorplanning.*
    DAC '98. — force-directed spreading precursor. [`eisenmann1998force`]
19. Karypis, Aggarwal, Kumar, Shekhar (1999). *Multilevel Hypergraph Partitioning:
    Applications in VLSI Domain.* IEEE TVLSI 7(1). — the multilevel
    coarsen-solve-refine paradigm behind the tile-grid framing. [`karypis1999hmetis`]
20. Garg, Könemann (1998). *Faster and Simpler Algorithms for Multicommodity Flow.*
    FOCS '98. — fractional MCF via multiplicative weights; the principled-solver
    option for the coarse routing subproblem. [`garg1998mcf`]
21. Müller, Radke, Vygen (2011). *Faster Min-Max Resource Sharing in Theory and
    Practice.* Math. Prog. Computation 3. — BonnRoute's shipped fractional-MCF
    global routing. [`mueller2011resource`]
22. Nocedal, Wright (2006). *Numerical Optimization*, 2nd ed. — trust-region
    methods; the cadence rationale of §3.24. [`nocedal2006numopt`]
