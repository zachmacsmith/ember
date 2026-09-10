# Provisional C design review: joint compact star construction

2026-09-10 UTC. **Design only; root requested a bounded exact contract after reviewing the initial recommendation to withhold implementation. No implementation or screen is authorized by this note.** A067 completes all twelve calls but regresses on regular96 against A065/A066 and retains WS/control deficits; A's score/pair sequence is stopped. B030 and its connected ablation both fail all twelve calls, and B's provisional hierarchy replacement is also not selected. A061 remains retained. Root correctly distinguishes an unproved hypothesis from an incoherent one: temporarily fixed outside chains alone do not invalidate an exploratory constructor. The [before-code contract](c_019_joint_star_contract.md) now specifies one root/growth trajectory and a restricted, explicit use of singleton leaves. This is not a C018 neutral-move refinement.

## Hypothesis and changed assumption

C018 establishes that unconstrained owner relocation can complete all four tested structures, but its first-valid Q570–868 and ten final regressions show that choosing one root against fixed neighboring chains does not yield compact placement. Earlier A061/MM maps locate most grid/honeycomb/wheel surplus in low-degree owners, while BA needs shared branches. A single physical site can satisfy several contacts cheaply only when its neighboring owners occupy compatible sites. B030's ability to move fragments has not supplied a complete alternative.

**Hypothesis:** jointly placing a center and an induced independent set of its neighbors on actual Zephyr couplers, from the first construction sweeps, can create those compact arrangements before individual contact locations become expensive commitments. A branching center and a costed assignment of neighboring singletons should serve both local low-degree structure and heterogeneous neighborhoods. The change is the *unit of construction and the jointly evaluated physical placement*: several adjacent owners are regenerated together, not individually moved according to distances to their current chains.

Maintain one nonempty, disjoint, connected territory per original owner, allowing missing source contacts before validity. Start once at Q=n using the existing source/target BFS singleton initialization. All target sites remain eligible and every owner is eventually a center. No source-family label, fixed hardware footprint, private witness, earlier complete constructor, MM/busclique call, restart selection or global IP enters this state.

The contract narrows leaf selection to **currently singleton** original neighbors with source degree at most the actual target maximum. Choose a deterministic maximal independent subset L by increasing source degree, then seeded source rank. Maximal does not mean maximum. An owner with a longer chain is never collapsed by serving as a leaf; every owner still receives center visits and may grow an arbitrary connected chain. A center that later returns to one site can become a leaf again. This preserves general branch-set representation while explicitly restricting the joint proposal; it may lose joint reach as more chains grow. Release the center and selected singleton sites privately. Other chains remain fixed for that proposal, not for the whole construction.

For a **specified connected center tree T**, assign each leaf v to a distinct free site f(v) in the actual target boundary of T. With leaves independent, all leaf–outside terms are separable. Minimum-cost bipartite matching therefore gives the best leaf assignment for this T under

```text
block cost(T,f) = |T| + |L|
  + sum over u--w outside block: lambda[u,w] * gap(T,C[w])
  + sum over v in L, v--w outside block:
        lambda[v,w] * gap({f(v)},C[w])
gap(A,B) = max(0, actual_target_distance(A,B)-1)
```

Internal star contacts are actual couplers and cost no missing-edge penalty. The formula is exact for the specified tree/assignment and frozen outside state; it is **not** an exact minimum minor or minimum center tree. An incomplete matching cannot publish missing owners. Matching is a conventional polynomial subroutine, not a global embedding IP. Use actual adjacency even when Zephyr coordinates accelerate boundary enumeration.

## Coherent provisional construction

The contract replaces this draft's potentially expensive all-root matching with one full-target optimistic root scan, followed by actual weighted boundary matching and one greedy connected growth trajectory. Root scores ignore competition between leaves, so their optimism remains a stated limitation; matching resolves that competition for the selected center footprint. Where matching is incomplete, retain its deficiency as a private signal and grow before publication. After an extension, recompute the joint assignment; an assigned leaf site can become a center site only if the completed proposal gives every leaf a new distinct site. Charge the occupied union and every affected original-edge gap. Do not sum independently routed arms or retain a leaf position solely because it was chosen first.

The exact contract uses single-site center extensions, jointly reassigning leaves after each selected extension. It specifies root/growth proxy scores, actual proposal scores, stable ties, construction acceptance and validity-preserving quality acceptance. No independent completed algorithm, top-k root pool or root/tree exhaustiveness is implied. This restriction buys a plausible polynomial query cost; it can miss a useful second-ranked extension or a non-improving bridge after the first covering assignment.

