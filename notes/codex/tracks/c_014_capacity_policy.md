# C014: capacity-aware contact-tree construction

**Before-code proposal; no implementation or candidate calls.** Preserve C013 and its failed star gate. The [offline certificates](../../../results/codex/c014-capacity-diagnostic001/summary.json) independently establish optimal star22 Q23 on both actual targets. An adjacent pair has 25 distinct external boundary sites; assigning the hub to the pair and 21 leaves to distinct boundary sites realizes the original source. Every source vertex needs a site and the degree-21 hub needs at least two, proving Q≥23. The measured maximum degree is **19 on Z2 and 20 on Z12**. The earlier C013 note and frozen Transfer002 protocol incorrectly state 20 for Z2; this correction changes neither the exclusion nor the certificate. Leave those bound artifacts unchanged and link this correction. All witness maps and the reproduction script remain evaluator-only, outside the candidate bundle.

**Hypothesis and choice.** C013 can repeatedly rebuild a hub as a singleton because its placement rule only considers contacts to introduced neighbors. C014 chooses actual-boundary capacity plus connected growth. It does not reserve named ports for future vertices or solve a matching/IP: those stronger assignments can impose unnecessary geometry and computation. Domain scores still guide placement, while a necessary fixed-chain capacity condition prevents the demonstrated representation error.

For every placed owner u, with chain B(u), define

```text
r(u) = number of original neighbors not yet introduced
C(u) = | N_H(B(u)) ∩ Free |
require C(u) ≥ r(u).
```

This is necessary **if the currently placed chains remain fixed**. Each different future neighbor chain must own a different currently free site adjacent to B(u). The count concerns distinct actual sites, not degree sums or physical edge counts. It is not a simultaneous-feasibility guarantee: owners can compete for the same sites, and the remaining chains may not connect their multiple required contacts. Later movement invalidates a fixed-state capacity argument. Every publication will nevertheless satisfy this condition for **all** introduced owners, with no permanent port assignments or restriction to a hardware strip.

## Exact change to C013 placement

Retain C013's source order, seeded integer ranks, actual Zephyr geometry, full-target root enumeration, shared-contact tree construction and score. Singleton domains still produce singleton starting roots, but no longer restrict the resulting chain to one site. For each ordinary root:

```text
Build the same connected tree realizing all introduced-neighbor contacts.
Evaluate the hypothetical state after this birth; recompute r for all owners.
If an older owner's C < r, reject this root and record every violating owner.
While the new owner's C < r:
    Consider every free site q adjacent to its current tree.
    Reject q if claiming it would make any older owner's C < r;
        record those owners as capacity blockers.
    Among admissible q choose greatest resulting new-owner C,
        then smallest C013 prospective-state score, then target rank.
    Claim q with one tree edge to its lowest-ranked adjacent tree site.
    If no admissible q exists, record capacity failure for this root.
After reaching C ≥ r, prune tree leaves in C013's order, but remove a leaf
    only if original contacts AND the new owner's capacity remain satisfied.
Score the complete candidate; choose among roots exactly as in C013.
```

With current new-owner free boundary R and current Free set F, a claim gives
`C' = |(R−{q}) ∪ (N_H(q) ∩ (F−{q}))|`. Other chains remain fixed: their capacity decreases by one exactly when q was on their free boundary. Score and capacity are recomputed against the proposed occupancy, never against a stale free set. Growth may take zero or negative immediate capacity gain when that is the best admissible step; corridors are not excluded by a positive-gain gate. Claimed sites increase strictly, so growth is finite without a numeric visit/length cap. Stop at the first sufficient capacity, then prune. A low-degree owner with sufficient boundary remains eligible as a singleton; an isolate owes zero future contacts.

Record all rejected-root explanations. On a failed growth root, the obstruction set contains recorded older capacity blockers and owners occupying the external boundary of its final attempted tree. Union these owner sets over completed roots. This may produce a broad group; it is an observed set of constraining chains, not a minimum conflict-set claim. All growth, scoring, rejected sites and unsuccessful roots consume the existing common deadline.

## Retraction, acceptance and failure meaning

Use the same one-state, net-one-vertex C013 transaction, adding the recorded capacity-obstruction owners to its initial K when ordinary placement fails. Rebuild privately with C014 PLACE, including closed owners whenever physical occupancy identifies them. A capacity-safe ordinary proposal that empties a future singleton domain still triggers C013's existing reconsideration; candidates at the same introduced set use the unchanged score. **Only capacity-safe proposals may publish or serve as ordinary fallback.** A cheaper unsafe singleton cannot win that comparison. All-source retraction uses the same growth rule, so it cannot silently restore the singleton-only hub restriction.

