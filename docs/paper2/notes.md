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
is already Steiner — union-of-paths is dead code (3.14). 85–95% of
wall-clock is the post-legality shortening, which earns ~30–38% ACL
(3.15). Legal-stage ACL does not predict polished ACL (r ≈ −0.01) —
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
measured: every search method sits 30–60% above the busclique template
and MM's polish cannot improve the template — dense is representational,
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
win, spin_glass −19% (3.34). **Diagonal alignment + insertion order
search: first search win over stock mm on K100; adjacent swaps proven
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
entire mechanism; first K100 win over mm** (3.52). Discrete order
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
discriminator machinery**; turán 10-seed mean 6.535 vs stock 8.098 with
the tail killed (worst 7.00 vs 10.09; 4/10 seeds at the 6.00 optimum) —
**BAR2 (≤6.5) missed by 0.035**, so no default flip by rule; owner call
open. First Pegasus movement from coarse machinery (ws −0.32). Residual:
grid/honeycomb stay at stock (their adjoint wins lived in the ordered
INIT, which gating can't reproduce post-pack) — the lattice fix lives at
init time; named open. Switch `cluster_moves`, fabric-agnostic.

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
domain). Probe (16 cells + 10-seed turán): **units win or tie EVERY
cell** — ER −0.20, spin_glass −0.24, ws −0.08/P16 ws −0.30, honeycomb
−0.14, turán 6.457 (beats s3.70's 6.53); zero ACL regressions; wall
grew seconds on winning cells inside a 60 s budget (the pre-registered
wall clause tripped as drafted — it mis-specified productive spend as
waste; recorded). BAR2's decisive branch fired: patch units exist and
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
