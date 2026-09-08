# Actual Ember development corpus selection

Date: 2026-09-08 UTC. This is input preparation, not an embedding experiment.
No algorithm results were read or used to choose graphs. No comparisons were
launched and `pilot.py` was not modified.

The initial artifact at `results/codex/012-corpus-selection` requests **485 graph
IDs** across **250 nonempty family/size cells**. It contains **481 verified graph
inputs**, spanning **35 families and 249 cells**, plus four explicit input errors.
All 36 original family names, including Sudoku, remain in its coverage ledger.
One identical-ID retry later recovered the missing Kagome input separately; three
random-planar URLs still returned HTTP 404. The initial selection and its errors
are unchanged. This is inherited development data, with no clean holdout claim.

## Fixed selection rule

`scripts/codex/corpus.py` reads the packed manifest directly and normalizes its
short keys. It does not use `load_graph()` or the existing metadata-only alias
redirection. Each requested ID therefore refers to its own original file.

The bins were fixed before downloads or graph execution:

| Source vertices | Initially verified inputs |
| --- | ---: |
| 1–16 | 60 |
| 17–64 | 70 |
| 65–128 | 65 |
| 129–256 | 66 |
| 257–512 | 66 |
| 513–1024 | 56 |
| 1025–2048 | 52 |
| 2049–4800 | 46 |

For each family/bin, rank entries by SHA-256 of the JSON object containing seed
`ember-codex-development-v1`, family, bin, and manifest ID; take the first two
entries, or the sole entry if only one exists. Manifest ordering has no effect.
The complete list of requested IDs is saved before loading begins. Failed or
duplicate inputs are never replaced by another ID. This is sampling manifest
entries, not a uniform sample of isomorphism classes: aliases in the inherited
manifest can increase a structure's selection probability. That limitation is
visible in the duplicate audit, and this small development selection does not
support population inference.

The necessary Z12 count screen uses `n <= 4800` and `m <= 45864`, checked against
the generated ideal `zephyr_graph(12, 4)` in a regression test. It admits 30,200 of
31,149 manifest entries; 949 violate at least one count bound. Exclusions are
based on manifest counts, whose correctness was not checked by downloading every
excluded graph. Every selected raw graph's actual counts are checked independently.
Passing these necessary conditions **does not prove embeddability**. Target
topology names stored in legacy metadata are not used to remove source families.

Sudoku IDs 37900 and 37901 have manifest sizes `(6561, 734832)` and
`(65536, 24084480)` respectively, so neither passes the count screen. Legitimate
smaller Sudoku instances would be a separately named supplemental corpus, with a
documented encoding and generator. These originals must not silently be resized.

## Full family coverage

“Eligible” below means passing manifest count bounds only. “Cells” counts nonempty
eligible bins. “Ready” refers to the unchanged initial selection, before recovery.

| Family | Manifest | Eligible | Cells | Requested | Ready | Errors |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| barabasi_albert | 3532 | 3416 | 8 | 16 | 16 | 0 |
| bcc_lattice | 26 | 22 | 7 | 14 | 14 | 0 |
| binary_tree | 11 | 11 | 8 | 10 | 10 | 0 |
| bipartite | 208 | 208 | 5 | 10 | 10 | 0 |
| circulant | 351 | 337 | 8 | 16 | 16 | 0 |
| complete | 56 | 56 | 5 | 10 | 10 | 0 |
| cubic_lattice | 76 | 74 | 8 | 16 | 16 | 0 |
| cycle | 65 | 63 | 8 | 16 | 16 | 0 |
| frustrated_square | 72 | 70 | 8 | 16 | 16 | 0 |
| generalized_petersen | 782 | 755 | 8 | 16 | 16 | 0 |
| grid | 149 | 143 | 8 | 16 | 16 | 0 |
| hardware_native | 42 | 41 | 8 | 15 | 15 | 0 |
| honeycomb | 162 | 151 | 8 | 16 | 16 | 0 |
| hypercube | 11 | 11 | 8 | 10 | 10 | 0 |
| johnson | 74 | 74 | 7 | 14 | 14 | 0 |
| kagome | 144 | 130 | 8 | 15 | 14 | 1 |
| king_graph | 72 | 70 | 8 | 16 | 16 | 0 |
| kneser | 41 | 38 | 5 | 10 | 10 | 0 |
| lfr_benchmark | 61 | 61 | 7 | 14 | 14 | 0 |
| named_special | 12 | 12 | 2 | 4 | 4 | 0 |
| path | 65 | 63 | 8 | 16 | 16 | 0 |
| planted_solution | 2616 | 2616 | 6 | 12 | 12 | 0 |
| random_er | 3024 | 3009 | 8 | 16 | 16 | 0 |
| random_planar | 216 | 216 | 7 | 14 | 11 | 3 |
| regular | 3521 | 3375 | 8 | 16 | 16 | 0 |
| sbm | 1125 | 1125 | 5 | 10 | 10 | 0 |
| shastry_sutherland | 72 | 72 | 7 | 14 | 14 | 0 |
| spin_glass | 598 | 595 | 6 | 12 | 12 | 0 |
| star | 64 | 63 | 8 | 16 | 16 | 0 |
| sudoku | 2 | 0 | 0 | 0 | 0 | 0 |
| tree | 27 | 26 | 8 | 15 | 15 | 0 |
| triangular_lattice | 196 | 196 | 8 | 16 | 16 | 0 |
| turan | 607 | 607 | 5 | 10 | 10 | 0 |
| watts_strogatz | 12550 | 11988 | 8 | 16 | 16 | 0 |
| weak_strong_cluster | 456 | 444 | 8 | 16 | 16 | 0 |
| wheel | 63 | 62 | 8 | 16 | 16 | 0 |

