# C019: joint compact star construction, before-code contract

2026-09-10 UTC. **Design for root review only. No implementation, test, candidate call, saved-map solve or launch has occurred.** This resolves the [provisional review](c_019_provisional_joint_star_construction.md). A write/commit race placed its revised version (SHA `16580dc26c130384d51bd3663bc94500fc595081384a7a4bf32e18d0df76ac3b`) in commit `0db593d5`, not the initial draft (SHA `4c7000690dfb36f849031aab5aeec62998fe7f7ea9390ff9534e1cd35f622762`). No exact initial file or retained Python variable was found; that initial draft survives in the conversation, not in the cited commit. A061 remains retained; fixed C018, A067 and B030 remain rejected. This contract defines one evolving constructor and one separately evaluated assignment ablation. Its components are conventional; no novelty or complete-performance claim follows from the design.

## Hypothesis, state and source block

MM's observed multi-contact singletons and shared branches suggest a joint placement deficit shared by grid/WS/control and heterogeneous source neighborhoods. Test whether **constructing a connected center together with several independently assigned singleton neighbors on actual couplers** creates compact contacts before committing long chains. External source-edge obligations remain soft until global validity. Unlike A037/A039, this is construction from Q=n with missing contacts allowed, not shortening an already valid block under hard external contacts. Unlike C018, several incident owners move together and their competition for distinct boundary sites is resolved before publication.

Keep one nonempty, connected, disjoint chain C[v] for every original source owner, with missing source contacts allowed. Chains may branch. There is no source prefix, physical partition, fixed footprint, disconnected owner, overlap, restart, independent completed-constructor choice, family label, witness input, MM/busclique call or global IP.

Use C018's exact normalization and initialization convention: one `random.Random(seed)`; pinned `variable_regions._adjacency` and `_initialize`; pass the same RNG onward, shuffle source ranks then target ranks once. The target start is the midpoint of the computed two-sweep BFS path, not a proved graph center. Supply a wall-only meter; inherited work counters do not stop it. The support source SHA is `696ab4a6882bf33fa48db733facd0517aba2fffbcc0a3445fc389d96df6dfa68`. Reuse helpers only, never its constructor. Empty-source and invalid-input behavior follows the reviewed C018 boundary.

At each sweep start, order all owners by decreasing incident weighted gap sum, then seeded source rank. Freeze that order for the sweep; every owner receives a center visit, including an owner moved as a leaf earlier. For center u, eligible leaves are original neighbors v with **|C[v]|=1 and deg_G(v) <= Delta_H**, where Delta_H is computed from the actual target. Greedily select a maximal independent subset L by increasing source degree, then source rank. This includes k=0 or 1: the same proposal formula then describes a center or pair, with no second constructor invoked.

A long owner cannot be collapsed by a leaf visit. It can shrink or grow when it becomes the center; if it returns to one site, it may later serve as a leaf. The degree test is necessary, not sufficient, for singleton feasibility. Thus the algorithm does not assume every leaf should always fit one site. Its **proposal restriction** is still substantial: multi-leaf coordination may disappear as owners grow. Record that loss explicitly rather than adding larger-leaf repairs after seeing it.

Release all of S={u} union L privately; let F contain their old sites and every globally unoccupied target site. All owners outside S remain fixed during this query. Precompute original-edge obligations outside S without dropping any. No source-family rule changes L, F, ordering or allocation.

## Exact conditional assignment and scoring

Let gap(A,B)=max(0,d_H(A,B)-1), using shortest distance on the actual full target. These distances guide placement; they do not certify free-space routing. Cache each outside owner's full-target distance field by that owner's exact geometry version. Inside one query, outside chains and weights are immutable; no field is refreshed because a private center grows.

Use integer edge weights lambda=2 initially. Define

