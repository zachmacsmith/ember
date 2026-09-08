# Native search runtime diagnostic

Recorded 2026-09-08 UTC. This bounded diagnostic profiles one fixed independent constructor, with contact repair disabled. No algorithm source was changed, no MM embedding was read, and no result was selected between configurations for use as an algorithm output.

The main measured bottleneck is layout search: 85.76% of the aggregate warm call time across the nine cases. Reinsertion cost construction and repeated contact/packing reconstruction are the main warm profile targets. Conversion, completion, and pruning together account for 1.31%. A separate quality issue is visible: a better layout score does not necessarily produce fewer physical qubits.

## Protocol and provenance

Before running, the following three existing development inputs and all three budgets were declared to the parent agent: `complete_40`, `random_er_80_d8`, and `grid_8x8`; budgets 100, 300, and 1000. These provide dense, irregular sparse, and regular sparse examples. They are diagnostic examples, not a representative sample of Ember or a basis for family-dependent dispatch.

All nine configurations use `native_embed(construction="search", max_asks=budget, polish_passes=0, seed=0, timeout=30.0)`. Unspecified source defaults are `order_strategy="random"`, `packing_passes=2`, `sched_seed=None` (resolved to seed 0), `beam_width=4`, `max_groups=64`, `polish_group_sizes=(2,3,4)`, and `polish_expansions=500000`. Packing-only and contact-repair settings are inactive in these calls. Inputs come exclusively from the serialized graph and target files in experiment 009, copied byte-for-byte. None of its result embeddings are inputs to this script.

The new [profiling script](../../../scripts/codex/profile_native.py) froze current package source and itself before execution. Each configuration ran in a new sequential worker using the preserved interpreter path `/Users/dabh/ember/.venv/codex-native/bin/python`, not the resolved interpreter symlink. Each worker had a newly created empty `NUMBA_CACHE_DIR`, then made one cold and one warm call on fresh graph copies. The predeclared ER/300 case made one additional warm cProfile call. This is 19 calls in nine workers, with one algorithm seed. Worker order was shuffled once using seed 14001; `PYTHONHASHSEED=0` and four numerical-library thread limits were set to 1. A 105-second process watchdog bounded each worker in addition to the 30-second call budget. Every call finished well within its limit.

“Cold” here means the first embedding call after imports in a fresh process with an empty configured JIT cache. “Warm” means compiled code and interpreter state were reused, but target preprocessing and the entire search were repeated. Imports, input decoding, and graph materialization happen before either call; the separately measured call time includes the script's source and target copies. Thus this is not a comparison of fully cold process latency against a fully cached embedding service.

Reproduction commands, using a new output directory:

```sh
.venv/bin/python scripts/codex/profile_native.py prepare results/codex/014-native-profile-repeat
.venv/bin/python scripts/codex/profile_native.py run results/codex/014-native-profile-repeat
```

The prepare command deliberately refuses to overwrite an existing directory. Reproducing the exact recorded implementation requires the frozen source, since the working tree can subsequently change.

Artifacts are under [results/codex/014-native-profile](../../../results/codex/014-native-profile): the manifest contains every source-file hash, exact job configuration and order; result JSON contains complete embeddings, diagnostics, stage timings, interpreter details, and dependency guards; `profiles/747e774c6d90bd8bd0e74dd6.prof` contains the warm ER/300 profile. The result directory is ignored by ordinary repository searches and is not committed automatically.

| Provenance item | SHA-256 or value |
| --- | --- |
| Git HEAD at preparation; working source additionally snapshotted | `44def007c833d18eba0403b9ed9679f877947a6e` |
| Canonical source-file hash map, 42 files | `9c1740f55c6c6a8efe5506264961dacca1b219b4e41fa118af2b4d90ab6af7e4` |
| Manifest file bytes | `71948372b540094fe3ca0f2e0752c0a8a9896a3fe3beacec49922b87fd11b6f0` |
| `native.py` bytes | `43d83368b28e1953d92a88e2cbe02720dccaf25ee9a4faac7db9b4e92649f9a3` |
| `plane.py` bytes | `deade3d95c67e68757efc60cf8d9bc6b60a51939ff4ae913ae9a8c0569e7c420` |
| `field.py` bytes | `1778a3af4670c34a8acdc51ec7be000195bb208f0213399203e4982c498bb18c` |
| Profiling script bytes | `62515ec34d946b0cc401eac342673bee65c1929ba32deceb1002d52bbe9bf903` |
| cProfile artifact bytes | `de6f5c10c422863cf033b69899e9dcb756cff1274d3463e41b26d738d620bb18` |
| Target record: ideal Zephyr Z12, 4800 vertices, 45864 edges | `38cde794d3c1461054a45b5a660d157737b019c19cb9a7b38e2027730e3d5938` |
| Complete graph: 40 vertices, 780 edges | `7dfc010d7e015339dede4f9b256578e11a2c7335b63a3a5d42c43bd733b73656` |
| ER graph: 80 vertices, 296 edges | `66cea797a499f13355c70a51fcd4301d0cd3ef4440042bf12b1ca6dfd6666898` |
| Grid: 64 vertices, 112 edges | `224635dde0d7de48088d3b1c780105e764811c6b43175f454d60f1d55e9da10d` |

