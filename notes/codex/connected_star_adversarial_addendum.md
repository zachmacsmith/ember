# Connected-center design: adversarial mathematical review

2026-09-08. The one-root choice remains a substantial search restriction even
if matching becomes cheap. The proposed distinct-site capacity bound and exact
domain compression are sound under the conditions below, but neither establishes
useful coverage within 25,000 auxiliary work units. This is a mathematical
review of the [connected-center specification](connected_star_relocation_spec.md)
and [proposed compression amendment](connected_star_domain_compression.md).
No solver call, implementation, or change to experiment 037 accompanies it.
Reviewed SHA256 values are `f7f411a24fafe9a25dfa7a715ad472f8a465d496be7643d9349086a5cb2c71ab`
for the specification and `16666b5d3863f553724c4ae1e92bb3bfd98dc3177b6bd28b0318c8a56f65e55b`
for the compression amendment.

## A seven-vertex target defeats the prescribed root choice

Take the source path `x—a—c—b—y` and select `{c,a,b}`, freezing `x,y`.
The target has vertices `A1,A2,u,v,B,X,Y` and exactly these edges:

```
X—A1—A2—u—v—B—Y
 \____/
```

The extra edge is `X—A2`. A valid incumbent is
`C[x]={X}`, `C[a]={A1,A2}`, `C[c]={u,v}`, `C[b]={B}`, `C[y]={Y}`.
The selected cost is five. With two singleton leaves, strict descent permits
at most two center qubits. Physical maximum degree is three.

The frozen leaf domains after release are `B_a={A1,A2}` and `B_b={B}`.
Choose stable labels so the equal-cost seed stream uses `X` before `Y` and
examines `A1` before `A2` among `X`'s neighbors. Concretely, logical labels
`c=0,a=1,b=2,x=3,y=4` and physical labels
`A1=0,A2=1,u=2,v=3,B=4,X=5,Y=6` provide that ordering.
The first available two-hop root emitted through `A1` is `A2`.
It has two available physical neighbors, `A1,u`, giving root score two—the
specified upper bound. The scan stops there.

Every valid center must touch the sole eligible `b` site `B`, so it must contain
`v`. A connected center containing both `A2` and `v` needs the three-vertex path
`A2—u—v`, exceeding the ceiling. Thus no subsequent lookahead, matching repair,
or BFS can rescue that fixed root. Yet `T={u,v}`, with `a` at `A2` and `b` at
`B`, is valid and lowers selected cost from five to four.

The same target illustrates nonmonotonicity: at `T={A2}` one leaf can be matched
to `A1`; growing to `{A2,A1}` consumes the last available `a` site and reduces
maximum matching size from one to zero. A larger footprint is not uniformly
better. This constructed example proves a search limitation, not its frequency
on Zephyr or the performance of an unimplemented operator.

## Couplers and distinct leaf sites are different capacities

For a second example, form a target from the edge `r—s`, with both `r,s`
adjacent to both `p,q`. Add an old center path `a—b—c—d`, pendant sites
`a',b',c',d'` at the corresponding path vertices, and the bridge `p—a'`.
There are no other edges. Maximum degree is three. The source is `K1,4`;
its valid incumbent uses `{a,b,c,d}` as center and the four pendant sites as
singleton leaves, costing eight qubits. Strict descent allows center size at
most three.

At the partial center `T={r,s}`, there are four external physical couplers but
only two distinct available sites: `P(T)={p,q}`. With one center addition left,
the edge-boundary relaxation permits capacity `4+(3−2)=5`, enough for source
degree four. Distinct-site capacity permits at most `2+(3−2)=3`, which cannot
host four singleton leaves. The proposed site bound correctly rejects this
footprint despite the passing edge bound. Another center elsewhere may work;
this rejection is conditional on retaining the current footprint.

