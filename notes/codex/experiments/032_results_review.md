# Experiment 032: independent review of four solver seeds

This fixed spectral/contact candidate does **not** demonstrate superiority across
the readiness inputs. It produced timely valid embeddings in all 136 calls;
MM succeeded in 122 of 136 calls and exceeded the 60-second deadline in 14.
Among the 122 matched timely successes, candidate ACL was lower in 38 trials,
higher in 76, and tied at the certified optimum in eight. No unresolved quality
tie occurred. Every planned observation remains in the analysis; no best-seed
or cross-method score was constructed.

The ordinary analyzer and a separate standard-library audit passed all 272
records. This review concerns 34 inherited development structures with 35 family
memberships, not 35 independent structures or a family-population experiment.
Original Sudoku remains absent from 017/032; the corrected q2/q3 supplement in
029 is separate and contributes no observations to this report.

The fixed candidate uses the 026 configuration: spectral initialization, 1000
placement evaluations, four contact passes, at most 512 groups of sizes 1–4,
width one, 16 extra boundary sites, round-robin coverage and the qubit/contact
redundancy objective. Default limits are 500000 shared refinement work units,
50000 per group and a 512-qubit region. MM receives the fixed seed and timeout
with its other options left at stock defaults.

## Frozen run, completion and retrieval

| Item | Verified value |
|---|---|
| Run | `032-solver-seed-replication` on `hyde03` |
| Commit | `9c01447dbc8ef2249664123d1b511504b8803222` |
| Source snapshot | `89a3e77bf1df22a7eea436e42f0bc04c81055e098d7baf78c632a76224046994` |
| Transport/input digest | `f02da9b1a88d747f8ba37e5e834395194cc084bd79ae3b47df73d09e13d83618` |
| Retrieval digest | `1cb5179aba2218de69c5f1babebe99241f1e8fe52e7bad5a3c779fdb719468a4` |
| Target | `38cde794d3c1461054a45b5a660d157737b019c19cb9a7b38e2027730e3d5938` |
| Target structure | Ideal Z12, 4800 qubits, 45864 couplers, maximum degree 20 |
| Trial plan | 34 inputs × MM/fixed spectral candidate × seeds 0–3; 272 calls |
| Controller | PID 125964; complete at `2026-09-08T04:20:52.891821Z` |
| Quiescence | 272 finalized; lock free; tmux stopped; supervisor exit 0 |
| Archive verification | 1450 indexed files, including 45 source files |

The launch was `2026-09-08T03:21:46.368074Z`. The worker interval spanned
3546.189551 seconds; the smallest gap between successive
claimed starts and preceding process completion was 0.001400426 seconds.
No worker overlap, missing worker record, retry, controller interruption, process
error or hard-watchdog termination was observed. Every process returned code zero.
Fresh SSH checks verified the same controller during execution. Full retrieval
began only after independently observed quiescence.

Both corpus sidecars, all 34 source records and the target are byte-identical to
026. All task hashes, the exact Cartesian task matrix, source hashes, source-map
hash, target hash, sidecar identities and retrieval/transport file hashes were
recomputed. Source-map differences from 026 are exactly `field.py` and `pilot.py`:
the former omits unused horizontal neighbor preparation (028); the latter adds
the supplement-ingestion path, which is inactive in this corpus run. The native
entry point, spectral initialization and contact-refinement modules are unchanged.
Relative to 029, all source bytes match, with only the unused supplement loader
omitted from the source map. No singleton-relocation, checkpoint-selection or
later capacity-correction code is part of 032.

## Independent validity and solver separation

The independent oracle checks exact source-key coverage, including isolates;
nonempty integer chains; membership in the original target; no duplicated qubit
within or across chains; connectedness; and coverage of every original source
edge by a physical coupler. It then recomputes Q, ACL, maximum chain length and
within-embedding chain-length variance. All 258 timely-success embeddings and
the ten valid late MM embeddings pass. The four remaining MM calls return no
valid embedding. Late quality appears only in diagnostic fields.

