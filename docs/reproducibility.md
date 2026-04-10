# Reproducibility

EMBER is designed so that any experiment can be reproduced exactly from a single file. This document explains the mechanisms that make this possible.

---

## The resolved YAML

Every `ember run` call writes two files alongside the batch output:

- `experiment.yaml` — a verbatim copy of the input file
- `experiment_resolved.yaml` — every parameter as actually used, including defaults that were filled in from config or package defaults

To reproduce a run exactly on any machine:

```bash
ember run results/my_batch/experiment_resolved.yaml
```

The resolved YAML captures:
- All algorithm names
- Exact graph selection string
- Topology names
- `n_trials`, `warmup_trials`, `timeout`
- `seed`
- `n_workers`
- `fault_rate`, `fault_seed`
- Any `note`
- `output_dir`

---

## Seeding

EMBER derives per-trial seeds deterministically from the master `seed` using SHA-256:

```
trial_seed = SHA-256("{seed}:{algorithm}:{graph_id}:{topology_name}:{trial}")[:4]
```

Properties of this scheme:

- **Order-independent** — the seed for trial 5 is the same whether trials 1–4 ran or not. This is essential for resume: a resumed run produces identical results to an uninterrupted run.
- **Cross-key independent** — changing the algorithm name does not affect seeds for other algorithms. Changing the problem name does not affect seeds for other problems.
- **Stable across Python versions** — SHA-256 is not affected by Python's hash randomization (`PYTHONHASHSEED`).
- **Warmup isolation** — warmup trials use negative trial indices to avoid collisions with measured trials.

The default seed is `42`. All results are reproducible out-of-the-box without specifying a seed.

---

## Global RNG reseeding

Before every `embed()` call, EMBER seeds both Python's global `random` module and `numpy.random` with the derived trial seed. This means algorithms that use `random` or `numpy.random` without an explicit seed parameter are still reproducible, as long as they do not call any other global RNG state between trials.

---

## Checkpoint and resume

If a benchmark is interrupted (Ctrl+C, job timeout, crash), it can be resumed:

```bash
ember resume                    # interactive list
ember resume <batch_id>         # specific run
```

**Clean cancellation (Ctrl+C):** EMBER writes a `checkpoint.json` listing every unfinished task with its exact seed. Resume reads this file and executes only the unfinished tasks.

**Crash:** No checkpoint is written. Resume scans the `workers/*.jsonl` files to determine which tasks completed (identified by their seeds) and re-executes the rest.

In both cases, the resumed run produces identical results to an uninterrupted run. The `compile_batch()` step deduplicates by `(algorithm, graph_id, graph_name, topology_name, trial_seed)` before writing to SQLite, so partially-written tasks cannot produce duplicate rows.

---

## Environment provenance

Every batch records the full environment in `config.json`:

```json
{
  "ember_version": "0.5.0",
  "python_version": "3.12.2",
  "platform": "macOS-14.2.1-arm64",
  "processor": "Apple M3",
  "dependencies": {
    "minorminer": "0.2.21",
    "networkx": "3.2.1",
    ...
  },
  "algorithms": {
    "minorminer": {"version": "0.2.21"},
    "clique": {"version": "0.2.21"}
  }
}
```

This records what was installed at run time, independent of what is installed now. When comparing results across machines, check that `ember_version` and algorithm versions match.

---

## Graph integrity

Graph files are verified against SHA-256 hashes in `manifest.json` at load time. If a graph file is modified or corrupted, the benchmark fails with a clear error before any trials run.

---

## Batch directory as a self-contained unit

A completed batch directory is self-contained:

```
results/my_batch/
├── config.json              # parameters + provenance
├── experiment_resolved.yaml # exact config to reproduce this run
├── results.db               # all trial data
├── summary.csv              # grouped statistics
└── README.md                # human-readable summary
```

To reproduce: copy `experiment_resolved.yaml` to another machine with the same `ember-qc` version, run it. The results will be identical.

---

## What is not guaranteed

- **Parallel execution order** — with `workers > 1`, trials execute concurrently. The final results are identical regardless of execution order, but wall times and per-worker JSONL files differ.
- **C++ binary algorithms** — ATOM and OCT reproducibility depends on their internal seeding. EMBER passes the derived seed but cannot guarantee the binary uses it.
- **`charme`** — RL-based; reproducibility depends on PyTorch and GPU state.
- **Cross-version reproducibility** — changing `ember-qc`, `minorminer`, or `networkx` versions may change results even with the same seed.
