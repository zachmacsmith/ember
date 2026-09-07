# The s3.127 rewrite plan (the working plan of the session that built it; kept verbatim as a record)

## Context

Max (2026-09-03): the engine is past fathomability (factored/ ≈ 8,100 lines, 28 knobs); the order-invariance board (s3.126) showed the ladder schedule is worth nothing on eight of ten cells and is the worst order on ER and turán; turán returns 9.253 from most paths — a specific attractor, not budget. Direction: stop measuring the old engine, find the deviations from the project's philosophy hidden in the code (Max's bet: at least one, secretly driving the bad numbers), measure meat vs engineering, and write a fresh small engine that a person can read in a sitting.

**The specification, in Max's words (the thing the rewrite is held to):**

> The algorithm leans heavily on the fact that D-Wave hardware graphs are a product topology between a grid and a complete bipartite graph. It leverages this geometric regularity to approach the problem in a way minorminer can't. What the geometry tells us is that variables ought to have a straight horizontal and vertical run that connects to all their graph neighbors, since that is how cliques and dense stuff tends to be embedded, and sparse stuff has short enough chains that this simplification ought not really hurt. It makes it easy to keep a minimal state per variable: its order on the x-axis and its order on the y-axis. From that we derive logically where the horizontal and vertical bars need to stretch. We optimize the sum of derived chain length over an idealized version of the graph (strictly weaker than the hardware). The optimization uses two dynamic programs that go back and forth, an interleaver and a packer. The packer takes the x and y orders and optimally gives each variable a position while using the derived reaches to enforce capacity. The interleaver (using a frozen order → position map from the packer) splits an order into two subsets and optimally weaves them back together. There is staleness between the two; we accept all moves and trust that near the solution the freezing is nearly exact and at the solution it is exact. The point is to make moves as impactful as possible, as quickly as possible, so that we attract to solutions minorminer stumbles toward incrementally. Minorminer runs at the end; we hope to remove it one day.

House principles the audit checks against: proposer == judge (one accounting); no penalty methods, no λ; feasibility by construction, never repair; no mechanism names a graph type; the init must not matter; question order must not matter; no id/label luck; no bandages; winners ship as defaults.

## Self-criticism before the audits report (what I already suspect, so the audits can be checked against it)

1. **The interleaver does not price what the judge prices.** It ramps values by 1e-4·slot to break ties (dp-internals §2: "a second objective, not a tiebreak", +9 to +11 units of bias at n=486), and under tied values (the production regime — packed line indices) 142/400 of its accepts were not improvements and 55 strictly worse. Accept-all adopts them. That is a proposer ≠ judge violation at the heart of the loop; the "at the optimum the freezing is exact" argument does not cover a proposer that is wrong about ties even at the optimum. Candidate driver of turán's 9.253: on the interleaved diagonal every block is a tie plateau.
2. **The bar term is missing from the objective.** Measured this session: the plane prices a contact-bearing point arm at 0; with it (`arm_cost`) plus strip, turán's crystal is found in 60 s. Under spans only, the interleaved state (every variable two-sided) and the crystal (every variable one-sided) sit on a plateau the judge cannot see. Not a knob in the rewrite: the objective.
3. **The kappa floor invents capacity demand** (deficit/4 widening on both axes, even contact-free ones; dp-internals §1). A degree heuristic inside the books is a proxy, and it is read by packer, converter and (in the sound judge) the pen. The rewrite should have no floor: capacity is the derived reach, nothing else, and the converter must seat exactly that.
4. **Repairs exist**: the straggler clamp, `_resort_orders` on misses (rewrites the ORDERS, i.e. the state, outside the move family), `_center_shift`, completion's extensions/bridges. Each is a place where what the plane meant is silently changed.
5. **Hidden geometry**: boundary zeroing on all fabrics, anchor at line 1, left-justification by a deque tie rule, the phantom trailing brick. Some are real fabric facts (Zephyr boundary parity), some are accidents; the rewrite should state each as a fact of the fabric or drop it.
6. **Acceptance by fingerprint can freeze a bug.** K100 = 7.26 and turán = 6.000 are template facts, safe; "grid pre-tail 1.76" is a number of the current family and its ceiling — use it as a floor, not a target.
7. **The tail.** The plane alone loses to minorminer on sparse cells; the rewrite must decide whether that gap is the family's ceiling (junction packing, abutment) or the objective's blindness (bar term) — the s3.125 smoke says the bar term recovers a third of it.

