# A065 remaining transfer: broader quality gain, persistent structural and time gaps

2026-09-10. **Exploratory continuation passes; no promotion.** The unchanged compiled policy retains all15 A064 successes and improves Q on five additional structures, across BA, ER, regular, SBM and a diagnostic control. Ten ties and every variance/time regression remain in the complete rows. The [frozen contract](065_remaining_transfer_screen.md) required three improvements across two families. This supports retaining the compiled implementation for mechanism research, not spending another cycle solely accelerating root ranking.

Run `065-compiled-boundary-remaining-transfer` on hyde06 completed once: 60/60 calls finalized, supervisor0, absent tmux and free run lock. Fetch001 verified440 files, digest `460e619c391d103ee02b45d6c21655c5eaf769e2e79a6e775e0d60a7e79bd347`. The original audit passed first attempt (1.628s process), as did the passive mechanism reader (1.422s); root verified273 audit and46 mechanism bindings plus six reader preparation bindings. All15 attempts for each of A065, A064, A061 and MM independently validate. No failure, late result or unknown time is omitted.

## Complete results

Q is total physical sites; ACL=Q/source vertices. One seed per encoding. The BA80 relabel g0022 remains separate from its parent g0002.

| Input | A065 Q / ACL | A064 Q | A061 Q | MM Q / ACL | A065 / MM solver seconds |
|---|---:|---:|---:|---:|---:|
| g0002 barabasi_albert n80 | 208 / 2.600000 | 213 | 216 | 257 / 3.212500 | 59.015 / 1.762 |
| g0003 regular n80 | 263 / 3.287500 | 263 | 268 | 279 / 3.487500 | 59.010 / 1.049 |
| g0004 watts_strogatz n80 | 161 / 2.012500 | 161 | 163 | 136 / 1.700000 | 59.009 / 0.546 |
| g0005 sbm n80 | 142 / 1.775000 | 142 | 153 | 131 / 1.637500 | 59.009 / 0.468 |
| g0007 random_er n160 | 1260 / 7.875000 | 1274 | 1289 | 1684 / 10.525000 | 59.047 / 29.626 |
| g0009 regular n160 | 823 / 5.143750 | 863 | 925 | 1018 / 6.362500 | 59.027 / 5.588 |
| g0010 watts_strogatz n160 | 456 / 2.850000 | 456 | 476 | 368 / 2.300000 | 59.024 / 1.770 |
| g0011 sbm n160 | 828 / 5.175000 | 862 | 894 | 833 / 5.206250 | 59.022 / 8.553 |
| g0012 random_planar n160 | 280 / 1.750000 | 280 | 284 | 276 / 1.725000 | 59.011 / 1.198 |
| g0014 honeycomb n190 | 215 / 1.131579 | 215 | 240 | 202 / 1.063158 | 59.005 / 0.324 |
| g0015 wheel n127 | 152 / 1.196850 | 152 | 206 | 144 / 1.133858 | 59.008 / 4.619 |
| g0018 diagnostic_control n160 | 557 / 3.481250 | 562 | 566 | 505 / 3.156250 | 59.044 / 3.509 |
| g0019 diagnostic_control n80 | 157 / 1.962500 | 157 | 158 | 150 / 1.875000 | 59.006 / 0.512 |
| g0020 diagnostic_control n160 | 342 / 2.137500 | 342 | 345 | 307 / 1.918750 | 59.017 / 1.859 |
| g0022 barabasi_albert n80 | 213 / 2.662500 | 213 | 220 | 233 / 2.912500 | 59.009 / 1.817 |

Within-chain variance (across-seed variance is unknown):

| Input | A065 | A064 | A061 | MM |
|---|---:|---:|---:|---:|
| g0002 | 1.59000000 | 1.57359375 | 1.58500000 | 2.69234375 |
| g0003 | 1.07984375 | 1.07984375 | 0.82750000 | 1.19984375 |
| g0004 | 0.88734375 | 0.88734375 | 0.86109375 | 0.43500000 |
| g0005 | 0.57437500 | 0.57437500 | 0.77984375 | 0.40609375 |
| g0007 | 2.94687500 | 3.17359375 | 2.86558594 | 14.06187500 |
| g0009 | 2.97308594 | 3.11371094 | 3.57089844 | 5.30609375 |
| g0010 | 2.75250000 | 2.75250000 | 2.38687500 | 1.26000000 |
| g0011 | 5.24437500 | 5.48734375 | 5.27984375 | 4.62621094 |
| g0012 | 1.02500000 | 1.02500000 | 1.02437500 | 0.83687500 |
| g0014 | 0.13531856 | 0.13531856 | 0.27811634 | 0.05916898 |
| g0015 | 2.34707669 | 2.34707669 | 2.14061628 | 1.54901110 |
| g0018 | 3.38714844 | 3.38734375 | 3.32359375 | 1.36933594 |
| g0019 | 0.96109375 | 0.96109375 | 0.97437500 | 0.55937500 |
| g0020 | 1.31859375 | 1.31859375 | 1.23183594 | 0.88714844 |
| g0022 | 1.84859375 | 1.84859375 | 1.88750000 | 1.52984375 |

The added within-chain variance regression relative to A064 is BA80 1.57359375→1.59000000; mean ACL still improves. The earlier BA160 and freshSBM100 variance increases remain in the [first screen](065_constructor_results.md). Variance across seeds is unknown. All solver/CPU/process values and maximum chains are preserved in [all rows](../../../results/codex/a065-remaining-transfer/report001/all_rows.json); small timing differences are observations, not speed claims from a single run.

