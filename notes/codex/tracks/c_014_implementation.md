# C014: first focused gate

2026-09-09. **Both declared tiny complete controls passed on the first attempt.** This supports the planned Z12 development screen, not promotion or an MM comparison. C013 and its rejected policy remain unchanged; its 27-call screen was never run. The [C014 policy](c_014_capacity_policy.md) corrects the earlier Z2 maximum-degree statement to 19 (Z12 remains 20).

The isolated module `zephyr_capacity_contact.py`, API `capacity_contact_embed`, implements capacity-aware connected growth and capacity-preserving pruning within one partial embedding. Proposed descriptor: `capacity-contact-domain`, configuration `{}`. It imports C013 state/contact/geometry helpers by file path, never the C013 constructor; existing budget and validity helpers remain unchanged. No registry or shared harness change was made here.

Root reviewed the complete source and wrapper; an independent A-track reviewer checked capacity updates, birth/retraction invariants, spanning-tree pruning and failure/guide semantics. Both reported no concrete blocker at module SHA256 `3b452c6167707bb8a351aa34028fd821586d4f7f253504bd81489ace593a2a64`, C013 `113d5b006abf5a87010b477d8107bb7460fcabdfe0954f2832356180c0377786`, and effective pre-code policy `647b47f99fea5ce58a3a6d177ea944f716e27d70445341a5aa97d96aa34dd3bc`. This is static review, not an exhaustive correctness claim.

## Observations

The [first-attempt packet](../../../results/codex/track-c-014-checks/attempt001/) preserves the seven pre-execution sources, exact invocation, stdout/stderr, status, every receipt and both returned embeddings. Five focused groups passed once. The suite process used 0.778392 s wall and 0.578040 s CPU; the preserved D-Wave NetworkX deprecation warning is unrelated to candidate validity. No check was rerun.

| Actual complete call | Status | Q | Mean ACL | Within-embedding chain variance | Wall s | CPU s |
|---|---|---:|---:|---:|---:|---:|
| star22, Z2, seed0, 5 s | valid SUCCESS | 23 | 1.045455 | 0.043388 | 0.157286 | 0.156322 |
| K2,10, Z2, seed0, 5 s | valid SUCCESS | 12 | 1 | 0 | 0.018260 | 0.018191 |

Both Q values equal evaluator-certified optima. No witness entered candidate initialization or input. Both outputs passed the existing independent original-graph oracle, returned within their allowances and reported no error; the import guard recorded no MM/busclique attempt. These are the only two actual complete calls. A separate injected-clock wrapper check is correctness evidence only, never performance data. There were no failed actual complete calls, timeouts, hidden retries or MM calls in this packet.

Star's first publication uses a two-site hub, then Q increases from 2 through 23. Its 664 completed roots include 160 growth steps, one per initial hub root. K2,10 publishes singleton chains throughout: 296 completed roots, zero growth. **Both complete calls used zero retractions.** They resolve the demonstrated singleton-only exclusion while preserving simultaneous shared-neighbor alignment on one distinct tiny control; they do not demonstrate full-constructor coordinated movement or transfer to Z12.

The focused checks establish these particular observations:

- Two physical couplers to one free site count as one capacity unit. A corridor example passes through a zero-gain growth step and prunes to a two-site tree whose capacity-supporting endpoints both survive.
- Claiming an unrelated owner's last required free contact records that owner as a blocker and rejects the unsafe proposal. Retraction recomputes both remaining original incidences and released capacity; in the supplied case both increase from zero to one. Entry states remain unchanged.
- Capacity exhaustion is distinct from contact unreachability. A completed capacity failure with no outside owner refuses the private transaction without invoking the contact-only guide. This is refusal evidence, not a successful expanding-retraction fixture.
- Injected interruption leaves unfinished growth unpublished. A previously certified complete private candidate can pass the final oracle while the interrupted root scan remains explicitly censored. The injected clock does not measure actual runtime.

## Decision and remaining risk

Proceed to the [separately frozen nine-input screen](c_014_constructor_screen.md) without another refinement. The tiny controls support representation repair; they cannot establish that individual capacity counts produce compatible contact geometry on larger graphs. The all-owner capacity invariant is necessary only for the currently fixed chains and does not certify simultaneous feasibility.

Computational cost remains unresolved. Star spent 0.148382 s in ordinary placement and recorded 855,808 diagnostic work units; K2,10 spent 0.012771 s and recorded 80,572. Full per-root receipts and repeated state reconstruction are charged costs. No new counter cap or optimization was inserted after these measurements. The complete screen must distinguish useful construction from cost censoring, over-reservation, unavailable coordinated moves and acceptance effects. Preserve every failure and regression; optimal tiny outputs alone provide no class-level improvement claim.
