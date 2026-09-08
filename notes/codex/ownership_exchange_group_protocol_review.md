# Ownership-exchange seed groups for a first reach/cost diagnostic

2026-09-08. Design only, for all 34 deletion-closed 042 incumbents under one
predeclared rule. No new corpus outcomes were read and no algorithm was run.
Root separately specifies time/work limits, original-graph validation and the
adapter. This note selects neither a production scheduler nor a portfolio.

**Recommendation: a balanced, footprint-prioritized sequence of connected
groups of sizes one through four, capped at 512 total groups.** Retain the
existing ordinary neighbor-window patterns and their within-group vertex order;
include otherwise eligible zero-excess groups. Build and freeze one sequence
from the immutable supplied incumbent before either diagnostic routine searches.
Both routines receive that same ordered sequence and incumbent. The 512 cap
comes from the existing joint-refinement configuration, not observed ownership
outcomes; it is a diagnostic limit, not a completeness guarantee.

## Why neither literal reuse nor singleton/pair-only is sufficient

[`round_robin_groups`](../../packages/ember-qc/src/ember_qc/algorithms/factored/contact_groups.py)
uses a sound individual degree bound to rank excess, emits all positive-excess
singletons first, then contiguous neighbor windows for larger groups. Neighbors
include logical adjacency and physical adjacency between occupied chains. It
omits every group whose summed excess is zero. A 512-group prefix can therefore
contain only singletons, and some groups are physically too large for ownership's
64-original-site bound. Literal reuse is easy but these omissions confound a
first test of a proposer that can admit outside owners.

Zero initial excess is not an impossibility certificate for this proposer.
Admission can introduce the positive-excess chain that ultimately shrinks.
For a hand-derived deletion-minimal example, take maximum target degree five,
chains `V={a,q}`, `D={x,y}`, and singleton chains `B1..B6,F`. Source edges are
`V–Bi` for all six i, `V–D`, and `D–F`. Target edges are `a–q,a–x,x–y,y–f`,
`q–bi,x–bi` for i=1,2,3, and `a–bi` for i=4,5,6. The largest target degrees
are five at a and x. The degree bound for V is
`ceil((7−2)/(5−2))=2`, so its two-site chain has zero excess. Every original
chain is individually deletion-minimal. Nevertheless deleting q and transferring
x from admitted D to V yields valid `V={a,x}, D={y}`, reducing Q from 11 to 10.
This is a mathematical fixture, not a Zephyr observation or proposer execution.
It shows why the zero-excess **initial singleton** must not be deemed useless;
it does not show that ordinary group `(V,D)` or another route cannot obtain the
same reduction.

A deterministic singleton/pair rule can cheaply expose both individual seeds
and simultaneous ownership changes. A valid one-site chain cannot supply a
deletion seed, but it can be an essential pair partner or subsequently admitted
owner. Two singleton chains together have no eligible deletion seed and can be
skipped exactly. Physically adjacent pairs are preferable to logical-edge-only
pairs: nonlogical neighboring chains can block moves, and their occupied unions
are connected. However, a singleton/pair-only ordinary control excludes its
existing three- and four-chain reconstruction. Ownership may then admit up to
eight chains. A positive result would show reach only against that restricted
control, not beyond the full ordinary neighborhood. The recommended one-through-
four rule addresses that avoidable restriction without enumerating arbitrary
subsets.

## Exact finite rule

Let `L[v]=len(C[v])`. Build the physical quotient graph B: distinct logical owners
v,w are adjacent exactly when some original target edge joins C[v] and C[w].
Valid incumbent chains are connected and disjoint, so a center together with
any of its B-neighbors has a connected occupied union. Every original logical
edge is already represented in B; adding source neighbors does not enlarge B
under this validity precondition.

Use the existing ordinary neighbor ranking unchanged. Its individual bound is
`ell[v]=max(1,ceil((degree_G(v)−2)/(Delta−2)))` for `Delta>2`, and one otherwise.
Set `e[v]=L[v]−ell[v]`. Let r be the rank obtained by ordering ordinary integer
source labels by their textual `repr`, reproducing `_ordered` without constructing
or reusing a method-specific context.
Order centers and each quotient-neighbor list by `(-e[v],-L[v],r[v])`.
This preserves the existing neighbor-window universe. No group is rejected
merely because its excess sum is zero.

