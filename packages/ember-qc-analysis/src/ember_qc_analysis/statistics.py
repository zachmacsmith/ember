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

    Returns a DataFrame indexed by graph_name, columns = algorithm names.
    NaN where an algorithm had no successful trial on that problem.
    """
    return (
        df[df['success']]
        .groupby(['algorithm', 'graph_name'])[metric]
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


def _log10_p_wilcoxon(x: np.ndarray, y: np.ndarray) -> float:
    """Compute log₁₀(p) for a two-sided Wilcoxon signed-rank test.

    Uses the normal approximation (valid for n ≥ 10) to avoid the
    machine-epsilon floor that makes p appear as exactly 0.0.
    Returns a negative number (e.g. -287.4 means p ≈ 10⁻²⁸⁷·⁴).
    """
    differences = x - y
    differences = differences[differences != 0]
    n = len(differences)
    if n == 0:
        return 0.0

    abs_d = np.abs(differences)
    ranks = stats.rankdata(abs_d)
    w_pos = np.sum(ranks[differences > 0])

    # Expected value and variance under H₀
    mean_w = n * (n + 1) / 4
    # Correction for ties
    unique_ranks, counts = np.unique(ranks, return_counts=True)
    tie_correction = np.sum(counts ** 3 - counts) / 48
    var_w = n * (n + 1) * (2 * n + 1) / 24 - tie_correction

    if var_w <= 0:
        return 0.0

    z = (w_pos - mean_w) / np.sqrt(var_w)
    # Two-sided: log₁₀(2) + log₁₀(SF(|z|))
    # logsf returns ln(SF), convert to log₁₀
    log10_one_tail = stats.norm.logsf(abs(z)) / np.log(10)
    log10_p = np.log10(2) + log10_one_tail
    return float(log10_p)


def _log10_p_chi2(statistic: float, df: int) -> float:
    """Compute log₁₀(p) for a chi-squared test statistic.

    Uses logsf first; if that underflows to -inf, falls back to an
    asymptotic upper-tail approximation:
        log SF(x, k) ≈ -(x - k)/2 * ln(2) - (k/2)*ln(x/k) + ...
    which remains finite for arbitrarily large x.
    """
    if df <= 0 or statistic <= 0:
        return 0.0
    log_p_ln = stats.chi2.logsf(statistic, df)  # natural log
    if np.isfinite(log_p_ln):
        return float(log_p_ln / np.log(10))

    # Asymptotic approximation for extreme chi-squared values.
    # For large x, the chi-squared SF ≈ pdf(x,k) * x / (x - k + 2)
    # where log pdf(x,k) = (k/2-1)*ln(x) - x/2 - (k/2)*ln(2) - gammaln(k/2)
    from scipy.special import gammaln
    k = df
    log_pdf = ((k / 2 - 1) * np.log(statistic)
               - statistic / 2
               - (k / 2) * np.log(2)
               - gammaln(k / 2))
    # SF ≈ pdf * x / (x - k + 2) for large x
    correction = np.log(statistic) - np.log(max(statistic - k + 2, 1))
    log_sf_ln = log_pdf + correction
    return float(log_sf_ln / np.log(10))


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

    Cell (A, B) = fraction of problems where algorithm A beats algorithm B.
    A win is: A succeeded and B failed, OR both succeeded and A has a
    strictly better ``metric`` value.  Ties (both succeed with equal metric)
    count for neither.  Diagonal is NaN.

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
        pair = per_problem[[a, b]]
        # Consider graphs where at least one algorithm has data
        present = pair[pair[a].notna() | pair[b].notna()]
        if present.empty:
            continue

        a_has = present[a].notna()
        b_has = present[b].notna()

        # One succeeded, the other failed → automatic win
        a_only = (a_has & ~b_has).sum()
        b_only = (~a_has & b_has).sum()

        # Both succeeded → compare metric values
        both_ok = present[a_has & b_has]
        if lower_is_better:
            a_better = (both_ok[a] < both_ok[b]).sum()
            b_better = (both_ok[a] > both_ok[b]).sum()
        else:
            a_better = (both_ok[a] > both_ok[b]).sum()
            b_better = (both_ok[a] < both_ok[b]).sum()

        a_wins = a_only + a_better
        b_wins = b_only + b_better
        total = len(present)
        if total == 0:
            continue
        matrix.loc[a, b] = a_wins / total
        matrix.loc[b, a] = b_wins / total

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
            median_a, median_b, median_diff,
            direction (which algorithm is better),
            w_statistic, p_value,
            corrected_p (Holm-Bonferroni),
            significant_005, significant_001, significant_0001,
            effect_size (rank-biserial r),
            effect_magnitude (negligible/small/medium/large)
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
                'median_a': np.nan, 'median_b': np.nan, 'median_diff': np.nan,
                'direction': '',
                'w_statistic': np.nan, 'p_value': np.nan,
                'log10_p': np.nan,
                'effect_size': np.nan,
            })
            continue

        x = common[a].values
        y = common[b].values
        med_a = float(np.median(x))
        med_b = float(np.median(y))
        med_diff = med_a - med_b

        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            w_stat, p_val = stats.wilcoxon(x, y, alternative='two-sided')

        # Log₁₀(p) via normal approximation — avoids underflow to 0
        log10_p = _log10_p_wilcoxon(x, y)

        # Direction: which is better (lower metric = better by default)
        if med_diff < 0:
            direction = f'{a} < {b}'
        elif med_diff > 0:
            direction = f'{a} > {b}'
        else:
            direction = 'equal'

        rows.append({
            'algo_a': a, 'algo_b': b, 'n_pairs': n,
            'median_a': med_a, 'median_b': med_b, 'median_diff': med_diff,
            'direction': direction,
            'w_statistic': float(w_stat), 'p_value': float(p_val),
            'log10_p': log10_p,
            'effect_size': _rank_biserial(x, y),
        })

    if not rows:
        return pd.DataFrame(columns=[
            'algo_a', 'algo_b', 'n_pairs',
            'median_a', 'median_b', 'median_diff', 'direction',
            'w_statistic', 'p_value',
            'corrected_p', 'significant_005', 'significant_001', 'significant_0001',
            'effect_size', 'effect_magnitude',
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
    result['significant_005'] = result['corrected_p'].apply(
        lambda p: bool(p < 0.05) if pd.notna(p) else False
    )
    result['significant_001'] = result['corrected_p'].apply(
        lambda p: bool(p < 0.01) if pd.notna(p) else False
    )
    result['significant_0001'] = result['corrected_p'].apply(
        lambda p: bool(p < 0.001) if pd.notna(p) else False
    )

    # Effect magnitude labels
    def _magnitude(r):
        if pd.isna(r):
            return ''
        r = abs(r)
        if r < 0.1:
            return 'negligible'
        elif r < 0.3:
            return 'small'
        elif r < 0.5:
            return 'medium'
        else:
            return 'large'

    result['effect_magnitude'] = result['effect_size'].apply(_magnitude)

    return result.reset_index(drop=True)


# ── Friedman test ────────────────────────────────────────────────────────────────

def friedman_test(df: pd.DataFrame,
                  metric: str = 'avg_chain_length') -> Dict:
    """Friedman test across all algorithms simultaneously (non-parametric ANOVA).

    Tests whether at least one algorithm differs significantly in `metric`
    from the others.  Requires ≥ 3 algorithms and ≥ 3 problems where all
    algorithms have a successful result.

    Includes Kendall's W effect size, per-algorithm mean ranks, and
    post-hoc Nemenyi critical difference.

    Args:
        df:     Derived DataFrame from load_batch().
        metric: Column to test.

    Returns:
        Dict with keys:
            statistic, p_value, significant_005, significant_001,
            n_problems, n_algorithms,
            kendalls_w (effect size: 0=no agreement, 1=complete agreement),
            mean_ranks (dict of algo → mean rank; rank 1 = best),
            rank_order (list of algos sorted best to worst),
            nemenyi_cd (critical difference for α=0.05, NaN if unavailable),
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

    # Log₁₀(p) via chi-squared survival function — avoids underflow to 0
    log10_p = _log10_p_chi2(float(stat), n_algos - 1)

    # ── Mean ranks (rank 1 = best = lowest metric value) ─────────────────
    rank_matrix = complete.rank(axis=1, method='average')
    mean_ranks = rank_matrix.mean(axis=0).to_dict()
    rank_order = sorted(mean_ranks, key=mean_ranks.get)

    # ── Kendall's W (coefficient of concordance) ─────────────────────────
    # W = χ² / (n * (k-1))  where χ² is Friedman statistic
    kendalls_w = float(stat) / (n_problems * (n_algos - 1)) if n_problems > 0 else np.nan

    # ── Nemenyi critical difference for post-hoc comparison ──────────────
    # CD = q_α * sqrt(k*(k+1) / (6*n))
    # q_α values from Studentized Range table for α=0.05
    # For k algorithms, use q_α(k, ∞)
    _q_alpha_005 = {
        3: 2.343, 4: 2.569, 5: 2.728, 6: 2.850, 7: 2.949,
        8: 3.031, 9: 3.102, 10: 3.164, 11: 3.219, 12: 3.268,
    }
    q_val = _q_alpha_005.get(n_algos, np.nan)
    nemenyi_cd = q_val * np.sqrt(n_algos * (n_algos + 1) / (6 * n_problems)) if not np.isnan(q_val) else np.nan

    return {
        'statistic': float(stat),
        'p_value': float(p_val),
        'log10_p': log10_p,
        'significant_005': bool(p_val < 0.05),
        'significant_001': bool(p_val < 0.01),
        'significant_0001': bool(p_val < 0.001),
        'n_problems': n_problems,
        'n_algorithms': n_algos,
        'kendalls_w': kendalls_w,
        'mean_ranks': {k: round(v, 6) for k, v in mean_ranks.items()},
        'rank_order': rank_order,
        'nemenyi_cd': float(nemenyi_cd) if not np.isnan(nemenyi_cd) else None,
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