Record and source-map digests use sorted-key compact JSON. File-byte digests are explicitly labeled above.

The host was `dabhmbp`, Darwin 25.6.0 arm64, Python 3.10.19, NetworkX 3.4.2, NumPy 2.2.6, Numba 0.65.1, dwave-networkx 0.8.19, and SciPy 1.15.3. MM was absent from installed distribution metadata. Worker-start one-minute host load ranged from 34.80 to 40.42; the host was not reserved. Warm process CPU/call wall ratios were 0.979–0.996. These observations do not make the measurements comparable to unmeasured cluster machines or MM timings.

## Validity and independence checks

All nine workers completed with return code zero. All 19 embeddings satisfy exact source coverage, nonempty and internally duplicate-free chains, target membership, connectedness, disjointness, and every source edge's contact requirement. The script validates each result independently of the native wrapper. A second read-only audit reconstructed graph adjacency from the serialized records and checked all embeddings and quality metrics again. The complete frozen source map, all nine job digests, all copied inputs, and recorded configurations matched their manifest hashes.

Every cold/warm pair has the same embedding hash; the extra profiled call matches its unprofiled pair too. This supports deterministic output under the measured cache states; it does not estimate variance over algorithm seeds. Installed-package checks, runtime import blockers, and post-call loaded-module checks reported no MM or busclique dependency attempt or loaded module in any worker. The entire package snapshot includes unused comparator adapter source files for provenance; their presence is distinct from loading or invoking them. These runtime checks complement the earlier source audit and do not themselves prove the absence of arbitrarily renamed copied code.

## Budget, work, and physical quality

Here `asks` is the existing diagnostic's count of reinsertion evaluations, including evaluations returning no changed order. It is not a count of completed embeddings or of successful proposals. `readouts` counts axis packing calls. The layout score is the recorded arm-span score; its accompanying capacity-overload penalty is zero in every row. “Constructed” is physical qubits after conversion/completion and before pruning; final qubits include pruning. Cold, warm, and profiled quality agree wherever repeated.

| Input | Budget | Evaluations | Readouts | Layout score | Constructed qubits | Final qubits | ACL | Maximum chain |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Complete 40 | 100 | 100 | 103 | 317 | 159 | 155 | 3.875 | 5 |
| Complete 40 | 300 | 300 | 119 | 316 | 160 | 156 | 3.900 | 5 |
| Complete 40 | 1000 | 515 | 119 | 316 | 160 | 156 | 3.900 | 5 |
| ER 80 | 100 | 100 | 185 | 691 | 361 | 307 | 3.8375 | 7 |
| ER 80 | 300 | 300 | 403 | 642 | 332 | 278 | 3.4750 | 6 |
| ER 80 | 1000 | 1000 | 699 | 614 | 323 | 273 | 3.4125 | 7 |
| Grid 8×8 | 100 | 100 | 171 | 294 | 173 | 121 | 1.890625 | 4 |
| Grid 8×8 | 300 | 300 | 327 | 229 | 147 | 92 | 1.437500 | 3 |
| Grid 8×8 | 1000 | 1000 | 401 | 221 | 145 | 89 | 1.390625 | 4 |

The clique is a concrete counterexample to assuming a better internal score means lower physical ACL: score 317→316 increases final qubits 155→156. The search saves its best `(overload, arm-span)` state and converts that state only at the end; it does not optimize actual post-pruning qubits. This discrepancy is a separate algorithm-quality question, not justification for selecting a smaller budget on cliques. A generic improvement should address the objective's relationship to physical chains, with its own ablation.

