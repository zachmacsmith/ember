# Ideas

The live-reference / immediate-packing / streamed-cost implementation and
[audit](live-results.md) are complete (2026-09-17): 635 tests, 75 exact fixed-work
trajectory pairs, 2,520 query measurements, 120 board runs and 15 valid native
fingerprints. K100's final bookmark arrives after two or three queries (~40 ms).
The board succeeds on 24/30 versus baseline 27/30 and stock MM 25/30. Query
timing is roughly flat overall; complete decoding now consumes 80% of runtime.
The [design contract](three-orders.md) is the authoritative resumption point.
[Partition](partition-results.md), [feedback](feedback-results.md) and
[first-build](three-orders-results.md) reports retain historical comparisons.
Implementation does not establish universal superiority or convergence.

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

Reference vertices rotate through source neighbors, current x/y/contact half-order
windows, and anchor-only groups. Renominate before each destination query, then
pack immediately if it changes an order. Each round also tries direct whole-order
transfers. These nominations define unordered partitions; either side borrows its
sequence from any current master order while fixing the other side in destination
order. Compare the exact best merges across both directions before one adoption.
Whole-order transfers are included. The common
objective uses frozen slots and current contact roles, with rank span as an
exact tie break. Changed minimizing candidates, including equal-score moves,
are adopted; the incumbent family guarantees the minimum cannot worsen.
Intermediate books need not satisfy capacity. Decode each changed query's
orders from a canonical expanded feasible seed. Each
conditional minimum cut optimizes one axis while enforcing both orientations'
capacity; alternate until stable. Adopt the decoded state even if it is worse,
and retain the best finite native bookmark. An unchanged query needs no redundant
pack. No per-proposal feasibility rejection cascade is introduced.

Cost preparation streams changes attached to actual contacts and
endpoint thresholds. The exact DP still visits its merge grid; sparse event work
does not imply a sparse DP or eliminate the cost of balanced windows.

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

The [clique diagnosis](clique-diagnosis.md) now establishes two specific issues:
the source-edge rank-span tie breaker is constant on cliques, so equal-slot
ordering can block useful moves; and conservative reservation cost plus greedy
course allocation can prefer longer physical embeddings. The old clique
embeddings remain representable. The general feedback response is implemented;
see the current contract for its move family, tie rule and paired controls.

Discussion on 2026-09-15 prioritizes the move family over random tie breaking.
The plateau shuffles were a diagnostic, not evidence that noise is the remedy.
Before this update, each selected group kept its destination-order sequence.
The new family takes the sequence from any master order and weaves it into
the destination complement; the same two-prefix kernel supports this.
The full-order case gave K100 940→775 qubits in two deterministic proposals and
one decode. This was a small diagnostic witness. The family is now implemented and measured in
[the feedback report](feedback-results.md). [Probe](data/three_order_imported_strand_probe.py).

The paired controls show dense gains and mixed sparse results. Optimizing
contact order matters on the board, but borrowing spatial strands into that
order has no demonstrated overall advantage over its own-strand optimization.
Schedule changes still alter quality. In that preceding full-feedback scheduler,
transition-cost construction consumed about 65% of board time and packing less
than 1%. These are historical figures, not the cost profile of the live loop.

"Reservation cost" must be explained as a conservative space envelope across
the two staggered courses, not treated as a synonym for physical chain length.
Meaningful convergence should be judged from the current trajectory as well
as the best bookmark. Adopting tied DP optima removes one unnecessary gate;
it does not by itself reconcile a capacity-relaxed proposal with feasible
packing. Logical speed work should eliminate repeated preparation according
to its lifetime (source, current contact requirements, partition), and exploit
richer moves at the same DP state size. It should not introduce an intricate
per-edge update apparatus or a graph-specific scheduling policy.

The contact order can be understood as a geometrically informed assignment of
contact responsibility: earlier endpoints supply H, later endpoints supply V,
with choices priced using both spatial coordinates and shared bar hulls. Every
prefix defines a consistently oriented cut. Borrowing this sequence for a
spatial weave transfers that collective organization, in addition to the
requirements already transmitted through the objective. This is an information
channel interpretation, not a convergence theorem or a claim that contact rank
is physical distance. Adjacent nonneighbors can swap without changing contacts.
The clique witness establishes useful coordination, but cannot establish the
stronger value of learning t from geometry: every clique order has nested
prefix/suffix neighborhoods. That distinction needs testing on general inputs.

For the history behind these choices, see [the chronicle](notes.md),
[the old verdict ledger](attraction.md), [the old pipeline](anatomy.md), and
[the historical handoff](../handoff/README.md). Hardware observations are in
[fabrics](fabrics.md), and the stock solver reference is
[MinorMiner internals](mm-internals.md). These records do not supersede the
current design contract.
