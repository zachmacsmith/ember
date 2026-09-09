# Next A diagnosis: does a guarded connector exist at the blocked state?

**Design only. Retain A061; A062 remains rejected.** The next question should be
whether the inherited insertion procedure misses a small admissible connector,
not which ordering key to try next. The branch stage stays unchanged.

A062 separates three observations. Ordering changes both successful output and
failure occurrence, but the singleton-count proxy did not preserve success.
The new planted failure stops at a local repair limit, not the global work or
wall deadline. Scheduling nevertheless costs 22.136s/31.744M units across calls.
These are respectively evidence about selection, a truncated physical proposal
search, and added cost; none identifies the optimal next row. Early physical
states were not saved, so reconstructing their exact alternative rankings is
not authorized by the receipts. The global branch-set representation can express
valid full minors; that does not establish feasibility with current owners fixed.

Use exactly the three saved blocked lifting states from A062: control planted
34404 seed 1, control wheel 2430 seed 1, and ready planted 34404 seed 0. Exclude the
two native-core failures because an insertion operator cannot act there.
Reconstruct each committed R using its actual processed journal IDs, then remove
only the failed row's created fill privately. Validate the saved E against its
committed R with the existing oracle before considering this private trial R.
No constructor replay or earlier-state inference is needed.

The pinned B004 primitive supplies a concrete distinction: `path()` uses finite
congestion prices and returns one shortest connector to a missing owner;
`cut()` then checks future frontiers. If every ownership cut fails, that root
branch ends rather than requesting another path. Root selection also truncates
64 candidates to four branches. Thus an admissible fixed-owner connector could
be missed through route/root selection even when the final guard is correct.
This is a static observation from
[`frontier_reinsertion_construction.py`](../../packages/ember-qc/src/ember_qc/algorithms/factored/frontier_reinsertion_construction.py)
(`f29cdef9…`), not an assertion that it caused these particular failures.

**Stated reach question:** keeping every placed chain exactly fixed, is there a
nonempty connected free chain of at most three sites for the failed vertex that
realizes all its trial-R contacts and preserves every existing future-port
requirement? Pending means adjacency in full trial R outside `placed ∪ {v}`,
including pending filled requirements. The new chain must also retain a free
neighbor if it has a pending requirement. A site may realize several contacts
for the same new vertex; raw coupler multiplicity does not count as separate
ownership capacity.

One optional exact local diagnostic answers that restricted question:

1. Compute free boundaries of fixed chains. Protect the sole free site of each
   old chain that still has a pending requirement after inserting v. An empty boundary already certifies failure
   with fixed owners.
2. Remove those protected sites from the free target graph. If no remaining
   connected component touches every required chain, save a certificate that
   **no fixed-owner insertion of any size** can satisfy these guards. This is a
   state/neighborhood restriction, not source-minor infeasibility.
3. Otherwise enumerate distinct connected sets of size 1–3, anchored on the
   boundary of the first required owner (canonical order). Check all contacts,
   all old/new future guards and disjointness; independently validate a witness
   against trial R restricted to placed vertices plus v. Stop at the first
   certified witness. If the required-owner set were empty, use every free site
   as an anchor; no special graph-family behavior is introduced.
4. Use one 5s/2M charged-item allowance per state and a 20s process watchdog,
   including setup, adjacency scans, enumeration/copies, certificates and
   publication. A complete enumeration can prove absence only within the
   size≤3 question. Interrupted enumeration is unknown, not negative evidence.
   Preserve all three records once; no selective retry or allowance increase.

This is an optional diagnosis, not an exact optimizer in production. A witness
shows the committed state admits a small fixed-owner insertion that the current
prepare/reconstruction/acceptance path did not publish; it does not alone locate
which internal stage missed it. A protected-component obstruction instead shows
that merely choosing another free route cannot work without prior ownership
growth/reassignment. Neither result proves that the A062 key was good or bad at
an earlier unsaved state. Scheduling time remains a separate measured overhead;
this diagnostic cannot promise to recover it.

Advance only if at least two states, including one rejected control state, have
certified size≤3 witnesses. That would support one general inherited-constructor
hypothesis: enforce the existing future-port exclusions *during* connector
construction, rather than finding a route and rejecting it afterward. It would
replace the corresponding routing rule for all lift insertions, with unchanged
reducer/core/acceptance/branch stage, not add a blocked-only repair cascade or
select among complete outputs. Root would review its exact bounded constructive
policy, then targeted new-risk checks would lead directly to the same diverse
six-structure/two-seed three-arm complete screen. No intermediate tuning gates.

**Self-critique:** three sites is a deliberately narrow reach question; a
negative result cannot rule out longer routes or coordinated old-owner moves.
Protecting only singleton boundaries is necessary but not sufficient: a proposed
chain can consume an entire multi-site boundary, hence the full guard remains
mandatory. Positive local witnesses may not improve an evolving constructor and
can reproduce A062's downstream regressions. Without the stated positive reach
evidence, stop this routing direction rather than try another ordering key,
repair cap or sequence. No code or diagnostic call is approved by this note.
