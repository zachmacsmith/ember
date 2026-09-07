# Open fronts (hand-off, written 2026-09-07)

Prioritized next steps for whoever continues the work, with what to
measure, what would falsify each idea, and where the code is. Sources:
the closing paragraph of `docs/paper2/notes.md` s3.127, the "Open
fronts" of `docs/paper2/ideas.md`, and a reading of the live code.
`HISTORY.md` in this folder explains how the design got here and lists
what was already refuted; check its §10 before proposing anything.

Code: `packages/ember-qc/src/ember_qc/algorithms/factored/` —
`plane.py` (engine: `profiles`, `books`, `judge`, `pack_axis`,
`readout`, `units`, `arrange`), `field.py` (kernels: `align_reinsert`
and its inner `_arm`, `pack_lines`, `arm_books`, `_stair_contacts`,
`stair_energy`, `wire_seeds_exact`, `complete_seeds`), `placement.py`
(`attract_embed`, the pipeline). Harnesses: `docs/paper2/data/
plane_fingerprint.py`, `rewrite_board.py`, `invariance_probe.py`, and
`docs/handoff/compare_baseline.py` against the frozen numbers in
`docs/handoff/baseline/`. Tests: `tests/algorithms/test_plane.py`,
`test_field.py`, `test_attraction.py`, `test_ball.py`.

## The owner's philosophy (each rule was paid for; receipts in HISTORY.md)

- **No penalty methods, no λ.** Finiteness and capacity are facts of
  the geometry, never a soft price. Capacity is the leading
  lexicographic key; a proposal the packer cannot seat is declined;
  the plane is extended past the chip so a valid state always exists.
  (s3.101 cap_pressure, s3.108b, s3.110: every weighted term either
  swamped the objective or was outvoted by it.)
- **Feasibility by construction, never repair.** Every state the search
  occupies is packer output. No clamps, no re-sorts, no fix-up passes
  inside the loop (s3.127 deviations list).
- **Proposer == judge, one accounting.** The books the packer packs are
  the books the judge prices and the converter seats. Two books were
  the source of most bugs (s3.113b, s3.124).
- **No mechanism names a graph type.** The crystal must emerge from
  general rules; there is no clique branch, no lattice branch
  (ideas.md §4.5).
- **The init must not matter.** The best optimizer wins from random;
  the init's only job is speed; a quality-changing init is a bug
  report against the optimizer (s3.120, s3.121b).
- **The question order must not matter.** Schedule sensitivity is a
  family/judge defect, measured with `sched_seed` draws (s3.126).
- **Budgets in work, never seconds.** `max_asks`; the clock was
  measured to be a parameter of the answer (s3.126, s3.127).
- **One switch per change, measured paired by (instance, seed)**
  against the shipped default and stock minorminer; **winners ship as
  defaults immediately**, losers are deleted with an archive commit.
- **Restrict the family, never the fidelity.** A restricted family
  judged exactly can only miss moves; a corrupted evaluation takes
  wrong ones (ideas_v3.112 §2.14).
- Notes contain ideas, algorithm-changing measurements and verified
  facts; seed-0 smoke is not a verdict; a number enters the record
  only with an artifact path (s3.74).

## 0. First: re-establish the fingerprint (an hour)

The s3.127 checkpoint table (notes, and `ideas.md`) quotes grid_200
pre-tail **1.40** and path-60 **1.033** — the step-4 file
(`data/plane_fingerprint_step4-plane2.json`). The step-5 file recorded
after the "extend both axes past the chip" fix
(`data/plane_fingerprint_step5-default.json`, also frozen in
`docs/handoff/baseline/`) reads grid_200 **1.605** (mx 6) and path-60
**1.067**; K100 7.26 and turán 6.000 on 10/10 are unchanged. `CLAUDE.md`
says "grid_200 pre-tail ≤ 1.76". Run `docs/handoff/compare_baseline.py`
on the current tree and pin the truth before using grid_200 as an
acceptance bar; if 1.605 is real, the strip fix cost the lattice 0.2
pre-tail and that is itself a measurement worth a line in the notes
(the s3.125 smoke had strip at 1.965 → post-tail 1.14, so the tail may
still recover it — check `new+mm` grid, 1.29 on the board).

## 1. Per-ask cost (the wall-clock arm's bottleneck)

