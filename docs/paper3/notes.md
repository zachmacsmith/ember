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

§4.6 RESULTS (2026-07-27, 600 rows, hyde06 outer5x8): **P3 racer bar PASSES on the
template-free cells — the selection claim is real.** On (160,0.05), where the
template never wins (race winners: mm 20-25, cuthill 1-4, clmm-core 0-1 of 25):
P16 seq -2.31% (84%) / par -5.57% (96%); Z12 seq -4.97% (88%) / par -7.53% (100%)
vs the seed-matched best-of-8 controls — both pre-registered fairness reads, both
topologies. Mechanism (honest): parallel best-of-8 stock MM finishes in 7.0-8.7 s
median (patience expires — the §4.7 budget-on-the-table finding) and the racer
converts the remaining wall-clock into ACL via warm-restart grinding of the best
basins; sequential racing additionally beats uniform 7.5-s slicing by adaptive
allocation. At equal wall-clock on equal cores, race8 beats the strongest stock-MM
multi-run configuration under MM's own stopping rules on 6/6 cells (mid cells
-1.9..-17.6% — but winner=template there 21-25/25, excluded from the selection
claim per pre-registration; the mid-band numbers are the ATE story wearing a racer
hat). Z12 (100,0.2) par read -1.86% at 76% misses the -2% bar — reported, not
claimed. Data: m3_race.csv.

§4.8b RESULTS (2026-07-27, 1,350 rows, 15 seeds): **beta-dhat CONFIRMS on all three
cells** — n=100: -2.62% (47/28/0 = 63%); n=140: -3.89% (65/10/0 = 87%); n=180:
-5.00% (53/11/0 = 83%) with success 64/75 (the feasibility cost is real and grows
with n; reported separately per rule 4). Claim (anatomy section): finite
diameter-scaled beta — the 2014 paper's OWN D^occ pricing spec — beats shipped
minorminer's lexicographic overlap pricing by 2.6-5% ACL on sparse deg-10 graphs,
at a feasibility cost that makes the shipped default the right GLOBAL choice; the
program's pricing trade has a measurable regime split. Candidate follow-up
(post-paper): density-gated beta inside the search arm. The other §4.8 flags
dissolve at 15 seeds: tree-sph 57% win rate (< 60% bar, n=100 only), beta-16 59%
(n=140 only), boltz-8 null; boltz-2.0 confirms exactly at the 60% bar on its single
cell (n=100, -2.27%) — recorded as a cell-specific curiosity, no claim.

**M3 CLOSED (2026-07-27). Gate scoreboard:** P1 ate PASS (dominant) · P2 clmm B1/B2
PASS (topology + regime caveats recorded) · p3-mmpolish PASS (mid/sparse add-on) ·
P3 racer PASS on template-free cells (both fairness reads) · P4 DIES (audition
load-bearing; two anatomy findings salvaged) · P6 anatomy: attach filter and
lexicographic pricing load-bearing (predictions), beta-dhat sparse split (novel,
confirmed) · KG2 2-swap LIVES (+3.6..4.8%) · KG3 subsumed by E0. Survivors to M4:
p3-ate, p3-clmm, p3-clmm-core (density-gated role), p3-mmpolish, p3-race8.

### 4.10 M4 — frozen eval, K=15, significance (2026-07-27)

PRE-REGISTERED 2026-07-27. **TUNING FREEZE: every arm's configuration is frozen at
e917c918** (no algorithm-code change after this entry counts for M4; the eval
instance seeds 901-915 have never been generated or run before this launch).
Scripts: m4_eval.py + m4_analysis.py @ e917c918. Stage main: 14 frozen cells x
{minorminer, mmfork-cuthill, p3-template, p3-ate, p3-clmm, p3-clmm-core,
p3-mmpolish, pssa, attraction} x ER inst seeds 901-915 (K_n instance-invariant,
seeds only) x algo seeds 10-14 x 60 s = 6,314 rows, hyde06 48W. Stage race: the 6
selection cells x 4 modes x 15 inst x 5 base seeds = 1,800 runs, outer5x8.
Bars (confirmation of M3 verdicts at eval scale, Wilcoxon signed-rank per cell +
Holm within-arm across cells, rank-biserial reported):
- p3-ate: Holm-significant (p<0.05) paired win vs MM on every above-p* cell, and
  no significant loss anywhere. Variance table: ate/template cross-seed std ratio
  vs MM reported (0.00x expected above p*).
- p3-clmm: >=1 Holm-significant mid-band win (B1 at scale); clmm-core reported
  under its density-gated role (dense cells only).
- p3-mmpolish: Holm-significant win on >=2 mid/sparse cells.
- p3-race8: the two fairness reads on the template-free cells, Wilcoxon p<0.05.
- Frontier: success counts on K180/K179 (report; MM expected 0/75-ish).
Success rates separate/unpaired; acl_spur column; wall within-batch only.

### 4.11 M5 — structured no-regression sweep (2026-07-27)

PRE-REGISTERED 2026-07-27. CLI route: experiments/m5_noregress.yaml @ e917c918
(structured ∪ lattice presets = 3,388 ids, pegasus_16, arms {minorminer, p3-ate,
p3-clmm, p3-mmpolish}, 1 trial, 60 s, master seed 4242, 56 workers; "(instance,
trial) pairing [CLI]" label mandatory on every table). Analyzer: m5_analyze.py @
e917c918 (pairs on graph_id, family x size-band buckets, raw ACL column — CLI has
no spur; stated on the table). Bar (verbatim from the plan): no family mean dACL >
+0.10 or success-rate drop > 1 pt for any p3 arm vs minorminer; else the failing
arm ships behind a density/regime guard and the sweep re-runs once with the guard.
Prediction (committed): p3-ate ties MM on sparse/structured families (auto-select
falls back to MM) and wins dense-structured (complete/turan/dense bipartite);
p3-clmm regresses on sparse families (its seeds hurt below the crossover — E0) and
is expected to need the density gate; p3-mmpolish never regresses.

