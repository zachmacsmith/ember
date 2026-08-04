# Minor Embedding Has Two Regimes: A Density-Resolved Map and a Never-Worse Adaptive Embedder

<!--
  DRAFT v1.2 (2026-08-03) — paper3 manuscript, branch `paper3`.
  v1.2 adds Section 12 (addendum): the composed embedder p3-ember,
  Zephyr-validated (§4.15/§4.16); Sections 1–11 unchanged from v1.0.
  Provenance convention: every quantitative claim carries a parenthetical anchor into the
  laboratory record — (§4.x) points into docs/paper3/notes.md, (§3.x) into
  docs/paper2/notes.md. Data files live in docs/paper3/data/; the measurement
  constitution is docs/paper3/protocol.md. All [PENDING-M5] and [PENDING: §4.10b]
  slots are now filled from §4.10b–§4.13 (layout supplement, full-library sweep,
  errata, idle speed table). Structure is Markdown-for-LaTeX: one # title, ## sections,
  ### subsections, numbered tables and figures, bracketed citation keys.
-->

**Authors:** [author list placeholder]

**Target venue:** [placeholder — quantum software / heuristics track]

---

## Abstract

Minor embedding — mapping a problem graph into chains of physical qubits on a
quantum annealer's working graph — is dominated in practice by a single heuristic,
minorminer, used as the structureless fallback for every source graph. This paper
shows that the problem it solves is not one problem. Minor embedding has two
regimes, split by a measurable source-density crossover p\*(n): below it,
stochastic search is the right tool and only constants are available; above it,
construction dominates search, and no amount of searching closes the gap.

The evidence is the first density-resolved crossover map: 109 Erdős–Rényi and
complete-graph cells on Pegasus P16 and Zephyr Z12, seven embedding strategies,
8,559 paired runs at a fixed 60 s budget (§4.1, §4.1b). The crossover p\*(n) falls
from 0.7 at n=40 to 0.12 at n=160 on P16 (0.9 to 0.12 on Z12); above it a
right-sized, source-trimmed clique template built in 0.2–1.3 s (§4.13) beats 60
seconds of minorminer search by 5–33%, with the margin a ridge along minorminer's
feasibility cliff — which is density-flat at n=140 across p=0.2–1.0 on both
fabrics at this budget (§4.1), and moves with budget (0/25 to 23/25 successes at
(180, 0.3) as budget grows 5 s to 180 s, §4.7).

The map's product is ATE, an adaptive template embedder: busclique template +
trimmability-aware slot assignment + evaluate-both selection against a search
arm. On 14 frozen evaluation cells with instance seeds never touched before the
tuning freeze (K=15), ATE wins every above-crossover cell — median paired ΔACL
−6.5% to −18.4% on ER (Holm-corrected p = 6.3e-13, rank-biserial 0.99–1.00) and
−19.4%/−32.2% on K140 (n=20 pooled seed-pairs, 20/0 and 18/0 sweeps, Wilcoxon p<2e-5; §4.14) — and
is never worse than minorminer on ACL beyond seed noise anywhere measured, at a
measured sub-second wall premium (§4.13): exact ties where it defers (75/75
pairs at Δ = 0.000 on each sparse control) and exactly zero cross-seed variance
where the template wins (§4.10). It embeds K180 on P16 and K179 on Z12 5/5 where
minorminer is 0/5, and
reaches the busclique bound (K184) on Z12 at better ACL than minorminer achieves
on K140, 44 vertices smaller (§4.1). The assignment stage is not decoration: it
beats a 32-random-assignment oracle and moves the crossover itself one grid step
below the naive template's (§4.9, §4.5).

