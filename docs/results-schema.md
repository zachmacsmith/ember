# Results Schema

Every completed EMBER batch produces a `results.db` SQLite database and a `runs.csv` export. This document describes every table and column.

---

## results.db

The database has five tables: `runs`, `batches`, `graphs`, `embeddings`, and `suspensions`.

### runs

One row per trial. This is the primary table for analysis.

| Column | Type | Description |
|---|---|---|
| `run_id` | TEXT PK | Unique trial identifier (UUID) |
| `batch_id` | TEXT FK | References `batches.batch_id` |
| `algorithm` | TEXT | Algorithm name as registered (e.g. `minorminer`, `clique`) |
| `algorithm_version` | TEXT | Version string reported by the algorithm |
| `graph_id` | INTEGER | Manifest graph ID; `0` for custom (user-supplied) graphs |
| `graph_name` | TEXT | Human-readable graph label (e.g. `complete_K8`) |
| `topology_name` | TEXT | Topology name (e.g. `pegasus_16`) |
| `trial` | INTEGER | Trial index within this (algorithm, problem, topology) combination (0-indexed) |
| `seed` | INTEGER | Per-trial seed derived from master seed |
| `wall_time` | REAL | Wall-clock time in seconds from start to end of `embed()` call |
| `cpu_time` | REAL | CPU time in seconds (may differ from wall_time with parallelism) |
| `status` | TEXT | Terminal status: `SUCCESS`, `TIMEOUT`, `CRASH`, `FAILURE`, `INVALID_OUTPUT` |
| `success` | INTEGER | 1 if an embedding was returned, 0 otherwise |
| `is_valid` | INTEGER | 1 if the embedding passed all validity checks, 0 otherwise; NULL if `success=0` |
| `partial` | INTEGER | 1 if the embedding covers only a subset of source nodes |
| `avg_chain_length` | REAL | Mean number of physical qubits per logical qubit across all chains |
| `max_chain_length` | INTEGER | Length of the longest single chain |
| `chain_length_std` | REAL | Standard deviation of chain lengths |
| `total_qubits_used` | INTEGER | Total physical qubits in the embedding |
| `total_couplers_used` | INTEGER | Total physical couplers used |
| `problem_nodes` | INTEGER | Number of nodes in the source graph |
| `problem_edges` | INTEGER | Number of edges in the source graph |
| `problem_density` | REAL | Edge density of the source graph (edges / possible edges) |
| `target_node_visits` | INTEGER | Algorithm-reported metric (where supported) |
| `cost_function_evaluations` | INTEGER | Algorithm-reported metric (where supported) |
| `embedding_state_mutations` | INTEGER | Algorithm-reported metric (where supported) |
| `overlap_qubit_iterations` | INTEGER | Algorithm-reported metric (where supported) |
| `error` | TEXT | Error message if `status=CRASH` or `status=INVALID_OUTPUT` |
| `created_at` | TEXT | ISO-8601 timestamp when this row was inserted |

**Uniqueness constraint:** `(algorithm, graph_id, graph_name, topology_name, trial, seed)` — duplicate rows are silently ignored during batch compilation.

**Interpreting status values:**

| Status | Meaning |
|---|---|
| `SUCCESS` | Algorithm returned an embedding; validity checks passed |
| `TIMEOUT` | `embed()` call exceeded the configured timeout |
| `CRASH` | `embed()` raised an unhandled exception |
| `FAILURE` | Algorithm returned an empty embedding without raising |
| `INVALID_OUTPUT` | Algorithm returned a non-empty embedding that failed validity checks |

---

### batches

One row per benchmark run.

