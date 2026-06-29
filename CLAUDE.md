# Minor-Embedding Algorithms — Research & Implementation Brief

**Purpose.** This document orients work on *new* minor-embedding algorithms intended to outperform
`minorminer` (MM), the de facto standard, and to be benchmarked inside **Ember / ember-qc** (the
minor-embedding benchmarking framework targeting D-Wave topologies, Pegasus and Zephyr). It captures
five candidate approaches, why each should beat MM, concrete implementation sketches, a build order,
and the evaluation protocol. It is written so an agent can pick up implementation without
re-deriving the design.

**How to use this file.** If the repo has no `CLAUDE.md`, this can serve as it (Claude Code reads
`CLAUDE.md` automatically on launch). If a `CLAUDE.md` already exists, keep this as
`docs/embedding-research.md` and add a one-line pointer to it from `CLAUDE.md`.

---

## 1. Problem and baseline

### 1.1 Minor embedding
Given a **source** (problem) graph `H` and a **target** (hardware) graph `G`, find a model
`φ: V(H) → 2^{V(G)}` (each `φ(v)` is a *chain*) such that:
1. each `φ(v)` induces a **connected** subgraph of `G`;
2. chains are **pairwise disjoint**;
3. every edge `(u,v) ∈ E(H)` has at least one `G`-edge between `φ(u)` and `φ(v)`.

The optimization objective (not just feasibility) is to **minimize qubit usage** — concretely the
**average chain length (ACL)** and total qubit count — and to keep **chain lengths uniform**. ACL
is the metric that correlates most strongly with quantum-annealing solution error.

### 1.2 What `minorminer` does (the thing to beat)
MM is **randomized coordinate descent**:
- Fix a random vertex order. For each vertex, **rip out** its chain and **rebuild** it as the union
  of weighted-shortest-path computations (Dijkstra / multisource A\*) to its already-placed neighbors.
- Overlap is penalized by a **myopic** vertex weight `wt(g) = diam(G)^(# chains currently using g)`,
  recomputed from scratch each pass.
- Iterate until no qubit is shared (valid) or a patience bound (default 10) is hit.

Three structural weaknesses follow directly from this design:
- **Crude inner step:** a chain is a *union of independent shortest paths* — a weak Steiner-tree
  heuristic.
- **Myopic congestion signal:** the overlap weight is a per-pass snapshot with no memory of how
  contested a qubit has been across iterations.
- **Order-dependence + randomization:** high run-to-run variance.

The original MM paper itself names *"better initial placement of vertex-models"* as the key open
problem.

### 1.3 Documented failure modes (targets for improvement)
From the most recent SOTA evaluation (Gómez-Tejedor et al., arXiv:2504.13376), embedding
Erdős–Rényi graphs into broken Pegasus:
- **Variance:** run-to-run ACL can differ by up to ~**4 qubits/chain** on the *same* instance.
- **Density cliff:** MM is beaten by deterministic **Clique Embedding (CE)** once the source's
  average degree exceeds the hardware degree — well below full density.
- **Time:** routinely hits the ~**1000 s** cutoff on large/dense instances.

A new method earns its place by beating MM on **at least one** of {ACL, ACL-variance, success
probability, wall-clock} without regressing the others on a meaningful instance class.

### 1.4 The landscape (so we don't reinvent)
- **Greedy local search, restyled:** layout-aware / spring seeding then MM (Pinilla & Wilton 2019;
  Zbinden et al. 2020 → "Layout Embedding" in Ocean); clique-seeded MM; probabilistic swap-shift
  annealing (Sugie et al. 2018).
- **Exact but unscalable:** integer programming / Benders decomposition (Bernal et al. 2020);
  Gröbner/equational (Dridi et al. 2018).
- **Deterministic templates (special structure):** Clique Embedding (Boothby et al. 2016);
  complete-bipartite templates (Sinno et al. 2025); 4-clique network on contracted *hardware*
  (Pelofske 2024).
- **Learned policies:** GNN-RL (CHARME, Ngo et al. 2024); PPO (Nembrini et al. 2025).

**White space → what's below:** global *continuous* optimization of the assignment, principled
(non-myopic) congestion-aware refinement, and genuine multiscale methods.

---

## 2. Design principles and shared infrastructure

Build the shared scaffolding first; four of the five approaches end in "round → repair," so a strong
shared backend is leverage and makes ablations fair.

