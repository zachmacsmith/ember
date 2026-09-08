# Independent review of connected-star pipeline experiment 039

2026-09-08. This complete-pipeline development screen is adverse for the fixed
connected-star policy: one input improves, three worsen, and 30 tie. Total Q
increases from **15,059 to 15,063**. All 68 returned embeddings are independently
valid on the original graphs and timely under their 60-second allowance. The
two connected moves save two qubits locally, while ordinary refinement saves
six fewer qubits overall. These results do not support promoting this policy.

No solver, embedding, prefix or MM call was made for this results audit. The
accepted 038 audit remains unchanged. Root owns the run lifecycle and retrieval;
this reviewer owns only additive 039 analysis artifacts and this note.

## Frozen provenance and completion

| Identity | Checked value |
|---|---|
| Production revision | `c61c474ca7bdd2f6e455cfa67f34af72b8d537cf` |
| Source map, 48 files | `63a0aed1a880cbf008aa68ae7201aed7a4da635dea9362e5d296b1d13a91a473` |
| Manifest bytes | `84197f8e3c2e4543ba5786eb51e31b1a57e1ade4de32c7ed51cb55d5d6a25bc3` |
| Transport, 154 files | `5fa828ca4db741120dcc2998f5bdb4d2f30563ae6c9b314709190262b85dce39` |
| Retrieved archive, 433 files | `9ad6f638f60242f51f79eb4002696c7222032bb76f8ff9406198a5ec40de4ed6` |
| Evaluator manifest, 103 listed files | `dc7632dd7d50cb72e81360f495d5b1a98c3a2ce68121c0ba4191dbfe9fa6c145` |
| Exact target | `38cde794d3c1461054a45b5a660d157737b019c19cb9a7b38e2027730e3d5938` |
| Terminal controller bytes | `33ea2fd7be40b7c9ab85cadf04102afecdb70c7e5954b5a26803c03d4378e1d5` |

Root launched controller 139008 once on hyde03 at 06:11:08 UTC; it completed at
06:24:51.479 UTC. Its detached supervisor exited zero. Root's subsequent process
inspection found the controller and last worker 139884 absent, no command
matching the run, and the inherited lock free. The retrieved terminal state
agrees with that separately hashed observation. All 68 unique workers returned
zero. Claims and supervisor records match the frozen task order exactly; their
measured spans do not overlap (minimum intervening gap 0.003310 seconds).
There are no missing worker records, restarts, process failures, dependency
violations, invalid outputs, whole-call timeouts or late diagnostic embeddings.

The audit checks every archived hash, the precise source map, the complete
transport inventory and both prescribed input/arm shuffles. The transport
contains the two ledgers, manifest, target, normalized graphs, source and tasks;
the raw originals and inverse label maps are evaluator-only files. Each original
node and edge maps exactly to its normalized input, and final embeddings are
validated again after restoring original source labels. Validation requires
exact source keys including isolates, nonempty disjoint target-member chains,
chain connectivity and coverage of every original source edge using the exact
original target edges. Q, ACL, maximum chain length, within-chain length variance
and physical contact redundancy R are independently recomputed. Within-chain
variance is not an across-seed ACL variance estimate.

Both methods use the pinned native environment, recorded Python 3.10.12,
NetworkX 3.4.2, NumPy 2.2.6, Numba 0.65.1, SciPy 1.15.3 and dwave-networkx
0.8.19. Every worker reports absent MM metadata, empty forbidden-import attempts
and no loaded embedding library, and imports the exact frozen native.py path.
The frozen worker also checks package absence before calling the candidate.
Its single-thread environment and distinct empty per-task JIT caches follow the
reviewed controller source. The source/protocol review and execution evidence
remain bound by their original hashes; no candidate imports were repeated by
the results auditor.

## Fixed-arm result and complete input table

The comparison retains all 34 original development structures, all 35 family
memberships and the explicit absence of original Sudoku. Frustrated-square and
king membership share one structure and contribute once to the aggregate.
Every call uses seed zero and the same 60-second allowance. The control is
`native-search-joint1-contacts-spectral`; the treatment changes only
`polish_star_policy='connected'`. No embeddings are selected or combined across
arms. Both have 34 timely successes, so the common-success population is all 34.

| Measure | Control | Connected |
|---|---:|---:|
| Timely valid calls | 34 / 34 | 34 / 34 |
| Total Q | 15,059 | 15,063 |
| Arithmetic mean of per-input ACL | 3.3351353061220093 | 3.337318881766284 |
| Total final physical R | 7,628 | 7,624 |
| Mean solver wall, seconds | 9.137039 | 9.315600 |
| Mean whole-process wall, seconds | 11.993923 | 12.186682 |

