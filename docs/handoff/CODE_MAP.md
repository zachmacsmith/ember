# CODE_MAP — the live package, function by function

Package: `packages/ember-qc/src/ember_qc/algorithms/factored/` on branch
`factored` (HEAD `39cffd06`, 2026-09-07, plus one uncommitted change in
the working tree on that date: `plane.units` asks one question per
*distinct* neighbourhood, +5 lines, described under `units` below).
Line numbers were read from that working tree; if a number is off by a
few lines after later edits, search for the function name.

```
   858  ball.py        the ball pass of the tail (composite chain re-embedding)
  1901  field.py       the fabric adapter and the exact kernels
    42  __init__.py    the registry entry (`attraction`)
   292  placement.py   the pipeline: attract_embed
   468  plane.py       the engine: two orders, packer, judge, interleaver loop
   185  polish.py      spur pruning (and an unused shorten/polish pair)
   156  trees.py       Steiner-tree chain assembly for the ball pass
  3902  total
```

Conventions used throughout the package:

- **orientation** `o`: `1` = horizontal (an h-arm runs along x on a
  *row* line), `0` = vertical (a v-arm runs along y on a *column*
  line). **axis** `ax`: `0` = x, `1` = y. The packer for axis 1 assigns
  rows and consumes orientation-1 tuples; axis 0 assigns columns and
  consumes orientation-0 tuples.
- `src_adj`: `{v: sorted list of neighbours}` for the source graph;
  `adj`: `{qubit: tuple of neighbour qubits}` for the target
  (`ember_qc.embedding_backend.build_adjacency`).
- "books" always means the triple returned by `arm_books` (see Data
  shapes).
- s3.NNN references are entries of `docs/paper2/notes.md`.

---

## 1. Data shapes

**`pos`** — `Dict[int, np.ndarray]`, one `np.array([x, y])` of two
floats per source variable. In the engine the values are
*integer-valued* line indices: `x` is the column line, `y` the row
line, in tile space (`TileGrid` coordinates). `plane.arrange` returns
such a dict; `tests/algorithms/test_attraction.py::test_positions_are_integer_line_indices`
pins integrality and `0 <= x <= W-1`. `y` is *not* clipped to the chip
during the search (rows past the chip are priced by the judge); after
the bounded projection (`arrange`, lines 438–459) both axes are on the
chip.

**orders** — `Dict[int, List[int]]`: `orders[0]` is the x-order (a
permutation of the variable ids, ascending column), `orders[1]` the
y-order. `rank_of(order)` gives `{v: rank}`. The *only* state of the
engine is the pair of orders; positions are derived from them by the
packer.

**the books triple** `(contacts, bars, tuples)` from `arm_books`:

- `contacts`: `{v: (h_us, v_us)}` — two lists of neighbour ids.
  `h_us` are the neighbours whose *columns* v's h-arm must reach (v is
  lower in the y-order than each of them: the stair rule); `v_us` are
  the neighbours whose *rows* v's v-arm must reach (v is higher than
  them). Every edge appears in exactly one endpoint's `h_us` and the
  other's `v_us`.
- `bars`: `{v: (np.array([hmin, hmax]), np.array([vmin, vmax]))}` —
  the h-hull (columns spanned: own x plus the x of every `h_us`) and
  the v-hull (rows spanned: own y plus the y of every `v_us`). With
  `snap=True` the hulls are not widened here (the widening goes into
  `tuples`); with `floor=True` (never in the engine) a degree-based
  kappa floor widens them.
- `tuples`: `{1: [(line, a, b, v), ...], 0: [(line, a, b, v), ...]}` —
  the claim intervals, one per *participating* arm. For orientation 1
  the tuple says "variable v claims positions `[a, b]` along row
  `line`" with `line = rint(y_v)`; for orientation 0, `[a, b]` along
  column `line = rint(x_v)`. Participation: `(hi - lo) >= min_span`;
  with the engine's `min_span=0` every arm participates and a
  zero-width arm is widened to `[a, a+1]` (the one-tile footprint).
  With `snap=True` (stride-2 fabrics) `[a, b]` is widened to
  `[min(a, ln_min-1), max(b, ln_max)]` where `ln_min/ln_max` are the
  rounded lines of the contacts plus the own corner — the parity-
  agnostic hull the converter will actually claim.

**`TileGrid`** (`field.py` 136–213) attributes:

| attribute | meaning |
|---|---|
| `graph` | the target `nx.Graph` (reference; coupler lookups) |
| `W`, `H` | number of column lines and row lines (Zephyr `(m, t)`: `W = H = 2m+1`; Z12 is 25 × 25) |
| `stride` | tile-along step between consecutive qubits of one wire run: 2 on course-resolved Zephyr, 1 elsewhere |
| `typed` | `True` when the family was recognised (chimera / pegasus / zephyr); `False` = untyped fallback bins |
| `wire_map` | `{(orientation, line, sub): {along: qubit}}` — every physical wire (lane) keyed by orientation, the line it lies on and its sub-lane index; the inner dict maps tile-along position to the qubit sitting there (stride-2 lanes hold one parity of positions only) |
| `sub` | per-qubit sub-lane index array (aligned with `qubits`) |
| `orient` | per-qubit orientation array |
| `qubits`, `coords` | sorted qubit ids and their drawing coordinates |
| `M`, `c`, `Minv` | affine fit drawing → tile space (`to_tile(p) = M @ p + c`) |
| `cap` | `(H, W, 2)` per-tile pool counts (legacy census; the engine uses `profiles`) |
| `_plane_profiles`, `_brick_pools`, `_line_pools` | memo caches written by `plane.profiles`, `_brick_pool_arrays`, `line_pools` |

**`profiles(grid)`** → `(ph, pv)`: `ph` has shape `(H, ceil(W/s))` —
row `r`, brick `b` = number of wire slots on row line `r` in brick
`b`; `pv` has shape `(W, ceil(H/s))` for column lines. Interior Z12
lines carry 8 per brick; the two boundary lines of each orientation are
zeroed when `stride > 1`.

**The result dict of `attract_embed`** (success):

```
{"embedding": {v: [qubits]},   # the finished (post-tail) embedding
 "time": float,                # wall seconds, whole call
 "stair_E": float,             # stair_energy of the bookmark, bar=0, 1 dp
 "legal_acl": float,           # mean chain length after legalization + spur_prune, BEFORE the tail
 "diag": {...}}                # below
```

Failure: `{"embedding": {}, "time": ..., "success": False, "status":
"FAILURE"}` plus `error` (the exception text) when an exception was
caught, or `stair_E` when the router failed after a successful arrange.
`attract_embed` never raises.

**`diag` keys** (placement.py 243–284), in the order they are written:

