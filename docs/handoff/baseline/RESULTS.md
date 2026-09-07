# Baseline results (frozen 2026-09-07)

Every file in this folder was produced by the code at the commit that
carries this folder (the s3.127 rewrite; engine `plane.py`), on a
128-core Linux server under a load average of 110–160 (which is why
budgets are counted in DP evaluations, not seconds — the engine's own
numbers do not depend on the load; the 60-second wall-clock arms do).
Re-run `docs/handoff/compare_baseline.py` to compare a modified tree
against these numbers.

## Files

| file | produced by | what |
|---|---|---|
| `plane_fingerprint_step6-dedupe.json` | `docs/paper2/data/plane_fingerprint.py step6-dedupe` | the acceptance fingerprints of the committed pipeline (after the duplicate-N(v) dedupe), `tail="none"`, work budgets — what `compare_baseline.py` compares against |
| `plane_fingerprint_step5-default.json` | the same harness one engine edit earlier | identical values; kept as the record the board was run with |
| `plane_fingerprint_step0-old.json` | the same harness on the ARCHIVED engine (commit `ea5d1cf2`) with `init_mode="random"` | the old engine's fingerprints from random starts, for reference |
| `rewrite_board_new-newmm.csv` | `rewrite_board.py new new+mm` | the paired board, the rewrite: `new` = `tail="none"` at work budgets; `new+mm` = `tail="mm"` at 60 s wall |
| `rewrite_board_mm.csv` | `rewrite_board.py mm` | stock `minorminer.find_embedding` at 60 s wall, same seeds |
| `rewrite_board_old.csv` | `PYTHONPATH=<worktree at ea5d1cf2> rewrite_board.py old` | the archived engine with its tail at 60 s wall |
| `rewrite_board_summary2.log` | `rewrite_board.py summary` | the merged table below |
| `invariance_probe_board.csv`, `invariance_summary.log` | `invariance_probe.py` | 5 question-order draws (`sched_seed`) and 5 init draws (`seed`) per cell, `tail="none"`, work budgets |

Cells and their graph ids: K100, K140 = `nx.complete_graph`; ER100_d10
= `nx.gnp_random_graph(100, 10/99, seed=12345)`; turan_n162 = gid 2647;
spin_glass_n163 = 37309; regular_n316 = 13096; ws_n486 = 17188;
grid_200 = 1590; honeycomb_200 = 32393; king_graph_196 = 32622 (all
via `ember_qc.load_graphs.load_graph`). Target: `dnx.zephyr_graph(12, 4)`.
Seeds: 0–9 on turán, ws, regular, ER; 0–2 elsewhere. Work budgets
(`max_asks`): K100 10000, K140 12000, ER 8000, turán 15000, spin_glass
12000, regular 10000, ws 15000, grid/honeycomb/king 8000.

## Fingerprints (engine only, `tail="none"`)

| cell | old engine, random init | rewrite |
|---|---|---|
| K8 on Z3 | 1.5 certified | 1.5 certified |
| K10 on Z3 | 1.8 certified | 1.8 certified |
| path-60 on Z12 | 1.017 | 1.067 |
| K100 on Z12 | 7.26 (budget-bound at 10k asks) | 7.26 at a fixpoint, 1,555 asks |
| turán n162, seeds 0–9 | 6.000 on 3/10 | **6.000 on 10/10** |
| grid_200 pre-tail | 1.87 | 1.605 |

## Paired board (ACL / mean max chain; successes in parentheses when < all)

| cell | minorminer 60 s | old engine + tail 60 s | rewrite, engine only | rewrite + tail 60 s |
|---|---|---|---|---|
| K100 | 10.47 / 15 | 7.26 / 8 | 7.26 / 8 | 7.26 / 8 |
| K140 | 20.29 / 40 (2/3) | 9.76 / 10 | 9.77 / 10.7 | 9.77 / 10.7 |
| spin_glass_n163 | 20.56 / 35 | 11.04 / 12.7 | 10.85 / 12.3 | 10.84 / 12 |
| turán n162 | 11.30 / 18.9 | 9.46 / 12.5 | **6.000 / 6** | **6.000 / 6** |
| ER100_d10 | 4.82 / 8.8 | 4.65 / 7.8 | 4.60 / 8.1 | **4.45 / 7.5** |
| regular_n316 | 3.59 / 9.6 | **2.78 / 6.5** | 4.75 / 13.6 | 3.61 / 9.3 |
| ws_n486 | 3.14 / 11.7 | **2.56 / 8.0** | 4.40 / 27.4 | 3.34 / 12.1 |
| grid_200 | 1.08 / 2 | 1.27 / 3 | 1.59 / 5.7 | 1.29 / 2.7 |
| honeycomb_200 | 1.16 / 2.3 | 1.33 / 2.7 | 1.89 / 6 | 1.24 / 2.7 |
| king_graph_196 | 1.76 / 3.7 | 1.83 / 4 | 2.56 / 7.7 | 2.11 / 4.7 |

Reading: the rewrite wins every dense cell and ER outright; it loses
to the old engine on regular, ws and king with the tail, ties grid,
wins honeycomb. Causes (measured; see `../OPEN_FRONTS.md`): per-ask
cost starves the 60-second arm; at a full budget the engine's own
sparse answers still carry long chains and lack the +0.4 the old
engine's spectral init supplied on exactly those cells.

## Invariance (engine only; range of pre-tail ACL over 5 draws; tol = max(0.3, 5%))

| cell | order draws: mean (range) | init draws: mean (range) |
|---|---|---|
| K100 | 7.26 (0.00) | 7.26 (0.01) |
| K140 | 9.757 (0.00) | 9.757 (0.00) |
| ER100_d10 | 4.66 (0.24) | 4.76 (0.25) |
| turán n162 | 6.000 (0.00) | 6.000 (0.00) |
| spin_glass_n163 | 10.86 (0.13) | 10.85 (0.12) |
| regular_n316 | 4.48 (**0.54**) | 4.60 (0.11) |
| ws_n486 | 4.28 (**0.39**) | 4.28 (**1.01**) |
| grid_200 | 1.59 (0.23) | 1.62 (0.20) |
| honeycomb_200 | 1.98 (0.17) | 1.94 (0.15) |
| king_graph_196 | 2.51 (0.22) | 2.56 (**0.32**) |

Bold = beyond tolerance. Every regular and ws run stopped on the ask
budget (15k asks ≈ 4 passes on ws), so part of that spread is
unfinished descent.

## How to judge a change

Better on a class means the mean over the class's cells (same seeds,
same budgets) drops by more than the tolerance in
`compare_baseline.py` without any cell's max chain growing, and the
dense cells stay at their templates. A change that helps one class and
hurts another is a finding to report, not a win.
