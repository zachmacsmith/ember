# Direct singleton relocation within contact reconstruction

Design and one self-critique saved before implementation. This is a proposed
operator in the existing single evolving embedding, using its existing
lexicographic objective `(assigned qubits, -logical-edge coupler redundancy)`.
There is no new constructor, restart, independent output selector, exact solver,
graph-family dispatch, MM call, or busclique call. Conventional common-boundary
search is not a novelty claim. The purpose is to test a particular coverage and
cost limitation of the current implementation.

## Current coverage and omissions

`contact_repair._add_boundary_sites` already intersects frozen logical-neighbor
boundaries. For a singleton group this identifies the right feasible-site set,
but admission is capped by `boundary_sites` (currently 16) and `max_region`.
Then `_alternatives` considers only a bounded root prefix and bounded number of
trees. It sorts alternatives by size and physical rank; the width-one group beam
also ranks prefixes before exact redundancy is compared. A valid, more redundant
singleton can therefore be omitted or discarded even after its site was found.
Neither a larger old-chain halo nor a more accurate tree builder removes these
omissions.

Both existing group schedulers omit groups with zero total excess over the
degree-based chain-size lower bound. In particular, a one-qubit chain cannot be
visited alone to improve redundancy. It can move only incidentally in a selected
group containing positive excess. Manually supplied singleton groups are already
accepted by `_repair` under `objective='qubits_contacts'`; scheduling and proposal
enumeration, rather than the declared objective, are the missing parts.

For source degree `d(v)` and maximum target degree `Delta`, `d(v) > Delta`
proves that no one-qubit embedding of `v` exists. Use this explicit test, including
when `Delta <= 2`: `_Context.lower_bound` deliberately returns the loose value
one in that case. A failed one-qubit search does not prove a longer chain locally
optimal. For example, a three-qubit chain might shorten to two although it cannot
shorten to one. Preserve the ordinary reconstruction opportunity in that case.

## Feasible sites, objective, and validity certificate

Assume the current whole embedding `C` has already passed original-graph
validation and both source and target are simple undirected graphs. Direct mode
must reject directed/multigraph/self-loop inputs explicitly before using this
certificate; the unchanged legacy path retains its current behavior. Native
already rejects these unsupported source inputs. All chains
except `C[v]` remain fixed. A site `q` is available if it is unoccupied or belongs
to `C[v]`. For every logical neighbor `w`, let `B[w]` be the available vertices
adjacent to at least one physical vertex of `C[w]`. Then

```
feasible singleton sites = intersection(B[w] for w in source_neighbors(v))
r(q) = number of physical couplers from q to logical-neighbor chains - d(v)
```

A common site is a complete connected, nonempty singleton chain. Availability
proves disjointness; the intersection proves every required incident logical
edge. Other chains and logical contacts are unchanged. Thus this local
certificate, applied to a validated incumbent with an up-to-date owner map, proves
whole-embedding validity without another whole-embedding scan for each candidate.
Meaningful tests independently validate committed embeddings against the original
graphs. The native pipeline retains its existing final whole-embedding validator.

For a longer old chain, every feasible singleton strictly lowers assigned qubits.
For an old singleton, a move is acceptable only under `qubits_contacts` and only
when `r(q)` strictly exceeds its current redundancy. Among acceptable singleton
sites, prefer larger `r(q)`; break equal scores by first discovery in the fixed
enumeration below. The same tie rule permits early termination at the admissible
upper bound `Delta - d(v)`. Moving a singleton changes only incident logical
couplers, so this local redundancy delta equals the global delta. Every committed
move strictly improves the same global lexicographic objective. This prevents
cycles at a fixed total qubit count, but does not prove improvement in final
qubits after later budget-limited search.

Two exact shortcuts avoid unproductive site search:

* An old singleton whose logical neighbors are all singletons has exactly one
  coupler per required logical edge on a simple target. Every valid alternative
  has the same redundancy, zero. Skip it. Do not apply this shortcut to a longer
  old chain, which might still shrink to one.
