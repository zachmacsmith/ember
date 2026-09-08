# Track C002: connected source aggregates and feasible connected splits

This revision is specified before its implementation or C002 outcomes. C001 remains frozen: zero of eight inputs produced an embedding, with independently valid partial quotient minors. Its stopping records reveal avoidable structural restrictions in addition to the deeper future-boundary problem.

**Hypothesis.** Preserve source connectivity during matching, spend local searches only on seeds whose removal leaves a connected donor with its required contacts, and treat proportional region size as a soft objective. This should remove C001's artificial source fragmentation, impossible seed attempts, and rejection of already feasible child partitions. The core remains a single contact-constrained uncoarsening constructor, not a mixture of methods or a graph-specific exception.

```text
coarsen source:
    within a level match only adjacent current aggregates; carry unmatched ones
    if the entire quotient has no edges, pair its disconnected components to finish the hierarchy
split one parent region:
    rank seeds by the same structural rule as C001
    remove seeds that are articulation vertices or consume a required donor's final contact
    run at most six remaining seeds, with the same connected boundary-transfer search
    try to reach the proportional resource target
    if further growth is blocked, accept only if both children already satisfy all
        connectivity, nonempty, source-degree capacity, and required-contact constraints
    certify the split before publishing; otherwise preserve failure and move to the next seed
finish:
    unchanged original-source validation, site deletion and final deadline validation
```

All prefilter, source-matching and certification work is charged under the original absolute deadline. No whole-constructor restart is added. The six-search cap, degree bounds, target handling and trimming policy remain unchanged. A separate module preserves V1 exactly and reuses only its structural utility functions; it does not call V1's constructor. The ordinary paired pilot and independent original-label oracle remain the evaluation path.

**Self-critique.** These corrections are necessary tests of the original concept, not a proof that the concept is sound. Connected aggregates can still require contacts that cannot be separated inside a fixed physical region. Soft balance can leave a child with enough degree-bound capacity but insufficient useful boundary arrangement for later splits. Feasible-seed filtering may increase preparation cost and does not make the six remaining local searches exhaustive. No setting was chosen to fit a particular family, and these three rules are applied to every input. No new novelty claim is added: multilevel partitioning remains established prior art as documented in `c_multilevel.md`.

**Cheap falsifier.** Keep the exact C001 eight-input panel, ideal Z12, seed 0, 15 seconds per method, and hyde04's pinned isolated environments. Run the single V2 candidate and fresh stock MM in separate paired processes, preserving all outcomes and actual wall time. Before the screen, use tiny structural fixtures to check connected source aggregates, infeasible-seed filtering, a contact-valid partition blocked only by optional balancing, and late output rejection. Fewer than four timely valid candidate embeddings again rejects this version as a useful general constructor. If the mechanism still fails at coarse region boundaries, replace or substantially redesign the strict parent-region restriction instead of increasing seed counts or time limits.
