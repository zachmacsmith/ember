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
@ <sha stamped at commit>, run with --resume against the E0 CSV (only new cells
execute; resume keys verified exact-match in the E0-author's validation).

Bars: none (baseline extension of §4.1; the §4.1 decision rules apply verbatim to
the new cells). Runs on hyde06 after e0_ceiling per QUEUE.md.

--- results appended below; nothing above this line is edited after launch ---

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