Three supporting instruments make the comparison honest and complete: a
measurement protocol (paired seeds, budget parity, polish parity, restart
controls) whose standing deflator shows that best-of-K restarts at equal
wall-clock are worth approximately nothing — the implicit freebie behind many
reported wins does not exist outside toy cells (§4.1 e0_ceiling); an exact
joint-repair polish that exhibits the move class minorminer's dynamics cannot
reach (58 pair moves where both endpoints are provably single-move stuck, §4.3)
and improves minorminer's own output on 10/12 feasible cells (§4.10); and a
rank-stability-gated racer that beats best-of-8 minorminer under both fairness
readings, pooled −7.7% (p = 1.5e-72; −3.8% to −6.8% excluding template-floor
wins) (§4.2, §4.10). An anatomy study of the shipped program closes the loop:
minorminer's undocumented exhaustive audition and lexicographic overlap pricing
are load-bearing, it leaves budget on the table by converging before its
deadline, and — unexpectedly — the 2014 paper's own finite-β pricing, which the
shipped program abandoned, beats the shipped default by 2.6–5.0% on sparse
graphs, a regime split inside the incumbent's own cost function (§4.7, §4.8,
§4.8b). The no-regression claim closes at ecosystem scale: a pre-registered
sweep of the complete Ember benchmark library on three architectures (≈595k
runs, bars committed before launch, §4.11). The unguarded first batch tripped
the bar; the pre-registered remedy (regime guards + one re-run) answered; and
every residual violation decomposed into a directly measured seed-noise null
(sd 1.57 pt per family, obtained for free from the guards' passthrough mode) or
a documented regime boundary. Final category verdicts over 35 families: the
polish arm 18W/17t/0L on P16 (17/17/1 on Z12, 15/18/2 on C16); ATE wins
dense-structured families on all three fabrics with no family-level ACL
regression on P16+Z12 beyond one near-native oddity (§4.11). The practitioner
default (minorminer.layout) is settled at both scales — ≈ stock on ACL, worse
on success on all three architectures, 0/5 at the dense cliff where stock is
5/5 (§4.10b, §4.11) — and an idle-machine speed table prices the products:
template 0.2–1.3 s (20–150× stock), clmm 3–5× on the mid-band, ATE = minorminer
plus a sub-second premium (§4.13).

---

## 1 Introduction

Quantum annealers do not implement arbitrary couplings. To run a problem whose
interaction graph G is not a subgraph of the hardware graph T, each logical
variable must be represented by a *chain* — a connected set of physical qubits
acting as one — such that every source edge is realized by at least one coupler
between the corresponding chains. Finding such a *minor embedding* is
NP-hard in general; its quality is consequential: longer chains dilute coupling
strength, consume qubits, and degrade solution quality downstream. The de facto
universal tool is minorminer, the D-Wave Ocean default, implementing the
Cai–Macready–Roy (CMR) heuristic [CMR14]. Its ecosystem role is precisely that
of the *structureless fallback*: when nothing is known about the source graph,
minorminer is what runs. On the largest published benchmark it ranks first on
random graphs among six methods (mean rank 1.63) [EMB26].

This paper's thesis is that the structureless problem minorminer is asked to
solve is two problems wearing one name, split by a measurable source-density
crossover p\*(n):

- **Below p\*(n): a search regime.** Sparse fixed-degree random graphs are
  expanders; their bisection width is Θ(n) while a quasi-planar qubit fabric's
  cut capacity grows only with the perimeter of the occupied region, so *any*
  embedder pays Θ(n) total chain mass. Measured: stock minorminer's mean chain
  length per vertex is flat at ACL/n ≈ 0.057 across n = 60–220 at fixed average
  degree 10 (§3.21). Minorminer already sits on the right scaling law; the
  available prizes are the constant, variance, speed, and feasibility — real,
  but bounded.
- **Above p\*(n): a construction regime.** Dense sources want the fabric's
  native crossbar structure. A clique template produced by polynomial
  construction (busclique), right-sized to n, restricted to the source's edges
  and spur-pruned, lands 16–57% *below* stock minorminer on complete graphs
  (K60: 6.73 vs 7.83; K100: 9.78 vs 13.62; K140: 13.17 vs 20.72, §3.26) — and
  minorminer's own full-budget polish cannot improve that construction at all
  (≤ 0.04 ACL in 3–42 s, §3.26). Above the crossover, search is not merely
  slower than construction; search *plus polish* cannot reach where
  construction starts.

Neither half is entirely new in isolation: constructions are known to win on
complete graphs, and search is known to win on sparse graphs (Section 2). What
has never been published is the boundary — where, in (n, p), one regime hands
over to the other, on which fabrics, at what budget, and with what margin — nor
an embedder that exploits the answer without ever losing on the other side.
Both are delivered here.

A word on method, because it shapes everything. Published embedding comparisons
routinely admit any of four measurement pitfalls: (i) multi-restart or
portfolio schemes compared against *single-shot* baselines; (ii) a polish or
post-processing step applied to the proposed method only; (iii) tuning on the
reported instances; (iv) survivor-filtered quality statistics (ΔACL computed
only where the proposed method succeeded). Each can manufacture a win the
underlying algorithm does not have; pilot measurements in this programme
demonstrated all four failure modes in-house before any result below was
produced. Every experiment in this paper therefore runs under a frozen
measurement constitution (Section 3): literal (instance, seed) pairing, equal
wall-clock at equal cores, one polish column for all arms, dev/eval instance
separation with a recorded tuning freeze, and pre-registered bars committed to
the repository before each launch. One protocol control is promoted to a
finding in its own right (Section 3.3): at equal wall-clock, best-of-K
restarting of stock minorminer — the implicit "free" baseline upgrade behind
much portfolio work — is worth essentially nothing on realistic cells, and is
actively harmful at the feasibility cliff (§4.1 e0_ceiling).

### 1.1 Contributions

1. **The density-resolved crossover map** (Section 4). 109 cells × 7 strategies
   × paired seeds on Pegasus-16 and Zephyr-12: p\*(n) per topology (falling
   0.7 → 0.12 as n grows 40 → 160); a headroom ridge reaching −33% along the
   feasibility cliff; the cliff itself density-flat at n=140 at 60 s on both
   fabrics; the frontier extended to the busclique bound (K180 on P16, K184 on
   Z12) at ACL better than minorminer manages on far smaller graphs (§4.1,
   §4.1b).
2. **ATE, a never-worse adaptive embedder** (Sections 5.1, 6). Template +
   trimmability-aware assignment + evaluate-both selection. Wins every
   above-crossover evaluation cell (−6.5..−18.4% ER at Holm p = 6.3e-13, K=15;
   −19.4/−32.2% K140 at n=20 pooled pairs, 20/0 and 18/0, p<2e-5 §4.14), ties
   minorminer exactly on sparse controls, zero cross-seed variance where the
   template wins, 5/5 vs 0/5 past minorminer's cliff (§4.10). The precise
   never-worse claim: never worse on ACL beyond seed noise anywhere measured —
   exact ties at K=15, no family-level ACL regression on P16+Z12 at library
   scale beyond one documented near-native family — for a measured sub-second
   wall premium (§4.11, §4.13). The assignment stage beats a random-assignment
   oracle and moves the crossover itself (§4.9, §4.5).
3. **An honest-measurement protocol with a deflator result** (Section 3): the
   best-of-K-at-equal-wall-clock freebie is ≈ 0 on real cells (−0.3..−0.4 ACL
   only on sparse; +0.3..+4.1 — i.e. harmful — at the cliff), deflating a
   common implicit assumption and calibrating every multi-run claim in the
   paper (§4.1 e0_ceiling).
4. **The first ACL-resolved evaluation of clique-seeded search (CLMM)**
   (Section 5.2): the literature's success-count result [ZBED20] reproduced on
   modern hardware graphs and extended with the quality axis it never measured
   — 43/67 minorminer-feasible cells won, up to −30.5%, 3–5× faster on the
   mid-band at one idle worker (§4.13), plus a degeneracy-core variant that is
   stronger dense and must be regime-gated, and a Pegasus/Zephyr asymmetry in
   the mid-band (§4.1, §4.5, §4.10).
5. **The missing move class, exhibited** (Section 5.3): exact bounded-region
   joint pair repair improves the K60 template at 58 source-adjacent pairs
   whose endpoints are both provably single-move stuck — the constructive
   ceiling is real but not tight (K60: 6.73 → ≤ 6.57), and minorminer's
   chain-local dynamics cannot reach these moves (§4.3, §4.4). Productized as
   a polish that improves minorminer's own output on 10/12 feasible cells
   (−0.5..−1.4%, §4.10).
6. **A rank-stability-gated racer** (Section 5.4): selection on early-polish
   ACL is predictive (ρ = 0.885 at the halfway quantum, §4.2) exactly where
   legal-stage selection is dead (r ≈ −0.01, §3.16); the resulting
   successive-halving racer beats best-of-8 minorminer under both the 1-core
   and 8-core fairness readings, pooled −7.7% (p = 1.5e-72), −3.8%/−6.8%
   excluding template-floor wins (§4.6, §4.10).
7. **Anatomy of the incumbent** (Section 7): pre-registered one-switch probes
   inside a byte-identical-at-defaults fork of minorminer 0.2.22 establish
   which undocumented mechanisms are load-bearing (the exhaustive audition,
   the Steiner attach filter, lexicographic overlap pricing), that minorminer
   leaves budget on the table by converging before its deadline, and that the
   2014 paper's own finite-β pricing beats the shipped program by 2.6–5.0% on
   sparse graphs at a feasibility cost — a regime split inside the incumbent's
   own cost function (§4.7, §4.8, §4.8b).
8. **An ecosystem-scale no-regression sweep, executed** (Section 6.8): the
   complete Ember benchmark library on Chimera-16, Pegasus-16 and Zephyr-12 —
   ≈595k runs under bars committed before launch (§4.11). The unguarded first
   batch tripped the bar (42 family × arm violations); the pre-registered
   remedy — regime guards + one re-run — resolved the trail to 19/16/22
   residual trips on P16/Z12/C16, every one decomposed into a *measured*
   seed-noise null (the guards' passthrough mode yields minorminer-at-another-
   seed replicates for free: sd 1.57 pt per family — a methodological
   contribution in its own right) or one of three documented regime boundaries.
   Category verdicts over 35 families: mmpolish 18W/17t/0L (P16), 17/17/1
   (Z12), 15/18/2 (C16); ATE wins dense-structured families on all three
   fabrics with no family-level ACL regression on P16+Z12 beyond one
   near-native family; the committed predictions (clmm's sparse regressions,
   C16 graceful degradation) confirmed verbatim (§4.11).

Throughout, parenthetical anchors (§4.x, §3.x) point into the archived,
append-only laboratory record shipped with the artifact; every table names its
generating script, commit, and CSV (Section 10).

---

## 2 Related work

**The incumbent and its paper.** Minorminer implements the CMR heuristic
[CMR14]: iteratively route each source vertex's chain through weighted shortest
paths, penalizing qubit overuse, until an overlap-free embedding emerges. The
shipped program (0.2.22), however, has outgrown its 2014 description in
load-bearing ways: the union-of-shortest-paths chain constructor described in
the paper is dead code (a nearest-attach Steiner builder ships instead); the
diam(G)^occupancy pricing is replaced by an effectively-infinite-base
exponential table — lexicographic overlap pricing; vertex order is reshuffled
every pass, not once per restart; and an entirely undocumented chain-shortening
phase consumes 85–95% of wall-clock (source-verified, with file:line citations,
in the artifact's mm-internals reference; summarized in Section 7). Much of the
literature benchmarks against, and reasons about, the 2014 sketch. This paper
treats the shipped program as the object of study and measures the
paper-vs-program deltas directly (Section 7).

**Layout-aware and clique-based construction.** minorminer.layout — the
documented practitioner default for geometric sources — computes layouts of
source and target, places by p-norm proximity, and seeds chains accordingly; it
is a baseline arm here, measured at both the frozen-cell and library scales
(Section 6.9: ≈ stock on ACL, strictly worse on success on all three
architectures, isolated lattice-family wins only), not a target.
minorminer.busclique constructs clique and biclique embeddings on
Chimera/Pegasus/Zephyr in polynomial time via a cached decomposition; it
minimizes *maximum* chain length (mean-optimality is open — the (n−1)/14 degree
bound on P16 sits ~30% below busclique K180's 16.67 mean). busclique is the
constructive engine behind both of this paper's dense arms.

**Clique-seeded search.** Zbinden et al. [ZBED20] seed minorminer with
busclique chains (CLMM) or spring-layout placements (SPMM) and show, on
Chimera and Pegasus, that CLMM wins *success counts* above density ≈ 0.08 and
embeds K185+ where minorminer fails at K175–180. Chain quality was never
measured ("running times very comparable"; ACL absent), and Zephyr did not yet
exist. Section 5.2 reproduces the frontier result on P16/Z12 and adds the ACL,
variance, and density axes; the mechanistic insight of theirs that survives
intact is that dense embeddings want long path-shaped chains (induced degree
≤ 2) — precisely what the crossbar template provides by construction.

**Search alternatives.** The Ember benchmark [EMB26] compares six embedders
across 24k+ graphs and three architectures: minorminer ranks first on random
graphs; PSSA — Sugie et al.'s simulated annealing over whole embedding states
with swap/shift moves, busclique-initialized [PSSA20] — leads on complete
graphs (−13.9% vs minorminer); OCT-based virtual-hardware embedding [OCT]
achieves −3% chains at 1/8 the time *when it succeeds* (48.6%), Chimera-only;
ATOM [ATOM23] is fast but worse; CHARME's RL constructor [CHARME24]
reconstructs to 1.96× minorminer ACL (see also [RLQMI26]). Crucially, none of
these results are density-resolved: [EMB26] aggregates over families, so the
regime structure this paper maps is invisible there — minorminer's #1 ranking
on "random" is an average over a regime it wins and a regime it loses by 30%.
A recent SOTA evaluation [SOTA26] confirms minorminer degrades with density
and calls for hybrids, without measuring a crossover. Bipartite-template
construction [BIP25] exploits K_{m,n} periodicity for bipartite sources —
adjacent to the template family here, specialized to a different source class.
Exact and IP approaches [BERNAL20] handle only tiny instances; their
single-block repair operator is an ancestor of the exact-repair polish in
Section 5.3. The 4-clique-network line [PRA24] pursues per-chain redundancy, a
different objective.

**The gap.** Construction is known to win dense (busclique, §3.26; CLMM's
success counts; PSSA-on-K_n) and search is known to win sparse (§3.21;
[EMB26]'s rankings). No published work (i) measures the crossover between
them, (ii) compares constructive against search ACL under a paired,
budget-matched, polish-symmetric, restart-controlled protocol, or (iii) ships
the adaptive selector the two-regime structure implies. Those are this paper's
contributions 1–3; contributions 4–7 populate the sparse side's bounded prizes
(variance, selection, speed, anatomy) under the same protocol.

---

## 3 The measurement protocol

The methods section of this paper *is* its measurement constitution
(protocol.md in the artifact), frozen before the first experiment and amendable
only by dated, justified entries in the laboratory record. This section states
the six rules, the reasoning, and the one control that became a finding.

### 3.1 Why a constitution

Embedding heuristics are stochastic, timeout-governed, and post-processed;
each property is an opening for accidental dishonesty. The four recurring
pitfalls (Section 1) are not hypothetical: each was reproduced in-house in
pilot work before this study — including a portfolio result whose entire
margin was best-of-4 restarts compared against single-shot minorminer, a
−1.8% polish banked by one arm only, and a variance claim that was the
mechanical variance of a min-of-4. The rules below each close one hole. They
are deliberately blunt; where a rule forces a weaker-looking number (and it
does — e.g. the racer's honest margin excludes its strongest cells, Section
6.5), the weaker number is the claim.

### 3.2 The six rules

1. **Pairing.** Headline claims use literal (instance, seed) pairs: every arm
   runs the same instance with the same seed, and ΔACL is computed within
   pairs. The breadth CLI route salts seeds per-algorithm and is labelled
   "(instance, trial) pairing [CLI]" wherever used; the two routes are never
   pooled in one statistic.
2. **No best-of-K vs single-shot, ever.** Any multi-run, portfolio, or
   selection scheme is measured at equal wall-clock on equal cores against
   minorminer given the identical multi-run privilege (best-of-K-parallel
   stock minorminer). Unconditional internal best-of-N is allowed only when
   the entire arm fits inside one stock run's budget (e.g. millisecond-scale
   template assignment seeds). A standing deflator experiment (Section 3.3)
   measures what the multi-run privilege is actually worth.
3. **Polish parity.** Every experiment logs both raw ACL and `acl_spur`
   (spur-pruned, deadline-bounded) for every arm *including minorminer*; a
   table uses exactly one column for all arms and names it. No arm ever banks
   a polish the baseline did not get.
4. **Dev/eval discipline.** Development instance seeds 101–115; evaluation
   seeds 901–915 (K=15), never generated, run, or inspected before a recorded
   tuning freeze. Algorithm seeds: dev 0–4, eval 10–14. Success rates are
   reported separately and unpaired; ΔACL is computed on both-succeed pairs
   only and labelled as such; no survivor filtering.
5. **Budgets.** 60.0 s per attempt everywhere except explicit time sweeps.
   Wall-clock comparisons are valid only within one batch (same host, same
   worker count, arms interleaved); cross-batch and cross-host time
   comparisons are banned; headline speed claims re-measure at one worker on
   an idle machine.
6. **Pre-registration.** Every experiment gets a numbered lab-record entry
   committed before launch: question, script @ git-sha, cells/arms/seeds/
   budget, numeric bars, and a decision tree. Results are appended below a
   line that is never edited after launch. Predictions, where committed, are
   reported against outcomes — including the ones that were wrong (Sections
   7.2, 7.5).

Three consequences of rule 6 deserve mention because they occurred. First, one
kill-gate rule was amended *before launch* when a build smoke revealed the
drafted rule mis-specified the oracle direction (§4.9; Section 5.1.2); the
amendment is dated, justified, and the original preserved. Second, one switch
technically cleared its survival bar in a 4-pair cell and the claim was
declined as below any evidential floor (§4.7; Section 7.2) — the recorded
lesson being that pre-registered bars need minimum-pairs floors. Third, at
library scale the pre-registered ±1 pt success bar turned out to be finer than
the measured single-trial seed-noise floor (sd 1.57 pt per family, §4.11;
Section 6.8.2); the pre-registered remedy path still functioned, nothing was
tightened against the measured noise (that would be tuning on test), and the
recorded lesson is the mirror image of the second: library-scale bars must be
stated against a measured null or buy ≥ 3 trials on small families.

### 3.3 The restart deflator: best-of-K at equal wall-clock is worth ≈ nothing

Rule 2 exists because "our method uses restarts/portfolios, but so could
minorminer" is usually left implicit — the assumption being that best-of-K
restarting is a cheap, transferable upgrade whose benefit a comparison may
quietly pocket. The standing deflator measures that assumption once, on the
frozen dev cells, at *equal wall-clock*: a 60 s budget split into K full
restarts of 60/K s each, best result kept (§4.1 e0_ceiling; 1,000 runs).

**Table 1 — the best-of-K freebie at equal wall-clock (median paired
Δacl_spur vs one 60 s run; §4.1 e0_ceiling).**
<!-- source: docs/paper3/data/e0_ceiling.csv, summary e0_ceiling_summary.txt -->

| cell class | bo3 | bo6 | bo12 | reading |
|---|---|---|---|---|
| sparse (160, 0.05) | −0.32 | −0.43 | −0.32 | real but small; restarts nearly free here |
| mid-band (100, 0.2/0.3) | ≈ −0.2 | ≈ 0 to +0.3 | ≈ 0 to +0.3 | splitting starts to hurt |
| (140, 0.2) | +0.29..+1.36 (all bo-K worse; bo6 0/24 wins) | | | the long grind wants contiguous time |
| cliff, P16 K140 | | | −2.7, but only by burning 137 s vs 59 s | equal wall-clock not even achievable: MM's cooperative timeout overshoots ~2.2× per 5 s slice |
| cliff, Z12 K140 | | | +1.8..+4.1 with 10/25 failures despite 143 s | restarting destroys the one continuous grind that works |

The often-quoted multi-restart gain of −5..−10% ACL does exist — in n = 20–40
toy cells with *full-budget, unequal-time* restarts, which is where pilot
measurements of it came from. It does not transfer to realistic cells at equal
wall-clock (§4.1 e0_ceiling). Three consequences: (i) the strong minorminer
configuration at 60 s is mostly the single run, so rule 2's binding control is
best-of-K only on sparse cells and for the racer's parallel frame; (ii) the
dense margins reported below (−11..−33%) tower over any restart freebie by an
order of magnitude; (iii) any published comparison that pockets a restart
advantage without equal-time controls should be read with this table in hand.

### 3.4 Instruments, environment, hygiene

All experiments run minorminer 0.2.22 (pinned; networkx 3.4.2, numpy 2.2.6,
scipy 1.15.3, dwave-networkx 0.8.19, CPython 3.10) on a dedicated host (EPYC
9575F, 64 physical cores; ≤ 48 workers for any run feeding a wall-clock
column; BLAS/OMP threads pinned to 1; one batch at a time via a run-ledger
lock) (§4.0.3, §4.0.5). Instance generation is cross-machine hash-verified
(§4.0.5). Anatomy probes use a fork of minorminer 0.2.22 that is byte-identical
to stock when all switches are at defaults — same embeddings, same RNG stream —
enforced by a build self-test and contract tests (§4.0.5; Section 7). Candidate
non-minorminer-family arms run under a subprocess watchdog (hard kill at
timeout + 30 s); minorminer-family arms are cooperative and exempt, which
matters when reading wall-clock tails (observed cooperative overruns to 89 s
on failures, §4.1; disclosed wherever they occur). Targets: `pegasus_16` (P16,
5,640 qubits, native clique bound K180) and `zephyr_12` (Z12, degree-20
fabric, clique bound K184 — larger than P16's despite fewer qubits) (§4.0.5);
the M5 library sweep (Section 6.8) adds `chimera_16x16x4` (C16, 2,048 qubits,
degree 6).

**Metrics.** ACL = mean chain length over source vertices (the paper's primary
quality metric; its limits as a proxy are treated in Section 8). Success = a
valid embedding within budget. All headline tables use the `acl_spur` column
(rule 3) on both-succeed pairs (rule 4); Wilcoxon signed-rank per cell with
Holm correction across cells within an arm, rank-biserial correlation reported
(§4.10).

---

## 4 The crossover map

The map experiment (E0) asks one question at scale: for each topology, at each
(n, p), which *strategy family* wins, where is minorminer's feasibility cliff,
and how much headroom above minorminer exists per cell (§4.1)?

### 4.1 Design

- **Grid:** 109 cells — ER G(n, p) ladders over p ∈ {0.05…0.9} at
  n ∈ {40…260}, plus K_n anchors including Zephyr frontier rungs around its
  clique bound — later extended by the two straddle cells (140, 0.12) and
  (140, 0.08) on both topologies (§4.1b). Total 8,559 rows.
- **Arms (7):** `minorminer` (stock 0.2.22); `mmfork-cuthill` (stock dynamics,
  fixed Cuthill–McKee vertex order — a search-guidance control); `clmm`
  (busclique chains as `initial_chains` to stock minorminer, after [ZBED20]);
  `template` (busclique clique right-sized to n, restricted to the source's
  edges, spur-pruned) and `clique` (untrimmed); `pssa` [PSSA20]; `attraction`
  (a placement-guided hybrid, the in-house sparse specialist). `template` and
  `clique` produced identical `acl_spur` in all 202 co-successes and are
  collapsed into one constructive family (§4.1).
- **Seeds/budget:** 3 instances × 5 algorithm seeds per cell (K_n cells one
  instance — instance-invariant; deterministic arms once), 60.0 s per attempt,
  arms interleaved in one queue (§4.1).
- **Pre-registered outputs:** p\*(n) per topology (defined as the smallest
  grid-p where `template` beats `minorminer` on `acl_spur` with ≥ 70%
  both-succeed win rate and median paired ΔACL < 0, per n-ladder); the
  headroom map; a CLMM verdict; the feasibility-cliff table; and a frozen
  standing dev suite chosen by a fixed rule (§4.1). A premise gate (≥ 5%
  best-arm headroom in at least one dense-random cell) was set to stop the
  programme before any algorithm code if the map came back flat; it passed
  with 32 qualifying cells (§4.1).

**Figure 1 — the crossover map** (`figures/fig_crossover_map.{pdf,png}`):
P16/Z12 grids over (n, p), colored by the best non-minorminer arm's median
paired ΔACL_spur% (scale −34..+5: only 3 cells anywhere are red, max +1.4%),
winner letters T/C/A (template/clmm/attraction), hatched frontier cells
(minorminer 0-for-all), grey all-fail cells, and the p\*(n) crossover line.
<!-- fig source: docs/paper3/data/fig_crossover.py over e0_crossover.csv (8,559 rows) -->

### 4.2 The crossover p\*(n)

**Table 2 — p\*(n): smallest density where the trimmed template beats stock
minorminer (§4.1 output 1; §4.1b).**

| n | P16 | Z12 |
|---|---|---|
| 40 | ≤ 0.7 | 0.9 |
| 60 | 0.5 | 0.7 |
| 80 | 0.5 (grid gap 0.08–0.5) | 0.5 |
| 100 | 0.3 | 0.3 |
| 140 | ∈ (0.12, 0.2] (§4.1b) | ∈ (0.12, 0.2] (§4.1b) |
| 160 | 0.12 | 0.12 |
| 180 | 0.3 † | — (minorminer 0/15 at n=180 everywhere) |

† The n=180 P16 ladder lies inside minorminer's feasibility fade (9/15
successes at p=0.3, 1/15 at p=0.7, §4.1); the win-rate-based p\* definition is
dominated there by which pairs exist, and the apparent rise from 0.12 (n=160)
to 0.3 (n=180) reflects the shrinking both-succeed set, not a reversal of the
regime. Inside the fully-feasible region the ladder is monotone: p\* falls as
n grows.

Two readings. First, the crossover *average degree* p\*·(n−1) ≈ 19–40, falling
with n: the construction regime begins well below visually "dense" graphs, and
earlier the larger the problem. By n=140 the construction wins at every
density minorminer survives (§4.1). Second, the two fabrics agree almost
exactly — Z12 sits one grid step denser than P16 at n ≤ 60 and is identical
from n=80 (§4.1) — evidence that the crossover is a property of the
source-density-vs-fabric-capacity trade, not an artifact of one topology.

The straddle extension (§4.1b) sharpened the n=140 row: at (140, 0.12) the
naive identity-assignment template *loses* (median +0.51 P16 / +0.61 Z12) while
at (140, 0.2) it wins 15/15 — so p\*(140) ∈ (0.12, 0.2] on both fabrics. This
cell pair becomes important in Section 5.1.3, where assignment moves the
product's crossover below the naive template's.

### 4.3 Headroom: a ridge along the cliff, and why it exists

Per cell, the headroom is the best non-minorminer arm's median paired
ΔACL_spur% (§4.1 output 2). Its structure (Figure 1):

- −5% at the crossover edge; −11..−19% at n=100; −20..−33% at n=140–180;
  peak −33.4% at P16 K140 (§4.1). The top of the dense-random map:
  −31.8% (Z12, 140@0.9), −30.7% (Z12, 140@0.7), −28.7% (P16, 140@0.7), all
  template wins at 15/15 sweeps (§4.1).
- **The mechanism is minorminer's density sensitivity, not the template's
  density insensitivity being magic.** The template's ACL is density-flat —
  P16 n=140: 12.4–13.2 across p = 0.2–1.0; Z12: 10.0–10.5 — because crossbar
  chains pay once for all-to-all capacity; minorminer's ACL climbs with p
  (14.6 → 19.8 and 11.7 → 15.1 over the same ladders) (§4.1). The dense
  headroom *is* that climb. **Figure 2** (`figures/fig_ladders.{pdf,png}`)
  plots exactly this: median ACL_spur vs p at n ∈ {100, 140, 180} on P16,
  with per-panel p\* markers and partial-success annotations.
- Below p\*, only a thin sparse strip survives: the attraction hybrid's
  −1..−7% at p ≤ 0.08 (including a 15/0 sweep at Z12 (160, 0.05)), persisting
  to n=140 at (140, 0.08) (−0.24 P16 / −0.06 Z12, §4.1b). This is the §3.21
  scaling argument made visible: on sparse expanders everything is
  constant-hunting.

### 4.4 The feasibility cliff and the frontier

At the 60 s budget, minorminer's cliff — the largest n with ≥ 4/5 success — is
**density-flat and topology-identical: n=140 at every p ∈ {0.2…1.0} on both
fabrics**, rising only in the sparse regime (160 at p=0.12, 180 at 0.08, 240
at 0.05) (§4.1 output 4). Past it, P16 fades (n=180: 9/15 at p=0.3, 1/15 at
0.7) while Z12 dies outright (n=180: 0/15 everywhere; K140 already 4/5)
(§4.1).

Budget qualification (from the Section 7 time sweep, §4.7): the cliff is a
*60 s statement*. At (180, 0.3) on P16, success climbs 0/25 → 4 → 14 → 23/25
as the budget grows 5 → 15 → 60 → 180 s (§4.7). Frontier claims in this paper
therefore always state their budget; time-to-first-legal is the right axis for
feasibility work, and the map's cliff line moves right with patience.

The constructive family and clmm extend the dense frontier to the busclique
bound — P16 K180, Z12 K184 = its maximum native clique (K189 all-fail) — **at
better ACL than minorminer achieves on much smaller graphs**: Z12 K184
template 12.98 vs minorminer's own K140 15.09 (−14% on +44 vertices); P16 K180
16.64 vs minorminer K140 19.77 (§4.1). Twelve cells are frontier cells in the
strict sense (minorminer 0-for-all, clmm succeeds), including an overflow band
beyond the clique bound reachable only by seeded search: ER n=200 at p=0.2 on
both fabrics and n=220 at p=0.12 on Z12 (6/15) (§4.1). **Figure 3**
(`figures/fig_frontier.{pdf,png}`) shows success rates at the nine past-cliff
cells with the K184/K140 ACL callout. This reproduces Zbinden's frontier
finding [ZBED20] on modern fabrics and adds the axis it lacked: the frontier
is not merely reachable — it is reachable at *better* quality than search
delivers strictly inside its own feasible region.

### 4.5 Context arms, deflators, and sensitivity

- **pssa ≈ template ± light SA polish**: identical medians in most shared
  cells, better by ~0.1 in 5 small-n cells, 0.45 s median; it inherits the
  template's n ≤ K_max wall and collapses on sparse (+79..+86% at the sparse
  control in later suites, §4.5) (§4.1). Consistent with the thesis: PSSA's
  dense wins *are* the template's.
- **attraction** owns the sparse strip (22/61 paired-cell wins, to −6% at
  p=0.05) and is the slow arm (32 s median on success; dense collapse by
  n=140) (§4.1).
- **clmm** (full verdict in Section 5.2): beats stock minorminer in 43/67
  minorminer-feasible paired cells — every paired cell with n ≥ 80, p ≥ 0.3,
  plus the mid-band down to p=0.08 — up to −30.5% (P16 K140), 36/43 at
  14–15/15 sweeps, and 2–4× faster than minorminer at n ≤ 100 (within-batch;
  the rule-5 idle re-measure reads 3–5× on the mid-band, Table 10, §4.13); it
  loses only sparse (21 cells, worst +1.11 ACL) (§4.1 output 3).
- **Convergence note that shapes the product:** above p\* at n ≈ 100–140,
  clmm and the raw template converge to the same medians (P16 100@0.9: both
  −2.24) — 60 s of seeded search adds nothing the template lacks (§4.1). The
  adaptive embedder's job above p\* is to *be* the template; seeded search's
  marginal value is speed at n ≤ 100, a hair at the K_n frontier, and the
  overflow band.
- **Sensitivity to the polish column (rule 3):** under raw ACL instead of
  `acl_spur`, 19 cells flip best-arm (pssa's unpruned output flatters it:
  spur-prune removes 0.73 ACL from minorminer vs 0.12 from pssa), 6
  crossover-edge cells flip a beats-minorminer verdict, and p\* moves one grid
  step on 3 ladders (§4.1). The pre-registered spur column stands everywhere;
  the flip census is disclosed as the price a polish-asymmetric comparison
  would silently pay.
- **Data quality:** 0 watchdog kills, 0 crashes; 465 failure rows overran
  60 s cooperatively (max 89.0 s); 30/109 cells all-arms-fail; 103 rows are
  template-infeasible by construction (n > clique bound); the cuthill control
  arm fails in < 30 ms on exactly the 3 disconnected sparse instances that
  stock minorminer embeds (a wrapper artifact on a context arm, disclosed;
  fixed with regression tests before M3, no frozen cell affected, §4.12.4)
  (§4.1).

---

## 5 The algorithms

Four arms survived their pre-registered gates into the frozen evaluation. Each
is described as built (full as-built specifications ship in the artifact's
`proposals/` directory), with the development-stage results that shaped it.
Registered-arm hygiene: one registered name per hyperparameter point, no
silent fallbacks, every arm passes the contract suite before entering a batch
(protocol.md).

### 5.1 ATE — the adaptive template embedder (`p3-template`, `p3-ate`)

**Mechanism.** For source G (n vertices) and target T with busclique clique
bound K_max(T):

```
if n <= K_max(T):
    tmpl = busclique.find_clique_embedding(n)     # right-sized, never a subset of a max clique
    POS  = crossing-position matrix               # POS[i][j] = index in chain i of its contact with chain j
    pi   = assign(G, POS)                         # vertex -> template chain (Section 5.1.2)
    embT = spur_prune(relabel(tmpl, pi), G)       # exact trim to the source's edges
    embT = shorten_chains(embT, ~50 ms)
else:
    embT = core-periphery: degeneracy-peel core -> template chains as initial_chains,
           stock minorminer routes the periphery
embM = search arm on the remaining budget         # stock minorminer
return the lower-ACL valid embedding              # ties -> template
```

The evaluate-both selector is the direct product of two map facts: the
template is essentially free (0.2–1.3 s at one idle worker including the exact
prune, Table 10) so it fits inside any search budget, and §3.26's
demonstration that search polish cannot improve the construction means no
interpolation between the arms is needed — evaluate both, keep the better
(§3.26). Below K_max the template
arm is deterministic and succeeds by construction (K_n embeds every subgraph);
`p3-ate`'s success set is the union of both arms'.

**Never-worse, mechanically.** Where the template loses (sparse), the selector
returns the search arm's embedding, whose internal minorminer stage reproduces
stock minorminer under the same seed whenever it completes within the reduced
budget — verified live: on both sparse control cells, ATE vs minorminer is an
*exact* all-tie, 75/75 pairs at Δ = 0.000, at both the dev and eval stages
(§4.5, §4.10). At library scale the same mechanism holds under CLI pairing
(Section 6.8): across the 61,361 eligible P16+Z12 graphs, p3-ate tripped no
family-level ACL bar outside the one documented near-native family — its
unguarded-P16 bar violations were success-only, traced to the n > K_max
core-periphery path's 50/50 budget split and closed by the pre-registered
guard (§4.11) — and the cost of the always-on insurance is measured, not
asserted: +0.0..+0.6 s wall per cell at one idle worker (Table 10, §4.13) and
~+0.6..+1.7% nominal, noise-level deltas on a few small lattice families (the
template-attempt tax, §4.11). The precise product claim is therefore: **never
worse on ACL beyond seed noise, for a sub-second wall premium.** The one
disclosed caveat: the internal selector compares the template's pruned ACL
against the search arm's raw ACL, so a near-tie across
polish columns could in principle mis-pick; experiment tables always re-apply
one polish column to all arms (rule 3), and the effect was never observed to
flip a verdict (as-built notes, proposals/ate.md).

#### 5.1.1 Trimmability-aware assignment

After trimming, a template chain's cost for vertex v is approximately the
*span* of the crossing coordinates of v's neighbors along chain π(v) — a
minimum-linear-arrangement-flavored objective over crossbar slots computed
entirely on POS, with no target-graph work. The pipeline: three seed orders
(identity, Cuthill–McKee, spectral) scored by an exact prune-simulator;
2-swap local search on the span objective from the best seed (deterministic
RNG, 100 ms cap implemented as a proposal-count budget so reruns are
bit-identical); final exact spur-prune. For complete sources the objective is
assignment-invariant and the stage is skipped exactly. The prune-simulator was
validated against the real spur-prune on 7 probe cells: total-cost gap within
−2.7..+1.8%, ≥ 60% of per-vertex values exact, max per-vertex error 2
(proposals/ate.md).

#### 5.1.2 The assignment honesty gate: beating the random oracle (§4.9)

Internal best-of-N over assignment seeds is protocol-legal (rule 2: the whole
arm costs ~1 s), but the 2-swap optimizer had to prove it is not decoration.
The pre-registered gate compares, on the six template-win dev cells: identity
assignment, the three seeds, the shipped pipeline, and a 32-random-assignment
oracle (§4.9; 792 rows, deterministic).

**Table 3 — assignment gains over identity (prune-only ACL, §4.9).**
<!-- source: docs/paper3/data/p1_kg2.csv -->

| cell | shipped pipeline | best-of-32-random | seeds-only |
|---|---|---|---|
| P16 (100, 0.3) | +4.6..+4.8% | +0.6..+1.8% | +2.9..+3.6% |
| P16 (140, 0.2) | +3.6..+4.8% | (same range) | (1.0–1.3 pp short of shipped) |
| Z12 (100, 0.3) | +3.7..+4.3% | | |
| Z12 (140, 0.2) | +3.6..+4.8% | | |
| K_n cells | exactly +0.00% | +0.00% | +0.00% |

The shipped optimizer beats the best of 32 random assignments by 0.24–0.47 ACL
everywhere; the K_n rows are the instrument check (assignment-invariance holds
exactly). Two footnotes with teeth. First, the drafted kill rule assumed the
random oracle upper-bounds the shipped pipeline and would have *killed a
working optimizer*; it was amended before launch when the build smoke showed
shipped beating the oracle, and the amendment is the recorded rule (§4.9).
Second, the scientific content: even dense *random* graphs carry ~4–5% of
assignment-exploitable structure (degree fluctuations and local edge
patterns). The "no latent structure in ER" intuition from the sparse regime
(§3.21) applies to placement geometry, not to slot assignment (§4.9).

#### 5.1.3 Assignment moves the crossover (§4.5)

The straddle cell (140, 0.12) — where the naive identity-assignment template
loses (+0.51/+0.61 median, §4.1b) — is exactly where the ~4% assignment gain
lands: the shipped ATE template *wins* there, P16 −0.529 (−4.7%, 23/1), Z12
−0.322 (−3.6%, 22/3) (§4.5). The product's crossover at n=140 therefore sits
at or below p=0.12, one grid step under the construction that defined the map
(and above (140, 0.08), where the template loses by +2.6..+3.2 ACL and the
selector defers to minorminer, §4.1b). The map is drawn with the naive
template; the shipped embedder widens the dense regime beyond it.

#### 5.1.4 The ceiling is not tight (§4.3, §4.4)

Is the template a floor? No — and establishing that sharpened the regime
claim. An exact bounded-region probe on the K60/P16 template (the §3.26
instrument, 404 qubits after prune, ACL 6.7333) found: single-vertex exact
repair improves only 2/60 vertices, but *joint pair* repair improves 103 of
the first 400 source-adjacent pairs (94 × −1 qubit, 9 × −2; 71 proven
pair-optimal) — including **58 pairs where both endpoints are provably
single-move stuck** (one endpoint proven stuck at radii 2, 3 and 4; the
partner chain relocates laterally at unchanged length to free the needed
qubit) (§4.3). Driving the sequential fixpoint (spur/shorten/x1/x2,
longest-first, deterministic): 404 → 394 qubits, ACL 6.7333 → 6.5667 (−2.5%),
deadline-bound at 30 minutes — an upper bound on the K60 template+polish
ceiling (§4.4). The regime picture at K60 is thus: minorminer 7.83 / template
6.73 / template + exact moves ≤ 6.57 (§4.4, §3.26). The economics matter as
much as the number: 30 minutes of exact repair bought −2.5%, so under the 60 s
discipline only a slice is capturable; the full-depth figure belongs to the
ceiling discussion, not the product arm (§4.4).

### 5.2 CLMM++ — clique-seeded search (`p3-clmm`, `p3-clmm-core`)

`p3-clmm` is the faithful [ZBED20] reproduction and the paper's mandatory
literature control: busclique chains for k = min(n, K_max) passed as
`initial_chains` to a *single-shot* stock minorminer call (source passed as a
graph object — the edge-list form silently drops isolated vertices, §3.23);
when k < n, chains go to the k lowest-degree vertices (sparse) or k random
vertices (dense), per their rule. `p3-clmm-core` replaces the selection with
the k highest-coreness vertices from a degeneracy peel and spur-prunes the
seeded chains against the seeded-subgraph edges before search — seed the hard
substructure, leave the periphery to the phase minorminer is good at.

Findings across E0, the dev gates, and the frozen eval:

- **The ACL axis the literature never measured** (§4.1 output 3): 43/67
  minorminer-feasible paired cells won, up to −30.5% (P16 K140), 3–5× faster
  on the mid-band at one idle worker (Table 10, §4.13); loses only sparse —
  regime-gated in any product use (eval sparse losses +13..+16%,
  Holm-significant, §4.10). The shipped v1.1 arm carries that gate: below
  density 0.15 it passes through to full-budget stock minorminer, with a
  guard=False kwarg preserving the faithful [ZBED20] control (§4.11;
  Section 6.8.1).
- **Convergence with the template** above p\* at n ≈ 100–140 (§4.1): the seeds
  do the work; the search adds nothing there. clmm's marginal value is speed,
  a hair at the frontier (Z12 K179: clmm 12.966 vs template 12.972, Table 7),
  and the overflow band n=200–220 beyond the clique bound (§4.1).
- **The core variant is a dense-side tool** (§4.5 B2): stronger than faithful
  clmm at (140, 0.2) on both fabrics (eval −14.8% vs −12.0% on P16, §4.10)
  and ties-or-beats at K_n, but *backfires* on the mid-band straddle
  ((140, 0.12): +3.7/+7.1% at eval where clmm is −1.6/+5.2%, §4.10) — it is
  shipped under an explicit density gate, and the gate is part of the claim.
- **Topology asymmetry, reported as found** (§4.5, §4.10): the mid-band edge
  is Pegasus-specific at n = 100–140. P16 (100, 0.2): −6.0% (Holm 1.2e-10);
  the same cell on Z12: +1.1%. P16 (140, 0.12): −1.6% (ns); Z12: +5.2%
  (significant loss). Zephyr's higher connectivity appears to leave less for
  clique seeds to pre-solve in the mid-band; the dense-side wins are
  fabric-independent.
- **Near-determinization**: core seeding collapses cross-seed variance to a
  0.06× median ratio vs minorminer (clmm 0.60×) (Table 6) — seeded
  search inherits much of the construction's reproducibility.
- **Library-scale boundaries, documented as such** (§4.11; Section 6.8.3):
  category record 7W/24t/4L (P16 merged), 6W/27t/2L (Z12), with
  dense-structured wins (Z12 bipartite −12.0%, complete −5.1%, turan −4.5%,
  kneser −2.5%) and two real boundaries — johnson (+0.228 mean ACL over 74
  graphs at density 0.172: genuinely seeded, and the seeds mislead the search
  exactly where the raw construction succeeds; p3-ate wins the same family
  −0.63) and the C16 gate (8 mid-family trips of +0.11..+0.28 because the
  0.15 threshold, calibrated on P16/Z12, sits below Chimera's higher
  crossover — the map's per-topology p\* made operational).

### 5.3 mmpolish — exact joint repair as a polish (`p3-mmpolish`)

The §4.3 probe did more than un-tighten the ceiling: it exhibited, with
validity certificates, a move class *outside* minorminer's reach — coordinated
two-chain relocations where each chain alone is provably at its bounded-region
optimum. minorminer's grind performs single-chain rip-and-reroute; §3.26
showed from one side that it cannot improve the template, and §4.3 shows from
the other side what the missing moves are (§4.3; the swap-gadget unit test
reproduces the scenario in miniature, proposals/polish.md).

`p3-mmpolish` productizes the operator: stock minorminer for 70% of the
budget (the v1.0 split; shipped v1.1 gives minorminer the *full* budget and
polishes on the leftover wall — the M5 redesign, below), then an anytime
polish (spur-prune, free-space shorten, exact single-vertex repair, exact
joint-pair repair; longest-first with dirty-set scheduling; monotone and valid
by construction). The exact engine is a
deterministic branch-and-bound over connected subgraphs of a radius-2 region
with admissible bounds — no IP solver; every move either proves optimality
within its region or reports itself unproven (§4.3 as-built).

Verdict (dev, confirmed at eval, §4.5, §4.10): a small, near-universal, free
improvement on minorminer's own output in the search regime — median wins on
all 10 minorminer-feasible ER cells at dev (18–25/25, typically −0.5..−1.2%);
Holm-significant at 10/12 feasible cells at eval (−0.5..−1.4%, sweeps of
75/0/0 typical). It does *not* help at the cliff (Z12 K140 +4.5%: the 30%
budget reservation costs more than repair returns; K179/K180 fail with their
base) — a mid/sparse-band add-on, shipped as such (§4.5, §4.10).

The M5 sweep both generalized and repaired the arm (Section 6.8). The v1.0
70/30 budget split cost success on legalization-hard families (binary_tree
9.1 pt, frustrated_square 6.9, weak_strong 4.1 on unguarded P16) — the one
committed M5 prediction that failed — and the pre-registered remedy became the
better design: v1.1 gives minorminer the full budget and spends only the
*leftover* wall (real on most instances, because stock patience expires early,
Section 7.3), making success ≡ stock by construction while preserving the
gains (§4.11). Category record across the library: **18W/17t/0L on P16,
17W/17t/1L on Z12, 15W/18t/2L on C16** — 50 wins, 52 ties, 3 losses over 105
architecture × family verdicts, with wins like watts_strogatz −3.2% over
Z12's 11,988-graph family and −2.6% over 5,309 C16 pairs (§4.11). One scope
note applies to all of this arm's margins: sub-2% ACL deltas are statistically
robust here but not established as practically significant downstream
(Section 8, item 2).

### 5.4 The racer (`p3-race8`) — selection under strict fairness

The racer is the sparse-side counterpart of evaluate-both: race K
heterogeneous arms, allocate budget by successive halving, return the best.
Portfolio schemes are where unfair baselines are easiest to smuggle in, so
this arm exists under the strictest frame in the paper: its baseline is
*best-of-K stock minorminer at equal wall-clock on equal cores* — never
single-shot — in both a 1-core sequential and an 8-core parallel reading
(rule 2).

**The gate (§4.2).** Selection needs a signal. Legal-stage ACL carries none
(r ≈ −0.01 to final, §3.16), so the racer was gated on a pre-registered
rank-stability probe: after one quantum of warm-restart polish, does early ACL
predict final ACL across seeds? Median per-instance Spearman ρ(best@q4,
best@q8) = **+0.885**, 9/9 instances ≥ 0.5, pooled instance-centered +0.876
(p ≈ 1e-46, N=144); even q1 pools at +0.72 (§4.2). The basin's quality becomes
visible after one quantum of grind — selection is possible precisely one phase
later than where it is dead. The same trajectories yielded the patience curve
that motivates the design (below) and Section 7.3's finding.

**Mechanism (as built).** K=8 roster: the template (one deterministic slot,
never halved — it costs ~1 s and floors success and quality where it wins),
stock minorminer × 4 seeds, cuthill, clmm, clmm-core. Legalize all cheaply
(legalization is 5–15% of a run's cost, §3.15); then rounds of fixed polish
quanta (budget/16) using the §4.2-verified warm-restart pattern; halve the
field by best-so-far ACL each round; the survivor grinds the remainder;
best-ever valid embedding wins. The control, `race_baseline_bestofk`, lives in
the same module so its accounting cannot drift.

**Why it wins where it wins (§4.6, §4.7).** On sparse cells, parallel
best-of-8 minorminer finishes in 6.4–8.0 s median (§4.10 Table 4b): stock
patience expires and minorminer *leaves the rest of the wall-clock on the
table* (Section 7.3). The racer converts that abandoned budget into ACL by
warm-restart grinding of the best basins; sequentially, it additionally beats
uniform 7.5 s slicing by adaptive allocation (uniform splitting is *worse*
than a single 60 s run on 3/4 smoke pairs — the e0_ceiling result again,
§4.6, proposals/portfolio.md).

**The honest read.** On mid cells the race winner is the template 72–75/75
(§4.10 Table 4b) — those wins are the ATE story wearing a racer hat, and the
pre-registration *excludes them from the selection claim* (§4.6). The
selection claim rests on the template-free sparse cells, both fairness
readings, and holds at dev (P16 (160, 0.05): seq −2.31%/84%, par −5.57%/96%;
Z12: seq −4.97%/88%, par −7.53%/100%, §4.6) and at eval (Section 6.5). One
dev read missed its bar and is reported, not claimed: Z12 (100, 0.2) parallel,
−1.86% at 76% vs the −2% bar (§4.6).

---

## 6 Evaluation

### 6.1 Frozen-eval design (§4.10)

Every arm's configuration was frozen at a recorded commit before the
evaluation instances existed: eval instance seeds 901–915 (K=15 per cell) had
never been generated, run, or inspected before the freeze; algorithm seeds
10–14; 60.0 s; the 14 frozen cells of the standing dev suite (7 per topology:
two mid-band cells, the straddle pair, K140, one past-cliff K_n, one sparse
control); 6,314 main rows + 1,800 racer rows (§4.10). Statistics: Wilcoxon
signed-rank per cell on both-succeed pairs, Holm-corrected across cells within
each arm, rank-biserial reported. p3-template is deterministic — its one value
per instance pairs against all 5 minorminer seeds of that instance; those
pairs are not independent and its p-values are anti-conservative (flagged
*det; `p3-ate` carries its own seeds and is the arm the claims rest on)
(§4.10, m4_headline.md).

**Headline: every development verdict confirmed on fresh instances with no
tuning inflation** — margins within ~1–2 pp of dev on the ER cells (see Table
11 for the two K_n exceptions and their explanation) (§4.10).

### 6.2 ATE vs minorminer (Table 4)

**Table 4 — p3-ate vs minorminer, all 14 frozen cells (acl_spur; both-succeed
pairs; Holm across cells; §4.10 Table 1).**
<!-- transcribed from docs/paper3/data/m4_headline.md Table 1, p3-ate rows -->

| cell | pairs | med ΔACL | Δ% | W/L/T | p_Holm | r_rb | succ ate | succ MM |
|---|---|---|---|---|---|---|---|---|
| P16 (100, 0.2) | 75 | −0.860 | −9.3% | 75/0/0 | 6.3e-13 | 1.00 | 75/75 | 75/75 |
| P16 (100, 0.3) | 75 | −1.650 | −15.3% | 75/0/0 | 6.3e-13 | 1.00 | 75/75 | 75/75 |
| P16 (140, 0.12) | 75 | −0.779 | −6.8% | 72/3/0 | 6.3e-13 | 0.99 | 75/75 | 75/75 |
| P16 (140, 0.2) | 75 | −2.707 | −18.4% | 75/0/0 | 6.3e-13 | 1.00 | 75/75 | 75/75 |
| P16 K140 | 5 | −3.186 | −19.5% | 5/0/0 | 0.250 † | 1.00 | 5/5 | 5/5 |
| P16 K180 | 0 | n/a — MM never succeeds | | | | | 5/5 | 0/5 |
| P16 (160, 0.05) | 75 | +0.000 | +0.0% | 0/0/75 | 1.000 (all-tie) | 0.00 | 75/75 | 75/75 |
| Z12 (100, 0.2) | 75 | −0.480 | −6.5% | 72/3/0 | 6.3e-13 | 0.99 | 75/75 | 75/75 |
| Z12 (100, 0.3) | 75 | −1.190 | −13.8% | 75/0/0 | 6.3e-13 | 1.00 | 75/75 | 75/75 |
| Z12 (140, 0.12) | 75 | −0.214 | −2.4% | 55/19/1 | 9.1e-07 | 0.70 | 75/75 | 75/75 |
| Z12 (140, 0.2) | 75 | −1.986 | −17.1% | 75/0/0 | 6.3e-13 | 1.00 | 75/75 | 75/75 |
| Z12 K140 | 5 | −5.136 | −32.9% | 5/0/0 | 0.250 † | 1.00 | 5/5 | 5/5 |
| Z12 K179 | 0 | n/a — MM never succeeds | | | | | 5/5 | 0/5 |
| Z12 (160, 0.05) | 75 | +0.000 | +0.0% | 0/0/75 | 1.000 (all-tie) | 0.00 | 75/75 | 75/75 |

† K_n cells are instance-invariant; the frozen-eval table carries the original
n=5 pairs, and §4.14's seed-deepening (15 fresh eval seeds, pooled n=20) settles
significance: ate P16 K140 −19.4% at 20/0 (p=1.9e-6), Z12 K140 −32.2% at 18/0
(p=7.6e-6). At n=5 alone, unanimity could not reach conventional significance
there — and the margin itself is baseline-seed-sensitive (P16 K140 swung
−33.5% dev → −19.5% eval; minorminer's cliff-seed std is 3.09 ACL, Table 6;
§4.12.3). Independent corroboration comes from the map's own K140 headroom
(−33.4% at P16, §4.1) and the 15/15 sweeps at the adjacent dense-ER cells
((140, 0.7): −28.7% P16 / −30.7% Z12; (140, 0.9): −31.8% Z12, §4.1). The K140
rows below keep the frozen-eval n=5 values; the pooled n=20 statistics (§4.14) are the citable ones.

Reading: every above-crossover ER cell is Holm-significant at 6.3e-13 with
rank-biserial 0.99–1.00 and win counts of 72–75 out of 75; both sparse
controls are *exact* ties — 75 pairs at Δ = 0.000 — which is the never-worse
selector observed at K=15 rather than asserted; and both past-cliff cells are
5/5 vs 0/5. The straddle cell is the smallest win by design: it lies below
the naive template's crossover and above the shipped one's (Section 5.1.3).

### 6.3 All arms at a glance (Table 5) and variance (Table 6)

**Table 5 — median paired Δ% vs minorminer, all arms × cells (acl_spur;
† = Holm p < 0.05; §4.10 Table 1).**
<!-- condensed from docs/paper3/data/m4_headline.md Table 1 -->

| cell | cuthill | template | clmm | clmm-core | mmpolish | pssa | attraction |
|---|---|---|---|---|---|---|---|
| P16 (100, 0.2) | −2.5† | −9.3† | −6.0† | −5.7† | −0.6† | +0.8 | −0.2 |
| P16 (100, 0.3) | −1.5† | −15.3† | −12.2† | −12.2† | −0.7† | −10.7† | +2.8† |
| P16 (140, 0.12) | −0.9 | −6.8† | −1.6 | +3.7† | −0.9† | +6.0† | −1.9 |
| P16 (140, 0.2) | −2.4† | −18.4† | −12.0† | −14.8† | −0.5 | −13.2† | +5.5† |
| P16 K140 (n=5; §4.14 n=20: −19.4%, 20/0, p=1.9e-6) | +3.1 | −19.5 | −15.9 | −19.5 | −0.3 | −18.6 | fail 0/5 |
| P16 (160, 0.05) | +0.9 | +35.6† | +16.2† | +22.4† | −1.4† | +85.9† | −5.7† |
| Z12 (100, 0.2) | −1.5 | −6.5† | +1.1 | +0.3 | −0.8† | +1.1 | −1.8 |
| Z12 (100, 0.3) | −2.2† | −13.8† | −10.0† | −10.3† | −0.8† | −10.1† | +1.0 |
| Z12 (140, 0.12) | −0.4 | −2.4† | +5.2† | +7.1† | −1.0† | +8.1† | −1.0 |
| Z12 (140, 0.2) | −1.4 | −17.1† | −11.9† | −13.8† | −0.6† | −13.5† | +1.8 |
| Z12 K140 (n=5; §4.14 n=20: −32.2%, 18/0, p=7.6e-6) | −7.0 | −32.9 | −31.9 | −33.0 | +4.5 | −32.9 | fail 0/5 |
| Z12 (160, 0.05) | +0.4 | +39.4† | +13.1† | +18.2† | −1.4† | +83.0† | −4.1† |

(The two past-cliff K_n cells have no pairs and are carried by Table 7.
p3-template rows carry the *det caveat of Section 6.1. One product note: the
shipped v1.1 clmm passes through to stock minorminer at (140, 0.12) — the one
frozen cell below its M5 density gate; this table measures the v1.0 arm,
§4.11.)

The regime structure is legible in every column: the constructive family and
its seeded relatives win everything above the crossover and lose the sparse
controls badly (template +35..+39%, pssa +83..+86% there); the sparse
specialists invert (attraction −4..−6% on the controls, losses above p\*);
mmpolish is the one arm in the black almost everywhere it is feasible, at
small magnitude; cuthill's fixed order is worth −1.5..−2.5% in the mid-band
(significant on 5 cells, §4.10) — the ordering lever from the search-guidance
line, still alive under this protocol.

**Table 6 — cross-seed ACL variance ratio vs minorminer (per-cell median of
per-instance stds; median across cells; §4.10 Table 2).**
<!-- source: m4_headline.md Table 2 -->

| arm | cuthill | template | ate | clmm | clmm-core | mmpolish | pssa | attraction |
|---|---|---|---|---|---|---|---|---|
| median ratio | 0.91× | 0.00× | **0.00×** | 0.60× | **0.06×** | 0.94× | 0.00× | 0.91× |

ATE's row is the operational half of the never-worse claim: **0.00× wherever
the template wins — zero cross-seed variance by construction — and exactly
1.00× where it defers to minorminer** (the sparse controls) (§4.10). For
scale, minorminer's per-cell median std runs 0.24–0.60 ACL on ER cells and
3.09 at P16 K140 (§4.10 Table 2): at the cliff, stock minorminer's
seed-to-seed spread exceeds its entire median margin to the template.
clmm-core's 0.06× shows seeding alone near-determinizes the search.

### 6.4 The frontier (Table 7)

**Table 7 — past-cliff success and quality (unpaired counts; §4.10 Table 3).**
<!-- source: m4_headline.md Table 3 -->

| cell | minorminer | cuthill | mmpolish | attraction | template | ate | clmm | clmm-core | pssa |
|---|---|---|---|---|---|---|---|---|---|
| P16 K180 succ | 0/5 | 0/5 | 0/5 | 0/5 | 1/1 | 5/5 | 5/5 | 5/5 | 5/5 |
| P16 K180 med acl_spur | — | — | — | — | 16.639 | 16.639 | 16.644 | 16.644 | 16.644 |
| Z12 K179 succ | 0/5 | 0/5 | 0/5 | 0/5 | 1/1 | 5/5 | 5/5 | 5/5 | 5/5 |
| Z12 K179 med acl_spur | — | — | — | — | 12.972 | 12.972 | 12.966 | 12.972 | 12.978 |

Every search-family arm (minorminer, cuthill, mmpolish, attraction) is
0-for-all past the cliff; every construction-carrying arm is perfect, at
template-or-better ACL. Combined with the map's K184 result (Z12's clique
bound embedded at 12.98, better than minorminer's own K140 at 15.09, §4.1),
the frontier section of the thesis needs no statistics: the regimes differ in
kind, not degree.

### 6.5 The racer at eval scale (Table 8)

**Table 8 — racer vs best-of-8 minorminer, both fairness readings (acl_spur;
§4.10 Table 4).**
<!-- source: m4_headline.md Table 4; excl-tpl = pairs whose race winner is the template excluded, per the §4.6 pre-registration -->

| cell / pool | read | n | med Δ% | win% | p |
|---|---|---|---|---|---|
| P16 (160, 0.05) | seq, 1 core | 75 | −3.25% | 80% | 1.8e-9 |
| P16 (160, 0.05) | par, 8 cores | 75 | −6.42% | 96% | 7.9e-14 |
| Z12 (160, 0.05) | seq, 1 core | 75 | −4.27% | 88% | 1.2e-11 |
| Z12 (160, 0.05) | par, 8 cores | 75 | −7.87% | 97% | 7.9e-14 |
| POOLED (6 cells) | seq, 1 core | 450 | −7.73% | 95% | 1.5e-72 |
| POOLED (6 cells) | par, 8 cores | 450 | −6.61% | 95% | 5.0e-73 |
| POOLED, excl-tpl | seq, 1 core | 154 | −3.78% | 84% | 2.8e-20 |
| POOLED, excl-tpl | par, 8 cores | 160 | −6.81% | 96% | 1.6e-27 |

The (160, 0.05) rows are the selection claim in its pure form: the template
never wins there (race winners: minorminer 58–60, cuthill 15–17 of 75, §4.10
Table 4b), so the margin is entirely selection + budget reclamation, and it
holds on both fabrics under both fairness readings. The pooled −7.7% is
dominated by mid cells where the winner is the template 72–75/75 — reported
for completeness, but the *claimed* portfolio residual is the excl-tpl pool:
−3.8% sequential, −6.8% parallel. Mechanism check at eval (§4.10 Table 4b):
best-of-8-parallel minorminer finishes the sparse cells in 6.4–8.0 s median
against the racer's 60 s — the margin is real time reclaimed from stock
patience (Section 7.3), allocated by a gate that works (§4.2).

### 6.6 Cost (Tables 9 and 10)

**Table 9 — median wall seconds per arm (P16 rows; within-batch only, rule 5;
§4.10 Table 5).**
<!-- source: m4_headline.md Table 5 -->

| cell | minorminer | template | ate | clmm | clmm-core | mmpolish | pssa | attraction |
|---|---|---|---|---|---|---|---|---|
| (100, 0.2) | 16.2 | 0.4 | 17.0 | 5.2 | 4.5 | 60.1 | 0.5 | 29.4 |
| (100, 0.3) | 27.4 | 0.6 | 28.6 | 6.6 | 6.5 | 60.2 | 0.5 | 48.3 |
| (140, 0.12) | 23.4 | 0.5 | 23.9 | 9.2 | 4.9 | 60.1 | 0.6 | 38.4 |
| (140, 0.2) | 42.7 | 0.6 | 42.2 | 11.5 | 8.8 | 60.1 | 0.6 | 60.3 |
| K140 | 60.8 | 1.3 | 62.0 | 61.1 | 62.6 | 60.6 | 0.6 | 73.2 |
| K180 | 72.3 | 1.3 | 68.2 | 68.0 | 62.9 | 53.3 | 0.6 | 81.1 |
| (160, 0.05) | 6.0 | 0.4 | 6.4 | 4.8 | 4.0 | 60.0 | 0.8 | 13.1 |

The template's 0.4–1.3 s column is the construction thesis in units of time:
above the crossover, the winning embedding costs two orders of magnitude less
wall-clock than the search it beats by 6–33%. ATE's cost tracks minorminer's
(its search arm dominates its wall where the template has already won —
by-design conservatism; an early-exit heuristic is deliberately absent so the
never-worse property stays unconditional). mmpolish pins its full budget by
construction. Cooperative overruns past 60 s (K_n columns; attraction to 81 s)
are the disclosed timeout coarseness of Section 3.4. Cross-batch and
cross-host comparisons of Table 9 are invalid (rule 5); every standalone speed
claim in this paper therefore comes from the rule-5 re-measure — one worker,
strictly sequential, idle host, 144 runs (§4.13):

**Table 10 — median wall seconds at one idle worker (workers=1, idle host;
§4.13).**
<!-- source: docs/paper3/data/m6_speed_summary.txt / m6_speed.csv @ deb88153 -->

| cell | minorminer | mm-layout | template | ate | clmm | mmpolish |
|---|---|---|---|---|---|---|
| P16 (100, 0.3) | 28.5 | 23.4 | 0.4 | 29.1 | 5.7 | 60.1 |
| P16 (140, 0.2) | 28.9 | 30.6 | 0.3 | 28.9 | 9.2 | 60.2 |
| P16 K140 | 60.9 | 69.2 | 1.2 | 61.0 | 51.9 | 61.6 |
| P16 (160, 0.05) | 5.1 | 5.6 | 0.2 | 5.4 | 5.1 | 60.0 |
| Z12 (100, 0.3) | 16.5 | 18.9 | 0.4 | 16.8 | 6.3 | 60.2 |
| Z12 K140 | 60.8 | 68.9 | 1.3 | 60.9 | 63.3 | 60.5 |

Every within-batch M4/M5 wall ratio reproduces idle (§4.13), and the idle
reads are the citable ones: the template runs 0.2–1.3 s at every cell —
20–150× under stock minorminer while 15–33% better on the dense cells; clmm's
mid-band is 5.7–9.2 s against minorminer's 16.5–28.9 s (3–5×) and joins the
full-budget class at K140; ATE costs minorminer plus a sub-second insurance
premium (+0.0..+0.6 s per cell — the always-run template attempt; Section 9);
mmpolish pins ≈ 60 s by design (it spends the leftovers); and
minorminer-layout is 1.1× *slower* than stock at the K140 cells (69 vs 61 s)
while failing them 0/5 (Section 6.9).

### 6.7 Dev-to-eval stability (Table 11)

**Table 11 — ATE margins, dev (seeds 101–105 × 0–4) vs eval (901–915 ×
10–14).** <!-- dev: dev_suite_summary.txt (§4.5); eval: m4_headline.md (§4.10) -->

| cell | dev Δ% | eval Δ% |
|---|---|---|
| P16 (100, 0.2) | −8.2% | −9.3% |
| P16 (100, 0.3) | −16.8% | −15.3% |
| P16 (140, 0.12) | −4.7% | −6.8% |
| P16 (140, 0.2) | −19.3% | −18.4% |
| P16 K140 | −33.5% | −19.5% |
| Z12 (100, 0.2) | −4.4% | −6.5% |
| Z12 (100, 0.3) | −15.2% | −13.8% |
| Z12 (140, 0.12) | −3.6% | −2.4% |
| Z12 (140, 0.2) | −17.6% | −17.1% |
| Z12 K140 | −30.6% | −32.9% |

ER cells reproduce within ~1–2 pp — no tuning inflation. The one large swing,
P16 K140 (−33.5% → −19.5%), is a property of the *baseline*, not the arm: the
template's value is fixed (13.171 at both stages, §4.5, §4.10) while
minorminer's K140 output swings by seeds (median std 3.09 ACL, Table 6) — at
the cliff, which five seeds stock minorminer gets determines whether it loses
by a fifth or a third.

### 6.8 The full-library sweep: no-regression at ecosystem scale (§4.11)

The final experiment is the pre-registered sweep of the *complete* Ember
benchmark library on all three flagship architectures — every library graph
that passes the per-topology pigeonhole (n ≤ qubit count): 31,140 graphs on
P16, 30,221 on Z12, 27,628 on C16 by pigeonhole (23,994 after
benchmark-manifest eligibility at run time) — more inclusive than the
benchmark's own embeddability sets; "attempted and failed" is data (§4.11 and
two dated pre-launch amendments). Arms: {minorminer, p3-template, p3-ate,
p3-clmm, p3-mmpolish} on the full eligible sets; minorminer-layout on the
n ≤ 1000 subsets (25,010 per topology; Section 6.9). ≈ 595k measured rows over
seven batches (three main + the P16 guarded re-run + three layout);
"(instance, trial) pairing [CLI]" labels mandatory; raw-ACL column (the CLI
logs no spur; stated on every table); wall-time within-batch only. The racer
is excluded by design (it burns the full budget on every row; its claims are
settled on the selection cells, §4.6/§4.10).

Pre-registered bar (verbatim, applied per topology × family): **no family mean
ΔACL worse than +0.10, and no success-rate drop over 1 point, for any p3 arm
vs minorminer** — otherwise the failing arm ships behind a density/regime
guard and the sweep re-runs once with the guard (§4.11). That remedy clause is
load-bearing below. Committed predictions: p3-ate ties minorminer on
sparse/structured families (auto-select falls back) and wins dense-structured
(complete/Turán/dense-bipartite); p3-clmm regresses on sparse families "and is
expected to need the density gate"; p3-mmpolish never regresses; and on C16 —
whose clique bound (~64) shrinks the template regime — p3-ate must degrade to
minorminer *gracefully*: that graceful degradation is the C16 claim (§4.11).

#### 6.8.1 The bar fires; the pre-registered remedy answers

The unguarded P16 batch (155,700 rows, arms v1.0) tripped the bar 42 times
(family × arm), and the violations decompose into exactly three mechanisms
(§4.11):

1. **p3-clmm ACL losses on sparse/structured families** (star +1.28, wheel
   +1.48, kagome +0.39, planted +0.36, grid +0.27 mean ΔACL) — the committed
   prediction, verbatim. Guard: below density 0.15 the arm passes through to
   full-budget stock minorminer (recorded in run metadata as passthrough; a
   guard=False kwarg preserves the faithful [ZBED20] control for script-route
   science).
2. **p3-ate success drops concentrated on large sparse lattices** (bcc 4.2 pt,
   triangular 3.6, grid 1.3) — all from the n > K_max core-periphery path's
   50/50 budget split halving minorminer's effective budget on time-marginal
   instances. On ACL the arm tripped nothing in the batch: its violations were
   success-only (§4.11). Guard: attempt core-periphery only at density ≥ 0.15
   (the overflow regime where it ever wins); sparse overflow leaves minorminer
   the full budget.
3. **p3-mmpolish success drops on legalization-hard families** (binary_tree
   9.1 pt, frustrated_square 6.9, weak_strong 4.1) — the fixed 70/30 budget
   split flipped instances that need > 70% of the budget to legalize. This is
   the one committed prediction that *failed* ("p3-mmpolish never regresses"
   held on ACL, not on success), and the remedy became the better design:
   v1.1 gives minorminer the full budget and the polish spends only the
   leftover wall — real on most instances because stock patience expires early
   (Section 7.3) — making success ≡ stock by construction.

The guards are regime gates at thresholds read off the E0 map (0.15 sits
between the measured p\* ladders), not fits to the sweep: they alter only
off-regime behavior; the single pre-registered re-run allowance was spent
exactly once (P16: the three guarded arms × 30,768 rows each, paired against
the original batch's minorminer/p3-template rows at identical derived seeds);
and the sole frozen-suite cell any guard touches is (140, 0.12), below clmm's
gate (Tables 4–5 measure v1.0; §4.11). This is the pre-registration doing its
job in the failure direction: the bar fired, the remedy was already written
down, and no post-hoc tuning entered the arms.

#### 6.8.2 The passthrough null: seed noise, measured for free

The guards produced a methodological instrument this paper did not plan.
**Below its gate, guarded p3-clmm *is* stock minorminer at a different derived
seed**, so on the 26 Z12 families under the gate the arm-vs-minorminer success
differences measure the CLI (instance, trial) pairing noise floor directly:
mean −0.00 pt, sd 1.57 pt, max |4.55| pt per family, symmetric (§4.11). Any
guarded arm provides minorminer-at-another-seed replicates for free — a
full-library comparison can carry its own measured null without spending one
extra run. Read against that null, every residual Z12 success violation
(1.4–4.5 pt: bcc, cubic, frustrated_square, king, cycle, wheel — correlated
across all three arms, which are minorminer-equivalent there post-guard) lies
*inside* it: seed noise, quantified, not regression. The same signature
recurs on P16 and C16 as single-graph flips in 11–72-graph families
(binary_tree's "9.1 pt" and "10 pt" trips are one graph each, dropped
identically by all three arms) (§4.11). The recorded lesson (Section 3.2): the
±1 pt bar sits below the single-trial noise floor at small-family granularity;
future library bars should be stated against a measured null or buy ≥ 3
trials. Nothing was tightened against the measured noise — that would be
tuning on test.

#### 6.8.3 Verdicts: three architectures, three documented boundaries

**Table 12 — M5 scoreboard: category verdicts over 35 families ((instance,
trial) pairing [CLI]; raw ACL; category win = median paired ΔACL < −0.5% at
≥ 55% win rate, loss symmetric, tie otherwise; §4.11).**
<!-- sources: m5_z12_results.md / m5_z12_percategory.txt (Z12, in-repo); P16/C16 per-category tables archived with their batches; verdict trail in notes.md §4.11 -->

| batch | eligible graphs | bar trips | p3-ate W/t/L | p3-mmpolish W/t/L | p3-clmm W/t/L |
|---|---|---|---|---|---|
| P16 unguarded (v1.0) | 31,140 | 42 | success-only trips (50/50 split) | success-only trips (70/30 split) | sparse ACL losses (predicted) |
| P16 merged (guarded) | 31,140 | 19 | 9/22/4 | **18/17/0** | 7/24/4 |
| Z12 (guarded) | 30,221 | 16 | 7/22/6 | 17/17/1 | 6/27/2 |
| C16 (guarded, v1.1.1) | 23,994 | 22 | 6/26/3 | 15/18/2 | —† |

† clmm's C16 per-category tally archives with the batch; its 8 ACL trips
(+0.11..+0.28) *are* the gate boundary, below. The full Z12 per-category table
is Appendix C (Table C1).

Readings, one arm at a time (§4.11):

- **p3-mmpolish is the consistency arm**: 50 wins, 52 ties, 3 losses over 105
  architecture × family verdicts — zero category losses on Pegasus (several
  residual bar trips there have *negative* mean ΔACL: better chains, 1–3
  marginal success flips). Wins are broad and small-to-moderate:
  watts_strogatz −3.2% over Z12's 11,988-graph family, −2.6% over 5,309 C16
  pairs, weak_strong_cluster −4.3% at 83% win rate (Z12).
- **p3-ate is the margin arm**: dense-structured category wins on all three
  fabrics — Z12 hardware_native −14.2%, bipartite −12.3%, complete −9.6%,
  kneser −9.5%, johnson −6.4%, turan −5.6%, spin_glass −3.5%; C16 kneser
  −8.5%, turan −7.2% (n=386), complete −6.9%, spin_glass −4.7% (n=282); P16
  merged 9 category wins including johnson −0.712 mean. On ACL it tripped no
  family bar on Z12 (johnson is a win) and none on P16 except the
  hardware_native oddity below; its Z12 nominal category losses are
  +0.6..+1.7% small-lattice deltas at noise level — the measured
  template-attempt tax (sub-second, Table 10). Ties are literal: below the
  crossover the arm returns its minorminer stage's embedding.
- **p3-clmm's boundaries are documented, not hidden** (Section 5.2): johnson
  (+0.228 mean, 74 graphs — dense-structured sources where seeds mislead the
  search and the raw construction wins) and the architecture-dependent gate
  (8 C16 mid-family trips: the 0.15 threshold, calibrated on P16/Z12, sits
  below Chimera's higher crossover — consistent with the map's per-topology
  p\*). The product arm covers both: ate wins johnson on both fabrics where
  the boundary appears (Z12 −6.4%, P16 −0.712 mean), and no further re-run
  was taken (the one allowance was spent; a v2 architecture-aware gate is
  future work, Section 9).
- **The third boundary is hardware_native**: a different arm trips this
  near-native family on each architecture (ate P16 +0.13 mean / 4.9 pt;
  mmpolish Z12 +5.9% — its single Z12 category loss) — sources that are
  (near-)subgraphs of the target are perturbed by any arm overhead or seed
  change. A native fast path (detect subgraph-embeddability, return length-1
  chains) would retire the oddity for every arm (Section 9).
- **The C16 prediction confirmed in substance**: graceful degradation is what
  happened — 6W/26t/3L with the dense-structured wins intact, and every ate
  success "violation" a 1–2-graph flip in a tiny family inside the correlated
  marginal-instance signature (§4.11). C16 wall discipline under v1.1.1:
  0 rows over 65 s, worst 63 s.

The bar-as-written verdict is FAIL on all three architectures (16–22 residual
trips); the decomposed verdict is that every residual trip is (a) inside the
measured seed-noise null or (b) one of the three boundaries above. Of the four
committed prediction clauses, three confirmed — clmm's sparse regressions and
its need for the gate verbatim, ate's sparse ties + dense-structured wins,
C16's graceful degradation in substance — and the fourth (mmpolish never
regresses) failed on its success half and was caught and repaired by the
pre-registered path (§4.11). Both verdicts are reported; the paper claims the
decomposed one and shows its work.

#### 6.8.4 What the sweep caught: two harness bugs and a bar

The sweep functioned as a test harness for the programme's own machinery, and
the errata it generated are part of the result (§4.12.7–8):

- **The YAML workers bug.** At M5 bring-up, the runner was found to silently
  ignore YAML worker counts (`workers:` never mapped to the internal
  `n_workers`; `trials`/`warmup` had the same mismatch masked by coinciding
  defaults) — every YAML-driven `ember run` in this repository's history had
  been single-worker (the paper-2 23k sweep used the CLI flag, which always
  worked; no §4.1–4.10 result is affected — all script-route or CLI-flag
  runs). Fixed with alias translation plus a unit check at 48aab69b, together
  with lazy worker-side instance materialization replacing an eager loader
  (serial hours, 27 GB parent, per-task target pickling) at 1e754132, A/B
  verified row-identical; both upstreamed to Ember as PR #1 (§4.12.7).
- **The `_find_split` runaway — found *by* the multi-architecture sweep.** The
  exact pair-split check in the repair engine iterated 2^|U| subsets with no
  deadline ticks. Invisible on P16/Z12, where |U| ≤ ~14 (16k subsets) — and on
  every dev/eval cell of Sections 4–6 — but Chimera's degree-6 fabric grows
  long chains with |U| = 25–40, turning "3 s" moves into 2^30–2^40-subset
  stalls (worst observed: 19.5 h on one row). Fixed at v1.1.1 (|U| > 22 →
  unproven skip; shared node/deadline accounting every 4,096 subsets; a
  regression test pins the bound). The contamination audit is disclosed in
  full: 21 successful mmpolish rows on P16/Z12 exceeded 65 s (worst 158 s) and
  are excluded from final tables (immaterial to every reported median); the
  partial C16 batch (29k rows, 21 h) was discarded and re-run entirely under
  v1.1.1; the §4.3/§4.4 exact-repair results are unaffected (per-move
  deadlines, small |U|) (§4.12.8).
- **The bar-calibration lesson** (Section 6.8.2): the ±1 pt success bar is
  finer than single-trial library noise. Kept as-written for this sweep;
  recorded for the next.

The general point is the reason M5 exists: a bug class invisible on two
architectures and on every hand-picked cell surfaced only under full-library,
multi-architecture load. Evaluations that sample a few families on one fabric
do not just under-measure generality — they structurally cannot catch this
class of failure.

### 6.9 The practitioner default, settled (§4.10b, §4.11)

minorminer.layout — p-norm placement, the documented practitioner default —
completes the baseline set at both scales.

On the 14 frozen cells (770 rows appended to the eval CSV at the same seeds
and budget, §4.10b): statistically indistinguishable from stock on every ER
eval cell (medians −0.06..+0.28, win rates 27–40 of 75 each way) — and
**strictly worse at the dense cliff: 0/5 on all four K_n cells**, where stock
is 5/5 (P16 K140) and 4/5 (Z12 K140). The p-norm initial chains actively fight
the extended-bar structure the cliff needs (the §3.10 anti-placement effect,
now measured in the shipped practitioner tool): the documented layout wrapper
*lowers* minorminer's feasibility ceiling on complete graphs at 60 s.
p3-ate beats max(stock, layout) on every above-crossover cell (vs layout
−0.31..−2.89 ACL at 69–75/75) and is exact-tie-grade on the sparse controls
(|median| ≤ 0.07) — every Section 6 margin stands against the practitioner
default, cell by cell (§4.10b).

At library scale (75,030 rows, n ≤ 1000 subsets, cross-batch pairing against
the main batches' minorminer rows at identical derived seeds, §4.11): median
paired ΔACL vs stock is +0.22% (P16), +0.00% (Z12), +0.00% (C16) — with losses
outnumbering wins (P16: 7,701W/10,006L) — and **success is lower on all three
architectures**: 80.7 vs 82.5% (P16), 82.3 vs 82.9% (Z12), 59.4 vs 63.3%
(C16). The home turf survives only as isolated lattice-family wins (honeycomb
−3..−6% on all three topologies, kagome −4.6% Z12, cubic −1.8% P16) against
symmetric harms elsewhere (cubic +3.2% C16, grid +2.2% C16); at the cliff it
is also 1.1× slower (Table 10, §4.13). No conclusion in this paper changes
against layout, and its library-wide success deficit extends the frozen-cell
cliff finding to ecosystem scale (§4.11).

---

## 7 Anatomy of the incumbent

Every claim in Sections 4–6 is relative to minorminer, so the paper owes the
reader an account of what minorminer actually is. This section measures it —
not the 2014 sketch, the shipped program — via pre-registered, one-switch
probes in a fork that is byte-identical to stock at defaults (§4.0.5). Beyond
due diligence, the probes returned two findings that reshape how the rest of
the paper should be read (7.3, 7.4) and one genuine surprise (7.6).

### 7.1 What ships is not what is cited

Source-verified deltas between the CMR description and minorminer 0.2.22
(file:line citations into the vendored source ship with the artifact;
mm-internals reference):

| the 2014 paper says | the shipped program does | where |
|---|---|---|
| chains = union of independent shortest paths | nearest-attach Steiner build; the union constructor is dead code | embedding.hpp:180, 198 |
| qubit weight diam(G)^occupancy | capped exponential table, max_beta effectively infinite → lexicographic overlap pricing | embedding_problem.hpp:254–265; util.hpp:134 |
| random vertex order per restart | re-shuffle every pass, five order strategies | embedding_problem.hpp:366 |
| root = argmin (Boltzmann proposed) | uniform among exact-minimum ties | pathfinder.hpp:372 |
| (no shortening phase described) | shortening = 85–95% of wall-clock: lockstep BFS + exhaustive audition | pathfinder.hpp:388 |
| Dijkstra as the engine | true in legalization (~5–15% of time); the dominant phase is unit-weight BFS | pathfinder.hpp:507 vs :433 |
| restarts as quality re-rolls (common reading) | `tries` are feasibility restarts that stop at first success | pathfinder.hpp:623 |

The methodological point: papers that benchmark "CMR" are benchmarking a
program whose load-bearing mechanisms appear nowhere in [CMR14]. The probes
below attach effect sizes to the deltas.

### 7.2 The exhaustive audition is load-bearing (the P4 kill, §4.7)

minorminer's shortening phase re-auditions every candidate root by
constructing the full Steiner chain and measuring it — the expensive step.
Two fork switches attacked the economics: estimate-only or budgeted auditions
(`short_audit`), and a fingerprint-based negative cache that skips provably
unchanged re-audits (`dirty_skip`). The pre-registered bet (committed
prediction: budgeted audition survives at small budgets, dirty-skip at ≥ 60 s)
was that cheaper auditions buy more sweeps than per-audit accuracy loss costs.

**The bet loses across the board** (§4.7; 1,200 rows, budgets 5–180 s):
estimate-only is +1.8..+4.9% worse at every substantive point; budgeted (j=3)
+1.6..+2.6% worse; dirty-skip produces byte-identical ACL with *no* wall
saving (40.9 vs 40.8 s — the skippable work sits in the failing tail, a
negligible share at these scales). One 4-pair cell technically cleared the
survival clause ((180, 0.3) @ 15 s: −0.72%); the claim was declined as below
any evidential floor, and the recorded protocol lesson is that bars need
minimum-pairs floors (§4.7). Verdict: the audition's cost *is* its accuracy;
the 85–95% slice is not fat to be trimmed. The switches remain in the fork as
anatomy instruments.

### 7.3 minorminer leaves budget on the table (§4.7)

From the same sweep: on mid cells, stock minorminer's median wall is
identical at 60 s and 180 s budgets — 40.8 s on (140, 0.2); 22.3 s on
(180, 0.1) — its internal patience expires and it returns with wall-clock
unspent (§4.7). This is rational under its own stopping rule and exactly
exploitable by a portfolio: the racer's sparse-cell margin (Section 6.5) is,
mechanically, this abandoned time re-invested through a working selection
gate (§4.6). The finding also explains why best-of-K-parallel finishes sparse
cells in 6–8 s (Table 8 discussion): each member quits early.

### 7.4 The cliff is budget-dependent (§4.7)

(180, 0.3) on P16: 0/25 → 4/25 → 14/25 → 23/25 successes at budgets 5 → 15 →
60 → 180 s (§4.7). Stated once more because it bounds this paper's own map:
E0's "density-flat cliff at n=140" is a 60 s statement (Section 4.4), and any
frontier comparison that does not state its budget is not a claim.

### 7.5 Tree and root: the paper's constructor is worse, its root rule is inert (§4.8, §4.8b)

- **Chain construction** (`chain_tree`): reviving the dead union-of-paths
  constructor — the one the 2014 paper describes — costs +1.7..+7.9% ACL;
  dropping the Steiner build's refcount>1 attach filter (textbook
  Takahashi–Matsuyama) is *catastrophic* on dense cells (+15.7% at
  (140, 0.3), 0/25 wins) (§4.8). The filter — an undocumented one-line
  restriction — is load-bearing exactly where chains are long. (At deg-10
  n=100 the paper's union build is a wash, −0.17%: the deltas only matter
  where the regime does.) A 15-seed confirm dissolved the one apparent
  sph-pure win (57% win rate, below the 60% bar) (§4.8b).
- **Boltzmann root choice** (`root_boltzmann`) — proposed in [CMR14], never
  shipped: null-to-worse, as predicted (T=8 clearly worse on most cells; one
  cell-specific −2.27% curiosity at exactly the confirm bar, recorded, no
  claim) (§4.8, §4.8b).

### 7.6 Pricing: a regime split inside minorminer's own cost function (§4.8, §4.8b)

The shipped program prices overlap *lexicographically* — any occupancy level
dominates any path length (max_beta effectively infinite) — where the 2014
paper specifies a finite diam^occ exchange rate. The probe ran both:

- **beta = 2 annihilates feasibility** (0/25 on nearly every cell; 4/25 at
  n=60): lexicographic overlap pricing is load-bearing for viability,
  prediction confirmed with dramatic effect (§4.8).
- **But beta = D̂ — the 2014 paper's own spec — beats the shipped program on
  sparse graphs**, confirmed at 15 seeds: deg-10 ladder, −2.62% (n=100, 63%
  win rate), −3.89% (n=140, 87%), −5.00% (n=180, 83%), with a real and
  growing feasibility cost (success 64/75 at n=180) and slower convergence
  (14–33 s vs 6–16 s at equal 60 s budget, so the ACL read is fair); it fails
  outright on dense (0–1/25 at p ≥ 0.2) (§4.8, §4.8b).

Reading: the program's abandonment of the paper's finite-β pricing bought
dense feasibility and *pays 2.6–5% ACL on sparse* — a measurable regime split
inside the incumbent's own cost function, sitting exactly on the paper's
p\*(n) axis, and a sparse-regime lever where the scaling argument (§3.21) had
located only "the constant". The shipped default remains the right global
choice; a density-gated β inside the search arm is recorded as the candidate
follow-up, deliberately not built under this paper's freeze (§4.8b).

### 7.7 What the anatomy buys the thesis

Assembled: minorminer is a search program whose quality mechanisms
(exhaustive audition, attach filter) are tuned for — and load-bearing in —
the long-chain regime near the cliff; whose pricing trades sparse quality for
dense feasibility; whose stopping rule abandons budget on easy cells; and
whose restarts are feasibility, not quality, devices. Each is a rational
design under a one-regime worldview, and each is precisely the seam the
two-regime map exploits: construction removes the need for the grind above
p\* (Sections 4–5), and budget reclamation plus selection harvest the
leftovers below it (Section 5.4).

---

## 8 Threats to validity and limitations

1. **Everything is at 60 s, and the map is budget-indexed.** The budget is
   the field's conventional working point, and budget parity is enforced
   throughout — but §4.7 measured the cliff *moving* with budget ((180, 0.3):
   0/25 → 4 → 14 → 23/25 successes across 5 → 15 → 60 → 180 s), so every
   p\*(n), headroom, and frontier statement in this paper — including the
   title claims — is a 60 s statement. For the quality crossover itself there
   is an argument for budget-stability in the template's favor (search
   plateaus by patience, §4.2/§4.7, while the construction is constant-time)
   plus the 5–180 s window of §4.7 — an argument and a window, not a
   measurement at other working points. A budget-resolved p\*(n, t) map is
   future work; until then the crossover should be quoted with its budget
   attached.
2. **ACL is a proxy, and the small margins must be scoped by it.** The
   downstream quantity is solution quality on hardware. The programme's
   simulator study found the within-problem (fixed-effects) correlation of
   ACL to ground-state probability to be ρ = −0.11 (p = 3e-8; slope −0.28
   P(GS) per ACL unit) — real, negative, and *weak* within a problem (the
   pooled ρ = −0.63 headline is confounded by problem difficulty). The
   consequence is a two-tier reading of this paper's margins. The regime
   margins (−6..−33% above p\*, plus the feasibility and variance results,
   which need no proxy) plausibly matter downstream. The sub-2% margins —
   mmpolish's −0.5..−1.4%, cuthill's −1.5..−2.5%, ATE's −2.4% at the Z12
   straddle edge, the racer's smallest reads — are statistically robust under
   this protocol (Holm-corrected, sweeps of 72–75/75) but are *not established
   as practically significant*: at ρ = −0.11 within-problem, sub-2% ACL is
   presumptively within the noise of what an annealer feels. They are claimed
   as measured ACL improvements, nothing more. Re-running the map's key cells
   against annealer (or high-fidelity simulator) quality metrics is the
   top-priority follow-up. Relatedly, busclique optimizes *maximum* chain
   length while this paper reports the mean; max-chain results co-move here
   (template wins both) but were not separately pre-registered.
3. **Instance families.** The map is Erdős–Rényi plus K_n. ER is the right
   first family (it is what "structureless fallback" means operationally, and
   the benchmark minorminer wins, [EMB26]) but real workloads are structured;
   the M5 sweep was the direct test (Section 6.8), and its verdict is the
   scoped one: category-level ties-or-wins nearly everywhere, dense-structured
   wins on all three fabrics, three documented boundaries — under CLI pairing,
   raw ACL, and a bar finer than the measured noise floor. The library's
   category means are regime mixtures: the dense-random headline lives in a
   thin slice of its ER graphs, so M5 complements rather than restates the
   map. Dev and eval instances also come from one generator implementation and
   two disjoint seed registries — disjoint seeds, same family.
4. **K_n cells are thin by construction.** Instance-invariance means K140 and
   the frontier success claim now rests on 20 attempts per arm per architecture
   (§4.14): ate/clmm 20/20 at P16 K180 and Z12 K179 where minorminer is 0/20; the
   K140 margins clear Wilcoxon at p<2e-5 with n=20 pooled pairs, and the margins
   themselves are baseline-seed-sensitive — P16 K140 swung −33.5% (dev) →
   −19.5% (eval) because minorminer's cliff-seed spread (std 3.09 ACL) exceeds
   its own median margin to the template (§4.12.3, Table 11). Corroboration
   is therefore triangulated rather than statistical: the map's independent
   K140 headroom (−33.4% P16, §4.1), the 15/15 sweeps at the adjacent
   dense-ER cells (−28.7..−31.8% at (140, 0.7–0.9), §4.1), and the
   deterministic template's fixed value (13.171 at both stages, §4.5/§4.10).
   K140 numbers are quoted with their pooled n=20 statistics wherever they appear. The
   deterministic-template pairing itself yields anti-conservative p-values
   (flagged *det throughout; the ATE column is the load-bearing one) (§4.10).
5. **Chimera.** C16's clique bound (~64) shrinks the template regime;
   ATE's claim there was pre-registered as graceful degradation to
   minorminer, not victory — and that is what M5 measured: 6W/26t/3L with
   dense-structured wins intact (§4.11, Section 6.8.3). A fabric with no
   useful clique construction would reduce ATE to its search arm everywhere;
   the two-regime *map* would still stand (it is a property of source-density
   vs fabric cut capacity), but the product's dense prize is
   fabric-conditional — and clmm's C16 gate boundary shows the *thresholds*
   are fabric-conditional too (Section 6.8.3).
6. **Pairing routes differ across scales.** Headline tables are literal
   (instance, seed) pairs (script route); the M5 breadth sweep pairs
   (instance, trial) with per-algorithm seed salting and no spur column [CLI]
   — labelled on every table, never pooled (rule 1). The two routes have
   never disagreed on a direction in this programme, M5's verdicts are
   CLI-labelled by construction, and the passthrough null (Section 6.8.2) now
   quantifies the CLI route's resolution: sd 1.57 pt on family success rates
   at single-trial granularity.
7. **Known measurement debts**, disclosed rather than hidden: cooperative
   timeout overruns (worst 89 s on failing attraction rows; ~2.2×
   per-5 s-slice overshoot at the cliff, which is why the equal-time
   best-of-K control is "not even achievable" there, §4.1); the cuthill
   control's disconnected-instance wrapper failure (3 instances, fixed at
   §4.12.4 with regression tests, no frozen cell affected); the
   template-vs-search cross-column selector caveat (Section 5.1); the
   §4.12.8 runaway's contamination footprint (21 successful mmpolish rows
   excluded, one partial batch discarded and re-run, Section 6.8.4). The
   formerly outstanding rule-5 debt — idle re-measure for standalone speed
   claims — is retired by Table 10 (§4.13), which reproduced every
   within-batch ratio.

