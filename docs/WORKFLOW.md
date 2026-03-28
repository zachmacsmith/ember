# QEBench — Benchmarking Workflow

## Quick Start

```python
import networkx as nx
import dwave_networkx as dnx
from qebench import benchmark_one, EmbeddingBenchmark

chimera = dnx.chimera_graph(4, 4, 4)

# === Option 1: Single call (input → output) ===
result = benchmark_one(
    source_graph=nx.complete_graph(10),
    target_graph=chimera,
    algorithm="minorminer",
    problem_name="K10",
    topology_name="chimera_4x4x4"
)

# Result contains everything:
# result.success          → True
# result.embedding        → {0: [1, 5, 9], 1: [2, 6], ...}
# result.is_valid         → True
# result.embedding_time   → 0.005
# result.avg_chain_length → 1.9
# result.total_qubits_used → 19

# === Option 2: Batch run ===
bench = EmbeddingBenchmark(chimera, results_dir="./results")
bench.run_full_benchmark(
    graph_selection="quick",
    methods=["minorminer"],
    n_trials=3,
    warmup_trials=1,
    topology_name="chimera_4x4x4"
)
bench.generate_report()
```

---

## Project Structure

```
Quantum_Embedding_benchmark/
├── qebench/                 # Core Python package
│   ├── __init__.py          #   clean re-exports
│   ├── benchmark.py         #   benchmark_one(), EmbeddingBenchmark
│   ├── registry.py          #   @register_algorithm, validate_embedding
│   ├── graphs.py            #   graph generation, loading, presets
│   ├── results.py           #   ResultsManager (batch dirs, CSV, JSON, summary)
│   └── topologies.py        #   topology registry (Chimera, Pegasus, Zephyr)
│
├── algorithms/              # External algorithm implementations
│   ├── atom/                #   ATOM C++ source (bugs fixed — see docs/atom_changes.md)
│   ├── charme/              #   CHARME Python RL framework
│   └── oct_based/           #   OCT C++ variants
│
├── test_graphs/             # Pre-generated graph JSON files
│   ├── presets.csv          #   named graph selections
│   ├── REGISTRY.md          #   auto-generated ID catalog
│   └── <category>/          #   graph JSON files
│
├── results/                 # Benchmark output (gitignored)
├── tests/                   # Test suite
├── docs/                    # Extended documentation
├── archived/                # Superseded code
│
├── README.md
├── WORKFLOW.md              # ← this file
├── TODO.md
├── requirements.txt
└── pytest.ini
```

---

## Architecture

```
benchmark_one()              ← atomic unit, stateless, input→output
    ↑ called by
EmbeddingBenchmark           ← batch runner (graph selection, multi-trial, reporting)
    ↑ reads from
ALGORITHM_REGISTRY           ← plugin dict of all registered algorithms
    ↑ populated by
@register_algorithm("name")  ← decorator in qebench/registry.py
```

---

## `benchmark_one()` — The Atomic Unit

```python
def benchmark_one(
    source_graph,        # NetworkX graph to embed
    target_graph,        # Hardware topology (Chimera, Pegasus, etc.)
    algorithm,           # Registered name (e.g., "minorminer")
    timeout=60.0,        # Seconds per attempt
    problem_name="",     # Label (e.g., "K10")
    topology_name="",    # Label (e.g., "chimera_4x4x4")
    trial=0,             # Trial number (metadata)
    **kwargs             # Forwarded to algorithm for hyperparameter control
) -> EmbeddingResult
```

**Returns** an `EmbeddingResult` containing:
- The actual embedding chain mapping
- Quality metrics (chain lengths, qubit/coupler counts)
- Validation (coverage, disjointness, connectivity, edge preservation)
- Problem metadata (nodes, edges, density)

---

## Adding a New Algorithm

```python
from qebench import EmbeddingAlgorithm, register_algorithm

@register_algorithm("my_greedy_v2")
class MyGreedyV2(EmbeddingAlgorithm):
    def embed(self, source_graph, target_graph, timeout=60.0, **kwargs):
        embedding = {}  # {source_node: [target_qubits, ...]}
        return {'embedding': embedding, 'time': elapsed}
```

Then use it anywhere:
```python
from qebench import benchmark_one
result = benchmark_one(K10, chimera, "my_greedy_v2")
```

---

## Graph Selection

| IDs | Category |
|-----|----------|
| 1–10 | Complete |
| 11–20 | Bipartite |
| 21–30 | Grid |
| 31–40 | Cycle |
| 41–50 | Tree |
| 51–60 | Special |
| 100+ | Random |

```python
from qebench import load_test_graphs
load_test_graphs("1-10")       # complete graphs
load_test_graphs("quick")      # preset from presets.csv
load_test_graphs("diverse")    # mix from every category
load_test_graphs("*")          # everything
```

Edit `test_graphs/presets.csv` to add presets. See `test_graphs/REGISTRY.md` for full catalog.
