# Track B: demand-aware connected-tree construction

2026-09-08. Exploratory candidate, specified before implementation. This is a separate direct constructor, not an initializer or refinement of the geometric wire layout. One evolving partial embedding is used throughout; no alternate constructor, competitor start, stored embedding, family dispatch or portfolio is allowed.

## Hypothesis and fixed first prototype

The geometric constructor's restricted horizontal/vertical chain shapes can cost physical qubits on sparse graphs even after local repair. Instead, place logical vertices directly as connected physical trees. Choose the next vertex by most already placed neighbors, then total degree, with deterministic seeded ties. Route its required contacts jointly through shared tree paths. A placed chain with remaining logical neighbors must retain enough distinct free boundary sites for those neighbors. This capacity requirement is necessary for extending that frozen chain without later growth; it is not a feasibility certificate for all remaining vertices.

Every free site receives a congestion price equal to the sum, over touching placed chains, of their remaining demand divided by their current free boundary size. A shortest-path step costs one plus that price. Recompute prices from the current partial embedding, so consuming scarce ports changes later routing. Choose up to 64 roots on the most constrained required chain's free boundary. Compute reverse multi-source distances to each required chain; retain up to eight roots by summed distances and evaluate the actual union of their predecessor paths. Choose the smallest connected union, then lower congestion cost, then greater free boundary and deterministic tie order. Prune dispensable leaves while retaining required contacts. Grow a chain, when necessary, by the adjacent site opening the most new distinct free boundary sites until its remaining demand can be served. There are no geometric coordinates or assumed target topology.

If construction fails, one bounded transaction may release at most two blocking existing chains, construct the new chain and reconstruct the displaced chains with the same operator. Commit only a complete valid partial embedding; otherwise restore the incumbent exactly. Blockers are selected by physical obstruction of required-chain boundaries, never by graph labels. This is bounded local displacement, not a restart.

After obtaining a complete embedding, make at most two deterministic sweeps rebuilding one chain with the same tree operator, accepting strict Q reductions only. No independent contact-search method is called. A final safe leaf-pruning pass is part of the tree operator, not a separate output selection.

```text
partial = empty; ownership = empty
while an unplaced source vertex remains:
    v = highest placed-neighbor count, degree, seeded tie
    recompute free ports and remaining-demand congestion prices
    T = connected_tree(v, partial, prices)
    if T fails:
        try one private transaction with at most two physical blockers released
        reconstruct v and all released owners; commit only the complete transaction
    if still impossible or interrupted: return explicit failed partial state
    otherwise commit T and advance
for at most two sweeps:
    rebuild each chain with its own sites released; accept only strict Q decrease
validate the complete original-source/target minor; return timely result
```

Fixed exploratory bounds: 64 root candidates, eight exact path unions, two displaced chains in one transaction per failed insertion, two improvement sweeps, 20 million target-adjacency scans, and the common 60-second deadline. These are workload bounds, not completeness claims. Setup, failed transactions, paths and final validation are inside that deadline. Budget interruption leaves earlier commits intact but a partial embedding is a failure. A completed valid incumbent may survive an interrupted improvement proposal; a late return is still a timeout.

## Self-critique and prior-art caveat

Shortest-path tree construction, congestion prices and rip-up/reroute are established ideas, including in generic routing and CMR-style minor embedding. This prototype does not establish novelty; its concrete hypothesis is whether explicit future distinct-port demand and direct, disjoint tree geometry improve this pipeline's construction quality/cost. It deliberately allows no overlap while routing, which can trap it where temporary overlap or a larger displacement would succeed. Root truncation and shared shortest-path trees can miss a smaller Steiner tree. Growing enough free ports can allocate unnecessarily long chains when future neighbors could be routed through fewer shared regions; prices may repel mutually adjacent future chains. A narrow physical corridor can require moving more than two owners. The two cleanup sweeps do not escape those limitations, and singleton rooted trees are not generally globally optimal.

With h target vertices, e target edges and k already placed neighbors, a full insertion can scan O(k e) adjacency entries for distance searches, plus path-union/growth work; the explicit scan cap bounds all insertions together. Prices cost occupied-boundary scans per insertion. Space is O(k h + e + total chain storage) in the worst case. This is plausibly affordable on 4,800-site Z12 for development graphs around 100 vertices, but the first screen must measure actual time rather than assert MM-scale speed.

