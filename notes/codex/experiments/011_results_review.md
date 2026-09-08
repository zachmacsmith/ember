# Experiment 011: independent results review

Reviewed 2026-09-08 UTC from the retrieved raw records, without using `analyze_pilot.py` or its generated summaries. Only this note was edited for the review; no algorithms were changed and no embeddings were rerun.

**Width-one joint repair is the strongest fixed candidate by mean ACL in this development screen, but the project goal remains unmet.** It improves on singleton repair in 11 of 18 matched trials and ties in seven. Against timely MM results, every candidate wins only on the two K40 and two complete-bipartite trials and loses on all 12 trials for the other six inputs. Width-four repair uses more work and has a slightly worse aggregate mean than width one. These are nine source graphs at two seeds, not graph-class estimates or confirmation results.

## Frozen protocol and audit

The [launch note](011_search_contact_ablation.md) specifies the hypotheses and fixed settings. Raw artifacts are in [the retrieved run](../../../results/codex/retrieved/hyde03/011-search-contact-ablation). Every method used seeds 0 and 1, a 60-second credited solver allowance, the same ideal Zephyr Z12 target, fresh worker processes, empty per-task JIT caches, and one numerical-library thread. All 90 trials ran sequentially on `hyde03`; methods were shuffled within source/seed blocks. The four native configurations are:

| Short name in this note | Recorded method | Search budget | Repair groups | Beam width |
| --- | --- | ---: | --- | ---: |
| Search | `native-search` | 1000 | Disabled | — |
| Single | `native-search-single` | 1000 | Sizes 1 | 1 |
| Joint1 | `native-search-joint1` | 1000 | Sizes 1, 2, 3, 4 | 1 |
| Joint4 | `native-search-joint4` | 1000 | Sizes 1, 2, 3, 4 | 4 |

Every enabled repair used four passes, 512 total group attempts, 500000 total popped BFS vertices, 50000 popped vertices per group, at most two group orders, three chain alternatives, halo 2, and a 512-qubit region cap. The last five settings follow the frozen implementation defaults. Limits are common across source graphs. Joint1 is already joint reconstruction with alternative group orders; it is not the singleton control. These rows are standalone ablations, not outputs selected into a portfolio.

The independent audit checked:

- All 510 retrieved file-byte hashes and their aggregate digest; all 143 transport input hashes; all 42 frozen source-file hashes; all 90 task identities/configurations and final/worker record pairs; all nine graph-record hashes and the target hash.
- All 90 complete returned embeddings against the original serialized source and target: exact source keys, nonempty chains, target membership, no internal duplicates, pairwise disjointness, connectedness, and source-edge contacts. Stored ACL, qubit count, maximum chain, and within-chain variance agree with recomputation. This includes the two valid but late MM embeddings.
- All 72 native trials used the native interpreter and frozen native source path. MM distribution metadata is absent; forbidden-import attempts and loaded prohibited modules are empty. MM's 18 trials used its separate interpreter and version 0.2.22. These runtime guards complement, rather than replace, the earlier source audit.
- Every final record has return code zero and agrees with its worker result except for controller-added fields. Recorded timeout classification and overrun agree with measured solver wall. Across the four native configurations, each source/seed has identical recorded layout state and diagnostics apart from times; its pre-repair qubit count agrees with Search's output. Complete pre-repair embeddings are not separately saved, so this last check is of recorded state/counts, not an independent hash comparison of pre-repair chains.
- All 392 accepted-repair trajectory entries have positive, arithmetically consistent savings, monotone cumulative work counts, and final totals matching the output. Recorded member-growth sums are internally consistent. Intermediate embeddings and member lengths are not serialized, so growth itself cannot be independently reconstructed from these records.

| Provenance | Digest |
| --- | --- |
| Source snapshot map | `73cca55965158b69bdbf94340cd36d701acd8fa426be191f457c4945284baeae` |
| Manifest file bytes | `dabbb44f2328e900c93b98fecc9beed0c5399d58b389e198ea42e1bcf202cfa1` |
| Transport input map | `c0c3b7ad995d94ff406b482d8b5109d5c4e9badbd63fb0c406225fc0ae13f2f0` |
| Retrieved artifact map | `e9cf78c386aa65e31915644f0fcc5e0b42a3ca3340dd00538be86452b6034945` |
| Target record | `38cde794d3c1461054a45b5a660d157737b019c19cb9a7b38e2027730e3d5938` |
| Native entry point bytes | `43d83368b28e1953d92a88e2cbe02720dccaf25ee9a4faac7db9b4e92649f9a3` |
| Contact repair bytes | `953e5259067ed6adb2f6d905e2e104a87938f4ee056906b4817608905eaa648f` |
| Experiment worker bytes | `2f496cca12d488678f213418eeb46cd58b37e5c332e2936248dde73b4e310810` |

