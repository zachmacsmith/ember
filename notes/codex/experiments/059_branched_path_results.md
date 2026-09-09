# A059: retained branches pass the fixed continuation gate

All18 fresh calls were timely, independently original-valid SUCCESS; the saved
screen passed with no errors. The fixed variant improves four inputs and ties
two against fresh A053, with no Q or coverage regression. Total Q1078→1045
(−33); macroACL1.405471→1.362104. Cycle reaches its Q126/ACL1 lower bound.
This passes the predeclared cycle-plus-another continuation gate, not a
promotion over MM or a claim across source classes.

Every call below succeeded; seconds are solver wall. The complete18-row
[CSV](../../../results/codex/059-results-review/all18.csv) also retains ACL,
maximum chain, within-chain variance, CPU/process time and status.

| Input | A053 Q | Branched Q | MM Q | A053 s | Branched s | MM s |
|---|---:|---:|---:|---:|---:|---:|
| Cycle 1829 | 148 | 126 | 126 | 2.352 | 3.133 | 0.342 |
| Cubic lattice 33219 | 258 | 258 | 187 | 9.212 | 6.878 | 0.841 |
| Kagome 32122 | 173 | 169 | 160 | 7.363 | 6.544 | 0.694 |
| Grid 1584 | 167 | 163 | 134 | 6.721 | 8.173 | 0.869 |
| Planted 34404 | 158 | 158 | 136 | 4.617 | 5.788 | 0.386 |
| Petersen 4083 | 174 | 171 | 165 | 8.367 | 8.892 | 0.522 |

The wrapper's base Q equals fresh A053 on all six inputs. Therefore its9
certified/committed moves account for the full33Q: cycle22, kagome4, grid4,
Petersen3. Cubic and planted tie. All26 unshortened path questions were feasible
(25 no-gain, one committed), consistent with repairing the earlier side-branch
representation exclusion. This does not establish optimality of the remaining
route/owner neighborhood or explain every unresolved gap.

The stage used981,514 declared units across all six calls, including45,684
branch units, and0.476247s. Final wrapper validation added47,098 reads and
0.013087s; counted additional work totals1,028,612. All six stages returned
`complete`;14/26 paths reached their normal32-attempt bound. There were569
questions:9 commits,25 no-strict-gain and535 infeasible fixed-route allocations.
The recorded215 retained components/280 retained sites are summed over path
queries, not unique physical objects. No global work/deadline stop, interrupted
certificate or missing accounting occurred; unvisited alternatives stay unknown.

All-attempt solver totals were38.6318s A053,39.4067s branched (+2.01%), and
3.6535s MM. Process totals were50.6653s,51.3244s (+1.30%), and7.4902s.
No branched/A053 individual solver or process ratio exceeded10. Prefix runtime
variation remains, so paired elapsed differences are not a measurement of
stage cost alone. MM still wins Q on cubic(+71 excess branched qubits),
kagome(+9), grid(+29), planted(+22), and Petersen(+6); cycle is an optimal tie.
MM totalsQ908/macroACL1.182722. Branched solver time remains15.01× MM on
planted and17.03× on Petersen; all six are slower than MM. These gaps are not
discharged by the favorable A053-relative aggregate.

Decision: unchanged-policy replication is justified; broader or MM promotion
is not. This is one seed on six exposed structures, not a source-population or
seed-variance estimate. The two A057 failed constructions cannot enter this
complete-output stage. One approved saved analysis ran after verified
quiescence; no constructor repeat, local saved-final search, source change or
unsaved physical-trace reconstruction occurred. Archive digest
`fca68e7319ad407a2da3a729f480845d017d55827add5a4691303ed01ca3f4af`;
all errors, raw receipts and denominators are retained under059-results-review.
