# Graph Presets

EMBER provides named presets for common graph selections. A preset is a
shorthand for a list of graph IDs — use it anywhere a graph selection is
accepted: `--graphs`, `ember graphs install`, or `load_test_graphs()` in
Python.

```bash
ember run --graphs benchmark ...       # use a preset in an experiment
ember graphs install sensitivity       # install graphs from a preset
ember graphs presets                   # list all presets with resolved counts
```

Presets are defined in `ember_qc/graphs/presets.csv` and can be extended
by editing that file or by composing presets with the selection syntax:

```bash
ember run --graphs "benchmark, 5550-5560"   # preset + extra IDs
```

---

## Preset overview

| Preset | Count | Target use case |
|---|---|---|
| `quick` | 12 | Smoke tests, CI, algorithm development |
| `installed` | 37 | Offline use — always available, no download |
| `default` | 36 | One small representative per graph type |
| `diverse` | 31 | Hand-picked variety across types and sizes |
| `benchmark` | 82 | Algorithm comparison with broad type coverage |
| `sensitivity` | 273 | Parameter-sensitivity analysis across sizes and densities |
| `small` | 617 | All graphs with n <= 10 |
| `structured` | 2,568 | All deterministic/algebraic graph types |
| `lattice` | 820 | Physics lattice types only |
| `physics` | 4,490 | All physics-motivated graphs |
| `hardware_native` | 42 | Hardware topology subgraphs |
| `named_special` | 12 | Classical named graphs |
| `all` | 31,083 | Complete library |

---

## Choosing a preset

### For algorithm development and CI

Use **`quick`** (12 graphs) or **`installed`** (37 graphs). These are
small, fast, always available offline, and cover enough graph types to
catch basic regressions.

```bash
ember run --algorithms my-algorithm --graphs quick --trials 1 --timeout 10
```

### For algorithm benchmarking

Use **`benchmark`** (82 graphs). Covers 33 of 36 families with 2–3
graphs each, spanning the full density range (0.006 to 1.0). Skews
toward small graphs (n <= 20) which makes runs fast — suitable for
per-commit benchmarking or multi-algorithm sweeps.

```bash
ember run --algorithms minorminer,pssa,clique --graphs benchmark --trials 3
```

### For parameter-sensitivity experiments

Use **`sensitivity`** (273 graphs). A strict superset of `benchmark`
that adds 191 mid-to-large graphs (n = 50–600) sampled at low and high
density per family across all 36 graph types. This is designed to
reveal quality/speed tradeoffs between algorithm variants (e.g.
`pssa-fast` vs `pssa-thorough`, `minorminer-fast` vs
`minorminer-aggressive`) that are invisible on small graphs where every
variant succeeds instantly.

```bash
ember run \
  --algorithms pssa-fast,pssa,pssa-weighted,pssa-thorough \
  --graphs sensitivity \
  --topologies chimera_16x16x4,pegasus_16,zephyr_12 \
  --trials 5
```

**Size distribution:**

| Range | Count |
|---|---|
| tiny (n <= 20) | 64 |
| small (21–50) | 16 |
| medium (51–100) | 70 |
| large (101–300) | 63 |
| xlarge (301–600) | 59 |

**Density distribution:**

| Range | Count |
|---|---|
| ultra-sparse (< 0.05) | 116 |
| sparse (0.05–0.2) | 56 |
| medium (0.2–0.5) | 46 |
| dense (0.5–0.8) | 28 |
| very dense (> 0.8) | 25 |

### For physics-focused research

Use **`physics`** (4,490 graphs) which includes all physics lattice
types (triangular, kagome, honeycomb, king graph, frustrated square,
Shastry-Sutherland, cubic, BCC) plus spin glass, weak-strong cluster,
and planted solution instances. Or use **`lattice`** (820 graphs) for
just the lattice types.

### For exhaustive evaluation

Use **`all`** (31,083 graphs). This is the complete library and will
take a long time to run, but is appropriate for final paper results.
Consider combining with `--workers` for parallelism:

```bash
ember run --algorithms minorminer,pssa --graphs all --workers 16
```

---

## Preset relationships

```
quick (12)  ⊂  default (36)
                    ↓
              diverse (31)     ← hand-picked, partially overlaps default
                    ↓
            benchmark (82)     ← curated for benchmarking
                    ↓
          sensitivity (273)    ← benchmark + mid/large density-spread supplement
                    ↓
               all (31,083)    ← complete library

lattice (820)  ⊂  physics (4,490)  ⊂  all
structured (2,568)  ⊂  all
hardware_native (42)  ⊂  all
named_special (12)  ⊂  all
small (617)  ⊂  all
```

---

## Suggested experiment configurations

### Run 1 — Core algorithm comparison (full library)

```yaml
name: core_comparison
algorithms: [minorminer, pssa, clique]
graphs: all
trials: 3
timeout: 60
seed: 42
```

### Run 2 — Parameter sensitivity (sensitivity preset)

```yaml
name: param_sensitivity
algorithms:
  - pssa-fast
  - pssa
  - pssa-weighted
  - pssa-thorough
  - minorminer-fast
  - minorminer
  - minorminer-aggressive
graphs: sensitivity
topologies: [chimera_16x16x4, pegasus_16, zephyr_12]
trials: 5
timeout: 60
seed: 42
```

### Run 3 — Chimera-only with all algorithms

```yaml
name: chimera_all_algos
algorithms:
  - minorminer
  - pssa
  - oct-triad
  - oct-hybrid-oct
  - atom
  - clique
graphs: all
topologies:
  - chimera_4x4x4
  - chimera_8x8x4
  - chimera_12x12x4
  - chimera_16x16x4
trials: 3
timeout: 60
seed: 42
```
