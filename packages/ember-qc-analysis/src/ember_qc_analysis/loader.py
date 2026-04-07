"""
ember_qc_analysis/loader.py
============================
Load an ember-qc batch directory into a DataFrame ready for analysis.

Primary source: results.db (SQLite) — the authoritative store written by compile_batch().
Fallback:       runs.csv — for batches produced before the SQLite pipeline.

Adds derived columns not stored in the database:
  category              — graph family inferred from graph_name prefix
  qubit_overhead_ratio  — total_qubits_used / problem_nodes
  coupler_overhead_ratio — total_couplers_used / problem_edges
  max_to_avg_chain_ratio — max_chain_length / avg_chain_length
  is_timeout            — wall_time >= 0.95 * timeout (from config)
"""

import json
import sqlite3
import numpy as np
import pandas as pd
from pathlib import Path
from typing import Dict, Tuple


# ── Schema ─────────────────────────────────────────────────────────────────────

_REQUIRED_COLUMNS = frozenset({
    'algorithm', 'graph_id', 'graph_name', 'topology_name', 'trial',
    'success', 'is_valid', 'wall_time',
    'avg_chain_length', 'max_chain_length',
    'total_qubits_used', 'total_couplers_used',
    'problem_nodes', 'problem_edges', 'problem_density',
})

# Special-graph names (not prefix-detectable)
_SPECIAL_GRAPHS = frozenset({'petersen', 'dodecahedral', 'icosahedral'})


# ── Category inference ──────────────────────────────────────────────────────────

def infer_category(graph_name: str) -> str:
    """Return the graph category for a graph_name string.

    Rules (case-insensitive prefix match):
        K<digits>         → complete
        bipartite_*       → bipartite
        grid_*            → grid
        cycle_*           → cycle
        tree_*            → tree
        petersen / dodecahedral / icosahedral → special
        random_*          → random
        anything else     → other
    """
    name = graph_name.strip().lower()
    if name in _SPECIAL_GRAPHS:
        return 'special'
    if name.startswith('k') and len(name) > 1 and name[1:].isdigit():
        return 'complete'
    for prefix, category in [
        ('bipartite_', 'bipartite'),
        ('grid_',      'grid'),
        ('cycle_',     'cycle'),
        ('tree_',      'tree'),
        ('random_',    'random'),
    ]:
        if name.startswith(prefix):
            return category
    return 'other'


# ── Column derivation ───────────────────────────────────────────────────────────

def _derive_columns(df: pd.DataFrame, timeout: float = 60.0) -> pd.DataFrame:
    """Add computed columns to a runs DataFrame (modifies a copy)."""
    df = df.copy()

    # Category
    df['category'] = df['graph_name'].apply(infer_category)

    # Qubit overhead ratio
    df['qubit_overhead_ratio'] = np.where(
        df['problem_nodes'] > 0,
        df['total_qubits_used'] / df['problem_nodes'],
        np.nan
    )

    # Coupler overhead ratio
    df['coupler_overhead_ratio'] = np.where(
        df['problem_edges'] > 0,
        df['total_couplers_used'] / df['problem_edges'],
        np.nan
    )

    # Max-to-avg chain ratio
    df['max_to_avg_chain_ratio'] = np.where(
        df['avg_chain_length'] > 0,
        df['max_chain_length'] / df['avg_chain_length'],
        np.nan
    )

    # Timeout flag (allow 5% tolerance)
    df['is_timeout'] = df['wall_time'] >= (timeout * 0.95)

    return df


# ── Validation ──────────────────────────────────────────────────────────────────

def _validate_columns(df: pd.DataFrame) -> None:
    """Raise ValueError if required columns are missing."""
    missing = _REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise ValueError(
            f"Batch is missing required columns: {sorted(missing)}\n"
            f"Available columns: {sorted(df.columns.tolist())}"
        )


# ── SQLite loader ───────────────────────────────────────────────────────────────

