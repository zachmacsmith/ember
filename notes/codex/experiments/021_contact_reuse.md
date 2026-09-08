# Contact assignment reuse during coordinate packing

Design and self-critique recorded before implementation, 2026-09-08 UTC.

## Dependency and intended change

With an explicit carried y-rank, `field._stair_contacts` depends on source adjacency, participating vertex keys, their iteration order, and the carried y-order. It does not inspect coordinate values. `plane.readout` changes coordinates while preserving these dependencies. Its input `bk`, when supplied, already has the documented precondition of matching the current positions and y-order.

The bounded change is to let `plane.books` accept explicit contact assignments and pass the current `bk[0]` when rebuilding geometry after a coordinate pack. Consecutive readouts in one initialization, proposal, or bounded projection already pass their valid returned `bk` forward. A new proposal still constructs fresh contacts before packing; no state is cached across proposals, source graphs, or calls. Arm spans, packing intervals, occupancy penalties, and all objective arithmetic are recomputed as before.

## Self-critique and invariants

- Reusing contacts across a changed carried y-order, source adjacency, or participating vertex set would be incorrect. The change reuses only an existing readout-local assignment after a coordinate-only transformation; independent readouts without `bk` reconstruct contacts. No source-name, object-identity, or global cache is introduced.
- Contacts contain mutable lists. The consumers inspected in `field.py` read them without mutation. Reuse must preserve that contract; tests will check that original assignments remain unchanged. Returned geometry must still be rebuilt, rather than sharing obsolete arm bounds.
- Co-located vertices must retain the carried-rank ordering. Recomputing order from coordinates or using coordinate tie-breaking would alter the algorithm. Tests will include tied coordinates and a reversed carried y-order.
- `field._VERIFY_CONTACTS` independently recomputes contact assignments when enabled. Preserve that diagnostic and run trajectory comparisons with it enabled in tests; no field changes are required.
- Exact ordering, arithmetic, tie decisions, proposal evaluation counts, and random draws should be unchanged at fixed evaluation budgets. Under a wall deadline, faster execution can naturally allow more work; this task makes no identical-deadline-output claim.
- Experiment 014 measured contact assignment as only one fraction of layout time. Eliminating redundant calls need not produce a measurable total speedup. Report observed before/after cold and warm timings without inferring a gain from fewer calls alone.

## Prespecified verification

Freeze before/after source, changing only `plane.py` between snapshots. Use the independent native environment and the existing frozen complete-40, ER-80, and grid-64 development graph records at seed 0 and budgets 300/1000. Contact refinement stays disabled. Each version/configuration gets a fresh process and empty JIT cache, then one cold and one warm call: 24 calls total. Record proposal-sequence hashes, accepted objective traces, full embeddings, work counts, contact rebuild counts, and stage timings; original graph validation and MM/busclique import guards remain active. The diagnostic trace instrumentation is identical in both versions.

Dedicated regressions will compare contact reuse against forced recomputation across packing sequences, changed orders, independent sources, and complete small search trajectories. Existing plane tests remain part of the focused check.

## Implementation and focused checks

`plane.books` now accepts optional explicit `contacts`; absent that argument, it derives them as before. The post-pack rebuild in `readout` passes its valid `bk[0]`. Every arm span, packed interval, and geometry object is still rebuilt. `arrange`, the proposal generator, scoring, ordering, deadlines, and all field/native/contact modules are unchanged. There is no cross-proposal contact reuse: the first readout of every new proposal still derives fresh contacts.

The dedicated regression file is [test_plane_contact_reuse.py](../../../tests/algorithms/test_plane_contact_reuse.py). It exercises both three-axis packing sequences, both snap modes, and bounded/unbounded packing, comparing geometry against direct fresh `field.arm_books` evaluation. Tied coordinates use an explicitly reversed carried order. Separate calls after changing y-order or mutating source adjacency must derive fresh contacts. Prior input geometry and contact assignments remain unchanged. Three complete small searches compare all attempted proposals, accepted objective traces, positions, geometry, and non-time diagnostics against a forced-recomputation reference, with `field._VERIFY_CONTACTS=True` throughout.

Focused command:

```sh
.venv/bin/python -m pytest tests/algorithms/test_plane_contact_reuse.py tests/algorithms/test_plane.py -q
```

Result: **20 passed**, one existing dwave-networkx deprecation warning, 26.72 seconds. This includes 12 new regressions and the existing plane tests.

## Frozen before/after comparison

Artifacts are under [results/codex/021-contact-reuse](../../../results/codex/021-contact-reuse). `before/` and `after/` each contain six job definitions, their frozen package source, the diagnostic worker, inputs, results, and logs. The after snapshot was copied from before and only its `plane.py` replaced, preventing unrelated concurrent repository work from entering the comparison. All 43 source-map entries were verified in each snapshot; exactly one differs.

| Identity | SHA-256 |
| --- | --- |
| Before source map | `6da93d809f7871dfc542f727b90f80fd39cb9ef66f5ef84e5b0b78a07ee1de95` |
| After source map | `58bbf3c5769e9c7f42a3e04fc60e127432cb244423705d41c30285c3814c790d` |
| Before `plane.py` bytes | `deade3d95c67e68757efc60cf8d9bc6b60a51939ff4ae913ae9a8c0569e7c420` |
| After `plane.py` bytes | `6c2deb7c36d7282c9f60308e5b59bada04e5e83ee3d6bc7c8159acd18deee292` |
| Target record, ideal Zephyr Z12 | `38cde794d3c1461054a45b5a660d157737b019c19cb9a7b38e2027730e3d5938` |
| Result-file hash map | `1d3f29cd7364ee52859d9ffaa9f550ea5c43a1fd6cc93107f0a5c71231e2e6ba` |