| key | meaning |
|---|---|
| `extent_mean`, `extent_max` | mean / max over variables of (h-hull width + v-hull width) of the bookmark's `bars`, in tiles |
| `stride` | `grid.stride` (2 on course Zephyr, 1 on Chimera/Pegasus/untyped) |
| `max_chain` | longest chain of the *finished* embedding |
| `arrange_wall` | seconds spent in `plane.arrange` |
| `legal_acl`, `legal_max_chain` | pre-tail mean and max chain length (same `legal_acl` as the top-level key) |
| `asks` | DP evaluations (`align_reinsert` calls) the engine made |
| `accepts` | proposals adopted (every non-declined proposal is adopted) |
| `passes` | bag passes started |
| `readouts` | packer readouts: 3 for the first picture, then 1 or 2 per proposal that reached the packer (a proposal declined as infeasible still counts its readouts); the bounded projection's three readouts are not counted |
| `bookmark_asks` | the ask count at which the best `(pen, stair)` was last improved — work-to-answer |
| `bookmark_wall` | seconds into `arrange` at that moment |
| `stopped_by` | `"fixpoint"` (a pass with zero accepts), `"asks"` (budget), `"deadline"`, `"trivial"` (n < 3 or untyped target: engine no-op), `"moves-off"` (only with `moves=False`) |
| `pen` | the bookmark's capacity overload (sum of squared per-(line, brick) overload; 0 = fits the chip) |
| `stair` | the bookmark's stair objective *with* the bar term (`bar = stride`) — differs from top-level `stair_E`, which is bar-free |
| `bars` | number of active arms in the bookmark (`n` means every variable is one-sided, the crystal) |
| `misses` | packer misses recorded with the bookmark — see Rough edges |
| `adopt_worse` | adopted proposals whose judged `(pen, stair)` was worse than the current state |
| `infeasible` | proposals declined because the packer could not seat everyone |
| `accept_traj` | per-pass accept counts, first 12 passes |
| `max_edge_span` | max over source edges of the L1 distance between endpoint positions (tiles) |
| `convert_miss` | stride 2 only: arms `_convert_line` could not seat on their required hull |
| `certified` | stride 2 only: `convert_miss == 0 and deficit_edges == 0 and corner_deficit == 0` — the constructive proof of validity; `TestCertificate` checks it against `validate_embedding` |
| `mm_skipped` | stride 2 only: the certified chains were used as the embedding without any minorminer call |
| `deficit_edges`, `corner_deficit`, `extensions`, `ext_qubits`, `bridges` | stride 2 only: `complete_seeds` counters — uncovered source edges left, variables whose own runs could not be joined, edge extensions made and qubits they added, 1-/2-qubit bridges added |
| `ball_accepts`, `ball_tried`, `ball_wall` | `tail="mm"` only: `ball_polish` accepted / tried counts and seconds |

Keys of `arrange`'s `info` that are **not** copied into `diag`:
`wall`, `orders`, `yrank`, `projected`, `proj_misses`, `trace`.

---

## 2. Call graph from `attract_embed`

```
Attraction.embed                                   __init__.py 36
└─ attract_embed(source, target, *, timeout, seed, max_asks, sched_seed, tail)   placement.py 111
   ├─ build_adjacency(target)                      embedding_backend
   ├─ target_layout(target)                        placement.py 56
   ├─ TileGrid(target, pos, fallback_bins=_auto_bins(nq), courses=True)   field.py 136
   │  └─ _tile_orient(target, courses=True)        field.py 57
   ├─ plane.arrange(src_adj, grid, seed, max_asks, deadline, snap, sched_seed)   plane.py 299
   │  ├─ [n<3 or untyped] arm_books(..., contacts=_stair_contacts(...), ybound=True) → "trivial"
   │  ├─ readout(ax, ...) ×3 for ax in (1, 0, 1)   plane.py 236   (the first picture)
   │  │  ├─ books(pos, src_adj, grid, yrank, snap)  plane.py 81
   │  │  │  ├─ _stair_contacts(pos, src_adj, yrank) field.py 237
   │  │  │  └─ arm_books(pos, src_adj, grid, kappa=1, floor=False, snap, min_span=0, contacts, yrank, ybound=False)   field.py 815
   │  │  │     └─ _bars_arrays(...)                 field.py 305
   │  │  └─ pack_axis(axis, order, pos, bk, grid, ranks, bounded)   plane.py 199
   │  │     ├─ _line_profiles(axis, grid, items, s, bounded)   plane.py 163
   │  │     │  ├─ profiles(grid)                    plane.py 39  → _brick_pool_arrays(grid, s)  field.py 890
   │  │     │  └─ ideal_pool(grid)                  plane.py 68  → line_pools(grid)  field.py 923
   │  │     ├─ _axis_coeffs(contacts, pos, axis, ranks)   field.py 1210
   │  │     └─ pack_lines(intervals, values, pools, coeffs, brick=(s, prof))   field.py 1387
   │  │        ├─ _jstar_profile (njit)             field.py 1299  → _seg_radd  field.py 1244
   │  │        └─ _pack_dp (njit)                   field.py 1332
   │  ├─ judge(bk, pos, src_adj, grid, bar=stride)  plane.py 109
   │  │  ├─ _cover_bricks                           plane.py 98
   │  │  └─ stair_energy(pos, src_adj, contacts, bar)   field.py 370
   │  ├─ loop:  units(orders, src_adj, rng)         plane.py 261
   │  │   per unit: align_reinsert(order, unit, src_adj, vals, None, axis, other, contacts, bar)   field.py 1515
   │  │             readout(ax) ; readout(1-ax, bk=bk2) ; judge ; adopt ; bookmark
   │  └─ [pen > 0] readout(ax, bounded=True) ×3 for ax in (0, 1, 0)   (the bounded projection)
   ├─ stair_energy(tpts, src_adj, contacts=books[0])   → stair_E
   ├─ [stride 2] wire_seeds_exact(grid, tpts, books[1], src_adj, books)   field.py 786
   │  ├─ _arm_targets(pos, contacts, bars, o, present)   field.py 622
   │  ├─ _convert_line(grid, claimed, chains, o, line, items, targets)   field.py 641   (per line)
   │  └─ _ensure_seeds(grid, claimed, chains, pos)   field.py 517 → _nearest_free  field.py 407
   ├─ [stride 1] wire_seeds_iv(grid, tpts, books[1], src_adj, snap=False, books)   field.py 529
   │  ├─ _color_claim_bars(grid, claimed, chains, o, tuples[o], targets)   field.py 425
   │  └─ _ensure_seeds
   ├─ [stride 2] complete_seeds(grid, seed_chains, src_adj, adj)   field.py 943
   ├─ [certified] emb = seed_chains, mm_skipped = True
   │  [else]      _mm_route(source, target, chains=seed_chains, seed=seed*100, timeout=cap)   placement.py 90
   │  [else]      snap(cent, coords, qubits, degree_order)  placement.py 71 ; _mm_route(chains=fb, seed=seed*100+99)
   ├─ spur_prune(emb, src_adj, adj, deadline)        polish.py 43
   ├─ [tail == "mm"] _mm_route(source, target, warm=emb, seed=seed, timeout=remaining)
   │                 ball_polish(finished, source, target, deadline, adj, grid)   ball.py 701
   │                 ├─ _hull_balls(work, src_adj, grid, rev)   ball.py 52
   │                 ├─ _trim_ball(S, src_adj)                   ball.py 130
   │                 ├─ _rebuild_ball_bars(S, work, src_adj, adj, grid, deadline, rng, rev)   ball.py 524
   │                 │  ├─ _stair_contacts ; _audit_claim (ball.py 193) ; complete_seeds(only=S)
   │                 ├─ _rebuild_ball(S, work, src_adj, adj, visits, deadline, rng)   ball.py 156
   │                 │  └─ sph_tree → _assemble                 trees.py 140 / 57
   │                 └─ spur_prune(trial, only=S)
   └─ bar_widths(books[1])                           field.py 395   (diagnostics)
```

`is_valid_embedding(emb, source, target, adj=adj)` (embedding_backend)
is the paranoia net at three points: before `mm_skipped`, after the
warm minorminer grind, after `ball_polish`.

**Registry.** `ember_qc/registry.py`: `ALGORITHM_REGISTRY: Dict[str,
EmbeddingAlgorithm]`; `register_algorithm(name)` (line 35) instantiates
the decorated class and stores it under `name`, also setting
`cls.name`. `ember_qc/algorithms/__init__.py` imports every algorithm
module for its side effect (line 9: `from ember_qc.algorithms import
factored`). `factored/__init__.py` (lines 26–42) registers
`@register_algorithm("attraction") class Attraction(EmbeddingAlgorithm)`
with `version = "0.3.0"`; `Attraction.embed(source, target, timeout=60.0,
**kwargs)` pops `seed` (None → 0) and calls `attract_embed(...,
timeout=timeout, seed=int(seed), **kwargs)`. So `ember run` with
algorithm `attraction` and the CLI's per-trial seed reaches
`attract_embed` with that seed; any other YAML parameter is forwarded as
a kwarg. `ALGORITHM_REGISTRY["attraction"].embed(...)` is what
`tests/algorithms/test_algorithm_contracts.py` exercises.

