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

## 2. Check what is available

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
pssa                   ✓           known bug: disconnected chains
atom                   ✗           run: ember install-binary atom
oct-fast-oct           ✗           run: ember install-binary oct
charme                 ✗           pip install ember-qc[charme]
```

For this tutorial, `minorminer` and `clique` are sufficient.

---

## 3. List the graph library

EMBER includes 167 bundled test graphs. To see them:

```bash
ember graphs list
ember graphs list --filter "1-10"    # preview a specific range
ember graphs presets                  # named presets like "quick", "diverse"
```

---

## 4. Check hardware topologies

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
zephyr_4          zephyr       512   4,096
zephyr_12         zephyr     4,800  45,864
```

For this tutorial we use `pegasus_16` — the topology that matches D-Wave's Advantage processor.

---

## 5. Write an experiment file

Create a file called `experiment.yaml`:

```yaml
name: my_first_benchmark
algorithms:
  - minorminer
  - clique
graphs: "quick"
topologies:
  - pegasus_16
trials: 3
timeout: 60.0
seed: 42
```

What each key means:

- `name` — label for this experiment; used in the output directory name
- `algorithms` — which algorithms to compare
- `graphs` — a preset name or ID range (see [graph-library.md](graph-library.md))
- `topologies` — hardware topology to embed onto
- `trials` — how many independent trials per (algorithm, graph, topology) combination
- `timeout` — seconds allowed per trial before marking TIMEOUT
- `seed` — master seed for reproducibility; all trial seeds are derived from this

---

## 6. Run the benchmark

```bash
ember run experiment.yaml
```

You will see a progress bar. Each cell is one trial.

```
my_first_benchmark  [pegasus_16]  ████████████████████  18/18  02:14
```

When complete:

```
Results written to: /path/to/results/my_first_benchmark_2026-03-28_14-30-00
```

Two files are written alongside the results:

- `experiment.yaml` — verbatim copy of your input
- `experiment_resolved.yaml` — all parameters as actually used, including defaults that were filled in

---

## 7. View results

```bash
ember results list
```

```
Batch ID                                    Algorithms         Graphs  Trials
------------------------------------------  -----------------  ------  ------
my_first_benchmark_2026-03-28_14-30-00      minorminer, clique      6       3
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

## 8. Understand the output directory

```
results/my_first_benchmark_2026-03-28_14-30-00/
├── config.json       — all run parameters + environment provenance
├── results.db        — SQLite database with all trial data
├── runs.csv          — every trial as a CSV row (for spreadsheets/pandas)
├── summary.csv       — grouped averages per (algorithm, topology)
├── README.md         — human-readable batch summary
└── workers/
    └── worker_*.jsonl  — raw per-trial records written during the run
```

To load results into Python:

```python
import sqlite3, pandas as pd

con = sqlite3.connect("results/my_first_benchmark_.../results.db")
df = pd.read_sql("SELECT * FROM runs", con)
print(df[["algorithm", "problem_name", "success", "avg_chain_length"]].head())
```

---

## 9. Generate an analysis report (optional)

If you installed `ember-qc-analysis`:

```bash
ember-analysis stage results/my_first_benchmark_2026-03-28_14-30-00
ember-analysis report
```

Or do it in one step from the benchmark run:

```bash
ember run experiment.yaml --analyze
```

This produces plots, summary tables, and significance tests under:

```
results/my_first_benchmark_.../analysis/
```

See [analysis-getting-started.md](analysis-getting-started.md) for more.

---

## 10. Next steps

- **Larger experiments** — add more algorithms and graphs to your YAML; set `workers: 8` to parallelise
- **Resume interrupted runs** — `ember resume` if a benchmark is cancelled or crashes
- **Change the output directory** — `ember config set output_dir ~/results`
- **Full YAML reference** — [experiment-yaml.md](experiment-yaml.md)
- **All CLI flags** — [cli-reference.md](cli-reference.md)
- **Custom algorithms** — [custom-algorithms.md](custom-algorithms.md)
