# 046: cumulative vacancy result screen

All 68 finalized outputs are timely SUCCESS and pass the reused independent original-label/edge validator. Vacancy improves **25/34**, ties nine, and worsens none. Total Q falls **15,016 → 14,927 (89 saved)**. The unweighted mean of the 34 per-input ACLs falls **3.32594 → 3.30557**.

Every treatment’s `before_qubits` exactly equals its paired control’s final Q. Saved per-call Q continuity holds, and 89 certified, independently gated and committed Q-minus-one candidates account for all 89 saved qubits. This is an unchanged-pipeline control comparison; there is no fresh MM arm in 046.

| Cost across 34 calls | Control | Vacancy treatment |
|---|---:|---:|
| Solver wall, total seconds | 187.415 | 194.742 |
| Process wall, total seconds | 210.037 | 217.553 |
| Solver wall, mean seconds | 5.512 | 5.728 |
| Solver wall, maximum seconds | 16.281 | 16.663 |

Fresh same-host paired solver-time ratios have mean **1.03981**, median **1.03697**, and maximum **1.10151**. The added stage costs 7.15982 seconds total: 7.00066 seconds in core queries, 0.15145 seconds in independent pre-adoption validation, and 0.00771 seconds in remaining wrapper work. Maximum stage wall is 0.51612 seconds. Core cost includes failed search and repeated setup/certification; the proposal count does not price those operations.

There are 123 queries: 89 committed queries consume 4.61321 core seconds and 846,114 proposals; 34 nonproposals consume 2.38745 core seconds and 520,587 proposals. In total, 1,366,701 proposals cover 13,247 deletion-seed attempts, including 5,293 seed-cap stops. The stage stops on its shared 50,000-proposal limit for 25 inputs and exhausts seeds for nine. No stage or native deadline, core error, invalid output or rejected certified proposal is recorded. No input reaches the 20-success ceiling; the largest improvement is nine qubits. The committed raw traces contain 139 relocation moves; this screen checks their accounting, not their intermediate physical states.

The table counts each of the 34 structures once. The frozen selection retains 35 family memberships; `ember_32616` carries both listed memberships. These are input descriptors, not family-level findings.

| Input | Membership | Q: control → vacancy | ACL: control → vacancy | Stage ms |
|---|---|---:|---:|---:|
| ember_22972 | watts_strogatz | 1699 → 1697 | 9.7644 → 9.7529 | 256.21 |
| ember_2229 | star | 137 → 137 | 1.0787 → 1.0787 | 6.27 |
| ember_4755 | hypercube | 453 → 452 | 3.5391 → 3.5312 | 128.67 |
| ember_31536 | random_planar | 300 → 296 | 1.9737 → 1.9474 | 220.72 |
| ember_5242 | johnson | 842 → 839 | 7.0167 → 6.9917 | 227.76 |
| ember_34404 | planted_solution | 145 → 144 | 1.0902 → 1.0827 | 83.97 |
| ember_6450 | random_er | 887 → 883 | 6.6692 → 6.6391 | 196.38 |
| ember_33587 | weak_strong_cluster | 427 → 426 | 3.3359 → 3.3281 | 165.48 |
| ember_10662 | barabasi_albert | 443 → 439 | 3.6311 → 3.5984 | 175.63 |
| ember_33402 | bcc_lattice | 152 → 150 | 1.6703 → 1.6484 | 238.86 |
| ember_3499 | circulant | 198 → 194 | 1.4776 → 1.4478 | 516.12 |
| ember_2030 | path | 141 → 141 | 1.0000 → 1.0000 | 0.58 |
| ember_37761 | named_special | 50 → 50 | 1.0870 → 1.0870 | 14.42 |
| ember_32122 | kagome | 166 → 157 | 1.2672 → 1.1985 | 479.83 |
| ember_1584 | grid | 173 → 168 | 1.3516 → 1.3125 | 401.96 |
| ember_3060 | turan | 460 → 460 | 5.1111 → 5.1111 | 127.15 |
| ember_31357 | lfr_benchmark | 189 → 184 | 1.8900 → 1.8400 | 194.10 |
| ember_1041 | complete | 1180 → 1180 | 9.2913 → 9.2913 | 270.78 |
| ember_1829 | cycle | 126 → 126 | 1.0000 → 1.0000 | 0.50 |
| ember_1363 | bipartite | 566 → 566 | 4.4921 → 4.4921 | 138.39 |
| ember_4083 | generalized_petersen | 210 → 203 | 1.6667 → 1.6111 | 233.28 |
| ember_14334 | regular | 1303 → 1301 | 9.3071 → 9.2929 | 256.63 |
| ember_2429 | wheel | 199 → 195 | 1.5669 → 1.5354 | 450.02 |
| ember_5411 | kneser | 415 → 411 | 3.2937 → 3.2619 | 139.17 |
| ember_37603 | hardware_native | 250 → 249 | 1.9531 → 1.9453 | 216.96 |
| ember_32616 | frustrated_square,king_graph | 242 → 240 | 2.0000 → 1.9835 | 216.07 |
| ember_5058 | tree | 134 → 134 | 1.1074 → 1.1074 | 19.02 |
| ember_30736 | sbm | 613 → 610 | 5.1083 → 5.0833 | 176.47 |
| ember_4905 | binary_tree | 138 → 136 | 1.0866 → 1.0709 | 52.05 |
| ember_32367 | honeycomb | 273 → 267 | 1.4368 → 1.4053 | 433.09 |
| ember_33018 | shastry_sutherland | 162 → 158 | 1.3388 → 1.3058 | 389.99 |
| ember_33219 | cubic_lattice | 222 → 217 | 1.7760 → 1.7360 | 277.17 |
| ember_31879 | triangular_lattice | 286 → 282 | 2.2344 → 2.2031 | 149.87 |
| ember_37302 | spin_glass | 1835 → 1835 | 11.4688 → 11.4688 | 306.24 |

The screen passed on its first execution with no errors. Exact per-input status, time, Q/ACL, stage entry Q, proposals and stop reasons are preserved in `results/codex/046-results-review/screen001/pairs.csv`; `rows.json` retains every task and summarized call diagnostics, and `memberships.json` preserves all 35 memberships. Source and task identities are checked with the frozen pilot task checker; original label maps and target/source bytes are checked with the unchanged accepted 042 evaluator helpers.

**Limits.** One seed on reused development inputs provides no across-run ACL variance, fresh-instance evidence, family-wide conclusion or MM-superiority claim. Intermediate chains and absolute commit timestamps are unsaved; this screen checks recorded admission/deadline arithmetic and all complete final outputs without reconstructing those unsaved observations. No exhaustive trace replay, solver call, constructor call, remote action or parameter change was part of this analysis.

Archive: `7784967c35c9e6152aedee6e9c38c41742da7f9194ceeda4ba71277e7d9f4199` (443 hash-verified files, quiescent controller). Runtime manifest: `79bc699bd2da6de320d9b2499bd733420199585086c19afa7afb0ba8ea9e5936`. Frozen screen: `169ace01eccaa3447fa1be5516423b139764643e6912c4417e0f093a0c3f9343`.

```sh
.venv/codex-native/bin/python -I -B results/codex/046-results-review/screen.py \
  --archive results/codex/retrieved/hyde03/046-vacancy-pipeline \
  --archive-digest 7784967c35c9e6152aedee6e9c38c41742da7f9194ceeda4ba71277e7d9f4199 \
  --out results/codex/046-results-review/NEW_SCREEN
```
