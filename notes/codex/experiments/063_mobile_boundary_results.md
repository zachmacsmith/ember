# A063: small transferable Q gains, severe owner-search starvation

2026-09-09 UTC. **Exploration; retain A061 as the research baseline.** A063
preserves all 22 successes and lowers Q on six primary structures, including
three fresh families. Its fixed exhaustive-owner schedule is too expensive:
every added stage reaches its deadline inside reconstruction, and none completes
an owner pass. Permit one bounded scheduling follow-up; do not promote A063,
repeat its present allocation, or infer that the unvisited neighborhood failed.

Evidence: the root-owned [credit audit](../../../results/codex/transfer-cycle-001/audit-a001/output/summary.json)
and [per-input comparisons](../../../results/codex/transfer-cycle-001/audit-a001/output/comparisons.json)
are the authority for status, original-graph validation, Q and time. The prepared
[mechanism reader](../../../results/codex/a063-transfer-analysis/mechanism.py)
(`2554b330720c5aaeea386bc0694528472528813d229738ebd313498df90a02de`)
ran once in [attempt001](../../../results/codex/a063-transfer-analysis/attempt001/status.json),
exit 0, summary PASS, no errors. Its
[rows](../../../results/codex/a063-transfer-analysis/attempt001/output/rows.json)
and [summary](../../../results/codex/a063-transfer-analysis/attempt001/output/summary.json)
are saved; interpretation here did not rerun either reader or any constructor.
Intermediate proposal maps were not physically replayed. Saved commit/query
receipts describe mechanism use; final-map credit comes from the shared audit.

## Complete-constructor result

All methods used seed 0 and the same 60-second allowance on hyde06, with native
candidate dependency isolation and a separate pinned MM environment. The panel
has 20 primary structures and two nested relabelings. All 66 attempts are
accounted for: A063 and fresh A061 succeed on 22/22; MM succeeds on 21/22 and
times out on K100. No A063 error, invalid returned map, late return, unknown time
field or A061-success loss occurred. Operator deadline stops are distinct from
these timely outer successes.

For **every encoding**, the A063 inherited-base Q equals independently run fresh
A061 Q. This observed equality establishes the added stage's Q contribution
here; it does not identify their elapsed times or imply equality on other runs.
Across the 20 primary structures, A061 Q8299 becomes A063 Q8288: six improvements,
14 ties, no Q regressions. The three fresh improvements save only five qubits.

| Input | A061 Q → A063 Q | MM Q | A063 − MM Q | A063 / MM solver seconds |
|---|---:|---:|---:|---:|
| ER80, fresh | 261 → 260 | 248 | +12 | 59.018 / 3.792 |
| BA80, fresh | 216 → 216 | 257 | −41 | 59.018 / 2.230 |
| Regular80, fresh | 268 → 268 | 279 | −11 | 59.018 / 1.768 |
| Watts–Strogatz80, fresh | 163 → 163 | 136 | +27 | 59.011 / 0.619 |
| SBM80, fresh | 153 → 151 | 131 | +20 | 59.019 / 0.905 |
| Planar80, fresh | 127 → 127 | 118 | +9 | 59.014 / 0.590 |
| ER160, fresh | 1289 → 1289 | 1684 | −395 | 59.075 / 30.697 |
| BA160, fresh | 633 → 631 | 597 | +34 | 59.022 / 16.878 |
| Regular160, fresh | 925 → 925 | 1018 | −93 | 59.041 / 8.335 |
| Watts–Strogatz160, fresh | 476 → 476 | 368 | +108 | 59.026 / 2.277 |
| SBM160, fresh | 894 → 894 | 833 | +61 | 59.043 / 11.163 |
| Planar160, fresh | 284 → 284 | 276 | +8 | 59.018 / 1.824 |
| Grid128 anchor | 168 → 164 | 133 | +31 | 59.013 / 0.513 |
| Honeycomb190 anchor | 240 → 239 | 202 | +37 | 59.010 / 0.658 |
| Wheel127 anchor | 206 → 205 | 144 | +61 | 59.017 / 5.564 |
| K100 sentinel | 726 → 726 | TIMEOUT | undefined | 59.171 / 61.159 |
| Hidden singleton control80 | 201 → 201 | 181 | +20 | 59.018 / 2.806 |
| Hidden singleton control160 | 566 → 566 | 505 | +61 | 59.027 / 3.581 |
| Hidden branch control80 | 158 → 158 | 150 | +8 | 59.013 / 0.863 |
| Hidden branch control160 | 345 → 345 | 307 | +38 | 59.020 / 2.521 |
| Grid128 nested relabel | 163 → 163 | 133 | +30 | 59.013 / 0.410 |
| BA80 nested relabel | 220 → 220 | 233 | −13 | 59.014 / 2.412 |