## Measured computation and mechanism decision

All15 A065/A064 stages reach their global deadline; none exhausts a complete fixed epoch. A065 solver wall/CPU/process totals are885.2635/885.2196/906.0879s, A064885.1876/885.1570/904.3496s, A061105.3624/105.3458/124.5817s and MM63.1983/63.1970/68.4265s. A065 takes about59s per call, while MM ranges0.324–29.626s. Its runtime objective remains unresolved, especially on sparse inputs.

A065's added stage uses778.0151s: root ranking84.8604s, reconstruction658.3574s, of which658.0393s is non-improving (84.58% of the stage). A064 spends605.6322s ranking and154.6756s reconstructing within772.6849s. A065 commits266 moves versus182. These nested costs must not be added to solver totals. No claim of identical bases or rejected-query trajectories is made for this second cohort; [the first cohort's separate receipt reversal](065_base_recovery_results.md) established that stronger fact only there.

The fixed policy's expectation of useful extra search transfers, but most sparse gaps survive. Stop ranking-only optimization as the immediate priority. A066 tests exact two-owner domains on the predeclared six first-screen maps, separating direct shortening, neutral relocation before shortening, and necessary joint release. Positive local witnesses must promptly face complete-constructor tests; their existence alone cannot sustain another repair sequence.

## Combined development gaps

The two disjoint screens cover24 encodings/22 structures. A065/A064/A06124/24 versus MM23/24; A065 has eight Q improvements and16 ties over A064,23 improvements and one K100 tie over A061. Against MM it has seven wins and16 losses on common-success encodings. Removing the two relabels leaves six wins and15 losses on21 common-success structures. The K100 MM timeout is a success advantage for this attempt, with no finite common-success ACL comparison.

The table excludes relabel duplicates. Means are descriptive across the displayed sizes, on common successes only; all input regressions above and in the first screen remain decisive. Diagnostic controls are not an Ember class. Within-chain variance is averaged here only as a descriptive property of these saved embeddings, not an estimate of algorithm variability.

| Development family | Inputs | Success A065 / MM | Mean ACL A065 / MM | A065 Q win / tie / loss vs MM | Mean within-chain variance A065 / MM | Mean solver seconds A065 / MM |
|---|---|---:|---:|---:|---:|---:|
| barabasi_albert | g0002, g0008 | 2/2 / 2/2 | 3.1125 / 3.4719 | 2 / 0 / 0 | 3.5997 / 4.2819 | 59.025 / 7.186 |
| complete | g0016 | 1/1 / 0/1 | undefined / undefined | 0 / 0 / 0 | undefined / undefined | 59.185 / 60.597 |
| diagnostic_control | g0017, g0018, g0019, g0020 | 4/4 / 4/4 | 2.5172 / 2.3031 | 0 / 0 / 4 | 1.6167 / 0.9336 | 59.019 / 1.914 |
| grid | g0013 | 1/1 / 1/1 | 1.2656 / 1.0391 | 0 / 0 / 1 | 0.1951 / 0.0375 | 59.011 / 0.490 |
| honeycomb | g0014 | 1/1 / 1/1 | 1.1316 / 1.0632 | 0 / 0 / 1 | 0.1353 / 0.0592 | 59.005 / 0.324 |
| random_er | g0001, g0007 | 2/2 / 2/2 | 5.5125 / 6.8125 | 1 / 0 / 1 | 2.2497 / 7.8509 | 59.030 / 16.730 |
| random_planar | g0006, g0012 | 2/2 / 2/2 | 1.6625 / 1.6000 | 0 / 0 / 2 | 0.8597 / 0.6056 | 59.010 / 0.865 |
| regular | g0003, g0009 | 2/2 / 2/2 | 4.2156 / 4.9250 | 2 / 0 / 0 | 2.0265 / 3.2530 | 59.019 / 3.318 |
| sbm | g0005, g0011, g0202 | 3/3 / 3/3 | 3.1533 / 3.0846 | 1 / 0 / 2 | 2.4495 / 2.0847 | 59.016 / 3.554 |
| watts_strogatz | g0004, g0010, g0201 | 3/3 / 3/3 | 2.4342 / 2.0767 | 0 / 0 / 3 | 1.6287 / 0.8774 | 59.017 / 1.044 |
| wheel | g0015 | 1/1 / 1/1 | 1.1969 / 1.1339 | 0 / 0 / 1 | 2.3471 / 1.5490 | 59.008 / 4.619 |

BA and regular now win at both displayed sizes. ER's attractive mean conceals its80-node loss; SBM160's small win does not erase SBM80/freshSBM100 losses. WS, planar, grid, honeycomb, wheel and all four diagnostic controls remain behind MM. Low-Q sparse embeddings plausibly require coordinated contact relocation or neutral transitions, while dense improvements show additional strict moves remain useful. This is a shared structural hypothesis, not a causal conclusion from family labels. Candidates receive no such labels.

[The retained A061 all-class record](../mm_gap_retained_a061.md) remains authoritative and unchanged, including prior failures and unmeasured Sudoku. A065 is a challenger with partial development coverage; no mixed algorithm, confirmation set, across-seed superiority or paper claim follows. [Combined projection](../../../results/codex/a065-remaining-transfer/combined001/summary.json) binds both input audits; it made no candidate calls.
