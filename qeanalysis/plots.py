"""
qeanalysis/plots.py
====================
All visualizations for qeanalysis.

Design principles
-----------------
- Every function accepts `df` (derived DataFrame from load_batch()) as first arg.
- All functions return the matplotlib Figure object so callers can further
  customise or test without file I/O.
- `save=False` by default; pass `save=True` and `output_dir` to write to disk.
- A single ALGO_PALETTE dict maps algorithm names → colours for consistency
  across all plots in the same report.

Adding new plots
----------------
Write a new standalone function following the same signature:

    def plot_my_analysis(df, ..., output_dir=None, save=False) -> plt.Figure:
        fig, ax = plt.subplots(...)
        # ... your code ...
        _maybe_save(fig, output_dir, "my_analysis.png", save)
        return fig

Then call it from BenchmarkAnalysis.generate_report() and add a method wrapper.
"""

import hashlib
import itertools
import warnings
from pathlib import Path
from typing import List, Optional

import matplotlib
matplotlib.use('Agg')   # non-interactive backend; safe in scripts and tests
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
import pandas as pd
import seaborn as sns


# ── Palette ─────────────────────────────────────────────────────────────────────

# Seaborn colorblind palette (6 safe colours). Extended with tab10 if >6 algos.
_CB_PALETTE = sns.color_palette('colorblind', 6)
_TAB10 = sns.color_palette('tab10', 10)
_MARKERS = ['o', 's', '^', 'D', 'v', '<', '>', 'p', '*', 'h']

def _algo_palette(algorithms) -> dict:
    """Return {algo_name: colour} using colorblind-safe palette."""
    algos = sorted(set(algorithms))
    palette = _CB_PALETTE if len(algos) <= 6 else _TAB10
    return {a: palette[i % len(palette)] for i, a in enumerate(algos)}

def _algo_markers(algorithms) -> dict:
    """Return {algo_name: marker} so plots are readable in greyscale."""
    algos = sorted(set(algorithms))
    return {a: _MARKERS[i % len(_MARKERS)] for i, a in enumerate(algos)}


def build_algo_palette(algorithms) -> dict:
    """Compute a consistent {algo: colour} mapping for a set of algorithms.

    Call once at report generation time and pass to all plot functions.
    """
    return _algo_palette(algorithms)


# ── Save helper ──────────────────────────────────────────────────────────────────

def _maybe_save(fig, output_dir, filename, save, subdir=None):
    if save and output_dir is not None:
        target = Path(output_dir) / subdir if subdir else Path(output_dir)
        target.mkdir(parents=True, exist_ok=True)
        fig.savefig(target / filename, dpi=150, bbox_inches='tight')
    plt.close(fig)


# ── 1. Category heatmap ─────────────────────────────────────────────────────────

def plot_heatmap(df: pd.DataFrame,
                 metric: str = 'avg_chain_length',
                 algo_palette=None,
                 output_dir=None,
                 save: bool = False) -> plt.Figure:
    """Heatmap: algorithm (rows) × graph category (columns), cell = mean metric.

    Only successful trials are included.
    """
    from qeanalysis.summary import summary_by_category
    pivot = summary_by_category(df, metric)

    if pivot.empty:
        fig, ax = plt.subplots()
        ax.text(0.5, 0.5, 'No data', ha='center', va='center')
        _maybe_save(fig, output_dir, f'{metric}_by_category.png', save,
                    subdir='figures/distributions')
        return fig

    fig, ax = plt.subplots(figsize=(max(6, pivot.shape[1] * 1.4),
                                    max(3, pivot.shape[0] * 0.9) + 1))
    sns.heatmap(
        pivot, ax=ax, annot=True, fmt='.2f',
        cmap='YlOrRd', linewidths=0.5, linecolor='white',
        cbar_kws={'label': metric.replace('_', ' ')}
    )
    ax.set_title(f'Mean {metric.replace("_", " ")} by algorithm and graph category')
    ax.set_xlabel('Graph category')
    ax.set_ylabel('Algorithm')
    plt.tight_layout()
    _maybe_save(fig, output_dir, f'{metric}_by_category.png', save,
                subdir='figures/distributions')
    return fig


# ── 2. Scaling plot ──────────────────────────────────────────────────────────────

def plot_scaling(df: pd.DataFrame,
                 metric: str = 'wall_time',
                 x: str = 'problem_nodes',
                 log: bool = False,
                 algo_palette=None,
                 output_dir=None,
                 save: bool = False) -> plt.Figure:
    """Line plot: metric vs x (aggregated across trials), one line per algorithm.

    Mean ± 1 std shaded ribbon.  Only successful trials included.
    """
    success_df = df[df['success']].copy()
    if success_df.empty:
        fig, ax = plt.subplots()
        ax.text(0.5, 0.5, 'No successful trials', ha='center', va='center')
        _maybe_save(fig, output_dir, f'scaling_{metric}_vs_{x}.png', save,
                    subdir='figures/scaling')
        return fig

    palette = algo_palette or _algo_palette(success_df['algorithm'].unique())
    fig, ax = plt.subplots(figsize=(9, 5))

    for algo, grp in success_df.groupby('algorithm'):
        agg = grp.groupby(x)[metric].agg(['mean', 'std']).reset_index()
        agg['std'] = agg['std'].fillna(0)
        color = palette[algo]
        ax.plot(agg[x], agg['mean'], marker='o', label=algo, color=color, linewidth=2)
        ax.fill_between(agg[x],
                        agg['mean'] - agg['std'],
                        agg['mean'] + agg['std'],
                        alpha=0.15, color=color)

    if log:
        ax.set_xscale('log')
        ax.set_yscale('log')

    ax.set_xlabel(x.replace('_', ' '))
    ax.set_ylabel(metric.replace('_', ' '))
    ax.set_title(f'Scaling: {metric.replace("_", " ")} vs {x.replace("_", " ")}')
    ax.legend(framealpha=0.9)
    ax.grid(alpha=0.3)
    plt.tight_layout()
    _maybe_save(fig, output_dir, f'scaling_{metric}_vs_{x}.png', save,
                subdir='figures/scaling')
    return fig