For the clique, the best recorded score occurs at evaluation 112 for both larger budgets. Between budgets 300 and 1000, 215 additional reinsertion evaluations produce no additional readout and no changed output. The 1000-budget run reports `fixpoint` at 515 evaluations; this is exhaustion under the implemented neighborhood/schedule, not a global embedding optimum. All other rows stop at the evaluation limit. The grid improves by 29 qubits from 100→300 and by 3 from 300→1000; ER improves by 29 and then 5. Maximum chain length increases again in both sparse examples at 1000. These three examples support measuring physical outcomes explicitly, but do not establish an optimal global budget.

## Stage timings

All values below are seconds, rounded after measurement. “Target setup” is adjacency + Zephyr coordinates + `TileGrid`; “convert/complete” combines those two stages. “Other” includes the caller's fresh graph copies, source relabeling, adapter work, and instrumentation overhead. Internal validation is timed separately; the external audit is outside solver time. The process wall column includes imports, input loading, both calls, and validation; the marked worker additionally includes cProfile. It is not a per-embedding latency.

| Input | Budget | Cold call | Warm call | Warm target setup | Warm search | Warm convert/complete | Warm prune | Warm internal validation | Warm other | Worker process |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Complete 40 | 100 | 1.6210 | 0.4465 | 0.0728 | 0.2867 | 0.0104 | 0.0022 | 0.0046 | 0.0698 | 2.9738 |
| Complete 40 | 300 | 2.0907 | 0.7657 | 0.0745 | 0.6041 | 0.0103 | 0.0021 | 0.0046 | 0.0700 | 3.7853 |
| Complete 40 | 1000 | 2.3012 | 1.0870 | 0.0760 | 0.9246 | 0.0103 | 0.0021 | 0.0046 | 0.0695 | 4.3216 |
| ER 80 | 100 | 1.8131 | 0.6176 | 0.0740 | 0.4469 | 0.0169 | 0.0091 | 0.0028 | 0.0678 | 3.3332 |
| ER 80 | 300 | 2.5940 | 1.2716 | 0.0727 | 1.1058 | 0.0171 | 0.0050 | 0.0026 | 0.0683 | 6.5627* |
| ER 80 | 1000 | 4.5450 | 2.9531 | 0.0745 | 2.7857 | 0.0148 | 0.0047 | 0.0029 | 0.0705 | 9.1231 |
| Grid 8×8 | 100 | 1.6518 | 0.4542 | 0.0728 | 0.3018 | 0.0107 | 0.0012 | 0.0009 | 0.0667 | 2.9997 |
| Grid 8×8 | 300 | 2.0768 | 0.9022 | 0.0736 | 0.7225 | 0.0095 | 0.0007 | 0.0010 | 0.0949 | 3.8738 |
| Grid 8×8 | 1000 | 3.0278 | 1.8231 | 0.0732 | 1.6728 | 0.0079 | 0.0006 | 0.0008 | 0.0679 | 5.7366 |

The 18 unprofiled calls used 32.04 seconds of measured call wall in total. All 19 calls used 33.17 process CPU seconds. Aggregate warm stage shares are: search 85.76%, target grid 4.81%, target coordinates 1.45%, target adjacency 0.18%, conversion 0.90%, completion 0.15%, pruning 0.27%, internal validation 0.24%, and other work 6.26%. These are shares summed over these calls, not averages over graph classes.

Search accounts for 20.25 of 21.72 total cold seconds and 8.85 of 10.32 total warm seconds. Its cold-minus-warm difference ranges from 1.172 to 1.594 seconds, median 1.204 seconds. Empty-cache JIT work is a plausible major cause, but this difference also includes first-use effects and host variation; compilation itself was not separately instrumented. Import wall has median 0.496 seconds (range 0.482–1.081); input loading/materialization has median 0.130 seconds (range 0.125–0.137). Those costs must be included in any eventual process-level comparison.

## Warm hotspot profile

The preselected ER/300 cProfile call took 1.778 seconds versus 1.272 unprofiled in the same worker, about 40% overhead. Its output and work counts are identical. The table reports profiled cumulative time, which includes descendants and therefore must not be added across overlapping rows. Profiling disproportionately affects Python-call-heavy code, so these are localization evidence rather than predicted savings.

