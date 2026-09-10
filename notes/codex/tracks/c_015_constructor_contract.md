# C015: constrained contact construction

2026-09-09. **Before-code contract; no constructor implementation yet.** The [routing diagnostic](c_014_routing_diagnostic_results.md) found a quota-safe insertion on all three failed ER/BA prefixes without moving an earlier chain. Each succeeded on its first examined root in 0.19–0.34s, including setup and independent validation. These are local feasibility results, not complete-constructor quality evidence. C014 remains rejected.

## Hypothesis and failure attribution

Contact routing that considers distinct boundary consumption while building a chain can prevent several C014 structural stops. Evaluating every complete root proposal is also unnecessary for feasibility and expensive: C014 recorded 768,728 proposals and about 1.95GB of finalized candidate JSON across nine calls. That establishes substantial work and output, not its precise avoidable fraction. C015 will test a coherent construction policy: constrained contact routes, capacity-preserving growth and first-admissible placement on one evolving partial minor.

The chain-set representation and hard quota inequalities remain sufficient for the three diagnosed insertions. Root/path choices caused missed feasible states; the greedy search remains incomplete. First-admissible placement changes acceptance and computational allocation and may reduce quality. The complete screen must decide whether this combined policy improves success at useful cost while retaining acceptable ACL. Root-count reductions or smaller output alone are not continuation evidence.

## Frozen proposed policy

Retain C014's source order, one-owner publication, ordinary-versus-rebuilt score comparison, coordinated retraction and hard capacity rules. No diagnostic prefix or witness chain may initialize the constructor. Inputs are arbitrary source graphs and the actual ideal Zephyr target; source-family labels, instance IDs, canned maps, MM and busclique are unavailable.

For a proposed owner x, compute each old owner's distinct free boundary and its post-birth consumption allowance `b(u)`, using the decrement in remaining neighbors when x is adjacent to u. Exclude zero-allowance boundary sites. Distinguish absence of a contact route in the original free graph from disconnection after this quota exclusion; only the former uses the inherited contact-obstruction guide. Record owners responsible for excluded sites or denied path/growth claims as capacity obstructions. These are constraints encountered by the search, not proof that no other tree exists.

Enumerate all eligible roots on the smallest permitted required-neighbor boundary in qualifying components, breaking the pivot tie by source rank. With no introduced neighbors, all permitted sites are eligible. A singleton contact domain does not suppress non-singleton routes. Rank roots by decreasing required contacts already supplied, increasing singleton future-capacity deficit, increasing inherited Zephyr center distance, then target rank. The deficit is `max(0, remaining_neighbors_of_x - free_boundary_size_of_root)`. This inexpensive ordering favors roots needing less routing/growth and uses the hardware geometry; it contains no source-class information.

At each root, build one shared contact tree using the diagnostic's quota-admissible path policy: shortest added path, then normalized boundary consumption, then target-rank sequence, with one retained label per reached site. Every added site's consumption must fit every old owner's remaining allowance. Stop a failed extension and try the next root.

If the completed contact tree lacks x's required future capacity, grow it through adjacent free sites that preserve every old quota. Choose the site maximizing resulting distinct free boundary capacity; ties use the existing C014 state score and target rank. As in C014, allow zero or negative capacity changes while the connected chain grows; a positive-gain-only restriction is not introduced. Preserve construction-tree leaf pruning only when all current contacts and old/new capacities remain valid.

**Accept the first complete admissible root proposal.** Finish its capacity/contact checks before returning it to the existing publication/retraction logic. There is no all-root best-state selection within this placement, no per-owner time limit and no artificial root/path/work cap. A failed placement examines the policy's remaining roots until exhaustion or the global construction deadline; root exhaustion is not connected-tree infeasibility. Ordinary and rebuilt complete private states still use C014's existing score when the transaction has both available.

```text
start one empty partial minor under the global construction deadline
while a source owner remains:
    choose x using the inherited source order
    compute old post-birth consumption allowances and order eligible roots
    for each root until first admissible proposal, exhaustion or global deadline:
        route required contacts while enforcing old consumption allowances
        grow/prune the new chain to satisfy its own remaining capacity
        check and return the first complete admissible placement
    use the inherited publication/retraction decision on that result
    publish only a completely checked net-one-owner transition
independently validate the complete returned embedding
```

## Computation and receipts

Route and growth trials use a private new-chain mask, existing boundary masks and consumption counts. Materialize a full `_State` only for a completed root proposal; do not copy the 4,800-site owner array for each growth-site trial. Compute tie scores from the same domain/geometry/rank formula on the hypothetical chain, and check incremental capacity results against direct counts at completed proposals. This is computational reuse of the same mathematical state, not an extra operator or changed quota.

Keep aggregate root/path/growth counts, failure reasons, obstruction owners and stage wall/CPU; accepted-birth receipts; and an exact terminal private prefix for diagnosing a failure. Do not serialize every rejected root's full per-owner capacity table. This reduces diagnostic material while retaining complete call failure/time accounting. Charge instrumentation, validation, final output and deadline overruns. Preserve the global final-validation reserve and late-result rules; the diagnostic five-second interval does not become a construction limit.

## Self-critique, cheap falsifier and immediate screen

First-admissible placement may choose larger chains or close future domains that all-root score selection would avoid. The new root order only estimates continuation quality. A single path label can discard feasible alternatives, greedy growth can still fail, and successful insertion can create later difficulties. These coordinated changes therefore test a construction policy, not an isolated proof that routing alone improves ACL. All earlier C014 failures and quality regressions stay in the record.

Reuse the existing oracle, dependency isolation and targeted capacity/retraction/deadline checks. Add checks only for the new risks: direct-versus-incremental consumption/score agreement, first-admissible stopping, contact-versus-capacity obstruction classification and scratch-state rollback. Two complete tiny controls, star22 and K2,10 on Z2, supply a cheap pre-screen falsifier for growth and compact contact construction without supplying witness maps. If the policy cannot retain valid control construction within its recorded allowance, stop and explain that failure before the development screen.

After checks, run the complete constructor promptly on exactly eight ideal-Z12 development structures, in the declared input order `g0001,g0101,g0102,g0004,g0013,g0017,g0202,g0203`: the three diagnosed ER/BA inputs, WS80, grid128, singleton-control80, and newly generated Transfer003 SBM100/planar100. Root reports the input review passed, with panel SHA256 `83e16a8b3144f9e81ab4811b4bfe5fb2e869ddec49b11570f450572d72599dec`; the fresh inputs have 336 and 294 edges respectively. Use seed 0 and 60s global allocations, candidate/A061/MM separately with paired timing on one host, independent full embedding validation and all failures charged. The fresh instances test transfer; the three earlier diagnostic maps are not inputs to the algorithm.

Continue only for end-to-end evidence beyond a local repair: recovered successes across ER and BA, retained control success, and credible behavior on fresh instances, with mean ACL, within-chain variability and all runtime costs reported separately by class. Across-seed variability remains unmeasured. Quality losses or large runtime costs must be preserved and explained, not hidden by dense-graph aggregates or a smaller output file. This is an exploratory continuation criterion, not promotion. The retained algorithm remains A061 unless broader class-level evidence justifies changing it.
