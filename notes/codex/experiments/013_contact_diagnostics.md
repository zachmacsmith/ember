# Experiment 013: contact reconstruction opportunity diagnostics

Design diagnostics only. No algorithm source changed; no MM embeddings were inputs.
The probe selects only valid `native-search` rows from the fixed development run.

Input run: `results/codex/009-first-development-screen`. Total diagnostic wall: 11.32 s.
Fixed groups per incumbent: up to 8; tree/BFS work cap per move: 20000.
Singleton root probes: up to 8 vertices and 64 roots each.

Every control starts from the same saved incumbent and exactly the same groups.
Group savings are independent alternative proposals: they must not be added into a claimed final ACL.
Extra-root scans use the existing tree builder and independently validate every shortening.

## Interpretation and two proposed revisions

This is a mechanism diagnostic on nine development instances, one constructor
seed each. It is not a new benchmark result, a held-out test, or evidence that
any revision will beat MM. The complete run used the isolated
`.venv/codex-native/bin/python` environment with `minorminer` unavailable. All
incumbents and reported replacement witnesses passed an independent NetworkX
validity check. Source and target graph hashes were checked before the probes.
The candidate implementation inspected here has SHA256
`953e5259067ed6adb2f6d905e2e104a87938f4ee056906b4817608905eaa648f`.

### What the controls identify

- **Beam width alone is not the immediate limit.** Across the fixed 72 groups,
  width 1, 4, and 8 found improvements in 34, 39, and 39 cases. BFS work was
  85,176, 217,069, and 286,940 popped vertices respectively. A width-8 prefix
  beam cannot recover chain alternatives that were never generated.
- **Tree quota and root quota are separate limits.** Raising generated trees
  from 3 to 8 while preserving the original 9-root ceiling found one additional
  WS group improvement. Allowing 24 roots as well found three additional king
  group improvements. The latter full change used 559,837 BFS expansions across
  the same 72 groups versus 217,069 for the baseline; 13 moves exhausted their
  20,000-expansion budget. Increasing every quota is not yet justified.
- **A single tie choice per root can miss an existing small tree.** Of 72
  expensive singleton probes, scanning up to 64 roots gave no gain beyond the
  default search. Enumeration of connected sets of size at most 3 nevertheless
  found a valid king vertex-11 replacement `[374, 3037, 3038]`, reducing its
  chain from 4 to 3. Root 3038 has rank 11; the scan tries forward neighbor
  ordering there and fails, while reverse ordering finds another valid tree
  `[662, 3037, 3038]`. Every witness was checked. Thus the root-scan null result
  is not proof that the generated-tree model is locally optimal. The exact
  checks examined 299,955 connected sets and certified no smaller chain than
  the scan result in the fixed region for 52 of the 72 probes. They do not
  certify a global embedding bound.
- **The local region omits real relocation sites.** Exhaustive boundary
  intersection for every one of the 446 non-singleton chains found 36 valid
  singleton sites. For ER vertex 47, its two-qubit chain can move to qubit 2845
  or 2869; for ER vertex 51, its two-qubit chain can move to qubit 494. All
  these sites lie outside the default singleton region. They are at free-space
  distance 3 from the old chain, not in disconnected components. Every other
  singleton-capable chain in these nine incumbents had a site within its
  default region. Vertices 47 and 51 are source neighbors, so these independent
  gains must not be summed without validating the combined move.
- **Blindly expanding the first few group regions does not address that
  opportunity.** Doubling the region cap yielded no additional gain on the
  fixed groups. Increasing halo 2 to 3 with cap 1024 lost three K40 proposals
  and added none there or elsewhere in that control. The ER singleton sites
  belong to lower-priority vertices outside those first eight tested groups;
  the two findings are compatible. Enlarged regions change root ranking and
  greedy paths, so the searched proposals need not be nested even though the
  available physical sites are nested.
- **Group coverage is restricted.** The first 64 groups cover only 24 of 74
  positive-bound-gap ER vertices, 24 of 45 regular vertices, and 24 of 50 WS
  vertices. The complete default pair list contains only 79 of 1,346
  logical-or-physical ER pairs and 78 of 459 WS pairs. Additional omitted-pair
  probes found valid coordinated opportunities: WS pair `[28, 29]` saves one
  qubit through member growth while both default singleton searches fail;
  eight probed omitted bipartite pairs each save two while their singleton
  searches fail. These comparisons concern the specified bounded singleton
  search, not exhaustive singleton impossibility. Most omitted-pair gains
  elsewhere are already explained by individual shortening. Coverage counts
  therefore motivate follow-up, but alone do not identify a better scheduling
  rule at matched total work.
