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

## 2. Kill ate's sparse "insurance tax" with a sub-K_max gate  [BUILD, small]

Evidence: on Z12, ate's ties sit at 38–47% win rates and its six +0.6..+1.7% nominal
lattice losses trace to the always-run template attempt (0.5–2 s of the 60 s budget)
below K_max — MM inside ate gets ~58 s vs the baseline's 60. Fix: skip the template
attempt below density ≈ 0.08 (every measured template win is at density ≥ 0.12;
E0's sparse control (160, 0.05) is a template loss). Alternative/complement: item 3.

## 3. Cheapen the template attempt itself  [BUILD]

Evidence: the 0.5–2.1 s template-stage cost is spur_prune-dominated (exact fixpoint
over all chains). An incremental prune (endpoints-first, early-exit when the first
full sweep accepts nothing) or an index-space rewrite should cut this to ≲100 ms,
shrinking the item-2 tax without any gate — keeping dense-random detection at every
density for free.

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

## 5. Racer terminal polish + roster upgrade  [BUILD, small]

Evidence: the racer returns best-ever raw (its §4.6/§4.10 wins are pre-polish);
mmpolish's universal small win applies verbatim to the survivor. Add: one terminal
polish quantum on the winner + the item-4 beta-dhat arm to the roster. Also consider
seeding one roster slot from the previous round's best embedding on repeated calls
(warm-start across instances is unexplored).

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
