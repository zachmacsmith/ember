# B030 design: construction through movable physical contacts

**WITHDRAWN BEFORE IMPLEMENTATION.** Root identified that this draft repeats
the explicit-contact architecture in [the earlier replacement review](b_construction_replacement_review.md)
and B018–B022. Wider contact moves, spectral initialization and annealing do not
by themselves establish a substantially different constructor. The draft is
preserved as a design error, with no code, checks or runs. The single active
replacement proposal is [disconnected ownership](b_030_disconnected_ownership_design.md).

2026-09-10. **Design only: no implementation, diagnostic or constructor run.**
Replace B029's architecture with explicit source-edge contact placement and
coordinated owner routing. This is one proposed algorithm, not a menu or a
novelty claim. B029 remains rejected; A061 remains the retained algorithm.

## Deficit and hypothesis

The target is **spatially compatible contact positions**, across sparse
low-degree sources and sources needing shared branches. In the
[saved A061/MM comparison](c_a061_static_map_results.md), degree-four owners
account for 22/29 excess grid sites, degree-three owners for 40/45 honeycomb
sites, and the degree-three rim for 37/40 wheel sites. MM packs more of these
owners' contacts onto singletons. BA is different: MM uses 38 branch sites
versus nine in A061 while using fewer total sites. Removing branches or
minimizing overlap is therefore not a common solution.

[B029](b_029_causal_decision.md) lowers initial overlap but increases initial Q
on all nine inputs; six fail, and both earlier successes worsen. Its later
shortening does not repair the initial length cost. [A066](../experiments/066_constructor_results.md)
shows useful but small coordinated contact changes: six net qubits beyond its
ablation, with every MM gap retained. Its eventual final Q appears at
8.181–17.217 s, followed by mostly unproductive search
([trajectories](../experiments/066_initial_trajectories.md)).
[C017](c_017_decision.md) finds one bounded alternative but proves the chosen
ER80/BA100 repair domains infeasible even without quotas. BA's fixed outside
contacts already exclude its length-bounded chain. These results support
revisiting several contact positions together; they do not prove that this
proposed representation or heuristic will do so efficiently.

**Hypothesis:** choosing and moving physical contact couplers as construction
variables, while charging the complete connecting trees of every affected
owner, can prevent incompatible contacts from becoming long, difficult-to-shorten
chains. A coordinated move should sometimes merge several terminals onto one
site for a low-degree owner, and sometimes create shared branches for a hub.
Both must earn lower complete-embedding Q, not merely a favorable local score.

## One state and a concrete proposed search

For each original source edge `uv`, store one oriented actual Zephyr coupler
`(p_uv, p_vu)`. Its endpoints are required terminals of owners `u` and `v`.
Each owner has one connected tree spanning its terminals; isolates have one
site. Terminals of the same owner may coincide, and branches may be shared.
Different owners may temporarily share sites. All original contacts are thus
represented throughout construction; a valid minor additionally requires
disjoint ownership and the unchanged independent validator.

This representation can express any minor: choose one supporting coupler for
each source edge and connected spanning trees of its owner sets. It does not
impose root pins, quotas, a source prefix, a path restriction or fixed chain
lengths. The heuristic neighborhood may still fail to reach such states.
Additional incidental contacts remain legal; a stored witness can be freely
reselected among current supporting couplers without changing ownership.

Start once from a source-only spectral placement as a **soft initialization**,
map its endpoint preferences onto actual Z12 couplers, and connect every owner's
terminals. No anchor remains compulsory. Disconnected components and isolates
need a single seeded placement rule, specified before code. Spectral placement
is initialization, not another complete algorithm or a selected result.

Alternate fair source-owner and source-edge visits, using two coordinated
operators on this same state:

1. **Contact contraction:** for owner `u`, choose a hardware graph-distance
   median of its current terminals. Propose one-coupler steps of *all* incident
   contacts toward that center, retaining actual hardware adjacency. This
   changes the contact endpoints of `u` and its neighbors together. Several
   `u` endpoints may coincide; no neighbor retains a compulsory old endpoint.
2. **Contact slide:** move one oriented contact to an adjacent coupler, including
   orientation reversal. This provides translations and changes of direction
   that contraction alone cannot supply. Repeated slides can traverse the
   connected hardware coupler graph; that reachability is not a convergence
   argument for the accepted search.

Privately release the trees of all affected owners and reconnect their updated
terminal sets in one seeded rotating order. Use full hardware adjacency and
current occupancy costs, with shortest-path attachment to the growing tree;
reuse its sites rather than charging independent path lengths. Unchanged
incident contacts remain terminal obligations, not fixed outside chain shapes.
The affected owners may develop new branches. Recount actual full-state Q and
occupancy after routing; a distance estimate is only a proposal heuristic.

Proposed acceptance uses `F = Q + sum_q price[q] * k[q]*(k[q]-1)/2`, retaining
Q from the first state instead of lexicographic overlap priority. Accept lower
F; allow neutral and uphill proposals by a seeded Metropolis rule. Initially
unit site prices increase by excess occupancy after each completed owner round.
Use initial mean chain length as the temperature scale, cooling over the frozen
wall allowance. These are unvalidated fixed exploratory choices, not an
assertion that this energy solves embedding. They require exact numeric and
tie rules in the implementation contract. Retain the best timely valid
incumbent from this one trajectory, even if the working state later overlaps.