--- results appended below per experiment; nothing above edited after launch ---

### 4.10b M4 supplement — the p-norm layout baseline (2026-07-27)

PRE-REGISTERED 2026-07-27 (before launch; added on user directive — the original
kickoff asked for MM "including with p-norm layout, the documented practitioner
default", and no paper3 experiment had carried the arm). Script: m4_eval.py --stage
main --arms minorminer-layout @ 3ea487e4 (dev_suite ARMS gains
"minorminer-layout"; registry arm = minorminer.layout.find_embedding, p-norm
placement). Cells/seeds/budget: the 14 frozen eval cells x eval inst seeds 901-915 x
algo seeds 10-14 x 60 s (rows append to m4_eval.csv; m4_analysis pairs it vs
minorminer like any arm). Bars: none (baseline completion) — the read is whether
layout changes ANY §4.10 conclusion: expected ≈ stock on dense ER (no geometry to
exploit), and the p3 margins must stand against max(stock, layout) per cell to be
quoted as "beats the practitioner default".

AMENDMENT to §4.11 (pre-launch, 2026-07-27): M5 arms gain minorminer-layout (its
home turf is structured sources); M5 graphs gain 1,100 sampled random/application
graphs (220 each from spin_glass, regular, watts_strogatz, planted_solution,
barabasi_albert; rng seed 4242) restoring the approved plan's scope that the
authored YAML had narrowed. Selection now parses to 4,488 graphs. The §4.11 bar
applies verbatim to all five families and both baselines.

--- results appended below; nothing above this line is edited after launch ---

SECOND AMENDMENT to §4.11 (pre-launch, 2026-07-27, user directive): M5 is now the
COMPLETE Ember benchmark — every library graph on every supported architecture at
the Ember paper's flagship sizes (chimera_16x16x4, pegasus_16, zephyr_12), replacing
the sampled sweep entirely (m5_noregress.yaml retired unlaunched; generator + six
batch YAMLs: experiments/gen_m5_full.py -> m5full_{c16,p16,z12}[_layout].yaml).
- Eligibility: per-topology pigeonhole only (n <= qubit count): 27,628 / 31,140 /
  30,221 graphs — MORE inclusive than the Ember paper's embeddability sets;
  "attempted and failed" is data. Oversized graphs are definitionally infeasible
  and excluded (running them proves nothing and risks unwatchdogged stalls).
- Arms: main batches {minorminer, p3-template, p3-ate, p3-clmm, p3-mmpolish} on the
  full eligible sets; minorminer-layout runs the n<=1000 subsets (25,010 graphs per
  topo — 80% of the library; p-norm layout on multi-thousand-node sources can stall
  CLI workers, which have no watchdog). p3-race8 excluded: it burns the full 60 s
  by design on every row (~1,500 core-h alone) and its claims are settled at §4.6/
  §4.10 on the selection cells.
- Pairing: (instance, trial) [CLI]; layout rows pair cross-batch against the main
  batch's minorminer rows at IDENTICAL derived seeds (seed derivation is
  batch-independent: root:algorithm:graph:topology:trial). Wall-time comparisons
  remain within-batch only.
- Volume/cost: ~520k rows (444,945 main + 75,030 layout); estimate 1,000–1,600
  core-h ≈ 18–29 h at 56 workers, sequential batches per QUEUE.md (order: p16,
  z12, c16, then the three layout batches).
- Bar: unchanged (§4.11), applied per (topology, family): no family mean dACL >
  +0.10 or success drop > 1 pt for any p3 arm vs minorminer, else regime-guard +
  one re-run. Prediction addition: on C16 (degree-6 fabric) the template regime is
  expected to shrink (busclique C16 max clique ~64) — p3-ate must degrade to MM
  gracefully there; that graceful degradation IS the C16 claim.

§4.10 RESULTS (2026-07-27; main 6,314 rows + race 1,800 rows; full tables in
m4_headline.txt/.md; layout supplement §4.10b appends after its run):

- **Every M3 verdict CONFIRMS on fresh eval instances (901-915, K=15) with Holm-
  corrected significance — no tuning inflation anywhere** (eval margins within
  ~1-2 pp of dev margins).
- p3-ate: all above-p* cells Holm p = 6.3e-13, rank-biserial 0.99-1.00, sweeps
  72-75/75; margins -6.5..-18.4% (ER) and -19.5/-32.9% (K140 P16/Z12, n=5
  unanimous); EXACT all-tie vs MM on both sparse controls (never-worse verified at
  K=15); K180/K179 5/5 vs MM 0/5. **Zero cross-seed variance above p* (0.00x),
  exactly 1.00x where it defers to MM.**
- p3-clmm: dense/mid wins Holm-significant (-6..-15.9% P16); sparse losses
  significant as expected (+13..+16%, regime-gated in product); the Z12 mid-band
  weakness reproduces ((100,0.2) +1.1%, (140,0.12) +5.2%) — reported as the
  topology asymmetry. clmm-core: stronger at (140,0.2) (-14.8%), worse at
  (140,0.12) (+3.7%) — the density gate holds; **variance 0.06x median** (core
  seeding near-determinizes the search).
