# Track B005: propagated singleton assumptions with connected-chain relaxation

2026-09-08. Saved before code. This implements option 1 of `b_feasibility_options.md`, not B004's rejected reinsertion schedule. One evolving partial minor E remains the only committed embedding. A persistent set P marks unplaced variables allowed connected chains. Initially P contains source vertices with degree exceeding the maximum target degree, a mathematical singleton exclusion. Promotions add to P; they do not restart E.

For each other unplaced vertex u, rebuild D[u] from all free physical sites intersected with the boundary of each already placed neighbor chain. On a logical edge between two such variables, apply the exact singleton revision D[u] ← D[u] ∩ N_H(D[v]). A site lacking any physically adjacent value for v cannot participate in an all-singleton completion under these current assumptions. This does not prove minor infeasibility. Compute N_H(D[v]) as a union of physical adjacency bitsets, cached by D[v] within that propagation call. Never use a partially computed union to delete values.

```text
E = empty; P = {u: source_degree(u) > maximum_target_degree}
while vertices remain:
    rebuild all singleton domains from current E and current P
    run a bounded arc-consistency queue on edges whose endpoints have domains
    if some domain is empty:
        promote its vertex (highest degree, then seeded tie); rebuild domains
    else if an unplaced promoted vertex exists:
        choose it by most placed neighbors, degree, seeded tie
        use the B003 connected-tree insertion primitive, once, with ordinary alternatives
    else:
        choose u by smallest domain, most placed neighbors, degree, seeded tie
        rank its values by lexicographically larger sorted neighbor support counts,
            then more free physical neighbors, then seeded physical rank
        test at most four values privately:
            stage singleton u; preserve the extension frontier
            rebuild remaining domains and propagate
            accept first value with no empty remaining domain and a valid partial minor
        if none succeeds: promote u and rebuild from unchanged E
    after each committed insertion, rebuild domains from scratch on next iteration
```

Old chains may grow or shed sites through the same connected-tree primitive when a promoted vertex is inserted. All previous domain deletions are therefore discarded on the next iteration. Likewise every promotion resets domains because its removed singleton constraints may have caused earlier deletions. Value trials are private and do not mutate E or the persistent promotion set. A finite four-value limit can cause unnecessary promotion; that is heuristic incompleteness, not an infeasibility certificate. Promoted vertices are selected before remaining singleton variables, making newly detected empty-domain conflicts immediate construction obligations.

The maximum counted work remains 20 million units, but its meaning is now explicit: an inherited adjacency scan, a domain-neighborhood bitset union, a directed arc revision, or one candidate-neighbor support test counts one unit. This is not numerically comparable to B003's pure adjacency-scan counter. Record propagation and value-support counters separately. Propagation has a fixed 200,000-unit allowance per call and five-million-unit total inside that common limit; remaining tree/value/validation work uses the same global limit. A propagation allowance interruption returns the soundly revised prefix with `complete=False`, never an arc-consistency claim. A partially computed neighborhood union is discarded. Cache at most 256 neighborhood masks per propagation call; deterministic eviction affects cost, not the mathematical revision. Every stage uses the same 60-second absolute deadline.

If propagation stops before convergence, nonempty domains can still contain unsupported values. They are provisional placement information; every actual insertion must independently preserve the minor conditions. An empty domain after completed sound revisions remains evidence against the current singleton assumptions even when other arcs remain unprocessed. Global work/deadline interruption returns only the last committed valid partial minor, with failure/timeout. No new embedding library, global exact solve, family dispatch, restart or competitor output is used.

Cheap checks before the same nine-input screen: a hand-built domain pair where all domains are nonempty but one candidate value has no physical support, while another does; confirm exact removal and retained feasible assignment. Force interruption halfway through a neighborhood union and confirm no unsound value deletion. Require an actual valid source-star embedding on a target of smaller maximum degree, exercising connected-chain promotion. Retain input/metadata determinism and original-graph validation. A positive toy establishes only the propagation rule's mechanism.

Self-critique: arc consistency ignores global injectivity conflicts among three or more variables, and its assumptions exclude completions requiring future chain growth. Promotion repairs that logical scope but can abandon useful singleton search early. The source-degree rule promotes all vertices of both complete-graph development inputs, so the current dense weakness can remain unchanged. The bounded queue may spend substantial work pruning nothing; union caching is an efficiency hypothesis, not a speed claim. Largest-support value ordering can reserve room in the wrong part of the target. Constraint propagation and connected-tree routing are established techniques; publication novelty is not claimed.

Freeze seed 0, 60 seconds and the unchanged nine development graph/target bytes, with fresh candidate/MM pairs on hyde02. All failures and time limits remain in the result. Falsifier: no final-Q improvement over B003 on the affected singleton-capable cases, or propagation consumes enough work/time to erase its practical benefit. Even a sparse success with unchanged dense failures falls short of the project objective. Do not choose outputs between this constructor and earlier B versions per input.


Implementation: standalone `factored/propagating_construction.py` (source SHA-256 `869998b75ccf7e1315e3569cd105d41c8ba2f4ff202cf971249aab5b82da47bf`). Domain rebuilding charges source-adjacency entries to the global limit; the propagation suballowance covers the queue and neighborhood unions. This distinction is explicit in separate counters. Eleven guarded targeted checks pass at `results/codex/track-b005-checks/attempt002`; the earlier ten-check pass is retained. The added check derives both domains from a valid original-graph partial minor and completes its remaining two singleton chains. No corpus result has been observed at this point. Detailed code/test hashes are recorded by the check runner; production files from previous experiments remain unchanged.


The frozen run is `results/codex/track-b-propagating-005`; exact source/task/input identities are in `results/codex/track-b005-checks/freeze.json` and the run manifest. All nine graph bytes and the target match B001–B004. It was staged and launched once on hyde02 using the existing detached supervisor. The initial sandbox DNS staging failure is retained in `stage-attempt001.json`; it occurred before any experiment invocation. No source or setting changes are made after launch.
