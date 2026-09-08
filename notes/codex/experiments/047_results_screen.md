# 047: current pipeline versus fresh stock MM

The unchanged bounded-vacancy pipeline succeeds on **34/34** inputs; stock MM 0.2.22 succeeds on **32/34**, with two TIMEOUT results. Among the 32 timely common successes, the candidate has **11 lower-ACL results, 19 higher-ACL results, and two ties**. Mean per-input ACL is **3.34086 for MM versus 2.86342 for the candidate**, a **14.29% reduction** on that common subset. Common-subset total Q is 13,972 versus 11,912 (2,060 fewer qubits). This aggregate improvement is not a win across these inputs or their graph classes.

**Speed remains a major deficit.** On the same 32 timely pairs, candidate/MM solver-time ratios have mean 10.4415, median 10.3318, and maximum 30.2974; **16/32 exceed 10×**. Process-time ratios have mean 6.1811, median 7.6845, maximum 12.8077, and **8/32 exceed 10×**. All ratios use fresh same-host pairs from this run; no historical MM measurements are pooled.

| All 34 attempted calls | MM | Current pipeline |
|---|---:|---:|
| Timely SUCCESS | 32 | 34 |
| TIMEOUT | 2 | 0 |
| Solver wall total, seconds | 311.886 | 194.174 |
| Solver wall median, seconds | 0.732 | 5.067 |
| Process wall total, seconds | 320.087 | 216.765 |
| Process wall median, seconds | 0.967 | 5.704 |

The lower aggregate candidate time coexists with the large typical paired slowdown: several difficult MM calls, including its two timeouts, dominate MM’s total. These all-attempt totals do not replace the paired runtime comparison.

MM’s `ember_1041` complete-graph call returns a valid Q=1,913 embedding after **60.98649 s**, so it remains an uncredited timeout; its diagnostic ACL is 15.06299. MM’s `ember_37302` spin-glass call returns no complete embedding after **67.98301 s**. The candidate succeeds on those inputs at Q=1,180 and Q=1,835. Both inputs are excluded from the common-quality and paired-runtime statistics.

The unchanged vacancy stage records 89 committed Q-minus-one contractions across 123 queries and 1,366,701 relocation proposals. Stage wall totals 7.17925 s: core queries 7.01875 s, independent adoption gates 0.15268 s, remaining wrapper work 0.00782 s. Twenty-five stages stop at the shared work limit and nine exhaust their seed lists; none records a stage deadline or core error. Its Q/count/budget/cost arithmetic passes. This does not isolate the stage’s benefit against MM; the candidate includes the whole inherited pipeline.

Every candidate and timely MM output passes the reused original-label/edge validator. The additional complete late MM output is also independently valid and remains uncredited. All 68 statuses and both missing/late outcomes are retained. The 34 structures have 35 memberships; the shared frustrated-square/king-graph input is counted once.

