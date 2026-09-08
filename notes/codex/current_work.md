# Current research checkpoint

Updated 2026-09-08 18:40 UTC. Branch `codex`. Goal active and unmet: one
general non-portfolio algorithm, no MM/busclique, ideal Z12, competitive mean
ACL and roughly MM-scale runtime. No new final-test inputs have been exposed.

- **A / root / hyde03:** 047 independently validates the current pipeline
  against fresh MM. On 32 common timely pairs: 11 ACL wins, 19 losses, two
  ties; macro ACL is 14.29% lower, driven by large gains on harder inputs.
  Candidate succeeds on all 34, MM on 32. Median paired solver ratio is
  10.33; 16/32 exceed 10×. Broad superiority and runtime goals remain unmet.
  [Results](experiments/047_results_screen.md). 048 is complete, all 68
  reported SUCCESS; original-output and scheduling checks are pending.
  [Launch](experiments/048_launch_record.md). A049 is design only: low-degree
  source elimination followed by core embedding and reverse reinsertion.
- **B / algorithm_audit / hyde02:** B005 completes 6/9 and obtains its first
  two MM wins: grid and honeycomb reach ACL 1. Four other timely pairs lose;
  ER regresses to failure. Constraint propagation helps singleton placement,
  but promotion to chains does not preserve its future feasibility.
  [Results](tracks/b_005_results.md). B006 tests one-use reuse of completed
  domains, with 14 targeted checks passed; the same nine-pair screen is next.
  B007's future-domain-aware growth is a separate proposed quality change.
- **C / benchmark_audit / hyde04:** C005 fails its predeclared test: still
  4/8 valid, all four lose MM, no new hard success or halved contact deficit.
  Constant-Q movement crosses the initial target boundary, but does not
  resolve the search limitations. [Results](tracks/c_005_results.md).
  C006 will test preserving distinct quotient neighbors during contraction,
  using C004's search baseline so failed C005 changes are not bundled.

The [workflow amendment](tracks/workflow.md) requires pre-code hypotheses,
pseudocode, self-critique and cheap falsifiers. Exploration retains isolated
libraries, meaningful targeted checks, independent original-edge validation,
and every failure/time. Exhaustive publication audits remain deferred.

All prior A controllers, including 048, are terminal. Observe existing runs
after network loss; never restart because SSH disconnected. Candidate outputs
are evaluated separately.

All findings remain exploratory. Local-move prior art is established; novelty,
seed variance and fresh-instance superiority remain unresolved.
