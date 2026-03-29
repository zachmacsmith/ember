# Graph Library

EMBER ships with 167 bundled test graphs covering structured, random, and application-motivated types. This document describes the ID ranges, graph types, selection syntax, and named presets.

---

## ID ranges

| ID Range | Type | Description |
|---|---|---|
| 1–7 | Complete | K4 through K15 — dense, clique structure |
| 11–16 | Bipartite | Complete bipartite K_{m,n} variants |
| 21–26 | Grid | 2D rectangular grids |
| 31–36 | Cycle | C5 through C30 |
| 41–45 | Tree | Binary and ternary trees |
| 51–53 | Special | Petersen, dodecahedral, icosahedral |
| 100–159 | Erdős–Rényi | Random graphs across node counts and densities |
| 200+ | NP problems | Graph-theoretic NP problem instances |

---

## Graph types

### Complete (1–7)
Complete graphs K_n where every pair of vertices is connected. Hard for embedding because of high edge density. The clique embedding algorithm (`clique`) is specifically designed for these.

### Bipartite (11–16)
Complete bipartite graphs K_{m,n}. Two disjoint sets with all cross edges. Relevant for QUBO problem structures.

### Grid (21–26)
2D rectangular grid graphs. Regular structure with predictable degree sequence. Representative of lattice-structured problems.

### Cycle (31–36)
Simple cycle graphs C_n. Sparse (degree 2 everywhere). Used to test chain routing in linear structures.

### Tree (41–45)
Binary and ternary trees. Low connectivity, no cycles. Typically easy to embed but useful for baseline comparisons.

### Special (51–53)
- **51** — Petersen graph (10 nodes, 15 edges; vertex-transitive)
- **52** — Dodecahedral graph (20 nodes, 30 edges)
- **53** — Icosahedral graph (12 nodes, 30 edges; maximum planar)

### Erdős–Rényi random (100–159)
Random graphs generated with the G(n, p) model. Span a range of node counts (typically 10–100) and densities (0.1–0.8). The most algorithmically diverse category — hardness varies significantly within the range.

### NP problems (200+)
Graphs derived from NP-hard problem instances: maximum cut, graph colouring, graph partitioning. Represent practically-motivated embedding targets.

---

## Selection syntax

Graphs are selected using a string expression. All selection strings work in the YAML `graphs` field, in `ember graphs list --filter`, and in `load_test_graphs()`.

| Expression | Result |
|---|---|
| `"1-60"` | IDs 1 through 60 inclusive |
| `"1-10, 30-50"` | IDs 1–10 and 30–50 |
| `"51, 52, 53"` | Just those three IDs |
| `"1-100, !50"` | IDs 1–100 excluding 50 |
| `"1-100 & !41-50"` | IDs 1–100 excluding the 41–50 range |
| `"*"` | All 167 bundled graphs |
| `"quick"` | Named preset (see below) |

Multiple ranges are combined with commas (union). `!` negates. `&` applies intersection. Negation and intersection have lower precedence than comma.

---

## Named presets

Presets are defined in `packages/ember-qc/src/ember_qc/graphs/presets.csv`.

| Preset | Selection | Description |
|---|---|---|
| `default` | `1-60` | All structured graphs |
| `all` | `*` | All 167 graphs |
| `quick` | `1-3, 31-32, 51` | 5 graphs for fast testing |
| `complete` | `1-10` | Complete graphs only |
| `bipartite` | `11-20` | Bipartite graphs only |
| `grid` | `21-30` | Grid graphs only |
| `cycle` | `31-40` | Cycle graphs only |
| `tree` | `41-50` | Tree graphs only |
| `special` | `51-60` | Special graphs only |
| `random` | `100-199` | All random (ER) graphs |
| `structured` | `1-60` | All structured types |
| `diverse` | `1, 3, 5, 12, 14, 22, 24, 32, 34, 41, 44, 51, 52, 53` | One representative per type |
| `small` | `1-3, 11-12, 21-22, 31-32, 41, 200-207` | Small graphs only |
| `np_problems` | `200-251` | NP problem instances |

List all presets:

```bash
ember graphs presets
```

---

## Filtering by size

In Python, you can filter by node count:

```python
from ember_qc import load_test_graphs

graphs = load_test_graphs("1-60", max_nodes=20)
graphs = load_test_graphs("random", min_nodes=30, max_nodes=60)
```

There is no CLI flag for size filtering — use a preset or selection string that covers the range you want, then filter programmatically if needed.

---

## Graph JSON format

Each graph is stored as a JSON file under `packages/ember-qc/src/ember_qc/graphs/library/<category>/`. The structure is:

```json
{
  "metadata": {
    "type": "complete",
    "n": 6
  },
  "num_nodes": 6,
  "num_edges": 15,
  "nodes": [0, 1, 2, 3, 4, 5],
  "edges": [[0,1],[0,2],[0,3],[0,4],[0,5],[1,2],...]
}
```

The `manifest.json` in the same directory contains SHA-256 hashes of every graph file and is checked at load time to detect corruption.

---

## Loading graphs in Python

```python
from ember_qc import load_graph, load_test_graphs, list_test_graphs

# Single graph by ID
G = load_graph(51)   # Petersen graph

# Multiple graphs by selection
graphs = load_test_graphs("1-10")   # list of (name, nx.Graph)

# Catalog
catalog = list_test_graphs()
for entry in catalog[:5]:
    print(entry["id"], entry["name"], entry["nodes"], entry["edges"])
```

---

## Regenerating the manifest

If you add or modify graph files, regenerate the manifest:

```bash
python scripts/generate_manifest.py
```

Then commit the updated `manifest.json`.
