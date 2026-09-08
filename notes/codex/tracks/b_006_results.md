# B006 development results

B006 exactly reproduces B005's final embeddings, retained partial embeddings, construction orders, committed updates and promotions on all nine inputs. Six candidate outputs succeed and three fail; all complete and partial minors validate on the original graphs. The frozen run completed before retrieval, and all 171 archived files passed their recorded hashes. There are still two timely ACL wins against fresh MM, on optimal one-site-per-vertex grid and honeycomb embeddings, and four losses. The late K100 MM result receives no timely credit.

| Input | B006 Q | Reuse hits | Counted work, B005 → B006 | Seconds, B005 → B006 |
|---|---:|---:|---:|---:|
| complete 40 | failed | 0 | 11.201M → 11.201M | 19.66 → 12.87 |
| complete 100 | failed | 0 | 20.000M → 20.000M | 23.87 → 31.06 |
| bipartite 30+30 | 330 | 0 | 13.399M → 13.399M | 21.78 → 16.24 |
| ER 80 | failed | 2 | 2.796M → 2.780M | 4.95 → 6.84 |
| regular 80 | 100 | 56 | 4.335M → 3.323M | 8.17 → 6.98 |
| Watts–Strogatz 80 | 141 | 19 | 7.481M → 7.183M | 11.35 → 14.01 |
| grid 64 | 64 | 63 | 1.573M → 0.933M | 4.00 → 4.40 |
| honeycomb 70 | 70 | 69 | 2.491M → 1.398M | 6.65 → 6.52 |
| king 64 | 113 | 3 | 3.031M → 3.016M | 4.01 → 5.94 |

The 212 immediate reuses remove 3,074,312 counted units. For every input, the observed B005-minus-B006 work difference equals the recorded original computation work of reused results. Grid's domain calls decrease from 128 to 65, and honeycomb's from 140 to 71; propagation work approximately halves. All propagation and global limits reconcile. Counts mix operations with different costs, so this reduction is not a prediction of proportional wall-time improvement.

Wall time is not consistently lower. Large differences also occur on dense inputs with zero reuse and exactly unchanged counted work, and fresh MM times vary substantially between runs. Candidate CPU/wall ratios remain 0.9978–0.9999 under load around 33–34 on 32 logical CPUs; that does not control frequency, cache or other host effects. These separately frozen runs therefore establish less repeated computation and observed exact behavior, not a portable measured speedup. Contemporary candidate/MM ratios range from 2.18 to 8.02 on the six successful pairs.

Retain this narrow reuse in the development constructor because it avoids demonstrably duplicate work without changing the observed choices. This does not promote the overall algorithm or repair its ER/dense failures. The separately specified B007 experiment will test whether growth after promotion can preserve future domains; that scientific change is absent here. No result selection between B005 and B006 is used.

Details: [pre-code specification](b_domain_reuse.md), [fresh MM pairs](../../../results/codex/track-b006-analysis/analysis001/pairs.csv), [raw records](../../../results/codex/track-b006-analysis/analysis001/rows.json), [exact continuity and work](../../../results/codex/track-b006-analysis/analysis001/reuse_summary.json), [freeze identities](../../../results/codex/track-b006-checks/freeze.json). Reproduction uses `track-b006-analysis/analyze.py`, followed by `summarize_reuse.py` with the new output directory and retrieved archive; existing directories are preserved.
