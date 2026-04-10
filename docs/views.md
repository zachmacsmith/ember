# Analysis Views

Views let you combine data from multiple batches and apply per-source filters
in a single analysis run.  Instead of analysing one batch at a time, a view
YAML file describes exactly which data to include and how to filter it.

## Quick start

```bash
# Create a view file
cat > my_comparison.yaml <<EOF
name: Algorithm comparison across runs
sources:
  - batch: batch_2026-04-10_19-18-24
    filters:
      algorithm: [minorminer, pssa]
  - batch: batch_2026-04-09_12-00-00
    filters:
      algorithm: [OCT, ATOM]
EOF

# Run analysis with the view
ember-a report --view my_comparison.yaml
ember-a plots  --view my_comparison.yaml topology
ember-a tables --view my_comparison.yaml
ember-a stats  --view my_comparison.yaml
```

## View YAML format

```yaml
# Required
name: Human-readable description of this view
sources:
  - batch: <batch_specifier>    # directory name, path, or prefix
    filters:                    # optional — omit to include all data
      <column>: <value_spec>

# Optional
output_name: my_slug            # defaults to slugified 'name'
```

### Batch specifiers

Each source's `batch` field accepts:
- **Full path**: `/absolute/path/to/batch_2026-04-10_19-18-24`
- **Directory name**: `batch_2026-04-10_19-18-24` (looked up in `input_dir`)
- **Name prefix**: `batch_2026-04-10` (must be unambiguous)

### Filter keys

Filters are key-value pairs that restrict which rows are included from
a source batch.

**SQL-level filters** (pushed to the database query for efficiency):

| Key | Type | Example |
|-----|------|---------|
| `algorithm` | string or list | `minorminer`, `[OCT, ATOM]` |
| `topology_name` | string or list | `chimera_16x16x4`, `[pegasus_16, zephyr_12]` |
| `graph_name` | string or list | `er_n10_p0.5_s0` |
| `graph_id` | int, list, or range | `42`, `[1, 2, 3]`, `1-500` |
| `status` | string or list | `SUCCESS`, `[SUCCESS, TIMEOUT]` |
| `success` | int | `1` (successful only) |

**Post-load filters** (applied after derived columns are computed):

| Key | Type | Example |
|-----|------|---------|
| `category` | string or list | `random_er`, `[grid, honeycomb]` |
| `base_topology` | string or list | `chimera_16x16x4` |
| `fault_rate` | float or list | `0.0`, `[0.0, 0.05]` |

### Exclusions

Prefix any value with `!` to exclude it:

```yaml
filters:
  algorithm: [minorminer, "!minorminer-fast"]   # minorminer but not fast variant
  category: ["!complete", "!petersen"]           # exclude complete and petersen
```

### ID ranges

`graph_id` supports range syntax:

```yaml
filters:
  graph_id: 1-500     # include graph IDs 1 through 500
```

## Output location

View results are written to `analysis/view_<output_name>/` to keep them
separate from single-batch analyses.  The `output_name` defaults to a
slugified version of `name` (lowercase, non-alphanumeric replaced with
underscores).

Override with `--output-dir`:

```bash
ember-a report --view my_view.yaml --output-dir custom/path
```

## Provenance

The combined DataFrame includes a `source_batch` column identifying which
batch each row originated from.  The merged config includes a `_view` key
with metadata:

```python
config['_view'] = {
    'name': 'Algorithm comparison across runs',
    'output_name': 'algorithm_comparison_across_runs',
    'yaml_path': '/path/to/my_comparison.yaml',
    'n_sources': 2,
    'source_batches': ['batch_2026-04-10_19-18-24', 'batch_2026-04-09_12-00-00'],
}
```

## Programmatic usage

```python
from ember_qc_analysis.views import load_view
from ember_qc_analysis import BenchmarkAnalysis

df, config = load_view("my_comparison.yaml")
view_name = config['_view']['output_name']

an = BenchmarkAnalysis(df=df, config=config, view_name=view_name)
an.generate_report()
```

## Examples

### Fault-rate comparison

```yaml
name: Fault-rate robustness on chimera
sources:
  - batch: batch_2026-04-10_fault_sweep
    filters:
      algorithm: [minorminer, pssa]
      base_topology: chimera_16x16x4
```

### Cherry-pick algorithms from different runs

```yaml
name: Best-of-each algorithm
sources:
  - batch: batch_2026-04-09_pssa_run
    filters:
      algorithm: pssa-thorough
  - batch: batch_2026-04-09_mm_run
    filters:
      algorithm: minorminer-aggressive
  - batch: batch_2026-04-08_oct_run
    filters:
      algorithm: OCT
      category: ["!complete"]    # OCT struggles with complete graphs
```

### Subset by graph type and size

```yaml
name: Sparse lattice comparison
sources:
  - batch: batch_2026-04-10_full_run
    filters:
      category: [grid, honeycomb, triangular_lattice, kagome]
      graph_id: 1-200
```
