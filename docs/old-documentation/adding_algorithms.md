# Adding New Embedding Algorithms

This document explains how to add a new minor embedding algorithm to QEBench so it is automatically available for benchmarking, testing, and comparison.

---

## Overview

All algorithms are registered through a simple plugin system in `qebench/registry.py`. Once registered, an algorithm:

- Appears in `list_algorithms()` and can be passed by name to `run_full_benchmark()`
- Is automatically included when `methods=None` (benchmark all)
- Is validated by the same `validate_embedding()` checks as every other algorithm
- Has its results stored identically in `runs.csv` and `runs.json`

There are two integration patterns depending on what the algorithm is:

| Pattern | Use when |
|---------|----------|
| **Pure Python** | Algorithm is a Python library (e.g. `minorminer`, a new scipy-based heuristic) |
| **C++ / external binary** | Algorithm is compiled code called via subprocess (e.g. ATOM, OCT-Based) |

---

## 1. The `EmbeddingAlgorithm` Interface

Every algorithm must subclass `EmbeddingAlgorithm` and implement one method:

```python
from qebench import EmbeddingAlgorithm, register_algorithm
import networkx as nx

@register_algorithm("my_algo")
class MyAlgorithm(EmbeddingAlgorithm):
    """Short description — shown in list_algorithms() output."""

    def embed(self, source_graph, target_graph, timeout=60.0, **kwargs):
        ...
```

### `embed()` contract

**Inputs:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `source_graph` | `nx.Graph` | The logical problem graph to embed. Nodes are integers 0..n-1. |
| `target_graph` | `nx.Graph` | The hardware topology (Chimera, Pegasus, or Zephyr graph from `dwave_networkx`). |
| `timeout` | `float` | Wall-clock seconds. The algorithm must respect this limit and return (or return `None`) before it expires. |
| `**kwargs` | | Reserved for future algorithm-specific parameters. Accept and ignore. |

**Output:**

Return a `dict` with at minimum:

```python
{
    'embedding': {0: [42, 43], 1: [7], 2: [128, 129, 130], ...},
    'time': 0.034,   # elapsed seconds as float
}
```

- `embedding` maps every logical node (integer key) to a **non-empty list of physical qubit indices** (integers).
- `time` should be the wall-clock time the algorithm actually used, measured inside `embed()`. Use `time.time()` before and after the core computation.
- Additional keys are allowed (e.g. `'method'`, `'chimera_dims'`) and are stored in `runs.json` but ignored by the benchmark runner.

**Return `None` on failure** — any of these conditions:
- No embedding was found within `timeout`
- The algorithm raised an exception internally
- The binary was not found / not compiled

Do **not** raise exceptions out of `embed()`. Catch all errors internally and return `None`. The benchmark runner treats `None` as a failed trial (`success=False`) and records it without crashing.

### Validation

After `embed()` returns, `validate_embedding()` runs automatically. It checks:

1. All source nodes are keys in `embedding`
2. All chains are non-empty
3. All physical qubits exist in `target_graph`
4. Chains are disjoint (no qubit appears in two chains)
5. Each chain is connected in `target_graph`
6. Every source edge has at least one physical edge between its two chains

A result can be `success=True` (embedding found) but `is_valid=False` (embedding found but fails one of the above checks). Both are recorded. This is what `oct-triad-reduce` exhibits on non-bipartite graphs.

---

## 2. Pure Python Algorithm

The simplest case — the algorithm is a Python library or custom Python code.

```python
# In qebench/registry.py, after the existing imports

@register_algorithm("my_greedy")
class MyGreedyAlgorithm(EmbeddingAlgorithm):
    """Custom greedy heuristic — describe what it does here."""

    def embed(self, source_graph, target_graph, timeout=60.0, **kwargs):
        import time
        from my_library import greedy_embed   # your library

        start = time.time()
        try:
            raw = greedy_embed(
                list(source_graph.edges()),
                list(target_graph.edges()),
                time_limit=timeout,
            )
            elapsed = time.time() - start

            if not raw:
                return None

            # Ensure keys and values are plain Python ints/lists
            embedding = {int(k): [int(q) for q in chain] for k, chain in raw.items()}
            return {'embedding': embedding, 'time': elapsed}

        except Exception as e:
            print(f"my_greedy error: {e}")
            return None
```

