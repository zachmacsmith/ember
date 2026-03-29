# QEAnalysis — Analysis Methods Reference

`qeanalysis` is the post-benchmark analysis package for QEBench. It takes a single batch directory produced by `qebench` as input and generates plots and tables in `analysis/<batch-name>/`.

No D-Wave stack or compiled binaries are needed to run analysis — only `pandas`, `numpy`, `scipy`, `matplotlib`, and `seaborn`.

---

## Quick Usage

```python
from qeanalysis import BenchmarkAnalysis

an = BenchmarkAnalysis("results/batch_2026-02-25_09-25-10/")
an.generate_report()   # runs all analyses; writes to analysis/<batch-name>/
```

Or call individual analyses directly:

```python
an.overall_summary()                       # DataFrame
an.significance_tests()                    # DataFrame
fig = an.plot_pareto(save=False)           # matplotlib Figure
```

---

## Derived Columns

At load time `load_batch()` adds the following columns to the raw `runs.csv` data:

| Column | Formula | Notes |
|--------|---------|-------|
| `category` | Inferred from `problem_name` prefix | `complete`, `bipartite`, `grid`, `cycle`, `tree`, `special`, `random`, `other` |
| `qubit_overhead_ratio` | `total_qubits_used / problem_nodes` | Physical qubits per logical qubit; 1.0 = no overhead |
| `coupler_overhead_ratio` | `total_couplers_used / problem_edges` | Physical couplers per logical edge |
| `max_to_avg_chain_ratio` | `max_chain_length / avg_chain_length` | Chain length uniformity; 1.0 = all chains equal |
| `is_timeout` | `embedding_time >= 0.95 × timeout` | True when an attempt likely hit the wall clock limit |

---

## 1. Summary Tables

### `overall_summary(df)`

Produces one aggregate row per algorithm across all problems and trials. All quality metrics (chain length, qubit usage, etc.) are computed on **successful trials only**; rate metrics use all trials.

| Output Column | Description |
|--------------|-------------|
| `n_trials` | Total trial count |
| `n_success` | Trials where embedding was found |
| `success_rate` | `n_success / n_trials` |
| `n_valid` | Trials where embedding is both found and passes validation |
| `valid_rate` | `n_valid / n_trials` |
| `time_mean` | Mean embedding time (seconds) |
| `time_std` | Standard deviation of embedding time |
| `time_median` | Median embedding time |
| `chain_mean` | Mean `avg_chain_length` across successful trials |
| `chain_std` | Standard deviation of `avg_chain_length` |
| `chain_median` | Median `avg_chain_length` |
| `max_chain_mean` | Mean of `max_chain_length` |
| `qubits_mean` | Mean `total_qubits_used` |
| `qubit_overhead_mean` | Mean `qubit_overhead_ratio` |
| `coupler_overhead_mean` | Mean `coupler_overhead_ratio` |
| `cv_time` | Coefficient of variation: `time_std / time_mean` — measures timing consistency |

**Interpretation:** `cv_time` near 0 indicates a deterministic algorithm; high `cv_time` (> 0.5) suggests high variance, particularly relevant for heuristics like minorminer.

---

### `summary_by_category(df, metric='avg_chain_length')`

A pivot table: **algorithms × graph categories**, where each cell is the mean of `metric` over successful trials. NaN where an algorithm had no successful trial in that category.

Categories present in the standard library: `complete`, `bipartite`, `grid`, `cycle`, `tree`, `special`, `random`.

**Use:** Identifies per-category strengths and weaknesses of each algorithm. Algorithms designed for structured graphs (e.g., clique embedding) may excel in one category but underperform on random graphs.

---

### `rank_table(df, metric='avg_chain_length', lower_is_better=True)`

For each problem where **≥ 2 algorithms** succeeded, algorithms are ranked 1 (best) through N (worst). The table reports each algorithm's mean and median rank across all problems.

