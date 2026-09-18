# Three-order native core

Native design approved 2026-09-14; bidirectional feedback approved 2026-09-15.
The **live reference / immediate packing / event-cost** change was approved
2026-09-17 and is implemented and audited, with 635 regression tests passing.
Its contract below supersedes stored
nomination catalogues and once-per-sweep packing. See
[live results](live-results.md) for implementation status and evidence.
The shared-partition extension is implemented and audited on 2026-09-17; its
merge-family contract supersedes selected-side-only borrowing rules.
See the [partition audit](partition-results.md) for 611 tests, 75 embedding runs,
and 2,520 query measurements. Exactness and native validity pass; overall
embedding-quality improvement is not established.
The feedback implementation and its paired experiments are complete on `factored`.
See [feedback results](feedback-results.md) for validation, measurements and limits,
and [first-build results](three-orders-results.md) for the preceding implementation.
This document is the resumption
point; historical notes describe
older algorithms and must not silently reinstate their rules.

## Intent and decisions

Search a large structured family cheaply. Use one general algorithm for sparse
and dense source graphs, with no graph-family detection, special initializers,
or graph-specific repairs. Changes should improve the overarching design.

The state is three permutations: x, y, and contact order t. Earlier t endpoint
u of edge uv supplies H(u), later endpoint v supplies V(v). Required contacts
determine bar existence. A mixed variable includes its own crossing in both
hulls; a single bar has no obligation to reach an absent perpendicular bar.
Isolates require one unused physical qubit each.

The owner selected **core first, abutment later**, and now **packing after each
changed individual order query**. Each query freezes completed coordinate
slots while comparing its full candidate family. Adopt its selected changed
canonical winner, including exact ties, then decode unconditionally even if
the decoded score worsens. Its intermediate book may violate capacity and is
never returned as an embedding. Retain the best usable decoded bookmark. No
legalization or feasibility-rejection cascade sits between these components.

Score: lexicographic (outside-chip reserved qubits, total reserved qubits),
with source-edge rank span across all three orders as the interleaver's exact
tie break. No floating epsilon or tunable capacity weight. Actual physical
qubits are reported separately: conservative reservations can contain slack.

## Conservative physical model

