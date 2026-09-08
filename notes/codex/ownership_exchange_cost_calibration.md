# Synthetic ownership-exchange cost calibration

2026-09-08. Pre-measurement design. This is a local implementation-cost diagnostic,
not a benchmark or an algorithm comparison. The isolated core remains unchanged
at SHA-256 `015781019833ee5a3f49dcec5a189161104003224b1327b44cedda6e084532bb`.
No Ember corpus, constructor, competitor, native pipeline, remote call or search
policy change is permitted here.

Use exactly all nine larger fixtures from the frozen independent review:
`cycle`, `remote_single`, `remote_batch`, `site64`, `site65`, `owners8`, `owners9`,
`negative_labels`, `transfer`. The first eight original graph/entry/group records
are in `fixtures001/expected.json`; the transfer is the exact five-site fixture
in the reviewed `attempt003/oracles.py`. Frozen `attempt003/fixture_actual.json`
supplies expected return values and work/trajectory diagnostics. Copy those
records and the reviewed source into this diagnostic's prepared bundle, preserving
provenance hashes before any timed candidate call.

Run **20 rounds**, all nine fixtures per round, for 180 calls. The listed order
rotates left by `round_index mod 9`; rounds and fixture indices start at zero.
Use one fresh isolated `.venv/codex-native/bin/python -I -B` process with the
module imported once. There is no warm-up call outside those 180 observations.
Each call receives freshly reconstructed ordinary containers and a fresh live
allowance of **1,000,000 units**, paired with an absolute deadline **1.0 second**
after the immediately preceding wall-clock sample. Entry setup, unsuccessful
search, output materialization and certification are inside the measured call.
Module import, argument reconstruction, external validity/identity checks and
JSON writing are separate measured costs. First observations are reported
separately; subsequent calls are interpreter-warm but never reuse algorithm state.
No per-call cold-process or end-to-end embedding claim is intended.

Record external full-query wall and process CPU nanoseconds, internal exclusive
stage times, all charged work, the full candidate/diagnostics and their exact
agreement with the frozen non-time result. Compare input values before/after.
Keep expected non-proposals; do not condition timing on finding a candidate.
Source/input/runner hashes must match before and after execution. Outputs use a
fresh directory and exclusive creation; no automatic retries or resumed partial
calibration. Unexpected exceptions remain recorded. Missing, interrupted or
identity-failing observations preclude a complete-calibration recommendation.

The predeclared planning rule uses all fixtures, including failures: for each
fixture take the nearest-rank 95th percentile of wall-seconds-per-unit and
CPU-seconds-per-unit over its 20 calls; let r be the largest of those 18 values.
Recommend only an initial diagnostic cap
`min(1_000_000, floor((0.25 / r) / 1000) * 1000)` units, with a **1.0-second wall
allowance**. If this is below 1,000 or any observation is incomplete, do not
recommend a cap from this run. The factor of four between the estimated 0.25 s
cost and the 1.0 s deadline is a declared precaution, not a statistical bound.
The wall deadline always remains authoritative. Record medians, range, the
selected percentile values and the largest observed ratio rather than only the
derived cap. No ordinary-routing pop count is converted into these units.

Self-critique: these fixtures are small and exercise only shallow searches. They
cannot establish the cost distribution of large-incumbent setup, long frozen
boundary scans, 256-state searches, allocation pressure or another host. Local
CPU is unreserved; scheduling and timer overhead affect sub-millisecond calls.
The fixed rotation reduces one simple order bias but is not a workload study.
This calibration may inform a conservative first finite allowance, while actual
development opportunity/cost coverage still needs a separately frozen diagnostic.

The prepared design bytes, runner, fixture list and hash manifest will be frozen
under `results/codex/ownership-exchange-cost-calibration/prepared` before timing.
Results and interpretation will be appended below without changing those bytes.

## Observed results

`attempt001` completed all **180 calls** with exact frozen non-time output/work
agreement, unchanged hashes and no prohibited imports. This includes 120 returned
proposals and all 60 expected non-proposals. No deadline or work limit bound a
call. A separate read-only arithmetic/hash audit passes all 180 records and the
prespecified order. No calibration retry was needed.

