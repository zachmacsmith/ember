# Experiment 026: independent spectral-initialization review

Both fixed arms returned timely valid embeddings on all 34 selected input
structures. Spectral initialization lowers ACL on 23 inputs, raises it on 9,
and ties on 2 relative to the contact-only control. It saves 644 total qubits
and lowers the equally weighted input mean ACL by 4.146%, from 3.479215 to
3.334972. The contact-only control reproduces all 34 outputs from 025 exactly.

Against the historical MM019 results, spectral has lower ACL on 8 inputs,
higher ACL on 21, and optimal ACL-1 ties on 2 among the 31 common timely
successes. The ties are the selected cycle and path. Both candidates also
succeed on the three inputs where MM019 exceeded its deadline. This is a
useful development improvement but does not meet the all-family objective.
No per-input choice between methods is made.

These are inherited development inputs, one selected graph per represented
family and one solver seed. There is no estimate of family mean performance,
across-seed ACL variance, or generalization. Within-embedding chain-length
variance remains a separate diagnostic. All aggregates count the shared
frustrated-square/king input once. Sudoku is still missing from this corpus
screen; its later corrected supplement is a separate experiment.

## Completion and immutable evidence

Controller PID 122275 on hyde03 completed all 68 tasks at
`2026-09-08T03:06:00.865762Z`. A fresh SSH observation verified controller
status complete, all 68 results finalized SUCCESS, lock free, tmux stopped,
and supervisor exit 0 before retrieval. No controller restart was performed.
The complete archive is
`results/codex/retrieved/hyde03/026-corpus-spectral-initialization/`.

Retrieval verified all 430 inventoried files. Independent verification
rechecked that inventory, the transport inventory, all 45 frozen source
files, the target, all 34 source graphs, both selection sidecars, all 68 task
digests, all result identities, and all claims and worker/final record pairs.
Every worker field is preserved in its final record. All workers returned
exit code 0 without interruption or missing provenance. Consecutive recorded
worker intervals are disjoint, with a minimum gap of 0.002710 seconds. Their
total span is 856.183217 seconds; the first started 36.978129 seconds after
025's final worker ended.

| Frozen identity | SHA-256 / commit |
| --- | --- |
| Commit | `f93f889f428baa26d1722382c77de385d4b4822f` |
| Source snapshot | `91824466fdd3880940df0cc6d3569a461a617c3d1ae883e50425ee368952a765` |
| Transport | `481ae432e47dc5b0c9f3951d38080ee21e9de0d9e52833bafd15985322c9608c` |
| Retrieved inventory | `b2a5cd4cac7394ade97f01dcf2c0f72f4619d009ad4f849e2fb0c9ce114610d9` |
| Target | `38cde794d3c1461054a45b5a660d157737b019c19cb9a7b38e2027730e3d5938` |
| Readiness selection | `06c02356f8df5503b57f280ba4939c298cc05834c563a3da8a71f96fe245db98` |

The target is ideal Z12: 4800 vertices and 45864 edges. All source graph
records, target bytes, and both selection sidecars are identical to retrieved
025 and 019. The sidecar file hashes remain
`7474bf4d873295f0c485134b7445753c5035af5b64876668d91673315b615c46`
for readiness and
`2b5d85755a519596230d25a0972b67028da5224e419ac8ce757288ca4a2ee47c`
for the original selection. Canonical selection/source/topology hashes and
actual node/edge counts match. Source metadata and attributes are empty;
family names and source IDs are evaluator provenance, not solver inputs.

All 68 records identify the frozen native entry point under this run's
`source/packages/ember-qc/src/ember_qc/algorithms/factored/native.py` and the
separate native interpreter
`/home/dabh/ember-codex/envs/4e1fb892db12754e/native/bin/python`.
Every worker passed the MM/busclique package-absence check, recorded no
forbidden import attempt or loaded embedding library, and reported
minorminer absent. All report Python 3.10.12, NumPy 2.2.6, SciPy 1.15.3,
NetworkX 3.4.2, Numba 0.65.1, and dwave-networkx 0.8.19.