The target has 4800 vertices and 45864 edges. The three source records are copied from experiment 009's graph files only; no saved embedding or MM result is an input. Per-input hashes are in both manifests.

The diagnostic worker is a frozen, instrumented derivative of `scripts/codex/profile_native.py`, saved as `profile_contact.py` inside the artifact directory and both snapshots. It sets the declared budgets to 300/1000, enables the existing accepted-trace output, counts contact rebuilds, and records an actual-proposal sequence hash. Each sequence entry records axis, old order, selected group, current-axis values, other-axis values, proposed order or rejection, and orientation choice. Sequence hashing is outside the measured solver interval; retaining entries and the accepted trace adds small identical instrumentation overhead to both versions. No cProfile call was added.

`run_pairs.py` interleaves before/after workers for each matched source/budget; seed 21001 shuffles pair order and version order within pairs. `execution_order.json` preserves that schedule. Every worker uses `/Users/dabh/ember/.venv/codex-native/bin/python`, an empty individual `NUMBA_CACHE_DIR`, `PYTHONHASHSEED=0`, and one-thread numerical-library limits. The entire source/target setup is repeated for both cold and warm calls; only process/JIT state is reused. Each solver call has a 30-second allowance, with an outer 105-second worker watchdog. Local execution completed through session 31860.

## Behavior and work

All 24 outputs independently validate against the original serialized graphs. Every source/budget has identical full embedding hashes, actual-proposal sequence hashes, accepted objective traces, best recorded state, and all non-time search/native diagnostics across before-cold, before-warm, after-cold, and after-warm. All worker return codes are zero. MM metadata is absent and prohibited import/module checks are empty in every worker.

Only redundant contact reconstruction changes. Counts below are per call and agree between cold and warm:

| Source | Budget | Actual evaluations | Axis readouts | Contact rebuilds before → after | Final qubits | ACL |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Complete 40 | 300 | 300 | 119 | 178 → 59 | 156 | 3.900000 |
| Complete 40 | 1000 | 515 | 119 | 178 → 59 | 156 | 3.900000 |
| ER 80 | 300 | 300 | 403 | 604 → 201 | 278 | 3.475000 |
| ER 80 | 1000 | 1000 | 699 | 1048 → 349 | 273 | 3.412500 |
| Grid 8×8 | 300 | 300 | 327 | 490 → 163 | 92 | 1.437500 |
| Grid 8×8 | 1000 | 1000 | 401 | 601 → 200 | 89 | 1.390625 |

The summed per-configuration contact rebuild count falls from 3099 to 1031, about two thirds. The search evaluation/readout/acceptance counts do not change. K40's 1000-budget run still stops at its recorded schedule fixpoint after 515 evaluations. This is behavior preservation on these trajectories, not a claim about global optimality or all possible inputs.

## Cold and warm measurements

Seconds below include native setup, layout, conversion, pruning, and internal validation; they also include the caller's source/target copies, as in experiment 014. Imports and independent final validation are measured outside this call. The warm-layout column isolates the layout stage.

| Source | Budget | Cold before → after | Warm before → after | Warm layout before → after |
| --- | ---: | ---: | ---: | ---: |
| Complete 40 | 300 | 1.8307 → 1.8361 | 0.7436 → 0.7312 | 0.5869 → 0.5755 |
| Complete 40 | 1000 | 2.2203 → 2.1930 | 1.0671 → 1.0512 | 0.9076 → 0.8923 |
| ER 80 | 300 | 2.3695 → 2.3607 | 1.2523 → 1.2289 | 1.0884 → 1.0626 |
| ER 80 | 1000 | 3.9542 → 4.1589 | 2.8354 → 2.8240 | 2.6773 → 2.6617 |
| Grid 8×8 | 300 | 1.9713 → 1.9626 | 0.8734 → 0.8534 | 0.7202 → 0.7043 |
| Grid 8×8 | 1000 | 2.9192 → 2.9425 | 1.8498 → 1.7961 | 1.7012 → 1.6495 |

Summed warm call time falls from 8.6215 to 8.4848 seconds, **1.59% lower**; summed warm layout time falls from 7.6817 to 7.5459 seconds, **1.77% lower**. All six warm pairs are lower, by 0.40–2.90%. Summed cold call time rises from 15.2652 to 15.4537 seconds, **1.23% higher**. These measurements establish a small observed warm difference and no observed aggregate cold improvement, rather than a reliable overall speedup.

The host is `dabhmbp`, Darwin 25.6.0 arm64, Python 3.10.19, NetworkX 3.4.2, NumPy 2.2.6, Numba 0.65.1, dwave-networkx 0.8.19, and SciPy 1.15.3. Worker-start one-minute load ranges from 22.99 to 37.22. This was an unreserved local host; the parent explicitly reported a concurrent local experiment-022 refinement diagnostic, session 98847, during this run. Interleaving helps but does not eliminate contention, cache effects, CPU-frequency variation, or first-call compilation differences. One cold/warm pair per configuration does not estimate timing variance or confidence intervals. No MM or cross-machine timing comparison is made.

## Result and limits

The implementation removes verified redundant computation with a small, explicit data dependency and preserves all checked search behavior. The observed warm benefit is modest, consistent with contact assignment being only part of the larger layout cost. It does not alter the search objective or improve embedding quality by itself.

`audit.json` stores the before/after snapshots, all result hashes, six comparison records, and validation counts. Hash/structure/metric checks passed for every output, and the source-map comparison confirms only `plane.py` changed. Fixed-budget behavior is the preservation target; a wall-limited run may perform more evaluations after any speed change. Broader correctness and larger inputs remain outside this bounded timing sample, while the existing staleness diagnostic and new differential tests remain available for future changes.
