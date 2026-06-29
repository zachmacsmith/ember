# Candidate minor-embedding algorithms (CLAUDE.md §3.1–3.4)

After PathFinder (§3.5; see `docs/pathfinder.md` and the paper in `docs/paper/`),
we explored the other four candidate algorithms from the research brief, each
implemented against the existing `EmbeddingAlgorithm` interface, reusing the
shared `embedding_backend.py`, and **evaluated the same way as PathFinder** —
Ember's `benchmark_one` harness, paired against `minorminer` (MM), on
Erdős–Rényi sources into clean Pegasus P6, broken Pegasus P6 (5% faults), and
Zephyr Z4. Each has its own writeup; this file is the cross-cutting summary.

| § | algorithm | module / registry name | writeup |
|---|-----------|------------------------|---------|
| 3.1 | Semi-relaxed **Gromov–Wasserstein** placement (POT) | `srgw.py` / `srgw` | [srgw.md](srgw.md) |
| 3.2 | **Differentiable** annealed soft-assignment (torch) | `diffembed.py` / `diff-softassign` | [diff-softassign.md](diff-softassign.md) |
| 3.3 | **Multilevel V-cycle** (coarsen→embed→refine) | `multilevel.py` / `multilevel` | [multilevel.md](multilevel.md) |
| 3.4 | **LNS + exact CP-SAT repair** (OR-Tools) | `lns_cpsat.py` / `lns-cpsat` | [lns-cpsat.md](lns-cpsat.md) |

## Results (verified from the committed CSVs)

8 cells × 3 seeds, vs `minorminer`. **ACL Δ** = grid-average `(cand−MM)/MM` mean
chain length (negative = shorter, better). **≤MM / win** = cells where the
candidate's mean ACL is not-worse / strictly-better. **std-wins** = cells with
lower cross-seed ACL std (the variance axis). All four are valid and **100%
success** on every cell.

| algorithm | ACL Δ (avg) | ≤MM | strict win | std-wins | time ×MM | headline |
|-----------|------------:|----:|-----------:|---------:|---------:|----------|
| `lns-cpsat`       | **−1.6%** | 8/8 | 7/8 | 4/8 | 15.9× | modest **mean-ACL win**, never-worse, exact repair, slow |
| `multilevel`      | −2.3%¹ | 7/8 | 7/8 | 6/8 | 1.3× | **variance win** (robust); mean-ACL edge is seed-fragile |
| `srgw`            | −0.1% | 5/8 | 2/8 | 6/8 | 3.4× | ACL ≈ tie, **variance win** from deterministic placement |
| `diff-softassign` | +0.0% | 8/8 | 0/8 | 0/8 | 2.4× | **negative result**: returns MM's embedding + overhead |

¹ The committed 3-seed grid shows multilevel at −2.3% mean ACL, but the agent's
own 5-seed ablation found the mean-ACL edge **shrinks to ~a tie** with more
seeds; the *robust, attributable* multilevel win is the **variance** reduction
(a cold-MM control does not reproduce it). Reported honestly here.

## What we learned

A clear theme runs through 3.1–3.3: **they optimize placement, but a valid
embedding needs connectivity/coverage that only the router/repair supplies.** So
each ends up routed or legalized by minorminer and lands at *MM-level mean ACL*,
banking (at most) a **variance** win from a more consistent global placement:

- **`srgw` (3.1)** — solves annealed entropic semi-relaxed GW (POT) for a global,
  deterministic qubit→vertex placement, then seeds MM. GW gives *correspondence,
  not connectivity* (we confirmed a pure round→grow→repair pipeline produces
  edge-invalid embeddings), so it is placement-only. Result: ACL tied, **std −28%
  avg / −40% on clean Pegasus** (up to 5.9× lower on a dense cell). Its predicted
  benefit, and only that.
- **`diff-softassign` (3.2)** — torch soft-assignment matrix with edge-reward +
  Laplacian-Dirichlet contiguity + load terms, τ-annealed. The continuation works
  (loss ↓, rounded ACL 18.6→9.2 as τ→0; init dominates: MM 2.25 ≪ spectral 5.35 ≪
  random 9.20) but the relaxation **cannot beat its MM warm-start** — repair
  inflates chains back to MM, so it returns MM's embedding plus optimization
  overhead. A clean **negative** that confirms the brief's risk ("contiguity is
  soft → repair matters; init matters").
- **`multilevel` (3.3)** — heavy-edge coarsening (2–4 levels) → multi-restart MM
  at the coarsest → a novel **chain-splitting interpolation operator** (graph-
  Voronoi split) on uncoarsening + FM rebalance; the dense finest level is
  legalized by MM warm-started from the projected layout. Robust **variance** win
  (6/8 cells, attributable to the multilevel structure, not the trim pass); the
  mean-ACL win is not seed-robust; no demonstrated advantage at larger scale.
- **`lns-cpsat` (3.4)** — the exception that **modestly beats MM on mean ACL**.
  Starts from MM, then repeatedly destroys a block (single vertex by default —
  cluster moves added zero gain in ablation) and **repairs it to optimality with
  a full connectivity-constrained CP-SAT model** (Bernal et al. 2020 IP,
  single-commodity flow for connectedness, boundary edges pinned). Exact
  single-vertex repair = pruning the spurs MM's union-of-shortest-paths leaves
  behind: **−1.6% ACL grid-avg (−2…−2.9% on density ≥ 0.5, up to −9% on a hard
  n40 d0.7 instance), strictly never-worse than MM**, at ~16× MM wall-clock. It
  edges PathFinder on 2/3 spot-check cells but is ~3× slower; its distinguishing
  property is an optimality certificate per repaired block.

**Bottom line.** None of 3.1–3.4 dominates MM the way `pathfinder-thorough` does
(−3…−8% ACL *and* large variance reduction). Among them: `lns-cpsat` is the only
genuine mean-ACL improver (modest, exact, expensive); `srgw` and `multilevel`
deliver real **variance** reductions cheaply; `diff-softassign` is an instructive
negative. These are exploratory (3 seeds); a higher-seed confirmation of the
`lns-cpsat` ACL win and the `srgw`/`multilevel` variance wins is the natural next
step before any would join PathFinder in a paper.

## Reproduce

Each algorithm is registered, so it runs through the normal harness. To
re-evaluate one against MM on the standard grid:

```bash
.venv/bin/python docs/candidate-algorithms/data/eval_candidate.py <module> <name> [timeout] [--smoke]
# e.g.
.venv/bin/python docs/candidate-algorithms/data/eval_candidate.py lns_cpsat lns-cpsat 120
```

Per-cell CSVs are in `data/<name>_summary.csv` and `data/<name>_raw.csv`.
