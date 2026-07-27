# Literature synthesis — minor embedding for quantum annealers

Seeded 2026-07-26 from the kickoff research sweep; expanded during M1 by the survey
fan-out. Each entry: what it does → what paper3 takes from it.

## The incumbent

- **Cai, Macready, Roy 2014** (arXiv:1406.2741) — the CMR heuristic; minorminer's paper.
  **Do not trust as a description of the shipped program**: shipped 0.2.22 uses a
  nearest-attach Steiner constructor (union-of-paths is dead code), an adaptive-base
  lexicographic overlap price (not diam^occ), per-pass reshuffled orders with five
  strategies, uniform-among-minima root choice (Boltzmann proposed, unshipped), and an
  undocumented shortening phase that consumes 85–95% of wall-clock. Full anatomy with
  file:line cites: `docs/paper2/mm-internals.md`. Paper-vs-program deltas are P6's subject.
- **minorminer.layout (p-norm)** — D-Wave's layout-aware wrapper (`minorminer-layout`
  arm, the documented practitioner default for geometric sources): layouts of S and T,
  p-norm placement, closest-qubit chains as `initial_chains`. On factored's grids it ran
  1.3× stock wall-clock; a baseline arm here, not a target.
- **minorminer.busclique** — polynomial clique/biclique embeddings on Chimera/Pegasus/
  Zephyr via `busgraph_cache`; right-sized `find_clique_embedding(n)`; also
  `largest_clique_by_chainlength(L)`. Minimizes MAX chain length (mean-optimality open —
  degree bound (n−1)/14 on P16 sits ~30% below busclique K180's 16.67). The engine of
  P1/P2.

## Direct competitors / prior art on our claims

- **Zbinden, Bärtschi, Eidenbenz, Djidjev 2020** (ISC, LNCS 12151): SPMM (spring-layout
  seeds) and CLMM (clique-chain seeds → MM). Pegasus: CLMM best above density ~0.08;
  only CLMM reaches K185+; SPMM best below. Success-count metric only; "running times
  very comparable"; **ACL never measured** — the gap P2 fills. Mechanistic insight we
  reuse: dense embeddings want long path-shaped chains (induced degree ≤2).
- **Ember paper** (arXiv:2604.25433, this project's `main`): 6 arms × 24k graphs ×
  C16/P16/Z12. MM ranks 1st on ER (rank 1.63) but **results are not density-resolved**
  (stated gap → E0). OCT-fast: −3% chains at 1/8 time when it succeeds (48.6%),
  Chimera-only. ATOM fast/worse. CHARME (reconstructed) 1.96× MM ACL. PSSA
  (busclique-init SA, tree mutations): leads complete graphs (−13.9% vs MM), weak on
  random. Clique: fastest, 2× chains overall.
- **Sugie et al. / Hitachi PSSA line** (arXiv:2012.02372 and predecessors): SA over
  whole embedding states with swap/shift moves. In-repo reimplementation = `pssa*` arms.
  P1's KG3 uses pssa-fast as the escape probe on the template.
- **ATOM** (arXiv:2307.01843): adaptive-topology growth, fast, Chimera-only binary in
  repo. **CHARME** (arXiv:2406.07124): RL chain construction; weak in ember's rerun.
  **RL embedding QMI 2026** (arXiv:2507.16004): same family, small instances.
- **SOTA evaluation** (arXiv:2504.13376 / FGCS 2026): confirms MM degrades with density;
  calls for hybrids; no density-resolved crossover map. PDF cached in session scratch.
- **Bipartite template framework** (arXiv:2504.21112): periodicity-exploiting K_{m,n}
  templates — bipartite-source specialists; adjacent to P1's biclique variant.
- **OCT-based embedding** (Goodrich et al.): odd-cycle-transversal virtual hardware;
  quality ≈ MM at 1/8 time when feasible; generalizing beyond Chimera is ember-paper
  future work, not ours.
- **4-clique network embedding** (PhysRevApplied 21, 034023): fixed 4-clique lattice
  minors for QAC-style robustness — different objective (per-chain redundancy), cite only.
- **Exact/IP approaches** (Bernal et al., CPAIOR 2020): tiny instances only; its
  single-block repair operator survives in P5b.
- **Broken-clique literature** (e.g. "Embedding of complete graphs in broken Chimera",
  QIP 2021): clique templates under faults — relevant to the faults evaluation axis;
  busclique itself computes on the actual (faulted) target.

## Synthesis → the gap paper3 claims

Construction wins dense (busclique/§3.26, CLMM success counts, PSSA-on-K_n) and search
wins sparse (§3.21, ember rankings) — but no published work (i) measures the crossover,
(ii) measures constructive ACL against search ACL under paired, budget-matched, polish-
symmetric, restart-controlled protocol, or (iii) ships the adaptive selector the two
regimes imply. That is E0 + P1/P2, with P3–P6 covering the sparse-side prizes
(variance/anytime, speed, anatomy).
