# Construction proposal: reserve connected unused access before coarsening

Design proposal only, 2026-09-08. Do not implement or change the current neutral-transport experiment on its basis. This is a possible next direction within track C, not a fourth concurrent research track or a combination of completed outputs.

**Hypothesis.** C006 partitions every vertex of its selected compact target into occupied regions. Unused vertices lie outside that selection; many internal chains then have no unused neighbor. Repairing this geometry after source assignment can require several constrained owner changes. Reserving a connected dominating set of unused vertices before coarsening could make every initial region accessible through a common unused component. This trades initial quotient contacts for routing freedom. It is a different construction hypothesis from searching harder in the saved final states.

The current code establishes the structural premise: `quotient_compact._subset` selects the compact induced target, and `quotient_distinct._coarsen` partitions every selected vertex into one of exactly n occupied regions. The final supplied-state diagnostics establish sealed endpoints, but do not prove when each endpoint became sealed or that initial reservation improves final quality.

## Candidate mechanism to review

Let U be the unchanged connected target selection, and choose its already computed center as the first reserved vertex. Build a connected dominating set D inside U by this fixed greedy rule. With dominated set B = D union N_U(D), repeatedly add a vertex x in N_U(D) outside D maximizing the number of previously undominated vertices in its closed neighborhood. Break ties by fixed target rank. Stop when B = U. If U is connected and B is incomplete, a boundary vertex with positive gain exists: take the middle vertex on a shortest path from D to the nearest vertex outside B (which has distance two). Every added vertex is adjacent to D, so D stays connected. No claim of a minimum or approximate-minimum dominating set is made.

```text
select the unchanged compact target U
D = {the unchanged selected center}; B = closed_neighborhood(D)
while B != U:
    x = boundary vertex with maximum newly dominated count, fixed-rank tie
    add x to D; update B
let O = U minus D
if |O| < number of source vertices or components(O) exceed that number:
    fail this initialization under the declared policy
coarsen O into exactly one connected region per source vertex
    retaining the existing distinct-neighbor contraction rule
assign source labels by the unchanged rule
keep D unused and expose full target adjacency for later source-edge routing
```

The geometric invariant is elementary: every occupied vertex outside D is adjacent to D, hence every nonempty occupied region has an unused neighbor. Since D is connected, any pair of occupied regions can initially be joined through unused vertices. This proves initial path availability only. Routing consumes those vertices; it can disconnect D or seal other regions. It also says nothing about the chain lengths of the eventual embedding or the number of source edges already represented by the initial quotient. A full candidate would need an explicit routing/search schedule and budget before implementation; this proposal does not specify one yet.

The current coarsener can only merge adjacent regions. A connected partition into n nonempty regions requires at least n occupied vertices and at most n occupied components. Those checks are useful immediate falsifiers. If they pass, the initializer must use actual occupied adjacency; it must not accidentally contract through the reserved set. Physical labels and the full target remain available to the original independent validator.

## Cheap falsifier before a constructor

If adopted for investigation, freeze the same eight exposed C inputs and their existing selected target sets. Under a small fixed per-input allowance, run only the proposed reserve selection and initialization; no source-edge search, cleanup or MM. Report every failure, reserve size, occupied component count, remaining vertices versus the existing degree bound, initial distinct quotient contacts, initially represented source edges and free-component access. Compare initial contacts with the already saved C006 values as descriptive evidence, with no historical timing claim. The dominating-set invariant should be independently checked on tiny graphs and on each retained initializer. If the reserve prevents even forming n regions, consumes most of the target, or destroys the contact capacity needed for dense inputs, stop before a full constructor.

**Self-critique.** Connected domination may reserve expensive high-degree vertices and remove the very cross-region contacts that make Zephyr useful. The complement can fragment into many components. The unchanged compact selection may be too small after reservation. A connected free region guarantees paths one at a time, not simultaneous disjoint routing or safe sequential consumption. Protecting every future endpoint could again create difficult global contention. For dense sources, many missing contacts may overwhelm even a connected reserve; for sparse sources, coarsening still begins with unnecessarily large chains. This is a conventional graph property used as a construction constraint, with no novelty or all-class performance claim. Any implementation needs a separately frozen exact experiment and should not expand allocation or alter the routing policy in response to observed inputs.
