# A055: permit locally minor-preserving degree-three elimination

Design only; no implementation, source diagnostic or constructor call. The
fixed ancestor is A053 `site_transfer_construction.py`
SHA256 `801432d5e5d1fc1918e7eb933a3af443064ee0833030a5b962773f2b50f700a1`.
A054 is not promoted: on its selected16, core excess increased134 Q while
lifting excess decreased104, leaving+30 Q and slightly higher total time.
That partition motivates retaining some degree-three simplification, without
claiming it identifies which individual reduction caused a loss.

**Hypothesis.** Allowing degree-three elimination only when two current
neighbors already touch may retain useful simplification while ensuring that
every filled core is a source minor. Retain all degree≤2 eliminations. One
fixed source rule applies everywhere; it never chooses a completed embedding,
uses family labels, checks prior Q, or switches constructor configuration.

A materially different alternative would keep every A053 degree-three move
but prioritize minimum newly created fill ahead of degree/rank. This might
change which junctions survive, but still admits independent-neighborhood
star→triangle steps and adds ordering uncertainty. Select the eligibility
rule below instead: it supplies an exact local structural certificate without
a fitted numerical threshold. Do not test or combine the ordering alternative
in this experiment. Merely requiring fewer than three new fill edges is
algebraically the selected rule, not a separate alternative.

## Exact policy and proof

Keep original component anchors, source/target ranks, normalization and the
heap key `(current_degree, fixed_source_rank, vertex)` from A053. A surviving
unprotected vertex `v` is eligible precisely when

```text
degree(v) <= 2
or (degree(v) == 3 and at least one edge joins two vertices in N(v)).
```

The neighborhood is in the **current filled graph**, including earlier fill.
For eligible degree3, choose a sorted existing neighbor edge `(a,b)` for the
source-only certificate and let `c` be the third neighbor. Contract `v–c`:
the existing `a–b` plus the two contracted edges give exactly the clique on
`{a,b,c}`; all other surviving edges are unchanged. For degree2, contract
into its smaller-labeled neighbor; degree0/1 may delete the branch set.
Repeated contractions/deletions compose by transitivity even when the
supporting `a–b` was earlier fill. The diagnostic witness choice does not
influence physical construction. Degree3 with independent neighbors fails
this particular local contraction test: it is not a general non-embeddability
certificate. The optimal-core Q bound does not bound the native heuristic's
chosen output or guarantee a feasible, constant-Q, or cheap reverse lift.

```text
initialize the same filled adjacency, anchors and ranks
heap = all currently eligible vertices, with unchanged degree/rank keys
while heap has a timely current entry:
    discard entries with stale degree or newly false eligibility
    S = sorted current neighbors; F = absent pairs of S only
    atomically finish the reduction row: add F, delete v, journal(v,S,F)
    affected = surviving S
    for each newly created edge (a,b):
        add every surviving common neighbor of a and b to affected
    for each affected vertex in fixed source-rank order:
        if currently eligible: enqueue its current degree/rank entry
construct every retained core vertex once using unchanged A053 core path
reverse the exact journal with unchanged transfer / ordinary / blocked repair
validate original full graph and actual returned time
```

**The common-neighbor update is required.** Adding fill `a–b` can make a
third vertex eligible without changing its degree and without that vertex
neighboring the removed vertex. The old neighbor-only requeue is insufficient.
For each new edge, scan the smaller endpoint adjacency (label tie-break),
check membership in the other endpoint adjacency, and deduplicate the affected
set. All membership tests observe the completed row's graph. Only endpoints
lose `v` or gain degree; only common neighbors acquire a new internal neighbor
edge. Thus this affected set is complete. Recheck eligibility on every pop;
no eligible-prefix truncation or stale boolean memo is allowed.

There are at most two new fill edges per permitted degree3 row, one per
degree2 row. Each degree3 predicate checks at most three neighbor pairs.
Additional update work is bounded by
`sum_(a,b in F) min(deg(a),deg(b))` membership scans plus affected-set sorting/
enqueues. This can still be large at hubs. Charge every new eligibility
inspection, pair membership, scanned common-neighbor member and queued entry
through the same live engine/global work meter; sorting/copying and all setup
remain inside the original wall deadline. Report these added reduction
counters separately without adding them twice to global scans. Existing
native-internal work remains outside that wrapper scan count.

Keep the 20M global allowance, all A053 core settings, at most one native call,
64/50k/1M transfer limits, 1M/5M blocked-repair limits, original absolute deadline,
fill-release provenance, pending-port guards, cleanup and atomic physical
adoption. Stop on interrupted reduction without constructing an incomplete
core; retain completed journal plus interrupted-stage diagnostics. Do not
renew work/time or return an alternative ancestor output. Identity changes
will state this predicate explicitly; no pilot registration is proposed yet.

## Cheap prospective falsifier

First propose one stdlib source-only pass over all34 frozen053 inputs, original
manifest order, seed0, **five seconds and two million source operations per
input**, including new reduction and composed source-minor checking. Compare
against the already saved complete053/054 source-only records rather than
rerunning constructors. Charge node/adjacency/heap/witness-member operations;
parsing, sorting and serialization costs remain explicit. Preserve all
34 records and interrupted/unknown statuses. Report core/journal hashes,
removed-degree counts, created/synthetic fill, eligibility rejections,
nonlocal activations, update work and witness validity. No target access.
No change from A053 or an unexplained old-record mismatch stops progression.

Before any candidate screen, use only a handful of structural checks:
existing-edge degree3 contraction; independent-neighbor rejection; older-fill
support/provenance; the nonlocal activation case below; and interruption
without partial-core admission. Verify the complete incremental heap order
against a tiny direct full-eligibility rescan oracle, not another copy of the
same requeue code. Transfer/repair and the shared physical validator stay fixed.

A hand-checkable activation graph has vertices `v,a,b,x,c`, edges
`v–a,v–b,x–a,x–b,x–c`, and otherwise disjoint K5 cliques containing `a`, `b`
and `c`, respectively. It has17 vertices/35 edges. The protected anchor is
`a` or `b` (degree6); `v` is the only degree2 vertex. Initially `x` has an
independent degree3 neighborhood. Removing `v` creates `a–b`; `x` must now
enter the heap although it was not a neighbor of `v`. Its next elimination
can use the older fill edge as support. Reverse ownership of the two rows'
created fill must restore exactly the original edges.

If the source-only gate and targeted checks pass, propose a separately frozen
small screen: the first **six** inputs whose new core or journal differs from
A053, plus the first unchanged input, all in original manifest order (fewer
if unavailable). This is at most seven structures/fourteen fresh A053/A055
calls, seed0,60 seconds on one host. Fix inclusion solely from reductions
before A055 physical outcomes; retain every excluded row and every output.
No follow-on panel follows automatically. Reject relevance if reductions do
not change; reject this fixed prototype for lost reach or unfavorable aggregate
quality/cost on the selected scope. Report every regression; no outcome-based
acceptance rule, mixture, cap change or claim about omitted inputs.

**Self-critique.** Conventional minor-preserving reduction is not novelty.
The useful A053 Petersen reductions may have independent degree-three
neighborhoods and therefore remain excluded, while triangle-supported fills
can still concentrate expensive demands. Fewer fill edges do not imply
fewer physical sites. The rule may preserve wheel simplification but sacrifice
other useful junction elimination; the source-only table cannot settle that.
Common-neighbor invalidation also adds real setup/reduction cost. A small
selected screen is an early falsifier, not evidence of all-class superiority,
seed stability, MM runtime parity or globally optimal lifting. Seek root review
of this exact policy before implementation or any diagnostic call.
