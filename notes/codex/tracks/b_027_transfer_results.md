# B027 transfer screen: stop the fixed constructor policy

Exploratory development evidence, 2026-09-09. B027 (`mobile-tree-recurrence`) succeeds on **3/22 encodings, representing 2/20 primary structures**, versus A061 21/22 (19/20 primary) and MM 20/22 (18/20 primary). It succeeds on **0/12 fresh structures across all six fresh families**, and on none of the four hidden-witness controls. The three valid outputs improve on A061 but all remain worse than MM. The frozen continuation criterion fails. Retain the recurrence termination mechanism as a demonstrated way to stop deterministic repetition; stop this fixed complete-constructor policy and do not promote it.

Authority: [original-graph audit](../../../results/codex/transfer-cycle-001/audit-b001/output/summary.json), [all 66 status/quality/time rows](../../../results/codex/transfer-cycle-001/audit-b001/output/rows.json), and [passive mechanism receipts](../../../results/codex/b027-transfer-analysis/attempt001/output/mechanisms.json). Both audit and prepared reader completed their first execution with exit 0 and no errors. This review read their saved outputs, checked all 27 reader bindings, and inspected the frozen routing, acceptance, pricing, recurrence and deadline code; it executed no constructors or readers again. The reader SHA is `90b633e395f3bda5e58ea3a3952ce781e28c99543b28f0718acf599c7eddd190`; frozen B027 SHA is `b6f7f9dc1cb155cbe9a764ce249fa210bb6dea72e43aac886e9916aa584b7cf8`. The archived run is `results/codex/retrieved/hyde02/track-b-mobile-tree-027`; full identity is in [the freeze record](../../../results/codex/transfer-cycle-001/freeze-b/freeze_result.json).

All comparisons below are paired on hyde02, seed 0, ideal Z12, 60 s solver allowance, isolated candidate/MM interpreters. Witness embeddings were hidden from candidates. These are development instances, not an untouched confirmation set. Extra relabelings are nested observations, not extra independent structures.

## Every input and regression

Each method cell gives **Q / solver seconds** for an independently credited embedding; ACL is Q/n. `F` is a returned failure and `T` a harness timeout, with its measured solver time retained. No finite ACL is assigned to either. A061 means `native-branched-path` from this same-host screen.

| Input | n | B027 | A061 | MM |
|---|---:|---:|---:|---:|
| g0001 fresh ER 80 | 80 | F / 59.065 | 261 / 27.904 | 248 / 8.922 |
| g0002 fresh BA 80 | 80 | F / 59.071 | 216 / 33.808 | 257 / 5.478 |
| g0003 fresh regular 80 | 80 | F / 59.015 | 268 / 23.683 | 279 / 3.231 |
| g0004 fresh Watts–Strogatz 80 | 80 | F / 59.015 | 163 / 28.518 | 136 / 1.338 |
| g0005 fresh SBM 80 | 80 | F / 59.033 | 153 / 24.131 | 131 / 1.701 |
| g0006 fresh planar 80 | 80 | F / 59.019 | 127 / 17.204 | 118 / 0.746 |
| g0007 fresh ER 160 | 160 | F / 59.046 | 1289 / 56.247 | T / 61.454 |
| g0008 fresh BA 160 | 160 | F / 59.074 | T / 60.093 | 597 / 40.905 |
| g0009 fresh regular 160 | 160 | F / 59.061 | 927 / 43.136 | 1018 / 44.548 |
| g0010 fresh Watts–Strogatz 160 | 160 | F / 59.059 | 477 / 53.696 | 368 / 5.567 |
| g0011 fresh SBM 160 | 160 | F / 59.066 | 894 / 52.582 | 833 / 28.571 |
| g0012 fresh planar 160 | 160 | F / 59.050 | 288 / 58.800 | 276 / 4.132 |
| g0013 exposed grid 1584 | 128 | 139 / 18.151 | 168 / 28.293 | 133 / 2.188 |
| g0014 exposed honeycomb 32367 | 190 | 225 / 37.721 | 236 / 48.529 | 202 / 1.725 |
| g0015 exposed wheel 2429 | 127 | F / 59.018 | 206 / 20.733 | 144 / 14.457 |
| g0016 exposed complete 100 | 100 | F / 59.022 | 726 / 50.024 | T / 63.822 |
| g0017 hidden singleton control 80 | 80 | F / 59.025 | 201 / 23.101 | 181 / 3.572 |
| g0018 hidden singleton control 160 | 160 | F / 59.023 | 566 / 34.984 | 505 / 5.493 |
| g0019 hidden branch control 80 | 80 | F / 59.030 | 158 / 23.820 | 150 / 1.309 |
| g0020 hidden branch control 160 | 160 | F / 59.069 | 345 / 41.066 | 307 / 5.029 |
| g0021 extra relabeling of g0013 | 128 | 141 / 18.597 | 163 / 28.984 | 133 / 1.349 |
| g0022 extra relabeling of g0002 | 80 | F / 59.014 | 220 / 27.225 | 233 / 3.013 |

B027 loses 18 A061 successes and 17 MM successes across the 22 encodings. It has no common-success Q regressions against A061, because its only three successes improve Q by 29, 11 and 22. Against MM those same outputs regress by 6, 23 and 8 qubits: ACL 1.08594 versus 1.03906 on the grid, 1.18421 versus 1.06316 on the honeycomb, and 1.10156 versus 1.03906 on the relabeled grid. These narrow quality improvements over A061 cannot offset the lost successes. The grid relabeling changes B027 Q from 139 to 141; BA fails under both encodings. No transfer improvement is demonstrated on a fresh source structure.