```text
A_v(q) = sum_[v--w, w outside S] lambda[v,w] * gap({q},C[w])
a_v    = min_[q in F, deg_H(q)>=deg_G(v)] A_v(q)
C_u(T) = sum_[u--w, w outside S] lambda[u,w] * gap(T,C[w])
B(T)   = (actual target neighbors of T intersect F) minus T
D_v(T) = {q in B(T): deg_H(q)>=deg_G(v)}
```

An empty domain for a_v is a completed failure of this singleton-leaf query, not source infeasibility. At a fixed nonempty connected center T, find a **maximum-cardinality, minimum-cost** injective leaf assignment f, with edge cost A_v(q)-a_v. The domains differ only by physical-degree thresholds and are nested; an ascending demand/capacity scan gives the exact maximum cardinality m(T). It supplies a cheap cardinality count, not the costed assignment.

For weighted assignment, use a standard rectangular shortest-augmenting-path/Hungarian routine with k real rows, |B| real columns and k dummy columns. Disallowed real edges are skipped. Every dummy edge has cost P=1+k*Cmax, where Cmax is the largest permitted nonnegative real edge cost (zero if none). This prioritizes maximum real cardinality exactly: changing one dummy dominates the largest possible k-edge cost difference. The remaining objective minimizes real cost. Keep all leaves distinct; do not compress by external-neighbor-set equality because lambda and cost vectors can differ. No global embedding solver is involved.

Rows follow fixed L order; real columns follow seeded target rank, then dummy columns follow leaf order. Augmentation scans those orders, retains the first predecessor at equal reduced distance, and chooses the first equal-distance next column. This specifies deterministic ties. Integer arithmetic must remain exact; an overflow/nonfinite programming condition is ERROR, not a search cap or an infeasibility certificate. k=0 returns the empty assignment with m=0 and no solver work.

For a completed partial assignment define the private score

```text
S(T,f) = (k-m(T), |T|+k+C_u(T)+sum_v a_v
                         +sum_[assigned v] (A_v(f(v))-a_v)).
```

Only m=k supplies a publishable block; then the second component is precisely block Q plus every incident external weighted gap. Every internal selected source edge is a physical center–leaf coupler. Selected leaves have no source edges between them. The old block cost must additionally include its old internal center–leaf gaps; they need not have been zero. Comparing those complete old/new incident costs gives the true change of global E=Q+sum_e lambda[e]*gap(C[e.u],C[e.v]). A partial score is diagnostic, never embedding quality.

## One root and one growth trajectory

This replaces the initial draft's all-root matching/all-successor scoring. There is **one selected root and one selected extension at each step**, with no top-k list, alternative-root retry, old-tree competitor or independent search state. Full-target access is retained. The restriction is an explicit proposal design motivated by query cost; it is not an empirical claim of adequate reach.

For every eligible available root r in F, evaluate T={r} with a cheap proxy. A root is excluded only if its connected component of H[F] has fewer than k+1 sites; that is a necessary size bound. For any T, obtain m(T) from the nested degree domains. For each leaf compute its minimum permitted boundary increment b_v=min_[q in D_v(T)](A_v(q)-a_v), with infinity for an empty domain. Let b_(1)..b_(m) be the m smallest leaf minima. Define

```text
P(T) = (k-m(T), |T|+k+C_u(T)+sum_v a_v+sum_[i=1..m(T)] b_(i)).
```

There are at least m finite b_v. P relaxes competition between different leaves and is a lower bound on the fixed-footprint partial assignment score S; it is **not** a lower bound for every future grown tree or the whole minor optimum. Select the root minimizing P lexicographically, then target rank. Compute its actual costed assignment only after that scan. The old whole center tree is rollback only; it is not included in minimization, so the completed proposal can have positive global Delta E.

For current T, score every q in B(T) by P(T union {q}), then target rank. This adds one actual adjacent site and preserves connectivity, including branching. Select only the best q and compute its actual assignment:

