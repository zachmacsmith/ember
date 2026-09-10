# A067: useful attachment changes, fixed policy rejected

2026-09-10 UTC. **Reject A067's frozen policy; keep A061 retained.** All 60
calls succeed and independently validate. Fresh strict Q gains over both A065
and A066 occur only on ER96 and BA96, below the required three random-source
families. Regular96 regresses by one qubit against **each** control. These two
failed conditions remain decisive despite improvements on all three earlier
regression anchors. Stop further attachment-score and narrow pair tuning; the
[next decision](../tracks/a_067_stopping_decision.md) states a reopening standard.

This is one seed on twelve development encodings/eleven structures, ideal Z12,
hyde06, with separate 60-second calls. The BA relabel is not a second structure.
The frozen [screen](../../../results/codex/a067-transfer/screen.json) and
[analysis plan](../tracks/a_067_screen_analysis.md) precede execution. Root
retrieved the terminal archive once, then ran the original common audit and
approved passive reader once: both first PASS, respectively 1.804 and 2.242
seconds process wall, with 276 and 68 bindings verified by root. This review
only reads their completed outputs; it adds no reader, constructor, validator,
exact solve or intermediate-map replay.

Each cell below is **Q / ACL**; ACL is rounded to four decimals. All five arms
have twelve credited successes and no timeout, invalid output or missing time.
The original [60 rows](../../../results/codex/a067-transfer/audit001/output/rows.json)
retain full precision, all variance values and every call's costs.

| Input | Retained A061 | A065 | A066 | A067 | MM |
|---|---:|---:|---:|---:|---:|
| g0301 ER96 | 398 / 4.1458 | 377 / 3.9271 | 377 / 3.9271 | 372 / 3.8750 | 403 / 4.1979 |
| g0302 BA96 | 290 / 3.0208 | 281 / 2.9271 | 281 / 2.9271 | 280 / 2.9167 | 318 / 3.3125 |
| g0303 regular96 | 367 / 3.8229 | 351 / 3.6563 | 351 / 3.6563 | **352 / 3.6667** | 398 / 4.1458 |
| g0304 WS96 | 224 / 2.3333 | 220 / 2.2917 | 217 / 2.2604 | 217 / 2.2604 | 192 / 2.0000 |
| g0305 SBM96 | 224 / 2.3333 | 217 / 2.2604 | 217 / 2.2604 | 217 / 2.2604 | 225 / 2.3438 |
| g0306 planar96 | 152 / 1.5833 | 152 / 1.5833 | 152 / 1.5833 | 152 / 1.5833 | 158 / 1.6458 |
| g0307 singleton control96 | 266 / 2.7708 | 260 / 2.7083 | 260 / 2.7083 | 260 / 2.7083 | 189 / 1.9688 |
| g0308 branch control96 | 177 / 1.8438 | 176 / 1.8333 | 175 / 1.8229 | 175 / 1.8229 | 171 / 1.7813 |
| g0309 BA96 relabel | 267 / 2.7813 | 264 / 2.7500 | 264 / 2.7500 | 263 / 2.7396 | 274 / 2.8542 |
| g0007 ER160 anchor | 1289 / 8.0563 | 1264 / 7.9000 | 1264 / 7.9000 | 1260 / 7.8750 | 1684 / 10.5250 |
| g0011 SBM160 anchor | 894 / 5.5875 | 836 / 5.2250 | 835 / 5.2188 | 834 / 5.2125 | 833 / 5.2063 |
| g0015 wheel127 anchor | 206 / 1.6220 | 152 / 1.1969 | 153 / 1.2047 | 148 / 1.1654 | 144 / 1.1339 |

A067 has six gains/five ties/one loss versus A066, and eight gains/three
ties/one loss versus A065, counting every encoding. Excluding the relabel,
A067 and retained A061 each have six MM Q wins and five losses, on the same
structures. A067 improves A061 on ten canonical structures and ties planar96,
but creates no additional MM win here. WS and singleton-control excesses stay
25 and 71 qubits versus MM; branch-control excess stays four versus A066.
The full package nevertheless closes substantial retained-A061 gaps: SBM160
goes from 61 excess qubits to one, and wheel from 62 to four. Most of that
progress is already present in A066; A067 adds one and five qubits respectively.
These gains matter, while large ER gains cannot erase the remaining deficits.
Fresh SBM96 and planar96 already favor A061 over MM, so this
screen does not support a universal SBM/planar loss or a class-wide win.

