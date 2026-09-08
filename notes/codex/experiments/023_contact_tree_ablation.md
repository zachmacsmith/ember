# Cumulative contact-tree ablation

Revision 020's design, self-critique and isolated mechanism tests are recorded in
`../contact_tree_revision_020.md`. Its fixed-incumbent proposal diagnostic finds
20 improving groups out of 36 with distance-guided trees, versus 14 with greedy
trees. That costs about 6.9 times as many counted expansions and 4.7 times the
local move wall time; independently improving groups cannot be added together.

This prespecified cumulative test uses the same 18 saved 011 native-search
incumbents and fixed work/region/group limits as 016/022. Replay legacy first,
then compare strict sites/groups refinement with the same policy using
`tree_policy='distance'`. The new builder has frontier width ONE and two shortest
witnesses per contact, with unchanged root and alternative quotas. The separate
redundancy objective is disabled in every arm. Every returned group remains
subject to complete original-graph validation and strict qubit reduction.

There are 54 sequential isolated calls, each with 60 seconds refinement allowance.
Results are under `results/codex/023-contact-tree-ablation`. Require all 36 strict
control/legacy outputs to reproduce 016 before interpreting changes. Report all
gains and regressions, actual charged work, tree-state counters, and wall time.
The comparator is a fixed policy; no per-input choice among outputs is allowed.

The lower-bound-guided proposal may spend its allowance on too few groups and
worsen final quality despite stronger local moves. This is the main falsifier.
No result from this run establishes end-to-end speed or all-family superiority.

Source snapshot: `108e354089d661c248a305ac2c34a0855cfa75b97d6e7c54f1265a2d8d807115`.
The 19 contact-tree tests pass, including an integrated replacement that preserves
frozen chains, full source contacts and the shared work cap without calling the
greedy tree builder. This establishes the configured call path and validity,
not embedding superiority.

## Result and disposition

All 54 outputs are valid and timely; all 36 legacy/strict controls exactly
reproduce their saved embeddings. The distance-tree policy has zero improvements,
12 ties and six regressions versus the fixed strict sites/groups control. It
uses 24 more qubits in total, with mean ACL 2.683171 versus 2.664248. The policy
is therefore **rejected for promotion** to the next end-to-end screen.

Its total charged work is 7,681,427 expansions versus 4,142,004. Thirteen calls
stop at the work limit, versus two controls. Total refinement wall is 16.9682
versus 16.0986 seconds; median paired ratio is 1.2495. The expansion and wall
ratios differ because the operation counter does not measure all computation.
The good fixed-group witnesses from 020 are real, but they do not yield better
cumulative embeddings under this search policy and allowance.

Lessons retained: spending more effort per tree can remove useful group
coverage, and replacing a shortest tree may change the locations of subsequent
contacts and bounded root alternatives. These data do not separate those causes.
A future distance-based pruning rule should be inexpensive and judged on the
full evolving embedding, not just successful individual proposals. The current
distance builder stays as a documented diagnostic implementation and mechanism
fixture; the remaining candidate uses greedy trees with the improved group
schedule and separately tested contact-redundancy acceptance. No per-graph
selection between the two tree builders is introduced.