- Before the first covering assignment, retain that selected growth even if its actual score or deficit worsens. Continue until covering, no available boundary, or interruption. A center can consume a formerly assigned leaf site; assignments are private and recomputed. T strictly grows, so there is no internal cycle, arbitrary length ceiling or quota. Finite F is the natural maximum.
- Once covering, retain the selected growth only if it remains covering and strictly lowers the second component of S. Otherwise stop and return the last covering block. Do not try a second extension. This stop means `selected_extension_nonimproving` or `selected_extension_loses_coverage`, not that all actual extensions, paths or block placements were exhausted.

If interrupted, the entire unfinished query supplies no new publication, even if an earlier footprint covered its leaves. A completed unavailable-boundary failure before coverage also supplies none. No BFS escape or bounded exact repair is appended. The first covering center may remain too long, or the one chosen extension may conceal a good alternative; these are falsifiable neighborhood limitations.

## Publication and acceptance

Privately reconstruct ownership by removing all old selected sites before inserting any new selected chain. Recount original selected incident contacts, connectivity, membership, disjointness, exact Q and all affected gaps; unaffected state is unchanged. Refresh geometry versions only for genuinely changed owners. Cache installation happens after atomic state publication, and incomplete cache work is discarded or left invalid. No same-geometry publication counts as movement.

Before first validity, admit a globally valid proposal after complete certification. Otherwise admit Delta E<=0; for positive Delta E use exp(-Delta E/Ttemp), where Ttemp=median(lambda)*max(0,1-elapsed/search_allowance)^2 (use median 2 when there are no source edges). Draw once for each completed geometrically changed, globally invalid proposal in this prevalid branch, including nonpositive Delta E; a nonpositive temperature rejects a positive Delta E. No draw occurs for an unchanged map or for the certified first-valid transition. At a completed still-invalid sweep, increase lambda by one for every currently missing original edge. Never update prices from an interrupted sweep. First validity ends that sweep and begins the validity-preserving phase; prices then freeze.

After first validity, require complete original validity for every publication. Admit strict Q reduction; at equal Q admit only an increase in R=sum_[original edges](actual interchain couplers-1). All other proposals roll back. This known secondary criterion makes quality movement strictly improve (Q,-R); it is not a new contact heuristic claim or unrestricted neutral exploration. An unchanged completed quality sweep terminates this fixed deterministic proposal policy. Since ranks, weights and state then stay fixed, another identical sweep would offer no new proposals. Report policy exhaustion, not neighborhood optimality. Q=n with full validity permits immediate optimal termination.

Every accepted valid proposal, including an equal-Q/R-improving move, completes certification and its deadline check before atomic publication and becomes the **latest certified state** retained for interruption and final output. The first-valid/strict-Q trajectory is a separate record: equal-Q acceptance updates the retained state and its admission receipt without adding a strict-Q event. An interruption before that admission completes leaves the previous certified state intact. The final validator checks the latest certified state, subject to the existing fatal-error and final-deadline rules; it does not revert to the geometry of the last strict-Q event.

```text
normalize and initialize once; create exact all-owner state and caches
certify immediately if the initial state has every original contact
while search time remains:
    freeze fair center order
    for center u:
        select current-singleton independent leaves; release S privately
        build immutable outside-gap costs; scan full F for one proxy root
        follow one connected growth trajectory with actual weighted assignment
        if a complete block returns:
            recount and decide acceptance; certify a valid proposal before publication
            atomically publish; update latest certified state for every valid admission
            record first validity / strict-Q event only when its Q condition is reached
    update missing-edge prices only after a completed invalid sweep
    stop after a completed unchanged valid sweep or a proved Q=n incumbent
return the timely independently validated incumbent, or fully accounted failure
```

