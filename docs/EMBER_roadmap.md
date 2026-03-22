# EMBER — Development Roadmap
### Prioritized Implementation Plan for an AI Coding Agent

This document is the authoritative task list for implementing EMBER. Each phase specifies what to build, exact implementation details, and what to verify before moving on. The developer guide (`EMBER_developer_guide.md`) contains coding standards, the algorithm interface contract, and team organization — read it first.

---

## Repository State

Working: algorithm registry, `benchmark_one()`, `EmbeddingBenchmark` runner, ~100 test graphs across 7 categories, 12 hardware topologies, 5 MinorMiner variants, OCT-based (6 variants), ATOM, PSSA (3 variants), embedding validation, analysis package (plots/tables/significance tests), 163 passing tests.

---

## Phase 1 — Scientific Integrity
**Owner: Zach | Target: Week of March 17 | Milestone: Internal v0.5**

Nothing in later phases produces trustworthy results until Phase 1 is complete.

---

### 1.1 Fix CPU Time for External-Process Algorithms

**Problem:** `time.process_time()` measures the current Python process only. ATOM, OCT, and any algorithm using `subprocess` report near-zero CPU time. This silently invalidates timing results for all C++ algorithms.

**Implementation:**

In the benchmark runner, detect whether the algorithm wrapper uses subprocess (check for a `_uses_subprocess = True` class attribute, or require all C++ wrappers to inherit from a `SubprocessAlgorithm` subclass). Apply the appropriate measurement:

For C++ algorithms:
```python
import resource

children_before = resource.getrusage(resource.RUSAGE_CHILDREN)
# ... subprocess.run(...) call inside embed() ...
children_after = resource.getrusage(resource.RUSAGE_CHILDREN)
cpu_elapsed = (
    (children_after.ru_utime - children_before.ru_utime) +
    (children_after.ru_stime - children_before.ru_stime)
)
```

For Python algorithms, `time.process_time()` is correct and unchanged.

Add `cpu_time_seconds` to `EmbeddingResult` alongside the existing `wall_time_seconds`.

**Verification:**
- Run ATOM on any graph. Assert `cpu_time_seconds > 0.01`.
- Run MinorMiner on the same graph. Assert `cpu_time_seconds > 0.0`.
- Run MinorMiner with a fixed seed twice. Assert both `cpu_time_seconds` values are within 20% of each other.

---

### 1.2 SHA-256 Graph Library Manifest

**Implementation:**

Generate `ember/graphs/library/manifest.sha256` listing every graph file with its hash:
```
random/er/er_n40_p015_s01.json  a3f2b8c9d1e4f7...
random/er/er_n40_p015_s02.json  7b1c3d5e8f2a1b...
```

Add manifest generation to the graph library build script. Add manifest verification to the runner's startup sequence:

```python
def verify_manifest(graph_dir: Path, manifest_path: Path) -> None:
    with open(manifest_path) as f:
        for line in f:
            filename, expected = line.strip().split("  ")
            actual = hashlib.sha256((graph_dir / filename).read_bytes()).hexdigest()
            if actual != expected:
                raise RuntimeError(f"Graph {filename} has been modified (hash mismatch)")
```

Runner must call `verify_manifest()` before loading any graphs. If verification fails, raise — do not proceed.

**Verification:**
- Modify one byte of a graph file. Assert runner raises `RuntimeError` before starting.
- Restore the file. Assert runner proceeds normally.

---

### 1.3 Environment Provenance Logging

**Implementation:**

At the start of every `EmbeddingBenchmark.run()` call, capture and write to `{batch_dir}/config.json`:

```python
import platform, sys, subprocess
from datetime import datetime, timezone

provenance = {
    "python_version": sys.version,
    "platform": platform.platform(),
    "processor": platform.processor(),
    "dependencies": subprocess.check_output(["pip", "freeze"]).decode(),
    "ember_version": ember.__version__,
    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    "experiment_config": config_dict,
}
```

**Verification:**
- Run any benchmark. Assert `config.json` exists in batch directory and is valid JSON.
- Assert `dependencies` field is non-empty and contains "networkx".

