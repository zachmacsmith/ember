# Independent review of experiment 036

Keep the corrected recurrence globally because it repairs the independently
verified class-capacity defect. This screen does not demonstrate a quality or
runtime improvement. All 34 corrected calls are timely valid successes, with
**9 wins, 17 ties, and 8 losses** against the original 033 spectral controls.
Total final qubits are **15,060 in both runs**, while mean per-input ACL worsens
slightly from **3.334421 to 3.335319**. Every regression is retained below.

This independent review follows the
[saved protocol](036_converter_correction_pipeline.md); its scripts do not
import an embedding algorithm or alter frozen experiment files.

## Preflight

The preflight passed before launch on 2026-09-08.

The [preflight script](../../../results/codex/036-independent-review/preflight.py)
and [complete evidence](../../../results/codex/036-independent-review/preflight.json)
verify all 46 frozen source files in both 033 and 036. Exactly one file differs:
`field.py`, from SHA256
`6d717696317192ad0df4f0fb6f5a26bb1da0dc4f57408cfad7ac810bb1a1fbfd`
to `a055553988ba3db17ef3588986c1719070c3fcfae4bbfcce7a7084ffe45c7690`.
The latter is the reviewed 035 correction. The 036 source snapshot is
`56338bafc7038d75001fe9fd36b067f246dc13ab796a2fdd29ded59b3226f243`,
from commit `18ab7590e1267c6281e4c8c4443fa00b73887228`.

All 37 copied input files are byte-identical: 34 source graphs, the target, and
both selection records. Selection, source, target, and topology digests also
recompute correctly. Every new task matches its 033 spectral control exactly
after removing only the task ID and source snapshot. There are precisely 34
tasks, seed 0, 60 seconds, one fixed spectral search configuration and the
unchanged default singleton policy `legacy`. No MM task is present.

The candidate interpreter is the preserved
`/Users/dabh/ember/.venv/codex-native/bin/python` symlink. Its environment has no
`minorminer`, `_minorminer`, `minorminer_fork`, or `busclique` module. Versions
are NumPy 2.2.6, SciPy 1.15.3, NetworkX 3.4.2, Numba 0.65.1, and
dwave-networkx 0.8.19, matching the reference. The unchanged pilot sets the four
BLAS/OpenMP/Numba thread limits to one, executes tasks sequentially, creates a
fresh task-specific JIT directory, checks imports and original graphs, and
enforces its existing worker/controller watchdogs. Presence of archived MM
adapter files in the frozen package is not evidence of their use: the candidate
loads the native entrypoint and forbids those dependency imports at runtime.
The completed audit below verifies these worker observations as well.

Before approval, 036 had no controller and all result, worker-result, claim,
cache, and log directories were empty. The prior 033 controller reported
completion, and process inspection confirmed controller 33003 and final worker
34600 absent. The checked-file hash-map digest is
`5428dc63d9a38e4b05ac4f5bffb34951a9d666b2790f361cd644f42489813721`.

One numerical qualification applies to 035's restricted exact class-assignment
claim: the helper starts cost accumulation at `0.0`. Exact integer cost
comparisons require accumulated spans to remain exactly representable in
binary64. The declared Z12 coordinates and problem sizes, and all 035 fixtures,
are far within that range. This audit makes no arbitrary huge-integer
exactness claim and does not change frozen source. This qualification is
separate from the already documented gap between interval-class feasibility
and complete physical seating on defective or missing-endpoint lanes.

The preflight script intentionally refuses to run after launch and opens its
output exclusively. Preserve its original evidence. The separate result
auditor rechecks frozen hashes and validates every final embedding in both
036 and the 34 original 033 controls, without invoking an embedding algorithm.

## Completed result verification

Root verified completion at 04:10:39.553752 UTC on 2026-09-08, after the
controller recorded finish time `1788840602.8600562`. Its launching process
exited zero; controller 38178 and final worker 39628 were absent. The saved
[completion record](../../../results/codex/036-launch/completion.json) documents
these process checks. The full result audit began only after this notification.

The [result auditor](../../../results/codex/036-independent-review/analyze.py)
rechecked all preflight file hashes and both complete manifests. It checked
every task identity and configuration, final/worker-result agreement, and all
34 new plus 34 original control embeddings against their original source and
target graphs. Independent checks cover source coverage, nonempty chains,
integer target membership, duplicate/disjoint occupancy, connected chains,
every logical edge, qubits, ACL, maximum chain length, within-chain variance,
and logical-edge contact redundancy. All pass. Reported refinement trajectories
also reconcile with final qubits and stay within declared group/work limits.

