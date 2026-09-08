# Independent review of the induced-star singleton core

2026-09-08. No integration blocker found in the frozen core. The independently
implemented original-graph oracle agrees on all **96** added tiny cases, including
**89,280** injective assignments. All **4,494** work/deadline prefix checks return
only certified strict-qubit improvements or no proposal. This clears a bounded
correctness gate; it establishes neither runtime competitiveness nor cumulative
benchmark gains. The connected-center extension remains design only.

This review follows the
[implementation specification](induced_star_implementation_spec.md),
[prior mathematical review](induced_star_relocation_review.md), and
[integration review](induced_star_integration_review.md). The reviewer did not
change implementation, focused tests, scheduler, native entrypoint, or benchmark
configuration, and ran no constructor or full embedding pipeline.

## Frozen sources and independent verifier

| Artifact | SHA256 |
| --- | --- |
| `induced_star_relocation.py` | `785a1ab9f88d8ec6454029fe648b5d62213063f17d4933bdadbef336602c965a` |
| `test_induced_star_relocation.py` | `ca23428c08bcebb77040c097ef73756f5f3cd5ded00b9392d7a63c72912fd0ba` |
| Independent `verify.py` | `4affbb9df1c1c78e18ccccbaa30175deff6aba9d1935e03fd59a6e55bc8c3146` |

Copies, source provenance, the verifier, all generated inputs, and complete
results are preserved under
[`results/codex/induced-star-core-review`](../../results/codex/induced-star-core-review).
The verifier imports the frozen core as a standalone module. It rejects
`minorminer`, `busclique`, and package-level `ember_qc` imports; source and target
adjacency, validation, coupler counts, and exhaustive assignment enumeration are
implemented independently using the standard library. It imports neither the
production contact context nor its validator. The frozen core itself imports
only `collections`, `dataclasses`, and `time`.

The implementation agent reported 139 guarded combined tests passing; root
independently reran the 85 focused new tests and verified the same hashes. This
review adds the missing varied frozen-center and larger-block oracle coverage
instead of interpreting those existing fixtures as comprehensive evidence.

## Certificate and root completeness review

For a validated incumbent on simple, undirected, loopless graphs, the fixed
selected induced star leaves only three kinds of obligations: singleton
availability, adjacency from each selected leaf to its center, and selected-to-
frozen contacts. The domain masks encode availability and every frozen contact
against actual target adjacency. Their actual-degree filter is necessary for
a singleton image. Selected old owners are removed from the frozen-contact set.

The one-hop stream from a frozen center neighbor contains every feasible center
site. The two-hop stream from a frozen leaf neighbor does also: every feasible
leaf site must be a fully eligible intermediate adjacent to its frozen neighbor,
and the feasible center must neighbor that leaf site. Thus pruning such
intermediates by their complete eligibility cannot remove a feasible complete
replacement. With no frozen obligations, the target's context order is a complete
root stream. First-discovery deduplication changes repeated work, not root
coverage. The minimum-estimate seed uses fixed hop/logical-rank tie breaks;
neither seed selection nor the masks consult graph-family metadata.

The augmenting-path matcher uses logical positions on its left and physical
labels on its right, preventing accidental partition merging. It processes
most-constrained leaves first and restores earlier assignments through alternating
paths. Failure to augment for a processed leaf proves that the processed prefix
cannot be covered, so later leaves cannot repair full-block feasibility. Extra
physical leaf–leaf edges are harmless; actual logical leaf–leaf edges reject the
selected block before matching.

Before returning a map, `_certificate` checks membership, distinct new sites,
released versus frozen ownership, every old and new selected incident logical
contact, and exact old/new incident coupler redundancy. Internal selected edges
are counted twice and divided by two; external edges are counted once. Strict
qubit descent permits a negative redundancy change. The unchanged outside
embedding supplies connectivity and source contacts outside the selected block.
The local certificate requires the caller's valid-incumbent and immutable-cache
contract; it is not a replacement for validation of an arbitrary input embedding.

## Added exhaustive cases

The added fixtures use deterministic seeds 0–95 with a recorded generation rule.
There are 48 selected blocks with three leaves and 48 with four. Target sizes
are eight, nine, and ten vertices (24, 48, and 24 cases respectively). Every case
has a two-qubit center initially, a two-qubit frozen chain, frozen occupied sites,
and an unchanged logical edge between the two frozen source vertices. Additional
target edges and leaf-to-frozen obligations vary; some selected leaves also
start with multiple qubits.

All 96 centers have frozen obligations: 64 have one frozen center neighbor and
32 have two. This explicitly exercises one-hop seed streams. The verifier first
validates each constructed incumbent independently. It then enumerates every
injective assignment of the selected logical vertices to all physical sites
available after release, merging each with the unchanged outside and checking
the full original graphs. These are synthetic correctness fixtures; their
existence or distribution is not benchmark evidence.

