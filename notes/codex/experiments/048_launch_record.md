# 048: cyclic seed-order screen, launch and completion

Frozen after the [pre-code hypothesis](048_cyclic_vacancy_hypothesis.md) and
33 focused checks passed. The 34 source graphs, target and selection bytes
are unchanged from 042/046/047. Seed 0, ideal Z12, 60 seconds per call;
68 separate fresh calls compare bounded and cyclic vacancy scheduling on
hyde03. No MM call is part of this treatment/control screen.

- Snapshot: `3b2c862ee9698765e72fd3edb3667d3225a84c648eadd210f224d07366d43873`.
- Manifest: `3d80a2bfe8b9d4dd597b47b3e272fbf46169d134c94a7c796ca6adef58407775`.
- Transport: `47b37763b93c5d76b63903281933166e49ef9051a9df0bc047fcab18ea8c3aa1`.
- Protocol: `12f8f75983df802be5961ad2c3dbc0171c13ad7a903fbd9d0cf8c5a0fc97c0fc`.

The existing cluster CLI staged once and started one detached controller,
PID 184715. Supervision started at Unix time 1788891819.4518578; controller
completion was 1788892254.7658336. All 68 calls report SUCCESS. Both terminal
observation and retrieval confirm a free lock, no running tmux session and
supervisor exit 0. The final active-worker record is historical. No restart
or duplicate launch occurred.

Retrieval verified 446 files under
`results/codex/retrieved/hyde03/048-cyclic-vacancy-pipeline`; archive digest
`5ddecb714599370ed91fd386a558711fd2a054209421d75bc7bbfda4a60a0caa`.
Exact CLI invocations, timestamps and outputs are in `results/codex/048-launch`.
The frozen minimal screen subsequently passed all original-output and cyclic
membership/order/cursor checks. [Results](048_results_screen.md): 18 quality
improvements, 16 ties, no regressions. It does not claim exhaustive intermediate
connectivity replay.
