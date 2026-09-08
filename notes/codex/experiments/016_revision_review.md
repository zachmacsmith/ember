# Review of contact reconstruction revision 016

No new embedding-validity defect or MM call path was found in the reviewed
integration. The review did reproduce a deadline-reporting defect, which the
root agent corrected during review. Ten focused review tests now pass. This is
a correctness and implementation review, not evidence of superior embedding
quality or publication novelty.

## Scope and provenance

Reviewed `contact_repair.py`, `native.py`, and `contact_groups.py`, together with
the change specification in `notes/codex/contact_revision_016.md`. The base Git
revision was `af339c19d2358ec227f9f343d1f54bc36293ab0e`; the review began against
uncommitted changes. The root agent subsequently committed the tested candidate
and harness as `d270f2bb`, including the diagnostic fixes. Final reviewed source
SHA256 values are:

| File under `packages/ember-qc/src/ember_qc/algorithms/factored/` | SHA256 |
|---|---|
| `contact_repair.py` | `802c9fed98918cb446933609f000f8ad2bf89f8fa7c4b646b8aec7e7deefd8ed` |
| `native.py` | `e800de0a92ae65f28b70a7cfe60654320b0ccf2100690c618901256c2e8b847f` |
| `contact_groups.py` | `43574f6f13eb33d790de535e4e614533d0f1df7f50d129932301b7832e1301bd` |

The frozen experiment manifest at
`results/codex/016-refinement-ablation/manifest.json` records snapshot
`0240d24d46f81f2f4d63ce9675315335ddeaca3ea4513d23967609925756e1c9` and contact
source hash `c7cf4f821c3f378087e9f08a4f967225e2cba880eb8a82dd1554aabb1a8427e6`.
It predates the deadline-reporting fixes. Those fixes do not change generated
groups, sites, routes, or accepted embeddings; they change timing diagnostics.
The frozen experiment must retain its original provenance.

Only the new review test file and this note were written by the reviewer.
The root agent owns the implementation fixes.

## Resolved finding: a late final validation could report a different stop reason

Before the fix, a final full-validity check could cross the deadline after the
last routing budget check. `contact_polish` then reported `group_limit` or
another normal completion reason. Direct `repair_group` could report `searched`.
A deterministic fake-clock example started at 0, used deadline 1, advanced to 2
during final validation, and returned a valid one-qubit improvement with
`wall=2` and `stopped_by='group_limit'`.

The root agent changed the finish paths to measure the end time and record
`deadline_overrun`, with `deadline` taking precedence when the deadline is
reached. Invalid-input errors retain their specific reason. Relevant locations
are `contact_repair.py:305`, `contact_repair.py:427`, and
`contact_repair.py:498`. The review regression covers both public contact APIs.

The native wrapper already independently checked its end time and returned
`status='TIMEOUT', success=False` for late results (`native.py:108`). A separate
test forces late polishing while preserving a valid embedding and confirms
that the wrapper does not describe it as a timely success. The test also
checks forwarding of the new boundary-site and group-policy arguments.

## Correctness and search boundaries

- Boundary candidates are intersections of the physical boundaries of frozen
  logical neighbors. Frozen occupied qubits are excluded before intersection
  (`contact_repair.py:135–150`). A site that would satisfy all contacts but is
  owned by another frozen chain is rejected in a new test.
- A complete frozen-contact site is only a candidate. Its contacts to selected
  neighbors are not assumed valid. `_alternatives` imposes contacts to already
  reconstructed members, and the final check still validates every original
  source obligation before committing (`contact_repair.py:378`). A new fixture
  offers two individually plausible remote sites that lack the selected chains'
  mutual edge; the combined shortening is correctly rejected.
- The original region and all selected old qubits are retained. Site addition
  stops at both the total site limit and region cap. If the old region already
  fills the cap, no new site is added. A selected vertex without frozen contacts
  does not nominate the whole target (`contact_repair.py:133–183`). These are
  intentional search restrictions, not completeness guarantees.
- Round-robin groups use the same union of logical neighbors and physically
  adjacent occupied chains as the previous selector (`contact_groups.py:57`).
  Enabled singleton groups precede larger groups. A depth window is contiguous
  and does not wrap; every eligible center is visited for a configured size
  before advancing to the next size. Group sets are deduplicated and nonpositive
  total degree-bound excess is skipped. With validated input, a group's total
  size cannot fall below the sum of those necessary bounds; zero excess therefore
  rules out a strict group reduction.
- The proposal list is a snapshot for one pass. Each attempted replacement
  nevertheless reads the current evolving embedding, so prior accepted moves
  cannot make the candidate-boundary calculation use stale chains. A stale
  proposal can waste a group attempt, but it does not bypass validity checks.
- Native conversion and completion failures still return explicit failure;
  contact reconstruction is invoked only after an independently validated
  construction. Revision 016 does not repair partial failed constructions.

## What the caps actually bound

