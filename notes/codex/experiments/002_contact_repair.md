# Experiment 002: bounded joint contact reconstruction

Date: 2026-09-07. Research branch: `codex`. Parent revision when this note was
written: `580d2044`; the new module and tests are uncommitted working-tree files
for the parent to review and record together with the pilot. No external
embedding algorithm was used to create the fixtures or produce these results.

## Question and prediction

Can a small beam of alternative local chain assignments retain a coordinated
move that strict single-chain shortening and one fixed-order greedy group
reconstruction cannot perform?

The pre-implementation design and self-critique are in
[`../contact_search_spec.md`](../contact_search_spec.md). This implementation
uses that specification's physical contact/occupancy representation and bounded
BFS reconstruction. It contains no integer-programming solver, MM, busclique,
external embedding executable, graph-family dispatch, or stored embedding table.
It is a refinement primitive, not yet a complete constructor or evidence of an
algorithm beating MM.

Prediction: on a physical graph where a one-qubit chain occupies a neighbor's
potential shortcut, retaining a slightly larger alternative for the first chain
can permit a larger net reduction after the second chain is reconstructed.

Falsifier for the minimal mechanism: the wider beam cannot retain and complete
that valid group move, or its output violates any original graph constraint.
Broader utility and runtime remain separate, untested hypotheses here.

## Implementation

New files:

- `packages/ember-qc/src/ember_qc/algorithms/factored/contact_repair.py`
- `tests/algorithms/test_contact_repair.py`

Public APIs:

```python
repair_group(embedding, source_graph, target_graph, group, *,
             beam_width=4, alternatives=3, halo=2, max_region=512,
             max_expansions=50000, max_orders=2, deadline=None)

contact_polish(embedding, source_graph, target_graph, *, timeout=None,
               deadline=None, max_passes=2, max_groups=128,
               group_sizes=(2, 3, 4), beam_width=4, alternatives=3,
               halo=2, max_region=512, max_expansions=500000,
               group_expansions=50000, max_orders=2)
```

Each returns `(embedding, diagnostics)`. The first accepts groups of one through
four vertices; singleton groups support the declared move-set ablation. The
second uses one evolving valid incumbent and regenerates candidate groups from
chain costs, source adjacency, and physically adjacent occupied chains. It does
not select among separate embedding algorithms.

For each group:

1. Keep all selected old qubits in the physical region. Add free neighbors up
   to the specified halo and total region cap. Frozen qubits are excluded. An
   oversized old group is skipped, never silently truncated.
2. For each beam prefix, derive contact sets for the next selected chain from
   its frozen and already-reconstructed logical neighbors. A contact may occur
   anywhere on those chains. Neighbors still pending guide root proposals
   through their old boundaries but do not freeze future contact positions.
3. Construct connected alternatives with BFS paths from the current tree to
   uncovered contact sets. Multiple roots and deterministic neighbor orders
   provide local alternatives. Include an available feasible old chain when
   it can participate in a strict group improvement.
4. Retain a bounded beam of partial assignments. Prefixes store only selected
   chains and their occupancy deltas as immutable sets; discarding a prefix
   rolls its occupancy back without touching the incumbent or whole target.
   Pair orders are both considered by default; larger-group order search is
   capped explicitly.
5. Before a complete proposal can replace the incumbent, independently check
   exact source coverage, target membership, duplicate entries, connectivity,
   disjointness, and every source edge. Require strict total group-qubit
   reduction. Individual members may grow.

The physical qubit count is authoritative. A lower bound used for pruning is
`max(1, ceil((degree(v)-2)/(Delta(target)-2)))` when the target maximum degree
exceeds two. This follows because a connected L-qubit chain has at most
`(Delta-2)*L+2` outgoing couplers and must contact every distinct logical
neighbor. For smaller target degrees the implementation uses the safe bound
one. No benchmark-instance parameter enters the bound.

## Resource and validity boundaries

- `max_expansions` counts popped vertices across region BFS and routing BFS;
  it does not count every sorting operation, contact-set lookup, or adjacency
  inspection. Graph setup and final validation still have their own costs.
- Region size, beam width, new alternatives, root attempts, selected chains,
  order alternatives, groups, passes, and routing expansions are all bounded.
  Each chain expansion attempts at most three times `alternatives` roots.
- Deadlines are checked between bounded operations and inside BFS. They are
  cooperative limits, not hard process interrupts. The external experiment
  harness remains responsible for hard wall limits and whole-process timing.
