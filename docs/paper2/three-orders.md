# Three-order native core

Native design approved 2026-09-14; bidirectional feedback approved 2026-09-15.
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

The owner explicitly selected **core first, abutment later**, and **packing
once per sweep**, not once per accepted interleaving. A sweep freezes completed
coordinate slots and changes their occupants and contact roles. The selected changed canonical
strand winner is adopted under the common fixed-slot score, including exact ties. Its intermediate book
may violate capacity and is never returned as an embedding. After the sweep,
decode its accumulated three-order proposal unconditionally, even if the
decoded score worsens. Retain the best usable decoded bookmark. No legalization
or feasibility-rejection cascade sits between these components.

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

## Total decoder and sweep contracts

Every decoder starts anew: consecutive groups of at most C active arms per
lane provide a feasible seed on an expanded ideal fabric. The extended m is
large enough for these groups and the actual chip. Alternate the same exact
conditional packer on both axes, starting with the seed's fixed axis bit.
Select the componentwise-smallest optimum in each pack. Equal-score updates
can only lower coordinates; stop when an entire sweep leaves them unchanged.
Coordinates are derived from orders and fixed seed, not inherited search state.

Before an interleaver sweep, fill dormant positions by integer monotone
interpolation between adjacent active coordinates; clamp open ends. Freeze
all slots for that sweep, including dormant slots. Do not reinterpolate after
a move. All three interleavers use the CURRENT contact order and book, so
their candidate scores refer to one common proposal objective.

The deliberate approximation is that fixed-slot proposals do not optimize
subsequent packing. Canonical decoding removes historical dormant positions
but does not prove that the interleaver can discover every useful arm birth.
Alternating exact axis packing does not prove joint global optimality.

## Validation and evidence

Retained tests include independent exhaustive merge/packing oracles, physical
conversion checks, tests forbidding implicit MinorMiner, and sweep/adoption
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
- `order_dp.py`: compiled exact forward/reversed merges for all three orders.
- `packing.py`: separation constraints, threshold costs, checked integer flow.
- `plane.py`: canonical decoding, frozen sweeps, unconditional adoption and
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
