# Ideas

The first three-order native build is implemented on `factored` (2026-09-14).
The [design contract](three-orders.md) is the authoritative resumption point;
the [results report](three-orders-results.md) records tests
and retained comparisons. Implementation does not establish superiority over
MinorMiner.

## The current idea

Separate where chains sit from which endpoint supplies each contact. The state
is three independent random orders: x, y, and contact order t. For edge uv,
the earlier t endpoint supplies a horizontal bar and the later a vertical bar.
Required contacts create the bars and determine their reaches. A variable with
both bars includes its own crossing; a variable with one bar has no obligation
to reach an absent perpendicular arm. An isolated variable needs one free qubit.

On intact Zephyr, reserve `[(a-1)//2, b//2]` for a bar whose contact extrema are
a and b. A brick can cover contacts at **three junction rows**, including the
shared boundary. Bounding reservation depth by the physical courses/tracks
allows interval coloring to produce connected, disjoint chains with the
required contacts. The objective is lexicographic outside-chip reserved volume,
then total reserved volume. Conservative reservations may exceed physical
qubit use; both are measured.

The three interleavers search exact merges of selected subsequences against
frozen coordinate slots and the same current book. Every strict improvement of
the common fixed-slot objective, with rank span as an exact tie break, is
accepted. Intermediate books need not satisfy capacity. After a sweep or work-budget exhaustion,
decode its accumulated orders from a canonical expanded feasible seed. Each
conditional minimum cut optimizes one axis while enforcing both orientations'
capacity; alternate until stable. Adopt the decoded state even if it is worse,
and retain the best finite native bookmark. Packing runs once per sweep, with
no per-proposal feasibility rejection cascade.

## What this commits us to

- One general algorithm for sparse and dense inputs: no graph-specific patches,
  special initializers, or repairs. Same-lane abutment is deferred.
- One conservative accounting shared by proposer, packer, and converter, with
  exact comparisons and no penalty parameter.
- Native output by default (`tail="none"`). Explicit `tail="mm"` may polish
  an already valid native embedding; it cannot rescue a native failure.
- Intact Zephyr support only in this build. Broader hardware support needs a
  sound physical model and validation.
- Work budgets and measured elapsed time, separate compilation accounting,
  independent small exact oracles, and paired tests across dense and sparse
  instances. Old fingerprints are historical comparisons, not acceptance laws.

## Questions the implementation leaves open

The contact order permits acyclic contact orientations; it is a structured
family, not a representation theorem for every short-chain embedding. Frozen
slots approximate the cost after packing, and alternating exact conditional
packs need not find the joint coordinate optimum. Initialization and schedule
robustness must be measured. A contiguous merge preserves its two subsequences,
but sequences of singleton moves can still reach arbitrary permutations.

The next conclusions should come from the retained comparisons: where native
solutions succeed, what prevents the remaining cases, and whether representation
or search explains the cost gap. Evaluate common structural changes against
that evidence before adding more mechanisms.

For the history behind these choices, see [the chronicle](notes.md),
[the old verdict ledger](attraction.md), [the old pipeline](anatomy.md), and
[the historical handoff](../handoff/README.md). Hardware observations are in
[fabrics](fabrics.md), and the stock solver reference is
[MinorMiner internals](mm-internals.md). These records do not supersede the
current design contract.
