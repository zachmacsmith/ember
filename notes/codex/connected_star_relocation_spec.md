# Connected-center induced-star refinement

2026-09-08. Design and self-critique only, saved before implementation. No
embedding call or performance measurement accompanies this note. The separately
specified [singleton-center core](induced_star_implementation_spec.md) remains
unchanged. This is a possible later extension of the same local neighborhood,
not a second constructor or a rule selecting algorithms by graph family.

The extension removes the center's singleton degree restriction: selected
leaves still become singletons, but their center may occupy a connected set of
several qubits. For each fixed center set, matching still solves the remaining
leaf assignment exactly. Choosing a small useful center set remains a bounded
heuristic problem. This distinction is the central proof boundary.

## Fixed-footprint certificate

Let `G` be the simple undirected loopless source, `H` the corresponding target,
and `C` a validated incumbent with nonempty, connected, pairwise-disjoint chains.
Choose a center `c` and at least two neighbors `L` that are mutually nonadjacent
in `G`. Write `S={c}∪L`, `k=|L|`, and `F_v=N_G(v)\S`. Freeze every chain
outside `S`. The selected old chains may have any positive lengths.

Available physical vertices after provisional release are

```
A = V(H) \ union(C[w] for w not in S).
B_l = {q in A : for every w in F_l, N_H(q) intersects C[w]},  l in L.
```

An empty `F_l` gives `B_l=A`. These are source-contact domains, using actual
target edges, and remain fixed throughout this one block query. A physical
degree test `degree_H(q) >= degree_G(l)` is an additional safe domain filter;
exclude a leaf globally when `degree_G(l) > Delta=max_degree(H)`. Do not apply
the singleton degree exclusion to the center.

For a proposed nonempty connected center footprint `T⊆A`, define

```
covered_c(T) = {w in F_c : some edge of H joins T to C[w]}.
P(T) = (N_H(T) \ T) intersect A.
D_l(T) = B_l intersect P(T).
K(T) = bipartite graph with distinct logical-leaf and physical-site identities,
       and edge (l,q) exactly when q belongs to D_l(T).
```

There is a valid replacement with **this exact center set** and singleton
leaves if and only if `covered_c(T)=F_c` and `K(T)` has a matching covering all
`k` leaves. A covering matching `M` gives `C'[c]=T`, `C'[l]={M(l)}`, and leaves
all outside chains unchanged.

Necessity follows from the original embedding conditions. For sufficiency,
connectivity of `T` and singleton leaves supplies connected chains; availability
and matching give disjoint ownership; the matching edges realize center–leaf
contacts; the domains and center coverage realize every selected-to-frozen
edge. No leaf–leaf source edge remains to check because `S` is an induced star.
Extra physical edges among selected leaves are allowed. A leaf can touch its
center through several physical couplers, and a frozen chain can be contacted
at any of its physical vertices. Logical and physical labels must never share
an untagged matching namespace.

This equivalence does not decide which source block or center footprint to
choose. A matching on incomplete domains can certify a complete valid placement,
but its failure is not proof of infeasibility. The proposed growth score below
requires a completed **maximum** matching for the currently represented full
boundary domains; a partially computed matching must not supply an exact
deficiency or a Hall-set certificate.

## Exact qubit ceiling and safe necessary bounds

Let `Q_old=sum(|C[v]| for v in S)`. A replacement has selected cost `|T|+k`.
Accept only strict total-qubit reduction and impose

```
s = Q_old - k - 1,
1 <= |T| <= s.
```

This is a net block ceiling, not `old_center_length-1`: shortening several leaves
can legitimately fund a larger center. If `s<1`, the selected neighborhood has
no strict reduction. A final acceptance may reduce contact redundancy; strict
qubit descent remains compatible with the existing `(Q,-redundancy)` objective.

A connected `t`-qubit center has at least `t-1` internal target edges. Therefore

```
degree_G(c) <= |delta_H(T)|
             = sum(degree_H(q) for q in T) - 2*|E_H(T)|
             <= (Delta-2)*t + 2.
```