### 2.1 Common embedder interface
All embedders return MM-compatible output so they drop into the same harness:

```python
# embedders/base.py
from typing import Protocol
import networkx as nx

Embedding = dict[int, list[int]]  # source node -> list of target (qubit) nodes; same as minorminer

class Embedder(Protocol):
    name: str
    def embed(self, source: nx.Graph, target: nx.Graph, *, seed: int | None = None) -> Embedding | None:
        ...
```

### 2.2 Shared "round → repair" backend
A single module that takes a soft / partial / overlapping assignment and returns a valid embedding:
- `round_assignment(S | coupling, target) -> partial_chains` (argmax / thresholding per qubit).
- `grow_to_connected(chains, target)` — expand each chain's support to a connected subgraph
  (BFS/Steiner within the qubits tentatively assigned to that vertex).
- `resolve_overlaps(chains, target)` — MM-style rip-up passes over contested qubits only.
- Used by approaches 1, 2, 3, 4. Keep it embedder-agnostic.

### 2.3 Baselines to beat (wrap, don't reimplement)
- `minorminer.find_embedding` (default patience) — primary baseline.
- D-Wave **Clique Embedding** (`minorminer.busclique`) — worst-case / density-cliff baseline.
- **Layout Embedding** (Ocean) — sparse-regime baseline.

### 2.4 Evaluation harness
One function `evaluate(embedding, source, target) -> metrics` returning: validity, total qubits,
ACL (mean + **std**), max chain length, chain-length uniformity (e.g. CV), and wall-clock. Variance
across seeds is a first-class metric, not an afterthought.

---

## 3. The five approaches

Ordered most-novel → safest. Each has a prototype "definition of done" (DoD) = beats or matches MM on
a small instance class in the harness.

### 3.1 Semi-relaxed Gromov–Wasserstein embedding (OT view) — *highest novelty / most paper-worthy*
**Idea.** Minor embedding is a structure-preserving, **many-to-one** soft assignment from qubits to
logical vertices. Gromov–Wasserstein (GW) transport matches two graphs by their *intra-graph*
distances (no shared space needed). Use **semi-relaxed GW (srGW)** — drop the hardware-side marginal
constraint — so multiple qubits can map to one logical vertex; those qubit sets are nascent chains.

**Why it beats MM.** Optimizes a *global* structural objective from the start instead of committing
vertex-by-vertex in a random order → should slash ACL-variance; the structural cost penalizes placing
strongly-coupled logical vertices far apart → directly attacks the density cliff.

**Sketch.**
1. Cost matrices: `C_H`, `C_G` = shortest-path (or effective-resistance) distances within each graph.
   Optionally fused-GW with a node feature (e.g. degree) if helpful.
2. Solve srGW with entropic mirror-descent / proximal point (POT: `ot.gromov`) → soft coupling `π`.
3. Anneal entropic regularization down; sharpen `π`.
4. Round: per logical vertex take its support under `π`; `grow_to_connected`; `resolve_overlaps`.

**Reuse.** POT (`ot.gromov.semirelaxed_gromov_wasserstein`, entropic/fused variants);
`networkx`/`dwave-networkx` for distances. For scale, **low-rank GW** (Scetbon et al. 2022) and
**sliced GW** — full GW is ~O(n²m²) per iter; the sliced/low-rank machinery is the route to large
Pegasus/Zephyr and is itself a novel contribution (a *sliced-GW minor-embedder*).

**Risks.** GW gives *correspondence*, not *connectivity* — the rounding/repair does real work. Test a
connectivity regularizer (penalize coupling mass with disconnected support).

**DoD.** Valid embeddings on ER `n∈{20..60}` into a Pegasus patch with lower ACL-variance than MM at
comparable mean ACL.

### 3.2 Differentiable embedding by annealed soft-assignment
**Idea.** MM's `diam(G)^k` overlap weight is a non-smooth barrier on a load variable. Make the whole
objective smooth and optimize globally by gradient descent + temperature homotopy. Represent the
embedding as a soft matrix `S ∈ R^{|V(G)|×|V(H)|}` (`S[q,v]` = prob. qubit q belongs to chain v),
**row-stochastic** (a qubit ≤ 1 chain; a chain owns many qubits → many-to-one, *not* a permutation).

**Loss = three terms.**
- **Edge satisfaction:** for each `(u,v)∈E(H)`, reward coupling mass on `G`-edges between supports of
  u and v.