# ── 3. Density-hardness (random graphs) ─────────────────────────────────────────

def plot_density_hardness(df: pd.DataFrame,
                          metric: str = 'avg_chain_length',
                          algo_palette=None,
                          output_dir=None,
                          save: bool = False) -> plt.Figure:
    """Line plot: metric vs graph density for random graphs, one line per (algo, n).

    Only graphs with category=='random' are included.
    """
    rand_df = df[(df['category'] == 'random') & df['success']].copy()

    fig, ax = plt.subplots(figsize=(9, 5))
    if rand_df.empty:
        ax.text(0.5, 0.5, 'No random graph data', ha='center', va='center')
        _maybe_save(fig, output_dir, f'density_hardness_{metric}.png', save,
                    subdir='figures/scaling')
        return fig

    palette = algo_palette or _algo_palette(rand_df['algorithm'].unique())
    linestyles = ['-', '--', '-.', ':']
    n_values = sorted(rand_df['problem_nodes'].unique())

    for algo, algo_grp in rand_df.groupby('algorithm'):
        color = palette[algo]
        for i, n in enumerate(n_values):
            n_grp = algo_grp[algo_grp['problem_nodes'] == n]
            if n_grp.empty:
                continue
            agg = n_grp.groupby('problem_density')[metric].mean().reset_index()
            ls = linestyles[i % len(linestyles)]
            label = f'{algo} (n={n})'
            ax.plot(agg['problem_density'], agg[metric],
                    marker='o', label=label, color=color, linestyle=ls)

    ax.set_xlabel('Graph density')
    ax.set_ylabel(metric.replace('_', ' '))
    ax.set_title(f'Density hardness: {metric.replace("_", " ")} vs density (random graphs)')
    ax.legend(framealpha=0.9, fontsize=8)
    ax.grid(alpha=0.3)
    plt.tight_layout()
    _maybe_save(fig, output_dir, f'density_hardness_{metric}.png', save,
                subdir='figures/scaling')
    return fig


# ── 4. Pareto frontier ───────────────────────────────────────────────────────────

def _pareto_front(points: np.ndarray) -> np.ndarray:
    """Return boolean mask of Pareto-optimal points (minimise both dimensions)."""
    n = len(points)
    is_pareto = np.ones(n, dtype=bool)
    for i in range(n):
        if not is_pareto[i]:
            continue
        dominated = np.all(points <= points[i], axis=1) & np.any(points < points[i], axis=1)
        dominated[i] = False
        is_pareto[dominated] = False
    return is_pareto


def plot_pareto(df: pd.DataFrame,
                x: str = 'wall_time',
                y: str = 'avg_chain_length',
                algo_palette=None,
                output_dir=None,
                save: bool = False) -> plt.Figure:
    """Scatter: one point per (algorithm, problem), Pareto frontier highlighted.

    Uses per-problem mean across successful trials.
    """
    success_df = df[df['success']].copy()
    if success_df.empty:
        fig, ax = plt.subplots()
        ax.text(0.5, 0.5, 'No successful trials', ha='center', va='center')
        _maybe_save(fig, output_dir, f'pareto_{x}_vs_{y}.png', save,
                    subdir='figures')
        return fig

    agg = success_df.groupby(['algorithm', 'problem_name'])[[x, y]].mean().reset_index()
    palette = algo_palette or _algo_palette(agg['algorithm'].unique())

    fig, ax = plt.subplots(figsize=(9, 6))

    for algo, grp in agg.groupby('algorithm'):
        color = palette[algo]
        ax.scatter(grp[x], grp[y], color=color, label=algo, alpha=0.65, s=40, zorder=3)

    # Pareto frontier across all points
    pts = agg[[x, y]].values
    if len(pts) >= 2:
        mask = _pareto_front(pts)
        front = agg[mask].sort_values(x)
        ax.plot(front[x], front[y], 'k--', linewidth=1.5,
                label='Pareto frontier', zorder=4)

    ax.set_xlabel(x.replace('_', ' '))
    ax.set_ylabel(y.replace('_', ' '))
    ax.set_title(f'Pareto frontier: {x.replace("_"," ")} vs {y.replace("_"," ")}')
    ax.legend(framealpha=0.9)
    ax.grid(alpha=0.3)
    plt.tight_layout()
    _maybe_save(fig, output_dir, f'pareto_{x}_vs_{y}.png', save,
                subdir='figures')
    return fig


# ── 5. Distribution violin ───────────────────────────────────────────────────────