Distinct logical neighbors require distinct outside physical owners, so the
first inequality is necessary even when those neighbors have long chains. For
`Delta>2`, a safe center lower bound is
`max(1,ceil((degree_G(c)-2)/(Delta-2)))`. Reject if this exceeds `s`. For
`Delta<=2`, use the actual boundary inequality without division by `Delta-2`;
do not reuse a formula outside its domain.

For illustration only, at `Delta=20` a degree-126 center needs at least seven
qubits by this bound. An incumbent containing an eleven-qubit center and 126
singleton leaves permits `s=10`, so a seven-to-ten-qubit replacement is not
excluded. This is a necessary-capacity calculation, not an embedding or
benchmark result. It establishes why a degree-above-20 center must not be
discarded from the generalized neighborhood.

During growth, with `r=s-|T|` steps remaining, a safe additional prune is

```
degree_G(c) > |delta_H(T)| + r*max(0,Delta-2).
```

Adding one vertex adjacent to the existing footprint changes the edge boundary
by `degree_H(x)-2*|N_H(x)∩T| <= Delta-2`. The bound is optimistic: repeated
contacts to the same owner and unusable outside vertices can make it very loose.
It does not assert that enough edge boundary implies a feasible matching.

## Source block and starting site: one fixed construction

Retain the proposed attached-attempt schedule: after a failed ordinary group
visit, use its first logical vertex as center, at most once per center per pass.
An accepted ordinary move suppresses this attempt. No independent center sweep
or extra group allowance is proposed. The future generalized operator applies
the same rule to every eligible center, including cases where its final center
is a singleton. It must not run a singleton method and a connected method and
choose the better output.

Drop only the old `degree_G(c)<=Delta` restriction. Retain degree-at-most-Delta
leaf candidates and rank them by decreasing `|C[l]|-1`, increasing source
degree, then stable logical rank. Greedily retain mutually nonadjacent leaves.
Use a blocked-neighbor set while selecting, rather than testing every retained
pair repeatedly: inspecting each accepted leaf's source adjacency is bounded
by `Delta`. Explicitly verify the final induced-star condition. Require `k>=2`
and the exact strict-Q ceiling above. There is no arbitrary 20-leaf cutoff;
`k` can exceed `Delta`. The selected independent subset is still only one
greedy subset and may be infeasible when a smaller subset would work.

Choose **one** initial center vertex using a deterministic root stream:

1. If a frozen center-neighbor chain exists, its available one-hop boundary is
   a necessary superset of at least one vertex of any feasible center footprint.
2. A frozen neighbor of a selected leaf gives a two-hop necessary superset of
   at least one center vertex. Prune intermediate leaf sites only by that leaf's
   complete frozen-contact eligibility.
3. Choose the cheapest estimated such stream by the singleton-core rule
   `Delta**h * chain_length`, with its fixed hop/logical-rank tie breaks. If
   there are no external obligations, stream available target vertices in
   stable physical-rank order. Deduplicate on first discovery; charge duplicates.

The first rule uses one frozen center neighbor, **not the intersection of all
center-neighbor boundaries**. A multi-qubit center may meet those contacts at
different vertices, so imposing the singleton intersection would invalidate
the extension.

For the same reason, do not apply the singleton core's center-site eligibility
mask to individual footprint vertices: neither `degree_H(q)>=degree_G(c)` nor
all frozen center contacts at one site is required. Only leaves retain their
singleton eligibility tests; the center is certified collectively.

While scanning roots, use the cheap optimistic score

```
root_score(q) = number of distinct adjacent frozen center-neighbor owners
                + min(k, number of available physical neighbors of q).
```

Choose the highest score, with first discovery breaking ties. The score ignores
leaf-specific domains and is only a routing heuristic. It is bounded above by
`min(degree_G(c),Delta)`, so stop immediately if that upper bound is attained;
otherwise finish the generated stream subject to work/deadline limits. Root
selection may consume the query allowance without leaving enough for growth;
record this failure instead of silently granting extra work. Once chosen, the
root never changes and no second footprint search starts in this query.

## Connected growth guided by matching deficiency

For the current footprint, compute a maximum matching `M(T)`, its size `nu(T)`,
and

