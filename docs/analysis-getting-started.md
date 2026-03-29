# Getting Started with ember-qc-analysis

`ember-qc-analysis` processes completed EMBER benchmark batches and produces plots, tables, and statistics. It has no quantum dependencies and can be installed on any machine.

---

## 1. Install

```bash
pip install ember-qc-analysis
```

Or together with ember-qc:

```bash
pip install ember-qc[analysis]
```

Verify:

```bash
ember-analysis version
```

Both `ember-analysis` and `ember-a` call the same entry point.

---

## 2. Point it at your results

You need a completed EMBER batch directory — one that contains `results.db` or `runs.csv`.

Set the input directory (where your batch directories live):

```bash
ember-analysis config set input_dir ~/results
```

Or use an environment variable:

```bash
export EMBER_ANALYSIS_INPUT_DIR=~/results
```

If `ember-qc` is installed on the same machine, `ember-analysis` can discover its output directory automatically the first time you run a command.

---

## 3. Stage a batch

If your input directory contains multiple batches, stage the one you want to work on:

```bash
ember-analysis batches list                  # see all available batches
ember-analysis stage results/my_batch_2026-03-28
```

`stage` validates that the directory is a valid batch and prints a summary:

```
Staged: my_batch_2026-03-28
  Algorithms: minorminer, clique
  Topology:   pegasus_16
  Graphs:     6
  Trials:     3 per combination
```

If your input directory contains exactly one batch, you do not need to stage — commands fall back to it automatically.

To clear the staged batch:

```bash
ember-analysis unstage
```

---

## 4. Run the full report

```bash
ember-analysis report
```

This generates:
- All plot groups (distributions, scaling, pairwise, success, graph-indexed, topology)
- Summary tables in CSV and LaTeX
- Statistical tests (significance, Friedman, win-rate matrix, correlations)

Output is written to `<batch_dir>/analysis/` by default. To specify a different location:

```bash
ember-analysis report -o /path/to/output
```

To regenerate all files even if they already exist:

```bash
ember-analysis report --overwrite
```

Change the figure format (default: png):

```bash
ember-analysis report -f pdf
```

---

## 5. View the output

```
my_batch_2026-03-28/
└── analysis/
    ├── plots/
    │   ├── distributions/
    │   ├── scaling/
    │   ├── pairwise/
    │   ├── success/
    │   ├── graph-indexed/
    │   └── topology/
    ├── tables/
    │   ├── overall_summary.csv
    │   ├── summary_by_category.csv
    │   ├── rank_table.csv
    │   └── *.tex
    └── stats/
        ├── win_rate_matrix.csv
        ├── significance_tests.csv
        ├── friedman_test.json
        └── correlation_matrix.csv
```

See [analysis-outputs.md](analysis-outputs.md) for a description of every file.

---

## 6. Run selectively

Generate only specific output types:

```bash
ember-analysis plots distributions pairwise     # specific plot groups
ember-analysis plots                            # all plot groups
ember-analysis plots --list                     # see available groups
ember-analysis tables                           # tables only
ember-analysis stats                            # statistics only
```

---

## 7. From the benchmark run

To generate a report automatically after `ember run`:

```bash
ember run experiment.yaml --analyze
```

---

## 8. Configuration

```bash
ember-analysis config show                          # all settings
ember-analysis config set output_dir ~/analysis     # default output location
ember-analysis config set fig_format pdf            # default figure format
ember-analysis config get input_dir                 # check a specific value
ember-analysis config path                          # config file location
```

Config keys:

| Key | Default | Description |
|---|---|---|
| `input_dir` | none | Directory containing batch subdirectories |
| `output_dir` | `<batch>/analysis/` | Where analysis outputs are written |
| `fig_format` | `png` | Figure format: `png`, `pdf`, or `svg` |
| `active_batch` | none | Currently staged batch path |

Environment variables: `EMBER_ANALYSIS_INPUT_DIR`, `EMBER_ANALYSIS_OUTPUT_DIR`, `EMBER_ANALYSIS_FIG_FORMAT`.

---

## 9. Use the Python API directly

```python
from ember_qc_analysis import BenchmarkAnalysis

an = BenchmarkAnalysis(
    batch_dir="results/my_batch_2026-03-28",
    output_root="~/analysis",
)

# Full report
an.generate_report()

# Individual components
summary = an.overall_summary()
print(summary[["success_rate", "avg_chain_length_mean"]])

win_matrix = an.win_rate_matrix(metric="avg_chain_length")
print(win_matrix)
```

See [analysis-outputs.md](analysis-outputs.md) for the full list of methods and what they return.
