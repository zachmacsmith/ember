"""
ember_qc_analysis — Post-benchmark analysis package for ember-qc
=================================================================

Separate from ember-qc: requires only pandas/numpy/scipy/matplotlib.
No D-Wave stack or C++ binaries needed.

Typical workflow
----------------
    from ember_qc_analysis import BenchmarkAnalysis

    an = BenchmarkAnalysis("results/batch_2026-02-24_14-30-00/")
    an.generate_report()   # runs everything; writes to analysis/<batch-name>/

Output layout produced by generate_report()
--------------------------------------------
    analysis/<batch-name>/
    ├── summary/        — CSV + LaTeX tables
    ├── statistics/     — significance tests, correlation, friedman
    ├── figures/
    │   ├── distributions/
    │   ├── graph_indexed/{by_graph_id,by_n_nodes,by_density}/
    │   ├── scaling/
    │   ├── pairwise/
    │   ├── success/
    │   └── topology/
    └── report.md
"""

import itertools
import json
from pathlib import Path
from typing import Dict, List, Optional

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pandas as pd

from ember_qc_analysis.loader    import load_batch, infer_category
from ember_qc_analysis.summary   import overall_summary, summary_by_category, rank_table
from ember_qc_analysis.statistics import (
    win_rate_matrix, significance_tests, friedman_test,
    correlation_matrix, density_hardness_summary,
)
from ember_qc_analysis.plots import (
    build_algo_palette,
    plot_heatmap, plot_scaling, plot_density_hardness,
    plot_pareto, plot_distributions, plot_head_to_head,
    plot_consistency, plot_topology_comparison,
    plot_problem_deep_dive, plot_chain_distribution,
    plot_win_rate_matrix, plot_success_heatmap,
    plot_success_by_nodes, plot_success_by_density,
    plot_graph_indexed_chain, plot_graph_indexed_time,
    plot_graph_indexed_success,
    plot_max_chain_distribution, plot_intersection_comparison,
)
from ember_qc_analysis.export import df_to_latex, export_tables
from ember_qc_analysis.filters import shared_graph_filter, apply_graph_filter, parse_graph_ids


__all__ = [
    'BenchmarkAnalysis',
    # Loader
    'load_batch', 'infer_category',
    # Summary
    'overall_summary', 'summary_by_category', 'rank_table',
    # Statistics
    'win_rate_matrix', 'significance_tests', 'friedman_test',
    'correlation_matrix', 'density_hardness_summary',
    # Plots
    'build_algo_palette',
    'plot_heatmap', 'plot_scaling', 'plot_density_hardness',
    'plot_pareto', 'plot_distributions', 'plot_head_to_head',
    'plot_consistency', 'plot_topology_comparison',
    'plot_problem_deep_dive', 'plot_chain_distribution',
    'plot_win_rate_matrix', 'plot_success_heatmap',
    'plot_success_by_nodes', 'plot_success_by_density',
    'plot_graph_indexed_chain', 'plot_graph_indexed_time',
    'plot_graph_indexed_success',
    'plot_max_chain_distribution', 'plot_intersection_comparison',
    # Export
    'df_to_latex', 'export_tables',
    # Filters
    'shared_graph_filter', 'apply_graph_filter', 'parse_graph_ids',
]


# ── BenchmarkAnalysis ─────────────────────────────────────────────────────────

