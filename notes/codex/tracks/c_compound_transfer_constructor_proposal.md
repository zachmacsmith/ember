# Proposed constructor discriminator: private compound transfers

**Design only; await root review before integration or calls.** The saved-state gate found two Q-neutral contact gains after articulation transfer, free reconnection and pruning. This supports testing a larger move neighborhood while keeping **every published owner region connected, nonempty and disjoint**. It does not justify a globally fragmented representation. The lost grid observation remains unknown.

Use the unchanged atomic constructor as the experimental control. Preserve its singleton initialization, source/target order, seeded missing-edge/endpoint choice, four-kind visit cycle, energy M+Q/26, temperature, original connected proposals, overall deadline/visit limit and final cleanup/validation reserve. Change only the transfer proposal's ability to consider one private compound candidate:

```text
At a transfer visit, keep the existing receiver and missing-edge target.
Enumerate target sites in the existing distance/seeded-tie order.
Evaluate ordinary connected-donor transfers exactly as before.
For at most the first eligible interior site in that same ordered prefix:
  require exactly two donor components, no lost current original contact,
  and a new contact for the selected missing edge;
  transfer privately, try one shortest unused donor-reconnection path;
  prune donor/receiver once in the gate's canonical order, ≤64 site visits;
  require all old and incidental gained contacts and final Q≤entry Q.
Compare the complete compound candidate with ordinary proposals using
the unchanged final energy/distance/seeded-rank ordering and score cap.
Commit one chosen move, or keep the current state untouched.
```

No alternative bridge, global assignment, saved embedding or constructor restart is available. Candidate generation, local component checks and exact contact-count deltas are charged. Freeze a small compound allowance before code: **one attempt per transfer visit, at most 128 attempts per constructor, at most 25,000 examined adjacency/chain/contact records and 0.05 seconds per attempt**, all clipped by the original search deadline. Reaching a bound discards the private candidate; it does not discard an already scored ordinary proposal. The two saved witnesses used approximately 10,500 and 5,200 local examinations before full diagnostic recount/certification, so this allowance tests a plausible local implementation without importing its expensive whole-target diagnostic scans into every visit.

The implementation must stage only the two changed chains and affected coupler-count deltas; ordinary options/order remain unchanged. After a commit, invalidate geometry-dependent caches for **both** changed owners, including Q-neutral moves. Reuse the exact final original-edge validator. No intermediate path/fragment or late private certificate earns embedding credit. Record generation exclusions, reconnection failures, compensation failures, work/time limits, scored/selected/committed compound moves and their Q/M deltas; these distinguish inaccessible candidates, neighborhood gain, acceptance and computational cost.

**One necessary full-constructor screen.** After focused integration correctness checks, propose the same eight original C inputs, seed 0, fifteen seconds per call, with three separately measured fixed arms: compound variant, unchanged atomic control, and fresh stock MM, sequentially on one host chosen by root. That is 24 calls, not a portfolio. No further saved-state gate or grid repeat precedes it. Require **at least 4/8 timely original-valid completions while retaining every atomic-control success** to continue this direction. Failure of that coverage threshold retires the variant even if partial M improves. Report Q and time on every valid pair and all failures; passing the threshold is not superiority to MM.

**Self-critique.** Useful connected transfers already existed at all five retained hard starts; scheduling, initialization and wider geometry may dominate. Only 2/64 sampled fragmented transfers met the Q bound, and compensation can exploit existing redundancy. A compound attempt can reduce the number of ordinary search visits; its count and shared-deadline cost are part of the test. Keeping published chains connected is the smallest supported change, but a positive local certificate may still fail to improve end-to-end coverage. No parameter sweep or novelty claim is proposed.
