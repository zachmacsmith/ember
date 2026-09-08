# Free paths repair some contacts but cannot complete these states

The [supplied-state diagnostic](c_free_path_diagnostic.md) found useful free routes, but no original-valid complete minor. More decisively, every saved C006b final state contains a missing edge incident to a chain with no unused neighbor. With existing ownership fixed, additions alone cannot repair such an edge: that chain cannot grow, and another chain cannot reach its boundary through unused sites. This rejects free-path augmentation as a sufficient completion mechanism for these four states, independently of the greedy ordering.

| Input | Initial missing / routable | Shortest extra sites per routable edge | Added Q | Final missing | Final Q | Diagnostic seconds / stop |
|---|---:|---:|---:|---:|---:|---|
| ER / ember_6450 | 161 / 51 | 1–12 | 146 | 123 | 686 | 8.747 / stalled |
| regular / ember_14334 | 232 / 117 | 1–18 | 53 | 207 | 1733 | 30.000 / interrupted |
| complete / ember_1041 | 3 / 2 | 3–7 | 10 | 1 | 3566 | 0.285 / stalled |
| SBM / ember_30736 | 82 / 22 | 1–11 | 95 | 62 | 579 | 2.262 / stalled |

Initially, each input's unused target subgraph has exactly one connected component, containing 4,260/3,120/1,244/4,316 sites. Only 75/133, 95/140, 78/127 and 64/120 chains touch it. All 286 initially unreachable missing edges lack free access at an endpoint; disconnected free space is not the obstruction. The per-edge path lengths above are individual shortest costs, not a joint minimum-Q solution.

Sequential minimum-extra-site augmentation makes 38/24/2/20 ownership additions and monotonically adds 38/25/2/20 missing source contacts. It preserves every previous contact. On the complete graph, canonical edges (43,123) and (17,61) receive paths of three and seven sites. The remaining edge (8,63) is blocked because chain 63 has no unused neighbor. Existing ownership must change to address this obstruction; assigning more free paths cannot do so.

The regular diagnostic stops during route recomputation at its declared 30-second cap. A separate saved-state recount finds 85 still-routable edges among its 207 remaining misses. Its raw last completed route table describes the preceding state (86/208), explicitly marked in the additive recount; it must not be read as a final table. No continuation ran. The other three final states have no free route. Safe deletion was omitted on all four because none completed.

The main diagnostic costs 41.541 seconds including serialization; independent replay and component recount add 0.951 seconds. Repeated route scans account for 18.2/79.6/0.043/3.0 million BFS adjacency examinations. These costs include failed work and are supplied-state diagnostic measurements, not constructor or MM timings. Original-label validation, every saved path, ownership addition, exact Q and preservation of prior contacts were checked against frozen original inputs/target. Five tiny test groups passed after two retained pre-execution corrections.

[Every missing-edge query](../../../results/codex/track-c-free-path-diagnostic/initial_missing_edges.csv), [raw results](../../../results/codex/track-c-free-path-diagnostic/results.json), [independent recount](../../../results/codex/track-c-free-path-diagnostic/independent_recount.json) and [manifest](../../../results/codex/track-c-free-path-diagnostic/review_manifest.json) retain evidence and limits. Any future integration needs ownership release or transfer and must charge its full construction cost. No new algorithm wrapper, corpus rerun, MM call or generalization claim was made.