- **The degree bound is too weak to measure local opportunity.** On these
  Zephyr graphs it is 1 for every source vertex of degree at most the target
  maximum degree. ER has Q=273 against a summed bound of 80, but the eight
  highest-cost groups did not improve under any tested control. The bound
  safely limits group size caps; it does not estimate the effect of frozen
  neighbor locations or show that Q=80 is attainable.

The implementation explains these effects. In
`packages/ember-qc/src/ember_qc/algorithms/factored/contact_repair.py`, `_region`
starts only from old selected qubits (lines 100–121). `_grow` commits to the
first reachable missing contact and returns as soon as known contacts are
covered (124–160). It never deliberately adds an optional branch just to make
an unbuilt group member easier to reconstruct. `_alternatives` uses old
unbuilt chains only as root hints and takes the first bounded distinct routes
(163–221). Prefix ranking uses only assigned qubits followed by label order
(293–297); it has no estimate of completion difficulty. `_groups` selects the
same highest-excess neighbors for each center and each group size (356–382).
These are documented search restrictions, not correctness defects: full
validation and atomic replacement remain in place.

### Revision 1: seed regions from required contacts

For the same selected group, retain every old selected qubit, then add a bounded
set of free sites drawn from the physical boundaries of its frozen logical
neighbors before spending the remaining region budget on free-space expansion.
For a singleton, the intersection of all required boundary sets identifies
every legal one-qubit site exactly and cheaply; those sites receive priority.
For larger groups, boundary masks provide the same graph-independent contact
information for selecting seeds. Contact reconstruction, the global objective,
occupancy constraints, deadline, and atomic acceptance remain unchanged. This
is a change to the neighborhood of the existing algorithm, not a second
constructor or portfolio member.

Self-critique: the demonstrated missing opportunity is only one qubit per ER
move, and a halo of 3 could reach these particular sites. A large collection
of boundary seeds could consume the region cap, fragment the free region, or
displace useful connecting paths. Dense boundaries can be expensive to scan.
The strict cap and deadline must include seed discovery; a seeded region is
not allowed to evict the incumbent's physical qubits. This change alone cannot
be presumed to close the observed ACL gaps.

Falsifier: first compare the same saved incumbents and same singleton/group
IDs under halo-only, halo-3, and boundary-seeded region construction, with
identical region and routing-work caps. The new construction should expose
and validate the stated ER witnesses; failure to do so disproves the intended
mechanism. Then compare cumulative runs at matched total time on additional
development seeds using one globally fixed configuration. If the gain is
explained entirely by greater work, or if dense quality falls, do not advance
the revision based on these two witnesses.

### Revision 2: make bounded route search resumable after failed completion

Separate the root-attempt budget from the retained-tree budget. Keep the next
root, unused neighbor-order alternative, and already-generated chain options
for each reconstruction prefix. When the current bounded prefix cannot be
completed, resume that same contact search to request another distinct route
instead of permanently discarding the search after three generated trees.
Spend one shared expansion budget across all continuations. Keep a small
number of physically distinct connected alternatives, including a longer
member when the group's remaining qubit cap still allows a net reduction.
Do not enlarge the prefix beam as the first response: width 8 did not improve
these controls. The root and tree controls above show why both continuations
need to be available, although their priority rule is still a hypothesis.

Self-critique: retaining continuation state adds Python overhead and can
degenerate into more breadth-first searches with no benefit. Changing route
generation cannot solve all limitations of cost-only prefix ranking or the
restricted group schedule. A currently feasible prefix may be globally poor,
so resuming only after complete failure can still miss better valid group
assignments. Novelty would require a defensible joint-search contribution and
broader evidence; resumable search by itself is not a publication claim.

Falsifier: retain the same 72 groups and the same 20,000-expansion per-move cap.
Trace which previously discarded route permits completion, including the
king singleton tie witness and the WS growth case. Compare the proposed
continuation rule against baseline and the simpler fixed 8-tree/24-root
control using both gain and time. If it merely reproduces the latter's work
without improving gain per unit time, reject the extra machinery. Cumulative
quality must then be tested on additional seeds; local alternative savings
remain non-additive.

No implementation of either revision is included in this experiment. Group
scheduling and a completion-aware prefix score remain documented limitations;
the present probes do not isolate a sufficiently supported replacement for
either, so they are not additional recommended revisions here.

## Controls on the same groups

