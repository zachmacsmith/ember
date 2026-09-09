# Where the retained constructor's excess sites occur

2026-09-09 UTC. Offline projection of the seven pairs fixed in the
[diagnostic plan](strategic_fill_diagnosis_plan.md). All fourteen saved maps
passed the existing independent original-graph oracle. Elimination journals,
recorded neighbor sets and created fill edges were reconstructed and checked.
No constructor, MM call, optimization or new graph generation occurred.

Each Q difference below is A061 minus MM, partitioned by the inherited
constructor's core membership. These are final physical maps, not the unsaved
initial core map. Auxiliary edges are contacts added by elimination that survive
in that intermediate core; missing contacts refer to the particular final map.

| Input | Core/source vertices | Final excess Q: core / eliminated | Auxiliary core edges | Missing auxiliary contacts: A061 / MM |
|---|---:|---:|---:|---:|
| grid1584 | 104/128 | +25 / +4 | 52 | 22 / 43 |
| honey32367 | 90/190 | +30 / +15 | 161 | 43 / 140 |
| BA10662 | 122/122 | +14 / 0 | 0 | 0 / 0 |
| wheel2429 | 1/127 | +3 / +37 | 0 | 0 / 0 |
| LFR31357 | 56/100 | −3 / +13 | 73 | 13 / 54 |
| planted34404 | 25/133 | +5 / +17 | 25 | 5 / 21 |
| planar31536 | 109/152 | −36 / +15 | 0 | 0 / 0 |

Grid and honeycomb require attention to core placement, not only later lifted
vertices. BA undergoes no reduction: its entire 14Q deficit is already in the
native core output. Wheel is the converse: the core is a single vertex and most
excess lies in the lifted rim. LFR's core-owner allocation is already 3Q smaller
than MM's while its lifted owners use 13Q more. These are different locations
of a shared possible difficulty: choosing and revising physical contact sites.

MM's grid, honeycomb, LFR and planted arrangements miss many temporary fill
contacts. Thus the candidate's intermediate constraints exclude those exact
arrangements. This does **not** prove an unavoidable Q penalty for embedding
the filled core, nor that fill causes the final gap. A061 also releases fill
contacts in its final maps. Wheel creates 123 fill edges during elimination
even though none survives in its one-vertex core; its final A/MM maps miss
44/101 of those historical contacts. BA has no fill and still loses; planar has
no fill and wins. Another fill threshold is not justified by this projection.

The initial native-core Q inferred from audited base-Q and committed net-Q
receipts is respectively 140,134,424,1,104,28,195. Its physical embedding was not
saved, so we cannot reconstruct initial contact locations or attribute later
Q changes to a particular geometric error. Inferences from final owner groups
do not make those unsaved maps observable.

Combined with the [static chain profiles](tracks/c_a061_static_map_results.md),
this motivates revisions that can move contacts across several owners and act
on both core and lifted vertices under the original source constraints. It does
not yet demonstrate an effective such operator. The planar retained-win contrast,
BA's more highly branched MM map and all final regressions remain part of the
explanation to test.

Evidence: [projection and exact inputs](../../results/codex/strategic-review-20260909/fill-projection001/summary.json),
[script](../../results/codex/strategic-review-20260909/fill_projection.py),
SHA256 `307e56de1c0c3dcd7fca7578a9b7f33452623c5ce253782d64447777bb47613f`.
The single projection passed in 0.248s. This is exploratory diagnosis from
selected exposed development maps, not a new embedding result or causal proof.
