# Post-Benchmark Analysis Module — Brainstorm

## Architecture Decision

The analysis functionality lives in a **separate `qeanalysis/` package**, not inside `qebench/`.

**Why separate?**
- `qebench` runs experiments — it imports C++ bindings, D-Wave stack, NetworkX topology graphs.
  The analysis module only needs CSV files; no quantum toolchain required.
- Different lifecycle: benchmarking is long-running and done once; analysis is iterated
  repeatedly while writing papers.
- Different dependencies: analysis needs `scipy` (Wilcoxon, Friedman), potentially
  `statsmodels`, heavier plotting. No reason to bloat the benchmark runner.
- Portability: a co-author or reviewer can run analysis on exported CSVs without
  installing D-Wave or minorminer at all.

**Directory layout:**
```
qeanalysis/             # The analysis package (source code)
├── __init__.py
├── loader.py           # Load + validate batch dir, derive computed columns
├── summary.py          # Aggregate tables (overall, by-category, rank)
├── plots.py            # All matplotlib/seaborn visualizations
├── statistics.py       # Wilcoxon, Friedman, correlation, significance
└── export.py           # LaTeX table generation, PDF plot export

analysis/               # Output directory (gitignored, like results/)
└── batch_2026-02-24_14-30-00/   # Named identically to the results batch
    ├── figures/                  # All generated plots (PNG + PDF)
    │   ├── scaling_time_vs_nodes.png
    │   ├── pareto_frontier.png
    │   └── ...
    └── tables/                   # All generated tables (CSV + .tex)
        ├── overall_summary.csv
        ├── overall_summary.tex
        ├── category_breakdown.csv
        └── ...
```

**Typical workflow:**
```python
# Step 1: Run benchmark (qebench) → writes results/batch_.../runs.csv
bench = EmbeddingBenchmark(...)
bench.run_full_benchmark(...)

# Step 2: Analyse (qeanalysis) → writes analysis/batch_.../
from qeanalysis import BenchmarkAnalysis
an = BenchmarkAnalysis("results/batch_2026-02-24_14-30-00/")
an.generate_report()   # runs everything, writes to analysis/<same-batch-name>/
```

---

This document brainstorms all desired analysis functionality.
The input is a completed benchmark batch directory (containing `runs.csv`, `runs.json`, `config.json`);
the output is tables, plots, and statistical summaries written to `analysis/<batch-name>/`.

---

## 1. Raw Data Available

Every row in `runs.csv` is one trial. The columns we can analyse are:

| Column | Type | Notes |
|--------|------|-------|
| `algorithm` | str | `minorminer`, `atom`, `oct-triad`, etc. |
| `problem_name` | str | `K10`, `grid_4x4`, `random_n15_d0.5_i0`, etc. |
| `topology_name` | str | `chimera_4x4x4`, `pegasus_16`, etc. |
| `trial` | int | Trial index within a run |
| `success` | bool | Whether an embedding was returned |
| `is_valid` | bool | Whether the embedding passes all validity checks |
| `embedding_time` | float | Seconds to find (or fail to find) the embedding |
| `avg_chain_length` | float | Mean physical qubits per logical qubit |
| `max_chain_length` | int | Length of longest chain |
| `total_qubits_used` | int | Total physical qubits across all chains |
| `total_couplers_used` | int | Physical couplers used for intra-chain connectivity |
| `problem_nodes` | int | Number of logical qubits (source graph |V|) |
| `problem_edges` | int | Number of logical edges (source graph |E|) |
| `problem_density` | float | 2|E| / (|V|(|V|-1)) |

Graph category is derivable from the `problem_name` prefix:
- `K*` → complete
- `bipartite_*` → bipartite
- `grid_*` → grid
- `cycle_*` → cycle
- `tree_*` → tree
- `petersen`, `dodecahedral`, `icosahedral` → special
- `random_*` → random (with embedded n, density, instance)

---

## 2. Analysis Views We Want

### 2.1 Per-Algorithm Aggregate Table

A single summary row per algorithm across all problems and topologies.

| Metric | Description |
|--------|-------------|
| Overall success rate | % of all trials that returned an embedding |
| Overall valid rate | % of all trials that produced a valid embedding |
| Mean / median embedding time | Over successful trials only |
| Std dev of embedding time | Consistency indicator |
| Mean avg chain length | Quality — lower is better |
| Mean max chain length | Worst-case chain overhead |
| Mean total qubits used | Physical resource consumption |
| Mean qubit overhead ratio | `total_qubits_used / problem_nodes` — ideal = 1 |
| Mean coupler overhead | `total_couplers_used / problem_edges` |

**Purpose:** Top-level leaderboard for papers. One table → instant ranking.

---

### 2.2 Per-Category Breakdown

Repeat the aggregate table but group by graph category: complete, bipartite, grid, cycle, tree, special, random.

