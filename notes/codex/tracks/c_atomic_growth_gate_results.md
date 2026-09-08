# Atomic growth passes the small constructor gate

All four predeclared calls ran once at seed 0 with five seconds each. Three returned independently valid minors at their exact minimum Q; triangle→path3 was rejected by its necessary edge-count bound. The two new delta/rollback checks also passed. No panel, registry or remote action occurred during these gates.

| Source → target | Atomic result | Q | Elementary reference | Atomic solver wall |
|---|---|---:|---|---:|
| path3 → path5 | SUCCESS | 3 | SUCCESS, Q3 | 0.351 ms |
| star4 → star4 | SUCCESS | 4 | SUCCESS, Q4 | 0.331 ms |
| triangle → cycle6 | SUCCESS | 6 | Visit cap, M1/Q3 | 0.409 ms |
| triangle → path3 | Necessary-bound failure | — | Same rejection | 0.062 ms |

The triangle provides the intended discriminator. Its singleton assignment, RNG state after initialization, first two visits and next chosen missing-edge endpoints match the saved elementary run. At visit 2, the atomic candidate adds `[5,4,3]` with ΔM=−1, ΔQ=+3 and ΔE=−0.25, so the unchanged acceptance rule commits it. The elementary candidate adds only site 5 with ΔM=0, ΔQ=+1 and ΔE=+0.25. Atomic growth completes before the next deletion visit. Independent replay verifies every committed state's connectedness, disjointness, contact delta and occupied volume. Cleanup deletes nothing; the output remains Q6.

This supports a **move-neighborhood** explanation for this specific gate: bundling required growth avoids exposing its positive-energy intermediate states to rejection and scheduled deletion. The disjoint representation can express the solution, and the unchanged energy accepts the complete move. It does not show that acceptance and scheduling are generally solved: later RNG consumption differs when the energy sign differs, and longer paths can consume access or produce poor ACL. The observed calls are far below the deadline, so this gate says little about computational cost at Ember sizes. Their tiny timings are not MM comparisons or evidence of a speed gain.

The next prepared experiment is [C007's full eight-input comparison](c_007_atomic_growth_screen.md): atomic growth, unchanged elementary growth as a separate experimental control, and fresh stock MM. Every arm starts from the original graphs independently. The elementary gate failure remains part of the evidence; the control is neither a fallback nor a portfolio member. No further supplied-state repairs or tiny policy changes are proposed before that diverse construction screen.

The [four-call summary](../../../results/codex/track-c-atomic-regions-gates/execution001/summary.json), raw calls, first-divergence record and focused checks are bound by the [review manifest](../../../results/codex/track-c-atomic-regions-gates/review_manifest.json). All prior elementary artifacts remain unchanged.