The manifest's parent revision is `904be3ecbf9baa5039b431585301fb906feda02e`. Map/record digests use sorted-key compact JSON; the manifest, task records, and retrieval index retain individual file/input hashes. The target has 4800 vertices and 45864 edges. Both environments report Python 3.10.12, NetworkX 3.4.2, NumPy 2.2.6, Numba 0.65.1, dwave-networkx 0.8.19, and SciPy 1.15.3.

## Success and ACL

Each native configuration succeeds within the allowance on 18/18 trials. MM succeeds on 16/18; both K100 trials are valid but late. Thus every native/MM comparison has 16 paired timely trials and two candidate-only timely successes. No MM-only timely success or double failure occurred.

Mean ACL below averages the two solver seeds for that exact source graph. No failed or late result contributes to these means.

| Source | MM | Search | Single | Joint1 | Joint4 |
| --- | ---: | ---: | ---: | ---: | ---: |
| Bipartite 30+30 | 3.116667 | 2.516667 | 2.466667 | 2.466667 | 2.466667 |
| Complete 100 | Timeout ×2 | 7.260000 | 7.260000 | 7.260000 | 7.260000 |
| Complete 40 | 5.312500 | 3.900000 | 3.875000 | 3.850000 | 3.812500 |
| Grid 8×8 | 1.101562 | 1.390625 | 1.351562 | 1.328125 | 1.312500 |
| Honeycomb 5×5 | 1.014286 | 1.321429 | 1.250000 | 1.150000 | 1.135714 |
| King 8×8 | 1.429688 | 1.945312 | 1.882812 | 1.796875 | 1.773438 |
| ER 80, recorded 296 edges | 2.737500 | 3.375000 | 3.237500 | 3.193750 | 3.275000 |
| Regular 80, degree 3 | 1.137500 | 1.718750 | 1.581250 | 1.462500 | 1.512500 |
| Watts–Strogatz 80 | 1.181250 | 1.856250 | 1.718750 | 1.612500 | 1.656250 |

The unweighted mean of the nine source means is Search 2.809337, Single 2.735949, Joint1 2.680046, and Joint4 2.689396. Joint1 therefore leads this particular fixed-candidate aggregate; its lead over Joint4 is only 0.009350 ACL. Joint4 has lower source means on K40, grid, honeycomb, and king; Joint1 has lower means on ER, regular, and Watts–Strogatz; two inputs tie. Selecting those individual outcomes would be a portfolio and is not proposed.

On the eight inputs with timely MM pairs, the unweighted means are MM 2.128869 and Joint1 2.107552. That small arithmetic advantage is driven by the two dense-input gains and must not be presented as an across-input victory: Joint1 loses on six of eight source means. The geometric mean of its 16 paired ACL ratios to MM is 1.0916, and the arithmetic mean of those ratios is 1.1178. Absolute ACL and relative ACL summaries weight differences differently; both are descriptive here.

K100's late MM embeddings have diagnostic ACL 10.07 and 10.66 at solver wall 61.781 and 63.139 seconds, respectively. All native configurations return ACL 7.26 within the allowance. This is evidence of timely-success coverage and an interesting diagnostic comparison, but K100 contributes no primary paired quality win against a timely MM result. The two MM outputs are not relabeled as successes.

## Sample variance of ACL

These are unbiased sample variances over the two run ACLs, with denominator `n−1`; for two values, `s²=(ACL₀−ACL₁)²/2`. They are different from the per-embedding variance of individual chain lengths stored as `within_chain_variance`.

| Source | MM | Search | Single | Joint1 | Joint4 |
| --- | ---: | ---: | ---: | ---: | ---: |
| Bipartite 30+30 | 0.0272222 | 0 | 0 | 0 | 0 |
| Complete 100 | — | 0 | 0 | 0 | 0 |
| Complete 40 | 0.4278125 | 0 | 0 | 0.0012500 | 0.0003125 |
| Grid 8×8 | 0.0001221 | 0 | 0.0030518 | 0.0004883 | 0.0019531 |
| Honeycomb 5×5 | 0 | 0.0082653 | 0.0050000 | 0.0050000 | 0.0025510 |
| King 8×8 | 0.0010986 | 0.0030518 | 0.0030518 | 0.0004883 | 0.0010986 |
| ER 80 | 0.0200000 | 0.0028125 | 0.0312500 | 0.0569531 | 0.0312500 |
| Regular 80, degree 3 | 0.0003125 | 0.0175781 | 0.0132031 | 0.0153125 | 0.0312500 |
| Watts–Strogatz 80 | 0.0000781 | 0.0063281 | 0.0038281 | 0.0200000 | 0.0657031 |