---

## 3. The parameter surface

```python
attract_embed(source_graph, target_graph, *,
              timeout=300.0, seed=0, max_asks=None, sched_seed=None,
              tail="mm", **ignored) -> dict
```

| parameter | meaning |
|---|---|
| `timeout` | wall-clock safety net in seconds. `0`/`None` → no deadline for the engine; each minorminer call then gets `FALLBACK_TIMEOUT = 60` s. With a timeout and `tail="mm"`, the engine and legalization get the first `TAIL_SPLIT = 0.5` of it, the tail the rest; with `tail="none"` the engine may use all of it. The engine's *real* stop is `max_asks` or its fixpoint; `stopped_by` says which fired. |
| `seed` | seeds the init (`np.random.default_rng(seed)` → two permutations, `arrange` 322–324) and, by default, the bag; also derives the minorminer seeds (`seed*100` legalization, `seed*100+99` fallback, `seed` for the warm grind). |
| `max_asks` | the work budget: the number of `align_reinsert` evaluations after which the engine stops (`stopped_by == "asks"`). `None` = unbounded (fixpoint or deadline). Must be `>= 1` (else `FAILURE` with an error). |
| `sched_seed` | seeds the per-pass shuffle of the question bag (`arrange` 327). `None` → `seed`. Varying it at fixed `seed` measures order sensitivity; varying `seed` at fixed `sched_seed` measures init sensitivity. `test_sched_seed_is_independent_of_seed` pins that `sched_seed=seed` is the default. |
| `tail` | `"mm"` (default; the shipped shape): after legalization, minorminer's warm-started grind (`skip_initialization=True`) and then `ball_polish`; `"none"`: the legal embedding as is — the engine's own answer. Anything else → `FAILURE` with an error. |
| `**ignored` | **any unknown keyword is silently swallowed** (`test_unknown_kwargs_ignored_and_bad_values_fail_loudly` pins it). A misspelled `max_ask=` or `shed_seed=` measures the default. Check `diag["asks"]`/`stopped_by` when in doubt. |

Determinism: the result is a function of `(source, target, seed,
sched_seed, max_asks)` when `stopped_by` is `"fixpoint"` or `"asks"`;
`"deadline"` stops (and the wall-bounded minorminer calls in the tail)
depend on the machine.

---

## 4. Fabric gates (decided once, in `attract_embed` 151–161)

`TileGrid(..., courses=True)` always; `stride2 = grid.stride > 1`;
`eff_exact = eff_snap = stride2`. `field.py` and `plane.py` never
inspect the fabric family themselves — everything they need is a fact of
the grid (`stride`, `wire_map`, `typed`, the pools).

- **Zephyr** (`dnx.zephyr_graph(m, t)`; family `"zephyr"`): course
  resolution makes `stride = 2` (each track's two j-courses become
  separate sub-lanes `sub = 2k + j`, a run is one course at stride-2
  positions). Consequences: `profiles` zeroes the two boundary lines of
  each orientation; the engine's books use `snap=True`; the converter is
  `wire_seeds_exact`; `complete_seeds` runs; the `certified` /
  `mm_skipped` diag keys exist; a zero-deficit completion that passes
  `is_valid_embedding` is used directly and minorminer is never called.
  The stair objective's bar is `bar = stride = 2` junctions per active
  arm.
- **Chimera / Pegasus** (`stride = 1`, typed, `wire_map` non-empty):
  the engine runs unchanged (`snap=False`, `bar = 1`), the converter is
  `wire_seeds_iv` (greedy interval colouring), there is no completion and
  no certificate (`certified`/`mm_skipped` absent), and the seed chains
  go to minorminer for legalization (`chainlength_patience=0`) — always.
  Pegasus junctions are ~56% complete, so coverage is not validity there.
- **Untyped targets** (family not chimera/pegasus/zephyr, e.g. a plain
  grid graph): `TileGrid` falls back to `fallback_bins` drawing-space
  bins with one untyped pool split across both slots and an empty
  `wire_map`; `line_pools` is empty, so `arrange` returns immediately
  with `stopped_by == "trivial"` (positions = the random permutations),
  `wire_seeds_iv` nearest-qubit-samples, and minorminer does all the
  work. `ball_polish` is also a no-op (no `wire_map` ⇒ no balls).
- **n < 3** on any fabric: `"trivial"` likewise.

---

## 5. Module by module

### 5.1 `plane.py` — the engine (463 lines)

Purpose: optimise the two orders. Everything here is arithmetic on the
orders plus calls into `field.py`'s kernels. `Pos = Dict[int,
np.ndarray]`, `Books = tuple`.

**`profiles(grid) -> (ph, pv)`** — lines 39–61. THE capacity book:
per-(line, brick) pools from `_brick_pool_arrays(grid, stride)`, copied
to float, boundary lines (`[0, :]` and `[-1, :]`) zeroed when
`stride > 1`. Memoised on `grid._plane_profiles`. Called by `judge`,
`_line_profiles`, tests. `test_plane.py::TestJudge::test_boundary_lines_zero_only_on_courses`
pins the zeroing (Z3: boundary rows sum to 0, interior row max 8;
Chimera boundary rows non-zero).

**`stride(grid) -> int`** — 64–65. `max(grid.stride, 1)`.

**`ideal_pool(grid) -> float`** — 68–70. `max(line_pools(grid).values())`
(8 on Z12): the pool an ideal interior line carries; used to extend the
packer's table past the chip.

**`rank_of(order) -> Dict[int, int]`** — 77–78.

**`books(pos, src_adj, grid, yrank, *, snap) -> Books`** — 81–95. The
engine's one accounting: `_stair_contacts(pos, src_adj, yrank=yrank)`
then `arm_books(kappa=1.0, floor=False, snap=snap, min_span=0.0,
contacts, yrank, ybound=False)`. No kappa floor (capacity is the packer's
business), one-tile footprints, y unclipped. Called by `readout`.

**`_cover_bricks(a, b, s, nb_eff) -> (lo, hi)`** — 98–106. Inclusive
hull `[a, b]` → half-open brick range `[floor(a/s), floor(b/s)+1)`, `hi`
clamped to `nb_eff` (the last capacity-bearing brick) so off-chip extent
on a real line is booked on the last real brick — the same rule
`pack_lines`' brick branch uses, so packer and judge agree. Called by
`judge`.

**`judge(bk, pos, src_adj, grid, *, bar) -> (pen: int, stair: float)`**
— 109–156. The objective, lexicographic. `pen`: for each orientation,
each tuple `(line, a, b, v)` deposits +1 on its brick range (difference
array per line, lines the chip lacks included with pool 0, off-chip lines
not clamped); `pen += sum(max(cover - pool, 0)**2)`. `stair =
stair_energy(pos, src_adj, contacts=bk[0], bar=bar)`. Integers
throughout, so tuple comparison is the exact order; no weights. Called
by `arrange` (after the first picture and after every adopted readout).
Pinned by `test_plane.py::TestJudge::test_pen_vs_brute_force_including_off_chip`
(brute-force per-(line, brick) overload on random states with rows up to
`2H`) and `test_stair_is_stair_energy_with_bar`.

**`_line_profiles(axis, grid, items, s, *, bounded=False) -> List[np.ndarray]`**
— 163–196. The packer's capacity table for one axis. `bounded=True`: the
chip's real lines only (rows of `ph`/`pv`). Unbounded (the search): each
real line's profile truncated at its last non-zero brick and extended
with `ideal_pool` bricks out to `need_b = far // s + 2` (past the
farthest hull among `items`), plus `extra = ceil(n / pool) + 1` extra
lines shaped like an interior line — enough for every order to have a
packing (the L_max lemma, `TestUnboundedPack`). Called by `pack_axis`.