```text
pool[1] = [(v,) for every v with 2 <= L[v] <= 64]
pool[2], pool[3], pool[4] = empty
seen[k] = empty sets for k=2,3,4
depth = 0
active = ranked centers with at least one quotient neighbor
while active is nonempty:
    for k in (2,3,4):
        for v in active, preserving ranked center order:
            if depth + k - 1 <= len(neighbors[v]):
                raw = (v, *neighbors[v][depth:depth+k-1])
                key = tuple(sorted(raw))   # numeric labels; set identity
                if key already seen[k]: continue
                if sum(L[u] for u in raw) > 64: continue
                if all(L[u] == 1 for u in raw): continue
                save raw as the first representative for key in pool[k]
                mark key seen[k]
    depth += 1
    remove centers with len(neighbors[v]) <= depth from active

sort each pool[k] by (sum(L[u] for u in group), tuple(sorted(group)))
groups = empty
while any pool has an unread entry and len(groups) < 512:
    for k in (1,2,3,4):
        if pool[k] has an unread entry and len(groups) < 512:
            append its next saved representative to groups
```

For pairs the depth windows enumerate every physically adjacent pair once after
deduplication. Triples and quadruples use contiguous windows; they do not enumerate
all neighbor subsets. Centers of length one remain eligible for these larger
patterns when another member can supply a deletion seed. This retains connected
groups whose short center joins two longer chains that are not physically adjacent
to one another. All filters use the original full-chain footprint including the
site that might later be deleted. No articulation/contact test is performed in
group preparation; the accepted proposer owns those charged seed checks.

The saved ordered representative matters. Ordinary `_repair` tries only bounded
chain orders (the group tuple, then its reverse with the current limit), so
numerically sorting the **payload** could silently change its reconstruction
search. Only the deduplication and sorting keys are canonicalized. The ownership
routine subsequently normalizes its own initial set as specified. Before the
512 cap, the proposed pools contain every connected, at-most-64-site group
eligible for ownership that literal untruncated `round_robin_groups` would
generate, with the same first ordered representative; additional zero-excess
groups are included. The final prioritized prefix is deliberately different.

If B has E edges, the prefilter pools contain at most n singleton groups,
E distinct pairs, 2E triple windows and 2E quadruple windows: at most `n+5E`
groups before the final 512 cap. Also `E <= Q*Delta/2`. The shrinking active
sequence gives `sum_v degree_B(v)=2E` center-depth visits. This is linear in
quotient edges apart from sorting, not combinatorial subset enumeration.

## Cost, interpretation and self-critique

Group preparation requires an occupied ownership map, an occupied target-edge
scan, ranked neighbor lists and complete pool ordering. Ordinary scan/sort work
is `O(|V_H| + Q*Delta + (n+E) log(n+E))` and space is `O(Q+n+E)`; computing
Delta needs only target row lengths. The graph, set, comparison, sorting and
copying work must be accounted by the adapter and included in its unchanged
deadline. The existing production grouping helper is not work-metered, so
calling it does not make that cost free. The accepted isolated core still
performs its own once-per-query private entry/owner validation; this may duplicate
a global preparation pass, but must not repeat it per group. An interrupted
preparation cannot claim to have selected the prescribed shortest-footprint
prefix or fall back to the partially discovered list. Preserve its partial cost
and report that no frozen group sequence was completed.

Save the exact ordered 0–512 group vector, its hash, counts by size, complete
eligible-pool counts, deduplication/filter counts and preparation completion/cost.
The declared vector and actually inspected search prefix are distinct. A first
returned candidate ends the isolated query; no outcome may reorder the suffix,
renew a per-group allowance or select a different sequence. The same rule and
limits apply to every input, including inputs with no eligible groups. Neither
graph names nor prior MM/candidate results enter it.

Self-critique: footprint order is a cost heuristic, not a proven contraction
likelihood. It can spend early work on tight small chains while useful long-chain
seeds occur later. Alternating sizes prevents list-level starvation only while
those streams exist; common work/deadline limits may still stop before a later
size or center is searched. Added zero-excess seeds can be expensive failures.
The 512 cap, contiguous windows, original connected-patch rule and ownership's
separate 8/64/depth/state limits still exclude many moves. None of these exclusions
may be reported as global contraction infeasibility.

A positive result means ownership found a Q−1 contraction that the particular
ordinary search did not find on the shared tested sequence and allowances.
It does **not** establish strict containment of either full neighborhood, lower
end-to-end ACL or acceptable pipeline cost. A singleton/pair-only pilot, if root
chooses that narrower scope instead, must be labeled accordingly and followed
by a prespecified one-through-four comparison before making a claim about the
current ordinary refiner. With the recommended rule that larger-size control
is present immediately, but a later full-pipeline experiment is still necessary
to measure group displacement, accepted-state changes and final quality. No
second sequence should be selected from this diagnostic's outcomes.

Source references: `contact_groups.py:9–75`, `contact_repair.py:69–75`,
`contact_repair.py:389–401` (bounded chain orders), and `pilot.py:276–289`
(existing 512-group, one-through-four configuration). The accepted ownership
specification remains SHA-256
`8d870c3a2e16615574ad018eec266258200bd7740b7cbd2450d47a47d299f82f`.