def plot_distributions(df: pd.DataFrame,
                       metric: str = 'avg_chain_length',
                       algo_palette=None,
                       output_dir=None,
                       save: bool = False) -> plt.Figure:
    """Violin plot of `metric` per algorithm (successful trials only)."""
    success_df = df[df['success']].copy()
    if success_df.empty or metric not in success_df.columns:
        fig, ax = plt.subplots()
        ax.text(0.5, 0.5, 'No data', ha='center', va='center')
        if metric == 'avg_chain_length':
            fname = 'chain_length_violin.png'
        elif metric == 'wall_time':
            fname = 'embedding_time_violin.png'
        else:
            fname = f'distribution_{metric}.png'
        _maybe_save(fig, output_dir, fname, save, subdir='figures/distributions')
        return fig

    palette = algo_palette or _algo_palette(success_df['algorithm'].unique())
    algos = sorted(success_df['algorithm'].unique())

    fig, ax = plt.subplots(figsize=(max(6, len(algos) * 1.5), 5))
    success_df = success_df.copy()
    success_df['_algo_color'] = success_df['algorithm'].map(palette)
    sns.violinplot(
        data=success_df, x='algorithm', y=metric, order=algos,
        hue='algorithm', palette=palette, legend=False,
        ax=ax, inner='box', cut=0
    )
    ax.set_xlabel('Algorithm')
    ax.set_ylabel(metric.replace('_', ' '))
    ax.set_title(f'Distribution of {metric.replace("_", " ")} per algorithm')
    ax.grid(axis='y', alpha=0.3)
    plt.xticks(rotation=20, ha='right')
    plt.tight_layout()

    if metric == 'avg_chain_length':
        fname = 'chain_length_violin.png'
    elif metric == 'wall_time':
        fname = 'embedding_time_violin.png'
    else:
        fname = f'distribution_{metric}.png'
    _maybe_save(fig, output_dir, fname, save, subdir='figures/distributions')
    return fig


# ── 6. Head-to-head scatter ──────────────────────────────────────────────────────

def plot_head_to_head(df: pd.DataFrame,
                      algo_a: str,
                      algo_b: str,
                      metric: str = 'avg_chain_length',
                      algo_palette=None,
                      output_dir=None,
                      save: bool = False) -> plt.Figure:
    """Scatter: per-problem mean metric for algo_a (x) vs algo_b (y).

    Points below the diagonal → algo_a wins (lower is better for most metrics).
    """
    success_df = df[df['success']].copy()
    per_problem = (
        success_df
        .groupby(['algorithm', 'problem_name'])[metric]
        .mean()
        .unstack(level='algorithm')
    )

    fig, ax = plt.subplots(figsize=(6, 6))

    if algo_a not in per_problem.columns or algo_b not in per_problem.columns:
        ax.text(0.5, 0.5, f'Missing data for {algo_a} or {algo_b}',
                ha='center', va='center')
        _maybe_save(fig, output_dir, f'scatter_{algo_a}_vs_{algo_b}.png', save,
                    subdir='figures/pairwise')
        return fig

    common = per_problem[[algo_a, algo_b]].dropna()
    if common.empty:
        ax.text(0.5, 0.5, 'No paired problems', ha='center', va='center')
        _maybe_save(fig, output_dir, f'scatter_{algo_a}_vs_{algo_b}.png', save,
                    subdir='figures/pairwise')
        return fig

    ax.scatter(common[algo_a], common[algo_b], alpha=0.7, s=50,
               color='steelblue', zorder=3)

    # Diagonal reference
    lo = min(common[algo_a].min(), common[algo_b].min()) * 0.95
    hi = max(common[algo_a].max(), common[algo_b].max()) * 1.05
    ax.plot([lo, hi], [lo, hi], 'k--', linewidth=1, alpha=0.5, label='Equal')

    # Win counts
    a_wins = (common[algo_a] < common[algo_b]).sum()
    b_wins = (common[algo_b] < common[algo_a]).sum()
    ax.set_title(f'{algo_a} vs {algo_b}\n{metric.replace("_"," ")}'
                 f'  ({algo_a} better: {a_wins}, {algo_b} better: {b_wins})')
    ax.set_xlabel(f'{algo_a} {metric.replace("_"," ")}')
    ax.set_ylabel(f'{algo_b} {metric.replace("_"," ")}')
    ax.legend()
    ax.grid(alpha=0.3)
    ax.set_aspect('equal', 'box')
    plt.tight_layout()
    _maybe_save(fig, output_dir, f'scatter_{algo_a}_vs_{algo_b}.png', save,
                subdir='figures/pairwise')
    return fig


# ── 7. Consistency (CV) ──────────────────────────────────────────────────────────

