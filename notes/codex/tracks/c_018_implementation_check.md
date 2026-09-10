# C018 isolated implementation and first focused check

2026-09-10 UTC. The [approved design](c_018_contact_relaxed_territories_design.md) and [before-code conventions](c_018_implementation_contract.md) now have an isolated implementation. Root owns registry changes, final screen freeze and launch. No C017 artifact, shared validator, existing constructor or other-track source changed. No development constructor was called.

`territory_relocation.py` contains the one-state constructor and root-domain ablation; `territory_relocation_kernels.py` contains five compiled array kernels. Both arms call the same driver and differ only in eligible roots. The unchanged pinned helper supplies normalization, singleton initialization and structural validation, never its constructor/search. Numerical import and cold JIT are inside the constructor clock, with compiler caching disabled. The only active budget is wall time; 256-dequeue BFS batches preserve the entire frontier and only provide clock observation points.

Implementation self-critique before the check: complete owner release removes the old local root restriction, but it does not optimize the root jointly with the final tree. The singleton-distance proxy can favor a location with poor free access, and canonical greedy paths can miss useful trees. A real positive-energy proposal reaches the annealed acceptance rule; old-state rollback is not a competing proposal. Distances, completed free-access failures, actual single-path energy changes, accepted/rejected/interrupted visits and first-valid/strict-Q events remain separate diagnostics. The complete screen must decide whether broader root movement helps validity and occupied length at useful cost. Tiny fixtures cannot establish that.

The first frozen check passed all four cases in one focused group: two tiny public constructor calls, zero development calls, zero errors, zero failed assertions and no prohibited dependency attempts. Test wall time was **2.574 s**, CPU **1.968 s**; recorded wrapper elapsed **2.960 s**. These timings describe the check, not candidate performance. Original independent-oracle validation covered complete original minors and, where explicitly marked partial, the realized contact subgraph with all owners retained; separate assertions recounted every original-edge contact.

The cases establish the specific new-risk boundaries:

- Nonadjacent owner relocation produces a completed uphill proposal (ΔE = +1), reaches stochastic acceptance, and preserves missing-contact accounting. Restricting roots to the old territory leaves the same fixture obstructed; its unchanged geometry does not invalidate the cache.
- Three incident contacts share a branching tree with four actual added sites instead of six independently counted path sites. Exact energy change is −8. Only the changed owner's cached geometry becomes stale, and refreshing it preserves all other distance rows.
- Interrupting private regrowth or the pre-publication check preserves the prior state. Interrupting immediately after publication retains coherent ownership, contacts and a committed record, without certifying a late incumbent. Interruption during certification preserves the previous valid incumbent and event history.
- A tiny public constructor returns an independently valid ACL-1 result. An injected final-validation boundary returns `TIMEOUT` with an empty credited mapping despite a previously certified first-valid event. This is an injected boundary test, not a measured wall overrun.

No mechanism or parameter changed after the first check freeze. Syntax compilation also passed. All eleven frozen source/helper/environment bindings were verified unchanged afterward. The existing deadline exception types are caught faithfully; the reused helper's exported work-capped meter is never instantiated.

Review bindings:

| Artifact | SHA-256 |
| --- | --- |
| Main production module | `cf9d4382155915a5f4cec8980949c46b40dff4282cd527f4dd0cd558895dc102` |
| Array kernels | `be490cb57a59dfb2044aea2733dc0b3d2a91301e8d55dbbf03e7dd6a2c9f0e35` |
| Focused test | `b6fec07757f0fe4dd21daa6ee4cae9265bf59fce03486b2c9ddb358488a2d794` |
| `results/codex/c018-territories/check_freeze001.json` | `415f707cf60045b354023b1e46e6d8fc60201fca2704bf5c3de351bce9c9a129` |
| `check001/output/summary.json` | `35c90052b2c8b01fdf455f0a300fc115202f8aed5d1686b386756291083df18b` |
| `check001/status.json` | `50a37d1ecad66f223815bf53410016e156b96a9d7b8dd92442f9ba4409060590` |

The local isolated environment reports NumPy 2.2.6, Numba 0.65.1, llvmlite 0.47.0 and NetworkX 3.4.2. The next decision is the already proposed five-input, two-seed complete screen with full roots, old-territory roots, retained A061 and MM on one host. No performance promotion follows from this check.
