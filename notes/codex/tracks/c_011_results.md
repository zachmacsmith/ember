# C011: removing work denial did not recover complete embeddings

The wall-limited ablation and unchanged C010 control each completed **2/8** inputs; fresh stock MM completed **6/8**. Both candidate successes are the path and tree, with optimal ACL 1 and the same Q as MM. No harder input was gained or existing success lost. Retire this fixed ablation; C010 remains retired. This is one exploratory seed on eight repeatedly exposed development inputs, not confirmation or evidence against every adaptive-clone constructor.

[All 24 rows](../../../results/codex/track-c-011-review/analysis001/table.csv) retain unsuccessful calls and their costs. Cells below give status, credited Q when valid, and solver seconds. F means FAILURE; T means TIMEOUT. The wall arm's failures stopped at the reserved search deadline, finished final inspection within 15 seconds, and returned no credited embedding.

| Input | C010 control | Wall ablation | Fresh MM |
|---|---:|---:|---:|
| path 2030 | S 141 / .385 | S 141 / .453 | S 141 / .143 |
| tree 5058 | S 121 / .350 | S 121 / .422 | S 121 / .133 |
| grid 1584 | F / .444 | F / 14.515 | S 134 / .347 |
| planar 31536 | F / .451 | F / 14.503 | S 281 / .574 |
| ER 6450 | F / .333 | F / 14.503 | S 1044 / 8.370 |
| regular 14334 | F / .399 | F / 14.506 | T / 15.284 |
| complete 1041 | F / .659 | F / 14.511 | T / 17.394 |
| SBM 30736 | F / .338 | F / 14.503 | S 638 / 4.085 |

The controlled comparison worked: every fully recorded control visit matched the treatment prefix after removing wall fields; all six treatment crossings of 19M exactly matched the control's denied charge. No prefix was mismatched or unavailable. These are saved decision/charge comparisons, not assertions about unsaved intermediate states. [Prefix receipts](../../../results/codex/track-c-011-review/analysis001/prefixes.json) preserve that limit.

Removing conservative work denial allowed 416–926M charged units on each harder input, versus about 19M. Nevertheless, 16,065 local revisions produced only 24 commits: 16,037 ended without an admissible site and four were interrupted. The treatment committed 6,326 splits; two further splits were interrupted. Its final harder-input states placed 1,537/2,087, 88/857, 97/930, 144/1,113, 98/1,266 and 81/873 clones respectively. All fail original-minor validity. Grid has M=0 but disconnected chains; the others also retain missing contacts. Failed local revision does not prove a split necessary, and partial placement does not establish an adequate global representation.

This rejects **unused wall time as a sufficient remedy for this policy**. It implicates the finite revision/splitting choices and their coordination, while leaving representation, greedy acceptance and ordering confounded. Initial input/setup took .863 seconds of the treatment's 87.915 total solver seconds; placement/splitting took 86.585. Preprocessing did not dominate the extended run. Charged bitset words are accounting units, not measured CPU operations.

All-attempt solver/CPU/process totals were control **3.359/3.358/5.330s**, treatment **87.915/87.911/91.759s**, MM **46.332/46.330/48.344s**, including MM's two late calls. The two common timely pairs give treatment/MM median solver ratio **3.165**. The frozen screen fails its ≥6 successes, ≥3 Q wins/ties and ≤3 ratio criteria. That last threshold is this experiment's historical rule, **not the user's runtime requirement or a universal promotion gate**; quality comes first with runtime roughly in MM's range.

The one saved-data audit passed without errors after checking all 237 archived files, original-label embeddings, auxiliary owner trees/edge identities, snapshots, deadlines and retained exceptions. Full costs and failure stages are in [receipt_summary.json](../../../results/codex/track-c-011-review/receipt_summary.json); exact provenance and the single invocation are bound by [review_manifest.json](../../../results/codex/track-c-011-review/review_manifest.json). No solver was rerun for this report.
