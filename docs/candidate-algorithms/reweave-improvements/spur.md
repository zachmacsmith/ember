# Reweave variant: `reweave-spur` — spur-pruning post-pass (Q3)

**Module:** `packages/ember-qc/src/ember_qc/algorithms/pf_spur.py`
**Registered name:** `reweave-spur`
**Baseline (frozen):** `reweave`

## Idea

The `lns-cpsat` matheuristic spends CP-SAT *seconds* to shave a little ACL off
`minorminer`, and an ablation pinned most of that gain on one cheap effect:
**deleting the redundant chain spurs** that a union-of-shortest-paths embedder
leaves behind. This variant reproduces that effect for free as a deterministic
post-pass on Reweave's final, already-valid embedding.

A qubit `q` in chain `φ(v)` is a **removable spur** iff BOTH:

- **(a) connectivity:** `φ(v) \ {q}` is still a connected subgraph of the target
  (`chain_connected`); and
- **(b) edge slack:** `q` is load-bearing for no incident edge — for every source
  edge `(v, u)`, some qubit of `φ(v) \ {q}` is still adjacent (in the target
  graph) to some qubit of `φ(u)`.

Removing such a `q` lowers ACL and qubit count and cannot break validity. Because
removing one spur can turn the qubit it was propping up into a new leaf, the pass
iterates to a **fixpoint**. Qubits and chains are visited in **sorted order**, so
the output is deterministic. Cost is `O(chain · degree)` per qubit per pass —
negligible next to routing.

## Contract — OK

Verified via `docs/candidate-algorithms/data/spur_verify.py`:

- `benchmark_one(K6, chimera_graph(4), 'reweave-spur')` → `is_valid=True`,
  deterministic across repeated runs.
- `K20 → chimera_graph(4)` (infeasible) → returns a **failure dict**
  (`success=False, status=FAILURE`), never `None`, never raises.
- Synthetic spur case `{0:[100,101,102], 1:[104,103]}` on a path target prunes to
  `{0:[102], 1:[103]}` — still valid, deterministic, and idempotent (a second
  prune is a no-op).
