# Constructor mechanism decisions: A062, B024 and C010

Exploration, 2026-09-09. All **79 fixed calls** completed on three hosts, each
with fresh same-host MM. All three saved-data analyses passed independent
validation. **No candidate passes its continuation rule.** Each policy remains
separate; selecting successes across them would be a prohibited portfolio.

| Track and hypothesis | Complete outcomes | Decision |
|---|---|---|
| A062: prioritize ready insertions with few direct singleton sites | 10/12 valid, unchanged control 9/12, MM 12/12; two recoveries, one lost success; wheel/grid quality regressions | Retire this priority; retain the measured branch control |
| B024: improve the initial assignment on the same target sites | 4/9 valid, control 6/9, MM 8/9; one inherited MM Q win | Retire this initializer |
| C010: grow an auxiliary source-clone graph when placement conflicts arise | 2/8 valid, MM 6/8; two optimal ACL1 ties; six work-limited failures | Retire the fixed work-limited policy; construction reach remains censored |

**A — ordering affects reach, but this priority is insufficient.**
[All 36 calls and class metrics](experiments/062_ready_lifting_results.md)
show that ready order recovered planted seed1 and wheel seed1 while losing
planted seed0. It changed order in every one of ten lifting calls. All 924
selection records completed, so incomplete scoring does not explain the result.
The new planted failure exhausts the existing local repair allowance, with a
valid partial minor and substantial global budget remaining; this does not
certify physical infeasibility. Both hypercube seed1 calls fail in the unchanged
native core before scheduling.

On eight common successes, final Q decreases by only six: base Q improves by
27 but the resulting maps allow 21 fewer sites to be removed by the unchanged
branch stage. Wheel worsens by six on its sole common seed; grid mean worsens
by one; honeycomb improves by seven. Both cycles remain optimal. Scheduler
wall costs 22.136 seconds inside the 127.037-second treatment solver total,
versus 102.856 for the control and 53.143 for MM. All attempts are included.
Ready still loses seven common MM quality comparisons, wins one, ties two
optimally, and fails two calls MM solves. Its grid ACL variance increases;
lower honeycomb variance still exceeds MM's. A lower partial/base Q alone
would have overstated the gain.

**B — improved initialization proxies do not establish improved construction.**
[All 27 calls](tracks/b_024_results.md) show that every nonclique starts with
both lower total target distance and fewer missing contacts, yet WS and grid
lose successful completion. Four sparse failures complete eight passes with
residual missing contacts and no overlap; their actions are uninterrupted.
All 2,754 completed route/erasure winners are accepted, including 545 energy
increases. This rules out strict-energy rejection as the current failure mode,
but leaves restricted moves and forced repair decisions coupled. K100 instead
pays 7.39 seconds for an invariant placement objective and hits the deadline.
Failure-inclusive solver totals are 67.501/86.814/53.575 seconds for B024,
control and MM. Fewer successes prevent calling the lower total a speed win.

**C — charged work and computational time must be distinguished.**
[All 16 calls](tracks/c_010_results.md) show optimal path/tree embeddings,
without splitting. Every other input stops at nineteen million charged units
after only 0.318–0.653 seconds of a fifteen-second allowance. Setup is 45.4%
of charged work but 22.2% of solver wall, so neither expensive preprocessing
alone nor poor wall-time scaling follows. Completed evidence includes 131
failed and six committed revisions, plus 300 committed splits. These expose
local limitations but do not resolve global reach. All-attempt solver totals
are 3.375 seconds versus MM's 46.474, including two late MM results; unequal
coverage prevents a speed claim.

## Gaps and next discriminating observations

The [all-class gap analysis](mm_gap_current_replications.md) and
[72 class/size rows](mm_gap_current_tables.md) remain the replicated reference
for success, paired mean ACL, sample variance and failure-inclusive runtime.
They cover all 36 labels. Eighteen memberships had worse paired mean ACL in
both development cohorts. These new policies are never pooled into that
baseline. This cycle's repeated exposed inputs provide mechanism evidence,
not held-out generalization or an all-class improvement. One-seed B/C screens
cannot estimate across-seed variance.

Several sparse deficits still plausibly share poorly coordinated physical
contacts. A's order intervention changes outcomes; B's distance intervention
does not yield general end-to-end gains. Neither observation establishes that
one cause explains every class. Dense/hypercube gains cannot cancel sparse
regressions or construction failures.

Three independent tracks continue. A's next task is a narrow diagnosis using
saved traces to distinguish the singleton-count proxy, physical move limits
and scheduling cost; another priority key or repair cap is not justified.
[B025](tracks/b_025_acceptance_discriminator.md) isolates acceptance by keeping
B023's generators, prices and schedule but retaining the incumbent when the
selected winner raises current-price energy. Its critique explicitly shows
that this can block necessary growth. [C011's controlled ablation](tracks/c_010_wall_budget_diagnostic_proposal.md)
keeps C010's placement/splitting choices and wall deadline while counting,
instead of denying, work above the old thresholds. Additional timely complete
embeddings distinguish unused runtime from an ineffective neighborhood;
smaller missing-edge counts do not. Both have approved before-code designs
and fixed small complete-constructor screens. No automatic tuning or portfolio
selection follows. The research objective remains unmet.
