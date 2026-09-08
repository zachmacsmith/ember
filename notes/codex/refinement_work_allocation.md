# Failed auxiliary search should not silently replace ordinary work

2026-09-08. Future allocation hypothesis and self-critique only. No production
change, experiment or revision to the frozen 038 diagnostic or connected-core
implementation policy is made by this note.

## Evidence and limited causal claim

The complete [037 comparison](experiments/037_results_review.md) shows why local
shortening alone is insufficient. Matching moves save 38 qubits inside the
treatment, while ordinary reconstruction saves 31 fewer than its control.
The whole pipeline saves only seven. Two regressing inputs have no committed
matching move at all. In this run all calls are timely and the saved upstream
stage summaries match within pairs. Auxiliary work consumes the shared work
allowance and leaves fewer ordinary operations on some inputs.

These observations support testing work allocation separately from the search
neighborhood. They do not establish that all 31 displaced qubits are caused by
the quota: successful moves also change subsequent reconstruction opportunities,
group membership and equal-Q trajectories. Nor do they establish that granting
more work would recover any particular unsaved continuation.

## One possible general policy, not yet selected

Retain one construction and its evolving valid incumbent. Keep ordinary
reconstruction's original work allowance W and fixed group/visit limits.
Allow attached auxiliary queries an additional, separately counted allowance
`floor(W/20)`. Both operations share the original absolute solver deadline.
Count total actual work as ordinary plus auxiliary, with total at most
`W + floor(W/20)`; do not call this equal work with the control. No extra
constructor, independent result selection, source-class condition or seed
choice is introduced.

Ordinary reconstruction still runs first in each existing group visit. A
failed visit can trigger the same once-per-center/pass auxiliary consideration.
The visit's combined work ceiling may remain unchanged, since auxiliary work
comes afterward; it must not reduce the allowance of a later ordinary visit.
Owner-cache setup and post-commit maintenance count only against the auxiliary
allowance and that visit's remaining work. Exhausting auxiliary allowance
disables further auxiliary work for the call. Every timeout or suppressed
ordinary operation due to elapsed wall time remains visible.

This would require explicit separate counters. Reusing a total counter as the
ordinary stopping test would reproduce the current displacement and violate
the proposed policy. The auxiliary allowance must not reset per pass, root or
group, and its descriptive returned work must not be charged a second time.
The exact current 5% fraction is a proposed engineering ceiling inherited from
the existing experiment, not a tuned or theoretically optimal allocation.

There is a useful conditional replay property to test: if no auxiliary move
commits, all auxiliary access to the incumbent is read-only, the same ordinary
non-time limits are reached and the deadline does not bind, ordinary results
should match the control's deterministic trajectory. The wall-time condition
matters; the policy cannot guarantee no regression under a binding deadline.
When an auxiliary move does commit, this property no longer applies, and even
strict local descent can still lead to a worse final output than the control.

## Self-critique before implementation

1. This spends more work. A nominal 5% operation allowance is not 5% of elapsed
   time, and root/matching/validation operations have different costs. Include
   the whole solver/process time and all setup, failed search and maintenance.
2. A harder runtime bound still cuts into later ordinary work. The conditional
   replay property is no substitute for measured success and quality under the
   actual deadline, especially on larger future inputs.
3. It may recover only the few no-commit regressions while leaving the much
   larger quality deficit against MM unchanged. That would be an engineering
   improvement, not the sought research result or a novelty claim.
4. An experiment changing both the connected neighborhood and this allocation
   would confound their effects. If tested, freeze an allocation-only comparison
   of the same auxiliary kernel first, or explicitly label a combined revision
   and avoid attributing gains to one component. Never select policies per input.
5. More generous quotas can hide an inefficient move. Compare end-to-end cost
   and useful improvement, retaining failures and zero-commit cases. Do not
   grant progressively larger budgets until a desired benchmark number appears.

The present connected-core interface can accept a caller-supplied visit budget,
but its implementation task continues to use the previously reviewed shared
budget contract. Any future scheduler change needs its own fixed specification,
counter/conditional-replay checks, and complete all-input experiment. No such
change or experiment is authorized by this design note.
