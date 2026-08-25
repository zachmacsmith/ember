# Anatomy of the attraction embedder (v5, plain language)

Rewritten 2026-08-25 after consolidation 7 (one engine, one pipeline;
the deleted eras live at archive commits `d8274198`, `09467299`,
`5be76754`, `12fe484c` — verdicts in attraction.md). The document
deepens in passes: the whole algorithm first, then the shared
vocabulary, then each piece mechanically. If a "how" here is not
enough to re-implement the piece, that is a bug in this file.

Code map: `placement.py` (driver), `seat.py` (THE arrange engine),
`field.py` (grid, books, packer, converter, completion), `coarsen.py`
(hierarchy + init), `polish.py` (prune), `ball.py` (post-processor).

## The whole algorithm in one breath

Every variable gets a seat on an ideal grid — an integer (column,
row). From seats alone, everything else is derived: which endpoint of
each edge reaches sideways and which reaches down (a rule keyed on
the row order), hence each variable's two "arms," hence how crowded
every line is. One search improves the seats under one objective read
lexicographically: first *does everything fit* (arm cover within each
line's wire budget, counted at the fabric's parity period so the
count is honest), then *how short are the chains*. The search's
strongest move teleports a whole cluster of variables to its provably
best re-weaving into the line order, so crowded valleys between here
and there never block it. A packer projects the finished seats into
the regular shape the next stage expects, a converter turns arms into
actual wire claims, a completion pass connects and verifies — often
*proving* validity, in which case minorminer is skipped entirely —
and minorminer's polish plus a region-rebuilding pass shorten
whatever remains.

## 0. The hardware in five facts

Everything fabric-specific reduces to these (measured; fabrics.md):

1. **A qubit is a bar** — a horizontal or vertical segment on a grid.
   Couplers exist where bars cross (internal), abut end-to-end
   (external), or run parallel one step apart (odd).
2. **Lines carry a fixed number of wires** (8 on course-resolved
   Zephyr). More overlapping arms than wires on one line means
   someone gets no wire.
3. **Zephyr bars have parity** (two "courses" per track, laid like
   brickwork): a bar can only start at every other position. One
   *brick* = 2 junctions = one bar length; a brick holds one junction
   of each parity, which is why whole-brick accounting cannot be
   fooled by parity (§2.4).
4. **Junctions are complete on Zephyr** (every h-bar couples every
   v-bar where they cross): "my arm crosses your arm" IS "we are
   coupled." This is what makes proof-of-validity possible — and it
   is false on Pegasus (~56%), which is why Pegasus is written off
   (s3.112) pending an elegant adapter.
5. **Boundary lines have half capacity** (one parity only); the
   packer zeroes their pools and the brick pools shrink there on
   their own.

## 1. The pipeline, one sentence per step

1. **Init**: a spectral sketch of the source graph, used once, for
   its per-axis ranks — the starting seats.
2. **Init projection** (`pack_project`): the exact packer turns ranks
   into real line assignments, nobody dropped.
3. **Arrange** (`seat_arrange`, the lex engine): strict descent on
   the one lexicographic objective — capacity first, chain length
   second — with the interleave jump as the workhorse move.