## Cheap falsifier and next decision

Use the existing nine fixed exploratory sources in `pilot.make_graphs`, Z12, seed zero, 60 seconds, fresh candidate/MM processes paired on hyde02. They span complete40/100, complete bipartite30+30, ER80, regular80, Watts–Strogatz80, grid64, honeycomb5x5 and king64. These already exposed development inputs are not held-out validation. Preserve every failure, work/deadline stop, ACL and runtime. Reuse the audited pilot's independent original-graph validator and detached lifecycle.

First ask whether construction succeeds and whether sparse ACL is competitive without severe dense regressions or timeouts. Broad failures or uniformly larger ACL will reject this version; one promising isolated case warrants mechanism analysis, not default promotion. Do not extend limits or select a per-input constructor after seeing this identity's outcomes. No claim of across-class superiority or novelty follows from this screen.

## Prototype and first freeze

Implemented as the standalone standard-library module `packages/ember-qc/src/ember_qc/algorithms/factored/demand_construction.py`, SHA-256 `b6d8db1acb620b3d2f1f9127743744bfc44bc8434009554d107ffda64624b417`. Six focused checks pass under an import guard: tiny full minors, a degree-six center requiring multiple sites on a degree-four target, infeasible partial construction, atomic failed displacement, deadline/work interruption, and seed/metadata/insertion-order control. They reuse `pilot.verify_embedding`; this is exploratory evidence, not exhaustive validation. Raw check output and source hashes are in `results/codex/track-b-checks/attempt001`.

A complete construction is fully validated before refinement. Each subsequent accepted replacement preserves contacts to all frozen neighbors and connectivity by the builder's local construction, and the existing pilot independently validates the final output against original graph edges. If refinement hits the work cap, the last complete valid incumbent may be returned within time. A deadline overrun never earns success; failed outputs are empty and retain their partial chains in diagnostics. The whole two-chain displacement transaction is independently validated before commitment.

The paired run `results/codex/track-b-demand-001` freezes all nine panel inputs, methods `mm,demand-tree`, seed0,60seconds and unchanged empty method configuration. Manifest SHA-256 `45e43e29b5c481beec80be27761633f3443f81a8187ecc755efb35e4729575b4`; source snapshot `5f1f54fbad3d7d3eafd048f18e5e457d96780d1832cf5e9a259cfbbc588d6c03`. The target is the original ideal Z12 hash `38cde794d3c1461054a45b5a660d157737b019c19cb9a7b38e2027730e3d5938`. Freeze identities and task order are recorded in `results/codex/track-b-checks/freeze001.json` before any outcomes.

Reproduction/preparation commands:

```sh
.venv/codex-native/bin/python -I -B results/codex/track-b-checks/run_checks.py results/codex/track-b-checks/NEW_CHECK_DIRECTORY
.venv/codex-native/bin/python -B scripts/codex/pilot.py init results/codex/NEW_RUN_ID --methods mm,demand-tree --seeds 1 --timeout 60 --candidate-python /home/dabh/ember-codex/envs/4e1fb892db12754e/native/bin/python --mm-python /home/dabh/ember-codex/envs/4e1fb892db12754e/mm/bin/python
.venv/bin/python scripts/codex/cluster.py --host hyde02 stage results/codex/track-b-demand-001
```

The existing detached cluster lifecycle owns each worker independently of SSH. No restart is allowed merely because observation is lost. Current source changes require a new run identity; do not replace the frozen run.

Before outcome retrieval, root highlighted an explicit limitation: the free-port reserve is checked only for the chain currently inserted. Later insertions can consume another chain's ports. Congestion prices react to this, but there is no global remaining-port-capacity invariant. Failures must distinguish this possibility from root truncation, weighted-distance cost and the finite scan limit. Host readiness reports 32 logical CPUs/affinity0–31; launch load around33 is comparable to that count, so wall timing must retain contention context and CPU/wall measurements.

Focused-check correction: the first author run invoked `pilot.verify_embedding` without asserting its returned reason; that validator reports failures by return value. `attempt002` adds explicit `reason is None` assertions and all six tests still pass. Production source and the frozen screen are unchanged; the weaker first run remains saved. The screen analyzer uses the corrected return-value check.

## Screen 001 result and next decision

