# Experiment 026: verified cluster launch

The frozen spectral-initialization comparison was started exactly once on
hyde03 after experiment 025 had completed and its archive had been retrieved
with all 429 file hashes verified. No 025 result was used to change the already
frozen 026 source, graph selection, parameters, or method list.

025 finished at `2026-09-08T02:51:07.705308Z`, with 68/68 finalized SUCCESS
records, controller status complete, lock free, tmux stopped, and supervisor
exit 0. Its retrieved inventory digest is
`6d4d1d4c8c87d6c2519be9ac982ea4f0fce763448b133aa44b5615e016de523c`.
The archive is `results/codex/retrieved/hyde03/025-corpus-contact-rearrangement/`.

026's supervisor started at `2026-09-08T02:51:44.531316Z` under tmux session
`ember-codex-ef2a0cc9c971540d0411` in the isolated `ember-codex` tmux server.
The maximum supervisor lifetime is 6420 seconds. The remote run directory is
`/home/dabh/ember-codex/runs/026-corpus-spectral-initialization`.

The immediate launch response preceded controller/worker record creation.
A separate fresh SSH status check then confirmed running controller PID
122275, active worker PID 122287, held inherited worker lock, live tmux
supervisor, and 0/68 finalized tasks at that observation. This distinguishes
successful worker startup from the launch command's initial return alone.
The inactive systemd fields are expected because tmux is the active supervisor.
A subsequent fresh status confirmed 4/68 finalized SUCCESS records, active
worker PID 122416, and the same live controller, held lock, and tmux supervisor.

Before launch, local verification checked all frozen source hashes and task
digests, the supplied commit and source identity, the two fixed method
configurations, and exact target/original-selection/readiness-selection
sidecars against 025. The launcher verifies staged transport before starting
the controller. The frozen identities are:

| Item | Identity |
| --- | --- |
| Commit | `f93f889f428baa26d1722382c77de385d4b4822f` |
| Source snapshot | `91824466fdd3880940df0cc6d3569a461a617c3d1ae883e50425ee368952a765` |
| Staged transport | `481ae432e47dc5b0c9f3951d38080ee21e9de0d9e52833bafd15985322c9608c` |
| Target | `38cde794d3c1461054a45b5a660d157737b019c19cb9a7b38e2027730e3d5938` |
| Readiness selection | `06c02356f8df5503b57f280ba4939c298cc05834c563a3da8a71f96fe245db98` |

The 68 tasks contain 34 calls to each of
`native-search-joint1-contacts` and
`native-search-joint1-contacts-spectral`. All use the same 34 source structures,
35 family memberships, missing Sudoku record, seed 0, ideal Z12, and 60-second
overall solver allowance. The only explicit configuration difference is
`initialization='spectral'`. The declared source-only initializer and its
work/deadline policy are described in `026_spectral_initialization.md`.

Both arms use the native environment
`/home/dabh/ember-codex/envs/4e1fb892db12754e/native/bin/python`, fresh
processes, empty per-task JIT caches, one numerical-library thread, and the
worker's MM/busclique absence guards. The run contains no MM tasks. MM019
can provide historical quality evidence only; timing comparisons must be
between the two arms of 026 itself.

Raw launch and fresh/progress status responses are saved separately from
the frozen task directory at `results/codex/026-launch/`. These observations
establish launch and liveness, not completion or an embedding-quality result.
Do not restart the controller after an observation failure; reconnect and
check the run lock and supervisor first. Fetch only after quiescence.

```sh
.venv/bin/python scripts/codex/cluster.py --host hyde03 start 026-corpus-spectral-initialization
.venv/bin/python scripts/codex/cluster.py --host hyde03 status 026-corpus-spectral-initialization
.venv/bin/python scripts/codex/cluster.py --host hyde03 fetch 026-corpus-spectral-initialization results/codex/retrieved/hyde03/026-corpus-spectral-initialization
```

The `start` command above records the action already performed; it is not
an instruction to launch a second controller.
