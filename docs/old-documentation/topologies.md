# Topology Registry

QEBench provides a registry of hardware topologies representing real D-Wave quantum annealing architectures. Topologies are generated on first use and cached in memory.

## Built-In Topologies

### Chimera

The Chimera topology was used in D-Wave's earlier machines (D-Wave 2000Q and prior). It consists of a grid of K₄,₄ unit cells with inter-cell couplers.

| Name | Params | Qubits | Edges | Notes |
|------|--------|--------|-------|-------|
| `chimera_4x4x4` | m=4, n=4, t=4 | 128 | 352 | Small test size |
| `chimera_8x8x4` | m=8, n=8, t=4 | 512 | 1,472 | Medium |
| `chimera_12x12x4` | m=12, n=12, t=4 | 1,152 | 3,360 | Large |
| `chimera_16x16x4` | m=16, n=16, t=4 | 2,048 | 6,016 | D-Wave 2000Q |

**Generator:** `dwave_networkx.chimera_graph(m, n, t)`

---

### Pegasus

The Pegasus topology is used in D-Wave Advantage systems. It has significantly higher connectivity than Chimera (degree 15 vs. degree 6), enabling more efficient embeddings.

| Name | Params | Qubits | Edges | Notes |
|------|--------|--------|-------|-------|
| `pegasus_4` | m=4 | 264 | 1,604 | Small test size |
| `pegasus_6` | m=6 | 680 | 4,484 | Medium |
| `pegasus_8` | m=8 | 1,288 | 8,804 | Large |
| `pegasus_16` | m=16 | 5,640 | 40,484 | D-Wave Advantage |

**Generator:** `dwave_networkx.pegasus_graph(m)`

---

### Zephyr

The Zephyr topology is used in D-Wave Advantage2 systems. It has even higher connectivity than Pegasus (degree 20), representing the latest quantum annealing hardware.

| Name | Params | Qubits | Edges | Notes |
|------|--------|--------|-------|-------|
| `zephyr_2` | m=2 | 160 | 1,224 | Small test size |
| `zephyr_4` | m=4 | 576 | 5,032 | Medium |
| `zephyr_6` | m=6 | 1,248 | 11,400 | Large |
| `zephyr_8` | m=8 | 2,176 | 20,328 | Advantage2 prototype |

**Generator:** `dwave_networkx.zephyr_graph(m)`

---

## Usage

### Single Topology

```python
from qebench import get_topology, EmbeddingBenchmark

chimera = get_topology("chimera_4x4x4")
bench = EmbeddingBenchmark(target_graph=chimera)
bench.run_full_benchmark(graph_selection="quick", methods=["minorminer"])
```

### Multi-Topology Comparison

```python
bench = EmbeddingBenchmark()
bench.run_full_benchmark(
    graph_selection="quick",
    methods=["minorminer", "clique"],
    topologies=["chimera_4x4x4", "pegasus_4", "zephyr_2"],
    n_trials=5,
    batch_note="Cross-topology comparison"
)
```

### Listing Topologies

```python
from qebench import list_topologies, list_topology_families, topology_info

# All topology names
print(list_topologies())

# Filter by family
print(list_topologies(family="pegasus"))
# ['pegasus_4', 'pegasus_6', 'pegasus_8', 'pegasus_16']

# All families
print(list_topology_families())
# ['chimera', 'pegasus', 'zephyr']

# Formatted table
print(topology_info())
```

### Topology Details

```python
from qebench import get_topology_config

config = get_topology_config("pegasus_16")
print(config.name)         # 'pegasus_16'
print(config.family)       # 'pegasus'
print(config.params)       # {'m': 16}
print(config.description)  # 'Pegasus P16 (D-Wave Advantage)'
```

---

## Registering Custom Topologies

```python
import networkx as nx
from qebench import register_topology

# Hypothetical topology
register_topology(
    name="hex_lattice_10x10",
    family="custom",
    generator=lambda: nx.hexagonal_lattice_graph(10, 10),
    params={"rows": 10, "cols": 10},
    description="10×10 hexagonal lattice"
)

# Broken hardware (simulate dead qubits)
import dwave_networkx as dnx
import random

def make_broken_pegasus():
    g = dnx.pegasus_graph(16)
    dead = random.sample(list(g.nodes()), k=int(0.05 * g.number_of_nodes()))
    g.remove_nodes_from(dead)
    return g

register_topology(
    name="pegasus_16_broken_5pct",
    family="pegasus_broken",
    generator=make_broken_pegasus,
    params={"m": 16, "dead_pct": 0.05},
    description="Pegasus P16 with 5% dead qubits"
)
```

---

## Algorithm Compatibility

| Algorithm | Chimera | Pegasus | Zephyr | Custom |
|-----------|---------|---------|--------|--------|
| `minorminer` | ✅ | ✅ | ✅ | ✅ |
| `clique` | ✅ | ✅ | ✅ | ⚠️ |
| `oct-triad` | ✅ | ❌ | ❌ | ❌ |
| `oct-fast-oct` | ✅ | ❌ | ❌ | ❌ |
| `atom` | ✅ | ❌ | ❌ | ❌ |

> **Note:** OCT-suite algorithms use Chimera's bipartite structure internally and only work with Chimera topologies. MinorMiner and clique embedding work on any topology.
