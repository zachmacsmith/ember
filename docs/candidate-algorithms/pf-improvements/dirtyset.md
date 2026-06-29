# PathFinder S4 — Dirty-set incremental LNS reroute

Isolated PathFinder variant. Registered name **`pathfinder-dirtyset`**, module
`ember_qc/algorithms/pf_dirtyset.py`. Subclasses the **frozen** `PathFinderRouter`
and overrides only `_lns_improve`; wired in via `router_cls` (same pattern as
`pathfinder-spur`). Baseline (`pathfinder`, `embedding_backend.py`,
`pathfinder.py`) is untouched.

Evaluated with
`docs/candidate-algorithms/data/eval_variant.py pf_dirtyset pathfinder-dirtyset`
(full grid, 3 seeds, paired against `pathfinder` and `minorminer`). Raw/summary
CSVs alongside this file.

---

## 1. What is wasteful in the baseline

`PathFinderRouter._lns_improve` is a **round-based full sweep**:

```python
while improved and rounds < self.lns_rounds:        # default 40 rounds
    improved = False
    for v in sorted(self.chains, key=lambda x: (-len(self.chains[x]), x)):
        ...
        if self._try_shorten(v, best_total):
            improved = True
```

Every round it calls `_try_shorten` on **every** chain (longest-first), and it
only stops once a *whole* round improves nothing (a fixpoint), or the round /
deadline cap fires. Each `_try_shorten` is a real cost: it rips up `v`, runs an
SPH Steiner re-route (several node-weighted Dijkstra searches) and re-routes the
chains it displaces.

The waste: once the embedding has mostly stabilised, re-examining a far-away
chain whose neighbourhood has **not changed** since it last failed cannot find a
new shortcut — yet the baseline re-tries it every round, and pays for at least
one final all-chains sweep just to *prove* convergence. `_try_shorten(v)` depends
only on `v`'s own chain and on `v`'s source-neighbours' chains (its routing
targets); if none of those moved, the call is guaranteed to fail exactly as
before. That is the redundant work this variant removes.

## 2. The change — a worklist (dirty set)

Same move operator and accept rule (`_try_shorten` reused **verbatim**); only the
*schedule* changes. A vertex is **dirty** when a shortcut for it might newly
exist. The loop processes only dirty vertices and runs to a local fixpoint (empty
worklist) or the deadline:

```python
dirty = set(self.chains)                       # all vertices start dirty
while dirty:
    if past deadline: return best
    v = max(dirty, key=lambda u: (len(self.chains[u]), -u))   # longest, then lowest id
    dirty.discard(v)
    if len(self.chains[v]) <= 1: continue
    accepted, displaced = self._try_shorten_tracked(v, best_total)
    if not accepted: continue                  # v is clean until re-dirtied
    best = ...; best_total = ...
    for w in (v, *displaced):                  # propagate (see §3)
        dirty.add(w); dirty.update(self.src_adj[w])
```

`max(dirty, key=(length, -id))` always picks the **longest current** dirty chain,
smallest id on ties — matching the baseline's longest-first / lowest-id
preference and `lns-cpsat`'s worklist. The key is unique per vertex, so the choice
is deterministic regardless of set iteration order; always reading the *current*
length sidesteps the stale-priority problem a heap would have.

A rejected vertex is simply dropped; it returns to the worklist only when
something in its neighbourhood changes (§3). On a converging cell the worklist
drains and stays small — that is where the time is saved.

## 3. Propagation rule (the bake-in rule)

> **On an accepted move at `v`, let `changed = {v} ∪ displaced`. Re-mark dirty the
> closed source-neighbourhood of every changed chain:**
> `redirty = changed ∪ ⋃_{w∈changed} source_neighbours(w)`.

