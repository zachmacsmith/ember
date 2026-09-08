# Revision 020: bounded search over partial contact trees

Design and self-critique recorded before implementation. This revision replaces
only the tree proposal inside one contact reconstruction. It does not change
construction, region selection, group selection, acceptance, or benchmark
policy. The root agent owns integration under one globally fixed `tree_policy`.

## API and invariants

```python
grow_contact_tree(root, available, masks, required, ctx, budget, size_cap,
                  reverse=False, *, frontier_width=4,
                  witnesses_per_contact=2, diagnostics=None)
```

The core arguments match the existing `_grow` primitive. `available` excludes
frozen occupied qubits and already assigned selected chains. Bit `i` in
`masks[q]` means qubit `q` contacts required neighbor set `i`. Only bits in
`required` are obligations. `ctx` supplies actual physical adjacency and stable
target ranks. The caller supplies the existing shared `_Budget` object.

Return either a connected `frozenset` containing `root`, within `available`,
covering every required contact and of size at most `size_cap`, or `None`.
Input sets, masks, and context are not modified. A completed tree found before
exhaustion may be returned; incomplete trees never escape. The embedding-level
caller still checks all source edges and commits atomically. No new contact
obligation is inferred from a graph family or an old embedding table.

## Admissible remaining-size estimate

For a connected partial tree `T`, let `C_i` be the available qubits carrying
missing contact bit `i`. Define

```text
h(T) = max over missing i of distance_available(T, C_i)
f(T) = |T| + h(T)
```

Distance is the minimum number of physical edges from any member of `T` to a
contact set in the available induced graph. Any connected extension must add
at least that many new vertices for each missing set. Consequently `h` never
overestimates the minimum additional qubits required, although different
contacts can make the true requirement much larger. If a contact cannot be
reached, no extension exists. If it cannot be reached within
`size_cap - |T|` edges, no extension fits the size cap. This is a bound for a
fixed partial tree, not a lower bound for replacing the root or other chains.

One multi-source BFS from `T` obtains all missing-contact distances and their
shortest witness paths. It processes no layer beyond the remaining size cap
and stops after the layer in which all missing sets were first reached.
Record up to two distinct shortest witness paths per missing bit; paths may
cover several contacts at once. Every processed BFS vertex calls `budget.pop()`.

## Pseudocode

```text
reject invalid root/cap or exhausted budget
if root already covers all required bits: return {root}
prepare root state with bounded multi-source BFS
    discard state if a contact is unreachable within the remaining size cap
    store h(T), covered mask, and bounded shortest witness paths
frontier := [root state]; seen := {root state}; best := none

while frontier is nonempty and the shared budget permits work:
    pop the state with smallest (|T| + h(T), missing-count, |T|, stable rank)
    for each distinct shortest witness path in that prepared state:
        form connected extension T' by adding the path
        discard duplicates and extensions exceeding size_cap
        retain a fully covering extension as best if it uses fewer qubits
    for each new incomplete extension:
        prepare distances and witness paths with the same shared budget
        discard if its optimistic total exceeds size_cap or cannot beat best
    merge prepared successors into frontier
    retain at most frontier_width states:
        first choose the best representative of each distinct covered mask
        then fill unused slots with remaining best-ranked states
return best completed tree, or none
```

The frontier bound is heuristic and removes any global optimality guarantee.
The admissible distance bound alone is used for impossibility/cost pruning;
coverage diversity is a stated search preference, not a proof of dominance.
Shortest-path witness choices remain incomplete because not every equal-length
physical path to an endpoint is enumerated. Neither limitation is hidden by the
term "admissible".

## Self-critique before implementation

The maximum-distance bound can be very weak when several contacts require
separate branches. Computing one BFS per candidate partial tree can also cost
more than the greedy builder saves. Restricting paths to shortest representatives
may still miss a route whose slightly longer early segment improves the final
tree. A contact mask does not summarize all physical consequences for other
selected chains, so diversity by mask can discard a useful location. The shared
budget, capped frontier, finite witnesses, and actual wall-time measurements
are essential; a larger beam by itself is not the proposed contribution.