- **Contiguity:** `trace(Sᵀ L_G S)` (Dirichlet energy over the hardware Laplacian) so each chain's
  membership varies smoothly across `G` → compact/connected supports → short chains (attacks ACL).
- **Load penalty:** discourage qubits claimed by >1 chain.

Sharpen with a Gumbel-Sinkhorn temperature schedule `τ → 0` (Mena et al. 2018; Cuturi 2019), then
discretize and repair.

**Why it beats MM.** The literal continuous-optimization answer to "this feels guess-and-check":
global, GPU-parallel gradient descent + continuation → lower variance, and the contiguity term
*directly* minimizes chain length.

**Reuse.** PyTorch/JAX autodiff; Sinkhorn layers; spectral preconditioning / init from `L_G`
eigenvectors (or one cheap MM pass).

**Risks.** Contiguity is soft (encourages, not guarantees, connected subgraphs) → repair matters;
non-convex → init matters. Shares the relax→anneal→round→repair skeleton with 3.1; build both on the
shared backend (§2.2) to ablate "structure matching" (GW) vs "explicit embedding objective" (this).

**DoD.** Same instance class as 3.1; demonstrate ACL decreasing as `τ` anneals; beat MM variance.

### 3.3 Multilevel V-cycle (coarsen → embed → refine)
**Idea.** Apply the multilevel paradigm that dominates graph partitioning (METIS). Coarsen the
*problem* graph by repeated heavy-edge matching into a hierarchy `H₀ ⊃ H₁ ⊃ … ⊃ H_k` (coarsest =
tens of vertices). Embed `H_k` with heavy effort (multi-restart MM or the Bernal IP). Uncoarsen: each
super-vertex's chain is a hardware region you already own → split it among its constituents by local
routing inside/around that region, then Fiduccia–Mattheyses-style boundary refinement (move qubits
between adjacent chains to cut ACL / fix overlaps) before descending.

**Why it beats MM.** The principled answer to MM's own stated open problem — coarse decisions are made
where global structure is visible and a single random order barely matters, then refined locally →
lower variance and better behavior on the large/dense instances where MM thrashes and times out.
(Hardware-side contraction exists — Pelofske's 4-clique — but problem-side V-cycles for ME are
unexplored.)

**Reuse.** METIS-style matching (`pymetis`/custom); FM refinement; MM/IP as coarse base solver.

**Risks.** The **chain-splitting interpolation operator** is the crux and has no off-the-shelf version;
tight regions cascade repairs upward. Make matching **hardware-aware** (contract source edges expected
to route cheaply), not purely weight-greedy.

**DoD.** On a mid-size instance, match MM ACL with markedly lower variance and lower wall-clock at
scale.

### 3.4 Matheuristic large-neighborhood search (LNS) with exact repair — *highest expected payoff*
**Idea.** Strongest "satisfaction" framing. Maintain a current embedding (allow invalid/overlapping).
Repeat: **destroy** a structured block — a community/cut in `H`, or the most-congested region in `G` —
freeing those chains + qubits; **repair** that block to optimality with the minor-embedding IP (or a
CP-SAT encoding) *restricted to the freed hardware region*, boundary conditions pinned by surrounding
fixed chains. Accept under simulated-annealing criterion; keep a tabu list of recently destroyed blocks.

**Why it beats MM.** IP/SAT alone is exact but dies past ~tens of vertices; pure local search (MM,
swap-shift) scales but sticks. Restricting the exact solver to a small freed neighborhood makes it
*both* tractable and scalable — the contested tangle MM can never untangle greedily gets solved
optimally in isolation. Anytime + controllable variance (more rounds → tighter ACL), unlike MM's
one-shot patience-bounded runs.

**Reuse.** The Bernal et al. (2020) IP formulation, or **OR-Tools CP-SAT** for the subproblem;
adaptive-LNS schedules; MM for the initial solution.

**Risks.** Defining the restricted subproblem's boundary conditions precisely (which external couplers
must be honored) takes care; tune destroy-size so the IP stays fast. Most engineering-heavy.

**DoD.** Take an instance where MM lands a bad (high-ACL) embedding; show destroy-repair monotonically
reduces ACL below MM's best-of-N.