- p3-mmpolish: Holm-significant at 10/12 MM-feasible cells (p ~ 6e-13, 75/0/0
  sweeps typical, -0.5..-1.4%); (140,0.2) P16 misses Holm (0.065, 75% wins);
  Z12 K140 +4.5% (0/5) — the known cliff weakness, excluded from the product's
  regime. mmfork-cuthill (context): -1.5..-2.5% significant on 5 cells.
- **Racer (Table 4): the selection claim confirms at eval scale.** Template-free
  sparse cells ((160,0.05), excl-tpl = full 75 pairs): P16 -3.25% seq (80%,
  p=1.8e-9) / -6.42% par (96%, p=7.9e-14); Z12 -4.27% seq (88%, p=1.2e-11) /
  -7.87% par (97%, p=7.9e-14). Pooled: seq -7.73% (95%, p=1.5e-72, 450 pairs).
  Mid cells: winner=template 72-75/75 (the ATE story wearing a racer hat,
  excluded from the selection claim per pre-registration).
- Frontier (Table 3): K180/K179 — MM, cuthill, mmpolish, attraction 0/5 each;
  template/ate/clmm/clmm-core/pssa 5/5 (ate/clmm at template-or-better ACL).

### 4.12 Errata & clarifications (2026-07-27, from the manuscript-drafting audit)

Dated corrections; original entries above are left as written (append-only).

1. **§4.1 "no non-monotonicity anywhere" — WRONG as written.** The P16 p* ladder
   reads 160→0.12 then 180→0.3. The apparent reversal is the win-rate definition
   starving on MM's feasibility fade at (180, 0.3) (MM 9/15 → fewer both-succeed
   pairs), not a true crossover reversal; the underlying template-vs-MM margin
   keeps improving with n. The manuscript carries this as a footnote to the p*
   table.
2. **§4.5 ATE (100,0.2) — transcription error.** Correct values: P16 −0.750
   (−8.2%, 25/0), Z12 −0.320 (−4.4%, 25/0). The entry's "−4.4% both topos" glued
   Z12's number onto P16.
3. **§4.10 "eval margins within ~1–2 pp of dev" — ER cells only.** P16 K140
   swung −33.5% (dev) → −19.5% (eval): n=5 pairs and MM's cliff-seed variance
   (med-std 3.09) dominate that cell's margin; the K_n headline numbers carry the
   n=5 caveat wherever quoted.
4. **§4.1 data-quality (i) resolution (previously unrecorded):** the
   mmfork-cuthill disconnected-source failure was fixed same-day at dd15edb3
   (wrapper places isolated vertices on free qubits and prunes them from
   var_order; regression tests test_forked_disconnected_source_with_order /
   test_forked_edgeless_source). No frozen dev/eval cell contains a disconnected
   instance, so no M3/M4 row was affected.
5. **Sha convention:** notes.md pre-registrations cite the commit CONTAINING the
   script content (correct for reproduction); QUEUE.md rows had cited the
   one-later "stamp" commits — QUEUE aligned to notes as of this entry.
6. **Ceiling-gap range:** canonical MM-only figure is 16–57% (K60 +16%, K100
   +39%, K140 +57% above the template); paper2's "30–60%" title spans all search
   arms, not MM alone.

