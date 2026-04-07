# Getting Started with EMBER

EMBER benchmarks minor embedding algorithms on quantum annealing hardware topologies. It runs entirely locally — no quantum hardware or cloud account required.

This tutorial takes you from installation to a completed benchmark with results in about 15 minutes.

---

## 1. Install

```bash
pip install ember-qc
```

To also install the companion analysis package:

```bash
pip install ember-qc[analysis]
```

Requires Python 3.10+.

Verify the installation:

```bash
ember version
```

---

## 2. Check your configuration

Before running anything, confirm the defaults:

```bash
ember config show
```

Output:

```
Key                  Value          Source
-------------------  -------------  --------
output_dir           (not set)      default
default_workers      1              default
default_timeout      60.0           default
default_topology     (not set)      default
default_graphs       (not set)      default
default_n_trials     1              default
default_warmup_trials 0             default
default_seed         42             default
default_fault_rate   0.0            default
log_level            WARNING        default
```

`output_dir` being unset means results are written to `./results/` relative to your **current working directory** when you run `ember run`. Change it to a permanent location with:

```bash
ember config set output_dir ~/results
```

Run `ember config show` at any time if results appear in an unexpected location — it will tell you exactly which directory `ember` is writing to and where each setting came from.

---

## 3. Check what is available

EMBER ships with several algorithms. Some require optional binaries.

```bash
ember algos list
```

You will see output like:

```
Algorithm              Available   Note
---------------------  ----------  ----------------------------
minorminer             ✓
minorminer-fast        ✓
minorminer-aggressive  ✓
minorminer-chainlength ✓
clique                 ✓
pssa                   ✓
atom                   ✗           run: ember install-binary atom
oct-fast-oct           ✗           run: ember install-binary oct
charme                 ✗           pip install ember-qc[charme]
```

For this tutorial, `minorminer` and `clique` are sufficient.

---

## 4. Explore the graph library

EMBER provides access to **31,083 graphs** across 36 types. 37 graphs are bundled with the package for offline use; all others are downloaded on demand and cached locally.

```bash
# Type overview: all 36 types with ID ranges and counts
ember graphs list

# All graphs of one type
ember graphs list complete
ember graphs list random_er

# Installed types/graphs only
ember graphs list -a

# Full metadata for a single graph
ember graphs info 1004

# Search by property
ember graphs search --type complete --max-nodes 20

# List all named presets with resolved counts
ember graphs presets
```

To install additional graphs before running a benchmark:

```bash
ember graphs install benchmark       # ~82 graphs curated for benchmarking
ember graphs install 1000-1055       # all complete graphs
ember graphs install --dry-run default   # preview without downloading
```

See [graph-library.md](graph-library.md) for the full type table, ID ranges, selection syntax, and all presets.

---

## 5. Check hardware topologies

```bash
ember topologies list
```

Output:

```
Name              Family    Nodes   Edges
----------------  --------  ------  ------
chimera_4x4x4     chimera      128     352
chimera_16x16x4   chimera    2,048   6,016
pegasus_4         pegasus      594   2,816
pegasus_16        pegasus    5,640  40,484
zephyr_4          zephyr       272   2,016
zephyr_12         zephyr     4,800  45,864
```

For this tutorial we use `pegasus_16` — the topology that matches D-Wave's Advantage processor.

---

## 6. Write an experiment file

Create a file called `experiment.yaml`:

```yaml
name: my_first_benchmark
algorithms:
  - minorminer
  - clique
graphs: installed
topologies:
  - pegasus_16
trials: 3
timeout: 60.0
seed: 42
```

What each key means:

- `name` — label for this experiment; used in the output directory name
- `algorithms` — which algorithms to compare
- `graphs` — a preset name or selection expression (see [graph-library.md](graph-library.md))
- `topologies` — hardware topology to embed onto
- `trials` — how many independent trials per (algorithm, graph, topology) combination
- `timeout` — seconds allowed per trial before marking TIMEOUT
- `seed` — master seed for reproducibility; all trial seeds are derived from this

The `installed` preset runs only the 37 graphs bundled with the package — no downloads needed. To run more graphs, use `benchmark`, `diverse`, or any selection expression.

See [experiment-yaml.md](experiment-yaml.md) for the full key reference including defaults.

---

## 7. Run the benchmark

```bash
ember run experiment.yaml
```