* An old singleton already attaining `Delta - d(v)` cannot improve redundancy.
  Skip it after its current score is known. A degree-zero old singleton also
  cannot improve. A longer degree-zero chain can shrink to its smallest-ranked
  old vertex directly, with redundancy zero.

## Bounded enumeration and cache

Use the frozen logical neighbor whose chain has the smallest target adjacency
volume `volume[w] = sum(degree_H(p) for p in C[w])`, breaking ties by the existing
stable logical order. Every feasible singleton lies on this neighbor's physical
boundary. Enumerate its chain vertices in stable physical-rank order and their
already rank-sorted target adjacency. Deduplicate candidate sites, discard frozen
occupied sites, and inspect each available candidate's target adjacency once.
Its neighboring owners reveal both distinct required contacts and the exact
coupler count. The candidate's actual target degree must also be at least `d(v)`.
This is equivalent to intersecting every boundary, without scanning all frozen
neighbor chains. It is independent of the local halo and region admission caps.

Maintain one cache containing physical owner, per-chain adjacency volume, and
the incumbent object/version it describes. Build it lazily on the first eligible
singleton visit, not on the legacy path. Setup also collects a stable queue of
initially one-qubit source vertices of degree at most `Delta` with at least one
longer logical-neighbor chain. All queue eligibility is checked again when used.
Source screening charges one work unit per inspected source vertex; degree-
ineligible vertices are rejected before iterating their source neighbors.

Every accepted ordinary group move invalidates the cache immediately, just as
every accepted direct move does. To refresh it, remove *all* old selected chains
before inserting any new selected chains: a physical qubit may change owner
within a reconstructed group. Update volumes only for changed chains. Each old
removed or new inserted physical vertex consumes one maintenance work unit.
Never expose a partly updated cache. If maintenance cannot finish within its
allowance or deadline, discard the cache, disable direct search for the rest of
the call, and retain the already accepted valid embedding. Do not rebuild an
owner map on each visit and do not continue using stale ownership. Initial setup
failure similarly disables the new operator without changing the incumbent.

The queue is intentionally incomplete: vertices that become singleton only
later are not added to it, and queued vertices are visited at most once per call.
Ordinary positive-excess singleton groups retain their existing opportunities on
later passes. This bounds new scheduling work rather than claiming exhaustive
coordinate descent.

Proposed internal API in a new `singleton_relocation.py` module:

```
build_singleton_cache(C, ctx, budget) -> complete cache or None
refresh_singleton_cache(cache, old_C, new_C, selected, ctx, budget) -> bool
direct_singleton(C, ctx, v, cache, budget, objective) -> (site or None, diagnostics)
```

The proposer does not mutate chains or cache. Its fully inspected best candidate
may be returned when the work limit truncates enumeration; diagnostics explicitly
distinguish a completed scan, a proven upper-bound stop, and an incomplete scan.
An interrupted partially inspected candidate is never usable. A deadline reached
before commit abandons this visit's proposal and retains the current incumbent.
Already accepted earlier moves remain valid. Final wall time and any deadline
overrun are measured honestly using the existing return convention.

## Shared work and scheduling policy for the first experiment

Expose one public option:

```
contact_polish(..., singleton_policy='legacy')  # allowed: legacy, direct
```

The default path and its diagnostics/search trajectory remain unchanged. Native
integration can expose `polish_singleton_policy`; the single new experiment arm
sets it globally to `direct`. No user-facing family-specific parameter exists.
Direct mode applies only if singleton groups are enabled. New zero-excess visits
also require the existing `qubits_contacts` objective.

The first tested direct policy uses these fixed limits. They are conservative
engineering hypotheses, not fitted constants or claims of optimal allocation:

1. All setup, queue screening, cache maintenance and direct site scans share an
   auxiliary allowance `max_expansions // 20` over the **whole call**, not per
   pass. Every charged auxiliary unit also increments the original global
   `expansions`. Legacy control performs none of this work and receives no
   silently reduced limit. Report auxiliary work separately so this deliberate
   allocation is visible.
2. Each existing singleton group may spend at most 256 units on direct proposal
   scans, capped by the remaining auxiliary allowance, original remaining global
   work, original `group_expansions`, and original deadline. Cache setup and
   refresh are not hidden inside the 256 scan limit: they are charged separately
   against the same auxiliary, global, **and active group** allowances. Thus
   setup cannot exceed the group's budget, and all work in a visit still totals
   at most `group_expansions`.
3. If direct search accepts a singleton, finish that visit. Otherwise, if the old
   chain is longer than one, run the existing singleton reconstruction using
   only that visit's remaining group/global budget. Degree-ineligible old chains
   skip direct enumeration and retain this ordinary reconstruction. An old
   singleton needs no fallback BFS: every improving feasible chain of size at
   most one is a singleton. Exhausting only the 256-unit scan allowance does not
   itself stop the whole call.
4. Refresh after an accepted ordinary reconstruction uses only the active
   group's remaining work, as well as the auxiliary/global allowance. An accepted
   move may consume the whole group budget; in that case refresh performs zero
   work and the cache is discarded. No maintenance is charged retroactively and
   no accepted valid move is rejected merely to keep the cache available.
5. Insert at most `max_groups // 16` new zero-excess singleton visits over the
   whole call. Count every actual such visit in the original `groups_tried` and
   original `max_groups`; there is no second group quota. Interleave one after
   each 15 ordinary visits. At a pass end, a nonempty partial block may permit
   one such visit, still within the same cumulative cap. Do not run an auxiliary
   sweep when there are no ordinary groups. Preserve the relative order of
   ordinary groups; any late groups displaced by this allocation are a measured
   cost. Consume/recheck queued candidates in stable logical order, charging each
   inspected queue entry against this scheduled visit's scan/group/auxiliary
   budget. Stop scanning when that allowance ends. An empty/skipped queue does
   not create an embedding move or claim successful group reconstruction.
6. At every stage, exhaustion of the auxiliary allowance disables additional
   auxiliary work; ordinary reconstruction continues within the remaining common
   limits. Cache setup is lazy and is not attempted when `max_passes=0`, no
   singleton visit exists, or the direct allowance is zero. No allowance resets
   across passes. All loops use the existing cooperative deadline checks.

For work-unit consistency with current BFS, examining one physical vertex's
adjacency costs one unit, rather than one unit per edge. Setup/refresh and source
screening use the units stated above. The worst adjacency work per charged scan
is therefore `O(Delta)`. Context construction, existing validation, dictionary
copying, sorting short chain lists, and ordinary group generation still contain
wall-time work not represented exactly by this counter; record total elapsed
time as well. These limits are cooperative work bounds, not a hard real-time
guarantee. Candidate inspection and deadline checks must not use wall time that
was excluded from the common native call deadline.

Pseudocode for an existing singleton visit:

```
remaining_group = min(group_expansions, remaining_global)
if direct eligible and auxiliary remains:
    lazily build complete owner/volume/queue cache, charging this visit
    if complete cache remains:
        inspect bounded seed-boundary candidates against frozen owners
        retain best fully certified strict lexicographic improvement
        if a proposal exists and deadline has not passed:
            commit only C[v] = [site]
            refresh cache within remaining allowances or disable it
            return accepted visit
if len(C[v]) > 1:
    run ordinary _repair on (v,) with remaining_group
    if accepted: refresh within remaining allowances or disable cache
return unchanged or ordinary accepted visit
```

For groups of size two through four, the proposal generator and acceptance rule
are unchanged; only a cache refresh may follow an accepted move. Integration
must aggregate each direct/maintenance unit exactly once. Diagnostics record
setup, refresh, queue and scan units; direct visits and degree/exact skips;
complete versus truncated enumerations; accepted shortenings versus equal-size
redundancy moves; cache disable reason; displaced ordinary-group opportunities;
and final actual qubits, total work, groups, wall time and deadline status.