The ordinary analyzer and the independent standard-library verifier both
pass. The latter imports neither the solver nor the runner's validator. It
checks exact source keys including isolates, nonempty integer chains,
original-target membership, disjointness, connectivity, and all source-edge
contacts using the **original target edges**. It recomputes ACL, qubit count,
maximum chain length, and within-embedding chain-length variance. All 68
credited embeddings pass, all externally measured solver walls are at most
60 seconds, and every recorded deadline overrun is zero. There are no
timeouts, invalid outputs, initialization/construction failures, or missing
results in 026.

## Fixed arms and complete quality comparison

The control is `native-search-joint1-contacts`. The spectral arm is
`native-search-joint1-contacts-spectral`, adding only
`initialization='spectral'` to the explicit configuration. Both use the same
search/conversion/pruning/contact-repair pipeline, seed 0, width one,
1000-placement-evaluation ceiling, four refinement passes, at most 512 groups,
group sizes 1–4, 500000 shared refinement work units, 512-qubit region cap,
16 boundary sites, round-robin group order, greedy contact trees, and the
qubit/contact-redundancy objective. Each arm keeps one configuration across
every input. The spectral initialization is conventional source-Laplacian
computation, not a separate embedding solver or a portfolio competitor
inside the pipeline.

| Fixed arm | Timely successes / attempted | Total qubits, 34 inputs | Mean ACL, 34 inputs | Mean ACL on the same 31 inputs with timely MM019 output |
| --- | ---: | ---: | ---: | ---: |
| Contacts control026 | 34 / 34 | 15706 | 3.479215 | 2.844822 |
| Spectral026 | 34 / 34 | 15062 | 3.334972 | 2.687571 |
| Historical MM019 | 31 / 34 | undefined for all 34 | undefined for all 34 | 2.961536 |

The contacts control has exact chain-set equality with contacts025 on every
input, as well as matching construction and pruned qubit counts. No cross-run
time equivalence is inferred from this output replay. The historical MM
records are revalidated after their complete retrieved archive is hash-checked.
They are used for quality only; there were no MM tasks in 026.

MM019's three timeout cases remain explicit:

| Input | MM019 timely result | Preserved late diagnostic |
| --- | --- | --- |
| complete 1041 | absent: TIMEOUT | valid, ACL 15.645669 |
| regular 14334 | absent: TIMEOUT | valid, ACL 15.100000 |
| spin_glass 37302 | absent: TIMEOUT | no valid source-covering embedding |

Their late outputs do not enter the 31 common timely comparisons. The
common-success subset is selected by MM's outcome; its mean cannot stand in
for unconditional all-input superiority. Full failure and deadline details
remain in `019_results_review.md`. Spectral's eight strict ACL wins remain
the selected bipartite, Johnson, random ER, SBM, star, Turán, Watts–Strogatz,
and weak–strong cluster inputs. Cycle and path now tie MM at the mathematical
ACL lower bound 1. Tree, binary tree, and the named-special graph remain above
MM's ACL-1 witnesses.

Against contacts control, the largest savings are Kagome (-75 qubits), wheel
(-55), triangular lattice (-52), circulant (-49), random planar (-47), and
the shared frustrated-square/king input (-42). The nine regressions are
random ER (+23), Barabási–Albert (+17), Kneser (+9), hypercube (+8), SBM (+6),
Turán (+3), and BCC, star, and spin_glass (+1 each). The ties are complete
and bipartite. All losses remain in the fixed-arm comparison.

## Initialization diagnostics and their limits

All 34 spectral calls use policy `component_scaled_laplacian_lobpcg`, seed 0,
requested iteration limit 64, tolerance 1e-5, and a shared 50000000 numerical
work-unit limit. The native call's original deadline includes initialization.
No numerical, dependency, work-limit, or deadline failure is recorded, and no
alternate initializer is invoked. The 34 control records explicitly identify
random initialization and contain no spectral-initialization record.

The independent audit reconstructs each source's connected components and
checks every component's first vertex, node/edge count, expected operator
nonzeros, solver branch, and reported dimensions. All 34 full initialization
records match their source graphs. Only planted solution is disconnected
(seven components); the other 33 inputs each have one component. Numerical
work accounting is consistent component by component: sparse work is operator
nonzeros times charged columns, dense base-case work is dimension cubed, and
the totals equal reported global work/columns. No dense base case is used in
this corpus screen; isolate components have zero numerical work.

This work counter excludes preprocessing, sorting, orthogonalization, and
preconditioning. Those operations still consume measured solver time. It is
not a count of all computational operations. The requested iteration limit is
recorded, but the actual iteration trace is not saved.

