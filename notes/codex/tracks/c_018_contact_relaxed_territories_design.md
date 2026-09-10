# C018 proposal: whole-territory relocation and regrowth

2026-09-10 UTC. **Design only; no implementation, model, constructor or experiment.** Replace C016's prefix constructor without enlarging C017. The disjoint, connected all-owner state with missing source contacts is **reused from C003–C007**, not a new representation. The proposed major change is whole-tree replacement at a freely chosen target root, rather than requiring growth from the owner's current boundary or obtaining a new position by swapping existing region labels. B's latest direction permits temporary owner fragmentation; C retains connected territories. The agents have coordinated that distinction and exchanged relevant earlier failures.

## What changes relative to the earlier C failures

C003 already allowed global region-label swaps and boundary changes; C005 crossed its initial occupied domain through adjacent vacancies. C006 improved initial distinct quotient contacts without improving coverage. C007 already started at Q=n, charged Q before validity, allowed existing contacts to break and used atomic free-path growth. Those facts rule out claiming any of these features as C018's new contribution. C003/C005/C006 retained four sparse successes with poor Q; C007 retained only two, losing grid and planar. These regressions remain rejected.

In C007, all 640 scored atomic paths were accepted, while 3,700/4,340 completed addition visits found no free path: 2,171 had no free boundary at the chosen endpoint and 1,529 exhausted the free-site BFS. Better acceptance of those paths was therefore not the observed bottleneck. C018 releases **all** sites of one owner, chooses any available target site as a fresh root, and builds a new shape against **all** its source neighbors. The new chain need not touch its old chain and no other owner must surrender a region or preserve a donor articulation. This directly tests whether endpoint access, rather than contact-relaxed ownership itself, trapped that earlier search. Old label swaps could make large jumps, but exchanged fixed current shapes among owners; this proposal regenerates geometry in vacant space.

Complementary changes are deliberate: all-incident geometric deficit enters the objective rather than merely breaking ties in exact missing-edge count; paths grow shared branches; the arbitrary `4|H|` visit and sixteen-score caps disappear; and a current-territory-root ablation isolates the proposed new freedom. This is a coherent redesign of the old framework, not a pure one-line causal comparison with C007. Neither more iterations nor a lower missing-edge total can validate it.

## Shared deficit and hypothesis

The selected static A061/MM comparisons locate 22/29 extra grid sites in degree-4 owners, 40/45 extra honeycomb sites in degree-3 owners, and 37/40 extra wheel sites in the rim. MM places more of those owners as singletons sharing several contacts. BA instead benefits from branched chains; its MM map has more branch sites while using fewer qubits. Core/lifted attribution differs across these inputs, so neither another lifting rule nor a path-only representation addresses the common problem. These are observations on selected exposed inputs, not causal proofs.

A066 demonstrates useful coordinated shortening across grid, WS and planar, but leaves other gaps. Its nine final Q values appear by 8.181–17.217 s, with 95.43% of the added-stage time afterwards. B029 improves initial overlap while increasing Q, then succeeds on only 3/9 with poor quality. C017 repairs ER100 locally but proves the fixed ER80/BA neighborhoods infeasible even without quotas. These results support testing a constructor that chooses **compatible contact locations across all owners before declaring a partial contact permanent**. They do not establish that this proposal works.

Hypothesis: releasing an owner's whole chain and proposing a new root beyond its old boundary permits low-degree owners to move into common-neighbor sites and high-degree owners to acquire shared branches. Together with all-incident geometric guidance and actual-Q cost, this should make the first complete embedding compact enough to avoid depending on prolonged later cleanup. A move may destroy an existing source contact when its overall spatial benefit justifies that temporary defect. Contact relaxation itself is not the new hypothesis.

## Concrete representation and first policy

For original source `G` and the actual ideal Z12 adjacency `H`, keep a nonempty connected site set `C[u]` for every source owner, an ownership array, and actual source-contact supports. All sets are disjoint. A spanning tree supports updates; arbitrary branching and extra induced hardware edges are allowed. There is no elimination/fill graph, introduced prefix, fixed outside-owner quota, owner length bound, hardware patch restriction or prescribed embedding template.

Initialize once with the earlier lean singleton policy: a degree-first seeded source BFS forest paired with a seeded target BFS prefix of `|V(G)|` sites. Its exact audited ordering/helper binding must be pinned before code; no previous constructor is called. This initialization is not an improvement claim. It is only an initial state; every target site is subsequently eligible. No family labels, instance identifiers, saved maps, known witnesses, MM or busclique are inputs. If the source has more vertices than available sites, nonempty disjoint ownership is impossible and the call fails explicitly.

For a source edge `uv`, define `g(uv)=max(0,d_H(C[u],C[v])−1)`, using shortest distance on actual target adjacency without excluding other owners. Because territories are disjoint, `g=0` means an actual physical contact. Use

```text
E = Q + sum over original source edges uv of lambda[uv] * g(uv)
Q = sum of chain sizes
```