All 136 candidate records use the native environment and the frozen run's
`source/packages/ember-qc/src/ember_qc/algorithms/factored/native.py`. Candidate
records have no forbidden import attempts, no loaded embedding libraries and
no installed MM version. Their worker first checks that MM/busclique packages
cannot be found, then installs the import blocker. MM records use the separate
MM environment and its installed `minorminer` implementation. The reviewed
native source path makes no MM/busclique call.

The interpreter paths are under
`/home/dabh/ember-codex/envs/4e1fb892db12754e/{native,mm}/bin/python`.
Every worker records Python 3.10.12, NetworkX 3.4.2, NumPy 2.2.6, Numba 0.65.1,
SciPy 1.15.3 and dwave-networkx 0.8.19; only the MM environment reports MM 0.2.22.
All workers record the same Linux/x86_64 host and affinity set 0–31. The earlier
machine probe in 010 identified an Intel Xeon w5-3435X. This was a shared host,
without an exclusive CPU reservation.

## Quality, failures and the effect of conditioning

For one source with n vertices, a successful trial has ACL = Q/n. The table
reports the mean and sample variance of ACL across that method's timely
successful seeds. Sample variance uses denominator k−1 and is undefined for
fewer than two successes. Exact rational calculations from integer Q avoid
rounding-based variance comparisons. This across-seed variance is distinct from
the within-embedding chain-length variance retained in the raw results.

Candidate mean/variance always use four successful seeds. MM mean/variance
use the displayed number of successes. The final column compares only identical
seeds where both methods succeeded; it is not the difference between unmatched
success-only means when MM has failed. A zero-success mean is missing, not zero.