| Initialization observation | Result |
| --- | --- |
| Two layout-vector residuals at most 1e-5 | 32 / 34 |
| Finite approximate layout accepted under the fixed rule | 2 / 34 |
| Inputs with uncertain spectral-subspace cutoff | 15 / 34 |
| Inputs with reported reference-rank deficiency | 0 / 34 |
| Inputs with captured solver warnings | 4 / 34 |
| Median / mean initialization seconds | 0.110880 / 0.145927 |
| Minimum / maximum initialization seconds | 0.079036 / 0.496324 |
| Median / maximum charged numerical work | 76000.5 / 642880 |

The largest work count is the regular input, 642880 of 50000000 allowed units.
All nested initialization/layout/solver wall records are consistent, and all
initialization deadline overruns are zero. Recorded residuals are finite;
centering and orthogonality errors meet the declared acceptance thresholds.
Each component's residual status, cutoff gap/uncertainty, and global status
are internally consistent with the saved values.

The two approximate cases are also the two ACL-1 MM ties:

| Input | Maximum residual of the two layout vectors | Initialization status | Final ACL | Cutoff uncertain |
| --- | ---: | --- | ---: | --- |
| cycle 1829 | 0.0001405234 | approximate | 1 | no |
| path 2030 | 0.0010788506 | approximate | 1 | yes |

Honeycomb and binary tree also have solver warnings: their first two
residuals meet tolerance, but the third residual does not. Their
`residual_tolerance` status therefore describes the two layout vectors, not
convergence of the entire three-vector block. The third vector is used in
the cutoff diagnostic. All warnings remain in the raw results.

The 15 cutoff-uncertain inputs are complete, grid, spin_glass, cubic lattice,
bipartite, path, star, Kneser, BCC, generalized Petersen, Turán, binary tree,
wheel, Johnson, and hypercube. This flag can reflect a small spectral gap or
uncertainty due to residuals; it is not a claim that all 15 have exact
eigenvalue degeneracy, and it is not an embedding failure.

The run does **not** retain eigenvectors or initial orders. Consequently, the
independent audit can verify diagnostic arithmetic and status consistency,
but cannot recompute each reported residual from a saved vector or inspect
each initial permutation. Small residuals alone also do not prove that the
selected subspace contains the lowest nonconstant modes. Frozen source and
the pre-run numerical/integration tests support the implementation path;
the final embedding oracle independently establishes the output's validity.
These are distinct forms of evidence. Future numerical investigation should
retain the needed vectors/orders if those claims become important.

## Search work and contemporaneous timing

All paired methods ran sequentially on hyde03 in fresh processes with separate
initially empty JIT caches and one numerical-library thread. Solver wall covers
graph copies, initialization (including lazy numerical-library import),
construction, pruning/refinement, and first-call compilation. Whole-process
wall also includes loading/import/startup and post-call validation outside
the timed solver call. Start-of-trial one-minute load ranged from 11.24 to
16.99. These are shared-host observations at one seed, not stable speed ratios
for other hosts or workloads.

| Arm | Median solver / process seconds | Mean solver / process seconds |
| --- | ---: | ---: |
| Contacts control026 | 8.285 / 11.171 | 10.280 / 13.001 |
| Spectral026 | 8.335 / 10.722 | 9.372 / 12.172 |

| Spectral/control ratio on 34 paired inputs | Mean | Median | Minimum | Maximum |
| --- | ---: | ---: | ---: | ---: |
| Solver wall | 0.933432 | 0.934619 | 0.469480 | 1.566077 |
| Process wall | 0.952168 | 0.954974 | 0.522941 | 1.505055 |

The maximum ratios occur on cycle, despite its ACL improvement to 1. Overall
observed paired ratios favor spectral, but one observation per input cannot
establish a small algorithmic timing effect. No MM timing ratio or pooled
026/025 timing estimate is reported.

Both arms reach 1000 placement evaluations on 33 inputs. On named-special,
the engine reports a `fixpoint` stop after 980 control evaluations and 779
spectral evaluations. Thus the declared bound is an evaluation ceiling, not
a guarantee of equal realized work. Both arms stay within it.