```text
initialize one all-owner singleton state; record initial defects
while the common construction allowance remains:
    visit every owner as a center in a frozen fair order
    choose its induced independent neighbor set; privately release that block
    evaluate actual center/leaf placements, growing a branching center as needed
        after each proposed extension, reassign leaves by boundary matching
        charge actual block Q and all incident original-edge gap changes
    if a complete private block exists:
        apply the frozen construction acceptance rule and publish atomically
    on full original validity, certify and retain the complete incumbent
    record first-valid Q/time and every later strict-Q incumbent
return a timely independently validated incumbent, or a complete failure record
```

The contract fixes global contact prices and a rule permitting nonmonotone working-state moves before validity; the old map is rollback only, so uphill proposals are reachable. After validity, the same joint block proposal accepts strict Q reduction or equal Q with more actual incident source-edge couplers. Changing several owners together may cross a plateau without accepting its intermediate states, but that benefit is unproved.

## Prior work this must not rebrand

| Prior direction | What is reused; what must change |
| --- | --- |
| C001/C002 coarse-region splitting; C003–C007 territories | Connected disjoint sets and contact relaxation already existed. No source hierarchy, target coarsening, fixed parent boundary, full-target occupancy or vacancy-only relocation is proposed. |
| C009 domain probabilities; C010–C017 clone/contact-domain constructors | No probabilistic domain ensemble or committed source prefix with future quotas. Matching describes one concrete private block; all original owners already exist and external contacts may change before validity. |
| C018 whole-owner regrowth | Full-target access and connected branching are retained capabilities. Replace one-owner placement against fixed neighbors with joint actual star geometry at construction time. This is not a new name for neutral cleanup. |
| B018–B022 explicit contact selection; B026–B029 tree reconstruction | There is no permanently selected coupler or merely trimmed neighbor boundary during the block query: center and leaf ownership are regenerated together. Exact fixed-tree matching does not remove the risk that remaining outside chains are badly placed. |
| B024 placement permutation; B030 fragment transport | Do not optimize only a fixed initial footprint's pairwise distance sum, or create disconnected contact-bearing fragments whose later merge cost is deferred. Here the selected block is connected owner-by-owner at publication and its actual Q is charged immediately. B030's failure is not evidence against all joint placement. |
| A037 singleton matching stars; A039 connected-center matching | The induced-star matching reduction and joint-owner shortening are already implemented/studied. A037's total gain was only seven Q across 34 structures, with regressions preserved. The proposed distinction is soft external obligations during **construction**, branching center growth coupled to reassignment, and evaluation of first-valid compactness. Reusing matching or moving its call earlier is not itself a novelty claim. |

The existing [literature review](../literature_review.md) covers CMR/MM all-neighbor rebuilding, Bian placement/Steiner routing, ATOM insertion and PSSA ownership moves; the [matching-star review](../induced_star_relocation_review.md) establishes close matching prior art. No fresh literature sweep was performed. Publication novelty would require a demonstrable new construction mechanism and later focused comparison, not these component names.

## Distinguishing explanations and self-critique

- **Representation:** final minors still use arbitrary connected disjoint chains, but only current singletons may be leaves. Count degree/length exclusions and joint block sizes: disappearance of multi-leaf blocks before validity would expose loss of joint reach, not a proof that larger leaves cannot work. A missing covering assignment concerns this footprint and local restriction, not global infeasibility.
- **Neighborhood:** the contract's ablation uses deterministic maximum-cardinality assignment without the soft cost, preserving fixed-footprint covering feasibility. More useful actual joint changes and better complete quality would support costed coordination. First-valid quality is a mechanism diagnostic; a larger first valid map followed promptly by strong final gains can still satisfy the user objective.
- **Acceptance:** retain completed block costs, changed-owner sets and admitted/rejected defect/Q changes. No compact proposal generated implicates root/tree construction; compact proposals consistently rejected implicate admission. Both must be distinguished from geometrically identical publications. A counterfactual successful trajectory cannot be inferred from a rejected move alone.
- **Cost:** all-root matching, repeated center growth and distance refresh may dominate. Record completed centers, roots, matchings, full blocks and the time to first validity. Few completed blocks before the wall boundary leave reach unresolved but demonstrate impractical allocation; many blocks without compact validity reject the practical mechanism. Counters remain diagnostic. Any active limit must follow measured cost and a separately frozen design, not appear as an unexplained cap.