def plot_consistency(df: pd.DataFrame,
                     algo_palette=None,
                     output_dir=None,
                     save: bool = False) -> plt.Figure:
    """Two-panel bar chart: coefficient of variation of time and chain length per algo.

    Lower CV → more consistent.  Computed per (algo, problem) pair, then averaged.
    Only problems with ≥ 2 successful trials contribute.
    """
    success_df = df[df['success']].copy()

    def _mean_cv(metric):
        cv_per_prob = (
            success_df.groupby(['algorithm', 'problem_name'])[metric]
            .agg(lambda s: s.std() / s.mean() if s.mean() != 0 and len(s) >= 2 else np.nan)
        )
        return cv_per_prob.groupby('algorithm').mean()

    cv_time  = _mean_cv('wall_time')
    cv_chain = _mean_cv('avg_chain_length')

    algos = sorted(set(cv_time.index) | set(cv_chain.index))
    palette = algo_palette or _algo_palette(algos)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 4))

    for ax, cv, title in [
        (ax1, cv_time,  'CV of embedding time'),
        (ax2, cv_chain, 'CV of avg chain length'),
    ]:
        vals = [cv.get(a, np.nan) for a in algos]
        colors = [palette[a] for a in algos]
        bars = ax.bar(algos, vals, color=colors)
        ax.set_title(title)
        ax.set_ylabel('Coefficient of variation')
        ax.set_ylim(bottom=0)
        ax.grid(axis='y', alpha=0.3)
        plt.setp(ax.get_xticklabels(), rotation=20, ha='right')

    plt.suptitle('Algorithm consistency (lower CV = more consistent)')
    plt.tight_layout()
    _maybe_save(fig, output_dir, 'consistency_cv.png', save,
                subdir='figures/distributions')
    return fig


# ── 8. Topology comparison ───────────────────────────────────────────────────────

def plot_topology_comparison(df: pd.DataFrame,
                              metric: str = 'avg_chain_length',
                              algo_palette=None,
                              output_dir=None,
                              save: bool = False) -> plt.Figure:
    """Grouped bar chart: metric per (algorithm × topology).

    Meaningful when results span multiple topologies.
    """
    success_df = df[df['success']].copy()
    topologies = sorted(success_df['topology_name'].dropna().unique())
    algos = sorted(success_df['algorithm'].unique())
    palette = algo_palette or _algo_palette(algos)

    agg = (
        success_df
        .groupby(['algorithm', 'topology_name'])[metric]
        .mean()
        .reset_index()
    )

    n_topos = len(topologies)
    n_algos = len(algos)
    width = 0.8 / n_algos
    x = np.arange(n_topos)

    fig, ax = plt.subplots(figsize=(max(6, n_topos * n_algos * 0.7 + 2), 5))

    for i, algo in enumerate(algos):
        vals = []
        for topo in topologies:
            row = agg[(agg['algorithm'] == algo) & (agg['topology_name'] == topo)]
            vals.append(row[metric].values[0] if not row.empty else np.nan)
        offset = (i - n_algos / 2 + 0.5) * width
        ax.bar(x + offset, vals, width=width * 0.9,
               label=algo, color=palette[algo], alpha=0.9)

    ax.set_xticks(x)
    ax.set_xticklabels(topologies, rotation=20, ha='right')
    ax.set_ylabel(metric.replace('_', ' '))
    ax.set_title(f'{metric.replace("_"," ")} by topology and algorithm')
    ax.legend(framealpha=0.9)
    ax.grid(axis='y', alpha=0.3)
    plt.tight_layout()
    _maybe_save(fig, output_dir, f'topology_comparison_{metric}.png', save,
                subdir='figures/topology')
    return fig


# ── 9. Problem deep dive ─────────────────────────────────────────────────────────

def plot_problem_deep_dive(df: pd.DataFrame,
                            problem_name: str,
                            algo_palette=None,
                            output_dir=None,
                            save: bool = False) -> plt.Figure:
    """Two-panel bar chart for a single problem: time and chain length per algorithm."""
    prob_df = df[df['problem_name'] == problem_name].copy()

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 4))

    if prob_df.empty:
        for ax in (ax1, ax2):
            ax.text(0.5, 0.5, f'No data for {problem_name}', ha='center', va='center')
        _maybe_save(fig, output_dir, f'deep_dive_{problem_name}.png', save,
                    subdir='figures')
        return fig

    success_df = prob_df[prob_df['success']]
    algos = sorted(prob_df['algorithm'].unique())
    palette = algo_palette or _algo_palette(algos)
    colors = [palette[a] for a in algos]

    for ax, metric, ylabel in [
        (ax1, 'wall_time',   'Embedding time (s)'),
        (ax2, 'avg_chain_length', 'Avg chain length'),
    ]:
        vals = []
        errs = []
        for algo in algos:
            adf = success_df[success_df['algorithm'] == algo]
            if adf.empty:
                vals.append(np.nan)
                errs.append(0)
            else:
                vals.append(adf[metric].mean())
                errs.append(adf[metric].std() if len(adf) > 1 else 0)

        bars = ax.bar(algos, vals, color=colors, alpha=0.9,
                      yerr=errs, capsize=4)
        ax.set_ylabel(ylabel)
        ax.set_title(f'{ylabel}\n({problem_name})')
        ax.grid(axis='y', alpha=0.3)
        plt.setp(ax.get_xticklabels(), rotation=20, ha='right')

        # Annotate bars with success/validity
        for bar, algo in zip(bars, algos):
            adf = prob_df[prob_df['algorithm'] == algo]
            n_ok = adf['success'].sum()
            n_valid = adf['is_valid'].sum()
            n_total = len(adf)
            annot = f'{n_ok}/{n_total} ✓'
            h = bar.get_height()
            if not np.isnan(h):
                ax.text(bar.get_x() + bar.get_width() / 2,
                        h * 1.02, annot,
                        ha='center', va='bottom', fontsize=7)

    plt.suptitle(f'Deep dive: {problem_name}')
    plt.tight_layout()
    fname = f'deep_dive_{problem_name.replace("/", "_")}.png'
    _maybe_save(fig, output_dir, fname, save, subdir='figures')
    return fig


