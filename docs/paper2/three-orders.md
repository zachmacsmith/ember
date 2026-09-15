# Three-order native core

Design contract approved 2026-09-14; first native build implemented on `factored`.
See [measured results](three-orders-results.md). This document is the resumption
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
coordinate slots and changes their occupants and contact roles. Every strict
winner under the common fixed-slot score is adopted. Its intermediate book
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
their strict improvements refer to one common proposal objective.

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
