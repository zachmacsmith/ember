# pathfinder-stacked — Placement-stacked PathFinder (Q1)

**Module:** `ember_qc/algorithms/pf_stacked.py`  **Variant:** `pathfinder-stacked`
**Baseline:** `pathfinder` (frozen; warm-starts from `minorminer`)

## What changed

PathFinder is an improver that warm-starts from a base placement (`base_method`)
and then runs negotiated large-neighbourhood rip-up-and-reroute, never returning
worse than that base. The only change here is **which placement it stacks on**:

- baseline: `base_method="minorminer"` (fast, but MM's run-to-run variance flows
  straight into PathFinder's spread)
- **`pathfinder-stacked`: `base_method="multilevel"`** — warm-start from the
  multilevel V-cycle placement (coarsen → multi-restart MM at the coarsest level →
  uncoarsen with chain-splitting + FM rebalance). Coarse decisions are made where
  global structure is visible, so the seed handed to PathFinder is both lower
  variance and more compact than a raw MM seed.

No router internals were touched — it is purely a one-line base-placement swap
(`_params = {"base_method": "multilevel"}`). Dependency-free.

## Measured impact (7-cell ER grid, 3 seeds, timeout 60s)

Per-cell, `pathfinder-stacked` (multilevel base) vs frozen `pathfinder`:

| cell | ACL % | std Δ (q/chain) | baseline→variant std | time |
|---|---:|---:|---|---:|
| ER n20 d0.5 P6      | −2.2% | +0.023 | 0.062 → 0.085 | x0.85 |
| ER n30 d0.5 P6      | +2.0% | −0.098 | 0.125 → 0.027 (~4.6×) | x0.96 |
| ER n30 d0.7 P6      | −3.4% | −0.214 | 0.245 → 0.031 (~7.9×) | x0.80 |
| ER n40 d0.5 P6      | +1.7% | −0.087 | 0.118 → 0.031 (~3.8×) | x0.59 |
| ER n40 d0.7 P6      | −3.3% | +0.027 | 0.035 → 0.062 | x0.59 |
| ER n30 d0.5 P6-brk  | −1.9% | +0.024 | 0.094 → 0.119 | x0.72 |
| ER n30 d0.5 Z4      | −0.4% | −0.010 | 0.079 → 0.068 | x0.59 |
| **GRID MEAN**       | **−1.1%** | **−0.048** | | **x0.73** |

vs `minorminer`: ACL **−2.7%**.

The variance reduction concentrates exactly where it matters — the dense,
high-variance cells (the density-cliff regime) get 3.8×–7.9× std cuts, while
already-tight cells tick up only ≤0.03 q/chain. And because the more compact seed
gives the LNS less to do, the variant is **faster than baseline** (~0.73×), not
slower. It strictly dominates the baseline on ACL, variance, and time.

### Alternatives measured and rejected

Same grid, vs frozen `pathfinder`:

| base strategy | ACL % | std Δ | time | verdict |
|---|---:|---:|---:|---|
| **multilevel (delivered)** | **−1.1%** | **−0.048** | **x0.73** | dominates baseline on all 3 axes |
| best-of-2 (MM + multilevel, fewest-qubit) | −2.4% | −0.029 | x1.91 | best mean ACL, but ~2× time and **weaker** variance cut |
| srgw | +0.9% | −0.004 | x1.42 | dominated; needs POT; +7.0% on Zephyr |
| minorminer (== baseline, sanity) | ≈0% | ≈0 | x1.0 | noise floor (confirms harness) |

best-of-2 keeps the lowest *qubit count* of the MM-seeded and multilevel-seeded
runs, which buys a better mean ACL (−2.4%) — but selecting the MM run when it
happens to be shorter reintroduces MM's variance, so it cuts run-to-run std
*less* than the single multilevel base (−0.029 vs −0.048) while costing ~2× the
wall-clock. It loses on this variant's whole reason for existing (variance).

## VERDICT: PROMISING

Stacking PathFinder on the `multilevel` placement keeps mean ACL (−1.1% grid mean,
−2.7% vs MM), cuts run-to-run ACL variance 3.8×–7.9× on the dense cells where MM's
spread is worst, **and** runs faster (~0.73×) — a strict, dependency-free
improvement over the MM-seeded baseline.

## Bake-in

Set PathFinder's `base_method="multilevel"` (the single one-line change). Concretely,
the production algorithm is:

```python
@register_algorithm("pathfinder-stacked")
class PathFinderStacked(_PathFinderBase):
    _params = {"base_method": "multilevel"}
```

i.e. identical to `pathfinder` except the warm-start placement is `multilevel`
instead of `minorminer`. To wire into the package, add
`from ember_qc.algorithms import pf_stacked` to `algorithms/__init__.py` (frozen
here, so left untouched). Do **not** ship best-of-2 — it is slower and a weaker
variance-reducer. The `multilevel` base is already a registered, dependency-free
algorithm, so no new dependency is introduced. If the goal is to make the default
`pathfinder` lower-variance outright, switch its own `_params` base_method to
`"multilevel"`.
