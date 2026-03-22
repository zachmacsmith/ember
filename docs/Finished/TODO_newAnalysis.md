# QEAnalysis — Implementation Specification: Graph-Indexed Plots and Output Structure

---

## Output Directory Structure

The current flat `analysis/<batch-name>/` structure should be replaced with a
subdirectory layout organised by plot type. Every call to `generate_report()`
produces the following layout:

    analysis/<batch-name>/
    ├── summary/
    │   ├── overall_summary.csv
    │   ├── overall_summary.tex
    │   ├── summary_by_category.csv
    │   ├── summary_by_category.tex
    │   ├── rank_table.csv
    │   ├── rank_table.tex
    │   └── pairwise_comparison.csv       # shared-graph head-to-head, all pairs
    │
    ├── figures/
    │   ├── distributions/                # per-metric distribution shapes
    │   │   ├── chain_length_kde.png
    │   │   ├── chain_length_violin.png
    │   │   ├── embedding_time_violin.png
    │   │   └── chain_length_by_category.png
    │   │
    │   ├── graph_indexed/                # new: per-graph dot/strip plots
    │   │   ├── by_graph_id/
    │   │   │   ├── chain_length.png
    │   │   │   ├── embedding_time.png
    │   │   │   └── success.png
    │   │   ├── by_n_nodes/
    │   │   │   ├── chain_length.png
    │   │   │   ├── embedding_time.png
    │   │   │   └── success.png
    │   │   └── by_density/
    │   │       ├── chain_length.png
    │   │       ├── embedding_time.png
    │   │       └── success.png
    │   │
    │   ├── scaling/                      # metric vs graph size/density
    │   │   ├── chain_length_vs_nodes.png
    │   │   ├── time_vs_nodes.png
    │   │   └── density_hardness.png
    │   │
    │   ├── pairwise/                     # head-to-head algorithm comparisons
    │   │   ├── win_rate_matrix.png
    │   │   └── scatter_{A}_vs_{B}.png    # one per algorithm pair
    │   │
    │   ├── success/                      # success rate visualisations
    │   │   ├── success_rate_heatmap.png
    │   │   ├── success_rate_by_nodes.png
    │   │   └── success_rate_by_density.png
    │   │
    │   └── topology/
    │       └── topology_comparison.png
    │
    ├── statistics/
    │   ├── significance_tests.csv
    │   ├── significance_tests.tex
    │   ├── friedman_test.txt
    │   ├── correlation_matrix.csv
    │   └── win_rate_matrix.csv
    │
    └── report.md

All subdirectories are created at the start of `generate_report()` before any
plots are generated. Saving to a subdirectory is determined by the plot function
— each function knows its own subdirectory and receives `output_dir` pointing to
the batch analysis root, not a specific subfolder.

---

## New Plot Type: Graph-Indexed Dot Plots

### Overview

These plots show per-trial or per-algorithm metric values with one position on
the x-axis per graph instance. They sit between aggregate summary tables (which
lose distribution information) and full distribution plots (which lose graph
identity). They answer the question: "which specific graphs are easy or hard, and
does that pattern differ across algorithms?"

All three x-axis variants share the same y-axis options and the same visual
language. They are saved into `figures/graph_indexed/{by_graph_id,by_n_nodes,
by_density}/` respectively.

---

### X-Axis Variants

**Variant 1 — `by_graph_id` (categorical)**

X-axis is categorical, one position per unique graph ID. Positions are ordered by
`graph_id` lexicographically, which is stable and deterministic across any set of
algorithms since it depends only on the graph suite.

Graph type boundaries are marked with vertical dividers and section labels
(e.g. "bipartite", "complete", "random") centred over their respective groups.
Individual graph ID tick labels are suppressed — the section labels do all the
interpretive work. This is the canonical cross-run comparison view: the x-axis
never changes as long as the graph suite is unchanged.

**Variant 2 — `by_n_nodes` (numeric)**

