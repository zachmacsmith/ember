# Independent implementation review of 040 offline replay

Result: the final reviewed offline revision passes the bounded independent
checks; no remaining blocker was found in this scope.

Scope: `offline.py`, the raw-converter instrumentation and the shared encoding
used by the accepted [040 design](physical_locality_diagnostic_review.md).
This review uses synthetic records and tiny converter-only cases. It does not
execute native construction, a corpus input, seeding, completion, pruning,
refinement or any embedding solver. The reviewer changed no author or prepared
file.

## Findings and corrections

The initial review identified these concrete issues, which the author accepted:

* A qubit-partition check did not bind recorded wire positions, lane assignments
  or grid dimensions to the actual target. The revised check reconstructs the
  expected map from the frozen target's coordinate attributes and checks the
  integer-label formula, coordinate ranges, complete membership and dimensions.
* Independent book reconstruction and equality checking were included in the
  incremental signature timer. They now have `book_verification_wall` outside
  the incremental subtotal. Actual signature construction, line conversion,
  candidate-cache work, merging and commit bookkeeping remain included.
* Snapshot chronology/counts and canonical adjacency order needed explicit
  checks. The revised code checks the initial state and first successive
  adoptions against recorded copy/ask/adoption counts and rejects reordered or
  omitted records. Published geometry hashes are verified against their receipt;
  a missing receipt remains unattested partial evidence.
* Offline encoding/publication needed separate accounting. The revised summary
  records those costs and publication failures. Dirty-line counts now distinguish
  old/new/union keys, removed lines and actual reconversions; deleted plus new
  keys must not be divided by the new-line count as a bounded fraction.

A final evidence-preservation correction now retains completed per-line records
and the current line key on caught interruptions. Full-reference failures also
retain explicitly uncertified partial chains/claims. Cache merge and terminal
deadline failures preserve the completed line records with no current line and
`committed=False`. A fatal process kill can still lose unflushed state; missing
work or output is not zero.

## Correctness assessment

The scalar book reconstruction agrees with the frozen formulas: source contacts
use the carried y-order; x endpoints are clipped to the grid; y endpoints retain
unbounded positive extent; rounded crossings use half-to-even rounding; and
snapped occupancy tuples retain the minimum unit span. The underlying bar and
tuple endpoints are kept distinct.

Line signatures retain sorted full arm items and their crossing targets. Dirty
lines are converted with an empty local claimed set, releasing their old claims.
Unchanged cached fragments are not modified. Merging restores orientation
`(1,0)`, ascending line order, source insertion order, empty chains and the exact
order of each emitted fragment. Full replay executes the original wire function
body up to a terminal callback before `_ensure_seeds`; removing that callback
restores its original AST.

The cache remains private through conversion, exact ordered full-output
comparison and deadline checks. A count-only match cannot pass when chain order
differs. Raw validity is independently reported against original edges; an
invalid but faithfully replayed raw state remains an observation. It is not an
ACL measurement or a reason to omit the state.

## Independent checks

The reviewer-owned
[`review_checks.py`](../../results/codex/040-physical-locality/independent-offline-review/review_checks.py)
imports no Ember package. It AST-extracts only the already frozen converter
helpers and uses fabricated wire maps; it never reads a corpus graph record.

Ten checks pass in the final
[`attempt003`](../../results/codex/040-physical-locality/independent-offline-review/attempt003/summary.json):
hand-computed clipping/rounding/carried-order books; 36 converter/cache pairs
plus unchanged-line reuse; fallback/signature ordering; second-line interruption
without cache mutation; equal-count/different-order rejection; wire corruption
that preserves the qubit partition; snapshot/order/count corruption; and a
synthetic clock that separates 100 units of diagnostic book verification from
the 7-unit incremental subtotal; and partial-work preservation after caught
reference-line, cache-line and terminal-merge interruptions. No prohibited or
Ember module was imported. The initial eight-check pass is retained as
`attempt002`; no failed run was discarded.

The final tested revision is:

| File | SHA256 |
| --- | --- |
| `offline.py` | `5d05f4428537d12e29fb5e6e47308ba14aa0d6f13752e85eba49f0fbaee720ed` |
| `common.py` | `4c75d637a6f96a4375fa7a38b92e3464b83116b483df3be0939a0fb637b64a6c` |
| `instrumentation.py` | `72eba8d970c0ba43e82c9cb20a11fff1487d8665c82536666a4fbedc326db13b` |
| Frozen `field.py` | `a055553988ba3db17ef3588986c1719070c3fcfae4bbfcce7a7084ffe45c7690` |

Exact repeat, using a new output directory:

```sh
.venv/bin/python results/codex/040-physical-locality/independent-offline-review/review_checks.py results/codex/040-physical-locality/independent-offline-review/reviewed_hashes_002.json results/codex/040-physical-locality/independent-offline-review/repeat001
```

The test harness refuses a different diagnostic revision or an existing output
directory. Passing this bounded offline review does not itself verify controller
supervision or authorize corpus execution. The existing nonbinding replay,
all-input coverage and fixed cost falsifiers still apply. Published partial
data remain conditional observations; full/cache equivalence is not a physical
embedding optimality certificate or an end-to-end runtime result.
