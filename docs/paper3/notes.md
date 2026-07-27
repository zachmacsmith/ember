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

RESULTS (2026-07-27; 8,235/8,235 rows, 0 watchdog kills / 0 crashes; acl_spur for
all arms per rule 3, dACL on both-succeed pairs per rule 4; analysis archived in
session scratchpad (e0_analysis.py), per-cell grid e0_cells.tsv; template==clique on
acl_spur in all 202 co-successes -> one constructive family, written "template"):

- **G1 PASS, decisively.** 32 dense-random ER cells (0.2<=p<=0.9) carry >=5%
  best-arm median headroom; top of the map: -31.8% (Z12 140@0.9), -30.7%
  (Z12 140@0.7), -28.7% (P16 140@0.7), all template at 15/15 wins.
- **p*(n) (output 1).** P16: n=40 <=0.7, 60 0.5, 80 0.5 (grid gap 0.08-0.5),
  100 0.3, 140 <=0.2 (left-censored), 160 0.12, 180 0.3. Z12: 40 0.9, 60 0.7,
  80 0.5, 100 0.3, 140 <=0.2, 160 0.12. No non-monotonicity anywhere. Crossover
  average degree p*(n-1) ~ 19-40, falling with n; Z12 sits one grid step denser
  than P16 at n<=60, identical from n=80. By n=140 the construction wins at every
  density MM survives.
- **Headroom (output 2)** is a ridge along the feasibility cliff: -5% at the
  crossover edge, -11..-19% at n=100, -20..-33% at n=140-180, peak P16 K140
  -33.4%. Template's level is density-FLAT (P16 n=140: 12.4-13.2 across
  p=0.2..1.0 while MM climbs 14.6->19.8; Z12 10.0-10.5 vs 11.7->15.1) — the
  dense headroom IS MM's density sensitivity. Below p* only attraction's sparse
  -1..-7% strip survives. **KG1 PASS**: template beats MM in 27 cells below
  p=0.9, down to p=0.12 (n=160, both topos; Z12 at 73% win rate).
- **CLMM (output 3): P2's ACL claim RETAINED.** clmm beats stock MM in 43/67
  MM-feasible paired cells — every paired cell with n>=80, p>=0.3, plus the
  mid-band to p=0.08 — up to -30.5% (P16 K140), 36/43 at 14-15/15 sweeps,
  2-4x faster than MM at n<=100 (full budget at n=140). Loses only sparse
  (21 cells, worst +1.11). Frontier: 12 cells where MM is 0-for-all and clmm
  embeds (P16 180@0.9, K180, 200@0.2; Z12 180@0.3-0.9, K179/K180/K184, 200@0.2,
  220@0.12 at 6/15).
- **Cliff (output 4).** MM's 60 s cliff is density-FLAT and topology-identical:
  n=140 at every p in {0.2..1.0} on BOTH topologies, rising only sparse (160 @
  0.12, 180 @ 0.08, 240 @ 0.05). P16 fades past it (180: 9/15@0.3, 1/15@0.7);
  Z12 dies outright (180: 0/15 everywhere; K140 already 4/5). The constructive
  family + clmm extend the dense frontier to the busclique bound — P16 180,
  Z12 184 = its max clique (K189 all-fail) — at BETTER ACL than MM on smaller
  graphs: Z12 K184 template 12.98 vs MM's own K140 15.09 (-14% on +44 vertices);
  P16 K180 16.64 vs MM K140 19.77. Zbinden's frontier reproduces on P16/Z12,
  now with the ACL axis Zbinden never measured.
- **Dev suite (output 5, FIXED rule): 14 cells, frozen in protocol.md.** P16:
  (100,0.2) (100,0.3) (140,0.12)+ (140,0.2) (140,1.0) (180,1.0) (160,0.05);
  Z12: (100,0.2) (100,0.3) (140,0.12)+ (140,0.2) (140,1.0) (179,1.0) (160,0.05).
  (+) the n=140 straddle-lo is left-censored and lands on grid-p 0.12, UNSAMPLED
  in E0 -> §4.1b pre-registers the two-cell baseline extension ((140,0.12) and
  (140,0.08), both topos) rather than swapping cells. Near-cliff-at-0.2
  duplicates (140,0.2) on both topos (merged).