The mean ACL difference is +0.0021835756442747474, or +0.06547% relative to
control. Total Q rises 0.02656%; these are different weightings of the same
34 structures. Kagome improves by four qubits. Kneser worsens by four,
hypercube by one, and named_special by three. There are 28 unresolved quality
ties and two provably optimal ties, cycle and path, with ACL=1. These ties are
reported without assuming the user accepts them as satisfying a strict win.

For the exact target, n=4,800, m=45,864 and maximum degree Δ=20. Each connected
chain of size s has at most 20s−2(s−1)=18s+2 outgoing couplers. A source vertex
of degree d therefore requires at least max(1, ceil((d−2)/18)) qubits. The audit
checks this bound and actual outgoing-coupler counts for every returned chain.
The sum gives the per-input lower bound in pairs.json. Only the cycle/path ties
attain it; nonattainment is not a proof that the bound can be attained.

Values below are rounded only for display; pairs.json/csv retain exact Q/n
fractions and full timing precision. The separate memberships.json/csv expands
all 35 labels as display records, without adding a second aggregate observation.

| Family / input | n / m | Status / valid, off; connected | Q, off → connected | ΔQ | ACL, off / connected | Maximum chain, off / connected | R, off / connected | Solver s, off / connected | Process s, off / connected | Result |
|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---|
| barabasi_albert / ember_10662 | 122 / 472 | SUCCESS / True; SUCCESS / True | 444 → 444 | 0 | 3.639 / 3.639 | 10 / 10 | 106 / 106 | 8.216 / 8.278 | 11.119 / 10.821 | unresolved_tie |
| bcc_lattice / ember_33402 | 91 / 216 | SUCCESS / True; SUCCESS / True | 152 → 152 | 0 | 1.670 / 1.670 | 6 / 6 | 23 / 23 | 5.550 / 5.552 | 7.497 / 7.497 | unresolved_tie |
| binary_tree / ember_4905 | 127 / 126 | SUCCESS / True; SUCCESS / True | 138 → 138 | 0 | 1.087 / 1.087 | 3 / 3 | 4 / 4 | 10.662 / 10.582 | 14.020 / 13.820 | unresolved_tie |
| bipartite / ember_1363 | 126 / 3969 | SUCCESS / True; SUCCESS / True | 566 → 566 | 0 | 4.492 / 4.492 | 5 / 5 | 0 / 0 | 8.921 / 8.489 | 11.827 / 10.808 | unresolved_tie |
| circulant / ember_3499 | 134 / 402 | SUCCESS / True; SUCCESS / True | 198 → 198 | 0 | 1.478 / 1.478 | 2 / 2 | 99 / 99 | 6.929 / 6.601 | 10.431 / 9.969 | unresolved_tie |
| complete / ember_1041 | 127 / 8001 | SUCCESS / True; SUCCESS / True | 1180 → 1180 | 0 | 9.291 / 9.291 | 10 / 10 | 1530 / 1530 | 14.991 / 14.942 | 18.413 / 18.390 | unresolved_tie |
| cubic_lattice / ember_33219 | 125 / 300 | SUCCESS / True; SUCCESS / True | 224 → 224 | 0 | 1.792 / 1.792 | 5 / 5 | 42 / 42 | 6.953 / 10.088 | 10.171 / 13.840 | unresolved_tie |
| cycle / ember_1829 | 126 / 126 | SUCCESS / True; SUCCESS / True | 126 → 126 | 0 | 1.000 / 1.000 | 1 / 1 | 0 / 0 | 10.188 / 5.585 | 14.501 / 9.318 | certified_optimal_tie |
| frustrated_square / king_graph / ember_32616 | 121 / 420 | SUCCESS / True; SUCCESS / True | 243 → 243 | 0 | 2.008 / 2.008 | 4 / 4 | 144 / 144 | 9.636 / 13.381 | 13.034 / 17.406 | unresolved_tie |
| generalized_petersen / ember_4083 | 126 / 189 | SUCCESS / True; SUCCESS / True | 212 → 212 | 0 | 1.683 / 1.683 | 5 / 5 | 17 / 17 | 6.906 / 6.944 | 10.009 / 10.159 | unresolved_tie |
| grid / ember_1584 | 128 / 232 | SUCCESS / True; SUCCESS / True | 173 → 173 | 0 | 1.352 / 1.352 | 3 / 3 | 15 / 15 | 11.077 / 11.366 | 14.216 / 14.669 | unresolved_tie |
| hardware_native / ember_37603 | 128 / 352 | SUCCESS / True; SUCCESS / True | 250 → 250 | 0 | 1.953 / 1.953 | 5 / 5 | 20 / 20 | 6.022 / 6.078 | 7.630 / 8.454 | unresolved_tie |
| honeycomb / ember_32367 | 190 / 264 | SUCCESS / True; SUCCESS / True | 273 → 273 | 0 | 1.437 / 1.437 | 4 / 4 | 14 / 14 | 7.766 / 7.666 | 10.374 / 10.167 | unresolved_tie |
| hypercube / ember_4755 | 128 / 448 | SUCCESS / True; SUCCESS / True | 457 → 458 | 1 | 3.570 / 3.578 | 7 / 7 | 70 / 71 | 6.579 / 6.863 | 8.455 / 8.742 | higher_acl |
| johnson / ember_5242 | 120 / 1680 | SUCCESS / True; SUCCESS / True | 846 → 846 | 0 | 7.050 / 7.050 | 12 / 12 | 653 / 653 | 8.829 / 10.756 | 11.361 / 14.123 | unresolved_tie |
| kagome / ember_32122 | 131 / 236 | SUCCESS / True; SUCCESS / True | 166 → 162 | -4 | 1.267 / 1.237 | 3 / 2 | 36 / 28 | 6.321 / 6.371 | 9.051 / 8.896 | lower_acl |
| kneser / ember_5411 | 126 / 315 | SUCCESS / True; SUCCESS / True | 420 → 424 | 4 | 3.333 / 3.365 | 7 / 7 | 45 / 50 | 7.979 / 9.879 | 10.862 / 13.912 | higher_acl |
| lfr_benchmark / ember_31357 | 100 / 204 | SUCCESS / True; SUCCESS / True | 189 → 189 | 0 | 1.890 / 1.890 | 6 / 6 | 46 / 46 | 6.729 / 6.681 | 9.766 / 9.569 | unresolved_tie |
| named_special / ember_37761 | 46 / 69 | SUCCESS / True; SUCCESS / True | 50 → 53 | 3 | 1.087 / 1.152 | 2 / 2 | 2 / 4 | 4.325 / 3.818 | 7.155 / 6.295 | higher_acl |
| path / ember_2030 | 141 / 140 | SUCCESS / True; SUCCESS / True | 141 → 141 | 0 | 1.000 / 1.000 | 1 / 1 | 0 / 0 | 12.127 / 12.136 | 17.134 / 17.170 | certified_optimal_tie |
| planted_solution / ember_34404 | 133 / 175 | SUCCESS / True; SUCCESS / True | 145 → 145 | 0 | 1.090 / 1.090 | 3 / 3 | 8 / 8 | 6.039 / 6.119 | 9.114 / 8.710 | unresolved_tie |
| random_er / ember_6450 | 133 / 870 | SUCCESS / True; SUCCESS / True | 892 → 892 | 0 | 6.707 / 6.707 | 11 / 11 | 148 / 146 | 8.635 / 8.322 | 11.114 / 10.611 | unresolved_tie |
| random_planar / ember_31536 | 152 / 450 | SUCCESS / True; SUCCESS / True | 300 → 300 | 0 | 1.974 / 1.974 | 6 / 6 | 117 / 117 | 7.902 / 8.165 | 9.752 / 10.120 | unresolved_tie |
| regular / ember_14334 | 140 / 2800 | SUCCESS / True; SUCCESS / True | 1304 → 1304 | 0 | 9.314 / 9.314 | 11 / 11 | 522 / 522 | 16.574 / 16.989 | 19.389 / 20.209 | unresolved_tie |
| sbm / ember_30736 | 120 / 625 | SUCCESS / True; SUCCESS / True | 616 → 616 | 0 | 5.133 / 5.133 | 8 / 8 | 123 / 121 | 8.604 / 8.662 | 11.761 / 11.877 | unresolved_tie |
| shastry_sutherland / ember_33018 | 121 / 270 | SUCCESS / True; SUCCESS / True | 162 → 162 | 0 | 1.339 / 1.339 | 3 / 3 | 47 / 47 | 9.069 / 5.579 | 13.188 / 7.746 | unresolved_tie |
| spin_glass / ember_37302 | 160 / 12720 | SUCCESS / True; SUCCESS / True | 1835 → 1835 | 0 | 11.469 / 11.469 | 12 / 12 | 2500 / 2500 | 17.552 / 17.679 | 19.394 / 19.746 | unresolved_tie |
| star / ember_2229 | 127 / 126 | SUCCESS / True; SUCCESS / True | 137 → 137 | 0 | 1.079 / 1.079 | 11 / 11 | 2 / 2 | 5.756 / 6.096 | 7.699 / 8.195 | unresolved_tie |
| tree / ember_5058 | 121 / 120 | SUCCESS / True; SUCCESS / True | 134 → 134 | 0 | 1.107 / 1.107 | 5 / 5 | 2 / 2 | 5.272 / 5.338 | 7.197 / 7.305 | unresolved_tie |
| triangular_lattice / ember_31879 | 128 / 384 | SUCCESS / True; SUCCESS / True | 287 → 287 | 0 | 2.242 / 2.242 | 4 / 4 | 142 / 142 | 12.814 / 12.521 | 16.126 / 15.231 | unresolved_tie |
| turan / ember_3060 | 90 / 2700 | SUCCESS / True; SUCCESS / True | 460 → 460 | 0 | 5.111 / 5.111 | 7 / 7 | 51 / 51 | 8.210 / 7.139 | 10.206 / 9.080 | unresolved_tie |
| watts_strogatz / ember_22972 | 174 / 1740 | SUCCESS / True; SUCCESS / True | 1712 → 1712 | 0 | 9.839 / 9.839 | 14 / 14 | 343 / 343 | 16.083 / 20.165 | 18.794 / 23.789 | unresolved_tie |
| weak_strong_cluster / ember_33587 | 128 / 1988 | SUCCESS / True; SUCCESS / True | 427 → 427 | 0 | 3.336 / 3.336 | 7 / 7 | 729 / 729 | 8.735 / 8.868 | 11.717 / 11.963 | unresolved_tie |
| wheel / ember_2429 | 127 / 252 | SUCCESS / True; SUCCESS / True | 200 → 200 | 0 | 1.575 / 1.575 | 11 / 11 | 28 / 28 | 12.710 / 13.034 | 15.316 / 15.738 | unresolved_tie |