**What is slow.** `align_reinsert._arm` in `field.py` (around lines
1691–1890): on axis 1 the `stepR` loop `for i in range(1, p+1)` and
the `stepQ` loop `for j in range(1, m+1)` are Python iterations, each
doing several small numpy calls (searchsorted, suffix max/min,
concatenate) — O(p) Python steps per arm, two arms (forward and
reversed) per ask. Also Python-looped per ask: the shared neighbour
setup `for t in range(n)`, the `_rect` scatter over all n variables
(both axes, both arms), the backtrack. For a singleton unit at n = 486
that is ~500 iterations × ~10 numpy calls × 2 arms ≈ tens of ms —
`ideas.md` quotes ~35 ms/ask; s3.126 measured ~40 asks/s on ws (turán
~110, grid ~130). Per adopted ask, `plane.arrange` then runs two
`readout`s (two `pack_lines` calls, three `books` computations — one
before the first pack, one after each pack) and a `judge` whose
overload loop is Python over every claim interval.

**Plan.** (a) Vectorize `stepR`/`stepQ`: the suffix extrema of
neighbour x-values over indices ≥ j are step functions with deg(v)
breakpoints; scatter each row's Q-neighbour x-values into a (p+1)×(m+1)
array and take `np.maximum.accumulate` / `np.minimum.accumulate` along
the reversed column axis (the R-side scalar per row is a single
searchsorted + suffix-extremum vector computed once per arm). The
`rrow_max` precomputation already does this for the Q rows; do the
same for R rows. (b) Replace the `_rect` loop with `np.add.at` on the
diff array. (c) Books: on an x-move the y-order is untouched, so the
contacts of the candidate equal the current contacts — pass them and
recompute only the hulls; the post-pack books can share the same
contacts. (d) `judge`: build the cover arrays by `np.add.at` per
orientation instead of the per-tuple loop. (e) `units()` emits one
N(v) tuple per variable; on twin-heavy graphs (turán: 81 identical
N(v)) the same tuple is asked repeatedly after every accept — dedupe
in `units()` (`arrange` already builds `nbr_units` as a set).

**Measure.** `diag["asks"] / diag["arrange_wall"]` on ws_n486 (and
turán, grid) at `tail="none"`, `max_asks=15000`, before and after;
report readouts/s too. The oracles in `test_field.py` (brute-force
interleaver, tied and distinct values, `bar=2`) and `test_plane.py`
must stay green, and `compare_baseline.py` must print "same" on every
cell — a vectorization that changes any fingerprint is a bug, not a
trade.

**Falsifier.** If asks/s on ws does not at least double, the Python
loops were not the cost; profile (`cProfile` around `arrange`) before
touching anything else. If the fingerprints move, the change altered
tie-breaking (`CH` prefers the R-step on ties; the reversed arm must
beat forward by 1e-12) — restore exact tie behaviour.

## 2. The sparse reach on ws / regular / king

**The facts.** At a full work budget the engine's own pre-tail on ws
is 4.40 with max chain 27 (board: `rewrite_board_new-newmm.csv`),
worse than the old engine from its spectral init (3.76) and comparable
to the old engine from a random init (4.18). The invariance map:
regular order range 0.54, ws order 0.39 / init 1.01, king init 0.32;
every regular/ws run stopped by `max_asks` (15k ≈ 4 passes on ws).
The init carried +0.3–0.4 on exactly these three cells in every
instrument since s3.120; by the separation principle the optimizer
must earn that itself.

**First discriminator (cheap, do it before any design).** Double and
quadruple the budget on ws/regular/king (`rewrite_board.py` with
BUDGET × 2, × 4; or `invariance_probe.py draws=5` at the larger
budgets). If the spread collapses and ACL falls toward 3.8 on ws, the
sensitivity was unfinished descent and front 1 is the whole answer.
If ACL plateaus with max chain still ~27 and the spread stays, the
family is the ceiling. Read `bookmark_asks` vs `asks` and
`accept_traj` (accepts per pass) — a pass count that never reaches a
fixpoint at 60k asks says the family churns.

**Candidates, in the order the notes rank them.**

