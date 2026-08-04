# Improvement ledger — evidence-grounded next steps (v1.2 candidates)

Started 2026-07-29 after the Z12 full-library results (§4.11). Every entry cites the
measurement that motivates it. Nothing here is built mid-M5 (protocol: no tuning
against the sweep in flight); items marked PAPER are future-work text, items marked
BUILD are concrete post-M5 engineering.

## 1. Stack the two winners: `p3-ate` + leftover exact polish  [BUILD, highest EV]

Evidence: p3-mmpolish wins/ties 34/35 Z12 categories as a strict-improvement wrapper
(−0.5..−6% wherever MM leaves budget, §4.11-Z12); p3-ate owns the dense margins
(−9..−33% dense-random cells, −5..−14% dense-structured). The two are composable by
construction: run ate, then spend the leftover wall on `anytime_polish` of whichever
embedding won. Expected: a single arm carrying BOTH stories, strictly dominating each
parent (polish is validity- and monotonicity-preserving). Cost: ~20 lines + a dev-cell
probe. Risk: none measurable (the polish self-terminates at its fixpoint).

**VERDICT (2026-08-03): LANDED — p3-ember ships.** §4.15 T1a all bars pass (never worse than ate; -1.3..-30.6% vsMM at 100%W). §4.16 library: +136 net successes, 23 small-win families, zero calibrated ACL violations, dense-structured 4/4 with success gains. The stack strictly dominates both parents as predicted.

## 2. Kill ate's sparse "insurance tax" with a sub-K_max gate  [BUILD, small]

