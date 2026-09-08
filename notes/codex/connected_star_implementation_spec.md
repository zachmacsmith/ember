# Connected-center core: fixed implementation policy

2026-09-08. Specification and self-critique before implementation. The broader
[design](connected_star_relocation_spec.md), reviewed
[compression amendment](connected_star_domain_compression.md), and
[adversarial review](connected_star_adversarial_addendum.md) supply the proof
boundaries. This note resolves representation and initialization choices for
one core implementation. It does not change the completed 037 experiment.

037's singleton-center treatment had six lower-ACL and four higher-ACL outputs,
24 ties and only seven qubits of net saving across 34 inputs. Its 25 committed
moves saved 38 qubits internally, while ordinary refinement saved 31 fewer.
That narrow, concentrated result does not justify a general advantage. A center
that may occupy several qubits tests a broader neighborhood, including centers
above the physical singleton degree limit. No input or family chooses a policy.

## One search and one source block

Use the original design's independent-leaf selection, strict selected-block
qubit ceiling, necessary root stream, one optimistic-score root, four-way
successor shortlist and Hall/frozen-contact steering BFS. Keep their stable
tie orders. Include both the physical edge-boundary and unfiltered available
site-boundary necessary bounds. A root never changes, and selected leaves never
change during a query. A complete zero-deficit state ends the search immediately.
The adversarial counterexample remains an expected heuristic failure; do not
special-case it or claim completeness for the connected search.

Unlike the singleton-center core, reject no center merely for degree above
Delta. Every selected leaf must still have degree at most Delta. Select by
decreasing old chain excess, increasing source degree and stable logical order,
using a blocked-neighbor set for independence. Require at least two leaves and
a positive strict center-size allowance. Charge every inspected source record.
The final selected vertices must induce exactly that source star.

## Capacitated assignment with charged compact states

Group leaves by exact frozen-neighbor-set equality. Class order is first
appearance in the fixed selected-leaf sequence; sites use the fixed physical
order. Keep individual leaves within each class in stable logical order for
final expansion. Static site eligibility is computed once per class/site pair
within the query, against fixed outside ownership, and is discarded afterward.
Use explicit sets/lists and charged scans; do not rely on an uncharged bit mask
whose width increases with source degree.

A local state contains the connected footprint, its distinct unfiltered
available boundary, frozen-center contact counts, a physical-site-to-class
assignment and class occupancy counts. Immutable query-local eligibility data
are shared across states. Successor evaluation makes a charged copy of these
compact state records; it does not copy duplicated leaf-to-site edge tables.
The original state and global incumbent remain unchanged. A partially copied
or updated state is discarded on interruption.

This **explicitly replaces** the earlier tentative reversible-edit mechanism
with compact charged copies. Copy every footprint, boundary, coverage,
assignment and count record with a budget check. Evaluate at most four
successors, retain the best completed improving successor by the existing
score/tie rule, and discard other states. Retaining that already charged state
needs no hidden replay or uncharged full copy. No interrupted successor may
supply an exact score or a selectable state. If the common budget expires,
return no proposal; do not publish a previously incomplete computation.

Build the root boundary and process new boundary sites in stable order. For
each new site, assign it directly to the first eligible underfilled class, if
one exists. This is only an initial feasible partial assignment. Then run
deterministic augmenting searches until all demands are met or a completed
search from every underfilled class finds no free site. Previously filled
classes can exchange their assigned sites along alternating paths. Direct
assignment does not establish maximal cardinality in overlapping domains.

For a successor, first remove the newly occupied center site and its assignment
if present, decrementing that class's count. Remove it from the boundary and
add genuinely new available boundary sites. Apply the same direct-fill rule to
new sites, then the complete augmenting search to restore a maximum assignment.
Existing assignments may be rearranged. A footprint growing does not imply
matching cardinality grows.

Use multi-source alternating search in stable class/site order. Start all
underfilled classes, record path predecessors and revisit neither class nor
site within one search. On reaching a free site, update ownership/counts along
the complete path; any interrupted update invalidates that entire candidate
state. Repeat until complete or a fully exhausted augmentation search proves
maximum cardinality. Record an exhausted search separately from interruption.

