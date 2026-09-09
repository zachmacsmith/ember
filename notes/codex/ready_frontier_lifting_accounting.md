# Ready-lifting pre-code accounting and publication contract

Frozen before implementation/check outcomes, supplementing the accepted
[policy](ready_frontier_lifting_hypothesis.md). The ordering key and eligibility
are unchanged. Prototype files will be `ready_lifting_schedule.py`, an isolated
A053 copy `ready_lifting_construction.py`, and an isolated wrapper copy
`ready_branched_path_construction.py`. Descriptor:
`native-ready-branched-path` → wrapper `branched_path_embed`, configuration `{}`.
The existing A053/native/helper/branched-stage files remain byte-for-byte intact.

Each selection scans the immutable journal in forward index order, skipping
committed indices; each row visit and each tested recorded-neighbor membership
costs one existing construction unit. No incremental readiness cache is used.
The highest pending index is the legacy comparator. With one ready row, no
physical scoring occurs and its count is null, not a fabricated zero.

For multiple ready rows, reuse the engine's existing `bit`, `adj_bits` and
`all_bits` target indexing. Let W=max(1,ceil(target_n /
sys.int_info.bits_per_digit)); record both W and the digit width. Build occupied
and needed-owner boundary masks by OR-ing the existing per-site masks. Charge
one unit per row/owner/site/dependency visit and W units before every whole-target
OR, XOR, AND or popcount. Charge one per completed key or selection/retirement
record. Dictionary/set accesses accompanying a charged visit have no second
fee. This is a conservative operation convention, not equal CPU time: a short
bigint still receives W units. Partial precharges survive interruption even
when the corresponding operation never executes; completed bigint operations
are also counted separately. No new bitset format or persistent physical-state
cache is introduced. Each ready row scans its full neighbor list even after an
empty intermediate intersection. No partial-key winner is published.

All units call the same engine `scan()`: scheduler work is a subset of its 20M
total and its expansion-stage counts. No separate allowance or restored units.
Check the original absolute deadline at phase boundaries and through the
existing periodic metered checks; check again after completed keys, before
publishing a selection and immediately before admitting the insertion. Physical-mask
setup, failed/partial scans, diagnostic construction and readiness maintenance
consume real wall time. Report scheduler wall separately as a subset of the
base stage time; do not add it a second time. Native/core timing, transfer and
repair sublimits, and the final branch policy remain unchanged.

Each selection receipt starts before traversal and retains completed key
records on cooperative interruption. It distinguishes ready-set completion,
key-scan completion, selected row, admission preparation and committed row.
A partial scan never publishes a selected winner. A failed chosen insertion
stops without trying another ready row. The scheduler processes no row until
its complete insertion and bookkeeping are ready; pending-set retirement and
the row-ID/commit receipt update occur in the same unchecked constant-size
publication block as E/R adoption after the final deadline check. Units for
those bounded updates are reserved immediately before that check, so a stop
there may charge reserved work without committing it. This conservative case
is explicit rather than claiming exact CPU instruction accounting.

Save original journal indices and vertices for every committed row, selection
keys/ready counts, first choice differing from the highest still-pending index,
and exact stopped phase. Reconstruct partial R from committed row IDs, not from
a reverse-prefix length. Failed selected-row diagnostics also carry its original
index; the old reverse_index field denotes its position in the original reverse
journal, and insertion_index separately gives actual attempted position.
The committed mapping and R remain untouched on interrupted keys, insertion,
pruning or admission. Publication of a late overall result remains uncredited
under the existing wrapper deadline rule. A fatal process kill can still lose
unflushed diagnostics; no new persistence claim is made.

Only the approved tiny bookkeeping/order/rollback/deadline risk checks follow,
with core calls mocked where necessary. No public constructor/corpus run,
saved-final gate, profiling or cap change is authorized before root freeze.

Before-code amendment: root requested reuse of existing engine bigints with
conservative W-unit charges instead of explicit word arrays. The superseded
array-accounting draft and first freeze record are preserved in the evidence
directory. No source or test existed before this amendment.
