"""
ember_qc_analysis/filters.py
============================
DataFrame filter utilities for analysis.

These are query concerns, not plotting concerns — filters are implemented
here so they can be tested independently and reused consistently across
plot functions and statistical analyses.
"""

import pandas as pd
from typing import List, Optional


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
