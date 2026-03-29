# Analysis Outputs

`ember-analysis report` produces three categories of output: plots, tables, and statistics. This document describes every file, what it shows, and how to interpret it.

All outputs are written to `<batch_dir>/analysis/` by default, organised into subdirectories.

---

## Plots

Plots are written to `analysis/plots/<group>/`. Default format is PNG; use `-f pdf` or `-f svg` for publication-ready formats.

### distributions/

Plots that show how embedding metrics are distributed across trials and problems.

**`chain_length_kde.png`**
Kernel density estimate of `avg_chain_length` for each algorithm. Overlaid curves with a shared x-axis. A curve shifted left indicates shorter average chains (more efficient). Width of the curve indicates variability.

**`max_chain_kde.png`**
Same as above for `max_chain_length`. Max chain length is the binding constraint — a single very long chain can make an otherwise good embedding unusable.

**`chain_violin.png`**
Violin plot of `avg_chain_length` per algorithm. Shows the full distribution shape, including tails. Compare the median line and the interquartile range across algorithms.

**`consistency.png`**
Coefficient of variation (CV = std/mean) of `avg_chain_length` per algorithm. Low CV means the algorithm produces consistent results across trials. High CV means high variance — the algorithm may be sensitive to seeds or problem structure.

**`heatmap.png`**
Algorithm × graph category heatmap of mean `avg_chain_length`. Cells are colour-coded: darker = longer chains. Useful for spotting which algorithms struggle with which categories.

### scaling/

Plots that show how performance changes as problem size grows.

**`scaling_chain.png`**
Mean `avg_chain_length` vs. `problem_nodes` with shaded ±1 std bands. Each algorithm is a separate line. Algorithms with flatter slopes scale better to larger problems.

**`scaling_time.png`**
Mean `wall_time` vs. `problem_nodes`. Reveals which algorithms have super-linear time complexity.

**`scaling_success.png`**
Success rate vs. `problem_nodes`. Shows where each algorithm begins to fail.

**`density_hardness.png`**
For random graphs only: mean `avg_chain_length` vs. edge density, with lines per algorithm. Embedding hardness typically peaks near the percolation threshold. This plot reveals whether algorithms differ in how they handle density.

### pairwise/

Direct algorithm-to-algorithm comparisons.

**`win_rate_heatmap.png`**
N×N matrix where cell (i, j) is the fraction of problems where algorithm i produced a shorter `avg_chain_length` than algorithm j. The diagonal is blank. Values above 0.5 mean algorithm i wins more often. Symmetric about the diagonal (cell (i,j) + cell (j,i) = 1.0).

**`head_to_head_<A>_vs_<B>.png`**
One plot per algorithm pair. X-axis: algorithm A's `avg_chain_length` per problem. Y-axis: algorithm B's `avg_chain_length` for the same problem. Points above the diagonal mean algorithm A won on that problem; points below mean B won. Useful for spotting when one algorithm consistently outperforms on specific problem types.

**`pareto.png`**
Scatter of mean `wall_time` vs. mean `avg_chain_length`, one point per algorithm. The Pareto frontier (algorithms that are not dominated in both dimensions) is highlighted. An algorithm on the frontier is optimal for some trade-off between speed and quality.

### success/

Success rate analysis.

**`success_heatmap.png`**
Algorithm × graph category heatmap of success rate. Cells range from 0 (never embeds) to 1 (always embeds). Identifies systematic failures by category.

**`success_by_nodes.png`**
Success rate vs. `problem_nodes`, one line per algorithm. Shows at what size each algorithm starts failing.

**`success_by_density.png`**
Success rate vs. problem edge density. For random graphs, this reveals whether failures cluster at high or low density.

### graph-indexed/

Plots that index results by individual graph properties rather than aggregating.

**`chain_by_graph_id.png`**
Mean `avg_chain_length` for each graph ID, grouped by algorithm. Useful for identifying specific graphs that are unusually hard.

**`chain_by_nodes.png`**
Per-graph mean `avg_chain_length` vs. that graph's node count. Scatter with a regression line per algorithm.

**`chain_by_density.png`**
Per-graph mean `avg_chain_length` vs. that graph's edge density.

### topology/

Performance broken down by hardware topology (only meaningful when multiple topologies were benchmarked).

