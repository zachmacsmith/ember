# B015: skip only certified disconnected-contact release blocks

Pre-code hypothesis, 2026-09-08. B014 certifies that B012's first two ER66 releases cannot support the fixed first-v/frozen-outside insertion. Skipping these blocks may let its unchanged one-million-unit query inspect a viable later block. Use a separate fixed B012 copy, with no other construction or routing change.

After privately releasing `K` and before its first insertion, recompute frozen free boundaries and B014's protected set `Z`: a frozen owner protects its sole free site when it still has an original pending neighbor after `v`, including released `K`. Required endpoints can protect their own sites. Reject if no connected component of the available target graph minus `Z` touches every frozen required chain.

Evaluate the same predicate efficiently: with required chains present, choose the one with the smallest unprotected boundary (tie by existing source rank). Explore components starting only from that boundary's sites, in existing physical rank order, marking each component once. Any qualifying component must touch this chosen endpoint, so other components need no scan. Return *not rejected* as soon as one explored component touches every required chain; exhaust all chosen-endpoint components before certifying rejection. Empty required set needs any unprotected free site. This traversal choice changes **only evaluation cost**, not insertion roots, path order or the mathematical skip predicate. A pass remains unknown as to embedding feasibility.

```text
for K in B012's unchanged block vector, within the same live repair allowance:
    privately release K
    result = metered protected-free component classification
    if interrupted: discard this private query and retain the committed entry
    if certified obstructed: record certificate and continue to the next K
    otherwise: run exactly B012's first-v insertion and restoration sequence
```

Charge owner/site/source/target-adjacency scans to the existing live scan method and original deadline. Record filter units and wall separately as **overlapping repair work**, including failed and interrupted scans. Preserve 1M per repair, 5M across repairs, 20M global, and all nested propagation/matching/growth limits; do not renew allowances or add a filter budget. Unknown is never an obstruction certificate. Preserve complete/partial filter evidence and all examined block records. Outside chains, global promotions and completed-domain invalidation retain B012's rules. Ordinary successful insertion never invokes this filter.

Self-critique: a large connected region can conceal the true capacity conflict; scanning it can use time without saving routing. The next surviving block may still exhaust the unchanged allowance. This first-v certificate deliberately excludes other rebuild orders or outside movement. Exact skipping expands inspected coverage only when it costs less than the certified failures; it does not promise better final ACL or novelty.

Before any panel, check the six fixed predicate cases against B014, a work/deadline interruption with entry rollback and truthful unknown status, overlapping scan totals, and unchanged ordinary-success choices. Then call only the same tiny local witness and the saved B011 ER66 local helper, once each, with their existing five-second allowance and live historical counters. The cheap falsifier remains actual ER66 recovery under the normal limit. Preserve failure rather than enlarging a cap, changing the order, restricting roots or selecting successful blocks by output quality. Stop for review after these local observations; no registry edit or broader screen is authorized.