PLACE must distinguish three exits: `contact_unreachable` (a completed free-component check finds no fixed-chain contact extension), `capacity_exhausted` (contact candidates exist but all attempted roots fail the capacity rule), and interruption. For a failed private rebuild:

```text
If capacity_exhausted:
    add recorded obstruction owners outside K and retry from the entry state;
    if none can be added, discard the private rebuild.
If contact_unreachable:
    use C013's occupancy-relaxed contact guide to add outside owners;
    no guide/no possible addition discards the private rebuild.
If interrupted: discard the unfinished transaction; do not classify exhaustion.
```

The guide remains a contact-only explanation, never an embedding or a capacity certificate. Its zero-owner inconsistency check applies **only** after completed `contact_unreachable` failure. It is not valid after capacity/scoring rejection. Claiming an unrelated owner's last required free contact records that owner as a blocker; reconsideration can move it rather than publishing the violation. K must grow strictly on retries. If the rebuild fails, retain a certified capacity-safe ordinary proposal if one exists; otherwise return failure. Keep C013's deadline, certified-complete-private-result handling, final existing original-edge gate, rollback and fatal/late noncredit. No new local work/time cap is active.

**Self-critique.** Maintaining future capacity before all contacts are placed can reserve more boundary than a flexible later trajectory needs. Greedy growth can choose the wrong geometry, consume another owner's scarce sites, or fill a corridor without finding enough boundary. Independent capacity counts miss shared-demand conflicts; a broad obstruction union can make retraction costly. All-root scoring can dominate runtime. These risks concern the representation, neighborhood and cost, and are not solved by declaring the necessary bound sufficient. The mechanism is unproved and its novelty uncertain.

## Cheap falsifier and next decision

Check only new risks: actual distinct-boundary counts and signed changes; consuming an unrelated owner's reserved capacity; growth through a zero-gain step; capacity surviving leaf pruning; all-owner publication checks; failure classification, strict K expansion and interruption rollback. Reuse the existing oracle and dependency guard. Then run exactly two real tiny complete calls, seed0/5 seconds each on Z2: **the preserved star22, requiring Q23**, and **K2,10, requiring Q12**. The second has an independently certified singleton witness: two target sites have 16 common neighbors, sufficient for ten distinct shared leaves. The candidate sees neither witness, coordinates on source vertices nor evaluator labels. The control tests simultaneous-contact alignment and continued use of singletons, beyond the star's degree requirement.

Failure of either tiny requirement rejects the fixed C014 policy; domain/capacity counters alone cannot justify another repair chain. A bounded further mechanism decision would need a specific discriminating explanation. If both pass, promptly freeze the same nine-input Transfer002 complete screen with fresh paired same-host A061/MM. Preserve its seven exposed and two new structures separately, all failures and actual time. Continue only with lower complete Q than A061 on two independently generated development inputs from different families, at least one no worse than timely MM, and no lost A061 singleton-control success. Every regression blocks promotion; the original per-class objective remains unchanged.

The star distinguishes the removed singleton exclusion from runtime: sufficient boundary must be constructed before the deadline. K2,10 distinguishes individual capacity from joint contact geometry. Generated safe proposals rejected by scoring implicate acceptance; no admissible growth sites with movable quota blockers implicates coordinated movement; successful growth followed by domain/guide cost censoring implicates computation. Capacity could also help community and hidden-control inputs by preventing several future neighbors from being forced through too few remaining sites, but only complete-constructor outcomes can establish that transfer.

## Root implementation clarification before code

Root authorized the isolated `zephyr_capacity_contact.capacity_contact_embed` implementation and focused checks; proposed descriptor `capacity-contact-domain`, config `{}`. C013 remains byte-for-byte unchanged. Its contact-tree helper returns sites, so recover one spanning tree by BFS on that actual induced subgraph, starting at the lowest target-rank site and visiting neighbors in target-rank order. Each added growth site attaches to its lowest-ranked adjacent current tree site. Retain these tree edges during leaf pruning; no root is protected. This deterministic recovery chooses one tree, not a search over spanning trees.

When retracting K, recompute capacity and remaining incidences from the resulting private state. For each retained owner, removing adjacent original owners increases r, but their released chains contribute at least one distinct free contact site per removed original neighbor; an entry state satisfying the bound therefore remains safe. Check that implication against actual released occupancy and original edges. Record the changes rather than carrying old r values across retraction. No nine-input or remote call is authorized before root reviews implementation and the two complete tiny controls.
