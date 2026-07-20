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
  *polishes* it (warm-started grind). This is the multilevel method of partitioning/
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

Pipeline per call:

1. **Init**: spectral layout of H scaled into the middle 80% of the target's drawing
   coordinates (`pegasus_layout` etc.); circle fallback for degenerate spectra
   (complete/tiny/disconnected graphs). No router call, no MM basin as anchor.
2. **Geometry** (per outer round): `geo_iters=10` steps of Laplacian attraction
   (η=0.5 toward neighbour-centroid mean) + binned density push (auto ~16×16 bins;
   capacity = working qubits/bin; charge = per-variable realized chain length from
   the previous round, else λ₀=3; overfull bins push toward the least-pressured
   8-neighbour, step scaled by overflow).
3. **Snap**: variables claim distinct nearest qubits, high degree first.
4. **Routing**: stock MM seeded cheap legalization (`initial_chains` singletons,
   `chainlength_patience=0`).
5. **Feedback**: spur-prune, read realized centroids + per-variable chain lengths
   back; repeat from 2 (`outer_rounds=3`), keep the best round by legal ACL.
6. **Finish**: stock MM full grind warm-started from the best round
   (`skip_initialization`), unconstrained.

Magic numbers, none swept: η=0.5, λ₀=3.0, outer_rounds=3, geo_iters=10, bins≈16,
γ=0 (region bias off by default; >0 is the refuted ablation arm).

## C. Idea ledger

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

### Unvalidated regressions in v3 (top priority to resolve)

Three changes were made together, none measured one-at-a-time (violates house
rules; flagged 2026-07-17):

1. Spectral init replaced v1's MM round-0 (also removed its basin anchor).
2. `geo_iters=10` inner steps per router call replaced v1's one-step-per-feedback
   cadence — ten unchecked attraction steps largely erase the previous round's
   realized geometry and re-derive a capacity-limited blob each round; the feedback
   loop that §3.19 showed was doing the work is mostly disconnected.
3. 3 outer rounds replaced v1's 10.

Single-cell probe hints at a cost (6.16 vs v1 ≈ 5.95 at n=100). Needs a proper
ablation: {init} × {cadence} × {rounds}, paired, before any conclusion about the
family is drawn from v3's numbers.

### Known operational weaknesses (cheap fixes first)

- **Budget structure**: every internal call gets `timeout=remaining`; a hard
  instance can burn the whole budget in round 1, leaving the polish scraps →
  predicted success-rate deficit at the hard tail vs stock MM's single integrated
  60 s attempt.
- **Correlated attempts**: our 3 rounds start from nearly identical geometry; MM's
  `tries` are independent. Bad placement fails three times. Also: seeded
  legalization from *bad* anchors can be slower than unseeded (§3.10
  anti-placement lesson).
- **Vestigial selection**: "best round by legal ACL" survives despite §3.16.
  Alternatives: last round, or briefly polish top-2–3 and race (successive
  halving).
- **Disconnected sources**: spectral layout degenerates; components may stack.
- **Proxy metric**: drawing coordinates ≠ hop distance on Pegasus (long wires);
  error largest at snap resolution.

### Parked / next (ordered; one switch at a time)

1. Budget fix (per-phase caps or fractional split).
2. Selection fix (drop legal-ACL best-round).
3. Cadence/rounds/init ablation (restore v1's validated dynamics as the control
   arm).
4. **Tile-graph coarse target**: replace uniform layout bins with the hardware's
   canonical coarsening (Chimera = grid of K4,4 tiles; Pegasus/Zephyr unit cells);
   capacity = working qubits per tile; coarse *edges* get capacities from actual
   inter-tile coupler counts (current field models node capacity only).
5. **Mass + shape charges**: smear each variable's λ along its expected chain tree
   instead of a point deposit (fixes the dense-regime monopole lie cheaply; the
   full particles-per-qubit model is the expensive limit).
6. **Continuous long-range density**: ePlace-style Poisson/electrostatic field or a
   capacitated-transport solve, replacing one-bin local pushes — fixes the plateau
   problem (interior of a uniformly overfull region currently cannot move; only the
   rim peels). Max's "real-valued centroids drifting under continuous repulsion".
7. Native-arm speed (only if the purity arm earns investment): BFS instead of
   heap-Dijkstra at uniform prices; `targets=` early-exit in
   `weighted_multisource_dijkstra`; region-bounded searches.

### Predictions on record — full-Ember sweep of 2026-07-17

(attraction hybrid v3 vs stock minorminer, ~24k P16-eligible graphs, 60 s, shared
seed; score these when results land)

- Small n (bulk of library): ACL ties, wall-clock worse but sub-timeout.
- Mid-size structured (grids/planar/lattices): best chance of genuine ACL wins.
- Mid-size random/expander: parity to slight loss.
- Dense (complete/dense bipartite): theoretically winnable, expected blunted to
  ~parity by the density-field plateau problem.
- Hard/near-capacity tail: measurable success-rate deficit (budget structure +
  correlated rounds), the most damaging and most fixable predicted loss.
