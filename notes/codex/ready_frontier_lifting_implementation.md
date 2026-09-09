# Dependency-ready lifting implementation

The isolated variant implements the accepted [ready-row policy](ready_frontier_lifting_hypothesis.md)
and [before-code accounting contract](ready_frontier_lifting_accounting.md).
`native-ready-branched-path` dispatches to
`factored/ready_branched_path_construction.py:branched_path_embed`, configuration
`{}`. Its base is `ready_lifting_construction.py`; only the new scheduler lives
in `ready_lifting_schedule.py`. Root owns descriptor addition and runtime freeze.

The reducer/journal/anchors, native core invocation, transfer, ordinary insertion,
blocked repair, pruning and original final validation remain inherited. Every
iteration computes readiness from **all recorded neighbors**, and chooses the
smallest completed direct singleton contact count, then highest pending journal
index. Counts are measured before current-row fill release/preparation. No
singleton count is treated as a full feasibility certificate. One ready row is
selected without physical scoring; its count remains null. A failed selected
insertion ends construction, with no attempt to choose another ready row.

The new stage records actual committed row indices and vertices. Original
`reverse_index` in a failure still means the original reverse-journal position;
new `journal_index` and `insertion_index` separate source provenance from actual
schedule position. `partial_requirements` comes from the committed R. The
processor retires a row only alongside E/R adoption after the deadline gate.
Interrupted key scans leave `selected_row=null`, preserve completed key records
and never use the best observed prefix. First departure reports a completed
choice, which may subsequently fail; the separate commit receipt is decisive.

The scheduler reuses existing target-index bitsets. It charges W target-word
units before each OR/XOR/AND/popcount, with W recorded from target size and
Python's integer digit width. Readiness, owner/site visits and record updates
are also charged to the same 20M budget. A periodic engine clock exception after
incrementing the engine counter still contributes that performed unit to the
scheduler subtotal. Interrupted precharges can exceed completed bigint work;
`bigint_operations_completed` distinguishes it. No physical-mask cache persists
between selections. This conservative accounting may itself bind before time;
it is not evidence that raising the cap would improve output.

Scheduler `wall` measures selection and pre-admission preparation and is inside
base expansion time. Constant-size retirement/receipt finalization is included
in the complete base/solver clocks, not added a second time. Actual final
publication remains subject to the original wrapper deadline. The inherited
branch operator, its limits, local deadline convention and final original gate
are unchanged; the wrapper body differs only in base import and identity text.
No new import invokes a constructor. Native/package import behavior stays the
same as the audited A053 path.

Six approved risk groups passed once in0.034s at
`results/codex/ready-lifting/checks/attempt001`; failures0, errors0, prohibited
import attempts0. They use stdlib graph predicates and the exact extracted new
lift loop with existing physical proposals mocked, so no public constructor,
native core or corpus call occurred. They cover the seven-node shared-fill
creator example in both logical orders and final R=original, an unmet filled
dependency, zero/tie/single-choice rules, a committed non-reverse-prefix state
followed by failure, no retry of another ready row, and clock/work interruption
during key scans/insertion/admission. Original inputs remain unmodified.

Static `source_equivalence.json` passes13 body comparisons: all seven inherited
top-level helpers/classes, the entire core/edgeless-anchor branch, physical
dispatch, released-fill pruning, final R/original validation and both wrapper
bodies after only declared identity-string normalization. Complete constructor
and wrapper diffs are saved. Original A053/native/physical helpers and measured
branch files retain their hashes. No broad inherited test suite was repeated.

Evidence also preserves the superseded explicit-word-array accounting draft and
its first before-code record. Root requested conservative charges on existing
bigints; `precode-v2.json` fixed that simpler convention before source existed.
No policy, numerical outcome or failed test motivated the amendment.

The prospective [A062 protocol](experiments/062_ready_lifting_screen.md) and
`062-preparation/comparison_plan.json` bind36 calls on the six approved existing
records, seeds0/1, all three arms on HYDE06. The mixed042/057 selection preserves
the same original012 provenance and exact target bytes. It contains no new
source graph. This is preparation only: no full-constructor result, improvement
or failure-prevention claim exists yet. Native-core failure remains out of scope,
and a zero direct count, destructive early fill release or scheduling cost can
make the fixed policy worse. The approved complete-output gate decides that;
there is no intermediate reach trial or proposed cap rescue.
