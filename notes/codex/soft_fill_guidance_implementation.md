# A052 one-guide prototype: reach restored, substantial guidance cost

The accepted fixed policy passes its small reach gate: all four prescribed outputs are original-valid, including the exposed cycle at **Q143**. It remains unregistered, pending parent review; no34-input run, extra guide, altered rank or increased allowance was added.

`factored/soft_guidance_construction.py` copies A051 and retains original-only requirements, its one-core-call bound and fixed repair primitives. Each prepared insertion chooses one currently placed virtual neighbor by source rank and computes an occupancy-ignoring target-distance map. The accepted keys use guidance after direct original contact count and before pressure in pool selection; complete private insertions still rank physical Q first. Edgeless original cores use the specified filled-core forest and parent guide while placing every survivor. Non-edgeless core construction remains unchanged, including the limitation on disconnected physical cores.

One full BFS charges every seed and target-edge examination through the existing engine scan method, including its live repair limit. Distances are private to that insertion; no partial map survives interruption and no map is reused after a guide moves. BFS/setup work and wall are overlapping subtotals of existing global/phase cost. Setup, queue and sort overhead remain inside the original deadline. Reports retain both completed and interrupted guide records.

## Checks and exactly four reach calls

The initial six-check run exposed unqualified `ROOTS`/`BRANCHES` names copied from the primitive module. No reach call ran in that attempt. Its exact source and failures are preserved under `attempt001`; qualifying the same pinned constants fixed the extraction error without a policy change. The subsequent **six groups pass in0.028s**: guided versus unguided root selection without enforcing guide contact, unchanged no-guide choices/work, independently computed target distances through occupied sites, fresh maps after ownership changes, exact repair/deadline interruption charging, edgeless-core forest coverage, and the unchanged single non-edgeless core call.

The four fixed reach calls then ran once each, seed0,20-second allowance and unchanged20M/global and repair caps:

| Input | A051 result | A052 result | Global scans | BFS calls | Guidance scans | Guidance wall | Total local wall |
|---|---|---|---:|---:|---:|---:|---:|
| Star128 |Q138|Q138|1,559,996|0|0|0s|1.245s|
| Wheel128 |Q218|Q228|14,398,158|84|7,705,242|4.636s|9.896s|
| Subdivided K5 |Q20|Q18|836,774|4|366,916|0.237s|0.604s|
| Exposed cycle126 |FAIL:119placed/Q266|Q143|14,326,865|83|7,613,507|4.660s|9.666s|

The star/wheel have127-degree hubs. All four use edgeless physical cores, invoke neither native nor repair, and finish without timeout or work exhaustion. The subdivision places all five surviving core vertices, guided by four forest edges. The cycle still has41 zero-placed-original-neighbor attempts, now ranked using virtual guidance; it completes below the predeclared266Q threshold. Historical A051 entries above compare quality/coverage only, not timing. Fixed050 completes that exact cycle atQ155, while historical049's fixed wheel and subdivision were better atQ189 and17.

**Lesson.** One virtual guide can restore useful construction reach without requiring its physical contact, but it is not a uniformly better placement rule. The wheel worsens10Q relative toA051; guide scans consume53.1% of cycle and53.5% of wheel global work. Their guide wall is48.2% and46.8% of total local call time. These measured overlapping costs must not be added again to global totals. The policy also changes edgeless-core order, so the subdivision improvement does not isolate distance ranking alone. There is no novelty, broad advantage or runtime guarantee claim. Parent review should weigh the successful cycle falsifier against this cost and the retained quality regressions before deciding any next experiment.

Evidence is frozen under `results/codex/a052-soft-guidance/attempt002`, with all source/target identities saved before execution and no prohibited imports. A final module-docstring correction is separately bound; its executable AST is identical to the tested body. No further solver calls occurred. The manifest retains both attempts and that exact correction.