```
deficit(T) = (k - nu(T)) + |F_c \ covered_c(T)|.
```

Each unit counts a currently missing logical obligation: one unassigned leaf
or one uncovered frozen center neighbor. Zero deficit gives the fixed-footprint
certificate. It is a search score, not a lower bound on future added qubits or
an ACL surrogate. Final acceptance always uses actual assigned qubits.

Maintain domains on the available boundary rather than routing separately to
each old leaf chain. Leaves with identical `F_l` have identical static domains
(their degree is `|F_l|+1` in an induced star), so cache one eligibility decision
per distinct frozen-obligation set and physical site. Keep the individual leaf
identities for matching. This equality-based reuse applies to any source;
it is not a rule recognizing stars by a stored family label. It reduces domain
work when obligations coincide, but does not make all matching edges free.

At each growth step:

1. Examine the available one-step frontier `X=P(T)`, including sites currently
   assigned to a leaf. For each `x`, cheaply count newly exposed eligible
   physical leaf sites and newly covered frozen center neighbors. Existing
   boundary sites must not be counted as new resources. An optimistic lower
   bound on the successor deficit is
   `k-min(k,nu(T)+new_sites(x)) + uncovered_after_x`.
2. Retain the four lowest-bound candidates; use more newly exposed sites for
   the current deficient leaf set, then stable physical rank, as tie breaks.
   Four is a proposed fixed engineering limit before results, not an optimized
   constant or a completeness claim. This is a shortlist of one-step edits to
   one state, not four independent construction trajectories.
3. Temporarily add each shortlisted vertex, repair the matching to a new
   maximum, and obtain its exact deficit. Restore the query state between
   candidates. Among completed candidates that strictly lower deficit, choose
   the smallest deficit, then greater matching size, then stable physical rank.
4. If no completed shortlisted successor reduces deficit, use one bounded BFS
   to steer through a possible zero-gain gap. Start simultaneously from the
   footprint, traverse only available sites, and limit depth to `s-|T|`. A goal
   either reaches an uncovered frozen-center boundary or exposes a new eligible
   boundary site for a leaf in the current alternating-reachable deficient set.
   For a leaf goal, its proposed leaf site must be outside both the current
   footprint and the reconstructed BFS path. A site already in the old leaf
   boundary is not a new matching resource. Use shortest distance then the
   existing stable traversal order. Add only the first new vertex on this route,
   recompute the exact matching, and reconsider all obligations next iteration.
5. If no complete route/extension can be obtained within the remaining budget,
   stop this query. Otherwise continue with the chosen larger footprint. No
   footprint shrinking, root change, backtracking, restart, or alternative
   leaf subset is included in this first design.

The deficient leaf set in step 4 comes from alternating reachability starting
at all unmatched leaves of a completed maximum matching. Follow unmatched edges
from leaves to physical sites and matched edges back to leaves. With no
augmenting path this supplies a Hall-deficient set in the current domain graph.
Its existence explains a shortage of jointly available sites; merely increasing
the domain of one already satisfied leaf need not help. Recompute it after
growth. It guides a route but does not guarantee that the eventual footprint
can preserve every domain and make the matching complete.

The BFS step may temporarily increase deficit by consuming a matched leaf site.
These are internal partial proposals only; the incumbent embedding is still
untouched. Growth is bounded by `s`, so the internal search cannot cycle by
revisiting the same footprint size. A zero-deficit footprint terminates the
query at once; no search for a second complete result or redundancy-optimal
matching follows.

## Matching is not monotone under center growth

This is a required invariant, not a minor implementation detail. Growing
`T` to `T∪{x}` removes `x` from the matching's right side. If `x` was matched,
its leaf becomes unmatched. A larger connected footprint can consequently
support a **smaller** maximum matching. Never treat `nu(T)` as monotone or keep
a leaf assignment to a vertex now owned by the center.

