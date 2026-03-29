# Quantum Embedding Benchmark Suite: Project Plan

## Project Vision

Build the first standardized, open-source benchmark suite for evaluating minor embedding algorithms against real-world problem QUBO graphs — not just abstract random graphs. Alongside it, develop a novel embedding algorithm inspired by pathfinding approaches, validated on this suite. Establish VQI's quantum software team as a contributor to critical quantum computing infrastructure.

---

## Current Codebase State

The foundation is already built and functional:

- **Graph library:** 93 pre-generated graphs across 7 categories, JSON serialization, ID-based selection system
- **Plugin architecture:** `@register_algorithm` decorator, `EmbeddingAlgorithm` ABC with `embed(source, target, timeout)` interface — any new algorithm is one file
- **Benchmark engine:** Multi-trial runs, per-run metric collection (chain lengths, qubit count, coupler count, wall-clock time), embedding validation (coverage, disjointness, connectivity, edge preservation)
- **Output:** CSV/JSON results, 4 matplotlib report plots
- **Algorithms integrated:** MinorMiner (working), ATOM C++ (timing only, outputs fake embeddings), OCT variants (C++ subprocess), CHARME RL (not yet callable)

### Key Gaps to Close

| Gap | What's needed | Priority |
|-----|--------------|----------|
| Only abstract/random test graphs | Real-problem QUBO graph generators | **Critical** |
| ATOM outputs fake embeddings | Modify C++ to output chain mapping | High |
| No graph characterization metrics | Degree distribution, treewidth estimate, clustering coefficient, community structure | High |
| Basic reporting only | Interactive comparison, per-algorithm drilldown, exportable tables | Medium |
| No warm-up runs | Discard first N trials for timing accuracy | Low |
| No hyperparameter sweep system | Config-driven parameter variation | Medium |
| No memory/resource tracking | Peak memory, CPU utilization | Low |
| Single hardware topology testing | Multi-topology support (Chimera, Pegasus, Zephyr) | High |
| No problem-class metadata | Tag graphs by origin problem type for analysis | High |

---

## Technical Deliverables

### Deliverable 1: Real-Problem QUBO Graph Generator Module

Add a new module (e.g., `problem_generators.py`) that generates QUBO interaction graphs from standard combinatorial optimization problem instances. Each generator should:

1. Accept a problem instance (from a standard library or parameterized)
2. Produce the QUBO formulation
3. Extract the interaction graph (the graph where nodes = QUBO variables, edges = nonzero quadratic terms)
4. Return the graph with full metadata (problem class, instance source, number of logical variables, edge density, known optimal value if available)

**Problem types to implement (in priority order):**

| Problem | Source instances | QUBO density | Why include |
|---------|----------------|--------------|-------------|
| Max-Cut | BiqMac library, Beasley OR-Library | Matches input graph | Trivial formulation, direct validation, canonical benchmark |
| Traveling Salesman (TSP) | TSPLIB (burma14, bayg29, etc.) | Very dense (near-complete) | High industry interest, stresses embedders |
| Job Shop Scheduling (JSP) | OR-Library (ft06, la01-la40) | Sparse, structured | Time-indexed formulation produces regular grid-like graphs |
| Graph Coloring | DIMACS challenge instances | Moderate density | Clean formulation, well-studied |
| Knapsack | Standard parameterized generation | Dense | Simple formulation, good for validation |
| Number Partitioning | Parameterized | Fully connected | Worst-case embedding scenario |
| Portfolio Optimization | Synthetic from real correlation matrices (e.g., S&P sector ETFs) | Fully connected but small | Finance relevance, funding narrative |

**Implementation per problem type:**
- `generate_instance(size, seed)` → raw problem data
- `to_qubo(instance)` → QUBO matrix Q
- `to_interaction_graph(Q)` → NetworkX graph with metadata
- `validate_formulation(instance, Q)` → verify known optimal maps to QUBO ground state for small instances

**Key reference:** Lucas (2014), "Ising formulations of many NP problems" — the Rosetta Stone for all QUBO formulations.

### Deliverable 2: Graph Characterization Module

Add `graph_analysis.py` that computes structural properties of any test graph:

- Number of nodes, edges, density (already have)
- Degree distribution (mean, std, min, max, histogram)
- Clustering coefficient (global and average local)
- Treewidth estimate (upper bound via min-degree heuristic)
- Community structure (modularity, number of communities via Louvain)
- Symmetry / automorphism group size estimate
- Planarity
- Bandwidth
- Whether the graph is bipartite

