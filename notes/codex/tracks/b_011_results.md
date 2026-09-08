# B011 development results

B011's connector filter recovers the diagnosed insertion in the full trajectory, but does not improve final completion or ACL. Six candidate calls succeed and three fail, exactly as in B009. All six completed qubit totals are unchanged. Fresh MM comparisons still contain two wins, on optimal grid and honeycomb embeddings, and four losses.

| Input | B009 → B011 outcome | Fresh MM Q | B011 seconds | B011/MM time |
|---|---:|---:|---:|---:|
| complete 40 | failed, 32 → 24 placed | 194 | 14.68 | — |
| complete 100 | failed, 35 → 34 placed | late | 50.86 | — |
| bipartite 30+30 | 330 → 330 Q | 180 | 40.24 | 5.80× |
| ER 80 | failed, 63 → 64 placed | 211 | 16.47 | — |
| regular 80 | 110 → 110 Q | 90 | 10.78 | 13.86× |
| Watts–Strogatz 80 | 133 → 133 Q | 94 | 18.60 | 10.09× |
| grid 64 | 64 → 64 Q | 70 | 4.22 | 3.60× |
| honeycomb 70 | 70 → 70 Q | 71 | 5.37 | 6.45× |
| king 64 | 128 → 128 Q | 90 | 13.00 | 5.27× |

All complete outputs and retained partial minors validate on original graphs. The run is quiescent, with all 18 tasks finalized and all 178 archived file hashes verified. The late K100 MM embedding is valid at 1,121 qubits but returns after 70.95 seconds and receives no timely credit. K100's candidate stops at the unchanged 20-million-unit allowance; the other candidate failures are blocked insertions.

ER's first 63 construction-order entries and committed-update records exactly match B009. B011 then inserts vertex 35, producing the exact 64-chain/218-qubit minor previously found in the supplied-state check. This is direct evidence that the local recovery survives the evolving trajectory. The next vertex, 66, needs placed neighbors 31, 67, 72 and 78 and blocks. The recovered insertion therefore shifts the obstruction rather than completing the graph. ER stops at 8.20 million units, well below its global work allowance.

The filter runs 3,007 times, consuming 155,203 counted units and 0.658 seconds total. Every filter computation finishes; 2,760 site exclusions are recorded across queries, counting repeated exclusions separately. Matching, growth and global accounting reconcile. The filter excludes no sites on regular, Watts–Strogatz or king, and is never invoked on grid or honeycomb. Its measured bookkeeping cost is small, but changed greedy paths make the dense partial outcomes worse. Load remains approximately 33–34 on 32 logical CPUs, and cross-run wall differences cannot be attributed solely to the filter.

Do not promote B011 as an overall improvement or raise its caps. Preserve the endpoint-safe exclusion rule and its actual recovery witness. The remaining problem is how to respond when preserving future contacts requires changing an already committed chain or preparation decision; repeatedly choosing a different feasible connector is not a general completion strategy. No such next candidate is included in this screen.

Details: [pre-code rule and critique](b_port_aware_routing.md), [obstruction and witness](b_010_frontier_results.md), [all fresh pairs](../../../results/codex/track-b011-analysis/analysis001/pairs.csv), [raw observations](../../../results/codex/track-b011-analysis/analysis001/rows.json), [filter/matching/growth accounting](../../../results/codex/track-b011-analysis/analysis001/port_summary.json), [freeze](../../../results/codex/track-b011-checks/freeze.json). Reproduce using `track-b011-analysis/analyze.py ARCHIVE NEW_DIRECTORY`, followed by `summarize_ports.py NEW_DIRECTORY`; neither calls a solver.
