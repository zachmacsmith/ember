# Experiment 033: independent completed-results review

Do not promote direct singleton relocation on this evidence. All 68 calls
succeeded with independently valid embeddings, but the fixed direct policy has
**7 wins, 22 ties, and 5 losses**, with **one more assigned qubit overall**. The
mean ACL across the 34 source inputs increases from **3.334421 to 3.334938**.
Local solver time is similar and slightly higher in aggregate. No parameter or
family-dependent policy selection follows from these results.

## Integrity, completion, and scope

Root verified completion at 03:50:20 UTC on 2026-09-08: the controller reported
`complete`, its launching process exited zero, and PID 33003 was absent. This
review began its full analysis only after that notification. A subsequent
direct process check found neither controller PID 33003 nor last worker PID 34600.
The controller's saved finish timestamp is `1788839357.0738418`.

The independent analyzer imports no candidate modules and executes no solver.
It rehashed all 46 frozen source files; checked the aggregate source identity,
both frozen corpus-selection records, all 34 sanitized graph records, the target,
and all 68 task identities; and checked final-result/worker-result agreement.
It independently reconstructed target adjacency and checked exact source keys,
nonempty chains, integer target membership, duplicate/disjoint occupancy,
connectivity, every logical edge, qubits, ACL, maximum chain length, and
within-embedding chain-length variance. All checks passed. The 34 source
topologies are distinct; the king/frustrated-square membership shares one row and
is counted once. Family labels below are evaluation metadata, not solver input.

Both arms used the same frozen source and settings except
`polish_singleton_policy='direct'`. The control omits this option and uses its
legacy default. Both used spectral initialization, 1,000 placement evaluations,
four refinement passes, 512 total group visits, sizes 1–4, beam width one,
500,000 total refinement work units, 50,000 per group, and 16 additional boundary
sites. The direct auxiliary share is 25,000 units, not additional work. The
target is ideal Z12, and all trials use solver seed zero and one 60-second
deadline. The converter audited in diagnostic 034 remains unchanged in this
frozen run; the comparison does not claim that converter defect is repaired.

| Identity | Value |
| --- | --- |
| Git revision | `684a95d5f00c4b36ffaab1e23983aca5d58ee0c3` |
| Frozen source | `e0ba48c4636082140e4a8d7040ecb22165712a1ef0672d0dee518948ef40853b` |
| Original target record | `38cde794d3c1461054a45b5a660d157737b019c19cb9a7b38e2027730e3d5938` |
| Independent summary | `79e6aaa66cf3bca99d60555b58923478446442842afa3611d8ff602091b5da1e` |
| Final/worker result hash map | `8f28a7365390996862abbd588689f322380928284283447881919cfa53228e9f` |

Detailed evidence is in
[`results/codex/033-independent-review`](../../../results/codex/033-independent-review):
`checks.json`, `pairs.csv`, `details.json`, and `review_manifest.json`. The manifest
records all analysis hashes. The analyzer later gained only an `--output` option
for fresh-directory rechecks; its original and current hashes are both recorded.

## Final quality and local timing by source

Every row is a pair of timely valid successes. `C→D` means contemporaneous
control to direct singleton policy; negative delta means the direct policy uses
fewer qubits. ACL is assigned qubits divided by the listed source vertex count.
Solver times are seconds on this one local host. Full process times are retained
in the CSV. This is one inherited development input per selected family, not an
estimate of a family's performance distribution.

