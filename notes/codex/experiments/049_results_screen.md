# 049: reduced-core construction screen

**Do not promote this prototype.** It succeeds on **32/34** inputs versus **34/34** for the cyclic pipeline. Among 32 common successes, it has **eight lower-Q results, seven higher-Q results and 17 ties**. Total Q is 14,539→14,528 (11 fewer), but mean per-input ACL worsens slightly, **3.41705→3.42080**. Lower summed Q does not imply lower macro ACL when input sizes differ.

All 66 complete successful outputs independently validate against the original graphs. The two failures retain valid partial minors against independently reconstructed active requirements. `ember_1829` (cycle) stops inserting vertex 114 after placing **98/126** vertices, at partial Q118. `ember_2429` (wheel) stops inserting vertex 125 after **81/127**, at partial Q111. These are **insertion-blocked failures**, not deadlines or work-limit stops. The wheel hub still has 85 distinct free neighboring sites for 46 pending demands; that count did not ensure successful bounded insertion touching all three required neighbors. A successful nearby tiny wheel fixture did not predict this corpus result.

Reduction affects 19 inputs and eliminates 1,244 source vertices. The other 15 keep their complete source as the core and produce identical Q, with solver totals increasing **107.982→111.401 seconds**. All **28 native core calls succeed**; six inputs use the edgeless base case. Thus the observed failures occur during lifting, not core construction.

Across all attempts, solver totals fall **195.046→179.465 seconds**, and process totals 217.816→201.892 seconds. The common-success solver totals are 185.862→176.674 seconds, but the paired median ratio is **1.02848**, so the typical input is slightly slower. Path and star retain Q at about 0.97 and 0.81 seconds; the two tree inputs reach ACL1 at about 0.79 and 0.82 seconds. These descriptive successes do not justify selecting methods by family.

Treatment core-call wall is **160.208 seconds**, expansion wall **14.160 seconds**, and reduction wall **0.0453 seconds**. Validation accounts for **7.386 seconds within those phases**, not an additional cost. There are 1,170 committed insertions and 91 committed released-fill deletions. The 391 staged pruning deletions include private alternatives and are not net pipeline savings. Every input remains below its 20-million scan limit; the largest uses 4,567,157 scans.

The frozen screen passes provenance, journal/reverse-fill, committed-partial validity, signed-Q, work and timing checks on all 68 rows and 35 memberships. It performs no intermediate physical trace replay. This is one seed on reused inputs, without an MM arm or across-run variance estimate. All statuses, ACL, timings and diagnostic costs remain in [pairs.csv](../../../results/codex/049-results-review/screen001/pairs.csv), [rows](../../../results/codex/049-results-review/screen001/rows.json) and [summary](../../../results/codex/049-results-review/screen001/summary.json).

Negative delta favors reduced-core. `FAIL` has no credited quality.

| Input | Membership | Cyclic Q | Reduced Q | Delta Q |
|---|---|---:|---:|---:|
| ember_22972 | watts_strogatz | 1694 | 1694 | +0 |
| ember_2229 | star | 137 | 137 | +0 |
| ember_4755 | hypercube | 452 | 452 | +0 |
| ember_31536 | random_planar | 288 | 260 | -28 |
| ember_5242 | johnson | 837 | 837 | +0 |
| ember_34404 | planted_solution | 144 | 156 | +12 |
| ember_6450 | random_er | 881 | 881 | +0 |
| ember_33587 | weak_strong_cluster | 426 | 426 | +0 |
| ember_10662 | barabasi_albert | 424 | 424 | +0 |
| ember_33402 | bcc_lattice | 150 | 135 | -15 |
| ember_3499 | circulant | 193 | 193 | +0 |
| ember_2030 | path | 141 | 141 | +0 |
| ember_37761 | named_special | 50 | 65 | +15 |
| ember_32122 | kagome | 154 | 179 | +25 |
| ember_1584 | grid | 165 | 169 | +4 |
| ember_3060 | turan | 460 | 460 | +0 |
| ember_31357 | lfr_benchmark | 179 | 178 | -1 |
| ember_1041 | complete | 1180 | 1180 | +0 |
| ember_1829 | cycle | 126 | FAIL | — |
| ember_1363 | bipartite | 566 | 566 | +0 |
| ember_4083 | generalized_petersen | 199 | 211 | +12 |
| ember_14334 | regular | 1301 | 1301 | +0 |
| ember_2429 | wheel | 193 | FAIL | — |
| ember_5411 | kneser | 409 | 409 | +0 |
| ember_37603 | hardware_native | 248 | 248 | +0 |
| ember_32616 | frustrated_square,king_graph | 240 | 227 | -13 |
| ember_5058 | tree | 134 | 121 | -13 |
| ember_30736 | sbm | 608 | 572 | -36 |
| ember_4905 | binary_tree | 136 | 127 | -9 |
| ember_32367 | honeycomb | 260 | 245 | -15 |
| ember_33018 | shastry_sutherland | 157 | 164 | +7 |
| ember_33219 | cubic_lattice | 216 | 260 | +44 |
| ember_31879 | triangular_lattice | 275 | 275 | +0 |
| ember_37302 | spin_glass | 1835 | 1835 | +0 |

Screen `dc4f96fb`, journal checker `3d431c13`, runtime snapshot `73564a80`, and task manifest `f34b975a` are bound in the [review manifest](../../../results/codex/049-results-review/manifest.json). Archive digest: `1a05e6e4ed3a0cf838fa9bba19ebaff7d3384a02bb8c94479d7381bf7cc3b16d`. Root confirmed quiescence before the screen's single execution; no candidate or converter was called by the screen.

```sh
.venv/codex-native/bin/python -I -B results/codex/049-results-review/screen.py --archive results/codex/retrieved/hyde03/049-reduced-core-pipeline --archive-digest 1a05e6e4ed3a0cf838fa9bba19ebaff7d3384a02bb8c94479d7381bf7cc3b16d --out results/codex/049-results-review/screen002
```