X-axis is numeric, showing `n_nodes`. Each dot's horizontal position is its node
count. Graph IDs serve only as a tiebreaker for overplotting when two graphs have
identical node counts; this tiebreaker must be deterministic (sort by graph_id
within ties). X-axis label is "Number of nodes." No section labels. The numeric
axis is the sole interpretive layer.

**Variant 3 — `by_density` (numeric)**

X-axis is numeric, showing `density`. Same logic as `by_n_nodes` but x encodes
density. Tiebreaker is `(n_nodes, graph_id)` for determinism. X-axis label is
"Graph density."

For variants 2 and 3, dots at identical x values should be separated with a
small deterministic horizontal jitter — enough to prevent exact overlap, not
enough to misrepresent the x value. The jitter must be seeded from `graph_id` so
it is identical across runs and algorithms.

---

### Metric Variants

Three metric variants are produced for each x-axis variant, giving nine plots
total in `figures/graph_indexed/`.

**Chain length dot plot**

Y-axis: `avg_chain_length`. One dot per trial per algorithm, coloured by
algorithm. Shared-graph filter applied per algorithm: a dot for algorithm A on
graph G is only plotted if algorithm A successfully embedded G. Algorithms are
not penalised for attempting harder graphs — the plot shows what each algorithm
actually achieved, not what it failed to achieve.

Overlay a larger marker (e.g. diamond or horizontal bar) for the per-algorithm
mean across trials for each graph, on top of the individual trial dots. The
individual dots should be small and semi-transparent; the mean marker should be
opaque and clearly distinguishable from trial dots.

**Embedding time dot plot**

Y-axis: `wall_time`, log scale. Same dot-per-trial structure as chain length.
Log scale is essential — times will span orders of magnitude across graph sizes.
Do not apply shared-graph filter here: timeout runs should appear at the timeout
ceiling value with a distinct marker shape (e.g. triangle pointing up) to show
they hit the limit rather than completing. This makes it immediately visible
which graphs are causing timeouts.

**Success heatmap (not a dot plot)**

For the success metric, a dot plot does not work well because success is binary.
Replace with a grid heatmap: graphs on x-axis (same ordering as the other
variants), algorithms on y-axis, cell colour encodes success rate across trials
for that (algorithm, graph) pair. Use a red-to-green colormap. Annotate cells
with the raw fraction (e.g. "2/3") when the number of trials is small enough
to fit. This is likely the most informative single figure in the analysis — it
immediately shows which algorithm fails on which specific graphs.

---

### Visual Design Requirements

**Consistent algorithm-to-colour mapping:** The same algorithm must have the same
colour in every figure in the report. Compute the mapping once at report
generation time from the full set of algorithms in the batch and pass it into
every plot function. Do not recompute per plot.

**Colourblind-safe palette:** Use a palette that is distinguishable under
deuteranopia and protanopia. Seaborn's `colorblind` palette or a manually
specified set of safe colours. Distinguish algorithms by both colour and marker
shape so the plots are readable in greyscale.

**Faceting for readability:** If the graph suite contains more than approximately
25 graphs, facet the `by_graph_id` variant by graph category — one panel per
category, shared y-axis, shared legend. Each panel shows only the graphs in that
category with section labels suppressed (the panel title serves that role). For
`by_n_nodes` and `by_density`, faceting is not needed because the continuous
x-axis naturally separates graphs.

**Legend placement:** Outside the plot area on the right side for all graph-
indexed plots. The graph count on the x-axis makes interior legend placement
unreliable.

**Figure sizing:** Graph-indexed plots should default to wider aspect ratios than
standard plots — something like 14×5 inches for the `by_graph_id` variant with
a moderate graph suite, scaling with graph count. Make width a function of graph
count rather than a fixed value.

---

### Shared-Graph Filter Implementation

