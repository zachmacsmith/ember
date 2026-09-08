# B008 diagnostic hypothesis: hidden competition for singleton sites

Design saved before diagnostic code or observations. B006/B007 propagate logical adjacency constraints, but do not enforce an injective assignment of remaining singleton variables. Nonempty domains can therefore share too few physical sites. A Hall deficit before a promotion cascade would justify studying a bounded all-different check; it would not establish that matching improves final ACL.

Use only the exposed ER80, Watts–Strogatz80 and king64 inputs, seed 0. Replay each frozen B006 and B007 constructor through at most 40 committed placements, under its unchanged 60-second deadline and work limits. Add one read-only observation hook after the main loop obtains its domains. Capture only completed, nonempty propagation results, with domain bitsets, committed count, promoted set, last update, counted work and the actual partial embedding. Stop at the first loop entry with 40 commits. No matching or I/O occurs inside the constructor; capture cost remains in its deadline. Compare all recorded choices and promotion prefixes with the already saved run. A deadline-bound or differing prefix is retained but cannot establish unchanged-trajectory evidence.

```text
for each captured completed domain state:
    build source-variable → available-target-site bipartite edges
    find maximum matching by deterministic augmenting paths
    if some variable is unmatched:
        traverse alternating paths from all unmatched variables
        return reached variables X and their reached sites N(X)
        independently verify the union of domains of X equals N(X)
        verify |N(X)| < |X|
```

Run matching offline with a fixed five-million edge-scan and five-second allowance per state; report unfinished cases as unknown, not collision-free. Check a hand collision of three nonadjacent variables sharing two sites against exhaustive assignments, and a feasible control. Preserve source/input hashes, raw domain masks, all partial failures and diagnostic costs. No MM calls, timing comparison, constructor policy change or new candidate is involved.

Self-critique: a covering matching ignores required edges between future variables and says nothing about connected chains after promotion. A Hall witness in propagated domains concerns the current singleton assumptions only. No deficit, or deficits appearing only after the observed decision failures, falsifies this explanation on the inspected prefix. Tiny connected-set domains would model promotion more faithfully but multiply candidate cost; root lookahead can avoid a bad commitment but may repeat the already rejected branching expense. This diagnostic tests the cheaper missing condition first, without assuming it is the right next algorithm.