# ── 10. Chain length distribution ────────────────────────────────────────────────

def plot_chain_distribution(df: pd.DataFrame,
                             algo_palette=None,
                             output_dir=None,
                             save: bool = False) -> plt.Figure:
    """Overlaid KDE of avg_chain_length per algorithm (successful trials only)."""
    success_df = df[df['success']].copy()
    if success_df.empty:
        fig, ax = plt.subplots()
        ax.text(0.5, 0.5, 'No successful trials', ha='center', va='center')
        _maybe_save(fig, output_dir, 'chain_length_kde.png', save,
                    subdir='figures/distributions')
        return fig

    palette = algo_palette or _algo_palette(success_df['algorithm'].unique())
    algos = sorted(success_df['algorithm'].unique())

    fig, ax = plt.subplots(figsize=(8, 4))
    for algo in algos:
        data = success_df[success_df['algorithm'] == algo]['avg_chain_length'].dropna()
        if data.empty or data.std() == 0:
            ax.axvline(data.mean(), label=algo, color=palette[algo], linestyle='--')
        else:
            sns.kdeplot(data, ax=ax, label=algo, color=palette[algo], fill=True, alpha=0.2)

    ax.set_xlabel('Avg chain length')
    ax.set_ylabel('Density')
    ax.set_title('Chain length distribution per algorithm')
    ax.legend(framealpha=0.9)
    ax.grid(alpha=0.3)
    plt.tight_layout()
    _maybe_save(fig, output_dir, 'chain_length_kde.png', save,
                subdir='figures/distributions')
    return fig


# ── 11. Win rate matrix ──────────────────────────────────────────────────────────

def plot_win_rate_matrix(df, metric='avg_chain_length', lower_is_better=True,
                         output_dir=None, save=False):
    """Heatmap of pairwise win rates between algorithms."""
    from qeanalysis.statistics import win_rate_matrix
    wm = win_rate_matrix(df, metric, lower_is_better)
    if wm.empty:
        fig, ax = plt.subplots()
        ax.text(0.5, 0.5, 'No data', ha='center', va='center')
        _maybe_save(fig, output_dir, 'win_rate_matrix.png', save, subdir='figures/pairwise')
        return fig
    fig, ax = plt.subplots(figsize=(max(5, len(wm) * 1.2), max(4, len(wm) * 1.0)))
    # Convert to percent for display
    wm_pct = wm * 100
    sns.heatmap(wm_pct, ax=ax, annot=True, fmt='.0f', cmap='RdYlGn',
                vmin=0, vmax=100, linewidths=0.5,
                cbar_kws={'label': '% problems won'})
    ax.set_title(f'Win rate matrix ({metric.replace("_"," ")})\n(row algo wins against col algo)')
    plt.tight_layout()
    _maybe_save(fig, output_dir, 'win_rate_matrix.png', save, subdir='figures/pairwise')
    return fig


# ── 12. Success heatmap ──────────────────────────────────────────────────────────

def plot_success_heatmap(df, output_dir=None, save=False):
    """Heatmap: algorithm × graph, cell = success rate across trials."""
    algos = sorted(df['algorithm'].unique())
    graphs = sorted(df['problem_name'].unique())

    # Build rate matrix
    data = pd.DataFrame(index=algos, columns=graphs, dtype=float)
    annot = pd.DataFrame(index=algos, columns=graphs, dtype=str)
    for algo in algos:
        for graph in graphs:
            sub = df[(df['algorithm'] == algo) & (df['problem_name'] == graph)]
            n_total = len(sub)
            n_ok = int(sub['success'].sum())
            data.loc[algo, graph] = n_ok / n_total if n_total > 0 else float('nan')
            annot.loc[algo, graph] = f'{n_ok}/{n_total}' if n_total <= 5 else f'{n_ok/n_total:.0%}'

    width = max(10, len(graphs) * 0.5)
    height = max(3, len(algos) * 0.8) + 1
    fig, ax = plt.subplots(figsize=(width, height))
    sns.heatmap(data.astype(float), ax=ax, annot=annot.values, fmt='',
                cmap='RdYlGn', vmin=0, vmax=1, linewidths=0.3,
                cbar_kws={'label': 'Success rate'})
    ax.set_title('Success rate per algorithm and graph')
    ax.set_xlabel('Graph')
    ax.set_ylabel('Algorithm')
    plt.xticks(rotation=45, ha='right', fontsize=7)
    plt.tight_layout()
    _maybe_save(fig, output_dir, 'success_rate_heatmap.png', save, subdir='figures/success')
    return fig


# ── 13. Success by nodes ─────────────────────────────────────────────────────────

def plot_success_by_nodes(df, algo_palette=None, output_dir=None, save=False):
    """Line plot: success rate vs n_nodes per algorithm."""
    palette = algo_palette or _algo_palette(df['algorithm'].unique())
    markers = _algo_markers(df['algorithm'].unique())
    algos = sorted(df['algorithm'].unique())

    fig, ax = plt.subplots(figsize=(9, 5))
    for algo in algos:
        adf = df[df['algorithm'] == algo]
        agg = adf.groupby('problem_nodes')['success'].mean().reset_index()
        ax.plot(agg['problem_nodes'], agg['success'],
                marker=markers[algo], label=algo, color=palette[algo], linewidth=2)
    ax.set_xlabel('Number of nodes')
    ax.set_ylabel('Success rate')
    ax.set_ylim(-0.05, 1.05)
    ax.set_title('Success rate vs graph size')
    ax.legend(framealpha=0.9, bbox_to_anchor=(1.02, 1), loc='upper left')
    ax.grid(alpha=0.3)
    plt.tight_layout()
    _maybe_save(fig, output_dir, 'success_rate_by_nodes.png', save, subdir='figures/success')
    return fig


