# Ember — `factored` branch

The **first build of the three-order native core is implemented** as of
2026-09-14. Start with the [design contract](docs/paper2/three-orders.md), then
the [results report](docs/paper2/three-orders-results.md) with retained
measurements. This is an implementation milestone; universal quality or speed
superiority over MinorMiner has not been established.

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

The interleavers optimize merges in all three orders against one common book
with coordinate slots frozen for an entire sweep. Every strict winner under
that fixed objective, including its exact rank-span tie break, is accepted.
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
- Count search work in DP evaluations (`max_asks`) and report actual elapsed
  time and compilation separately. Initialization and schedule robustness are
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
