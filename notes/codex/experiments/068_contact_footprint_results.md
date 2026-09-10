# A068 complete result: useful construction evidence, fixed policy rejected

2026-09-10 UTC. **Reject the frozen full-footprint policy; retain A061.** All
48 calls were timely, independently valid successes, but full footprint loses
to A061 on BA100 and the BA96 relabel and to booking on seven inputs. The two
other numerical conditions pass: substantial positive MM-gap closure in WS
and SBM, and booking-ablation gains on four independent structures. Those
gains do not cancel the regressions. This is single-seed development evidence,
not promotion or an all-class result.

## Complete outcomes and every regression

F = contact footprint; B = identical active physical conversion with virtual
inactive-arm booking. Cells are **Q / ACL**; all four methods succeed on every
row. Times are solver seconds, F / MM. Every method's solver wall, CPU, process
time and within-chain variance are preserved in the
[48-call CSV](../../../results/codex/a068-footprint/mechanism001/output/all_calls.csv).

| Input | F Q / ACL | B Q / ACL | A061 Q / ACL | MM Q / ACL | F / MM seconds |
|---|---:|---:|---:|---:|---:|
| g0013 grid128 | 157 / 1.227 | 156 / 1.219 | 168 / 1.312 | 133 / 1.039 | 7.040 / 0.518 |
| g0014 honeycomb190 | 237 / 1.247 | 229 / 1.205 | 240 / 1.263 | 202 / 1.063 | 12.812 / 0.450 |
| g0102 BA100 | 306 / 3.060 | 273 / 2.730 | 282 / 2.820 | 199 / 1.990 | 12.831 / 6.655 |
| g0302 BA96 | 268 / 2.792 | 280 / 2.917 | 290 / 3.021 | 318 / 3.312 | 10.038 / 2.346 |
| g0309 BA96 relabel | 283 / 2.948 | 274 / 2.854 | 267 / 2.781 | 274 / 2.854 | 8.111 / 4.114 |
| g0303 regular96 | 354 / 3.688 | 346 / 3.604 | 367 / 3.823 | 398 / 4.146 | 12.035 / 2.837 |
| g0304 WS96 | 203 / 2.115 | 198 / 2.062 | 224 / 2.333 | 192 / 2.000 | 9.459 / 0.683 |
| g0307 singleton control96 | 216 / 2.250 | 255 / 2.656 | 266 / 2.771 | 189 / 1.969 | 10.511 / 1.643 |
| g0308 branch control96 | 176 / 1.833 | 177 / 1.844 | 177 / 1.844 | 171 / 1.781 | 5.882 / 1.211 |
| g0007 ER160 | 1286 / 8.037 | 1261 / 7.881 | 1289 / 8.056 | 1684 / 10.525 | 15.746 / 29.248 |
| g0011 SBM160 | 850 / 5.312 | 867 / 5.419 | 894 / 5.588 | 833 / 5.206 | 13.896 / 13.305 |
| g0015 wheel127 | 206 / 1.622 | 206 / 1.622 | 206 / 1.622 | 144 / 1.134 | 4.420 / 5.692 |

F improves nine A061 encodings, loses two and ties wheel. Its A061 losses are
BA100 **+24 Q** and BA96 relabel **+16 Q**. Its booking losses are grid **+1**,
honeycomb **+8**, BA100 **+33**, BA96 relabel **+9**, regular **+8**, WS **+5**
and ER160 **+25**. Booking itself loses **+7 Q** to A061 on the BA relabel;
it is not a regression-free substitute. No outputs are combined.

On eleven canonical structures, F and A061 each beat MM on BA96, regular96
and ER160 and lose on the other eight. There is no new canonical MM-win
structure. F additionally loses the MM win that A061 obtains on the relabel
in this cohort. That relabel remains a veto row, not a second structure vote.
Canonical BA mean ACL is F **2.9258**, B **2.8233**, A061 **2.9204**, MM
**2.6513**; the BA96 gain must not hide BA100's regression. Other ordinary
families each have one input here, so the table gives their class-level mean
with that limited support. Controls stay separate.

F closes **65.6%** of A061's positive WS-to-MM Q gap and **72.1%** of its SBM
gap, satisfying the two-ordinary-family condition. Grid closes 31.4%, honeycomb
7.9%, and BA100's gap grows 28.9%. The singleton control closes 64.9% but does
not vote as an ordinary family. F beats B on BA96 (−12 Q), SBM160 (−17),
singleton control (−39) and branch control (−1): two ordinary plus two control
structures support that distinct mechanism condition.

Within-chain variance also has regressions. F versus A061 rises on BA100
(4.2364 vs 3.2876), BA96 (3.1024 vs 2.9996), its relabel (3.0702 vs 2.5876)
and ER160 (3.8111 vs 2.8656); it falls on the other changing rows and ties
wheel. F versus B increases variance on seven rows, decreases it on regular,
SBM and both controls, and ties wheel. Across-seed ACL variance is unmeasured.

## Mechanism and allocation interpretation

