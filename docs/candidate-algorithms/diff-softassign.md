# Differentiable embedding by annealed soft-assignment (`diff-softassign`)

Candidate algorithm 3.2 from the minor-embedding research brief. Module:
`packages/ember-qc/src/ember_qc/algorithms/diffembed.py`. Registered name:
`diff-softassign`. Pure `torch` (CPU); no GPU or optional deps.

**One-line result.** A correct, contract-respecting implementation that **does
not beat minorminer (MM)**: warm-started from MM it reproduces MM's embedding
*exactly* on every grid cell (ACL delta +0.0 %) while running 2–8× slower;
standalone (no MM seed) it produces *valid but much longer* chains. The
continuous optimization is real and behaves as theory predicts — the τ-annealing
ACL trend is clean — but on Pegasus/Zephyr it cannot out-place MM. This is the
honest negative result the brief explicitly anticipated ("contiguity is soft →
repair matters; init matters").

---

## 1. Idea & why it might beat MM

Represent the embedding as a soft matrix `S ∈ R^{m×(n+1)}` (m = |V(G)| qubit
rows, n = |V(H)| logical columns + 1 "unassigned" column), made **row-stochastic**
by a per-qubit softmax with temperature τ: `S = softmax(Z/τ)`. Each qubit's row
is a distribution over the n chains plus an escape column, so a qubit belongs to
≤ 1 chain while a chain may own many qubits — many-to-one, the opposite of a
permutation. The entire objective is smooth, so it can be optimized *globally* by
gradient descent with a temperature homotopy (τ: 1 → 0), instead of MM's
randomized vertex-by-vertex rip-up-and-rebuild. The loss has three parts:

- **Edge satisfaction** (reward): for each `(u,v) ∈ E(H)`, soft adjacency
  `Σ_{(q,r)∈E(G)} S[q,u]S[r,v] + S[q,v]S[r,u] = Σ S_uᵀ A_G S_v` — maximal when
  adjacent logical vertices sit on *adjacent* qubits.
- **Contiguity** (minimize): the graph-Laplacian Dirichlet energy
  `trace(Sᵀ L_G S) = Σ_{(q,r)∈E(G)} ‖S[q]−S[r]‖²`, a smoothness prior making each
  chain's membership vary slowly across the fabric → compact supports → short chains.
- **Load** (minimize): penalizes a qubit split across > 1 chain; the unassigned
  column lets surplus qubits stay empty rather than be forced into a chain.

**Why it *might* beat MM.** It is the literal continuous-optimization answer to
"this feels guess-and-check": a single global objective optimized by GPU/CPU
gradient descent with continuation should have **lower run-to-run variance** than
MM's order-dependent randomized search, and the contiguity term *directly*
minimizes chain length (the ACL metric that correlates with annealing error).

---

## 2. Background consulted + takeaways

- **Mena, Belanger, Linderman, Snoek, "Learning Latent Permutations with
  Gumbel–Sinkhorn Networks," ICLR 2018** ([arXiv:1802.08665](https://arxiv.org/abs/1802.08665)).
  Learns latent matchings end-to-end by relaxing hard assignments to (doubly)
  stochastic matrices and sharpening them with a temperature τ: as τ → 0 the soft
  matrix approaches a hard assignment, but at very low τ the gradient vanishes —
  hence **anneal** τ rather than fix it small. *Takeaways used:* the
  softmax-with-temperature relaxation and the τ → 0 homotopy. I deliberately
  **drop the stochastic Gumbel perturbation** (it samples assignments) and run a
  deterministic annealed softmax, because the contract requires identical output
  for a fixed seed. I also use a *row*-stochastic softmax, not the doubly
  stochastic Sinkhorn operator: minor embedding is many-to-one (a chain owns many
  qubits), so only the qubit-side marginal should be normalized.

- **Cuturi, Teboul, Vert, "Differentiable Ranking and Sorting using Optimal
  Transport," NeurIPS 2019** ([arXiv:1905.11885](https://arxiv.org/abs/1905.11885)).
  Replaces a non-differentiable combinatorial operator (sort) with an
  entropy-regularized OT proxy solved by Sinkhorn, recovering gradients. *Takeaway
  used:* the general recipe of swapping a hard combinatorial step for a smooth,
  temperature-controlled surrogate and annealing the regularization — the same
  move applied here to the hard qubit→vertex argmax.

- **Graph-Laplacian Dirichlet energy as a smoothness/compactness prior** (graph
  signal processing). The quadratic form `fᵀ L f = Σ_{(i,j)∈E} w_ij (f_i − f_j)²`
  measures how much a signal `f` varies across edges; a smoothness prior
  `∝ exp(−λ fᵀ L f)` prefers signals that change little between adjacent nodes
  (see e.g. [Pang & Cheung 2016, random-walk graph Laplacian smoothness
  prior](https://arxiv.org/abs/1607.01895)). *Takeaway used:* applying this
  column-wise, `trace(Sᵀ L_G S)`, makes each chain's membership a smooth signal on
  the hardware graph, which encourages a compact (low-perimeter), near-connected
  support — exactly the contiguity term. **Key caveat that turned out to be the
  whole story:** this prior *encourages* but does **not guarantee** a connected
  subgraph, so a rounding-and-repair stage must do the real combinatorial work,
  and the quality of the relaxation's *placement* (hence its init) dominates the
  outcome.

---

## 3. Implementation

### Loss (count-normalized so every term is O(1))
```
L(S) = − w_edge · edge_sat + w_cont · contiguity + w_load · load + w_spread · spread
```
with `S_real = S[:, :n]` (the unassigned column excluded), and:

- `edge_sat = ⟨A_H, M / (c⊗c)⟩ / |E_H|`, where `M = S_realᵀ A_G S_real`,
  `c_v = Σ_q S[q,v]` is column mass, and `A_H` is the source adjacency.
- `contiguity = Σ_{(q,r)∈E_G} ‖S_real[q]−S_real[r]‖² / |E_G|` (= `trace(Sᵀ L_G S)`
  on the real columns, computed from the target edge list).
- `load = Σ_q (a_q² − Σ_v S_real[q,v]²) / m`, `a_q = Σ_v S_real[q,v]` (zero iff each
  row is one-hot among real columns).
- `spread = Σ_q a_q / m` (pushes surplus mass to "unassigned").

**The single most important implementation fact.** The raw bilinear edge reward
`Σ S_uᵀ A_G S_v` is *unbounded* and grows with the squared mass a chain claims, so
its unconstrained optimum **piles every chain onto the same dense qubit region**
(the loss ran to −83 and rounding produced ungrowable garbage — invalid at every
τ). No constant weight on the bounded load/spread penalties can offset an
unbounded reward. The fix is to **column-normalize** the edge term by `c_u·c_v`:
spreading or overlapping then yields *no* reward (≈ 0.02/edge for the
spread-over-everything degenerate vs ≈ 1/edge for a concentrated, adjacent
placement), so the optimum genuinely wants adjacent vertices on adjacent qubits.
This was the hardest part to get right.

### Softmax / temperature
`S = softmax(Z/τ, dim=1)`; τ follows a geometric ladder from `tau_start=1.0` to
`tau_end=0.08` over `n_levels=7` levels, `inner_steps=25` Adam steps per level
(`lr=0.03`). Deterministic annealed softmax — no Gumbel noise. Determinism is
secured by seeding torch/numpy/python from `kwargs['seed']`, pinning
`torch.set_num_threads(1)`, and using CPU-stable ops (`index_add`-based
`A_G·S_real`, no `torch.sparse`). The schedule is **iteration-bounded** (not
wall-clock bounded), so output is identical run-to-run regardless of load; the
deadline is only a safety cutoff a well-budgeted run never trips.

### Init (matters enormously — see §4)
- `mm` *(default)*: one quick `minorminer` pass, one-hot into logits, the rest
  pointing at "unassigned", plus small seeded noise.
- `spectral`: low Laplacian eigenvectors of source & target embed both into a
  shared eigenspace; logits seed by proximity (MM-free geometric warm start).
- `random`: small Gaussian logits.

### Backend reuse & the repair that had to be added
Canonical tail per the brief: `round_assignment_matrix` (argmax per qubit, the
unassigned column acting as a learned threshold) → `grow_to_connected` →
`resolve_overlaps`. **This was not enough.** `grow_to_connected` and
`resolve_overlaps` make each chain connected and the set disjoint, but they never
move two *different* chains together, so they fail (return `None`) whenever the
soft placement left two adjacent vertices apart — an **edge-coverage** miss, which
is exactly what soft contiguity cannot prevent. I added a bounded, deterministic
`_stitch_edges` step — invoked only when `resolve_overlaps` returns `None` — that
routes a shortest-path connector for each uncovered source edge using the
backend's own `weighted_multisource_dijkstra` / `reconstruct_path` primitives,
then re-runs `resolve_overlaps`. Coverage is also guaranteed for any logical
vertex that won no qubit by seeding it its most-probable free qubit. The best
*valid* embedding seen across all τ levels (including the MM seed itself) is
returned, so the method is **never worse than its minorminer warm start**.

---

## 4. Results

### Full grid vs minorminer (3 seeds/cell, timeout 90 s; ER → P6 / broken-P6 / Z4)
Reproduce: `.venv/bin/python docs/candidate-algorithms/data/eval_candidate.py
diffembed diff-softassign 90`. Raw/summary CSVs in `data/`.

| cell | MM ACL ± std | MM q | MM t(s) | diff ACL ± std | diff q | diff t(s) | ACL Δ |
|------|-------------:|-----:|--------:|---------------:|-------:|----------:|------:|
| ER n20 d0.3 P6 | 1.800 ± 0.108 | 36.0 | 0.04 | 1.800 ± 0.108 | 36.0 | 0.75 | +0.0 % |
| ER n20 d0.5 P6 | 2.317 ± 0.131 | 46.3 | 0.10 | 2.317 ± 0.131 | 46.3 | 0.34 | +0.0 % |
| ER n20 d0.7 P6 | 2.583 ± 0.062 | 51.7 | 0.13 | 2.583 ± 0.062 | 51.7 | 0.34 | +0.0 % |
| ER n30 d0.3 P6 | 2.711 ± 0.129 | 81.3 | 0.19 | 2.711 ± 0.129 | 81.3 | 0.50 | +0.0 % |
| ER n30 d0.5 P6 | 3.356 ± 0.110 | 100.7 | 0.57 | 3.356 ± 0.110 | 100.7 | 0.83 | +0.0 % |
| ER n30 d0.7 P6 | 3.911 ± 0.247 | 117.3 | 0.83 | 3.911 ± 0.247 | 117.3 | 1.06 | +0.0 % |
| ER n30 d0.5 P6-broken | 3.478 ± 0.087 | 104.3 | 0.39 | 3.478 ± 0.087 | 104.3 | 0.62 | +0.0 % |
| ER n30 d0.5 Z4 | 2.744 ± 0.087 | 82.3 | 0.27 | 2.744 ± 0.087 | 82.3 | 0.57 | +0.0 % |

Success 3/3 for both everywhere. The default (MM-init) returns the *byte-identical*
MM embedding on every seed — so ACL, std, max-chain, and qubit count all match
exactly, and the only difference is wall-clock (diff is 2–8× slower because of the
torch optimization + repair it runs before concluding it cannot beat the seed).
**No axis is won; wall-clock is lost.**

### τ-annealing trend (the requested deliverable)
`init=random`, ER n20 d0.5 → P6, seed 0. ACL is measured by rounding+repairing the
soft `S` at each temperature level. Reproduce: `.venv/bin/python
docs/candidate-algorithms/data/diff_annealing.py`.

| level | τ | loss | valid | ACL after round→repair |
|------:|------:|-------:|:-----:|------:|
| 0 | 1.000 |  1.205 | yes | 18.55 |
| 1 | 0.656 |  0.031 | yes | 18.45 |
| 2 | 0.431 | −0.038 | yes | 17.05 |
| 3 | 0.283 | −0.096 | no  | — |
| 4 | 0.186 | −0.133 | yes | 10.45 |
| 5 | 0.122 | −0.158 | yes |  9.70 |
| 6 | 0.080 | −0.178 | yes |  **9.20** |

As τ anneals toward 0 the loss decreases monotonically and the rounded ACL falls
from **18.55 → 9.20** — the soft assignment sharpens from a diffuse blur (every
qubit fractionally in many chains → huge chains after rounding) toward a crisp,
compact placement. The continuation works exactly as intended; it simply
converges to a placement that is still far worse than MM's 2.25.

### Init ablation (ER n20 d0.5 → P6, seed 0) — init dominates everything
| init | returned ACL | qubits | valid levels | time |
|------|-------------:|-------:|:-----------:|-----:|
| `mm`       | **2.250** (= MM) |  45 | 7/7 | 0.36 s |
| `spectral` | 5.350 | 107 | 7/7 | 0.97 s |
| `random`   | 9.200 | 184 | 6/7 | 1.01 s |

A factor-of-4 ACL gap between MM and random init confirms the non-convex
objective is dominated by its starting point. Without a good combinatorial seed,
the relaxation cannot find a low-ACL basin on these hardware graphs.

---

## 5. Verdict & limitations (honest)

**Verdict.** `diff-softassign` is a correct, deterministic, contract-respecting
implementation that **ties MM exactly with an MM warm start and loses to MM
standalone and on wall-clock**. It does not beat MM on ACL, ACL-variance, success,
or time on any tested cell. Reported plainly as the brief asks: *a correct
implementation that does not beat MM is a valid result.*

**Why it doesn't win — root cause.** The relaxation optimizes *correspondence /
placement*, but a minor embedding needs *connectivity and edge coverage*, which
the smooth objective only encourages. So the rounded soft assignment must be
repaired, and the repair (growing + stitching uncovered edges) **inflates chains
back up** — the soft placement is simply a worse starting routing than MM's, whose
shortest-path chain construction is purpose-built for coverage. Concretely:

- **Soft contiguity ≠ connectivity / coverage.** The Dirichlet prior even
  *prefers singletons* (a single qubit has lower boundary energy than a blob), so
  the relaxation pushes toward a near-permutation that cannot satisfy
  high-degree vertices, and stitching then lengthens chains.
- **Non-convex, init-bound.** A 4× ACL gap between MM and random init (§4) means
  the only way to reach a competitive basin is to start in MM's basin — at which
  point the gradient steps find nothing better and the method is an expensive MM
  pass-through.
- **No variance win.** Because it returns MM's own embedding, its across-seed ACL
  std equals MM's (it does not reduce the variance it was meant to attack).

**What I simplified / would try next.** (a) Deterministic annealed softmax instead
of stochastic Gumbel–Sinkhorn (contract: determinism). (b) The edge-coverage
`_stitch_edges` repair is the load-bearing combinatorial component — a more
embedding-native rounding (e.g. feeding the soft placement as *initial chains* to
a routing pass, or a connectivity-regularized objective that penalizes coupling
mass with disconnected support) is the obvious next lever, but it pushes the
method toward "MM with a learned seed" rather than a standalone differentiable
embedder. (c) The genuinely promising direction the data points to is **variance,
not mean ACL**: a from-scratch differentiable run is deterministic per seed, so an
ablation that decouples the optimizer's seed from MM's could test whether the
continuous objective yields *tighter* ACL across instances — the one axis where a
global method should, in principle, still beat MM.
