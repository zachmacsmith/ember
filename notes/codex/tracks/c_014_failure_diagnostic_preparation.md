# C014 saved-prefix diagnostic preparation

2026-09-09. **Prepared for root review; the three development-prefix diagnostics have not run.** The before-code hypothesis, pseudocode, falsifier, self-critique and staged authorization are in [the failure review](c_014_failure_review.md). C014 remains rejected. No new routing, exact solve or constructor refinement was implemented.

The separate [diagnostic](../../../results/codex/c014-failure-diagnostic/diagnostic.py) decodes selected private states from rank-encoded scores; checks birth counts, Q, reintroduction chronology and selected-root identity; validates induced partial minors with the unchanged original oracle; and recomputes every recorded rejected tree's capacities and old-owner deficits. It then computes complete components after excluding zero-allowance boundary sites and evaluates all 140 saved previous-placement/contact-tree combinations. It preserves duplicate proposals, selected-chain controls, all quota violations and all independent validation failures. A changed prior placement must itself be admissible, as must the combined state, before a diagnostic witness is recorded. This examines saved choices only.

The [extractor](../../../results/codex/c014-failure-diagnostic/prepare.py) reads only the three candidate terminal records, their frozen graphs, target topology and existing common-audit bindings. Its 758,800-byte packet contains three compact candidate records, target nodes/edges and the unchanged oracle. It contains no constructor source, MM embedding, hidden witness or private original-label map. Candidate graphs keep their frozen node ordering, permitting exact internal-index to solver-label conversion. Extraction does not decode the score, validate the minor or evaluate a counterfactual.

Four [focused synthetic check groups](../../../results/codex/c014-failure-diagnostic/test_diagnostic.py) passed on the first attempt:

- Nonidentity rank inversion, invalid permutation, duplicate and foreign target ranks, and owner-order errors.
- Distinct free sites rather than coupler multiplicity, including the decrement of an old owner's remaining count when x is its original neighbor.
- A genuine zero-allowance cut and a surviving component that nevertheless fails the new owner's capacity requirement.
- A changed previous chain that contacts x but loses an earlier required contact: the independent oracle rejects it despite safe capacity counts.

The check process used `-I -S -B`, imported only stdlib and the unchanged oracle, and read zero development cases. Internal check wall/CPU were 0.000437/0.000437s; recorded process wall was 0.055730s. Input preparation passed first attempt in 1.456190s internally, 1.517500s process wall. Both stderr files are empty. These are synthetic correctness and extraction results, **not evidence that the three decoded development prefixes or any alternative pass**.

Exact input and code bindings are saved in `results/codex/c014-failure-diagnostic/preparation001.json`. Packet manifest SHA256 is `912641bca35af0bbfedb304d55590c97c4bea340d82429cae49f5163f8af3d91`; diagnostic SHA256 `46fe6336241e77af052d77aafe8cbf380dc1d342f96aea592d77cda61101186c`; checks SHA256 `943800c038d6050b7adf0f88a181c7e0f05b14b0b9a2d610b21d714e072d4fae`; extractor SHA256 `b4192646fa4d79af501632fb773f42863a89793f1ebebd971524daea4cd47463`.

Next action is root code/check review, then one recorded isolated diagnostic execution if authorized. No additional routing or exact-solver work is authorized. A negative recorded-choice result is not exhaustive over earlier placement changes; a surviving component is inconclusive; and even a positive witness cannot establish complete-constructor quality or revive the rejected policy.