Across-seed ACL variability is undefined with one seed. Within-embedding chain-length variances on g0013/g0014/g0021 are B027 **0.12543/0.22396/0.13812**, A061 **0.32422/0.25717/0.24554**, and MM **0.03754/0.05917/0.03754**. These are a different metric and also leave B027 worse than MM on every shared success.

All-attempt solver/CPU/process seconds are B027 **1196.241/1195.779/1225.455**, A061 **806.561/806.242/910.437**, and MM **308.551/308.420/338.915**. All 66 rows have measured times; none is imputed. The totals include every failure and both nested relabelings. All three B027 successful calls are slower than their paired MM calls; one is about 8.3 times slower and two about 13.8–21.9 times slower. Overall time ratios cannot rescue the success deficit or establish the user's final runtime objective.

## Mechanism diagnosis and work allocation

The original-graph oracle independently certifies **final** outputs. Initial overlap, first-valid time, transitions, recurrence and operation counts below are constructor receipts, not independent trajectory certificates. Only the first 16 visits and last visit are saved in detail; full counters do not reconstruct omitted transitions.

- **Construction does resolve overlap on two exposed structures.** All three credited calls start from an overlapping completed initialization: overlap 17, 11 and 20 on grid, honeycomb and grid relabeling. Their first recorded valid Q is 141, 242 and 141 at internal elapsed times 12.489, 7.486 and 13.602 s. Subsequent valid quality search reduces Q by 2, 17 and 0 before the independently validated final outputs. Thus these are complete-constructor successes, not simply favorable valid initializations. They do not isolate which coordinated B026 operator caused the improvement.
- **Recurrence termination transfers cheaply, but does not enlarge search reach.** The three successes stop at exact complete-state recurrences with periods 2, 12 and 2, after 4, 19 and 4 quality sweeps. The code keys chains, witnesses, cached trees, occupancy, Q and overlap using full tuple equality. The records report 4, 19 and 4 distinct boundaries. All recurrence work together costs 0.144 s, at most 0.26% of an individual successful solver call. No failure reaches recurrence checking. There is no B026 panel control, so this screen does not measure a B026-to-B027 speedup. A repeated deterministic quality state certifies repetition of that policy, not neighborhood or embedding optimality.
- **Computation prevents much of the intended feasibility search from occurring.** Routing consumes **1146.187/1196.241 s (95.82%)** of all-attempt solver time. Every failure interrupts routing at the search deadline. Three never finish initialization: ER 160 places 108/160 owners, regular 160 places 159/160, and complete 100 places 37/100. Of the other 16 failures, 12 complete no feasibility sweep. The policy updates congestion prices after initialization and after complete feasibility sweeps, so those 12 get only one update. These include persistent wheel and hidden-control failures as well as several fresh families. Exact joint-root distance searches and their Python heap/adjacency/meter cost therefore starve both later construction and congestion adaptation.
- **Cost is not established as the sole explanation.** Watts–Strogatz 80 and SBM 80 complete four feasibility sweeps, planar 80 two, and branch control 80 one, yet still fail with overlap 10, 3, 14 and 29. Feasibility accepts every complete certified proposal, including overlap increases; prices change only between whole sweeps. The root score sums independently shortest neighbor distances with root cost counted once, while attachment can share additional path segments. Its exact minimizer need not minimize the resulting shared tree's cost or actual overlap. A deficient proposal objective, neighborhood or price/acceptance schedule remains plausible. Zero `no_joint_root` receipts among complete visits does not mean the search can reach a disjoint minor.
- **There is no active work, query or pass cap to relax.** The frozen code leaves those limits unset; counters and the first-16 trace bound are diagnostics. The 60 s outer allowance reserves 1 s for finalization, explaining failure solver times 59.014–59.074 s. Observed finalization is much cheaper than that reserve, which can be reviewed in a subsequent experiment, but recovering roughly one second would not address routing's dominant cost. Recurrence exits are justified by deterministic repeated state, rather than an arbitrary patience threshold. A universal 3-times-MM runtime gate was not applied.

## One bounded follow-up hypothesis, not an implementation decision

**Hypothesis:** expensive exact routing prevents enough congestion-price updates to resolve overlap on several source structures; a semantically identical faster routing implementation will improve complete-constructor success within the same 60 s allowance. This tests computation separately from representation, neighborhood and acceptance. It does not propose more wall time, a new constructor portfolio, or a globally exact embedding solve.

If this is selected for a later track, predeclare an acceleration-only experiment preserving root scores, tie ordering, completed proposals, transfer rules, acceptance, and price-update schedule. First establish non-time transition equivalence on bounded cases and measure routing acceleration on the same host. Then run small complete constructors on two recorded failures with contrasting sweep exposure (for example ER 80 and SBM 80) plus two fresh instances from structurally different families. Keep original and accelerated runs separate with paired MM and A061 controls; record completed sweeps, price updates, overlap evolution, final independent validity/Q and all cost/failures. Do not select outputs across runs.

**Discriminating observation:** a verified routing speedup that produces several times more complete feasibility sweeps and new valid embeddings on different structures supports computation as a shared limiting cause. Similar overlap stagnation despite that increased search exposure, or recurrence without quality competitive with MM, argues for redesigning proposal/price or move mechanisms instead. An implementation that fails to accelerate or changes completed decisions is an inconclusive cost experiment. The present evidence cannot choose between neighborhood and acceptance as the remaining cause. No optimization work or additional calls were performed for this proposed follow-up; fixed B027 remains rejected regardless of its outcome.
