# B031 proposal: transport a vacant Zephyr strip during construction

2026-09-10. **Before-code derivation; no implementation or experiment.** A finite
vacant band can be moved toward a blocked insertion while preserving a valid
partial minor. Only required cut crossings add chain sites. This is a concrete
operation, not evidence of good complete embeddings. Source-family labels,
MM/busclique calls or maps, learned initialization and global IP are excluded.

## Exact finite map

Use original Z12 coordinates `(u,w,k,j,z)`, with `w=0..24`, `k=0..3`,
`j=0..1`, `z=0..11`. Authority is the actual supplied adjacency and the pinned
[generator loops](../../../.venv/codex-native/lib/python3.10/site-packages/dwave_networkx/generators/zephyr.py:194),
SHA `8bcda95437a6a6836a45fc215a82bb8c2b60e60fbac985e1793bf1826d8122a3`.
No third paper was consulted. In particular, the executable internal-edge rule is

```
(0, 2w+1+a(2i−1), k, j, z) ~ (1, 2z+1+b(2j−1), h, i, w),
                                      a,b,i,j in {0,1}.
```

Choose integers `0 ≤ A < B ≤ 11`. Every site in the destination band

`V_B = {u=0, w∈{2B,2B+1}} ∪ {u=1, z=B}`

must be **unused**, across all other coordinates. This is a real empty-capacity
condition, not a count of free sites elsewhere. On occupied sites define F:

```
F(0,w,k,j,z) = (0,w+2,k,j,z)  if 2A ≤ w < 2B
F(1,w,k,j,z) = (1,w,k,j,z+1)  if A ≤ z < B
F(q) = q otherwise.
```

The empty band prevents collisions at the far end. Moved vertical w values are
at most 23 and moved horizontal z values at most 11, so no target enlargement
occurs. All sites outside the finite slab remain fixed. Noncrossing chains in
the slab **do move**, at unchanged length; a claim that only crossing chains'
coordinates change would be false. The operation spans the other coordinate
direction: it is a slab displacement, not an arbitrary small rectangular warp.

Let R contain a spanning tree for each current owner and one actual coupler
for each required original source edge between introduced owners. Choose these
from the current map with fixed seeded ties; they are transaction certificates,
not permanent witness endpoints restricting later construction. For each edge
of R crossing the near cut, its left endpoint has form
`q=(1,w,k,j,A−1)`. Add `b(q)=(1,w,k,j,A)` to q's owner. Add each such site once,
even if q supports several required edges. For A=0 there are no left endpoints.
The new chain is `F(C_v) ∪ {b(q): q belongs to v and crosses R}`.

**Coupler proof.** Same-side edges in the slab undergo the exact period
translation `(w→w+2)` / `(z→z+1)`; outside edges stay fixed. No occupied edge
crosses the vacant far band. The three possible near-cut cases follow directly
from the generator loops:

| Old required edge | Preserved connection |
|---|---|
| Horizontal external, z=A−1 to A, same j/k/w | Old left q → new b(q) → F(right), along consecutive external edges. |
| Horizontal odd, `(j=1,z=A−1)` to `(j=0,z=A)` | q → b(q), then the actual odd edge `(1,A)` to `(0,A+1)`. |
| Internal, horizontal `(j=1,z=A−1)` to vertical w=2A | b(q) at horizontal `(j=1,z=A)` contacts F(right) at vertical w=2A+2 by the same internal formula. |

Vertical external/odd edges keep a common w and never straddle this cut. These
cases cover all generator edges crossing it. Each b(q) lies in the newly
vacated horizontal layer z=A, is adjacent to q, and cannot collide with any
other image or another b(q). Hence owner connectivity, disjointness and all
required original contacts survive. The exact increase is
`ΔQ = |{distinct required left endpoints q}| ≤ 25·4·2 = 200`, usually a subset
of occupied cut sites; it is independent of slab width. This is not Q doubling.

The same construction can preserve **every occupied hardware coupler** by
taking all of them in R, but that may add unnecessary bridges for incidental
contacts and keep a chain sealed. The proposed rule preserves only the stated
trees and original-edge witnesses. It may lose unneeded hardware contacts;
every required original source contact remains. Actual adjacency checks and
the existing validator must confirm any implementation before publication.

Other directions are conjugates of F, using exact generator symmetries: swap
orientations `S(u,w,k,j,z)=(1−u,w,k,j,z)`; reflect x by
`R_x(0,w,k,j,z)=(0,24−w,k,j,z)` and
`R_x(1,w,k,j,z)=(1,w,k,1−j,11−z)`.
The external/odd loops and internal formula are invariant under these maps.
Enumerate +x, −x, +y, −y; there is no permanent frontier or expired region.

## Why it can expose compatible contacts

After displacement, both vertical layers w=2A and 2A+1 are empty. At w=2A+1,
one free vertical site can contact multiple horizontal bridge owners whose
other coordinates satisfy the actual internal-edge rule. This is a common
physical neighbor, not a sum of separate distance estimates.

For example, A=5, B=7 and two owners with horizontal rails
`(1,11,0,0,z)` and `(1,11,1,1,z)`, each owning z=4,5, require two bridges at
z=5 after movement. Every `(0,11,k,j,5)` is then free unless newly assigned,
and adjacent to both bridges. Thus several distinct new source vertices can
simultaneously use singleton sites there when their obligations allow it.
Old contacts at w=9 and w=11 survive at w=9 and w=13. This example establishes
compatible access, not that the added bridge Q beats every alternative route.

