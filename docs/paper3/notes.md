# paper3 — lab record

Chronological, append-only. Numbering continues the house convention: paper2's record
ended at §3.31; experiments here are §4.x. Every experiment is pre-registered per
`protocol.md` rule 6. Prior records: `docs/paper2/notes.md` (factored),
`new-algorithm:docs/paper/` (paper 1, autopsied 2026-07-26 — see §4.0.2).

## 1. Mission

Beat stock minorminer 0.2.22 on **dense random graphs** (primary; MM's ecosystem role is
the structureless fallback), without regressing on structured (secondary). Metrics:
success rate (viability), mean ACL, cross-seed ACL variance, wall-clock.

**Thesis under test:** minor embedding has two regimes split by a measurable source-density
crossover p*(n). Below p*: search — sparse fixed-degree ER is bisection-limited, MM sits
on the optimal scaling law (§3.21), and only constants/variance/speed/feasibility are
available. Above p*: construction — every search method, MM included, lands 16–57% above
a constructive ceiling that a right-sized, source-trimmed clique template attains
deterministically in milliseconds, and MM's own polish cannot improve that construction
at all (§3.26). Deliverables: the first density-resolved crossover map (P16/Z12), and an
adaptive embedder that is never worse than MM anywhere and claims the dense regime.

## 2. Inherited evidence (anchors, all source-verified)

- §3.26 (factored): busclique K_n template restricted to source edges + spur-prune vs
  stock MM — K60 6.73 vs 7.83, K100 9.78 vs 13.62, K140 13.17 vs 20.72, biK48_96 6.21
  vs 6.68; MM full grind improves the template ≤0.04 ACL in 3–42 s. Never built as an arm.
- §3.21 (factored): ER at fixed avg degree 10 → ACL/n ≈ 0.057 flat over n=60–220 (two
  datasets); crossbar reused on ER(180, deg 10) = 13.87 vs MM 10.1. Sparse prize ≈ the
  constant only.
- Zbinden et al. 2020: CLMM (busclique chains → `initial_chains` → MM) wins success
  counts above p≈0.08 on Pegasus; embeds K185+ on P16 where MM fails at 175–180. ACL
  unmeasured. SPMM wins below 0.08.
- Ember paper (arXiv:2604.25433): MM ranks 1st on ER among 6 arms; results never
  density-resolved; PSSA (busclique-initialized SA) leads complete graphs (−13.9% vs MM).
- Paper-1 autopsy: best-of-12 stock-MM seeds = −4.8..−10% ACL (the ceiling probe);
  MM+spur-prune = −1.8% for ~2 ms. Hence protocol rules 2 and 3.
- MM anatomy (docs/paper2/mm-internals.md): shortening phase = 85–95% of wall-clock;
  `tries` = feasibility restarts (stop at first success); `threads` no-op;
  union-of-paths constructor is dead code (Steiner attach shipped); history/cost memory
  inert inside real MM (§3.13); `initial_chains` supported (pass source as GRAPH OBJECT
  — edge-list form drops isolated vertices).

## 3. Portfolio (specs in `proposals/`)

P1 ATE (adaptive template embedder — headline dense arm) · P2 CLMM++ (seeded search —
mid-band, feasibility frontier, literature control) · P3 portfolio/racer (equal
wall-clock race vs best-of-K-parallel MM only; demoted pending rank-stability probe) ·
P4 shortener economics (fork switches: short_audit, dirty_skip) · P5 symmetric polish
infra + joint-repair probe · P6 fork anatomy (union-vs-Steiner, Boltzmann root, finite
max_beta).

## 4. Experiments

### 4.0 Program setup (2026-07-26)

- 4.0.1 Branch `paper3` created off `factored` (strictly additive over main). Scaffold:
  protocol.md (constitution + frozen seed registries), this file, QUEUE.md, proposals/,
  survey.md, `ember_qc/algorithms/paper3/` auto-import subpackage (file-add-only for
  parallel worktrees).
- 4.0.2 Fairness rules derive from the paper-1 autopsy (best-of-K, one-arm polish,
  tune-on-test, seed-leak i=0 in the "disjoint" K=15 rerun). See protocol.md.
