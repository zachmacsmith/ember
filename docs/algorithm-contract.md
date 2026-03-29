# EMBER — Algorithm Contract

This document is the complete specification for implementing an algorithm wrapper in EMBER. Read the strict requirements. Everything else is optional.

---

## Strict Requirements

A wrapper that satisfies these five requirements is a valid, fully runnable algorithm.

### 1. Subclass and register

```python
from ember_qc.registry import EmbeddingAlgorithm, register_algorithm

@register_algorithm("my_algorithm")
class MyAlgorithm(EmbeddingAlgorithm):
    ...
```

### 2. Implement `embed()`

```python
def embed(self, source_graph, target_graph, **kwargs) -> dict:
    ...
```

- `source_graph`: NetworkX Graph. Do not assume specific node labeling.
- `target_graph`: NetworkX Graph. Node labels depend on topology.
- `**kwargs`: must be accepted. The runner passes `seed`, `timeout`, and other
  parameters through this.
- Return `{'embedding': {source_node: [target_nodes, ...]}}` on success.
- Return `{'embedding': {}}` on failure.
- Never return `None`. Never raise an unhandled exception.

The `'embedding'` key is always required. The runner calls `result.get('embedding', {})`
on every return path — a dict without it is treated as failure with no embedding.

```python
# Correct — named key, plain Python lists
return {
    'embedding': {
        0: [100, 101, 102],
        1: [200, 201],
        2: [300],
    }
}

# Wrong — embedding returned directly without named key
return {0: [100, 101], 1: [200]}

# Wrong — sets, tuples, and numpy arrays break downstream serialization
return {'embedding': {0: {100, 101}, 1: (200,), 2: np.array([300])}}

# If your algorithm uses numpy internally, cast before returning
embedding = {int(k): [int(v) for v in chain] for k, chain in raw.items()}
return {'embedding': embedding}
```

### 3. Implement `version`

```python
@property
def version(self) -> str:
    return "1.0.0"
```

Return a meaningful version string. For vendored code, return the commit hash you
copied from. For pip packages, return the installed version string.

### 4. Do not modify input graphs

`source_graph` and `target_graph` are shared objects across parallel runs. If your
algorithm needs to mutate the graph, work on a copy:

```python
source = source_graph.copy()
```

### 5. Respect the timeout

Check `kwargs.get('timeout', 60.0)` and ensure your algorithm terminates within that
time. The mechanism is up to you — pass it as a native parameter, a CLI flag, or poll
`time.perf_counter()` in your main loop. An algorithm that ignores the timeout blocks
the entire benchmark.

```python
timeout = kwargs.get('timeout', 60.0)
```

The contract test suite verifies this empirically: your algorithm is run against an
impossible graph with a short timeout and must return within a grace period.

Do not call `sys.exit()` or `os._exit()`. Raise an exception if something goes wrong.
The runner catches it, logs it, and marks the run `CRASH`.

---

## What the Runner Computes

The following are computed or set by the runner from the validated embedding. Do not
return these — if present, they are ignored:

- `success` — inferred from embedding non-emptiness
- `wall_time` — measured externally around the `embed()` call; any `'time'` key in your return dict is ignored
- `cpu_time` — measured externally via `process_time()` or `RUSAGE_CHILDREN`
- `is_valid` — set after Layer 1 structural validation
- `status` on success — set to `SUCCESS` after validation passes
- `total_qubits_used`, `max_chain_length`, `avg_chain_length`, `chain_length_std`,
  `total_couplers_used`, `qubit_overhead` — all computed from the validated embedding

What actually flows through from your return dict to `EmbeddingResult`:

| Field | Key in your dict |
|-------|-----------------|
| `embedding` | `'embedding'` |
| `status` (failure only) | `'status'` |
| `partial` | `'partial'` |
| `error` | `'error'` |
| `metadata` | `'metadata'` |
| Four algorithmic counters | see Suggestions |

---

## Suggestions

These improve analysis quality. None are required for a valid, runnable result.

### Seed handling

