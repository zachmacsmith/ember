# C016 before-code contract: publish admissible births

2026-09-09. **Proposal only; no implementation or execution.** Root requested this bounded follow-up after reviewing C015's complete failure. C015 remains rejected at 0/8 versus A061/MM 8/8. This contract changes one acceptance/computation policy in one evolving embedding, with no portfolio, MM/busclique calls, witness initialization, source-family labels or instance-specific choices.

Hypothesis: C015 spends most of its allowance reconstructing earlier chains after a valid ordinary birth because a pending singleton domain becomes empty. With connected multi-site births available, that event is a quality indicator rather than proof of infeasibility. Publishing the valid ordinary birth promptly, reserving coordinated retraction for actual constrained-placement failure, will recover complete construction on several persistent deficits within the existing global allowance. The hypothesis concerns computation allocation and publication; it does not assert that the resulting embeddings beat MM in ACL.

Measured motivation: 242/243 C015 transactions began with an ordinary proposal available; 181 completed private results were discarded, consuming 311.708 seconds of nested placement wall. Six terminal transactions left an ordinary birth unpublished. However, ER100 has a genuine completed ordinary failure and planar an interrupted one. These preserve a concrete possibility of later route, quota or computational obstruction even after proactive rebuilding is removed. See [C015 result](c_015_results.md) and [causal attribution](c_015_causal_review.md).

## Mechanism and pseudocode

Retain C015's root domain and ranking, first-admissible selection, one-label quota-aware paths, exact scratch consumption checks, capacity growth/pruning, hard old/new quota rules, source-order rule, inherited scoring, and retraction/expansion mechanics. Earlier choices can still move during a single private reconstruction after a failed birth. Changing the published history can change later source order under the same source-order rule; it must not be described as an identical trajectory.

```text
state := empty certified embedding
while some source vertices are pending:
    v := unchanged source-selection rule(state)
    ordinary := unchanged constrained PLACE(state, v)
    record its success, failure or interruption and singleton-domain changes
    if ordinary exists:
        chosen := ordinary
    else:  # completed placement failure, never a deadline interruption
        chosen := unchanged coordinated transaction(state, v, ordinary=None,
                                                    ordinary_failure=recorded failure)
    if chosen does not exist: stop with construction obstruction
    certify contacts, connectivity, disjointness and all quotas
    check global deadline and exact net-one introduced-set change
    publish chosen atomically as the single evolving state
apply unchanged complete-private recovery and final validation/output rules
```

There is no new time cap, work cap, per-owner allowance, top-K limit, postprocessor, routing variant or independent constructor. Preserve the existing 60-second complete-call allocation and 0.5-second final reserve; account for all initialization, instrumentation, validation, serialization and failure time. Existing counters remain diagnostic. No selection among complete algorithms' outputs is permitted. MM runs separately as the paired comparator.

Keep C015/C014 source immutable. A new isolated candidate module may reuse their unchanged state, placement and transaction helpers, while implementing this publication rule explicitly; do not mutate imported module globals or monkeypatch production helpers. Record the new source and check hashes before any complete screen. No shared correctness-infrastructure change is needed.

## Specific checks and cheap falsifier

Reuse the audited harness and original oracle. Add only focused checks for the new transition risks: (1) an admissible ordinary birth that empties a singleton domain is published with exactly its proposed chains and no transaction call; (2) an actual completed ordinary failure still enters coordinated reconstruction and either publishes a valid net-one result or records obstruction; (3) an interruption never masquerades as failure or exposes a partially published state, including interruption during the publication certificate. Use existing small state fixtures and controlled deadline/failure injection where needed; validate returned fixture minors and quotas with existing infrastructure. Preserve every check attempt. The established routing/capacity checks need not be repeated exhaustively.

If these checks pass, go directly to a frozen **eight-input complete-constructor screen**, with the same ideal Z12 encodings g0001, g0101, g0102, g0004, g0013, g0017, g0202 and g0203 from Transfer003; seed 0, 60 seconds. Run C016, retained A061 and pinned MM independently on the same host under existing dependency isolation and complete failure/time accounting. Root owns descriptor/snapshot and execution review. This contract does not itself authorize a launch.

The cheap falsifier is end-to-end: if completion still fails on the three diagnosed ER/BA inputs, the three prior C014 successes are not retained, or neither fresh input completes, reject this fixed C016 policy. Also reject continuation for material quality/runtime regressions even if success criteria pass. These are exploratory continuation criteria, not promotion. Report all eight results, partial-state warnings, accepted rebuilds and their costs; do not replace failures with partial ACL. There is no universal 3× MM gate. Measured paired cost and the user's roughly MM-order runtime objective guide the decision, with quality first.

If retraction cost falls but ordinary placement or failed-birth rebuilding still consumes the budget, the remaining computation/route limitation is exposed. If ordinary placement exhausts its neighborhood well before the allowance, the saved obstruction distinguishes that outcome from runtime exhaustion but is not an exact infeasibility proof. If completion improves while ACL regresses, the allocation hypothesis gains support but placement quality remains unresolved. A full success with promising classwise quality would justify fresh instances/sizes/relabelings, then separate untouched confirmation; this reused panel alone is insufficient.

Self-critique: proactive rebuilding sometimes improved the inherited score (50 C015 transactions) and may prevent later traps. Publishing the first feasible chain can consume useful connectivity, reduce future capacity, worsen ACL, or force a more expensive late rebuild. Individual quota inequalities do not ensure simultaneous future feasibility, and the unchanged one-label route search is incomplete. The available C015 ordinary proposals are only partial births; their existence proves neither completion nor good final quality. This single controlled complete experiment can test the allocation explanation quickly. Do not continue local repairs merely because more owners get published or fewer rebuilds occur.

Stop after this screen for a mechanism decision. No additional fixed-prefix routing diagnostic or further refinement sequence is part of this contract.