| Output Column | Description |
|--------------|-------------|
| `mean_rank` | Average rank across all problems where the algorithm succeeded |
| `median_rank` | Median rank |
| `n_problems_ranked` | Number of problems where this algorithm was included in the ranking |

**Interpretation:** Mean rank is less sensitive to outliers than mean metric value; it is the basis of most statistical comparisons in the embedding literature. An algorithm ranked 1st on average is the "best" by this measure, independent of the absolute metric scale.

---

## 2. Statistical Analyses

### `win_rate_matrix(df, metric='avg_chain_length', lower_is_better=True)`

An N × N pairwise win rate matrix. Cell (A, B) = fraction of problems where algorithm A achieves a strictly better per-problem mean `metric` than algorithm B, considering only problems where both algorithms had successful trials.

- Diagonal is NaN (self-comparison undefined).
- A + B = 1: cell (A, B) and cell (B, A) are complementary.
- Values in [0, 1]; multiply by 100 for percentages.

**Interpretation:** A cell value of 0.75 means algorithm A beat B on 75% of problems. Values above 0.5 indicate A is consistently better than B on that metric.

---

### `significance_tests(df, metric='avg_chain_length', min_pairs=5)`

Wilcoxon signed-rank test for all algorithm pairs on per-problem mean `metric`.

**Method:**
1. For each problem, compute the mean `metric` over successful trials for each algorithm.
2. For each pair (A, B), collect the per-problem means as matched pairs (only problems where both succeeded).
3. Run a two-sided Wilcoxon signed-rank test on the paired differences.
4. Apply Holm-Bonferroni correction across all pairs to control the familywise error rate.

The Wilcoxon signed-rank test is preferred over paired t-tests because it makes no distributional assumptions (embedding times are typically heavy-tailed and non-normal).

| Output Column | Description |
|--------------|-------------|
| `algo_a`, `algo_b` | Algorithm pair |
| `n_pairs` | Number of problems where both algorithms succeeded |
| `w_statistic` | Wilcoxon W statistic |
| `p_value` | Raw two-sided p-value |
| `corrected_p` | Holm-Bonferroni corrected p-value |
| `significant` | True if `corrected_p < 0.05` |
| `effect_size` | Rank-biserial r ∈ [−1, 1] |

**Effect size (rank-biserial r):**

```
r = 1 − 2W / (n(n+1)/2)
```

where W is the smaller of the sum of positive and negative signed ranks, and n is the number of non-zero differences. Magnitude interpretation: |r| < 0.3 small, 0.3–0.5 medium, > 0.5 large.

**Guards:** Pairs with fewer than `min_pairs` observations are reported as NaN rather than producing unreliable test results.

**Holm-Bonferroni procedure:** Adjusts for multiple comparisons while being less conservative than Bonferroni. For k tests sorted by ascending p-value, the corrected p at rank i is `min(1, p_i × (k − i + 1))`, subject to the monotonicity constraint that corrected p-values are non-decreasing.

---

### `friedman_test(df, metric='avg_chain_length')`

Non-parametric equivalent of one-way repeated-measures ANOVA. Tests whether at least one algorithm is significantly different from the others across all problems simultaneously.

**Method:** scipy's `friedmanchisquare`, applied to per-problem mean metrics. Only problems where **all** algorithms had a successful trial are included (complete blocks).

Requires ≥ 3 algorithms and ≥ 3 complete problems; returns an error string otherwise.

| Output Key | Description |
|-----------|-------------|
| `statistic` | Friedman chi-square statistic |
| `p_value` | Associated p-value |
| `significant` | True if p < 0.05 |
| `n_problems` | Number of complete problems used |
| `n_algorithms` | Number of algorithms compared |

**Interpretation:** A significant Friedman result justifies running pairwise comparisons (`significance_tests`). A non-significant result means there is insufficient evidence to conclude any algorithm differs from the others on that metric.

---

### `correlation_matrix(df, graph_props=None, embed_metrics=None, method='spearman')`