- Context arms: pssa == template ± light SA polish (identical medians in most
  shared cells, better in 5 small-n cells by ~0.1; 0.45 s median; inherits the
  n<=maxclique wall and the sparse losses) — consistent with the thesis: its
  wins ARE the template's. attraction owns only the sparse strip (22/61 paired
  cells, to -6% at p=0.05, incl. a 15/0 sweep at Z12 160@0.05) and is the slow
  arm (32 s median success, failures to 89.0 s, dense collapse by n=140).
- Data quality: (i) **mmfork-cuthill fails in <30 ms on exactly the 3
  DISCONNECTED instances** ((100,0.05) seeds 101/102, (80,0.08) seed 102, both
  topos) — stock MM embeds them 15/15; fix before M3 (cuthill is a control
  arm). (ii) 465 failure rows overran 60 s (max 89.0 s; watchdog never fired).
  (iii) rule-3 sensitivity: 19 cells flip best-arm raw-vs-spur (pssa's unpruned
  output flatters it: prune gain mm 0.73 vs pssa 0.12 ACL); 6 crossover-edge
  cells flip a beats-MM verdict; p* moves one grid step on 3 ladders under raw.
  The pre-registered spur column stands. (iv) 103 INFEASIBLE = template/clique
  at n > max clique, by construction; 30/109 cells all-arms-fail.
- M3 design note: above p* at n~100-140, clmm and the raw template CONVERGE to
  the same medians (P16 100@0.9: both -2.24 — 60 s of seeded search adds nothing
  the template lacks). ATE's job above p* is to BE the template; clmm's marginal
  value is speed at n<=100, a hair of polish at the K_n frontier (Z12 K179:
  12.953 vs 12.978), and the n>maxclique overflow band (200-220).

### 4.1b E0 extension — the unsampled n=140 straddle (2026-07-27)

PRE-REGISTERED 2026-07-27

Question: baseline the two unsampled cells the dev-suite rule needs — (140, 0.12)
and (140, 0.08) on both topologies — same arms/seeds/budget as E0. Also determines
whether p*(140) is even lower than 0.12 (the n=160 ladder says 0.12 is winnable).

