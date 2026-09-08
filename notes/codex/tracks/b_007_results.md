# B007 development results

B007 improves completion from six to seven of nine inputs, but its quality tradeoff is unfavorable. The previously failing ER input now completes at 310 qubits, versus fresh MM's 211. Among the six inputs completed by both B006 and B007, Watts–Strogatz costs 52 additional qubits, king saves one, and four tie: a net increase of 51. Grid and honeycomb retain their optimal ACL of 1. The seven timely candidate/MM pairs contain two wins and five losses.

| Input | Q, B006 → B007 | Fresh MM Q | B007 seconds | B007/MM time |
|---|---:|---:|---:|---:|
| complete 40 | failed → failed | 194 | 17.76 | — |
| complete 100 | failed → failed | late | 44.40 | — |
| bipartite 30+30 | 330 → 330 | 180 | 29.67 | 6.12× |
| ER 80 | failed → 310 | 211 | 22.62 | 3.64× |
| regular 80 | 100 → 100 | 90 | 7.04 | 13.52× |
| Watts–Strogatz 80 | 141 → 193 | 94 | 24.20 | 20.89× |
| grid 64 | 64 → 64 | 70 | 4.31 | 3.93× |
| honeycomb 70 | 70 → 70 | 71 | 6.16 | 5.38× |
| king 64 | 113 → 112 | 90 | 8.24 | 8.94× |

All complete outputs and retained partial minors validate on their original graphs. Both dense failures remain: K40 blocks after 32 placements, and K100 exhausts 20 million counted units after 35. The late MM K100 embedding is valid at 1,057 qubits but returns after 62.61 seconds and receives no timely credit. The detached controller completed all 18 tasks before retrieval; all 174 archived file hashes pass.

There are 325 growth queries, consuming 2,104,045 counted units across the nine calls. Fifty-one resolved proposals commit 57 added sites; these are local investments, not final qubit savings. Every accepted growth has a completed, nonempty propagation result and a passed commit deadline. Recorded growth/propagation limits and overlapping global accounting reconcile, with no local growth or propagation cap hit. Growth consumes 8.27 seconds in total, including failed queries. The existing raw records retain every rejection and limit.

The scientific warning is clear: fewer promotions do not imply shorter eventual chains. Watts–Strogatz promotions fall from 60 to 45 while final Q rises from 141 to 193; king's fall from 60 to 54 with only one qubit saved. The checks enforce local domain consistency, but provide no completion or later routing-cost guarantee. ER's recovered completion is useful evidence of reach, not competitive quality.

Do not promote this fixed growth policy. Retain its feasible-growth mechanism and the negative lesson for a different construction revision; merely increasing its search allowance is unsupported. Fresh paired timings also remain far from the runtime goal on regular and Watts–Strogatz. Host load was approximately 33–34 on 32 logical CPUs, so neither cross-run changes nor these single paired observations establish a portable speed ratio.

Details: [pre-code hypothesis and critique](b_future_domain_growth.md), [all fresh pairs](../../../results/codex/track-b007-analysis/analysis001/pairs.csv), [raw observations](../../../results/codex/track-b007-analysis/analysis001/rows.json), [growth accounting](../../../results/codex/track-b007-analysis/analysis001/growth_summary.json), [frozen identities](../../../results/codex/track-b007-checks/freeze.json). Reproduce with `track-b007-analysis/analyze.py ARCHIVE NEW_OUTPUT_DIRECTORY`, then `summarize_growth.py NEW_OUTPUT_DIRECTORY`; both operate only on saved records.
