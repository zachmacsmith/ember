# B028 complete-constructor decision

2026-09-09. **Reject the fixed acceleration-only constructor and do not broaden its screen.** B028 succeeds on 2/6 inputs, B027 on 1/6, and A061/MM on 6/6 each. The one recovered success is reused SBM80; both fresh inputs fail. Thus the [frozen requirement](b_028_constructor_screen.md)—recovery in two families including a fresh input—is unmet. The compiled router remains a tested local implementation mechanism, without constructor promotion.

All 24 calls completed on hyde02, seed0, ideal Z12, configuration `{}`, 60 s allowance, separate fresh workers. Root's [original-graph audit](../../../results/codex/transfer-cycle-002/audit-b001/output/summary.json) passes with every solver wall/CPU and process time known. The [passive reader](../../../results/codex/b028-constructor-analysis/attempt001/output/summary.json) ran once, passed, and bound all 24 raw records; 12 B027/B028 receipts are present. No new candidate calls or refinement followed this screen. Returned validity is independently audited; intermediate mechanism statements below are constructor receipts.

## Complete outcomes and regressions

Cells show **Q (mean ACL)**. F is an uncredited failure, with undefined Q/ACL; overlapping diagnostic states never receive embedding credit.

| Input | B028 | B027 | A061 | MM |
|---|---:|---:|---:|---:|
| ER80, reused g0001 | F | F | 261 (3.2625) | 248 (3.1) |
| SBM80, reused g0005 | 140 (1.75) | F | 153 (1.9125) | 131 (1.6375) |
| Grid128, reused g0013 | 139 (1.085938) | 139 (1.085938) | 168 (1.3125) | 133 (1.039063) |
| Hidden singleton80, reused g0017 | F | F | 201 (2.5125) | 181 (2.2625) |
| ER100, fresh g0101 | F | F | 344 (3.44) | 350 (3.5) |
| BA100, fresh g0102 | F | F | 282 (2.82) | 199 (1.99) |

| Solver wall seconds, including failures | B028 | B027 | A061 | MM |
|---|---:|---:|---:|---:|
| ER80 | 59.043 | 59.056 | 30.025 | 10.771 |
| SBM80 | 47.159 | 59.065 | 19.963 | 2.767 |
| Grid128 | 36.478 | 15.896 | 31.679 | 1.287 |
| Hidden singleton80 | 59.045 | 59.055 | 31.303 | 11.929 |
| Fresh ER100 | 59.049 | 59.037 | 31.644 | 9.099 |
| Fresh BA100 | 59.049 | 59.045 | 37.352 | 14.356 |

B028's two valid outputs improve Q against A061 but both remain worse than MM: +9 Q on SBM, +6 on grid. Their solver times are respectively 17.04 and 28.33 times paired MM. Grid also regresses against B027 by 2.295 times solver time and 2.337 times process time (17.175→40.135 s), for identical Q. These losses remain explicit despite the recovered SBM success.

Within-embedding chain-length variance on SBM is B028 **0.9875**, A061 **0.77984375**, MM **0.40609375**: B028 regresses against both. On grid it is B028/B027 **0.12542724609375**, A061 **0.32421875**, MM **0.03753662109375**. Across-seed ACL variance is unestimated. The [24 exact rows](../../../results/codex/b028-constructor-analysis/attempt001/output/audited_rows.json) retain all CPU/process/RSS measurements, statuses and quality values; the [comparisons](../../../results/codex/b028-constructor-analysis/attempt001/output/comparisons.json) retain per-input reference gaps. No aggregate quality score hides failures.

## What acceleration resolved

Both implementations finish initialization on all six inputs, with the same recorded initial Q and overlap O. **This panel demonstrates no recovered initialization failure.** Neither starts valid. Full initialization elapsed time was not recorded; the `initialization` stage measures exclusive scheduling overhead and cannot substitute for it.

| Input | Initial O | Final O B027→B028 | Complete visits B027→B028 | Complete feasibility sweeps B027→B028 | Price updates B027→B028 |
|---|---:|---:|---:|---:|---:|
| ER80 | 58 | 61→42 | 107→251 | 0→2 | 1→3 |
| SBM80 | 25 | 5→0 | 426→962 | 4→7 | 5→8 |
| Grid128 | 17 | 0→0 | 1281→1281 | 5→5 | 6→6 |
| Hidden singleton80 | 58 | 65→77 | 84→116 | 0→0 | 1→1 |
| Fresh ER100 | 81 | 87→60 | 128→311 | 0→2 | 1→3 |
| Fresh BA100 | 75 | 62→19 | 123→413 | 0→3 | 1→4 |

