# A068 development gaps against MM

2026-09-10 UTC. **Exploratory, seed 0, ideal Z12, paired on hyde06. A061 remains retained.** All four methods have 12/12 independently validated timely successes. This cohort has 12 encodings / 11 structures; the BA relabel has no independent structure vote. It emphasizes persistent deficits and does not replace the [original breadth table](mm_gap_retained_a061.md) or [earlier two-seed cohorts](mm_gap_development_20260910.md).

The full footprint policy changes active supports and removes inactive reservations. The booking ablation uses the same new supports and physical conversion while retaining virtual inactive reservations. Each produces one result; no outputs are combined.

| Input | n | MM ACL | A061 ACL | Footprint ACL | Booking ACL | Footprint ΔQ/A061 | Booking ΔQ/A061 | Footprint solver s / MM s |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Grid | 128 | 1.0391 | 1.3125 | 1.2266 | 1.2188 | -11 | -12 | 7.040 / 0.518 |
| Honeycomb | 190 | 1.0632 | 1.2632 | 1.2474 | 1.2053 | -3 | -11 | 12.812 / 0.450 |
| BA | 100 | 1.9900 | 2.8200 | 3.0600 | 2.7300 | +24 | -9 | 12.831 / 6.655 |
| BA | 96 | 3.3125 | 3.0208 | 2.7917 | 2.9167 | -22 | -10 | 10.038 / 2.346 |
| BA96 relabel | 96 | 2.8542 | 2.7812 | 2.9479 | 2.8542 | +16 | +7 | 8.111 / 4.114 |
| Regular | 96 | 4.1458 | 3.8229 | 3.6875 | 3.6042 | -13 | -21 | 12.035 / 2.837 |
| WS | 96 | 2.0000 | 2.3333 | 2.1146 | 2.0625 | -21 | -26 | 9.459 / 0.683 |
| Singleton control | 96 | 1.9688 | 2.7708 | 2.2500 | 2.6562 | -50 | -11 | 10.511 / 1.643 |
| Branch control | 96 | 1.7812 | 1.8438 | 1.8333 | 1.8438 | -1 | +0 | 5.882 / 1.211 |
| ER | 160 | 10.5250 | 8.0563 | 8.0375 | 7.8812 | -3 | -28 | 15.746 / 29.248 |
| SBM | 160 | 5.2062 | 5.5875 | 5.3125 | 5.4188 | -44 | -27 | 13.896 / 13.305 |
| Wheel | 127 | 1.1339 | 1.6220 | 1.6220 | 1.6220 | +0 | +0 | 4.420 / 5.692 |

ACL here is Q/n for one credited embedding. Across-seed ACL variance is **unmeasured**; within-chain variance is retained separately in the audited rows and passive comparison output. No class-population mean or variance is inferred from these individual development inputs.

The full policy closes 65.6% of the WS gap, 72.1% of SBM160 and 64.9% of the singleton-control gap; grid closes 31.4%. BA100 instead grows its MM excess from 83 to 107 Q. The same BA96 topology changes from a 22 Q improvement over A061 to a 16 Q loss under relabeling. Both the gain and regression remain evidence; neither an aggregate improvement nor one seed proves a general class result.

Booking improves nine encodings against A061, ties two and loses 7 Q on the BA96 relabel. It closes 34.3% of the grid gap, 81.3% of WS and 44.3% of SBM160, while its singleton-control closure is 14.3%. This supports further investigation of the contact-support change more broadly than the claim that inactive booking is always harmful. It does not promote either fixed policy.

All 11 entered layouts per native arm hit 1000 asks; the wheel bypasses native construction. Neither new arm hits its geometry deadline or overruns the downstream reserve. A measured allocation limit remains, but extra asks are not established as a cure. Full solver/CPU/process totals are 122.781/122.749/141.192s; booking 124.734/124.690/144.595s; A061 125.461/125.433/147.701s; MM 68.703/68.695/74.139s. Sparse-instance ratios remain substantially larger than these totals suggest; preserve the per-input clocks. No universal 3× gate is applied.

Plausible shared deficit: contact placement and packing before cleanup affect several sparse and modular structures, while complete native bypass on wheel means this change cannot address that deficit. Different booking trajectories, surrogate quality and fixed-ask search remain competing explanations of the BA/regression split. The current data do not distinguish them sufficiently to select another policy.

Evidence: `results/codex/a068-footprint/audit001/output/` (original independent oracle, firstPASS) and `mechanism001/output/` (firstPASS). Root verified 259 common and 44 passive bindings in `root_analysis_review001.json`. All 48 cold calls and costs are retained; no constructor was rerun.