Reuse C018's cold time origin, absolute deadline min(start+timeout,supplied deadline), and final reserve min(0.5 s,timeout/10). All support import, array setup, compilation, matching, rejected growth, cache maintenance and validation are charged. Inner compiled loops yield for wall checks; batch sizes control observations, never amount of admissible work. No work-unit, query-count, center-size, root-count, sweep-count, improvement-count or MM-ratio stop is active. On interruption retain only earlier certified incumbents; final original validation must finish before the final deadline. Unexpected runtime errors, including post-incumbent ValueError, remain fatal ERROR with top-level error and no credited embedding. Diagnostics after the deadline cannot create positive credit. Preserve outer kills, missing diagnostics and unknown time as such.

## Reuse boundary and plausible computation

Static review of A039 `connected_star_relocation.py::_maximum_assignment` (lines 291–363) confirms unweighted augmentation and fixed-boundary Hall deficiency. It has no cost optimization or improving alternating-cycle phase. Reuse its distinct-site boundary, private ownership, occupied-site deletion, completed-versus-interrupted and original-edge certificate reasoning. **Do not call it and claim minimum cost.** A peer independently agrees. Its hard-domain compression and auxiliary/work limits also do not transfer unchanged. No shared source or validator needs editing.

Use packed arrays and a compiled weighted assignment kernel. The expensive factors are explicit. Let h=4800, Delta=20, k=|L|, b=|B(T)| and d_out the number of selected external original-edge incidences. Building leaf/center cost vectors costs O(h*d_out) after the needed cached outside distance fields. Root scanning costs O(h*Delta*k), plus small degree histograms and leaf-minimum ranking. Each weighted assignment costs O(k^2*(b+k)); it runs once per chosen footprint, **not at all h roots or all b successors**. Candidate growth proxies use cached best/second boundary costs per leaf plus at most Delta newly exposed neighbors, giving O(b*Delta*k), with a small O(k log k) ranking term per successor. Recompute those caches after each retained growth. All actual boundary updates exclude occupied outside owners and duplicate sites.

The existing measurements constrain expectations:

| Saved measurement | What it supports; what it does not |
| --- | --- |
| C018 full arm: 7.835 s root scoring over 16,856 complete proposals; 20.306 s regrowth; 5.869 s distance refresh, ten calls | Approximately 0.465 ms per existing root/proposal scan on that host. A new scan with k=4 and roughly six old incident terms has around 13 times as many neighbor/leaf terms before cost-vector construction, so millisecond-scale, not microsecond-scale, blocks are plausible. This is an operation-count estimate, not measured C019 speed. |
| A037: 1.146140 s proposal wall including setup, 1,034 root queries, only 25 matched roots and 168 inspected matching edges | Old hard-domain rejection dominates; this cannot calibrate weighted matching throughput. Its 2,048 query limit and 25,000 auxiliary share are rejected as C019 runtime controls. |
| A039: 1.386770 s proposal wall including 0.021549 s setup; 140 started queries, 337 assignment checks and 334 completed maximum assignments | Small connected-block bookkeeping is practical in its measured regime, but 26/34 calls hit the old auxiliary cap. The roughly 9.9 ms amortized proposal/query ratio includes selection/setup and is not a pure matching time or an uncapped guarantee. |

For illustration, k=4,b=20 gives O(384) weighted-assignment loop-scale terms; k=8,b=60 gives O(4352), before constants and allocation. A 96-owner sweep with several-millisecond blocks can plausibly fit within seconds; cold compilation, field refresh, larger degrees and long precoverage growth can dominate. This supports a **bounded implementation test**, not a runtime prediction or a universal gate. It avoids the implausible all-roots-times-all-grown-trees design. If measured work completes only a few blocks within 60 s, retire this allocation or specify one evidenced cost correction; do not extrapolate quality from unmatched partial states.

Timing sources are the existing C018 results/projection and [A037](../experiments/037_results_review.md)/[A039](../experiments/039_results_review.md) reviewed records, including `results/codex/039-results-review/{final-reviewed,reviewed-report-tables}`. No new timing experiment or passive reader was executed for this estimate. B030's 535.510/708.140 s distance-field cost cautions against uncontrolled refreshes; C019's query-local outside fields are static, but multi-owner publications may still invalidate several cached fields.