Evidence: on Z12, ate's ties sit at 38–47% win rates and its six +0.6..+1.7% nominal
lattice losses trace to the always-run template attempt (0.5–2 s of the 60 s budget)
below K_max — MM inside ate gets ~58 s vs the baseline's 60. Fix: skip the template
attempt below density ≈ 0.08 (every measured template win is at density ≥ 0.12;
E0's sparse control (160, 0.05) is a template loss). Alternative/complement: item 3.

**VERDICT (2026-08-03): LANDED.** §4.15 bar (iii): (160,0.05) median construct_s - MM wall = -0.07 s (was +0.3-0.5 s in ate) — the tax is dead; sparse cells simultaneously turned into wins via the stage-4 polish (-1.3%/-7.4%).

## 3. Cheapen the template attempt itself  [BUILD]

Evidence: the 0.5–2.1 s template-stage cost is spur_prune-dominated (exact fixpoint
over all chains). An incremental prune (endpoints-first, early-exit when the first
full sweep accepts nothing) or an index-space rewrite should cut this to ≲100 ms,
shrinking the item-2 tax without any gate — keeping dense-random detection at every
density for free.

**STATUS (2026-08-03): PARTIAL** — W1b spur_prune clean-chain-skip landed (byte-identical corpus-proven, 1.22-1.32x template speedup; commit ac064754). Full index-space rewrite not attempted.

## 4. Productize the confirmed beta-dhat sparse win  [BUILD, biggest untapped margin]

Evidence: §4.8b (15-seed confirm) — finite diameter-scaled pricing (the 2014 paper's
own spec) beats shipped minorminer by −2.6% (n=100), −3.9% (n=140), −5.0% (n=180) on
sparse deg-10 ER at 63–87% win rates, with a feasibility cost (64/75 at n=180). This
is currently only an anatomy finding; it is the sparse-regime counterpart of the
template story and the largest measured unclaimed margin (§3.21 said only "the
constant" exists on sparse — beta-dhat harvests part of it). Product paths:
(a) a density-gated `p3-mm-beta` arm (beta=dhat below density ~0.1, stock above)
with stock-MM fallback on failure; (b) zero-risk: add a beta-dhat arm to the
p3-race8 roster (the racer's selection machinery absorbs its feasibility risk and
its diversity is exactly what the roster wants). (b) first; costs one roster line.

**VERDICT (2026-08-03): anatomy CONFIRMED, product paths FAILED.** T1c: beta-dhat transfers to Z12 (-3.5%/-5.6% at n=140/180, 73/76%W, NO feasibility cost). But §4.16 kills p3-mm-beta-fb at library scale: the 0.6/0.4 split costs success on 5 families (planted_solution -104 graphs) — the v1.0-mmpolish 70/30 lesson — and beta engaged below the density gate HURTS structured sparse lattices (bcc +0.167; the win is deg-10-ER-specific). beta_ramp: 0/3 cells, margin erodes with n; stays a kwargs-only switch (ramp2h==ramp2 tie confirmed the plumbing). NEXT-DONE (v1.3, §4.17, 2026-08-04): p3-mm-beta-mf built and evaluated. T3: all bars pass (success SET == stock every cell; -3.46%/71%W, -5.63%/80%W — full-budget beta margins recovered from the leftover with higher win rates). T4 library: BAR1 PASS (-28 ~ null vs stock; +333 vs -fb with every -fb kill family healed) — the arm is VALIDATED SAFE and supersedes -fb as the below-gate default. But BAR3 FAIL (1/3 claim families): the library's below-gate mass is not deg-10 ER — margins dilute to ~-0.5..-1.5% at ~52%W (real mean shifts on thousand-pair families, below the claim bar). The sparse-ER win is a dev-scale/anatomy claim only. CLOSED: no further product path for beta pricing on Zephyr; remaining upside is P16 (where beta's feasibility cost made -fb-style designs risky — mf's construction sidesteps it; untested there).

## 5. Racer terminal polish + roster upgrade  [BUILD, small]

Evidence: the racer returns best-ever raw (its §4.6/§4.10 wins are pre-polish);
mmpolish's universal small win applies verbatim to the survivor. Add: one terminal
polish quantum on the winner + the item-4 beta-dhat arm to the roster. Also consider
seeding one roster slot from the previous round's best embedding on repeated calls
(warm-start across instances is unexplored).

**VERDICT (2026-08-03): KILLED.** T1d: race9 +0.00% median both reads, 44/40%W, 48% pair-interference — mm-beta WINS 13-15/25 races individually but the 9th slot's dilution of arms 0-7 offsets it exactly; the roster is saturated at 8 (consistent with e0_ceiling's zero-freebie). Terminal polish: tpol=0.0 s — races consume the full budget, so the polish never engages. race8 remains the shipped racer.

## 6. clmm boundary science: johnson / random_planar / Z12 mid-band  [PAPER first]

Evidence: johnson (density 0.172, seeded): clmm +0.23 ACL while ate's template WINS
−0.63 — seeds mislead the search exactly where the raw construction succeeds;
random_planar +1.8% (small dense-planar graphs above the gate); and the reproducible
Z12-vs-P16 mid-band asymmetry (§4.5/§4.10: clmm's (100,0.2)/(140,0.12) wins are
Pegasus-only). Hypothesis worth one probe: Zephyr's degree-20 fabric legalizes easily
without guidance, so seed anchoring buys little mid-band there, and on
template-friendly structured-dense families the right move is the template itself,
not template-seeded search. Candidate fix if the probe supports it: structure gate —
prefer template over seeding when the source's clique-template restriction score
(cheap, computable from POS) is high.

**VERDICT (2026-08-03): probe FAILED, hypothesis INVERTED — structure gate DEAD.** Pre-registered read (W4): AUC(low restriction score -> johnson-signature positive) = 0.366 vs the 0.8 bar over 883 all-three-succeed Z12 graphs (64 pos / 819 neg). Positives mean score 4.22 vs negatives 3.45; johnson has the HIGHEST mean restriction score (5.94; within-family AUC 0.814 for HIGH->signature) yet reproduces the signature (mean d_ate -0.41, d_clmm +0.47, 15/27 positives), while random_planar positives sit at the LOW end — bimodal across families; even the flipped classifier (0.634) misses the bar. Interpretation: seeds mislead MM precisely where the template restriction is geometrically STRESSED yet the raw template still beats MM. No POS-score gate is buildable; retained as boundary science (data: probe_structure_gate.csv).

## 7. hardware_native mmpolish loss (+5.9%)  [investigate before engineering]

Evidence: the single Z12 category loss (41 graphs, MM success 48.8% → ~20 pairs).
Near-native embeddings have chains ≈ 1–2; suspicion: small-sample seed noise rather
than a polish pathology (polish is monotone per-run — a paired loss can only come
from the different MM-stage seed). Check the P16/C16 batches for replication before
touching anything.

## 8. Feasibility-mode near the cliff  [PAPER + probe]

Evidence: §4.7 — the cliff is budget-dependent ((180, 0.3): 0/25 → 23/25 across
5→180 s) and MM converges early on mid cells (patience expiry) while burning fully at
the cliff; §4.5 — the racer's success-union and clmm's frontier cells. A
time-to-first-legal product mode (raised patience + template/clmm seeding + no
shortening phase) could push the practical frontier at fixed budget; measure
time-to-first-legal as the primary axis.

## 9. Exact-repair scheduling depth  [PAPER]

Evidence: §4.4 — 30 min of x1/x2 buys −2.5% on K60 (deadline-bound, not converged);
§4.3 — improving pairs cluster by combined chain length and region overlap. A
predicted-gain move scheduler (train-free: order by the §4.3 CSV's observable
features) would capture more of the fixpoint inside 60 s; x3 joint moves exist by
extension with rapidly growing regions (diminishing returns expected — bound them
before building).

## 10. Bar calibration for library-scale sweeps  [PAPER/protocol]

Evidence: §4.11 — the ±1 pt / ±0.10 ACL family bars sit below the measured CLI
seed-noise floor (sd 1.57 pt success per family; single-trial, per-arm seeds).
Future full-library bars should be stated against a measured null (the passthrough
trick generalizes: any guarded arm provides MM-at-another-seed replicates for free)
or use ≥3 trials on small families.

## 11. Architecture-aware clmm gate  [BUILD, small]

Evidence: §4.11-C16 — the density-0.15 seeding gate (calibrated on P16/Z12) trips 8
mid-family ACL bars on Chimera because the crossover is architecture-dependent
(E0's p*(n) differs per topology; C16's shrunken K_max=64 and degree-6 fabric push
it higher). Fix: gate on a per-target threshold derived from the E0 map — e.g.
density >= c · (fabric degree / K_max-normalized) or simply a per-family-of-target
constant {C16: 0.35, P16: 0.15, Z12: 0.15} — the busgraph cache already identifies
the target family. Zero effect on P16/Z12 behavior.

**STATUS (2026-08-03): BUILT/LANDED** — clmm v1.2.0 kmax-keyed threshold (kmax < 1.6*sqrt(|V|) -> 0.35, else 0.15; P16/Z12 byte-identity regression-tested). C16 re-measure deferred with the P16/C16 decision.

## 12. Native fast path for hardware-native sources  [BUILD, small]

Evidence: hardware_native trips a different arm on each architecture (§4.11: ate
P16 +0.13 mean ACL / 4.9 pt succ; mmpolish Z12 +5.9%): these sources are (near-)
subgraphs of the target, MM finds near-identity embeddings, and any arm overhead
or per-arm seed perturbation flips marginal cases. Fix: a cheap pre-stage in every
p3 arm — attempt a direct subgraph placement (greedy label-preserving match or
minorminer.subgraph if available; budget ~100 ms); on success return chains of
length 1 (ACL exactly 1.0, unbeatable). Makes all arms strictly >= MM on native
sources and removes the recurring flag.

**VERDICT (2026-08-03): LANDED — flag RETIRED.** T1b: ember 109/205 vs MM 98/205 on hardware_native, 7 graphs at ACL exactly 1.0 (6 glasgow + 1 label-identity, attribution deterministic). §4.16: success 21 vs 20, mean dACL -0.171 — the recurring M5 flag is closed. v1.3 refinements CLOSED (2026-08-03, probe P @ 209d7575): the adaptive/deep glasgow budget is DEAD — 0/7 hits on the flip honeycombs at 5/10/20 s solver budgets (either the scale is beyond the solver or the graphs are not exact subgraphs — MM's 1.2-1.6 ACL showed nearness, not membership); with no deep payoff the node-cap alone cannot clear a bar and p3-ember2 was not built (§4.17 decision tree).
