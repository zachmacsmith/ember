# Exact domains expose feasible exchanges, then free-space connectivity blocks them

The [exact-domain diagnostic](c_directed_vacancy_domains.md) finds one additional ER repair and preserves both previous SBM witnesses exactly. The complete query has nonempty feasible domains, so the earlier disconnected prefix concealed usable donor replacements. None of these independent queries completes its whole original source, and no full candidate is promoted.

| Input | Queries | Certified before → after | Attempted replacements before → after | Diagnostic seconds before → after |
|---|---:|---:|---:|---:|
| ER / ember_6450 | 8 | 0 → 1 | 440 → 21 | 0.594 → 0.641 |
| regular / ember_14334 | 8 | 0 → 0 | 512 → 274 | 0.715 → 6.208 |
| complete / ember_1041 | 1 | 0 → 0 | 64 → 64 | 0.227 → 1.253 |
| SBM / ember_30736 | 8 | 2 → 2 | 426 → 147 | 0.614 → 0.696 |

The source states, protected original contacts P, 25 selected edges, ranking, beam/depth/donor/site limits and 30-second input deadline are unchanged. Exact domains intersect the original free frontier with boundaries of every donor-remainder component and every neighbor contact lost by deleting the release site. All domain construction and rejected release sites are charged. The original full replacement checks and original-target certificate remain in place.

On the complete query, 94 of 1,316 release-site domains are nonempty, containing 1,935 admissible replacements from 13,368 raw possibilities. All first 64 attempted replacements preserve donor connectivity and P, but the newly available pocket cannot reach the opposite endpoint through unused sites. The domain computation is practical; empty local domains are not the explanation for this query's failure. The 64/state limit still prevents an exhaustive conclusion about its remaining admissible replacements.

Across 51 visited private states, 8,826 release-site domains reduce 51,314 raw possibilities to 2,747 admissible replacements. Of 506 actual attempts, none is disconnected or loses P: 385 fail the free-path test, 118 enter the feasible child pool before possible beam pruning, and three certify. Three queries reach the state proposal cap, versus twenty previously. Repeated free-path checks contribute 11.3 million adjacency examinations on regular and 1.49 million on complete, explaining why fewer invalid proposals do not imply lower total cost.

The new ER repair targets (4,80): donor 60 replaces site 3,864 with 6, then a six-site free path creates the contact, taking Q from 540 to 546. The SBM proposals remain Q=487 and Q=485 from separate Q=484 entries. Independent original-label replay verifies P after every donor move and the requested edge after growth. No outputs are combined; every whole-source check remains incomplete.

Independent tiny enumeration agrees with the domains on 2,976 replacements, including articulation releases and singleton frontier restrictions. Five inherited occupied-endpoint, two-step, negative, cap and deadline cases also pass; two retained expectation corrections reflect rejection moving into domain construction. Total measured diagnostic/artifact/evaluator time is 9.213 seconds, with no deadline interruption.

[Queries](../../../results/codex/track-c-directed-vacancy-domains/queries.csv), [all excluded edges](../../../results/codex/track-c-directed-vacancy-domains/all_missing_edges.csv), [domains and raw attempts](../../../results/codex/track-c-directed-vacancy-domains/results.json) and [manifest](../../../results/codex/track-c-directed-vacancy-domains/review_manifest.json) retain the evidence. Exact filtering is useful, but the next hypothesis must address connection to the correct unused region rather than nearest-vacancy distance alone. These are repeated supplied-state diagnostics, with no constructor/MM comparison or novelty/generalization claim.
