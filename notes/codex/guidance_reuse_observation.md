# Saved A052 guide repetition

Read-only analysis of the four already completed A052 reach calls finds repeated guide identities, but does not prove exact distance-cache reuse. No candidate, source generator, converter or new embedding call ran.

Every saved BFS completed on connected ideal Z12. The target has91,728 directed edge incidences, so `BFS scans − 91,728` independently yields its number of guide-chain seeds. All inferred sizes are positive. Owner/count and `(owner,size)` frequency tables, each individual receipt and input hashes are preserved under `results/codex/a052-guidance-reuse-observation/analysis001`.

| Input | BFS calls | Distinct guide owners | Adjacent same-owner records | Repeated owner/size pairs | Associated BFS scans |
|---|---:|---:|---:|---:|---:|
| Star128 |0|0|0|0|0|
| Wheel128 |84|49|1|35|3,210,515|
| Subdivided K5 |4|1|3|3|275,187|
| Cycle126 |83|44|4|39|3,577,431|
| Total |171|94 across separate calls|8|77|7,063,133|

The77 repeats are45.0% of queries. They also match the most recently queried size for that owner, so one entry per owner has the same optimistic count here. A single globally most-recent map could cover at most eight of these records. “Adjacent” refers only to saved BFS records; unguided insertions may intervene.

The repeated-pair scans are45.0% of15,685,665 total BFS scans. Their associated saved wall is4.318s of9.533s. **These are potential-work upper bounds, not measured cache hits or predicted speedups.** Equal owner and size does not establish equal occupied sites, and exact key construction, lookup and retained-map storage have costs. No reuse is counted across the four separate constructors. Repetition is sufficient to justify the separately written exact-cache hypothesis; it does not justify changing frozen052 or assuming end-to-end savings.