This distance supplies a geometric search direction, not a certificate that a free route exists. Site occupancy is enforced by proposals and independent validation. A singleton touching several required neighbors gets all those benefits while paying for one site; a new shared branch is charged once by its actual added sites.

Visit owners in seeded sweeps, prioritizing high incident contact deficit with seeded ties and visiting every owner. One visit privately releases its entire territory. Evaluate every available singleton root with incident distance score `S(q)`. Before validity, sample **one** root with probability proportional to `exp(−(S(q)−min S)/R)`, where `R = median(lambda)*max(1,degree(u))`; use stable normalized exponentials. This gives nonlocal roots a proposal probability even when an old, sealed position has the best singleton score. It does not rank actual rebuilt-tree cost exactly. At that root, repeatedly attach the free shortest path with the greatest strict decrease in actual incident `E`, updating all contacts and charging the union of newly owned sites. Paths may attach anywhere on the growing tree and satisfy several neighbors. Only actual couplers and currently available sites are used. If no path has negative energy change, stop growth.

The resulting tree is the **sole proposal** passed to acceptance. The old tree is retained only for computing the signed change and for rollback on rejection/interruption; it does not compete in a minimum-energy proposal selector. Consequently positive-energy completed proposals actually reach the uphill acceptance rule. No independently constructed outputs are combined.

Before the first complete minor, accept every energy decrease or tie and accept an increase with probability `exp(−ΔE/T)`. Initial edge weights are two site-cost units. After a complete sweep, increase each still-missing edge's weight by one; satisfied edges retain their weight. For a first frozen policy, use `T = median(lambda) * (1−elapsed/available_search_time)^2`, with zero-temperature acceptance at expiry; define the empty-edge median as two. These are explicit starting choices for review, not empirically established settings. Record accepted contact losses, later recoveries, Q and every weight update. No hidden local iteration, root-count or path-length cap is introduced.

At first validity, save its time/Q and switch this same state to validity-preserving strict-Q descent. Root choice becomes the deterministic minimum singleton score with fixed seeded ties; regrowth is unchanged. Return when a complete owner sweep changes no chain, or at the existing call deadline. The former is exhaustion of this deterministic proposal policy, not all possible roots/trees or global optimality. This phase deliberately cannot rescue poor construction by prolonged contact-breaking search: poor first-valid quality is evidence against the constructor hypothesis. Preserve the best valid map from this one trajectory for interruption-safe output.

```text
create one injective singleton assignment for all original owners
check initial contact completeness and record initial validity if present
until deadline or terminal valid sweep:
    for every owner in the current deficit-prioritized sweep:
        privately release its connected territory
        sample one available root from full-target incident distance scores
            (deterministic minimum after first validity)
        greedily grow a branching tree by actual free-path energy improvements
        accept using current construction energy/temperature,
            or require validity and smaller Q after first validity
        atomically publish ownership and all affected source contacts
        record first validity and every strict valid-Q improvement
    before validity: raise weights on still-missing contacts
    after validity: return if the full sweep made no change
independently validate the saved complete incumbent, or report failure
```

Actual adjacency is authoritative. Cache a multi-source target-distance array per territory; changing owner `u` invalidates its array, while other arrays remain valid because the metric ignores occupancy. Free-path search uses current occupancy afresh. Compact compiled arrays are the intended implementation. One full distance refresh costs `O(|V(H)|+|E(H)|)`; full root scoring costs `O(degree(u)|V(H)|)`. Growth can require several such traversals and all setup/update time is charged. Zephyr rail/odd/cross couplers may accelerate traversal, but neither a geometric indexing trick nor a drawn crossing establishes an embedding or novelty.

## Distinguishing explanations before any refinement

| Explanation | Discriminating observation |
|---|---|
| Representation | Every actual minor can be represented by these connected disjoint sets, so a valid-map representation exclusion is not claimed. The strict ownership requirement may nevertheless make useful intermediate trajectories inaccessible to cheap moves. Repeated small geometric gaps with no actual free connecting path, even while many unrelated sites are free, would expose spatial obstruction hidden by the distance metric. |
| Move neighborhood | The controlled constructor ablation restricts the fresh root to sites in the owner's old territory, changing no energy, sampling formula, regrowth, acceptance or budget. Record roots outside the old territory, successful regrowth after old-boundary access failure, broken/recovered contacts and multi-contact singleton/shared-branch formation. Better complete outcomes from the full version support releasing the old access restriction. If relocation occurs but the same unresolved edges circulate, that neighborhood is insufficient; if it never occurs, the mechanism was not exercised. |
| Acceptance | Preserve each completed proposal's signed ΔE and each positive-energy acceptance draw. Useful proposed relocations consistently rejected implicate the rule; absence of those proposals implicates root scoring/regrowth instead. Large accepted contact losses without later complete improvement reject the intended tradeoff. These observations do not isolate a universally better temperature or penalty schedule, and no acceptance sweep is implied. |
| Cost | Measure refresh/root-score/path-growth/validation wall, first validity and valid-Q events. Few full sweeps before the deadline implicate computational cost; many completed relocations followed by a flat or invalid trajectory implicate the search. Operation counts remain diagnostics; no lower work cap is justified by this design. |

