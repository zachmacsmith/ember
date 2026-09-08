# Experiment 004: preserve graph identity in statistical comparisons

Date: 2026-09-07. Branch: `codex`. This is a benchmark analysis repair; it does
not change or select embedding algorithms.

## Problem and source evidence

`statistics._per_problem_means` and `summary.rank_table` previously grouped
successful trials by `(algorithm, graph_name)` alone. Distinct manifest graphs
with the same display name, or the same graph evaluated on different hardware,
therefore became one observation. This changed graph means, ranks, sample counts,
and paired significance tests.

The existing schema supplies these usable fields:

- `benchmark.py` documents `graph_id` as a unique manifest integer ID, with `0`
  reserved for custom/non-manifest graphs.
- `compile.py` stores `graph_id`, `graph_name`, `topology_name`, `batch_id`, and
  `algorithm_version` in `runs`. `config_json` belongs to the `batches` table.
- `loader.py` exports those run identifiers; old records can have `graph_id=0`.
- `views.py` adds `source_batch` when combining results from source batches.

No graph-structure digest, target-structure digest, or per-row configuration hash
exists in that schema. This repair does not invent those fields or assert that
names or graph sizes prove structural identity.

## Implemented behavior

The common grouping helper now uses source identity, full `topology_name`, and
batch provenance. A positive manifest ID is the source identity, independent of
display-name spelling. For zero, missing, or malformed IDs, the fallback uses the
graph name and the existing `problem_nodes`/`problem_edges` fields when available.
The fallback emits a warning that indistinguishable records can still conflate.
Without either an ID or a name, grouping raises a clear error.

`batch_id` takes precedence; `source_batch` fills missing values. Missing target
or configuration provenance produces a warning. Unknown components remain in
separate strata from known components instead of being discarded by pandas.
Distinct batches remain separate because the analysis frame cannot establish
equivalence of their configurations. This is deliberately conservative:
algorithms run exclusively in separate batches do not automatically become paired
observations. A future explicit configuration-equivalence API would require
additional metadata and validation outside this repair.

Repeated successful trials within a stratum still contribute to its arithmetic
mean. Failed trials do not affect ACL means. Multiple `algorithm_version` values
within one algorithm/problem/batch cell raise an error instead of silently pooling
implementations. Different algorithms can have different versions.

`rank_table`, pairwise Wilcoxon tests, Friedman tests, and win rates share this
identity logic. The aggregate trial summaries (`overall_summary` and
`summary_by_category`) retain their documented aggregation behavior.

The repair also preserves an attempted-trial mask. Previously an algorithm with
no trial on a problem could be counted as having failed it, while an algorithm
whose trials all failed could disappear entirely. Win rates now compare problems
attempted by both algorithms. At least one must have a successful metric to enter
the existing win-rate denominator; both-failed problems remain excluded. An
all-failed algorithm remains visible, with missing quality means.

## Validation

Command:

```text
.venv/bin/python -m pytest -q tests/test_codex_analysis_identity.py
```

Result: **29 passed**, one existing `dwave-networkx` deprecation warning, in
16.57 seconds. The cases cover colliding names with distinct IDs, repeated trial
means, topology sizes and architectures, distinct full fault-topology labels,
batch provenance, absent trials versus failures, all-failed algorithms, legacy
and partially missing identity, version conflicts, rank counts, six paired
Wilcoxon observations, three complete Friedman blocks, empty input, and input
immutability. `git diff --check` also passed.

Before editing, the relevant existing suite was attempted with:

```text
.venv/bin/python -m pytest -q tests/test_ember_qc_analysis.py -k 'TestSummary or TestWinRate or TestSignificance' --maxfail=1
```

It failed in fixture setup before reaching the assigned functions:
`sample_df` uses the old `problem_name` field and directly calls
`loader._derive_columns`, which accesses `graph_name` (`KeyError: graph_name`).
That preexisting loader/fixture mismatch was reported to the parent agent and
left outside this task's assigned files. The new regressions use the current run
schema and explicitly test the helper's legacy fallback independently.

## Limitations and follow-up

IDs are trusted as the existing manifest identifiers, not validated against graph
structure in this analysis layer. Custom graphs with identical names and sizes
cannot be distinguished using current metadata alone; the warning makes that
limitation explicit. Full topology names retain available target distinctions,
but cannot prove that two underlying target edge sets are identical.

Several plotting functions contain their own name-based grouping operations;
they are outside the assigned `statistics.py`/`summary.py` scope and were reported
for follow-up. Statistical tables and plots should not be assumed to have
identical grouping semantics until those plotting paths are reviewed.

Repeated configurations of the same physical graph are separate analysis strata.
They must not be presented as independent graph samples without a stated
experimental design; this repair prevents accidental merging but is not a
hierarchical statistical model.