The initial missing-input records are:

| ID | Name | Bin | Initial error | Identical-ID retry |
| --- | --- | --- | --- | --- |
| 31704 | planar_n931_s4 | 513–1024 | HTTP 404 | HTTP 404 |
| 31705 | planar_n1042_s0 | 1025–2048 | HTTP 404 | HTTP 404 |
| 31710 | planar_n1167_s0 | 1025–2048 | HTTP 404 | HTTP 404 |
| 32106 | kagome_3x6 | 65–128 | DNS resolution failure | Verified successfully |

`random_planar / 1025–2048` is the only nonempty requested cell with no initial
ready graph. Retry files and the complete second-attempt record live under
`recovery/`; they do not alter `selection.json`. The recovered Kagome source hash
is `2e9dc97bcc8f8ff323e668dcb924703891fc634250dcdacf9237c9a76a813591`.
Its second-attempt record retains the earlier DNS error under
`previous_attempt_error`, explicitly distinguishing it from the successful retry.

## Structural identity and label audit

Each raw file must match the manifest hash prefix and requested ID/name/family.
The decoder requires a simple undirected graph, unique node declarations, explicit
edge endpoints, no self-loops, no duplicate undirected edges, and exact actual
counts matching both manifest and raw count metadata. It accepts the legacy
node-link `links` field and the newer `edges` field, but rejects ambiguous input
containing both. Isolated vertices remain in the solver graph.

Algorithms receive deterministic integer labels and unweighted adjacency only.
Source family, name, coordinates, vertex attributes, edge weights and graph
metadata remain in sidecars/raw files rather than becoming algorithm hints. This
is the declared unweighted minor-embedding problem. The original-label mapping is
preserved for witness translation. Target coordinate metadata remains a separate
matter for the pilot's ideal Z12 target and is not stripped by this source adapter.

Records distinguish several hashes:

- `raw_sha256`: exact original bytes, including metadata and serialization order.
- `source_hash`: full sanitized record, directly compatible with
  `pilot.graph_record()` and the pilot's task/source identity.
- `normalized_topology_hash`: vertices and edges after deterministic integer
  relabeling, ignoring attributes and node/edge serialization order.
- `labeled_topology_hash`: retains original ordered labels as well as adjacency.
- `node_order_hash` and `edge_order_hash`: preserve original serialization order
  for audit rather than treating order changes as independent graph structures.

Equal normalized topology hashes identify the same indexed embedding problem
(with a recorded inverse mapping), apart from cryptographic collision risk.
Different hashes do **not** prove non-isomorphism: sorted-label relabeling is not
isomorphism canonicalization. No global pairwise isomorphism search or misleading
WL-hash uniqueness claim was made.

The initial 481 rows contain **460 distinct normalized structures**, with
**20 duplicate groups**: 11 within-family and 9 across families. Examples include
complete/cycle IDs 1001 and 1800; complete/frustrated-square/king IDs 1007, 32601,
32801; cubic-lattice/hypercube IDs 33200 and 4751; and binary-tree/tree pairs.
Several BCC and LFR requests duplicate another selected structure in the same
family. All memberships and original IDs are retained; these are not independent
graph samples. `cells[].distinct_normalized_topologies` records cases where two
requested IDs supply only one exact structure. No metadata alias was substituted.
Duplicates involving unselected corpus files or differently labeled isomorphic
structures remain unmeasured.

