# Track C003: target coarsening with global connected-region reconfiguration

This is a substantially revised constructor, specified before implementation. C001/C002 failed on all eight inputs. C002's saved allocation already lacks enough physical boundary couplers to represent the required original source edges on six inputs. Its fixed region boundaries are therefore removed from the new mechanism.

**Hypothesis.** Build a relatively dense physical quotient by repeatedly contracting adjacent target regions of similar size, preferring fewer connecting couplers among equally sized partners. Such light-edge contractions destroy fewer available inter-region couplers than compact heavy-edge merging. Once the target has one connected region per source vertex, assign source labels structurally and optimize the entire quotient. Two proposals act on one evolving state: exchange the source labels of two complete regions, or transfer a boundary target site between regions while preserving donor and recipient connectivity. Transfers may cross any earlier coarsening boundary. Missing original source edges, not boolean coarse edges, define the objective. No chains overlap; there is no demand-priced tree routing or independent construction portfolio.

```text
read exact original source/target adjacency under absolute deadline D
coarsen the largest connected target component to n connected regions:
    match small neighboring regions; among equally sized partners prefer fewer couplers
    never exceed the number of merges needed to leave n regions
assign high-degree / already-constrained source vertices to compatible available regions
build exact source-indexed physical coupler counts and the missing-original-edge set
while an original edge is missing and construction allowance remains:
    select one missing edge (u,w)
    alternate fixed proposal types on this same current state:
        exchange region labels u and a candidate region adjacent to w
        or transfer a safe boundary site into u, guided by target distance toward w
    score the exact change in missing original edges
    accept an improving/neutral proposal, or a bounded-temperature uphill proposal
    update exact coupler counts and invalidate affected connectivity/distance caches
if missing edges remain: return explicit failure or timeout and partial-state diagnostics
validate the first complete minor against original edges
delete unnecessary sites, reserving time for final validation/private output
validate the final mapping and reject late success
```

Coarsening, source assignment, all proposal generation, rejected work, BFS distance calculations, connectivity calculations, state copies, cleanup and validation share one solver clock. Imports follow the pilot convention and remain in process time. A fixed final-validation reserve of `min(0.5 seconds, 10% of timeout)` may stop search or cleanup early; it does not extend D. If cleanup reaches that reserve after a valid minor exists, keep the current valid minor and perform the common final validation. Failed calls never claim a valid embedding from a merely complete ownership partition.

The initial policy uses one seeded RNG, at most eight structurally eligible label-exchange partners, and at most sixteen nearest eligible boundary-site proposals per visit. It alternates the two move types, accepts nonincreasing missing-edge count, and uses constant temperature 0.5 for positive missing-edge changes. These are fixed initial search choices, not fitted parameters. Target-distance guidance ranks boundary transfers but does not route a path or release an entire chain. Failed/neutral moves and cache reconstruction costs are recorded. No architecture coordinates, family labels, cached embedding, global integer program, external embedder, or per-input method selection is used.

**Self-critique/prior art caveat.** Graph contraction, graph matching, simulated annealing and connected partition moves are established techniques; novelty cannot be claimed merely by combining their names. The specific hypothesis is that light-edge target coarsening plus freely movable disjoint regions supplies useful minor construction while preserving exact original edge multiplicities. It needs a focused prior-art comparison if results warrant one. The initial quotient may still be too local or sparse, and a single-site move can be trapped by donor articulation structure. Allocating the entire target also risks long chains and costly cleanup. Coupler availability is necessary but does not ensure that a good source assignment exists. Unlike C002, the state can now escape a deficient allocation by changing old boundaries; whether the proposed moves do so fast enough is an empirical question.

**Cheap falsifier.** First independently recount coupler/missing-edge changes after tiny label exchanges and safe/unsafe site transfers; test connected/disjoint ownership, original-edge validation, and late output handling. Then use the same C001/C002 eight readiness sources, ideal Z12, seed 0, 15 seconds per method and hyde04 environments. Compare one fixed C003 configuration with fresh stock MM in separate paired processes. Preserve all failures and both solver/process wall time; late valid MM quality remains diagnostic. Fewer than four timely valid candidate embeddings rejects this initial mechanism for general construction. A successful constructor with universally much worse Q calls for a different compactness mechanism rather than a paper claim. No held-out graphs are generated or inspected.
