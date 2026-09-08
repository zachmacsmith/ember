# 040: independent review of raw-wire locality costs

2026-09-08. Saved line-cache updates used **24.8823 s**, versus **34.6920 s**
for full raw conversion of the same 1,088 adopted states: a summed ratio of
**0.71723**. Their recorded geometric transitions took **10.7990 s**, making
the update/transition ratio **2.30412**. Every input exceeded the prespecified
10% cost threshold. The protocol therefore supports **deferring this version
of per-proposal physical pricing**. Cache reuse is useful, but the measured
update is too expensive for that declared use criterion.

The complete independent audit passes with zero errors. All 34 input pairs
have matching, timely geometry observations; all 68 phase workers exit zero
and are reaped without timeouts, alarms or overruns. All **1,122 saved states**
reconstruct exactly from the saved cache fragments, and every raw chain map
independently satisfies the original logical graph on the exact target edges.
Root repeated the saved-data auditor once: all nine JSON and two CSV outputs
are byte-identical, including provenance. No converter or embedding solver was
called during either audit.

## Scope and coverage

The frozen [040 protocol](../physical_locality_diagnostic_review.md) uses the
same 34 development structures and 35 family memberships as 039, with ideal
Zephyr12, seed 0, spectral initialization, and the unchanged production search.
The shared `frustrated_square`/`king_graph` topology is one computational input
and one contributor to aggregate costs. Both family memberships remain in the
tables. Original Sudoku is missing; the separate smaller Sudoku supplement is
not part of this experiment. This is neither a clean holdout nor a replicated
estimate of a family population.

Each input has one reference geometry call followed by one capture call in the
same fresh worker. Each call has a common 60-second allowance; both share one
absolute 150-second process allowance. Offline replay then runs in a separate
process with its own absolute 60-second allowance. The latter compares full
raw conversion and cached conversion of the saved states. Initial replay is
full-first; subsequent replay order alternates by state index.

All inputs reach the **33-copy limit: initial state plus 32 adoptions**. The
search continues after copying stops. On 33 inputs, both calls reach 1,000
asks. `ember_37761` (`named_special`) instead reaches a natural fixpoint after
779 asks and 70 adoptions. Across inputs, the complete capture searches make
8,096 adoptions, ranging from 43 to 434 per input; only their first 1,088
adoptions are copied. The final selected/projection state is a separate search
return, not an additional adopted-state sample. No later-state cost is inferred
by multiplying these prefix measurements.

An initial progress message incorrectly said every search reached 1,000 asks;
the recorded stop counters prompted an immediate correction. All quantitative
cost and validity findings were unchanged.

## Cost result and variability

All times below are sums over the 34 distinct inputs. Ratios divide the summed
times unless explicitly described as per-input statistics.

| Quantity | Recorded value |
| --- | ---: |
| Adopted updates | 1,088 |
| Full raw conversion of updates | 34.691982 s |
| Cached update, including signatures/merge/commit | 24.882259 s |
| Recorded corresponding geometric transitions | 10.799030 s |
| Update/full | 0.717234 |
| Update/transition | 2.304120 |
| Initial full conversion | 1.133186 s |
| Initial cache construction | 1.183840 s |
| Initial cache/full | 1.044700 |
| Full conversion, initial included | 35.825168 s |
| Incremental work, initial included | 26.066098 s |
| Initial-included incremental/full | 0.727592 |

The two predeclared cost rules have different outcomes. The aggregate update
cost remains below full conversion, so the rule rejecting a speed benefit
relative to full conversion does not fire. The rule deferring per-proposal
pricing above 10% of geometric transition cost fires on **all 34 inputs**.
No input has an undefined transition denominator in this run.

The per-input update/full ratio has median **0.77164** and range
**0.18984–1.06954**. Updates are faster on 29 inputs and slower on five:
`hardware_native` (1.00500), `kneser` (1.01400), `bcc_lattice` (1.04515),
`kagome` (1.06954), and `hypercube` (1.00767). These small slowdowns remain
visible. Per-input update/transition has median **3.04921** and range
**0.61085–6.55609**; even the smallest ratio exceeds the 0.10 criterion.
These are descriptive observations from one execution, not confidence
intervals or seed-variance estimates.

## What the cache reused

Across adopted updates, 18,069 of 28,461 old/new line-union incidences are dirty:
**63.49%**. Of 28,243 current line incidences, 17,851 are reconverted
(**63.21%**) and 10,392 are reused. The dirty set also includes 218 removed
lines. Removed lines incur no line-converter call but still require cache
maintenance. This accounting includes them explicitly.

