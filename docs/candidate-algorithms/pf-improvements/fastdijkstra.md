# PathFinder improvement S1 — faster node-weighted Dijkstra core

**Module:** `ember_qc/algorithms/pf_fastdijkstra.py`
**Registry name:** `pathfinder-fastdijkstra`
**Baseline:** `pathfinder` (frozen = today's *un-bounded* `pathfinder-base`)
**Status:** ❌ **not baked — superseded by bounded routing (S3).** This was a pure
speed win **measured against the un-bounded engine**, where the per-route Dijkstra
runs over the *full* target graph. The production router instead adopted **bounded
routing (S3)**, which shrinks each Dijkstra to a small region by a different
mechanism — and the two **fully overlap**. A Prompt-10 follow-up re-tested numba
*on top of* the final production router (`pf_numba.py`): a region-restricted numba
kernel is a **wash** (within noise of pure-Python `pathfinder`), and a full-graph
numba kernel is **~24% slower** than bounded routing. With **70–84%** of runtime in
the compiled-C++ `minorminer` base call, compiling the routing inner loop does not
speed up the optimized algorithm. The production router stays pure Python; the
numbers below stand only against the un-bounded baseline.

---

## TL;DR

| metric | result |
|---|---|
| Contract (kernel vs backend Dijkstra) | **bit-identical** dist + pred + path + visit-count, 240 randomized cases |
| Embedding equivalence (end-to-end) | **identical embeddings & telemetry**, 18/18 (cell × seed) |
| ACL Δ vs baseline (grid-mean) | **+0.0%** (identical on every cell) |
| ACL-std Δ vs baseline | **+0.000** (identical on every cell) |
| **Time ratio vs baseline (end-to-end, grid-mean)** | **×0.37** (≈2.7× faster) |
| Time ratio on **n40 d0.7** (slowest cell) | **×0.36** (5.09 s → 1.81 s) |
| Time ratio, **routing core only** (MM-seed excluded) | **×0.174** (≈5.8× faster) |
| numba required? | **Yes** — the pure-Python fallback is ~2× *slower* than baseline |

**Verdict:** ship it, gated on `numba`. It does not change *what* PathFinder computes
(provably — same shortest paths, same predecessor tree, same chains), only *how
fast*. The improver phase (`_lns_improve` / `_cold_start`), whose per-route,
per-neighbour Dijkstra is PathFinder's dominant cost, gets ~5.8× faster; the
end-to-end number is smaller only because every run still pays the **shared,
unchanged minorminer base-embed**.

---

## What it changes (and what it does not)

The bottleneck is the pure-Python node-weighted multisource Dijkstra
(`embedding_backend.weighted_multisource_dijkstra`: `heapq` over tuples + `dict`
cost/dist/pred lookups), invoked **once per placed neighbour, per route**, and a
route is rebuilt for the longest chain plus its displaced chains on **every** LNS
round. On the eval grid that is thousands of full-graph SSSPs.

`FastDijkstraRouter(PathFinderRouter)` overrides exactly two things:

1. **`__init__`** — precompute, **once per (source, target)**:
   * a `node → index` map and `index → node` list;
   * **CSR** integer arrays `indptr (int64[N+1])`, `indices (int64[nnz])`, where
     `indices[indptr[i]:indptr[i+1]]` is node *i*'s neighbour tuple from
     `build_adjacency`, **in order** (this ordering is what makes relaxation order
     — and therefore the predecessor tree — match the baseline);
   * reusable `dist`/`pred`/heap work buffers (no per-call allocation).

2. **`_steiner_route`** — a line-for-line copy of the baseline whose *only* change
   is the inner SSSP: convert the `self.node_cost` dict → a `float64` array once
   per route, mask `forbidden` nodes with `+inf`, call the compiled kernel, then
   map the returned index arrays back to the `{node: …}` dist/pred dicts the rest
   of the (unchanged) method consumes. Everything downstream — root selection,
   nearest-tree attachment, `reconstruct_path` — is byte-for-byte the baseline.

Nothing else is touched: seeding, cold-start, LNS accept/restore logic, telemetry
counters, and registration parameters are all inherited.

### Why the results are *identical*, not just "as good"

The kernel reproduces the baseline's determinism exactly:

* **Node-weighted metric** — path cost = Σ `cost[node]` over the path incl. both
  endpoints; `float64` accumulation along a fixed path is bit-identical to the
  baseline's Python `float`.
* **Tie-break** — a binary min-heap keyed by `(accumulated_cost,
  insertion_counter)`, the counter strictly increasing across sources **and**
  relaxations, so every heap key is unique and the pop order is uniquely defined.
  This is the same order `heapq` produces from `(cost, tie, node)` tuples (the
  unique `tie` means `node` is never compared).
* **Source order** — sources are seeded in the *same* `boundary`-set iteration
  order the baseline uses (the override builds the identical set the identical
  way).
* **forbidden / `default_cost`** — a forbidden node gets `cost = +inf` (never
  entered: `d + inf` never beats a finite `dist`); a forbidden source is skipped;
  missing nodes default to `1.0`. Same observable behaviour as the baseline's
  `if w in forbidden: continue` and `cost.get(w, default_cost)`.

Because pop order, relaxation order, and the strict-`<` update rule all match, the
`dist` **and** `pred` are reproduced bit-for-bit — hence identical chains,
identical embeddings, identical ACL, identical variance.

---

## Verification

### 1. Kernel contract — `fastdijkstra_contract.py`
240 randomized cases (Erdős–Rényi, 2-D grid, small Pegasus/Zephyr targets;
non-contiguous node ids; random full-coverage cost maps; random `forbidden`;
random source sets), each comparing the kernel against
`weighted_multisource_dijkstra`:

```
cases: 240   dist mismatches: 0   pred mismatches: 0   path mismatches: 0   settle mismatch: 0
CONTRACT: OK (bit-identical to baseline)
```

`dist` dicts (keys + bit-equal values), `pred` dicts, every reconstructed path,
and the settled-node count (== the baseline's `visit_counter` increment) all match.

### 2. End-to-end equivalence — `fastdijkstra_equiv.py`
6 cells × 3 seeds, full `embed()` for `pathfinder` vs `pathfinder-fastdijkstra`:

```
cases: 18   embedding diffs: 0   counter diffs: 0
EQUIVALENCE: OK (identical embeddings & telemetry)
```

Identical chains *and* identical telemetry (`target_node_visits`,
`cost_function_evaluations`, `embedding_state_mutations`,
`overlap_qubit_iterations`) — confirming the variant walks the exact same search.

---

## Results — `eval_variant.py pf_fastdijkstra pathfinder-fastdijkstra` (full grid, 3 seeds)

| cell | ACL base | ACL fast | ACL Δ | std Δ | t base (s) | t fast (s) | time ratio |
|---|---:|---:|---:|---:|---:|---:|---:|
| ER n20 d0.5 P6        | 2.267 | 2.267 | +0.0% | 0.000 | 0.508 | 0.159 | ×0.31 |
| ER n30 d0.5 P6        | 3.300 | 3.300 | +0.0% | 0.000 | 1.677 | 0.730 | ×0.44 |
| ER n30 d0.7 P6        | 3.889 | 3.889 | +0.0% | 0.000 | 2.411 | 1.078 | ×0.45 |
| ER n40 d0.5 P6        | 4.417 | 4.417 | +0.0% | 0.000 | 3.405 | 1.420 | ×0.42 |
| **ER n40 d0.7 P6**    | **5.075** | **5.075** | **+0.0%** | **0.000** | **5.091** | **1.808** | **×0.36** |
| ER n30 d0.5 P6-broken | 3.433 | 3.433 | +0.0% | 0.000 | 1.595 | 0.572 | ×0.36 |
| ER n30 d0.5 Z4        | 2.689 | 2.689 | +0.0% | 0.000 | 1.886 | 0.525 | ×0.28 |
| **GRID MEAN** | — | — | **+0.0%** | **+0.000** | — | — | **×0.37** |

(vs `minorminer`: ACL −1.7% grid-mean — unchanged from the baseline, as expected.)

### Routing core in isolation — `fastdijkstra_isolate.py`
The end-to-end ratio is diluted by the shared, unchanged MM base-embed. Seeding
both routers from the *same* MM embedding and timing only `_lns_improve`:

```
ROUTING-ONLY total: base=29.65s  fast=5.15s  ratio=0.174x  (speedup 5.76x)   ACL identical on every case
```

Per-cell routing ratios cluster tightly at **×0.15–0.19** (≈5–6.5× faster),
including **×0.18–0.19 on n40 d0.7**. This is the true speedup of the Dijkstra
core; the grid `×0.37` is what survives after re-adding the MM seed both share.

---

## Is `numba` required?

**Yes — it is the entire source of the win.** The module also ships the
spec-requested **pure-array Python fallback** (`heapq` over `(cost, counter, idx)`
tuples, array cost lookups, locally-bound names, used automatically if `numba` is
absent). Measured on the routing-heavy cells:

```
PURE-PYTHON FALLBACK (numba off): routing ratio = 1.93x  (i.e. ~2x SLOWER)   ACL identical
```

The fallback is **correct** (bit-identical embeddings) but **slower than the
baseline**: replacing `dict` lookups with NumPy *scalar* indexing
(`indices[e]`, `cost[w]`, `dist[w]`) trades cheap C-level `dict.get` for boxed
`np.int64`/`np.float64` per access, and the per-call `dist.fill(inf)` resets all
*N* nodes whereas the baseline only ever populates the *reached* ones. CPython's
`heapq` is already C, so there is little left for pure Python to win. The
**compiled kernel is what removes the interpreter from the hot loop.**

The one-time JIT (`@njit(cache=True)`) is warmed at import (before any timing) and
cached to disk across processes, so it never lands in a measured run.

---

## Bake-in recommendation

Adopt it, with `numba` made a dependency of the PathFinder fast path:

* **New deps:** `numba` (pulls `llvmlite`). Both are pre-built wheels for the
  project's Python/arch (here `numba 0.65.1`, `llvmlite 0.47.0`, py3.10/arm64).
* **Degrade gracefully when `numba` is absent:** because the pure-array fallback is
  *slower* than the baseline, the bake-in should **fall back to the existing
  `weighted_multisource_dijkstra`** (not to the array fallback) when `numba`
  cannot be imported. The array fallback is retained in the module only as a
  correctness oracle / spec artifact.

### Exact fast-Dijkstra signature (to augment the backend)

```python
# numba @njit(cache=True); pure-array Python twin with identical semantics.
def fast_multisource_dijkstra(
    indptr,   # int64[N+1]   CSR row pointers (target adjacency, build_adjacency order)
    indices,  # int64[nnz]   CSR neighbour node-indices, per-node tuple order preserved
    cost,     # float64[N]   per-node cost; +inf == forbidden (never entered/seeded)
    sources,  # int64[ns]    seed node-indices, processed in this exact order
    dist,     # float64[N]   OUT: reset to +inf, then min path-cost (+inf == unreached)
    pred,     # int64[N]     OUT: reset to -1; reached node's pred is -1 iff source else idx
    hc, ht, hi,  # float64/int64/int64 scratch heap arrays, capacity >= N + nnz
) -> int:        # number of settled (non-stale) pops == baseline visit_counter increment
    ...
```

Path cost = Σ `cost[node]` over the path (both endpoints). Heap ordered by
`(cost, insertion_counter)` with a globally increasing counter ⇒ deterministic,
baseline-identical pop order and predecessor tree.

The call-site adapter the variant already implements (and which the backend wrapper
would mirror): precompute CSR + node↔index maps + work buffers **once per target**;
per route convert the cost dict → array, mask `forbidden` with `+inf`, build the
source index array in set-iteration order, call the kernel, and map the reached
`dist`/`pred` indices back to `{node: …}` dicts. Keeping `dist`/`pred` as arrays
through the rest of `_steiner_route` (skipping the dict rebuild) is a further, but
unnecessary-for-this-result, optimization — `N ≈ 600–680` makes the rebuild cheap.

---

## Files

* `ember_qc/algorithms/pf_fastdijkstra.py` — the variant (numba kernel + fallback + `FastDijkstraRouter`).
* `docs/candidate-algorithms/data/fastdijkstra_contract.py` — kernel-vs-backend bit-identity (240 cases).
* `docs/candidate-algorithms/data/fastdijkstra_equiv.py` — end-to-end embedding/telemetry equivalence (18 cases).
* `docs/candidate-algorithms/data/fastdijkstra_isolate.py` — routing-only speedup (MM seed excluded).
* `docs/candidate-algorithms/data/pathfinder-fastdijkstra_variant_{raw,summary}.csv` — eval grid output.
