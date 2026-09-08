# B011 hypothesis: exclude impossible connectors before routing

Pre-code specification. The ancestor is exact B009. Its ER blocked-state diagnostic finds an admissible alternative connector, while three traced branches repeatedly choose a path through two unrelated owners' sole free port. B011 changes only this necessary-condition filter inside the existing path search. All root limits, matching/growth rules, deadlines and work allowances remain fixed.

For the current private chains, new chain v and missing contact owners M, let P(q) contain every owner u other than v whose sole free boundary site is q and which still has an unplaced original-source neighbor. A connector site q is unusable for every currently eligible two-ended cut if `|P(q)| > 1`, or if `P(q) = {u}` with `u not in M`. Such a cut assigns new sites only to v and one terminal w. Any protected third owner stays unchanged and loses its last frontier. When P(q) contains only an eligible terminal, retain q: assigning it to that terminal can expose a new frontier.

```text
At each path query, reuse its freshly computed ownership/boundary/free state.
Collect sole-port owners with future demand, excluding the new chain.
Build the universally unusable-site set using the rule above.
Run the existing weighted Dijkstra search, skipping those free sites.
Keep existing terminal selection, ownership cuts and final validation unchanged.
Recompute the set at the next query after any adopted ownership cut.
```

This filters only sites unusable for **every** currently missing terminal. A site allowed for terminal u might still yield a shortest path to another terminal; existing cut validation handles that remaining incompleteness. No terminal-specific searches, restarts or extra path attempts are added. Existing roots already undergo the unchanged frontier check.

Charge each inspected owner and scanned source-neighbor obligation inside the current global work limit, record those counts separately, and check the common deadline during setup and the existing search. Deriving the set costs at most O(placed vertices + their source-adjacency entries) per path query; the target boundary bitsets already exist. Sorting/tiny set operations remain charged to elapsed time. This is a necessary pruning rule, not a claim of identical trajectories or equal wall time under binding limits.

Targeted checks: two protected owners at one site; the unique eligible-terminal exemption and its valid ownership cut; recomputation after a frontier changes; deadlines and entry nonmutation. Test the actual saved ER insertion once under the normal unchanged allowance, with independent physical validation and all work retained. If these pass, freeze the same nine exposed inputs, seed 0, fresh MM pairs on hyde02, and compare directly with B009.

Self-critique: this detects only singleton free boundaries. Longer connectors may jointly exhaust a multi-site boundary; allowed sites can impose inconsistent terminal requirements. Filtering one dead route may select another dead route, and protecting frontiers does not settle competition among future vertices. Added bookkeeping can displace other work. The current two-ended cut cannot relocate a third owner, so its impossibility certificate is local to that primitive. Falsifier: supplied-state recovery fails, or the full panel loses completion/quality or useful runtime despite the local witness. No novelty claim or automatic cap increase follows.