**Key questions answered:**
- Which algorithm dominates on dense graphs (complete, bipartite)?
- Which is best on sparse graphs (tree, cycle, grid)?
- Does any algorithm collapse specifically on random graphs?
- How does performance change from structured to unstructured problems?

**Output:** One summary table per category, or a single matrix table:

```
               complete  bipartite  grid   cycle   tree   special  random
minorminer       2.1       1.8      1.3    1.1     1.0     2.4      1.7
atom             2.3       2.0      1.4    1.2     1.1     2.6      1.9
oct-triad        2.8       2.2      1.5    1.2     1.1     2.9      2.1
                       (avg_chain_length, lower is better)
```

---

### 2.3 Scaling Analysis

How do metrics grow as the problem gets harder?

**X-axis options:**
- `problem_nodes` — size scaling
- `problem_edges` — edge scaling
- `problem_density` — density scaling (for random graphs especially)

**Y-axis options (one plot per):**
- `embedding_time` — time complexity
- `avg_chain_length` — quality degradation with size
- `total_qubits_used` — resource scaling
- `max_chain_length` — worst-case overhead growth

**Per-algorithm line plots** with:
- Mean ± 1 std error ribbon across trials and instances at each x-value
- Optional polynomial/exponential curve fit with R² displayed
- Log-log version to estimate complexity class (O(n), O(n²), etc.)

**Key questions:**
- Does minorminer scale polynomially or worse?
- Does ATOM's time grow faster than minorminer past n=15?
- Does density increase chain length linearly or faster?

---

### 2.4 Density-Hardness Analysis

Specifically for the random graph suite: at fixed n, how does density
affect each metric?

Plot: `density` (x) vs. `avg_chain_length` / `embedding_time` (y),
one line per algorithm per fixed n-value.

Expected finding: embedding generally gets harder as density increases
(more edges → longer chains needed), but algorithms may hit different
inflection points.

---

### 2.5 Head-to-Head Pairwise Comparison

For every pair of algorithms (A, B), across all problems where both succeeded:

**Scatter:** A's metric on x-axis, B's metric on y-axis, one point per problem.
Points above the diagonal → B wins. Points below → A wins.

**Win rate table:** For metric `avg_chain_length`:

```
        minorminer  atom  oct-triad  oct-fast-oct
minorminer    —      62%     55%         48%
atom         38%      —      51%         44%
...
                 (% of problems where row algo beats column algo)
```

**Improvement plot:** For each problem where A beats B, plot the percentage
improvement in chain quality. Highlights which problem types show the biggest
advantage.

---

### 2.6 Pareto Frontier Plot

Scatter plot: `embedding_time` (x) vs. `avg_chain_length` (y).
One point per (algorithm, problem) — or averaged across trials.

Points on the lower-left Pareto frontier are the best trade-offs:
fast AND high quality. Points on the frontier should be highlighted/labeled.

**Per-topology version:** Separate plots or facets for Chimera, Pegasus, Zephyr.

---

### 2.7 Trial Consistency / Variance Analysis

For algorithms with multiple trials, measure run-to-run consistency.

**Metrics:**
- Coefficient of variation (CV = std/mean) for embedding_time per (algo, problem)
- Same for avg_chain_length
- Box plots or violin plots to show spread

**Key question:** Is minorminer consistent? (It is stochastic — we expect higher variance than ATOM.)

**Inter-trial range:** max - min across trials for chain length and time.
If an algorithm sometimes finds excellent embeddings and sometimes terrible ones,
the range is wide — makes it risky for practical use.

---

### 2.8 Topology Comparison

When multiple topologies are included in a run:
- Same problem on Chimera vs. Pegasus vs. Zephyr
- Qubit utilization rate: `total_qubits_used / topology_total_qubits` — how much of the hardware is consumed?
- Do certain algorithms make better use of denser topologies (Pegasus > Chimera)?
- Does success rate differ by topology for the same problem?

**Output:** Grouped bar chart — one group per topology, bars per algorithm.

---

### 2.9 Per-Problem Deep Dive

For a single specified problem (e.g., K10), show all algorithms side by side:

- Bar chart: avg_chain_length per algorithm
- Bar chart: embedding_time per algorithm
- Success/validity status per algorithm
- Best embedding found: chain length distribution histogram (per-chain breakdown)

**Use case:** When writing a paper section about a specific instance.

---

### 2.10 Chain Length Distribution

For a selected algorithm (or all algorithms side by side):

- Histogram / KDE of `avg_chain_length` across all problems
- Separate histogram of `max_chain_length`
- Max-to-avg ratio: `max_chain_length / avg_chain_length` — a well-balanced
  embedding has this close to 1

**Violin plot version:** One violin per algorithm showing the full distribution
of avg_chain_length values across all tested problems.

