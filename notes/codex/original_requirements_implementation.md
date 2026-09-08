# A051 literal original-only requirements: failed reach gate

The literal A051 prototype passes its five targeted correctness groups but **fails the predeclared basic reach gate**. It is not registered in the pilot and must not proceed to the34-input comparison in this form. No soft placement guidance, extra retry, larger cap or alternative complete constructor was added.

`factored/original_requirements_construction.py` is an isolated copy of the fixed050 wrapper. The filled elimination order, protected anchors and surviving vertex set remain. The core call receives the original induced graph on **all** survivors, and the original physical edge count determines whether to use native or direct edgeless placement. There is no re-reduction. Physical requirements and pending demands remain full original adjacency throughout. No synthetic edge is removed during lifting and no removed-fill cleanup runs, including within blocked repair. Original changed-chain pruning, fixed050 repair, common deadline and scan limits remain.

The five checks passed in0.054s: exact K5-edge-subdivision core input without its synthetic edge, placement of all five survivors of an original edgeless core, nested-fill ordering with the≤3 placed-original-neighbor bound, unchanged no-fill star choices, and deadline rollback/late-core rejection. Inputs remain untouched and partial requirements equal original adjacency restricted to placed vertices. The separate target-edge oracle validates each saved completed or partial output. No prohibited imports occurred.

Four fixed reach calls then ran once each in the isolated local native environment, seed0,20-second allowance, original20M global scans and inherited repair limits. Their records and source/target identities were frozen before execution.

| Fixed input | n / m | Original core vertices / edges | Result | Q | Placed | Scans | Local wall |
|---|---:|---:|---|---:|---:|---:|---:|
| Star, degree127 | 128 /127 | 1 /0 | SUCCESS |138|128|1,559,869|1.339s|
| Wheel, degree127 hub |128 /254|1 /0|SUCCESS|218|128|6,990,166|5.857s|
| Subdivided K5 |15 /20|5 /0|SUCCESS|20|15|2,477,942|1.882s|
| Exposed cycle `ember_1829` |126 /126|1 /0|WORK_LIMIT|266 partial|119|20,000,000|15.174s|

All three complete outputs are original-valid, and the cycle's retained119-vertex partial minor is valid against its original induced requirements. No result timed out. None of these four cases invoked native or blocked repair: the cycle's ordinary insertion consumed the remaining global allowance before returning. Its **41 outer insertion attempts with zero placed original neighbors** make the lost spatial-guidance concern concrete. Intermediate physical locations were not saved, so this count alone does not reconstruct or prove the exact spatial cause.

The saved049 reach outputs are starQ138, wheelQ189 and subdivisionQ17; A051 ties the star and worsens the other two. These historical quality comparisons are not fresh timing comparisons. The exact exposed cycle completes in fixed050 atQ155, whereas this literal variant fails with an already larger partial Q. Partial Q is not a valid full-output comparison or an estimate of eventual completion.

**Lesson.** Removing synthetic physical requirements can reduce the core's contact burden while removing useful constraints on placement and pending demands. The subdivision's filled ordering core has10edges, but its five original-core vertices have none and must all be placed directly; the change is substantive even though the core vertex set stays fixed. The failure means fewer mandatory contacts are insufficient as this construction policy. Any future soft-guidance mechanism requires a separately documented hypothesis; it is not bundled here. No broad quality, novelty or MM claim follows.

Evidence: `results/codex/a051-original-requirements/attempt001` preserves all four results and the five-check log; `manifest.json` binds implementation, tests, pre-code amendment and all evidence. No prior050/native/helper bytes were changed. The runner refuses an existing output directory; any authorized repeat would require a new destination.
