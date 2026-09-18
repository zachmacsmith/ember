# Live reference moves — implementation and audit

Implementation and the detached audit are complete on `factored` (2026-09-17).
The
[approved contract](three-orders.md#live-reference-moves-and-streamed-costs-approved-2026-09-17)
replaces the group catalogue with live reference nominations and packs after
every changed destination query. The DP rewrite preserves the exact candidate
family and canonical winners while streaming contact and endpoint costs.

## Baseline and validation

The baseline is the uncommitted shared-partition implementation with source
SHA256 `fc4560cc54307c562841b93601141f907bcbc502e504e7ffd6396aaa8df5b0d6`.
Its [record](data/live_baseline.json), [source archive](data/live_baseline.tar.gz),
and [patch](data/live_baseline.patch) preserve a reconstructable snapshot.
Applying that patch to the recorded base commit has been checked to reproduce
the exact source hash. The preceding [partition audit](partition-results.md)
and all its artifacts remain unchanged.

All **635 algorithm, registry and backend tests pass** (12.82 seconds warm;
one existing dependency deprecation warning). The [validation record](data/live_validation.json)
and [test log](data/live_validation.log) retain the command and source hash.
The focused DP tests include 240 randomized frozen-dense comparisons, independent
exhaustive oracles, every transition price at boundary/no-cross/full-cross cases,
linear event-storage bounds, shared summaries, and deadline/traceback checks.
Loop tests cover all fifteen relation/destination combinations per vertex,
live nominations, immediate packing, neutral/worse adoption, and interruptions.

All **75 fixed-work trajectories match exactly** between the loop-only and
complete versions: current/bookmarked orders, coordinates, scores, and shared
non-timing diagnostics. [Equivalence record](data/live_equivalence.json).

The frozen complete source hash is
`2903eb74adb3362309f3ac06d8ca9ddd99c33f37c30f67b2203c19b4be6bef23`.
The isolated loop-only control is
`14e12d52a5ae76c7b48a3c28ee10b03706272bf06ad51404950b522388a1faaf`.
The [freeze record](data/live_freeze.json) links reconstructable archives.
All other factored modules remain byte-identical to baseline, and the decoder
function is unchanged. The packer, conservative physical model, conversion,
and bookmark selection remain outside this change.

## Measurement protocol

The four paired board arms are the preserved baseline, the new loop with frozen
old kernels, the complete implementation, and stock MinorMiner. Use the existing
ten cases and seeds 0/1/2, one worker, and ten warm seconds per request. Actual
elapsed time and compilation are separate. Only the stock arm may invoke MM.
The loop-only control is an isolated source snapshot, not a production mode.

The complete implementation also runs the fifteen existing fingerprints. The
63 retained fixed-snapshot queries run twenty times each on baseline and new
kernels. Fixed-work loop-only/full runs must agree in orders, decoded geometry,
scores, and outputs when deadlines do not interfere.

Improving usable layouts are retained during timed native calls and materialized
and validated afterward. Their timestamps provide early-quality profiles without
performing physical conversion at every search step. MM exposes only its final
returned result through the current benchmark API. Relation-attributed work and
decoded improvements describe coupled trajectories; they are not controlled
causal comparisons of nomination families.

These are the algorithm's improving **reservation** bookmarks. Their physical
qubit counts need not decrease at every update, because coloring may use slack
differently. The audit does not substitute a physical-qubit bookmark policy.

Long tests and audits run as detached server jobs with resumable artifacts and
persistent status/log files. Source hashes are frozen before timed work; old
artifacts are never overwritten. Passing criteria are exact subproblems,
deterministic completed queries, removal of redundant transition representations,
and valid native output. Performance and convergence remain measured outcomes.

## Fixed-query measurements

All **63 queries × 20 repetitions × 2 implementations** completed with zero
timed compilation and exact score, canonical permutation and provenance matches.
Each version performed 8,640 merge solves and 19,424,760 DP cells. The streamed
version counted 5,341,480 event states and 7,400,020 event updates. Query inputs
are the retained immutable K100, ER100 and grid200 snapshots, covering all
destinations and sizes 1, 2, n/4, n/2, n−2, n−1 and n.

| Snapshot / destination | Baseline total ms | Streamed total ms | Baseline / streamed |
|---|---:|---:|---:|
| K100 / x | 48.576 | 54.762 | 0.887 |
| K100 / y | 65.977 | 68.771 | 0.959 |
| K100 / contact | 66.529 | 64.989 | 1.024 |
| ER100 / x | 25.673 | 34.326 | 0.748 |
| ER100 / y | 24.441 | 28.400 | 0.861 |
| ER100 / contact | 34.457 | 29.378 | 1.173 |
| grid200 / x | 53.612 | 56.130 | 0.955 |
| grid200 / y | 52.931 | 57.182 | 0.926 |
| grid200 / contact | 70.388 | 42.904 | 1.641 |

Across all repetitions, elapsed query time was **0.4426 → 0.4368 seconds**;
median per-query speedup was **0.973×**. This is essentially flat overall,
with faster sparse contact queries and slower spatial queries on these inputs.
It does not establish a general runtime gain. Preparation fell from 0.3440 to
0.2221 seconds, while fill rose from 0.0539 to 0.1777 seconds: the new fill includes
price application formerly done during preparation. The parent grid remains
quadratic, and the other scratch storage is linear in vertices plus edges.
This storage reduction is separate from measured elapsed time.

[Baseline queries](data/live_micro_baseline.json) and
[streamed queries](data/live_micro_full.json) retain all repetitions, stage
times, input hashes and work. Fresh-cache compilation for these two sessions
was 8.502 and 8.943 seconds respectively, outside the query timings.

## Ten-second paired board

All **120 runs** completed. Values below are physical qubits for seeds 0, 1, 2;
`fail` means no fitting native bookmark or no MM embedding within the request.
No partial embedding is counted as success.

| Case | Baseline | Live loop / old kernels | Complete implementation | Stock MM |
|---|---|---|---|---|
| K100 | 792, 782, 794 | 773, 780, 777 | 773, 780, 777 | 1078, 1087, 1070 |
| K140 | 1442, 1450, 1467 | 1432, 1437, 1435 | 1432, 1437, 1435 | fail, fail, 3187 |
| ER100 | 586, 522, 573 | 585, 589, 613 | 585, 589, 613 | 500, 507, 485 |
| Turán 162 | 972, 972, 972 | 972, 972, 972 | 972, 972, 972 | 1708, 2197, 1945 |
| Spin glass 163 | 1880, 1871, 1884 | 1891, 1914, 1882 | 1891, 1914, 1881 | fail, fail, fail |
| Regular 316 | 1702, 1629, 1553 | fail, fail, fail | fail, fail, fail | 1063, 1078, 1040 |
| WS 486 | fail, fail, fail | fail, fail, fail | fail, fail, fail | 1571, 1542, 1371 |
| Grid 200 | 347, 331, 344 | 392, 354, 413 | 392, 359, 413 | 208, 231, 210 |
| Honeycomb 200 | 403, 429, 397 | 468, 444, 475 | 468, 444, 475 | 228, 222, 246 |
| King 196 | 622, 563, 596 | 617, 630, 618 | 617, 630, 618 | 370, 367, 298 |

| Measurement | Baseline | Loop / old kernels | Complete | Stock MM |
|---|---:|---:|---:|---:|
| Successes | 27/30 | 24/30 | 24/30 | 25/30 |
| Actual total elapsed seconds | 300.285 | 300.267 | 300.275 | 172.305 |
| Queries | 860,533 | 66,465 | 66,637 | — |
| Merge solves | 7,469,941 | 554,580 | 557,381 | — |
| DP cells | 10,631,474,995 | 3,892,453,704 | 4,009,247,946 | — |
| Decodes | 349 | 60,698 | 60,760 | — |
| Interleaver seconds | 294.208 | 58.028 | 54.750 | — |
| Complete decoder seconds | 1.470 | 239.349 | 241.513 | — |
| Conditional packing seconds (included above) | 0.767 | 106.960 | 108.267 | — |

On the 24 baseline/full common successes, the complete version wins/ties/loses
**9/3/12**, using 21,439 versus 20,991 total physical qubits (**2.13% more**).
The three lost regular-graph successes occur with either kernel implementation.
Loop-only/full agree on 22 of their 24 successful physical-qubit counts, with
one win and one loss. On 19 MM/full common successes, full wins seven dense
cases and loses twelve sparse cases. The common-success qubit totals are
12,884 versus MM's 16,144, but neither that weighted total nor either arm's
success count establishes universal superiority. Native succeeds where MM fails
on all three spin-glass seeds; MM succeeds on the regular and WS cases.

Complete decoding now consumes **80.43%** of full-board elapsed time; conditional
packing kernels account for **36.06%**. Interleaving accounts for **18.23%**.
Packing-problem construction, reservation rebuilding and validity work live in
the remaining decoder time; these timings do not isolate those subcomponents.
The streamed arm constructs 818,470,049 event states and applies 1,367,162,067
event updates. More frequent geometric feedback changes the balance of work
substantially. It does not demonstrate a broad speed or success improvement.

[Baseline](data/live_board_baseline.json), [loop-only](data/live_board_loop.json),
[complete](data/live_board_full.json) and [MM](data/live_board_mm.json) retain
every case, average/max chain lengths, actual elapsed time, compilation,
current/bookmark trajectories and work. All timed calls are compilation-free;
all native calls forbid MM. The common ten-second value is a request, not a
claim that every call runs exactly ten seconds: stock MM often returns early
and can overrun its requested timeout.

Fresh-cache board compilation took 8.473 / 8.539 / 8.831 seconds for baseline /
loop-only / full, outside the timed calls. Stock MM has no Numba compilation.
The raw session records retain import, first-call and warm-call times separately.

## Early geometry and relation attribution

All three full K100 runs reached their final reservation bookmark after **two
or three queries**, at 0.0399 / 0.0394 / 0.0411 seconds. Physical output was
773 / 780 / 777 qubits. The baseline reached its own final bookmarks at
8.967 / 1.054 / 2.258 seconds, with 792 / 782 / 794 qubits. This is direct evidence
that the live loop exposes the clique arrangement quickly on these seeds; it is
not a general convergence result. Current states continued moving afterward,
and equal reservation scores can still produce different physical qubit counts.

| Elapsed threshold | Baseline usable bookmarks | Loop-only | Full |
|---|---:|---:|---:|
| 0.01 s | 0 | 0 | 0 |
| 0.1 s | 22 | 24 | 20 |
| 1 s | 24 | 24 | 24 |
| 10 s | 27 | 24 | 24 |

These counts include adapter/initialization time and are sensitive to crossing
a short elapsed-time threshold. The raw artifacts retain every improving usable
bookmark, not only these four samples. They cannot be compared with an MM
intermediate trajectory, which its current API does not expose.

Full-board attribution:

| Nomination relation | Queries | Interleaver s | Decode s | Immediate decoded improvements | Bookmark improvements |
|---|---:|---:|---:|---:|---:|
| Source N(v) | 13,241 | 6.356 | 50.041 | 3,228 | 299 |
| x window | 13,225 | 14.405 | 49.404 | 2,944 | 304 |
| y window | 13,225 | 15.008 | 50.060 | 3,167 | 333 |
| Contact window | 13,230 | 15.177 | 48.845 | 3,146 | 350 |
| Anchor only | 13,227 | 3.730 | 42.078 | 2,030 | 123 |
| Whole order | 489 | 0.0745 | 0.940 | 94 | 48 |

The balanced windows account for 93.5% of DP cells. Source nominations use
236,474,672 cells, anchor-only queries 24,246,934, and whole transfers none.
All families participate in one coupled trajectory; their attribution counts
do not prove which family is most valuable per unit of work in isolation.

The full arm made 60,730 changed queries: 40,646 strict and 20,084 neutral.
Every case has exactly one initial decode plus one decode per change. It adopted
9,852 worse decoded results, as specified, without invalidating its bookmarks.
It started 163 reference rounds, completed 133, and made 22,059 reference visits.
The recorded round states did not repeat, but that does not prove useful continued
progress or convergence. Nomination itself cost 0.241 seconds across the board.

## Work-budget fingerprints

All **15 fingerprints are valid**, with zero native MM calls or timed compilation.
They retain their historical query budgets and longer timeout requests; they
are separate from the ten-second board. Actual total elapsed time is
**427.249 seconds**. Fresh-cache compilation took 8.910 seconds beforehand.

| Case | Seeds | Queries per run | Physical qubits | Average / maximum chain | Actual seconds |
|---|---|---:|---:|---|---:|
| K8 | 0 | 2,000 | 14 | 1.75 / 2 | 0.508 |
| K10 | 0 | 2,000 | 21 | 2.10 / 3 | 0.830 |
| Path60 | 0 | 3,000 | 63 | 1.05 / 2 | 2.226 |
| K100 | 0 | 10,000 | 773 | 7.73 / 9 | 25.003 |
| Turán162 | 0–9 | 15,000 | 972 each | 6.00 / 6 | 35.455–36.159 each |
| Grid200 | 0 | 8,000 | 338 | 1.69 / 5 | 40.010 |

The K100 bookmark arrived around 40 ms from call start, but the specified
10,000-query run continued for 25 seconds. There is deliberately no quiet-sample
stop. Equal query budgets across old and new loops imply very different amounts
of decoding work. [Raw fingerprints](data/live_fingerprint_full.json).

## Limits and remaining questions

Exact fixed-slot merges and native validity are preserved. The no-queue loop
and immediate squishing are implemented without source-family exceptions.
The event rewrite removes dense price storage, but the microbenchmarks show
roughly flat total query time. Frequent decoding dominates the new wall budget.

The useful dense behavior and the lost sparse successes coexist. These results
do not identify one frozen subproblem as the cause, establish an optimal packing
cadence, or justify per-graph remedies. The questions remain structural: how much
organization survives each immediate decode, how to reduce repeated decoder
work without losing its exact conditional problem, and how much progress large
merges transmit relative to their grid and decoding costs. The current design
does not claim rapid global convergence or schedule-independent final embeddings.

## Durable artifacts

The [validated summary](data/live_summary.json) joins all four board arms,
fingerprints, exact microquery comparisons and fixed-work equivalence. The
[detached supervisor](data/live_audit_supervisor.py),
[completed status](data/live_audit_status.json) and [audit log](data/live_audit.log)
retain the sequential run and successful exit. Artifacts save after completed
cases and refuse resumption with changed source/input provenance. Baseline,
loop-only and full source archives remain linked from their provenance records.
All 135 embedding runs, 2,520 timed query calls and 150 fixed-work calls completed;
native MM calls, invalid returned embeddings and timed compilation were all zero.