def _load_from_db(db_path: Path, batch_id: str) -> pd.DataFrame:
    """Read all runs for batch_id from results.db into a DataFrame."""
    con = sqlite3.connect(db_path)

    # Enumerate the columns we want, in stable order.  Only select those that
    # actually exist in the table so the loader works with databases produced
    # by older ember-qc versions that predate some columns.
    _DESIRED_COLS = [
        'batch_id', 'algorithm', 'algorithm_version',
        'graph_id', 'graph_name', 'topology_name', 'trial', 'seed',
        'wall_time', 'cpu_time', 'status', 'success', 'is_valid', 'partial',
        'avg_chain_length', 'max_chain_length', 'chain_length_std',
        'total_qubits_used', 'total_couplers_used',
        'problem_nodes', 'problem_edges', 'problem_density',
        'target_node_visits', 'cost_function_evaluations',
        'embedding_state_mutations', 'overlap_qubit_iterations',
        'error', 'created_at',
    ]
    existing_cols = {row[1] for row in con.execute("PRAGMA table_info(runs)")}
    select_cols = [c for c in _DESIRED_COLS if c in existing_cols]
    cols_sql = ', '.join(select_cols)

    df = pd.read_sql_query(
        f"SELECT {cols_sql} FROM runs WHERE batch_id = ?"
        " ORDER BY topology_name, algorithm, graph_id, trial",
        con,
        params=(batch_id,),
    )
    con.close()

    # SQLite stores booleans as INTEGER (0/1) or NULL.
    # astype(bool) is unsafe: NaN (from NULL) converts to True.
    for col in ('success', 'is_valid', 'partial'):
        if col in df.columns:
            df[col] = df[col].apply(lambda x: bool(x) if pd.notna(x) else None)

    return df


def _load_config_from_db(db_path: Path, batch_id: str) -> Dict:
    """Read config_json from the batches table; return empty dict on failure."""
    try:
        con = sqlite3.connect(db_path)
        row = con.execute(
            "SELECT config_json FROM batches WHERE batch_id = ?", (batch_id,)
        ).fetchone()
        con.close()
        if row and row[0]:
            return json.loads(row[0])
    except Exception:
        pass
    return {}


# ── Public API ──────────────────────────────────────────────────────────────────

def load_batch(batch_dir) -> Tuple[pd.DataFrame, Dict]:
    """Load a qebench batch directory into a DataFrame + config dict.

    Reads from results.db (SQLite) if present; falls back to runs.csv for
    batches produced before the SQLite pipeline was introduced.

    Args:
        batch_dir: Path (str or Path) to a batch directory produced by
                   qebench.EmbeddingBenchmark.run_full_benchmark().

    Returns:
        (df, config) where df has all runs columns plus the derived columns
        (category, qubit_overhead_ratio, ...) and config is the parsed
        config.json dict (empty dict if file absent).

    Raises:
        FileNotFoundError: if batch_dir does not exist, or neither
                           results.db nor runs.csv is found.
        ValueError: if required columns are missing.
    """
    batch_dir = Path(batch_dir)
    if not batch_dir.exists():
        raise FileNotFoundError(f"Batch directory not found: {batch_dir}")

    batch_id = batch_dir.name

    # ── Load runs ──────────────────────────────────────────────────────────────
    db_path = batch_dir / 'results.db'
    runs_csv = batch_dir / 'runs.csv'

    if db_path.exists():
        df = _load_from_db(db_path, batch_id)
        # Config: prefer config.json (richer), fall back to batches table
        config_json = batch_dir / 'config.json'
        if config_json.exists():
            with open(config_json) as f:
                config = json.load(f)
        else:
            config = _load_config_from_db(db_path, batch_id)
    elif runs_csv.exists():
        df = pd.read_csv(runs_csv)
        for col in ('success', 'is_valid'):
            if col in df.columns:
                df[col] = df[col].astype(bool)
        config_json = batch_dir / 'config.json'
        config: Dict = {}
        if config_json.exists():
            with open(config_json) as f:
                config = json.load(f)
    else:
        raise FileNotFoundError(
            f"No results.db or runs.csv found in {batch_dir}"
        )

    # ── Backward compat: pre-v1.1.0 batches used 'problem_name' ───────────────
    if 'graph_name' not in df.columns and 'problem_name' in df.columns:
        df = df.rename(columns={'problem_name': 'graph_name'})
    if 'graph_id' not in df.columns:
        df['graph_id'] = 0

    # ── Validate schema ────────────────────────────────────────────────────────
    _validate_columns(df)

    # ── Derive computed columns ────────────────────────────────────────────────
    timeout = float(config.get('timeout', 60.0))
    df = _derive_columns(df, timeout=timeout)

    return df, config
