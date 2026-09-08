# B006: reuse the immediately preceding completed domain computation

Hypothesis saved before code, 2026-09-08. B005 computes the remaining domains inside each successful singleton trial, then rebuilds and propagates the identical state at the start of the next iteration. Grid and honeycomb respectively perform 128 and 140 complete propagations for 64 and 70 commits. Avoiding that duplicate work may improve runtime while retaining the same placement choices.

```text
pending_domains = absent
at each outer iteration:
    consume pending_domains if present, otherwise rebuild and propagate
    clear pending_domains immediately
    perform unchanged promotion, tree insertion or singleton trial
    after a singleton trial commits, if its remaining-domain propagation completed:
        carry those domains to the immediately following iteration
    on promotion, tree insertion, failure or partial propagation: carry nothing
```

This is a one-use value passed along exact control-flow continuity, not a lookup cache. Only the accepted singleton trial's dictionary can be carried, after the final commit check. The committed embedding is precisely that trial, and the promotion set is unchanged. No source/target/promotion/chain mutation occurs before consumption. In particular, domain results from rejected trials or from before chain growth are never eligible. A completed result for the last vertex need not be consumed after construction terminates.

Record domain-build calls, reuse hits, and each reused result's measured original build/propagation work. The latter describes work that produced the reused value, not a universal claim about hypothetical saved work under a binding allowance. Total counted work and wall time remain authoritative. All existing global, propagation and deadline limits stay fixed. With nonbinding limits, complete fixed-point results and subsequent choices should match B005. Binding global/time or propagation sublimits can change later available work; those outcomes must remain visible.

Self-critique: counters and code show duplication, but Python state preparation or routing may dominate wall time. Reusing only completed passes deliberately leaves other opportunities untouched. A stale result after promotion or tree mutation would incorrectly constrain future placements; local one-use scope and explicit invalidation are the principal safeguards. This is an implementation optimization, not scientific novelty or a fix for B005's failed relaxation strategy.

Before the same nine-input/fresh-MM screen, compare exact embeddings, construction orders and committed updates with frozen B005 on tiny nonbinding fixtures. Exercise promotion/tree transitions and force partial propagation to verify no carry. Confirm that build counts decrease when reuse occurs and inputs remain unchanged. Falsifier: changed choices under nonbinding limits, any stale carry, no measurable work reduction, or worse full-call timing/quality. Retain all results. The separate B007 hypothesis is to grow promoted chains while preserving future domains; it is not part of this change.


Implementation is the separate standalone `factored/propagating_reuse_construction.py`; B005 remains unchanged. Fourteen guarded checks pass in `results/codex/track-b006-checks/attempt001`, including five exact nonbinding comparisons to B005 and dedicated partial-pass/promotion invalidation cases. On those fixtures, B005 minus B006 counted work equals the sum of reused results' original computation work. The check manifest binds both module versions and the tests. No development-panel output has been observed yet.


The pre-outcome run is `results/codex/track-b-reuse-006`, with exact identities in `results/codex/track-b006-checks/freeze.json`. It retains all nine source/target bytes and the seed/deadline settings. The source/harness owner declared a stable window before initialization; staging and the single detached hyde02 launch used the existing audited cluster helper. Final analysis will compare complete embeddings and retained partials, not merely Q.