| Source ID / mapped family | n | Q C→D | ΔQ | ACL C→D | Solver seconds C→D |
| --- | ---: | ---: | ---: | ---: | ---: |
| 33587 / weak_strong_cluster | 128 | 425→425 | +0 | 3.3203→3.3203 | 7.577→7.691 |
| 1041 / complete | 127 | 1180→1180 | +0 | 9.2913→9.2913 | 13.443→13.922 |
| 32367 / honeycomb | 190 | 273→274 | +1 | 1.4368→1.4421 | 6.614→7.436 |
| 1584 / grid | 128 | 173→172 | -1 | 1.3516→1.3438 | 5.264→5.562 |
| 31879 / triangular_lattice | 128 | 287→287 | +0 | 2.2422→2.2422 | 5.957→6.376 |
| 37603 / hardware_native | 128 | 249→248 | -1 | 1.9453→1.9375 | 5.615→5.488 |
| 37302 / spin_glass | 160 | 1836→1836 | +0 | 11.4750→11.4750 | 21.775→20.927 |
| 1829 / cycle | 126 | 126→126 | +0 | 1.0000→1.0000 | 4.390→4.144 |
| 33219 / cubic_lattice | 125 | 224→224 | +0 | 1.7920→1.7920 | 6.005→5.800 |
| 1363 / bipartite | 126 | 566→566 | +0 | 4.4921→4.4921 | 8.192→8.373 |
| 2030 / path | 141 | 141→141 | +0 | 1.0000→1.0000 | 4.511→4.205 |
| 2229 / star | 127 | 137→137 | +0 | 1.0787→1.0787 | 5.869→6.383 |
| 3499 / circulant | 134 | 199→198 | -1 | 1.4851→1.4776 | 5.200→5.415 |
| 5411 / kneser | 126 | 423→423 | +0 | 3.3571→3.3571 | 6.821→7.016 |
| 10662 / barabasi_albert | 122 | 444→443 | -1 | 3.6393→3.6311 | 7.368→7.245 |
| 31357 / lfr_benchmark | 100 | 184→188 | +4 | 1.8400→1.8800 | 5.660→5.560 |
| 33402 / bcc_lattice | 91 | 153→153 | +0 | 1.6813→1.6813 | 5.106→5.232 |
| 14334 / regular | 140 | 1304→1304 | +0 | 9.3143→9.3143 | 9.412→9.716 |
| 30736 / sbm | 120 | 617→617 | +0 | 5.1417→5.1417 | 7.944→7.527 |
| 4083 / generalized_petersen | 126 | 209→209 | +0 | 1.6587→1.6587 | 6.520→6.059 |
| 6450 / random_er | 133 | 893→893 | +0 | 6.7143→6.7143 | 7.985→8.602 |
| 32616 / frustrated_square / king_graph | 121 | 241→245 | +4 | 1.9917→2.0248 | 6.079→6.374 |
| 5058 / tree | 121 | 132→133 | +1 | 1.0909→1.0992 | 5.885→5.180 |
| 32122 / kagome | 131 | 162→161 | -1 | 1.2366→1.2290 | 5.639→5.423 |
| 3060 / turan | 90 | 460→460 | +0 | 5.1111→5.1111 | 7.178→6.790 |
| 37761 / named_special | 46 | 49→49 | +0 | 1.0652→1.0652 | 2.794→2.802 |
| 4905 / binary_tree | 127 | 139→139 | +0 | 1.0945→1.0945 | 5.080→5.005 |
| 2429 / wheel | 127 | 200→201 | +1 | 1.5748→1.5827 | 7.392→6.814 |
| 33018 / shastry_sutherland | 121 | 162→159 | -3 | 1.3388→1.3140 | 5.165→5.780 |
| 22972 / watts_strogatz | 174 | 1712→1712 | +0 | 9.8391→9.8391 | 10.333→11.190 |
| 5242 / johnson | 120 | 846→846 | +0 | 7.0500→7.0500 | 7.930→8.135 |
| 31536 / random_planar | 152 | 306→304 | -2 | 2.0132→2.0000 | 7.887→7.665 |
| 34404 / planted_solution | 133 | 146→146 | +0 | 1.0977→1.0977 | 5.204→5.716 |
| 4755 / hypercube | 128 | 462→462 | +0 | 3.6094→3.6094 | 6.830→6.518 |

Control uses 15,060 qubits in total and direct uses 15,061. The mean ACL above
weights each distinct input equally; summing qubits weights input sizes
differently. Both summaries are unfavorable here. A single solver seed per
input provides no estimate of across-run ACL variance. The independently checked
within-chain variance is a different statistic and must not be relabeled as
solver repeatability.

## Proposal gains, search coverage, and regressions

Direct singleton proposals accept 185 moves: 129 shortenings save 143 qubits,
and 56 moves preserve size. Their total reported redundancy change is +16,
including losses of redundancy on accepted shortenings. Those moves are part of
one evolving embedding; the 143 qubits are not an improvement over the control.
Ordinary reconstruction in the direct arm saves 471 qubits, versus 615 total
saved by control reconstruction. Thus final total savings are 614 versus 615.

Across all calls, accepted moves increase from 1,176 to 1,212 and equal-size
moves from 607 to 646. Total reported redundancy gain increases from 681 to 692,
despite the worse final assigned-qubit total. This directly cautions against
using accepted-move count or final redundancy as a surrogate success metric.

The following table details all inputs whose final qubits change. `Q saved` and
`R gain` give control/direct/singleton-operator values; the singleton contribution
is already included in the direct value. Ordinary visits exclude the newly
scheduled extra visits. Complete corresponding records for all 34 inputs are
in `details.json`.

