# CLI Reference — ember-analysis

Both `ember-analysis` and `ember-a` invoke the same entry point. Run `ember-analysis --help` or `ember-analysis <command> --help` at any time.

---

## ember-analysis stage

Set the active batch context.

```
ember-analysis stage BATCH_DIR
```

Validates that `BATCH_DIR` is a valid ember-qc batch (contains `results.db`) and saves it as the active batch. Subsequent commands that need a batch use this path.

```bash
ember-analysis stage results/my_benchmark_2026-03-28
```

Prints batch metadata on success:

```
Staged: my_benchmark_2026-03-28
  Algorithms: minorminer, clique
  Topology:   pegasus_16
  Graphs:     6
  Trials:     3 per combination
```

---

## ember-analysis unstage

Clear the active batch context.

```
ember-analysis unstage
```

After unstaging, commands that need a batch fall back to automatic discovery from `input_dir`.

---

## ember-analysis report

Run the full analysis pipeline on the active batch.

```
ember-analysis report [-o PATH] [-f FMT] [--overwrite]
```

| Flag | Description |
|---|---|
| `-o, --output-dir PATH` | Override output directory (default: `<batch>/analysis/`) |
| `-f, --format FMT` | Figure format: `png`, `pdf`, or `svg` (default: `png`) |
| `--overwrite` | Regenerate files even if they already exist |

Generates all plots, tables, and statistics files. Output layout:

```
<output_dir>/
├── plots/
│   ├── distributions/
│   ├── scaling/
│   ├── pairwise/
│   ├── success/
│   ├── graph-indexed/
│   └── topology/
├── tables/
└── stats/
```

```bash
ember-analysis report
ember-analysis report -o ~/my_analysis -f pdf
ember-analysis report --overwrite
```

---

## ember-analysis plots

Generate plot groups selectively.

```
ember-analysis plots [GROUP...] [-o PATH] [-f FMT] [--overwrite] [--list]
```

| Argument / Flag | Description |
|---|---|
| `GROUP` | One or more plot group names (space-separated); omit for all groups |
| `-o, --output-dir PATH` | Override output directory |
| `-f, --format FMT` | Figure format: `png`, `pdf`, or `svg` |
| `--list` | Print available plot groups and exit |
| `--overwrite` | Regenerate existing files |

**Plot groups:**

| Group | Description |
|---|---|
| `distributions` | Embedding metric distributions: chain length KDE, violin plots, consistency |
| `scaling` | Performance scaling with problem size: metric vs. nodes with std bands |
| `pairwise` | Algorithm pairwise comparisons: win-rate heatmap, head-to-head scatter |
| `success` | Success rate analysis: by category, by node count, by density |
| `graph-indexed` | Metrics indexed by graph ID, node count, and density |
| `topology` | Performance by hardware topology: grouped bars, Pareto frontier |

```bash
ember-analysis plots                          # all groups
ember-analysis plots distributions pairwise  # specific groups
ember-analysis plots --list                  # show available groups
ember-analysis plots -f pdf --overwrite
```

---

## ember-analysis tables

Generate summary tables in CSV and LaTeX.

```
ember-analysis tables [-o PATH] [--overwrite]
```

| Flag | Description |
|---|---|
| `-o, --output-dir PATH` | Override output directory |
| `--overwrite` | Regenerate existing files |

Produces:
- `overall_summary.csv` / `.tex` — one row per algorithm
- `summary_by_category.csv` / `.tex` — algorithm × graph category matrix
- `rank_table.csv` / `.tex` — mean and median rank per algorithm

```bash
ember-analysis tables
ember-analysis tables -o ~/paper/tables
```

---

## ember-analysis stats

Run statistical analysis.

```
ember-analysis stats [-o PATH] [--overwrite]
```

| Flag | Description |
|---|---|
| `-o, --output-dir PATH` | Override output directory |
| `--overwrite` | Regenerate existing files |

Produces:
- `win_rate_matrix.csv` — pairwise win rates
- `significance_tests.csv` — Wilcoxon signed-rank tests with Holm–Bonferroni correction
- `friedman_test.json` — Friedman non-parametric ANOVA result
- `correlation_matrix.csv` — Spearman correlations between graph properties and embedding metrics

```bash
ember-analysis stats
```

---

## ember-analysis batches

List and inspect available batches.

### ember-analysis batches list

```
ember-analysis batches list [-i PATH]
```

| Flag | Description |
|---|---|
| `-i, --input-dir PATH` | Override input directory |

Lists all valid ember-qc batch directories under the configured input directory.

```bash
ember-analysis batches list
ember-analysis batches list -i ~/results
```

### ember-analysis batches show

```
ember-analysis batches show BATCH_ID
```

Prints the summary for a specific batch.

---

## ember-analysis config

Manage persistent configuration.

### ember-analysis config show

```
ember-analysis config show
```

Prints all config keys, their values, and where each value comes from.

### ember-analysis config get

```
ember-analysis config get KEY
```

Prints the resolved value for one key.

### ember-analysis config set

```
ember-analysis config set KEY VALUE
```

Sets a persistent config value.

**Config keys:**

| Key | Type | Default | Env variable |
|---|---|---|---|
| `input_dir` | string | none | `EMBER_ANALYSIS_INPUT_DIR` |
| `output_dir` | string | `<batch>/analysis/` | `EMBER_ANALYSIS_OUTPUT_DIR` |
| `fig_format` | string | `png` | `EMBER_ANALYSIS_FIG_FORMAT` |
| `active_batch` | string | none | — |

### ember-analysis config reset

```
ember-analysis config reset
```

Deletes the config file and reverts all keys to defaults.

### ember-analysis config path

```
ember-analysis config path
```

Prints the path to the config file. On macOS: `~/Library/Application Support/ember-qc-analysis/config.json`.

---

## ember-analysis version

```
ember-analysis version
```

Prints the installed `ember-qc-analysis` package version.
