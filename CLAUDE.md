# Ember — `factored` branch

The **live-reference / immediate-packing / streamed-cost** implementation and
audit are complete (2026-09-17). Start with the
[design contract](docs/paper2/three-orders.md) and
[live audit](docs/paper2/live-results.md): 635 regression tests, 75 exact
fixed-work trajectory pairs, 2,520 query measurements, 120 board runs and 15
valid native fingerprints. K100 reaches its final reservation bookmark in two
or three queries (~40 ms). The board succeeds on 24/30 versus baseline 27/30
and stock MM 25/30. Query timing is roughly flat overall; complete decoding
now consumes 80% of native board time. Universal speed, quality and convergence
claims remain unproved.

The [partition](docs/paper2/partition-results.md),
[feedback](docs/paper2/feedback-results.md) and
[first-build](docs/paper2/three-orders-results.md) reports preserve earlier
implementations and measurements; their older scheduling rules are historical.

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

Live groups around reference vertices define unordered partitions. A fixed
seeded reference permutation and rotating source/x/y/contact/anchor relation
provide coverage. Order windows have size floor(n/2); source groups are N(v),
anchor groups are {v}. Renominate from current state before every destination
query. Each round also opens with whole-order queries. Either
side can borrow a sequence from any current order, forward or reversed, while
the other side keeps its destination sequence. Compare the union before one
adoption. Duplicate pairs are solved once; whole-order transfers are included.
Coordinate slots stay frozen for one query. Changed minimizing candidates,
including exact ties after the rank-span tie break, are adopted. The incumbent
family guarantees a nonworsening fixed-slot score; no donor equality is imposed.
Packing happens **after each changed individual query**, including a query
interrupted between completed candidates:
a canonical feasible expanded
seed is packed by alternating exact conditional minimum cuts. Each conditional
pack enforces capacity in both orientations. This is not a joint global x/y
optimality claim. The decoded proposal is adopted even when its score worsens;
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
- `max_asks` counts destination/partition queries, each comparing at most 11
  distinct merge pairs (at most six for singleton/complement partitions).
  Report actual DP solves/cells and nomination/preparation/fill time,
  elapsed time, and compilation separately. Initialization and schedule robustness are
  measured goals, not theorems or assumed acceptance criteria.
- No group catalogue or sampled-no-op stopping rule. Each vertex is seen once
  per n reference visits; a reference visit contains three fresh destination
  nominations. Event-based costs retain the exact fixed-strand merge problem.
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
