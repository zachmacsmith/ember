# A062: ready-order lifting fails the fixed advancement gate

The single saved analysis **passed with zero errors**; the mechanism gate **failed**. Keep the unchanged branched-path control. Ready-order lifting recovered planted 34404 seed 1 and wheel 2430 seed 1, but lost planted seed 0 and regressed wheel and grid common-seed means. No tuning or additional call follows this screen.

All credited outputs passed original-label validation. Control/ready/MM succeeded **9/12,10/12,12/12**; none timed out. Planted has no common successful seed, so its two conditional ACL means are not a paired quality comparison. Across eight common successes, ready has 3 gains/2 losses/3 ties, Q 2506→2500 (−6). Wheel regresses +6Q on its sole common seed, grid mean +1Q; honeycomb mean improves −7Q. Hypercube seed 1 remains an inherited native-core failure in both arms, before scheduling.

The new planted seed 0 failure occurs after 39 committed insertions (64/133 vertices), at vertex 106 requiring 103/104, with a valid committed partial R. It exhausts the unchanged 1M local repair allowance within 2,758,769/20M total units; it is not a global deadline or representation-capacity proof. Recovered control failures were likewise blocked lifting states.

Ordering diverged in all 10 lifting calls, first at insertion 0–5. All 924 selection records fully determined their choices; 779 selected a different pending row from legacy reverse order. This demonstrates that order changes affect reach and quality, while this singleton-count priority does not preserve success. Counts remain receipt-checked: unsaved intermediate chains prevent independent physical-key recount. Core Q receipts agree between arms wherever a core was admitted.

On common successes, base Q improves 27 while the changed embeddings yield 21 fewer qubits saved by the unchanged branch stage: final net −6. Cycle base gains 17/3 are entirely absorbed by smaller later branch gains; both final cycles remain optimal Q126. Grid seed 0 gains 1 at base but loses 4 of subsequent shortening, ending +3Q. Honeycomb gains 10/2 at base, plus 0/2 extra branch savings.

All-attempt solver/CPU/process totals are control 102.856/102.761/123.901s, ready 127.037/127.010/148.734s, MM 53.143/53.136/59.252s. Scheduler cost is 22.136s and 31,743,983 counted units across calls; it is inside expansion 27.784→53.308s, not additive. No ready/control ratio exceeds10×. Ready loses to MM in 7 common rows, wins hypercube seed 0 (−460Q), ties both ACL1 cycles, and fails 2 rows MM solves. Ready exceeds MM 10× on 8 solver and 4 process comparisons, including failed attempts. Dense quality gains do not erase these gaps.

Each cell below is **Q / solver seconds**; `F` is FAILURE. Full-precision status/ACL/max-chain/within-chain variance/CPU/solver/process rows are in [all36.csv](../../../results/codex/062-results-review/all36.csv).

| Structure (ID) | Seed | Control | Ready | MM | Final ΔQ | Base ΔQ / branch-saving Δ |
|---|---:|---:|---:|---:|---:|---:|
| planted_solution (34404) | 0 | 158 / 6.168 | F / 5.800 | 136 / 0.291 | — | — |
| planted_solution (34404) | 1 | F / 6.055 | 146 / 6.374 | 135 / 0.389 | — | — |
| wheel (2430) | 0 | 186 / 6.621 | 192 / 11.902 | 167 / 10.221 | +6 | +6 / +0 |
| wheel (2430) | 1 | F / 5.541 | 189 / 10.925 | 161 / 9.209 | — | — |
| grid (1584) | 0 | 163 / 9.747 | 166 / 7.794 | 134 / 0.683 | +3 | -1 / -4 |
| grid (1584) | 1 | 152 / 9.260 | 151 / 9.075 | 131 / 0.471 | -1 | +0 / +1 |
| honeycomb (32367) | 0 | 241 / 11.971 | 231 / 16.516 | 196 / 0.664 | -10 | -10 / +0 |
| honeycomb (32367) | 1 | 237 / 8.219 | 233 / 16.429 | 195 / 0.681 | -4 | -2 / +2 |
| cycle (1829) | 0 | 126 / 2.033 | 126 / 4.081 | 126 / 0.213 | +0 | -17 / -17 |
| cycle (1829) | 1 | 126 / 1.989 | 126 / 3.059 | 126 / 0.188 | +0 | -3 / -3 |
| hypercube (4756) | 0 | 1275 / 16.262 | 1275 / 15.930 | 1735 / 10.857 | +0 | +0 / +0 |
| hypercube (4756) | 1 | F / 18.990 | F / 19.154 | 1275 / 19.276 | — | — |

Successful-seed **mean ACL / sample variance** follows; `n` counts successful seeds, and variance is unavailable for n<2. Exact rational values and per-class time totals/variance are in [class_metrics.csv](../../../results/codex/062-results-review/class_metrics.csv).

| Structure | Control | Ready | MM |
|---|---:|---:|---:|
| planted_solution | 1.187970 / — (n=1) | 1.097744 / — (n=1) | 1.018797 / 0.000028 (n=2) |
| wheel | 1.309859 / — (n=1) | 1.341549 / 0.000223 (n=2) | 1.154930 / 0.000893 (n=2) |
| grid | 1.230469 / 0.003693 (n=2) | 1.238281 / 0.006866 (n=2) | 1.035156 / 0.000275 (n=2) |
| honeycomb | 1.257895 / 0.000222 (n=2) | 1.221053 / 0.000055 (n=2) | 1.028947 / 0.000014 (n=2) |
| cycle | 1.000000 / 0.000000 (n=2) | 1.000000 / 0.000000 (n=2) | 1.000000 / 0.000000 (n=2) |
| hypercube | 4.980469 / — (n=1) | 4.980469 / — (n=1) | 5.878906 / 1.614380 (n=2) |

The fixed gate rejects promotion despite two recoveries and another noncycle gain. This six-record/two-seed exposed sample supplies no all-class or population claim; unknown alternatives and prior failures remain. The result separates an influential construction ordering choice from a successful general heuristic.

Provenance: archive `402a4ca9…`, frozen manifest `deabfff2…`, analyzer `e2fe9960…`; one execution, exit 0 and empty stderr. [Analysis summary](../../../results/codex/062-results-review/analysis001/summary.json), [construction details](../../../results/codex/062-results-review/construction_details.csv), [cost receipts](../../../results/codex/062-results-review/costs.json), and [ordering receipts](../../../results/codex/062-results-review/ordering_summary.json) retain the full accounting.