class BenchmarkAnalysis:
    """Main entry point for analysing a single ember-qc batch.

    Args:
        batch_dir:    Path to the batch directory (contains results.db or
                      runs.csv, and optionally config.json).
        output_root:  Root directory for analysis output.
                      Results are written to output_root/<batch-name>/.
                      Defaults to "analysis/" relative to the current directory.
    """

    def __init__(self, batch_dir, output_root: str = 'analysis/'):
        self._batch_dir = Path(batch_dir)
        self._df, self._config = load_batch(self._batch_dir)
        self._output_root = Path(output_root)
        self._filter_subdir: str = ''   # set by filter_graphs(); appended to output_dir

    # ── Properties ────────────────────────────────────────────────────────────

    @property
    def df(self) -> pd.DataFrame:
        return self._df

    @property
    def config(self) -> dict:
        return self._config

    @property
    def batch_name(self) -> str:
        return self._batch_dir.name

    @property
    def output_dir(self) -> Path:
        base = self._output_root / self.batch_name
        return base / self._filter_subdir if self._filter_subdir else base

    @property
    def figures_dir(self) -> Path:
        return self.output_dir / 'figures'

    @property
    def summary_dir(self) -> Path:
        return self.output_dir / 'summary'

    @property
    def tables_dir(self) -> Path:
        """Alias for summary_dir (backward compatibility)."""
        return self.summary_dir

    @property
    def statistics_dir(self) -> Path:
        return self.output_dir / 'statistics'

    # ── Graph filtering ───────────────────────────────────────────────────────

    def filter_graphs(
        self,
        graphs: Optional[str] = None,
        graph_type: Optional[str] = None,
    ) -> 'BenchmarkAnalysis':
        """Restrict all subsequent analyses to a subset of graphs.

        Sets ``self._df`` to the filtered rows and routes all output into a
        named subdirectory (e.g. ``analysis/<batch>/graphs_1-10__type_random/``).
        Can be called multiple times; each call further narrows the selection
        and appends to the subfolder name.

        Args:
            graphs:     Graph selection string (e.g. ``"1-10"``, ``"1-60,!35"``,
                        ``"quick"``).  Preset names require ember-qc to be
                        installed.  ``"*"`` or ``None`` means no ID filter.
            graph_type: Graph category (``"random"``, ``"complete"``,
                        ``"bipartite"``, ``"grid"``, ``"cycle"``, ``"tree"``,
                        ``"special"``, ``"other"``).

        Returns:
            ``self``, for method chaining::

                an = BenchmarkAnalysis("results/batch/")
                an.filter_graphs(graphs="1-20", graph_type="random")
                an.generate_report()

        Raises:
            ValueError: for unrecognised graph spec tokens or category names.
            RuntimeError: if the filter removes all rows from the DataFrame.
        """
        filtered, slug = apply_graph_filter(self._df, graphs=graphs, graph_type=graph_type)
        if filtered.empty:
            raise RuntimeError(
                f"Graph filter graphs={graphs!r} graph_type={graph_type!r} "
                "produced an empty DataFrame — no matching rows."
            )
        self._df = filtered
        if slug:
            self._filter_subdir = (
                f"{self._filter_subdir}__{slug}" if self._filter_subdir else slug
            )
        return self

    # ── Summary tables ────────────────────────────────────────────────────────

    def overall_summary(self) -> pd.DataFrame:
        return overall_summary(self._df)

    def summary_by_category(self, metric: str = 'avg_chain_length') -> pd.DataFrame:
        return summary_by_category(self._df, metric)

    def rank_table(self, metric: str = 'avg_chain_length',
                   lower_is_better: bool = True) -> pd.DataFrame:
        return rank_table(self._df, metric, lower_is_better)

    # ── Statistical analyses ──────────────────────────────────────────────────

    def win_rate_matrix(self, metric: str = 'avg_chain_length',
                        lower_is_better: bool = True) -> pd.DataFrame:
        return win_rate_matrix(self._df, metric, lower_is_better)

    def significance_tests(self, metric: str = 'avg_chain_length') -> pd.DataFrame:
        return significance_tests(self._df, metric)

    def friedman_test(self, metric: str = 'avg_chain_length') -> dict:
        return friedman_test(self._df, metric)

    def correlation_matrix(self,
                            graph_props: Optional[List[str]] = None,
                            embed_metrics: Optional[List[str]] = None) -> pd.DataFrame:
        return correlation_matrix(self._df, graph_props, embed_metrics)

    # ── Plot wrappers ─────────────────────────────────────────────────────────
    # Each method returns the Figure and saves to the correct subdirectory.
    # output_dir is always the batch analysis root; plot functions resolve
    # their own subdirectory from that root.

    def plot_heatmap(self, metric: str = 'avg_chain_length',
                     save: bool = True) -> plt.Figure:
        return plot_heatmap(self._df, metric,
                            output_dir=self.output_dir, save=save)

    def plot_scaling(self, metric: str = 'wall_time',
                     x: str = 'problem_nodes', log: bool = False,
                     save: bool = True) -> plt.Figure:
        return plot_scaling(self._df, metric, x, log,
                            output_dir=self.output_dir, save=save)

    def plot_density_hardness(self, metric: str = 'avg_chain_length',
                               save: bool = True) -> plt.Figure:
        return plot_density_hardness(self._df, metric,
                                     output_dir=self.output_dir, save=save)

    def plot_pareto(self, x: str = 'wall_time',
                    y: str = 'avg_chain_length',
                    save: bool = True) -> plt.Figure:
        return plot_pareto(self._df, x, y,
                           output_dir=self.output_dir, save=save)

    def plot_distributions(self, metric: str = 'avg_chain_length',
                            save: bool = True) -> plt.Figure:
        return plot_distributions(self._df, metric,
                                  output_dir=self.output_dir, save=save)

    def plot_head_to_head(self, algo_a: str, algo_b: str,
                           metric: str = 'avg_chain_length',
                           save: bool = True) -> plt.Figure:
        return plot_head_to_head(self._df, algo_a, algo_b, metric,
                                 output_dir=self.output_dir, save=save)

    def plot_consistency(self, save: bool = True) -> plt.Figure:
        return plot_consistency(self._df,
                                output_dir=self.output_dir, save=save)

    def plot_topology_comparison(self, metric: str = 'avg_chain_length',
                                  save: bool = True) -> plt.Figure:
        return plot_topology_comparison(self._df, metric,
                                        output_dir=self.output_dir, save=save)

    def plot_problem_deep_dive(self, graph_name: str,
                                save: bool = True) -> plt.Figure:
        return plot_problem_deep_dive(self._df, graph_name,
                                      output_dir=self.output_dir, save=save)

    def plot_chain_distribution(self, save: bool = True) -> plt.Figure:
        return plot_chain_distribution(self._df,
                                       output_dir=self.output_dir, save=save)

    def plot_win_rate_matrix(self, metric: str = 'avg_chain_length',
                              save: bool = True) -> plt.Figure:
        return plot_win_rate_matrix(self._df, metric,
                                    output_dir=self.output_dir, save=save)

    def plot_success_heatmap(self, save: bool = True) -> plt.Figure:
        return plot_success_heatmap(self._df,
                                    output_dir=self.output_dir, save=save)

    def plot_success_by_nodes(self, save: bool = True) -> plt.Figure:
        return plot_success_by_nodes(self._df,
                                     output_dir=self.output_dir, save=save)

    def plot_success_by_density(self, save: bool = True) -> plt.Figure:
        return plot_success_by_density(self._df,
                                       output_dir=self.output_dir, save=save)

    def plot_graph_indexed_chain(self, x_mode: str = 'by_graph_id',
                                  save: bool = True) -> plt.Figure:
        return plot_graph_indexed_chain(self._df, x_mode,
                                        output_dir=self.output_dir, save=save)

    def plot_graph_indexed_time(self, x_mode: str = 'by_graph_id',
                                 save: bool = True) -> plt.Figure:
        return plot_graph_indexed_time(self._df, x_mode,
                                       output_dir=self.output_dir, save=save)

    def plot_graph_indexed_success(self, x_mode: str = 'by_graph_id',
                                    save: bool = True) -> plt.Figure:
        return plot_graph_indexed_success(self._df, x_mode,
                                          output_dir=self.output_dir, save=save)

    def plot_max_chain_distribution(self, save: bool = True) -> plt.Figure:
        return plot_max_chain_distribution(self._df,
                                           output_dir=self.output_dir, save=save)

    def plot_intersection_comparison(self, algo_a: str, algo_b: str,
                                      save: bool = True) -> plt.Figure:
        return plot_intersection_comparison(self._df, algo_a, algo_b,
                                             output_dir=self.output_dir, save=save)

    # ── Export ────────────────────────────────────────────────────────────────

    def export_latex(self, output_dir=None) -> None:
        """Write all summary tables as .tex and .csv files."""
        out = Path(output_dir) if output_dir else self.summary_dir
        tables = {
            'overall_summary': (
                self.overall_summary(),
                'Algorithm performance summary',
                'tab:overall_summary',
            ),
            'rank_table_chain': (
                self.rank_table('avg_chain_length'),
                'Algorithm rank by average chain length',
                'tab:rank_chain',
            ),
            'rank_table_time': (
                self.rank_table('wall_time'),
                'Algorithm rank by embedding time',
                'tab:rank_time',
            ),
            'summary_by_category_chain': (
                self.summary_by_category('avg_chain_length'),
                'Mean average chain length by graph category',
                'tab:category_chain',
            ),
            'summary_by_category_time': (
                self.summary_by_category('wall_time'),
                'Mean embedding time by graph category',
                'tab:category_time',
            ),
            'pairwise_comparison': (
                self.win_rate_matrix('avg_chain_length'),
                'Win rate matrix (avg chain length)',
                'tab:win_rate_chain',
            ),
        }
        export_tables(tables, out)

    # ── Full report ───────────────────────────────────────────────────────────

    def generate_report(self, fmt: str = 'png') -> Path:
        """Run all analyses and write output to analysis/<batch-name>/.

        Output layout:
            summary/     — CSV + LaTeX tables
            statistics/  — significance tests, correlation, friedman
            figures/     — all plots in subdirectories (see module docstring)
            report.md    — index with descriptions of every output

        Args:
            fmt: Image format for figures ('png', 'pdf', 'svg').

        Returns:
            Path to the output directory.
        """
        # ── Create all subdirectories upfront ─────────────────────────────
        for subdir in [
            self.summary_dir,
            self.statistics_dir,
            self.figures_dir / 'distributions',
            self.figures_dir / 'graph_indexed' / 'by_graph_id',
            self.figures_dir / 'graph_indexed' / 'by_n_nodes',
            self.figures_dir / 'graph_indexed' / 'by_density',
            self.figures_dir / 'scaling',
            self.figures_dir / 'pairwise',
            self.figures_dir / 'success',
            self.figures_dir / 'topology',
        ]:
            subdir.mkdir(parents=True, exist_ok=True)

        algos = sorted(self._df['algorithm'].unique())
        # Compute palette once — same colour for every algorithm in every figure
        palette = build_algo_palette(algos)

        generated_figures = []
        generated_tables  = []
        generated_stats   = []

        def _run(label, fn):
            try:
                fn()
                generated_figures.append(label)
            except Exception as e:
                print(f"  [plot] {label}: {e}")

        # ── Distribution plots ────────────────────────────────────────────
        _run('chain_length_kde',
             lambda: plot_chain_distribution(
                 self._df, algo_palette=palette,
                 output_dir=self.output_dir, save=True, fmt=fmt))
        _run('max_chain_length_kde',
             lambda: plot_max_chain_distribution(
                 self._df, algo_palette=palette,
                 output_dir=self.output_dir, save=True, fmt=fmt))
        _run('chain_length_violin',
             lambda: plot_distributions(
                 self._df, 'avg_chain_length', algo_palette=palette,
                 output_dir=self.output_dir, save=True, fmt=fmt))
        _run('embedding_time_violin',
             lambda: plot_distributions(
                 self._df, 'wall_time', algo_palette=palette,
                 output_dir=self.output_dir, save=True, fmt=fmt))
        _run('chain_length_by_category',
             lambda: plot_heatmap(
                 self._df, 'avg_chain_length', algo_palette=palette,
                 output_dir=self.output_dir, save=True, fmt=fmt))
        _run('consistency_cv',
             lambda: plot_consistency(
                 self._df, algo_palette=palette,
                 output_dir=self.output_dir, save=True, fmt=fmt))

        # ── Scaling plots ─────────────────────────────────────────────────
        _run('chain_length_vs_nodes',
             lambda: plot_scaling(
                 self._df, 'avg_chain_length', 'problem_nodes',
                 algo_palette=palette, output_dir=self.output_dir, save=True, fmt=fmt))
        _run('time_vs_nodes',
             lambda: plot_scaling(
                 self._df, 'wall_time', 'problem_nodes',
                 algo_palette=palette, output_dir=self.output_dir, save=True, fmt=fmt))
        _run('density_hardness',
             lambda: plot_density_hardness(
                 self._df, algo_palette=palette,
                 output_dir=self.output_dir, save=True, fmt=fmt))

        # ── Pairwise plots ────────────────────────────────────────────────
        _run('win_rate_matrix',
             lambda: plot_win_rate_matrix(
                 self._df, output_dir=self.output_dir, save=True, fmt=fmt))
        for a, b in itertools.combinations(algos, 2):
            _run(f'scatter_{a}_vs_{b}',
                 lambda a=a, b=b: plot_head_to_head(
                     self._df, a, b, output_dir=self.output_dir, save=True, fmt=fmt))
            _run(f'intersection_{a}_vs_{b}',
                 lambda a=a, b=b: plot_intersection_comparison(
                     self._df, a, b, algo_palette=palette,
                     output_dir=self.output_dir, save=True, fmt=fmt))

        # ── Success plots ─────────────────────────────────────────────────
        _run('success_rate_heatmap',
             lambda: plot_success_heatmap(
                 self._df, output_dir=self.output_dir, save=True, fmt=fmt))
        _run('success_rate_by_nodes',
             lambda: plot_success_by_nodes(
                 self._df, algo_palette=palette,
                 output_dir=self.output_dir, save=True, fmt=fmt))
        _run('success_rate_by_density',
             lambda: plot_success_by_density(
                 self._df, algo_palette=palette,
                 output_dir=self.output_dir, save=True, fmt=fmt))

        # ── Graph-indexed plots (3 x_modes × 4 metrics = 12 plots) ──────
        for x_mode in ('by_graph_id', 'by_n_nodes', 'by_density'):
            _run(f'graph_indexed/{x_mode}/chain_length',
                 lambda xm=x_mode: plot_graph_indexed_chain(
                     self._df, xm, algo_palette=palette,
                     output_dir=self.output_dir, save=True, fmt=fmt))
            _run(f'graph_indexed/{x_mode}/max_chain_length',
                 lambda xm=x_mode: plot_graph_indexed_chain(
                     self._df, xm, algo_palette=palette,
                     metric='max_chain_length',
                     output_dir=self.output_dir, save=True, fmt=fmt))
            _run(f'graph_indexed/{x_mode}/embedding_time',
                 lambda xm=x_mode: plot_graph_indexed_time(
                     self._df, xm, algo_palette=palette,
                     output_dir=self.output_dir, save=True, fmt=fmt))
            _run(f'graph_indexed/{x_mode}/success',
                 lambda xm=x_mode: plot_graph_indexed_success(
                     self._df, xm,
                     output_dir=self.output_dir, save=True, fmt=fmt))

        # ── Topology comparison ───────────────────────────────────────────
        _run('topology_comparison',
             lambda: plot_topology_comparison(
                 self._df, algo_palette=palette,
                 output_dir=self.output_dir, save=True, fmt=fmt))

        # ── Pareto frontier ───────────────────────────────────────────────
        _run('pareto_frontier',
             lambda: plot_pareto(
                 self._df, algo_palette=palette,
                 output_dir=self.output_dir, save=True, fmt=fmt))

        # ── Summary tables → summary/ ─────────────────────────────────────
        try:
            self.export_latex()
            generated_tables = [
                'overall_summary', 'rank_table_chain', 'rank_table_time',
                'summary_by_category_chain', 'summary_by_category_time',
                'pairwise_comparison',
            ]
        except Exception as e:
            print(f"  [tables] export: {e}")

        # ── Statistics → statistics/ ──────────────────────────────────────
        try:
            sig = self.significance_tests()
            sig.to_csv(self.statistics_dir / 'significance_tests.csv')
            export_tables(
                {'significance_tests': (sig, 'Wilcoxon significance tests', 'tab:sig')},
                self.statistics_dir,
            )
            generated_stats.append('significance_tests')
        except Exception as e:
            print(f"  [stats] significance_tests: {e}")

        try:
            fr = self.friedman_test()
            (self.statistics_dir / 'friedman_test.txt').write_text(
                '\n'.join(f'{k}: {v}' for k, v in fr.items()) + '\n'
            )
            generated_stats.append('friedman_test')
        except Exception as e:
            print(f"  [stats] friedman_test: {e}")

        try:
            corr = self.correlation_matrix()
            corr.to_csv(self.statistics_dir / 'correlation_matrix.csv')
            generated_stats.append('correlation_matrix')
        except Exception as e:
            print(f"  [stats] correlation_matrix: {e}")

        try:
            wm = self.win_rate_matrix()
            wm.to_csv(self.statistics_dir / 'win_rate_matrix.csv')
            generated_stats.append('win_rate_matrix')
        except Exception as e:
            print(f"  [stats] win_rate_matrix: {e}")

        # ── report.md ─────────────────────────────────────────────────────
        self._write_report_md(generated_figures, generated_tables, generated_stats)

        print(f"\nAnalysis complete -> {self.output_dir}/")
        print(f"  summary/     ({len(generated_tables)} tables)")
        print(f"  statistics/  ({len(generated_stats)} outputs)")
        print(f"  figures/     ({len(generated_figures)} plots)")
        print(f"  report.md")

        return self.output_dir

    def _write_report_md(self, figures: list, tables: list, stats: list) -> None:
        lines = [
            f'# Analysis Report: {self.batch_name}\n',
            f'Batch note: {self._config.get("batch_note", "—")}\n',
            f'Algorithms: {", ".join(sorted(self._df["algorithm"].unique()))}\n',
            f'Problems: {self._df["graph_name"].nunique()}',
            f'  |  Topologies: {", ".join(sorted(self._df["topology_name"].dropna().unique()))}\n',
            '\n---\n',
            '## Figures\n',
            '### distributions/\n',
            '- `chain_length_kde.png` — overlaid KDE of avg chain length per algorithm\n',
            '- `max_chain_length_kde.png` — overlaid KDE of max chain length per algorithm\n',
            '- `chain_length_violin.png` — violin + box of chain length distribution\n',
            '- `embedding_time_violin.png` — violin + box of wall time distribution\n',
            '- `chain_length_by_category.png` — heatmap: mean chain length by algo × graph category\n',
            '- `consistency_cv.png` — coefficient of variation for time and chain length\n',
            '\n### graph_indexed/\n',
            'Twelve plots organised into three x-axis variants:\n',
            '- **by_graph_id/** — one position per graph ID (categorical). Use this to see\n',
            '  exactly which graphs are hard or easy. Section labels mark graph categories.\n',
            '- **by_n_nodes/** — x encodes node count (numeric). Use this to see scaling\n',
            '  with graph size. Deterministic jitter separates overlapping points.\n',
            '- **by_density/** — x encodes graph density (numeric). Use this to see how\n',
            '  edge density affects embeddability and chain length.\n',
            '\nEach directory contains:\n',
            '- `chain_length.png` — avg chain length per trial (dots) + per-graph mean\n',
            '  (diamond). Each algorithm shown only where it succeeded; absence = failure.\n',
            '- `max_chain_length.png` — same structure as chain_length.png but shows max\n',
            '  chain length per run. NaN values (pre-SQLite batches) are silently dropped.\n',
            '- `embedding_time.png` — wall time per trial on log scale. No shared-graph\n',
            '  filter; timeout runs shown with triangle-up marker.\n',
            '- `success.png` — success rate heatmap (algorithm × graph, red=0 green=1).\n',
            '  The most informative single figure: shows which algorithm fails on which graphs.\n',
            '\n### scaling/\n',
            '- `chain_length_vs_nodes.png`, `time_vs_nodes.png` — mean ± std ribbon vs node count\n',
            '- `density_hardness.png` — metric vs density for random graphs (trend lines)\n',
            '\n### pairwise/\n',
            '- `win_rate_matrix.png` — N×N heatmap: % of problems where row algo beats col algo\n',
            '- `scatter_{A}_vs_{B}.png` — one per algorithm pair; diagonal = equal performance\n',
            '- `intersection_{A}_vs_{B}.png` — grouped bar chart on shared-success graphs only.\n',
            '  5 metrics normalised to intersection-best. Ghost bars show unfiltered means.\n',
            '  Annotation shows intersection N and per-algo success counts.\n',
            '\n### success/\n',
            '- `success_rate_heatmap.png` — algo × all-graphs heatmap with raw fractions\n',
            '- `success_rate_by_nodes.png`, `success_rate_by_density.png` — success vs graph properties\n',
            '\n### topology/\n',
            '- `topology_comparison.png` — grouped bars by topology and algorithm\n',
            '\n---\n',
            '## Summary Tables (summary/)\n',
        ]
        for t in tables:
            lines.append(f'- `{t}.csv` / `{t}.tex`\n')
        lines += ['\n## Statistics (statistics/)\n']
        for s in stats:
            lines.append(f'- `{s}`\n')

        with open(self.output_dir / 'report.md', 'w') as fh:
            fh.write(''.join(lines))
