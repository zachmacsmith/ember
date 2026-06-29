# srGW — Semi-relaxed Gromov–Wasserstein placement for minor embedding (§3.1)

Registered algorithm: **`srgw`** (`ember_qc/algorithms/srgw.py`), version `1.0.0`.
Evaluated with `docs/candidate-algorithms/data/eval_candidate.py srgw srgw 90`
(paired vs `minorminer`, full grid). Raw/summary CSVs alongside this file.

---

## 1. Idea & why it might beat MM

Minor embedding is a structure-preserving, **many-to-one** soft assignment from
qubits to logical vertices. Gromov–Wasserstein (GW) optimal transport compares
two graphs by their *intra-graph* distances alone — no shared space needed — so
it directly matches a problem graph `H` to a hardware graph `G`. The
**semi-relaxed** variant (srGW) drops the hardware-side marginal, so the
transport plan `T` (shape `n×m`, `T[i,q]` = mass of logical vertex `i` on qubit
`q`) may map *many* qubits onto one logical vertex — the nascent chains.

The pitch against `minorminer` (MM): MM is randomized coordinate descent over a
**random vertex order**, and the MM paper itself names *"better initial
placement of vertex-models"* as the key open problem. Its documented weakness is
**run-to-run ACL variance** (up to ~4 qubits/chain on the same instance). srGW
optimizes a **global** structural objective and is **fully deterministic** (it
depends only on the two graphs), so it yields one stable placement of every
vertex. Holding that placement fixed should remove MM's dominant variance source
(random order / initial scatter) — attacking exactly the documented weakness —
while the structural cost co-locates strongly-coupled logical vertices, which
should not hurt (and may help) mean ACL.

**The honest catch, which shaped the whole design:** GW yields
**correspondence, not connectivity**. The plan tells you *where* a vertex
belongs, but the per-qubit argmax sets are scattered and do **not** satisfy edge
coverage on their own. I verified this empirically: feeding `T` straight through
the canonical `round_assignment → grow_to_connected → resolve_overlaps` pipeline
produces **invalid** embeddings (e.g. only 40/103 source edges covered, chains
overlapping and sprawling to avg-support 34 qubits). Chain *construction* is a
separate, mature problem. So srGW is used for the one thing it does uniquely
well — **global, deterministic placement** — and a competent router
(`minorminer`) builds the chains from that placement. This isolates srGW's
contribution: *MM from scratch* vs *MM from an srGW placement*.

---

## 2. Background consulted

- **Vincent-Cuaz, Flamary, Corneli, Vayer, Courty — "Semi-relaxed
  Gromov-Wasserstein divergence and applications on graphs" (ICLR 2022,
  arXiv:2110.02753).** The method. Relaxing one marginal gives a divergence that
  is cheaper and well-suited to graph *partitioning* — and partitioning is
  precisely the many-qubits-to-one-vertex structure of a chain assignment.
  Take-away: srGW's free target marginal is the right primitive; its argmax over
  source vertices per qubit is a soft partition of the fabric into chains.
- **Xu, Luo, Zha, Carin — "Gromov-Wasserstein Learning for Graph Matching and
  Node Embedding" (ICML 2019, arXiv:1901.06003).** GW as a graph-matching engine
  and the proximal/entropic gradient machinery. Take-away: entropic
  regularization with a **schedule** (anneal `ε` down) escapes poor local optima
  then sharpens — the homotopy I adopted.
- **POT `ot.gromov` docs / source (v0.9.6).** Verified the exact installed API:
  `entropic_semirelaxed_gromov_wasserstein(C1, C2, p, loss_fun='square_loss',
  epsilon=…, symmetric=…, G0=…, log=…)` returns the **`(ns×nt)`** coupling
  (with `log=True`, `(T, log)`; `log['err']` is the per-iteration error list).
  `C1` = source cost, `C2` = target cost, `p` = source marginal. Empirically:
  the solve is **deterministic** (independent of `random_state` when `G0=None`),
  ~0.08 s per solve on Pegasus P6, and lower `ε` concentrates the plan onto
  fewer qubits (e.g. 680→68 qubits with mass as `ε`: 1.0→0.05).
- **Scetbon, Peyré, Cuturi — "Linear-time GW via low-rank couplings" (2022)**
  and **sliced GW.** Skimmed for scale. Not needed here: full entropic srGW is
  already <0.1 s/solve at these sizes (`m ≤ 680`), so low-rank/sliced machinery
  (the route to much larger fabrics) was left as future work and noted, not
  implemented.

