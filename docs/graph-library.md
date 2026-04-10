# Graph Library

EMBER provides access to **31,083 graphs** across 36 types, hosted on HuggingFace (`zachmacsmith/ember-graphs`). 37 graphs are bundled with the package for offline use; all others are downloaded on demand and cached locally.

---

## Graph types and ID ranges

| Family | Type | ID Range | Count | n range |
|---|---|---|---|---|
| Structured | complete | 1000–1055 | 56 | 2–287 |
| Structured | bipartite | 1200–1407 | 208 | 4–492 |
| Structured | grid | 1550–1697 | 146 | 4–5,625 |
| Structured | cycle | 1800–1863 | 64 | 3–5,640 |
| Structured | path | 2000–2063 | 64 | 3–5,640 |
| Structured | star | 2200–2262 | 63 | 4–5,316 |
| Structured | wheel | 2400–2462 | 63 | 4–5,316 |
| Structured | turan | 2600–3235 | 607 | 3–428 |
| Algebraic | circulant | 3350–3700 | 351 | 5–5,640 |
| Algebraic | generalized_petersen | 3800–4644 | 782 | 8–5,640 |
| Algebraic | hypercube | 4750–4760 | 11 | 4–4,096 |
| Algebraic | binary_tree | 4900–4910 | 11 | 3–4,095 |
| Algebraic | tree | 5050–5077 | 27 | 7–5,461 |
| Algebraic | johnson | 5200–5273 | 74 | 10–2,002 |
| Algebraic | kneser | 5400–5440 | 41 | 10–406 |
| Random | random_er | 5550–8802 | 3,012 | 10–4,283 |
| Random | barabasi_albert | 8950–12646 | 3,524 | 3–5,640 |
| Random | regular | 12750–16453 | 3,518 | 6–5,640 |
| Random | watts_strogatz | 16600–29976 | 12,540 | 6–5,640 |
| Random | sbm | 30100–31221 | 1,122 | 20–600 |
| Random | lfr_benchmark | 31350–31412 | 61 | 50–3,000 |
| Random | random_planar | 31500–31691 | 192 | 10–742 |
| Physics lattice | triangular_lattice | 31800–31995 | 196 | 9–2,926 |
| Physics lattice | kagome | 32100–32250 | 144 | 12–5,824 |
| Physics lattice | honeycomb | 32350–32517 | 162 | 8–5,830 |
| Physics lattice | king_graph | 32600–32671 | 72 | 9–5,184 |
| Physics lattice | frustrated_square | 32800–32871 | 72 | 9–5,184 |
| Physics lattice | shastry_sutherland | 33000–33071 | 72 | 4–1,369 |
| Physics lattice | cubic_lattice | 33200–33275 | 76 | 8–4,913 |
| Physics lattice | bcc_lattice | 33400–33425 | 26 | 35–6,119 |
| Physics models | weak_strong_cluster | 33550–34005 | 456 | 16–5,640 |
| Physics models | planted_solution | 34150–36765 | 2,616 | 25–1,318 |
| Physics models | spin_glass | 36900–37497 | 598 | 10–958 |
| Hardware | hardware_native | 37600–37641 | 42 | 8–4,928 |
| Special | named_special | 37750–37761 | 12 | 5–46 |
| Special | sudoku | 37900–37901 | 2 | 6,561–65,536 |

---

## Selection syntax

The same selection syntax works in the YAML `graphs` field, in `ember graphs install`, in `ember graphs cache delete`, and in `load_test_graphs()`.

| Expression | Result |
|---|---|
| `"1000-1055"` | IDs 1000 through 1055 inclusive |
| `"1000-1010, 5550-5560"` | Two ranges combined |
| `"1004, 1008, 1553"` | Specific IDs |
| `"1000-1100, !1050"` | Range excluding one ID |
| `"1000-1100 & !1040-1050"` | Range excluding a sub-range |
| `"*"` | All 31,083 graphs |
| `"benchmark"` | Named preset |

Multiple ranges are combined with commas (union). `!` excludes. `&` applies before exclusion.

---

## Named presets

Presets are defined in `ember_qc/graphs/presets.csv`.

