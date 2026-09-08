# Fixed diagnostic group generation: implementation and author checks

2026-09-08. The isolated diagnostic helper implements the accepted
[four-stream rule](ownership_exchange_group_protocol_review.md), SHA-256
`147f5e7f7d4c0698003cd93caaf664a7d28f9a3de6ef77bc66f04e607c4d4352`.
No production algorithm, corpus input, remote process or embedding solver was
used or changed. This is author evidence pending independent review.

The API in [ownership_diagnostic_groups.py](../../scripts/codex/ownership_diagnostic_groups.py)
is `diagnostic_groups(embedding, source_adj, target_adj, *, limit=512,
deadline=None) -> (groups_or_none, info)`. A completed result is a list of tuple
payloads. `[]` denotes a completed empty selection; `None` denotes interrupted
or detected-invalid generation. Even `limit=0` completes the pools and their
sorting before selecting an empty vector. The diagnostic's fixed limit remains
512. No provisional prefix is published.

All mappings are ordinary dictionaries; chains are nonempty ordinary lists;
adjacency rows are ordinary lists or tuples; labels are ordinary integers.
Scalar/type/source-coverage/occupancy checks and occupied target-row checks
protect quotient construction. As root clarified before implementation, the
independently valid minor and stable simple undirected graphs remain caller
preconditions. This helper does not perform a third full chain-connectivity or
logical-contact validation. Source symmetry and unused target edges are not
re-certified here. Source integer representations must be supported by Python's
configured integer-to-text limit, because the accepted rank uses `repr`.

The maximum target degree includes unused sites through their adjacency-row
lengths. The quotient uses occupied physical adjacency, including contacts that
are not logical edges. Group representatives preserve the existing center/
neighbor/window order; canonical integer tuples serve only as keys. A shrinking
active-center sequence avoids an `n * max_degree` sparse-graph traversal.
Complete pools sort by footprint and canonical group key, then sizes one through
four alternate to the cap. Neither source names nor method-specific contexts
are consulted.

`info.complete` is authoritative. `generation_complete` means all pools finished
sorting; `selection_materialized` means the private capped vector was assembled.
Either can be true when a later deadline prevents publication. Only a completed
timely return sets `returned_groups` and `vector_sha256`. The vector hash is
SHA-256 of UTF-8 compact JSON arrays, with no trailing newline. Interrupted pool
counts remain partial or null rather than inferred from unseen windows.

`pool_counts` records, for each size, raw window occurrences, duplicates of an
already retained eligible set, over-cap windows, windows with no deletion seed,
eligible distinct groups and selected groups. On complete generation,
`raw = duplicates + over_site_cap + no_seed + eligible`. Filters follow the
specified order, so repeated ineligible occurrences count as repeated failed
filters. Actual source/target/occupied sizes and quotient edges are separate.

`events` are typed diagnostic counts, not CPU instructions or the ownership
search's elementary-budget units. In particular builtin sorting is counted by
calls/items, not comparisons. These heterogeneous counts must not be summed to
claim equal search work. Exclusive `stage_wall` values sum to complete helper
`wall`, including validation, sorting, encoding, hashing and finalization. All
helper cost belongs inside each arm's existing common deadline; no work or time
allowance is renewed. The separate search allowance and adapter remain root's
protocol decisions. Deadline checks surround loops and builtin operations, with
a final measured-time check rejecting late materialization. This is cooperative
timing, not a hard real-time guarantee for interpreter operations.

The guarded final author run at
`results/codex/ownership-diagnostic-group-checks/attempt002` passes **seven test
groups** in 0.83 seconds of suite time. The earlier six-group run is preserved
as `attempt001`; it also passed. Source bytes are identical in both runs.

| Synthetic evidence | Result |
|---|---|
| All 64 four-owner quotient graphs | Complete sequences match an independent tiny subset/window oracle, including 263 eligible existing ordered representatives; 384 limited calls match exact prefixes and complete pool counts. |
| Varied chain lengths and labels | Complete, path and star quotient fixtures match independent groups; original ordered payloads survive, including triples/quads whose order differs from numeric sorting. Reversing input and adjacency order preserves vectors and hashes. |
| Zero-excess fixture | The supplied maximum-degree-five minor is independently deletion-minimal. Manual deletion/transfer changes Q11 to Q10. The zero-excess singleton appears in the new sequence and is absent from literal existing grouping; the old two-chain group remains available, so this is not a superiority claim. No ownership proposer ran. |
| Caps and empty selections | Whole original footprints at 64/65 and singleton partners behave as specified; all-singleton and empty inputs return completed empty vectors. |
| Unused target degree | Adding an unoccupied degree-ten component changes the degree bound/ranked ordered representative exactly as the existing rule requires, while quotient adjacency stays fixed. |
| Real 512 cutoff | A supplied 20-owner, 40-site minor produces 823 eligible groups: 20/190/324/289 by size. The first 512 select 20/164/164/164. An independent full enumeration agrees; limit zero still finishes all 823 eligible-pool counts. |
| Interruption and invalid structure | All 399 observed fake-clock cut positions return no vector, including late encoding/finalization; the final crossing reports the measured overrun. Sixteen detected malformed scalar/structure cases return `invalid_input`. Input mappings/lists remain unchanged. |

The only executed repository comparator is the existing pure group enumerator,
loaded by explicit file path under a guard. No Ember package, D-Wave, MM,
busclique, NumPy or SciPy module was imported. The exhaustive subset enumeration
is confined to small test fixtures; the helper itself uses the accepted linear
window enumeration. These checks establish implementation behavior, not useful
contraction frequency or pipeline cost.

Frozen source SHA-256:
`838ffb1df7389e13fe110a318818c81eb16b7db7932ab03b3af54c8dd938daf6`.
Frozen checks:
`7f22249061b165f914b6470117a629fa8e80662a941a7fffed3ffb65bdfa9092`.
Final summary:
`e8fc5a92a87bb446fc2f414be14436bc67c0900173faf3425cda6bb838464549`.
The artifact manifest binds all retained scripts, source copies, raw fixtures,
results, command and interpreter identities. A portable repeat uses a **new**
output directory:

```text
.venv/codex-native/bin/python -I -B results/codex/ownership-diagnostic-group-checks/checks.py --repo /Users/dabh/ember --out results/codex/ownership-diagnostic-group-checks/root-repeat
```
