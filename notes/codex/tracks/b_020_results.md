# B020: reject both complete contact constructors

**Paired and single-primary contact construction both failed on all nine inputs.** Stock MM returned eight timely valid minors; K100 returned a valid Q1113 embedding at 64.211 s, receiving no credit under the 60 s limit. The frozen analyzer ran once and passed all 27 records, including independent original-graph checks and exact saved initial/final Q/O/energy. No constructor was rerun.

All candidate initial states were overlapping and exactly equal across arms. Every final candidate state remained overlapping; their output mappings were empty. The table shows overlap excess O, **not embedding quality**. All candidate solver times were 59.010–59.083 s, ending at the unchanged search deadline before the final reserve.

| Input | Initial O | Paired final O | Single final O | MM Q / solver s |
|---|---:|---:|---:|---:|
| K40 | 49 | 49 | 49 | 194 / 11.215 |
| K100 | 169 | 169 | 169 | timeout / 64.211 |
| Bipartite30+30 | 69 | 69 | 69 | 180 / 3.281 |
| ER80 | 123 | 107 | 105 | 211 / 4.089 |
| Regular80 | 107 | 71 | 73 | 90 / 1.076 |
| WS80 | 125 | 82 | 98 | 94 / 1.013 |
| Grid64 | 86 | 54 | 68 | 70 / 0.419 |
| Honeycomb70 | 88 | 45 | 53 | 71 / 0.607 |
| King64 | 95 | 78 | 83 | 90 / 1.721 |

**Neighborhood and cost.** Paired completed 1,859/2,349 queries (79.1%); single completed 2,869/3,487 (82.3%). Their query-work-limit counts were 481 and 609, plus nine final search-deadline interruptions each. Almost all interruptions occurred while building contact pools. That stage consumed 78.7%/90.7% of counted work. Neither reached the global work limit. Paired evaluated 29,809 complete combinations and committed 219 moves, including 110 changing two witnesses; single evaluated 11,478 and committed 211. More joint activity did not produce a valid final minor.

**Acceptance and representation.** No query discarded all its completed eligible proposals without making a commit. Paired rejected 13 lower-Q proposals, all energy ties that increased overlap by one; single rejected none. The strict feasible-Q phase was never reached. These receipts do not identify acceptance as the principal cause: the shared BFS initialization concentrated overlapping owners, and both bounded neighborhoods failed to resolve them within the actual cost. Interrupted pools leave unknown alternatives; they do not justify raising limits. Energy changes across price updates are not descent evidence.

Failure-inclusive solver/process totals were 531.382/545.073 s paired, 531.471/545.940 s single, and 87.632/98.827 s MM. CPU totals were 531.278, 531.105 and 87.578 s. Host load was 33.21–34.48 on 32 available CPUs, so timing retains that contention qualification.

**Decision:** retire these two complete policies. This screen provides no ACL comparison or promotion case for pairing. It does not disprove every contact-first representation, but further local gains or cap changes alone would not address the demonstrated failure. [All statuses/times](../../../results/codex/track-b020-analysis/analysis001/table.csv), [per-input receipts](../../../results/codex/track-b020-analysis/mechanism001/per_input.csv), and [full totals](../../../results/codex/track-b020-analysis/mechanism001/totals.json) preserve the negative evidence.
