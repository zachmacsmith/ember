# Contact reconstruction: bounded prior-art check

Date: 2026-09-07. This is a mechanism comparison, not a novelty claim or a
performance result. No algorithm source was changed and no experiment was run
for this note. The earlier [literature review](literature_review.md) was a starting
point; the primary papers below were reopened and their relevant mechanisms
checked against the actual implementation.

## Implementation examined

Repository HEAD: `580d20447a78f92cafa2343bd63794fcb6a87c82`. The working tree
contains uncommitted work. SHA-256 of the examined
`packages/ember-qc/src/ember_qc/algorithms/factored/contact_repair.py`:
`b8a73f42e401e4db37b31b521d110cd91270ae63fa5c5839b01f581bc6fffd93`.

The implemented primitive starts from a valid embedding. It releases one to four
whole chains provisionally, retains the outside chains, and limits replacement
to the old selected qubits plus a bounded free-qubit halo. Each selected chain
must contact its frozen and already-reconstructed neighbors; still-pending
selected neighbors provide a preference based on their old locations, not a
fixed contact obligation.

Tree proposals use bounded BFS from the growing tree to uncovered contact sets.
Several root/tie choices generate alternatives. A bounded beam stores partial
joint assignments and their occupied qubits; prefix ranking currently favors
smaller cumulative size. Complete candidates are fully validated and accepted
only if the total selected qubit count strictly falls. Individual chains may
grow. Several reconstruction orders are considered under explicit limits.

These observations follow from `_grow`, `_alternatives`, `_repair`, `repair_group`,
and `contact_polish`. Group proposals use chain excess, source adjacency, and
physically adjacent occupied chains; a blocker need not be a logical neighbor.
The module uses the supplied target adjacency: the repair
primitive itself contains no Zephyr-coordinate-specific construction. Describing
this module alone as a novel native-Zephyr geometric algorithm would overstate
what is implemented.

The [construction specification](contact_search_spec.md) additionally proposes
states with missing vertices/contacts, followed by lexicographic ranking of
missing vertices, missing contacts, and qubits. That partial-repair behavior is
not provided by the examined valid-input API. Its correctness, acceptance policy,
and experimental contribution remain separate questions.

## Three closest prior mechanisms

### 1. CMR: localized chain reconstruction and ownership reassignment

