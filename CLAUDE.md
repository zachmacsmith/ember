# Ember — `factored` branch

This branch holds the **attraction** embedder (`packages/ember-qc/src/ember_qc/algorithms/factored/`),
a placement-first minor embedder for D-Wave fabrics, on top of `main`'s benchmarking framework.
The s3.127 rewrite (2026-09-03) replaced the previous engine; the archived tree is commit
`ea5d1cf2` and the archived probes live in `docs/paper2/archive/probes/`.

**The algorithm in one breath.** A D-Wave fabric is a grid of lanes with a complete bipartite
junction wherever lanes cross, so a variable's chain is one horizontal run and one vertical run
whose reaches follow from two orders alone: the variable's rank on the x-axis and on the y-axis.
The engine (`plane.py`, ~400 lines) optimizes those two orders. A packer DP derives positions
under hard capacity; the stair rule derives every chain from the positions and the y-order; the
objective is capacity overload first, then derived chain length (spans plus one bar per active
arm); one move re-inserts a set of variables at its exact optimum over all weaves (an interleaver
DP), where the sets are the contiguous runs of each order at every scale and every variable's
neighbourhood; the schedule is a seeded bag; every proposal is adopted; the stop is a work budget
or a pass with no accepts. The adapter (`field.py`) turns the layout into qubits — books,
converter, completion, certificate — and on course-resolved Zephyr a zero-deficit completion is a
proof of validity, so minorminer is skipped. Minorminer is an optional polisher (`tail="mm"`).

**Ground rules.** Proposer and judge read one accounting (the books). No penalty methods, no λ:
capacity is the leading lexicographic key and infeasible proposals are declined. No mechanism
names a graph type. The init must not matter (it is two random permutations) and the question
order must not matter (measure it with the bag seed). Budgets are counted in DP evaluations
(`max_asks`), never in seconds, so a measurement never depends on the box's load. Fingerprints
(`docs/paper2/data/plane_fingerprint.py`) are the acceptance test of any engine change: K8/K10 on
Z3 certified at the template, path-60 ≈ 1.02, K100 = 7.26 at a fixpoint, turán n162 = 6.000 from
every random init, grid_200 pre-tail ≤ 1.76. Measure paired by (instance, seed) against stock
minorminer and against the archived default (a worktree at `ea5d1cf2`). Winners ship as defaults.

**Read `docs/paper2/ideas.md` first** (one page: the algorithm, the principles, the open fronts),
then `docs/paper2/anatomy.md` (the pipeline as built), `docs/paper2/fabrics.md` (measured
fabric facts), `docs/paper2/mm-internals.md` (what shipped minorminer actually does) and
`docs/paper2/notes.md` (the chronicle; s3.127 is the rewrite entry). `docs/paper2/archive/` is
history, not instruction.

The minorminer C++ fork (`scripts/mm_fork.patch`, `build_mm_fork.sh`; registered as `mmfork*`)
is unchanged: stock 0.2.22 plus two switches, byte-identical to stock when unset. The paper-1
Reweave line lives only on the `new-algorithm` branch; do not reintroduce it.