This change is motivated by the missed connected tree and route-quota effects
in experiment 013 and the limitations identified in review 016. It is not a
novelty or superiority claim. A tiny fixture will establish only the declared
tree-search mechanism. A bounded replay on saved native-search incumbents can
test whether that mechanism also exposes existing opportunities. No MM
embeddings or integer-programming solver are inputs.

## Discriminating checks

1. A contact-set fixture in which the nearest first contact creates an avoidable
   branch must fail with the existing greedy builder at a fixed size cap and
   succeed with the new distance-prioritized search, including width one if the
   bound alone identifies the better extension.
2. Check completed-tree connectivity, membership, contact coverage, and size with
   an independent graph oracle; check the distance bound against tiny exhaustive
   extensions. Exhausted calls must return no partial tree and preserve inputs.
3. Compare fixed roots/groups on the same saved native-search embedding, with the
   same available region, masks, size cap, and work allowance. Record added
   routing work and wall time. A gain that disappears at matched work/time does
   not justify advancement.

Implementation and measured results will be appended below after these design
requirements have been recorded.

## First fixed-incumbent diagnostic

Input: nine successful native-search rows from `results/codex/009-first-development-screen`, constructor seed 0. Source/target hashes and input/output validity were independently checked. No MM embedding or module was used.

Each control starts from the same saved incumbent and the same first four legacy groups. Outer group beam 1, alternatives 3, halo 2, region cap 512, two group orders, and 20,000 shared expansions per move. New tree controls use two shortest witnesses per contact and frontier width 1 or 4. There is no cumulative application; individual group savings cannot be added into a final ACL.

