# Why the first native build regresses on cliques

2026-09-14 follow-up to the [first-build results](three-orders-results.md).
Diagnosis only: production code is unchanged. Two issues are established:
order plateaus and the gap between conservative reservations and physical cost.

## The old embeddings remain representable

The recorded K10/18-qubit and K100/726-qubit embeddings both fit the new model.
Every source edge has a cross-orientation contact in the old embedding; the
forced H-before-V precedences form a DAG, so a compatible contact order exists.
Every designated bar fits the existing physical run, every crossing is present,
and the conservative capacities hold. Abutment and cyclic contact orientations
are unnecessary for these witnesses. This does not establish that the new
objective or its tie rules select those embeddings.

## Clique axis packing separates: a proved special property

Let f and l be the first and last contact-order vertices. Every H bar contains
x(l); every V bar contains y(f). Thus all bars on a lane overlap at a common
junction, and capacity is exactly "at most C active bars per lane," independent
of the opposite axis. Inside the chip, reserved cost is an x-only sum of H
widths plus a y-only sum of V widths. The feasible coordinate sets separate too.
The canonical seeds fit for these cases, so the exact conditional packers reach
a joint reservation minimum for their fixed orders. Alternating-coordinate
local minima do not explain these particular clique regressions. This is a
mathematical diagnostic fact, not a clique-specific production rule.

Independent K10 enumeration confirms this: all 715 monotone placements of nine
active x bars on five interior lines, with y solved exactly, give reservation
minimum 22 for both the native bookmark and synchronized orders.

In fact, K10 has an order-independent reservation lower bound of 22 at C=8.
Its 18 active bars need at least two columns and two rows. A mixed vertex u on
a column different from x(l) makes H(u) and H(f) each span two distinct columns;
each therefore costs at least two reserved bricks. Symmetrically at least two
V bars span distinct rows. The 18-bar base plus four extra bricks gives 22,
which the search achieves. This lower bound is on reservations, not qubits.

## A frozen-order plateau blocks useful search

For K_n, the source-edge rank span in any permutation is n(n²−1)/6; across all
three orders it is n(n²−1)/2. The tie breaker is therefore constant. Every
contact order also has n−2 mixed variables and 2n−2 bars. Neither quantity gives
a clique plateau gradient.

The actual K100 final state, seed 0, stops after 4,320 asks at 947 reservations
and 940 qubits. Shuffling only the relative order of variables at identical
coordinate slots changes no coordinates, roles, contacts, hulls or embedding.
These shuffles decompose into adjacent equal-score swaps, which the strict
winner gate disallows. Five diagnostic shuffles followed by one ordinary
interleaver sweep and one decode give:

| Shuffle seed | Strict winners unlocked | Decoded reservations | Physical qubits |
|---:|---:|---:|---:|
| 0 | 7 | 967 | 951 |
| 1 | 3 | 944 | 936 |
| 2 | 23 | 955 | 932 |
| 3 | 11 | 936 | 919 |
| 4 | 10 | 946 | 933 |

Three improve decoded reservations. The other two illustrate disagreement
between frozen and decoded cost. Thus a fixed point of the merge families
depends on arbitrary tied-slot ordering; it is not a geometric convergence
certificate. This does not establish random drift as the best remedy.

For comparison, the same K100 decoder with synchronized x=y=t gives 822
reservations and 782 qubits. This is a control, not a proposed initializer.

## Reservation cost and physical length disagree

For a hull [a,b], physical course j uses
q_j=floor((b−j)/2)−floor((a−j)/2)+1 qubits. With conservative width
R=floor(b/2)−floor((a−1)/2)+1, this is
q_0=R−[a is even], q_1=R−[b is even]. Which course receives which arm matters.
Current greedy coloring guarantees feasibility but ignores these discounts.

| Witness | Reservations | Greedy qubits | Optimal course qubits |
|---|---:|---:|---:|
| Native K10 bookmark | 22 | 21 | 20 |
| Native K10 final accepted layout | 22 | 20 | 18 |
| Old K10 coordinates, compatible contact order | 24 | 21 | 18 |
| Old K100 coordinates, compatible contact order | 845 | 777 | 726 |
| Same old K100 orders, canonical coordinates | 845 | 781 | 733 |

The course optimum is exact for these clique lane assignments: bars on each
lane all overlap, giving a small assignment problem. This diagnostic does not
implement general cost-aware interval coloring.

These witnesses show both objective disagreement and physical slack among
equal-reservation coordinates. They do not invalidate the capacity proof, and
do not prove that *every* reservation-optimal layout has poor physical cost.
The actual K10 final state already has 20 greedy qubits at reservation score22,
whereas its earlier retained bookmark has21. Bookmark comparisons use only
reservations; they cannot recognize that physical improvement. Optimal course
assignment on that final state gives a validated 18-qubit embedding. Thus K10
can simultaneously attain minimum reservations and the old physical result.
Its observed regression is avoidable coloring and bookmark loss, not a proved
tradeoff forced by the conservative model.

## Implications, not yet implemented

Search needs meaningful motion within equal-slot arrangements. One candidate
general tie signal is the rank width of the actual contact hulls, rather than
all source-edge rank spans. It uses existing requirements and can distinguish
arrangements on these plateaus. Its effectiveness remains a hypothesis; K10
already attains the global reservation optimum, so this signal alone cannot
reduce that score.

Conservative feasibility and physical cost must remain distinguishable even
when derived from one shared book. Course assignment and physical cost among
reservation ties are design questions for all graphs. They warrant neither a
clique template nor a repair phase. Any revision should preserve the per-sweep
cadence and exact stated subproblems.

## Evidence

- [Search probe](data/three_order_clique_search_probe.py) and [results](data/three_order_clique_search_probe.json).
- [Geometry probe](data/three_order_clique_geometry_probe.py) and [results](data/three_order_clique_geometry_probe.json).
- Reference captures: [K10](data/three_order_clique_old_10.json), [K100](data/three_order_clique_old_100.json), from commit `810745629ee5f711ee8b2d8157c648cf6b7ef548`.

Probes retain orders, coordinates and code/input hashes, and independently
validate physical witnesses. Diagnostic shuffles and assignments are not
production mechanisms.

Follow-up, 2026-09-15: the [imported-strand probe](data/three_order_imported_strand_probe.py)
tests an alternative to random plateau drift. Prescribing a selected group's
internal sequence from another master order uses the same two-prefix DP.
Two full-order proposals and one decode improve the K100 fixed point from
940 to775 qubits. The plateau result therefore should not be read as a case
for relying on randomness; the move family's internal-order restriction is a
concrete limitation to address. Production behavior is unchanged.
