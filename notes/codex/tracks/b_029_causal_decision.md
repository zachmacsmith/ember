# B029 causal decision

2026-09-10. The [complete screen](b_029_constructor_results.md) rejects the fixed
assumption that reducing overlap through the chosen local root score will
produce good complete embeddings, with later quality sweeps recovering the
added chain length. Construction remains incomplete on ER, BA, WS, SBM100 and
the synthetic control; both retained successes have worse ACL. Those are
substantial deficits across structures, not one unfavorable aggregate score.

**What the controlled comparison resolves.** Anchor and B028 have equal recorded
initial Q/O on every input and equal final success/Q here. B029 changes both
initial statistics on every input: fewer overlaps, more memberships. These are
scalar observations, not recovered-map or full-trajectory equivalence claims.

| Input | Initial Q, anchor → B029 | Initial O, anchor → B029 | Final B029 O |
|---|---:|---:|---:|
| ER80 | 156 → 175 | 58 → 54 | 13 |
| SBM80 | 124 → 154 | 25 → 20 | 0 |
| Grid128 | 136 → 146 | 17 → 8 | 0 |
| Singleton80 | 126 → 165 | 58 → 55 | 39 |
| ER100 | 176 → 217 | 81 → 73 | 16 |
| BA100 | 161 → 177 | 75 → 60 | 3 |
| WS100 | 164 → 181 | 59 → 46 | 2 |
| SBM100 | 173 → 199 | 67 → 59 | 9 |
| Planar100 | 154 → 170 | 54 → 39 | 0 |

Lower initial O did not reliably buy earlier validity or better incumbent ACL.
On SBM80, B029 first becomes valid later and at Q170 versus Q141; four subsequent
qubit reductions leave Q166 versus Q140. Grid first becomes valid at Q147,
then makes no strict quality improvement through three completed quality
sweeps and stops at a period-2 recurrence. Anchor/B028 reach Q141 and improve
to Q139. Planar100 is the positive exception: validity at 55.743 s, followed
by Q174→172→171 before the deadline. Its measured benefit is retained.

This implicates the interaction of overlap-first root ranking, construction
choices and later shortening capability. It does not separately identify which
alternative acceptance schedule or move neighborhood would solve the remaining
problem. The final saved grid visit excludes all 20 adjacent hardware roots
because required labels are unavailable; it is an optimum only on the captured
domain. This observation does not establish that those excluded roots admit a
better feasible chain, nor that completing their labels would help. Detailed
visits contain the first sixteen and last only; they cannot describe all quality
queries or estimate an all-visit failure rate.

**What the computation resolves.** Retaining arrays removes most dictionary
conversion: B028's conversion receipts total 175.187 s, versus 1.370 s for
anchor and 1.329 s for B029. Yet the complete anchor algorithm gains no success
or Q here and takes more total time; grid rises from 27.652 to 42.629 s for
the same Q139. Additional compact-evaluator setup, compilation, materialization
and certification must be charged. Faster conversion alone is insufficient.

B029's disjoint routing stages consume 349.771 s (68.1% of solver wall), and
union stages 121.703 s (23.7%). Union compilation-containing dispatch receipts
are 31.825 s and materialization receipts 42.236 s; these overlap stage totals
and are not additional costs or compiler-free estimates. It completes 66,421
of 66,422 local trials and records 1,323 local root moves, with 86,569 excluded
neighbor events. Those events are not distinct sites. Anchor completes 11,918
trials and no root moves. Complete visits are almost equal, 5,971 versus 5,972.
The extra local work establishes that the operator ran, not that it advanced
the final research objective.

**Decision.** Stop this fixed overlap-prioritized local-descent constructor and
the acceleration-only continuation. Retain the exact union-cost evaluator,
array-retention result, planar success and all regressions as evidence; do not
declare every root-movement mechanism ineffective. B may replace the current
architecture. Before another implementation, a new hypothesis must address the
shared completion/chain-length tradeoff and state what time-to-validity and
incumbent-ACL trajectories would justify it in a complete-constructor screen.
Do not enlarge local root search merely because overlap, trial count or warm
cost improves. This note proposes no new candidate or diagnostic execution.