**Purpose:** This enables the core research question — do real-problem QUBO graphs have systematically different structural properties than random graphs of equivalent size and density? And do those structural differences predict embedding algorithm performance?

### Deliverable 3: Multi-Topology Hardware Support

Extend the benchmark engine to test against multiple hardware topologies:

- **Chimera** C(M, N, L) — D-Wave 2000Q era (already supported)
- **Pegasus** P(M) — D-Wave Advantage (use `dwave_networkx.pegasus_graph`)
- **Zephyr** Z(M) — D-Wave Advantage2 (use `dwave_networkx.zephyr_graph`)
- **Broken graphs** — simulate dead qubits by removing random nodes from ideal topologies

This means `EmbeddingBenchmark.__init__` should accept a list of target topologies and iterate across them, or results should be tagged by topology.

### Deliverable 4: Enhanced Reporting and Leaderboard

**Reporting improvements:**
- Results grouped by problem class, density band, and topology
- Head-to-head algorithm comparison tables
- Statistical significance testing (Wilcoxon signed-rank across trials)
- Pareto frontier plots (time vs. chain quality)
- Exportable LaTeX tables for papers

**Public leaderboard:**
- Static site on GitHub Pages generated from results JSON
- Tables sortable by: problem class, graph density, topology, metric
- Contribution workflow: fork → run benchmarks → submit PR with results JSON → CI validates format → site rebuilds
- Algorithm metadata: name, paper citation, whether it's topology-specific

### Deliverable 5: Novel Embedding Algorithm (Pathfinder-Inspired)

Develop and validate a new minor embedding algorithm. Details are the team's core research contribution and will evolve, but the infrastructure should support:

- Registration via `@register_algorithm` (already supported)
- Hyperparameter variation via `**kwargs`
- Comparison against all registered algorithms on the full benchmark suite
- Analysis of which problem classes and graph structures it excels on

---

## Paper Strategy

### Paper 1: The Benchmark Suite

**Title (working):** "QEBench: A Standardized Benchmark Suite for Minor Embedding Algorithms Using Real-Problem QUBO Graphs"

**Venue targets:** IEEE International Conference on Quantum Computing and Engineering (QCE), or similar

**Core contribution:** The first benchmark suite that evaluates embedding algorithms against QUBO interaction graphs derived from real combinatorial optimization problems, not just random graph families. Includes the open-source tool, the curated instance library, and the graph characterization analysis showing structural differences between real-problem and random graphs.

**Key sections:**
1. Motivation: existing embedding papers benchmark only against random graphs (Erdős-Rényi, BA, d-regular), which don't reflect real workloads
2. Benchmark design: problem generators, instance curation, graph characterization methodology
3. Structural analysis: systematic comparison of real-problem QUBO graph properties vs. random graphs at equivalent size/density — demonstrate they are structurally distinct
4. Baseline results: MinorMiner, Clique Embedding, and any other available algorithms evaluated across the full suite on Chimera, Pegasus, and Zephyr
5. The open-source tool: architecture, extensibility, how to contribute

**This paper can be written as soon as the suite is built and baseline results are collected, independent of your own algorithm.**

### Paper 2: Structural Analysis and Algorithm Performance

**Title (working):** "How Problem Structure Affects Minor Embedding: An Empirical Study Across Combinatorial Optimization Problem Classes"

**Venue targets:** Quantum Information Processing, or Quantum Science and Technology

**Core contribution:** Empirical evidence that embedding algorithm rankings change depending on problem structure. Characterize which graph properties predict embedding quality for different algorithms. Potentially identify "algorithm selection" rules — given a QUBO's structural properties, which embedding algorithm should you use?

**Key sections:**
1. Graph characterization of QUBO interaction graphs across 6-7 problem classes
2. Embedding results across multiple algorithms and topologies
3. Correlation analysis: which structural properties (density, treewidth, clustering, community structure) predict embedding success rate, chain length, qubit overhead?
4. Algorithm selection analysis: can you predict the best embedding algorithm from graph properties alone?
5. Recommendations for practitioners

**This paper requires the suite from Paper 1 to be complete and is the "insight" paper that establishes your team's expertise.**

### Paper 3: The Novel Algorithm

**Title (working):** TBD based on algorithmic approach

