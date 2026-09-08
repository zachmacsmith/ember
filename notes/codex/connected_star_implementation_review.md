# Independent review of the connected-center implementation policy

2026-09-08. The fixed-footprint assignment, charged compact-state representation,
and shared-budget policy are mathematically consistent with the preceding
design and adversarial reviews. The termination-order ambiguity identified
below is resolved in the final reviewed policy. This is a specification review: no connected
implementation, constructor, refiner, benchmark, or solver was run.

## Reviewed documents

| Document | SHA256 read for this review |
| --- | --- |
| Initial `connected_star_implementation_spec.md` | `5fdaea0c5e2bbf203d21030eb576c0e05e4d81766f2f3fb791c12a86c6f9fe1b` |
| Final `connected_star_implementation_spec.md` | `41e7b0bc31d7fa44a8c2f326d0a143315b6e5f178a5e7164cc530a32919f1e99` |
| `connected_star_relocation_spec.md` | `f7f411a24fafe9a25dfa7a715ad472f8a465d496be7643d9349086a5cb2c71ab` |
| `connected_star_domain_compression.md` | `301185fde486026902ed1535952c4c0ac0843980ac6ace535323f00fdb4ae051` |
| `connected_star_adversarial_addendum.md` | `1f5bd5d160d01a8f0286d3a6c8b5bf90d7c7e8c3e1b42d6543feea283c15553d` |

The adversarial addendum records an earlier compression-draft identity. This
review directly checks the current compression text listed here rather than
assuming that earlier hash covers later wording. Historical evidence need not
be rewritten to erase that distinction.

## Exact assignment and Hall guidance

Exact equality of frozen logical-neighbor sets is sufficient for compression.
Every selected leaf has only the center as a selected neighbor, so leaves in
one class also have the same logical degree and singleton degree filter.
Their old chain lengths and positions affect released availability and the
block's Q allowance; they do not impose different replacement-site constraints.
This depends on verifying an induced source star, fixed selected vertices,
fixed outside ownership, and exact target edges.

A class of multiplicity c requires c distinct eligible boundary sites. An
assignment of physical sites to classes with capacity c is exactly the integral
source/class/site/sink flow described in the amendment. Stable expansion of
each class's distinct sites to its actual logical leaves preserves all source
contacts. Physical-site capacity remains one even if several classes accept it.

The direct-fill rule is a valid initialization, not an exact assignment solver.
The subsequent multisource alternating search must start every underfilled
class and allow any reached filled class to exchange assigned sites. A simple
augmenting path can visit each class/site at most once; after one path update,
fresh reachability must be computed for the changed assignment. This remains
valid when a class has demand greater than one. Completing all demand proves
maximum cardinality immediately; otherwise a completely exhausted search from
all underfilled classes is necessary before claiming exact deficiency.

Deleting a boundary site newly occupied by the center removes its assignment
and decrements its class count. Existing assignments remain feasible on the
remaining old boundary. New eligible sites can then be directly filled, and
augmentation restores a maximum assignment. Cardinality can decrease despite
center growth. Compression does not remove this nonmonotonicity.

For maximum but incomplete assignment, the Hall set contains alternating-
reachable classes. Its demand is the sum of their multiplicities. Count the
*full* eligibility neighborhood, including sites already owned by those classes.
Every such neighboring site must be occupied by a reachable class or an
augmentation would exist; at least one reachable class is underfilled. This
proves the stated demand shortage. A residual traversal that omits saturated
owned arcs cannot substitute its reached-site count for that full neighborhood.
Interrupted domain or augmenting scans establish neither a maximum nor a
Hall certificate.

## Charged copies and cache separation

The new policy explicitly supersedes the earlier reversible-update/replay
mechanism. Each trial owns a charged copy of its footprint, unfiltered boundary,
coverage counts, site/class assignments, and class occupancies. A completed
best state can be retained by reference; there is no reason to rebuild it or
silently deep-copy it when it becomes current. The current state, retained best
state, and currently evaluated candidate must have no shared mutable state
records. An interrupted copy or alternating-path update discards that trial;
it does not require a partly completed rollback of the current state.

If t, b, f, a, and g are the numbers of represented footprint, boundary,
coverage, assigned-site, and class-count records, one such copy costs
`O(t+b+f+a+g)` charged records. This is different from copying all duplicated
leaf-domain edges. It is still not free, and four candidates can consume a
substantial part of the allowance. No improved overall complexity or wall-time
claim follows just from replacing the representation.

Eligibility shared among trial states must mean the static class/site predicate
against fixed released availability and outside ownership. Membership in the
current center's boundary is state-dependent and must not be stored as that
static predicate. A demand-driven memo may safely append a *completed* static
eligibility decision during speculative evaluation: its value is independent
of which successor is chosen. An interrupted eligibility scan must never be
cached as a complete true/false decision. The query's entire memo is discarded
before selected vertices or the incumbent change.