Spearman rank correlation between graph structural properties and embedding performance metrics, computed on successful trials only.

Default graph properties: `problem_nodes`, `problem_edges`, `problem_density`

Default embedding metrics: `embedding_time`, `avg_chain_length`, `max_chain_length`, `total_qubits_used`

Returns a `(graph_props × embed_metrics)` DataFrame of correlation coefficients ∈ [−1, 1]. NaN where a column has zero variance or fewer than 3 common observations.

**Why Spearman?** Spearman rank correlation is appropriate here because:
- Embedding metrics often scale non-linearly with graph size.
- Distributions are typically skewed and non-normal.
- Ranks are robust to outliers (e.g., rare pathological cases where an algorithm fails on a small graph).

**Interpretation:** A strong positive correlation between `problem_nodes` and `avg_chain_length` (r ≈ 0.8–1.0) indicates that chain length grows with problem size — expected. A strong correlation with `problem_density` but not `problem_nodes` would suggest the embedding difficulty is driven more by connectivity than by graph size.

---

### `density_hardness_summary(df, metric='avg_chain_length')`

Aggregates `metric` by `(algorithm, problem_nodes, problem_density)` for **random graphs only** (category == `'random'`). Used to characterize how embedding difficulty grows with edge density at fixed graph size.

| Output Column | Description |
|--------------|-------------|
| `algorithm` | Algorithm name |
| `problem_nodes` | Number of nodes n |
| `problem_density` | Target edge density p |
| `{metric}_mean` | Mean metric over all instances and trials at (n, p) |
| `{metric}_std` | Standard deviation |
| `n_trials` | Total trial count at (n, p) |

**Use:** Plotting this table (via `plot_density_hardness`) produces curves analogous to phase transition plots common in combinatorial optimization benchmarking.

---

## 3. Visualizations

All plot functions accept `df` as the first argument, return a `matplotlib.Figure`, and optionally save to `output_dir` when `save=True`. Colors are consistent across all plots in a report via a shared `tab10` palette keyed by algorithm name.

---

### `plot_heatmap(df, metric='avg_chain_length')`

**What:** Heatmap of mean `metric`, rows = algorithms, columns = graph categories.

**How:** Calls `summary_by_category()` and renders via `seaborn.heatmap`. Annotated with cell values. Red-white-blue diverging colormap (lower = blue = better for chain length).

**Use:** Immediately shows which algorithms struggle with which graph families.

---

### `plot_scaling(df, metric='embedding_time', x='problem_nodes', log=False)`

**What:** Line plot showing how `metric` scales with graph size, one line per algorithm. Shaded band shows ±1 standard deviation across trials.

**How:** Groups by `(algorithm, x)`, computes mean ± std. Log scale optional for both axes.

**Use:** Characterizes algorithmic complexity. A line with slope 1 in log-log space suggests linear scaling; slope 2 suggests quadratic.

---

### `plot_density_hardness(df, metric='avg_chain_length')`

**What:** Scatter + line plots for random graphs only. X-axis = edge density, Y-axis = `metric`. One subplot per unique `problem_nodes` value, one line per algorithm.

**Use:** Shows how embedding difficulty grows with density at fixed graph size. Algorithms robust to density will show flatter lines.

---

### `plot_pareto(df, x='embedding_time', y='avg_chain_length')`

**What:** Scatter plot with one point per `(algorithm, problem)` representing that algorithm's mean performance. The Pareto frontier (lower-left convex hull) is highlighted.

**How:** Computes per-problem means, then finds Pareto-optimal points where no other algorithm is simultaneously faster and shorter. Non-dominated points are marked with a bold outline.

**Use:** Summarizes the time–quality trade-off across all problems in one plot. Points on the frontier represent the "best" algorithms for at least one operating regime.

---

### `plot_distributions(df, metric='avg_chain_length')`

**What:** Violin plot of `metric` distribution per algorithm, with overlaid box-and-whisker showing median and interquartile range.

