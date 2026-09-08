# Independent review of isolated deletion closure

2026-09-08. No blocker found for the stated valid-input, stable simple-undirected
adjacency contract. This is a correctness review of an isolated module, not
approval of native integration or evidence of corpus quality/runtime benefit.
No author source/tests, native, pilot or frozen experiment was edited.

Reviewed module SHA256:
`66a2bc21af6c035ca0b03f9065e2ce780ca0503b9be1af95487eb19e6be67d8b`.
The [accepted design](deletion_closure_design.md) has SHA256
`ee63f2fb850c4dc8d5269aff33ceb9d734374e4e1820e36aefa670745d0bc9fd`;
the [author implementation note](deletion_closure_implementation.md) inspected
here has SHA256
`923668e66c7bc580dae8ca8238ff49ef0a638dacfcb6a4287221f0216689c5c3`.
The author's 73 checks are separate evidence and were not rerun as this review.

## Why skipping unchanged chains is sound

Suppose deleting q from C_u failed during a completed sweep in which C_u did
not change. Every current site was considered in sorted order unless the chain
was already a singleton. Later deletions in other chains leave both nonemptiness
and connectivity of C_u minus q unchanged. They can only remove contacts from
that remainder, never create a missing contact. Thus the failed deletion cannot
become safe while C_u stays fixed.

Only a deletion within C_u can therefore make one of its earlier failed sites
newly removable. Retaining exactly the chains changed by their own preceding
sweep revisits every such possibility. There is no certificate reuse for a
proposed deletion: `_connected` and `_covers` check the current remainder against
current neighbor chain sets immediately before preparing its replacement.
Neighbor deletions can make a formerly safe proposal fail, which is why this
fresh check is necessary.

Induct on global rounds and then on the sorted chain/site visits. The optimized
and legacy states start equal. An omitted chain sweep consists entirely of
failed tests by the monotonicity fact; it cannot change state. Each retained
candidate is tested in the same state, so its acceptance, surviving list order
and `(round, source vertex, qubit)` record agree. Both advance to another global
round precisely when at least one deletion occurred. For nonempty inputs the
completed round counts agree as well. Empty inputs have the same empty result
and accepted sequence, although the optimized code starts no round.

At completion every chain has had an unchanged final sweep or is a singleton;
subsequent neighbor shrinkage cannot make its rejected deletion safe. The result
has no safe single-qubit deletion. This is not a minimum-Q minor-embedding claim
and does not restrict later relocation, transfer or growth.

Termination follows from strictly decreasing Q on acceptance: at most Q0−n
deletions and, for nonempty inputs, at most Q0−n+1 global rounds. Across all
rounds, chain u is swept at most its initial length L_u times. This bounds
candidate attempts by the sum of L_u squared, but each attempt can still scan
the chain and its incident contacts. A loose per-attempt bound is
O((1+d_u)L_u*Delta), for source degree d_u and maximum target degree Delta.
Skipping failed sweeps supplies no speed guarantee; new initial checks and
repeated connectivity/contact scans are real costs.

## Independent execution

The portable verifier is
`results/codex/deletion-closure-independent-review/verify.py`. It imports only
stdlib modules and a hash-bound private copy of the candidate file. An import
guard rejects Ember, scientific graph packages, MM and busclique. No candidate
helper is used by the oracle: full validity is checked from the original
undirected physical edge set, and each reference deletion receives a complete
minor validation under unoptimized global sweeps.

The exhaustive domain includes all 64 simple target graphs on four sites,
source edge versus two isolates, all three-way site assignments (first chain,
second chain, unused), and every permutation of each nonempty assigned list.
Source and target labels are nonconsecutive Python integers, including negative
values. Mapping keys are inserted in reverse numerical order to distinguish
input order from the prescribed sorted sweep order.