480 initial inputs already used ordered zero-based integer labels. ID 37761 was
the sole exception; it was relabeled with the mapping preserved. The sanitized
inputs remove 7,522 node attributes and 141,703 edge attributes in total. Source
weights changing without adjacency changes do not create new embedding problems.

## Artifacts and proposed pilot adapter

The generation command was:

```sh
.venv/bin/python scripts/codex/corpus.py results/codex/012-corpus-selection --download
```

The directory contains `original-manifest.json`, `request.json` with the complete
31,149-entry coverage/exclusion ledger, `selection.json`, `coverage.md`, validated
`graphs/ember_<ID>.json`, original `raw/` files, inverse label maps under `labels/`,
and the exact selection-time `selector.py`. The initial selection used 51 local
files and downloaded 430 verified original files; it did not modify the bundled
library, existing cache, or `.verified.json`. The initial artifact was approximately
267 MB before recovery and selector-source additions. Choose a small readiness
tranche before transferring or executing the entire selection.

Immutable initial identities:

```text
selection:
d0b16cd1db9cb00ae0bce6a3499652f1a3d64d41eb8a5c5574c27cc60d481937
original manifest SHA-256:
8396feb80c63f05cc64693dcfd99da345b87a1e7e4aa9542724f9491edac4a9d
selection-time selector SHA-256:
16c0557a4c9360835186b4ae3d4988b6d12fbadc553be33f2b5e05d4ff093d31
```

After that freeze, the current adapter gained an explicit incomplete-input option;
this does not change requested IDs, graphs, source hashes, or the initial artifact.
Use the current `corpus.py` API:

```python
loaded = corpus.load_selection(selection_path, allow_missing=True)
coverage = loaded.selection["families"]
missing_inputs = loaded.missing_inputs
for graph_id, graph_key, graph, record in loaded:
    # graph_key is ember_<ID>; pilot.graph_record(graph) hashes to source_hash.
    # Freeze a chosen readiness subset before any algorithm executes.
    ...
```

Default `allow_missing=False` rejects the incomplete initial selection. The
explicit option returns an iterable object retaining the complete original
selection and all missing-input records; iteration yields only verified inputs.
An adapter must save that full selection identity/coverage together with the
predeclared readiness-subset IDs. Distinguish 485 requested corpus inputs, 481
initially ready inputs, the chosen subset, and actual algorithm task counts. A
download error is not an algorithm failure, and an unselected ready graph is not
an attempted trial. Preserve corpus ID/family/bin metadata outside solver inputs.

The root agent owns any pilot schema change. The suggested interface is a
`--corpus-selection` path, explicit incomplete-input acknowledgement, and a frozen
ID subset. Copy selected sanitized records into the run and verify their
`source_hash`; retain the full corpus-selection ID and source/target identities.
Never regenerate the selected graph from its name or import the legacy loader's
alias resolution. Seed repeats remain repeats on the same graph. Exact duplicate
structures need grouped analysis and, if computation is shared, an explicit
membership mapping rather than extra supposedly independent samples.

## Verification and interpretation limits

`tests/test_codex_corpus.py`: **17 tests passed**. They check deterministic ranking,
bin/count boundaries, empty-family retention, order/attribute/relabel invariance,
isolate preservation, malformed-source rejection, within/cross-family duplicate
membership, immutable selection behavior, metadata identity, incomplete-input
acknowledgement, and exact pilot round-trip compatibility. None run an algorithm
or download a graph.

Separately, all 481 initial ready raw files were reparsed and rechecked against
their manifest identities, actual counts, normalized topology hashes and stored
solver hashes. Their reconstructed NetworkX graphs reproduced exact
`pilot.graph_record()` hashes. The frozen selector source hash was also checked.
The recovered Kagome file passed the same decoder during its separate retry.

Two manifest IDs per cell do not establish family distributions, variance,
success rates, density coverage, or all-family superiority. The fixed node bins
provide a broad development screen; density and generator-parameter coverage still
need an explicit design before confirmation. Large sources can pass the count
screen and nevertheless be impossible or expensive. Existing full-library tuning
means every inherited source here remains development data, irrespective of new
algorithm seeds, relabeling, or this selection's randomization.
