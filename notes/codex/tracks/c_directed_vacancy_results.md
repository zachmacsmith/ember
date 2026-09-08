# Directed donor exchanges open two sealed SBM contacts

The [fixed directed-vacancy diagnostic](c_directed_vacancy_diagnostic.md) certified two repairs among 25 queried missing edges. Both are on SBM; neither completes its original source graph. This establishes limited supplied-state reach for contact-preserving donor relocation, without promoting a constructor or combining independent query outputs.

| Input | Sealed missing edges / queried | Certified repairs | Replacement attempts | Queries reaching 64/state cap | Diagnostic seconds |
|---|---:|---:|---:|---:|---:|
| ER / ember_6450 | 110 / 8 | 0 | 440 | 6 | 0.594 |
| regular / ember_14334 | 115 / 8 | 0 | 512 | 8 | 0.715 |
| complete / ember_1041 | 1 / 1 | 0 | 64 | 1 | 0.227 |
| SBM / ember_30736 | 60 / 8 | 2 | 426 | 5 | 0.614 |

Each query starts from its unchanged C006b final partial state. It freezes both endpoint chains and all unselected donors, preserves every initially realized original edge P, and only accepts donor replacements that bring the nearest unused site strictly closer to a sealed endpoint. A subsequent unused-only path creates the requested contact. Every intermediate donor chain remains connected/disjoint and retains its size. The same query, beam, depth, owner, site and time limits apply throughout.

For SBM edge (0,20), donor 42 replaces site 4,189 with 4,178; the path adds sites 585, 4,190 and 4,189 to endpoint 0. Q becomes 487 from 484. For edge (7,11), donor 43 replaces site 551 with 4,755; adding site 551 to endpoint 7 gives Q=485. Independent original-label replay verifies all P contacts after each relocation and the requested new edge after growth. These are separate proposals, with no cumulative success or full-minor quality claim.

The negative results are strongly limited by proposal ordering. Of 1,442 attempts, 890 produce disconnected donor replacements, 543 lose a P contact, seven open an unused pocket disconnected from the other endpoint's free region, and two certify. Twenty queries exhaust their 64/state prefix. The complete query tests only 64 of 13,368 generated replacements, all disconnected; this cannot establish donor infeasibility. All supplied-state attempts finish at the initial state or after one relocation. A two-exchange transport is demonstrated only in the tiny fixture: depth one fails, depth two succeeds, and rollback preserves the entry.

All 478 initial missing edges remain in the ledger: 192 are not sealed, 25 are queried, and 261 are excluded by the predeclared query prefix. No query reaches the 30-second input deadline. Total diagnostic, artifact and evaluator time is 2.415 seconds; work includes proposal generation/sorting, rejected replacements, copies, distance scans and certificates. Five focused groups passed, with a separate narrow late-output retention check; no corpus constructor, MM or remote call occurred.

[Query results](../../../results/codex/track-c-directed-vacancy/queries.csv), [every excluded edge](../../../results/codex/track-c-directed-vacancy/all_missing_edges.csv), [raw attempts](../../../results/codex/track-c-directed-vacancy/results.json) and [manifest](../../../results/codex/track-c-directed-vacancy/review_manifest.json) retain the evidence. The next useful falsifier is exact local feasibility filtering before ranking replacement sites, under unchanged caps. Nearest-vacancy distance alone also misses whether the released site connects to the required free region. Novelty, full-candidate quality and generalization remain unproved.
