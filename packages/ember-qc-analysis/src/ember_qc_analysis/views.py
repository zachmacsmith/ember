"""
ember_qc_analysis/views.py
===========================
Load and combine data from multiple batches with per-source filters.

A **view** is a YAML file that describes which batches to load and how to
filter each one.  The result is a single concatenated DataFrame ready for
the standard analysis pipeline (plots, tables, statistics).

Example view YAML::

    name: Chimera fault-rate comparison
    sources:
      - batch: batch_2026-04-10_19-18-24
        filters:
          algorithm: [minorminer, pssa]
          base_topology: chimera_16x16x4
      - batch: batch_2026-04-09_12-00-00
        filters:
          algorithm: [OCT, ATOM]
          category: ["!complete", "!petersen"]
          graph_id: 1-500

    output_name: chimera_fault_comparison   # optional, derived from 'name' if omitted
"""

import re
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import pandas as pd
import yaml

from ember_qc_analysis._config import resolve_input_dir
from ember_qc_analysis.loader import (
    _derive_columns,
    _validate_columns,
    _load_from_db,
)

# ── Filter parsing ────────────────────────────────────────────────────────────

# Range pattern: "1-500", "100-200"
_RANGE_RE = re.compile(r'^(\d+)-(\d+)$')


def _parse_filter_value(value: Any) -> Tuple[list, list]:
    """Parse a filter value into (include, exclude) lists.

    Handles:
      - scalar:  "minorminer"  → include=["minorminer"], exclude=[]
      - list:    ["OCT", "!ATOM"] → include=["OCT"], exclude=["ATOM"]
      - negation prefix "!" means exclude
    """
    if not isinstance(value, list):
        value = [value]
    include, exclude = [], []
    for v in value:
        s = str(v)
        if s.startswith('!'):
            exclude.append(s[1:])
        else:
            include.append(s)
    return include, exclude


def _parse_id_range(spec: str) -> Optional[Tuple[int, int]]:
    """Parse "100-500" into (100, 500), or None if not a range."""
    m = _RANGE_RE.match(spec.strip())
    if m:
        return int(m.group(1)), int(m.group(2))
    return None


def _build_where_clauses(
    filters: Dict[str, Any],
    existing_cols: set,
) -> Tuple[str, list]:
    """Convert a filter dict into a SQL WHERE fragment and parameter list.

    Supported filter keys map to runs table columns (or derived columns
    handled post-load).  The following are handled at the SQL level for
    efficiency:

      algorithm, topology_name, graph_name, graph_id, status, success,
      trial, seed

    Other keys (category, base_topology, fault_rate) are applied as
    pandas filters after loading + deriving columns.

    Returns:
        (where_fragment, params) — e.g. (" AND algorithm IN (?,?)", ["OCT", "ATOM"])
    """
    # Columns that exist in the DB and can be filtered via SQL
    _SQL_FILTERABLE = {
        'algorithm', 'topology_name', 'graph_name', 'graph_id',
        'status', 'success', 'trial', 'seed',
    }

    clauses: list = []
    params: list = []

    for key, value in filters.items():
        if key not in _SQL_FILTERABLE:
            continue
        if key not in existing_cols:
            continue

        # Special case: graph_id range like "1-500"
        if key == 'graph_id' and isinstance(value, str):
            rng = _parse_id_range(value)
            if rng:
                clauses.append(f"{key} BETWEEN ? AND ?")
                params.extend(rng)
                continue

        include, exclude = _parse_filter_value(value)

        if include:
            placeholders = ','.join('?' * len(include))
            clauses.append(f"{key} IN ({placeholders})")
            params.extend(include)
        if exclude:
            placeholders = ','.join('?' * len(exclude))
            clauses.append(f"{key} NOT IN ({placeholders})")
            params.extend(exclude)

    where = (' AND '.join(clauses)) if clauses else ''
    return where, params