Q is total chain size; ACL is Q divided by source vertex count. On the 19 primary
inputs with timely MM results, A063 has **4 Q wins and 15 losses**, no ties. All
four wins were already A061 wins. Their equal-input mean ACL is A063 3.013990
versus MM 2.995320. Among the 12 fresh primary inputs, A063 wins 4 and loses 8;
its smaller mean ACL (3.577604 versus 3.705208) is dominated by ER160 and regular
gains and does not erase those eight losses. The three fresh stage gains remain
above MM. The K100 timeout establishes a success difference, not a finite ACL
win. Both known-singleton controls miss their certified Q=n lower bound by wide
margins; the witnesses were hidden from candidates.

Within-embedding chain-length variance improves over MM on 6/19 primary common
successes and worsens on 13/19. Two stage improvements worsen that variance
relative to A061: BA160 5.39184 → 6.92809 and wheel 2.14062 → 4.07948. These losses
are retained despite their lower Q. **Across-seed ACL variance is unmeasured**;
one seed and nested relabelings do not estimate it.

The grid stage gain does not transfer to its second labeling: Q168 → 164 on the
parent versus Q163 → 163 on the relabel, with MM Q133 on both. Neither BA80
labeling gains in the stage; their final Q differs by +4, while MM changes by
−24. These are sensitivity observations, not two extra structural successes.

All-attempt solver totals, including both nested encodings and the MM timeout,
are A063 1298.640s, A061 227.338s, MM 161.565s; process-wall totals are 1343.205s,
270.747s and 174.389s. For the 19 primary common successes, A063 consumes
1121.442s versus MM 97.584s; 15 paired solver ratios exceed 10. Individual ratios
range from 1.92 to 114.96 on those primary pairs. This is measured cost evidence,
not an active universal ratio gate. Base and added-stage timings are recorded
separately; their cross-call differences are not stage speedups.

## What the mechanism evidence resolves

There are eight admitted strict-Q moves across six primary inputs. Five are
accepted at the first ranked root: ER80 (−1), SBM80 (−2), grid (−3 then −1),
honeycomb (−1). None changes donor ownership. The remaining moves are BA160
(−1 at root rank112, then −1 at rank3) and wheel (−1 at rank14). Only these three
commits trim donors: respectively 7 sites from 5 donors, 6 from 5 donors, and 9
from 8 donors. Their focus chains grow by 6, 5 and 8 sites, respectively, while
total Q falls by one. This confirms actual beneficial ownership redistribution
in the saved trajectory; it does not isolate its benefit from whole-chain
reconstruction or establish that donor mobility is necessary on those graphs.

All 22 operators stop during reconstruction; zero owner passes complete. Sixteen
encodings reach only the first owner. The other six admit their early moves,
then spend the remaining stage on a later owner's roots. Each encoding attempts
710–3304 roots in total. No fixed-owner root search completes without gain, so
the record contains **no completed no-gain pass** from which to reject the
remaining owners or this whole heuristic neighborhood.

The new stage uses 1072.222s. Nonimproving completed reconstructions alone use
1045.837s (97.54%); all-neighbor root generation uses 21.867s (2.04%). Successful
smaller-Q reconstructions use 0.0475s, excluding their root generation,
certification and other work. These root/query figures are nested in stage time
and must not be added to it. Work counters are diagnostic; no work/root/pass cap
stops the search. The explicit one-second finalization reserve is not the cause
of spending tens of seconds on thousands of unproductive roots.

