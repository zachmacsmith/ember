# Contact rearrangements on the fixed Ember readiness inputs

Protocol fixed before this run's outcomes. Retain every one of the 34 exact source
structures in selection 017, all 35 family memberships and its missing Sudoku record.
Compare exactly two fixed end-to-end candidate configurations at seed 0 and 60 seconds:
strict sites/groups reconstruction and the same pipeline with the lexicographic
qubit/contact-redundancy objective. This is 68 trials on hyde03, started only after
019 finishes. Both use greedy contact trees; the unsuccessful distance-tree
revision is excluded globally, with its negative results preserved in 023.

The selection of contact redundancy is based on 022/024's 18 development incumbents:
25 additional qubits saved, nine improvements, seven ties and two regressions,
with modest observed overhead after redundant validation was removed. That result
does not demonstrate transfer to these 34 corpus structures. This screen tests
such transfer without any family-dependent parameters or outcome selection.

Both arms use the same independent constructor, 1000 placement evaluations,
four refinement passes, 512 total groups, 500000 shared work units, region cap 512,
16 additional boundary-contact sites, group sizes 1–4, outer beam width 1 and the
round-robin group schedule. Only the acceptance objective differs. The same
source/target graphs and solver seed are supplied in fresh processes and
separate empty JIT caches. Numerical-library threads remain fixed at one.

MM's full 019 outcomes remain a historical quality comparator on the identical
inputs/seed/target/version, with their successes and failures explicitly retained.
MM is not rerun in this development screen. Do not report contemporaneous MM
timing ratios for 025, silently pair missing outcomes, or pool elapsed timings
across runs. The strict candidate control is rerun here to detect changed
construction behavior and provide within-run timing comparisons. Any confirmatory
MM timing claim requires new paired runs after the algorithm is frozen.

One graph per family and one seed do not establish family means or ACL variance.
Report each fixed candidate separately, all failures, and the exact shared-input
mapping. A tie where MM reaches ACL 1 must be described as an optimal tie, never
as lower mean ACL. The user's preferred success criterion for such ties remains
a pending clarification; the research objective is not redefined by this screen.

## Frozen inputs and staging

Code revision: `a33a44848d877baf085fb503a98bfdf8b0bcd0e5`.
Source snapshot: `c4df2294edf74b55f767ee443e30f88d4a068cbed8a21e9b45cf33df420ffb8d`.
Verified transport digest: `dd31a6a2c94f15da08e6549eb8eada585a1e24fbeb9f493b05bad2e8509b5827`.
The 68 tasks are frozen locally at `results/codex/025-corpus-contact-rearrangement`
and staged at `/home/dabh/ember-codex/runs/025-corpus-contact-rearrangement` on
hyde03. Staging did not start a worker; launch followed observed quiescence of
019 to preserve the declared sequential host protocol.

## Launch and live verification

The detached tmux supervisor started at Unix time `1788835033.8327`, in session
`ember-codex-9e948f74e5d7acd28000` on the separate `ember-codex` tmux server. Its
maximum lifetime is 6420 seconds. A fresh SSH status check confirmed controller
PID 120218 and worker PID 120414, a busy inherited lock, a live tmux session and
17 finalized successes out of 68 planned trials. This is an intermediate status,
not evidence about complete-run performance. Continue this exact run without
restarting it after a connection interruption; retrieve after verified quiescence.

A later fresh check confirms terminal quiescence: all 68 tasks finalized SUCCESS,
controller complete, inherited lock free, tmux stopped and supervisor exit 0.
The benchmark auditor is retrieving and hash-verifying the archive. Full
quality and timing interpretation remains pending independent analysis; the
all-success count alone does not establish an ACL improvement.
