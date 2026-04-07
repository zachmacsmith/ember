"""
ember_qc_analysis/summary.py
============================
Aggregate table computations for benchmarking results.

All functions accept the derived DataFrame produced by ember_qc_analysis.loader.load_batch()
and return a tidy pandas DataFrame ready for display or export.

Quality metrics (chain length, timing, qubit counts) are always computed on
*successful* trials only.  Success/validity *rates* are computed on all trials.
"""

import numpy as np
import pandas as pd
from typing import Optional


# ── Helpers ─────────────────────────────────────────────────────────────────────

def _cv(series: pd.Series) -> float:
    """Coefficient of variation (std / mean). Returns NaN if mean is 0."""
    mu = series.mean()
    return float(series.std() / mu) if mu != 0 else float('nan')


# ── Public functions ─────────────────────────────────────────────────────────────

def overall_summary(df: pd.DataFrame) -> pd.DataFrame:
    """One summary row per algorithm across all problems and topologies.

    Returns a DataFrame with columns:
        algorithm, n_trials, n_success, success_rate, valid_rate,
        time_mean, time_std, time_median, cv_time,
        chain_mean, chain_std, chain_median,
        max_chain_mean, max_chain_std, qubits_mean, qubit_overhead_mean,
        coupler_overhead_mean

    Quality metrics (time_*, chain_*, ...) are over successful trials only.
    success_rate and valid_rate use all trials.
    """
    rows = []
    for algo, grp in df.groupby('algorithm'):
        n_total = len(grp)
        success_grp = grp[grp['success']]
        n_success = len(success_grp)

        row = {
            'algorithm': algo,
            'n_trials': n_total,
            'n_success': n_success,
            'success_rate': n_success / n_total if n_total > 0 else float('nan'),
            'valid_rate': float(grp['is_valid'].mean()),
        }

        if n_success > 0:
            row['time_mean']   = float(success_grp['wall_time'].mean())
            row['time_std']    = float(success_grp['wall_time'].std())
            row['time_median'] = float(success_grp['wall_time'].median())
            row['cv_time']     = _cv(success_grp['wall_time'])
            row['chain_mean']  = float(success_grp['avg_chain_length'].mean())
            row['chain_std']   = float(success_grp['avg_chain_length'].std())
            row['chain_median']= float(success_grp['avg_chain_length'].median())
            row['max_chain_mean'] = float(success_grp['max_chain_length'].mean())
            row['max_chain_std']  = float(success_grp['max_chain_length'].std())
            row['qubits_mean'] = float(success_grp['total_qubits_used'].mean())

            if 'qubit_overhead_ratio' in success_grp.columns:
                row['qubit_overhead_mean'] = float(
                    success_grp['qubit_overhead_ratio'].mean()
                )
            if 'coupler_overhead_ratio' in success_grp.columns:
                row['coupler_overhead_mean'] = float(
                    success_grp['coupler_overhead_ratio'].dropna().mean()
                )
        else:
            for col in ['time_mean', 'time_std', 'time_median', 'cv_time',
                        'chain_mean', 'chain_std', 'chain_median',
                        'max_chain_mean', 'max_chain_std', 'qubits_mean',
                        'qubit_overhead_mean', 'coupler_overhead_mean']:
                row[col] = float('nan')

        rows.append(row)

    return pd.DataFrame(rows).set_index('algorithm')


def summary_by_category(df: pd.DataFrame,
                         metric: str = 'avg_chain_length') -> pd.DataFrame:
    """Algorithm × graph-category matrix of mean `metric` (successful trials only).

    Args:
        df:     Derived DataFrame from load_batch().
        metric: Column name to aggregate (must exist in df).

    Returns:
        DataFrame indexed by algorithm, columns = sorted category names.
        NaN where no successful trials exist for that (algo, category) pair.
    """
    if metric not in df.columns:
        raise ValueError(f"metric '{metric}' not found in DataFrame columns.")

    success_df = df[df['success']].copy()
    pivot = (
        success_df
        .groupby(['algorithm', 'category'])[metric]
        .mean()
        .unstack(level='category')
    )
    return pivot


def rank_table(df: pd.DataFrame,
               metric: str = 'avg_chain_length',
               lower_is_better: bool = True) -> pd.DataFrame:
    """Mean rank of each algorithm per problem, aggregated across all problems.

    For each problem where ≥ 2 algorithms have at least one successful trial,
    algorithms are ranked 1 (best) to N (worst) by their mean metric across trials.
    Ranks are then averaged across all problems to give an overall ranking.

    Args:
        df:               Derived DataFrame from load_batch().
        metric:           Column name to rank by.
        lower_is_better:  If True (default), lower metric value → better rank.

    Returns:
        DataFrame with index = algorithm and columns:
            mean_rank, median_rank, std_rank, n_problems_ranked
        Sorted by mean_rank ascending.
    """
    if metric not in df.columns:
        raise ValueError(f"metric '{metric}' not found in DataFrame columns.")

    # Per-problem mean metric per algorithm (successful trials only)
    per_problem = (
        df[df['success']]
        .groupby(['algorithm', 'graph_name'])[metric]
        .mean()
        .unstack(level='algorithm')
    )

    # Only rank problems where ≥ 2 algorithms succeeded
    per_problem = per_problem.dropna(thresh=2)

    if per_problem.empty:
        return pd.DataFrame(columns=['mean_rank', 'median_rank', 'std_rank', 'n_problems_ranked'])

    # Rank across columns (algorithms) for each problem row
    ascending = lower_is_better
    ranks = per_problem.rank(axis=1, ascending=ascending, method='average')

    summary = pd.DataFrame({
        'mean_rank':        ranks.mean(),
        'median_rank':      ranks.median(),
        'std_rank':         ranks.std(),
        'n_problems_ranked': ranks.notna().sum(),
    })
    return summary.sort_values('mean_rank')
