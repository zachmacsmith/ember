# C007 host amendment before observations

2026-09-08 22:56 UTC. The original hyde04 freeze and successful staging are
preserved. Its sole start attempt was rejected before creating a supervisor:
`tmux` is absent. Status001 confirms zero finalized tasks, no controller,
no supervision record, free lock and no tmux session. A read-only probe confirms
`Linger=no`, `KillUserProcesses=false`, and `timeout` present. There has been
no C007 algorithm call, result, or candidate-dependent selection.

Move the entire fixed 24-call experiment to idle hyde03, under a new run name
`track-c-007b-atomic-growth`. Use the already isolated native/MM environments
`4e1fb892db12754e` (Python3.10.12). The same three arms, configurations, graph
and target bytes, seed0, shuffled task order and fifteen-second timeout remain.
Source snapshot stays fixed; task IDs/manifest change with interpreter paths.
This changes host/Python, so no04 historical time is pooled. All paired times
come from03. Local constructor gates already used native Python3.10; existing
runtime dependency guards and independent validators are reused.

The original pre-observation mechanism protocol and plan remain immutable.
This amendment supersedes only their host/interpreter/run-path statements.
Root owns a new freeze/stage/start record under `track-c007b-launch`; the
unstarted04 bundle is retained as transport evidence and will not be started.
