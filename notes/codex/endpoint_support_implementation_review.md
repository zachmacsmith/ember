# Independent review of endpoint-support refinement

2026-09-08. The reviewed implementation satisfies the bounded implementation
contract. No unresolved implementation blocker was found. One diagnostic omission
was corrected before the independent execution: distinct incident source edges
are now counted separately from examined source adjacency entries. This is a
correctness and accounting review, not evidence that the policy improves ACL.
No corpus, embedding constructor, MM, busclique or cluster operation was invoked
by this review.

The review covers the [implementation specification](endpoint_support_implementation_spec.md),
SHA256 `03cd87e074c8632c1361b7320e2d7942e5482d00505b138909b57d510501b8eb`,
the [design](endpoint_support_design.md) and [root critique](endpoint_support_root_review.md),
the complete new scorer, contact-refinement changes, and native/pilot boundaries.
The author declared these production bytes stable before execution:

| File | SHA256 |
| --- | --- |
| `endpoint_support.py` | `491682336d4974cbbb1024d4b6c3d9b57a691c9029940d067e0a67868b00a040` |
| `contact_repair.py` | `c6f9a5555b010d5e877b568c1ee760e72d170f1f7e0c186179de16b53630da85` |
| `native.py` | `2aab860de0c6d450b09e24af67c7582619c9818acec257566463b3c7700a4e43` |
| `scripts/codex/pilot.py` | `938da94f320dd66ae509d9e931a56e7b5d9b4db3f263cda6430f63a93307b4bb` |

The first three files are in `packages/ember-qc/src/ember_qc/algorithms/factored`.
Full paths, specification and original reference hashes are retained in
[`source_hashes.json`](../../results/codex/endpoint-support-independent-review/source_hashes.json).
The execution verified those identities before import and after every test group
had completed. No source file was changed by the reviewer.

## Independent evidence

The reviewer-owned [unittest harness](../../results/codex/endpoint-support-independent-review/checks.py)
uses NetworkX only to store tiny supplied graphs. Its mathematical oracle builds
connectivity from the whole target edge list, checks every original source edge,
and constructs both directed support sets by enumerating every physical edge.
It does not call the implementation's ownership overlay, incident scan,
connectivity predicate or redundancy function to obtain its expected scores.

The [successful execution](../../results/codex/endpoint-support-independent-review/attempt002/summary.json)
passed all **nine test groups** in 2.39944 seconds under the pinned native Python,
NetworkX 3.4.2. That duration is test-suite wall time, not an embedding-performance
measurement. The native environment had no importable `minorminer`; a separate
import guard prohibited MM and any busclique module. No prohibited import was
attempted or loaded. The original failed reviewer invocation is preserved under
`attempt001`: it stopped before importing candidate code because this environment
does not install the workspace as an editable package. The corrected harness
explicitly loads the declared source root. This was a reviewer setup error, not
a candidate or benchmark failure.

* **Exhaustive tiny scores:** all 64 simple target graphs on four physical
  vertices, with both possible simple two-vertex source graphs (one edge or two
  isolates), gave 3,162 valid entry embeddings. Every valid replacement that kept
  the unselected chains unchanged was checked for groups `{0}`, `{1}` and `{0,1}`:
  **121,800 scores** agreed exactly with the whole-edge oracle. These included
  101,466 replacements releasing an old selected site and 66,426 transferring an
  old site between selected owners; those overlapping counts are not additional
  independent cases. Owner construction occurred once per scored group, and
  selected-selected incident edges were counted once.
* **Outside-edge cancellation:** 96 further score calls used mixed logical and
  physical labels, four multi-qubit chains, unselected logical edges and changed
  selected ownership. Incident histogram/R differences equalled independently
  enumerated global differences. Graph structures and entry chains were unchanged.
* **Acceptance:** a supplied equal-Q proposal changed directed support `(1,3)`
  to `(2,2)` while reducing raw redundancy by one. It was accepted, with signed
  `R=-1` and histogram delta `{1:-1,2:+2,3:-1}` retained through full-polish
  aggregation. A sequence of complete proposals retained the best current
  histogram, rejected a later candidate that only improved on the entry, and
  rejected a distinct placement with an exactly tied histogram.
* **Strict Q and unknown deltas:** a valid strict-Q improvement committed with
  scoring patched to fail if invoked. A subsequent equal-Q comparison lazily
  scored the new best and proposal; the unavailable original-entry score stayed
  unavailable, so the net R/histogram delta remained null. Interrupting that later
  comparison preserved the earlier valid strict-Q incumbent.
* **Interruption:** a fake clock crossed the actual scorer's deadline check at
  each of its 50 recorded check positions, covering owner setup, source edges,
  overlay, support sets, selected qubits, physical adjacency, histogram and final
  score completion. Four separate histogram-comparison prefixes were interrupted.
  None published a partial score; incomplete ownership was unpublished. A final
  original-graph validation crossing the deadline could not commit or increment
  accepted-update counters. A proposal consuming the last permitted routing
  expansion could still be scored and accepted without adding routing work.
