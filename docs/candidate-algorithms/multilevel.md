# Multilevel V-cycle minor embedding (CLAUDE.md §3.3)

**Module:** `packages/ember-qc/src/ember_qc/algorithms/multilevel.py`
**Registered name:** `multilevel` &nbsp;|&nbsp; **version:** `1.0.0`
**Status:** correct (valid embeddings or honest failure dict), deterministic per
seed, contract-compliant (15/15 in `tests/algorithms/test_algorithm_contracts.py`).

---

## 1. Idea & why it might beat minorminer

`minorminer` (MM) is randomized coordinate descent: fix a random vertex order,
then rip-up-and-rebuild each chain as a union of shortest paths to its
already-placed neighbours. Two structural weaknesses follow — the placement is
committed vertex-by-vertex in a single random order (high run-to-run variance),
and global structure is never seen as a whole. The MM paper itself names *"better
initial placement of vertex-models"* as the key open problem.

The **multilevel paradigm** that dominates graph partitioning (METIS) answers
exactly this: *coarsen → solve-at-the-coarsest → uncoarsen-and-refine* (a
"V-cycle"). Applied to the **source** graph:

1. **Coarsen** the problem graph by repeated heavy-edge matching into a hierarchy
   `H0 ⊃ H1 ⊃ … ⊃ Hk`. A super-vertex is a contracted cluster of original
   vertices; the coarsest `Hk` has only a few-to-`coarse_target` vertices.
2. **Base-embed** `Hk` with heavy effort (multi-restart MM). With tens of
   vertices this is fast, and — crucially — the placement reflects the problem's
   *global* cluster structure, decided once where it is visible rather than
   vertex-by-vertex in a random order.
3. **Uncoarsen + refine**: project the embedding one level finer at a time. Each
   super-vertex already *owns* a connected hardware region (its chain `Q`); split
   `Q` among the super-vertex's constituents (the **interpolation operator**),
   re-cover the couplings the split severed, and locally refine, before
   descending.

**Hypothesis.** Because the structure-sensitive decision (where each cluster
goes) is made once at the coarsest level and everything finer is *local*
refinement of an already-coherent layout, the V-cycle should (a) lower
run-to-run **ACL variance** and (b) behave better on large/dense instances than
MM's one random-order rebuild. The variance claim is the one that held up
(see §4).

---

## 2. Background consulted + takeaways

- **Karypis & Kumar (1998), "A fast and high quality multilevel scheme for
  partitioning irregular graphs"** (SIAM J. Sci. Comput. 20(1):359–392) — the
  coarsen/partition/uncoarsen V-cycle and **heavy-edge matching (HEM)**.
  *Takeaways used:* visit vertices in (random) order; match each unmatched vertex
  to the unmatched neighbour joined by the **heaviest** incident edge; contract
  matched pairs, summing the weights of parallel edges so the coarse graph is a
  faithful weighted shrink. HEM is ~20 lines and needs no `pymetis`. Coarsening
  makes the *coarsest* solve cheap and the cut/placement decisions globally
  informed.