**`pack_axis(axis, order, pos, bk, grid, ranks, *, bounded=False) -> ({v: line}, misses)`**
— 199–233. One forced pack: intervals from `bk[2][axis]` (variables
without a tuple are dropped from the pack — with `min_span=0` there are
none), coefficients `_axis_coeffs(bk[0], pos, axis, ranks=ranks[axis])`,
then `pack_lines(ivs, vals, [0]*L, coeffs=cs, brick=(s, prof))`. A
variable the DP skipped (`None`) is put on its order-predecessor's line
(the first assigned line if it is at the front) and counted in `misses`.
Called by `readout`. Pinned by
`test_plane.py::TestPacker::test_pack_axis_zero_own_overload_and_order_kept`
(monotone in the order, integer lines, x within the chip, zero overload
on the packed axis when `misses == 0`).

**`readout(axis, orders, pos, src_adj, grid, *, snap, bounded=False, bk=None) -> (pos, books, misses)`**
— 236–254. Orders → positions on one axis with the other held. Computes
books on the incoming positions (unless `bk` is passed for exactly these
positions and y-order), packs, rewrites `pos[v][axis] = float(line)`,
computes books again on the result. Called by `arrange` (first picture,
per adopted ask, projection).

**`units(orders, src_adj, rng) -> List[(axis, unit_tuple)]`** — 261–296.
One pass's questions, shuffled by `rng.permutation`: for each axis,
every contiguous run of the current order at scales `n//2, n//4, …, 2`
and `1`, at offsets stepping by `max(scale//2, 1)` (half-overlapping),
plus every *distinct* neighbourhood `N(v)` (sorted, excluding v, only
if `1 <= |N(v)| < n`; a `seen` set at 289–293 — the uncommitted
2026-09-07 change — makes twins that share a neighbourhood one unit, so
turán's two blocks contribute 2 units per axis, not 162) as one unit on
each axis. No pairs. Called by `arrange` each pass.

**`arrange(src_adj, grid, *, seed=0, max_asks=None, deadline=None, snap=False, moves=True, trace=False, sched_seed=None) -> (pos, books, info)`**
— 299–468. The engine loop.
1. `rng = default_rng(seed)`: `px`, `py` permutations → `pos`;
   `rng = default_rng(sched_seed or seed)` for the bag.
2. `typed = grid.typed and line_pools(grid)`; if `n < 3` or untyped →
   books on the raw positions (`ybound=True`), `stopped_by="trivial"`,
   return.
3. `orders` from the positions; `bar = stride`; `nbr_units` = the set of
   N(v) tuples (for the trace).
4. First picture: `readout` for axes `(1, 0, 1)` reusing books between
   halves; `e_cur = judge(...)`; `best = (e_cur, pos, books, miss,
   orders)`.
5. Loop while `moves` and not expired (`asks >= max_asks` or past
   `deadline`): `passes += 1`; for each `(ax, unit)` in `units(...)`:
   skip if `tried[(ax, unit)] == state_ver` (a declined question is not
   re-asked until an accept); `asks += 1`; `align_reinsert(order,
   set(unit), src_adj, vals, None, axis=ax, other=other, contacts=bk[0],
   bar=bar)`; `None` → memo and continue; else write the new order's
   values by rank into a candidate, `readout(ax)` with fresh books (the
   moved axis: its contacts changed), then if `miss == 0` `readout(1-ax,
   bk=bk2)` (the other axis: its hulls changed); any `miss > 0` →
   `infeasible += 1`, memo, continue (a proposal the packer cannot seat
   is outside the valid set — never priced, never adopted). Otherwise
   `judge`, count `adopt_worse` if worse, optionally append to `trace`,
   **adopt unconditionally**, `state_ver += 1`, `accepts += 1`, bookmark
   if strictly better by `(pen, stair)`.
6. After a pass with zero accepts: `stopped_by="fixpoint"` (unless the
   budget expired in the same pass).
7. If the bookmark's `pen > 0` (hangs off the chip): the bounded
   projection — `readout(bounded=True)` for axes `(0, 1, 0)` on the
   bookmark's orders, stragglers counted in `proj_misses`; the reported
   `pen`/`stair` stay the search's.
8. `info` gets `pen`, `stair`, `bars` (active arms of the handed-over
   books), `misses`, `orders`, `yrank`, `wall`.

Called by `attract_embed`. Pinned by `test_plane.py::TestArrange`
(trivial/untyped no-op; bookmark equals `judge` of the returned state
and `stopped_by == "fixpoint"` at unbounded budget; `max_asks=30` stops
at exactly 30 asks, deterministically; K_{8,8} reaches `bars == 16`,
`pen == 0`) and end-to-end by `test_attraction.py`.

### 5.2 `placement.py` — the pipeline (292 lines)

Constants: `FALLBACK_TIMEOUT = 60.0` (per minorminer call when no
deadline), `SEED_STRIDE = 100`, `TAIL_SPLIT = 0.5`.

**`target_layout(target) -> {qubit: np.array}`** — 56–68. Native
`dnx.*_layout` for pegasus/chimera/zephyr, else `nx.spectral_layout`.
Called by `attract_embed`, `ball_polish` (when no grid is passed), tests.

**`snap(cent, coords, qubits, degree_order) -> {v: qubit}`** — 71–83.
Each variable, highest degree first, claims the nearest unclaimed qubit
in drawing space. The fallback's seeds only. Called by `attract_embed`
when both the seeded legalization and the certificate failed.

**`_auto_bins(n_qubits) -> int`** — 86–87. `clip(sqrt(nq)/5, 4, 16)`
fallback bins for untyped targets.

**`_mm_route(source_graph, target_graph, *, chains=None, warm=None, seed=0, timeout=60.0) -> Embedding`**
— 90–108. Stock `minorminer.find_embedding` in one of two roles:
seeded cheap legalization (`initial_chains=chains, chainlength_patience=0`)
or warm-started polish (`initial_chains=warm, skip_initialization=True`).
Passes the source as a graph object (an edge list would drop isolated
vertices). Returns `{}` on failure. Called three times by
`attract_embed` (legalize, fallback, tail).

**`attract_embed(...)`** — 111–292. Described in sections 2–4 above.
Order of operations: validate `tail`/`max_asks`; adjacency, sorted
nodes, `src_adj`, `degree_order`; layout and `TileGrid`; gates; `arrange`
with `engine_deadline`; `stair_E`; seeds (exact or iv); completion
(stride 2); certificate check → `mm_skipped`, else seeded minorminer
with the remaining engine wall (`cap`), else nearest-qubit fallback with
the remaining total wall; `_failure(stair_E=...)` if still empty;
`spur_prune`; `legal_acl`/`legal_max_chain`; tail; diagnostics. The
whole body is inside `try/except Exception` → `_failure(error=str(exc))`
with a logged traceback.

### 5.3 `field.py` — the fabric adapter and the exact kernels (1901 lines)

The module docstring (1–36) still describes the pre-rewrite "alternating
arrangement" dynamics; the load-bearing invariants it lists (bars never
recentred; packings order-preserving; seed derivation best-effort) still
hold. The section banner at 1144–1161 is likewise historical.

