# Hand-off: the attraction embedder (branch `factored`, September 2026)

This folder is the entry point for a researcher, and for an AI assistant
working with them, who is picking up this project cold. Read this file
first, then the others in the order listed. Everything here was written
against the tree at the commit that carries this folder; if the code
and the docs disagree, the code is the truth and the docs are the bug.

## What this project is

A **placement-first minor embedder** for D-Wave quantum annealers, meant
to replace D-Wave's `minorminer` on Zephyr-class hardware. The idea:

- A D-Wave fabric is a grid of **lanes** with a **complete bipartite
  junction** wherever lanes cross. A qubit is a bar on a lane. A chain
  (the set of qubits standing in for one source variable) is one
  horizontal run plus one vertical run, and a source edge is a
  crossing of one variable's run with the other's.
- Therefore a variable's chain follows from two numbers: its **rank on
  the x-axis and its rank on the y-axis**. The whole state is two
  orders. A packer DP turns orders into positions under hard capacity;
  the "stair rule" turns positions into chains; the objective is the
  derived chain length with capacity as the leading key.
- The search re-inserts sets of variables into an order at their
  exact optimum (an interleaver DP). Every proposal is adopted; the
  best judged state is kept. Budgets are counted in DP evaluations,
  never seconds.
- On course-resolved Zephyr the layout converts to qubits with a
  **certificate**: a zero-deficit completion is a proof of validity and
  `minorminer` is never called. `minorminer` is an optional polisher.

The engine is `plane.py` (about 430 lines). The whole live package is
about 3,900 lines. It replaced an 8,200-line predecessor on
2026-09-03 after an audit found the old engine's bad numbers were
caused by its init, its unit family, and a schedule that spent 93% of
every pass on edge pairs that never improved anything.

## Where things stand (the honest summary)

Against stock `minorminer` at 60 s and against the archived previous
engine, on the standard 10-cell board (see `EXPERIMENTS.md`):

- **Dense graphs**: solved to the template. K100 = 7.26, K140 = 9.77,
  spin glass 10.85, turán n162 = **6.000 on every random start** (the
  old engine: 9.46; minorminer: 11.3). Nothing else comes close.
- **ER100 (degree 10)**: 4.45 with the tail — the best number this
  project has recorded.
- **Sparse graphs** (regular, small-world, king; grid and honeycomb
  are a tie): the new engine **loses** to the old engine with its
  polisher by 0.3–0.8 ACL. Two measured causes, both open fronts: a
  new-engine DP evaluation costs about five times an old one, so the
  60-second arm finishes a fraction of a pass; and at a full work
  budget the engine's own answer on small-world graphs still carries
  chains of ~27 qubits.
- **Invariance**: the engine is order-free and init-free within
  tolerance on 7 of 10 cells; regular and ws are order-sensitive and
  ws is init-sensitive at the budgets used.

The exact tables, the commands that produced them, and the frozen
result files are in `baseline/`. `compare_baseline.py` re-runs the
fingerprints and prints better/worse per cell against them.

## Read in this order

1. `ALGORITHM.md` — the algorithm from first principles, with
   diagrams. Read all of it before touching the engine.
2. `CODE_MAP.md` — every function in the live package, the data
   shapes, the call graph, the tests, the parameter surface.
3. `EXPERIMENTS.md` — environment, graph loading, the harnesses, the
   budgets, the nohup convention, expected runtimes, how to compare.
4. `HISTORY.md` — how the design got here and, most valuable, the
   table of ideas already tried and refuted. Do not re-derive them.
5. `OPEN_FRONTS.md` — prioritized next steps with the falsifier for
   each.
6. `AI_HANDOFF.md` — the working conventions and the owner's
   principles, written for an AI assistant; the pitfalls we hit.
7. `baseline/RESULTS.md` — the frozen numbers and how they were made.

The older project documentation lives in `docs/paper2/` (`ideas.md`,
`anatomy.md`, `fabrics.md`, `mm-internals.md`, `dp-internals.md`, and
the chronicle `notes.md`, whose entry 3.127 is the rewrite). The
previous engine's full history and its probe scripts are archived in
`docs/paper2/archive/`; the previous engine itself is at git commit
`ea5d1cf2`.

## Quick start (five minutes)

```bash
git clone https://github.com/zachmacsmith/ember.git && cd ember
git checkout factored
python3.11 -m venv .venv && . .venv/bin/activate
pip install -e packages/ember-qc
python -m pytest tests/algorithms/test_plane.py tests/algorithms/test_attraction.py -q   # ~2 min
python - <<'EOF'
import networkx as nx, dwave_networkx as dnx
from ember_qc.algorithms.factored import attract_embed
r = attract_embed(nx.complete_graph(10), dnx.zephyr_graph(3, 4), seed=0,
                  tail="none", max_asks=2000)
d = r["diag"]
print(r["legal_acl"], d["max_chain"], d["certified"], d["mm_skipped"], d["stopped_by"])
# expect: 1.8 2 True True fixpoint
EOF
python docs/handoff/compare_baseline.py smoke   # a laptop-sized comparison
```

## The five parameters

`attract_embed(source, target, *, timeout=300, seed=0, max_asks=None,
sched_seed=None, tail="mm", **ignored)` — `timeout` is a safety net;
`max_asks` is the real budget (DP evaluations); `seed` seeds the init
(two permutations); `sched_seed` seeds the question order (defaults to
`seed`); `tail` is `"mm"` (minorminer grind + ball pass) or `"none"`.
Unknown keyword arguments are silently ignored, so a misspelled
parameter measures the default.