# ── 14. Success by density ───────────────────────────────────────────────────────

def plot_success_by_density(df, algo_palette=None, output_dir=None, save=False):
    """Line plot: success rate vs problem_density per algorithm."""
    palette = algo_palette or _algo_palette(df['algorithm'].unique())
    markers = _algo_markers(df['algorithm'].unique())
    algos = sorted(df['algorithm'].unique())

    fig, ax = plt.subplots(figsize=(9, 5))
    for algo in algos:
        adf = df[df['algorithm'] == algo]
        # Bin density into ~10 bins
        adf = adf.copy()
        adf['density_bin'] = pd.cut(adf['problem_density'], bins=10)
        agg = adf.groupby('density_bin', observed=True)['success'].mean()
        midpoints = [iv.mid for iv in agg.index]
        ax.plot(midpoints, agg.values,
                marker=markers[algo], label=algo, color=palette[algo], linewidth=2)
    ax.set_xlabel('Graph density')
    ax.set_ylabel('Success rate')
    ax.set_ylim(-0.05, 1.05)
    ax.set_title('Success rate vs graph density')
    ax.legend(framealpha=0.9, bbox_to_anchor=(1.02, 1), loc='upper left')
    ax.grid(alpha=0.3)
    plt.tight_layout()
    _maybe_save(fig, output_dir, 'success_rate_by_density.png', save, subdir='figures/success')
    return fig


# ── Graph-indexed helpers ────────────────────────────────────────────────────────

def _graph_jitter(graph_id: str, magnitude: float) -> float:
    """Deterministic jitter for a graph, seeded from its ID string."""
    seed = int(hashlib.md5(graph_id.encode()).hexdigest(), 16) % (2 ** 32)
    rng = np.random.default_rng(seed)
    return float(rng.uniform(-magnitude, magnitude))


def _category_of(problem_name: str) -> str:
    """Quick category lookup without importing loader (avoids circular)."""
    from qeanalysis.loader import infer_category
    return infer_category(problem_name)


def _draw_chain_dots_categorical(ax, df, graphs, algos, palette, markers):
    """Draw dot plot on ax with categorical x positions for the given graphs."""
    x_pos = {g: i for i, g in enumerate(graphs)}
    categories = [_category_of(g) for g in graphs]

    for algo in algos:
        adf = df[df['algorithm'] == algo]
        xs_trial, ys_trial = [], []
        xs_mean, ys_mean = [], []
        for g in graphs:
            gdf = adf[adf['problem_name'] == g]
            if gdf.empty:
                continue
            xs_trial.extend([x_pos[g]] * len(gdf))
            ys_trial.extend(gdf['avg_chain_length'].tolist())
            xs_mean.append(x_pos[g])
            ys_mean.append(gdf['avg_chain_length'].mean())
        ax.scatter(xs_trial, ys_trial,
                   color=palette[algo], marker=markers[algo],
                   alpha=0.35, s=20, zorder=2)
        ax.scatter(xs_mean, ys_mean,
                   color=palette[algo], marker='D', s=60,
                   zorder=3, edgecolors='black', linewidths=0.5)

    # Category boundaries and section labels
    prev_cat = None
    cat_start = 0
    boundaries = []
    for i, (g, cat) in enumerate(zip(graphs, categories)):
        if cat != prev_cat:
            if prev_cat is not None:
                boundaries.append((cat_start, i - 1, prev_cat))
                ax.axvline(i - 0.5, color='gray', linewidth=0.8, alpha=0.5, linestyle='--')
            cat_start = i
            prev_cat = cat
    boundaries.append((cat_start, len(graphs) - 1, prev_cat))

    for start, end, cat in boundaries:
        mid = (start + end) / 2
        # y=1.02 is axes-coordinate (just above top of plot) since we use
        # get_xaxis_transform() where x=data, y=axes.
        ax.text(mid, 1.02, cat, ha='center', va='bottom', fontsize=8,
                fontstyle='italic', color='dimgray',
                transform=ax.get_xaxis_transform())

    ax.set_xticks([])  # suppress individual graph ID labels
    ax.set_xlim(-0.5, len(graphs) - 0.5)
    ax.grid(axis='y', alpha=0.3)


def _add_category_labels(ax, graphs, categories):
    """Add vertical dividers and category section labels to a categorical plot."""
    prev_cat = None
    cat_start = 0
    for i, (g, cat) in enumerate(zip(graphs, categories)):
        if cat != prev_cat:
            if prev_cat is not None:
                ax.axvline(i - 0.5, color='gray', linewidth=0.8, alpha=0.5, linestyle='--')
                mid = (cat_start + i - 1) / 2
                ax.text(mid, 1.02, prev_cat, transform=ax.get_xaxis_transform(),
                        ha='center', fontsize=8, fontstyle='italic', color='dimgray')
            cat_start = i
            prev_cat = cat
    if prev_cat is not None:
        mid = (cat_start + len(graphs) - 1) / 2
        ax.text(mid, 1.02, prev_cat, transform=ax.get_xaxis_transform(),
                ha='center', fontsize=8, fontstyle='italic', color='dimgray')


