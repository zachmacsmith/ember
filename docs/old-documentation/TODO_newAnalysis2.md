# Analysis Amendment: Shared-Graph Intersection Chart and Max Chain Length

---

## 1. Shared-Graph Intersection Comparison Chart

### Purpose

When algorithms have different success rates, naive average chain length
comparisons are misleading — an algorithm that succeeds on harder larger graphs
will appear to perform worse on average even if it produces better embeddings.
This chart computes all metrics exclusively on the intersection of graphs where
both algorithms succeeded, eliminating that bias entirely.

### What gets produced

One figure per algorithm pair, saved to `figures/pairwise/intersection_{A}_vs_{B}.png`.

The figure is a grouped bar chart with one cluster of bars per metric. Each
cluster contains two bars — one per algorithm — showing the mean of that metric
computed only on the shared success set. The metrics shown are:

- `avg_chain_length`
- `max_chain_length`
- `wall_time`
- `total_qubits`
- `qubit_overhead`

Because these metrics have different scales and units, they cannot share a
single y-axis. Normalise each metric to the better algorithm's value so bars
show relative performance: 1.0 means equal, values above 1.0 mean worse. This
is the default. The raw values should appear as bar annotations so a reader can
recover the actual numbers.

Below the chart, include a clearly visible annotation showing:

- Intersection size N (graphs where both succeeded)
- Algorithm A total successes / total attempts
- Algorithm B total successes / total attempts

This contextualises the comparison — an intersection of 5 graphs out of 50
attempts is a much weaker comparison than 45 out of 50.

Include a second set of ghost bars showing the unfiltered mean for each
algorithm (all successful runs, not just shared ones). Render these behind the
intersection bars in a lighter shade of the same colour. This makes the skew
effect visually explicit — a reader can directly see how much the average shifts
when the filter is applied.

### Data requirements

The shared-graph filter from `filters.py` handles the intersection logic.
The chart function receives a pre-filtered DataFrame — it does not implement
filtering itself. This keeps the chart function testable independently of the
filter logic.

### Integration

`generate_report()` calls this for every algorithm pair automatically. With N
algorithms in the batch there are N*(N-1)/2 pairs, each producing one figure.
These all go into `figures/pairwise/`. A failure on one pair should not prevent
the others from generating.

---

## 2. Max Chain Length

### Storage

`max_chain_length` and `chain_length_std` are computed by the worker immediately
after validation passes, while the embedding is already in memory. They are
stored in the JSONL record alongside `avg_chain_length` and `total_qubits`.

`compile_batch()` reads these values directly from the JSONL record and inserts
them into the `runs` table — no recomputation at compile time. `compile_batch()`
must include both columns in the `CREATE TABLE` statement and the insert.

This is the correct pattern for any per-run metric derivable directly from the
embedding: compute in the worker where the embedding is already in memory, store
in JSONL, insert at compile time as a plain read. Compilation is a mechanical
translation from JSONL to SQLite, not a computation step.

Existing batches that predate this change will have NULL for these columns.
Analysis code must handle NULL gracefully rather than erroring.

### Where it appears in analysis

**`overall_summary()`:** Add `max_chain_mean` (mean of per-run max chain length
across successful trials) and `max_chain_std` alongside the existing `chain_mean`
and `chain_std` columns.

**`summary_by_category()`:** Add `max_chain_length` as an available metric
parameter, selectable the same way `avg_chain_length` is.

**Graph-indexed dot plots:** Add `max_chain_length` as a fourth metric variant
alongside `avg_chain_length`, `wall_time`, and success. Saved as
`figures/graph_indexed/{by_graph_id,by_n_nodes,by_density}/max_chain_length.png`.
Same dot-per-trial structure as the `avg_chain_length` variant.

**Shared-graph intersection chart:** Already included as one of the five metrics
in the grouped bar chart above.

**Distributions:** Add a `max_chain_length` KDE plot to `figures/distributions/`
alongside the existing `avg_chain_length` KDE. One overlaid curve per algorithm,
same structure as the existing chain length distribution plot.

---

## What to Test After Implementation

**Worker computation:**
- `max_chain_length` and `chain_length_std` are present in the JSONL record
  immediately after a successful run — verify by inspecting a worker JSONL file
  directly before `compile_batch()` runs.
- `max_chain_length` in the JSONL matches `max(len(chain) for chain in
  embedding.values())` for that run (spot-check several runs).
- Neither value is recomputed in `compile_batch()` — the insert reads them
  directly from the JSONL record.

**Database:**
- `max_chain_length` and `chain_length_std` are present as columns in the
  `runs` table after `compile_batch()` runs.
- Values in the database match the JSONL source records exactly.
- Analysis does not error on batches where these columns are NULL.

**Analysis outputs:**
- `overall_summary()` includes `max_chain_mean` and `max_chain_std` columns.
- The intersection chart renders for a known algorithm pair and shows the
  correct intersection N in the annotation.
- The intersection N is smaller than or equal to the smaller of the two
  algorithms' individual success counts (set theory sanity check).
- The ghost bars (unfiltered means) are visually distinct from the intersection
  bars and labelled clearly.
- All four graph-indexed metric variants generate for all three x-axis variants
  (twelve plots total including the new max chain length variant).