* **Validation separation:** empty/duplicate/unknown/frozen-owned chains and
  absent logical contacts could not produce a usable score. A deliberately
  disconnected chain with valid contacts could produce a contact score, as the
  private collector's contract permits, but the full original-graph validator
  rejected the proposal. A score is never a complete embedding certificate.
* **Legacy replay:** sixteen actual tiny-polish pairs covered both historical
  objectives, both group schedules, and ordinary/direct-singleton/matching-star/
  connected-star settings. Returned embeddings and every non-time diagnostic
  matched the exact pre-edit `contact_repair.py`, SHA256
  `0ce3c2e7f7287a173294190e476a47901d606043970eb46d6ff3f48ba9ec5f97`.
  Only the explicitly named `wall`, `proposal_wall`, `query_wall`, `setup_wall`,
  `refresh_wall`, and `last_refresh_wall` fields were excluded. Limits were
  nonbinding in time. This does not assert identical trajectories at a binding
  deadline.

The author separately retained 56 passing focused checks in
`results/codex/endpoint-support-checks/focused004`, on the same production hashes,
including the actual Z12 supplied witness and native API/error/skip cases. This
review read those tests and their hash-bound result rather than rerunning the
author's full native fixture. Independent evidence above comes from the
reviewer's separately written oracle, fixtures and failure injections.

## Source findings and interpretation

[`endpoint_support.py:57`](../../packages/ember-qc/src/ember_qc/algorithms/factored/endpoint_support.py#L57)
publishes ownership only after completed setup. The overlay releases old selected
sites, permits transfers between selected owners, and rejects frozen ownership.
The adjacency scan inserts both endpoint directions, including endpoints on a
frozen neighbor, while counting selected-selected physical couplers once.
Support sets deduplicate endpoints independently of coupler multiplicity.
The comparison finds the smallest changed histogram bin without a fitted weight,
cutoff, sort-based score or R tie-breaker.

[`contact_repair.py:436`](../../packages/ember-qc/src/ember_qc/algorithms/factored/contact_repair.py#L436)
compares equal-Q candidates to the current best. Strict-Q acceptance requires
full original-graph validity and the final deadline check but no secondary scan.
No lazy score is completed solely to replace a diagnostic null. Per-group cached
scores belong to complete immutable selected-chain lists. The outside mapping is
an internal caller invariant; the private scorer does not independently recheck
every frozen chain on each call. The public path constructs trials by replacing
selected keys only, and validates the complete trial before acceptance.

The old objective branches retain their previous eager redundancy computation
and schema. The new policy is rejected with distance trees, direct singletons,
or either auxiliary star policy, and rejects directed, multigraph or looped
inputs at contact/native boundaries even when refinement is disabled. The pilot
adds one named configuration differing only in the objective parameter; no
constructor, restart, graph-family dispatch or new search portfolio is added.

The missing distinct incident-edge counter was the sole implementation change
requested by this review. `source_adjacency_entries` still honestly counts every
examined neighbor-list entry, including both entries of an internal selected
edge. New `incident_source_edges` counts each admitted undirected incident edge
once. Both include completed partial work. This did not change acceptance,
ownership semantics or routing expansions.

The [041 draft protocol](experiments/041_endpoint_support_protocol.md) correctly
describes a scoring-policy comparison, since lazy ownership and deadline checking
also differ from the eager historical control. It preserves all 34 structures,
35 memberships and explicit missing original Sudoku family, common same-host
budgets, failure accounting and nullable signed deltas. Two interpretation details
were sent to root before freeze: `best_equal_updates` counts accepted within-group
incumbent updates, whereas `equal_size_moves` counts final equal-Q group commits;
`unknown_moves` counts committed groups with an unavailable net delta. A group can
contain both a strict-Q and a later equal-Q update. Also, `interrupted_stage` is
the last recorded stage, not a complete interruption histogram. Setup, score,
comparison and proposal-validation wall counters are separate; initial validation
and remaining overhead still belong to total solver time.

The Z12 counterexample remains a material limitation: a better histogram can
worsen deletion flexibility. Its center minima of one and three concern deletion
of supplied center sites only; unrestricted fixed-leaf relocation permits the
same singleton center in both states. Neither state is claimed to arise from the
bounded proposer or be deletion-minimal. These tests do not show a beneficial
complete-pipeline trajectory, bounded-deadline performance, family superiority,
seed variance or publication-level novelty. The separately frozen all-input
screen must decide whether this implemented policy merits further work.

## Reproduction and review identity

Run once into a fresh, exclusive destination; no pytest is required:

```sh
.venv/codex-native/bin/python -B results/codex/endpoint-support-independent-review/checks.py --repo-root . --reference-root results/codex/endpoint-support-checks/reference --source-hashes results/codex/endpoint-support-independent-review/source_hashes.json --output results/codex/endpoint-support-independent-review/repeat-new
```

The reviewer script SHA256 is
`72e8f4a228755a7fe3f087513ef1370d358473eb7596a0f8b6f1fdff120e0eb9`.
The [review manifest](../../results/codex/endpoint-support-independent-review/review_manifest.json)
binds the script, exact inputs, all successful and failed reviewer artifacts,
this note and the author evidence inspected. The bounded review is complete;
any later source change needs its own identity and appropriate review before
the planned experiment.
