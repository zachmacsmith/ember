# B021: separate frozen incidence from routing failure

Design only, following [B020's complete failure](b_020_results.md). No implementation, solver or new reconstruction call accompanies this note.

## What the saved dense queries establish

The first K40 paired query changes edges `(20,31),(31,37)`. Its selected chains are `20:{4384,1018}`, `31:{4384,1053,4253}`, `37:{4384,1053,4229}`. Every site remains an endpoint of an **unchanged** witness: owner20 uses edges0–20/1–20; owners31 and37 use their edges to0,2,21. Therefore every selected membership is compulsory. With outside chains fixed, neither Q nor O nor fixed-price energy can decrease, regardless of routing or pool size. Its sixteen completed combinations have unchanged O49 and Q89 or90. The first K100 paired query, on owners14/46/52, has the same complete retained-site lock; its completed proposals have O169–171, never lower than entry169. These are hand-checkable first-query certificates from the saved initial witnesses, not a claim that every dense query is locked.

This explains why completing a query need not test useful relocation. B020 separately establishes expensive pool construction, but no query discarded all its completed eligible proposals. Neither dense paired run committed a move or completed a price-update sweep. Energy ties reject their unchanged states; accepting a geometrically identical state would not remove the compulsory endpoints.

**Cheap next observation, proposed before code:** classify all 497 recorded query scopes in those two unchanged paired states; no target search or candidate call. Cache the incident endpoint multiplicities once. For selected owners A and changed edges F, let T_u be endpoints of all incident witnesses outside F. At site q, let b_q count unchanged outside owners plus selected owners with q in T_u. Then

`O_min >= sum_q max(0,b_q-1)`;

`E_min >= Q_outside + sum_u max(1,|T_u|) + sum_q lambda(q) max(0,b_q-1)`.

These are lower bounds, not connectivity/attainability claims. If the first equals entry O, overlap reduction is impossible in that scope. If the second reaches entry E, strict energy improvement is impossible. Report both certificates, all compulsory-site sets, saved completed proposal scores, and interrupted stages separately. For a query lacking either certificate, failure remains unexplained: an absent improving proposal can reflect the finite pool or greedy tree builder. A scored overlap reduction rejected by energy would instead directly identify an acceptance restriction. Stop at two seconds/500k owner-endpoint/site operations including setup and decoding wall; retain unknown prefixes. This tests locking before spending another routing budget.

## Two update principles, only one worth considering further

**Whole-vertex contact-domain rerouting** replaces one complete chain and chooses every incident contact anywhere on the frozen neighbor chains. It removes mandatory old endpoints, but is essentially the fixed-neighbor connected-tree reconstruction already used by B001, with overlap now permitted privately. B001's sparse quality losses show why renaming that primitive is insufficient. It is a useful causal control, not a fresh competitive proposal; weighted chain rerouting is established [CMR](https://arxiv.org/html/1406.2741) prior art.

**Joint whole-incidence block reconstruction** is the stronger hypothesis: select two owners sharing congestion, release both complete branch sets and **all** incident contact bindings, then grow their replacement trees together. Every contact to a frozen neighbor is a set-valued obligation, and their internal source edge is also free to choose its coupler. Recorded witnesses certify the eventual choice; they do not fix retained terminals. This differs from B020's two-edge release and B004/B012's sequential first-new-vertex rebuilding of a disjoint partial minor. It also avoids C's partition of free target space. It remains conventional group routing in broad outline, not a novelty claim.

```
maintain one full-source connected/contact-valid state, allowing overlap privately
visit each owner once per sweep, ordered by current conflict then seeded rank
choose one co-owner sharing its largest conflict, with seeded ties
remove the two complete trees and their incident bindings in a private block
grow two connected partial trees together; retain at most four joint states
    each obligation chooses contact sites from the current neighbor boundary
    allow both selected trees to grow before fixing their mutual contact
certify all incident original edges; score actual Q/O at fixed prices
commit one complete improving block; otherwise roll back
```

Retain the 20M-work/60s global ceiling, bounded state/route expansion and at most eight owner sweeps; no Cartesian enumeration over all incident edges. Exact pool/root/branch rules would need a subsequent short pre-code policy. The hypothesis is removal of correlated obligatory endpoints through joint chain placement, not a wider edge pool. Whole-block copying, boundary scans and failed partial states must all count. High degree can still exhaust a visit; there is no MM-scale runtime claim yet.

**Critique and falsifier.** Freezing outside chains can still make the cavity infeasible; coordinating two owners can miss a required third, and strict energy may refuse useful growth. The earlier distance-tree and reinsertion failures warn that a beam can spend coverage without improving final output. First confirm whether incidence locking is prevalent with the cheap saved classifier. If not, this proposed mechanism loses its current evidential basis.

A fixed positive joint witness uses source path `X–u–v–Y`, target edges `a–b,x–b,y–b,x–c,c–d,d–y`, and chains `CX={x},Cu={a,b},Cv={b},CY={y}`. Initial witnesses are `(x,b),(a,b),(b,y)`, Q5/O1/E6 at lambda=1. Hold X/Y fixed. Joint replacement `Cu={c},Cv={d}` gives Q4/O0/E4. No single-owner strict-energy improvement exists: u has no singleton contacting both frozen x and v's b; every connected overlap-free u alternative lies in `{a,c,d}`, whose components cannot contact both. A replacement retaining overlap needs at least two sites, hence E≥6. For v, no overlap-free singleton contacts both u's `{a,b}` and y; its old singleton b has E6, and two sites already cost E≥6 even without overlap. Thus a joint move crosses an actual fixed-price acceptance barrier. This hand-derived witness establishes neither convergence after changing prices nor a need for joint moves on B9. Triangle-on-path is the negative full-minor case. Any later implementation must promptly face complete constructors and a diverse fixed screen; local overlap gains alone cannot revive the retired policies.
