# C018 complete screen results

2026-09-10 UTC. **Exploratory result: full-root C018 completed 10/10, old-root C018 completed 0/10, but every full-root Q regressed against both retained A061 and MM.** Reject the fixed policy. The controlled root-domain change supports completion across the tested structures; it does not deliver compact embeddings.

The frozen screen used ideal Z12, five Transfer004 encodings, seeds 0/1 and separate C018/full-root, C018/old-root, A061 and MM calls on hyde03, each with 60 s cold allowance. These are four original structures, including a known-feasible singleton control; g0309 relabels g0302. No private witness or MM output supplied a candidate. Root verified 40/40 finalized outcomes, terminal supervisor/lock/tmux state and one retrieval (339 files, digest `60013727d849d739f4860e3858914d9efdbd15a10d1366e62e3de8a69011f958`). The unchanged original-label oracle audit and approved passive reader passed on their first executions; root verified their 222 and 229 bindings. No time field is unknown. The ten old-root timeouts remain failures, with no credited ACL.

Every full-root regression is shown below. Times are seconds from the cold call; the final column is returned solver wall, not the last-improvement timestamp. First-valid entries are saved constructor-validator receipts; returned embeddings independently passed the original-label audit.

| Input / seed | First-valid Q @ time | Final C018 Q @ return | A061 Q | MM Q | C018 − A061 / MM |
| --- | --- | --- | --- | --- | --- |
| Grid128 / 0 | 706 @ 3.566 | 331 @ 5.291 | 168 | 133 | +163 / +198 |
| Grid128 / 1 | 570 @ 3.339 | 273 @ 4.855 | 161 | 133 | +112 / +140 |
| BA96 / 0 | 696 @ 2.683 | 428 @ 4.622 | 290 | 318 | +138 / +110 |
| BA96 / 1 | 660 @ 4.197 | 467 @ 5.681 | 287 | 271 | +180 / +196 |
| SBM96 / 0 | 592 @ 2.973 | 347 @ 4.593 | 224 | 225 | +123 / +122 |
| SBM96 / 1 | 623 @ 3.530 | 389 @ 4.810 | 238 | 217 | +151 / +172 |
| Singleton control96 / 0 | 740 @ 3.708 | 462 @ 5.725 | 266 | 189 | +196 / +273 |
| Singleton control96 / 1 | 868 @ 3.216 | 473 @ 5.581 | 236 | 176 | +237 / +297 |
| BA96 relabel / 0 | 678 @ 3.303 | 414 @ 5.372 | 267 | 274 | +147 / +140 |
| BA96 relabel / 1 | 691 @ 3.078 | 418 @ 4.929 | 293 | 287 | +125 / +131 |

All three successful methods have 2/2 successes per encoding. Values below are **mean ACL (sample variance across the two solver seeds)**. These variances are descriptive and fragile; they are not within-chain variance or a class-level uncertainty estimate.

| Encoding | C018 | A061 | MM | Mean solver wall C018 / A061 / MM |
| --- | --- | --- | --- | --- |
| Grid128 | 2.3594 (0.10266) | 1.2852 (0.00150) | 1.0391 (0) | 5.073 / 5.615 / 0.292 |
| BA96 | 4.6615 (0.08252) | 3.0052 (0.00049) | 3.0677 (0.11985) | 5.151 / 6.157 / 3.696 |
| SBM96 | 3.8333 (0.09570) | 2.4063 (0.01063) | 2.3021 (0.00347) | 4.701 / 5.827 / 0.953 |
| Singleton control96 | 4.8698 (0.00656) | 2.6146 (0.04883) | 1.9010 (0.00917) | 5.653 / 5.842 / 1.396 |
| BA96 relabel | 4.3333 (0.00087) | 2.9167 (0.03668) | 2.9219 (0.00917) | 5.151 / 5.749 / 3.031 |

C018's seed variance is smaller than MM's on BA/control/relabel and larger on grid/SBM, while its mean ACL loses everywhere. Its within-chain variance also exceeds both references on every paired row; all values remain in `mechanism001/output/encoding_statistics.json`. Relabeling changes C018 Q by −14/−49 for seeds 0/1 while preserving completion and both quality regressions. This is transfer of the completion benefit across an encoding change, not encoding invariance or a fifth independent structure. The hidden-singleton control demonstrates a particularly large compactness deficit: Q=96 is known feasible, but neither C018 nor these reference runs reaches it.

All full-root calls stopped with `valid_policy_exhausted`, after a complete unchanged quality sweep, at 4.593–5.725 s; none was cut short by the search deadline. First validity appeared at 2.683–4.197 s with Q=570–868. A further **92–147 strict-Q admissions** per call reduced Q to 273–473; event counts of 93–148 include first validity. Last improvements occurred at 4.374–5.421 s, followed by approximately 0.193–0.366 s of unchanged-sweep/finalization work. This is deterministic one-proposal policy exhaustion, not proof that no better tree or neutral transition exists. Repeating the deterministic quality sweep from this saved terminal state supplies no new proposal. A full rerun with a different timeout could change earlier time-dependent acceptance and the resulting state; it is not a tested remedy.

Total observed solver wall / CPU / process wall, including failures: C018 **51.460 / 51.457 / 56.410 s**; old roots **595.006 / 594.976 / 632.355 s**; A061 **58.381 / 58.378 / 66.943 s**; MM **18.735 / 18.734 / 21.451 s**. Full C018's exclusive stage wall includes 20.306 s regrowth, 9.474 s incumbent validation, 7.835 s root scoring and 5.869 s distance refresh; all cold setup/import/JIT costs were charged. There is no new runtime gate. Grid's mean solver time is about 17.4 times MM's despite much worse quality; other encodings also require separate inspection rather than an aggregate speed claim.

Old roots used 970–1,139 completed sweeps per call before the 59.5 s search boundary, yet retained 58/58, 180/214, 123/123, 280/313 and 175/205 missing source edges respectively in the table's encoding order. Its 1,057,155 “commits” include **1,044,785 identical states**; only 12,370 actually change geometry. Five million recorded missing free endpoints and the persistent defects are not evidence of insufficient visit count. Terminal partial Q values are diagnostic only and are never compared as successful ACL.

Sources and bindings: screen `ccb538b5cb6fde182193056e876408a530819420d53f9df66cf057b56a7c8f25`; manifest `f8d41179ed29eff5b2f351ac5a169982ce59e4df766dc2ab4bac9e02d1ab3da0`; source snapshot `1b123236393082641750d6f8e28fa83a182c4de96f64f840e1d8a837b652aa6e`. Complete audited rows, per-seed comparisons, relabels and all failures remain under `results/codex/c018-territories/{audit001,mechanism001}/output`. Two narrowly scoped scalar projections were recorded once each in `decision_projection001` and `decision_projection002`; the second adds root's requested identical-geometry and neutral-Q distinctions, preserving the first. Neither imports candidates or calls a solver. The [decision](c_018_decision.md) separates the useful mechanism evidence from rejection of the policy.
