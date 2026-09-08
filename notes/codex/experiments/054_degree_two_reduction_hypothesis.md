# A054: degree-two reduction with unchanged transfer expansion

Design only, before implementation, reduction diagnostics or candidate calls.
This instantiates the root's [degree-two proposal](../degree_two_reduction_proposal.md)
from fixed A053: `site_transfer_construction.py` SHA256
`801432d5e5d1fc1918e7eb933a3af443064ee0833030a5b962773f2b50f700a1`,
with `site_transfer.py` SHA256
`c61b2479f2a380c4ea412f9002859626db8f7579b16737bad141b079becd241b`.
The positive 053 screen supports retaining that ancestor within the reduced
line, with its planted/wheel losses and historical cyclic/cubic deficits intact.

**Hypothesis.** Retaining degree-three junctions may reduce artificial physical
contact requirements enough to offset a larger constructed core. Change only
the eligibility threshold from current filled degree ≤3 to ≤2. Core construction
and lifting continue to enforce the resulting filled requirements. This is
neither the rejected original-only policy nor soft guidance, and makes no
choice between complete candidate outputs.

## Exact policy

Copy the isolated A053 wrapper to a separately identified constructor. Replace
the two reduction eligibility comparisons—the initial heap and later neighbor
reinsertions—from `len(row)<=3` to `len(row)<=2`. Keep the heap key
`(current_degree, fixed_source_rank, vertex)` and stale-entry handling intact.
No degree-three fallback occurs if the core is large. Every surviving vertex
belongs to the core; do not re-reduce disconnected/edgeless components by a
different rule. Identity/doc/diagnostic additions state `elimination_degree_limit=2`;
they do not affect ordering. Transfer and repair modules remain byte-identical.

The anchor in each original source component remains its maximum-original-
degree vertex, with the same seeded rank resolving ties. Preserve normalization,
rank generation, filled-neighbor sorting, exact `created_fill` journal, original
native core configuration, eager imports and at most one native call. Preserve
edgeless-core handling, reverse order, current-row fill release, pending demands,
first-certified transfer, ordinary insertion, blocked repair, pruning, full
original validation and atomic requirement/mapping adoption. Helper preconditions
allowing up to three required neighbors stay unchanged; actual reverse rows now
have at most two placed neighbors. No threshold or mode is chosen from family,
observed result, core size, or target properties.

```text
compute the same original-component anchors and fixed ranks
heap = unprotected vertices whose current filled degree is at most 2
while a current eligible heap entry exists:
    S = its sorted remaining neighbors
    F = only absent pairs in S, added as fill (at most one edge)
    journal (v,S,F); delete v; enqueue newly eligible neighbors
construct every surviving core vertex using the unchanged A053 core path
reverse journal with unchanged A053 transfer / ordinary / blocked repair
validate the completed original minor and actual returned time
```

Keep the original absolute deadline, 20M global scans, 64 screened roots/four
ordinary branches, 64 transfer sites, 50k transfer scans per query/1M cumulative,
and 1M repair scans per query/5M cumulative. All subtotals remain inside global
work/time. A larger native core still receives only the remaining relative
allowance, with the existing outer deadline rejecting a late return. Preserve
all failed/unadopted core evidence and valid committed partial requirements;
there is no retry, renewed deadline, free alternative output, or cap increase.

For degree two with distinct neighbors `a,b`, contracting `a–v` and discarding
duplicate edges yields exactly deletion of `v` plus edge `a–b`. Degree-zero/one
removal is vertex deletion. Composing these operations proves that the final
core is a minor of the original source. Consequently any original embedding
induces some core embedding with no more occupied sites, so the **optimal**
core Q cannot exceed the original optimum. This proves neither the quality of
the heuristic's chosen core embedding nor a feasible/cheap reverse lift.
Existing `a–b` remains an original or older synthetic requirement; only a row
that actually created it may remove it on reversal.

## Proposed bounded diagnostic, before a 34-input candidate screen

First freeze a stdlib, source-only comparison on **all 34 existing 053 input
records**, in their manifest order, seed0. Each input has a fixed five-second
wall allowance and two-million source-operation allowance shared across both
threshold replays, witness construction and checks. Charge node/adjacency
visits, heap operations and copied witness members; sorting/allocation and
input parsing stay inside wall time. Retain interrupted prefixes with unknown
core/comparison/certificate outcomes rather than filling them with success or
zero. These are diagnostic limits, not candidate work units. Independently replay both thresholds
using the stated heap/anchor rule; check threshold3 against saved 053 journals.
Do not import or invoke a constructor, target converter, MM or graph generator.
Record every input's journal/core hashes, eliminated degree counts, core node/
edge counts, created fill totals, original versus synthetic core-edge counts,
anchor identities, and whether the core or order changes. Retain the 35 evaluator
memberships without dispatching on them. Raw input hashes and all zero-change
rows remain in the output.

For each threshold2 replay, compose an explicit **source-minor witness**:
start with singleton source branch sets; delete the branch set for a degree0/1
removal; for degree2 merge `v` into its smaller-labeled remaining neighbor.
This witness choice does not enter the candidate. Check nonempty connected
disjoint branch sets and original-edge witnesses for every final core edge.
It certifies the structural claim only, with no target embeddability inference.

After parent approval to implement, use a handful of focused checks: a cycle
whose first suppression creates an edge; a triangle where that edge already
exists; a four-cycle journal with older shared fill retained until its own
row reverses; disconnected/isolated components retaining their anchors; and
K4, where threshold2 retains all degree-three vertices. Compare each suppression
to direct source-edge contraction and verify the final original requirements.
Retain a small deadline/partial-journal case. No exhaustive graph sweep or
shared-validator changes are needed.

Then propose exactly **eight fresh-process calls**: A053 followed by A054 on
each of the four already frozen inputs—star128, wheel128, subdivided K5,
and exposed cycle126—seed0, 20 seconds each, unchanged work limits. Validate
original final/prefix mappings and report Q, all statuses, core size/Q, work,
solver/process time, transfers/cleanup and repairs. Save the exact input/runner
hashes and order before measuring. No MM call or historical timing comparison.

Star, cycle and the fully subdivided K5 are expected to have identical reduction
journals under both thresholds; they are controls for nonbinding equivalence,
not expected quality improvements. Wheel's degree-three rim stays in the core
under threshold2, so it tests the cost and reach of the larger native call.
Cubic inputs in the source-only table illustrate another possible change;
neither example selects policy. An unexplained nonbinding control difference,
invalid output or basic reach failure stops progression. No changed reductions
would falsify relevance on this panel. A changed-core quality loss or no quality
gain remains explicit for parent review rather than motivating threshold/cap
adjustments. No full 054 panel, seed/generalization run or registration follows
automatically from these checks.

**Self-critique.** The minor property constrains an optimum the inherited native
heuristic does not compute. Keeping junctions can discard useful simplification
and increase native runtime; many inputs may simply return to full-source native
construction plus wrapper cost. Degree-two suppression can still concentrate
future demands at poorly placed endpoints, while a one-site transfer may not
exist. The fixed reach panel primarily tests three unchanged cases and one
larger core, so it cannot resolve the quality effect on the whole development
set. These are conventional reductions, without a novelty, minimum-Q or
cross-class superiority claim. Retain every separate result and seek parent
review of this exact diagnostic before implementation or calls.