Thus **computation allocation is the directly observed failure**. Representation
and neighborhood restrictions remain plausible on unexplored owners, but are
not resolved. Strict-Q acceptance does not block the eight generated smaller
maps, and the data do not show a smaller valid proposal rejected for a non-time
reason. Neutral preparation may still be necessary elsewhere; this experiment
does not test it. Root-distance sums rank candidates but are not a valid final-Q
lower bound: the reconstruction can prune its original root. Do not discard
roots using `1 + maximum root distance` without a separate proof covering that
pruning operation.

## Bounded follow-up proposal; no implementation yet

**Hypothesis.** Exhausting one owner's roots before exposing other owners spends
most time after useful alternatives for that owner have become rare. Interleaving
the same ordered root searches across owners can discover additional strict-Q
improvements in several source structures under the same wall allowance. This
changes search scheduling, while holding reciprocal terminals, tree construction,
root ranking, actual-Q admission, base constructor and validators fixed.

An epoch is one unchanged incumbent embedding and witness bundle. Keep a rotating
owner queue and lazy per-owner query cursors. One visit advances one complete
root reconstruction, retaining every unexamined root for a later visit. This is
an interleaving unit, not a root rejection cap. Query preparation, cached arrays,
memory, cursor operations and disposal remain timed.

```text
current = one unchanged A061 call under the original absolute deadline
queue = owners in the declared length/rank order; cursors = empty
while the original stage allowance remains:
    u = next owner in queue
    lazily prepare/rank u's query for current's epoch
    if the exact strict-gain bound excludes u or its roots are exhausted:
        retire u from this epoch's queue
    else:
        reconstruct its next root using the unchanged A063 neighborhood
        advance its cursor; enqueue u behind other remaining owners
        if actual Q decreases and the full original certificate passes:
            atomically adopt the single prepared incumbent
            invalidate all query cursors, terminals and root rankings
            repopulate the owner queue, continuing from u's successor
    if the entire current epoch is exhausted without a commit: stop
discard unfinished work on deadline; independently validate the final map
```

The precise successor order after commits must be frozen before code; a safe
version retains the pass's fixed owner permutation until its rotation completes,
then recomputes length/rank order. It must not restart at the longest owner after
every commit. Without commits and with enough time, deferred roots are revisited
and the same per-owner searches finish. After a commit, occupancy and reciprocal
witnesses change, so reusing an old query would be unsound. No independent
constructor output is selected and no MM map enters the state.

**Self-critique.** Root ranking per newly exposed owner can become the next cost
barrier, and a commit invalidates other owners' prepared work. A simple rotation
is fair in reconstruction count, not in CPU time. It may delay the observed BA
rank112 and wheel rank14 gains; neither gain may be silently dropped. Changed
visit order changes the embedding trajectory and can worsen final Q despite
strict-Q admission within each run. This follow-up is a test of coverage value,
not a claim that round-robin scheduling is the final algorithm or novel by itself.

**Cheap falsifier.** Before another redesign, freeze a small complete-constructor
comparison on ER80, SBM80, BA160, Watts–Strogatz80, planar160 and singleton-control80
from this development panel, seed0, the same 60s allowance and same-host timing.
These include all three fresh gain families, two fresh failures and a hidden
Q=n control. Root owns final control composition and execution authorization.
Report original-validated final Q/success and complete elapsed costs first;
then unique owners reached, completed roots by owner, time to each admitted Q,
root-preparation time, invalidated work and memory. Increased owner coverage
without additional final-Q improvement rejects the central scheduling explanation
on the tested cases. Failure to increase coverage because ranking or invalidation
consumes the budget instead identifies a computation-cost redesign need. Any
success loss or Q regression blocks promotion; a specific affected mechanism may
receive one explicitly justified follow-up. Do not proceed on coverage counts
alone. A positive small result must promptly face all 20 structures, relabelings,
fresh instances and repeated seeds; the untouched confirmation set stays separate.

Stop the present exhaustive-owner allocation, an unexplained first-root-only
variant, and a cap-increase-only repeat. Retain the measured whole-chain contact
reconstruction mechanism for this bounded cost test. None of these findings
changes the final objective of class-level quality improvement with preserved
success and acceptable runtime.