Construction uses 19255 total qubits for control and 18494 for spectral,
a reduction of 761 before pruning. After pruning the totals are 16370 and
15672, respectively. Contact refinement saves another 664 control qubits and
610 spectral qubits, producing the net final reduction of 644. Control
refinement reports 22 work-limit, 11 group-limit, and one no-improvement stop;
spectral reports 13, 19, and two. All refinement expansion/group/pass counters
remain within their frozen limits and all refinement deadline overruns are
zero. These observations suggest the initializer changes the construction
problem materially; they do not imply that a larger refinement budget would
eliminate the remaining losses.

## Family-mapped observations

Each row is one input at seed 0. MM019 ACL is historical quality evidence only;
the time ratios compare the two contemporaneous 026 candidates. The two rows
marked `*` share the exact input `ember_32616` and the same tasks/embeddings.
Their normalized topology hash is
`ad061ab01ea949cfe9e993013fde26052d059f31be29c63a2ef3a93d3a06c1c4`.
All totals above count that input once. Distinct normalized hashes do not
prove pairwise non-isomorphism. CSV aggregation must group by `graph_key`,
not count repeated family memberships as independent observations.

Sudoku has no eligible READY input in the original fixed selection because
both inherited manifest entries fail the necessary Z12 count bounds. It is
not attempted here, and its absence is not a candidate failure. The corrected
two-size development supplement in 029 is separately identified and does not
change this 34-input/35-membership corpus result.

| Family | Selected ID → input ID | n / m | MM019 ACL | Control026 ACL | Spectral026 ACL | Spectral − control qubits | Spectral/control solver / process time |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| barabasi_albert | 10662 | 122 / 472 | 3.3607 | 3.5000 | 3.6393 | +17 | 0.96 / 1.08 |
| bcc_lattice | 33402 | 91 / 216 | 1.2637 | 1.6703 | 1.6813 | +1 | 0.99 / 0.94 |
| binary_tree | 4905 | 127 / 126 | 1.0000 | 1.1811 | 1.0945 | -11 | 0.91 / 0.96 |
| bipartite | 1363 | 126 / 3969 | 6.1587 | 4.4921 | 4.4921 | +0 | 0.97 / 0.98 |
| circulant | 3499 | 134 / 402 | 1.4627 | 1.8507 | 1.4851 | -49 | 0.82 / 0.84 |
| complete | 1041 | 127 / 8001 | TIMEOUT | 9.2913 | 9.2913 | +0 | 0.78 / 0.77 |
| cubic_lattice | 33219 | 125 / 300 | 1.4960 | 1.9200 | 1.7920 | -16 | 0.79 / 0.80 |
| cycle | 1829 | 126 / 126 | 1.0000 | 1.1508 | 1.0000 | -19 | 1.57 / 1.51 |
| frustrated_square * | 32816 → 32616 | 121 / 420 | 1.4132 | 2.3388 | 1.9917 | -42 | 0.93 / 1.00 |
| generalized_petersen | 4083 | 126 / 189 | 1.3095 | 1.8175 | 1.6587 | -20 | 0.58 / 0.64 |
| grid | 1584 | 128 / 232 | 1.0469 | 1.6484 | 1.3516 | -38 | 0.86 / 0.90 |
| hardware_native | 37603 | 128 / 352 | 1.4609 | 2.1953 | 1.9453 | -32 | 0.88 / 0.97 |
| honeycomb | 32367 | 190 / 264 | 1.0316 | 1.6474 | 1.4368 | -40 | 0.93 / 0.96 |
| hypercube | 4755 | 128 / 448 | 3.2969 | 3.5469 | 3.6094 | +8 | 1.04 / 1.04 |
| johnson | 5242 | 120 / 1680 | 9.8750 | 7.4167 | 7.0750 | -41 | 0.90 / 0.94 |
| kagome | 32122 | 131 / 236 | 1.2214 | 1.8092 | 1.2366 | -75 | 0.87 / 0.90 |
| king_graph * | 32616 | 121 / 420 | 1.4132 | 2.3388 | 1.9917 | -42 | 0.93 / 1.00 |
| kneser | 5411 | 126 / 315 | 2.8968 | 3.2857 | 3.3571 | +9 | 1.02 / 1.03 |
| lfr_benchmark | 31357 | 100 / 204 | 1.6000 | 1.9800 | 1.8400 | -14 | 0.91 / 0.91 |
| named_special | 37761 | 46 / 69 | 1.0000 | 1.1522 | 1.0652 | -4 | 0.94 / 0.93 |
| path | 2030 | 141 / 140 | 1.0000 | 1.2340 | 1.0000 | -33 | 0.71 / 0.81 |
| planted_solution | 34404 | 133 / 175 | 1.0226 | 1.3759 | 1.0977 | -37 | 0.80 / 0.85 |
| random_er | 6450 | 133 / 870 | 7.8496 | 6.5414 | 6.7143 | +23 | 0.94 / 0.92 |
| random_planar | 31536 | 152 / 450 | 1.8487 | 2.3224 | 2.0132 | -47 | 0.97 / 0.98 |
| regular | 14334 | 140 / 2800 | TIMEOUT | 9.3500 | 9.3143 | -5 | 0.96 / 0.97 |
| sbm | 30736 | 120 / 625 | 5.3167 | 5.0917 | 5.1417 | +6 | 0.68 / 0.73 |
| shastry_sutherland | 33018 | 121 / 270 | 1.2149 | 1.6777 | 1.3388 | -41 | 1.55 / 1.47 |
| spin_glass | 37302 | 160 / 12720 | TIMEOUT | 11.4625 | 11.4688 | +1 | 1.15 / 1.12 |
| star | 2229 | 127 / 126 | 1.1339 | 1.0709 | 1.0787 | +1 | 0.97 / 0.96 |
| sudoku | no eligible READY input | — | not attempted | not attempted | not attempted | — | — |
| tree | 5058 | 121 / 120 | 1.0000 | 1.1901 | 1.0909 | -12 | 0.86 / 0.89 |
| triangular_lattice | 31879 | 128 / 384 | 2.0859 | 2.6484 | 2.2422 | -52 | 1.01 / 1.05 |
| turan | 3060 | 90 / 2700 | 8.8111 | 5.0778 | 5.1111 | +3 | 0.99 / 0.95 |
| watts_strogatz | 22972 | 174 / 1740 | 13.7931 | 9.9655 | 9.8391 | -22 | 1.03 / 1.05 |
| weak_strong_cluster | 33587 | 128 / 1988 | 3.6797 | 3.3828 | 3.3203 | -8 | 1.00 / 1.00 |
| wheel | 2429 | 127 / 252 | 1.1575 | 2.0079 | 1.5748 | -55 | 0.47 / 0.52 |