| Input | Membership | MM status | Q: MM → current | ACL: MM → current | Solver s: MM → current | Ratio |
|---|---|---|---:|---:|---:|---:|
| ember_22972 | watts_strogatz | SUCCESS | 2400 → 1697 | 13.7931 → 9.7529 | 20.159 → 8.648 | 0.4290 |
| ember_2229 | star | SUCCESS | 144 → 137 | 1.1339 → 1.0787 | 6.796 → 4.442 | 0.6536 |
| ember_4755 | hypercube | SUCCESS | 422 → 452 | 3.2969 → 3.5312 | 1.350 → 5.425 | 4.0174 |
| ember_31536 | random_planar | SUCCESS | 281 → 296 | 1.8487 → 1.9474 | 0.569 → 6.377 | 11.2138 |
| ember_5242 | johnson | SUCCESS | 1185 → 839 | 9.8750 → 6.9917 | 8.934 → 6.527 | 0.7306 |
| ember_34404 | planted_solution | SUCCESS | 136 → 144 | 1.0226 → 1.0827 | 0.173 → 3.930 | 22.7573 |
| ember_6450 | random_er | SUCCESS | 1044 → 883 | 7.8496 → 6.6391 | 8.362 → 6.494 | 0.7766 |
| ember_33587 | weak_strong_cluster | SUCCESS | 471 → 426 | 3.6797 → 3.3281 | 3.694 → 6.110 | 1.6538 |
| ember_10662 | barabasi_albert | SUCCESS | 410 → 439 | 3.3607 → 3.5984 | 5.519 → 5.940 | 1.0762 |
| ember_33402 | bcc_lattice | SUCCESS | 115 → 150 | 1.2637 → 1.6484 | 0.280 → 4.437 | 15.8221 |
| ember_3499 | circulant | SUCCESS | 196 → 194 | 1.4627 → 1.4478 | 0.341 → 4.729 | 13.8874 |
| ember_2030 | path | SUCCESS | 141 → 141 | 1.0000 → 1.0000 | 0.143 → 3.405 | 23.7594 |
| ember_37761 | named_special | SUCCESS | 46 → 50 | 1.0000 → 1.0870 | 0.113 → 2.296 | 20.4001 |
| ember_32122 | kagome | SUCCESS | 160 → 157 | 1.2214 → 1.1985 | 0.262 → 4.771 | 18.1815 |
| ember_1584 | grid | SUCCESS | 134 → 168 | 1.0469 → 1.3125 | 0.353 → 4.616 | 13.0750 |
| ember_3060 | turan | SUCCESS | 793 → 460 | 8.8111 → 5.1111 | 33.117 → 5.783 | 0.1746 |
| ember_31357 | lfr_benchmark | SUCCESS | 160 → 184 | 1.6000 → 1.8400 | 0.360 → 4.537 | 12.5968 |
| ember_1041 | complete | TIMEOUT | — → 1180 | — → 9.2913 | 60.986 → 11.881 | — |
| ember_1829 | cycle | SUCCESS | 126 → 126 | 1.0000 → 1.0000 | 0.140 → 3.328 | 23.8492 |
| ember_1363 | bipartite | SUCCESS | 776 → 566 | 6.1587 → 4.4921 | 36.874 → 6.521 | 0.1769 |
| ember_4083 | generalized_petersen | SUCCESS | 165 → 203 | 1.3095 → 1.6111 | 0.253 → 4.698 | 18.5468 |
| ember_14334 | regular | SUCCESS | 2114 → 1301 | 15.1000 → 9.2929 | 42.856 → 7.768 | 0.1813 |
| ember_2429 | wheel | SUCCESS | 147 → 195 | 1.1575 → 1.5354 | 2.680 → 5.849 | 2.1828 |
| ember_5411 | kneser | SUCCESS | 365 → 411 | 2.8968 → 3.2619 | 1.643 → 5.481 | 3.3360 |
| ember_37603 | hardware_native | SUCCESS | 187 → 249 | 1.4609 → 1.9453 | 1.060 → 4.723 | 4.4543 |
| ember_32616 | frustrated_square,king_graph | SUCCESS | 171 → 240 | 1.4132 → 1.9835 | 0.398 → 4.992 | 12.5447 |
| ember_5058 | tree | SUCCESS | 121 → 134 | 1.0000 → 1.1074 | 0.132 → 4.002 | 30.2974 |
| ember_30736 | sbm | SUCCESS | 638 → 610 | 5.3167 → 5.0833 | 4.169 → 5.933 | 1.4231 |
| ember_4905 | binary_tree | SUCCESS | 127 → 136 | 1.0000 → 1.0709 | 0.133 → 3.961 | 29.7635 |
| ember_32367 | honeycomb | SUCCESS | 196 → 267 | 1.0316 → 1.4053 | 0.316 → 5.696 | 18.0433 |
| ember_33018 | shastry_sutherland | SUCCESS | 147 → 158 | 1.2149 → 1.3058 | 0.351 → 4.543 | 12.9292 |
| ember_33219 | cubic_lattice | SUCCESS | 187 → 217 | 1.4960 → 1.7360 | 0.491 → 4.641 | 9.4499 |
| ember_31879 | triangular_lattice | SUCCESS | 267 → 282 | 2.0859 → 2.2031 | 0.895 → 5.142 | 5.7454 |
| ember_37302 | spin_glass | TIMEOUT | — → 1835 | — → 11.4688 | 67.983 → 16.548 | — |

**Remaining gaps.** Nineteen inputs still use more qubits, including substantial deficits on the honeycomb, shared king/frustrated-square, hardware-native and wheel examples. Many low-ACL MM calls finish in fractions of a second while the candidate takes several seconds. The strong dense-input gains make the macro average favorable; they do not remove these deficits. This one-seed reused development panel provides no across-run ACL variance, fresh-instance evidence, or family-wide guarantee. Minor embedding refinement and cyclic scheduling remain mechanisms under investigation, with no novelty claim from this result.

Screen001 passed on its first execution. Exact task identities, all per-input Q/ACL and solver/process times, stage diagnostics, and 35 memberships are in `results/codex/047-results-review/screen001`. The checker reuses the accepted 042 original-label oracle and frozen pilot task checker. No candidate, constructor, remote, historical-MM or exhaustive trace call occurred during analysis. Intermediate chains and absolute commit timestamps are unsaved; those observations are not reconstructed.

Archive: `82d476b4869e31320ad1bdc212012c7f4bc7dae511cc4e71ff94517a589d279d` (444 verified files, complete quiescent controller). Runtime manifest: `aa932046df941e0bf8907f6ea4e42dc0b6afdba31bd9c53b2241d520e1300d19`. Frozen screen: `8050a36ea223ef525fda82dadeeb668f592d533e7c27451668cc2e04edddabc8`.

```sh
.venv/codex-native/bin/python -I -B results/codex/047-results-review/screen.py \
  --archive results/codex/retrieved/hyde03/047-current-pipeline-mm \
  --archive-digest 82d476b4869e31320ad1bdc212012c7f4bc7dae511cc4e71ff94517a589d279d \
  --out results/codex/047-results-review/NEW_SCREEN
```