The shared-graph filter is a query concern, not a plotting concern. Implement
it as a standalone function in `qeanalysis/filters.py` (or equivalent) that
takes a DataFrame and a list of algorithms and returns only the rows where all
specified algorithms succeeded on that graph. The plotting function calls this
filter before computing any aggregates or rendering any dots. This ensures the
filter logic is testable independently and reused consistently across plots.

For the chain length dot plot, apply the filter per algorithm pair if exactly
two algorithms are selected, or apply the all-algorithm intersection if more
than two are selected. Document which filter was applied in the figure subtitle
so a reader knows the comparison is fair.

---

### Integration with `generate_report()`

`generate_report()` should call all three x-axis variants for all three metric
variants automatically, producing all nine plots. Each call is independent —
a failure in one plot should not prevent the others from generating. Wrap each
plot call in a try/except that logs the failure and continues.

The report.md file should reference all nine plots with a brief description of
what each x-axis variant shows and when to use it. A reader who only looks at
report.md should understand which plot to open for which analytical question.

---

## Updates to Existing Analyses

**`plot_chain_distribution` (existing KDE plot):** No changes to the function
itself. Move output to `figures/distributions/chain_length_kde.png`. The existing
plot answers a different question from the new graph-indexed plots — keep both.

**`plot_head_to_head` (existing pairwise scatter):** Move output to
`figures/pairwise/scatter_{A}_vs_{B}.png`. No changes to logic. Generate one
file per algorithm pair automatically in `generate_report()`.

**`plot_density_hardness` (existing):** Move output to
`figures/scaling/density_hardness.png`. No logic changes. This plot is
complementary to the new `by_density` graph-indexed plot — the existing one
aggregates by density bin and shows trend lines, the new one shows individual
graph instances.

**`summary_by_category` (existing):** Add `max_chain_length` and
`chain_length_std` as additional metric options alongside `avg_chain_length`.
These should be available wherever `avg_chain_length` is currently the default
metric parameter.

---

## Secondary Metrics

**`max_chain_length`:** Should be stored in the `runs` table during
`compile_batch()`, computed from the embedding dict alongside `avg_chain_length`.
Analysis code reads it directly from SQLite — it must not deserialise embeddings
to compute it. Include it in `overall_summary()` output as `max_chain_mean` and
in `summary_by_category()` as an available metric.

**`chain_length_std`:** Same — store during compilation, read in analysis.
Include in `overall_summary()` as `chain_std_mean` (mean of per-run std across
successful trials). Also expose as an available metric in `summary_by_category()`.

**`max_to_avg_chain_ratio`:** Already a derived column computed at load time.
No changes needed. Include it in `overall_summary()` if not already present.

---

## What to Test After Implementation

**Output structure:**
- After `generate_report()`, all nine subdirectories exist.
- Each expected file is present in the correct subdirectory.
- No plot files appear in the root `analysis/<batch-name>/` directory.

**Graph-indexed plots:**
- X-axis ordering is identical across two runs with the same graph suite but
  different algorithm subsets (determinism test).
- Section labels appear in the correct positions for `by_graph_id` variant.
- Individual graph ID tick labels are suppressed in `by_graph_id`.
- Numeric x-axis shows actual `n_nodes` / `density` values in respective variants.
- Jitter for `by_n_nodes` and `by_density` is identical across runs (seeded).
- Timeout runs appear at the ceiling with a distinct marker in the time plot.
- Shared-graph filter reduces the plotted dot count when algorithms have
  different success sets (verify with a mock dataset where one algorithm
  fails on a known subset of graphs).

**Colour consistency:**
- The same algorithm has the same colour in every figure produced by a single
  `generate_report()` call.

**Failure isolation:**
- Deliberately breaking one plot function does not prevent the remaining plots
  from generating.

**Metric availability:**
- `max_chain_length` and `chain_length_std` are readable from SQLite without
  deserialising embeddings.
- Both appear in `overall_summary()` and are accepted as metric parameters in
  `summary_by_category()`.