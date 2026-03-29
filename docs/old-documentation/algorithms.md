# Algorithm Registry

QEBench uses a plugin system for embedding algorithms. All algorithms implement `EmbeddingAlgorithm` and are auto-registered via `@register_algorithm("name")`.

## Working Algorithms

### `minorminer`
**D-Wave MinorMiner** — industry-standard heuristic embedding.

- **Type:** Heuristic, randomized
- **Source:** `pip install minorminer` (D-Wave)
- **Paper:** Cai, Macready & Roy (2014), "A practical heuristic for finding graph minors"
- **Strengths:** Fast, general-purpose, works on any topology (Chimera, Pegasus, Zephyr)
- **Weaknesses:** Non-deterministic, quality varies between runs

```python
result = benchmark_one(source, target, "minorminer")
```

---

### `minorminer-aggressive`
**D-Wave MinorMiner (aggressive)** — CMR with more restarts for higher quality embeddings.

- **Type:** Heuristic, randomized
- **Source:** `minorminer` (same as above, different parameters)
- **Parameters:** `tries=50`, `max_no_improve=20`
- **Strengths:** Better embedding quality and shorter chains than default minorminer
- **Weaknesses:** Significantly slower — ~5× more attempts per run
- **Best for:** When embedding quality matters more than speed (e.g., final benchmarks, dense graphs)
```python
result = benchmark_one(source, target, "minorminer-aggressive")
```

---

### `minorminer-fast`
**D-Wave MinorMiner (fast)** — CMR with fewer restarts for rapid turnaround.

- **Type:** Heuristic, randomized
- **Source:** `minorminer` (same as above, different parameters)
- **Parameters:** `tries=3`, `max_no_improve=3`
- **Strengths:** Very fast — good for large-scale sweeps or quick feasibility checks
- **Weaknesses:** Lower success rate and longer chains than default minorminer
- **Best for:** Large graph libraries where you just need a quick pass, or as a lower-quality baseline
```python
result = benchmark_one(source, target, "minorminer-fast")
```

---

### `minorminer-chainlength`
**D-Wave MinorMiner (chain-optimised)** — CMR tuned to minimise chain lengths.

- **Type:** Heuristic, randomized
- **Source:** `minorminer` (same as above, different parameters)
- **Parameters:** `tries=20`, `chainlength_patience=20`
- **Strengths:** Produces shorter chains than default — important for solution quality on real hardware (longer chains increase noise sensitivity)
- **Weaknesses:** Slower than default, roughly similar speed to `minorminer-aggressive`
- **Best for:** Benchmarking chain length specifically, or preparing embeddings for actual QPU runs
```python
result = benchmark_one(source, target, "minorminer-chainlength")
```

---

### `clique`
**D-Wave Clique Embedding** — topology-aware deterministic baseline.

- **Type:** Deterministic, topology-native
- **Source:** `minorminer.busclique.find_clique_embedding`
- **Strengths:** Very fast (sub-millisecond), deterministic, exploits known topology structure
- **Weaknesses:** Higher qubit overhead — embeds into clique substructure rather than optimizing per-problem
- **Note:** Works best on D-Wave native topologies (Chimera, Pegasus, Zephyr)

```python
result = benchmark_one(source, target, "clique")
```

---

### `oct-triad`
**TRIAD** — deterministic OCT-based embedding using biclique virtual hardware.

- **Type:** Deterministic
- **Source:** C++ binary (`algorithms/oct_based/embedding/driver`)
- **Paper:** Goodrich, Sullivan & Humble (2018), "Optimizing adiabatic quantum program compilation using a graph-theoretic framework"
- **Chimera only:** Requires Chimera topology
- **Strengths:** Deterministic, handles dense graphs, guaranteed 2 qubits/node
- **Weaknesses:** Chimera-only, typically higher qubit usage than minorminer

```python
result = benchmark_one(source, chimera_graph, "oct-triad")
```

---

### `oct-triad-reduce`
**Reduced TRIAD** — TRIAD with chain reduction post-processing.

- **Type:** Deterministic
- **Same as `oct-triad`** but applies reduction subroutines to minimize chain lengths after initial embedding
- **Typically produces same or better chains** than plain TRIAD