Only a maximum assignment supplies an exact deficit. Hall guidance uses the
reachable classes with their actual multiplicity demands. Its full neighbor
set includes sites already assigned to those classes, even if a residual
traversal skips saturated arcs. Count distinct sites and charge this work.
The steering BFS retains the original depth/availability/path-exclusion rules
and adds only one vertex before recomputing obligations. No root restart,
backtracking, shrink step or second complete-result selection is included.

## Certificate, interface and work

Expand class assignments to individual leaves in stable order only when all
demands and frozen center contacts are covered. Recheck nonempty connected
center, singleton leaves, distinct ownership, target membership and every
selected incident original source edge. Recount exact incident couplers and
old/new selected qubits. Require strict total qubit descent. The center may
grow while the block shrinks, so report actual `member_growth`; do not reuse
the singleton core's constant zero. Secondary contact redundancy may decrease
on a strict Q improvement. A final deadline check precedes returning a proposal.

Implement a new internal `ConnectedStarSearch` with the same public local
proposal/cache interface as `StarSearch`: `propose(embedding, center, visit)`
returns selected replacement chains and diagnostics, and `refresh(old, new,
selected, visit)` updates ownership after an external atomic commit. Reuse the
audited owner-cache and shared-budget primitives where appropriate, without
changing the singleton core's behavior. Constructor work stays constant and
ownership setup remains lazy. Do not call singleton proposal search internally.

The total auxiliary share remains `floor(global_work/20)`, including setup,
selection, all queries and post-commit cache maintenance. Each query also shares
the current ordinary visit's remaining allowance. The connected query has no
additional 2,048-unit cutoff: its absolute ceiling is the remaining auxiliary
and active-visit allowance, at most 25,000 units under the current global
settings. This is the previously disclosed allocation change, not an assertion
of equal query coverage or equal wall time with 037.

Charge source and chain records, qubits, physical adjacency scans, eligibility
checks, state copies/edits, class/site edges, queue operations, path records,
assignment recovery, scoring and certificates. Each physical adjacency scan
performs at most Delta neighbor checks; larger logical/class sets require
explicit charged iteration. Sort/allocation costs remain included in wall time.
Selection/setup/query/refresh stage totals must reconcile with the supplied
visit counter and total auxiliary work exactly once.

Keep cache identity tied to the exact immutable incumbent. Refresh removes all
old selected owners before adding new ones. An interrupted refresh disables
future auxiliary attempts for that call and retains the already accepted valid
embedding. No partial cache, domain or speculative state survives a query.
Distinguish returned certified proposals from eventual scheduler commits.

## Required focused checks and limitations

Before integration, independently compare fixed-footprint class assignment with
expanded-leaf exhaustive assignment on small graphs, including multiple-demand
classes, overlapping domains, occupied-site deletion and Hall neighborhoods
containing owned sites. Exercise every budget/deadline prefix on representative
successful and failing moves; it must yield a valid strict reduction or no
proposal, with the original embedding intact. Check cache identity/refresh
interruption, label collisions, empty frozen obligations and negative R gain.

The seven-vertex adversarial example should retain its documented failure under
the fixed root rule. The distinct-site rejection example should remain a safe
conditional prune. Include at least one actual ideal-Z12 witness with a
multi-qubit or above-Delta center, using a valid independently constructed
incumbent; no MM/busclique output can seed a test. This is a correctness and
mechanism witness, not evidence of corpus superiority. Keep all successful and
unsuccessful synthetic checks and their exact construction rules.

Self-critique: compact copies can still dominate when domains are heterogeneous;
one query can exhaust the whole auxiliary share; the first root may be unusable;
greedy leaf selection can exclude a feasible smaller block; and a successful
local move can displace better ordinary reductions, as 037 demonstrated. The
initial direct-fill rule avoids some repeated scans but establishes no general
linear bound. None of this proves MM-scale performance or novelty. The core
must pass correctness review before any scheduler integration or new frozen
all-input comparison. No production default is changed by this specification.

Status: ready for independent implementation-policy review. No connected core
has yet been implemented or benchmarked.
