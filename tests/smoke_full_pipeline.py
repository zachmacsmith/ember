"""
Smoke Benchmark — Full End-to-End Pipeline
==========================================
Run this manually after major architectural changes to validate the complete
pipeline: EmbeddingBenchmark → compile_batch → ResultsManager → BenchmarkAnalysis.

What it exercises:
  1. EmbeddingBenchmark.run_full_benchmark() with explicit problem list
  2. Multi-topology run (chimera_4x4x4, pegasus_4)
  3. compile_batch: results.db created with runs/embeddings/graphs/batches tables
  4. workers/ directory populated with per-process JSONL files
  5. summary.csv present and non-empty
  6. BenchmarkAnalysis.generate_report() runs without error
  7. Expected output files exist: figures/ (subdirs) + summary/ + statistics/ populated
  8. results.db has correct number of rows and key columns
  9. All row statuses are valid enum values
 10. At least one algorithm succeeds on every graph in each topology
 11. Deterministic columns match the stored reference snapshot

Reference comparison
--------------------
A reference snapshot (COMPARE_COLS only, sorted) is stored in
tests/reference_data/smoke_reference.csv. After each run the smoke test
compares the new output against this snapshot. Any deviation is flagged as
a regression — architectural changes should not alter embedding results.

To update the reference (e.g. after intentionally fixing a bug):
  Option A — flip the flag below:
      UPDATE_REFERENCE = True   (remember to set it back before committing)

  Option B — environment variable (keeps the file unchanged):
      UPDATE_REFERENCE=1 conda run -n minor python tests/smoke_full_pipeline.py

Run normally:
    conda run -n minor python tests/smoke_full_pipeline.py
"""

import csv
import json
import os
import sqlite3
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import networkx as nx

from qebench.benchmark import EmbeddingBenchmark

# ── Configuration ─────────────────────────────────────────────────────────────

# Flip to True (or set env var UPDATE_REFERENCE=1) to overwrite the reference
# snapshot with the current run's output. Reset to False before committing.
UPDATE_REFERENCE: bool = os.environ.get("UPDATE_REFERENCE", "0") == "1"

SEED = 42  # Fixed seed passed to run_full_benchmark() — keeps results deterministic

PROBLEMS = [
    ("K4",             nx.complete_graph(4)),
    ("K6",             nx.complete_graph(6)),
    ("ER_n8_d04",      nx.erdos_renyi_graph(8, 0.4, seed=42)),
    ("cycle_10",       nx.cycle_graph(10)),
    ("bipartite_3x3",  nx.complete_bipartite_graph(3, 3)),
    ("grid_3x3",       nx.convert_node_labels_to_integers(nx.grid_2d_graph(3, 3))),
]

METHODS    = ["minorminer", "minorminer-fast", "clique"]
TOPOLOGIES = ["chimera_4x4x4", "pegasus_4"]
N_TRIALS   = 2
TIMEOUT    = 30.0

VALID_STATUSES = {"SUCCESS", "INVALID_OUTPUT", "TIMEOUT", "CRASH", "OOM", "FAILURE"}

# Paths relative to figures/ — subdirectory layout produced by generate_report()
EXPECTED_FIGURES = [
    # distributions/
    "distributions/chain_length_kde.png",
    "distributions/max_chain_length_kde.png",
    "distributions/chain_length_violin.png",
    "distributions/embedding_time_violin.png",
    "distributions/avg_chain_length_by_category.png",
    "distributions/consistency_cv.png",
    # scaling/
    "scaling/scaling_avg_chain_length_vs_problem_nodes.png",
    "scaling/scaling_wall_time_vs_problem_nodes.png",
    "scaling/density_hardness_avg_chain_length.png",
    # pairwise/
    "pairwise/win_rate_matrix.png",
    # success/
    "success/success_rate_heatmap.png",
    "success/success_rate_by_nodes.png",
    "success/success_rate_by_density.png",
    # topology/
    "topology/topology_comparison_avg_chain_length.png",
    # root figures/
    "pareto_wall_time_vs_avg_chain_length.png",
    # graph_indexed/
    "graph_indexed/by_graph_id/chain_length.png",
    "graph_indexed/by_graph_id/max_chain_length.png",
    "graph_indexed/by_graph_id/embedding_time.png",
    "graph_indexed/by_graph_id/success.png",
    "graph_indexed/by_n_nodes/chain_length.png",
    "graph_indexed/by_n_nodes/max_chain_length.png",
    "graph_indexed/by_n_nodes/embedding_time.png",
    "graph_indexed/by_n_nodes/success.png",
    "graph_indexed/by_density/chain_length.png",
    "graph_indexed/by_density/max_chain_length.png",
    "graph_indexed/by_density/embedding_time.png",
    "graph_indexed/by_density/success.png",
    # pairwise intersection comparisons (all 3 pairs from METHODS sorted)
    "pairwise/intersection_clique_vs_minorminer.png",
    "pairwise/intersection_clique_vs_minorminer-fast.png",
    "pairwise/intersection_minorminer_vs_minorminer-fast.png",
]

