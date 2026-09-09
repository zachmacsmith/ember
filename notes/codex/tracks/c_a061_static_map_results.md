# A061 static maps: sparse deficits often sit in low-degree chains

All fourteen selected A061/MM seed-0 maps are timely original-valid embeddings. The saved-map projection passed after verifying the 646-file archive and original-label provenance; it took .603 seconds internally, .714 seconds including process startup. No map was modified, optimized or regenerated. The [scope fixed before projection](c_a061_static_map_diagnostic_scope.md) deliberately selects six known deficits and one retained-win contrast, so these are descriptive development comparisons.

Entries are **A061 / MM**. Branch sites have degree at least three in the target graph induced by their chain; cycle rank is summed `edges−sites+1`. “Contactless” means no coupler to an original source-neighbor chain, and includes required singleton isolates. Removable sites are tested individually against the unchanged map; counts are not simultaneous or sequential savings.

| Input | Q | Singletons | Branch sites / cycle rank¹ | Contactless sites | Individually removable |
|---|---:|---:|---:|---:|---:|
| grid1584 | 163 / 134 | 96 / 122 | 0,0 / 0,0 | 0 / 0 | 4 / 0 |
| honey32367 | 241 / 196 | 146 / 184 | 0,0 / 0,0 | 4 / 0 | 0 / 0 |
| BA10662 | 424 / 410 | 10 / 23 | 9,0 / 38,3 | 24 / 9 | 2 / 13 |
| wheel2429 | 187 / 147 | 100 / 119 | 4,0 / 3,0 | 10 / 0 | 1 / 1 |
| LFR31357 | 170 / 160 | 55 / 56 | 0,1 / 2,1 | 10 / 2 | 0 / 2 |
| planted34404 | 158 / 136 | 113 / 130 | 0,0 / 0,0 | 11 / 6 | 0 / 0 |
| planar31536 | 260 / 281 | 82 / 73 | 2,0 / 2,3 | 5 / 0 | 0 / 15 |

¹ Each comma pair is `(branch sites, cycle rank)` for that method. These are induced physical graphs, not inferred constructor routes or chosen spanning trees.

Several deficits are not explained by branch-heavy chains. Grid's degree-4 owners account for 22 of its 29 extra A061 sites; its degree-4 singleton count is 61 versus MM's 80. Honeycomb's degree-3 owners account for 40 of 45 extra sites, with 108 versus 142 singletons. Wheel's degree-3 rim accounts for 37 of the 40-site gap; the hub accounts for three. Thus low-degree placement/contact sharing is a concrete strategic target; the observations do not distinguish geometric initialization, required lifting contacts, owner assignment or allowed rearrangements.

Site contact sharing counts **distinct original neighbors**, separately from physical coupler multiplicity. On grid, 62 A061 sites touch four original neighbors versus 80 MM sites; on honeycomb, 108 versus 142 sites touch three. BA is different: MM has 38 branch sites in 28 chains, versus nine in nine A061 chains, while using fewer sites. More branching is therefore not uniformly wasteful. Every physical contact count and source-degree stratum is retained in the [per-owner/site detail](../../../results/codex/a061-static-map-review/analysis001/details.json).

Contactless sites are not generally padding. All four honeycomb, ten wheel and ten LFR A061 contactless sites are articulation points of their current chains. Of planted's eleven, six are singleton isolates and five are articulations; none is individually removable. A single-deletion cleanup cannot start on the current honeycomb, LFR, planted or planar A061 maps. That does not prove global minimality or rule out joint relocation. Planar is a useful contrast: A061 wins by 21 Q despite five necessary contactless connectors and fewer degree-3 singletons; its advantages occur elsewhere. The fifteen individually removable MM sites do not establish fifteen jointly achievable savings.

Pinned Zephyr coordinates classify all induced chain edges without leftovers. BA uses 241/150 same-course, 2/14 odd and 59/127 cross-orientation edges; grid uses 6/0, 6/0 and 23/6 respectively. These describe different footprints, **not a measured geometric-efficiency ranking**. They justify asking how compact low-degree placements retain multiple contacts, not prescribing another rail or local-repair heuristic.

[Seven paired records and exact degree deltas](../../../results/codex/a061-static-map-review/comparisons.json), [compact CSV](../../../results/codex/a061-static-map-review/analysis001/compact.csv), [selected task/result/map hashes](../../../results/codex/a061-static-map-review/analysis001/selected_maps.json), and [review manifest](../../../results/codex/a061-static-map-review/review_manifest.json) preserve the complete projection. Removability uses exact remaining-chain connectivity and per-original-neighbor supporting-site sets; other chains and contacts remain unchanged. Root's separate auxiliary-fill analysis is not duplicated, and no new constructor or confirmation claim follows.