**`_tile_orient(target, *, courses=False) -> {q: (tile_x, tile_y, orientation, sub)} | None`**
— 57–133. Hardware coordinates → tile coordinates per family. Chimera:
`(j, i, u, k)`. Pegasus (nice coordinates `(t, y, x, u, k)`):
`(x, y, u, 4t + k)`. Zephyr `(u, w, k, j, z)`: position along the wire
`p = 2z + j`; `sub = 2k + j` when `courses` else `k`; `u == 0` vertical
→ `(w, p, 0, sub)`, `u == 1` horizontal → `(p, w, 1, sub)`. `None` for
unrecognised families. Called by `TileGrid.__init__`.

**`class TileGrid`** — 136–213; `__init__(target, pos, fallback_bins=16, courses=False)`
150–205 builds the attributes in section 1 (typed branch: `W`, `H` from
the max tile coordinates, `wire_map` keyed `(u, line, sub)` with
`line = ty` for horizontal and `tx` for vertical; untyped branch: bins).
`to_tile(p)` 209–210 and `to_drawing_delta(d)` 212–213 apply the affine
fit. Constructed by `attract_embed`, `ball_polish`, tests. `TestTileGrid`,
`TestZephyrGrid`, `TestZephyrCourses` pin capacities, wire runs being
coupled paths, junction completeness on Zephyr, `line_pools`.

**`_stair_contacts(pos, src_adj, yrank=None) -> {v: (h_us, v_us)}`**
— 237–275. The diagonal (stair) rule. With `yrank`: `u` goes to `h_us`
iff `yrank[v] < yrank[u]`, else `v_us`. Without: the legacy `(y, id)`
tie-break. Called by `plane.books`, `plane.arrange` (trivial branch),
`_bars_arrays`, `arm_books`, `stair_energy`, `wire_seeds_iv`,
`_rebuild_ball_bars`, tests. Pinned by `TestBooksEquivalence` (against a
verbatim pre-vectorisation reference) and `TestStaircase`.

**`derive_bars_stair(pos, src_adj, *, kappa=13.0, floor=True, bounds=None, contacts=None) -> BarIntervals`**
— 278–302. Bars only (the `bars` element of the books) via
`_bars_arrays`. Not called by the pipeline; used by `TestStaircase`,
`TestSnapClaims`, `TestZephyrCourses`.

**`_bars_arrays(pos, src_adj, *, kappa, floor, bounds, contacts) -> (ids, (hmin, hmax, vmin, vmax), (hv, hu, vv, vu))`**
— 305–367. Vectorised hulls: scatter-min/max of contact coordinates onto
each owner's own coordinate; optional kappa floor (`deg/kappa - 1`
deficit split four ways); optional clipping to `bounds = (W, H)` or
`(W, None)` (y unclipped, only floored at 0). The edge index arrays are
reused by `arm_books`' snap widening. Called by `derive_bars_stair`,
`arm_books`. Pinned by `TestBooksEquivalence`.

**`stair_energy(pos, src_adj, contacts=None, *, bar=0.0) -> float`**
— 370–392. Sum over variables of h-hull width + v-hull width (own
coordinate included), plus `bar` per active arm (a side with >= 1
contact). Called by `plane.judge`, `attract_embed` (`stair_E`, bar 0),
tests. Pinned by `TestAlignReinsert::test_stair_energy_bar_closed_form_on_clique`
(`e0 + bar·2(n-1)` on the diagonal clique) and used as the ground truth
in every `align_reinsert` and `judge` oracle test.

**`bar_widths(bars) -> {v: np.array([w, h])}`** — 395–399. Diagnostics
(`extent_*`). Called by `attract_embed`.

**`_nearest_free(grid, claimed, pt_tile, want_orient) -> qubit | None`**
— 407–422. Nearest unclaimed qubit to a tile-space point among the 64
nearest (orientation-matched when asked). Called by `_ensure_seeds`,
`wire_seeds_iv` (untyped branch).

**`_color_claim_bars(grid, claimed, chains, orientation, bars, targets=None, require_free=False, rng=None) -> None`**
— 425–514. Greedy left-endpoint interval colouring of `(line, a, b, v)`
bars onto the line's sub-lanes; claims the run's qubits over
`[floor(a), ceil(b)]` (or, with `targets`, the integer hull of the
interval and the parity-snapped crossing positions `p* = c` if `c ≡ s
(mod 2)` else `c-1`). `require_free` (ball use) admits only lanes whose
positions across the range are all unclaimed. Oversubscribed bars are
skipped (left to `_ensure_seeds`). Called by `wire_seeds_iv`; tests
`TestZephyrCourses::test_boundary_half_pool_and_parity_coloring`,
`TestOrderMode::test_require_free_skips_occupied_lanes`.

**`_ensure_seeds(grid, claimed, chains, pos) -> None`** — 517–526.
Every variable gets at least one (nearest unclaimed) qubit. Called by
`wire_seeds_iv`, `wire_seeds_exact`.

**`wire_seeds_iv(grid, pos, bars, src_adj=None, snap=False, books=None) -> {v: [qubits]}`**
— 529–619. The stride-1 converter. Untyped grid: nearest-qubit sampling
along each bar. Typed: tuples from `books` (or rebuilt from `bars`, with
snap widening when `snap`), then `_color_claim_bars` for orientation 1
then 0, then `_ensure_seeds`. Best effort — never fails. Called by
`attract_embed` on stride-1 fabrics. `TestWireSeeds`, `TestSnapClaims`.

**`_arm_targets(pos, contacts, bars, orientation, present) -> {v: (a0, b0, sorted crossing lines)}`**
— 622–638. Per-arm snap targets for one orientation: the rounded lines
of the contacts plus the own corner. Called by `wire_seeds_exact`.

**`_convert_line(grid, claimed, chains, orientation, line, items, targets) -> (misses, 0)`**
— 641–783. The exact per-line converter (s3.96 v2). For each arm on
the line, the *required hull* per parity class `R[pi] = (min, max)` of
the parity-snapped targets (`c` or `c-1`), falling back to a single
position at the interval midpoint when an arm has no targets. Then an
exact DP over arms sorted by earliest required-lo, state = the frozenset
of active `(arm, class)` pairs (<= 8 members on any feasible line),
capacity checked at starts (interval-graph fact), cost = total required
hull length, ties broken by history. Seating: per class, left-endpoint
order, first lane whose run over `[lo, hi]` is present, unclaimed and
stride-contiguous (`_lane_ok`); an unseated arm retries the other class,
then any lane on the books interval, and counts a miss. Called by
`wire_seeds_exact` per `(orientation, line)`. Its correctness is checked
end to end by the certificate (`TestCertificate`,
`test_fingerprint_k10_z3_certified_template`).

**`wire_seeds_exact(grid, pos, bars, src_adj, books) -> (chains, {"convert_miss", "convert_flips"})`**
— 786–812. Orientation 1 then 0; per line `_convert_line`; then
`_ensure_seeds`. `convert_flips` is always 0 now. Called by
`attract_embed` on stride 2.

**`arm_books(pos, src_adj, grid, *, kappa, floor=True, snap=False, min_span=1.0, contacts=None, yrank=None, ybound=True) -> (contacts, bars, tuples)`**
— 815–887. THE one accounting (section 1). With `_VERIFY_CONTACTS`
(module global, 1205, default `False`) a reused `contacts` is asserted
equal to a fresh recomputation (`TestContactsFreshness` flips it on).
Lines are `np.rint` of the coordinates (half-to-even, matching Python
`round`). Called by `plane.books`, `plane.arrange`, tests. Pinned by
`TestBooksEquivalence::test_randomized_equivalence` (40 random states ×
2 grids × random `kappa/snap/floor/min_span` against verbatim
pre-s3.114 references; contacts, bars and tuples must be *exactly*
equal, order and duplicates included) and
`test_contacts_passthrough_identity`; `TestOrderMode::test_min_span_zero_books_have_footprint`.

