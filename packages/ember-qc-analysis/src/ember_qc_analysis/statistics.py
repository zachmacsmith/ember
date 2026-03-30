"""
ember_qc_analysis/statistics.py
================================
Statistical comparison functions for benchmarking results.

All functions accept the derived DataFrame from ember_qc_analysis.loader.load_batch().

Design for extensibility
-------------------------
Each analysis is a standalone function — to add a new test, just add a new
function here and call it from BenchmarkAnalysis or generate_report().
No registration or framework changes needed.
"""

import itertools
import warnings

import numpy as np
import pandas as pd
from scipy import stats
from typing import Dict, List, Optional, Tuple


# ── Helpers ─────────────────────────────────────────────────────────────────────

def _per_problem_means(df: pd.DataFrame, metric: str) -> pd.DataFrame:
    """Per-problem mean of `metric` for each algorithm (successful trials only).

    Returns a DataFrame indexed by problem_name, columns = algorithm names.
    NaN where an algorithm had no successful trial on that problem.
    """
    return (
        df[df['success']]
        .groupby(['algorithm', 'problem_name'])[metric]
        .mean()
        .unstack(level='algorithm')
    )


def _holm_bonferroni(p_values: List[float]) -> List[float]:
    """Apply Holm-Bonferroni correction to a list of p-values.

    Returns corrected p-values in the same order as the input.
    """
    n = len(p_values)
    if n == 0:
        return []
    indexed = sorted(enumerate(p_values), key=lambda x: x[1])
    corrected = [None] * n
    prev_corrected = 0.0
    for rank, (orig_idx, p) in enumerate(indexed):
        c = p * (n - rank)
        c = max(c, prev_corrected)   # monotonicity constraint
        c = min(c, 1.0)
        corrected[orig_idx] = c
        prev_corrected = c
    return corrected


def _rank_biserial(x: np.ndarray, y: np.ndarray) -> float:
    """Effect size for Wilcoxon signed-rank test (rank-biserial r).

    r = 1 - 2W / (n*(n+1)/2) where W is the smaller Wilcoxon statistic.
    Value in [-1, 1]; magnitude indicates practical significance.
    """
    n = len(x)
    if n == 0:
        return float('nan')
    differences = x - y
    differences = differences[differences != 0]
    if len(differences) == 0:
        return 0.0
    abs_d = np.abs(differences)
    ranks = stats.rankdata(abs_d)
    w_pos = np.sum(ranks[differences > 0])
    w_neg = np.sum(ranks[differences < 0])
    w_min = min(w_pos, w_neg)
    max_w = len(differences) * (len(differences) + 1) / 2
    return float(1 - 2 * w_min / max_w) if max_w > 0 else 0.0


# ── Win rate matrix ──────────────────────────────────────────────────────────────

def win_rate_matrix(df: pd.DataFrame,
                    metric: str = 'avg_chain_length',
                    lower_is_better: bool = True) -> pd.DataFrame:
    """N×N matrix of pairwise win rates between algorithms.

    Cell (A, B) = fraction of problems where algorithm A has a strictly
    better mean `metric` than algorithm B (on successful trials).
    Diagonal is NaN.

    Args:
        df:               Derived DataFrame from load_batch().
        metric:           Column to compare.
        lower_is_better:  If True, lower value → better.

    Returns:
        DataFrame with algorithm names as both index and columns.
        Values are fractions in [0, 1] (multiply by 100 for percentages).
    """
    per_problem = _per_problem_means(df, metric)
    algos = list(per_problem.columns)
    matrix = pd.DataFrame(np.nan, index=algos, columns=algos)

    for a, b in itertools.combinations(algos, 2):
        common = per_problem[[a, b]].dropna()
        if common.empty:
            continue
        if lower_is_better:
            a_wins = (common[a] < common[b]).sum()
        else:
            a_wins = (common[a] > common[b]).sum()
        total = len(common)
        matrix.loc[a, b] = a_wins / total
        matrix.loc[b, a] = (total - a_wins) / total

    return matrix


