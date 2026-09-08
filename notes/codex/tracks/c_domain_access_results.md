# Failed queries have no overlooked one-exchange route in their saved domains

The [saved-domain classification](c_domain_access_classification.md) finds no necessary-positive replacement for any failed query. The complete query's 1,871 untested admissible pairs therefore cannot create its missing edge with one exchange followed by a free path. This conclusion applies to the saved domains and private states, not to unrestricted ownership repair.

| Input | Saved private states / admissible pairs | Untested pairs | Untested necessary-positive | Positive pairs in failed queries |
|---|---:|---:|---:|---:|
| ER / ember_6450 | 10 / 101 | 80 | 78 | 0 |
| regular / ember_14334 | 16 / 277 | 3 | 0 | 0 |
| complete / ember_1041 | 1 / 1935 | 1871 | 0 | 0 |
| SBM / ember_30736 | 24 / 434 | 287 | 23 | 0 |

For each recorded private state, the check reconstructs exact ownership, validates every protected source contact P, and computes the unused target components accessible from the opposite endpoint. A replacement must release a site adjacent to the sealed endpoint, and that site must touch the other endpoint or an accessible unused component through a neighbor other than the consumed site. The latter test is necessary only: consuming an articulation site could still break the route. No necessary-positive is counted as a new certified repair.

Of the complete query's untested pairs, 426 would open an inaccessible pocket and 1,445 would not yet open the sealed endpoint. Its 64 attempted pairs also open inaccessible pockets. Across regular's 277 saved pairs, 231 open inaccessible pockets and 46 do not yet open the endpoint. Thus simply re-ranking these existing one-exchange proposals cannot repair either failed query set.

ER's 78 untested necessary-positive pairs are alternatives for the already-certified edge (4,80). SBM's 23 are alternatives for its already-certified edge (7,11). They provide no new missed-edge evidence. All three actually certified proposals pass the necessary test. In total, 104 pairs are necessary-positive, comprising those three witnesses and 101 untested alternatives; the alternatives have not received exact path certification.

The bounded classification covers all 2,747 saved admissible pairs across 51 states in 1.965 seconds, including serialization, without interruption. It charges 3.782 million component-adjacency examinations, 50,169 neighbor tests, state reconstruction and original-contact validation. Tiny enumeration checks 256 cases without a false negative, and a separate consumed-articulation fixture demonstrates a false positive. No donor, path or constructor search was rerun.

[All pair classifications](../../../results/codex/track-c-domain-access/pairs.csv), [reconstructed-state results](../../../results/codex/track-c-domain-access/results.json), [summary](../../../results/codex/track-c-domain-access/summary.json) and [manifest](../../../results/codex/track-c-domain-access/review_manifest.json) retain the evidence. The next design should continue bounded ownership transport between the endpoint-accessible unused regions, preserving intermediate pockets as private states instead of discarding them immediately. [The follow-up proposal](c_component_transport_proposal.md) remains unimplemented. No cap increase, full C007 run, new embedding-quality claim or novelty claim follows from this classification.
