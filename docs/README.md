# EMBER Documentation

## Getting Started

| Document | Description |
|---|---|
| [getting-started.md](getting-started.md) | Guided tutorial: install, write a YAML, run a benchmark, view results. Start here. |
| [troubleshooting.md](troubleshooting.md) | Common problems and fixes: results in wrong place, all TIMEOUT, CRASH causes, reproducibility. |

## ember-qc Reference

| Document | Description |
|---|---|
| [experiment-yaml.md](experiment-yaml.md) | Complete reference for every key in an experiment YAML file, with types, defaults, and examples. |
| [cli-reference.md](cli-reference.md) | Every `ember` command and flag. One section per command group, with full flag tables. |
| [results-schema.md](results-schema.md) | `results.db` table definitions, `runs.csv` column list, `config.json` structure. |
| [graph-library.md](graph-library.md) | Graph ID ranges, types, selection syntax, and named presets. |
| [topologies.md](topologies.md) | Chimera, Pegasus, Zephyr: node counts, edge counts, structural properties, algorithm compatibility. |
| [reproducibility.md](reproducibility.md) | How EMBER ensures reproducible results: seeding, resolved YAML, checkpointing, versioning. |

## Custom Algorithms

| Document | Description |
|---|---|
| [algorithm-contract.md](algorithm-contract.md) | Formal specification for implementing an algorithm wrapper. Read before contributing a new algorithm. |
| [custom-algorithms.md](custom-algorithms.md) | Practical guide to writing, adding, and managing custom algorithms. |

## ember-qc-analysis

| Document | Description |
|---|---|
| [analysis-getting-started.md](analysis-getting-started.md) | Install, stage a batch, run a report, read the outputs. |
| [analysis-cli-reference.md](analysis-cli-reference.md) | Every `ember-analysis` command and flag. |
| [analysis-outputs.md](analysis-outputs.md) | Every plot, table, and statistics file that `generate_report()` produces, with interpretation notes. |

## Other

- [old-documentation/](old-documentation/) — archived working documents, design specs, and task notes from development.