- *More passes / cheaper asks* — front 1.
- *Unit families.* Today: contiguous runs of each order at dyadic
  scales, plus N(v). The old engine's hierarchy units gathered
  scattered similar nodes (ER 5.31 → 4.907, s3.115) and the s3.127
  audit measured `hier_units` as the best turán arm; N(v) replaced
  them. Graph-side units at radius 2 (N(N(v))) or BFS balls of size
  k are order-independent, need no hierarchy, and are one line in
  `plane.units`. Falsifier: paired board, ws/regular/king pre-tail
  must drop beyond tol with turán still 6.000 on 10/10 and K100 at a
  fixpoint (the s3.116 `hier_units` toxicity on the crystal is the
  hazard to watch: turán 10.9).
- *Abutment.* The plane's family is one cross per variable; the
  product topology's grid half — two chains meeting END TO END on the
  same lane via an external coupler — is unused. On lattices and
  liquids minorminer's gain is largely single-orientation chains
  (grid: 96 two-bar crosses → single bars, s3.125). Abutment would let
  two variables share a lane segment-to-segment with no crossing. It
  touches the books (`arm_books`: a hull may end where a neighbour's
  begins), the converter (`_convert_line` seating adjacent intervals
  on one wire) and the judge (no bar for a crossing that is an
  abutment). Design discussion first; falsifier as above, and the
  certificate must still fire (`certified` True, `extensions` 0).
- *Junction packing.* Several short chains sharing a junction's 8×8
  wires more tightly than the per-brick pool models — the converter
  (`_convert_line`) already decides this exactly per line; the
  question is whether the packer's per-brick pool is the binding
  approximation on ws. Measure first: on the ws bookmark, compare
  `pen` (0) against `convert_miss` and `deficit_edges`; if the
  converter misses while the judge says pen 0, the books under-book
  and junction packing is not the issue.