**`_brick_pool_arrays(grid, s) -> (ph, pv)`** — 890–920. Count, per
`(orientation, line, brick = t // s)`, the wire slots in `wire_map`.
Memoised per `s` on `grid._brick_pools`. Called by `plane.profiles`.

**`line_pools(grid) -> {(orientation, line): count}`** — 923–940. The
number of sub-lanes per line from `wire_map` (empty for untyped grids).
Memoised. Called by `plane.ideal_pool`, `plane.arrange` (the typed
test). `TestZephyrCourses::test_line_pools_census`.

**`complete_seeds(grid, chains, src_adj, adj, only=None) -> (chains, info)`**
— 943–1141. Exactness completion by interval arithmetic on
junction-complete fabrics. Builds `rev: qubit → (u, line, sub, p)`;
`ext_to` computes the free bars needed to extend a run to a position
(same wire, stride steps, all unclaimed; a hole inside the run is not
extendable). Three passes: **corner** (each variable's own h- and v-runs
must couple; cheapest crossing extension, else `corner_deficit`),
**edge** (every source edge not yet coupled: cheapest extension among
both orientations of both endpoints, recorded as `extensions`/
`ext_qubits`; the coupled check is live so earlier extensions cover
later edges), **bridge** (1- then 2-free-qubit bridges for the
parallel-only residue; else `deficit_edges`). `only` restricts which
chains may be extended (the ball pass). Called by `attract_embed`
(stride 2), `_place_cross`, `_rebuild_ball_bars`. Pinned by
`TestCompleteSeeds` (edge extension creates a coupler; corner pass joins
an L; bridge pass on parallel runs; deterministic and input untouched)
and `TestOrderMode::test_complete_seeds_only_freezes_others`.

**`_target_kappa(grid) -> float`** — 1164–1184. Derived contact
capacity (mean cross-orientation degree / stride on stride 2; mean degree
− 2 otherwise). Not called by the pipeline (the engine uses `kappa=1,
floor=False`); tests only.

**`line_depth(intervals) -> int`** — 1187–1202. Max overlap depth by
endpoint sweep; touching endpoints do not overlap. Not called by the
pipeline; the brute-force oracle inside `test_pack_lines_matches_brute_force`
and the reference feasibility pass in `TestPackLinesFeasibilityEquivalence`.

**`_MISS_COST = 1e6`** — 1207. The DP's skip price; any real cost is
smaller.

**`_axis_coeffs(contacts, pos, axis, ranks=None) -> {v: int}`** —
1210–1241. Linear coefficients of the stair energy's `axis` term: for
each net (`{v} + v_us(v)` on axis 1, `{v} + h_us(v)` on axis 0) the
order-max member gets +1 and the order-min member −1, so `E_axis =
Σ c_v · pos[v][axis]` for any assignment monotone in the carried order
(`ranks`). Called by `plane.pack_axis`. Pinned by
`TestOrderMode::test_axis_coeffs_reproduce_stair_energy`.

**`_seg_radd(mx, dz, N, lo, hi, v)`** (njit) — 1244–1272: iterative
lazy range-add on a max segment tree. **`_jstar_pass(lo, hi, nseg, c)`**
(njit) — 1275–1296: for uniform capacity `c`, `js[i]` = minimal `j`
such that items `j..i-1` have overlap depth `<= c` (two pointers).
**`_jstar_profile(lo, hi, caps)`** (njit) — 1299–1329: the same with
per-brick caps (leaves start at `-cap[b]`, feasible iff root `<= 0`).
**`_pack_dp(n, L, values, coeffs, use_coeffs, js2d, capidx, miss)`**
(njit) — 1332–1384: the s3.59 line-packing DP, `f[l][i]` = best cost of
the first `i` items using lines `< l`… with transitions carry (`-2`),
skip at `miss` (`-1`), or a contiguous run `[j, i)` on line `l` with
`j >= js[i]` via a sliding-window minimum; returns the parent table and
the cost. All four are called only from `pack_lines`. First call
compiles (`cache=True` writes `__pycache__/*.nbi`; ~1–2 s once per
environment).

**`pack_lines(intervals, values, pools, coeffs=None, brick=None) -> (assign, cost)`**
— 1387–1505. Exact order-preserving line packing. Items pre-sorted by
the carried order; each line takes a contiguous run; feasibility is hard
capacity (uniform `pools[l]` or, with `brick=(s, profiles)`, per-brick
profiles with hull endpoints clamped to the last capacity-bearing brick
— off-chip extent is free on both ends); cost is displacement
`|value - l|` or, with `coeffs`, `coeffs[k]·l` (the true objective);
structurally unplaceable items are skipped at `_MISS_COST` and returned
as `None`. Marshals into the kernels above and backtracks. Called by
`plane.pack_axis`. **Oracle tests:**
`TestArrangement::test_pack_lines_matches_brute_force` (30 random
instances, `n <= 6`, `L <= 4`: exhaustive enumeration of all
non-decreasing complete assignments with `line_depth` feasibility;
optimal cost, order preservation, capacity),
`test_pack_lines_skips_only_when_infeasible`,
`TestPackLinesFeasibilityEquivalence::test_randomized_equivalence` and
`test_zero_coeffs_tie_cascade_and_duplicates` (the JIT kernels against a
verbatim Python copy of the pre-s3.92 sweep + DP: identical assignments
and cost), `TestOrderMode::test_jstar_incremental_matches_reference`,
`test_pack_lines_coeffs_beats_displacement`,
`test_pack_lines_coeffs_respects_capacity`,
`TestUnboundedPack::test_feasibility_lemma_no_misses`.

**`rank_scale(n) -> float`** — 1508–1512. `2n² + 1`: the lexicographic
scale of `align_reinsert`'s pricing.

**`align_reinsert(order, cluster, src_adj, values, anchors, *, axis, other, contacts, slot_costs=False, bar=0.0) -> (new_order | None, flipped)`**
— 1515–1899. The move: remove `cluster` from `order` and re-insert it at
the exact optimum over all interleavings with the rest `R`, the cluster
`S` kept in its internal order or reversed. Values (the axis's line
indices, fixed to slots), the other axis's values and `bar` are scaled
by `rank_scale(n)` and the slot index is added, so the DP minimises
(true cost, total rank span) lexicographically. Axis 1 (y): induced-rule
pricing — contacts are re-derived per candidate as the y-order is built
bottom-up ("placed after = above"); the transition cost of placing a
variable is its h-span over the *not-yet-placed* neighbours' x values
(`stepR`/`stepQ` matrices), the v-term is Σ gap × #arms crossing the gap
(the `CG` count grid by rectangle scatter + 2-D prefix sum), and the bar
is priced per active arm inside the same transitions. Axis 0 (x):
contacts frozen (`contacts` argument), h-nets priced by the gaps they
cross. The `(p+1) × (m+1)` grid DP collapses to one
`np.minimum.accumulate` per line (`_arm`, 1691–1887); the forward and
reversed arms are compared and the better one returned only if it is
strictly better than the current order's own path cost (`e0`) and
differs from it; otherwise `(None, False)`. `anchors` non-`None` with any
finite entry → declined (`test_anchored_view_declines`); `n < 3`, empty
or full cluster → declined. `slot_costs=True` (singletons) returns the
per-slot cost vector instead — unused by the pipeline. Called by
`plane.arrange` (every ask). **Oracle tests:**
`TestAlignReinsert::test_axis1_exact_and_optimal_vs_brute_force[bar,tied]`
and `test_axis0_exact_and_optimal_vs_brute_force[bar,tied]` (15 random
instances each, `n < 10`, `|S| ∈ [2, 4]`: the returned order's
`stair_energy` (rank contacts on y, frozen contacts on x, with the bar)
equals the minimum over *every* merge × both orientations, and a
`None` means no merge beats the current state; `tied=True` is the
production regime of packed integer line indices),
`test_deterministic_and_noop_on_optimal`,
`test_plane.py::TestArrange::test_biclique_gather_is_one_move`.

