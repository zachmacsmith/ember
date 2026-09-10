# B029 saved-map decision

2026-09-10. **Proceed to one small complete-constructor screen.** Exact local
chain-union scoring and adjacent-root descent improve the declared overlap-first
objective on three of four candidate states. This resolves a proposal-ranking
deficit on several structures. It does not establish construction success: all
four selected states still overlap and receive no valid-minor or ACL credit.
B028 remains rejected.

| Saved input | Anchor (O, Phi, Q) | Selected (O, Phi, Q) | Distinct roots / moves | Cold process wall |
|---|---:|---:|---:|---:|
| ER80 g0001 | 43, 361, 250 | 39, 353, 254 | 55 / 2 | 12.32 s |
| Singleton control80 g0017 | 75, 418, 187 | 73, 421, 193 | 56 / 2 | 16.05 s |
| ER100 g0101 | 56, 520, 336 | 56, 520, 336 | 20 / 0 | 13.09 s |
| BA100 g0102 | 18, 280, 241 | 15, 276, 240 | 54 / 2 | 14.58 s |

All four workers finish every planned stage under the frozen 60 s allowance;
there are no censored stages, incomplete trials, import violations or terminal
errors. They perform 189 complete trial evaluations, including one repeated
selected materialization per state, and no routing or complete-constructor
calls. Independently checked selected chains are connected, preserve source
contacts and recorded witnesses, and have correct ownership and exact Q/O/Phi.
O is excess memberships. The original minor oracle supplies no validity credit
while O remains positive. Entry and route-array immutability, unsaved trial
scores and original-pipeline equivalence remain worker receipts, with the
selected state independently recounted by the unchanged checker.

**Preserve the regressions.** ER80 adds four memberships relative to its anchor;
the singleton control adds six and increases Phi by three. Relative to entry,
selected Q changes are +5, +4, +2 and -8. Overlap priority intentionally permits
these changes; complete convergence and subsequent ACL improvement must justify
them. The control's hidden witness was never supplied to the candidate.

The control and BA selected scores equal the best observed `(O, Phi, Q)` scores
in the earlier censored full-root diagnostics. ER80 stops at a strict adjacent
local optimum, although four previously examined roots have a better key
(O38/Phi357/Q259). This demonstrates a remaining neighborhood limitation for
that fixed state, without establishing that a larger search is worth its cost.
ER100 has no better B029-key root among its 630 previously completed proposals;
the previous lower-Phi examples have worse O. Its final physical neighborhood
also excludes one root missing three settled labels, so its tie cannot be
called a complete geometric local optimum. Those observations distinguish the
objective/domain questions from the demonstrated ER80 local-neighborhood gap.
The old best-overlap summary used `(O, Q, Phi)`; a separate passive projection
reorders all 4,314 old complete current-root receipts by B029's actual key.
Neither old diagnostic exhausts its captured root pool.

**Cost interpretation.** Whole-process totals are 56.04 s wall, 53.95 s user CPU
and 1.99 s system CPU. Worker wall totals 48.042 s; remaining process cost stays
charged. Local descent takes 5.592, 8.206, 5.866 and 7.878 s. Each cold anchor
contains two compilation dispatches, totaling 5.546–8.097 s per state. The first
adjacent-neighbor trials after that anchor span 0.0133, 0.0377, 0.0274 and
0.0242 s, measured from the first trial's start through the last trial's finish.
This span excludes the anchor and some loop entry/exit administration; it is
not a warmed full-constructor timing. Including the cold anchor, the same span
is 5.562–8.138 s, exceeding the prior measured warm route costs
(0.782/0.549/1.389/1.165 s). Thus the frozen cheap-cost claim does not hold for
the cold first pass. The bounded follow-up is justified by a specific observed
explanation: expensive initial compilation followed by inexpensive additional
root trials, with three objective improvements. Only complete calls can test
whether this cost amortizes usefully. No cost is excluded and no new active
runtime gate is introduced.

This is reused-state mechanism evidence on ER, BA and a synthetic control,
not generalization evidence for the new constructor. The next screen retains
the two B028 successes and all four failures, adds three other development
structures and includes a fixed-anchor ablation. Do not add plateau/root-pool
refinements before those complete results. Stop exhaustive root reconstruction
as a production strategy; keep its already saved evidence.

Execution authority is `results/codex/track-b029-union`: one launch on hyde02,
terminal supervisor and all four worker exits 0, absent tmux/processes, one
terminal inventory and one fetch. All 58 retrieved files match inventory digest
`3f24837892191e4366564e22a95db85eaee0f936142c702053c51e8f58074e09`.
Packet manifest is `7f7987388b5995203636986eea695a4305b314ed16223355729a66588352aa1c`.
The passive projection passed first execution in 0.330 s process time;
`passive_preparation001/freeze.json` binds 61 inputs and the independently
checked output is `saved_analysis001/summary.json`, SHA256
`95cb3e20e8a4221b57ac767ed5fa339d4fde936f4950796f773d2455f87a3161`.
The subsequent score-order/cost attribution passed once in 0.102 s process
time; its eight-input freeze, source and output are under
`mechanism_preparation001`, `project_mechanism.py` and `mechanism_analysis001`.
Both projections import no candidate and perform no search. Raw RSS remains
available without an algorithm-specific memory interpretation.
