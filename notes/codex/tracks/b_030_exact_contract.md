# B030 exact exploratory contract

2026-09-10. Resolves [the reviewed design](b_030_disconnected_ownership_design.md)
before code. No implementation or run. The following choices are fixed for the
first experiment; they are not empirically optimized defaults.

**Initialization and randomness.** Normalize source vertices by supplied node
order and retain the original-label inverse. Use one `Random(seed)` to shuffle
source and target rank permutations, in that order. Source order is BFS over
components: start each component at maximum remaining source degree, ties by
source rank; order newly discovered neighbors by decreasing degree then rank.
Target order is BFS, with neighbors in target-rank order, from the site nearest
the center of ideal Z12. For `(u,w,k,j,z)`, its center is `(x,y)=(w,2z+j+1/2)`
if u=0 and `(2z+j+1/2,w)` otherwise. Minimize `(x−12)^2+(y−12)^2`, ties by rank.
Assign the first n target-BFS sites to the source order: exactly Q=n. No site
is pinned and all target sites remain eligible. Empty source returns the
validated empty map; n>|H| returns recorded failure. Unsupported hardware
coordinates or malformed input are explicit errors, never a substitute policy.

**Exact geometry and energy.** Hardware distances ignore occupancy and use the
actual full target graph. For each source edge e=uv, let
`D(e)=max(0,d_H(Cu,Cv)−1)` and let `m(e)` be its independently recounted missing
contact indicator. Define `P(v)` as the complete component-graph MST weight,
with edge weight `max(0,d_H(Ci,Cj)−1)`; P=0 for one component. Use Prim with
component minimum-target-rank ties. There is no component or distance cutoff.
Distances can be cached by their exact site-set/target identity; changed-owner
and private-residual sets cannot reuse stale fields.

`E = Q + sum_e lambda[e]*(m(e)+D(e)) + sum_v gamma[v]*P(v)`.

All coefficients initially equal integer 1. At the end of a **completed** sweep,
increase lambda[e] by 1 exactly for currently missing e, and gamma[v] by 1
exactly for currently fragmented v. No decay, clamp or update on a partial
sweep. Recompute entry energy under the new prices. D supplies a gradient when
no contact exists; P penalizes separation between already contact-bearing pieces
of one owner. Neither ignores a missing obligation just because its count has
not changed. Both ignore blocked corridors, and P can overcount shared branches:
these are guidance scores, not bounds or connectivity certificates.

**Fair schedule and admission.** A sweep visits every owner in source order,
cyclically shifted by the sweep number. Each owner receives PATCH, LABEL, MERGE
slots, in that order. Each slot consumes exactly three RNG draws even if skipped:
focus selection, proposal selection, admission. Use uniform selection through
the fixed ranked order where specified below. Every slot selects at most one
proposal; no trial-count or sweep cap terminates the algorithm.
With prices unchanged inside the sweep, accept ΔE≤0; otherwise accept iff
`log(1−admission_draw) < −ΔE`. Temperature is exactly one qubit-cost unit,
without cooling or restarts. The valid incumbent may survive subsequent uphill
working-state moves. The ablation applies the same rule but additionally rejects
any proposal with a disconnected owner. Geometry/proposal/price definitions
are otherwise identical; diverging histories are expected.

**PATCH.** Choose focus q uniformly among the visited owner's sites. P contains
q and every occupied hardware neighbor r of q whose owner equals q's owner or
is its original source neighbor. Thus the patch includes the entire immediate
contact star, not a top-k sample. Moving it can split any participating owner.
Enumerate every integer translation `(a,b)` in `[-24,24]^2`, excluding (0,0):

```
T(a,b)(0,w,k,j,z) = (0, w+b, k, j xor (a mod 2), z+floor((a+j)/2))
T(a,b)(1,w,k,j,z) = (1, w+a, k, j xor (b mod 2), z+floor((b+j)/2))
```

This is translation in the underlying Zephyr grid. Decode **original target
linear IDs**, not reordered array indices, using
`id=(((u*25+w)*4+k)*2+j)*12+z`; remap through the adapter afterward.
Keep a translation only if every destination coordinate is in range,
destinations are injective and free after removing P, and every actual edge
inside P maps to an actual target edge. Origin/destination overlap is legal:
vacate all original sites, then install all translated labels simultaneously.
The ±24 range contains every feasible translation of a nonempty Z12 patch;
out-of-range coordinates are rejected rather than wrapped. This neighborhood
does not include rotations, but singleton swaps below can change orientation
and rail position. No adjacency is inferred solely from coordinates.

