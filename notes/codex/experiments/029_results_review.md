# Experiment 029: independent Sudoku supplement review

All six calls return timely valid embeddings on the frozen ideal Z12 target.
The fixed contacts candidate uses fewer qubits than MM on both observed
Sudoku sizes: 24 versus 25 at box order 2, and 405 versus 408 at box order 3.
The fixed spectral candidate ties MM at order 2 with 25 qubits and improves
order 3 to 394 qubits. The order-2 tie is demonstrably nonoptimal: contacts'
24-qubit embedding is a validated better witness on that same source/target.

These are two fixed development structures and one solver seed. There is
no claim about a Sudoku population, family-wide superiority, optimum chain
length, or across-seed ACL variance. Each candidate is reported separately;
the better method is not selected per graph. These results are not pooled
with readiness selection 017, corpus runs 019/025/026, or local smoke timings.

## Retrieval and identity

The run at `/home/dabh/ember-codex/runs/029-sudoku-development-comparison`
on hyde03 completed all six tasks under controller PID 124544 at
`2026-09-08T03:08:11.141676Z`. Fresh status confirmed controller complete,
6/6 finalized SUCCESS, lock free, tmux stopped, and supervisor exit 0 before
retrieval. The complete local archive is
`results/codex/retrieved/hyde03/029-sudoku-development-comparison/`.
All 95 retrieved file hashes passed verification. No restart was performed.

| Frozen identity | SHA-256 / commit |
| --- | --- |
| Commit | `4cad1d67c59484b4d9583e02f49d06e1a556b2af` |
| Source snapshot | `321f24371678f3080b4aef67bcdb43479b5acce7b7ec90b47acdf01b82afd747` |
| Transport | `88e1c99260de51f3c42c1a226ed71a664f3cecdc199357b20369d5edb518b29a` |
| Retrieved inventory | `eb27661c6f97ff253e30a15f77e00eb070969bb8ea83b4fe5b00b4e1111f17a9` |
| Supplement | `e6e3036634164be8e5491d0c6b8d41e8d4fb042fd63fe3fd43fda3538018f047` |
| Complete comparison plan | `ff77c22ce191c2dfe27dfab9cac149e4b7dd9fcf3618b8e14d41514ac33846a0` |
| Ideal Z12 target | `38cde794d3c1461054a45b5a660d157737b019c19cb9a7b38e2027730e3d5938` |

The ordinary analyzer passed. The independent standard-library audit
rechecked the transport/retrieval inventories, all 46 frozen source files,
all eight supplement bundle files, the supplement identity, and the complete
two-source × three-method × one-seed comparison plan. It recomputed all six
task digests and checked task/result source, target, supplement, plan, graph
ID, configuration, seed, and timeout bindings. The task, claim, worker-result,
and final-result directories contain exactly the same six task IDs.
Every worker field survives unchanged in its final result.

The copied supplement has the exact permitted file set and contains no
symlinks. Its generator source bytes match the frozen runtime loader source.
The copied original Sudoku entries match the full frozen inherited manifest,
whose byte hash matches the supplement's recorded original-manifest hash.
The new IDs do not collide with any of the 31,149 inherited IDs. This audit
uses the shipped source/provenance; it does not depend on a mutable external
027 directory or import the supplement generator as its semantic oracle.

## Source graph semantics and scope

Box order is the box width, not the full board side. The graph has one vertex
per cell and an edge exactly when two distinct cells share a row, column,
or box. Independent exhaustive pair checking verifies every required and
forbidden contact: 120 pairs at order 2 and 3240 pairs at order 3. Actual
degrees, node/edge counts, and disjoint row/column/additional-box edge counts
agree with the frozen provenance.

| Graph ID | Box order | Board side | Vertices | Edges | Regular degree | Row / column / additional-box edges |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| 1000002 | 2 | 4 | 16 | 56 | 7 | 24 / 24 / 8 |
| 1000003 | 3 | 9 | 81 | 810 | 20 | 324 / 324 / 162 |

