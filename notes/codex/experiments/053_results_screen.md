# 053: one-site transfer during filled-core expansion

**Retain for further evaluation, without a general promotion claim.** The one
saved-result screen passed: all 68 outputs are original-valid, timely SUCCESS,
representing 34 inputs/35 memberships. No failure, timeout, internal error,
dependency violation or lost result occurred. The archive, receipt checks and
original-label validation are preserved unchanged.

Against fresh fixed A050, A053 gives 10 lower-Q results, two higher and 22 ties:
total Q14,866→14,797 (−69), macro ACL3.298135→3.278605. Both regressions remain
explicit: planted `ember_34404` Q156→158 (+2), and wheel `ember_2429` Q183→187
(+4). The largest gain is generalized Petersen `ember_4083` Q211→174 (−37).
Initial core Q is identical in every pair, totaling 13,407 in both arms; the
differences follow expansion. All 28 native core calls per arm succeeded,
with six edgeless base cases.

Same-host, fresh-process solver time totaled 185.646→186.012 s; process time
207.943→208.430 s. Median solver ratio was 0.9994, maximum 1.2377 on the
unchanged-Q star; no pair exceeded 10×. Global scans fell
39,238,515→38,279,479. Core wall totaled 159.736→160.280 s; expansion
20.048→19.653 s. Validation subtotals 10.592→9.636 s overlap those phases
and must not be added again. This one-seed sample does not establish a reliable
runtime difference.

All 1,244 reverse rows were visited and committed. Transfer receipts contain
134 certificates, 134 returns and 134 actual commits across 12 inputs, with
unchanged raw Q; subsequent inherited cleanup removed 12 sites on those
updates. These local counts are not 134 or 146 qubits saved against A050:
the measured whole-pipeline difference is 69. The other transfer receipts
comprise 643 no-donor skips and 467 unsuccessful queries. In total 2,884 donor
sites were inspected, consuming 3,291,331 scans and 1.684 s inside expansion/
global totals. Maximum query work was 19,906/50,000 scans; maximum constructor
transfer work 599,064/1M; maximum pool 25 and inspected prefix 20/64. No transfer
allowance bound this run. A053 invoked no blocked repairs; A050 invoked two,
totaling 228,464 scans and 0.136 s.

Historical 048 cyclic **quality only** gives 10 wins, seven losses, 17 ties:
Q14,858→14,797 (−61), macro ACL3.290160→3.278605. All 34 are comparable
successes. Persistent deficits include cubic Q216→258 (+42), cycle Q126→148
(+22), kagome Q154→173 (+19), planted Q144→158 (+14), named-special Q50→58
(+8), Shastry Q157→163 (+6), and grid Q165→167 (+2). Historical timing is not
pooled. This remains an exposed development set, not a held-out or multi-seed
result.

The screen checks filled journals, current-row fill removal, active partial
requirements, original final validity, and receipt Q/work/cleanup continuity.
Unsaved intermediate donor chains, cross-donor ranking, full candidate pools
and local contact/connectivity certificates are not independently replayed.
No solver or candidate rerun followed the result.

All statuses below are SUCCESS. Q/ACL/time entries are fresh 050 / A053; time
is solver seconds. The last column is saved 048 Q only. The full 68 rows,
process times and 35 memberships remain in `screen001`.

