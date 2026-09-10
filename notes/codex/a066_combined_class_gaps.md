# Combined A066 development gaps, with A061 retained

2026-09-10. **A061 remains the retained full-class algorithm.** This table
describes the completed initial and broader A066 comparisons, not a promotion
or a census of every Ember class. A066 fails its broader no-regression criterion
against A065 despite useful local gains. Preserve the
[initial result](experiments/066_constructor_results.md) and
[broader rejection](experiments/066_remaining_transfer_results.md).

There are 26 encodings/24 distinct structures, seed 0. Exclude grid relabel
g0021 and BA relabel g0022 from class means and structural counts; retain both
in the all-call data. All three native methods succeed on all 24 canonical
structures. MM succeeds on 23 and times out on K100. On common successes,
A061 has 4 lower-Q/19 higher-Q results; A065 and A066 each have 5 lower-Q/18
higher-Q results. There are no Q ties with successful MM here. ER100 g0101
remains unmeasured by A066. These are exposed development data, not confirmation
or across-seed estimates.

Mean ACL gives each canonical structure equal weight within its class. The
last column preserves every A066/MM Q excess, so a large dense-input gain
cannot erase a sparse or intermediate-size loss. Sizes identify the displayed
inputs only; they never enter a candidate policy as family rules.

| Class (structures) | Retained A061 mean ACL | A065 mean ACL | A066 mean ACL | MM mean ACL | A066 Q − MM Q by size |
|---|---:|---:|---:|---:|---|
| ER (2) | 5.6594 | 5.5219 | 5.5250 | 6.8125 | 80:+4; 160:−420 |
| BA (3) | 3.1588 | 2.8563 | 2.8563 | 2.9779 | 80:−49; 100:+36; 160:−18 |
| Regular (2) | 4.5656 | 4.2188 | 4.2156 | 4.9250 | 80:−16; 160:−195 |
| WS (3) | 2.4975 | 2.4342 | 2.4246 | 2.0767 | 80:+25; 100:+20; 160:+85 |
| SBM (3) | 3.3700 | 3.1700 | 3.1596 | 3.0846 | 80:+8; 100:+10; 160:+4 |
| Random planar (3) | 1.7008 | 1.6750 | 1.6696 | 1.5833 | 80:+8; 100:+14; 160:+3 |
| Grid (1) | 1.3125 | 1.2656 | 1.2422 | 1.0391 | 128:+26 |
| Honeycomb (1) | 1.2632 | 1.1316 | 1.1158 | 1.0632 | 190:+10 |
| Wheel (1) | 1.6220 | 1.1969 | 1.2047 | 1.1339 | 127:+9 |
| Singleton controls (2) | 3.0250 | 2.9844 | 2.9719 | 2.7094 | 80:+18; 160:+48 |
| Branch controls (2) | 2.0656 | 2.0500 | 2.0469 | 1.8969 | 80:+7; 160:+34 |
| K100 (1) | — | — | — | timeout | no common-success comparison |

All three native K100 calls return Q726/ACL7.26. MM's timeout has unknown
credited Q/ACL; do not impute a quality gap or a successful speed ratio.
The grid relabel remains Q157 versus MM133, and BA relabel Q213 versus MM233;
these are encoding sensitivity observations, not extra structural wins/losses.
The BA and ER mean advantages do not satisfy improvement across their displayed
instances. WS, SBM, planar and both control classes lose on every displayed
size. Thus aggregate gains cannot support an all-class claim.

**Variability and runtime are separate deficits.** Across-seed ACL variance
is unknown. The variance column below is the mean of each embedding's
within-chain length variance, which measures a different quantity. Time ranges
use paired same-host solver-wall ratios on common successes, keeping each
cohort's actual comparator. Ratios are descriptive single-call measurements.

| Class | A061/MM solver-wall ratio | A066/MM solver-wall ratio | Mean within-chain variance, A066 / MM |
|---|---:|---:|---:|
| ER | 0.560–2.484 | 2.234–15.335 | 2.2650 / 7.8509 |
| BA | 0.636–4.499 | 3.276–29.409 | 3.6445 / 3.4446 |
| Regular | 1.655–6.133 | 6.915–37.609 | 2.0265 / 3.2530 |
| WS | 6.076–16.467 | 28.673–93.937 | 1.6601 / 0.8774 |
| SBM | 1.092–11.558 | 5.279–96.611 | 2.4504 / 2.0847 |
| Random planar | 6.407–12.946 | 30.052–104.016 | 0.9121 / 0.5996 |
| Grid | 16.650 | 122.774 | 0.1835 / 0.0375 |
| Honeycomb | 27.037 | 161.525 | 0.1234 / 0.0592 |
| Wheel | 1.405 | 12.017 | 1.2809 / 1.5490 |
| Singleton controls | 4.701–5.882 | 18.250–32.064 | 2.1427 / 1.1440 |
| Branch controls | 4.334–7.957 | 22.798–57.893 | 1.1438 / 0.7233 |

Every attempt remains in the
[113-call CSV](../../results/codex/a066-remaining-transfer/report001/all_calls.csv),
including the initial nine pruning-ablation calls, both relabels and MM's timeout.
The four common methods account for 104 calls. Full all-attempt solver/CPU/process
totals and per-class cost objects are in the
[passive report](../../results/codex/a066-remaining-transfer/report001/summary.json).
No timing exclusion, best-output selection or success-only grand total is used.
The retained algorithm's four wins are the measured reference; A066's extra
BA160 win does not replace A061 without the required broader retention decision.

The most plausible shared quality deficit is inefficient placement and reuse
of physical contacts: WS, the controls, grid/honeycomb, planar and BA100 still
need substantially shorter connected chains. This is a hypothesis, not a cause
established by family labels. A066's pair/ordinary interaction shows that useful
local contacts do not compose monotonically into the best final geometry.
Fixed outside contact domains can also exclude every useful short tree, so
changing attachment choice alone may be insufficient. The proposed
[A067 test](tracks/a_067_contact_coverage_decision.md) changes that choice and
must earn complete quality gains promptly; B/C can investigate broader changes
to construction representation.

The cost deficit has at least two regimes. Many small/local inputs reach their
eventual quality early and spend most remaining time rejecting reconstruction;
larger ER/regular/SBM inputs spend substantial time ranking roots and still
admit improvements near the deadline. This supports measured allocation and
incumbent trajectories, not a universal early cutoff. No universal 3× gate or
speed-only extension follows from the table.

Cross-cohort caution: previous A065 remaining-transfer had Q828 versus MM833 on
SBM160; the new unchanged A065 timed call has Q836 versus the same MM833.
All 15 shared MM Q values are unchanged, while A065 also changes on ER160
(1260→1263) and regular160 (823→824). Preserve both experiments; this comparison
does not establish a changed implementation or quantify run-to-run variance.
Earlier class-win counts and these counts have different scope and observed
timed outcomes and must not be silently interchanged.

The root-reviewed passive report passed once in 0.425899 seconds process wall,
with no candidate imports/calls, new validators, MM-map reads or intermediate
replay. Its source and 12 input files are bound before execution; summary SHA256
`6fe49155a7451bf4790f229cb52674deb166778fa0d69e8ec89fcfaf65da095e`.
Exact graph IDs, family allocation, excluded aliases, every individual gap and
unknown value remain in that report. Historical audited rows SHA256
`75e842fb49e241b6a31abfb03988b6be24a9f9a700f0c604ece4a5ad3451ebf5`
support the narrow cross-cohort comparison only.
