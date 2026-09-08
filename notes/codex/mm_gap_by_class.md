# MM gap analysis by graph class — 2026-09-08

**The current retained A053 prototype still has 18 observed ACL deficits.**
Against the frozen seed-zero MM047 reference on the same original inputs,
it has 11 lower-ACL outcomes, 18 higher outcomes, three optimal ACL-one ties
(path, tree, binary tree), and two candidate successes without timely MM
success. A053 succeeds on all 34 inputs. This is a historical quality
comparison, not a fresh A053/MM timing experiment. All rows remain visible;
dense gains do not compensate for a class deficit.

Evidence has three separate scopes. [047](experiments/047_results_screen.md)
is the latest fresh same-host MM comparison, using older A046: 34/34 versus
32/34 successes and 11 wins, 19 losses, two optimal ties on common successes.
[053](experiments/053_results_screen.md) measures the current retained reduced
prototype at one seed against A050, with no fresh MM arm.
[032](experiments/032_results_review.md) has four seeds for still older A026;
its variability cannot be assigned to A053. All are exposed development
instances: one source per family membership, with one shared king/frustrated
structure. Seeds do not supply new source instances. No family-population
mean, seed robustness of A053, or held-out generalization is established.

The table shows successful-call ACL; with one seed it is a single observation,
not an estimated class mean. A053 success is 1/1 in every row. A missing MM
ACL is a timeout, never zero. The complete graph's late valid MM result and
the spin-glass timeout remain uncredited. King/frustrated rows share one
structure and count once in totals. The separate corrected Sudoku supplement
has no A053 observation yet.

| Class | MM047 success / 1 | MM047 ACL | A053 ACL | ΔQ | Decision gap |
|---|---:|---:|---:|---:|---|
| barabasi_albert | 1 | 3.3607 | 3.4754 | +14 | loss |
| bcc_lattice | 1 | 1.2637 | 1.4505 | +17 | loss |
| binary_tree | 1 | 1.0000 | 1.0000 | +0 | optimal tie |
| bipartite | 1 | 6.1587 | 4.4921 | -210 | win |
| circulant | 1 | 1.4627 | 1.4403 | -3 | win |
| complete | 0 | — | 9.2913 | — | mm timeout |
| cubic_lattice | 1 | 1.4960 | 2.0640 | +71 | loss |
| cycle | 1 | 1.0000 | 1.1746 | +22 | loss |
| frustrated_square | 1 | 1.4132 | 1.8760 | +56 | loss |
| generalized_petersen | 1 | 1.3095 | 1.3810 | +9 | loss |
| grid | 1 | 1.0469 | 1.3047 | +33 | loss |
| hardware_native | 1 | 1.4609 | 1.9375 | +61 | loss |
| honeycomb | 1 | 1.0316 | 1.2789 | +47 | loss |
| hypercube | 1 | 3.2969 | 3.5312 | +30 | loss |
| johnson | 1 | 9.8750 | 6.9750 | -348 | win |
| kagome | 1 | 1.2214 | 1.3206 | +13 | loss |
| king_graph | 1 | 1.4132 | 1.8760 | +56 | loss |
| kneser | 1 | 2.8968 | 3.2460 | +44 | loss |
| lfr_benchmark | 1 | 1.6000 | 1.7000 | +10 | loss |
| named_special | 1 | 1.0000 | 1.2609 | +12 | loss |
| path | 1 | 1.0000 | 1.0000 | +0 | optimal tie |
| planted_solution | 1 | 1.0226 | 1.1880 | +22 | loss |
| random_er | 1 | 7.8496 | 6.6241 | -163 | win |
| random_planar | 1 | 1.8487 | 1.7105 | -21 | win |
| regular | 1 | 15.1000 | 9.2929 | -813 | win |
| sbm | 1 | 5.3167 | 4.7667 | -66 | win |
| shastry_sutherland | 1 | 1.2149 | 1.3471 | +16 | loss |
| spin_glass | 0 | — | 11.4688 | — | mm timeout |
| star | 1 | 1.1339 | 1.0787 | -7 | win |
| tree | 1 | 1.0000 | 1.0000 | +0 | optimal tie |
| triangular_lattice | 1 | 2.0859 | 2.1484 | +8 | loss |
| turan | 1 | 8.8111 | 5.1111 | -333 | win |
| watts_strogatz | 1 | 13.7931 | 9.7356 | -706 | win |
| weak_strong_cluster | 1 | 3.6797 | 3.3281 | -45 | win |
| wheel | 1 | 1.1575 | 1.4724 | +40 | loss |

The full [quality CSV](../../results/codex/mm-gap-20260908/current_quality_by_class.csv)
retains graph IDs, status denominators, exact Q differences and missing
current-variance fields. The [runtime CSV](../../results/codex/mm-gap-20260908/paired_runtime_by_class.csv)
separates all 35 class memberships: fresh A046/MM047 solver and process times,
paired ratios, and A053 absolute times. It deliberately leaves A053/MM ratios
missing because those arms were not contemporaneous. No different-host or
cross-version timing ratio is constructed.

