# Equal-size contact rearrangement

Design and self-critique recorded before implementation. This is a research
configuration of the same evolving contact-reconstruction heuristic. No other
constructor, MM embedding, graph-family dispatch, or exact solver is involved.

The current move accepts only a strict reduction in selected physical qubits.
Consequently it cannot accept a contact rearrangement that keeps total size
unchanged but makes later shortening possible. Revision 016 improves group
coverage while leaving that restriction intact. This is a hypothesized mechanism;
there is no measured improvement from equal-size moves yet.

For a valid embedding C, let c(u,v) be the number of actual physical couplers
between chains C[u] and C[v] for a logical edge (u,v). Define redundancy
R(C) = sum over logical edges of (c(u,v)-1). Optimize the lexicographic objective
(total assigned qubits, -R). All logical contacts, chain connectivity, disjointness,
and frozen ownership remain hard constraints. Extra contacts between nonadjacent
logical vertices do not contribute. The secondary objective rewards interchangeable
edge witnesses; it is a heuristic proxy for future shortening, not a bound on it.

For one group, allow generated complete proposals up to its current size. After
full original-graph validation, accept a smaller group or an equal-size group
whose incident logical edges have strictly greater redundancy. Edges outside the
selected group are unchanged, so the incident-edge delta equals the global delta.
Accepting equal size requires a strict integer redundancy increase, preventing
cycles at a fixed total size. Existing group, region, search-work and deadline
caps still bound a run. Count equal-size accepted moves separately from actual
qubits saved. Later smaller moves may lower redundancy; the primary objective
still decreases. Return the final valid incumbent.

Self-critique: redundant couplers need not permit a removable qubit, and maximizing
them could trap chains in tightly occupied areas. Counting them has nontrivial
overhead. A width-one prefix search may seldom propose helpful rearrangements;
changing acceptance alone does not establish adequate exploration. The mechanism
resembles established secondary-objective local search and is not by itself a
novelty claim. A strict lexicographic objective also forbids temporary worsening
of redundancy that might be necessary. More accepted moves are not evidence of
better quality, and this research arm must not be selected per graph.

First validate the objective against direct coupler enumeration and a small
mechanism fixture where equal-size relocation increases contact redundancy while
strict shortening cannot move. Verify all actual embeddings independently, input
preservation, and that repeated moves strictly decrease the declared objective.
Then compare fixed strict and redundancy configurations on the same 18 independent
011 search incumbents, using the revision-016 sites/groups settings and unchanged
budgets. Report final qubits, equal-size moves, charged work, total timing, and
regressions. Reject or defer this direction if extra rearrangements produce no
useful reductions at comparable time/work. Do not combine it with the separate
partial-tree proposal change before its independent effect is measured.

Implementation passes 37 focused contact/review tests. The mechanism fixture
requires a two-qubit chain under the fixed external contacts; the revised policy
relocates it without changing size and increases its actual incident coupler
redundancy by two, while strict shortening does not move. This establishes the
acceptance mechanism only, not later chain savings.

The diagnostic is frozen in `results/codex/022-contact-redundancy` with source
snapshot `544a8a671b51ad53f0cafe57b23edf88089b72b13b9b22f081f6245202f57a3f`.
It contains 54 calls: an 18-case legacy replay gate followed by the 18 strict
sites/groups controls and 18 equal-size redundancy calls. Every call uses a fresh
isolated MM-free process. Whole-target edge enumeration independently verifies
the total redundancy delta outside measured refinement time. Both strict replay
sets must match their saved 011/016 counterparts before effects are interpreted.

```sh
.venv/bin/python scripts/codex/refinement_ablation.py prepare results/codex/022-contact-redundancy --experiment contact-redundancy
.venv/bin/python scripts/codex/refinement_ablation.py run results/codex/022-contact-redundancy
```

All 54 calls completed successfully and passed original-graph validation,
dependency guards, work/deadline checks, and trajectory arithmetic. All 36 old
legacy/sites-groups outputs reproduce their saved embeddings exactly. Against
the strict sites/groups control, the redundancy policy saves 25 more qubits:
nine lower-qubit results, seven ties, two regressions. Its mean ACL over these
18 observations is 2.645448 versus 2.664248. It accepts 260 equal-size moves.
The two regressions are complete40 seed1 and regular80 seed0. No sparse-input
mean advantage over MM is established by this result.

Measured refinement totals are 48.3616 seconds for redundancy versus 16.1826
for strict sites/groups; median paired ratio is 1.6819. Total charged expansions
are 4,411,954 versus 4,142,004. The much larger timing increase than expansion
increase shows that this counter omits relevant per-proposal work. In particular,
every complete equal-size proposal currently receives full embedding validation
before its exact redundancy score is compared to the incumbent. Rejecting an
already nonimproving score before validation is a candidate behavior-preserving
optimization. Final accepted proposals must still pass full validation.

`scripts/codex/analyze_refinement.py` records checks and full per-trial metrics
in the run's `analysis.json`; it requires complete successful observations and
explicitly refuses failed/late runs pending separate failure analysis. Timings
are refinement only on a shared laptop, with concurrent contact-reuse profiling;
they do not establish practical end-to-end performance against MM. This policy
is not yet promoted into the native end-to-end candidate.
