# Codex research records

Initial session: 2026-09-07; branch `codex`, starting from `81074562`.
Current constraints: one novel non-portfolio algorithm, no MM or busclique in its
execution, ideal Z12, primary mean ACL, runtime roughly within MM's order of magnitude.
An independent native constructor and bounded joint contact reconstruction are
implemented and tested in an environment without MM. No algorithm has yet
demonstrated the requested superiority across graph families. The current
research candidate uses structural group coverage and permits equal-size contact
rearrangements only when an exact secondary objective improves; broader results
remain necessary, and novelty is unproved.

- [Final research plan](../../PLAN_CODEX.md)
- [Append-only user prompts](../../PROMPTS_CODEX.md)
- [Independent candidates and critiques](candidates.md)
- [Plan self-critiques and revisions](plan_self_critique.md)
- [Current heuristic specification](contact_search_spec.md)
- [Diagnostic exact model; superseded as runtime algorithm](joint_region_spec.md)
- [Algorithm/source audit and reproduction probes](algorithm_audit.md)
- [Benchmark/data audit and small test results](benchmark_audit.md)
- [Primary-source literature review](literature_review.md)
- [Cluster inventory and persistent execution design](cluster.md)
- [Session decisions and work log](session_log.md)
- [Completed first Z12 ablation and remaining MM gaps](experiments/011_results_review.md)
- [Actual Ember corpus provenance and missing inputs](experiments/012_corpus_selection.md)
- [Fixed corpus readiness selection](experiments/017_corpus_readiness.md)
- [Completed broad Ember screen and remaining quality/runtime deficits](experiments/019_results_review.md)
- [Contact rearrangement result and validation-cost correction](experiments/022_results_review.md)
- [Rejected distance-tree policy and lessons](experiments/023_contact_tree_ablation.md)
- [Broader contact-rearrangement experiment protocol](experiments/025_corpus_contact_rearrangement.md)
- [Complete contact-rearrangement results, including regressions](experiments/025_results_review.md)
- [Spectral initializer design and critique](spectral_initialization_spec.md)
- [Independent numerical and attribution review](spectral_initialization_review.md)
- [Fixed spectral integration experiment](experiments/026_spectral_initialization.md)
- [Corrected Sudoku development inputs and preserved original records](experiments/027_sudoku_development_supplement.md)
- [Geometric-search performance diagnosis and bounded improvement](geometry_performance_spec.md)
- [Sudoku comparison protocol and frozen supplementary run](experiments/029_sudoku_comparison_protocol.md)
- [Physical-qubit checkpoint hypothesis and preimplementation critique](physical_checkpoint_spec.md)
- [Generalization and final confirmation protocol](generalization_protocol.md)

Earlier audit recommendations favoring exact local construction are historical
inputs to the plan. User prompt 4 and the current heuristic specification supersede
them. Initial brainstorms and audits are preserved as historical records. Current
implementation and performance statements require the frozen source and complete
experiment artifacts linked from the later notes.