# ── 15. Graph-indexed chain length ───────────────────────────────────────────────

def plot_graph_indexed_chain(df, x_mode='by_graph_id', algo_palette=None,
                              output_dir=None, save=False):
    """Dot plot: avg_chain_length per graph instance.

    x_mode: 'by_graph_id' (categorical) | 'by_n_nodes' (numeric) | 'by_density' (numeric)
    Shows per-trial dots (small, semi-transparent) + per-algorithm mean marker (diamond).
    Shared-graph filter: only graphs where ALL algorithms have at least one success.
    """
    from qeanalysis.filters import shared_graph_filter
    success_df = df[df['success']].copy()
    if success_df.empty:
        fig, ax = plt.subplots()
        ax.text(0.5, 0.5, 'No successful trials', ha='center', va='center')
        _maybe_save(fig, output_dir, 'chain_length.png', save,
                    subdir=f'figures/graph_indexed/{x_mode}')
        return fig

    algos = sorted(success_df['algorithm'].unique())
    palette = algo_palette or _algo_palette(algos)
    markers = _algo_markers(algos)

    # Shared-graph filter: intersection of graphs where each algorithm succeeded
    filt_df = shared_graph_filter(success_df, algos)
    if filt_df.empty:
        filt_df = success_df  # fall back if no common graphs

    graphs = sorted(filt_df['problem_name'].unique())
    n_graphs = len(graphs)
    n_algos = len(algos)

    if x_mode == 'by_graph_id':
        # Categorical x-axis
        facet = n_graphs > 25
        categories = [_category_of(g) for g in graphs]

        if facet:
            unique_cats = sorted(set(categories))
            n_cats = len(unique_cats)
            fig, axes = plt.subplots(1, n_cats,
                                     figsize=(max(14, n_graphs * 0.4), 5),
                                     sharey=True)
            if n_cats == 1:
                axes = [axes]
            for ax, cat in zip(axes, unique_cats):
                cat_graphs = [g for g in graphs if _category_of(g) == cat]
                _draw_chain_dots_categorical(ax, filt_df, cat_graphs, algos, palette, markers)
                ax.set_title(cat, fontsize=10)
                ax.set_xlabel('')
            axes[0].set_ylabel('Avg chain length')
            handles = [mpatches.Patch(color=palette[a], label=a) for a in algos]
            fig.legend(handles=handles, bbox_to_anchor=(1.01, 0.9), loc='upper left',
                       framealpha=0.9, fontsize=8)
            fig.suptitle('Chain length by graph (all algorithms, shared-graph filter)')
        else:
            width = max(14, n_graphs * 0.55)
            fig, ax = plt.subplots(figsize=(width, 5))
            _draw_chain_dots_categorical(ax, filt_df, graphs, algos, palette, markers)
            ax.set_ylabel('Avg chain length')
            ax.set_title('Chain length by graph (shared-graph filter)')
            handles = [mpatches.Patch(color=palette[a], label=a) for a in algos]
            ax.legend(handles=handles, bbox_to_anchor=(1.01, 1), loc='upper left',
                      framealpha=0.9, fontsize=8)
    else:
        # Numeric x-axis
        x_col = 'problem_nodes' if x_mode == 'by_n_nodes' else 'problem_density'
        xlabel = 'Number of nodes' if x_mode == 'by_n_nodes' else 'Graph density'
        x_range = filt_df[x_col].max() - filt_df[x_col].min()
        jitter_mag = max(0.01, x_range * 0.015)

        fig, ax = plt.subplots(figsize=(10, 5))
        for algo in algos:
            adf = filt_df[filt_df['algorithm'] == algo]
            # Per-trial dots
            x_trial = [row[x_col] + _graph_jitter(row['problem_name'], jitter_mag)
                       for _, row in adf.iterrows()]
            ax.scatter(x_trial, adf['avg_chain_length'],
                       color=palette[algo], marker=markers[algo],
                       alpha=0.35, s=25, zorder=2)
            # Per-graph mean
            means = adf.groupby('problem_name').agg(
                {x_col: 'first', 'avg_chain_length': 'mean'}
            )
            x_mean = [xv + _graph_jitter(gid, jitter_mag)
                      for gid, xv in zip(means.index, means[x_col])]
            ax.scatter(x_mean, means['avg_chain_length'],
                       color=palette[algo], marker='D', s=70,
                       label=algo, zorder=3, edgecolors='black', linewidths=0.5)
        ax.set_xlabel(xlabel)
        ax.set_ylabel('Avg chain length')
        ax.set_title(f'Chain length vs {xlabel.lower()} (shared-graph filter)')
        ax.legend(bbox_to_anchor=(1.02, 1), loc='upper left', framealpha=0.9, fontsize=9)
        ax.grid(alpha=0.3)

    plt.tight_layout()
    _maybe_save(fig, output_dir, 'chain_length.png', save,
                subdir=f'figures/graph_indexed/{x_mode}')
    return fig


# ── 16. Graph-indexed embedding time ────────────────────────────────────────────

