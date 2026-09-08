# Distinct endpoint support as an equal-size refinement objective

Design and self-critique only. No implementation, constructor, solver, corpus
observation or change to frozen040. The proposal replaces a secondary objective
inside the existing single evolving refinement state. It adds no graph-family
dispatch, restarts, portfolio or parameter search. It is a hypothesis about
future shortening, not a claimed improvement or novelty result.

## What the quantity certifies

Assume simple undirected source/target graphs and a valid embedding with
nonempty, connected, disjoint chains `C_u`. For each directed source edge define

```
S_uv = {q in C_u : some p in C_v is adjacent to q in the target}
s_uv = |S_uv| >= 1.
```

For one qubit `q` in `C_u`, deleting it preserves **all logical-edge contacts**
if and only if every source neighbor `v` supported by `q` has `s_uv >= 2`.
Necessity follows because removing the only supporting endpoint removes that
contact. Sufficiency follows because another endpoint in `C_u` still reaches
each affected neighbor. Other source edges are unchanged. Nonemptiness and
connectivity of `C_u \ {q}` remain separate mandatory conditions. The test alone
does not authorize deleting the only qubit of an isolated chain.

This statement concerns one deletion with all other chains fixed. It does not
compose automatically across qubits or chains. For example, let chains be
`C_u={a,b}`, `C_v={x,y}`, with internal edges `a-b,x-y` and physical contacts
`a-x,b-y`. Both directed support sizes are two. Deleting `a` alone or `y` alone
is valid, but deleting both leaves `{b}` and `{x}` with no contact. A full group
proposal still needs original-edge and connectivity validation.

## A parameter-free potential

Let `N_k(C)` count directed source edges with support size exactly `k`. Compare
valid embeddings by lexicographically minimizing

```
Phi(C) = (Q(C), N_1(C), N_2(C), ..., N_|V(target)|(C)).
```

Any strict qubit reduction takes priority, regardless of its support changes.
At equal Q, fewer support-one edges wins; only on a tie do support-two edges
matter, then support-three, and so on. Exact ties are rejected. Do not add raw
coupler redundancy as an undeclared final tie-breaker or use floating weighted
sums to approximate this ordering. Sparse integer histograms suffice: inspect
the smallest index with a nonzero difference. The fixed number of directed
edges is `2|E(source)|`, so unaffected terms and trailing zero bins cancel.

This is equivalent to lexicographically maximizing the sorted support-size
vector, starting with its smallest entries. It directs attention toward scarce
support rather than rewarding arbitrary additional couplers on already well
supported contacts. The rule has no fitted weights or support cutoff. It does
not assert that the smallest support is the actual obstruction to shortening.

Strict descent prevents cycles of embedding states: at fixed Q the finite
histogram strictly decreases, and Q itself never increases. This supplies no
useful small iteration bound; there can be many distinct histogram values.
Existing pass, group, search-work and deadline limits remain essential.

## Difference from raw coupler redundancy

