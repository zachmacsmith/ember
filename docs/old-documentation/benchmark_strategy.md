# Embedding Algorithm Benchmark Strategy
### VQI Benchmark Suite — Algorithm Selection & Integration Plan

*Companion document to "Graph Minor Embedding Algorithms for Quantum Annealing"*

---

## Executive Summary

Of the 22 known minor embedding algorithms surveyed, **8–10 are worth benchmarking**, and only **6 are essential**. This document tiers every algorithm by benchmark priority, explains the rationale, identifies which are currently competitive on the frontier, and provides concrete integration steps for each.

The key insight: the benchmark suite's value comes primarily from the **diversity of test graphs** (real-world QUBO topologies vs. the standard random graphs used in every prior study), not from exhaustively including every algorithm ever published. A focused selection of algorithms that represent distinct competitive approaches is both more tractable and more publishable.

---

## Tier 1 — Essential (Must Benchmark)

These are the algorithms that any credible embedding benchmark must include. They represent the current competitive frontier, are actively compared against each other in the literature, and cover the major algorithmic paradigms (iterative heuristic, structured/deterministic, simulated annealing, adaptive, and learning-based).

---

### 1. MinorMiner (CMR) ⭐ Baseline

**Why essential:** The universal baseline. Every single paper in this space compares against MinorMiner. It is the default in D-Wave's Ocean SDK and the algorithm most practitioners actually use. If your benchmark doesn't include it, the paper is dead on arrival.

**Current competitiveness:** Still solid for mid-density graphs, especially on Chimera. Struggles on Pegasus with dense graphs. Has known failure modes that more recent algorithms exploit.

**Integration:**
```bash
pip install minorminer
```
```python
from minorminer import find_embedding
import dwave_networkx as dnx

target = dnx.pegasus_graph(16)  # or chimera_graph, zephyr_graph
embedding = find_embedding(
    source_edges,
    target.edges(),
    random_seed=42,
    tries=10,        # number of restart attempts
    max_no_improvement=10,
    timeout=60       # seconds
)
```

**Benchmark notes:**
- Run multiple seeds (10–100) per instance and report success rate, median chain length, and best-found qubit count
- Record wall-clock time per attempt
- MinorMiner is stochastic — variance is itself an important metric
- Use default parameters as the baseline, but consider also testing with tuned `tries` and `chainlength_patience`

---

### 2. Clique Embedding (CE) ⭐ Deterministic Reference

**Why essential:** The deterministic worst-case reference. For any problem of size N, you can always embed it by first embedding K_N, then mapping the problem as a subgraph. This establishes the upper bound on qubit usage that any good algorithm should beat. Also the only polynomial-time guaranteed method for fully-connected problems.

**Current competitiveness:** Not competitive for sparse problems (massive overhead), but optimal for dense/fully-connected problems. Serves as both a participant and a calibration point.

**Integration:**
```bash
pip install minorminer
```
```python
from minorminer import find_clique_embedding
import dwave_networkx as dnx

target = dnx.pegasus_graph(16)
# Embed K_n (complete graph on n nodes)
clique_emb = find_clique_embedding(n, target)
# Then restrict to your problem's edges
```

**Benchmark notes:**
- Deterministic — only needs one run per instance
- Report the "clique number" (largest embeddable K_n) for each hardware topology as a reference point
- Use it to compute the "overhead ratio" = (qubits used by algorithm X) / (qubits used by clique embedding) as a normalized metric

---

### 3. OCT-Based / Fast-OCT-Reduce ⭐ Quality Champion

**Why essential:** Produces the highest-quality embeddings (fewest qubits) among methods with public code. The top-down approach via odd cycle transversal decomposition is architecturally distinct from all bottom-up heuristics. If an algorithm claims to be "good," it needs to be compared against OCT's quality.

**Current competitiveness:** Best-in-class for qubit minimization, but prohibitively slow for large instances. This speed/quality tradeoff is exactly what a benchmark should quantify.