**Venue targets:** Quantum Information Processing, Physical Review A, or QCE

**Core contribution:** A new minor embedding algorithm, evaluated on the standardized benchmark suite against all existing algorithms, with analysis of where and why it outperforms.

**Key sections:**
1. Algorithm description and theoretical motivation (pathfinder inspiration)
2. Complexity analysis
3. Evaluation on QEBench (your own suite) — full comparison across problem classes, densities, topologies
4. Analysis of structural conditions where the algorithm excels
5. End-to-end validation: does better embedding actually produce better annealing solutions?

**This paper is strongest because it's validated on an already-published, independently usable benchmark suite, which makes the results credible and reproducible.**

---

## Timeline (February 2026 → Early 2027)

### Phase 1: Foundation (Feb–May 2026) — Alongside VQI CubeSat Foundation Semester

**Focus:** Architecture upgrades and problem generators. Work in bursts when bandwidth allows.

- [ ] Design and implement `problem_generators.py` interface
- [ ] Implement Max-Cut generator (simplest, validates pipeline)
- [ ] Implement TSP generator (from TSPLIB instances)
- [ ] Implement `graph_analysis.py` characterization module
- [ ] Fix ATOM to output real embeddings
- [ ] Add Pegasus and Zephyr topology support
- [ ] Add warm-up runs to benchmark engine
- [ ] Begin pathfinder algorithm prototyping

**Milestone:** Can generate real-problem QUBO graphs, characterize them, and benchmark MinorMiner against them on multiple topologies.

### Phase 2: Build-Out (Summer 2026) — Concentrated Development

**Focus:** Complete the suite, run comprehensive baselines, develop algorithm.

- [ ] Implement remaining problem generators (JSP, Graph Coloring, Knapsack, Number Partitioning, Portfolio Optimization)
- [ ] Validate all QUBO formulations against known optima on small instances
- [ ] Run full baseline benchmarks: all available algorithms × all problem types × all topologies × multiple trials
- [ ] Structural analysis: compare real-problem vs. random graph properties systematically
- [ ] Build enhanced reporting module with LaTeX export
- [ ] Build GitHub Pages leaderboard (static site from results JSON)
- [ ] Iterate on pathfinder algorithm, benchmark continuously against suite
- [ ] Polish README, contribution guidelines, CI for result submission validation
- [ ] **Public release of v0.1** — core suite with 4-5 problem types, baseline results, leaderboard

**Milestone:** Public repo with usable benchmark suite. Draft of Paper 1 underway.

### Phase 3: Research and Publication (Fall 2026) — VQI Scale and Fund Semester

**Focus:** Write papers, refine algorithm, engage community.

- [ ] Submit Paper 1 (benchmark suite) to QCE 2027 or equivalent
- [ ] Run structural analysis experiments for Paper 2
- [ ] Finalize pathfinder algorithm, run comprehensive evaluation
- [ ] Reach out to D-Wave research team with the published suite
- [ ] Incorporate community feedback, update leaderboard
- [ ] Draft Paper 2 (structural analysis)

**Milestone:** Paper 1 submitted. Algorithm competitive with existing methods. D-Wave aware of the project.

### Phase 4: Algorithm Publication (Winter 2026–Spring 2027)

**Focus:** Final algorithm paper, community adoption.

- [ ] Submit Paper 2 (structural analysis)
- [ ] Complete final algorithm evaluation
- [ ] Write and submit Paper 3 (novel algorithm)
- [ ] Suite v1.0 release with full problem library, multiple contributed algorithm results

**Milestone:** Three papers in pipeline. Established benchmark suite with external users.

---

## Team Role Allocation

| Role | Owner | Responsibilities |
|------|-------|-----------------|
| Architecture + Algorithm Lead | Zach | Framework design, plugin interfaces, code quality standards, algorithm development, final review of all code before merge |
| Problem Formulation + Validation | Teammate A | Implement QUBO generators from Lucas (2014), validate against known optima, graph characterization analysis, experiment execution |
| Infrastructure + Reporting | Teammate B | C++ integration fixes (ATOM), enhanced reporting module, leaderboard site, CI setup, documentation |

**Zach's specific ownership:** Interface design for `problem_generators.py` and `graph_analysis.py` (sets the standard others implement against), all pathfinder algorithm development, architectural decisions, final polish pass before any public release.

---

## Risk Mitigation

