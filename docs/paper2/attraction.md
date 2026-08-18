# Attraction — the idea ledger (condensed)

Condensed 2026-08-06 (Max's directive: notes contain IDEAS; the fossil
record was crowding them out). The full pre-condensation ledger is
`archive/attraction_v3.69_full.md`; superseded code lives at the archive
commits (`612ced3e`, `9d99ebdd`, `023283a1`). **Read `ideas.md` first** —
the confirmed principles and open questions live there. This file keeps
only what prevents re-derivation: every idea tried, its verdict, and the
one-line reason. If you are about to propose something, check it here.

Verdicts: SHIPPED (in the default), REFUTED (measured worse or wrong),
SUPERSEDED (replaced by something better), PARKED (live, with an unblock
condition — see the last section).

## Coarsening / multilevel

| Idea | Verdict | Why |
|---|---|---|
| Leader aggregation to natural fixpoint | validated candidate | one clustering rule replaces twin-hash + matching + depth decree at parity; quotient protection emerges from the weighted score (s3.74 caveat: "parity" carries a ±0.2 expander wobble at n=3 — regular +0.20 in `data/aggregation_probe.csv`, sign flipped in `data/adjoint_probe.csv`) |
| Cluster moves (coarsen the MOVES, not the state) | SHIPPED | member sets gathered as E-gated composites — no summarization, no sizes; eliminates transport's noise losses with zero discriminator machinery; turán 8.12→6.52 at 3 seeds, worst 6.80 vs 9.46 (`data/cmove_probe.csv`; corrected s3.74 — "8.10→6.46" had grafted the s3.71 probe's number onto this mechanism); first Pegasus movement |
| Generous merging (threshold-free move units) | SHIPPED | risk asymmetry inverted under the move frame: τ retired on the units path |
| One-shot-per-cluster cap | SUPERSEDED | a budget rule wearing physics clothes; strict-descent acceptance + free proxy no-ops make the energy itself the schedule |
| y-only cluster gathers | SUPERSEDED | inherited axis asymmetry, not designed; both-axes gathers produced the first dense-Pegasus win (P16 turán −0.61) |
| Lateral (equal-E) acceptance for cluster moves | RETIRED | the churn engine; strict descent bounds re-proposals with no counting rules |
| Per-member affinity criterion | SHIPPED (by correctness decree) | the correct merge criterion (fragments any ratio → 1; size artifact fixed at root); its deep hierarchies expose the open CONSUMPTION defect — nested fragment units pre-empt the full-block gather (turán 6.71 vs 6.46), to be fixed by unit selection/ordering, not by reverting the score |
| Admissibility matching (merge only if someone's best) | SHIPPED | constant-free fix for forced leftover marriages; preserves block purity to the last level |
| τ threshold on the move-unit path | RETIRED | the score only ranks; a pair merges because it is the best available, never because it clears a bar |
| Measure-transport unpack (adjoint junction) | DELETED (consolidation 4, archive d8274198) | wins where the coarse order is real (turán hits 6.00 optimum; lattices fall), loses where it is spectral noise (expanders) — as an unconditional INIT; its gather was subsumed by cluster moves; its lattice claim was solved outright by the order state (s3.76), leaving it nothing to be parked for |
| Twin-hash / one matching round / no-fixpoint decree | DELETED from units path | topology detection; affinity-1 pairs assemble families through ordinary rounds (hash survives only in the legacy init path, queued for the init round) |
| Adjacency-only candidate rule | DELETED | overrode the criterion's own edge/support interpolation; its connectivity justification retracted as unmeasured |
| Coarse-level attraction relaxation | REFUTED | collapses supernodes — the collapse lesson one level up |
| Heavy-edge matching | REFUTED | interleaves edgeless-inside blocks |
| Single global COARSE_SPAN scale | REFUTED | no one value serves crystal and liquid; wants compression-adaptive |
| V-cycle V1 (two-stage, spectral-of-coarse) | SHIPPED (stride-gated) | heals sparse, sets dense records; measured on Zephyr only |

## Initialization / footprint

| Idea | Verdict | Why |
|---|---|---|
| Hier init (dendrogram orders: RCM quotient + attachment-rank expansion, s3.77) | REFUTED as init | ER/expander cells moved the WRONG way (ER +0.23, regular +1.07, king +0.74); linearization destroys the 2-D geometry spectral ranks carry; right move-unit generator, wrong order generator — turán's 10/10-seed 6.000 shows the crystal exception |
| Init offset generator (spiral vs random vs grid, s3.78) | measured near-inert | arrange erases within-cluster offsets on ordinary cells; evenness matters only on giant twin blocks (turán 10-seed: spiral 6.02, grid 6.09, random 6.34); golden angle = ornamentation, purge-eligible |
| pack_lines incremental jstar | REFUTED (bench) | 6->6 / 21->17 ms — never the bottleneck; reverted same-day |
| Segment ("crystal-shaped") member spreads | REFUTED | pre-ordering members pre-empts the E-gated moves that discover better orders |
| Pre-formed K_n diagonal at the junction | REFUTED | same pre-emption mechanism, re-measured: +0.4 despite better energy |
| Compact init | REFUTED | interleaves blocks harder than insertion recovers |
| Spectral init as load-bearing | SUPERSEDED | warm-start heuristic only; results must survive random init |
| Wire-mass region sizing | PARKED | no-op on symmetric coarse graphs; helps heterogeneous only |
| Tangent-tiling closure scale | PARKED | constant-free and gates the hard cell, but the tuned constant still wins |

## Packing / claim layer

| Idea | Verdict | Why |
|---|---|---|
| Exact order-preserving DP + one integer pool census | SHIPPED | lane oversubscription becomes structurally impossible |
| Claim-time parity-exact aiming ("aim, don't repair") | SHIPPED | extensions go to zero; completion becomes a verifier |
| Exact seeds + mm-skip gate | SHIPPED | on junction-complete fabrics coverage = validity; legalizer skipped |
| Overload hinge² in every gate energy | SHIPPED | feasibility visible to evaluation; made order-annealing unnecessary |
| Uniform packing slack (derate everywhere) | REFUTED | trades away the parity slack the aim step needs |
| Unconditional boundary spill | REFUTED | wins one cell, regresses cells with interior slack |
| Deficit-first lexicographic selection | SUPERSEDED | deficit and E must be traded, not ordered |
| Optimistic line capacity (masked_pool) | SUPERSEDED | records superseded by exact seeds |

## Order search / discrete moves

| Idea | Verdict | Why |
|---|---|---|
| Best-insertion order sweeps | SHIPPED | the global relocation move that makes block separation emerge from any init |
| edge_monotonize (per-edge transpositions) | SHIPPED | leverage ∝ edge length IS the sparse/dense interpolation, no cluster awareness |
| Adjacent-swap / swap-Metropolis order search | REFUTED | plateau-bound; swaps cannot make long joint moves |
| Discrete order annealing (order_shake) | SUPERSEDED | only ever dodged overload the gates couldn't see; deleted once overload entered the energy |
| Decaying reshake cycles | REFUTED | cycle-0 contraction is the entire mechanism |
| Cycle-0 contraction before first pack | SHIPPED | cracks the frozen fixed point that nearest-line packing restores |
| Radial inversion | REFUTED | null-to-harmful (confound recorded: no post-inversion repair ran) |
| Degree gate for participation | SUPERSEDED | per-axis interval participation; κ is floor physics only |
| Gather orientation bit (block[::-1] competes, s3.89) | SHIPPED (default) | reversal is the fold's atom translations can't compose; ws −0.113, grid −0.090, zero regressions/cost |
| One-axis fold (rank-interval reversal, s3.89) | REFUTED | preserves the axis multiset — both strands on the same wires (194/194 ov-vetoed); trades chord span to the seam edge, net zero |
| Two-axis hairpin fold (riffle + strand split, s3.89) | DELETED at consolidation 5 — re-measured on the s3.93 baseline (fold2_probe: wins nothing, P16 K100 +0.94); its pre-s3.93 target dissolved with the line-count bound | first mechanism to move ws on BOTH fabrics (Z12 −0.184, P16 −0.271 w/ orient); held by P16-dense: stair-E folds are fictions on 56% junctions (K100 +1.05) |
| Fold ov-ratchet relaxed while infeasible (s3.89) | SHIPPED (inside fold_moves) | the ratchet guards feasibility ONCE ATTAINED; mid-arrange it blocked E 57k→12k over +250 ov |
| Eager fold pass (screen+execute everything) | REFUTED | ~150 composites ate the placement budget, acl worse DESPITE 9 accepts; one-per-pass + geometry memo is the shape |
| strain_rank (proxy-gain-ordered cluster execution, s3.89) | REFUTED; DELETED at consolidation 5 (09467299) | adds nothing over the fold arm; coarsest-first was already good enough at these volumes — ranking wasn't the bottleneck |
| Exact per-line converter v2 (exact_convert, s3.96) | SHIPPED (default) | required-hull claims + classed-active-set DP; corner deficits 0 everywhere, ER legalizes natively (first sparse skip fire); probe: wins/ties every cell (K100 −0.26 w/ mx 9→8, spin_glass −0.31), deciders at parity |
| Certified diag (converter misses 0 + completion closed, s3.97) | SHIPPED (observable) | the conditional theorem's premise as a first-class output; certified-and-invalid = 0 empirically; 5 Z12 cells certify 3/3 (all skip mm); turán honestly refuses (44 fallback seats) |
| Required-hull census as gate pressure (census_required, s3.97) | REFUTED; DELETED at consolidation 5 | blind spot visible (41 vs 6 on ws) but ±35 vs stair-E thousands flips nothing on Z12; P16 mispricing regression before stride-gating; lever off |
| Crossfinder: rip-and-replace as THE algorithm (s3.90) | PROTOTYPED; driver DELETED at consolidation 5 — _place_cross lives on in ball.py | sparse structured: legal + near-optimal in seconds (cycle400 1.042/4.3s); liquids/dense DO NOT legalize — straight crosses can't route around load, and exclusive claims delete mm's load-bearing overlap; endpoint: occupancy-priced overlap + squeeze, to be discussed |
| Ball-prime: grind removal via |S|=1 exact-cross questions (s3.91) | REFUTED for now | dense: grind-free ties at 6-20x speedup; everywhere else grind irreplaceable (turán +0.61, ws +1.31) — the tail polishes mm's own construction on sparse, and ball's sph/Dijkstra fallback (41 ms/tree) burns the budget; singles help marginally, lever kept |
| Grind removal RE-MEASURED on the s3.93 baseline (s3.94) | REFUTED, conclusively | not a packer artifact: better seeds made the grind's contribution LARGER (ws +1.19 w/ max 8→16, turán +0.92 w/ max 6→14); dense still grind-free at 5-20x; next fronts are negotiated completion + a BFS-native ball router, not the grinder |
| Demotion autopsy on the s3.93 baseline (s3.95) | MAP MEASURED | grid: demoted (in-place slimming, 1/559 big moves); turán: pattern holds but grind fixes claim-layer max-chain outliers 19→6 by relocation (points at the exact per-line converter); ws/regular: grind still edits heavily (46%/65% big moves, earns −1.2/−2.3) — plane-level residuals remain |
| Straggler clamp (clamp_miss, s3.92) | SHIPPED (default), value gated on seed submission | repairs the 69-ghost death spiral (seeds: deficits 141→97) but final ACL is sub-tol WORSE on discard-pathway cells (ws +0.12, P16 ws +0.27) — better seeds thrown away, only hint-noise reaches the output; the discard fix is the unlock |
| Incremental pack_lines feasibility (s3.92) | SHIPPED (identical) | the two-pointer re-sorted the window at every step (412k line_depth calls/run); lazy max segment tree, byte-identical jstar, equivalence-tested — no arm |
| Seed discard on liquids (found s3.92) | NAMED DEFECT | arrange exhausts the placement half, cap<=0 skips legalization, fallback mm runs from single-qubit hints — completed seeds (90% edges covered) thrown away; repair: submit seeds warm to the fallback (to discuss) |
| Infinite Zephyr packer (unbounded_pack, s3.93) | SHIPPED (default) | drop the line-count bound, keep hard capacity, census carries the finite fabric, one final bounded projection; ws 3.037→2.552 / mx 10.7→8.1 at 10 seeds — first sub-mm liquid; P16 ws −0.461; turán exact 6.000 10/10; dense identical; king +0.237 open |
| submit_seeds (warm seeds to the fallback, s3.93) | REFUTED; DELETED at consolidation 5 | no effect anywhere (ws +0.043) — legal-stage carries no information (mm-internals §6 confirmed in our pipeline); lever kept off |
| Anchor unbounded layouts at line 1 (s3.93) | SHIPPED (inside unbounded_pack) | line 0 is a boundary line; anchoring there broke turán's exactness (6.00→6.70, skip gate dark) |

## Representation

| Idea | Verdict | Why |
|---|---|---|
| Span state (positions only; extents derived) | SHIPPED | derivable ⇒ readout; energy becomes the real chain length |
| Staircase/diagonal readout (single edge coverage) | SHIPPED | one designated crossing per edge halves the seed overpay |
| Extents as state (v1, v2) | REFUTED | gradient flow can't break the row/column permutation symmetry; assignment and attraction fight |
| Per-edge contact state | REFUTED | 60× the state, nothing measurable bought; corners + derived arms is the representation |
| Exclusive connector claiming | REFUTED | more rigid than the router's own overlap pricing |
| Point state + density bins | SUPERSEDED | monopole approximation is near-disinformation when chains are long |

## Continuous dynamics / pressure

| Idea | Verdict | Why |
|---|---|---|
| Density-limited attraction | SHIPPED | pure attraction orbits (collapse is its fixed point); the density term makes it descend |
| Excluded-volume wall | REFUTED | the wall leaks through arm growth; settlement energies fictional |
| Local congestion penalty at any weight | REFUTED | gradient-blind inside uniform overload — only the rim peels (Gauss's law) |
| Two-term hinge + Poisson interior | REFUTED | plateau true but not binding; descent can't find feasible states that exist by counting |
| Fixed-step stiff-barrier descent | REFUTED | bang-bang; Armijo fixed numerics but not the wall |
| Realized-demand congestion charge | REFUTED | realized state satisfies capacity by construction; only proposal demand signals |
| History/multiplier memory terms | REFUTED twice | inert where a fresh present term covers the job (in minorminer AND in our field) |
| Over-solving the coarse model (geo_iters>1) | REFUTED | the coarse model is calibrated only near the last realized embedding |

## Fabric / wiring

| Idea | Verdict | Why |
|---|---|---|
| Course-resolved Zephyr adapter (courses=True) | SHIPPED | the fold made real lanes unclaimable and under-provisioned arms 2×; representation, not law |
| Wire-exact post-hoc matching | PARKED | coupler-blind layouts admit no perfect assignment; existence, not optimization, is the problem |
| Coupler-aware coloring / coupled scoring | REFUTED (0-for-4) | metric saturates; superseded by exactness on junction-complete fabrics |
| restrict_chains fork patch | SHIPPED | stock hang = leaky AND-mask + unbounded parent walk; fixed at byte-parity |

## State representation (v4)

| Idea | Verdict | Why |
|---|---|---|
| Order state (two orders; positions = derived readout, s3.76) | SHIPPED (default; Max 2026-08-08) | true-objective linear DP replaces displacement packing; turán 6.02 at 10 seeds ≈ the constructive optimum; lattice block falls (honeycomb 1.09, king 1.53); largest Pegasus movement ever (K100 −1.87, all three P16 cells win); expanders pay +0.16/+0.40 — but ER is not order-free (variance clusters; ideas §3) |
| Occupancy footprint in order-mode books | SHIPPED (inside order_state) | zero-width arms are census-invisible (line_depth: touching = disjoint) → free total collapse on the no-snap path; a bar occupies its tile — width-floor b=a+1, no-op under snap |

## Polish / rerouting

| Idea | Verdict | Why |
|---|---|---|
| Ball v3 (obligation-hull questions, constant-free, s3.83) | SHIPPED as selector; ladder claim REFUTED | completeness achieved (every chain asks every pass; cliques self-gate free) but ball-first still blights liquids (ws +1.68, max 10→22) — asking is not answering: sum-optimal blight admits no sum-improving repair; the damage is objective-level |
| Re-asked descent (mm's tie/order randomization at ball scale, s3.82) | REFUTED | ball-rng ≈ deterministic ball on every basin cell (turán 6.63 vs 6.61; ws 4.14 vs 4.13) — randomizing a confined fixed question set explores the confinement; mm's edge = randomized interrogation × global relocation at single-chain granularity |
| tail="ball+mm" (ball BEFORE the grind, s3.80) | REFUTED | ball's greedy descent traps the grind's basin (turán +0.59@10 seeds, ws +0.87 with max chain 11→22); free-polish doctrine generalized: nothing runs before the polish that narrows its basin |
| tail="mm+ball" (grind first, ball after) | SHIPPED (default, s3.81) | wins or ties every board cell at equal budget, zero regressions, max chain never worse (ws −0.35 with max 11→9.3); the grind keeps its free basin, ball harvests what it cannot see |
| Bar-based ball rebuild + router fallback (s3.77) | SHIPPED (default arm) | >= router on every probe cell; bars harvest quick wins ~30x faster, router restructures; requires require_free coloring + only=-scoped completion |
| Bars-only ball rebuild | REFUTED standalone | near-zero accepts off turán; stride-1 corners are a ~56% junction coin without completion — sph_tree stays load-bearing |
| Ball polish (whole-chain composite re-embed, s3.75) | validated candidate | beats warm-started mm grind 17/26 at equal seconds on identical inputs (turán −1.45; first fabric-agnostic Pegasus wins); strict descent = never harmful; lattices unmoved (order-level residual, out of the move class by design); rebuild primitive is router-grade — stage 1 shares the bar constructor |
| Energy-plateau contraction stopping (contract_stable) | REFUTED | the plateau never fires: stair-E is monotone toward collapse, so the step count IS the repulsion — no honest internal stopping rule exists; 50-cap beat 16 on turán/spin_glass but lost K100 and still hurt P16; the fix is removing the continuous state, not re-knobbing it |

## Protocol / pipeline shape

| Idea | Verdict | Why |
|---|---|---|
| Multi-round feedback (re-derive from realized centroids) | REFUTED dense / PARKED sparse | rounds destroy insertion-found order |
| Region-biased polish | REFUTED | the placement must improve an UNCONSTRAINED polish or it wasn't real |
| Best-of-N by legal-stage ACL | REFUTED | legal ACL carries zero information about polished ACL (r ≈ 0) |
| Exactness gate as a decision bar | REFUTED | gate-as-trophy blocks outcome-improving flips; outcomes decide |
| Per-cell best-arm boards | REFUTED | the portfolio trap as a reporting convention |
| minorminer+busclique max as "an algorithm" | REFUTED by definition | the portfolio trap itself — the thing this project exists to not be |

## Parked, with unblock conditions

- **Adjoint transport** (`vcycle_transport`): needs the order-reality
  discriminator, derived from the merge certificate — not a gate.
- **Aggregation default** (`vcycle_agg`): validated at parity twice;
  awaiting owner call on the default flip.
- **bar_domains / restricted polish**: unblocked (fork patch works);
  its own round — the highest-EV route onto Pegasus.
- **Pegasus co-design**: revisit the stride gate; coupler-aware aiming
  on ~56% junctions is the exactness principle's generalization test.
- **Corridor / traversal pricing**: needs its own design round; naive
  reservation sabotages cliques.
- **Hard-frontier eval**: success-vs-budget curves and max-embeddable-n
  cliffs near capacity — the claim class that matters for replacement.
- **Crossing-parity-aware packing**: the exact packer trades turán's
  parity slack; named, undesigned.
- **Extents/dE/dd derivation**: unblocks the score self-entry, τ's
  retirement, h/v mass split, transport scale, and a Galerkin-consistent
  coarse energy at once. See ideas.md §3.
