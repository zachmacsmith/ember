# Ember — `factored` branch

The **three-order native core with bidirectional order feedback is implemented**
as of 2026-09-15. Start with the [design contract](docs/paper2/three-orders.md),
then the [feedback results](docs/paper2/feedback-results.md): 590 tests and 245
timed cases, including paired mechanism controls and schedule sensitivity.
Dense results improve; sparse results are mixed, and full feedback does not
establish an overall advantage over one-way borrowing. Universal quality or
speed superiority over MinorMiner has not been established. The
[first-build report](docs/paper2/three-orders-results.md) retains earlier results.

The [clique diagnosis](docs/paper2/clique-diagnosis.md) establishes order
plateaus and physical losses in course assignment/bookmark ties. The old clique
embeddings remain representable; fitting clique axis packing is jointly exact
for reservations. The feedback change broadens the move family while leaving
packing, physical accounting, coloring and bookmark selection unchanged.

The attraction embedder lives in
`packages/ember-qc/src/ember_qc/algorithms/factored/`, alongside the repository's
benchmarking framework and graph dataset support. Its current native target is
**intact Zephyr only**.

## Current algorithm

State is three independent random permutations from one seed: spatial orders x
and y, and contact order t. On each source edge, the earlier t endpoint supplies
the horizontal bar and the later endpoint the vertical bar. Contacts determine
which bars exist and their reaches. Two bars of one variable meet at their own
crossing; a single bar has no absent-arm anchor. Isolates receive unused qubits.

An arm reaching junctions a through b reserves the inclusive brick interval
`[(a-1)//2, b//2]`. A reserved brick can touch **three junction rows**. This
conservative model supports a sound interval-coloring conversion on intact
Zephyr. Search minimizes outside-chip reserved volume, then total reserved
volume; reservations and actual physical qubits are reported separately.

For each selected group, the interleavers compare sequences borrowed from all
three current orders, forward and reversed, keeping the destination complement
fixed. Duplicate strands are solved once; whole-order transfers are included.
Coordinate slots stay frozen for the sweep. Changed minimizing candidates,
including exact ties after the rank-span tie break, are adopted. The incumbent
family guarantees a nonworsening fixed-slot score; no donor equality is imposed.
Packing happens **once per sweep**, including a sweep cut short by its budget:
a canonical feasible expanded
seed is packed by alternating exact conditional minimum cuts. Each conditional
pack enforces capacity in both orientations. This is not a joint global x/y
optimality claim. The decoded sweep is adopted even when its score worsens;
the best finite native bookmark is retained for output.

The public entry point is `attract_embed` in `placement.py`; `plane.py` owns
search and decoding, `native_model.py` the shared book, `packing.py` conditional
minimum cuts, and `order_dp.py` the interleavers. The default is
`tail="none"`. Explicit `tail="mm"` may polish an already valid native result;
it cannot legalize a failed native attempt. There is no implicit MinorMiner
fallback.

## Working rules

- Improve the common design. No graph-family detection, special initializers,
  per-instance repairs, or cascades that reject accepted proposals during
  decoding. Same-lane abutment is deferred until after this core.
- Keep proposal, packing, and conversion accounting consistent. Use exact
  lexicographic comparisons, not tunable penalties or floating tolerances.
- `max_asks` counts selected-group queries, each now comparing up to six
  distinct strands. Report actual DP solves/cells and preparation/fill time,
  elapsed time, and compilation separately. Initialization and schedule robustness are
  measured goals, not theorems or assumed acceptance criteria.
- Check changes with independent optimization oracles, physical embedding
  validation, and paired dense/sparse measurements. Historical fingerprint
  numbers are comparison evidence, not mandatory targets for the new model.
- Keep the design contract and results report current. Do not restore an older
  rule merely because it appears in a handoff or chronicle.

## Historical context

[Ideas](docs/paper2/ideas.md) is the short current summary.
[Hardware facts](docs/paper2/fabrics.md) and
[MinorMiner internals](docs/paper2/mm-internals.md) remain useful references.
[The handoff](docs/handoff/README.md), `docs/paper2/anatomy.md`,
`docs/paper2/attraction.md`, and `docs/paper2/notes.md` record earlier designs;
the handoff index identifies their historical scope. The predecessor before
the s3.127 rewrite is archived at `ea5d1cf2`, with probes in
`docs/paper2/archive/`.

The separate C++ MinorMiner fork (`scripts/mm_fork.patch`, `build_mm_fork.sh`,
registered as `mmfork*`) is stock 0.2.22 plus two switches, byte-identical to
stock when unset. The paper-1 Reweave line lives on `new-algorithm`; do not
reintroduce it into this core.
