# 054 launch record

2026-09-08. Run `054-degree-two-focused-pipeline` on hyde03 compares fixed
A053 and A054 on 16 exposed structures / 17 memberships, seed 0, ideal Z12,
60 seconds each. The [protocol](054_degree_two_focused_screen.md) selects all
13 inputs whose source-only core or journal changes, plus the first three
unchanged controls in the existing manifest order. This selection precedes
A054 corpus outcomes; no inference is made for the other 18 inputs.

- Source snapshot: `6cf5167ab50aa8a95c664e6d5a2911a7e27c92f87a96e5d17a358dc6e4dd350e`.
- Task manifest: `63e146c12d4c96595f67eaf4b86de53f0f29781abfa84fa4ad910b609955af3d`.
- Protocol: `ff45d19f37724243db587cb890b1e19a8feb880ba4a1f8099cfe2264bb0983b5`.
- Pilot: `9324805cc067862035454edd64166756ace9d679877af7c60a239366e5b437c3`.
- Transport input digest: `67783db330b49e6d37f426c24d8d4f3df0f4cd9b3e6d70fc0e564737bcd3dab5`.

Freeze, stage001 and start001 succeed once. The detached tmux session is
`ember-codex-1be2f2ca0cd6bcd8ba9f`, with a 3180-second outer bound and
supervision start Unix 1788904687.9210181. There is one actual launch and
no restart. Unique invocation directories under `results/codex/054-launch`
preserve argv, stdout, stderr and exit codes. Root owns launch and retrieval.

Status001 is terminal: 32/32 SUCCESS, controller 200969 finished at Unix
1788904869.227288, free lock, absent tmux and supervisor exit 0. The last
active-record PID 201118 is historical. Fetch001 verifies 266 files at
`results/codex/retrieved/hyde03/054-degree-two-focused-pipeline`, archive
digest `cf4c6d6d9bac230faa98331ace719619855639e88933d76005880ae1923eb2d6`.
No observation or transport failure occurred. The prepared saved-result
screen passes on its first execution; no candidate rerun follows.
