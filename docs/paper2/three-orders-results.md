# Three-order native build: retained results

First-build evaluation, 2026-09-14. The implementation follows the
[design contract](three-orders.md). It is standalone, fast at the inherited
work budgets, and **not yet a general quality improvement** over the recorded
implementation or stock MinorMiner. No source-graph-specific changes were made
in response to these results.

## Protocol

The board has ten fixed graphs on intact Z12, seeds 0/1/2, paired by graph and
seed. `native_board.py` reuses the existing board's graph loaders and budgets.
The reference is the unmodified pre-change `factored` tree at
`810745629ee5f711ee8b2d8157c648cf6b7ef548`, extracted before implementation;
its source package was imported in separate workers. Stock MinorMiner is
0.2.22. All embeddings were independently validated against actual couplers.

- **Native/work**: inherited per-cell ask budgets (8,000–15,000) and a 60-second
  safety cap. A sweep with no strict proposal winner can stop earlier.
- **Native/wall**: the identical algorithm, no ask limit, 60-second cap.
- **Reference**: inherited ask budgets, 60-second cap, explicit `tail="none"`.
  The old implementation retains its historical mechanisms; observed MM calls
  were zero in every reference board case.
- **MM**: stock `find_embedding`, paired seed, requested timeout 60 seconds.
  Actual elapsed time is recorded; several calls exceeded that request.

Each arm used three workers, with startup/warmup excluded from case timings.
Arms overlapped on a shared 128-logical-CPU machine with load averages roughly
72–99. These are real elapsed measurements under that load, not isolated CPU
benchmarks. Ask counts are implementation-specific units, not equal amounts of
work across engines. Every native benchmark made MM calls raise if attempted.

## Board: quality

Each successful entry is **median physical qubits / median average chain
length** across its three seeds. Failures are excluded from these medians and
shown explicitly; medians must not be read as paired wins. Per-seed maximum
chain lengths, reservations and all diagnostics are in the linked JSON files.

| Graph | Native/work Q / ACL | Native/wall Q / ACL | Reference Q / ACL | MM Q / ACL |
|---|---:|---:|---:|---:|
| K100 | 928 / 9.280 | 928 / 9.280 | 726 / 7.260 | 1038 / 10.380 |
| K140 | 1663 / 11.879 | 1627 / 11.621 | 1368 / 9.771 | 2796.5 / 19.975 (2/3) |
| ER100_d10 | 545 / 5.450 | 511 / 5.110 | 462 / 4.620 | 500 / 5.000 |
| turan_n162 | 972 / 6.000 | 972 / 6.000 | 1180 / 7.284 | 1869 / 11.537 |
| spin_glass_n163 | 2029 / 12.448 | 2004 / 12.294 | 1770 / 10.859 | 3090 / 18.957 |
| regular_n316 | 1682 / 5.323 | 1324 / 4.190 | 1741 / 5.509 | 1063 / 3.364 |
| ws_n486 | failure (0/3) | failure (0/3) | failure (0/3) | 1542 / 3.173 |
| grid_200 | 419 / 2.095 | 334 / 1.670 | 321 / 1.605 | 210 / 1.050 |
| honeycomb_200 | 440 / 2.200 | 358 / 1.790 | 372 / 1.860 | 228 / 1.140 |
| king_graph_196 | 591 / 3.015 | 531 / 2.709 | 493 / 2.515 | 367 / 1.872 |

## Board: elapsed time and work

Each entry is **median elapsed seconds / median asks actually completed**.
MM has no comparable interleaver ask counter. The reference did not return
that counter on its failed WS cases. Times include failed cases.

