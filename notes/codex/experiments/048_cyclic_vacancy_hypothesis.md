# 048: continue deletion-seed traversal across contractions

Specified before implementation, 2026-09-08. This changes one scheduling rule
in the bounded cumulative vacancy stage, with the same repair neighborhood,
proposal limits, wall allowance and validators.

**Hypothesis.** Restarting the seed order after every accepted contraction
spends a limited stage budget revisiting earlier locations before inspecting
later ones. In 046, 677,713 of 1,366,701 proposals occur at an owner/site key
already examined by an earlier query. This count does not establish unchanged
search dependencies or prove wasted work. Twenty-five inputs hit 50,000
proposals; none hit its wall deadline and the largest stage wall is 0.516 seconds.
Continuing a cyclic traversal may spread the same work across useful locations.

```text
run unchanged construction, contact refinement and final safe deletion
freeze an owner priority from entry chain length, source degree and canonical ID
start the unchanged stage clock and shared 50,000-proposal allowance
cursor = none
for at most 20 successful contractions:
    list every currently eligible (owner, site) deletion seed
    order by frozen owner priority, then canonical target site
    begin immediately after cursor, wrapping once; first call starts at the front
    run the same bounded contact-directed vacancy search in that order
    if a timely, independently validated Q-minus-one proposal returns:
        adopt it; cursor = its deletion seed
    else stop and retain the current valid embedding
perform unchanged final original-graph validation and deadline classification
```

Each query still enumerates the complete current seed set once; newly acquired
sites are eligible in that set. A disappeared cursor need not remain present:
use the first strictly later key, or wrap if none exists. The order is a global
structural rule, with no graph family, saved competitor, alternate constructor,
restart, negative-result cache or selection between algorithm outputs. The
existing default and ordinary bounded policies must retain their behavior.
All setup, failed work, sorting, copying and validation remain in elapsed time.

**Self-critique.** A repair can make an earlier failed seed productive, so
deferring it may lose valuable compound trajectories. Repeated keys alone do
not identify repeated search states. Fixed entry owner priority may become less
appropriate as chains shorten; cyclic order can still revisit locations after
wrapping. This is a conventional scheduling experiment, not a novelty claim.
It could change final quality in either direction despite monotone local Q.

**Cheap falsifier.** First check ordering, disappeared cursors, newly acquired
sites, wraparound and unchanged default behavior on small supplied embeddings;
independently validate a real two-step cumulative repair and deadline/work
rollback. Then use the audited pipeline on all 34 unchanged readiness inputs,
seed zero, Z12, 60 seconds, separate fresh bounded-control/cyclic-treatment
processes on one host. Retain all failures and Q regressions. If the same work
budget gives no aggregate quality gain, reject the scheduling change rather
than increasing its cap. Original-label validation and complete cost accounting
remain mandatory; exhaustive search/replay is deferred. The concurrently
running 047 MM comparison remains frozen and unaffected.

Saved-counter evidence: `results/codex/046-results-review/root_search_counters.json`.
It runs no solver and makes no claim that repeated owner/site keys can safely
be cached.