Of 10,368 occupancy/source/target combinations, 3,162 are independently valid.
Their list permutations produce **7,464 candidate calls**. Every call agrees
exactly with the reference final lists, dictionary key order, accepted records
including chain sizes, and completed global rounds. Every final embedding is
valid and independently checked against every possible single deletion.
The records contain 9,936 accepted deletions and 5,760 skipped failed chain
sweeps across these tiny cases. These are exhaustive-test totals, not corpus
savings or performance measurements.

The two-variable domain cannot exercise multiple logical obligations. Two
additional fixed four-site/three-variable cases check a center with two frozen
neighbors: one must retain both sites; adding one actual contact makes exactly
one deletion legal. Both agree with the full-minor reference. No graph label or
architecture metadata enters the candidate or the oracle.

Two order-sensitive fixtures then cover **190 individual checkpoint
interruption positions**, including every pre-commit check (four total) and two
second-commit interruptions retaining an earlier accepted deletion. Every
returned mapping equals the corresponding independently reconstructed valid
reference prefix. Original chains and both adjacency maps remain unchanged.
Expiry during the 14 private-copy checkpoints returns the original complete
mapping, never a partial copy. After `copy_complete`, returned lists are private;
initial-check and closure-completion flags match the reached boundaries. Partial
operation counters never exceed the corresponding completed-fixture counts,
and the phase times sum to the reported wall time.

Two final-bookkeeping clock cases deliberately cross the absolute deadline
after the final structural checkpoint. They correctly retain
`closure_complete=True`/`stopped_reason='closed'` while reporting an overrun of
1 second. Therefore closure completion is **not** a timely-caller certificate.
A future native caller must retain its independent final validation, elapsed
time and overall timeout classification.

`attempt001` passed the exhaustive and interruption checks. `attempt002` adds
the two degree-two cases; it also passes, with source hash unchanged and no
prohibited imports. No failed candidate case was found. All earlier artifacts
are retained. The final audit took approximately 0.87 seconds in the recorded
environment; this is verifier duration, not a closure or embedding benchmark.

## Limits and integration boundary

Full stable, symmetric, simple, loopless target adjacency remains the caller's
precondition. Initial checking does not certify every unused target edge or
replace a graph-normalization/architecture contract. Source coverage, chain
membership/disjointness, source symmetry, connectivity and contacts are checked
before an accepted deletion. An early `input_validated=False` return is not a
validity certificate for an arbitrary invalid caller input.

Atomicity here concerns the module's cooperative expiry checkpoints. Copying
and replacement construction finish privately before publication; no expiry
checkpoint separates the consistent commit updates. This does not promise
thread safety, persistent output after process termination, or preemption of a
Python sorting/container primitive. Binding deadlines may produce a different
valid prefix from legacy because initial checks and skipped scans change timing.

The exhaustive domain is finite and mostly has source degree at most one; the
two extra cases and static argument extend coverage but are not exhaustive
proofs over arbitrary inputs. No corpus embedding, constructor, native call or
cluster action was executed. The module contains no graph-family dispatch,
random choice, alternative solver or reconstruction. Deletion cleanup is an
established operation, not a novelty claim. Any integration and full-pipeline
comparison remain separate work requiring root acceptance; experiment 041 and
the endpoint control/treatment remain unchanged by this review.

## Artifacts and safe repeat

Full inputs are defined by the saved protocol and per-case chain lists. Raw
successful cases are in `attempt002/cases.jsonl`; interruption states and all
performed counters are in `interruptions.json`; the additional cases are in
`multiple_neighbors.json`. `summary.json`, `invocation.json` and `manifest.json`
bind the complete run. The separate review manifest binds these artifacts, this
note, the candidate and verifier hashes.

From the repository root, choose a fresh output directory:

```sh
.venv/codex-native/bin/python -I -B results/codex/deletion-closure-independent-review/verify.py results/codex/deletion-closure-independent-review/root_repeat
```

The verifier refuses existing directories and uses no third-party dependency;
another compatible Python interpreter may run the same command. Its recorded
source hash must match the reviewed revision before and after execution.