Boundary scans call the same `_Budget.pop()` used by routing, and the aggregate
contact loop gives each group at most the remaining global work allowance.
The new tests exercise limits 1, 7, 25, and 80 with smaller per-group allowances
and confirm `boundary_expansions <= expansions <= max_expansions`, the group
cap, and the region cap while independently checking validity.

The counted work unit is a processed physical vertex, not every machine
operation. Adjacency traversal, set operations, sorting, context construction,
group selection, and full validity checks are not all separately charged.
Some of those operations have no cancellation point. On bounded-degree Zephyr,
one adjacency traversal has a bounded number of incident couplers, but this
does not make the whole Python routine a hard real-time operation. Native
conversion also retains its documented cancellation limitation
(`native.py:93–97`). Final overrun reporting and the worker watchdog remain
necessary; an expansion cap must not be presented as an exact CPU-time cap.

The region cap bounds the routing region, not all temporary memory: frozen
ownership and boundary sets can involve the wider target. Likewise the group
selector prepares ranked neighbor lists before searching larger groups. With
`d_v` the degree in its logical-or-physical neighbor graph, its preparation
includes `sum_v O(d_v log d_v)` sorting work. After that, active-center filtering
makes generation `O(s sum_v d_v)` for the configured larger sizes `s <= 3`,
rather than scanning every center through the maximum neighbor depth. A tight
singleton-first cap returns before preparing physical neighbor lists.

## Determinism, scope, and independence

Site ranking uses old selected-neighbor contacts, available physical degree,
and unique target rank. Group ranking uses chain excess, length, and source
rank. No source-family name, instance identifier, or supplied embedding table
is consulted. The new mixed-label test reverses graph insertion and chain
orders, changes irrelevant source metadata, and obtains the same selected
boundary site and counted work. Stable ordinary labels are assumed;
`_ordered` uses type names and `repr`, so arbitrary custom objects with unstable
representations do not gain a new reproducibility guarantee.

The native constructor remains intentionally restricted to integer-labeled
Zephyr targets with the coordinate information needed by its geometric
conversion. That architectural assumption is explicit in `native.py:125–147`.
It is not dispatch on the source graph's family. Its source-label adapter still
uses source insertion order, so source relabeling with a changed insertion order
can change a fixed-seed construction, as previously documented.

The reviewed call path is:

```text
native_embed
  -> plane.arrange OR the explicitly configured packed layout
  -> wire_seeds_exact -> complete_seeds -> spur_prune
  -> contact_polish -> one configured group selector
  -> bounded contact reconstruction -> original-graph validation
```

No run selects a constructor or group policy by comparing competing outputs.
The package initializer still exposes legacy methods that can call MM; those
methods are outside the reviewed native call path. A fresh run in the isolated
candidate environment had `minorminer` unavailable, replaced the inherited
`placement._mm_route` with a failing sentinel, and ran native search with both
revision options enabled. It succeeded on K8/Z3 with 12 physical qubits,
12 attempted groups, 1,144 counted expansions, and 98 boundary expansions.
No `minorminer`, `_minorminer`, or `busclique` module was loaded. This is a runtime
independence check, not a timing comparison or quality claim.

## Verification

```sh
.venv/bin/python -m pytest tests/algorithms/test_contact_revision_review.py -q
```

Result: **10 passed in 1.14 s**. The sole warning was the existing
`dwave-networkx` deprecation warning. The tests cover selected-chain contact
obligations, frozen ownership, mixed-label determinism, shared work limits,
both contact APIs' deadline reports, and the native wrapper's late-result guard.
The previously reported broader suite was not rerun by this reviewer.

## Principled next direction if these small changes are insufficient

The next useful intervention is the contact-tree generation and completion
estimate, with the region and scheduler held fixed for its first comparison.
The current builder commits to the first reachable uncovered contact, keeps one
tie ordering per root attempt, and the group prefix is ranked by assigned
qubits alone. Experiment 013 found a valid small tree missed by that generator
and showed that a longer selected member can enable a net group reduction.
Adding more sites or groups does not remove either restriction.

A bounded replacement can retain a few partial connected trees that reach
different contact sets, reuse shortest-path searches, and account for an
optimistic distance to the still-required frozen contacts before discarding a
prefix. It should remain one contact-reconstruction routine over one occupancy
state, under the same group, region, work, and deadline limits. The first test
should use identical incumbent/group pairs and record which additional valid
tree enabled each reduction; then compare cumulative outcomes at matched total
time on further development inputs with one global configuration.

Self-critique: branching over partial trees can spend its budget on many similar
states, and weak distance estimates may not predict the cost of disjoint joint
completion. A better local router also cannot guarantee recovery from a poor
global construction or failed native placement. Reject the change if additional
valid reductions disappear at equal work/time, or if the trace merely shows more
search without better completion decisions. These observations motivate a
testable direction; they do not establish novelty or all-family superiority.