§4.10b RESULTS (2026-07-27, 770 rows appended to m4_eval.csv; paired analysis in
this entry — m4_analysis's fixed arm list omits the supplement, computed directly):

- **minorminer-layout ≈ stock MM on every ER eval cell**: medians −0.06..+0.28,
  win rates 27-40 of 75 each way — no significant difference anywhere; the
  documented practitioner default does not change the dense-random story.
- **Layout is strictly WORSE at the dense cliff: 0/5 on ALL four K_n cells**
  (K140 P16/Z12 where stock is 5/5 and 4/5; K180/K179 where both fail). The
  p-norm initial chains actively fight the extended-bar structure the cliff
  needs — the same §3.10 anti-placement effect, now measured in the practitioner
  default. Quotable: the D-Wave-documented layout wrapper LOWERS MM's feasibility
  ceiling on complete graphs at 60 s.
- **p3-ate beats max(stock, layout) on every above-p* cell**: vs layout −0.31..
  −2.89 at 69-75/75; exact-tie-grade on sparse (40/33..40/35, |med| ≤ 0.07 — ate
  defers to stock MM, which ≈ layout there). The "beats the practitioner default"
  quote is licensed cell-by-cell.
- M4 is now fully closed (main + race + supplement).

7. **(2026-07-28) Harness bug found during M5 bring-up — YAML worker counts were
   silently ignored.** `_build_resolved_params` copied YAML keys verbatim but the
   runner reads internal names: documented `workers:` never mapped to `n_workers`
   (fell through to default 1); `trials`/`warmup` had the same mismatch, masked by
   coinciding defaults. Every YAML-driven `ember run` in this repo's history was
   single-worker (the paper2 23k sweep used the `--workers` CLI flag, which always
   worked). Fixed at 48aab69b with alias translation + unit check; upstream Ember
   should inherit the fix. Also at M5 bring-up: eager full-selection loading
   (serial hours + 27 GB parent + per-task target pickling) replaced by lazy
   worker-side materialization at 1e754132 (A/B verified: identical (seed, ACL)
   rows vs the eager path; zero test regressions). Neither change affects any
   §4.1-§4.10 result (all script-route or CLI-flag runs).

§4.11 RESULTS — P16 main batch (2026-07-28; 155,700 rows; m5_analyze verdict table
archived with the batch): **the bar FIRED — 42 family x arm violations — and the
pre-registered remedy (regime guards + one re-run) is applied.** Decomposition:
1. **p3-clmm ACL losses on sparse/structured families** (star +1.28, wheel +1.48,
   grid +0.27, kagome +0.39, planted +0.36...): the §4.11 committed prediction,
   verbatim. Remedy: density gate at 0.15 — below it the arm passes through to
   full-budget stock MM (metadata selection=guard_passthrough_mm); guard=False
   kwarg preserves the faithful literature control for script-route science.
2. **p3-ate success drops concentrated on large sparse lattices** (bcc 4.2 pt,
   triangular 3.6, grid 1.3...): ALL from the n > K_max core+periphery path's
   50/50 budget split halving MM's effective budget on time-marginal instances.
   ACL never regressed on ANY of the 31,140 graphs (the never-worse ACL property
   held library-wide). Remedy: attempt core+periphery only at density >= 0.15
   (the overflow regime where it ever wins); sparse overflow -> MM keeps the
   full budget (template_mode=skipped_sparse_overflow).
3. **p3-mmpolish success drops on hard families** (binary_tree 9.1 pt,
   frustrated_square 6.9, weak_strong 4.1...): the fixed 70/30 budget split —
   instances needing >70% of budget to legalize flipped to failure. Remedy
   (v1.1): MM gets the FULL budget; polish spends only the leftover wall (§4.7:
   MM patience-expires early on most instances) — success == stock MM by
   construction on time-marginal instances, polish gains preserved elsewhere.
Also noted: several 1.0-1.4 pt "violations" are single-graph flips in 12-72-graph
families under CLI per-arm seed noise — the 1 pt bar is below the noise floor at
that granularity; reported as-is, remedied incidentally by the guards. Arm
versions bumped to 1.1.0; M4 (closed) measured v1.0 — the guards alter only
off-regime behavior (no M4 headline cell is affected except (140,0.12) for
clmm, which becomes passthrough). Re-run plan: z12/c16/layout batches run the
guarded arms from scratch; P16 re-runs the three guarded arms only (minorminer/
p3-template rows reused; pairing on graph_id at identical derived seeds).

§4.11 RESULTS — Z12 main batch (2026-07-29; 151,105 rows; first architecture fully
under the v1.1 guards): **bar-as-written FAILS (16 violations, down from P16's 42);
the noise-aware reading PASSES with one documented regime boundary.**
- **The guards enabled a direct seed-noise null**: on the 26 families below the
  density gate, guarded p3-clmm IS minorminer at a different derived seed — the
  arm-vs-MM success differences there measure the CLI (instance, trial) pairing
  noise floor directly: mean -0.00 pt, sd 1.57 pt, max |4.55| pt across families,
  perfectly symmetric. Every residual success violation (1.4-4.5 pt: bcc, cubic,
  frustrated_square, king, cycle, wheel — for all three arms, which are all
  MM-equivalent there post-guard) lies INSIDE this null. Verdict: seed noise,
  quantified, not regression. The 1 pt bar is below the noise floor at
  full-library single-trial granularity (recorded as a bar-calibration lesson;
  no code change — tightening arms against measured noise would be tuning on
  test).
- **ACL violations**: hypercube (+0.18..+0.42, ALL arms incl. polish-monotone
  mmpolish) = 7 successes over 11 graphs at straddling density — small-sample
  seed luck. **johnson +0.228 for p3-clmm is REAL** (density 0.172, genuinely
  seeded; 74 graphs): a regime boundary for the mid-band arm on dense structured
  sources — and on the same family **p3-ate BEATS MM by -0.63** (7.112 vs 7.739;
  the template fits johnson geometry and evaluate-both selects it). The product
  story is intact: clmm's boundary is documented; the product arm covers it and
  wins.
- p3-ate: zero ACL regressions library-wide again (johnson is a WIN); all its
  success deltas inside the null. p3-mmpolish: broad small ACL wins persist
  under the v1.1 leftover-budget design (turan -0.256, spin-glass-class families
  similar), success deltas inside the null.

8. **(2026-07-30) C16 runaway: `_find_split` had no budget enforcement.** The exact
   pair-split check iterated 2^|U| subsets with no deadline/cap ticks. Invisible on
   P16/Z12 (|U| <= ~14 -> 16k subsets); on Chimera's degree-6 long chains |U|
   reaches 25-40 -> 2^30-2^40 subsets, turning "3 s" moves into hours (worst
   observed: 19.5 h on one row; the C16 batch collapsed to ~1.4k rows/h with
   workers pinned). Fixed at v1.1.1: |U| > 22 -> unproven skip; tick shared
   node/deadline accounting every 4096 subsets; regression test
   test_joint_repair_bounded_on_long_chain_pairs. CONTAMINATION AUDIT: Z12 — 10
   successful mmpolish rows exceeded 65 s (worst 143 s; the other 3,784 >65 s rows
   are MM-stage cooperative-overshoot FAILURES, no ACL impact); P16 — 11 successful
   rows (worst 158 s). Those 21 rows are flagged for exclusion from final tables
   (immaterial to any reported median); the C16 partial batch (29k rows, 21 h) is
   DISCARDED and re-run entirely under v1.1.1. The §4.4 K60 fixpoint number is
   unaffected (P16 template, small |U|); the §4.3 probe ran per-move deadlines on
   P16 (worst pair wall 3.04 s recorded — bounded).

§4.11 RESULTS — C16 main batch (2026-07-31; 23,994 graphs x 5 arms after manifest
eligibility; v1.1.1 wall discipline verified: 0 rows > 65 s, worst 63 s):
**bar-as-written FAILS (22 violations); the committed C16 prediction is CONFIRMED
in substance.** (i) p3-ate degrades gracefully as predicted — 6W/26t/3L with dense-
structured wins intact (kneser -8.5%, turan -7.2% n=386, complete -6.9%,
spin_glass -4.7% n=282); its success violations are 1-2-graph flips in tiny
families (binary_tree "10 pt" = ONE graph, dropped identically by all three arms —
the correlated marginal-instance signature inside the §4.11-Z12 noise null).
(ii) p3-mmpolish: 15W/18t/2L on its third architecture (watts_strogatz -2.6% over
5,309 pairs) — the consistency claim generalizes. (iii) **p3-clmm's density gate is
architecture-dependent**: 8 mid-family mean-ACL trips (+0.11..+0.28) because the
0.15 threshold, calibrated on P16/Z12, sits below Chimera's higher crossover
(consistent with E0's per-topology p* map). Documented boundary; v1.2 candidate =
architecture-aware gate scaled by target K_max/degree (improvement-notes #11); no
further re-run (the single pre-registered guarded re-run was spent at P16, and the
product arm covers the regime). Per-category table archived with the batch.

§4.11 RESULTS — P16 guarded re-run, merged verdict (2026-07-31; rerun = 3 guarded
arms @ v1.1/v1.1.1 x 30,768 rows, paired against the original batch's minorminer/
p3-template rows at identical derived seeds): **violations 42 -> 19; the guards
reproduce their Z12 behavior on Pegasus.** Category verdicts: p3-mmpolish
**18W/17t/0L — zero category losses on Pegasus** (several residual bar trips have
NEGATIVE mean dACL: better chains, 1-3 marginal success flips); p3-ate 9W/22t/4L
(johnson now a -0.712 mean WIN); p3-clmm 7W/24t/4L. Residual violations decompose
as before: single-graph success flips in small families (binary_tree 9.1 pt = one
graph of 11; frustrated/triangular/shastry correlated across arms — the marginal-
instance signature inside the §4.11-Z12 noise null) + clmm hypercube (+0.34, 11
graphs, seed luck). **hardware_native is now a recurring cross-architecture
oddity** (ate P16 +0.13 mean/4.9 pt; mmpolish Z12 +5.9%): near-native sources are
perturbed by any arm overhead/seed change — improvement-notes #12 (native fast
path: detect subgraph-embeddable sources and return the identity-style embedding
before any machinery; would make every arm strictly >= MM there). mmpolish rerun
wall discipline: worst 164 s = MM-stage cooperative overshoot (same class as stock
MM's own rows; the §4.12.8 runaway class is gone).

§4.11 RESULTS — layout batches, M5 CLOSE (2026-07-31; 75,030 rows, n<=1000 subsets,
cross-batch pairing vs main-batch minorminer at identical derived seeds):
**minorminer-layout ~= stock MM on ACL at library scale and WORSE on success on all
three architectures.** Median paired dACL: P16 +0.22%, Z12 +0.00%, C16 +0.00% (with
losses outnumbering wins: e.g. P16 7,701W/10,006L); success: P16 80.7 vs 82.5%, Z12
82.3 vs 82.9%, C16 59.4 vs 63.3%. Home-turf check: layout wins a few lattice
families modestly (honeycomb -3..-6% across topologies, kagome -4.6% Z12, cubic
-1.8% P16) and is neutral-to-harmful elsewhere (cubic +3.2% C16, grid +2.2% C16).
Conclusion: the documented practitioner default never changes a paper3 conclusion —
all p3 margins quoted vs max(stock, layout) stand, and layout's overall success
deficit extends §4.10b's cliff finding to library scale.

**M5 COMPLETE.** Final tally: ~595k measured rows across 6+1 batches, three
architectures, all arms; verdict trail: P16 unguarded FAIL (42) -> guards ->
Z12 16 / P16-merged 19 / C16 22 violations, all decomposed to (a) the measured
seed-noise null, (b) documented regime boundaries (clmm arch-dependent gate,
hardware_native), with the committed predictions (clmm sparse regressions,
C16 graceful degradation) confirmed verbatim. mmpolish: 0 category losses on P16,
1 on Z12, 2 on C16 across 35 families. ate: zero library-wide ACL regressions on
P16+Z12; dense-structured wins on all three architectures.

### 4.13 Idle speed table (2026-07-31)

PRE-REGISTERED 2026-07-31 (protocol rule 5: headline speed claims re-measured at
workers=1 on an idle machine). Script: docs/paper3/data/m6_speed.py @ deb88153. hyde06 (now idle, load ~2), workers=1 strictly sequential. Cells: P16
(100,0.3), (140,0.2), (140,1.0)=K140, (160,0.05); Z12 (100,0.3), (140,1.0);
instances 101-103 (K_n once) x eval seeds 10-11; arms {minorminer,
minorminer-layout, p3-template, p3-ate, p3-clmm, p3-mmpolish}; 60 s budget.
Deliverable: the paper's median-wall table (no bars; measurement). Expected from
within-batch data: template 0.5-2 s, clmm 4-12 s (n<=140 mid), MM/layout 15-60 s,
ate ~= MM (contains it), mmpolish ~= 60 s by design (uses leftovers).

--- results appended below; nothing above this line is edited after launch ---

§4.13 RESULTS (2026-08-01, hyde06 idle load ~2, workers=1 strictly sequential,
144 runs): the paper's speed table (m6_speed_summary.txt / .csv). Headlines:
**p3-template 0.2-1.3 s at every cell — 20-150x faster than minorminer while
15-33% better on the dense cells**; p3-clmm 5.7-9.2 s on the mid-band (3-5x
faster than MM's 16.5-28.9 s) and full-budget-class at K140; p3-ate = MM + a
visible 0.3-0.5 s insurance premium (29.1 vs 28.5 s etc. — the improvement-notes
#2/#3 tax, now precisely measured); p3-mmpolish ~= 60 s by design (spends
leftovers); minorminer-layout 1.1x SLOWER than stock at the K140 cells (69 vs
61 s) and mixed on mid cells. All within-batch M4/M5 wall ratios reproduce idle.

9. **(2026-08-01) §4.11-P16 phrasing correction:** "ACL never regressed on ANY of
   the 31,140 graphs" overstated the analyzer's granularity — the measurement is
   FAMILY-MEAN bars (no ate family ACL violation in the unguarded P16 run; the
   merged re-verdict records one, hardware_native +0.13 mean). The defensible
   claim, used by the manuscript, is family-level: no family ACL regression beyond
   the documented near-native boundary. Per-graph tallies were never computed.

### 4.14 K_n seed deepening — n=5 -> n=20 pairs (2026-08-01)

PRE-REGISTERED 2026-08-01. The manuscript's remaining structural weakness: the
K140 headline margins rest on 5 pairs (Wilcoxon floor 0.0625) and the K180/K179
frontier on 5 attempts/arm. K_n cells are instance-invariant, so fresh algorithm
seeds extend them directly. Script: docs/paper3/data/m6_k140.py @ 65819fc6.
Cells: P16 (140,1.0), (180,1.0); Z12 (140,1.0), (179,1.0). Arms {minorminer,
p3-ate, p3-clmm, p3-mmpolish}; eval algo seeds 15-29 (15 fresh; disjoint from
M4's 10-14, pooled to n=20 for the paper's K_n rows). 60 s; hyde06 idle,
8 workers (ACL/success only — walls not table-bearing). Bars: none (evidence
deepening; the M4 K_n rows and Table 3 frontier counts are restated at n=20 with
Wilcoxon recomputed).

--- results appended below; nothing above this line is edited after launch ---

§4.14 RESULTS (2026-08-01, 240 runs, hyde06 idle; pooled with M4 eval seeds 10-14
-> n=20 per K_n cell): **the K_n evidence is no longer thin.**
- P16 K140: ate median -3.168 (-19.4%), 20/0, Wilcoxon p=1.9e-6; clmm -15.8%,
  19/1, p=3.8e-6. Z12 K140: ate -4.968 (-32.2%), 18/0, p=7.6e-6 (MM 18/20 —
  the cliff-edge flakiness reproduces at n=20); clmm -31.4%, 18/0.
- Frontier at 20 attempts/arm: ate and clmm 20/20 at P16 K180 AND Z12 K179 where
  minorminer is 0/20 — the feasibility-ceiling claim now rests on 20-for-20 vs
  0-for-20 per architecture.
- mmpolish at K_n: median exactly 0.000 (P16) / 0/7 small losses (Z12, p=0.018)
  — the documented cliff exclusion, unchanged.
Data: m6_k140.csv. The manuscript's K_n rows, Table 3 frontier counts, and the
n=5 caveats are restated at n=20.

## 5. v1.2 improvement program (2026-08-02, plan approved: all five workstreams)

Basis: improvement-notes.md items 1-6, 11, 12 + the NEW beta_ramp idea. Zephyr-only
validation; P16/C16 deferred to a user decision. Frozen-arm policy: p3-ate/
p3-mmpolish/p3-race8/p3-template stay byte-identical; new behavior = NEW names
(p3-ember, p3-mm-beta[-fb], p3-race9); sole in-place edit = clmm's kmax-keyed guard
threshold (Z12/P16-identity, unit-tested). Interface freeze for the build wave:
paper3/beta.py exports dhat_of(source)->float and _GATE_MAX_DENSITY = 0.11; the
racer agent stubs a local copy and the coordinator swaps the import at merge.

BUILD RECORD (P1 wave complete 2026-08-03; four worktree agents, merged in the
planned order A2->A3->A1->A4; all merges conflict-free; racer's local _dhat
swapped to beta.dhat_of at merge as contracted):
- W2/A2 (9fc2ffdd): beta.py (p3-mm-beta gate<0.11 passthrough-above; -fb = 0.6x
  budget beta then stock-MM rescue on the actual remainder), beta_ramp/
  beta_ramp_hold fork switches (5-site plumbing x2; saturates DBL_MAX/4; zero
  rng draws), regenerated mm_fork.patch (760 lines) vs pristine 0.2.22,
  build_mm_fork.sh self-test extended (OFF-parity + engaged combos), p6_probes
  --topo Z12/--confirm-beta (900 tasks -> *_z12 files; P16 resume keys
  protected; committed P16 summaries regenerate byte-identically). 789
  algorithm tests green vs a from-scratch fork build. FINDING: beta_ramp_hold
  inert in single-shot find_embedding (see §4.15 amendment 3).
- W3/A3 (a2127e33): race.py p3-race9 (mm-beta stage kind with parent-computed
  dhat threaded as a picklable float; RACE9_SPEC appended at index 8 so arms
  0-7 keep race8's exact seed derivations; opt-in terminal anytime_polish,
  monotone + validity-gated, terminal_polish_s accounted), t1d_race9.py (4
  modes, §4.15 bars printed as verdicts, both par modes at 8 workers).
  race8 FROZEN — replay test pins values captured at 2161c9dc.
- W1/A1 (0a317117 + ac064754): native.py (structural gates -> label-subset
  identity -> Glasgow, deterministic, never trusted unvalidated) + ember.py
  (p3-ember v1.0.0: native -> template with sub-K_max density gate >= 0.08 ->
  stock-MM remainder -> select, tie->template -> leftover anytime_polish;
  tiny-timeout <= 2 s skips Glasgow + polish). W1b LANDED: spur_prune
  clean-chain-skip, byte-identical on the deadline-free corpus gate,
  1.22-1.32x template speedup (revert = git revert ac064754 alone). A1 flagged
  the Glasgow wall smoke at 5.667 s -> resolved by §4.15 amendment 1
  (eligibility gate; coordinator-measured tax curve).
- W4/A4 (aea0196a): clmm v1.2.0 kmax-keyed guard threshold. DEVIATION from the
  plan's literal "kmax < 100" cut: P4=36 / Z3=40 / Z4=56 would be misclassified
  chimera-class, breaking the prescribed identity tests — replaced by the
  size-normalized key kmax < 1.6*sqrt(|V_target|) (chimera-class ratio sqrt(2)
  ~ 1.41 at every size; P/Z >= 1.7), which reproduces the intended flagship
  split exactly (C16 64 -> 0.35; P16 180 / Z12 184 -> 0.15) and is
  broken-qubit-robust. P16/Z12 byte-identity regression-tested (v1.1 hashes
  captured pre-change). Probe verdict: §4.15 amendment 4 / improvement-notes
  #6 — structure gate DEAD.
- Coordinator (this merge): race.py dhat import swap; native.py
  glasgow_eligible gate; ember.py construct_s; dev_suite ARMS += p3-ember;
  §4.15 amendments 1-4.

### 4.15 v1.2 T1 — Zephyr dev gates (2026-08-02)

PRE-REGISTERED 2026-08-02 (before any build merge or launch). Scripts land in the
build wave; each T1 sub-batch's sha is stamped into QUEUE.md at launch. Dev
registries (rule 4): inst seeds 101-105, algo seeds 0-4 (15-seed confirms 0-14),
CLI master 42, 60 s, hyde06 <=48W.

- T1a (p3-ember, dev cells): dev_suite --topo Z12, arms {minorminer, p3-template,
  p3-ate, p3-mmpolish, p3-ember}, the 7 frozen Z12 dev cells.
- T1b (native fast path): CLI, graphs 37600-37641 (hardware_native; 41 Z12-eligible),
  arms {minorminer, p3-ate, p3-ember}, trials 5, master seed 42.
- T1c (beta family): p6_probes --topo Z12, deg-10 n in {100,140,180}, switches
  {stock, beta-dhat, ramp(r=2, hold 0/1)} x 15 seeds + p3-mm-beta/-fb x 5 seeds.
- T1d (racer A/B): race8 vs race9 paired, Z12 (160,0.05) + (100,0.2), seq+par reads,
  5 inst x 5 base seeds.
- MANDATORY pre-CLI smoke: find_subgraph wall < 5 s on the largest Z12-eligible
  source (no CLI watchdog).

BARS (noise-calibrated per improvement-notes #10):
- p3-ember: (i) dense carry — within 1% of p3-ate's median margins on (100,0.3),
  (140,0.2), K140 AND never > +0.25% median worse than ate on ANY cell (polish is
  monotone; a violation is a bug); (ii) sparse win — (160,0.05) and (100,0.2)
  median dACL_spur < -0.5% AND >=55%W vs MM; (iii) tax kill — median wall vs MM on
  (160,0.05) <= +0.2 s within-batch; (iv) K179 5/5; (v) hardware_native: every
  native_hit row ACL == 1.0; family success >= MM (deficits count only at >=3
  graphs).
- beta arms (Z12-transfer test of §4.8b; the degree-20 fabric may shrink the sparse
  margin — stated up front): beta-dhat and each ramp variant CONFIRM iff median
  < -1% AND >=60%W at 15 seeds on >=2 of the 3 deg-10 cells. Ramp additionally:
  success >= stock-1 per cell while holding >=80% of dhat's ACL margin -> the ramp
  becomes the below-gate engine of a future v2 (separately pre-registered).
  p3-mm-beta-fb: success == stock exactly per cell. Decision tree: dhat fails on
  Z12 -> beta.py arms die this cycle; the racer's mm-beta slot stays (zero-risk
  diversity).
- race9 vs race8 (paired at the same master seeds): median < -0.5% AND >=60%W on
  (160,0.05) in >=1 fairness read with the other read non-regressing (median <= 0).
  Diagnostic: race9 worse on >40% of pairs in any read -> roster-interference
  investigation before shipping.
- CLI family rules: success drops real only above max(2.6 pt, 3 graphs) (2.6 pt ~
  95th pct of the measured sd-1.57 null); family ACL bars only at >=10 pairs.

AMENDMENTS (2026-08-03, pre-launch — dated before any T1 run; nothing launched):

1. **Glasgow tier eligibility** (resolves the A1 build-smoke violation: wall
   5.667 s >= the 5 s bar on the largest Z12-eligible source, Z8-scale n=2176).
   Coordinator re-measured the tax curve (mac, stock 0.2.22, timeout=1, into
   Z12): find_subgraph's supplemental preprocessing runs OUTSIDE its own timeout
   and scales with SOURCE edges — gnp sources ~1.06 s (the 1 s int-floor solver
   budget), Z4/5.0k edges 1.71 s, Z6/11.4k 3.25 s, Z8/20.3k 5.24 s — and the Z8
   probe MISSES after paying 5.24 s (a 1-2 s solver budget cannot crack
   ~2000-node subgraph isomorphism; at that scale label-identity is the only
   realistic hit path). Remedy (native.py::glasgow_eligible): the Glasgow tier
   runs only when source edges <= 15,000 AND modal-degree concentration
   (fraction of nodes with degree within +-1 of the modal degree) >= 0.6.
   Measured split: sparse-ER dev cells <= 0.43, BA 0.56 | QPU graphs with 5%
   broken 0.80-0.93, perfect fabrics >= 0.71, grid 0.97, cycle/hypercube/
   random-regular 1.00, random tree 0.94 — the accepted set is exactly where a
   subgraph hit is plausible; a sparse-ER call is a measured pure-miss ~1.06 s
   tax. Structural + label-identity tiers stay universal. The smoke bar reads:
   find_subgraph wall < 5 s on the largest glasgow-ELIGIBLE Z12 source
   (re-verified pre-T1b; the largest Z12-eligible FAMILY source now pays only
   µs-ms gates). SMOKE (2026-08-03, mac, through try_native): gnp(160,0.05)
   gated 0.002 s; Z6 eligible 3.603 s MISS (< 5 s bar PASS); Z8 gated 0.003 s;
   Z12-with-5%-broken aligned labels -> label_identity hit 0.062 s ACL 1.0;
   grid 12x12 and cycle-200 -> glasgow_hit ~0.37 s ACL 1.0 (the eligibility
   set is winnable, not merely protective).
2. **Bar (iii) wall term made precise**: "median wall vs MM" compares ember's
   time-to-FIRST-VALID embedding (meta ``construct_s``, visible in dev_suite
   arm_meta) against MM's wall — stock MM's wall IS its time-to-first-valid.
   Ember's stage-4 anytime tail spends the leftover to the shared deadline by
   design (the mmpolish precedent; §4.13 mmpolish ~= 60 s walls) and is not the
   (iii) quantity. Total wall stays logged; every ACL comparison remains
   equal-total-budget.
3. **T1c expected tie** (A2 build finding, documented in-tree): beta_ramp_hold
   is observationally inert in single-shot find_embedding — the chainlength
   phase never re-reads qubit prices and ep.embedded never reverts — so
   ramp2h == ramp2 byte-identically. T1c treats the exact tie as CONFIRMING
   instrumentation (the §4.7 dirty_skip precedent), not a wasted arm.
4. **W4 probe verdict** (pre-registered in the W4 kickoff, not a §4.15 bar;
   recorded at improvement-notes #6): AUC 0.366 vs the 0.8 bar over 883
   all-three-succeed Z12 graphs — FAIL with the direction INVERTED (johnson
   positives sit at HIGH template-restriction score, within-johnson AUC 0.814
   for high->signature; random_planar positives at the LOW end — bimodal
   across families, no threshold separates). The v1.3 structure gate is dead;
   the finding is retained as item-6 boundary science.

--- results appended below; nothing above this line is edited after launch ---

### 4.16 v1.2 T2 — Z12 library re-verify (2026-08-02)

PRE-REGISTERED 2026-08-02. Launch gated on 4.15 verdicts. One CLI batch: arms
{p3-ember, p3-mm-beta-fb} ONLY (race9 excluded per the racer-in-sweeps precedent;
clmm v1.2 is Z12-identical by construction — its unit test is the evidence), the
same 30,201-graph Z12-eligible set, trials 1, timeout 60, master seed 4242, 60W.
Pairing: m5_analyze --baseline-db results/m5full_z12/batch/results.db (graph_id
pairing vs the archived minorminer rows; "(instance, trial) [CLI]" regime; the
sd-1.57 pt/family null governs — cross-arm rows never share derived seeds, see
errata 4.12.10).
BARS: p3-ember — no family ACL violation (>=10-pair rule); no success drop >
max(2.6 pt, 3 graphs); POSITIVE claims: carries ate's dense-structured category
wins (kneser/turan/complete/spin_glass class, median < -0.5% AND >=55%W), mmpolish-
class small wins on >=5 families by the same rule, hardware_native flag retired
(success >= MM, mean dACL <= 0). p3-mm-beta-fb — success within the null on every
family (the fallback guarantee); the ACL claim requires >=3 below-gate families
each independently passing median < -0.5% AND >=55%W; above-gate families are
exact passthrough (metadata spot-check). Remedy budget: ONE regime-guarded re-run
of a failing arm, freshly pre-registered.

--- results appended below; nothing above this line is edited after launch ---

10. **(2026-08-02) "identical derived seeds" mis-phrasing (found by the v1.2 surface
    audit).** The §4.11 second amendment and a gen_m5_full.py comment claimed layout
    rows pair against main-batch minorminer rows "at IDENTICAL derived seeds". Wrong:
    _derive_seed (benchmark.py) salts the ALGORITHM NAME into the key, so cross-ARM
    rows never share seeds — that is precisely the "(instance, trial) [CLI]" regime
    of protocol rule 1. The true (and sufficient) property is that seed derivation is
    BATCH-independent: any arm's rows pair against another batch's rows exactly as
    validly as within one batch, governed by the measured sd-1.57 pt/family null.
    (The P16 rerun's replacement property — same arm name, same derived seeds — was
    and remains correct.) No reported table used the wrong framing; every CLI table
    carried the correct pairing label. Comment fixed at gen_m5_full.py.