| Source | Fixed groups | Policy | Independent group savings | Expansions | Move wall s | Work-cap hits | Prepared states |
|---|---|---|---|---:|---:|---:|---:|
| bipartite_30_30 | `[[0, 30], [0, 30, 31], [0, 30, 31, 32], [1, 30]]` | greedy | `[2, 2, 2, 2]` | 643 | 0.01274 | 0 | 0 |
| bipartite_30_30 | `[[0, 30], [0, 30, 31], [0, 30, 31, 32], [1, 30]]` | distance1 | `[2, 2, 2, 2]` | 2954 | 0.01723 | 0 | 178 |
| bipartite_30_30 | `[[0, 30], [0, 30, 31], [0, 30, 31, 32], [1, 30]]` | distance4 | `[2, 2, 2, 2]` | 2954 | 0.01720 | 0 | 178 |
| complete_100 | `[[13, 18], [13, 18, 2], [13, 18, 2, 25], [2, 13]]` | greedy | `[0, 0, 0, 0]` | 4972 | 0.02311 | 0 | 0 |
| complete_100 | `[[13, 18], [13, 18, 2], [13, 18, 2, 25], [2, 13]]` | distance1 | `[0, 0, 0, 0]` | 72229 | 0.17411 | 3 | 1027 |
| complete_100 | `[[13, 18], [13, 18, 2], [13, 18, 2, 25], [2, 13]]` | distance4 | `[0, 0, 0, 0]` | 79343 | 0.17952 | 3 | 1179 |
| complete_40 | `[[11, 18], [11, 18, 26], [11, 18, 26, 7], [26, 11]]` | greedy | `[0, 0, 0, 0]` | 1643 | 0.00830 | 0 | 0 |
| complete_40 | `[[11, 18], [11, 18, 26], [11, 18, 26, 7], [26, 11]]` | distance1 | `[1, 1, 0, 1]` | 80000 | 0.16866 | 4 | 1703 |
| complete_40 | `[[11, 18], [11, 18, 26], [11, 18, 26, 7], [26, 11]]` | distance4 | `[1, 0, 1, 1]` | 80000 | 0.17557 | 4 | 1934 |
| grid_8x8 | `[[26, 17], [26, 17, 35], [26, 17, 35, 19], [17, 26, 16]]` | greedy | `[0, 1, 1, 1]` | 963 | 0.00613 | 0 | 0 |
| grid_8x8 | `[[26, 17], [26, 17, 35], [26, 17, 35, 19], [17, 26, 16]]` | distance1 | `[0, 1, 1, 1]` | 9481 | 0.01663 | 0 | 145 |
| grid_8x8 | `[[26, 17], [26, 17, 35], [26, 17, 35, 19], [17, 26, 16]]` | distance4 | `[0, 1, 1, 1]` | 9481 | 0.01600 | 0 | 145 |
| honeycomb_5x5 | `[[48, 15], [48, 15, 24], [48, 15, 24, 3], [50, 15]]` | greedy | `[0, 1, 1, 0]` | 1504 | 0.00552 | 0 | 0 |
| honeycomb_5x5 | `[[48, 15], [48, 15, 24], [48, 15, 24, 3], [50, 15]]` | distance1 | `[0, 1, 1, 0]` | 3871 | 0.00873 | 0 | 144 |
| honeycomb_5x5 | `[[48, 15], [48, 15, 24], [48, 15, 24, 3], [50, 15]]` | distance4 | `[0, 1, 1, 0]` | 3871 | 0.00875 | 0 | 144 |
| king_8x8 | `[[11, 19], [11, 19, 21], [11, 19, 21, 3], [38, 19]]` | greedy | `[0, 0, 0, 1]` | 1991 | 0.00816 | 0 | 0 |
| king_8x8 | `[[11, 19], [11, 19, 21], [11, 19, 21, 3], [38, 19]]` | distance1 | `[1, 1, 1, 1]` | 10245 | 0.02021 | 0 | 156 |
| king_8x8 | `[[11, 19], [11, 19, 21], [11, 19, 21, 3], [38, 19]]` | distance4 | `[1, 1, 1, 1]` | 10245 | 0.02015 | 0 | 156 |
| random_er_80_d8 | `[[27, 29], [27, 29, 1], [27, 29, 1, 17], [1, 27]]` | greedy | `[0, 0, 0, 0]` | 12631 | 0.02259 | 0 | 0 |
| random_er_80_d8 | `[[27, 29], [27, 29, 1], [27, 29, 1, 17], [1, 27]]` | distance1 | `[0, 0, 0, 0]` | 58292 | 0.08523 | 1 | 479 |
| random_er_80_d8 | `[[27, 29], [27, 29, 1], [27, 29, 1, 17], [1, 27]]` | distance4 | `[0, 0, 0, 0]` | 63442 | 0.09107 | 2 | 540 |
| regular_80_d3 | `[[27, 70], [27, 70, 74], [27, 70, 74, 13], [55, 70]]` | greedy | `[2, 2, 2, 1]` | 6168 | 0.01326 | 0 | 0 |
| regular_80_d3 | `[[27, 70], [27, 70, 74], [27, 70, 74, 13], [55, 70]]` | distance1 | `[2, 2, 2, 1]` | 13216 | 0.02181 | 0 | 126 |
| regular_80_d3 | `[[27, 70], [27, 70, 74], [27, 70, 74, 13], [55, 70]]` | distance4 | `[2, 2, 2, 1]` | 13216 | 0.02221 | 0 | 126 |
| watts_strogatz_80 | `[[0, 29], [0, 29, 56], [0, 29, 56, 77], [13, 27]]` | greedy | `[0, 0, 0, 0]` | 9316 | 0.01756 | 0 | 0 |
| watts_strogatz_80 | `[[0, 29], [0, 29, 56], [0, 29, 56, 77], [13, 27]]` | distance1 | `[0, 0, 0, 0]` | 23200 | 0.03643 | 0 | 151 |
| watts_strogatz_80 | `[[0, 29], [0, 29, 56], [0, 29, 56, 77], [13, 27]]` | distance4 | `[0, 0, 0, 0]` | 23200 | 0.03648 | 0 | 151 |

Tree module SHA256: `3e5b99d58475584a52ff4ccadcf0b30161c686f8c036bb50e38a85a3d106f22f`.
Contact caller SHA256 during this diagnostic: `1dd3fd5eb23a7416f5724035609c2c122309cdc7c803f94f5018fad9ab521a9e`. The caller used its default strictly reducing acceptance policy.

### Previously observed king singleton opportunity

On the same saved king instance and vertex 11 from experiment 013, fixed group
`[11]`, outer beam 1, alternatives 3, halo 2, region cap 512, one order, and
20,000 expansions:

- greedy: `[3060, 3061, 3062, 278]` to `[3060, 3061, 3062, 278]`, saving 0 qubits; 182 expansions, 0.000543 s, 0 prepared partial trees.
- distance1: `[3060, 3061, 3062, 278]` to `[3037, 3038, 350]`, saving 1 qubits; 722 expansions, 0.001946 s, 12 prepared partial trees.

