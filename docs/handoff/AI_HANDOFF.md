# Notes for the next AI assistant

Written by the assistant that did the s3.124–s3.127 work (the wrap,
the two switches, the order-invariance instrument, the audit, and the
rewrite), for whichever model works with the next researcher. The
researcher's principles come first; the mechanics second; the traps
last.

## The owner's principles, in their words where I have them

These are not doctrine invented by an assistant. Each one was paid for
with a measurement, and the receipts are in `HISTORY.md`.

- **"The best optimizer wins from random."** The init must not matter.
  If a quality-changing init helps, that is a bug report against the
  optimizer, not an asset. (The old engine's init pre-committed turán's
  worst y-order and the seed could not change it.)
- **"Question order must not matter."** Schedule sensitivity is a
  defect of the move family or the objective, never something to tune.
  Measure it with `sched_seed` draws. A smart order may only make the
  fixpoint faster.
- **"No penalty methods."** Finiteness and capacity are facts of the
  geometry, never a soft price: capacity is the leading lexicographic
  key, a proposal the packer cannot seat is declined, and the plane is
  extended past the chip so that a state always exists. Do not open
  with a λ-weighted overflow term.
- **Feasibility by construction, never repair.** Every state the search
  occupies is packer output. The only projection is the bounded one at
  the end, and only if the bookmark hangs off the chip, and it is
  counted.
- **Proposer == judge, one accounting.** The books the packer packs are
  the books the judge prices and the converter seats. Two books were
  the source of more bugs than anything else in this project's history.
- **"No mechanism may name a graph type."** No special moves for
  cliques, no branches for lattices. The regime must emerge (dense →
  the template, sparse → short arms) from the same rules.
- **Budgets in work, not seconds.** `max_asks`. The clock was measured
  to be a parameter of the answer.
- **One switch per change, measured paired by (instance, seed) against
  the shipped default; winners ship as defaults immediately; losers are
  deleted.** Do not keep refuted levers around.
- **"Notes are ideas."** The chronicle records ideas, measurements that
  change the algorithm, and verified facts. No micro-verdict
  accretion, no in-house vocabulary drift. Write plainly.
- **Fathomability is a first-class goal.** The tree must stay readable
  in a sitting. When it stops being that, rewrite rather than prune.

## How the researcher works

They pace the work by discussion. Answer the question first; do not
launch experiment sweeps unprompted; propose the cheapest discriminating
measurement and let them decide. They like being shown the mechanism
(a trace, a count, a per-seed row) more than a verdict. They commit;
the assistant does not commit unless asked. When they push back, they
are usually right about the principle and want the measurement that
settles it.

## Mechanics that took time to learn

- **Fingerprints before boards.** `docs/paper2/data/plane_fingerprint.py`
  runs in minutes and catches regressions on the cells that matter
  (K10/Z3 certified at 1.8; K100 = 7.26 at a fixpoint; turán 6.000 on
  10/10 random inits; path-60 ≈ 1.03; grid_200 pre-tail ≤ 1.76). Run it
  after every engine change. `docs/handoff/compare_baseline.py` diffs
  against the stored baseline.
- **Work budgets.** `max_asks` per cell (see `EXPERIMENTS.md`). A turán
  run at 15,000 asks takes ~4 minutes on a loaded server; ws ~8. On a
  laptop, start with the smoke cells and smaller budgets.
- **Long jobs survive the session only under nohup.** The harness
  background tasks of an AI session die when the session restarts.
  Pattern: `nohup .venv/bin/python script.py > log 2>&1 &` and a
  `done-*` sentinel printed at the end; poll the log.
- **`pkill -f` can kill your own shell** if the pattern appears in the
  command line that runs it (it did, twice). Use `pkill -f '[p]attern'`
  in a command that does not otherwise mention the pattern.
- **The working directory can reset between tool calls** in some
  harnesses; use absolute paths or `cd` at the top of each command.
- **Unknown kwargs are ignored by `attract_embed`.** A typo measures
  the default silently. Probe scripts used to carry a "typo fence"
  (assert kwargs ⊆ known fields); the new surface has five parameters,
  check them by eye.
- **The DP is exact; trust the oracles.** `align_reinsert` and
  `pack_lines` are brute-force tested (`tests/algorithms/test_field.py`,
  `test_plane.py`). When a number looks wrong, the bug is in the books,
  the readout, or the loop, not in the kernels.
- **Read `legal_acl`, not just ACL.** `legal_acl` is the engine's own
  answer before any polisher. `tail="none"` makes the two equal.
- **Determinism is a tested property.** Same `(seed, sched_seed)` ⇒ same
  embedding. Iterate dicts in sorted order; seed every RNG explicitly.
- **The archived engine** (commit `ea5d1cf2`) can be run for paired
  comparison from a git worktree with its `packages/ember-qc/src` on
  `PYTHONPATH`; `rewrite_board.py old` does that.

## Things I got wrong, so you do not repeat them

- I claimed the bar term (one qubit per active arm) was a constant on
  turán. It is the largest single differential there (162 active arms
  at the crystal vs 322 interleaved). Measure before asserting.
- I removed the interleaver's ε-ramp outright after an audit showed it
  made no bad accepts. It was a load-bearing tiebreak: without it,
  sparse graphs stall on plateaus (path-60 1.017 → 1.5). It is now an
  exact lexicographic tiebreak (`rank_scale(n) = 2n²+1`).
- I re-packed only the moved axis after a move (an audit suggestion).
  Cross-axis overload then persisted and accept-all wandered in
  overloaded states. The packer's guarantee is both axes.
- I made the x-axis a hard strip (real columns only) during search. A
  random start cannot be packed into 23 columns, every proposal was
  declined, and the engine never left its initial state on regular and
  ws. Both axes are extended past the chip during search now.
- I let the bounded projection pack rows before columns. Arms hanging
  past the last real brick are free in a row pack, so it stacked
  everyone on row 1. Columns first.
- I overwrote a tracked probe script by choosing an existing filename.
  Check `git status` before naming files in `docs/paper2/data/`.

## What I would do next, in order

1. Per-ask cost (the `stepR`/`stepQ` Python loops in
   `align_reinsert._arm`; one books computation per pack). Measure
   asks/s on ws before and after; the fingerprints must not move.
2. The sparse reach: why ws keeps 27-qubit chains at a full budget;
   the invariance map's sensitive cells (regular: order; ws: both;
   king: init). Candidates in `OPEN_FRONTS.md`.
3. Only then the tail question and Pegasus.
