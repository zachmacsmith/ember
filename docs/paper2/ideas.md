# Ideas

The entry point. One page: the algorithm, the principles any change
must respect, and the open fronts. History is elsewhere and is history,
not instruction: `notes.md` (chronicle; s3.127 is the rewrite),
`attraction.md` (verdict ledger of the old engine — check before
proposing), `anatomy.md` (as-built spec of the rewrite),
`fabrics.md` (measured hardware facts), `mm-internals.md` (what
shipped minorminer actually does), `archive/` (the old engine's
records and its probe scripts).

## The algorithm (s3.127, `factored/plane.py`)

1. A D-Wave fabric is a grid of **lanes** with a complete bipartite
   **junction** wherever lanes cross. A qubit is a bar on a lane; a
   chain is a horizontal run plus a vertical run; a source edge is a
   crossing of one variable's run with the other's.
2. **State** = two orders: each variable's rank on the x-axis and on
   the y-axis. Nothing else is stored. Init = two seeded permutations.
3. **Readout**: the packer DP gives every variable a line on each axis
   — each line takes a contiguous run of the order, feasible iff the
   run's claim intervals fit the line's per-brick pools (the chip's
   real lines, boundary lines zero on course fabrics, extended past
   the chip with the ideal pool so a packing always exists). The stair
   rule then derives every chain: the endpoint lower in the y-order
   reaches sideways to the other's column, the higher reaches down.
4. **Objective**, lexicographic: brick overload of the claim intervals
   against the chip (pool 0 off-chip) first, then total derived chain
   length = every active arm's span plus one bar (the qubit an arm
   needs even when its hull is one junction). One accounting: the
   books the packer packs, the judge prices and the converter seats.
5. **Move**: remove a set of variables from one order and re-insert it
   at its exact optimum over all weaves, forward or reversed (the
   interleaver DP, pricing the frozen picture: the other axis fixed,
   spots on its own axis fixed, occupants moving). **Units** per pass:
   every contiguous run of each order at scales n/2 … 1, and every
   variable's neighbourhood N(v) — the order-independent gather (for a
   biclique N(v) is the other block, so the bipartition is one move;
   for a sparse graph, "bring my neighbours to me"). No pairs.
6. **Schedule**: one seeded bag per pass. **Acceptance**: every DP
   proposal is adopted (the proposer's picture is frozen; the readout
   re-packs the moved axis then the other; the judge scores what the
   packer produced; the bookmark keeps the best). A proposal the
   packer cannot seat is declined — outside the valid set. The DP's
   own gate is strict improvement in true cost with total rank span
   as an exact lexicographic tiebreak (the tie-moves are the drift
   that compacts sparse chains).
7. **Stop**: a pass with zero accepts (the fixpoint certificate), or
   the work budget `max_asks` (DP evaluations — never seconds), or the
   wall clock as a reported safety net.
8. **Adapter** (`field.py`): books → converter → completion →
   certificate. On course-resolved Zephyr a zero-deficit completion is
   a proof of validity and minorminer is skipped. `tail="mm"` runs
   minorminer's warm grind and the ball pass afterwards; `tail="none"`
   is the engine's own answer.

Parameters: `timeout`, `seed`, `sched_seed`, `max_asks`, `tail`.

## Principles (each one was paid for; s3.127's audit is the receipt)

- **The init must not matter.** The old default init pre-committed a
  maximally interleaved y-order on turán and the seed could not change
  it (two inits ever); it was the driver of the 9.253 attractor.
- **Question order must not matter.** Schedule sensitivity is a
  family/judge defect. The ladder was worth nothing on 8/10 cells and
  was the worst order on ER and turán.
- **Units must not be defined by the current order alone.** A reinsert
  keeps both sides as subsequences, so contiguous runs cannot
  un-interleave; N(v) can.
- **Proposer == judge**, one accounting; feasibility by construction,
  never repair; no penalty methods, no λ.
- **The objective must be the qubits.** A contact-bearing point arm
  costs a bar; the span-only objective was off by −76% on grid.
- **Budgets in work, not wall.** The clock was a parameter of the
  answer (turán needed the third pass).
- **No mechanism names a graph type.** Winners ship as defaults.

## Open fronts

1. **The paired board.** The rewrite vs stock minorminer and vs the
   archived default (worktree at `ea5d1cf2`), 10 cells, paired by
   (instance, seed), `tail="none"` and `tail="mm"`. Fingerprints so far
   (tail none, work budgets): K100 7.26 at a fixpoint, turán 6.000 on
   10/10 random inits, grid_200 pre-tail 1.40 (old 1.87), path-60 1.033.
2. **The instrument on the new engine**: bag draws (`sched_seed`) ×
   random inits (`seed`) per cell; the claim is order-free and
   init-free within tolerance. ER's delocalized near-minima are the
   cell to watch.
3. **The sparse ceiling.** The plane's family is one cross per
   variable; lattices reach ~1.4 pre-tail where minorminer polishes to
   ~1.3. Candidates: abutment (two chains meeting end to end on a lane,
   the grid half of the product topology) and junction packing.
4. **Performance.** The interleaver's per-ask Python loop is O(p) at
   n≈500 (~35 ms); vectorize if ws is budget-bound.
5. **Parked**: Pegasus (junctions ~56% complete: converter/completion/
   certificate gated to stride 2; the engine runs), max chain as a
   third lexicographic slot.
