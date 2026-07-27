# hyde06 run queue / ledger

One batch at a time on hyde06. A run may launch only when no row above it is `RUNNING`.
Columns: script@sha is the pre-registered commit; W = workers.

| # | experiment | script @ sha | host | W | est core-h | status | notes |
|---|-----------|--------------|------|---|-----------|--------|-------|
| 1 | E0 crossover map (§4.1) | e0_crossover.py @ caf62119 | hyde06 | 48 | ~75 (≈2.7 h wall) | DONE 2026-07-27 | 8,235 rows; CSV+summary rsync'd to repo |