**One cheap actual-coupler check before a complete screen.** Construct the above
two-rail fixture with singleton blockers at every original common neighbor:
`(0,w,k,j,5)` for w=9,10,11. Let blockers at w=9 and w=11 supply required old
contacts to both rails. Check original validity, exact ΔQ=2, preservation of
those contacts and newly available common singleton sites using the unchanged
oracle. The initial common-singleton domain is empty; this alone does not mean
all larger insertion trees fail.

Include the blocked-insertion case in the same focused check: one owner at
`p=(0,10,0,0,5)`, each actual neighbor occupied by a distinct singleton owner,
and one required old contact to `(1,11,0,0,5)`. Other occupied neighbors need
not be logical neighbors. A new leaf of p has no free route initially. Under
the same map, p moves to w=12, its required contact moves with it, and
`(1,11,1,1,5)` is a free neighbor for the new leaf. Here no R edge crosses the
cut, so transport adds zero Q. An occupied destination-band site or a missing
required image coupler must reject the transaction; interruption must preserve
the entry. These are proposed checks, not executed observations or performance
evidence. The coordinate proof does not replace original validation.

## One coherent constructor to test

**Hypothesis.** A compact valid prefix can keep its existing contacts compatible
while moving unused capacity to blocked owners, avoiding independent long
repairs. The final benefit must exceed the cost of bridges and displacement.

Use one seeded degree-tied source BFS forest order. Initially place its first
owner at a central target site; disconnected components use the nearest free
site to the same center, with fixed target ties. For a vertex with introduced
neighbors, search the full target: one clean multi-source BFS per neighbor
chain through free sites, then every mutually reachable free root. Its new
chain is the union of canonical root-to-neighbor paths, excluding their occupied
terminal sites. Choose minimum **actual free-union cardinality**, ties by target
rank. Existing owners otherwise stay unchanged. No path-length sum substitutes
for actual Q, and no degree quota or three-strip birth window is imposed.

```
for v in the single fixed source order:
    try ordinary minimum-union insertion on the current valid prefix
    if no clean root exists:
        enumerate feasible vacant-band transports in all four directions
        for each private transported state, try the same insertion of v
        choose smallest actual (transport ΔQ + inserted-chain Q), fixed ties
        if none completes under the deadline, report failure and partial costs
    certify and publish the entire transport-plus-birth transaction, or birth
return the independently validated complete map
```

Transport occurs only after placement is blocked, never solely because a proxy
looks bad. Empty-band absence is an explicit neighborhood failure. No transport
publishes without its successful birth, so there are at most |V(G)| published
transports and no independent restart outputs. No postprocessing or alternative
constructor supplies the result. Candidate alternatives here are single-birth
transactions on one state, not competing complete embeddings.

Map/witness work is O(Q+|R|); preconditions can use maintained strip occupancy.
There are at most `4·binom(12,2)=264` directed cut pairs. Ordinary insertion
costs k target BFS traversals plus root path-union evaluation; a blocked step
can multiply that cost by the feasible pair count. Order pairs by ΔQ and use
only the exact local lower bound ΔQ+1 to skip a pair unable to improve an
already completed transaction. This bound applies because this transaction
only adds bridges and a nonempty new owner, not to arbitrary minor embeddings.
All imports, candidate copies, rejected scans, certificates and cancellations
share the original deadline; no cap silently declares search exhausted. Reserve
finalization time using the audited convention, and discard late/fatal outputs.

## Critique and complete falsifier

The vacant full band is a strong precondition and may disappear early. Several
sealed owners can need incompatible deformations. A shifted slab preserves
old contact geometry rather than improving every contact; bridge costs may
accumulate, and successful but long ordinary insertions never trigger this
mechanism. Root/path canonicalization can still miss compact trees. Deformation
permission therefore neither guarantees completion nor closes A061's grid/SBM/
branch-control gaps. The all-root query cost may dominate the cheap geometric
map. Component novelty is unproved; the concrete difference is finite vacancy
transport with required-contact preservation, not the name “adaptive topology.”

B030's patches permitted fragmentation/contact loss and depended on later
reconnection; this move preserves a valid prefix. B018–B029 changed couplers
or rebuilt owner trees; here whole side arrangements move coherently, with
transaction-local witnesses. C012's rejected 5/22 policy expired strips and
immobilized roots/closed owners; this policy does neither and requires no live
port guard. C019 jointly assigns stars; A's initial-footprint review changes
initial placement. Those remain separate mechanisms, not portfolio arms.

After root reviews this note and any implementation's focused check, propose
the existing six B030 encodings, seeds 0/1, B031/ordinary-only/A061/MM: 48 cold
60 s calls, methods paired on one host. No new inputs or witness exposure.
Record every blocked insertion, available band, certified/rejected transport,
actual bridge/birth Q, time-to-validity and final incumbent trajectory. Require
all twelve B031 calls timely valid; deformation must resolve blocked placements
on at least two distinct structures including a fresh-development input, and
two-seed mean final Q must beat A061 on at least two structures. Show ablation
recoveries, all common-success Q changes, every regression and all failure costs.
No first validity, unavailable bands, costly queries, or complete but inflated
maps distinguish different failure causes. None justifies an automatic wider
band, extra runtime or acceptance change. This is an exploratory continuation
criterion, not all-class promotion; root must freeze the eventual contract.