There are 58 feasible fixed-block replacements and 38 infeasible cases. The
untruncated core returns 58 certified proposals, rejects 16 cases by the proved
singleton degree bound, and exhausts its root stream without a matching in the
remaining 22. There are zero oracle disagreements. Every returned map also has
independently verified source coverage, chain membership/disjointness,
connectivity, source contacts, positive Q savings, and exact redundancy deltas.

The public `StarSearch` wrapper greedily selects its own block, which may differ
from the declared three/four-leaf block. The verifier separately enumerates that
selected block whenever it is formed, and compares every completed wrapper
decision to the corresponding oracle. Outcomes are 44 accepted proposals,
33 complete no-match decisions, 16 center-degree exclusions, and three
insufficient-leaf exclusions. Different feasible counts between the wrapper
and the fixed-block queries reflect this deliberate subset rule, not an oracle
mismatch. Maximum observed query work is 216 units directly and 264 through
selection plus the wrapper; maximum wrapper setup-plus-query work is 280.
These small counts do not estimate Z12 query cost.

## Work, deadline, cache, and interruption review

`_SharedBudget` charges query work into the active visit, the whole-call auxiliary
allowance, and the query ceiling exactly once. Owner setup and refresh have no
2,048-query cap, but still use the active visit and the same auxiliary allowance.
Per-query stage totals reconcile with work, and the wrapper's reported new work
excludes already performed ordinary work. The existing focused tests exercise
the 2,048-unit truncation and owner setup larger than that limit; the added tiny
fixtures do not reach it.

The new verifier checks every work prefix on eight predeclared fixtures and
varied deterministic prefixes on the others. Each prefix is tested twice: once
as a work limit and once as a simulated deadline reached at that charged-work
position. Across 4,494 calls, no counter exceeds its limit, no incomplete output
is published, no original chain or valid owner map changes, and every returned
proposal independently validates. Completely finished work exactly at its work
cap may return a certificate; an observed deadline still forbids it. Simulated
prefix deadlines test interruption semantics, not real-time latency. The
existing focused test separately exercises an actually expired clock deadline.

An accepted ordinary shortening of the multi-qubit frozen chain is also checked
on a complete tiny target. Refresh removes the released physical owner and
publishes the new incumbent identity; the next proposal uses the refreshed
frozen contacts and agrees with a newly enumerated oracle. Every refresh work
prefix and simulated deadline boundary preserves both immutable embeddings.
Interrupted refresh leaves the cache invalid, and a subsequent direct query
rejects it as stale. Existing focused tests additionally cover ownership transfer
between selected vertices, setup interruption, identity mismatch, no rebuild
after disablement, and lazy no-cache refresh.

The source relies on immutable incumbent maps and chain lists, not deep hashes
on every call. In-place mutation with unchanged identity violates the internal
contract and is not detected universally. The integration must preserve that
contract and refresh after every accepted ordinary or star move. No proposal
can rely on a partially refreshed cache.

## Remaining integration conditions and diagnostic distinctions

The following are requirements already in the saved integration design, not
requests for a new search policy:

- Preserve the existing common deadline and remaining active-group/global work.
  Work charged through the adapter must not be charged again from returned
  descriptive counters. There is no fresh group or auxiliary allowance per
  attempted center.
- Recheck the deadline before committing a returned proposal, then record actual
  committed savings. Core finishing/bookkeeping occurs after its final internal
  certificate check, so returning a certified proposal is not permission to
  ignore a deadline reached before the scheduler commits it.
- Keep the graph-kind and initial-embedding validation requirements at the
  public boundary. The standalone core assumes these conditions; its context
  does not retain enough graph-kind information to re-establish them itself.
- Preserve off-policy behavior and refresh or invalidate ownership after every
  accepted ordinary move. Query masks are local to the selected block and cannot
  be cached across commits.

`complete_proposals` increments when a covering matching is found, before the
final certificate and returned-map construction. It may be positive on a
truncated query. `move['accepted']` and the search's `certified_proposals` count
fully certified returned proposals, but those still precede the scheduler's
commit. Report these three stages distinctly; none of their counts alone proves
comparative qubit improvement.

The mathematical certificate is exact for the chosen singleton block, while
root truncation and greedy leaf selection limit search coverage. Future
cumulative comparisons must retain failed, skipped, and zero-gain cases and
all setup, displaced-work, and elapsed-time costs. The current review authorizes
no generalized connected-center implementation and makes no novelty claim.

## Safe additive reproduction

```sh
.venv/codex-native/bin/python results/codex/induced-star-core-review/verify.py results/codex/induced-star-core-review/root_repeat
```

Use a fresh output directory if that name already exists. The script checks
the frozen source hashes and writes new input, observation, refresh, and summary
artifacts without modifying originals. The saved 3.94-second elapsed value is
the duration of this oracle audit, not a solver runtime comparison. All 96 input
records, every fixed-block oracle result, prefix outcome counts, and refresh
checks are retained in the original `final/` directory. The review manifest
records their hashes and the note's identity.

Status: core review complete, with no blocker under the stated internal contract.
Scheduler integration still requires its own independent review before the
cumulative experiment.
