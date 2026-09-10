# A066 transfer: reject the fixed policy, preserve the mechanism evidence

2026-09-10. **The frozen continuation criterion fails.** A066 retains all 17
successes and improves seven inputs over A065, but ER160, SBM160 and wheel each
regress by one qubit. These regressions reject this fixed policy for continuation
under its declared criterion. They do not establish that every coordinated pair
move is harmful. A061 remains the retained full-class algorithm.

The [unchanged screen](066_remaining_transfer_screen.md) completed all 68 cold
calls on hyde06: A066, A065, A061 and MM, seed 0, 60 seconds, ideal Z12.
Each native arm succeeds 17/17; MM succeeds 16/17 and times out on K100.
Original audit first PASS: 2.165 seconds, root verified 296 bindings. Corrected
mechanism analysis first PASS: 2.813 seconds, root verified 71 bindings.
There are no missing call-time fields. No failed record was replaced or rerun.

| Input | A066 Q | A065 Q | Retained A061 Q | MM Q | A066 − A065 |
|---|---:|---:|---:|---:|---:|
| BA80 | 208 | 208 | 216 | 257 | 0 |
| Regular80 | 263 | 263 | 268 | 279 | 0 |
| WS80 | 161 | 161 | 163 | 136 | 0 |
| SBM80 | 139 | 142 | 153 | 131 | −3 |
| ER160 | 1264 | 1263 | 1289 | 1684 | **+1** |
| BA160 | 579 | 579 | 633 | 597 | 0 |
| Regular160 | 823 | 824 | 925 | 1018 | −1 |
| WS160 | 453 | 456 | 476 | 368 | −3 |
| SBM160 | 837 | 836 | 894 | 833 | **+1** |
| Planar160 | 279 | 280 | 284 | 276 | −1 |
| Honeycomb190 | 212 | 215 | 240 | 202 | −3 |
| Wheel127 | 153 | 152 | 206 | 144 | **+1** |
| K100 | 726 | 726 | 726 | timeout | 0 |
| Singleton control160 | 553 | 557 | 566 | 505 | −4 |
| Branch control80 | 157 | 157 | 158 | 150 | 0 |
| Branch control160 | 341 | 342 | 345 | 307 | −1 |
| BA80 relabel | 213 | 213 | 220 | 233 | 0 |

Seven gains span six families; regular, SBM, honeycomb and diagnostic controls
extend beyond the initial grid/WS/planar gain families. Seven ties and all three
losses remain visible. These are 17 previously exposed encodings/16 structures,
not fresh transfer or confirmation. The BA relabel is not another independent
structure. Combined class results and all persistent MM gaps are
[reported separately](../a066_combined_class_gaps.md).

Comparisons remain cohort-specific. On all 15 inputs shared with the previous
A065 remaining screen, MM's Q is unchanged. In particular, SBM160's prior
A065/MM result was 828/833; these new timed calls give 836/833, with the same
A061 Q894. The algorithm source did not change. This is observed finite-wall
outcome variation, not evidence of a new universal SBM failure or a changed MM
comparator. No repeat-run or determinism campaign was conducted. The historical
audited row file is `results/codex/a065-remaining-transfer/audit001/output/rows.json`,
SHA256 `75e842fb49e241b6a31abfb03988b6be24a9f9a700f0c604ece4a5ad3451ebf5`.

**The three regressions have different receipt patterns.**

| Input | Common base Q | A066 pair savings | A066 ordinary savings | A065 ordinary savings | Receipt observation |
|---|---:|---:|---:|---:|---|
| ER160 | 1289 | 0 | 25 | 26 | All 22 A066 scalar admissions match the A065 prefix; A065 adds Q1264→1263 at 58.212 s. A066 has no exact/pair observations. |
| SBM160 | 894 | 0 | 57 | 58 | All 43 A066 scalar admissions match the A065 prefix; A065 adds Q837→836 at 55.160 s. Ten pair attempts, no pair admission. |
| Wheel127 | 206 | 10 | 43 | 54 | Ten scalar admissions match, then a pair versus ordinary move changes the sequence. A066 reaches Q153 at 9.827 s; A065 reaches Q152 at 11.361 s. |