---

### `oct-fast-oct`
**Fast-OCT** — randomized OCT decomposition with repeated restarts.

- **Type:** Randomized (seed=42, runs=100)
- **Paper:** Goodrich, Sullivan & Humble (2018)
- **Chimera only**
- **Strengths:** Often produces the best embedding quality among OCT variants
- **Note:** Uses greedy randomized OCT approximation with 100 restarts

---

### `oct-fast-oct-reduce`
**Reduced Fast-OCT** — Fast-OCT with chain reduction.

- **Best quality** among OCT-suite algorithms — combines randomized OCT with reduction

---


### PSSA — path-annealing simulated annealing, adapted for D-Wave hardware.
* Type: Simulated annealing heuristic (auto tmax, scaled to hardware size)
* Paper: Sugie et al. (2020) arXiv:2004.03819
* Chimera, Pegasus, Zephyr
* Strengths: Strong on cubic/regular graphs, terminal search recovers wasted qubits
* Note: install — see github.com/Unmolsharma/PSSA-Dwave-Implementation-

### pssa-weighted

PSSA with degree-weighted shift proposals.
* Type: Simulated annealing heuristic (weighted, auto tmax)
* Paper: Sugie et al. (2020) arXiv:2004.03819
* Chimera, Pegasus, Zephyr
* Strengths: Best variant for 3-regular and cubic input graphs
* Note: install — see github.com/Unmolsharma/PSSA-Dwave-Implementation-

### pssa-fast

PSSA with reduced iteration count for quick runs.
* Type: Simulated annealing heuristic (tmax=50,000)
* Paper: Sugie et al. (2020) arXiv:2004.03819
* Chimera, Pegasus, Zephyr
* Strengths: Fast feasibility checks, good for large parameter sweeps
* Note: Oinstall — see github.com/Unmolsharma/PSSA-Dwave-Implementation-

### pssa-thorough

PSSA with extended iteration count for best quality.
* Type: Simulated annealing heuristic (tmax=2,000,000)
* Paper: Sugie et al. (2020) arXiv:2004.03819
* Chimera, Pegasus, Zephyr
* Strengths: Highest quality embeddings, best for final benchmarks and hard graphs
* Note: install — see github.com/Unmolsharma/PSSA-Dwave-Implementation-


## Partially Working

### `oct-hybrid-oct` / `oct-hybrid-oct-reduce`
**Hybrid-OCT** — combined deterministic + randomized approach.

- **Status:** Runs but frequently produces invalid embeddings on non-bipartite graphs
- **Works correctly** on bipartite source graphs
- **Chimera only**

### `atom`
**ATOM** — grows its own Chimera topology dynamically.

- **Status:** Binary runs but only outputs timing, not the actual chain mapping
- **Fix needed:** Modify C++ source to write embedding to file
- **Source:** C++ binary (`algorithms/atom/main`)

### `charme`
**CHARME** — reinforcement learning-based embedding.

- **Status:** Stub — `embed()` returns None
- **Fix needed:** Integrate Python modules (`charme/env.py`, `charme/models.py`, `charme/ppo.py`)
- **Paper:** RL-based minor embedding (2025)
- **Source:** `algorithms/charme/`

---

## Adding a New Algorithm

```python
from qebench.registry import register_algorithm, EmbeddingAlgorithm

@register_algorithm("my_algorithm")
class MyAlgorithm(EmbeddingAlgorithm):
    """My custom embedding algorithm."""
    
    def embed(self, source_graph, target_graph, timeout=60.0, **kwargs):
        # Your embedding logic here
        embedding = {node: [physical_qubits] for node in source_graph.nodes()}
        elapsed = ...
        return {'embedding': embedding, 'time': elapsed}
        # Return None if embedding fails
```

## Listing Algorithms

```python
from qebench import list_algorithms, ALGORITHM_REGISTRY

print(list_algorithms())
# ['atom', 'charme', 'clique', 'minorminer', 'oct-fast-oct', ...]

# Get algorithm details
algo = ALGORITHM_REGISTRY["minorminer"]
print(algo.description)
```
