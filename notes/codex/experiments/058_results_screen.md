# 058: current Sudoku baseline

Exploration, 2026-09-08. Two unchanged audited Sudoku inputs, two seeds each,
ideal Z12, A053 and stock MM separately on hyde02 with 60 seconds per call.
All eight calls succeed and pass the existing independent original-graph
validator. One saved-data analysis passes without errors. No solver reruns.

| Input | Success A053 / MM | Mean ACL A053 / MM | Sample variance A053 / MM | Mean solver seconds A053 / MM |
|---|---:|---:|---:|---:|
| order 2, 16 vertices | 2/2 / 2/2 | 1.59375 / 1.56250 | 0.001953 / 0 | 10.477 / 0.531 |
| order 3, 81 vertices | 2/2 / 2/2 | 4.71605 / 5.13580 | 0.030483 / 0.019509 | 29.367 / 13.879 |

Order 2 is a 2% mean regression; its seed-zero Q25 tie is not an optimal tie
(an older independently validated Q24 witness exists). Order 3 improves mean
ACL by 8.17%, with both seeds winning. A053 has higher sample variance on both
inputs. Two observations are weak variability evidence, not a class estimate.

Paired solver time ratios are 24.625 and 15.662 on order 2, and 1.581 and
3.700 on order 3. Paired process time ratios are 11.733/7.521 and 1.761/3.785,
respectively. All-attempt solver totals are 79.690 seconds for A053 and 28.819
for MM; process totals are 99.569 and 33.055. CPU totals are 79.588 and 28.798.
No missing times, failures or late outputs occur. These ratios use only this
same-host run; do not pool older Sudoku measurements or other cluster hosts.

This closes the current-policy Sudoku measurement gap, not the algorithm gap.
The larger input's gain cannot hide the smaller input's quality and runtime
regressions. Both sizes are exposed development inputs. Generalization to new
Sudoku structures or seeds is unconfirmed. Retain A053 as a research baseline;
there is no new mechanism to promote in this measurement-only experiment.

One stage and detached start; controller 230205 finished at Unix
1788909965.6155205, lock free, session absent, supervisor exit 0. Retrieval
verifies 144 files with digest
`72e8427d5a2cd8dfc547b51105bc7b1fce8a8a7c7a8204f5943daf9f624025b8`.
Source `d10316a34bdc6f0d32428c28b0e28e572e5849a78f0782d6f4a0d6aae3ae4aec`;
manifest `debe3cb5c4c36cce79d1779656cd8787d727abd09d8537bf308a50e3e3c3dec5`.
Existing factored sources equal056 and all input/task source bytes equal029.
The added audited supplement module accounts for the new source snapshot.

[Protocol](058_current_sudoku_baseline.md),
[all results](../../../results/codex/058-results-review/analysis001/per_input.json),
[all status and time records](../../../results/codex/058-results-review/analysis001/rows.json),
[launch evidence](../../../results/codex/058-launch/),
[analysis and bindings](../../../results/codex/058-results-review/).