The runner seeds `random` and `numpy.random` globally before every trial via
`_reseed_globals()`. You only need to handle seeding yourself if your algorithm has
its own internal RNG parameter — for example, minorminer's `random_seed=`:

```python
seed = kwargs.get('seed', None)

embedding = minorminer.find_embedding(
    source_graph.edges(),
    target_graph.edges(),
    random_seed=seed,
)
```

If your algorithm uses only Python's `random` or `numpy.random`, no seeding code is
needed — the runner handles it.

### Subprocess flag

If your algorithm calls an external binary via `subprocess`, set this class attribute:

```python
class MyAlgorithm(EmbeddingAlgorithm):
    _uses_subprocess = True
```

The runner uses `RUSAGE_CHILDREN` to measure CPU time for subprocess algorithms.
Without this flag, your algorithm will record near-zero CPU time in the database
with no warning.

For temporary file I/O in C++ wrappers, use `tempfile.mkstemp()` — not
`NamedTemporaryFile`, which holds the file handle open while the subprocess tries
to read it:

```python
import tempfile, os

fd, path = tempfile.mkstemp(suffix='.json')
try:
    with os.fdopen(fd, 'w') as f:
        json.dump(data, f)
    proc = subprocess.run(["./binary", path, ...], timeout=timeout)
finally:
    if os.path.exists(path):
        os.remove(path)
```

### Failure status

When returning an empty embedding, include a `'status'` key to distinguish why. The
runner defaults to `FAILURE` if absent, which loses the `TIMEOUT` vs `FAILURE`
distinction that matters for analysis — whether a graph is unembeddable or just needs
more time are different conclusions.

| Status | When to set |
|--------|-------------|
| `FAILURE` | Algorithm completed but found no valid embedding |
| `TIMEOUT` | Time limit reached before a solution was found |
| `OOM` | Out of memory, if your algorithm can detect this |

```python
return {'embedding': {}, 'status': 'TIMEOUT'}
```

Do not set `SUCCESS`, `INVALID_OUTPUT`, or `CRASH` — these are set by the runner.

### Algorithmic counters

Declare which counters your algorithm reports and populate them in the return dict.
These measure algorithmic work independent of hardware and are used for cross-algorithm
comparison.

```python
class MyAlgorithm(EmbeddingAlgorithm):
    supported_counters = ['target_node_visits', 'cost_function_evaluations']
```

| Counter | What to count |
|---------|--------------|
| `target_node_visits` | Each target graph node examined during path search or chain placement |
| `cost_function_evaluations` | Each call to the objective or cost function |
| `embedding_state_mutations` | Each time a chain assignment is created, changed, or destroyed |
| `overlap_qubit_iterations` | Each complete pass of an overlap-resolution loop |

Only populate counters you can measure precisely. A wrong counter is worse than a
missing one — it silently invalidates cross-algorithm comparisons. Each increment
must be a single integer addition with no branching or allocation per increment.
Omit keys entirely for counters you do not measure — do not set them to `0` unless
the algorithm genuinely performed zero of that operation.

```python
def embed(self, source_graph, target_graph, **kwargs):
    visits = 0
    mutations = 0

    # ... algorithm work ...
    for q in candidates:
        visits += 1
    embedding[v] = chain
    mutations += 1

    return {
        'embedding': {0: [100, 101], 1: [200]},
        'target_node_visits': visits,
        'embedding_state_mutations': mutations,
    }
```

---

## Opt-In Features

### Graceful early stopping

If you prefer to clean up state before returning on timeout rather than being
interrupted mid-execution:

```python
timeout = kwargs.get('timeout', 60.0)
wall_start = time.perf_counter()

for iteration in range(max_iterations):
    if time.perf_counter() - wall_start >= timeout:
        return {'embedding': {}, 'status': 'TIMEOUT'}
    # ... iteration work ...
```

### Partial embedding on timeout

If your algorithm has useful intermediate state when it times out, you can return it
for diagnostic analysis. The runner preserves the embedding but skips validation and
metric computation.

