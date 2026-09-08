# Independent ordinary-adapter review

2026-09-08. **The bounded adapter review passes after two diagnostic-accounting
corrections.** No unresolved candidate-validity or first-return semantics defect
was found. This review covers the adapter and common final gate, not the separate
043 worker/controller, corpus preparation or measured proposal reach.

Reviewed adapter SHA-256:
`7a6b2abaa886bcd5002eced4dde17b277b5d206164fb1ebadfc0e2de0e5cfc30`.
The [accepted specification](ordinary_proposal_diagnostic_adapter_spec.md) is
`7c1a99d3c6c94b2e16ec4b080f77ae6c6d2b5a54f6f58d433a8206d1d65b3210`.
The unchanged ordinary contact source remains
`c6f9a5555b010d5e877b568c1ee760e72d170f1f7e0c186179de16b53630da85`.
All 26 records in the final author manifest pass independent hash readback.

The loader checks and compiles the exact source bytes without a package import
or bytecode-cache lookup. The actual worker must use that bound loader; synthetic
module injection is deliberately available and is not evidence of authorized
runtime provenance. The fixed `qubits_contacts`/greedy path calls no MM,
busclique, alternate proposer or method selector.

The ordinary context, private entry copy and entry validation are shared once.
Every group receives the same entry and its original ordered tuple. Region,
redundancy, routing and internal trial-validation work remain in unchanged
`_repair`; none is cached or removed between calls. Within-group best selection
is preserved. Equal-Q returns are retained as evidence but never become the next
group's input. The first returned strict-Q result ends the batch, including a
result that saves more than one qubit. An invalid positive result stops with an
error; a late positive result is retained but uncredited. Neither causes a search
for a later favorable result.

The shared final gate derives connectivity and contacting owners from original
target edges, not mutable context adjacency. It checks full source coverage,
disjoint nonempty connected chains, every logical edge, strict Q and the allowed
outside-chain equality, then returns private lists. Ownership additionally asks
for exactly one fewer qubit. Raw return time is separate from completion of this
gate and the adapter's final mutation/bookkeeping checks. The existing last-unit
behavior is retained: consuming the last routing unit does not prohibit a timely
valid output; crossing the common deadline does.

Nonpositive result evidence uses selected-chain deltas and a selected-size Q
calculation. This avoids adding a whole-incumbent result scan for every failed
group, and is justified by the pinned `_repair` body's unchanged-outside contract.
A positive result receives a complete mapping delta and independent full gate.
This assumption is scoped to the reviewed source, not arbitrary injected
proposers. Entry, graph topology/order, groups and context are compared at arm
boundaries. Graph attributes are excluded by the declared structure-only input
contract and must remain absent from the actual worker's inputs.

There are real diagnostic costs: ordinary context construction scans/sorts the
whole target; before/after structural snapshots also scan it; the common positive
gate rebuilds target adjacency and contacts from the whole original edge set.
These are a bounded number of per-arm or per-positive-output scans, not newly
added per-group full-graph checks. The existing `_repair` still has its own
whole-owner redundancy and trial-validation costs. All remain in wall time;
ordinary routing expansions do not count them. They must not be equated with
ownership's elementary work meter or omitted from the arm's common deadline.

## Findings and targeted independent execution

Review of the initial adapter `16db9350…` found two accounting gaps. A raising
`_repair` call could have consumed unknown work while `expansions` retained only
the prior returned-record sum. Also exceptional setup, entry validation or gate
work left the named phase at zero and moved its elapsed time into administration.
The source still rejected output correctly; these were evidence errors.

The author preserved the earlier revision and corrected both. `expansions` is
now explicitly the known trustworthy returned-record prefix.
`routing_accounting_complete` and `unaccounted_group_indices` identify missing
counts; `expansions_exact` is null unless the total is known. Setup, entry
validation and final-gate intervals use `finally` so interrupted work stays in
its actual phase. The inspected diff changes accounting and timing wrappers,
not `_repair`, its fixed options or the entry/group trajectory.

Only the identified gaps were executed independently. The stdlib harness uses
a three-site graph facade and stub proposer; it imports neither NetworkX nor an
embedding package and never calls `_repair`, a constructor or corpus input.
Three independent test groups pass:

- Setup/entry-validation/gate exceptions advance a fake clock by 2/3/5 seconds.
  Each duration remains in its correct stage, total wall agrees, and output is
  rejected without caller mutation.
- A trustworthy seven-unit nonpositive return precedes a raising call. The
  second allowance is 13 from the original 20, both calls see the same entry,
  known work remains seven and the exact total is null with occurrence 1 marked
  unaccounted.
- Returned counters `-1`, above allowance, boolean and null preserve the raw
  error records and mark total work unknown instead of claiming zero work.

Evidence is in `results/codex/ordinary-adapter-independent-review/attempt001`;
summary SHA-256
`a0f621ea0b41b0fbecfae969acb79c5cb9ddfdd65c58c2ad62c0ae115c7515a9`.
The source stayed unchanged and all prohibited-import checks passed. No independent
test failed. The author's separately retained iterator-snapshot test failure
predates this review and is not an independent execution result.

The author previously passed 12 groups, including three real tiny public-wrapper
replays, original-edge validity, immutable equal-Q handling, multiple-qubit gains,
ordering, final-clock boundaries and last-unit/global-remainder behavior. After
the correction the author reran six affected groups. Their final test source is
`10a8e9c0d9eb916bb715dfce3a26acfe2ed1c91745b5122793aa7975baf69ee6`;
targeted author summary is
`58561e7966e4593a50c0aa0747f085c32cdd40677e9a7e5aba5bc8871873b138`.
I read this evidence and source but did not repeat that suite. This distinction
limits the independent execution claim; the full unchanged proposer is supported
by the source review and existing reviewed tests, not another broad run here.

The portable focused repeat requires a **new** output directory:

```text
.venv/codex-native/bin/python -I -B results/codex/ordinary-adapter-independent-review/check_failures.py --repo /Users/dabh/ember --out results/codex/ordinary-adapter-independent-review/root-repeat --expected-source-sha 7a6b2abaa886bcd5002eced4dde17b277b5d206164fb1ebadfc0e2de0e5cfc30
.venv/codex-native/bin/python -I -B results/codex/ordinary-adapter-independent-review/verify_author_records.py --repo /Users/dabh/ember --out results/codex/ordinary-adapter-independent-review/author_records_root.json
```

The review manifest binds the note, scripts, raw independent results and final
source/author identities. No production or author-owned file was edited by this
reviewer. Root's separate worker/source freeze and independent lifecycle review
remain necessary before any diagnostic corpus execution.
