# B015: certified skips advance the query, but do not restore the block

2026-09-08. **Do not launch a panel for this fixed policy.** The component filter skips the first two certified failures, but ER66 still exhausts its unchanged one-million-unit repair allowance. The tiny local witness succeeds. No registry edit, cluster action or full constructor comparison occurred.

| Fixed local call | Result | Repair units | Filter units, included | Whole diagnostic wall |
|---|---|---:|---:|---:|
| Tiny occupied endpoint | Valid full minor, 4 Q | 178 | 17 | 0.093 s |
| Saved B011 ER66 | No reconstruction | 1,000,000 | 20,400 | 0.802 s |

The separate `propagating_component_construction.py` implements the [pre-code skip-only policy](b_component_skip.md). It leaves the pool, block order, ordinary roots/routing, frozen ownership, promotion history and all work/deadline limits unchanged. It evaluates the exact component predicate through a smallest-boundary endpoint: a qualifying component must touch that endpoint. This changes only filter evaluation work, not insertion root selection.

The ER filter certifies release `[53]` with 121 units and `[55]` with 136 units. The complete blocks cost 402 and 416 units including copying and administration counted by the existing repair meter. Release `[31]` then passes after 20,143 filter units. The constructor inserts vertex **66 privately**, but exhausts the remaining allowance while restoring **31**. Its final recorded missing contact is chain 72; physical site 1991 remains protected by frozen owners 53 and 55. This temporary insertion is **not a committed extension** of the saved 64-chain/218-Q incumbent. Later release blocks are uninspected, so the result does not establish their infeasibility.

All three ER classifications finish; their combined filter wall is 0.01417 seconds, included in 0.597 seconds of helper wall. The global replay counter moves from 8,200,649 to 9,200,649. Matching and propagation counters stay at 99,944 and 691,179; growth adds five units for a completed `no_singleton_neighbor` check. Separate replay setup costs 184,048 units and is included in diagnostic wall. These local timings and overlapping counters do not establish a portable runtime improvement.

[Eight targeted test groups](../../../results/codex/track-b015-checks/attempt001/summary.json) pass: the six prescribed predicate cases, original-graph relocation/frozen ownership, arbitrary-degree pool handling, local/global/last-unit limits, interruption as unknown with rollback, nested accounting, reuse invalidation, and exact ordinary-success choices/work on two tiny controls. No failed test attempt or candidate-source correction occurred. The [two local records](../../../results/codex/track-b015-checks/attempt002-local-reach/summary.json) preserve all examined blocks, filter evidence, partial work and unchanged caller chains/promotions. No incomplete or late output receives recovery credit.

The failure now occurs during restoration, after a valid first insertion. A possible next question is whether the same fixed-frozen obstruction arises at that intermediate state, or whether restoration merely needs a different bounded route. Neither explanation is established by these records alone. No further filter placement, routing change, larger cap or block reordering is implemented here.

Stable source SHA-256: `ab9d63a680e5e6e2fbdbcdfd1f000122e8e9cac3584c3b64fee1ccfc43e1a671`; tests: `12a75062cf4155395b00ef068d3c8bc09dce1804f9549e057bbffc1f5920a86e`. Synthetic checks can be repeated in a new directory with `.venv/codex-native/bin/python -B results/codex/track-b015-checks/run_checks.py OUTPUT`; the fixed local observations are already preserved and need not be rerun.
