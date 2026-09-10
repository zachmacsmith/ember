# A065/A064 saved entry-map and trajectory comparison

2026-09-10. **Before-code diagnostic proposal; root review precedes execution on
constructor outcomes.** The completed screen reports three A065 Q gains over
A064 and six ties, but the existing passive reader compares starting Q only.
No algorithm refinement, constructor call, rerouting or MM-map access is proposed.

**Hypothesis.** Paired A065/A064 calls start from the same ordered embedding, and
A065 follows the same committed state sequence farther within its wall budget.
Recovering their starting maps and comparing shared committed prefixes will
separate extra search from differences already present in the inherited base.
Unequal bases falsify that causal interpretation for the affected pair. Equal
bases followed by different committed moves falsify exact-prefix equivalence
and require explanation before attributing all differences to acceleration.

```text
bind the passing common audit, receipt audit, frozen sources and candidate files
for each A065/A064 call independently:
    decode its already independently valid final embedding into internal indices
    use frozen source/target node order; preserve every chain's element order
    walk committed receipts backward, without running any search:
        require each changed owner's current chain == its recorded after chain
        require owner uniqueness, valid indices and the recorded Q transition
        replace those chains with their recorded before chains simultaneously
        retain this reconstructed ordered state and its receipt index
    require recovered entry Q matches both wrapper and operator entry Q
    independently validate that recovered entry using the unchanged minor oracle
    check before/after links against the recovered forward state sequence
compare paired entry maps directly, both ordered and as physical chain sets
compare complete state/semantic-move prefixes directly, ignoring clocks/counters
save entries, compact per-epoch fingerprints, first divergence and all failures
```

The pinned pilot inserts graph nodes in record order and serializes chain lists
without sorting; A063 `_Context` preserves that label/index order and chain order.
Receipt owners and sites are internal indices; final maps contain external labels.
Do not apply seeded rank permutations to either. Source keys use explicit node
order, not JSON dictionary order. Keep changed-owner order as recorded. Compare
root, root rank, owner, round/slot, Q and ordered before/after chains as semantic
move fields; time/work and invalidated-cache accounting are excluded. Report
state-prefix and semantic-move-prefix agreement separately. Equal site sets with
different list order are reported separately, never silently normalized away.

Use the existing standalone original oracle for recovered entries, without
importing candidate code. Existing audits own final embedding credit. Read only
A065/A064 raw maps; MM records and witnesses remain untouched. One tiny supplied
fixture with nontrivial external label order checks correct reversal, then a
corrupted after-chain ordering must be rejected despite identical site sets.
Also corrupt a linked before-chain so the previous receipt's after-chain cannot
match. These are focused diagnostic checks, not constructor experiments.

**Self-critique.** Reversal establishes consistency of immutable saved receipts
with the final map; it does not replay the algorithm or independently reconstruct
unrecorded rejected proposals. A different entry may itself result from timing in
the inherited constructor. Shared committed prefixes do not prove equality of
every rejected query or that remaining MM deficits are purely computational.
Recovered intermediate maps are receipt-derived; only the recovered entries
receive new independent validation. No diagnostic success promotes A065 or
changes a benchmark outcome. Preserve malformed/missing cases and diagnostic
time rather than assuming a shared base when reconstruction fails.
