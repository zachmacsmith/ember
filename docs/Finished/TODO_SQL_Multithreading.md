## Database Schema Specification

---

### Storage Architecture

Two-phase write pattern: workers write to per-worker JSONL files during execution, a single consolidation step merges them into SQLite at batch end, and a separate Parquet file holds telemetry for instrumented runs. SQLite is the source of truth for results and querying. Parquet is append-only telemetry, never queried via SQLite.

---

### JSONL Worker Files

One file per worker, named by worker ID. Each line is a self-contained JSON object representing one completed run — all fields needed to reconstruct a full result row without joining against any other file. This means denormalizing graph metadata and algorithm metadata into every record at write time, even though it creates redundancy. The cost is file size; the benefit is that consolidation is a simple insert loop with no lookups.

Workers never write to each other's files. No locking required.

---

### SQLite Tables

**`runs`** — one row per trial, the primary results table

The core table. Every completed trial has exactly one row regardless of status. Fields:

- Run identity: `run_id` (UUID, primary key), `batch_id`, `algorithm_name`, `algorithm_version`, `graph_id`, `graph_class`, `topology`, `trial`, `seed`
- Timing: `wall_time`, `cpu_time` (nullable)
- Outcome: `status`, `success`, `is_valid`, `partial`
- Embedding quality metrics (all nullable, only populated on SUCCESS): `total_qubits`, `max_chain_length`, `avg_chain_length`, `chain_length_std`, `qubit_overhead`
- Algorithmic counters (all nullable): `target_node_visits`, `cost_function_evaluations`, `embedding_state_mutations`, `overlap_qubit_iterations`
- Diagnostics: `error` (nullable text), `validation_layer` (nullable, which layer failed), `validation_check` (nullable, which check failed)
- Bookkeeping: `created_at` timestamp

Do not store the embedding dict itself in this table. It belongs in `embeddings`.

**`embeddings`** — one row per successful run, stores the actual chain assignment

Separate from `runs` because the embedding dict is large and most queries against `runs` don't need it. Fields:

- `run_id` (foreign key to `runs`, primary key)
- `embedding_json` — the validated embedding serialized as JSON text
- `n_chains`, `total_nodes` (denormalized for fast filtering without deserializing)

Only populated for `SUCCESS` status. Partial embeddings from `TIMEOUT` runs go in `partial_embeddings` (see below).

**`partial_embeddings`** — diagnostic storage for timeout partial results

Same structure as `embeddings` but for runs where `partial: True`. Excluded from all analysis queries by default. Fields mirror `embeddings` plus `n_overlapping_qubits` and `n_unresolved_chains` to quantify how close the algorithm was.

**`graphs`** — one row per unique source graph in the benchmark

Stores graph metadata that is stable across all runs on that graph. Fields:

- `graph_id` (primary key)
- `graph_class`, `topology`, `n_nodes`, `n_edges`, `density`
- Structural properties worth precomputing: `is_bipartite`, `max_degree`, `avg_degree`, `diameter` (nullable — expensive to compute for large graphs)
- `graph_json` or a reference to the graph file — the actual graph structure for reconstruction

This table exists so graph properties don't have to be recomputed per run and so queries like "all runs on graphs with density > 0.5" are fast.

**`batches`** — one row per benchmark batch

- `batch_id` (primary key)
- `started_at`, `completed_at`
- `n_runs_planned`, `n_runs_completed`, `n_success`, `n_timeout`, `n_crash`, `n_invalid_output`, `n_failure`, `n_skipped`
- `config_json` — full benchmark configuration serialized as JSON (algorithms run, graph classes, trial count, timeout, hyperparameters)
- `ember_version`, `python_version`, `platform`

**`suspensions`** — records algorithm suspension events

- `batch_id`, `algorithm_name`, `graph_class`, `suspended_at` timestamp
- `trigger_status` (CRASH or INVALID_OUTPUT), `rate_at_suspension`, `runs_completed_before_suspension`
- `runs_skipped` — count of runs not executed due to suspension

**`layer4_flags`** — Layer 4 statistical anomaly report

One row per flagged anomaly, written at batch end:

- `batch_id`, `check_name` (seed_irreproducible, timing_outlier, counter_monotonicity, universal_failure)
- `algorithm_name` (nullable), `graph_id` (nullable), `graph_class` (nullable)
- `detail_json` — structured details of the anomaly
- `flagged_at` timestamp

---

### Indexes

Create these at consolidation time, not during schema setup — indexes slow down bulk inserts:

- `runs(batch_id)`
- `runs(algorithm_name, graph_class)` — the most common query pattern
- `runs(status)` — filtering by outcome
- `runs(graph_id)` — joining to graphs table
- `runs(algorithm_name, graph_id, trial, seed)` — uniqueness enforcement and log retrieval

Add a unique constraint on `(algorithm_name, graph_id, trial, seed)` to catch duplicate inserts during consolidation.

---

### Parquet Telemetry File

Separate from SQLite entirely. Written once at consolidation from the JSONL records that include telemetry. Never joined against SQLite in normal analysis — it's for deep per-run inspection only.

**Schema** (columnar, one row per instrumented run):

- `run_id` — foreign key to SQLite `runs` for joining when needed
- `stage_number` — iteration index within the run
- `max_overlap_at_stage`, `sum_chains_at_stage`, `n_overlapping_qubits_at_stage`
- `p_fac_at_stage`, `h_max_at_stage`, `h_mean_at_stage` — cost function state
- `stage_wall_time` — time spent on this iteration

This structure assumes algorithms instrument themselves per-iteration. Only runs where the algorithm returns telemetry data produce rows here. The `run_id` join key is sufficient to connect telemetry back to the full result context in SQLite.

Partition the Parquet file by `algorithm_name` if telemetry volume is large — this makes per-algorithm convergence analysis significantly faster.

---

### Consolidation Step

The merge from JSONL → SQLite happens once, after all workers complete. It must:

1. Open SQLite with WAL mode enabled — faster for the bulk insert pattern
2. Insert all JSONL records in a single transaction per worker file — do not commit per-row
3. Enforce the unique constraint on `(algorithm_name, graph_id, trial, seed)` — duplicate records from worker file overlap should be rejected with a clear error, not silently overwritten
4. Build indexes after all inserts complete
5. Run `ANALYZE` after indexing so the query planner has accurate statistics
6. Write the Parquet telemetry file from the subset of records that include stage-level data
7. Update the `batches` row with final counts

The consolidation step is the only process that writes to SQLite. Workers never touch it directly.