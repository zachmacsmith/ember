# B023 selection: construction with temporary contact loss and overlap

2026-09-08. **Selection record; B022 remains retired.** No implementation, routing, supplied-state query, constructor call or new outcome analysis accompanied this note. The subsequent exact pre-code policy is [b_023_policy.md](b_023_policy.md); it supersedes the provisional full-pass scheduling below with interleaved visits, before any code or observations.

**Hypothesis.** A constructor that can temporarily abandon logical contacts while clearing contested physical sites may escape B022's expensive requirement to rebuild a contact-complete state inside each bounded query. Use one integral collection of connected chains; permit both missing logical contacts and cross-owner overlap during construction. Route missing contacts and erase obstructing branches in alternating passes, without permanent anchors or coupler witnesses. This is a different feasible-state restriction and update policy, not a larger whole-incidence beam.

[B022](b_022_results.md) actually changed dense states: 474 commits included 291 overlap reductions. Nevertheless, it produced only one valid embedding, 31% above MM's Q. Its 107 interrupted queries discarded 230 eligible proposals, but none of those proposals had zero overlap. Of completed scores, 795 overlap reductions were ineligible under its energy rule. These observations establish limited practical construction, publication loss and restrictive acceptance; they do **not** prove that contact preservation caused failure. The proposed observation must test that distinction.

## One concrete mechanism

Let every source vertex have a nonempty connected chain. Maintain exact Q, site multiplicities and missing original-edge indicators:

`M = number of source edges without a physical coupler`,
`O = sum_q max(0, owner_count(q) - 1)`.

Start with distinct singleton sites in the same source/target BFS rank scheme, without B019's initial half-path unions. No initial site remains compulsory. Isolates also have singleton chains. The current state is a minor only when **M=O=0** and independent original-graph validation passes.

```text
normalize once; initialize singleton chains and exact contact/occupancy counts
repeat complete passes under one work allowance and absolute deadline:
    visit missing source edges in fixed seeded order
        route one endpoint tree to the actual boundary of the other tree
        publish the cheaper of the two directed path unions
    visit overlapping sites in fixed seeded physical order
        remove that site from one owner and retain one connected component
        choose the owner/component by the exact resulting penalized cost
        lost logical contacts become pending routing obligations
    increase prices on currently missing edges and overlapping sites
    retain a better-Q map only after M=O=0 and full validation
return the best timely validated map encountered in this one trajectory
```

For routing, the endpoint is a site **adjacent** to the other chain; sharing its site alone is not contact. Nonnegative node-weighted shortest paths may cross other owners. Each union is connected. For erasure, enumerate the components after deleting the contested site; retaining any one preserves connectivity, while explicitly losing its discarded contacts. A singleton requires a replacement singleton rather than an empty chain. Its replacement and tie rules must be fixed before code, not inferred from outcomes. All owners sharing affected sites enter the exact updates.

Use `F = Q + sum_e mu_e * missing_e + sum_q lambda_q * excess_q`, initially unit prices. Prices increase by the observed defect after a completed pass. F ranks alternatives **within** a selected defect repair; it is not a strict descent gate against the old state. Routing must repair its selected missing edge, and erasure must remove its selected contested ownership. Either may worsen other defects. Record signed M/O/Q/F changes, including energy increases. A completed move publishes atomically; interruption discards its private work, not earlier completed moves. The final full validator and all setup, routing, component scans, scoring and bookkeeping share the allowance.

## Distinction, cost and critique

The representation retains connectivity but relinquishes B019–B022's hard contact invariant. Its neighborhood consists of a completed single-contact path or a contact-breaking connected erasure, rather than a contact-complete two-owner reconstruction. Acceptance permits explicitly recorded defect tradeoffs instead of strict energy descent. Cost replaces root pools/beam combinations with at most two shortest-path searches per missing-edge visit and component work at occupied conflicts. Exact affected-site contact counts avoid recounting every original edge for each alternative. Repeated global searches can still dominate; no speed gain is assumed.

This is also distinct from C's tested integral constructors, which kept cross-owner disjointness, and C009's simultaneous finite connected-chain domains/probability messages. Valid minors belong to all these representations: the difference is the allowed intermediate states. B's earlier insertion/release policies returned valid partial minors; they did not publish missing contacts among already represented vertices. Temporary overlap and negotiated routing are conventional ingredients; no novelty claim is made for them or this untested combination.

**Self-critique.** Two singleton owners may repeatedly route through the same narrow corridor, then erase each other's required contacts. Growing prices need not end that cycle. For a sparse graph, long routes between initially distant singleton sites can become an unnecessarily large valid minor even after overlap clears. Permitting contact loss does not by itself supply a good placement process. Conversely, a path source on a path target should be able to move contacts and reach singleton chains; a triangle source on a path must never receive valid credit. Both missing contacts and overlap being allowed enlarges the state space and can make coordination harder. Initialization, representation and acceptance change together, so one screen cannot identify their separate causal contributions.

**Discriminating observation and cheap full-constructor falsifier, proposed for review.** After only targeted connectivity/contact-update, deliberate-contact-loss and rollback checks, run the same nine exposed B inputs, seed0, candidate/fresh MM, twenty seconds and 20M counted units per candidate: eighteen complete calls. Continue only with at least **7/9 timely valid** and Q no larger than MM on at least **three common successes**, including optimal ACL=1 ties. Report the median common solver-time ratio and all-attempt time; a quality pass alone would not establish MM-scale cost. Record whether deliberate contact loss is actually followed by contact restoration and complete validity, how many completed repairs increase F, M/O at pass boundaries, work-limited moves, and routing/erasure/scoring time. Never use reduced M/O, favorable private Q or discarded proposals to compensate for failed complete construction. If contact-breaking moves never contribute to a valid trajectory, this screen does not support the central hypothesis. If complete quality misses the fixed gate, retire this policy without increasing pools, passes or budgets.