# ── Pairwise significance tests ──────────────────────────────────────────────────

def significance_tests(df: pd.DataFrame,
                        metric: str = 'avg_chain_length',
                        min_pairs: int = 5) -> pd.DataFrame:
    """Wilcoxon signed-rank test for all algorithm pairs on per-problem mean metric.

    For each pair (A, B), tests whether the median difference in `metric`
    across problems is significantly different from zero.

    Args:
        df:         Derived DataFrame from load_batch().
        metric:     Column to test.
        min_pairs:  Minimum number of paired observations to run the test.
                    Pairs with fewer observations are reported as NaN.

    Returns:
        DataFrame with one row per pair and columns:
            algo_a, algo_b, n_pairs,
            w_statistic, p_value,
            corrected_p (Holm-Bonferroni),
            significant (p < 0.05 after correction),
            effect_size (rank-biserial r)
    """
    per_problem = _per_problem_means(df, metric)
    algos = list(per_problem.columns)
    rows = []

    for a, b in itertools.combinations(algos, 2):
        common = per_problem[[a, b]].dropna()
        n = len(common)
        if n < min_pairs:
            rows.append({
                'algo_a': a, 'algo_b': b, 'n_pairs': n,
                'w_statistic': np.nan, 'p_value': np.nan,
                'effect_size': np.nan,
            })
            continue

        x = common[a].values
        y = common[b].values
        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            w_stat, p_val = stats.wilcoxon(x, y, alternative='two-sided')
        rows.append({
            'algo_a': a, 'algo_b': b, 'n_pairs': n,
            'w_statistic': float(w_stat), 'p_value': float(p_val),
            'effect_size': _rank_biserial(x, y),
        })

    if not rows:
        return pd.DataFrame(columns=[
            'algo_a', 'algo_b', 'n_pairs', 'w_statistic',
            'p_value', 'corrected_p', 'significant', 'effect_size'
        ])

    result = pd.DataFrame(rows)

    # Holm-Bonferroni correction on non-NaN p-values
    valid_mask = result['p_value'].notna()
    corrected = [np.nan] * len(result)
    if valid_mask.any():
        valid_p = result.loc[valid_mask, 'p_value'].tolist()
        corr_p = _holm_bonferroni(valid_p)
        for i, idx in enumerate(result[valid_mask].index):
            corrected[idx] = corr_p[i]
    result['corrected_p'] = corrected
    result['significant'] = result['corrected_p'].apply(
        lambda p: bool(p < 0.05) if not np.isnan(p) else False
    )

    return result.reset_index(drop=True)


# ── Friedman test ────────────────────────────────────────────────────────────────

def friedman_test(df: pd.DataFrame,
                  metric: str = 'avg_chain_length') -> Dict:
    """Friedman test across all algorithms simultaneously (non-parametric ANOVA).

    Tests whether at least one algorithm differs significantly in `metric`
    from the others.  Requires ≥ 3 algorithms and ≥ 3 problems where all
    algorithms have a successful result.

    Args:
        df:     Derived DataFrame from load_batch().
        metric: Column to test.

    Returns:
        Dict with keys: statistic, p_value, significant, n_problems, n_algorithms,
        and 'error' (string) if the test could not be run.
    """
    per_problem = _per_problem_means(df, metric)
    complete = per_problem.dropna()  # only problems where all algos succeeded

    n_algos = complete.shape[1]
    n_problems = complete.shape[0]

    if n_algos < 3:
        return {'error': f'Need ≥ 3 algorithms; got {n_algos}.', 'n_algorithms': n_algos}
    if n_problems < 3:
        return {'error': f'Need ≥ 3 complete problems; got {n_problems}.', 'n_problems': n_problems}

    groups = [complete[col].values for col in complete.columns]
    stat, p_val = stats.friedmanchisquare(*groups)

    return {
        'statistic': float(stat),
        'p_value': float(p_val),
        'significant': bool(p_val < 0.05),
        'n_problems': n_problems,
        'n_algorithms': n_algos,
    }


