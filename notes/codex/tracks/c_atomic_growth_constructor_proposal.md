# Controlled next discriminator: atomic free-path addition

**Hypothesis.** The variable-region representation admits the saved triangle completion, but its elementary growth must cross two positive-energy intermediates and can be undone by scheduled deletion. One atomic contact-completing path may make useful growth admissible under the **unchanged** energy, rather than increasing time or tuning temperature. This tests addition granularity against the [failed elementary policy](c_variable_occupancy_constructor_results.md); it is not another supplied-state repair run.

**Exact proposed change.** Keep singleton initialization, source/target orders, missing-edge/endpoint choice, swap/transfer/deletion definitions, `E=M+Q/(1+d)`, T=0.5, four-operation cycle, 4|H| visit cap, and all common deadline/cleanup/final-gate rules. Replace only an addition visit:

```text
Choose missing (u,w) and orientation using the existing draws.
Enumerate/shuffle u's free boundary exactly as the elementary visit.
Order roots by the existing full-target distance and shuffled rank.
Run one multi-source BFS through currently unused full-target sites;
stop at the first site adjacent to w, with target neighbors in rank order.
If no path exists, record an empty addition visit; try no alternate path.
Privately score assigning the entire recovered path to u, including all
incidental original contacts; ΔQ is the path's number of unused sites.
Apply the unchanged acceptance rule to its exact ΔM + ΔQ/(1+d).
On acceptance, commit all path sites and contact/version bookkeeping
atomically; never expose a partially added path after interruption.
```

There is one scored path, within the existing sixteen-score ceiling. All frontier, distance-cache, BFS, scoring and private-copy work is charged. Chains remain connected/disjoint; additions retain existing contacts. The original destination-chain version governs the distance cache. No owned-site traversal, source-family branch, path portfolio, reserve constraint, fallback constructor or extra search cap is introduced. The RNG rule remains unchanged: a positive selected energy draws once, a nonpositive energy draws none. Consequently trajectories can consume different later random draws after the first differing proposal; this is an explicit confound, not an exact random-stream replay claim. Before that point their initialized state and directed choices must agree.

**Self-critique.** Atomic paths are established embedding operations; novelty is unproved. This larger neighborhood can use too many sites, consume future access and fail at sealed endpoints, as C's earlier routing-only diagnostics showed. Here label swaps, transfers and deletions remain available during construction, so those diagnostics do not determine the full trajectory. Better completion may still lose badly on ACL. A changed path-search cost and later RNG trajectory also prevent interpreting a quality difference as a pure energy experiment.

**Cheap full-construction falsifier.** First check exact multi-site contact/Q deltas and interrupted atomic rollback. Then repeat exactly the same four seed-0, five-second full-constructor gates. Require the same optimal path/star outputs, the Q6 cycle completion with an actual atomic growth commit, and no credit on triangle→path3. Save the first differing proposal's energy and every failed/censored call. If the growth gate still fails, stop this variant. If all pass, promptly request the existing diverse eight-input, seed-0, fifteen-second same-host paired-MM screen; do not add a sequence of supplied-state repairs or further tiny tuning. **Proposal only; no implementation or call authorized yet.**
