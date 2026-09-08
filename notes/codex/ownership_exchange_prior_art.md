# Ownership exchange: closest prior mechanisms and contribution boundary

2026-09-08. Bounded primary-source review, with no implementation, solver,
corpus, cluster or new diagnostic calls. Reviewed the exact
[design](research_next_mechanism_review.md), SHA-256
`0f0db0b06c9808f1ad41b93fb53d5a817d89ea11536f754f2085deaaec594295`.
The conclusion is **substantial prior overlap and an unproved narrower
contribution**, not established novelty.

## Exact proposal under review

The detailed design preserves nonempty connected chains and disjoint ownership
after every exploratory transfer/swap. Only logical contacts may temporarily
be missing. This is narrower than allowing arbitrary invalid partial assignments.
It first removes a contact-essential site whose removal preserves its chain's
connectivity. The remaining occupied sites are redistributed among selected
whole chains; admission may expand that selected set through a blocking owner.
Outside ownership stays fixed, global Q remains exactly one below entry Q, and
only a complete valid improvement is published. Search uses fixed caps and a
shared deadline. The source graph within the selected set need not be a star.

## Closest primary mechanisms

**Bian et al. (2014), §2.2.5, is the closest elementary move set.** Their partial
embedding consists of disjoint connected chains, with unsatisfied logical edges
allowed. The annealing score combines distances for missing edges and a small
penalty on squared chain sizes. Moves add a free qubit, delete or transfer one
while preserving its chain, or exchange two qubits between chains subject to
connectivity conditions. Thus deleting a contact-essential qubit, temporarily
losing contacts, and changing ownership to repair them are established. The
inspected formulation does not prescribe the proposed deletion-conditioned,
Q−1 occupied-patch search or its admission rule. Its exchange test removes each
site before checking chain validity; do not silently equate that test with an
atomic swap of two singleton chains. [Primary article, §2.2.5](https://www.frontiersin.org/journals/physics/articles/10.3389/fphy.2014.00056/full).

**PSSA supplies whole-chain swaps and ownership shifts.** Sugie et al. describe
swapping logical assignments of two chains, shifting a leaf between chains and
annealing the number of represented logical edges. Their terminal phase deletes
only sites that preserve nonemptiness, connectivity and the represented-edge
count, then uses free-site BFS to repair remaining missing edges. The proposed
initial deletion deliberately crosses that terminal phase's contact-preserving
boundary; its fixed Q−1 search also differs from PSSA's annealing objective.
However, singleton-owner swapping is already a special case of whole-chain
swapping. The proposed hand witness demonstrates a deletion barrier and swap,
not a fundamentally new ownership operation. The cited experiments emphasize
large King's graphs, not current ideal-Z12 ACL refinement. [Paper, Algorithms 1–2, §§3–4.1 and Appendix 8.2](https://arxiv.org/html/2004.03819).

**CMR already reconstructs ownership and searches through infeasibility.** It
removes and reinserts one vertex-model using occupancy-weighted shortest paths;
temporary chain overlap is permitted. Its implementation discussion assigns
shared path portions to the rebuilt model and singly used portions to a
neighbor's model. Its localized variant searches near the prior root. Hence
multi-chain ownership changes and local search are not sufficient distinctions.
The proposed design instead fixes occupied material after one deletion and
searches contact deficits while retaining disjoint connected chains. That is a
different restricted search process, not proof of a larger or better reachable
neighborhood. [CMR, §3 implementation improvements and §5](https://arxiv.org/html/1406.2741).

**Current MM already supports refinement and constrained domains.** The official
API documents valid initial embeddings entering chain-length improvement,
unchangeable `fixed_chains`, restricted physical domains and `suspend_chains`
requirements to intersect specified target sets. This matters because starting
from an incumbent, freezing outside assignments and representing contact sets
are established capabilities. It does not establish that the current C++
implementation executes the proposed deletion-conditioned exchange search.
The 2014 CMR pseudocode alone cannot characterize the present baseline. No MM
call or source reuse is proposed. [D-Wave general-embedding API, observed Ocean 9.4.0 documentation](https://docs.dwavequantum.com/en/latest/ocean/api_ref_minorminer/source/general_embedding.html).

**ATOM and CHARME are less direct.** ATOM chooses clean shortest paths for a new
logical vertex and distributes their unoccupied sites between the new chain and
existing neighbors using degrees. Its topology adaptation relocates an existing
embedding into an expanded Chimera structure and adds connecting sites. The
inspected procedure does not contract a fixed occupied patch by exchanging its
owners. [ATOM, Algorithms 2–3 and §III-B/C](https://arxiv.org/html/2307.01843).
CHARME chooses the next logical vertex and uses ATOM's deterministic insertion/
adaptation transition. That learned insertion order is distinct from searching
joint reassignment of already occupied sites after a forced deletion.
[CHARME v2, §3.3 and Algorithm 1](https://arxiv.org/html/2406.07124v2).

**Ejection chains limit the generic novelty claim.** Glover's author-hosted
paper constructs compound moves through reference structures that need not be
feasible tours; feasible trial completions are recovered from them. Section 4,
printed p. 232, explicitly distinguishes the intermediate steps from feasible
tour modifications. Thus temporarily damaging a constraint, propagating an
exchange and publishing a repaired solution is a longstanding search principle.
This TSP construction is an analogy, not a minor-embedding algorithm or a
transferable runtime theorem. The proposed bounded DFS is not automatically a
specialized ejection-chain algorithm merely because it uses transfers.
[Glover, 1996, §§3–4](https://leeds-faculty.colorado.edu/glover/fred%20pubs/266%20-%20TSP%20-%20Ejection%20Chains%20DAM%201996.pdf).

A targeted search also surfaced Gómez-Tejedor et al.'s current study of minimal
embedding quality. Its stated contribution evaluates MM/clique embedding and
hardware-solution effects; it is not evidence of a new ownership-exchange
operator. I did not count general optimization LNLS using precomputed embeddings
as local search *of* embeddings. [Primary preprint](https://arxiv.org/html/2504.13376).

## One defensible, still unproved contribution boundary

The research hypothesis can be stated narrowly: **a deletion-conditioned,
connected ownership-exchange search with conflict-driven admission of occupied
whole chains can find useful one-qubit contractions at bounded cost that the
fixed sequential whole-chain reconstruction misses on Zephyr.** This describes
what needs evidence, not an originality or performance result.

The informative distinction would be the combined search restriction, boundary
representation and cost-effective exploration, rather than ownership, missing
contacts, locality, deterministic ordering or a final validator individually.
Ordinary reconstruction already changes multiple owners and may find exactly
the same contractions. Comparison should therefore include the existing fixed
ordinary proposer and bounded elementary transfer/whole-chain-swap controls from
the same incumbent and under disclosed total work/time. These are experimental
comparisons, not runtime selection among outputs.

## Self-critique and unresolved evidence

For fixed p occupied sites and k selected owners, even the unconstrained labels
of the p−1 remaining sites number k^(p−1). Connectivity/contact tests prune this
space but do not make a 256-state, top-four, depth-eight search exhaustive.
Pruning must preserve contacts to every fixed chain and connectivity through all
retained portions; a patch boundary cannot be replaced by one arbitrary anchor.
Admission, undo, ownership refresh and failed successor generation may dominate
the useful search. Atomic publication and exact global validation are correctness
requirements, not novelty contributions.

The occupied-only restriction cannot use the free-site shortcut in the design's
counterexample. Connected intermediate chains can also exclude contractions
requiring temporary disconnection or extra sites. Strict one-qubit reduction
can produce a worse later local minimum. A hand witness establishes neither
uniqueness versus ordinary reconstruction nor useful corpus coverage. This
review did not execute that witness or verify the design's historical result
tables anew.

The bounded search inspected these primary descriptions, not every published
variant or every MM internal move. No absence claim follows from unproductive
search terms. Before a publication claim, require independent original-graph
certificates, actual extra contractions versus the fixed ordinary control,
complete unsuccessful-work accounting, globally fixed full-pipeline results,
new instances/seeds and a fresh same-host MM comparison. Nothing here establishes
an across-class ACL gain or authorizes implementation.