# ── Correlation analysis ─────────────────────────────────────────────────────────

def correlation_matrix(df: pd.DataFrame,
                        graph_props: Optional[List[str]] = None,
                        embed_metrics: Optional[List[str]] = None,
                        method: str = 'spearman') -> pd.DataFrame:
    """Spearman (or Pearson) correlation between graph properties and embedding metrics.

    Computed on successful trials only.  Returns a (graph_props × embed_metrics)
    DataFrame of correlation coefficients.

    Args:
        df:            Derived DataFrame from load_batch().
        graph_props:   Columns to use as predictors (rows of the output matrix).
        embed_metrics: Columns to use as outcomes (columns of the output matrix).
        method:        'spearman' (default, non-parametric) or 'pearson'.

    Returns:
        DataFrame of shape (len(graph_props), len(embed_metrics)) with correlation
        coefficients.  NaN where a column has zero variance.
    """
    if graph_props is None:
        graph_props = ['problem_nodes', 'problem_edges', 'problem_density']
    if embed_metrics is None:
        embed_metrics = [
            'wall_time', 'avg_chain_length',
            'max_chain_length', 'total_qubits_used'
        ]

    success_df = df[df['success']].copy()

    # Filter to columns that exist
    graph_props  = [c for c in graph_props  if c in success_df.columns]
    embed_metrics = [c for c in embed_metrics if c in success_df.columns]

    if not graph_props or not embed_metrics:
        return pd.DataFrame()

    corr_fn = stats.spearmanr if method == 'spearman' else stats.pearsonr

    data = {}
    for em in embed_metrics:
        row = {}
        for gp in graph_props:
            x = success_df[gp].dropna()
            y = success_df[em].dropna()
            common_idx = x.index.intersection(y.index)
            x_c = x.loc[common_idx]
            y_c = y.loc[common_idx]
            if len(common_idx) < 3 or x_c.std() == 0 or y_c.std() == 0:
                # Correlation is undefined when either input is constant or
                # there are too few points — return NaN rather than letting
                # scipy emit a ConstantInputWarning.
                row[gp] = np.nan
            else:
                # Use [0] rather than tuple unpacking: scipy >= 1.9 returns a
                # named result object (SpearmanrResult / PearsonRResult) for
                # the 2-variable case; [0] is the correlation coefficient on
                # both old and new scipy without relying on __iter__ semantics.
                r = corr_fn(x_c, y_c)[0]
                row[gp] = float(r)
        data[em] = row

    # data is {embed_metric: {graph_prop: r_value}}
    # pd.DataFrame(data) → columns = embed_metrics, index = graph_props
    # → shape (len(graph_props) × len(embed_metrics)) as documented
    result = pd.DataFrame(data, index=graph_props)
    return result


# ── Density-hardness summary ─────────────────────────────────────────────────────

def density_hardness_summary(df: pd.DataFrame,
                              metric: str = 'avg_chain_length') -> pd.DataFrame:
    """Mean `metric` grouped by (algorithm, problem_density) for random graphs.

    Useful for plotting how embedding difficulty grows with graph density.
    Only considers graphs in the 'random' category.

    Returns:
        DataFrame with columns: algorithm, problem_density, problem_nodes,
        metric_mean, metric_std, n_trials.
        Sorted by algorithm, then problem_nodes, then problem_density.
    """
    rand_df = df[(df['category'] == 'random') & df['success']].copy()
    if rand_df.empty:
        return pd.DataFrame(columns=['algorithm', 'problem_density',
                                     'problem_nodes', f'{metric}_mean',
                                     f'{metric}_std', 'n_trials'])

    grouped = rand_df.groupby(['algorithm', 'problem_nodes', 'problem_density'])[metric]
    result = grouped.agg(
        metric_mean='mean',
        metric_std='std',
        n_trials='count'
    ).reset_index()
    result = result.rename(columns={'metric_mean': f'{metric}_mean',
                                    'metric_std':  f'{metric}_std'})
    return result.sort_values(['algorithm', 'problem_nodes', 'problem_density'])