Times are the saved admission clocks relative to wrapper entry. Scalar prefix
equality includes owner, Q, rank, donor/stem counts and epoch; it does not prove
equal maps, unsaved queries or deterministic counterfactual trajectories.
ER/SBM support a finite-time ordinary-search explanation, without identifying
host variation, per-query overhead or unsaved state differences separately.
Wheel demonstrates that ten local pair savings can coexist with worse complete
Q after a different trajectory. No pruning-only arm ran here, so neither that
loss nor any complete gain is isolated to the pair operator alone.

All 1,622 pair attempts finish: 1,587 exhausted and 35 admitted. Twelve selected
assignments satisfy the recorded neutral-first condition; 23 do not. The latter
is not proof that every assignment for those pairs requires joint release.
Across this panel, 35 pair savings plus 366 ordinary savings replace A065's 388
ordinary savings, giving 13 net qubits saved despite the regressions. For example,
honeycomb makes 13 pair admissions but improves only three final qubits; BA80
admits one pair yet ties A065. Regular160 improves one qubit with zero pair
admissions. Pair counts cannot be credited as complete quality improvements.

Within-chain variance increases against A065 on ER160, regular160, WS160,
planar160 and both 160-node controls. SBM160 and wheel have lower within-chain
variance despite worse Q. All exact variances, including unchanged rows and the
initial WS100/planar100 increases, remain in the
[113-call scalar CSV](../../../results/codex/a066-remaining-transfer/report001/all_calls.csv).
Across-seed ACL variance is unmeasured; chain-length dispersion is a different
quantity.

| Arm | All-call solver wall (s) | Solver CPU (s) | Process wall (s) |
|---|---:|---:|---:|
| A066 | 1003.627 | 1003.470 | 1039.843 |
| A065 | 1003.663 | 1003.512 | 1037.438 |
| A061 | 186.845 | 186.806 | 219.361 |
| MM, including timeout | 147.661 | 147.642 | 156.901 |

All 34 added native stages stop at their deadlines and remain cost-censored.
A066 spends 639.556 of 822.080 stage seconds in non-improving reconstruction
(77.80%). Its 1.037-second nested pair/obstruction/admission cost is already
included; all 1,550 underlying intervals have known time. This does not imply
that removing that cost would preserve the accepted sequence. Root ranking is
also substantial on larger ER/regular/SBM inputs. A066 regular160 still admits
its eventual final Q at 57.578 seconds, directly limiting the initial panel's
retrospective early-gain interpretation. No shorter-runtime policy was tested.

**Next decision:** stop this fixed A066 continuation and further narrow pair
extensions. Retain the low-cost valid operator evidence, the wheel interaction
and the late ordinary gains. The
[revised A067 design](../tracks/a_067_contact_coverage_decision.md) proposes one
attachment change with a tiny falsifier followed promptly by a complete screen
including fresh development inputs, all three regression anchors, and both
A065/A066 controls. No A067 implementation or execution is authorized here.

Evidence: `results/codex/a066-remaining-transfer/`. Screen SHA256
`62ad3fee5e9c842e3cd079184b2c22bbbd73d436a9d3d2e8e842d06ce879b9eb`;
manifest `32729336990fc0633b7e43593cf11dc84746a128481bea151c3dd47d94b5ce2d`;
unchanged source snapshot
`5fca57bae67709454f2140f85c7a60106d6c60b372485a522fb6c91c71838dbe`.
Original audit summary SHA256
`14df8dd2ba2a70aa6e80567026ade4a2dd914bf0debde07b80a73142954b1c7f`;
mechanism summary
`0436e697d3c0f5552a8f1cf93f8303f94b9fb7236a192cb8c4d0a2af3d714346`.
Root-reviewed passive report first PASS, 0.425899 seconds process/0.297511 seconds
projection; source `cd33b4a9a7c19221b9bb9b2b11c42031384bcd52ec75bb0c509caa04ce6c12c9`,
summary `6fe49155a7451bf4790f229cb52674deb166778fa0d69e8ec89fcfaf65da095e`,
CSV `ca1830d424f5814e2a3cf2ca5debe63849ae9ed90e3a06ba3bb599ec57ab42ff`.
The 13-file before-execution binding is
`3214db657179930a1b8c4baaf216361f18f0c9e3e6b57da34e4d5b6bc726c6b7`.
No candidate, new validator, MM map or intermediate-map replay was used.