## Whole-pipeline accounting and failed work

All 68 diagnostic audits pass. The audit reconstructs trajectory Q from the
pruned total and recorded savings, and reconciles the result with independently
validated final chains. It recounts final physical R and checks every signed
change, including possible negative changes on a strict Q improvement.
Initial/intermediate R is inferred backwards from final R and the trace; it is
not independently measured from missing intermediate embeddings.

| Saved accounting quantity, summed over each arm | Control | Connected |
|---|---:|---:|
| Constructed Q | 18,490 | 18,490 |
| Pruned Q | 15,676 | 15,676 |
| Ordinary Q savings | 617 | 611 |
| Connected Q savings | 0 | 2 |
| All refinement Q savings | 617 | 613 |
| Ordinary accepted moves | 1,163 | 1,149 |
| Connected accepted moves | 0 | 2 |
| Ordinary groups visited | 14,528 | 14,435 |
| Ordinary work | 10,585,018 | 10,341,645 |
| Auxiliary work | 0 | 693,724 |
| Total shared work | 10,585,018 | 11,035,369 |

Auxiliary work is exactly **11,896 setup + 681,511 query + 317 refresh**.
It remains inside the same active visit and 500,000-unit whole-call budget;
its total is limited to 25,000 per call. All per-visit ordinary, proposal,
refresh and total amounts reconcile, including incomplete work and zero-charge
attempts after disabling the cache. This connected query has no separate
2,048-unit cap: 38 attempts exceed that amount, and the largest query consumes
24,736 units. Twenty-six calls reach the exact 25,000-unit auxiliary allowance.
There are 25 complete cache builds and 34 successful refreshes. Recorded final
stops are identical in count for both arms: 19 group-limit, 13 work-limit and two
no-improvement calls. Auxiliary interruption is distinct from a whole-call
timeout; no whole call times out here.

