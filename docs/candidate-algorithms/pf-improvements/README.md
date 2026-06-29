# PathFinder optimization pass

After PathFinder shipped, we ran a structured pass of 8 candidate improvements
(3 quality, 5 speed), each implemented as an **isolated variant** (a
`PathFinderRouter` subclass changing exactly one thing) and measured against the
**frozen baseline** `pathfinder` with the shared `data/eval_variant.py` harness
(7-cell ER grid into clean Pegasus P6, broken P6, Zephyr Z4; 3 seeds; baseline
and variant run back-to-back per cell so time ratios are robust to CPU
contention). The verified winners were then composed and **baked into
production**.

## Results (verified from `data/*_variant_summary.csv`)

vs the frozen baseline `pathfinder` (= today's `pathfinder-base`). ACL Δ negative =
shorter; time ratio < 1 = faster. All variants stayed 100% valid + deterministic.

| id | variant | ACL Δ | std Δ | time ×base | outcome |
|----|---------|------:|------:|-----------:|---------|
| **Q3** | spur-pruning post-pass | **−0.7%** | −0.005 | ×1.00 | **baked in** (free quality) |
| **Q1** | placement-stacking (multilevel seed) | **−1.1%** | **−0.048** | ×0.73 | **baked in** as `pathfinder-stacked` |
| Q1′ | placement-stacking (best-of-{mm,ml}) | −2.4% | −0.029 | ×1.91 | noted (best ACL, but 2× time) |
| Q4 | exact Dreyfus–Wagner Steiner | +0.0% | — | ×0.99 | rejected (no gain over SPH) |
| **S3** | bounded region + early termination | **+0.0%** | +0.000 | **×0.33** | **baked in** (3× faster, identical chains, dep-free) |
| **S4** | dirty-set incremental LNS | +0.1% | +0.005 | **×0.74** | **baked in** (fewer re-sweeps, same moves) |
| S1 | numba CSR fast-Dijkstra | +0.0% | +0.000 | ×0.37 | not baked (bit-identical, but adds a numba dep and overlaps with S3) |
| S2 | A\* / landmark routing | **+1.7%** | +0.009 | ×0.28 | rejected (quality regression) |
| S5 | parallel restarts | +0.0%¹ | — | ×0.71¹ | deferred (orthogonal; future) |

¹ S5 is measured vs `pathfinder-thorough`, under contention; a clean re-measure
should approach ×0.25.

## What was baked into production

`pathfinder_opt.py` composes the three quality-safe, compounding winners — **S3
bounded routing + S4 dirty-set LNS + Q3 spur-pruning** — by multiple inheritance
(each overrides a different method) into `_OptimizedRouter`, and registers the
production family on top of the unchanged base engine (`pathfinder.py`):

| algorithm | what | vs `pathfinder-base` |
|-----------|------|----------------------|
| `pathfinder` | optimized (S3+S4+Q3), MM-seeded | **×0.31 (3.2× faster), ACL −0.6%** |
| `pathfinder-stacked` | optimized + multilevel placement (Q1) | ×0.35, **ACL −1.1%, std −0.048** |
| `pathfinder-thorough` | optimized + best-of-4 restarts | lower ACL & variance, more time |
| `pathfinder-cold` | optimized, no MM seed | standalone fallback |
| `pathfinder-base` | the original engine | reference / paper reproducibility |

Net: the production `pathfinder` is **~3× faster than the original at
equal-or-better ACL** (−2.3% vs minorminer), closing most of the wall-clock gap
to C++ minorminer while keeping PathFinder's ACL/variance advantage; the
optimizations are pure-Python (no new hard dependency) and quality-safe
(deterministic, 100% valid).

## Rejected / deferred (honest)

- **A\* routing (S2):** faster but **+1.7% ACL** — the changed root/attach order
  hurts quality; bounded routing (S3) gives a comparable speedup with *zero*
  quality change, so it dominates.
- **Exact Steiner (Q4):** no ACL gain — PathFinder's SPH inner step is already
  near-optimal for the small terminal sets here; representative-terminal
  Dreyfus–Wagner is only a heuristic for the underlying group-Steiner problem.
- **numba fast-Dijkstra (S1):** bit-identical and ~2× faster, but it adds a numba
  dependency and overlaps with bounded routing (both speed up the same step).
  Left available as a future optional accelerator (numba primary, fall back to the
  pure-Python primitive).
- **parallel restarts (S5):** orthogonal speed win for the thorough mode; left as
  future work.

Per-variant agent writeups are in this directory (`spur.md`, `dirtyset.md`,
`fastdijkstra.md`, `stacked.md`, `parallel.md`); the bounded / A\* / exact-Steiner
agents were interrupted before writing theirs, but their modules, CSVs, and the
table above capture the results.

## Reproduce

```bash
.venv/bin/python docs/candidate-algorithms/data/eval_variant.py pathfinder_opt pathfinder pathfinder-base 60
```
