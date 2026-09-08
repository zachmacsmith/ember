# Current research checkpoint

Updated 2026-09-08 18:11 UTC. Branch `codex`. Goal active and unmet: one
general non-portfolio algorithm, no MM/busclique, ideal Z12, competitive mean
ACL and roughly MM-scale runtime. No new final-test inputs have been exposed.

- **A / root / hyde03:** 046 is positive and independently validated: all68
  timely valid,25improvements/9ties/0regressions,89Q saved, macroACL
  3.325937→3.305570, solver total+3.9%.
  [Results](experiments/046_results_screen.md).
  The unchanged candidate is running against freshMM in047: same34inputs,
  seed0,60seconds,68paired calls; controller182328.
  [Launch](experiments/047_launch_record.md).
  048 tests continuing seed traversal after a contraction; literature owns
  implementation and targeted checks, root owns eventual freeze/lifecycle.
  [Pre-code hypothesis](experiments/048_cyclic_vacancy_hypothesis.md).
- **B / algorithm_audit / hyde02:** B004 completes7/9 but loses all7ACLpairs
  toMM. Bipartite improves strongly; three other outputs regress and repair
  cost is excessive. Reject the fixed schedule. B005 investigates propagated
  placement domains with explicit relaxation to connected chains.
  [Results](tracks/b_local_reinsertion.md),
  [design options](tracks/b_feasibility_options.md).
- **C / benchmark_audit / hyde04:** C003 completes4/8 but chains remain much
  longer thanMM. C004 is running the same8inputpanel with one compact connected
  target allocation; no restart ladder or per-input output choice.
  [Results](tracks/c_003_results.md).

The [workflow amendment](tracks/workflow.md) requires pre-code hypotheses,
pseudocode, self-critique and cheap falsifiers. Exploration retains isolated
libraries, meaningful targeted checks, independent original-edge validation,
and every failure/time. Exhaustive publication audits remain deferred.

047 snapshotfcda1fc0 / manifestaa932046 / transport3b34ed93. Frozen inputs and
lifecycle records: `results/codex/047-current-pipeline-mm`,
`results/codex/047-launch`. All prior A controllers are terminal. Observe the
existing run after network loss; never restart because SSH disconnected.

All findings remain exploratory. Local-move prior art is established; novelty,
seed variance and fresh-instance superiority remain unresolved.
