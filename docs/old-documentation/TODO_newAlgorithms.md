# Graph Minor Embedding Algorithms for Quantum Annealing

A comprehensive catalog of all competitive (current and historical) algorithms for the graph minor embedding problem — mapping logical problem graphs onto the sparse hardware topologies of quantum and CMOS annealers.

---

## 1. MinorMiner (CMR Heuristic)

**Authors:** Jun Cai, William G. Macready, Aidan Roy (D-Wave Systems)  
**Year:** 2014  
**Status:** 🟢 Industry standard — the default embedding tool in D-Wave's Ocean SDK

**Summary:** The foundational heuristic for general-purpose minor embedding. It iteratively constructs vertex-models (chains) for each logical variable by finding shortest paths on the hardware graph. It starts with an initial (possibly overlapping) placement, then refines iteratively — removing and reinserting chains to reduce overlaps until a valid embedding is found or a timeout is reached. It is stochastic, topology-agnostic, and works well on sparse logical graphs but can struggle with dense graphs, especially on Pegasus.

**Key Features:**
- Supports `initial_chains`, `fixed_chains`, and `restrict_chains` for user-guided embedding
- Both Python and C++ API
- Topology-agnostic (works on Chimera, Pegasus, Zephyr, arbitrary graphs)

**Paper:** [arXiv:1406.2741](https://arxiv.org/abs/1406.2741)  
**GitHub:** [github.com/dwavesystems/minorminer](https://github.com/dwavesystems/minorminer)  
**Install:** `pip install minorminer`

```python
from minorminer import find_embedding
embedding = find_embedding(source_edges, target_edges)
```

---

## 2. Clique Embedding (CE) / Fast Clique Minor Generation

**Authors:** Tomas Boothby, Andrew D. King, Aidan Roy (D-Wave Systems)  
**Year:** 2016 (Chimera), extended for Pegasus & Zephyr  
**Status:** 🟢 Active — included in D-Wave's minorminer package

**Summary:** A deterministic, polynomial-time algorithm for embedding complete graphs (cliques) into structured hardware topologies. It exploits the regular structure of Chimera/Pegasus/Zephyr graphs to construct "native clique minors" with uniform, near-minimal chain lengths using L-shaped block structures. For Chimera C(M,N,L), it runs in O(N⁵). This serves as both a standalone tool for fully-connected problems and as a worst-case baseline for evaluating other heuristics.

**Key Features:**
- Deterministic — always produces the same result
- Handles broken/faulty qubits
- Polynomial-time for all D-Wave topologies
- Used as a subroutine by other algorithms (e.g., CLMM)

**Paper:** [arXiv:1507.04774](https://arxiv.org/abs/1507.04774) — *Fast clique minor generation in Chimera qubit connectivity graphs*  
**GitHub:** Part of [github.com/dwavesystems/minorminer](https://github.com/dwavesystems/minorminer)  
**Install:** `pip install minorminer`

```python
from minorminer import find_clique_embedding
embedding = find_clique_embedding(k, target_graph)
```

---

## 3. OCT-Based Embedding (Virtual Hardware Framework)

**Authors:** Timothy D. Goodrich, Blair D. Sullivan, Travis S. Humble  
**Year:** 2018  
**Status:** 🟡 Research — excellent quality but slow for large instances

**Summary:** A top-down, structured approach that introduces a *virtual hardware* abstraction layer. It decomposes the problem graph using Odd Cycle Transversal (OCT) to exploit bipartite structure, then maps through a biclique virtual hardware layer. The "Fast-OCT-reduce" variant combines the OCT decomposition with generalized reduction methods. This method produces high-quality embeddings (fewer qubits) but suffers from high computational complexity, making it impractical for time-sensitive applications.

**Variants:**
- `triad` / `triad-reduce` — baseline triangle-based
- `cmr` — Cai-Macready-Roy wrapped in the framework  
- `oct` / `oct-reduce` — OCT-based embedding
- `fast-oct` / `fast-oct-reduce` — optimized OCT (best overall quality)

**Paper:** Goodrich, Sullivan & Humble. "Optimizing adiabatic quantum program compilation using a graph-theoretic framework." *Quantum Information Processing* 17(5):118, 2018.  
**GitHub:** [github.com/TheoryInPractice/aqc-virtual-embedding](https://github.com/TheoryInPractice/aqc-virtual-embedding)  
**Language:** C++ with Python wrappers

---

## 4. PSSA (Probabilistic Swap-Shift Annealing)

**Authors:** Yuya Sugie, Yuki Yoshida, Normann Mertig, et al. (Hitachi / Hokkaido University)  
**Year:** 2018 (original), 2020 (improved)  
**Status:** 🟡 Research — strong performer, especially on King's graph / CMOS topologies

**Summary:** Uses simulated annealing to explore the space of super-vertex placements (SVPs). New placements are generated using random swaps and shifts of super-vertices while monitoring the number of faithfully represented edges. Originally won a hardware embedding contest, outperforming the CMR heuristic by allowing embedding of problems with up to 50% more variables on King's graph topologies.

**Iterations:**
- **PSSA v1 (2018):** Original swap-shift-annealing on King's graph hardware
- **Improved PSSA (2020):** Added (i) an additional search phase, (ii) degree-oriented super-vertex shift rule, and (iii) optimized annealing schedules. Tested on hardware graphs up to 102,400 spins.

**Key Features:**
- Particularly strong on King's graph (CMOS annealer) topologies
- Outperforms CMR by factor of ~3.2× (random-cubic) and ~2.8× (Barabási-Albert) on large hardware
- Produces path-like super-vertices (vs. tree-type in CMR)

**Papers:**
- Original: Sugie et al. "Graph Minors from Simulated Annealing for Annealing Machines with Sparse Connectivity." TPNC 2018. [Springer](https://link.springer.com/chapter/10.1007/978-3-030-04070-3_9)
- Improved: [arXiv:2004.03819](https://arxiv.org/abs/2004.03819) — published in *Soft Computing* 25, 1731–1749 (2021).  
**Code:** No public repository found. The algorithm is described in detail in the papers.

---

## 5. Layout-Aware MinorMiner (LAMM)

**Authors:** Jose P. Pinilla, Steven J.E. Wilton (University of British Columbia)  
**Year:** 2019  
**Status:** 🟡 Available in D-Wave SDK as "Layout Embedding"

**Summary:** Introduces "layout-awareness" to the embedding process, using spatial position information of both the logical and hardware graphs to guide initial qubit allocation. A graph layout algorithm (e.g., force-directed) positions logical variables, which is then mapped onto the physical hardware layout to seed the MinorMiner heuristic with spatially coherent initial chains. Works well when the problem has a natural spatial/geometric structure, but underperforms on random graphs without inherent layout.

**Key Features:**
- Uses graph layout algorithms (e.g., Fruchterman-Reingold) to compute initial positions
- Best for problems with natural spatial structure
- Available in D-Wave Ocean SDK as `dwave.embedding.layout`

**Papers:**
- Pinilla & Wilton. "Layout-Aware Embedding for Quantum Annealing Processors." ISC 2019. [Springer](https://link.springer.com/chapter/10.1007/978-3-030-20656-7_7)
- Pinilla & Wilton. "Structure-Aware Minor-Embedding for Machine Learning in Quantum Annealing Processors." 2024. [Springer](https://link.springer.com/chapter/10.1007/978-3-031-37966-6_5)  
**GitHub:** [github.com/joseppinilla/embedding-methods](https://github.com/joseppinilla/embedding-methods)

---

## 6. Spring-Based MinorMiner (SPMM)

**Authors:** Stefan Zbinden, Andreas Bärtschi, Hristo Djidjev, Stephan Eidenbenz (Los Alamos National Lab)  
**Year:** 2020  
**Status:** 🟡 Research — strong for sparse graphs on Pegasus

**Summary:** Similar in spirit to LAMM but with a refined approach. Uses a tuned Fruchterman-Reingold spring algorithm to compute an initial layout for the logical graph nodes mapped onto the hardware, then uses weighted edges to attract chains to good initial positions before invoking MinorMiner for refinement. Outperforms standard MinorMiner on sparse graphs for the Pegasus topology.

**Key Features:**
- Best performer for sparse graphs (edge density < 0.08) on Pegasus
- Uses spring-based force-directed layout for initialization
- Significant improvement over LAMM's consecutive diffusion phase

**Paper:** Zbinden et al. "Embedding Algorithms for Quantum Annealers with Chimera and Pegasus Connection Topologies." ISC High Performance 2020. [Springer](https://link.springer.com/chapter/10.1007/978-3-030-50743-5_10) / [PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC7295343/)  
**Code:** No standalone public repo. The algorithm seeds MinorMiner via its `initial_chains` API.

---

## 7. Clique-Based MinorMiner (CLMM)

**Authors:** Stefan Zbinden, Andreas Bärtschi, Hristo Djidjev, Stephan Eidenbenz (Los Alamos National Lab)  
**Year:** 2020  
**Status:** 🟡 Research — best performer for dense graphs on Pegasus

**Summary:** Uses D-Wave's clique embedding as an initialization step. It first finds a clique embedding for a subset of the logical variables using `find_clique_embedding`, which provides well-structured "L-shaped" initial chains. The remaining unembedded variables are left for MinorMiner to place. This approach dominates on dense graphs for Pegasus topology, where standard MinorMiner fails to embed medium-density graphs that are known to have clique embeddings.

**Key Features:**
- Clear winner for dense graphs (edge density > 0.08) on Pegasus
- Leverages structured clique embedding as initialization
- Together with SPMM, forms a complementary pair covering all density ranges

**Paper:** Same as SPMM — Zbinden et al. "Embedding Algorithms for Quantum Annealers with Chimera and Pegasus Connection Topologies." ISC High Performance 2020. [Springer](https://link.springer.com/chapter/10.1007/978-3-030-50743-5_10)  
**Code:** No standalone repo. Implemented by calling `find_clique_embedding` then `find_embedding` with `initial_chains`.

---

## 8. Integer Programming (IP) for Minor Embedding

**Authors:** David E. Bernal, Kyle E.C. Booth, Raouf Dridi, Hedayat Alghassi, Sridhar Tayur, Davide Venturelli (CMU / NASA QuAIL / USRA)  
**Year:** 2020  
**Status:** 🟡 Research — exact method, impractical for large instances

**Summary:** Formulates minor embedding as an integer program, providing the first exact (non-heuristic) approach. Two formulations are proposed: (1) a direct IP translation from Dridi et al.'s equational formulation, and (2) a decomposition into an assignment master problem with fiber condition-checking subproblems. Crucially, this can detect instance infeasibility and provide optimality bounds — capabilities no heuristic method offers.

**Key Features:**
- Can prove a problem is unembeddable (infeasibility detection)
- Provides bounds on solution quality
- Too slow for routine use but valuable for benchmarking and validation

**Paper:** [arXiv:1912.08314](https://arxiv.org/abs/1912.08314) — published in CPAIOR 2020. [Springer](https://link.springer.com/chapter/10.1007/978-3-030-58942-4_8)  
**Code:** Available from authors upon request.

---

## 9. ATOM (Adaptive TOpology eMbedding)

**Authors:** Hoang M. Ngo, Tamer Kahveci, My T. Thai (University of Florida)  
**Year:** 2023  
**Status:** 🟢 Active research — fastest method available

**Summary:** Introduces the concept of *adaptive topology* — an expandable subgraph of the hardware graph that grows along with the embedding size as needed. Rather than fixing the hardware graph size upfront, ATOM iteratively selects logical nodes and embeds them, expanding the hardware region only when necessary. This decouples runtime from the total hardware graph size, making it dramatically faster.

**Key Features:**
- Up to 20× faster than MinorMiner and 66× faster than OCT-based
- Hardware-size independent — adapts automatically
- Comparable embedding quality (qubit count) to other methods
- Implemented in C++ for Chimera topology

**Paper:** [arXiv:2307.01843](https://arxiv.org/abs/2307.01843) — published in IEEE ICC 2023.  
**Code:** Available from authors. Contact: Hoang M. Ngo (University of Florida).

---

## 10. 4-Clique Network Minor Embedding

**Authors:** Elijah Pelofske (Los Alamos National Lab)  
**Year:** 2024  
**Status:** 🟡 Research — Pegasus-specific technique

**Summary:** Instead of using standard linear-path chains (where qubits form a path), this method constructs chains from connected paths of 4-cliques, exploiting the fact that the Pegasus topology contains many K₄ subgraphs. While 4-clique chains use more qubits, they provide significantly more ferromagnetic couplers per chain, increasing chain integrity and reducing chain breaks. This allows weaker chain coupling strengths, freeing up more of the programmable weight range for the actual problem.

**Key Features:**
- Pegasus-specific (does not work on Chimera, which has max clique size 2)
- Trades qubit count for stronger chain coupling
- Reduces chain breaks and improves solution quality
- Uses minorminer on the contracted 4-clique network graph

**Paper:** Pelofske. "4-Clique Network Minor Embedding for Quantum Annealers." *Phys. Rev. Applied* 21, 034023 (2024). [APS](https://link.aps.org/doi/10.1103/PhysRevApplied.21.034023) / [arXiv:2301.08807](https://arxiv.org/abs/2301.08807)  
**Code:** Described algorithmically; uses minorminer as a subroutine on the contracted graph.

---

## 11. CHARME (Chain-Based Reinforcement Learning)

**Authors:** Hoang M. Ngo, Nguyen H K. Do, Minh N. Vu, Tre' R. Jeter, Tamer Kahveci, My T. Thai  
**Year:** 2024  
**Status:** 🟢 Active research — RL-based, state-of-the-art quality for sparse graphs

**Summary:** The first major reinforcement learning approach to minor embedding. CHARME uses a Graph Neural Network (GNN) for policy modeling, a state transition algorithm that guarantees valid embeddings, and an order exploration strategy for efficient training. It treats embedding as a sequential decision-making problem — the RL agent decides the order in which logical nodes are embedded and where to place chains. Outperforms MinorMiner and ATOM on qubit usage for sparse graphs.

**Key Features:**
- GNN-based policy learns structural features
- Guarantees valid embeddings via state transition algorithm
- Best qubit efficiency for sparse logical graphs among fast methods
- Runtime comparable to ATOM (fastest methods)

**Paper:** [arXiv:2406.07124](https://arxiv.org/abs/2406.07124) — published in *ACM Transactions on Quantum Computing*, 2025. [ACM](https://dl.acm.org/doi/10.1145/3763244)  
**Code:** Contact authors (University of Florida). Built on top of ATOM's framework.

---

## 12. PPO-Based RL Embedding (Nembrini et al.)

**Authors:** Riccardo Nembrini et al.  
**Year:** 2025  
**Status:** 🟡 Early research — proof-of-concept

**Summary:** An independent RL approach using Proximal Policy Optimization (PPO). Treats minor embedding as a sequential decision-making problem where an agent iteratively maps problem variables to hardware qubits. Tested on both fully-connected and random problem graphs for Chimera and Zephyr topologies. Produces valid embeddings consistently, especially on the more modern Zephyr topology, though with less efficient qubit usage than dedicated heuristics.

**Key Features:**
- Topology-agnostic RL framework
- Scales to moderate problem sizes
- Particularly effective on Zephyr topology

**Paper:** [arXiv:2507.16004](https://arxiv.org/abs/2507.16004) — July 2025.  
**Code:** Not yet publicly available.

---

## 13. Choi's Foundational Work

**Authors:** Vicky Choi  
**Year:** 2008 (Part I), 2011 (Part II)  
**Status:** 🔵 Foundational theory

**Summary:** The theoretical foundation for minor embedding in adiabatic quantum computation. Part I addresses the parameter setting problem (choosing chain coupling strengths). Part II introduces the concept of minor-universal graph design — constructing hardware graphs that efficiently support embedding of broad families of input graphs. This work defined the problem space that all subsequent algorithms operate in.

**Papers:**
- Choi. "Minor-embedding in adiabatic quantum computation: I. The parameter setting problem." *Quantum Inf. Process.* 7, 193–209 (2008).
- Choi. "Minor-embedding in adiabatic quantum computation: II. Minor-universal graph design." *Quantum Inf. Process.* 10, 343–353 (2011).

---

## 14. TRIAD Embedding

**Authors:** Vicky Choi  
**Year:** 2008/2011  
**Status:** 🔵 Foundational — superseded by faster methods

**Summary:** The earliest systematic embedding method for Chimera hardware. Embeds arbitrary graphs into Chimera by exploiting the K(L,L) bipartite unit cell structure, using "triangle"-shaped chain patterns. It proves that any graph up to a certain size can be embedded into a given Chimera graph but is somewhat inefficient and constrains the problem to a limiting size. This is the ancestor of the Clique Embedding approach.

**Papers:** Choi (2008, 2011) — see entry #13 above.  
**Code:** Implemented within the OCT-based framework at [TheoryInPractice/aqc-virtual-embedding](https://github.com/TheoryInPractice/aqc-virtual-embedding) as the `triad` and `triad-reduce` algorithms.

---

## 15. Klymko-Sullivan-Humble (KSH) Embedding

**Authors:** Christine Klymko, Blair D. Sullivan, Travis S. Humble (Oak Ridge National Lab)  
**Year:** 2012/2014  
**Status:** 🔵 Foundational — evolved into OCT-based framework

**Summary:** Extended Choi's TRIAD method with an improved complete-graph embedding algorithm for Chimera, plus the first systematic methods for handling hard faults (broken qubits) without approximating the original problem. Scales linearly in time and quadratically in footprint. Showed algorithms are more resilient to faulty hardware than naive approaches. This work directly led to the OCT-based virtual hardware framework (entry #3).

**Paper:** [arXiv:1210.8395](https://arxiv.org/abs/1210.8395) — published in *Quantum Inf. Process.* 13, 709–729 (2014).  
**Code:** Evolved into [TheoryInPractice/aqc-virtual-embedding](https://github.com/TheoryInPractice/aqc-virtual-embedding).

---

## 16. Systematic Cartesian Product Embedding

**Authors:** Arman Zaribafiyan, Dominic J.J. Marchand, Seyed Saeed Changiz Rezaei (1QBit)  
**Year:** 2016/2017  
**Status:** 🟡 Problem-specific — for Cartesian product graphs

**Summary:** A deterministic, systematic method that exploits the structure of Cartesian products of complete graphs (K_m □ K_n), which appear frequently in scheduling, coloring, and constraint satisfaction problems. Decomposes the embedding by first embedding one factor in a repeatable pattern, then placing and connecting copies. Produces scalable embeddings with desirable chain-length distributions. Also addresses faulty qubits.

**Key Features:**
- Deterministic and reproducible
- Scalable to larger processors
- Problem-specific (Cartesian product structure required)

**Paper:** [arXiv:1602.04274](https://arxiv.org/abs/1602.04274) — published in *Quantum Inf. Process.* 16, 136 (2017). [Springer](https://link.springer.com/article/10.1007/s11128-017-1569-z)  
**Code:** No public repository found.

---

## 17. Template-Based Minor Embedding (TEAQC)

**Authors:** Thiago Serra, Teng Huang, Arvind U. Raghunathan, David Bergman (MERL / Bucknell / UConn)  
**Year:** 2019/2022  
**Status:** 🟢 Active — open-source, Chimera-specific

**Summary:** Uses integer linear programming (ILP) to search for embeddings within specific classes of Chimera graph minors called "templates." Rather than embedding into the full hardware graph, the method precomputes structured template minors and then uses ILP to map the problem graph into one of these templates. This combines the optimality guarantees of IP methods with the efficiency of structured embeddings. Can handle broken qubits via a fault-tolerant extension.

**Variants:**
- **Clique Overlap Embedding:** Uses simulated annealing with improved guiding pattern and shifting rule
- **Fault Tolerant Template Embedding:** Extends the ILP formulation for Chimera graphs with faulty qubits

**Paper:** [arXiv:1910.02179](https://arxiv.org/abs/1910.02179) — published in *INFORMS Journal on Computing* 34(1), 427–439, 2022. [INFORMS](https://pubsonline.informs.org/doi/10.1287/ijoc.2021.1065)  
**GitHub:** [github.com/merlresearch/TEAQC](https://github.com/merlresearch/TEAQC) ✅  
**License:** AGPL-3.0

---

## 18. Date-Potok Efficient Embedding

**Authors:** Prasanna Date, Robert Patton, Catherine Schuman, Thomas Potok (Oak Ridge National Lab)  
**Year:** 2019  
**Status:** 🟡 Research

**Summary:** Proposes an efficient embedding algorithm focused on reducing qubit usage and achieving objective function values close to the global minimum. Uses a greedy construction approach tailored for the D-Wave 2000Q, with the explicit goal of making embeddings that improve actual QA solution quality (not just minimizing chain length). Compared against D-Wave's built-in embedding algorithms.

**Paper:** Date et al. "Efficiently embedding QUBO problems on adiabatic quantum computers." *Quantum Inf. Process.* 18(4):117, 2019. [Springer](https://link.springer.com/article/10.1007/s11128-019-2236-3)  
**Code:** No public repository found.

---

## 19. Okada Subproblem Embedding

**Authors:** Shunta Okada, Masayuki Ohzeki, Masayoshi Terabe, Shinichiro Taguchi  
**Year:** 2019  
**Status:** 🟡 Research — decomposition approach

**Summary:** Rather than embedding the entire problem at once, this method embeds larger subproblems iteratively. It selects easily-embeddable logical variables as subproblems and uses Cai's heuristic as a subroutine, then combines partial solutions. This "divide and embed" strategy is particularly useful for problems too large to embed monolithically.

**Paper:** Okada et al. "Improving solutions by embedding larger subproblems in a D-Wave quantum annealer." *Scientific Reports* 9, 2098, 2019. [Nature](https://www.nature.com/articles/s41598-018-38388-4)  
**Code:** No public repository found.

---

## 20. Lobe-Lutz Broken Chimera Embedding (Exact)

**Authors:** Elisabeth Lobe, Annette Lutz (German Aerospace Center / DLR)  
**Year:** 2021  
**Status:** 🟡 Research — exact method for complete graphs on faulty hardware

**Summary:** Formulates embedding of complete graphs into broken (faulty) Chimera graphs as a matching problem with additional linear constraints. While NP-hard in general, the method is fixed-parameter tractable in the number of inaccessible vertices, making it practical for real hardware with a moderate number of faults. Embeds larger complete graphs than previous heuristic approaches on real D-Wave hardware with faulty qubits.

**Paper:** Lobe & Lutz. "Embedding of complete graphs in broken Chimera graphs." *Quantum Inf. Process.* 20, 228 (2021). [Springer](https://link.springer.com/article/10.1007/s11128-021-03168-z)  
**Code:** No public repository found. (Note: same authors also proved minor embedding in broken Chimera/Pegasus/Zephyr is NP-complete in *TCS* 2024.)

---

## 21. Parity Mapping / Scalable Parity Embedding

**Authors:** Various (Lechner, Hauke, Zoller lineage)  
**Year:** 2015–2025  
**Status:** 🟡 Research — alternative paradigm

**Summary:** An entirely different approach that bypasses standard minor embedding. Instead of mapping logical variables to chains, the parity architecture encodes optimization problems by mapping each logical coupling to a physical qubit, with parity constraints enforcing consistency. This produces fixed, modular, scalable embeddings that work for any problem without problem-specific compilation. The trade-off is higher qubit overhead.

**Paper:** Recent extension: "Scalable embedding of parity constraints in quantum annealing hardware." *Phys. Rev. A* 111, 012435 (2025). [APS](https://journals.aps.org/pra/abstract/10.1103/PhysRevA.111.012435)  
**Code:** No general public implementation found.

---

## 22. Optimised Universal Bipartite Embedding

**Authors:** (Multiple groups, 2025)  
**Year:** 2025  
**Status:** 🟡 Recent research

**Summary:** A universal minor-embedding framework specifically for complete bipartite graphs (e.g., RBMs) on Pegasus topology. Exploits the periodic structure of the hardware to produce deterministic embeddings with significantly shorter chains than MinorMiner. Achieves 99.98% reduction in embedding time for large bipartite graphs compared to MinorMiner.

**Paper:** [arXiv:2504.21112](https://arxiv.org/abs/2504.21112) — "Optimised Quantum Embedding: A Universal Minor-Embedding Framework for Large Complete Bipartite Graphs" (2025).  
**Code:** No public repository found.

---

## Quick Comparison Table

| # | Algorithm | Year | Approach | Speed | Quality | Best For | Public Code |
|---|-----------|------|----------|-------|---------|----------|-------------|
| 1 | MinorMiner (CMR) | 2014 | Iterative heuristic | Medium | Good | General purpose | ✅ pip install |
| 2 | Clique Embedding | 2016 | Deterministic, structural | Fast | Optimal for cliques | Fully-connected problems | ✅ pip install |
| 3 | OCT-Based | 2018 | Top-down, graph decomposition | Slow | Excellent | Quality-critical applications | ✅ GitHub |
| 4 | PSSA | 2018/2020 | Simulated annealing | Medium | Very good | King's graph / CMOS hardware | ❌ |
| 5 | LAMM | 2019 | Layout-guided heuristic | Medium | Moderate | Spatially-structured problems | ✅ GitHub |
| 6 | SPMM | 2020 | Spring-layout initialization | Medium | Good | Sparse graphs on Pegasus | ❌ (uses minorminer API) |
| 7 | CLMM | 2020 | Clique-seeded initialization | Medium | Very good | Dense graphs on Pegasus | ❌ (uses minorminer API) |
| 8 | IP Methods | 2020 | Integer programming | Very slow | Optimal | Proving infeasibility / benchmarking | 📧 By request |
| 9 | ATOM | 2023 | Adaptive topology heuristic | Very fast | Good | Large-scale, time-sensitive | 📧 By request |
| 10 | 4-Clique Network | 2024 | Topology-specific chain design | Medium | Good (quality) | Pegasus hardware | ❌ (uses minorminer) |
| 11 | CHARME | 2024 | Reinforcement learning (GNN) | Fast | Very good | Sparse graphs | 📧 By request |
| 12 | PPO-RL | 2025 | Reinforcement learning (PPO) | Medium | Moderate | Zephyr topology | ❌ |
| 13 | Choi (theory) | 2008 | Foundational theory | N/A | N/A | Theoretical framework | N/A |
| 14 | TRIAD | 2008 | Structured unit-cell | Fast | Moderate | Baseline / small problems | ✅ (in OCT repo) |
| 15 | KSH | 2014 | Fault-tolerant clique | Medium | Good | Hardware with faults | ✅ (in OCT repo) |
| 16 | Cartesian Product | 2017 | Deterministic structural | Fast | Good | K_m □ K_n graphs | ❌ |
| 17 | TEAQC (Templates) | 2022 | ILP on template minors | Slow | Very good | Chimera, quality-focused | ✅ GitHub |
| 18 | Date-Potok | 2019 | Greedy construction | Fast | Good | Solution quality focus | ❌ |
| 19 | Okada Subproblem | 2019 | Divide & embed | Medium | Good | Problems too large to embed whole | ❌ |
| 20 | Lobe-Lutz (Exact) | 2021 | Matching + constraints | Slow | Optimal for cliques | Broken Chimera hardware | ❌ |
| 21 | Parity Mapping | 2015+ | Alternative paradigm | Fast | Fixed overhead | Universal, any problem | ❌ |
| 22 | Universal Bipartite | 2025 | Deterministic structural | Very fast | Excellent | Complete bipartite / RBMs | ❌ |

---

## How to Get Started

For most practical applications, the D-Wave Ocean SDK provides everything you need:

```bash
pip install dwave-ocean-sdk
```

```python
import minorminer
import dwave_networkx as dnx

# Generate a Pegasus hardware graph
pegasus = dnx.pegasus_graph(16)

# Your problem graph
import networkx as nx
problem = nx.random_regular_graph(d=5, n=50)

# Standard heuristic embedding (CMR)
embedding = minorminer.find_embedding(problem.edges(), pegasus.edges())

# Clique embedding (for fully-connected problems)
clique_emb = minorminer.find_clique_embedding(30, pegasus)
```

For research on alternative algorithms, the OCT-based framework at [TheoryInPractice/aqc-virtual-embedding](https://github.com/TheoryInPractice/aqc-virtual-embedding) provides the most complete open-source alternative. For SPMM/CLMM, you can replicate them by using `find_clique_embedding` or spring layout algorithms to generate `initial_chains` passed to `find_embedding`.