| Graph | Native/work s / asks | Native/wall s / asks | Reference s / asks | MM s |
|---|---:|---:|---:|---:|
| K100 | 1.043 / 5,400 | 1.130 / 5,400 | 11.286 / 1,555 | 60.880 |
| K140 | 3.927 / 12,000 | 11.215 / 31,407 | 19.506 / 2,102 | 64.455 |
| ER100_d10 | 0.611 / 8,000 | 3.593 / 55,080 | 14.129 / 3,147 | 2.654 |
| turan_n162 | 2.989 / 15,000 | 60.020 / 319,947 | 60.065 / 8,778 | 60.129 |
| spin_glass_n163 | 4.127 / 12,000 | 21.574 / 66,045 | 26.153 / 3,559 | 60.677 |
| regular_n316 | 1.535 / 10,000 | 60.015 / 534,503 | 60.082 / 6,310 | 3.643 |
| ws_n486 | 3.055 / 15,000 | 60.002 / 344,217 | 60.128 / unreported | 4.518 |
| grid_200 | 0.672 / 8,000 | 60.010 / 888,011 | 35.375 / 8,000 | 0.369 |
| honeycomb_200 | 0.626 / 8,000 | 60.006 / 932,963 | 37.712 / 8,000 | 0.412 |
| king_graph_196 | 0.844 / 8,000 | 60.009 / 635,698 | 42.642 / 8,000 | 1.402 |

Across all 30 paired cases:

- `native`: 27/30 valid; median elapsed 1.465 s; 0 MM calls.
- `native_wall`: 27/30 valid; median elapsed 60.006 s; 0 MM calls.
- `baseline`: 27/30 valid; median elapsed 36.693 s; 0 MM calls.
- `mm`: 29/30 valid; median elapsed 4.406 s; 30 MM calls.

Paired quality comparisons, restricted to cases where both methods succeeded:

- `native` versus `baseline`: 5 shorter, 0 tied, 22 longer; 27 common successes.
- `native` versus `mm`: 11 shorter, 0 tied, 15 longer; 26 common successes.
- `native_wall` versus `baseline`: 9 shorter, 0 tied, 18 longer; 27 common successes.
- `native_wall` versus `mm`: 11 shorter, 0 tied, 15 longer; 26 common successes.

The broad conclusions are limited but useful. Native search beats MM's chain
length on the measured dense clique, biclique and spin-glass cases, while the
reference still packs cliques and spin glass more tightly. The biclique is
reliably six qubits per variable, including all ten fingerprint starts.
The 60-second reference board arm stops before recovering its previously
recorded biclique result of six; that is a budget effect, not a new lower bound.

Longer native search improves regular, grid and honeycomb layouts. It still
fails all three WS seeds after 60 seconds and remains behind MM on the sparse
board. K100 reaches a proposal fixpoint early and gains nothing from the
larger budget. These observations do not prove a representational ceiling:
a fixed-slot fixpoint is conditional on the current decoded coordinates.
They do show that simply spending more asks at this cadence does not resolve
the main quality gaps. Future work should examine the interaction of contact
roles, frozen slots and canonical axis packing, with abutment still deferred.

## Fingerprints

The original six fingerprint cells were run with their existing work budgets,
including all ten biclique seeds. All **15/15** returned independently valid
native embeddings with zero MM calls. The values below are observations,
not new hardcoded acceptance targets.

| Cell | Seeds | Median Q | Median ACL | Median maximum chain | Median seconds | Median asks |
|---|---:|---:|---:|---:|---:|---:|
| K8 | 1 | 14 | 1.750 | 2 | 0.007 | 78 |
| K10 | 1 | 21 | 2.100 | 3 | 0.016 | 594 |
| path60 | 1 | 65 | 1.083 | 2 | 0.165 | 3,000 |
| K100 | 1 | 940 | 9.400 | 12 | 0.819 | 4,320 |
| turan_n162 | 10 | 972 | 6.000 | 6 | 3.079 | 15,000 |
| grid_200 | 1 | 465 | 2.325 | 7 | 0.839 | 8,000 |

K10's old recorded 1.8 and K100's 7.26 are not preserved (now 2.1 and 9.4 for
these fingerprint seeds). The implementation has not silently redefined these
regressions as improvements. The expanded three-order state and individually
exact kernels do not imply that their composition finds the old optimum.

## Kernel and compilation measurements