**Integration:**
```bash
git clone https://github.com/TheoryInPractice/aqc-virtual-embedding.git
cd aqc-virtual-embedding
make
```

The repo includes a batch experiment runner. Key algorithms to test:
- `fast-oct-reduce` — the best overall variant
- `oct-reduce` — slightly different quality/speed tradeoff
- `cmr` — their wrapper around the CMR heuristic (useful sanity check)

Config file format:
```
[hardware]
chimera 8 8 4
[programs]
<your_graph_generator> <n_min> <n_max> <step> <density>
[algorithm names]
fast-oct-reduce
```

**Benchmark notes:**
- Set generous timeouts (the algorithm is slow — 10–60 min for large instances)
- The quality advantage over MinorMiner is the main story; runtime comparison is secondary
- Only supports Chimera topology natively — you may need to adapt for Pegasus/Zephyr

---

### 4. ATOM ⭐ Speed Champion

**Why essential:** The fastest known method — up to 20× faster than MinorMiner and 66× faster than OCT-based. Its adaptive topology concept is a fundamentally different approach. Any benchmark studying scalability must include it.

**Current competitiveness:** Frontier-competitive on speed. Qubit quality is comparable to MinorMiner (sometimes better, sometimes worse). The real value is embedding problems that other methods time out on.

**Integration:**
- Contact: Hoang M. Ngo, University of Florida (the lead author of both ATOM and CHARME)
- Implemented in C++
- Designed for Chimera topology; may need adaptation for Pegasus/Zephyr
- If code is unavailable, ATOM's approach can be partially replicated by starting with a small Chimera subgraph and expanding

**Benchmark notes:**
- The key metric is the runtime-vs-quality Pareto frontier
- Test on the largest instances where MinorMiner starts struggling (>500 logical variables)
- ATOM's advantage grows with problem size — design test cases accordingly

---

### 5. PSSA (Improved, 2020) ⭐ SA-Based Champion

**Why essential:** The best-performing simulated annealing approach, and the only algorithm demonstrated to scale to 102,400-node hardware graphs. Won a competitive embedding contest. Represents the "metaheuristic" paradigm that is distinct from the path-based (CMR), structural (OCT), and adaptive (ATOM) approaches.

**Current competitiveness:** Excellent on King's graph (CMOS) topologies. Strong on random-cubic and Barabási-Albert graphs. Less tested on Pegasus/Zephyr but the approach is topology-agnostic in principle.

