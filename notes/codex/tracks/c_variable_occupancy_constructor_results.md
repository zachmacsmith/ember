# Variable occupancy: the first constructor policy fails its growth gate

The four predeclared full-constructor calls ran once at seed 0 with five seconds each. Path and star returned optimal singleton embeddings; the negative triangle→path input was rejected. Triangle→cycle6 exhausted its **24-visit cap**, not its deadline, with one missing edge. This fixed policy fails its gate and will not enter the eight-input panel.

| Source → target | Status | Final Q | Missing edges | Solver wall |
|---|---|---:|---:|---:|
| path3 → path5 | SUCCESS | 3 | 0 | 0.338 ms |
| star4 → star4 | SUCCESS | 4 | 0 | 0.322 ms |
| triangle → cycle6 | FAILURE: visit cap | 3 | 1 | 0.673 ms |
| triangle → path3 | FAILURE: necessary edge bound | — | — | 0.057 ms |

Before these calls, three focused mechanism checks passed: exact contact/Q deltas for all four moves, independent growth and deletion while contacts remain missing plus cache invalidation, and interrupted scoring/commit rollback. The execution retained every call and used an independent NetworkX recount of original edges and each committed search state. All replay checks passed, inputs stayed unchanged, and no prohibited import was attempted. Failed-state Q is occupied volume, not the quality of a valid embedding. These tiny timings carry no performance comparison to MM.

The triangle trajectory contains three accepted additions, three accepted deletions, six neutral label swaps and six empty transfer visits. Three other additions were rejected. Q varied 3–5 while M stayed 1. Every selected addition had ΔE=+0.25; every selected deletion had ΔE=−0.25. At visit 6, Q=5 and the only unused site, 4, touched both missing-edge endpoints. The next scheduled deletion removed site 5, destroying that immediate completion opportunity before the next addition visit. This implicates the interaction of finite scheduling, elementary moves and acceptance; it does not isolate acceptance alone or reject the disjoint-region representation. Runtime was not the limiting factor.

An explicit certificate from the **actual final state** further distinguishes those issues. Starting with chains `{0:[1],1:[0],2:[2]}`, adding sites 5, 4, 3 in that order to chain 1 gives `(M,Q)=(1,3)→(1,4)→(1,5)→(0,6)`. Independent original-edge validation confirms the final minor. The elementary energy changes are +0.25,+0.25,−0.75: two positive preparatory steps precede completion, whereas their atomic sum is −0.25. This is saved-state arithmetic, not another solver call or a credited result. Q=6 is necessary here: any proper induced subset of the six-cycle is a forest and cannot contain a triangle minor.

The next proposed discriminator changes only addition to one atomic free-path proposal, retaining initialization, energy and visit schedule. Its rationale and limits are in [the pre-code proposal](c_atomic_growth_constructor_proposal.md). No such constructor call has run. Full traces, work, gate results and certificate are linked by the [review manifest](../../../results/codex/track-c-variable-regions-gates/review_manifest.json); the [four-call summary](../../../results/codex/track-c-variable-regions-gates/execution001/summary.json) preserves all outcomes.