There is nevertheless a useful incremental bound. Old boundary-domain edges
survive except those incident to `x`; new right-side sites lie among neighbors
of `x` outside the old footprint and boundary. Since `x` has a neighbor in `T`,
there are at most `Delta-1` such new sites. Remove `x` and its possible matched
edge, add the new site domains, then run deterministic augmenting-path searches
until no augmenting path remains or matching size reaches
`min(k, number_of_eligible_right_sites)`. At most `Delta` successful augmentations
are needed: at most one repairs the deleted matched site and at most
`Delta-1` exploit new sites. An unsuccessful completed augmenting search proves
maximal cardinality for that updated graph. Work-limited failure does not.

Use reversible query-local updates and charge domain edits, augmenting-edge
examinations, restoration, and any replay of the chosen successor. The global
incumbent and published owner cache must never be mutated to evaluate a trial.
If restoration cannot finish within allowance, discard the entire local query;
do not continue from a partially restored matching. Storing a best complete
successor or rebuilding it later is permissible only with its copying/replay
work included. The complexity below allows a charged replay.

## Pseudocode and atomic acceptance

```
connected_star_query(incumbent, center, context, owner_cache, shared_budget):
    select one independent leaf set; charge all inspected source records
    compute selected Q, frozen obligations, and strict center-size ceiling s
    reject only proved structural/capacity impossibilities
    require owner_cache describes this exact immutable incumbent
    choose one root from the necessary stream with the fixed optimistic rule
    T = {root}; construct complete current boundary domains
    compute a maximum matching; abandon if interrupted
    while remaining shared allowance and common deadline permit:
        if every leaf matched and every frozen center neighbor covered:
            check complete original-edge local certificate and exact Q/R delta
            if all checks finish and deadline permits: return certified proposal
            return no proposal
        if |T| == s or safe boundary bound fails: return no proposal
        evaluate up to four ranked one-step extensions with reversible matching
        choose one exact-deficit improvement if available
        otherwise obtain one first step from the bounded deficiency-guided BFS
        if no complete next state: return no proposal
        T, matching, domains = that one next state
    return no proposal
```

Before committing a proposal, verify all selected chains against original adjacency:
membership, nonempty connected center, singleton/distinct leaves, center–leaf
contacts, and all frozen contacts. Independently count exact old/new logical-edge
couplers incident to `S`, once per logical edge. The delta may be negative on
a strict shortening. Require the current incumbent identity and deadline to
still match, then atomically replace all selected chains. Only after commit
refresh the dedicated owner cache by removing all old selected owners before
adding any new ones. An interrupted refresh disables subsequent auxiliary
queries while retaining the already committed valid embedding. Query domains
and eligibility decisions never survive a changed selected block or incumbent.

Partial matching, incomplete scores, truncated BFS, or incomplete certificates
produce no published move. Failure says only that this bounded query found no
proposal. Even a fully exhausted greedy root/footprint trajectory is not proof
that the block lacks a smaller replacement. The native final graph validator
remains in place after any future integration.

Use distinct diagnostics for a proved failed matching on one fully represented
fixed footprint and `heuristic_no_proposal` for the whole growth query. A BFS
with one predecessor per site also need not discover every route whose final
leaf witness avoids its path; alternate paths to the same endpoint are not
enumerated. Neither BFS exhaustion nor exhausting the four-way shortlist may
be reported as exhaustive block infeasibility.

## Work, space, scheduling, and runtime scope

This design seeks bounded practical cost; it has not established MM-scale wall
time. Keep all work inside the same native deadline, original active-visit and
global limits, and the existing auxiliary share `floor(max_expansions/20)`.
Cache setup, refresh, failed source selection, root scans, all matching/BFS
work, scoring and certificates consume that share; it never resets per pass.
Use the singleton-core ownership discipline, but not its singleton-only center
eligibility restriction or a persistent leaf-domain cache.

The first singleton core has a 2,048-unit query cap. It cannot be assumed to
support larger connected blocks at unchanged coverage: domain/certificate work
alone can exceed it. For a **separately approved future diagnostic**, propose
using the active visit's remaining allowance and remaining auxiliary allowance
as the connected query cap, without an additional 2,048-unit cutoff. At current
settings this is at most 25,000 units over the whole call, often much less after
owner setup or earlier work. This is an explicit change in allocation, not a
free extension of the singleton core's experiment. One early query may consume
the entire auxiliary share. No such policy is authorized for integration by
this note, and no current frozen experiment is changed.

