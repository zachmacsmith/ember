"""
ember_qc_analysis/plots.py
==========================
All visualizations for ember_qc_analysis.

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

def _maybe_save(fig, output_dir, filename, save, subdir=None, fmt='png'):
    if save and output_dir is not None:
        target = Path(output_dir) / subdir if subdir else Path(output_dir)
        target.mkdir(parents=True, exist_ok=True)
        # Use fmt to override the extension so callers don't need to change their filenames
        out_name = Path(filename).stem + '.' + fmt
        fig.savefig(target / out_name, dpi=150, bbox_inches='tight')
    plt.close(fig)


# ── 1. Category heatmap ─────────────────────────────────────────────────────────

def plot_heatmap(df: pd.DataFrame,
                 metric: str = 'avg_chain_length',
                 algo_palette=None,
                 output_dir=None,
                 save: bool = False,
                 fmt: str = 'png') -> plt.Figure:
    """Heatmap: algorithm (rows) × graph category (columns), cell = mean metric.

    For most metrics only successful trials are included.
    ``success_rate`` and ``wall_time`` use all trials.
    """
    if metric == 'win_rate':
        # Win rate: % of graphs where this algorithm has the shortest
        # avg_chain_length among all algorithms (successful trials only)
        sdf = df[df['success']].copy()
        if sdf.empty:
            fig, ax = plt.subplots()
            ax.text(0.5, 0.5, 'No successful data', ha='center', va='center')
            _maybe_save(fig, output_dir, 'by_category.png', save,
                        subdir=f'figures/category_breakdown/{metric}', fmt=fmt)
            return fig
        # For each graph_id, find the algorithm(s) with the minimum avg_chain_length
        best = sdf.loc[sdf.groupby('graph_id')['avg_chain_length'].idxmin()]
        # Count wins per (algorithm, category)
        win_counts = best.groupby(['algorithm', 'category']).size().unstack(level='category', fill_value=0)
        # Total graphs per category (where at least one algo succeeded)
        total_per_cat = best.groupby('category').size()
        pivot = win_counts.div(total_per_cat, axis=1)
        # Ensure all algorithms appear (even if zero wins)
        all_algos = sorted(df['algorithm'].unique())
        pivot = pivot.reindex(all_algos, fill_value=0.0)
    elif metric == 'success_rate':
        # Compute success rate per (algorithm, category)
        pivot = (
            df.groupby(['algorithm', 'category'])['success']
            .mean()
            .unstack(level='category')
        )
    elif metric == 'wall_time':
        # Embedding time across all trials (not just successful)
        pivot = (
            df.groupby(['algorithm', 'category'])[metric]
            .mean()
            .unstack(level='category')
        )
    elif metric == 'relative_time':
        # Relative slowdown: each cell = algo_time / best_time for that category
        raw = (
            df.groupby(['algorithm', 'category'])['wall_time']
            .mean()
            .unstack(level='category')
        )
        col_min = raw.min(axis=0)
        col_min = col_min.replace(0, np.nan)  # avoid div by zero
        pivot = raw.div(col_min, axis=1)
    else:
        from ember_qc_analysis.summary import summary_by_category
        pivot = summary_by_category(df, metric)

    if pivot.empty:
        fig, ax = plt.subplots()
        ax.text(0.5, 0.5, 'No data', ha='center', va='center')
        _maybe_save(fig, output_dir, 'by_category.png', save,
                    subdir=f'figures/category_breakdown/{metric}', fmt=fmt)
        return fig

    # Choose colormap
    if metric in ('success_rate', 'win_rate'):
        hm_cmap = 'RdYlGn'
    elif metric == 'relative_time':
        hm_cmap = 'RdYlGn_r'  # 1x = green (low), high multiplier = red
    else:
        hm_cmap = 'YlOrRd'

    fig, ax = plt.subplots(figsize=(max(6, pivot.shape[1] * 1.4),
                                    max(3, pivot.shape[0] * 0.9) + 1))
    if metric in ('success_rate', 'win_rate'):
        annot_fmt = '.0%'
    elif metric == 'relative_time':
        annot_fmt = '.1f'
    else:
        annot_fmt = '.2f'

    hm_kwargs = dict(
        cmap=hm_cmap, linewidths=0.5, linecolor='white',
        cbar_kws={'label': _HEATMAP_LABELS.get(metric, metric.replace('_', ' '))}
    )

    if metric == 'wall_time':
        # Log colour scale so small differences aren't washed out by outliers
        from matplotlib.colors import LogNorm
        floor = max(pivot.min().min(), 1e-4)  # avoid log(0)
        ceil = pivot.max().max()
        hm_kwargs['norm'] = LogNorm(vmin=floor, vmax=ceil)
    elif metric == 'relative_time':
        from matplotlib.colors import LogNorm
        hm_kwargs['norm'] = LogNorm(vmin=1.0, vmax=max(pivot.max().max(), 2.0))
    elif metric in ('success_rate', 'win_rate'):
        hm_kwargs['vmin'] = 0.0
        hm_kwargs['vmax'] = 1.0

    sns.heatmap(
        pivot, ax=ax, annot=True, fmt=annot_fmt, **hm_kwargs
    )
    label = _HEATMAP_LABELS.get(metric, metric.replace('_', ' '))
    ax.set_title(f'{label} by algorithm and graph category')
    ax.set_xlabel('Graph category')
    ax.set_ylabel('Algorithm')
    plt.tight_layout()
    _maybe_save(fig, output_dir, 'by_category.png', save,
                subdir=f'figures/category_breakdown/{metric}', fmt=fmt)
    return fig


# ── Category family groupings ────────────────────────────────────────────────────

_CATEGORY_FAMILIES = {
    'random': [
        'random_er', 'random_planar', 'barabasi_albert',
        'watts_strogatz', 'sbm', 'lfr_benchmark', 'regular',
    ],
    'structured': [
        'complete', 'bipartite', 'circulant', 'turan',
        'johnson', 'kneser', 'hypercube', 'generalized_petersen',
    ],
    'lattice': [
        'grid', 'honeycomb', 'triangular_lattice', 'kagome',
        'king_graph', 'cubic_lattice', 'bcc_lattice',
        'shastry_sutherland', 'frustrated_square',
    ],
    'tree_path': [
        'path', 'cycle', 'star', 'wheel',
        'binary_tree', 'tree',
    ],
    'application': [
        'spin_glass', 'weak_strong_cluster', 'planted_solution',
        'hardware_native', 'sudoku', 'named_special',
    ],
}

_FAMILY_LABELS = {
    'random': 'Random / stochastic graphs',
    'structured': 'Structured / algebraic graphs',
    'lattice': 'Lattice / physics-inspired graphs',
    'tree_path': 'Trees, paths & cycles',
    'application': 'Application & benchmark graphs',
}


def plot_heatmap_by_family(df: pd.DataFrame,
                           metric: str = 'avg_chain_length',
                           algo_palette=None,
                           output_dir=None,
                           save: bool = False,
                           fmt: str = 'png') -> List[plt.Figure]:
    """Per-family category heatmaps: one figure per graph family.

    Splits the full category heatmap into smaller, readable chunks
    grouped by graph family. Saved to ``figures/category_breakdown/``.
    """
    figs = []
    present_cats = set(df['category'].unique())

    for family_key, family_cats in _CATEGORY_FAMILIES.items():
        # Only include categories that exist in this dataset
        cats = [c for c in family_cats if c in present_cats]
        if not cats:
            continue

        fdf = df[df['category'].isin(cats)]
        if fdf.empty:
            continue

        # Reuse plot_heatmap but with filtered data — build the figure manually
        fig = plot_heatmap(fdf, metric=metric, algo_palette=algo_palette,
                           output_dir=None, save=False, fmt=fmt)

        # Update title to include family name
        ax = fig.axes[0]
        label = _HEATMAP_LABELS.get(metric, metric.replace('_', ' '))
        family_label = _FAMILY_LABELS.get(family_key, family_key)
        ax.set_title(f'{label}\n{family_label}')
        plt.tight_layout()

        _maybe_save(fig, output_dir, f'{family_key}.png', save,
                    subdir=f'figures/category_breakdown/{metric}', fmt=fmt)
        figs.append(fig)

    return figs


def plot_heatmap_family_summary(df: pd.DataFrame,
                                metric: str = 'avg_chain_length',
                                algo_palette=None,
                                output_dir=None,
                                save: bool = False,
                                fmt: str = 'png') -> plt.Figure:
    """Compact heatmap: algorithm × graph family (5 columns).

    Each family column aggregates all categories in that family using
    macro-averaging (mean of per-category values) so that large categories
    don't dominate.
    """
    present_cats = set(df['category'].unique())
    all_algos = sorted(df['algorithm'].unique())

    rows = {}
    for family_key, family_cats in _CATEGORY_FAMILIES.items():
        cats = [c for c in family_cats if c in present_cats]
        if not cats:
            continue
        fdf = df[df['category'].isin(cats)]
        if fdf.empty:
            continue

        if metric == 'win_rate':
            sdf = fdf[fdf['success']].copy()
            if sdf.empty:
                continue
            best = sdf.loc[sdf.groupby('graph_id')['avg_chain_length'].idxmin()]
            win_counts = best.groupby('algorithm').size()
            total = best.shape[0]
            for algo in all_algos:
                rows.setdefault(algo, {})[family_key] = win_counts.get(algo, 0) / total if total else 0.0
        elif metric == 'success_rate':
            per_cat = fdf.groupby(['algorithm', 'category'])['success'].mean().unstack('category')
            macro = per_cat.mean(axis=1)
            for algo in all_algos:
                rows.setdefault(algo, {})[family_key] = macro.get(algo, np.nan)
        elif metric == 'wall_time':
            per_cat = fdf.groupby(['algorithm', 'category'])[metric].mean().unstack('category')
            macro = per_cat.mean(axis=1)
            for algo in all_algos:
                rows.setdefault(algo, {})[family_key] = macro.get(algo, np.nan)
        elif metric == 'relative_time':
            per_cat = fdf.groupby(['algorithm', 'category'])['wall_time'].mean().unstack('category')
            macro = per_cat.mean(axis=1)
            best_time = macro.min()
            best_time = best_time if best_time > 0 else np.nan
            for algo in all_algos:
                rows.setdefault(algo, {})[family_key] = macro.get(algo, np.nan) / best_time if best_time else np.nan
        else:
            sdf = fdf[fdf['success']].copy()
            if sdf.empty:
                continue
            per_cat = sdf.groupby(['algorithm', 'category'])[metric].mean().unstack('category')
            macro = per_cat.mean(axis=1)
            for algo in all_algos:
                rows.setdefault(algo, {})[family_key] = macro.get(algo, np.nan)

    if not rows:
        fig, ax = plt.subplots()
        ax.text(0.5, 0.5, 'No data', ha='center', va='center')
        _maybe_save(fig, output_dir, 'by_family.png', save,
                    subdir=f'figures/category_breakdown/{metric}', fmt=fmt)
        return fig

    pivot = pd.DataFrame(rows).T
    # Reorder columns to match family order
    family_order = [k for k in _CATEGORY_FAMILIES if k in pivot.columns]
    pivot = pivot[family_order]
    # Use readable family labels
    pivot.columns = [_FAMILY_LABELS.get(c, c) for c in pivot.columns]

    # Colormap and formatting
    if metric in ('success_rate', 'win_rate'):
        hm_cmap = 'RdYlGn'
        annot_fmt = '.0%'
    elif metric == 'relative_time':
        hm_cmap = 'RdYlGn_r'
        annot_fmt = '.1f'
    else:
        hm_cmap = 'YlOrRd'
        annot_fmt = '.2f'

    fig, ax = plt.subplots(figsize=(max(6, len(pivot.columns) * 2.5),
                                    max(3, len(pivot) * 0.9) + 1))

    hm_kwargs = dict(
        cmap=hm_cmap, linewidths=0.5, linecolor='white',
        cbar_kws={'label': _HEATMAP_LABELS.get(metric, metric.replace('_', ' '))}
    )

    if metric == 'wall_time':
        from matplotlib.colors import LogNorm
        floor = max(pivot.min().min(), 1e-4)
        ceil = pivot.max().max()
        hm_kwargs['norm'] = LogNorm(vmin=floor, vmax=ceil)
    elif metric == 'relative_time':
        from matplotlib.colors import LogNorm
        hm_kwargs['norm'] = LogNorm(vmin=1.0, vmax=max(pivot.max().max(), 2.0))
    elif metric in ('success_rate', 'win_rate'):
        hm_kwargs['vmin'] = 0.0
        hm_kwargs['vmax'] = 1.0

    sns.heatmap(pivot, ax=ax, annot=True, fmt=annot_fmt, **hm_kwargs)
    label = _HEATMAP_LABELS.get(metric, metric.replace('_', ' '))
    ax.set_title(f'{label} by algorithm and graph family\n(macro-averaged within each family)')
    ax.set_xlabel('Graph family')
    ax.set_ylabel('Algorithm')
    plt.tight_layout()
    _maybe_save(fig, output_dir, 'by_family.png', save,
                subdir=f'figures/category_breakdown/{metric}', fmt=fmt)
    return fig


# ── 2. Scaling plot ──────────────────────────────────────────────────────────────

def plot_scaling(df: pd.DataFrame,
                 metric: str = 'wall_time',
                 x: str = 'problem_nodes',
                 log: bool = False,
                 bin_size: Optional[int] = None,
                 algo_palette=None,
                 output_dir=None,
                 save: bool = False,
                 fmt: str = 'png') -> plt.Figure:
    """Scatter + smoothed trend: metric vs x, one trace per algorithm.

    Raw trial points are shown as a light scatter; the trend line is the
    binned mean with a ±1 std ribbon.  Binning avoids the extreme zigzag
    produced when hundreds of unique x values each have only one or two
    trials.  Only successful trials are included.

    Args:
        bin_size: Width of x-axis bins used for the trend line.  Defaults
                  to ``None``, which auto-selects roughly 40 bins across
                  the observed data range.  Pass an explicit integer (e.g.
                  ``bin_size=10``) to override.
    """
    success_df = df[df['success']].copy()
    if success_df.empty:
        fig, ax = plt.subplots()
        ax.text(0.5, 0.5, 'No successful trials', ha='center', va='center')
        _maybe_save(fig, output_dir, f'scaling_vs_{x}.png', save,
                    subdir=f'figures/scaling/{metric}', fmt=fmt)
        return fig

    palette = algo_palette or _algo_palette(success_df['algorithm'].unique())
    fig, ax = plt.subplots(figsize=(12, 5))

    for algo, grp in success_df.groupby('algorithm'):
        color = palette[algo]
        xvals = grp[x].dropna()
        if xvals.empty:
            continue

        # ── Auto bin size ─────────────────────────────────────────────────
        x_min, x_max = float(xvals.min()), float(xvals.max())
        effective_bin = bin_size or max(1, int((x_max - x_min) / 40))

        # ── Raw scatter (light, behind trend) ─────────────────────────────
        ax.scatter(grp[x], grp[metric],
                   alpha=0.12, s=6, color=color, linewidths=0)

        # ── Binned mean ± 1 std ───────────────────────────────────────────
        lo = (int(x_min) // effective_bin) * effective_bin
        hi = (int(x_max) // effective_bin + 1) * effective_bin
        bins = np.arange(lo, hi + effective_bin, effective_bin)
        centers = (bins[:-1] + bins[1:]) / 2.0

        grp = grp.copy()
        grp['_bin'] = pd.cut(grp[x], bins=bins, labels=centers).astype(float)
        agg = (grp.groupby('_bin', observed=True)[metric]
               .agg(mean='mean', std='std', n='count')
               .reset_index())
        agg['std'] = agg['std'].fillna(0)
        agg = agg[agg['n'] > 0].dropna(subset=['mean'])

        ax.plot(agg['_bin'], agg['mean'],
                color=color, linewidth=2, label=algo)
        ax.fill_between(agg['_bin'],
                        agg['mean'] - agg['std'],
                        agg['mean'] + agg['std'],
                        alpha=0.18, color=color)

    if log:
        ax.set_xscale('log')
        ax.set_yscale('log')

    ax.set_xlabel(x.replace('_', ' '))
    ax.set_ylabel(metric.replace('_', ' '))
    ax.set_title(f'Scaling: {metric.replace("_", " ")} vs {x.replace("_", " ")}')
    ax.legend(framealpha=0.9)
    ax.grid(alpha=0.3)
    plt.tight_layout()
    _maybe_save(fig, output_dir, f'scaling_vs_{x}.png', save,
                subdir=f'figures/scaling/{metric}', fmt=fmt)
    return fig


# ── 3. Density-hardness (random graphs) ─────────────────────────────────────────

def plot_density_hardness(df: pd.DataFrame,
                          metric: str = 'avg_chain_length',
                          algo_palette=None,
                          output_dir=None,
                          save: bool = False,
                          fmt: str = 'png') -> plt.Figure:
    """Line plot: metric vs graph density for random graphs, one line per (algo, n).

    Only graphs with category=='random' are included.
    """
    rand_df = df[(df['category'] == 'random') & df['success']].copy()

    fig, ax = plt.subplots(figsize=(9, 5))
    if rand_df.empty:
        ax.text(0.5, 0.5, 'No random graph data', ha='center', va='center')
        _maybe_save(fig, output_dir, 'density_hardness.png', save,
                    subdir=f'figures/scaling/{metric}', fmt=fmt)
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
    _maybe_save(fig, output_dir, 'density_hardness.png', save,
                subdir=f'figures/scaling/{metric}', fmt=fmt)
    return fig


# ── 4. Size × density heatmap ───────────────────────────────────────────────────

_HEATMAP_METRICS = frozenset({
    'avg_chain_length', 'max_chain_length', 'qubit_overhead_ratio',
    'success_rate', 'wall_time',
})

# Colormaps: for chain/qubit/time metrics lower is better → red=high=bad.
# For success_rate higher is better → green=high=good.
_HEATMAP_CMAPS = {
    'avg_chain_length':    'RdYlGn_r',
    'max_chain_length':    'RdYlGn_r',
    'qubit_overhead_ratio':'RdYlGn_r',
    'success_rate':        'RdYlGn',
    'wall_time':           'RdYlGn_r',
}

_HEATMAP_LABELS = {
    'avg_chain_length':    'Average chain length (qubits)',
    'max_chain_length':    'Max chain length (qubits)',
    'qubit_overhead_ratio':'Qubit overhead ratio',
    'success_rate':        'Success rate',
    'wall_time':           'Embedding time (s)',
    'win_rate':            'Win rate (best chain length)',
    'relative_time':       'Relative slowdown (×fastest)',
}


def plot_size_density_heatmap(
    df: pd.DataFrame,
    metric: str = 'avg_chain_length',
    graph_categories: Optional[List[str]] = None,
    algo: Optional[str] = None,
    node_bin_size: Optional[int] = 10,
    density_bin_size: Optional[float] = 0.05,
    smooth: bool = True,
    smooth_sigma: float = 1.0,
    vmin: Optional[float] = None,
    vmax: Optional[float] = None,
    x_max: Optional[float] = None,
    cmap: Optional[str] = None,
    algo_palette=None,
    output_dir=None,
    save: bool = False,
    fmt: str = 'png',
) -> plt.Figure:
    """2-D heatmap: graph size (nodes, x) × density (y), coloured by a metric.

    Each cell shows the mean of ``metric`` across all graphs and trials that
    fall within that (nodes, density) combination.  Best used with random ER
    graphs (``category == 'random'``) where size and density are both explicit
    parameters.

    When ``metric='success_rate'`` the mean is computed over *all* rows
    (including failures) so partial-success cells reflect the true rate.
    All other metrics are averaged over successful trials only.

    With one trial per graph, success rate per cell is the fraction of
    distinct graphs at that (n, density) point that produced a valid
    embedding — a meaningful estimate as long as ≥ 2 graphs share the cell.

    Args:
        df:               Derived DataFrame from ``load_batch()``.
        metric:           One of ``'avg_chain_length'``, ``'max_chain_length'``,
                          ``'qubit_overhead_ratio'``, ``'success_rate'``.
        graph_categories: Categories to include.  Defaults to ``['random']``
                          (Erdős-Rényi graphs).
        algo:             Restrict to one algorithm.  ``None`` averages over
                          all algorithms present in the filtered data.
        node_bin_size:    Bin width for the node axis.  Defaults to ``10``
                          (groups nodes 0–9, 10–19, …).  ``None`` uses exact
                          node counts (may produce very thin cells).
        density_bin_size: Bin width for the density axis.  Defaults to
                          ``0.05`` (20 bands from 0–1).  ``None`` uses exact
                          density values (rounded to 3 dp).
        smooth:           Apply Gaussian smoothing across cells before
                          plotting.  Helps reveal gradients when coverage
                          is sparse.  Default ``True``.
        smooth_sigma:     Standard deviation for the Gaussian kernel in
                          cell units.  Default ``1.0``.
        vmin, vmax:       Colour-scale limits.  Defaults to data range.
                          Pass the same values to all per-algorithm plots so
                          colour scales are comparable.
        x_max:            Override the right edge of the x-axis (node count).
                          Pass the same value to all per-algorithm plots so
                          they share the same x range for easy comparison.
                          ``None`` auto-clips to the rightmost column with data.
        cmap:             Matplotlib colormap name.  Auto-selected per metric
                          when ``None``.
        algo_palette:     Ignored (accepted for API consistency).
        output_dir:       Base output directory.
        save:             Write to disk when ``True``.
        fmt:              Image format (``'png'``, ``'pdf'``, ``'svg'``).

    Returns:
        matplotlib Figure.
    """
    if metric not in _HEATMAP_METRICS:
        raise ValueError(
            f"metric must be one of {sorted(_HEATMAP_METRICS)}, got {metric!r}"
        )

    # ── Filter ────────────────────────────────────────────────────────────────
    if graph_categories is None:
        graph_categories = ['random_er']

    fdf = df[df['category'].isin(graph_categories)].copy()

    fname_suffix = 'size_density'
    fig, ax = plt.subplots(figsize=(16, 8))

    if fdf.empty:
        ax.text(0.5, 0.5,
                f'No data for categories: {graph_categories}',
                ha='center', va='center', transform=ax.transAxes)
        _maybe_save(fig, output_dir, f'{fname_suffix}.png', save,
                    subdir=f'figures/scaling/{metric}', fmt=fmt)
        return fig

    if algo is not None:
        fdf = fdf[fdf['algorithm'] == algo]
        if fdf.empty:
            ax.text(0.5, 0.5, f'No data for algorithm {algo!r}',
                    ha='center', va='center', transform=ax.transAxes)
            _maybe_save(fig, output_dir, f'{fname_suffix}.png', save,
                        subdir=f'figures/scaling/{metric}', fmt=fmt)
            return fig

    # ── Aggregate metric ──────────────────────────────────────────────────────
    is_success = metric == 'success_rate'
    # success_rate and wall_time use all trials; other metrics use only successful
    _use_all_trials = metric in ('success_rate', 'wall_time')
    if is_success:
        agg_df = fdf.copy()
        agg_col = 'success'
    elif _use_all_trials:
        agg_df = fdf.copy()
        agg_col = metric
    else:
        if metric not in fdf.columns:
            raise ValueError(f"Column '{metric}' not found in DataFrame.")
        agg_df = fdf[fdf['success']].copy()
        agg_col = metric

    if agg_df.empty:
        ax.text(0.5, 0.5, 'No data in filtered set',
                ha='center', va='center', transform=ax.transAxes)
        _maybe_save(fig, output_dir, f'{fname_suffix}.png', save,
                    subdir=f'figures/scaling/{metric}', fmt=fmt)
        return fig

    # ── Bin axes ──────────────────────────────────────────────────────────────
    _use_log_x = metric in ('success_rate', 'wall_time')
    if node_bin_size is not None:
        n_min = max(1, int(agg_df['problem_nodes'].min()))
        n_max = int(agg_df['problem_nodes'].max())
        if n_max > n_min and _use_log_x:
            n_log_bins = max(10, min(40, int(np.log2(n_max / n_min) * 4)))
            bins = np.unique(np.geomspace(n_min, n_max + 1, n_log_bins + 1).astype(int))
            bins = sorted(set(bins))
            if len(bins) < 2:
                bins = [n_min, n_max + 1]
            labels = [np.sqrt(bins[i] * bins[i + 1]) for i in range(len(bins) - 1)]
            agg_df['_x'] = pd.cut(
                agg_df['problem_nodes'], bins=bins, labels=labels,
                include_lowest=True,
            ).astype(float)
        elif n_max > n_min:
            lo = (n_min // node_bin_size) * node_bin_size
            hi = (n_max // node_bin_size + 1) * node_bin_size
            bins = list(range(lo, hi + node_bin_size, node_bin_size))
            labels = [b + node_bin_size // 2 for b in bins[:-1]]
            agg_df['_x'] = pd.cut(
                agg_df['problem_nodes'], bins=bins, labels=labels,
            ).astype(float)
        else:
            agg_df['_x'] = agg_df['problem_nodes'].astype(float)
    else:
        agg_df['_x'] = agg_df['problem_nodes'].astype(float)

    if density_bin_size is not None:
        lo = (agg_df['problem_density'].min() // density_bin_size) * density_bin_size
        hi = min(1.0 + density_bin_size,
                 (agg_df['problem_density'].max() // density_bin_size + 1) * density_bin_size)
        d_bins = list(np.arange(lo, hi + density_bin_size / 2, density_bin_size))
        d_labels = [round(b + density_bin_size / 2, 4) for b in d_bins[:-1]]
        agg_df['_y'] = pd.cut(
            agg_df['problem_density'], bins=d_bins, labels=d_labels,
        ).astype(float)
    else:
        agg_df['_y'] = agg_df['problem_density'].round(3)

    agg_df = agg_df.dropna(subset=['_x', '_y'])

    # ── Pivot ─────────────────────────────────────────────────────────────────
    pivot = (
        agg_df.groupby(['_y', '_x'], observed=True)[agg_col]
        .mean()
        .unstack(level='_x')
    )
    pivot = pivot.sort_index(ascending=True).sort_index(axis=1, ascending=True)

    X = pivot.columns.values.astype(float)
    Y = pivot.index.values.astype(float)
    Z = pivot.values  # shape: (n_densities, n_nodes)

    # ── Gaussian smoothing (NaN-aware) ────────────────────────────────────────
    if smooth and smooth_sigma > 0:
        from scipy.ndimage import gaussian_filter
        # Treat NaN as 0-weight; smooth values and weights separately then divide
        Z_filled = np.where(np.isnan(Z), 0.0, Z)
        W        = (~np.isnan(Z)).astype(float)
        Z_sm     = gaussian_filter(Z_filled, sigma=smooth_sigma)
        W_sm     = gaussian_filter(W,        sigma=smooth_sigma)
        with np.errstate(invalid='ignore'):
            Z = np.where(W_sm > 0.05, Z_sm / W_sm, np.nan)

    # ── Plot ──────────────────────────────────────────────────────────────────
    chosen_cmap = cmap or _HEATMAP_CMAPS[metric]
    cmap_obj = plt.get_cmap(chosen_cmap).copy()
    cmap_obj.set_bad('lightgray')   # NaN cells shown in gray

    im = ax.pcolormesh(X, Y, Z, cmap=cmap_obj, vmin=vmin, vmax=vmax,
                       shading='nearest')

    cb = plt.colorbar(im, ax=ax)
    cb.set_label(_HEATMAP_LABELS.get(metric, metric))

    if _use_log_x:
        ax.set_xscale('log')
    # Clip x-axis to the range that actually has data
    valid_cols = np.where(~np.all(np.isnan(Z), axis=0))[0]
    if valid_cols.size:
        if _use_log_x:
            x_left = X[valid_cols[0]]
            x_right = float(x_max) if x_max is not None else X[valid_cols[-1]]
            ax.set_xlim(x_left * 0.8, x_right * 1.2)
        else:
            x_margin = (X[1] - X[0]) if len(X) > 1 else 5.0
            x_right = float(x_max) if x_max is not None else X[valid_cols[-1]]
            ax.set_xlim(X[valid_cols[0]] - x_margin, x_right + x_margin)

    ax.set_xlabel('Number of nodes')
    ax.set_ylabel('Density')

    cats_str = ', '.join(graph_categories)
    algo_str = f' — {algo}' if algo else ' — all algorithms'
    ax.set_title(
        f'{_HEATMAP_LABELS.get(metric, metric)} '
        f'vs graph size and density\n({cats_str}{algo_str})'
    )

    plt.tight_layout()
    algo_tag = f'_{algo}' if algo else ''
    _maybe_save(fig, output_dir, f'{fname_suffix}{algo_tag}.png', save,
                subdir=f'figures/scaling/{metric}', fmt=fmt)
    return fig


def plot_size_density_heatmap_grid(
    df: pd.DataFrame,
    metric: str = 'avg_chain_length',
    graph_categories: Optional[List[str]] = None,
    node_bin_size: Optional[int] = 10,
    density_bin_size: Optional[float] = 0.05,
    smooth: bool = True,
    smooth_sigma: float = 1.0,
    vmin: Optional[float] = None,
    vmax: Optional[float] = None,
    x_max: Optional[float] = None,
    cmap: Optional[str] = None,
    algo_palette=None,
    output_dir=None,
    save: bool = False,
    fmt: str = 'png',
) -> plt.Figure:
    """Grid of per-algorithm heatmaps for side-by-side comparison.

    Creates one subplot per algorithm, all sharing the same colour scale
    and axis ranges for direct visual comparison.

    Args:
        Same as ``plot_size_density_heatmap`` except ``algo`` is removed —
        all algorithms in the data are plotted.

    Returns:
        matplotlib Figure with the grid of heatmaps.
    """
    if metric not in _HEATMAP_METRICS:
        raise ValueError(
            f"metric must be one of {sorted(_HEATMAP_METRICS)}, got {metric!r}"
        )

    if graph_categories is None:
        graph_categories = ['random_er']

    fdf = df[df['category'].isin(graph_categories)].copy()

    fname_suffix = 'size_density_grid'

    if fdf.empty:
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.text(0.5, 0.5,
                f'No data for categories: {graph_categories}',
                ha='center', va='center', transform=ax.transAxes)
        _maybe_save(fig, output_dir, f'{fname_suffix}.png', save,
                    subdir=f'figures/scaling/{metric}', fmt=fmt)
        return fig

    algos = sorted(fdf['algorithm'].unique())
    n_algos = len(algos)

    if n_algos == 0:
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.text(0.5, 0.5, 'No algorithms in filtered data',
                ha='center', va='center', transform=ax.transAxes)
        _maybe_save(fig, output_dir, f'{fname_suffix}.png', save,
                    subdir=f'figures/scaling/{metric}', fmt=fmt)
        return fig

    # Grid layout: up to 3 columns for a balanced look (e.g. 5 algos → 3+2)
    n_cols = min(n_algos, 3)
    n_rows = (n_algos + n_cols - 1) // n_cols
    fig, axes = plt.subplots(n_rows, n_cols,
                             figsize=(5 * n_cols, 4.5 * n_rows),
                             squeeze=False)

    # ── Compute shared colour limits if not provided ─────────────────────
    is_success = metric == 'success_rate'
    _use_all_trials = metric in ('success_rate', 'wall_time')
    _use_log_x = metric in ('success_rate', 'wall_time')
    if is_success:
        agg_col = 'success'
        global_agg = fdf.copy()
    elif _use_all_trials:
        agg_col = metric
        global_agg = fdf.copy()
    else:
        agg_col = metric
        global_agg = fdf[fdf['success']].copy()

    if vmin is None or vmax is None:
        if is_success:
            _auto_vmin, _auto_vmax = 0.0, 1.0
        elif not global_agg.empty and agg_col in global_agg.columns:
            _auto_vmin = float(global_agg[agg_col].min())
            _auto_vmax = float(global_agg[agg_col].max())
        else:
            _auto_vmin, _auto_vmax = 0.0, 1.0
        if vmin is None:
            vmin = _auto_vmin
        if vmax is None:
            vmax = _auto_vmax

    # Shared x_max
    if x_max is None and not global_agg.empty:
        x_max = float(global_agg['problem_nodes'].max())

    chosen_cmap = cmap or _HEATMAP_CMAPS[metric]
    cmap_obj = plt.get_cmap(chosen_cmap).copy()
    cmap_obj.set_bad('lightgray')

    last_im = None

    for idx, algo in enumerate(algos):
        row, col = divmod(idx, n_cols)
        ax = axes[row][col]

        adf = fdf[fdf['algorithm'] == algo].copy()
        if is_success or _use_all_trials:
            agg_df = adf.copy()
        else:
            agg_df = adf[adf['success']].copy()

        if agg_df.empty:
            ax.text(0.5, 0.5, 'No data', ha='center', va='center',
                    transform=ax.transAxes, fontsize=9)
            ax.set_title(algo, fontsize=10, fontweight='bold')
            continue

        # Bin nodes (log-spaced only for success_rate)
        if node_bin_size is not None:
            n_min = max(1, int(agg_df['problem_nodes'].min()))
            n_max = int(agg_df['problem_nodes'].max())
            if n_max > n_min and _use_log_x:
                n_log_bins = max(10, min(40, int(np.log2(n_max / n_min) * 4)))
                nbins = np.unique(np.geomspace(n_min, n_max + 1, n_log_bins + 1).astype(int))
                nbins = sorted(set(nbins))
                if len(nbins) < 2:
                    nbins = [n_min, n_max + 1]
                nlabels = [np.sqrt(nbins[i] * nbins[i + 1]) for i in range(len(nbins) - 1)]
                agg_df['_x'] = pd.cut(
                    agg_df['problem_nodes'], bins=nbins, labels=nlabels,
                    include_lowest=True,
                ).astype(float)
            elif n_max > n_min:
                lo = (n_min // node_bin_size) * node_bin_size
                hi = (n_max // node_bin_size + 1) * node_bin_size
                nbins = list(range(lo, hi + node_bin_size, node_bin_size))
                nlabels = [b + node_bin_size // 2 for b in nbins[:-1]]
                agg_df['_x'] = pd.cut(
                    agg_df['problem_nodes'], bins=nbins, labels=nlabels,
                ).astype(float)
            else:
                agg_df['_x'] = agg_df['problem_nodes'].astype(float)
        else:
            agg_df['_x'] = agg_df['problem_nodes'].astype(float)

        if density_bin_size is not None:
            dlo = (agg_df['problem_density'].min() // density_bin_size) * density_bin_size
            dhi = min(1.0 + density_bin_size,
                      (agg_df['problem_density'].max() // density_bin_size + 1) * density_bin_size)
            d_bins = list(np.arange(dlo, dhi + density_bin_size / 2, density_bin_size))
            d_labels = [round(b + density_bin_size / 2, 4) for b in d_bins[:-1]]
            agg_df['_y'] = pd.cut(
                agg_df['problem_density'], bins=d_bins, labels=d_labels,
            ).astype(float)
        else:
            agg_df['_y'] = agg_df['problem_density'].round(3)

        agg_df = agg_df.dropna(subset=['_x', '_y'])
        if agg_df.empty:
            ax.text(0.5, 0.5, 'No binned data', ha='center', va='center',
                    transform=ax.transAxes, fontsize=9)
            ax.set_title(algo, fontsize=10, fontweight='bold')
            continue

        pivot = (
            agg_df.groupby(['_y', '_x'], observed=True)[agg_col]
            .mean()
            .unstack(level='_x')
        )
        pivot = pivot.sort_index(ascending=True).sort_index(axis=1, ascending=True)

        X = pivot.columns.values.astype(float)
        Y = pivot.index.values.astype(float)
        Z = pivot.values

        if smooth and smooth_sigma > 0:
            from scipy.ndimage import gaussian_filter
            Z_filled = np.where(np.isnan(Z), 0.0, Z)
            W = (~np.isnan(Z)).astype(float)
            Z_sm = gaussian_filter(Z_filled, sigma=smooth_sigma)
            W_sm = gaussian_filter(W, sigma=smooth_sigma)
            with np.errstate(invalid='ignore'):
                Z = np.where(W_sm > 0.05, Z_sm / W_sm, np.nan)

        im = ax.pcolormesh(X, Y, Z, cmap=cmap_obj, vmin=vmin, vmax=vmax,
                           shading='nearest')
        last_im = im

        if _use_log_x:
            ax.set_xscale('log')
        # Shared x range
        valid_cols = np.where(~np.all(np.isnan(Z), axis=0))[0]
        if valid_cols.size:
            if _use_log_x:
                x_left = X[valid_cols[0]]
                x_right = float(x_max) if x_max is not None else X[valid_cols[-1]]
                ax.set_xlim(x_left * 0.8, x_right * 1.2)
            else:
                x_margin = (X[1] - X[0]) if len(X) > 1 else 5.0
                x_right = float(x_max) if x_max is not None else X[valid_cols[-1]]
                ax.set_xlim(X[valid_cols[0]] - x_margin, x_right + x_margin)

        ax.set_title(algo, fontsize=10, fontweight='bold')
        if col == 0:
            ax.set_ylabel('Density')
        else:
            ax.set_ylabel('')
        if row == n_rows - 1:
            ax.set_xlabel('Nodes')
        else:
            ax.set_xlabel('')

    # Hide unused subplots
    for idx in range(n_algos, n_rows * n_cols):
        row, col = divmod(idx, n_cols)
        axes[row][col].set_visible(False)

    # Shared colorbar
    if last_im is not None:
        fig.subplots_adjust(right=0.88)
        cbar_ax = fig.add_axes([0.90, 0.15, 0.02, 0.7])
        cb = fig.colorbar(last_im, cax=cbar_ax)
        cb.set_label(_HEATMAP_LABELS.get(metric, metric))

    cats_str = ', '.join(graph_categories)
    fig.suptitle(
        f'{_HEATMAP_LABELS.get(metric, metric)} vs size × density ({cats_str})',
        fontsize=13, y=1.01,
    )

    plt.tight_layout(rect=[0, 0, 0.88, 0.98])
    _maybe_save(fig, output_dir, f'{fname_suffix}.png', save,
                subdir=f'figures/scaling/{metric}', fmt=fmt)
    return fig


# ── 5. Pareto frontier ───────────────────────────────────────────────────────────

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
                save: bool = False,
                fmt: str = 'png') -> plt.Figure:
    """Scatter: one point per (algorithm, problem), Pareto frontier highlighted.

    Uses per-problem mean across successful trials.
    """
    success_df = df[df['success']].copy()
    if success_df.empty:
        fig, ax = plt.subplots()
        ax.text(0.5, 0.5, 'No successful trials', ha='center', va='center')
        _maybe_save(fig, output_dir, f'pareto_{x}_vs_{y}.png', save,
                    subdir='figures', fmt=fmt)
        return fig

    agg = success_df.groupby(['algorithm', 'graph_name'])[[x, y]].mean().reset_index()
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
                subdir='figures', fmt=fmt)
    return fig


# ── 5. Distribution violin ───────────────────────────────────────────────────────

def plot_distributions(df: pd.DataFrame,
                       metric: str = 'avg_chain_length',
                       algo_palette=None,
                       output_dir=None,
                       save: bool = False,
                       fmt: str = 'png') -> plt.Figure:
    """Violin plot of `metric` per algorithm (successful trials only)."""
    success_df = df[df['success']].copy()
    _dist_metric_dir = 'chain_length' if metric == 'avg_chain_length' else metric
    if success_df.empty or metric not in success_df.columns:
        fig, ax = plt.subplots()
        ax.text(0.5, 0.5, 'No data', ha='center', va='center')
        _maybe_save(fig, output_dir, 'violin.png', save,
                    subdir=f'figures/distributions/{_dist_metric_dir}', fmt=fmt)
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
    if metric == 'wall_time':
        ax.set_yscale('log')
        ax.set_ylabel('Embedding time (s)')
    ax.set_title(f'Distribution of {metric.replace("_", " ")} per algorithm')
    ax.grid(axis='y', alpha=0.3, which='both')
    plt.xticks(rotation=20, ha='right')
    plt.tight_layout()

    _maybe_save(fig, output_dir, 'violin.png', save,
                subdir=f'figures/distributions/{_dist_metric_dir}', fmt=fmt)
    return fig


# ── Category-balanced summary bars ───────────────────────────────────────────────

def plot_balanced_summary(df: pd.DataFrame,
                          algo_palette=None,
                          output_dir=None,
                          save: bool = False,
                          fmt: str = 'png') -> plt.Figure:
    """Two-panel bar chart: macro-averaged success rate and chain length.

    Each graph category contributes equally (average of per-category
    averages) so that large categories don't dominate the overall numbers.
    """
    algos = sorted(df['algorithm'].unique())
    palette = algo_palette or _algo_palette(algos)
    cats = sorted(df['category'].unique())

    # ── Success rate: macro-average ──
    sr_per_cat = (
        df.groupby(['algorithm', 'category'])['success']
        .mean()
        .unstack(level='category')
    )
    macro_sr = sr_per_cat.mean(axis=1).reindex(algos)

    # ── Chain length: macro-average (successful trials only) ──
    sdf = df[df['success']]
    cl_per_cat = (
        sdf.groupby(['algorithm', 'category'])['avg_chain_length']
        .mean()
        .unstack(level='category')
    )
    macro_cl = cl_per_cat.mean(axis=1).reindex(algos)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))

    # Success rate bars
    colors = [palette[a] for a in algos]
    bars1 = ax1.bar(algos, macro_sr.values, color=colors)
    ax1.set_ylabel('Success rate')
    ax1.set_title('Category-balanced success rate')
    ax1.set_ylim(0, 1.05)
    for bar, val in zip(bars1, macro_sr.values):
        ax1.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.01,
                 f'{val:.1%}', ha='center', va='bottom', fontsize=9)
    ax1.grid(axis='y', alpha=0.3)
    ax1.tick_params(axis='x', rotation=20)

    # Chain length bars
    bars2 = ax2.bar(algos, macro_cl.values, color=colors)
    ax2.set_ylabel('Avg chain length')
    ax2.set_title('Category-balanced avg chain length\n(successful only)')
    for bar, val in zip(bars2, macro_cl.values):
        if not np.isnan(val):
            ax2.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.1,
                     f'{val:.2f}', ha='center', va='bottom', fontsize=9)
    ax2.grid(axis='y', alpha=0.3)
    ax2.tick_params(axis='x', rotation=20)

    plt.tight_layout()
    _maybe_save(fig, output_dir, 'balanced_summary.png', save,
                subdir='figures/distributions/summary', fmt=fmt)
    return fig


def plot_balanced_time(df: pd.DataFrame,
                       algo_palette=None,
                       output_dir=None,
                       save: bool = False,
                       fmt: str = 'png') -> plt.Figure:
    """Side-by-side median vs mean category-balanced embedding time.

    Shows how much timeouts and outliers inflate the mean relative to
    the median, making the impact of extreme values immediately visible.
    """
    algos = sorted(df['algorithm'].unique())
    palette = algo_palette or _algo_palette(algos)
    colors = [palette[a] for a in algos]

    # Per-category median, then macro-average across categories
    median_per_cat = (
        df.groupby(['algorithm', 'category'])['wall_time']
        .median()
        .unstack(level='category')
    )
    macro_median = median_per_cat.mean(axis=1).reindex(algos)

    # Per-category mean, then macro-average across categories
    mean_per_cat = (
        df.groupby(['algorithm', 'category'])['wall_time']
        .mean()
        .unstack(level='category')
    )
    macro_mean = mean_per_cat.mean(axis=1).reindex(algos)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))

    # Median
    bars1 = ax1.bar(algos, macro_median.values, color=colors)
    ax1.set_ylabel('Embedding time (s)')
    ax1.set_title('Category-balanced embedding time\n(median per category)')
    ax1.set_yscale('log')
    for bar, val in zip(bars1, macro_median.values):
        if not np.isnan(val):
            ax1.text(bar.get_x() + bar.get_width() / 2, bar.get_height() * 1.15,
                     f'{val:.3f}s', ha='center', va='bottom', fontsize=9)
    ax1.grid(axis='y', alpha=0.3, which='both')
    ax1.tick_params(axis='x', rotation=20)

    # Mean
    bars2 = ax2.bar(algos, macro_mean.values, color=colors)
    ax2.set_ylabel('Embedding time (s)')
    ax2.set_title('Category-balanced embedding time\n(mean per category)')
    ax2.set_yscale('log')
    for bar, val in zip(bars2, macro_mean.values):
        if not np.isnan(val):
            ax2.text(bar.get_x() + bar.get_width() / 2, bar.get_height() * 1.15,
                     f'{val:.2f}s', ha='center', va='bottom', fontsize=9)
    ax2.grid(axis='y', alpha=0.3, which='both')
    ax2.tick_params(axis='x', rotation=20)

    # Match y-axis range so the visual difference is clear
    ymin = min(ax1.get_ylim()[0], ax2.get_ylim()[0])
    ymax = max(ax1.get_ylim()[1], ax2.get_ylim()[1])
    ax1.set_ylim(ymin, ymax)
    ax2.set_ylim(ymin, ymax)

    plt.tight_layout()
    _maybe_save(fig, output_dir, 'balanced_time.png', save,
                subdir='figures/distributions/wall_time', fmt=fmt)
    return fig


def plot_per_topology_summary(df: pd.DataFrame,
                              algo_palette=None,
                              output_dir=None,
                              save: bool = False,
                              fmt: str = 'png') -> List[plt.Figure]:
    """Per-topology balanced summary: one figure per topology.

    Each figure has 3 panels: category-balanced success rate, chain length,
    and median embedding time for that topology only.
    """
    if 'topology_name' not in df.columns and 'base_topology' not in df.columns:
        return []

    topo_col = 'base_topology' if 'base_topology' in df.columns else 'topology_name'
    topos = sorted(df[topo_col].unique())
    algos = sorted(df['algorithm'].unique())
    palette = algo_palette or _algo_palette(algos)
    colors = [palette[a] for a in algos]
    figs = []

    for topo in topos:
        tdf = df[df[topo_col] == topo]
        if tdf.empty:
            continue

        cats = sorted(tdf['category'].unique())

        # Success rate
        sr_per_cat = tdf.groupby(['algorithm', 'category'])['success'].mean().unstack(level='category')
        macro_sr = sr_per_cat.mean(axis=1).reindex(algos)

        # Chain length (successful only)
        sdf = tdf[tdf['success']]
        if not sdf.empty:
            cl_per_cat = sdf.groupby(['algorithm', 'category'])['avg_chain_length'].mean().unstack(level='category')
            macro_cl = cl_per_cat.mean(axis=1).reindex(algos)
        else:
            macro_cl = pd.Series(np.nan, index=algos)

        # Embedding time (median)
        et_per_cat = tdf.groupby(['algorithm', 'category'])['wall_time'].median().unstack(level='category')
        macro_et = et_per_cat.mean(axis=1).reindex(algos)

        fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(17, 5))
        fig.suptitle(f'Topology: {topo}', fontsize=14, fontweight='bold')

        # Success rate
        bars1 = ax1.bar(algos, macro_sr.values, color=colors)
        ax1.set_ylabel('Success rate')
        ax1.set_title('Category-balanced success rate')
        ax1.set_ylim(0, 1.05)
        for bar, val in zip(bars1, macro_sr.values):
            if not np.isnan(val):
                ax1.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.01,
                         f'{val:.1%}', ha='center', va='bottom', fontsize=9)
        ax1.grid(axis='y', alpha=0.3)
        ax1.tick_params(axis='x', rotation=20)

        # Chain length
        bars2 = ax2.bar(algos, macro_cl.values, color=colors)
        ax2.set_ylabel('Avg chain length')
        ax2.set_title('Category-balanced chain length\n(successful only)')
        for bar, val in zip(bars2, macro_cl.values):
            if not np.isnan(val):
                ax2.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.1,
                         f'{val:.2f}', ha='center', va='bottom', fontsize=9)
        ax2.grid(axis='y', alpha=0.3)
        ax2.tick_params(axis='x', rotation=20)

        # Embedding time (median, log scale)
        bars3 = ax3.bar(algos, macro_et.values, color=colors)
        ax3.set_ylabel('Median embedding time (s)')
        ax3.set_title('Category-balanced embedding time\n(median, all trials)')
        ax3.set_yscale('log')
        for bar, val in zip(bars3, macro_et.values):
            if not np.isnan(val):
                ax3.text(bar.get_x() + bar.get_width() / 2, bar.get_height() * 1.15,
                         f'{val:.3f}s', ha='center', va='bottom', fontsize=9)
        ax3.grid(axis='y', alpha=0.3, which='both')
        ax3.tick_params(axis='x', rotation=20)

        plt.tight_layout(rect=[0, 0, 1, 0.95])
        _maybe_save(fig, output_dir, f'summary_{topo}.png', save,
                    subdir='figures/topology', fmt=fmt)
        figs.append(fig)

    return figs


# ── 6. Head-to-head scatter ──────────────────────────────────────────────────────

def plot_head_to_head(df: pd.DataFrame,
                      algo_a: str,
                      algo_b: str,
                      metric: str = 'avg_chain_length',
                      algo_palette=None,
                      output_dir=None,
                      save: bool = False,
                      fmt: str = 'png') -> plt.Figure:
    """Scatter: per-problem mean metric for algo_a (x) vs algo_b (y).

    Points below the diagonal → algo_a wins (lower is better for most metrics).
    """
    success_df = df[df['success']].copy()
    per_problem = (
        success_df
        .groupby(['algorithm', 'graph_name'])[metric]
        .mean()
        .unstack(level='algorithm')
    )

    fig, ax = plt.subplots(figsize=(6, 6))

    if algo_a not in per_problem.columns or algo_b not in per_problem.columns:
        ax.text(0.5, 0.5, f'Missing data for {algo_a} or {algo_b}',
                ha='center', va='center')
        _maybe_save(fig, output_dir, f'scatter_{algo_a}_vs_{algo_b}.png', save,
                    subdir='figures/pairwise', fmt=fmt)
        return fig

    common = per_problem[[algo_a, algo_b]].dropna()
    if common.empty:
        ax.text(0.5, 0.5, 'No paired problems', ha='center', va='center')
        _maybe_save(fig, output_dir, f'scatter_{algo_a}_vs_{algo_b}.png', save,
                    subdir='figures/pairwise', fmt=fmt)
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
                subdir='figures/pairwise', fmt=fmt)
    return fig


# ── 7. Consistency (CV) ──────────────────────────────────────────────────────────

def plot_consistency(df: pd.DataFrame,
                     algo_palette=None,
                     output_dir=None,
                     save: bool = False,
                     fmt: str = 'png') -> plt.Figure:
    """Two-panel bar chart: coefficient of variation of time and chain length per algo.

    Lower CV → more consistent.  Computed per (algo, problem) pair, then averaged.
    Only problems with ≥ 2 successful trials contribute.
    """
    success_df = df[df['success']].copy()

    def _mean_cv(metric):
        cv_per_prob = (
            success_df.groupby(['algorithm', 'graph_name'])[metric]
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
                subdir='figures/distributions/chain_length', fmt=fmt)
    return fig


# ── 8. Topology comparison ───────────────────────────────────────────────────────

def plot_topology_comparison(df: pd.DataFrame,
                              metric: str = 'avg_chain_length',
                              algo_palette=None,
                              output_dir=None,
                              save: bool = False,
                              fmt: str = 'png') -> plt.Figure:
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
                subdir='figures/topology', fmt=fmt)
    return fig


# ── 9. Problem deep dive ─────────────────────────────────────────────────────────

def plot_problem_deep_dive(df: pd.DataFrame,
                            graph_name: str,
                            algo_palette=None,
                            output_dir=None,
                            save: bool = False,
                            fmt: str = 'png') -> plt.Figure:
    """Two-panel bar chart for a single problem: time and chain length per algorithm."""
    prob_df = df[df['graph_name'] == graph_name].copy()

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 4))

    if prob_df.empty:
        for ax in (ax1, ax2):
            ax.text(0.5, 0.5, f'No data for {graph_name}', ha='center', va='center')
        _maybe_save(fig, output_dir, f'deep_dive_{graph_name}.png', save,
                    subdir='figures', fmt=fmt)
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
        ax.set_title(f'{ylabel}\n({graph_name})')
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

    plt.suptitle(f'Deep dive: {graph_name}')
    plt.tight_layout()
    fname = f'deep_dive_{graph_name.replace("/", "_")}.png'
    _maybe_save(fig, output_dir, fname, save, subdir='figures', fmt=fmt)
    return fig


# ── 10. Chain length distribution ────────────────────────────────────────────────

def plot_chain_distribution(df: pd.DataFrame,
                             algo_palette=None,
                             output_dir=None,
                             save: bool = False,
                             fmt: str = 'png') -> plt.Figure:
    """Overlaid KDE of avg_chain_length per algorithm (successful trials only)."""
    success_df = df[df['success']].copy()
    if success_df.empty:
        fig, ax = plt.subplots()
        ax.text(0.5, 0.5, 'No successful trials', ha='center', va='center')
        _maybe_save(fig, output_dir, 'chain_length_kde.png', save,
                    subdir='figures/distributions', fmt=fmt)
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
    _maybe_save(fig, output_dir, 'kde.png', save,
                subdir='figures/distributions/chain_length', fmt=fmt)
    return fig


# ── 11. Win rate matrix ──────────────────────────────────────────────────────────

def plot_win_rate_matrix(df, metric='avg_chain_length', lower_is_better=True,
                         output_dir=None, save=False, fmt='png'):
    """Heatmap of pairwise win rates between algorithms."""
    from ember_qc_analysis.statistics import win_rate_matrix
    wm = win_rate_matrix(df, metric, lower_is_better)
    if wm.empty:
        fig, ax = plt.subplots()
        ax.text(0.5, 0.5, 'No data', ha='center', va='center')
        _maybe_save(fig, output_dir, 'win_rate_matrix.png', save, subdir='figures/pairwise', fmt=fmt)
        return fig
    fig, ax = plt.subplots(figsize=(max(5, len(wm) * 1.2), max(4, len(wm) * 1.0)))
    # Convert to percent for display
    wm_pct = wm * 100
    sns.heatmap(wm_pct, ax=ax, annot=True, fmt='.0f', cmap='RdYlGn',
                vmin=0, vmax=100, linewidths=0.5,
                cbar_kws={'label': '% problems won'})
    ax.set_title(f'Win rate matrix ({metric.replace("_"," ")})\n(row algo wins against col algo)')
    plt.tight_layout()
    _maybe_save(fig, output_dir, 'win_rate_matrix.png', save, subdir='figures/pairwise', fmt=fmt)
    return fig


# ── 12. Success heatmap ──────────────────────────────────────────────────────────

_MAX_GRAPH_HEATMAP = 300  # beyond this a per-graph heatmap is unreadable


def plot_success_heatmap(df, output_dir=None, save=False, fmt='png'):
    """Heatmap: algorithm × graph, cell = success rate across trials."""
    algos = sorted(df['algorithm'].unique())
    graphs = sorted(df['graph_name'].unique())

    if len(graphs) > _MAX_GRAPH_HEATMAP:
        fig, ax = plt.subplots(figsize=(8, 2))
        ax.text(0.5, 0.5,
                f'Too many graphs ({len(graphs):,}) for per-graph heatmap.\n'
                'Use plot_success_by_nodes() or plot_success_by_density() instead.',
                ha='center', va='center', fontsize=10)
        ax.axis('off')
        _maybe_save(fig, output_dir, 'success_rate_heatmap.png', save,
                    subdir='figures/success', fmt=fmt)
        return fig

    # Vectorised: groupby instead of O(algos × graphs) nested loop
    agg = df.groupby(['algorithm', 'graph_name'])['success'].agg(
        n_ok='sum', n_total='count'
    ).reset_index()
    agg['rate'] = agg['n_ok'] / agg['n_total'].replace(0, float('nan'))
    agg['label'] = agg.apply(
        lambda r: f"{int(r.n_ok)}/{int(r.n_total)}"
        if r.n_total <= 5 else f"{r.rate:.0%}", axis=1
    )
    data  = agg.pivot(index='algorithm', columns='graph_name', values='rate').reindex(index=algos, columns=graphs)
    annot = agg.pivot(index='algorithm', columns='graph_name', values='label').reindex(index=algos, columns=graphs).fillna('')

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
    _maybe_save(fig, output_dir, 'success_rate_heatmap.png', save, subdir='figures/success', fmt=fmt)
    return fig


# ── 13. Success by nodes ─────────────────────────────────────────────────────────

def plot_success_by_nodes(df, algo_palette=None, output_dir=None, save=False, fmt='png'):
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
    ax.set_xscale('log')
    ax.set_title('Success rate vs graph size')
    ax.legend(framealpha=0.9, bbox_to_anchor=(1.02, 1), loc='upper left')
    ax.grid(alpha=0.3, which='both')
    plt.tight_layout()
    _maybe_save(fig, output_dir, 'success_rate_by_nodes.png', save, subdir='figures/success', fmt=fmt)
    return fig


# ── 14. Success by density ───────────────────────────────────────────────────────

def plot_success_by_density(df, algo_palette=None, output_dir=None, save=False, fmt='png'):
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
    _maybe_save(fig, output_dir, 'success_rate_by_density.png', save, subdir='figures/success', fmt=fmt)
    return fig


# ── Graph-indexed helpers ────────────────────────────────────────────────────────

def _graph_jitter(graph_id: str, magnitude: float) -> float:
    """Deterministic jitter for a graph, seeded from its ID string."""
    seed = int(hashlib.md5(graph_id.encode()).hexdigest(), 16) % (2 ** 32)
    rng = np.random.default_rng(seed)
    return float(rng.uniform(-magnitude, magnitude))


def _category_of(graph_name: str) -> str:
    """Quick category lookup without importing loader (avoids circular)."""
    from ember_qc_analysis.loader import infer_category
    return infer_category(graph_name)


def _draw_chain_dots_categorical(ax, df, graphs, algos, palette, markers,
                                  metric='avg_chain_length'):
    """Draw dot plot on ax with categorical x positions for the given graphs."""
    x_pos = {g: i for i, g in enumerate(graphs)}
    categories = [_category_of(g) for g in graphs]

    graph_set = set(graphs)
    for algo in algos:
        adf = df[(df['algorithm'] == algo) & df['graph_name'].isin(graph_set)].copy()
        adf = adf.dropna(subset=[metric])
        if adf.empty:
            continue
        adf['_x'] = adf['graph_name'].map(x_pos)
        adf = adf.dropna(subset=['_x'])
        xs_trial = adf['_x'].tolist()
        ys_trial = adf[metric].tolist()
        means = adf.groupby('_x')[metric].mean()
        xs_mean = means.index.tolist()
        ys_mean = means.values.tolist()
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
                              metric='avg_chain_length',
                              output_dir=None, save=False, fmt='png'):
    """Dot plot: chain length metric per graph instance.

    x_mode:  'by_graph_id' (categorical) | 'by_n_nodes' (numeric) | 'by_density' (numeric)
    metric:  column to plot; defaults to 'avg_chain_length'. Pass 'max_chain_length' for
             the max-chain variant.
    Shows per-trial dots (small, semi-transparent) + per-algorithm mean marker (diamond).
    Each algorithm only appears where it succeeded — absence is itself the signal.
    """
    success_df = df[df['success']].copy()
    # Drop rows where the requested metric is NaN (pre-SQLite batches may have nulls)
    if metric in success_df.columns:
        success_df = success_df.dropna(subset=[metric])

    fname = 'chain_length.png' if metric == 'avg_chain_length' else f'{metric}.png'
    ylabel = 'Avg chain length' if metric == 'avg_chain_length' else metric.replace('_', ' ').title()

    if success_df.empty:
        fig, ax = plt.subplots()
        ax.text(0.5, 0.5, 'No successful trials', ha='center', va='center')
        _maybe_save(fig, output_dir, fname, save,
                    subdir=f'figures/graph_indexed/{x_mode}', fmt=fmt)
        return fig

    algos = sorted(success_df['algorithm'].unique())
    palette = algo_palette or _algo_palette(algos)
    markers = _algo_markers(algos)

    filt_df = success_df
    graphs = sorted(filt_df['graph_name'].unique())
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
                _draw_chain_dots_categorical(ax, filt_df, cat_graphs, algos, palette, markers,
                                             metric=metric)
                ax.set_title(cat, fontsize=10)
                ax.set_xlabel('')
            axes[0].set_ylabel(ylabel)
            handles = [mpatches.Patch(color=palette[a], label=a) for a in algos]
            fig.legend(handles=handles, bbox_to_anchor=(1.01, 0.9), loc='upper left',
                       framealpha=0.9, fontsize=8)
            fig.suptitle(f'{ylabel} by graph (successful trials only)')
        else:
            width = max(14, n_graphs * 0.55)
            fig, ax = plt.subplots(figsize=(width, 5))
            _draw_chain_dots_categorical(ax, filt_df, graphs, algos, palette, markers,
                                         metric=metric)
            ax.set_ylabel(ylabel)
            ax.set_title(f'{ylabel} by graph (successful trials only)')
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
            x_trial = [row[x_col] + _graph_jitter(row['graph_name'], jitter_mag)
                       for _, row in adf.iterrows()]
            ax.scatter(x_trial, adf[metric],
                       color=palette[algo], marker=markers[algo],
                       alpha=0.35, s=25, zorder=2)
            # Per-graph mean
            means = adf.groupby('graph_name').agg(
                {x_col: 'first', metric: 'mean'}
            )
            x_mean = [xv + _graph_jitter(gid, jitter_mag)
                      for gid, xv in zip(means.index, means[x_col])]
            ax.scatter(x_mean, means[metric],
                       color=palette[algo], marker='D', s=70,
                       label=algo, zorder=3, edgecolors='black', linewidths=0.5)
        ax.set_xlabel(xlabel)
        ax.set_ylabel(ylabel)
        ax.set_title(f'{ylabel} vs {xlabel.lower()} (successful trials only)')
        ax.legend(bbox_to_anchor=(1.02, 1), loc='upper left', framealpha=0.9, fontsize=9)
        ax.grid(alpha=0.3)

    plt.tight_layout()
    _maybe_save(fig, output_dir, fname, save,
                subdir=f'figures/graph_indexed/{x_mode}', fmt=fmt)
    return fig


# ── 16. Graph-indexed embedding time ────────────────────────────────────────────

def plot_graph_indexed_time(df, x_mode='by_graph_id', algo_palette=None,
                             output_dir=None, save=False, fmt='png'):
    """Dot plot: wall_time per graph instance, log scale.

    Timeout runs appear at the timeout ceiling with a distinct marker (triangle up).
    No shared-graph filter — shows all runs including timeouts.
    """
    if df.empty:
        fig, ax = plt.subplots()
        ax.text(0.5, 0.5, 'No data', ha='center', va='center')
        _maybe_save(fig, output_dir, 'embedding_time.png', save,
                    subdir=f'figures/graph_indexed/{x_mode}', fmt=fmt)
        return fig

    algos = sorted(df['algorithm'].unique())
    palette = algo_palette or _algo_palette(algos)
    markers_map = _algo_markers(algos)

    timeout_val = df['wall_time'].max() * 1.05

    if x_mode == 'by_graph_id':
        graphs = sorted(df['graph_name'].unique())
        n_graphs = len(graphs)
        width = max(14, n_graphs * 0.55)
        fig, ax = plt.subplots(figsize=(width, 5))
        x_pos = {g: i for i, g in enumerate(graphs)}
        categories = [_category_of(g) for g in graphs]

        for algo in algos:
            adf = df[df['algorithm'] == algo]
            for g in graphs:
                gdf = adf[adf['graph_name'] == g]
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
                jx = row[x_col] + _graph_jitter(str(row['graph_name']), jitter_mag)
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
                subdir=f'figures/graph_indexed/{x_mode}', fmt=fmt)
    return fig


# ── 17. Graph-indexed success ────────────────────────────────────────────────────

def plot_graph_indexed_success(df, x_mode='by_graph_id', output_dir=None, save=False, fmt='png'):
    """Success rate heatmap: algorithm × graph, with same x-ordering as other variants.

    Note: for by_n_nodes and by_density x_modes, graphs are still shown as categorical
    positions (same ordering as by_graph_id) since success is binary.
    """
    algos = sorted(df['algorithm'].unique())
    graphs = sorted(df['graph_name'].unique())

    if len(graphs) > _MAX_GRAPH_HEATMAP:
        fig, ax = plt.subplots(figsize=(8, 2))
        ax.text(0.5, 0.5,
                f'Too many graphs ({len(graphs):,}) for per-graph heatmap.\n'
                'Use plot_success_by_nodes() or plot_success_by_density() instead.',
                ha='center', va='center', fontsize=10)
        ax.axis('off')
        _maybe_save(fig, output_dir, 'success.png', save,
                    subdir=f'figures/graph_indexed/{x_mode}', fmt=fmt)
        return fig

    # Vectorised: groupby instead of O(algos × graphs) nested loop
    agg = df.groupby(['algorithm', 'graph_name'])['success'].agg(
        n_ok='sum', n_total='count'
    ).reset_index()
    agg['rate'] = agg['n_ok'] / agg['n_total'].replace(0, float('nan'))
    agg['label'] = agg.apply(lambda r: f"{int(r.n_ok)}/{int(r.n_total)}", axis=1)

    rate_pivot  = agg.pivot(index='algorithm', columns='graph_name', values='rate').reindex(index=algos, columns=graphs)
    annot_pivot = agg.pivot(index='algorithm', columns='graph_name', values='label').reindex(index=algos, columns=graphs).fillna('')

    data  = rate_pivot.values
    annot = annot_pivot.values

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
                subdir=f'figures/graph_indexed/{x_mode}', fmt=fmt)
    return fig


# ── 18. Max chain length distribution (KDE) ──────────────────────────────────

def plot_max_chain_distribution(df: pd.DataFrame,
                                 algo_palette=None,
                                 output_dir=None,
                                 save: bool = False,
                                 fmt: str = 'png') -> plt.Figure:
    """Overlaid KDE of max_chain_length per algorithm (successful trials only).

    Batches that predate the max_chain_length column will have NaN values;
    those rows are silently dropped so the plot degrades gracefully.
    """
    success_df = df[df['success']].copy()
    if 'max_chain_length' in success_df.columns:
        success_df = success_df.dropna(subset=['max_chain_length'])

    if success_df.empty or 'max_chain_length' not in success_df.columns:
        fig, ax = plt.subplots()
        ax.text(0.5, 0.5, 'No max_chain_length data', ha='center', va='center')
        _maybe_save(fig, output_dir, 'max_chain_length_kde.png', save,
                    subdir='figures/distributions', fmt=fmt)
        return fig

    palette = algo_palette or _algo_palette(success_df['algorithm'].unique())
    algos = sorted(success_df['algorithm'].unique())

    fig, ax = plt.subplots(figsize=(8, 4))
    for algo in algos:
        data = success_df[success_df['algorithm'] == algo]['max_chain_length'].dropna()
        if data.empty:
            continue
        if data.std() == 0:
            ax.axvline(data.mean(), label=algo, color=palette[algo], linestyle='--')
        else:
            sns.kdeplot(data, ax=ax, label=algo, color=palette[algo], fill=True, alpha=0.2)

    ax.set_xlabel('Max chain length')
    ax.set_ylabel('Density')
    ax.set_title('Max chain length distribution per algorithm')
    ax.legend(framealpha=0.9)
    ax.grid(alpha=0.3)
    plt.tight_layout()
    _maybe_save(fig, output_dir, 'max_kde.png', save,
                subdir='figures/distributions/chain_length', fmt=fmt)
    return fig


# ── 19. Shared-graph intersection comparison ─────────────────────────────────

def plot_intersection_comparison(df: pd.DataFrame,
                                  algo_a: str,
                                  algo_b: str,
                                  algo_palette=None,
                                  output_dir=None,
                                  save: bool = False,
                                  fmt: str = 'png') -> plt.Figure:
    """Grouped bar chart comparing two algorithms on their shared-success graphs.

    For each of five metrics the figure shows:
      - Solid bars: means computed only on graphs where BOTH algorithms succeeded
        (intersection set).
      - Ghost bars (lighter, behind): unfiltered means across all successful runs.

    Both sets are normalised to the better algorithm's intersection value so bars
    represent relative performance: 1.0 = equal, > 1.0 = worse.  Raw values are
    annotated on the solid bars so readers can recover the actual numbers.

    An annotation at the bottom shows:
      - Intersection size N (graphs where both succeeded)
      - Per-algorithm success counts out of total problems
    """
    METRICS = [
        ('avg_chain_length',    'Avg chain\nlength'),
        ('max_chain_length',    'Max chain\nlength'),
        ('wall_time',           'Wall\ntime (s)'),
        ('total_qubits_used',   'Total\nqubits'),
        ('qubit_overhead_ratio','Qubit\noverhead'),
    ]

    success_df = df[df['success']].copy()

    # Graphs where each algorithm succeeded
    a_graphs = set(success_df[success_df['algorithm'] == algo_a]['graph_name'].unique())
    b_graphs = set(success_df[success_df['algorithm'] == algo_b]['graph_name'].unique())
    shared_graphs = a_graphs & b_graphs
    N = len(shared_graphs)

    n_problems = df['graph_name'].nunique()

    palette = algo_palette or _algo_palette([algo_a, algo_b])
    color_a = palette.get(algo_a, _CB_PALETTE[0])
    color_b = palette.get(algo_b, _CB_PALETTE[1])

    intersection_df = success_df[success_df['graph_name'].isin(shared_graphs)]

    # Collect per-metric data (only metrics with data in both algos)
    metrics_data = []
    for col, label in METRICS:
        if col not in success_df.columns:
            continue
        int_a = (intersection_df[intersection_df['algorithm'] == algo_a][col]
                 .dropna().mean() if N > 0 else float('nan'))
        int_b = (intersection_df[intersection_df['algorithm'] == algo_b][col]
                 .dropna().mean() if N > 0 else float('nan'))
        raw_a = success_df[success_df['algorithm'] == algo_a][col].dropna().mean()
        raw_b = success_df[success_df['algorithm'] == algo_b][col].dropna().mean()

        # Skip metric if no intersection data for either algo
        if np.isnan(int_a) and np.isnan(int_b):
            continue

        # Normalise to intersection-best (lower is better for all 5 metrics)
        valid = [v for v in (int_a, int_b) if not np.isnan(v)]
        ref = min(valid) if valid else 1.0
        if ref == 0:
            ref = 1.0

        metrics_data.append({
            'label': label,
            'a_int': int_a,  'b_int': int_b,
            'a_int_norm': int_a / ref if not np.isnan(int_a) else float('nan'),
            'b_int_norm': int_b / ref if not np.isnan(int_b) else float('nan'),
            'a_raw_norm': raw_a / ref if not np.isnan(raw_a) else float('nan'),
            'b_raw_norm': raw_b / ref if not np.isnan(raw_b) else float('nan'),
        })

    n_metrics = len(metrics_data)

    if n_metrics == 0:
        fig, ax = plt.subplots()
        ax.text(0.5, 0.5, f'No shared data for {algo_a} vs {algo_b}',
                ha='center', va='center')
        fname = f'intersection_{algo_a}_vs_{algo_b}.png'
        _maybe_save(fig, output_dir, fname, save, subdir='figures/pairwise', fmt=fmt)
        return fig

    fig, ax = plt.subplots(figsize=(max(9, n_metrics * 2.0), 6))
    x = np.arange(n_metrics)
    width = 0.35
    ghost_alpha = 0.22

    # Ghost bars (unfiltered means, lighter shade) — rendered first (behind)
    for i, m in enumerate(metrics_data):
        ax.bar(x[i] - width / 2, m['a_raw_norm'], width,
               color=color_a, alpha=ghost_alpha, zorder=1)
        ax.bar(x[i] + width / 2, m['b_raw_norm'], width,
               color=color_b, alpha=ghost_alpha, zorder=1)

    # Solid bars (intersection means) — rendered in front
    bars_a = ax.bar(x - width / 2, [m['a_int_norm'] for m in metrics_data], width,
                    color=color_a, label=algo_a, alpha=0.9, zorder=2)
    bars_b = ax.bar(x + width / 2, [m['b_int_norm'] for m in metrics_data], width,
                    color=color_b, label=algo_b, alpha=0.9, zorder=2)

    # Raw value annotations on solid bars
    def _fmt(v):
        if np.isnan(v):
            return ''
        if abs(v) >= 1000:
            return f'{v:.0f}'
        if abs(v) >= 10:
            return f'{v:.1f}'
        return f'{v:.2f}'

    for bar, m in zip(bars_a, metrics_data):
        h = bar.get_height()
        if not np.isnan(h) and h > 0:
            ax.text(bar.get_x() + bar.get_width() / 2, h + 0.015,
                    _fmt(m['a_int']), ha='center', va='bottom', fontsize=7, rotation=45)
    for bar, m in zip(bars_b, metrics_data):
        h = bar.get_height()
        if not np.isnan(h) and h > 0:
            ax.text(bar.get_x() + bar.get_width() / 2, h + 0.015,
                    _fmt(m['b_int']), ha='center', va='bottom', fontsize=7, rotation=45)

    # Reference line at 1.0 (equal performance)
    ax.axhline(1.0, color='black', linewidth=0.8, linestyle='--', alpha=0.4, zorder=0)

    ax.set_xticks(x)
    ax.set_xticklabels([m['label'] for m in metrics_data], fontsize=9)
    ax.set_ylabel('Relative performance (1.0 = equal,  > 1.0 = worse)', fontsize=9)
    ax.set_title(f'Intersection comparison: {algo_a} vs {algo_b}\n'
                 f'(metrics normalised to intersection-best value)')
    ax.set_ylim(bottom=0)
    ax.grid(axis='y', alpha=0.3)

    # Legend: solid + ghost
    ghost_a = mpatches.Patch(color=color_a, alpha=ghost_alpha,
                              label=f'{algo_a} (all successes)')
    ghost_b = mpatches.Patch(color=color_b, alpha=ghost_alpha,
                              label=f'{algo_b} (all successes)')
    solid_handles, solid_labels = ax.get_legend_handles_labels()
    ax.legend(handles=solid_handles + [ghost_a, ghost_b],
              labels=solid_labels + [f'{algo_a} (all successes)',
                                      f'{algo_b} (all successes)'],
              framealpha=0.9, fontsize=8, loc='upper right')

    # Bottom annotation
    annot = (f'Intersection: N = {N} graphs (both succeeded)   |   '
             f'{algo_a}: {len(a_graphs)}/{n_problems} problems succeeded   |   '
             f'{algo_b}: {len(b_graphs)}/{n_problems} problems succeeded')
    fig.text(0.5, 0.01, annot, ha='center', va='bottom', fontsize=8,
             style='italic', color='dimgray',
             bbox=dict(boxstyle='round,pad=0.3', facecolor='lightyellow', alpha=0.6))

    plt.tight_layout(rect=[0, 0.07, 1, 1])

    fname = f'intersection_{algo_a}_vs_{algo_b}.png'
    _maybe_save(fig, output_dir, fname, save, subdir='figures/pairwise', fmt=fmt)
    return fig
