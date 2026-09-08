# Deletion after contact refinement: conditional design and critique

2026-09-08. Mathematical design only, written before the independent final
deletion audit returns. No integration or embedding call is made by this note.
The [saved-output audit](final_deletion_audit_design.md) will determine whether
this omission is observable in the current development control. The production
native path at commit `c61c474ca7bdd2f6e455cfa67f34af72b8d537cf` prunes before
contact refinement and performs only validation afterward. The generic
`polish()` function's final pruning pass is not on that path.

## Why a final pass might help

A group reconstruction can change which physical sites on its frozen neighbors
carry contacts. It can also make an earlier reconstructed member redundant when
a later member is placed. Complete minor validity does not imply that every
qubit is necessary. A final deletion closure would consume one evolving valid
embedding and remove individually unnecessary sites; it is neither another
embedder nor a choice between independently generated results.

This operation is established cleanup, not a novelty claim. Its potential value
is actual Q reduction at a modest measured cost. Individually removable-site
counts are only diagnostic: several safe individual deletions need not coexist.

## A useful monotonicity fact

Fix a chain C_u and a candidate q in C_u. If deleting q is unsafe, shrinking
other chains through valid deletions cannot make that same deletion safe while
C_u itself remains unchanged. Nonemptiness and connectivity of C_u minus q are
unchanged. For every logical neighbor v, shrinking C_v can only remove physical
contacts from C_u minus q; it cannot supply a missing one.

Consequently, only a deletion within C_u can create a newly removable site in
C_u. Such a deletion can remove a branch and turn a former articulation into a
non-articulation. Deletions elsewhere may invalidate a previously safe deletion,
so safety must still be rechecked against current chains immediately before
commit. The statement assumes a valid minor, fixed logical/physical graphs and
deletion-only updates; it does not apply across relocation, transfer or growth.

One possible efficient closure processes chains in a fixed order, repeatedly
deleting safe sites in the current chain until none remain. A later chain's
deletions cannot reopen an earlier closed chain. The final state is therefore
minimal under single-qubit deletion, but not necessarily minimum-Q.

That chain-at-a-time order is **not** guaranteed to match the existing pruning
routine. The old routine interleaves a single sorted-site sweep over every
chain, then repeats the global sweep. Competing contact deletions can make
different orders choose different surviving sites or different final Q.

A separate optimization can preserve the old nonbinding sequence: after each
global sweep, revisit only chains that themselves lost a site during that
sweep. Skipping other chains skips only failed deletion attempts by the fact
above. Keep the old sorted chain and site order within every remaining sweep.
This should preserve the accepted deletion sequence under nonbinding deadlines;
binding deadlines can still change the returned valid prefix. It needs an
independent replay test before that claim is made about code.

## Conditional implementation boundary

If the saved-output audit finds no safe deletion on all 34 control outputs,
do not add a final closure on this evidence. Preserve the negative finding.
If it finds opportunities, specify one fixed cleanup policy in a separate
experimental option and compare full pipelines under the same absolute deadline.
Do not silently add it to either arm of the endpoint-support experiment.

Use deterministic order, connected nonempty chains, actual original-graph
contacts and a check immediately before each commit. A deadline interruption
returns the last certified state; copying, ownership/support construction,
connectivity work and final validation remain inside the common allowance.
Report phase time, attempted deletions, accepted deletions and incomplete closure.
Do not equate an interrupted closure with a minimal embedding.

Direct support sets and chain articulation checks could reduce repeated work,
but persistent support bookkeeping must update both directed endpoints after
each physical deletion. An endpoint on a neighboring chain loses support only
after its final coupler into the shortened chain disappears. Counting couplers
as distinct supporting sites is incorrect. Start with a clearly checkable
implementation; optimize only with measured need and exact oracle agreement.

## Self-critique before any implementation

This cleanup can save nothing, consume time needed by refinement or validation,
and create additional timeouts. Deletion order can remove useful alternate
contacts and foreclose later relocation; using it only at the end limits that
interaction but does not remove the deadline tradeoff. Adding cleanup after
refinement cannot recover quality lost by the constructor's placement choices.
The subset-minimal result has no approximation guarantee for minor-embedding Q.