## Census — meat vs engineering (function-by-function, working tree)

| bucket | lines | share |
|---|---|---|
| docstrings + comments | 2390 | 29% |
| blank | 580 | 7% |
| live MEAT (default path) | 1634 | 20% |
| live ENGINEERING (default path) | 1084 | 13% |
| DEAD (unreachable under defaults) | 2562 | 31% |
| total | 8244 | |

Of executable code (5274): meat 31%, engineering 21%, dead 49%. Of the live path (2718): meat 60%, engineering 40%. Half the live meat is in field.py, and four blocks are most of it: interleaver `align_reinsert`+`_arm` (210), `complete_seeds` (130), converter `_convert_line`+`_arm_targets` (108), packer kernels `_pack_dp`+`_jstar_*`+`_seg_radd`+`_axis_coeffs` (131) — about 580 lines of exact, oracle-tested logic. That is the "600 lines of pure logic" Max remembers; everything else is scaffolding around it.

Dead by module: seat.py 837/914 (the lex engine; only `seat_energy` survives, called once for a diagnostic), orders.py 376/715 (wave loop, tiles, xy, widen, wrap, strip, arm_cost, hier — all knob-gated), placement.py 217/593 (dead inits, dead engines, dead tails), costs.py and loop.py entirely (the old router), ball.py 242 (`_place_cross`). Knobs: 28; 12 load-bearing on the default path, 13 read-but-inert, 3 never evaluated. placement.py spends 21 code lines and 277 comment lines declaring knobs; its diagnostics block is ~110 lines.

Live call graph (default): attract_embed → TileGrid/target_layout → multilevel_init → rank reduction → order_arrange(plane, carry): readout = pack_project(project=False) [`_stair_contacts` → `arm_books`/`_bars_arrays` (kappa floor) → `_axis_coeffs` → `pack_lines`/`_pack_dp`/`_jstar_pass`], judge = `stair_energy`, moves = `_probe` → `align_reinsert` → `_try_adopt` (re-readout, `_resort_orders` on misses) → THE projection pack_project(project=True, brick_pools) [+`_jstar_profile`, `_center_shift`] → `arm_books` → `wire_seeds_exact`/`_convert_line` → `complete_seeds` → certificate/`is_valid_embedding` → minorminer legalize (if deficits) → `spur_prune` → minorminer grind → `ball_polish`.

Exact kernels with brute-force oracles (keep verbatim): `align_reinsert`+`_arm` (all merges × orientations, both bar values), `pack_lines`+`_pack_dp` (all assignments), `_jstar_pass`/`_seg_radd` (reference pass), `_stair_contacts`/`_bars_arrays`/`arm_books` (verbatim pre-s3.114 references), `complete_seeds` (validity/deficit properties), `stair_energy` (is the oracle).

## The adapter and kernels the rewrite keeps (with sizes)

Keep verbatim (≈1,250 lines): `_tile_orient` + `TileGrid` (155), `_stair_contacts` (39), `_bars_arrays` (63), `stair_energy` (23), `arm_books` (73), `_brick_pool_arrays`/`line_pools`/`_target_kappa` (70), `_axis_coeffs` (32), packer kernels `_seg_radd`/`_jstar_pass`/`_jstar_profile`/`_pack_dp` (135) + `pack_lines` (119), `align_reinsert` (378), converter `_arm_targets`/`_convert_line`/`wire_seeds_exact` (187) + the stride-1/untyped seeding path (207), `complete_seeds` (199), `spur_prune` (60), `_mm_route` (24), `ball_polish` (158, placement-independent), registration (25).

Delete with the rewrite: all of orders.py (970), seat.py's search half (~650) and its judges except what the strip key needs, `pack_project` (325; the `_half` core is re-implemented as the strip readout), `_center_shift`, `edge_monotonize`, `xy_reinsert`, `stair_step`, `bar_domains`, coarsen.py entirely (548) if init is random, `source_positions`/`_landmark_cent`/rank reduction, costs.py + loop.py (the old router, 400), `_place_cross` (ball singles).