### 5.4 `polish.py` — spur pruning (185 lines)

**`spur_prune(chains, src_adj, adj, *, deadline=None, only=None) -> Embedding`**
— 43–102. Delete every removable spur (a qubit whose removal keeps the
chain connected and every incident source edge covered), chains and
qubits in sorted order, to a fixpoint; input not mutated; chains never
below one qubit; `deadline` bounds the loop (safe to stop early);
`only` restricts which chains are pruned (coverage still checked against
the full dict). Called by `attract_embed` (after legalization),
`ball_polish` (scoped to the ball / the single). Tests:
`test_ball.py::TestHelpers::test_spur_prune_only_restricts`.

**`shorten_chains(...)`** — 105–170 and **`polish(...)`** — 173–185:
free-space rip-up-and-shorten sweeps with `sph_tree`. **Not called by
the live pipeline** (only `polish` calls `shorten_chains`, and nothing
calls `polish`). Kept as the documented minorminer-`chainlength_patience`
analogue.

### 5.5 `trees.py` — chain assembly (156 lines)

**`_assemble(v, placed, chains, adj, prices, visit_counter, *, attach_to_root_only, forbidden_extra=None, require_all_neighbors=False, rng=None) -> sorted qubit list | None`**
— 57–137. For each placed neighbour `u`, a node-weighted multisource
Dijkstra from `u`'s boundary with `u`'s own chain (and `forbidden_extra`)
forbidden; root = the qubit reached by most neighbours (ties: least
total cost, then lowest id, or uniform among ties with `rng`); attach
neighbours nearest-first to the growing tree (`sph`) or to the root
only (`union`). `require_all_neighbors` → `None` unless every placed
neighbour attached.

**`sph_tree(...)`** — 140–143: `_assemble(attach_to_root_only=False)`.
Called by `_rebuild_ball`, `_place_cross` (fallback), `shorten_chains`.
**`union_of_paths(...)`** — 146–150 and **`TREES`** — 153–156: the
ablation arm; unused by the pipeline.

### 5.6 `ball.py` — the ball pass of the tail (858 lines)

