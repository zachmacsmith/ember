# Experiment 027: corrected Sudoku development inputs

Preparation design and self-critique recorded before implementation, 2026-09-08 UTC.
This task creates inputs only. No embedding will be computed.

The [generalization protocol](../generalization_protocol.md#sudoku-corrected-sizes-scope-and-feasibility)
reserves box orders 2 and 3 for development and orders 4 and 5 for later,
separate purposes. This supplement will contain only orders 2 and 3. Original
manifest IDs 37900 and 37901 remain unchanged. New IDs 1000002 and 1000003 will
be collision-checked against that manifest and paired with explicit supplement
version, box order, and board side in evaluator-only provenance.

The generator will form a cell-conflict graph by adding cliques for every row,
column, and box. A separate all-pairs predicate will verify that two distinct
cells are adjacent exactly when they share a row, column, or box. Counts and
regular degree will be checked independently; tests will also compare with
NetworkX's Sudoku generator. Solver records will use only consecutive integer
vertices, edges, and empty attribute dictionaries.

Pre-implementation critique:

1. The previous error confused board side with box order. The public generator
   must accept only the two authorized box orders, declare board side separately,
   and reject 4 and 5 rather than incidentally generating reserved inputs.
2. Count checks alone cannot validate constraints. The independent pair predicate
   must detect missing or extra edges even when counts remain correct.
3. Provenance can accidentally become an initialization hint. All family labels,
   row/column interpretation, IDs, parameters, and generation details belong in
   sidecars, not graph metadata or attributes.
4. Reusing an output directory could erase the distinction from prior inputs.
   Creation must refuse every existing destination; loading must verify frozen
   file and semantic identities. An interrupted partial output must fail loading
   and cannot be silently resumed or overwritten.
5. Passing Z12 vertex and edge counts is only a necessary condition. These two
   fixed graphs provide development structures, not proven embeddability,
   stochastic puzzle replicates, or clean confirmation data.

## Frozen records

Implemented in [sudoku_supplement.py](../../../scripts/codex/sudoku_supplement.py).
The frozen bundle is
[027-sudoku-development-supplement](../../../results/codex/027-sudoku-development-supplement).
It contains two sanitized graph files, two evaluator-only provenance sidecars,
a copy of the original two Sudoku manifest entries, a generator source snapshot,
a protocol snapshot, and a completion manifest. No original manifest or generator
file was altered. The declared source generator version is
`sudoku-cell-conflict-v1`.

| New graph ID | Box order | Board side | Vertices | Edges | Regular degree | Row / column / additional-box edges |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| 1000002 | 2 | 4 | 16 | 56 | 7 | 24 / 24 / 8 |
| 1000003 | 3 | 9 | 81 | 810 | 20 | 324 / 324 / 162 |

The direct pair predicate checks all 120 or 3240 unordered vertex pairs,
respectively. “Additional-box” counts exclude contacts already present in a row
or column. Thus the three columns of contact counts sum to the actual undirected
edge count without double counting. Both graphs pass the declared necessary Z12
vertex/edge bounds; both sidecars explicitly retain
`embedding_feasibility="unproved"`.

The two numeric IDs were checked for collisions against all 31,149 inherited
manifest IDs. They are supplement identities, not edits or replacements for
37900/37901. Original 37900 still records 6561 vertices and 734832 edges; original
37901 still records 65536 vertices and 24084480 edges. Their exact entries are
preserved in `provenance/original_sudoku_entries.json`. The original manifest's
byte hash still matches its hash recorded before output creation.

Box orders 4 and 5 appear only as reserved, ungenerated orders in the bundle
manifest and frozen protocol. The generator API rejects those orders. No
confirmation or size-extension graph was created, and no clean-holdout or
structural-novelty claim is made. The sidecars explicitly record that comparison
against the complete inherited structure universe has not been performed.

## Hashes and storage boundary

| Artifact identity | SHA-256 |
| --- | --- |
| Supplement content identity | `e6e3036634164be8e5491d0c6b8d41e8d4fb042fd63fe3fd43fda3538018f047` |
| Bundle manifest bytes | `70c9b98f379e7edb835f5e74ee7975bf2ad51c70b230ebadddbf78ea118c8d6b` |
| Frozen generator source | `5d1fa6e28e8778e8d307ca49a00e2181a1ba857007366b9c5e75fbe45ceb2824` |
| Frozen protocol source | `5722855980017c5098b7ba4d86c31042841d7729328af8d956f10baf3751cdf6` |
| Unchanged original manifest bytes | `8396feb80c63f05cc64693dcfd99da345b87a1e7e4aa9542724f9491edac4a9d` |
| q2 canonical graph record | `fb89a8fafe5eebbb3480232c4027549d06a16efa473bc2a9850b91c40f9a1a65` |
| q3 canonical graph record | `52580f5927c9d291163cb251d6dacd171a5fb78e9fbf174051644c2a54940659` |
| q2 normalized labeled topology | `6c8c2ddd14fabf03524a8193f4c27c02fd1c8edc8179a24bb6826139d5c6bddc` |
| q3 normalized labeled topology | `efd0653128625e369aabf180384d75406589dab1969a0b6383ce97a7556be233` |

Canonical object hashes use sorted, compact JSON, matching `pilot.digest`.
Separate byte hashes cover every frozen file. Topology hashes use the actual
zero-based labeled node/edge record; they are not isomorphism-canonical hashes.
Scientific parameters, the row-major labeling interpretation, family, graph IDs,
and count-bound references occur only in provenance. Solver records contain
exactly `nodes`, `edges`, `metadata`, `node_attributes`, and `edge_attributes`, with
all attribute dictionaries empty. Tests confirm exact roundtrip compatibility
with `pilot.graph_from_record` and `pilot.graph_record`.

“Immutable” here is an API and verification property, not an operating-system
read-only permission: creation refuses an existing destination, even an empty or
partially written one; the completion manifest is written last. Loading checks
its content identity, every file hash, the exact permitted file set, absence of
symlinks, the two declared IDs/parameters, sanitized structure, all cell pairs,
and provenance against recomputed semantics. A damaged or incomplete bundle
fails explicitly. It is never silently resumed, regenerated in place, or repaired.

## Verification

[test_codex_sudoku_supplement.py](../../../tests/test_codex_sudoku_supplement.py)
passes **34 focused tests**. Besides analytic counts and every-pair checking,
the tests compare both complete edge sets with installed NetworkX 3.4.2
`sudoku_graph(q)`. Its independently maintained generator source is
`.venv/lib/python3.10/site-packages/networkx/generators/sudoku.py`, SHA-256
`90b33600fd07e3debab9888d3b5a001449afe6a05fb54fdb39f62e711c5ec4cd`.
The supplement's generator and loader use only the Python standard library;
NetworkX is a test oracle, not a runtime constructor dependency.

Tests cover reserved/ambiguous parameter rejection; graph/node/edge hint rejection;
invalid, duplicate, and foreign vertices/edges; a wrong graph with the same edge
count and degree sequence; ID collisions; unchanged inherited entries; all
frozen-file corruption; unexpected added files; symlinks; incomplete bundles;
semantic corruption even after consistent file rehashing; and independence of
mutable returned copies. The test command reported 0.28 seconds for the final
run, with the existing test environment's `dwave-networkx` deprecation warning.
That duration is test execution time, not an embedding benchmark.

```sh
.venv/bin/python -m pytest -q tests/test_codex_sudoku_supplement.py
.venv/codex-native/bin/python -I scripts/codex/sudoku_supplement.py verify
```

The one creation call used the isolated Python 3.10.19 interpreter:

```sh
.venv/codex-native/bin/python -I scripts/codex/sudoku_supplement.py freeze
```

Repeating that creation command now refuses the existing frozen destination.
MM is unavailable in that interpreter. Neither the generator nor loader imports
or invokes an embedding algorithm. No graph embeddings, timing comparisons with
MM, or feasibility witnesses were generated.

## Later runner integration API

`load_supplement(directory)` verifies the entire bundle and returns two items in
box-order order. Each item contains `id`, `graph_key`, `graph_record_path`,
`record`, and evaluator-only `provenance`. Graph keys are
`sudoku_supplement_v1_q2` and `sudoku_supplement_v1_q3`. Convert only `record` through
`pilot.graph_from_record`; do not merge the provenance into the graph. The source
hash is available as `item["provenance"]["source_hash"]`.

No adapter change was made in `pilot.py`. A later comparison must explicitly
declare this supplement, use both development inputs under its fixed policy,
freeze their identities with the solver, and preserve original Sudoku outcomes
as separate historical records. Changing Sudoku puzzle clues would not create
additional structures of this fixed cell-conflict graph.
