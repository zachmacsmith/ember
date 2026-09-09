# B024 proposed discriminator: jointly place source vertices on the same sites

**Design only; no implementation or calls.** [B023](b_023_results.md) validates temporary contact loss/restoration as a usable transition, but its four sparse successes still use 2.04–3.26× MM Q after cleanup. Only one action was interrupted; all completed route/erasure actions committed. The evidence supports examining placement and growth quality, not another publication-cap rescue.

**Hypothesis.** Jointly coordinating the initial source-to-site bijection can avoid creating long routes that later erasure and leaf pruning cannot adequately shorten. Keep **exactly B023's initial set of n target sites**. Change only their assignment to source vertices; preserve routing, erasure, prices, edge/physical order, forced acceptance, cleanup and all limits. This controls physical scale. It is an initialization experiment, not a new claim that a distance objective equals final ACL.

For initial sites S, compute exact shortest-path distances `D(x,y)` in the **full target graph**, with BFS from each x in S stopping when every site in S has been reached. Define the integer placement cost `C(pi)=sum_(u,v in E(G)) D(pi(u),pi(v))`. Starting from B023's bijection, make **two source-ID-ordered passes over every unordered source pair**. Immediately exchange their assigned sites only when the exact global C decreases strictly. Ties retain the current assignment. Delta calculation uses incident source edges, with the pair's own edge unchanged and shared-neighbor terms cancelling. No additional random draws or independent starts.

```text
perform B023's unchanged normalization/BFS singleton initialization
compute full-target distances between those same n sites
for two fixed passes over all source pairs (u,v):
    compute exact change in C under their simultaneous site exchange
    if negative, update this one evolving bijection
publish the completed bijection and rebuild its contact counts
run B023's unchanged interleaved routing/erasure and final gate
```

This is a bounded coupled placement heuristic, not an exact quadratic-assignment solve. C already tested whole-chain pair swaps using missing-contact changes during construction; this proposal does not claim that pair swaps themselves are new. Its controlled question is whether globally considering **target distance before growth**, on the identical initial footprint, changes complete B023 outcomes. It does not duplicate C's finite connected-chain domains/messages or its earlier independent-set assignment diagnostic.

**Cost and interruption.** All BFS node/adjacency scans, pair/incident-edge evaluations and publication count inside the same 20M/20s allowance; B023's final reserve remains intact. Distance storage is O(n²); worst-case BFS work is O(n(|V(H)|+|E(H)|)), and two complete pair passes cost O(n²+n|E(G)|). Early BFS stopping preserves exact distances. Partial preparation must not launch a fresh constructor budget or publish a selectively favorable prefix; record interruption and stop. No placement-only numerical gain receives embedding credit.

**Self-critique.** Distance ignores competition between routes and same-owner path sharing. Initial sites can be intrinsically unsuitable even under their best permutation. Pair descent may miss useful longer permutations. For a complete source, every bijection has the same distance sum, so this stage cannot help its geometry. B023 may later erase the initial assignment, or stop at an unnecessarily large first feasible map. A failed screen will not identify these causes uniquely.

**Cheap falsifier, proposed for review.** Check a fixed four-vertex path whose scrambled assignment `[0,2,1,3]` on a target path has C=5 and admits a C=3 singleton embedding; check complete-source permutation invariance and interrupted preparation. Then one B9 screen: this initializer plus unchanged B023, contemporaneous B023 control, and fresh MM, seed0/20s, **27 complete calls** on one host. Require the existing >=7/9 validity and >=3 common Q-win/tie gate; no larger pass, price or routing allowance. Initial C/M, accepted swaps, setup cost, routing work, first-feasible/final Q and retained initial sites are sufficient observations. Lower C followed by lower Q on several sparse inputs supports coordinated placement; lower C without Q improvement shows this proxy/footprint/repair combination is insufficient. No swaps leaves heuristic reach or footprint quality unresolved. Setup exhausting the allowance is a cost failure. None of these permits a family selector, partial-Q success claim or automatic follow-up tuning.
