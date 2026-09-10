# A066 initial screen: quality gains arrive early, first-validity discovery is unknown

2026-09-10. **A066 reaches its eventual final Q within 8.181–17.217 seconds of
wrapper entry on these nine calls, then continues searching until approximately
59 seconds.** After those last improvements, 428.544 of 449.048 added-stage
seconds remain: 95.43% of the observed stage time. This is retrospective evidence
of poor use of the remaining search time on this panel, not an early-stopping
policy or a shorter-runtime result. Other inputs may improve later.

The passive projection covers all 27 completed A066, pruning-only and A065 calls,
with 186 saved admissions, on the first nine encodings/eight structures. The
original constructor results and every MM deficit remain in
[the complete-screen report](066_constructor_results.md). No constructor,
validator or candidate module was called for this projection.

The table shows A066. Handoff bounds refer to when the wrapper can first report
its successful A061 base; they do not identify when A061 internally discovered a
valid embedding. Bounds are rounded outward to six decimal places. Other times
are rounded to milliseconds; these are clock observations, not statistical
confidence intervals.

| Input | Reported valid-base handoff bounds (s) | Base → final ACL | First eventual-final-Q admission (s) | Operator time afterwards (s) |
|---|---:|---:|---:|---:|
| ER80 | 8.687377–8.687457 | 3.2625 → 3.1500 | 11.670 | 47.235 |
| Planar80 | 7.283688–7.283752 | 1.5875 → 1.5750 | 8.181 | 50.738 |
| Grid128 | 8.375939–8.376029 | 1.3125 → 1.2422 | 9.333 | 49.561 |
| Singleton control80 | 9.409540–9.409659 | 2.5125 → 2.4875 | 10.297 | 48.552 |
| WS100 | 9.811774–9.811836 | 2.4800 → 2.4300 | 13.882 | 45.030 |
| SBM100 | 8.935884–8.935965 | 2.6100 → 2.5100 | 12.310 | 46.612 |
| Grid128 relabel | 8.687828–8.687902 | 1.2734 → 1.2266 | 9.819 | 49.109 |
| BA100 | 12.193845–12.193926 | 2.8200 → 2.3500 | 17.217 | 41.680 |
| Planar100 | 7.726576–7.726611 | 1.7400 → 1.6900 | 8.909 | 50.026 |

[Admission-by-admission ACL/Q curve data](../../../results/codex/a066-initial-trajectories/projection001/admissions.csv)
retains both elapsed wrapper and operator timestamps for all three arms. The
[full scalar projection](../../../results/codex/a066-initial-trajectories/projection001/summary.json)
retains unrounded handoff bounds, headline solver/process times and every point.
No unobserved intermediate point or internal time-to-first-validity is imputed.

Timing origins matter. The handoff's lower bound is the measured base-call
interval; its upper bound is the added-stage meter's start. That start is derived
from the consistent difference between each admission's wrapper and operator
elapsed times. A valid-base handoff must precede the added stage. Actual internal
first-validity discovery remains unrecorded. The eventual final Q first appears
at the identified strict-Q admission; its remaining operator time follows from
the recorded stage meter. Full solver and process wall use their own recorded
intervals and remain charged. Intermediate embeddings are not independently
revalidated here; original audit credit applies to the final returned maps.

The same retrospective pattern appears in the controls: A065 spends 423.180 of
447.401 operator seconds after its eventual final Q, and pruning-only spends
430.006 of 450.785 seconds. Their final quality differs from A066 where the pair
mechanism helps, so these totals are not time-to-equal-quality comparisons.

The decision supported here is to measure first validity and incumbent quality
trajectories in future complete screens and distinguish expensive initial
construction from later unproductive search. These data do not justify a fixed
cutoff chosen from nine development examples, and do not show that a shorter
call would survive its final validation/output gate. The already-running broader
A066 screen continues unchanged; no further candidate work was performed.

Evidence: `results/codex/a066-initial-trajectories/`. Root verified all eight
before-execution bindings and executed the projection once: PASS, 0.096432 seconds
process wall, 0.070980 seconds projection time before output. Summary SHA256
`3067f7dcdca58d37766ed05b7cd2f62a7be6417cc0af02ca0643c58c3a3b308a`;
CSV SHA256 `2ed79a5abcbdbc0bfefd67fb23fcd070c99c82b9c4a7f5e9d6d2b51591d3c733`.
Scope remains seed 0, exposed development data, no confirmation and no across-seed
variance estimate.