| Family (ID; n) | MM timely / 4 | MM mean ACL | MM ACL s² | Candidate mean ACL | Candidate ACL s² | Common seeds | Paired mean Δ |
|---|---:|---:|---:|---:|---:|---|---:|
| barabasi_albert (10662; 122) | 4 | 3.40369 | 0.0195008 | 3.56148 | 0.00674102 | 0,1,2,3 | 0.157787 |
| bcc_lattice (33402; 91) | 4 | 1.2967 | 0.0189188 | 1.58516 | 0.00622912 | 0,1,2,3 | 0.288462 |
| binary_tree (4905; 127) | 4 | 1 | 0 | 1.08071 | 0.000511501 | 0,1,2,3 | 0.0807087 |
| bipartite (1363; 126) | 2 | 7.4881 | 0.000787352 | 4.49206 | 0 | 1,3 | -2.99603 |
| circulant (3499; 134) | 4 | 1.50746 | 0.00137373 | 1.48321 | 0.000533712 | 0,1,2,3 | -0.0242537 |
| complete (1041; 127) | 0 | — | — | 9.29528 | 2.06667e-05 | — | — |
| cubic_lattice (33219; 125) | 4 | 1.386 | 0.006416 | 1.864 | 0.013056 | 0,1,2,3 | 0.478 |
| cycle (1829; 126) | 4 | 1 | 0 | 1 | 0 | 0,1,2,3 | 0 |
| frustrated_square/king_graph (32616; 121) | 4 | 1.50207 | 0.00520798 | 1.95868 | 0.000591945 | 0,1,2,3 | 0.456612 |
| generalized_petersen (4083; 126) | 4 | 1.3373 | 0.0207651 | 1.67659 | 0.00232531 | 0,1,2,3 | 0.339286 |
| grid (1584; 128) | 4 | 1.08203 | 0.00311279 | 1.36914 | 0.00530497 | 0,1,2,3 | 0.287109 |
| hardware_native (37603; 128) | 4 | 1.45312 | 0.00854492 | 1.89648 | 0.00554911 | 0,1,2,3 | 0.443359 |
| honeycomb (32367; 190) | 4 | 1.04737 | 0.0012373 | 1.44211 | 0.00120037 | 0,1,2,3 | 0.394737 |
| hypercube (4755; 128) | 4 | 3.10156 | 0.0241292 | 3.09961 | 0.115779 | 0,1,2,3 | -0.00195312 |
| johnson (5242; 120) | 4 | 9.16875 | 0.570619 | 7.03542 | 0.00760995 | 0,1,2,3 | -2.13333 |
| kagome (32122; 131) | 4 | 1.16031 | 0.00252511 | 1.25191 | 0.000582717 | 0,1,2,3 | 0.0916031 |
| kneser (5411; 126) | 4 | 3.04762 | 0.0188964 | 3.43651 | 0.00407323 | 0,1,2,3 | 0.388889 |
| lfr_benchmark (31357; 100) | 4 | 1.665 | 0.0552333 | 1.8925 | 0.00449167 | 0,1,2,3 | 0.2275 |
| named_special (37761; 46) | 4 | 1.03804 | 0.00263863 | 1.09239 | 0.000748267 | 0,1,2,3 | 0.0543478 |
| path (2030; 141) | 4 | 1 | 0 | 1 | 0 | 0,1,2,3 | 0 |
| planted_solution (34404; 133) | 4 | 1.0188 | 1.88441e-05 | 1.11466 | 0.000240262 | 0,1,2,3 | 0.0958647 |
| random_er (6450; 133) | 4 | 7.69173 | 0.330526 | 6.48872 | 0.0278516 | 0,1,2,3 | -1.20301 |
| random_planar (31536; 152) | 4 | 1.71711 | 0.0184384 | 2.03783 | 0.00255006 | 0,1,2,3 | 0.320724 |
| regular (14334; 140) | 2 | 15.8143 | 1.02041 | 9.30893 | 0.00106718 | 0,3 | -6.5 |
| sbm (30736; 120) | 4 | 5.45 | 0.0664352 | 5.125 | 0.00550926 | 0,1,2,3 | -0.325 |
| shastry_sutherland (33018; 121) | 4 | 1.25826 | 0.00671061 | 1.37397 | 0.0146791 | 0,1,2,3 | 0.115702 |
| spin_glass (37302; 160) | 0 | — | — | 11.4656 | 1.30208e-05 | — | — |
| star (2229; 127) | 4 | 1.12992 | 0.000227334 | 1.07677 | 1.55e-05 | 0,1,2,3 | -0.0531496 |
| tree (5058; 121) | 4 | 1 | 0 | 1.10331 | 6.83013e-05 | 0,1,2,3 | 0.103306 |
| triangular_lattice (31879; 128) | 4 | 1.91797 | 0.0457967 | 2.36523 | 0.00689189 | 0,1,2,3 | 0.447266 |
| turan (3060; 90) | 3 | 7.42593 | 1.44572 | 5.90278 | 0.287521 | 1,2,3 | -1.25926 |
| watts_strogatz (22972; 174) | 3 | 13.3161 | 0.224832 | 9.70546 | 0.0133081 | 0,1,3 | -3.61494 |
| weak_strong_cluster (33587; 128) | 4 | 3.68359 | 0.0051473 | 3.36328 | 0.00148519 | 0,1,2,3 | -0.320312 |
| wheel (2429; 127) | 4 | 1.16732 | 0.000924835 | 1.54134 | 0.00121417 | 0,1,2,3 | 0.374016 |

The `frustrated_square/king_graph` row is one solver input, `ember_32616`,
representing original selected IDs 32816 and 32616. Both family labels remain
visible; every aggregate counts the structure once. All 34 normalized inputs
have different (n, m, sorted degree sequence) signatures, proving pairwise
nonisomorphism for this subset. This does not establish statistical independence.
The excluded original Sudoku family has no source or solver observation here.

Two source-matched aggregate views are necessary:

| Inclusion rule | Inputs | Candidate mean ACL | MM mean ACL | Candidate minus MM | Inputs lower / higher / equal candidate mean |
|---|---:|---:|---:|---:|---:|
| All four seeds timely for both | 28 | 2.261285635 | 2.222561782 | +0.038723854 | 7 / 19 / 2 |
| At least one common timely seed | 32 | 2.905942596 | 3.321129022 | -0.415186426 | 11 / 19 / 2 |