**Runtime is a separate deficit.** Fresh047 median solver ratio is 10.332;
16/32 timely pairs exceed 10×. Median process ratio is 7.685, with 8/32 above
10×. The worst solver ratios are tree 30.30×, binary tree 29.76×, cycle 23.85×,
path 23.76× and planted solution 22.76×. Larger dense MM calls make aggregate
candidate seconds look favorable while many small-input calls remain slower.
Fixed preparation/search work and fresh-process compilation are plausible
contributors, but these timings alone do not apportion them. Current A053's
runtime and seed variability require fresh replication rather than importing
those older ratios. Hyde06's isolated environments are prepared for that
measurement; this report contains no results from it.

**Across-seed variability remains version-specific.** The following is the
older032 evidence only. Both mean and sample variance use each method's
successful seeds; A026 succeeds 4/4 throughout, MM denominators are shown.
Variance uses k−1 and is undefined for fewer than two successes. Missing
seeds are not imputed. For unequal success sets, compare means only on matched
successful seeds, available in the [variability CSV](../../results/codex/mm-gap-20260908/older_variability_by_class.csv).
This is variability of ACL across solver seeds, not variance of chain lengths
inside one embedding. A053's current across-seed variance is unknown for every
class, not zero.

| Class | MM032 success / 4 | MM mean ACL / s² | Older A026 mean ACL / s² |
|---|---:|---:|---:|
| barabasi_albert | 4 | 3.40369 / 0.0195008 | 3.56148 / 0.00674102 |
| bcc_lattice | 4 | 1.2967 / 0.0189188 | 1.58516 / 0.00622912 |
| binary_tree | 4 | 1 / 0 | 1.08071 / 0.000511501 |
| bipartite | 2 | 7.4881 / 0.000787352 | 4.49206 / 0 |
| circulant | 4 | 1.50746 / 0.00137373 | 1.48321 / 0.000533712 |
| complete | 0 | — / — | 9.29528 / 2.06667e-05 |
| cubic_lattice | 4 | 1.386 / 0.006416 | 1.864 / 0.013056 |
| cycle | 4 | 1 / 0 | 1 / 0 |
| frustrated_square | 4 | 1.50207 / 0.00520798 | 1.95868 / 0.000591945 |
| generalized_petersen | 4 | 1.3373 / 0.0207651 | 1.67659 / 0.00232531 |
| grid | 4 | 1.08203 / 0.00311279 | 1.36914 / 0.00530497 |
| hardware_native | 4 | 1.45312 / 0.00854492 | 1.89648 / 0.00554911 |
| honeycomb | 4 | 1.04737 / 0.0012373 | 1.44211 / 0.00120037 |
| hypercube | 4 | 3.10156 / 0.0241292 | 3.09961 / 0.115779 |
| johnson | 4 | 9.16875 / 0.570619 | 7.03542 / 0.00760995 |
| kagome | 4 | 1.16031 / 0.00252511 | 1.25191 / 0.000582717 |
| king_graph | 4 | 1.50207 / 0.00520798 | 1.95868 / 0.000591945 |
| kneser | 4 | 3.04762 / 0.0188964 | 3.43651 / 0.00407323 |
| lfr_benchmark | 4 | 1.665 / 0.0552333 | 1.8925 / 0.00449167 |
| named_special | 4 | 1.03804 / 0.00263863 | 1.09239 / 0.000748267 |
| path | 4 | 1 / 0 | 1 / 0 |
| planted_solution | 4 | 1.0188 / 1.88441e-05 | 1.11466 / 0.000240262 |
| random_er | 4 | 7.69173 / 0.330526 | 6.48872 / 0.0278516 |
| random_planar | 4 | 1.71711 / 0.0184384 | 2.03783 / 0.00255006 |
| regular | 2 | 15.8143 / 1.02041 | 9.30893 / 0.00106718 |
| sbm | 4 | 5.45 / 0.0664352 | 5.125 / 0.00550926 |
| shastry_sutherland | 4 | 1.25826 / 0.00671061 | 1.37397 / 0.0146791 |
| spin_glass | 0 | — / — | 11.4656 / 1.30208e-05 |
| star | 4 | 1.12992 / 0.000227334 | 1.07677 / 1.55e-05 |
| tree | 4 | 1 / 0 | 1.10331 / 6.83013e-05 |
| triangular_lattice | 4 | 1.91797 / 0.0457967 | 2.36523 / 0.00689189 |
| turan | 3 | 7.42593 / 1.44572 | 5.90278 / 0.287521 |
| watts_strogatz | 3 | 13.3161 / 0.224832 | 9.70546 / 0.0133081 |
| weak_strong_cluster | 4 | 3.68359 / 0.0051473 | 3.36328 / 0.00148519 |
| wheel | 4 | 1.16732 / 0.000924835 | 1.54134 / 0.00121417 |

