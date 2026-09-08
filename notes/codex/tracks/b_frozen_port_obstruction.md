# B013 design: certify an unusable frozen contact before rebuilding

Pre-code diagnostic hypothesis, 2026-09-08. B012 spends one million repair units inside its first release block `[53]`, without inserting ER66 or reaching the other 20 blocks. A cheap necessary obstruction may reject such a block before routing. This would preserve its release pool/order, first-return policy, root limits and global/local allowances. No B013 candidate or new solver invocation is authorized at this checkpoint.

## Exact predicate and scope

For one existing ordered block `K`, let `F = E without K` be the frozen incumbent and `A = V(target) minus union(F)` the available sites **after the whole release**. Recompute each frozen chain's distinct free boundary

`B(w) = {q in A : q is adjacent to some site in F[w]}`.

Its remaining demand after the first insertion is

`P(w) = source_neighbors(w) minus (F.keys union {v})`.

This includes neighbors in released `K`, which have not yet been restored. A demand solely for `v` does not qualify. Every frozen owner with nonempty `P(w)` and singleton `B(w)={q}` protects site `q`. Let `Z` be the union of these protected sites. Include the required endpoint itself: the protecting owner need not be a different chain. With `R = source_neighbors(v) intersect F.keys`, reject the block if any `r in R` satisfies `B(r) minus Z = empty`. Record the offending endpoint, complete boundary and protecting owner/demand sets. An empty `B(r)` is also an obstruction. Otherwise return **not rejected**, never “feasible.”

```text
for K in B012's unchanged complete block vector:
    F = immutable entry with whole K removed
    recompute available sites and all frozen free boundaries
    Z = sole free ports of frozen owners with pending demand after v
    if any frozen required endpoint has no boundary site outside Z:
        save its certificate; skip only this release block
    else:
        the existing v-first reconstruction would remain eligible
```

**Proof limit.** To contact frozen endpoint `r`, the new chain must occupy some site in `B(r)`. If every such site is protected, that occupation removes a frozen owner's last free port while it still has an original pending demand. It violates the existing intermediate frontier guard. Frozen owners cannot grow, relocate or be pruned. Private preparation and new-chain growth only consume initially available sites; later pruning of new sites cannot create a free site outside the post-release set `A`. Thus the rejected **first-v/frozen-outside primitive** cannot succeed. This is not a certificate against arbitrary simultaneous reconstruction, another insertion order, another release set, or future movement of frozen chains. Passing does not establish connectivity, matching feasibility or eventual restoration.

## Fixed cheap diagnostic before implementation

Use only the saved B011 ER66 input and all 21 blocks already published by B012; preserve their order and include every result. No candidate/helper/constructor call, graph generation or MM input is needed. Implement an independent stdlib set classifier after review, scanning original target adjacency. Use a five-second total deadline and 500,000 counted owner/site/adjacency/source-obligation operations for the whole classification, including decoding/setup time in wall. Check around loops and final recording. Preserve partial completed classifications and interruption; do not infer that an uninspected block passes. Report exact inspected/rejected/unknown counts, certificates, earliest surviving block, work and wall. Do not change the block ranking from these results or raise the cap.

Fixed tiny checks will distinguish: (1) a required endpoint's sole site protected by another frozen owner; (2) self-protection when the endpoint still needs a later neighbor; (3) releasing an occupied site opening a second, unprotected contact, which must pass; and (4) a frozen owner's demand solely for `v` versus demand for a released member of `K`. The former is excluded from `P`, the latter retained. For cases (1)/(3), use source edges `(0,1),(0,4),(2,3)`, entry `1:[0],2:[2],4:[4]`, new `v=0`, release `K={4}`. Target edges `(0,1),(2,1),(4,5)` give the obstruction; adding `(0,4)` opens the alternative. For case (2), use source edges `(0,1),(1,2),(0,4)`, target edges `(0,1),(4,5)`, entry `1:[0],4:[4]`, and the same new vertex/release. For case (4), use target edges `(0,1),(2,1),(4,5),(1,5)` and the cases (1)/(3) entry/release. Source edges `(0,1),(0,2),(0,4)` permit the shared contact; replacing `(0,2)` by `(2,4)` makes frozen owner 2 protect it. These test the predicate, not the greedy routing algorithm.

**Self-critique.** This detects only singleton-port obstructions. Multiple-site capacity conflicts, disconnected contacts and root/path truncation remain. Some rejected cases already fail quickly in frozen preparation, adding redundant cost. Recomputing full boundaries per block costs roughly `O(Q_F Delta + |F| + sum(degree(w)))`, with bitsets/sets and record construction also charged to wall. Skipping an early block may expose a later expensive failure rather than a recovery. The fixed classification can support a bounded skip experiment only if it finds an early certificate cheaply; actual ER66 reconstruction still needs its own subsequent gate. This is a necessary-condition optimization of the existing neighborhood, not a new embedding algorithm or novelty claim.
