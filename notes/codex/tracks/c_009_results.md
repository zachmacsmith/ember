# C009: connected-domain constructor — retire

C009 achieves **0/8 timely valid embeddings**, versus stock MM's **6/8**. It fails the fixed six-completion/three-Q-win-or-tie/runtime rule and is retired. There are no common valid pairs, so candidate ACL comparisons and the required median runtime ratio are undefined. All eight candidate returns are explicit **FAILURE**, with no fatal exception, at the nineteen-million search-work cap; final recount/output brings total charged work to 19.007–19.022 million. None reaches the fifteen-second wall allowance or obtains a valid incumbent.

Candidate cells show diagnostic **Q / missing original edges / overlap excess**, followed by solver seconds. These are incomplete assignments, never credited embeddings. E/R counts completed epochs/committed regeneration batches. MM cells show valid Q/solver seconds; **late** maps are valid but uncredited. Full ACL/process/status data are in the [sixteen-row table](../../../results/codex/track-c-009-review/analysis001/table.csv).

| Input | Candidate Q/M/O; seconds | E/R | MM Q; seconds |
|---|---:|---:|---:|
| Path | 209/26/0; 4.414 | 3/2 | 141; 0.173 |
| Tree | 240/6/1; 4.235 | 4/3 | 121; 0.132 |
| Grid | 190/144/2; 4.069 | 2/1 | 134; 0.352 |
| Planar | 152/403/0; 3.933 | 1/0 | 281; 0.592 |
| ER | 133/805/0; 3.979 | 1/0 | 1044; 8.389 |
| Regular | 140/2684/0; 4.194 | 1/0 | late 2481; 15.394 |
| Complete | 127/7758/11; 4.585 | 1/0 | late 2170; 17.382 |
| SBM | 120/576/0; 4.044 | 1/0 | 638; 4.127 |

The [receipts](../../../results/codex/track-c-009-review/receipt_summary.json) identify **generation cost**, not merely dense probability arithmetic. Candidate solver time totals 33.455 seconds: domain generation consumes 24.977 (74.7%), coordination 5.131 (15.3%), and initialization 2.549 (7.6%). MM solver time totals 46.542 seconds, including its two late returns; failed candidate times establish cost, not speed superiority. Candidate/MM process totals are 35.561/48.637 seconds.

Only fourteen of forty-eight possible epochs and six regeneration batches complete. The five inputs with no committed regeneration remain at singleton domains despite partial generation work for 94,42,14,3 and57 owners respectively. Their outcomes are censored tests of non-singleton coordination. The complete input spends 8.439 million units on probability work; other failures spend most charged work in routing. Counts separately include adjacency traversal and neighbor ordering, rather than pretending both are unique edge examinations. Across inputs, 4,657 root constructions report support against every neighboring **old domain list**; seven routes are interrupted. That local support does not guarantee a compatible new library or full selection.

The small-input evidence is also limited: path missing edges fall 118→44→26 while Q grows 141→169→209; tree ends with six missing edges and overlap. Path's last library reports pairwise support for every original edge, yet the selected map is invalid. This cannot distinguish globally inconsistent domains from approximate selection failure. The known-feasible primitive fixture does not settle that corpus question, and no domain CSP or unsaved trajectory was solved.

The [approved auditor](../../../results/codex/track-c-009-review/analyze.py) ran once, passed with zero errors, verified the archived file map, and independently recounted original-label final/diagnostic contacts, connectivity, Q and overlap. The original auditor and additive error-credit correction are preserved. [Final bindings](../../../results/codex/track-c-009-review/review_manifest.json) include every failure. No constructor rerun, parameter adjustment, held-out confirmation, variance estimate or novelty claim follows.
