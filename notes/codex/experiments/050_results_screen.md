# 050: blocked reinsertion restores both missing completions

The frozen saved-result screen passed on its first execution: **34/34 treatment successes versus32/34 control successes**, with **all32 common Q ties**. All66 complete outputs pass independent validation against original source labels and target edges; both control failures retain valid partial minors against reconstructed requirements. All68 statuses,35 memberships and34 input pairs are preserved. There are no timeouts, dependency violations, internal errors or exhausted repair allowances.

The only repair calls are the preidentified cycle and wheel obstructions. Cycle `ember_1829` relocates owner68 while inserting114: entryQ118→120,80,381scans,0.046145s. Wheel `ember_2429` relocates owner12 while inserting125: entryQ111→116,148,083scans,0.091650s. Both return and commit the first complete one-owner block; four internal insertions reconstruct the two blocks. Subsequent ordinary lifting completes cycle at **Q155/ACL1.23016** and wheel at **Q183/ACL1.44094**. These seven added sites at the repaired steps are signed insertion growth, not contraction savings. No extra fill pruning occurs inside either repair.

Repair cost totals **228,464scans and0.137795s**, already included in global/expansion cost. Across all34 attempts, solver wall is **179.162→185.530s** and process wall **201.481→208.071s**. Expansion rises14.058→20.045s, partly because the two rescued runs now finish74 additional insertions. Core wall is160.043→159.583s. Validation is an overlapping subtotal,7.333→10.592s; do not add it to phase totals. On32 common successes, solver wall is176.391→179.443s; the median paired ratio is1.0107. This single same-host run does not establish the cause or repeatability of small timing changes.

Core Q matches across every pair and independently matches saved native final Q or anchor counts. The unchanged32 complete cases total14,528Q with macroACL3.420797 on both arms. The treatment's all34 total14,866Q has wider coverage and must not be compared directly with the control's32-success total. All1,244 reverse insertions complete in the treatment; its maximum global work is5,635,728scans, below20M. Accepted repair, returned certificate, signed Q, actual cleanup and nested work receipts reconcile exactly.

| Input | Membership | Control Q | Repair Q | Control s | Repair s |
|---|---|---:|---:|---:|---:|
| 22972 | watts_strogatz | 1694 | 1694 | 8.944 | 9.013 |
| 2229 | star | 137 | 137 | 0.808 | 0.970 |
| 4755 | hypercube | 452 | 452 | 5.652 | 5.624 |
| 31536 | random_planar | 260 | 260 | 6.022 | 6.300 |
| 5242 | johnson | 837 | 837 | 6.945 | 6.913 |
| 34404 | planted_solution | 156 | 156 | 2.861 | 3.121 |
| 6450 | random_er | 881 | 881 | 6.770 | 6.797 |
| 33587 | weak_strong_cluster | 426 | 426 | 6.318 | 6.373 |
| 10662 | barabasi_albert | 424 | 424 | 6.139 | 6.181 |
| 33402 | bcc_lattice | 135 | 135 | 3.986 | 4.095 |
| 3499 | circulant | 193 | 193 | 4.896 | 4.936 |
| 2030 | path | 141 | 141 | 0.949 | 1.156 |
| 37761 | named_special | 65 | 65 | 2.312 | 2.382 |
| 32122 | kagome | 179 | 179 | 4.562 | 4.680 |
| 1584 | grid | 169 | 169 | 4.519 | 4.611 |
| 3060 | turan | 460 | 460 | 5.937 | 6.013 |
| 31357 | lfr_benchmark | 178 | 178 | 4.656 | 4.913 |
| 1041 | complete | 1180 | 1180 | 12.056 | 12.086 |
| 1829 | cycle | FAILURE | 155 | 1.253 | 2.337 |
| 1363 | bipartite | 566 | 566 | 6.693 | 6.689 |
| 4083 | generalized_petersen | 211 | 211 | 5.197 | 5.552 |
| 14334 | regular | 1301 | 1301 | 8.047 | 8.021 |
| 2429 | wheel | FAILURE | 183 | 1.518 | 3.750 |
| 5411 | kneser | 409 | 409 | 5.866 | 5.657 |
| 37603 | hardware_native | 248 | 248 | 4.853 | 4.862 |
| 32616 | frustrated_square,king_graph | 227 | 227 | 5.206 | 5.328 |
| 5058 | tree | 121 | 121 | 0.779 | 0.958 |
| 30736 | sbm | 572 | 572 | 6.196 | 6.190 |
| 4905 | binary_tree | 127 | 127 | 0.828 | 1.003 |
| 32367 | honeycomb | 245 | 245 | 6.480 | 7.022 |
| 33018 | shastry_sutherland | 164 | 164 | 4.621 | 4.723 |
| 33219 | cubic_lattice | 260 | 260 | 5.046 | 5.058 |
| 31879 | triangular_lattice | 275 | 275 | 5.368 | 5.302 |
| 37302 | spin_glass | 1835 | 1835 | 16.878 | 16.915 |

**Historical quality comparison only.** Against049's saved cyclic arm on the same34 inputs, A050 uses **14,866Q versus14,858Q (+8)**. MacroACL is **3.2981353184815916 versus3.2901595864724213**; there are9 lower-Q,8 higher-Q and17 tied inputs. Cycle is155 versus126Q, while wheel is183 versus193Q. Thus restored coverage does not establish an overall quality improvement over cyclic. This comparison uses saved quality only and supports no cross-run timing inference; the full pairs and input hashes are in `historical_quality.json`.

This supports retaining the blocked-only repair for reach within this development screen. It does not fix049's existing successful-output regressions or establish broad superiority, ACL variance, novelty or an MM result. The screen reconstructs the journal and committed partial requirements but does not replay unsaved intermediate physical chains or independently reconstruct every port-pool decision.

Run identities: source `f000a676…`, manifest `665a4214…`, retrieved455-file digest `c5c20efd…`. Root verified terminal quiescence before retrieval. Fetch001 was a local CLI syntax error, corrected by fetch002 without remote restart. Exact hashes, all rows and the full paired CSV are bound by `results/codex/050-results-review/manifest_v2.json`.