Two seeds give one degree of freedom per estimate. A recorded zero means only that these two ACLs agree; it is not a zero-variance guarantee. Repair can increase run-to-run ACL variation even when its mean improves: Joint1's ER variance rises from Search's 0.0028125 to 0.0569531 because the two runs improve by different amounts. These data do not support a general variance reduction claim.

## Repair gains, work, and coverage

Savings below are reductions in total physical qubits, summed over both seeds for each source. All repair starts are valid Search outputs; this experiment does not exercise partial-embedding recovery.

| Source | Single savings | Joint1 savings | Joint4 savings |
| --- | ---: | ---: | ---: |
| Bipartite 30+30 | 6 | 6 | 6 |
| Complete 100 | 0 | 0 | 0 |
| Complete 40 | 2 | 4 | 7 |
| Grid 8×8 | 5 | 8 | 10 |
| Honeycomb 5×5 | 10 | 24 | 26 |
| King 8×8 | 8 | 19 | 22 |
| ER 80 | 22 | 29 | 16 |
| Regular 80, degree 3 | 22 | 41 | 33 |
| Watts–Strogatz 80 | 22 | 39 | 32 |
| Total | 97 | 170 | 152 |

Single beats Search in 15 trials and ties in three. Joint1 beats Single in 11 and ties in seven, saving 73 additional qubits. Joint4 beats Single in 11, ties in four, and loses in three. Against Joint1, Joint4 wins six, ties seven, and loses five; it uses 18 more qubits across all 18 trials. All repair outputs still weakly improve their own Search starting count, because each accepted move strictly reduces total qubits.

| Work over 18 trials | Single | Joint1 | Joint4 |
| --- | ---: | ---: | ---: |
| Group attempts | 1510 | 7913 | 6557 |
| Accepted moves | 90 | 160 | 142 |
| Accepted moves with a growing member, reported | 0 | 12 | 14 |
| Popped BFS vertices | 131394 | 3869129 | 6218225 |
| Beam expansions | 116 | 72899 | 115577 |
| Tree construction attempts | 13559 | 250043 | 582241 |
| Total repair wall, seconds | 1.0321 | 15.5037 | 28.6130 |
| Reported stops: no improvement / group cap / work cap | 18 / 0 / 0 | 12 / 4 / 2 | 9 / 2 / 7 |

Joint1's accepted singleton/pair/triple/quadruple moves save 65/33/37/35 qubits; Joint4's save 51/27/34/40. These totals demonstrate that accepted joint moves contribute to the observed trajectories, but do not prove the gains are impossible for another singleton schedule. Member growth is present at both beam widths and is not evidence unique to width four.

Joint4 performs 1.607× Joint1's popped-vertex work and takes 1.846× its directly timed repair wall, while attempting only 82.9% as many groups. Equal work caps do not imply equal realized work or neighborhood coverage. ER seed 0 is a concrete example: Joint1 reaches 217 group attempts and saves four qubits; Joint4 reaches only 72 and saves one. Both consume 500000 popped vertices. Watts–Strogatz seed 0 similarly reaches 495 groups/saves 16 with Joint1 versus 97 groups/saves six with Joint4 at the same expansion cap. This is consistent with wider reconstruction spending effort before reaching other useful groups. Different accepted trajectories also change later opportunities, so the records do not isolate budget coverage as the sole cause.

The stop label `no_improvement` requires care. Six such records also have exactly 512 group attempts: Joint1 on K40 seed 1, honeycomb seed 1, and king seed 1; Joint4 on honeycomb seed 1 and both king seeds. The implementation generates a pass truncated to the remaining group allowance, then returns `no_improvement` if that final prefix changes nothing. These six runs exhausted their total group budget; the label does not certify a complete unsuccessful neighborhood pass. Even uncapped `no_improvement` refers only to the generated groups, bounded region, roots, alternatives, and orders, not to local optimality under all legal chain moves. Group-attempt totals do not reveal unique vertices or regions explored, because unsuccessful group identities are not serialized.

All four native configurations have the same recorded construction stopping distribution: four source/seed trials report schedule `fixpoint` (K40 and bipartite, both seeds); fourteen hit the 1000-evaluation limit. Those internal schedule stops do not certify physical-chain optimality. No native run stopped by deadline.

## Runtime on the same host

Each cell is the two-seed arithmetic mean **solver wall / whole-process wall**, in seconds. K100's MM row is diagnostic failed-run time, not successful latency.

