# hyde06 run queue / ledger

One batch at a time on hyde06. A run may launch only when no row above it is `RUNNING`.
Columns: script@sha is the pre-registered commit; W = workers.

| # | experiment | script @ sha | host | W | est core-h | status | notes |
|---|-----------|--------------|------|---|-----------|--------|-------|
| 1 | E0 crossover map (§4.1) | e0_crossover.py @ caf62119 | hyde06 | 48 | ~75 (≈2.7 h wall) | DONE 2026-07-27 | 8,235 rows; CSV+summary rsync'd to repo |
| 2 | e0_ceiling (§4.1 rule-2 deflator) | e0_ceiling.py @ caf62119, cells = 10 MM-feasible dev cells | hyde06 | 48 | ~17 | DONE 2026-07-27 | 1,000 rows; freebie ≈0/negative except sparse |
| 3 | E0 extension (§4.1b) | e0_crossover.py @ f04a4115 --resume | hyde06 | 48 | ~6 | DONE 2026-07-27 | p*(140) ∈ (0.12, 0.2] both topos |
| 4 | M3 battery (§4.5–4.8) | dev_suite/p4_pareto/p6_probes/m3_race @ 94d5e046 | hyde06 | 48/40/48/outer5 | ~110 | DONE 2026-07-27 | all gates resolved |
| 5 | P6 confirm (§4.8b) | p6_probes.py --confirm @ 9bec9817 | hyde06 | 48 | ~8 | DONE 2026-07-27 | beta-dhat confirmed 3/3 cells |
| 6 | M4 eval main+race (§4.10) | m4_eval.py @ e917c918 | hyde06 | 48 / outer5 | ~150 | DONE 2026-07-27 | freeze @ e917c918; supplement queued in M5 chain |
| 7 | M4 supplement (§4.10b) | m4_eval.py --arms minorminer-layout @ 3ea487e4 | hyde06 | 48 | ~18 | DONE 2026-07-28 | layout ~= stock ER, 0/5 all K_n |
| 8 | M5 FULL benchmark (§4.11) | m5full batches @ 51f4ad99+, chains m5full/m5b/m5c | hyde06 | ~2500 | DONE 2026-07-31 | ~594k rows; guards v1.1/v1.1.1; verdicts in notes |
| 9 | idle speed table (§4.13) | m6_speed.py @ deb88153 | hyde06 | ~2 | DONE 2026-08-01 | workers=1 idle |
| 10 | K_n seed deepening (§4.14) | m6_k140.py @ 65819fc6 | hyde06 | 8 | ~4 | DONE 2026-08-01 | row added retroactively 2026-08-03 (ledger gap); 240 runs |
| 11 | v1.2 T1 chain (§4.15: T1a dev / T1b native / T1c beta+arms / T1d race) | run_t1_hyde06.sh @ ac38cd89 (dev_suite --topo Z12; t1b_native.yaml; p6_probes --topo Z12 --confirm-beta; t1c_arms.py; t1d_race9.py) | hyde06 | 48/40/48/30/outer5 | ~35 (~1-2 h wall) | DONE 2026-08-03 | T1a summary preserved (raw re-run = row 13 R1); T1b PASS (ember 109/205 vs MM 98, 35 ACL-1.0 rows); T1c beta-dhat CONFIRM 2/3 cells, -fb PASS 3/3 (ramp rows -> row 13 R2); T1d race9 FAIL (median +0.00%, 44/40%W, interference 48%) — race8 ships |
| 12 | v1.2 T2 library re-verify (§4.16) | t2_z12.yaml @ sha stamped at launch | hyde06 | 60 | ~250-340 (~5-7 h wall) | BLOCKED on §4.15 verdicts | arms {p3-ember, p3-mm-beta-fb}; pairs vs archived m5full_z12 minorminer rows via m5_analyze --baseline-db |
| 13 | T1 remedies R1+R2 (§4.15 results note) | run_t1_remedies.sh @ 4366a255 | hyde06 | 48 | ~12 | RUNNING 2026-08-03 | R1 = T1a re-run (raw CSV clobbered by a mid-chain deploy of the tracked M3 record; sync now excludes result records; first-run summary preserved as replication anchor). R2 = 450 ramp rows re-run (stale fork .so, masked build error). stock/beta-dhat/arm/T1b/T1d rows stand |
