"""
ember_qc_analysis/filters.py
============================
DataFrame filter utilities for analysis.

These are query concerns, not plotting concerns — filters are implemented
here so they can be tested independently and reused consistently across
plot functions and statistical analyses.
"""

import re
import pandas as pd
from typing import List, Optional, Set, Tuple


# ── Graph category constants ─────────────────────────────────────────────────

# Kept for backward compatibility — code that imports VALID_CATEGORIES still
# works.  Validation in apply_graph_filter now uses the actual categories
# present in the DataFrame rather than this static set, so runs with any of
# the 36 manifest graph families are handled automatically.
VALID_CATEGORIES = frozenset({
    'complete', 'bipartite', 'grid', 'cycle', 'path', 'star', 'wheel',
    'tree', 'binary_tree', 'random', 'random_er', 'random_planar',
    'barabasi_albert', 'watts_strogatz', 'regular', 'sbm', 'lfr_benchmark',
    'planted_solution', 'weak_strong_cluster', 'circulant', 'hypercube',
    'johnson', 'kneser', 'turan', 'generalized_petersen',
    'honeycomb', 'triangular_lattice', 'kagome', 'frustrated_square',
    'king_graph', 'cubic_lattice', 'bcc_lattice', 'shastry_sutherland',
    'spin_glass', 'hardware_native', 'sudoku', 'special', 'other',
})


# ── Graph ID selection parsing ───────────────────────────────────────────────

def parse_graph_ids(spec: str) -> Set[int]:
    """Parse a graph selection string into a set of integer IDs.

    Tries to delegate to ``ember_qc.load_graphs.parse_graph_selection`` when
    ember-qc is installed, which enables named presets (e.g. ``"quick"``,
    ``"benchmark"``).  Falls back to a built-in parser for numeric specs.

    Supported syntax (built-in parser):
        ``"*"``         — wildcard; returns ``{-1}`` (sentinel for "all graphs")
        ``"5"``         — single ID
        ``"1-10"``      — inclusive range
        ``"1-10,!5"``   — range with exclusion
        ``"1,3,7-12"``  — comma-separated mix

    Args:
        spec: Selection string.

    Returns:
        Set of integer IDs.  ``{-1}`` is a sentinel meaning "no ID filter".

    Raises:
        ValueError: if a token cannot be parsed and ember-qc is not available
            to interpret it as a preset name.
    """
    spec = spec.strip()

    # Try ember-qc's full parser (supports presets, negation, *)
    try:
        from ember_qc.load_graphs import parse_graph_selection
        return parse_graph_selection(spec)
    except ImportError:
        pass  # ember-qc not installed — fall back to built-in parser
    except Exception as exc:
        raise ValueError(f"ember-qc could not parse graph spec {spec!r}: {exc}") from exc

    # Built-in parser — handles integers, ranges, exclusions, wildcard
    if spec == '*':
        return {-1}

    includes: Set[int] = set()
    excludes: Set[int] = set()

    for token in re.split(r'[,&]', spec):
        token = token.strip()
        if not token:
            continue
        exclude = token.startswith('!')
        if exclude:
            token = token[1:].strip()

        if '-' in token:
            parts = token.split('-', 1)
            try:
                lo, hi = int(parts[0]), int(parts[1])
            except ValueError:
                raise ValueError(
                    f"Cannot parse graph range {token!r}. "
                    "Use integers and ranges (e.g. '1-10'). "
                    "Preset names require ember-qc to be installed."
                ) from None
            rng = set(range(lo, hi + 1))
            (excludes if exclude else includes).update(rng)
        else:
            try:
                val = int(token)
            except ValueError:
                raise ValueError(
                    f"Cannot parse graph token {token!r}. "
                    "Use integers and ranges (e.g. '1-10'). "
                    "Preset names require ember-qc to be installed."
                ) from None
            (excludes if exclude else includes).add(val)

    return includes - excludes