Using each full replay's saved line timers, dirty current lines account for
22.44545 s of 33.68376 s of line-conversion time: **66.64%**. Thus counting
lines alone modestly understates the conversion work affected in this prefix.
Actual dirty-line conversion in the incremental replays takes 21.29216 s;
separate evaluations need not have identical wall times. Neither value is
substituted for the measured full update subtotal.

The accepted proposals can have broad consequences: changed positions have
median 18 and maximum 163 vertices per update; changed carried y-ranks have
median 3 and maximum 165; changed ordered chains have median 63 and maximum
186. These measurements explain why a small selected vertex group does not
establish a small physical update. They motivate studying a cheaper physical
estimate before implementing frequent exact conversion. They do not authorize
family-specific solver dispatch or establish a useful replacement objective.

## All inputs

`Q` is the independently counted number of qubits in the raw chain map.
Every chain map in this table, and every intervening saved state, is valid.
The two Q columns refer specifically to initial state and adoption 32; they
are not the final embedding produced by the complete search/repair/polish
pipeline. Lower/higher Q between those two states occurs on 19/13 structures,
with two ties. No best intermediate state is selected as an algorithm result.
“Dirty lines” divides dirty incidences by the old/new union across 32 updates.
Both timing ratios also use sums across those same 32 updates.

| Input / family | n | m | Initial → adoption 32 Q | Dirty lines | Update/full | Update/transition |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 10662 / barabasi_albert | 122 | 472 | 670 → 618 | 67.0% | 0.760 | 3.542 |
| 33402 / bcc_lattice | 91 | 216 | 257 → 263 | 97.9% | 1.045 | 4.328 |
| 4905 / binary_tree | 127 | 126 | 330 → 288 | 65.2% | 0.744 | 3.046 |
| 1363 / bipartite | 126 | 3969 | 1556 → 1337 | 63.8% | 0.781 | 2.213 |
| 3499 / circulant | 134 | 402 | 269 → 271 | 38.6% | 0.442 | 1.835 |
| 1041 / complete | 127 | 8001 | 1613 → 1427 | 47.8% | 0.609 | 0.925 |
| 33219 / cubic_lattice | 125 | 300 | 355 → 372 | 86.3% | 0.940 | 4.313 |
| 1829 / cycle | 126 | 126 | 252 → 252 | 48.6% | 0.560 | 1.842 |
| 32616 / frustrated_square, king_graph | 121 | 420 | 289 → 313 | 74.0% | 0.855 | 3.053 |
| 4083 / generalized_petersen | 126 | 189 | 323 → 363 | 75.0% | 0.834 | 3.705 |
| 1584 / grid | 128 | 232 | 290 → 315 | 78.8% | 0.941 | 6.556 |
| 37603 / hardware_native | 128 | 352 | 364 → 395 | 93.2% | 1.005 | 3.977 |
| 32367 / honeycomb | 190 | 264 | 428 → 464 | 75.1% | 0.601 | 6.512 |
| 4755 / hypercube | 128 | 448 | 736 → 675 | 93.7% | 1.008 | 5.089 |
| 5242 / johnson | 120 | 1680 | 1174 → 985 | 65.9% | 0.762 | 2.261 |
| 32122 / kagome | 131 | 236 | 265 → 281 | 82.6% | 1.070 | 3.578 |
| 5411 / kneser | 126 | 315 | 699 → 688 | 94.6% | 1.014 | 2.909 |
| 31357 / lfr_benchmark | 100 | 204 | 320 → 308 | 60.6% | 0.663 | 3.115 |
| 37761 / named_special | 46 | 69 | 97 → 98 | 38.6% | 0.501 | 1.591 |
| 2030 / path | 141 | 140 | 282 → 282 | 8.8% | 0.190 | 0.635 |
| 34404 / planted_solution | 133 | 175 | 274 → 277 | 39.0% | 0.510 | 1.650 |
| 6450 / random_er | 133 | 870 | 1172 → 1067 | 63.8% | 0.726 | 3.088 |
| 31536 / random_planar | 152 | 450 | 408 → 413 | 78.8% | 0.882 | 3.511 |
| 14334 / regular | 140 | 2800 | 1788 → 1504 | 75.3% | 0.870 | 1.929 |
| 30736 / sbm | 120 | 625 | 868 → 793 | 71.2% | 0.812 | 3.222 |
| 33018 / shastry_sutherland | 121 | 270 | 252 → 275 | 75.0% | 0.853 | 2.997 |
| 37302 / spin_glass | 160 | 12720 | 2515 → 2273 | 44.7% | 0.611 | 0.611 |
| 2229 / star | 127 | 126 | 335 → 290 | 53.5% | 0.654 | 4.288 |
| 5058 / tree | 121 | 120 | 326 → 278 | 73.9% | 0.834 | 3.569 |
| 31879 / triangular_lattice | 128 | 384 | 404 → 386 | 13.6% | 0.212 | 0.933 |
| 3060 / turan | 90 | 2700 | 808 → 603 | 69.4% | 0.791 | 1.672 |
| 22972 / watts_strogatz | 174 | 1740 | 2350 → 2048 | 86.1% | 0.937 | 3.082 |
| 33587 / weak_strong_cluster | 128 | 1988 | 526 → 455 | 23.5% | 0.327 | 0.827 |
| 2429 / wheel | 127 | 252 | 358 → 340 | 27.1% | 0.282 | 1.511 |