Any final-pipeline gain needs all-input validity/timeliness accounting and a
fixed control; applying cleanup offline to cached outputs alone is not a solver
benchmark. It is a development hypothesis and no evidence about new graph
instances, seed variance, Pegasus, Chimera or superiority over MM.

## Accepted isolated implementation contract

Root authorized this module only after the independent audit found individual
deletions on 13 of 34 controls. That outcome does not select a deletion order or
authorize native integration. The frozen diagnostic records remain unchanged.

API: `deletion_closure(chains, src_adj, adj, *, deadline=None)` returns
`(embedding, info)`. Source and target labels are ordinary Python integers
(excluding booleans); source keys may be nonconsecutive. The input is a full
valid minor for stable simple undirected loopless source/target adjacency maps,
with nonempty list-valued chains. No algorithm, random choice, external solver
or new parameter is called. `deadline` is an absolute `time.perf_counter()`
timestamp, matching native. Nonfinite/non-numeric deadline values are rejected.

The caller must supply a valid entry. The module checks source coverage, chain
membership/disjointness, initial connectivity and original logical contacts
before accepting any deletion. Source adjacency is normalized once with integer,
loop and symmetry checks. It does not certify every unused target edge: the
target's stable undirected adjacency remains a caller precondition. Input lists
and adjacency maps are never mutated.

Copying is interruptible. Before a complete private mapping exists, expiry
returns the untouched **original mapping**, which may therefore alias the input,
with `input_validated=False` and `closure_complete=False`. A partial copy is
never returned. After copying, expiry returns the complete private mapping;
all its accepted deletions already preserve the caller's valid entry. If initial
checking is interrupted, `input_validated` remains false. This convention does
not certify a caller-supplied invalid input and requires future native callers
to retain their original final validation and timeliness reporting.

Visit chains in sorted source-key order. Within each active chain, visit a
sorted snapshot of its current sites once, applying successful deletions
immediately. Preserve the original list order of surviving sites. Repeat global
rounds, retaining only chains that deleted at least one of their own sites in
their preceding completed sweep. A chain-at-a-time fixpoint is explicitly not
this policy. Singleton chains need no attempt. Stable initial/current chain sets
support connectivity and contact tests; there is no persistent endpoint cache.

A candidate must leave a nonempty connected chain and a physical contact to
every current neighboring chain. Build the replacement list and diagnostic
record privately, check the absolute deadline immediately before committing,
then update the mapping, its chain set and acceptance record without another
cancellable checkpoint between those operations. Connectivity traversals,
adjacency scans, copying, source setup, initial validation, sorting boundaries
and record preparation all check the same deadline. Python container primitives
and sorting are cooperative boundaries, not preemptible hard deadlines. No
time is subtracted from the caller's allowance, and no interrupted candidate
supports a commit. An earlier accepted deletion survives later interruption.

Diagnostics: initial-check completion, private-copy completion, closure
completion, stopped stage/reason, total wall/deadline overrun, disjoint phase
walls, performed copy/setup/initial-validation/deletion/connectivity/contact
work, attempted and accepted deletions, completed rounds/chain sweeps and the
ordered accepted `(round, source vertex, qubit)` sequence with chain sizes.
Counts include performed partial work. A completed closure has no remaining
safe single deletion; it is not a minimum-Q or approximation certificate.

Before independent review, require tiny original-graph oracles, randomized
valid fixtures and nonbinding replay against the unchanged production
`spur_prune`. Independently reconstruct the legacy accepted sequence using
whole-minor single-removal checks. Include conflicting cross-chain contacts,
an earlier site that becomes non-articulating after a later self-deletion,
arbitrary integer labels, input immutability, empty graphs, invalid inputs,
expiry during copy/setup/connectivity/contact/commit preparation, and retention
of the last valid accepted prefix. No saved corpus embedding is passed through
this module during implementation tests. Root independently reviews source,
tests and accounting before any pipeline change.
