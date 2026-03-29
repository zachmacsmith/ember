# Faulty Qubit Simulation — Feature Specification

---

## Overview

Benchmark runs can simulate hardware faults by removing qubits and/or couplers from the topology before passing it to algorithms. Two modes are supported: random fault simulation (a fault rate applied stochastically) and explicit fault specification (exact nodes and edges to remove). The mode is inferred from which parameters are passed — no separate enable flag is needed.

---

## Interface

Parameters added to `run_full_benchmark()`:

```python
run_full_benchmark(
    ...
    fault_rate: float = 0.0,                        # fraction of qubits to remove randomly
    fault_seed: Optional[int] = None,               # seed for random fault generation
    faulty_nodes: Optional[Collection[int]] = None, # explicit qubits to remove
    faulty_couplers: Optional[Collection[Tuple[int, int]]] = None,  # explicit couplers to remove
)
```

Mode is inferred:
- `fault_rate > 0` → random fault simulation
- `faulty_nodes` or `faulty_couplers` non-empty → explicit fault simulation
- All defaults → no simulation, topology unchanged
- `fault_rate > 0` AND (`faulty_nodes` or `faulty_couplers`) non-empty → `ValueError` raised immediately before any runs start

---

## `simulate_faults()`

Standalone function, not a method. Usable independently of the benchmark runner.

```python
def simulate_faults(
    topology: nx.Graph,
    fault_rate: float = 0.0,
    fault_seed: Optional[int] = None,
    faulty_nodes: Optional[Collection[int]] = None,
    faulty_couplers: Optional[Collection[Tuple[int, int]]] = None,
) -> nx.Graph:
```

### Random mode (`fault_rate > 0`)

```python
rng = random.Random(fault_seed)
n_faults = int(len(topology) * fault_rate)  # len(topology) = node count in NetworkX
faulty = set(rng.sample(list(topology.nodes()), n_faults))
return topology.subgraph([n for n in topology.nodes() if n not in faulty]).copy()
```

Removes `n_faults` randomly selected nodes and all their incident edges. Returns a copy, not a view.

### Explicit mode (`faulty_nodes` or `faulty_couplers` provided)

Two independent removal steps applied in order:

1. Remove all nodes in `faulty_nodes` and their incident edges
2. Remove all edges in `faulty_couplers` while keeping both endpoint nodes (unless already removed in step 1)

```python
working = topology.copy()
if faulty_nodes:
    working.remove_nodes_from(faulty_nodes)
if faulty_couplers:
    working.remove_edges_from(faulty_couplers)
return working
```

### Validation

Validated before any modification:

- Any node in `faulty_nodes` that does not exist in `topology` → `ValueError` with the offending node IDs listed
- Any coupler in `faulty_couplers` referencing a non-existent node → `ValueError` with the offending coupler listed
- `fault_rate` outside `[0.0, 1.0]` → `ValueError`
- `fault_rate > 0` and non-empty `faulty_nodes` or `faulty_couplers` → `ValueError`

Silent failure (NetworkX ignoring missing nodes) is not acceptable here — explicit fault lists are expected to come from hardware calibration data and a mismatch with the topology indicates a configuration error.

---

## Integration with `run_full_benchmark()`

Fault simulation is applied once per topology per run, before any tasks are built. All trials across all algorithms and graphs share the same faulted topology. This is the correct behaviour — the fault pattern represents a fixed hardware state, not a per-trial condition.

```python
# Applied during topology resolution, before task list construction
if fault_rate > 0:
    topology = simulate_faults(topology, fault_rate=fault_rate, fault_seed=fault_seed)
elif faulty_nodes or faulty_couplers:
    topology = simulate_faults(topology, faulty_nodes=faulty_nodes, faulty_couplers=faulty_couplers)
```

For multi-topology runs, fault simulation is applied independently to each topology using the same parameters.

---

## Config Logging

Fault parameters are recorded in `config.json` for full reproducibility. The exact removed nodes and couplers are always logged — not just the parameters used to generate them — so the precise topology used in a run can be reconstructed without re-running `simulate_faults`.

**Random mode:**
```json
"fault_simulation": {
    "mode": "random",
    "fault_rate": 0.05,
    "fault_seed": 42,
    "faulty_nodes": [103, 205, 441, ...],
    "faulty_couplers": []
}
```

**Explicit mode:**
```json
"fault_simulation": {
    "mode": "explicit",
    "fault_rate": null,
    "fault_seed": null,
    "faulty_nodes": [103, 205],
    "faulty_couplers": [[103, 104], [200, 205]]
}
```

**No faults:**
```json
"fault_simulation": null
```

---

---

## Additional Behaviour

### Disconnected Topology

Fault simulation may produce a disconnected topology, particularly at higher fault rates or when explicit faults target high-degree hub nodes. This is not treated as an error — the run proceeds and algorithms handle unembeddable instances via normal failure paths.

After `simulate_faults` returns, the runner checks connectivity. If the resulting topology is disconnected, `TOPOLOGY_DISCONNECTED` is added to the run-level warning registry. It appears in the end summary:

```
⚠️  Warnings:
   TOPOLOGY_DISCONNECTED  Fault simulation produced a disconnected topology.
                          pegasus_16: 3 connected components after fault removal.
```

Full details are written to the batch log regardless of verbose setting.

### Isolated Node Cleanup

In explicit mode, removing couplers may leave nodes with no remaining edges. Such nodes are useless for embedding and are automatically removed as a cleanup step after coupler removal:

```python
isolated = [n for n, deg in working.degree() if deg == 0]
working.remove_nodes_from(isolated)
```

Isolated nodes removed during cleanup are logged in `config.json` under `faulty_nodes` alongside any explicitly specified faulty nodes, so the full set of removed nodes is always on record. The cleanup step does not apply in random mode since node removal already takes incident edges with it.

## Verification

- `fault_rate=0.05` on Pegasus 16 (~5,600 nodes) produces ~280 removed nodes (within ±1 of `int(5600 * 0.05)`)
- Same `fault_rate` and `fault_seed` produces identical faulted topology on two calls
- `faulty_nodes={103}` removes node 103 and all its incident edges; node 104 remains present
- `faulty_couplers={(103, 104)}` removes the edge between 103 and 104 but both nodes remain
- Non-existent node in `faulty_nodes` raises `ValueError` naming the offending node
- Non-existent coupler raises `ValueError` naming the offending coupler
- `fault_rate=0.05` alongside non-empty `faulty_nodes` raises `ValueError`
- `fault_rate=0.0` alongside non-empty `faulty_nodes` does not raise — zero rate is treated as no random faults
- Config `faulty_nodes` list matches the actual nodes removed, verified by comparing against the topology node sets before and after