| Input | Final ΔQ | Q saved C/D/S | R gain C/D/S | Ordinary visits C→D | Displaced | Auxiliary work |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 32367 | +1 | 21/20/8 | 12/15/1 | 512→480 | 32 | 3028 |
| 1584 | -1 | 24/25/6 | 14/13/-2 | 512→480 | 32 | 2507 |
| 37603 | -1 | 30/31/13 | 10/12/4 | 512→480 | 32 | 3620 |
| 3499 | -1 | 12/13/4 | -3/-9/-7 | 512→480 | 32 | 2406 |
| 10662 | -1 | 21/22/4 | 34/34/3 | 292→293 | 0 | 4540 |
| 31357 | +4 | 35/31/6 | 15/23/2 | 512→483 | 29 | 3331 |
| 32616 | +4 | 28/24/1 | 61/69/4 | 512→485 | 27 | 3711 |
| 5058 | +1 | 4/3/1 | -1/-1/0 | 512→496 | 0 | 983 |
| 32122 | -1 | 38/39/16 | 15/14/4 | 512→480 | 32 | 2477 |
| 2429 | +1 | 40/39/27 | 5/9/-1 | 512→480 | 32 | 3418 |
| 33018 | -3 | 25/28/8 | 30/28/2 | 512→480 | 32 | 2220 |
| 31536 | -2 | 23/25/9 | 48/53/6 | 512→480 | 32 | 3744 |

The five regressions have different observed forms:

* **Tree 5058 (+1Q):** neither arm accepts an equal-size move. The direct arm's
  three reported accepted-move records match the control's first three records.
  The control then saves one more qubit with group `[1,6,34,4]`; direct has no
  corresponding fourth accepted move. Both exhaust the shared 512-group limit.
  Direct executes 496 ordinary visits plus 16 extra visits. Its displaced-group
  counter is zero because that counter measures only a remaining generated
  suffix, not counterfactual coverage on later passes.
* **Honeycomb 32367 (+1Q):** after five matching reported moves, control shortens
  vertex 17 by two qubits while direct next moves singleton 1 at unchanged size
  and gains one redundant contact. Total shortening is 21 versus 20, while
  redundancy gain is 12 versus 15. Direct visits 480 ordinary groups plus 32
  extra groups and records 32 displaced generated groups.
* **LFR 31357 (+4Q):** after 20 matching reported moves, the next accepted move is
  an equal-size move on different selected chains. The direct trajectory ends
  with greater redundancy gain (23 versus 15) and less shortening (31 versus 35),
  with 29 extra visits and 29 displaced generated groups.
* **King/frustrated-square 32616 (+4Q):** after nine matching reported moves,
  different singleton chains receive the next equal-size moves. Direct gains
  eight more redundant contacts but saves four fewer qubits, with 27 extra
  visits and 27 displaced generated groups.
* **Wheel 2429 (+1Q):** after 38 matching reported moves, control next shortens a
  four-chain group; direct next takes an equal-size singleton move. Direct saves
  39 qubits versus 40 and gains nine redundant contacts versus five. It records 32
  extra visits and 32 displaced generated groups.

These descriptions compare recorded move identities and Q/R deltas, not the
unrecorded intermediate physical chain sets. Matching reported prefixes do not
prove identical intermediate embeddings. The data support missing accepted
shortening in the tree case and divergent equal-size trajectories in the other
four; they do not isolate a causal contribution from each displacement or move.
There is no justification for tuning the policy by these five inputs.

## Work, cache, and acceptance checks

Ordinary visits total 14,488 for control and 14,089 for direct. Direct adds 520
actual extra visits, for 14,609 total visits, and records 450 displaced generated
groups. The difference of 399 ordinary visits is not supposed to equal 450:
the latter is a within-pass suffix count, and the evolving states and later
group lists differ. Extra slots total 530; ten slots find no actual extra visit.

Total charged refinement work decreases from 10,624,904 to 10,382,169. Direct
auxiliary work is 92,140: setup 19,978, refresh 14,351, queue screening 612, and
proposal scans 57,199. It is included in the original work total. Every row
respects 500,000 total work and 512 group visits. The maximum recorded active-visit
work is 11,355, below 50,000, and the largest auxiliary use is 7,102, below 25,000.
Every row has at most 32 extra slots and 32 actual extra visits.

There are 2,431 completed direct scans, zero truncated scans, zero proven-bound
stops, and 881 degree-ineligible skips. No row exhausts the auxiliary cap. Cache
setup completes once on every input. There are 1,200 completed refreshes and
one disable event: `refresh_work_limit` on random-ER 6450, when shared global work
reaches 500,000. Its final embedding remains valid and tied with control at 893Q.
The other 33 rows report no cache disable.

Control stops at the group limit 20 times, work limit 12 times, and no improvement
twice. Direct stops at the group limit 21 times, work limit 11 times, and no
improvement twice. Neither arm times out or reaches the four-pass limit.

All recorded trajectory Q totals exactly telescope from `pruned_qubits` to
independently counted final qubits. Every accepted entry has either positive
qubit saving or zero saving with strictly positive reported R gain. Total Q/R
gains and equal-size counts match their trajectory sums; direct-operator sums
match entries marked `operator='singleton'`. Final R is independently counted
from actual logical-edge couplers. Subtracting the trajectory's cumulative R
gain gives the same inferred starting R in both arms for all 34 inputs.