```text
place all source-edge contacts once; connect owner terminal sets
while wall time remains:
    select the next contact-contraction or contact-slide visit
    propose changed physical couplers; identify every affected owner
    privately rebuild their connected trees against all required terminals
    recount actual Q, multiplicities and contact support
    apply the fixed acceptance rule; publish the complete transaction or discard
    if ownership is disjoint: validate and record a better valid incumbent
    record first validity, every incumbent-Q change, costs and rejected proposals
return the best timely independently valid map from this trajectory, or failure
```

This differs from B029's root descent against fixed residual neighbor trees and
captured route labels. It also differs from C's proposed replacement, coordinated
with its author: C retains disjoint connected territories and permits missing
contacts; B retains explicit contacts and permits shared ownership. Neither
candidate receives the other's result, an MM map, a diagnostic witness or a
canned embedding. No MM/busclique code or global IP is involved.

## Competing explanations and distinguishing observations

| Explanation | Observation that would distinguish it |
|---|---|
| Representation | A valid hidden control must admit the explicit contact/tree form, checked only by the independent diagnostic side. An inability to encode it is an implementation/representation error, not heuristic failure. Extra terminal constraints beyond one chosen contact per original edge would be an unintended restriction. |
| Neighborhood | With the same evaluator and acceptance rule, coordinated contraction produces certified smaller affected unions that elementary slides do not, and changes complete outcomes. If both generate only nonimprovements after completed routing, increasing temperature has no demonstrated useful proposal to admit. A negative heuristic search does not prove no larger move exists. |
| Acceptance | Actual complete proposals with lower Q and clearable occupancy are repeatedly rejected, or admitted neutral/uphill proposals precede valid improvements. Log their exact Q/occupancy/F changes and admission decisions. A separately frozen same-neighborhood acceptance ablation may test causality; no counterfactual trajectory is inferred from a rejected proposal alone. |
| Computation | Routing affected neighborhoods consumes the allowance before fair source coverage, or candidate materialization/certification dominates. Measure completed and interrupted proposals, distinct owners visited, affected-set sizes and phase wall/CPU. Cheap slides completing while blocks repeatedly time out implicates block cost; it does not establish an expressive limitation. |

Counters diagnose exposure; none silently terminates search. Routing a star can
rebuild `1 + degree(u)` owners and several terminal joins per owner. This may be
far more expensive than its coupler proposal. Charge compilation, initialization,
rejected work, validation and process overhead. Any later active neighborhood or
work limit needs measured justification and a new frozen experiment.

## Self-critique and cheap disproof

Explicit contacts add variables and can create a large, overlapping initial
state. A spectral seed can separate contacts badly on dense or irregular sources
and is sensitive to eigenvalue degeneracy; it supplies no embedding guarantee.
Contraction may simply move length from one owner to its neighbors. One-step
contact proposals can still face collective barriers, and a fixed median can
be a poor destination. Sequential private rerouting can replace one ordering
problem with another. Adaptive prices and annealing can cycle or achieve
validity only after excessive chain growth. These are direct failure modes,
not reasons to add an indefinite sequence of local repairs. The possible
research contribution is the coordinated contact-placement construction;
spectral placement, routing and annealing themselves are established ideas.

After only specific terminal/ownership, transaction-interruption and relabeling
checks with the existing oracle and dependency guard, use **four small complete
constructors** as the cheap falsifier: fresh low-degree lattice, irregular
hub-bearing source, clustered source and hidden known-embedding control,
approximately 24–40 vertices. Compare full B030 and a slides-only ablation in
separate cold calls, same host/seed, a frozen 15 s allowance. This is a small
development screen, not a saved-state optimization. A contract must fix actual
inputs, initialization and policy parameters before code or outcome inspection.

If completed block proposals mostly redistribute Q without increasing distinct
contacts per occupied owner site, and full B030 shows neither earlier validity
nor lower final Q on two different structures, its central compaction assumption
has no continuation support. If block routing instead remains censored, report
the unresolved mechanism and measured cost; at most one justified allocation
or implementation follow-up may be proposed. No positive intermediate metric
alone advances this policy. Local savings that disappear in final results are
negative evidence, as in the completed B029/A066 comparisons.

## Prompt complete-constructor continuation, separate from promotion

If that cheap screen supports the mechanism, use ten development encodings of
eight structures: the existing ER80, BA100, grid128 and planar100 anchors; fresh
honeycomb, SBM, path and hidden known-embedding inputs; and two source relabelings.
The exact fresh sizes and manifests must be fixed independently of outcomes.
Run B030, retained A061 and pinned MM separately with 60 s cold allowances and
same-host paired timing. The untouched confirmation set remains untouched.

The proposed **continuation criterion** is timely validity on all ten small
inputs, plus lower final Q than A061 on at least two distinct structures,
including a fresh sparse input. Show every per-input MM gap and every A061
regression; optimal ACL-one ties count as ties. Record first validity and the
full incumbent ACL trajectory, including flat late intervals. Do not count a
relabel as independent generalization or infer variance from one seed.

Passing permits a broader mechanism evaluation, not retention or a publication
claim. A failed fixed policy remains rejected; a specific observed cause may
justify one bounded follow-up without erasing its regression. Promotion still
requires the separate class-level success/mean ACL/variability/runtime objective,
with no dense gains hiding sparse losses. Report all-call costs and paired
time-to-quality where actually observed. The 15/60 s screening envelopes are
explicit experiment allocations, not evidence of roughly-MM-order performance
and not a universal timing-ratio gate. No constructor screen is authorized by
this design note alone.
