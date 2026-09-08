# Current research checkpoint

Updated 2026-09-08 19:07 UTC. Branch `codex`. Goal active and unmet: one
general non-portfolio algorithm, no MM/busclique, ideal Z12, competitive mean
ACL and roughly MM-scale runtime. No new final-test inputs have been exposed.

- **A / root / hyde03:** 047 independently validates the current pipeline
  against fresh MM. On 32 common timely pairs: 11 ACL wins, 19 losses, two
  ties; macro ACL is 14.29% lower, driven by large gains on harder inputs.
  Candidate succeeds on all 34, MM on 32. Median paired solver ratio is
  10.33; 16/32 exceed 10×. Broad superiority and runtime goals remain unmet.
  [Results](experiments/047_results_screen.md). 048 passes independent checks:
  18 improvements, 16 ties, no regressions; 69 further Q saved with total
  solver time 194.330→194.629 seconds. Retain cyclic continuation for further
  development. [Results](experiments/048_results_screen.md).
  A049 passes its 11 focused checks and star/wheel/subdivision reach gate.
  Its 68-call reduced-core comparison is now running on03, controller187555.
  Native remains unchanged; the wrapper owns the original deadline and checks
  every core return. [Launch](experiments/049_launch_record.md).
- **B / algorithm_audit / hyde02:** B005 completes 6/9 and obtains its first
  two MM wins: grid and honeycomb reach ACL 1. Four other timely pairs lose;
  ER regresses to failure. Constraint propagation helps singleton placement,
  but promotion to chains does not preserve its future feasibility.
  [Results](tracks/b_005_results.md). B006 reproduces all nine final/partial
  embeddings and decisions exactly, removing 3,074,312 counted units through
  212 immediate reuses. Wall time is mixed; no speedup claim.
  [Results](tracks/b_006_results.md). B007's separate future-domain-guided
  growth passes 15 focused checks, including actual triangle/C4 completion
  and preserved existing contacts; its nine-input screen has started on02.
- **C / benchmark_audit / hyde04:** C006 preserves more distinct initial
  quotient contacts on all eight inputs. On complete, initial missing edges
  fall 5,554→1,168 and final missing edges 3,514→146. It still completes
  only 4/8, and all four timely quality pairs lose MM.
  [Results](tracks/c_006_results.md). The unchanged-code 60-second followup
  is running on04, controller170867, testing continued convergence versus a
  plateau. Fresh paired MM uses the same allowance and host.
  C005's unsuccessful boundary-exchange policy remains excluded.

The [workflow amendment](tracks/workflow.md) requires pre-code hypotheses,
pseudocode, self-critique and cheap falsifiers. Exploration retains isolated
libraries, meaningful targeted checks, independent original-edge validation,
and every failure/time. Exhaustive publication audits remain deferred.

All A controllers before 049, including 048, are terminal. Observe existing runs
after network loss; never restart because SSH disconnected. Candidate outputs
are evaluated separately.

All findings remain exploratory. Local-move prior art is established; novelty,
seed variance and fresh-instance superiority remain unresolved.