Initially support intact Zephyr Z(m,t), using interior junction lines 1..2m-1
and C=2t courses/tracks per line. An arm reaching junctions a..b reserves

    I(a,b) = [(a-1)//2, b//2]  (inclusive).

For physical course j, the actual indices are [(a-j)//2, (b-j)//2], a subset
of I. Interval depth <= C on every lane permits greedy interval coloring onto
the C physical courses/tracks. Same-color reservations are disjoint; the
actual runs are connected and disjoint. Complete interior junctions supply
all designated source contacts and mixed-variable corners. Thus materializing
a feasible book needs no parity search, completion, or MinorMiner repair.

**Correction to the discussion:** reserved brick z can be touched by contacts
at junctions 2z, 2z+1, OR 2z+2. The proposed two-row O(nL) packing recurrence
omitted this shared boundary and is not valid. Do not implement it.

## Exact conditional packing

For one moved-axis order, opposite coordinates and roles are fixed. Own-axis
bars have fixed reservation intervals. Their same-row capacity is equivalent
to monotone predecessor constraints y[j] >= y[i]+1. For each opposite lane,
sort its bars' first and last contact ranks independently. At its kth start
(k>C), its (k-C)th end must precede that start in reserved-brick coordinates:

    y[start] >= 2*(y[end]//2)+3.

Keep the greatest predecessor for each destination in each constraint family.
Together with order monotonicity, these are O(n) implications on coordinates.
Expand thresholds [y[i]>=line] to a minimum-weight closure graph with O(nL)
nodes/arcs. The minimum cut minimizes exact unary endpoint costs while
enforcing BOTH capacity directions. This is a graph-size bound, not an O(nL)
runtime claim. Use checked int64 flow capacities; installed SciPy 1.17.1's
maximum_flow silently truncates capacities to int32.

The implementation propagates exact lower bounds forward and upper bounds
backward before constructing the graph, removing thresholds forced by those
bounds. This preserves the conditional optimum and makes the graphs much
smaller in the retained large-instance probe. A compiled integer push-relabel
kernel solves the remaining graph; residual source reachability selects the
smallest minimizing coordinate vector.

Total reserved cost uses distinct minimum and maximum endpoint coefficients:
maxcount*floor(y/2) - mincount*floor((y-1)/2), plus active-bar constants.
Outside-brick length is max(hi-m+1,0)-max(lo-m,0); bars on outside lanes count
their whole reservation. This remains a unary objective under a fixed order.

## Total decoder and query contracts

Every decoder starts anew: consecutive groups of at most C active arms per
lane provide a feasible seed on an expanded ideal fabric. The extended m is
large enough for these groups and the actual chip. Alternate the same exact
conditional packer on both axes, starting with the seed's fixed axis bit.
Select the componentwise-smallest optimum in each pack. Equal-score updates
can only lower coordinates; stop when an entire sweep leaves them unchanged.
Coordinates are derived from orders and fixed seed, not inherited search state.

Before an interleaver query, fill dormant positions by integer monotone
interpolation between adjacent active coordinates; clamp open ends. Freeze
all slots for that query, including dormant slots. After a changed query,
decode before nominating the next group. An unchanged query can reuse the
same coordinate completion. Spatial candidates use fixed contact nets from
the current contact order. Contact candidates derive their own requirements
from their proposed sequence. All candidates share the same coordinate slots
and objective.

The deliberate approximation is that fixed-slot proposals do not optimize
subsequent packing. Canonical decoding removes historical dormant positions
but does not prove that the interleaver can discover every useful arm birth.
Alternating exact axis packing does not prove joint global optimality.

## Validation and evidence

Retained tests include independent exhaustive merge/packing oracles, physical
conversion checks, tests forbidding implicit MinorMiner, and query/adoption
tests. The existing fingerprint cases and paired dense/sparse board record
work, real elapsed time, compilation separately, success, physical qubits and
chain lengths. Performance limitations warrant structural analysis, not a
collection of per-graph exceptions.

Planning probes (inline only; useful checks, not retained benchmark artifacts):
230 small conditional problems / 8,845 monotone assignments matched direct
capacity, costs and brute optima. A real 486-vertex WS pilot with SciPy flow
took roughly 0.13-0.47 s per conditional pack, motivating per-sweep decoding.
These are not production timing or embedding-quality claims. The retained
tests and [benchmark artifacts](three-orders-results.md) supersede these probes.

## Implementation status

- `native_model.py`: source normalization, contact requirements, conservative
  books, dormant-coordinate interpolation and independent capacity check.
- `order_dp.py`: compiled exact forward/reversed merges for all three orders,
  with sparse event costs, query-local strand caches and best-only traceback.
- `packing.py`: separation constraints, threshold costs, checked integer flow.
- `plane.py`: live reference nominations, query-local frozen slots, immediate
  canonical decoding after changes, unconditional adoption and
  finite bookmarks. A deadline is checked between kernels; a running kernel
  finishes, and the last valid decoder state and earlier bookmark survive.
- `placement.py`: intact-Zephyr verification, interval coloring, physical runs,
  isolated qubits and independent embedding validation. Default `tail="none"`;
  explicit `tail="mm"` can only polish an already valid result. An unsuccessful
  or unavailable polish preserves that native result.
- Diagnostics separate asks, accepted moves, decoder calls, axis packing work,
  packing/interleaver/decoder time, reserved and outside qubits, actual physical
  qubits, active orientations and MM calls. `legal_acl` describes native output;
  `physical_qubits` and `max_chain` describe the returned, optionally polished
  embedding. Timeout includes startup; `timeout=0` retains the existing meaning
  of no wall limit. Cold compilation is measured separately in experiments.
- Abutment, defective hardware and Pegasus are deliberately outside this build.
  Conditional optimality is established by the stated subproblems and oracles;
  global packing optimality and universal superiority over MM are not claimed.


## Bidirectional order feedback (approved 2026-09-15)

This historical section records the first feedback implementation. The
shared-partition extension below retains its accounting and replaces its
nomination/query family. The live-reference contract supersedes both older
schedulers, packing cadences and stopping rules.

For one destination and selected vertex set, keep the destination complement
in its current order. Extract the selected strand from each current x/y/t
order, forward and reversed, deduplicate, and solve each distinct oriented-strand merge problem.
The destination-forward family contains the incumbent, so the completed
candidate union cannot worsen (outside reservations, reservations, rank span).
Adopt changed tied optima. The deterministic tie priorities are: changed over
unchanged; genuinely borrowed over either destination strand; cyclic donor
order (destination+1)%3, (destination+2)%3, destination; forward over reverse.
An alias of a destination strand does not earn borrowed priority. Existing DP
path ties stay unchanged. This is exact over the stated union of merges only.

Retain dyadic blocks and distinct neighborhoods and include the whole vertex
set once per destination. Whole-set transfers have no merge choices and use
direct scoring. Donors are read from live proposal orders; frozen slots and
once-per-sweep decoding are unchanged. There is no hard equality between t and
either spatial order. A worse decoded sweep continues as the current state;
its bookmark never controls acceptance.

One ask remains one selected-group query, now containing up to six unique
strand evaluations. Report actual DP solves/cells and preparation/fill time.
Share invariant preparation within a query; use two value rows and traceback
parents. Check deadlines between candidate kernels and retain the best
completed candidate plus incumbent when interrupted. A complete unchanged
sweep is a fixed point of these returned candidates; equal-cost changes may
continue until the budget. timeout=0 still disables the wall limit, so setting
max_asks=None together with timeout=0 permits unbounded exploration. Record current versus
bookmark scores and recurring sweep states; do not infer convergence from a
flat best-so-far curve. These state hashes cover orders and coordinates, not
the schedule RNG, and do not prove a deterministic search cycle.

The packer, reservation model, interval coloring, and bookmark selection are
held fixed. Deferred work includes abutment, physical-cost-aware coloring, and
simpler exact packing. The current packer can leave empty rows: conservative
shared-brick capacity and endpoint parity both make skipping a row useful.

Completed measurement protocol: preserve the strict native snapshot; compare it with neutral
self-strand moves, whole-order-only borrowing, frozen t, one-way borrowing
(spatial orders may borrow t but t keeps its own strands), and full feedback.
Use the existing fingerprint and ten-case board, paired seeds 0/1/2, one worker,
a common 10-second warm board limit, and separately recorded compilation.
Repeat full-feedback initialization seed0 with schedule seeds1/2. Stock MM is a
separate comparison; standalone runs forbid MM calls. These measurements must
distinguish coordination from learned feedback rather than assume the latter.
Baseline provenance is retained in data/feedback_baseline.json. The
[feedback report](feedback-results.md) separates measured gains from unresolved
mechanism claims: dense cases improve, sparse results are mixed, and full
feedback does not establish an overall advantage over one-way borrowing.


## Why the same two-prefix DP supports borrowed orders

Fix the selected strand A and the destination complement B. At table entry
(i,j), exactly the first i vertices of A and first j vertices of B have been
emitted. That prefix SET is known regardless of the path taken to the entry.
The two choices are to emit the next vertex of A or the next vertex of B:

    F[0,0] = (0,0,0)
    F[i,j] = min_lex(
        F[i-1,j] + (outside_A, reserved_A, cut[i,j]),
        F[i,j-1] + (outside_B, reserved_B, cut[i,j]))

Omit predecessors outside the table. cut[i,j] counts source edges crossing
the emitted prefix; summing these cuts gives moved-order edge rank span. The
other two orders' spans are constant for this query.

For a spatial move, slots are nondecreasing: charge each opposite bar at its
first and last emitted contact. Their reserved-length contributions are
1-floor((slot-1)/2) and floor(slot/2), respectively, with matching outside-chip
charges. Its own-orientation bar's cost depends on its assigned slot. For a
contact move, the known prefix determines the emitted vertex's earlier and
later neighbors, so both complete arm hulls and any mixed corner can be
charged immediately. These facts make (i,j) a sufficient state even when A
comes from another order. Capacity and later packing are absent from this
subproblem. Fixed parent ties return one canonical optimum per strand; the
union compares those representatives without enumerating all tied paths.

The DP keeps two value rows, but parents, cuts and transition tables still
require O(|A||B|+n) memory. Per-query bounds and roles are shared among donors;
transition tables depend on each particular strand and are rebuilt. Timing
fields are nested: transition_wall is part of preparation_wall; dp_wall is
fill plus traceback; direct_wall is whole-order scoring. interleave_wall also
includes Python candidate selection and metadata overhead. packing_wall is
part of decode_wall, so these totals must not be added twice.


## Shared partitions and either-side borrowing (2026-09-17)

Historical nomination/sweep policy; the exact either-side merge family and
canonical orientation remain current. Live nominations and per-query packing
below supersede this section's scheduling rules.

### Decisions and established subproblem

At sweep start, nominate half-overlapping blocks from **all three** orders at
the existing approximately halved sizes, open source neighborhoods N(v), and
the whole vertex set. Each proper group defines an unordered partition S/T.
Deduplicate both identical and complementary nominations globally, and offer
each resulting partition once to every destination. Canonical identity is the
smaller side; equal halves choose the lexicographically smaller sorted vertex
tuple. Dense IDs start at zero, so that tie chooses the side containing zero.
Compact bitsets make complement calculation cheap. Source neighborhoods are
prepared once per search; order blocks are prepared once per sweep.

For destination r and each current donor d in x/y/t, compare BOTH families:

    merge(d|S forward/reversed, r|T)
    merge(r|S, d|T forward/reversed)

Only one strand borrows in any individual solve. The other keeps its current
destination sequence. All candidates see the same query snapshot; compare them
before adopting one winner. These are exact merges under frozen coordinate
slots, not exact optimization of subsequent packing.

Every solve puts the complement of the canonical smaller side in the first
strand A and the smaller side in B. Deduplicate ordered (A_sequence,B_sequence)
pairs in this fixed orientation. The DP's existing predecessor tie rule favors
A; transposing arbitrary calls before deduplication could change their returned
tracebacks. Canonical orientation deliberately makes complementary nominations
return the same representative, while it can change historical tied outputs.

Winner priority remains objective, changed result, genuinely borrowed sequence,
cyclic donor, forward before reverse, then side A before B. Genuine borrowing
excludes aliases of the destination's forward **or reversed** sequence on the
side actually borrowed. Duplicate provenance uses those intrinsic priorities.
Evaluate candidates in deterministic donor/direction/side order. Changed-result
priority compares the canonical returned tracebacks, not all tied paths.

There are at most 11 unique merge pairs: six nominations from each side share
the destination/destination pair. Singleton/complement partitions need at most
six. Their family contains ordinary singleton reinsertion, each whole-order
transfer, and that transfer with the singleton optimally repositioned. This is
a containment statement for the fixed-slot objective, not a runtime or physical
quality dominance claim. Whole-set queries stay direct scores, distinct from
empty standalone queries, which remain no-ops. They remain useful as cheap
queries even though each singleton/complement family contains their candidates:
direct scoring avoids the merge tables and traceback.

### Implementation choices and boundaries

Validation, baseline scoring, roles and bounds are shared across both borrowing
directions. No cross-query cache may reuse requirements after live orders change.
Keep the existing compiled transition construction and two-row DP. A deadline
between candidates returns the best completed result including the incumbent.

Sort canonical query identities before the seeded shuffle. Memberships stay
fixed during a sweep while donor sequences are live. Packing remains once after
a changed complete or budget-truncated sweep; worse decoded proposals continue,
and only usable decoded layouts enter the independent bookmark. The schedule,
packer, brick accounting, coloring and public attraction interface are unchanged.
Simultaneous placement exchanges and scheduling-policy changes are deferred.

One ask now means one destination/partition query. Diagnostics count unique
partitions and duplicate sweep nominations, candidate pairs and duplicate pair
descriptors, winning side/size, actual solves/cells, and nomination/preparation/
DP/packing time. Unique-partition counts sum across sweeps; source neighborhood
duplicates are removed once, not recounted on every pass. Side A is 0 and B is 1.

Slots are row/column proposal values, not physical sites. An H-only variable's
x value is dormant and does not anchor its H hull; a V-only variable's y value
is likewise dormant. Complete dormant values once before the sweep so contact
moves can price an appearing orientation. This remains a deliberate approximation.

### Evidence and unresolved questions

The baseline is commit 7a4214bc444012f70cd29af982358e5311ed22ae, with preserved
source provenance in [partition_baseline.json](data/partition_baseline.json).
Validation and paired speed measurements are recorded in
[partition-results.md](partition-results.md). The completed audit verifies
611 tests and native validity. All 63 paired frozen queries improve or tie;
the 30-case board has unchanged success and 3.9% higher paired qubit use.
Symmetric nomination and deterministic
completed queries do not prove schedule-independent final layouts or convergence.

## Outer-loop review: restore packing feedback (2026-09-17; not implemented)

Historical proposal. The approved change below selects still more immediate
feedback: fresh nomination and packing around each individual destination query.

The original 0.13–0.47-second packing concern above came from a preliminary
SciPy pilot. In the current paired board, complete decoding averages 4.29 ms
over 348 calls, including construction and capacity checking; axis packing
averages 2.24 ms per decode. These averages include budget-truncated calls and
are not universal bounds. Full-sweep amortization has retained an obsolete
cost premise while the nomination family has expanded.

The architectural concern is that fixed-slot cost only estimates the cost after
decoding. It can overprice spans that packing would collapse or underprice
capacity conflicts. Optimizing it more thoroughly does not guarantee better
decoded orders. A richer move catalogue should not automatically delay geometric
feedback. This is independent of graph family or the sign of benchmark changes.

The next proposed coordination unit is one partition queried once in each of
x/y/contact, with live donors, followed by an unconditional decode if anything
changed. Keep the nomination queue across those units, refreshing its membership
catalogue after exhaustion. Thus nomination fairness and geometry refresh have
separate boundaries, without an added numerical cadence parameter. An unchanged
unit is not a convergence certificate. No claim is made that three queries
always reach a clique template, or that the decoded objective always decreases.

This outer-loop question precedes a substantial transition-kernel rewrite.
Event-based cost construction remains a possible exact simplification; its
speedup and final implementation were not established at that point. This
proposal was superseded by the approved live-reference implementation below.

## Live reference moves and streamed costs (approved 2026-09-17)

### Decisions and boundaries

This is the current implementation contract. Initialization still produces three
independent permutations from the initialization seed. Scheduling uses a separate
`SeedSequence([effective_sched_seed, 1])` stream; the effective schedule seed
defaults to the initialization seed. Draw one reference permutation, a relation
phase in 0..4, and a destination phase in 0..2. Store no catalogue of groups.

At reference position i in round r, select relation
`(i+r+relation_phase)%5` from source/x/y/contact/anchor. Start destinations at
`(i+r+destination_phase)%3` and visit the other two cyclically. Before EVERY
destination query, nominate from the current state: N(v), {v}, or a contiguous
window of size max(1,n//2) in the selected current order. A window contains v;
sample its start uniformly from all valid starts, without wrapping or clamping.
The relation persists for a reference visit; membership does not.

Each round opens with one whole-order query per destination, starting at
`(r+destination_phase)%3`. These use direct scoring, while anchor-only queries
provide the larger singleton/complement family containing whole transfers and
optimal anchor reinsertion. All queries retain live donors, either-side borrowing,
canonical strand orientation, pair deduplication and the existing winner ties.

Decode immediately after EVERY changed individual query. Accept neutral changes
and worse decoded scores. An unchanged query needs no duplicate decode. A new
query completes dormant coordinates from the most recent decoded layout, so its
slots are fixed only for that query. Partial queries retain their best completed
candidate, and the existing deadline-aware total decoder and finite bookmark
protect output validity. Packing, reservations, coloring and bookmark selection
are unchanged. No graph-specific initializer, repair, or source-family rule is
introduced.

Here n counts nonisolated source vertices; isolates are assigned at conversion.
Every complete round contains 3n+3 queries. Every vertex is a reference once per
n reference visits, sees all five relations per five rounds and all fifteen
relation/first-destination combinations per fifteen rounds. These are coverage
statements in visits, not wall-time or convergence guarantees. A quiet sampled
round cannot establish a fixed point; stop only on the existing work/time budget,
disabled moves, or trivial input. Timeout zero and no ask budget remain unbounded.

### Exact event recurrences

Within a query, lazily cache each ordered strand's positions, same-strand earlier
neighbor counts, and the appropriate contact-net extrema. Reversals are ordinary
separate entries. Caches expire after the query; accepted moves cannot reuse stale
roles or coordinates. Spatial slot coefficients and unchanged unary costs are
prepared once. The candidate family and objective do not change.

For A first and canonical smaller B second, let C(i,j) be the number of source
edges crossing the emitted-prefix cut. Maintain C(i,0) and the number a[j] of
emitted A neighbors of B[j]. Entering an A row updates only its B neighbors;
then the cut across the row obeys

    C(i,0) = C(i-1,0) + degree(A[i-1]) - 2*same_before(A[i-1]),
    C(i,j) = C(i,j-1) + degree(B[j-1])
                         - 2*(same_before(B[j-1]) + a[j-1]).

Both predecessors into a cell add this same cut. Thus no dense cut table is
needed. Two integer value rows and canonical parent ties still solve precisely
the same merge problem. Summing cuts gives the destination's edge-rank span;
the other two orders' spans are constant within this query and can be omitted
without changing comparisons.

For a contact move, a vertex with d opposite-strand neighbors has d+1 arm-cost
states. Construct its neighbor sequence in opposite-strand order by adjacency
scattering. Prefix-y and suffix-x extrema combine with fixed same-strand neighbors
to price V and H respectively. Include the own crossing iff both orientations
exist. Across an A row, change A's state only when crossing a B neighbor. Entering
a row updates the B states of the newly emitted A vertex's neighbors. Bar birth
and disappearance are therefore exact events, not separately repaired cases.

For a spatial move, each contact net supplies endpoint threshold events. Its A
minimum contributes while the B prefix has not passed bmin; its A maximum
contributes after bmax. The transposed rules apply to B. Four counters distinguish
minimum/maximum and inside/outside anchoring lanes. Count/distribute events by
threshold and emission row in linear space; apply the existing brick-cost formula
at the current slot inside the fill. No dense difference or transition grids
remain. Shared brick boundaries and signed endpoint charges are unchanged.

The parent matrix is the only quadratic candidate structure. Other preparation
uses O(n+|E|) storage, and the DP still visits O(|A||B|+n) states. Sparse contacts
reduce event work; they do not eliminate the merge grid. Including adjacency
scans and event updates, fill work is O(|A||B|+n+|E|). A fixed-strand merge
searches its binomial family exactly, not all permutations or subsequent packs.

Avoid constructing a permutation for every candidate. Worse scores need no
traceback; a score below the incumbent implies change. A tie at the incumbent
uses a canonical parent walk to test equality. Retain winning parents/strands and
materialize the winning order once. Keep at most current and best parent grids.
Integer checks and between-kernel deadlines remain mandatory.

### Evidence and diagnostics

One ask is still one destination/partition query. Passes now count reference
rounds started, with completed rounds and reference visits reported separately.
Retired global nomination-uniqueness counters are unavailable. Default trajectories
summarize reference rounds; optional tracing records each query and decoded result.
Relation-attributed work and improvements are descriptive, not causal evidence.

Event/state/update and traceback counts accompany existing solve/cell/time counters.
The fused fill includes per-cell price application: its time cannot be compared
to the old table-only fill without including old preparation too. Correctness
requires differential score AND canonical-order agreement with a test-only dense
reference, plus the independent physical and exhaustive optimization oracles.

Baseline provenance and measurements are in [live-results.md](live-results.md).
The completed audit retains 75 exact trajectory pairs, 2,520 query measurements,
120 board runs and 15 valid fingerprints. Results remain separate from the
decisions and exact statements above. Global convergence and universal quality
or speed gains are not assumed.
