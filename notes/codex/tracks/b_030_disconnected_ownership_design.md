# B030: construction with temporary disconnected ownership

2026-09-10. **One design proposal; no implementation or execution.** B029 is
retired and A061 remains retained. The first B030 contact-coupler draft was
withdrawn after root identified its overlap with B018–B022; that draft and this
correction remain saved. Novelty is unproved.

## Hypothesis and the assumption that changes

**Requiring every owner's sites to be connected after every move can force
premature connecting paths.** Permit disconnected contact-bearing components
during construction, then relocate components and their contact neighborhoods
together so that they coalesce without retaining those paths. Keep ownership
disjoint and sparse. Charge geometric separation and actual occupied Q from
the start; a count of components alone cannot distinguish nearby fragments
from physically incompatible ones.

The common deficit is spatial compatibility of source contacts. Saved A061/MM
maps attribute 22/29 extra grid sites to degree-four owners, 40/45 honeycomb
sites to degree-three owners, and 37/40 wheel sites to its degree-three rim.
MM has more singleton contact sharing there. BA instead needs useful branching:
MM has 38 branch sites versus nine in A061 while using fewer total sites
([map comparison](c_a061_static_map_results.md)). This design therefore seeks
both contact coalescence and shared branches, without a path-only restriction.

The completed evidence does not prove this hypothesis. B029 lowers initial
overlap and raises initial Q on all nine inputs; it fails six and worsens both
earlier successes ([decision](b_029_causal_decision.md)). A066's coordinated
contact exchange saves only six net qubits beyond its ablation; its final Q
arrives at 8.181–17.217 s, followed by mostly unproductive search
([results](../experiments/066_constructor_results.md),
[trajectories](../experiments/066_initial_trajectories.md)). C017's ER80/BA100
neighborhoods are infeasible even without quotas; BA's fixed outside contacts
already exclude its short-chain domain ([decision](c_017_decision.md)).

**Reconciliation with old B/C work.** B018–B020 already used movable contact
witnesses and connected trees, then failed all nine complete inputs. B021
certified compulsory-terminal locks in all 497 saved dense scopes. B022 released
whole incidence and moved those states, but completed only 1/9. B023 allowed
lost contacts and overlap, completing 6/9 with large sparse Q deficits; B024's
better placement proxies worsened complete results; B025's energy restriction
reduced success to 2/9. None justifies more contact pools, price tuning or a new
name for whole-chain reconstruction. They all preserved each owner's connectivity.
C's earlier quotient partitions and its current proposed territories likewise
keep each owner connected. However, [its after-C007 memo](c_after_atomic_growth_constructor_hypotheses.md)
already proposed global fragmentation with component-count energy: **this is
not a new representation idea in the repo**. That proposed global constructor
was not implemented. Its [saved-state gate](c_fragmentation_gate_results.md)
found only two compact witnesses among 64 fragmented transfers: 27 had no free
bridge and 35 increased Q by 1–12; the grid observation was lost and remains
unknown. Those results supported only a private transfer/reconnect operation.
C008 kept published owners connected, completed 3/8, and worsened all three MM
comparisons ([results](c_008_results.md)). C009 instead coordinated finite
connected-chain domains and completed 0/8; it did not test global fragmentation.

The changed **major design assumption** is therefore specific: connectivity
repair need not reconnect a donor immediately through free space while all
other owners stay fixed. B030 transports contact-bearing patches containing
several owners *before* reconnecting them, and scores geometric separation
rather than component count. This may allow coalescence without the old gate's
long/no-free bridges. It is a proposed replacement for current B's architecture,
revisiting an earlier unimplemented hypothesis with a different repair mechanism;
mere fragmentation, additional time or another single-donor bridge is not the
proposal. It uses neither an all-target partition nor permanent contact witnesses.

## State, moves and pseudocode

The state labels each hardware site as free or owned by one source vertex.
Every source owner has at least one site; its sites may have several connected
components. Start with exactly one site per source vertex, Q=n, in one seeded
structural source-to-target placement. An initial compact BFS seed is only a
placement, not a restricted physical domain: every Z12 site remains available.
No already-complete algorithm, MM output or hidden witness supplies this state.

Maintain actual missing original contacts M and per-owner component sets. For
owner v, use the MST weight of its component-distance graph as geometric debt
P(v), where a component-pair edge has weight `max(0, d_H(Ci,Cj)-1)`. Distances
use actual hardware adjacency. P is guidance, **not a lower bound on additional
Q**: it ignores occupied obstacles and may overcount shared connecting branches.
Lazy target-distance caches belong to this call and their full cost is charged.
Also record the actual added-Q/contact-loss cost of performed merge proposals.

Use three coordinated operations on the same label state:

- Transport a contact-bearing physical patch to a vacant compatible position,
  preserving its internal couplers. A patch may contain several owners; moving
  only part of an owner is allowed. Actual Zephyr translations can propose such
  moves, but every destination adjacency is checked. Single-site and label-swap
  moves supply changes that a rigid patch cannot express. No owner may vanish.
- Create or remove an owned boundary site, or exchange labels, to form missing
  original contacts and reduce separation. Losing other contacts or splitting
  an owner is an explicit possible cost, not a hidden invalid state.
- For a selected fragmented owner, propose an actual connecting path through
  free sites, merging components and pruning dispensable sites. This exposes
  the real length price of reconnection. It is one operator, not a compulsory
  full-tree reconstruction after every contact move.

