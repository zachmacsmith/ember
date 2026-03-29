"""
tests/test_smoke_pipeline.py
=============================
Full pipeline smoke test, converted to pytest.

Exercises EmbeddingBenchmark → compile_batch (results.db) end-to-end using
a fixed set of inline graphs so the test never breaks because the graph suite
changed.  A reference snapshot of the deterministic output columns is stored in
``tests/reference_data/smoke_reference.csv`` and checked for regressions.

Run normally (CI / every push):
    pytest tests/test_smoke_pipeline.py -v

Generate or refresh the reference snapshot:
    UPDATE_REFERENCE=1 pytest tests/test_smoke_pipeline.py -v

The benchmark fixture is module-scoped so the 30-run benchmark executes once
and all test functions share the result.
"""

from __future__ import annotations

import csv
import json
import os
import sqlite3
from pathlib import Path

import networkx as nx
import pytest

pytestmark = pytest.mark.skipif(
    pytest.importorskip("minorminer", reason="minorminer not installed") is None,
    reason="minorminer not installed",
)

# ---------------------------------------------------------------------------
# Configuration — fixed inline problems, never driven by the graph suite
# ---------------------------------------------------------------------------

PROBLEMS = [
    ("K4",            nx.complete_graph(4)),
    ("K6",            nx.complete_graph(6)),
    ("cycle_8",       nx.cycle_graph(8)),
    ("grid_3x3",      nx.convert_node_labels_to_integers(nx.grid_2d_graph(3, 3))),
    ("bipartite_2x3", nx.complete_bipartite_graph(2, 3)),
]
METHODS    = ["minorminer", "minorminer-fast", "clique"]
TOPOLOGIES = ["chimera_4x4x4"]
N_TRIALS   = 2
SEED       = 42
TIMEOUT    = 30.0

# Deterministic columns used for regression comparison.
# Excludes timing (machine-dependent), run_id (UUID), and error (transient).
COMPARE_COLS = [
    "algorithm", "problem_name", "topology_name", "trial",
    "success", "status", "is_valid",
    "avg_chain_length", "max_chain_length",
    "total_qubits_used", "total_couplers_used",
    "problem_nodes", "problem_edges",
    "algorithm_version", "partial",
    "target_node_visits", "cost_function_evaluations",
    "embedding_state_mutations", "overlap_qubit_iterations",
]
SORT_COLS = ["topology_name", "algorithm", "problem_name", "trial"]

VALID_STATUSES = {"SUCCESS", "INVALID_OUTPUT", "TIMEOUT", "CRASH", "OOM", "FAILURE"}

REFERENCE_CSV = Path(__file__).parent / "reference_data" / "smoke_reference.csv"

# ---------------------------------------------------------------------------
# Module-scoped fixture: run the benchmark once for the whole test session
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def batch_dir(tmp_path_factory):
    """Run a full benchmark and return the batch directory path."""
    from ember_qc.benchmark import EmbeddingBenchmark

    results_root = tmp_path_factory.mktemp("smoke_results")
    bench = EmbeddingBenchmark(results_dir=str(results_root))
    path = bench.run_full_benchmark(
        problems=PROBLEMS,
        methods=METHODS,
        topologies=TOPOLOGIES,
        n_trials=N_TRIALS,
        timeout=TIMEOUT,
        seed=SEED,
        batch_note="smoke_pipeline_test",
    )
    return Path(path)

# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _rows_from_db(db_path: Path) -> list[dict]:
    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    rows = con.execute("SELECT * FROM runs").fetchall()
    con.close()
    available = set(rows[0].keys()) if rows else set()
    keep = [c for c in COMPARE_COLS if c in available]
    trimmed = [{c: str(r[c]) if r[c] is not None else "" for c in keep} for r in rows]
    return sorted(trimmed, key=lambda r: [r.get(c, "") for c in SORT_COLS])

# ---------------------------------------------------------------------------
# Output file presence
# ---------------------------------------------------------------------------

def test_batch_dir_is_directory(batch_dir):
    assert batch_dir.is_dir(), f"batch_dir not found: {batch_dir}"


def test_results_db_present(batch_dir):
    assert (batch_dir / "results.db").exists()


def test_workers_dir_present(batch_dir):
    assert (batch_dir / "workers").is_dir()


def test_config_json_present(batch_dir):
    assert (batch_dir / "config.json").exists()


def test_summary_csv_present(batch_dir):
    assert (batch_dir / "summary.csv").exists()


def test_runs_csv_present(batch_dir):
    assert (batch_dir / "runs.csv").exists()


def test_worker_jsonl_files_present(batch_dir):
    workers = list((batch_dir / "workers").glob("worker_*.jsonl"))
    assert len(workers) > 0, "No worker JSONL files found in workers/"

# ---------------------------------------------------------------------------
# results.db integrity
# ---------------------------------------------------------------------------

def test_db_row_count(batch_dir):
    expected = len(PROBLEMS) * len(METHODS) * N_TRIALS * len(TOPOLOGIES)
    con = sqlite3.connect(batch_dir / "results.db")
    actual = con.execute("SELECT COUNT(*) FROM runs").fetchone()[0]
    con.close()
    assert actual == expected, f"Expected {expected} rows, got {actual}"