**`_hull_balls(work, src_adj, grid, rev) -> List[tuple]`** — 52–127.
One question per chain: its obligation hull (bounding rectangle of its
footprint tiles, extended per neighbour to the nearest line the
neighbour's runs occupy on each axis); the ball = anchor + every chain
with a footprint tile inside the hull; size < 2 skipped; deduped.
Untyped grids → no balls. Called by `ball_polish` each sweep. Tests:
`test_ball.py::TestHullQuestions`.

**`_trim_ball(S, src_adj) -> tuple`** — 130–153. Drop degree-0 members
and components of `S`'s induced subgraph with no neighbour outside `S`
(no attachment point); `()` if fewer than 2 remain. Called by
`ball_polish`. Tests: `TestHelpers::test_trim_drops_isolated_and_interior_components`.

**`_rebuild_ball(S, work, src_adj, adj, visits, deadline, rng=None) -> {v: chain} | None`**
— 156–190. The router rebuild: members in dynamic greedy order (most
already-placed neighbours first), each by `sph_tree` with every other
chain's qubits forbidden and all placed neighbours required. Called by
`ball_polish` when the bar rebuild rejects. Tests:
`TestHelpers::test_rebuild_rejects_cleanly_on_deadline`.

**`_audit_claim(grid, claimed, orientation, lines, lo, hi, cross_lines, rng=None) -> (line, sub, qubits, cost) | None`**
— 193–247. Lane audition by measured cost: every lane on the candidate
`lines` whose run over `[lo, hi]` is present, unclaimed and
stride-contiguous; cost = qubits to claim + parity misses (stride 2: a
crossing target `c` the lane cannot couple, `p* = c` or `c-1` absent
from the run); minimum by `(cost, line, sub)`, uniform among ties with
`rng`. Called by `_place_cross`, `_rebuild_ball_bars`. Tests:
`TestAuditClaim`.

**`_runs_of(chain, rev) -> (h_runs, v_runs)`** — 256–273. A chain's
physical runs as `(line, p_lo, p_hi)`. Called by `_place_cross`.

**`_place_cross(v, work, src_adj, adj, grid, rev, rng, *, allow_deficit, incumbent, realize_cap, deadline, visits=None, window=0) -> chain | None`**
— 276–520. The `|S| = 1` exact-cross move: score every anchor tile
(within `window` of the neighbours' reachable lines) by (coverage
deficit, hull length), shuffle exact ties, realise down the ranking via
`_audit_claim` on both arms + scoped `complete_seeds` (stride 2) +
scoped verify, first realisation shorter than `incumbent` wins; falls
back to `sph_tree`. Called only by `ball_polish(singles=True)` — **off
by default** in the pipeline. Tests: `test_crossfinder.py::TestBallSingles`.

**`_rebuild_ball_bars(S, work, src_adj, adj, grid, deadline, rng=None, rev=None) -> {v: chain} | None`**
— 524–698. The bar rebuild: member pseudo-positions by a median
fixed-point sweep from frozen neighbours' run lines; `_stair_contacts`
on those; per member an obligation hull per orientation (candidate
lines = the integer rows/columns of the perpendicular hull, crossing
targets = the contacts' lines); members placed in dynamic greedy order
by `_audit_claim` on each needed arm; scoped `complete_seeds(only=S)`
on stride 2; connectivity and coverage verified per member; any failure
→ `None`. Called by `ball_polish` first. Tests: `TestBarRebuild`.

**`ball_polish(chains, source_graph, target_graph, *, deadline=None, adj=None, grid=None, max_sweeps=None, rng_seed=None, singles=False) -> (Embedding, info)`**
— 701–858. Validates the input (invalid → returned unchanged,
`info["invalid_input"]`); builds `grid` (courses on) and `rev` if not
given; sweeps: optional singles pass, then regenerate the trimmed,
deduped hull balls from the current embedding, shuffle with `rng`, for
each ball try `_rebuild_ball_bars` then `_rebuild_ball`, scoped
`spur_prune`, accept iff the members' total qubit count strictly
decreases; stop after a dry sweep (two with an rng), `max_sweeps`, or
the deadline; final `is_valid_embedding` guard reverts to the input on
any breakage (`info["guard_reverted"]`). `info`: `tried`, `accepted`,
`sweeps`, `questions`, `wall`, optionally `bar_rebuilds`,
`single_tried`, `single_accepts`. Called by `attract_embed` when
`tail == "mm"` (defaults: no singles, no rng, no sweep cap, the call's
deadline). Tests: `test_ball.py` (guards, valid-and-never-longer,
determinism, idempotence at the fixpoint, a constructed improvement,
tail variants), `test_crossfinder.py`.

---

## 6. Tests

All under `tests/algorithms/` (`pytest.ini` at the repo root sets
`pythonpath` to both packages' `src/` and `--timeout=120`, so
`pytest-timeout` must be installed). Run from the repo root:

```
.venv/bin/python -m pytest tests/algorithms -q
```

Verified 2026-09-07: **505 passed in 99 s** (on the loaded 128-core
box; expect 2–4 minutes on a laptop, the numba kernels compiling on the
first run).

| file | lines | what it covers |
|---|---|---|
| `test_field.py` | 1362 | the adapter and the kernels: `TestTileGrid`, `TestStaircase` (stair rule and `stair_energy` closed forms), `TestArrangement` (`line_depth`; **`pack_lines` vs brute force**), **`TestAlignReinsert`** (exactness + optimality vs brute force on both axes, with/without bar, tied/untied), `TestArmLengthGating`, **`TestCompleteSeeds`**, `TestSnapClaims`, `TestWireSeeds`, `TestZephyrGrid`, `TestZephyrCourses` (wire_map, line pools, boundary half-pool, parity colouring, course seeds valid), `TestOrderMode` (`_axis_coeffs`, coeffs packing, footprints, jstar reference, scoped completion, `require_free`), `TestContactsFreshness` (the staleness fence on Z6), **`TestPackLinesFeasibilityEquivalence`** (JIT kernels vs the Python original), `TestUnboundedPack`, **`TestCertificate`**, **`TestBooksEquivalence`** |
| `test_plane.py` | 190 | the engine: `TestJudge` (`stair` == `stair_energy`; **`pen` vs brute force including off-chip**; boundary zeroing), `TestPacker` (monotone/integer/on-chip/zero-overload readout; determinism), `TestArrange` (trivial & untyped no-op; bookmark == judge, fixpoint and asks stops, determinism; K_{8,8} gather in one move) |
| `test_attraction.py` | 182 | end to end on Chimera 4×4×4 / Z3 / Pegasus 4: validity, determinism, `diag` surface, registry contract, unknown kwargs ignored / bad `tail` and `max_asks` fail loudly, stride 2 on Zephyr with the exact stack, the K10/Z3 certified fingerprint (`legal_acl == 1.8`, `max_chain == 2`, `pen == 0`), stride gate off Zephyr, `max_asks=1` still legalizes, `sched_seed` semantics, untyped fallback (`"trivial"`), isolated vertices, integer positions |
| `test_ball.py` | 335 | `ball_polish` and its helpers on Z3 with a K-ish source; `TestTail` (tail mm/none/default; rng-seeded determinism) |
| `test_crossfinder.py` | 49 | `ball_polish(singles=True)` (the `_place_cross` arm): valid, non-increasing, deterministic, off = control |
| `test_algorithm_contracts.py` | 296 | the framework's contract for every registered algorithm, `attraction` included: return format, failure format, timeout grace, seed reproducibility, input immutability, no stdout, counters, version |
| `test_mmfork_history.py` | 112 | the minorminer C++ fork (`minorminer_forked`, not part of this package): parity with stock when its switches are unset |

The exact, brute-force-oracle-tested kernels and the test that pins
each:

| kernel | pinned by |
|---|---|
| `pack_lines` (+ `_pack_dp`, `_jstar_pass`, `_jstar_profile`, `_seg_radd`) | `test_pack_lines_matches_brute_force`; `TestPackLinesFeasibilityEquivalence`; `test_jstar_incremental_matches_reference`; `TestUnboundedPack` |
| `align_reinsert` | `TestAlignReinsert::test_axis1_…` and `test_axis0_exact_and_optimal_vs_brute_force` (4 parametrisations each) |
| `_stair_contacts`, `_bars_arrays`, `arm_books` | `TestBooksEquivalence` |
| `_axis_coeffs` | `test_axis_coeffs_reproduce_stair_energy` |
| `stair_energy` (bar term) | `test_stair_energy_bar_closed_form_on_clique`, `TestStaircase` |
| `plane.judge`, `plane.profiles` | `TestJudge` (`test_pen_vs_brute_force_including_off_chip`) |
| `plane.pack_axis` / `readout` | `TestPacker` |
| `complete_seeds` | `TestCompleteSeeds`, `test_complete_seeds_only_freezes_others` |
| `_convert_line` / `wire_seeds_exact` (via the certificate) | `TestCertificate`, `test_fingerprint_k10_z3_certified_template`, `test_exact_stack_default_diag_on_zephyr` |

---

## 7. Known rough edges and TODOs (as of this tree)

1. **Per-ask cost at n ≈ 500 is a Python loop.** `align_reinsert._arm`
   (field.py 1713–1773) builds `stepR` row by row in a `for i in
   range(1, p+1)` Python loop (and `stepQ` column by column); at
   `n = 486` (ws) this is ~35 ms per ask and the engine runs at ~40
   asks/s, so a 15,000-ask budget is ~6 minutes and the 60 s `new+mm`
   arm finishes a fraction of a pass. Vectorising the `stepR`
   construction is open front 1 ("Per-ask cost") in
   `docs/paper2/ideas.md`.
2. **Books are computed three times per proposal.** `readout` (plane
   236–254) computes `books` before and after its pack; `arrange` calls
   it with `bk=None` for the moved axis and reuses `bk2` for the other,
   so each proposal that reaches the packer costs 2 packs + 3
   `arm_books` (`_stair_contacts` + `_bars_arrays` + the tuple loop over
   every variable). `docs/paper2/ideas.md` open front 1 names "one
   books computation per pack" as the target alongside the `stepR`
   vectorisation.
3. **`_line_profiles` extension sizes are heuristic.** The unbounded
   table extends every line to `far // s + 2` bricks and adds
   `ceil(n / pool) + 1` extra lines shaped like an interior line. That is
   enough for a packing to exist (the L_max lemma) but it is not tight,
   and the extra lines' bricks are all at `ideal_pool` even where the
   chip's own line would have a dead qubit; the judge prices the truth,
   the packer only needs existence.
4. **The bounded projection is columns-first `(0, 1, 0)`** (plane
   452). The comment explains why (rows-first stacked everyone on one
   row while x hung off the chip); it is an ordering choice, not a
   theorem, and a bookmark with `pen > 0` is handed over with counted
   `proj_misses` that the converter will miss and minorminer must
   repair. `projected`/`proj_misses` are in `arrange`'s `info` but not
   in `diag`.
5. **`misses` semantics.** `diag["misses"]` is the `miss` value stored
   with the bookmark: for the initial picture that is the miss count of
   the *last* of the three readouts (axis 1), not the sum; any later
   bookmark has `misses == 0` by construction (a proposal with a miss is
   declined before it can be judged). So the key is informative only
   when the search never improved on the init.
6. **`trace` diag.** `arrange(trace=True)` records
   `(asks, axis, |unit|, unit is an N(v), e_cur, e2)` per adopted ask in
   `info["trace"]`, but `attract_embed` never passes `trace` and does not
   forward it; to get a trace call `plane.arrange` directly (as
   `test_attraction.py::test_positions_are_integer_line_indices` does).
7. **`stopped_by == "passes"`** (plane 434) is unreachable in practice
   (the loop only leaves by fixpoint or expiry); `"moves-off"` needs
   `moves=False`, which `attract_embed` never passes.
8. **`_convert_line` returns `(misses, 0)`** — the `flips` slot and
   `convert_flips` in the info are vestigial (always 0).
9. **`polish.shorten_chains`/`polish.polish`, `trees.union_of_paths`/`TREES`,
   `ball._place_cross` (singles), `align_reinsert(slot_costs=True)`,
   `derive_bars_stair`, `_target_kappa`, `line_depth`** are live code
   with no pipeline caller (tests and ablation arms only).
10. **The `field.py` module docstring and the banner at 1144–1161**
    describe the pre-rewrite dynamics (subgradient descent, alternating
    arrangement); read `plane.py`'s docstring for the current engine.
11. **`extent_*` diag** are computed from `books[1]` (the un-widened
    hulls), not from the claim tuples, so they undercount the snap
    widening on stride 2.
12. **Wall-clock dependence with `tail="mm"`.** The seeded legalization
    and the warm grind are minorminer calls bounded by the remaining
    wall, so `tail="mm"` results depend on the machine even at a fixed
    `max_asks`; only `tail="none"` runs that stop by `"fixpoint"` or
    `"asks"` are machine-independent.