Each row first averages the matched successful seeds within each included source,
then weights those sources equally. The first aggregate is 1.74% worse for the
candidate; the second is 12.50% lower. The reversal arises from including the
partially successful dense MM cases and is a warning against choosing an
inclusion rule after seeing the result. Neither aggregate proves family-wide
superiority or credits the 14 failures. Complete/spin-glass have no common timely
MM seed and remain outside both conditional ACL aggregates.

For the 28 fully observed inputs, candidate sample variance is lower on 18,
higher on eight and equal on two. These are descriptive comparisons of only
four seeds on one source per represented family; they do not establish lower
population variance. The small hypercube mean improvement is only one qubit
over four calls: candidate Q = [462, 373, 374, 378], MM Q = [422, 381, 381, 404].
Its candidate sample variance is about 4.80 times MM's, so this is not a robust
mean/variance advantage.

Seed zero exactly replays all 34 candidate embeddings from 026, including chain
serialization, after the 028 optimization. Seed-zero contemporaneous MM pairing
gives seven lower ACL, 21 higher, two optimal ties and four candidate-only
successes. Seeds 1–3 give 31 lower, 55 higher, six optimal ties and ten
candidate-only successes. The additional seeds do not create new source samples
or a clean holdout. No historical 026/019 timing enters this experiment.

## Every unsuccessful observation

All 14 are MM `TIMEOUT` records. All have measured solver wall greater than
60 seconds and process return code zero; none was a hard watchdog kill. Ten
contain valid late embeddings and four contain no valid embedding. No late Q
or ACL in this table is credited to the success-only summaries above.

| Family / ID | Seed | Task ID | Solver s | Process s | Valid late Q | Diagnostic ACL |
|---|---:|---|---:|---:|---:|---:|
| complete / 1041 | 0 | `31025a73d89dafe4533ac318` | 63.049534 | 64.004706 | 1935 | 15.2362 |
| complete / 1041 | 1 | `5fdc3b8c14b536a5f7ecfa17` | 62.568450 | 63.420451 | 2098 | 16.5197 |
| complete / 1041 | 2 | `bfe19aebc667c2612146b879` | 62.065285 | 63.392192 | 2318 | 18.252 |
| complete / 1041 | 3 | `07895339afebda5c7b8b7a74` | 62.016782 | 62.769883 | 2461 | 19.378 |
| spin_glass / 37302 | 0 | `5d1fe8e4c1a582f0be26aa49` | 73.286505 | 74.202458 | — | — |
| spin_glass / 37302 | 1 | `034b54c4c2f4b171da6486b0` | 75.403328 | 76.615970 | — | — |
| spin_glass / 37302 | 2 | `fadb71f4bdfea8e55ce28477` | 69.929435 | 70.547610 | — | — |
| spin_glass / 37302 | 3 | `3ff38797c495aafad3645325` | 78.319689 | 79.466368 | — | — |
| bipartite / 1363 | 0 | `751dc7a133292ea809ed3d44` | 60.238676 | 61.444091 | 776 | 6.15873 |
| bipartite / 1363 | 2 | `6ce9ff40016b9efad921830d` | 60.463158 | 61.611316 | 777 | 6.16667 |
| regular / 14334 | 1 | `ee58663ca2ebd5258e97d279` | 61.649607 | 62.787679 | 2132 | 15.2286 |
| regular / 14334 | 2 | `8fc0fb83d70763ef63b0ffd4` | 61.245635 | 62.294417 | 2138 | 15.2714 |
| turan / 3060 | 0 | `e7e0c6889e86dbebede92199` | 61.620129 | 62.471480 | 793 | 8.81111 |
| watts_strogatz / 22972 | 2 | `98aa94e6b89bff2da50a4659` | 60.058753 | 61.418001 | 2357 | 13.546 |

The smallest overrun is 0.058753 seconds (Watts–Strogatz, seed 2); the largest
is 18.319689 seconds (spin-glass, seed 3). The same strict external deadline is
applied to both methods. These observations show reliability under this run's
deadline convention, not that the timeout instances are impossible or that MM
could never embed them under another budget.