Counts show improved groups / tested groups, then largest individual qubit saving, total BFS expansions, and summed move time.

`routes8` allows up to 24 root attempts and 8 distinct generated trees per prefix; `routes8_roots9` keeps the original 9-root ceiling while retaining up to 8 trees.
The root-ceiling control suppresses surplus `_grow` calls in this script; it restores the original helper after each move. Algorithm files are unchanged.

| Source | Control | Improved / tested | Max saving | Growing-member proposals | BFS expansions | Move time s | Region-cap hits |
|---|---|---:|---:|---:|---:|---:|---:|
| bipartite_30_30 | base | 8/8 | 2 | 0 | 2451 | 0.0375 | 0 |
| bipartite_30_30 | beam1 | 8/8 | 2 | 0 | 1323 | 0.0264 | 0 |
| bipartite_30_30 | beam8 | 8/8 | 2 | 0 | 3073 | 0.0453 | 0 |
| bipartite_30_30 | routes8 | 8/8 | 2 | 0 | 9089 | 0.0525 | 0 |
| bipartite_30_30 | region1024 | 8/8 | 2 | 0 | 2451 | 0.0388 | 0 |
| bipartite_30_30 | halo3_region1024 | 8/8 | 2 | 0 | 3600 | 0.0477 | 0 |
| bipartite_30_30 | routes8_roots9 | 8/8 | 2 | 0 | 3122 | 0.0398 | 0 |
| complete_100 | base | 0/8 | 0 | 0 | 15314 | 0.0909 | 0 |
| complete_100 | beam1 | 0/8 | 0 | 0 | 8552 | 0.0436 | 0 |
| complete_100 | beam8 | 0/8 | 0 | 0 | 17673 | 0.1010 | 0 |
| complete_100 | routes8 | 0/8 | 0 | 0 | 43088 | 0.1833 | 0 |
| complete_100 | region1024 | 0/8 | 0 | 0 | 15314 | 0.0906 | 0 |
| complete_100 | halo3_region1024 | 0/8 | 0 | 0 | 21468 | 0.1248 | 0 |
| complete_100 | routes8_roots9 | 0/8 | 0 | 0 | 17215 | 0.0966 | 0 |
| complete_40 | base | 3/8 | 1 | 0 | 5981 | 0.0417 | 0 |
| complete_40 | beam1 | 1/8 | 1 | 0 | 3153 | 0.0179 | 0 |
| complete_40 | beam8 | 3/8 | 1 | 0 | 6152 | 0.0425 | 0 |
| complete_40 | routes8 | 3/8 | 1 | 0 | 19833 | 0.0714 | 0 |
| complete_40 | region1024 | 3/8 | 1 | 0 | 5981 | 0.0418 | 0 |
| complete_40 | halo3_region1024 | 0/8 | 0 | 0 | 6609 | 0.0459 | 0 |
| complete_40 | routes8_roots9 | 3/8 | 1 | 0 | 7208 | 0.0461 | 0 |
| grid_8x8 | base | 7/8 | 2 | 0 | 4942 | 0.0313 | 0 |
| grid_8x8 | beam1 | 7/8 | 2 | 0 | 1965 | 0.0127 | 0 |
| grid_8x8 | beam8 | 7/8 | 2 | 0 | 6689 | 0.0440 | 0 |
| grid_8x8 | routes8 | 7/8 | 2 | 0 | 17685 | 0.0603 | 0 |
| grid_8x8 | region1024 | 7/8 | 2 | 0 | 4942 | 0.0313 | 0 |
| grid_8x8 | halo3_region1024 | 7/8 | 2 | 0 | 7080 | 0.0463 | 0 |
| grid_8x8 | routes8_roots9 | 7/8 | 2 | 0 | 7529 | 0.0389 | 0 |
| honeycomb_5x5 | base | 5/8 | 1 | 0 | 7732 | 0.0360 | 0 |
| honeycomb_5x5 | beam1 | 5/8 | 1 | 0 | 2684 | 0.0129 | 0 |
| honeycomb_5x5 | beam8 | 5/8 | 1 | 0 | 11608 | 0.0511 | 0 |
| honeycomb_5x5 | routes8 | 5/8 | 1 | 0 | 28336 | 0.0724 | 0 |
| honeycomb_5x5 | region1024 | 5/8 | 1 | 0 | 7732 | 0.0351 | 0 |
| honeycomb_5x5 | halo3_region1024 | 5/8 | 1 | 0 | 13335 | 0.0585 | 0 |
| honeycomb_5x5 | routes8_roots9 | 5/8 | 1 | 0 | 11322 | 0.0432 | 0 |
| king_8x8 | base | 5/8 | 1 | 0 | 10373 | 0.0516 | 0 |
| king_8x8 | beam1 | 5/8 | 1 | 0 | 4023 | 0.0202 | 0 |
| king_8x8 | beam8 | 5/8 | 1 | 0 | 13104 | 0.0698 | 0 |
| king_8x8 | routes8 | 8/8 | 2 | 0 | 25666 | 0.0877 | 0 |
| king_8x8 | region1024 | 5/8 | 1 | 0 | 10373 | 0.0515 | 0 |
| king_8x8 | halo3_region1024 | 5/8 | 1 | 0 | 12503 | 0.0732 | 0 |
| king_8x8 | routes8_roots9 | 5/8 | 1 | 0 | 14970 | 0.0627 | 0 |
| random_er_80_d8 | base | 0/8 | 0 | 0 | 53827 | 0.1125 | 0 |
| random_er_80_d8 | beam1 | 0/8 | 0 | 0 | 28333 | 0.0509 | 0 |
| random_er_80_d8 | beam8 | 0/8 | 0 | 0 | 57256 | 0.1104 | 0 |
| random_er_80_d8 | routes8 | 0/8 | 0 | 0 | 125517 | 0.2131 | 0 |
| random_er_80_d8 | region1024 | 0/8 | 0 | 0 | 53827 | 0.1016 | 0 |
| random_er_80_d8 | halo3_region1024 | 0/8 | 0 | 0 | 66069 | 0.1328 | 0 |
| random_er_80_d8 | routes8_roots9 | 0/8 | 0 | 0 | 75428 | 0.1357 | 0 |
| regular_80_d3 | base | 8/8 | 3 | 0 | 45413 | 0.0954 | 0 |
| regular_80_d3 | beam1 | 8/8 | 3 | 0 | 13243 | 0.0322 | 0 |
| regular_80_d3 | beam8 | 8/8 | 3 | 0 | 68375 | 0.1420 | 0 |
| regular_80_d3 | routes8 | 8/8 | 3 | 0 | 130987 | 0.2245 | 0 |
| regular_80_d3 | region1024 | 8/8 | 3 | 0 | 45413 | 0.0953 | 0 |
| regular_80_d3 | halo3_region1024 | 8/8 | 3 | 0 | 69815 | 0.1567 | 0 |
| regular_80_d3 | routes8_roots9 | 8/8 | 3 | 0 | 71438 | 0.1387 | 0 |
| watts_strogatz_80 | base | 3/8 | 1 | 0 | 71036 | 0.1392 | 5 |
| watts_strogatz_80 | beam1 | 0/8 | 0 | 0 | 21900 | 0.0434 | 5 |
| watts_strogatz_80 | beam8 | 3/8 | 1 | 0 | 103010 | 0.2054 | 5 |
| watts_strogatz_80 | routes8 | 4/8 | 1 | 4 | 159636 | 0.2740 | 5 |
| watts_strogatz_80 | region1024 | 3/8 | 1 | 0 | 80114 | 0.1596 | 0 |
| watts_strogatz_80 | halo3_region1024 | 3/8 | 1 | 0 | 112509 | 0.2257 | 4 |
| watts_strogatz_80 | routes8_roots9 | 4/8 | 1 | 4 | 111131 | 0.2111 | 5 |

