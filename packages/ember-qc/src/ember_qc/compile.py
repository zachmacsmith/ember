"""
ember_qc/compile.py
==================
Consolidate per-worker JSONL files into a SQLite database after a benchmark run.

Usage (called automatically by EmbeddingBenchmark.run_full_benchmark):
    from ember_qc.compile import compile_batch
    compile_batch(batch_dir)

Can also be run as a standalone script to recompile an existing batch:
    python -m ember_qc.compile results/batch_2026-03-14_10-30-00
"""

import json
import platform
import sqlite3
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Union

import pandas as pd


# ── Schema ─────────────────────────────────────────────────────────────────────

_DDL = """
PRAGMA journal_mode = WAL;

CREATE TABLE IF NOT EXISTS batches (
    batch_id              TEXT PRIMARY KEY,
    started_at            TEXT,
    completed_at          TEXT,
    n_runs_planned        INTEGER,
    n_runs_completed      INTEGER,
    n_success             INTEGER,
    n_timeout             INTEGER,
    n_crash               INTEGER,
    n_invalid_output      INTEGER,
    n_failure             INTEGER,
    config_json           TEXT,
    ember_version         TEXT,
    python_version        TEXT,
    platform              TEXT
);

CREATE TABLE IF NOT EXISTS graphs (
    problem_name          TEXT PRIMARY KEY,
    problem_nodes         INTEGER,
    problem_edges         INTEGER,
    problem_density       REAL
);

CREATE TABLE IF NOT EXISTS runs (
    run_id                        TEXT PRIMARY KEY,
    batch_id                      TEXT REFERENCES batches(batch_id),
    algorithm                     TEXT,
    algorithm_version             TEXT,
    problem_name                  TEXT REFERENCES graphs(problem_name),
    topology_name                 TEXT,
    trial                         INTEGER,
    seed                          INTEGER,
    wall_time                     REAL,
    cpu_time                      REAL,
    status                        TEXT,
    success                       INTEGER,
    is_valid                      INTEGER,
    partial                       INTEGER,
    avg_chain_length              REAL,
    max_chain_length              INTEGER,
    chain_length_std              REAL,
    total_qubits_used             INTEGER,
    total_couplers_used           INTEGER,
    problem_nodes                 INTEGER,
    problem_edges                 INTEGER,
    problem_density               REAL,
    target_node_visits            INTEGER,
    cost_function_evaluations     INTEGER,
    embedding_state_mutations     INTEGER,
    overlap_qubit_iterations      INTEGER,
    error                         TEXT,
    created_at                    TEXT,
    UNIQUE(algorithm, problem_name, topology_name, trial, seed)
);

CREATE TABLE IF NOT EXISTS embeddings (
    run_id                TEXT PRIMARY KEY REFERENCES runs(run_id),
    embedding_json        TEXT,
    n_chains              INTEGER,
    total_qubits_used     INTEGER
);

-- partial_embeddings: stub — benchmark_one() discards the partial embedding
-- (sets raw_embedding = None) before constructing EmbeddingResult, so no data
-- ever reaches the JSONL. Populate once benchmark_one() is updated to preserve
-- the partial chain assignment on TIMEOUT runs.

CREATE TABLE IF NOT EXISTS suspensions (
    id                            INTEGER PRIMARY KEY AUTOINCREMENT,
    batch_id                      TEXT,
    algorithm                     TEXT,
    problem_name                  TEXT,
    suspended_at                  TEXT,
    trigger_status                TEXT,
    rate_at_suspension            REAL,
    runs_completed_before         INTEGER,
    runs_skipped                  INTEGER
);

CREATE TABLE IF NOT EXISTS layer4_flags (
    id                            INTEGER PRIMARY KEY AUTOINCREMENT,
    batch_id                      TEXT,
    check_name                    TEXT,
    algorithm                     TEXT,
    problem_name                  TEXT,
    detail_json                   TEXT,
    flagged_at                    TEXT
);
"""

_INDEX_DDL = """
CREATE INDEX IF NOT EXISTS idx_runs_batch        ON runs(batch_id);
CREATE INDEX IF NOT EXISTS idx_runs_algo_problem ON runs(algorithm, problem_name);
CREATE INDEX IF NOT EXISTS idx_runs_status       ON runs(status);
CREATE INDEX IF NOT EXISTS idx_runs_problem      ON runs(problem_name);
"""


# ── Helpers ────────────────────────────────────────────────────────────────────

