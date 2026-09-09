# C replacement proposal: conflict-directed source splitting

**Design only, pending review.** Select one replacement: grow a graph of source-vertex copies using bounded heuristic placement. Defer continuous ownership fields, which retain C009's unresolved conversion from soft agreement to one feasible assignment.

**Evidence and hypothesis.** [C009](c_009_results.md) completed no minor: generation consumed 74.7% of solver time, five inputs never published regenerated domains, and path/tree grew Q without completing. Pairwise support did not establish global consistency. [C008](c_008_results.md) also left large sparse-graph Q gaps. Introduce physical sites individually after placement conflicts, revising implicated placements before requiring longer chains. This could preserve singleton opportunities and avoid expensive full-chain alternatives; the evidence does not establish its reach.

**State.** Initially the auxiliary graph equals the source, with one *clone* per owner. Internal edges connect each owner's clones as a tree; every original edge has exactly one auxiliary edge between its endpoint owners. A complete injective subgraph placement implies an original minor. Partial placements are not minors: placed sites may be disconnected through unplaced clones. No chain alternatives or supplied embeddings are used.

```text
Start with the source itself as the clone graph and an empty physical placement.
Select an unplaced clone using placed-neighbor count, admissible-site count,
then auxiliary degree and fixed source/clone rank.
Greedily place it at one ranked admissible unused target site.
If none is found, make at most four prescribed local revision attempts.
If these fail, split the conflicted unplaced clone once, when eligible;
otherwise terminate with its unresolved conflict and complete cost record.
Continue this one evolving state until complete or a fixed bound stops it.
Return only an independently validated, timely original-source minor.
```

**Limited placement neighborhood.** Admissible sites satisfy target degree at least auxiliary degree, adjacency to placed auxiliary neighbors, and injectivity. These are necessary local constraints. Consider the first 32 in one seeded target permutation; choose by minimum, then total, remaining adjacent-site support of unplaced neighbors, with seeded ties. Charge ranking, domains and failed scans.

On conflict, record responsible neighbor constraints and occupied candidate sites. Remove at most four implicated placed clones, ranked by recency; everyone else stays fixed. Greedily replace that block plus the conflicted clone. At most four attempts use successive conflict pivots, without joint-assignment branching. Publish only a fully consistent block; otherwise restore it. There is no retained search tree, global exact CSP/subgraph solver, route-and-erase trajectory, or constructor restart.

**Split rule.** Degree conflicts trigger splitting immediately; adjacency/occupancy conflicts require failed local revisions first. Replace an unplaced clone of degree at least two by two same-owner clones joined internally. Sort incident constraints by increasing individual physical support, ties by fixed edge rank, and distribute alternately. Reassign each incidence exactly once, including internal edges; this preserves owner trees and original-edge identities. Degree-zero/one conflicts cannot split. Each irrevocable split adds one to Q; stop before target size is exceeded. No cleanup: first-valid Q tests whether delayed splitting avoids unnecessary occupancy.

**Self-critique and diagnosis.** Failed heuristic placement does **not** prove that an extra clone is necessary. The four-clone scope, 32-site prefix and fixed partition can miss placements or impose unsuitable trees; older placements can lock geometry and dense splitting can exhaust work. Record conflicts, revised blocks, failed/published placements, Q changes and stage/work limits. Completed failed revisions implicate the tested neighborhood/partition jointly; truncation implicates cost. Only constraint-valid blocks are accepted, so acceptance cannot be assessed without proposal validity. A known singleton fixture wrongly split specifically reveals placement-induced Q inflation. None proves a corpus-level explanation or failure of every clone representation.

Constraint-based physical subgraph placement is established: King et al. use Glasgow for their subgraph mappings in [Supplement I.D](https://www.dwavequantum.com/media/bljnr3zz/beyond-classical-computation-in-quantum-simulation.pdf#page=20). This proposal uses no such solver. Neither source splitting nor its combination with greedy placement has an established novelty claim here.

**Proposed cheap falsifier.** Check clone-tree/original-edge preservation, revision rollback, and interruption/non-credit only. Include a known singleton placement and triangle on six-cycle as representation checks, not efficacy evidence. Then directly test all eight unchanged C inputs, seed 0, ideal Z12, candidate/fresh MM on the same host, fifteen seconds each. Fix 20 million support/adjacency/domain-word operations including setup, reserving 0.5 seconds for original validation/output. Continue only with **6/8 timely valid**, Q no larger than MM on **three common timely inputs** (optimal ACL=1 ties allowed), and median common-pair solver ratio at most **3**. Retain every failure and distinguish work/wall censoring. This proposed sixteen-call exploration is not a launch authorization or confirmation set. Freeze routine pivot ordering and work definitions before implementation. No numerical calls were made.