All 68 checked workers report the isolated interpreter, frozen native module,
empty per-task JIT policy, unique process and cache identities within each run,
matching dependency versions, and no prohibited imports or loaded embedding
libraries. Every success is within 60 seconds, with zero reported overrun.
The source/target inputs remain byte-identical. The comparison contains no new
MM observations and forms no local/remote timing ratio.

The [full per-input CSV](../../../results/codex/036-independent-review/final/pairs.csv)
contains all stage counts and times; the
[checked details](../../../results/codex/036-independent-review/final/details.json)
include validation results, final chain-set hashes, refinement checks, and
upstream differences. The raw final, worker, and task record hash-map digest is
`a240fc7cf70c20c585c702d091eecbd2a06e6ba91c4239903f106f45485173b1`.

## Physical stages and attribution

All 34 stored non-time spectral-initialization and layout diagnostics match
exactly, including final orders, ranks, proxy values, and search counts. This
removes the observed upstream-summary differences that complicated earlier
cross-run comparisons. Stored summaries still do not constitute a complete
internal-state trace, so their equality is not a proof of byte-identical
hidden placement state.

Every conversion in both runs reports zero misses and zero flips. Every
completion counter is zero: no reported missing logical edges, extensions,
extension qubits, bridges, or corner deficits. Thus the specific incomplete
seating witnesses from 034 do not appear as conversion failures in this screen.
The correction can still change feasible class assignments and subsequent
physical search. Only three final chain sets match exactly between the runs.

Reported constructed qubits fall by three overall, from 18,509 to 18,506, and
change on two inputs. After pruning, qubits instead rise by five, from 15,675
to 15,680, with nine inputs changed. Refinement saves 615 versus 620 qubits,
leaving equal final totals. More refinement savings are therefore not a final
quality gain over control. Accepted moves change from 1,176 to 1,171; equal-size
moves from 607 to 592; total charged refinement work from 10,624,904 to
10,576,968. Both runs stop 20 refinements at the group limit, 12 at the work
limit, and two with no improvement. These stage summaries come from recorded
diagnostics; intermediate chains were not saved for independent revalidation.
Final chains were independently validated.

The largest favorable final changes are random-planar input 31536 (−6 qubits)
and hypercube input 4755 (−5). The largest regressions are LFR input 31357 (+5)
and kagome input 32122 (+4). Those labels are evaluation metadata, not solver
inputs or implementation branches. The total-Q tie and slight mean-ACL loss
are both reported because these summaries weight source sizes differently.
One seed on these inherited development graphs estimates neither across-seed
ACL variance nor performance on unseen instances.

## All input pairs

All rows are timely valid successes; negative ΔQ favors corrected conversion.
ACL is final Q divided by the listed vertex count. Stage counts are solver
diagnostics, final Q is independently checked. Solver times are descriptive
observations from separate local runs.

