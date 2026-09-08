# B012 hypothesis: rebuild only a blocked local ownership assignment

Pre-code hypothesis, 2026-09-08. B011 recovers one ER insertion but blocks on the next vertex, 66. A response should revise committed ownership only when ordinary insertion fails, rather than paying B004's expensive-insertion repair cost throughout construction. The candidate will release at most one or two placed required neighbors or actual critical-port competitors, rebuild the new vertex and those owners, and freeze every other chain.

Before fixing the pool rule, inspect the saved B011 ER state with exact free-boundary sets and one read-only call of its unchanged preparation helper, under five seconds. Determine whether preparation creates the conflict or the entry already has an unusable required contact. Do not rerun insertion, a constructor, or MM. This diagnostic can establish a local fixed-ownership obstruction, not graph infeasibility.

The concrete release schedule, frozen-state matching/growth contract, bounds and self-critique will be saved below after that inspection and before any response implementation. The fixed cheap falsifier is the saved ER66 state plus a tiny occupied-endpoint reconstruction witness. No larger-cap rescue or outcome-selected pool is allowed.

## Entry evidence and exact proposed policy

The saved ER entry has 64 placed vertices using 218 qubits. New vertex 66 requires placed neighbors 31, 67, 72 and 78. Chain 72 has only free site 1991 on its boundary; that site is also the sole free port of unrelated owners 53 and 55, which still need unplaced original neighbors. Unchanged B011 preparation leaves every chain identical. Assigning a connector through 1991 to either of its two endpoints cannot restore both third owners' frontiers. This excludes the existing fixed-ownership connector operation at this contact, not an embedding after relocation. The free graph otherwise has a component touching all four required chains. Evidence: [entry sets](../../../results/codex/track-b012-reconstruction/attempt001-entry/observations.json), [preparation](../../../results/codex/track-b012-reconstruction/attempt002-prepare/preparation.json). Preparation takes 0.284 s including 184,048 setup units; zero counted query scans does not mean zero work.

Use B011 as the fixed ancestor. Trigger one reconstruction query only when its ordinary **connected insertion returns no candidate**. Never trigger for expensive success, a rejected singleton trial, deadline/global exhaustion or an error. Keep the existing promotion, matching, growth and successful-insertion rules.

Let `R` be every placed original neighbor of the new vertex `v`. Compute distinct free boundaries from the immutable failed-step entry. A critical competitor is an owner outside `R` with an original neighbor still absent after inserting `v`, and sole free boundary site `q` in the union of `R`'s boundaries. Retain the first **two** competitors, ranked by decreasing number of required boundaries containing `q`, then increasing chain size and fixed source tie rank. A required contact is *blocked by these outside owners* when its nonempty boundary consists entirely of sole ports of critical competitors (use all competitors for this test, before truncation). Rank all required neighbors by blocked contacts first, then chain size and source rank; retain the first **four**. The pool is the retained competitors followed by retained required neighbors. There is no source-degree restriction or family metadata. Record full eligible counts and omissions.

Enumerate all one- and two-owner subsets `K` of this at-most-six-owner pool. Order the at-most-21 blocks by `(sum of entry chain sizes, |K|, sorted pool ranks)`. Every block starts from the same entry, privately removing exactly `K`'s whole chains. Insert `v` first; reinsert `K` by decreasing currently placed original-neighbor count, decreasing original degree, then fixed source rank. Return the first complete valid block; do not compare successful outputs or require lower Q.

```text
ordinary = unchanged_connected_insert(v, E)
if ordinary exists: continue the unchanged B011 path
otherwise, within one live bounded repair allowance:
    construct the complete capped pool and ordered block vector
    for K in that fixed vector:
        private = E without K; movable = K union {v}
        freeze every other chain exactly
        for u in [v] followed by the fixed adaptive reinsertion order of K:
            run frozen-aware connected insertion, then existing future growth
            if insertion fails: discard this block
        certify coverage E.keys union {v}, original contacts, connectedness,
            disjointness, target membership, future ports and frozen equality
        if complete and timely: return this block for one atomic main commit
    otherwise preserve E and report the failed construction
```

Frozen preparation cannot grow an outside chain; if its existing rule demands such growth, that block fails. A connector to a frozen endpoint assigns all its new sites to the inserted owner. Cuts between movable owners remain available; pruning changes only movable owners. During private rebuilding, `promoted union K` excludes temporarily released old owners from singleton-domain variables, while their original pending contacts still constrain construction. Global promotion history is untouched. Extra growth retains B011's completed-propagation/covering-matching requirement. **Do not add a new covering-matching condition to ordinary repaired-block acceptance**: B011 may retain a valid base with unresolved future domains, and changing that separately would confound this ownership experiment. Invalidate completed-domain reuse on entry, every private mutation and query exit.

Pool construction, copies, failed blocks, routing, propagation, matching, growth and certification share **1,000,000 repair scans per blocked insertion** and **5,000,000 total repair scans**, included inside the unchanged **20,000,000 global scans**. Keep propagation/matching/growth limits live across all failed blocks; never renew their totals. There are at most 57 insertion calls and 228 ordinary root branches across the 21 blocks, but the shared limits can stop much earlier. Scalar/bitset administration and sorting remain charged to the original absolute deadline. A local repair stop discards its private state; nested matching/growth records retain their partial cost and an explicit repair-interruption status. Completion on the last allowed scan can publish after the final clock check. No late return is a success. Record ordered releases, rebuild order, reasons, Q, work, proposal/certificate/actual-commit distinctions; intermediate growth is not automatically a realized final-Q gain.

## Cheap falsifier and self-critique

Before any constructor screen, use only the saved ER66 entry and this fixed tiny occupied-endpoint witness: source path `0–1–2–3`, target edges `(0,1),(1,2),(2,3),(0,4),(1,5)`, entry `0:[0],2:[1],3:[2]`, new vertex 1. No free component touches both required chains. Releasing source owner 0 allows `1:[0],0:[4]` while owners 2 and 3 remain fixed. A stdlib original-edge check may verify this hand assignment; it does not predict the greedy helper's output. After implementation, call only the local helper once per fixture, with the declared scan limits and a five-second wall allowance, and retain failure. Also check frozen urgent-growth rejection, rollback, nested limits, no repair on ordinary success and domain-reuse invalidation. Failure on both fixed fixtures rejects this policy before a panel; a positive local result only justifies considering the unchanged nine-input screen.

The pool can omit necessary owners, and one/two removals cannot resolve every conflict. Building `v` first may prevent restoration of released chains despite a feasible joint placement. Frozen preparation is deliberately more restrictive than ordinary construction. Failed early blocks can exhaust the allowance, and successful rebuilding can increase final Q or create later dead ends. B004 already falsified frequent immediate-Q-driven rebuilding; blocked-only use avoids that schedule but does not prove affordable runtime. This is conventional local release and rerouting within one evolving constructor, not a novelty or all-class performance claim. The test must demonstrate actual additional reach, then measure final failures, ACL and total cost without selecting a method by input.

The [tiny independent check](../../../results/codex/track-b012-reconstruction/attempt003-hand-witness/witness.json) passes: the hand-proposed full minor uses four sites, outside chains are unchanged, and no free component can supply the original frozen insertion. It executes no candidate. Reproduce in a new output directory with `.venv/codex-native/bin/python -B results/codex/track-b012-reconstruction/check_occupied_endpoint.py OUTPUT`. The fixed greedy reconstruction remains unimplemented and untested at this design checkpoint.