| Risk | Mitigation |
|------|-----------|
| QUBO formulations have subtle bugs | Validate every generator against brute-force optimal for small instances (n ≤ 15). Cross-reference with Lucas (2014) and original application papers. |
| Algorithm doesn't outperform existing methods | Paper 1 and Paper 2 are valuable independent of your own algorithm. The suite is the contribution. Algorithm results are bonus. |
| D-Wave not interested | The suite has value to the broader quantum annealing community regardless. Target academic users first. |
| Scope creep delays release | Define v0.1 as 3-4 problem types + MinorMiner baseline only. Ship that, then iterate. |
| Bandwidth conflict with CubeSat | This project is burst-compatible. Set monthly milestones, not weekly ones. CubeSat always takes priority. |
| Teammate execution quality | Zach defines interfaces and code standards first. Teammates implement against clear specs. Zach reviews before merge. |

---

## Why This Matters

No standardized benchmark exists for minor embedding algorithms using real-world problem structures. Every paper in the field motivates with real applications, then benchmarks on random graphs. This suite fills that gap. For VQI, it establishes the quantum software team as a contributor to foundational quantum computing infrastructure — complementing the CubeSat hardware effort and strengthening the case for funding and partnerships.



## Is annealing growing?

Yes, meaningfully. D-Wave reported a **314% year-over-year increase** in usage of its Advantage2 annealing systems, and usage of their Stride hybrid solver increased 114% in just six months. ([The Quantum Insider](https://thequantuminsider.com/2026/01/27/d-wave-advancements-annealing-gate-model-dual-platform/)) Revenue is up 235% through the first nine months of 2025, and they've crossed 100 revenue-generating customers. ([The Motley Fool](https://www.fool.com/investing/2025/12/22/wall-street-analysts-quantum-computing-stock/)) D-Wave also acquired Quantum Circuits for $550 million in January 2026 to add gate-model capability ([D-Wave Quantum](https://www.dwavequantum.com/company/newsroom/press-release/d-wave-to-acquire-quantum-circuits/)), which signals they're doubling down, not winding down. The quantum annealing equipment market is projected to grow from about **$1.2 billion to $4.4 billion by 2035**. ([Precedence Research](https://www.precedenceresearch.com/press-release/quantum-annealing-equipment-market)) This isn't hype — real companies are paying real money to use these machines for logistics, finance, defense, and manufacturing.

## Is embedding the bottleneck?

This is where the instinct is very well supported by the literature.

A comprehensive review published just weeks ago states it plainly: *"This embedding bottleneck represents arguably the most significant barrier to practical quantum annealing scalability."* The review notes that *"a 5,000 physical qubit device typically supports only 400–800 logical variables after embedding"* — meaning **embedding overhead consumes 80–92% of the hardware's raw capacity**. ([arXiv — Quantum Annealing for Combinatorial Optimization: Foundations, Architectures, Benchmarks, and Emerging Directions](https://arxiv.org/html/2602.03101v1))

A separate recent study reaches the same conclusion from a different angle: *"The primary bottleneck to scaling quantum annealing lies not simply in the number of qubits, but in the overhead associated with embedding and encoding problems onto the quantum hardware. Minor embeddings typically require between 5 and 12 physical qubits to represent a single logical variable."* ([Quantum Zeitgeist](https://quantumzeitgeist.com/quantum-annealing-tackles-complex-problems-previously/))

The RL-based embedding paper from July 2025 frames it similarly: minor embedding *"often acts as a computational bottleneck, requiring a time that exceeds by orders of magnitude the actual quantum annealing process."* ([arXiv — Minor Embedding for Quantum Annealing with Reinforcement Learning](https://arxiv.org/abs/2507.16004))

And the Pusan National University noise modeling work established experimentally that embedding overhead is a significant bottleneck, and there's a **direct connection between embedding chain length and hardware noise reliability**. ([Quantum Zeitgeist](https://quantumzeitgeist.com/quantum-systems-annealing-noise-modeling-connects-embedding-chain-length-reliability/))

The TECNALIA group's April 2025 paper, which is the most thorough recent evaluation of embedding algorithms, found that there's a *"clear correlation between the average chain length of embeddings and the relative errors of the solutions sampled,"* underscoring *"the critical influence of embedding quality on quantum annealing performance."* ([arXiv — Addressing the Minor-Embedding Problem in Quantum Annealing](https://arxiv.org/abs/2504.13376))