Count one unit per source/chain record, occupied qubit, physical adjacency scan,
distinct domain-class eligibility check, examined matching edge, matching-state
record edit/copy/restore, or queue operation. Physical adjacency and one leaf
domain test perform at most `O(Delta)` elementary membership checks. Center
coverage must use adjacent-owner membership and cached counts, not an uncharged
scan through all potentially high-degree center obligations for every site.
If bit masks span many machine words, charge their word operations or use
explicit bounded scans; the old at-most-21-bit assumption no longer applies.
Sort costs and allocations remain wall-time costs and have to be measured.

Let `N=|V(H)|`, `Q` occupied qubits, `d=degree_G(c)`, `g<=k` distinct leaf
obligation classes, `b_t<=min(N,Delta*t)` eligible boundary sites, and
`e_t<=k*b_t` matching edges at footprint size `t`.

| Component | Bound before work truncation |
| --- | --- |
| Owner build | `O(n+Q)` records and `O(Q)` stored owners |
| Leaf selection | `O(d log d + k*Delta)` with charged candidate/adjacency screening |
| Frozen obligations | `O(d+k*Delta)` source records |
| Necessary root stream | `O(N)` emitted roots; up to seed-chain length times `Delta**h` walk records before deduplication |
| Root boundary matching | at most `Delta` augmentations, each `O(k+e_1)` |
| One successor matching repair | at most `Delta` augmentations plus one failed search, each `O(k+e_t+ k*Delta)` in the enlarged graph |
| Main boundary-domain storage | worst `O(k*b_t)`; identical-domain sharing may reduce this to `O(g*b_t+k)` |
| Four trials and a chosen-state replay | a fixed multiplier of the successor cost, charged each time |
| One complete steering BFS | `O(N*Delta)` adjacency work, plus site eligibility work and charged path checks; radius and global budget may stop it much earlier |
| Growth iterations | at most `s-1`, with no backtracking or independent restarts |

Ignoring BFS and domain construction, the conservative matching term over
growth is `O(k*Delta**2*s**2)` for fixed four-way lookahead. It is polynomial,
not a favorable constant-time claim. A high-degree block, many distinct frozen
leaf domains, or repeated Hall failures can still make it unusable. Root/BFS
deduplication uses `O(N)` memory, with matching state `O(k+e_s)` and bounded
trial logs. Lazy caches must be discarded at query end. All interruption checks
occur inside scans and augmenting paths, before charging more work; bounded
counters plus cooperative deadline checks are not a hard real-time guarantee.

## Relationship to existing methods and novelty

The matching certificate extends the singleton-center argument by contracting
a fixed connected target footprint conceptually. Solnon's LAD already uses a
root-conditioned bipartite neighborhood graph with variable domains and a
covering matching. Independent leaves make the condition sufficient for the
restricted selected block; allowing a connected center does not make matching
a new technique. See the [independent prior-art review](induced_star_relocation_review.md)
and Solnon's [author paper](https://liris.cnrs.fr/Documents/Liris-4568.pdf).

