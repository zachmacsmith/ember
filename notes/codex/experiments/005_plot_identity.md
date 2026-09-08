# Experiment 005: preserve problem identity in plots

Date: 2026-09-07. Branch: `codex`. Scope: `plots.py`, a dedicated regression test
file, and this note. No embedding algorithm or runtime selection policy changed.

## Identity audit and repair

The prior statistical repair in experiment 004 exposed several independent
plotting calculations that still used graph display names as identities. This
could merge different manifest graph IDs, target topologies, or configurations
into a single plotted point or success column. It also created false pairs and
false shared-success intersections.

`_identified_plot_rows` now calls the existing statistical `_problem_keys` helper
and assigns a local integer code to each source/target/batch tuple. The code is
used only for grouping within the plot. Display names remain labels; colliding
labels include available source ID, full target name, and batch provenance.
Existing category metadata takes precedence over name-based category inference.
Jitter uses the full identity representation and is stable under row reordering.

The helper preserves the same legacy warnings, unknown-component strata, custom
graph fallback, and mixed-version rejection as the statistical tables. It does
not introduce structural hashes, new database columns, or runtime algorithm
dispatch by graph ID or category.

The repaired paths are:

- Pareto points: separate successful-trial means for each algorithm and problem.
- Head-to-head points: use `_per_problem_means` directly, so graph, target, and
  configuration must match before two values form a pair.
- Consistency: compute trial variation within an identified problem before
  averaging coefficients of variation across problems.
- Success heatmaps and graph-indexed success: one column per identified problem,
  including distinct labels and a size guard that counts identities.
- Graph-indexed chain and time plots: distinct categorical positions and
  per-problem means; numeric jitter distinguishes the identities without changing
  the metric values.
- Shared-success intersection: intersect identified problems, and count those
  identities in the displayed success totals.
- Problem deep dive: a display name matching multiple identities raises a clear
  error instructing the caller to prefilter `graph_id`, `topology_name`, and/or
  `batch_id`. It no longer silently combines those records.

No `graph_name` groupby or name-only shared-success intersection remains in
`plots.py`. Intentional aggregations by graph size, density, category, or topology
retain their existing weighting. The shared-success bar means likewise retain
their documented successful-run weighting after the corrected intersection.

## Category and family win plots

Two additional paths previously grouped only by `graph_id` and selected the best
individual trial using `idxmin`. Consequently target/configuration distinctions
were lost, algorithms with extra trials had more opportunities to win, and ties
depended on input order.

These plots now compare each algorithm's mean successful ACL per identified
problem. A problem is eligible only if every algorithm represented in the input
frame attempted it and at least one algorithm succeeded. An absent experiment
does not become a failed embedding. Algorithms tied for the smallest mean share
one unit of win credit equally. This is explicitly an all-algorithm comparison,
distinct from the existing pairwise win-rate matrix.

The family win summary now follows its existing documented macro-average:
compute category win rates, then average the category rates equally. A category
containing many more graphs no longer silently receives more weight in that
particular summary. Labels and docstrings explain the minimum-mean ACL and tie
policy.

## Separately confirmed Pareto correctness bug

The audit found `_pareto_front` reversed the dominance relation despite its
docstring specifying minimization of both dimensions. Before the fix, the
hand-computed input `[[1, 1], [2, 2]]` returned `[False, True]`: it discarded the
strictly better point. The dedicated test failed on that exact mismatch before
the implementation was changed.

After the parent authorized this additional correctness fix within `plots.py`,
the comparison was reversed to discard points greater than or equal to the
current point in both dimensions, with at least one strict inequality. Equal
duplicates remain on the frontier. Regression cases cover reversed input order,
tradeoffs, equal coordinates, and every nonempty subset of the 3-by-3 integer
grid, checked against the direct mathematical definition of nondominance.

The head-to-head docstring also had the direction of a point below the diagonal
reversed: its y-coordinate belongs to algorithm B. The description now agrees
with the existing correct plotted win counts.

## Validation

The initial identity suite passed **40 tests**. The subsequent tiny Pareto test
was intentionally run against the old implementation and failed with actual
`[False, True]` versus expected `[True, False]`, confirming the independent bug.

Final command:

```text
.venv/bin/python -m pytest -q tests/test_codex_plot_identity.py tests/test_codex_analysis_identity.py
```

Final result: **74 passed** (45 plot regressions and 29 statistical identity
regressions), one existing `dwave-networkx` deprecation warning, in 17.55 seconds.
`git diff --check` passed. Tests inspect plotted values, point/column counts,
intersections, within-problem variation, and displayed labels rather than only
checking that a figure object exists. The inherited
`tests/test_ember_qc_analysis.py` fixture mismatch remains as documented in
experiment 004; these regressions use the actual current run schema.

## Limits

The scientific provenance limits from experiment 004 remain: custom graphs with
the same name and sizes cannot be distinguished without additional metadata;
target names cannot prove edge-set equality; and separate batches are kept
separate instead of assuming their configurations are equivalent. These plots
do not establish statistical independence of repeated graph configurations.

Numeric size/density plots can legitimately contain overlapping coordinates for
distinct problems. Per-problem calculations remain separate. Broad category and
trial-distribution plots intentionally summarize multiple problems; their
aggregation is not a claim that those graphs are the same instance.

Ambiguous name-based deep dives now require their caller to filter the DataFrame;
the public signature remains unchanged. Automatic callers that supplied an
ambiguous name may therefore need to handle that explicit error.