---

## 9 Future work

Every item below is grounded in a measurement already reported and recorded,
with its evidence, in the artifact's improvement ledger (twelve entries;
improvement-notes.md). The roadmap in brief: **stack the two winners** — run
ATE, then spend the leftover wall on the exact polish, composing the margin
arm with the consistency arm in one strictly-dominating pass (both components
are validity- and monotonicity-preserving; ledger #1); **productize the
confirmed β = D̂ sparse pricing** (§4.8b) as a density-gated arm or, zero-risk,
a racer roster slot — at −2.6..−5.0% it is the largest measured unclaimed
margin in the sparse regime (#4, #5); **architecture-aware gates** — re-derive
clmm's 0.15 density gate per target from the E0 map, since C16's crossover
sits higher (#11), and probe *why* Zephyr's degree-20 fabric neutralizes
mid-band seeding while template-friendly structured-dense families (johnson)
prefer the raw construction over seeded search (#6); **a native fast path** —
detect (near-)subgraph-embeddable sources and return length-1 chains before
any machinery runs, retiring the recurring hardware_native oddity and making
every arm ≥ minorminer there by construction (#12); **erase ATE's sub-second
insurance premium** by gating or cheapening the template attempt below
density ≈ 0.08 — every measured template win sits at ≥ 0.12 (#2, #3); **a
feasibility mode** optimizing time-to-first-legal (raised patience, seeding,
no shortening phase) to push the budget-dependent cliff (§4.7) at fixed cost
(#8); **deeper exact repair** via predicted-gain move scheduling toward the
§4.4 ceiling, with x3 moves bounded before built (#9); and **bar calibration
for library-scale sweeps** — state bars against the free passthrough null or
buy ≥ 3 trials on small families (#10). None of these were built after the
tuning freeze; all inherit the constitution.

---

## 10 Reproducibility

The unit of reproducibility is the pre-registered experiment: a numbered
lab-record entry (question, bars, decision tree) committed before launch, a
script at a recorded commit, and a results CSV; results are appended below a
never-edited line. The record also preserves the programme's mistakes in
place — the one pre-launch bar amendment (§4.9), the declined technical win
(§4.7), the predictions that were wrong (§4.7's fixed-wall-clock bet) —
because a record that cannot show its corrections cannot support its claims.

**Table 13 — claim-to-artifact index.**
<!-- shas as recorded in notes.md pre-registration blocks; QUEUE.md launch shas aligned to notes per the §4.12.5 convention note -->

| result | record | script @ sha | data |
|---|---|---|---|
| crossover map, p\*, headroom, cliff, frontier | §4.1 | e0_crossover.py @ caf62119 | e0_crossover.csv (8,559 rows) |
| straddle extension | §4.1b | e0_crossover.py --resume @ f04a4115 | (appended) |
| best-of-K deflator | §4.1 | e0_ceiling.py @ caf62119 | e0_ceiling.csv |
| rank-stability gate + patience curve | §4.2 | p3_rank_stability.py @ bf1a9713 | p3_rank_stability.csv |
| K60 pair-move probe | §4.3 | p5_k60_pairmoves.py @ 2e06a7f6 | p5_k60_pairmoves.csv |
| K60 exact fixpoint | §4.4 | p5_k60_fixpoint.py @ 50479b69 | p5_k60_fixpoint.txt |
| dev-suite kill gates | §4.5 | dev_suite.py @ 94d5e046 | dev_suite.csv |
| racer vs rule-2 baselines (dev) | §4.6 | m3_race.py @ 94d5e046 | m3_race.csv |
| shortener Pareto (P4 kill) + budget findings | §4.7 | p4_pareto.py @ 94d5e046 | p4_pareto.csv |
| anatomy probes | §4.8 | p6_probes.py @ 94d5e046 | p6_probes.csv |
| 15-seed anatomy confirm | §4.8b | p6_probes.py --confirm @ 9bec9817 | p6_probes_confirm.csv |
| assignment honesty gate | §4.9 | p1_kg2.py @ 94d5e046 | p1_kg2.csv |
| frozen eval (headline + racer) | §4.10 | m4_eval.py / m4_analysis.py @ e917c918 (tuning freeze) | m4_eval.csv, m4_race.csv, m4_headline.md |
| layout supplement (frozen cells) | §4.10b | m4_eval.py --stage main --arms minorminer-layout @ 3ea487e4 | m4_eval.csv (770 rows appended) |
| full-library sweep: 3 main + 3 layout batches + P16 guarded re-run | §4.11 (+2 amendments, per-batch result entries) | gen_m5_full.py → m5full_{c16,p16,z12}[_layout,_rerun].yaml @ 51f4ad99 (launch, QUEUE.md); analyzer m5_analyze.py @ e917c918; arms v1.1 (guards) / v1.1.1 (repair bound) | m5_z12_results.md + m5_z12_percategory.txt (in-repo); per-batch DBs + P16/C16 per-category tables archived on the run host (~700 MB, not in git) |
| M5 harness/engine errata + fixes | §4.12.7–8, §4.12.4 | worker-alias fix @ 48aab69b; lazy materialization @ 1e754132; `_find_split` bound @ v1.1.1; cuthill wrapper fix @ dd15edb3 — each with a unit/regression test | contamination audit in §4.12.8 (21 rows excluded; C16 partial discarded) |
| idle speed table | §4.13 | m6_speed.py @ deb88153 | m6_speed.csv, m6_speed_summary.txt |

Figures 1–3 regenerate deterministically from e0_crossover.csv via one script
(fig_crossover.py; figures/README.md documents the conventions). The frozen
seed registries (dev 101–115, eval 901–915; algorithm dev 0–4, eval 10–14),
the six rules, and the frozen 14-cell suite are in protocol.md; the
experiment-host ledger (one batch at a time, worker caps, load logging) is
QUEUE.md. The fork ships as a patch against minorminer 0.2.22 plus a build
script whose self-test enforces byte-identical-at-defaults parity; 210
contract tests cover the minorminer-family arms and every registered p3 arm
(§4.0.5). Environment pins, the cross-machine instance-hash check, and
per-host busclique cache warm-up are recorded in §4.0.3/§4.0.5. All paths
above are repository-relative under docs/paper3/.

---

## 11 Conclusion

Minor embedding's incumbent has been asked, for a decade, to be one algorithm
for what turns out to be two problems. The density-resolved map locates the
boundary — p\*(n) falling from 0.7 to 0.12 as n grows to 160, on two modern
fabrics, with a headroom ridge reaching −33% along a feasibility cliff that is
density-flat at this budget (a 60 s statement throughout, Section 8) — and the
regime above it belongs to construction: a 0.2–1.3 s template (§4.13) that 60
seconds of search cannot match, cannot improve, and (past the cliff) cannot
even reach. The regime below it belongs to search, where the map is equally
clear that only constants are on offer — and the paper harvests them anyway
(selection −3.8..−6.8% under strict fairness, exact repair −0.5..−1.4%,
ordering −1.5..−2.5%, and a paper-vs-program pricing lever worth 2.6–5%; the
sub-2% entries scoped by the ACL proxy, Section 8). ATE packages the boundary
as a product: never worse than minorminer on ACL beyond seed noise anywhere
measured, at a measured sub-second wall premium; −6..−33% above the crossover
(the −33% end from unanimous n=5 K_n cells, map-corroborated); zero seed
variance where it wins; perfect success where the incumbent fails. The
measurement constitution — paired seeds, budget parity, polish parity, restart
controls, pre-registration — is offered as a contribution in its own right;
its deflator result (best-of-K at equal wall-clock is worth approximately
nothing) retires an assumption the field mostly never wrote down. And the
claim is now ecosystem-shaped: ≈595k runs over the complete benchmark library
on three architectures, under bars committed before launch. The first batch
tripped the bar; the pre-registered remedy answered; every residual violation
decomposed into a measured seed-noise null — obtained for free from the
guards' passthrough mode — or a documented regime boundary. The polish arm
closed at 50 wins, 52 ties, 3 losses over 105 architecture × family verdicts;
the adaptive embedder won dense-structured families on all three fabrics with
no family-level ACL regression on P16+Z12 beyond one near-native oddity; the
practitioner default settled at ≈ stock on ACL and worse on success
everywhere; three of the four committed prediction clauses confirmed, and
the one that failed was caught by the bar and repaired by the path written
down before launch (§4.11). The map, the embedder, and the constitution that
measured them are, as of this sweep, ecosystem-tested.

---

## 12 Addendum (v1.2): the composed embedder — Zephyr-validated

*Added 2026-08-03. Scope: everything in this section is validated on Zephyr
Z12 only (pre-registrations §4.15/§4.16); Pegasus/Chimera extension is
deliberately deferred. Nothing in Sections 1–11 changed.*

### 12.1 EMBER: composing the measured winners

The v1.0 evaluation left three composable results on the table: the polish
arm's near-universal small win (Section 6.7), ATE's dense dominance with its
measured 0.3–0.5 s sparse insurance tax (§4.13), and the hardware_native
families' recurring per-arm flags (§4.11). `p3-ember` composes them into one
arm (ledger items 1, 2, 12): a **native fast path** (structural gates →
label-subset identity → an eligibility-gated Glasgow subgraph call; a hit is
all-length-1 chains, ACL exactly 1.0), then **ATE's template stage** gated at
density ≥ 0.08 below K\_max (killing the sparse tax), then **stock minorminer**
on the remaining budget, lower-ACL winner selected (tie → template), then the
**exact-repair polish** on the leftover wall. The Glasgow tier is gated on
source eligibility (≤15k edges and modal-degree concentration ≥ 0.6 — QPU
graphs, grids, cycles, regular graphs pass; sparse ER, a measured pure-miss
~1 s tax, does not), a bar amendment dated before launch (§4.15 am. 1).

Dev gates (§4.15, five frozen Z12 cells + two K\_n cells, 25 pairs each):
ember is **never worse than ATE on any cell** (better on 5/7, to −4.5%) and
beats stock minorminer at **100% win rate on every readable cell** — medians
−7.4% (100,0.2), −16.2% (100,0.3), −7.6% (140,0.12), −18.4% (140,0.2),
−30.6% (K140), −1.3% (160,0.05); K179 5/5 where minorminer is 0/5. The
sparse cells flip from ATE's ties to wins: the time-to-first-valid tax is
**−0.07 s** (bar ≤ +0.2 s), i.e. the insurance premium is gone while the
polish converts the saved budget into ACL. On the 41-graph hardware_native
family (5 trials), ember embeds 109/205 vs minorminer's 98/205 with 7 graphs
at ACL exactly 1.0 (attribution deterministic: 6 Glasgow hits, 1 label
identity; §4.15 T1b).

At library scale (§4.16: the same 30,201-graph Z12 set as Section 6.8,
paired against the archived minorminer rows under the calibrated bars of
§4.12.10 — drops real only above max(2.6 pt, 3 graphs), ACL at ≥10 pairs):
**ember posts +136 net successes, zero family ACL violations, success gains
of +4.5 to +12.2 pt on the dense-structured families it targets (complete
−10.3%, kneser −10.9%, turan −8.2%, spin\_glass −6.2% at 70–78% win rates),
23 families of polish-class small wins, and the hardware_native flag closed
(success 21 vs 20, mean ΔACL −0.171).** One family tripped the letter of the
success bar — honeycomb, net −5 graphs against a 3.9-graph threshold — and
the pre-registered probe resolved it as the null's tail: at three fresh
seeds per flip graph, minorminer and ember tie exactly (13/21 each; the flip
graphs are n≈1900–2300 pigeonhole-edge lattices where cliff-seed variance
dominates; §4.16 probe). Expected tail count across 35 families at the 95th
percentile threshold is ~1.8.

### 12.2 Negative results, measured

The same cycle killed three candidates, each with a cause worth recording.

**The beta product arms.** The finite diameter-scaled pricing of Section 7
transfers to Zephyr as anatomy — −3.5%/−5.6% at n=140/180 on the deg-10
ladder at 73–76% win rates, with *no* feasibility cost on the degree-20
fabric (§4.15 T1c) — but both product paths failed. `p3-mm-beta-fb` (beta at
0.6× budget, stock rescue) died at library scale: the fixed split costs
success on five families (planted\_solution −104 graphs alone) because
instances stock minorminer legalizes in 25–60 s get only a 24 s rescue — the
v1.0 polish arm's 70/30 lesson (Section 6.7) reproduced in a new arm; and
below the density gate the pricing *hurts* structured sparse lattices
(bcc\_lattice +0.167) — the win is ER-specific. The dev ladder, which
legalizes in 4–17 s, could not have caught the first failure; the §4.15
transfer-risk clause anticipated exactly this gap. The measured fix — stock
minorminer first at full budget, beta re-run in the leftover, keep the
better — is ledgered for a future cycle, not shipped. **The beta ramp** (a
new fork switch: max\_beta = D̂ growing ×2 per unembedded pass) holds
feasibility by construction but surrenders the margin as n grows (0/3
confirm cells; retention 71%/17%/negative vs the ≥80% bar): ramping toward
infinite beta abandons finite pricing precisely where it pays. **The
nine-arm racer** ties race8 exactly (+0.00% median): the beta arm
individually wins 13–15 of 25 races when present, but the ninth slot's
budget dilution of the other eight offsets its wins — the roster is
saturated at this budget, consistent with the equal-wall-clock deflator of
Section 3 (§4.15 T1d; race8 remains the shipped configuration).

A methods footnote the sweep produced for free: the `complete` family under
`p3-mm-beta-fb` is provably a stock-minorminer passthrough at a different
derived seed, and its +0.108 mean ΔACL over 44 pairs *measures* the
cross-batch ACL null at cliff K\_n families — the ±0.10 family ACL bar of
Section 6.8 sits below the ACL seed-noise floor there, extending the
passthrough-null trick of §4.12.10 from success rates to ACL.

### 12.3 Provenance

Pre-registrations §4.15/§4.16 (bars committed before launch; two dated
pre-launch amendments); runs: T1 chain + remedies (QUEUE rows 11/13; two
instrumentation incidents — a stale fork binary behind a pipe-masked build
error, and a deploy that clobbered a live result file — were root-fixed,
their blast radii audited, and their re-runs pre-registered; the re-run
reproduced the preserved first-run medians exactly), T2 batch t2\_z12
(60,402 rows), honeycomb probe (QUEUE row 14). Data in-repo:
`dev_suite.csv`, `p6_probes_confirm_beta_z12.csv`, `t1c_arms_z12.csv`,
`t1d_race9.csv`, `t2_verdicts_summary.txt`, `t2_z12_percategory.txt`,
`t2_honeycomb_probe.csv`; analyzers `t1_verdicts.py`, `t2_verdicts.py`;
batch DBs archived (run host + `results/t2_z12/`). Frozen-arm policy held:
`p3-ate`, `p3-mmpolish`, `p3-race8`, `p3-template` byte-identical to v1.0;
the one in-place edit (the clmm architecture gate) is Z12/P16
byte-identity-regression-tested; the spur-prune fast path is corpus-proven
output-identical (1.2–1.3× template speedup).

---

## References

<!-- to be converted to BibTeX; keys as used in text -->

- [CMR14] J. Cai, W. G. Macready, A. Roy. *A practical heuristic for finding
  graph minors.* arXiv:1406.2741 (2014).
- [ZBED20] S. Zbinden, A. Bärtschi, H. Djidjev, S. Eidenbenz. *Embedding
  algorithms for quantum annealers with Chimera and Pegasus connection
  topologies.* ISC High Performance 2020, LNCS 12151.
- [EMB26] Z. Macaskill-Smith, U. Sharma, M. Warner, K. Varga, D. A. B. Hyde.
  *Ember: An Extensible Benchmark Suite for Quantum Annealing Embedding
  Algorithms.* arXiv:2604.25433 (2026).
- [PSSA20] Y. Sugie et al. *Simulated-annealing-based embedding for quantum
  annealers (PSSA line).* arXiv:2012.02372 and predecessors.
- [ATOM23] *ATOM: adaptive topology embedding.* arXiv:2307.01843.
- [CHARME24] *CHARME: RL chain construction for minor embedding.*
  arXiv:2406.07124.
- [RLQMI26] *RL-based minor embedding.* arXiv:2507.16004.
- [SOTA26] *State-of-the-art evaluation of minor-embedding heuristics.*
  arXiv:2504.13376; FGCS (2026).
- [BIP25] *Bipartite template embedding framework.* arXiv:2504.21112.
- [OCT] T. D. Goodrich, B. D. Sullivan, T. S. Humble. *Optimizing adiabatic
  quantum program compilation using a graph-theoretic framework.* Quantum
  Information Processing 17, 118 (2018).
- [BERNAL20] D. Bernal et al. *Integer-programming approaches to minor
  embedding.* CPAIOR 2020.
- [PRA24] *Four-clique network minor embedding.* Phys. Rev. Applied 21,
  034023 (2024).
- [MM] D-Wave Systems. *minorminer 0.2.22* (source; incl. `busclique` and
  `minorminer.layout`). The vendored copy and fork patch ship with the
  artifact.

---

## Appendix A — the frozen suite

14 cells, fixed by a pre-registered rule from the map (two cells straddling
p\* on the n≈100 ladder, the resolved n=140 straddle pair, the densest
feasible K_n anchor, one past-cliff rung, one sparse control per topology;
§4.1 output 5, §4.1b):

- P16: (100, 0.2), (100, 0.3), (140, 0.12), (140, 0.2), K140, K180
  (past-cliff), (160, 0.05) (sparse control)
- Z12: (100, 0.2), (100, 0.3), (140, 0.12), (140, 0.2), K140, K179
  (past-cliff), (160, 0.05) (sparse control)

Dev instances: seeds 101–105 (E0 baselines 101–103); eval instances
901–915; K_n cells instance-invariant. Bars on this suite use `acl_spur`
(rule 3).

## Appendix B — inherited anchors used in the text

- §3.26 (constructive ceiling, P16, 60 s, 3 seeds): template vs stock
  minorminer — K60 6.73 vs 7.83; K100 9.78 vs 13.62; K140 13.17 vs 20.72;
  biK48_96 6.21 vs 6.68; minorminer's full grind improves the template by
  ≤ 0.04 ACL in 3–42 s.
- §3.21 (sparse scaling): stock minorminer ACL/n ≈ 0.057, flat over
  n = 60–220 at fixed average degree 10 (two datasets); the K180 crossbar
  reused on ER(180, deg 10) yields 13.87 vs minorminer's 10.1 — the
  construction is not descriptive of good sparse embeddings, completing the
  two-sidedness of the regime claim.
- §3.16 (dead selection signal): legal-stage ACL vs final ACL, r ≈ −0.01 —
  the negative space that makes the §4.2 gate result informative.
- §3.15/§3.17 (economics): legalization ≈ 5–15% of wall-clock; the
  shortening phase is 85–95% and earns ~30–38% ACL; its cost concentrates in
  the exhaustive audition, peaking exactly when no improvement exists.

## Appendix C — M5 per-category table, Zephyr Z12

**Table C1 — Z12 full-library per-category results (30,221 eligible graphs ×
5 arms, 60 s, arms v1.1; (instance, trial) pairing [CLI]; raw ACL; cells =
median paired ΔACL% vs minorminer on both-succeed pairs (win rate) · success%;
bold = category win: median < −0.5% at ≥ 55% win rate; §4.11;
data/m5_z12_results.md).** Ten mmpolish rows affected by the §4.12.8 runaway
(worst 143 s) are excluded; immaterial to every median shown. The measured
seed-noise floor on family success rates is sd 1.57 pt / max 4.55 pt
(Section 6.8.2). P16 and C16 per-category tables archive with their batches
(Table 13).

| category | n | MM succ% | p3-ate | p3-mmpolish | p3-clmm | p3-template |
|---|---|---|---|---|---|---|
| watts_strogatz | 11988 | 66.5 | +0.0% (47%W) · 67%s | **−3.2% (65%W)** · 67%s | +0.0% (43%W) · 67%s | +25.0% (17%W) · 67%s |
| barabasi_albert | 3416 | 66.3 | +0.0% (45%W) · 67%s | **−1.6% (56%W)** · 66%s | +0.0% (37%W) · 67%s | +12.0% (25%W) · 67%s |
| regular | 3375 | 57.8 | −1.0% (53%W) · 58%s | **−2.9% (64%W)** · 58%s | +0.0% (48%W) · 58%s | +16.0% (29%W) · 59%s |
| random_er | 3024 | 72.1 | +0.0% (43%W) · 74%s | +0.0% (46%W) · 72%s | +0.0% (39%W) · 74%s | +3.6% (28%W) · 74%s |
| planted_solution | 2616 | 91.2 | +0.0% (44%W) · 91%s | −0.2% (50%W) · 91%s | +0.0% (44%W) · 91%s | +33.9% (13%W) · 92%s |
| sbm | 1125 | 76.9 | +0.0% (48%W) · 77%s | **−2.1% (57%W)** · 77%s | +0.0% (41%W) · 77%s | +26.9% (19%W) · 78%s |
| generalized_petersen | 755 | 91.7 | +0.0% (43%W) · 91%s | +0.0% (47%W) · 92%s | +0.0% (45%W) · 92%s | +22.4% (13%W) · 92%s |
| turan | 607 | 83.2 | **−5.6% (60%W)** · 88%s | **−2.4% (57%W)** · 83%s | **−4.5% (59%W)** · 87%s | +0.0% (49%W) · 88%s |
| spin_glass | 598 | 69.2 | **−3.5% (62%W)** · 74%s | **−2.6% (61%W)** · 69%s | +0.0% (49%W) · 74%s | +6.6% (43%W) · 74%s |
| weak_strong_cluster | 444 | 54.5 | +0.0% (50%W) · 56%s | **−4.3% (83%W)** · 55%s | +0.0% (45%W) · 57%s | +15.3% (13%W) · 60%s |
| circulant | 337 | 86.9 | +0.0% (43%W) · 88%s | −0.7% (53%W) · 88%s | +0.0% (46%W) · 87%s | +25.0% (11%W) · 87%s |
| random_planar | 216 | 88.9 | +0.0% (42%W) · 89%s | **−2.1% (58%W)** · 89%s | +1.8% (35%W) · 89%s | +43.0% (2%W) · 89%s |
| bipartite | 208 | 81.2 | **−12.3% (66%W)** · 83%s | +0.0% (38%W) · 80%s | **−12.0% (64%W)** · 82%s | **−12.3% (62%W)** · 85%s |
| triangular_lattice | 182 | 90.1 | +0.0% (42%W) · 90%s | **−2.4% (59%W)** · 90%s | +0.0% (46%W) · 90%s | +28.2% (9%W) · 88%s |
| honeycomb | 151 | 72.8 | +0.7% (40%W) · 74%s | +0.0% (43%W) · 73%s | +0.0% (47%W) · 74%s | +10.1% (20%W) · 72%s |
| grid | 143 | 82.5 | +0.0% (38%W) · 84%s | +0.0% (48%W) · 84%s | +0.0% (46%W) · 83%s | +17.2% (6%W) · 85%s |
| kagome | 130 | 71.5 | +1.1% (45%W) · 74%s | **−1.5% (55%W)** · 72%s | +0.0% (49%W) · 73%s | +17.3% (18%W) · 71%s |
| johnson | 74 | 43.2 | **−6.4% (81%W)** · 43%s | **−4.1% (84%W)** · 43%s | +4.5% (31%W) · 43%s | **−3.6% (62%W)** · 43%s |
| cubic_lattice | 74 | 56.8 | +0.0% (40%W) · 55%s | +0.0% (45%W) · 55%s | +0.4% (34%W) · 55%s | +9.0% (20%W) · 57%s |
| king_graph | 70 | 72.9 | +0.8% (37%W) · 71%s | **−5.2% (65%W)** · 73%s | −1.0% (52%W) · 71%s | +30.0% (10%W) · 73%s |
| frustrated_square | 70 | 74.3 | +0.6% (40%W) · 71%s | **−5.7% (70%W)** · 73%s | +0.2% (45%W) · 70%s | +29.9% (14%W) · 73%s |
| shastry_sutherland | 66 | 100.0 | +1.1% (36%W) · 100%s | **−2.8% (62%W)** · 100%s | +0.0% (45%W) · 100%s | +14.9% (17%W) · 100%s |
| cycle | 63 | 96.8 | +0.0% (22%W) · 95%s | +0.0% (21%W) · 97%s | +0.0% (25%W) · 97%s | +0.1% (10%W) · 94%s |
| star | 63 | 71.4 | +0.0% (38%W) · 73%s | +0.0% (29%W) · 73%s | +0.0% (24%W) · 73%s | +0.0% (40%W) · 95%s |
| path | 63 | 95.2 | +0.0% (0%W) · 95%s | +0.0% (0%W) · 97%s | +0.0% (0%W) · 95%s | +0.2% (0%W) · 95%s |
| wheel | 62 | 93.5 | +0.0% (40%W) · 94%s | +0.0% (45%W) · 92%s | +0.0% (36%W) · 95%s | +35.0% (7%W) · 92%s |
| lfr_benchmark | 61 | 68.9 | −0.1% (50%W) · 69%s | **−5.0% (71%W)** · 69%s | **−2.8% (60%W)** · 69%s | +4.9% (36%W) · 69%s |
| complete | 56 | 78.6 | **−9.6% (66%W)** · 86%s | −0.8% (52%W) · 79%s | **−5.1% (61%W)** · 86%s | **−8.1% (59%W)** · 86%s |
| kneser | 41 | 56.1 | **−9.5% (87%W)** · 66%s | **−1.4% (65%W)** · 61%s | **−2.5% (65%W)** · 66%s | **−8.9% (61%W)** · 66%s |
| hardware_native | 41 | 48.8 | **−14.2% (74%W)** · 51%s | +5.9% (42%W) · 49%s | **−3.0% (63%W)** · 51%s | +34.1% (25%W) · 51%s |
| tree | 26 | 92.3 | +0.0% (21%W) · 92%s | +0.0% (33%W) · 92%s | +0.0% (29%W) · 92%s | +6.5% (21%W) · 92%s |
| bcc_lattice | 22 | 63.6 | +1.7% (38%W) · 59%s | **−2.1% (57%W)** · 64%s | +6.2% (46%W) · 59%s | +20.9% (15%W) · 59%s |
| named_special | 12 | 100.0 | +0.0% (8%W) · 100%s | +0.0% (0%W) · 100%s | +0.0% (8%W) · 100%s | +27.1% (0%W) · 100%s |
| hypercube | 11 | 63.6 | +3.7% (0%W) · 64%s | +0.0% (14%W) · 64%s | +0.0% (14%W) · 64%s | +50.0% (0%W) · 64%s |
| binary_tree | 11 | 81.8 | +0.0% (11%W) · 91%s | +0.0% (11%W) · 82%s | +0.0% (11%W) · 82%s | +6.7% (11%W) · 91%s |

Reading notes (§4.11): p3-mmpolish wins or ties 34/35 categories (sole loss
hardware_native, 41 graphs); p3-ate's ties are literal minorminer-at-another-
seed and its +0.6..+1.7% nominal small-lattice entries are the template-attempt
tax at noise level; p3-clmm's johnson/random_planar entries are its documented
boundaries (ate covers both); p3-template standalone loses everywhere sparse by
design — it ships inside p3-ate. Library category means are regime mixtures:
the dense-random headline lives at the (n ≥ 80, p ≥ 0.2) cells of the
crossover map, a thin slice of the library's ER graphs.
