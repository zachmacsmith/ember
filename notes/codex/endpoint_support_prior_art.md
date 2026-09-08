# Distinct endpoint support: targeted prior-art review

2026-09-08. Bounded primary-source review; no algorithm implementation or
embedding calls. Recommendation: treat endpoint support as an experimentally
testable secondary potential, with explicit credit to existing witness tracking
and chain deletion methods. This review did not locate the exact proposed
histogram objective, but does not establish novelty or expected ACL improvement.

For a valid embedding of source G into target H, define

\[
S_{u\to v}=\{q\in C_u:N_H(q)\cap C_v\ne\varnothing\},\qquad
s_{u\to v}=|S_{u\to v}|.
\]

These are directed sets for each source edge. They count physical **vertices**,
not the number of couplers between chains. The proposed secondary comparison
lexicographically minimizes \(N_1,N_2,\ldots\), where \(N_j\) counts directed
source edges with support size j, only between valid states with equal total
qubit count Q. All available target couplers count; choosing a different recorded
witness for an unchanged embedding cannot change this potential.

The closest verified mechanisms are as follows. Statements about absence refer
only to the specified passages, not every implementation or subsequent work.

| Primary source and passage | Verified overlap and distinction |
| --- | --- |
| [Cai, Macready and Roy, 2014, §3 and implementation improvements](https://arxiv.org/html/1406.2741) | Reconstruct a chain using weighted shortest paths to neighboring chains. Neighbor chains are sets of possible destinations, handled with a dummy vertex. Shared path segments belong to the reconstructed chain; a segment used by only one path may instead extend its neighboring chain. The specified progress measures concern overlap and summed chain size. Contact choice and ownership redistribution are established ingredients; these passages do not maximize the number of alternative supporting endpoints. |
| [D-Wave C++ reference, document labelled release 0.2.6, printed pp. 27–30 and 44–47](https://app.readthedocs.com/projects/d-wave-systems-minorminer/downloads/pdf/latest/) | `get_link`/`set_link` record one linking qubit for each neighboring logical variable. `refcount` includes parent and link references; `trim_leaf`/`trim_branch` remove dispensable tree portions; `steal` transfers available qubits while updating links. `flip_back` distributes path segments to neighbors. Thus explicitly tracking endpoint witnesses to support chain reduction predates this proposal. A selected-link reference count is different from the cardinality of the complete set S. |
| [Current D-Wave general-embedding API](https://docs.dwavequantum.com/en/latest/ocean/api_ref_minorminer/source/general_embedding.html) | `chainlength_patience` governs passes reconstructing chains adjacent to all logical neighbors. Valid initial chains can enter this improvement phase directly. Reported progress includes maximum chain length and the number of longest chains. The public API supplies no documented distinct-endpoint histogram objective; API silence does not establish its absence from all internal behavior. |
| [Sugie et al., 2020, PSSA §4.1 and Appendix 8.2](https://arxiv.org/html/2004.03819) | A qubit is deletable only when removal preserves a nonempty connected chain and does not reduce the number of represented logical edges. Repeated deletion frees hardware for BFS repair of missing logical edges. This is the closest direct shrinkability criterion: for a valid incumbent, its contact-preservation part is equivalent to the support-set test below. The paper's stated PSSA score counts represented logical edges, not alternative support sites for already represented edges. Its local connectivity implementation exploits King's-graph geometry; that implementation should not be presumed valid on Zephyr. |
| [Bian et al., 2014, §§2.2.3–2.2.5](https://www.frontiersin.org/journals/physics/articles/10.3389/fphy.2014.00056/full) | The authors explicitly discuss improving existing embeddings. Their annealing moves add, remove, transfer or exchange physical qubits, with connected chains retained. The score combines distances for missing logical edges with a small penalty on squared chain sizes. Equal-Q rearrangement and endpoint transfer are established local-search ideas; this score does not measure distinct support for satisfied edges. |
| [ATOM, 2023, §III-B and Algorithm 2](https://arxiv.org/html/2307.01843) | Clean shortest paths connect a new chain to existing neighbors. Center selection minimizes summed path lengths, and new path vertices are distributed between chains using logical degrees. This addresses contact routing and chain allocation, rather than an equal-Q endpoint-support potential. [CHARME, v2, §3.1.2, Eq. 9](https://arxiv.org/html/2406.07124v2) learns the next logical vertex, uses ATOM transitions, and rewards qubit-count change plus an exploration term. These explicit formulas do not specify the proposed support histogram. This does not exclude implicit sensitivity to contact geometry in its learned policy. |
| [Bernal et al., 2019 v2, §3.1 Eq. 9, §3.2 and §4.1 Eq. 13](https://arxiv.org/html/1912.08314) | The IP formulation explicitly represents physical couplers witnessing logical edges; the decomposition assigns one physical-edge witness to each logical edge. Total qubit use is an objective, and available embedding edges are mentioned as another representable objective. Therefore explicit edge-witness variables or optimizing additional available edges are not new concepts. The inspected formulation does not aggregate witness endpoints into the proposed directed support histogram. No correctness claim about every printed IP constraint is needed for this observation. |

There is also limited source corroboration for MM: read-only `git show` of the
locally available upstream-labelled release-0.2.22 object
`e27ec28fcf731f7e85df5b107596880202bc703d`, file
`include/find_embedding/chain.hpp`, shows one `links[v]` entry per neighboring
variable and removal by `trim_leaf` when parent/link reference count is zero.
`steal` temporarily drops the shared link, transfers removable vertices, and
restores the link. The source was read as text, never imported or executed.
Remote retrieval of the corresponding pinned header failed during this review;
the independently fetched D-Wave reference above supports the historical
mechanism. This narrow inspection is not a complete audit of pinned MM's scoring
or of the repository's modified fork.
The inspected header bytes have SHA256
`f480e4e59dad116faf33ce586c4ccfaeff97166ad65ae6bff0427a61d1ecdc9f`.

The following deductions are mathematical observations from the definition,
rather than literature claims:

- With all other chains fixed, deleting q from C_u preserves every logical
  contact exactly when, for each neighbor v supported by q, another member of
  S_(u→v) remains. For one-qubit deletion this is s_(u→v) ≥ 2. Nonemptiness and
  connectivity remain separate requirements. Singleton chains inevitably have
  support size one for each incident logical edge, even in an optimal embedding.
- Coupler count is insufficient: edges a–x and a–y give two couplers but one
  supporting endpoint on chain {a,b}. Edges a–x and b–y give the same coupler
  count and two supporting endpoints. Add internal edges a–b and x–y to make
  both two-chain examples valid.
- Fewer single-support obligations need not yield more deletable qubits. Let
  the source be a star with center u and leaves v,w,z. Fix leaf chains {x},{y},
  {t}. The target contains paths a–b–c and d–e–f, with external edges a–x,
  a–y, a–t, d–x, f–y, d–t, f–t and no others. Both center choices {a,b,c}
  and {d,e,f} give valid embeddings with Q=6. Their directed N_1 values are
  respectively 6 and 5, so the proposed potential prefers the second. The
  first can delete c then b, reaching Q=4. In the second, d and f each carry
  a sole obligation, while e is an articulation: no single-qubit deletion
  preserves validity. This fixed small graph is a reasoning counterexample,
  not a Zephyr experiment or a proof against more general reconstruction.
- Only source edges incident to changed chains can change their support sets,
  but **both directions** must be recomputed, including the frozen endpoint.
  Scanning the old/new selected chains' incident target edges with exact
  ownership identifies both sets without scanning entire frozen chains.
  Multiple couplers sharing an endpoint must be deduplicated. This establishes
  an exact local update route, not its runtime advantage.

The narrow distinction worth testing is whether increasing *available distinct
endpoint alternatives* during equal-Q refinement helps subsequent Q reductions,
beyond existing selected-witness bookkeeping and raw coupler redundancy.
Support concentration across logical edges, articulation structure and spatial
separation are omitted information. Any later ablation should retain one fixed
move generator and budgets, measure actual subsequent reductions and charged
overhead, and allow a negative result. Neither the cited work nor this review
establishes that the histogram is new, sufficiently informative, or beneficial
on Zephyr across Ember's graph classes.