### 3.5 Negotiated-congestion routing (PathFinder) — *safest, smallest delta from minorminer*
**Idea.** Minor embedding *is* multi-net global routing: each chain is a Steiner tree (a "net")
connecting terminals (qubits adjacent to neighbor chains) while competing for a congested fabric —
the FPGA/VLSI routing problem, where rip-up-and-reroute has been refined for 30 years. Two upgrades:
1. Replace MM's shortest-path-union with a real **Steiner-tree approximation** (primal-dual 2-approx,
   or Mehlhorn 1988) so each chain is built jointly → shorter chains.
2. Replace MM's myopic `diam(G)^k` with **PathFinder negotiated congestion** (McMurchie–Ebeling 1995):
   `cost(q) = (base_q + history_q) · present_q`, where `present_q` scales with current over-users and
   `history_q` **accumulates across iterations** every time q is over-subscribed. A consistent,
   growing price forces chains to negotiate scarce qubits over rounds; provably tends to legal,
   low-congestion routings. Read it as iterating toward a Lagrangian congestion dual rather than MM's
   snapshot.

**Why it beats MM.** Same local-search skeleton, but the congestion signal has *memory* and the inner
Steiner step is better → lower ACL with less thrashing on dense graphs. Smallest change to the existing
`minorminer` codebase → easiest head-to-head; cleanly isolates "is it the congestion signal or the
search structure that hurts MM?"

**Reuse.** `minorminer`'s Dijkstra/A\* core; PathFinder cost update loop; standard Steiner approximations.

**Risks.** History-cost schedule needs tuning (too aggressive → oscillation), but well-understood in
the routing literature.

**DoD.** Drop-in router beats MM ACL mean and variance on dense ER (`density ≥ 0.3`) at equal time
budget.

---

## 4. Suggested build order
1. **§2 scaffolding** — interface, shared round→repair backend, eval harness, baseline wrappers.
2. **3.5 PathFinder** — smallest delta; immediate apples-to-apples; isolates congestion vs structure.
3. **3.4 LNS + exact repair** — targets the documented failure modes head-on; its optimal
   sub-solutions double as a local quality yardstick.
4. **3.1 srGW** and **3.2 differentiable** — the genuine research bets, on the shared backend so they
   ablate against each other (structure matching vs explicit objective). srGW is the most publishable.
5. **3.3 multilevel** — most engineering-uncertain (interpolation operator); do once the backend and
   baselines are mature.

---

## 5. Evaluation protocol (keep comparable to the SOTA eval)
- **Targets:** broken Pegasus (Advantage) and Zephyr (Advantage2) via `dwave-networkx`. Run on graph
  topologies; hardware calls optional/secondary.
