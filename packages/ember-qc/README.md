# EMBER

**Extensive Benchmark for Evaluation and Reproducible comparison of quantum annealing embedding algorithms.**

[![CI](https://github.com/zachmacsmith/ember/actions/workflows/ci.yml/badge.svg)](https://github.com/zachmacsmith/ember/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/ember-qc.svg)](https://pypi.org/project/ember-qc/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

EMBER is a benchmarking framework for comparing minor embedding algorithms on quantum annealing hardware topologies. It provides a standardised experiment interface, a diverse graph library of 31,083 graphs spanning structured, random, and physics-motivated problem types, and reproducible execution infrastructure with seeding, checkpointing, and result collection.

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
graphs: installed
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

EMBER ships with 37 graphs bundled for offline use and provides on-demand access to a library of **31,083 graphs** across 36 types hosted on HuggingFace. Graphs not bundled are downloaded automatically and cached locally on first use.

### Graph types

| Family | Types | Count | n range |
|---|---|---|---|
| Structured | complete, bipartite, grid, cycle, path, star, wheel, turan | 1,148 | 2–5,640 |
| Algebraic | circulant, generalized_petersen, hypercube, johnson, kneser | 1,259 | 4–5,640 |
| Trees | binary_tree, tree | 38 | 3–5,461 |
| Random | random_er, barabasi_albert, regular, watts_strogatz, sbm, lfr_benchmark, random_planar | 23,969 | 3–5,640 |
| Physics lattice | triangular_lattice, kagome, honeycomb, king_graph, frustrated_square, shastry_sutherland, cubic_lattice, bcc_lattice | 820 | 4–6,119 |
| Physics models | spin_glass, weak_strong_cluster, planted_solution | 3,670 | 10–5,640 |
| Hardware | hardware_native | 42 | 8–4,928 |
| Special | named_special, sudoku | 14 | 5–65,536 |

### Browsing and installing graphs

```bash
ember graphs list                        # overview: all types with ID ranges and counts
ember graphs list complete               # all complete graphs with node/edge counts
ember graphs list -a                     # installed types only
ember graphs info 1004                   # full metadata for graph ID 1004
ember graphs search --type random_er --max-nodes 20
ember graphs presets                     # all named presets with graph counts
```

### Installing graphs

```bash
ember graphs install benchmark           # install the benchmark preset (~82 graphs)
ember graphs install 1000-1055           # install all complete graphs
ember graphs install "5550-5600, !5575"  # install a range with exclusions
ember graphs install --dry-run default   # preview without downloading
```

### Presets

| Preset | Count | Description |
|---|---|---|
| `installed` | 37 | Bundled with the package — always available offline |
| `quick` | 12 | One smallest graph per main type |
| `default` | 36 | One small representative per type |
| `diverse` | 31 | Hand-picked across all types, varied n |
| `benchmark` | 82 | Curated for algorithm benchmarking, n=3–100 |
| `structured` | 2,568 | All deterministic/algebraic types |
| `lattice` | 820 | All physics lattice types |
| `physics` | 4,490 | Lattices + spin_glass + weak_strong_cluster + planted_solution |
| `hardware_native` | 42 | Hardware topology graphs |
| `named_special` | 12 | Petersen, Tutte, Chvátal, etc. |
| `small` | 617 | All graphs with n ≤ 10 |
| `all` | 31,083 | Everything |

### Cache management

```bash
ember graphs cache                       # disk usage summary by type
ember graphs cache delete benchmark      # remove specific graphs
ember graphs cache delete --all          # wipe entire cache
ember graphs verify                      # SHA-256 integrity check on all cached graphs
ember graphs verify --fix                # re-download any corrupt files
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
| `pssa` | ✓ included | Path-annealing SA; auto topology detection |
| `pssa-weighted` | ✓ included | Degree-weighted shifts — best for regular graphs |
| `pssa-fast` | ✓ included | tmax=50,000 — good for large sweeps |
| `pssa-thorough` | ✓ included | tmax=2,000,000 — highest quality, slow |
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

See the [algorithm contract](https://github.com/zachmacsmith/ember/blob/main/docs/algorithm-contract.md) and [custom algorithms guide](https://github.com/zachmacsmith/ember/blob/main/docs/custom-algorithms.md) for the full specification.

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
ember run <experiment.yaml> [flags]       Run a benchmark
ember run --analyze                       Run benchmark and generate analysis report
ember resume [batch_id]                   Resume an interrupted run

ember graphs list [TYPE] [-a]             List graph types or graphs of a type
ember graphs info <id>                    Show full metadata for a graph
ember graphs install <spec>               Download graphs to local cache
ember graphs presets                      List named presets with graph counts
ember graphs search [--type T] [filters]  Search manifest by property
ember graphs cache                        Show cache disk usage
ember graphs cache delete <spec|--all>    Remove graphs from cache
ember graphs verify [--fix]               Verify and repair cached graphs

ember results list                        List completed runs
ember results show <batch_id>             Show run summary
ember topologies list [--family F]        List hardware topologies
ember topologies info                     Show topology details
ember algos list [--available]            List algorithms and availability
ember algos template                      Print algorithm template
ember algos dir                           Print user algorithms directory
ember config show/set/get/reset/path      Manage configuration
ember install-binary <atom|oct>           Install compiled algorithm binaries
ember version                             Show package version
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

## Documentation

Full documentation: [github.com/zachmacsmith/ember/tree/main/docs](https://github.com/zachmacsmith/ember/tree/main/docs)

| Document | Description |
|---|---|
| [Getting Started](https://github.com/zachmacsmith/ember/blob/main/docs/getting-started.md) | Full tutorial with examples |
| [Experiment YAML Reference](https://github.com/zachmacsmith/ember/blob/main/docs/experiment-yaml.md) | All YAML keys and defaults |
| [CLI Reference](https://github.com/zachmacsmith/ember/blob/main/docs/cli-reference.md) | All `ember` commands and flags |
| [Results Schema](https://github.com/zachmacsmith/ember/blob/main/docs/results-schema.md) | Database tables and column definitions |
| [Custom Algorithms](https://github.com/zachmacsmith/ember/blob/main/docs/custom-algorithms.md) | Writing and registering custom algorithms |
| [Reproducibility](https://github.com/zachmacsmith/ember/blob/main/docs/reproducibility.md) | Seeding, resolved YAML, checkpointing |
| [Troubleshooting](https://github.com/zachmacsmith/ember/blob/main/docs/troubleshooting.md) | Common problems and fixes |

---

## Contributing

Contributions are welcome. Please open an issue before submitting a pull request for significant changes.

---

## License

MIT — see [LICENSE](LICENSE) for details.