- `contact_polish` builds graph adjacency once, includes setup/validation in its
  reported wall time, and aggregates work across unsuccessful groups too.
  `repair_group` also includes its setup/validation in reported wall time.
- Invalid inputs return unchanged with `invalid_input=True`. This first API
  does not claim to complete partial or invalid constructor output.
- A search exhausted before discovering a valid improvement returns the
  incumbent unchanged. A valid improvement found before exhaustion may be
  returned. Input mappings and chain lists are not mutated.
- Accepted moves preserve feasibility and strictly reduce total qubit count.
  There is no claim of a globally optimal replacement, convergence to the
  unrestricted local optimum, or successful construction of arbitrary graphs.

## Coordinated fixture and result

The source has two interacting vertices A and B. A also touches two frozen
leaves; B touches two other frozen leaves. Initially A uses physical qubit 0,
and B uses the path 1–2–3–4. A is already at the one-qubit lower bound. With A
frozen, B's two leaf contacts require the four-qubit path, so neither selected
chain can strictly shorten alone.

A different physical route, 5–6, preserves A's two external obligations and
touches qubit 0. Moving A there allows B to occupy qubit 0 alone while preserving
B's own external contacts and the A–B contact. The deltas are +1 and −3,
respectively, for a net saving of two qubits. All four external chains remain
unchanged.

With the **same A-first reconstruction order**, the implemented beam-width-one
control keeps A={0} and fails to improve. The wider beam retains A={5,6} until
B is rebuilt:

| Beam width | New A | New B | Qubits saved | Members growing | BFS expansions | Tree attempts |
|---:|---|---|---:|---:|---:|---:|
| 1 | {0} | {1,2,3,4} | 0 | 0 | 28 | 10 |
| 4 | {5,6} | {0} | 2 | 1 | 54 | 20 |
| 8 | {5,6} | {0} | 2 | 1 | 54 | 20 |

The region contains seven qubits. The width-four run expands six beam
successors and reaches one strictly improving complete proposal. Width eight
does no additional work on this fixture because the candidate set is already
smaller than either beam.

This proves a distinction only for the **declared** controls on this constructed
fixture. A different group order, another greedy rule, a plateau move, or a
different single-chain algorithm could behave differently. It does not show
that the method beats the old ball routine under all orders, outperforms MM,
or scales to Zephyr Z12. The fixture was chosen to exercise a mechanism, not
to estimate performance on an evaluation distribution.

## Verification

Command:

```sh
.venv/bin/python -m pytest tests/algorithms/test_contact_repair.py -q
```

Result after the final compatibility/budget review: **18 passed in 0.44 s**.
Environment: Python 3.10.19, NetworkX 3.4.2. The test harness reports the existing
dwave-networkx deprecation warning from `tests/conftest.py`; fixtures use
ordinary NetworkX graphs and no external embedder.

Meaningful checks include:

- The coordinated +1/−3 move, the same-order beam-one control, and independently
  checked inability of a strict one-chain reduction on that incumbent.
- Full structural validation using a separate simple NetworkX-based oracle.
- Untouched frozen chains and unchanged original input objects.
- Atomic rollback for expired deadlines, zero/one expansion budgets, and a
  region cap smaller than the old group.
- Rejection of foreign singleton qubits, extra source keys, duplicate chain
  entries, empty chains, and disconnected chains.
- Correct handling of an isolated source vertex and string-valued labels.
- Runtime import guard against MM/busclique names during a successful polish.
- Determinism at fixed work budgets.
- Eight small random quotient-graph incumbents built by contracting disjoint
  connected physical paths, checking validity, monotone size, and aggregate
  work/group bounds without using MM-generated inputs.

## Lessons and next decision

The local primitive now supports an experimentally observable coordinated move
and maintains the necessary physical invariants. Its beam retains alternatives
that a fixed-order first-choice reconstruction discards. Width four was enough
for this fixture; that is not a general recommendation derived from one graph.

The next decision belongs to the broad development pilot: apply the same fixed
constructor, group-generation rule, region policy, and work limits across
multiple graph families and scales. Compare widths one/four/eight and singleton
versus coupled groups with total work/time reported. Check dense incumbents for
preserved quality and scarce improvements; measure sparse success and actual
qubit reductions. Reject or revise the primitive if benefits require unbounded
regions, very wide beams, or a runtime far above the project's MM comparison
budget. Do not add family-specific rules or special cases in response to one
favorable or adverse instance.