All 35 memberships, including the shared topology's two labels, are also
available separately in `analysis001/memberships.json` and `.csv`.

## Validity, replay and failed-work accounting

The audit verifies all 153 prepared file hashes, all 48 production source
hashes, the 10 diagnostic files, the execution manifest and transport map.
It reconstructs each canonical graph from the preserved original labels and
edges; graph attributes cannot replace the source or target structure.
The exact 4,800-qubit/45,864-coupler target has maximum degree 20. Its stored
coordinates independently bind all 400 physical lanes, positions and stride.

For each captured state, the auditor reconstructs carried contacts, bar
intervals, snapped arms and per-line signatures from saved positions/orders
and original topology. Starting from the previous committed cache, it applies
exactly the recorded dirty/new/removed line entries, then joins fragments in
orientation `(1,0)`, ascending line, and saved within-fragment order. Every
nonempty fragment lies on one lane in ascending contiguous stride-2 order.
The reconstructed ordered chains, claimed-qubit set and both counters exactly
match the saved full output. Reused lines receive the same per-line counter
checks as changed lines.

The independent physical oracle checks exact source keys, nonempty chains,
target membership, disjoint ownership, connectivity and every original source
edge. All 1,122 states pass, with maximum raw chain length 21. Both recorded
converter counters total zero. The frozen `convert_miss` counter can describe
fallback seating, and is not generally a count of absent chains or missing
logical edges; its meaning is not inferred from its name. The second counter
is always zero in this frozen converter and does not count parity changes.

All 34 reference/capture pairs match initial orders, complete returned geometry
and books/orders/trace, static wires, source adjacency, scheduler RNG, and
proposal/unit stream digests. Caller-input fingerprints are reconstructed;
the recorded before/after native-argument fingerprints agree. No forbidden
physical-stage call or prohibited-package import attempt is recorded. The
native environment's pinned package identities and absence of MM/busclique
match the execution manifest and the 23 successful remote synthetic checks.

Every geometry publication receipt and offline observation hash reconciles.
Every saved phase outcome agrees with controller state and its absolute
deadline, alarm metadata, exit status and measured elapsed time. Serial phase
intervals do not overlap. There are no actual skipped, missing, failed,
interrupted or late records to omit or impute in this run.

Before reading results, independent synthetic review found three weaknesses in
the first auditor helper: grand totals could hide incorrect per-line counters;
failed rows accepted negative costs and omitted completed nested cache work;
and interrupted line records could violate the required traversal prefix.
The failed rejection tests are retained. The corrected helper preserves known
cache/full/partial work without committing it or inventing missing durations,
checks line traversal prefixes and validates the frozen counter/lane rules.
Overlapping mode and line times are explicitly distinguished. Its final
independent 11-check suite and the author's eight reviewer checks pass.

## Timing limits and diagnostic overhead

The common geometry clocks total **950.9678 s** over 68 calls; the maximum is
**59.1331 s**. Whole geometry phase time totals **1,063.3244 s**, with maximum
**116.2506 s**, within its 150-second allowance. Offline phase time totals
**177.4371 s**, with maximum **25.4194 s**, within its 60-second allowance.
These process clocks include work beyond the update subtotals.

Across all offline states, recorded diagnostic book verification takes
10.7699 s, equality checks 4.0254 s, and original-graph physical validation
17.5904 s. Offline setup takes 47.5334 s; record encoding and JSON publication
take 4.6561 s and 10.0052 s. Signature construction takes 3.3092 s and is already
included in incremental work; it must not be added to that subtotal again.
The report exposes these components instead of treating the full offline
process as a deployable cache update.

