# Geometry-guided contact search: heuristic design

2026-09-07. Current lead hypothesis after user prompt 4. The user requires a single
non-portfolio algorithm roughly within MM's runtime order of magnitude. This design
is unimplemented. Its pre-implementation critique is below. The IP-led design in
`joint_region_spec.md` is superseded as the runtime method and retained only as a
tiny diagnostic oracle.

## One state and one fixed construction path

Maintain physical chain sets, qubit ownership, connected-tree representations,
logical contact witnesses and explicit missing vertices/edges. Every realized chain
must be connected, target-valid and disjoint from other realized chains. A state
with missing logical contacts is an intermediate assignment, not an embedding.

Use one reproducible structural ordering and a bounded number of geometric
packing/conversion passes to propose the initial chains. The existing order-based
code is a source of auditable primitives, not a mandatory long optimization phase.
Compare a cheaper shared-order construction against it as separate development
revisions; freeze one constructor for the chosen algorithm. Never run several
complete constructors and choose their best result at runtime.

Native construction may leave overlaps, disconnected sets, missing vertices or
missing contacts. An explicit conversion into the authoritative state must resolve
ownership deterministically, retain a connected component for each realized chain,
and place discarded/missing vertices in a pending set. Recompute every lost contact.
Nothing is marked successful during this normalization. Its cost and how much useful
geometry it discards are measured; repeated destructive normalization rejects that
constructor revision rather than being hidden in a fallback.

## Bounded joint reconstruction

1. Choose a pair of interacting chains, or a small group (initially 2–4) including
   missing vertices or blockers. Use measured missing contacts, current qubit cost
   and local congestion; source family labels and graph IDs are unavailable.
2. Release complete selected chains provisionally. Their old qubits plus a bounded
   set of nearby free vertices form the allowed region. Unselected chains remain
   fixed. A contact to a frozen chain can use any actual adjacent qubit in that
   chain; do not freeze the old contact endpoint unnecessarily.
3. Generate a few connected alternatives for the next selected logical vertex.
   Grow trees toward uncovered neighboring-chain contact sets, charging actual new
   qubits and reusing existing tree vertices at zero additional qubit cost. Use
   several root/contact/tie choices to retain occupancy-diverse alternatives.
4. Store a small beam (initially 4–8) of partial **joint** assignments, including
   unresolved contact obligations and reversible occupancy changes. Expand them
   with another chain. An early route can be rejected when it prevents a later
   chain from connecting. Try both orders for pairs; bound order search for larger
   groups. These are local search alternatives, not independent embedding algorithms.
5. Rank complete proposals by global remaining missing vertices, then missing
   logical contacts, then actual total qubits. All constraints touching the group
   enter the score; unchanged outside-outside contacts are constant. During valid
   refinement, require zero deficits and a strict reduction in total qubits before
   committing an improved incumbent. One member may lengthen if the group's net
   qubit change is negative.
6. Validate the proposal, commit atomically or roll back. Keep a fully valid
   incumbent separately from exploration state. A bounded plateau/backtracking
   policy may revise working choices during construction; it must have explicit
   visit/work limits and cannot be described as guaranteed feasible descent.

The same operation completes missing vertices/contacts and shortens valid chains.
Its final full-embedding validator checks exact source coverage, membership,
connectivity, disjointness, duplicate entries and all source edges against the
original immutable target. Local caches and claimed certificates never replace it.

## Time and memory discipline

Cap group size, physical-region size, beam width, tree alternatives, routing vertex
expansions, total proposals and wall time. Include old chain choices among proposals
so the search can retain a valid configuration; a bounded beam may still prune it,
therefore rollback must preserve an independent incumbent.

Use arrays or compact bitsets for qubit ownership/contact sets, and undo records
instead of copying the whole graph per beam prefix. A bounded BFS/tree-growth pass
is linear in the inspected local graph; total work multiplies by the number of
beam expansions and uncovered contact searches. That multiplier must be measured,
especially on dense graphs. Avoid claiming linear total runtime from linear BFS.
Cache static geometry or optimistic distances. Recheck or invalidate paths and
reachability whenever occupancy changes. Compile/profile the measured hot loop
after correctness is established; changing languages alone is not a new algorithm.

Initially target about 1x, 3x and 10x stock-MM end-to-end times on development
instances, with equal-time curves. Freeze a practical size-based work/time policy
before holdout evaluation; never use a holdout's MM embedding or output to configure
the candidate. Report time to first valid embedding and later quality improvement,
including source layout, conversion, cache setup, validation, and all failed moves.
No routine IP call is part of this implementation. Tiny exact diagnoses are separate
experiments; a future optional exact subroutine needs a cost-benefit result first.

## Decisive development experiment

Use independently constructed inputs from cliques, bicliques, Erdős–Rényi, random
regular, Watts–Strogatz, grid, honeycomb and king graphs at several sizes. These are
development diagnostics, not the final family set. Pair the same constructor,
selected regions and routing primitive under beam widths 1, 4 and 8, and compare
one-chain versus coupled replacement with equal total routing/time budgets.

Record complete-embedding success; actual ACL and maximum chain; construction and
refinement time; routing expansions; beam rejection reasons; memory; accepted net
qubit reductions; and how many improvements require at least one member to grow.
Keep full trajectories and embeddings. A toy example with deltas +1 and -3 gives
net -2 qubits; demonstrate the limitations of the specific single-chain move set
rather than asserting all single-chain algorithms cannot achieve the same result.

Promote only if useful coupled improvements survive these controls, construction
remains reliable, dense quality is retained, and representative runtime stays
roughly within 10x MM. If benefits appear only with broad regions, large beams,
or expensive exact repair, record the limitation and revise/reject that version.

## Self-critique before implementation

The beam is still an ordered approximation to a coupled problem. It can discard
the only useful prefix, and sequential tree construction might not generate the
needed mutually changing contacts at any small width. Regions can be too local for
small-world edges; dense contact sets can make routing expensive; inexpensive
initial geometry may sacrifice the previous dense improvements. Reversible state
and caches introduce correctness risks requiring targeted tests against a simple
uncached implementation on small cases.

Beam search, Steiner growth and local rerouting are not new individually. CMR also
reassigns some path portions between neighbors, and the current repository already
rebuilds groups greedily. The potential contribution is a precise bounded coupled
contact/ownership neighborhood and its efficient use of native Zephyr, demonstrated
to improve quality at comparable order of runtime. It remains a hypothesis until
the literature comparison and ablations substantiate it.