def _bool_int(val) -> int:
    """Coerce any truthy value to 0/1 for SQLite INTEGER columns."""
    if isinstance(val, bool):
        return int(val)
    if isinstance(val, str):
        return 1 if val.lower() in ('true', '1', 'yes') else 0
    return 1 if val else 0


def _read_jsonl(path: Path) -> list:
    records = []
    with open(path) as fh:
        for line in fh:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


# ── Core consolidation ─────────────────────────────────────────────────────────

def compile_batch(batch_dir: Union[str, Path]) -> Path:
    """Consolidate worker JSONL files into SQLite and export runs.csv.

    Steps:
      1. Read all workers/worker_*.jsonl files.
      2. Create results.db with the full schema.
      3. Insert records (one transaction per worker file).
      4. Build indexes and ANALYZE.
      5. Export runs.csv for backward compatibility with qeanalysis.
      6. Parquet telemetry — stub (not yet implemented).

    Args:
        batch_dir: Path to a batch directory produced by EmbeddingBenchmark.

    Returns:
        Path to the created results.db file.
    """
    batch_dir = Path(batch_dir)
    workers_dir = batch_dir / "workers"
    db_path = batch_dir / "results.db"

    jsonl_files = sorted(workers_dir.glob("worker_*.jsonl")) if workers_dir.exists() else []
    if not jsonl_files:
        print(f"  compile_batch: no worker JSONL files found in {workers_dir}")
        return db_path

    # Read config for provenance
    config: dict = {}
    config_json = batch_dir / "config.json"
    if config_json.exists():
        with open(config_json) as fh:
            config = json.load(fh)

    batch_id = batch_dir.name
    provenance = config.get("provenance", {})

    con = sqlite3.connect(db_path)
    con.executescript(_DDL)
    # Migrate: add chain_length_std if absent (DBs created before this version)
    try:
        con.execute("ALTER TABLE runs ADD COLUMN chain_length_std REAL")
        con.commit()
    except sqlite3.OperationalError:
        pass  # column already exists

    # Insert or ignore batches row (started_at from config timestamp if available)
    con.execute(
        """INSERT OR IGNORE INTO batches
           (batch_id, started_at, n_runs_planned, config_json,
            ember_version, python_version, platform)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (
            batch_id,
            config.get("timestamp"),
            config.get("total_measured_runs"),
            json.dumps(config),
            provenance.get("ember_version"),
            provenance.get("python_version", platform.python_version()),
            provenance.get("platform", platform.platform()),
        ),
    )
    con.commit()

    now_iso = datetime.now(timezone.utc).isoformat()
    total_inserted = 0
    duplicate_count = 0

    for jf in jsonl_files:
        records = _read_jsonl(jf)
        with con:
            for rec in records:
                # ── graphs table (upsert-or-ignore) ───────────────────────────
                con.execute(
                    """INSERT OR IGNORE INTO graphs
                       (problem_name, problem_nodes, problem_edges, problem_density)
                       VALUES (?, ?, ?, ?)""",
                    (
                        rec.get("problem_name"),
                        rec.get("problem_nodes"),
                        rec.get("problem_edges"),
                        rec.get("problem_density"),
                    ),
                )

                # ── runs table ────────────────────────────────────────────────
                run_id = str(uuid.uuid4())
                embedding = rec.get("embedding")
                # chain_length_std: compute from chain_lengths list in JSONL
                _chain_lengths = rec.get("chain_lengths") or []
                _chain_length_std = (
                    float(__import__('statistics').stdev(_chain_lengths))
                    if len(_chain_lengths) >= 2 else 0.0
                )
                try:
                    con.execute(
                        """INSERT INTO runs (
                               run_id, batch_id,
                               algorithm, algorithm_version,
                               problem_name, topology_name, trial, seed,
                               wall_time, cpu_time,
                               status, success, is_valid, partial,
                               avg_chain_length, max_chain_length, chain_length_std,
                               total_qubits_used, total_couplers_used,
                               problem_nodes, problem_edges, problem_density,
                               target_node_visits, cost_function_evaluations,
                               embedding_state_mutations, overlap_qubit_iterations,
                               error, created_at
                           ) VALUES (
                               ?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?
                           )""",
                        (
                            run_id,
                            rec.get("batch_id", batch_id),
                            rec.get("algorithm"),
                            rec.get("algorithm_version"),
                            rec.get("problem_name"),
                            rec.get("topology_name"),
                            rec.get("trial"),
                            rec.get("seed"),
                            rec.get("wall_time"),
                            rec.get("cpu_time"),
                            rec.get("status"),
                            _bool_int(rec.get("success")),
                            _bool_int(rec.get("is_valid")),
                            _bool_int(rec.get("partial")),
                            rec.get("avg_chain_length"),
                            rec.get("max_chain_length"),
                            _chain_length_std,
                            rec.get("total_qubits_used"),
                            rec.get("total_couplers_used"),
                            rec.get("problem_nodes"),
                            rec.get("problem_edges"),
                            rec.get("problem_density"),
                            rec.get("target_node_visits"),
                            rec.get("cost_function_evaluations"),
                            rec.get("embedding_state_mutations"),
                            rec.get("overlap_qubit_iterations"),
                            rec.get("error"),
                            now_iso,
                        ),
                    )
                    total_inserted += 1

                    # ── embeddings ────────────────────────────────────────────
                    if embedding and _bool_int(rec.get("success")):
                        emb_json = json.dumps(embedding)
                        con.execute(
                            """INSERT OR IGNORE INTO embeddings
                               (run_id, embedding_json, n_chains, total_qubits_used)
                               VALUES (?, ?, ?, ?)""",
                            (
                                run_id,
                                emb_json,
                                len(embedding),
                                rec.get("total_qubits_used"),
                            ),
                        )
                    # partial_embeddings: not written — benchmark_one() nulls
                    # raw_embedding on TIMEOUT before the result is constructed.

                except sqlite3.IntegrityError:
                    duplicate_count += 1

    # ── Indexes and statistics ─────────────────────────────────────────────────
    con.executescript(_INDEX_DDL)
    con.execute("ANALYZE")

    # ── Update batches row with final counts ───────────────────────────────────
    counts = con.execute(
        """SELECT
               COUNT(*),
               SUM(CASE WHEN status='SUCCESS'        THEN 1 ELSE 0 END),
               SUM(CASE WHEN status='TIMEOUT'        THEN 1 ELSE 0 END),
               SUM(CASE WHEN status='CRASH'          THEN 1 ELSE 0 END),
               SUM(CASE WHEN status='INVALID_OUTPUT' THEN 1 ELSE 0 END),
               SUM(CASE WHEN status='FAILURE'        THEN 1 ELSE 0 END)
           FROM runs WHERE batch_id = ?""",
        (batch_id,),
    ).fetchone()
    con.execute(
        """UPDATE batches SET
               completed_at       = ?,
               n_runs_completed   = ?,
               n_success          = ?,
               n_timeout          = ?,
               n_crash            = ?,
               n_invalid_output   = ?,
               n_failure          = ?
           WHERE batch_id = ?""",
        (now_iso, *counts, batch_id),
    )
    con.commit()
    con.close()

    if duplicate_count:
        print(f"  compile_batch: {duplicate_count} duplicate record(s) skipped")

    # ── Export runs.csv (backward compat with qeanalysis) ─────────────────────
    _export_runs_csv(db_path, batch_dir)

    # ── Parquet telemetry — stub ───────────────────────────────────────────────
    # Not yet implemented: algorithms do not yet emit per-stage telemetry.
    # When instrumented runs are available, read records with a 'stages' key
    # from the JSONL files and write a partitioned Parquet file here.

    print(f"  compile_batch: {total_inserted} run(s) written → {db_path.name}")
    return db_path


def _export_runs_csv(db_path: Path, batch_dir: Path) -> None:
    """Export the runs table as runs.csv for qeanalysis backward compatibility."""
    con = sqlite3.connect(db_path)
    df = pd.read_sql_query(
        """SELECT
               algorithm, problem_name, topology_name, trial, seed,
               wall_time, cpu_time, status, success, is_valid, partial,
               avg_chain_length, max_chain_length, chain_length_std,
               total_qubits_used, total_couplers_used,
               problem_nodes, problem_edges, problem_density,
               target_node_visits, cost_function_evaluations,
               embedding_state_mutations, overlap_qubit_iterations,
               algorithm_version, error
           FROM runs
           WHERE batch_id = ?
           ORDER BY topology_name, algorithm, problem_name, trial""",
        con,
        params=(db_path.parent.name,),
    )
    con.close()
    # Coerce 0/1 integer columns to bool, preserving NULL as empty.
    # .astype(bool) is unsafe: NaN (from NULL) converts to True rather than NA.
    for col in ("success", "is_valid", "partial"):
        df[col] = df[col].apply(lambda x: bool(x) if pd.notna(x) else None)
    df.to_csv(batch_dir / "runs.csv", index=False)


# ── CLI entry point ────────────────────────────────────────────────────────────

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python -m ember_qc.compile <batch_dir>")
        sys.exit(1)
    compile_batch(sys.argv[1])
