# C016 complete-constructor result: reject

2026-09-10 UTC. **C016 completes 3/8 inputs versus retained A061 and MM 8/8. All three completed embeddings have worse ACL than both comparators.** The frozen falsifier fails: none of ER80/ER100/BA100 recovers, only two of three prior C014 successes survive, and fresh planar completes with poor quality. Do not broaden or promote this fixed policy. C015 remains rejected, and A061 remains retained; no outputs are combined.

The 24 independent seed-0 calls ran on hyde03 with ideal Z12 and 60-second allocations. Root confirmed terminal supervision and fetched once: 254 files, digest `a0799b2d749a198e27b59234a6b4bf8ded6c41e58a4fcac96f132c04ddcd0570`. The original audit passes first execution, with all times known and all 24 results accounted for; root verified 188 bindings. The prepared passive reader also passes first execution with eight checked receipts. Original-label validity alone determines credit. Five failures remain failures, even though their published and terminal-private snapshots are independently valid induced partial minors with no quota violations.

Within-chain variance below is distinct from across-seed ACL variance, which remains unestimated. A dash indicates unavailable final quality, never zero.

| Input | C016 Q / ACL | A061 Q / ACL | MM Q / ACL | Within-chain variance: C016 / A061 / MM |
|---|---:|---:|---:|---:|
| g0001 ER80 | FAILURE | 261 / 3.2625 | 248 / 3.1000 | — / 1.568594 / 1.640000 |
| g0101 ER100 | FAILURE | 344 / 3.4400 | 350 / 3.5000 | — / 2.066400 / 2.130000 |
| g0102 BA100 | FAILURE | 282 / 2.8200 | 199 / 1.9900 | — / 3.287600 / 1.769900 |
| g0004 WS80 | 218 / 2.7250 | 163 / 2.0375 | 136 / 1.7000 | 2.399375 / 0.861094 / 0.435000 |
| g0013 grid128 | 212 / 1.65625 | 168 / 1.31250 | 133 / 1.0390625 | 1.616211 / 0.324219 / 0.037537 |
| g0017 singleton control80 | FAILURE | 201 / 2.5125 | 181 / 2.2625 | — / 0.774844 / 0.918594 |
| g0202 SBM100 | FAILURE | 261 / 2.6100 | 241 / 2.4100 | — / 1.357900 / 1.221900 |
| g0203 planar100 | 281 / 2.8100 | 174 / 1.7400 | 155 / 1.5500 | 2.733900 / 1.032400 / 0.587500 |

The WS/grid/planar ACL gaps to MM are +60.3%, +59.4% and +81.3%, respectively. Larger within-chain variance accompanies these quality losses, but variance alone is not the rejection rule. The success and mean-ACL requirements already fail.

| Input | C016 solver wall / CPU / process wall (s) | A061 solver / process wall (s) | MM solver / process wall (s) |
|---|---:|---:|---:|
| g0001 | 25.4368 / 25.4337 / 25.8143 | 5.6765 / 6.9344 | 2.3126 / 2.6216 |
| g0101 | 7.3685 / 7.3676 / 7.6908 | 6.0669 / 7.0910 | 1.6437 / 2.0230 |
| g0102 | 53.6498 / 53.6486 / 54.0735 | 7.4818 / 8.2911 | 4.0665 / 4.3819 |
| g0004 | 15.5783 / 15.5781 / 15.9727 | 5.1097 / 6.0866 | 0.3843 / 0.6670 |
| g0013 | 14.1468 / 14.1451 / 14.5622 | 5.1842 / 5.9316 | 0.3078 / 0.5665 |
| g0017 | 59.5070 / 59.5049 / 59.8297 | 4.9996 / 5.9857 | 1.2345 / 1.4686 |
| g0202 | 59.5072 / 59.5054 / 59.8697 | 5.8842 / 6.7334 | 1.1335 / 1.4182 |
| g0203 | 20.2558 / 20.2529 / 20.6317 | 5.6201 / 6.4807 | 0.6074 / 0.9178 |

Totals including every failure, solver wall / CPU / process wall: C016 **255.4501 / 255.4362 / 258.4445 s**; A061 46.0230 / 46.0215 / 53.5346 s; MM 11.6903 / 11.6896 / 14.0648 s. Successful C016 calls take 33.4–46.0 times their paired MM solver time. This is measured cost evidence, not a universal ratio gate. All timing pairs share a host, but one run does not estimate timing variability. Preserve raw RSS without attributing inherited process high-water marks to the algorithm alone.

ER80/ER100/BA100 terminate on completed construction obstructions at 55/80, 39/100 and 84/100 published owners, with partial Q236/134/376. Control and SBM reach the search deadline at 49/80 and 87/100 owners, with partial Q326/386. These partial quantities are not ACL. No final complete private embedding rescues any failure. The [causal decision](c_016_causal_decision.md) distinguishes the three neighborhood stops from the two runtime stops.

All three successes recover failures from C015's 0/8 screen. That does not erase C014's stronger prior results: WS Q175 becomes Q218, grid Q143 becomes Q212, and the control's certified Q80 optimum remains lost. Historical C014 SBM80 regression and BA160/planar160 failures remain recorded outside this panel. The panel was already exposed through C015; its two newer inputs provide transfer observations but no untouched confirmation or broad class-level estimate.

Evidence: [original rows](../../../results/codex/c016-constructor/audit001/output/rows.json), [passive receipts](../../../results/codex/c016-constructor/mechanism001/output/details.json), [compact projection](../../../results/codex/c016-constructor/causal001/output.json). Screen SHA256 `75859986590609dfbe501cb74bdd9d57f0553486175c8eee84ef952aa4e5a08f`; source snapshot `c46397e8deb4d6b5f9c839157f08c95c1d280c75789dce7d0aa2817db828e17f`; manifest `eb13cd9a31dd0c6bed63f84c41e723132aadebe4b2fddb920e79ad51fd44141c`. No constructor refinement or new launch accompanies this result.