**`topology_comparison.png`**
Grouped bar chart: algorithms on the x-axis, bars grouped by topology. Shows whether relative algorithm performance is consistent across hardware families.

**`topology_chain_distribution.png`**
Violin plots faceted by topology — the chain-length distribution for each algorithm on each topology.

---

## Tables

Tables are written to `analysis/tables/` in both CSV and LaTeX (`.tex`) formats.

### `overall_summary.csv`

One row per algorithm. Columns:

| Column | Description |
|---|---|
| `algorithm` | Algorithm name |
| `n_trials` | Total trial count (including failures) |
| `success_rate` | Fraction of trials that embedded successfully |
| `valid_rate` | Fraction of trials where the embedding passed structural validation |
| `time_mean` | Mean wall time per trial (seconds) |
| `time_std` | Standard deviation of wall time |
| `time_median` | Median wall time |
| `chain_mean` | Mean `avg_chain_length` across successful trials |
| `chain_std` | Standard deviation of `avg_chain_length` |
| `chain_median` | Median `avg_chain_length` |
| `max_chain_mean` | Mean `max_chain_length` |
| `qubits_mean` | Mean total qubits used |
| `qubit_overhead_mean` | Mean qubit overhead ratio (qubits used / problem nodes) |

### `summary_by_category.csv`

Algorithm × graph category matrix. Each cell is the mean `avg_chain_length` for that algorithm on that graph category. Missing cells (no successful trials in that category) are blank.

### `rank_table.csv`

One row per algorithm. For each (algorithm, problem, topology) triple, algorithms are ranked by `avg_chain_length` (lower is better). Columns:

| Column | Description |
|---|---|
| `algorithm` | Algorithm name |
| `mean_rank` | Mean rank across all problems (rank 1 = best) |
| `median_rank` | Median rank |
| `rank_std` | Standard deviation of rank |

---

## Statistics

Statistics files are written to `analysis/stats/`.

### `win_rate_matrix.csv`

N×N matrix (algorithms × algorithms). Cell (i, j) is the win rate of algorithm i over algorithm j: the fraction of problem instances where algorithm i achieved a shorter `avg_chain_length`. The diagonal is `NaN`. Complement: `win_rate[i,j] + win_rate[j,i] = 1.0`.

### `significance_tests.csv`

Pairwise Wilcoxon signed-rank test results with Holm–Bonferroni correction for multiple comparisons. One row per algorithm pair. Columns:

| Column | Description |
|---|---|
| `algo_a`, `algo_b` | Algorithm pair |
| `n_pairs` | Number of problems where both algorithms succeeded |
| `w_statistic` | Wilcoxon W statistic |
| `p_value` | Uncorrected p-value |
| `corrected_p` | Holm–Bonferroni corrected p-value |
| `significant` | True if `corrected_p < 0.05` |
| `effect_size` | Rank-biserial correlation r (0 = no effect, 1 = perfect) |

A row marked `significant=True` means the performance difference between the two algorithms is unlikely to be due to chance. The effect size indicates how large the difference is in practice.

### `friedman_test.json`

Friedman non-parametric ANOVA result for all algorithms simultaneously. Fields:

```json
{
  "statistic": 42.3,
  "p_value": 0.0001,
  "n_problems": 60,
  "n_algorithms": 4
}
```

A low p-value means at least one algorithm performs significantly differently from the others. Use the pairwise significance tests to identify which pairs differ.

### `correlation_matrix.csv`

Spearman rank correlation between graph structural properties and embedding metrics. Rows and columns are graph properties (nodes, edges, density, degree, etc.) and embedding metrics (avg_chain_length, wall_time, etc.). Values range from -1 to 1. Strong positive correlation (> 0.5) means graphs with that property tend to produce higher values of that metric.

---

## Python API

All outputs can also be generated from Python:

```python
from ember_qc_analysis import BenchmarkAnalysis

an = BenchmarkAnalysis("results/my_batch")

# Tables
print(an.overall_summary())
print(an.summary_by_category(metric="avg_chain_length"))
print(an.rank_table(metric="avg_chain_length"))

# Statistics
print(an.win_rate_matrix(metric="avg_chain_length"))
print(an.significance_tests(metric="avg_chain_length"))
print(an.friedman_test(metric="avg_chain_length"))
print(an.correlation_matrix())

# Full report
an.generate_report(output_root="~/analysis", overwrite=True, fig_format="pdf")
```