Both complete embeddings passed the independent original-graph validator. This
is a replay of a development opportunity already identified in experiment 013,
not held-out evidence.

## Implementation and integration result

Implemented in
`packages/ember-qc/src/ember_qc/algorithms/factored/contact_trees.py` with no
changes to the contact caller, native constructor, or benchmark harness by this
agent. The module does not call the greedy builder, MM, busclique, or an IP
solver. It imports only standard-library data structures. The recommended first
globally fixed configuration is `frontier_width=1, witnesses_per_contact=2`;
the callable default remains width 4 so both values are explicit in comparisons.

Integration replaces the existing `_grow` call for that fixed policy:

```python
chain = grow_contact_tree(root, available, masks, required, ctx, budget,
                          size_cap, reverse=bool(attempt % 2),
                          frontier_width=1, witnesses_per_contact=2)
```

The existing root quota, alternative quota, frozen-contact construction, old
chain retention, and embedding-level acceptance remain caller responsibilities.
There is no greedy fallback inside the new proposal. Optional `diagnostics`
accumulates prepared/expanded-state counts, frontier and coverage peaks,
distance and unreachable prunes, completed-tree counts, and consumed BFS work.

Implementation detail: the frontier is trimmed after each prepared successor
is inserted, so it never stores more than its configured number of prepared
states. This can differ from selecting a beam after retaining a complete batch
of successors. Both procedures are incomplete heuristics; the distance bound
does not make either complete. Temporary witness paths and duplicate-state
bookkeeping are separate from the capped frontier.

The 36 fixed-group comparisons found improvements in 14 groups with greedy and
20 with either distance width. Width 1 added three K40 and three king proposals
and lost none of the baseline proposals in this small sample. Width 4 changed
which K40 group improved without increasing the count. The saved king singleton
check also recovered an existing valid shortening at the original root quota.

The cost is material: width 1 used 273,488 counted expansions versus 39,831 for
greedy, about 6.9 times as much. Summed independent move times were about 0.55
and 0.12 seconds, respectively. K40 and K100 consumed most of the additional
work, and multiple moves exhausted their equal 20,000-expansion allowances.
These measurements justify a small cumulative quality ablation of width 1;
they do not justify an end-to-end speed claim or an assumption that the broader
ACL gap is closed. The comparisons use only four early groups per instance and
one saved construction seed, so they are development evidence.

The implementation bounds each BFS by the remaining chain size and charges
each processed BFS vertex to the caller's budget. Set operations, path assembly,
sorting, and bookkeeping still take additional time. In the worst case each
prepared state explores the available region; repeated preparations explain
the observed overhead. A capped frontier does not by itself make a state
evaluation cheap. No unmeasured caching or speed improvement is claimed.

## Verification and final source

```sh
.venv/bin/python -m pytest tests/algorithms/test_contact_trees.py -q
```

**18 tests passed in 0.31 seconds**, with the existing `dwave-networkx`
deprecation warning. Tests establish a real missed-greedy mechanism at width
one, check the distance bound against tiny exhaustive connected extensions,
verify completed-tree invariants and coverage diversity, and exercise budget
exhaustion, expired deadlines, mixed labels, and retained completed output.
Invalid negative obligation masks and noninteger size caps are rejected rather
than entering undefined bit iteration or cap comparisons.

Final tree-module SHA256:
`bb7b9373d195d3a40d757a6e3500ed43aa3b8db7b8fdc7e8016e48f159a4bc7d`.
The first diagnostic's earlier module hash is preserved above. The only later
module change added validation for invalid masks and caps; valid-input search
behavior is unchanged.

### Root integration follow-up

The root agent integrated `tree_policy='distance'` with width 1 and two witnesses
per contact, leaving the other root/alternative quotas unchanged. One additional
integration test checks frozen chains, atomic replacement, work counters, and a
failing greedy-builder sentinel. The root reports **19 tree tests passing** after
integration. The root owns the frozen experiment 023 cumulative ablation of
legacy, boundary/group revision, and boundary/group revision plus distance trees;
it uses strictly reducing qubit acceptance so the separate equal-size acceptance
experiment does not confound this comparison. No outcome of that ablation is
claimed in this note.
