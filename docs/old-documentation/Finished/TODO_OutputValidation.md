# Runner Validation: Implementation Specification

---

## Overview

The runner must validate every algorithm result independently before it enters
the database. The algorithm is treated as an untrusted black box — nothing it
claims about its own output is accepted without verification.

Validation is split into four layers. Layers 1-3 are mandatory and run on every
single result. Layer 4 is a batch-level post-processing step that runs once after
all trials complete.

A result that fails any Layer 1-3 check is assigned status `INVALID_OUTPUT` and
has no quality metrics computed. It is stored for debugging purposes only.

---

## Where Validation Lives in the Codebase

Validation should be implemented as a single module (e.g. `validation.py`) that
the runner imports. It should have no dependencies on algorithm code — only on
the result dict, the source graph, and the target graph. The runner calls validation
immediately after `embed()` returns and before writing anything to the database.

The runner should never inline validation logic — all checks go through this module
so they can be tested independently and updated without touching runner logic.

---

## Layer 1 — Structural Validation

**Purpose:** Verify that the embedding is mathematically correct.

**When it runs:** On every result where `success: True` and the embedding is
non-empty. If the algorithm returned `success: False`, skip Layer 1 and go
directly to Layer 3.

**Checks (in this order):**

1. **Coverage** — every vertex in the source graph has a corresponding key in the
   embedding dict. No source vertex may be absent.

2. **Non-empty chains** — every chain in the embedding contains at least one
   target node. A key mapping to an empty list is a structural failure.

3. **Connectivity** — for every chain, the set of target nodes it contains must
   form a connected subgraph of the target graph. Use the target graph's adjacency
   structure to verify this. A chain of length 1 is trivially connected.

4. **Disjointness** — no target node may appear in more than one chain. Build a
   reverse map (target node → source vertex) while iterating chains and fail
   immediately on the first collision.

5. **Edge preservation** — for every edge in the source graph, at least one edge
   must exist in the target graph between the two corresponding chains. This
   requires checking target graph adjacency between every pair of chains connected
   by a source edge.

**Failure behavior:** The first failing check sets status to `INVALID_OUTPUT`.
Record which check failed and a human-readable description of why (e.g. which
source vertex was missing, which target node was duplicated). Do not continue
to subsequent checks after a failure — return immediately.

**Performance note:** All five checks are O(n + e) in total across the source and
target graphs. Do not implement them in a way that is quadratic — disjointness in
particular should use a set or dict, not nested loops.

---

## Layer 2 — Type and Format Validation

**Purpose:** Catch serialization bugs and type errors before they corrupt the
database.

**When it runs:** On every result, before Layer 1. Type errors would cause Layer 1
to crash rather than fail gracefully, so Layer 2 must run first.

**Checks:**

1. **Key validity** — all keys in the embedding dict are node IDs that exist in
   the source graph. No extra keys, no missing keys (this overlaps with Layer 1
   coverage check but catches the case where extra spurious keys are present).

2. **Value validity** — all node IDs in every chain exist in the target graph.

3. **Type correctness** — all keys and chain values are plain Python `int`. The
   most common failure here is `numpy.int64` leaking from internal algorithm
   computation. This breaks JSON serialization and database storage silently.
   Check the type explicitly, not just whether the value is integer-like.

4. **Chain format** — all chains are Python `list` objects. Sets, tuples, and
   numpy arrays are invalid even if their contents would otherwise pass.

5. **Wall time validity** — wall time must be a positive, finite float. Reject
   NaN, infinity, zero, and negative values.

6. **CPU time plausibility** — if `cpu_time` is present in the result, it must
   be a non-negative float and must not exceed wall time multiplied by the number
   of CPU cores on the machine. CPU time greater than wall time × cores is
   physically impossible and indicates a measurement bug. Use `os.cpu_count()` to
   get core count at runtime.

**Failure behavior:** Same as Layer 1 — first failure sets `INVALID_OUTPUT`,
record which check failed, return immediately.

---

## Layer 3 — Consistency Validation

**Purpose:** Catch logical contradictions between fields in the result dict.

**When it runs:** On every result, after Layers 1 and 2.

**Checks:**

1. **Success implies non-empty embedding** — if `success: True`, the embedding
   must be non-empty. An algorithm claiming success with an empty dict is
   contradicting itself.

2. **Failure implies empty embedding** — if `success: False` and `partial: False`,
   the embedding should be empty. A non-empty embedding on a non-partial failure
   is a contradiction. This is a warning-level flag rather than a hard failure —
   log it but do not necessarily set `INVALID_OUTPUT` unless the embedding also
   fails Layer 1.