---

### 1.4 Train/Test Split Enforcement

**Implementation:**

Establish the directory structure:
```
ember/graphs/library/
├── train/
├── test/
└── manifest.sha256
```

Add a startup check:

```python
def check_train_test_overlap(library_path: Path) -> None:
    train_ids = {f.stem for f in (library_path / "train").rglob("*.json")}
    test_ids  = {f.stem for f in (library_path / "test").rglob("*.json")}
    overlap = train_ids & test_ids
    if overlap:
        raise RuntimeError(f"Train/test overlap detected: {overlap}")
```

Call at runner startup alongside manifest verification.

**Verification:**
- Copy one graph into both `train/` and `test/`. Assert runner raises `RuntimeError`.
- Remove the duplicate. Assert runner starts normally.

---

### Phase 1 Smoke Benchmark

Run: 20 graphs (mixed categories) × 2 topologies (Pegasus 16, Chimera 16×16×4) × 2 algorithms (MinorMiner, ATOM) × 3 seeds.

Confirm: `cpu_time_seconds` non-zero for ATOM, manifest verified at startup, `config.json` written, overlap detection fires on a deliberate violation.

---

## Phase 2 — Graph Library
**Owner: Team member B | Target: Week of March 31 | Milestone: ~600 graphs 


### 2.2 QUBO Generators

**File:** `ember/graphs/qubo_generators.py`

Each function returns a plain `nx.Graph`. No benchmark infrastructure dependencies. Priority order:

| Function | Problem | Notes |
|---|---|---|
| `maxcut_qubo_graph(G)` | MAX-CUT | Input graph IS the QUBO graph |
| `partition_qubo_graph(n, weights, seed)` | Number Partitioning | Complete graph on n variables |
| `coloring_qubo_graph(G, n_colors, seed)` | Graph Coloring | n×k variables, constraint edges |
| `tsp_qubo_graph(n_cities, seed)` | TSP | n² variables, O(n³) constraint edges |
| `portfolio_qubo_graph(n_assets, seed)` | Portfolio Optimization | Dense from covariance matrix |

Both generators and pre-generated instances go in the repo. Generators are required for reviewer reproducibility — graphs labeled `tsp_n8` cannot be verified without them.

---

### 2.3 Planted Solution Graphs

**Purpose:** The only graph class that allows comparison to the theoretical optimum. Guaranteed valid embedding with chain length 1.

**Construction:** Take a hardware topology. Randomly select n_source_nodes nodes. Contract them to form a source graph. The contraction mapping is the ground-truth optimal embedding.

```python
def planted_solution_graph(
    topology: nx.Graph,
    n_source_nodes: int,
    seed: int = None
) -> Tuple[nx.Graph, Dict]:
    """Returns (source_graph, optimal_embedding) where chain length = 1 for all vertices."""
```

Store source graph in `planted/{topology}/`. Store ground-truth embedding as sidecar JSON. Generate ≥10 instances per topology family at varied sizes.

**Verification:** Ground-truth embedding passes validator. MinorMiner finds a valid embedding on all planted graphs.

---

### 2.4 Random Graph Scale-Up

Extend existing generators in `graphs.py`. Do not rewrite or re-seed them.

| Type | n values | Secondary param | Seeds | ~Count |
|---|---|---|---|---|
| Erdős-Rényi | 20–180 step 20 | p ∈ {0.02,0.05,0.08,0.10,0.15,0.20,0.30,0.50} | 3 | 216 |
| Barabási-Albert | 20–180 step 20 | m ∈ {1,2,3,4,5} | 2–3 | 100 |
| d-Regular | 20–180 step 20 | d ∈ {3,4,5,6,8,10} | 2 | 80 |

---

### 2.5 Stress Test Graphs

**Near-threshold:** Binary search for largest n such that ER(n, 0.1) embeds on Pegasus 16 in ≥50% of seeds with MinorMiner. Generate 10–15 instances near this threshold.

**High-degree hubs:** One degree-50 node connected to degree-3 peripheral nodes. 10 instances with varied hub-to-peripheral ratios.

---

### 2.6 Graph Structural Properties

