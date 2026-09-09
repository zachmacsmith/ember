# A061 passes the fixed breadth gate

The one approved saved analysis passes with zero errors. A053 and branched path
each return 34/34 timely original-valid embeddings; MM succeeds 29/34 and times
out on five. Branched path improves six inputs and ties 28, with **no individual
Q regression or lost A053 success**. Its two new noncycle gains are named-special
37761 (58→53Q) and honeycomb 32367 (243→241Q), satisfying the exact breadth rule.
Both still lose to MM. This is observed per-input non-regression on 34 exposed
structures, not a class-population guarantee or a claim based only on means.

Total Q 14797→14757 (−40), macroACL3.278605→3.267446. Every wrapper base Q equals
fresh A053, so the full 40 Q gain belongs to the added stage. Thirteen certificates
were admitted. The remaining four gains repeat cycle (−22 Q), kagome (−4), grid (−4)
and Petersen (−3). The stage used 9,518,834 units, including 305,972 branch units;
its final wrapper gate adds 3,914,616 units, for 13,433,450 total added units.
Stage/gate wall totals are 5.6791/1.0986 s. All failed proposals and capped searches
are retained: 2303 attempts, 2155 insufficient suffixes, 132 no-strict-gain,
three side-contact rejections and 13 commits; 52 path attempt limits remain.

Two stage work stops retain the unmodified valid base: complete 1041 stops during
path generation; spin-glass 37302 stops while revalidating entry, before planning
a path. The latter initial certificate is explicitly incomplete; no proposal
is published, and the wrapper's independent final validation completes. Both
calls are timely and credited, without treating their unvisited alternatives
as negative mechanism evidence. The other 32 stages finish. No allowance or
route policy changed after outcomes.

All 35 class memberships follow; frustrated-square/king 32616 is one physical
input and contributes only once to 34-input totals. Positive Branch−MM means
MM has lower Q. Every number is a successful original-valid output; all five
MM timeouts remain explicit.

| Class/input | A053 Q | Branch Q | Fresh MM Q/status | Branch−A053 | Branch−MM |
|---|---:|---:|---:|---:|---:|
| watts strogatz 22972 | 1694 | 1694 | 2400 | +0 | -706 |
| star 2229 | 137 | 137 | 144 | +0 | -7 |
| hypercube 4755 | 452 | 452 | 422 | +0 | +30 |
| random planar 31536 | 260 | 260 | 281 | +0 | -21 |
| johnson 5242 | 837 | 837 | 1185 | +0 | -348 |
| planted solution 34404 | 158 | 158 | 136 | +0 | +22 |
| random er 6450 | 881 | 881 | 1044 | +0 | -163 |
| weak strong cluster 33587 | 426 | 426 | 471 | +0 | -45 |
| barabasi albert 10662 | 424 | 424 | 410 | +0 | +14 |
| bcc lattice 33402 | 132 | 132 | 115 | +0 | +17 |
| circulant 3499 | 193 | 193 | 196 | +0 | -3 |
| path 2030 | 141 | 141 | 141 | +0 | +0 |
| named special 37761 | 58 | 53 | 46 | -5 | +7 |
| kagome 32122 | 173 | 169 | 160 | -4 | +9 |
| grid 1584 | 167 | 163 | 134 | -4 | +29 |
| turan 3060 | 460 | 460 | TIMEOUT | +0 | undefined |
| lfr benchmark 31357 | 170 | 170 | 160 | +0 | +10 |
| complete 1041 | 1180 | 1180 | TIMEOUT | +0 | undefined |
| cycle 1829 | 148 | 126 | 126 | -22 | +0 |
| bipartite 1363 | 566 | 566 | TIMEOUT | +0 | undefined |
| generalized petersen 4083 | 174 | 171 | 165 | -3 | +6 |
| regular 14334 | 1301 | 1301 | TIMEOUT | +0 | undefined |
| wheel 2429 | 187 | 187 | 147 | +0 | +40 |
| kneser 5411 | 409 | 409 | 365 | +0 | +44 |
| hardware native 37603 | 248 | 248 | 187 | +0 | +61 |
| frustrated square 32816 | 227 | 227 | 171 | +0 | +56 |
| king graph 32616 | 227 | 227 | 171 | +0 | +56 |
| tree 5058 | 121 | 121 | 121 | +0 | +0 |
| sbm 30736 | 572 | 572 | 638 | +0 | -66 |
| binary tree 4905 | 127 | 127 | 127 | +0 | +0 |
| honeycomb 32367 | 243 | 241 | 196 | -2 | +45 |
| shastry sutherland 33018 | 163 | 163 | 147 | +0 | +16 |
| cubic lattice 33219 | 258 | 258 | 187 | +0 | +71 |
| triangular lattice 31879 | 275 | 275 | 267 | +0 | +8 |
| spin glass 37302 | 1835 | 1835 | TIMEOUT | +0 | undefined |