Cai, Macready, and Roy reconstruct a logical vertex's model using paths to its
neighboring models, penalizing overlapping occupancy. Their implementation
discussion explicitly allows singly used portions of those paths to be assigned
to neighboring models. Section 5 localizes the search using multisource shortest
paths and the previous root. Thus shortest paths to chain sets, movable contacts,
local search, and changing neighboring ownership are all present in the original
method. See Section 3, Figure 4, and Section 5 of
[A practical heuristic for finding graph minors](https://arxiv.org/html/1406.2741).

The concrete candidate distinction is its bounded search over alternative
reconstructions of a selected group, with disjoint occupancy within each prefix
and acceptance by total group qubits. That distinction must be stated at the
move-set level. The existing toy fixture only separates specified strict
single-chain and fixed-order greedy controls; it cannot establish that CMR or
modern MM cannot reach the same final embedding through other moves.

Current MM also documents fixed chains, restricted chain domains, refinement
from initial embeddings, and a `suspend_chains` transformation requiring a chain
to intersect each supplied qubit set. These features further limit claims that
frozen boundaries or set-valued contacts alone are new. The opened documentation
identifies MM 0.2.22; it is not a substitute for auditing the experiment's exact
pinned baseline. [D-Wave general embedding documentation](https://docs.dwavequantum.com/en/latest/ocean/api_ref_minorminer/source/general_embedding.html).

### 2. Bian et al.: partial-chain optimization and joint routing

Section 2.2.5 already describes disjoint partial chains with unfulfilled logical
edges. Its score combines distances for unfulfilled edges and a small penalty
on squared chain sizes. Moves add an unused adjacent qubit, remove or transfer
a qubit while preserving connectivity, or exchange qubits between two chains.
This is direct prior art for the proposed partial-state representation and
contact-versus-size objective family.

Section 2.2.2 separately gives joint disjoint Steiner routing using multicommodity
MILP, greedy routing, and occupancy-penalized rip-up routing. Those routing
problems connect predetermined terminal sets. See
[Discrete optimization using quantum annealing on sparse Ising models](https://www.frontiersin.org/journals/physics/articles/10.3389/fphy.2014.00056/full).

The present candidate instead uses whole-chain alternatives in a bounded beam
and variable physical contact locations. Its planned lexicographic missing-edge
count and total qubits also differ from the stated distance/squared-size score.
These are distinctions to investigate, not evidence that this combination is
unprecedented. The earlier literature note emphasized routing and missed the
particularly relevant partial-embedding subsection; that omission matters.

### 3. Improved PSSA: missing-contact search and BFS repair

PSSA maintains disjoint connected placements and scores the number of realized
logical edges. Swaps and endpoint shifts can be accepted despite temporarily
losing contacts. Its terminal search deletes unnecessary qubits and then uses
free-vertex BFS to connect missing logical edges. The paper explicitly notes
that a shortest route can obstruct another connection, whereas a longer route
could avoid that obstruction, and that routing order matters. These observations
appear in Sections 2.1, 3, and 4 of
[Minor-embedding heuristics for large-scale annealing processors with sparse hardware graphs of up to 102,400 nodes](https://arxiv.org/html/2004.03819).

Consequently, neither “optimize missing contacts while preserving disjointness”
nor “sometimes grow one route so another can connect” is a new motivation.
The candidate's testable distinction is retaining alternative *joint* chain
assignments before committing a complete group change, instead of terminal
sequential BFS plus the described swap/shift search.

PSSA's examined experiments prioritize embeddable size on King's graphs; they
do not establish ACL behavior on fixed ideal Z12. Its clique-pattern initializer
must not be silently imported into the candidate. This comparison is to the
published mechanism, not a complete audit or reproduction of every PSSA variant.

## ATOM and CHARME: relevant, but different primary decisions

ATOM chooses a center using clean shortest-path distances to already embedded
neighbors, then assigns free qubits along those paths to both the new chain and
existing chains according to logical degree. Failed insertion invokes Chimera
topology adaptation. The exposition assumes enough available hardware; this does
not guarantee success on a prescribed fixed Z12 target. See Section III and
Algorithm 2 of
[ATOM: An Efficient Topology Adaptive Algorithm for Minor Embedding in Quantum Computing](https://arxiv.org/html/2307.01843).

CHARME's action chooses the next logical vertex. Its deterministic transition
uses ATOM's node-embedding and topology-adapting procedures; order exploration
supports learning that choice. Section 3.3 does not specify the candidate's
small-group beam reconstruction. See
[CHARME: A Chain-Based Reinforcement Learning Approach for the Minor Embedding Problem](https://arxiv.org/html/2406.07124v2).

The defensible comparison is therefore construction order and insertion/extension
versus coordinated reconstruction of existing ownership. “A chain-based state,”
clean BFS, or extending an existing neighbor during insertion is insufficient
as a distinction. This review did not audit their current executable call graphs
again; the earlier note's provenance cautions remain applicable to any reuse.

## What a discriminating experiment must establish

The following are proposed controls and failure criteria derived from the code,
not results reported by these papers. They are separate experimental variants,
not a portfolio inside the candidate.

| Claimed practical distinction | Required evidence | Interpretation if the control matches it |
| --- | --- | --- |
| Keeping interacting route alternatives matters | Same starting embedding, selected group, halo, route generator, reconstruction orders, and total work/time; compare beam width one with wider beams | A different budget or order explains the apparent advantage; no beam-specific benefit established |
| Whole-group replacement helps beyond simpler updates | Compare with one-chain reconstruction, both pair orders, and bounded sequences of simple connected ownership transfers from the same state | The larger move may remain useful, but the fixture does not isolate an advantage over simpler moves |
| Movable contacts reduce cost | Compare original endpoint restrictions against full adjacency-to-frozen-chain contact sets with otherwise identical search | This is an effective implementation choice if it helps, not novelty in set-valued contacts |
| Partial repair improves construction | Start every control from the same normalized state; compare sequential free-space contact BFS and coupled reconstruction at equal budgets; report time to first valid embedding and all remaining deficits | A polish-only gain or an easier initializer does not establish better construction |
| Net group size is the useful acceptance quantity | Log accepted deltas for every member, including growth, final net savings, and contact changes | Merely changing chain ownership without quality/success benefit is not sufficient |
| The method improves the intended research outcome | Fixed Z12, paired source instances, one frozen candidate path, pinned MM baseline, per-family ACL and success, whole-run timing | Toy feasibility and a few favorable chain moves do not establish an Ember-wide advantage |

The current prefix score is principally cumulative qubits, so it can discard a
slightly larger prefix that leaves substantially better contact opportunities.
The toy fixture demonstrates that this can matter at width one. It does not
establish that a small width retains enough diversity on real Z12 instances.
Record completion/rejection causes and quality gained per inspected target
vertex as well as per second.

For planned partial repair, strict descent in `(missing contacts, qubits)` can
reject intermediate growth that approaches a missing contact without realizing
it yet. A full regional reconstruction can sometimes bridge the entire gap in
one move, but finite regions need not permit that. The specification's bounded
plateau/backtracking policy therefore needs explicit implementation and tests;
a successful lexicographic descent is not a feasibility guarantee. Any distance
heuristic used to guide those transitions should be compared against the
distance-based precedent above, not presented as a new objective family.

## Scope and uncertainty

Searches covered minor embedding with joint rerouting, multiple-chain repair,
beam search, and local/large-neighborhood search, in addition to the named
papers. No examined source established this exact bounded implementation, but
that is not evidence of absence of prior art. The code's BFS, beam search,
reversible occupancy, and destroy/reconstruct pattern are established general
search ingredients.

Some search hits for “large neighborhood local search with efficient embeddings”
concern solving the *QUBO* using embedded subproblems, rather than improving the
minor embedding itself. The [AQC 2021 author abstract](https://aqc2021.org/oral_abstract/day1/Jack_Raymond.pdf)
makes that distinction clear. Such work is contextual, not evidence that the
same embedding-reconstruction move was already implemented.

The remaining plausible contribution is a precisely defined, efficiently bounded
group reconstruction mechanism that demonstrably improves a single independent
construction/refinement algorithm. Its originality and practical value both
remain unestablished. Claims about runtime, every Ember family, or Zephyr-specific
advantages require the corresponding experiments; this note supplies none.
