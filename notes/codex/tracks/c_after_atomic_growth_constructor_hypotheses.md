# After C007: distinguish misplaced labels from costly ownership rearrangement

C007's equal starts isolate its elementary/atomic comparison, not initialization quality. The path/tree starts miss 119/140 and 99/120 edges. Conversely, all 491 completed atomic label exchanges on the complete input have ΔM=0: permuting labels of a complete source cannot change its missing-contact count for fixed physical regions. Better label placement may help some inputs but cannot solve that geometric deficiency. C001/C002's fixed partitions, C003–C006's fixed occupancy, reserved-access constraints and repeated supplied-state repairs will not be revived.

Two hypotheses follow. **Only the second remains a possible constructor direction, subject to a saved-state mechanism gate.** Joint label assignment is diagnostic only; it must not become a global constructor. Both are design only, with no novelty claim, implementation or calls.

## 1. Joint reassignment of independent source labels

**Hypothesis.** Pairwise swaps can miss a useful permutation of several regions even when current physical geometry already supports the source. A polynomial assignment step could correct this without adding qubits.

```text
Take one supplied assignment; do not construct or evolve an embedding.
Construct a fixed greedy coloring of its source.
For each independent color class S, hold outside owners fixed.
C[u,j] = missing edges from u to outside S if u receives region j.
Find a minimum-cost bijection between labels S and their current regions.
Prefer identity on ties; record whether a strict reduction exists.
Keep every query independent of the supplied assignment.
```

Because S contains no source edge, this matrix gives the **exact** missing-contact objective for the joint reassignment; there is no ignored internal-edge term. Q and region connectivity/disjointness stay unchanged. This uses bipartite assignment, not a global integer program, independent constructor selection or graph-family branch.

**Cheap discriminator, still unexecuted.** Realize a three-label cost matrix `[[1,0,3],[3,1,0],[0,3,1]]` using three independent logical vertices and fixed outside neighbor chains. Identity costs 3; every transposition costs 4; one cyclic reassignment costs 0. This distinguishes a pairwise local minimum from unsupported geometry, without claiming the annealed pairwise method can never escape. It authorizes no constructor or supplied-state assignment call. Clique invariance is decisive: this cannot repair the missing physical quotient contacts on the complete input.

**Self-critique.** Independent sets are small in dense sources and singletons in a clique, so this mechanism cannot be the general answer alone. Computing all contact costs and assignments may exceed its benefit. Reusing a failed growth engine as the other phase also leaves two possible bottlenecks. Therefore this is a diagnostic alternative, not the currently preferred complete algorithm.

## 2. Disjoint ownership with temporarily disconnected chains

**Hypothesis.** Requiring every donor to remain connected after each single ownership change forces expensive preparatory growth or prevents useful interior transfers. Permit temporary fragmentation while retaining exact disjoint ownership and nonempty labels. This differs from B's connected trees with temporary overlap and explicit coupler witnesses.

```text
Start one lean singleton assignment; never overlap physical owners.
Track M = missing original contacts, C = sum(chain_components−1), and Q.
Score E = M + C + Q/(1+d), with the same fixed acceptance temperature.
Permit adjacent ownership transfers/deletions that split a donor.
Choose routing obligations from missing contacts and disconnected owners;
one free-path proposal joins endpoint owners or two components of one owner.
Recount the affected components and all changed contacts exactly.
Only M=C=0 can pass the original minor gate and enter deletion cleanup.
```

The state can express a disconnected donor temporarily; no intermediate is called an embedding. Nonempty/disjoint ownership is mandatory, and failed connectivity obligations remain explicit. The exact component penalty, obligation ordering and work budget would be frozen before code rather than tuned after outcomes.

**Illustration, not the central falsifier.** Use source triangle A–D–B–A and target edges `{0–2,1–2,2–3,2–4,3–4,1–5,3–5}`. Start A={0}, D={1,2,3}, B={4}, with 5 free. Moving site 2 from D to A gives `(M,C,Q): (1,0,5)→(0,1,5)`; adding 5 to D gives `(0,0,6)`. A connected-only sequence also exists—add 5 first, then transfer 2—but its first step increases Q without reducing M. This is not an absolute reachability separation. C007 already accepted 92.6% of positive-energy elementary additions, so avoiding this tiny uphill preparation is weak evidence. The proposed replacement is the [single saved-state transfer discriminator](c_fragmentation_saved_state_discriminator.md), which must establish useful interior transfers and affordable reconnection before any constructor implementation.

**Self-critique.** Fragmentation can accumulate obligations that cannot be reconnected without overlap, so lower M alone may be illusory progress. Exact component updates and free routing add work to an already expensive search. The explicit fixture proves only one reordered dependency; the broader representation may still be poorly placed or inefficient. No extra time, temperature search, fixed-size hierarchy or supplied-state repair sequence is proposed.