The common audit's five `fresh_q_gain_families` compare with **A061**. They are
not the frozen requirement of three fresh families beating **both A065/A066**;
the passive summary correctly reports only ER and BA and a false criterion.
All older [A066 regressions](066_remaining_transfer_results.md) remain rejected
observations. The unchanged controls' current ER/SBM timed outcomes differ from
the previous cohort; comparisons here use these contemporaneous calls, without
silently replacing historical results or estimating run-to-run variance.

**Trajectories and cost.** The following are A067's observed handoff bounds
and first observation of its eventual final Q, measured from wrapper entry.
Internal first-valid discovery inside A061 is unknown. Full admitted Q/ACL
curves for all three added-stage arms are in the
[admission CSV](../../../results/codex/a067-transfer/mechanism001/output/admissions.csv).
Bounds are displayed to six decimals; final admission times to milliseconds.
The last two columns describe charged A067 cost and completed-tree coverage;
they do not constitute matched-query comparisons.

| Input | Reported valid-base handoff [s] | First final Q [s] | Non-improving reconstruction / stage [s] | Completed trees A066 → A067 |
|---|---:|---:|---:|---:|
| ER96 | [10.016586, 10.016672] | 18.377 | 42.045 / 48.896 | 11,831 → 5,199 |
| BA96 | [8.880776, 8.880840] | 11.704 | 46.792 / 50.052 | 9,769 → 3,658 |
| Regular96 | [9.320420, 9.320476] | 14.625 | 43.967 / 49.620 | 10,043 → 4,602 |
| WS96 | [6.489406, 6.489454] | 9.269 | 49.206 / 52.431 | 14,517 → 7,785 |
| SBM96 | [8.510444, 8.510491] | 9.993 | 47.812 / 50.419 | 13,485 → 6,748 |
| Planar96 | [6.796696, 6.796765] | Base handoff; no admission | 51.015 / 52.119 | 11,836 → 7,552 |
| Singleton control96 | [7.286121, 7.286186] | 9.898 | 48.416 / 51.585 | 9,179 → 7,875 |
| Branch control96 | [5.954265, 5.954319] | 6.837 | 51.583 / 52.999 | 14,539 → 8,864 |
| BA96 relabel | [9.392251, 9.392321] | 13.769 | 45.817 / 49.539 | 11,576 → 4,484 |
| ER160 | [15.298760, 15.298854] | 46.049 | 25.827 / 43.618 | 3,911 → 1,914 |
| SBM160 | [14.563919, 14.563989] | 50.783 | 24.860 / 44.369 | 3,788 → 2,947 |
| Wheel127 | [6.236849, 6.236918] | 14.591 | 47.604 / 52.684 | 8,223 → 1,392 |

All 36 added stages stop at their deadline; none exhausts its current epoch.
All 36 base and final-validation scopes complete, so final quality is credited
while added search remains cost-censored. The large unused root queues do not
prove that their unvisited roots would help. A067 reaches eventual Q by 18.378
seconds on all nine 96-node encodings, yet ER160/SBM160 still improve at
46.049/50.783 seconds. A universal early cutoff is unsupported. Matching base
Q across arms and fresh A061 calls does not establish equal base maps or equal
internal discovery times; substantial base-time variation also affects wrapper
timing. Operator-relative admission clocks remain in the saved rows.

Every A067 input completes fewer trees than A066. Its non-improving work still
dominates the small/local inputs. On ER160 and SBM160, root-search wall falls
from 19.989/22.078 seconds in A066 to 11.421/13.748 in A067, while non-improving
reconstruction rises from 15.675/12.944 to 25.827/24.860. These are different
realized trajectories under the same wall envelope, not an isolated per-query
speed experiment. Whole-operator coverage counters show actual execution of
the new rule: ER96 has 16,687 searches and 16,686 extensions; the singleton
control has 26,152 searches, 26,151 extensions, 109,430 groups gained and 45,795
sites added. Even that larger contact count yields no final gain over A066.
All twelve rows record `bound_closed = extensions` and `searches = extensions + 1`,
with no exhausted-search event. These counters include interrupted and rejected
work and cannot measure
optimal trees, reusable contacts in the final map, or individual path quality.

**The regular96 loss is not just a shared sequence cut one admission short.**
All three base scalar Q values are 367. Their first two scalar admissions agree,
but A067's third changes owner68 with two donors, while both controls change
owner38 with one. Each makes ten admissions. A067 saves 15 ordinary qubits and
ends Q352; controls save 16 and end Q351. A067's final admission occurs at
14.625 seconds, versus 13.468 for A066. This establishes changed realized moves
and greater search cost, not which omitted or rejected tree caused the loss.
There is no pair admission on this input. Strict-Q acceptance is unchanged and
all admitted moves meet it; rejection counts do not establish a neutral barrier.