Rank destinations using missing-contact and component-distance changes; recount
actual Q, M and affected connectivity before acceptance. A proposed initial
energy is `Q + sum_e lambda[e]*missing[e] + sum_v gamma[v]*P(v)`. Prices start
in qubit units and increase on persistent unsatisfied obligations after complete
fair sweeps. Within a fixed-price sweep, seeded Metropolis acceptance permits
neutral/uphill moves. Exact proposal order, price increments, temperature and
ties must be frozen in the before-code contract; none is established by existing
results. Do not compare energies across different prices as descent evidence.

```text
initialize sparse labels with one site per owner; count missing contacts
while the common wall allowance remains:
    select a contact or fragmented owner by the fixed fair schedule
    propose patch transport, label/site change, or real component merge
    privately recount affected components, contacts, Q and geometric debt
    apply the frozen acceptance rule and publish atomically, or discard
    when M=0 and every owner is connected:
        run the unchanged validator; record a better timely valid incumbent
    record all work, first validity and every incumbent-Q change
return the best valid incumbent from this one trajectory, otherwise failure
```

C keeps disjoint **connected** territories with missing contacts; B keeps
disjoint potentially **disconnected** ownership. The connectivity-preserving
ablation below isolates that new permission within B's own proposal machinery.
No independent algorithms' outputs are combined. No source-family labels,
instance IDs, canned embeddings, MM/busclique dependency or global IP are used.

## Competing explanations and distinguishing observations

| Explanation | Discriminating observation |
|---|---|
| Representation | The state can express any ordinary minor. A hidden valid control must be encodable by the independent diagnostic side, with its witness unavailable to the candidate. Failure to encode it indicates an unintended implementation restriction. Fractional or ghost contacts are never credited. |
| Neighborhood | Accepted moves temporarily split an owner, retain useful physical contacts, and later coalesce into valid lower-Q incumbents; a connectivity-preserving ablation loses that benefit. Fragment creation alone is not support. Negative local searches do not prove that a better arrangement is absent. |
| Acceptance | Fully evaluated useful patch/merge proposals are rejected by the actual rule, rather than never generated. Log exact Q/M/P changes and decisions. Rejected proposals do not establish a better counterfactual trajectory; a later acceptance ablation needs separate justification. |
| Cost | Distance/component recounts or real merges consume the allowance before meaningful proposal coverage. Completed repeated coalescence attempts with bad Q differ from interrupted attempts. Preserve both and measure phase wall/CPU, cache work, affected sizes and discarded proposals. |

No component, visit or route counter is a stopping gate. Geometry, full recount,
materialization, validation, imports and discarded work share the allowance.
Any later active local limit needs measured justification and a new experiment.

## Self-critique and cheap complete-constructor falsifier

The danger is substituting disconnected fragments for B029's overlaps: many
cheap contacts can create an expensive or practically unconnectable collection
of pieces. Geometric debt ignores occupancy, while shortest merges may merely
restore the long paths that this design deferred. Patch motion can destroy
outside contacts, and simultaneous owner coalescence can require a much larger
move. Component and distance accounting may cost more than ordinary routing.
These risks directly challenge the architecture; they are not reasons to keep
repairing it because M or component counts fall. Placement, label search and
annealing are established ideas; a publication contribution remains unproved.

Reuse the audited harness, dependency guard and original validator. Add only
specific checks for disconnected-state accounting, patch ownership/nonempty
owners, honest M/P updates, relabeling and interrupted atomic publication.
Then proceed directly to a small complete screen, with **two seeds**: Transfer004
ER96 g0301, BA96 g0302, SBM96 g0305, hidden branch-control96 g0308, the existing
grid128 anchor g0013, and BA relabel g0309. These are six encodings/five structures,
not six independent generalization samples. Candidate inputs contain graphs
only. Transfer004 panel SHA256 is
`b54a8ed0af8e35b3901630fddd2892e3735338ad29104913d3332df49eed250d`;
root must freeze exact graph/seed/source identities before any call.

Propose B030, its connectivity-preserving ablation, retained A061 and pinned MM
as separate cold calls: 48 calls with the existing 60 s development envelope.
Pair methods for each graph/seed on the same host; spare nodes can take other
complete pairs. The ablation rejects proposals leaving an owner disconnected
but otherwise uses identical machinery. Different later trajectories are expected;
this is a policy comparison, not replay of the same states.

**Cheap disproof:** contact counts improve, but fragments persist or real merges
cause large Q jumps, and B030 gains neither completion nor final-Q benefit over
its ablation on two distinct structures. That would reject the proposed
practical benefit, even if disconnected intermediate states are frequently used.
Interrupted searches implicate cost and leave reach unresolved. Do not add a
saved-state solver series or enlarge patch scope automatically.

**Mechanism continuation, not promotion:** require timely success on all twelve
candidate calls, final Q gains over the ablation on at least two structures
including a fresh input, and lower Q than retained A061 on at least two
structures. Show every seed, relabel result, failure and Q regression against
both A061 and MM. A failed fixed policy remains rejected; a specific measured
cause can justify a bounded follow-up without deleting its regressions.

Record exact time to first validity, every incumbent ACL admission, the Q jump
at reconnection, and flat late intervals. Component/M/P histories explain work;
only complete independently validated maps establish progress. Report all-attempt
solver/process costs and per-pair MM ratios without a universal multiplier gate.
Sixty seconds is an exploratory envelope, not MM-scale performance evidence.
Two seeds provide limited variability evidence, not a class-population estimate.
The full class-level objective and untouched confirmation set remain unchanged.
This design note authorizes no implementation or execution by itself.