## Optimality certificates

The exact frozen target has maximum degree Δ = 20. A connected k-qubit chain
has at least k−1 internal couplers, so at most (Δ−2)k+2 couplers can leave it.
A source vertex of degree d needs at least d outgoing couplers to distinct
neighbor chains. Therefore:

`k >= max(1, ceil((d - 2)/(Delta - 2)))`,

and summing over source vertices gives a necessary lower bound on Q. Every
validated returned chain was checked against its individual bound, the actual
number of couplers leaving that chain and the target-degree capacity; every
total Q satisfies the summed bound. A valid witness attaining the bound proves
optimality. The bound by itself does not prove feasibility or certify a larger
Q as optimal.

Exact attaining witnesses in 032 are: both methods on cycle and path, every
seed; MM on binary_tree and tree, every seed; and MM on named_special, seeds
0 and 1. All have ACL one. The eight paired optimal ties are exactly the four
cycle and four path pairs. No paired tie above ACL one occurred, and no
unresolved paired tie occurred. As an example of a nontrivial bound, star needs
at least 133 qubits, but its candidate witnesses use 136–137 and MM uses
142–146, so no star optimality claim is made. Acceptance of optimal ties as
meeting the project goal remains a separate user decision.

## Initialization and refinement diagnostics

All 136 spectral initializations completed without deadline/work-limit/dependency
or numerical failure: 122 report `residual_tolerance`, 14 `approximate`.
The fixed numerical limits are 64 iterations, tolerance 1e-5 and 50000000 work units.
Approximate results occur on honeycomb seeds 2–3; cycle and path seeds 0–3;
binary_tree seeds 2–3; and wheel seeds 1–2. Both cycle and path attain optimal
embeddings despite their approximate numerical initialization, so these records
do not establish that greater eigensolver accuracy would improve embedding Q.

Twenty-three initialization calls retain warnings (46 messages); 60 calls flag
an uncertain cutoff; and complete-graph seed 1 flags a rank-deficient reference
orientation. That call still records residual tolerance and returns a valid
1180-qubit embedding. No flag is hidden or treated as evidence of a failed
embedding. All 136 have complete component diagnostics. There are no dense-base
case solves in these selected inputs; the planted-solution input contains seven
components, including six isolates, and the other 33 inputs are connected.

Initialization work is at most 648620 of the fixed 50000000-unit limit; median
work is 77346. Mean initialization wall is 0.148462 seconds, median 0.116815,
maximum 0.813318. The audit checks component sizes/edges, operator nonzeros and
column-work accounting, tolerance labels against recorded residuals, recorded
orthogonality/centering diagnostics, cutoff-gap flags and nested timing. The
eigenvectors and initial order are not saved: residuals and lowest-mode selection
cannot be independently recomputed from vectors. These are diagnostic consistency
checks; final embedding validity is checked independently from physical edges.

Layout uses 1000 evaluations in 132 calls. The four named-special calls stop
at 779, 990, 973 and 830 evaluations for seeds 0–3. Contact refinement stops at
the group limit in 75 calls, work limit in 50, and no improvement in 11; none
stops because of a deadline. All recorded work, group, pass and region limits
pass their checks: at most 500000 shared work, 512 groups, four passes and a
512-qubit region. Actual passes are one or two.

The 4714 recorded accepted moves include 2517 equal-Q moves and 473 increases
in a group member's chain length, counting each affected member once per accepted
move. The complete accepted-move trajectories sum
to the recorded Q savings, equal-Q count, member-growth count and contact
redundancy change. Cumulative work is monotone, groups contain valid distinct
source vertices, total Q never increases, and every equal-Q acceptance has a
positive contact-redundancy gain. Aggregate constructed Q is 73983; pruning
reduces it to 62503; refinement saves 2350 more, giving final Q 60153. These
totals sum calls, not one composite embedding. Intermediate chain sets are not
saved, so trajectory arithmetic does not independently validate each intermediate
embedding. Rejected proposals are not reconstructable from these records.

