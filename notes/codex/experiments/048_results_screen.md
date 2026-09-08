# 048: cyclic vacancy continuation

Cyclic continuation improves **18 of 34 inputs**, ties 16, and regresses none against the preceding bounded vacancy stage. All **68 outputs are timely SUCCESS and independently valid on the original source and target graphs**. Total Q falls **14,927→14,858**, saving 69 additional qubits; mean per-input ACL falls **3.30557→3.29016**. All 34 pairs have identical Q immediately before vacancy refinement.

Fresh same-host solver totals are **194.330→194.629 seconds**; the paired ratio has median **1.00185**, mean 1.00099, and maximum 1.02743. Process totals are 216.947→217.655 seconds. These measurements support retaining cyclic continuation for further development; they do not establish a repeatable speed difference.

| Vacancy-stage quantity | Bounded | Cyclic |
|---|---:|---:|
| Committed Q-minus-one contractions | 89 | 158 |
| Queries | 123 | 192 |
| Relocation proposals | 1,366,701 | 1,301,929 |
| Inspected deletion seeds | 13,247 | 11,545 |
| Per-seed cap stops | 5,293 | 5,023 |
| Stage wall, seconds | 7.13942 | 7.41145 |
| Core wall, seconds | 6.97975 | 7.13354 |
| Adoption-validation wall, seconds | 0.15258 | 0.26734 |
| Whole-stage work / exhausted-seed stops | 25 / 9 | 21 / 13 |

No stage deadline, rejected certificate, or core error is recorded. The largest cyclic count is 19 accepted contractions, below the 20-success ceiling. Its largest stage wall is 0.52647 seconds. Thus the additional reach appears within the unchanged allowance; the cyclic policy does not increase that allowance.

The saved-state checker reverses 235 committed membership moves and checks all **192 complete cyclic schedules**, including cursor continuity, current chain eligibility, newly acquired sites, and inspected prefixes. It finds 493 newly acquired-site occurrences among 63,556 planned seed entries. The 156 schedules that plan a wrap do **not** prove that search reached that wrap. This limited replay does not establish intermediate connectivity or contact validity, and unsaved absolute commit timestamps cannot be reconstructed.

The screen preserves all 34 structures, 35 memberships, statuses, Q/ACL, solver/process times, and stage accounting. One structure has two memberships and is counted once. This is one seed on reused development inputs, with no MM arm; it provides no across-run ACL variance, new-family generalization, or novelty claim.

The table retains every input; negative delta favors cyclic. Complete numerical records are in [pairs.csv](../../../results/codex/048-results-review/screen001/pairs.csv), with [summary](../../../results/codex/048-results-review/screen001/summary.json) and [all rows](../../../results/codex/048-results-review/screen001/rows.json).

| Input | Membership | Bounded Q | Cyclic Q | Delta Q |
|---|---|---:|---:|---:|
| ember_22972 | watts_strogatz | 1697 | 1694 | -3 |
| ember_2229 | star | 137 | 137 | +0 |
| ember_4755 | hypercube | 452 | 452 | +0 |
| ember_31536 | random_planar | 296 | 288 | -8 |
| ember_5242 | johnson | 839 | 837 | -2 |
| ember_34404 | planted_solution | 144 | 144 | +0 |
| ember_6450 | random_er | 883 | 881 | -2 |
| ember_33587 | weak_strong_cluster | 426 | 426 | +0 |
| ember_10662 | barabasi_albert | 439 | 424 | -15 |
| ember_33402 | bcc_lattice | 150 | 150 | +0 |
| ember_3499 | circulant | 194 | 193 | -1 |
| ember_2030 | path | 141 | 141 | +0 |
| ember_37761 | named_special | 50 | 50 | +0 |
| ember_32122 | kagome | 157 | 154 | -3 |
| ember_1584 | grid | 168 | 165 | -3 |
| ember_3060 | turan | 460 | 460 | +0 |
| ember_31357 | lfr_benchmark | 184 | 179 | -5 |
| ember_1041 | complete | 1180 | 1180 | +0 |
| ember_1829 | cycle | 126 | 126 | +0 |
| ember_1363 | bipartite | 566 | 566 | +0 |
| ember_4083 | generalized_petersen | 203 | 199 | -4 |
| ember_14334 | regular | 1301 | 1301 | +0 |
| ember_2429 | wheel | 195 | 193 | -2 |
| ember_5411 | kneser | 411 | 409 | -2 |
| ember_37603 | hardware_native | 249 | 248 | -1 |
| ember_32616 | frustrated_square,king_graph | 240 | 240 | +0 |
| ember_5058 | tree | 134 | 134 | +0 |
| ember_30736 | sbm | 610 | 608 | -2 |
| ember_4905 | binary_tree | 136 | 136 | +0 |
| ember_32367 | honeycomb | 267 | 260 | -7 |
| ember_33018 | shastry_sutherland | 158 | 157 | -1 |
| ember_33219 | cubic_lattice | 217 | 216 | -1 |
| ember_31879 | triangular_lattice | 282 | 275 | -7 |
| ember_37302 | spin_glass | 1835 | 1835 | +0 |

Frozen screen `33b2f858`, schedule checker `94e58228`, runtime source `3b2c862e`, and task manifest `3d80a2bf` are bound in the [review manifest](../../../results/codex/048-results-review/manifest.json). Archive digest is `5ddecb714599370ed91fd386a558711fd2a054209421d75bc7bbfda4a60a0caa`. The screen ran once after root confirmed quiescence; no candidate or converter was called.

Rerun into a new output directory:

```sh
.venv/codex-native/bin/python -I -B results/codex/048-results-review/screen.py --archive results/codex/retrieved/hyde03/048-cyclic-vacancy-pipeline --archive-digest 5ddecb714599370ed91fd386a558711fd2a054209421d75bc7bbfda4a60a0caa --out results/codex/048-results-review/screen002
```
