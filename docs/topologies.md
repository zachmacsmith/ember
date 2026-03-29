# Hardware Topologies

EMBER benchmarks minor embedding onto D-Wave quantum annealing hardware topologies. Three topology families are registered: Chimera, Pegasus, and Zephyr.

---

## Chimera

Chimera is the topology used in D-Wave 2000Q and earlier processors. It is a bipartite grid of unit cells, each a complete bipartite graph K_{4,4}.

**Structure:** An `m×n×t` Chimera graph has `2·m·n·t` nodes arranged in a grid of `m×n` unit cells, each containing `2t` qubits. Standard processors use `t=4`.

**Properties:**
- Degree: most nodes have degree `t + t` = `2t` (connections within the cell plus to adjacent cells); boundary nodes have lower degree
- Bipartite within each unit cell
- Regular structure makes embedding patterns predictable

| Name | Nodes | Edges | Description |
|---|---|---|---|
| `chimera_4x4x4` | 128 | 352 | Small test topology |
| `chimera_8x8x4` | 512 | 1,472 | Medium |
| `chimera_12x12x4` | 1,152 | 3,360 | Large |
| `chimera_16x16x4` | 2,048 | 6,016 | Full D-Wave 2000Q |

**When to use:** Chimera is the best-studied topology with the most published embedding results. Use it for comparisons with prior work or when running the ATOM algorithm (Chimera-only).

---

## Pegasus

Pegasus is the topology used in D-Wave Advantage processors. It improves on Chimera by adding internal couplers within each unit cell and additional long-range connections.

**Structure:** Pegasus graphs have a complex irregular structure. A Pegasus(m) graph has `24(m-1)² + 3(m-1)` nodes. The standard D-Wave Advantage uses `m=16`.

**Properties:**
- Average degree: approximately 15 (versus ~6 in Chimera)
- Much higher connectivity makes embedding generally easier
- Non-bipartite structure — more algorithm-friendly than Chimera

| Name | Nodes | Edges | Description |
|---|---|---|---|
| `pegasus_4` | 594 | 2,816 | Small test topology |
| `pegasus_6` | 1,394 | 7,286 | Medium |
| `pegasus_8` | 2,574 | 14,056 | Large |
| `pegasus_16` | 5,640 | 40,484 | Full D-Wave Advantage |

**When to use:** Pegasus is the current D-Wave standard. Use `pegasus_16` for results directly applicable to the D-Wave Advantage processor.

---

## Zephyr

Zephyr is the topology introduced in D-Wave Advantage2. It further increases connectivity over Pegasus.

**Structure:** A Zephyr(m) graph has `4m(2m+1)` nodes. The planned full processor uses `m=12`.

**Properties:**
- Average degree: approximately 20
- Highest connectivity of the three families
- Relatively few published embedding results — a good target for new research

| Name | Nodes | Edges | Description |
|---|---|---|---|
| `zephyr_2` | 56 | 336 | Minimal test topology |
| `zephyr_4` | 272 | 2,016 | Small |
| `zephyr_6` | 600 | 5,040 | Medium |
| `zephyr_8` | 1,040 | 9,360 | Large |
| `zephyr_12` | 4,800 | 45,864 | Projected full processor |

**When to use:** Zephyr results are most relevant for forward-looking comparisons and hardware planning for the Advantage2 generation.

---

## Listing topologies

```bash
ember topologies list
ember topologies list --family pegasus
ember topologies info
```

---

## Using topologies in experiments

```yaml
topologies:
  - pegasus_16
  - chimera_16x16x4
```

When multiple topologies are listed, EMBER benchmarks every (algorithm, graph, topology) triple. Results are grouped by topology in the output.

---

## Registering custom topologies

You can register additional topology variants in Python:

```python
from ember_qc.topologies import register_topology
import dwave_networkx as dnx

register_topology(
    name="my_pegasus",
    family="pegasus",
    generator=lambda: dnx.pegasus_graph(12),
    params={"m": 12},
    description="Custom Pegasus-12 topology",
)
```

After registration, `"my_pegasus"` is available as a topology name in YAML and CLI.

---

## Algorithm compatibility

Some algorithms are restricted to specific topology families:

| Algorithm | Supported topologies |
|---|---|
| `minorminer` | all |
| `clique` | all |
| `pssa` | chimera, pegasus, zephyr |
| `atom` | chimera only |
| `oct-*` | chimera only |
| `charme` | all (when available) |

Incompatible (algorithm, topology) pairs are silently skipped before the run starts. EMBER logs a `TOPOLOGY_INCOMPATIBLE` warning for each skipped pair.
