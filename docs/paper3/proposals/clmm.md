# P2 — CLMM++: template-seeded search (`p3-clmm`, `p3-clmm-core`, ...)

Mid-band contender, feasibility-frontier arm, and mandatory literature control.
Owner: (M2 agent). Status: spec.

## Mechanism

1. **`p3-clmm` — faithful Zbinden reproduction (the control):** busclique
   `find_clique_embedding(k)` chains passed as `initial_chains` to stock
   `minorminer.find_embedding` (source as GRAPH OBJECT — edge-list drops isolated
   vertices, §3.23 bug-1); k = min(n, K_max); when k < n, chains assigned to k
   lowest-degree vertices (sparse) or k random vertices (dense) per their rule;
   `skip_initialization=False` (MM legalizes around seeds). Single-shot — CLMM is not a
   restart scheme.
2. **Variants:** `p3-clmm-core` — seed the degeneracy k-core (the hard sub-structure)
   instead of degree/random selection, periphery left to MM's search (where MM excels);
   seed-form sweep (raw clique chains vs spur-pruned chains vs prune-to-core-subgraph)
   — which wins is p-dependent, measured not assumed; seed-size ladder k ∈ {n/4, n/2,
   3n/4, K_max} (all ~free from the same cache) — script-route kwargs, registered names
   only for survivors.
3. Output feeds `p3-ate` as its search arm once both exist.

## Novelty

Zbinden measured success counts only, Chimera/Pegasus, no Zephyr, no trimming,
degree/random selection. New: ACL-, variance-, and density-resolved evaluation under
honest controls; degeneracy-core seeding; pruned seeds; size ladder; Z12; head-to-head
vs the raw template (never run in the literature).

## Predictions

Mid-band p ∈ [0.08, p*], n ∈ [100, 300]: success-rate wins (their result, retested on
MM 0.2.22) and modest conditional ACL wins (0–8%) where MM's polish cannot fully wash
out the seed. Frontier: max-embeddable-n extension on P16/Z12 (K182+, ER n=300 p ≥ 0.3),
plus K140-class cells where unseeded arms fail.

## Viability

Seeds pre-solve the hardest sub-structure; MM legalizes the periphery — the demonstrated
K185+ mechanism. Frontier success results cannot "fail" as science: either outcome is
reportable.

## Kill gate (pre-registered)

6 mid-band cells (p ∈ {0.1, 0.2, 0.3} × n ∈ {150, 220}) + 2 frontier cells (K182, ER
n=300 p=0.5), 5 dev seeds, 60 s: `p3-clmm` + one variant vs stock MM. Kill the ACL claim
if no cell shows a paired win; kill ++ if it never beats the reproduction. Success/
frontier story survives regardless.

## Cost & reuse

200–400 LOC, `algorithms/paper3/clmm.py`. Reuses stock minorminer `initial_chains`
path, busclique cache, `degeneracy` order in `search_orders.py`, P1's prune utilities
(import from `ate` module or shared `_template_core.py`).

## Fairness

Must beat: stock MM (paired, same seed); the faithful reproduction (to claim ++); raw
template+prune on any n ≤ K_max cell it claims. No restarts. Success and ACL reported
separately.