For proposal sampling, write `Pu=P∩Cu`, `Ru=Cu\P`. For every moved u include the
term `max(0,d_H(T(Pu),Ru)−1)` when Ru is nonempty. For each directed original
neighbor v of such u include `max(0,d_H(T(Pu),Rv)−1)` when Rv is nonempty.
Let S(T) be the arithmetic mean of these terms, or zero if none exists. Sample
one eligible translation with weight `exp(-(S(T)−min S))`, cumulative order
lexicographic (a,b), using the proposal draw. This unweighted mean is only a
placement guide; no candidate is accepted using it. Enumeration covers the
whole defined translation domain; it does not reconstruct a chain for each
destination. Recount the selected proposal's full affected Q/m/D/P for admission.

**LABEL.** Its subtype is `sweep_number mod 4`, so every owner receives every
subtype each four sweeps. There are no hidden trial loops.

| Subtype | Single proposal |
|---|---|
| 0, relocate/swap | Select q uniformly in Cu. Consider every r outside Cu, free or owned; relocate q's label to a free r, or swap the two labels. Sample r using the PATCH guide for moving `{q}` to `{r}`, ignoring the displaced owner's cost only in this guide. Recount both owners exactly for admission. |
| 1, grow | Uniform free site adjacent to Cu; label it u. |
| 2, transfer | Uniform site r adjacent to Cu, owned by v≠u with |Cv|>1; change its label to u. A disconnected donor is permitted in the full arm. |
| 3, delete | Uniform site in Cu if |Cu|>1; make it free. |

Eligible site sets use target-rank order. Empty sets produce a counted no-proposal
slot. No owner can disappear, and ownership never overlaps. The global relocate
domain supplies direction/rail changes unavailable to a rigid patch. Uniform
growth/deletion/transfer still receives the exact D/P energy gradient; their
proposal distribution itself is not an estimate of final ACL.

**MERGE.** If u is fragmented, order its components by minimum target rank and
select one uniformly with the focus draw. Find the minimum-added-site path from
that component to any other u component in `H[free ∪ Cu]`: 0 cost for existing
u sites, 1 for free sites, with target-rank/first-parent ties. Exhaustion means
no path in this current free domain, not impossibility on Z12. Add its free
sites to u as one proposal; charge its exact Q increase. Do not perform an
implicit pruning or compensation search; later DELETE slots are explicit.
No route is needed for an already connected owner. Record free-route cost,
actual Q change and component/contact changes separately from P.

**Transaction, deadline and output.** Privately finish changed labels, affected
component/contact/distance recounts, acceptance receipt and deadline check before
publication. Unchanged owners and their incident edge terms stay exact; any
affected cache is invalidated. Search stops at the caller deadline minus
`min(1 s, 0.05*timeout)`, including initialization, caches and all rejected work.
There is no per-query clock, work cap or time extension. If M=0 and every owner
is connected, certify using the existing validator before adding a strictly
lower-Q valid incumbent; equal-Q states do not replace it. Record first-valid
time and every incumbent Q/ACL change. Implementation clarification before checks:
stop immediately when a certified incumbent has Q=n, the exact minimum for
nonempty disjoint owners; this is a mathematical optimum, not a work cap.
Finalization and final validation must
finish before the original deadline; late output receives no success credit.
Without a timely valid incumbent return no embedding, retaining the actual
stop reason, all partial-state defects and complete failure/time accounting.
The existing independent original-graph audit owns benchmark credit.

**One specific new-risk fixture, then the direct screen.** On a Z12 external
rail take a,b,c,d at z=3,4,5,6 with `(u,w,k,j)=(0,12,0,0)`. Source U−V starts
as U={a,b}, V={c}. PATCH at c is {b,c}; translation (2,0) maps it onto {c,d},
overlapping its origin. Correct simultaneous publication gives U={a,c}, V={d}:
Q=3, M=0, P(U)=1, and the original oracle must reject this disconnected state.
The actual free merge adds b and restores validity at Q=4. Check exact states,
cached versus direct distances, ablation rejection, and interruption immediately
before publication. This deliberately demonstrates contact-preserving movement
with an expensive reconnection, not a positive research result. It adds no
new validator or saved-state performance campaign.

After that focused check and the already required guard/transaction checks,
go directly to the design's **48 cold calls**: g0013/g0301/g0302/g0305/g0308/g0309,
seeds 0 and 1, B030/connected-ablation/A061/MM, 60 s, same-host paired methods.
Freeze identities and randomized order before execution. The predeclared
continuation criteria remain unchanged. Contact gain followed by persistent
fragments or large reconnection-Q jumps, without two-structure complete gains,
disproves this fixed compaction mechanism. Censored routing/recounts instead
leave reach unresolved while exposing cost. No numerical retuning or broader
screen follows automatically. Root reviews this contract before algorithm code.
