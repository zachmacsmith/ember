# QEBench — Task Tracker & Roadmap

## ✅ Completed

### Framework Architecture
- [x] Refactored to stateless `benchmark_one()` — the atomic unit
- [x] `EmbeddingResult` stores actual embeddings, topology_name, problem metadata
- [x] Warm-up trials (discarded before measurement)
- [x] Multi-trial support with per-trial numbering
- [x] Dead method cleanup (removed `run_minorminer`, `run_atom`, `benchmark_single`, etc.)

### Package Structure
- [x] Created `qebench/` Python package with clean `__init__.py`
- [x] `qebench/benchmark.py` — benchmark_one, EmbeddingBenchmark, EmbeddingResult
- [x] `qebench/registry.py` — algorithm plugin system
- [x] `qebench/graphs.py` — graph loading, selection, presets
- [x] `qebench/results.py` — ResultsManager (batch dirs, CSV, JSON, summary)
- [x] `qebench/topologies.py` — topology registry (chimera, pegasus, zephyr)

### Results Storage
- [x] Auto-timestamped batch directories (`results/batch_YYYY-MM-DD_HH-MM-SS/`)
- [x] `runs.csv` — every trial as a row (no embeddings, lightweight)
- [x] `runs.json` — every trial with actual embeddings (full archive)
- [x] `summary.csv` — grouped averages ± std dev by (algo, graph, topology)
- [x] `config.json` — machine-readable run settings
- [x] `README.md` — human-readable summary per batch
- [x] `batch_note` parameter for annotating runs
- [x] `latest` symlink to most recent batch

### Multi-Topology Support
- [x] Topology registry with 12 built-in D-Wave topologies
- [x] Chimera (4×4×4, 8×8×4, 12×12×4, 16×16×4)
- [x] Pegasus (P4, P6, P8, P16)
- [x] Zephyr (Z2, Z4, Z6, Z8)
- [x] Custom topology registration (`register_topology`)
- [x] Multi-topology benchmarking (`topologies=["chimera_4x4x4", "pegasus_4"]`)

### Directory Cleanup
- [x] Archived 9 redundant files to `archived/`
- [x] Renamed `implementations/` → `algorithms/`
- [x] Moved `charme-rl-minor-embedding/` into `algorithms/`
- [x] Structured `results/` directory

### Testing
- [x] 84 tests, all passing (2.0s)
- [x] Covers: imports, benchmark_one, EmbeddingResult, metrics, registry, graph selection, presets, graph loading, batch runner, results storage, topology registry

### Documentation
- [x] `WORKFLOW.md` — benchmarking workflow and API reference (package structure corrected)
- [x] `docs/SESSION_SUMMARY.md` — full record of framework redesign session
- [x] `docs/atom_changes.md` — exact C++ modifications made to ATOM source
- [x] `docs/algorithms.md` and `docs/topologies.md` — algorithm/topology references

### Onboarding
- [x] `requirements.txt` — Python dependencies listed

### Algorithm Fixes (Completed)
- [x] **ATOM output fix** — Fixed buffer underflow in `extract_order()`, replaced broken multithreaded BFS with serial fallback, uncommented `embedding->print()` so binary outputs chain mapping to stdout; Python wrapper captures and parses this output (see `docs/atom_changes.md`)
- [x] **MinorMiner NetworkX 3.x fix** — resolved node string conversion and target graph format issues
- [x] **Graph loader NetworkX version fix** — `load_graph()` now detects whether the JSON uses `'edges'` or `'links'` as the edge key and passes it explicitly to `node_link_graph()`; `save_graph()` normalizes to `'edges'` on write (fixes all 15 `TestGraphLoading`/`TestBatchRunner` failures)

---

## 🔬 Algorithm Status

| Algorithm | Status | Notes |
|-----------|--------|-------|
| `minorminer` | ✅ Working | NetworkX 3.x compatibility fixed |
| `clique` | ✅ Working | — |
| `oct-triad` | ✅ Working | — |
| `oct-triad-reduce` | ✅ Working | — |
| `oct-fast-oct` | ✅ Working | Was segfaulting due to input file format bug; fixed — node orderings now written |
| `oct-fast-oct-reduce` | ✅ Working | Same fix as fast-oct |
| `oct-hybrid-oct` | ⚠️ Runs, often invalid | Produces embeddings but fails validation on non-bipartite graphs — known limitation |
| `oct-hybrid-oct-reduce` | ⚠️ Same | Same as hybrid-oct |
| `atom` | ✅ Fixed | Buffer underflow + threading + output parsing all fixed (see `docs/atom_changes.md`) — verify embedding quality in practice |
| `charme` | ❌ Stub | Python RL framework, `embed()` returns None — needs direct Python module import |

---

## 🐛 Active Bugs

~~All clear — see Completed section for resolved issues.~~

---

## 🚀 Onboarding & Compilation

### Quick-Start Setup
- [x] **One-command setup script** (`setup.sh`) — installs Python deps, compiles ATOM and OCT, prints algorithm availability summary
- [x] ~~`requirements.txt` or `pyproject.toml`~~ — `requirements.txt` exists
- [ ] **Pre-built binaries** for macOS arm64 (or at minimum, verified Makefile targets)

