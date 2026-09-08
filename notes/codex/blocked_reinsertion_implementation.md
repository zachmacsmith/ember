# A050 blocked-only reinsertion implementation

Implemented the fixed policy in [050's pre-code hypothesis](experiments/050_blocked_reinsertion_hypothesis.md). The separate method `native-reduced-core-repair` calls `factored/reduced_reinsertion_construction.py:reduced_core_embed` with `{}` configuration. Frozen 049's module and native implementation are unchanged. One filled-core construction is followed by reverse expansion; only an ordinary insertion returning no candidate invokes local repair.

The new `blocked_reinsertion.py` loads exact B004 primitive bytes (`f29cdef9…`) without calling B004's constructor or broader repair selector. It uses the live requirement graph, engine and absolute deadline. At most two critical port competitors join the at-most-three required neighbors; at most 15 one/two-owner blocks are tried in the predeclared order. Each starts from the same entry, freezes every other chain, and returns the first complete reconstruction preserving original contact, connectivity, ownership and future-port guards. There is no relaxed guard or alternative complete embedding selection.

The live allowance is clipped to one million scans per blocked step, five million cumulative repair scans, and the unchanged 20 million global scans. Selection and all failed rebuilds use that allowance. Copying, bitset operations and some existing primitive loops are deadline-bounded rather than represented one-for-one by scans; scan counts are algorithmic work counters, not a complete machine-operation model. Repair wall/scans are **subtotals of expansion/global cost**. `ordinary_insertion_queries` counts outer attempts; inherited `insertion_queries` also counts private rebuild calls. Setup is not repeated within repair.

After a repair, extra removed-fill cleanup touches only selected owners. Its actual Q reduction is saved per block and in the returned repair record; global `staged_pruned_sites` remains a separate counter that includes discarded trials. A certified proposal's `committed` flag remains false until the wrapper's final clock check and joint chain/requirement adoption. An interrupted proposal retains the previous partial minor and its previous requirement graph. No successful insertion invokes repair or changes 049's cleanup.

## Fixed local reach results

All three prescribed cases succeeded on the first tested block; original active requirements, frozen ownership and all future frontiers were checked independently. These are local supplied-state results, not completed-constructor comparisons.

| Entry | Selected owner | Entry → proposed Q | Repair scans | Diagnostic wall including setup |
|---|---:|---:|---:|---:|
| P4 occupied endpoint | 0 | 2 → 3 | 40 | 0.000334 s |
| Saved 049 cycle `ember_1829` | 68 | 118 → 120 | 80,381 | 0.178624 s |
| Saved 049 wheel `ember_2429` | 12 | 111 → 116 | 148,083 | 0.221509 s |

Evidence is under `results/codex/a050-blocked-reinsertion/repair_reach001`. The first script's `source_state_unchanged` field compared two post-call samples and is not an independent nonmutation check. This limitation is preserved. Additive `frozen_R_validation.json` instead validates all three saved outputs against pre-execution R; the subsequent narrow unit check snapshots R before calling repair and verifies exact equality afterward. The reach-tested helper snapshot is retained; final helper changes add committed/cleanup diagnostics only.

## Focused checks and limitations

`checks001` passed eight groups in 0.039 s under the isolated native interpreter with zero prohibited imports: true entry/R nonmutation, original-edge P4 validity, query/cumulative/global clipping, interruption rollback, exact fill cleanup count with a frozen endpoint, unchanged 049 no-block choices/work on three tiny inputs, one wrapper repair commit, and a certified late repair retaining the preceding filled R. Both new standalone adapter checks passed in 0.48 s (A050 and the independently owned B011 registry). No failed correctness run occurred; earlier explanatory guard-relax observations remain explicitly inadmissible, with every artifact preserved.

Reproduce the narrow checks with a **new** output directory:

```sh
.venv/codex-native/bin/python -I -B results/codex/a050-blocked-reinsertion/run_checks.py results/codex/a050-blocked-reinsertion/checks-new
```

The fixed neighborhood can miss other competing owners or require a different insertion order. Successful repairs may increase Q or impair later expansion. The cycle/wheel reach result does not resolve 049's successful-output quality regressions and is not a novelty claim. Full-pipeline testing and remote lifecycle belong to the parent task.