Captured transition time begins at the align wrapper and ends before the
snapshot copy. Its denominator includes **1.6130 s** of recorded proposal
encoding/hash work across these adoptions. No overhead is subtracted to extend
a deadline or estimate an uninstrumented speedup. Across complete reference
and capture calls, stream encoding/hash timers total 87.8710 s; capture copies
take 2.0147 s; post-return payload encoding takes 11.1111 s. These counters have
different scopes and overlap larger clocks. The stream timer does not measure
every counter update, timer call or append in the wrappers.

The reference is instrumented. The second geometry call is a same-process
second invocation, and offline's initial full conversion precedes cache
construction. No universal cold/warm-JIT or complete-pipeline speed claim is
made. Timings come from this same-host diagnostic execution with the frozen
thread settings, not exclusive-core measurements or historical/MM comparisons.

Full unit/proposal values are encoded into length-framed hashes during the
search, but only their digests/counts are saved. Later auditors can compare
those recorded digests under the reviewed wrappers; they cannot independently
reconstruct each stream element. Likewise, this saved-output audit verifies
fragment/full-output agreement and physical legality without re-executing the
converter's greedy/DP seating choices or proving their optimality. Unsaved
states, work and internal memory histories remain unknown. The diagnostic
does not demonstrate final ACL superiority, a family mean, or generalization.

## Frozen evidence and repeatability

Root launched exactly once on hyde03 at **07:37:00 UTC**, controller PID
143531. It completed at Unix time **1788854277.6030006**
(**07:57:57.603 UTC**). Fresh terminal status/inventory showed no matching
processes, a free inherited lock, stopped tmux session and supervisor exit 0.
Root retrieved the run and verified its exact **2,654-file** inventory before
the independent audit opened any observations. `retrieval.json` is the
additional local verification record.

| Identity | SHA256/digest |
| --- | --- |
| Production revision | `c61c474ca7bdd2f6e455cfa67f34af72b8d537cf` |
| Source snapshot | `63a0aed1a880cbf008aa68ae7201aed7a4da635dea9362e5d296b1d13a91a473` |
| Execution manifest | `3f6155277ba866f376427b105371bb7b8a8abc70cefe961542f5a139534e096d` |
| Transport map, 165 files | `9dfba5ece5e210c9ca932c5b4fa277e807ceafb3b67d083239c61590fdbe8865` |
| Retrieved artifact map | `13d0e1782fa2679efe4943d7d8b846816b5a7694a5e868c83041eec4b21ac3e1` |
| Pre-observation auditor freeze | `dac7db6d6f79a66d5b8ffa1ac72e00cbe0382dd0f2c38605ec0d173e598b3ff7` |
| Frozen main auditor | `2f01b38fad9828124629114ad944a1bf4befbe712f32ef770d7f949ba71067ac` |
| Independent locality helper | `6ca02ea8832741676ca9ebbff70e6f8c0ea4b3931720489d4b044ddb2a937a9c` |
| Independent codec | `0952ac48df1164818cbc2f516f4cc5275d49a69d4e3535478915a8be42283ad1` |
| Final audited summary | `8c15c24c7a310b335a1f809f3662905943d48df9654db51210dbb4c8a9b32a58` |

The frozen audit passed on its first actual-run execution; its stderr is empty.
Root read the full main auditor and independent helper review, ran the same
frozen code into a separate destination, and verified all nine JSON and two
CSV outputs byte for byte. Evidence is in
`results/codex/040-root-results-review/root-repeat-comparison.json`.
The ordinary frozen diagnostic report independently agrees with the state
counts and the three principal timing sums.

From the repository root, a future saved-data repeat uses a **new destination**:

```sh
.venv/codex-native/bin/python -B results/codex/040-results-review/pre-execution/analyze.py results/codex/retrieved/hyde03/040-physical-locality results/codex/040-results-review/repeat-new --archive-digest 13d0e1782fa2679efe4943d7d8b846816b5a7694a5e868c83041eec4b21ac3e1
```

The auditor refuses an existing destination and verifies the archive before
analysis. `analysis001/` contains complete per-input, membership, geometry,
phase and state records; `report-tables/` contains the derived descriptive
table. `review_manifest.json` binds this note, the review artifacts and the
external archive/repetition references. No experiment rerun is needed.
