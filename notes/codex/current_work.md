# Current research checkpoint

Updated 2026-09-08 19:00 UTC. Branch `codex`. Goal active and unmet: one
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
  A049 is being implemented: low-degree source elimination followed by one
  core embedding and reverse reinsertion. Its star, wheel and subdivision
  reach gate must pass before a corpus launch. Native remains unchanged;
  the wrapper owns the original deadline and checks every core return.
  [Pre-code design](experiments/049_source_reduction_hypothesis.md).
- **B / algorithm_audit / hyde02:** B005 completes 6/9 and obtains its first
  two MM wins: grid and honeycomb reach ACL 1. Four other timely pairs lose;
  ER regresses to failure. Constraint propagation helps singleton placement,
  but promotion to chains does not preserve its future feasibility.
  [Results](tracks/b_005_results.md). B006 reproduces all nine final/partial
  embeddings and decisions exactly, removing 3,074,312 counted units through
  212 immediate reuses. Wall time is mixed; no speedup claim.
  [Results](tracks/b_006_results.md). B007's separate future-domain-guided
  growth passes 15 focused checks, including actual triangle/C4 completion
  and preserved existing contacts; the nine-input screen is next.
- **C / benchmark_audit / hyde04:** C006 preserves more distinct initial
  quotient contacts on all eight inputs. On complete, initial missing edges
  fall 5,554→1,168 and final missing edges 3,514→146. It still completes
  only 4/8, and all four timely quality pairs lose MM.
  [Results](tracks/c_006_results.md). An unchanged-code 60-second followup
  on all eight inputs will test whether the improved search continues to
  completion or plateaus; fresh paired MM uses the same allowance and host.
  C005's unsuccessful boundary-exchange policy remains excluded.

The [workflow amendment](tracks/workflow.md) requires pre-code hypotheses,
pseudocode, self-critique and cheap falsifiers. Exploration retains isolated
libraries, meaningful targeted checks, independent original-edge validation,
and every failure/time. Exhaustive publication audits remain deferred.

All prior A controllers, including 048, are terminal. Observe existing runs
after network loss; never restart because SSH disconnected. Candidate outputs
are evaluated separately.

All findings remain exploratory. Local-move prior art is established; novelty,
seed variance and fresh-instance superiority remain unresolved.
