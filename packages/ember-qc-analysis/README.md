# ember-qc-analysis

Post-benchmark analysis for EMBER. Processes completed `ember-qc` benchmark batches and produces plots, tables, and statistical tests.

No quantum dependencies — install on any machine.

---

## Installation

```bash
pip install ember-qc-analysis
```

Or together with the benchmark runner:

```bash
pip install ember-qc[analysis]
```

Requires Python 3.10+.

---

## Quick Start

**Stage a batch and generate a full report:**

```bash
ember-analysis stage results/my_benchmark_2026-03-28
ember-analysis report
```

**Or run analysis automatically after a benchmark:**

```bash
ember run experiment.yaml --analyze
```

**Outputs** are written to `<batch_dir>/analysis/`:

```
analysis/
├── plots/
│   ├── distributions/    — chain length KDE, violin plots, consistency
│   ├── scaling/          — performance vs. problem size
│   ├── pairwise/         — win-rate heatmap, head-to-head scatter, Pareto
│   ├── success/          — success rate by category, nodes, density
│   ├── graph-indexed/    — metrics indexed by graph properties
│   └── topology/         — performance by hardware topology
├── tables/
│   ├── overall_summary.csv/.tex
│   ├── summary_by_category.csv/.tex
│   └── rank_table.csv/.tex
└── stats/
    ├── win_rate_matrix.csv
    ├── significance_tests.csv
    ├── friedman_test.json
    └── correlation_matrix.csv
```

---

## CLI Reference

Both `ember-analysis` and `ember-a` invoke the same entry point.

```
ember-analysis stage <batch_dir>            Set the active batch
ember-analysis unstage                      Clear the active batch
ember-analysis report [-o PATH] [-f FMT]    Run the full analysis pipeline
ember-analysis plots [GROUP...] [-f FMT]    Generate specific plot groups
ember-analysis tables [-o PATH]             Generate summary tables
ember-analysis stats [-o PATH]              Run statistical tests
ember-analysis batches list                 List available batches
ember-analysis config show/set/get/reset    Manage configuration
ember-analysis version                      Show package version
```

---

## Python API

```python
from ember_qc_analysis import BenchmarkAnalysis

an = BenchmarkAnalysis("results/my_batch")

# Tables
summary = an.overall_summary()          # one row per algorithm
by_cat  = an.summary_by_category()      # algorithm × graph category
ranks   = an.rank_table()               # mean rank per algorithm

# Statistics
win_matrix = an.win_rate_matrix()       # N×N pairwise win rates
sig_tests  = an.significance_tests()    # Wilcoxon + Holm-Bonferroni
friedman   = an.friedman_test()         # non-parametric multi-algorithm ANOVA
corr       = an.correlation_matrix()    # Spearman: graph properties vs. metrics

# Full report
an.generate_report(
    output_root="~/analysis",
    overwrite=True,
    fig_format="pdf",
)
```

---

## Configuration

```bash
ember-analysis config set input_dir ~/results       # directory containing batch subdirectories
ember-analysis config set output_dir ~/analysis     # override default output location
ember-analysis config set fig_format pdf            # default figure format (png/pdf/svg)
ember-analysis config show                          # all settings
```

Environment variables: `EMBER_ANALYSIS_INPUT_DIR`, `EMBER_ANALYSIS_OUTPUT_DIR`, `EMBER_ANALYSIS_FIG_FORMAT`.

---

## Documentation

- [Getting Started](https://github.com/zachmacsmith/ember/blob/main/docs/analysis-getting-started.md)
- [CLI Reference](https://github.com/zachmacsmith/ember/blob/main/docs/analysis-cli-reference.md)
- [Analysis Outputs](https://github.com/zachmacsmith/ember/blob/main/docs/analysis-outputs.md) — every plot and table explained

---

## License

MIT
