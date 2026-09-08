# A052: one virtual guide for original-only construction

Design only, before implementation. The fixed ancestor is the rejected literal A051 prototype; physical requirements remain original-only. This is one evolving construction, not a choice between completed filled/original embeddings. No registration or corpus run is proposed yet.

**Hypothesis.** A filled elimination order contains useful spatial information even when its synthetic contacts need not be realized. Giving an insertion one already placed virtual neighbor as a distance guide may prevent A051's zero-contact placements from scattering, while retaining cheaper original-core requirements. The exposed cycle's41 zero-placed-original-neighbor attempts and failed119-vertex/Q266 prefix motivate this test; they do not establish its cause or this remedy.

## Exact proposed first policy

Keep the filled elimination journal and protected anchors unchanged. For a reverse-inserted vertex `v`, its virtual neighbors are `journal_neighbors(v) − original_neighbors(v)`. They are not physical requirements or pending demands. Among those currently placed after inherited preparation, choose the one with smallest fixed source tie rank as the **single guide**. If none is placed, use no guide. This also applies when the fixed local repair reinserts an old owner; a temporarily released guide is unavailable. No family or stored input ID is inspected.

For an original edgeless core, first compute a deterministic spanning forest of the **filled core**: start each component at its maximum-original-degree vertex, resolve ties by source rank, and use a frontier ordered by decreasing original degree then source rank. Discover each new vertex through the first already reached neighbor, saving that parent. Place core vertices in this discovery order. The parent is the guide; all such edges are synthetic because the physical core is edgeless. This places every survivor without re-reduction and keeps one guide available except at component roots. For a non-edgeless original core, retain A051's one native call unchanged. Its physical graph may be disconnected; this first policy does **not** reorganize native's component placements. Later expansion still uses virtual guidance. That limitation is intentional to avoid changing two constructors at once.

For a guide chain `Cw`, compute one complete unweighted multi-source BFS on the original target, ignoring occupancy, to obtain `d(q,Cw)`. Define `g(q)=max(0,d(q,Cw)−1)`; unreachable sites have infinity. With no guide, `g(q)=0` and perform no BFS. Distance is a ranking signal only: it never reserves sites, creates a contact, changes a frontier guard, or rejects a candidate solely for being distant. Occupied target sites may participate in this distance calculation even though routing still obeys its original free-site rules.

Use the following exact keys, with the same64 screened roots and four rebuilt branches:

- Initial free-root pool: `(-direct_original_contacts, g, original_pressure_price, -free_degree, target_rank)`.
- Frontier-valid screened roots: `(-direct_original_contacts, original_domain_key, g, original_pressure_price, target_rank)`.
- Complete valid private insertions: `(total_Q, original_domain_key, g(root), target_rank)`.
- Edgeless-core placement: `(g, -free_degree, target_rank)`, retaining the original pending-frontier acceptance check.

`original_domain_key` is the unchanged sorted negative singleton-domain-size vector. Final physical Q remains the first complete-insertion criterion. Direct contact count is only an original-routing heuristic; these keys do **not** prove that the best original connection cost survives the64/four truncation. Placing guidance ahead of pressure in the root pool is deliberate: when no original neighbor is placed, distant sites otherwise have lower pressure and can defeat a guidance tie-break. Existing paths, ownership cuts, pruning, matching-free repair policy and physical validation are unchanged.

```text
compute the same filled journal and original-only R
construct original core once, or place its edgeless survivors by filled forest
for each ordinary/private insertion:
    run inherited original-demand preparation
    choose one currently placed virtual guide by the fixed rule
    complete its target-distance BFS, charging the live allowance
    use distance only in the fixed root/complete-insertion ranking keys
    retain original contacts, connectivity, disjointness and pending-port guards
    commit at most the existing insertion result before the original deadline
```

Every BFS target-edge examination consumes one inherited scan; seeding its chain is also charged. Copying, sorting and queue operations count in elapsed time and obey the original deadline. Distances are local to one prepared insertion and reused only for its root branches; there is no cross-call cache or refresh state. A repair's BFS consumes the same remaining query/cumulative/global work as its other operations. Interrupted BFS aborts that insertion privately; no partial distance map, reordered prefix or uncharged retry is used. A call costs at most `O(|Cw|+|V_H|+|E_H|)` time and `O(|V_H|)` storage. This can itself consume the20M cap; fewer routing searches must pay for it. One guide avoids up to three full maps per insertion and potentially higher filled-core degree, at the cost of ignoring other virtual neighbors.

## Fixed small diagnostic and self-critique

First check a tiny target path with a virtual guide at one end: with no placed original neighbor, closer frontier-safe roots must outrank distant zero-pressure roots; a distant result remains valid when that is the only feasible placement. Check that physical required adjacency is exactly original, that no-guide keys recover A051, and that a BFS interruption preserves entry/R. Verify filled-forest ordering places all edgeless-core survivors, and changing guide ownership invalidates the next call's distance rather than reusing it.

Then run exactly the four already frozen A051 reach inputs—star128, wheel128, subdivided K5 and exposed cycle126—once under the same20-second diagnostic allowance and unchanged20M/repair caps. Compare to their saved A051 statuses/Q, without historical timing inference. The cycle must complete rather than merely consume more work, and its final Q must improve on A051's already266Q partial count. Retain every outcome; failure ends this prototype before34 inputs. Report guidance calls/scans/wall separately as overlapping subtotals, root changes if cheaply observable, all original-valid final/prefix mappings, Q and total work/time. The unchanged star is a no-fill control.

**Self-critique.** A single guide may draw a vertex toward the wrong side of a later separator. Hop distance ignores occupancy and bottlenecks, so physically close chains can still be hard to connect. A filled forest can crowd an edgeless core; hard original domains can override guidance in the final shortlist. Local clustering may improve the cycle but worsen multi-neighbor graphs. Full-target BFS cost may defeat the intended runtime benefit, and this limited prototype leaves non-edgeless disconnected core placement untouched. These are conventional spatial ordering and distance heuristics, not a novelty claim. Only a successful fixed reach result would justify considering a separately frozen comparison against one fixed ancestor; no per-input output selection is allowed.

**Requested parent review before code:** accept or revise the one-guide rule, its position ahead of pressure in pool ranking, the edgeless-core forest order, and the charged full-target BFS. They define one explicit prototype and should not change after its outcomes.