---

## 3. Implementation

**Pipeline (`embed_srgw`):**

1. **Cost matrices.** `C_H`, `C_G` = intra-graph all-pairs shortest-path
   distances, each normalised to `[0,1]`; unreachable pairs (disconnected
   source / faulted hardware) → `max_finite_distance + 1` so srGW sees "far",
   not `inf`. (P6 all-pairs builds in ~0.3 s.)
2. **Annealed entropic srGW.** Solve `entropic_semirelaxed_gromov_wasserstein`
   over an `ε` schedule `(1.0, 0.5, 0.25, 0.1, 0.05)`, warm-starting each step
   from the previous plan `G0=T`. Uniform source marginal `p = 1/n`. The anneal
   checks the deadline between steps and stops early with the current plan.
3. **Placement (`_placement_seeds`).** Each logical vertex, in order of srGW
   confidence (peak transported mass, descending), takes its highest-mass qubit
   not already claimed → a **disjoint, deterministic** one-qubit-per-vertex
   placement `{vertex: [qubit]}`. Partial when the target has fewer qubits than
   the source (MM accepts partial `initial_chains`).
4. **Route.** `minorminer.find_embedding(source, target_edges,
   initial_chains=placement, random_seed=seed)`.
5. **Fallbacks** (so the contract and "never worse than MM" both hold): plain MM
   → pure backend repair (`round_assignment → grow_to_connected →
   resolve_overlaps` on the srGW plan) → failure dict. Every candidate is gated
   by `is_valid_embedding` before return.

**Backend reuse** (`ember_qc.embedding_backend`): `build_adjacency` and
`is_valid_embedding` gate every result; `round_assignment`, `grow_to_connected`,
and `resolve_overlaps` form the last-resort repair path (the canonical §2.2
round→grow→repair, kept as a genuine fallback even though GW correspondence
rarely clears edge coverage on its own).

**Key choices.** *Single-qubit center seeds* beat backend-built connected
"blobs" in testing (blobs were inconsistent: sometimes better mean, sometimes
worse; centers gave a consistent variance win at equal mean). *Determinism* is
intrinsic: srGW depends only on the graphs, so the placement — and hence the
across-seed variance reduction — is real, not a seeding trick. The only
seed-dependence is MM's routing, which is exactly what srGW is trying to
stabilize.

**Scale handling.** `C_G` is 680×680 (P6) / 576×576 (Z4); full entropic srGW is
<0.1 s/solve and the anneal ~0.5 s, plus ~0.3 s for cost matrices → ~1 s
fixed overhead per trial, all deadline-guarded. No target-patch restriction was
needed at these sizes; for much larger fabrics the noted route is low-rank/
sliced GW.