The central risk is substantial: exact leaf assignment for one tree does not solve global layout, and successive stars may undo one another's useful external contacts. Singleton leaves may be the wrong local representation for heterogeneous sources. Growing a center to fit many leaves can recreate C014's capacity-driven length inflation. Exhaustive root matching could be too expensive at MM scale; evaluating only a proxy-selected root could recreate C018's proposal defect. These are design questions to resolve before code, not reasons to run a succession of local exact diagnostics. Allocation should be withheld if the before-code contract cannot express a plausible measured-cost implementation of the joint placement.

## Cheap complete-constructor falsifier and continuation

If subsequently authorized, use the contract's focused check packet and a direct small complete screen on existing Transfer004 grid128 g0013, BA96 g0302, WS96 g0304, SBM96 g0305, singleton control96 g0307 and BA relabel g0309, seeds 0/1. Candidate, its cardinality-only assignment ablation, retained A061 and MM run separately on the same host within each pair: 48 cold 60 s calls. This is a proposed matrix, not launch authorization. No new inputs, private-witness access or output selection. Freeze all identities and reuse the audited harness and original oracle.

Reject the fixed policy against the continuation criterion below if it fails that criterion, preserving every failure and regression. A mechanism may receive one separately specified bounded follow-up only when complete results support a distinguishing explanation; local savings or interruption alone cannot promote it. If the two assignment modes tie on strong complete quality, the weighted-assignment claim is unsupported and the simpler fixed policy can be assessed separately. Never combine their outputs.

A continuation worth considering must have **12/12 timely valid final outputs, no row-wise final Q regression against A061, and substantial final gains on two distinct original structures in both seeds**, including one of grid/WS/control and one of BA/SBM. On those structures require at least one-third closure of a positive A061-to-MM Q gap at each matched seed; where A061 already ties or beats MM, require improvement over A061 instead of dividing by a nonpositive gap. First-valid Q below A061's final Q is **not a mandatory gate**. Use first-valid, first-A061-match and incumbent-Q trajectories to distinguish compact construction from prompt effective cleanup and from expensive stalled refinement. Relabels count once structurally and cannot hide regressions. ACL-1 optimal ties remain allowed. Attribute weighted assignment only if its complete outcome improves over the cardinality-only ablation on a qualifying structure in both seeds.

Report every status, mean ACL, two-seed sample variance, within-chain variance and all-attempt wall/CPU/process cost. Strong final quality and its time trajectory must support MM's order-of-magnitude runtime aim; no aggregate dense gain or universal multiplier decides allocation. A 59 s result on a subsecond-MM input remains a material runtime deficit even when valid. No confirmation-set, Pegasus/Chimera or paper claim follows from this exploratory screen.

## Initial critique and revised allocation status

The first review recommended withholding implementation because all-root matching/growth cost and global coordination were unresolved. Root requested a bounded contract rather than treating those uncertainties as a veto before an informative test. The concrete distinction is joint creation of actual center–leaf contacts with paid center length and leaf assignment before publication; A037/A039 instead enforce already valid hard external contacts. This is sufficient for contract work, without a prior complete-performance proof. The remaining proxy-selected root and fixed-outside risks are real and explicitly falsifiable, not resolved by terminology.

Root's completed B diagnosis strengthens this judgment: 507 accepted patches reduce aggregate M by 251 while adding 473 units of component debt; 613 accepted merges reduce M by 301 while adding 1,747 Q. No M=0 state is observed; minimum M is 67. Distance fields consume 535.510 of 708.140 solver seconds and interrupt 22/24 native calls. These are root-reported complete records, not a new analysis here. They reject the explanation that fragmentation was simply unused or only needed one final merge, and give no basis for an acceleration-only continuation. This draft's repeated boundary/assignment queries could incur the same expensive coordination failure even while every local cost is exact.

The useful retained design fact is conditional: a connected center and independent leaves admit an exact additive assignment cost against the temporarily fixed outside. The contract tests whether repeatedly generating these actual compact contacts before long commitments is a useful general construction mechanism. It is not a claim of class-spanning performance or novelty. Another local score, broader neutral acceptance or a larger exact campaign alone would not settle the question.

The original draft SHA was `4c7000690dfb36f849031aab5aeec62998fe7f7ea9390ff9534e1cd35f622762`. This revision incorporates root's two critiques and completed A/B outcomes; no result artifact or earlier policy rejection changes. **Next action is root review of the exact contract. No implementation, matching benchmark, saved-map exact campaign or 48-call launch follows automatically.**
