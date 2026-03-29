# ATOM Algorithm - C++ Modifications

To integrate the ATOM algorithm into the `Quantum_Embedding_benchmark` framework and ensure it runs reliably on modern systems (macOS/Apple Silicon), several critical bug fixes and functional enhancements were applied to the original C++ source code.

## Summary of Changes

| Bug/Issue | Location | Fix Description | Rationale |
| :--- | :--- | :--- | :--- |
| **Segfault (Buffer Underflow)** | `main.cpp`: `extract_order()` | Added bounds check: `for (int i = 0; i < seed_limit && !seed_set->empty(); i++)` | Prevented `vector::erase` on an empty vector, which caused undefined behavior and crashes under `-O1` or higher optimization. |
| **Broken Multithreading** | `main.cpp`: `find_embedding_own()` | Replaced buggy `std::thread` implementation with the authors' own serial BFS fallback. | The original `std::thread` usage had data race issues and compilation warnings on modern C++. The serial version is stable and sufficient for benchmarking. |
| **No Embedding Output** | `main.cpp`: `main()` | Uncommented `embedding->print()` and moved it before the final `return 0;`. | Enabled the binary to output the logical-to-physical mapping to `stdout`, which is then captured and parsed by the Python wrapper. |

## Implementation Details

### 1. Buffer Underflow Fix
The `extract_order` function attempted to erase the first 5 elements of `seed_set` without checking if the vector actually contained that many elements. On macOS with modern `libc++`, this triggered a `negative-size-param` error in `memmove`.

```cpp
// Before
for (int i = 0; i < seed_limit; i++) {
  seed_set->erase(seed_set->begin());
}

// After
for (int i = 0; i < seed_limit && !seed_set->empty(); i++) {
  seed_set->erase(seed_set->begin());
}
```

### 2. Threading to Serial Fallback
The multithreaded BFS was unstable. Fortunately, a commented-out serial loop existed in the source.

```cpp
// Before: Buggy threaded version
while (it != old_node->end()) {
  vector<std::thread> threads;
  // ... spawn threads ...
  // ... join threads ...
}

// After: Stable serial version
int idx = 0;
for (auto it = old_node->begin(); it != old_node->end(); ++it) {
    BFS(embedding, *it, idx, topo_row, topo_column, label_HW, f);
    idx ++;
}
```

### 3. Output Capture
By uncommenting `embedding->print()`, the binary now outputs lines in the format `x y k color`. This allows the `qebench` Python wrapper to reconstruct the chain mapping from the captured `stdout`.

## Compilation
The algorithm should be compiled using the provided `Makefile` in `algorithms/atom/`:
```bash
cd algorithms/atom
make
```
This produces the `main` executable used by the benchmark framework.