All eleven entered F conversions report zero missing arms, missing contacts,
corner deficits or added completion sites. Wheel has an edgeless reduced core
and bypasses native entirely. Thus these observed losses are not conversion
failures. The implementation realizes its smaller physical representation,
but that alone does not guarantee better complete geometry or lifting.

The booking ablation rejects a universal benefit from removing inactive
reservations under this fixed search. It also shows a substantive positive
mechanism on several inputs. A plausible explanation is that finite
interleaving/repacking trajectories and their surrogate score use the added
freedom unevenly; virtual reservations can incidentally constrain a trajectory
favorably. This is an explanation to test, not an established regularization
principle. The current experiment does not distinguish move reach from
finite search effort or score mismatch.

Both variants improve A061 on eight shared canonical structures. This is
complete cross-instance support for their shared active-arm/corner/pricing
change, despite opposite booking policies; it is not seed replication and
does not isolate those complementary changes individually. Benefit cannot be
attributed solely to freeing inactive packing capacity.

BA100 is a concrete warning about local compactness: F's raw/pruned filled-core
Q is **146/144**, below B's **151/151**, yet its complete handoff is **306**
versus **273**. Core size59 and lifting requirements are the same. The smaller
early core does not certify cheaper subsequent refinement/lifting. Without
another saved-state analysis, this does not isolate which downstream stage
created the difference. The unreduced BA96 relabel already has worse raw F
Q (**298 vs 289**), so its regression cannot be explained by lifting alone.

Every entered layout—11 per native arm—reaches **1000 asks**. F geometry takes
4.101–13.344s; neither new arm reaches its geometry deadline or overruns the
10s downstream reserve. Simultaneous ask/deadline flags are false on all22
new-arm layouts. F last improves its geometric bookmark at asks999 on the BA
relabel,988 on ER160,968 on the singleton control and948 on SBM160. Therefore
1000 is still not a demonstrated saturation point. These are surrogate
improvements, not evidence of later physical-Q gains. All old A061 simultaneous
deadline flags remain unknown because that field was not saved.

Other artificial limits remain visible. F contact refinement stops on a group
limit for six cores and a work limit for five. Its vacancy stage exhausts the
50,000-proposal allowance on BA96, its relabel, regular, WS, ER and SBM in
0.210–0.344s despite a1s local allowance. This screen retains those fixed
limits; their exhaustion does not establish useful work was exhausted. A
representation-only attribution cannot ignore these downstream restrictions.

F totals **122.781s solver wall /122.749s CPU /141.192s process**;
B124.734/124.690/144.595; A061125.461/125.433/147.701;
MM68.703/68.695/74.139. All48 attempts and every timing field are observed.
F's aggregate cost is close to A061, but grid and WS are about14× MM and
honeycomb28×. Dense ER's MM cost cannot conceal those deficits. Conversion,
completion and initial core validation total only0.2255,0.0369 and0.0327s for
F's eleven cores; geometry dominates that new stage. Complete downstream time
after layout totals27.930s, nested within the solver total. A061 lacks the new
fine timing fields. Even wheel's unchanged bypass computation differs in wall
time across calls, so single paired samples do not establish causal speedups.

## Validity times and next decision

F's observed original-source handoffs, as **Q at seconds**, are grid159@6.884,
honeycomb240@12.586, BA100306@12.633, BA96268@9.864, relabel283@7.982,
regular354@11.787, WS203@9.274, singleton216@10.331, branch176@5.777,
ER1286@15.459, SBM850@13.656 and wheel206@4.305. The final path stage changes
only grid to157 by6.955s and honeycomb to237 by12.696s. Individual commit
times are unsaved; all other final Q values are observed at handoff. These are
handoff observations, not internal first-validity discovery or a safe early
cutoff. Native core timestamps/Q remain separately scoped in
[the passive rows](../../../results/codex/a068-footprint/mechanism001/output/rows.json).

Stop extending this fixed footprint policy by adding score or packing repairs.
Preserve the representation as a mechanism with mixed complete evidence. If
root allocates a bounded follow-up, the supported question is whether measured
search allocation changes complete outcomes while retaining BA100/relabel
anchors—not whether another raw-Q decrease is achievable. Late bookmarks and
short active-cap stops justify that question, not a prediction of success or
permission to spend60s on every sparse input. Any allocation change needs its
own frozen complete comparison; none is launched here. A061 remains retained
while root compares the other independent tracks.

Evidence: root's original audit first PASS (259 bindings), followed by this
passive reader's first PASS (44 bound input files,0.184485s process), with no
new minor validations or constructor calls. Common summary SHA256
`2410877e8136edb1f2ac2a833b72b440edab71b7f13dce83c91fdf73e933a5f8`;
[passive summary](../../../results/codex/a068-footprint/mechanism001/output/summary.json)
SHA256 `d634a492741ad3fd9a058d87a018b3b39496cbfdfc3f1dd13f9f11bd2d8edbcd`.
Frozen source `8ca7abb4434a1d7517318e24bf1b01ec75ca34f1eb6e866b436147e1ddd5616a`;
manifest `00ace9baa575b0c57fba2d8b123a9ab9da0d5b43416fe0d4afcd43ea46496a39`.
No untouched confirmation set has been created.