def plot_graph_indexed_time(df, x_mode='by_graph_id', algo_palette=None,
                             output_dir=None, save=False):
    """Dot plot: wall_time per graph instance, log scale.

    Timeout runs appear at the timeout ceiling with a distinct marker (triangle up).
    No shared-graph filter — shows all runs including timeouts.
    """
    if df.empty:
        fig, ax = plt.subplots()
        ax.text(0.5, 0.5, 'No data', ha='center', va='center')
        _maybe_save(fig, output_dir, 'embedding_time.png', save,
                    subdir=f'figures/graph_indexed/{x_mode}')
        return fig

    algos = sorted(df['algorithm'].unique())
    palette = algo_palette or _algo_palette(algos)
    markers_map = _algo_markers(algos)

    timeout_val = df['wall_time'].max() * 1.05

    if x_mode == 'by_graph_id':
        graphs = sorted(df['problem_name'].unique())
        n_graphs = len(graphs)
        width = max(14, n_graphs * 0.55)
        fig, ax = plt.subplots(figsize=(width, 5))
        x_pos = {g: i for i, g in enumerate(graphs)}
        categories = [_category_of(g) for g in graphs]

        for algo in algos:
            adf = df[df['algorithm'] == algo]
            for g in graphs:
                gdf = adf[adf['problem_name'] == g]
                if gdf.empty:
                    continue
                for _, row in gdf.iterrows():
                    is_timeout = row.get('is_timeout', False)
                    mk = '^' if is_timeout else markers_map[algo]
                    ax.scatter(x_pos[g], row['wall_time'],
                               color=palette[algo], marker=mk,
                               alpha=0.5 if not is_timeout else 0.9,
                               s=30, zorder=2)

        _add_category_labels(ax, graphs, categories)
        ax.set_yscale('log')
        ax.set_ylabel('Wall time (s, log scale)')
        ax.set_title('Embedding time by graph')
        ax.set_xticks([])
        ax.set_xlim(-0.5, len(graphs) - 0.5)
        ax.grid(axis='y', alpha=0.3)

    else:
        x_col = 'problem_nodes' if x_mode == 'by_n_nodes' else 'problem_density'
        xlabel = 'Number of nodes' if x_mode == 'by_n_nodes' else 'Graph density'
        x_range = df[x_col].max() - df[x_col].min()
        jitter_mag = max(0.01, x_range * 0.015)

        fig, ax = plt.subplots(figsize=(10, 5))
        for algo in algos:
            adf = df[df['algorithm'] == algo]
            for _, row in adf.iterrows():
                is_timeout = row.get('is_timeout', False)
                mk = '^' if is_timeout else markers_map[algo]
                jx = row[x_col] + _graph_jitter(str(row['problem_name']), jitter_mag)
                ax.scatter(jx, row['wall_time'],
                           color=palette[algo], marker=mk,
                           alpha=0.5 if not is_timeout else 0.9,
                           s=30, zorder=2)
        ax.set_xlabel(xlabel)
        ax.set_yscale('log')
        ax.set_ylabel('Wall time (s, log scale)')
        ax.set_title(f'Embedding time vs {xlabel.lower()}')
        ax.grid(alpha=0.3)

    # Legend: algorithms + timeout marker
    handles = [mpatches.Patch(color=palette[a], label=a) for a in algos]
    handles.append(plt.Line2D([0], [0], marker='^', color='gray', linestyle='None',
                               markersize=8, label='Timeout'))
    ax.legend(handles=handles, bbox_to_anchor=(1.02, 1), loc='upper left',
              framealpha=0.9, fontsize=8)
    plt.tight_layout()
    _maybe_save(fig, output_dir, 'embedding_time.png', save,
                subdir=f'figures/graph_indexed/{x_mode}')
    return fig


# ── 17. Graph-indexed success ────────────────────────────────────────────────────

def plot_graph_indexed_success(df, x_mode='by_graph_id', output_dir=None, save=False):
    """Success rate heatmap: algorithm × graph, with same x-ordering as other variants.

    Note: for by_n_nodes and by_density x_modes, graphs are still shown as categorical
    positions (same ordering as by_graph_id) since success is binary.
    """
    algos = sorted(df['algorithm'].unique())
    graphs = sorted(df['problem_name'].unique())

    data = np.full((len(algos), len(graphs)), np.nan)
    annot = np.empty((len(algos), len(graphs)), dtype=object)

    for i, algo in enumerate(algos):
        for j, graph in enumerate(graphs):
            sub = df[(df['algorithm'] == algo) & (df['problem_name'] == graph)]
            n = len(sub)
            k = int(sub['success'].sum())
            data[i, j] = k / n if n > 0 else np.nan
            annot[i, j] = f'{k}/{n}'

    width = max(10, len(graphs) * 0.5)
    height = max(3, len(algos) * 0.9) + 1
    fig, ax = plt.subplots(figsize=(width, height))

    sns.heatmap(data, ax=ax, annot=annot, fmt='',
                cmap='RdYlGn', vmin=0, vmax=1,
                linewidths=0.3, linecolor='white',
                xticklabels=graphs, yticklabels=algos,
                cbar_kws={'label': 'Success rate'})
    ax.set_xticklabels(ax.get_xticklabels(), rotation=45, ha='right', fontsize=7)
    ax.set_title(f'Success rate per algorithm x graph ({x_mode})')
    ax.set_xlabel('Graph')
    ax.set_ylabel('Algorithm')
    plt.tight_layout()
    _maybe_save(fig, output_dir, 'success.png', save,
                subdir=f'figures/graph_indexed/{x_mode}')
    return fig
