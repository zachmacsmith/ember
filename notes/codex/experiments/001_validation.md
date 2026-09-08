# Experiment 001: make embedding validation authoritative

Date: 2026-09-07 (America/Chicago). Branch: `codex`. This is benchmark correctness work after plan approval, not an embedding-algorithm experiment or performance claim. Changes contain no graph-family or graph-ID-specific behavior.

## Problem and hypothesis

The audit reproduced two false certifications: `evaluate()` accepted an extra source key, and `benchmark_one()` accepted K3 singleton chains on a path target when the algorithm supplied a denser `chimera_graph`. A foreign singleton target vertex could bypass structural checking. Metrics were computed before public evaluation validated the result. A solver could also modify the graph objects supplied by the runner, changing the problem later used for validation.

The hypothesis is that a complete structural predicate, checked against the original problem before scoring, rejects these outputs while preserving valid embeddings, isolates, arbitrary hashable labels in the mathematical API, and normal benchmark serialization.

## Changes

- `validation.py`: Layer 1 now independently checks mapping format, exact source keys including isolates, finite nonempty chain collections, original target membership even for singleton chains, connectedness, disjointness including duplicate entries within a chain, and every source-edge contact. It no longer requires Layer 2 to establish mathematical preconditions. Layer 2 retains the benchmark's stricter integer-ID/list-chain serialization contract and rejects malformed outer containers without raising an incidental exception.
- `benchmark.py`: `evaluate()` validates first and returns zeroed quality fields for invalid outputs. The `validate=False` keyword remains accepted for call compatibility, emits `DeprecationWarning`, and cannot bypass checking. Its `valid` result is now an actual Boolean. ACL uses total used qubits divided by the source vertex count after exact coverage has been proved.
- `benchmark_one()` passes structural graph copies to the algorithm and validates against the caller's original source and target. Algorithm-returned `chimera_graph` is ignored as a validation authority. Success follows complete structural validity and the measured deadline, not the algorithm's success/partial/status flags. A legitimately incomplete timeout remains unsuccessful.
- Returned results whose externally measured `embed()` wall time exceeds the declared timeout are classified `TIMEOUT`. A structurally valid late embedding is preserved with `is_valid=True` for diagnostics, but `success=False`, empty chain-length metrics and zero credited quality totals. Algorithm-reported elapsed time cannot conceal an overrun. Results returned exactly at the deadline remain eligible.
- `{}` is valid for an empty source, using ACL/max-chain zero as an explicit reporting convention. `None` remains invalid. This agrees with the independently repaired backend validator. Empty-source rows are not ACL observations for nonempty graph instances.

Metrics on unsuccessful rows remain zero only to preserve the existing result schema; analysis must filter by timely success and must not interpret those zeros as good ACL. In particular, a late valid result's `is_valid=True` is a statement about its mathematics, not successful completion within budget.

## Timing boundary and compatibility

The existing runner timing boundary remains the call to `embed()`. Runner-owned structural copies occur before that timer; graph loading and post-return verification also remain outside it. Algorithm-specific initialization, internal preprocessing, construction and repair performed inside `embed()` remain charged. This change does not introduce a new watchdog or terminate an in-process solver; it prevents returned late outputs from being credited as timely results. The parallel runner's existing hard cap is still an operational safeguard, not extra credited search time.

Previously accepted invalid `evaluate()` outputs no longer retain apparent quality statistics. Explicitly disabling validation no longer does so. A valid returned embedding with `success=False` now counts as success if it arrived on time; a purported success arriving late now counts as timeout. Those are intentional corrections to the trust boundary. Graph copying isolates adjacency structure; it does not promise a deep copy of arbitrary mutable nested metadata.

The low-level `compute_embedding_metrics()` helper lacks a source graph, so it cannot certify an embedding. Its documented precondition is an already validated embedding; public evaluation and benchmark ingestion enforce that precondition.

## Verification

Focused suite:

```text
.venv/bin/python -m pytest tests/test_evaluate.py tests/test_codex_validation.py tests/test_registry.py -q
77 passed, 1 warning, 0.50 seconds
```

The warning is the installed dwave-networkx deprecation notice. Tests cover extra/missing keys, isolates, empty and malformed chains, foreign singleton and longer chains, unhashable vertices, repeated/overlapping qubits, disconnected chains, missing logical contacts, original-target substitution, source/target mutation, misleading success metadata, the empty-source convention, and deadline enforcement using a deterministic clock. Tests intercept metric computation so rejected or late outputs cannot silently be scored.

A short existing ingestion/export smoke check was also run before adding deadline enforcement:

```text
EMBER_UNFINISHED_DIR=/private/tmp/ember-codex-validation-staging .venv/bin/python -m pytest tests/test_smoke_pipeline.py -q -k 'not reference_snapshot'
16 passed, 1 failed, 1 deselected, 1 warning, 3.56 seconds
```

The failed existing test expects `runs.csv`. The unchanged `compile_batch()` implementation writes SQLite and returns without producing that file; the batch did contain the required database, rows, embeddings, worker JSONL and summary checked by the other 16 tests. No exporter/source outside this assignment was changed to satisfy that unrelated expectation. The historical reference-snapshot test was deliberately excluded because this check targeted ingestion/storage, not old numerical baseline agreement. This result is not reported as a completely passing integration suite.

`git diff --check` passed for the assigned source/test files. The earlier audit note was corrected to distinguish the reported `tail='none'` board arm from proven MM-free execution; its raw numerical evidence was preserved.

## Limits and next step

These checks establish the demonstrated trust-boundary fixes, not a new algorithm, scientific superiority or complete correctness of every result/analysis path. The backend validator was repaired independently by another agent and uses the same empty-source policy. Root coordinates combined regression testing and commits. This task made no commit and ran no new embedding research benchmark or cluster job.