- Never prints; inherits a `version` str (`"2.0.0"`). Respects the deadline (the
  prune runs only once, after Reweave's own time-budgeted `run`).

By construction pruning only *removes* qubits guarded by (a)+(b), so it cannot
add overlaps, disconnect a chain, or drop an edge. The `run()` override still
re-validates with `is_valid_embedding` and returns the **unpruned** embedding if
validity were ever broken (it never was, across the whole grid).

## Measurement — variant vs frozen `reweave`

`eval_variant.py pf_spur reweave-spur 60` (3 seeds/cell):

| cell | reweave ACL | spur ACL | ACL Δ% | std Δ | time × |
|---|---|---|---|---|---|
| ER_n20_d0.5_P6    | 2.267 | 2.267 | +0.0% | +0.000 | 0.96 |
| ER_n30_d0.5_P6    | 3.300 | 3.289 | −0.3% | −0.011 | 1.00 |
| ER_n30_d0.7_P6    | 3.889 | 3.844 | −1.1% | −0.025 | 1.06 |
| ER_n40_d0.5_P6    | 4.417 | 4.392 | −0.6% | −0.017 | 1.07 |
| ER_n40_d0.7_P6    | 5.075 | 4.958 | −2.3% | +0.036 | 0.93 |
| ER_n30_d0.5_P6brk | 3.433 | 3.422 | −0.3% | −0.016 | 0.91 |
| ER_n30_d0.5_Z4    | 2.689 | 2.689 | +0.0% | +0.000 | 1.06 |

**GRID MEAN vs `reweave`: ACL −0.7%, std −0.005, time ×1.00.**
**GRID MEAN vs `minorminer`: ACL −2.3%.**

- The gain scales with density/size (biggest on `n40_d0.7`, −2.3%) — exactly where
  union-of-shortest-paths leaves the most spurs.
- **No per-cell regression** (worst cell is +0.0%): pruning only removes
  provably-redundant qubits behind a validity guard, so it is strictly safe.
- **Time ×1.00** confirms the prune is free; the ±5% jitter is CPU-contention
  noise from back-to-back runs, not prune cost.
- std mostly improves; the lone +0.036 (`n40_d0.7`) is the side-effect of
  unevenly shortening chains in the cell with the largest ACL drop.
- The marginal gain over `reweave` (−0.7%) is smaller than over `minorminer`
  (−2.3%) because Reweave's LNS already removes *some* spurs while shortening
  the longest chains; pruning mops up the rest, including spurs on the short
  chains LNS never reroutes.

## Standalone: spur-pruning on plain `minorminer` (the cheap shadow of lns-cpsat)

`spur_on_minorminer.py` applies the **same** `prune_spurs` directly to raw
`minorminer` output across the grid:

| cell | mm ACL | +prune ACL | ACL Δ% | prune time |
|---|---|---|---|---|
| ER_n20_d0.5_P6    | 2.317 | 2.300 | −0.7% | 0.27 ms |
| ER_n30_d0.5_P6    | 3.356 | 3.311 | −1.3% | 1.08 ms |
| ER_n30_d0.7_P6    | 3.911 | 3.856 | −1.4% | 1.75 ms |
| ER_n40_d0.5_P6    | 4.517 | 4.392 | −2.8% | 3.33 ms |
| ER_n40_d0.7_P6    | 5.167 | 4.975 | −3.7% | 4.23 ms |
| ER_n30_d0.5_P6brk | 3.478 | 3.422 | −1.6% | 1.30 ms |
| ER_n30_d0.5_Z4    | 2.744 | 2.711 | −1.2% | 1.04 ms |

**GRID MEAN: ACL −1.8% over raw minorminer, ~1.86 ms/embedding, all valid.**

### vs `lns-cpsat` on the 5 cells it reported

| cell | lns-cpsat Δ% | spur Δ% | fraction recovered |
|---|---|---|---|
| n20_d0.5    | −2.2% | −0.7% | 34% |
| n30_d0.5    | −2.3% | −1.3% | 58% |
| n30_d0.7    | −2.0% | −1.4% | 71% |
| n30_d0.5brk | −2.9% | −1.6% | 56% |
| n30_d0.5_Z4 | −2.0% | −1.2% | 60% |
| **MEAN**    | **−2.3%** | **−1.3%** | **56%** |

`lns-cpsat` averages ~5.9 s/embedding on these cells; spur-pruning averages
~1 ms — **~5000× faster** while recovering **~56%** of the ACL gain. So the
hypothesis ("lns-cpsat's gain is mostly spur removal") is *largely* borne out:
about half of CP-SAT's ACL win is pure, free spur deletion; the remainder is
genuine path-rerouting CP-SAT does on top. On the larger `n40` cells (which
`lns-cpsat` never reached) pruning alone already buys −2.8% to −3.7%.

## VERDICT: PROMISING

Free (time ×1.00), strictly safe (no per-cell regression, validity-guarded),
deterministic; −0.7% grid-mean ACL on top of `reweave` and −2.3% over
`minorminer`, scaling to −2.3% on the densest cell. As a standalone op it is a
genuine cheap improver for *any* embedder (−1.8% on raw minorminer at ~2 ms),
recovering ~56% of a multi-second matheuristic's gain.

## Bake-in note — promote to a universal `embedding_backend.prune_spurs`

The logic is already a free function `prune_spurs(embedding, source, target)` in
`pf_spur.py` (the `adj` / `src_adj` kwargs are perf-only and can be dropped or
kept). Move it verbatim into `embedding_backend.py` next to `resolve_overlaps`
and call it as a finishing pass from any embedder. Exact logic:

```python
def prune_spurs(embedding, source, target, *, adj=None, src_adj=None):
    """Delete removable spur qubits from every chain, to a fixpoint."""
    if adj is None:
        adj = build_adjacency(target)
    if src_adj is None:
        src_adj = {v: list(source.neighbors(v)) for v in source.nodes()}
    chains = {int(v): [int(q) for q in qs] for v, qs in embedding.items()}
    changed = True
    while changed:
        changed = False
        for v in sorted(chains):
            chain = chains[v]
            if len(chain) <= 1:
                continue
            # neighbour qubit-sets, reflecting prunings earlier in this pass
            nbr_sets = {u: set(chains[u]) for u in src_adj.get(v, []) if chains.get(u)}
            for q in sorted(chain):            # sorted() snapshots the list
                if len(chain) <= 1:
                    break
                remainder = [x for x in chain if x != q]
                if not chain_connected(remainder, adj):          # (a) connectivity
                    continue
                rem_set = set(remainder)
                covered = True
                for u in src_adj.get(v, []):                      # (b) edge slack
                    u_set = nbr_sets.get(u)
                    if not u_set:
                        covered = False                          # neighbour unplaced → keep q
                        break
                    if not any(w in u_set for x in rem_set for w in adj.get(x, ())):
                        covered = False
                        break
                if covered:
                    chain.remove(q)
                    changed = True
    return chains
```

Key invariants that make it universally safe:
- only chains of length ≥ 2 are touched ⇒ a chain is never emptied;
- removal is gated on (a) connectivity and (b) edge coverage **re-checked against
  the current (already-pruned) neighbour chains**, so coverage stays symmetric and
  every edge stays covered from both endpoints;
- it only ever removes qubits ⇒ disjointness is preserved automatically;
- visiting `sorted(chains)` then `sorted(chain)` ⇒ deterministic output.

Callers should still gate on `is_valid_embedding(pruned, …)` and fall back to the
input as a belt-and-braces guard (it never triggered across the grid).

## Files

- `packages/ember-qc/src/ember_qc/algorithms/pf_spur.py` — variant + `prune_spurs`.
- `docs/candidate-algorithms/data/spur_verify.py` — contract / correctness checks.
- `docs/candidate-algorithms/data/spur_on_minorminer.py` — standalone-on-minorminer sweep.
- `docs/candidate-algorithms/data/reweave-spur_variant_{raw,summary}.csv` — eval output.