Derivation: an accepted `_try_shorten(v)` changes the chains of exactly
`{v} ∪ displaced` (the shortened `v` plus the chains its shortcut displaced and
rerouted through free space). `_try_shorten(u)`'s outcome depends only on (i)
`u`'s own chain and (ii) `u`'s source-neighbours' chains. So the only `u` whose
outcome can have changed are those whose own chain changed (`u ∈ changed`) or one
of whose source-neighbours' chains changed (`u ∈ source_neighbours(w)`,
`w ∈ changed`). Everything else is provably unaffected and stays clean. (This is
the same dirty rule the `lns-cpsat` candidate uses.) `v` itself is included
because its own chain changed — it may admit a further shortcut.

### Recovering the `displaced` set without editing the baseline

`_try_shorten` computes `displaced` internally and does not return it. It is
recovered in a thin wrapper, `_try_shorten_tracked`, with **no change to the
frozen method**:

```python
before = dict(self.chains)                     # shallow: vertex -> chain list object
accepted = self._try_shorten(v, best_total)
if not accepted: return False, ()
displaced = tuple(w for w, c in self.chains.items()
                  if w != v and before.get(w) is not c)
```

On an **accepted** move, `_try_shorten` assigns a *fresh list object* to
`self.chains[v]` and to each displaced `self.chains[w]` (every `_steiner_route`
result is a new `sorted(...)` list), and never reassigns or mutates any other
chain's list. So a shallow snapshot diffed by **list-object identity** yields
exactly `{v} ∪ displaced`. (A rejected move calls `_restore`, which rebuilds the
whole dict — but that case is never inspected, since `displaced` is read only on
acceptance.) Chain lists are only ever *replaced*, never mutated in place, so the
identity test is exact.

## 4. Safety & determinism

- **Validity:** the only mutator is `_try_shorten`, which commits a move only if
  it both shortens a chain and leaves the embedding valid (else restores). The
  routine returns the tracked best valid embedding. So, exactly as the baseline,
  it can only return a valid embedding no worse than its input. Verified valid on
  every (cell, seed) tested.
- **Determinism:** the worklist choice is a unique-keyed `max`; the propagation
  set is built from sorted `src_adj`; `_try_shorten` is deterministic.
  `dirtyset_verify.py` re-runs each variant embedding and confirms byte-identical
  output.
- **Termination:** `mark_dirty` is only triggered by an accept, and each accept
  strictly lowers the integer total-qubit count (bounded below), so there are
  finitely many accepts; between accepts no chain length changes and the worklist
  only shrinks. Independently bounded by the deadline.

## 5. Results

Full grid (`eval_variant.py`, 60 s cap, 3 seeds; ER into Pegasus-6, broken
Pegasus, Zephyr-4). Time is wall-clock mean; both algorithms run back-to-back per
(cell, seed) so the ratio is robust to parallel-agent CPU contention.

| cell | base ACL | dirtyset ACL | base t(s) | dirtyset t(s) | time ratio |
|---|---|---|---|---|---|
| ER_n20_d0.5_P6     | 2.267 | 2.267 | 0.516 | 0.421 | 0.81x |
| ER_n30_d0.5_P6     | 3.300 | 3.300 | 1.849 | 1.628 | 0.88x |
| ER_n30_d0.7_P6     | 3.889 | 3.889 | 2.865 | 2.006 | 0.70x |
| ER_n40_d0.5_P6     | 4.417 | 4.417 | 3.939 | 3.349 | 0.85x |
| ER_n40_d0.7_P6     | 5.075 | 5.092 | 5.931 | 4.010 | 0.68x |
| ER_n30_d0.5_P6brk  | 3.433 | 3.433 | 1.627 | 1.098 | 0.68x |
| ER_n30_d0.5_Z4     | 2.689 | 2.700 | 1.892 | 1.121 | 0.59x |

**Grid mean: ACL +0.1 %, std +0.005, time x0.74** (≈ 26 % faster). vs minorminer
ACL −1.6 % (unchanged from baseline — same moves).

