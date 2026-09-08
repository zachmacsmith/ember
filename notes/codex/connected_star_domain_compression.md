# Compress identical leaf obligations in connected-center refinement

2026-09-08. Proposed amendment and self-critique before any implementation.
The [connected-center design](connected_star_relocation_spec.md) remains
unimplemented, and experiment 037 is unchanged. This note proposes an exact
representation reduction inside that one refinement operation, not another
constructor or a choice between algorithms. The independent
[adversarial review](connected_star_adversarial_addendum.md) confirms the
equivalence and capacity bound with the implementation caveats recorded below.

## Identical constraints permit a capacitated assignment graph

The selected source vertices induce a star with center c and independent
leaves. For a leaf l, let F_l be its set of frozen logical neighbors. Leaves
with identical F_l have the same physical eligibility domain: availability,
contact with every chain in F_l, adjacency to the current connected center T,
and the physical degree test. Their logical degrees also agree, since each has
exactly one selected neighbor, c. Old chain positions and lengths affect the
released region and total shortening allowance, but impose no additional
constraint on a replacement singleton.

Partition leaves by exact equality of F_l. For class a let c_a be its number
of leaves. Construct a flow network with source-to-class capacity c_a,
class-to-eligible-boundary-site capacity one, and site-to-sink capacity one.
An integral flow of value k, the total number of selected leaves, exists if and
only if the original duplicated-leaf graph has a covering matching. Forward
conversion forgets individual leaf identities; reverse conversion assigns the
class's distinct occupied sites to its leaves in stable order. No source family
label, approximate similarity or learned grouping enters this equivalence.

This is conventional capacitated matching, not a novelty claim. The potential
benefit is avoiding duplicated eligibility edges and state in this particular
local search. Every individual source leaf must still be represented and checked
in the final original-edge certificate.

## Incremental search and exact deficiency

Maintain each physical site's assigned class and each class's assigned count.
An augmenting search begins at an underfilled class, traverses eligible sites,
and follows an occupied site to its assigned class. Reaching a free site allows
one unit of additional assignment by reversing this alternating path. Use
stable class/site order and do not publish a partially reversed path. Stop only
at a covering assignment or after a completed search from all underfilled
classes establishes that none can reach a free site.

For a completed maximum assignment, alternating reachability gives a set S of
classes. Its singleton demand is sum(c_a for a in S), not |S|. If assignment is
incomplete and no augmentation exists, every neighbor site is occupied by a
reachable class, and at least one reachable class is underfilled. Hence demand
exceeds the number of neighboring sites. That demand-weighted deficiency can
guide the same center-growth operation. An interrupted search establishes no
such conclusion.

The Hall neighborhood must include sites already assigned to those classes.
A residual augmenting search may skip a saturated class-to-site arc, but that
site still belongs to the class's full eligibility neighborhood. Counting only
right-side vertices visited by that residual traversal would undercount the
neighborhood; include the already owned sites or scan the full domains, charging
that work. Independent review identified this implementation distinction.

When a new center qubit consumes an assigned site, decrement its class count
and remove that site. Newly exposed available boundary sites may restore or
increase total assignment. The previous nonmonotonicity warning still applies;
compression does not turn growth into monotone coverage. At most one assignment
is lost on deletion, and at most Delta-1 new sites are exposed, preserving the
earlier bound on successful augmentations. All scans, count changes, copies,
rollback and final expansion to individual leaves must be charged.

With g distinct classes and b boundary sites, eligibility-edge storage is at
most g*b rather than k*b, plus k leaf identities needed for final output.
Repeated naive augmenting searches can still scan the same sites many times.
Compression alone therefore does not prove linear work even when g=1. A
separately specified direct assignment of newly encountered free eligible sites
to underfilled classes could provide an initial feasible partial assignment;
general overlapping classes still require the complete augmenting search.
No such initialization policy has yet been selected or measured.

## A distinct-site capacity bound

Let P(T) be the available external physical boundary of the connected center.
For one growth step x in P(T), the new boundary loses x and gains at most
Delta-1 new sites, because x already has a neighbor in T. Therefore

    |P(T union {x})| <= |P(T)| + Delta - 2.

If r additional center qubits are allowed, the optimistic condition

    k <= |P(T)| + r * max(0, Delta - 2)

is necessary for any final singleton-leaf assignment. Count distinct available
sites, not couplers or already occupied frozen sites. This condition can be
stronger than the edge-boundary bound when several couplers reach the same site.
P(T) here is the unfiltered available boundary. Replacing it by only sites
eligible for some leaf invalidates the Delta-2 growth argument: an added center
site might itself be ineligible and therefore remove no site from that filtered
set while exposing Delta-1 eligible sites.
It ignores eligibility domains and frozen center contacts, so passing it does
not establish a feasible replacement. The maximum-degree relaxation is weak
when successive additions expose many shared neighbors. For Delta below two,
using zero as the possible positive growth remains optimistic and safe.

## Self-critique and decision boundary

1. Many inputs may have g=k. Then compression saves little and bookkeeping may
   increase runtime. The fixed algorithm must retain these cases in its results.
2. Capacity accounting, alternating paths and rollback add implementation risks.
   Small exhaustive assignment checks must compare both representations,
   including deletion of an occupied site, interrupted updates and classes with
   multiple demands. Tiny exact enumeration is a correctness oracle only.
3. Recovering individual leaves only at acceptance is safe solely because all
   members have identical external obligations and no selected leaf-leaf edges.
   Approximate grouping or extending this rule to arbitrary source blocks would
   invalidate the proof.
4. The same single root and greedy connected growth can still miss useful moves.
   Faster assignment does not establish useful search, lower final ACL, or
   improvement over the current pipeline.
5. Neither a capacitated matching representation nor the boundary inequality is
   itself a publication claim. The contribution must be assessed through the
   full principled heuristic, prior-art attribution and reproducible outcomes.

Independent proof and cost review is complete. The separate
[implementation policy](connected_star_implementation_spec.md) fixes the
representation and work accounting and awaits its own review before coding.
Do not alter the completed singleton-center experiment or implement multiple
connected variants and select outputs per input.
