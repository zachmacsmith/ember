# C015 implementation and tiny controls

2026-09-09. **Ready for the eight-input Z12 constructor screen.** The new first-admissible constrained constructor passes four focused risk groups and both authorized complete Z2 controls on the first attempts. Both controls retain C014's certified optimal Q. No source changes were needed after testing, and no Z12 constructor call was made by this preparation.

The [before-code contract](c_015_constructor_contract.md) was frozen before implementation. Root reviewed the new source before checks. [C015 source](../../../packages/ember-qc/src/ember_qc/algorithms/zephyr_constrained_contact.py) exports `constrained_contact_embed`; its SHA256 is `b870572b5bffd79f31bb0ace89e41e79ea64361d1cc346d8356f455c0063c9fa`. C014, C013, geometry support and the existing validation backend remain unchanged. The C014 constructor is not called: C015 imports its helpers and retains the transaction/publication control flow, whose placement calls resolve to the new C015 routine.

Completed proposals are built with quota-aware contact paths, capacity-preserving growth and pruning. Scratch masks and distinct-site consumption counts avoid constructing a full state for each growth-site trial. At materialization, direct state capacities and the existing score must agree exactly with scratch counts and the hypothetical score. A placement returns its first fully admissible root. A stopped successful scan is recorded as first-admissible, not exhaustive. Capacity failures arising after site exclusion or denied claims are separated from contact disconnection in the unrestricted free graph; only contact disconnection can use the inherited contact guide.

Per-placement diagnostics retain counts, root outcomes, obstruction owners and accepted sites. The final record includes an exact last private entry and source owner. Rejected growth trials do not emit complete capacity tables. Instrumentation, validation and output remain charged, with the inherited global deadline and final-validation reserve; no per-owner five-second cap exists.

## Focused checks

[Four groups](../../../tests/test_codex_constrained_contact.py) passed first attempt, in 0.004414s internal wall / 0.004413s CPU, 0.535279s recorded process wall:

- Scratch/direct capacity and score agreement; zero-gain growth, capacity-preserving leaf pruning and unchanged entry state.
- First-admissible stopping with additional roots available; a connected alternative route that avoids a zero-allowance singleton site and preserves every original partial contact.
- Capacity-induced component exclusion versus actual contact disconnection; inability to reach new-owner capacity; refusal to invoke the contact guide for that capacity failure.
- Interrupted scratch growth leaves the entry unchanged; a completed certificate followed by deadline expiration cannot publish or retain the proposed complete state.

These checks made zero complete constructor calls. The two complete controls ran afterward under the same source/check freeze, each once with seed 0, a five-second test allocation and ideal Z2. The unchanged independent oracle validates both returned embeddings.

| Control | C015 Q / ACL | C014 reference Q | Q change | C015 measured wall / CPU seconds | Roots examined / generated |
|---|---:|---:|---:|---:|---:|
| star22: 22 vertices, 21 edges | 23 / 1.045455 | 23 | 0 | 0.020622 / 0.020270 | 22 / 664 |
| K2,10: 12 vertices, 20 edges | 12 / 1.000000 | 12 | 0 | 0.009864 / 0.009794 | 12 / 323 |

Within-chain variance is 0.04338843 and 0 respectively; maximum chains are 2 and 1. The original C014 controls took approximately 0.1573s and 0.0183s and examined 664 and 296 roots. Those earlier timings were not paired with these calls, so they are historical observations, not speedup estimates. C015's generated roots can differ because its root domain and ordering changed. These first-admissible choices retain the control optima but do not show that global ACL is preserved.

The tiny-call process took 0.516309s including imports and test output. Both constructors returned successfully, with no timeout, fatal error or prohibited dependency attempt. Both used zero retractions: positive full-constructor retraction behavior remains for the Z12 screen to exercise. The saved stderr contains the existing `dwave-networkx` deprecation warning; it contains no test failure.

All calls and stdout/stderr are preserved in `results/codex/c015-constructor-checks/risk001` and `tiny001`. Nine source/contract bindings were frozen before checks and rechecked before tiny calls; exact check and outcome bindings are in `results/codex/c015-constructor-checks/freeze001.json`. The test source SHA256 is `02ae74d506cde4f3516cdf081750ac6dcda2289281ff3ba518acdb7bac2cb449`.

Proceed directly to the contracted complete Z12 screen under root's harness/registry ownership. No additional local routing diagnostic is indicated. The old C014 five failures, its SBM/WS Q regressions and the BA160/planar160 runtime deficits remain preserved. First-admissible selection, greedy routes and growth can still harm later construction or mean ACL. A061 remains retained, and no promotion, confirmation or publication claim follows from these controls.
