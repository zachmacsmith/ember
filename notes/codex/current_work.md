# Current research checkpoint

Updated 2026-09-08 20:25 UTC. Branch `codex`. Goal active and unmet: one
general non-portfolio algorithm, no MM/busclique, ideal Z12, competitive mean
ACL and roughly MM-scale runtime. No new final-test inputs have been exposed.

- **A / literature / hyde03:** Keep048 cyclic continuation as the overall
  development baseline. A050's blocked-only reconstruction restores34/34
  coverage from049's32/34, with exact Q ties on all32 common successes.
  The two successful repairs consume0.138s; total solver wall increases
  179.16→185.53s, including the two completed expansions. Historical quality
  against048 still slightly trails:14,866 versus14,858Q, macroACL3.298135
  versus3.290160. [Results](experiments/050_results_screen.md).
  Literal original-only physical requirements (A051) pass five correctness
  groups but fail the fixed four-case reach gate: cycle stops at119/126
  vertices with20M scans. Star ties, wheel/subdivision worsen. Reject this
  policy before a corpus run. [Lesson](original_requirements_implementation.md).
  A052 is a separate soft spatial-guidance design, not implemented yet.
- **B / algorithm_audit / hyde02:** B011 port-aware paths recover one saved
  ER step but still complete6/9, with all six Q totals exactly matchingB009.
  ER blocks at the next vertex; both dense partial prefixes worsen.
  Reject promotion. [Results](tracks/b_011_results.md). B012 now implements
  blocked-only release/reconstruction from the fixedB011 ancestor: at most
  two released owners, every outside chain frozen, unchanged global and
  nested limits. Two fixed local reach calls precede any panel decision.
  [Pre-code policy](tracks/b_blocked_reconstruction.md).
- **C / benchmark_audit / hyde04:** Exact donor replacement domains repair
  3/25 supplied missing-edge queries versus2 previously, with no whole-source
  completion. [Results](tracks/c_directed_vacancy_domain_results.md).
  Classification of all2,747 saved admissible pairs rules out an overlooked
  one-exchange repair in the failed queries' recorded domains.
  [Evidence](tracks/c_domain_access_results.md). Strict component-separation
  descent still repairs only the same3/25. None of its217 noncertifying
  proposals progress, so no second-depth state is entered. Positive gap1 is
  impossible under this region definition; gap2 usually demands immediate
  connection. Reject this policy. A separate bounded neutral-continuation
  design is next; no full C007 constructor or MM run has been requested.

All preceding cluster runs, including050 andB011, are terminal, quiescent and
retrieved. Observe existing runs after network loss; never restart because
SSH disconnected. Candidate outputs are evaluated separately. Local proposals
operate within one algorithm; complete outputs are never pooled.

The [workflow amendment](tracks/workflow.md) requires pre-code hypotheses,
pseudocode, self-critique and cheap falsifiers. Exploration retains isolated
libraries, targeted checks, independent original-edge validation, and every
failure/time. Exhaustive publication audits remain deferred. All findings here
are exploratory; novelty, seed variance and fresh-instance superiority remain
unresolved. The latest fresh-MM baseline screen has11wins,19losses and2ties
on32 common timely inputs; its lower macro ACL does not establish all-class
superiority, and the median solver ratio is10.33.