# Tables are now written to summary/ (renamed from tables/)
EXPECTED_TABLES = [
    "overall_summary.csv",
    "overall_summary.tex",
    "rank_table_chain.csv",
    "rank_table_chain.tex",
    "pairwise_comparison.csv",
    "pairwise_comparison.tex",
]

EXPECTED_STATS = [
    "significance_tests.csv",
    "friedman_test.txt",
    "correlation_matrix.csv",
    "win_rate_matrix.csv",
]

# Reference snapshot location
REFERENCE_DIR = Path(__file__).parent / "reference_data"
REFERENCE_CSV = REFERENCE_DIR / "smoke_reference.csv"

# Columns used for regression comparison — excludes timing (varies per machine),
# seed (RNG-internal), run_id (UUID), and error (transient strings). Everything
# else must be bit-identical to the reference when the same master seed is used.
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

# Sort key for stable row ordering before comparison
SORT_COLS = ["topology_name", "algorithm", "problem_name", "trial"]


# ── Helpers ───────────────────────────────────────────────────────────────────

passed = 0
failed = 0
issues = []


def check(condition: bool, label: str):
    global passed, failed
    if condition:
        passed += 1
    else:
        failed += 1
        issues.append(label)


def section(title: str):
    print(f"\n{'─' * 70}")
    print(f"  {title}")
    print(f"{'─' * 70}")


def _read_compare_rows_from_db(db_path: Path) -> list:
    """Query results.db and return sorted rows with only COMPARE_COLS."""
    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    # Fetch all columns — we'll filter to COMPARE_COLS after
    rows = con.execute(
        "SELECT * FROM runs ORDER BY topology_name, algorithm, problem_name, trial"
    ).fetchall()
    con.close()

    available = set(rows[0].keys()) if rows else set()
    cols = [c for c in COMPARE_COLS if c in available]
    trimmed = [{c: str(r[c]) if r[c] is not None else "" for c in cols} for r in rows]
    return sorted(trimmed, key=lambda r: [r.get(c, "") for c in SORT_COLS])


def _read_compare_rows_from_csv(csv_path: Path) -> list:
    """Read the reference CSV and return sorted rows with only COMPARE_COLS."""
    with open(csv_path) as fh:
        rows = list(csv.DictReader(fh))
    cols = [c for c in COMPARE_COLS if c in (rows[0] if rows else {})]
    trimmed = [{c: r[c] for c in cols} for r in rows]
    return sorted(trimmed, key=lambda r: [r.get(c, "") for c in SORT_COLS])


# ── RUN ───────────────────────────────────────────────────────────────────────

