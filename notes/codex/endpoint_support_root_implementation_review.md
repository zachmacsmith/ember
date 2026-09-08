# Root acceptance of the endpoint implementation

2026-09-08. Root read the full scorer, complete contact/native/pilot diff,
author implementation note and full independent implementation review.
The supported experimental path satisfies the reviewed specification.
No static blocker was found; the legacy paths retain their source-level
acceptance logic and are covered by exact non-time replay checks.

The [independent review](endpoint_support_implementation_review.md) establishes
121,800 whole-edge oracle comparisons, affected-edge cancellation, ownership
release/transfer, current-best comparisons, signed and unknown net deltas,
strict-Q acceptance without a secondary scan and cancellation before commit.
It also checks sixteen paired legacy-polish replays. The author preserves
56 final focused tests, 191 regressions before the last test-only addition,
32 detailed old-policy replays, and all failed reviewer/test setup attempts.
These are bounded correctness/compatibility checks, not performance evidence.

The caller keeps outside chains unchanged; the private scorer is not a full
embedding validator. The public acceptance path checks complete original-graph
validity and the common deadline. A strict-Q best need not have a measured
secondary score. Null net deltas and partial signed known totals therefore
must remain distinct in the forthcoming results audit.

Root accepts a separate [041 development comparison](experiments/041_endpoint_support_protocol.md)
after frozen-input/source/environment preflight and target-environment focused
checks. The untouched legacy control and experimental endpoint arm are separate
observations. No output is combined, and no final deletion closure is enabled
in either. The actual-Z12 proxy counterexample, possible scoring cost and
unestablished novelty remain material limitations.

The small pre-edit reference fixtures needed by the new replay tests must be
tracked explicitly despite the general results-directory ignore rule, so a
fresh checkout retains the baseline. Independent artifact hashes and root's
source review bind the exact candidate revision; later cleanup integration
must not mutate the frozen 041 bundle.