def test_db_required_columns(batch_dir):
    con = sqlite3.connect(batch_dir / "results.db")
    cols = {d[1] for d in con.execute("PRAGMA table_info(runs)").fetchall()}
    con.close()
    required = {
        "algorithm", "algorithm_version", "problem_name", "topology_name",
        "trial", "seed", "wall_time", "cpu_time",
        "status", "success", "is_valid", "partial",
        "avg_chain_length", "max_chain_length",
        "total_qubits_used", "total_couplers_used",
        "problem_nodes", "problem_edges",
    }
    missing = required - cols
    assert not missing, f"runs table missing columns: {missing}"


def test_db_valid_statuses(batch_dir):
    con = sqlite3.connect(batch_dir / "results.db")
    statuses = {r[0] for r in con.execute("SELECT DISTINCT status FROM runs").fetchall()}
    con.close()
    bad = statuses - VALID_STATUSES
    assert not bad, f"Invalid status values in runs table: {bad}"


def test_db_has_at_least_one_success(batch_dir):
    con = sqlite3.connect(batch_dir / "results.db")
    count = con.execute("SELECT COUNT(*) FROM runs WHERE success=1").fetchone()[0]
    con.close()
    assert count > 0, "No successful embeddings recorded"


def test_embeddings_table_populated(batch_dir):
    con = sqlite3.connect(batch_dir / "results.db")
    n = con.execute("SELECT COUNT(*) FROM embeddings").fetchone()[0]
    con.close()
    assert n > 0, "embeddings table is empty"


def test_graphs_table_row_count(batch_dir):
    con = sqlite3.connect(batch_dir / "results.db")
    n = con.execute("SELECT COUNT(*) FROM graphs").fetchone()[0]
    con.close()
    assert n == len(PROBLEMS), f"graphs table: expected {len(PROBLEMS)} rows, got {n}"


def test_batches_table_has_one_row(batch_dir):
    con = sqlite3.connect(batch_dir / "results.db")
    n = con.execute("SELECT COUNT(*) FROM batches").fetchone()[0]
    con.close()
    assert n == 1, f"batches table: expected 1 row, got {n}"

# ---------------------------------------------------------------------------
# config.json content
# ---------------------------------------------------------------------------

def test_config_json_has_required_keys(batch_dir):
    with open(batch_dir / "config.json") as f:
        cfg = json.load(f)
    for key in ("algorithms", "topologies", "n_trials", "timeout"):
        assert key in cfg, f"config.json missing '{key}'"


def test_config_json_algorithms_match(batch_dir):
    with open(batch_dir / "config.json") as f:
        cfg = json.load(f)
    assert set(cfg["algorithms"]) == set(METHODS), (
        f"algorithms mismatch: {cfg['algorithms']} vs {METHODS}"
    )


def test_config_json_has_provenance(batch_dir):
    with open(batch_dir / "config.json") as f:
        cfg = json.load(f)
    provenance = cfg.get("provenance", {})
    assert "ember_version" in provenance, "config.json missing provenance.ember_version"

# ---------------------------------------------------------------------------
# Reference snapshot comparison
# ---------------------------------------------------------------------------

def test_reference_snapshot(batch_dir):
    """Deterministic output columns must match the stored reference snapshot.

    Skipped automatically when no reference file exists.
    Set UPDATE_REFERENCE=1 to generate or refresh the reference.
    """
    db_path = batch_dir / "results.db"
    new_rows = _rows_from_db(db_path)

    if os.environ.get("UPDATE_REFERENCE") == "1":
        REFERENCE_CSV.parent.mkdir(parents=True, exist_ok=True)
        if new_rows:
            cols = list(new_rows[0].keys())
            with open(REFERENCE_CSV, "w", newline="") as fh:
                writer = csv.DictWriter(fh, fieldnames=cols)
                writer.writeheader()
                writer.writerows(new_rows)
        pytest.skip(f"Reference snapshot written to {REFERENCE_CSV} ({len(new_rows)} rows)")

    if not REFERENCE_CSV.exists():
        pytest.skip(
            f"No reference snapshot at {REFERENCE_CSV}. "
            "Run with UPDATE_REFERENCE=1 to generate one."
        )

    with open(REFERENCE_CSV) as fh:
        ref_rows_raw = list(csv.DictReader(fh))

    keep = [c for c in COMPARE_COLS if c in (ref_rows_raw[0] if ref_rows_raw else {})]
    ref_rows = sorted(
        [{c: r.get(c, "") for c in keep} for r in ref_rows_raw],
        key=lambda r: [r.get(c, "") for c in SORT_COLS],
    )

    assert len(new_rows) == len(ref_rows), (
        f"Row count mismatch: got {len(new_rows)}, reference has {len(ref_rows)}"
    )

    diffs = []
    for i, (new, ref) in enumerate(zip(new_rows, ref_rows)):
        row_id = (new.get("algorithm"), new.get("problem_name"), new.get("trial"))
        for col in COMPARE_COLS:
            if col not in new or col not in ref:
                continue
            if new[col] != ref[col]:
                diffs.append(
                    f"  row {i} {row_id} col={col!r}: "
                    f"got {new[col]!r}, expected {ref[col]!r}"
                )

    assert not diffs, (
        f"Regression — {len(diffs)} field(s) differ:\n"
        + "\n".join(diffs[:20])
        + (f"\n  … and {len(diffs) - 20} more" if len(diffs) > 20 else "")
        + "\n\nTo accept these as the new baseline: "
        "UPDATE_REFERENCE=1 pytest tests/test_smoke_pipeline.py"
    )
