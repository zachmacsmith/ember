# P1 — ATE: Adaptive Template Embedder (`p3-template`, `p3-ate`)

The headline dense arm. Owner: (M2 agent). Status: spec.

## Mechanism

```
ATE(G, T, budget):
  cache = busgraph_cache(T)                      # warmed per machine
  if n <= K_max(T):
      tmpl  = cache.find_clique_embedding(n)     # right-sized (never subset a max clique)
      POS   = crossing_position_matrix(tmpl, T)  # POS[i][j] = index in chain i of the
                                                 # contact with chain j; O(n^2), cached per (T, n)
      pi    = assign(G, POS)                     # vertex -> template chain
      emb_T = spur_prune(relabel(tmpl, pi), G)   # factored/polish.py, exact trim
      emb_T = shorten_chains(emb_T, deadline~50ms)
  else:
      emb_T = core_periphery(G, T, cache)        # degeneracy-peel core -> template;
                                                 # MM routes periphery via initial_chains
                                                 # (source passed as GRAPH OBJECT)
  emb_M = search_arm(G, T, remaining_budget)     # stock MM (later: p3-clmm)
  return argmin_ACL(emb_T, emb_M)                # both reported in metadata
```

**Assignment.** After pruning, a path-shaped template chain for v costs ≈ the span of
the crossing coordinates of v's neighbors → objective `min_pi Σ_v span_{u∈N(v)}
POS[pi(v)][pi(u)]` (minimum-linear-arrangement flavor over crossbar slots). Pipeline:
(a) seed orders {identity, cuthill, spectral} from `search_orders.py`; (b) score each
exactly by prune-simulation on POS (no target-graph work); (c) 2-swap local search on
the span objective, deterministic RNG, 100 ms cap; (d) final spur_prune. Zero cross-seed
variance by construction.

## Registered variants

`p3-template` (template arm alone, deterministic; fails for n>K_max unless
core-periphery kicks in), `p3-ate` (auto-select template vs stock-MM search arm at equal
total budget; the never-worse product arm). Assignment ablations via kwargs in the
script route only.

## Novelty vs prior art

CLMM seeds *search* (success-metric only, no trim/assignment, no ACL); DWaveCliqueSampler
practice = untrimmed clique template, no assignment, no adaptive fallback; 2504.21112 =
bipartite sources only. New: density-resolved crossover map; trimmability-aware
assignment; never-worse selector with a deterministic 100%-success arm below K_max;
"search cannot improve the construction" as a regime demonstration (§3.26: ≤0.04).

## Predictions (pre-registered intuitions, not bars)

K-ladder P16 replicates §3.26 (16/39/57% at K60/K100/K140); ER crossover p*(n) ∈
[0.25, 0.6], decreasing in n; margin 10–30% at p ∈ [0.7, 0.9]; trimmed-template ACL
model ≈ (n/12 + 1.5)·(1 − 2/(pn+1)) on P16. Z12 analog expected (busclique native).

## Viability

n ≤ K_max: legal by construction (K_n embeds every subgraph) — success 100%,
deterministic, where factored search arms failed K140 0/3. n > K_max: core+periphery
inherits CLMM's demonstrated frontier extension (K185+ on P16). `p3-ate` success =
union of both arms.

## Kill gates (pre-registered)

- **KG1** = E0 crossover map itself: kill if template+prune (identity assignment) never
  beats MM below p=0.9 at any n.
- **KG2** assignment honesty gate: on win/near-tie cells, 32 random assignments + prune
  → oracle spread; kill the 2-swap optimizer if best-of-32 gain < 2%; keep seeds-only if
  seeds capture the spread. (Internal best-of-N is protocol-legal here: whole arm ≪ one
  MM run.)
- **KG3** escape probe (informational): pssa-fast initialized AT the pruned template on
  K100 + one dense-ER cell. Predicted: cannot improve (§3.26 joint-move blindness).

## Cost & reuse

400–700 LOC python, `algorithms/paper3/ate.py` (+`_template_core.py` helpers). Reuses
`minorminer.busclique.busgraph_cache`, `factored/polish.py` (spur_prune,
shorten_chains), `embedding_backend.py` (validity, growth), `search_orders.py`, the
template-restriction recipe in `docs/paper2/data/dense_attrib.py`.

## Fairness

Must beat, paired at equal budget: stock MM; MM+spur (same polish column); `p3-clmm`
(P2); on any n ≤ K_max cell also raw busclique+prune (to show assignment/trim add
value). Cold-cache wall-clock disclosed once per target; warm cache is the default.
Assignment tuned on dev seeds only.