| Function in frozen source | Calls | Own seconds | Cumulative seconds | Interpretation |
| --- | ---: | ---: | ---: | --- |
| `plane.arrange` | 1 | 0.0238 | 1.5047 | Complete layout search |
| `field.align_reinsert` | 300 | 0.1508 | 0.7444 | Reinsertion preparation and both orientations |
| `field.align_reinsert.<locals>._arm` | 600 | 0.2284 | 0.4780 | Transition costs, crossing counts, recurrence/backtracking |
| `field..._rect` | 100666 | 0.0999 | 0.1348 | Repeated rectangle updates within `_arm` |
| `plane.readout` | 403 | 0.0061 | 0.5810 | Repeated packing/reconstruction |
| `plane.books` | 604 | 0.0014 | 0.3031 | Contact assignment and arm geometry |
| `field.arm_books` | 604 | 0.0694 | 0.2312 | Rebuilds arm geometry |
| `field._stair_contacts` | 604 | 0.0574 | 0.0705 | Rebuilds directional contact ownership |
| `plane.pack_axis` | 403 | 0.0083 | 0.2600 | Prepares and applies axis packing |
| `plane._line_profiles` | 403 | 0.0302 | 0.0902 | Recreates capacity-profile extensions |
| `plane.judge` | 201 | 0.0371 | 0.1429 | Full overload and arm-span scoring |
| NetworkX `Graph.copy` | 2 | <0.0001 | 0.1268 | Diagnostic caller's graph copies |
| `field._pack_dp` | 403 | 0.0080 | 0.0081 | Already compiled packing recurrence |

Other call volume includes 109433 `numpy.array` calls and 48300 ndarray `argsort` calls. The already compiled packing recurrence accounts for little of this warm run; compilation of its first use should not be confused with its steady-state cost. The reinsertion `_arm` routine remains a different, Python-heavy calculation.

## Focused improvement opportunities

These are source-supported optimization hypotheses, not implemented changes or measured speedups. They should apply uniformly to all source graphs.

1. **Reduce reinsertion preparation and Python inner-loop overhead.** `align_reinsert` repeatedly builds directed adjacency slot arrays, partitions/sorts neighbor indices, constructs transition arrays, and performs rectangle updates. A fixed source adjacency representation and compiled array kernels could retain the same candidate order and recurrence while reducing allocation and Python calls. Cluster membership and carried order change, so their derived arrays cannot be cached under source identity alone. Preserve iteration order, exact tie behavior, and arithmetic semantics; compare proposal traces and final hashes at equal budgets, not only final ACL.
2. **Reuse contact assignments when the carried y-order is unchanged.** With explicit ranks, `_stair_contacts` depends on source adjacency, participating vertices, and y-order, not coordinate values. `readout` rebuilds it around a coordinate-only pack, and both axis packs of a proposal use the same carried y-order. Contact reuse across those operations is a concrete opportunity. Arm spans and occupancies still depend on coordinates and must be updated. Cache invalidation on a y-order change is essential.
3. **Reuse immutable capacity data without confusing it with occupancy.** `profiles(grid)` already caches its base arrays. `_line_profiles` still scans and extends them on every packing call. Cache immutable line metadata or extension templates by all determining dimensions, including axis, stride, target capacities, required extent, and bounded/unbounded mode. Do not reuse mutable array state or suppress off-target capacity penalties.
4. **Consider incremental scoring only after simpler reuse is verified.** Full overload and span recomputation costs 0.143 profiled seconds here. Changed chains can affect multiple lines after repacking; an incremental implementation must account for every changed interval and contact. Compare its score against full recomputation through complete trajectories before relying on it. It has a smaller observed ceiling than the reinsertion and reconstruction work.
5. **Separate service setup from algorithm work transparently.** Immutable target geometry and adjacency could be reused when the exact target topology and relevant attributes are identical. Source-name or family-only keys would be incorrect, especially for defective targets. The diagnostic's caller graph copies also cost time, but they preserve original validation inputs; removing that protection merely to improve timing is not an acceptable optimization. Any explicit immutable preprocessing API should account for its cold cost and reuse policy in both candidate and comparator measurements.

Conversion, completion, pruning, and validation are low-priority speed targets on these inputs. Preserve validation. Reducing work budgets or changing stopping rules would change the search, so it is a separate quality/runtime experiment rather than a behavior-preserving optimization. The nonmonotonic physical result at larger budgets also rules out treating the proxy as proof of monotonic ACL improvement.

## Limits and checks

This is one seed on three development graphs, one local machine, one cold/warm pair per configuration, and one profiled case. It estimates neither seed-to-seed ACL variance nor timing distributions, class-wide quality, defect tolerance, scaling to larger sources, or performance against MM. Cold/warm repeats test cache-state consistency, not independent stochastic trials. Wall-budget cancellation was not exercised because every call was short. The profiling wrappers add a small unquantified measurement overhead.

The profiling script passed syntax compilation and `git diff --check`; the complete hash/structure/metric audit passed as described above. No algorithm source edits or further large runs were performed for this diagnostic.
