# B029 complete-screen analysis preparation

2026-09-10. Analysis code is ready; it has not read or analyzed the running
constructor's outcomes. Root owns the frozen 54-call screen and its lifecycle.

The original Transfer002 audit assigned every extra comparator the same
`predecessor` label and therefore could not represent B029's six arms. Its
isolated `results/codex/b029-constructor/analyze.py` adapter changes only that
label expression to the actual method name. The original source hash is pinned;
reversing this expression proves full AST equality. The first targeted check
produced five distinct comparator labels and unchanged retained/MM labels in
0.052 s, with no validator or candidate calls. Validation and credit rules are
unchanged. The frozen screen references this corrected adapter.

The unexecuted `mechanism.py` adapts the B028 reader for B029, its fixed-anchor
ablation and paired B028. The six scalar/file/output helper functions retain
identical ASTs. All 54 terminal raw records must match the original audit's
hashes; that audit alone supplies success, Q/ACL, variability and time credit.
The 27 native receipt projections retain failures, first-valid observations,
sweeps, routing costs, union counters, compilation and terminal statuses.
Detailed first-sixteen/last visits are deduplicated and explicitly reported as
a sample; aggregate counters cover every visit. Exclusive timing stages and
overlapping dispatch receipts remain separate. Whole-process CPU is absent from
the existing pilot and remains unknown. No new correctness infrastructure,
trajectory replay or search is introduced.

`mechanism_identity.json` binds the frozen source snapshot, manifest, exact
methods, screen, oracle, audit adapter and reader. The code, full diff and eight
preparation bindings are ready for root review in `mechanism_preparation001.json`.
The sampled receipt projection does not independently certify intermediate
states or establish generalization; complete audited results decide whether
the mechanism continues.
