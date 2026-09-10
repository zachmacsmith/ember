# C015 passive review: rebuilding after an available birth

2026-09-09. Saved candidate receipts and the frozen source establish that **242 of 243 private rebuild transactions were proactive**, rather than responses to a failed ordinary birth. This review performs no constructor call, graph search, or validator replay. C015 remains rejected, 0/8 versus A061/MM 8/8.

In the frozen `_run`, a successful `_place` is published directly only when it creates no newly empty pending singleton domain. Otherwise `_transaction` retracts earlier owners and reconstructs them privately, then compares its result with the already available ordinary proposal. The `ordinary_preferred` status means that the complete private reconstruction was discarded by this comparison. A pending source's empty singleton domain means it has no free **one-site** placement touching all introduced neighbors. It does not establish that a connected multi-site chain cannot be placed. C015 explicitly supports such chains.

Sequential placement receipts are partitioned at ordinary calls and aligned one-to-one with the publication ledger by source, prior introduced count, and prior Q. The intervening rebuild/guide calls belong to that outer step. The passive projection checks agreement with ordinary scores, newly empty sets, rebuild reintroductions, published Q, and the existing reader's nested-time totals. It does not reconstruct historical embeddings or read MM/witness maps.

| Input | Ordinary success / failure / interrupted | Proactive / failed-birth transactions | Retraction stage (s) | Discarded complete rebuilds; nested placement seconds | Terminal outer step |
|---|---:|---:|---:|---:|---|
| ER80 g0001 | 56 / 0 / 0 | 37 / 0 | 43.847 | 29; 36.552 | ordinary Q198 available; rebuild interrupted |
| ER100 g0101 | 46 / 1 / 0 | 32 / 1 | 49.930 | 27; 36.371 | ordinary failed; rebuild interrupted |
| BA100 g0102 | 51 / 0 / 0 | 34 / 0 | 44.661 | 20; 37.733 | ordinary Q170 available; rebuild interrupted |
| WS80 g0004 | 75 / 0 / 0 | 35 / 0 | 41.842 | 26; 31.785 | ordinary Q189 available; rebuild interrupted |
| grid128 g0013 | 119 / 0 / 0 | 30 / 0 | 49.495 | 26; 43.427 | ordinary Q188 available; rebuild interrupted |
| control80 g0017 | 38 / 0 / 0 | 17 / 0 | 50.121 | 13; 41.964 | ordinary Q164 available; rebuild interrupted |
| fresh SBM100 g0202 | 51 / 0 / 0 | 26 / 0 | 51.870 | 19; 41.136 | ordinary Q139 available; rebuild interrupted |
| fresh planar100 g0203 | 66 / 0 / 1 | 31 / 0 | 44.837 | 21; 42.742 | ordinary placement interrupted; no available proposal |

All 502 completed ordinary successes use their first started root. The available terminal proposals are source-certified partial births for 56/51/75/119/38/51 owners, respectively; they are not complete embeddings and were not independently replayed in this review. Their successful receipts agree with each pending publication's score. The score's first component is **Q + pending count + empty-domain count**, not Q; the table uses the placement's explicit `Q_after`.

The 243 transactions comprise:

- **181 `ordinary_preferred`:** 1,494 nested placement calls, 311.708274 s wall / 311.692669 s CPU. These complete private results were discarded; this measured nested cost alone is 65.48% of all C015 solver wall.
- **50 `rebuilt`:** 312 calls, 14.077204 s wall / 14.077088 s CPU. All also had an ordinary proposal. Their chosen private states improve the inherited lexicographic score; this is not necessarily an ACL improvement.
- **5 `rebuild_failed_capacity_no_outside`:** 103 calls, 21.300850 s wall / 21.297790 s CPU. Each falls back to an available ordinary proposal.
- **7 interrupted transactions:** 52 calls, 28.859178 s wall / 28.856771 s CPU. Six had ordinary proposals; the ER100 transaction follows the only completed ordinary failure. Planar's deadline instead occurs during ordinary placement.

Nested transaction placement wall totals 375.945505 s, within 376.603441 s of total retraction-stage wall. The remaining 0.657936 s covers unallocated transaction overhead. Per-transaction enclosing timers are absent: the grouped seconds exclude retraction copies, certificates, score calculations and control overhead, and are **not** exact full transaction durations. Never add nested and enclosing time. This attribution describes work actually performed; it does not estimate a faster counterfactual constructor.

Recorded capacity failures total 29 placement calls, 28 inside private rebuilds and one ordinary ER100 call. Twenty-four failure calls generate zero roots; five explore roots and reject seven completed trees. All are labeled `capacity_exhausted`, with no `contact_unreachable` failure or guide use. A failure of the permitted-component/path/growth policy is not exhaustive connected-chain infeasibility. Interrupted roots are censored and must not be counted as rejected. No additional cut certificates or path searches are performed here.

## What is resolved and what remains open

The acceptance rule and computation allocation are directly implicated: source semantics and matching ledgers show that the algorithm delays admissible births for proactive reconstruction, usually discards the reconstruction, and frequently loses its final ordinary proposal at the deadline. Rebuilding can help the inherited score, so its removal is not established as universally beneficial. Representation and route-neighborhood limits remain possible later: fixed individual quotas and one retained path label can reject useful states, and the recorded ordinary ER100 failure already shows that direct publication alone cannot be assumed to remove every obstruction.

An observation distinguishing the remaining explanations is a complete constructor that publishes each admissible ordinary proposal while keeping all placement mechanics fixed. If it still cannot complete, the recorded terminal cause and ordinary/rebuild costs will locate the residual obstruction; if it completes with poor ACL, avoiding proactive work resolves completion cost without resolving placement quality. This supports one separately frozen complete-policy experiment, not a chain of new local routing diagnostics. No counterfactual completion, final ACL, or class superiority is claimed.

Evidence: [passive projection](../../../results/codex/c015-constructor/causal001/output.json), [projection source](../../../results/codex/c015-constructor/causal001/summarize.py). Source SHA256 `1b8149a19df74bf565c7e20ea063a2c3c6eb3f35de4b28cd112cee444d9b2eb2`; output `709890eaf97a6d7006886e7c19132723d18e45e9488dddad1ac73fad56e5bba2`. The projection's first saved execution passes and binds ten input files. Earlier exploratory terminal-print code stopped on a null ordinary score for ER100; its corrected display preserved that genuine ordinary failure. This was a readout error, with no altered candidate result or experiment rerun. Frozen `_run`/`_transaction` source is the archived C015 module SHA256 `b870572b5bffd79f31bb0ace89e41e79ea64361d1cc346d8356f455c0063c9fa`.
