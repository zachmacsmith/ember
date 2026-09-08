# B012: blocked-only reconstruction local gate

2026-09-08. **Do not launch a nine-input screen for this fixed policy.** The tiny occupied-endpoint witness succeeds, but the prescribed ER66 continuation does not recover. This is a negative local reach/cost result, not a full-constructor comparison.

The isolated module `propagating_reconstruction_construction.py` extends B011 with the [pre-code policy](b_blocked_reconstruction.md): one blocked-only query, at most two released owners from two critical competitors and four required neighbors, all other chains frozen, first complete valid reconstruction. Ordinary successful insertions keep B011's path. The shared global, matching, propagation and growth limits are retained; the repair allowance is one million counted units per blockage and five million across a constructor. No new covering-matching gate or global promotion mutation was added. The shared pilot registry remains unchanged.

| Fixed supplied state | Result | Repair units | Helper wall | Whole diagnostic wall |
|---|---|---:|---:|---:|
| Tiny occupied endpoint | Valid full minor, 4 Q | 161 | 0.00042 s | 0.108 s |
| Saved B011 ER66 | No reconstruction | 1,000,000 | 0.568 s | 0.776 s |

The [complete local records](../../../results/codex/track-b012-checks/attempt002-local-reach/summary.json) preserve source/input identities and failed work. Both calls return within their five-second limits, leave caller chains and promotions unchanged, and run under the prohibited-import guard. The tiny result independently validates original contacts, connectedness, disjointness and unchanged outside chains. Its success establishes only this supplied move's reach.

ER's pool is `[53,55,72,31,78,67]`; no eligible owner was omitted. The complete ordered vector contains 21 blocks. The query exhausts its entire allowance in the **first** block, releasing only 53 and attempting to insert 66. It never reaches reinsertion of 53 or any later block. The final recorded path search still lacks contact 72, while site 1991 remains protected by frozen owner 55. Therefore this run does not assess release of 72 or joint release of 53/55. In particular, it is not evidence that every prescribed block is infeasible.

The saved ER work counter resumes at 8,200,649 and ends at 9,200,649. Separate replay setup costs 184,048 units and is included in the diagnostic wall; it is not a fresh constructor allowance. Existing matching, growth and propagation counters remain exactly 99,944, 276,188 and 691,179: no such query is reached. Increasing those limits would not address this failure. Counting is not a total machine-operation model; bitset and Python administration remain in measured time.

Six [targeted test groups](../../../results/codex/track-b012-checks/attempt001/summary.json) pass, covering original-graph relocation/frozen ownership, arbitrary-degree pool truncation, local/global limits and last-unit completion, nested matching/growth interruption accounting, domain reuse invalidation, deadline rollback, and exact ordinary-success choices/work on two tiny controls. No candidate-source correction or failed test attempt occurred. Reproduce synthetic checks in a new directory with `.venv/codex-native/bin/python -B results/codex/track-b012-checks/run_checks.py OUTPUT`; the two local-helper observations are already retained and need not be rerun.

This policy confirms that ownership relocation can work, but its released-Q ordering spends all available work before a potentially relevant larger block is inspected. A future proposal should justify rejecting structurally futile releases or directing a block toward the full conflict before routing; blindly enlarging the allowance would repeat the same cost problem. Any such policy change requires its own critique and fixed test. No full constructor, MM call, cluster action or broader screen was run for B012.

Stable source SHA-256: `8fbf424e9e2a77f13946c3bd77db43eb16a723c82da6290eb449c456e3737a0b`; test SHA-256: `2e6cf4b12b45f1685a199a7c757aa606d719479892194cfeb394b22aaeab9bf1`.