Interface contract downstream of the engine (placement.py:894-956): `tpts` = integer-valued tile coordinates in-window; the contacts bundle (or `_orders`/`_yrank`) that the layout was optimized under (the two-books rule); a diag dict. Untyped targets: engine no-op, minorminer does everything (keep). Pegasus/Chimera: stride 1, converter/completion/certificate gated off; the engine half is fabric-agnostic and runs, the story degrades to capacity-first + MM legalization (keep the `eff_*` gates in one place).

Hidden couplings found (the rewrite states each as a fact or drops it): the converter is co-designed with packer-shaped states (measured: a capacity-clean non-packer state converts at 578 deficits, 0 after one pack) → the rewrite's state is packer output by construction; the kappa floor is implemented in four places, the one-tile footprint in three, boundary zeroing in three, the phantom-brick clamp in three with deliberately different rules (pack absorbs, `row_overflow` does not) — ONE books function must be the only accounting; `min_span` is a three-valued switch as a float; anchor at line 1; `snap`'s −1 widening; `_MISS_COST` magic; `np.rint` half-to-even; the stride hinge in `_lane_ok`/`ext_to`; determinism is a tested end-to-end property (sorted iteration, seeded RNGs only).

## The deviation audit (measured, ranked)

The reframing fact: **on turán the default judge already prefers the crystal** — stair 1768 at the crystal vs 2598 at the 9.253 state vs 3906 at the init. The engine never gets there. Turán is a reachability-and-budget failure; the sparse cells are an objective failure.

1. **The default init pre-commits the worst y-order, and the seed cannot change it.** `multilevel_init` (coarsen.py:500-534; the "spectral" init on Zephyr) coarsens turán to a 2-node quotient, the n<3 circle fallback puts the two supernodes at the same y, and the disc spread makes the y-order alternate blocks 133 times. `seed` reaches the init only as a shuffle of a 2-element list, so turán has exactly two inits over all seeds, mirror images — that is why 9.253 "recurs across seeds". Every init whose y-order is already nearly block-separated (plain spectral, landmark, trivial) reaches 6.000 in 60 s. Violates "the init must not matter" and "the crystal is the output shape, not the input shape". **This is the deviation Max was unaware of.**
2. **The move family cannot un-interleave.** A reinsert keeps R and S as subsequences, so the run count can never drop below max(runs(R), runs(S)); from an alternating order no single contiguous-run move can halve it. The one unit that can gather a scattered block is the graph-derived group (`hier_units`), default off and labelled "toxic on the plane crystal" — measured here as the single best arm on turán (6.000, stair 1663). The units must not be defined by the current order alone.
3. **A pass is 93% edge pairs.** turán: 938 interval asks + 13,122 pair asks per pass; at 60 s the engine never leaves pass 1; the bookmark sits at ask 726 (all improvement from intervals) while 12,700 pair asks improve nothing. At 300 s the third pass reaches the crystal. The clock is a parameter of the answer. Pairs are dead weight under carry (subsumed by scale-2 runs plus reversal).
4. **Schedule sensitivity (6.49–10.28 on the same ask set)** is the symptom of 2 and 3: the bag wins because it re-asks intervals between pairs.
5. **The judge is blind to one qubit per active arm** (sparse driver): predicted vs realized qubit mass is off by −76% on grid and −68% on ws under the default objective, −1% to −8% with the bar term. And **my own comment in placement.py is false**: "on turán the active-arm count is fixed" — the crystal has 162 active arms, the interleaved state 322; the bar term is the largest single differential on turán (324 stair units), which is why arm_cost+strip found the crystal in 60 s. The term belongs in the objective unconditionally (`bar = stride`).
6. **Accept-all's premise fails hardest near the optimum**: a y-move is priced against frozen x, then the readout re-packs BOTH axes; `adopt_worse` is 7% from the init and 40% at the crystal. `axis_single` (re-pack only the moved axis) makes the frozen picture literally true and measurably helps (8.815 vs 9.253). Not the acceptance rule: audit mode is worse (9.92).
7. **The epsilon ramp is a second objective** (46.5% of weaves differ, 17.6% extra tie-accepts that bump `state_ver` and invalidate the whole memo → budget churn) but exonerated as a driver: 0 bad accepts, 0 missed improvements over 938 real asks and an exhaustive K_{20,20} check. The oracle is circular (applies the ramp; draws distinct values).
8. **Kappa floor**: wrong in principle (widens a contact-free axis from a degree heuristic) but exonerated on turán (0 deficits; `span_floor=False` reproduces 9.253 exactly). Given hard column capacity the floor is redundant (81 contacts force ≥ 11 columns anyway).
9. Hidden geometry and label luck present, not implicated: boundary zeroing (a real Zephyr parity fact), anchor at line 1, deque tie left-justification, `_MISS_COST` λ, `free[0]`/id-sorted completion, `stride` selected by a family string, eigensolver switch at n>300.
10. Repairs present, inert on measured cells: completion's extensions/bridges, `_convert_line`'s fallback, `_resort_orders` (live under `strip`).