def apply_graph_filter(
    df: pd.DataFrame,
    graphs: Optional[str] = None,
    graph_type: Optional[str] = None,
) -> Tuple[pd.DataFrame, str]:
    """Filter a runs DataFrame to a subset of graphs.

    Args:
        df:          Derived DataFrame from ``load_batch()``.
        graphs:      Graph selection string (e.g. ``"1-10"``, ``"1-60,!35"``,
                     ``"quick"``).  Preset names require ember-qc to be
                     installed.  ``"*"`` or ``None`` means no ID filter.
        graph_type:  Graph category name (e.g. ``"random"``, ``"bipartite"``).
                     See :data:`VALID_CATEGORIES` for the full list.

    Returns:
        ``(filtered_df, filter_slug)`` where ``filter_slug`` is a
        filesystem-safe string describing the active filter (empty string when
        no filter is applied).  The slug is used by ``BenchmarkAnalysis`` to
        route output into a named subdirectory.

    Raises:
        ValueError: for unknown graph IDs spec tokens or invalid category names.
    """
    filtered = df
    parts: List[str] = []

    # ── ID filter ─────────────────────────────────────────────────────────────
    if graphs:
        ids = parse_graph_ids(graphs)
        if ids != {-1}:   # {-1} is the wildcard sentinel — no filtering
            # Warn if the entire DataFrame uses graph_id=0 (pre-v1.1 batches)
            if 'graph_id' in filtered.columns and (filtered['graph_id'] == 0).all():
                import warnings
                warnings.warn(
                    "All rows have graph_id=0 (pre-v1.1 batch or custom-only run). "
                    "--graphs filter operates on graph_id and will remove all rows.",
                    stacklevel=2,
                )
            filtered = filtered[filtered['graph_id'].isin(ids)]
            # Build a readable slug (sanitise commas/spaces → underscores)
            slug_spec = re.sub(r'[,&\s]+', '_', graphs.strip()).strip('_')
            parts.append(f"graphs_{slug_spec}")

    # ── Category filter ───────────────────────────────────────────────────────
    if graph_type:
        cat = graph_type.lower()
        available = set(filtered['category'].unique()) if 'category' in filtered.columns else set()
        if cat not in available:
            raise ValueError(
                f"Graph type {graph_type!r} not found in this batch. "
                f"Types present: {', '.join(sorted(available))}"
            )
        filtered = filtered[filtered['category'] == cat]
        parts.append(f"type_{cat}")

    slug = '__'.join(parts)
    return filtered.copy(), slug


def shared_graph_filter(df: pd.DataFrame,
                        algorithms: Optional[List[str]] = None) -> pd.DataFrame:
    """Return rows where ALL specified algorithms have at least one success.

    For each graph (graph_name), checks whether every algorithm in
    `algorithms` has at least one successful trial.  Returns only the rows
    for graphs that pass this test — for all algorithms.

    Args:
        df:          DataFrame of runs (must contain 'algorithm',
                     'graph_name', 'success' columns).
        algorithms:  List of algorithm names to require.  If None or empty,
                     uses all algorithms present in df.

    Returns:
        Filtered DataFrame (subset of rows from df).  Empty if no graph
        has a successful trial for all specified algorithms.

    Example::

        # Only keep graphs where both minorminer and atom succeeded
        filtered = shared_graph_filter(df, ['minorminer', 'atom'])
    """
    if algorithms is None or len(algorithms) == 0:
        algorithms = df['algorithm'].unique().tolist()

    # For each graph: set of algorithms that have ≥1 success
    success_df = df[df['success']]
    algo_set = set(algorithms)

    graphs_with_all = (
        success_df[success_df['algorithm'].isin(algo_set)]
        .groupby('graph_name')['algorithm']
        .apply(lambda s: algo_set.issubset(set(s)))
    )

    qualifying_graphs = graphs_with_all[graphs_with_all].index.tolist()

    return df[df['graph_name'].isin(qualifying_graphs)].copy()