## Self-critique before implementation

The exact feasible-site characterization establishes validity and local coverage,
not the usefulness of redundancy as a guide. Moving an optimal-size chain can
occupy a site needed for later group shortening. Even a direct qubit saving may
change later search adversely. The current bounded scan is not guaranteed to
find the best singleton or any singleton on a large boundary. Choosing the least
adjacency-volume neighbor minimizes the enumeration seed cost, but not necessarily
time to the most useful candidate. Its deterministic first-discovery ties are an
algorithmic choice, not an invariant under arbitrary graph isomorphisms.

Cache correctness is the principal new validity risk. Invalidation must precede
every accepted ownership change, including selected-chain qubit transfers and
multiple accepted moves in one pass. Early returns must not leave reusable stale
state. The local certificate is sound only for the current validated incumbent,
simple target, and exact owner map. Tests must cover these conditions directly,
not merely compare proposer output to itself.

The new cache may cost more than small singleton searches save. Charging refresh
against the current group's remaining budget can disable direct work early after
an expensive accepted reconstruction; this is an intentional bounded failure
mode to expose in diagnostics, not something to hide by rebuilding uncharged.
The 5% auxiliary allocation and 1-in-16 additional-visit cap bound displacement,
but cannot guarantee better cumulative quality. Experiment 023 already falsified
a stronger isolated tree mechanism: it recovered a real missed proposal but
spent enough work to lose cumulative group coverage and produced no full-run
wins. Experiment 030 found a real seven-qubit unrefined checkpoint opportunity on
one dense input, with large evaluation overhead and no savings on either sparse
input. Neither isolated mechanism justifies promoting this one.

This design introduces a second way to generate a proposal within one fixed
state, objective and schedule; it does not compare independent embedding
algorithms or outputs. Nevertheless its added implementation complexity needs
an end-to-end benefit. If the benefit is absent, preserve the tests and lesson,
then disable the research option globally rather than tuning it by graph family.

## Validation and predeclared experiment 033

Before broad execution, independently check small fixtures that establish:
global boundary sites outside the old halo; an equal-size singleton redundancy
gain omitted by positive-excess scheduling; exact degree and all-singleton skips;
continued three-to-two search after unsuccessful one-qubit enumeration; frozen
chain and input preservation; within-group owner transfers; a subsequent direct
search after an accepted joint move; setup/refresh interruption; shared group,
auxiliary and global caps across passes; deterministic enumeration; and deadline
rollback of uncommitted proposals. A fixture proves only the stated mechanism.
Compare the untouched legacy policy's full non-time trajectory where practical.

Then run the entire native pipeline on **all 34 current readiness source inputs**,
Zephyr Z12, seed zero, and one common 60-second deadline, with the same host and
frozen source snapshot. Run two globally fixed configurations: current spectral
initialization plus current contact settings as control, and the identical
configuration with `singleton_policy='direct'`. This is 68 calls, with a newly
executed contemporaneous control. Apply contact polishing once through each
ordinary pipeline; do not append this operator to completed baseline outputs.
Use existing MM-absent runtime isolation and independent original-graph validation.
Experiment 032 separately supplies repeated-seed candidate/MM evidence.

Report every input, failures and late calls; paired final assigned qubits/ACL,
wall time and charged work; direct versus joint accepted moves; cache costs and
disable events; ordinary-group displacement and all cap/deadline stops. Retain
regressions. A larger number of accepted redundancy moves is not a success
criterion. No useful final savings at comparable total cost, systematic budget
losses, or any validity/cache failure falsifies or defers the proposed integration.
Do not select between the two configurations per input and do not infer broad
superiority from the mechanism fixtures or a single seed.

Status: design saved; no singleton module, integration, or new embedding run has
been performed under this revision yet.
