# 047: fresh MM comparison of the bounded vacancy pipeline

Specified 2026-09-08 while 046 is running, before its quality outcomes are read.
Launch only if 046 demonstrates cumulative Q reductions without unexplained
quality or success regressions. This tests the unchanged candidate, not a new
algorithm, and does not select a configuration separately for each graph.

**Question.** How much of the remaining ACL gap to stock MM does the current
spectral/contact/deletion/vacancy pipeline close, and what is its complete
runtime and failure profile? Older MM comparisons predate several corrections
and refinements. Fresh same-host pairs are necessary to assess the current
implementation; historical MM outputs will not serve as candidate inputs.

```text
freeze unchanged 046 candidate source/configuration and the same 34 inputs
for each input, seed zero, in the audited deterministic paired order:
    run stock MM in its separate environment, with a 60-second deadline
    run the one candidate in the MM/busclique-free environment, same deadline
retain every process result and timing; independently validate original edges
report valid paired Q/ACL, both failure distributions, and all runtime costs
```

Use hyde03 after 046 terminates. Ideal Z12, all 34 readiness structures and
35 memberships; exact source and target bytes remain unchanged. MM receives
the existing stock comparator settings. Candidate is
`native-search-joint1-contacts-spectral-vacancy`, identical to 046 treatment.
The audited harness, dependency guards and validators remain. No new holdout
graphs, parallel algorithm selection, graph-family dispatch or exact solver.

**Self-critique.** One seed cannot estimate seed variance or demonstrate
class-wide superiority. These inputs are heavily exposed development data.
Conditional ACL can look favorable when MM fails on dense cases, so retain the
complete failure table and never credit a late valid output. Same-host serial
pairs reduce host confounding but cannot remove shared-machine variability.
The stage allowance depends on preceding elapsed time and may affect its
search trajectory. A positive comparison would justify additional seeds and
later untouched instances, not a publication claim.

**Cheap falsifier.** This single-seed panel can show that the current fixed
candidate still loses broadly, or that any ACL gain requires excessive runtime.
Report every per-input difference, median and maximum paired timing ratios,
and the count exceeding 10x MM among timely common pairs. Do not replace failed
comparators or hide their time. Use those results to decide the next general
mechanism, not to choose an algorithm by graph family.
