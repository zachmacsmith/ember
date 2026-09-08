# Current A053 versus MM: per-class gaps

Exploratory evidence, 2026-09-08. **A053 does not meet the research objective.**
Its advantage on difficult dense inputs coexists with repeated short-chain
regressions, occasional construction failures and substantial runtime deficits
on inputs where MM is fast. The comparisons below keep those separate.

Three unchanged-policy measurements now cover all 36 Ember class labels:
056 has 34 original structures (35 memberships), four seeds per method on
hyde06; 057 has 35 additional archived records, two seeds on hyde03; 058 has
two audited Sudoku sizes, two seeds on hyde02. King/frustrated share one original
structure, so their original rows are not independent observations. All sources
are exposed development data; excluding exact normalized copies does not prove
different isomorphism classes. No held-out generalization claim follows.

| Cohort | A053 successes | MM successes | Lower / higher Q on common successes | Ties | Solver seconds A053 / MM, all attempts |
|---|---:|---:|---:|---:|---:|
| 056: original, four seeds | 134/136 | 120/136 | 40 / 65 | 13 | 1306.722 / 1870.228 |
| 057: additional, two seeds | 68/70 | 64/70 | 25 / 33 | 4 | 403.471 / 717.732 |
| 058: Sudoku, two sizes | 4/4 | 4/4 | 2 / 1 | 1 | 79.690 / 28.819 |

Of 056's ties, 12 have optimal ACL1 (path/tree/binary tree). Of 057's ties,
two have optimal ACL1 (path). Sudoku's Q25 tie is above a known Q24 witness,
so it is not resolved by the optimal-tie allowance. A053 fails one planted
and one wheel call in056; one hypercube and one wheel call in057. MM has
16 and6 timeouts, respectively. Valid-but-late outputs receive no quality
credit. Successful-only averages are not unconditional expected quality.

The [complete tables](mm_gap_current_tables.md)
show every class and denominator. ACL means and sample variances there use
**the same commonly successful seeds** for each pair of methods. No variance
is estimated from one success. Solver and process means include every attempt,
including failures and actual overruns. Different hosts and interpreter versions
are separate cohorts; there are no cross-host timing ratios. Successful means
over each method's own seed set, all statuses, individual timing ratios and
exact arithmetic remain in the underlying 056/057/058 records linked below.

Among the27 original structures with four common successes, A053 has lower
sample variance in18, equal in4 and higher in5. Among29 additional structures
with two common successes, those counts are15/2/12. A053 nevertheless exceeds
10× MM solver time on44/118 original and20/62 additional common seed pairs;
maxima are27.921× and23.25×. Low variance around excessive ACL does not resolve
a quality gap, and a lower failure-inclusive total runtime does not resolve
these per-instance runtime gaps.

Eighteen class memberships have a positive paired mean ACL gap in both056
and057. Particularly useful repeated deficits are grid (+14.26%, +24.82%),
honeycomb (+19.85%, +22.09%), hardware-native (+28.63%, +26.09%),
kagome (+8.72%, +28.07%), and cycle (+10.91%, +8.42%). Cubic repeats the
sign but changes from +42.28% to +0.52%, illustrating why one representative
does not characterize a class. Remaining repeated deficits are Barabási–Albert,
BCC, frustrated square, generalized Petersen, king, LFR, named graphs,
planted solution, random planar, Shastry–Sutherland, triangular lattice and
wheel. Wheel's comparison is conditional on its surviving candidate seeds.

Binary tree and tree achieve ACL1 throughout both candidate cohorts; MM ties
on the original representatives and has slightly higher means on the additional
ones. These are acceptable quality outcomes with runtime still assessed.
Hypercube's original four-seed mean changes the earlier seed-zero loss to a
small gain, while its additional representative has a candidate failure.
Complete graphs have no timely common MM output in either cohort: report a
success advantage, not a finite paired ACL win. Sudoku is mixed by size:
order2 is 2% worse and order3 is 8.17% better, with higher candidate variance
on both. None of these cases can be collapsed into an all-class win.

