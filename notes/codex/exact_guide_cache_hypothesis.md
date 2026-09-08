# Exact per-owner guide-distance reuse

Design only, after the saved repetition observation and before any implementation. Frozen A052 remains unchanged. Its four reach receipts contain77 repeated `(guide,size)` queries out of171, but do not save the site sets needed to establish cache hits.

**Hypothesis.** Some repeated queries use the same guide chain on the same immutable target. Retaining their complete distance map can avoid repeated full-target BFS without changing any distance, rank or physical move. This addresses implementation cost only; it does not repair the wheel's quality regression or establish overall promotion.

## Exact proposed contract

Use one lazy cache owned by one A052 constructor call. The engine's normalized target adjacency is immutable for that call; do not share across calls, targets, source identities or processes. Retain at most one entry for each guide owner:

```text
cache[owner] = (exact sorted tuple of current prepared chain sites,
                read-only complete target-distance map)
```

At every guided insertion, construct the key from the **actual prepared** chain, including inside a private repair. Charge one inherited scan per enumerated site and preserve the original deadline through sorting and equality/lookup. Choose the guide by the unchanged rule before lookup. Compare exact tuples, never owner/length/hash alone; ordinary dictionary hashing may locate an entry, but full equality establishes reuse. No-guide calls perform neither key work nor BFS.

On an exact match, return the retained read-only map after a deadline check. On any mismatch, run the unchanged complete BFS with its original seed/edge charges, then admit that completed map under the new key. An interrupted BFS does not publish a partial map or evict the prior completed entry. A clock check immediately precedes cache admission and use. Wrapping a privately owned completed dictionary in a read-only view avoids an additional whole-map copy; no mutable map reference may escape to code that can alter it.

This is **lookup invalidation**, not incremental distance maintenance: any changed site tuple misses, including same-size swaps, shrinkage, growth, or relocation. All accepted ordinary/core/repair moves are covered because the next lookup reads current ownership rather than trusting a stale generation counter. Private failed branches may have computed maps for placements never adopted; retaining such a pure target/seed result is mathematically safe only because every subsequent use rechecks the exact seed tuple. With one entry per owner it may evict a more useful map, which is a performance limitation, not a validity exception.

The distance depends only on immutable target edges and that seed set. It is independent of other chains' occupancy, pending demands and the current source requirement graph because A052's BFS deliberately ignores occupancy. Those other changes still affect all inherited ranking and physical-feasibility work normally. No guide choice, cap, key position or candidate selection is changed.

## Accounting, memory and falsifier

Keep the same global/repair scan limits and absolute deadline. Add explicit cache lookup, hit/miss, key-site work and wall fields; preserve actual BFS scans/calls separately. A hit reports zero BFS work, not its hypothetical avoided scan count. Key creation, equality, queue disposal, cache admission and eventual cache lifetime remain in elapsed time. A diagnostic “avoided BFS” estimate must be separate from performed work. The cache consumes `O(number of guided owners × target vertices)` space, potentially much more than one BFS map; report retained entries/site values and peak. The first prototype does not claim a constant memory bound or introduce an unreviewed eviction parameter.

Before a candidate run, use a few fixed checks: identical site tuples hit after unrelated occupancy changes; same-size different sites miss; growth/shrink and private rollback cannot reuse the wrong map; interrupted key/BFS/admission retains entry and the previous complete cache; returned maps cannot be mutated. Compare a hit's map directly with a fresh independent tiny-target BFS. Include live repair-limit charging.

If authorized after those checks, replay exactly the four frozen A052 reach inputs once with the cache, same seed and20-second/20M limits. Require identical final embeddings and ranking/decision receipts wherever the saved A052 run was nonbinding. Report actual hit rate, key costs, BFS reduction, peak storage, total work/time and all failures. The optimistic77 repeats may produce fewer true hits. If no meaningful net cost reduction appears, or correctness/equality fails, reject the prototype rather than changing ranks or capacities. A gain in this small replay is not a same-host paired runtime claim against the earlier measurements.

**Self-critique.** Guided owners can change sites often, and small chains still require exact comparisons. Saved owner/size repetition may overstate hits. Full maps can retain substantial memory or incur allocator/cache pressure. Lower scan use can change the reachable search prefix when a work/deadline limit binds, so equal outputs are only expected under nonbinding conditions; such differences need honest reporting. This is conventional exact memoization of a pure BFS function, not a new embedding mechanism or novelty claim. Parent review is required before implementation; frozen052 is never altered in place.