CMR rebuilds a vertex model from neighboring models using weighted shortest
paths, root selection, and path unions. Its localized version also grows
searches toward contact obligations. It explicitly considers transferring
singly used path portions to neighboring vertex models. Therefore connected
growth, contact routing, and some coordinated ownership changes are established
ideas. See Sections 3 and 5 of
[Cai, Macready and Roy](https://arxiv.org/html/1406.2741).

The proposed operational distinction is simultaneous injective assignment of
many movable singleton neighbors while a connected center grows, with an exact
fixed-footprint feasibility certificate and a Hall-deficiency routing signal.
It uses disjoint available space and a valid frozen outside embedding throughout
the query; no overlap-weighted CMR constructor, MM call, busclique call, or IP
solver is part of this design. These distinctions define the experiment; they
are not proof of novelty. Matching-constrained Steiner routing and related
local-minor search may already contain this combination and need further review
before a publication claim.

The current generic proposer constructs chains sequentially inside a bounded
region, retaining only a small prefix beam: `contact_repair.py:255–290` and
`323–400`. It has no exact many-leaf distinct-site assignment stage. Its
`_add_boundary_sites` at lines 124–180 intersects **each chain's** frozen
contacts; applying that intersection to a multi-qubit center would be wrong.
The older `trees.py:85–137` already contains CMR-like distance/root/path-union
logic. A future implementation should use only the actual-adjacency context,
owner cache, and bounded matching/queue primitives; it need not call that router.

## Self-critique before implementation

The mathematical extension is stronger than the actual search. One greedy leaf
subset, one optimistically selected root, monotone footprint growth, four
one-step trials, and nearest deficiency routing can all discard useful choices.
Even though the fixed-footprint formulation contains singleton centers as a
special case, this search does not exhaust the first singleton core's roots or
guarantee retaining its successful placements. No claim of a strict practical
superset follows.

Matching deficiency is local and can mislead geometry. Exposing many sites for
the same constrained subset may leave another subset unreachable; nearest
Hall-resource growth can consume a crucial leaf site or a narrow passage.
Plateau steps allow some bridges but cannot undo an unfortunate earlier center
vertex. A near-optimal high-degree center may require deleting an interior old
vertex, changing the chosen root, or moving leaves as longer chains. Those
possibilities are excluded here. Fixed frozen contacts can make every explored
footprint infeasible despite a better larger-block move.

The large-block certificate and matching may exhaust allowance before any
proposal. Exact reuse for identical obligations helps a structural special
case but provides no guarantee on heterogeneous neighborhoods. A 5% work share
does not imply 5% elapsed time: work units differ, repeated matching/restoration
adds Python overhead, and the current whole pipeline already has substantial
runtime deficits. Using the entire remaining auxiliary share for one query can
reduce useful ordinary-group coverage. Both033 and023 showed why isolated
proposal gains are insufficient evidence for cumulative quality.

Every accepted move reduces Q immediately, but its arbitrary covering matching
and changed center geometry can damage later opportunities. The036 correction
also showed that altered physical assignments and extra refinement savings do
not automatically improve final ACL. Do not optimize this design against one
high-degree star witness or select it only for favorable source names.

## Falsifiable next diagnostic, requiring separate authorization

Before code, independently review the fixed-footprint proof, boundary bounds,
nonmonotone matching update, and the proposed changed query allocation. Then
use tiny original graphs to enumerate connected center subsets and injective
leaf assignments: compare the certificate with an independent complete-graph
validator, including a matched site consumed by growth, a restoration failure,
distinct frozen obligations, extra physical leaf edges, and source leaf edges
that must reject the block. A constructed witness proves only that mechanism.

After correctness checks, use **all 34 saved 036 valid incumbents** with one
fixed scheduling rule, identical shared total work/deadline, and no MM inputs
or new constructor. Report source degree, selected-leaf count, distinct-domain
count, center ceiling, charged work by stage, unsuccessful queries, and actual
wall time. Degree/size strata are reporting categories only. Do not remove
low-degree or zero-gain inputs from the comparison.

The useful initial falsifiers are: high-degree eligible blocks consistently
truncate before complete matching/certification; incremental matching or BFS
dominates elapsed time without new reductions; or a cumulative replay saves
fewer total qubits than the unchanged control because other groups lose work.
If any occurs, retain the failure evidence and revise the mechanism or reject
its allocation before a full-pipeline trial. A smaller selected block or a new
root strategy would require a separately saved general rule, not an exception
for whichever benchmark failed. No current measurement establishes this
extension's quality, runtime, or novelty.

## Independent mathematical check after the draft

The literature reviewer checked the fixed-footprint equivalence and the
incremental-matching bound independently on 2026-09-08. Both hold under the
stated fixed selected source block, unchanged outside ownership, nonempty
connected available center, complete frozen obligations, and an added vertex
outside and adjacent to the current footprint. The `Delta` bound counts only
**successful augmentations**. Failed searches, edge examinations, domain work,
and restoration remain additional charged work; it is not a `Delta`-operation
runtime claim. This was a mathematical review, not an implementation test or
an embedding experiment.

Status: design and consistency review complete; specification stable for parent
review. Implementation and diagnostic execution are not authorized by this note.
