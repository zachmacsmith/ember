# Extending contact search to partial native assignments

2026-09-07. **Design only; not implemented or promoted.** This is an extension
of the same bounded contact reconstruction described in
[`contact_search_spec.md`](contact_search_spec.md), not a second constructor,
an external fallback, a solver-led algorithm, or a graph-family dispatcher.

The immediate Z12 development priority remains quality on valid native-search
incumbents: the parent reports that the candidate trials completed so far in
screen 009 are valid. The small construction failures below justify specifying
partial-state support, but do not establish that it is the current Z12
bottleneck. Do not tune a construction patch exclusively to these small cases.

## 1. What failed native output actually contains

Small diagnostics ran with
`PYTHONPATH=packages/ember-qc/src .venv/codex-native/bin/python`, preserving the
isolated interpreter path. MM was unavailable. All graph/chain properties
below were recomputed against actual target adjacency, not inferred from
converter counters.

Settings: seed 4, two packing passes, shared random order, no polishing,
10-second safety timeout. K30 used the search constructor with one ask instead.
Regular80 used degree 3 and generator seed 7; WS80 used degree 4, rewiring
probability 0.1, generator seed 11.

| Failed source / target | Present chains | Missing vertices | Assigned qubits | Missing logical edges |
|---|---:|---:|---:|---:|
| Path40 / Z2 | 40/40 | 0 | 92 | 7 |
| Path80 / Z3 | 77/80 | 3 | 188 | 32 |
| K30 / Z2, search at one ask | 30/30 | 0 | 111 | 14 |
| Regular80 / Z3 | 80/80 | 0 | 200 | 56 |
| WS80 / Z3 | 73/80 | 7 | 221 | 60 |

Every present chain in these five outputs was nonempty, connected, and
target-valid. Chains were pairwise disjoint, without duplicate qubits or
foreign source keys. This is a favorable starting point: these particular
failures require missing-contact repair and sometimes vertex insertion,
without structural cleanup. It does not prove that every native failure has
these properties.

The path instances have independently verified ACL-1 witnesses obtained from
simple physical paths; see
[`experiments/006_generality.md`](experiments/006_generality.md). No independent
feasibility claim is made here for the other three failed instances.

Missing vertices need not imply exhausted qubits. Path80's partial assignment
leaves 148 of Z3's 336 qubits unused. In `field.py:517–526`, `_ensure_seeds`
calls `_nearest_free`, whose search examines only the 64 nearest candidates
(`field.py:407–422`). The word "guarantee" in `_ensure_seeds` is stronger than
that bounded search supports. A pending-vertex representation is necessary;
finding a free qubit elsewhere would still not prove its contacts routable.

## 2. Authoritative partial-state invariant

Let G=(V,E) be the immutable source and H=(Q,F) the original target. Store:

- A present set P subset V and a mapping C on exactly P. Each C[v] is a
  nonempty connected subset of Q. Different chains are vertex-disjoint.
- An inverse owner map for all assigned qubits; it must agree exactly with C.
- Pending vertices V minus P, including isolated source vertices without chains.
- An edge is witnessed exactly when both endpoints are present and an actual
  edge of H joins their chains. Store witnesses or an uncovered-edge bitset,
  and independently check it against physical adjacency.
- The original source/target identities, search state, random state, work
  counters, and current best partial assignment.

Empty lists are not realized chains. They are normalized to pending vertices.
Extra source keys, foreign target qubits, duplicates, overlaps, or disconnected
chains cannot silently enter this state.

For the first implementation, accept already structurally valid partial maps
and reject unexpected structural corruption with diagnostics. This covers all
five observed failures and avoids hiding converter bugs behind a destructive
normalizer. If broader native outputs later require normalization, specify it
as an explicit internal step: resolve ownership deterministically, retain one
connected component per remaining chain, mark empty results pending, and
recompute every lost contact. Record qubits/contacts discarded. A valid partial
input must be unchanged by normalization. Such a normalizer is not currently
justified as an unconditional operation.

## 3. One objective for completion and refinement

Use the lexicographic tuple

```text
K(C) = (missing_vertices, missing_logical_edges, assigned_qubits).
```

Missing logical edges include edges with absent endpoints; do not exclude
them from the deficit count. Feasibility precedes qubit count. A complete
valid embedding has first two entries zero; comparing K then reproduces
the current strict qubit-reduction rule. A repair may add qubits when it
reduces a preceding deficit component.

An edge incident to a selected group can be lost if other changes yield a
strictly better global K. Requiring every old contact to remain forever would
make the completion neighborhood unnecessarily rigid. Every such loss must be
counted; a single new contact is not a success if the whole group worsens K.
The missing-vertex priority is explicit: inserting a vertex can take precedence
over an increase in edge deficits. Measure these trades; do not silently add
an extra acceptance condition later without naming a research revision.

