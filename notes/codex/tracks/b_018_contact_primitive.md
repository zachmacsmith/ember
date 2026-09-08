# B018: exact small movable-contact gate

2026-09-08, saved before code. Authorization is only one joint contact proposal and three fixed small calls. No constructor, sweep, adaptive-price policy, registry or panel is implemented. The [replacement review](b_construction_replacement_review.md) supplies the hypothesis and prior-art caveat.

Inputs are simple symmetric integer-keyed source/target adjacency, nonempty connected owner-site lists (overlap permitted), one oriented witness `(q,r)` for every canonical source edge `(u,v)` with u<v, and one/two adjacent changed source edges. Source and rebuilding order is ascending integer order; changed edges and terminal processing use lexicographic source-edge order. Physical order is `Random(0).shuffle(sorted(target))`; oriented-coupler ties use `(rank[q],rank[r])`.

Build each owner's canonical BFS spanning tree using physical-rank neighbor order. Remove the changed-edge obligations, then repeatedly delete nonterminal leaves in physical-rank order. If no obligations remain, the private retained tree is empty. Repeated same-owner terminals have separate obligation counts but one physical site. Unchanged witnesses remain compulsory, including those incident to outside owners.

Candidate region is the closed one-hop neighborhood of all selected old trees. Enumerate its actual directed couplers. Build endpoint-attachment distances from each retained tree; for an empty retained tree, its singleton attachment estimate is the site's increment. Common ranking occupancy contains outside chains and every selected retained tree. Node increment is zero on the growing owner's current tree, otherwise 2 if another owner occupies the site and 1 if not. Prices are exactly lambda=1. Keep the old coupler first, then the three cheapest different couplers by summed endpoint estimate and oriented physical rank. Examine the Cartesian product in pool order, at most 16 combinations.

For each combination, rebuild selected owners in source-rank order. Occupancy uses unchanged outside chains, completed selected trees and not-yet-rebuilt retained trees. Start an empty tree at its first required terminal; attach subsequent terminals in source-edge order by node-weighted Dijkstra, with heap `(distance,physical_rank,site)`, first-parent ties and no equal-distance parent replacement. Prune nonterminal leaves again. Verify every tree and every original-edge witness, then compute actual unions: `Q=sum|C|`, `O=sum(max(0,owner_count-1))`, energy `Q+O`.

If entry O=0, only O=0 with strictly lower Q is eligible. Otherwise only strictly lower energy is eligible. Select the best complete eligible combination by `(energy,O,Q,witness-rank-vector)`; this is one neighborhood search, with no evolving intermediate commit. Unselected lists stay byte-for-byte ordered. Return at most one atomic proposal after a final deadline check. Any work/deadline interruption discards the whole query, preserving its examined-combination diagnostics and unchanged entry. No interrupted best prefix is published.

Each call has the same 5-second absolute allowance and 100,000 units. Each inspected adjacency entry/site/terminal/ownership entry is charged; heap/sort and administration remain in wall time. Validation, copying, pool generation and final materialization are included. Exact last-unit completion may publish after only the final clock check; incomplete work is unknown, not failure proof. Full original-graph validation remains separate from the weaker private contact/tree certificate.

The immutable input JSON will record these cases before any call:

| Case | Source; target | Initial chains; witnesses; changed edges |
| --- | --- | --- |
| Path gain | 0–1–2; 0–1–2–3–4 | C0=[0], C1=[1,2,3], C2=[4]; 01→(0,1), 12→(3,4); change 01,12 |
| Optimal star | Both stars centered at 0 with leaves 1,2,3 | Every Cv=[v]; 0i→(0,i); change 01,02 |
| Impossible cycle | Triangle 0,1,2; path 0–1–2 | C0=[0], C1=[1], C2=[1,2]; 01→(0,1), 02→(0,1), 12→(1,2); change 01,12 |

The path's fixed witnesses force Q≥5; moving contacts permits Q=3, but the actual fixed pool must find a gain without adjustment. The star checks repeated center terminals and cannot beat Q=4. The triangle's private state has Q=4/O=1; a path has no triangle minor, so neither initial nor returned overlapping chains may receive feasible credit. These hand facts are not new measured outcomes.

Before the three calls, targeted checks cover trimming/duplicate obligations, exact union energy, contact preservation, failed/deadline rollback, and prohibited imports. Preserve all failures. Small success demonstrates only this specified update's reach; it does not distinguish it from all prior joint reconstruction, and pool truncation or greedy attachments may still defeat the hypothesis. Stop after recording the three calls for root review.
