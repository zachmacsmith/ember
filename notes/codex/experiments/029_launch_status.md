# Experiment 029: verified Sudoku comparison launch

The exact staged Sudoku development comparison was started once on hyde03
after 026 completed and its 430-file archive was retrieved with all file
hashes verified. 026 finished at `2026-09-08T03:06:00.865762Z`; fresh status
confirmed all 68 results finalized, controller complete, lock free, tmux
stopped, and supervisor exit 0. Its retrieval inventory digest is
`b2a5cd4cac7394ade97f01dcf2c0f72f4619d009ad4f849e2fb0c9ce114610d9`.

029's supervisor started at `2026-09-08T03:07:05.003000Z` in tmux session
`ember-codex-49812573bd23b20a2c63`, with a maximum lifetime of 840 seconds.
The remote directory is
`/home/dabh/ember-codex/runs/029-sudoku-development-comparison`.
A fresh SSH status check confirmed controller PID 124544, active worker
PID 124553, held inherited worker lock, and live tmux supervisor, with 0/6
results finalized at that first observation. The initial launch response
preceded controller/worker record creation; it was not the only liveness check.

| Frozen identity | SHA-256 / commit |
| --- | --- |
| Commit | `4cad1d67c59484b4d9583e02f49d06e1a556b2af` |
| Source snapshot | `321f24371678f3080b4aef67bcdb43479b5acce7b7ec90b47acdf01b82afd747` |
| Transport | `88e1c99260de51f3c42c1a226ed71a664f3cecdc199357b20369d5edb518b29a` |
| Sudoku supplement | `e6e3036634164be8e5491d0c6b8d41e8d4fb042fd63fe3fd43fda3538018f047` |
| Comparison plan | `ff77c22ce191c2dfe27dfab9cac149e4b7dd9fcf3618b8e14d41514ac33846a0` |
| Ideal Z12 target | `38cde794d3c1461054a45b5a660d157737b019c19cb9a7b38e2027730e3d5938` |

Local prelaunch checks verified the supplied commit and source identity, all
frozen source hashes, all six task digests, fixed seed/deadline/configurations,
the supplement and plan IDs, all eight supplement bundle file hashes, and exact
target bytes against 026. The launcher verifies the staged transport before
starting the controller. Full supplement semantic and result auditing belongs
to the completed-run review, not to this liveness record.

There are two explicit development sources: box order 2 (16 vertices) and
box order 3 (81 vertices). Both receive MM, contacts, and spectral-contacts
at seed 0 and 60 seconds, six trials in total. Candidate and MM environments
remain separate. This supplement is not a replacement for original oversized
Sudoku inputs and is not merged into readiness selection 017. Orders 4 and 5
remain outside this run. No outcome was used to select a method per source or
alter the frozen comparison.

Raw launch and fresh-status responses are saved at
`results/codex/029-launch/`. Timing comparisons must use the three arms within
029; no timing population is pooled with earlier corpus or local smoke runs.
These records establish successful launch only, not completion or quality.

```sh
.venv/bin/python scripts/codex/cluster.py --host hyde03 status 029-sudoku-development-comparison
.venv/bin/python scripts/codex/cluster.py --host hyde03 fetch 029-sudoku-development-comparison results/codex/retrieved/hyde03/029-sudoku-development-comparison
```

Fetch only after verified quiescence. Do not restart after a transient status
or connection failure; check the existing supervisor and lock first.

## Later completion and retrieval

A later fresh status confirmed 6/6 finalized SUCCESS records, controller
complete, lock free, tmux stopped, and supervisor exit 0. Completion was
`2026-09-08T03:08:11.141676Z`. The completed archive was then retrieved with
all 95 file hashes verified; inventory digest is
`eb27661c6f97ff253e30a15f77e00eb070969bb8ea83b4fe5b00b4e1111f17a9`.
The independent semantic, provenance, embedding, and timing review is in
`029_results_review.md`. The original launch observations above remain intact.
