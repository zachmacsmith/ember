# B007 hypothesis: promotion must use future domains when growing a chain

Pre-code design, 2026-09-08. B005/B006 promotion permits multi-qubit chains, but its tree primitive can immediately choose another singleton that recreates the detected future-domain conflict. The first such promotions in ER, Watts–Strogatz and king do exactly this. B007 will test whether modest extra chain growth before commit can preserve the remaining singleton assumptions. It will retain B006 reuse only if the separate B006 screen supports it.

```text
For a promoted vertex v, construct the usual valid private partial insertion T.
Rebuild future domains using T; never retain domains from before this insertion.
If a remaining singleton domain is empty:
    for at most four connected growth steps:
        compute relaxed future domains omitting only the v-contact restriction,
            while keeping all currently occupied sites unavailable
        rank free neighbors of C[v] by distinct future-neighbor domain coverage,
            then free extension space and deterministic physical rank
        test at most four sites as one-site connected extensions:
            rebuild and propagate the actual future domains
            return the first extension whose pass completes with no empty domain
        otherwise continue privately from the best tested unresolved extension
If no growth resolves the conflict within the limits, discard growth and retain T.
Commit through the unchanged final deadline gate; keep only one evolving minor.
```

The unresolved-extension ranking first minimizes empty-domain count, then prefers larger sorted domain cardinalities. Every logical neighbor contributes one set of distinct possible physical sites; repeated couplers to a site do not create independent capacity. This is still a heuristic: nonempty arc-consistent domains do not establish global injectivity or a full completion. A relaxation whose domains are already empty without v's contact restriction cannot be repaired by merely enlarging v while reserving more sites; discard that growth query.

Growth adds only free sites adjacent to C[v], preserving connectivity, disjointness and every already required contact. Existing chains are frozen during growth, including any changes made in T by its initial insertion. Invalidate all carried domains after any growth, even if a later trial is rejected; a subsequent complete computation can establish new eligible domains. A completed grown proposal can have higher current Q than T: that is the intended feasibility investment, which B004's local strict-Q acceptance never permitted.

Bound each growth query to 500,000 counted units, all growth queries to three million, inside the existing 20-million global units and 60-second deadline. Propagation keeps its existing sublimits. Growth and propagation counters overlap and must not be added as independent work. A local limit discards unresolved private growth; deadline/global failure preserves the last committed partial minor. No restart, independent constructor, family rule or comparator output is used.

Cheap witness: source triangle and a target four-cycle. A first chain [0] leaves both future domains {1,3}, with no support for their mutual edge. Growing it to [0,1] yields domains {2,3}, allowing the valid four-qubit minor. Add a frozen required neighbor at physical site 4 adjacent to 0 to verify that growth preserves an existing original-source contact. Tests must exercise the actual feedback/selection rule, original-graph validation, rollback and domain invalidation; no broad exhaustive suite is planned.

Self-critique: the best local extension may lead away from the necessary bridge or consume another variable's only site. Four steps cannot resolve distant conflicts, and incomplete propagation cannot certify resolution. Choosing another initial root may be more useful than growth, but this experiment deliberately isolates growth feedback. Dense inputs whose remaining vertices all need chains have no singleton-domain information to preserve and may remain unchanged. The mechanism is conventional constraint-guided growth, with no novelty claim.

After targeted checks, use the same nine fixed inputs, seed 0 and fresh MM pairs. Falsifier: no reduction of promotion cascades or final Q/completion loss, or extra work overwhelms the benefit. Preserve increased-Q decisions, failed growth, regressions and all limits. This hypothesis is separate from B006's performance-only reuse test; no B007 code or run exists at this point.