**What was hard / what I learned.** The hard truth is §1's catch: GW gives
correspondence, not connectivity. My first attempts — (a) the pure canonical
pipeline and (b) a self-contained single-pass srGW-affinity Dijkstra router —
both produced invalid or much-worse embeddings (a competent standalone router
would essentially re-derive PathFinder's negotiated rip-up). The design that
*works and stays genuinely srGW* is srGW-for-placement + a mature router, which
also yields the cleanest isolation of srGW's actual contribution.

---

## 4. Results (full grid, 3 seeds/cell, paired vs minorminer)

ACL = average chain length (mean ± population std across seeds). srGW std lower
is **bold**; mean-ACL win (lower) marked `*`.

| cell | succ (mm / srgw) | MM ACL ± std | srGW ACL ± std | ACL Δ | qubits mm/srgw | t(s) mm/srgw |
|---|---|---|---|---|---|---|
| ER n20 d0.3 P6 | 3/3 / 3/3 | 1.800 ± 0.108 | **1.750* ± 0.082** | −2.8% | 36 / 35 | 0.03 / 0.74 |
| ER n20 d0.5 P6 | 3/3 / 3/3 | 2.317 ± 0.131 | 2.317 ± **0.047** | +0.0% | 46.3 / 46.3 | 0.09 / 0.84 |
| ER n20 d0.7 P6 | 3/3 / 3/3 | 2.583 ± 0.062 | 2.600 ± 0.108 | +0.7% | 51.7 / 52 | 0.13 / 0.90 |
| ER n30 d0.3 P6 | 3/3 / 3/3 | 2.711 ± 0.129 | 2.722 ± **0.103** | +0.4% | 81.3 / 81.7 | 0.19 / 1.11 |
| ER n30 d0.5 P6 | 3/3 / 3/3 | 3.356 ± 0.110 | 3.356 ± **0.087** | +0.0% | 100.7 / 100.7 | 0.54 / 1.20 |
| ER n30 d0.7 P6 | 3/3 / 3/3 | 3.911 ± 0.247 | 3.911 ± **0.042** | +0.0% | 117.3 / 117.3 | 0.84 / 1.58 |
| ER n30 d0.5 P6-broken | 3/3 / 3/3 | 3.478 ± 0.087 | **3.322* ± 0.166** | −4.5% | 104.3 / 99.7 | 0.37 / 1.33 |
| ER n30 d0.5 Z4 | 3/3 / 3/3 | 2.744 ± 0.087 | 2.900 ± **0.054** | +5.7% | 82.3 / 87 | 0.29 / 0.84 |

**Aggregates.**
- **Success:** 3/3 in every cell for both — srGW is **never worse** than MM
  (the plain-MM fallback guarantees it).
- **Mean ACL:** essentially identical — grand mean 2.860 (MM) vs 2.860 (srGW).
  srGW wins 2 cells (−2.8%, −4.5%), ties 3, loses 3 (worst +5.7% on Zephyr).
- **ACL variance (the headline axis):** srGW std lower in **6 / 8** cells.
  Average std **0.120 (MM) → 0.086 (srGW), −28%** overall; on **clean Pegasus**
  (6 cells) **0.131 → 0.078, −40%**. Best case, dense `n30 d0.7`: **0.247 →
  0.042, a 5.9× reduction at identical mean ACL**.
- **Wall-clock:** srGW adds ~0.7–1.6 s fixed overhead (cost matrices + anneal)
  vs MM's 0.03–0.84 s. Both are orders of magnitude under the ~1000 s SOTA
  cutoff; srGW is the slower of the two here.

**Does it win on any axis? Yes — ACL variance**, srGW's claimed strength, on
clean Pegasus (−40% avg std, up to 5.9× on the dense cell), at matched mean ACL
and matched success. It ties on mean ACL and success, and loses on wall-clock.

---

## 5. Verdict & limitations (honest)

**Verdict.** A correct, contract-clean srGW embedder that delivers srGW's
*predicted* benefit and nothing more: **MM-equal mean ACL and success, with
materially lower run-to-run ACL variance** on clean Pegasus (−40% avg, 5.9× on
the densest cell). The deterministic global placement does stabilize MM exactly
as the brief hypothesized. It does **not** broadly beat MM on mean ACL, and it
costs ~1 s extra per trial.

**Limitations / honesty.**
- **It is MM-routed.** srGW's genuine, isolated contribution is *placement*; the
  chains are built by `minorminer`, because GW gives correspondence, not
  connectivity (demonstrated, not assumed). So "srgw" is best read as
  *srGW-placement-seeded MM*, and the fair comparison is MM-from-scratch vs
  MM-from-srGW-placement — which is what the table shows.
- **The variance win is mixed off clean Pegasus.** srGW std is *higher* than MM
  on broken P6 (0.166 vs 0.087) and on `n20 d0.7` (0.108 vs 0.062). With only
  3 seeds these std estimates are noisy; the aggregate trend favors srGW, but
  the per-cell picture is not uniform.
- **Zephyr regression.** srGW's placement *raised* mean ACL by 5.7% on Z4 — its
  shortest-path geometry maps onto Zephyr less faithfully than onto Pegasus.
- **Mean ACL is not improved.** The structural objective co-locates neighbors
  enough to match MM, but the per-qubit argmax placement carries no
  connectivity guarantee, so it does not systematically shorten chains.
- **Pure-srGW does not work.** The canonical round→grow→repair pipeline on the
  raw plan is invalid (edge coverage fails); it survives only as a gated
  last-resort fallback.

**If continued:** (i) seed MM with small *connected* srGW regions chosen to
respect source adjacency (promote edge coverage at placement time); (ii) a
fused-GW degree/feature term and a Zephyr-aware cost to fix the Z4 regression;
(iii) low-rank / sliced srGW to scale past P6/Z4; (iv) more seeds to firm up the
variance estimates.
