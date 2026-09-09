# Dependency-ready lifting with constrained insertions first

Design only after A061; no source edit or numerical call. Retain the measured
branched-path stage unchanged. This is one alteration inside its inherited
A053 constructor, not a replacement constructor, source-reduction change or
larger repair neighborhood. Adaptive source splitting belongs to C; B tests
initial assignment separately.

The exposed bottleneck is **construction ordering under changing physical
ownership**, rather than unavailable global minor representation. In A049's
saved cycle/wheel failures, contact routes existed but consumed an unrelated
pending owner's only free port. A050 repaired those particular prefixes; A060's
planted seed1 and A057's wheel seed1 still failed during lifting. A061 leaves
grid, honeycomb and other short-chain deficits despite its useful final stage.
These facts motivate arranging constrained pending insertions earlier, but do
not prove the fixed journal order caused any latest failure or quality loss.
[Port evidence](experiments/049_failure_frontiers.md),
[failure-stage evidence](experiments/057_failure_stage_diagnosis.md),
[replication](experiments/060_branched_path_results.md),
[breadth results](experiments/061_branched_path_results.md).

The distinction is testable in one complete-constructor comparison. The
neighborhood can already grow chains, split connector ownership, transfer a
site and release a bounded block; its opportunities depend on the current
occupancy. Change which legally ready vertex receives those exact operations.
Do not relax contact/frontier acceptance. No improvement after actual ordering
changes weakens this scheduling hypothesis; unchanged choices do not test it.
Improvements only at much greater total cost fail the practical claim. Native
core geometry failure is outside this change: A057 hypercube seed1 and most
recorded >10×MM core/layout time would remain upstream. This is not a proposed
universal runtime fix.

## Why some reverse rows can commute

Keep the A053 reducer, anchors and entire numbered journal immutable. Row
`i=(v,N_i,F_i)` records all surviving neighbors, **including fill neighbors**,
and the edges newly created when v was eliminated. Its dependencies are N_i;
each is in the retained core or a later forward-elimination row. The dependency
graph is therefore acyclic. A row is ready iff every vertex in N_i is placed.
Original-neighbor readiness alone is insufficient.

Let P be the processed rows, E their placed chains plus the core, and R the
usual all-node requirement adjacency with exactly the F_i for i in P removed.
Every created fill edge has a unique creator: once present, it survives until
an endpoint is eliminated, and an eliminated endpoint never returns during
forward reduction. An original edge cannot be newly created as fill. For a
ready unprocessed v, all placed requirement neighbors of v are exactly N_i:
an earlier-eliminated neighbor cannot already be processed because it depends
on v. No earlier processed fill release can have removed an edge incident to
unplaced v; that release itself would have required v to be placed.

Two simultaneously ready rows consequently do not depend on each other, and
neither row's fill deletion involves the other's new vertex. Their unique fill
deletions and placements commute as graph edits. Physical choices and Q need
not commute. Inserting either first requires its usual independent certificate
against that row's private R; after both, the same pair of R edits is present.
After all rows, R is exactly the original graph and all source vertices are
placed. This proves requirement bookkeeping, not guaranteed physical lifting.

Shared fill support is a useful countercheck: take a K5 core missing edge a–b
and two degree-two vertices u,v both adjacent to a,b. Eliminating u first
creates a–b; eliminating v creates nothing. Both rows are ready at the core.
Undoing u first releases a–b earlier than the legacy order, but both orders
recover the same original requirements. Never keep/recreate that synthetic
edge merely because v also used it as a scaffold. Conversely, a dependency
through a recorded synthetic neighbor may not be skipped.

## One fixed proposed policy

For each ready v, define the **direct singleton contact set at the committed
entry**, before fill release, preparation or pruning:

`D_v = free_sites ∩ intersection(boundary(E[w]) for w in N_v)`.

The empty-neighbor intersection is all free sites. Choose the smallest
`(|D_v|, -journal_index)`; the tie order is exactly legacy reverse order.
Zero comes first. It means no direct singleton at the current fixed endpoints,
not impossibility: a multi-qubit connector, old-chain growth or repair can work.
It also does not include the future-port guard or count all ordinary proposals.
This deliberately cheap urgency signal is the only new selection rule; no
distance, family, Q forecast, secondary lookahead or policy adaptation is added.
With one ready row, select it directly.

```
reduce once exactly as A053; construct the same core once
pending = all journal rows; placed = core; R = usual initial requirements
while pending:
    ready = rows whose complete recorded neighbor sets are placed
    finish all ready-row direct-contact counts under the live budget/deadline
    i = minimum(count, legacy reverse index)
    trial_R = R with exactly row_i.created_fill removed
    run unchanged A053 transfer -> ordinary insertion -> blocked-only repair
        against trial_R, including existing released-fill pruning and guards
    if no timely certified insertion: stop; preserve E, R, pending and failure
    atomically adopt E, trial_R and retire row_i; update dependency readiness
validate complete original graph; then run the unchanged branched-path wrapper
```

There is no retry of a different ready row after the chosen insertion fails.
No candidate is evaluated to choose the scheduler key. A partial key scan cannot
select a prefix winner: interruption stops with the prior committed state.
All boundary scans, readiness maintenance, bitset intersections/counts, copies
and logs consume the existing 20M construction allowance and original absolute
deadline; no renewal or extra search allowance. Bitset costs scale with target
word count, not mathematical O(1). Existing transfer/repair/root caps remain.
Retain failed partial R, all chosen row IDs/keys/ready counts, first departure
from legacy, scheduler work/wall, base/core/lift Q and the unchanged branch
receipts. The final saved-data checker must reconstruct R by actual row IDs,
not assume a contiguous reversed journal prefix.

Self-critique: small direct domains can be misleading when a short multi-site
path is plentiful. Pulling zero-domain rows forward could increase expensive
routing, and releasing shared fill earlier can destroy useful spatial guidance.
This is a fail-first scheduling heuristic, not a new embedding representation
or a proof that local options compose. It may leave all relevant dependencies
serial, fail to rescue any bad prefix, or damage successful outputs. Native
cost and core failures remain. No new mechanism is bundled to rescue those
outcomes.

## Proposed bounded decision, pending root review

Only tiny new-risk checks precede physical work: the shared-fill example in
both orders, a synthetic-neighbor dependency, tie/no-choice equivalence,
atomic failure/R rollback, and interruption before completed key selection.
They check graph bookkeeping and policy, not exhaustive neighborhood reach.

Then one prospective complete-constructor screen: six existing records
planted34404, additional wheel2430, grid1584, honeycomb32367, cycle1829 and
additional hypercube4756, seeds0/1, fresh unchanged A061/new variant/MM on one
host, 60s (36 calls; contiguous pilot seeds, no harness change). The two
additional records use their already audited A057 originals/labels. Cycle
retains the optimal-ACL control; hypercube makes the out-of-scope core failure
visible rather than silently excluding it. No saved-final gate or adaptive
seed/input substitution.

Proposed advancement requires no lost fresh A061 success or per-structure
common-seed mean-Q regression; at least one fresh control lifting failure
recovered and a gain on another noncycle structure; and no >10× fresh A061
solver/process ratio. If the known control failures do not recur, their
prevention remains untested; no replacement seed is added. All MM quality,
coverage, seed variability and runtime gaps remain separate. Actual order
divergences and subsequent complete outcomes distinguish this hypothesis from
more routing effort or changed acceptance. A negative or cost-censored screen
ends this fixed policy, rather than starting another order/cap adjustment chain.

This note requests review of that exact scheduling policy and proposed screen;
it authorizes no implementation or execution.
