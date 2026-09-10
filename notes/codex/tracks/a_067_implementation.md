# A067 implementation: ready for source review and the complete screen

2026-09-10. **The four focused tiny-check groups passed on their first execution.**
This implements the reviewed [A067 decision](a_067_contact_coverage_decision.md).
No complete development constructor, MM comparison or cluster action occurred.
A066's rejected policy, three regressions, large sparse runtime gaps and late
useful large-instance improvements remain unchanged.

Two isolated files were added under `packages/ember-qc/src/ember_qc/algorithms/factored/`:
- `contact_coverage_reconstruction.py` overrides ordinary reconstruction's path
  selection in an inherited A065 context and imports the unchanged A066 search.
- `contact_coverage_construction.py` exports `contact_coverage_embed`, with one
  unchanged A061 construction and the same wrapper deadlines, final reserve,
  final validation, strict-Q acceptance and pair policy as A066.

The new path selector performs multi-source BFS from the entire growing tree.
Each discovered site retains one canonical shortest-path predecessor and the
union of distinct missing contact groups along that actual path. Exact integer
cross products compare added sites per newly reached group; ties prefer fewer
sites and then the existing seeded endpoint rank. Site-contact masks are cached
only within one reconstruction. The new mask cache is discarded when that
reconstruction ends.

The proof-based depth stop uses the total number of still-missing groups as an
upper bound on any path's benefit. Its strict inequality preserves tied layers;
it makes no claim about all equal-length paths or global minimum Q. The next
fringe can already be materialized when the following layer is excluded; that
work remains charged. There is no intermediate-tree Q cutoff, source-family
condition, root/owner cap, fixed mask width or production exact solver.

All mask construction/union/counting, site/edge visits and selections belong to
the existing reconstruction phase and deadline. New counters identify searches,
bound closures, exhausted searches, extension sites and distinct groups gained.
They are diagnostics, never active work limits. Final witness selection and tree
trimming are identical to A063. Search preparation, root ranking, scheduling,
atomic admission and invalidation are inherited unchanged.

Static AST review confirms unchanged operator lifecycle, wrapper `_run`, public
entry behavior and final witness/trim code, apart from new function and identity
names. All five bound prior source files remained unchanged. Reading the package's
Python >=3.9 declaration prompted an exact portable bit-count fallback before
any check execution; the frozen Python 3.10 native environment uses `int.bit_count`.
This is a pre-execution compatibility correction, not a failed experiment repair.

First-pass checks cover:
1. The reviewed five-free-site fixture: independently valid focus trees of four
   versus three sites, and an unchanged nearest-choice control.
2. Repeated contacts at sites and along a path, 70 contact groups without mask
   truncation, the portable count function, and final trimming that removes the
   starting root. The high-degree fixture is a unit case, not Z12 evidence.
3. A later endpoint winning a tied BFS layer, retaining the equality layer of
   the depth bound, and excluding a provably inferior deeper layer.
4. Interruption during mask expansion and after partial private tree growth,
   preserving the incumbent; valid strict-Q admission through the existing
   search; and one stubbed-base wrapper call through final validation, followed
   by independent oracle validation of its returned map.

The original independent oracle and import guard were reused. MM, `_minorminer`
and busclique were physically absent; there were zero forbidden import attempts,
failures, errors or changed bindings. Process wall was 2.310227 seconds; test-body
wall was 0.733843 seconds. The tests construct only literal tiny fixtures; there
were zero complete development constructor calls and exactly one stubbed-base
wrapper call. No exhaustive suite or additional trial was run.

Evidence is in `results/codex/a067-implementation/`: before-implementation record,
static source review and wrapper diff, 17-file check freeze, first action record,
full test log and summary. Root owns registry, source review, freeze and the
reviewed 60-call complete screen with fresh Transfer004 inputs, all three A066
regression anchors and separate A065/A066/A061/MM controls.

Coverage per site remains a local proxy; fixed donor geometry and canonical path
selection remain restrictive. Per-root cost may increase and complete trajectories
may regress. The tiny positive fixture supplies correctness evidence only. The
next decision must use complete outputs and incumbent trajectories, not more local
repair experiments or a presumed runtime improvement.

SHA256: core `b7dc49630410e1cd5bc5086d3b50dbb2b2e3a8bef91eb026483d7bfc8cc25c62`;
wrapper `438a2bdb9ff0ed2425f742e3aa07ec63d8570f2cca60de21a6d41530bfa35abf`;
checks `7b7e8717526e8d534dca01897240b81c883031f0c67a1ce628f80a34c4acf1b8`;
check freeze `7f6afe5a4ef4eeffe296bea55b12b422d890fbfab1e4d7af02fd8584afa1bd2b`.
First check summary `c6b050c556c3553d8344db34388c40d8e86333c091f892f116d753a3e64cc03f`.
