# EMBER

**Extensive Benchmark for Evaluation and Reproducible comparison of quantum annealing embedding algorithms.**

[![CI](https://github.com/zachmacsmith/ember/actions/workflows/ci.yml/badge.svg)](https://github.com/zachmacsmith/ember/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

EMBER is a benchmarking framework for comparing minor embedding algorithms on quantum annealing hardware topologies. It provides a standardised experiment interface, a diverse graph library spanning structured, random, and physics-motivated problem types, and reproducible execution infrastructure with seeding, checkpointing, and result collection.

---

## Installation

```bash
pip install ember-qc
```

With the companion analysis package:

```bash
pip install ember-qc[analysis]
```

Requires Python 3.10+. No quantum hardware required — all benchmarks run locally.

---

## Quick Start

**1. Create an experiment file:**

```yaml
# experiment.yaml
name: quick_comparison
algorithms:
  - minorminer
  - clique
graphs: "1-60"
topologies:
  - pegasus_16
trials: 3
timeout: 60.0
seed: 42
```

**2. Run it:**

```bash
ember run experiment.yaml
```

**3. View results:**

```bash
ember results list
ember results show <batch_id>
```

Results are saved to `./results/` in your current directory by default. To change the default output location:

```bash
ember config set output_dir /path/to/results
```

---

## Graph Library

EMBER includes a graph library covering structured, random, and application-motivated graph types:

| ID Range | Type | Description |
|---|---|---|
| 1–7 | Complete | K4 through K15 |
| 11–16 | Bipartite | K_{m,n} variants |
| 21–26 | Grid | 2D rectangular grids |
| 31–36 | Cycle | C5 through C30 |
| 41–45 | Tree | Binary and ternary trees |
| 51–53 | Special | Petersen, dodecahedral, icosahedral |
| 100–159 | Erdős–Rényi | Random graphs across node counts and densities |
| 200+ | NP problems | Graph-theoretic NP problem instances |

Graphs are selected using a range expression:

```bash
ember graphs list                     # all available graphs
ember graphs list --filter "1-60"     # preview a selection
ember graphs presets                  # all named presets
```

---

## Algorithms

| Algorithm | Availability | Notes |
|---|---|---|
| `minorminer` | ✓ included | Standard MinorMiner |
| `minorminer-fast` | ✓ included | tries=3 |
| `minorminer-aggressive` | ✓ included | tries=50 |
| `minorminer-chainlength` | ✓ included | chainlength_patience=20 |
| `clique` | ✓ included | Clique embedding via busclique |
| `pssa` | ⚠ included | Known bug: disconnected chains on all test graphs — avoid for now |
| `pssa-weighted` | ⚠ included | Same known bug |
| `pssa-fast` | ⚠ included | Same known bug |
| `pssa-thorough` | ⚠ included | Same known bug |
| `charme` | optional | `pip install ember-qc[charme]` + PyTorch |
| `atom` | optional | `ember install-binary atom` |
| `oct-triad` | optional | `ember install-binary oct` |
| `oct-fast-oct` | optional | Recommended OCT variant |

Check what is available in your environment:

```bash
ember algos list
ember algos list --available
```

---

## Custom Algorithms

Write your own algorithm in a `.py` file following the algorithm contract:

```python
# my_algorithm.py
from ember_qc.registry import EmbeddingAlgorithm, register_algorithm

@register_algorithm("my-algorithm")
class MyAlgorithm(EmbeddingAlgorithm):

    @property
    def version(self) -> str:
        return "0.1.0"

    def embed(self, source_graph, target_graph, **kwargs) -> dict:
        timeout = kwargs.get("timeout", 60.0)
        seed = kwargs.get("seed", None)

        # your implementation here

        return {"embedding": {}}    # return {} on failure
```

Get a fully documented template:

```bash
ember algos template > my_algorithm.py
```

Place the file in the user algorithms directory to have it loaded automatically:

```bash
ember algos dir    # shows the directory path
```

See `docs/EMBER_developer_guide.md` for the full algorithm contract specification.

---

## Output Layout

Each completed run produces a timestamped batch directory:

```
results/
├── batch_2026-03-28_14-30-00/
│   ├── config.json       — run parameters and environment provenance
│   ├── results.db        — SQLite: runs, embeddings, graphs, batches tables
│   ├── runs.csv          — every trial as a row (exported from SQLite)
│   ├── summary.csv       — grouped averages ± std dev per (algorithm, topology)
│   ├── README.md         — human-readable batch summary
│   └── workers/
│       ├── worker_12345.jsonl
│       └── worker_12346.jsonl
└── latest -> batch_2026-03-28_14-30-00/   (symlink to most recent)
```

Runs in progress are staged in `runs_unfinished/` (a sibling of `results/`) and moved
to `results/` only after successful compilation. Anything in `runs_unfinished/` is
incomplete and can be resumed or deleted.

---

## Reproducing Experiments

Every `ember run experiment.yaml` call writes two files alongside the results:

- `experiment.yaml` — verbatim copy of the input file
- `experiment_resolved.yaml` — fully resolved config with all flag overrides applied

To reproduce a run exactly:

```bash
ember run experiment_resolved.yaml
```

---

## Resuming Interrupted Runs

Benchmarks that are interrupted (Ctrl+C, job timeout, crash) can be resumed:

```bash
ember resume                    # shows list of incomplete runs
ember resume <batch_id>         # resume a specific run
ember resume --delete-all       # clean up all incomplete runs
```

---

## Configuration

```bash
ember config show                         # all settings and their sources
ember config set output_dir ~/results     # set default output directory
ember config set default_workers 8        # set default parallelism
ember config set default_timeout 120.0    # set default per-trial timeout
ember config get output_dir               # get a single value
ember config reset                        # restore all defaults
ember config path                         # show config file location
```

All config values can also be set via environment variables:

| Variable | Config key |
|---|---|
| `EMBER_OUTPUT_DIR` | `output_dir` |
| `EMBER_WORKERS` | `default_workers` |
| `EMBER_TIMEOUT` | `default_timeout` |
| `EMBER_TOPOLOGY` | `default_topology` |
| `EMBER_SEED` | `default_seed` |
| `EMBER_N_TRIALS` | `default_n_trials` |

Environment variables take precedence over stored config, which takes precedence over defaults. Explicit arguments to `ember run` always take highest precedence.

---

## CLI Reference

```
ember run <experiment.yaml> [flags]    Run a benchmark
ember run --analyze                    Run benchmark and generate analysis report
ember resume [batch_id]                Resume an interrupted run
ember results list                     List completed runs
ember results show <batch_id>          Show run summary
ember graphs list [--filter SPEC]      List available graphs
ember graphs presets                   List named presets
ember topologies list [--family F]     List hardware topologies
ember topologies info                  Show topology details
ember algos list [--available]         List algorithms and availability
ember algos template                   Print algorithm template
ember algos dir                        Print user algorithms directory
ember config show/set/get/reset/path   Manage configuration
ember install-binary <atom|oct>        Install compiled algorithm binaries
ember version                          Show package version
```

---

## Analysis

Install the companion analysis package:

```bash
pip install ember-qc-analysis
# or
pip install ember-qc[analysis]
```

`ember-qc-analysis` has no quantum dependencies and can be installed on any machine.
It provides tools for loading, comparing, and visualising benchmark results from EMBER
output directories.

To automatically generate an analysis report after a benchmark run:

```bash
ember run experiment.yaml --analyze
```

---

## Hardware Topologies

EMBER benchmarks embedding onto standard D-Wave hardware topologies:

| Topology | Family | Nodes | Edges |
|---|---|---|---|
| `chimera_16x16x4` | Chimera | 2,048 | 6,016 |
| `pegasus_16` | Pegasus | 5,640 | 40,484 |
| `zephyr_12` | Zephyr | 4,800 | 45,864 |

Smaller variants (`chimera_4x4x4`, `pegasus_4`, etc.) are also registered for testing.

```bash
ember topologies list
ember topologies list --family pegasus
```

---

## Requirements

- Python 3.10+
- networkx >= 2.6
- numpy >= 1.20
- pandas >= 1.3
- dwave-networkx >= 0.8
- minorminer >= 0.2

No D-Wave account or quantum hardware required.

---

## Contributing

Contributions are welcome. To add a new algorithm, see `docs/EMBER_developer_guide.md`.

Please open an issue before submitting a pull request for significant changes.

---

## License

MIT — see [LICENSE](LICENSE) for details.