**Common pitfalls:**
- Embedding keys must be integers matching `source_graph.nodes()` exactly. If your library returns string keys, convert them.
- Chains must be lists of integers. Some libraries return tuples or numpy integers — convert with `[int(q) for q in chain]`.
- Do not let the algorithm run past `timeout`. Pass the timeout to the underlying library if it supports one; otherwise wrap the call in a `threading.Timer` or `concurrent.futures`.

---

## 3. C++ / External Binary Algorithm

For compiled algorithms (like ATOM and OCT-Based), `embed()` writes the problem graph to a temporary file, invokes the binary via `subprocess`, reads the output file, then cleans up.

### File structure convention

Place the algorithm's source code in:
```
algorithms/
└── my_algo/
    ├── Makefile       # produces: algorithms/my_algo/my_algo (the binary)
    ├── src/
    └── ...
```

The Makefile should produce a single binary at a known relative path (e.g. `algorithms/my_algo/my_algo` or `algorithms/my_algo/build/driver`). The `embed()` method locates this binary relative to the project root.

### Input format

Decide on an input format your binary accepts. Most embedding binaries expect an edge-list text file. The OCT-suite uses this format (which is also what ATOM uses):

```
<number_of_nodes>
<node_0>
<node_1>
...
<node_n-1>
<u0> <v0>
<u1> <v1>
...
```

Where node orderings are `0, 1, ..., n-1` and edges follow.

### Output format

Your binary needs to write an embedding to a file (or stdout). The simplest format is one line per logical node:

```
0: 42, 43
1: 7
2: 128, 129, 130
```

### Template

```python
import os
import subprocess
import tempfile
import time
from pathlib import Path

@register_algorithm("my_cpp_algo")
class MyCppAlgorithm(EmbeddingAlgorithm):
    """My C++ embedding algorithm — brief description."""

    _BINARY = Path("./algorithms/my_algo/my_algo")

    def embed(self, source_graph, target_graph, timeout=60.0, **kwargs):
        binary = self._BINARY.resolve()
        if not binary.exists():
            print("⚠️  my_cpp_algo not compiled. Run: cd algorithms/my_algo && make")
            return None

        # --- Write input file ---
        with tempfile.NamedTemporaryFile(
            mode='w', suffix='.graph', delete=False
        ) as f:
            n = source_graph.number_of_nodes()
            f.write(f"{n}\n")
            for node in range(n):
                f.write(f"{node}\n")
            for u, v in source_graph.edges():
                f.write(f"{u} {v}\n")
            input_file = f.name

        output_file = tempfile.mktemp(suffix='.embedding')

        start = time.time()
        try:
            subprocess.run(
                [str(binary), '-i', input_file, '-o', output_file],
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            elapsed = time.time() - start

            # --- Parse output file ---
            embedding = {}
            if os.path.exists(output_file) and os.path.getsize(output_file) > 0:
                with open(output_file, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if ':' in line:
                            node_part, chain_part = line.split(':', 1)
                            chain = [int(x) for x in chain_part.split(',') if x.strip()]
                            if chain:
                                embedding[int(node_part.strip())] = chain

            if not embedding:
                return None

            return {'embedding': embedding, 'time': elapsed}

        except subprocess.TimeoutExpired:
            return None
        except Exception as e:
            print(f"my_cpp_algo error: {e}")
            return None
        finally:
            # Always clean up temp files
            for p in [input_file, output_file]:
                if os.path.exists(p):
                    os.unlink(p)
```

