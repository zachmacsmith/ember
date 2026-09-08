# B009 hypothesis: require distinct singleton placements

Pre-code specification, 2026-09-08. The fixed comparison ancestor is B007, including its domain reuse and bounded growth. B008 found completed, nonempty domains with certified Hall deficits before early promotions. B009 changes one feasibility criterion: accepting a private singleton placement or extra promoted-chain growth requires completed propagation **and a covering bipartite matching** of remaining unpromoted variables to distinct free sites. This remains necessary, not sufficient, for their eventual simultaneous singleton embedding.

```text
For each private singleton trial:
    rebuild/propagate its remaining domains
    reject empty or incomplete propagation
    compute bounded maximum matching; accept only completed covering results
For ordinary promoted-chain insertion T:
    if actual future domains and matching are complete and covering, retain T
    otherwise use the existing four-step, four-site connected growth search
    discard a relaxed domain state if its completed matching proves a deficit
        (relax only this chain's contact condition; growth otherwise removes sites)
    rank tested extensions by completed matching deficit, then domain sizes
    adopt extra qubits only after completed propagation and covering matching
    discard unresolved private growth and retain valid T at the existing deadline gate
```

The initial frontier-site shortlist remains B007's distinct-domain ordering; matching-deficit ranking applies to its actually tested extensions. Unknown matching results cannot authorize acceptance or rank ahead of a completed result. A per-query limit rejects that private alternative; it is not a proof that the graph or even the current singleton model is infeasible. If no singleton trial succeeds, the existing heuristic promotion remains available and is recorded with rejection reasons. Exhausting the total matching allowance stops construction with its last committed valid partial minor.

Use deterministic augmenting paths, standard-library only, with 100,000 counted units per query and two million total inside the unchanged 20-million global budget and common 60-second deadline. Charge inspected domain edges, queue visits and matching updates; record matching scans, work, status and wall separately. Matching, propagation and growth counters can overlap; do not sum them as disjoint work. Growth still has four steps/four trials, 500,000 units per query and three million total. Matching interrupted by growth/global/deadline limits propagates that interruption and cannot leave an accepted private proposal.

Targeted checks: an arc-consistent Hall collision rejected at singleton acceptance; an actual connected growth that restores distinct assignments; frozen original-contact preservation; exact matching work/deadline and rollback behavior. Reuse B008's independent assignment/witness check rather than another exhaustive suite. Then freeze the same nine development inputs, seed 0, fresh MM pairs on hyde02; compare B009 with B007 explicitly and retain every failure, regression and limit.

Self-critique: covering matching ignores logical edges between future variables and can favor a poor geometric commitment. Rejection may merely promote vertices earlier, and high-degree vertices excluded from singleton domains receive no benefit. The same four frontier alternatives may all be bad; matching does not supply better roots. More expensive consistency can also consume useful construction work. This is conventional all-different reasoning, with no novelty claim. Falsifier: early collisions disappear but final Q/completion does not improve, or added work makes the pipeline impractical. No larger caps, outcome-based policy selection or alternate constructor is included.

Implementation evidence: the separate `propagating_matching_construction.py` follows this policy. Six focused test groups pass, including the actual three-leaf/two-site Hall collision, growth that opens a third distinct site, required frozen contact preservation, independent tiny assignment optima, exact query-cap completion, total-work/final-deadline interruption and rollback. Matching work records include interrupted queries; accepted growth records explicitly retain zero deficit and completed propagation. No development-panel output has been observed for B009 at this point. Source/test identities and raw test output are under `results/codex/track-b009-checks/attempt001`.