Measurements used `dabhmbp`, arm64 macOS 26.6.2, Python 3.10.19 in the isolated
native environment. The host reported ten CPUs and load averages
55.82/65.05/80.75; its CPUs were unreserved. Query wall and CPU totals were
255.518 ms and 255.469 ms for 331,160 charged units. These are local synthetic
observations, not expected cluster or embedding times.

All table times are milliseconds; wall values are median / nearest-rank p95
over the fixed 20 calls. CPU and setup columns are medians.

| Fixture | Return | Work/call | Wall median / p95 | CPU | Setup wall |
|---|---|---:|---:|---:|---:|
| cycle | candidate | 1,527 | 1.250 / 1.522 | 1.249 | 0.176 |
| remote_single | none | 963 | 0.782 / 0.844 | 0.782 | 0.147 |
| remote_batch | candidate | 2,014 | 1.605 / 1.783 | 1.605 | 0.149 |
| site64 | candidate | 7,254 | 5.102 / 5.228 | 5.103 | 0.624 |
| site65 | none | 967 | 0.775 / 0.810 | 0.775 | 0.630 |
| owners8 | candidate | 1,769 | 1.413 / 1.670 | 1.413 | 0.257 |
| owners9 | none | 829 | 0.700 / 0.761 | 0.699 | 0.252 |
| negative_labels | candidate | 618 | 0.554 / 0.601 | 0.554 | 0.105 |
| transfer | candidate | 617 | 0.535 / 0.571 | 0.536 | 0.103 |

Setup contributes 49.245 ms of the aggregate query wall. In `site65`, which
returns no candidate, median setup alone is 0.630 ms of 0.775 ms. It is retained
in every cost ratio. Individual full-query walls range from 0.512 to 5.290 ms.
The first cycle observation is 1.575 ms versus 1.248 ms median over its remaining
19 observations; this does not estimate a general cold/warm difference.

Separate costs total 15.801 ms wall / 9.644 ms CPU for the one module import,
5.628 / 5.627 ms for argument preparation, 63.401 / 63.432 ms for diagnostic
verification, and 149.896 / 95.789 ms for JSON serialization. The script through
summary construction records 535.896 ms wall / 444.529 ms CPU. Standard-library
startup precedes that script timer. These non-query costs are excluded from the
work-throughput rule, not silently treated as deployment-free operations.

The largest fixture p95 ratio is the cycle CPU ratio,
**0.9973804846 microseconds/unit**; the largest individual wall ratio is
1.0349919094 microseconds/unit. The predeclared rule therefore recommends
**250,000 units paired with 1.0 second**, solely as an initial diagnostic choice.
The largest actually executed query used only 7,254 units. No call measured a
250,000-unit or deadline-limited search. All fixtures have source degree at most
two, target degree at most four, and at most 66 occupied sites: they cannot
certify throughput on high-degree Zephyr inputs, long frozen boundaries or large
incumbents.

After reading this calibration, root separately chose a proposed **1,250,000-unit
cap with a common five-second allowance** for its later whole-protocol freeze,
scaling the one-second recommendation by five. That is a planning extrapolation,
not a measured runtime guarantee or an authorization from this calibration to
run development inputs. Ordinary routing keeps its separately defined work
allowance; its pops are not equated with exchange units.

The immutable pre-measurement manifest has SHA-256
`bc871e7398b9710a2e2cf0d2b3420c98cff17f8ab18492c5ebca2162c305f07a`;
the frozen runner has `513a7451e76bf2aed1baf7081cbfb9435805a93a977f505c01b898b627a3cb94`.
[`attempt001/summary.json`](../../results/codex/ownership-exchange-cost-calibration/attempt001/summary.json)
contains full ranges, p95 values and first/later observations;
[`identity.json`](../../results/codex/ownership-exchange-cost-calibration/attempt001/identity.json)
records the host and clock identities.
[`reconciliation.json`](../../results/codex/ownership-exchange-cost-calibration/reconciliation.json)
independently recounts the arithmetic. The original design and every raw call
remain preserved under the prepared bundle and fresh attempt directory.