| Source | MM | Search | Single | Joint1 | Joint4 |
| --- | ---: | ---: | ---: | ---: | ---: |
| Bipartite 30+30 | 2.954 / 3.732 | 5.906 / 8.550 | 3.662 / 5.613 | 6.543 / 9.638 | 6.328 / 8.808 |
| Complete 100, MM late | 62.460 / 63.351 | 9.216 / 11.522 | 10.398 / 13.401 | 10.597 / 12.594 | 17.855 / 21.128 |
| Complete 40 | 4.381 / 5.526 | 5.462 / 9.168 | 4.097 / 7.419 | 5.107 / 8.350 | 6.255 / 9.833 |
| Grid 8×8 | 0.311 / 0.946 | 4.299 / 6.648 | 4.290 / 7.276 | 4.624 / 7.123 | 5.275 / 7.578 |
| Honeycomb 5×5 | 0.329 / 0.947 | 4.763 / 7.731 | 4.824 / 7.555 | 6.394 / 9.440 | 5.886 / 9.037 |
| King 8×8 | 0.581 / 1.424 | 7.235 / 10.109 | 8.096 / 11.694 | 7.175 / 10.214 | 8.031 / 10.789 |
| ER 80 | 2.191 / 3.107 | 8.147 / 11.543 | 7.360 / 10.234 | 8.021 / 11.471 | 9.268 / 12.367 |
| Regular 80, degree 3 | 0.388 / 1.047 | 7.950 / 11.468 | 9.654 / 14.097 | 9.068 / 12.569 | 9.906 / 13.725 |
| Watts–Strogatz 80 | 0.385 / 0.844 | 4.609 / 6.696 | 4.712 / 6.720 | 5.372 / 7.148 | 5.603 / 7.548 |

Ratios below are formed within each of the 16 timely source/seed pairs on `hyde03`, then summarized. They exclude both late K100 MM trials.

| Candidate / MM | Median solver-wall ratio | Geometric mean solver-wall ratio | Median process-wall ratio | Geometric mean process-wall ratio |
| --- | ---: | ---: | ---: | ---: |
| Search | 12.044 | 6.958 | 7.067 | 5.136 |
| Single | 12.302 | 6.612 | 7.604 | 5.003 |
| Joint1 | 13.081 | 7.502 | 7.145 | 5.389 |
| Joint4 | 14.026 | 8.167 | 7.688 | 5.700 |

Joint1's solver-wall ratios range from 0.996 to 27.282; only one of the 16 is below one. No candidate has lower whole-process wall than MM on any timely pair. Solver-CPU ratios closely track wall ratios; Joint1's median CPU ratio is 13.085. The method therefore still has a material speed gap under the measured cold-call protocol. Warm service latency requires a separately declared cache/reuse protocol; it cannot replace these measurements after seeing them.

The host is shared Linux x86_64 with affinity to CPUs 0–31. Worker-start one-minute load ranges from 11.60 to 16.90. Two cold runs per source do not estimate timing distributions or isolate host effects. Some refined calls finish faster than their Search-only counterpart despite the same recorded construction state, illustrating why differences between separate total-call times are not reliable measurements of repair cost. The directly instrumented repair stage is more informative for that ablation. Do not pool these times with experiment 009 or 014's laptop times.

## Remaining gaps and next interpretation

Joint1 is a reasonable fixed development lead because it has the lowest observed macro ACL, dominates Single on these paired quality results, and uses less repair work than Joint4. It is not a statistically established winner, and it does not defeat MM across the tested inputs. Its remaining mean ACL excesses over MM are:

| Source | ACL excess | Relative excess | Mean additional qubits |
| --- | ---: | ---: | ---: |
| Grid 8×8 | 0.2265625 | 20.57% | 14.5 |
| Honeycomb 5×5 | 0.1357143 | 13.38% | 9.5 |
| King 8×8 | 0.3671875 | 25.68% | 23.5 |
| ER 80 | 0.4562500 | 16.67% | 36.5 |
| Regular 80, degree 3 | 0.3250000 | 28.57% | 26.0 |
| Watts–Strogatz 80 | 0.4312500 | 36.51% | 34.5 |

The evidence supports improving the coverage and cost of the same repair process rather than widening the beam by default. Singleton repair cheaply captures 97 qubits of reduction, and joint repair adds useful reductions, but the remaining sparse-input gaps are much larger than Joint4's occasional extra gains. Work-cap losses on ER/regular/Watts–Strogatz and group-cap truncation elsewhere suggest testing uniform changes to group selection, candidate cost, or region access with explicit work accounting. They do not justify graph-family settings or selecting a different algorithm per source.

This screen establishes an incremental benefit from joint repair under these bounded settings. It does not establish novelty, a variance advantage, adequate speed, scaling across Ember, or the ability to repair failed constructions. Larger and independent confirmation samples remain necessary after development changes; the nine graphs and two seeds here should remain labeled development data.
