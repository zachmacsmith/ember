# Reweave optimization pass

After Reweave shipped, we ran a structured pass of 8 candidate improvements
(3 quality, 5 speed), each implemented as an **isolated variant** (a
`ReweaveRouter` subclass changing exactly one thing) and measured against the
**frozen baseline** `reweave` with the shared `data/eval_variant.py` harness
(7-cell ER grid into clean Pegasus P6, broken P6, Zephyr Z4; 3 seeds; baseline
and variant run back-to-back per cell so time ratios are robust to CPU
contention). The verified winners were then composed and **baked into
production**.

## Results (verified from `data/*_variant_summary.csv`)

vs the frozen baseline `reweave` (= today's `reweave-base`). ACL Δ negative =
shorter; time ratio < 1 = faster. All variants stayed 100% valid + deterministic.

| id | variant | ACL Δ | std Δ | time ×base | outcome |
|----|---------|------:|------:|-----------:|---------|
| **Q3** | spur-pruning post-pass | **−0.7%** | −0.005 | ×1.00 | **baked in** (free quality) |
| **Q1** | placement-stacking (multilevel seed) | **−1.1%** | **−0.048** | ×0.73 | **baked in** as `reweave-stacked` |
| Q1′ | placement-stacking (best-of-{mm,ml}) | −2.4% | −0.029 | ×1.91 | noted (best ACL, but 2× time) |
| Q4 | exact Dreyfus–Wagner Steiner | +0.0% | — | ×0.99 | rejected (no gain over SPH) |
| **S3** | bounded region + early termination | **+0.0%** | +0.000 | **×0.33** | **baked in** (3× faster, identical chains, dep-free) |
| **S4** | dirty-set incremental LNS | +0.1% | +0.005 | **×0.74** | **baked in** (fewer re-sweeps, same moves) |
| S1 | numba CSR fast-Dijkstra | +0.0% | +0.000 | ×0.37† | not baked (bit-identical, but adds a numba dep and **fully overlaps with S3** — no net gain on the final router; see follow-up below) |
| S2 | A\* / landmark routing | **+1.7%** | +0.009 | ×0.28 | rejected (quality regression) |
| S5 | parallel restarts | +0.0%¹ | — | ×0.71¹ | deferred (orthogonal; future) |

¹ S5 is measured vs `reweave-thorough`, under contention; a clean re-measure
should approach ×0.25.

† S1's ×0.37 is vs the *un-bounded* frozen baseline (= `reweave-base`); the
bounded production router (S3) captures the same Dijkstra speedup by a different
mechanism, so on the final router numba is a wash (see the S1 bullet below).

## What was baked into production

`reweave_opt.py` composes the three quality-safe, compounding winners — **S3
bounded routing + S4 dirty-set LNS + Q3 spur-pruning** — by multiple inheritance
(each overrides a different method) into `_OptimizedRouter`, and registers the
production family on top of the unchanged base engine (`reweave.py`):

| algorithm | what | vs `reweave-base` |
|-----------|------|----------------------|
| `reweave` | optimized (S3+S4+Q3), MM-seeded | **×0.31 (3.2× faster), ACL −0.6%** |
| `reweave-stacked` | optimized + multilevel placement (Q1) | ×0.35, **ACL −1.1%, std −0.048** |
| `reweave-thorough` | optimized + best-of-4 restarts | lower ACL & variance, more time |
| `reweave-cold` | optimized, no MM seed | standalone fallback |
| `reweave-base` | the original engine | reference / paper reproducibility |

Net: the production `reweave` is **~3× faster than the original at
equal-or-better ACL** (−2.3% vs minorminer), closing most of the wall-clock gap
to C++ minorminer while keeping Reweave's ACL/variance advantage; the
optimizations are pure-Python (no new hard dependency) and quality-safe
(deterministic, 100% valid).

## Rejected / deferred (honest)

- **A\* routing (S2):** faster but **+1.7% ACL** — the changed root/attach order
  hurts quality; bounded routing (S3) gives a comparable speedup with *zero*
  quality change, so it dominates.
- **Exact Steiner (Q4):** no ACL gain — Reweave's SPH inner step is already
  near-optimal for the small terminal sets here; representative-terminal
  Dreyfus–Wagner is only a heuristic for the underlying group-Steiner problem.
- **numba fast-Dijkstra (S1):** bit-identical and ~2.7× faster *against the
  un-bounded preliminary engine* — but that gain **fully overlaps with bounded
  routing (S3)**: both accelerate the same Dijkstra step, by compiling it vs. by
  shrinking it. **Re-tested against the final production router** (bounded+dirty-set+spur)
  as a Prompt-10 follow-up (`pf_numba.py`): a numba kernel *restricted to the
  bounded region* (persistent +inf cost array, O(region) setup) is a **wash** —
  within noise of pure-Python `reweave` (n40 d0.7 P6: 1.74 s vs 1.74 s; identical
  ACL; valid; deterministic) — and replacing bounded routing with a *full-graph*
  numba search is **~24% slower**. Profiling attributes **70–84%** of
  optimized-`reweave` runtime to the compiled-C++ `minorminer` base call itself,
  which caps any routing-side speedup (Reweave's wall-clock is ≥ minorminer's
  *by construction* — it runs minorminer then improves). So numba does **not** speed
  up the optimized algorithm; the production router stays pure Python (no numba
  dependency). Kept as the reproducible, un-registered `pf_numba.py` behind the
  paper's fairness finding (§Limitations). A C++ rewrite of the same kernel hits the
  same ceiling.
- **parallel restarts (S5):** orthogonal speed win for the thorough mode; left as
  future work.

Per-variant agent writeups are in this directory (`spur.md`, `dirtyset.md`,
`fastdijkstra.md`, `stacked.md`, `parallel.md`); the bounded / A\* / exact-Steiner
agents were interrupted before writing theirs, but their modules, CSVs, and the
table above capture the results.

## Reproduce

```bash
.venv/bin/python docs/candidate-algorithms/data/eval_variant.py reweave_opt reweave reweave-base 60
```