- *Long chains specifically.* `legal_max_chain` 27 on ws is the tail
  of a distribution; s3.106's lesson is that the tail separates while
  the mass does not. Before adding a max-chain key (front 5), look at
  which variables own the long chains (`max_edge_span` in diag; the
  bookmark's `bars` and hull widths via `bar_widths`) — if they are
  the WS shortcut endpoints, this is the fold (s3.87), which no
  single-variable or set move has reached at plane resolution
  (s3.121, s3.123).

## 3. The wall-clock arm (the shipped shape)

`placement.py`: with a `timeout` and `tail="mm"`, the engine gets
`TAIL_SPLIT = 0.5` of the wall and the tail the rest. At 60 s the
engine finishes a fraction of a pass on ws (~1,200 asks at 40/s
against ~5,000+ units per pass) and hands minorminer a barely-moved
random state; that is why `new+mm` loses to `old` on regular/ws/king
(3.61 vs 2.78, 3.34 vs 2.56, 2.11 vs 1.83) while winning everything
dense.

**Measure.** For ws/regular/king, ACL of `new+mm` as a function of the
engine's share: run the engine to its fixpoint or `max_asks` with no
deadline, then give the tail a fixed 30 s — is the engine's full
answer a better seed for minorminer than its 30-second answer? And the
reverse: stock minorminer at 60 s vs minorminer warm-started from the
engine's fixpoint at 30 s. Pointers: `attract_embed(timeout=...,
max_asks=...)`; `_mm_route(warm=...)` is the grind; `legal_acl` is
the pre-tail number.

**Falsifier.** If the fixpoint seed does not beat the 30-second seed
by more than the tail's own spread, the wall-clock loss is front 2,
not a budget split, and no split will fix it. If it does, front 1
buys it directly and the protocol of front 6 should report it.

## 4. Pegasus (parked)

State: the engine runs on P16 (`TileGrid` builds; stride 1, so the
boundary-line zeroing and the exactness path are off), but the
converter, completion and certificate are gated to stride 2
(`placement.py`: `stride2`, `eff_exact`, `eff_snap`), and every
cover-count objective assumes crossing = coupler, which is false on
Pegasus's ~56%-complete junctions (fabrics.md §3; s3.89, s3.103,
s3.111b: every seat-family arm was "toxic" there). Max wrote it off at
s3.112. Unblock condition (ideas.md): an elegant adapter — a
coupler-predicate cover accounting shared with the Zephyr machinery,
not a parallel engine. If it is ever picked up: first measure how the
plane's `pen`/`stair` relate to real deficits on P16 K100 and P16 ws
(the two cells the old records track), then decide whether the
predicate belongs in `profiles()` (a per-(line, brick) pool that
already knows which crossings exist) or in the books.

## 5. Max chain as a third lexicographic slot (parked)

Never built. The judge is `(pen, stair)`; a third key `max chain`
would make the engine prefer, among equal-length layouts, the one
with the shortest worst chain. Cautions on record: principle 13 (wins
must not buy fatter tails) says report max chain next to ACL, not
optimize it; s3.83 ("sum vs max dogma") and s3.106 (the separating
term was a sum with the benign unit exempted, not a max). As a THIRD
key it is a tiebreak only, so it cannot hurt ACL; the question is
whether it does anything. Build: `judge` returns `(pen, stair, mx)`
with `mx` the largest active-arm span + bar (from `bk[1]`); the
interleaver cannot price it, so it only re-selects the bookmark and
steers nothing under accept-all (the s3.124 lesson). Falsifier: paired
board, `legal_max_chain` must drop on ws/regular without ACL rising
beyond tol; if it only re-selects among equal states and the max does
not move, delete it.

## 6. A work-budget-only benchmark protocol

Today's board mixes currencies: `new` is at a work budget, `mm` and
`old` are at 60 s wall, `new+mm` is the engine at a work budget inside
a 60 s wall with the tail on the clock. Every "wall flag" and
"deadline jitter" caveat in the notes since s3.110 came from this.
Proposal: (1) the engine's answer is ALWAYS reported at `max_asks`
with no deadline (`tail="none"`, `legal_acl`, `legal_max_chain`,
`bookmark_asks`, `stopped_by`); (2) the tail is measured separately,
warm-started from that answer, at a fixed wall (minorminer has no
work knob; `ball_polish` has `tried`); (3) stock minorminer's number
is a wall number and is labelled as such. Then two runs of the same
config at different box loads must agree exactly on (1) — that is the
protocol's own falsifier, and the `invariance_probe.py` rows already
carry `stopped_by` to check it. Per-cell budgets live in
`rewrite_board.py` (`BUDGET`); keep them with the results.

## 7. Other things found while reading the code

- **Hygiene items from `dp-internals.md` still present in the live
  kernels**: the pack DP's deque pops ties with `>=` (prefers the
  shortest run on the current line — an unrecorded bias), `_MISS_COST`
  is a hard-coded 1e6 sized for a retired objective, and
  `_brick_pool_arrays` still emits a trailing pool-0 brick column
  (`plane._cover_bricks` clamps to the last capacity-bearing brick and
  `_line_profiles` trims to it before extending, so it is neutralized in
  the judge and the search and live only in the bounded projection). None
  is known to change a number; each is a one-line measured flip.
  Resolved by construction in the rewrite: the id-collapse, the
  interleaver tie regime under rank contacts (s3.127: 0 bad accepts),
  the ramp (now an exact tiebreak), monotonize's blind spot (deleted),
  boundary zeroing (gated to stride > 1).
- **`infeasible` should be zero now.** Since both axes are extended
  past the chip, `pack_axis` should never miss during search; if
  `diag["infeasible"]` is non-zero on any cell, proposals are being
  silently discarded and the L_max extension (`_line_profiles`:
  `extra` lines) is short somewhere. Check it on the board CSVs.
- **`adopt_worse`** is reported but unused; under accept-all it is
  the count of proposals the judge disagreed with. Its ratio on ws vs
  turán is the cheapest reading of how stale the frozen picture is on
  sparse cells (s3.127 deviation 6 measured 7% at the init, 40% at
  the crystal before the both-axes readout).
- **The bounded projection** (`arrange`, `pen > 0` branch) is the one
  remaining repair-shaped step: stragglers take their predecessor's
  line and are counted (`proj_misses`). On the board every Z12 cell
  ended at pen 0, so it never fired; if a larger instance does fire
  it, the converter sees a clamped layout and the certificate fails —
  that is the expected, honest outcome, not a bug.
- **Unknown kwargs are ignored** by `attract_embed`; a misspelled
  parameter silently measures the default. There is no typo fence.

## What "done" looks like for the next milestone

The board `rewrite_board.py` re-run with fronts 1 and 6 in place: the
`new` arm at a work budget on every cell, the `new+mm` arm with the
tail warm-started from the engine's fixpoint; the target is
regular/ws/king at or below the old engine's polished numbers (2.78 /
2.56 / 1.83) with turán still 6.000 on 10/10, K100 7.26 at a fixpoint,
and the invariance map order- and init-free within tol on all ten
cells. Anything that gets there ships as the default; anything that
does not is deleted with an archive commit and one line in the notes.