Script: docs/paper3/data/e0_crossover.py with the two cells appended to the grid
@ f04a4115, run with --resume against the E0 CSV (only new cells
execute; resume keys verified exact-match in the E0-author's validation).

Bars: none (baseline extension of §4.1; the §4.1 decision rules apply verbatim to
the new cells). Runs on hyde06 after e0_ceiling per QUEUE.md.

--- results appended below; nothing above this line is edited after launch ---

RESULTS (2026-07-27, 324 rows appended to e0_crossover.csv):

- **p*(140) ∈ (0.12, 0.2] on BOTH topologies** — template at (140, 0.12): P16 median
  +0.51 (2/13), Z12 +0.61 (1/14) = loses; at (140, 0.2) it wins 15/15 (§4.1). The
  dev-suite straddle pair is real and fully baselined; the left-censoring is resolved.
- (140, 0.08): all constructive arms lose big (template +2.6..+3.2); attraction wins
  small (−0.24 P16 / −0.06 Z12) — the sparse strip persists at n=140. MM 15/15
  everywhere in the extension.
- Mid-band interpolation confirmed at n=140: **clmm still beats MM at (140, 0.12) on
  P16** (median −0.46, 10/5; Z12 neutral +0.04) — seeded search extends the win region
  below the raw-template crossover, the P2 mid-band role in one number. cuthill −0.44
  (10/5) there too (its fixed-order effect is alive on mid-band).

**e0_ceiling RESULTS (2026-07-27, 1,000 rows; the rule-2 deflator, measured at equal
wall-clock on the frozen dev cells — supersedes the paper-1 tiny-cell probe):**

- **The best-of-K freebie largely does not exist at equal wall-clock.** Sparse
  (160, 0.05): bo3/bo6/bo12 = −0.32/−0.43/−0.32 spur (real but small — the one
  regime where restarts are nearly free, consistent with §4.2's q1-convergence).
  Mid-band (100, 0.2/0.3): bo3 ≈ −0.2, bo6/bo12 ≈ 0 to +0.3 (splitting starts to
  hurt). (140, 0.2): ALL best-of-K arms WORSE (+0.29..+1.36 spur, bo6 0/24 wins) —
  the long grind wants contiguous time. Dense cliff: P16 K140 bo12 gains on raw
  (−2.7 spur) but only by BURNING 137 s vs 59 s (MM's cooperative timeout overshoots
  ~2.2× per 5 s slice — equal-wall-clock best-of-K is not even achievable there);
  Z12 K140 is unambiguous: bo-K loses +1.8..+4.1 spur with 10/25 failures at bo12,
  despite 143 s. Restarting at the cliff destroys the one continuous grind that works.
- Paper-1's −4.8..−10% ceiling-probe number came from n=20–40 toy cells with
  full-budget (unequal-time) restarts; it does NOT transfer to real cells at equal
  wall-clock. Consequence for rule 2: the strong MM configuration at 60 s is mostly
  the SINGLE run; bo-K is the binding control only on sparse cells (and the parallel
  variant for the racer). Our dense margins (−11..−33%) tower over any restart
  freebie by an order of magnitude.

### 4.2 Rank-stability probe — the P3 gate + P4 patience curve (2026-07-26)

PRE-REGISTERED 2026-07-26

Question: does ACL early in MM's polish predict final ACL across seeds of the same
instance? §3.16 killed selection on LEGAL-stage ACL (r ≈ −0.01); this asks whether
selection on EARLY-POLISH ACL works instead — the gate for P3's successive-halving
racer. The same trajectories give P4's patience/diminishing-returns curve.

Script: docs/paper3/data/p3_rank_stability.py @ bf1a9713. Host: local mac, 8 workers
(gate is a within-run correlation; absolute seconds are mac-specific and feed no
cross-arm table — P4's Pareto re-measures on hyde06).

Cells/seeds/budget: ER (n,p) ∈ {(100,0.1), (140,0.2), (100,0.5)} × instance seeds
{101,102,103} × 16 algo seeds; per (instance,seed): legalize (patience=0, ≤8 s) then
8 warm-restart polish quanta × 7 s; terminal spur row extra.

Bars / decision tree:
- **P3 gate: median per-instance Spearman ρ(acl_best@q4, acl_best@q8) ≥ 0.5 → the
  racer proceeds (build late in M2). ρ < 0.5 → no racer**; portfolio.md demoted to
  plain heterogeneous measurement at M3 (pre-declared).
- P4: no bar — the per-quantum improvement shares are design input for short_audit's
  time-matched Pareto.

--- results appended below; nothing above this line is edited after launch ---

RESULTS (2026-07-26, 144/144 trajectories complete, 0 legalize failures):

- **GATE PASS.** Spearman ρ(acl_best@q4, acl_best@q8) per instance: median **+0.885**,
  9/9 instances ≥ 0.5 (range +0.53..+0.96); pooled instance-centered ρ@q4 = **+0.876**
  (p ≈ 1e-46, N=144). Even q1 pools at +0.72. Correlation to the terminal-spur column
  ρ(q4, spur) = +0.52..+0.95 per instance. **The racer is unlocked** — selection on
  early-POLISH ACL works precisely where legal-stage selection was dead (§3.16
  r ≈ −0.01): the basin's quality becomes visible after one quantum of grind.
- **P4 patience readout:** improvement share by quantum is regime-split — sparse
  n=100 p=0.1: q1 = 87.9% of the total drop (cumulative 96.5% by q3); dense n=100
  p=0.5: q1 = 34.6% and q8 still adds 11.4% (not converged at 64 s); n=140 p=0.2
  in between (q1 46.7%). Stock MM's uniform patience misallocates: sparse should
  stop early, dense should grind longer. Terminal spur is worth another −0.13
  (sparse) to −1.8 (dense) ACL on top of q8 — large on dense, reinforcing rule 3.
- Caveat: 20/144 trajectories show raw q1 > legal ACL (worst +3.03) — raw
  per-quantum ACL is not monotone under warm restart (MM's passes wander before
  improving; acl_best is monotone by construction and is what the gate uses).
  Warm-start integrity itself is confirmed (q1 chain-overlap Jaccard 0.14–0.95 vs
  ~0.001 for a re-init; smoke had 3/3 q1 ≤ legal).
- Data: p3_rank_stability.csv (1,440 rows), summary in p3_rank_stability_summary.txt.
  Decision per pre-registration: build the P3 racer (late-M2), baseline
  best-of-K-parallel stock MM per protocol rule 2.

### 4.3 P5b-dense: the K60 pair-move probe — the ceiling is not tight (2026-07-27)

Pre-registration and full results live in `proposals/polish.md` (kept there during the
parallel worktree wave; this entry is the lab-record pointer). Script
p5_k60_pairmoves.py @ 2e06a7f6, run @ 4e748890, deterministic, local mac, 27.6 min.

**Verdict: the pre-registered negative is FALSIFIED.** On the exact §3.26 instrument
(busclique K60 + spur-prune, 404 qubits, ACL 6.7333): x1 exact single-vertex repair
improves 2/60 vertices (proven); x2 joint pair repair improves **103 of the first 400
pairs** (94×−1 qubit, 9×−2; 71 proven pair-optimal), and **58 pairs improve where BOTH
endpoints are proven single-move stuck** (radius up to 4) — the partner chain relocates
laterally at unchanged length to free the needed qubit. Genuine joint-move blindness,
exhibited with validity certificates. Caveats: 62% of x2 searches unproven under the
5 s cap (weakens only negatives); sweep truncated at 400/1770 by the pre-registered
rule (only ADDS unfound moves). Premise correction: spur-prune is NOT a no-op on K_n
(busclique leaves coverage-redundant qubits: 4 at K60/P16); §3.26 anchors unaffected.

Two-sided reading (recorded verbatim in polish.md): (a) the constructive ceiling is
not tight — an exact-repair polish stacked on the template lowers it further,
strengthening P1; (b) none of this rescues MM: its move set still cannot find these
moves (§3.26) — the missing move class is now exhibited, not inferred.

### 4.4 K60 exact-move fixpoint — how far does the ceiling move? (2026-07-27)

PRE-REGISTERED 2026-07-27

Question: the sequential achievable gain on the K60 template under anytime_polish
(spur/shorten/x1/x2, longest-first, deterministic) — the ceiling-shift number §4.3
could not provide (moves measured from the same base are not additive).

Script: docs/paper3/data/p5_k60_fixpoint.py @ 50479b69. Local mac,
deterministic, 30-min deadline, no wall-clock claims (measurement, not a race).

Bars: none (measurement). Decision: the fixpoint ACL becomes the template+polish
reference line for P1's M3 bars and the paper's ceiling discussion; if the gain is
≥ ~0.1 ACL, `p3-template` grows an optional exact-polish stage (flag, default TBD at
M3) — evaluated under the same 60 s budget discipline as everything else.

--- results appended below; nothing above this line is edited after launch ---

RESULTS (2026-07-27): **404 → 394 qubits, ACL 6.7333 → 6.5667 (−0.1667, −2.5%),
valid.** Wall 1800.2 s — the run is DEADLINE-BOUND, not converged: 6.5667 is an upper
bound on the K60 template+polish ceiling, and the §4.3 caveat (unproven negatives,
unswept pairs) means further gains may exist. Decision rule fires (≥0.1 ACL):
`p3-template` gets an optional exact-polish flag at M3, but the ECONOMICS are the real
finding — 30 min of exact repair bought −2.5%, so under the 60 s discipline only a
slice is capturable; the flag's M3 evaluation must use the 60 s budget, and the
full-depth number belongs to the ceiling discussion, not the product arm. Updated
regime picture: MM@K60 7.83 (§3.26) / template 6.73 / template+exact-moves ≤ 6.57.

### 4.5 M3 dev-suite kill gates (2026-07-27)

PRE-REGISTERED 2026-07-27. Script: dev_suite.py @ 94d5e046. Frozen dev suite
(protocol.md) × arms {minorminer, mmfork-cuthill, p3-template, p3-ate, p3-clmm,
p3-clmm-core, p3-mmpolish, pssa, attraction} × inst seeds 101–105 × algo seeds 0–4 ×
60 s; hyde06 ≤48 workers; acl_spur; paired vs minorminer AND vs p3-template.
Bars (per the drafted blocks in proposals/{ate,clmm,polish}.md, applied verbatim):
- P1 (p3-ate): median paired dACL_spur <= -2% vs MM on >= half the dev cells with
  p > p* ((100,0.3), (140,0.2), K140, past-cliff feasibility), AND never worse than
  MM (median) on any below-p* cell. Fail -> ATE demoted to p3-template-only arm.
- P2 B1: >=1 mid-band cell ((100,0.2), (140,0.12)) with p3-clmm paired win (here:
  median < 0 and >=60% win rate; Wilcoxon at M4 scale). B2: p3-clmm-core beats
  p3-clmm anywhere (ACL or success). B3: frontier cells report-only.
- p3-mmpolish: beats minorminer (its own base + polish) by median < 0 on >=2 mid
  cells at equal 60 s — else the mid-band polish claim dies (K_n side settled
  §4.3/4.4).
- Context arms report-only. Success rates separate/unpaired everywhere.

### 4.6 M3 racer vs rule-2 baselines (2026-07-27)

PRE-REGISTERED 2026-07-27. Script: m3_race.py @ 94d5e046. Cells P16/Z12 (100,0.2),
(100,0.3), (160,0.05); inst 101–105 × base seeds 0–4 × 60 s; modes (a) p3-race8
sequential (b) best-of-8 sequential (c) best-of-8 PARALLEL (8 cores, seed-matched to
b) (d) race parallel (8 cores). hyde06 --outer-workers 5 (~41 procs). Bars: the
racer claim = (a) beats (b) [1-core fairness] AND (d) beats (c) [8-core fairness] on
median paired dACL_spur on >=2 of the 4 sparse/mid cells; on (100,0.3)
template-floor wins are expected and excluded from the selection claim
(winner=template rows analyzed separately). Fail -> P3 ships as systems observation
(§4.1 ceiling already shows bo-K weak); variance/anytime/success-union reported
regardless.

### 4.7 M3 shortener Pareto (2026-07-27)

PRE-REGISTERED 2026-07-27. Script: p4_pareto.py @ 94d5e046. Cells P16 ER(180,0.1),
ER(180,0.3), ER(140,0.2); inst 101–105 × algo seeds 0–4; budgets {5,15,60,180} s;
arms {stock, short_audit=1, short_audit=2+j3, dirty_skip=1} via fork
(fallback=False). Bar (shortener.md draft, verbatim): a switch survives iff at >=1
budget it wins median paired dACL_spur with >=60% both-succeed win rate, or
|d|<=1% at <=0.5x stock wall (within-batch walls; headline re-measured workers=1
idle). Stock dominates everywhere -> P4 dies, patience curve ships as anatomy.
Prediction (committed): audit=1 dies on ACL; audit=2 survives via the speed clause
at small budgets; dirty survives at >=60 s.

### 4.8 M3 anatomy probes P6a/b/c (2026-07-27)

PRE-REGISTERED 2026-07-27. Script: p6_probes.py @ 94d5e046. Cells: deg-10 ladder
n∈{60,100,140,180} + ER(100,0.3) + ER(140,0.3) (+ (140,0.2) as the near-cliff cell
for P6c — substituted for the draft's ER(260,0.2), outside the feasible set per
§4.1 output 4). Arms: stock; chain_tree∈{1,2}; root_boltzmann∈{0.5,2,8};
max_beta∈{2,16,dhat}. Predictions (committed, from anatomy.md): stock beats union
by a few % ACL; sph-pure ≈ stock; Boltzmann null at T<=2; finite beta worse on
feasibility near the cliff, ≈null on ACL where both succeed. Report-only; any arm
beating stock by >=1% median escalates to a 15-seed confirm before any claim.

### 4.9 M3 assignment honesty gate KG2 (2026-07-27)

PRE-REGISTERED 2026-07-27. Script: p1_kg2.py @ 94d5e046, local run (template-side
only, ~minutes). Cells: the 6 template-win dev cells. Per instance: identity,
cuthill seed, spectral seed, shipped 2-swap, 32 random assignments (prune-only,
uniform). AMENDED KILL RULE (sharpened BEFORE launch — the drafted rule assumed the
random oracle bounds the shipped pipeline; the build smoke showed shipped BEATING
best-of-32-random, which must not fire a kill): the 2-swap optimizer dies iff
max(shipped, best-of-32-random) gain < 2% over identity; if shipped >= 2% it lives
regardless of the random oracle; seeds-only replaces it iff best-seed >=
shipped - 0.5%. KG3 note: the E0 map answers the escape probe observationally
(pssa ≈ template ± <=0.1 on shared dense cells, §4.1) — recorded as subsumed.

--- results appended below per experiment; nothing above edited after launch ---

§4.9 RESULTS (2026-07-27, 792 rows, local, deterministic): **the 2-swap assignment
optimizer LIVES.** gainship (shipped pipeline vs identity, prune-only ACL): P16
(100,0.3) +4.6..+4.8% / (140,0.2) +3.6..+4.8%; Z12 (100,0.3) +3.7..+4.3% /
(140,0.2) +3.6..+4.8%; K_n cells exactly +0.00% (assignment-invariant control
confirms the instrument). best-of-32-random reaches only +0.6..+1.8% — the shipped
optimizer beats the random oracle by 0.24..0.47 ACL everywhere; the ORIGINAL drafted
rule (kill if oracle < 2%) would have killed a working optimizer and is superseded by
the §4.9 amended rule committed before launch (the script's printed READ1/READ2 lines
apply the old rule — disregard them; the CSV is authoritative). Seeds-only capture
(+2.9..+3.6%) is 1.0–1.3 pp short of shipped → seeds do not replace the 2-swap.
Scientific note: even dense RANDOM graphs carry ~4–5% of assignment-exploitable
structure (degree fluctuations + local edge patterns) — the "no latent structure"
intuition from §3.21 applies to placement geometry, not to slot assignment.

§4.5 RESULTS (2026-07-27, 2,214 rows, hyde06 48W; full table dev_suite_summary.txt):

- **P1 p3-ate: PASS, overwhelming.** Above-p* cells all won at 20-25/25: P16
  (100,0.3) -16.8%, (140,0.2) -19.3%, K140 -33.5%, (140,0.12) -4.7% (23/1); Z12
  (100,0.3) -15.2%, (140,0.2) -17.6%, K140 -30.6%, (140,0.12) -3.6% (22/3), plus
  (100,0.2) -4.4% both topos. Sparse control (160,0.05): EXACT tie with MM 0.000
  (0/0/25 both topos) — the never-worse auto-select verified live (winner=mm there;
  winner=template above p*, ties p3-template to the third decimal). Frontier: K180/
  K179 5/5 at 16.64/12.97 where MM+cuthill+attraction are 0/5.
- **THE STRADDLE FLIP — assignment moves p* itself.** At (140,0.12), where the naive
  identity-assignment template LOSES (§4.1b: +0.51/+0.61), the shipped ATE template
  (KG2's 2-swap assignment + trim) WINS: P16 -0.529 (-4.7%, 23/1), Z12 -0.322
  (-3.6%, 22/3). The §4.9 assignment gain (+3.6..4.8%) is exactly the flip margin:
  **ATE's crossover sits BELOW the naive template's p*(140) in (0.12, 0.2]** — the
  product widens the dense regime beyond the construction that defined it.
- **P2: B1 PASS** — mid-band paired wins P16 (100,0.2) -4.7% (20/5) and (140,0.12)
  -2.9% (16/9). Topology asymmetry: the same cells on Z12 are +2.8% (7/18) and +0.4%
  (12/13) — clmm's mid-band edge is Pegasus-specific at n=100-140; report as-is.
  **B2 PASS** — clmm-core beats clmm at (140,0.2) on BOTH topos (-15.0 vs -12.9;
  -14.9 vs -12.4) and ties-or-beats at K_n; but core BACKFIRES at (140,0.12)
  (+5.0/+5.6% vs clmm's -2.9/+0.4) — core-seeding is a dense-side tool; regime-gate
  it. **B3**: K179 clmm 12.961 vs template 12.972 (4/0/1) — seeded polish shaves a
  hair off the template at the frontier, again.
- **p3-mmpolish: PASS.** Median < 0 on ALL 10 MM-feasible ER cells, win rates
  18-25/25 (typical -0.5..-1.2%): the exact-repair polish is a small, near-universal
  free improvement on MM's own output in the search regime. It does NOT help at the
  cliff (P16 K140 +3.0% — the 30% budget reservation costs more than repair returns;
  K179/K180 fail with their base). Product shape: mid/sparse-band add-on.
- Context: attraction wins the sparse control (-4.3% 21/3 Z12; -2.8% 17/8 P16) and
  Z12 (100,0.3) (-2.1%) — the sparse specialist as mapped. pssa collapses sparse
  (+79..+86%). cuthill: -1.6..-3.7% mid-band; K140 split by topology (P16 -6.2%,
  Z12 +4.2%, n=4-5 — noisy at the cliff).
- Ops: Z12 K140 MM 4/5 (cliff-edge flakiness, matches E0); attraction 0/5 on all
  K_n cells at 70-81 s (cooperative overrun, watchdog never fired); all other arms
  100% success on MM-feasible cells.

§4.7 RESULTS (2026-07-27, 1,200 rows): **P4 dies in substance.** dirty_skip produces
byte-identical ACL everywhere (med d exactly +0.000, no wall saving: 40.9 vs 40.8 s —
skips fire only in the failing tail, which is a negligible share at these scales).
audit2 +1.6..+2.6% worse at every substantive point; audit1 +1.8..+4.9% worse except
one 4-pair cell ((180,0.3)@15 s: -0.72%, 3/4 wins) where the win-clause TECHNICALLY
fired — we decline the claim (4 pairs is below any evidential floor; pre-registration
lesson recorded: bars need minimum-pairs floors). The §3.17 fixed-wall-clock bet
LOSES: cheaper auditions do not buy compensating sweeps — the exhaustive audition is
load-bearing for polish quality (its cost is the accuracy, matching the M2
micro-timing). Registered arms stay for the anatomy section only.

Two anatomy findings worth the run: (i) **stock MM converges before its budget on
mid cells** — wall median 40.8 s at BOTH 60 s and 180 s budgets on (140,0.2) (22.3 s
on (180,0.1)): patience expires and MM leaves budget on the table; (ii) **the
feasibility cliff is budget-dependent**: (180,0.3) success 0/25 → 4 → 14 → 23/25
across budgets 5→180 s — E0's "density-flat cliff at n=140" is a 60 s statement, and
frontier claims must state their budget (time-to-first-legal is the right axis).

§4.8 RESULTS (2026-07-27, 1,450 rows): predictions confirmed on two of three fronts,
one genuine surprise thread on the third.
- **P6a (tree): stock's filtered nearest-attach Steiner is the best of the three**,
  as predicted. union +1.7..+7.9% worse; pure-SPH catastrophic on dense (+15.7% at
  (140,0.3), 0/25 wins) — the refcount>1 attach filter is load-bearing exactly where
  chains are long. (2014-paper union at deg-10 n=100 is a wash, -0.17%.)
- **P6b (Boltzmann root): null-to-worse**, as predicted (T=8 clearly worse on most
  cells; scattered weak -1.4..-1.9% blips at one cell are inside the multiple-
  comparison noise floor; included in the §4.8b confirm anyway per the tree).
- **P6c (finite beta): the surprise.** beta=2 ANNIHILATES feasibility (0/25 on
  nearly every cell; 4/25 at n=60) — lexicographic overlap pricing is load-bearing
  for viability, prediction confirmed with dramatic effect. BUT **beta-dhat — the
  2014 paper's own D^occ spec — BEATS the shipped pricing on sparse deg-10 cells**:
  -0.9% (n=60), -2.97% (n=100, 16/9), -2.23% (n=140, 18/7), -4.79% (n=180, 16/5 at
  21/25 success), and beta-16 -1.52% at n=180; while failing outright on dense
  (0-1/25 at p>=0.2). Reading: the shipped program's abandonment of the paper's
  finite-beta pricing bought dense feasibility and PAYS 2-5% ACL on sparse — a
  regime split inside MM's own cost function, and a sparse-regime lever where §3.21
  located only "the constant". Wall cost: beta-dhat converges slower (14-33 s vs
  6-16 s stock at 60 s budget — same budget, so the ACL read is fair).

### 4.8b P6 surprise confirm — 15-seed re-test (2026-07-27)

PRE-REGISTERED 2026-07-27. Per the §4.8 decision tree: every arm flagged < -1%
median re-runs at 15 algo seeds before any claim. Script: p6_probes.py --confirm @ 9bec9817 (flag added per the escape clause)
mode = cells {deg-10 n in {100, 140, 180}} x arms {stock,
tree-sph, boltz-2.0, boltz-8.0, beta-16.0, beta-dhat} x inst seeds 101-105 x algo
seeds 0-14 x 60 s (if the script lacks a --confirm flag, an equivalent explicit
cell/arm/seed invocation or minimal flag addition at a fresh sha is permitted and
recorded here). Bars: a surprise CONFIRMS iff median paired dACL_spur < -1% with
>=60% win rate at 15 seeds on the same cell; beta-dhat additionally reports success
separately (21/25 at n=180 in §4.8). Confirmed beta-dhat -> the anatomy section
gains the "paper-vs-program pricing regime split" claim and a candidate follow-up
(density-gated beta inside ATE's search arm — NOT built at M3). Unconfirmed -> noise
paragraph.

--- results appended below; nothing above this line is edited after launch ---
