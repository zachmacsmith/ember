# Isolated deletion closure: implementation and review boundary

The experimental `factored/deletion_closure.py` module is ready for independent
review. It is not called by native, contact refinement or the benchmark runner.
No saved corpus embedding was passed through it during implementation checks.
The earlier 34-input audit and its 43 individual certificates remain unchanged;
they are not composed savings from this module.

`deletion_closure(chains, src_adj, adj, *, deadline=None)` returns a complete
mapping and diagnostics. It requires a valid entry on stable simple undirected
adjacency maps with ordinary integer labels and nonempty list chains. Source
keys need not be consecutive. Initial checks cover source structure, exact
placement, occupied qubits, chain connectivity and every source contact. The
target's full undirected structure remains a caller precondition.

The implementation preserves legacy `spur_prune`'s accepted deletion sequence
when time does not bind: global rounds, sorted source keys, and sorted snapshots
of each chain's sites. Surviving sites retain their original list order. Only
chains with their own deletion in the preceding completed sweep are revisited.
Each proposal independently checks current connectivity and contacts; there is
no endpoint cache or reuse of a stale deletion certificate.

The absolute `perf_counter` deadline covers private copying, source setup,
initial checking and search. Traversals check it per performed work unit;
sorting and Python container operations are cooperative boundaries. Replacement
lists and trace records are prepared before the final commit check. An expired
candidate cannot remove a qubit, and earlier accepted deletions are retained.
Expiry before the complete copy returns the untouched input mapping, explicitly
marked as an alias with `input_validated=False`; no partial copy is returned.
After copying, the returned mapping and lists are private. A future native caller
must retain its final original-graph validation and timeliness accounting.

Diagnostics distinguish attempted deletions from accepted deletions, started
from completed sweeps, and initial validity from closure completion. They save
the complete accepted `(round, source vertex, qubit)` sequence, disjoint phase
wall times, performed copy/setup/adjacency/connectivity/contact work and deadline
overrun. Work categories describe performed operations, not equivalent CPU
instructions. A complete result is minimal under one safe deletion at a time;
it is not a minimum-qubit embedding.

## Focused validation and frozen revision

The guarded final run passed **73 tests** under Python 3.10.19, with zero
attempted MinorMiner or busclique imports. Forty deterministic random valid tiny
minors agree with both unchanged production `spur_prune` and an independent
whole-minor single-removal oracle, including the accepted order. Separate tests
cover order-sensitive cross-chain interference, an earlier articulation that
becomes removable after a later self-deletion, arbitrary integer labels,
unchanged input, invalid entries, all clock interruption prefixes on a fixed
fixture, interruption immediately before commit, and retention of an earlier
accepted deletion. Every returned interrupted fixture is independently valid.

Exact successful invocation:

```sh
.venv/bin/python -B results/codex/deletion-closure-checks/run_tests.py results/codex/deletion-closure-checks/attempt003
```

The harness refuses to overwrite an attempt directory. A repeat must name a new
directory. The saved summary binds the tested source, test, design and unchanged
legacy reference hashes. `attempt001` preserves the initial environment failure
(the isolated native environment lacked pytest); no tests ran in that attempt.
`attempt002` passed the earlier 72-check suite. `attempt003` includes the added
complete clock-prefix check. Its reported 0.46 seconds is tiny-test suite time,
not closure runtime on the corpus or an end-to-end embedding result.

Frozen source SHA-256:
`66a2bc21af6c035ca0b03f9065e2ce780ca0503b9be1af95487eb19e6be67d8b`.
Frozen test SHA-256:
`4fa3e5ede99e471d3ae116ed6607a371cd70cdbc76fc76e4019937c747ef8792`.
Accepted design SHA-256:
`ee63f2fb850c4dc8d5269aff33ceb9d734374e4e1820e36aefa670745d0bc9fd`.

## Remaining limits

Repeated connectivity and contact scans can be expensive. There is no measured
corpus cost, integrated quality result or speed claim. Binding deadlines may
produce different valid prefixes from legacy because skipped scans and initial
checking change elapsed work. The last structural completion check and return
are not one preemptible operation, so `closure_complete` is not a claim that the
whole caller finished before its deadline; wall and overrun remain explicit.
Deletion order may foreclose later relocation, and no such relocation is tested
here. Independent source review is required before any pipeline integration.
