# Independent review of the 040 physical-line diagnostic

Recommendation: proceed to the bounded diagnostic implementation under the
amended design, then review its frozen code and synthetic checks before any
corpus execution. The decomposition is valid for the current raw converter.
It establishes neither final embedding quality nor inexpensive proposal pricing.
No candidate code, embedding call, prefix call, corpus experiment or remote
operation was executed in this review. Experiment 039 and its diagnostic helper
remain unchanged.

The reviewed [design](physical_locality_diagnostic_review.md) has SHA256
`c5dd735cdc1713baab9b7f76dc6641949877ee366682d6cd280e537cec8e3750`.
The original design is preserved at
[`design-before-independent-clarifications.md`](../../results/codex/040-physical-locality/design-before-independent-clarifications.md),
SHA256 `2d71deb4ea57cc7b9dfc110451c9f7f17280109e3a3ea8a53b42e0de300a53eb`.

## Preparation independently checked

Read-only Python standard-library checks rehashed the entire
[`prepared`](../../results/codex/040-physical-locality/prepared) directory, compared
its exact membership with the two frozen upstream maps and two selection
ledgers, and compared every copied file's actual bytes with its upstream file.
All 153 declared files pass; there are no symlinks or undeclared files apart from
the preparation manifest itself.

| Evidence | Verified identity |
| --- | --- |
| Preparation manifest | `eca3cb626475eba348a5154d91c9ee993e04f58940b72fca2a9a0bc27d3a9230` |
| 153-file map digest | `a5ddbd44613f37ebfa63c2e4232920573775fd3727e647dedce0b968b945bdcf` |
| 48-file source snapshot | `63a0aed1a880cbf008aa68ae7201aed7a4da635dea9362e5d296b1d13a91a473` |
| Frozen 039 manifest | `84197f8e3c2e4543ba5786eb51e31b1a57e1ade4de32c7ed51cb55d5d6a25bc3` |
| Upstream evaluator manifest | `dc7632dd7d50cb72e81360f495d5b1a98c3a2ce68121c0ba4191dbfe9fa6c145` |
| 103-file evaluator map digest | `ed83c891a0eb981c4d070b0a7ad17e88605064e2d2c848f87d2cd9f100199102` |
| Canonical target digest | `38cde794d3c1461054a45b5a660d157737b019c19cb9a7b38e2027730e3d5938` |

The 153 copies comprise 48 source files, 103 evaluator/input files and two
selection ledgers. The upstream manifests are bound by their hashes in the
preparation manifest; they are not additional copied evaluator files. An eventual
standalone diagnostic freeze must retain these provenance bindings explicitly.

All 34 inverse label maps are bijections and reproduce every original source
edge in the corresponding normalized graph. Every normalized node sequence is
exactly `0..n-1`, with empty graph/node/edge metadata. The selection retains 35
family memberships over those 34 solver inputs. The target bytes match frozen
039: 4,800 nodes, 45,864 edges, ideal Zephyr Z12. Its recorded coordinate tuples
independently yield 400 distinct course lanes, each with 12 sites, over 50
orientation/line pairs. All 4,800 physical IDs occur once, their coordinate
attributes agree with linear-label arithmetic, and every consecutive stride-two
lane pair has an original target edge. These are record checks, not a new
`TileGrid` construction or embedding test.

One deliberately stronger preliminary check failed: the evaluator label map is
**not** always the original JSON node insertion order. For `ember_37761`, positions
32 through 45 in that original order contain
`34,35,36,37,40,41,42,43,33,38,39,44,45,32`; the map at those positions contains
`32,33,34,35,36,37,38,39,40,41,42,43,44,45`. The topology/bijection check passes.
This is an ordering distinction, not corrupted preparation. The amended design
correctly requires workers to consume the exact frozen normalized record and
keeps originals/maps evaluator-only. Directly loading the original node order
would change native relabeling and could change seeded geometry.

Current `field.py` and `plane.py` also match their frozen 039 copies, respectively
`a055553988ba3db17ef3588986c1719070c3fcfae4bbfcce7a7084ffe45c7690` and
`5459df9e949df9b0b2e855f100361770b054523542a67c06ece50cbfa1b9b1e8`.
The [earlier physical cost model](physical_cost_model.md) contains historical
converter failures; the reviewed source already has the 035 interval-DP fix.
Those historical failures must not be reported as current behavior.

## Why the decomposition and observation boundaries are sound

In frozen `field.py:700`, `_convert_line` reads only the specified line's wire
runs, ordered arm items, crossing targets, stride and live claims. Physical
qubits in other orientation/line pairs cannot intersect that line's runs.
Consequently a conversion starting from an empty local claim set produces the
same line fragments as full conversion, provided earlier claims on that same
line are built by that one call. Do not leave the old line's claims in a global
occupied set while reconverting it.

