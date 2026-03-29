# TODO — Algorithm Layer

Derived from a comparison of `Algorithm_Contract.md`, `docs/Algorithm_status.md`, and the
current codebase. Items are grouped by priority.

---

## High Priority

### 1. Add `'success': True` to all success return paths

`Algorithm_Contract.md` requires the `success` field on **every** return path. Every
algorithm in `qebench/registry.py` currently omits it on success:

```python
# Current — wrong
return {'embedding': embedding, 'time': elapsed}

# Required
return {'embedding': embedding, 'time': elapsed, 'success': True}
```

The runner infers success from non-empty embedding, which the contract explicitly
forbids relying on. Affects: `minorminer`, `minorminer-aggressive`, `minorminer-fast`,
`minorminer-chainlength`, `clique`, `atom`, all six OCT variants.

---

### 2. Wrap PSSA as a proper `EmbeddingAlgorithm`

`algorithms/pssa_dwave/` is a standalone benchmarking system (`core.py`, `benchmark.py`)
that has never been integrated with the `EmbeddingAlgorithm` contract. It cannot run
through the benchmark pipeline at all.

Required fixes before wrapping (from `Algorithm_status.md`):

1. Add `timeout` parameter to `embed()`
2. Return `{'embedding': {}, 'time': elapsed, 'success': False}` on failure — not `None`
3. Remove `print(f"PSSA error: {e}")` — use `logging.getLogger(__name__).debug(...)`
4. Handle `seed=kwargs.get('seed', None)` for reproducibility
5. Measure CPU time alongside wall-clock
6. Change registration-time `print("✓ PSSA algorithms registered...")` to `logging.info(...)`

---

### 3. Implement Layer 3 validation (consistency checks)

`qebench/validation.py` has a TODO comment noting Layer 3 is unimplemented. It must
run after Layers 1 and 2 on every result:

- If `success: True`, embedding must be non-empty
- If `success: False` and `partial: False`, embedding should be empty
- If any counter is present, it must be a non-negative `int`
- `status` must be a valid enum value (`SUCCESS`, `TIMEOUT`, `CRASH`, `OOM`,
  `INVALID_OUTPUT`, `FAILURE`)

---

## Medium Priority

### 4. Add `chain_length_std` and `qubit_overhead` to `EmbeddingResult`

`Algorithm_Contract.md` lists both as runner-computed fields on the dataclass. Neither
exists in `qebench/benchmark.py`'s `EmbeddingResult`:

- `chain_length_std` — already computed and stored in the SQLite schema via
  `qebench/compile.py`, but never on the Python object
- `qubit_overhead` — `total_qubits / n_source_nodes` — not computed anywhere

Adding these to the dataclass would make them available to `qeanalysis` without
needing to re-derive them from the DB.

---

### 5. Replace `time.time()` with `time.perf_counter()` in all algorithms

`Algorithm_Contract.md` is explicit: *"use `perf_counter` — NOT `time.time()`,
`perf_counter` is monotonic."* Every algorithm in `registry.py` uses `time.time()`.

`time.time()` can jump backwards under NTP clock corrections. Not a common failure
mode, but it directly contradicts the contract and produces non-monotonic wall times
in edge cases.

---

### 6. Add `supported_counters` class attribute to `EmbeddingAlgorithm`

`Algorithm_Contract.md` requires:

```python
class MyAlgorithm(EmbeddingAlgorithm):
    supported_counters = ['target_node_visits', 'cost_function_evaluations']
```

This distinguishes "algorithm does not report this counter" from "counter is not
applicable to this algorithm's design." Currently absent from the base class and all
implementations — `qeanalysis` cannot tell the difference.

---

### 7. Write `TestAlgorithmContract` parametrized test suite

`Algorithm_Contract.md` specifies a full contract test class parametrized over all
registered algorithms. It does not exist in `tests/test_qebench.py`. Nine tests
needed per algorithm:

1. Returns result on success (correct dict type, `wall_time` float, `cpu_time ≥ 0`)
2. Returns result on failure (not None, `success == False`, valid status)
3. Respects timeout (wall time < timeout + 3s grace)
4. Seed reproducibility (same seed → same embedding)
5. Does not modify input graphs (SHA-256 before/after)
6. No stdout output (capture and assert empty)
7. Counters are valid types (non-negative `int`, not float)
8. Counters reproducible with same seed
9. `version` is a non-empty string

---

## Low Priority

### 8. Remove stale `validate_embedding()` from `registry.py`

`qebench/registry.py:110–155` contains an old boolean-return `validate_embedding()`
that predates the Layer 1/2 system. It is never called anywhere. It also contains a
`print(f"Validation error: {e}")` which violates the no-stdout rule.

---

### 9. Reconcile `results.py` output with qeanalysis output structure

`qebench/results.py` still writes `README.md` and `summary.csv` into the batch root.
`qeanalysis` now writes `report.md`, `summary/`, and `statistics/` into a separate
reports directory. These are redundant and inconsistent:

- `ResultsManager._save_readme()` → writes `README.md` (stale name)
- `ResultsManager._save_summary()` → writes `summary.csv` (superseded by qeanalysis)

The simplest resolution: keep `ResultsManager` writing only `config.json` and the
raw data files (`results.db`, `runs.csv`, `workers/`), and let qeanalysis own all
human-readable outputs.

---

### 10. Add `SOURCE.md` and license files to vendored algorithm directories

`Algorithm_status.md` requires every vendored third-party algorithm to have:
- A copy of the original license
- A `SOURCE.md` with the source repo URL and exact commit hash

None of `algorithms/charme/`, `algorithms/oct_based/`, or `algorithms/pssa_dwave/`
have these. Required before any reproducibility claims in a paper.

---

### 11. Implement Layer 4 statistical batch checks (post-batch quality report)

Runs once after all trials complete — a quality report, not a gate:

- **Seed reproducibility spot-check**: re-run 5% of (algorithm, graph, topology)
  triples with same seed; assert identical embeddings
- **Timing outlier detection**: flag runs where wall time > 10× median for that
  (algorithm, graph class)
- **Counter monotonicity**: for the same algorithm on increasing graph sizes,
  counters should generally increase
- **Universal failure detection**: if all algorithms fail on an instance, flag as
  potentially unembeddable

---

## Discard

The following items from `Algorithm_status.md` are premature and should not be
implemented yet:

- **YAML config + CLI** (`ember run smoke.yaml --smoke`) — there is no CLI entry
  point and no config schema. The current `run_full_benchmark()` API is sufficient.
- **Phased test directory structure** (`tests/phase1/`, `tests/phase2/`, ...) —
  the flat `tests/` layout with descriptive class names works fine at current scale.