| Preset | Count | Description |
|---|---|---|
| `all` | 31,083 | Every graph in the library |
| `installed` | 37 | Bundled with the package — always available offline |
| `quick` | 12 | One smallest graph per main type |
| `default` | 36 | One small representative per type |
| `diverse` | 31 | Hand-picked across all types, varied n |
| `benchmark` | 82 | Curated for algorithm benchmarking, n=3–100 |
| `sensitivity` | 273 | Superset of `benchmark` extended with mid/large graphs (n=50–600) across all 36 families at varied densities; designed for parameter-sensitivity experiments |
| `structured` | 2,568 | All deterministic/algebraic types |
| `lattice` | 820 | All physics lattice types |
| `physics` | 4,490 | Lattices + spin_glass + weak_strong_cluster + planted_solution |
| `hardware_native` | 42 | Hardware topology graphs |
| `named_special` | 12 | Petersen, Tutte, Chvátal, McGee, Franklin, etc. |
| `small` | 617 | All graphs with n ≤ 10 |

```bash
ember graphs presets    # list all presets with resolved counts
```

---

## Browsing the library

```bash
# Type overview: ID ranges, total count, installed count
ember graphs list

# All graphs of one type
ember graphs list complete
ember graphs list random_er

# Installed types/graphs only
ember graphs list -a
ember graphs list complete -a

# Full metadata for a single graph
ember graphs info 1004

# Search by property
ember graphs search --type random_er --max-nodes 20
ember graphs search --topology chimera --min-nodes 50 --max-nodes 200
ember graphs search --type complete -a    # installed complete graphs only
```

---

## Installing graphs

```bash
# Install a preset
ember graphs install benchmark
ember graphs install physics

# Install by ID range or selection
ember graphs install 1000-1055
ember graphs install "5550-5600, !5575"

# Preview without downloading
ember graphs install --dry-run lattice
```

Graphs are cached in the platform user data directory:
- macOS: `~/Library/Application Support/ember-qc/graphs/`
- Linux: `~/.local/share/ember-qc/graphs/`

---

## Cache management

```bash
ember graphs cache                       # disk usage summary by type
ember graphs cache delete benchmark      # remove a preset
ember graphs cache delete 1000-1055      # remove a range
ember graphs cache delete --all          # wipe entire cache (prompts confirmation)
ember graphs verify                      # SHA-256 integrity check on all cached graphs
ember graphs verify --fix                # re-download any corrupt files automatically
```

---

## Filtering by size in Python

```python
from ember_qc import load_test_graphs

# Only graphs with 10–50 nodes
graphs = load_test_graphs("benchmark", min_nodes=10, max_nodes=50)

# All random_er graphs with at most 30 nodes
graphs = load_test_graphs("structured", max_nodes=30)
```

---

## Loading graphs in Python

```python
from ember_qc.load_graphs import (
    load_graph, load_test_graphs, list_test_graphs,
    list_graph_types, graph_info, search_graphs,
)

# Single graph by ID — downloads and caches if not installed
G = load_graph(37760)   # Petersen graph

# Multiple graphs by selection or preset
graphs = load_test_graphs("installed")       # list of (name, nx.Graph)
graphs = load_test_graphs("benchmark", max_nodes=50)

# Catalog from manifest (fast — no files needed)
catalog = list_test_graphs()
for entry in catalog[:5]:
    print(entry["id"], entry["name"], entry["nodes"])

# Type overview
for t in list_graph_types():
    print(t["category"], t["total"], t["installed"])

# Full metadata for one graph
info = graph_info(1004)
print(info["name"], info["nodes"], info["installed"])

# Search
results = search_graphs(category="random_er", max_nodes=20)
```

---

## Graph JSON format

Each graph is stored as a JSON file named `{id}_{name}.json`:

```json
{
  "id": 1004,
  "name": "K6",
  "category": "complete",
  "num_nodes": 6,
  "num_edges": 15,
  "density": 1.0,
  "metadata": { "n": 6 },
  "graph": {
    "directed": false,
    "multigraph": false,
    "nodes": [{"id": 0}, ...],
    "edges": [{"source": 0, "target": 1}, ...]
  }
}
```

The bundled `manifest.json` stores abbreviated metadata for all 31,083 graphs and is used for fast lookup without loading files.