Cache complete actual outputs, including unsuccessful required-hull seating,
alternate parity and fallback. Preserve sorted `(a,b,v)` items and full target
sets; span cost or DP assignment alone is insufficient. The minimum-span class
assignment is not an exact physical-lane optimization. The second returned
counter is currently zero even when seating changes parity. A miss can still
emit fallback qubits. None of these quantities establishes raw validity.

Global cached chains must concatenate fragments in the converter's orientation
order `(1,0)` and ascending line order, preserving local emission order and
empty source chains. Equality of total Q alone would miss ordering, ownership,
fallback and omission errors. Actual complete chain lists, claimed sets and
counters must agree with the unmodified converter prefix immediately before
`_ensure_seeds`. Raw invalidity remains an observed result; it must not silently
remove a state from the diagnostic or become a claim of low ACL.

The two proposed capture locations match `plane.arrange`: after the initial
three-pack state and first `best` assignment, and after each complete adoption
and bookmark update. The current search adopts every feasible proposal, including
equal or worse geometric scores. Capturing only new bookmarks would answer a
different question. Keep both carried orders: ties in packed coordinates do not
recover the y-order used to assign contacts. Reconstruct contacts from that rank,
then bars and occupancy tuples using `snap=True`, `min_span=0`, `floor=False`,
`kappa=1`, and `ybound=False`. Tuple endpoints can differ from bar endpoints.

Initial packing plus the first 32 adoptions is a bounded early-trajectory sample.
Both calls must continue to their original stop or 1,000 asks. The final best
state and possible projection belong to the replay comparison, not the captured
adoption sequence. Exact equality of complete non-time outputs and actual
proposal streams, with both deadlines nonbinding, supports observed
noninterference only for those paired calls. Identical wrappers and equal
deadlines alone do not prove it. Explicitly whitelist timing fields omitted from
comparison rather than deleting arbitrary diagnostics with similar names.

## Resolved process, timing and publication concerns

The amended design resolves the material issues raised during this review:

* Geometry uses one absolute 150-second worker backstop around two separate
  60-second common-deadline calls. Offline analysis uses a different supervised
  process with its own 60-second total allowance, armed before heavy imports and
  decoding. Its time cannot come from a reset geometry alarm or leftover time.
* The completed reference is persisted before capture starts. RAM-only snapshots
  can be lost if the worker is killed; such snapshots are missing. No filesystem
  work is introduced inside the capture hooks to claim otherwise.
* Candidate line-cache changes remain private until all work and the timely full
  comparison finish. A mismatch or expired comparison cannot publish a partial
  cache. Finalized records use no-clobber atomic publication. A killed process
  cannot promise preservation of an unflushed in-memory cache; the last durable
  complete record is the recovery boundary.
* Incremental update cost includes signatures, dirty-line conversion, candidate
  cache work, merging and commit bookkeeping. Diagnostic full conversion,
  equality checking and original-graph validation have separate timers and are
  included in total diagnostic cost. Excluding them from the proposed update
  subtotal must not exclude the update's own required data copying or merging.

The unchanged per-line DP has no cancellation checks and can be expensive.
Cooperative checks between lines therefore require the independent alarm and
process-group cleanup. Preserve partial progress without calling a late or
incomplete conversion exact. If equality fails, the exactness claim fails even
when the incremental count looks better.

Keep the predeclared falsifiers: incremental updates costing at least full
conversion reject a speed benefit; updates exceeding 10% of the corresponding
captured transition work defer per-proposal use. Compare sums over the same
completed post-initial pairs and report each input's coverage. Initial cache and
setup costs also belong in amortized totals. Zero-transition inputs have no
transition ratio. Incomplete inputs preclude an all-input cheapness claim;
conditional results cannot pass the threshold by silently dropping them.

## Remaining pre-execution requirements

No mathematical blocker remains in the amended design. Implementation still
needs a frozen, independently reviewed bundle and synthetic evidence for:

1. Exact AST restoration after removing only the two capture hooks; unchanged
   reference body, proposal wrappers without mutation or RNG consumption, and
   zero conversion/completion/pruning/refinement calls during geometry.
2. Deep snapshot copies, stable numeric encoding, the two hook positions, final
   projection exclusion, and exact original-label/canonical-order boundaries.
3. Full-prefix versus per-line equivalence on ordering, fallback, missing-line,
   occupancy, changed-target and same-count/different-output examples.
4. An interrupted dirty-line update and an interrupted comparison leaving the
   committed cache unchanged; no-clobber output rejection and preserved missing
   observations after a fatal alarm.
5. Separate process deadlines, inherited lock ownership, termination/reaping,
   exact timer boundaries and unchanged fixed observation/cost thresholds.

These are implementation checks, not permission to launch or a claim about
observed locality. Even a successful 040 diagnostic would cover adopted early
states and raw conversion only; it would not establish the cost of pricing
rejected proposals, final ACL, or performance across graph families.
