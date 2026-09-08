# C007b: atomic growth does not survive the full-constructor screen

Retire both fixed variable-occupancy policies. Atomic and elementary growth each completed **2/8** inputs; fresh MM completed **6/8** within budget. Atomic growth lost the previous C006 grid/planar successes and therefore fails the predeclared rule. Its one-missing-edge grid result does not justify further tuning.

All 24 calls ran on hyde03 at seed 0 with fifteen seconds each. The earlier hyde04 start was refused before any trial; its evidence remains separate. The amended saved-data analyzer ran once, accepted all 223 archive hashes and found no audit errors. Every retained candidate map has nonempty, connected, disjoint chains; timeout maps still miss original edges and are not valid original minors.

Entries below are successful Q, or **T(Q/M)** for timeout occupied volume/missing-edge count. MM's **late Q** maps are original-valid diagnostics without timely-success credit.

| Input | MM | Elementary | Atomic |
|---|---:|---:|---:|
| path 2030 | 141 | 183 | 193 |
| tree 5058 | 121 | 154 | 172 |
| grid 1584 | 134 | T(359/7) | T(303/1) |
| planar 31536 | 281 | T(368/38) | T(345/40) |
| ER 6450 | 1044 | T(368/375) | T(463/367) |
| regular 14334 | late 2481 | T(476/1623) | T(559/1670) |
| complete 1041 | late 2170 | T(484/5115) | T(618/4988) |
| SBM 30736 | 638 | T(350/185) | T(377/207) |

The tiny gate's acceptance improvement was real but insufficient. All **640** scored atomic paths had negative ΔE and were accepted. Of 4,340 completed addition visits, **3,700 (85.3%)** found no free path: 2,171 had no free boundary at the chosen endpoint; 1,529 exhausted BFS from nonempty roots. The latter cannot distinguish a sealed destination from disconnected unused access using these records alone. Five further addition visits were interrupted. Thus rejecting proposed atomic growth was not the observed bottleneck. Elementary growth already accepted 1,877/2,027 positive-energy additions (92.6%): Z12's occupancy weight is 1/26, much smaller than the tiny cycle's 1/4.

Cost also limits both trajectories. Each failed candidate stops at the 14.5-second search/cleanup boundary, retains its final diagnostic map, and uses the reserved final-validation interval. The six failed atomic calls completed 1,962–3,350 visits and recorded roughly 63–67 million combined helper/free-BFS adjacency examinations each. These are work counts, not separately measured BFS times. Atomic growth was faster than elementary growth on path/tree but used more qubits; its solver times, 2.824/2.851 seconds, were 16.3/21.0 times MM's. MM's regular/complete calls returned valid maps after 15.394/17.432 seconds and remain TIMEOUT.

Both arms share exactly the same initial assignments, which controls their comparison without establishing that initialization is good. Recorded action differences and subsequent trajectories combine changed growth reach, geometry, acceptance draws and scheduling; they do not isolate one universal cause. The evidence rejects these constructors, not every disjoint-region representation. No constructor rerun, longer allowance or follow-up implementation followed. One development instance/seed per class supports no family-mean, variance or generalization claim.

The [full table](../../../results/codex/track-c-007-review/analysis001/table.csv), [mechanism summary](../../../results/codex/track-c-007-review/mechanism001/summary.json) and raw references are bound by the [review manifest](../../../results/codex/track-c-007-review/review_manifest.json).