```python
return {
    'embedding': partial_embedding,   # may contain overlaps — not a valid embedding
    'success': False,
    'partial': True,
    'status': 'TIMEOUT',
}
```

All four keys are required for the runner to enter the partial path. Omitting any one
causes the runner to treat it as a normal failure and discard the embedding.

---

## Availability declarations

Declare pip package requirements and binary dependencies so EMBER can report
availability correctly:

```python
class MyAlgorithm(EmbeddingAlgorithm):
    _requires = ["some_pip_package"]           # checked via importlib
    _binary   = Path("/path/to/binary")        # or a zero-arg callable
```

`is_available()` returns `(True, "")` if all requirements are met, or
`(False, "reason string")` if not. The runner shows the reason in `ember algos list`.

---

## Topology restrictions

If your algorithm only works on certain hardware families, declare it:

```python
class MyAlgorithm(EmbeddingAlgorithm):
    supported_topologies = ['chimera']
```

Incompatible (algorithm, topology) pairs are skipped before the run starts with a
`TOPOLOGY_INCOMPATIBLE` warning. `None` (the default) means all topologies.

---

## Vendored Code

All third-party algorithm code must be copied into `algorithms/` alongside:

- The original license file
- A `SOURCE.md` documenting the source repo URL, exact commit hash, and any patches applied

```
# SOURCE.md
Source: https://github.com/example/algorithm
Commit: a3f8c21d

## Patches
- [2026-03-01] Fixed None return on isolated vertices. Upstream issue: #42.
```

Document patches at the patch site in the source file as well:

```python
# EMBER PATCH — 2026-03-01
# Upstream bug: returns None when source graph has isolated vertices.
# Fixed by returning {} explicitly.
```

Do not use external pip dependencies for algorithm implementations. Infrastructure
packages (NetworkX, NumPy, D-Wave SDK) remain as pip dependencies. Only algorithm
implementations are vendored.

C++ algorithms cannot be vendored as binaries. Document the exact build steps and
compiler version in `algorithms/{algo}/BUILD.md`.

---

## Minimum Valid Example

```python
from ember_qc.registry import EmbeddingAlgorithm, register_algorithm
import minorminer

@register_algorithm("minorminer_basic")
class MinorMinerBasic(EmbeddingAlgorithm):

    supported_counters = []
    _uses_subprocess = False

    @property
    def version(self) -> str:
        return "0.1.9"

    def embed(self, source_graph, target_graph, **kwargs) -> dict:
        timeout = kwargs.get('timeout', 60.0)
        seed    = kwargs.get('seed', None)

        embedding = minorminer.find_embedding(
            source_graph.edges(),
            target_graph.edges(),
            timeout=timeout,
            random_seed=seed,
        )

        return {'embedding': dict(embedding)} if embedding else {'embedding': {}}
```

---

## Contract Test Suite

These tests run against every registered algorithm. Your wrapper must pass all of them
before merging. The full suite is at `tests/algorithms/test_algorithm_contracts.py`.

Core checks:

| Test | What it verifies |
|------|-----------------|
| `test_returns_dict` | `embed()` returns a dict, never None |
| `test_has_embedding_key` | Return dict contains `'embedding'` key |
| `test_has_time_key` | Return dict contains `'time'` key (float) |
| `test_embedding_chains_are_lists` | All chains are lists of ints, not sets/tuples/arrays |
| `test_failure_returns_dict_not_none` | Failure on impossible graph returns a dict |
| `test_failure_embedding_is_empty_dict` | Failure embedding is `{}` not `None` |
| `test_completes_within_grace_period` | With 0.5s timeout, returns within 5s |
| `test_same_seed_same_embedding` | Same seed → identical embedding on two consecutive calls |
| `test_graphs_unchanged_after_embed` | Input graphs are not mutated |
| `test_no_stdout_on_success` | No stdout output on successful embedding |
| `test_version_returns_string` | `version` property returns a non-empty string |
| `test_counters_are_nonneg_ints` | Declared counters are non-negative integers |
