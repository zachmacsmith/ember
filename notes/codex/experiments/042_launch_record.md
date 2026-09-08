Experiment 042 was launched once on hyde03 at 2026-09-08 15:28:00.073 UTC,
under controller 165387. It compares the fixed spectral/contact control with
the same pipeline followed by optional deletion cleanup, across all 34 original
development structures (35 memberships, shared topology counted once).
The 68 calls are serial, seed zero, ideal Z12, with the same 60-second native
deadline and 90-second process watchdog. Endpoint scoring is off in both arms.
There is no MM arm, portfolio, restart or extra cleanup allowance.

The frozen source revision is `c789e5bcefc0d34498e83107474e4bfaf82f2a6e`.
Its 50-file snapshot is
`14d2d4b8fec918e06b08ce3404ed194e5bbe745adf37eb6c9658813140c62063`;
manifest SHA256 is
`49fa55780f0cb732eb0439af12122d877c157a98ef91178fca864ce6ffd0b063`.
The verified 156-file transport digest is
`d6510eab6afcf1d203f0eaf8f512f3a770c652cd1c55fe2e979845eec8a9407d`.
The local run is `results/codex/042-final-deletion-pipeline`; the remote run is
`/home/dabh/ember-codex/runs/042-final-deletion-pipeline`.

Root read the complete independent local/remote preflight and synthetic
wrappers, accepted the final report, and verified all 84 review files and
35 references. The final preflight manifest is
`337a04be0c13873701a9b1653028ffebedaa522a2469d325983d448b2678fdb1`.
The target-environment synthetic suite passed all 12 groups once, with actual
reviewed native/deletion modules and no prohibited imports. All ten retrieved
evidence files match digest
`f04bdebf2d86dfcc791f22655fb5c7d31b35232226b96ef0153c48db08ac6c8f`.
The known dwave-networkx deprecation warning is retained. A reviewer's initial
empty-stderr assertion was corrected using the saved evidence; neither tests
nor benchmark calls were repeated for that correction.

The final remote metadata observation at 15:23:07.062 UTC found the staged run
unattempted, all source/input bytes exact, empty output/cache directories and
nine earlier manifest-bearing runs quiescent. The prepared native environment
contains no MM or busclique package. Root's prelaunch acceptance is saved in
`results/codex/042-launch/root-prelaunch-acceptance.json`, SHA256
`7f57ad841397eaae94167da001a446932de71a86395e5da9b74508100b80ce9d`.

The detached route is tmux plus timeout, with a 6,420-second supervisor ceiling
and `KillUserProcesses=false`. A fresh SSH observation at 15:28:01.097 UTC
confirmed controller 165387 and worker 165408 as actual matching processes,
with the inherited lock held and tmux running. This demonstrates detached
execution and fresh reconnection, not a physical WiFi-switch test.

Root owns subsequent observations and retrieval. If an observer disconnects,
inspect this same run; do not launch another controller. Retrieve only after
verified controller/worker quiescence. Outcomes remain pending. The result
auditor is being prepared against the already frozen comparison expectations,
including independent reversal and forward validation of the full deletion
trace. Internal cleanup savings and full-pipeline paired improvements will be
reported separately. One development seed cannot establish variance,
generalization or MM superiority.
