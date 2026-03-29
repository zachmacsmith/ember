# EMBER

**Extensive Benchmark for Evaluation and Reproducible comparison of quantum annealing embedding algorithms.**

[![CI](https://github.com/zachmacsmith/ember/actions/workflows/ci.yml/badge.svg)](https://github.com/zachmacsmith/ember/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

EMBER is a benchmarking framework for comparing minor embedding algorithms on quantum annealing hardware topologies. Define an experiment in a YAML file, run it with a single command, and get reproducible results with plots, tables, and statistical tests.

No quantum hardware or cloud account required — all benchmarks run locally.

---

## Packages

This repository contains two packages:

| Package | PyPI | Description |
|---|---|---|
| [`ember-qc`](packages/ember-qc/) | `pip install ember-qc` | Benchmark runner: experiment execution, graph library, algorithm registry, CLI |
| [`ember-qc-analysis`](packages/ember-qc-analysis/) | `pip install ember-qc-analysis` | Analysis: plots, tables, statistical tests for completed benchmark batches |

`ember-qc-analysis` has no quantum dependencies and can be installed on any machine, including one without access to D-Wave libraries.

---

## Quick Start

**1. Install:**

```bash
pip install ember-qc[analysis]
```

**2. Create an experiment file:**

```yaml
# experiment.yaml
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

**3. Run:**

```bash
ember run experiment.yaml
```

**4. View results:**

```bash
ember results show my_first_benchmark_2026-03-28_14-30-00
```

**5. Generate analysis report:**

```bash
ember run experiment.yaml --analyze
```

Results are written to `./results/` in your current directory by default. See the [getting-started guide](docs/getting-started.md) for a full walkthrough.

---

## Repository Layout

```
ember/
├── packages/
│   ├── ember-qc/           — benchmark runner package
│   └── ember-qc-analysis/  — analysis package
├── docs/                   — documentation
├── tests/                  — shared test suite
├── scripts/                — developer tools (not installed)
└── archived/               — superseded files
```

---

## Documentation

Full documentation lives in [`docs/`](docs/).

### Getting started
- [Getting Started](docs/getting-started.md) — install, write a YAML, run, view results
- [Troubleshooting](docs/troubleshooting.md) — common problems and fixes

### Reference
- [Experiment YAML Reference](docs/experiment-yaml.md) — every key, type, default, and example
- [CLI Reference (ember)](docs/cli-reference.md) — all `ember` commands and flags
- [Results Schema](docs/results-schema.md) — `results.db` tables, `runs.csv` columns, `config.json`
- [Graph Library](docs/graph-library.md) — ID ranges, selection syntax, named presets
- [Hardware Topologies](docs/topologies.md) — Chimera, Pegasus, Zephyr specs

### Custom algorithms
- [Algorithm Contract](docs/algorithm-contract.md) — formal specification for algorithm wrappers
- [Custom Algorithms Guide](docs/custom-algorithms.md) — practical guide to writing and registering algorithms

### Advanced
- [Reproducibility](docs/reproducibility.md) — seeding, resolved YAML, checkpointing, versioning

### Analysis (ember-qc-analysis)
- [Analysis Getting Started](docs/analysis-getting-started.md) — install, stage a batch, run a report
- [Analysis CLI Reference](docs/analysis-cli-reference.md) — all `ember-analysis` commands and flags
- [Analysis Outputs](docs/analysis-outputs.md) — every plot, table, and statistics file explained

---

## License

MIT — see [LICENSE](LICENSE) for details.
