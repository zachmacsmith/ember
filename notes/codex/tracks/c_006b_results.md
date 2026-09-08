# C006b: additional time does not complete the harder inputs

The [prespecified 60-second follow-up](c_006b_longer_allowance.md) rejects extra time alone as a sufficient remedy: C006 remains 4/8 successful. Every timely candidate/MM quality pair still loses on Q. The four early-success embeddings and their work counters replay C006 exactly; no algorithm policy changed.

All 64 source files, eight original inputs, ideal Z12, seed 0, method configurations and paired method order are byte-identical to C006. Each fresh candidate and MM process received 60 seconds on hyde04. Only task timeout/identity and the new manifest's creation time/task list changed. This is an unchanged-algorithm budget experiment on repeatedly examined development inputs.

| Family / graph | Final missing at 15s → 60s | C006b Q / ACL | Fresh MM Q / ACL | Solver seconds C / MM |
|---|---:|---:|---:|---:|
| path / ember_2030 | 0 → 0 | 313 / 2.220 | 141 / 1.000 | 0.226 / 0.146 |
| tree / ember_5058 | 0 → 0 | 207 / 1.711 | 121 / 1.000 | 0.177 / 0.135 |
| grid / ember_1584 | 0 → 0 | 367 / 2.867 | 134 / 1.047 | 0.361 / 0.365 |
| random_planar / ember_31536 | 0 → 0 | 457 / 3.007 | 281 / 1.849 | 0.577 / 0.566 |
| random_er / ember_6450 | 190 → 161 | timeout | 1044 / 7.850 | 59.501 / 8.346 |
| regular / ember_14334 | 337 → 232 | timeout | 2114 / 15.100 | 59.501 / 42.769 |
| complete / ember_1041 | 146 → 3 | timeout | 1913 / 15.063 (late) | 59.503 / 60.796 |
| sbm / ember_30736 | 90 → 82 | timeout | 638 / 5.317 | 59.501 / 4.156 |

Continued search reduces the independently recounted final missing-edge counts on all four failures. The complete graph reaches a logged best count of two at visit 6,446, then performs 6,117 further visits without improvement and ends with three missing edges. Its best intermediate map was not saved; the final three-edge deficit is independently verified. ER, regular and SBM finish with logged best counts 157, 231 and 75. These results indicate improvement followed by difficult remaining contacts, not completed embeddings or a proof of permanent stagnation.

Hard-input search visits increase from 25,383/8,379/3,013/29,013 to 107,707/36,109/12,563/121,735. BFS adjacency examinations increase from 59.1/74.5/76.2/55.5 million to 237.0/308.8/316.4/225.2 million. All initial region maps and overlapping saved improvement records agree exactly. Every failed partition remains connected and disjoint, with independently recounted Q exactly equal to its fixed allocation: 540/1,680/3,556/484. Neutral and accepted transitions between logged improvements were never saved, so full intermediate-state replay is not claimed.

MM succeeds on seven inputs within the allowance; its complete-graph embedding is valid but late and receives diagnostic quality only. Candidate failures stop near 59.5 seconds under the unchanged validation reserve. On the four timely pairs, candidate/MM solver ratios are 1.55/1.31/0.99/1.02 and process ratios 1.22/1.11/approximately 1.00/1.06. These single-run measurements support no broad speed claim; historical times are kept separate.

The saved-data audit passed all 163 archive hashes, original-label validation, contact/contraction accounting and explicit partial-Q conservation. No solver or test-suite rerun occurred during analysis. [Results and saved traces](../../../results/codex/track-c-006b/review/results.json), [CSV](../../../results/codex/track-c-006b/review/pairs.csv), [decision](../../../results/codex/track-c-006b/review/hypothesis.json) and [manifest](../../../results/codex/track-c-006b/review_manifest.json) retain every outcome and cost. Retain distinct-neighbor initialization, but change the search mechanism before another screen; increasing this timeout again is unsupported. Novelty, family-level means/variance and generalization remain unproved.