On the 28 fully observed032 structures, A026 has seven lower means, 19 higher
means and two optimal ties; its macro ACL is 1.74% worse. Including the four
partially successful MM structures reverses the aggregate to 12.50% lower on
common seeds. This demonstrates why success conditioning and dense gains must
remain visible. Lower sample variance on 18 of the 28 structures does not
resolve their mean-ACL deficits; four seeds are only exploratory evidence.

**Sudoku coverage:** [029](experiments/029_results_review.md) separately has two
corrected development inputs, orders2/3 with16/81 vertices, seed0. MM uses
25/408 Q, the fixed contacts candidate24/405, and the fixed spectral candidate
25/394. Every call succeeds. Each method is separate; selecting their better
output is forbidden. The spectral order2 tie is not certified optimal because
the contacts witness is smaller. No A053 or across-seed result exists here.
These two inputs should enter a separate provenance-preserving current-policy
screen; they are not silently folded into the34-input readiness cohort.

**Structural priorities and discriminating observations**

1. **Compact contact placement and movement before feasibility.** Large current
   deficits include cubic+37.97%, king/frustrated+32.75%, hardware-native+32.62%,
   wheel+27.21%, named-special+26.09%, grid+24.63% and honeycomb+23.98%. These
   sources differ in degree, but all reference embeddings have short chains.
   The shared hypothesis is that early placement or retained ownership makes
   compact contacts hard to reach. This is an inference, not an identification
   from class names. B019 tests mutable coupler contacts with temporary overlap;
   C's fresh constructor tests variable occupied size and disjoint-region moves.
   Record complete candidate feasibility/Q and which proposed changes existed,
   were eligible, were accepted, or were interrupted. A discovered compact
   proposal rejected by acceptance implicates acceptance; a bounded exhaustive
   local diagnostic proving none exists implicates that neighborhood, not global
   impossibility. Query-cap prefixes without complete proposals implicate cost
   before they diagnose a local optimum.
2. **Reduction demands versus lifting restrictions.** A054's minor-preserving
   degree-two core still worsened final Q on seven of13 changed inputs. Its
   lower lifting excess and higher core excess are descriptive, not causal.
   A055 holds core/lifting policies fixed and changes only eligible source
   reductions, then tests every changed structure in a complete constructor.
   In contrast, cycle's A053 Q148 versus the known valid Q126 demonstrates that
   a cheap core is insufficient; expansion order or available owner moves may
   prevent closure without growth. That needs its own discriminating evidence,
   not another claim that fewer fill edges will solve every deficit. For a
   minor-preserving core, projecting an existing full-source valid embedding
   through the reduction certificate can optionally demonstrate a cheaper
   representable core without running or seeding a candidate from MM. It would
   separate representation capacity from the heuristic's achieved core Q.
3. **Acceptance barriers versus unavailable moves.** C's routing guard held at
   all446 commits yet completed none of8 inputs;11,917 cut rejections were due
   to unused connectivity/emptiness. This rejects that constrained fixed-path
   policy. It does not show that its starts have no feasible route. The new C
   constructor removes that restriction and changes initialization, so those
   effects are initially confounded. A promising complete-constructor result
   should receive one controlled initialization/move or acceptance ablation,
   not a chain of repairs selected by falling missing-edge counts. B019 should
   similarly distinguish unchanged overlap due to pool exhaustion, rejected
   energy changes or unfinished queries before any refinement.
4. **Cost that exceeds useful search.** Prioritize measured setup, distance-cache
   rebuild and proposal counts on the same full-constructor cases. If complete
   eligible proposals improve embeddings but few fit the deadline, optimize
   their implementation or reuse prepared state. If a cheap completed finite
   neighborhood has no progress, merely raising time is poorly motivated. A
   separate warm-cache experiment can attribute compilation overhead, but the
   standard cold end-to-end timings remain charged and reported.

These are analysis groups, never algorithm dispatch rules. Low maximum degree
alone does not explain all losses: wheel has a degree126 hub while most of its
vertices have degree3, and hardware-native has no degree≤3 vertex. The saved
[structural measurements](../../results/codex/mm-gap-20260908/structural_features.csv)
make those distinctions explicit. The next priority is a mechanism that improves
several short-chain deficits while retaining dense success, not an aggregate
score or an instance-specific exception.

**Milestone decision:** retire A054 as a replacement and the fixed access-guard
routing policy; retain A053 provisionally while testing A055's narrow structural
claim. Advance B019 and C's new representation directly through their four
small complete-constructor falsifiers, then a diverse fixed screen if warranted.
No current candidate has demonstrated generalization beyond exposed sources.
Current-policy seed replication addresses measurement uncertainty; it is a
baseline experiment within track A, not a fourth algorithm or a portfolio.

The [analysis script and input manifest](../../results/codex/mm-gap-20260908/manifest.json)
bind already audited records. The script checks source/target/seed identity,
recomputes all Q/n and exact rational seed variances, and preserves all272 old
seed outcomes. It invokes no constructor, graph generator, MM or new validator.
