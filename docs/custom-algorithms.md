# Custom Algorithms

EMBER loads algorithm files from a user directory automatically on startup. You can add any algorithm that satisfies the contract and it will appear in `ember algos list`, be selectable in experiment YAML files, and run alongside built-in algorithms.

---

## Where to put your file

```bash
ember algos dir
```

This prints the path to your user algorithms directory. On macOS it is typically:

```
~/Library/Application Support/ember-qc/algorithms/
```

Any `.py` file placed there is imported when `ember_qc` is loaded. If the file contains `@register_algorithm(...)` decorators, those algorithms are registered automatically.

---

## Get the template

```bash
ember algos template > my_algorithm.py
```

This writes a fully commented template to `my_algorithm.py`. Open it and fill in your implementation.

---

## Minimum implementation

```python
from ember_qc.registry import EmbeddingAlgorithm, register_algorithm

@register_algorithm("my-algorithm")
class MyAlgorithm(EmbeddingAlgorithm):

    @property
    def version(self) -> str:
        return "1.0.0"

    def embed(self, source_graph, target_graph, **kwargs) -> dict:
        timeout = kwargs.get("timeout", 60.0)
        seed    = kwargs.get("seed", None)

        # ---- your algorithm here ----

        # Return on success:
        return {"embedding": {source_node: [target_qubits, ...], ...}}

        # Return on failure:
        # return {"embedding": {}, "status": "FAILURE"}

        # Return on timeout:
        # return {"embedding": {}, "status": "TIMEOUT"}
```

The five requirements are:

1. Subclass `EmbeddingAlgorithm` and apply `@register_algorithm("name")`
2. Implement `embed()` — returns a dict with an `'embedding'` key
3. Implement `version` — returns a non-empty string
4. Never modify `source_graph` or `target_graph` in place
5. Honour the `timeout` kwarg and return within it

For the full formal specification, see [algorithm-contract.md](algorithm-contract.md).

---

## Add it to your algorithms directory

```bash
cp my_algorithm.py "$(ember algos dir)/"
```

Verify it loaded:

```bash
ember algos list
```

Your algorithm appears with a `[custom]` tag. If it failed to load, a warning is printed — check for import errors in your file.

---

## Use it in a benchmark

```yaml
# experiment.yaml
algorithms:
  - minorminer
  - my-algorithm
graphs: "quick"
topologies:
  - pegasus_16
trials: 5
```

```bash
ember run experiment.yaml
```

---

## Declaring dependencies

If your algorithm requires pip packages, declare them so `is_available()` works correctly:

```python
@register_algorithm("my-algorithm")
class MyAlgorithm(EmbeddingAlgorithm):
    _requires = ["some_package", "another_package"]
```

If any listed package is not importable, `ember algos list` shows the algorithm as unavailable with a reason, and `run_full_benchmark()` raises an error before starting rather than failing mid-run.

If your algorithm wraps a C++ binary:

```python
from ember_qc._paths import get_user_binary_dir

@register_algorithm("my-binary-algo")
class MyBinaryAlgorithm(EmbeddingAlgorithm):
    _binary = get_user_binary_dir() / "my_algo" / "binary"
    _uses_subprocess = True
```

---

## Restricting to certain topologies

If your algorithm only works on Chimera hardware:

```python
@register_algorithm("chimera-only")
class ChimeraAlgorithm(EmbeddingAlgorithm):
    supported_topologies = ["chimera"]
```

EMBER skips incompatible (algorithm, topology) pairs before the run starts and logs a `TOPOLOGY_INCOMPATIBLE` warning.

---

## Algorithmic counters (optional)

If your algorithm can report how much work it did, declare the counters it supports and include them in the return dict:

```python
@register_algorithm("my-algorithm")
class MyAlgorithm(EmbeddingAlgorithm):
    supported_counters = ["target_node_visits", "embedding_state_mutations"]

    def embed(self, source_graph, target_graph, **kwargs) -> dict:
        visits = 0
        mutations = 0

        # ... your algorithm ...
        for q in candidates:
            visits += 1

        return {
            "embedding": result,
            "target_node_visits": visits,
            "embedding_state_mutations": mutations,
        }
```

Available counters:

| Counter | What to count |
|---------|--------------|
| `target_node_visits` | Each target graph node examined during search |
| `cost_function_evaluations` | Each call to the objective/cost function |
| `embedding_state_mutations` | Each chain assignment created, changed, or destroyed |
| `overlap_qubit_iterations` | Each complete pass of an overlap-resolution loop |

Only declare counters you can measure precisely. Omit keys you cannot measure — do not set them to `0` unless the algorithm genuinely performed zero of that operation.

---

## Removing a custom algorithm

Delete the `.py` file from the algorithms directory:

```bash
rm "$(ember algos dir)/my_algorithm.py"
```

The algorithm disappears from `ember algos list` on the next run.

---

## Vendored third-party code

If you are copying an existing algorithm implementation into the repo (rather than importing it as a pip package), follow the vendoring policy:

1. Place the source files in `packages/ember-qc/src/ember_qc/algorithms/`
2. Include the original `LICENSE` file
3. Create a `SOURCE.md` with the repo URL, commit hash, and a list of any patches applied

```
# SOURCE.md
Source: https://github.com/example/algorithm
Commit: a3f8c21d

## Patches
- [2026-03-01] Fixed None return on isolated vertices.
```

Mark patches in the source file too:

```python
# EMBER PATCH — 2026-03-01
# Upstream: returns None on isolated vertices. Fixed.
```

---

## Troubleshooting

**Algorithm does not appear in `ember algos list`**
- Check that the file is in `ember algos dir`
- Run `python /path/to/my_algorithm.py` to catch import errors
- Ensure `@register_algorithm(...)` is applied before the class body ends

**Algorithm shows as unavailable**
- If `_requires` is set, check that all listed packages are installed: `pip list | grep <package>`
- If `_binary` is set, check that the file exists and is executable

**`ember run` raises "algorithm not available"**
- The runner checks availability before starting. Install the missing dependency or remove the algorithm from the YAML.

**Results show `INVALID_OUTPUT` for every trial**
- Your `embed()` is returning numpy types in the embedding chains. Cast: `{int(k): [int(v) for v in chain] for k, chain in raw.items()}`

**Results show `CRASH` for every trial**
- Your `embed()` is raising an unhandled exception. Add a `try/except` and return `{"embedding": {}, "status": "FAILURE", "error": str(e)}`.
