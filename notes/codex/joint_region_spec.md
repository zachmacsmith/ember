# Joint contact-region optimization: pre-implementation specification

2026-09-07. **Reclassified after user prompt 4: diagnostic exact oracle only.**
The proposed IP-led construction below is superseded as a runtime algorithm.
The selected direction is a fast heuristic core; tiny exact solves may help explain
local missed improvements or later become a tightly bounded subroutine if measured
cost warrants it. This specification combines brainstorm mechanisms 6, 8 and 9.
It is a mathematical design, not implemented code or evidence of novelty/performance.
Self-critique appears below and in the plan.

## State and operation

Let G=(V,E) be the simple undirected source and H=(Q,F) the immutable ideal Z12.
An assigned subset A of V has nonempty, connected, pairwise disjoint branch sets
C[v] contained in Q. Every edge of G[A] has an actual H coupler between its sets.
The pending set V\A and its unfulfilled edge obligations remain explicit.
Only A=V can produce a successful embedding; partial validity is not success.

One operation changes the branch sets of S, a subset of A, optionally adding a
pending logical vertex. It chooses from a physical region U containing all old
chains of selected vertices and a subset of currently unused qubits. No qubit owned
by an unselected chain is allowed. Do not free just a rectangular slice of a chain:
the initial formulation frees whole chains so there are no unmodeled outside pieces.

Freeze all C[w] for w in A\S. Moving a blocked outside chain means adding w to S,
then rebuilding the model. The same operation inserts vertices during construction
and reduces qubit count during refinement; no independent-algorithm result selection
occurs. An audited geometric initialization may be studied as a separate fixed
revision, never as a competing runtime constructor.

## Exact local model

For every selected logical vertex v and allowed physical qubit q, use binary
x[v,q]. Require sum_q x[v,q] >= 1 and sum_v x[v,q] <= 1. The set of true x[v,q]
is the new branch set.

Connectivity can be enforced with a single-commodity flow per branch set:

- Select one binary root r[v,q] with sum_q r[v,q]=1 and r[v,q] <= x[v,q].
- For every oriented edge (p,q) of H[U], permit nonnegative flow f[v,p,q], bounded
  above by |U| times both endpoint assignment variables.
- Add flow h[v,q] from a synthetic source with 0 <= h[v,q] <= |U| r[v,q].
- At each q impose h[v,q] + sum_p f[v,p,q] - sum_p f[v,q,p] = x[v,q].

Summing conservation shows total injected flow equals selected-qubit count. An
assigned component without the root cannot receive net flow, contradicting its
positive demand. Conversely a connected branch set supports such flow along a
spanning tree. The synthetic source is a mathematical variable, never a physical
qubit or an edge added to the target. Flow may be continuous; assignment is binary.

For logical edge {v,w} whose endpoints are both selected, introduce binary contact
witnesses z[v,w,p,q] for oriented physical couplers (p,q) in H[U]. Require
z <= x[v,p], z <= x[w,q], and sum_(p,q) z >= 1. Both physical orientations must be
available because logical-edge ordering is arbitrary. Witnesses are existential;
unused interchain couplers are allowed.

For edge {v,w} with v selected and w frozen, let B[w] be the physical vertices in U
adjacent to any member of C[w]. Require sum_(q in B[w]) x[v,q] >= 1. This leaves the
contact location free over the whole frozen chain instead of fixing a terminal.
There is no logical degree constraint requiring distinct physical endpoints for
different edges; one assigned qubit can have multiple incident contact couplers.

Edges between frozen vertices already hold. Edges to not-yet-inserted vertices are
tracked as future obligations and enter constraints when both endpoints become
assigned. On a complete state, all source edges are represented by one of these cases.

Minimize sum_(v,q) x[v,q]. Frozen qubits contribute a constant, so this minimizes
actual total qubits locally, equivalently ACL when G is fixed and fully embedded.
An optional second optimization at the optimal qubit count can minimize maximum
chain length; future-space or shape preferences must be declared secondary
heuristics, not misrepresented as exact quality improvements. Do not sacrifice ACL
for an unrequested secondary constraint without measuring and documenting it.

For refinement, feed the existing region assignment as a valid incumbent. Require
every returned assignment to pass an independent whole-embedding validator before
acceptance. A model timeout with no better valid solution keeps the incumbent.
No feasible solution under a strict improvement cap means only that this region
has no smaller solution, if infeasibility was actually proved.

## Construction and region selection

Start from no assigned vertices and a reproducible structural order. An insertion
adds one pending vertex, together with selected already assigned neighbors and
blockers. The allowed physical region includes their old chains plus free vertices
near possible contacts. The very first vertex requires an explicit seed region;
it has no boundary contact to guide placement. Compare a fixed topology-central
seed placement and a reproducible geometry-guided revision on development data;
freeze one choice before confirmation, without runtime competition.

A failed insertion can expand U, add blocking chains to S, or backtrack an earlier
placement inside the same state trajectory. Expansion is bounded by the run budget;
there is no completeness or polynomial-time guarantee. Reaching all of H would be
a general minor-embedding IP and can be impractical. Source graph size <= |Q| is
only a necessary condition for success.

Initial pilot region limits should be calibrated, for example 2–8 logical chains
and roughly 32–256 physical vertices, always large enough to contain all selected
old chains. These are starting experimental ranges, not tuned final parameters or
promises of feasibility. Longer dense chains may require larger regions. Record
each model's variable/constraint count, setup time, solve time, feasibility status,
objective bound, improvement and reason for stopping. Large region failures should
not be conflated with proof of no embedding.

Use full H adjacency, including external and odd Zephyr couplers. Geometry may
propose U, but all assignment/contact constraints are built from H. Relabel source
vertices and remove incidental generator-coordinate attributes in invariance tests.

## Correctness facts that can be claimed if implemented faithfully

Given a valid frozen partial embedding, a feasible local solution satisfying the
constraints yields a valid embedding of the expanded assigned subgraph: assignment
enforces disjointness and membership; flow enforces connectivity; the edge cases
exhaust all assigned logical edges. This is an inductive preservation argument,
not a guarantee that the solver finds a feasible insertion.

On full valid embeddings, accepted strict reductions in the positive integer total
qubit count terminate after finitely many accepted moves. That fact does not bound
rejected searches, prove escape from a local minimum, guarantee an embedding, or
prove global optimality. A globally optimal result needs a separate global bound.

## Self-critique before implementation

The basic formulation is established mathematical machinery. General embedding IP
and connectivity decomposition appear in [Bernal et al.](https://arxiv.org/abs/1912.08314);
multicommodity-flow and Steiner routing appear in [Bian et al.](https://www.frontiersin.org/journals/physics/articles/10.3389/fphy.2014.00056/full).
These sources supply prior art, not a claim that this exact local algorithm is new.

The model's contact variables scale with logical edges times physical couplers;
flow variables scale with selected chains times physical couplers. Even small
regions may be expensive. A minimal-length partial embedding may consume the space
needed for future insertion. Whole-chain regions can be too large for dense graphs,
while small regions cannot repair global placement mistakes in sparse expanders.
Strict descent can stall. Regions with movable external contact sets still freeze
the external chains and do not optimize arbitrary interfaces. These are falsifiable
limitations, not details to hide behind an exact-solver label.

The first useful outcomes are (1) agreement with exhaustive tiny instances,
(2) an explicit case where simultaneous contact changes beat the existing declared
single/sequential move sets, and (3) measured improvement on several independently
constructed sparse and dense development embeddings. If the exact model only serves
as an oracle for a later scalable operation, report that role and critique the
new operation before implementation. No paper claim follows from a single toy win.