You will see a progress bar. Each cell is one trial.

```
my_first_benchmark  [pegasus_16]  ████████████████████  18/18  02:14
```

When complete:

```
Results written to: results/my_first_benchmark_2026-03-28_14-30-00
```

**Where are my results?** By default, results are written to `./results/` relative to your current directory. To use a different location, set `output_dir` in config (step 2) or pass `--output-dir` to `ember run`.

Two files are also written alongside the results:

- `experiment.yaml` — verbatim copy of your input
- `experiment_resolved.yaml` — all parameters as actually used, including filled-in defaults

---

## 8. View results

```bash
ember results list
```

```
Batch ID                                    Algorithms         Graphs  Trials
------------------------------------------  -----------------  ------  ------
my_first_benchmark_2026-03-28_14-30-00      minorminer, clique     37       3
```

```bash
ember results show my_first_benchmark_2026-03-28_14-30-00
```

This prints a summary table:

```
Algorithm     Success   Avg Chain   Max Chain   Qubits   Time (s)
-----------   -------   ---------   ---------   ------   --------
minorminer      100%        2.4         4.0        14.2      1.3
clique          100%        4.0         4.0        16.0      0.1
```

---

## 9. Understand the output directory

```
results/my_first_benchmark_2026-03-28_14-30-00/
├── config.json              — all run parameters + environment provenance
├── results.db               — SQLite database with all trial data
├── runs.csv                 — every trial as a CSV row (for spreadsheets/pandas)
├── summary.csv              — grouped averages per (algorithm, topology)
├── README.md                — human-readable batch summary
├── experiment.yaml          — copy of your input file
├── experiment_resolved.yaml — fully resolved parameters used
└── workers/
    └── worker_*.jsonl         — raw per-trial records written during the run
```

To load results into Python:

```python
import sqlite3, pandas as pd

con = sqlite3.connect("results/my_first_benchmark_.../results.db")
df = pd.read_sql("SELECT * FROM runs", con)
print(df[["algorithm", "graph_name", "success", "avg_chain_length"]].head())
```

See [results-schema.md](results-schema.md) for all column definitions.

---

## 10. Configuration and priority

EMBER resolves every setting from four sources in this order (highest wins):

1. **CLI flag** — `ember run experiment.yaml --workers 4 --timeout 30`
2. **YAML key** — field in your experiment file
3. **Environment variable** — `EMBER_WORKERS=4`, `EMBER_OUTPUT_DIR=/results`
4. **Stored config** — set with `ember config set key value`
5. **Package default** — built-in fallback

This means: if you set `default_workers: 4` in your YAML, it overrides the stored config. If you pass `--workers 8` on the CLI, that overrides the YAML. Run `ember config show` to check what is currently stored.

**Common configuration tasks:**

```bash
ember config set output_dir ~/results          # permanent output location
ember config set default_workers 8             # run 8 trials in parallel
ember config set default_timeout 120.0         # allow 2 min per trial
ember config set default_seed 42               # same seed for all experiments
```

**Workers guidance:** Use `workers: 1` (the default) when debugging — single-worker mode makes failures easier to diagnose because errors appear directly in the terminal. Increase workers once the experiment is validated and you need throughput.

---

## 11. Generate an analysis report (optional)

If you installed `ember-qc-analysis`:

```bash
ember-analysis stage results/my_first_benchmark_2026-03-28_14-30-00
ember-analysis report
```

Or run analysis automatically after the benchmark:

```bash
ember run experiment.yaml --analyze
```

This produces plots, summary tables, and significance tests under:

```
results/my_first_benchmark_.../analysis/
```

See [analysis-getting-started.md](analysis-getting-started.md) for more.

---

## 12. Next steps

- **Resume interrupted runs** — `ember resume` if a benchmark is cancelled or crashes
- **Graph library** — [graph-library.md](graph-library.md) — all 36 types, ID ranges, presets, selection syntax
- **Full YAML reference** — [experiment-yaml.md](experiment-yaml.md)
- **All CLI flags** — [cli-reference.md](cli-reference.md)
- **Results database schema** — [results-schema.md](results-schema.md)
- **Custom algorithms** — [custom-algorithms.md](custom-algorithms.md)
- **Reproducibility** — [reproducibility.md](reproducibility.md)
- **Troubleshooting** — [troubleshooting.md](troubleshooting.md)