---

### 2.11 Correlation Analysis

Compute Pearson/Spearman correlations between graph properties and embedding metrics:

| Graph property | Metric to correlate |
|----------------|---------------------|
| `problem_nodes` | `embedding_time` |
| `problem_edges` | `total_qubits_used` |
| `problem_density` | `avg_chain_length` |
| `problem_density` | `success` (point-biserial) |
| `problem_nodes` | `max_chain_length` |

**Output:** Correlation matrix heatmap, one per algorithm.

**Hypothesis to test:** Is density a stronger predictor of chain length than node count?

---

### 2.12 Statistical Significance Testing

Before claiming "Algorithm A is better than B", test significance.

**Wilcoxon signed-rank test** (non-parametric, paired):
- Null hypothesis: no difference in median chain length between A and B on the same problems
- Output p-values in the head-to-head comparison table

**Friedman test** (multi-algorithm extension of Wilcoxon):
- Rank all algorithms on each problem, test if the rank distribution differs across algorithms

**Multiple comparisons correction:** Bonferroni or Holm correction when testing many pairs.

**Output:** p-value tables, significance markers (* p<0.05, ** p<0.01, *** p<0.001).

---

### 2.13 Rank Aggregation

For each problem, rank all algorithms by a given metric (1 = best).
Then aggregate ranks across problems.

**Mean rank table:**
```
Algorithm    | Time rank | Chain rank | Overall avg rank
minorminer   |    2.1    |    1.8     |     1.95
atom         |    3.2    |    2.1     |     2.65
oct-triad    |    1.3    |    3.5     |     2.40
```

**Rank distribution:** For each algorithm, histogram of ranks across problems.
An algorithm that is consistently 2nd place may be better than one that is
sometimes 1st but often 4th.

---

### 2.14 Validity Rate Analysis

Separate from success rate: how often do returned embeddings actually pass
all validity checks?

- Validity rate per (algorithm, category)
- Which graph types cause validity failures for `oct-hybrid-oct`?
- Do larger graphs produce more invalidity?

**Invalidity breakdown:** Would require extending the framework to record *why*
validation failed (chain disconnected? node coverage? edge missing?) — flag for
future implementation.

---

### 2.15 Timeout / Failure Analysis

- Timeout rate per algorithm (failures where `embedding_time ≈ timeout`)
- True failure rate (algorithm ran but returned nothing, not a timeout)
- Error message frequency (group error strings, count occurrences)

---

## 3. Visualizations Summary

| Plot | X | Y | Grouping |
|------|---|---|----------|
| Heatmap | graph category | algorithm | metric value (color) |
| Line plot | problem_nodes | embedding_time | algorithm (color) |
| Line plot | problem_density | avg_chain_length | algorithm × n (color+linestyle) |
| Box / violin | algorithm | avg_chain_length | facets by category |
| Scatter | embedding_time | avg_chain_length | algorithm (color), Pareto frontier |
| Scatter | A's chain length | B's chain length | — (pairwise comparison) |
| Bar chart | algorithm | metric | grouped by topology |
| Bar chart | algorithm | metric | single problem deep dive |
| Histogram | avg_chain_length | count | per algorithm (overlaid) |
| Correlation heatmap | graph properties | embedding metrics | per algorithm |
| Rank distribution | rank (1–N) | frequency | per algorithm |

All plots should:
- Use a consistent color palette per algorithm (defined once, used everywhere)
- Be exportable as PNG (300 dpi) and PDF for vector/LaTeX inclusion
- Have clear axis labels and titles

---

## 4. Paper-Ready Table Exports

For inclusion in papers, the module should export:

| Table | Format | Contents |
|-------|--------|----------|
| Overall leaderboard | LaTeX + CSV | One row per algorithm, all aggregate metrics |
| Per-category breakdown | LaTeX | Metric value per (algo, category) |
| Head-to-head win rates | LaTeX | Algorithm × algorithm win percentage matrix |
| Statistical significance | LaTeX | Wilcoxon p-values between all pairs |
| Rank aggregation | LaTeX | Mean rank per algorithm per metric |
| Scaling fit parameters | CSV | Fitted exponent / R² for time-vs-nodes |

LaTeX tables should be publication-ready: `booktabs` formatting,
proper `\multicolumn` headers, caption + label arguments.

---

## 5. Proposed Module Interface

