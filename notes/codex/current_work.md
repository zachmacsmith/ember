# Current research checkpoint

Updated 2026-09-08 19:30 UTC. Branch `codex`. Goal active and unmet: one
general non-portfolio algorithm, no MM/busclique, ideal Z12, competitive mean
ACL and roughly MM-scale runtime. No new final-test inputs have been exposed.

- **A / root and literature / hyde03:** Retain 048 cyclic continuation as the
  development baseline: 18 improvements, 16 ties, no regressions, another
  69 Q saved at nearly unchanged total time. Its predecessor's fresh MM
  screen has 11 wins, 19 losses and two ties on 32 common timely pairs;
  macro ACL is 14.29% lower, but median solver ratio is 10.33.
  [048 results](experiments/048_results_screen.md).
  Reject 049 reduced-core promotion: 32/34 successes versus 34/34, slightly
  worse common-input macro ACL despite 11 fewer total Q. Cycle and wheel
  fail during reinsertion, with work and deadline limits nonbinding. Trees
  reach ACL 1 and run faster. [049 results](experiments/049_results_screen.md).
  Next: bounded local release/reinsertion only when lifting blocks, testing
  whether occupied endpoints can move while outside chains remain fixed.
- **B / algorithm_audit / hyde02:** B007 growth recovers ER but still loses
  five of seven timely MM pairs and worsens WS sharply. Reject its quality
  policy. [Results](tracks/b_007_results.md). B008 finds certified Hall
  deficits in all six inspected B006/B007 prefixes: nonempty domains do not
  ensure distinct placements. All 262 offline matching queries finish in
  0.206 seconds total; this is a diagnostic cost, not integrated timing.
  [Evidence](tracks/b_008_hall_results.md). B009 replaces the weak acceptance
  criterion with bounded covering matching; six focused groups pass. The
  same nine-input fresh-MM screen is next.
- **C / benchmark_audit / hyde04:** C006b's unchanged 60-second allowance
  still completes only 4/8 and loses all four timely MM comparisons.
  Complete reaches a logged best of two missing edges but ends with three;
  the best mapping was not saved. [Results](tracks/c_006b_results.md).
  Supplied-state free paths add contacts but complete none of four states.
  Every state has a missing edge incident to a chain with no unused neighbor,
  proving additions alone cannot finish while ownership stays fixed.
  [Diagnostic](tracks/c_free_path_results.md). Next: a bounded directed
  ownership-repair mechanism, first on tiny and supplied states.

All three preceding cluster controllers are terminal and quiescent. Observe
existing runs after network loss; never restart because SSH disconnected.
Candidate outputs are evaluated separately. Local proposals act on one evolving
embedding and are not a portfolio of independent constructor outputs.

The [workflow amendment](tracks/workflow.md) requires pre-code hypotheses,
pseudocode, self-critique and cheap falsifiers. Exploration retains isolated
libraries, targeted checks, independent original-edge validation, and every
failure/time. Exhaustive publication audits remain deferred. All findings here
are exploratory; novelty, seed variance and fresh-instance superiority remain
unresolved.
