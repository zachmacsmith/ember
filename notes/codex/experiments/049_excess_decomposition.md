# 049: retained-core and lifting excess

This saved-result decomposition finds that **five of the seven successful Q regressions already have core excess above the full-source cyclic baseline excess**. No constructors, new seeds, source generators or physical trace calls were used. All 34 initial core Q values match independent saved native final Q (28 calls) or singleton anchor counts (six base cases).

For source size `n`, core size `c`, initial core qubits `Qc`, final qubits `Q`, and `e=n−c` eliminated vertices:

- Core excess is `Qc−c`.
- Signed lifting excess is `Q−Qc−e`.
- Baseline excess is `Qbaseline−n`.

Their exact identity is `ΔQ = core excess + lifting excess − baseline excess`. Lifting includes growth or pruning of old chains, so it is not the excess length of newly inserted chains alone. Negative values are possible: the BCC case has lifting excess −2.

Across the seven regressions, core excess is **337**, baseline excess **275**, and lifting excess **57**: `62+57=119` extra qubits. Cubic lattice is the clearest core case: core excess134 versus baseline91, plus lifting1, produces its44Q loss. Planted solution and grid instead enter lifting below the baseline excess by8 and1, but add20 and5, producing12Q and4Q losses.

Across all **17 completed reduced inputs**, core excess1117 plus lifting130 is1247, versus baseline1258: the existing −11Q aggregate. Two other reduced inputs fail and have no final lifting decomposition. The15 unreduced inputs are exact Q ties. Their records remain in `all34.json`.

| Input | Membership | n→core | Core Q | Core excess | Lift excess | Baseline excess | ΔQ |
|---|---|---:|---:|---:|---:|---:|---:|
| 2229 | star | 127→1 | 1 | 0 | 10 | 10 | +0 |
| 31536 | random_planar | 152→109 | 195 | 86 | 22 | 136 | -28 |
| 34404 | planted_solution | 133→25 | 28 | 3 | 20 | 11 | +12 |
| 33402 | bcc_lattice | 91→59 | 105 | 46 | -2 | 59 | -15 |
| 2030 | path | 141→1 | 1 | 0 | 0 | 0 | +0 |
| 37761 | named_special | 46→28 | 39 | 11 | 8 | 4 | +15 |
| 32122 | kagome | 131→105 | 144 | 39 | 9 | 23 | +25 |
| 1584 | grid | 128→104 | 140 | 36 | 5 | 37 | +4 |
| 31357 | lfr_benchmark | 100→56 | 104 | 48 | 30 | 79 | -1 |
| 1829 | cycle | 126→1 | 1 | 0 | — | 0 | FAIL |
| 4083 | generalized_petersen | 126→77 | 151 | 74 | 11 | 73 | +12 |
| 2429 | wheel | 127→1 | 1 | 0 | — | 66 | FAIL |
| 32616 | frustrated_square,king_graph | 121→117 | 221 | 104 | 2 | 119 | -13 |
| 5058 | tree | 121→1 | 1 | 0 | 0 | 13 | -13 |
| 30736 | sbm | 120→119 | 571 | 452 | 0 | 488 | -36 |
| 4905 | binary_tree | 127→1 | 1 | 0 | 0 | 9 | -9 |
| 32367 | honeycomb | 190→90 | 134 | 44 | 11 | 70 | -15 |
| 33018 | shastry_sutherland | 121→97 | 137 | 40 | 3 | 36 | +7 |
| 33219 | cubic_lattice | 125→117 | 251 | 134 | 1 | 91 | +44 |

**Lesson and limits.** A next quality hypothesis should address the filled core's retained cost as well as lifting. This is an arithmetic localization, not causal proof: fill changes the constructed graph and search history, and later pruning can offset an expensive core. The equal-Q shared configurations do not establish identical physical core placements. The failed cycle and wheel retain prefix excess20 and30 respectively; those use only97 and80 actually inserted vertices and must not be confused with completed lifting excess. Coverage repair and quality remain separate empirical questions. This is one seed on reused development inputs, with no MM comparison or novelty claim.

Frozen runner, all34 records, reduced19 and regression7 tables, exact input hashes and equations are under `results/codex/049-results-review/excess-decomposition/analysis001`. The original049 report and050 analyzer are unchanged. Re-run `decompose.py` only after selecting a new output directory in a separate copy; its fixed `analysis001` destination refuses overwrite.