## Coverage and lower-bound gap

The degree bound is a necessary individual-chain bound, not an attainable embedding objective.

| Source | Incumbent Q | Sum degree bound | Positive-gap vertices | Covered by first 64 groups | Selected pairs / logical-or-physical pairs |
|---|---:|---:|---:|---:|---:|
| bipartite_30_30 | 151 | 120 | 31 | 22 | 59/928 |
| complete_100 | 726 | 600 | 100 | 24 | 99/4950 |
| complete_40 | 156 | 120 | 32 | 24 | 39/780 |
| grid_8x8 | 89 | 64 | 19 | 19 | 59/231 |
| honeycomb_5x5 | 88 | 70 | 16 | 16 | 64/251 |
| king_8x8 | 122 | 64 | 42 | 23 | 63/408 |
| random_er_80_d8 | 273 | 80 | 74 | 24 | 79/1346 |
| regular_80_d3 | 145 | 80 | 45 | 24 | 79/465 |
| watts_strogatz_80 | 153 | 80 | 50 | 24 | 78/459 |

## Extra-root opportunity probes

Only rows where scanning more roots improves upon the default singleton search appear here. Absence is not proof of no opportunity.

| Source | Vertex | Old length | Default singleton | Extra-root result | Best root rank | Roots scanned / available | Expansions |
|---|---:|---:|---:|---:|---:|---:|---:|

