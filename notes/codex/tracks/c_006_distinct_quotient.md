# C006: contraction that preserves distinct quotient neighbors

**Hypothesis.** C004's small-region matching prefers low physical coupler multiplicity, but an original source vertex needs contacts to distinct other regions. In a simple quotient, contracting adjacent u and v loses exactly `1 + |N(u) ∩ N(v)|` edges: their mutual edge disappears, and each common neighbor contributes one duplicate adjacency. Favoring smaller distinct loss may leave a more useful quotient for source assignment and missing-edge repair, particularly on dense graphs.

```text
use exactly C004's one compact target subset and source-degree allocation
at each matching level, order small regions first with the same seeded ties
for each unmatched region u:
    consider its adjacent unmatched partners v
    minimize (partner size, current distinct adjacency loss, seeded rank)
    contract the selected pair immediately in the current quotient
    update all neighboring adjacency/multiplicity records before the next score
stop at exactly n connected target regions
run unchanged C004 source assignment, search, deletion and original-target gates
```

The partner-size priority remains first, so this is not unconstrained maximization of quotient edges. Raw physical coupler counts are retained to update exact contacts, but do not rank equal-size partners. Immediate updates matter: disjoint selected pairs can share neighbors, so their losses on the initial batch graph are not additive. Per-level before/after counts and accumulated current losses must agree. Existing C004 raw-coupler scores between still-unmatched regions would not change under these immediate updates. There are no C005 free-site moves, extra domain sizes, independent constructor calls, family rules or external embedding routines.

Initial connected-region maps and quotient degrees will be retained for a direct original-target recount. C004 did not save its initial map. One separately labeled, bounded initialization-only diagnostic will reproduce its exact frozen subset/coarsening/assignment utilities on the same eight inputs, requiring exact replay of its saved initial missing-edge counts. It will call neither its constructor nor search/MM. Its timing is diagnostic overhead, not part of a candidate-versus-MM comparison. C006's own map creation and all construction/search work remain inside its common deadline.

**Self-critique/prior art.** This contraction identity is elementary graph theory; using it is not a novelty claim. More quotient edges do not ensure that a prescribed source graph is a subgraph of the quotient, and source assignment may still be poor. The fixed compact domain can remain inadequate; preserving unrelated contacts can consume sites that low-ACL source chains do not need. Size priority can dominate the new score. Incremental score/update work also costs time. This experiment tests a contact-preservation hypothesis within the established movable-region framework, rather than asserting feasibility or broad superiority.

**Cheap falsifier.** Tiny tests independently recount exact contraction losses, weighted physical contacts and connected regions, including equal raw multiplicity with unequal distinct loss and a stale-batch counterexample. Then freeze the same eight inputs, ideal Z12, seed 0, 15 seconds and fresh paired MM on hyde04. The initial-capacity hypothesis fails if distinct quotient edges do not increase on at least three inputs, or represented source edges do not increase on at least two of the four harder inputs. Even if that mechanism test passes, no algorithm promotion follows without retaining all four C004 successes and obtaining a new timely harder success or a timely quality win against MM. All eight failures, late outputs and costs remain visible; no held-out claim is made.