**How:** Successful trials only. Violins show the full distribution shape via kernel density estimation.

**Use:** Reveals whether an algorithm is consistently good or highly variable. A wide violin with a high median is worse than a narrow violin at the same median.

---

### `plot_head_to_head(df, algo_a, algo_b, metric='avg_chain_length')`

**What:** Scatter plot with one point per problem. X-axis = algo A's mean `metric`, Y-axis = algo B's mean `metric`. The diagonal y = x is drawn as a reference; points above it mean B wins on that problem, below means A wins.

**Use:** Identifies whether one algorithm's advantage is consistent across all problems, or driven by a few outliers.

---

### `plot_consistency(df)`

**What:** Two-panel bar chart. Left panel: coefficient of variation (CV = std/mean) of `embedding_time`. Right panel: CV of `avg_chain_length`. One bar per algorithm.

**Use:** Lower CV = more reproducible. Deterministic algorithms should have CV ≈ 0 for chain length (same answer every time) but may vary in time. Heuristics like minorminer typically have non-zero CV for both.

---

### `plot_topology_comparison(df, metric='avg_chain_length')`

**What:** Grouped bar chart. Groups = algorithms, bar clusters = topologies. Only meaningful when a batch covers multiple topologies.

**Use:** Shows how the same algorithm performs differently across Chimera, Pegasus, and Zephyr. Larger topologies generally allow shorter chains due to higher qubit connectivity.

---

### `plot_problem_deep_dive(df, problem_name)`

**What:** Two-panel bar chart for a single named problem. Left panel: mean `embedding_time` per algorithm. Right panel: mean `avg_chain_length`. Bars are annotated with success/validity counts.

**Use:** Detailed per-problem comparison. Useful for understanding why one algorithm dominates or fails on a specific graph instance.

---

### `plot_chain_distribution(df)`

**What:** Overlaid KDE (kernel density estimate) and histogram of `avg_chain_length` across all successful trials, one curve per algorithm.

**Use:** Shows the full shape of each algorithm's chain length distribution across all problems simultaneously. Ideal algorithms have distributions concentrated at low values with thin tails.

---

## 4. Export

### `df_to_latex(df, caption='', label='', float_fmt='.3f', index=True)`

Converts a DataFrame to a publication-ready LaTeX table string using `booktabs` formatting (`\toprule`, `\midrule`, `\bottomrule`). Implemented without `pandas.to_latex()` to avoid a `jinja2` dependency.

Column format is auto-computed: first column left-aligned (`l`), remaining columns right-aligned (`r`). Special characters (`_`, `%`, `&`) are escaped automatically.

---

### `export_tables(tables_dict, output_dir)`

Writes a dict of DataFrames as both `.csv` and `.tex` files:

```python
export_tables({
    'overall_summary': (df, 'Caption text', 'tab:label'),
    'win_rate': (win_df, 'Win rates', 'tab:win'),
}, output_dir='analysis/batch_X/tables/')
```

---

## 5. Extending qeanalysis

The package is designed for easy extension:

**Adding a new statistical test:**
1. Add a standalone function to `qeanalysis/statistics.py`.
2. Add a thin wrapper method to `BenchmarkAnalysis` in `qeanalysis/__init__.py`.
3. Call it from `generate_report()` to include it in every auto-generated report.

**Adding a new plot:**
1. Add a function to `qeanalysis/plots.py` following the standard signature:
   ```python
   def plot_my_analysis(df, ..., output_dir=None, save=False) -> plt.Figure:
       fig, ax = plt.subplots(...)
       # ...
       _maybe_save(fig, output_dir, 'my_analysis.png', save)
       return fig
   ```
2. Add a wrapper to `BenchmarkAnalysis` and a call in `generate_report()`.
3. Add a test in `tests/test_qeanalysis.py::TestPlots` asserting the function returns a `plt.Figure`.

No registration system or framework changes are needed.
