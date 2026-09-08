# Current research checkpoint

Updated 2026-09-08 19:49 UTC. Branch `codex`. Goal active and unmet: one
general non-portfolio algorithm, no MM/busclique, ideal Z12, competitive mean
ACL and roughly MM-scale runtime. No new final-test inputs have been exposed.

- **A / root and literature / hyde03:** Retain 048 cyclic continuation as the
  development baseline: 18 improvements, 16 ties, no regressions, another
  69 Q saved at nearly unchanged total time. Its predecessor's fresh MM
  screen has 11 wins, 19 losses and two ties on 32 common timely pairs;
  macro ACL is 14.29% lower, but median solver ratio is 10.33.
  [048 results](experiments/048_results_screen.md).
  Reject 049: 32/34 successes and slightly worse common-input macro ACL.
  [049 results](experiments/049_results_screen.md). Its two failed lifts
  involve contention for another chain's last free extension site.
  [Diagnosis](experiments/049_failure_frontiers.md). A050's bounded release
  repair passes P4 and both saved failed steps with every future guard intact.
  Cycle/wheel each succeed after moving one identified competing owner.
  Narrow rollback and unchanged ordinary-path checks precede a fresh
  049-versus050 screen on03; its launcher is prepared but not run.
- **B / algorithm_audit / hyde02:** B009's covering matching is cheap but
  loses ER completion: 6/9 versus B007's7/9, with two fresh MM wins/four losses.
  All846 matching queries complete; reject policy promotion.
  [Results](tracks/b_009_results.md). B010 finds an admissible alternative
  route at ER's saved blocked step. The existing search repeatedly chooses
  a shorter route consuming unrelated chains' last free site.
  [Evidence](tracks/b_010_frontier_results.md). B011 will filter connector
  sites unusable under every eligible two-ended ownership cut, with the
  same search/matching/growth limits. Targeted reach precedes the nine-input
  fresh-MM comparison on02.
- **C / benchmark_audit / hyde04:** C006b still completes only4/8 and loses
  all four timely MM comparisons at60seconds. [Results](tracks/c_006b_results.md).
  Free paths cannot finish any of its four saved hard states with ownership
  fixed. Directed donor exchanges repair2/25 inspected sealed edges, both
  on SBM; neither query completes the original source.
  [Diagnostic](tracks/c_directed_vacancy_results.md). Most attempts reject
  disconnected/contact-losing donor replacements. The next separate
  diagnostic computes exact local replacement domains before ranking,
  under the same query/depth/beam/deadline limits. No full C007 run yet.

All preceding cluster runs, including B009 and049, are terminal and quiescent.
Observe existing runs after network loss; never restart because SSH disconnected.
Candidate outputs are evaluated separately. Local proposals operate within one
algorithm; independently generated complete outputs are never pooled.

The [workflow amendment](tracks/workflow.md) requires pre-code hypotheses,
pseudocode, self-critique and cheap falsifiers. Exploration retains isolated
libraries, targeted checks, independent original-edge validation, and every
failure/time. Exhaustive publication audits remain deferred. All findings here
are exploratory; novelty, seed variance and fresh-instance superiority remain
unresolved.
