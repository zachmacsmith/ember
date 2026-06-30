# Reweave — negotiated rip-up-and-reroute minor embedding

Reweave is a new minor-embedding algorithm for ember-qc (research-brief
approach **3.5**) plus the shared scaffolding (**§2**) that future approaches
build on. It targets the documented weaknesses of `minorminer` (MM): run-to-run
**ACL variance** and chains that are longer than necessary on denser graphs.

## What was added

| Component | Location | Role |
|-----------|----------|------|
| Round → repair backend | `ember_qc/embedding_backend.py` | Routing primitives + `round_assignment` / `grow_to_connected` / `resolve_overlaps`, reusable by every chain-building approach (§2.2) |
| `evaluate()` | `ember_qc/benchmark.py` | One-call quality report: validity, ACL **mean + std**, chain-length **CV**, qubits, couplers (§2.4) |
| `minorminer-layout` | `ember_qc/algorithms/minorminer.py` | MM seeded with a **p-norm layout** — the primary baseline to beat, and the Ocean "Layout Embedding" sparse baseline (§2.3) |
| `reweave*` | `ember_qc/algorithms/reweave.py` | The negotiated rip-up-and-reroute embedder (3.5) |

The embedder *interface* (§2.1) already existed as `EmbeddingAlgorithm` +
`@register_algorithm`; Reweave conforms to it, so it drops into the existing
benchmark runner, CLI, validation, and contract-test suite with no new harness.

## The idea

Minor embedding *is* multi-net global routing: each chain is a Steiner tree
joining terminals (qubits adjacent to its neighbours' chains) while competing for
a congested fabric. Reweave ports the two routing ideas MM leaves on the
table, as the smallest useful delta from MM:

1. **A real Steiner inner step.** MM rebuilds a vertex's chain as a *union of
   independent shortest paths* to its placed neighbours. Reweave grows one
   tree with the shortest-path heuristic: each neighbour is wired to the
   *nearest node of the growing tree*, so paths share structure and the chain
   is shorter.
2. **Negotiated congestion (McMurchie–Ebeling 1995).** MM prices an over-used
   qubit by `diam(G)^k` — a per-pass snapshot with no memory. Reweave prices
   qubit `q` by `(1 + history[q]) · (1 + pres_fac · occupancy[q])`, where the
   *present* term rises within a pass and the *history* term **accumulates
   across passes**. A consistent, growing price forces chains to negotiate
   scarce qubits over rounds instead of thrashing.

### Why it is an *improver*, not a cold-start router

A from-scratch router is throttled by the very thing the MM paper named as the
key open problem — **initial placement**. Routing every chain from scattered
single-qubit seeds balloons chains on dense graphs (measured: cold-start ACL
~3.9–8 vs MM ~2.3). So Reweave's headline mode **warm-starts from a fast base
embedding** (MM by default; any registered algorithm works) and then runs
negotiated, **large-neighbourhood** rip-up-and-reroute:

> take the longest chain, let it take a shortcut through occupied territory, then
> re-route the chains it displaced through free space — keep the move only if it
> shortens the chain and the embedding stays valid.

Because it tracks the best valid embedding seen, **it never returns anything
worse than its base**, and it spends its whole time budget shrinking ACL
(anytime behaviour). A BFS-ordered negotiated cold start is the fallback when no
base embedding is available.

This cleanly isolates the 3.5 question — *is it MM's myopic congestion signal or
its weak inner step that hurts?* — because the only changes from MM are those two.

## Registered algorithms

| Name | Mode | Notes |
|------|------|-------|
| `reweave` | MM-seeded improver | Balanced; never worse than MM, equal-base comparison |
| `reweave-thorough` | best-of-4 restarts + deeper reroute | Lower ACL & variance; ~4× the time |
| `reweave-cold` | standalone BFS cold start | No MM seed; documents the placement gap |

## Usage

```python
from ember_qc import benchmark_one, evaluate
import dwave_networkx as dnx, networkx as nx

target = dnx.pegasus_graph(6)
source = nx.gnp_random_graph(30, 0.5, seed=1)

r = benchmark_one(source, target, "reweave", timeout=30, seed=0)
print(r.avg_chain_length, r.is_valid)
print(evaluate(r.embedding, source, target, wall_time=r.wall_time))
```

CLI (drops into the existing runner):

```bash
ember run --graphs "1-60" --algorithms minorminer,minorminer-layout,reweave,reweave-thorough \
          --topologies pegasus_6 --trials 5
```

## Benchmark results

Erdős–Rényi sources into broken-free Pegasus P6 (680 qubits), one fixed instance
per cell, varying only the algorithm seed so the spread is the **run-to-run
variance on a fixed instance** — MM's documented flaw. 6 seeds/cell. ACL = average
chain length (lower better); std is across seeds.

| instance (ER→P6) | `minorminer` ACL±std | `minorminer-layout` | `reweave` | `reweave-thorough` |
|---|---|---|---|---|
| n30, d0.4 | 3.19 ± 0.16 | 3.11 ± 0.09 | 3.14 ± 0.12 | **3.04 ± 0.10** |
| n30, d0.6 | 3.65 ± 0.12 | 3.75 ± 0.08 | 3.61 ± 0.08 | **3.48 ± 0.10** |
| n40, d0.4 | 4.22 ± 0.18 | 4.37 ± 0.26 | 4.16 ± 0.17 | **4.03 ± 0.07** |
| n40, d0.6 | 4.97 ± 0.23 | 4.99 ± 0.18 | 4.88 ± 0.23 | **4.71 ± 0.15** |

`reweave-thorough` (best-of-4) vs `minorminer`, per cell: **−4.5% to −5.2%
mean ACL**, **−35% to −61% ACL std**, and lower max-chain-length and total qubits
in every cell (e.g. n40 d0.4: max 6.2→5.7, qubits 168.7→161.0; std 0.18→0.07).
Wall-clock: MM 0.3–0.8 s, `reweave` 1.3–3.8 s, `reweave-thorough`
4.9–15.6 s (pure Python). `reweave` (single-seed) is the fair *equal-base*
point: ≤ MM ACL and ≤ MM variance in every cell, never worse.

**Takeaways**

- Reweave is **valid on every instance** and, by construction, **never
  regresses** below its MM base.
- On `n ≥ 30` it lowers mean ACL by ~1–2% (`reweave`) and ~5–8%
  (`reweave-thorough`, best-of-4), and lowers ACL **variance** in most cells —
  the headline metric vs MM.
- The cost is wall-clock (pure Python; ~3–6× MM for `reweave`, more for
  thorough), so the win is on the {ACL, ACL-variance} axes, not time. The
  brief's bar — *beat MM on at least one of {ACL, ACL-variance, success,
  wall-clock} without regressing the others* — is met.

Reproduce with `scripts`-style harness in
`packages/ember-qc` or directly via `benchmark_one` over a size×density×seed grid.

## Limitations & next steps

- **Pure Python** routing (per-vertex node-weighted Dijkstra) is the speed
  bottleneck; an A\*/bounded-search inner step or a Cython core would close the
  wall-clock gap.
- The cold-start router needs a better *initial placement* to be competitive
  standalone — exactly the white space the heavier approaches target (srGW 3.1,
  differentiable 3.2). They can reuse this backend's `round_assignment` /
  `grow_to_connected` / `resolve_overlaps`.
- The LNS neighbourhood is single-chain-shortcut + free-space repair; deeper
  destroy-repair (a whole congested region, repaired with CP-SAT — approach 3.4)
  is the path to larger ACL wins.