3. **Counter types** — any algorithmic counters present in the result
   (`target_node_visits`, `cost_function_evaluations`, `embedding_state_mutations`,
   `overlap_qubit_iterations`) must be non-negative Python `int` values. Floats
   and negative values are invalid.

4. **Status is a known value** — if `status` is present, it must be one of the
   defined valid status strings. Unknown status strings are rejected.

**Failure behavior:** Hard failures (checks 1, 3, 4) set `INVALID_OUTPUT`.
Soft failures (check 2) are logged as warnings but do not change the status.

---

## Layer 4 — Statistical Sanity Checks

**Purpose:** Catch systematic issues that only become visible across many runs.

**When it runs:** Once, after the full batch completes and all results are in
the database. This is a reporting step, not a gating step — it produces a
flagged anomaly report for human review. It does not retroactively change the
status of any result already stored.

**Checks:**

1. **Seed reproducibility** — for a random sample of successful results (suggested:
   5% of the batch), re-run the same (algorithm, graph, topology, seed) triple and
   compare the returned embedding to the stored one. If they differ, the algorithm
   is not properly seeded. Flag the algorithm and graph class combination. Do not
   modify stored results — add a separate reproducibility flag.

2. **Timing outliers** — for each (algorithm, graph class) combination, compute
   the median wall time across all runs. Flag any individual run where wall time
   exceeds 10× that median. These may indicate hangs, unenforced timeouts, or
   system-level interference.

3. **Counter monotonicity** — for each algorithm, group successful results by
   source graph size. For each counter field, check whether counter values
   generally increase with graph size. Flag cases where a larger graph required
   fewer operations than a smaller one. This is a soft flag — not impossible, but
   worth investigating.

4. **Universal failure detection** — identify any graph instance where no algorithm
   in the benchmark achieved `SUCCESS`. Flag these instances as potentially
   unembeddable or as candidates for a shared bug in how that graph type is handled.

**Output:** Layer 4 produces a structured anomaly report that is written to the
runner log and printed to stderr as a summary. It does not modify the results
database.

---

## Integration with the Runner

The runner's `benchmark_one()` function should follow this sequence after
`embed()` returns:

1. Measure wall time externally using `perf_counter()` — do not trust the
   algorithm's reported time as the authoritative value.
2. Run Layer 2 (type/format) first.
3. Run Layer 1 (structural) if Layer 2 passed and the algorithm reported success.
4. Run Layer 3 (consistency) unconditionally.
5. Determine final status from validation results — a passing validation on a
   success result becomes `SUCCESS`; any validation failure becomes
   `INVALID_OUTPUT`.
6. Compute quality metrics (chain lengths, qubit overhead, etc.) only if final
   status is `SUCCESS`.
7. Write the result to the database regardless of status — all results are stored,
   but only `SUCCESS` results have metrics populated.

Layer 4 is called separately after the batch loop completes, not inside
`benchmark_one()`.

---

## What to Test After Implementation

**Unit tests for each check in isolation:**

- Layer 1: construct minimally invalid embeddings that fail exactly one check each
  (missing vertex, empty chain, disconnected chain, shared qubit, missing edge).
  Verify the correct check name is reported in each case.
- Layer 2: construct results with numpy int keys, tuple chains, NaN wall time,
  and CPU time exceeding wall × cores. Verify each is caught.
- Layer 3: construct results with `success: True` and empty embedding, results
  with float counters, and results with unknown status strings.

**Integration tests:**

- A known-valid embedding passes all three layers and is assigned `SUCCESS`.
- A known-invalid embedding (one shared qubit) passes Layer 2, fails Layer 1
  check 4, and is assigned `INVALID_OUTPUT`.
- An algorithm that returns `numpy.int64` keys is caught at Layer 2 before
  Layer 1 runs.
- The runner's final status field matches what validation determined, not what
  the algorithm self-reported.

**Layer 4 tests:**

- A batch where one algorithm is given a fixed seed but shuffles internally
  produces a `seed_irreproducible` flag.
- A batch with one injected 100× timing outlier produces a `timing_outlier` flag.
- A batch where all algorithms fail on one instance produces a `universal_failure`
  flag for that instance.

**Regression test:**

- Run the full validation suite against all currently registered algorithms on
  a small graph. All should pass Layers 1-3 without `INVALID_OUTPUT`. If any
  fail, fix the algorithm wrapper before merging the validation module.