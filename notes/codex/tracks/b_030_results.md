# B030 complete screen: both policies rejected

2026-09-10. **B030 and its connected ablation each failed all twelve calls;
retained A061 and MM succeeded on all twelve.** Neither B030 arm recorded a
first-valid incumbent or any incumbent ACL trajectory. Their failed partial Q
values are not ACL observations. The predeclared continuation criterion fails.

This was the frozen 48-call, two-seed Transfer004 screen on ideal Z12, with all
four methods paired on hyde02. Five structures plus a BA relabel were tested;
the branch-control witness remained hidden. Root completed the terminal checks
and retrieved 380 files once, digest
`e9675eaea1d231f514543b6b2aeda8ffa1c9bde7049bb1d89105e2b5ea4f2985`.
The original-graph audit and approved passive reader passed on their first
executions, with 240 and 54 bindings verified by root. All 48 solver wall/CPU
and process wall fields are observed. There are no known fatal native errors.
The B failures are recorded search failures, not missing outputs or late-valid
embeddings. No constructor, validator or original reader was rerun here.

Both B arms are FAILURE/FAILURE on every table row. The remaining comparison
tracks the retained algorithm's actual deficits, without pooling dense gains
over sparse losses. Q values and differences are seed 0 / seed 1.

| Encoding | A061 Q | MM Q | A061 − MM | Mean ACL A061 / MM | Mean solver s A061 / MM |
|---|---:|---:|---:|---:|---:|
| Grid128 g0013 | 168 / 162 | 133 / 133 | +35 / +29 | 1.28906 / 1.03906 | 35.685 / 1.222 |
| ER96 g0301 | 398 / 363 | 403 / 435 | −5 / −72 | 3.96354 / 4.36458 | 37.056 / 11.634 |
| BA96 g0302 | 290 / 288 | 318 / 271 | −28 / +17 | 3.01042 / 3.06771 | 27.445 / 14.595 |
| SBM96 g0305 | 224 / 238 | 225 / 217 | −1 / +21 | 2.40625 / 2.30208 | 29.825 / 4.681 |
| Branch control96 g0308 | 179 / 191 | 171 / 176 | +8 / +15 | 1.92708 / 1.80729 | 31.293 / 2.639 |
| BA relabel g0309 | 267 / 296 | 274 / 287 | −7 / +9 | 2.93229 / 2.92188 | 33.301 / 21.034 |

Sample variance of ACL across the two seeds, A061 / MM: grid
0.001099 / 0; ER 0.066461 / 0.055556; BA 0.000217 / 0.119846;
SBM 0.010634 / 0.003472; branch control 0.007813 / 0.001356;
BA relabel 0.045627 / 0.009169. These fragile two-seed statistics are distinct
from within-chain variance, which remains in all audited rows. Both B arms
have undefined mean ACL and variance. Relabeling supplies encoding evidence,
not another independent structure. These are development-instance results,
not class-population estimates or confirmation evidence.

All-attempt solver wall / CPU / process wall totals, seconds:

| Method | Success | Solver wall | Solver CPU | Process wall |
|---|---:|---:|---:|---:|
| B030 | 0/12 | 708.140 | 707.512 | 736.628 |
| Connected ablation | 0/12 | 708.115 | 707.617 | 734.160 |
| A061 | 12/12 | 389.210 | 388.617 | 449.915 |
| MM | 12/12 | 111.609 | 111.442 | 131.613 |

Each B call used approximately 59.0 solver seconds and reached its search
deadline, preserving the one-second finalization reserve. No counter limit
stopped the run. There is no new runtime gate or failed-call speedup claim.
Comparisons remain within hyde02; C018's different-host times are not pooled.

The full arm made 31,037 recorded slots and 96 completed sweeps in total
(5–13 per call); the ablation made 40,793 slots and 129 sweeps (6–18).
Every started slot has its scalar receipt. No recorded working state in either
arm reached M=0, including fragmented states. Full-arm minimum observed M ranges
from 67 to 262; its final M ranges from 68 to 262. The complete-call terminal
defects below preserve both seeds. Q/M/P denotes occupied sites, missing source
edges and geometric component debt, **not a valid embedding**.

| Encoding | B030 final Q/M/P, seed 0 / 1 | Ablation final Q/M, seed 0 / 1 |
|---|---|---|
| Grid128 | 280/103/6 / 491/68/23 | 237/112 / 328/92 |
| ER96 | 319/221/16 / 270/262/4 | 205/265 / 185/265 |
| BA96 | 338/164/8 / 454/120/32 | 223/193 / 209/198 |
| SBM96 | 398/100/47 / 512/87/55 | 255/126 / 268/132 |
| Branch control96 | 363/139/19 / 264/156/18 | 189/200 / 194/188 |
| BA relabel | 220/200/25 / 269/179/7 | 201/197 / 224/185 |

The full arm has fewer terminal missing contacts on eleven pairs, but more Q
on all twelve; the relabel seed-0 M also regresses, 200 versus 197. No outcome
supports converting those proxy gains into successful quality claims.

The one root-reviewed scalar reduction passed on its first execution via the
existing local-action recorder, process 1.168619 s. It reads only already approved
analysis outputs and preserves their hashes, all 48 audit rows and all 24 native
call summaries. Evidence: `results/codex/b030-constructor/decision_projection001/`;
output summary SHA
`49743fb029229af9cb66026132350db256d45e3af90769f3d41636d809016bfb`.
The original passive summary remains
`d1ae765c6c18ea7c59c1a77eccc41dd88f041a79624335b9c36b5645aa7aac04`.
Full outputs are under `audit001/output` and `mechanism001/output`; the
[causal decision](b_030_decision.md) interprets the mechanism and cost evidence.