There are 4,045 auxiliary considerations: two accepted, 114 completed heuristic
non-proposals, 47 auxiliary-limit reports, 2,906 disabled checks, 872 too-few-leaf
rejections and 104 zero-excess rejections. The 140 started core queries include
two certified proposals, 114 completed heuristic rejections and 24 interrupted
queries. Completed rejection details are 83 no-root, 23 center-ceiling and eight
steering-exhausted. These outcomes do not prove block or source infeasibility.
A maximum assignment concerns one fixed center footprint, and the one-root,
bounded-growth heuristic does not enumerate all footprints or roots.

Only two covering assignments are reported, and both become returned certificates
and committed moves; none is discarded between certification and commit.
The audit distinguishes these counters instead of assuming a matching success
is a committed result. One commit records center growth, and neither has negative
R gain. No committed center exceeds the target maximum degree in this screen,
although the policy permits such centers and its separate synthetic witness does
exercise that case.

| Input / committed block | Block Q before → after | Retained center sizes | Committed member growth | Signed R gain | Whole-input Q, control → connected |
|---|---:|---|---:|---:|---:|
| Kagome, center degree 4, two independent leaves | 7 → 6 | 1 → 2 → 3 → 4 | 1 | +2 | 166 → 162 |
| named_special, center degree 3, three independent leaves | 6 → 5 | 1 → 2 | 0 | 0 | 50 → 53 |

