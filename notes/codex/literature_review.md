# Minor embedding literature review

Date: 2026-09-07. Scope: a bounded primary-source sweep for the Codex research plan, with emphasis on mechanisms that can inform an independently implemented, MM-free and busclique-free Zephyr algorithm. This is a map of relevant prior art, not a completed novelty search or a replication of reported results. No embedding algorithm was implemented or benchmarked for this review.

User clarification: prioritize embedding quality even when slower; the result must be one algorithm, not a sequential or parallel portfolio that selects the best independent result. The mechanisms below are alternatives for scientific investigation or components of one evolving embedding state. They are not a proposal to run separate embedding algorithms and select a winner.

Target clarification: the initial research target is ideal Zephyr Z12. Working-graph and other-architecture observations below concern later validation and prior-art limitations, not an expansion of that initial target.

The reviewed literature provides several useful mechanisms, but no verified evidence here establishes a method that dominates modern MinorMiner on every Ember family on Zephyr. Historical claims against older MM versions, results on expandable hardware, and results on other architectures must not be substituted for the intended experiment.

## Primary sources and verified mechanisms

### 1. Cai–Macready–Roy (CMR), 2014

[A practical heuristic for finding graph minors](https://arxiv.org/html/1406.2741), Jun Cai, William G. Macready, Aidan Roy.

The construction repeatedly replaces one logical vertex's connected hardware model. It computes weighted shortest paths from neighboring models, selects a root using summed distances, and joins paths. Temporary overlap is discouraged by exponentially increasing occupancy costs. The paper also discusses assigning singly used path portions to neighboring models and randomized root choice. Thus variable rerouting, root selection, overlap penalties, and simple transfer of connecting path portions are established prior art.

The current [D-Wave minorminer documentation](https://docs.dwavequantum.com/en/latest/ocean/api_ref_minorminer/source/index.html) identifies `find_embedding` with this heuristic family, and `find_clique_embedding` with separate native-clique work. The implementation has evolved; the 2014 pseudocode is insufficient to characterize the exact baseline. The [author implementation](https://github.com/dwavesystems/minorminer) is Apache-2.0. This permits source study, but the project constraint excludes calling it in candidate construction or refinement.

### 2. Constraint placement and Steiner routing, 2014

[Discrete optimization using quantum annealing on sparse Ising models](https://www.frontiersin.org/journals/physics/articles/10.3389/fphy.2014.00056/full), Zhengbing Bian et al., Sections 2.2.1–2.2.4.

This paper separates placement of local constraints from routing copies of logical variables into connected, disjoint sets. It explicitly describes multicommodity-flow MILP, greedy Steiner-tree approximation, and repeated removal and replacement of routes with occupancy penalties. It considers total qubit use and maximum chain size. The fixed-terminal routing formulation differs from unrestricted minor embedding because contact locations are predetermined by placement. The paper also describes CMR-style shortest-path chains for unrestricted embedding.

Inference: neither “VLSI-inspired routing,” “Steiner trees,” nor “joint disjoint-tree optimization” alone is a credible novelty claim. A stronger distinction would require a specific new neighborhood, movable contact constraints, a new Zephyr representation, or a demonstrably useful algorithmic decomposition. Restricting exact optimization to a small repair region could make these established formulations practical.

### 3. ATOM, 2023

[ATOM: An Efficient Topology Adaptive Algorithm for Minor Embedding in Quantum Computing](https://arxiv.org/html/2307.01843), Hoang M. Ngo, Tamer Kahveci, My T. Thai; IEEE ICC 2023, DOI [10.1109/ICC45041.2023.10279010](https://doi.org/10.1109/ICC45041.2023.10279010).

ATOM maintains a valid partial embedding, adds logical vertices through clean shortest paths, and expands its active Chimera topology when insertion fails. Its insertion procedure can extend existing neighboring chains as well as create the new chain. Initialization embeds a small dense subgraph. The exposition explicitly assumes hardware large enough for the embedding, while experiments also investigate hardware-size limits. The adaptive expansion rule is tied to Chimera coordinates.

Inference: the most transferable ideas are validity-preserving insertion, insertion-order search, and choosing where growth has low total cost. Merely replacing Chimera with a Zephyr graph does not establish the correctness of topology expansion. A native Zephyr implementation should verify every coordinate transformation or avoid transformations entirely. Maintaining validity can reduce repair overhead, but may commit too early and create unnecessarily long chains. ATOM's published claims need a fixed-target, paired-budget replication before comparison with Ember results.

Author code: [Quantum-annealing-minor-embedding](https://github.com/ngominhhoang/Quantum-annealing-minor-embedding), inspected revision `a391f503734805ff0d50288a65b9eaf4ab473de0`. The recursive tree contains `main.cpp`, a notebook, and utilities. GitHub reports no detected license and no license file appeared in that tree. Public visibility alone should not be treated as a reuse license. No complete source-level call-graph audit was performed here.

### 4. CHARME, 2024 preprint / ACM TQC article

[CHARME: A Chain-Based Reinforcement Learning Approach for the Minor Embedding Problem](https://arxiv.org/html/2406.07124v2), Hoang M. Ngo et al.; DOI [10.1145/3763244](https://doi.org/10.1145/3763244).

CHARME chooses the next logical vertex using a GNN policy, while an ATOM-derived deterministic transition constructs the chain and may expand the topology. Order exploration supplies useful action sequences during training. The reported main hardware experiments use Chimera, and synthetic training uses Barabási–Albert graphs; the work also includes real graph data. Its reported inference time is not training cost. The paper's argument for transfer to Pegasus relies on Chimera being a subgraph, which establishes neither optimal use of Pegasus couplers nor competitive Zephyr embeddings.

Inference: order optimization and learning to select vertices are already claimed mechanisms. A learned policy deserves priority only after a deterministic constructor is competitive and order sensitivity is measured. Training solely on one graph distribution would be a weak basis for an all-family claim. A finite hardware limit must remain explicit when interpreting guarantees based on topology expansion.

Author code: [charme-rl-minor-embedding](https://github.com/ngominhhoang/charme-rl-minor-embedding), inspected revision `bb64a171b357d981789eee16654ec02bee13fed7`. No license file appeared in the recursive tree; the repository contains precompiled binaries and copies of CMR/OCT source. The following code paths were inspected, rather than inferred from filenames:

- [`generate_training_data.py`](https://github.com/ngominhhoang/charme-rl-minor-embedding/blob/bb64a171b357d981789eee16654ec02bee13fed7/generate_training_data.py) calls `convert_graph_to_embeddingMinorminer` to build baseline embeddings.
- [`charme/env.py`](https://github.com/ngominhhoang/charme-rl-minor-embedding/blob/bb64a171b357d981789eee16654ec02bee13fed7/charme/env.py) calls that helper during `MinorEmbeddingEnv.__init__` when `mode == 0`; `step` instead invokes an ATOM executable. It also uses a shared output filename and an external order-list file.
- [`train.py`](https://github.com/ngominhhoang/charme-rl-minor-embedding/blob/bb64a171b357d981789eee16654ec02bee13fed7/train.py) selects `mode=0` and displays MM baseline sizes. This confirms MM execution in the supplied training workflow, not that inference itself calls MM or that the policy imitates MM embeddings.

Therefore the supplied workflow is not a drop-in foundation for the strict MM-free candidate path. Separate baseline evaluation from candidate training, initialization, and inference; establish provenance for any reused model or utility. This review did not run the code or establish full runtime correctness.

### 5. PSSA and improved PSSA, 2018–2020

[Minor-embedding heuristics for large-scale annealing processors with sparse hardware graphs of up to 102,400 nodes](https://arxiv.org/html/2004.03819), Yuya Sugie et al.

PSSA keeps disjoint connected placements and optimizes how many logical edges they realize. It swaps whole logical assignments and transfers chain endpoints, accepting some worsening moves through simulated annealing. Initialization subdivides a known complete-graph embedding into nearly equal paths. The improved method adds redundant-qubit deletion and BFS repair, degree-sensitive transfer proposals, and revised schedules. Its main experiments concern King's graphs; prior Chimera experiments are discussed. The main objective is successful embedding size, not minimum ACL.

Inference: ownership swaps, qubit transfers, degree-sensitive allocation, and deletion followed by repair are established ideas. Directly using Ember's PSSA adapter may violate the no-busclique rule if its initializer derives from busclique; that needs a local audit. A novel variant must contribute beyond a different annealing schedule. Search from short, incomplete placements might better match ACL than filling the target graph, but its feasibility behavior is uncertain.

### 6. OCT virtual hardware, 2017–2018

[Optimizing Adiabatic Quantum Program Compilation using a Graph-Theoretic Framework](https://arxiv.org/abs/1704.01996), Timothy D. Goodrich, Travis S. Humble, Blair D. Sullivan.

The work uses a complete-bipartite virtual hardware layer and odd-cycle-transversal decomposition of the logical graph, followed by embedding reduction. It exploits bipartite structure on fault-free Chimera. Its broad technique is structured embedding through a simpler hardware minor rather than unrestricted routing.

Author code: [aqc-virtual-embedding](https://github.com/TheoryInPractice/aqc-virtual-embedding). The inspected [`LICENSE`](https://github.com/TheoryInPractice/aqc-virtual-embedding/blob/master/LICENSE) is BSD 3-Clause even though GitHub's metadata labels it `NOASSERTION`. The repository includes several embedding algorithms, so importing the entire framework does not establish an MM-free path.

Inference: orientation partitioning or a bipartite template is not new by itself. Zephyr-specific contact optimization that uses additional same-orientation couplers could be a substantive extension, but the distinction must be derived and compared with template embedding prior art.

### 7. Template-based integer programming, 2019–2022

[Template-based Minor Embedding for Adiabatic Quantum Optimization](https://arxiv.org/pdf/1910.02179), Thiago Serra, Teng Huang, Arvind Raghunathan, David Bergman; preprint version 2, 2021, subsequently published in INFORMS Journal on Computing.

The paper introduces bipartite and quadripartite Chimera template embeddings and integer programs that assign logical vertices into them. It demonstrates that a minimum-size OCT is not sufficient to decide embeddability in the bipartite template: partition sizes matter. One formulation certifies feasibility or infeasibility within its template, not within all hardware minors. Tests span five random graph classes.

Inference: this is directly relevant to any proposed orientation, biclique, or dense-core construction. Optimize actual physical cost and capacity rather than a proxy such as OCT cardinality. A template failure proves nothing about unrestricted source embeddability. An integrated algorithm could relax its template constraints and continue revising the same embedding state. New Zephyr templates must improve the representational tradeoff rather than merely translate established Chimera templates.

### 8. General integer-programming and decomposition methods, 2019–2020

[Integer programming techniques for minor-embedding in quantum annealers](https://arxiv.org/html/1912.08314), David E. Bernal et al.

The paper formulates minor embedding directly as integer programming and through a master assignment problem with connectivity-checking subproblems. It supports minimizing total assigned qubits and discusses other chain objectives. Exact methods can produce quality bounds and infeasibility certificates. Reported experiments show advantages on some small instances but worse scaling than heuristics when heuristics readily find embeddings.

Inference: a whole-target exact solver is unlikely to be the first competitive implementation. Local exact optimization over several chains is more plausible. The local model must include nonempty connected chains, disjointness, internal logical contacts, and contacts to fixed outside chains. A bound from a restricted neighborhood is local, not a global optimality certificate. Solvers and formulations themselves are prior art; novelty would lie in region selection, movable boundaries, decomposition, or a new effective search strategy.

### 9. Layout and clique initialization followed by MM, 2020

[Embedding Algorithms for Quantum Annealers with Chimera and Pegasus Connection Topologies](https://pmc.ncbi.nlm.nih.gov/articles/PMC7295343/), Stefanie Zbinden, Andreas Bärtschi, Hristo Djidjev, Stephan Eidenbenz; DOI [10.1007/978-3-030-50743-5_10](https://doi.org/10.1007/978-3-030-50743-5_10).

Spring-Based MinorMiner (SPMM) uses source/target layouts for initialization; Clique-Based MinorMiner (CLMM) begins with a clique embedding and then uses MM. The study compares methods on Erdős–Rényi, Barabási–Albert, and regular graphs on Chimera and Pegasus. Its reported winners differ by density.

Inference: these algorithms violate the requested candidate constraint as published. Nevertheless, their density-dependent behavior argues for testing distinct sparse and dense construction mechanisms. Layout alone and clique-then-shortening alone are established prior art. A new independent optimizer may be publishable, but replacing an MM call with a reimplementation of the same update would not establish a new mechanism.

### 10. Native clique construction, 2015–2016

[Fast clique minor generation in Chimera qubit connectivity graphs](https://arxiv.org/abs/1507.04774), Kelly Boothby, Andrew D. King, Aidan Roy.

The paper defines native clique minors with near-minimal, uniform model sizes and gives a polynomial-time search for maximum native clique minors in an induced Chimera subgraph. The contemporary D-Wave package extends native clique utilities to Pegasus and Zephyr.

Inference: an independently coded reproduction of the standard construction would satisfy a literal absence of library calls while still lacking the requested scientific novelty. Structured dense-graph initialization is useful only if the new work clearly improves the construction or its subsequent independent optimization. Excluding the busclique routine does not remove this prior art.

### 11. Cartesian-product constructions, 2016–2017

[Systematic and Deterministic Graph-Minor Embedding for Cartesian Products of Graphs](https://arxiv.org/abs/1602.04274), Arman Zaribafiyan, Dominic J. J. Marchand, Seyed Saeed Changiz Rezaei.

The method exploits a graph product by embedding one factor in a repeatable pattern, then placing and connecting copies. The work focuses on products of complete graphs and discusses inoperable qubits. Its systematic construction targets efficient qubit use and chain distributions.

Inference: repeated motif and graph-product recognition can help structured families, but neither is a novel general idea. A proposed module should document exact graph recognition and a valid extension path, and measure recognition cost. A method specialized to a product class does not imply a gain on all Ember families.

### 12. Reinforcement learning with qubit-level actions, 2025–2026

[Minor Embedding for Quantum Annealing with Reinforcement Learning](https://arxiv.org/html/2507.16004), Riccardo Nembrini, Maurizio Ferrari Dacrema, Paolo Cremonesi; [journal article](https://link.springer.com/article/10.1007/s42484-026-00341-4).

A PPO agent chooses hardware qubits for variables selected by a round-robin rule. This differs from CHARME's vertex-order action. The study includes Zephyr and Chimera; the journal protocol uses cliques of 3–10 vertices and random graphs up to 30 vertices. The paper reports that larger hardware action spaces can greatly inflate qubit use despite successful embeddings.

Inference: this supplies relevant native-Zephyr RL prior art, not evidence that RL beats MM at Ember scale. Feasible embeddings and short embeddings are distinct outcomes. An initial deterministic search project should not assume that adding a neural policy resolves the difficult construction or optimization subproblem.

### 13. Zephyr structure and working graphs

[Zephyr Topology of D-Wave Quantum Processors](https://dwavequantum.com/media/2uznec4s/14-1056a-a_zephyr_topology_of_d-wave_quantum_processors.pdf), Kelly Boothby, Andrew D. King, Jack Raymond, technical report dated 2021-09-22. The search index exposes the report, but direct PDF opening failed during this review; no detailed result from the unavailable body is used here.

The official [Zephyr graph generator documentation](https://docs.dwavequantum.com/en/latest/ocean/api_ref_dnx/generated/dwave_networkx.zephyr_graph.html) defines orientation/offset coordinates and external, odd, and internal edges. The [official topology description](https://support.dwavesys.com/hc/en-us/articles/6820989477911-What-Is-the-Zephyr-Topology) specifies nominal degree 20, comprising sixteen internal, two external, and two odd couplers. D-Wave's [working-graph documentation](https://docs.dwavequantum.com/en/latest/quantum_research/topologies.html) explains that available qubits/couplers can change following calibration.

Inference: algorithms should operate on the actual supplied adjacency, with coordinate structure used as an optimization aid. Hash the full hardware graph. A result on ideal `Z_m` and a result on a defective working graph are different experimental conditions.

### 14. Chain robustness is a different objective

[4-Clique network minor embedding for quantum annealers](https://doi.org/10.1103/physrevapplied.21.034023), Elijah Pelofske, 2024, deliberately spends more qubits on densely connected chains to improve robustness. The paper's Zephyr clique contractions become disconnected, limiting that construction there; its embeddings on contracted Pegasus graphs use MM. This is unsuitable as an ACL-minimizing candidate under the present constraints.

[Minimizing minor embedding energy: an application in quantum annealing](https://arxiv.org/abs/1905.03291), Yan-Long Fang and P. A. Warburton, concerns ferromagnetic chain coupling strengths and preservation of intended states. It is not an algorithm for minimizing chain cardinality.

Inference: lower mean ACL is a clear embedding objective, but it does not by itself prove better QPU solution quality. That second claim would require a separate annealing experiment with controlled chain-strength choices.

## Implications for candidate selection

These are research hypotheses, not discovered performance results or novelty claims. Each includes a preimplementation critique.

| Mechanism worth prioritizing | Proposed differentiating detail | Self-critique | Discriminating experiment |
| --- | --- | --- | --- |
| Joint local optimization of several chains | Reassign contacts and ownership inside native Zephyr regions while preserving a valid outside embedding; include outside contact sets rather than frozen terminal qubits | Existing Steiner/IP routing already optimizes multiple disjoint trees. Regions that are too small cannot escape poor layouts; large regions may time out. Novelty is unproven. | Compare single-chain, two-chain, and region solves with identical initial embeddings and total budgets. Record improvements per second and accepted qubit reductions. |
| Zephyr insertion with explicit future contact capacity | Choose short connected sets using the real local neighbor structure and reserve space for not-yet-realized edges; allow bounded coordinated relocation | This overlaps ATOM and occupancy-aware routing. Capacity scores can become inaccurate surrogates for eventual ACL and hurt dense cases. | Ablate future-contact scoring and relocation separately on sparse, dense, and hub-rich held-out instances. |
| Separator or multilevel construction with flexible interfaces | Embed source regions into hardware regions while jointly choosing a small set of boundary contacts, then refine across region boundaries | Partition/routing ideas are old; Zephyr cuts may lack capacity. Source coarsening may create high-degree vertices whose later expansion is impossible. | Compare measured cut demand with available couplers; track whether refinement erases partition-boundary overhead. Include expander-like graphs as deliberate stress cases. |
| Short incomplete connected placements with contact repair | Optimize missing-edge count jointly with physical size, using swaps and small simultaneous ownership changes without clique-derived initialization | PSSA already covers swaps/transfers and post-search repair. A shorter start can make feasibility much harder. Multiobjective weights may cause endless sacrifice of contacts. | Compare fixed feasibility-first ordering with explicit size caps, using identical wall time and reporting failures alongside ACL. |

The first hypothesis looks most promising for a paper-quality mechanism because it can expose a concrete limitation of single-chain refinement and can be ablated cleanly. It still requires a competitive independent initializer, and the exact joint-routing prior art must be acknowledged. The literature sweep did not establish that no previous work uses this exact neighborhood.

A coherent version could use one joint re-embedding primitive both to insert a pending logical vertex and to improve existing chains. For an initial model, free entire selected chains plus nearby unused qubits, and freeze every unselected chain. The subproblem chooses new connected sets and their contacts to neighboring frozen chains. Freeing an arbitrary spatial window instead can split a selected chain into outside components; those components must be represented explicitly in connectivity constraints. This is a proposed modeling precaution, not an implemented result.

## Measurement consequences

The following are proposed experimental safeguards, derived from the target question rather than performance claims in the papers:

1. For fixed source graph order, minimizing total assigned qubits is exactly minimizing ACL. Compare family-level means with explicitly stated graph weights; a pooled qubit total changes the weighting toward larger graphs.
2. Separate variation across repeated seeds on one graph from variation across different graph instances. Neither is the same as variance of individual chain lengths within one embedding.
3. Include all failures. Reporting ACL only for each algorithm's successful cases can reward the algorithm that fails on difficult graphs. Paired-success ACL is useful but must appear alongside success rates and their overlap.
4. Use paired instances, fixed hardware snapshots, version-pinned MM, and comparable end-to-end budgets. Include topology analysis, initialization, refinement, and selection costs. Report training and amortized inference separately when applicable.
5. Match timing comparisons within each physical compute node; record node identity, thread count, compiler/build, and load. Pool paired effects rather than raw seconds from unlike machines.
6. Hold out graph instances and seeds from tuning. Structure-sensitive moves must use computable properties rather than test-set identity. Best-of-independent-algorithm selection is excluded by the user's single-algorithm requirement, regardless of whether its full cost is counted. Ablation algorithms can still be compared experimentally without becoming candidate components.
7. Some instances have optimal ACL 1, so strict improvement on every instance is mathematically impossible when MM attains that bound. Define the all-family goal as a statistically supported aggregate improvement, allowing optimal ties and retaining success-rate requirements.

Version warning: the public [Ember preprint](https://arxiv.org/abs/2604.25433) describes 24,016 instances and a main comparison on Chimera. The parent repository audit reports a current manifest of 31,149 instances. These are different snapshots; neither corpus count nor published architecture results should be silently transferred into the new Z12 experiment.

## Open items for a deeper novelty review

- Retrieve and inspect the complete Zephyr technical report, including its example embeddings and benchmark conditions.
- Retrieve Yang and Dinneen's 2016 report, *Graph minor embeddings for D-Wave computer architecture*; its existence is confirmed by the [author bibliography](https://www.cs.auckland.ac.nz/~mjd/mjdbib.html), but its mechanisms were not inspected here.
- Inspect Date et al.'s *Efficiently embedding QUBO problems on adiabatic quantum computers*, [ORNL publication record](https://www.ornl.gov/publication/efficiently-embedding-qubo-problems-adiabatic-quantum-computers) and [author manuscript](https://www.osti.gov/servlets/purl/1557505), before claiming novelty for dense graph chain reduction. The record specifies perfect Chimera hardware.
- Inspect the original PSSA paper/contest implementation and exact initialization path in Ember. Distinguish the published algorithm from the repository's architecture adaptation.
- Extend the search to local exact minor models, bounded-treewidth dynamic programming, graph partitioning with terminal constraints, VLSI detailed routing, and fixed-parameter disjoint connected-subgraph problems. Absence of an exact phrase in search results is not absence of prior art.
- Audit source and checkpoint provenance before importing external algorithms. No paper's pseudocode, repository README, or benchmark claim has been treated as a correctness certificate in this review.
