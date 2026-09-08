# Isolated ownership-exchange implementation

2026-09-08. This implements the subsequently authorized isolated prototype in
the [accepted specification](ownership_exchange_implementation_spec.md), SHA-256
`8d870c3a2e16615574ad018eec266258200bd7740b7cbd2450d47a47d299f82f`.
The specification's earlier design-only boundary was superseded by root's
explicit implementation instruction after acceptance commit `e95e8855`.
There is no native/contact/pilot integration or corpus experiment here.

## Behavior and boundaries

[`ownership_exchange.py`](../../packages/ember-qc/src/ember_qc/algorithms/factored/ownership_exchange.py)
imports only the standard library. The API is
`ownership_exchange(embedding, source_adj, target_adj, seed_groups, *, budget, deadline=None)`.
It returns `(candidate_or_none, info)`. A nonempty batch shares one checked
private entry and ownership map. Groups remain in the supplied order; normalization
is lazy, repeated occurrences remain separate, and every group/deletion seed
starts from the same entry. No proposal is internally accepted or cached across
calls. The first timely independently certified candidate ends the query.

The fixed limits remain eight whole chains, 64 original occupied patch sites
including the deleted site, depth eight, four retained children and 256 entered
states per seed. Complete child generation precedes ranked DFS. Exact ownership
signatures include the selected set; minimum entered depth permits shallower
revisits. Hash collisions receive explicit token equality checks. Whole-donor
admission and simultaneous transfer/swap use copied child views; interrupted
children cannot modify their parent, the entry, or the caller's lists.

The final certificate independently rebuilds ownership and checks every source
contact, chain connectivity, exact whole-entry-chain patch union, outside equality,
the surviving patch partition, permanently absent deletion site, and `Q_entry−1`.
It does not trust the incremental deficit set. Full candidate and trace preparation
finish before the last publication reservation. Using the last work unit is legal.
A final deadline check also includes stack unwinding and diagnostic finalization;
late rejection retains certificate status but returns no candidate and reports
the last observed elapsed time.

Source and target must be stable simple undirected loopless graphs with ordinary
integer labels. The module checks source symmetry and occupied target rows;
unused target structure remains a caller precondition. Detected malformed input
returns `invalid_input`; malformed budget/deadline scalars raise `ValueError`.
An empty group sequence does not copy or validate an embedding.

## Costs and diagnostic interpretation

Entry and full-certificate contact checks accumulate contacting owner pairs in
one occupied-target-adjacency scan, then visit each source adjacency entry once.
They do not scan a chain again for each logical neighbor. Connectivity and touched
row checks add separate linear scans. Thus ordinary validation scans cost
`O(Q Δ+n+m)`; charged source-label ordering adds sorting work. Selected-state
checks cost `O(p Δ)` scan work with `p≤64`; frozen-neighbor boundary walks can be
much larger. No measured runtime advantage follows from these bounds.

`work_total` and the disjoint `work` categories equal the live budget's expansion
delta, including setup, rejected descriptors, comparisons, copies, hash/equality
tokens, validation and failed attempts. Merge sorting charges comparisons and
item reads/writes. Group, seed and generation work intervals are **nested** and
must not be summed together. `stage_wall` is exclusive and sums to query wall;
it includes checkpoint/bookkeeping overhead. Python primitives and deallocation
remain cooperative, not a hard real-time guarantee.

Group and seed indices are zero based. `groups_inspected` means normalization
finished; `groups_completed` counts visits that finished without returning a
candidate. A successful return stops a seed/group early, so their `complete`
flags do not claim exhaustive traversal. Use their explicit return reason and
the separate certificate/return flags. `generated_feasible` can be positive when
generation was interrupted and no certificate was attempted. `proposal` can
retain certified metadata after a final return-time deadline rejection;
`candidate_returned=False` and `q_after=None` then remain authoritative. Unknown
partial stages stay null. Neither restricted exhaustion nor a cap proves that
no useful contraction exists.

## Author checks and preserved failures

The guarded command is:

```text
.venv/bin/python -B results/codex/ownership-exchange-author-checks/run_checks.py results/codex/ownership-exchange-author-checks/<new-attempt>
```

Each attempt snapshots the source/spec/tests and refuses an existing output
directory. The final author run, `attempt004`, passes **38 tests** in 1.34 seconds
of suite time, with no prohibited import attempts and unchanged source hashes.
This is correctness-test time, not an embedding-speed comparison.

The fixed six-source witness returns the intended two swaps, reducing seven
occupied sites to six in 1,527 work units. Every allowance from zero through
1,526 returns no candidate; exactly 1,527 units permits the certificate. Another
580 interrupted complete-generation prefixes preserve their parent and entry,
including 536 prefixes after a whole-owner admission was staged. Six independent
complete-child/rank comparisons cover four qualifying four-site targets and
the two fixed larger witnesses. Other checks cover batch restart and order,
the connected-patch exclusion, missing free-site escape, whole-donor site/chain
caps, hash collisions, false incremental deficits, and deadline publication.
These are arbitrary-target toy facts, not Zephyr or benchmark results.

`attempt001` had 33 passes and one test-only failure: its original domain produced
six qualifying oracle cases, while an unjustified assertion demanded at least
ten. No child or validity comparison failed. `attempt002` temporarily broadened
the tiny source domain and passed 34 tests; those bytes remain preserved. Root
correctly required keeping the intended domain rather than satisfying a quota.
The final test restores that domain and asserts its exact six cases. `attempt003`
passed 37 tests after the final-clock diagnostic check; `attempt004` adds the
direct interrupted-parent checks. No search rule or parameter changed from these
outcomes. Frozen attempts and the final manifest preserve the complete sequence.

Self-critique: full generation and repeated private child copying may spend the
allowance before a promising child is entered; sharing entry setup does not
establish useful amortization. Occupied-only exchange deliberately excludes
free-site routes and some remote swaps. Fixed limits and conflict choice exclude
other feasible assignments. The prototype demonstrates neither novelty nor
better final ACL; independent oracle review and a separately authorized mechanism
comparison are still required before any integration decision.

Frozen core SHA-256: `015781019833ee5a3f49dcec5a189161104003224b1327b44cedda6e084532bb`.
Frozen tests: `6654d95dd6cf6ef561c5d901b6088f41a3072b5553700e77814ada1c17516b03`.
