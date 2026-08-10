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
| tail="ball+mm" (ball BEFORE the grind, s3.80) | REFUTED | ball's greedy descent traps the grind's basin (turán +0.59@10 seeds, ws +0.87 with max chain 11→22); free-polish doctrine generalized: nothing runs before the polish that narrows its basin |
| tail="mm+ball" (grind first, ball after) | named next | s3.75 measured ball-on-grind-output at 17/26 wins, never harmful; the equal-budget arm is unprobed |
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
