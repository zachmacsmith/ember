# 049: reduced-core construction screen

Launched after the [pre-code design](049_source_reduction_hypothesis.md),
11 focused checks and all three positive Z12 reach falsifiers passed. Root
reviewed the source, narrow cleanup correction and targeted checks; no repeated
audit was needed. Native and its cyclic configuration remain unchanged.

The 34 structures, 35 memberships, target and selection bytes exactly match
042/048. Seed 0, 60 seconds per call, 68 fresh separate processes on hyde03:
`native-search-joint1-contacts-spectral-vacancy-cyclic` versus
`native-reduced-core`. The latter has empty external configuration and makes
at most one fixed native call on its reduced core. No MM arm is part of this
control/treatment experiment. No corpus output was used by either method.

- Snapshot: `73564a802ca8be67bdcde07b096c71882e9dd7d9458d5a39136802e111bd5f45`.
- Manifest: `f34b975a46059d29ca23c794e9a8cea725c1be09816d3d4efbe093d55e1111cb`.
- Protocol: `e75a42842a941230342e5a87c18c21dc23abb2dbc2576dece08316b8a30f23c1`.
- Transport: `9b4755368fa8c4ef501c918c4d2e396c8a9157afda01e643a346bc8eac0b675a`.
- Pilot: `8eeb7b4be1f6d3dc9f6c34638049d2908f9b8b1b0f9fef527e919f1b137299a0`.

The existing cluster CLI staged once and started once. Controller 187555
started at Unix time 1788894349.7950585. A fresh SSH observation confirms
the running controller, worker187613, occupied lock and live tmux session
`ember-codex-fa39528c0ce57653b60c`; six of 68 calls were finalized SUCCESS.
The detached supervisor has its ordinary 6420-second outer cap. Those statuses
are provisional until final independent validation. No restart is authorized
merely because an observing connection drops.

Exact commands/timestamps are retained in `results/codex/049-launch`; immutable
inputs are in `results/codex/049-reduced-core-pipeline`. The saved-data screen
will retain every failure and total cost, independently validate original
outputs and active partial requirements, and check reduction/work accounting.
It will not replay every intermediate physical search proposal. The current
claim is only that the targeted implementation gate passed and the development
experiment is running.
