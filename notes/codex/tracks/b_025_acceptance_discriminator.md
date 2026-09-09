# B025 proposal: test forced repair acceptance separately

**Design only; no code or calls.** Use exact B023 as the ancestor, without B024 placement. B023/024 accepted every completed route/erasure winner; their sparse failures usually completed all eight passes, while B024 improved both initialization proxies and still lost valid outputs. This leaves a concrete ambiguity: are the available edits too restricted, or does forcing an expensive edit immediately undo useful contacts and inflate chains?

**Hypothesis and one change.** Let the incumbent remain unchanged when B023's already-selected winner increases its exact current-price energy `F=Q+sum(lambda*excess)+sum(mu*missing)`. Commit iff `F_proposed <= F_current`. Equality retains B023's selected winner, so neutral defect-changing moves remain possible. Keep its initialization, complete proposal enumeration, tie order, interleaving, eight passes, prices, cleanup, final validator and 20M/20s allowance unchanged. In particular, a rejected route/erasure retains the price update that preceded it and advances the existing visit/cursor schedule; rejection does not retry locally or reset any limit.

```text
visit the next ordinary edge/conflict and apply its unchanged price update
fully generate and score exactly B023's existing alternatives
choose its unchanged minimum-ranked winner
if winner exists and its F <= the current state's F:
    publish with the unchanged final deadline check
else:
    retain the current chains; record a completed acceptance rejection
continue the unchanged constructor; credit only timely original-valid output
```

The hypothesis is that allowing the existing price observations to accumulate before paying for growth or destructive erasure reduces repair churn on several sparse structures. This is an acceptance discriminator, not a new neighborhood or a claim of energy convergence. Prices change across visits, so accepted-state F values across those updates are not a single descent potential.

**Distinct information.** B020–022 used contact-witness/whole-incidence rebuilding while preserving all contacts; their strict-energy decisions do not test this rule on B023's states with missing contacts and overlap. B023 introduced unconditional defect-directed publication. C's region moves/annealing used disjoint incomplete states and different energies; A's valid-minor refinement and lifting also do not supply this controlled comparison. No novelty is claimed. The first rejected B023-style winner is the first possible state divergence; later candidate sets naturally differ even though their generating code is identical.

**Self-critique and negative witness.** Rejection can delay necessary growth indefinitely within the fixed schedule. With one logical edge, target path0…11, and supplied singleton chains at0 and11, either route adds10 sites. Its resulting F is12, but the unchanged incumbent F reaches only11 after eight edge-price increments (mu goes1→9). The new gate rejects every route, although B023 completes a valid Q12 map immediately. This is a hand-derived supplied-state limitation, not a claim about its BFS initializer. Restricted singleton relocation and the eight-pass policy interact with acceptance; a negative result cannot prove forced acceptance was harmless everywhere.

**Proposed falsifier.** After only an improving/tie/uphill publication check and interrupted-rejection accounting, run the same diverse B9 complete-constructor screen: treatment, contemporaneous B023 and fresh MM, seed0/20s,27 calls. Keep the >=7/9 validity and >=3 common MM Q-win/tie gate. Save completed rejection counts by route/erasure, their Q/M/O/F deltas, later selected-defect recurrence, all work and every failure. No exhaustive local diagnostic is needed. Rejections followed by improved complete validity/Q support the acceptance hypothesis; lower partial energy does not. No rejections means the gate never exercised. Repeated fully scored rejection with missing defects implicates this acceptance/neighborhood combination; interruption instead limits the cost inference. Unchanged representation and proposal code control two causes, but downstream scheduling and available routes remain coupled after divergence. If the complete gate fails, retire this rule without adjusting prices, passes or caps.