| Column | Type | Description |
|---|---|---|
| `batch_id` | TEXT PK | Batch identifier (matches the directory name) |
| `started_at` | TEXT | ISO-8601 timestamp |
| `completed_at` | TEXT | ISO-8601 timestamp |
| `n_runs_planned` | INTEGER | Total trials scheduled |
| `n_runs_completed` | INTEGER | Trials actually executed |
| `n_success` | INTEGER | Count where `status=SUCCESS` |
| `n_timeout` | INTEGER | Count where `status=TIMEOUT` |
| `n_crash` | INTEGER | Count where `status=CRASH` |
| `n_invalid_output` | INTEGER | Count where `status=INVALID_OUTPUT` |
| `n_failure` | INTEGER | Count where `status=FAILURE` |
| `config_json` | TEXT | Full run config as JSON (same content as `config.json`) |
| `ember_version` | TEXT | `ember-qc` version at run time |
| `python_version` | TEXT | Python version at run time |
| `platform` | TEXT | OS and hardware platform string |

---

### graphs

One row per unique source graph. Values are duplicated from `runs` for convenient joining.

| Column | Type | Description |
|---|---|---|
| `graph_id` | INTEGER | Manifest graph ID; `0` for custom graphs (part of composite PK) |
| `graph_name` | TEXT | Human-readable graph label (part of composite PK) |
| `problem_nodes` | INTEGER | Number of nodes |
| `problem_edges` | INTEGER | Number of edges |
| `problem_density` | REAL | Edge density |

---

### embeddings

One row per successful trial. Stores the raw embedding for post-processing or export.

| Column | Type | Description |
|---|---|---|
| `run_id` | TEXT PK FK | References `runs.run_id` |
| `embedding_json` | TEXT | JSON mapping `{source_node: [target_qubits]}` |
| `n_chains` | INTEGER | Number of chains (equals `problem_nodes` for complete embeddings) |
| `total_qubits_used` | INTEGER | Redundant with `runs.total_qubits_used`; kept for direct access |

---

### suspensions

One row per algorithm suspension event. EMBER suspends an algorithm when its failure rate on a given problem type exceeds a threshold, to avoid wasting compute on systematically failing algorithms.

| Column | Type | Description |
|---|---|---|
| `id` | INTEGER PK | Auto-increment |
| `batch_id` | TEXT | Batch where suspension occurred |
| `algorithm` | TEXT | Suspended algorithm |
| `graph_name` | TEXT | Graph that triggered suspension |
| `suspended_at` | TEXT | ISO-8601 timestamp |
| `trigger_status` | TEXT | Status that triggered suspension (`TIMEOUT`, `CRASH`, etc.) |
| `rate_at_suspension` | REAL | Failure rate at the time of suspension |
| `runs_completed_before` | INTEGER | Successful runs before this suspension |
| `runs_skipped` | INTEGER | Runs skipped due to this suspension |

---

## Loading from Python

To load from SQLite with a join:

```python
import sqlite3, pandas as pd
con = sqlite3.connect("results/my_batch/results.db")
df = pd.read_sql("""
    SELECT r.*, b.ember_version
    FROM runs r
    JOIN batches b USING (batch_id)
    WHERE r.success = 1
""", con)
```

---

## summary.csv

`summary.csv` contains aggregated statistics per `(algorithm, topology_name)` group. It is generated after compilation as a convenience view.

Typical columns: `algorithm`, `topology_name`, `n_trials`, `success_rate`, `avg_chain_length_mean`, `avg_chain_length_std`, `wall_time_mean`, `wall_time_std`.

---

## config.json

Every batch directory contains a `config.json` recording the full run environment:

```json
{
  "batch_id": "my_benchmark_2026-03-28_14-30-00",
  "ember_version": "0.5.0",
  "python_version": "3.12.2",
  "platform": "macOS-14.2.1-arm64",
  "processor": "Apple M3",
  "dependencies": {
    "minorminer": "0.2.21",
    "networkx": "3.2.1"
  },
  "algorithms": ["minorminer", "clique"],
  "graphs": "quick",
  "topologies": ["pegasus_16"],
  "n_trials": 3,
  "timeout": 60.0,
  "seed": 42,
  "workers": 1
}
```

This is also stored in `batches.config_json` in the database.

---

## worker JSONL files

During a run, each worker writes one JSON record per trial to `workers/worker_<pid>.jsonl`. These are low-level records used for checkpointing and crash recovery. After successful compilation into `results.db`, they can be ignored.
