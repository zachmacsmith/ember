# C019 implementation preparation

2026-09-10 UTC. Root authorized the fixed contract SHA
`f996952fdb1db4f8ab94d70abbd3adf6f66f2f5d562f96e7b571a69797b27db9`
for isolated implementation and one focused guarded packet, with source review
before that packet executes. No development call or launch is authorized here.

New files are `joint_star_construction.py`, `joint_star_kernels.py` and
`tests/test_codex_joint_star_construction.py`. Separate public entrypoints expose
weighted and cardinality-only assignment; the constructor, root/growth policy,
true proposal scores, acceptance and clocks are shared. Root owns registry,
freezes and all remote work. Existing modules and validators remain unchanged.

The implementation copies C018's wall meter, hash-pinned support loading,
normalization/initialization convention, distance-cache structure and final
error/deadline handling into the new module. It does not import or call C018's
constructor. BFS/contact counting kernels retain their reviewed operation, while
the new root/growth proxies and exact integer assignment have separate kernels.
Hungarian search returns after each column scan for a wall check; root/growth
scans likewise resume in batches. Batch size is an observation interval only.

Specific risks are weighted matching with dummy sites and forbidden edges;
subtracting old internal source-edge gaps; consuming an assigned boundary site;
protecting long-chain neighbors from leaf selection; invalidating every actually
changed owner's fields; and retaining the latest certified equal-Q/R-improving
geometry when strict-Q events do not change. Every visit keeps scalar outcomes
and phase costs; full maps are limited to labeled initial/first-valid/terminal
and returned-state diagnostics. Unfinished proposals cannot publish.

Implementation arithmetic uses checked bounds before compiled signed integer
costs/potentials. An overflow is an instrument ERROR, never a work limit or
infeasibility finding. No new algorithm allocation, constraint or active cap is
introduced. First source/check bytes and any failed packet will be preserved.

The first packet is prepared, not executed: four focused cases cover the
specified risks, with tiny assignment enumeration, actual shared-site competition,
a degree-six center on a maximum-degree-three target, protected long neighbors,
cache changes, interrupted assignment/growth/publication, latest equal-Q/R state,
both tiny public entrypoints and final-deadline/post-valid-error rejection.
It uses the unchanged original-label oracle and C018 guard behavior. There are
four planned tiny public calls and zero development calls. No broad suite or
performance probe is included.

Before freezing, root's static review identified a counter-accounting edge:
`boundary_summary` now lies inside the existing `try/finally`, so a deadline
immediately afterward retains its work count. Admission timestamps are captured
after certification and first-map diagnostic preparation, immediately before
publication. These are accounting clarifications; root/growth/assignment and
acceptance policies are unchanged. No executable check has run yet.