## Focused falsifier, ablation and continuation

If implementation is later authorized, use **one focused guarded check packet**, not another broad exact campaign: tiny weighted assignments including shared best sites, unequal leaf costs, partial deficiency and deletion of an assigned boundary site compared with direct enumeration; one actual-edge block fixture covering a branching center and a protected long-chain neighbor; atomic interruption and post-incumbent fatal-error cases. Reuse the original oracle and dependency guard. These check only the new weighted objective, leaf-selection invariant and multi-owner publication risks.

The complete screen proposed in the review is unchanged in size: existing Transfer004 g0013/g0302/g0304/g0305/g0307/g0309, seeds 0/1, separate C019, cardinality-only C019, A061 and MM calls, 48 cold 60 s calls with paired timing on the same host. **Root must separately authorize source/check freeze and launch.** Cardinality-only mode uses the same assignment routine and ties with permitted real costs set to zero and dummy cost one; proposal and acceptance scores still use true A_v costs. All other mechanisms are identical. It preserves fixed-footprint covering feasibility; unlike the draft's greedy sequential assignment, it isolates costed placement from avoidable cardinality failure. Both outputs are evaluated separately.

The cheap central falsifier is failure to obtain compact complete embeddings despite substantial completed multi-leaf proposals. Preserve first-valid time/Q, every strict-Q incumbent and terminal time; an evaluator can derive the first time matching A061's final Q from those saved events, without exposing reference Q to a candidate. Record all block sizes and degree/long-chain exclusions, real geometry changes, covering failures versus interruptions, proxy-to-actual assignment cost gaps, selected extension rejections, actual Delta Q/M/E/R and phase wall/CPU. Do not save only accepted operations. These observations distinguish:

- **Representation:** eligible singleton leaves disappear as chains grow, so construction falls back structurally to k=0/1 blocks; or fixed footprints have insufficient distinct eligible sites. This does not prove that larger-leaf stars work.
- **Neighborhood:** many completed blocks, small proxy-to-assignment gaps and consistently poor complete quality challenge the chosen star/root/growth reach; large gaps implicate the competition-blind root/extension proxy. Neither is a global impossibility result.
- **Acceptance:** useful actually constructed blocks rejected by their exact global tradeoffs identify a possible admission restriction; rejected intermediate metrics alone do not establish an improving complete path.
- **Cost:** few completed blocks or repeated interruptions in a measured phase distinguish insufficient practical coverage from many completed unsuccessful proposals. A larger timeout is a new policy because prevalid temperature uses elapsed fraction.

Continue the **fixed policy** only with 12/12 timely valid outputs, no row-wise final Q regression against A061, and substantial final gains in both seeds on two original structures: one grid/WS/control and one BA/SBM. On each qualifying matched seed close at least one-third of a positive A061-to-MM Q gap; if that reference gap is nonpositive, improve A061 instead. Optimal ACL-1 ties remain allowed. First-valid Q is diagnostic, not a gate: prompt strong final gains after a larger first map remain useful. A weighted-assignment contribution additionally requires complete gains over the cardinality-only arm on a qualifying structure in both seeds; tied strong outcomes support assessing the simpler fixed policy, never a portfolio. Report every relabel regression, class status/ACL/variance and full-attempt time separately. Two seeds provide fragile exploratory variance, not a class-population claim.

Failure rejects this fixed policy; a specific mechanism can receive a separately bounded follow-up when complete evidence distinguishes its cause. No follow-up is automatic. Self-critique remains that proxy root choice, singleton-leaf attrition, myopic postcoverage growth and potentially large distance costs may defeat the new coordination capability. The required evidence is end-to-end multi-structure gap closure with a plausible measured path toward MM's runtime scale. C018-neutral repairs, more local exact solves or better intermediate contact scores alone cannot satisfy it.