The logs contain no intermediate chain snapshots, so individual actual R deltas
cannot be independently reconstructed. The paired R identity is a consistency
check, not a substitute for them. Likewise aggregate scan work and the frozen
implementation support the 256-unit scan limit, but no per-visit scan logs exist
to independently measure each such limit. The audit checks all observable
aggregate caps and retains these limits on the claim.

## Timing and historical 026 replay

| Same-run measurement | Control | Direct |
| --- | ---: | ---: |
| Solver wall total, seconds | 240.625 | 242.073 |
| Solver wall mean, seconds | 7.0772 | 7.1198 |
| Process wall total, seconds | 276.497 | 277.725 |
| Refinement wall total, seconds | 40.703 | 40.902 |

The median paired direct/control ratio is 1.00884 for solver wall and 1.00377 for
process wall. All 68 records use host `dabhmbp`, Darwin arm64, the isolated native
interpreter, identical recorded package versions,68 distinct worker PIDs, and 68
distinct per-task JIT cache paths. Compilation is charged to solver time. No MM
package is present, imported, or attempted in these successful workers. The
longest solver call takes 21.775 seconds and no deadline overrun is reported.

This local host was not reserved: one-minute start load ranges from 6.88 to 46.88,
and other local development diagnostics occurred during the run. The small
timing difference is not a precise speed effect. No 033 timing is pooled with
remote 032 MM results or with 026 on hyde03.

Within 033, all 34 pairs have identical non-time layout diagnostics, constructed
qubit counts, and pruned qubit counts. These are saved-stage checks; no pre-prune
embedding replay was executed and the actual pre-prune chains were not saved.

Against the seed-zero spectral control in 026,28 of 34 final physical chain sets
match exactly and 32 of 34 final qubit counts match. Non-time layout diagnostics
match 28 inputs, constructed counts match 30, and pruned counts match 31. The six
different physical embeddings are below; arrows run from historical 026 to 033
control.

| Input | Constructed Q | Pruned Q | Final Q | Accepted placement proposals |
| --- | ---: | ---: | ---: | ---: |
| 1041 / complete | 1184→1184 | 1180→1180 | 1180→1180 | 304→276 |
| 37302 / spin_glass | 1840→1840 | 1836→1837 | 1835→1836 | 384→407 |
| 1363 / bipartite | 777→776 | 567→568 | 566→566 | 94→107 |
| 2229 / star | 276→286 | 137→137 | 137→137 | 91→105 |
| 3060 / turan | 544→547 | 461→461 | 460→460 | 135→134 |
| 5242 / johnson | 873→876 | 864→865 | 849→846 | 264→269 |

All six calls in both runs complete all 1,000 placement evaluations, stop layout
search at its evaluation limit, and return before 60 seconds. Their solver times
are retained separately in `details.json` (historical range 6.03–26.62 seconds,
local range 5.87–21.77 seconds); no timeout or truncated placement budget explains
these six differences.

All six initializer records report residual tolerance reached and an uncertain
cutoff, with equal reported initializer work between runs. Corresponding
eigenvalues differ by at most 6.67e-16 and residual summaries by at most 7.44e-16.
The spectral module is byte-identical and recorded NumPy/SciPy versions match,
but the platforms differ (Linux x86_64 on hyde03 versus Darwin arm64 locally).
Small numerical differences affecting order choices in a tied eigenspace are a
plausible explanation consistent with the initializer's documented limits;
the saved records do not establish that cause or retain the initial order needed
to locate the first divergence.

The whole frozen programs are also not byte-identical:033 includes the recorded
horizontal-preprocessing optimization in `field.py` and optional singleton
integration in native/contact code. Inspection finds the old contact traversal
unchanged for the control; the preprocessing edit avoids constructing unused
horizontal neighbor views. These are additional version differences to retain
in the replay provenance, not grounds for asserting a numerical cause. No
cross-host speed claim or changed-code quality attribution is made from 026.

## Reproduction and decision

The independent analyzer validates immutable inputs and refuses to overwrite its
outputs. To repeat it after completion in a fresh analysis directory:

```sh
.venv/codex-native/bin/python results/codex/033-independent-review/analyze.py \
  --root-completion-verified --output /tmp/ember-033-independent-repeat \
  results/codex/033-singleton-relocation-ablation \
  results/codex/retrieved/hyde03/026-corpus-spectral-initialization
```

Retain the implementation's correctness tests and these lessons, but keep the
globally fixed control policy as the current candidate. The singleton operator
recovers local opportunities without delivering a cumulative gain here. The
next algorithm change should be evaluated as a separately frozen revision;
this screen supplies neither an across-family MM victory nor a reason to select
between these two configurations by input.
