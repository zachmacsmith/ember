# S5 — Parallelise the restarts (`reweave-parallel`)

**Variant module:** `packages/ember-qc/src/ember_qc/algorithms/pf_parallel.py`
**Registered name:** `reweave-parallel`
**Baseline it optimises:** `reweave-thorough` (sequential best-of-4)
**Goal:** identical embedding quality, lower wall-clock.

## What thorough does, and what we change

`reweave-thorough` (`_params = {base_method:"minorminer", lns_rounds:80,
lns_penalty:4.0, base_fraction:0.4, n_restarts:4}`) runs **four independent
seed→improve restarts sequentially** inside `embed_reweave`, each on a
`timeout/4` slice, and keeps the fewest-qubit valid embedding. The restarts are
mutually independent — restart *i* never reads anything restart *j* produced — so
running them one-after-another only spends wall-clock.

`reweave-parallel` keeps the algorithm **byte-for-byte identical** and changes
only *when* the restarts run: it dispatches the four restarts to a
`concurrent.futures.ProcessPoolExecutor` (one worker per restart) and gathers the
results. This is a change in the *driver*, not in any router method, so it is a
class with its own `embed()` rather than a `router_cls` subclass.

## How quality is held byte-equivalent

| ingredient | sequential thorough | `reweave-parallel` |
|---|---|---|
| per-restart router seed | `base_seed + i*1_000_003` | identical — worker *i* calls `embed_reweave(seed=base_seed + i*1_000_003, n_restarts=1)` (stride `i==0` inside, so router seed == that value) |
| per-restart budget | `slice_timeout = timeout/4`, `base_timeout = max(1, slice·0.4)` | each worker gets `timeout/4`; `base_fraction=0.4` reproduces the same seed/improve split |
| params | `lns_rounds=80, lns_penalty=4.0, base_method="minorminer"` | same dict, passed through to each worker |
| best-of selection | `if total < best_total` over `i=0..3` → first restart wins on ties | `min` over `(total_qubits, restart_index)` → first restart wins on ties (order-independent) |

The worker is a **top-level, picklable** function `_pf_restart_worker(source,
target, timeout, seed, params)` that simply calls
`embed_reweave(..., n_restarts=1)` and returns the standard result dict. The
source/target graphs pickle cleanly (verified: pegasus_6, zephyr_4, ER graphs).

**Budget note.** The sequential driver gives restart *i* a *cumulative* deadline
`start + slice·(i+1)`; if earlier restarts finish early, a later restart can use
the leftover. We give each worker a flat `timeout/4` — the nominal slice, and an
exact match for restart 0. Byte-equivalence therefore holds whenever every
restart converges within its `timeout/4` slice (the LNS loop terminates on
`improved=False` well before the deadline for these instance sizes). Measured on
the eval grid this is the case: embeddings are identical (below). A flat slice is
also what keeps the wall-clock win — a staggered budget (worker 3 gets the full
`timeout`) would erase the speedup.

## Determinism / tie-break

Per-restart seeds are fixed (`base_seed + i*1_000_003`), so the *set* of candidate
embeddings is fixed regardless of which worker finishes first. Selecting
`min(total_qubits, restart_index)` is order-independent and reproduces thorough's
"first restart wins on a tie" rule exactly (strict `<` on the key). Summed
operation counters match the sequential driver's aggregation.

## Contract

Never crashes, never returns `None`, prints nothing. If the pool fails to
start/submit/gather, or every worker returns an empty embedding, `_parallel_embed`
returns `None` and `embed()` **falls back to sequential
`embed_reweave(n_restarts=4, **thorough_params)`** — i.e. ordinary thorough.
A per-restart worker exception is caught and that restart is dropped; the rest
still count. The gather is capped at the full `timeout` as a safety net (workers
self-cap at `timeout/4`, so it returns much sooner).

Contract check (`parallel_verify.py`): registered ✓, valid on K6→chimera4 ✓,
deterministic (seed0==seed0) ✓, infeasible K20→path_graph(2) returns a clean
failure dict (`success=False`, no crash, no `None`) ✓.

## Byte-equivalence vs thorough (standalone, `parallel_verify.py`, 20s/instance)

| instance | identical? | qubits tho/par | ACL tho/par | t_tho | t_par | ratio |
|---|---|---|---|---|---|---|
| ER20 d0.5 P6 | **yes** | 44 / 44 | 2.200 / 2.200 | 1.6s | 2.8s | x1.73 |
| ER30 d0.7 P6 | **yes** | 110 / 110 | 3.667 / 3.667 | 10.5s | 5.8s | x0.56 |
| ER40 d0.5 P6 | **yes** | 180 / 180 | 4.500 / 4.500 | 13.0s | 6.3s | x0.48 |
| ER30 d0.5 Z4 | **yes** | 78 / 78 | 2.600 / 2.600 | 6.3s | 3.7s | x0.59 |

**4/4 embeddings byte-identical.** On small instances (ER20: thorough only 1.6s)
the ~2-3s process-pool spawn + `ember_qc` re-import overhead dominates, so
parallel is *slower* (x1.73). On the cells where thorough actually works
(10-13s), parallel wins clearly (**x0.48–0.59**) — and this is **under 8-agent
contention**, which both slows the 4 simultaneous spawns/restarts and understates
the true speedup. A clean machine would show a ratio closer to
`1/4 + spawn_overhead/thorough_time`.

## Headline eval (`eval_variant.py pf_parallel reweave-parallel reweave-thorough 60`)

<!-- EVAL_GRID_PLACEHOLDER -->

## Verdict

<!-- VERDICT_PLACEHOLDER -->

## Precise change for baking in

Fold the parallel-restart driver into `embed_reweave` (or a thin wrapper)
behind a flag, keeping all four ingredients:

1. **Top-level worker** `_pf_restart_worker(source, target, timeout, seed, params)`
   calling `embed_reweave(..., n_restarts=1)` — must be module-level for
   `spawn` picklability.
2. **Parallel restart loop:** submit `n_restarts` workers to a
   `ProcessPoolExecutor(max_workers=n_restarts)`, each with `timeout/n_restarts`
   and seed `base_seed + i*1_000_003`.
3. **Budget handling:** flat `timeout/n_restarts` per worker (preserves quality
   *and* the speedup); gather capped at the overall `timeout`.
4. **Determinism / tie-break:** pick `min(total_qubits, restart_index)`; sum the
   operation counters.
5. **Fallback:** on any pool failure or empty harvest, run the existing
   sequential `embed_reweave(n_restarts=n)` so the contract (never crash /
   `None`, no stdout) is unconditionally honoured.

Suggested shape: add `parallel: bool = False` (or `max_workers`) to
`embed_reweave`; when set and `n_restarts > 1`, run the loop in the pool
instead of sequentially. `reweave-thorough` can then flip it on for a free
~2–4× wall-clock win at identical quality. Guard the pool import/use so a
restricted environment (no fork/spawn) cleanly degrades to sequential.