**File:** `ember/graphs/properties.py`

```python
@dataclass
class GraphProperties:
    n_vertices: int
    n_edges: int
    density: float
    avg_degree: float
    max_degree: int
    min_degree: int
    degree_std: float
    avg_clustering: float
    algebraic_connectivity: float   # Fiedler value via scipy sparse eigensolver
    is_planar: bool                 # only compute for n <= 100
    is_bipartite: bool
    source_problem: Optional[str]   # "MAX-CUT", "TSP", etc. if QUBO
```

Store as `{graph_id}_properties.json` sidecar. Parallelise computation with `multiprocessing.Pool`. Do not compute exact diameter — use BFS approximation for large graphs or omit.

**Verification:**
- Every graph has a properties sidecar
- `algebraic_connectivity > 0` for all connected graphs
- `density == 1.0` for all complete graphs

---

### Phase 2 Smoke Benchmark

- Load all graphs; assert every graph has a properties sidecar
- Assert at least one graph from each of the 6 top-level categories loads correctly
- Run MinorMiner on all planted-solution graphs; assert ground-truth embeddings pass validator with chain length 1

---

## Phase 3 — Data Pipeline
**Owner: Zach | Target: Week of April 7 | Milestone: Full benchmark runnable**

---

### 3.1 JSONL-per-Worker + SQLite Compilation

**During benchmark:** Each worker writes to its own `.jsonl` file. No locking.

```python
worker_file = output_dir / f"workers/worker_{os.getpid()}.jsonl"
with open(worker_file, "a") as f:
    f.write(json.dumps(result.to_dict()) + "\n")
```

**Compilation script** (`ember/pipeline/compile.py`):
1. Read all `worker_*.jsonl` files
2. Validate every embedding
3. Compute metrics
4. Write `runs` and `metrics` tables to SQLite
5. Write per-vertex telemetry to Parquet

**Do not put per-vertex telemetry in SQLite.** Nested arrays for 90K runs in blob columns makes the database unmanageable and slow for the ML data loader. Parquet only.

```
batch_dir/
├── workers/worker_*.jsonl
├── results.db
├── telemetry/per_vertex_{batch_id}.parquet
└── config.json
```

**Verification:**
- 50 graphs × 1 topology × 2 algorithms × 5 seeds
- Row count in `runs` = 500
- No `INVALID_OUTPUT` for known-good algorithms
- Parquet readable with `pandas.read_parquet()` when `record_per_vertex=True`

---

### 3.2 Per-Vertex Telemetry

```python
@dataclass
class EmbeddingResult:
    # ... existing fields ...
    per_vertex_data: Optional[Dict[int, dict]] = None
```

Compute post-hoc for MinorMiner:
```python
def compute_per_vertex_data(embedding, target_graph):
    return {
        v: {
            "chain_length": len(chain),
            "chain_diameter": nx.diameter(target_graph.subgraph(chain)) if len(chain) > 1 else 0,
        }
        for v, chain in embedding.items()
    }
```

Only collected when `record_per_vertex=True`.

---

### 3.3 Checkpointing

```python
checkpoint_key = f"{algorithm}_{graph_id}_{topology}_{seed}"
if checkpoint_key in completed:
    continue
# ... run ...
completed.add(checkpoint_key)
save_checkpoint(completed, batch_dir)
```

On `resume=True`, load checkpoint and skip completed keys.

**Verification:** Interrupt at 30%. Resume. Assert total reaches 100% without re-running completed keys. Assert results identical to an uninterrupted run.

---

### Phase 3 Smoke Benchmark

50 graphs × 2 topologies × 2 algorithms × 5 seeds. Interrupt at ~30%, resume, verify correct completion and all output artifacts.

---

## Phase 4 — Configuration and Reproducibility
**Owner: Zach | Target: Week of April 14 | Milestone: YAML-driven experiments**

---

### 4.1 YAML Experiment Configuration

```yaml
experiment_name: "dense_graphs_pegasus"
algorithms: [minorminer, oct-fast-oct-reduce, atom]
graphs:
  selection: "qubo"
topologies: [pegasus_16, chimera_16x16x4]
seeds: 10
timeout_seconds: 120
record_per_vertex: true
faulty_qubit_rate: 0.0
```