## Contemporaneous timing

Each trial uses a fresh process and empty per-task JIT cache. Solver wall starts
before source/target copies and includes first-call compilation, initialization,
construction and refinement. Implementation imports and post-solve validation
are outside solver wall but inside controller process wall. Both timing measures
are retained; no per-trial time or seed is selected. Calls are sequential on
the same shared host, not an isolated machine performance test.

| Method | Calls measured | Mean solver s | Median solver s | Mean process s | Median process s |
|---|---:|---:|---:|---:|---:|
| MM | 136 | 12.519694 | 1.251478 | 13.311572 | 2.273678 |
| Fixed spectral candidate | 136 | 9.895627 | 8.423478 | 12.754724 | 10.908252 |

All-attempt means include MM's long unsuccessful calls and must not be read as
a universal candidate speed advantage. The paired ratios expose the smaller
inputs where candidate overhead is large:

| Ratio population | n | Median solver ratio | Maximum solver ratio | Solver ratios >10 | Median process ratio | Maximum process ratio | Process ratios >10 |
|---|---:|---:|---:|---:|---:|---:|---:|
| All attempts with measured times | 136 | 7.025469 | 28.412993 | 50 | 5.308095 | 14.275719 | 9 |
| Both methods timely and valid | 122 | 7.925897 | 28.412993 | 50 | 6.184611 | 14.275719 | 9 |

The largest ratios, 28.412993 solver and 14.275719 process, both occur on cycle
seed 2, where the two methods tie at ACL one. Candidate solver wall ranges from
3.365619 to 28.862586 seconds; MM ranges from 0.216741 to 78.319689 seconds,
including timeouts. The roughly 10× speed goal is not met uniformly. Four seeds
are too few for a stable tail estimate, and shared-host variation remains a
limitation even though all comparisons here are contemporaneous.

## Consequences and limits

The broad limitations persist with additional solver seeds: the fixed candidate
often produces longer chains on sparse inputs; exact cycle/path ties coexist
with higher runtime; and some mean improvements have higher variability. Dense
cases supply several large quality improvements and expose MM deadline failures,
but those results cannot be substituted for evidence of improvement on every
class. Lower observed variance on many fully observed inputs also does not
compensate for a higher mean on 19 of them.

This is a development replication, with one source per family label, fixed
solver seeds and no protected source sample. Seed zero was already used during
development; seeds 1–3 do not undo that source-level exposure. No significance
test, confidence claim, source-generalization claim, family-wide mean claim or
publication-success claim is made. Future changes must remain a single general
algorithm; these diagnostics do not justify family-specific dispatch or choosing
a successful seed after observing its output.

## Reproduction and additive audit artifacts

The retrieved archive is
`results/codex/retrieved/hyde03/032-solver-seed-replication/`.
Its immutable received files are untouched. The additive `analysis/` directory
contains the ordinary report/CSVs plus `independent_review.py`,
`ember_embedding_oracle.py`, `ember_initialization_seed_audit.py`,
`independent_review.json`, `independent_results.csv`, `independent_pairs.csv`,
`seed_zero_replay.csv`, and this note's generator. Original returned embeddings
remain in `results/<task_id>.json`.

```sh
.venv/bin/python scripts/codex/analyze_pilot.py results/codex/retrieved/hyde03/032-solver-seed-replication
.venv/bin/python results/codex/retrieved/hyde03/032-solver-seed-replication/analysis/independent_review.py results/codex/retrieved/hyde03/032-solver-seed-replication results/codex/retrieved/hyde03/026-corpus-spectral-initialization
```

For a repeat that leaves the original analysis files unchanged, append
`--output results/codex/032-independent-repeat` to the independent command.

The independent audit imports neither the pilot runner, the candidate nor the
graph generator. Its helpers use only the Python standard library. Its source
files and outputs are separately hashed in `analysis/audit_artifacts.json`.
This review is additive; no algorithm, runner, corpus or frozen result was edited.