- 4.0.3 hyde06 provenance: EPYC 9575F, 64 physical cores / 128 SMT, 503 GB RAM, Debian,
  system python 3.11.2, uv at ~/.local/bin/uv, g++ 12.2.0, outbound HTTPS OK, no GitHub
  ssh key, $HOME 96% full → everything under /data/dabh/. Worker policy: ≤64 always;
  ≤48 for any run whose wall_time feeds a table; BLAS/OMP=1.
- 4.0.4 Salvaged from `new-algorithm`: `ember_qc/anneal.py` (SVMC + random Ising),
  solution-quality pipeline scripts (parked in `data/solution_quality/`), the
  ceiling-probe pattern (reimplemented as `e0_ceiling.py`).
- 4.0.5 hyde06 bring-up complete (2026-07-26): /data has 15 TB free; repo rsync'd
  (tracked files only — deploys are always of committed state); uv CPython 3.10.x venv;
  pins verified identical to local (networkx 3.4.2 / numpy 2.2.6 / scipy 1.15.3 /
  minorminer 0.2.22 / dwave-networkx 0.8.19); fork built, **parity OK**; instance-hash
  cross-check mac↔hyde06: `6bdf7fd108125ea3` == match; 210 MM-family contract tests
  pass. busgraph_cache warmed under /data/dabh/xdg: **P16 max clique = 180 (as
  expected), Z12 max clique = 184** — Zephyr's clique capacity exceeds Pegasus's despite
  fewer qubits (degree 20); cache builds were seconds, not minutes, on this host.

### 4.1 E0 — the density-resolved crossover map (2026-07-26)

PRE-REGISTERED 2026-07-26

Question: for each topology (P16, Z12), at which (n, p) does each strategy family win
(search=MM, seeded=CLMM, constructive=template/clique, alt-search=pssa/attraction/
cuthill), where is MM's feasibility cliff, and how much headroom above MM exists per
cell? The map ember's papers never drew (§3.21 measured one sparse diagonal; §3.26 four
dense anchors).

Script: docs/paper3/data/e0_crossover.py @ caf62119. Companion deflator:
e0_ceiling.py @ caf62119 (runs after dev-suite selection).

Cells / arms / seeds / budget: 109 cells (p ∈ {0.05..0.9} ladders + K_n anchors incl.
Z12 frontier rungs around max clique 184) × {minorminer, mmfork-cuthill, clmm, template,
clique, pssa, attraction} × 3 instances (seeds 101–103; K_n cells 1 instance —
instance-seed-independent) × 5 algo seeds (0–4; deterministic arms once) × 60 s.
≈8,235 rows. hyde06, 48 workers, BLAS/OMP=1.

Pre-registered decision outputs:
1. p*(n) per topology = smallest grid-p where `template` beats `minorminer` on the
   acl_spur column with ≥70% both-succeed win rate AND median paired ΔACL < 0, per
   n-ladder.
2. Headroom map: per cell, best-non-MM-arm median paired ΔACL_spur% vs MM.
3. CLMM verdict: does clique seeding beat stock MM 0.2.22 anywhere MM succeeds?
4. Feasibility-cliff table: per (topo, p), largest n with MM success ≥ 4/5.
5. Standing dev suite frozen by FIXED rule: per topology — the two cells straddling
   p* on the n≈100 and n≈140 ladders (4), densest feasible K_n anchor + one rung past
   MM's cliff (2), one sparse control (p=0.05, mid-n), one near-cliff mid-density cell
   (largest n with MM success 4/5 at p=0.2) → ≤16 cells total.

Bars / decision tree:
- **G1 (premise gate): at least one dense-random ER cell (p ≥ 0.2) shows ≥5%
  best-arm median headroom over MM → proceed to M2 builds. Otherwise STOP and rescope
  with the user before any algorithm code.**
- Template wins somewhere below p=0.9 → P1 ATE proceeds (KG1 pass). Never below
  p=0.9 → P1's ER claim dies; dense-structured/K_n story only.
- CLMM beats MM nowhere (ACL) → P2's ACL claim demoted to success/frontier only
  (its kill gate has a second chance at M3 with core-seeding variants).

--- results appended below; nothing above this line is edited after launch ---
