# Anatomy of the attraction embedder (s3.127, the rewrite)

The pipeline as built. If a "how" here is not enough to re-implement
the piece, that is a bug in this file. Code map: `plane.py` (the
engine, ~400 lines), `field.py` (the fabric adapter and the exact
kernels), `placement.py` (the pipeline and the registry entry),
`polish.py` (spur pruning), `ball.py` + `trees.py` (the ball pass of
the tail).

## 0. The hardware in four facts (measured; fabrics.md)

1. A qubit is a **bar** on a lane; couplers exist where bars cross
   (internal), abut end to end (external), or run parallel one step
   apart (odd).
2. A line carries a fixed number of **wires** (8 on course-resolved
   Zephyr), counted per **brick** (the parity period: 2 junctions on
   Zephyr, 1 elsewhere).
3. Junctions are **complete** on Zephyr, so "my run crosses your run"
   is "we are coupled" — a zero-deficit completion is a proof of
   validity. Pegasus junctions are ~56% complete: the exactness path
   is gated to stride 2.
4. The two **boundary lines** of each orientation carry one course
   parity only; their pools are zero on course fabrics.

## 1. The pipeline (placement.py)

1. `TileGrid` over the target (lanes, wires, bricks; `stride` = 2 on
   course-resolved Zephyr).
2. `plane.arrange(src_adj, grid, seed, max_asks, deadline, snap,
   sched_seed)` → the bookmark's positions and books.
3. Seeds: `wire_seeds_exact` (stride 2) or `wire_seeds_iv`, from the
   bookmark's books — the same books the engine judged.
4. `complete_seeds` (stride 2): corner, edge and bridge passes by
   interval arithmetic; `deficit_edges == corner_deficit == 0` and a
   passing validity check ⇒ the embedding, minorminer skipped.
5. Otherwise minorminer legalization seeded with the chains, then one
   nearest-qubit-seeded fallback.
6. `spur_prune`, then the tail: `tail="mm"` = minorminer's warm grind
   then `ball_polish`; `tail="none"` = the legal embedding as is.
7. The result dict: `embedding`, `time`, `stair_E`, `legal_acl`
   (pre-tail), `diag`.

Wall: with a `timeout` and a tail, the engine and legalization get the
first half (`TAIL_SPLIT`), the tail the rest; the engine's real stop is
`max_asks` or its fixpoint, and `stopped_by` says which fired.

## 2. The engine (plane.py)

**State.** Two orders `ox`, `oy` over the variables. Init: two
permutations from `default_rng(seed)`.

**Profiles** (`profiles(grid)`): the capacity book, `(ph, pv)` per
(line, brick) from `_brick_pool_arrays`, boundary lines zeroed when
`stride > 1`. The packer packs against it (extended past the chip with
the ideal pool) and the judge prices against it (pool 0 off-chip).

**Books** (`books`): `_stair_contacts(pos, yrank)` — the endpoint
lower in the y-order reaches sideways (its h-contacts), the higher
reaches down (its v-contacts) — then `arm_books(floor=False,
min_span=0, snap, ybound=False)`: bars = hulls of the contacts plus
the own seat; tuples = the claim intervals `(line, a, b, v)` per
orientation, every arm at least one tile. No capacity floor from a
degree heuristic: capacity is the derived reach, enforced by the
packer.

**Readout** (`readout(axis, orders, pos)`): books on the current
positions; `pack_axis`: each line takes a contiguous run of the
carried order, feasible iff the run's intervals fit the line's brick
profile; cost = the true stair objective linearized by `_axis_coeffs`
(exact for any assignment monotone in the order); `pack_lines`
(`_pack_dp` + `_jstar_profile` + `_seg_radd`). Columns are the chip's
real columns extended along their bricks past the chip; rows are the
chip's rows plus enough uniform rows to seat everyone. A variable the
DP cannot seat takes its predecessor's line and is counted. Positions
are rewritten as integer-valued floats; books again on the result.
After a move, the moved axis is re-packed first, then the other.

**Judge** (`judge`): `(pen, stair)`. `pen` = Σ over (orientation,
line, brick) of max(cover − pool, 0)² over the tuples, using the
pack's own brick rule (hull [a,b] covers bricks floor(a/s)..floor(b/s),
clamped to the last capacity-bearing brick on chip lines). `stair` =
`stair_energy(bar=stride)` = Σ active-arm spans + stride per active
arm. Integers; tuple comparison.

**Units** (`units`): on each axis, every contiguous run of the current
order at scales n/2, n/4, …, 2, 1 (half-overlapping) and every N(v).
One `default_rng(sched_seed)` permutation of the whole list per pass.

**Move.** `align_reinsert(order, unit, vals, other, contacts, bar)`:
the interleaver DP prices every merge of the rest and the unit
(forward and reversed) under the frozen picture — on axis 1 contacts
re-derived per candidate by the induced rule, on axis 0 contacts
frozen — and returns the best weave iff it strictly improves the
scaled objective `true_cost × rank_scale(n) + total rank span`
(`rank_scale = 2n²+1`: rank span is an exact lexicographic tiebreak).
Memo: a (unit, axis) declined at the current state version is not
re-asked until an accept.

**Loop.** For each unit in the bag: memo check → ask → readout (moved
axis, then the other) → if the packer missed, decline → judge → adopt
(every proposal) → bookmark by `(pen, stair)` → state version += 1.
Stop: zero-accept pass (`fixpoint`), `asks ≥ max_asks` (`asks`), or the
deadline (`deadline`). Returns the bookmark's positions, its books, and
the diagnostics (`asks`, `accepts`, `passes`, `bookmark_asks`,
`stopped_by`, `pen`, `stair`, `bars`, `misses`, `adopt_worse`,
`infeasible`, `accept_traj`).

Untyped targets and n < 3: the engine returns rank positions and the
router does the work.

## 3. The exact kernels (field.py; all brute-force oracle-tested)

`_stair_contacts`, `_bars_arrays`/`arm_books`, `stair_energy`,
`_axis_coeffs`, `pack_lines` (`_pack_dp`, `_jstar_pass`,
`_jstar_profile`, `_seg_radd`), `align_reinsert`, `_convert_line` /
`wire_seeds_exact` (parity classes, required hulls, lane seating),
`complete_seeds` (corner / edge / bridge passes), `spur_prune`.

## 4. Diagnostics worth reading

`legal_acl` and `legal_max_chain` (the engine's own answer before any
tail), `certified` (every arm seated its required hull and completion
closed), `mm_skipped`, `pen` (0 ⇒ the bookmark fits the chip),
`bars` (active arms; n ⇒ every variable one-sided), `bookmark_asks`
vs `asks` (work-to-answer), `stopped_by`.