On the 29 common successes, branched path wins 8, loses 17 and ties 4 at optimal
ACL 1 (path, cycle, tree, binary tree). Its paired macroACL is 2.463346 versus
MM 2.649578, with 874 fewer Q in total; these favorable means coexist with the
listed 17 losses. A053 has 8 wins/18 losses/3 optimal ties on the same29 inputs.
MM's own 29-success mean must not be compared as a paired mean to candidate's
34-success mean. Five candidate-only successes are turan, complete, bipartite,
regular and spin-glass. No historical MM output is pooled into these comparisons.

Same-host all-attempt solver totals A053/branch/MM are 336.854/333.695/442.332s;
CPU totals 336.699/333.513/442.206s and process totals 404.921/401.233/462.841s.
The slightly lower branch total is a fresh-call timing observation, not proof
that adding the stage speeds the inherited constructor. No branch/A053 time
ratio exceeds 10. Branch exceeds 10×MM solver time on 12 inputs and process time
on five, despite the overall total benefiting from MM's five timeouts.
On the 29 common successes, solver totals are 246.334/243.955/120.287s and
process totals 305.032/302.037/137.454s: both candidate arms cost more than MM
on this paired set. No failure time has been removed from the all-attempt totals.
[All 102 rows](../../../results/codex/061-results-review/all102.csv) and
[all class ACL/time ratios](../../../results/codex/061-results-review/class_metrics.md)
retain CPU, process costs, failures and denominators.

| >10×MM rows | Rows | Inherited A053 s | Core s | Layout inside core s (known rows) | Expansion s | Branch s | Final gate s |
|---|---:|---:|---:|---:|---:|---:|---:|
| A053 | 12 | 98.282 | 78.346 | 62.653 (11/12) | 17.942 | — | — |
| Branch | 12 | 95.980 | 77.437 | 62.266 (11/12) | 16.657 | 1.173 | 0.035 |

Core/layout timers are nested, and inherited validation overlaps stage timers;
they cannot be added as independent costs. Unassigned core time is not labeled
JIT. [Saved scalar receipts](../../../results/codex/061-results-review/over10x_cost_scalars.csv)
place most of the slow-row cost upstream of this small stage, without explaining
the cause of a quality deficit.

Decision: retain the unchanged branched variant within measured development
scope; the fixed gate passes, while MM/class/runtime gaps remain. This single
seed provides **no across-seed variance estimate**; reported within-chain
variance describes chains within one result. A060's planted seed1 lifting
failure and A057's wheel lifting/hypercube native-core failures remain unchanged
historical evidence, outside this complete-output stage's reach. No solver
repeat, profiling, trace expansion, route/cap tuning or source change followed.
The global branch-set representation already permits MM's embeddings; retained
branches expand the local proposal's representation, not global minor capacity.
A separate design-only construction hypothesis follows, rather than another
shortening-stage refinement.