A copy (with resolved graph IDs and software versions appended) is written to `{batch_dir}/config.yaml`.

After implementing, version-control `tests/smoke/smoke_benchmark.yaml` as the canonical smoke test.

---

### 4.2 Faulty Qubit Simulation

```python
def simulate_faults(topology: nx.Graph, fault_rate: float, seed: int = None) -> nx.Graph:
    rng = random.Random(seed)
    n_faults = int(len(topology) * fault_rate)
    faulty = set(rng.sample(list(topology.nodes()), n_faults))
    return topology.subgraph([n for n in topology.nodes() if n not in faulty]).copy()
```

Test at 0%, 1%, 3%, 5%. Applied to topology before passing to algorithm.

**Verification:**
- YAML config parses correctly; unknown fields raise `ValueError`
- Config copy in `batch_dir` matches original plus resolved additions
- 5% fault rate on Pegasus 16 produces ~5% fewer nodes (within ±1%)
- Same seed produces identical faulty topology on two calls

---

## Phase 5 — Analysis Enhancements
**Owner: Zach | Target: Week of April 21 | Milestone: Paper-ready outputs**

### 5.1 Per-Graph-Property Regression
Scatter plots using `GraphProperties` from Phase 2.6: density vs. ACL by algorithm, max degree vs. success rate, algebraic connectivity vs. embedding time.

### 5.2 Novel Chain Metrics
Add to metrics layer and SQLite schema:
- **Chain diameter:** `nx.diameter(target.subgraph(chain))`
- **Chain length CV:** `std(chain_lengths) / mean(chain_lengths)`

### 5.3 LaTeX Table Verification
Verify existing `.tex` exporter compiles against IEEE TQE and ACM TQC templates. Fix formatting discrepancies.

---

## Phase 6 — Public Release
**Owner: Zach | Target: Week of April 28 | Milestone: v1.0**

- README reflecting full library, QUBO generators, planted solutions, new metrics
- `pyproject.toml`: `pip install -e .` from clean environment
- GitHub Actions: pytest on push; manifest verification on changes to `graphs/library/`
- Quickstart notebook: YAML config → Pareto plot
- License audit: all vendored algorithm licenses compatible with EMBER's license

---

## Full Release Checklist (v1.0)

**Graph Library**
- [ ] ~600 graphs with typed IDs
- [ ] All SHA-256 verified against manifest
- [ ] Train/test split enforced programmatically
- [ ] QUBO generators for ≥4 problem classes in repo alongside pre-generated graphs
- [ ] Planted-solution graphs for all three topology families with ground-truth embeddings
- [ ] GraphProperties sidecar for every graph

**Algorithms**
- [ ] ≥4 algorithms benchmarked
- [ ] PSSA contract violations fixed
- [ ] All vendored code has license file + SOURCE.md with commit hash
- [ ] Algorithm contract tests pass for every registered algorithm

**Data Integrity**
- [ ] CPU time correct for C++ algorithms (RUSAGE_CHILDREN)
- [ ] Wall-clock and CPU time in every result
- [ ] Every embedding validated before metrics computed
- [ ] Validator catches all four failure modes
- [ ] Per-vertex telemetry in Parquet, not SQLite

**Execution**
- [ ] 600 graphs × 3 topologies × 4 algorithms × 10 seeds completes without crashes
- [ ] Checkpointing: interrupted run resumes correctly
- [ ] YAML config drives runs; copy in every batch directory
- [ ] Provenance logged in every batch directory

**Analysis**
- [ ] LaTeX tables compile against IEEE TQE template
- [ ] Pareto plot renders
- [ ] Wilcoxon tests produce correct p-values
- [ ] Property regression plots generated

**Release**
- [ ] All unit tests pass: `pytest tests/ -v`
- [ ] Smoke benchmark (canonical YAML) completes without errors
- [ ] README accurate
- [ ] `pip install -e .` works from clean environment
- [ ] GitHub Actions CI passing