On WS96, A066/A067 each save one pair qubit plus six ordinary qubits. Their
branch-control split is one plus one; singleton control has no pair commit and
six ordinary qubits in either arm. Wheel changes from A066's ten pair plus 43
ordinary qubits to eleven plus 47. ER160/SBM160 gains are wholly ordinary.
Pair effects are not separable from later ordinary trajectories after an
admission; local savings cannot be added to comparator gains.

**Variability and all-call time.** Across-seed ACL variance is undefined here.
The next table reports within-embedding chain-length variance, a different
metric, and paired same-host solver-wall ratios. No failure cost is excluded.

| Input | Within-chain variance A067 / MM | A067 − A066 variance | A067/MM solver wall |
|---|---:|---:|---:|
| ER96 | 2.08854 / 2.53375 | +0.06261 | 19.797× |
| BA96 | 2.80556 / 3.36068 | −0.03288 | 26.254× |
| Regular96 | 1.22222 / 1.70790 | −0.00336 | 17.473× |
| WS96 | 1.04677 / 0.66667 | 0 | 64.487× |
| SBM96 | 1.40093 / 1.20475 | 0 | 37.946× |
| Planar96 | 0.63889 / 0.68707 | 0 | 105.948× |
| Singleton control96 | 2.22743 / 0.71777 | 0 | 25.501× |
| Branch control96 | 0.87489 / 0.67090 | 0 | 56.372× |
| BA96 relabel | 2.83843 / 2.47873 | +0.10927 | 17.190× |
| ER160 | 3.02188 / 14.06188 | +0.04438 | 2.113× |
| SBM160 | 5.36734 / 4.62621 | +0.18395 | 3.745× |
| Wheel127 | 2.04352 / 1.54901 | +0.76260 | 13.128× |

Compared with A065, A067 also increases WS and branch-control variance by
0.00684 each, while wheel variance decreases by 0.30355; the other signs match
the A066 column. Thus regular96's slightly lower variance does not erase its
Q loss, and several Q gains increase variance. BA relabel sensitivity is not
across-seed variability or another independent graph. Runtime remains far
beyond roughly MM's order on several sparse inputs despite the shared 60-second
exploration allowance; no fixed universal multiplier or speedup is inferred.

| Method, all 12 calls | Solver wall [s] | Solver CPU [s] | Process wall [s] |
|---|---:|---:|---:|
| A061 retained | 109.094 | 109.073 | 129.803 |
| A065 | 708.296 | 708.226 | 731.563 |
| A066 | 708.251 | 708.194 | 730.838 |
| A067 | 708.265 | 708.204 | 730.182 |
| MM | 66.648 | 66.646 | 72.382 |

The [passive rows](../../../results/codex/a067-transfer/mechanism001/output/rows.json)
preserve exclusive phases, nested query/root/pair costs, unknown fields and
every admission. Nested costs are already inside stage/call time; do not sum
them again. No untouched confirmation set has been created; this entire screen
is development evidence. Historical class gaps are preserved in the
[A066 table](../a066_combined_class_gaps.md), not pooled
with this screen as an across-seed estimate.

Evidence SHA256: source snapshot
`d9c86d0f02d3e0a18490acb7590bc900c2b44737a4d1376e0b03c1ff54c43492`;
manifest `cc23d455f3c7c036afcec55a66d9f8869f5b0b67b2982ab7b0050bfcd03f8c88`;
archive digest `f81a1e29642900cf8e6a0f6eac24fc6643b8635de54839c672eb548debf23c28`
(446 files, root retrieval); common summary
`07203a4c87d49761e4b0857d23d3ed1934dd09b6c2ffd935caeda070c10066b0`;
common rows `13f8b0ab8cc6e945f5235a375b076e6e10b6245483956c83c05a4eadbfd3bdf3`;
passive summary `c41c0a1470c69396411ddc0d2b461b8886b926b316869c803657366d727448ee`;
passive rows `245efc9011f3c9d070d195e02e5ca91e9ce884334e286cb4cb9467157de3b146`;
admission CSV `d092937e63885e8d633b4c040a65d3ad9816aaaa08eb0455f99ff33820e48aeb`.
The approved reader/preparation hashes remain in the saved analysis plan and
`mechanism_preparation001.json`. No source or frozen outcome changed here.