Visits include initialization and quality work. B028 first resolves SBM overlap at **34.776 s/Q141**, improves to Q140 at **35.137 s**, then stops at a recorded period-2 quality recurrence at 47.159 s. B027 reaches only four complete feasibility sweeps and ends with O5. This supports computation starvation as a real cause on SBM, without proving the full trajectories identical under different clock truncations.

Grid first becomes valid at 12.129 s for B027 versus 24.339 s for B028. Both record Q141→140→139 and four complete quality sweeps before period-2 recurrence. B028's last strict gain occurs at 27.530 s. Total recurrence bookkeeping costs only **0.049 s across all six B028 calls**; recurrence is not the runtime bottleneck.

All four B028 failures retain complete overlapping states and stop at the search deadline: ER80/BA100 interrupt conversion, hidden singleton80/ER100 interrupt the kernel. None loses a recorded first-valid embedding in finalization. Lower final overlap on ER/BA is incomplete progress, not quality credit. The control worsens to O77 despite additional visits, while still completing no feasibility sweep. No saved full sweep-by-sweep overlap history exists.

## Charged cost and next mechanism decision

B028 spends **299.749/319.824 s (93.72%)** of total solver wall time in routing and its disjoint substages, including failures. The largest exclusive components are kernel **115.373 s**, conversion **101.321 s**, per-query packing **42.929 s**, seeding **16.942 s**, and allocation **12.988 s**; lazy imports cost **6.398 s** and once-per-engine target packing **1.469 s**. Compilation-dispatch receipts total **39.344 s**, but overlap kernel/seeding and include useful execution. Typed-list compilation can also occur in allocation. These are not additive compiler-free runtime estimates. Every call compiles two dispatchers; no cache, warmup exclusion, or arithmetic fallback is recorded.

The grid regression has a concrete implementation cause: per-query packing alone costs **18.596 s**, exceeding B027's entire 15.896 s call. Its conversion costs another 2.614 s; compiling dispatches cost 3.807 s inclusively. One-time target packing is only 0.137 s. Repeated whole-target adaptation, not just cold JIT, defeats inexpensive local routes. This warrants preserving the kernel as reusable evidence, not another speed-only constructor iteration.

**Next bounded question: does the priced joint-root proposal objective exclude useful overlap-reducing moves that its coordinated owner neighborhood could represent?** Existing feasibility acceptance admits every complete proposal, including overlap increases, so rejection of generated complete proposals does not explain these four failures. Conversely, only zero to three complete sweeps cannot establish that the neighborhood itself is incapable.

A subsequent diagnostic should use candidate-only saved states from the control and fresh ER/BA, with fixed outside chains, to compare the existing complete proposal's actual ΔO/ΔQ against a small bounded neighborhood solve. Use exact solving only as an optional local instrument. A lower-overlap feasible alternative within the same owner/interface neighborhood, coupled with unfavorable routing-surrogate preference, would support redesigning that objective or congestion feedback. Improvement available only after enlarging the movable owner/interface set would support a neighborhood redesign. Failure of a bounded solve leaves the question unresolved; it is not a global impossibility result. No witness/MM embedding may initialize either diagnostic arm, and any resulting mechanism must pass a fresh complete-constructor screen before continuation. This note authorizes no new implementation or calls.

Archive authority: root verified 243 files, digest `fa4fc35a0734ff329cddc97ba4b8da33ad989fb1b595f2f6130051b984d30e7b`; manifest `14faf948c02b6c553fe3a4893f02e7cdcd541dd80c3d0d760d8b3e99d4d9f5b8`. Reader SHA `1f6f81bc94bb59ebc224298279019ec2cc9beb6445f8b7457baa67647a214757`; [invocation and terminal status](../../../results/codex/b028-constructor-analysis/attempt001/) preserve the one 0.128 s passive execution. All findings remain exploratory development evidence; the untouched confirmation set remains unused.