Three docstrings verified false: `field.py:12-17` ("not a simulated proxy"), `field.py:33-36` (participation by arm length — both live call sites pass `min_span=0`), `placement.py:494-496` (mine, above).

## Design — the rewrite

**Files.** One new engine file `factored/plane.py` (target ≤ 500 lines of code). Kernels stay where they are for now (`field.py`: contacts/books, packer kernels, interleaver, converter, completion) and the dead half of field.py is deleted in the same round; `orders.py`, `seat.py`, `coarsen.py`, `costs.py`, `loop.py` are deleted; `placement.py` shrinks to the handoff (books → converter → completion → certificate → tail) and the registry entry. `ball.py` and `polish.py` stay as the tail.

**The engine, as Max specified it, with the audit's corrections built in:**

- **State** = two orders `(ox, oy)`. Init = two seeded permutations. No geometry device, no coarsening, no ranks-from-points.
- **Readout** = the packer, per axis, on the strip: x into the real columns (per-column brick profiles, boundary columns zeroed, extended above the chip with the ideal pool), y ideal and anchored at 1. One move re-packs only its own axis (audit #6). Books = `arm_books` with `floor=False` (audit #8), `min_span=0` stated as the rule "every arm is at least one tile". Misses are counted, never clamped silently: a miss is the leading key.
- **Objective** = lexicographic: [row overflow + misses] first, then Σ over active arms of (span + stride). The bar is unconditional (audit #5). Judge and proposer read the same books; the interleaver prices the bar in its transitions (built this session, oracle-tested).
- **Move** = `align_reinsert` (remove a set, reinsert at its optimal weave, forward or reversed). **Units** (audit #2): (a) contiguous runs of the current order at scales n/2 … 2 (no pairs — audit #3); (b) the order-independent gather units `N(v)` for every v — the neighbours of a variable as one block. For a biclique `N(v)` is the other block, so the bipartition is one move; for a sparse graph it is "bring my neighbours to me"; no coarsening, no thresholds, no graph type named. Units of size 1 are the scale-1 runs.
- **Schedule** = one bag per pass over all units on both axes, seeded; accept every DP proposal (Max's rule) but the DP's own gate is true-cost strict improvement with rank-span only as a lexicographic tiebreak (audit #7: no ramp as an additive term); the `tried` memo keyed by (unit, axis) and invalidated per accept as today.
- **Stop** = work budget in DP asks plus the fixpoint certificate (a pass with zero accepts); the wall clock only as a safety net that is reported, never a parameter of the answer.
- **Projection** = the strip readout is already on the chip in x; the final y pack is the bounded pack with real row profiles; `strip_miss`/row overflow at the bookmark are reported as the capacity report. No `_center_shift`, no `_resort_orders`, no clamp beyond the counted miss.
- **Handoff** unchanged: `arm_books(tpts, contacts of the bookmark's y-order)` → `wire_seeds_exact` → `complete_seeds` → certificate → (tail).
- **Parameters**: `timeout` (safety), `seed`, `max_asks`, `tail ∈ {"none", "mm"}`. Nothing else. Diagnostics: asks, bookmark_asks, passes, stopped_by, pen, stair, bars, strip_miss, certified, mm_skipped, legal_acl, legal_max_chain.

**Acceptance (fingerprints, then the instrument):** K8 on Z3 = the template; K100 = 7.26; turán n162 from a random init reaches exactly 6.000 (the N(v) unit makes it one move) within a stated ask budget on all 10 seeds; path-60 = 1.017; grid pre-tail ≤ 1.76 (a floor, not a target). Then the s3.126 instrument on the new engine: bag draws must agree within tolerance on every cell (order-free by construction is the claim), random inits must agree (init-free is the claim). Then the standard board against stock minorminer and the old default, paired by (instance, seed).

**Deletion list is executed in the same round**, not later: the point is a tree a person can read.

## Decisions (Max, 2026-09-03)

- **Tail:** kept as an optional external polisher behind one parameter `tail ∈ {"none", "mm"}` (mm = warm grind + ball pass on the finished embedding). The engine is measured with `tail="none"`; the shipped default is decided by the board.
- **Old engine:** deleted in the same round. Max commits the current tree as the archive first; the paired comparison board runs the old default from a git worktree checked out at that commit.
- Pegasus/Chimera: unchanged gating (engine runs, converter/completion/certificate gated to stride 2).

## Design corrections from the review (measured against the code)

1. **N(v) works as claimed.** Measured on K_{81,81} in an interleaved y-order with packed tied values and bar=2: one `align_reinsert(oy, N(v), axis=1)` ask returns the block-separated order (2 runs), true cost 5219 → 3134, 17 ms. Cost per ask O(p·m + n + E); at n=486 ≈ 35 ms (the `stepR` Python loop dominates, vectorize later if ws is budget-bound). Per pass: turán ≈ 1,260 asks (≈ 25 s unloaded) vs 14,060 today; ws ≈ 3,900 asks (≈ 2.5 min).
2. **The ramp goes, and the interleaver stays exact.** 300 tied-value trials vs brute force under rank contacts: the ramped DP makes 0 bad accepts but 77/231 accepts are plateau moves (true cost unchanged), each bumping `state_ver`, wiping the memo, and making the zero-accept fixpoint unreachable on plateaus; without the ramp 154 accepts, all strict and optimal, 0/0/0/0. Change: `field.py:1751` `val = np.asarray(values, dtype=float)`; oracle gains a tied-values arm with unramped rank-contact ground truth (`test_field.py:432-459`).
3. **The y-readout uses real row profiles on the chip, extended above with the ideal pool** — the mirror of the existing `real_x` rule. Row 0 has pool 0 so no anchor rule; no `unb`/`L_max` branch; and a pen-0 bookmark is entirely on the chip on both axes, so **there is no final projection**: the judged state is the handed-over state.
4. **The leading key is the total brick overload of the books against one profile table** (pool 0 off-chip, no phantom absorption), not `row_overflow + misses`. It subsumes rows-beyond-the-chip, prices the cross-axis staleness of single-axis readouts (a y-move can overload columns until the next x-move), and makes misses diag only (a straggler booked on its predecessor's line shows up as overload). Integers → tuple comparison, no `_LEX_M` scalar.
5. **The handoff must pass the engine's books/yrank.** Today placement.py:903-908 recomputes `arm_books` without `yrank`, which disagrees with rank contacts on tied rows under the `_VERIFY_CONTACTS` fence.
6. **Tail** = `tail ∈ {"none", "mm"}`, where `"mm"` is today's `mm+ball` (warm grind then the ball pass); ball.py stays, `_place_cross`/`singles` deleted. The wall split for the tail is one stated safety constant (0.5), reported as `stopped_by="deadline"` when it fires; never a knob.
7. Keep list additions: `derive_bars_stair` (6 tests use it), `bar_widths` (diag), `wire_seeds_iv` (stride-1 path).
8. Boundary zeroing gated on `stride > 1` (the Zephyr one-parity fact); this changes Chimera/Pegasus relative to every recorded number — recorded as a decision, measured on the contract cells.

## The new file: `factored/plane.py` (≈ 400 code lines)

```python
def profiles(grid) -> (ph, pv)           # _brick_pool_arrays(grid, s) with lines 0 and L-1 zeroed iff stride > 1; memoized. THE capacity book.
def books(pos, src_adj, grid, oy)        # arm_books(pos, src_adj, grid, kappa=1.0, floor=False, min_span=0.0, contacts=_stair_contacts(pos, src_adj, yrank=rank(oy)), yrank=rank(oy), ybound=False)
def judge(bk, grid, prof, *, bar)        # -> (pen, stair): pen = Σ_(orient, line, brick) max(cover − pool, 0)² over bk[2] tuples (bricks floor(a/s)..floor(b/s)); stair = Σ spans over bk[1] + bar·#active sides over bk[0]
def pack_axis(axis, order, pos, bk, grid, ranks)  # items = bk[2][axis]; real line profiles extended (axis 0: along bricks to ceil(ymax/s)+2 at pool_u; axis 1: ceil(n/pool_u) uniform rows appended); coeffs = _axis_coeffs(bk[0], pos, axis, ranks); pack_lines(...); a None takes its order-predecessor's line (monotone by construction, no re-sort) and is counted
def readout(axis, ox, oy, pos, src_adj, grid)     # books → pack_axis → new pos (integer floats) → books on the new pos (same contacts) → (pos, bk, misses)
def units(ox, oy, src_adj, rng)          # per pass: contiguous runs of each order at scales n/2, n/4, …, 2, 1 (half-overlapping) on both axes + N(v) for every v on both axes; one shuffled bag
def arrange(src_adj, grid, *, seed, max_asks=None, deadline=None) -> (pos, bk, info)
    # init: two seeded permutations; pos from readout(1) then readout(0)
    # loop: for each unit in the bag: memo check → align_reinsert(order, unit, …, bar=stride) (no ramp; strict true-cost improvement) → readout(axis) → judge → adopt (accept-all) → bookmark by (pen, stair) → memo invalidation on accept
    # stop: zero-accept pass (fixpoint) | asks ≥ max_asks | deadline (safety) ; info: asks, bookmark_asks, passes, accepts, stopped_by, pen, stair, bars, misses
```

Untyped grid or n < 3: return rank positions unchanged (as `order_arrange` does today).

`placement.py` shrinks to: grid/eff gates → `plane.arrange` → `arm_books` identical to the engine's (or the engine's `bk` passed through) → `wire_seeds_exact` / `wire_seeds_iv` → `complete_seeds` → certificate → `spur_prune` → tail → result dict. Signature `attract_embed(source_graph, target_graph, *, timeout=300.0, seed=0, max_asks=None, tail="mm", **ignored)`.

## Build order with checkpoints (each checkpoint is a fingerprint, tail="none")

0. **Archive.** Max commits the current tree (the s3.124b–s3.126 state) as the archive commit; the comparison board later runs the old default from a worktree at that commit. Fingerprint harness `docs/paper2/data/plane_fingerprint.py`: K8/K10 on Z3 (certified, mm_skipped, extensions == 0, template ACL), path-60 on Z12 (1.017), K100 on Z12 (7.26), turán 2647 on Z12 seeds 0–9 random init (6.000, mx 6, at a stated `max_asks`), grid_200 pre-tail floor (≤ 1.76). Record the current default's values at step 0.
1. **Ramp removal + tied oracle** (field.py:1751; test_field.py). Checkpoint: `TestAlignReinsert` green on both arms; suite green.
2. **plane.py: `profiles`, `books`, `judge`, `pack_axis`, `readout`** with oracle tests (judge stair == `stair_energy(bar)`; judge pen == brute-force footprint counter over all lines; `pack_axis` output has zero overload on its own axis and preserves the order). Checkpoint: replace the engine call by "seeded orders → readout(1), readout(0), readout(1) → handoff"; K8/Z3 converts `certified=True` from a random order.
3. **The loop** (runs at all scales, bag, accept-all, memo, bookmark, stops, diag). Checkpoint: K8/K10 template, path-60 1.017, K100 7.26.
4. **N(v) units.** Checkpoint: turán 6.000 on 10/10 seeds within budget; `bookmark_asks` recorded. Pin the K_{8,8} one-move fact as a test.
5. **Shrink and delete**: placement.py to the handoff (~400 lines); `__init__.py` (drop costs/loop/`Factored`, rewrite the docstring); delete orders.py, seat.py, coarsen.py, costs.py, loop.py, and the dead half of field.py (`stair_step`, `edge_monotonize`, `xy_reinsert`, `_center_shift`, `pack_project`, `bar_domains`) and `source_positions`/`_landmark_cent`; delete tests test_orders.py, test_seat.py, test_coarsen.py, test_factored.py; rewrite the test_attraction.py assertions that name dead knobs/diag keys (listed in the review: `test_diag_reports_arm_gating_fields`, `test_stride_gate_byte_identity_off_zephyr`, `test_feasibility_fallback` → `max_asks=1`, `TestOrderState` → `plane.readout`); test_field.py: drop `TestStaircase.stair_step`, `TestArrangement`, `TestEdgeMonotonize`, `TestBarDomains`, re-target the two `pack_project` users; probe scripts under docs/paper2/data move to `docs/paper2/archive/` with a header note. Docs: CLAUDE.md, anatomy.md (rewrite for plane.py), ideas.md status, dp-internals §2 resolved, attraction.md ledger. Checkpoint: full suite green; harness byte-equal to step 4. Size target: package ≈ 3,900 lines including ball/polish/trees.
6. **Measurement**: the s3.126 instrument on the new engine (bag draws × random inits per cell; the claim is order-free and init-free within tolerance); then the standard 10-cell board paired by (instance, seed) against stock minorminer and the archived default, tail="none" and tail="mm".

## Tests to write

- `tests/algorithms/test_plane.py`: judge oracles (stair, pen); `pack_axis` invariants (zero own-axis overload, order preserved, integer in-window x, monotone values under the miss rule); readout determinism; no-op on untyped/n<3; bookmark `(pen, stair)` equals `judge` of the returned state; fixpoint stop; `max_asks` respected and seed-stable; N(v) on K_{8,8} interleaved → 2 runs in one accepted ask; e2e valid + deterministic on Z3 and C4.
- `test_field.py::TestAlignReinsert` tied arm (unramped rank-contact truth).
- `test_attraction.py`: rewrites per the review, plus the fingerprint test (K8/Z3 certified + template ACL) and `max_asks=1` legalization.

## Verification

Suite green after step 5; the fingerprint harness at every checkpoint; the instrument shows order- and init-freedom on the new engine; the paired board vs the archived default (worktree) and stock minorminer, pre-tail and tailed. Long runs via nohup to `docs/paper2/data/*.log` with the `done-probe` sentinel.

## Build log (what measurement changed after approval)

- **The ramp is a tiebreak that does real work.** Removed outright, the old engine falls from 1.017 to 1.5 on path-60 and the new engine to 1.35: on a path nearly every weave ties in true cost and preferring the smaller rank span is the drift that compacts the chain. Restored as an EXACT lexicographic tiebreak: values (and the other axis's values, and the bar) scaled by `rank_scale(n) = 2n²+1`, slot index added — a rank-span difference can never outweigh one unit of true cost. Oracles: accepted ⇒ true cost ≤ current and equal to the brute-force optimum. Old engine back to 1.017; new engine 1.05.
- **Single-axis readout is toxic.** After an x-move the rows stay as they were and are overloaded (cross-axis staleness); accept-all adopts the state; turán's bookmark then froze at the init for 15,000 asks on 3 of 10 seeds. The readout now re-packs the moved axis, then the other — the packer's guarantee on both axes, as the spec says. Turán: every seed in the crystal class within 1,500 asks.
- **A proposal the packer cannot seat is declined** (outside the valid set; not priced, not adopted). Never fired on turán after the readout fix; kept as the rule.
- Checkpoint 4 (new engine, tail none, work budgets; `plane_fingerprint_step4-plane2.json`): K8/K10/Z3 certified at the template; path-60 1.033 (old 1.017); K100 7.26 at a FIXPOINT in 1,370 asks (old: budget-bound at 10,000); **turán 6.000 on 10/10 random inits** (old: 3/10); grid_200 pre-tail 1.40 (old 1.87; old polished 1.33). Steps 0–4 done; step 5 (deletion) waits on the archive commit.

## Risks (from the review, carried)

Cross-axis staleness under single-axis readouts is priced by the judge, not repaired; a pen>0 bookmark is handed over as judged (the converter misses on absent lines, minorminer legalizes) — decided: hand over the judged state; Chimera/Pegasus change under stride-gated boundary zeroing; the `stepR` loop is the perf item at n≈500; determinism requires one seeded RNG and sorted iteration; `_ensure_seeds` still guarantees a qubit per variable.
