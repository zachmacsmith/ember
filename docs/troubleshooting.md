# Troubleshooting

Common problems and how to resolve them.

---

## Results in the wrong place

**Symptom:** `ember run` completes but you cannot find the output directory.

**Cause:** `output_dir` is not set, so results are written to `./results/` relative to the directory you ran `ember run` from.

**Fix:**

```bash
ember config show          # check what output_dir is set to
ember config set output_dir ~/results   # set a permanent location
```

Or override per-run:

```bash
ember run experiment.yaml --output-dir /tmp/my_results
```

---

## All trials are TIMEOUT

**Symptom:** Every trial in `runs.csv` has `status=TIMEOUT`.

**Causes:**

1. `timeout` is too short for the problem size and algorithm.
2. The algorithm is slow on the selected topology.

**Fix:**

```bash
# Increase timeout in your YAML
timeout: 300.0

# Or set a higher default
ember config set default_timeout 300.0
```

To find the actual median runtime before it times out, try a small subset with a generous timeout:

```yaml
graphs: "1-7"       # just the complete graphs
timeout: 600.0
trials: 1
```

Then look at `wall_time` in the results to calibrate.

---

## All trials are CRASH

**Symptom:** Every trial has `status=CRASH` and the `error` column shows the same exception.

**Common causes:**

- **Missing binary** — `atom` or `oct-*` algorithms crash if the binary is not installed. Run `ember algos list` to check. Install with `ember install-binary atom` or `ember install-binary oct`.
- **Import error** — a custom algorithm file has a syntax error or a missing import. Run `ember algos list` to see if the algorithm appears as available.
- **Incompatible topology** — `atom` and `oct-*` require Chimera. Check `ember algos list` to see topology restrictions.

**Diagnosis:**

```bash
ember run experiment.yaml --workers 1    # run single-threaded so stack traces are visible
```

The full exception is stored in `runs.error` in the database:

```python
import sqlite3, pandas as pd
con = sqlite3.connect("results/my_batch/results.db")
df = pd.read_sql("SELECT algorithm, error FROM runs WHERE status='CRASH' LIMIT 5", con)
print(df)
```

---

## High TIMEOUT rate for one algorithm

**Symptom:** One algorithm times out on most problems; others succeed.

**Interpretation:** The algorithm is slower than others for this problem type and topology. This is informative — it means the timeout is an active constraint on that algorithm's results.

**Options:**

- Increase `timeout` to see whether the algorithm eventually succeeds.
- Accept the timeout rate as part of the benchmark (it will appear in success rate plots).
- Use `workers: 1` and watch the terminal for progress output.

---

## Algorithm produces `is_valid=0`

**Symptom:** Trials succeed (`success=1`) but `is_valid=0`.

**Meaning:** The algorithm returned an embedding that failed one or more structural validity checks:
- Chain disconnection: a chain of physical qubits is not connected in the target graph.
- Edge violation: an edge between two source nodes is not represented by a coupler between their chains.
- Chain overlap: two chains share the same physical qubit.

**Cause:** This is typically a bug in the algorithm. The `pssa` algorithm family can produce disconnected chains on some problem types.

**What to do:** Exclude invalid runs from analysis by filtering `is_valid = 1`:

```python
df_valid = df[(df["success"] == 1) & (df["is_valid"] == 1)]
```

---

## `ember resume` shows no incomplete runs

**Symptom:** After an interrupted run, `ember resume` reports nothing to resume.

**Cause:** EMBER writes incomplete runs to `runs_unfinished/` (a sibling directory of `results/`). If `output_dir` was changed between runs, `ember resume` may be looking in the wrong place.

**Fix:**

```bash
ember config show           # check output_dir
ls ~/results/runs_unfinished/   # look in the configured directory
ember resume --input-dir ~/results
```

---

## Workers cause non-reproducible results

**Symptom:** Running the same experiment twice with the same seed produces different `avg_chain_length` values when `workers > 1`.

**Cause:** This is expected. With `workers > 1`, trials execute concurrently and share the host's global random number state. Individual trial seeds are still deterministic (derived from the master seed), but the interaction of concurrent threads with some algorithms' global RNG use can introduce variation.

**Fix for reproducibility:** Set `workers: 1` to enforce sequential execution. Results are identical across runs with the same seed.

See [reproducibility.md](reproducibility.md) for details.

---

## `ember config show` shows unexpected values

**Symptom:** A setting appears to be `env` or `config` source when you expected default.

**Cause:** An environment variable (`EMBER_OUTPUT_DIR`, `EMBER_WORKERS`, etc.) is set in your shell, overriding the stored config.

**Fix:**

```bash
env | grep EMBER          # list all EMBER environment variables
unset EMBER_WORKERS       # remove a specific override
```

Or add `unset EMBER_*` to your shell profile if the variables are set there.

---

## Results database is locked

**Symptom:** An error like `database is locked` when loading `results.db`.

**Cause:** Another process (e.g. a running benchmark or a Jupyter kernel) has the database open.

**Fix:** Close all other processes accessing the database, or copy it to a new location before opening:

```bash
cp results/my_batch/results.db /tmp/my_batch.db
```

---

## Analysis report is empty or partially generated

**Symptom:** `ember-analysis report` exits without error but some plots are missing.

**Common causes:**

1. **Only one algorithm** — pairwise plots (`win_rate_heatmap.png`, `head_to_head_*.png`) require at least two algorithms.
2. **Only one topology** — topology comparison plots are skipped when only one topology was benchmarked.
3. **All trials failed** — if `success_rate` is 0 for all algorithms, chain length distributions cannot be plotted.

Check `ember-analysis report --overwrite` and review the terminal output for per-plot warnings.

---

## Installation issues

**`ember` command not found after `pip install ember-qc`:**

The script is not on your PATH. Check:

```bash
pip show ember-qc | grep Location
```

Then add the `bin/` directory (or `Scripts/` on Windows) to your PATH, or run via:

```bash
python -m ember_qc.cli <command>
```

**`pip install ember-qc[analysis]` fails on dependency:**

`ember-qc-analysis` requires `scipy` and `matplotlib`. On some systems you may need to install them first:

```bash
pip install scipy matplotlib
pip install ember-qc[analysis]
```