with tempfile.TemporaryDirectory(prefix="qebench_smoke_") as tmpdir:

    results_root = Path(tmpdir) / "results"
    analysis_root = Path(tmpdir) / "analysis"

    section("STEP 1: EmbeddingBenchmark.run_full_benchmark()")

    bench = EmbeddingBenchmark(results_dir=str(results_root))
    batch_dir = bench.run_full_benchmark(
        problems=PROBLEMS,
        methods=METHODS,
        topologies=TOPOLOGIES,
        n_trials=N_TRIALS,
        timeout=TIMEOUT,
        seed=SEED,
        batch_note="smoke_full_pipeline",
    )

    check(batch_dir is not None, "run_full_benchmark() returned None")
    batch_path = Path(batch_dir)
    check(batch_path.is_dir(), f"batch_dir does not exist: {batch_path}")
    print(f"  Batch directory: {batch_path.name}")

    # ── CHECK 2: Output files present ────────────────────────────────────────

    section("CHECK 2: Results files present")

    db_path      = batch_path / "results.db"
    workers_dir  = batch_path / "workers"
    config_json  = batch_path / "config.json"
    summary_csv  = batch_path / "summary.csv"
    runs_csv     = batch_path / "runs.csv"   # exported from SQLite for qeanalysis

    check(db_path.exists(),     "results.db not found in batch dir")
    check(workers_dir.is_dir(), "workers/ directory not found in batch dir")
    check(config_json.exists(), "config.json not found in batch dir")
    check(summary_csv.exists(), "summary.csv not found in batch dir")
    check(runs_csv.exists(),    "runs.csv not found in batch dir")

    jsonl_files = list(workers_dir.glob("worker_*.jsonl")) if workers_dir.exists() else []
    check(len(jsonl_files) > 0, "No worker JSONL files found in workers/")

    for f in [db_path, workers_dir, config_json, summary_csv, runs_csv]:
        exists = f.exists()
        print(f"  {'✓' if exists else '✗'}  {f.name}")
    print(f"  ✓  workers/ contains {len(jsonl_files)} JSONL file(s)")

    # ── CHECK 3: results.db integrity ────────────────────────────────────────

    section("CHECK 3: results.db integrity")

    db_rows = []
    if db_path.exists():
        con = sqlite3.connect(db_path)
        con.row_factory = sqlite3.Row

        # Row count
        db_rows = con.execute("SELECT * FROM runs").fetchall()
        expected_rows = len(PROBLEMS) * len(METHODS) * N_TRIALS * len(TOPOLOGIES)
        check(len(db_rows) == expected_rows,
              f"runs table: expected {expected_rows} rows, got {len(db_rows)}")
        print(f"  Row count: {len(db_rows)} (expected {expected_rows})")

        # Required columns
        col_names = {d[1] for d in con.execute("PRAGMA table_info(runs)").fetchall()}
        required_cols = {
            "algorithm", "algorithm_version", "problem_name", "topology_name",
            "trial", "seed", "wall_time", "cpu_time",
            "status", "success", "is_valid", "partial",
            "avg_chain_length", "max_chain_length",
            "total_qubits_used", "total_couplers_used",
            "problem_nodes", "problem_edges",
        }
        missing_cols = required_cols - col_names
        check(not missing_cols, f"runs table missing columns: {missing_cols}")
        print(f"  Columns present: {len(col_names)} "
              f"({'all required' if not missing_cols else 'MISSING: ' + str(missing_cols)})")

        # Status validity
        bad_statuses = [
            r["status"] for r in db_rows if r["status"] not in VALID_STATUSES
        ]
        check(not bad_statuses,
              f"runs table: {len(bad_statuses)} rows with invalid status: {set(bad_statuses)}")
        print(f"  Status validity: {'OK' if not bad_statuses else 'FAIL'}")

        # Successes per topology
        for topo in TOPOLOGIES:
            successes = [r for r in db_rows
                         if r["topology_name"] == topo and r["success"] == 1]
            check(len(successes) > 0,
                  f"No successful embeddings for topology {topo!r}")
            print(f"  Successes in {topo}: {len(successes)}")

        # embeddings table populated
        n_emb = con.execute("SELECT COUNT(*) FROM embeddings").fetchone()[0]
        check(n_emb > 0, "embeddings table is empty")
        print(f"  embeddings table: {n_emb} row(s)")

        # graphs table populated
        n_graphs = con.execute("SELECT COUNT(*) FROM graphs").fetchone()[0]
        check(n_graphs == len(PROBLEMS), f"graphs table: expected {len(PROBLEMS)}, got {n_graphs}")
        print(f"  graphs table: {n_graphs} unique problem(s)")

        # batches table
        n_batches = con.execute("SELECT COUNT(*) FROM batches").fetchone()[0]
        check(n_batches == 1, f"batches table: expected 1 row, got {n_batches}")
        print(f"  batches table: {n_batches} batch row(s)")

        con.close()

    # ── CHECK 4: config.json content ─────────────────────────────────────────

    section("CHECK 4: config.json content")

    if config_json.exists():
        with open(config_json) as fh:
            cfg = json.load(fh)

        check("algorithms"  in cfg, "config.json missing 'algorithms'")
        check("topologies"  in cfg, "config.json missing 'topologies'")
        check("n_trials"    in cfg, "config.json missing 'n_trials'")
        check("timeout"     in cfg, "config.json missing 'timeout'")
        provenance = cfg.get("provenance", {})
        check("qebench_version" in provenance,
              "config.json missing provenance.qebench_version")
        check(set(cfg.get("algorithms", [])) == set(METHODS),
              f"config algorithms mismatch: {cfg.get('algorithms')} vs {METHODS}")
        print(f"  qebench_version: {provenance.get('qebench_version', '?')}")
        print(f"  algorithms:      {cfg.get('algorithms')}")
        print(f"  topologies:      {cfg.get('topologies')}")

    # ── CHECK 5: BenchmarkAnalysis.generate_report() ─────────────────────────

    section("CHECK 5: BenchmarkAnalysis.generate_report()")

    report_dir = None
    try:
        from qeanalysis import BenchmarkAnalysis
        an = BenchmarkAnalysis(batch_dir, output_root=str(analysis_root))
        report_dir = an.generate_report(fmt="png")
        check(True, "generate_report() raised an exception")
        print(f"  Report written to: {report_dir}")
    except Exception as e:
        check(False, f"generate_report() raised: {e}")
        print(f"  ERROR: {e}")

    # ── CHECK 6: Expected output files exist ──────────────────────────────────

    section("CHECK 6: Analysis output files")

    if report_dir is not None:
        figures_dir   = Path(report_dir) / "figures"
        summary_dir   = Path(report_dir) / "summary"
        statistics_dir = Path(report_dir) / "statistics"

        check(figures_dir.is_dir(),    f"figures/ not created: {figures_dir}")
        check(summary_dir.is_dir(),    f"summary/ not created: {summary_dir}")
        check(statistics_dir.is_dir(), f"statistics/ not created: {statistics_dir}")

        for fname in EXPECTED_FIGURES:
            p = figures_dir / fname
            check(p.exists(), f"Missing figure: {fname}")
            print(f"  {'✓' if p.exists() else '✗'}  figures/{fname}")

        for fname in EXPECTED_TABLES:
            p = summary_dir / fname
            check(p.exists(), f"Missing table: {fname}")
            print(f"  {'✓' if p.exists() else '✗'}  summary/{fname}")

        for fname in EXPECTED_STATS:
            p = statistics_dir / fname
            check(p.exists(), f"Missing stat output: {fname}")
            print(f"  {'✓' if p.exists() else '✗'}  statistics/{fname}")

        report_md = Path(report_dir) / "report.md"
        check(report_md.exists(), "report.md not written by generate_report()")
        print(f"  {'✓' if report_md.exists() else '✗'}  report.md")

    # ── CHECK 7: Reference snapshot comparison ────────────────────────────────

    section("CHECK 7: Reference snapshot comparison")

    if db_path.exists():
        new_rows = _read_compare_rows_from_db(db_path)

        if UPDATE_REFERENCE:
            # ── UPDATE MODE: save the current run as the new reference ────────
            REFERENCE_DIR.mkdir(parents=True, exist_ok=True)
            if new_rows:
                cols = list(new_rows[0].keys())
                with open(REFERENCE_CSV, "w", newline="") as fh:
                    writer = csv.DictWriter(fh, fieldnames=cols)
                    writer.writeheader()
                    writer.writerows(new_rows)
            print(f"  Reference snapshot UPDATED → {REFERENCE_CSV}")
            print(f"  ({len(new_rows)} rows, {len(COMPARE_COLS)} columns)")
            check(True, "")  # always pass when updating

        elif not REFERENCE_CSV.exists():
            # ── FIRST RUN: no reference yet ───────────────────────────────────
            print(f"  No reference snapshot found at {REFERENCE_CSV}")
            print(f"  Re-run with UPDATE_REFERENCE=1 to create it.")
            check(True, "")

        else:
            # ── COMPARISON MODE ───────────────────────────────────────────────
            ref_rows = _read_compare_rows_from_csv(REFERENCE_CSV)

            row_count_ok = len(new_rows) == len(ref_rows)
            check(row_count_ok,
                  f"Reference row count mismatch: got {len(new_rows)}, expected {len(ref_rows)}")
            print(f"  Row count: {len(new_rows)} vs reference {len(ref_rows)} "
                  f"{'✓' if row_count_ok else '✗'}")

            if row_count_ok:
                diffs = []
                for i, (new, ref) in enumerate(zip(new_rows, ref_rows)):
                    row_id = (new.get("topology_name", "?"),
                              new.get("algorithm", "?"),
                              new.get("problem_name", "?"),
                              new.get("trial", "?"))
                    for col in COMPARE_COLS:
                        if col not in new or col not in ref:
                            continue
                        if new[col] != ref[col]:
                            diffs.append(
                                f"row {i} {row_id} col={col!r}: "
                                f"got {new[col]!r}, expected {ref[col]!r}"
                            )
                check(not diffs,
                      f"Reference mismatch ({len(diffs)} field(s) differ)")
                if diffs:
                    print(f"  REGRESSION — {len(diffs)} field(s) differ:")
                    for d in diffs[:10]:
                        print(f"    ✗ {d}")
                    if len(diffs) > 10:
                        print(f"    … and {len(diffs) - 10} more")
                    print(f"\n  To accept these changes as the new baseline:")
                    print(f"    UPDATE_REFERENCE=1 conda run -n minor python {Path(__file__).name}")
                else:
                    print(f"  All {len(new_rows)} rows match reference snapshot ✓")


# ── Summary ───────────────────────────────────────────────────────────────────

print(f"\n{'=' * 70}")
total = passed + failed
print(f"RESULT: {passed}/{total} checks passed")

if issues:
    print(f"\nFAILURES ({len(issues)}):")
    for i in issues:
        if i:
            print(f"  ✗ {i}")
else:
    print("All checks passed — full pipeline smoke verified.")

print("=" * 70)

sys.exit(0 if failed == 0 else 1)
