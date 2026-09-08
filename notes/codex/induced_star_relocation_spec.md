# Joint singleton placement for an induced star

2026-09-08. New local-search hypothesis and self-critique, saved before
implementation. This extends candidate6's connected-region idea within one
evolving embedding. No code, embedding call or performance result is claimed
here. The fixed spectral constructor and current contact refinement remain the
development candidate; experiment033 did not justify adopting its direct
singleton policy.

## Mechanism and exact restricted problem

Let `c` be a logical center and `L` a subset of its logical neighbors with no
edges between members of `L`. The selected source subgraph on `S={c} union L`
is an induced star. Freeze every chain outside `S`, release all old selected
chains provisionally, and seek a one-qubit chain for every selected vertex.
The selected old chains need not already be singletons. Require at least one
old selected chain to contain more than one qubit: a complete proposal then
strictly reduces total qubits, regardless of its contact-redundancy change.

For each selected source vertex `v`, compute an eligible physical set `B[v]`:

```
B[v] = physical vertices free after releasing S
       intersected with the boundary of every frozen logical neighbor chain
```

An empty intersection of obligations means all available physical sites, not
an empty eligible set. Membership uses actual original-target couplers. A
frozen neighboring chain may be contacted anywhere along that chain.

For a proposed center site `q in B[c]`, form a bipartite graph with logical
leaves `L` on the left and physical sites on the right. Leaf `u` can use exactly
the sites in `B[u] intersect N_target(q)`, excluding `q`. A matching covering
every leaf gives the complete proposed selected embedding. All selected chains
are singletons, all center-leaf contacts exist, there are no leaf-leaf demands,
all frozen-boundary contacts hold, and the matching enforces distinct ownership.
The old embedding outside `S` is unchanged. This proves validity of a complete
proposal for a simple undirected loopless source and target.

Conversely, every all-singleton replacement of this chosen block with center
at `q` induces such a covering matching. Thus, with complete eligible sets and
an exhaustive root search, this procedure decides the restricted replacement
problem exactly. It does not decide general minor embedding, optimize the
choice of logical block, or guarantee finding a reduction after truncation.
No integer-programming solver is necessary.

One selected vertex with logical degree greater than the actual maximum target
degree cannot become a singleton. Exclude such leaves and skip such centers
using this proved necessary condition. Stronger necessary conditions include
nonempty leaf candidate lists, enough distinct available neighbors of `q`,
and the existence of a covering matching. These conditions use graph structure,
not family labels, source identifiers or observations of MM.

## Why this differs from the failed033 proposal

033 searched for a singleton replacement of one chain while all other chains
remained fixed. Its added equal-size relocations and shared-budget cost produced
7 improvements,22ties,5regressions and one more qubit overall on the34input
development screen. The independent audit supports retaining the old global
policy. These results do not establish that wider joint relocation is useful.

Here neighboring logical vertices can change their physical sites together.
The restricted star structure turns their distinct-site competition into a
matching problem. It can consider more than the current generic2–4chain groups
without enumerating every product of leaf choices. It cannot rely on a
singleton movement alone creating a useful later opportunity: the complete
block must immediately reduce qubits.

This is one proposal within the same refinement of one incumbent. It neither
runs multiple constructors nor selects the best output of independent embedding
algorithms. No per-family dispatch or portfolio is proposed.

## Selection, budget and integration questions still to settle

Select one independent subset of a center's neighbors by a deterministic
structural rule, prioritizing chains that can contribute a qubit reduction.
Do not enumerate independent sets or tune separate choices per graph family.
Any selected source edge between two leaves invalidates the matching reduction;
test the induced-star condition explicitly before a proposal.

Eligible-set construction can start from the smallest frozen-neighbor boundary
and inspect target ownership/adjacency. With no frozen obligations, represent
the available set implicitly. For each root, the right side of the matching
has at most its physical degree, which keeps this part small on Z12. Cache
only within an immutable incumbent/block query initially; stale ownership and
boundary caches must never survive a committed move without an exact refresh.

Root ordering, block-size/scan limits and the scheduling share of the existing
contact-search budget require a separate frozen integration specification before
implementation. Charge eligible-set construction, root screening, every matching
edge examined, validity work and all failures. A matching routine that checks
time only between roots cannot promise a strict per-call deadline. Truncation
must mean no proposal, with the unchanged valid incumbent retained.

Avoid adding a new full sweep merely because it is easy to implement. The033
and023 results show that a useful isolated proposal can lose through reduced
coverage elsewhere. The initial discriminating test should replay fixed valid
incumbents and compare the new operation with the existing joint reconstruction
on the same blocks and one shared total allowance, before a full-pipeline screen.
Do not select whichever operator wins per input after the comparison.

## Self-critique before implementation

This is a highly restricted all-singleton neighborhood. Dense sources often
have small independent neighborhoods or degrees above the target limit; long
high-degree hubs cannot shrink to one qubit. Freezing omitted neighbors may
leave every eligible root set empty. Gains may be concentrated on sparse
structures already helped by existing matching or subgraph-placement methods.
These are limitations of the move, not grounds for family-specific exceptions.

Choosing a maximal independent leaf subset can exclude a smaller useful block:
adding a leaf adds obligations and competition. An unsuccessful larger block
does not certify failure of its subsets. A bounded deterministic subset rule
therefore needs both a complexity bound and an explicit coverage limitation.
Do not describe it as searching every induced star.

Computing eligible sets for many leaves can cost more than ordinary rerouting.
Matching may reject most roots, and global free-root enumeration may dominate
on a4800vertex target. Any improvement must survive total-work and end-to-end
time comparisons, including setup; sparse MM cases already expose our runtime
deficit. The move must be rejected or revised if it displaces more useful
existing proposals.

All successful proposals have the same selected qubit count `|S|`. Finding a
maximum-redundancy covering matching would require weighted assignment and
additional work. A first complete matching suffices for strict qubit descent,
but can leave worse contacts for later search. This tradeoff must be specified,
not hidden in a claim that the local procedure optimizes final quality.

Bipartite matching and star-subgraph placement are established mathematical
ideas. This note claims only a particular restricted neighborhood and its
validity argument. A prior-art review is required before attributing novelty
to its use for minor-embedding refinement. Its worth here depends on a
counterexample to the current neighborhood, exhaustive small-case validity,
and cumulative improvements under fixed general budgets.

## Discriminating evidence required next

1. Give a small valid original-target embedding where single-chain singleton
   relocation fails for every selected chain, but a joint induced-star
   replacement reduces qubits. Independently enumerate the relevant placements.
2. Review primary literature for matching-based minor embedding and local
   simultaneous contact relocation; document overlaps and unresolved attribution.
3. Specify deterministic block/root selection and complete work accounting,
   then compare a simple implementation with exhaustive injective assignments
   on tiny graphs, including leaf-leaf edges, occupied sites and interruptions.
4. Only then test fixed saved development incumbents, preserve all zero-gain
   and negative cumulative cases, and decide whether a full-pipeline comparison
   is warranted. Generalization still requires new source instances.

Status: design/critique only. No implementation or new experiment has begun.