The solver graph copies exactly match their frozen bundle records. Each uses
consecutive integer labels, the complete verified edge list, and empty graph,
node, and edge attributes. Row-major cell interpretation, family labels,
parameters, and IDs occur only in evaluator provenance. Source-record hashes
are `fb89a8fafe5eebbb3480232c4027549d06a16efa473bc2a9850b91c40f9a1a65`
for order 2 and
`52580f5927c9d291163cb251d6dacd171a5fb78e9fbf174051644c2a54940659`
for order 3.

Original Sudoku IDs 37900 and 37901 remain preserved, with recorded sizes
6561 vertices / 734832 edges and 65536 vertices / 24084480 edges. This
supplement does not replace them or retroactively fill the missing Sudoku
entry in readiness 017. Box orders 4 and 5 remain reserved and ungenerated.
No comparison against the entire inherited isomorphism universe is claimed.
Changing puzzle clues would not create new structures of these fixed
cell-conflict graphs.

Both frozen input sidecars still state `embedding_feasibility="unproved"`.
That statement describes the evidence at input generation and is deliberately
unchanged. The independently validated embeddings in **this result archive**
now constitute explicit feasibility witnesses for these two source hashes on
this ideal-Z12 target hash. `analysis/feasibility_witnesses.json` links all three
valid witnesses per source by method, task ID, and embedding hash. It makes a
separate result-level feasibility statement without altering input provenance
or selecting an algorithm's output from competing methods.

## Embedding validity and isolation

For all six outputs, the independent oracle checks exact source keys including
isolates, nonempty integer chains, original-target membership, disjointness,
connectivity, and every logical contact using the original target edges.
It recomputes qubit count, ACL, maximum chain length, and within-embedding
chain-length variance. The target contains 4800 vertices and 45864 edges.
All outputs pass; all solver calls finish within 60 seconds, report zero
deadline overrun, and return process exit code 0. There are no failed,
interrupted, invalid, late, or missing trials.

All four native calls use the frozen native entry point and
`/home/dabh/ember-codex/envs/4e1fb892db12754e/native/bin/python`.
The package-absence checks pass; minorminer is absent, and no forbidden import
attempt or loaded embedding library is recorded. The two comparator calls use
the separate `mm/bin/python` environment and minorminer 0.2.22. MM receives
only source/target copies, seed 0, timeout 60, and default configuration.
Candidates receive no MM embeddings or family parameters.

All calls report Python 3.10.12 with NetworkX 3.4.2, NumPy 2.2.6, Numba 0.65.1,
SciPy 1.15.3, and dwave-networkx 0.8.19. Native settings remain the fixed search
with 1000 placement-evaluation ceiling, four refinement passes, width one,
512 groups of sizes 1–4, 500000 refinement work units, 16 boundary sites,
round-robin group coverage, greedy contact trees, and qubit/contact-redundancy
objective. Spectral adds only `initialization='spectral'`. No source-specific
configuration or competing-method selection occurs.

## Exact quality and measured time

`Q` is total used physical qubits; `ACL = Q / number of source vertices`.
There is one observation per row, not an average over repeated seeds.

| Box order | Method | Q | ACL | Solver seconds | Process seconds |
| --- | --- | ---: | ---: | ---: | ---: |
| 2 | MM | 25 | 1.562500 | 0.338828 | 1.072930 |
| 2 | Contacts | 24 | 1.500000 | 5.810456 | 10.117250 |
| 2 | Spectral contacts | 25 | 1.562500 | 3.677090 | 7.105386 |
| 3 | MM | 408 | 5.037037 | 10.373248 | 11.434121 |
| 3 | Contacts | 405 | 5.000000 | 13.796522 | 17.146612 |
| 3 | Spectral contacts | 394 | 4.864198 | 14.819317 | 19.062780 |