| Source / mapped family | n | Constructed Q old→new | Pruned Q old→new | Refinement saved old→new | Final Q old→new | ΔQ | Solver seconds old→new |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 33587 / weak_strong_cluster | 128 | 450→450 | 435→435 | 10→8 | 425→427 | +2 | 7.577→7.278 |
| 1041 / complete | 127 | 1184→1184 | 1180→1180 | 0→0 | 1180→1180 | +0 | 13.443→15.348 |
| 32367 / honeycomb | 190 | 471→471 | 294→294 | 21→21 | 273→273 | +0 | 6.614→6.697 |
| 1584 / grid | 128 | 308→308 | 197→197 | 24→24 | 173→173 | +0 | 5.264→5.348 |
| 31879 / triangular_lattice | 128 | 380→380 | 332→332 | 45→45 | 287→287 | +0 | 5.957→5.989 |
| 37603 / hardware_native | 128 | 399→397 | 279→278 | 30→28 | 249→250 | +1 | 5.615→5.592 |
| 37302 / spin_glass | 160 | 1840→1840 | 1837→1837 | 1→1 | 1836→1836 | +0 | 21.775→20.287 |
| 1829 / cycle | 126 | 252→252 | 133→134 | 7→8 | 126→126 | +0 | 4.390→4.021 |
| 33219 / cubic_lattice | 125 | 356→356 | 245→245 | 21→21 | 224→224 | +0 | 6.005→5.226 |
| 1363 / bipartite | 126 | 776→776 | 568→568 | 2→2 | 566→566 | +0 | 8.192→7.841 |
| 2030 / path | 141 | 282→282 | 144→144 | 3→3 | 141→141 | +0 | 4.511→4.150 |
| 2229 / star | 127 | 286→286 | 137→137 | 0→0 | 137→137 | +0 | 5.869→5.653 |
| 3499 / circulant | 134 | 269→269 | 211→211 | 12→13 | 199→198 | -1 | 5.200→4.957 |
| 5411 / kneser | 126 | 557→557 | 465→467 | 42→47 | 423→420 | -3 | 6.821→6.247 |
| 10662 / barabasi_albert | 122 | 555→555 | 465→465 | 21→21 | 444→444 | +0 | 7.368→6.771 |
| 31357 / lfr_benchmark | 100 | 292→292 | 219→219 | 35→30 | 184→189 | +5 | 5.660→5.276 |
| 33402 / bcc_lattice | 91 | 244→244 | 165→166 | 12→14 | 153→152 | -1 | 5.106→5.073 |
| 14334 / regular | 140 | 1333→1333 | 1314→1314 | 10→10 | 1304→1304 | +0 | 9.412→8.912 |
| 30736 / sbm | 120 | 680→680 | 631→631 | 14→15 | 617→616 | -1 | 7.944→6.919 |
| 4083 / generalized_petersen | 126 | 346→346 | 236→236 | 27→24 | 209→212 | +3 | 6.520→5.391 |
| 6450 / random_er | 133 | 951→951 | 906→906 | 13→14 | 893→892 | -1 | 7.985→7.593 |
| 32616 / frustrated_square / king_graph | 121 | 324→324 | 269→269 | 28→26 | 241→243 | +2 | 6.079→5.632 |
| 5058 / tree | 121 | 255→255 | 136→137 | 4→3 | 132→134 | +2 | 5.885→4.917 |
| 32122 / kagome | 131 | 286→286 | 200→200 | 38→34 | 162→166 | +4 | 5.639→5.068 |
| 3060 / turan | 90 | 547→547 | 461→461 | 1→1 | 460→460 | +0 | 7.178→6.555 |
| 37761 / named_special | 46 | 99→99 | 64→62 | 15→12 | 49→50 | +1 | 2.794→3.057 |
| 4905 / binary_tree | 127 | 269→269 | 145→145 | 6→7 | 139→138 | -1 | 5.080→4.639 |
| 2429 / wheel | 127 | 312→312 | 240→240 | 40→40 | 200→200 | +0 | 7.392→6.448 |
| 33018 / shastry_sutherland | 121 | 274→274 | 187→189 | 25→27 | 162→162 | +0 | 5.165→4.947 |
| 22972 / watts_strogatz | 174 | 1793→1792 | 1746→1745 | 34→33 | 1712→1712 | +0 | 10.333→9.915 |
| 5242 / johnson | 120 | 876→876 | 865→865 | 19→19 | 846→846 | +0 | 7.930→8.002 |
| 31536 / random_planar | 152 | 409→409 | 329→329 | 23→29 | 306→300 | -6 | 7.887→7.555 |
| 34404 / planted_solution | 133 | 280→280 | 156→158 | 10→13 | 146→145 | -1 | 5.204→4.641 |
| 4755 / hypercube | 128 | 574→574 | 484→484 | 22→27 | 462→457 | -5 | 6.830→6.377 |

## Runtime limits and retained decision

Observed total solver wall time is 240.625→228.323 seconds and full process
time 276.497→261.206 seconds. This is not an isolated converter speed estimate:
the unchanged layout stage alone changes from 192.451 to 183.020 seconds,
and refinement from 40.703 to 37.706 seconds. Both runs used `dabhmbp`, but
one-minute load observations span 6.881–45.972 in the control and 15.839–51.738
in the corrected run. Tasks were not interleaved between treatments. The
protocol therefore does not support attributing the runtime decrease to the
converter change.

Retain the separate 035 difficult-line result: the feasible nine-arm Z12
witness grows from 30 to 240 peak states and from 0.293 to 1.816 milliseconds
mean warm converter time, a 6.21-fold slowdown. The broader 036 calls complete
within their deadlines but do not establish a general state-growth or runtime
bound. The corrected restricted recurrence remains the fixed development
implementation because of its capacity correctness, with no per-input switch
to the defective recurrence. Further physical-quality improvement still needs
a separate general mechanism and its own cumulative evaluation.

## Safe reproduction

These commands recheck saved data only and require fresh output directories:

```sh
.venv/codex-native/bin/python results/codex/036-independent-review/analyze.py results/codex/036-independent-review/root_repeat
.venv/codex-native/bin/python results/codex/036-independent-review/summarize_stages.py results/codex/036-independent-review/root_repeat results/codex/036-independent-review/root_repeat_stages
```

If either output directory already exists, use a new name. Do not rerun the
prelaunch-only preflight or any embedding worker to reproduce this analysis.
The result auditor SHA256 is
`7d0f8f369e90d0e89ead6595499c9b97d27c1b22f4fe9408d590f6e63b1e1b47`;
its original summary records this identity and the checked raw-file digest.
The additive stage summary and table were generated by
[`summarize_stages.py`](../../../results/codex/036-independent-review/summarize_stages.py),
which records its own source hash and the input-pair artifact hash.
