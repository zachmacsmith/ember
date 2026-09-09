# C011: computation-allocation comparison launch

`track-c-011-wall-budget` was frozen, staged and started once on hyde03;
24 fixed calls, C010/C011/MM, seed0/15s. The [proposal](c_010_wall_budget_diagnostic_proposal.md),
[implementation](c_011_wall_budget_implementation.md) and
[protocol](c_011_wall_budget_screen.md) remain fixed. Root verified23 author
bindings, all35 copied input files and the exact24 task vector.

- Source snapshot: `757bc9f911c9cefdda50ecba033a3cbf182fb98e980891ebaa0667d6493e61f8`.
- Manifest: `cf2231118287f5dcf1f23d0ae64f04d1d16e3b091c73c12f3c3549a457752ac6`.
- Plan: `baac23fabf3cd091759394c8969ae54c7a59b5ba84166489945ade7a8cb2eaf5`.
- Author manifest: `5268e7b6a2ceac1fa8ad9294706fbfe2edcb20b020512101781ad6a6d603f012`.
- Transport input digest: `2e5bb2584459c95f762620fabcfb17cf38edbec2a8419c4bbcba489845bdd490`.
- Detached start epoch: `1788921599.204276`.

Candidate/MM environments remain isolated, with the unchanged original
validator and all late/error non-credit gates. The only pilot changes are
two new constructor entries; all33 inherited entries and other AST are
unchanged. Action evidence is in `results/codex/track-c011-launch`.
Observation failure never permits another start.

Terminal update, 2026-09-09: all24 calls finalized; controller221967 exited0
at1788921747.147618. One retrieval preserved237 files, archive digest
`21ccf8f9ad394a6b2dfc35e0533c1e44a83d9f31371dfeb321c38eaa8c60fd9c`.
The single saved-data analysis passed with no audit errors. Root read the
[results](c_011_results.md) and verified31 final evidence bindings in
`results/codex/track-c-011-review/review_manifest.json`, SHA256
`bbed3d416b7805e9def0ba3042a95324ac0618e3a44c2e936b99785b2a0c5264`.
Retire the fixed wall-allocation variant: both candidates2/8,MM6/8; no extra
completion despite using the formerly unused search time.