The Kagome retained growth includes a steering step whose recorded deficit rises
from one to two before later falling to zero. That is consistent with center
growth taking a site away from a leaf assignment. The saved added-site IDs allow
exact reconstruction of retained center sites, connectivity and physical edge
boundary. Old individual chain lengths, outside ownership, leaf assignments,
discarded successor states and complete BFS paths are not saved. Accordingly,
block certificate and member-growth arithmetic are checked for consistency;
full intermediate physical validity and the exact previous center length cannot
be independently reconstructed. Final original-graph validity is independently
established for every call.

Across core queries, the recorded totals are 589 generated root encounters,
25 duplicate encounters, 276 root candidates and 56 published selected roots.
There are 1,682 successor candidates, 269 trials, 266 completed successors and
two first-zero terminations. Steering performs 31 searches, visits 2,881 nodes
and retains 12 steering steps. The sum of per-query leaf counts is 947 and of
per-query distinct demand-class counts is 821; those are not global distinct
vertex/class counts. There are 334 completed maximum assignments, 460 direct
assignments and six successful augmentations. The reported footprint peak
is eight sites; the largest independently reconstructed retained center has seven. All saved class memberships are checked against the source's
frozen outside-neighbor sets, and retained center boundary/connectivity and
copy/work arithmetic are checked against the original target.

Uncertified considerations consume **682,742 work units**: 11,565 setup and
671,177 query. This includes unsuccessful selection/search work and zero-charge
disabled records, not just promising queries. Committed proposals consume
10,665 units including setup; all refreshes consume another 317. Thus 98.42% of
auxiliary work occurs in uncertified considerations. Eligibility checks and
class-site edge checks are the two largest charged stages, 213,308 and 212,767
units respectively. Uncommitted visits consume 10,447,799 total units, while
committed visits consume 587,570; both populations remain in the work totals.

The adverse total is not explained away by the two strict local improvements.
Kagome gains one qubit from its connected move and three additional ordinary
savings. named_special gains one locally but has four fewer ordinary savings.
Kneser and hypercube accept no connected move, use their entire auxiliary share
and lose four and one ordinary qubit savings respectively. Their shared work
cap ends the ordinary sequence earlier. Globally, auxiliary work rises 693,724,
ordinary work falls 243,373, and total work rises 450,351. This screen therefore
exposes both unproductive query cost and later-trajectory effects. It supports
retaining these lessons before a separately specified general refinement; it
supplies no justification for choosing a method by graph family or observed
outcome.

## Timing, replay and scientific limits

All timing comparisons here are within 039 on hyde03. The median paired
connected/control solver ratio is 1.007378, mean 1.017006, range 0.548183–1.450865.
For whole-process wall the corresponding values are 1.005996, 1.015800 and
0.587347–1.360778. The maximum connected solver wall is 20.164860 seconds, well
inside the 60-second allowance. Solver CPU totals are 310.634221 versus
316.709356 seconds. The recorded contact phase totals are 38.249547 versus
40.832986 seconds; connected proposal wall is 1.386770 seconds and includes
0.021549 seconds of setup. These component timings are nested, not additive
whole-pipeline speed improvements.

The workers are fresh processes with empty per-task JIT caches, so compilation
remains charged to solver execution. Implementation imports and post-return
harness validation are outside the solver clock and inside process wall; graph
copies and the full candidate call are inside solver wall. The machine is Linux
x86_64, with affinity allowing CPUs 0–31 and fixed single-thread settings. It is
not an exclusively reserved core. Observed one-minute load spans 11.376953 to
16.950195. There is one timing sample per input/arm; load, process startup,
compilation and cache effects preclude attributing the large individual timing
changes to the small auxiliary rule alone.

