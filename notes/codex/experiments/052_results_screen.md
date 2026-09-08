# 052: original requirements with soft guidance

**Reject promotion.** Honeycomb `ember_32367` exhausted the unchanged 20-million-scan allowance after 49 lifts: 139/190 vertices placed, Q362 in an independently valid partial minor. Solver time was 13.048 s; this was a work-limit failure, not a timeout. Its original core succeeded at Q90, but expansion consumed 10.497 s and stopped before an ordinary insertion returned a blocked result; no repair query ran. The failed insertion identity is unsaved. All 14 guide owners before failure were distinct: the proposed per-owner distance cache has **zero possible hits** on this prefix. Guide setup/BFS consumed 1,284,467 scans (6.42%). Keep caching unimplemented; it cannot remove this observed obstruction.

The one saved-data screen passed: all 68 rows retained, all 67 complete outputs original-valid and timely, with 34 inputs/35 memberships. Fresh fixed-050 control succeeded 34/34; treatment 33/34. Across 33 common successes, treatment had 6 lower-Q results, 6 higher and 21 ties: Q14,621→14,833 (+212), macro ACL 3.359004→3.412648. All-attempt solver time rose 185.731→208.621 s; process time 208.009→231.093 s. There were no internal errors or timeouts.

Core Q summed over all 34 attempts fell 13,407→13,168, yet completed lifting lost quality. Petersen `ember_4083` grew from Q211 to Q427 despite core Q151→77 and **no guide BFS**. Its expansion took 9.076 s. Wheel worsened Q183→225; cycle improved Q155→143. This tests original requirements plus guidance together, not guidance in isolation.

Historical 048 cyclic quality, evaluated on the same 33 successful treatment inputs, gives 7 wins, 9 losses, 17 ties: Q14,598→14,833 (+235), macro ACL 3.348394→3.412648. Its honeycomb also succeeded. This is a quality-only comparison; historical timing is not pooled.

Across all treatment attempts: 1,193/1,244 reverse insertions committed; all 28 native core calls succeeded, with six edgeless base cases. Physical core edges totalled 41,407 versus 42,027 filled-core edges. Guidance completed all 250 BFS calls: 22,932,263 scans plus 2,343 setup scans, 10.192 s BFS and 0.00146 s setup. Wheel alone invoked repair: two certified/committed queries, four blocks, six rebuild calls, 1,254,990 scans, 0.697 s and signed Q growth +10. Two guide calls (183,458 scans) occurred inside repair. These costs overlap global/expansion totals and must not be added again. No physical fill cleanup occurred; 518 staged pruned sites are private work, not net savings.

This single-seed exposed-input screen establishes neither general infeasibility nor a causal decomposition. Saved journals, partial requirements, counters and final chains were checked; unsaved intermediate chains, distance maps and chosen roots were not replayed. The raw archive and failed output remain unchanged.

| All-attempt cost | Fixed 050 | A052 |
|---|---:|---:|
| Global scans | 39,238,515 | 98,054,396 |
| Core wall (s) | 159.939 | 154.471 |
| Expansion wall (s) | 19.957 | 48.217 |
| Validation subtotal (s; overlaps phases) | 10.536 | 9.574 |

All control outputs below succeeded. `F` is the uncredited treatment failure; Q is total occupied qubits. Times are fresh 052 solver seconds. The historical Q column is saved 048 cyclic quality only. Complete ACL/process/counter fields and all 35 memberships are retained in `screen001`.

