# QEBench — Quantum Embedding Benchmark

A standardized, extensible benchmarking framework for comparing minor embedding algorithms on D-Wave quantum hardware topologies.

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

## Overview

QEBench provides a clean, reproducible pipeline for benchmarking minor embedding algorithms across:

- **Algorithms:** minorminer variants, ATOM, OCT (fast-oct-reduce recommended), PSSA, CHARME (RL) — all registered via a plugin system
- **Topologies:** 12 built-in D-Wave topologies (Chimera, Pegasus, Zephyr)
- **Test graphs:** Pre-generated library of 100+ graphs across 7 categories
- **Metrics:** embedding time, success rate, chain length, qubit/coupler usage, embedding validity

---

## Project Structure

```
qebench/                    # Benchmark runner package
├── benchmark.py            #   benchmark_one(), EmbeddingBenchmark
├── registry.py             #   @register_algorithm, ALGORITHM_REGISTRY
├── graphs.py               #   load_test_graphs(), graph presets
├── results.py              #   ResultsManager (batch dirs, CSV, JSON)
└── topologies.py           #   topology registry (Chimera, Pegasus, Zephyr)

qeanalysis/                 # Post-benchmark analysis package (separate from qebench)
├── loader.py               #   Load batch dir, derive computed columns
├── summary.py              #   Aggregate tables (overall, by-category, rank)
├── plots.py                #   All visualizations (scaling, Pareto, heatmaps, ...)
├── statistics.py           #   Wilcoxon, Friedman, correlation, significance tests
└── export.py               #   LaTeX table + PDF plot export

algorithms/                 # External algorithm implementations
├── atom/                   #   ATOM C++ source (fixed — see docs/atom_changes.md)
├── charme/                 #   CHARME RL Python framework (stub — needs trained model)
├── charme-rl/              #   CHARME RL alternative source
├── oct_based/              #   OCT C++ variants
└── pssa_dwave/             #   PSSA Python package (editable install)

test_graphs/                # Pre-generated graph JSON library
├── complete/               #   K4, K5, K6, K8, K10, K12, K15
├── bipartite/              #   K_{2,3} through K_{5,5}
├── grid/                   #   2×2 through 5×5
├── cycle/                  #   5- to 30-node cycles
├── tree/                   #   balanced trees (r=2/3, d=3–5)
├── special/                #   Petersen, Dodecahedral, Icosahedral
├── random/                 #   n∈{6,8,10,15,20} × d∈{0.2,0.3,0.5,0.7} × 3 instances
├── presets.csv             #   named selections (quick, diverse, ...)
└── REGISTRY.md             #   full graph catalog

results/                    # Benchmark output (gitignored)
└── batch_YYYY-MM-DD_.../   #   timestamped batch from each run

analysis/                   # Analysis output (gitignored)
└── batch_YYYY-MM-DD_.../   #   matches results batch name; contains figures/ + tables/

tests/                      # Pytest suite (84 tests)
docs/                       # Extended documentation
archived/                   # Superseded scripts
```

---

## Installation

### One-command setup (recommended)

```bash
bash setup.sh
```

This single script does everything:
1. Installs all Python dependencies (`requirements.txt`)
2. Compiles the ATOM C++ binary (`algorithms/atom/main`)
3. Compiles the OCT-Based C++ binary (`algorithms/oct_based/embedding/driver`)
4. Prints a summary of which algorithms are ready to use

**Requirements:** Python 3.8+, `g++` for C++ algorithms (macOS: `xcode-select --install` | Linux: `sudo apt install g++`). If `g++` is not found, the script skips compilation and the Python-only algorithms (minorminer, clique) still work.

### Manual setup

```bash
pip install -r requirements.txt                      # Python deps (minorminer + clique work immediately)
pip install -e algorithms/pssa_dwave/                # PSSA (pure Python, no compilation)
cd algorithms/atom     && make                       # compile ATOM
cd algorithms/oct_based && make build               # compile OCT variants
```

---

## Quick Start

### 1. Single Embedding (one call)

```python
import networkx as nx
import dwave_networkx as dnx
from qebench import benchmark_one

chimera = dnx.chimera_graph(4, 4, 4)
result = benchmark_one(
    source_graph=nx.complete_graph(10),
    target_graph=chimera,
    algorithm="minorminer",
    problem_name="K10",
    topology_name="chimera_4x4x4"
)

print(result.success)           # True
print(result.avg_chain_length)  # e.g. 2.1
print(result.embedding_time)    # e.g. 0.012
print(result.is_valid)          # True
```

### 2. Batch Benchmark

```python
from qebench import EmbeddingBenchmark
import dwave_networkx as dnx

chimera = dnx.chimera_graph(4, 4, 4)
bench = EmbeddingBenchmark(chimera, results_dir="./results")
bench.run_full_benchmark(
    graph_selection="quick",          # preset from test_graphs/presets.csv
    methods=["minorminer", "oct-triad"],
    n_trials=5,
    warmup_trials=1,
    topology_name="chimera_4x4x4",
    batch_note="initial_run"
)
bench.generate_report()
```