def _apply_post_load_filters(
    df: pd.DataFrame,
    filters: Dict[str, Any],
) -> pd.DataFrame:
    """Apply filters on derived columns (category, base_topology, fault_rate).

    These columns don't exist in the DB — they're computed by _derive_columns()
    after loading.  We apply them as pandas boolean masks.
    """
    _POST_LOAD_KEYS = {'category', 'base_topology', 'fault_rate'}

    for key in _POST_LOAD_KEYS:
        if key not in filters:
            continue
        if key not in df.columns:
            continue

        value = filters[key]

        # fault_rate: numeric comparison
        if key == 'fault_rate':
            if isinstance(value, (int, float)):
                df = df[df[key] == value]
            elif isinstance(value, list):
                df = df[df[key].isin([float(v) for v in value])]
            continue

        # graph_id range applied post-load (if it wasn't SQL-filterable)
        if key == 'graph_id' and isinstance(value, str):
            rng = _parse_id_range(value)
            if rng:
                df = df[(df[key] >= rng[0]) & (df[key] <= rng[1])]
                continue

        include, exclude = _parse_filter_value(value)
        if include:
            df = df[df[key].isin(include)]
        if exclude:
            df = df[~df[key].isin(exclude)]

    return df


# ── View loading ──────────────────────────────────────────────────────────────

def _resolve_batch_path(batch_spec: str, input_dir: Optional[Path] = None) -> Path:
    """Resolve a batch specifier to a directory path.

    Accepted forms:
      1. Absolute or relative path that exists.
      2. Directory name inside input_dir.
      3. Unique prefix match against batch names in input_dir.
    """
    p = Path(batch_spec).expanduser()
    if p.exists():
        return p.resolve()

    if input_dir is None:
        input_dir = resolve_input_dir(prompt=False)
    if input_dir is None:
        raise FileNotFoundError(
            f"Cannot resolve batch '{batch_spec}': no input_dir configured. "
            "Set it with: ember-a config set input_dir /path/to/results"
        )

    # Exact name
    exact = input_dir / batch_spec
    if exact.exists():
        return exact.resolve()

    # Prefix match
    candidates = [d for d in input_dir.iterdir() if d.is_dir() and d.name.startswith(batch_spec)]
    if len(candidates) == 1:
        return candidates[0].resolve()
    if len(candidates) > 1:
        raise ValueError(
            f"Ambiguous batch spec '{batch_spec}' matches {len(candidates)} "
            f"batches: {', '.join(c.name for c in candidates[:5])}"
        )

    raise FileNotFoundError(
        f"Batch not found: '{batch_spec}' (searched in {input_dir})"
    )


def _load_source(
    source: dict,
    input_dir: Optional[Path] = None,
) -> Tuple[pd.DataFrame, dict]:
    """Load a single source entry from a view YAML.

    Returns (filtered_df, config_dict).
    """
    batch_spec = source['batch']
    filters = source.get('filters', {})
    batch_dir = _resolve_batch_path(batch_spec, input_dir)
    batch_id = batch_dir.name

    db_path = batch_dir / 'results.db'
    runs_csv = batch_dir / 'runs.csv'

    # Load config
    config = {}
    config_json = batch_dir / 'config.json'
    if config_json.exists():
        import json
        with open(config_json) as f:
            config = json.load(f)

    # Load runs with SQL-level filtering where possible
    if db_path.exists():
        con = sqlite3.connect(db_path)
        existing_cols = {row[1] for row in con.execute("PRAGMA table_info(runs)")}

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
        select_cols = [c for c in _DESIRED_COLS if c in existing_cols]
        cols_sql = ', '.join(select_cols)

        # Build WHERE with batch_id + user filters
        where_parts = ['batch_id = ?']
        params: list = [batch_id]

        user_where, user_params = _build_where_clauses(filters, existing_cols)
        if user_where:
            where_parts.append(user_where)
            params.extend(user_params)

        where_sql = ' AND '.join(where_parts)
        query = f"SELECT {cols_sql} FROM runs WHERE {where_sql} ORDER BY topology_name, algorithm, graph_id, trial"

        df = pd.read_sql_query(query, con, params=params)
        con.close()

        # Bool coercion
        for col in ('success', 'is_valid', 'partial'):
            if col in df.columns:
                df[col] = df[col].apply(lambda x: bool(x) if pd.notna(x) else None)

    elif runs_csv.exists():
        # Legacy CSV fallback — no SQL filtering, filter in pandas
        df = pd.read_csv(runs_csv)
        for col in ('success', 'is_valid'):
            if col in df.columns:
                df[col] = df[col].astype(bool)
    else:
        raise FileNotFoundError(
            f"No results.db or runs.csv in {batch_dir}"
        )

    # Backward compat
    if 'graph_name' not in df.columns and 'problem_name' in df.columns:
        df = df.rename(columns={'problem_name': 'graph_name'})
    if 'graph_id' not in df.columns:
        df['graph_id'] = 0

    # Derive columns (category, base_topology, fault_rate, etc.)
    timeout = float(config.get('timeout', 60.0))
    df = _derive_columns(df, timeout=timeout)

    # Apply post-load filters (category, base_topology, fault_rate)
    df = _apply_post_load_filters(df, filters)

    # Tag source batch for provenance
    df['source_batch'] = batch_id

    return df, config