For a selected group S, only source edges incident to S can change. Maintain
their before/after witness statuses to compute exact deltas; frozen-frozen
missing edges remain missing constants. Full recomputation is the initial
oracle for checking an incremental implementation.

The initial revision should accept only strict K improvements. A full pass
without improvement means this bounded search stalled, not that G is
unembeddable. Plateau moves or global rollback are separate future revisions
with explicit visit limits, if observations justify them. Finite integer K
strictly decreases on accepted moves, but that fact supplies no useful
scalability or success guarantee; proposal/work/deadline bounds remain required.

## 4. Selecting a small logical group

Use the same physical ownership/contact representation as the valid polisher:

1. If there are pending vertices, schedule one by a globally fixed structural
   priority, such as unresolved incident degree with seeded ties. If there
   are no pending vertices, schedule an uncovered source edge.
2. Include its endpoints when present/pending. Add a realized neighbor or
   blocking owner indicated by bounded routing probes, up to four vertices.
3. Record which frozen chains obstruct attempted routes. An owner becomes a
   group candidate because its physical occupancy blocks contact search,
   not because the source graph has a recognized name or category.
4. Rotate among unresolved items so one persistent obstruction cannot consume
   all proposals. Count attempts, no-progress visits, and work independently.

A group may contain pending vertices, realized vertices, or both. There is no
assumption that every selected source vertex already owns a chain. The old
assignment—including absence for a pending vertex—is a legal rollback choice.

An initial group is not allowed to expand without bound. A fixed policy may
try at most one bounded region enlargement and one blocker substitution or
addition. If the group-size/region/work cap prevents progress, preserve the
current state, record the reason, and schedule another unresolved item.

## 5. Physical region and growth allowance

Always include **all** old qubits of selected realized chains; never truncate
an incumbent chain to meet a region cap. Add nearby free qubits and selected
owners' released qubits. Every unselected chain remains physically frozen.

For a pending vertex, obtain seed candidates from free boundaries of its
realized neighbors. For an entirely pending source component with no such
boundary, use a bounded globally reproducible free-region search. Native
geometric positions may guide this search, but the search must represent
"nothing found in the attempted region" separately from "no free qubit
exists." A fixed nearest-64 cutoff is not a global capacity certificate.

Region discovery itself consumes work. Track obstructing frozen owners, but
never route through their qubits unless they are explicitly selected in a
new group proposal. A disconnected region is permitted; each realized chain
must still be connected within one component.

Keep the existing group/beam/BFS bounds. In addition, replace the current
`old_group_qubits - 1` size cap during incomplete construction with a declared
growth allowance:

```text
group_qubit_cap <= min(region_size,
                      old_group_qubits + allowed_growth,
                      target_size - frozen_qubits - reserve_for_other_pending).
```

Reserve at least one qubit for each pending vertex outside S. This is a
necessary counting precaution, not a guarantee that later contacts can be
routed. A globally fixed small growth allowance may be increased once after a
diagnosed size-cap failure, subject to a fixed maximum and the total work
budget. Choose/freeze these engineering limits using the broad development
pilot; do not derive separate settings from individual families or instances.

The current full-degree lower bound on a chain's length assumes it realizes
all its incident contacts. It is **not** a valid minimum size for an incomplete
chain. During partial search, one qubit per realized chain is a safe lower
bound; stronger bounds must be tied to contacts that the proposal actually
requires. Retain the current degree-based bound when full validity is required.

## 6. Extending the beam and tree proposals

The present `_alternatives` rejects a chain when any frozen neighbor's
boundary is unavailable, and `_grow` returns a route only after it touches
every required boundary. Those conditions are too strong for partial
completion: a local move may improve several contacts without fixing them all.

Extend the **same** BFS tree-growth operation as follows:

- Known realized neighbors supply contact sets. Pending neighbors outside the
  group remain unresolved obligations, not empty hard target sets that make
  every proposal fail. Selected neighbors already reconstructed supply their
  new physical boundaries.
- Retain a bounded number of connected intermediate trees as contact sets are
  reached, not only a tree satisfying every neighbor. If further contacts are
  unreachable or the growth cap is exhausted, such a tree may still be a
  useful partial candidate. Its actual remaining contacts are evaluated.
- For a pending selected vertex, allow a connected nonempty insertion or the
  unchanged absent choice. For an existing selected vertex, preserve at least
  one connected choice; the incumbent remains independently available even
  if the beam prunes it.
- Continue to keep several group prefixes with distinct occupancies, using
  the existing bounded order alternatives. Later routing can reject an
  earlier placement without mutating the incumbent.