| Input / family | n | 050 Q | 052 Q | ΔQ | 050 s | 052 s | 048 Q |
|---|---:|---:|---:|---:|---:|---:|---:|
| ember_22972 / watts_strogatz | 174 | 1694 | 1694 | +0 | 8.962 | 9.227 | 1694 |
| ember_2229 / star | 127 | 137 | 137 | +0 | 0.979 | 0.967 | 137 |
| ember_4755 / hypercube | 128 | 452 | 452 | +0 | 5.708 | 5.645 | 452 |
| ember_31536 / random_planar | 152 | 260 | 260 | +0 | 6.266 | 6.246 | 288 |
| ember_5242 / johnson | 120 | 837 | 837 | +0 | 6.889 | 6.779 | 837 |
| ember_34404 / planted_solution | 133 | 156 | 142 | -14 | 3.088 | 4.333 | 144 |
| ember_6450 / random_er | 133 | 881 | 881 | +0 | 6.771 | 6.837 | 881 |
| ember_33587 / weak_strong_cluster | 128 | 426 | 426 | +0 | 6.372 | 6.377 | 426 |
| ember_10662 / barabasi_albert | 122 | 424 | 424 | +0 | 6.197 | 6.245 | 424 |
| ember_33402 / bcc_lattice | 91 | 135 | 110 | -25 | 4.122 | 3.373 | 150 |
| ember_3499 / circulant | 134 | 193 | 193 | +0 | 4.940 | 4.936 | 193 |
| ember_2030 / path | 141 | 141 | 141 | +0 | 1.154 | 1.147 | 141 |
| ember_37761 / named_special | 46 | 65 | 75 | +10 | 2.347 | 1.975 | 50 |
| ember_32122 / kagome | 131 | 179 | 160 | -19 | 4.711 | 4.982 | 154 |
| ember_1584 / grid | 128 | 169 | 183 | +14 | 4.583 | 5.047 | 165 |
| ember_3060 / turan | 90 | 460 | 460 | +0 | 5.921 | 6.068 | 460 |
| ember_31357 / lfr_benchmark | 100 | 178 | 184 | +6 | 4.959 | 5.459 | 179 |
| ember_1041 / complete | 127 | 1180 | 1180 | +0 | 12.188 | 12.135 | 1180 |
| ember_1829 / cycle | 126 | 155 | 143 | -12 | 2.313 | 7.128 | 126 |
| ember_1363 / bipartite | 126 | 566 | 566 | +0 | 6.597 | 6.663 | 566 |
| ember_4083 / generalized_petersen | 126 | 211 | 427 | +216 | 5.506 | 11.592 | 199 |
| ember_14334 / regular | 140 | 1301 | 1301 | +0 | 8.138 | 7.971 | 1301 |
| ember_2429 / wheel | 127 | 183 | 225 | +42 | 3.718 | 8.155 | 193 |
| ember_5411 / kneser | 126 | 409 | 409 | +0 | 5.657 | 5.776 | 409 |
| ember_37603 / hardware_native | 128 | 248 | 248 | +0 | 4.854 | 4.896 | 248 |
| ember_32616 / frustrated_square,king_graph | 121 | 227 | 227 | +0 | 5.225 | 5.228 | 240 |
| ember_5058 / tree | 121 | 121 | 121 | +0 | 0.948 | 0.947 | 134 |
| ember_30736 / sbm | 120 | 572 | 597 | +25 | 6.193 | 6.140 | 608 |
| ember_4905 / binary_tree | 127 | 127 | 127 | +0 | 0.990 | 1.018 | 136 |
| ember_32367 / honeycomb | 190 | 245 | F | — | 7.064 | 13.048 | 260 |
| ember_33018 / shastry_sutherland | 121 | 164 | 158 | -6 | 5.036 | 4.762 | 157 |
| ember_33219 / cubic_lattice | 125 | 260 | 235 | -25 | 5.102 | 5.159 | 216 |
| ember_31879 / triangular_lattice | 128 | 275 | 275 | +0 | 5.309 | 5.360 | 275 |
| ember_37302 / spin_glass | 160 | 1835 | 1835 | +0 | 16.927 | 16.998 | 1835 |


Evidence: [screen summary](../../../results/codex/052-results-review/screen001/summary.json), [all rows](../../../results/codex/052-results-review/screen001/rows.json), [historical/cache arithmetic](../../../results/codex/052-results-review/saved_comparison.json), [manifest](../../../results/codex/052-results-review/manifest.json). One screen execution, exit 0; no candidate reruns or physical trace expansion. Frozen screen command:

```sh
.venv/codex-native/bin/python -I -B results/codex/052-results-review/screen.py --archive results/codex/retrieved/hyde03/052-original-soft-guidance-pipeline --archive-digest 053a3e42e31ba881ec4528660bcb4ba1068519cfdad0f5769589bac2a19e3192 --out results/codex/052-results-review/screen001
```

The output directory is immutable; the command is recorded for provenance, not a request to rerun it. Manifest SHA256 `37b37635bd4b6eb8599556de5d633e1700181f4a2d80b428b3a052758db4fa6a`; archive digest `053a3e42e31ba881ec4528660bcb4ba1068519cfdad0f5769589bac2a19e3192`.
