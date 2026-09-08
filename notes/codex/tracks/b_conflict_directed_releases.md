# B016 proposal: choose releases from complete-block contact obligations

Design only, 2026-09-08. B015 skips two impossible first insertions but then inserts ER66 privately and cannot restore owner 31. The saved original graph shows why that release has a stronger problem: frozen owner 72 is adjacent to **both** selected vertices 66 and 31. Its after-release boundary is `{1991,2002}`, and site 1991 must stay free for frozen owners 53/55's remaining future demand. One usable physical site cannot belong to two disjoint selected chains. This is a general boundary-capacity obstruction, not an exception for these labels.

**Hypothesis.** A blocked reconstruction should select a release that addresses its constrained logical contacts before minimizing released Q. Use B015 as the explicit fixed comparison ancestor. Change only construction of its candidate block vector: reject complete-block capacity violations, then prioritize releasing the constrained required owners or their actual protecting competitors. Keep the same capped owner pool, one/two-owner blocks, first-valid return, frozen rebuilding, ordinary roots/routing, first-v component check and deadlines. No candidate is implemented here.

## Capacity certificate after the whole release

For candidate `K`, let `W=K union {v}`, frozen chains `F=E without K`, and `A=V(target) minus union(F)`. Recompute each frozen owner's distinct free boundary `B(r)` from `A`. Define:

- `d(r) = |N_source(r) intersect W|`: selected logical neighbors whose contacts must exist when **all W** have been restored.
- `p(r) = 1` if `N_source(r) minus (F.keys union W)` is nonempty, otherwise 0: demand remaining **after the complete block**.
- `Z_W`: every sole boundary site of a frozen owner with `p=1`.

For every frozen owner, necessary conditions are

`|B(r) minus Z_W| >= d(r)` and `|B(r)| >= d(r)+p(r)`.

Each of `r`'s distinct selected logical neighbors must own a different site adjacent to frozen chain `r`. Sites in `Z_W` must remain free; a remaining future demand additionally needs an unoccupied boundary site. A single free site can satisfy several frozen owners' future guards, so **do not sum their guard counts into a global distinct-site demand**. These conditions concern the complete selected block with all outside chains frozen and the existing final frontier guard. They do not assume that sites protected solely while `K` is absent remain reserved after `K` is restored. Do not substitute `Z_W` into B015's different, first-v component filter.

Any violated row certifies rejection. Passing is inconclusive: different rows share boundary sites, selected chains must connect, and restoration can still fail. A sum of row deficits is not a qubit lower bound or a count of independent physical deficits. No such numerical sum is used as an ACL estimate.

## Fixed selection rule

Before release, evaluate these rows once with `W={v}` and `F=E`. Let `B0` be the required owners with violated rows. Let `C0` contain the actual owners protecting sites on `B0`'s boundaries, excluding the corresponding endpoint itself. This identifies a failed obligation and its protecting owners from source/target adjacency alone.

Retain B012/B015's existing pool of at most two critical competitors and four required owners and its at-most-21 subsets. Record any `B0` or `C0` owner omitted by that existing cap. Complete the capacity assessment of every block under the live repair allowance; interrupted assessment publishes no reordered prefix. Discard only certified violations. Sort the survivors by:

1. Tier 0 if `K` intersects `B0`; tier 1 if it does not but intersects `C0`; tier 2 otherwise.
2. Decreasing number of directly released owners in `B0`.
3. Increasing released Q, block size, then the existing ordered pool positions.

Thus a direct response to a constrained required contact precedes collateral release of an incidental neighbor. When there is no such baseline obstruction, the tier/coverage terms tie and the original released-Q ordering remains. The priority is a hypothesis: it does not prove direct release cheaper or better than releasing competitors.

```text
only after ordinary connected insertion returns no candidate:
    build the unchanged capped pool and all one/two-owner blocks
    identify baseline constrained required owners and their protecting owners
    recompute complete-block capacity for every candidate release
    if interrupted: retain the unchanged committed entry
    order certified-surviving blocks by bottleneck tier, then released footprint
    run the unchanged B015 private rebuilding loop; return its first valid block
```

All assessment, copying, failed blocks and certification stay inside **1M repair units per blockage, 5M repair units total, 20M global units**, with unchanged nested matching/propagation/growth limits and the original deadline. There is no new owner cap, restart, family rule, alternate constructor or successful-output comparison. Assessment needs at most 22 boundary/demand passes (baseline plus 21 releases), each bounded by occupied-site adjacency and source-incidence work; it may consume a material part of the query and must be metered explicitly.

## Shared static diagnostic bound

Before classifier code, fix **five seconds and 2,000,000 counted owner/site/target-adjacency/source-incidence operations total** for all tiny checks plus the baseline and at-most-21 release blocks on **both** supplied states. Input decoding, graph setup, pool preparation, sorting and record construction remain in measured wall. Record per-stage work, every completed or partial block and every uninspected index. An interrupted capacity assessment is unknown and cannot publish a completed reordered vector. The diagnostic uses no candidate methods or local-helper calls.

Freeze complete-40's original `propagating-tree-ports`, seed-0 task identity and `FAILURE/construction_blocked` status before inspecting its release outcomes, alongside ER66's already fixed entry. Exclude deadline/work-limit failures. Add tiny cases that distinguish selected demand `d` from post-block demand `p`, and demonstrate that one protected free site can satisfy multiple future guards without an invented global free-site count.

## Cheap falsifier and critique

Before any implementation, independently check the certificate on: the existing tiny occupied-endpoint witness; a fixed triangle collision with source edges `(0,1),(0,2),(1,2),(3,4)`, entry `1:[1],2:[0],3:[3]`, new vertex 0/release `{1}`, target edges `(0,1),(0,2),(3,2),(1,4)`; and the same target with `(0,4)` added. The first triangle has one usable site for two selected contacts at frozen owner 2 and must reject; the added site removes that particular obstruction. Also check source path `0–1–2`, entry `1:[1],2:[0]`, target path `0–1–2`, release `{1}`: owner 2's pending demand for released 1 is counted in `d`, not incorrectly reserved as future `p`.

Classify the fixed pool and capacity-priority vector on **both** already exposed B011 blocked states, ER66 and complete-40, without reconstruction. Exclude the complete-100 work-limit state: it is not an eligible ordinary blocked return. Freeze this additional state before reading its release outcomes; retain every inadmissible, eligible or unclassified block. A useful result must address constraints without merely selecting a label, and must expose some viable bounded neighborhood. If later implementation is authorized, the cheap reach gate remains the tiny witness and actual saved blocked states under normal allowances, not a larger-cap rescue or new constructor rerun.

This is preferable to simply filtering each later insertion while pretending every current chain is frozen: newly inserted 66 is movable, so such a certificate can be too strong for the actual restoration primitive. Complete-block capacity refers only to the truly frozen outside owners and all selected demands at once. Its limitation is the opposite: it can miss connectivity and shared-site constraints entirely. Prioritizing a bottleneck hub can demand a long, expensive reconstruction; a competitor pair may have been easier. Baseline rows can also reflect an obstruction that ordinary chain growth would solve, so this policy remains blocked-only. The proposed ordering can still spend all work on its first admissible block. These are conventional constraint reasoning and local rerouting ideas, not a novelty or all-class superiority claim.