```python
from qeanalysis import BenchmarkAnalysis

# Load from a results batch directory; output goes to analysis/<batch-name>/
an = BenchmarkAnalysis("results/batch_2026-02-24_14-30-00/")
# or: an = BenchmarkAnalysis.from_csv("results/batch_.../runs.csv")

# ── Summary tables ────────────────────────────────────────────────────────────
an.overall_summary()                      # DataFrame: one row per algorithm
an.summary_by_category("avg_chain_length")  # DataFrame: algo × category matrix
an.rank_table("avg_chain_length")         # Mean rank per algorithm

# ── Comparisons ───────────────────────────────────────────────────────────────
an.head_to_head("minorminer", "atom")     # Scatter + win rate for one pair
an.win_rate_matrix("avg_chain_length")    # Full N×N win rate table
an.pareto_plot("embedding_time", "avg_chain_length")  # Pareto frontier scatter

# ── Scaling ───────────────────────────────────────────────────────────────────
an.scaling_plot("embedding_time", x="problem_nodes", log=True)
an.density_plot("avg_chain_length")       # Random graphs: density vs metric

# ── Distributions ─────────────────────────────────────────────────────────────
an.distribution_plot("avg_chain_length")  # Violin / box per algorithm
an.consistency_plot()                     # CV of time and chain length

# ── Deep dives ────────────────────────────────────────────────────────────────
an.problem_deep_dive("K10")              # All algorithms on one problem
an.topology_comparison("avg_chain_length")  # Bar chart across topologies
an.correlation_matrix()                  # Graph properties vs. metrics heatmap

# ── Statistics ────────────────────────────────────────────────────────────────
an.significance_tests("avg_chain_length")  # Wilcoxon p-values, all pairs

# ── Exports ───────────────────────────────────────────────────────────────────
an.export_latex("paper_tables/")         # All tables as .tex files
an.export_plots("paper_figures/", fmt="pdf")  # All plots as PDFs
an.generate_report("analysis_report/")  # HTML or Markdown report with everything
```

---

## 6. Design Decisions to Make Before Building

1. **Module location:** `qeanalysis/` package at repo root, sibling to `qebench/`.
   Output always goes to `analysis/<batch-name>/` (gitignored like `results/`).

2. **Input flexibility:**
   - Load from batch directory path (reads `runs.csv` + `config.json` automatically)
   - Load from a list of batch directories (merge multiple runs for comparison)
   - Load from a raw DataFrame (for programmatic use)

3. **Derived columns to pre-compute at load time:**
   - `category` (from `problem_name` prefix)
   - `qubit_overhead_ratio` = `total_qubits_used / problem_nodes`
   - `coupler_overhead_ratio` = `total_couplers_used / problem_edges` (guard div-by-zero)
   - `max_to_avg_chain_ratio` = `max_chain_length / avg_chain_length`
   - `is_timeout` (bool: `embedding_time >= timeout - epsilon`)

4. **Missing data policy:**
   - Failed trials (success=False) should be excluded from quality metrics
     (time, chain length) but included in success/validity rate computations
   - Clearly document which metrics include failures and which exclude them

5. **Multi-topology runs:**
   - All topology-sensitive analyses should have a `topology=` filter argument
   - Default: aggregate over all topologies (averaged or separately)

6. **Plot style:**
   - Define a fixed algorithm color map at module level
   - Use matplotlib + seaborn for consistency with existing code
   - All figures should be returned AND optionally saved (don't always write to disk)

7. **Statistical test scope:**
   - Only run significance tests when there are ≥ 3 paired observations
   - Report effect size (Cohen's d or rank-biserial r) alongside p-values

---

## 7. Specific Questions the Analysis Should Answer

These are the concrete research questions the papers will address:

**Paper 1 — QEBench benchmark:**
1. What is the overall ranking of algorithms across all test graphs?
2. On which graph categories does each algorithm perform best/worst?
3. How does performance scale with graph size?
4. Which algorithm gives the best time/quality trade-off?

**Paper 2 — Problem structure and embedding difficulty:**
5. Which graph properties (density, treewidth, clustering) predict embedding difficulty?
6. Do structured graphs (complete, bipartite) embed differently from random ones of the same size?
7. Is there a density threshold where embedding quality degrades sharply?
8. Which algorithm is most robust to graph structure variation?

**Paper 3 — Novel algorithm evaluation:**
9. On which specific problem classes does the new algorithm outperform existing ones?
10. Is the improvement statistically significant?
11. What is the overhead cost (time) relative to the quality gain?
12. Does performance hold across all three topology families?

---

## 8. Priority Order for Implementation

1. **Load + derive columns** — the foundation everything else needs
2. **Overall summary table** — first thing needed for any paper
3. **Summary by category** — immediately useful for Paper 1
4. **Scaling plots** — high visual impact, needed early
5. **Head-to-head + win rate matrix** — core comparison tool
6. **Pareto plot** — useful visual for the time/quality trade-off
7. **Distribution plots** (violin/box) — shows variance, important for stats
8. **Statistical significance tests** — needed before any claim about ranking
9. **Correlation matrix** — needed for Paper 2
10. **LaTeX export** — needed once results are final for papers
11. **HTML/Markdown report generator** — convenience wrapper over everything else
