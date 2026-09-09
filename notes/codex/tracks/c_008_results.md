# C008: compound-transfer constructor — retire

The fixed compound policy completes **3/8** inputs, retaining atomic's **2/8**, against stock MM's **6/8**. It fails the predeclared minimum of four completions and is retired. The additional grid completion is useful mechanism evidence, but all three timely MM comparisons have worse compound Q/ACL; path and tree also worsen against atomic. These are eight reused development inputs, one seed and fifteen seconds per call on hyde03, with separate fixed arms.

Cells show **Q / solver seconds** for timely valid outputs. **T[Q,M]** denotes a timeout with diagnostic occupied sites and missing original edges; **late Q** is a valid MM map returned after the allowance, receiving no quality credit. ACL and process times for every call are in the [24-row table](../../../results/codex/track-c-008-review/analysis001/table.csv).

| Input | Stock MM | Atomic control | Compound |
|---|---:|---:|---:|
| Path, n141 | 141 / 0.170 | 193 / 2.807 | 206 / 4.705 |
| Tree, n121 | 121 / 0.136 | 172 / 2.897 | 174 / 2.697 |
| Grid, n128 | 134 / 0.352 | T[302,1] / 14.507 | 245 / 10.261 |
| Planar, n152 | 281 / 0.571 | T[345,39] / 14.508 | T[405,50] / 14.509 |
| ER, n133 | 1044 / 8.386 | T[463,367] / 14.511 | T[415,366] / 14.509 |
| Regular, n140 | late 2481 / 15.351 | T[543,1681] / 14.513 | T[557,1672] / 14.513 |
| Complete, n127 | late 2170 / 17.492 | T[619,4965] / 14.518 | T[619,4961] / 14.519 |
| SBM, n120 | 638 / 4.101 | T[379,206] / 14.509 | T[457,171] / 14.509 |

The [receipts](../../../results/codex/track-c-008-review/receipt_summary.json) reconcile **908 attempts**: 859 find no eligible interior transfer, 29 inflate Q, six lack a bridge, three exhaust local work, and eleven certify. Nine certificates are selected and committed, directly removing twelve missing contacts with net zero Q (fifteen bridge sites added and fifteen sites deleted). The other two lose proposal selection; no selected certificate is rejected by acceptance. Six inputs first diverge through a compound commit from equal recorded entry states. Regular and complete have none: their first differences occur at deadline-truncated ordinary visits, so their partial-M differences are not compound-reach evidence.

Access and eligibility dominate the added neighborhood: only 49 attempts reach a potentially useful interior site; 3,499 ordinary addition visits find no free path. The shared initial assignments match on all eight inputs, controlling this comparison without establishing initialization quality. Compound's entire private work is 582,052 records and 0.459 seconds, approximately 0.51% of its total solver time. Shared distance/atomic BFS accounts for 408.1 million adjacency examinations; this is work, not separately measured BFS time. Total solver/process seconds are MM 46.558/48.581, atomic 92.770/95.653, compound 90.223/93.212, including all timeouts. Improving this small private routine's speed cannot explain the broad failure. Search, proposal selection and changed trajectories remain coupled; a compound score can replace one ordinary score within the fixed sixteen-score prefix.

The approved [auditor](../../../results/codex/track-c-008-review/analyze.py) ran once and passed with zero errors after all 228 archive hashes were verified. It checked original-label chain/contact validity, deadlines and accounting; no solver or trajectory was rerun. Expected timeout strings and null returned maps caused two additive receipt-summary assertions, preserved before correction; the accepted audit and raw outputs were unchanged. Root separately read the summary/table; no root full-auditor repeat is claimed. [Bindings and execution evidence](../../../results/codex/track-c-008-review/review_manifest.json) preserve all failures. This screen supports neither a family-mean/variance claim nor generalization or novelty.