## Exact small singleton check

On the same root-probe vertices and halo-2 region, enumerate connected singleton, pair, and triple sets smaller than the scan result.
This is a diagnostic certificate within a fixed region, not an embedding constructor or a global lower bound.

| Source | Probed vertices | Extra-root improvements | Exact additional improvements | Connected sets tested | No shorter tree certified in region |
|---|---:|---:|---:|---:|---:|
| bipartite_30_30 | 8 | 0 | 0 | 3836 | 8 |
| complete_100 | 8 | 0 | 0 | 54406 | 0 |
| complete_40 | 8 | 0 | 0 | 24406 | 5 |
| grid_8x8 | 8 | 0 | 0 | 15373 | 8 |
| honeycomb_5x5 | 8 | 0 | 0 | 2681 | 8 |
| king_8x8 | 8 | 0 | 1 | 8731 | 7 |
| random_er_80_d8 | 8 | 0 | 0 | 58430 | 0 |
| regular_80_d3 | 8 | 0 | 0 | 25773 | 8 |
| watts_strogatz_80 | 8 | 0 | 0 | 106319 | 8 |

## Omitted pair probes

Probe up to eight logical-or-physical adjacent pairs absent from the entire default pair list, ranked by total degree-bound excess and then labels.
The final column compares each independent pair move with the sum of two independent singleton gains; it is not a proof that every possible singleton route fails.

| Source | Improving omitted pairs / tested | Max saving | Pair exceeds independent singleton savings | BFS expansions | Move time s |
|---|---:|---:|---:|---:|---:|
| bipartite_30_30 | 8/8 | 2 | 8 | 1128 | 0.0259 |
| complete_100 | 0/8 | 0 | 0 | 9298 | 0.0512 |
| complete_40 | 3/8 | 1 | 0 | 3421 | 0.0293 |
| grid_8x8 | 5/8 | 1 | 0 | 2014 | 0.0119 |
| honeycomb_5x5 | 3/8 | 1 | 0 | 3358 | 0.0125 |
| king_8x8 | 3/8 | 2 | 1 | 3837 | 0.0194 |
| random_er_80_d8 | 0/8 | 0 | 0 | 13678 | 0.0351 |
| regular_80_d3 | 4/8 | 1 | 0 | 22267 | 0.0444 |
| watts_strogatz_80 | 2/8 | 1 | 1 | 23737 | 0.0533 |

## Singleton sites anywhere in the supplied target

For every non-singleton source chain, intersect the physical boundaries of all frozen logical neighbors, then exclude frozen occupied qubits.
All remaining sites are enumerated, including the released old chain, and every proposed one-qubit replacement is independently validated.
Compare membership in the default singleton halo-2 region capped at 512 qubits. Counts refer to independent moves on the original incumbent.

| Source | Non-singleton chains | With any singleton site | With site outside region | With sites only outside region | Valid sites | Diagnostic time s |
|---|---:|---:|---:|---:|---:|---:|
| bipartite_30_30 | 60 | 0 | 0 | 0 | 0 | 0.0070 |
| complete_100 | 100 | 0 | 0 | 0 | 0 | 0.0520 |
| complete_40 | 40 | 0 | 0 | 0 | 0 | 0.0066 |
| grid_8x8 | 19 | 4 | 0 | 0 | 4 | 0.0165 |
| honeycomb_5x5 | 16 | 4 | 0 | 0 | 6 | 0.0255 |
| king_8x8 | 42 | 1 | 0 | 0 | 1 | 0.0086 |
| random_er_80_d8 | 74 | 3 | 2 | 2 | 4 | 0.0433 |
| regular_80_d3 | 45 | 9 | 0 | 0 | 11 | 0.0560 |
| watts_strogatz_80 | 50 | 8 | 0 | 0 | 10 | 0.0517 |

## Reproduction and raw records

```sh
.venv/codex-native/bin/python scripts/codex/contact_diagnostics.py --run results/codex/009-first-development-screen --groups 8 --root-vertices 8 --roots 64 --work 20000 --raw-output /tmp/013_contact_diagnostics.rerun.json
```

Complete raw records: [013_contact_diagnostics.json](data/013_contact_diagnostics.json).

SHA256: `febc165623db957410bfdbe55d36d0349a0c18a6d8623d8b87a087d85531bb95`.
