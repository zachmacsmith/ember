# C017 bounded diagnostic result

2026-09-10 UTC. **Stop this diagnostic neighborhood.** It finds a valid hard-quota alternative on ER100, but ER80 and BA100 are infeasible even after removing quotas. The contract's requirement for support on both an ER input and BA100 is unmet. C016 remains rejected; no constructor or further local expansion follows.

Six workers ran once on hyde03 in the frozen randomized order. All finished below the 60 s cold-worker allowance, all outer exits and supervisor exit were 0, and terminal observation found no tmux session or matching process. All 76 retrieved files match the terminal inventory. No worker restart, missing time, censoring, prohibited import or worker error occurred.

| Input | Mode | Local result | Cold worker wall / CPU (s) | Solver wall (s) | Process wall / CPU (s) |
|---|---|---|---|---:|---|
| ER80 | hard quotas | infeasible | 0.792 / 0.783 | 0.019 | 1.01 / 0.99 |
| ER80 | relaxed quotas | infeasible | 12.778 / 12.770 | 12.377 | 12.89 / 12.88 |
| ER100 | hard quotas | feasible | 25.302 / 25.292 | 24.035 | 25.59 / 25.57 |
| ER100 | relaxed quotas | feasible | 18.186 / 18.178 | 17.362 | 18.28 / 18.27 |
| BA100 | hard quotas | infeasible | 0.335 / 0.326 | 0.001 | 0.39 / 0.37 |
| BA100 | relaxed quotas | infeasible | 0.644 / 0.634 | 0.003 | 0.84 / 0.83 |

Totals: **58.037365 s worker wall, 57.983095 s worker CPU; 59.00 s process wall, 58.91 s process CPU.** GNU time is rounded to hundredths. These are diagnostic costs, not complete-constructor timings or an MM speed comparison. Model/domain preparation completed well within the allowance: model construction took 0.002–0.636 s; solve time dominated both ER100 workers and relaxed ER80. No artificial work cap censored a conclusion.

All three pairs have identical saved domains, variables, bounds and complete common sparse constraint matrices. Hard mode appends only quota rows. ER80 has domains of 337 and 5 sites, 5,755 variables, and 10,899/10,843 hard/relaxed rows. ER100 has domains of 1,763, 10 and 16 sites, 38,008 variables, and 72,470/72,436 rows. BA100 has domains of 0, 3 and 2 sites, 38 variables, and 202/118 rows. The empty domain belongs to its failed owner; sound contact-distance pruning already rules out a connected chain within length 3 while all outside chains remain fixed. No exact model was enlarged.

The original oracle independently revalidated both ER100 witnesses and their 34-owner induced partial source. Outside chains are unchanged, changed lengths respect their bounds, and both witnesses satisfy every final quota. Hard mode changes private Q from 122 to 124, with all three changed chains of length 2. Relaxed mode gives Q125, with failed-owner length 3 and blocker lengths 2 and 2. Their partial ACLs are 3.647059 and 3.676471; within-chain variances are 3.581315 and 3.512976. These are partial minors with 66 source owners still absent, so they confer **no class-level ACL, completion or generalization improvement**. Neither witness may initialize a candidate.

The first passive outcome reader failed before crediting a row because JSON converts integer dictionary keys to strings, changing sorted-key digest order. Its failure and source remain preserved. Separate v002 restores integer keys only in the original domain-record fields `length_bounds`, `domains` and `fixed_chains`; all six restored digests equal the workers' original digests. The exact three-hunk diff and scope receipts are saved. No model, worker or input changed, and no solve was rerun. Corrected passive verification passed in 0.645480 s wall / 0.619383 s CPU, 0.683369 s enclosing process. It uses the original oracle, unchanged capacity projection and unchanged B029 process parser; no model construction, solver or constructor call.

Evidence: [preparation](c_017_preparation.md), [corrected verified outcome](../../../results/codex/c017-conflict/analysis002/summary.json), [reader correction and six digest receipts](../../../results/codex/c017-conflict/analysis_correction001.json), [exact reader diff](../../../results/codex/c017-conflict/analysis_v001_v002.diff). Archive digest `bddbb0392df28e5ce959b1230643832c06bc265c472f69f8830aaa018dd57e55`; corrected outcome SHA `e701492d837659e1a39b95ce75c29ef20f4fb83d220745db2cbba267f49df052`.
