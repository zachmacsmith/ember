# Balanced corpus readiness selection

Date: 2026-09-08 UTC. This is readiness planning only: no algorithm outcomes were
used, no downloads or comparisons ran, and no pilot code changed.

`results/codex/017-corpus-readiness/selection.json` selects **one original READY
input from each of 35 represented Ember families**. The 35 family rows correspond
to **34 exact normalized graph structures**. All selected graphs have 46–190
vertices, within the fixed 512-vertex cap. Sudoku is explicitly missing because
the original corpus has no count-eligible instance. No family required silently
relaxing the size cap.

## Selection rule and provenance

Only the immutable original `012-corpus-selection/selection.json` was read.
Its four input-error records remain errors for this selection; the later recovered
Kagome file was not silently added. The source ledger still records 485 requested
inputs, 481 READY inputs, and four initial input errors.

For each original family, retain rows with `status == READY`,
`0 < actual_nodes <= 512`, and the necessary ideal-Z12 count bounds
`actual_nodes <= 4800`, `actual_edges <= 45864`. Choose the minimum of:

```python
(abs(log2(actual_nodes / 128)), source_hash, manifest_id)
```

The logarithmic distance treats multiplicative deviations above and below 128
symmetrically. Source-hash and integer-ID ordering resolve ties deterministically.
These criteria were specified before any performance measurement on this
readiness selection. A family with no qualifying original READY row receives an
explicit missing-family record, rather than a larger or substituted graph.

The artifact's `identity.family_selections` contains the 35 chosen rows, scores,
available-candidate counts, original IDs/names, node/edge counts, original size
bins, graph and raw-file hashes, label-map paths, and source-record paths.
`identity.solver_inputs` contains the 34 deduplicated inputs and their complete
family memberships. Source files remain in the original 012 artifact; no graphs
were regenerated or altered. The original manifest-derived labels and metadata
remain sidecars, while solver inputs contain the already verified integer-labeled,
unweighted source structures described in note 012.

## Selected family representatives

| Family | Original ID | Vertices | Edges |
| --- | ---: | ---: | ---: |
| barabasi_albert | 10662 | 122 | 472 |
| bcc_lattice | 33402 | 91 | 216 |
| binary_tree | 4905 | 127 | 126 |
| bipartite | 1363 | 126 | 3969 |
| circulant | 3499 | 134 | 402 |
| complete | 1041 | 127 | 8001 |
| cubic_lattice | 33219 | 125 | 300 |
| cycle | 1829 | 126 | 126 |
| frustrated_square | 32816 | 121 | 420 |
| generalized_petersen | 4083 | 126 | 189 |
| grid | 1584 | 128 | 232 |
| hardware_native | 37603 | 128 | 352 |
| honeycomb | 32367 | 190 | 264 |
| hypercube | 4755 | 128 | 448 |
| johnson | 5242 | 120 | 1680 |
| kagome | 32122 | 131 | 236 |
| king_graph | 32616 | 121 | 420 |
| kneser | 5411 | 126 | 315 |
| lfr_benchmark | 31357 | 100 | 204 |
| named_special | 37761 | 46 | 69 |
| path | 2030 | 141 | 140 |
| planted_solution | 34404 | 133 | 175 |
| random_er | 6450 | 133 | 870 |
| random_planar | 31536 | 152 | 450 |
| regular | 14334 | 140 | 2800 |
| sbm | 30736 | 120 | 625 |
| shastry_sutherland | 33018 | 121 | 270 |
| spin_glass | 37302 | 160 | 12720 |
| star | 2229 | 127 | 126 |
| tree | 5058 | 121 | 120 |
| triangular_lattice | 31879 | 128 | 384 |
| turan | 3060 | 90 | 2700 |
| watts_strogatz | 22972 | 174 | 1740 |
| weak_strong_cluster | 33587 | 128 | 1988 |
| wheel | 2429 | 127 | 252 |

The missing family record is Sudoku: two original manifest entries, zero passing
Z12 count bounds, and zero original READY inputs. A future legitimate smaller
Sudoku generator would define a separately documented supplemental corpus.

## Exact duplicates and aggregation

Frustrated-square ID 32816 and king-graph ID 32616 have identical sanitized graph
records and normalized topology hashes. They are linked to one solver input:

```text
input_id: topology_ad061ab01ea949cfe9e99301
representative_graph_id: 32616
source_hash:
629d308e0f90fbbb26519f608092432e76d4b1197b8896cd737d72aaa1109449
normalized_topology_hash:
ad061ab01ea949cfe9e993013fde26052d059f31be29c63a2ef3a93d3a06c1c4
memberships: frustrated_square / 32816; king_graph / 32616
```

The representative is the smallest selected original ID in that exact-structure
group. Each algorithm/configuration/seed should therefore produce 34 solver tasks,
not 35 independent trials. The result can appear in both family coverage rows
with the shared-input relationship explicit, but it must carry **one structure
weight** in any aggregate. Do not duplicate it in a macro average or treat its two
memberships as independent evidence. If a future family-weighted analysis is
needed, define weights respecting these shared structures before making a claim.

Different normalized hashes are not a proof of non-isomorphism. This selection
inherits the limited exact-content audit from 012, so additional relabeled
isomorphisms may exist. Consequently “34 unique solver inputs” is an exact-record
statement, not proof of 34 independent isomorphism classes.

## Identity and verification

```text
readiness selection ID:
06c02356f8df5503b57f280ba4939c298cc05834c563a3da8a71f96fe245db98
original corpus selection ID:
d0b16cd1db9cb00ae0bce6a3499652f1a3d64d41eb8a5c5574c27cc60d481937
```

The readiness identity includes the original selection file's SHA-256, criteria,
all family choices, solver-input mappings, and explicit missing families. The
source file's checksum was verified unchanged after selection.

Each of the 35 family choices was independently recomputed using exact rational
distance `max(n, 128) / min(n, 128)`, whose monotonic logarithm yields the specified
ranking. This confirmed every winner without depending on floating-point tie
behavior. All chosen graph hashes, normalized topology hashes, node/edge counts,
the 34 unique solver inputs, and all 35 membership mappings were checked. No
performance measurement formed part of these checks.

This tranche supports an end-to-end readiness screen across the available family
names. One graph per family cannot establish family-level mean ACL, variance,
success rates, size generalization, or all-family superiority. It remains
inherited development data; neither new seeds nor its deterministic selection
make it a clean holdout. Every passing count screen still leaves actual embedding
feasibility unproved.
