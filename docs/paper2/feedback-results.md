# Bidirectional order feedback — results

Implemented on `factored`, 2026-09-15. Full feedback improves the clique and spin-glass cases, but does **not** establish a general advantage over neutral-only or one-way search. The exact packer, reservation model, physical coloring and bookmark selection are unchanged. See the [design and recurrence](three-orders.md#bidirectional-order-feedback-approved-2026-09-15).

## Correctness and protocol

**590 tests pass** across algorithms, registry and backend, including exhaustive donor-merge and packing oracles, frozen-slot/deadline tests, and independent physical validation. Historical fixture builders now use fixed work budgets; their assertions are preserved. The only warning is the existing dwave_networkx deprecation. [Validation record](data/feedback_validation.json).

The existing ten-case Z12 board uses paired initialization/schedule seeds 0, 1 and 2, one worker, a requested **10-second warm wall limit**, and no ask cap. All 210 main-board rows have matching source/target hashes and zero timed compilation events. Another 15 fingerprint and 20 schedule-sensitivity runs bring the completed experiment to **245 timed cases**, excluding warmups and interrupted setup. Native calls to MinorMiner raise; none occurred. Extra independent validation and graph loading are outside measured calls; the native entry point’s own validation remains inside. Any unexpected timed compilation would remain in elapsed time and be flagged.

| Configuration | Search difference | Successes | Median actual seconds |
|---|---|---:|---:|
| [Strict baseline](data/feedback_board_strict.json) | Archived own-strand moves; strict acceptance | 27/30 | 10.004 |
| [Neutral only](data/feedback_board_neutral.json) | Own strands; equal-score acceptance | 27/30 | 10.006 |
| [Whole-order borrowing](data/feedback_board_macro.json) | Borrowing only on whole-set moves | 27/30 | 10.005 |
| [Frozen contact](data/feedback_board_frozen.json) | All spatial donors; initial contact order fixed | 26/30 | 10.005 |
| [One-way borrowing](data/feedback_board_oneway.json) | All spatial donors; contact uses its own strands | 27/30 | 10.006 |
| [Full feedback](data/feedback_board_feedback.json) | All donors on all three orders | 27/30 | 10.006 |
| [Stock MM](data/feedback_board_mm.json) | Stock MinorMiner | 25/30 | 2.856 |

Every full-feedback run uses its deadline. Strict native stops at a fixed point in 10 cases and reaches its deadline in 20. Stock MM exceeds 10.1 seconds in 12 cases, with a maximum of **18.187 seconds**. Equal requested limits therefore do not mean equal actual runtimes.

## Physical embedding quality

Median physical qubits among successful seeds; each ordinary numeric entry represents 3/3 successes. A dash means 0/3. The partially successful entries are marked explicitly. Per-run average and maximum chain lengths, elapsed time and work are retained in each linked artifact and aggregated in the summary data.

| Case | Strict | Neutral | Whole only | Frozen t | One-way | Full | MM |
|---|---:|---:|---:|---:|---:|---:|---:|
| K100 | 928 | 815 | 814 | 781 | 786 | 789 | 1078 |
| K140 | 1627 | 1492 | 1490 | 1445 | 1451 | 1447 | 3187 (1/3) |
| ER100_d10 | 511 | 521 | 513 | 617 | 518 | 523 | 500 |
| turan_n162 | 972 | 972 | 972 | 1781 | 972 | 972 | 1945 |
| spin_glass_n163 | 2004 | 1988 | 1884 | 1935 | 1875 | 1872 | — |
| regular_n316 | 1448 | 1435 | 1395 | 1917 (2/3) | 1393 | 1400 | 1063 |
| ws_n486 | — | — | — | — | — | — | 1542 |
| grid_200 | 347 | 317 | 324 | 516 | 318 | 326 | 210 |
| honeycomb_200 | 379 | 364 | 364 | 538 | 371 | 393 | 228 |
| king_graph_196 | 531 | 542 | 548 | 715 | 574 | 580 | 367 |

Full feedback and strict native succeed on the same 27 cases. On those paired successes, full feedback wins 15, ties four and loses eight on physical qubits: **3.5% lower geometric-mean qubit use**. Against MM, full feedback has five exclusive successes (two K140 seeds and all three spin-glass seeds), while MM alone succeeds on the three WS cases. Among their 22 common successes, full feedback wins seven and loses 15. These results do not establish superiority over MM, especially on sparse graphs.

## What the controls establish

The following ratios compare full feedback with each control on common successful seeds. Below 1 favors full feedback; these small samples are development evidence, not significance or universality claims.

| Control | Paired successes | Full wins / ties / losses | Geometric-mean qubit ratio |
|---|---:|---:|---:|
| Neutral only | 27 | 14 / 3 / 10 | 1.0042 |
| Whole-order borrowing | 27 | 12 / 4 / 11 | 1.0040 |
| Frozen contact | 26 | 21 / 0 / 5 | 0.7919 |
| One-way borrowing | 27 | 11 / 3 / 13 | 1.0029 |

- **Optimizing contact order matters.** Freezing it markedly hurts Turán and sparse cases and loses one regular-graph success. Frozen contact already matches the clique gains, so cliques alone cannot demonstrate learned contact responsibilities.
- **Borrowing within proper subsets helps the dense cases.** Full feedback beats whole-order-only borrowing on all nine K100, K140 and spin-glass seeds. Sparse regressions offset that advantage across the board.
- **Importing spatial strands into contact order has no demonstrated overall benefit here.** Full feedback is essentially tied with one-way search, averaging 0.29% more qubits. The added route is exercised: 181,478 accepted contact proposals are attributed to spatial donors. One-way still optimizes contact order against geometry through its objective; this control does not remove all feedback between geometry and contacts.

## Work, compilation and convergence

The 15 standard fingerprint runs are all valid and MM-free. At their existing work budgets, seed-0 K100 improves from 940 to **785** qubits, grid200 from 465 to **315**, and path60 from 65 to **63**. K8 stays 14, K10 stays 21, and all ten Turán seeds stay 972. These are work-budget comparisons; their final partial-sweep decode can differ from a longer wall-budget trajectory. [Fingerprint artifact](data/feedback_fingerprint_feedback.json).

A fresh-cache warmup records **8.773 seconds of compilation**, or 9.326 seconds including imports and both warmups. The subsequent fingerprint calls contain no compile events.

Across the full-feedback board, 1.881 million group queries evaluate 6.544 million merge DPs and 9.812 billion DP cells. Preparation takes 238.52 seconds, including 193.83 seconds constructing transitions; DP fill/traceback takes 23.40 seconds, and axis packing 2.71 seconds. Out of 300.28 seconds elapsed, transition construction is **64.5%**, fill/traceback **7.8%**, and packing **0.9%**. Preparation and transition times overlap; packing is part of decoding. The measured bottleneck is cost preparation, not max flow.

The K100 fingerprint itself takes 1.689 seconds: 1.404 seconds preparing costs, 0.051 seconds filling/tracing the DP, and 0.014 seconds packing. Shared preparation and rolling value rows preserve the exact subproblem; they do not make total DP memory linear because transition/cut/parent tables remain quadratic.

All six clique board runs end their last completed sweep at their best reservation score. Across all 27 usable cases, however, 13 last completed sweeps remain above their bookmarks; the largest gap is 69 reservations. No exact repeated layout was observed in the main full-feedback board. About 79.1% of its adoptions are neutral. Incomplete decoder tails are excluded from this comparison, and repeated layout hashes would not prove a cycle in the schedule RNG.

The unchanged objective/bookmark mismatch is visible directly: the final K100 fingerprint layout uses **781 physical qubits**, but the saved result uses **785**, both at **822 reservations**. K10 also remains at 21. Neither physical-coloring improvements nor a new bookmark rule belongs to this change.

## Schedule sensitivity

Initialization is fixed at seed 0; schedule seeds 1 and 2 are compared with the main board’s schedule seed 0, using the same 10-second warm limit. Entries below are **physical qubits / maximum chain length**. All three schedules succeed on the same nine cases and fail on WS. The twenty added runs have zero timed compilation and zero MM calls. [Sensitivity artifact](data/feedback_sensitivity_feedback.json).

| Case | Schedule 0 | Schedule 1 | Schedule 2 |
|---|---:|---:|---:|
| K100 | 785 / 9 | 789 / 9 | 781 / 9 |
| K140 | 1445 / 11 | 1450 / 11 | 1457 / 11 |
| ER100_d10 | 523 / 9 | 508 / 8 | 521 / 9 |
| turan_n162 | 972 / 6 | 972 / 6 | 972 / 6 |
| spin_glass_n163 | 1872 / 13 | 1868 / 13 | 1895 / 14 |
| regular_n316 | 1366 / 11 | 1471 / 15 | 1435 / 12 |
| ws_n486 | — | — | — |
| grid_200 | 326 / 3 | 326 / 3 | 353 / 4 |
| honeycomb_200 | 393 / 6 | 371 / 4 | 396 / 5 |
| king_graph_196 | 557 / 9 | 557 / 7 | 528 / 6 |

The largest physical-qubit range is 8.3% above the best schedule on grid200, followed by 7.7% on the regular graph. Maximum chain lengths also vary. Thus success is stable in these runs, while quality remains schedule-sensitive; richer moves have not eliminated that dependence. These are wall-budget comparisons, so completed work and the final interrupted sweep can also differ. No production parameters were tuned during the experiment.

## Reproduction and boundaries

The [harness](data/feedback_board.py) records source, harness, loader, validator and MM source/binary hashes; graph hashes accompany each row, and dependency versions accompany each artifact. The [summary data](data/feedback_summary.json) contains paired aggregates and artifact hashes. The [baseline record](data/feedback_baseline.json) identifies commit `f7a48a65c7d4344d169e976251d4eaa962dfaa6f`, source hash `6a7980d06f5f4345e753657d4277d0bc1f81d6ba32c0fd1991da370d351ce975`. New native controls share source hash `c60f9af48965d3f0d1ae52e39454313d5fedeac0c748f59258e4207a88ddd7b2`.

Run `feedback_board.py --policy all` for the sequential main board, `--policy feedback --suite fingerprint --cold-cache` for fingerprints and compilation, and `--policy feedback --suite sensitivity` for the schedule study. All commands use `.venv/bin/python` from the repository root. Strict replay needs the preserved source snapshot, or a checkout of that recorded commit supplied with `--baseline-src`.

The interrupted setup artifact is excluded. Earlier 60-second results remain separately labeled in [three-orders-results.md](three-orders-results.md). Exactness concerns each fixed-strand merge and conditional pack; global packing/search convergence is not claimed. The core retains intact Zephyr, native output and no implicit MM, with no graph-specific fixes. Neutral search may use its entire budget, and `timeout=0` with no work limit is explicitly unbounded.