def load_view(
    yaml_path: Union[str, Path],
    input_dir: Optional[Path] = None,
) -> Tuple[pd.DataFrame, dict]:
    """Load a view YAML file, returning a combined DataFrame and merged config.

    Args:
        yaml_path: Path to the view YAML file.
        input_dir: Base directory to resolve batch names.  If None, uses
                   the configured analysis input_dir.

    Returns:
        (df, view_config) where df is the concatenated, filtered DataFrame
        from all sources, and view_config is the parsed view YAML dict
        (including name, output_name, and source metadata).

    Raises:
        FileNotFoundError: if the YAML file or any referenced batch is missing.
        ValueError: if the YAML is malformed or all filters produce empty data.
    """
    yaml_path = Path(yaml_path)
    if not yaml_path.exists():
        raise FileNotFoundError(f"View file not found: {yaml_path}")

    with open(yaml_path) as f:
        view = yaml.safe_load(f)

    if not isinstance(view, dict):
        raise ValueError(f"View YAML must be a mapping, got {type(view).__name__}")

    sources = view.get('sources')
    if not sources or not isinstance(sources, list):
        raise ValueError("View YAML must have a 'sources' list with at least one entry")

    # Derive output_name
    if 'output_name' not in view:
        name = view.get('name', yaml_path.stem)
        # Slugify: lowercase, replace non-alnum with underscore
        view['output_name'] = re.sub(r'[^a-z0-9]+', '_', name.lower()).strip('_')

    # Load each source
    frames = []
    configs = []
    for i, source in enumerate(sources):
        if 'batch' not in source:
            raise ValueError(f"Source #{i+1} missing 'batch' key")
        try:
            df, cfg = _load_source(source, input_dir=input_dir)
        except FileNotFoundError as e:
            raise FileNotFoundError(f"Source #{i+1}: {e}") from e
        frames.append(df)
        configs.append(cfg)

    if not frames:
        raise ValueError("No data loaded from any source")

    combined = pd.concat(frames, ignore_index=True)

    if combined.empty:
        raise ValueError(
            "All sources produced empty DataFrames after filtering. "
            "Check your filter specifications."
        )

    # Validate schema
    _validate_columns(combined)

    # Merge configs: use first source's config as base, note multi-batch
    merged_config = dict(configs[0]) if configs else {}
    merged_config['_view'] = {
        'name': view.get('name', yaml_path.stem),
        'output_name': view['output_name'],
        'yaml_path': str(yaml_path),
        'n_sources': len(sources),
        'source_batches': [s['batch'] for s in sources],
    }
    # Aggregate timeout as max across sources
    if len(configs) > 1:
        merged_config['timeout'] = max(
            float(c.get('timeout', 60.0)) for c in configs
        )

    return combined, merged_config
