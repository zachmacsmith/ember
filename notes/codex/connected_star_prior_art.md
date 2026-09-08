# Connected-center refinement: targeted prior-art review

2026-09-08. Recommendation: describe this as a proposed local minor-embedding
refinement built from established matching and routing methods. The most useful
new comparison is the **polymatroid Steiner problem**, which already couples
connected network selection with distinct assignments. A general claim that
combining Steiner routing, matching, or coordinated chain changes is new would
be untenable. The narrower proposed combination still needs attribution work
and experimental evidence; this review establishes neither novelty nor an
advantage over MM or the existing generic contact operation.

This is a design-only review of
[the connected-center specification](connected_star_relocation_spec.md), SHA256
`f7f411a24fafe9a25dfa7a715ad472f8a465d496be7643d9349086a5cb2c71ab`.
No implementation, embedding run, parameter change, or change to experiment 037
was made. The current singleton-center operation and its comparison remain
separate from this unimplemented extension.

## Six relevant primary sources

The distinctions below compare the stated methods with the current specification;
they are not claims that those methods cannot be extended to cover it. Page
numbers refer to the linked PDF where indicated.

### 1. Călinescu and Zelikovsky: The Polymatroid Steiner Problems (2005)

The paper minimizes tree cost subject to spanning a base of a polymatroid on
the graph vertices. Its sensor application explicitly allows each sensor to
monitor only one target from its allowed set: selected sensors must support a
matching covering all targets. The author manuscript's introductory formulation
identifies these feasible sensor sets with matroid bases and defines the rank
function as monotone and submodular. This is direct prior art for connected
selection constrained by distinct resource assignments, and is more pertinent
than citing ordinary group Steiner alone. [Publisher abstract and bibliographic
record](https://link.springer.com/article/10.1007/s10878-005-1412-9),
[author manuscript](https://www.cs.iit.edu/~calinesc/polysteiner.pdf).

The specification's center and leaf roles must be physically disjoint, and its
leaf resources are outside the selected center. Consequently its matching
coverage as a function of the center can decrease. A direct identification with
the paper's monotone rank formulation is therefore unjustified. This observation
does not rule out an exact reduction with additional constraints; none has been
proved here. Do not import its approximation guarantee.

Verification limit: the publisher abstract was read directly; the explicit
matching/rank passage was available in the search index of the author PDF.
Repeated full-PDF opens failed, so the detailed approximation algorithm was
not independently reviewed.

### 2. Gholami Rudi et al.: RANGI (2013)

RANGI searches for connected subgraphs whose vertices can receive distinct
allowed query colors. Its author preprint, Sections 4.1–4.3, PDF pages 4–7,
describes connected-subgraph enumeration, growth by a neighboring vertex,
branch pruning, and a bipartite maximum-matching validity test. Section 4.2
explicitly trades a cheap distinct-color count against the cost of running the
full matching test. [Author preprint](https://litcave.rudi.ir/rangi.pdf),
[author publication record](https://nit.rudi.ir/cv.pdf).

This overlaps with connected growth, assignment domains, and the proposed cheap
successor bound followed by exact matching. RANGI assigns colors to vertices
inside its connected motif. Here the center occupies a connected set while
assigned leaf sites lie outside it and must meet frozen chain contacts. The
specified first-result, bounded growth policy also differs from motif
enumeration. RANGI does not supply evidence that the proposed Hall-directed
growth will be fast or effective on Zephyr.

Bibliography: *IEEE/ACM Transactions on Computational Biology and Bioinformatics*
10(2), 504–513; DOI `10.1109/TCBB.2012.167`. The author PDF and publication
record were checked; no RANGI code was imported or reviewed.

### 3. Solnon: AllDifferent-based filtering for subgraph isomorphism (2010)

Section 4, Definition 1 on author-preprint page 11, builds a bipartite graph
between neighbors of a pattern vertex and neighbors of a proposed target vertex.
An edge exists when the target neighbor lies in the corresponding pattern
neighbor's domain. A covering matching is required; pages 11–13 discuss
incremental maintenance. [Author preprint](https://liris.cnrs.fr/Documents/Liris-4568.pdf),
[publication DOI](https://doi.org/10.1016/j.artint.2010.05.002).

For a fixed connected center, contracting it to a root leaves precisely this
kind of neighborhood/domain assignment test for the selected leaves. The
frozen-center contacts need an additional coverage check. Independent source
leaves make the restricted assignment certificate sufficient, while arbitrary
subgraph-isomorphism instances still have additional constraints. This supports
attributing the certificate to conventional constraint matching. It does not
choose a center footprint or supply the proposed physical routing policy.

The fresh web fetch failed; the previously downloaded primary PDF was rechecked
locally. It is preserved at
[Solnon_LAD_author_preprint.pdf](../../results/codex/induced-star-witness/Solnon_LAD_author_preprint.pdf),
SHA256 `2dcf030f09096d8f2d53e853b1bae02d3d21993eca525b61818cc5493f0517af`.

### 4. Régin: A Filtering Algorithm for Constraints of Difference in CSPs (1994)

The AAAI paper represents distinct-value constraints by a variable/value graph,
tests feasibility with a covering matching, and uses alternating paths and
cycles for filtering. Its deletion-propagation procedure reuses an existing
matching rather than always recomputing from scratch; see PDF pages 3–4,
Algorithms 1–3. [Official AAAI paper](https://cdn.aaai.org/AAAI/1994/AAAI94-055.pdf).

Assignment matching, alternating searches, and reuse after deleted choices are
established components. The paper does not establish the specification's routing
rule that expands a physical center toward a new site for an alternating-reachable
leaf. In particular, its filtering argument cannot turn an interrupted search
into a maximum-matching or Hall-deficiency certificate. The connection here is
algorithmic machinery, not an equivalent embedding objective.

### 5. Cai, Macready and Roy: A practical heuristic for finding graph minors (2014)

Section 3 constructs a vertex model using distances to neighboring models,
root selection, and unions of paths. Its implementation discussion explicitly
allows singly used path portions to be assigned to neighboring models, so
coordinated ownership changes are already present. Section 5 gives localized
multisource shortest-path search. [Primary arXiv manuscript,
1406.2741v1](https://arxiv.org/html/1406.2741).

This is close prior art for localized routing and modifying related branch
sets. The proposed operation instead releases a selected block, represents
movable singleton leaves by domains, and commits a valid strict-qubit reduction
only after a joint assignment certificate. Those are distinctions from the
described procedure, not proof of novelty or superior search. The 2014 text is
also not an audit of every mechanism in today's MM implementation.

The HTML masthead displays a later rendering date; the version identifier is
`1406.2741v1`, submitted 10 June 2014. Its reported hardware experiments concern
Chimera, not evidence for this proposal on Z12.

### 6. Bian et al.: Discrete optimization using quantum annealing on sparse Ising models (2014)

Section 2.2.2 formulates disjoint routing of several terminal sets and discusses
multicommodity formulations, greedy Steiner routing, and rip-up routing.
Section 2.2.5 explicitly describes adding a free qubit, removing or transferring
one between chains, and exchanging two qubits between different chains while
preserving chain connectivity. Its partial-embedding objective includes missing
contacts and chain sizes. [Primary Frontiers article](https://www.frontiersin.org/journals/physics/articles/10.3389/fphy.2014.00056/full).

Joint ownership constraints and local changes to multiple branch sets therefore
need attribution. The proposed move changes a whole selected star and solves
its singleton leaf assignment simultaneously, with outside chains frozen and
strict final qubit descent. The cited passages do not give that exact move, its
Hall-directed growth, or its budget policy. They provide no basis for saying
that this proposal dominates their move sequences.

## Mathematical implications for this design

The following are deductions from the specification, not claims made by the
papers above.

Let `B_l` be the static allowed sites for selected leaf `l`, after releasing
the selected old chains and retaining all outside chains. For a connected
center `T`, the domain is `B_l ∩ (N_H(T) \ T)` restricted to available sites.
The maximum matching size on these domains is `nu(T)`.

1. **Center growth has a real exclusion constraint.** Consider an available
   path `r—x—y`, with a frozen vertex `w` adjacent only to `x`. A leaf needing
   contact with `w` has `B_l={x}`. It can be assigned when `T={r}`, but not when
   `T={r,x}`. Thus `nu` falls from one to zero although the center grew. This
   tiny graph argument explains why a monotone Steiner rank assumption fails.
   Duplicating physical sites into independent routing and assignment copies
   would erase the conflict unless the reduction also enforced their exclusive
   use; no such equivalence has been established.
2. **Hall-directed expansion has a conditional rationale.** Starting from a
   completed maximum matching with unmatched leaves, alternating reachability
   identifies a deficient leaf set. Adding a genuinely new right-side site
   adjacent to a reachable leaf, while retaining every old domain edge, creates
   an augmenting path. Actual center growth can also delete a matched right-side
   site, so the same conclusion does not hold for its net effect. A BFS goal
   outside the center and its proposed path is necessary to avoid consuming
   that goal immediately; it does not guarantee a final complete assignment.
3. **The incremental update bound is not a runtime guarantee.** With fixed
   selected leaves, fixed outside ownership and static `B_l`, adjoining `x`
   removes at most one old right-side site and exposes at most `Delta-1` new
   sites. The retained matching needs at most `Delta` successful augmentations
   to become maximum again. Edge scans, failed searches, domain evaluation,
   copying and rollback can still be expensive and must remain charged.
4. **Fixed-center exactness does not make the search exact.** One root, one
   independent leaf subset, four shortlisted one-step successors and a greedy
   center-growth trajectory may miss an improving replacement. Failure of the
   completed matching proves infeasibility only for that fully represented
   fixed center; a truncated or exhausted heuristic query proves no broader
   exclusion.

## Remaining empirical and attribution questions

The potentially useful contribution is a bounded move inside one evolving
embedding: choose a connected center while maintaining distinct movable leaf
assignments and all frozen contacts, then commit strict qubit descent. Its
usefulness must be measured against the existing generic reconstruction and
the singleton-center move on the same inputs and resource limits. The existing
size-three physical witness is not a witness for an advantage of this
connected-center extension.

If the extension is later authorized, separate experiments should determine
whether Hall-directed routing adds value beyond an ordinary missing-contact
signal, whether incremental matching reduces actual elapsed time, and whether
larger selected blocks justify their setup and domain costs. Report failures,
budget truncations, lost ordinary improvements and end-to-end totals. Such
fixed-policy ablations test mechanisms; they must not select a winner per input
or alter the already frozen 037 comparison.

The bounded search covered matching-constrained Steiner formulations, connected
list-color assignment, constraint matching, and explicit minor-embedding local
moves. It did not verify an earlier implementation of this exact combination.
That is an unresolved literature question, not evidence of absence. It also
did not review all contemporary MM source, all network-design variants with
exclusive roles, or all subgraph-constraint solvers. No source here establishes
MM-scale runtime, a Zephyr-wide ACL gain, or publication novelty for this design.
