# Shared partitions — implementation and speed audit

Implemented and audited on `factored` (2026-09-17). The broader query family is
exact and native validity is preserved. The timed board has the same success
count as the baseline and 3.9% higher paired geometric-mean physical-qubit use;
this is not evidence of universal quality or speed improvement. The
[contract](three-orders.md#shared-partitions-and-either-side-borrowing-2026-09-17)
defines the exact candidate family and unchanged packing boundary.

Baseline: commit `7a4214bc444012f70cd29af982358e5311ed22ae`, factored source
SHA256 `c60f9af48965d3f0d1ae52e39454313d5fedeac0c748f59258e4207a88ddd7b2`.
The snapshot and replay instructions are recorded in
[partition_baseline.json](data/partition_baseline.json).

New factored source SHA256:
`fc4560cc54307c562841b93601141f907bcbc502e504e7ffd6396aaa8df5b0d6`.

## Correctness

**611 tests pass** across algorithms, registry, and backend in 14.24 seconds.
The only warning is the existing dwave-networkx deprecation. The focused query
suite has 48 tests; sweep integration has 20. See the
[validation record](data/partition_validation.json).

The query oracles enumerate all four-vertex source graphs and additional
instances up to seven vertices, comparing the union of both borrowing directions
on every destination. They cover tied slots, disappearing/reappearing bars,
reverse and alias strands, complementary-input identity including provenance,
canonical traceback orientation, incumbent and whole-transfer containment,
shared preparation, integer bounds, and interruptions. Separate tests attain
the maximum 11 general solves and six singleton/complement solves.

Sweep tests cover cross-order blocks, complementary neighborhoods, deterministic
nomination enumeration, fixed memberships with live donors, frozen slots, one
packing boundary, unconditional worse decoded adoption, and valid bookmarks.
No-query paths skip neighborhood preparation. Existing conditional-packing and
native physical-conversion tests remain in the regression suite. `packing.py`,
`native_model.py`, and `placement.py` are byte-identical to the baseline.

## Measurement protocol

The audit compares only the preserved baseline and the new implementation.
Common K100, ER100_d10, and grid_200 microbenchmark snapshots use independent
seed-0 orders, a completed baseline decode, and dormant-coordinate completion.
Each destination and selected-set size 1, 2, n/4, n/2, n−2, n−1, n is measured
20 times without a candidate deadline: 63 queries and 1,260 calls per version.
Inputs are checked once, then queries use `checked=False`, as the search does
after validation. Source and snapshot hashes are checked, and repeated completed outputs
must agree. Stage times include all candidate solves, not just the winner.

The existing ten-case board uses paired seeds 0/1/2 and a 10-second warm wall
request. One worker runs baseline and new sequentially, followed by the existing
15 fingerprints at their recorded work budgets. MinorMiner calls raise in all
native measurements. Graph loading and independent external validation are
outside measured embedding calls; native entry-point validation remains inside.
Fresh-cache warmup and compilation events are recorded separately. A deadline
is checked between kernels, so actual elapsed time may exceed the request.

After ten completed new-board cases, the audit was handed to a detached server
worker so it could continue without an active chat/SSH connection. Completed
rows were preserved; the interrupted, unsaved case was rerun. The resumed
worker records another separate warmup session. No interrupted partial timing
is included in the paired results, and only one benchmark worker runs at a time.

This is a speed and behavior audit. No graph-specific tuning or quality-based
architectural acceptance rule is applied. The larger query family has a provable
fixed-slot containment property; its effect on time-limited decoded embeddings
is measured separately.

## Fixed-snapshot query results

All 63 paired queries completed deterministically across their 20 repetitions,
with matching inputs, zero timed compilation and zero MinorMiner calls. The new
family improves the integer objective on **31 queries**, ties on 32, and worsens
none. Improvements include every singleton, size-two, and quarter-set query,
plus four balanced queries. Near-whole and whole queries tie. This concerns the
full lexicographic objective, including rank span, and does not imply every
improvement reduces physical qubits after decoding.

| Work over all 1,260 calls per version | Baseline | Shared partitions |
|---|---:|---:|
| Actual query seconds | 0.330 | 0.465 |
| Merge solves | 4,860 | 8,640 |
| DP cells | 10,642,980 | 19,424,760 |
| Preparation seconds | 0.254 | 0.361 |
| Transition construction seconds (within preparation) | 0.199 | 0.303 |
| DP fill/traceback seconds | 0.028 | 0.056 |

The new enumeration discards 4,320 duplicate candidate descriptions. Singleton
queries now solve six merges instead of one; balanced queries solve eleven
instead of six. Near-whole singleton-complement queries still solve six. Whole
queries reuse their incumbent score and directly score the other candidates.
The wider family therefore adds real work, while canonical orientation minimizes
the rolling-row width. These short measurements establish actual work and rough
query cost; they are too brief to infer small constant-factor speed differences.
The compiled transition and DP kernels themselves are unchanged.

For each fixed query, take its median elapsed time over twenty repetitions,
then take the median paired new/baseline ratio over the nine graph/destination
queries of that size:

| Selected size | Baseline/new merge solves | Median paired time ratio |
|---|---:|---:|
| 1 | 1 / 6 | 3.50 |
| 2 | 2 / 7 | 2.62 |
| n/4 | 6 / 11 | 1.74 |
| n/2 | 6 / 11 | 1.88 |
| n−2 | 6 / 7 | 1.14 |
| n−1 | 6 / 6 | 1.02 |
| n | Direct scores only | 0.90 |

These sizes describe the original destination-prefix nomination; the new query
canonicalizes it to its smaller side. Per-graph, per-axis, per-size stage times
and cell counts are available in the [summary data](data/partition_summary.json).

Raw records: [baseline](data/partition_micro_baseline.json),
[new](data/partition_micro_new.json), and
[common snapshots](data/partition_snapshots.json).

## Ten-case board

Both versions return valid embeddings on **27/30 runs** and explicit no-fit
failures on all three WS seeds. Every returned embedding passes independent
validation. The following values are medians across the three successful
seeds; a dash denotes zero successes. Average chain lengths are physical
qubits divided by source vertices; full per-run values remain in the artifacts.

| Case | Baseline qubits | New qubits | Baseline/new average chain | Baseline/new maximum chain |
|---|---:|---:|---:|---:|
| K100 | 789 | 792 | 7.89 / 7.92 | 9 / 9 |
| K140 | 1447 | 1450 | 10.34 / 10.36 | 11 / 11 |
| ER100_d10 | 523 | 573 | 5.23 / 5.73 | 8 / 9 |
| turan_n162 | 972 | 972 | 6.00 / 6.00 | 6 / 6 |
| spin_glass_n163 | 1872 | 1880 | 11.48 / 11.53 | 13 / 13 |
| regular_n316 | 1421 | 1629 | 4.50 / 5.16 | 11 / 15 |
| ws_n486 | — | — | — | — |
| grid_200 | 326 | 344 | 1.63 / 1.72 | 3 / 4 |
| honeycomb_200 | 393 | 403 | 1.97 / 2.02 | 5 / 6 |
| king_graph_196 | 580 | 596 | 2.96 / 3.04 | 9 / 8 |

| Aggregate work over 30 calls | Baseline | Shared partitions |
|---|---:|---:|
| Actual elapsed seconds | 300.285 | 300.286 |
| Median actual seconds | 10.005 | 10.006 |
| Queries | 1,876,344 | 860,448 |
| Merge solves | 6,529,373 | 7,470,592 |
| DP cells | 9,791,945,294 | 10,624,279,494 |
| Preparation seconds | 237.902 | 243.281 |
| Transition construction seconds (within preparation) | 193.107 | 212.331 |
| DP fill/traceback seconds | 23.628 | 30.287 |
| Axis packing seconds | 2.695 | 0.779 |

The new queries examine more merge families, so ask counts are not equivalent
work units across versions. The new board evaluates 8.5% more DP cells, while
its different nomination list and larger queries also change when packing
occurs. Lower total packing time is not a faster packer: that implementation
is unchanged. New nomination preparation takes 0.727 seconds total, and pair
deduplication removes 2,843,738 duplicate descriptions. The baseline did not
instrument these counters. Transition construction still dominates elapsed time.

These wall-limited results do not demonstrate an embedding-quality improvement.
Among the 27 common successes, the new version uses fewer physical qubits in
five cases, ties in three, and uses more in nineteen; the paired geometric-mean
qubit ratio is 1.0394 (3.9% higher).
They do not contradict exact containment of the fixed-slot merge family:
memberships, search paths, completed sweeps, and decoded layouts differ. No
graph-specific response or acceptance-rule change was introduced.

Raw board records: [baseline](data/partition_board_baseline.json) and
[new](data/partition_board_new.json).

## Trajectories, fingerprints, and compilation

Every board call reaches its deadline. Baseline/new complete 1,064/288 full
sweeps and perform 1,124/348 decodes including initialization and budget-truncated
tails. This demonstrates a real cadence consequence of the expanded nomination
and query families; the rule remains one decode per changed sweep. It does not
isolate a cause for the quality difference.

The last completed sweep lies above its bookmark in 14/13 of the 27 usable
baseline/new runs. The largest in-chip reservation gap anywhere in their
completed sweep trajectories is 63/99. Worse decoded proposals are adopted
306/86 times; no repeated sweep layout is recorded. New adoptions include
104,029 strict and 481,033 neutral moves. These observations do not certify
convergence or schedule independence, and incomplete sweep/decode tails are
excluded from the completed-sweep comparison.

All **15 new fingerprints are valid and MM-free**, taking 70.247 seconds total
at their existing work budgets. The preceding fingerprint artifact has the
same source hash as the preserved baseline; its qubit counts are shown as
historical work-budget evidence, not newly paired timing measurements.

| Fingerprint | Prior recorded qubits | New qubits | New average/max chain | New elapsed seconds |
|---|---:|---:|---:|---:|
| K8 | 14 | 14 | 1.75 / 2 | 0.115 |
| K10 | 21 | 21 | 2.10 / 3 | 0.127 |
| path60 | 63 | 63 | 1.05 / 2 | 0.355 |
| K100 | 785 | 808 | 8.08 / 9 | 3.679 |
| Turán n162, all ten seeds | 972 | 972 | 6.00 / 6 | 6.171–6.685 |
| grid_200 | 315 | 431 | 2.155 / 6 | 2.217 |

The K100 fingerprint's final current layout uses 807 physical qubits while its
returned bookmark uses 808. Bookmark selection still uses reservations, so this
physical distinction does not change the retained result. Packing, coloring,
and bookmark changes remain outside this implementation.

Fresh-cache compilation is **8.544 seconds** for the baseline board worker and
**8.601/8.612 seconds** for the two new-board sessions before/after detachment.
The new fingerprint worker compiles for **8.611 seconds**, with 0.325 seconds
of imports and an 8.842-second first warmup call containing that compilation.
The subsequent warmup call takes 0.013 seconds. All 75 measured embedding calls
and all 2,520 micro calls have zero compilation events. Per-session imports,
warmups, and compilation records are retained without folding them into warm
timing comparisons.

The [new fingerprint artifact](data/partition_fingerprint_new.json),
[prior fingerprint artifact](data/feedback_fingerprint_feedback.json), and
[validated summary](data/partition_summary.json) retain the supporting records.
The acceptance checks—exact subproblems, deterministic completed queries,
deduplicated work, and valid native output—pass. Global optimality, convergence,
schedule-independent final embeddings, and universal quality gains are not
claimed.

## Reproduction

From the repository root:

```bash
.venv/bin/python docs/paper2/data/partition_bench.py --suite all --policy all --cold-cache
.venv/bin/python docs/paper2/data/partition_summary.py
```

The [harness](data/partition_bench.py) retains hashes for source, input graphs,
snapshots, harness, validator, and dependencies, and writes resumable artifacts.
The baseline can be replayed from its snapshot or extracted from the recorded
commit and supplied with `--baseline-src`. Earlier feedback and longer-run
artifacts are preserved separately.
