# C015 complete-constructor result: reject

2026-09-09. **C015 completes 0/8 inputs; retained A061 and MM each complete 8/8.** All eight C015 calls return FAILURE after exhausting the search allowance. The required recovery of ER80/ER100/BA100, retention of WS/grid/control successes, and at least one fresh success all fail. Do not broaden or promote this fixed policy. A061 remains retained; no combination of outputs is selected.

The frozen screen ran 24 independent calls on hyde03, ideal Z12, seed 0, 60 seconds each. The original audit passes with no unknown solver/CPU/process times; the passive mechanism reader passes with eight checked receipts and zero errors. Root verified 29 reader bindings. Candidate receipts show no prohibited import attempts or loaded embedding libraries. Neither analysis invokes a constructor. These are development observations, including fresh SBM100 and planar100, with no confirmation evidence.

| Input | C015 status | Published owners / n; partial Q | A061 Q / ACL | MM Q / ACL |
|---|---|---:|---:|---:|
| g0001 ER80 | FAILURE | 55/80; 189 | 261 / 3.2625 | 248 / 3.1000 |
| g0101 ER100 | FAILURE | 46/100; 136 | 344 / 3.4400 | 350 / 3.5000 |
| g0102 BA100 | FAILURE | 50/100; 163 | 282 / 2.8200 | 199 / 1.9900 |
| g0004 WS80 | FAILURE | 74/80; 186 | 163 / 2.0375 | 136 / 1.7000 |
| g0013 grid128 | FAILURE | 118/128; 187 | 168 / 1.3125 | 133 / 1.0390625 |
| g0017 singleton control80 | FAILURE | 37/80; 158 | 201 / 2.5125 | 181 / 2.2625 |
| g0202 fresh SBM100 | FAILURE | 50/100; 135 | 261 / 2.6100 | 241 / 2.4100 |
| g0203 fresh planar100 | FAILURE | 66/100; 181 | 174 / 1.7400 | 155 / 1.5500 |

Partial Q counts occupied sites in an incomplete embedding and is **not ACL or a quality win**. Every published and terminal-private snapshot checked by the existing reader is a valid induced partial minor with no individual capacity violation. None covers its full source. There is no complete private candidate recovered at finalization, fatal exception, or unrecorded timeout substitution: the reported failures remain failures.

| Input | C015 solver wall / CPU / process wall (s) | A061 solver / process wall (s) | MM solver / process wall (s) | A061 / MM within-chain variance |
|---|---:|---:|---:|---:|
| g0001 | 59.5054 / 59.4997 / 60.0138 | 7.3345 / 10.0563 | 3.2525 / 3.7830 | 1.568594 / 1.640000 |
| g0101 | 59.5034 / 59.4979 / 59.8942 | 6.8977 / 7.9307 | 1.7122 / 2.0179 | 2.066400 / 2.130000 |
| g0102 | 59.5046 / 59.5009 / 59.9133 | 9.4494 / 10.4436 | 4.7405 / 5.0758 | 3.287600 / 1.769900 |
| g0004 | 59.5106 / 59.5067 / 60.2230 | 7.5811 / 10.5662 | 0.5800 / 1.1204 | 0.861094 / 0.435000 |
| g0013 | 59.5061 / 59.5050 / 60.0518 | 6.8869 / 8.9522 | 0.3686 / 0.7162 | 0.324219 / 0.037537 |
| g0017 | 59.5042 / 59.5011 / 59.9364 | 5.5387 / 7.0310 | 1.5927 / 2.1234 | 0.774844 / 0.918594 |
| g0202 | 59.5061 / 59.4969 / 60.1857 | 7.0615 / 8.2854 | 1.2480 / 1.6180 | 1.357900 / 1.221900 |
| g0203 | 59.5043 / 59.4994 / 59.9424 | 6.6125 / 7.9320 | 0.7628 / 1.1685 | 1.032400 / 0.587500 |

All failure time is charged. Totals, solver wall / CPU / process wall: C015 **476.0447 / 476.0075 / 480.1607 s**; A061 57.3624 / 57.3571 / 71.1975 s; MM 14.2573 / 14.2560 / 17.6231 s. Per-input comparisons are paired on the same host; these single calls do not estimate timing variability. C015 mean ACL and within-chain variance are undefined for every input. Across-seed ACL variance is unestimated for every method. Preserve raw RSS but do not interpret its inherited process high-water mark as algorithm-specific memory.

The historical C014 WS/grid/control successes (Q175/143/80) become failures. In particular, the control's prior certified ACL1 is lost. C014's separate SBM80 Q regression and BA160/planar160 failures remain recorded outside this panel. Advancing the three formerly early-failing ER/BA prefixes farther does not compensate for these regressions. Grid already consumes Q187 for 118 owners, exceeding both complete baselines; later reconstruction could change this, so it is a partial-state warning, not a final ACL measurement.

## Mechanism decision

Quota-aware contact routing can construct many admissible births, but this complete policy fails operationally. There are 502 successful ordinary placements, one completed ordinary failure (ER100), and one interrupted ordinary placement (planar). Of 243 rebuild transactions, **242 start despite an available ordinary birth**. The [saved-receipt causal review](c_015_causal_review.md) attributes 311.708 seconds of nested placement work to 181 completed rebuilds discarded in favor of that already available birth. All retraction stages consume 376.603 seconds, 79.11% of solver wall. Six runs end inside proactive rebuilding while an ordinary birth remains unpublished.

Root generation records 1,317,089 roots; only 2,443 start and 2,435 finish. There are 2,428 first-admissible successful placements, seven completed rejected roots, and eight interrupted roots. These counts distinguish generated lists from performed routing. The first-admissible policy removes the former all-root evaluation requirement, but root-list generation, routing, and repeated private reconstruction still incur cost. Counters impose no stop; the only active runtime allocation is the global allowance with a 0.5-second final reserve. There is no per-owner cap or universal MM-ratio gate to relax. The recorded one-label route and greedy growth rules remain incomplete search neighborhoods.

The complete evidence resolves an acceptance/computation mismatch: singleton-domain loss triggers expensive rebuilding even though multi-site insertion remains available. It does not prove fixed quotas, first-root selection, or routing are sufficient for good complete embeddings. The two fresh failures provide evidence that this mismatch is not confined to the three diagnosed prefixes. No improved class-level result or MM capability claim follows from this screen.

Stop C015 and further local routing diagnostics. A separately frozen publication-policy experiment may test that specific mismatch while preserving routing/quota/source-order rules; it must return immediately to the same complete-constructor panel and preserve every regression. The [C016 contract](c_016_constructor_contract.md) is a proposal only. No constructor refinement is implemented by this result review.

Evidence: [original rows](../../../results/codex/c015-constructor/audit001/output/rows.json), [original audit summary](../../../results/codex/c015-constructor/audit001/output/summary.json), [passive receipt details](../../../results/codex/c015-constructor/mechanism001/output/details.json). Frozen screen SHA256 `9c6f989fafc96a3f6402834474ae00981dda5a32c5719655427d104f440d916d`; snapshot `5d20423663adaebf2692e484e25165b335b0ef814a28e103ed15ed8a999b9718`; reader identity `27769c9a4bd4a5463987f1b8fa39f615919fb6aac83421273da2c00879fcb99c`.