For cost reporting, the shared memo can contain sites examined by discarded
successors or steering BFS, not just the current boundary. If u distinct sites
have been examined during the query, its potential storage is `O(g*u)`, rather
than automatically `O(g*b)` for the current b-site boundary. All materialized
entries and class/site scans remain charged, and the work limit can truncate
before such a table is complete. The older complexity table for duplicated
domains and reversible logs should not be quoted as the measured cost of this
new representation. Record copied records and actual memo size in diagnostics.

## Termination-order clarification

The reviewed implementation draft says both that a complete zero-deficit state
ends search immediately (lines 19–24) and that the best completed successor is
chosen by the earlier score/tie rule (lines 53–60). The older design's step 3
scores the shortlist and breaks exact ties by physical rank. These policies
can differ: two shortlisted candidates can both have exact deficit zero,
while the optimistic shortlist order places the larger physical rank first.

Root explicitly chose the following resolution during this review:

* Traverse the one fixed shortlist in its prescribed optimistic-score order.
* The first fully computed zero-deficit successor goes directly to full local
  certification. Do not examine later candidates to select another complete
  placement. Certificate failure or interruption returns no proposal.
* For nonzero candidates, complete the prescribed shortlist while allowance
  remains, then choose the improving completed successor by exact deficit,
  matching size, and physical rank. An interrupted candidate cannot supply a
  score or become the selected state.

This is sound and consistent with one fixed growing local search. It explicitly
overrides the former physical-rank tie rule *among complete zero-deficit
successors*. Root wrote that precedence into the final implementation policy
before code, so either behavior cannot later be selected after seeing results.
Full certification and the final common-deadline check still precede return;
finding deficit zero does not waive their cost or validate a partial state.

The final policy also explicitly distinguishes an eligibility decision known
false after a completed failed-contact check from an interrupted unknown
evaluation; true requires every required contact. It prohibits publishing an
interrupted unknown as false or using incomplete domains for an exact score.
Its added diagnostic paragraph separates fixed-footprint assignment completion,
returned certificates, scheduler commits, and whole-query heuristic exhaustion.
These clarifications agree with the proof and accounting boundaries above.

The root itself remains the single root selected from the prescribed necessary
stream and optimistic score. Neither the first-zero rule nor class compression
permits restarting at another root or changing selected leaves. The seven-
vertex adversarial example should therefore retain its documented failure.
Shortlist or steering-BFS exhaustion remains a heuristic failure, not proof
that no smaller connected-center replacement exists.

## Budgets, certificate, and implementation gate

Removing the separate 2,048-unit cutoff is explicitly disclosed. Every operation
still consumes the same active ordinary visit and whole-call auxiliary share.
After any setup, earlier query, or maintenance, effective remaining work is the
minimum of the *current* unused visit allowance and unused auxiliary allowance.
It must not be frozen before setup or reset per root, pass, or query. Shared
budget primitives reading live counters meet this requirement. Returned work
counts are descriptive after charging and must not be added to the visit twice.

The 25,000-unit maximum at current settings covers all auxiliary selection,
setup, queries, state copies, certificates, and maintenance in the entire call.
One connected query can consume the remainder. This does not give equal search
coverage or equal time to 037's capped singleton queries, and 5% of operation
units is not 5% of wall time. Deadline prefixes need to exercise copying,
direct assignment, augmentation/path updates, Hall scans, BFS, certificates,
and refresh; all published outcomes must be a fully valid strict reduction or
no proposal.

The strict center ceiling remains `Q_old - number_of_leaves - 1`. A center may
grow while shortening leaves makes the whole block smaller. Both physical
edge-boundary and *unfiltered distinct available site* bounds are safe necessary
relaxations under fixed availability and connected one-site growth. Neither
proves feasibility. Center obligations are covered collectively by its full
connected footprint; the singleton center degree/intersection filters must
not leak into this extension.

Final class expansion and independent original-edge checks are required even
after exact assignment: connected nonempty center, singleton distinct leaves,
target membership, frozen-owner exclusion, all selected incident edges, exact
Q, and exact incident-coupler R change. Negative R change is permitted only with
strict Q reduction. `member_growth` must count actual grown logical chains,
which can include the center, rather than inheriting the singleton core's zero.
A returned certified proposal is still distinct from the scheduler's later
atomic commit. Failed post-commit cache refresh disables auxiliary search and
retains that valid committed embedding.

The required exhaustive fixed-footprint assignment comparisons, interruption
prefixes, adversarial failures, and independently constructed Z12 mechanism
witness are appropriate correctness gates. They establish neither useful
coverage within the work allowance nor superiority over MM. The 037 result
already shows that local Q savings and unsuccessful auxiliary work can reduce
later ordinary savings. Any subsequent performance comparison must preserve
the fixed all-input protocol and all regressions.

Review conclusion: the representation, exact assignment, bounds, certificate,
and shared-budget choices are sound as specified. The final policy resolves
the termination and eligibility-publication issues. No remaining specification
blocker was identified. This review clears no uninspected code and supplies no
embedding-performance result.