## Mechanisms worth testing across several deficits

**Coordinated contact placement is the leading shared hypothesis**, not a
confirmed explanation. Grid, honeycomb, cycle, Petersen, kagome and planted
instances repeatedly retain extra sites despite low MM ACL. One-site transfers
cannot move a sequence of singleton owners, and isolated chain reconstruction
keeps contacts imposed by other owners fixed. Joint ownership changes may
remove several boundaries together. A053's saved cycle accepts all18 available
neutral transfers and uses only3.009M/20M scans: neither rejecting those neutral
moves nor exhausting its global allowance explains that case. A joint path
operator tests whether an already occupied route contains removable overhead.
The fixed six-state gate produces a valid optimal cycle Q148→126 but ties all
five other inputs, so its cycle-plus-another advancement criterion fails.
All557 inspected non-cycle routes fail segment allocation. For the fixed route
and owner order, earliest-ending segments are a complete feasibility test:
inductively they end no later than any feasible partition, leaving at least as
much route for the next owner. Extra prefix sites cannot remove positive contact
coverage. This corrects the proposal's mistaken suggestion that alternate cuts
might rescue those completed queries. The remaining restriction is which route
sites/order and branch contacts are represented, with unvisited routes unknown.
No result from this post-success stage can repair a failed constructor.

**Contact obligations can lock a narrow neighborhood before acceptance is
tested.** B020's fresh contact constructors complete0/9, even though paired
updates reduce overlap more on some inputs. In inspected dense queries, every
selected chain site is still required by an unchanged incident witness.
A compulsory-site lower bound can certify that a query cannot improve overlap
or fixed-price energy. Such equality identifies a neighborhood restriction;
an improving complete proposal rejected by the rule would instead implicate
acceptance. Cost-censored routing without either observation remains unknown.
Releasing all incident bindings of a small connected owner block is the next
general construction hypothesis, contingent on the saved classification.

**Connected ownership and access to unused target sites can constrain
construction.** C007's atomic free-path rule completes only2/8; all640 scored
atomic additions are accepted, yet85.3% of completed addition visits have no
free route. Elementary growth already accepts92.6% of positive growth moves.
These observations disfavor simple growth acceptance as the dominant remedy.
Temporary private fragmentation followed by reconnection can test whether
articulation-site ownership prevents a useful contact-preserving move. Two
saved witnesses establish such extra local reach; both remain incomplete minors,
connected controls also help, and one input lost its result to a driver error.
The next meaningful observation is improved complete-constructor success on a
fixed diverse panel, not another decrease in the number of missing edges.

**Cost and feasibility remain distinct obligations.** Small-ACL inputs often
also have high same-host runtime ratios (e.g. additional grid, honeycomb and
Petersen; Sudoku order2). This is consistent with setup or broad search work
being poorly matched to cheap instances, but wall ratios alone do not attribute
that cost. Separately,057's hypercube stops at failed native conversion, while
its wheel has locally work-censored lifting repair below the global limit.
More postprocessing cannot fix either. Preserved stopping counters distinguish
these from global timeout; a different complete construction must demonstrate
both feasibility and acceptable total cost. There will be no automatic budget
increase or extra repair sequence based only on intermediate metrics.

Prioritize these general mechanisms rather than family-specific dispatch.
Keep A's quality operation, B's overlap-removing constructor and C's disjoint
region constructor independent. A positive local discriminator goes directly
to a bounded complete-constructor screen; a failed screen retires or redesigns
the mechanism. This table is the regression reference, not a training target
for individual graph identities.

[056 audited data](../../results/codex/056-results-review/analysis001/),
[057 report and full tables](../../results/codex/057-results-review/RESULTS.md),
[058 report](experiments/058_results_screen.md),
[057 failure diagnosis](experiments/057_failure_stage_diagnosis.md),
[B020 results](tracks/b_020_results.md),
[C007 results](tracks/c_007_results.md),
[projection inputs](../../results/codex/mm-gap-current-20260908/projection_manifest.json).
The [earlier gap note](mm_gap_by_class.md) remains a historical cohort report.