Results are saved to a timestamped batch directory:
```
results/
└── batch_2026-02-24_14-30-00/
    ├── runs.csv        # every trial as a row
    ├── runs.json       # full archive with embeddings
    ├── summary.csv     # averages ± std dev per (algo, graph, topology)
    ├── config.json     # run settings
    └── README.md       # human-readable summary
```

### 3. Post-Benchmark Analysis

Once a benchmark batch has run, pass its directory to `BenchmarkAnalysis` to generate all plots and tables automatically. `run_full_benchmark()` returns the batch directory path, so you can chain them directly:

```python
from qebench import EmbeddingBenchmark
from qeanalysis import BenchmarkAnalysis

bench = EmbeddingBenchmark(target_graph=None)
batch_dir = bench.run_full_benchmark(
    graph_selection="quick",
    topologies=["chimera_4x4x4"],
    methods=["minorminer", "oct-triad"],
    n_trials=5,
)

BenchmarkAnalysis(batch_dir).generate_report()
# → writes to analysis/<batch-name>/
```

`generate_report()` produces:

```
analysis/batch_2026-02-25_09-25-10/
├── figures/          # 10 plot types + per-pair head-to-head + per-problem deep dives
│   ├── heatmap_avg_chain_length.png
│   ├── pareto_embedding_time_vs_avg_chain_length.png
│   ├── scaling_embedding_time_vs_problem_nodes.png
│   ├── head_to_head_minorminer_vs_oct-triad.png
│   └── ...
├── tables/           # 7 tables as both .csv and .tex (booktabs)
│   ├── overall_summary.csv / .tex
│   ├── win_rate_chain.csv / .tex
│   ├── significance_chain.csv / .tex
│   └── ...
└── README.md         # index of all generated files
```

You can also call individual analyses directly:

```python
an.overall_summary()            # aggregate stats per algorithm
an.win_rate_matrix()            # N×N pairwise win rate table
an.significance_tests()         # Wilcoxon + Holm-Bonferroni p-values
an.friedman_test()              # non-parametric multi-algo ANOVA
an.correlation_matrix()         # Spearman: graph properties vs. embedding metrics
fig = an.plot_pareto(save=False)  # returns matplotlib Figure
```

See [`docs/analysis.md`](docs/analysis.md) for a detailed description of every analysis method, the statistics used, and how to add new analyses.

---

### 4. Load Test Graphs

```python
from qebench import load_test_graphs

problems = load_test_graphs("1-10")     # complete graphs
problems = load_test_graphs("quick")    # preset selection
problems = load_test_graphs("diverse")  # one from each category
problems = load_test_graphs("*")        # all graphs
```

Graph IDs map to categories (see `test_graphs/REGISTRY.md`):

| IDs | Category |
|-----|----------|
| 1–10 | Complete |
| 11–20 | Bipartite |
| 21–30 | Grid |
| 31–40 | Cycle |
| 41–50 | Tree |
| 51–60 | Special |
| 100+ | Random |

---

## Algorithm Status

### minorminer variants (pure Python, no compilation)

| Algorithm | Status | Notes |
|-----------|--------|-------|
| `minorminer` | ✅ Working | Default heuristic — good balance of speed and quality |
| `minorminer-aggressive` | ✅ Working | More restarts (`tries=50`) — higher quality, slower |
| `minorminer-fast` | ✅ Working | Fewer restarts (`tries=3`) — fastest, lower quality |
| `minorminer-chainlength` | ✅ Working | Optimised for short chains (`chainlength_patience=20`) |
| `clique` | ✅ Working | Deterministic topology-aware baseline (`busclique`) |

### OCT-Based (requires compiled binary)

The OCT suite has six variants. **`oct-fast-oct-reduce` is the recommended OCT algorithm** — it consistently outperforms the others in both chain length and validity across all graph types. The others are registered but not recommended for primary benchmarking.

| Algorithm | Status | Notes |
|-----------|--------|-------|
| `oct-fast-oct-reduce` | ✅ Working ⭐ | **Recommended** — best chain length, valid on general graphs |
| `oct-fast-oct` | ✅ Working | Fast-OCT without chain reduction — superseded by reduce variant |
| `oct-triad` | ✅ Working | Deterministic, 2 qubits/node — reliable but longer chains |
| `oct-triad-reduce` | ⚠️ Often invalid | Chain reduction produces invalid embeddings on non-bipartite graphs |
| `oct-hybrid-oct` | ⚠️ Often invalid | Valid only on bipartite graphs |
| `oct-hybrid-oct-reduce` | ⚠️ Often invalid | Same limitation as hybrid-oct |

### Other algorithms