**Key points:**
- Always use `finally` to clean up temp files, including on timeout and exception.
- Use `capture_output=True` to suppress binary stdout/stderr from flooding the terminal.
- `timeout=timeout` on `subprocess.run` causes it to raise `subprocess.TimeoutExpired` — catch this and return `None`.
- The `cwd` argument controls the working directory of the subprocess. Some binaries (like ATOM) require `cwd` to be their own directory to find relative data files. Pass `cwd=str(binary.parent)` if needed.

---

## 4. Where to Add the Code

### Option A: Add directly to `qebench/registry.py` (simple algorithms)

For short, self-contained implementations, add the class at the bottom of `registry.py` after the existing algorithm definitions. This is the simplest approach and is how `minorminer`, `clique`, and `charme` are implemented.

### Option B: Separate file + import (larger algorithms)

For more complex algorithms, put the implementation in a new file and import it:

```
qebench/
├── registry.py
├── algorithms/
│   ├── __init__.py
│   └── my_algo.py     ← your implementation here
```

Then at the bottom of `registry.py`:

```python
# Import to trigger registration
from qebench.algorithms import my_algo  # noqa: F401
```

The `@register_algorithm` decorator runs at import time, so the import is all that's needed.

### Option C: Source code in `algorithms/` (external repos / compiled code)

For C++ algorithms or external codebases, keep the source in `algorithms/<name>/` and only the Python wrapper class in `registry.py`. This keeps the compiled code organized:

```
algorithms/
├── atom/              # C++ source + Makefile
├── oct_based/         # C++ source + Makefile
└── my_algo/           # your C++ source + Makefile
```

---

## 5. Registering Multiple Variants

If your algorithm has multiple variants (different flags, reduction steps), use a factory function rather than copy-pasting the class. This is how the six OCT-suite variants are registered:

```python
def _make_my_algo_variant(variant_name, flags, desc):
    class MyAlgoVariant(EmbeddingAlgorithm):
        __doc__ = desc
        def embed(self, source_graph, target_graph, timeout=60.0, **kwargs):
            # use variant_name and flags here
            ...
    MyAlgoVariant.__name__ = f"MyAlgo_{variant_name}"
    return MyAlgoVariant

_VARIANTS = {
    'fast':    (['-f'], 'Fast variant — fewer repeats'),
    'precise': (['-r', '200'], 'Precise variant — more repeats'),
}
for _name, (_flags, _desc) in _VARIANTS.items():
    _cls = _make_my_algo_variant(_name, _flags, _desc)
    register_algorithm(f"my_algo-{_name}")(_cls)
```

---

## 6. Verifying the Registration

After adding the class, confirm it appears:

```python
from qebench import list_algorithms
print(list_algorithms())
# [..., 'my_algo', ...]
```

Then run a quick smoke test on a small graph:

```python
from qebench import benchmark_one
import networkx as nx
import dwave_networkx as dnx

result = benchmark_one(
    source_graph=nx.complete_graph(4),
    target_graph=dnx.chimera_graph(4),
    algorithm="my_algo",
    problem_name="K4_test",
)
print(result.success, result.is_valid, result.avg_chain_length)
```

---

## 7. Updating the Tests

Add a test case to `tests/test_qebench.py` in the `TestAlgorithmRegistry` class:

```python
def test_my_algo_registered(self):
    from qebench import ALGORITHM_REGISTRY
    assert 'my_algo' in ALGORITHM_REGISTRY

def test_my_algo_runs(self):
    """Smoke test: runs without error on K4."""
    result = benchmark_one(
        source_graph=nx.complete_graph(4),
        target_graph=self.chimera,
        algorithm='my_algo',
        problem_name='K4',
    )
    # Result should be either a valid success or a clean failure
    assert isinstance(result.success, bool)
    if result.success:
        assert result.avg_chain_length > 0
```

Run the full test suite to confirm nothing is broken:

```bash
pytest tests/ -v
```

---

## 8. Updating the README Algorithm Status Table

After verifying the algorithm works, update the table in `README.md`:

```markdown
| `my_algo` | ✅ Working | Brief description |
```

Or if it has known limitations:

```markdown
| `my_algo` | ⚠️ Partial | Valid only on sparse graphs |
```