The specification's edge bound is a safe necessary relaxation, not a mistaken
feasibility certificate. Its root score already counts distinct physical
neighbors, and its successor score explicitly requires genuinely new sites.
An implementation must not replace those sets with coupler counts, domain-edge
counts, or the sum of class-domain sizes. A site eligible for several leaves
still has capacity one. Inflated counts can distort the optimistic ranking even
when a final exact matching prevents an invalid commit.

For fixed released availability and `x in P(T)`, exactly

```
P(T union {x}) = (P(T) minus {x}) union
                ((N_H(x) intersect A) minus (T union P(T))).
```

The new part has at most `Delta−1` sites since `x` already neighbors `T`.
Thus the amendment's `k <= |P(T)| + r*max(0,Delta−2)` is a sound necessary
condition. It assumes connected one-site growth and fixed availability.
**Keep P unfiltered.** If only eligible leaf sites are counted, the added center
site may itself be ineligible; no eligible site is then removed, and as many as
`Delta−1` eligible sites may be added. Substituting that filtered set into the
same `Delta−2` formula could incorrectly prune a feasible extension.

## Compression is exact; cheap augmentation is a separate question

The amendment's equivalence holds: independent leaves with identical frozen
neighbor sets have identical singleton domains, including the degree filter.
A class of multiplicity `c_g` therefore needs that many distinct eligible sites.
A unit-capacity physical-site assignment to classes can be expanded into an
individual leaf assignment, and every individual assignment contracts back.
The demand of a class subset is `sum(c_g)`, not its number of classes.

The proposed augmenting search must permit previously filled classes to exchange
assigned sites along alternating paths. For Hall accounting, include every site
in the neighborhood of the reachable classes, including sites a class already
owns. For example, an underfilled class of demand two owning its sole eligible
site has neighborhood size one. A literal residual-flow traversal can omit that
site because its class-to-site arc is saturated; counting only reached right
vertices would give the wrong deficiency. Explicit neighborhood counting or
marking those owned sites avoids the ambiguity. This is a representation pitfall,
not a flaw in the amendment's stated capacitated-assignment equivalence.

Stable expansion to individual leaves preserves feasibility, but compression
does not automatically preserve the same selected physical sites or future
search trajectory. Exact equality of frozen obligations, no selected leaf-leaf
edges, and unchanged availability are essential. Source traversal, class
construction, assignment updates, rollback and final individual certificates
still require charged work. The amendment correctly avoids promising linear
work from compression alone or silently selecting a new initialization policy.

## What the 25,000-unit share can and cannot support

At the current global limit, 25,000 units cover **all** auxiliary queries,
setup and refresh for the entire refinement call. Building ownership costs
`n+Q` records; later attempts receive only the remainder and the current ordinary
visit's unused allowance. Work units also have unequal elementary costs, so a
5% operation allowance is not a 5% elapsed-time guarantee.

For illustration, 126 singleton leaves around an eleven-qubit old center do not
rule out a seven-to-ten-qubit replacement by the degree-20 bound. A seven-qubit connected
center has at most 128 external edges and hence at most 128 available boundary
sites. Materializing that conservative duplicated-leaf domain table uses
`126*128 = 16,128` entries. Four full copies of such a state would already require
64,512 record operations, before selection, routing or certification. This
diagnoses an unsuitable eager-copy representation; it is not a cost lower bound
for every implementation or evidence that a Z12 footprint attains that boundary.
Reversible edits and identical-domain compression can avoid those copies.

Even a single demand class can be costly if every unit augmentation restarts at
the first site: assigning 126 leaves may inspect `1+...+126 = 8,001` sites just
through repeated prefix scans. With heterogeneous domains (`g` near `k`), domain
construction and matching may remain substantial. Root enumeration, duplicate
walks and failed steering BFS can spend the remainder without a proposal.

A favorable small-domain, short-route case plausibly fits the allowance; the
specification supplies no uniform coverage guarantee for high-degree centers.
The unresolved prioritization question is whether fixing one root produces
enough useful neighborhoods to justify this machinery. The counterexample shows
why cheaper assignment alone cannot answer it. Any later revision or diagnostic
must be separately specified; current policy and frozen results stay intact.