The current `_contact_redundancy` in
[`contact_repair.py:303`](../../packages/ember-qc/src/ember_qc/algorithms/factored/contact_repair.py#L303)
counts excess actual couplers on incident logical edges. Several couplers may
share one endpoint, so that count need not describe protection against deleting
that endpoint. Support counts retain this distinction.

A fixed small target illustrates a genuine ordering disagreement. The source
is one edge `u-v`. Freeze `C_v={x,y,z}` with internal edges `x-y,y-z`. Candidate
chains for `u` are `{a,b}` and `{c,d}`, with internal edges `a-b,c-d`. The only
inter-chain edges are `a-x,a-y,a-z,c-x,d-y`. Both embeddings have Q=5.
The first has three couplers but support sizes `(1,3)`; the second has two
couplers but sizes `(2,2)`. Raw redundancy prefers the first, while the proposed
potential prefers the second. This distinguishes the objectives; it is not
evidence that the second gives a better final embedding.

There is also a valid mechanism for future shortening. Use source path
`x-a-v-b`, chains `x:[6], a:[0,1], v:[2], b:[3]`, and target edges
`0-1,1-6,0-2,2-3,0-5,1-5,3-5`. Moving `v` from 2 to 5 preserves Q and changes
`s_av` from one to two. Vertex 0 can then be removed from `C_a`, leaving `[1]`
connected to both `[6]` and `[5]`. Raw redundancy also rewards this particular
move; it demonstrates the contact-support mechanism, not an advantage over the
existing secondary objective or reachability under the bounded proposer.

## Exact global comparison from affected edges

Let `K` be the chains changed by a complete group proposal, and
`E_K={uv in E(source) : u in K or v in K}`. Only those undirected edges can
change support. **Both directed supports on each such edge must be counted**,
including the support lying on a frozen neighbor's chain. A selected singleton
can move and change which frozen neighbor qubits touch it even though its own
directed support remains one.

Scanning the selected chains is sufficient. For every physical contact `q-p`
with `q in C_u`, `u in K`, and owner `p=v` a source neighbor, add `q` to the set
for `u→v` and `p` to the set for `v→u`. This recovers the complete endpoint sets
on both sides without scanning all qubits in the frozen chains. Deduplicate
physical endpoints within each directed set; selected-selected contacts may be
encountered twice but must not count twice.

```
incident_support_histogram(chains, selected, owner):
    initialize both directed support sets for every edge in E_K
    for u in selected, in existing deterministic source order:
        for q in chains[u], in existing physical order:
            check the existing absolute deadline
            for p in target_adjacency[q]:
                v = owner(p)
                if v is a source neighbor of u:
                    S[u,v].add(q)
                    S[v,u].add(p)
    reject an absent logical contact rather than treating size zero as quality
    return histogram of all |S[u,v]| for directed edges induced by E_K

compare_equal_size(old, proposal, selected):
    old_hist = incident_support_histogram(old, selected, old_owner)
    new_hist = incident_support_histogram(proposal, selected, proposal_owner)
    delta = new_hist - old_hist
    accept only if the first nonzero delta is negative,
        the complete proposal is valid, and the final deadline check succeeds
```

Because every omitted edge is identical, this comparison equals the global
potential comparison; no whole-graph histogram or global histogram cache is
required. Within one group search, compare against its current best complete
proposal, not merely the original group embedding. All proposals share frozen
outside chains and the same affected edge set.

An incumbent ownership map can be built once per existing group visit and used
with a temporary selected-group overlay: release its old physical sites, then
map proposed sites to their new owners. This avoids an O(Q) owner rebuild for
every proposal and needs no cache maintenance between group visits. Do not use
stale ownership after a commit. A future persistent owner cache would require a
separate, explicit atomic refresh/invalidity contract; it is unnecessary to
establish this objective.

With maximum target degree `Delta`, selected qubit count `Q_K`, and incident
logical-edge count `m_K`, a score scan costs
`O(Delta*Q_K + m_K)` expected time with hash sets and at most that much temporary
endpoint storage. Building ownership costs O(Q) per visit; proposal overlays
cost O(old_Q_K + new_Q_K). These are real costs, not constant-time score updates.
Chain order and vertex labels affect deterministic iteration only, not the
mathematical potential.

## Scheduling, resource accounting and comparison scope

Evaluate support only for complete proposals at the existing acceptance point;
do not rank groups, roots, partial trees or beam prefixes by it. Preserve the
constructor, proposals, region/root limits, group/pass ordering, work ceilings
and original deadline. In particular,
[`round_robin_groups`](../../packages/ember-qc/src/ember_qc/algorithms/factored/contact_groups.py)
continues to exclude groups with no degree-bound excess. This proposal does not
add visits for isolated optimal-size chains or change auxiliary allocation.

An identical *schedule rule* cannot guarantee identical visited groups after an
accepted equal-size move: physical adjacency, later opportunities, accepted-pass
flags and subsequent group construction can change. Additional scoring time can
also displace work at a binding deadline even without a commit. These are the
same distinctions established in the
[allocation review](refinement_work_allocation_review.md). Do not describe the
potential as preserving the entire old search trajectory.

The current redundancy scan builds ownership and counts couplers outside the
`_Budget.pop` expansion counter; changing its score must not silently redefine
that counter or claim this work is free. For an objective-only comparison, retain
the same accounting policy and common deadline, expose ownership/endpoint scans
and score wall time separately, and use the same owner/incident-edge machinery
for the raw-redundancy control. Any change that charges scoring to ordinary
expansions or changes ownership maintenance is a separate implementation change
requiring a normalized control; it cannot masquerade as an unchanged budget.
Finite graph, group and complete-proposal limits bound the scoring work, while
cooperative deadline checks bound cancellation latency between physical scans.

Avoid requiring a secondary score to justify an already valid strict-Q
improvement. Its priority does not depend on that score; a later equal-size
comparison can lazily obtain the new incumbent's histogram. Apply the same
score-evaluation timing policy to the control. Always retain final original-graph
validation and deadline checks, and publish no equal-size proposal from a partial
or interrupted score. Diagnostics must distinguish Q saved, equal-size commits,
and the signed support-histogram delta; a support improvement is not Q saved.

## Self-critique and decisive counterexamples

**Support can improve while deletability worsens.** The literature agent supplied
this hand-checked fixed-target example. The source has center `u` adjacent to
three leaves with frozen chains `{x},{y},{t}`. The target has paths `a-b-c` and
`d-e-f`, external edges `a-x,a-y,a-t,d-x,f-y,d-t,f-t`, and no others.
Both center choices use three qubits, so total Q=6. Choice `{a,b,c}` has `N_1=6`;
choice `{d,e,f}` has `N_1=5,N_2=1` and is preferred. Yet the first deletes `c`
then `b` and reaches Q=4. The second cannot delete `d` or `f` because they alone
support different leaves, and cannot delete articulation `e`. Its immediately
deletable-qubit count is zero. Generic reconstruction might relocate it again;
this is a proxy counterexample, not an impossibility result or a claim about
which candidates the current bounded search actually generates.

**Singleton saturation is structural.** If `|C_u|=1`, every outgoing `s_uv` is
necessarily one in every valid embedding with that chain size. These unavoidable
terms cancel when unchanged; a large `N_1` is not itself a defect that refinement
can remove. Moving that singleton can still change reverse support on a longer
neighbor. On an edge with one singleton endpoint, the other support size equals
the raw coupler count, so the new distinction is mostly how improvements across
edges are prioritized. When both endpoint chains remain singletons, neither
directed term can change. A group that is already at its chain lower bounds is
still omitted by the unchanged schedule.

**Cardinality forgets geometry and joint constraints.** It does not locate
articulations, distinguish short rerouting alternatives, or measure whether
several obligations share a useful removable region. The two-chain example
above also shows why individually safe deletions need not coexist. Favoring one
fewer support-one edge can sacrifice many larger support counts elsewhere;
lexicographic priority is a principled choice, not a theorem that this trade is
beneficial. It can reject a necessary temporary worsening or an equal-histogram
relocation that would enable a later reduction.

**Runtime and novelty remain open.** Maintaining endpoint sets costs more than
incrementing coupler counts, and better-looking equal-size moves can extend
passes or remove later opportunities. This conventional lexicographic local
objective is not by itself a publication-level algorithmic contribution.
The exact deletion condition and affected-edge calculation explain its meaning;
they do not establish prior-art novelty or global quality superiority.

If separately authorized, first compare the local histogram delta against whole
original-target-edge enumeration on tiny valid minors, including frozen reverse
supports, selected-selected edges, duplicate endpoint contacts, simultaneous
deletion and articulation witnesses, ties and deadline interruption. Then freeze
one all-34-input full-pipeline comparison of the same current constructor and
refiner, changing only the normalized equal-Q acceptance potential, seed 0 and
the same 60-second allowance. No per-input selection or seed tuning. Report all
Q/ACL outcomes, validity/timeliness, equal-size commits, scoring cost and displaced
visits. More histogram descent alone is not success; no lower common-success
mean ACL, extra failures, or unacceptable cost is evidence against promotion.
Even a positive development screen would still need repeated seeds, new input
instances and a separate novelty assessment.
