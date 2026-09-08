# B005 development results

B005 produces the first Track B ACL wins against fresh MM: grid and honeycomb reach one qubit per source vertex, the absolute minimum. It is still an incomplete, slower general constructor. Six of nine inputs succeed; all six embeddings and three retained partial minors pass the reused original-graph validator. The controller and detached supervisor finished before retrieval; all 169 retrieved files passed their recorded hashes. Source and settings stayed frozen.

| Input | B003 Q | B005 Q | MM Q | B005 / MM seconds |
|---|---:|---:|---:|---:|
| complete 40 | failed | failed | 194 | 19.66 / 13.55 |
| complete 100 | failed | failed | 1113, late | 23.87 / 69.55 |
| bipartite 30+30 | 330 | 330 | 180 | 21.78 / 10.12 |
| ER 80 | 298 | failed | 211 | 4.95 / 10.04 |
| regular 80 | 114 | 100 | 90 | 8.17 / 0.47 |
| Watts–Strogatz 80 | 112 | 141 | 94 | 11.35 / 0.79 |
| grid 64 | 73 | **64** | 70 | 4.00 / 0.44 |
| honeycomb 70 | 83 | **70** | 71 | 6.65 / 0.40 |
| king 64 | 108 | 113 | 90 | 4.01 / 0.60 |

There are two wins and four losses among timely common pairs. K100's late MM embedding receives no timely credit. Relative to B003, three successful outputs improve, two regress, one ties, and ER loses completion. These are seed-0 observations on exposed development inputs, not variance estimates or class-level evidence.

Grid/honeycomb make 64/70 singleton commits with no promotions or tree calls; all 128/140 propagation passes complete. Regular improves by 14 qubits with 57 singleton commits. Conversely, ER promotes 70 variables and blocks after 44 insertions; Watts–Strogatz and king promote 60 each. No propagation allowance is exhausted anywhere. Both complete graphs and bipartite promote every variable by degree and reproduce B003's construction outcomes, as predicted before execution.

All propagation/query/global counters reconcile within their declared limits. Counts mix adjacency and bitset operations and are not comparable to B003's raw scans. Contemporary successful timing ratios range from 2.15 to 17.29 times MM. Host load remains approximately 33–34 on 32 logical CPUs, with candidate CPU/wall ratios 0.9978–1.0000; these are host-specific observations.

Retain the feasibility mechanism, but do not promote the full candidate. Promotion currently permits chain growth without requiring it to preserve future domains. The first value-trial promotions on ER, Watts–Strogatz and king immediately commit singleton chains, followed by many empty-domain promotions; this supports investigating that interaction, not larger propagation caps. A separate avoidable cost is that a successful singleton trial computes domains for the next state, then the outer iteration recomputes that same state. Completed results could potentially be reused. Neither direction is implemented here.

Details: [pre-code specification](b_domain_propagation.md), [pair CSV](../../../results/codex/track-b005-analysis/analysis001/pairs.csv), [raw diagnostics](../../../results/codex/track-b005-analysis/analysis001/rows.json), [propagation accounting](../../../results/codex/track-b005-analysis/analysis001/propagation_summary.json), [freeze identities](../../../results/codex/track-b005-checks/freeze.json). Reproduction uses `track-b005-analysis/analyze.py`, then `summarize_propagation.py`, with the retrieved `track-b-propagating-005` archive and a new output directory.