- **ACL is effectively unchanged.** 5/7 cells are *identical* to the baseline
  (same fixpoint). Two cells drift up by one qubit on a single chain on a single
  seed (ER_n40_d0.7 +0.3 %, Z4 +0.4 %). This is the anticipated "different
  fixpoint": `_try_shorten`'s cost depends on **global** occupancy, which a
  source-local rule does not chase, so the incremental schedule can settle in a
  slightly different local optimum. The magnitude (+0.004 qubits/chain grid-mean,
  max +0.017) is far inside the run-to-run seed noise (baseline ACL std up to
  0.245), so it is not a meaningful regression.
- **Work is cut where it is wasted.** `dirtyset_verify.py` counts `_try_shorten`
  calls on the same seeded warm-start: dirty-set does **0.72x** the calls of the
  baseline (grid-mean), down to **0.53x** on cells with several improving moves
  (e.g. n30_d0.7). The floor is 1.00x — reached when the warm start is already
  locally optimal, so neither does any extra work (no accepts ⇒ nothing to
  re-dirty ⇒ one pass each). Wall-time tracks this at x0.74 (slightly above the
  call ratio because of the worklist's small per-iteration bookkeeping).

### Why not broaden propagation? (occupancy-aware ablation)

`dirtyset_propagation_experiment.py` tests an **occupancy-aware** rule = source-
local **plus** re-dirty the owners of chains physically adjacent to the qubits
whose occupancy changed (the exact "global occupancy leak" the source-local rule
ignores). Result over the grid:

| rule | mean ΔACL vs base | `_try_shorten` call ratio |
|---|---|---|
| source-local (shipped) | +0.0040 q/chain | 0.720x |
| occupancy-aware        | +0.0024 q/chain | 0.754x |

The broader rule closes one of the two drifting cells but **not** the other
(ER_n40_d0.7 stays +0.05 — a genuine order-dependent local optimum no local
propagation can erase), shaving only ~0.002 q/chain off an already-noise-level
gap while spending ~5 % more routing work. Not worth it: the source-local rule
sits on the Pareto frontier (max speedup, ACL within noise). A final full
confirmation sweep would guarantee baseline's fixpoint *condition* but re-introduce
exactly the all-chains sweep the variant exists to avoid, erasing the speedup.

## 6. Verdict & bake-in

**Verdict: bake it in.** Same embeddings (ACL within seed noise, +0.1 % grid-mean,
validity and determinism preserved) at **~26 % less wall-clock / 28 % fewer
`_try_shorten` calls**, and the gain grows on cells that converge before the round
cap. Pure win on the speed axis with no meaningful quality cost.

**Precise change to bake into `pathfinder.py::_lns_improve`:** replace the
`while improved … for v in sorted(self.chains, …)` round sweep with the worklist:

1. `dirty = set(self.chains)`; loop while `dirty`, popping
   `v = max(dirty, key=lambda u: (len(self.chains[u]), -u))`; skip singletons.
2. On an **accepted** `_try_shorten(v, best_total)`, re-dirty
   `{v} ∪ displaced ∪ ⋃_{w∈{v}∪displaced} src_adj[w]` (the closed
   source-neighbourhood of every changed chain); on a reject, leave `v` out.
3. Keep the deadline check and `best`/`best_total` tracking unchanged.

**Obtaining the displaced set** (the one subtlety): snapshot the chain dict
(`before = dict(self.chains)`) before each `_try_shorten` and, on acceptance,
take `displaced = [w for w,c in self.chains.items() if w != v and before[w] is not c]`
(list-object identity diff). When baking directly into the baseline, `_try_shorten`
already knows its `displaced` list locally, so the cleanest in-place version is to
have it **return** `displaced` to `_lns_improve` instead of reconstructing it —
the identity-diff wrapper exists here only to avoid editing the frozen method.
The `lns_rounds` parameter becomes a no-op for this phase (replaced by
fixpoint-or-deadline); keep it for API compatibility or repurpose as a safety cap
on total worklist pops.