Do not rank prefixes by qubit count alone. At a fixed depth, use optimistic
missing-vertex/contact counts followed by assigned qubits. Edges whose two
endpoints are frozen or already finalized can be assessed exactly; edges
touching an unbuilt selected chain remain unresolved and must not be declared
permanently missing yet. The bound may optimistically assume those contacts
will be met. It is a beam-ranking heuristic, not an exact joint solver.

When every group member has been considered, recompute K for the completed
partial proposal and validate all structural invariants. Only a strict global
K improvement may replace the state. Once missing vertices and edges are both
zero, the same comparison permits only valid qubit reductions. No separate
constructor is run and no best-of-independent-method selection occurs.

## 7. Deadline, rollback, success, and checkpoint contract

- Keep group changes local until validation/commit. Exhausted BFS, discarded
  prefixes, failed region growth, and expired deadlines leave the incumbent
  untouched. An already accepted improvement survives a later interruption.
- Before the first full embedding exists, return `CONSTRUCTION_FAILED` or
  `TIMEOUT` with an explicitly labeled best partial assignment and deficits.
  Do not return it as `embedding` or calculate a successful-run ACL from it.
- After first full validity, save that incumbent separately and record time
  to first valid embedding. Return only fully validated embeddings through
  the successful result field. The experiment harness applies its own
  end-to-end timeout/eligibility rule.
- Checkpoint source/target hashes, full chain ownership, pending vertices,
  contact status, seed/RNG state, scheduling state, consumed work, and stage
  times. On restoration, recompute/validate physical invariants and contacts.
  An SSH reconnection must resume the same task rather than start an
  additional constructor.
- Count failed proposals and region discovery, not only accepted routes.
  Report wall time externally and identify bounded operations that cannot
  yet be interrupted internally. A cooperative deadline is not a hard
  process watchdog.

## 8. Relationship to existing completion

`field.complete_seeds` extends chains along their existing wires, then tries
one- or two-free-qubit bridges. It cannot insert a missing source vertex and
does not jointly release/reassign multiple chains. Its sorted source-edge
pass makes immediate local decisions. It is an inexpensive geometric proposal
stage, not a guarantee of full completion.

The proposed extension retains the same original constructor and physical
state, but can relocate multiple chains, change their contact locations, and
keep alternative occupancies until later members are placed. It uses actual
target adjacency rather than assuming that a geometric crossing suffices.
There should be one authoritative missing-contact count after geometric
completion and after every new move; converter counters are diagnostic only.

The extension is not a renamed call to MM, its fork, busclique, or an exact
embedding solver. Nonetheless, joint routing, beam search, partial embeddings,
and Steiner growth are established ideas. No novelty claim follows from this
specification alone.

## 9. Self-critique and falsifying experiments before implementation

**Success risk.** Local lexicographic descent can stall even on an easily
embeddable graph. Repair may require more than four chains or temporarily
more missing contacts. A partial vertex insertion can also consume space
needed elsewhere. This first design intentionally reports those failures
rather than concealing them with unlimited expansion or an external fallback.

**Scaling risk.** Returning intermediate trees and scoring unsatisfied contacts
multiplies beam alternatives. Dense neighbor sets can make contact-set setup
cost more than BFS. Fixed region, growth, alternative, group, and total-work
limits are essential. Profiling must distinguish contact bookkeeping from
vertex expansions before any native compilation work.

**Correctness risk.** The new partial validator, edge-deficit bookkeeping,
absent choices, and prefix bounds are the highest-risk changes. Reusing the
valid-only minimum-length bound or treating unbuilt selected neighbors as
frozen absent chains would incorrectly prune legitimate partial candidates.

**Scientific risk.** Two feasible path failures on small targets are not an
evaluation distribution. The early Z12 screen currently points to quality,
not widespread invalid construction. This extension must earn priority on
broader deficits or larger instances; a special path rule is not acceptable.

Before promotion, require:

1. Tiny invariant tests for missing vertices, missing edges, disconnected or
   overlapping raw input rejection, exact deficit deltas, pending isolated
   vertices, loss-and-gain contact accounting, growth caps, and timeout
   rollback. Check incremental counts against a complete independent oracle.
2. A generic example where repairing an edge requires added qubits, and a
   coordinated example where one group member moves so another can be
   inserted. Neither uses a precomputed embedding in the candidate process.
3. Paired repair attempts on the **same saved partial assignments**, from
   multiple source structures and sizes, comparing the same operation at
   widths one/four/eight with all work recorded. Use diagnostic witnesses
   only outside the candidate process.
4. Unchanged valid-input semantics and dense incumbent quality, plus measured
   total runtime consistent with the project's approximate MM budget range.
5. No promotion based solely on these tiny examples. If the Z12 screen shows
   negligible incomplete construction, keep this design deferred while
   improving quality within the same physical contact-search framework.
