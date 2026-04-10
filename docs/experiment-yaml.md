# Experiment YAML Reference

Every `ember run` invocation is driven by a YAML file. This document is the complete reference for every supported key.

---

## Minimal example

```yaml
name: my_experiment
algorithms:
  - minorminer
  - clique
graphs: "1-60"
topologies:
  - pegasus_16
trials: 5
```

Only `algorithms`, `graphs`, and `topologies` are required if you are happy with the other defaults.

---

## All keys

### `name`

**Type:** string
**Default:** `"experiment"`
**Description:** Human-readable label for this experiment. Used in the output directory name and the `README.md` written with results.

```yaml
name: chimera_comparison_2026
```

---

### `algorithms`

**Type:** list of strings, or comma-separated string
**Default:** all registered and available algorithms
**Description:** Which algorithms to benchmark. Each entry is a registered algorithm name.

```yaml
algorithms:
  - minorminer
  - minorminer-fast
  - clique
  - pssa
```

Or as a single string:

```yaml
algorithms: "minorminer, clique"
```

Run `ember algos list` to see all registered names. Run `ember algos list --available` to filter to those available in your current environment.

---

### `graphs`

**Type:** string
**Default:** `"*"` (all graphs)
**Description:** Which graphs to benchmark. Accepts a selection expression or a preset name. See [graph-library.md](graph-library.md) for the full syntax.

```yaml
graphs: "1-60"          # IDs 1 through 60
graphs: "quick"         # named preset
graphs: "1-100, !50"    # IDs 1–100 excluding 50
graphs: "*"             # all 167 bundled graphs
```

---

### `topologies`

**Type:** list of strings, or comma-separated string
**Default:** value of `ember config get default_topology`
**Description:** Hardware topologies to embed onto. Each entry is a registered topology name. The benchmark runs every (algorithm, graph, topology, trial) combination.

```yaml
topologies:
  - pegasus_16
  - chimera_16x16x4
```

Run `ember topologies list` to see all registered names.

---

### `trials`

**Type:** integer
**Default:** `5`
**Description:** Number of independent measured trials per (algorithm, graph, topology) combination. More trials give tighter confidence intervals.

```yaml
trials: 10
```

---

### `warmup`

**Type:** integer
**Default:** `1`
**Description:** Number of warmup trials run before measurement begins. Warmup trials are not saved to results. Used to amortise JIT compilation and library loading costs.

```yaml
warmup: 0
```

---

### `timeout`

**Type:** float (seconds)
**Default:** `60.0`
**Description:** Maximum wall-clock seconds allowed per trial. If an algorithm exceeds this, the trial is marked `TIMEOUT`.

```yaml
timeout: 120.0
```

---

### `seed`

**Type:** integer
**Default:** `42`
**Description:** Master random seed. All per-trial seeds are derived deterministically from this value using SHA-256, so results are fully reproducible from the seed alone.

```yaml
seed: 12345
```

---

### `workers`

**Type:** integer
**Default:** `1`
**Description:** Number of parallel worker processes. Set to the number of CPU cores you want to dedicate to the benchmark. Workers execute trials concurrently and write to separate JSONL files.

```yaml
workers: 8
```

Setting `workers: 1` runs sequentially (simplest, easiest to debug). Parallel execution does not change seeds or results — only wall time.

---

### `output_dir`

**Type:** string (path)
**Default:** value of `ember config get output_dir`, or `./results/` if not set
**Description:** Directory where the batch output is written. The batch subdirectory is created inside this path.

```yaml
output_dir: /home/user/benchmark_results
```

---

### `note`

**Type:** string
**Default:** none
**Description:** Free-text annotation stored in `config.json` alongside the results. Useful for distinguishing runs.

```yaml
note: "after fixing pssa seed handling"
```

---

### `fault_rate`

**Type:** float, list of floats, or mapping (0.0–1.0)
**Default:** `0.0` (no faults)
**Description:** Fraction of hardware nodes to remove from each topology before embedding. Simulates faulty qubits.

```yaml
fault_rate: 0.03    # 3% of qubits disabled
```

To sweep multiple fault rates in a single batch, pass a list. Each
(topology, rate) pair becomes a virtual topology named
`topology@fr=0.05` in the results:

```yaml
fault_rate: [0.0, 0.01, 0.05, 0.10, 0.20]
```

Or via CLI: `--fault-rate 0.0,0.01,0.05,0.10,0.20`

To set different rates per topology, use a mapping:

```yaml
fault_rate:
  pegasus_16: 0.01
  chimera_16x16x4: 0.05
```

---

### `fault_seed`

**Type:** integer
**Default:** same as `seed`
**Description:** Seed for which nodes to remove when using `fault_rate`. Independent of the trial seed. Using a fixed `fault_seed` with a fixed `fault_rate` produces the same faulty topology across runs.

```yaml
fault_seed: 99
```

---

## Priority order

When the same parameter is set in multiple places, the order of precedence from highest to lowest is:

1. CLI flag (e.g. `--trials 10`)
2. YAML file
3. Environment variable (e.g. `EMBER_SEED=42`)
4. Stored config (`ember config set ...`)
5. Package default

---

## The resolved YAML

Every run writes `<name>_resolved.yaml` alongside the results. This file records every parameter as actually used — including defaults that were filled in and config values that were applied. To reproduce a run exactly:

```bash
ember run experiment_resolved.yaml
```

---

## Full example

```yaml
name: pegasus_comparison
algorithms:
  - minorminer
  - minorminer-fast
  - minorminer-aggressive
  - clique
graphs: "1-60"
topologies:
  - pegasus_16
trials: 10
warmup: 2
timeout: 90.0
seed: 42
workers: 4
output_dir: ~/results
note: "baseline comparison, structured graphs only"
fault_rate: 0.0
```