4. **Normalizer** (`pack_project` again): one more pack projects the
   searched seats into the packer-shaped family the converter and
   completion were co-designed with (their measured remaining job,
   s3.110 — capacity is already the search's own invariant).
5. **Conversion**: the per-line converter claims actual wires
   (parity-aware, corner-included), counting any arm it could not
   seat in full.
6. **Completion**: pure interval arithmetic connects each chain at a
   corner, covers remaining edges, bridges the residue — if deficits
   hit zero, the result is provably valid (`certified`) and
   minorminer legalization is skipped (`mm_skipped`).
7. **Routing fallback**: otherwise capped minorminer legalization
   from our seeds, then an uncapped last resort.
8. **Tail polish**: minorminer's warm unconstrained grind, then
   `ball_polish` LAST, harvesting the coordinated re-layouts
   single-chain moves cannot see (ball before the grind was measured
   worse, s3.80 — nothing may narrow the grind's basin) (I still
   stand in incredible disbelief of this, surely this is only
   happening because something else is going on somewhere else and
   it's rippling to effect us here).

Steps 1–4 live on the ideal plane and never touch hardware defects;
steps 5–8 are the adapter and its nets. A validity guard wraps the
end: a broken late pass can never corrupt a legal result.

## 2. The vocabulary (what every stage shares)

**2.1 Seats.** The state is a dict `{variable: (col, row)}` of
integers. Everything else — contacts, arms, cover, energy — is a
readout of the seats, recomputed, never stored (ideas §2.3). The two
axis *orders* (sort by coordinate, ties by id) are induced from the
seats; the interleave move works in that order space.

**2.2 The stair rule (contacts).** For each edge (u, v): whichever
endpoint is *lower* in the y-order reaches the other with its
horizontal arm; the higher one reaches down with its vertical arm.
Every edge gets exactly one designated crossing. On a clique laid
along the diagonal this reproduces the optimal template exactly; on
sparse graphs it decays into short local arms (s3.34).

**2.3 Arms.** A variable's h-arm is the interval from its own column
to the furthest column it must reach (hull of its h-contacts), on its
own row; the v-arm is the mirror. The engine's arms are
*demand-honest*: a side with no contacts deposits nothing (an empty
side needs no bar — the s3.108 phantom-arm lesson). The
packer/converter *books* (`arm_books`) are a widened variant of the
same arms: a capacity floor (a chain of L qubits can host at most
~kappa·L couplers, so arms are widened to at least deg/kappa − 1) and
a one-tile occupancy footprint — counting, not tuning.

**2.4 The brick, and the two rulers.** Capacity is counted per
(orientation, line, brick), where a brick = `grid.stride` junctions =
one bar length; pools come from the wire map (8 on interior Zephyr
bricks). Whole-brick counting is honest: a bar covers exactly one
brick, and end-rounding to brick boundaries books no phantom
half-qubits (s3.107/109). Chain *length*, by contrast, stays at
junction resolution — the sharp ruler. Constraint coarse, objective
fine: each detail at its own resolution.

**2.5 The objective.** One scalar, read as a lexicographic pair:

    E = pen · 2^26 + stair
    pen   = Σ hinge²(brick cover − brick pool)   [capacity, leading]
    stair = Σ arm hull spans (junctions)         [length, second]

All quantities are integers, so the scalar IS the tuple order:
capacity never trades against length at any exchange rate (there is
no λ to tune — the weighting-defect family is unrepresentable,
s3.110). A search that reaches pen 0 keeps feasibility as an
invariant forever after, because strict descent cannot re-enter
overload.

## 3. The pieces, one level deeper

### 3.1 Init (coarsen.py)

Coarsen the source to a small quotient graph (mutual-preference
aggregation to its natural fixpoint), lay the quotient out spectrally
(circle fallback for degenerate spectra), spread members around their
supernode, then keep only the per-axis *ranks* of the points. The
init is deliberately unclever: its one job is a starting order where
"close in the graph" roughly means "close in both orders" — results
must survive a random init anyway. The same hierarchy's groups become
the *units* the engine's cluster moves act on (coarsen the moves,
never the state — ideas §2.10).

### 3.2 pack_project (field.py) — the packer, alone

**What.** Given seats, re-derive the books and assign every variable
a row and a column — the exactly cheapest assignment the current
orders allow, under hard integer wire capacity. Runs once as init
projection (step 2) and once as normalizer (step 4).

**How.** One forced pack per axis on the *ideal* crossbar (uniform
pools, as many lines as demand needs — nobody is ever dropped), with
`edge_monotonize` between them (for each edge whose x-order disagrees
with its y-order, swap the two x-values if total h-length strictly
drops — load-bearing: it feeds the x-pack's ordering), then one
*bounded* pack per axis with the real pools (boundary lines zeroed)
to land everything in the real window. `final_width_x/y` records the
ideal demand on the way; residues are clamped onto real lines.

**The pack itself** (the s3.59/93 DP, per axis): seat the y-order
lineup into rows, each row taking one contiguous group. Total arm
length folds into one integer *coefficient* per variable
((#hulls it tops) − (#hulls it bottoms)), making the cost separable:
Σ coefficient × row. A two-index DP (rows used × variables seated)
with a sliding-window minimum finds the exact optimum under "≤ pool
arms deep per line"; competing hypotheses coexist in table cells
until the future extends the cheaper one, so no flip-flop is
possible. Exactness matters because the packer's output defines the
family everything downstream trusts.

**Why it survives.** Not for capacity — the engine owns that now —
but because the converter and completion were co-designed with
packer-shaped states (measured, s3.110: a capacity-clean searched
state converts at 578 deficits raw, 0 after one pack, cleanliness
preserved). The pack is a family projection. Deleting it requires a
converter co-designed with the engine's own family (§5).

### 3.3 The lex engine (seat.py) — the search

All moves are judged by ONE evaluator (`seat_energy`, §2.5) —
proposer and judge are the same arithmetic, so there is no second
court to reject work. Strict descent, deterministic; deadline checked
between batches. Fast candidate scans are allowed to be approximate,
but every chosen candidate is re-scored exactly before acceptance
(`fast_miss` counts scan/audit disagreements; a per-pass cross-check
against the reference evaluator is the drift alarm).

- **Interleave jump** (`best_interleave` — the unit move, s3.111).
  Take one hierarchy unit out of one axis's order and re-insert it at
  the exact optimum over ALL interleavings with the rest (a DP prices
  every weave at once: induced-rule pricing on y, frozen contacts on
  x, forward and reversed unit), handing the same coordinate multiset
  back by rank — spots don't move, occupants do. The DP's candidate
  is audited by the evaluator; a decline costs one evaluation, and
  "already optimally woven" is a free certificate. It is a JUMP: it
  lands on the final state without traversing anything, so the hard
  capacity key cannot path-block it. Jump and hard key are measured
  complements — either alone loses the turán crystal, together they
  hold it at the optimum on all deep seeds (s3.111b).
- **Swap sweeps** — pairwise seat swaps over source edges (x, y, or
  both; y-swaps flip contacts and are priced exactly).
- **Single re-seats** (`best_seat`) — one variable, every seat on the
  grid, fast prefix-array scan + exact audit of the top candidates.
- **Rigid translations** (`best_translate`) — one unit, every
  in-window offset; vertices on cross-boundary edges get full hull
  recomputes (a shift can flip who-is-below on a boundary edge —
  Max's catch).

Ladder (s3.81): the coarse move (interleave, coarsest units first)
runs to its own fixpoint before the fine moves are released — greedy
fine moves would narrow the coarse basin.

### 3.4 Conversion (field.py) — arms become wire claims

Per (orientation, line): each arm's *required* span is its contacts'
positions plus its own corner, widened one junction for parity slack,
projected into each parity class. A small exact DP (state = the
classed set of still-active arms, ≤ 8) assigns arms to parity classes
so required spans fit the 4+4 wires; a left-endpoint sweep then seats
claims onto wires, parity-preferred, counting a `convert_miss` for
any arm that could not seat its required span in full (a miss still
claims what it can). Snap aiming — choosing claim ranges so each
designated crossing lands on a coupler at claim time — is folded into
this arithmetic ("aim, don't repair": extensions dropped to ~0 when
it shipped, s3.56).

### 3.5 Completion and the certificate

Three passes of interval arithmetic over the claims: connect each
chain's own h-run and v-run at their cheapest feasible crossing
(corner pass); for each still-uncovered source edge, extend the
cheapest of the four run-pairs until the crossing coupler exists
(edge pass); bridge the residue through one or two free qubits
(bridge pass). Junction completeness makes crossing arithmetic equal
adjacency, so if converter misses and deficits all reach zero the
embedding is *proved* valid before any router runs: `certified` is
set and minorminer legalization is skipped. The full validity check
stays as the paranoia net.

### 3.6 The tail

If the certificate did not fire: stock minorminer legalizes from our
seeds (capped at `round_frac` of the budget so the polish cannot be
starved), with one uncapped fallback from nearest-qubit seeds. Then
spur-pruning, then minorminer's full grind runs warm-started and
*unconstrained* (the placement must improve the endpoint of a free
polish or it was not a real improvement — s3.22), then `ball_polish`:
evict a small set of whole chains chosen by a derived obligation
hull, rebuild them jointly against the frozen rest (bars-first, then
a router fallback), accept only strict total decrease. That is the
coordinated regional move minorminer structurally cannot make, judged
directly on qubit counts.

## 4. Knobs (12) and diagnostics

`round_frac=0.5` (budget before the polish), `kappa=None` (derived
from the fabric), `span_floor=True`, `exact_seeds=True` (Zephyr
gate), `snap_claims=True` (Zephyr gate), `vcycle=True`,
`vcycle_agg=True`, `cluster_moves=True`, `cluster_units=True`,
`init_mode="spectral"`, `tail="mm+ball"` ({"mm+ball", "ball+mm",
"mm", "ball", "none"}), `ball_singles=False`. Consolidations 5–7
(archives 09467299, 5be76754, 12fe484c + purge 37d3439c) deleted
every other lever; verdicts in attraction.md. Unknown kwargs are
ignored (old probe scripts degrade gracefully).

Diagnostics (`diag`): `extent_mean`/`extent_max`, `stride`,
`E_interp`/`E_contract`, `max_chain`, the walls, the engine counters
(`seat_accepts`, `trans_accepts`, `swap_accepts`,
`interleave_accepts`/`_declines`/`_noops`, `seat_passes`,
`seat_fast_miss`, `accept_traj`, and `seat_pen`/`seat_stair` — pen 0
certifies the feasibility invariant held), the normalizer's fit
observables (`final_width_x/y`, `projection_misses`, `unb_miss`),
and on Zephyr `mm_skipped`, `deficit_edges`, `corner_deficit`,
`extensions`, `ext_qubits`, `bridges`, `convert_miss`, `certified`.

## 5. Lineage and open fronts

The engine descends from the s3.102 seat prototype through three
measured rounds — the brick ruler (s3.107-109), the lexicographic
objective (s3.110; alone it was path-blocked), the interleave jump
(s3.111; the resurrected insertion DP) — shipped together at
consolidation 7 (s3.112) when the combination reached board parity
with the old orders engine, crystal included, and the orders court
was deleted.

Open fronts (live list in ideas.md §3): the **lex-family converter**
(spill-aware per-line brick seating) would delete the normalizer pack
and the classed DP — the last seam where one stage buys what another
should own; the polish is still minorminer (`ball_polish` is the
replacement path); **Pegasus is written off** (owner's call, s3.112 —
runs, regresses; parked behind an elegant coupler-predicate adapter);
max-chain has a natural future home as a third lexicographic slot,
deliberately unopened.
