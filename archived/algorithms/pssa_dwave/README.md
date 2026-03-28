# pssa_dwave

**PSSA minor embedding algorithm adapted for D-Wave hardware — Chimera, Pegasus, Zephyr.**

Based on Sugie et al. (2020) *"Minor Embedding with Large-Scale Quantum Annealing"* (arXiv:2004.03819), rewritten to target D-Wave topologies instead of Hitachi's King's graph.

---

## What changed from the paper

| Component | Paper (King's graph) | This repo (D-Wave) |
|-----------|---------------------|---------------------|
| Hardware graph | King's graph `L×L`, degree 8 | `chimera(m)`, `pegasus(m)`, `zephyr(m)` |
| Guiding pattern | Okuyama K_{L+1} diagonal stripes | `minorminer.busclique` clique embedding |
| Schedule T0 | 60.315 (fixed) | 45–70 (topology-dependent) |
| Schedule Thalf | 33.435 (fixed) | 22–40 (topology-dependent) |
| Schedule beta | 0.9999 (fixed) | 0.9998–0.99995 (topology-dependent) |
| tmax | 7×10^7 (102,400-node HW) | Auto-scaled: `max(200k, 7e7 × n_hw / 102400)` |
| Everything else | — | Identical |

The core algorithm — path invariant, swap/shift moves, double-exponential schedule, terminal search — is unchanged.

---

## Install

```bash
pip install dwave-networkx minorminer networkx numpy
pip install -e .
```

---

## Quick start

```python
import networkx as nx
from pssa_dwave import embed

# Embed a 3-regular graph into Chimera(4)
I = nx.random_regular_graph(3, 10, seed=0)
success, phi = embed(I, topology="chimera", size=4, seed=42)

print(success)   # True/False
print(phi)       # {input_node: [hw_node, ...], ...}
```

```python
# More control
from pssa_dwave import ImprovedPSSA

algo = ImprovedPSSA(
    topology = "pegasus",
    size     = 2,
    tmax     = 500_000,
    weighted = True,      # best for regular graphs
    seed     = 0,
)
result = algo.run(I)
print(result)  # EmbeddingResult(pegasus(2), ✓ 15/15 edges, 1.23s)
```

---

## Parameters — full explanation

### `topology`
Which D-Wave hardware graph to build.

| Value | Hardware | Degree | Notes |
|-------|----------|--------|-------|
| `"chimera"` | Chimera C(m,m,4) | ≈6 | Oldest, sparsest. Hardest to embed into. |
| `"pegasus"` | Pegasus P(m) | ≈15 | Current D-Wave Advantage hardware. Good balance. |
| `"zephyr"` | Zephyr Z(m) | ≈20 | Next-gen D-Wave. Densest, easiest to embed into. |

---

### `size` (integer, `m`)
The dimension parameter for the topology. Controls how many physical qubits exist.

| Topology | `size=2` | `size=4` | `size=8` | `size=16` |
|----------|----------|----------|----------|-----------|
| Chimera  | 128 nodes | 512 | 2,048 | 8,192 |
| Pegasus  | 24 nodes | 216 | 1,176 | 5,627 |
| Zephyr   | 36 nodes | 160 | 528 | 1,680 |

Practical rule: use `size=4` for chimera, `size=2` for pegasus/zephyr when testing. Use the actual machine size for production runs.

---

### `tmax` — annealing iterations
**The most important parameter for quality.**

Number of swap/shift proposals to make total. More = better embeddings, slower runtime.

```
Default (auto): max(200_000, int(7e7 × n_hw / 102_400))
```

| Preset | tmax | Use case |
|--------|------|----------|
| `pssa-fast` | 50,000 | Quick feasibility check, large sweeps |
| auto chimera(4) | ~1,400,000 | Default — good balance |
| auto pegasus(16) | ~3,850,000 | Default for full Advantage hardware |
| `pssa-thorough` | 2,000,000 | Final benchmarks, hard graphs |

**Why auto-scaling?** The paper used 7×10^7 iterations for a 102,400-node King's graph. D-Wave hardware is much smaller (max ~5,600 nodes for Pegasus). Scaling proportionally keeps annealing time per hardware node roughly constant.

---

### `T0` — initial temperature (phase 1)
Controls how willing the algorithm is to accept *worse* embeddings early on, allowing escape from local traps.

| Topology | Default | Why |
|----------|---------|-----|
| Chimera | **70.0** | Sparse (degree 6) → fewer move options → needs more exploration |
| Pegasus | **55.0** | Medium density — close to paper defaults |
| Zephyr | **45.0** | Dense (degree 20) → many options per move → less exploration needed |

Higher T0 → more random early exploration → slower to converge but avoids traps.
Lower T0 → greedier early behaviour → faster but can get stuck.

---

### `Thalf` — phase 2 initial temperature
The algorithm has two annealing phases. `Thalf` is the temperature at the start of phase 2 (second half of iterations). Always less than T0.

| Topology | Default |
|----------|---------|
| Chimera | **40.0** |
| Pegasus | **28.0** |
| Zephyr | **22.0** |

The ratio `T0 / Thalf` controls how sharp the "reset" between phases is. The paper uses `60.315 / 33.435 ≈ 1.8×`. These defaults preserve that ratio per topology.

---

### `beta` — cooling rate
The exponential decay factor applied every `cool_every` steps.

```
T(t) = T0 × beta^(t // cool_every)
```

Closer to 1.0 → slower cooling → more exploration → better quality, slower.
Further from 1.0 → faster cooling → greedier, faster, more likely to get stuck.

| Topology | Default | Rationale |
|----------|---------|-----------|
| Chimera | **0.9998** | Slow cooling — sparse HW needs more search |
| Pegasus | **0.9999** | Paper default — good all-rounder |
| Zephyr | **0.99995** | Faster cooling OK — dense HW guides search naturally |

---

### `cool_every` — temperature update interval
How many iteration steps between each temperature reduction. Default: **1000**.

Lower → temperature drops more frequently → faster cooling schedule.
Higher → temperature stays constant longer → each "epoch" explores more.

You rarely need to change this. Tuning `beta` achieves the same effect more cleanly.

---

### `pa_end` — final any-direction shift probability
PSSA's shift moves come in two flavours:
- **Guiding shift**: move a chain endpoint toward a node in the *same* guiding chain (conservative, preserves structure)
- **Any-direction shift**: move to *any* adjacent hardware node regardless of guiding pattern (exploratory)

`pa` linearly ramps from `pa0=0.095` (at t=0) to `pa_end` (at t=tmax).

| Topology | Default pa_end | Why |
|----------|---------------|-----|
| Chimera | **0.40** | Sparse — stay close to guiding structure to avoid thrashing |
| Pegasus | **0.487** | Paper default |
| Zephyr | **0.55** | Dense — more any-direction is safe, helps fill complex structure |

Higher pa_end → more exploration late in annealing → better for dense/irregular input graphs.
Lower pa_end → more conservative late behaviour → better for sparse/regular input graphs.

---

### `weighted` — degree-weighted shift direction
When `True`, shift proposals prefer moving chain endpoints *away* from high-degree input nodes and *toward* low-degree input nodes. This concentrates hardware resources where the input graph is most densely connected.

```
Direction probability ∝ chain_length(i) / degree(i)
```

| Use when... | weighted |
|-------------|----------|
| 3-regular, cubic graphs | `True` — they benefit most |
| Erdős-Rényi, random graphs | `True` helps slightly |
| Complete graphs | `False` — all degrees equal, weighting does nothing |
| Dense hub-and-spoke graphs | `True` — hubs get more HW resources |

Default: `False` (safer default for unknown graphs).

---

### `seed`
Random seed for reproducibility. `None` = non-deterministic.

---

## QEBench integration

After installing pssa_dwave, import it once before running your benchmark:

```python
import pssa_dwave.improved_pssa   # registers all PSSA variants

bench.run_full_benchmark(
    methods    = ["pssa", "pssa-weighted", "pssa-fast", "pssa-thorough", "minorminer"],
    topologies = ["chimera_4x4x4", "pegasus_2"],
    n_trials   = 5,
)
```

Registered algorithm names:

| Name | Description |
|------|-------------|
| `pssa` | Default — auto tmax, no weighting |
| `pssa-weighted` | Degree-weighted shifts — best for cubic/regular graphs |
| `pssa-fast` | tmax=50,000 — quick sweeps |
| `pssa-thorough` | tmax=2,000,000 — high quality |

---

## Running tests

```bash
pytest tests/ -v
```

All 40 tests run without dwave-networkx installed (uses a 6×6 grid as surrogate hardware).

---

## File structure

```
pssa_dwave/
├── pssa_dwave/
│   ├── __init__.py          # public API
│   ├── core.py              # hardware graphs, guiding pattern, schedule, PSSA Alg 1
│   ├── terminal_search.py   # Algorithm 2 — topology agnostic
│   ├── improved_pssa.py     # ImprovedPSSA class + QEBench registration
│   └── benchmark.py         # benchmark runner
├── tests/
│   └── test_pssa_dwave.py   # 40 unit tests
├── experiments/
│   └── run_dwave_benchmark.py
├── setup.py
└── README.md
```