**Integration:**
- No public code. Must either:
  1. Contact authors: Yuya Sugie, Normann Mertig (Hitachi/Hokkaido University)
  2. Reimplement from the paper — the algorithm is well-described in [arXiv:2004.03819](https://arxiv.org/abs/2004.03819)
- Core idea: explore super-vertex placements via probabilistic swaps and shifts with an annealing schedule
- Your FPGA place-and-route background actually makes you well-positioned to reimplement this, since the swap/shift operations are analogous to placement perturbations

**Benchmark notes:**
- If reimplementing, validate against the paper's reported results on random cubic graphs before using in the benchmark
- Test with multiple annealing schedules
- PSSA's advantage is most visible on large hardware graphs — use the largest available topologies

---

### 6. CHARME ⭐ Learning-Based Champion

**Why essential:** The strongest RL-based method and the newest serious contender. Outperforms MinorMiner and ATOM on qubit usage for sparse graphs. Represents the emerging ML-for-combinatorial-optimization paradigm. Reviewers will expect to see at least one learning-based method.

**Current competitiveness:** Best qubit efficiency among fast methods for sparse logical graphs. Runtime comparable to ATOM. However, requires training, which introduces a setup cost that traditional heuristics don't have.

**Integration:**
- Contact: Hoang M. Ngo, University of Florida (same group as ATOM)
- Built on top of ATOM's framework
- Requires: PyTorch, GNN libraries, training data
- Training pipeline: generate training graphs → run ATOM for initial embedding orders → train GNN policy → inference on test graphs

**Benchmark notes:**
- Report training time separately from inference time
- Test generalization: train on one graph class, test on another
- The training cost amortization story matters — is it worth training if you're embedding thousands of problems?

---

## Tier 2 — Strongly Recommended

These add meaningful signal to the benchmark. They either provide a different perspective (initialization strategies, optimality bounds), cover an important niche, or have accessible code that makes inclusion easy.

---

### 7. SPMM + CLMM (Initialization Strategies)

**Why recommended:** Together they cover the full density spectrum on Pegasus better than MinorMiner alone. SPMM wins on sparse graphs, CLMM wins on dense graphs. They demonstrate that smart initialization is often more important than the core algorithm.

**Current competitiveness:** The SPMM/CLMM combination is the best known approach for maximizing embeddability on Pegasus across all densities.

**Integration:** These are not standalone algorithms — they are initialization strategies for MinorMiner.

```python
from minorminer import find_embedding, find_clique_embedding
import dwave_networkx as dnx
import networkx as nx

target = dnx.pegasus_graph(16)

# --- CLMM: Clique-based initialization ---
# Find a clique embedding for a subset of the problem
n_vars = len(source_graph.nodes())
clique_size = min(n_vars, 180)  # max clique on Pegasus ~180
try:
    clique_emb = find_clique_embedding(clique_size, target)
    # Use as initial_chains for the full problem
    initial = {v: clique_emb[i] for i, v in enumerate(list(source_graph.nodes())[:clique_size])}
    embedding = find_embedding(source_edges, target.edges(), initial_chains=initial)
except:
    embedding = find_embedding(source_edges, target.edges())

# --- SPMM: Spring-based initialization ---
# Compute a force-directed layout of the source graph
pos = nx.spring_layout(source_graph, seed=42)
# Map positions to hardware qubits (nearest-neighbor assignment)
# Then pass as initial_chains to find_embedding
```

**Benchmark notes:**
- Compare MinorMiner (default), MinorMiner+SPMM, MinorMiner+CLMM as three variants
- The density crossover point (~0.08 edge density on Pegasus) is a key finding to validate

---

### 8. TEAQC (Template-Based)

**Why recommended:** Open-source ILP method with a fundamentally different approach (template minors). Provides near-optimal solutions on Chimera and can prove optimality bounds.

**Current competitiveness:** Good quality, slow speed. Chimera-only in the current implementation.

**Integration:**
```bash
git clone https://github.com/merlresearch/TEAQC.git
cd TEAQC
pip install -r requirements.txt
# Follow the README for configuration
```

**Benchmark notes:**
- Only useful if benchmarking on Chimera topology
- Good for validating that your benchmark metrics are consistent (its ILP solutions provide a quality reference)

---

### 9. IP Methods (Bernal et al.)

**Why recommended:** The only method that can prove an instance is unembeddable. Essential for establishing ground truth on small instances and for validating that other algorithms aren't missing embeddable instances.

**Current competitiveness:** Not competitive for runtime, but irreplaceable for validation.

**Integration:**
- Contact: David E. Bernal Neira (CMU → now at other institutions)
- Uses standard IP solvers (Gurobi, CPLEX)
- Practical only for small instances (≤50 logical variables on Chimera)

**Benchmark notes:**
- Use on a small subset of instances to establish ground truth
- Report the optimality gap: (best heuristic qubits) / (IP optimal qubits)
- Even partial results (LP relaxation bounds) are valuable

---

### 10. 4-Clique Network Embedding

**Why recommended if testing on Pegasus:** A creative topology-aware approach that trades qubits for chain integrity. Tests a fundamentally different design philosophy (stronger chains vs. shorter chains).

**Current competitiveness:** Not competitive on qubit count, but potentially superior on actual QA solution quality due to reduced chain breaks.

**Integration:**
```python
# The approach: contract the hardware graph into a 4-clique network,
# then use minorminer on the contracted graph
import networkx as nx
from minorminer import find_embedding
import dwave_networkx as dnx

pegasus = dnx.pegasus_graph(16)

# Algorithm 1 from the paper: contract 4-cliques
# Each node in contracted graph = 2 physical qubits (a 4-clique)
# Each edge in contracted graph = 4 physical couplers
# Then embed into the contracted graph
contracted = contract_4cliques(pegasus)  # you'd implement this
embedding_contracted = find_embedding(source_edges, contracted.edges())
# Map back to physical qubits
```

**Benchmark notes:**
- Only meaningful on Pegasus (Chimera has max clique 2, Zephyr has different structure)
- If your benchmark includes QA solution quality metrics (not just embedding metrics), this method's advantage becomes visible

---

## Tier 3 — Optional / Niche

Include these only if your benchmark has a specific reason to (e.g., testing a particular topology, validating fault-tolerance claims, or achieving comprehensive coverage for a survey-style paper).

---

### 11. Date-Potok Efficient Embedding

**Why optional:** Interesting focus on solution quality rather than just qubit count, but no public code and the approach is not well-characterized enough to replicate reliably.

**Include if:** Your benchmark explicitly measures downstream QA solution quality (not just embedding metrics).

---

### 12. Okada Subproblem Embedding

**Why optional:** The "divide and embed" approach is architecturally interesting but operates at a different level — it's more of a problem decomposition strategy than an embedding algorithm per se.

**Include if:** Your benchmark includes problems that are too large to embed monolithically (>5000 logical variables).

---

### 13. PPO-RL (Nembrini et al., 2025)

**Why optional:** Very new, proof-of-concept stage. Less mature than CHARME. Results are promising on Zephyr but not yet competitive with established methods.

**Include if:** You want comprehensive RL coverage, or if you're specifically benchmarking on Zephyr topology.

---

### 14. Lobe-Lutz Exact Method

**Why optional:** Only applies to complete graph embedding on broken Chimera. Extremely specialized.

**Include if:** Your benchmark specifically studies the impact of hardware faults on embeddability.

---

### 15. LAMM (Layout-Aware MinorMiner)

**Why optional:** Superseded by SPMM, which uses the same core idea but with better execution. Including both would be redundant.

**Include if:** You want to show the progression from LAMM → SPMM as an ablation study.

---

## Do Not Benchmark

These are not meaningful to include as benchmark participants, either because they are subsumed by other methods, are theoretical frameworks rather than algorithms, or apply to a fundamentally different problem.

| Algorithm | Reason to Exclude |
|-----------|-------------------|
| Choi (2008/2011) | Foundational theory, not a runnable algorithm |
| TRIAD | Subsumed by OCT-based framework (which includes `triad` as a variant) |
| KSH (Klymko et al.) | Evolved into OCT-based; testing OCT covers this |
| Cartesian Product (Zaribafiyan) | Only works for K_m □ K_n graphs — not general-purpose |
| Universal Bipartite (2025) | Only works for complete bipartite graphs / RBMs |
| Parity Mapping | Different paradigm entirely — not minor embedding |

---

## Recommended Benchmark Configuration

### Algorithm Set (Minimum Viable)

For a strong publication, benchmark these **6 algorithms**:

| Algorithm | Role in Benchmark | Source |
|-----------|-------------------|--------|
| MinorMiner | Universal baseline | `pip install minorminer` |
| Clique Embedding | Deterministic upper bound | `pip install minorminer` |
| OCT (fast-oct-reduce) | Quality reference | GitHub (public) |
| ATOM | Speed reference | Contact authors |
| PSSA | Metaheuristic reference | Contact authors / reimplement |
| CHARME | Learning-based reference | Contact authors |

For an **expanded benchmark** (stronger paper), add:

| Algorithm | Added Value | Source |
|-----------|-------------|--------|
| SPMM/CLMM | Initialization strategy comparison | Implement via minorminer API |
| TEAQC | ILP-based quality reference (Chimera) | GitHub (public) |
| IP (Bernal) | Ground truth on small instances | Contact authors |