The first version is rejected as competitive construction evidence: 5/9 candidate calls succeeded, four failed, and all five timely valid pairs had larger ACL than MM. MM had eight successes and one timeout. The audit rechecked all retained bytes, task/input identities, every returned embedding against the supplied original graph edges, actual Q and timing. Full tables and diagnostics: `results/codex/track-b-demand-analysis/analysis001`; immutable archive: `results/codex/retrieved/hyde02/track-b-demand-001`, digest `acd0b1716f739e727dc195a8c0b65255fcfb08c8d733117664983a17c8c98c0d`.

| Input | Candidate status | Candidate ACL | MM status | MM ACL | Candidate seconds | MM seconds |
|---|---|---:|---|---:|---:|---:|
| complete_40 | FAILURE | — | SUCCESS | 4.8500 | 23.399 | 6.012 |
| complete_100 | FAILURE | — | TIMEOUT | 11.1300 | 39.523 | 66.657 |
| bipartite_30_30 | FAILURE | — | SUCCESS | 3.0000 | 35.061 | 4.385 |
| random_er_80_d8 | FAILURE | — | SUCCESS | 2.6375 | 7.277 | 10.720 |
| regular_80_d3 | SUCCESS | 1.8500 | SUCCESS | 1.1250 | 5.628 | 0.861 |
| watts_strogatz_80 | SUCCESS | 1.6875 | SUCCESS | 1.1750 | 3.298 | 0.812 |
| grid_8x8 | SUCCESS | 1.6562 | SUCCESS | 1.0938 | 2.888 | 0.495 |
| honeycomb_5x5 | SUCCESS | 1.4000 | SUCCESS | 1.0143 | 1.846 | 0.500 |
| king_8x8 | SUCCESS | 1.8438 | SUCCESS | 1.4062 | 15.188 | 1.611 |

The MM K100 embedding was valid but late (66.657seconds against60), so its displayed ACL11.13 is diagnostic only and the pair is not a timely comparison. No failed candidate receives ACL credit. All five successful candidate embeddings are independently valid and timely, but 3.69–9.43times slower than paired MM. There are no wins or ties. This one seed estimates neither across-seed variance nor graph-family population quality.

K40/K100/bipartite stop at exactly20million scans after placing27/22/35 vertices, respectively. These are workload failures, not completed negative searches. Their walls are23.40/39.52/35.06seconds. K40 and bipartite have no negative remaining-port gaps at interruption, whereas K100 has seven (minimum−10). ER80 stops after61vertices with a blocked contact, five negative remaining-port gaps (minimum−2), and one unsuccessful displacement transaction. Every retained partial is itself a valid minor of the placed source subgraph. A negative port gap demonstrates loss of the earlier reserve, not by itself a proof of why the entire continuation fails.

The successful sparse constructions also expose placement rigidity. The rebuilding sweeps save zero qubits on regular/Watts–Strogatz/grid/honeycomb and only one on king. Independent recomputation of paths against fixed neighboring chains does not undo the earlier choice of where those neighbors sit. Larger scan/root allowances would not directly address this measured quality problem.

Host load was around33 on32logicalCPUs. Candidate solver CPU/wall ratios were0.9966–0.99995, so direct CPU descheduling was small in these calls; retain contention context and avoid treating the timing ratios as portable hardware constants. All18 tasks finalized, the controller and detached supervisor completed with exit0, and the lock/tmux session were absent before retrieval.

**Next decision:** do not promote or spend a larger budget on this version. A concrete next hypothesis is to make insertion a joint operation: connect the new chain to existing neighbors through shortest free paths and allow the path sites to extend either endpoint chain, updating their demands together. This changes the frozen-neighbor restriction that the current sweeps could not overcome. Search can use one multi-target expansion from the current partial chain instead of separate full distance maps to64roots for every demand. This is a future single-constructor revision, not a portfolio or an authorized outcome-selected per-input choice. It needs its own concise pre-code specification/self-critique and unchanged nine-input screen before implementation. No second run is launched here.

Reproduce the saved-output screen, without calling any solver:

```sh
.venv/codex-native/bin/python -B results/codex/track-b-demand-analysis/analyze.py results/codex/retrieved/hyde02/track-b-demand-001 results/codex/track-b-demand-analysis/NEW_OUTPUT_DIRECTORY
```