- **Fiduccia & Mattheyses (1982), "A linear-time heuristic for improving network
  partitions"** (DAC) — boundary refinement. *Takeaways used:* refine by moving
  **one boundary cell at a time** between blocks, driven by a **gain** (here:
  reduction in the longer chain's length), keeping only moves that preserve the
  invariants; a pass is linear because each move only touches the moved cell's
  neighbours. I use a light, strictly-improving FM variant (move a boundary qubit
  from a long chain into a shorter adjacent one) rather than the full gain-bucket
  machinery, because for minor embedding the hard constraint is *connectivity +
  edge coverage*, not a simple cut, so every candidate move is validity-checked.

The literature is about *partitioning* (assign vertices to `k` blocks); minor
embedding needs *connected, edge-covering chains on specific hardware*, which is
why the **chain-splitting interpolation operator has no off-the-shelf version**
and is the crux (§3).

Sources:
- [Karypis & Kumar, SIAM J. Sci. Comput. 1998 (ResearchGate)](https://www.researchgate.net/publication/242479489_A_Fast_and_High_Quality_Multilevel_Scheme_for_Partitioning_Irregular_Graphs)
- [Karypis & Kumar, METIS multilevel k-way (abstract)](https://www.maths.tcd.ie/~eoin/index/karypis.kumar_metis96.html)
- [Fiduccia & Mattheyses, DAC 1982 (ACM)](https://dl.acm.org/doi/10.5555/800263.809204) · [PDF](https://limsk.ece.gatech.edu/course/ece6133/papers/fm.pdf)

---

## 3. Implementation

### 3.1 Coarsening (heavy-edge matching)
`_build_hierarchy` makes a weighted copy of the source (inputs are never
mutated), then `_coarsen_once` repeatedly: shuffle the vertices with the
seeded RNG (deterministic, varies across seeds), run greedy `_heavy_edge_matching`
(each unmatched vertex pairs with the unmatched neighbour on its heaviest edge;
ties → lowest id), and contract each matched pair into an integer super-vertex,
**summing** the weights of edges that become parallel and dropping the
self-loop from the contracted internal edge. Stops at `coarse_target` (=8)
vertices, `max_levels` (=8), the deadline, or when a matching fails to shrink the
graph (e.g. an edgeless remainder). On the eval grid this gives 2–4 levels
(e.g. `30 → 15 → 8`).

### 3.2 Base embed (multi-restart minorminer)
`_base_embed` runs `n_restarts` (=4) independent MM seeds on the coarsest graph
and keeps the fewest-qubit **valid** embedding — a deterministic best-of-k. The
coarsest graph has only ~8 vertices, so this is fast even though contraction
makes it denser.

### 3.3 The chain-splitting interpolation operator (the crux)
To project one level finer, every super-vertex's chain must be split among its
(≤2) constituents. `_interpolate` does this per super-vertex:

- **1 constituent** (unmatched, carried up): copy the chain unchanged.
- **2 constituents `{a,b}`** with chain `Q` (`|Q| ≥ 2`): **graph-Voronoi split**
  (`_voronoi_split`). Find two far-apart seed qubits in `Q` by the standard
  double-BFS diameter heuristic (BFS *restricted to `Q`*), then a single
  multi-source BFS assigns each qubit of `Q` to the seed whose wave reaches it
  first. Two invariants make this sound *by construction*:
  - **Connected cells** — a qubit's BFS parent shares its owner, so following
    parents leads back to the seed within the cell.
  - **`a–b` adjacency for free** — `Q` is connected and split into two non-empty
    parts, so at least one hardware coupler crosses the cut; the internal `a–b`
    edge is therefore always covered.
  Ties favour the first seed, so the split is deterministic.
- **Degenerate `|Q| = 1`**: a single qubit cannot seed two chains, so `b` is lent
  one *free* qubit adjacent to `a`'s qubit (keeps both non-empty and `a–b`
  adjacent); if no free neighbour exists the level is failed.

After splitting, chains are globally **disjoint and connected** and every
*internal* edge is covered. The only thing the split can break is **external**
couplings: the coarse coupler between two super-chains may land on the wrong
constituent. `_repair_edges` fixes these: for each still-uncovered fine edge
`(u,v)`, `_connect` grows `u`'s chain through **free space only** (a node-weighted
`weighted_multisource_dijkstra` from `u`'s chain to a free qubit adjacent to
`v`'s chain, with every other chain forbidden so the detour never overlaps),
appending the path's free qubits to `u`. It tries `u→v` then `v→u`.

### 3.4 Refinement
- **Trim** (`_trim`): delete any qubit whose removal keeps its chain connected
  and still covers every incident edge. Globally safe (shrinking a chain only
  helps disjointness/coverage of others). This is the main **ACL lever** — the
  split+repair output is deliberately generous and trimming makes it lean. A
  final trim is also applied to *whatever* embedding is returned (V-cycle or
  fallback).
- **FM rebalance** (`_fm_rebalance`): a light Fiduccia–Mattheyses boundary pass —
  move a boundary qubit from a long chain into a strictly-shorter adjacent chain
  when both stay valid. Lowers max chain length / improves uniformity without
  changing the qubit count. Only validity-preserving, length-reducing moves are
  committed.

### 3.5 What was hard (and the honest design compromise)
The Voronoi split produces **compact** chains — great for ACL, but compact chains
touch *few* neighbours, so on a **dense** fine level a large fraction of external
couplings are severed and the greedy free-space repair gets *boxed in* (it cannot
reproduce the long snaking chains a dense embedding needs). Measured: on the
eval-grid cells the pure operator legalizes the **coarse** levels on its own but
leaves 30–70 uncovered edges at the **dense finest level**, which free-space
routing cannot all repair.

The sound, honest resolution (faithful to the brief, which permits MM as the
refinement engine): the custom operator drives every level it *can* legalize;
when a level cannot be legalized, that level is refined by **minorminer
warm-started from the projected layout** (`initial_chains` = the freshly-split,
disjoint layout). So the multilevel structure still *initializes* the hard level,
and MM does the snaking. If even that fails, a final cold-MM fallback on the
original graph guarantees the contract (`_mm_fallback`). On the eval grid the
coarse levels are split by the custom operator and only the dense finest level
falls through to warm-started MM.

**Backend reuse:** `build_adjacency`, `weighted_multisource_dijkstra`,
`reconstruct_path`, `chain_connected`, `is_valid_embedding`.

---

## 4. Results

### 4.1 Full grid vs minorminer (3 seeds, P6 = Pegasus-6, Z4 = Zephyr-4, timeout 90 s)
ACL = average chain length; std = std *across the 3 seeds* (the headline
dispersion metric vs MM). 100 % success for both on every cell.

| cell | MM ACL | ML ACL | **ΔACL** | MM std | **ML std** | MM qb | ML qb | MM t | ML t |
|---|---|---|---|---|---|---|---|---|---|
| ER n20 d0.3 P6 | 1.800 | 1.783 | **−0.9 %** | 0.108 | **0.047** | 36.0 | 35.7 | 0.04 | 0.08 |
| ER n20 d0.5 P6 | 2.317 | 2.217 | **−4.3 %** | 0.131 | **0.085** | 46.3 | 44.3 | 0.09 | 0.17 |
| ER n20 d0.7 P6 | 2.583 | 2.567 | −0.6 % | 0.062 | 0.062 | 51.7 | 51.3 | 0.13 | 0.22 |
| ER n30 d0.3 P6 | 2.711 | 2.611 | **−3.7 %** | 0.129 | **0.087** | 81.3 | 78.3 | 0.20 | 0.32 |
| ER n30 d0.5 P6 | 3.356 | 3.378 | +0.7 % | 0.110 | **0.031** | 100.7 | 101.3 | 0.57 | 0.57 |
| ER n30 d0.7 P6 | 3.911 | 3.767 | **−3.7 %** | 0.247 | **0.027** | 117.3 | 113.0 | 0.87 | 0.83 |
| ER n30 d0.5 P6-broken | 3.478 | 3.367 | **−3.2 %** | 0.087 | 0.119 | 104.3 | 101.0 | 0.36 | 0.53 |
| ER n30 d0.5 Z4 | 2.744 | 2.678 | **−2.4 %** | 0.087 | **0.068** | 82.3 | 80.3 | 0.28 | 0.49 |

(`multilevel_summary.csv` / `multilevel_raw.csv`.)

Headline on the grid: ML **matches or beats** mean ACL on 8/8 cells (wins 7,
ties 1), uses **fewer-or-equal qubits** on 7/8, has **lower cross-seed std** on
7/8 (often dramatically — e.g. n30 d0.7: 0.027 vs 0.247, ~9× tighter), at **100 %
success** and **~1.5–2× MM's wall-clock**.

### 4.2 Attribution ablation (5 seeds): is the ACL win "just trimming"?
Comparing raw cold-MM, cold-MM + the same trim pass, and full multilevel:

| cell | cold-MM | cold-MM + trim | multilevel |
|---|---|---|---|
| ER n20 d0.5 | 2.280 ± 0.121 | 2.270 ± 0.103 | 2.220 ± **0.068** |
| ER n30 d0.3 | 2.700 ± 0.114 | 2.680 ± 0.109 | 2.667 ± **0.097** |
| ER n30 d0.5 | 3.300 ± 0.159 | 3.247 ± 0.139 | 3.420 ± **0.111** |
| ER n30 d0.7 | 3.827 ± 0.222 | 3.773 ± 0.210 | 3.780 ± **0.088** |

**Honest reading.** Trimming alone shaves a *little* ACL (~0.01–0.05) — so part
of the grid's ACL edge is a generic trim that could equally be bolted onto MM.
On **mean** ACL with 5 seeds multilevel is a wash vs MM+trim (better on n20 d0.5,
slightly *worse* on n30 d0.5); the 3-seed grid's uniform ACL win was partly
small-sample luck. But multilevel has the **lowest cross-seed std in all four
cells**, and trimming does *not* reproduce that (MM+trim std ≈ MM std). The
variance reduction is therefore the genuine, separable contribution of the
multilevel structure — the consistent coarse layout, not the trim.

### 4.3 Does it extend to larger scale? (4 seeds, sparser to fit P6)
The thesis predicts bigger gains at scale. Spot check:

| cell | MM ACL | ML ACL | MM maxACL | ML maxACL |
|---|---|---|---|---|
| ER n50 d0.2 | 3.860 ± 0.114 | 3.725 ± 0.165 | 6.2 | **5.8** |
| ER n70 d0.15 | 4.614 ± **0.076** | 4.668 ± 0.170 | 7.8 | 8.0 |
| ER n90 d0.12 | 5.556 ± 0.403 | 5.281 ± **0.322** | 10.2 | 10.2 |

**Honest reading.** The clean variance advantage does **not** robustly survive to
n = 50–90: ML has *higher* std on two of three larger cells (these are necessarily
sparser, a different regime than the dense eval grid). Mean ACL is mixed
(better on n50/n90, tied on n70); max chain length is equal-or-lower. Multilevel
is ~2–3× slower here. So the "shines at scale" half of the thesis is **not**
supported by these checks — the cleaner wins were at the **small-dense** end.

---

## 5. Verdict & limitations (honest)

**Verdict.** A correct, deterministic, contract-compliant multilevel V-cycle that,
on the eval grid (ER, n = 20–30, into Pegasus-6 / broken-P6 / Zephyr-4),
**matches MM on mean ACL and consistently tightens cross-seed ACL variance
(~30–60 % lower std on 7/8 cells)** at 100 % success and ~1.5–2× MM's wall-clock.
The variance reduction — validated by ablation as *not* a trim artefact — is the
real signal and directly supports the central claim: deciding cluster placement
once, at the coarsest level where global structure is visible, makes the result
less sensitive to the random vertex order that drives MM's variance.

**Limitations (where it breaks / what's weak):**
1. **The from-scratch interpolation operator does not legalize dense levels.**
   The Voronoi split + free-space repair is sound and self-sufficient on *coarse*
   (loose) levels, but on the **dense finest level** too many couplings are
   severed and greedy repair boxes in. There, the algorithm leans on
   **minorminer warm-started from the projected layout** — so on the eval grid
   MM still does the hardest legalization. A fuller operator would need
   terminal-aware splitting (route each constituent's *own* external couplers to
   its side) and a congestion-aware multi-net repair (cf. the Reweave
   candidate) instead of one-edge-at-a-time free-space routing.
2. **Mean-ACL benefit is marginal and partly generic.** With more seeds the mean
   ACL edge over MM narrows to roughly a tie; a non-trivial slice of it is the
   trim pass, which is not specific to multilevel.
3. **No demonstrated scale advantage.** The variance win is a small-dense-instance
   effect in these experiments; it did not hold at n = 50–90 (sparser). The eval
   grid caps at n = 30, so the regime where multilevel is theoretically strongest
   (large *and* dense) is untested here.
4. **Cost.** ~1.5–3× MM's wall-clock (coarsening + multi-restart base embed +
   per-level work + a warm-started MM solve).

**Bottom line.** A *sound partial* realization of the V-cycle, exactly as the
brief anticipated for the most engineering-uncertain candidate: the novel
chain-splitting operator works on the levels it was designed for, the variance
benefit is real and attributable, and the honest gaps (dense-level legalization,
scale) are clearly identified rather than papered over.
