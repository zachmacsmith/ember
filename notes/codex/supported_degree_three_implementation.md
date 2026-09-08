# A055 implementation gate

The fixed source-representation rule and its bounded gates are complete.
The source-only pass processed all34 inputs once: all prior records agree,
all composed source-minor witnesses validate, eight reductions change against
053 and nine against054. There are23 actual nonlocal activations and16,007
additional eligibility/update/queue operations. Maximum total per-input
work/wall is167,440/0.06184s versus2M/5s. Every input, including all zero-change
cases, is retained in `a055-supported-degree-three/all_source_rows.csv` and
`source-comparison001`; diagnostic encoding/publication time is separate.

`factored/supported_degree_three_construction.py:reduced_core_embed` copies
A053. Only reduction, its two private charge/eligibility helpers and identity
change. The same anchors and degree/rank order are retained. Degree3 requires
one current neighbor edge; newly created fill enqueues both surviving old
neighbors and common neighbors of its endpoints. A stale heap entry rechecks
eligibility. Earlier fill may support a later contraction. The physical core,
transfer, ordinary insertion, blocked repair, pruning and validation paths
are unchanged, with one original deadline and inherited limits.

Added inspections/enqueues charge through the existing global scan meter.
`diag.reduction_detail.work` counts consumed units by category, already
included in reduction/global totals. Rejection/enqueue/activation event
counters are separate; rejection counts include repeated eligibility visits.
A nonlocal activation means a newly eligible degree3 vertex outside the
removed vertex's neighborhood had no supporting edge before that row's fill.
This is checked from current adjacency excluding exactly that new fill.
No eligibility cache is maintained.

A completed journal row is preserved immediately. Interruption retains its
completed prefix, the current reduction stage/row-plan status and performed
work; no incomplete core reaches native or physical expansion. Private source
mutation never changes the supplied graph. The returned partial physical
mapping on this path is empty, with honest deadline/work status.

Six focused tests passed on their first execution in0.019s: exact scope outside
reduction, supported/independent-neighbor cases,17-node activation/older-fill
provenance, direct-rescan ordering on fixed tiny graphs, charged work prefixes,
and a mid-update deadline preventing core admission. They compare actual
source-edge contractions and a full-eligibility rescan to the incremental
heap. No real native, corpus or reach call occurred. The one stub adapter
check for `native-supported-degree-three` passed in0.29s; removing its sole
registry entry gives the previous pilot AST.

The initial first-six selection is preserved. A timestamped root/user scope
amendment now includes all eight changed sources plus one unchanged control,
18 prospective calls. The [protocol](experiments/055_supported_degree_three_screen.md)
records the representation hypothesis, other plausible causes, exclusions and
full-constructor falsifier. No remote action or physical result is part of this
gate. Source-minor validity constrains an optimum, not native heuristic quality
or a cheap lift. High-degree common-neighbor scans can cost time; the seven-
input original proposal and eighteen-call amended protocol are not evidence
of improvement. Root reviews this gate before freezing the physical screen.