### Algorithm Compilation
- [ ] **Verify OCT Makefile** compiles cleanly on macOS with Apple Clang
- [x] ~~Debug fast-oct segfault~~ — fixed via node ordering fix
- [x] ~~Verify ATOM Makefile compiles~~ — ATOM compiled and fixed
- [ ] **Add compilation status check** — `qebench.check_algorithms()` prints which binaries are found/working

### Algorithm Integration Fixes
- [x] ~~ATOM output fix~~ — completed; see `docs/atom_changes.md`
- [ ] **CHARME integration** — import `charme.env`, `charme.models` Python modules directly (currently `embed()` returns None)
- [ ] **Add clique embedding** — `dwave_networkx.find_clique_embedding` as registered baseline

---

## 🔲 Remaining Tasks

### Algorithm Integration (High Priority)
- [ ] **CHARME integration** — RL-based algorithm requires Python module import, not subprocess call; `embed()` currently returns None
- [ ] **OCT compilation verification** — confirm all OCT C++ variants compile cleanly on macOS Apple Clang (fast-oct and hybrid-oct segfaults were fixed, but a clean Makefile pass should be verified)
- [ ] **Clique embedding** — add `dwave_networkx.find_clique_embedding` as a registered algorithm (easy baseline)

### Real-Problem QUBO Generators (Critical for Paper 1)
- [ ] **Design `problem_generators.py` interface** — `generate_instance()` → `to_qubo()` → `to_interaction_graph()`
- [ ] **Max-Cut generator** — BiqMac/Beasley instances, trivial QUBO formulation (start here)
- [ ] **TSP generator** — TSPLIB instances (burma14, bayg29), dense QUBO
- [ ] **Job Shop Scheduling** — OR-Library instances, sparse structured graphs
- [ ] **Graph Coloring** — DIMACS challenge instances
- [ ] **Knapsack** — parameterized generation, dense
- [ ] **Number Partitioning** — fully connected (worst-case embedding)
- [ ] **Portfolio Optimization** — synthetic from correlation matrices
- [ ] **Validate all formulations** against brute-force optimal for small instances

### Graph Characterization (High Priority for Paper 2)
- [ ] **Create `graph_analysis.py`** module with structural property computation:
  - [ ] Degree distribution (mean, std, min, max)
  - [ ] Clustering coefficient (global + average local)
  - [ ] Treewidth estimate (min-degree heuristic upper bound)
  - [ ] Community structure (Louvain modularity, number of communities)
  - [ ] Planarity
  - [ ] Bandwidth
  - [ ] Bipartiteness
  - [ ] Symmetry / automorphism group size estimate
- [ ] **Attach characterization to all test graphs** as metadata
- [ ] **Compare real-problem vs random graph properties** systematically

### Broken/Noisy Topologies
- [ ] **Simulate dead qubits** — remove random nodes from ideal topologies
- [ ] **Broken topology registration** — `chimera_4x4x4_broken_5pct` etc.
- [ ] **Benchmark on broken vs ideal** to measure robustness

### Enhanced Reporting & Analysis
- [ ] **Head-to-head comparison tables** — algorithm A vs B per problem class
- [ ] **Statistical significance testing** — Wilcoxon signed-rank across trials
- [ ] **Pareto frontier plots** — time vs. chain quality
- [ ] **Exportable LaTeX tables** for papers
- [ ] **Results grouped by problem class** and density band
- [ ] **Per-algorithm drilldown** visualizations

### Hyperparameter System
- [ ] **Config-driven parameter variation** — sweep algorithm hyperparameters
- [ ] **Record hyperparameters in results** for reproducibility

### Resource Tracking
- [ ] **Peak memory measurement** per embedding attempt
- [ ] **CPU utilization** tracking

### Public Release & Leaderboard
- [ ] **GitHub Pages leaderboard** — static site generated from results JSON
- [ ] **Contribution workflow** — fork → run → submit PR with results
- [ ] **CI validation** of submitted results format
- [ ] **Polish README** with badges, quickstart, contribution guide
- [ ] **v0.1 release** — core suite with 3-4 problem types + MinorMiner baseline

### Novel Algorithm (Paper 3)
- [ ] **Prototype pathfinder-inspired embedding algorithm**
- [ ] **Register via `@register_algorithm`**
- [ ] **Benchmark against all existing algorithms** on full suite
- [ ] **Analyze structural conditions** where it excels

---

## 📄 Paper Timeline

| Paper | Title (working) | Depends On | Target |
|-------|----------------|------------|--------|
| **Paper 1** | QEBench: Standardized Benchmark Suite | QUBO generators, graph characterization, baseline results | QCE 2027 |
| **Paper 2** | How Problem Structure Affects Embedding | Paper 1 complete, structural analysis | QIP or QST |
| **Paper 3** | Novel Embedding Algorithm | Paper 1 + competitive algorithm | QIP, PRA, or QCE |