- **Source instances:** ER over size × density grids (e.g. `size ∈ {10,…,300}`, `density ∈
  {0.05,…,1.0}`), plus **d-regular**, **Barabási–Albert**, and **k-NN geometric** graphs (the SOTA
  paper's recommended extensions). Multiple seeds per cell.
- **Baselines:** `minorminer` (default patience), Clique Embedding (worst-case), Layout Embedding (sparse).
- **Metrics:** success probability; ACL **mean and std** (variance is the key differentiator vs MM);
  total qubits; max chain length; chain-length uniformity (CV); wall-clock.
- **Headline comparisons** (tie results to the documented MM weaknesses):
  - ACL-variance vs MM (MM spreads up to ~4 qubits/chain).
  - Behavior across the density cliff (where MM loses to CE once source avg-degree > hardware degree).
  - Wall-clock on large/dense (where MM hits ~1000 s).

---

## 6. Suggested repo layout
```
ember/
  embedders/
    base.py              # Embedder protocol, Embedding type
    backend.py           # round_assignment, grow_to_connected, resolve_overlaps
    baseline_mm.py       # wraps minorminer.find_embedding
    baseline_clique.py   # wraps busclique / Clique Embedding
    pathfinder.py        # 3.5
    lns_repair.py        # 3.4 (+ cpsat_subproblem.py)
    srgw.py              # 3.1
    diff_softassign.py   # 3.2
    multilevel.py        # 3.3
  eval/
    harness.py           # evaluate(embedding, source, target) -> metrics
    instances.py         # ER / d-regular / BA / kNN generators
    run_benchmark.py     # size×density grids, seeds, baselines, CSV out
  docs/
    embedding-research.md  # this file (if CLAUDE.md is used for repo conventions)
```

---

## 7. References
- Cai, Macready, Roy (2014). *A practical heuristic for finding graph minors.* arXiv:1406.2741. **(minorminer)**
- Gómez-Tejedor, Osaba, Villar-Rodriguez (2025). *Addressing the Minor-Embedding Problem in QA and Evaluating SOTA Algorithm Performance.* arXiv:2504.13376. **(failure modes / eval design)**
- Boothby, King, Roy (2016). *Fast clique minor generation in chimera qubit connectivity graphs.* QIP 15:495–508. **(Clique Embedding)**
- Boothby, Bunyk, Raymond, Roy (2020). *Next-generation topology of D-Wave quantum processors.* arXiv:2003.00133. **(Pegasus)**
- Boothby, King, Raymond (2021). *Zephyr Topology of D-Wave Quantum Processors.* **(Zephyr)**
- Bernal, Booth, Dridi, Alghassi, Tayur, Venturelli (2020). *Integer programming techniques for minor-embedding in quantum annealers.* CPAIOR 2020; arXiv:1912.08314. **(IP / 3.4 repair)**
- Dridi, Alghassi, Tayur (2018). *A novel algebraic geometry compiling framework for adiabatic quantum computations.* arXiv:1810.01440. **(equational/Gröbner)**
- Pinilla, Wilton (2019). *Layout-aware embedding for quantum annealing processors.* ISC HPC. **(layout-aware)**
- Zbinden, Bärtschi, Djidjev, Eidenbenz (2020). *Embedding algorithms for QA with Chimera and Pegasus topologies.* ISC HPC. **(spring/clique-based)**
- Sugie et al. (2018). *Graph minors from simulated annealing for annealing machines with sparse connectivity.* TPNC. **(PSSA)**
- Goodrich, Sullivan, Humble (2018). *Optimizing adiabatic quantum program compilation using a graph-theoretic framework.* QIP 17. **(virtual hardware / OCT)**
- Pelofske (2024). *4-clique network minor embedding for quantum annealers.* Phys. Rev. Applied 21:034023; arXiv:2301.08807. **(hardware contraction)**
- Sinno, Groß, Chancellor, et al. (2025). *Optimised Quantum Embedding … complete bipartite graphs.* arXiv:2504.21112. **(bipartite template)**
- Ngo, Do, Vu, Kahveci, Thai (2024). *CHARME: A chain-based RL approach for the minor embedding problem.* arXiv:2406.07124. **(GNN-RL)**
- Nembrini, Ferrari Dacrema, Cremonesi (2025). *Minor Embedding for Quantum Annealing with Reinforcement Learning.* arXiv:2507.16004. **(PPO)**
- Xu, Luo, Zha, Carin (2019). *Gromov-Wasserstein Learning for Graph Matching and Node Embedding.* ICML; arXiv:1901.06003. **(GWL / 3.1)**
- Chen et al. (2020). *Graph Optimal Transport for Cross-Domain Alignment.* arXiv:2006.14744. **(graph OT)**
- Vincent-Cuaz, Flamary, Corneli, Vayer, Courty (2022). *Semi-relaxed Gromov-Wasserstein divergence and applications on graphs.* ICLR. **(srGW / 3.1)**
- Vayer, Chapel, Flamary, Tavenard, Courty (2019). *Fused Gromov-Wasserstein distance.* **(FGW option)**
- Scetbon, Peyré, Cuturi (2022). *Linear-time Gromov-Wasserstein via low-rank couplings.* **(scalable GW)**
- Mena, Belanger, Linderman, Snoek (2018). *Learning Latent Permutations with Gumbel-Sinkhorn Networks.* arXiv:1802.08665. **(3.2 sharpening)**
- Cuturi, Teboul, Vert (2019). *Differentiable Ranking and Sorting using Optimal Transport.* NeurIPS. **(differentiable OT)**
- McMurchie, Ebeling (1995). *PathFinder: A Negotiation-Based Performance-Driven Router for FPGAs.* FPGA. **(3.5 negotiated congestion)**
- Karypis, Kumar (1998). *A fast and high quality multilevel scheme for partitioning irregular graphs (METIS).* **(3.3 coarsening)**
- Fiduccia, Mattheyses (1982). *A linear-time heuristic for improving network partitions.* DAC. **(3.3 refinement)**
- Mehlhorn (1988). *A faster approximation algorithm for the Steiner problem in graphs.* IPL. **(3.5 Steiner)**

---
*Tooling note:* core deps likely include `dwave-networkx`, `minorminer`, `networkx`, `POT`,
`torch`/`jax`, `ortools` (CP-SAT), and a partitioner (`pymetis` or custom). Pin versions in the repo.