| Box order | Candidate | Candidate − MM qubits | Solver/MM ratio | Process/MM ratio |
| --- | --- | ---: | ---: | ---: |
| 2 | Contacts | -1 | 17.148706 | 9.429549 |
| 2 | Spectral contacts | 0 | 10.852390 | 6.622411 |
| 3 | Contacts | -3 | 1.330010 | 1.499600 |
| 3 | Spectral contacts | -14 | 1.428609 | 1.667184 |

These are contemporaneous comparisons from the same sequential run on hyde03.
All calls use fresh workers, separate initially empty JIT caches, and one
numerical-library thread. Solver wall includes copies, initialization,
construction, pruning/refinement, and first-call compilation. Process wall
also includes startup/loading/import and post-call validation. The full
recorded worker span is 65.957942 seconds; consecutive worker intervals are
disjoint, with minimum gap 0.003078 seconds.

At order 2, both candidates exceed 10× MM in measured solver wall, although
both process-wall ratios are below 10×. At order 3, the quality improvements
cost approximately 1.33–1.43× solver time and 1.50–1.67× process time. The
small order-2 MM denominator and charged candidate first-call costs matter
to this interpretation. These are shared-host, single-trial ratios; they
do not establish stable timing differences or a general runtime bound.
No timings from other experiments or machines enter the table.

## Spectral and refinement records

Both spectral calls complete under the fixed numerical policy, seed 0,
requested iteration limit 64, tolerance 1e-5, and 50000000 numerical work-unit
allowance. The independent audit checks source components, solver branch,
operator nonzeros, dimensions, residual-status consistency, cutoff flags,
numerical work arithmetic, and nested initialization/layout/solver walls.

| Box order | Numerical branch | Initialization seconds | Charged work | Maximum of two layout-vector residuals | Cutoff uncertain |
| --- | --- | ---: | ---: | ---: | --- |
| 2 | Dense base case | 0.155452 | 4480 | 5.6474e-16 | no |
| 3 | LOBPCG | 0.172919 | 52731 | 7.1382e-6 | yes |

Both report `residual_tolerance`, no warnings, no reference-rank deficiency,
and zero initialization deadline overrun. Order 2 charges 4096 dense units
plus 384 sparse units; order 3 charges 31 operator columns × 1701 nonzeros.
Preprocessing, sorting, orthogonalization, and preconditioning are outside
this numerical work counter but remain inside measured time. The order-3
cutoff flag records subspace uncertainty, not an embedding failure or a proof
of exact eigenvalue degeneracy.

As in 026, eigenvectors and initial orders are not saved, so diagnostic
consistency is checked without independently recomputing residuals from saved
vectors. Low residuals alone do not prove lowest-mode selection. Every
refinement group/pass/expansion counter remains within its declared limit,
all refinement deadline overruns are zero, and reported qubit savings equal
the difference between pruned and final qubit counts.

## Saved evidence and limits

The retrieved `analysis/` directory contains the ordinary analyzer outputs,
`input_provenance.json`, `independent_review.py`, the independent embedding
and initialization helpers, `independent_review.json`,
`independent_results.csv`, and `feasibility_witnesses.json`. Raw tasks,
embeddings, source, logs, all eight bundle files, and original statements
remain unchanged. Analysis additions are outside the original retrieval
inventory.

These observations establish feasibility and small per-source quality gains
over MM for fixed candidates. They do not establish all-Sudoku superiority,
solve the original oversized corpus instances, or resolve the remaining MM
losses on other graph families. In particular, the spectral policy improves
order 3 but loses one qubit to contacts at order 2. Preserve that regression
and keep subsequent parameter choices global and explicit. Additional solver
seeds would measure stochastic variation on these same structures; they would
not create independent Sudoku graph instances or a clean source holdout.

```sh
.venv/bin/python scripts/codex/analyze_pilot.py results/codex/retrieved/hyde03/029-sudoku-development-comparison
.venv/bin/python results/codex/retrieved/hyde03/029-sudoku-development-comparison/analysis/independent_review.py results/codex/retrieved/hyde03/029-sudoku-development-comparison
```