These observations discriminate operational failures without claiming that one finite experiment proves an entire representation or move class impossible. No local IP, widened exact diagnostic or witness-guided restart is proposed.

## Cheap falsifier and complete-constructor continuation

After one focused tiny correctness check, the falsifier is immediately a **complete-constructor screen**, not another saved-state repair. Use the already generated and independently checked Transfer004 panel, SHA `b54a8ed0af8e35b3901630fddd2892e3735338ad29104913d3332df49eed250d`: old grid128 `g0013`, fresh BA96 `g0302`, fresh SBM96 `g0305`, hidden-singleton-witness control96 `g0307`, and BA relabel `g0309`. Their original source sizes/edges are 128/232, 96/368, 96/284, 96/561 and 96/368; all five graph-file hashes were checked against that panel during this design. Use solver seeds **0 and 1**, with ideal Z12 and 60 s cold allowances, planned host **hyde03**. Run C018, its old-territory-root ablation, **retained A061**, and MM separately with frozen randomized arm order: 40 calls. A066 is exploratory comparison context, not the retained baseline. The ablation is evidence only, never a fallback output. No graph generation, witness inspection, new confirmation exposure or prior-map initialization is needed.

The one tiny check covers the genuinely new risks together: a released whole owner can relocate to a nonadjacent free site; completed uphill proposals reach acceptance; signed Q/contact changes and arbitrary branching are recounted; changed-owner distance caches invalidate correctly; and interruption cannot publish a partial ownership/contact update or credit a missing-contact state. Reuse the original oracle, guard and deadline infrastructure. This is not another search-performance gate followed by repeated local repairs. Exact source/input identities and callable policy details require the ordinary before-run freeze after design review.

Central falsification: if contact-breaking moves occur but the full constructor fails the known-feasible control or remains invalid on two original structures, or obtains validity with uniformly worse Q than the retained algorithm, reject this first policy. If almost no proposed move survives or the clock permits few visits, classify that narrower acceptance/cost result instead of declaring the contact representation disproved. Do not continue because contact distance, edge count or singleton count improved.

A result worth one prompt continuation would be success on all ten input/seed rows, no Q regression against A061 on any row, and at least one-third closure of its positive Q gap to MM on two different original structures, with a complete-outcome benefit over the old-territory-root ablation on at least one of them. Compute gap closure per matched input/seed; do not let a gain on one seed hide its mate's regression. ACL-one ties are optimal. Preserve both seed values, means and sample variances, with the relabel treated as encoding evidence rather than another independent structure. This is an exploratory selection rule, not class-level promotion or a runtime claim.

That result would justify a promptly frozen continuation using remaining Transfer004 ER96/regular96/WS96/planar96/branched-control96 and an existing honeycomb anchor, again with two seeds. Require cross-structure quality benefit, full success and useful first-valid/final-Q trajectories. Keep observed MM time ratios separate; expensive calls must show substantial quality gains and a credible path toward roughly MM's order of magnitude, without inventing a universal 3× cutoff. No dense aggregate can compensate for a sparse regression. Two seeds provide only a fragile initial variability estimate, and untouched confirmation remains separate. No further local repair series is authorized by a promising intermediate statistic.

## Self-critique and scope

Strict disjointness may be too restrictive for inexpensive rearrangement even though it represents every final minor. Whole-owner singleton-root scoring ignores shared-branch cost and current obstacles; greedy path growth can miss a useful pair of paths whose first addition costs energy. The unrestricted root domain does not cure that scoring limitation. Monotonically growing contact penalties may reproduce B029's quality tradeoff, while root sampling and annealing may waste time breaking contacts. The unchanged compact initialization can recreate C007's sealed regions; the whole-owner relocation must demonstrably escape them. Post-validity descent may be too weak. These are serious reasons to test first-valid quality and complete transfer, rather than add mechanisms until one development case succeeds. Territory search, annealing and negotiated routing are established ideas; no publication novelty is claimed for this unimplemented combination.

Grounding: [C003](c_003_results.md), [C005](c_005_results.md), [C006](c_006_results.md), [C007](c_007_results.md) and its [atomic policy](c_atomic_growth_constructor_proposal.md); [A066 complete results](../experiments/066_constructor_results.md), [A trajectories](../experiments/066_initial_trajectories.md), [B029 complete results](b_029_constructor_results.md) and [decision](b_029_causal_decision.md), [C017 rejection](c_017_decision.md), [static maps](c_a061_static_map_results.md), [core/lifted attribution](../strategic_fill_diagnosis_results.md), and [actual Zephyr connectivity](c_zephyr_structural_capability_review.md). The next action is root's design review only.