| Input / family | n | Q050 / Q053 | ΔQ | ACL050 / ACL053 | s050 / s053 | Transfers | Q048 |
|---|---:|---:|---:|---:|---:|---:|---:|
| ember_22972 / watts_strogatz | 174 | 1694 / 1694 | +0 | 9.736 / 9.736 | 8.974 / 9.172 | 0 | 1694 |
| ember_2229 / star | 127 | 137 / 137 | +0 | 1.079 / 1.079 | 0.972 / 1.203 | 0 | 137 |
| ember_4755 / hypercube | 128 | 452 / 452 | +0 | 3.531 / 3.531 | 5.602 / 5.565 | 0 | 452 |
| ember_31536 / random_planar | 152 | 260 / 260 | +0 | 1.711 / 1.711 | 6.219 / 6.473 | 0 | 288 |
| ember_5242 / johnson | 120 | 837 / 837 | +0 | 6.975 / 6.975 | 6.847 / 6.836 | 0 | 837 |
| ember_34404 / planted_solution | 133 | 156 / 158 | +2 | 1.173 / 1.188 | 3.128 / 3.378 | 9 | 144 |
| ember_6450 / random_er | 133 | 881 / 881 | +0 | 6.624 / 6.624 | 6.844 / 6.812 | 0 | 881 |
| ember_33587 / weak_strong_cluster | 128 | 426 / 426 | +0 | 3.328 / 3.328 | 6.393 / 6.388 | 0 | 426 |
| ember_10662 / barabasi_albert | 122 | 424 / 424 | +0 | 3.475 / 3.475 | 6.163 / 6.201 | 0 | 424 |
| ember_33402 / bcc_lattice | 91 | 135 / 132 | -3 | 1.484 / 1.451 | 4.071 / 4.056 | 5 | 150 |
| ember_3499 / circulant | 134 | 193 / 193 | +0 | 1.440 / 1.440 | 4.902 / 5.002 | 0 | 193 |
| ember_2030 / path | 141 | 141 / 141 | +0 | 1.000 / 1.000 | 1.154 / 1.250 | 0 | 141 |
| ember_37761 / named_special | 46 | 65 / 58 | -7 | 1.413 / 1.261 | 2.342 / 2.312 | 6 | 50 |
| ember_32122 / kagome | 131 | 179 / 173 | -6 | 1.366 / 1.321 | 4.721 / 4.645 | 6 | 154 |
| ember_1584 / grid | 128 | 169 / 167 | -2 | 1.320 / 1.305 | 4.649 / 4.625 | 7 | 165 |
| ember_3060 / turan | 90 | 460 / 460 | +0 | 5.111 / 5.111 | 5.952 / 5.995 | 0 | 460 |
| ember_31357 / lfr_benchmark | 100 | 178 / 170 | -8 | 1.780 / 1.700 | 4.964 / 4.962 | 7 | 179 |
| ember_1041 / complete | 127 | 1180 / 1180 | +0 | 9.291 / 9.291 | 12.119 / 12.096 | 0 | 1180 |
| ember_1829 / cycle | 126 | 155 / 148 | -7 | 1.230 / 1.175 | 2.319 / 1.946 | 18 | 126 |
| ember_1363 / bipartite | 126 | 566 / 566 | +0 | 4.492 / 4.492 | 6.652 / 6.740 | 0 | 566 |
| ember_4083 / generalized_petersen | 126 | 211 / 174 | -37 | 1.675 / 1.381 | 5.523 / 4.955 | 26 | 199 |
| ember_14334 / regular | 140 | 1301 / 1301 | +0 | 9.293 / 9.293 | 8.062 / 8.034 | 0 | 1301 |
| ember_2429 / wheel | 127 | 183 / 187 | +4 | 1.441 / 1.472 | 3.760 / 4.115 | 19 | 193 |
| ember_5411 / kneser | 126 | 409 / 409 | +0 | 3.246 / 3.246 | 5.778 / 5.799 | 0 | 409 |
| ember_37603 / hardware_native | 128 | 248 / 248 | +0 | 1.938 / 1.938 | 4.850 / 5.037 | 0 | 248 |
| ember_32616 / frustrated_square,king_graph | 121 | 227 / 227 | +0 | 1.876 / 1.876 | 5.252 / 5.267 | 0 | 240 |
| ember_5058 / tree | 121 | 121 / 121 | +0 | 1.000 / 1.000 | 0.966 / 0.985 | 0 | 134 |
| ember_30736 / sbm | 120 | 572 / 572 | +0 | 4.767 / 4.767 | 6.243 / 6.431 | 0 | 608 |
| ember_4905 / binary_tree | 127 | 127 / 127 | +0 | 1.000 / 1.000 | 0.990 / 1.027 | 0 | 136 |
| ember_32367 / honeycomb | 190 | 245 / 243 | -2 | 1.289 / 1.279 | 7.018 / 6.749 | 22 | 260 |
| ember_33018 / shastry_sutherland | 121 | 164 / 163 | -1 | 1.355 / 1.347 | 4.763 / 4.691 | 6 | 157 |
| ember_33219 / cubic_lattice | 125 | 260 / 258 | -2 | 2.080 / 2.064 | 5.076 / 5.045 | 3 | 216 |
| ember_31879 / triangular_lattice | 128 | 275 / 275 | +0 | 2.148 / 2.148 | 5.401 / 5.339 | 0 | 275 |
| ember_37302 / spin_glass | 160 | 1835 / 1835 | +0 | 11.469 / 11.469 | 16.976 / 16.882 | 0 | 1835 |

Evidence: [summary](../../../results/codex/053-results-review/screen001/summary.json), [all rows](../../../results/codex/053-results-review/screen001/rows.json), [receipt totals](../../../results/codex/053-results-review/receipt_totals.json), [manifest](../../../results/codex/053-results-review/manifest.json). Frozen source `a31c828398a6c46d080767684602ebc91777358fb3b0df56b46be0e38e59ee99`; run manifest `a2464802ae68b14d9f6d79ecd31a42225b68d552c5d8e773ad035aedb76d7404`. Root verified terminal controller 197491, lock free, tmux absent and supervisor 0 before fetching 462 files. Archive digest `fc533127acc57d0dba5e804c2646066e2a6b6a0a09e4cbc0f49936c825ecaf23`.

The one completed screen command, exit 0, is recorded for provenance; its output directory is immutable:

```sh
.venv/codex-native/bin/python -I -B results/codex/053-results-review/screen.py --archive results/codex/retrieved/hyde03/053-site-transfer-pipeline --archive-digest fc533127acc57d0dba5e804c2646066e2a6b6a0a09e4cbc0f49936c825ecaf23 --out results/codex/053-results-review/screen001
```
