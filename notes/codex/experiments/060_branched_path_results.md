# A060 replication passes its fixed continuation gate

The one combined saved analysis passes with no audit errors:70/72 calls are
timely original-valid successes. Both candidate failures are original planted
34404,seed1; MM succeeds24/24. Additional branched coverage is12/12, with no
lost A053 success and no class paired-mean Q regression. Grid(−0.5Q) and
planted(−1.5Q) provide exactly the required two noncycle additional class gains.
These are small effects; cubic, kagome and Petersen additional means tie.
The fixed gate passes without changing code, caps, seeds or outputs.

All instance/seed Q values follow. Every numeric entry is a timely valid
SUCCESS; FAIL entries are retained. [All72 metrics/times](../../../results/codex/060-results-review/all72.csv)
and [complete class means, sample variances and times](../../../results/codex/060-results-review/class_statistics.md)
retain all three arms and exact denominators.

| Cohort/input | A053 Q seeds0/1 | Branched Q seeds0/1 | MM Q seeds0/1 | Paired mean ΔQ |
|---|---:|---:|---:|---:|
| additional Cycle 1827 | 115/104 | 101/101 | 101/101 | -8.5 |
| additional Cubic 33222 | 396/372 | 396/372 | 382/382 | 0 |
| additional Kagome 32115 | 239/240 | 239/240 | 187/187 | 0 |
| additional Grid 1590 | 267/261 | 267/260 | 220/203 | -0.5 |
| additional Planted 34374 | 139/142 | 138/140 | 126/124 | -1.5 |
| additional Petersen 4018 | 110/109 | 110/109 | 93/94 | 0 |
| original Cycle 1829 | 148/135 | 126/126 | 126/126 | -15.5 |
| original Cubic 33219 | 258/232 | 258/232 | 187/163 | 0 |
| original Kagome 32122 | 173/165 | 169/164 | 160/153 | -2.5 |
| original Grid 1584 | 167/155 | 163/152 | 134/131 | -3.5 |
| original Planted 34404 | 158/FAIL | 158/FAIL | 136/135 | 0 (seed0 only) |
| original Petersen 4083 | 174/184 | 171/184 | 165/194 | -1.5 |

Additional03 has5 wins/7 ties, Q2494→2473(−21), macroACL1.600902→1.584285;
MM hasQ2200/macroACL1.426928. Original06 has7 wins/4 ties on11 common successes,
Q1949→1903(−46); its successful candidate macroACL1.390095→1.357123 excludes
the planted failure. MM's12-success mean1.178869 is not the same paired seed
set: its Q is1675 on the11 common seeds,1810 over all12. Wrapper base Q matches
fresh A053 everywhere known, so all67Q savings belong to the stage. Original
seed0 quality matches059 in all18 observations;059 remains separate.

Both original planted seed1 calls complete a26-vertex/45-edge native core but
block during lifting at96/133 placed vertices, using3,127,838 lift units. The
new stage never runs on that failed prefix. The historical056 failure is kept,
not reset. Stage invocations were23/24, all completing:7 additional commits
save21Q;13 original commits save46Q. Additional stage/gate costs are0.94630/
0.03209s; original invoked-stage/gate known sums are1.21622/0.03376s. There are
no new global stage work/deadline stops; normal route-attempt caps still limit
search. Uninvoked-stage fields remain null rather than fabricated observations.

Same-host solver totals A053/branched/MM are53.155/54.230/4.427s on03 and
83.213/86.691/6.093s on06, including both failed attempts. Process totals are
60.939/61.932/7.243s and103.078/107.467/11.831s. No branched/A053 ratio exceeds10,
but branched exceeds10×MM solver time on9 additional and10 original rows,
including the failed original planted call. Cost scalars below separate the
inherited constructor from the small added stage; nested timers cannot be
summed as independent work, and residual core time is not labeled JIT.

MM gaps remain: additional branched loses9, wins1 (cubic seed1), and ties both
cycles optimally. Originals lose8, win1 (Petersen seed1), tie both cycles, and
fail once where MM succeeds. Additional cubic's mean remains worse than MM
despite its one winning seed. Original Petersen's favorable paired mean coexists
with its seed0 loss. Seed variability is not uniformly reduced: additional grid
ACL variance increases0.000450→0.0006125; original Petersen increases0.003149→
0.005322. Two seeds cannot establish stable class variance.

Decision: the unchanged local proposal mechanism merits a separately declared
broader measurement, not MM or all-class promotion and not another local repair.
The global connected-branch-set representation already expresses MM mappings;
retained branches repair a restriction in the local path proposal. The evidence
covers two exposed representatives of six families with two seeds, not held-out
graphs. No source refinement, constructor repeat, new profiling or physical
trace replay followed these outcomes.

| >10×MM rows | Rows | Inherited A053 s | Native core s | Layout within core s (recorded rows) | Expansion s | Added branch s |
|---|---:|---:|---:|---:|---:|---:|
| additional A053 | 9 | 40.398 | 34.175 | 27.033 (8/9) | 5.210 | — |
| additional branched | 9 | 40.182 | 33.970 | 26.915 (8/9) | 5.195 | 0.696 (9 invoked) |
| original A053 | 10 | 70.352 | 56.285 | 46.214 (9/10) | 12.591 | — |
| original branched | 10 | 73.081 | 59.648 | 49.164 (9/10) | 11.989 | 1.006 (9 invoked) |

The saved core/layout and expansion timings place most observed cost upstream of the new path stage. These scalars identify a cost domain, not the cause of a quality gap or a measured JIT fraction. [Individual scalar receipts](../../../results/codex/060-results-review/over10x_cost_scalars.csv) retain failures and unassigned residuals.