The native/work board spends a median **0.028 s** in conditional packing and
**1.098 s** in interleaving per case. Its maximum total conditional-packing time
is **0.053 s**. Decoder construction, book rebuilding and certification are
additional work; the artifact reports packing time separately from elapsed
case time. The retained 486-vertex conditional-packing probe verifies both
capacity directions and shared costs. Warm axis packs in that probe take
roughly **0.001 s** after exact domain propagation. This is an axis-pack
measurement, not an embedding time or a linear-runtime claim.

Cold compilation is materially different. Two fresh-cache fingerprint workers
spent **20.40 and 20.62 s** in combined import/compilation/warmup under concurrent
load. A separate fresh-process event-timed probe measured **13.423 s inside
Numba compilation**, **0.424 s importing**, and **13.759 s** for the first
Path8/Z3 embedding call. The same call then took **0.0071 s**, with no compilation
events. Nested compilation is not double-counted. This small warmup covers the
signatures exercised by the board; it is not a guarantee against future
compilation for other input dtypes. Cached worker startup in the native/work
board was 1.12–1.28 s and is also excluded from case timings.

## Correctness checks

The broad command below passed **574 tests** (one dependency deprecation
warning). Two subsequently added deterministic deadline regressions also pass
with the nine existing plane tests: **11 passed** in that focused run.
Production code was unchanged after the broad run and benchmark hash.

```bash
.venv/bin/python -m pytest tests/algorithms tests/test_registry.py tests/test_embedding_backend.py -q
.venv/bin/python -m pytest tests/algorithms/test_plane.py -q
```

Coverage includes every four-vertex source graph for all three interleavers,
independent exhaustive legal merges/monotone packings, tied slots, disappearing
bars, both capacity directions, shared brick boundaries, axis symmetry,
int64 flow and overflow guards. Physical tests cover mixed and single bars,
disconnected sources, isolates and coordinate labels on actual Zephyr couplers.
Standalone tests make routing calls raise. Controlled sweep/deadline tests prove
that packing stays between sweeps, worse decoded proposals are adopted, and an
earlier valid bookmark survives interrupted work.

## Artifacts and reproduction

- [Benchmark harness](data/native_board.py)
- [Native work-budget board](data/three_order_board_native.json)
- [Native wall-budget board](data/three_order_board_native_wall.json)
- [Pre-change reference board](data/three_order_board_baseline.json)
- [Stock MinorMiner board](data/three_order_board_mm.json)
- [Native fingerprints](data/three_order_fingerprint_native.json)
- [Conditional packing probe](data/three_order_packing_probe.py) and [measurements](data/three_order_packing_probe.json)
- [Compilation probe](data/native_compile_probe.py) and [measurements](data/three_order_compilation.json)

All native board and fingerprint artifacts contain the package SHA256
`6a7980d06f5f4345e753657d4277d0bc1f81d6ba32c0fd1991da370d351ce975`.
The reference package SHA256 is
`6b7878b3d97c133c151656afabdd3178f50f006f5bcb186b9a60a7fab51b4dd4`.
Graph specifications and budget definitions are imported from the existing
`plane_fingerprint.py` and `rewrite_board.py` harnesses; no graph-family choice
is made by the embedder. JSON files contain per-case elapsed time, work,
success, physical qubits, ACL, maximum chain, reservations, active bars,
packing/interleaving time, MM calls and startup/source provenance.

```bash
.venv/bin/python docs/paper2/data/native_board.py --suite fingerprint --engine native --workers 2 --cold-cache
.venv/bin/python docs/paper2/data/native_board.py --engine native --workers 3
.venv/bin/python docs/paper2/data/native_board.py --engine native --workers 3 --wall-only --output docs/paper2/data/three_order_board_native_wall.json
.venv/bin/python docs/paper2/data/native_board.py --engine baseline --workers 3 --baseline-src /tmp/ember-three-order-baseline-8107456/packages/ember-qc/src
.venv/bin/python docs/paper2/data/native_board.py --engine mm --workers 3
.venv/bin/python docs/paper2/data/native_compile_probe.py
```

The temporary baseline path is the extracted reference commit, not another
live branch. Recreate that checkout from the recorded commit if the temporary
snapshot is no longer available. A finished board artifact has `load_at_end`;
all linked board/fingerprint artifacts are complete.