All 34 within-pair layout, spectral initialization, conversion, completion,
constructed-Q and pruned-Q records match after removing timing fields. Each arm
has 32 residual-tolerance initializations and two approximate initializations.
The recorded initialization arithmetic and residual-based classifications pass
the independent helper; eigenvectors are not saved and residuals are not
recomputed. Exact recorded upstream equality is not identity of unsaved
intermediate chains or geometry.

The historical 037 control is checked against its accepted archive digest
`84aac4c4a530e3c07f78366eb35407e139d5f85fde5bcdf6b697f26d94379a25`.
All 34 control embeddings, including serialized chain order, and all complete
non-time diagnostics exactly replay 037. This is separate consistency evidence.
No historical time ratio, historical MM comparison or pooled timing population
is constructed. One seed on inherited development structures establishes neither
family population means, across-seed ACL variance nor unseen-instance performance.
There is no MM arm in 039 and no across-family research claim.

## Independent repeat, corrections and frozen outputs

The first complete audit passed with 68 checked diagnostic records. Root read the
main provenance, original-label, worker, validity and scoring logic and independently
repeated the frozen `analysis001/analyze.py`: all ten JSON outputs were byte-identical.
The original summary hash is
`67eccd238f4ce940ff50d58fc3bcde854cac4465eb0f54a837640d4c2c40c8b3`.
Root's ordinary analyzer and independent rational pairing also agree on the result.

Two auditor-only corrections are preserved explicitly. Raw hash enumeration was
restricted to the verified archive inventory plus retrieval.json so later additive
analysis files cannot change a repeat; all ten JSON and three CSV tables remained
byte-identical. A later report inspection caught mislabeled load-average summary
keys: the second/third tuple entries describe five/fifteen minutes, not two/three.
The final reviewed summary changes only those keys. All nine other JSON tables are
byte-identical, and the two summaries are exactly equal after those key renames.
The saved comparisons and local `os.getloadavg` documentation make this correction
reviewable without another full root execution. Root independently accepted the
exact two-site source diff and verified all nine non-summary tables against its
repeat; the final summary matches after only the eight load-window key renames.
That acceptance is saved in root-final-correction-comparison.json. A separate ad hoc display command
accessed a null off-arm auxiliary record before filtering; its correction is retained
and did not affect any auditor run or benchmark result. No solver reruns occurred.

The connected helper passed 12 stdlib test methods, including four previously saved
core traces and 20 corruption subcases, before reading 039 outcomes. Checks include
negative signed R on a degree-22 Z12 witness, center growth, interrupted work,
post-certificate deadline rejection, failed refresh preserving a commit, the off
path and a query above 2,048 units. Its saved earlier check iterations also passed.
These are auditor checks, not additional observations in the benchmark population.

Final reviewed outputs are in `results/codex/039-results-review/final-reviewed/`;
full per-input mechanism totals and the displayed table are in
`reviewed-report-tables/`. The all-input, membership, original validity, raw
provenance, initialization, history, detailed query/visit/maintenance records and
missing-original-family tables remain independently inspectable. The earlier
successful executions and root repeat are preserved.

| Final audit artifact | SHA256 |
|---|---|
| Main analyzer | `faeeb51321a2ff72003dbd7d31f31963892e61ed664ca3fad79f2d7ee61ee77e` |
| Connected diagnostic helper | `6ad65fd6e6d34827b32c27527c0a0d45acd5d3d7f27e2c4995f20e13dffaed2e` |
| Original embedding oracle | `e4718c2ec09f3ec80e035ef89648f81b45413f52c7580123ef129419b25612d9` |
| Initialization helper | `0043f26c6d624ab2825ab8e0018435adf751df9fe5897c47b3d45e4e62d88d5d` |
| Final reviewed summary | `4ea7dc4e152f2d082a08547ed651454d5138f1488f41ebb7635084d49031880c` |
| Detailed records | `3b7cf67730a74a583e82fa1097a94b284300089e1a975c408931926a639450e6` |
| Report table generator | `dcdebbbdd759d9adec638f5cc532433e748f44ada9c96f4177af53c49e3b9a10` |

For a fresh standalone repeat, choose a new output directory:

```sh
.venv/bin/python -B results/codex/039-results-review/final-reviewed/analyze.py results/codex/retrieved/hyde03/039-connected-star-pipeline results/codex/retrieved/hyde03/037-induced-star-pipeline --output results/codex/039-results-review/new-repeat
```