| Algorithm | Status | Notes |
|-----------|--------|-------|
| `atom` | ✅ Working | C++ binary; bugs fixed — see `docs/atom_changes.md` |
| `pssa` | ✅ Working | Path-annealing SA; auto topology detection, auto tmax |
| `pssa-weighted` | ✅ Working | Degree-weighted shifts — best for cubic/regular graphs |
| `pssa-fast` | ✅ Working | `tmax=50,000` — good for large sweeps |
| `pssa-thorough` | ✅ Working | `tmax=2,000,000` — best quality, slow |
| `charme` | ❌ Stub | RL framework — requires pre-trained model + PyTorch |

---

## Compiling C++ Algorithms

### ATOM

```bash
cd algorithms/atom
make
# produces: algorithms/atom/main
```

See [`docs/atom_changes.md`](docs/atom_changes.md) for a record of the bug fixes applied to the original source (buffer underflow, threading, output parsing).

### OCT-Based

```bash
cd algorithms/oct_based
make
# produces: algorithms/oct_based/embedding/driver
```

---

## Hardware Topologies

12 built-in D-Wave topologies are registered at import time:

| Family | Available Sizes |
|--------|----------------|
| Chimera | `chimera_4x4x4`, `chimera_8x8x4`, `chimera_12x12x4`, `chimera_16x16x4` |
| Pegasus | `pegasus_4`, `pegasus_6`, `pegasus_8`, `pegasus_16` |
| Zephyr | `zephyr_2`, `zephyr_4`, `zephyr_6`, `zephyr_8` |

```python
from qebench import list_topologies, get_topology
print(list_topologies())
graph = get_topology("pegasus_16")
```

Multi-topology benchmark:
```python
bench.run_full_benchmark(
    graph_selection="diverse",
    methods=["minorminer"],
    topologies=["chimera_4x4x4", "pegasus_4", "zephyr_4"]
)
```

---

## Adding a New Algorithm

```python
from qebench import EmbeddingAlgorithm, register_algorithm
import time

@register_algorithm("my_greedy_v2")
class MyGreedyV2(EmbeddingAlgorithm):
    def embed(self, source_graph, target_graph, timeout=60.0, **kwargs):
        start = time.time()
        embedding = {}  # {source_node: [target_qubits]}
        # ... your logic here ...
        return {'embedding': embedding, 'time': time.time() - start}
```

Then use it immediately:
```python
result = benchmark_one(source, target, "my_greedy_v2")
```

---

## Running Tests

```bash
pytest tests/ -v
```

163 tests covering: `qebench` (imports, `benchmark_one`, `EmbeddingResult`, metrics, registry, graph selection, presets, graph loading, batch runner, results storage, topology registry) and `qeanalysis` (loader, summary tables, win rate, significance tests, plots, export, full integration).

---

## Metrics

| Metric | Description | Better |
|--------|-------------|--------|
| `success` | Embedding found within timeout | True |
| `is_valid` | Passes all validity checks | True |
| `embedding_time` | Seconds to find embedding | Lower |
| `avg_chain_length` | Mean physical qubits per logical qubit | Lower |
| `max_chain_length` | Longest single chain | Lower |
| `total_qubits_used` | Physical qubits in embedding | Lower |
| `total_couplers_used` | Physical couplers in embedding | Lower |

Validity checks: node coverage, chain disjointness, chain connectivity, edge preservation.

---

## Roadmap

See [`TODO.md`](TODO.md) for the full task tracker. Key upcoming work:

- **QUBO problem generators** — Max-Cut, TSP, Job Shop, Graph Coloring (Paper 1)
- **Graph characterization module** — treewidth, clustering, community structure (Paper 2)
- **CHARME RL integration** — requires pre-trained model and PyTorch; not yet runnable
- **Broken topology benchmarks** — simulate dead qubits
- **Novel algorithm** — pathfinder-inspired embedding (Paper 3)

---

## Documentation

| File | Contents |
|------|----------|
| [`WORKFLOW.md`](WORKFLOW.md) | Full API reference and architecture |
| [`TODO.md`](TODO.md) | Task tracker and paper timeline |
| [`docs/analysis.md`](docs/analysis.md) | qeanalysis methods: statistics, plots, export |
| [`docs/adding_algorithms.md`](docs/adding_algorithms.md) | How to add new embedding algorithms |
| [`docs/adding_test_graphs.md`](docs/adding_test_graphs.md) | How to add graphs to the test library |
| [`docs/atom_changes.md`](docs/atom_changes.md) | ATOM C++ bug fixes |
| [`docs/algorithms.md`](docs/algorithms.md) | Algorithm integration details |
| [`docs/topologies.md`](docs/topologies.md) | Topology registry reference |
| [`docs/troubleshooting.md`](docs/troubleshooting.md) | Common issues and fixes |

---

## Citation

```bibtex
@software{qebench_2026,
  author  = {Macaskill-Smith, Zach and Sharma, Unmol},
  title   = {QEBench: Quantum Embedding Benchmark},
  year    = {2026},
  url     = {https://github.com/Unmolsharma/Quantum_Embedding_benchmark}
}
```

---

## License

MIT License

---

## Acknowledgments

- D-Wave Systems for `minorminer` and `dwave-networkx`
- Authors of ATOM, OCT-Based, and CHARME