## Saved audit artifacts and interpretation

The retrieved `analysis/` directory contains the ordinary analyzer's reports,
the independent verifier and shared oracle, `independent_review.json`,
`family_results.csv`, `family_table.md`, and `initialization_records.csv`.
The latter has one checked row for every spectral initialization; complete
component diagnostics and warning strings remain in the raw worker results
and independent JSON's copied diagnostics. Analysis additions are outside
the original 430-file retrieval inventory; frozen inputs, source, results,
and sidecars remain unchanged.

The main positive result is improvement on many of the sparse inputs that
contact refinement alone could not improve enough, including two optimal
ties. The main negative result is the remaining 21 losses to MM among the
31 common timely successes, with nine regressions relative to the candidate
control. The conventional initializer is useful here, but it is neither a
novelty result by itself nor evidence of a universal embedding advantage.
Keep these failures and all parameter choices in the development record;
do not turn residual flags, family names, or observed winners into a method
selection rule. Repeated seeds, additional source instances and sizes, and
protected final evaluation remain necessary for the eventual claim.

After 026 quiescence and verified retrieval, the already frozen 029 Sudoku
comparison was started as authorized. Its launch is recorded separately in
`029_launch_status.md`. None of its outcomes or timings enter this report.

```sh
.venv/bin/python scripts/codex/analyze_pilot.py results/codex/retrieved/hyde03/026-corpus-spectral-initialization
.venv/bin/python results/codex/retrieved/hyde03/026-corpus-spectral-initialization/analysis/independent_review.py results/codex/retrieved/hyde03/026-corpus-spectral-initialization results/codex/retrieved/hyde03/025-corpus-contact-rearrangement results/codex/retrieved/hyde03/019-ember-readiness-screen
.venv/bin/python results/codex/retrieved/hyde03/026-corpus-spectral-initialization/analysis/family_report.py results/codex/retrieved/hyde03/026-corpus-spectral-initialization results/codex/retrieved/hyde03/019-ember-readiness-screen
```
