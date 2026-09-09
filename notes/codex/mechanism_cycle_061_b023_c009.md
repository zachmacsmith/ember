# Constructor decisions after 136 calls

2026-09-09. Ideal Z12, exposed development inputs, separate algorithms and fresh
same-host MM comparisons. Every planned call is terminal and retained. All three
saved independent analyses pass; none reruns a constructor. The research goal
remains unmet.

| Mechanism | Complete outputs | End-to-end quality | Decision |
|---|---|---|---|
| A061: unchanged branch-preserving path reconstruction | 34/34, A053 34/34, MM 29/34 | Six improvements and 28 ties against A053; versus MM, eight wins, 17 losses, four optimal ACL-1 ties and five MM timeouts | Retain the measured stage; prioritize construction next |
| B023: permit temporary contact loss and overlap | 6/9, MM 8/9 | One common Q win, five losses; misses seven-success/three-win-or-tie rule | Retire fixed policy |
| C009: finite connected-chain domains and approximate coordination | 0/8, MM 6/8 | No valid candidate output; ACL comparison undefined | Retire fixed policy |

A's frozen breadth gate passes with exactly two new noncycle improvements:
named-special Q58→53 and honeycomb Q243→241. The other improvements are cycle,
kagome, grid and Petersen. All 40 saved qubits come from 13 committed moves;
every wrapper base Q matches fresh A053. Both candidates return all 34 seed-0
inputs without a Q regression. This extends observed reach to two more
structures; it does not establish class-population or seed-variance improvement.
The prior planted/wheel/hypercube seed failures remain unresolved.

The MM comparison illustrates why aggregate quality is insufficient. On 29
common successes the new candidate's macro mean ACL is 2.4633 versus MM 2.6496,
yet it loses on 17 inputs. Grid remains Q163 versus 134, honeycomb 241 versus
196, and the newly improved named-special input 53 versus MM's optimal 46.
The per-class baseline and its replicated variance estimates remain separate
from this one-seed candidate version. Dense gains cannot discharge these losses.

B shows that temporary contact loss can occur on a trajectory that finishes
valid: every one of its six successes contains loss followed by restoration.
That does not isolate the transition's causal benefit from its other changes.
The four sparse successes still use 2.04–3.26 times MM's Q after final cleanup.
Only one of 2,868 route/erasure actions is interrupted; strict energy rejection
does not occur. ER and king finish all eight passes with previously lost contacts
still missing. This implicates placement, available moves or disruptive forced
acceptance rather than a general primitive-interruption explanation. These
causes remain confounded; another local repair is not justified by partial counts.

C spends 74.7% of its solver time generating domains. Five inputs never publish
a non-singleton replacement library before the search-work cap. Path/tree/grid
do publish replacements and remain invalid. Pairwise support in path's final
library cannot distinguish globally incompatible alternatives from a poor joint
selection. Merely increasing domain size or work would not resolve that causal
ambiguity. Keep the computational evidence and redesign construction.

Failure-inclusive solver totals: A053 336.854 / A061 333.695 / MM 442.332 seconds
on 06; B023 84.011 / MM 66.195 on 02; C009 33.455 / MM 46.542 on 03. A's stage
itself costs 5.679 seconds plus final validation; its slightly lower measured
total than A053 is not a demonstrated speedup. Twelve of its 29 common MM
solver ratios exceed ten. B's common median ratio is 4.03; C has no common
valid ratio. Failed or late returns remain in all time totals.

Three next directions remain separate and design-only until their mechanisms
and cheap falsifiers are reviewed: construction constraints in A, final chain
cost and coordinated placement in B, and cheaper compatible construction states
in C. Any implementation requires hypothesis, pseudocode and self-critique first.
No domain, route, pass, price or work-cap rescue is inferred from these results.

[Replicated class gap analysis](mm_gap_current_replications.md),
[all baseline class/size rows](mm_gap_current_tables.md),
[A061 saved results](../../results/codex/061-results-review/analysis001/summary.json),
[B023 results](tracks/b_023_results.md), [C009 results](tracks/c_009_results.md).
